#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU OSCP测试UI组件
深色卡片风格 + PySide6原生实现
"""

from ui.widgets.dark_combobox import DarkComboBox
from ui.styles import SCROLLBAR_STYLE, START_BTN_STYLE, update_start_btn_state
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGridLayout,
    QSpinBox, QDoubleSpinBox, QFrame, QApplication,
    QSizePolicy, QScrollArea, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont
import sys
from log_config import get_logger
from lib.i2c.i2c_interface_x64 import I2CInterface
from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
from core.pmu_test.oscp import (
    OSCPMonitorWorker, OSCPTestWorker,
    parse_hex_address, get_changed_bits, format_changed_bits,
)

logger = get_logger(__name__)


class CardFrame(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)
        self.main_layout.setSpacing(8)

        if title:
            self.title_row = QHBoxLayout()
            self.title_row.setSpacing(8)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.title_row.addWidget(self.title_label)
            self.title_row.addStretch()
            self.main_layout.addLayout(self.title_row)
        else:
            self.title_label = None
            self.title_row = None


class PMUOSCPUI(N6705CConnectionMixin, QWidget):
    """PMU OSCP测试UI组件"""

    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None, instrument_manager=None):
        super().__init__()

        self._instrument_manager = instrument_manager
        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)

        self.is_test_running = False
        self.test_thread = None
        self.test_worker = None

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()

        self.sync_n6705c_from_top()

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        self.setStyleSheet("""
        QWidget {
            background-color: #050b1a;
            color: #e8eefc;
        }

        QWidget#leftPanelInner {
            background-color: transparent;
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

        QFrame#cardFrame {
            background-color: #0d1833;
            border: 1px solid #1a2a52;
            border-radius: 12px;
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
            color: #8fa7d6;
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

        QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
            background-color: #0a1733;
            color: #eef4ff;
            border: 1px solid #20335f;
            border-radius: 8px;
            padding: 6px 10px;
            selection-background-color: #1fa3ff;
        }
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            width: 0px; height: 0px; border: none;
        }

        QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
            border: 1px solid #2dd4ff;
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
            color: #eef4ff;
            border: 1px solid #20335f;
            selection-background-color: #1a3260;
            outline: 0px;
        }

        QComboBox QAbstractItemView::item {
            background-color: #0a1733;
            color: #eef4ff;
            padding: 4px 8px;
        }

        QComboBox QAbstractItemView::item:hover {
            background-color: #1a3260;
        }

        QComboBox QFrame {
            background-color: #0a1733;
            border: 1px solid #20335f;
        }

        QPushButton {
            min-height: 34px;
            border-radius: 8px;
            padding: 6px 14px;
            border: 1px solid #273a66;
            background-color: #1a2748;
            color: #dce8ff;
            font-weight: 600;
        }

        QPushButton:hover {
            background-color: #22345e;
            border: 1px solid #35508c;
        }

        QPushButton:pressed {
            background-color: #16233f;
        }

        QPushButton:disabled {
            background-color: #11182b;
            color: #5f6d8f;
            border: 1px solid #1c2742;
        }
""" + START_BTN_STYLE + """
        QPushButton#smallActionBtn {
            min-height: 34px;
            padding: 6px 10px;
            border-radius: 8px;
            background-color: #1d2a49;
            color: #c8d7f5;
        }

        QPushButton[role="secondary"] {
            background-color: #1d2a49;
            color: #c8d7f5;
            border: 1px solid #26385f;
            border-radius: 8px;
        }

        QPushButton[role="secondary"]:hover {
            background-color: #24365c;
            border: 1px solid #355184;
        }

        QPushButton[role="outline"] {
            background-color: #081227;
            color: #c8d7f5;
            border: 1px solid #28406f;
            border-radius: 8px;
        }

        QPushButton[role="outline"]:hover {
            background-color: #0b1730;
            border: 1px solid #3b5b98;
        }

        QPushButton#abortBtn {
            background-color: #3d1830;
            color: #ff6f96;
            border: 1px solid #5f2748;
            border-radius: 8px;
            font-weight: 600;
        }

        QPushButton#abortBtn:hover {
            background-color: #51203e;
        }

        QPushButton#abortBtn:disabled {
            background-color: #251421;
            color: #805469;
            border: 1px solid #3b2130;
        }

        QFrame#resultContainer {
            background-color: #09142e;
            border: 1px solid #1a2d57;
            border-radius: 16px;
        }

        QFrame[role="resultBox"] {
            background-color: #020b22;
            border: 1px solid #1a2d57;
            border-radius: 12px;
        }

        QFrame[role="resultBox"][state="active"] {
            background-color: #041f2a;
            border: 1px solid #14d3b0;
        }

        QFrame[role="resultBox"][state="muted"] {
            background-color: #071126;
            border: 1px solid #16294f;
        }

        QLabel[role="resultValue"] {
            color: #f2f6ff;
            font-size: 15px;
            font-weight: 800;
            background-color: transparent;
        }

        QLabel[role="resultValue"][state="active"] {
            color: #19f5c8;
            font-size: 18px;
        }

        QLabel[role="resultCaption"] {
            color: #7d94c5;
            font-size: 10px;
            background-color: transparent;
        }

        QLabel#resultSummary {
            color: #9bb6e8;
            font-size: 11px;
            background-color: transparent;
        }
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.page_title = QLabel("OSCP Automated Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Configure and execute OSCP validation sequences.")
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
        self.left_scroll.setFixedWidth(320)
        self.left_scroll.setObjectName("leftScrollArea")
        self.left_scroll.setStyleSheet("""
            QScrollArea#leftScrollArea {
                background-color: #0d1833;
                border: 1px solid #1a2a52;
                border-radius: 16px;
            }
        """ + SCROLLBAR_STYLE)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("leftPanelInner")

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        self.connection_card = CardFrame("N6705C ")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.test_setting_card = CardFrame("Test Setting")
        self._build_test_setting_card()
        left_layout.addWidget(self.test_setting_card)

        self.config_card = CardFrame("OSCP Configuration")
        self._build_config_card()
        left_layout.addWidget(self.config_card)

        left_layout.addStretch()

        self.left_scroll.setWidget(self.left_panel)
        left_wrapper.addWidget(self.left_scroll, 1)

        self.start_test_btn = QPushButton("▶ START")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_wrapper.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("■ STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()

        content_layout.addLayout(left_wrapper)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)

        self.result_frame = QFrame()
        self.result_frame.setObjectName("resultContainer")
        result_outer_layout = QVBoxLayout(self.result_frame)
        result_outer_layout.setContentsMargins(16, 12, 16, 12)
        result_outer_layout.setSpacing(10)

        result_header_layout = QHBoxLayout()
        result_title = QLabel("⊙ Results")
        result_title.setObjectName("sectionTitle")
        result_header_layout.addWidget(result_title)
        result_header_layout.addStretch()
        self.result_status_label = QLabel("WAITING")
        self.result_status_label.setStyleSheet("color:#6b84b8; font-size:10px; font-weight:700;")
        result_header_layout.addWidget(self.result_status_label)
        result_outer_layout.addLayout(result_header_layout)

        result_row = QHBoxLayout()
        result_row.setSpacing(12)

        self.result_boxes = {}
        result_items = [
            ("threshold", "THRESHOLD", "Protection voltage"),
            ("register", "REG CHANGE", "Before → After"),
            ("bits", "BIT CHANGE", "Changed bits"),
            ("device", "I2C TARGET", "Device / Register"),
            ("sweep", "SWEEP", "Range / Step"),
        ]

        for key, title_text, caption_text in result_items:
            box = QFrame()
            box.setProperty("role", "resultBox")
            box.setProperty("state", "muted")
            box.style().polish(box)

            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(10, 8, 10, 8)
            box_layout.setSpacing(4)

            title_lbl = QLabel(title_text)
            title_lbl.setAlignment(Qt.AlignCenter)
            title_lbl.setStyleSheet("color:#6b84b8; font-size:10px; font-weight:700;")

            value_lbl = QLabel("---")
            value_lbl.setAlignment(Qt.AlignCenter)
            value_lbl.setProperty("role", "resultValue")
            value_lbl.setProperty("state", "active" if key == "threshold" else "normal")
            value_lbl.style().polish(value_lbl)

            caption_lbl = QLabel(caption_text)
            caption_lbl.setAlignment(Qt.AlignCenter)
            caption_lbl.setProperty("role", "resultCaption")
            caption_lbl.style().polish(caption_lbl)

            box_layout.addWidget(title_lbl)
            box_layout.addWidget(value_lbl)
            box_layout.addWidget(caption_lbl)
            result_row.addWidget(box)
            self.result_boxes[key] = {
                "box": box,
                "value": value_lbl,
                "caption": caption_lbl,
            }

        self.protection_current_label = self.result_boxes["threshold"]["value"]
        self.recovery_current_label = self.result_boxes["register"]["value"]
        self.bit_change_label = self.result_boxes["bits"]["value"]
        self.trigger_time_label = self.result_boxes["device"]["value"]
        self.recovery_time_label = self.result_boxes["sweep"]["value"]

        result_outer_layout.addLayout(result_row)
        self.result_summary_label = QLabel("Result details will appear after OVP/UVP register transition is detected.")
        self.result_summary_label.setObjectName("resultSummary")
        self.result_summary_label.setWordWrap(True)
        result_outer_layout.addWidget(self.result_summary_label)

        right_splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            self.result_frame, show_progress=True, stretch=(4, 1)
        )
        self.log_edit = self.execution_logs.log_edit
        self.progress_bar = self.execution_logs.progress_bar
        self.progress_text_label = self.execution_logs.progress_text_label
        self.clear_log_btn = self.execution_logs.clear_log_btn
        right_layout.addWidget(right_splitter, 1)

    def _build_connection_card(self):
        self.build_n6705c_connection_widgets(
            self.connection_card.main_layout,
            title_row=self.connection_card.title_row,
        )

    def _build_test_setting_card(self):
        layout = self.test_setting_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self.type_label = QLabel("Type")
        self.type_label.setObjectName("fieldLabel")
        self.test_type_combo = DarkComboBox(bg="#0a1733", border="#20335f")
        self.test_type_combo.addItems(["OCP", "SCP", "OVP", "UVP"])
        self.test_type_combo.setCurrentIndex(2)

        self.method_label = QLabel("Test Method")
        self.method_label.setObjectName("fieldLabel")
        self.test_method_combo = DarkComboBox(bg="#0a1733", border="#20335f")

        grid.addWidget(self.type_label, 0, 0)
        grid.addWidget(self.test_type_combo, 1, 0)
        grid.addWidget(self.method_label, 0, 1)
        grid.addWidget(self.test_method_combo, 1, 1)

        layout.addLayout(grid)

    def _build_config_card(self):
        layout = self.config_card.main_layout

        self.config_grid = QGridLayout()
        self.config_grid.setHorizontalSpacing(10)
        self.config_grid.setVerticalSpacing(6)

        self.dev_addr_label = QLabel("Dev Addr (hex)")
        self.dev_addr_label.setObjectName("fieldLabel")
        self.device_addr_edit = QLineEdit("0x17")
        self.device_addr_edit.setPlaceholderText("0x17")
        self.device_addr_edit.setMaxLength(5)

        self.reg_addr_label = QLabel("Reg Addr (hex)")
        self.reg_addr_label.setObjectName("fieldLabel")
        self.reg_addr_edit = QLineEdit("0x033b")
        self.reg_addr_edit.setPlaceholderText("0x033b")
        self.reg_addr_edit.setMaxLength(6)

        self.iic_width_label = QLabel("IIC Width")
        self.iic_width_label.setObjectName("fieldLabel")
        self.iic_width_combo = DarkComboBox(bg="#0a1733", border="#20335f")
        self.iic_width_combo.addItem("8-bit", int(I2CWidthFlag.BIT_8))
        self.iic_width_combo.addItem("10-bit", int(I2CWidthFlag.BIT_10))
        self.iic_width_combo.addItem("32-bit", int(I2CWidthFlag.BIT_32))
        self.iic_width_combo.setCurrentIndex(1)

        self.monitor_ch_label = QLabel("Monitor CH")
        self.monitor_ch_label.setObjectName("fieldLabel")
        self.monitor_channel_combo = DarkComboBox(bg="#0a1733", border="#20335f")
        self.monitor_channel_combo.addItems(["1", "2", "3", "4"])

        self.test_ch_label = QLabel("Test CH")
        self.test_ch_label.setObjectName("fieldLabel")
        self.test_channel_combo = DarkComboBox(bg="#0a1733", border="#20335f")
        self.test_channel_combo.addItems(["1", "2", "3", "4"])
        self.test_channel_combo.setCurrentIndex(1)

        self.start_label = QLabel("Start (V)")
        self.start_label.setObjectName("fieldLabel")
        self.start_spin = QDoubleSpinBox()

        self.end_label = QLabel("End (V)")
        self.end_label.setObjectName("fieldLabel")
        self.end_spin = QDoubleSpinBox()

        self.step_label = QLabel("Step (V)")
        self.step_label.setObjectName("fieldLabel")
        self.step_spin = QDoubleSpinBox()

        self.delay_label = QLabel("Delay Time (ms)")
        self.delay_label.setObjectName("fieldLabel")
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setDecimals(1)
        self.delay_spin.setRange(0.0, 60000.0)
        self.delay_spin.setSingleStep(10.0)
        self.delay_spin.setValue(100.0)

        for spin in [self.start_spin, self.end_spin, self.step_spin]:
            spin.setDecimals(3)
            spin.setRange(0.0, 9999.0)
            spin.setSingleStep(0.01)

        self.start_spin.setValue(0.0)
        self.end_spin.setValue(0.0)
        self.step_spin.setValue(0.0)

        self._reg_widgets = [
            (self.dev_addr_label, self.device_addr_edit),
            (self.reg_addr_label, self.reg_addr_edit),
            (self.iic_width_label, self.iic_width_combo),
        ]
        self._monitor_widgets = [
            (self.monitor_ch_label, self.monitor_channel_combo),
        ]
        self._common_widgets = [
            (self.test_ch_label, self.test_channel_combo),
            (self.start_label, self.start_spin),
            (self.end_label, self.end_spin),
            (self.step_label, self.step_spin),
            (self.delay_label, self.delay_spin),
        ]

        layout.addLayout(self.config_grid)
        self._rebuild_config_grid()

    def _rebuild_config_grid(self):
        while self.config_grid.count():
            item = self.config_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        method = self.test_method_combo.currentText()
        if method == "Reg":
            fields = self._reg_widgets + self._common_widgets
        else:
            fields = self._monitor_widgets + self._common_widgets

        row, col = 0, 0
        for text_label, widget in fields:
            self.config_grid.addWidget(text_label, row, col)
            self.config_grid.addWidget(widget, row + 1, col)
            text_label.show()
            widget.show()
            col += 1
            if col >= 2:
                col = 0
                row += 2

    def _init_ui_elements(self):
        self._update_n6705c_connect_button_state(False)
        self.stop_test_btn.setEnabled(False)

        self.test_type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.test_method_combo.currentIndexChanged.connect(self._on_method_changed)

        self.bind_n6705c_signals()

        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)

        self._update_method_options()
        self._update_test_config()

    def _on_type_changed(self, index=None):
        self._update_method_options()
        self._rebuild_config_grid()
        self._update_test_config()

    def _update_method_options(self):
        test_type = self.test_type_combo.currentText()
        self.test_method_combo.blockSignals(True)
        current_method = self.test_method_combo.currentText()
        self.test_method_combo.clear()
        if test_type in ["OCP", "SCP"]:
            self.test_method_combo.addItems(["Reg", "Current"])
        else:
            self.test_method_combo.addItems(["Reg", "Voltage"])
        idx = self.test_method_combo.findText(current_method)
        self.test_method_combo.setCurrentIndex(max(idx, 0))
        self.test_method_combo.blockSignals(False)

    def _on_method_changed(self, index=None):
        self._rebuild_config_grid()
        self._update_test_config()

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_single_test()

    def _update_test_config(self, index=None):
        test_type = self.test_type_combo.currentText()

        if test_type in ["OCP", "SCP"]:
            self.start_label.setText("Start (A)")
            self.end_label.setText("End (A)")
            self.step_label.setText("Step (A)")

            self.start_spin.setRange(0.0, 10.0)
            self.end_spin.setRange(0.0, 10.0)
            self.step_spin.setRange(0.001, 1.0)

            self.start_spin.setSingleStep(0.001)
            self.end_spin.setSingleStep(0.001)
            self.step_spin.setSingleStep(0.001)

            self.start_spin.setDecimals(3)
            self.end_spin.setDecimals(3)
            self.step_spin.setDecimals(4)
        else:
            self.start_label.setText("Start (V)")
            self.end_label.setText("End (V)")
            self.step_label.setText("Step (V)")

            self.start_spin.setRange(0.0, 20.0)
            self.end_spin.setRange(0.0, 20.0)
            self.step_spin.setRange(0.001, 2.0)

            self.start_spin.setSingleStep(0.001)
            self.end_spin.setSingleStep(0.001)
            self.step_spin.setSingleStep(0.001)

            self.start_spin.setDecimals(3)
            self.end_spin.setDecimals(3)
            self.step_spin.setDecimals(4)

    def get_test_config(self):
        test_type = self.test_type_combo.currentText()
        method = self.test_method_combo.currentText()

        config = {
            "test_type": test_type,
            "method": method,
            "test_channel": self.test_channel_combo.currentText(),
            "delay_time_ms": self.delay_spin.value(),
        }

        if method == "Reg":
            config.update({
                "device_address": parse_hex_address(self.device_addr_edit.text(), "DevAddr", 0x3FF),
                "register_address": parse_hex_address(self.reg_addr_edit.text(), "RegAddr", 0xFFFF),
                "iic_width": self.iic_width_combo.currentData(),
            })
        else:
            config["monitor_channel"] = self.monitor_channel_combo.currentText()

        if test_type in ["OCP", "SCP"]:
            config.update({
                "current_start": self.start_spin.value(),
                "current_end": self.end_spin.value(),
                "current_step": self.step_spin.value(),
            })
        else:
            config.update({
                "voltage_start": self.start_spin.value(),
                "voltage_end": self.end_spin.value(),
                "voltage_step": self.step_spin.value(),
            })

        return config

    def set_test_running(self, running):
        update_start_btn_state(self.start_test_btn, running,
                               start_text="▶ START",
                               stop_text="■ STOP")
        self.stop_test_btn.setEnabled(running)

        widgets = [
            self.test_type_combo,
            self.test_method_combo,
            self.test_channel_combo,
            self.monitor_channel_combo,
            self.start_spin,
            self.end_spin,
            self.step_spin,
            self.delay_spin,
            self.device_addr_edit,
            self.reg_addr_edit,
            self.iic_width_combo,
            self.search_btn,
        ]

        for widget in widgets:
            widget.setEnabled(not running)

    def _on_single_test(self):
        if self.is_test_running:
            self.set_system_status("测试正在运行中...", True)
            return

        try:
            config = self.get_test_config()
        except ValueError as e:
            self.set_system_status(str(e), True)
            return
        test_type = config["test_type"]
        method = config["method"]

        if not self.is_connected or self.n6705c is None:
            self.set_system_status("请先连接N6705C仪器", True)
            return

        self.set_system_status("测试进行中")
        self.is_test_running = True
        self.clear_results()
        self.set_test_running(True)

        config_copy = config.copy()
        config_copy.pop("test_type", None)
        config_copy.pop("method", None)

        if test_type in ["OCP", "SCP"]:
            config_copy["sweep_start"] = config_copy.pop("current_start", 0)
            config_copy["sweep_end"] = config_copy.pop("current_end", 0)
            config_copy["sweep_step"] = config_copy.pop("current_step", 0)
        else:
            config_copy["sweep_start"] = config_copy.pop("voltage_start", 0)
            config_copy["sweep_end"] = config_copy.pop("voltage_end", 0)
            config_copy["sweep_step"] = config_copy.pop("voltage_step", 0)

        self.test_thread = QThread(self)
        if method == "Reg":
            self.test_worker = OSCPTestWorker(test_type, self.n6705c, config_copy)
        else:
            self.test_worker = OSCPMonitorWorker(test_type, self.n6705c, config_copy)
        self.test_worker.moveToThread(self.test_thread)
        self.test_thread.started.connect(self.test_worker.run)
        self.test_worker.status_update.connect(self.set_system_status)
        self.test_worker.status_update.connect(
            lambda msg, _err=None: self.append_log(f"[INFO] {msg}")
        )
        self.test_worker.progress_update.connect(self.set_progress)
        self.test_worker.result_update.connect(self._on_test_result)
        self.test_worker.result_detail_update.connect(self._on_test_result_detail)
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_worker.test_finished.connect(self.test_thread.quit)
        self.test_thread.finished.connect(self.test_worker.deleteLater)
        self.test_thread.finished.connect(self.test_thread.deleteLater)
        self.test_thread.finished.connect(self._cleanup_test_thread)
        self.test_thread.start()

        logger.info("执行单次测试，配置: %s", config)

    def _on_stop_test(self):
        if self.is_test_running and self.test_thread:
            self.set_system_status("正在停止测试...")
            if self.test_worker:
                self.test_worker.stop()
            self.test_thread.quit()
            if not self.test_thread.wait(1000):
                self.test_thread.terminate()
                self.test_thread.wait()
            self._on_test_finished(False)

    def _cleanup_test_thread(self):
        self.test_thread = None
        self.test_worker = None

    def _on_test_result(self, result_type, value):
        if result_type == "保护电压":
            self.protection_current_label.setText(f"{value:.3f} V")
            self._set_result_box_state("threshold", "active")
        elif result_type == "保护电流":
            self.protection_current_label.setText(f"{value:.3f} A")
            self._set_result_box_state("threshold", "active")

    def _on_test_result_detail(self, result):
        if result.get("no_trigger"):
            self._show_no_trigger_result(result)
            return

        method = result.get("method", "reg")
        test_type = result.get("test_type", "OSCP")
        delay_time_ms = result.get("delay_time_ms")
        points_count = result.get("points_count")

        self.result_status_label.setText("TRIGGERED")
        self.result_status_label.setStyleSheet("color:#19f5c8; font-size:10px; font-weight:800;")

        if method == "monitor":
            threshold_val = result.get("threshold_value")
            monitor_before = result.get("monitor_before")
            monitor_after = result.get("monitor_after")
            monitor_channel = result.get("monitor_channel")
            start_val = result.get("start_value")
            end_val = result.get("end_value")
            step_val = result.get("step_value")
            is_current = test_type in ["OCP", "SCP"]
            unit = "A" if is_current else "V"

            self.protection_current_label.setText(f"{threshold_val:.3f} {unit}")
            self.recovery_current_label.setText(f"{monitor_before:.4f} → {monitor_after:.4f} {unit}")
            self.bit_change_label.setText(f"CH{monitor_channel}")
            self.trigger_time_label.setText(f"Delay {delay_time_ms:.1f} ms")
            self.recovery_time_label.setText(f"{start_val:.3f}→{end_val:.3f} {unit}")

            self.result_boxes["threshold"]["caption"].setText(f"{test_type} threshold")
            self.result_boxes["register"]["caption"].setText("Monitor before → after")
            self.result_boxes["bits"]["caption"].setText("Monitor channel")
            self.result_boxes["device"]["caption"].setText("Settle delay")
            self.result_boxes["sweep"]["caption"].setText(f"Step {step_val:.4f} {unit}, {points_count} pts")

            for key in self.result_boxes:
                self._set_result_box_state(key, "active")

            self.result_summary_label.setText(
                f"{test_type} detected monitor abrupt change at {threshold_val:.3f} {unit}. "
                f"Monitor CH{monitor_channel} changed from {monitor_before:.4f} to {monitor_after:.4f} {unit}."
            )
        else:
            threshold_voltage = result.get("threshold_voltage")
            reg_before = result.get("trigger_reg_before")
            reg_after = result.get("trigger_reg_after")
            changed_bits = result.get("changed_bits", get_changed_bits(reg_before, reg_after))
            bit_change_text = format_changed_bits(changed_bits)
            device_addr = result.get("device_address")
            reg_addr = result.get("register_address")
            iic_width = result.get("iic_width")
            start_voltage = result.get("start_voltage")
            end_voltage = result.get("end_voltage")
            step_voltage = result.get("step_voltage")

            self.protection_current_label.setText(f"{threshold_voltage:.3f} V")
            self.recovery_current_label.setText(f"0x{reg_before:X} → 0x{reg_after:X}")
            self.bit_change_label.setText(bit_change_text)
            self.trigger_time_label.setText(f"0x{device_addr:02X} / 0x{reg_addr:04X}")
            self.recovery_time_label.setText(f"{start_voltage:.3f}→{end_voltage:.3f} V")

            self.result_boxes["threshold"]["caption"].setText(f"{test_type} threshold")
            self.result_boxes["register"]["caption"].setText(f"IIC Width {iic_width}, delay {delay_time_ms:.1f} ms")
            self.result_boxes["bits"]["caption"].setText(f"{len(changed_bits)} bit(s) changed")
            self.result_boxes["device"]["caption"].setText("Device addr / Reg addr")
            self.result_boxes["sweep"]["caption"].setText(f"Step {step_voltage:.4f} V, {points_count} pts")

            for key in self.result_boxes:
                self._set_result_box_state(key, "active")

            self.result_summary_label.setText(
                f"{test_type} detected register transition at {threshold_voltage:.3f} V. "
                f"REG changed from 0x{reg_before:X} to 0x{reg_after:X}; bit change: {bit_change_text}."
            )

    def _show_no_trigger_result(self, result):
        test_type = result.get("test_type", "OSCP")
        method = result.get("method", "reg")
        delay_time_ms = result.get("delay_time_ms")
        points_count = result.get("points_count")

        self.result_status_label.setText("NO TRIGGER")
        self.result_status_label.setStyleSheet("color:#ffb84d; font-size:10px; font-weight:800;")

        if method == "monitor":
            initial_monitor = result.get("initial_monitor")
            monitor_channel = result.get("monitor_channel")
            start_val = result.get("start_value")
            end_val = result.get("end_value")
            step_val = result.get("step_value")
            is_current = test_type in ["OCP", "SCP"]
            unit = "A" if is_current else "V"

            self.protection_current_label.setText("Not Found")
            self.recovery_current_label.setText(f"{initial_monitor:.4f} {unit}")
            self.bit_change_label.setText(f"CH{monitor_channel}")
            self.trigger_time_label.setText(f"Delay {delay_time_ms:.1f} ms")
            self.recovery_time_label.setText(f"{start_val:.3f}→{end_val:.3f} {unit}")

            self.result_boxes["threshold"]["caption"].setText(f"No {test_type} transition")
            self.result_boxes["register"]["caption"].setText("Monitor stable")
            self.result_boxes["bits"]["caption"].setText("Monitor channel")
            self.result_boxes["device"]["caption"].setText("Settle delay")
            self.result_boxes["sweep"]["caption"].setText(f"Step {step_val:.4f} {unit}, {points_count} pts")

            for key in self.result_boxes:
                self._set_result_box_state(key, "muted")

            self.result_summary_label.setText(
                f"{test_type} sweep completed without abrupt change on Monitor CH{monitor_channel}. "
                f"Initial monitor value: {initial_monitor:.4f} {unit}."
            )
        else:
            initial_reg = result.get("initial_reg")
            device_addr = result.get("device_address")
            reg_addr = result.get("register_address")
            iic_width = result.get("iic_width")
            start_voltage = result.get("start_voltage")
            end_voltage = result.get("end_voltage")
            step_voltage = result.get("step_voltage")

            self.protection_current_label.setText("Not Found")
            self.recovery_current_label.setText(f"0x{initial_reg:X}")
            self.bit_change_label.setText("None")
            self.trigger_time_label.setText(f"0x{device_addr:02X} / 0x{reg_addr:04X}")
            self.recovery_time_label.setText(f"{start_voltage:.3f}→{end_voltage:.3f} V")

            self.result_boxes["threshold"]["caption"].setText(f"No {test_type} transition")
            self.result_boxes["register"]["caption"].setText(f"IIC Width {iic_width}, delay {delay_time_ms:.1f} ms")
            self.result_boxes["bits"]["caption"].setText("No bit changed")
            self.result_boxes["device"]["caption"].setText("Device addr / Reg addr")
            self.result_boxes["sweep"]["caption"].setText(f"Step {step_voltage:.4f} V, {points_count} pts")

            for key in self.result_boxes:
                self._set_result_box_state(key, "muted")

            self.result_summary_label.setText(
                f"{test_type} sweep completed without register transition. "
                f"Initial REG stayed at 0x{initial_reg:X} across configured scan range."
            )

    def _set_result_box_state(self, key, state):
        if key not in self.result_boxes:
            return
        box = self.result_boxes[key]["box"]
        box.setProperty("state", state)
        box.style().unpolish(box)
        box.style().polish(box)
        box.update()

    def _on_test_finished(self, success):
        self.is_test_running = False
        self.set_test_running(False)

        if success:
            if self.result_status_label.text() != "TRIGGERED":
                self.result_status_label.setText("DONE")
                self.result_status_label.setStyleSheet("color:#19f5c8; font-size:10px; font-weight:800;")
            self.set_system_status("测试完成")
        elif self.result_status_label.text() != "NO TRIGGER":
            self.result_status_label.setText("STOPPED")
            self.result_status_label.setStyleSheet("color:#ffb84d; font-size:10px; font-weight:800;")
            self.set_system_status("测试停止", True)

    def update_test_result(self, result):
        if "protection_current" in result:
            self.protection_current_label.setText(f"{result['protection_current']:.4f} A")
        if "recovery_current" in result:
            self.recovery_current_label.setText(f"{result['recovery_current']:.4f} A")
        if "changed_bits" in result:
            self.bit_change_label.setText(format_changed_bits(result["changed_bits"]))
        if "trigger_time" in result:
            self.trigger_time_label.setText(f"{result['trigger_time']:.4f} ms")
        if "recovery_time" in result:
            self.recovery_time_label.setText(f"{result['recovery_time']:.4f} ms")

    def clear_results(self):
        self.result_status_label.setText("RUNNING" if self.is_test_running else "WAITING")
        self.result_status_label.setStyleSheet("color:#6b84b8; font-size:10px; font-weight:700;")
        self.protection_current_label.setText("---")
        self.recovery_current_label.setText("---")
        self.bit_change_label.setText("---")
        self.trigger_time_label.setText("---")
        self.recovery_time_label.setText("---")
        self.result_boxes["threshold"]["caption"].setText("Protection voltage")
        self.result_boxes["register"]["caption"].setText("Before → After")
        self.result_boxes["bits"]["caption"].setText("Changed bits")
        self.result_boxes["device"]["caption"].setText("Device / Register")
        self.result_boxes["sweep"]["caption"].setText("Range / Step")
        self.result_summary_label.setText("Result details will appear after OVP/UVP register transition is detected.")
        for key in self.result_boxes:
            self._set_result_box_state(key, "muted")
        self.set_progress(0)

    def update_instrument_info(self, instrument_info):
        if self.is_connected:
            self.set_system_status("● Connected")

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def set_progress(self, value: int):
        self.execution_logs.set_progress(value)

    def i2c_test(self):
        self.set_system_status("执行I2C测试...")

        try:
            i2c = I2CInterface()
            self.set_system_status("I2C接口初始化成功")

            device_addr = 0x17
            width_flag = I2CWidthFlag.BIT_10

            reg_addr_read = 0x0000
            logger.info("1. 读取操作：")
            logger.info("   设备地址: 0x%02X", device_addr)
            logger.info("   寄存器地址: 0x%04X", reg_addr_read)
            logger.info("   位宽模式: %s", width_flag.name)

            read_data = i2c.read(device_addr, reg_addr_read, width_flag)
            logger.info("   读取结果: 0x%04X", read_data)
            self.set_system_status(f"I2C读取成功: 0x{read_data:04X}")

            reg_addr_write = 0x1e7
            write_data = 0x20AA
            logger.info("2. 写入操作：")
            logger.info("   设备地址: 0x%02X", device_addr)
            logger.info("   寄存器地址: 0x%04X", reg_addr_write)
            logger.info("   写入数据: 0x%04X", write_data)
            logger.info("   位宽模式: %s", width_flag.name)

            i2c.write(device_addr, reg_addr_write, write_data, width_flag)
            logger.info("   写入成功")
            self.set_system_status("I2C写入成功")

            logger.info("3. 验证写入结果：")
            verify_data = i2c.read(device_addr, reg_addr_write, width_flag)
            logger.info("   寄存器地址0x%04X的当前值: 0x%04X", reg_addr_write, verify_data)
            logger.info("   验证%s", '成功' if verify_data == write_data else '失败')

            if verify_data == write_data:
                self.set_system_status("I2C测试完成，验证成功")
            else:
                self.set_system_status("I2C测试完成，但验证失败", True)

            return True

        except Exception as e:
            error_msg = f"I2C测试操作失败: {e}"
            logger.error(error_msg, exc_info=True)
            self.set_system_status(error_msg, True)
            return False


if __name__ == '__main__':
    from ui.standalone import resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pmu_test_ui = PMUOSCPUI()
    pmu_test_ui.setWindowTitle("PMU OSCP Automated Test")
    resize_and_center_window(pmu_test_ui)
    pmu_test_ui.show()

    sys.exit(app.exec())
