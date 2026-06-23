# -*- coding: utf-8 -*-
"""
OSCP 测试 Worker（仅依赖 PySide6.QtCore，不依赖 QtWidgets）。

从 ui/pages/pmu_test/pmu_oscp_ui.py 的 OSCPMonitorWorker / OSCPTestWorker 平移而来，
算法/解析委托 core.pmu_test.oscp.oscp_analysis，行为零变更。
"""

import time

from PySide6.QtCore import QObject, Signal

from log_config import get_logger
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockI2C
from lib.i2c.i2c_interface_x64 import I2CInterface
from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag

from .oscp_analysis import (
    get_changed_bits,
    format_changed_bits,
    generate_sweep_points,
    generate_voltage_points,
)

logger = get_logger(__name__)


class OSCPMonitorWorker(QObject):
    status_update = Signal(str, bool)
    result_update = Signal(str, float)
    result_detail_update = Signal(dict)
    progress_update = Signal(int)
    test_finished = Signal(bool)

    def __init__(self, test_type, n6705c, config):
        super().__init__()
        self.test_type = test_type
        self.n6705c = n6705c
        self.config = config
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            success = self._run_monitor_sweep()
            self.test_finished.emit(success)
        except Exception as e:
            logger.error("OSCP Monitor测试失败: %s", e, exc_info=True)
            self.status_update.emit(f"测试失败: {str(e)}", True)
            self.test_finished.emit(False)

    def _run_monitor_sweep(self):
        test_channel = int(self.config.get("test_channel", 2))
        monitor_channel = int(self.config.get("monitor_channel", 1))
        start_val = float(self.config.get("sweep_start", 0.7))
        end_val = float(self.config.get("sweep_end", 1.5))
        step_val = float(self.config.get("sweep_step", 0.1))
        delay_time_ms = float(self.config.get("delay_time_ms", 100.0))

        is_current_type = self.test_type in ["OCP", "SCP"]

        sweep_points = generate_sweep_points(start_val, end_val, step_val, self.test_type)
        if not sweep_points:
            self.status_update.emit("扫描参数无效，请检查Start/End/Step", True)
            return False

        unit = "A" if is_current_type else "V"
        restore_state = self._capture_channel_state(test_channel, start_val)
        self.status_update.emit(f"执行{self.test_type} Monitor测试...", False)

        try:
            initial_val = sweep_points[0]
            if is_current_type:
                self.n6705c.set_current(test_channel, initial_val)
            else:
                self.n6705c.set_voltage(test_channel, initial_val)
            self.n6705c.channel_on(test_channel)
            self._sleep_ms(max(delay_time_ms, 100.0))
            if not self.is_running:
                return False

            if is_current_type:
                initial_monitor = self.n6705c.measure_current(monitor_channel)
            else:
                initial_monitor = self.n6705c.measure_voltage(monitor_channel)
            last_monitor = initial_monitor

            self.status_update.emit(
                f"{self.test_type} Monitor初始值: {initial_monitor:.4f} {unit} @ sweep={initial_val:.3f} {unit}", False
            )
            logger.info(
                "%s Monitor测试: test_ch=%d, monitor_ch=%d, start=%.3f, end=%.3f, step=%.4f, delay=%.1f ms, init_monitor=%.4f",
                self.test_type, test_channel, monitor_channel, start_val, end_val, step_val, delay_time_ms, initial_monitor
            )

            threshold_val = None
            threshold_ratio = 0.2
            total_points = len(sweep_points)

            for idx, sweep_val in enumerate(sweep_points):
                if not self.is_running:
                    self.status_update.emit("测试已停止", True)
                    return False

                self.progress_update.emit(int((idx + 1) / total_points * 100))

                if is_current_type:
                    self.n6705c.set_current(test_channel, sweep_val)
                else:
                    self.n6705c.set_voltage(test_channel, sweep_val)
                self._sleep_ms(delay_time_ms)
                if not self.is_running:
                    self.status_update.emit("测试已停止", True)
                    return False

                if is_current_type:
                    current_monitor = self.n6705c.measure_current(monitor_channel)
                else:
                    current_monitor = self.n6705c.measure_voltage(monitor_channel)

                logger.info(
                    "%s Monitor扫描: sweep=%.4f %s, monitor=%.4f %s, last=%.4f",
                    self.test_type, sweep_val, unit, current_monitor, unit, last_monitor
                )
                self.status_update.emit(
                    f"{self.test_type}扫描 {sweep_val:.3f} {unit}, Monitor={current_monitor:.4f} {unit}", False
                )

                if abs(last_monitor) > 1e-6:
                    change_ratio = abs(current_monitor - last_monitor) / abs(last_monitor)
                else:
                    change_ratio = abs(current_monitor - last_monitor)

                if change_ratio > threshold_ratio and sweep_val != sweep_points[0]:
                    threshold_val = sweep_val
                    logger.info(
                        "%s Monitor阈值触发: sweep=%.4f %s, monitor %.4f -> %.4f %s, ratio=%.2f%%",
                        self.test_type, sweep_val, unit, last_monitor, current_monitor, unit, change_ratio * 100
                    )
                    self.result_update.emit(
                        "保护电流" if is_current_type else "保护电压", threshold_val
                    )
                    self.result_detail_update.emit({
                        "test_type": self.test_type,
                        "method": "monitor",
                        "threshold_value": threshold_val,
                        "monitor_before": last_monitor,
                        "monitor_after": current_monitor,
                        "monitor_channel": monitor_channel,
                        "delay_time_ms": delay_time_ms,
                        "start_value": start_val,
                        "end_value": end_val,
                        "step_value": step_val,
                        "points_count": len(sweep_points),
                        "restore_voltage": restore_state["voltage"],
                    })
                    self.status_update.emit(
                        f"{self.test_type}阈值: {threshold_val:.3f} {unit}, Monitor {last_monitor:.4f} -> {current_monitor:.4f} {unit}", False
                    )
                    break

                last_monitor = current_monitor

            if threshold_val is None:
                self.result_detail_update.emit({
                    "test_type": self.test_type,
                    "method": "monitor",
                    "no_trigger": True,
                    "initial_monitor": initial_monitor,
                    "monitor_channel": monitor_channel,
                    "delay_time_ms": delay_time_ms,
                    "start_value": start_val,
                    "end_value": end_val,
                    "step_value": step_val,
                    "points_count": len(sweep_points),
                    "restore_voltage": restore_state["voltage"],
                })
                self.status_update.emit(f"{self.test_type}测试结束，未检测到突变", True)
                return False
            return True
        finally:
            self._restore_channel_state(test_channel, restore_state)

    def _capture_channel_state(self, channel, fallback_voltage):
        voltage = float(fallback_voltage)
        is_on = True
        try:
            if hasattr(self.n6705c, "measure_voltage"):
                voltage = float(self.n6705c.measure_voltage(channel))
        except Exception as e:
            logger.warning("读取测试前通道电压失败: %s", e)
        try:
            if hasattr(self.n6705c, "get_channel_state"):
                is_on = bool(self.n6705c.get_channel_state(channel))
        except Exception as e:
            logger.warning("读取测试前通道开关状态失败: %s", e)
        return {"voltage": voltage, "is_on": is_on}

    def _restore_channel_state(self, channel, restore_state):
        restore_voltage = float(restore_state.get("voltage", 0.0))
        was_on = bool(restore_state.get("is_on", True))
        try:
            self.n6705c.set_voltage(channel, restore_voltage)
            if was_on:
                self.n6705c.channel_on(channel)
            elif hasattr(self.n6705c, "channel_off"):
                self.n6705c.channel_off(channel)
            self.status_update.emit(f"通道{channel}已恢复到测试前电压 {restore_voltage:.3f} V", False)
        except Exception as e:
            logger.error("恢复N6705C通道%s失败: %s", channel, e, exc_info=True)
            self.status_update.emit(f"通道{channel}恢复失败: {e}", True)

    def _sleep_ms(self, delay_time_ms):
        remaining_ms = max(0, int(delay_time_ms))
        while remaining_ms > 0 and self.is_running:
            chunk_ms = min(remaining_ms, 50)
            time.sleep(chunk_ms / 1000.0)
            remaining_ms -= chunk_ms


class OSCPTestWorker(QObject):
    status_update = Signal(str, bool)
    result_update = Signal(str, float)
    result_detail_update = Signal(dict)
    progress_update = Signal(int)
    test_finished = Signal(bool)

    def __init__(self, test_type, n6705c, config):
        super().__init__()
        self.test_type = test_type
        self.n6705c = n6705c
        self.config = config
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        try:
            success = self._run_voltage_register_sweep()
            self.test_finished.emit(success)
        except Exception as e:
            logger.error("OSCP测试失败: %s", e, exc_info=True)
            self.status_update.emit(f"测试失败: {str(e)}", True)
            self.test_finished.emit(False)

    def _run_voltage_register_sweep(self):
        test_channel = int(self.config.get("test_channel", 2))
        device_addr = int(self.config.get("device_address", 0))
        reg_addr = int(self.config.get("register_address", 0))
        iic_width = int(self.config.get("iic_width", I2CWidthFlag.BIT_10))
        start_voltage = float(self.config.get("sweep_start", 0.7))
        end_voltage = float(self.config.get("sweep_end", 1.5))
        step_voltage = float(self.config.get("sweep_step", 0.1))
        delay_time_ms = float(self.config.get("delay_time_ms", 100.0))

        voltage_points = generate_voltage_points(start_voltage, end_voltage, step_voltage, self.test_type)
        if not voltage_points:
            self.status_update.emit("电压扫描参数无效，请检查Start/End/Step", True)
            return False

        i2c = self._create_i2c()
        restore_state = self._capture_channel_state(test_channel, start_voltage)
        self.status_update.emit(f"执行{self.test_type}测试...", False)

        try:
            initial_voltage = voltage_points[0]
            self.n6705c.set_voltage(test_channel, initial_voltage)
            self.n6705c.channel_on(test_channel)
            self._sleep_ms(max(delay_time_ms, 100.0))
            if not self.is_running:
                return False

            raw_init = i2c.read(device_addr, reg_addr, iic_width)
            last_raw = raw_init
            self.status_update.emit(
                f"{self.test_type}初始寄存器: 0x{raw_init:X} @ {initial_voltage:.3f} V", False
            )
            logger.info(
                "%s测试: device=0x%02X, reg=0x%04X, width=%s, start=%.3f V, end=%.3f V, step=%.4f V, delay=%.1f ms, init=0x%X",
                self.test_type, device_addr, reg_addr, iic_width, start_voltage, end_voltage, step_voltage, delay_time_ms, raw_init
            )

            threshold_voltage = None
            total_points = len(voltage_points)
            for idx, voltage in enumerate(voltage_points):
                if not self.is_running:
                    self.status_update.emit("测试已停止", True)
                    return False

                self.progress_update.emit(int((idx + 1) / total_points * 100))

                self.n6705c.set_voltage(test_channel, voltage)
                self._sleep_ms(delay_time_ms)
                if not self.is_running:
                    self.status_update.emit("测试已停止", True)
                    return False

                raw_now = i2c.read(device_addr, reg_addr, iic_width)
                logger.info(
                    "%s扫描: voltage=%.4f V, reg=0x%X, init=0x%X",
                    self.test_type, voltage, raw_now, raw_init
                )
                self.status_update.emit(
                    f"{self.test_type}扫描 {voltage:.3f} V, REG=0x{raw_now:X}", False
                )

                if raw_now != last_raw:
                    threshold_voltage = voltage
                    changed_bits = get_changed_bits(last_raw, raw_now)
                    logger.info(
                        "%s阈值触发: voltage=%.4f V, reg 0x%X -> 0x%X, bits=%s",
                        self.test_type, voltage, last_raw, raw_now, format_changed_bits(changed_bits)
                    )
                    self.result_update.emit("保护电压", threshold_voltage)
                    self.result_detail_update.emit({
                        "test_type": self.test_type,
                        "threshold_voltage": threshold_voltage,
                        "trigger_reg_before": last_raw,
                        "trigger_reg_after": raw_now,
                        "changed_bits": changed_bits,
                        "initial_reg": raw_init,
                        "device_address": device_addr,
                        "register_address": reg_addr,
                        "iic_width": iic_width,
                        "delay_time_ms": delay_time_ms,
                        "start_voltage": start_voltage,
                        "end_voltage": end_voltage,
                        "step_voltage": step_voltage,
                        "points_count": len(voltage_points),
                        "restore_voltage": restore_state["voltage"],
                    })
                    self.status_update.emit(
                        f"{self.test_type}阈值: {threshold_voltage:.3f} V, REG 0x{last_raw:X} -> 0x{raw_now:X}", False
                    )
                    break

                last_raw = raw_now

            if threshold_voltage is None:
                self.result_detail_update.emit({
                    "test_type": self.test_type,
                    "no_trigger": True,
                    "initial_reg": raw_init,
                    "changed_bits": [],
                    "device_address": device_addr,
                    "register_address": reg_addr,
                    "iic_width": iic_width,
                    "delay_time_ms": delay_time_ms,
                    "start_voltage": start_voltage,
                    "end_voltage": end_voltage,
                    "step_voltage": step_voltage,
                    "points_count": len(voltage_points),
                    "restore_voltage": restore_state["voltage"],
                })
                self.status_update.emit(f"{self.test_type}测试结束，未检测到寄存器变化", True)
                return False
            return True
        finally:
            self._restore_channel_state(test_channel, restore_state)

    def _capture_channel_state(self, channel, fallback_voltage):
        voltage = float(fallback_voltage)
        is_on = True
        try:
            if hasattr(self.n6705c, "measure_voltage"):
                voltage = float(self.n6705c.measure_voltage(channel))
        except Exception as e:
            logger.warning("读取测试前通道电压失败，使用起始电压作为恢复值: %s", e)
        try:
            if hasattr(self.n6705c, "get_channel_state"):
                is_on = bool(self.n6705c.get_channel_state(channel))
        except Exception as e:
            logger.warning("读取测试前通道开关状态失败，默认恢复为ON: %s", e)
        return {"voltage": voltage, "is_on": is_on}

    def _restore_channel_state(self, channel, restore_state):
        restore_voltage = float(restore_state.get("voltage", 0.0))
        was_on = bool(restore_state.get("is_on", True))
        try:
            self.n6705c.set_voltage(channel, restore_voltage)
            if was_on:
                self.n6705c.channel_on(channel)
            elif hasattr(self.n6705c, "channel_off"):
                self.n6705c.channel_off(channel)
            self.status_update.emit(f"通道{channel}已恢复到测试前电压 {restore_voltage:.3f} V", False)
            logger.info("OSCP测试结束恢复通道%s: voltage=%.6f V, output=%s", channel, restore_voltage, "ON" if was_on else "OFF")
        except Exception as e:
            logger.error("恢复N6705C通道%s失败: %s", channel, e, exc_info=True)
            self.status_update.emit(f"通道{channel}恢复失败: {e}", True)

    def _create_i2c(self):
        if DEBUG_MOCK:
            if hasattr(self.n6705c, "_mock_i2c") and self.n6705c._mock_i2c is not None:
                return self.n6705c._mock_i2c
            i2c = MockI2C()
            if hasattr(self.n6705c, "_mock_i2c"):
                self.n6705c._mock_i2c = i2c
            return i2c
        return I2CInterface()

    def _sleep_ms(self, delay_time_ms):
        remaining_ms = max(0, int(delay_time_ms))
        while remaining_ms > 0 and self.is_running:
            chunk_ms = min(remaining_ms, 50)
            time.sleep(chunk_ms / 1000.0)
            remaining_ms -= chunk_ms
