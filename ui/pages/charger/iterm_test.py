#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "lib", "i2c"))

from ui.widgets.dark_combobox import DarkComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGridLayout, QSpinBox, QDoubleSpinBox, QFrame,
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

ITERM_REGISTER_MAP = {
    0: {"code": 0x00, "current_ma": 60},
    1: {"code": 0x01, "current_ma": 120},
    2: {"code": 0x02, "current_ma": 180},
    3: {"code": 0x03, "current_ma": 240},
    4: {"code": 0x04, "current_ma": 300},
    5: {"code": 0x05, "current_ma": 360},
    6: {"code": 0x06, "current_ma": 420},
    7: {"code": 0x07, "current_ma": 480},
}


class _ItermTestWorker(QObject):
    log_message = Signal(str)
    progress = Signal(int)
    result_row = Signal(dict)
    test_finished = Signal(bool)

    def __init__(self, n6705c, config):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        try:
            device_addr = self._cfg["device_addr"]
            iterm_reg = self._cfg["iterm_reg"]
            iic_width = self._cfg["iic_width"]
            measure_channel = self._cfg["measure_channel"]
            settle_time = self._cfg["settle_time_ms"] / 1000.0
            iterm_map = self._cfg.get("iterm_map", ITERM_REGISTER_MAP)

            i2c = I2CInterface()
            self._i2c = i2c

            total = len(iterm_map)

            self.log_message.emit(
                f"[TEST] Starting Iterm test on device 0x{device_addr:02X}, "
                f"reg 0x{iterm_reg:02X}"
            )

            for idx, (key, entry) in enumerate(iterm_map.items()):
                if self._stop_flag:
                    self.log_message.emit("[TEST] Test stopped by user.")
                    break

                code = entry["code"]
                expected_ma = entry["current_ma"]

                try:
                    self._i2c.write(device_addr, iterm_reg, code, iic_width)
                    time.sleep(settle_time)

                    if self._n6705c is not None:
                        measured_str = self._n6705c.measure_current(measure_channel)
                        measured_a = float(measured_str)
                        measured_ma = abs(measured_a) * 1000.0
                    else:
                        measured_ma = 0.0

                    tolerance = self._cfg.get("tolerance_pct", 15.0)
                    lower = expected_ma * (1 - tolerance / 100.0)
                    upper = expected_ma * (1 + tolerance / 100.0)
                    result = "PASS" if lower <= measured_ma <= upper else "FAIL"

                    row = {
                        "code": f"0x{code:02X}",
                        "expected_ma": f"{expected_ma}",
                        "measured_ma": f"{measured_ma:.2f}",
                        "result": result,
                    }
                    self.result_row.emit(row)
                    self.log_message.emit(
                        f"[DATA] Code 0x{code:02X}: Expected {expected_ma}mA, "
                        f"Measured {measured_ma:.2f}mA => {result}"
                    )
                except Exception as e:
                    self.log_message.emit(f"[ERROR] Code 0x{code:02X}: {e}")
                    self.result_row.emit({
                        "code": f"0x{code:02X}",
                        "expected_ma": f"{expected_ma}",
                        "measured_ma": "ERR",
                        "result": "ERROR",
                    })

                pct = int((idx + 1) / total * 100)
                self.progress.emit(pct)

            self.test_finished.emit(True)
        except Exception as e:
            self.log_message.emit(f"[ERROR] {e}")
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


class ItermTestUI(QWidget):
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
        self._export_data = []
        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0

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
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #4f46e5;
            }
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4cc9f0;
            }
            QComboBox { padding-right: 24px; }
            QComboBox::drop-down {
                border: none; width: 22px; background: transparent;
            }
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
            QLabel#metricLabel {
                color: #9db6db;
                font-size: 12px;
                background-color: transparent;
            }
            QLabel#metricValue {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                background-color: transparent;
            }
            QFrame#miniStatCard {
                background-color: #0a1733;
                border: 1px solid #1b315f;
                border-radius: 10px;
            }
        """)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.page_title = QLabel("\U0001f50b Iterm Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel(
            "Validate Charger IC termination current settings across all Iterm codes."
        )
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

        self.connection_card = CardFrame("\u26a1 N6705C CONNECTION")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.param_card = CardFrame("\u21c4 TEST PARAMETERS")
        self._build_param_card()
        left_layout.addWidget(self.param_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("\u25b6 START ITERM TEST")
        self.start_test_btn.setObjectName("primaryStartBtn")

        self.stop_test_btn = QPushButton("\u25a0 STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.setEnabled(False)

        left_layout.addWidget(self.start_test_btn)
        left_layout.addWidget(self.stop_test_btn)

        content_layout.addWidget(self.left_panel)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)

        result_frame = QFrame()
        result_frame.setObjectName("chartContainer")
        result_outer = QVBoxLayout(result_frame)
        result_outer.setContentsMargins(16, 16, 16, 16)
        result_outer.setSpacing(10)

        result_header = QHBoxLayout()
        result_title = QLabel("\U0001f4ca Iterm Test Results")
        result_title.setObjectName("sectionTitle")
        result_header.addWidget(result_title)
        result_header.addStretch()

        result_outer.addLayout(result_header)

        mini_stat_layout = QHBoxLayout()
        self.total_card = self._create_mini_stat("Total", "0")
        self.pass_card = self._create_mini_stat("PASS", "0")
        self.fail_card = self._create_mini_stat("FAIL", "0")
        mini_stat_layout.addWidget(self.total_card["frame"])
        mini_stat_layout.addWidget(self.pass_card["frame"])
        mini_stat_layout.addWidget(self.fail_card["frame"])
        result_outer.addLayout(mini_stat_layout)

        self.result_log = QTextEdit()
        self.result_log.setObjectName("logEdit")
        self.result_log.setReadOnly(True)
        result_outer.addWidget(self.result_log, 1)

        right_layout.addWidget(result_frame, 4)

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

        self.progress_text_label = QLabel("0% Complete")
        self.progress_text_label.setObjectName("fieldLabel")
        log_header.addWidget(self.progress_text_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(120)
        log_header.addWidget(self.progress_bar)

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

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("smallActionBtn")
        search_row.addWidget(self.search_btn)

        layout.addLayout(search_row)

        self.connect_btn = QPushButton("\U0001f517  Connect")
        self.connect_btn.setObjectName("dynamicConnectBtn")
        self.connect_btn.setProperty("connected", "false")
        layout.addWidget(self.connect_btn)

    def _build_param_card(self):
        layout = self.param_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_dev = QLabel("Device Addr (hex)")
        lbl_dev.setObjectName("fieldLabel")
        self.device_addr_edit = QLineEdit("0x6A")

        lbl_width = QLabel("IIC Width")
        lbl_width.setObjectName("fieldLabel")
        self.iic_width_combo = DarkComboBox()
        self.iic_width_combo.addItem("8BIT", I2CWidthFlag.BIT_8)
        self.iic_width_combo.addItem("10BIT", I2CWidthFlag.BIT_10)
        self.iic_width_combo.addItem("32BIT", I2CWidthFlag.BIT_32)

        lbl_ch = QLabel("Measure Channel")
        lbl_ch.setObjectName("fieldLabel")
        self.measure_channel_combo = DarkComboBox()
        self.measure_channel_combo.addItems(["1", "2", "3", "4"])

        lbl_reg = QLabel("Iterm Reg (hex)")
        lbl_reg.setObjectName("fieldLabel")
        self.iterm_reg_edit = QLineEdit("0x03")

        lbl_settle = QLabel("Settle Time (ms)")
        lbl_settle.setObjectName("fieldLabel")
        self.settle_time_spin = QSpinBox()
        self.settle_time_spin.setRange(50, 10000)
        self.settle_time_spin.setValue(500)
        self.settle_time_spin.setSingleStep(50)

        lbl_tol = QLabel("Tolerance (%)")
        lbl_tol.setObjectName("fieldLabel")
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(1.0, 50.0)
        self.tolerance_spin.setValue(15.0)
        self.tolerance_spin.setDecimals(1)
        self.tolerance_spin.setSingleStep(1.0)

        grid.addWidget(lbl_dev, 0, 0)
        grid.addWidget(self.device_addr_edit, 0, 1)
        grid.addWidget(lbl_width, 1, 0)
        grid.addWidget(self.iic_width_combo, 1, 1)
        grid.addWidget(lbl_ch, 2, 0)
        grid.addWidget(self.measure_channel_combo, 2, 1)
        grid.addWidget(lbl_reg, 3, 0)
        grid.addWidget(self.iterm_reg_edit, 3, 1)
        grid.addWidget(lbl_settle, 4, 0)
        grid.addWidget(self.settle_time_spin, 4, 1)
        grid.addWidget(lbl_tol, 5, 0)
        grid.addWidget(self.tolerance_spin, 5, 1)
        layout.addLayout(grid)

    def _create_mini_stat(self, label_text, value_text):
        frame = QFrame()
        frame.setObjectName("miniStatCard")
        frame.setFixedHeight(60)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        lbl = QLabel(label_text)
        lbl.setObjectName("metricLabel")
        val = QLabel(value_text)
        val.setObjectName("metricValue")
        lay.addWidget(lbl)
        lay.addWidget(val)
        return {"frame": frame, "label": lbl, "value": val}

    def _init_ui_elements(self):
        self._update_connect_button_state(False)
        self.append_log("[SYSTEM] Iterm Test ready.")

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)
        self.start_test_btn.clicked.connect(self._on_start_test)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.clear_log_btn.clicked.connect(self._on_clear_log)

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        self.connect_btn.setProperty("connected", "true" if connected else "false")
        self.connect_btn.setText("\u21b2  Disconnect" if connected else "\U0001f517  Connect")

        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.connect_btn.update()

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
            self.n6705c = N6705C(device_address)

            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
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

    def _on_start_test(self):
        if not self.is_connected or self.n6705c is None:
            self.append_log("[ERROR] Not connected to N6705C instrument.")
            return
        if self.is_test_running:
            return

        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0
        self.result_log.clear()
        self._export_data = []

        try:
            device_addr = int(self.device_addr_edit.text(), 16)
            iterm_reg = int(self.iterm_reg_edit.text(), 16)
        except ValueError:
            self.append_log("[ERROR] Invalid hex address.")
            return

        iic_width = self.iic_width_combo.currentData()

        config = {
            "device_addr": device_addr,
            "iterm_reg": iterm_reg,
            "iic_width": iic_width,
            "measure_channel": int(self.measure_channel_combo.currentText()),
            "settle_time_ms": self.settle_time_spin.value(),
            "tolerance_pct": self.tolerance_spin.value(),
        }

        self.set_test_running(True)
        self.set_progress(0)

        self.test_thread = QThread()
        self.test_worker = _ItermTestWorker(self.n6705c, config)
        self.test_worker.moveToThread(self.test_thread)

        self.test_worker.log_message.connect(self.append_log)
        self.test_worker.progress.connect(self.set_progress)
        self.test_worker.result_row.connect(self._on_result_row)
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_thread.started.connect(self.test_worker.run)

        self.test_thread.start()

    def _on_stop_test(self):
        if self.test_worker is not None:
            self.test_worker.request_stop()
        self.append_log("[TEST] Stop requested...")

    def _on_result_row(self, row):
        self._total_count += 1
        if row["result"] == "PASS":
            self._pass_count += 1
        else:
            self._fail_count += 1

        self.result_log.append(
            f"Code {row['code']}: Expected {row['expected_ma']}mA, "
            f"Measured {row['measured_ma']}mA  [{row['result']}]"
        )
        self._export_data.append(row)

        self.total_card["value"].setText(str(self._total_count))
        self.pass_card["value"].setText(str(self._pass_count))
        self.fail_card["value"].setText(str(self._fail_count))

    def _on_test_finished(self, success):
        self.set_test_running(False)
        if success:
            self.append_log("[TEST] Iterm test completed.")
        else:
            self.append_log("[TEST] Iterm test ended with errors.")
        if self.test_thread is not None:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_thread = None
            self.test_worker = None

    def _on_clear_log(self):
        self.log_edit.clear()

    def set_test_running(self, running):
        self.is_test_running = running
        self.start_test_btn.setEnabled(not running)
        self.stop_test_btn.setEnabled(running)
        self.device_addr_edit.setEnabled(not running)
        self.iterm_reg_edit.setEnabled(not running)
        self.iic_width_combo.setEnabled(not running)
        self.measure_channel_combo.setEnabled(not running)
        self.settle_time_spin.setEnabled(not running)
        self.tolerance_spin.setEnabled(not running)
        self.visa_resource_combo.setEnabled(not running)
        self.search_btn.setEnabled(not running)
        self.connect_btn.setEnabled(not running)

        if running:
            self.set_system_status("\u25cf Running")
        else:
            self.set_system_status("\u25cf Ready" if not self.is_connected else "\u25cf Connected")

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}% Complete")

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Running" in status or "Searching" in status or "Connecting" in status or "Disconnecting" in status:
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def append_log(self, msg):
        self.log_edit.append(msg)
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def get_test_config(self):
        try:
            device_addr = int(self.device_addr_edit.text(), 16)
            iterm_reg = int(self.iterm_reg_edit.text(), 16)
        except ValueError:
            device_addr = 0
            iterm_reg = 0
        return {
            "device_addr": device_addr,
            "iterm_reg": iterm_reg,
            "iic_width": self.iic_width_combo.currentData(),
            "measure_channel": int(self.measure_channel_combo.currentText()),
            "settle_time_ms": self.settle_time_spin.value(),
            "tolerance_pct": self.tolerance_spin.value(),
        }

    def clear_results(self):
        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0
        self.total_card["value"].setText("0")
        self.pass_card["value"].setText("0")
        self.fail_card["value"].setText("0")
        self.result_log.clear()

    def update_test_result(self, result):
        if "total" in result:
            self.total_card["value"].setText(str(result["total"]))
        if "pass" in result:
            self.pass_card["value"].setText(str(result["pass"]))
        if "fail" in result:
            self.fail_card["value"].setText(str(result["fail"]))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ItermTestUI()
    window.setWindowTitle("Iterm Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())
