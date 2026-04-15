#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU Output Voltage测试UI组件
暗色卡片式重构版本（PySide6）
"""

import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "lib", "i2c"))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QFrame, QTextEdit,
    QSizePolicy, QProgressBar
)
from ui.widgets.dark_combobox import DarkComboBox
from ui.styles.button import SpinningSearchButton, update_connect_button_state
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QMargins
from PySide6.QtGui import QFont
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from i2c_interface_x64 import I2CInterface
from ui.styles import SCROLLBAR_STYLE
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C, MockI2C

try:
    from PySide6.QtCharts import (
        QChart, QChartView, QLineSeries, QValueAxis
    )
    from PySide6.QtGui import QPainter, QColor, QPen
    HAS_QTCHARTS = True
except Exception:
    HAS_QTCHARTS = False


class OutputVoltageTestThread(QThread):
    log_message = Signal(str)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    result_update = Signal(dict)
    test_finished = Signal()

    def __init__(self, n6705c, config, debug_flag=False):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._debug = debug_flag
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        try:
            device_addr = int(self._cfg["device_addr"], 16)
            reg_addr = int(self._cfg["reg_addr"], 16)
            msb = self._cfg["msb"]
            lsb = self._cfg["lsb"]
            width_flag = int(self._cfg["width_flag"])
            min_code = int(self._cfg["min_code"], 16)
            max_code = int(self._cfg["max_code"], 16)
            vmeter_ch = int(self._cfg["vmeter_channel"].replace("CH ", ""))

            if self._debug:
                i2c = MockI2C()
                self.log_message.emit("[DEBUG] Using Mock I2C interface.")
            else:
                i2c = I2CInterface()

            self._n6705c.set_mode(vmeter_ch, "VMETer")

            bit_count = msb - lsb + 1
            mask = (1 << bit_count) - 1

            default_reg = i2c.read(device_addr, reg_addr, width_flag)
            data_base = default_reg & (~(mask << lsb))

            max_code = min(max_code, mask)
            min_code = max(min_code, 0)

            total_points = max_code - min_code + 1
            if total_points <= 0:
                self.log_message.emit("[ERROR] Invalid code range (min >= max).")
                return

            self.log_message.emit(f"[TEST] Device=0x{device_addr:02X}, Reg=0x{reg_addr:04X}, "
                                  f"MSB={msb}, LSB={lsb}, WidthFlag={width_flag}")
            self.log_message.emit(f"[TEST] Code range: 0x{min_code:X} ~ 0x{max_code:X} ({total_points} points)")

            hex_width = len(f"{max_code:X}")

            self.chart_clear.emit()

            sleep_time = 0.0 if self._debug else 0.05

            default_voltage = self._n6705c.measure_voltage(vmeter_ch)
            default_code = (default_reg >> lsb) & mask
            self.log_message.emit(f"[TEST] Default voltage: {default_voltage:.4f}V (0x{default_code:X})")

            voltages = []
            codes = []

            settle_start = time.time()
            write_reg = data_base | (min_code << lsb)
            i2c.write(device_addr, reg_addr, write_reg, width_flag)
            self.log_message.emit(f"[TEST] Setting min_code=0x{min_code:X}, waiting for output to stabilize...")

            recent_voltages = []
            while True:
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user during stabilization.")
                    self.test_finished.emit()
                    return
                v = self._n6705c.measure_voltage(vmeter_ch)
                recent_voltages.append(v)
                if len(recent_voltages) >= 3:
                    last3 = recent_voltages[-3:]
                    if (max(last3) - min(last3)) <= 0.005:
                        break
                time.sleep(sleep_time)

            time.sleep(0.1)
            settle_elapsed_ms = (time.time() - settle_start) * 1000.0
            self.log_message.emit(f"[TEST] Wait for mincode output cose: {settle_elapsed_ms:.0f}ms")

            code = min_code
            while code <= max_code:
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user.")
                    break

                write_reg = data_base | (code << lsb)
                i2c.write(device_addr, reg_addr, write_reg, width_flag)
                time.sleep(sleep_time)

                if self._debug and isinstance(self._n6705c, MockN6705C):
                    self._n6705c._last_expected_v = 1.0

                measured_v = self._n6705c.measure_voltage(vmeter_ch)

                voltages.append(measured_v)
                codes.append(code)

                self.chart_point.emit(float(code), measured_v)

                self.log_message.emit(
                    f"[MEAS] Code=0x{code:0{hex_width}X}  Measured={measured_v:>8.4f}V"
                )

                idx = code - min_code
                progress = int((idx + 1) / total_points * 100)

                sat_threshold = 0.001

                low_valid = 0
                for k in range(1, len(voltages)):
                    if abs(voltages[k] - voltages[k - 1]) > sat_threshold:
                        low_valid = k
                        break
                else:
                    low_valid = len(voltages) - 1

                high_valid = len(voltages) - 1
                for k in range(len(voltages) - 1, 0, -1):
                    if abs(voltages[k] - voltages[k - 1]) > sat_threshold:
                        high_valid = k - 1
                        break
                else:
                    high_valid = 0

                if high_valid <= low_valid:
                    high_valid = len(voltages) - 1
                    low_valid = 0

                valid_voltages = voltages[low_valid:high_valid + 1]
                valid_codes = codes[low_valid:high_valid + 1]

                result = {"progress": progress, "default_voltage": default_voltage, "default_code": default_code}
                if len(valid_voltages) >= 1:
                    result["min_voltage"] = min(valid_voltages)
                    result["max_voltage"] = max(valid_voltages)
                    result["valid_min_code"] = valid_codes[0]
                    result["valid_max_code"] = valid_codes[-1]
                if len(valid_voltages) >= 2:
                    avg_step = (valid_voltages[-1] - valid_voltages[0]) / (len(valid_voltages) - 1) * 1000.0
                    result["step_voltage"] = avg_step

                    full_scale = valid_voltages[-1] - valid_voltages[0]
                    if abs(full_scale) > 1e-9:
                        n = len(valid_voltages)
                        ideal_step = full_scale / (n - 1)
                        max_dev = 0.0
                        for j in range(n):
                            ideal_v = valid_voltages[0] + ideal_step * j
                            dev = abs(valid_voltages[j] - ideal_v)
                            if dev > max_dev:
                                max_dev = dev
                        result["linearity"] = max_dev / abs(full_scale) * 100.0
                    else:
                        result["linearity"] = 0.0

                self.result_update.emit(result)
                code += 1

            if len(voltages) >= 2 and not self._stop_flag:
                sat_threshold = 0.001

                low_valid = 0
                for k in range(1, len(voltages)):
                    if abs(voltages[k] - voltages[k - 1]) > sat_threshold:
                        low_valid = k
                        break

                high_valid = len(voltages) - 1
                for k in range(len(voltages) - 1, 0, -1):
                    if abs(voltages[k] - voltages[k - 1]) > sat_threshold:
                        high_valid = k - 1
                        break

                if high_valid > low_valid:
                    self.log_message.emit(
                        f"[TEST] Valid code range: 0x{codes[low_valid]:0{hex_width}X} ~ "
                        f"0x{codes[high_valid]:0{hex_width}X} "
                        f"({codes[high_valid] - codes[low_valid] + 1} effective points out of {len(voltages)} total)"
                    )

            i2c.write(device_addr, reg_addr, default_reg, width_flag)
            self.log_message.emit("[TEST] Register restored to default value.")

        except Exception as e:
            self.log_message.emit(f"[ERROR] Test failed: {e}")
        finally:
            self.test_finished.emit()


class CardFrame(QFrame):
    """卡片容器"""
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


class PMUOutputVoltageUI(QWidget):
    """PMU Output Voltage测试UI组件"""

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

            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #4f46e5;
            }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px; height: 0px; border: none;
            }

            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
                border: 1px solid #4cc9f0;
            }

            QComboBox {
                padding-right: 24px;
            }

            QComboBox::drop-down {
                border: none;
                width: 22px;
                background: transparent;
            }

            QComboBox QAbstractItemView {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                selection-background-color: #334a7d;
            }

            QComboBox QAbstractItemView::item {
                background-color: #0a1733;
                color: #eaf2ff;
                padding: 4px 8px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #1a3260;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #334a7d;
            }

            QComboBox QFrame {
                background-color: #0a1733;
                border: 1px solid #27406f;
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

            QPushButton:pressed {
                background-color: #0d1a37;
            }

            QPushButton:disabled {
                background-color: #0b1430;
                color: #5c7096;
                border: 1px solid #1a2850;
            }

            QPushButton#smallActionBtn {
                min-height: 28px;
                padding: 4px 10px;
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
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
                    stop:0 #5b5cf6,
                    stop:1 #6a38ff
                );
            }

            QPushButton#primaryStartBtn:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b6cff,
                    stop:1 #7d4cff
                );
            }

            QPushButton#stopBtn {
                background-color: #4a1020;
                border: 1px solid #d9485f;
                color: #ffd5db;
            }

            QPushButton#stopBtn:hover {
                background-color: #5a1326;
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
                color: #7ea7ff;
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
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
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # 标题区
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.page_title = QLabel("⚙ Output Voltage Linearity Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Configure and execute automated output voltage linearity validation sequences.")
        self.page_subtitle.setObjectName("pageSubtitle")

        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_subtitle)
        root_layout.addLayout(header_layout)

        # 主体区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        root_layout.addLayout(content_layout, 1)

        # 左侧
        self.left_panel = QFrame()
        self.left_panel.setObjectName("panelFrame")
        self.left_panel.setFixedWidth(320)

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(16)

        self.connection_card = CardFrame("⚡ N6705C CONNECTION")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.vmeter_card = CardFrame("☷ VMETER CHANNEL SELECTION")
        self._build_vmeter_card()
        left_layout.addWidget(self.vmeter_card)

        self.test_param_card = CardFrame("⚙ TEST PARAMETERS")
        self._build_test_param_card()
        left_layout.addWidget(self.test_param_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("▷ Start Sequence")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_layout.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("■ Stop")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()

        content_layout.addWidget(self.left_panel)

        # 右侧
        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)

        # 图表区域
        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartContainer")
        chart_outer_layout = QVBoxLayout(self.chart_frame)
        chart_outer_layout.setContentsMargins(16, 16, 16, 16)
        chart_outer_layout.setSpacing(10)

        chart_header_layout = QHBoxLayout()
        self.chart_title = QLabel("∿ Output Voltage Linearity")
        self.chart_title.setObjectName("sectionTitle")
        chart_header_layout.addWidget(self.chart_title)
        chart_header_layout.addStretch()

        self.export_result_btn = QPushButton("⇩ Export CSV")
        self.export_result_btn.setObjectName("exportBtn")
        chart_header_layout.addWidget(self.export_result_btn)

        chart_outer_layout.addLayout(chart_header_layout)

        self.chart_widget = self._create_chart_widget()
        chart_outer_layout.addWidget(self.chart_widget, 1)

        stat_layout = QHBoxLayout()
        stat_layout.setSpacing(10)

        self.default_voltage_card = self._create_mini_stat("默认值", "---")
        self.min_voltage_card = self._create_mini_stat("最小值", "---")
        self.max_voltage_card = self._create_mini_stat("最大值", "---")
        self.step_voltage_card = self._create_mini_stat("步进", "---")
        self.linearity_card = self._create_mini_stat("线性度", "---")

        stat_layout.addWidget(self.default_voltage_card["frame"])
        stat_layout.addWidget(self.min_voltage_card["frame"])
        stat_layout.addWidget(self.max_voltage_card["frame"])
        stat_layout.addWidget(self.step_voltage_card["frame"])
        stat_layout.addWidget(self.linearity_card["frame"])

        chart_outer_layout.addLayout(stat_layout)
        right_layout.addWidget(self.chart_frame, 4)

        # 日志区域
        self.log_frame = QFrame()
        self.log_frame.setObjectName("logContainer")
        log_layout = QVBoxLayout(self.log_frame)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(10)

        log_header_layout = QHBoxLayout()
        self.log_title = QLabel("›_ EXECUTION LOGS")
        self.log_title.setObjectName("sectionTitle")
        log_header_layout.addWidget(self.log_title)
        log_header_layout.addStretch()

        self.progress_text_label = QLabel("0% Complete")
        self.progress_text_label.setObjectName("fieldLabel")
        log_header_layout.addWidget(self.progress_text_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(96)
        log_header_layout.addWidget(self.progress_bar)

        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("smallActionBtn")
        log_header_layout.addWidget(self.clear_log_btn)

        log_layout.addLayout(log_header_layout)

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
        self.visa_resource_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.visa_resource_combo.setMinimumContentsLength(10)
        self.visa_resource_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
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

    def _build_vmeter_card(self):
        layout = self.vmeter_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        vmeter_label = QLabel("VMeter Channel")
        vmeter_label.setObjectName("fieldLabel")

        self.vmeter_channel_combo = DarkComboBox()
        self.vmeter_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])

        grid.addWidget(vmeter_label, 0, 0)
        grid.addWidget(self.vmeter_channel_combo, 0, 1)

        layout.addLayout(grid)

    def _build_test_param_card(self):
        layout = self.test_param_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        lbl_dev = QLabel("Device Addr")
        lbl_dev.setObjectName("fieldLabel")
        self.device_addr_edit = QLineEdit("0x27")

        lbl_reg = QLabel("Reg Addr")
        lbl_reg.setObjectName("fieldLabel")
        self.reg_addr_edit = QLineEdit("0x0135")

        lbl_msb = QLabel("MSB")
        lbl_msb.setObjectName("fieldLabel")
        self.msb_spin = QSpinBox()
        self.msb_spin.setRange(0, 255)
        self.msb_spin.setValue(7)

        lbl_lsb = QLabel("LSB")
        lbl_lsb.setObjectName("fieldLabel")
        self.lsb_spin = QSpinBox()
        self.lsb_spin.setRange(0, 255)
        self.lsb_spin.setValue(0)

        lbl_width = QLabel("Width Flag")
        lbl_width.setObjectName("fieldLabel")
        self.iic_width_flag_combo = DarkComboBox()
        self.iic_width_flag_combo.addItem("8 BIT", 0)
        self.iic_width_flag_combo.addItem("10 BIT", 1)
        self.iic_width_flag_combo.addItem("32 BIT", 2)
        self.iic_width_flag_combo.setCurrentIndex(1)

        lbl_min = QLabel("Min Code (Hex)")
        lbl_min.setObjectName("fieldLabel")
        self.min_code_edit = QLineEdit("0x0")

        lbl_max = QLabel("Max Code (Hex)")
        lbl_max.setObjectName("fieldLabel")
        self.max_code_edit = QLineEdit("0xFF")

        grid.addWidget(lbl_dev, 0, 0)
        grid.addWidget(lbl_reg, 0, 1)
        grid.addWidget(self.device_addr_edit, 1, 0)
        grid.addWidget(self.reg_addr_edit, 1, 1)

        grid.addWidget(lbl_msb, 2, 0)
        grid.addWidget(lbl_lsb, 2, 1)
        grid.addWidget(self.msb_spin, 3, 0)
        grid.addWidget(self.lsb_spin, 3, 1)

        grid.addWidget(lbl_width, 4, 0, 1, 2)
        grid.addWidget(self.iic_width_flag_combo, 5, 0, 1, 2)

        grid.addWidget(lbl_min, 6, 0)
        grid.addWidget(lbl_max, 6, 1)
        grid.addWidget(self.min_code_edit, 7, 0)
        grid.addWidget(self.max_code_edit, 7, 1)

        layout.addLayout(grid)

        # 兼容旧逻辑保留的隐藏控件
        self.iic_weight_spin = QDoubleSpinBox()
        self.iic_weight_spin.setRange(0.001, 1000.0)
        self.iic_weight_spin.setValue(10.0)
        self.iic_weight_spin.hide()

        self.output_channel_combo = DarkComboBox()
        self.output_channel_combo.addItems(["OUT1", "OUT2", "OUT3", "OUT4"])
        self.output_channel_combo.hide()

        self.set_voltage_spin = QDoubleSpinBox()
        self.set_voltage_spin.setRange(0.0, 20.0)
        self.set_voltage_spin.setValue(3.3)
        self.set_voltage_spin.hide()

        self.load_current_min_spin = QDoubleSpinBox()
        self.load_current_min_spin.setRange(0.0, 5000.0)
        self.load_current_min_spin.setValue(0.0)
        self.load_current_min_spin.hide()

        self.load_current_max_spin = QDoubleSpinBox()
        self.load_current_max_spin.setRange(0.0, 5000.0)
        self.load_current_max_spin.setValue(500.0)
        self.load_current_max_spin.hide()

        self.current_step_spin = QDoubleSpinBox()
        self.current_step_spin.setRange(1.0, 100.0)
        self.current_step_spin.setValue(50.0)
        self.current_step_spin.hide()

        self.measure_count_spin = QSpinBox()
        self.measure_count_spin.setRange(1, 100)
        self.measure_count_spin.setValue(5)
        self.measure_count_spin.hide()

        self.stabilize_time_spin = QSpinBox()
        self.stabilize_time_spin.setRange(10, 5000)
        self.stabilize_time_spin.setValue(500)
        self.stabilize_time_spin.hide()

        self.sample_interval_spin = QSpinBox()
        self.sample_interval_spin.setRange(10, 1000)
        self.sample_interval_spin.setValue(100)
        self.sample_interval_spin.hide()

        self.min_voltage_spin = QDoubleSpinBox()
        self.min_voltage_spin.setRange(0.0, 20.0)
        self.min_voltage_spin.setValue(0.6)
        self.min_voltage_spin.hide()

        self.max_voltage_spin = QDoubleSpinBox()
        self.max_voltage_spin.setRange(0.0, 20.0)
        self.max_voltage_spin.setValue(1.2)
        self.max_voltage_spin.hide()

        self.ovp_spin = QDoubleSpinBox()
        self.ovp_spin.setRange(0.0, 25.0)
        self.ovp_spin.setValue(4.0)
        self.ovp_spin.hide()

        self.save_config_btn = QPushButton("Save Config")
        self.save_config_btn.hide()

        self.load_config_btn = QPushButton("Load Config")
        self.load_config_btn.hide()

        class _HiddenCheckBox(QWidget):
            def __init__(self, checked=True):
                super().__init__()
                self._checked = checked

            def isChecked(self):
                return self._checked

            def setChecked(self, checked):
                self._checked = checked

            def setEnabled(self, enabled):
                super().setEnabled(enabled)

        self.ovp_checkbox = _HiddenCheckBox(True)
        self.ovp_checkbox.hide()

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
            self.axis_x.setRange(0, 255)
            self.axis_x.setTickCount(9)
            self.axis_x.setLabelFormat("%d")
            self.axis_x.setTitleText("Register Value")
            self.axis_x.setLabelsColor(QColor("#9fc0ef"))
            self.axis_x.setTitleBrush(QColor("#9fc0ef"))
            self.axis_x.setGridLineColor(QColor("#2a3f6a"))

            self.axis_y = QValueAxis()
            self.axis_y.setRange(0.5, 1.3)
            self.axis_y.setTickCount(9)
            self.axis_y.setTitleText("Measured Voltage (V)")
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
        label = QLabel("Output Voltage Linearity Chart")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#7da2d6; font-size:14px; font-weight:600; background: transparent;")
        v.addWidget(label)
        return placeholder

    def _create_mini_stat(self, title, value):
        frame = QFrame()
        frame.setObjectName("miniStatCard")
        frame.setMinimumHeight(68)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("metricLabel")

        value_label = QLabel(value)
        value_label.setObjectName("metricValue")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return {
            "frame": frame,
            "title": title_label,
            "value": value_label
        }

    def _init_ui_elements(self):
        self._update_connect_button_state(False)
        self.append_log("[SYSTEM] Ready. Waiting for instrument connection.")
        self.append_log("[TEST] UI initialized successfully.")
        self.set_progress(0)

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)
        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        self.msb_spin.valueChanged.connect(self._update_code_range)
        self.lsb_spin.valueChanged.connect(self._update_code_range)

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def _update_code_range(self):
        msb = self.msb_spin.value()
        lsb = self.lsb_spin.value()
        if msb < lsb:
            return
        bit_count = msb - lsb + 1
        max_val = (1 << bit_count) - 1
        self.min_code_edit.setText("0x0")
        self.max_code_edit.setText(f"0x{max_val:X}")

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        update_connect_button_state(self.connect_btn, connected)

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

    def append_log(self, message):
        self.log_edit.append(message)

    def _on_clear_log(self):
        self.log_edit.clear()

    def set_progress(self, value: int):
        value = max(0, min(100, int(value)))
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}% Complete")

    def get_test_config(self):
        return {
            'output_channel': self.output_channel_combo.currentText(),
            'set_voltage': self.set_voltage_spin.value(),
            'load_current_min': self.load_current_min_spin.value(),
            'load_current_max': self.load_current_max_spin.value(),
            'current_step': self.current_step_spin.value(),
            'measure_count': self.measure_count_spin.value(),
            'stabilize_time': self.stabilize_time_spin.value(),
            'sample_interval': self.sample_interval_spin.value(),
            'enable_ovp': self.ovp_checkbox.isChecked(),
            'ovp_value': self.ovp_spin.value(),

            'vmeter_channel': self.vmeter_channel_combo.currentText(),
            'device_addr': self.device_addr_edit.text().strip(),
            'reg_addr': self.reg_addr_edit.text().strip(),
            'msb': self.msb_spin.value(),
            'lsb': self.lsb_spin.value(),
            'width_flag': self.iic_width_flag_combo.currentData(),
            'min_code': self.min_code_edit.text().strip(),
            'max_code': self.max_code_edit.text().strip(),
        }

    def set_test_running(self, running):
        """设置测试运行状态"""
        self.is_test_running = running

        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(running)
        if running:
            self.start_test_btn.setText("■ Stop")
            self.start_test_btn.setObjectName("stopBtn")
        else:
            self.start_test_btn.setText("▷ Start Sequence")
            self.start_test_btn.setObjectName("primaryStartBtn")
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.start_test_btn.update()

        widgets = [
            self.vmeter_channel_combo,
            self.device_addr_edit,
            self.reg_addr_edit,
            self.msb_spin,
            self.lsb_spin,
            self.iic_width_flag_combo,
            self.min_code_edit,
            self.max_code_edit,
            self.visa_resource_combo,
            self.search_btn,
            self.connect_btn
        ]

        for widget in widgets:
            widget.setEnabled(not running)

        if running:
            self.set_system_status("● Running")
            self.append_log("[TEST] Starting Output Voltage Linearity Test Sequence...")
        else:
            self.set_system_status("● Ready" if not self.is_connected else "● Connected")
            self.append_log("[TEST] Test stopped or completed.")

    def update_test_result(self, result):
        if 'default_voltage' in result:
            code_str = f"(0x{result['default_code']:X})" if 'default_code' in result else ""
            self.default_voltage_card["value"].setText(f"{result['default_voltage']:.4f}V{code_str}")
        if 'min_voltage' in result:
            code_str = f" (0x{result['valid_min_code']:X})" if 'valid_min_code' in result else ""
            self.min_voltage_card["value"].setText(f"{result['min_voltage']:.4f} V{code_str}")
        if 'max_voltage' in result:
            code_str = f" (0x{result['valid_max_code']:X})" if 'valid_max_code' in result else ""
            self.max_voltage_card["value"].setText(f"{result['max_voltage']:.4f} V{code_str}")
        if 'step_voltage' in result:
            self.step_voltage_card["value"].setText(f"{result['step_voltage']:.4f} mV")
        if 'linearity' in result:
            self.linearity_card["value"].setText(f"{result['linearity']:.4f}%")
        if 'progress' in result:
            self.set_progress(result['progress'])

    def clear_results(self):
        self.default_voltage_card["value"].setText("---")
        self.min_voltage_card["value"].setText("---")
        self.max_voltage_card["value"].setText("---")
        self.step_voltage_card["value"].setText("---")
        self.linearity_card["value"].setText("---")
        self.set_progress(0)
        self.append_log("[SYSTEM] Results cleared.")

    def set_system_status(self, status, is_error=False):
        """设置系统状态"""
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

    def update_instrument_info(self, instrument_info):
        """更新连接的仪器信息"""
        self.instrument_info_label.setText(instrument_info)

    def _on_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        if DEBUG_MOCK:
            self.visa_resource_combo.clear()
            self.visa_resource_combo.addItem("DEBUG::MOCK::N6705C")
            self.set_system_status("● Mock device ready")
            self.append_log("[DEBUG] Mock device loaded, skip real VISA scan.")
            return
        self.set_system_status("● Searching")
        self.append_log("[SYSTEM] Scanning VISA resources...")
        self.search_btn.setEnabled(False)
        self.search_timer.start(100)

    def _search_devices(self):
        """搜索N6705C设备"""
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
        """动态连接按钮：未连接时连接，已连接时断开"""
        if self.is_connected:
            self._on_disconnect()
        else:
            self._on_connect()

    def _on_connect(self):
        """连接N6705C设备"""
        if DEBUG_MOCK:
            self.n6705c = MockN6705C()
            self._update_connect_button_state(True)
            self.set_system_status("● Connected (Mock)")
            self.search_btn.setEnabled(False)
            self.instrument_info_label.setText("Mock N6705C (DEBUG)")
            self.append_log("[DEBUG] Mock N6705C connected.")
            self.connection_status_changed.emit(True)
            return
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

    def get_n6705c_instance(self):
        """获取N6705C控制器实例"""
        return self.n6705c

    def is_n6705c_connected(self):
        """检查N6705C是否已连接"""
        return self.is_connected

    def _on_start_test(self):
        if not self.is_connected or self.n6705c is None:
            self.append_log("[ERROR] Not connected to N6705C instrument.")
            return
        if self.is_test_running:
            return

        self.clear_results()
        self.set_test_running(True)

        config = {
            "vmeter_channel": self.vmeter_channel_combo.currentText(),
            "device_addr": self.device_addr_edit.text().strip(),
            "reg_addr": self.reg_addr_edit.text().strip(),
            "msb": self.msb_spin.value(),
            "lsb": self.lsb_spin.value(),
            "width_flag": self.iic_width_flag_combo.currentData(),
            "min_code": self.min_code_edit.text().strip(),
            "max_code": self.max_code_edit.text().strip(),
        }

        self.test_thread = OutputVoltageTestThread(self.n6705c, config, DEBUG_MOCK)
        self.test_thread.log_message.connect(self.append_log)
        self.test_thread.chart_point.connect(self._update_chart_point)
        self.test_thread.chart_clear.connect(self._on_chart_clear)
        self.test_thread.result_update.connect(self.update_test_result)
        self.test_thread.test_finished.connect(self._on_test_finished)
        self.test_thread.start()

    def _on_stop_test(self):
        if self.test_thread is not None:
            self.test_thread.request_stop()
        self.append_log("[TEST] Stop requested...")

    def _on_test_finished(self):
        self.set_test_running(False)

    def _on_chart_clear(self):
        if HAS_QTCHARTS and hasattr(self, 'series'):
            self.series.clear()

    def _update_chart_point(self, reg_value, measured_v):
        if HAS_QTCHARTS and hasattr(self, 'series'):
            self.series.append(reg_value, measured_v)

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
                self.axis_y.setRange(max(0, min_y - margin_y), max_y + margin_y)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from log_config import setup_logging, get_logger
    setup_logging()
    _logger = get_logger(__name__)

    def custom_message_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return
        _logger.debug("%s:%s - %s", context.file, context.line, message)

    qInstallMessageHandler(custom_message_handler)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = PMUOutputVoltageUI()
    window.setWindowTitle("PMU Output Voltage Linearity Test")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())