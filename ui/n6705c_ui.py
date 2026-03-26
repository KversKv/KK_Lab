#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N6705C电源分析仪UI组件
方案A修正版：
1. 底色统一
2. 删除 Channel 标题的外框感
3. 删除 SET MODE 按钮
4. 主按钮移动到 Voltage/Current 输入框下方
5. 保留仪器连接/测量/设置逻辑
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QGridLayout, QFrame, QApplication, QCheckBox,
    QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont
import pyvisa

from instruments.n6705c import N6705C


class _ConsumptionTestWorker(QObject):
    channel_result = Signal(int, float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, n6705c, channels, test_time, sample_period):
        super().__init__()
        self.n6705c = n6705c
        self.channels = channels
        self.test_time = test_time
        self.sample_period = sample_period
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            if self._is_stopped:
                self.finished.emit()
                return
            result = self.n6705c.fetch_current_by_datalog(
                self.channels, self.test_time, self.sample_period
            )
            for ch, avg_current in result.items():
                if self._is_stopped:
                    break
                self.channel_result.emit(ch, float(avg_current))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


class N6705CUI(QWidget):
    connection_status_changed = Signal(bool)

    CHANNEL_COLORS = {
        1: {"accent": "#d4a514", "bg": "#1a1708", "border": "#3d2e08"},
        2: {"accent": "#18b67a", "bg": "#081a14", "border": "#0a3d28"},
        3: {"accent": "#2f6fed", "bg": "#081028", "border": "#0c2a5e"},
        4: {"accent": "#d14b72", "bg": "#1a080e", "border": "#3d0c22"},
    }

    def __init__(self):
        super().__init__()

        self.rm = None
        self.instrument = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []
        self.current_channel = 1
        self.is_testing = False
        self._test_thread = None
        self._test_worker = None

        self.channel_themes = {
            1: {
                "accent": "#d4a514",
                "accent_hover": "#e3b729",
                "accent_soft": "#342808",
                "accent_border": "#7a5e12",
                "text_dim": "#c9b06a"
            },
            2: {
                "accent": "#18b67a",
                "accent_hover": "#21c487",
                "accent_soft": "#0a2a20",
                "accent_border": "#14694b",
                "text_dim": "#7bc7a8"
            },
            3: {
                "accent": "#2f6fed",
                "accent_hover": "#4680f0",
                "accent_soft": "#0c2048",
                "accent_border": "#264d9b",
                "text_dim": "#8db4ff"
            },
            4: {
                "accent": "#d14b72",
                "accent_hover": "#df5f85",
                "accent_soft": "#34111d",
                "accent_border": "#7e2f47",
                "text_dim": "#d79ab1"
            }
        }

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()

        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._search_devices)
        self.search_timer.setSingleShot(True)

        self._apply_channel_theme(self.current_channel)

    # =========================
    # 全局样式
    # =========================
    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setObjectName("RootWidget")

        self.setStyleSheet("""
        QWidget#RootWidget {
            background-color: #07111f;
        }

        QWidget {
            background-color: #07111f;
            color: #d6e2ff;
        }

        QLabel {
            color: #c8d6f0;
            background: transparent;
            border: none;
        }

        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #091426;
            border: 1px solid #17345f;
            border-radius: 6px;
            padding: 4px 6px;
            color: #d7e3ff;
        }

        QPushButton {
            background-color: #0b1730;
            border: 1px solid #23417a;
            border-radius: 6px;
            padding: 6px 14px;
            color: #dbe6ff;
        }

        QPushButton:hover {
            background-color: #10203e;
        }
        """)

    # =========================
    # 顶部栏
    # =========================
    def _create_top_bar(self):
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            QFrame {
                background-color: #07111f;
                border: 1px solid #132849;
                border-radius: 12px;
            }
        """)
        outer_layout = QVBoxLayout(top_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: #07111f;
                border: none;
            }
        """)
        header_widget.setFixedHeight(54)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(10)

        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("""
            QLabel {
                color: #00f5c4;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(icon_label)

        title_label = QLabel("Keysight N6705C DC Power Analyzer")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 800;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.all_on_btn = QPushButton("⏻ All On")
        self.all_on_btn.setStyleSheet(self._neon_on_button_style())

        self.all_off_btn = QPushButton("▢ All Off")
        self.all_off_btn.setStyleSheet(self._neon_off_button_style())

        header_layout.addWidget(self.all_on_btn)
        header_layout.addWidget(self.all_off_btn)

        outer_layout.addWidget(header_widget)

        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #07111f;
                border: none;
            }
            QLabel {
                color: #c8d1e6;
                font-size: 12px;
            }
            QComboBox, QLineEdit {
                background-color: #091426;
                color: #d0d8ea;
                border: 1px solid #17345f;
                border-radius: 8px;
                padding: 6px 10px;
            }
            QPushButton {
                background-color: #0b1730;
                color: #d0d0d0;
                border: 1px solid #23417a;
                border-radius: 8px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #10203e;
            }
        """)
        top_layout = QGridLayout(content_widget)
        top_layout.setContentsMargins(16, 8, 16, 14)
        top_layout.setHorizontalSpacing(10)
        top_layout.setVerticalSpacing(8)

        self.connection_status = QLabel("● 未连接")
        self.connection_status.setStyleSheet("color:#7fa1d9; font-weight:bold;")

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(320)
        self.device_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
        self.device_combo.setToolTip("选择要连接的设备")

        self.search_btn = QPushButton("搜索")
        self.connect_btn = QPushButton("连接")
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.setEnabled(False)

        top_layout.addWidget(QLabel("状态"), 0, 0)
        top_layout.addWidget(self.connection_status, 0, 1)

        top_layout.addWidget(QLabel("资源"), 1, 0)
        top_layout.addWidget(self.device_combo, 1, 1, 1, 3)
        top_layout.addWidget(self.search_btn, 1, 4)
        top_layout.addWidget(self.connect_btn, 1, 5)
        top_layout.addWidget(self.disconnect_btn, 1, 6)

        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.all_on_btn.clicked.connect(self._on_all_on_clicked)
        self.all_off_btn.clicked.connect(self._on_all_off_clicked)

        outer_layout.addWidget(content_widget)
        return top_frame

    # =========================
    # 主布局
    # =========================
    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(8, 8, 8, 8)

        self.top_bar = self._create_top_bar()
        main_layout.addWidget(self.top_bar)
        main_layout.addSpacing(8)   # 只保留顶部栏和 tabs 之间一点空隙

        self.channel_tabs = self._create_channel_tabs()
        main_layout.addWidget(self.channel_tabs)

        self.channels = []
        self.setting_widget = self._create_setting_widget()
        main_layout.addWidget(self.setting_widget, 1)

        self.consumption_test_panel = self._create_consumption_test_panel()
        main_layout.addWidget(self.consumption_test_panel)

    def _create_channel_tabs(self):
        tab_wrap = QWidget()
        tab_wrap.setAttribute(Qt.WA_StyledBackground, True)
        tab_wrap.setStyleSheet("""
            QWidget {
                background-color: #07111f;
                border: none;
            }
        """)

        layout = QHBoxLayout(tab_wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.channel_tab_buttons = []
        for i in range(1, 5):
            btn = QPushButton(f"• Channel {i}")
            btn.setCheckable(True)
            btn.setMinimumSize(104, 40)
            btn.clicked.connect(lambda checked=False, ch=i: self._switch_channel(ch))
            self.channel_tab_buttons.append(btn)
            layout.addWidget(btn)

        layout.addStretch()

        self.channel_tab_buttons[0].setChecked(True)
        self._refresh_channel_tab_styles()
        return tab_wrap

    def _create_setting_widget(self):
        self.setting_frame = QFrame()
        self.setting_frame.setStyleSheet("""
            QFrame {
                background-color: #0a1930;
                border: 1px solid #14305e;
                border-radius: 14px;
            }
        """)

        setting_layout = QVBoxLayout(self.setting_frame)
        setting_layout.setAlignment(Qt.AlignTop)
        setting_layout.setContentsMargins(12, 12, 12, 12)
        setting_layout.setSpacing(12)

        # ===== 顶部标题行：只保留纯标题，不要外框感 =====
        setting_header = QHBoxLayout()
        setting_header.setContentsMargins(0, 0, 0, 0)
        setting_header.setSpacing(12)

        self.channel_title_label = QLabel("Channel 1")
        self.channel_title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 800;
                color: #ffffff;
                padding: 0px;
                margin: 0px;
                border: none;
                background: transparent;
            }
        """)
        setting_header.addWidget(self.channel_title_label)

        self.cv_btn = QPushButton("PS2Q")
        self.cc_btn = QPushButton("CC")
        self.cr_btn = QPushButton("VMETer")
        self.cp_btn = QPushButton("AMETer")
        self.mode_buttons = [self.cv_btn, self.cc_btn, self.cr_btn, self.cp_btn]

        for btn in self.mode_buttons:
            btn.setCheckable(True)
            btn.setMinimumHeight(28)
            btn.clicked.connect(lambda checked=False, b=btn: self._on_mode_button_clicked(b))

        self.cv_btn.setChecked(True)

        mode_layout = QHBoxLayout()
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(0)
        for btn in self.mode_buttons:
            mode_layout.addWidget(btn)

        setting_header.addLayout(mode_layout)
        setting_header.addStretch()

        self.output_toggle = QPushButton()
        self.output_toggle.setCheckable(True)
        self.output_toggle.setFixedSize(46, 26)
        self.output_toggle.clicked.connect(self._on_output_toggle_clicked)
        setting_header.addWidget(self.output_toggle)

        setting_layout.addLayout(setting_header)

        # ===== 参数区 =====
        params_container = QFrame()
        params_container.setStyleSheet("""
            QFrame {
                background-color: #0a1930;
                border: 1px solid #132849;
                border-radius: 12px;
            }
        """)
        params_grid = QGridLayout(params_container)
        params_grid.setContentsMargins(8, 8, 8, 8)
        params_grid.setSpacing(12)

        # Voltage
        voltage_frame = QFrame()
        voltage_frame.setStyleSheet("""
            QFrame {
                background-color: #0b1b34;
                border: 1px solid #102746;
                border-radius: 12px;
            }
        """)
        voltage_layout = QVBoxLayout(voltage_frame)
        voltage_layout.setContentsMargins(14, 14, 14, 14)
        voltage_layout.setSpacing(8)

        voltage_label = QLabel("Voltage (V)")
        voltage_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #97aed9;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        voltage_layout.addWidget(voltage_label)

        self.voltage_value = QLineEdit("0.0000")
        self.voltage_value.setFrame(False)
        self.voltage_value.setStyleSheet("""
            QLineEdit {
                font-size: 22px;
                font-weight: bold;
                color: #6d83b3;
                background: transparent;
                border: none;
                outline: none;
                padding: 0px;
                margin: 0px;
            }
            QLineEdit:focus {
                border: none;
                outline: none;
                background: transparent;
            }
        """)
        self.voltage_value.setFixedHeight(40)
        voltage_layout.addWidget(self.voltage_value)

        voltage_input_row = QHBoxLayout()
        voltage_input_row.setSpacing(8)

        voltage_set_label = QLabel("SET")
        voltage_set_label.setStyleSheet("font-size: 12px; color: #7392cb; min-width: 28px;border: none;")
        voltage_input_row.addWidget(voltage_set_label)

        self.voltage_set_input = QLineEdit("5")
        self.voltage_set_input.setFixedHeight(34)
        voltage_input_row.addWidget(self.voltage_set_input)

        voltage_unit = QLabel("V")
        voltage_unit.setStyleSheet("font-size: 18px; color: #7fa1d9; min-width: 16px;border: none;")
        voltage_input_row.addWidget(voltage_unit)

        voltage_layout.addLayout(voltage_input_row)
        params_grid.addWidget(voltage_frame, 0, 0)

        # Current
        current_frame = QFrame()
        current_frame.setStyleSheet("""
            QFrame {
                background-color: #0b1b34;
                border: 1px solid #102746;
                border-radius: 12px;
            }
        """)
        current_layout = QVBoxLayout(current_frame)
        current_layout.setContentsMargins(14, 14, 14, 14)
        current_layout.setSpacing(8)

        current_label = QLabel("Current (A)")
        current_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #97aed9;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        current_layout.addWidget(current_label)

        self.current_value = QLineEdit("0.0000")
        self.current_value.setStyleSheet("""
            QLineEdit {
                font-size: 22px;
                font-weight: bold;
                color: #6d83b3;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.current_value.setFixedHeight(40)
        current_layout.addWidget(self.current_value)

        current_input_row = QHBoxLayout()
        current_input_row.setSpacing(8)

        current_set_label = QLabel("LIM")
        current_set_label.setStyleSheet("font-size: 12px; color: #7392cb; min-width: 28px;border: none;")
        current_input_row.addWidget(current_set_label)

        self.limit_current_value = QLineEdit("1")
        self.limit_current_value.setFixedHeight(34)
        current_input_row.addWidget(self.limit_current_value)

        current_unit = QLabel("A")
        current_unit.setStyleSheet("font-size: 18px; color: #7fa1d9; min-width: 16px;border: none;")
        current_input_row.addWidget(current_unit)

        current_layout.addLayout(current_input_row)
        params_grid.addWidget(current_frame, 0, 1)

        # 按钮区：位于输入框下面
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)

        self.on_button = QPushButton("⏻ On")
        self.on_button.setStyleSheet(self._neon_on_button_style())
        self.on_button.clicked.connect(lambda checked=False: self._on_channel_toggle(checked, self.current_channel))

        self.off_button = QPushButton("▢ Off")
        self.off_button.setStyleSheet(self._neon_off_button_style())
        self.off_button.clicked.connect(self._on_off_button_clicked)

        self.measure_btn = QPushButton("MEASURE")
        self.measure_btn.setStyleSheet(self._primary_action_button_style())
        self.measure_btn.clicked.connect(self._on_measure_button_clicked)

        self.set_btn = QPushButton("SET")
        self.set_btn.setStyleSheet(self._primary_action_button_style())
        self.set_btn.clicked.connect(self._on_set_button_clicked)

        action_row.addWidget(self.on_button)
        action_row.addWidget(self.off_button)
        action_row.addStretch()
        action_row.addWidget(self.measure_btn)
        action_row.addWidget(self.set_btn)

        params_grid.addLayout(action_row, 1, 0, 1, 2)

        setting_layout.addWidget(params_container)

        # ===== 一键调整 =====
        tools_container = QFrame()
        tools_container.setStyleSheet("""
            QFrame {
                background-color: #0a1930;
                border: 1px solid #132849;
                border-radius: 12px;
            }
        """)
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setContentsMargins(12, 12, 12, 12)
        tools_layout.setSpacing(10)

        tools_title = QLabel("一键调整")
        tools_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        tools_layout.addWidget(tools_title)

        channel_select_layout = QHBoxLayout()
        channel_select_layout.setSpacing(10)

        channel_select_label = QLabel("通道选择:")
        channel_select_label.setStyleSheet("font-size: 11px; color: #8ea6cf;border: none;")
        channel_select_layout.addWidget(channel_select_label)

        self.channel_checkboxes = []
        for i in range(1, 5):
            checkbox = QPushButton(f"通道 {i}")
            checkbox.setCheckable(True)
            if i in [2, 3, 4]:
                checkbox.setChecked(True)
            checkbox.setStyleSheet(self._batch_channel_button_style())
            self.channel_checkboxes.append(checkbox)
            channel_select_layout.addWidget(checkbox)

        channel_select_layout.addStretch()
        tools_layout.addLayout(channel_select_layout)

        voltage_set_layout = QHBoxLayout()
        voltage_set_layout.setSpacing(10)

        voltage_set_label = QLabel("电压设置(V):")
        voltage_set_label.setStyleSheet("font-size: 11px; color: #8ea6cf;border: none;")
        voltage_set_layout.addWidget(voltage_set_label)

        self.voltage_inputs = []
        for voltage in [3.8, 0.8, 1.2, 1.8]:
            input_box = QLineEdit(f"{voltage:.4f}")
            input_box.setFixedWidth(92)
            self.voltage_inputs.append(input_box)
            voltage_set_layout.addWidget(input_box)

        voltage_set_layout.addStretch()
        tools_layout.addLayout(voltage_set_layout)

        current_limit_layout = QHBoxLayout()
        current_limit_layout.setSpacing(10)

        current_limit_label = QLabel("限流设置(A):")
        current_limit_label.setStyleSheet("font-size: 11px; color: #8ea6cf;border: none;")
        current_limit_layout.addWidget(current_limit_label)

        self.current_limit_inputs = []
        for current in [0.2, 0.02, 0.02, 0.02]:
            input_box = QLineEdit(f"{current:.4f}")
            input_box.setFixedWidth(92)
            self.current_limit_inputs.append(input_box)
            current_limit_layout.addWidget(input_box)

        current_limit_layout.addStretch()
        tools_layout.addLayout(current_limit_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        measure_all_btn = QPushButton("Measure")
        set_all_btn = QPushButton("Set")
        auto_btn = QPushButton("Auto")

        for btn in [measure_all_btn, set_all_btn, auto_btn]:
            btn.setStyleSheet(self._primary_action_button_style())
            buttons_layout.addWidget(btn)

        measure_all_btn.clicked.connect(self._on_measure_all_clicked)
        set_all_btn.clicked.connect(self._on_set_all_clicked)
        auto_btn.clicked.connect(self._on_auto_clicked)

        buttons_layout.addStretch()
        tools_layout.addLayout(buttons_layout)

        setting_layout.addWidget(tools_container)

        channel_data = {
            'on_button': self.on_button,
            'off_button': self.off_button,
            'voltage_value': self.voltage_value,
            'current_value': self.current_value,
            'limit_current_value': self.limit_current_value,
            'voltage_set_input': self.voltage_set_input,
            'set_btn': self.set_btn,
            'toggle': self.output_toggle
        }
        self.channels.append(channel_data)

        return self.setting_frame

    # =========================
    # Current Consumption Test
    # =========================
    def _create_consumption_test_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #0a1930;
                border: 1px solid #132849;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 16px; color: #f2c94c;")
        title = QLabel("Current Consumption Test")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch()

        self.ct_save_btn = QPushButton("💾 Save DataLog")
        self.ct_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0b1730;
                color: #dbe6ff;
                border: 1px solid #23417a;
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 10px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #10203e; }
        """)
        header_row.addWidget(self.ct_save_btn)
        layout.addLayout(header_row)

        params_row = QHBoxLayout()
        params_row.setSpacing(12)

        time_label = QLabel("Test Time (s)")
        time_label.setStyleSheet("font-size: 11px; color: #8ea6cf;")
        self.ct_test_time_input = QLineEdit("10")
        self.ct_test_time_input.setFixedWidth(80)
        self.ct_test_time_input.setAlignment(Qt.AlignCenter)

        period_label = QLabel("Sample Period (s)")
        period_label.setStyleSheet("font-size: 11px; color: #8ea6cf;")
        self.ct_sample_period_input = QLineEdit("0.001")
        self.ct_sample_period_input.setFixedWidth(80)
        self.ct_sample_period_input.setAlignment(Qt.AlignCenter)

        params_row.addWidget(time_label)
        params_row.addWidget(self.ct_test_time_input)
        params_row.addSpacing(8)
        params_row.addWidget(period_label)
        params_row.addWidget(self.ct_sample_period_input)
        params_row.addStretch()
        layout.addLayout(params_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.ct_start_btn = QPushButton("▶ START TEST")
        self.ct_start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ct_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #062b2b;
                color: #00f5c4;
                border: 1px solid #00cfa6;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                min-height: 38px;
            }
            QPushButton:hover { background-color: #0a3a3a; }
            QPushButton:disabled {
                background-color: #0b1730;
                color: #5a6b8e;
                border: 1px solid #1b2847;
            }
        """)

        self.ct_stop_btn = QPushButton("🟥 STOP")
        self.ct_stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ct_stop_btn.setEnabled(False)
        self.ct_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a0a1c;
                color: #ff4fa3;
                border: 1px solid #d63384;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                min-height: 38px;
            }
            QPushButton:hover { background-color: #3a1028; }
            QPushButton:disabled {
                background-color: #0b1730;
                color: #5a6b8e;
                border: 1px solid #1b2847;
            }
        """)

        btn_row.addWidget(self.ct_start_btn, 1)
        btn_row.addWidget(self.ct_stop_btn, 1)
        layout.addLayout(btn_row)

        channels_row = QHBoxLayout()
        channels_row.setSpacing(10)

        self.ct_channel_cards = {}
        for ch in range(1, 5):
            card = self._create_ct_channel_card(ch)
            channels_row.addWidget(card, 1)

        layout.addLayout(channels_row, 1)

        self.ct_start_btn.clicked.connect(self._ct_start_test)
        self.ct_stop_btn.clicked.connect(self._ct_stop_test)
        self.ct_save_btn.clicked.connect(self._ct_save_datalog)

        return panel

    def _get_checkmark_path(self, accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

    def _create_ct_channel_card(self, ch_num):
        colors = self.CHANNEL_COLORS[ch_num]

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg']};
                border: 1px solid {colors['border']};
                border-radius: 10px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(100)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        checkbox = QCheckBox(f"CH {ch_num}")
        checkbox.setChecked(False)
        icons = self._get_checkmark_path(colors['accent'])
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                image: url("{icons['unchecked']}");
            }}
            QCheckBox::indicator:checked {{
                image: url("{icons['checked']}");
            }}
        """)

        top_row.addWidget(checkbox)
        top_row.addStretch()
        layout.addLayout(top_row)

        layout.addStretch()

        avg_label = QLabel("AVG CURRENT")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setStyleSheet("color: #8ea6cf; font-size: 11px; font-weight: 600;")
        layout.addWidget(avg_label)

        value_label = QLabel("- - -")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['accent']};
                font-size: 18px;
                font-weight: 700;
                letter-spacing: 4px;
            }}
        """)
        layout.addWidget(value_label)

        layout.addStretch()

        self.ct_channel_cards[ch_num] = {
            "card": card,
            "checkbox": checkbox,
            "value_label": value_label,
        }

        return card

    @staticmethod
    def _format_current(current_A):
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.3f} A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.3f} mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.3f} µA"
        elif abs_i >= 1e-9:
            return f"{current_A*1e9:.3f} nA"
        else:
            return f"{current_A:.3e} A"

    def _ct_start_test(self):
        if self.is_testing:
            return
        if not self.is_connected or not self.n6705c:
            self.connection_status.setText("请先连接N6705C")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            return

        selected_channels = [
            ch for ch in range(1, 5)
            if self.ct_channel_cards[ch]["checkbox"].isChecked()
        ]
        if not selected_channels:
            return

        try:
            test_time = float(self.ct_test_time_input.text())
            sample_period = float(self.ct_sample_period_input.text())
        except ValueError:
            return

        self.is_testing = True
        self.ct_start_btn.setEnabled(False)
        self.ct_stop_btn.setEnabled(True)

        for ch in range(1, 5):
            self.ct_channel_cards[ch]["value_label"].setText("- - -")

        worker = _ConsumptionTestWorker(
            self.n6705c, selected_channels, test_time, sample_period
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.channel_result.connect(self._ct_on_channel_result)
        worker.error.connect(self._ct_on_error)
        worker.finished.connect(self._ct_on_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._ct_on_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        thread.start()

    def _ct_on_channel_result(self, channel, avg_current):
        if channel in self.ct_channel_cards:
            label = self.ct_channel_cards[channel]["value_label"]
            if avg_current is not None:
                label.setText(self._format_current(avg_current))
            else:
                label.setText("- - -")

    def _ct_on_error(self, err_msg):
        print(f"Consumption test error: {err_msg}")

    def _ct_on_finished(self):
        self.is_testing = False
        self.ct_start_btn.setEnabled(True)
        self.ct_stop_btn.setEnabled(False)

    def _ct_on_thread_cleaned(self):
        self._test_worker = None
        self._test_thread = None

    def _ct_stop_test(self):
        if self._test_worker:
            self._test_worker.stop()
        self.is_testing = False
        self.ct_start_btn.setEnabled(True)
        self.ct_stop_btn.setEnabled(False)

    def _ct_save_datalog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DataLog", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            print(f"Saving datalog to: {file_path}")

    # =========================
    # 样式工具
    # =========================
    def _neon_on_button_style(self):
        return """
        QPushButton {
            background-color: #062b2b;
            color: #00f5c4;
            border: 1px solid #00cfa6;
            border-radius: 8px;
            padding: 8px 18px;
            min-width: 88px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #0a3a3a;
            border: 1px solid #00f5c4;
            color: #3fffd7;
        }
        """

    def _neon_off_button_style(self):
        return """
        QPushButton {
            background-color: #2a0a1c;
            color: #ff4fa3;
            border: 1px solid #d63384;
            border-radius: 8px;
            padding: 8px 18px;
            min-width: 88px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #3a1028;
            border: 1px solid #ff4fa3;
            color: #ff7dbd;
        }
        """

    def _primary_action_button_style(self):
        return """
        QPushButton {
            background-color: #2a64c8;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 11px;
            min-width: 88px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #3672dc;
        }
        """

    def _batch_channel_button_style(self):
        return """
            QPushButton {
                background-color: #25314a;
                color: #91a7d1;
                border: 1px solid #31476f;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                min-width: 60px;
            }
            QPushButton:checked {
                background-color: #2a64c8;
                color: white;
            }
            QPushButton:hover {
                background-color: #31405f;
            }
        """

    def _build_channel_tab_style(self, ch, checked=False):
        theme = self.channel_themes[ch]
        if checked:
            return f"""
            QPushButton {{
                background-color: #0b1730;
                color: #ffffff;
                border: 1px solid {theme['accent_border']};
                border-bottom: 2px solid {theme['accent']};
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 700;
                text-align: left;
            }}
            """
        else:
            return f"""
            QPushButton {{
                background-color: #08132b;
                color: {theme['text_dim']};
                border: 1px solid #12284e;
                border-bottom: 2px solid transparent;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 700;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_soft']};
                color: #ffffff;
                border: 1px solid {theme['accent_border']};
            }}
            """

    def _build_mode_button_style(self, active=False):
        theme = self.channel_themes[self.current_channel]
        if active:
            return f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: #111111;
                border: 1px solid {theme['accent_hover']};
                padding: 5px 14px;
                font-size: 12px;
                font-weight: 700;
                border-radius: 0px;
            }}
            """
        else:
            return """
            QPushButton {
                background-color: #08111f;
                color: #7c8aac;
                border: 1px solid #1b2842;
                padding: 5px 14px;
                font-size: 12px;
                border-radius: 0px;
            }
            QPushButton:hover {
                background-color: #0c1628;
                color: #dbe6ff;
            }
            """

    def _apply_mode_button_styles(self):
        for btn in self.mode_buttons:
            btn.setStyleSheet(self._build_mode_button_style(btn.isChecked()))
        if self.mode_buttons:
            self.mode_buttons[0].setStyleSheet(
                self.mode_buttons[0].styleSheet() + "QPushButton {border-top-left-radius: 8px; border-bottom-left-radius: 8px;}"
            )
            self.mode_buttons[-1].setStyleSheet(
                self.mode_buttons[-1].styleSheet() + "QPushButton {border-top-right-radius: 8px; border-bottom-right-radius: 8px;}"
            )

    def _refresh_channel_tab_styles(self):
        for i, btn in enumerate(self.channel_tab_buttons, start=1):
            btn.setStyleSheet(self._build_channel_tab_style(i, i == self.current_channel))
            btn.setChecked(i == self.current_channel)

    def _apply_channel_theme(self, channel_num):
        theme = self.channel_themes[channel_num]

        self.channel_title_label.setText(f"Channel {channel_num}")

        self.setting_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #0a1930;
                border: 1px solid {theme['accent_border']};
                border-radius: 14px;
            }}
        """)

        self.output_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: #25314a;
                border: none;
                border-radius: 13px;
            }}
            QPushButton:checked {{
                background-color: {theme['accent']};
                border: none;
                border-radius: 13px;
            }}
        """)

        self._refresh_channel_tab_styles()
        self._apply_mode_button_styles()

    # =========================
    # 初始化
    # =========================
    def _init_ui_elements(self):
        pass

    # =========================
    # 通道/模式
    # =========================
    def _switch_channel(self, channel_num):
        self.current_channel = channel_num
        self._apply_channel_theme(channel_num)

    def _on_mode_button_clicked(self, clicked_button):
        for btn in self.mode_buttons:
            btn.setChecked(btn is clicked_button)
        self._apply_mode_button_styles()
        
        # 立即设置模式到仪器
        if self.is_connected and self.n6705c:
            try:
                channel_num = self.current_channel
                ui_mode = self._get_current_mode_text()
                inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
                self.n6705c.set_mode(channel_num, inst_mode)
                print(f"通道{channel_num}模式已设置为: {inst_mode}")
            except Exception as e:
                print(f"设置模式失败: {str(e)}")

    def _get_current_mode_text(self):
        if self.cv_btn.isChecked():
            return "PS2Q"
        if self.cc_btn.isChecked():
            return "CC"
        if self.cr_btn.isChecked():
            return "VMETer"
        if self.cp_btn.isChecked():
            return "AMETer"
        return "PS2Q"

    def _map_ui_mode_to_instrument_mode(self, ui_mode):
        mapping = {
            "PS2Q": "PS2Q",
            "CC": "CCLoad",
            "VMETer": "VMETer",
            "AMETer": "AMETer",
        }
        return mapping.get(ui_mode, "PS2Q")

    # =========================
    # 数据接口
    # =========================
    def get_channel_settings(self, channel_num):
        if 1 <= channel_num <= 4 and self.channels:
            channel = self.channels[0]
            return {
                'enabled': channel['toggle'].isChecked(),
                'voltage_set': float(channel['voltage_set_input'].text()),
                'current_set': float(channel['current_value'].text()),
                'current_limit': float(channel['limit_current_value'].text())
            }
        return None

    def update_channel_values(self, channel_num, voltage, current, limit_current):
        if 1 <= channel_num <= 4 and self.channels:
            channel = self.channels[0]
            channel['voltage_value'].setText(f"{voltage:.4f}")
            channel['current_value'].setText(f"{current:.4f}")
            channel['limit_current_value'].setText(f"{limit_current:.4f}")

    def get_channel_toggle(self, channel_num):
        if 1 <= channel_num <= 4 and self.channels:
            return self.channels[0]['toggle']
        return None

    def set_all_channels_enabled(self, enabled):
        for channel in self.channels:
            channel['toggle'].setChecked(enabled)

    # =========================
    # 连接逻辑
    # =========================
    def _on_search(self):
        self.connection_status.setText("搜索中...")
        self.connection_status.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
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

            print(f"找到 {len(self.available_devices)} 个设备")
            for dev in self.available_devices:
                print(f"设备地址: {dev}")

            compatible_devices = self.available_devices.copy() if self.available_devices else []
            n6705c_devices = []

            for dev in compatible_devices:
                try:
                    instr = self.rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    print(f"设备 {dev} 的IDN: {idn}")
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception as e:
                    print(f"查询设备 {dev} 失败: {str(e)}")

            self.device_combo.clear()
            self.device_combo.setEnabled(True)

            if n6705c_devices:
                for dev in n6705c_devices:
                    self.device_combo.addItem(dev)

                self.connection_status.setText(f"找到 {len(n6705c_devices)} 个N6705C设备")
                self.connection_status.setStyleSheet("color: #00a859; padding: 10px; font-weight: bold;")
                self.connect_btn.setEnabled(True)

                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    self.device_combo.setCurrentText(default_device)
                else:
                    self.device_combo.setCurrentIndex(0)
            else:
                self.device_combo.addItem("未找到N6705C设备")
                self.device_combo.setEnabled(False)
                self.connection_status.setText("未找到N6705C设备")
                self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
                self.connect_btn.setEnabled(False)

        except Exception as e:
            print(f"搜索过程中发生错误: {str(e)}")
            self.connection_status.setText(f"搜索失败: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.connect_btn.setEnabled(False)
        finally:
            self.search_btn.setEnabled(True)

    def _on_connect(self):
        self.connection_status.setText("连接中...")
        self.connection_status.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
        self.connect_btn.setEnabled(False)

        try:
            device_address = self.device_combo.currentText()
            self.n6705c = N6705C(device_address)

            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self.is_connected = True
                self.connection_status.setText("已连接")
                self.connection_status.setStyleSheet("color: #00a859; padding: 10px; font-weight: bold;")
                self.disconnect_btn.setEnabled(True)
                self.connection_status_changed.emit(True)
            else:
                self.connection_status.setText("设备不匹配")
                self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
                self.connect_btn.setEnabled(True)

        except Exception as e:
            self.connection_status.setText(f"连接失败: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.connect_btn.setEnabled(True)

    def _on_disconnect(self):
        self.connection_status.setText("断开中...")
        self.connection_status.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
        self.disconnect_btn.setEnabled(False)

        try:
            if hasattr(self.n6705c, 'instr') and self.n6705c and self.n6705c.instr:
                self.n6705c.instr.close()
            if hasattr(self.n6705c, 'rm') and self.n6705c and self.n6705c.rm:
                self.n6705c.rm.close()

            self.instrument = None
            self.n6705c = None
            self.is_connected = False

            self.connection_status.setText("未连接")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.connect_btn.setEnabled(True)
            self.connection_status_changed.emit(False)

        except Exception as e:
            self.connection_status.setText(f"断开失败: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.disconnect_btn.setEnabled(True)

    # =========================
    # 单通道操作
    # =========================
    def _on_channel_toggle(self, unused_checked=False, channel_num=None):
        if channel_num is None:
            channel_num = self.current_channel

        if self.is_connected and self.n6705c:
            try:
                self.n6705c.channel_on(channel_num)
                self.output_toggle.setChecked(True)
                print(f"通道{channel_num}已打开")
            except Exception as e:
                print(f"打开通道{channel_num}失败: {str(e)}")
        else:
            self.output_toggle.setChecked(True)

    def _on_off_button_clicked(self):
        channel_num = self.current_channel
        if self.is_connected and self.n6705c:
            try:
                self.n6705c.channel_off(channel_num)
                print(f"通道{channel_num}已关闭")
            except Exception as e:
                print(f"关闭通道{channel_num}失败: {str(e)}")

        self.output_toggle.setChecked(False)

    def _on_output_toggle_clicked(self, checked):
        channel_num = self.current_channel
        if checked:
            self._on_channel_toggle(True, channel_num)
        else:
            self._on_off_button_clicked()

    def _on_set_button_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            channel_num = self.current_channel
            voltage_set = float(self.voltage_set_input.text())
            current_set = float(self.current_value.text())
            limit_current_set = float(self.limit_current_value.text())

            ui_mode = self._get_current_mode_text()
            inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
            self.n6705c.set_mode(channel_num, inst_mode)

            self.n6705c.set_voltage(channel_num, voltage_set)
            self.n6705c.set_current(channel_num, current_set)
            self.n6705c.set_current_limit(channel_num, limit_current_set)

            print(f"通道{channel_num}设置已发送 - 模式: {inst_mode}, 电压: {voltage_set}V, 电流: {current_set}A, 电流限制: {limit_current_set}A")
        except Exception as e:
            print(f"设置发送失败: {str(e)}")

    def _on_measure_button_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            channel_num = self.current_channel
            voltage = float(self.n6705c.measure_voltage(channel_num))
            current = float(self.n6705c.measure_current(channel_num))
            limit_current = float(self.n6705c.get_current_limit(channel_num))
            self.update_channel_values(channel_num, voltage, current, limit_current)
            print(f"通道{channel_num}测量值 - 电压: {voltage:.4f}V, 电流: {current:.4f}A, 电流限制: {limit_current:.4f}A")
        except Exception as e:
            print(f"测量失败: {str(e)}")

    # =========================
    # 全通道操作
    # =========================
    def _on_all_on_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            for ch in range(1, 5):
                self.n6705c.channel_on(ch)
            self.output_toggle.setChecked(True)
            print("所有通道已打开")
        except Exception as e:
            print(f"All On 失败: {str(e)}")

    def _on_all_off_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            for ch in range(1, 5):
                self.n6705c.channel_off(ch)
            self.output_toggle.setChecked(False)
            print("所有通道已关闭")
        except Exception as e:
            print(f"All Off 失败: {str(e)}")

    # =========================
    # 批量操作
    # =========================
    def _on_measure_all_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            selected_channels = [i + 1 for i, checkbox in enumerate(self.channel_checkboxes) if checkbox.isChecked()]
            if not selected_channels:
                print("未选择任何通道")
                return
            for channel_num in selected_channels:
                self.n6705c.set_mode(channel_num, "VMETer")
                print(f"通道{channel_num}已设置为电压表模式")
        except Exception as e:
            print(f"设置电压表模式失败: {str(e)}")

    def _on_set_all_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            selected_channels = [i + 1 for i, checkbox in enumerate(self.channel_checkboxes) if checkbox.isChecked()]
            if not selected_channels:
                print("未选择任何通道")
                return

            voltages = [float(self.voltage_inputs[i].text()) for i in range(4)]
            current_limits = [float(self.current_limit_inputs[i].text()) for i in range(4)]

            for channel_num in selected_channels:
                idx = channel_num - 1
                voltage = voltages[idx]
                current_limit = current_limits[idx]
                self.n6705c.set_mode(channel_num, "PS2Q")
                self.n6705c.set_voltage(channel_num, voltage)
                self.n6705c.set_current_limit(channel_num, current_limit)
                self.n6705c.channel_on(channel_num)
                print(f"通道{channel_num}设置已发送 - 电压: {voltage}V, 电流限制: {current_limit}A")
        except Exception as e:
            print(f"设置发送失败: {str(e)}")

    def _on_auto_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            selected_channels = [i + 1 for i, checkbox in enumerate(self.channel_checkboxes) if checkbox.isChecked()]
            if not selected_channels:
                print("未选择任何通道")
                return

            for channel_num in selected_channels:
                self.n6705c.set_mode(channel_num, "VMETer")
                measured_voltage = float(self.n6705c.measure_voltage(channel_num))
                print(f"通道{channel_num}测量电压: {measured_voltage:.4f}V")

                new_voltage = measured_voltage + 0.01
                print(f"通道{channel_num}新电压: {new_voltage:.4f}V")

                self.n6705c.set_mode(channel_num, "PS2Q")
                self.n6705c.set_voltage(channel_num, new_voltage)
                self.n6705c.channel_on(channel_num)
                print(f"通道{channel_num}已打开")
        except Exception as e:
            print(f"Auto操作失败: {str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = N6705CUI()
    win.setWindowTitle("N6705C测试系统")
    win.setGeometry(100, 100, 1200, 820)
    win.show()

    sys.exit(app.exec())
