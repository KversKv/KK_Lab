#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt
from ui.theme import FONT_MONO
from ui.pages.n6705c_power_analyzer.widgets import (
    SlideToggle,
    INPUT_BG, INPUT_BORDER, WIDGET_RADIUS, PREFIX_TEXT, UNIT_TEXT,
    CONTENT_BG, CONTAINER_RADIUS, PANEL_BG, PANEL_BORDER,
    CARD_BG, CARD_BORDER, VALUE_OFF_COLOR,
)


class SettingViewMixin:
    def _create_unified_input(self, prefix_text, default_value, unit_text):
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {INPUT_BG};
                border: 1px solid {INPUT_BORDER};
                border-radius: {WIDGET_RADIUS};
            }}
        """)
        container.setFixedHeight(36)

        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(10, 0, 10, 0)
        h_layout.setSpacing(6)

        prefix = QLabel(prefix_text)
        prefix.setStyleSheet(f"color: {PREFIX_TEXT}; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        prefix.setFixedWidth(32)
        h_layout.addWidget(prefix)

        input_field = QLineEdit(default_value)
        input_field.setFrame(False)
        input_field.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none;
                color: #ffffff; font-size: 14px; font-weight: 600; padding: 0px;
            }
            QLineEdit:disabled {
                color: #4a5a7a; background: transparent; border: none;
            }
        """)
        h_layout.addWidget(input_field, 1)

        unit = QLabel(unit_text)
        unit.setStyleSheet(f"color: {UNIT_TEXT}; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        unit.setFixedWidth(16)
        h_layout.addWidget(unit)

        return container, prefix, input_field, unit

    def _create_setting_widget(self):
        setting_wrapper = QWidget()
        setting_wrapper.setStyleSheet("QWidget { background: transparent; border: none; }")
        wrapper_layout = QVBoxLayout(setting_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        self.setting_frame = QFrame()
        self.setting_frame.setObjectName("SettingContentFrame")
        self.setting_frame.setStyleSheet(f"""
            QFrame#SettingContentFrame {{
                background-color: {CONTENT_BG};
                border: 1px solid #14305e;
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)

        setting_layout = QVBoxLayout(self.setting_frame)
        setting_layout.setAlignment(Qt.AlignTop)
        setting_layout.setContentsMargins(12, 12, 12, 12)
        setting_layout.setSpacing(12)

        setting_header = QHBoxLayout()
        setting_header.setContentsMargins(0, 0, 0, 0)
        setting_header.setSpacing(12)

        self.channel_title_label = QLabel("Channel 1")
        self.channel_title_label.setStyleSheet("""
            QLabel { font-size: 16px; font-weight: 800; color: #ffffff;
                     padding: 0px; margin: 0px; border: none; background: transparent; }
        """)
        setting_header.addWidget(self.channel_title_label)

        self.cv_btn = QPushButton("PS2Q")
        self.cc_btn = QPushButton("CC")
        self.cr_btn = QPushButton("VMETer")
        self.cp_btn = QPushButton("AMETer")
        self.mode_buttons = [self.cv_btn, self.cc_btn, self.cr_btn, self.cp_btn]

        for btn in self.mode_buttons:
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.setMinimumWidth(70)
            btn.clicked.connect(lambda checked=False, b=btn: self._on_mode_button_clicked(b))

        self.cv_btn.setChecked(True)

        mode_container = QFrame()
        mode_container.setStyleSheet(f"""
            QFrame {{
                background-color: #0c1628;
                border: 1px solid #1b2842;
                border-radius: {WIDGET_RADIUS};
            }}
        """)
        mode_layout = QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(2)
        for btn in self.mode_buttons:
            mode_layout.addWidget(btn)

        setting_header.addWidget(mode_container)
        setting_header.addStretch()

        self.output_toggle = SlideToggle()
        self.output_toggle.clicked.connect(self._on_output_toggle_clicked)
        setting_header.addWidget(self.output_toggle)

        setting_layout.addLayout(setting_header)

        params_container = QFrame()
        params_container.setStyleSheet(f"""
            QFrame {{ background-color: {PANEL_BG}; border: 1px solid {PANEL_BORDER}; border-radius: {CONTAINER_RADIUS}; }}
        """)
        params_grid = QGridLayout(params_container)
        params_grid.setContentsMargins(8, 8, 8, 8)
        params_grid.setSpacing(12)

        voltage_frame = QFrame()
        voltage_frame.setStyleSheet(f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}")
        voltage_layout = QVBoxLayout(voltage_frame)
        voltage_layout.setContentsMargins(14, 14, 14, 14)
        voltage_layout.setSpacing(8)

        voltage_label = QLabel("VOLTAGE (V)")
        voltage_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #97aed9; letter-spacing: 1px; border: none; }")
        voltage_layout.addWidget(voltage_label)

        self.voltage_value = QLineEdit("0.0000")
        self.voltage_value.setFrame(False)
        self.voltage_value.setReadOnly(True)
        self.voltage_value.setStyleSheet(f"""
            QLineEdit {{ font-family: {FONT_MONO}; font-size: 26px; font-weight: bold; color: {VALUE_OFF_COLOR}; background: transparent; border: none; letter-spacing: 1px; }}
        """)
        self.voltage_value.setFixedHeight(44)
        voltage_layout.addWidget(self.voltage_value)

        (self.voltage_input_container, self.voltage_set_label,
         self.voltage_set_input, self._voltage_unit_label) = self._create_unified_input("Set", "5", "V")
        self.voltage_set_input.returnPressed.connect(self._on_voltage_input_enter)
        self.voltage_set_input.textChanged.connect(self._on_voltage_text_changed)
        voltage_layout.addWidget(self.voltage_input_container)
        params_grid.addWidget(voltage_frame, 0, 0)

        current_frame = QFrame()
        current_frame.setStyleSheet(f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}")
        current_layout = QVBoxLayout(current_frame)
        current_layout.setContentsMargins(14, 14, 14, 14)
        current_layout.setSpacing(8)

        current_label = QLabel("CURRENT (A)")
        current_label.setStyleSheet("QLabel { font-size: 12px; font-weight: 600; color: #97aed9; letter-spacing: 1px; border: none; }")
        current_layout.addWidget(current_label)

        self.current_value = QLineEdit("0.0000")
        self.current_value.setReadOnly(True)
        self.current_value.setStyleSheet(f"""
            QLineEdit {{ font-family: {FONT_MONO}; font-size: 26px; font-weight: bold; color: {VALUE_OFF_COLOR}; background-color: transparent; border: none; letter-spacing: 1px; }}
        """)
        self.current_value.setFixedHeight(44)
        current_layout.addWidget(self.current_value)

        (self.current_input_container, self.current_set_label,
         self.limit_current_value, self._current_unit_label) = self._create_unified_input("Lim", "1", "A")
        self.limit_current_value.returnPressed.connect(self._on_current_input_enter)
        self.limit_current_value.textChanged.connect(self._on_current_text_changed)
        current_layout.addWidget(self.current_input_container)
        params_grid.addWidget(current_frame, 0, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)

        self.measure_btn = QPushButton("MEASURE")
        self.measure_btn.clicked.connect(self._on_measure_clicked)

        self.set_btn = QPushButton("SET")
        self.set_btn.clicked.connect(self._on_set_clicked)

        action_row.addWidget(self.measure_btn)
        action_row.addWidget(self.set_btn)
        action_row.addStretch()

        params_grid.addLayout(action_row, 1, 0, 1, 2)
        setting_layout.addWidget(params_container)

        channel_data = {
            'voltage_value': self.voltage_value,
            'current_value': self.current_value,
            'limit_current_value': self.limit_current_value,
            'voltage_set_input': self.voltage_set_input,
            'toggle': self.output_toggle
        }
        self.channels.append(channel_data)

        wrapper_layout.addWidget(self.setting_frame)
        return setting_wrapper
