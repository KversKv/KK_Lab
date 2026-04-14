#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "lib", "i2c"))

from ui.widgets.dark_combobox import DarkComboBox
from ui.styles import SCROLLBAR_STYLE
from ui.styles.button import SpinningSearchButton, update_connect_button_state
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGridLayout, QFrame, QDoubleSpinBox, QSpinBox,
    QTextEdit, QProgressBar, QSizePolicy, QScrollArea,
    QApplication
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtGui import QFont
import time
import pyvisa
import serial.tools.list_ports

from instruments.power.keysight.n6705c import N6705C
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C, MockVT6002
from i2c_interface_x64 import I2CInterface
from Bes_I2CIO_Interface import I2CSpeedMode, I2CWidthFlag


STATUS_REGISTER_MAP = {
    "CHG_STAT": {"addr": 0x0B, "bits": "7:5", "desc": "Charge Status"},
    "VBUS_STAT": {"addr": 0x0B, "bits": "4:2", "desc": "VBUS Status"},
    "PG_STAT": {"addr": 0x0B, "bits": "1", "desc": "Power Good Status"},
    "THERM_STAT": {"addr": 0x0B, "bits": "0", "desc": "Thermal Regulation Status"},
    "WATCHDOG_FAULT": {"addr": 0x0C, "bits": "7", "desc": "Watchdog Timer Fault"},
    "BOOST_FAULT": {"addr": 0x0C, "bits": "6", "desc": "Boost Fault"},
    "CHRG_FAULT": {"addr": 0x0C, "bits": "5:4", "desc": "Charge Fault"},
    "BAT_FAULT": {"addr": 0x0C, "bits": "3", "desc": "Battery Fault"},
    "NTC_FAULT": {"addr": 0x0C, "bits": "2:0", "desc": "NTC Fault"},
}


class _SearchSerialWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            ports = serial.tools.list_ports.comports()
            result = [f"{p.device} - {p.description}" for p in ports]
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _StatusPollWorker(QObject):
    log_message = Signal(str)
    status_update = Signal(dict)
    progress = Signal(int)
    test_finished = Signal(bool)
    error = Signal(str)

    def __init__(self, n6705c, config, vt6002=None):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._vt6002 = vt6002
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def _read_reg_value(self, i2c, device_addr, reg_addr, iic_width, bits_str):
        raw = i2c.read(device_addr, reg_addr, iic_width)
        if ":" in bits_str:
            hi, lo = [int(x) for x in bits_str.split(":")]
            mask = ((1 << (hi - lo + 1)) - 1) << lo
            val = (raw & mask) >> lo
        else:
            bit_pos = int(bits_str)
            val = (raw >> bit_pos) & 1
        return raw, val

    def _write_reg_value(self, i2c, device_addr, reg_addr, iic_width, value):
        i2c.write(device_addr, reg_addr, value, iic_width)

    def run(self):
        try:
            device_addr = self._cfg["device_addr"]
            iic_width = self._cfg["iic_width"]
            reg_addr = self._cfg["reg_addr"]
            bits_str = self._cfg["reg_bit"]
            test_item = self._cfg["test_item"]

            i2c = I2CInterface()
            self._i2c = i2c

            raw_init, val_init = self._read_reg_value(i2c, device_addr, reg_addr, iic_width, bits_str)
            self.log_message.emit(
                f"[TEST] Initial register 0x{reg_addr:02X} bits[{bits_str}] = "
                f"0x{val_init:02X} ({val_init})  (raw=0x{raw_init:04X})"
            )
            self.status_update.emit({
                "INIT": {
                    "raw": raw_init, "value": val_init,
                    "desc": "Initial Value", "addr": reg_addr, "bits": bits_str,
                }
            })

            if test_item == "Voltage Sweep":
                self._run_voltage_sweep(i2c, device_addr, reg_addr, iic_width, bits_str, val_init)
            elif test_item == "Current Sweep":
                self._run_current_sweep(i2c, device_addr, reg_addr, iic_width, bits_str, val_init)
            elif test_item == "Temperature Sweep":
                self._run_temperature_sweep(i2c, device_addr, reg_addr, iic_width, bits_str, val_init)
            elif test_item == "Reg Sweep":
                self._run_reg_sweep(i2c, device_addr, reg_addr, iic_width, bits_str, val_init)

        except Exception as e:
            self.log_message.emit(f"[ERROR] {e}")
            self.error.emit(str(e))
            self.test_finished.emit(False)

    def _generate_levels(self, start, end, step):
        if step <= 0:
            return []
        ascending = end >= start
        levels = []
        current_level = start
        if ascending:
            while current_level <= end + step * 0.01:
                levels.append(round(current_level, 6))
                current_level += step
        else:
            while current_level >= end - step * 0.01:
                levels.append(round(current_level, 6))
                current_level -= step
        return levels

    def _sweep_loop(self, i2c, device_addr, reg_addr, iic_width, bits_str, val_init,
                    levels, unit, set_func, step_delay_s):
        total_steps = len(levels)
        if total_steps == 0:
            self.log_message.emit("[ERROR] No sweep steps generated.")
            self.test_finished.emit(False)
            return

        start = levels[0]
        end = levels[-1]
        self.log_message.emit(
            f"[TEST] Sweep: {start} {unit} -> {end} {unit}, "
            f"total {total_steps} steps"
        )

        threshold_value = None

        for idx, level in enumerate(levels):
            if self._stop_flag:
                self.log_message.emit("[TEST] Stopped by user.")
                break

            set_func(level)
            time.sleep(step_delay_s)

            try:
                raw_now, val_now = self._read_reg_value(
                    i2c, device_addr, reg_addr, iic_width, bits_str
                )
            except Exception as e:
                self.log_message.emit(f"[ERROR] Read register failed at {level}{unit}: {e}")
                pct = int((idx + 1) / total_steps * 100)
                self.progress.emit(pct)
                continue

            self.status_update.emit({
                "SWEEP": {
                    "raw": raw_now, "value": val_now,
                    "desc": f"@ {level:.4g} {unit}", "addr": reg_addr, "bits": bits_str,
                }
            })

            self.log_message.emit(
                f"[DATA] {level:.4g} {unit} -> reg=0x{raw_now:04X}, "
                f"bits[{bits_str}]=0x{val_now:02X} ({val_now})"
            )

            if val_now != val_init:
                threshold_value = level
                self.log_message.emit(
                    f"[RESULT] Register flipped at {level:.4g} {unit}! "
                    f"Value changed: 0x{val_init:02X} -> 0x{val_now:02X}"
                )
                self.progress.emit(100)
                break

            pct = int((idx + 1) / total_steps * 100)
            self.progress.emit(pct)

        if threshold_value is not None:
            self.log_message.emit(f"[RESULT] Threshold = {threshold_value:.4g} {unit}")
        elif not self._stop_flag:
            self.log_message.emit(
                f"[WARN] Register did not flip during sweep ({start} {unit} -> {end} {unit})."
            )

        self.test_finished.emit(threshold_value is not None)

    def _run_voltage_sweep(self, i2c, device_addr, reg_addr, iic_width, bits_str, val_init):
        start = self._cfg["start_voltage"]
        end = self._cfg["end_voltage"]
        step = self._cfg["step_voltage"]
        step_delay_s = self._cfg.get("step_delay_ms", 10) / 1000.0
        test_channel = self._cfg["test_channel"]
        levels = self._generate_levels(start, end, step)
        self._n6705c.channel_on(test_channel)
        time.sleep(0.2)

        def set_func(level):
            self._n6705c.set_voltage(test_channel, level)

        self._sweep_loop(i2c, device_addr, reg_addr, iic_width, bits_str, val_init,
                         levels, "V", set_func, step_delay_s)

    def _run_current_sweep(self, i2c, device_addr, reg_addr, iic_width, bits_str, val_init):
        start = self._cfg["start_current"]
        end = self._cfg["end_current"]
        step = self._cfg["step_current"]
        step_delay_s = self._cfg.get("step_delay_ms", 10) / 1000.0
        test_channel = self._cfg["test_channel"]
        levels = self._generate_levels(start, end, step)
        self._n6705c.channel_on(test_channel)
        time.sleep(0.2)

        def set_func(level):
            self._n6705c.set_current(test_channel, level / 1000.0)

        self._sweep_loop(i2c, device_addr, reg_addr, iic_width, bits_str, val_init,
                         levels, "mA", set_func, step_delay_s)

    def _run_temperature_sweep(self, i2c, device_addr, reg_addr, iic_width, bits_str, val_init):
        vt = self._vt6002
        if vt is None:
            self.log_message.emit("[ERROR] VT6002 chamber not connected.")
            self.test_finished.emit(False)
            return
        start = self._cfg["start_temp"]
        end = self._cfg["end_temp"]
        step = self._cfg["step_temp"]
        step_delay_s = self._cfg.get("step_delay_ms", 10) / 1000.0
        levels = self._generate_levels(start, end, step)
        TEMP_TOLERANCE = 1.0
        TEMP_SETTLE_POLL_S = 2.0
        TEMP_SETTLE_TIMEOUT_S = 600
        try:
            vt.start()
            self.log_message.emit("[TEMP-SWEEP] Chamber power ON.")
        except Exception as e:
            self.log_message.emit(f"[TEMP-SWEEP] Chamber start warning: {e}")
        total_steps = len(levels)
        if total_steps == 0:
            self.log_message.emit("[ERROR] No sweep steps generated.")
            self.test_finished.emit(False)
            return
        self.log_message.emit(
            f"[TEST] Temperature Sweep: {start} C -> {end} C, total {total_steps} steps"
        )
        threshold_value = None
        for idx, temp_set in enumerate(levels):
            if self._stop_flag:
                self.log_message.emit("[TEST] Stopped by user.")
                break
            self.log_message.emit(f"[TEMP-SWEEP] Setting chamber to {temp_set:.1f} C ...")
            try:
                vt.set_temperature(temp_set)
            except Exception as e:
                self.log_message.emit(f"[TEMP-SWEEP] Set temp error: {e}")
            settle_start = time.time()
            settled = False
            while not settled:
                if self._stop_flag:
                    break
                try:
                    actual = vt.get_current_temp()
                except Exception:
                    actual = None
                if actual is not None and abs(actual - temp_set) <= TEMP_TOLERANCE:
                    self.log_message.emit(
                        f"[TEMP-SWEEP] Chamber stable at {actual:.1f} C (target {temp_set:.1f} C)."
                    )
                    settled = True
                else:
                    elapsed_settle = time.time() - settle_start
                    if elapsed_settle > TEMP_SETTLE_TIMEOUT_S:
                        self.log_message.emit(
                            f"[TEMP-SWEEP] Timeout waiting for {temp_set:.1f} C "
                            f"(current: {actual} C). Measuring anyway."
                        )
                        settled = True
                    else:
                        actual_str = f"{actual:.1f}" if actual is not None else "N/A"
                        self.log_message.emit(
                            f"[TEMP-SWEEP] Waiting... current={actual_str} C, "
                            f"target={temp_set:.1f} C, elapsed={elapsed_settle:.0f}s"
                        )
                        time.sleep(TEMP_SETTLE_POLL_S)
            if self._stop_flag:
                break
            time.sleep(step_delay_s)
            try:
                raw_now, val_now = self._read_reg_value(i2c, device_addr, reg_addr, iic_width, bits_str)
            except Exception as e:
                self.log_message.emit(f"[ERROR] Read register failed at {temp_set:.1f} C: {e}")
                self.progress.emit(int((idx + 1) / total_steps * 100))
                continue
            self.status_update.emit({
                "SWEEP": {"raw": raw_now, "value": val_now, "desc": f"@ {temp_set:.1f} C", "addr": reg_addr, "bits": bits_str}
            })
            self.log_message.emit(
                f"[DATA] {temp_set:.1f} C -> reg=0x{raw_now:04X}, bits[{bits_str}]=0x{val_now:02X} ({val_now})"
            )
            if val_now != val_init:
                threshold_value = temp_set
                self.log_message.emit(
                    f"[RESULT] Register flipped at {temp_set:.1f} C! "
                    f"Value changed: 0x{val_init:02X} -> 0x{val_now:02X}"
                )
                self.progress.emit(100)
                break
            self.progress.emit(int((idx + 1) / total_steps * 100))
        if threshold_value is not None:
            self.log_message.emit(f"[RESULT] Threshold Temperature = {threshold_value:.1f} C")
        elif not self._stop_flag:
            self.log_message.emit(f"[WARN] Register did not flip during temperature sweep ({start} C -> {end} C).")
        self.test_finished.emit(threshold_value is not None)

    def _run_reg_sweep(self, i2c, device_addr, reg_addr, iic_width, bits_str, val_init):
        write_reg_addr = self._cfg["write_reg_addr"]
        start_val = int(self._cfg["reg_start_value"])
        end_val = int(self._cfg["reg_end_value"])
        step_val = int(self._cfg["reg_step_value"])
        step_delay_s = self._cfg.get("step_delay_ms", 10) / 1000.0
        if step_val <= 0:
            self.log_message.emit("[ERROR] Reg step must be > 0.")
            self.test_finished.emit(False)
            return
        ascending = end_val >= start_val
        levels = []
        current_val = start_val
        if ascending:
            while current_val <= end_val:
                levels.append(current_val)
                current_val += step_val
        else:
            while current_val >= end_val:
                levels.append(current_val)
                current_val -= step_val
        total_steps = len(levels)
        if total_steps == 0:
            self.log_message.emit("[ERROR] No reg sweep steps generated.")
            self.test_finished.emit(False)
            return
        self.log_message.emit(
            f"[TEST] Reg Sweep: write 0x{write_reg_addr:02X}, value {start_val} -> {end_val}, "
            f"step={step_val}, total {total_steps} steps"
        )
        threshold_value = None
        for idx, reg_val in enumerate(levels):
            if self._stop_flag:
                self.log_message.emit("[TEST] Stopped by user.")
                break
            try:
                self._write_reg_value(i2c, device_addr, write_reg_addr, iic_width, reg_val)
            except Exception as e:
                self.log_message.emit(f"[ERROR] Write reg failed at value={reg_val}: {e}")
                self.progress.emit(int((idx + 1) / total_steps * 100))
                continue
            time.sleep(step_delay_s)
            try:
                raw_now, val_now = self._read_reg_value(i2c, device_addr, reg_addr, iic_width, bits_str)
            except Exception as e:
                self.log_message.emit(f"[ERROR] Read register failed at value={reg_val}: {e}")
                self.progress.emit(int((idx + 1) / total_steps * 100))
                continue
            self.status_update.emit({
                "SWEEP": {"raw": raw_now, "value": val_now, "desc": f"@ reg_val={reg_val}", "addr": reg_addr, "bits": bits_str}
            })
            self.log_message.emit(
                f"[DATA] reg_val={reg_val} (0x{reg_val:02X}) -> reg=0x{raw_now:04X}, "
                f"bits[{bits_str}]=0x{val_now:02X} ({val_now})"
            )
            if val_now != val_init:
                threshold_value = reg_val
                self.log_message.emit(
                    f"[RESULT] Register flipped at reg_val={reg_val} (0x{reg_val:02X})! "
                    f"Value changed: 0x{val_init:02X} -> 0x{val_now:02X}"
                )
                self.progress.emit(100)
                break
            self.progress.emit(int((idx + 1) / total_steps * 100))
        if threshold_value is not None:
            self.log_message.emit(f"[RESULT] Threshold Reg Value = {threshold_value} (0x{threshold_value:02X})")
        elif not self._stop_flag:
            self.log_message.emit(f"[WARN] Register did not flip during reg sweep ({start_val} -> {end_val}).")
        self.test_finished.emit(threshold_value is not None)


class CardFrame(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(12)
        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.main_layout.addWidget(self.title_label)
        else:
            self.title_label = None



class StatusRegisterTestUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None, vt6002_chamber_ui=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._vt6002_chamber_ui = vt6002_chamber_ui
        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []
        self.vt6002 = None
        self.is_vt6002_connected = False
        self._vt6002_syncing = False
        self._vt6002_search_thread = None
        self._vt6002_search_worker = None
        self.is_test_running = False
        self.test_thread = None
        self.test_worker = None
        self.status_labels = {}
        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._search_devices)
        self.search_timer.setSingleShot(True)
        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()
        self._sync_from_top()

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)
        self.setStyleSheet("""
            QWidget { background-color: #020817; color: #dbe7ff; }
            QWidget#leftPanelInner { background-color: transparent; }
            QLabel { background-color: transparent; color: #dbe7ff; border: none; }
            QLabel#pageTitle { font-size: 18px; font-weight: 700; color: #f8fbff; background-color: transparent; }
            QLabel#pageSubtitle { font-size: 12px; color: #7da2d6; background-color: transparent; }
            QFrame#panelFrame { background-color: #08132d; border: 1px solid #16274d; border-radius: 18px; }
            QFrame#cardFrame { background-color: #071127; border: 1px solid #1a2b52; border-radius: 14px; }
            QLabel#cardTitle { font-size: 11px; font-weight: 700; color: #f4f7ff; letter-spacing: 0.5px; background-color: transparent; }
            QLabel#sectionTitle { font-size: 12px; font-weight: 700; color: #f4f7ff; background-color: transparent; }
            QLabel#fieldLabel { color: #8eb0e3; font-size: 11px; background-color: transparent; }
            QLabel#statusOk { color: #15d1a3; font-weight: 600; background-color: transparent; }
            QLabel#statusWarn { color: #ffb84d; font-weight: 600; background-color: transparent; }
            QLabel#statusErr { color: #ff5e7a; font-weight: 600; background-color: transparent; }
            QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QTextEdit { background-color: #0a1733; color: #eaf2ff; border: 1px solid #27406f; border-radius: 8px; padding: 6px 10px; selection-background-color: #4f46e5; }
            QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 0px; height: 0px; border: none; }
            QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus, QTextEdit:focus { border: 1px solid #4cc9f0; }
            QComboBox { padding-right: 24px; }
            QComboBox::drop-down { border: none; width: 22px; background: transparent; }
            QComboBox QAbstractItemView { background-color: #0a1733; color: #eaf2ff; border: 1px solid #27406f; selection-background-color: #334a7d; }
            QPushButton { min-height: 34px; border-radius: 9px; padding: 6px 14px; border: 1px solid #2a4272; background-color: #102042; color: #dfeaff; font-weight: 600; }
            QPushButton:hover { background-color: #162a56; border: 1px solid #3c5fa1; }
            QPushButton:pressed { background-color: #0d1a37; }
            QPushButton:disabled { background-color: #0b1430; color: #5c7096; border: 1px solid #1a2850; }
            QPushButton#primaryStartBtn { min-height: 36px; border-radius: 12px; font-size: 15px; font-weight: 800; color: white; border: 1px solid #645bff; background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5b5cf6, stop:1 #6a38ff); }
            QPushButton#primaryStartBtn:hover { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6b6cff, stop:1 #7d4cff); }
            QPushButton#stopBtn { background-color: #4a1020; border: 1px solid #d9485f; color: #ffd5db; }
            QPushButton#stopBtn:hover { background-color: #5a1326; }
            QPushButton#smallActionBtn { min-height: 28px; padding: 4px 10px; border-radius: 8px; background-color: #13254b; color: #dce7ff; }
            QFrame#chartContainer, QFrame#logContainer { background-color: #09142e; border: 1px solid #1a2d57; border-radius: 16px; }
            QTextEdit#logEdit { background-color: #061022; border: 1px solid #1f315d; border-radius: 8px; color: #7cecc8; font-family: Consolas, "Courier New", monospace; font-size: 11px; }
            QProgressBar { background-color: #152749; border: none; border-radius: 4px; text-align: center; color: #b7c8ea; min-height: 8px; max-height: 8px; }
            QProgressBar::chunk { background-color: #5b5cf6; border-radius: 4px; }
            QLabel#regName { color: #dbe7ff; font-size: 12px; font-weight: 600; background-color: transparent; }
            QLabel#regValue { color: #ffffff; font-size: 13px; font-weight: 700; background-color: transparent; }
            QLabel#regDesc { color: #7da2d6; font-size: 10px; background-color: transparent; }
            QFrame#regCard { background-color: #0a1733; border: 1px solid #1b315f; border-radius: 10px; }
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        self.page_title = QLabel("\U0001f4cb Status Register Test")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("Monitor and poll Charger IC status registers in real-time.")
        self.page_subtitle.setObjectName("pageSubtitle")
        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_subtitle)
        root_layout.addLayout(header_layout)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        root_layout.addLayout(content_layout, 1)

        left_wrapper = QVBoxLayout()
        left_wrapper.setContentsMargins(0, 0, 0, 0)
        left_wrapper.setSpacing(8)
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.left_scroll.setFixedWidth(275)
        self.left_scroll.setObjectName("leftScrollArea")
        self.left_scroll.setStyleSheet("""
            QScrollArea#leftScrollArea { background-color: #08132d; border: 1px solid #16274d; border-radius: 18px; }
        """ + SCROLLBAR_STYLE)
        self.left_panel = QWidget()
        self.left_panel.setObjectName("leftPanelInner")
        self.left_panel.setMinimumWidth(253)
        self.left_panel.setMaximumWidth(253)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(16)

        self.test_item_card = CardFrame("\u25c9 TEST ITEM")
        self._build_test_item_card()
        left_layout.addWidget(self.test_item_card)
        self.connection_card = CardFrame("\u26a1 N6705C CONNECTION")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)
        self.vt6002_card = CardFrame("\U0001f321 VT6002 CHAMBER")
        self._build_vt6002_card()
        left_layout.addWidget(self.vt6002_card)
        self.test_config_card = CardFrame("\u2637 TEST CONFIG")
        self._build_test_config_card()
        left_layout.addWidget(self.test_config_card)
        self.register_config_card = CardFrame("\u2194 REGISTER CONFIG")
        self._build_register_config_card()
        left_layout.addWidget(self.register_config_card)
        left_layout.addStretch()
        self.left_scroll.setWidget(self.left_panel)
        left_wrapper.addWidget(self.left_scroll, 1)

        self.start_test_btn = QPushButton("\u25b6 START POLL")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_wrapper.addWidget(self.start_test_btn)
        self.stop_test_btn = QPushButton("\u25a0 STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()
        content_layout.addLayout(left_wrapper)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)
        reg_frame = QFrame()
        reg_frame.setObjectName("chartContainer")
        reg_outer = QVBoxLayout(reg_frame)
        reg_outer.setContentsMargins(16, 16, 16, 16)
        reg_outer.setSpacing(10)
        reg_header = QHBoxLayout()
        reg_title = QLabel("\U0001f4ca Register Status")
        reg_title.setObjectName("sectionTitle")
        reg_header.addWidget(reg_title)
        reg_header.addStretch()
        reg_outer.addLayout(reg_header)
        reg_grid = QGridLayout()
        reg_grid.setHorizontalSpacing(12)
        reg_grid.setVerticalSpacing(12)
        col = 0
        row = 0
        for name, info in STATUS_REGISTER_MAP.items():
            card = self._create_reg_card(name, info)
            reg_grid.addWidget(card["frame"], row, col)
            self.status_labels[name] = card
            col += 1
            if col >= 3:
                col = 0
                row += 1
        reg_outer.addLayout(reg_grid)
        reg_outer.addStretch()
        right_layout.addWidget(reg_frame, 4)

        self.log_frame = QFrame()
        self.log_frame.setObjectName("logContainer")
        log_layout = QVBoxLayout(self.log_frame)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(10)
        log_header = QHBoxLayout()
        self.log_title = QLabel("\u2299 Execution Logs")
        self.log_title.setObjectName("sectionTitle")
        log_header.addWidget(self.log_title)
        log_header.addStretch()
        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("smallActionBtn")
        log_header.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_header)
        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)
        log_layout.addWidget(self.log_edit)
        right_layout.addWidget(self.log_frame, 1)

    def _build_test_item_card(self):
        layout = self.test_item_card.main_layout
        self.test_item_combo = DarkComboBox()
        self.test_item_combo.addItems(["Voltage Sweep", "Current Sweep", "Temperature Sweep", "Reg Sweep"])
        layout.addWidget(self.test_item_combo)

    def _on_test_item_changed(self):
        item = self.test_item_combo.currentText()
        is_voltage = (item == "Voltage Sweep")
        is_current = (item == "Current Sweep")
        is_temp = (item == "Temperature Sweep")
        is_reg = (item == "Reg Sweep")
        if hasattr(self, 'vt6002_card'):
            self.vt6002_card.setVisible(is_temp)
        if hasattr(self, 'voltage_param_widget'):
            self.voltage_param_widget.setVisible(is_voltage)
        if hasattr(self, 'current_param_widget'):
            self.current_param_widget.setVisible(is_current)
        if hasattr(self, 'temp_param_widget'):
            self.temp_param_widget.setVisible(is_temp)
        if hasattr(self, 'reg_param_widget'):
            self.reg_param_widget.setVisible(is_reg)
        if hasattr(self, 'test_channel_label'):
            needs_channel = is_voltage or is_current
            self.test_channel_label.setVisible(needs_channel)
            self.test_channel_combo.setVisible(needs_channel)

    def _build_connection_card(self):
        layout = self.connection_card.main_layout
        self.system_status_label = QLabel("\u25cf Ready")
        self.system_status_label.setObjectName("statusOk")
        layout.addWidget(self.system_status_label)
        self.instrument_info_label = QLabel("USB0::0x0957::0x0F07::MY53004321")
        self.instrument_info_label.setObjectName("fieldLabel")
        self.instrument_info_label.setWordWrap(True)
        layout.addWidget(self.instrument_info_label)
        self.visa_resource_combo = DarkComboBox()
        self.visa_resource_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
        layout.addWidget(self.visa_resource_combo)
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self.search_btn = SpinningSearchButton()
        search_row.addWidget(self.search_btn)
        layout.addLayout(search_row)
        self.connect_btn = QPushButton()
        update_connect_button_state(self.connect_btn, connected=False)
        layout.addWidget(self.connect_btn)

    def _build_vt6002_card(self):
        layout = self.vt6002_card.main_layout
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.vt6002_indicator = QLabel("\u25cb")
        self.vt6002_indicator.setFixedWidth(14)
        self.vt6002_indicator.setStyleSheet("color: #ff5a7a; font-size: 14px; background: transparent;")
        self.vt6002_status_label = QLabel("Not Connected")
        self.vt6002_status_label.setStyleSheet("color: #ff5a7a; font-weight: 600; font-size: 11px;")
        status_row.addWidget(self.vt6002_indicator)
        status_row.addWidget(self.vt6002_status_label, 1)
        layout.addLayout(status_row)
        select_row = QHBoxLayout()
        select_row.setSpacing(6)
        self.vt6002_combo = DarkComboBox()
        self.vt6002_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.vt6002_search_btn = SpinningSearchButton()
        self.vt6002_search_btn.setFixedWidth(36)
        select_row.addWidget(self.vt6002_combo, 1)
        select_row.addWidget(self.vt6002_search_btn)
        layout.addLayout(select_row)
        btn_row = QHBoxLayout()
        self.vt6002_connect_btn = QPushButton("Connect")
        update_connect_button_state(self.vt6002_connect_btn, connected=False)
        btn_row.addWidget(self.vt6002_connect_btn)
        layout.addLayout(btn_row)

    def _build_test_config_card(self):
        layout = self.test_config_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self.test_channel_label = QLabel("Test Channel")
        self.test_channel_label.setObjectName("fieldLabel")
        self.test_channel_combo = DarkComboBox()
        self.test_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        grid.addWidget(self.test_channel_label, 0, 0)
        grid.addWidget(self.test_channel_combo, 0, 1)
        layout.addLayout(grid)

        self.voltage_param_widget = QWidget()
        self.voltage_param_widget.setStyleSheet("background: transparent;")
        v_grid = QGridLayout(self.voltage_param_widget)
        v_grid.setContentsMargins(0, 0, 0, 0)
        v_grid.setHorizontalSpacing(10)
        v_grid.setVerticalSpacing(10)
        lbl_start_v = QLabel("Start Voltage (V)")
        lbl_start_v.setObjectName("fieldLabel")
        self.start_voltage_spin = QDoubleSpinBox()
        self.start_voltage_spin.setRange(0.0, 20.0)
        self.start_voltage_spin.setValue(3.0)
        self.start_voltage_spin.setSingleStep(0.1)
        self.start_voltage_spin.setDecimals(2)
        lbl_end_v = QLabel("End Voltage (V)")
        lbl_end_v.setObjectName("fieldLabel")
        self.end_voltage_spin = QDoubleSpinBox()
        self.end_voltage_spin.setRange(0.0, 20.0)
        self.end_voltage_spin.setValue(5.0)
        self.end_voltage_spin.setSingleStep(0.1)
        self.end_voltage_spin.setDecimals(2)
        lbl_step_v = QLabel("Step Voltage (V)")
        lbl_step_v.setObjectName("fieldLabel")
        self.step_voltage_spin = QDoubleSpinBox()
        self.step_voltage_spin.setRange(0.001, 10.0)
        self.step_voltage_spin.setValue(0.1)
        self.step_voltage_spin.setSingleStep(0.01)
        self.step_voltage_spin.setDecimals(3)
        lbl_delay_v = QLabel("Step Delay (ms)")
        lbl_delay_v.setObjectName("fieldLabel")
        self.step_delay_v_spin = QSpinBox()
        self.step_delay_v_spin.setRange(1, 60000)
        self.step_delay_v_spin.setValue(10)
        self.step_delay_v_spin.setSingleStep(10)
        v_grid.addWidget(lbl_start_v, 0, 0)
        v_grid.addWidget(self.start_voltage_spin, 0, 1)
        v_grid.addWidget(lbl_end_v, 1, 0)
        v_grid.addWidget(self.end_voltage_spin, 1, 1)
        v_grid.addWidget(lbl_step_v, 2, 0)
        v_grid.addWidget(self.step_voltage_spin, 2, 1)
        v_grid.addWidget(lbl_delay_v, 3, 0)
        v_grid.addWidget(self.step_delay_v_spin, 3, 1)
        layout.addWidget(self.voltage_param_widget)

        self.current_param_widget = QWidget()
        self.current_param_widget.setStyleSheet("background: transparent;")
        c_grid = QGridLayout(self.current_param_widget)
        c_grid.setContentsMargins(0, 0, 0, 0)
        c_grid.setHorizontalSpacing(10)
        c_grid.setVerticalSpacing(10)
        lbl_start_c = QLabel("Start Current (mA)")
        lbl_start_c.setObjectName("fieldLabel")
        self.start_current_spin = QDoubleSpinBox()
        self.start_current_spin.setRange(0.0, 10000.0)
        self.start_current_spin.setValue(100.0)
        self.start_current_spin.setSingleStep(10.0)
        self.start_current_spin.setDecimals(1)
        lbl_end_c = QLabel("End Current (mA)")
        lbl_end_c.setObjectName("fieldLabel")
        self.end_current_spin = QDoubleSpinBox()
        self.end_current_spin.setRange(0.0, 10000.0)
        self.end_current_spin.setValue(1000.0)
        self.end_current_spin.setSingleStep(10.0)
        self.end_current_spin.setDecimals(1)
        lbl_step_c = QLabel("Step Current (mA)")
        lbl_step_c.setObjectName("fieldLabel")
        self.step_current_spin = QDoubleSpinBox()
        self.step_current_spin.setRange(0.1, 5000.0)
        self.step_current_spin.setValue(50.0)
        self.step_current_spin.setSingleStep(1.0)
        self.step_current_spin.setDecimals(1)
        lbl_delay_c = QLabel("Step Delay (ms)")
        lbl_delay_c.setObjectName("fieldLabel")
        self.step_delay_c_spin = QSpinBox()
        self.step_delay_c_spin.setRange(1, 60000)
        self.step_delay_c_spin.setValue(10)
        self.step_delay_c_spin.setSingleStep(10)
        c_grid.addWidget(lbl_start_c, 0, 0)
        c_grid.addWidget(self.start_current_spin, 0, 1)
        c_grid.addWidget(lbl_end_c, 1, 0)
        c_grid.addWidget(self.end_current_spin, 1, 1)
        c_grid.addWidget(lbl_step_c, 2, 0)
        c_grid.addWidget(self.step_current_spin, 2, 1)
        c_grid.addWidget(lbl_delay_c, 3, 0)
        c_grid.addWidget(self.step_delay_c_spin, 3, 1)
        layout.addWidget(self.current_param_widget)

        self.temp_param_widget = QWidget()
        self.temp_param_widget.setStyleSheet("background: transparent;")
        t_grid = QGridLayout(self.temp_param_widget)
        t_grid.setContentsMargins(0, 0, 0, 0)
        t_grid.setHorizontalSpacing(10)
        t_grid.setVerticalSpacing(10)
        lbl_start_t = QLabel("Start Temp (C)")
        lbl_start_t.setObjectName("fieldLabel")
        self.start_temp_spin = QDoubleSpinBox()
        self.start_temp_spin.setRange(-55.0, 200.0)
        self.start_temp_spin.setValue(-40.0)
        self.start_temp_spin.setSingleStep(5)
        self.start_temp_spin.setDecimals(1)
        lbl_end_t = QLabel("End Temp (C)")
        lbl_end_t.setObjectName("fieldLabel")
        self.end_temp_spin = QDoubleSpinBox()
        self.end_temp_spin.setRange(-55.0, 200.0)
        self.end_temp_spin.setValue(85.0)
        self.end_temp_spin.setSingleStep(5)
        self.end_temp_spin.setDecimals(1)
        lbl_step_t = QLabel("Step Temp (C)")
        lbl_step_t.setObjectName("fieldLabel")
        self.step_temp_spin = QDoubleSpinBox()
        self.step_temp_spin.setRange(0.1, 100.0)
        self.step_temp_spin.setValue(25.0)
        self.step_temp_spin.setSingleStep(5)
        self.step_temp_spin.setDecimals(1)
        lbl_delay_t = QLabel("Step Delay (ms)")
        lbl_delay_t.setObjectName("fieldLabel")
        self.step_delay_t_spin = QSpinBox()
        self.step_delay_t_spin.setRange(1, 60000)
        self.step_delay_t_spin.setValue(1000)
        self.step_delay_t_spin.setSingleStep(100)
        t_grid.addWidget(lbl_start_t, 0, 0)
        t_grid.addWidget(self.start_temp_spin, 0, 1)
        t_grid.addWidget(lbl_end_t, 1, 0)
        t_grid.addWidget(self.end_temp_spin, 1, 1)
        t_grid.addWidget(lbl_step_t, 2, 0)
        t_grid.addWidget(self.step_temp_spin, 2, 1)
        t_grid.addWidget(lbl_delay_t, 3, 0)
        t_grid.addWidget(self.step_delay_t_spin, 3, 1)
        layout.addWidget(self.temp_param_widget)

        self.reg_param_widget = QWidget()
        self.reg_param_widget.setStyleSheet("background: transparent;")
        r_grid = QGridLayout(self.reg_param_widget)
        r_grid.setContentsMargins(0, 0, 0, 0)
        r_grid.setHorizontalSpacing(10)
        r_grid.setVerticalSpacing(10)
        lbl_write_reg = QLabel("Write Reg Addr (Hex)")
        lbl_write_reg.setObjectName("fieldLabel")
        self.write_reg_addr_edit = QLineEdit("0x00")
        lbl_reg_start = QLabel("Start Value")
        lbl_reg_start.setObjectName("fieldLabel")
        self.reg_start_spin = QSpinBox()
        self.reg_start_spin.setRange(0, 255)
        self.reg_start_spin.setValue(0)
        lbl_reg_end = QLabel("End Value")
        lbl_reg_end.setObjectName("fieldLabel")
        self.reg_end_spin = QSpinBox()
        self.reg_end_spin.setRange(0, 255)
        self.reg_end_spin.setValue(255)
        lbl_reg_step = QLabel("Step")
        lbl_reg_step.setObjectName("fieldLabel")
        self.reg_step_spin = QSpinBox()
        self.reg_step_spin.setRange(1, 255)
        self.reg_step_spin.setValue(1)
        lbl_delay_r = QLabel("Step Delay (ms)")
        lbl_delay_r.setObjectName("fieldLabel")
        self.step_delay_r_spin = QSpinBox()
        self.step_delay_r_spin.setRange(1, 60000)
        self.step_delay_r_spin.setValue(10)
        self.step_delay_r_spin.setSingleStep(10)
        r_grid.addWidget(lbl_write_reg, 0, 0)
        r_grid.addWidget(self.write_reg_addr_edit, 0, 1)
        r_grid.addWidget(lbl_reg_start, 1, 0)
        r_grid.addWidget(self.reg_start_spin, 1, 1)
        r_grid.addWidget(lbl_reg_end, 2, 0)
        r_grid.addWidget(self.reg_end_spin, 2, 1)
        r_grid.addWidget(lbl_reg_step, 3, 0)
        r_grid.addWidget(self.reg_step_spin, 3, 1)
        r_grid.addWidget(lbl_delay_r, 4, 0)
        r_grid.addWidget(self.step_delay_r_spin, 4, 1)
        layout.addWidget(self.reg_param_widget)

    def _build_register_config_card(self):
        layout = self.register_config_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        lbl_width = QLabel("IIC Width")
        lbl_width.setObjectName("fieldLabel")
        self.iic_width_combo = DarkComboBox()
        self.iic_width_combo.addItem("8 BIT", I2CWidthFlag.BIT_8)
        self.iic_width_combo.addItem("10 BIT", I2CWidthFlag.BIT_10)
        self.iic_width_combo.addItem("32 BIT", I2CWidthFlag.BIT_32)
        self.iic_width_combo.setCurrentIndex(1)
        lbl_dev = QLabel("Device Addr (Hex)")
        lbl_dev.setObjectName("fieldLabel")
        self.device_addr_edit = QLineEdit("0x6A")
        lbl_reg_addr = QLabel("Reg Addr (Hex)")
        lbl_reg_addr.setObjectName("fieldLabel")
        self.reg_addr_edit = QLineEdit("0x0B")
        lbl_reg_bit = QLabel("Reg Bit")
        lbl_reg_bit.setObjectName("fieldLabel")
        self.reg_bit_edit = QLineEdit("6")
        grid.addWidget(lbl_width, 0, 0)
        grid.addWidget(self.iic_width_combo, 0, 1)
        grid.addWidget(lbl_dev, 1, 0)
        grid.addWidget(self.device_addr_edit, 1, 1)
        grid.addWidget(lbl_reg_addr, 2, 0)
        grid.addWidget(self.reg_addr_edit, 2, 1)
        grid.addWidget(lbl_reg_bit, 3, 0)
        grid.addWidget(self.reg_bit_edit, 3, 1)
        layout.addLayout(grid)

    def _create_reg_card(self, name, info):
        frame = QFrame()
        frame.setObjectName("regCard")
        frame.setMinimumHeight(80)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        name_label = QLabel(name)
        name_label.setObjectName("regName")
        value_label = QLabel("---")
        value_label.setObjectName("regValue")
        desc_label = QLabel(f"[0x{info['addr']:02X}] Bits {info['bits']} \u2014 {info['desc']}")
        desc_label.setObjectName("regDesc")
        lay.addWidget(name_label)
        lay.addWidget(value_label)
        lay.addWidget(desc_label)
        return {"frame": frame, "name_label": name_label, "value_label": value_label, "desc_label": desc_label}

    def _init_ui_elements(self):
        self._update_connect_button_state(False)
        self.append_log("[SYSTEM] Status Register Test ready.")
        self._on_test_item_changed()
        self._on_vt6002_connection_changed()

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)
        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        self.test_item_combo.currentTextChanged.connect(self._on_test_item_changed)
        self.vt6002_search_btn.clicked.connect(self._search_vt6002)
        self.vt6002_connect_btn.clicked.connect(self._toggle_vt6002)
        if self._vt6002_chamber_ui is not None:
            self._vt6002_chamber_ui.connection_changed.connect(self._on_vt6002_connection_changed)

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        update_connect_button_state(self.connect_btn, connected)

    def _on_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        self.set_system_status("\u25cf Searching")
        self.append_log("[SYSTEM] Scanning VISA resources...")
        self.search_btn.setEnabled(False)
        self.search_timer.start(100)

    def _search_devices(self):
        try:
            if self.rm is None:
                try:
                    self.rm = pyvisa.ResourceManager()
                except Exception:
                    self.rm = pyvisa.ResourceManager('@ni')
            self.available_devices = list(self.rm.list_resources()) or []
            compatible_devices = []
            if self.available_devices:
                compatible_devices = self.available_devices.copy()
            n6705c_devices = []
            for dev in compatible_devices:
                try:
                    instr = self.rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception:
                    pass
            self.visa_resource_combo.setEnabled(True)
            self.visa_resource_combo.clear()
            if n6705c_devices:
                for dev in n6705c_devices:
                    self.visa_resource_combo.addItem(dev)
                count = len(n6705c_devices)
                self.set_system_status(f"\u25cf Found {count} device(s)")
                self.append_log(f"[SYSTEM] Found {count} compatible N6705C device(s).")
                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    self.visa_resource_combo.setCurrentText(default_device)
                else:
                    self.visa_resource_combo.setCurrentIndex(0)
            else:
                self.visa_resource_combo.addItem("No N6705C device found")
                self.visa_resource_combo.setEnabled(False)
                self.set_system_status("\u25cf No device found", is_error=True)
                self.append_log("[SYSTEM] No compatible N6705C instrument found.")
        except Exception as e:
            self.set_system_status("\u25cf Search failed", is_error=True)
            self.append_log(f"[ERROR] Search failed: {str(e)}")
        finally:
            self.search_btn.setEnabled(True)

    def _on_connect_or_disconnect(self):
        if self.is_connected:
            self._on_disconnect()
        else:
            self._on_connect()

    def _on_connect(self):
        self.set_system_status("\u25cf Connecting")
        self.append_log("[SYSTEM] Attempting instrument connection...")
        self.connect_btn.setEnabled(False)
        try:
            device_address = self.visa_resource_combo.currentText()
            if DEBUG_MOCK:
                self.n6705c = MockN6705C()
                idn_match = True
            else:
                self.n6705c = N6705C(device_address)
                idn = self.n6705c.instr.query("*IDN?")
                idn_match = "N6705C" in idn
            if idn_match:
                self._update_connect_button_state(True)
                self.set_system_status("\u25cf Connected")
                self.search_btn.setEnabled(False)
                pretty_name = device_address
                try:
                    pretty_name = device_address.split("::")[1]
                except Exception:
                    pass
                self.instrument_info_label.setText(pretty_name)
                self.append_log("[SYSTEM] N6705C connected successfully.")
                if not DEBUG_MOCK:
                    self.append_log(f"[IDN] {idn.strip()}")
                if self._n6705c_top:
                    self._n6705c_top.connect_a(device_address, self.n6705c)
                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("\u25cf Device mismatch", is_error=True)
                self.append_log("[ERROR] Connected device is not N6705C.")
        except Exception as e:
            self.set_system_status("\u25cf Connection failed", is_error=True)
            self.append_log(f"[ERROR] Connection failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_disconnect(self):
        self.set_system_status("\u25cf Disconnecting")
        self.append_log("[SYSTEM] Disconnecting instrument...")
        self.connect_btn.setEnabled(False)
        try:
            if self._n6705c_top:
                self._n6705c_top.disconnect_a()
                self.n6705c = None
            else:
                if self.n6705c is not None:
                    if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                        self.n6705c.instr.close()
                    if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                        self.n6705c.rm.close()
                self.n6705c = None
            self._update_connect_button_state(False)
            self.set_system_status("\u25cf Ready")
            self.search_btn.setEnabled(True)
            self.instrument_info_label.setText("USB0::0x0957::0x0F07::MY53004321")
            self.append_log("[SYSTEM] Instrument disconnected.")
            self.connection_status_changed.emit(False)
        except Exception as e:
            self.set_system_status("\u25cf Disconnect failed", is_error=True)
            self.append_log(f"[ERROR] Disconnect failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_vt6002_connection_changed(self):
        if self._vt6002_syncing:
            return
        if self._vt6002_chamber_ui is None:
            return
        vt = self._vt6002_chamber_ui.vt6002
        if vt is not None:
            is_open = isinstance(vt, MockVT6002) or (hasattr(vt, 'ser') and vt.ser.is_open)
            if is_open:
                self.vt6002 = vt
                self.is_vt6002_connected = True
                port = getattr(self._vt6002_chamber_ui, 'current_port', 'Unknown')
                self._update_vt6002_ui(True, f"Connected: {port}")
                self.append_log(f"[VT6002] Synced: {port}")
                return
        self.vt6002 = None
        self.is_vt6002_connected = False
        self._update_vt6002_ui(False, "Not Connected")
        self.append_log("[VT6002] Disconnected (synced).")

    def _search_vt6002(self):
        if DEBUG_MOCK:
            self.vt6002_combo.clear()
            self.vt6002_combo.addItem("[MOCK] COM3 - VT6002 Chamber")
            return
        if self._vt6002_search_thread is not None and self._vt6002_search_thread.isRunning():
            return
        self.vt6002_search_btn.setEnabled(False)
        self.vt6002_connect_btn.setEnabled(False)
        worker = _SearchSerialWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_vt6002_search_done)
        worker.error.connect(self._on_vt6002_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_vt6002_thread_cleanup())
        self._vt6002_search_thread = thread
        self._vt6002_search_worker = worker
        thread.start()

    def _on_vt6002_thread_cleanup(self):
        self._vt6002_search_thread = None
        self._vt6002_search_worker = None

    def _on_vt6002_search_done(self, ports):
        self.vt6002_combo.clear()
        if ports:
            for port in ports:
                self.vt6002_combo.addItem(port)
            self.vt6002_connect_btn.setEnabled(True)
        else:
            self.vt6002_combo.addItem("No serial ports found")
            self.vt6002_connect_btn.setEnabled(False)
        self.vt6002_search_btn.setEnabled(True)

    def _on_vt6002_search_error(self, err):
        self.append_log(f"[VT6002] Search error: {err}")
        self.vt6002_search_btn.setEnabled(True)
        self.vt6002_connect_btn.setEnabled(False)

    def _toggle_vt6002(self):
        if self.is_vt6002_connected:
            self._disconnect_vt6002()
        else:
            self._connect_vt6002()

    def _connect_vt6002(self):
        self.vt6002_connect_btn.setEnabled(False)
        if DEBUG_MOCK:
            vt = MockVT6002()
            port = "MOCK"
        else:
            try:
                from instruments.chambers.vt6002_chamber import VT6002
                port_str = self.vt6002_combo.currentText()
                port = port_str.split()[0]
                vt = VT6002(port)
            except Exception as e:
                self.append_log(f"[VT6002] Connection failed: {e}")
                self._update_vt6002_ui(False, "Error")
                return
        self.vt6002 = vt
        self.is_vt6002_connected = True
        self._update_vt6002_ui(True, f"Connected: {port}")
        self.append_log(f"[VT6002] Connected: {port}")
        if self._vt6002_chamber_ui is not None:
            self._vt6002_syncing = True
            self._vt6002_chamber_ui.vt6002 = vt
            self._vt6002_chamber_ui.current_port = port
            self._vt6002_chamber_ui._set_connection_ui(True)
            self._vt6002_chamber_ui._set_controls_enabled(True)
            self._vt6002_chamber_ui.connection_changed.emit()
            self._vt6002_syncing = False

    def _disconnect_vt6002(self):
        self.vt6002_connect_btn.setEnabled(False)
        try:
            if self.vt6002 is not None:
                self.vt6002.close()
        except Exception as e:
            self.append_log(f"[VT6002] Close error: {e}")
        self.vt6002 = None
        self.is_vt6002_connected = False
        self._update_vt6002_ui(False, "Disconnected")
        self.append_log("[VT6002] Disconnected.")
        if self._vt6002_chamber_ui is not None:
            self._vt6002_syncing = True
            self._vt6002_chamber_ui.vt6002 = None
            self._vt6002_chamber_ui.current_port = None
            self._vt6002_chamber_ui.is_chamber_on = False
            self._vt6002_chamber_ui._set_connection_ui(False)
            self._vt6002_chamber_ui._set_controls_enabled(False)
            self._vt6002_chamber_ui._set_power_ui(False)
            self._vt6002_chamber_ui.connection_changed.emit()
            self._vt6002_syncing = False

    def _update_vt6002_ui(self, connected, status_text):
        color = "#18a067" if connected else "#ff5a7a"
        self.vt6002_indicator.setText("\u25cf" if connected else "\u25cb")
        self.vt6002_indicator.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")
        self.vt6002_status_label.setText(status_text)
        self.vt6002_status_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 11px;")
        update_connect_button_state(self.vt6002_connect_btn, connected)
        self.vt6002_search_btn.setEnabled(not connected)
        self.vt6002_combo.setEnabled(not connected)

    def get_test_config(self):
        test_item = self.test_item_combo.currentText()
        device_addr = int(self.device_addr_edit.text(), 16)
        reg_addr = int(self.reg_addr_edit.text(), 16)
        reg_bit = self.reg_bit_edit.text().strip()
        iic_width = self.iic_width_combo.currentData()

        cfg = {
            "test_item": test_item,
            "device_addr": device_addr,
            "reg_addr": reg_addr,
            "reg_bit": reg_bit,
            "iic_width": iic_width,
        }

        if test_item == "Voltage Sweep":
            ch_text = self.test_channel_combo.currentText()
            cfg["test_channel"] = int(ch_text.replace("CH ", ""))
            cfg["start_voltage"] = self.start_voltage_spin.value()
            cfg["end_voltage"] = self.end_voltage_spin.value()
            cfg["step_voltage"] = self.step_voltage_spin.value()
            cfg["step_delay_ms"] = self.step_delay_v_spin.value()
        elif test_item == "Current Sweep":
            ch_text = self.test_channel_combo.currentText()
            cfg["test_channel"] = int(ch_text.replace("CH ", ""))
            cfg["start_current"] = self.start_current_spin.value()
            cfg["end_current"] = self.end_current_spin.value()
            cfg["step_current"] = self.step_current_spin.value()
            cfg["step_delay_ms"] = self.step_delay_c_spin.value()
        elif test_item == "Temperature Sweep":
            cfg["start_temp"] = self.start_temp_spin.value()
            cfg["end_temp"] = self.end_temp_spin.value()
            cfg["step_temp"] = self.step_temp_spin.value()
            cfg["step_delay_ms"] = self.step_delay_t_spin.value()
        elif test_item == "Reg Sweep":
            cfg["write_reg_addr"] = int(self.write_reg_addr_edit.text(), 16)
            cfg["reg_start_value"] = self.reg_start_spin.value()
            cfg["reg_end_value"] = self.reg_end_spin.value()
            cfg["reg_step_value"] = self.reg_step_spin.value()
            cfg["step_delay_ms"] = self.step_delay_r_spin.value()

        return cfg

    def _on_start_test(self):
        test_item = self.test_item_combo.currentText()

        if test_item in ("Voltage Sweep", "Current Sweep"):
            if not self.is_connected or self.n6705c is None:
                self.append_log("[ERROR] N6705C not connected. Please connect first.")
                return

        if test_item == "Temperature Sweep":
            if not self.is_vt6002_connected or self.vt6002 is None:
                self.append_log("[ERROR] VT6002 chamber not connected. Please connect first.")
                return

        config = self.get_test_config()
        self.append_log(f"[TEST] Starting {test_item} ...")
        self.append_log(f"[CONFIG] {config}")

        self.set_test_running(True)

        vt6002_ref = self.vt6002 if test_item == "Temperature Sweep" else None

        self.test_worker = _StatusPollWorker(self.n6705c, config, vt6002=vt6002_ref)
        self.test_thread = QThread()
        self.test_worker.moveToThread(self.test_thread)

        self.test_thread.started.connect(self.test_worker.run)
        self.test_worker.log_message.connect(self.append_log)
        self.test_worker.status_update.connect(self._on_status_update)
        self.test_worker.progress.connect(self._on_progress)
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_worker.error.connect(self._on_test_error)

        self.test_worker.test_finished.connect(self.test_thread.quit)
        self.test_worker.error.connect(self.test_thread.quit)
        self.test_thread.finished.connect(self.test_worker.deleteLater)
        self.test_thread.finished.connect(self.test_thread.deleteLater)

        self.test_thread.start()

    def _on_stop_test(self):
        if self.test_worker:
            self.test_worker.request_stop()
            self.append_log("[SYSTEM] Stop requested...")
        self.set_test_running(False)

    def set_test_running(self, running: bool):
        self.is_test_running = running
        self.start_test_btn.setVisible(not running)
        self.stop_test_btn.setVisible(running)
        self.test_item_combo.setEnabled(not running)
        self.connect_btn.setEnabled(not running)
        self.visa_resource_combo.setEnabled(not running)
        self.search_btn.setEnabled(not running and not self.is_connected)
        self.test_channel_combo.setEnabled(not running)
        self.vt6002_connect_btn.setEnabled(not running)
        self.vt6002_search_btn.setEnabled(not running)

    def _on_test_finished(self, success):
        self.set_test_running(False)
        if success:
            self.append_log("[SYSTEM] Test completed successfully \u2714")
        else:
            self.append_log("[SYSTEM] Test completed (no flip detected or error).")

    def _on_test_error(self, msg):
        self.set_test_running(False)
        self.append_log(f"[ERROR] {msg}")

    def _on_status_update(self, data):
        for key, info in data.items():
            value = info.get("value", 0)
            raw = info.get("raw", 0)
            desc = info.get("desc", "")
            reg_addr = info.get("addr", 0)
            bits = info.get("bits", "")
            for name, card in self.status_labels.items():
                reg_info = STATUS_REGISTER_MAP.get(name, {})
                if reg_info.get("addr") == reg_addr:
                    if ":" in reg_info.get("bits", ""):
                        hi, lo = [int(x) for x in reg_info["bits"].split(":")]
                        mask = ((1 << (hi - lo + 1)) - 1) << lo
                        val = (raw & mask) >> lo
                    else:
                        bit_pos = int(reg_info["bits"])
                        val = (raw >> bit_pos) & 1
                    card["value_label"].setText(f"0x{val:02X} ({val})")

    def _on_progress(self, pct):
        pass

    def _on_clear_log(self):
        self.log_edit.clear()
        self.append_log("[SYSTEM] Log cleared.")

    def set_system_status(self, text, is_error=False):
        self.system_status_label.setText(text)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.setStyle(self.system_status_label.style())

    def append_log(self, message):
        self.log_edit.append(message)
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def clear_results(self):
        for name, card in self.status_labels.items():
            card["value_label"].setText("---")

    def update_test_result(self, result):
        if isinstance(result, dict):
            self._on_status_update(result)

    def _sync_from_top(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            self.n6705c = self._n6705c_top.n6705c_a
            addr = self._n6705c_top.visa_resource_a or ""
            self._update_connect_button_state(True)
            self.set_system_status("\u25cf Connected (shared)")
            self.instrument_info_label.setText(addr)
            self.search_btn.setEnabled(False)
            self.visa_resource_combo.setCurrentText(addr)
            self.append_log(f"[SYSTEM] Synced N6705C from main page: {addr}")
