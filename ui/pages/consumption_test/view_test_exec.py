#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test 测试执行与结果导出（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - 固件下载槽：_browse_firmware / _download_to_dut / _on_ctrl_download_started /
    _on_ctrl_download_state_changed / _on_ctrl_download_finished /
    _on_ctrl_download_error / _on_ctrl_download_cleaned / _stop_download
  - 通道 force 配置：_parse_channel_key / _build_channel_force_configs
  - 测试流程：_on_start_test / _start_test / consumption_test_force /
    _on_force_high_channel_result / _on_test_summary / _on_test_error /
    _on_test_finished / _on_test_thread_cleaned / _stop_test
  - Auto Test：_on_auto_test / _on_auto_test_error / _on_auto_test_finished /
    _on_auto_test_thread_cleaned / _stop_auto_test
  - 导出：_save_datalog / _export_bin_results_to_excel
  - 公共读取：_format_current / update_channel_current /
    get_selected_channels / get_test_config

依赖宿主类（ConsumptionTestUI）与其它 Mixin 提供属性与槽。
"""

import os
import re
from PySide6.QtWidgets import (
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import QThread
from lib.download_tools.download_script import (
    DownloadMode,
    DownloadState,
)
from ui.widgets.progress_button import ProgressButton
from log_config import get_logger
from core.consumption_test.workers import (
    _ConsumptionTestForceHighWorker,
    _ConsumptionTestForceWorker,
)

logger = get_logger(__name__)


class ConsumptionTestViewTestExecMixin:

    def _browse_firmware(self):
        start_dir = os.path.dirname(self.firmware_path)
        if not os.path.isdir(start_dir):
            start_dir = ""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Firmware File(s)", start_dir,
            "Firmware Files (*.bin *.hex);;All Files (*)"
        )
        if file_paths:
            self.firmware_paths = file_paths
            self.firmware_path = file_paths[0]
            names = [os.path.basename(p) for p in file_paths]
            self.firmware_file_input.setText("; ".join(names))
            for fp in file_paths:
                self.append_log(f"[SYSTEM] Firmware file selected: {os.path.basename(fp)}")

    def _download_to_dut(self):
        if not self.firmware_path:
            logger.warning("No firmware file selected")
            self.append_log("[WARNING] No firmware file selected.")
            return

        if self._controller.is_download_running():
            logger.warning("Download already in progress")
            self.append_log("[WARNING] Download already in progress.")
            return

        port_text = self.get_selected_serial_port()
        if not port_text:
            logger.warning("No serial port selected")
            self.append_log("[WARNING] No serial port selected.")
            return

        m = re.search(r'(\d+)', port_text)
        com_port = m.group(1) if m else port_text

        mode_str = self.download_mode_toggle.value().lower()
        mode = DownloadMode.FLASH if mode_str == "flash" else DownloadMode.RAMRUN

        self._controller.start_download(com_port, self.firmware_path, mode)

    def _on_ctrl_download_started(self, file_size):
        self.download_btn.setFileSize(file_size)
        self.download_btn.setStateWaiting()

    def _on_ctrl_download_state_changed(self, state_value):
        if state_value in (DownloadState.WAITING_SYNC.value, DownloadState.SYNCING.value):
            if self.download_btn.state() != ProgressButton.STATE_WAITING:
                self.download_btn.setStateWaiting()
        elif state_value == DownloadState.PROGRAMMING.value:
            self.download_btn.setStateProgramming()

    def _on_ctrl_download_finished(self, result):
        if result.success:
            self.download_btn.setStateComplete()
        else:
            self.download_btn.setStateFailed()

    def _on_ctrl_download_error(self, err_msg):
        self.download_btn.setStateFailed()

    def _on_ctrl_download_cleaned(self):
        pass

    def _stop_download(self):
        self._controller.stop_download()
        self.download_btn.setStateFailed()
        self.append_log("[DOWNLOAD] Download stopped by user.")
        logger.info("Download stopped by user")

    def _parse_channel_key(self, channel_key):
        m = re.match(r'^([AB])-CH(\d+)$', channel_key)
        if m:
            return m.group(1), int(m.group(2))
        m = re.match(r'^GPIO(\d+)$', channel_key, re.IGNORECASE)
        if m:
            return "MCU", int(m.group(1))
        return None, None

    def _build_channel_force_configs(self):
        """构建每通道的 force 配置字典。

        返回:
            {(device_label, hw_ch): {
                "force_mode": "force"/"auto",
                "force_value": float,        # force 模式下的目标电压(V)
                "boost_mode": "constant"/"percent",
                "boost_value": float,        # auto 模式下的增压值
            }}
            Force 模式且 force_value 为空/非法时跳过该通道(走 Auto 默认值)。
            Auto 模式下 boost_value 为空/非法时使用默认 0.02。
        """
        configs = {}
        for cfg in self._channel_configs:
            if not cfg["enabled"]:
                continue
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                continue

            force_mode = cfg.get("force_mode", "auto")
            entry = {
                "force_mode": force_mode,
                "force_value": None,
                "boost_mode": cfg.get("boost_mode", "constant"),
                "boost_value": 0.02,
            }

            if force_mode == "force":
                val_text = cfg.get("force_value", "").strip()
                if not val_text:
                    continue
                try:
                    entry["force_value"] = float(val_text)
                except ValueError:
                    continue
            else:
                val_text = cfg.get("boost_value", "").strip()
                if val_text:
                    try:
                        entry["boost_value"] = float(val_text)
                    except ValueError:
                        pass

            configs[(device_label, hw_ch)] = entry
        return configs

    def _on_start_test(self):
        self._start_test()

    def _start_test(self):
        if self.is_testing:
            return

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        force_high_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}

        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                self.append_log(f"[ERROR] Invalid channel key: {cfg['channel']}")
                return
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            is_conn = getattr(self, f"is_connected_{attr}", False)
            if not is_conn or not inst:
                self.append_log(f"[ERROR] N6705C-{device_label} is not connected (required by {cfg['name']}).")
                return
            if device_label not in force_high_map:
                force_high_map[device_label] = (inst, [])
            if hw_ch not in force_high_map[device_label][1]:
                force_high_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = 0
        self.bin_result_table.hide()
        self.start_test_btn.setStateWaiting()
        self.append_log(
            f"[TEST] Starting force-high consumption test: "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"time={test_time}s, base_period={sample_period*1e6:.0f}us"
        )

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is not None and hw_ch is not None:
                channel_names[(device_label, hw_ch)] = cfg["name"]

        worker = _ConsumptionTestForceHighWorker(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_high_map, test_time, sample_period,
            channel_names=channel_names,
            channel_force_configs=self._build_channel_force_configs(),
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.channel_result.connect(self._on_force_high_channel_result)
        worker.test_summary.connect(self._on_test_summary)
        worker.progress.connect(self.start_test_btn.setProgress)
        worker.error.connect(self._on_test_error)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        self.start_test_btn.setStateProgramming()
        self.start_test_btn._progress_timer.stop()
        thread.start()

    def consumption_test_force(self):
        if self.is_testing:
            return

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        force_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}

        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                self.append_log(f"[ERROR] Invalid channel key: {cfg['channel']}")
                return
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            is_conn = getattr(self, f"is_connected_{attr}", False)
            if not is_conn or not inst:
                self.append_log(f"[ERROR] N6705C-{device_label} is not connected (required by {cfg['name']}).")
                return
            if device_label not in force_map:
                force_map[device_label] = (inst, [])
            if hw_ch not in force_map[device_label][1]:
                force_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = 0
        self.bin_result_table.hide()
        self.start_test_btn.setStateWaiting()
        self.append_log(
            f"[TEST] Starting force-auto consumption test: "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"time={test_time}s, base_period={sample_period*1e6:.0f}us"
        )

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is not None and hw_ch is not None:
                channel_names[(device_label, hw_ch)] = cfg["name"]

        worker = _ConsumptionTestForceWorker(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_map, test_time, sample_period,
            channel_names=channel_names,
            channel_force_configs=self._build_channel_force_configs(),
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.channel_result.connect(self._on_force_high_channel_result)
        worker.test_summary.connect(self._on_test_summary)
        worker.progress.connect(self.start_test_btn.setProgress)
        worker.error.connect(self._on_test_error)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        self.start_test_btn.setStateProgramming()
        self.start_test_btn._progress_timer.stop()
        thread.start()

    def _on_force_high_channel_result(self, device_label, hw_channel, avg_current, phase):
        cfg_idx = self._config_index_map.get(device_label, {}).get(hw_channel)
        if cfg_idx is not None and cfg_idx in self.channel_cards:
            label = self.channel_cards[cfg_idx]["value_label"]
            label.setText(self._format_current(avg_current))

    def _on_test_summary(self, summary):
        vbat_remain = summary.get("vbat_remain")
        if vbat_remain is not None and self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText(self._format_current(vbat_remain))

        if self._current_total_bins > 1:
            self._bin_results_data.append(summary)
            self._add_bin_result_row(summary)

    def _on_test_error(self, err_msg):
        self.append_log(f"[ERROR] {err_msg}")

    def _on_test_finished(self):
        self.is_testing = False
        self.start_test_btn.setStateComplete()
        self.append_log("[TEST] Test completed.")

    def _on_test_thread_cleaned(self):
        self._test_worker = None
        self._test_thread = None

    def _stop_test(self):
        if self._test_worker:
            self._test_worker.stop()
        self.is_testing = False
        self.start_test_btn.setStateFailed()
        self.append_log("[TEST] Test stopped.")

    def _on_auto_test(self):
        if self.is_testing:
            self.append_log("[WARNING] A test is already running.")
            return

        firmware_paths = getattr(self, 'firmware_paths', [])
        if not firmware_paths:
            if self.firmware_path:
                firmware_paths = [self.firmware_path]
            else:
                self.append_log("[ERROR] No firmware file selected.")
                return

        port_text = self.get_selected_serial_port()
        if not port_text:
            self.append_log("[ERROR] No serial port selected.")
            return
        m = re.search(r'(\d+)', port_text)
        com_port = m.group(1) if m else port_text

        mode_str = self.download_mode_toggle.value().lower()
        download_mode = DownloadMode.FLASH if mode_str == "flash" else DownloadMode.RAMRUN

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        poweron_key = self.poweron_channel_combo.currentText() if self.poweron_channel_combo else ""
        reset_enabled = (
            self.reset_enable_cb.isChecked()
            if getattr(self, "reset_enable_cb", None) is not None else False
        )
        control_method = (
            self.control_method_toggle.value()
            if getattr(self, "control_method_toggle", None) else "N6705C"
        )
        reset_key = self.reset_channel_combo.currentText() if self.reset_channel_combo else ""
        if not poweron_key:
            self.append_log("[ERROR] PowerON channel not configured.")
            return
        if reset_enabled and not reset_key:
            self.append_log("[ERROR] RESET channel not configured.")
            return

        poweron_dl, poweron_hw = self._parse_channel_key(poweron_key)
        if poweron_dl is None:
            self.append_log("[ERROR] Invalid PowerON channel key.")
            return
        if reset_enabled:
            reset_dl, reset_hw = self._parse_channel_key(reset_key)
            if reset_dl is None:
                self.append_log("[ERROR] Invalid RESET channel key.")
                return
        else:
            reset_dl, reset_hw = None, None

        if control_method == "MCU":
            if poweron_dl != "MCU" or (reset_enabled and reset_dl != "MCU"):
                self.append_log("[ERROR] MCU control requires GPIO channels for PowerON/RESET.")
                return
            if not self.is_mcu_connected or self.mcu_io is None:
                self.append_log("[ERROR] MCU IO is not connected (required by PowerON/RESET).")
                return
            poweron_inst = self.mcu_io
            poweron_dl = "MCU"
            if reset_enabled:
                reset_inst = self.mcu_io
                reset_dl = "MCU"
            else:
                reset_inst = None
        else:
            poweron_attr = poweron_dl.lower()
            poweron_inst = getattr(self, f"n6705c_{poweron_attr}", None)
            poweron_conn = getattr(self, f"is_connected_{poweron_attr}", False)
            if not poweron_conn or not poweron_inst:
                self.append_log(f"[ERROR] N6705C-{poweron_dl} is not connected (required by PowerON).")
                return

            if reset_enabled:
                reset_attr = reset_dl.lower()
                reset_inst = getattr(self, f"n6705c_{reset_attr}", None)
                reset_conn = getattr(self, f"is_connected_{reset_attr}", False)
                if not reset_conn or not reset_inst:
                    self.append_log(f"[ERROR] N6705C-{reset_dl} is not connected (required by RESET).")
                    return
            else:
                reset_inst = None

        poweron_polarity = self.poweron_polarity_toggle.value()
        reset_polarity = (
            self.reset_polarity_toggle.value() if reset_enabled else "rising"
        )

        force_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}
        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                self.append_log(f"[ERROR] Invalid channel key: {cfg['channel']}")
                return
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            is_conn = getattr(self, f"is_connected_{attr}", False)
            if not is_conn or not inst:
                self.append_log(f"[ERROR] N6705C-{device_label} is not connected (required by {cfg['name']}).")
                return
            if device_label not in force_map:
                force_map[device_label] = (inst, [])
            if hw_ch not in force_map[device_label][1]:
                force_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        try:
            stabilization_delay_sec = float(self.stable_delay_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid stable delay.")
            return
        try:
            download_pgm_rate = int(self.download_baudrate_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid baudrate.")
            return
        sample_period = 20.0 / 1_000_000

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            dl, hw = self._parse_channel_key(cfg["channel"])
            if dl is not None and hw is not None:
                channel_names[(dl, hw)] = cfg["name"]

        # 根据测试模式决定 config_text 来源:
        #   standard(标准电压) → 按启用通道 Name 匹配电源轨配置合并
        #   high_voltage(外供高压) → 不需要 I2C 配置, config_text 留空
        test_mode = getattr(self, "_test_mode", "high_voltage")
        if test_mode == "standard":
            config_text = self._build_config_text_for_standard_mode(enabled_configs)
        else:
            config_text = ""

        # 两个测试前配置区域: 开关 ON 且有内容时传入 worker, 作为独立步骤经 I2C 下发
        #   vbat_pre_test          → Step 8.5, Step 9(Vbat 总电流测量)前
        #   power_pre_distribution → Step 10.5, Step 10 外供电压稳定后、Step 11 主配置前
        vbat_pre_test_text = (
            self._get_pre_config_text("vbat_pre_test")
            if self._get_pre_config_enabled("vbat_pre_test") else ""
        )
        power_pre_distribution_text = (
            self._get_pre_config_text("power_pre_distribution")
            if self._get_pre_config_enabled("power_pre_distribution") else ""
        )

        chip_combo_text = self.chip_combo.currentText() if self.chip_combo.currentIndex() > 0 else None

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = len(firmware_paths)
        self.auto_test_btn.setStateWaiting()

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        if self._current_total_bins > 1:
            self._setup_bin_result_table()
        else:
            self.bin_result_table.hide()

        reset_desc = f"{reset_key}({reset_polarity})" if reset_enabled else "DISABLED"
        mode_desc = "Std V (配置模式)" if test_mode == "standard" else "High V (外供高压)"
        vbat_pre_desc = (
            f"ON({len([ln for ln in vbat_pre_test_text.splitlines() if ln.strip()])} cmds)"
            if vbat_pre_test_text else "OFF"
        )
        pre_dist_desc = (
            f"ON({len([ln for ln in power_pre_distribution_text.splitlines() if ln.strip()])} cmds)"
            if power_pre_distribution_text else "OFF"
        )
        self.append_log(
            f"[AUTO_TEST] Starting auto test: {len(firmware_paths)} BIN(s), "
            f"Mode={mode_desc}, "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"Control={control_method}, "
            f"PowerON={poweron_key}({poweron_polarity}), "
            f"RESET={reset_desc}, "
            f"VbatPreCfg={vbat_pre_desc}, "
            f"PreDistCfg={pre_dist_desc}, "
            f"StableDelay={stabilization_delay_sec:.1f}s, "
            f"Baudrate={download_pgm_rate}"
        )

        worker_kwargs = dict(
            com_port=com_port,
            firmware_paths=firmware_paths,
            download_mode=download_mode,
            poweron_device_label=poweron_dl,
            poweron_inst=poweron_inst,
            poweron_hw_ch=poweron_hw,
            poweron_polarity=poweron_polarity,
            reset_device_label=reset_dl,
            reset_inst=reset_inst,
            reset_hw_ch=reset_hw,
            reset_polarity=reset_polarity,
            vbat_device_label=vbat_device_label,
            vbat_inst=vbat_inst,
            vbat_hw_ch=vbat_hw_ch,
            force_map=force_map,
            test_time=test_time,
            sample_period=sample_period,
            channel_names=channel_names,
            chip_combo_text=chip_combo_text,
            selected_chip_config=self.selected_chip_config,
            config_text=config_text,
            vbat_pre_test_text=vbat_pre_test_text,
            power_pre_distribution_text=power_pre_distribution_text,
            parse_config_commands_fn=self._parse_config_commands,
            resolve_device_fn=self._resolve_device,
            channel_force_configs=self._build_channel_force_configs(),
            force_config_enabled=(test_mode == "standard"),
            test_mode=test_mode,
            control_method=control_method,
            stabilization_delay_sec=stabilization_delay_sec,
            download_pgm_rate=download_pgm_rate,
        )
        self._controller.start_auto_test(worker_kwargs)
        self.auto_test_btn.setStateProgramming()
        self.auto_test_btn._progress_timer.stop()

    def _on_auto_test_error(self, err_msg):
        pass

    def _on_auto_test_finished(self):
        self.is_testing = False
        self.auto_test_btn.setStateComplete()

    def _on_auto_test_thread_cleaned(self):
        self._auto_test_worker = None
        self._auto_test_thread = None

    def _stop_auto_test(self):
        self._controller.stop_auto_test()
        self.is_testing = False
        self.auto_test_btn.setStateFailed()
        self.append_log("[AUTO_TEST] Auto test stopped by user.")

    def _save_datalog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DataLog", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            logger.info("Saving datalog to: %s", file_path)
            self.append_log(f"[SYSTEM] DataLog saved to: {file_path}")

    def _export_bin_results_to_excel(self):
        """把 BIN 结果导出为 .xlsx。

        - 电流列(每个 enabled 通道 + Vbat_remain)统一换算为 µA,
          且单位只写在表头(形如 "Vbat (µA)"),数据单元格里只保留裸数值,
          方便后续在 Excel 里继续计算 / 画图。
        - 非电流列(BIN / Voltage)保持原样(Voltage 仍为 "3.800 | 3.800" 这类
          由 UI 组装好的字符串,与 QTableWidget 一致)。
        - 数据源优先使用 self._bin_results_data(即测试时原始 summary,含浮点数),
          因此不受 UI 单位自动换算格式(mA/µA/nA)的影响。
        """
        table = getattr(self, "bin_result_table", None)
        summaries = list(getattr(self, "_bin_results_data", []) or [])
        if table is None or table.columnCount() == 0 or not summaries:
            QMessageBox.information(
                self, "Nothing to Export",
                "There are no BIN results to export yet.\n"
                "Run an Auto Test first and try again."
            )
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            QMessageBox.critical(
                self, "Export Failed",
                "Python package 'openpyxl' is required to export Excel.\n"
                "Please install it first:\n\n    pip install openpyxl"
            )
            return

        from datetime import datetime
        default_name = f"consumption_bin_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        default_path = os.path.join(os.getcwd(), default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export BIN Results",
            default_path,
            "Excel Files (*.xlsx);;All Files (*)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"

        try:
            # ---- 先根据 enabled 通道配置组装列定义 ----
            # column 元组: (title, kind)
            #   kind = "bin" | "voltage" | "current" | "vbat_remain"
            unit_suffix = " (\u00b5A)"  # µA
            columns = [("BIN", "bin"), ("Voltage", "voltage")]
            enabled_cfgs = [cfg for cfg in self._channel_configs if cfg["enabled"]]
            for cfg in enabled_cfgs:
                columns.append((f"{cfg['name']}{unit_suffix}", "current", cfg))
            has_sub = any(
                not cfg["name"].lower().startswith("vbat") for cfg in enabled_cfgs
            )
            if has_sub:
                columns.append((f"Vbat_remain{unit_suffix}", "vbat_remain"))

            def _to_ua(value):
                """A -> µA;None / 非数值返回空串。"""
                if value is None:
                    return ""
                try:
                    return round(float(value) * 1e6, 3)
                except (TypeError, ValueError):
                    return ""

            def _voltage_text(summary):
                channel_voltages = summary.get("channel_voltages", {}) or {}
                parts = []
                for cfg in enabled_cfgs:
                    device_label, hw_ch = self._parse_channel_key(cfg["channel"])
                    v = channel_voltages.get((device_label, hw_ch))
                    parts.append(f"{v:.4g}" if v is not None else "N/A")
                return " | ".join(parts) if parts else "- - -"

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "BIN Results"

            header_font = Font(bold=True, color="FFFFFF", size=11)
            header_fill = PatternFill("solid", fgColor="1F3864")
            header_align = Alignment(horizontal="center", vertical="center")
            cell_align = Alignment(horizontal="center", vertical="center")
            thin_side = Side(style="thin", color="B4C7E7")
            thin_border = Border(
                left=thin_side, right=thin_side,
                top=thin_side, bottom=thin_side,
            )
            row_fill_even = PatternFill("solid", fgColor="F2F6FC")

            for col_idx, col_def in enumerate(columns, start=1):
                title = col_def[0]
                cell = ws.cell(row=1, column=col_idx, value=title)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align
                cell.border = thin_border

            # ---- 数据行 ----
            for r, summary in enumerate(summaries):
                excel_row = r + 2
                bin_name = summary.get("bin_name", f"BIN-{r + 1}")
                channels = summary.get("channels", {}) or {}
                vbat_current = summary.get("vbat")
                vbat_remain = summary.get("vbat_remain")

                for col_idx, col_def in enumerate(columns, start=1):
                    kind = col_def[1]
                    if kind == "bin":
                        value = bin_name
                    elif kind == "voltage":
                        value = _voltage_text(summary)
                    elif kind == "current":
                        cfg = col_def[2]
                        if cfg["name"].lower().startswith("vbat"):
                            value = _to_ua(vbat_current)
                        else:
                            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
                            value = _to_ua(channels.get((device_label, hw_ch)))
                    elif kind == "vbat_remain":
                        value = _to_ua(vbat_remain)
                    else:
                        value = ""

                    cell = ws.cell(row=excel_row, column=col_idx, value=value)
                    cell.alignment = cell_align
                    cell.border = thin_border
                    if isinstance(value, (int, float)):
                        cell.number_format = "0.000"
                    if r % 2 == 1:
                        cell.fill = row_fill_even

            # ---- 列宽自适应 ----
            for col_idx, col_def in enumerate(columns, start=1):
                title = col_def[0]
                max_len = len(str(title))
                for row_cells in ws.iter_rows(
                    min_row=2, max_row=len(summaries) + 1,
                    min_col=col_idx, max_col=col_idx,
                ):
                    for c in row_cells:
                        tl = len(str(c.value)) if c.value is not None else 0
                        if tl > max_len:
                            max_len = tl
                ws.column_dimensions[get_column_letter(col_idx)].width = min(
                    max(max_len + 4, 10), 40
                )
            ws.row_dimensions[1].height = 22
            ws.freeze_panes = "A2"

            wb.save(file_path)
            self.append_log(f"[EXPORT] BIN results exported to: {file_path}")
            QMessageBox.information(
                self, "Export Succeeded",
                f"BIN results have been exported to:\n{file_path}"
            )
        except Exception as e:
            logger.exception("Export BIN results failed")
            self.append_log(f"[ERROR] Export BIN results failed: {e}")
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export BIN results:\n{e}"
            )

    @staticmethod
    def _format_current(current_A):
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.3f} A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.3f} mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.3f} µA"
        elif abs_i >= 1e-9:
            return f"{current_A*1e9:.3f} nA"
        else:
            return f"{current_A:.3e} A"

    def update_channel_current(self, channel_idx, avg_current):
        if channel_idx in self.channel_cards:
            label = self.channel_cards[channel_idx]["value_label"]
            if avg_current is not None:
                label.setText(self._format_current(avg_current))
            else:
                label.setText("- - -")

    def get_selected_channels(self):
        return [
            cfg["channel"] for cfg in self._channel_configs if cfg["enabled"]
        ]

    def get_test_config(self):
        """读取当前页配置快照（同时供 AI ai_get_config 复用，键名与
        apply_config_to_controls 对齐）。

        AI 可修改的字段（与 apply_config_to_controls 对齐，禁臆造键名）：
          - chip_name                  : str        当前所选芯片名（chip_combo 文本）
          - test_mode                  : str        "high_voltage" / "standard"
          - test_time_s                : float      Test Time (s)
          - stable_delay_s             : float      Stable Delay (s)
          - download_baudrate          : int        固件下载波特率
          - download_mode              : str        "flash" / "ramrun"
          - control_method             : str        "N6705C" / "MCU"
          - mcu_type                   : str        "ch9114f" / "yd_rp2040"
          - poweron_channel            : str        PowerON 通道键（如 "B-CH1" / "GPIO0"）
          - poweron_polarity           : str        "rising" / "falling"
          - reset_enabled              : bool       是否启用 RESET
          - reset_channel              : str        RESET 通道键（reset_enabled=False 时为 ""）
          - reset_polarity             : str        "rising" / "falling"
          - firmware_paths             : list[str]  已选固件路径列表
          - channel_configs            : list[dict] 每通道 {name, channel, enabled,
                                                   force_mode, force_value, boost_mode, boost_value}
        只读字段（仅供 AI 观察状态，apply_config_to_controls 不接受）：
          - n6705c_a/b_connected       : bool
          - mcu_connected              : bool
          - serial_port                : str
          - selected_chip_config       : dict | None  当前芯片完整配置（含 power_distribution）
        """
        try:
            test_time = float(self.test_time_input.text())
        except (ValueError, AttributeError):
            test_time = None
        try:
            stable_delay = float(self.stable_delay_input.text())
        except (ValueError, AttributeError):
            stable_delay = None
        try:
            baudrate = int(self.download_baudrate_input.text())
        except (ValueError, AttributeError):
            baudrate = None

        download_mode = (
            self.download_mode_toggle.value().lower()
            if getattr(self, "download_mode_toggle", None) is not None else "ramrun"
        )
        control_method = (
            self.control_method_toggle.value()
            if getattr(self, "control_method_toggle", None) is not None else "N6705C"
        )
        mcu_type = self._current_mcu_type()

        poweron_channel = (
            self.poweron_channel_combo.currentText()
            if getattr(self, "poweron_channel_combo", None) is not None else ""
        )
        poweron_polarity = (
            self.poweron_polarity_toggle.value()
            if getattr(self, "poweron_polarity_toggle", None) is not None else "rising"
        )
        reset_enabled = bool(
            self.reset_enable_cb.isChecked()
            if getattr(self, "reset_enable_cb", None) is not None else False
        )
        reset_channel = (
            self.reset_channel_combo.currentText()
            if getattr(self, "reset_channel_combo", None) is not None and reset_enabled else ""
        )
        reset_polarity = (
            self.reset_polarity_toggle.value()
            if getattr(self, "reset_polarity_toggle", None) is not None and reset_enabled else "rising"
        )

        # 深拷贝 channel_configs，避免外部修改回写本页状态
        chan_snapshot = [
            {
                "name": cfg.get("name", ""),
                "channel": cfg.get("channel", ""),
                "enabled": bool(cfg.get("enabled", False)),
                "force_mode": cfg.get("force_mode", "auto"),
                "force_value": cfg.get("force_value", ""),
                "boost_mode": cfg.get("boost_mode", "constant"),
                "boost_value": cfg.get("boost_value", ""),
            }
            for cfg in self._channel_configs
        ]

        chip_name = ""
        if getattr(self, "chip_combo", None) is not None and self.chip_combo.currentIndex() > 0:
            chip_name = self.chip_combo.currentText()

        return {
            # 只读状态
            'n6705c_a_connected': self.is_connected_a,
            'n6705c_b_connected': self.is_connected_b,
            'mcu_connected': bool(self.is_mcu_connected),
            'serial_port': self.get_selected_serial_port(),
            'selected_chip_config': self.selected_chip_config,
            'is_testing': bool(self.is_testing),
            # AI 可写键
            'chip_name': chip_name,
            'test_mode': getattr(self, "_test_mode", "high_voltage"),
            'test_time_s': test_time,
            'stable_delay_s': stable_delay,
            'download_baudrate': baudrate,
            'download_mode': download_mode,
            'control_method': control_method,
            'mcu_type': mcu_type,
            'poweron_channel': poweron_channel,
            'poweron_polarity': poweron_polarity,
            'reset_enabled': reset_enabled,
            'reset_channel': reset_channel,
            'reset_polarity': reset_polarity,
            'firmware_paths': list(self.firmware_paths or ([self.firmware_path] if self.firmware_path else [])),
            'channel_configs': chan_snapshot,
            # 兼容旧键（保持向后兼容，等同 selected_chip_config）
            'firmware_path': self.firmware_path,
            'config_content': self.config_content,
            'selected_chip': self.selected_chip_config,
            'channel_configs_legacy': [c["channel"] for c in chan_snapshot if c["enabled"]],
        }
