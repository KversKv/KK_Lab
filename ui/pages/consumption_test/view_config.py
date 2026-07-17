#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test 配置面板视图构建（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - _create_test_config_panel     : Test Config 面板（Test Time / Control / MCU / PwrON / Reset）
  - _on_control_method_changed    : N6705C ↔ MCU 切换联动
  - _on_reset_enable_toggled      : Reset 使能联动
  - _create_channel_config_section: Channel Config 滚动区
  - _add_channel_config_card      : 单个通道配置卡片
  - _on_config_enable_changed / _update_card_disabled_state
  - _on_config_name_changed / _on_config_channel_changed
  - _on_force_mode_changed / _on_force_value_changed / _on_boost_mode_changed / _on_boost_value_changed
  - _remove_channel_config

依赖宿主类（ConsumptionTestUI）提供：
  - self.NAME_OPTIONS / self._channel_configs / self._channel_config_widgets
  - self._channel_config_row / self._saved_control_channels / self._current_control_method
  - self._get_available_channel_options() / self._get_control_channel_options()
  - self._set_combo_options() / self._refresh_result_cards()
  - self._on_mcu_search() / self._on_mcu_connect_or_disconnect()
"""

import os

from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.pages.consumption_test.widgets import (
    ControlMethodToggle, PolarityToggle, BinaryTextToggle,
)
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.button import SpinningSearchButton
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox,
    QScrollArea, QWidget, QSizePolicy, QStackedLayout,
)
from PySide6.QtCore import Qt


_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "consumption_test_SVGs"
)


class ConsumptionTestViewConfigMixin:

    def _create_test_config_panel(self):
        config_frame = QFrame()
        config_frame.setObjectName("testConfigPanel")
        config_frame.setStyleSheet("""
            QFrame#testConfigPanel {
                background-color: #0a1228;
                border: 1px solid #1a2d57;
                border-radius: 12px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(12, 10, 12, 10)
        config_layout.setSpacing(8)

        config_header = QHBoxLayout()
        config_header.setSpacing(6)
        cfg_icon = QLabel()
        _wrench_svg = os.path.join(_PAGE_SVGS_DIR, "wrench.svg")
        if os.path.isfile(_wrench_svg):
            cfg_icon.setPixmap(_tinted_svg_icon(_wrench_svg, "#c8d6f0", 14).pixmap(14, 14))
        cfg_icon.setFixedSize(16, 16)
        cfg_icon.setStyleSheet("background: transparent; border: none;")
        cfg_title = QLabel("Test Config")
        cfg_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
        config_header.addWidget(cfg_icon)
        config_header.addWidget(cfg_title)
        config_header.addStretch()
        config_layout.addLayout(config_header)

        label_style = "font-size: 11px; color: #7e96bf;"
        label_width = 72

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        time_label = QLabel("Test Time (s)")
        time_label.setStyleSheet(label_style)
        time_label.setFixedWidth(label_width)
        self.test_time_input = QLineEdit("10")
        self.test_time_input.setFixedHeight(24)
        self.test_time_input.setAlignment(Qt.AlignCenter)
        self.test_time_input.setStyleSheet("""
            QLineEdit {
                background-color: #020816;
                border: 1px solid #1c2f54;
                border-radius: 6px;
                padding: 2px 8px;
                color: #d7e3ff;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #5b7cff;
            }
        """)
        grid.addWidget(time_label, 0, 0, Qt.AlignVCenter)
        grid.addWidget(self.test_time_input, 0, 1, Qt.AlignVCenter)

        method_label = QLabel("Control")
        method_label.setStyleSheet(label_style)
        method_label.setFixedWidth(label_width)
        self.control_method_toggle = ControlMethodToggle()
        self.control_method_toggle.setFixedWidth(140)
        method_ctrl_row = QHBoxLayout()
        method_ctrl_row.setSpacing(0)
        method_ctrl_row.addWidget(self.control_method_toggle)
        method_ctrl_row.addStretch()
        grid.addWidget(method_label, 1, 0, Qt.AlignVCenter)
        grid.addLayout(method_ctrl_row, 1, 1)

        label_style_sm = "font-size: 10px; color: #7e96bf;"

        mcu_block = QVBoxLayout()
        mcu_block.setContentsMargins(0, 0, 0, 0)
        mcu_block.setSpacing(4)
        mcu_type_row = QHBoxLayout()
        mcu_type_row.setContentsMargins(0, 0, 0, 0)
        mcu_type_row.setSpacing(4)
        mcu_port_row = QHBoxLayout()
        mcu_port_row.setContentsMargins(0, 0, 0, 0)
        mcu_port_row.setSpacing(4)
        mcu_status_row = QHBoxLayout()
        mcu_status_row.setContentsMargins(0, 0, 0, 0)
        mcu_status_row.setSpacing(4)

        self.mcu_type_label = QLabel("MCU")
        self.mcu_type_label.setStyleSheet(label_style)
        self.mcu_type_label.setFixedWidth(label_width)
        self.mcu_com_label = QLabel("COM")
        self.mcu_com_label.setStyleSheet(label_style)
        self.mcu_com_label.setFixedWidth(label_width)

        self.mcu_status_label = QLabel("● Disconnected")
        self.mcu_status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.mcu_status_label.setStyleSheet(
            "color: #8ea6cf; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_port_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.mcu_port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mcu_port_combo.setFixedHeight(24)
        self.mcu_port_combo.setMinimumContentsLength(8)
        self.mcu_port_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.mcu_port_combo.addItem("Select MCU COM...")
        font = self.mcu_port_combo.font()
        font.setPixelSize(11)
        self.mcu_port_combo.setFont(font)
        self.mcu_search_btn = SpinningSearchButton(parent=config_frame)
        self.mcu_search_btn.setFixedSize(24, 24)
        self.mcu_type_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.mcu_type_combo.setFixedHeight(24)
        self.mcu_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mcu_type_combo.setMinimumContentsLength(8)
        self.mcu_type_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.mcu_type_combo.addItem("YD-RP2040", userData="yd_rp2040")
        self.mcu_type_combo.addItem("CH9114F", userData="ch9114f")
        # 默认选中 CH9114F
        self.mcu_type_combo.setCurrentIndex(1)
        font = self.mcu_type_combo.font()
        font.setPixelSize(11)
        self.mcu_type_combo.setFont(font)
        self.mcu_connect_btn = QPushButton("Connect")
        self.mcu_connect_btn.setFixedHeight(24)
        self.mcu_connect_btn.setFixedWidth(88)
        self.mcu_connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #053b38;
                border: 1px solid #08c9a5;
                border-radius: 6px;
                color: #10e7bc;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 8px;
            }
            QPushButton:hover { background-color: #064744; }
            QPushButton:disabled {
                background-color: #0D1734;
                color: #3a4a6a;
                border: 1px solid #18264A;
            }
        """)
        mcu_type_row.addWidget(self.mcu_type_combo, 1)
        mcu_type_row.addSpacing(28)
        mcu_port_row.addWidget(self.mcu_port_combo, 1)
        mcu_port_row.addWidget(self.mcu_search_btn, 0, Qt.AlignVCenter)
        mcu_status_row.addWidget(self.mcu_status_label, 0, Qt.AlignVCenter)
        mcu_status_row.addStretch()
        mcu_status_row.addWidget(self.mcu_connect_btn, 0, Qt.AlignVCenter)
        grid.addWidget(self.mcu_type_label, 2, 0, Qt.AlignVCenter)
        grid.addLayout(mcu_type_row, 2, 1)
        grid.addWidget(self.mcu_com_label, 3, 0, Qt.AlignVCenter)
        grid.addLayout(mcu_port_row, 3, 1)
        grid.addLayout(mcu_status_row, 4, 1)

        poweron_label = QLabel("PwrON")
        poweron_label.setStyleSheet(label_style_sm)
        poweron_label.setFixedWidth(label_width)
        self.poweron_channel_combo = DarkComboBox()
        self.poweron_channel_combo.setFixedHeight(24)
        self.poweron_channel_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.poweron_channel_combo.font()
        font.setPixelSize(11)
        self.poweron_channel_combo.setFont(font)
        for opt in self._get_available_channel_options():
            self.poweron_channel_combo.addItem(opt)
        for i in range(self.poweron_channel_combo.count()):
            if self.poweron_channel_combo.itemText(i) == "B-CH1":
                self.poweron_channel_combo.setCurrentIndex(i)
                break
        self.poweron_polarity_toggle = PolarityToggle()
        poweron_row = QHBoxLayout()
        poweron_row.setContentsMargins(0, 0, 0, 0)
        poweron_row.setSpacing(4)
        poweron_row.addWidget(self.poweron_channel_combo, 1)
        poweron_row.addWidget(self.poweron_polarity_toggle, 0, Qt.AlignVCenter)

        reset_label_row = QHBoxLayout()
        reset_label_row.setContentsMargins(0, 0, 0, 0)
        reset_label_row.setSpacing(4)
        reset_label = QLabel("Reset")
        reset_label.setStyleSheet(label_style_sm)
        self.reset_enable_cb = QCheckBox()
        self.reset_enable_cb.setChecked(False)
        self.reset_enable_cb.setToolTip("Enable Reset channel. When unchecked, RESET step is skipped.")
        self.reset_enable_cb.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
                background: transparent;
            }
        """)
        reset_label_row.addWidget(reset_label)
        reset_label_row.addWidget(self.reset_enable_cb)
        reset_label_row.addStretch()
        reset_label_container = QWidget()
        reset_label_container.setFixedWidth(label_width)
        reset_label_container.setLayout(reset_label_row)

        self.reset_channel_combo = DarkComboBox()
        self.reset_channel_combo.setFixedHeight(24)
        self.reset_channel_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.reset_channel_combo.font()
        font.setPixelSize(11)
        self.reset_channel_combo.setFont(font)
        for opt in self._get_available_channel_options():
            self.reset_channel_combo.addItem(opt)
        for i in range(self.reset_channel_combo.count()):
            if self.reset_channel_combo.itemText(i) == "B-CH2":
                self.reset_channel_combo.setCurrentIndex(i)
                break
        self.reset_polarity_toggle = PolarityToggle()
        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 0, 0, 0)
        reset_row.setSpacing(4)
        reset_row.addWidget(self.reset_channel_combo, 1)
        reset_row.addWidget(self.reset_polarity_toggle, 0, Qt.AlignVCenter)

        self._n6705c_poweron_label = poweron_label
        self._n6705c_reset_label = reset_label
        self._n6705c_reset_label_container = reset_label_container
        self._mcu_row_widgets = [
            self.mcu_type_label,
            self.mcu_type_combo,
            self.mcu_com_label,
            self.mcu_port_combo,
            self.mcu_search_btn,
            self.mcu_status_label,
            self.mcu_connect_btn,
        ]
        grid.addWidget(poweron_label, 5, 0, Qt.AlignVCenter)
        grid.addLayout(poweron_row, 5, 1)
        grid.addWidget(reset_label_container, 6, 0, Qt.AlignVCenter)
        grid.addLayout(reset_row, 6, 1)

        self.reset_enable_cb.toggled.connect(self._on_reset_enable_toggled)
        self._on_reset_enable_toggled(self.reset_enable_cb.isChecked())

        config_layout.addLayout(grid)

        self._control_channel_row_widgets = [
            self._n6705c_poweron_label,
            self.poweron_channel_combo,
            self.poweron_polarity_toggle,
            self._n6705c_reset_label_container,
            self.reset_channel_combo,
            self.reset_polarity_toggle,
        ]

        self.mcu_search_btn.clicked.connect(self._on_mcu_search)
        self.mcu_connect_btn.clicked.connect(self._on_mcu_connect_or_disconnect)
        self.mcu_type_combo.currentIndexChanged.connect(self._on_mcu_type_changed)
        self.control_method_toggle.toggled.connect(self._on_control_method_changed)
        self._on_control_method_changed(self.control_method_toggle.value())

        return config_frame

    def _on_control_method_changed(self, method):
        prev_method = getattr(self, "_current_control_method", method)
        if prev_method != method and getattr(self, "poweron_channel_combo", None) is not None:
            self._saved_control_channels.setdefault(prev_method, {})["poweron"] = (
                self.poweron_channel_combo.currentText()
            )
        if prev_method != method and getattr(self, "reset_channel_combo", None) is not None:
            self._saved_control_channels.setdefault(prev_method, {})["reset"] = (
                self.reset_channel_combo.currentText()
            )
        self._current_control_method = method

        if hasattr(self, "_mcu_row_widgets"):
            for w in self._mcu_row_widgets:
                w.setVisible(method == "MCU")

        self._refresh_mcu_gpio_options()

        visible = True
        if hasattr(self, "_control_channel_row_widgets"):
            for w in self._control_channel_row_widgets:
                w.setVisible(visible)

    def _on_mcu_type_changed(self, _idx=None):
        if getattr(self, "is_mcu_connected", False):
            self.append_log(
                "[MCU] Type changed while connected. Please reconnect to apply."
            )
        self._refresh_mcu_gpio_options()
        if hasattr(self, "mcu_port_combo") and self.mcu_port_combo is not None:
            self.mcu_port_combo.clear()
            if self._current_mcu_type() == "ch9114f":
                self.mcu_port_combo.addItem("Select CH9114F COM...")
            else:
                self.mcu_port_combo.addItem("Select MCU COM...")

    def _refresh_mcu_gpio_options(self):
        if getattr(self, "control_method_toggle", None) is None:
            return
        method = self.control_method_toggle.value()
        if method != "MCU":
            return
        options = self._get_control_channel_options(method)
        defaults = self._saved_control_channels.get(method, {})
        self._set_combo_options(
            self.poweron_channel_combo,
            options,
            defaults.get("poweron", "GPIO0"),
        )
        self._set_combo_options(
            self.reset_channel_combo,
            options,
            defaults.get("reset", "GPIO1"),
        )

    def _on_reset_enable_toggled(self, checked):
        if hasattr(self, "reset_channel_combo") and self.reset_channel_combo is not None:
            self.reset_channel_combo.setEnabled(checked)
        if hasattr(self, "reset_polarity_toggle") and self.reset_polarity_toggle is not None:
            self.reset_polarity_toggle.setEnabled(checked)

    def _create_channel_config_section(self):
        config_frame = QFrame()
        config_frame.setObjectName("testConfigFrame")
        config_frame.setStyleSheet("""
            QFrame#testConfigFrame {
                background-color: #0a1228;
                border: 1px solid #1a2d57;
                border-radius: 12px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(14, 10, 14, 10)
        config_layout.setSpacing(8)

        config_header = QHBoxLayout()
        config_header.setSpacing(8)
        cfg_icon = QLabel()
        _settings_svg = os.path.join(_PAGE_SVGS_DIR, "settings.svg")
        if os.path.isfile(_settings_svg):
            cfg_icon.setPixmap(_tinted_svg_icon(_settings_svg, "#c8d6f0", 14).pixmap(14, 14))
        cfg_icon.setFixedSize(16, 16)
        cfg_icon.setStyleSheet("background: transparent; border: none;")
        cfg_title = QLabel("Channel Config")
        cfg_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        config_header.addWidget(cfg_icon)
        config_header.addWidget(cfg_title)
        config_header.addStretch()
        config_layout.addLayout(config_header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFixedHeight(200)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QWidget#channelConfigContainer {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: #0a1228;
                height: 6px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: #2a3f6e;
                min-width: 30px;
                border-radius: 3px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        self._channel_config_container = QWidget()
        self._channel_config_container.setObjectName("channelConfigContainer")
        self._channel_config_row = QHBoxLayout(self._channel_config_container)
        self._channel_config_row.setContentsMargins(0, 0, 0, 0)
        self._channel_config_row.setSpacing(10)
        self._channel_config_row.addStretch()

        scroll_area.setWidget(self._channel_config_container)
        config_layout.addWidget(scroll_area)

        return config_frame

    def _add_channel_config_card(self, name, channel_key, enabled):
        idx = len(self._channel_configs)
        config = {
            "name": name, "channel": channel_key, "enabled": enabled,
            "force_mode": "auto",        # "force" / "auto"
            "force_value": "",           # Force 模式下用户输入电压(V)
            "boost_mode": "constant",    # "constant" / "percent" (Auto 模式)
            "boost_value": "0.02",       # Auto 模式下增压值
        }
        self._channel_configs.append(config)

        card = QFrame()
        card_id = f"cfgCard{idx}"
        card.setObjectName(card_id)
        card.setStyleSheet(f"""
            QFrame#{card_id} {{
                background-color: #0d1b3e;
                border: 1px solid #1c2f54;
                border-radius: 8px;
            }}
        """)
        card.setFixedWidth(160)
        card.setMinimumHeight(220)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(5)

        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        enable_cb = QCheckBox("Enable")
        enable_cb.setChecked(enabled)
        enable_cb.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        top_row.addWidget(enable_cb)
        top_row.addStretch()

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #5a6b8e;
                border: none;
                font-size: 13px;
                font-weight: 700;
                min-height: 0px;
                padding: 0px;
            }
            QPushButton:hover { color: #ff5a5a; }
        """)
        top_row.addWidget(remove_btn)
        card_layout.addLayout(top_row)

        # Name 行: 标签 + 下拉菜单同一行
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        name_label = QLabel("Name")
        name_label.setStyleSheet("font-size: 10px; color: #7e96bf;")
        name_label.setFixedWidth(32)
        name_row.addWidget(name_label)

        name_input = DarkComboBox()
        name_input.setFixedHeight(26)
        font = name_input.font()
        font.setPixelSize(12)
        name_input.setFont(font)
        for opt in self.NAME_OPTIONS:
            name_input.addItem(opt)
        for i in range(name_input.count()):
            if name_input.itemText(i) == name:
                name_input.setCurrentIndex(i)
                break
        else:
            name_input.setEditable(True)
            name_input.setCurrentText(name)
            name_input.setEditable(False)
        name_row.addWidget(name_input, 1)
        card_layout.addLayout(name_row)

        # Channel 行: 标签 + 下拉菜单同一行
        ch_row = QHBoxLayout()
        ch_row.setSpacing(6)
        ch_label = QLabel("CH")
        ch_label.setStyleSheet("font-size: 10px; color: #7e96bf;")
        ch_label.setFixedWidth(32)
        ch_row.addWidget(ch_label)

        channel_combo = DarkComboBox()
        channel_combo.setFixedHeight(26)
        font = channel_combo.font()
        font.setPixelSize(11)
        channel_combo.setFont(font)
        options = self._get_available_channel_options()
        for opt in options:
            channel_combo.addItem(opt)
        for i in range(channel_combo.count()):
            if channel_combo.itemText(i) == channel_key:
                channel_combo.setCurrentIndex(i)
                break
        ch_row.addWidget(channel_combo, 1)
        card_layout.addLayout(ch_row)

        # Force 模式切换: Force (用户输入固定电压) / Auto (按 boost 增压)
        force_mode_toggle = BinaryTextToggle(
            left_key="force", left_label="Force",
            right_key="auto", right_label="Auto",
            initial=config["force_mode"],
            fixed_height=22, fixed_width=140,
        )
        card_layout.addWidget(force_mode_toggle)

        # Force/Auto 互斥内容区: index 0 = Force 输入框, index 1 = Auto 三件套
        force_auto_stack = QStackedLayout()
        force_auto_stack.setContentsMargins(0, 0, 0, 0)
        force_auto_stack.setSpacing(0)

        # ---- Page 0: Force 模式下显示 电压输入框 ----
        force_page = QWidget()
        force_page_layout = QVBoxLayout(force_page)
        force_page_layout.setContentsMargins(0, 0, 0, 0)
        force_page_layout.setSpacing(5)

        force_value_input = QLineEdit()
        force_value_input.setPlaceholderText("V (Force)")
        force_value_input.setText(config["force_value"])
        font = force_value_input.font()
        font.setPixelSize(11)
        force_value_input.setFont(font)
        force_value_input.setMaximumHeight(26)
        force_value_input.setStyleSheet("""
            QLineEdit {
                background-color: #0a1733;
                color: #c8d8f8;
                border: 1.5px solid #27406f;
                border-radius: 6px;
                padding: 0px 10px;
                max-height: 18px;
            }
            QLineEdit:disabled {
                background-color: #060d1f;
                color: #3a4a6a;
                border: 1.5px solid #1a2a4a;
            }
        """)
        force_page_layout.addWidget(force_value_input)
        force_auto_stack.addWidget(force_page)

        # ---- Page 1: Auto 模式下显示 Boost Mode toggle + 增压值输入框 ----
        auto_page = QWidget()
        auto_page_layout = QVBoxLayout(auto_page)
        auto_page_layout.setContentsMargins(0, 0, 0, 0)
        auto_page_layout.setSpacing(5)

        boost_mode_label = QLabel("Boost Mode")
        boost_mode_label.setStyleSheet("font-size: 10px; color: #7e96bf;")
        auto_page_layout.addWidget(boost_mode_label)

        boost_mode_toggle = BinaryTextToggle(
            left_key="constant", left_label="Const",
            right_key="percent", right_label="Pct",
            initial=config["boost_mode"],
            fixed_height=22, fixed_width=140,
        )
        auto_page_layout.addWidget(boost_mode_toggle)

        boost_value_input = QLineEdit()
        boost_value_input.setPlaceholderText("boost value")
        boost_value_input.setText(config["boost_value"])
        font = boost_value_input.font()
        font.setPixelSize(11)
        boost_value_input.setFont(font)
        boost_value_input.setMaximumHeight(26)
        boost_value_input.setStyleSheet("""
            QLineEdit {
                background-color: #0a1733;
                color: #c8d8f8;
                border: 1.5px solid #27406f;
                border-radius: 6px;
                padding: 0px 10px;
                max-height: 18px;
            }
            QLineEdit:disabled {
                background-color: #060d1f;
                color: #3a4a6a;
                border: 1.5px solid #1a2a4a;
            }
        """)
        auto_page_layout.addWidget(boost_value_input)
        force_auto_stack.addWidget(auto_page)

        # 初始 page:force_mode == "force" -> 0, 否则 "auto" -> 1
        force_auto_stack.setCurrentIndex(0 if config["force_mode"] == "force" else 1)
        card_layout.addLayout(force_auto_stack)

        stretch_idx = self._channel_config_row.count() - 1
        self._channel_config_row.insertWidget(stretch_idx, card)

        wdata = {
            "card": card,
            "card_id": card_id,
            "enable_cb": enable_cb,
            "name_input": name_input,
            "channel_combo": channel_combo,
            "remove_btn": remove_btn,
            "name_label": name_label,
            "ch_label": ch_label,
            "force_mode_toggle": force_mode_toggle,
            "force_auto_stack": force_auto_stack,
            "force_value_input": force_value_input,
            "boost_mode_label": boost_mode_label,
            "boost_mode_toggle": boost_mode_toggle,
            "boost_value_input": boost_value_input,
            "config_index": idx,
        }
        self._channel_config_widgets.append(wdata)

        enable_cb.toggled.connect(lambda checked, i=idx: self._on_config_enable_changed(i, checked))
        name_input.currentTextChanged.connect(lambda text, i=idx: self._on_config_name_changed(i, text))
        channel_combo.currentIndexChanged.connect(lambda ci, i=idx: self._on_config_channel_changed(i))
        remove_btn.clicked.connect(lambda checked=False, i=idx: self._remove_channel_config(i))
        force_mode_toggle.toggled.connect(lambda val, i=idx: self._on_force_mode_changed(i, val))
        force_value_input.textChanged.connect(lambda text, i=idx: self._on_force_value_changed(i, text))
        boost_mode_toggle.toggled.connect(lambda val, i=idx: self._on_boost_mode_changed(i, val))
        boost_value_input.textChanged.connect(lambda text, i=idx: self._on_boost_value_changed(i, text))

        self._update_card_disabled_state(wdata, enabled)
        self._refresh_result_cards()

    def _on_config_enable_changed(self, idx, checked):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["enabled"] = checked
            self._update_card_disabled_state(self._channel_config_widgets[idx], checked)
            self._refresh_result_cards()

    def _update_card_disabled_state(self, wdata, enabled):
        wdata["name_input"].setEnabled(enabled)
        wdata["channel_combo"].setEnabled(enabled)
        wdata["remove_btn"].setEnabled(enabled)
        wdata["force_mode_toggle"].setEnabled(enabled)
        # Force/Auto 切换: 用 QStackedLayout 切换显示页,只显示对应模式的控件
        is_force = wdata["force_mode_toggle"].value() == "force"
        stack = wdata["force_auto_stack"]
        stack.setCurrentIndex(0 if is_force else 1)
        # 当前可见页的子控件跟随 enabled 状态;不可见页的控件也置 disabled
        # 防止用户用 Tab 键聚焦到隐藏控件
        if enabled:
            if is_force:
                wdata["force_value_input"].setEnabled(True)
                wdata["boost_mode_label"].setEnabled(False)
                wdata["boost_mode_toggle"].setEnabled(False)
                wdata["boost_value_input"].setEnabled(False)
            else:
                wdata["force_value_input"].setEnabled(False)
                wdata["boost_mode_label"].setEnabled(True)
                wdata["boost_mode_toggle"].setEnabled(True)
                wdata["boost_value_input"].setEnabled(True)
        else:
            wdata["force_value_input"].setEnabled(False)
            wdata["boost_mode_label"].setEnabled(False)
            wdata["boost_mode_toggle"].setEnabled(False)
            wdata["boost_value_input"].setEnabled(False)

        card = wdata["card"]
        card_id = wdata["card_id"]
        if enabled:
            card.setStyleSheet(f"""
                QFrame#{card_id} {{
                    background-color: #0d1b3e;
                    border: 1px solid #1c2f54;
                    border-radius: 8px;
                }}
            """)
            wdata["name_label"].setStyleSheet("font-size: 10px; color: #7e96bf;")
            wdata["ch_label"].setStyleSheet("font-size: 10px; color: #7e96bf;")
            wdata["remove_btn"].setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #5a6b8e;
                    border: none;
                    font-size: 13px;
                    font-weight: 700;
                    min-height: 0px;
                    padding: 0px;
                }
                QPushButton:hover { color: #ff5a5a; }
            """)
        else:
            card.setStyleSheet(f"""
                QFrame#{card_id} {{
                    background-color: #080e1e;
                    border: 1px solid #131d36;
                    border-radius: 8px;
                }}
            """)
            wdata["name_label"].setStyleSheet("font-size: 10px; color: #3a4a6a;")
            wdata["ch_label"].setStyleSheet("font-size: 10px; color: #3a4a6a;")
            wdata["remove_btn"].setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #2a3550;
                    border: none;
                    font-size: 13px;
                    font-weight: 700;
                    min-height: 0px;
                    padding: 0px;
                }
            """)

    def _on_config_name_changed(self, idx, text):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["name"] = text
            self._refresh_result_cards()

    def _on_config_channel_changed(self, idx):
        if idx < len(self._channel_configs):
            wdata = self._channel_config_widgets[idx]
            raw = wdata["channel_combo"].currentText()
            self._channel_configs[idx]["channel"] = raw
            self._refresh_result_cards()

    def _on_force_mode_changed(self, idx, val):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["force_mode"] = val
            wdata = self._channel_config_widgets[idx]
            is_force = (val == "force")
            # 切换 stack 显示页: Force -> page 0, Auto -> page 1
            wdata["force_auto_stack"].setCurrentIndex(0 if is_force else 1)
            is_enabled = wdata["enable_cb"].isChecked()
            if is_enabled:
                if is_force:
                    wdata["force_value_input"].setEnabled(True)
                    wdata["boost_mode_label"].setEnabled(False)
                    wdata["boost_mode_toggle"].setEnabled(False)
                    wdata["boost_value_input"].setEnabled(False)
                else:
                    wdata["force_value_input"].setEnabled(False)
                    wdata["boost_mode_label"].setEnabled(True)
                    wdata["boost_mode_toggle"].setEnabled(True)
                    wdata["boost_value_input"].setEnabled(True)

    def _on_force_value_changed(self, idx, text):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["force_value"] = text

    def _on_boost_mode_changed(self, idx, val):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["boost_mode"] = val

    def _on_boost_value_changed(self, idx, text):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["boost_value"] = text

    def _remove_channel_config(self, idx):
        if idx >= len(self._channel_configs):
            return
        wdata = self._channel_config_widgets[idx]
        wdata["card"].hide()
        wdata["card"].deleteLater()

        self._channel_configs.pop(idx)
        self._channel_config_widgets.pop(idx)

        for i, w in enumerate(self._channel_config_widgets):
            w["config_index"] = i
            w["enable_cb"].toggled.disconnect()
            w["name_input"].currentTextChanged.disconnect()
            w["channel_combo"].currentIndexChanged.disconnect()
            w["remove_btn"].clicked.disconnect()
            w["force_mode_toggle"].toggled.disconnect()
            w["force_value_input"].textChanged.disconnect()
            w["boost_mode_toggle"].toggled.disconnect()
            w["boost_value_input"].textChanged.disconnect()
            w["enable_cb"].toggled.connect(lambda checked, ci=i: self._on_config_enable_changed(ci, checked))
            w["name_input"].currentTextChanged.connect(lambda text, ci=i: self._on_config_name_changed(ci, text))
            w["channel_combo"].currentIndexChanged.connect(lambda cii, ci=i: self._on_config_channel_changed(ci))
            w["remove_btn"].clicked.connect(lambda checked=False, ci=i: self._remove_channel_config(ci))
            w["force_mode_toggle"].toggled.connect(lambda val, ci=i: self._on_force_mode_changed(ci, val))
            w["force_value_input"].textChanged.connect(lambda text, ci=i: self._on_force_value_changed(ci, text))
            w["boost_mode_toggle"].toggled.connect(lambda val, ci=i: self._on_boost_mode_changed(ci, val))
            w["boost_value_input"].textChanged.connect(lambda text, ci=i: self._on_boost_value_changed(ci, text))

        self._refresh_result_cards()
