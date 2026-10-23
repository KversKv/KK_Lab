#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test MCU 相关后台 Worker（QObject，仅 QtCore）。

从 ui/pages/consumption_test/consumption_test.py 平移而来，行为零变更：
  - _SearchMcuPortWorker : MCU 端口扫描（CH9114F / YD-RP2040）
  - _ConnectMcuWorker    : 本地 MCU 连接 + GPIO 高阻初始化
  - _McuPinsHighZWorker  : 共享会话连接后批量置高阻输入
  - _IoStateSetWorker    : PwrON/RESET IO 手动快捷设置（MCU GPIO / N6705C PS2Q）
"""

from PySide6.QtCore import QObject, Signal

from log_config import get_logger


logger = get_logger(__name__)


class _SearchMcuPortWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, mcu_type="yd_rp2040"):
        super().__init__()
        self._mcu_type = mcu_type

    def run(self):
        try:
            if self._mcu_type == "ch9114f":
                from instruments.MCU_IO.ch9114f import (
                    list_ch9114f_ports, CH9114_USB_VID, CH9114_USB_PID,
                )
                import serial.tools.list_ports
                ports = list_ch9114f_ports() or []
                # 构建 device -> description 映射，补全下拉显示的完整端口名
                desc_map = {}
                for info in serial.tools.list_ports.comports():
                    if info.vid == CH9114_USB_VID and info.pid == CH9114_USB_PID:
                        desc_map[info.device] = info.description or info.device
                labels = [f"{p} - {desc_map.get(p, p)}" for p in ports]
                self.finished.emit(labels)
            else:
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                self.finished.emit([f"{p.device} - {p.description}" for p in ports])
        except Exception as e:
            logger.error("MCU port scan failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _ConnectMcuWorker(QObject):
    finished = Signal(object, str)
    gpio_init_done = Signal(list)
    error = Signal(str)

    def __init__(self, port, mcu_type="yd_rp2040", baudrate=921600, hiz_pins=None):
        super().__init__()
        self._port = port
        self._mcu_type = mcu_type
        self._baudrate = baudrate
        self._hiz_pins = list(hiz_pins) if hiz_pins else []

    def run(self):
        try:
            from instruments.factory import create_mcu_io
            if self._mcu_type == "ch9114f":
                inst = create_mcu_io("ch9114f", port=self._port)
            else:
                inst = create_mcu_io("yd_rp2040", port=self._port, baudrate=self._baudrate)
            ok = inst.connect()
            if not ok:
                self.error.emit(f"Failed to connect {self._port}")
                return
            self.gpio_init_done.emit(self._init_pins_high_z(inst))
            self.finished.emit(inst, inst.identify())
        except Exception as e:
            logger.error("MCU IO connection failed: %s", e, exc_info=True)
            self.error.emit(str(e))

    def _init_pins_high_z(self, inst):
        """Set all available GPIO pins to high-impedance input; returns failed pins."""
        failed = []
        for pin in self._hiz_pins:
            try:
                inst.in_pull(pin, "none")
            except Exception as e:  # noqa: BLE001
                failed.append(pin)
                logger.warning("MCU GPIO%d high-Z init failed: %s", pin, e)
        return failed


class _McuPinsHighZWorker(QObject):
    """共享会话连接后把所有可用 GPIO 引脚置高阻输入的后台 Worker。"""

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, inst, pins):
        super().__init__()
        self._inst = inst
        self._pins = list(pins)

    def run(self):
        try:
            failed = []
            for pin in self._pins:
                try:
                    self._inst.in_pull(pin, "none")
                except Exception as e:  # noqa: BLE001
                    failed.append(pin)
                    logger.warning("MCU GPIO%d high-Z init failed: %s", pin, e)
            self.finished.emit(failed)
        except Exception as e:
            logger.error("MCU GPIO high-Z failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _IoStateSetWorker(QObject):
    """手动设置 PwrON/RESET IO 状态的后台 Worker（"⋯" 快捷设置菜单）。

    MCU 通道 (GPIOx): 输出高/低电平, 或切高阻输入;
    N6705C 通道 (A/B-CHx): PS2Q 模式输出 2.3V/0.1V (限流 0.2A),
    高阻则先设 Output-Off-Mode=HIGHZ 再关闭通道, 与 Auto Test
    中 POWERON/RESET 脉冲使用的电平/时序保持一致。
    """

    finished = Signal(str, str)  # label, state
    error = Signal(str)

    def __init__(self, inst, label, hw_ch, is_mcu, state):
        super().__init__()
        self._inst = inst
        self._label = label
        self._hw_ch = hw_ch
        self._is_mcu = is_mcu
        self._state = state

    def run(self):
        try:
            if self._is_mcu:
                if self._state == "High":
                    self._inst.out(self._hw_ch, 1)
                elif self._state == "Low":
                    self._inst.out(self._hw_ch, 0)
                else:
                    self._inst.in_pull(self._hw_ch, "none")
            elif self._state == "HighZ":
                self._inst.set_mode(self._hw_ch, "PS2Q")
                try:
                    self._inst.set_output_off_mode(self._hw_ch, "HIGHZ")
                except AttributeError:
                    pass
                self._inst.channel_off(self._hw_ch)
            else:
                voltage = 2.3 if self._state == "High" else 0.1
                self._inst.set_mode(self._hw_ch, "PS2Q")
                self._inst.set_voltage(self._hw_ch, voltage)
                self._inst.set_current_limit(self._hw_ch, 0.2)
                self._inst.channel_on(self._hw_ch)
            self.finished.emit(self._label, self._state)
        except Exception as e:
            logger.error("IO state set failed: %s", e, exc_info=True)
            self.error.emit(str(e))
