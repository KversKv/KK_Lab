#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Test Worker:对多个 BIN 顺序执行 下载 -> 启动 -> Force 测试 的完整流程。

原实现集中在单个巨型方法里,这里保持行为不变,但:
 - 把与 ForceHigh/ForceAuto 共享的 datalog / summary 逻辑抽到 common.py;
 - 把巨型方法按 Step 切分成若干小方法,便于阅读和调试。
"""

import os
import queue
import threading
import time as _time

from PySide6.QtCore import QObject, Signal

from lib.download_tools.download_script import download_bin, detect_chip_from_bin
from chips.bes_chip_configs.bes_chip_configs import get_chip_config

from .common import (
    CURRENT_UNIT,
    _UNIT_CONFIG,
    _format_current_unified,
    build_datalog_tasks,
    build_summary_payload,
    configure_datalog_all,
    fetch_datalog_all,
    start_datalog_sync,
    wait_datalog_with_progress,
)


class AutoTestWorker(QObject):
    log_message = Signal(str)
    channel_result = Signal(str, int, float, str)
    test_summary = Signal(dict)
    progress = Signal(float)
    download_state_changed = Signal(str)
    download_finished = Signal(object)
    download_error = Signal(str)
    finished = Signal()
    error = Signal(str)

    _AUTO_SET_SPECIAL_VOLTAGES = [0.625, 0.67, 0.725, 0.78]

    def __init__(self, com_port, firmware_paths, download_mode,
                 poweron_device_label, poweron_inst, poweron_hw_ch, poweron_polarity,
                 reset_device_label, reset_inst, reset_hw_ch, reset_polarity,
                 vbat_device_label, vbat_inst, vbat_hw_ch,
                 force_map, test_time, sample_period,
                 channel_names=None,
                 chip_combo_text=None, selected_chip_config=None,
                 config_text=None, parse_config_commands_fn=None,
                 resolve_device_fn=None, force_voltages=None):
        super().__init__()
        self.com_port = com_port
        self.firmware_paths = list(firmware_paths)
        self.download_mode = download_mode
        self.poweron_device_label = poweron_device_label
        self.poweron_inst = poweron_inst
        self.poweron_hw_ch = poweron_hw_ch
        self.poweron_polarity = poweron_polarity
        self.reset_device_label = reset_device_label
        self.reset_inst = reset_inst
        self.reset_hw_ch = reset_hw_ch
        self.reset_polarity = reset_polarity
        self.vbat_device_label = vbat_device_label
        self.vbat_inst = vbat_inst
        self.vbat_hw_ch = vbat_hw_ch
        self.force_map = force_map
        self.test_time = test_time
        self.sample_period = sample_period
        self.channel_names = channel_names or {}
        self.chip_combo_text = chip_combo_text
        self.selected_chip_config = selected_chip_config
        self.config_text = config_text or ""
        self._parse_config_commands_fn = parse_config_commands_fn
        self._resolve_device_fn = resolve_device_fn
        self.force_voltages = force_voltages or {}
        self._is_stopped = False

    # ---- 生命周期 ----
    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            self._auto_test()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    # ---- 工具 ----
    @staticmethod
    def _align_voltage(v, special_values=None):
        if special_values is None:
            special_values = AutoTestWorker._AUTO_SET_SPECIAL_VOLTAGES
        grid_v = round(round(v / 0.05) * 0.05, 4)
        best = grid_v
        best_dist = abs(v - grid_v)
        for sv in special_values:
            dist = abs(v - sv)
            if dist < best_dist:
                best = sv
                best_dist = dist
        return best

    def _toggle_signal(self, inst, hw_ch, polarity):
        if polarity == "rising":
            active_v, inactive_v = 2.3, 0.1
        else:
            active_v, inactive_v = 0.1, 2.3
        # 通道可能因上一轮 POWERON/RESET 脉冲结束后已被关闭,先保证 ON 再输出脉冲
        try:
            inst.channel_on(hw_ch)
        except Exception as e:
            self._log(f"[WARNING] channel_on before toggle failed (CH{hw_ch}): {e}")
        inst.set_voltage(hw_ch, active_v)
        _time.sleep(0.1)
        inst.set_voltage(hw_ch, inactive_v)
        # 脉冲发送完毕立即关闭通道,避免持续驱动芯片的控制管脚
        try:
            inst.channel_off(hw_ch)
        except Exception as e:
            self._log(f"[WARNING] channel_off after toggle failed (CH{hw_ch}): {e}")

    def _setup_control_channel(self, inst, hw_ch, polarity):
        v = 0.1 if polarity == "rising" else 2.3
        inst.set_mode(hw_ch, "PS2Q")
        inst.set_voltage(hw_ch, v)
        inst.set_current_limit(hw_ch, 0.2)
        inst.channel_on(hw_ch)

    def _set_force_channels_to_vmeter(self, reason=""):
        """把所有 force_map 中的 enabled 子通道切到 VMeter 模式,避免它们在 Vbat
        测量阶段以 source 状态倒灌/干扰主路电流。"""
        if not self.force_map:
            return
        suffix = f" ({reason})" if reason else ""
        self._log(f"[AUTO_TEST] Setting sub-channels to VMeter to avoid interference{suffix}...")
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                try:
                    n6705c_inst.set_mode(ch, "VMETer")
                    n6705c_inst.channel_on(ch)
                except Exception as e:
                    self._log(f"[WARNING] Failed to set {device_label}-CH{ch} to VMeter: {e}")
        _time.sleep(0.3)

    def _log(self, msg):
        self.log_message.emit(msg)

    # ---- 主流程 ----
    def _auto_test(self):
        total_bins = len(self.firmware_paths)
        if total_bins == 0:
            self.error.emit("No firmware files provided.")
            return

        all_bin_results = []

        for bin_idx, bin_path in enumerate(self.firmware_paths):
            if self._is_stopped:
                return

            bin_name = os.path.basename(bin_path)
            base = bin_idx / total_bins
            span = 1.0 / total_bins

            self._log(f"[AUTO_TEST] === BIN {bin_idx+1}/{total_bins}: {bin_name} ===")

            if not self._prepare_poweron_vbat(base, span):
                return

            detected_chip_name = self._step_detect_chip(bin_path)
            if not self._step_download_and_reset(bin_path, bin_name, base, span):
                return
            if self._is_stopped:
                return

            vbat_current = self._step_measure_vbat_total(base, span)
            if vbat_current is None:
                return

            default_voltages = self._step_record_default_voltages()

            chip_config, config_commands = self._resolve_config_commands(detected_chip_name)
            i2c, chip_info, original_registers = self._step_save_original_registers(config_commands)
            if i2c is None:
                config_commands = None  # 保持原行为:I2C 失败则跳过

            self.progress.emit(base + 0.55 * span)
            if self._is_stopped:
                return

            self._step_force_plus20(default_voltages)
            _time.sleep(0.4)
            self.progress.emit(base + 0.58 * span)
            if self._is_stopped:
                return

            if config_commands and i2c:
                self._step_execute_config_commands(i2c, chip_info, config_commands)
            self.progress.emit(base + 0.62 * span)
            if self._is_stopped:
                return

            self._step_auto_set_voltages(default_voltages)
            _time.sleep(0.4)
            self.progress.emit(base + 0.65 * span)
            if self._is_stopped:
                return

            results, vbat_remain = self._step_sub_channel_consumption(
                vbat_current, base, span,
            )
            if results is None:
                return

            self.progress.emit(base + 0.92 * span)
            if self._is_stopped:
                return

            if config_commands and original_registers and i2c:
                self._step_restore_registers(i2c, original_registers)

            self._step_restore_vmeter()

            channel_voltages = self._collect_channel_voltages(default_voltages)
            self._emit_summary(results, vbat_current, vbat_remain, bin_name, channel_voltages)

            all_bin_results.append({
                "bin_name": bin_name,
                "vbat": vbat_current,
                "channels": dict(results),
                "vbat_remain": vbat_remain,
                "channel_voltages": channel_voltages,
            })
            self.progress.emit(base + span)
            self._log(f"[AUTO_TEST] === BIN {bin_idx+1}/{total_bins}: {bin_name} completed ===")

        self.progress.emit(1.0)
        if len(all_bin_results) > 1:
            self._emit_final_summary_table(all_bin_results)
        self._log("[AUTO_TEST] All auto test completed.")

    # ---- Step 子方法 ----
    def _prepare_poweron_vbat(self, base, span):
        self._log("[AUTO_TEST] Step 1: Configuring PowerON and RESET channels...")
        self._setup_control_channel(self.poweron_inst, self.poweron_hw_ch, self.poweron_polarity)
        self._setup_control_channel(self.reset_inst, self.reset_hw_ch, self.reset_polarity)
        self.progress.emit(base + 0.02 * span)
        if self._is_stopped:
            return False

        self._log("[AUTO_TEST] Step 2: Configuring Vbat channel (3.8V, 0.2A)...")
        self.vbat_inst.set_mode(self.vbat_hw_ch, "PS2Q")
        self.vbat_inst.set_voltage(self.vbat_hw_ch, 3.8)
        self.vbat_inst.set_current_limit(self.vbat_hw_ch, 0.2)
        self.vbat_inst.channel_on(self.vbat_hw_ch)
        _time.sleep(0.5)
        self.progress.emit(base + 0.04 * span)
        return not self._is_stopped

    def _step_detect_chip(self, bin_path):
        chip = detect_chip_from_bin(bin_path)
        if chip:
            self._log(f"[AUTO_TEST] Detected chip from BIN: {chip}")
            return f"bes{chip.lower()}"
        return None

    def _step_download_and_reset(self, bin_path, bin_name, base, span):
        self._log(f"[AUTO_TEST] Step 3: Starting download listener: {bin_name}")
        download_thread, result_queue = self._start_download_async(bin_path)
        _time.sleep(0.4)

        self._log("[AUTO_TEST] Step 4: Triggering RESET then POWERON for download handshake...")
        self._toggle_signal(self.reset_inst, self.reset_hw_ch, self.reset_polarity)
        _time.sleep(0.05)
        self._toggle_signal(self.poweron_inst, self.poweron_hw_ch, self.poweron_polarity)

        self._log("[AUTO_TEST] Waiting for download to complete...")
        download_thread.join(timeout=180)
        download_result = None
        try:
            download_result = result_queue.get_nowait()
        except Exception:
            pass
        self.progress.emit(base + 0.30 * span)
        if self._is_stopped:
            return False

        if download_result is None or not download_result.success:
            err_msg = "Unknown error"
            if download_result and download_result.error_message:
                err_msg = download_result.error_message
            self._log(f"[AUTO_TEST] Download failed: {err_msg}")
            self.error.emit(f"Download failed for {bin_name}: {err_msg}")
            return False

        self._log("[AUTO_TEST] Step 5: Download completed successfully.")
        if self._is_stopped:
            return False

        self._log("[AUTO_TEST] Step 6: Sending POWERON then RESET to boot chip...")
        self._toggle_signal(self.poweron_inst, self.poweron_hw_ch, self.poweron_polarity)
        _time.sleep(0.05)
        self._toggle_signal(self.reset_inst, self.reset_hw_ch, self.reset_polarity)
        self._log("[AUTO_TEST] Waiting 2s for chip stabilization...")
        _time.sleep(2.0)
        self.progress.emit(base + 0.35 * span)
        return not self._is_stopped

    def _step_measure_vbat_total(self, base, span):
        self._log("[AUTO_TEST] Step 7: Measuring Vbat total current...")
        # 在采集 Vbat 之前,确保其它 enabled 子通道处于 VMeter(只测量)状态,
        # 防止它们以 source 模式干扰 Vbat 主路电流。
        self._set_force_channels_to_vmeter(reason="pre-Vbat")
        if self._is_stopped:
            return None
        stop_check = lambda: self._is_stopped
        vbat_result = self.vbat_inst.fetch_current_by_datalog(
            [self.vbat_hw_ch], self.test_time, self.sample_period,
            stop_check=stop_check,
        )
        if self._is_stopped:
            return None
        vbat_current = vbat_result.get(self.vbat_hw_ch, 0.0)
        self.channel_result.emit(
            self.vbat_device_label, self.vbat_hw_ch, float(vbat_current), "vbat"
        )
        self._log(
            f"[AUTO_TEST] Vbat total current: {_format_current_unified(vbat_current)}"
        )
        self.progress.emit(base + 0.50 * span)
        if self._is_stopped:
            return None
        return vbat_current

    def _step_record_default_voltages(self):
        self._log("[AUTO_TEST] Step 8: Recording default sub-channel voltages...")
        # Step 7 已经把子通道切到 VMeter;这里兜底一次,避免某些异常路径跳过。
        self._set_force_channels_to_vmeter(reason="pre-measure")
        default_voltages = {}
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                try:
                    v = float(n6705c_inst.measure_voltage(ch))
                    default_voltages[(device_label, ch)] = v
                    ch_name = self.channel_names.get(
                        (device_label, ch), f"{device_label}-CH{ch}"
                    )
                    self._log(f"[AUTO_TEST]   {ch_name}: {v:.4f}V")
                except Exception as e:
                    self._log(f"[WARNING] Failed to measure {device_label}-CH{ch}: {e}")
                    default_voltages[(device_label, ch)] = 0.0
        return default_voltages

    def _resolve_config_commands(self, detected_chip_name):
        chip_config = self.selected_chip_config
        if detected_chip_name:
            refreshed = get_chip_config(detected_chip_name, force_reload=True)
            if refreshed:
                chip_config = refreshed
                self._log(f"[AUTO_TEST] Using chip config for: {detected_chip_name}")

        config_commands = None
        if self.config_text:
            config_commands = self._parse_config_commands_fn(self.config_text)
            self._log(
                f"[AUTO_TEST] Using pasted configuration ({len(config_commands)} commands)"
            )
        elif chip_config:
            pd = chip_config.get("power_distribution")
            if pd and isinstance(pd, dict) and len(pd) > 0:
                raw_lines = []
                for _section, cmds in pd.items():
                    if isinstance(cmds, list):
                        raw_lines.extend(cmds)
                config_commands = self._parse_config_commands_fn("\n".join(raw_lines))
                self._log(
                    f"[AUTO_TEST] Using chip config power_distribution "
                    f"({len(config_commands)} commands)"
                )
        return chip_config, config_commands

    def _step_save_original_registers(self, config_commands):
        if not config_commands:
            return None, None, {}

        self._log("[AUTO_TEST] Step 8 (cont.): Recording original register values...")
        original_registers = {}
        try:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            i2c = I2CInterface()
            if not i2c.initialize():
                self._log("[ERROR] I2C interface initialization failed.")
                return None, None, {}
            chip_info = i2c.bes_chip_check()
            self._log(
                f"[AUTO_TEST] Chip detected via I2C: {chip_info.get('chip_name', 'N/A')}"
            )
            for cmd in config_commands:
                if cmd["op"] not in ("WRITE", "WRITE_BITS"):
                    continue
                target = cmd.get("target", "NO_PREFIX")
                reg_addr = cmd["reg_addr"]
                device_addr, width = self._resolve_device_fn(chip_info, target)
                if device_addr is None or width is None:
                    continue
                key = (device_addr, reg_addr, width)
                if key in original_registers:
                    continue
                try:
                    val = i2c.read(device_addr, reg_addr, width)
                    original_registers[key] = val
                    self._log(
                        f"[AUTO_TEST]   Saved reg dev=0x{device_addr:02X} "
                        f"addr=0x{reg_addr:08X} = 0x{val:X}"
                    )
                except Exception as e:
                    self._log(
                        f"[WARNING] Failed to read reg 0x{reg_addr:08X}: {e}"
                    )
            return i2c, chip_info, original_registers
        except Exception as e:
            self._log(f"[ERROR] I2C setup failed: {e}")
            return None, None, {}

    def _step_force_plus20(self, default_voltages):
        self._log("[AUTO_TEST] Step 9: Setting sub-channels to default voltage + 20mV...")
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                try:
                    fv = self.force_voltages.get((device_label, ch))
                    ch_name = self.channel_names.get(
                        (device_label, ch), f"{device_label}-CH{ch}"
                    )
                    if fv is not None:
                        n6705c_inst.set_mode(ch, "PS2Q")
                        n6705c_inst.set_voltage(ch, fv)
                        n6705c_inst.set_current_limit(ch, 1.0)
                        n6705c_inst.channel_on(ch)
                        self._log(
                            f"[AUTO_TEST]   {ch_name}: Force Vol -> {fv:.4f}V (user override)"
                        )
                    else:
                        v_default = default_voltages.get((device_label, ch), 0.0)
                        v_plus20 = v_default + 0.02
                        n6705c_inst.set_mode(ch, "PS2Q")
                        n6705c_inst.set_voltage(ch, v_plus20)
                        n6705c_inst.set_current_limit(ch, 1.0)
                        n6705c_inst.channel_on(ch)
                        self._log(
                            f"[AUTO_TEST]   {ch_name}: {v_default:.4f}V -> {v_plus20:.4f}V (+20mV)"
                        )
                except Exception as e:
                    self._log(f"[ERROR] Failed to set {device_label}-CH{ch}: {e}")

    def _step_execute_config_commands(self, i2c, chip_info, config_commands):
        self._log("[AUTO_TEST] Step 10: Executing configuration commands...")
        try:
            for idx_cmd, cmd in enumerate(config_commands):
                op = cmd["op"]
                target = cmd.get("target", "NO_PREFIX")
                reg_addr = cmd["reg_addr"]
                device_addr, width = self._resolve_device_fn(chip_info, target)
                if device_addr is None or width is None:
                    self._log(
                        f"[ERROR] Cannot resolve device for target={target}, "
                        f"skip cmd #{idx_cmd+1}"
                    )
                    continue
                if op == "WRITE_BITS":
                    msb, lsb, value = cmd["msb"], cmd["lsb"], cmd["value"]
                    current_val = i2c.read(device_addr, reg_addr, width)
                    bit_mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                    new_val = (current_val & ~bit_mask) | ((value << lsb) & bit_mask)
                    i2c.write(device_addr, reg_addr, new_val, width)
                    self._log(
                        f"[AUTO_TEST]   #{idx_cmd+1} WRITE_BITS dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} [{msb}:{lsb}]=0x{value:X} "
                        f"(0x{current_val:X} -> 0x{new_val:X})"
                    )
                elif op == "WRITE":
                    value = cmd["value"]
                    i2c.write(device_addr, reg_addr, value, width)
                    self._log(
                        f"[AUTO_TEST]   #{idx_cmd+1} WRITE dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} data=0x{value:X}"
                    )
                elif op == "READ":
                    read_val = i2c.read(device_addr, reg_addr, width)
                    self._log(
                        f"[AUTO_TEST]   #{idx_cmd+1} READ dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} => 0x{read_val:X}"
                    )
        except Exception as e:
            self._log(f"[ERROR] Config execution failed: {e}")

    def _step_auto_set_voltages(self, default_voltages):
        self._log(
            "[AUTO_TEST] Step 11: Adjusting sub-channels with Auto Set logic "
            "(in-place, keep PS2Q alive)..."
        )
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                try:
                    fv = self.force_voltages.get((device_label, ch))
                    ch_name = self.channel_names.get(
                        (device_label, ch), f"{device_label}-CH{ch}"
                    )
                    if fv is not None:
                        n6705c_inst.set_voltage(ch, fv)
                        self._log(
                            f"[AUTO_TEST]   {ch_name}: Force Vol -> {fv:.4f}V (user override)"
                        )
                    else:
                        v_default = default_voltages.get((device_label, ch), 0.0)
                        aligned_v = self._align_voltage(v_default)
                        v_plus20 = v_default + 0.02
                        new_v = max(aligned_v, v_default)
                        n6705c_inst.set_voltage(ch, new_v)
                        self._log(
                            f"[AUTO_TEST]   {ch_name}: {v_plus20:.4f}V -> {new_v:.4f}V "
                            f"(default={v_default:.4f}V, aligned={aligned_v:.4f}V)"
                        )
                except Exception as e:
                    self._log(f"[ERROR] Auto set failed {device_label}-CH{ch}: {e}")

    def _step_sub_channel_consumption(self, vbat_current, base, span):
        self._log("[AUTO_TEST] Step 12: Running sub-channel consumption test...")
        results = {(self.vbat_device_label, self.vbat_hw_ch): float(vbat_current)}
        vbat_remain = None

        task_list = build_datalog_tasks(
            self.force_map, self.vbat_device_label, self.vbat_hw_ch, self.sample_period
        )

        if not task_list:
            return results, vbat_remain

        self._log("[AUTO_TEST] Configuring datalog on instruments...")
        active_tasks = configure_datalog_all(task_list, self.test_time, self._log)
        if not active_tasks:
            return results, vbat_remain

        start_datalog_sync(active_tasks, self._log, timeout=30)

        def _tick(frac):
            self.progress.emit(base + (0.65 + frac * 0.25) * span)

        if not wait_datalog_with_progress(self.test_time, lambda: self._is_stopped, _tick):
            return None, None

        self._log("[AUTO_TEST] Fetching results...")
        fetch_errors = fetch_datalog_all(active_tasks, self.test_time, self._log, timeout=30)

        vbat_label = self.vbat_device_label
        vbat_ch = self.vbat_hw_ch
        for idx, task in enumerate(active_tasks):
            if fetch_errors[idx]:
                continue
            cr = task["curr_result"] or {}
            for ch in task["force_channels"]:
                avg_i = cr.get(ch, 0.0)
                self.channel_result.emit(
                    task["device_label"], ch, float(avg_i), "force_auto"
                )
                results[(task["device_label"], ch)] = float(avg_i)
            if task["device_label"] == vbat_label and vbat_ch in cr:
                vbat_remain = float(cr[vbat_ch])
        return results, vbat_remain

    def _step_restore_registers(self, i2c, original_registers):
        self._log("[AUTO_TEST] Step 13: Restoring original register values...")
        for (device_addr, reg_addr, width), orig_val in original_registers.items():
            try:
                i2c.write(device_addr, reg_addr, orig_val, width)
                self._log(
                    f"[AUTO_TEST]   Restored dev=0x{device_addr:02X} "
                    f"reg=0x{reg_addr:08X} = 0x{orig_val:X}"
                )
            except Exception as e:
                self._log(
                    f"[WARNING] Failed to restore reg 0x{reg_addr:08X}: {e}"
                )

    def _step_restore_vmeter(self):
        self._log("[AUTO_TEST] Step 14: Restoring sub-channels to VMeter mode...")
        for _device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            n6705c_inst.restore_channels_to_vmeter(hw_channels)

    def _collect_channel_voltages(self, default_voltages):
        channel_voltages = {}
        try:
            vbat_v = float(self.vbat_inst.measure_voltage(self.vbat_hw_ch))
        except Exception:
            vbat_v = 3.8
        channel_voltages[(self.vbat_device_label, self.vbat_hw_ch)] = vbat_v
        for key, v in default_voltages.items():
            fv = self.force_voltages.get(key)
            channel_voltages[key] = fv if fv is not None else v
        return channel_voltages

    # ---- 下载异步 ----
    def _start_download_async(self, bin_path):
        result_queue = queue.Queue()

        def _download_thread_fn():
            try:
                def _on_state(state):
                    self.download_state_changed.emit(state.value)
                result = download_bin(
                    com_port=self.com_port,
                    bin_file=bin_path,
                    mode=self.download_mode,
                    timeout=120,
                    on_state_change=_on_state,
                )
                result_queue.put(result)
            except Exception as e:
                self.download_error.emit(str(e))
                result_queue.put(None)

        t = threading.Thread(target=_download_thread_fn, daemon=True)
        t.start()
        return t, result_queue

    def _run_download(self, bin_path):
        # 保留旧接口:同步方式跑一次下载。
        result_queue = queue.Queue()

        def _download_thread_fn():
            try:
                def _on_state(state):
                    self.download_state_changed.emit(state.value)
                result = download_bin(
                    com_port=self.com_port,
                    bin_file=bin_path,
                    mode=self.download_mode,
                    timeout=120,
                    on_state_change=_on_state,
                )
                result_queue.put(result)
            except Exception as e:
                self.download_error.emit(str(e))
                result_queue.put(None)

        t = threading.Thread(target=_download_thread_fn, daemon=True)
        t.start()
        t.join(timeout=180)
        try:
            return result_queue.get_nowait()
        except queue.Empty:
            return None

    # ---- 输出 ----
    def _emit_summary(self, results, vbat_current, vbat_remain,
                      bin_name="", channel_voltages=None):
        summary, _ = build_summary_payload(
            device_map=self.force_map,
            channel_names=self.channel_names,
            vbat_label=self.vbat_device_label,
            vbat_ch=self.vbat_hw_ch,
            results=results,
            vbat_current=vbat_current,
            vbat_remain=vbat_remain,
            channel_voltages=channel_voltages,
            log_fn=self._log,
            bin_name=bin_name,
        )
        self.test_summary.emit(summary)

    def _emit_final_summary_table(self, all_bin_results):
        vbat_name = self.channel_names.get(
            (self.vbat_device_label, self.vbat_hw_ch), "Vbat"
        )
        ordered_keys = []
        for device_label, (_, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                ordered_keys.append((device_label, ch))

        voltage_sub_headers = [vbat_name] + [
            self.channel_names.get(key, f"{key[0]}-CH{key[1]}") for key in ordered_keys
        ]

        col_headers = [vbat_name]
        for key in ordered_keys:
            col_headers.append(self.channel_names.get(key, f"{key[0]}-CH{key[1]}"))
        has_vbat_remain = any(r.get("vbat_remain") is not None for r in all_bin_results)
        if has_vbat_remain:
            col_headers.append("Vbat_remain")

        cfg = _UNIT_CONFIG.get(CURRENT_UNIT, _UNIT_CONFIG["uA"])
        scale = cfg["scale"]
        suffix = cfg["suffix"]

        rows = []
        voltage_rows = []
        for r in all_bin_results:
            bin_name = r["bin_name"]
            channels = r.get("channels", {})
            vals = [f"{r.get('vbat', 0.0) * scale:.4f}"]
            for key in ordered_keys:
                vals.append(f"{channels.get(key, 0.0) * scale:.4f}")
            if has_vbat_remain:
                vr = r.get("vbat_remain")
                vals.append(f"{vr * scale:.4f}" if vr is not None else "N/A")
            rows.append((bin_name, vals))

            cv = r.get("channel_voltages", {})
            vbat_v = cv.get((self.vbat_device_label, self.vbat_hw_ch))
            v_vals = [f"{vbat_v:.4g}" if vbat_v is not None else "N/A"]
            for key in ordered_keys:
                kv = cv.get(key)
                v_vals.append(f"{kv:.4g}" if kv is not None else "N/A")
            voltage_rows.append((bin_name, v_vals))

        bin_col_width = max(len(r[0]) for r in rows)
        bin_col_width = max(bin_col_width, len("BIN"))

        voltage_sub_widths = []
        for i, sub in enumerate(voltage_sub_headers):
            max_w = len(sub)
            for _, v_vals in voltage_rows:
                max_w = max(max_w, len(v_vals[i]))
            voltage_sub_widths.append(max_w)

        val_col_widths = []
        for i, hdr in enumerate(col_headers):
            max_w = len(hdr)
            for _, vals in rows:
                max_w = max(max_w, len(vals[i]))
            val_col_widths.append(max_w)

        voltage_header_str = " | ".join(
            f"{h:>{voltage_sub_widths[i]}}" for i, h in enumerate(voltage_sub_headers)
        )
        voltage_col_width = len(voltage_header_str)
        voltage_col_header = "Voltage"
        if len(voltage_col_header) < voltage_col_width:
            pad_total = voltage_col_width - len(voltage_col_header)
            left = pad_total // 2
            right = pad_total - left
            voltage_col_header_padded = " " * left + voltage_col_header + " " * right
        else:
            voltage_col_header_padded = voltage_col_header
            voltage_col_width = len(voltage_col_header)

        unit_label = f"(Unit: {suffix})"

        sep = " | "
        header_cells = [f"{'BIN':<{bin_col_width}}", voltage_col_header_padded]
        for i, hdr in enumerate(col_headers):
            header_cells.append(f"{hdr:>{val_col_widths[i]}}")
        header_line = sep.join(header_cells)

        sub_header_cells = [" " * bin_col_width, voltage_header_str]
        for i, _ in enumerate(col_headers):
            sub_header_cells.append(" " * val_col_widths[i])
        sub_header_line = sep.join(sub_header_cells)

        total_width = len(header_line)
        sep_line = "-" * total_width

        self._log("[SUMMARY] " + "=" * total_width)
        self._log(f"[SUMMARY] Auto Test Results {unit_label}")
        self._log("[SUMMARY] " + sep_line)
        self._log(f"[SUMMARY] {header_line}")
        self._log(f"[SUMMARY] {sub_header_line}")
        self._log("[SUMMARY] " + sep_line)
        for idx, (bin_name, vals) in enumerate(rows):
            _, v_vals = voltage_rows[idx]
            voltage_cell = " | ".join(
                f"{v:>{voltage_sub_widths[i]}}" for i, v in enumerate(v_vals)
            )
            cells = [f"{bin_name:<{bin_col_width}}",
                     f"{voltage_cell:>{voltage_col_width}}"]
            for i, v in enumerate(vals):
                cells.append(f"{v:>{val_col_widths[i]}}")
            self._log(f"[SUMMARY] {sep.join(cells)}")
        self._log("[SUMMARY] " + "=" * total_width)


__all__ = ["AutoTestWorker"]
