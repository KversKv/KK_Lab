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
    QTextEdit, QProgressBar, QSizePolicy, QScrollArea,
    QApplication, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer, QMargins
from PySide6.QtGui import QFont
import time
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from i2c_interface_x64 import I2CInterface
from Bes_I2CIO_Interface import I2CSpeedMode, I2CWidthFlag

try:
    from PySide6.QtCharts import (
        QChart, QChartView, QLineSeries, QValueAxis
    )
    from PySide6.QtGui import QPainter, QColor, QPen
    HAS_QTCHARTS = True
except Exception:
    HAS_QTCHARTS = False


class _RegulationVoltageWorker(QObject):
    log_message = Signal(str)
    progress = Signal(int)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    result_update = Signal(dict)
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
            reg_addr = self._cfg["reg_addr"]
            msb = self._cfg["msb"]
            lsb = self._cfg["lsb"]
            min_code = self._cfg["min_code"]
            max_code = self._cfg["max_code"]
            iic_width = self._cfg["iic_width"]
            meter_ch = int(self._cfg["vmeter_channel"].replace("CH ", ""))
            tolerance_pct = self._cfg.get("tolerance_pct", 5.0)
            base_voltage = self._cfg.get("base_voltage", 4.2)
            step_mv = self._cfg.get("step_mv", 16.0)

            i2c = I2CInterface()
            self._i2c = i2c

            self._n6705c.set_mode(meter_ch, "VMETer")

            bit_count = msb - lsb + 1
            mask = (1 << bit_count) - 1

            default_reg = i2c.read(device_addr, reg_addr, iic_width)
            data_base = default_reg & (~(mask << lsb))

            max_code = min(max_code, mask)
            min_code = max(min_code, 0)

            total_points = max_code - min_code + 1
            if total_points <= 0:
                self.log_message.emit("[ERROR] Invalid code range (min >= max).")
                self.test_finished.emit(False)
                return

            self.log_message.emit(
                f"[TEST] Device=0x{device_addr:02X}, Reg=0x{reg_addr:02X}, "
                f"MSB={msb}, LSB={lsb}"
            )
            self.log_message.emit(
                f"[TEST] Code range: 0x{min_code:X} ~ 0x{max_code:X} ({total_points} points)"
            )
            self.log_message.emit(
                f"[TEST] Base voltage={base_voltage}V, Step={step_mv}mV, Tolerance={tolerance_pct}%"
            )

            hex_width = len(f"{max_code:X}")

            self.chart_clear.emit()

            default_measured = self._n6705c.measure_voltage(meter_ch)
            default_code = (default_reg >> lsb) & mask
            self.log_message.emit(
                f"[TEST] Default value: {default_measured:.4f}V (0x{default_code:X})"
            )

            measurements = []
            codes = []
            pass_count = 0
            fail_count = 0

            settle_start = time.time()
            write_reg = data_base | (min_code << lsb)
            i2c.write(device_addr, reg_addr, write_reg, iic_width)
            self.log_message.emit(
                f"[TEST] Setting min_code=0x{min_code:X}, waiting for output to stabilize..."
            )

            recent_values = []
            while True:
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user during stabilization.")
                    self.test_finished.emit(False)
                    return
                v = self._n6705c.measure_voltage(meter_ch)
                recent_values.append(v)
                if len(recent_values) >= 3:
                    last3 = recent_values[-3:]
                    if (max(last3) - min(last3)) <= 0.005:
                        break
                time.sleep(0.05)

            time.sleep(0.1)
            settle_elapsed_ms = (time.time() - settle_start) * 1000.0
            self.log_message.emit(
                f"[TEST] Wait for mincode output cost: {settle_elapsed_ms:.0f}ms"
            )

            code = min_code
            while code <= max_code:
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user.")
                    break

                write_reg = data_base | (code << lsb)
                i2c.write(device_addr, reg_addr, write_reg, iic_width)
                time.sleep(0.05)

                measured = self._n6705c.measure_voltage(meter_ch)

                measurements.append(measured)
                codes.append(code)

                expected_v = base_voltage + (code - min_code) * step_mv / 1000.0
                error_pct = abs(measured - expected_v) / expected_v * 100.0 if expected_v != 0 else 0.0
                result = "PASS" if error_pct <= tolerance_pct else "FAIL"

                if result == "PASS":
                    pass_count += 1
                else:
                    fail_count += 1

                self.chart_point.emit(float(code), measured)

                self.log_message.emit(
                    f"[MEAS] Code=0x{code:0{hex_width}X}  Expected={expected_v:>8.4f}V  "
                    f"Measured={measured:>8.4f}V  Error={error_pct:.2f}%  [{result}]"
                )

                idx = code - min_code
                pct = int((idx + 1) / total_points * 100)

                result_dict = {
                    "progress": pct,
                    "default_value": default_measured,
                    "default_code": default_code,
                    "total": len(measurements),
                    "pass_count": pass_count,
                    "fail_count": fail_count,
                }
                if len(measurements) >= 1:
                    result_dict["min_value"] = min(measurements)
                    result_dict["max_value"] = max(measurements)
                if len(measurements) >= 2:
                    avg_step = (measurements[-1] - measurements[0]) / (len(measurements) - 1) * 1000.0
                    result_dict["step_value"] = avg_step

                    full_scale = measurements[-1] - measurements[0]
                    if abs(full_scale) > 1e-9:
                        n = len(measurements)
                        ideal_step = full_scale / (n - 1)
                        max_dev = 0.0
                        for j in range(n):
                            ideal_v = measurements[0] + ideal_step * j
                            dev = abs(measurements[j] - ideal_v)
                            if dev > max_dev:
                                max_dev = dev
                        result_dict["linearity"] = max_dev / abs(full_scale) * 100.0
                    else:
                        result_dict["linearity"] = 0.0

                self.result_update.emit(result_dict)
                code += 1

            i2c.write(device_addr, reg_addr, default_reg, iic_width)
            self.log_message.emit("[TEST] Register restored to default value.")

            self.log_message.emit(
                f"[TEST] Regulation Voltage test complete. "
                f"PASS={pass_count}, FAIL={fail_count}, Total={len(measurements)}"
            )
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


class RegulationVoltageTestUI(QWidget):
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
            QPushButton#exportBtn {
                min-height: 28px;
                padding: 4px 12px;
                border-radius: 8px;
                background-color: #16284f;
                color: #dfe8ff;
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

        self.page_title = QLabel("\u26a1 Regulation Voltage Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Traverse charger regulation voltage register codes and verify output voltage accuracy.")
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

        self.channel_config_card = CardFrame("\u2637 TEST CHANNEL CONFIG")
        self._build_channel_config_card()
        left_layout.addWidget(self.channel_config_card)

        self.config_card = CardFrame("\u21c4 REGISTER RANGE")
        self._build_config_card()
        left_layout.addWidget(self.config_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("\u25b6 START TEST")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_layout.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("\u25a0 STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()

        content_layout.addWidget(self.left_panel)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartContainer")
        chart_outer_layout = QVBoxLayout(self.chart_frame)
        chart_outer_layout.setContentsMargins(16, 16, 16, 16)
        chart_outer_layout.setSpacing(10)

        chart_header_layout = QHBoxLayout()
        self.chart_title = QLabel("\u223f Regulation Voltage Linearity")
        self.chart_title.setObjectName("sectionTitle")
        chart_header_layout.addWidget(self.chart_title)
        chart_header_layout.addStretch()

        self.export_result_btn = QPushButton("\u21e9 Export CSV")
        self.export_result_btn.setObjectName("exportBtn")
        chart_header_layout.addWidget(self.export_result_btn)

        chart_outer_layout.addLayout(chart_header_layout)

        self.chart_widget = self._create_chart_widget()
        chart_outer_layout.addWidget(self.chart_widget, 1)

        stat_layout = QHBoxLayout()
        stat_layout.setSpacing(10)

        self.default_value_card = self._create_mini_stat("Default", "---")
        self.min_value_card = self._create_mini_stat("Min", "---")
        self.max_value_card = self._create_mini_stat("Max", "---")
        self.step_value_card = self._create_mini_stat("Step", "---")
        self.linearity_card = self._create_mini_stat("Linearity", "---")
        self.pass_card = self._create_mini_stat("PASS", "0")
        self.fail_card = self._create_mini_stat("FAIL", "0")

        stat_layout.addWidget(self.default_value_card["frame"])
        stat_layout.addWidget(self.min_value_card["frame"])
        stat_layout.addWidget(self.max_value_card["frame"])
        stat_layout.addWidget(self.step_value_card["frame"])
        stat_layout.addWidget(self.linearity_card["frame"])
        stat_layout.addWidget(self.pass_card["frame"])
        stat_layout.addWidget(self.fail_card["frame"])

        chart_outer_layout.addLayout(stat_layout)
        right_layout.addWidget(self.chart_frame, 4)

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

    def _build_channel_config_card(self):
        layout = self.channel_config_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        vmeter_label = QLabel("Vbat Channel")
        vmeter_label.setObjectName("fieldLabel")

        self.vmeter_channel_combo = DarkComboBox()
        self.vmeter_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])

        acin_label = QLabel("AC_IN Channel")
        acin_label.setObjectName("fieldLabel")

        self.acin_channel_combo = DarkComboBox()
        self.acin_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])

        grid.addWidget(vmeter_label, 0, 0)
        grid.addWidget(self.vmeter_channel_combo, 0, 1)
        grid.addWidget(acin_label, 1, 0)
        grid.addWidget(self.acin_channel_combo, 1, 1)

        layout.addLayout(grid)

    def _build_config_card(self):
        layout = self.config_card.main_layout

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
        self.device_addr_edit = QLineEdit("0x1A")

        lbl_reg_addr = QLabel("Reg Addr (Hex)")
        lbl_reg_addr.setObjectName("fieldLabel")
        self.reg_addr_edit = QLineEdit("0x0004")

        lbl_msb = QLabel("MSB")
        lbl_msb.setObjectName("fieldLabel")
        self.msb_edit = QLineEdit("7")

        lbl_lsb = QLabel("LSB")
        lbl_lsb.setObjectName("fieldLabel")
        self.lsb_edit = QLineEdit("2")

        lbl_min_code = QLabel("Min Code")
        lbl_min_code.setObjectName("fieldLabel")
        self.min_code_edit = QLineEdit("0x00")

        lbl_max_code = QLabel("Max Code")
        lbl_max_code.setObjectName("fieldLabel")
        self.max_code_edit = QLineEdit("0x3F")

        grid.addWidget(lbl_width, 0, 0)
        grid.addWidget(self.iic_width_combo, 0, 1)
        grid.addWidget(lbl_dev, 1, 0)
        grid.addWidget(self.device_addr_edit, 1, 1)
        grid.addWidget(lbl_reg_addr, 2, 0)
        grid.addWidget(self.reg_addr_edit, 2, 1)
        grid.addWidget(lbl_msb, 3, 0)
        grid.addWidget(self.msb_edit, 3, 1)
        grid.addWidget(lbl_lsb, 4, 0)
        grid.addWidget(self.lsb_edit, 4, 1)
        grid.addWidget(lbl_min_code, 5, 0)
        grid.addWidget(self.min_code_edit, 5, 1)
        grid.addWidget(lbl_max_code, 6, 0)
        grid.addWidget(self.max_code_edit, 6, 1)

        layout.addLayout(grid)

    def _create_chart_widget(self):
        if HAS_QTCHARTS:
            self.series = QLineSeries()
            pen = QPen(QColor("#00d6a2"))
            pen.setWidth(2)
            self.series.setPen(pen)

            chart = QChart()
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(True)
            chart.setPlotAreaBackgroundBrush(QColor("#09142e"))
            chart.legend().hide()
            chart.addSeries(self.series)
            chart.setMargins(QMargins(0, 0, 0, 0))

            self.axis_x = QValueAxis()
            self.axis_x.setRange(0, 63)
            self.axis_x.setTickCount(9)
            self.axis_x.setLabelFormat("%d")
            self.axis_x.setTitleText("Register Code")
            self.axis_x.setLabelsColor(QColor("#9fc0ef"))
            self.axis_x.setTitleBrush(QColor("#9fc0ef"))
            self.axis_x.setGridLineColor(QColor("#2a3f6a"))

            self.axis_y = QValueAxis()
            self.axis_y.setRange(3.0, 5.0)
            self.axis_y.setTickCount(9)
            self.axis_y.setTitleText("Regulation Voltage (V)")
            self.axis_y.setLabelsColor(QColor("#9fc0ef"))
            self.axis_y.setTitleBrush(QColor("#9fc0ef"))
            self.axis_y.setGridLineColor(QColor("#2a3f6a"))

            chart.addAxis(self.axis_x, Qt.AlignBottom)
            chart.addAxis(self.axis_y, Qt.AlignLeft)
            self.series.attachAxis(self.axis_x)
            self.series.attachAxis(self.axis_y)

            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.Antialiasing)
            chart_view.setStyleSheet("background: transparent; border: none;")
            return chart_view

        placeholder = QFrame()
        placeholder.setStyleSheet("""
            QFrame {
                background-color: #09142e;
                border: 1px solid #1b315f;
                border-radius: 10px;
            }
        """)
        v = QVBoxLayout(placeholder)
        label = QLabel("Regulation Voltage Chart")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#7da2d6; font-size:14px; font-weight:600; background: transparent;")
        v.addWidget(label)
        return placeholder

    def _create_mini_stat(self, label_text, value_text):
        frame = QFrame()
        frame.setObjectName("miniStatCard")
        frame.setMinimumHeight(68)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setObjectName("metricLabel")
        val = QLabel(value_text)
        val.setObjectName("metricValue")
        lay.addWidget(lbl)
        lay.addWidget(val)
        return {"frame": frame, "label": lbl, "value": val}

    def _init_ui_elements(self):
        self._update_connect_button_state(False)
        self.append_log("[SYSTEM] Regulation Voltage Test ready.")
        self.set_progress(0)

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)
        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        self.export_result_btn.clicked.connect(self._on_export_csv)
        self.msb_edit.textChanged.connect(self._update_code_range)
        self.lsb_edit.textChanged.connect(self._update_code_range)

    def _update_code_range(self):
        try:
            msb = int(self.msb_edit.text())
            lsb = int(self.lsb_edit.text())
        except ValueError:
            return
        if msb < lsb:
            return
        bit_count = msb - lsb + 1
        max_val = (1 << bit_count) - 1
        self.min_code_edit.setText("0x0")
        self.max_code_edit.setText(f"0x{max_val:X}")

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        self.connect_btn.setProperty("connected", "true" if connected else "false")
        self.connect_btn.setText("\u21b2  Disconnect" if connected else "\U0001f517  Connect")

        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.connect_btn.update()

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

        self.clear_results()
        self._export_data = []

        try:
            device_addr = int(self.device_addr_edit.text(), 16)
            reg_addr = int(self.reg_addr_edit.text(), 16)
            msb = int(self.msb_edit.text())
            lsb = int(self.lsb_edit.text())
            min_code = int(self.min_code_edit.text(), 16)
            max_code = int(self.max_code_edit.text(), 16)
        except ValueError:
            self.append_log("[ERROR] Invalid hex address or parameter.")
            return

        iic_width = self.iic_width_combo.currentData()

        if HAS_QTCHARTS and hasattr(self, 'axis_y'):
            self.axis_y.setTitleText("Regulation Voltage (V)")

        config = {
            "vmeter_channel": self.vmeter_channel_combo.currentText(),
            "device_addr": device_addr,
            "reg_addr": reg_addr,
            "msb": msb,
            "lsb": lsb,
            "min_code": min_code,
            "max_code": max_code,
            "iic_width": iic_width,
        }

        self.set_test_running(True)
        self.set_progress(0)

        self.test_thread = QThread()
        self.test_worker = _RegulationVoltageWorker(self.n6705c, config)
        self.test_worker.moveToThread(self.test_thread)

        self.test_worker.log_message.connect(self.append_log)
        self.test_worker.progress.connect(self.set_progress)
        self.test_worker.chart_point.connect(self._update_chart_point)
        self.test_worker.chart_clear.connect(self._on_chart_clear)
        self.test_worker.result_update.connect(self._on_result_update)
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_thread.started.connect(self.test_worker.run)

        self.test_thread.start()

    def _on_stop_test(self):
        if self.test_worker is not None:
            self.test_worker.request_stop()
        self.append_log("[TEST] Stop requested...")

    def _on_chart_clear(self):
        if HAS_QTCHARTS and hasattr(self, 'series'):
            self.series.clear()

    def _update_chart_point(self, reg_value, measured):
        if HAS_QTCHARTS and hasattr(self, 'series'):
            self.series.append(reg_value, measured)
            self._export_data.append((reg_value, measured))

            pts = self.series.points()
            if pts and hasattr(self, 'axis_x') and self.axis_x is not None:
                min_x = int(min(p.x() for p in pts))
                max_x = int(max(p.x() for p in pts))
                margin_x = max(int((max_x - min_x) * 0.05), 1)
                self.axis_x.setRange(max(0, min_x - margin_x), max_x + margin_x)

            if pts and hasattr(self, 'axis_y') and self.axis_y is not None:
                min_y = min(p.y() for p in pts)
                max_y = max(p.y() for p in pts)
                margin_y = max((max_y - min_y) * 0.05, 0.01)
                self.axis_y.setRange(min_y - margin_y, max_y + margin_y)

    def _on_result_update(self, result):
        if 'default_value' in result:
            code_str = f"(0x{result['default_code']:X})" if 'default_code' in result else ""
            self.default_value_card["value"].setText(f"{result['default_value']:.4f}V {code_str}")
        if 'min_value' in result:
            self.min_value_card["value"].setText(f"{result['min_value']:.4f} V")
        if 'max_value' in result:
            self.max_value_card["value"].setText(f"{result['max_value']:.4f} V")
        if 'step_value' in result:
            self.step_value_card["value"].setText(f"{result['step_value']:.4f} mV")
        if 'linearity' in result:
            self.linearity_card["value"].setText(f"{result['linearity']:.4f}%")
        if 'pass_count' in result:
            self.pass_card["value"].setText(str(result['pass_count']))
        if 'fail_count' in result:
            self.fail_card["value"].setText(str(result['fail_count']))
        if 'progress' in result:
            self.set_progress(result['progress'])

    def _on_test_finished(self, success):
        self.set_test_running(False)
        if success:
            self.append_log("[TEST] Regulation Voltage test completed.")
        else:
            self.append_log("[TEST] Regulation Voltage test ended with errors.")
        if self.test_thread is not None:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_thread = None
            self.test_worker = None

    def _on_clear_log(self):
        self.log_edit.clear()

    def _on_export_csv(self):
        if not self._export_data:
            self.append_log("[EXPORT] No data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Code,Measured_Voltage\n")
                for code_val, measured_val in self._export_data:
                    f.write(f"{int(code_val)},{measured_val:.6f}\n")
            self.append_log(f"[EXPORT] Data exported to {path}")
        except Exception as e:
            self.append_log(f"[ERROR] Export failed: {e}")

    def set_test_running(self, running):
        self.is_test_running = running
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(running)
        if running:
            self.start_test_btn.setText("\u25a0 STOP")
            self.start_test_btn.setObjectName("stopBtn")
        else:
            self.start_test_btn.setText("\u25b6 START TEST")
            self.start_test_btn.setObjectName("primaryStartBtn")
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.start_test_btn.update()
        self.device_addr_edit.setEnabled(not running)
        self.reg_addr_edit.setEnabled(not running)
        self.msb_edit.setEnabled(not running)
        self.lsb_edit.setEnabled(not running)
        self.min_code_edit.setEnabled(not running)
        self.max_code_edit.setEnabled(not running)
        self.iic_width_combo.setEnabled(not running)
        self.vmeter_channel_combo.setEnabled(not running)
        self.acin_channel_combo.setEnabled(not running)
        self.visa_resource_combo.setEnabled(not running)
        self.search_btn.setEnabled(not running)
        self.connect_btn.setEnabled(not running)

        if running:
            self.set_system_status("\u25cf Running")
            self.append_log("[TEST] Starting Regulation Voltage Test Sequence...")
        else:
            self.set_system_status("\u25cf Ready" if not self.is_connected else "\u25cf Connected")

    def set_progress(self, value):
        value = max(0, min(100, int(value)))
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
        self.log_edit.verticalScrollBar().setValue(self.log_edit.verticalScrollBar().maximum())

    def get_test_config(self):
        try:
            device_addr = int(self.device_addr_edit.text(), 16)
            reg_addr = int(self.reg_addr_edit.text(), 16)
            msb = int(self.msb_edit.text())
            lsb = int(self.lsb_edit.text())
            min_code = int(self.min_code_edit.text(), 16)
            max_code = int(self.max_code_edit.text(), 16)
        except ValueError:
            device_addr = 0
            reg_addr = 0
            msb = 7
            lsb = 0
            min_code = 0
            max_code = 0x3F
        return {
            "vmeter_channel": self.vmeter_channel_combo.currentText(),
            "device_addr": device_addr,
            "reg_addr": reg_addr,
            "msb": msb,
            "lsb": lsb,
            "min_code": min_code,
            "max_code": max_code,
            "iic_width": self.iic_width_combo.currentData(),
        }

    def clear_results(self):
        self.default_value_card["value"].setText("---")
        self.min_value_card["value"].setText("---")
        self.max_value_card["value"].setText("---")
        self.step_value_card["value"].setText("---")
        self.linearity_card["value"].setText("---")
        self.pass_card["value"].setText("0")
        self.fail_card["value"].setText("0")
        self.set_progress(0)

    def update_test_result(self, result):
        self._on_result_update(result)

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
    window = RegulationVoltageTestUI()
    window.setWindowTitle("Regulation Voltage Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())