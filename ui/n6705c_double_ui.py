#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.dark_combobox import DarkComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGridLayout, QFrame, QApplication, QCheckBox,
    QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont
import pyvisa

from instruments.n6705c import N6705C


class _ConsumptionTestWorker(QObject):
    channel_result = Signal(str, int, float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, n6705c, device_label, channels, test_time, sample_period):
        super().__init__()
        self.n6705c = n6705c
        self.device_label = device_label
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
                self.channel_result.emit(self.device_label, ch, float(avg_current))
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"[{self.device_label}] {e}")
            self.finished.emit()


CHANNEL_COLORS = {
    1: {"accent": "#d4a514", "bg": "#1a1708", "border": "#3d2e08"},
    2: {"accent": "#18b67a", "bg": "#081a14", "border": "#0a3d28"},
    3: {"accent": "#2f6fed", "bg": "#081028", "border": "#0c2a5e"},
    4: {"accent": "#d14b72", "bg": "#1a080e", "border": "#3d0c22"},
}

CHANNEL_THEMES = {
    1: {
        "accent": "#d4a514", "accent_hover": "#e3b729",
        "accent_soft": "#342808", "accent_border": "#7a5e12", "text_dim": "#c9b06a"
    },
    2: {
        "accent": "#18b67a", "accent_hover": "#21c487",
        "accent_soft": "#0a2a20", "accent_border": "#14694b", "text_dim": "#7bc7a8"
    },
    3: {
        "accent": "#2f6fed", "accent_hover": "#4680f0",
        "accent_soft": "#0c2048", "accent_border": "#264d9b", "text_dim": "#8db4ff"
    },
    4: {
        "accent": "#d14b72", "accent_hover": "#df5f85",
        "accent_soft": "#34111d", "accent_border": "#7e2f47", "text_dim": "#d79ab1"
    }
}


def _get_checkmark_path(accent_color):
    safe_name = accent_color.replace("#", "").replace(" ", "")
    icons_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "resources", "icons"
    )
    return {
        "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
        "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
    }


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


def _neon_on_button_style():
    return """
    QPushButton {
        background-color: #062b2b; color: #00f5c4;
        border: 1px solid #00cfa6; border-radius: 8px;
        padding: 8px 18px; min-width: 88px; font-size: 12px; font-weight: 600;
    }
    QPushButton:hover { background-color: #0a3a3a; border: 1px solid #00f5c4; color: #3fffd7; }
    """


def _neon_off_button_style():
    return """
    QPushButton {
        background-color: #2a0a1c; color: #ff4fa3;
        border: 1px solid #d63384; border-radius: 8px;
        padding: 8px 18px; min-width: 88px; font-size: 12px; font-weight: 600;
    }
    QPushButton:hover { background-color: #3a1028; border: 1px solid #ff4fa3; color: #ff7dbd; }
    """


def _primary_action_button_style():
    return """
    QPushButton {
        background-color: #2a64c8; color: white; border: none; border-radius: 6px;
        padding: 8px 16px; font-size: 11px; min-width: 88px; font-weight: 600;
    }
    QPushButton:hover { background-color: #3672dc; }
    """


def _batch_channel_button_style():
    return """
        QPushButton {
            background-color: #25314a; color: #91a7d1;
            border: 1px solid #31476f; border-radius: 6px;
            padding: 6px 10px; font-size: 11px; min-width: 60px;
        }
        QPushButton:checked { background-color: #2a64c8; color: white; }
        QPushButton:hover { background-color: #31405f; }
    """


class N6705CDoubleUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self):
        super().__init__()

        self.devices = {
            "A": {"rm": None, "n6705c": None, "is_connected": False},
            "B": {"rm": None, "n6705c": None, "is_connected": False},
        }

        self.current_device = "A"
        self.current_channel = 1
        self.is_testing = False
        self._test_threads = {}
        self._test_workers = {}

        self._setup_style()
        self._create_layout()

        self.search_timer_a = QTimer(self)
        self.search_timer_a.timeout.connect(lambda: self._search_devices("A"))
        self.search_timer_a.setSingleShot(True)

        self.search_timer_b = QTimer(self)
        self.search_timer_b.timeout.connect(lambda: self._search_devices("B"))
        self.search_timer_b.setSingleShot(True)

        self._apply_channel_theme(self.current_device, self.current_channel)

    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setObjectName("RootWidget")
        self.setStyleSheet("""
        QWidget#RootWidget { background-color: #07111f; }
        QWidget { background-color: #07111f; color: #d6e2ff; }
        QLabel { color: #c8d6f0; background: transparent; border: none; }
        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #091426; border: 1px solid #17345f;
            border-radius: 6px; padding: 4px 6px; color: #d7e3ff;
        }
        QPushButton {
            background-color: #0b1730; border: 1px solid #23417a;
            border-radius: 6px; padding: 6px 14px; color: #dbe6ff;
        }
        QPushButton:hover { background-color: #10203e; }
        """)

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(8, 8, 8, 8)

        self.top_bar = self._create_top_bar()
        main_layout.addWidget(self.top_bar)
        main_layout.addSpacing(8)

        self.channel_tabs = self._create_channel_tabs()
        main_layout.addWidget(self.channel_tabs)

        self.setting_widget = self._create_setting_widget()
        main_layout.addWidget(self.setting_widget, 1)

        self.consumption_test_panel = self._create_consumption_test_panel()
        main_layout.addWidget(self.consumption_test_panel)

    # =========================
    # 顶部栏 (A & B 连接)
    # =========================
    def _create_top_bar(self):
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            QFrame { background-color: #07111f; border: 1px solid #132849; border-radius: 12px; }
        """)
        outer_layout = QVBoxLayout(top_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setStyleSheet("QWidget { background-color: #07111f; border: none; }")
        header_widget.setFixedHeight(54)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(10)

        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("QLabel { color: #00f5c4; font-size: 24px; font-weight: bold; }")
        header_layout.addWidget(icon_label)

        title_label = QLabel("Keysight N6705C × 2  DC Power Analyzer")
        title_label.setStyleSheet("QLabel { color: #ffffff; font-size: 18px; font-weight: 800; }")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.all_on_btn = QPushButton("⏻ All On")
        self.all_on_btn.setStyleSheet(_neon_on_button_style())
        self.all_off_btn = QPushButton("▢ All Off")
        self.all_off_btn.setStyleSheet(_neon_off_button_style())
        self.all_on_btn.clicked.connect(self._on_all_on_clicked)
        self.all_off_btn.clicked.connect(self._on_all_off_clicked)

        header_layout.addWidget(self.all_on_btn)
        header_layout.addWidget(self.all_off_btn)
        outer_layout.addWidget(header_widget)

        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget { background-color: #07111f; border: none; }
            QLabel { color: #c8d1e6; font-size: 12px; }
            QLineEdit {
                background-color: #091426; color: #d0d8ea;
                border: 1px solid #17345f; border-radius: 8px; padding: 6px 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #091426; color: #d0d8ea;
                border: 1px solid #17345f; selection-background-color: #1a3260; outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                background-color: #091426; color: #d0d8ea; padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #1a3260;
            }
            QComboBox QFrame {
                background-color: #091426; border: 1px solid #17345f;
            }
            QPushButton {
                background-color: #0b1730; color: #d0d0d0;
                border: 1px solid #23417a; border-radius: 8px; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #10203e; }
        """)
        grid = QGridLayout(content_widget)
        grid.setContentsMargins(16, 8, 16, 14)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        default_addresses = {
            "A": "TCPIP0::K-N6705C-06098.local::hislip0::INSTR",
            "B": "TCPIP::K-N6705C-03845.local::hislip0::INSTR",
        }

        self.conn_widgets = {}
        for row, (label, color) in enumerate([("A", "#00f5c4"), ("B", "#f2994a")]):
            tag = QLabel(f"  {label}  ")
            tag.setStyleSheet(f"color: {color}; font-weight: 900; font-size: 14px; min-width: 24px;")
            tag.setAlignment(Qt.AlignCenter)

            status = QLabel("● 未连接")
            status.setStyleSheet("color:#7fa1d9; font-weight:bold;")

            combo = DarkComboBox(bg="#091426", border="#17345f")
            combo.setMinimumWidth(300)
            combo.addItem(default_addresses[label])

            search_btn = QPushButton("搜索")
            connect_btn = QPushButton("连接")
            disconnect_btn = QPushButton("断开")
            disconnect_btn.setEnabled(False)

            search_btn.clicked.connect(lambda _checked=False, lb=label: self._on_search(lb))
            connect_btn.clicked.connect(lambda _checked=False, lb=label: self._on_connect(lb))
            disconnect_btn.clicked.connect(lambda _checked=False, lb=label: self._on_disconnect(lb))

            grid.addWidget(tag, row, 0)
            grid.addWidget(status, row, 1)
            grid.addWidget(combo, row, 2, 1, 2)
            grid.addWidget(search_btn, row, 4)
            grid.addWidget(connect_btn, row, 5)
            grid.addWidget(disconnect_btn, row, 6)

            self.conn_widgets[label] = {
                "status": status, "combo": combo,
                "search_btn": search_btn, "connect_btn": connect_btn,
                "disconnect_btn": disconnect_btn,
            }

        outer_layout.addWidget(content_widget)
        return top_frame

    # =========================
    # Channel Tabs: A-CH1~4 + B-CH1~4
    # =========================
    def _create_channel_tabs(self):
        tab_wrap = QWidget()
        tab_wrap.setAttribute(Qt.WA_StyledBackground, True)
        tab_wrap.setStyleSheet("QWidget { background-color: #07111f; border: none; }")

        layout = QHBoxLayout(tab_wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.channel_tab_buttons = []
        for dev_label in ["A", "B"]:
            for ch in range(1, 5):
                btn = QPushButton(f"{dev_label}-CH{ch}")
                btn.setCheckable(True)
                btn.setMinimumSize(90, 38)
                btn.clicked.connect(
                    lambda checked=False, d=dev_label, c=ch: self._switch_channel(d, c)
                )
                self.channel_tab_buttons.append(btn)
                layout.addWidget(btn)
            if dev_label == "A":
                sep = QFrame()
                sep.setFixedWidth(2)
                sep.setStyleSheet("QFrame { background: #1b2847; border: none; }")
                layout.addWidget(sep)

        layout.addStretch()
        self.channel_tab_buttons[0].setChecked(True)
        self._refresh_channel_tab_styles()
        return tab_wrap

    # =========================
    # 通道设置区（共用）
    # =========================
    def _create_setting_widget(self):
        self.setting_frame = QFrame()
        self.setting_frame.setStyleSheet("""
            QFrame { background-color: #0a1930; border: 1px solid #14305e; border-radius: 14px; }
        """)

        setting_layout = QVBoxLayout(self.setting_frame)
        setting_layout.setAlignment(Qt.AlignTop)
        setting_layout.setContentsMargins(12, 12, 12, 12)
        setting_layout.setSpacing(12)

        setting_header = QHBoxLayout()
        setting_header.setContentsMargins(0, 0, 0, 0)
        setting_header.setSpacing(12)

        self.channel_title_label = QLabel("A - Channel 1")
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

        params_container = QFrame()
        params_container.setStyleSheet("""
            QFrame { background-color: #0a1930; border: 1px solid #132849; border-radius: 12px; }
        """)
        params_grid = QGridLayout(params_container)
        params_grid.setContentsMargins(8, 8, 8, 8)
        params_grid.setSpacing(12)

        voltage_frame = QFrame()
        voltage_frame.setStyleSheet("QFrame { background-color: #0b1b34; border: 1px solid #102746; border-radius: 12px; }")
        voltage_layout = QVBoxLayout(voltage_frame)
        voltage_layout.setContentsMargins(14, 14, 14, 14)
        voltage_layout.setSpacing(8)

        voltage_label = QLabel("Voltage (V)")
        voltage_label.setStyleSheet("QLabel { font-size: 14px; color: #97aed9; }")
        voltage_layout.addWidget(voltage_label)

        self.voltage_value = QLineEdit("0.0000")
        self.voltage_value.setFrame(False)
        self.voltage_value.setStyleSheet("""
            QLineEdit { font-size: 22px; font-weight: bold; color: #6d83b3; background: transparent; border: none; }
            QLineEdit:focus { border: none; background: transparent; }
        """)
        self.voltage_value.setFixedHeight(40)
        voltage_layout.addWidget(self.voltage_value)

        v_input_row = QHBoxLayout()
        v_input_row.setSpacing(8)
        v_input_row.addWidget(QLabel("SET"))
        self.voltage_set_input = QLineEdit("5")
        self.voltage_set_input.setFixedHeight(34)
        v_input_row.addWidget(self.voltage_set_input)
        v_input_row.addWidget(QLabel("V"))
        voltage_layout.addLayout(v_input_row)
        params_grid.addWidget(voltage_frame, 0, 0)

        current_frame = QFrame()
        current_frame.setStyleSheet("QFrame { background-color: #0b1b34; border: 1px solid #102746; border-radius: 12px; }")
        current_layout = QVBoxLayout(current_frame)
        current_layout.setContentsMargins(14, 14, 14, 14)
        current_layout.setSpacing(8)

        current_label = QLabel("Current (A)")
        current_label.setStyleSheet("QLabel { font-size: 14px; color: #97aed9; }")
        current_layout.addWidget(current_label)

        self.current_value = QLineEdit("0.0000")
        self.current_value.setStyleSheet("""
            QLineEdit { font-size: 22px; font-weight: bold; color: #6d83b3; background-color: transparent; border: none; }
        """)
        self.current_value.setFixedHeight(40)
        current_layout.addWidget(self.current_value)

        c_input_row = QHBoxLayout()
        c_input_row.setSpacing(8)
        c_input_row.addWidget(QLabel("LIM"))
        self.limit_current_value = QLineEdit("1")
        self.limit_current_value.setFixedHeight(34)
        c_input_row.addWidget(self.limit_current_value)
        c_input_row.addWidget(QLabel("A"))
        current_layout.addLayout(c_input_row)
        params_grid.addWidget(current_frame, 0, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)

        self.on_button = QPushButton("⏻ On")
        self.on_button.setStyleSheet(_neon_on_button_style())
        self.on_button.clicked.connect(self._on_channel_on)

        self.off_button = QPushButton("▢ Off")
        self.off_button.setStyleSheet(_neon_off_button_style())
        self.off_button.clicked.connect(self._on_channel_off)

        self.measure_btn = QPushButton("MEASURE")
        self.measure_btn.setStyleSheet(_primary_action_button_style())
        self.measure_btn.clicked.connect(self._on_measure_clicked)

        self.set_btn = QPushButton("SET")
        self.set_btn.setStyleSheet(_primary_action_button_style())
        self.set_btn.clicked.connect(self._on_set_clicked)

        action_row.addWidget(self.on_button)
        action_row.addWidget(self.off_button)
        action_row.addStretch()
        action_row.addWidget(self.measure_btn)
        action_row.addWidget(self.set_btn)

        params_grid.addLayout(action_row, 1, 0, 1, 2)
        setting_layout.addWidget(params_container)

        # ===== 一键调整 (8通道) =====
        tools_container = QFrame()
        tools_container.setStyleSheet("""
            QFrame { background-color: #0a1930; border: 1px solid #132849; border-radius: 12px; }
        """)
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setContentsMargins(12, 12, 12, 12)
        tools_layout.setSpacing(10)

        tools_title = QLabel("一键调整")
        tools_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        tools_layout.addWidget(tools_title)

        ab_columns_layout = QHBoxLayout()
        ab_columns_layout.setSpacing(12)

        self.batch_channel_buttons = []
        self.batch_voltage_inputs = []
        self.batch_current_inputs = []

        default_voltages = [3.8, 0.8, 1.2, 1.8, 3.8, 0.8, 1.2, 1.8]
        default_currents = [0.2, 0.02, 0.02, 0.02, 0.2, 0.02, 0.02, 0.02]

        for dev_idx, (dev_label, dev_color) in enumerate([("A", "#00f5c4"), ("B", "#f2994a")]):
            dev_frame = QFrame()
            dev_frame.setStyleSheet(f"""
                QFrame {{ background-color: #0b1b34; border: 1px solid #102746; border-radius: 10px; }}
            """)
            dev_layout = QVBoxLayout(dev_frame)
            dev_layout.setContentsMargins(10, 8, 10, 8)
            dev_layout.setSpacing(6)

            dev_title = QLabel(f"N6705C - {dev_label}")
            dev_title.setStyleSheet(f"color: {dev_color}; font-size: 12px; font-weight: 700; border: none;")
            dev_layout.addWidget(dev_title)

            ch_select_row = QHBoxLayout()
            ch_select_row.setSpacing(6)
            ch_label = QLabel("通道:")
            ch_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
            ch_select_row.addWidget(ch_label)
            for i in range(1, 5):
                btn = QPushButton(f"{dev_label}-{i}")
                btn.setCheckable(True)
                btn.setChecked(True)
                btn.setStyleSheet(_batch_channel_button_style())
                self.batch_channel_buttons.append(btn)
                ch_select_row.addWidget(btn)
            ch_select_row.addStretch()
            dev_layout.addLayout(ch_select_row)

            v_row = QHBoxLayout()
            v_row.setSpacing(6)
            v_label = QLabel("电压(V):")
            v_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
            v_row.addWidget(v_label)
            offset = dev_idx * 4
            for i in range(4):
                inp = QLineEdit(f"{default_voltages[offset + i]:.4f}")
                inp.setFixedWidth(72)
                self.batch_voltage_inputs.append(inp)
                v_row.addWidget(inp)
            v_row.addStretch()
            dev_layout.addLayout(v_row)

            c_row = QHBoxLayout()
            c_row.setSpacing(6)
            c_label = QLabel("限流(A):")
            c_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
            c_row.addWidget(c_label)
            for i in range(4):
                inp = QLineEdit(f"{default_currents[offset + i]:.4f}")
                inp.setFixedWidth(72)
                self.batch_current_inputs.append(inp)
                c_row.addWidget(inp)
            c_row.addStretch()
            dev_layout.addLayout(c_row)

            ab_columns_layout.addWidget(dev_frame, 1)

        tools_layout.addLayout(ab_columns_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        measure_all_btn = QPushButton("Measure")
        set_all_btn = QPushButton("Set")
        auto_btn = QPushButton("Auto")

        for btn in [measure_all_btn, set_all_btn, auto_btn]:
            btn.setStyleSheet(_primary_action_button_style())
            buttons_layout.addWidget(btn)

        measure_all_btn.clicked.connect(self._on_batch_measure)
        set_all_btn.clicked.connect(self._on_batch_set)
        auto_btn.clicked.connect(self._on_batch_auto)

        buttons_layout.addStretch()
        tools_layout.addLayout(buttons_layout)

        setting_layout.addWidget(tools_container)

        return self.setting_frame

    # =========================
    # Consumption Test (8通道)
    # =========================
    def _create_consumption_test_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame { background-color: #0a1930; border: 1px solid #132849; border-radius: 12px; }
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
                background-color: #0b1730; color: #dbe6ff;
                border: 1px solid #23417a; border-radius: 6px;
                font-size: 11px; padding: 4px 10px; min-height: 28px;
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
                background-color: #062b2b; color: #00f5c4;
                border: 1px solid #00cfa6; border-radius: 8px;
                font-weight: 700; font-size: 13px; min-height: 38px;
            }
            QPushButton:hover { background-color: #0a3a3a; }
            QPushButton:disabled { background-color: #0b1730; color: #5a6b8e; border: 1px solid #1b2847; }
        """)
        self.ct_stop_btn = QPushButton("🟥 STOP")
        self.ct_stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ct_stop_btn.setEnabled(False)
        self.ct_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a0a1c; color: #ff4fa3;
                border: 1px solid #d63384; border-radius: 8px;
                font-weight: 700; font-size: 13px; min-height: 38px;
            }
            QPushButton:hover { background-color: #3a1028; }
            QPushButton:disabled { background-color: #0b1730; color: #5a6b8e; border: 1px solid #1b2847; }
        """)
        btn_row.addWidget(self.ct_start_btn, 1)
        btn_row.addWidget(self.ct_stop_btn, 1)
        layout.addLayout(btn_row)

        self.ct_channel_cards = {}

        a_group_label = QLabel("N6705C - A")
        a_group_label.setStyleSheet("color: #00f5c4; font-size: 12px; font-weight: 700;")
        layout.addWidget(a_group_label)

        a_row = QHBoxLayout()
        a_row.setSpacing(8)
        for ch in range(1, 5):
            card = self._create_ct_channel_card("A", ch)
            a_row.addWidget(card, 1)
        layout.addLayout(a_row)

        b_group_label = QLabel("N6705C - B")
        b_group_label.setStyleSheet("color: #f2994a; font-size: 12px; font-weight: 700;")
        layout.addWidget(b_group_label)

        b_row = QHBoxLayout()
        b_row.setSpacing(8)
        for ch in range(1, 5):
            card = self._create_ct_channel_card("B", ch)
            b_row.addWidget(card, 1)
        layout.addLayout(b_row)

        self.ct_start_btn.clicked.connect(self._ct_start_test)
        self.ct_stop_btn.clicked.connect(self._ct_stop_test)
        self.ct_save_btn.clicked.connect(self._ct_save_datalog)

        return panel

    def _create_ct_channel_card(self, dev_label, ch_num):
        colors = CHANNEL_COLORS[ch_num]
        key = (dev_label, ch_num)

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: {colors['bg']}; border: 1px solid {colors['border']}; border-radius: 10px; }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(90)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        checkbox = QCheckBox(f"{dev_label}-CH{ch_num}")
        checkbox.setChecked(False)
        icons = _get_checkmark_path(colors['accent'])
        checkbox.setStyleSheet(f"""
            QCheckBox {{ color: #ffffff; font-size: 12px; font-weight: 700; background: transparent; spacing: 6px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; image: url("{icons['unchecked']}"); }}
            QCheckBox::indicator:checked {{ image: url("{icons['checked']}"); }}
        """)

        top_row.addWidget(checkbox)
        top_row.addStretch()
        layout.addLayout(top_row)

        layout.addStretch()

        avg_label = QLabel("AVG CURRENT")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setStyleSheet("color: #8ea6cf; font-size: 10px; font-weight: 600;")
        layout.addWidget(avg_label)

        value_label = QLabel("- - -")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{ color: {colors['accent']}; font-size: 16px; font-weight: 700; letter-spacing: 3px; }}
        """)
        layout.addWidget(value_label)

        layout.addStretch()

        self.ct_channel_cards[key] = {
            "card": card, "checkbox": checkbox, "value_label": value_label,
        }
        return card

    # =========================
    # 样式工具
    # =========================
    def _build_channel_tab_style(self, dev_label, ch, checked=False):
        theme = CHANNEL_THEMES[ch]
        dev_color = "#00f5c4" if dev_label == "A" else "#f2994a"
        if checked:
            return f"""
            QPushButton {{
                background-color: #0b1730; color: #ffffff;
                border: 1px solid {theme['accent_border']};
                border-bottom: 2px solid {dev_color};
                border-top-left-radius: 10px; border-top-right-radius: 10px;
                padding: 6px 10px; font-size: 12px; font-weight: 700;
            }}
            """
        else:
            return f"""
            QPushButton {{
                background-color: #08132b; color: {theme['text_dim']};
                border: 1px solid #12284e; border-bottom: 2px solid transparent;
                border-top-left-radius: 10px; border-top-right-radius: 10px;
                padding: 6px 10px; font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {theme['accent_soft']}; color: #ffffff;
                border: 1px solid {theme['accent_border']};
            }}
            """

    def _build_mode_button_style(self, active=False):
        theme = CHANNEL_THEMES[self.current_channel]
        if active:
            return f"""
            QPushButton {{
                background-color: {theme['accent']}; color: #111111;
                border: 1px solid {theme['accent_hover']};
                padding: 5px 14px; font-size: 12px; font-weight: 700; border-radius: 0px;
            }}
            """
        else:
            return """
            QPushButton {
                background-color: #08111f; color: #7c8aac;
                border: 1px solid #1b2842;
                padding: 5px 14px; font-size: 12px; border-radius: 0px;
            }
            QPushButton:hover { background-color: #0c1628; color: #dbe6ff; }
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
        idx = 0
        for dev_label in ["A", "B"]:
            for ch in range(1, 5):
                is_current = (dev_label == self.current_device and ch == self.current_channel)
                self.channel_tab_buttons[idx].setStyleSheet(
                    self._build_channel_tab_style(dev_label, ch, is_current)
                )
                self.channel_tab_buttons[idx].setChecked(is_current)
                idx += 1

    def _apply_channel_theme(self, dev_label, channel_num):
        theme = CHANNEL_THEMES[channel_num]
        self.channel_title_label.setText(f"{dev_label} - Channel {channel_num}")
        self.setting_frame.setStyleSheet(f"""
            QFrame {{ background-color: #0a1930; border: 1px solid {theme['accent_border']}; border-radius: 14px; }}
        """)
        self.output_toggle.setStyleSheet(f"""
            QPushButton {{ background-color: #25314a; border: none; border-radius: 13px; }}
            QPushButton:checked {{ background-color: {theme['accent']}; border: none; border-radius: 13px; }}
        """)
        self._refresh_channel_tab_styles()
        self._apply_mode_button_styles()

    # =========================
    # 通道/模式
    # =========================
    def _switch_channel(self, dev_label, channel_num):
        self.current_device = dev_label
        self.current_channel = channel_num
        self._apply_channel_theme(dev_label, channel_num)

    def _get_current_n6705c(self):
        dev = self.devices[self.current_device]
        if dev["is_connected"] and dev["n6705c"]:
            return dev["n6705c"]
        return None

    def _on_mode_button_clicked(self, clicked_button):
        for btn in self.mode_buttons:
            btn.setChecked(btn is clicked_button)
        self._apply_mode_button_styles()
        n6705c = self._get_current_n6705c()
        if n6705c:
            try:
                inst_mode = self._map_ui_mode_to_instrument_mode(self._get_current_mode_text())
                n6705c.set_mode(self.current_channel, inst_mode)
            except Exception as e:
                print(f"[{self.current_device}] 设置模式失败: {e}")

    def _get_current_mode_text(self):
        if self.cv_btn.isChecked(): return "PS2Q"
        if self.cc_btn.isChecked(): return "CC"
        if self.cr_btn.isChecked(): return "VMETer"
        if self.cp_btn.isChecked(): return "AMETer"
        return "PS2Q"

    def _map_ui_mode_to_instrument_mode(self, ui_mode):
        return {"PS2Q": "PS2Q", "CC": "CCLoad", "VMETer": "VMETer", "AMETer": "AMETer"}.get(ui_mode, "PS2Q")

    # =========================
    # 连接逻辑
    # =========================
    def _on_search(self, label):
        w = self.conn_widgets[label]
        w["status"].setText("搜索中...")
        w["status"].setStyleSheet("color: #ff9800; font-weight:bold;")
        w["search_btn"].setEnabled(False)
        timer = self.search_timer_a if label == "A" else self.search_timer_b
        timer.start(100)

    def _search_devices(self, label):
        w = self.conn_widgets[label]
        dev = self.devices[label]
        try:
            if dev["rm"] is None:
                try:
                    dev["rm"] = pyvisa.ResourceManager()
                except Exception:
                    dev["rm"] = pyvisa.ResourceManager('@ni')

            resources = list(dev["rm"].list_resources()) or []
            n6705c_devices = []
            for r in resources:
                try:
                    instr = dev["rm"].open_resource(r, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    if "N6705C" in idn:
                        n6705c_devices.append(r)
                except Exception:
                    pass

            w["combo"].clear()
            w["combo"].setEnabled(True)
            if n6705c_devices:
                for d in n6705c_devices:
                    w["combo"].addItem(d)
                w["status"].setText(f"找到 {len(n6705c_devices)} 个N6705C")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                w["connect_btn"].setEnabled(True)
                w["combo"].setCurrentIndex(0)
            else:
                w["combo"].addItem("未找到N6705C设备")
                w["combo"].setEnabled(False)
                w["status"].setText("未找到N6705C")
                w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
                w["connect_btn"].setEnabled(False)
        except Exception as e:
            w["status"].setText(f"搜索失败: {e}")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            w["connect_btn"].setEnabled(False)
        finally:
            w["search_btn"].setEnabled(True)

    def _on_connect(self, label):
        w = self.conn_widgets[label]
        dev = self.devices[label]
        w["status"].setText("连接中...")
        w["status"].setStyleSheet("color: #ff9800; font-weight:bold;")
        w["connect_btn"].setEnabled(False)
        try:
            address = w["combo"].currentText()
            dev["n6705c"] = N6705C(address)
            idn = dev["n6705c"].instr.query("*IDN?")
            if "N6705C" in idn:
                dev["is_connected"] = True
                w["status"].setText("已连接")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                w["disconnect_btn"].setEnabled(True)
            else:
                w["status"].setText("设备不匹配")
                w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
                w["connect_btn"].setEnabled(True)
        except Exception as e:
            w["status"].setText(f"连接失败: {e}")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            w["connect_btn"].setEnabled(True)

    def _on_disconnect(self, label):
        w = self.conn_widgets[label]
        dev = self.devices[label]
        w["status"].setText("断开中...")
        w["status"].setStyleSheet("color: #ff9800; font-weight:bold;")
        w["disconnect_btn"].setEnabled(False)
        try:
            if dev["n6705c"] and hasattr(dev["n6705c"], 'instr') and dev["n6705c"].instr:
                dev["n6705c"].instr.close()
            dev["n6705c"] = None
            dev["is_connected"] = False
            w["status"].setText("未连接")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            w["connect_btn"].setEnabled(True)
        except Exception as e:
            w["status"].setText(f"断开失败: {e}")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            w["disconnect_btn"].setEnabled(True)

    # =========================
    # 单通道操作
    # =========================
    def _on_channel_on(self):
        n6705c = self._get_current_n6705c()
        if n6705c:
            try:
                n6705c.channel_on(self.current_channel)
                self.output_toggle.setChecked(True)
            except Exception as e:
                print(f"[{self.current_device}] 打开通道{self.current_channel}失败: {e}")
        else:
            self.output_toggle.setChecked(True)

    def _on_channel_off(self):
        n6705c = self._get_current_n6705c()
        if n6705c:
            try:
                n6705c.channel_off(self.current_channel)
            except Exception as e:
                print(f"[{self.current_device}] 关闭通道{self.current_channel}失败: {e}")
        self.output_toggle.setChecked(False)

    def _on_output_toggle_clicked(self, checked):
        if checked:
            self._on_channel_on()
        else:
            self._on_channel_off()

    def _on_set_clicked(self):
        n6705c = self._get_current_n6705c()
        if not n6705c:
            return
        try:
            ch = self.current_channel
            voltage_set = float(self.voltage_set_input.text())
            current_set = float(self.current_value.text())
            limit_set = float(self.limit_current_value.text())
            inst_mode = self._map_ui_mode_to_instrument_mode(self._get_current_mode_text())
            n6705c.set_mode(ch, inst_mode)
            n6705c.set_voltage(ch, voltage_set)
            n6705c.set_current(ch, current_set)
            n6705c.set_current_limit(ch, limit_set)
        except Exception as e:
            print(f"[{self.current_device}] 设置发送失败: {e}")

    def _on_measure_clicked(self):
        n6705c = self._get_current_n6705c()
        if not n6705c:
            return
        try:
            ch = self.current_channel
            voltage = float(n6705c.measure_voltage(ch))
            current = float(n6705c.measure_current(ch))
            limit_current = float(n6705c.get_current_limit(ch))
            self.voltage_value.setText(f"{voltage:.4f}")
            self.current_value.setText(f"{current:.4f}")
            self.limit_current_value.setText(f"{limit_current:.4f}")
        except Exception as e:
            print(f"[{self.current_device}] 测量失败: {e}")

    # =========================
    # 全通道操作
    # =========================
    def _on_all_on_clicked(self):
        for label, dev in self.devices.items():
            if dev["is_connected"] and dev["n6705c"]:
                try:
                    for ch in range(1, 5):
                        dev["n6705c"].channel_on(ch)
                except Exception as e:
                    print(f"[{label}] All On 失败: {e}")
        self.output_toggle.setChecked(True)

    def _on_all_off_clicked(self):
        for label, dev in self.devices.items():
            if dev["is_connected"] and dev["n6705c"]:
                try:
                    for ch in range(1, 5):
                        dev["n6705c"].channel_off(ch)
                except Exception as e:
                    print(f"[{label}] All Off 失败: {e}")
        self.output_toggle.setChecked(False)

    # =========================
    # 批量操作
    # =========================
    def _get_selected_batch_channels(self):
        result = {"A": [], "B": []}
        for idx, btn in enumerate(self.batch_channel_buttons):
            if btn.isChecked():
                dev_label = "A" if idx < 4 else "B"
                ch = (idx % 4) + 1
                result[dev_label].append(ch)
        return result

    def _on_batch_measure(self):
        selected = self._get_selected_batch_channels()
        for label, channels in selected.items():
            dev = self.devices[label]
            if not dev["is_connected"] or not dev["n6705c"] or not channels:
                continue
            try:
                for ch in channels:
                    dev["n6705c"].set_mode(ch, "VMETer")
            except Exception as e:
                print(f"[{label}] 设置电压表模式失败: {e}")

    def _on_batch_set(self):
        selected = self._get_selected_batch_channels()
        for label, channels in selected.items():
            dev = self.devices[label]
            if not dev["is_connected"] or not dev["n6705c"] or not channels:
                continue
            try:
                offset = 0 if label == "A" else 4
                for ch in channels:
                    idx = offset + ch - 1
                    voltage = float(self.batch_voltage_inputs[idx].text())
                    current_limit = float(self.batch_current_inputs[idx].text())
                    dev["n6705c"].set_mode(ch, "PS2Q")
                    dev["n6705c"].set_voltage(ch, voltage)
                    dev["n6705c"].set_current_limit(ch, current_limit)
                    dev["n6705c"].channel_on(ch)
            except Exception as e:
                print(f"[{label}] 设置发送失败: {e}")

    def _on_batch_auto(self):
        selected = self._get_selected_batch_channels()
        for label, channels in selected.items():
            dev = self.devices[label]
            if not dev["is_connected"] or not dev["n6705c"] or not channels:
                continue
            try:
                for ch in channels:
                    dev["n6705c"].set_mode(ch, "VMETer")
                    measured_voltage = float(dev["n6705c"].measure_voltage(ch))
                    new_voltage = measured_voltage + 0.01
                    dev["n6705c"].set_mode(ch, "PS2Q")
                    dev["n6705c"].set_voltage(ch, new_voltage)
                    dev["n6705c"].channel_on(ch)
            except Exception as e:
                print(f"[{label}] Auto操作失败: {e}")

    # =========================
    # Consumption Test 逻辑
    # =========================
    def _ct_start_test(self):
        if self.is_testing:
            return

        try:
            test_time = float(self.ct_test_time_input.text())
            sample_period = float(self.ct_sample_period_input.text())
        except ValueError:
            return

        tasks = {}
        for dev_label in ["A", "B"]:
            dev = self.devices[dev_label]
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            selected = [
                ch for ch in range(1, 5)
                if self.ct_channel_cards[(dev_label, ch)]["checkbox"].isChecked()
            ]
            if selected:
                tasks[dev_label] = selected

        if not tasks:
            return

        self.is_testing = True
        self.ct_start_btn.setEnabled(False)
        self.ct_stop_btn.setEnabled(True)
        self._pending_tests = set(tasks.keys())

        for dev_label in ["A", "B"]:
            for ch in range(1, 5):
                self.ct_channel_cards[(dev_label, ch)]["value_label"].setText("- - -")

        for dev_label, channels in tasks.items():
            worker = _ConsumptionTestWorker(
                self.devices[dev_label]["n6705c"], dev_label, channels, test_time, sample_period
            )
            thread = QThread()
            worker.moveToThread(thread)

            thread.started.connect(worker.run)
            worker.channel_result.connect(self._ct_on_channel_result)
            worker.error.connect(self._ct_on_error)
            worker.finished.connect(self._ct_on_ui_update)
            worker.finished.connect(thread.quit)
            thread.finished.connect(lambda lb=dev_label: self._ct_on_thread_cleaned(lb))
            thread.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            self._test_threads[dev_label] = thread
            self._test_workers[dev_label] = worker
            thread.start()

    def _ct_on_channel_result(self, dev_label, channel, avg_current):
        key = (dev_label, channel)
        if key in self.ct_channel_cards:
            label = self.ct_channel_cards[key]["value_label"]
            if avg_current is not None:
                label.setText(_format_current(avg_current))
            else:
                label.setText("- - -")

    def _ct_on_error(self, err_msg):
        print(f"Consumption test error: {err_msg}")

    def _ct_on_ui_update(self):
        if not self._pending_tests:
            self.is_testing = False
            self.ct_start_btn.setEnabled(True)
            self.ct_stop_btn.setEnabled(False)

    def _ct_on_thread_cleaned(self, dev_label):
        self._test_workers.pop(dev_label, None)
        self._test_threads.pop(dev_label, None)
        self._pending_tests.discard(dev_label)
        if not self._pending_tests:
            self.is_testing = False
            self.ct_start_btn.setEnabled(True)
            self.ct_stop_btn.setEnabled(False)

    def _ct_stop_test(self):
        for worker in self._test_workers.values():
            worker.stop()
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = N6705CDoubleUI()
    win.setWindowTitle("N6705C × 2 DC Power Analyzer")
    win.setGeometry(50, 50, 1400, 950)
    win.show()

    sys.exit(app.exec())
