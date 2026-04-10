#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ui.widgets.dark_combobox import DarkComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGridLayout, QSpinBox, QDoubleSpinBox, QFrame,
    QTextEdit, QProgressBar, QSizePolicy, QScrollArea,
    QApplication, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtGui import QFont
from pathlib import Path
import time

i2c_lib_path = Path(__file__).parent.parent.parent.parent / "lib" / "i2c"
sys.path.insert(0, str(i2c_lib_path))

from i2c_interface_x64 import I2CInterface
from Bes_I2CIO_Interface import I2CSpeedMode, I2CWidthFlag


class _ConfigTraverseWorker(QObject):
    log_message = Signal(str)
    progress = Signal(int)
    result_row = Signal(dict)
    test_finished = Signal(bool)

    def __init__(self, i2c, config):
        super().__init__()
        self._i2c = i2c
        self._cfg = config
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        try:
            device_addr = self._cfg["device_addr"]
            reg_start = self._cfg["reg_start"]
            reg_end = self._cfg["reg_end"]
            iic_width = self._cfg["iic_width"]

            total = reg_end - reg_start + 1
            if total <= 0:
                self.log_message.emit("[ERROR] Invalid register range.")
                self.test_finished.emit(False)
                return

            self.log_message.emit(f"[TEST] Traversing registers 0x{reg_start:02X} ~ 0x{reg_end:02X} on device 0x{device_addr:02X}")

            for i, reg in enumerate(range(reg_start, reg_end + 1)):
                if self._stop_flag:
                    self.log_message.emit("[TEST] Test stopped by user.")
                    break

                for bit_val in range(256):
                    if self._stop_flag:
                        break
                    try:
                        self._i2c.write(device_addr, reg, bit_val, iic_width)
                        time.sleep(0.005)
                        readback = self._i2c.read(device_addr, reg, iic_width)
                        match = "PASS" if readback == bit_val else "FAIL"
                        self.result_row.emit({
                            "reg": f"0x{reg:02X}",
                            "write": f"0x{bit_val:02X}",
                            "read": f"0x{readback:02X}",
                            "result": match
                        })
                        if match == "FAIL":
                            self.log_message.emit(
                                f"[FAIL] Reg 0x{reg:02X}: wrote 0x{bit_val:02X}, read 0x{readback:02X}"
                            )
                    except Exception as e:
                        self.log_message.emit(f"[ERROR] Reg 0x{reg:02X} val 0x{bit_val:02X}: {e}")

                pct = int((i + 1) / total * 100)
                self.progress.emit(pct)
                self.log_message.emit(f"[TEST] Register 0x{reg:02X} traverse complete.")

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


class ConfigTraverseTestUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.i2c = None
        self.is_test_running = False
        self.test_thread = None
        self.test_worker = None
        self._export_data = []

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

        self.page_title = QLabel("⚙ Config Traverse Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Traverse all config register values and verify read-back on the Charger IC.")
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

        self.config_card = CardFrame("⇄ REGISTER RANGE")
        self._build_config_card()
        left_layout.addWidget(self.config_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("▶ START TRAVERSE")
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

        stat_frame = QFrame()
        stat_frame.setObjectName("chartContainer")
        stat_outer = QVBoxLayout(stat_frame)
        stat_outer.setContentsMargins(16, 16, 16, 16)
        stat_outer.setSpacing(10)

        stat_header = QHBoxLayout()
        stat_title = QLabel("📊 Traverse Results")
        stat_title.setObjectName("sectionTitle")
        stat_header.addWidget(stat_title)
        stat_header.addStretch()

        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        stat_header.addWidget(self.system_status_label)

        stat_outer.addLayout(stat_header)

        mini_stat_layout = QHBoxLayout()
        self.total_card = self._create_mini_stat("Total Regs", "0")
        self.pass_card = self._create_mini_stat("PASS", "0")
        self.fail_card = self._create_mini_stat("FAIL", "0")
        mini_stat_layout.addWidget(self.total_card["frame"])
        mini_stat_layout.addWidget(self.pass_card["frame"])
        mini_stat_layout.addWidget(self.fail_card["frame"])
        stat_outer.addLayout(mini_stat_layout)

        self.result_log = QTextEdit()
        self.result_log.setObjectName("logEdit")
        self.result_log.setReadOnly(True)
        stat_outer.addWidget(self.result_log, 1)

        right_layout.addWidget(stat_frame, 4)

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

    def _build_config_card(self):
        layout = self.config_card.main_layout

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_start = QLabel("Start Reg (hex)")
        lbl_start.setObjectName("fieldLabel")
        self.reg_start_edit = QLineEdit("0x00")

        lbl_end = QLabel("End Reg (hex)")
        lbl_end.setObjectName("fieldLabel")
        self.reg_end_edit = QLineEdit("0x1F")

        grid.addWidget(lbl_start, 0, 0)
        grid.addWidget(self.reg_start_edit, 0, 1)
        grid.addWidget(lbl_end, 1, 0)
        grid.addWidget(self.reg_end_edit, 1, 1)

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
        self.append_log("[SYSTEM] Config Traverse Test ready.")
        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0

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

        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0
        self.result_log.clear()
        self._export_data = []

        try:
            device_addr = int(self.device_addr_edit.text(), 16)
            reg_start = int(self.reg_start_edit.text(), 16)
            reg_end = int(self.reg_end_edit.text(), 16)
        except ValueError:
            self.append_log("[ERROR] Invalid hex address.")
            return

        width_text = self.iic_width_combo.currentText()
        iic_width = I2CWidthFlag.IIC_8BIT if width_text == "8bit" else I2CWidthFlag.IIC_16BIT

        config = {
            "device_addr": device_addr,
            "reg_start": reg_start,
            "reg_end": reg_end,
            "iic_width": iic_width,
        }

        self.set_test_running(True)
        self.set_progress(0)

        self.test_thread = QThread()
        self.test_worker = _ConfigTraverseWorker(self.i2c, config)
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
                f"Reg {row['reg']}: W={row['write']} R={row['read']}  [{row['result']}]"
            )
            self._export_data.append(row)

        self.total_card["value"].setText(str(self._total_count))
        self.pass_card["value"].setText(str(self._pass_count))
        self.fail_card["value"].setText(str(self._fail_count))

    def _on_test_finished(self, success):
        self.set_test_running(False)
        if success:
            self.append_log("[TEST] Config traverse test completed.")
        else:
            self.append_log("[TEST] Config traverse test ended with errors.")
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
        self.reg_start_edit.setEnabled(not running)
        self.reg_end_edit.setEnabled(not running)
        self.iic_width_combo.setEnabled(not running)
        self.i2c_connect_btn.setEnabled(not running)

        if running:
            self.set_system_status("● Running")
        else:
            self.set_system_status("● Ready")

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}% Complete")

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Running" in status:
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
            reg_start = int(self.reg_start_edit.text(), 16)
            reg_end = int(self.reg_end_edit.text(), 16)
        except ValueError:
            device_addr = 0
            reg_start = 0
            reg_end = 0
        return {
            "device_addr": device_addr,
            "reg_start": reg_start,
            "reg_end": reg_end,
            "iic_width": self.iic_width_combo.currentText(),
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

    def _sync_from_top(self):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ConfigTraverseTestUI()
    window.setWindowTitle("Config Traverse Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())
