#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ui.widgets.dark_combobox import DarkComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGridLayout, QSpinBox, QFrame,
    QTextEdit, QProgressBar, QSizePolicy,
    QApplication, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtGui import QFont
from pathlib import Path
import time

i2c_lib_path = Path(__file__).parent.parent.parent.parent / "lib" / "i2c"
sys.path.insert(0, str(i2c_lib_path))

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
    poll_done = Signal()
    error = Signal(str)

    def __init__(self, i2c, config, register_map):
        super().__init__()
        self._i2c = i2c
        self._cfg = config
        self._register_map = register_map
        self._stop_flag = False
        self._continuous = config.get("continuous", False)
        self._poll_interval = config.get("poll_interval_ms", 500)

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        try:
            device_addr = self._cfg["device_addr"]
            iic_width = self._cfg["iic_width"]

            while not self._stop_flag:
                results = {}
                for name, reg_info in self._register_map.items():
                    if self._stop_flag:
                        break
                    try:
                        raw = self._i2c.read(device_addr, reg_info["addr"], iic_width)
                        bits_str = reg_info["bits"]
                        if ":" in bits_str:
                            hi, lo = [int(x) for x in bits_str.split(":")]
                            mask = ((1 << (hi - lo + 1)) - 1) << lo
                            val = (raw & mask) >> lo
                        else:
                            bit_pos = int(bits_str)
                            val = (raw >> bit_pos) & 1
                        results[name] = {
                            "raw": raw,
                            "value": val,
                            "desc": reg_info["desc"],
                            "addr": reg_info["addr"],
                            "bits": bits_str,
                        }
                    except Exception as e:
                        self.log_message.emit(f"[ERROR] Read {name}: {e}")
                        results[name] = {"raw": 0, "value": -1, "desc": reg_info["desc"], "addr": reg_info["addr"], "bits": bits_str}

                self.status_update.emit(results)
                self.poll_done.emit()

                if not self._continuous:
                    break

                for _ in range(self._poll_interval // 50):
                    if self._stop_flag:
                        break
                    time.sleep(0.05)

            self.log_message.emit("[TEST] Status register polling stopped.")
        except Exception as e:
            self.error.emit(str(e))


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.i2c = None
        self.is_test_running = False
        self.test_thread = None
        self.test_worker = None
        self.status_labels = {}

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()

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
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QTextEdit:focus {
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
            QCheckBox {
                color: #dbe7ff;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #27406f;
                border-radius: 4px;
                background-color: #0a1733;
            }
            QCheckBox::indicator:checked {
                background-color: #5b5cf6;
                border: 1px solid #7872ff;
            }
        """)

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

        self.i2c_card = CardFrame("🔌 I2C CONNECTION")
        self._build_i2c_card()
        left_layout.addWidget(self.i2c_card)

        self.poll_card = CardFrame("⏱ POLL SETTINGS")
        self._build_poll_card()
        left_layout.addWidget(self.poll_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("▶ START POLL")
        self.start_test_btn.setObjectName("primaryStartBtn")

        self.stop_test_btn = QPushButton("■ STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.setEnabled(False)

        left_layout.addWidget(self.start_test_btn)
        left_layout.addWidget(self.stop_test_btn)

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

        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        reg_header.addWidget(self.system_status_label)
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

    def _build_i2c_card(self):
        layout = self.i2c_card.main_layout

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_dev = QLabel("Device Addr (hex)")
        lbl_dev.setObjectName("fieldLabel")
        self.device_addr_edit = QLineEdit("0x6A")

        lbl_width = QLabel("IIC Width")
        lbl_width.setObjectName("fieldLabel")
        self.iic_width_combo = DarkComboBox()
        self.iic_width_combo.addItems(["8bit", "16bit"])

        grid.addWidget(lbl_dev, 0, 0)
        grid.addWidget(self.device_addr_edit, 0, 1)
        grid.addWidget(lbl_width, 1, 0)
        grid.addWidget(self.iic_width_combo, 1, 1)

        layout.addLayout(grid)

        self.i2c_connect_btn = QPushButton("Connect I2C")
        self.i2c_connect_btn.setObjectName("primaryStartBtn")
        layout.addWidget(self.i2c_connect_btn)

        self.i2c_status_label = QLabel("● Disconnected")
        self.i2c_status_label.setObjectName("statusErr")
        layout.addWidget(self.i2c_status_label)

    def _build_poll_card(self):
        layout = self.poll_card.main_layout

        self.continuous_check = QCheckBox("Continuous Polling")
        self.continuous_check.setChecked(True)
        layout.addWidget(self.continuous_check)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_interval = QLabel("Poll Interval (ms)")
        lbl_interval.setObjectName("fieldLabel")
        self.poll_interval_spin = QSpinBox()
        self.poll_interval_spin.setRange(100, 10000)
        self.poll_interval_spin.setValue(500)
        self.poll_interval_spin.setSingleStep(100)

        grid.addWidget(lbl_interval, 0, 0)
        grid.addWidget(self.poll_interval_spin, 0, 1)

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
        self.append_log("[SYSTEM] Status Register Test ready.")

    def _bind_signals(self):
        self.i2c_connect_btn.clicked.connect(self._on_i2c_connect)
        self.start_test_btn.clicked.connect(self._on_start_test)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.clear_log_btn.clicked.connect(self._on_clear_log)

    def _on_i2c_connect(self):
        if self.i2c is not None:
            self.i2c = None
            self.i2c_status_label.setText("● Disconnected")
            self.i2c_status_label.setObjectName("statusErr")
            self.i2c_status_label.style().unpolish(self.i2c_status_label)
            self.i2c_status_label.style().polish(self.i2c_status_label)
            self.i2c_connect_btn.setText("Connect I2C")
            self.append_log("[I2C] Disconnected.")
            return

        try:
            self.i2c = I2CInterface()
            self.i2c_status_label.setText("● Connected")
            self.i2c_status_label.setObjectName("statusOk")
            self.i2c_status_label.style().unpolish(self.i2c_status_label)
            self.i2c_status_label.style().polish(self.i2c_status_label)
            self.i2c_connect_btn.setText("Disconnect I2C")
            self.append_log("[I2C] Connected successfully.")
        except Exception as e:
            self.append_log(f"[ERROR] I2C connect failed: {e}")

    def _on_start_test(self):
        if self.i2c is None:
            self.append_log("[ERROR] I2C not connected.")
            return
        if self.is_test_running:
            return

        try:
            device_addr = int(self.device_addr_edit.text(), 16)
        except ValueError:
            self.append_log("[ERROR] Invalid device address.")
            return

        width_text = self.iic_width_combo.currentText()
        iic_width = I2CWidthFlag.IIC_8BIT if width_text == "8bit" else I2CWidthFlag.IIC_16BIT

        config = {
            "device_addr": device_addr,
            "iic_width": iic_width,
            "continuous": self.continuous_check.isChecked(),
            "poll_interval_ms": self.poll_interval_spin.value(),
        }

        self.set_test_running(True)

        self.test_thread = QThread()
        self.test_worker = _StatusPollWorker(self.i2c, config, STATUS_REGISTER_MAP)
        self.test_worker.moveToThread(self.test_thread)

        self.test_worker.log_message.connect(self.append_log)
        self.test_worker.status_update.connect(self._on_status_update)
        self.test_worker.poll_done.connect(self._on_poll_done)
        self.test_worker.error.connect(lambda e: self.append_log(f"[ERROR] {e}"))
        self.test_thread.started.connect(self.test_worker.run)

        self.test_thread.start()
        self.append_log("[TEST] Status register polling started.")

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

    def _on_poll_done(self):
        if not self.continuous_check.isChecked():
            self._cleanup_thread()
            self.append_log("[TEST] Single poll completed.")

    def _on_clear_log(self):
        self.log_edit.clear()

    def set_test_running(self, running):
        self.is_test_running = running
        self.start_test_btn.setEnabled(not running)
        self.stop_test_btn.setEnabled(running)
        self.device_addr_edit.setEnabled(not running)
        self.iic_width_combo.setEnabled(not running)
        self.i2c_connect_btn.setEnabled(not running)
        self.continuous_check.setEnabled(not running)
        self.poll_interval_spin.setEnabled(not running)

        if running:
            self.set_system_status("● Polling")
        else:
            self.set_system_status("● Ready")

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Polling" in status or "Running" in status:
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
        return {
            "device_addr": device_addr,
            "iic_width": self.iic_width_combo.currentText(),
            "continuous": self.continuous_check.isChecked(),
            "poll_interval_ms": self.poll_interval_spin.value(),
        }

    def clear_results(self):
        for name in self.status_labels:
            self.status_labels[name]["value_label"].setText("---")
            self.status_labels[name]["value_label"].setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700; background-color: transparent; border: none;")

    def update_test_result(self, result):
        self._on_status_update(result)

    def _sync_from_top(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = StatusRegisterTestUI()
    window.setWindowTitle("Status Register Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())
