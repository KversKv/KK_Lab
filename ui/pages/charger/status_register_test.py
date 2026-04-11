#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "lib", "i2c"))

from ui.widgets.dark_combobox import DarkComboBox
from ui.styles import SCROLLBAR_STYLE
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGridLayout, QFrame, QDoubleSpinBox, QSpinBox,
    QTextEdit, QProgressBar, QSizePolicy,
    QApplication
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtGui import QFont
import time
import pyvisa

from instruments.power.keysight.n6705c import N6705C
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


class _StatusPollWorker(QObject):
    log_message = Signal(str)
    status_update = Signal(dict)
    progress = Signal(int)
    test_finished = Signal(bool)
    error = Signal(str)

    def __init__(self, n6705c, config):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
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

    def run(self):
        try:
            device_addr = self._cfg["device_addr"]
            iic_width = self._cfg["iic_width"]
            reg_addr = self._cfg["reg_addr"]
            bits_str = self._cfg["reg_bit"]
            test_channel = self._cfg["test_channel"]
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

            if test_item == "Voltage":
                start = self._cfg["start_voltage"]
                end = self._cfg["end_voltage"]
                step = self._cfg["step_voltage"]
                unit = "V"
            else:
                start = self._cfg["start_current"]
                end = self._cfg["end_current"]
                step = self._cfg["step_current"]
                unit = "mA"

            if step <= 0:
                self.log_message.emit("[ERROR] Step must be > 0.")
                self.test_finished.emit(False)
                return

            step_delay_s = self._cfg.get("step_delay_ms", 10) / 1000.0

            ascending = end >= start
            if not ascending:
                step = -abs(step)

            levels = []
            current_level = start
            if ascending:
                while current_level <= end + step * 0.01:
                    levels.append(round(current_level, 6))
                    current_level += abs(step)
            else:
                while current_level >= end + step * 0.01:
                    levels.append(round(current_level, 6))
                    current_level -= abs(step)

            total_steps = len(levels)
            if total_steps == 0:
                self.log_message.emit("[ERROR] No sweep steps generated.")
                self.test_finished.emit(False)
                return

            self.log_message.emit(
                f"[TEST] Sweep {test_item}: {start} {unit} -> {end} {unit}, "
                f"step={abs(step)} {unit}, total {total_steps} steps"
            )

            self._n6705c.channel_on(test_channel)
            time.sleep(0.2)

            threshold_value = None

            for idx, level in enumerate(levels):
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user.")
                    break

                if test_item == "Voltage":
                    self._n6705c.set_voltage(test_channel, level)
                else:
                    self._n6705c.set_current(test_channel, level / 1000.0)

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
                self.log_message.emit(
                    f"[RESULT] Threshold {test_item} = {threshold_value:.4g} {unit}"
                )
            elif not self._stop_flag:
                self.log_message.emit(
                    f"[WARN] Register did not flip during sweep "
                    f"({start} {unit} -> {end} {unit})."
                )

            self.test_finished.emit(threshold_value is not None)
        except Exception as e:
            self.log_message.emit(f"[ERROR] {e}")
            self.error.emit(str(e))
            self.test_finished.emit(False)


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

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []

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
            QWidget {
                background-color: #020817;
                color: #dbe7ff;
            }
            QLabel {
                background-color: transparent;
                color: #dbe7ff;
                border: none;
            }
            QLabel#pageTitle {
                font-size: 18px;
                font-weight: 700;
                color: #f8fbff;
                background-color: transparent;
            }
            QLabel#pageSubtitle {
                font-size: 12px;
                color: #7da2d6;
                background-color: transparent;
            }
            QFrame#panelFrame {
                background-color: #08132d;
                border: 1px solid #16274d;
                border-radius: 18px;
            }
            QFrame#cardFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 14px;
            }
            QLabel#cardTitle {
                font-size: 11px;
                font-weight: 700;
                color: #f4f7ff;
                letter-spacing: 0.5px;
                background-color: transparent;
            }
            QLabel#sectionTitle {
                font-size: 12px;
                font-weight: 700;
                color: #f4f7ff;
                background-color: transparent;
            }
            QLabel#fieldLabel {
                color: #8eb0e3;
                font-size: 11px;
                background-color: transparent;
            }
            QLabel#statusOk {
                color: #15d1a3;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusWarn {
                color: #ffb84d;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusErr {
                color: #ff5e7a;
                font-weight: 600;
                background-color: transparent;
            }
            QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QTextEdit {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #4f46e5;
            }
            QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4cc9f0;
            }
            QComboBox { padding-right: 24px; }
            QComboBox::drop-down { border: none; width: 22px; background: transparent; }
            QComboBox QAbstractItemView {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                selection-background-color: #334a7d;
            }
            QPushButton {
                min-height: 34px;
                border-radius: 9px;
                padding: 6px 14px;
                border: 1px solid #2a4272;
                background-color: #102042;
                color: #dfeaff;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #162a56;
                border: 1px solid #3c5fa1;
            }
            QPushButton:pressed { background-color: #0d1a37; }
            QPushButton:disabled {
                background-color: #0b1430;
                color: #5c7096;
                border: 1px solid #1a2850;
            }
            QPushButton#primaryStartBtn {
                min-height: 36px;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 800;
                color: white;
                border: 1px solid #645bff;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5b5cf6, stop:1 #6a38ff
                );
            }
            QPushButton#primaryStartBtn:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b6cff, stop:1 #7d4cff
                );
            }
            QPushButton#stopBtn {
                background-color: #4a1020;
                border: 1px solid #d9485f;
                color: #ffd5db;
            }
            QPushButton#stopBtn:hover { background-color: #5a1326; }
            QPushButton#smallActionBtn {
                min-height: 28px;
                padding: 4px 10px;
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
            }
            QPushButton#dynamicConnectBtn {
                min-height: 34px;
                border-radius: 10px;
                padding: 6px 14px;
                font-weight: 700;
            }
            QPushButton#dynamicConnectBtn[connected="false"] {
                background-color: #053b38;
                border: 1px solid #08c9a5;
                color: #10e7bc;
            }
            QPushButton#dynamicConnectBtn[connected="false"]:hover {
                background-color: #064744;
                border: 1px solid #19f0c5;
                color: #43f3d0;
            }
            QPushButton#dynamicConnectBtn[connected="false"]:pressed {
                background-color: #042f2d;
            }
            QPushButton#dynamicConnectBtn[connected="true"] {
                background-color: #3a0828;
                border: 1px solid #d61b67;
                color: #ffb7d3;
            }
            QPushButton#dynamicConnectBtn[connected="true"]:hover {
                background-color: #4a0b31;
                border: 1px solid #f0287b;
                color: #ffd0e2;
            }
            QPushButton#dynamicConnectBtn[connected="true"]:pressed {
                background-color: #330722;
            }
            QFrame#chartContainer, QFrame#logContainer {
                background-color: #09142e;
                border: 1px solid #1a2d57;
                border-radius: 16px;
            }
            QTextEdit#logEdit {
                background-color: #061022;
                border: 1px solid #1f315d;
                border-radius: 8px;
                color: #7cecc8;
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
            }
            QProgressBar {
                background-color: #152749;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: #b7c8ea;
                min-height: 8px;
                max-height: 8px;
            }
            QProgressBar::chunk {
                background-color: #5b5cf6;
                border-radius: 4px;
            }
            QLabel#regName {
                color: #dbe7ff;
                font-size: 12px;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#regValue {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                background-color: transparent;
            }
            QLabel#regDesc {
                color: #7da2d6;
                font-size: 10px;
                background-color: transparent;
            }
            QFrame#regCard {
                background-color: #0a1733;
                border: 1px solid #1b315f;
                border-radius: 10px;
            }
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.page_title = QLabel("📋 Status Register Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Monitor and poll Charger IC status registers in real-time.")
        self.page_subtitle.setObjectName("pageSubtitle")

        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_subtitle)
        root_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        root_layout.addLayout(content_layout, 1)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("panelFrame")
        self.left_panel.setFixedWidth(275)

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(16)

        self.connection_card = CardFrame("⚡ N6705C CONNECTION")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.test_config_card = CardFrame("☷ TEST CONFIG")
        self._build_test_config_card()
        left_layout.addWidget(self.test_config_card)

        self.register_config_card = CardFrame("↔ REGISTER CONFIG")
        self._build_register_config_card()
        left_layout.addWidget(self.register_config_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("▶ START POLL")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_layout.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("■ STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()

        content_layout.addWidget(self.left_panel)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)

        reg_frame = QFrame()
        reg_frame.setObjectName("chartContainer")
        reg_outer = QVBoxLayout(reg_frame)
        reg_outer.setContentsMargins(16, 16, 16, 16)
        reg_outer.setSpacing(10)

        reg_header = QHBoxLayout()
        reg_title = QLabel("📊 Register Status")
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
        self.log_title = QLabel("⊙ Execution Logs")
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

    def _build_connection_card(self):
        layout = self.connection_card.main_layout

        self.system_status_label = QLabel("● Ready")
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

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("smallActionBtn")
        search_row.addWidget(self.search_btn)

        layout.addLayout(search_row)

        self.connect_btn = QPushButton("🔗  Connect")
        self.connect_btn.setObjectName("dynamicConnectBtn")
        self.connect_btn.setProperty("connected", "false")
        layout.addWidget(self.connect_btn)

    def _build_test_config_card(self):
        layout = self.test_config_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        test_ch_label = QLabel("Test Channel")
        test_ch_label.setObjectName("fieldLabel")

        self.test_channel_combo = DarkComboBox()
        self.test_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])

        test_item_label = QLabel("Test Item")
        test_item_label.setObjectName("fieldLabel")

        self.test_item_combo = DarkComboBox()
        self.test_item_combo.addItems(["Voltage", "Current"])

        grid.addWidget(test_ch_label, 0, 0)
        grid.addWidget(self.test_channel_combo, 0, 1)
        grid.addWidget(test_item_label, 1, 0)
        grid.addWidget(self.test_item_combo, 1, 1)

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

        self.current_param_widget.setVisible(False)

        self.test_item_combo.currentTextChanged.connect(self._on_test_item_changed)

    def _on_test_item_changed(self, text):
        is_voltage = text == "Voltage"
        self.voltage_param_widget.setVisible(is_voltage)
        self.current_param_widget.setVisible(not is_voltage)

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

        desc_label = QLabel(f"[0x{info['addr']:02X}] Bits {info['bits']} — {info['desc']}")
        desc_label.setObjectName("regDesc")

        lay.addWidget(name_label)
        lay.addWidget(value_label)
        lay.addWidget(desc_label)

        return {"frame": frame, "name_label": name_label, "value_label": value_label, "desc_label": desc_label}

    def _init_ui_elements(self):
        self._update_connect_button_state(False)
        self.append_log("[SYSTEM] Status Register Test ready.")

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)
        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.clear_log_btn.clicked.connect(self._on_clear_log)

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        self.connect_btn.setProperty("connected", "true" if connected else "false")
        self.connect_btn.setText("⟲  Disconnect" if connected else "🔗  Connect")

        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.connect_btn.update()

    def _on_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        self.set_system_status("● Searching")
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
                self.set_system_status(f"● Found {count} device(s)")
                self.append_log(f"[SYSTEM] Found {count} compatible N6705C device(s).")

                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    self.visa_resource_combo.setCurrentText(default_device)
                else:
                    self.visa_resource_combo.setCurrentIndex(0)
            else:
                self.visa_resource_combo.addItem("No N6705C device found")
                self.visa_resource_combo.setEnabled(False)
                self.set_system_status("● No device found", is_error=True)
                self.append_log("[SYSTEM] No compatible N6705C instrument found.")

        except Exception as e:
            self.set_system_status("● Search failed", is_error=True)
            self.append_log(f"[ERROR] Search failed: {str(e)}")
        finally:
            self.search_btn.setEnabled(True)

    def _on_connect_or_disconnect(self):
        if self.is_connected:
            self._on_disconnect()
        else:
            self._on_connect()

    def _on_connect(self):
        self.set_system_status("● Connecting")
        self.append_log("[SYSTEM] Attempting instrument connection...")
        self.connect_btn.setEnabled(False)

        try:
            device_address = self.visa_resource_combo.currentText()
            self.n6705c = N6705C(device_address)

            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self._update_connect_button_state(True)
                self.set_system_status("● Connected")
                self.search_btn.setEnabled(False)

                pretty_name = device_address
                try:
                    pretty_name = device_address.split("::")[1]
                except Exception:
                    pass

                self.instrument_info_label.setText(pretty_name)
                self.append_log("[SYSTEM] N6705C connected successfully.")
                self.append_log(f"[IDN] {idn.strip()}")

                if self._n6705c_top:
                    self._n6705c_top.connect_a(device_address, self.n6705c)

                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("● Device mismatch", is_error=True)
                self.append_log("[ERROR] Connected device is not N6705C.")
        except Exception as e:
            self.set_system_status("● Connection failed", is_error=True)
            self.append_log(f"[ERROR] Connection failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_disconnect(self):
        self.set_system_status("● Disconnecting")
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

            self.set_system_status("● Ready")
            self.search_btn.setEnabled(True)
            self.instrument_info_label.setText("USB0::0x0957::0x0F07::MY53004321")
            self.append_log("[SYSTEM] Instrument disconnected.")

            self.connection_status_changed.emit(False)

        except Exception as e:
            self.set_system_status("● Disconnect failed", is_error=True)
            self.append_log(f"[ERROR] Disconnect failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_start_test(self):
        if not self.is_connected or self.n6705c is None:
            self.append_log("[ERROR] Not connected to N6705C instrument.")
            return
        if self.is_test_running:
            return

        try:
            device_addr = int(self.device_addr_edit.text(), 16)
        except ValueError:
            self.append_log("[ERROR] Invalid device address.")
            return

        try:
            reg_addr = int(self.reg_addr_edit.text(), 16)
        except ValueError:
            self.append_log("[ERROR] Invalid register address.")
            return

        iic_width = self.iic_width_combo.currentData()
        test_item = self.test_item_combo.currentText()

        config = {
            "device_addr": device_addr,
            "iic_width": iic_width,
            "reg_addr": reg_addr,
            "reg_bit": self.reg_bit_edit.text(),
            "test_channel": int(self.test_channel_combo.currentText().replace("CH ", "")),
            "test_item": test_item,
        }

        if test_item == "Voltage":
            config["start_voltage"] = self.start_voltage_spin.value()
            config["end_voltage"] = self.end_voltage_spin.value()
            config["step_voltage"] = self.step_voltage_spin.value()
            config["step_delay_ms"] = self.step_delay_v_spin.value()
        else:
            config["start_current"] = self.start_current_spin.value()
            config["end_current"] = self.end_current_spin.value()
            config["step_current"] = self.step_current_spin.value()
            config["step_delay_ms"] = self.step_delay_c_spin.value()

        self.set_test_running(True)

        self.test_thread = QThread()
        self.test_worker = _StatusPollWorker(self.n6705c, config)
        self.test_worker.moveToThread(self.test_thread)

        self.test_worker.log_message.connect(self.append_log)
        self.test_worker.status_update.connect(self._on_status_update)
        self.test_worker.progress.connect(self._on_progress)
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_worker.error.connect(lambda e: self.append_log(f"[ERROR] {e}"))
        self.test_thread.started.connect(self.test_worker.run)

        self.test_thread.start()
        self.append_log(f"[TEST] Status register sweep test started ({test_item}).")

    def _on_stop_test(self):
        if self.test_worker is not None:
            self.test_worker.request_stop()
        self.append_log("[TEST] Stop requested...")
        self._cleanup_thread()

    def _cleanup_thread(self):
        if self.test_thread is not None:
            self.test_thread.quit()
            self.test_thread.wait(2000)
            self.test_thread = None
            self.test_worker = None
        self.set_test_running(False)

    def _on_status_update(self, results):
        for name, data in results.items():
            if name in self.status_labels:
                val = data["value"]
                if val == -1:
                    self.status_labels[name]["value_label"].setText("ERR")
                    self.status_labels[name]["value_label"].setStyleSheet("color: #ff5e7a; font-size: 13px; font-weight: 700; background-color: transparent; border: none;")
                else:
                    self.status_labels[name]["value_label"].setText(f"0x{val:02X} ({val})")
                    self.status_labels[name]["value_label"].setStyleSheet("color: #15d1a3; font-size: 13px; font-weight: 700; background-color: transparent; border: none;")

    def _on_progress(self, value):
        self.append_log(f"[PROGRESS] {value}%")

    def _on_test_finished(self, success):
        self._cleanup_thread()
        if success:
            self.append_log("[TEST] Sweep test completed successfully.")
        else:
            self.append_log("[TEST] Sweep test finished (no flip detected or error).")

    def _on_clear_log(self):
        self.log_edit.clear()

    def set_test_running(self, running):
        self.is_test_running = running
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(running)
        if running:
            self.start_test_btn.setText("■ STOP")
            self.start_test_btn.setObjectName("stopBtn")
        else:
            self.start_test_btn.setText("▶ START POLL")
            self.start_test_btn.setObjectName("primaryStartBtn")
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.start_test_btn.update()
        self.test_channel_combo.setEnabled(not running)
        self.test_item_combo.setEnabled(not running)
        self.start_voltage_spin.setEnabled(not running)
        self.end_voltage_spin.setEnabled(not running)
        self.step_voltage_spin.setEnabled(not running)
        self.step_delay_v_spin.setEnabled(not running)
        self.start_current_spin.setEnabled(not running)
        self.end_current_spin.setEnabled(not running)
        self.step_current_spin.setEnabled(not running)
        self.step_delay_c_spin.setEnabled(not running)
        self.device_addr_edit.setEnabled(not running)
        self.iic_width_combo.setEnabled(not running)
        self.reg_addr_edit.setEnabled(not running)
        self.reg_bit_edit.setEnabled(not running)
        self.visa_resource_combo.setEnabled(not running)
        self.search_btn.setEnabled(not running)
        self.connect_btn.setEnabled(not running)

        if running:
            self.set_system_status("● Polling")
        else:
            self.set_system_status("● Ready" if not self.is_connected else "● Connected")

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Polling" in status or "Running" in status or "Searching" in status or "Connecting" in status or "Disconnecting" in status:
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def append_log(self, msg):
        self.log_edit.append(msg)
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    def get_test_config(self):
        try:
            device_addr = int(self.device_addr_edit.text(), 16)
        except ValueError:
            device_addr = 0
        try:
            reg_addr = int(self.reg_addr_edit.text(), 16)
        except ValueError:
            reg_addr = 0x0B
        config = {
            "test_channel": int(self.test_channel_combo.currentText().replace("CH ", "")),
            "test_item": self.test_item_combo.currentText(),
            "device_addr": device_addr,
            "iic_width": self.iic_width_combo.currentData(),
            "reg_addr": reg_addr,
            "reg_bit": self.reg_bit_edit.text(),
        }
        if config["test_item"] == "Voltage":
            config["start_voltage"] = self.start_voltage_spin.value()
            config["end_voltage"] = self.end_voltage_spin.value()
            config["step_voltage"] = self.step_voltage_spin.value()
            config["step_delay_ms"] = self.step_delay_v_spin.value()
        else:
            config["start_current"] = self.start_current_spin.value()
            config["end_current"] = self.end_current_spin.value()
            config["step_current"] = self.step_current_spin.value()
            config["step_delay_ms"] = self.step_delay_c_spin.value()
        return config

    def clear_results(self):
        for name in self.status_labels:
            self.status_labels[name]["value_label"].setText("---")
            self.status_labels[name]["value_label"].setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700; background-color: transparent; border: none;")

    def update_test_result(self, result):
        self._on_status_update(result)

    def _sync_from_top(self):
        if not self._n6705c_top:
            return
        if self._n6705c_top.is_connected_a and self._n6705c_top.n6705c_a:
            self.n6705c = self._n6705c_top.n6705c_a
            self._update_connect_button_state(True)
            self.search_btn.setEnabled(False)
            if self._n6705c_top.visa_resource_a:
                self.visa_resource_combo.clear()
                self.visa_resource_combo.addItem(self._n6705c_top.visa_resource_a)
        elif not self.is_connected:
            self._update_connect_button_state(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = StatusRegisterTestUI()
    window.setWindowTitle("Status Register Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())
