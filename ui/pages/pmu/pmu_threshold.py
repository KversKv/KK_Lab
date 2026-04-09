#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU Threshold & Is_gain测试UI组件
暗色卡片式重构版本（PySide6）
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QSpinBox, QFrame, QTextEdit,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
import os
import pyvisa

from instruments.power.keysight.n6705c import N6705C


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


class FixedPopupComboBox(QComboBox):
    """下拉框：确保弹出列表从控件下方开始"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.view().window().setStyleSheet(
            "background-color: #0a1733; border: 1px solid #27406f;"
        )
        self.view().setStyleSheet(
            "background-color: #0a1733; color: #eaf2ff; "
            "selection-background-color: #334a7d; outline: 0px;"
        )

    def showPopup(self):
        super().showPopup()
        view = self.view()
        if view and view.window():
            popup = view.window()
            popup.setStyleSheet(
                "background-color: #0a1733; border: 1px solid #27406f;"
            )
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(global_pos.x(), global_pos.y())


class PMUThresholdUI(QWidget):
    """PMU Threshold测试UI组件"""

    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None, mso64b_top=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self._mso64b_top = mso64b_top
        self.rm = None
        self.n6705c = None
        self.available_devices = []
        self.is_connected = False

        self.scope_connected = False
        self.scope_resource = None

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

    @staticmethod
    def _get_checkmark_path(accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        _cb_icons = self._get_checkmark_path("4f46e5")
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

            QLabel#statusErr {
                color: #ff5e7a;
                font-weight: 600;
                background-color: transparent;
            }

            QLabel#statusWarn {
                color: #ffb84d;
                font-weight: 600;
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

            QFrame#resultContainer, QFrame#logContainer {
                background-color: #09142e;
                border: 1px solid #1a2d57;
                border-radius: 16px;
            }

            QLineEdit, QComboBox, QSpinBox, QTextEdit, QTableWidget {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #4f46e5;
            }

            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QTableWidget:focus {
                border: 1px solid #4cc9f0;
            }

            QComboBox {
                padding-right: 24px;
            }

            QComboBox::drop-down {
                border: none;
                width: 22px;
                background: transparent;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }

            QComboBox QAbstractItemView {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                selection-background-color: #334a7d;
                outline: 0px;
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

            QPushButton#dynamicConnectBtn {
                min-height: 30px;
                border-radius: 8px;
                padding: 4px 12px;
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

            QPushButton#primaryActionBtn {
                min-height: 36px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
                color: white;
            }

            QPushButton#primaryActionBtn[running="false"] {
                border: 1px solid #645bff;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5b5cf6,
                    stop:1 #6a38ff
                );
            }

            QPushButton#primaryActionBtn[running="false"]:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b6cff,
                    stop:1 #7d4cff
                );
            }

            QPushButton#primaryActionBtn[running="true"] {
                background-color: #8d0f3e;
                border: 1px solid #df4a7a;
                color: #ffd9e6;
            }

            QPushButton#primaryActionBtn[running="true"]:hover {
                background-color: #a11247;
                border: 1px solid #f05a8c;
            }

            QPushButton#exportBtn {
                min-height: 28px;
                padding: 4px 12px;
                border-radius: 8px;
                background-color: #16284f;
                color: #dfe8ff;
            }

            QTextEdit#logEdit {
                background-color: #050d22;
                border: 1px solid #1f315d;
                border-radius: 8px;
                color: #7cecc8;
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
            }

            QTableWidget {
                background-color: #030b1f;
                border: 1px solid #1f315d;
                border-radius: 8px;
                gridline-color: #15284f;
                color: #dbe7ff;
            }

            QHeaderView::section {
                background-color: #08142f;
                color: #c7d7f6;
                border: none;
                border-bottom: 1px solid #16305c;
                padding: 6px;
                font-weight: 700;
            }

            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #102448;
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

            QCheckBox {
                color: #dbe7ff;
                background: transparent;
                spacing: 6px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                image: url("__UNCHECKED__");
            }

            QCheckBox::indicator:checked {
                image: url("__CHECKED__");
            }
        """.replace("__UNCHECKED__", _cb_icons['unchecked']).replace("__CHECKED__", _cb_icons['checked']))

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        self.page_title = QLabel("⚙ Threshold & Is_gain Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Configure and execute automated threshold and is_gain validation sequences.")
        self.page_subtitle.setObjectName("pageSubtitle")

        title_layout.addWidget(self.page_title)
        title_layout.addWidget(self.page_subtitle)
        root_layout.addLayout(title_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        root_layout.addLayout(content_layout, 1)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("panelFrame")
        self.left_panel.setFixedWidth(500)

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(14)

        self.connection_card = CardFrame("⚡ INSTRUMENTS CONNECTION")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.channel_card = CardFrame("☷ CHANNEL SELECTION")
        self._build_channel_card()
        left_layout.addWidget(self.channel_card)

        self.is_gain_card = CardFrame("◉ IS_GAIN CONFIG")
        self._build_is_gain_card()
        left_layout.addWidget(self.is_gain_card)

        self.threshold_card = CardFrame("◉ THRESHOLD CONFIG")
        self._build_threshold_card()
        left_layout.addWidget(self.threshold_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("▷  Start Sequence")
        self.start_test_btn.setObjectName("primaryActionBtn")
        self.start_test_btn.setProperty("running", "false")
        left_layout.addWidget(self.start_test_btn)

        # 兼容旧代码
        self.stop_test_btn = QPushButton("Abort Test")
        self.stop_test_btn.hide()

        content_layout.addWidget(self.left_panel)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        content_layout.addLayout(right_layout, 1)

        self.result_frame = QFrame()
        self.result_frame.setObjectName("resultContainer")
        result_layout = QVBoxLayout(self.result_frame)
        result_layout.setContentsMargins(12, 12, 12, 12)
        result_layout.setSpacing(10)

        result_header = QHBoxLayout()
        self.result_title = QLabel("▦ Test Results")
        self.result_title.setObjectName("sectionTitle")
        result_header.addWidget(self.result_title)
        result_header.addStretch()

        self.export_result_btn = QPushButton("⇩ Export CSV")
        self.export_result_btn.setObjectName("exportBtn")
        result_header.addWidget(self.export_result_btn)

        result_layout.addLayout(result_header)

        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(["STEP", "REGISTER VALUE", "IS_GAIN", "THRESHOLD (V)"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.setAlternatingRowColors(False)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setShowGrid(False)
        result_layout.addWidget(self.result_table)

        right_layout.addWidget(self.result_frame, 5)

        self.log_frame = QFrame()
        self.log_frame.setObjectName("logContainer")
        log_layout = QVBoxLayout(self.log_frame)
        log_layout.setContentsMargins(12, 12, 12, 12)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        self.log_title = QLabel("›_ EXECUTION LOGS")
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

        log_layout.addLayout(log_header)

        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(110)
        log_layout.addWidget(self.log_edit)

        right_layout.addWidget(self.log_frame, 1)

    def _build_connection_card(self):
        layout = self.connection_card.main_layout

        n6705c_label = QLabel("N6705C DC Power Analyzer")
        n6705c_label.setObjectName("fieldLabel")
        layout.addWidget(n6705c_label)

        self.visa_resource_combo = FixedPopupComboBox()
        self.visa_resource_combo.addItem("USB0::0x0957::0x0F07::MY53004321::INSTR")
        layout.addWidget(self.visa_resource_combo)

        n670_row = QHBoxLayout()
        n670_row.setSpacing(8)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("smallActionBtn")

        self.connect_btn = QPushButton("🔗  Connect")
        self.connect_btn.setObjectName("dynamicConnectBtn")
        self.connect_btn.setProperty("connected", "false")

        n670_row.addWidget(self.search_btn)
        n670_row.addWidget(self.connect_btn)
        layout.addLayout(n670_row)

        scope_label = QLabel("MSO64B Oscilloscope")
        scope_label.setObjectName("fieldLabel")
        layout.addWidget(scope_label)

        self.scope_resource_edit = QLineEdit("TCPIP0::192.168.1.100::inst0::INSTR")
        layout.addWidget(self.scope_resource_edit)

        self.scope_connect_btn = QPushButton("🔗  Connect")
        self.scope_connect_btn.setObjectName("dynamicConnectBtn")
        self.scope_connect_btn.setProperty("connected", "false")
        layout.addWidget(self.scope_connect_btn)

    def _build_channel_card(self):
        layout = self.channel_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_vin = QLabel("VIN Channel")
        lbl_vin.setObjectName("fieldLabel")
        self.vin_channel_combo = FixedPopupComboBox()
        self.vin_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])

        lbl_load = QLabel("Load Channel")
        lbl_load.setObjectName("fieldLabel")
        self.load_channel_combo = FixedPopupComboBox()
        self.load_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        self.load_channel_combo.setCurrentIndex(1)

        lbl_vmeter = QLabel("VMeter Channel")
        lbl_vmeter.setObjectName("fieldLabel")
        self.vmeter_channel_combo = FixedPopupComboBox()
        self.vmeter_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        self.vmeter_channel_combo.setCurrentIndex(2)

        grid.addWidget(lbl_vin, 0, 0)
        grid.addWidget(self.vin_channel_combo, 0, 1)

        grid.addWidget(lbl_load, 1, 0)
        grid.addWidget(self.load_channel_combo, 1, 1)

        grid.addWidget(lbl_vmeter, 2, 0)
        grid.addWidget(self.vmeter_channel_combo, 2, 1)

        layout.addLayout(grid)

    def _build_is_gain_card(self):
        layout = self.is_gain_card.main_layout

        top_row = QHBoxLayout()

        mode_label = QLabel("测试方法")
        mode_label.setObjectName("fieldLabel")
        self.is_gain_method_combo = FixedPopupComboBox()
        self.is_gain_method_combo.addItems(["CV测试法", "CC测试法"])

        self.is_gain_enable_checkbox = QCheckBox("是否遍历")
        self.is_gain_enable_checkbox.setChecked(True)

        top_row.addWidget(mode_label)
        top_row.addWidget(self.is_gain_method_combo, 1)
        top_row.addWidget(self.is_gain_enable_checkbox)
        layout.addLayout(top_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_dev = QLabel("Device Addr")
        lbl_dev.setObjectName("fieldLabel")
        self.is_gain_device_addr_edit = QLineEdit("0x60")

        lbl_reg = QLabel("Reg Addr")
        lbl_reg.setObjectName("fieldLabel")
        self.is_gain_reg_addr_edit = QLineEdit("0x01")

        lbl_msb = QLabel("MSB")
        lbl_msb.setObjectName("fieldLabel")
        self.is_gain_msb_spin = QSpinBox()
        self.is_gain_msb_spin.setRange(0, 255)
        self.is_gain_msb_spin.setValue(7)

        lbl_lsb = QLabel("LSB")
        lbl_lsb.setObjectName("fieldLabel")
        self.is_gain_lsb_spin = QSpinBox()
        self.is_gain_lsb_spin.setRange(0, 255)
        self.is_gain_lsb_spin.setValue(4)

        grid.addWidget(lbl_dev, 0, 0)
        grid.addWidget(lbl_reg, 0, 1)
        grid.addWidget(self.is_gain_device_addr_edit, 1, 0)
        grid.addWidget(self.is_gain_reg_addr_edit, 1, 1)

        grid.addWidget(lbl_msb, 2, 0)
        grid.addWidget(lbl_lsb, 2, 1)
        grid.addWidget(self.is_gain_msb_spin, 3, 0)
        grid.addWidget(self.is_gain_lsb_spin, 3, 1)

        layout.addLayout(grid)

    def _build_threshold_card(self):
        layout = self.threshold_card.main_layout

        top_row = QHBoxLayout()

        mode_label = QLabel("测试方法")
        mode_label.setObjectName("fieldLabel")
        self.threshold_method_combo = FixedPopupComboBox()
        self.threshold_method_combo.addItems(["寄存器测试法", "示波器测量法"])

        self.threshold_enable_checkbox = QCheckBox("是否遍历")
        self.threshold_enable_checkbox.setChecked(True)

        top_row.addWidget(mode_label)
        top_row.addWidget(self.threshold_method_combo, 1)
        top_row.addWidget(self.threshold_enable_checkbox)
        layout.addLayout(top_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_dev = QLabel("Device Addr")
        lbl_dev.setObjectName("fieldLabel")
        self.threshold_device_addr_edit = QLineEdit("0x60")

        lbl_reg = QLabel("Reg Addr")
        lbl_reg.setObjectName("fieldLabel")
        self.threshold_reg_addr_edit = QLineEdit("0x02")

        lbl_msb = QLabel("MSB")
        lbl_msb.setObjectName("fieldLabel")
        self.threshold_msb_spin = QSpinBox()
        self.threshold_msb_spin.setRange(0, 255)
        self.threshold_msb_spin.setValue(3)

        lbl_lsb = QLabel("LSB")
        lbl_lsb.setObjectName("fieldLabel")
        self.threshold_lsb_spin = QSpinBox()
        self.threshold_lsb_spin.setRange(0, 255)
        self.threshold_lsb_spin.setValue(0)

        grid.addWidget(lbl_dev, 0, 0)
        grid.addWidget(lbl_reg, 0, 1)
        grid.addWidget(self.threshold_device_addr_edit, 1, 0)
        grid.addWidget(self.threshold_reg_addr_edit, 1, 1)

        grid.addWidget(lbl_msb, 2, 0)
        grid.addWidget(lbl_lsb, 2, 1)
        grid.addWidget(self.threshold_msb_spin, 3, 0)
        grid.addWidget(self.threshold_lsb_spin, 3, 1)

        layout.addLayout(grid)

    def _init_ui_elements(self):
        self._update_connect_button_state(self.connect_btn, False)
        self._update_connect_button_state(self.scope_connect_btn, False)
        self._update_test_button_state(False)
        self.append_log("[SYSTEM] Ready. Waiting for instrument connection.")
        self.set_progress(0)
        self.stop_test_btn.setEnabled(False)

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect_n6705c)
        self.scope_connect_btn.clicked.connect(self._on_connect_or_disconnect_scope)
        self.start_test_btn.clicked.connect(self._on_start_or_abort_clicked)
        self.stop_test_btn.clicked.connect(self._abort_test_from_external)

    def _abort_test_from_external(self):
        if self.is_test_running:
            self.set_test_running(False)
            self.append_log("[TEST] Abort requested by external stop button.")

    def _update_connect_button_state(self, button: QPushButton, connected: bool):
        button.setProperty("connected", "true" if connected else "false")
        button.setText("⟲  Disconnect" if connected else "🔗  Connect")
        button.style().unpolish(button)
        button.style().polish(button)
        button.update()

    def _sync_from_top(self):
        if self._n6705c_top:
            if self._n6705c_top.is_connected_a and self._n6705c_top.n6705c_a:
                self.n6705c = self._n6705c_top.n6705c_a
                self.is_connected = True
                self._update_connect_button_state(self.connect_btn, True)
                self.search_btn.setEnabled(False)
                if self._n6705c_top.visa_resource_a:
                    self.visa_resource_combo.clear()
                    self.visa_resource_combo.addItem(self._n6705c_top.visa_resource_a)
            elif not self.is_connected:
                self._update_connect_button_state(self.connect_btn, False)

        if self._mso64b_top:
            if self._mso64b_top.is_connected and self._mso64b_top.mso64b:
                self.scope_resource = self._mso64b_top.visa_resource
                self.scope_connected = True
                self.scope_resource_edit.setText(self._mso64b_top.visa_resource)
                self._update_connect_button_state(self.scope_connect_btn, True)
            elif not self.scope_connected:
                self._update_connect_button_state(self.scope_connect_btn, False)

    def _update_test_button_state(self, running: bool):
        self.is_test_running = running
        self.start_test_btn.setProperty("running", "true" if running else "false")
        self.start_test_btn.setText("□  Abort Test" if running else "▷  Start Sequence")
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.start_test_btn.update()

    def append_log(self, message):
        self.log_edit.append(message)

    def set_progress(self, value: int):
        value = max(0, min(100, int(value)))
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}% Complete")

    def get_test_config(self):
        return {
            "vin_channel": self.vin_channel_combo.currentText(),
            "load_channel": self.load_channel_combo.currentText(),
            "vmeter_channel": self.vmeter_channel_combo.currentText(),

            "is_gain_method": self.is_gain_method_combo.currentText(),
            "is_gain_enable_listen": self.is_gain_enable_checkbox.isChecked(),
            "is_gain_enable_traverse": self.is_gain_enable_checkbox.isChecked(),
            "is_gain_device_addr": self.is_gain_device_addr_edit.text().strip(),
            "is_gain_reg_addr": self.is_gain_reg_addr_edit.text().strip(),
            "is_gain_msb": self.is_gain_msb_spin.value(),
            "is_gain_lsb": self.is_gain_lsb_spin.value(),

            "threshold_method": self.threshold_method_combo.currentText(),
            "threshold_enable_listen": self.threshold_enable_checkbox.isChecked(),
            "threshold_enable_traverse": self.threshold_enable_checkbox.isChecked(),
            "threshold_device_addr": self.threshold_device_addr_edit.text().strip(),
            "threshold_reg_addr": self.threshold_reg_addr_edit.text().strip(),
            "threshold_msb": self.threshold_msb_spin.value(),
            "threshold_lsb": self.threshold_lsb_spin.value()
        }

    def set_test_running(self, running):
        self._update_test_button_state(running)
        self.stop_test_btn.setEnabled(running)

        widgets = [
            self.vin_channel_combo,
            self.load_channel_combo,
            self.vmeter_channel_combo,

            self.is_gain_method_combo,
            self.is_gain_enable_checkbox,
            self.is_gain_device_addr_edit,
            self.is_gain_reg_addr_edit,
            self.is_gain_msb_spin,
            self.is_gain_lsb_spin,

            self.threshold_method_combo,
            self.threshold_enable_checkbox,
            self.threshold_device_addr_edit,
            self.threshold_reg_addr_edit,
            self.threshold_msb_spin,
            self.threshold_lsb_spin,

            self.visa_resource_combo,
            self.scope_resource_edit,
            self.search_btn,
            self.connect_btn,
            self.scope_connect_btn
        ]

        for widget in widgets:
            widget.setEnabled(not running)

        if running:
            self.append_log("[TEST] Starting Threshold & Is_gain Test Sequence...")
        else:
            self.append_log("[TEST] Test stopped or completed.")

    def clear_results(self):
        self.result_table.setRowCount(0)
        self.set_progress(0)
        self.append_log("[SYSTEM] Results cleared.")

    def add_result_row(self, step, reg_value, is_gain, threshold_v):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)

        items = [
            QTableWidgetItem(str(step)),
            QTableWidgetItem(str(reg_value)),
            QTableWidgetItem(f"{is_gain}"),
            QTableWidgetItem(f"{threshold_v}")
        ]

        for col, item in enumerate(items):
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if col == 1:
                item.setForeground(QColor("#5f8cff"))
            elif col == 3:
                item.setForeground(QColor("#00d6a2"))
            self.result_table.setItem(row, col, item)

    def update_test_result(self, result):
        if "rows" in result and isinstance(result["rows"], list):
            self.result_table.setRowCount(0)
            for row in result["rows"]:
                self.add_result_row(
                    row.get("step", ""),
                    row.get("reg_value", ""),
                    row.get("is_gain", ""),
                    row.get("threshold", "")
                )
        elif any(k in result for k in ("step", "reg_value", "is_gain", "threshold")):
            self.add_result_row(
                result.get("step", ""),
                result.get("reg_value", ""),
                result.get("is_gain", ""),
                result.get("threshold", "")
            )

        if "progress" in result:
            self.set_progress(result["progress"])

        log_parts = []
        if "reg_value" in result:
            log_parts.append(f"Reg: {result['reg_value']}")
        if "is_gain" in result:
            log_parts.append(f"Is_gain: {result['is_gain']}")
        if "threshold" in result:
            log_parts.append(f"Threshold: {result['threshold']}V")

        if log_parts:
            self.append_log("[MEASURE] " + ", ".join(log_parts))

    def set_system_status(self, status, is_error=False):
        self.page_subtitle.setText(status)
        if is_error:
            self.page_subtitle.setObjectName("statusErr")
        elif "Connecting" in status or "Searching" in status or "Running" in status:
            self.page_subtitle.setObjectName("statusWarn")
        else:
            self.page_subtitle.setObjectName("pageSubtitle")

        self.page_subtitle.style().unpolish(self.page_subtitle)
        self.page_subtitle.style().polish(self.page_subtitle)
        self.page_subtitle.update()

    def update_instrument_info(self, instrument_info):
        pass

    def _on_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        self.set_system_status("Searching VISA resources...")
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
            n6705c_devices = []

            for dev in self.available_devices:
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
                self.append_log(f"[SYSTEM] Found {len(n6705c_devices)} compatible N6705C device(s).")
                self.set_system_status(f"Found {len(n6705c_devices)} device(s)")
            else:
                self.visa_resource_combo.addItem("No N6705C device found")
                self.visa_resource_combo.setEnabled(False)
                self.set_system_status("No N6705C device found", is_error=True)
                self.append_log("[SYSTEM] No compatible N6705C instrument found.")

        except Exception as e:
            self.set_system_status("Search failed", is_error=True)
            self.append_log(f"[ERROR] Search failed: {str(e)}")
        finally:
            self.search_btn.setEnabled(True)

    def _on_connect_or_disconnect_n6705c(self):
        if self.is_connected:
            self._on_disconnect_n6705c()
        else:
            self._on_connect_n6705c()

    def _on_connect_or_disconnect_scope(self):
        if self.scope_connected:
            self._on_disconnect_scope()
        else:
            self._on_connect_scope()

    def _on_connect_n6705c(self):
        self.set_system_status("Connecting N6705C...")
        self.append_log("[SYSTEM] Attempting N6705C connection...")
        self.connect_btn.setEnabled(False)

        try:
            device_address = self.visa_resource_combo.currentText()
            self.n6705c = N6705C(device_address)
            idn = self.n6705c.instr.query("*IDN?")

            if "N6705C" in idn:
                self.is_connected = True
                self._update_connect_button_state(self.connect_btn, True)
                self.search_btn.setEnabled(False)
                self.append_log("[SYSTEM] N6705C connected.")
                self.append_log(f"[IDN] {idn.strip()}")
                self.set_system_status("N6705C connected")

                if self._n6705c_top:
                    self._n6705c_top.connect_a(device_address, self.n6705c)

                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("Device mismatch", is_error=True)
                self.append_log("[ERROR] Connected device is not N6705C.")

        except Exception as e:
            self.set_system_status("N6705C connection failed", is_error=True)
            self.append_log(f"[ERROR] N6705C connection failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_disconnect_n6705c(self):
        self.set_system_status("Disconnecting N6705C...")
        self.append_log("[SYSTEM] Disconnecting N6705C...")
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

            self.is_connected = False
            self._update_connect_button_state(self.connect_btn, False)
            self.search_btn.setEnabled(True)

            self.append_log("[SYSTEM] N6705C disconnected.")
            self.set_system_status("N6705C disconnected")
            self.connection_status_changed.emit(False)

        except Exception as e:
            self.set_system_status("N6705C disconnect failed", is_error=True)
            self.append_log(f"[ERROR] N6705C disconnect failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_connect_scope(self):
        self.set_system_status("Connecting MSO64B...")
        self.append_log("[SYSTEM] Attempting MSO64B connection...")
        self.scope_connect_btn.setEnabled(False)

        try:
            resource = self.scope_resource_edit.text().strip()
            if resource:
                self.scope_resource = resource
                self.scope_connected = True
                self._update_connect_button_state(self.scope_connect_btn, True)
                self.append_log("[SYSTEM] MSO64B connected.")
                self.set_system_status("MSO64B connected")

                if self._mso64b_top:
                    self._mso64b_top.connect(resource)
            else:
                self.set_system_status("Invalid scope resource", is_error=True)
                self.append_log("[ERROR] Invalid scope resource.")

        except Exception as e:
            self.set_system_status("MSO64B connection failed", is_error=True)
            self.append_log(f"[ERROR] MSO64B connection failed: {str(e)}")
        finally:
            self.scope_connect_btn.setEnabled(True)

    def _on_disconnect_scope(self):
        self.set_system_status("Disconnecting MSO64B...")
        self.append_log("[SYSTEM] Disconnecting MSO64B...")
        self.scope_connect_btn.setEnabled(False)

        try:
            if self._mso64b_top and self._mso64b_top.is_connected:
                self._mso64b_top.disconnect()

            self.scope_resource = None
            self.scope_connected = False
            self._update_connect_button_state(self.scope_connect_btn, False)
            self.append_log("[SYSTEM] MSO64B disconnected.")
            self.set_system_status("MSO64B disconnected")

        except Exception as e:
            self.set_system_status("MSO64B disconnect failed", is_error=True)
            self.append_log(f"[ERROR] MSO64B disconnect failed: {str(e)}")
        finally:
            self.scope_connect_btn.setEnabled(True)

    def _on_start_or_abort_clicked(self):
        if self.is_test_running:
            self.set_test_running(False)
            self.append_log("[TEST] Abort requested by user.")
            self.stop_test_btn.click()
        else:
            self.set_test_running(True)

    def get_n6705c_instance(self):
        return self.n6705c

    def is_n6705c_connected(self):
        return self.is_connected
        