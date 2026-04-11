#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ui.widgets.dark_combobox import DarkComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGridLayout, QFrame, QApplication, QCheckBox,
    QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from log_config import get_logger

logger = get_logger(__name__)
from ui.pages.power.n6705c_ui import SlideToggle


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


class _DoubleChannelSyncWorker(QObject):
    result = Signal(dict)
    finished = Signal()

    def __init__(self, n6705c, channel_num):
        super().__init__()
        self.n6705c = n6705c
        self.channel_num = channel_num

    def run(self):
        data = {}
        try:
            data["channel_state"] = self.n6705c.get_channel_state(self.channel_num)
        except Exception:
            data["channel_state"] = None
        try:
            data["mode"] = self.n6705c.get_mode(self.channel_num)
        except Exception:
            data["mode"] = None
        try:
            data["voltage"] = float(self.n6705c.fetch_voltage(self.channel_num))
        except Exception:
            data["voltage"] = None
        try:
            data["current"] = float(self.n6705c.fetch_current(self.channel_num))
        except Exception:
            data["current"] = None
        try:
            data["limit_current"] = float(self.n6705c.get_current_limit(self.channel_num))
        except Exception:
            data["limit_current"] = None
        self.result.emit(data)
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
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
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
    QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
    """


def _neon_off_button_style():
    return """
    QPushButton {
        background-color: #2a0a1c; color: #ff4fa3;
        border: 1px solid #d63384; border-radius: 8px;
        padding: 8px 18px; min-width: 88px; font-size: 12px; font-weight: 600;
    }
    QPushButton:hover { background-color: #3a1028; border: 1px solid #ff4fa3; color: #ff7dbd; }
    QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
    """


def _outline_action_button_style():
    return """
    QPushButton {
        background-color: #0c1a38; color: #8eb4e8;
        border: 1px solid #23417a; border-radius: 6px;
        padding: 8px 16px; font-size: 11px; min-width: 88px; font-weight: 700;
    }
    QPushButton:hover { background-color: #122448; color: #b8d4ff; border: 1px solid #3a6cc8; }
    QPushButton:disabled { background-color: #0D1734; color: #3a4a6a; border: 1px solid #18264A; }
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
        QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
    """


def _connect_button_style():
    return """
        QPushButton {
            background-color: #0a3d28; color: #00f5c4;
            border: 1px solid #00cfa6; border-radius: 8px;
            padding: 6px 18px; font-size: 12px; font-weight: 700;
            min-width: 90px;
        }
        QPushButton:hover { background-color: #0e5535; border: 1px solid #00f5c4; color: #3fffd7; }
        QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
    """


def _disconnect_button_style():
    return """
        QPushButton {
            background-color: #3d1a1a; color: #ff6b6b;
            border: 1px solid #ff4444; border-radius: 8px;
            padding: 6px 18px; font-size: 12px; font-weight: 700;
            min-width: 90px;
        }
        QPushButton:hover { background-color: #552222; border: 1px solid #ff6b6b; color: #ff9999; }
        QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
    """


class N6705CDoubleUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._top = n6705c_top
        self.devices = {
            "A": {"rm": None, "n6705c": None, "is_connected": False},
            "B": {"rm": None, "n6705c": None, "is_connected": False},
        }

        self.current_device = "A"
        self.current_channel = 1
        self.is_testing = False
        self._test_threads = {}
        self._test_workers = {}
        self._sync_thread = None
        self._sync_worker = None
        self._dirty_voltage = False
        self._dirty_current = False

        self._setup_style()
        self._create_layout()

        self.search_timer_a = QTimer(self)
        self.search_timer_a.timeout.connect(lambda: self._search_devices("A"))
        self.search_timer_a.setSingleShot(True)

        self.search_timer_b = QTimer(self)
        self.search_timer_b.timeout.connect(lambda: self._search_devices("B"))
        self.search_timer_b.setSingleShot(True)

        self._apply_channel_theme(self.current_device, self.current_channel)

        self._update_ui_connection_state("A", False)

        if self._top:
            self._sync_from_top()

    def _sync_from_top(self):
        if not self._top:
            return
        for label, attr_suffix in [("A", "a"), ("B", "b")]:
            n6705c = getattr(self._top, f"n6705c_{attr_suffix}", None)
            is_conn = getattr(self._top, f"is_connected_{attr_suffix}", False)
            visa_res = getattr(self._top, f"visa_resource_{attr_suffix}", "")
            if is_conn and n6705c:
                self.devices[label]["n6705c"] = n6705c
                self.devices[label]["is_connected"] = True
                w = self.conn_widgets[label]
                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                if visa_res:
                    w["combo"].clear()
                    w["combo"].addItem(visa_res)
                w["toggle_conn_btn"].setText("Disconnect")
                w["toggle_conn_btn"].setStyleSheet(_disconnect_button_style())
                self._update_ui_connection_state(label, True)
        if self.devices[self.current_device]["is_connected"]:
            self._start_channel_sync()

    def _start_channel_sync(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        if self._sync_thread is not None and self._sync_thread.isRunning():
            return
        worker = _DoubleChannelSyncWorker(dev["n6705c"], self.current_channel)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.result.connect(self._on_channel_sync_result)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_channel_sync_done)
        self._sync_thread = thread
        self._sync_worker = worker
        thread.start()

    def _on_channel_sync_result(self, data):
        if data.get("channel_state") is not None:
            self.output_toggle.setChecked(data["channel_state"])
        self._update_output_visual_state()

        mode_raw = data.get("mode")
        if mode_raw is not None:
            ui_mode = self._map_instrument_mode_to_ui_mode(mode_raw)
            for btn in self.mode_buttons:
                btn.setChecked(btn.text() == ui_mode)
            self._apply_mode_button_styles()
            self._update_labels_for_mode(ui_mode)

        voltage = data.get("voltage")
        current = data.get("current")
        limit_current = data.get("limit_current")
        if voltage is not None and current is not None and limit_current is not None:
            self.update_channel_values(self.current_device, self.current_channel, voltage, current, limit_current)

        self._dirty_voltage = False
        self._dirty_current = False
        self._update_set_button_dirty_state()

    def _on_channel_sync_done(self):
        self._sync_thread = None
        self._sync_worker = None

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
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
            background-color: #070F28; border: 1px solid #131D3A; color: #4a5a7a;
        }
        QPushButton {
            background-color: #0b1730; border: 1px solid #23417a;
            border-radius: 6px; padding: 6px 14px; color: #dbe6ff;
        }
        QPushButton:hover { background-color: #10203e; }
        QPushButton:disabled {
            background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847;
        }
        QCheckBox:disabled { color: #4a5a7a; }
        """)

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(8, 8, 8, 8)

        self.top_bar = self._create_top_bar()
        main_layout.addWidget(self.top_bar)
        main_layout.addSpacing(8)

        self.batch_tools_panel = self._create_batch_tools_panel()
        main_layout.addWidget(self.batch_tools_panel)
        main_layout.addSpacing(8)

        self.channel_tabs = self._create_channel_tabs()
        main_layout.addWidget(self.channel_tabs)

        self.setting_widget = self._create_setting_widget()
        main_layout.addWidget(self.setting_widget, 1)

        self.consumption_test_panel = self._create_consumption_test_panel()
        main_layout.addWidget(self.consumption_test_panel)

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
            QComboBox QAbstractItemView::item:hover { background-color: #1a3260; }
            QComboBox QFrame { background-color: #091426; border: 1px solid #17345f; }
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

            status = QLabel("● Disconnected")
            status.setStyleSheet("color:#8ea6cf; font-weight:bold;")

            combo = DarkComboBox(bg="#091426", border="#17345f")
            combo.setMinimumWidth(300)
            combo.addItem(default_addresses[label])

            search_btn = QPushButton("Search")

            toggle_conn_btn = QPushButton("Connect")
            toggle_conn_btn.setStyleSheet(_connect_button_style())
            toggle_conn_btn.clicked.connect(lambda _checked=False, lb=label: self._on_toggle_connection(lb))

            search_btn.clicked.connect(lambda _checked=False, lb=label: self._on_search(lb))

            grid.addWidget(tag, row, 0)
            grid.addWidget(status, row, 1)
            grid.addWidget(combo, row, 2, 1, 2)
            grid.addWidget(search_btn, row, 4)
            grid.addWidget(toggle_conn_btn, row, 5)

            self.conn_widgets[label] = {
                "status": status, "combo": combo,
                "search_btn": search_btn, "toggle_conn_btn": toggle_conn_btn,
            }

        outer_layout.addWidget(content_widget)
        return top_frame

    def _create_channel_tabs(self):
        tab_wrap = QWidget()
        tab_wrap.setAttribute(Qt.WA_StyledBackground, True)
        tab_wrap.setStyleSheet("QWidget { background-color: #07111f; border: none; }")

        layout = QHBoxLayout(tab_wrap)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.channel_tab_buttons = []
        for dev_label in ["A", "B"]:
            for ch in range(1, 5):
                btn = QPushButton(f"● {dev_label}-CH{ch}")
                btn.setCheckable(True)
                btn.setMinimumSize(90, 34)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(
                    lambda checked=False, d=dev_label, c=ch: self._switch_channel(d, c)
                )
                self.channel_tab_buttons.append(btn)
                layout.addWidget(btn)
            if dev_label == "A":
                sep = QFrame()
                sep.setFixedWidth(2)
                sep.setFixedHeight(24)
                sep.setStyleSheet("QFrame { background: #1b2847; border: none; }")
                layout.addWidget(sep)

        layout.addStretch()
        self.channel_tab_buttons[0].setChecked(True)
        self._refresh_channel_tab_styles()
        return tab_wrap

    def _create_unified_input(self, prefix_text, default_value, unit_text):
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #091426;
                border: 1px solid #17345f;
                border-radius: 8px;
            }
        """)
        container.setFixedHeight(36)

        h_layout = QHBoxLayout(container)
        h_layout.setContentsMargins(10, 0, 10, 0)
        h_layout.setSpacing(6)

        prefix = QLabel(prefix_text)
        prefix.setStyleSheet("color: #5a7aa8; font-size: 12px; font-weight: 600; border: none; background: transparent;")
        prefix.setFixedWidth(28)
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
        unit.setStyleSheet("color: #4a6490; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        unit.setFixedWidth(16)
        h_layout.addWidget(unit)

        return container, prefix, input_field, unit

    def _create_setting_widget(self):
        setting_wrapper = QWidget()
        setting_wrapper.setStyleSheet("QWidget { background: transparent; border: none; }")
        wrapper_layout = QVBoxLayout(setting_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        self.accent_top_line = QFrame()
        self.accent_top_line.setFixedHeight(3)
        self.accent_top_line.setStyleSheet("QFrame { background-color: transparent; border: none; border-radius: 0px; }")
        wrapper_layout.addWidget(self.accent_top_line)

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
            btn.setMinimumHeight(30)
            btn.setMinimumWidth(70)
            btn.clicked.connect(lambda checked=False, b=btn: self._on_mode_button_clicked(b))

        self.cv_btn.setChecked(True)

        mode_container = QFrame()
        mode_container.setStyleSheet("""
            QFrame {
                background-color: #0c1628;
                border: 1px solid #1b2842;
                border-radius: 8px;
            }
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
        voltage_label.setStyleSheet("QLabel { font-size: 14px; color: #97aed9; border: none; }")
        voltage_layout.addWidget(voltage_label)

        self.voltage_value = QLineEdit("0.0000")
        self.voltage_value.setFrame(False)
        self.voltage_value.setReadOnly(True)
        self.voltage_value.setStyleSheet("""
            QLineEdit { font-size: 22px; font-weight: bold; color: #6d83b3; background: transparent; border: none; }
        """)
        self.voltage_value.setFixedHeight(40)
        voltage_layout.addWidget(self.voltage_value)

        (self.voltage_input_container, self.voltage_set_label,
         self.voltage_set_input, self._voltage_unit_label) = self._create_unified_input("Set", "5", "V")
        self.voltage_set_input.returnPressed.connect(self._on_voltage_input_enter)
        self.voltage_set_input.textChanged.connect(self._on_voltage_text_changed)
        voltage_layout.addWidget(self.voltage_input_container)
        params_grid.addWidget(voltage_frame, 0, 0)

        current_frame = QFrame()
        current_frame.setStyleSheet("QFrame { background-color: #0b1b34; border: 1px solid #102746; border-radius: 12px; }")
        current_layout = QVBoxLayout(current_frame)
        current_layout.setContentsMargins(14, 14, 14, 14)
        current_layout.setSpacing(8)

        current_label = QLabel("Current (A)")
        current_label.setStyleSheet("QLabel { font-size: 14px; color: #97aed9; border: none; }")
        current_layout.addWidget(current_label)

        self.current_value = QLineEdit("0.0000")
        self.current_value.setReadOnly(True)
        self.current_value.setStyleSheet("""
            QLineEdit { font-size: 22px; font-weight: bold; color: #6d83b3; background-color: transparent; border: none; }
        """)
        self.current_value.setFixedHeight(40)
        current_layout.addWidget(self.current_value)

        (self.current_input_container, self.current_set_label,
         self.limit_current_value, self._current_unit_label) = self._create_unified_input("Lim", "1", "A")
        self.limit_current_value.returnPressed.connect(self._on_current_input_enter)
        self.limit_current_value.textChanged.connect(self._on_current_text_changed)
        current_layout.addWidget(self.current_input_container)
        params_grid.addWidget(current_frame, 0, 1)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)

        self.measure_btn = QPushButton("MEASURE")
        self.measure_btn.setStyleSheet(_outline_action_button_style())
        self.measure_btn.clicked.connect(self._on_measure_clicked)

        self.set_btn = QPushButton("SET")
        self.set_btn.setStyleSheet(_outline_action_button_style())
        self.set_btn.clicked.connect(self._on_set_clicked)

        action_row.addWidget(self.measure_btn)
        action_row.addWidget(self.set_btn)
        action_row.addStretch()

        params_grid.addLayout(action_row, 1, 0, 1, 2)

        setting_layout.addWidget(params_container)

        wrapper_layout.addWidget(self.setting_frame)
        return setting_wrapper

    def _create_batch_tools_panel(self):
        self.batch_collapsed = True

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.batch_toggle_btn = QPushButton("▶  Quick Setup")
        self.batch_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a1930; color: #8ea6cf;
                border: 1px solid #132849; border-radius: 8px;
                padding: 8px 16px; font-size: 12px; font-weight: 700;
                text-align: left;
            }
            QPushButton:hover { background-color: #0e1f3d; color: #b8d0f0; }
        """)
        self.batch_toggle_btn.clicked.connect(self._toggle_batch_panel)
        outer_layout.addWidget(self.batch_toggle_btn)

        self.batch_content = QFrame()
        self.batch_content.setStyleSheet("""
            QFrame {
                background-color: #0a1930;
                border: 1px solid #132849;
                border-top: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        self.batch_content.setVisible(False)

        tools_layout = QVBoxLayout(self.batch_content)
        tools_layout.setContentsMargins(12, 10, 12, 12)
        tools_layout.setSpacing(10)

        ab_columns_layout = QHBoxLayout()
        ab_columns_layout.setSpacing(12)

        self.batch_channel_buttons = []
        self.batch_voltage_inputs = {}
        self.batch_current_inputs = {}

        for dev_label, dev_color in [("A", "#00f5c4"), ("B", "#f2994a")]:
            col_frame = QFrame()
            col_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #0b1b34;
                    border: 1px solid #102746;
                    border-radius: 10px;
                }}
            """)
            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(10, 8, 10, 8)
            col_layout.setSpacing(8)

            col_title = QLabel(f"Device {dev_label}")
            col_title.setStyleSheet(f"color: {dev_color}; font-weight: 800; font-size: 13px; border: none;")
            col_layout.addWidget(col_title)

            ch_row = QHBoxLayout()
            ch_row.setSpacing(6)
            ch_label = QLabel("Channels:")
            ch_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
            ch_row.addWidget(ch_label)
            for ch in range(1, 5):
                cb = QPushButton(f"CH {ch}")
                cb.setCheckable(True)
                if ch in [2, 3, 4]:
                    cb.setChecked(True)
                cb.setStyleSheet(_batch_channel_button_style())
                self.batch_channel_buttons.append((dev_label, ch, cb))
                ch_row.addWidget(cb)
            ch_row.addStretch()
            col_layout.addLayout(ch_row)

            v_row = QHBoxLayout()
            v_row.setSpacing(6)
            v_lbl = QLabel("Voltage (V):")
            v_lbl.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
            v_row.addWidget(v_lbl)
            self.batch_voltage_inputs[dev_label] = []
            for v in [3.8, 0.8, 1.2, 1.8]:
                inp = QLineEdit(f"{v:.4f}")
                inp.setFixedWidth(80)
                self.batch_voltage_inputs[dev_label].append(inp)
                v_row.addWidget(inp)
            v_row.addStretch()
            col_layout.addLayout(v_row)

            c_row = QHBoxLayout()
            c_row.setSpacing(6)
            c_lbl = QLabel("Current Limit (A):")
            c_lbl.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
            c_row.addWidget(c_lbl)
            self.batch_current_inputs[dev_label] = []
            for c in [0.2, 0.02, 0.02, 0.02]:
                inp = QLineEdit(f"{c:.4f}")
                inp.setFixedWidth(80)
                self.batch_current_inputs[dev_label].append(inp)
                c_row.addWidget(inp)
            c_row.addStretch()
            col_layout.addLayout(c_row)

            ab_columns_layout.addWidget(col_frame, 1)

        tools_layout.addLayout(ab_columns_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        measure_all_btn = QPushButton("Measure")
        set_all_btn = QPushButton("Set")
        auto_btn = QPushButton("Auto")

        for btn in [measure_all_btn, set_all_btn, auto_btn]:
            btn.setStyleSheet(_outline_action_button_style())
            buttons_layout.addWidget(btn)

        measure_all_btn.clicked.connect(self._on_batch_measure)
        set_all_btn.clicked.connect(self._on_batch_set)
        auto_btn.clicked.connect(self._on_batch_auto)

        buttons_layout.addStretch()
        tools_layout.addLayout(buttons_layout)

        outer_layout.addWidget(self.batch_content)
        return outer

    def _toggle_batch_panel(self):
        self.batch_collapsed = not self.batch_collapsed
        self.batch_content.setVisible(not self.batch_collapsed)
        if self.batch_collapsed:
            self.batch_toggle_btn.setText("▶  Quick Setup")
            self.batch_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930; color: #8ea6cf;
                    border: 1px solid #132849; border-radius: 8px;
                    padding: 8px 16px; font-size: 12px; font-weight: 700; text-align: left;
                }
                QPushButton:hover { background-color: #0e1f3d; color: #b8d0f0; }
            """)
        else:
            self.batch_toggle_btn.setText("▼  Quick Setup")
            self.batch_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930; color: #b8d0f0;
                    border: 1px solid #132849; border-bottom: none;
                    border-top-left-radius: 8px; border-top-right-radius: 8px;
                    border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
                    padding: 8px 16px; font-size: 12px; font-weight: 700; text-align: left;
                }
                QPushButton:hover { background-color: #0e1f3d; color: #d0e4ff; }
            """)

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
        icon.setStyleSheet("font-size: 16px; color: #f2c94c; border: none;")
        title = QLabel("Current Consumption Test")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff; border: none;")
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

        time_label = QLabel("Test Time (s):")
        time_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
        self.ct_test_time_input = QLineEdit("10")
        self.ct_test_time_input.setFixedWidth(80)
        self.ct_test_time_input.setAlignment(Qt.AlignCenter)

        period_label = QLabel("Sample Period (s):")
        period_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
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

        self.ct_start_btn = QPushButton("▶  START TEST")
        self.ct_start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ct_start_btn.setStyleSheet("""
            QPushButton {
                background-color: #062b2b; color: #00f5c4;
                border: 1px solid #00cfa6; border-radius: 8px;
                font-weight: 700; font-size: 13px; min-height: 38px;
            }
            QPushButton:hover { background-color: #0a3a3a; }
            QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
        """)

        self.ct_stop_btn = QPushButton("■  STOP")
        self.ct_stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ct_stop_btn.setEnabled(False)
        self.ct_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a0a1c; color: #ff4fa3;
                border: 1px solid #d63384; border-radius: 8px;
                font-weight: 700; font-size: 13px; min-height: 38px;
            }
            QPushButton:hover { background-color: #3a1028; }
            QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
        """)

        btn_row.addWidget(self.ct_start_btn, 1)
        btn_row.addWidget(self.ct_stop_btn, 1)
        layout.addLayout(btn_row)

        devices_row = QHBoxLayout()
        devices_row.setSpacing(12)

        self.ct_channel_cards = {}
        for dev_label, dev_color in [("A", "#00f5c4"), ("B", "#f2994a")]:
            dev_frame = QFrame()
            dev_frame.setStyleSheet(f"""
                QFrame {{ background-color: #0b1b34; border: 1px solid #102746; border-radius: 10px; }}
            """)
            dev_layout = QVBoxLayout(dev_frame)
            dev_layout.setContentsMargins(10, 8, 10, 8)
            dev_layout.setSpacing(6)

            dev_title = QLabel(f"Device {dev_label}")
            dev_title.setStyleSheet(f"color: {dev_color}; font-weight: 700; font-size: 12px; border: none;")
            dev_layout.addWidget(dev_title)

            ch_row = QHBoxLayout()
            ch_row.setSpacing(6)
            for ch in range(1, 5):
                card = self._create_ct_channel_card(dev_label, ch)
                ch_row.addWidget(card, 1)
            dev_layout.addLayout(ch_row)

            devices_row.addWidget(dev_frame, 1)

        layout.addLayout(devices_row, 1)

        self.ct_start_btn.clicked.connect(self._ct_start_test)
        self.ct_stop_btn.clicked.connect(self._ct_stop_test)
        self.ct_save_btn.clicked.connect(self._ct_save_datalog)

        return panel

    def _create_ct_channel_card(self, dev_label, ch_num):
        colors = CHANNEL_COLORS[ch_num]
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: {colors['bg']}; border: 1px solid {colors['border']}; border-radius: 8px; }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(90)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        icons = _get_checkmark_path(colors['accent'])
        checkbox = QCheckBox(f"CH {ch_num}")
        checkbox.setChecked(False)
        checkbox.setStyleSheet(f"""
            QCheckBox {{ color: #ffffff; font-size: 12px; font-weight: 700; background: transparent; spacing: 5px; }}
            QCheckBox::indicator {{ width: 16px; height: 16px; image: url("{icons['unchecked']}"); }}
            QCheckBox::indicator:checked {{ image: url("{icons['checked']}"); }}
        """)
        layout.addWidget(checkbox)
        layout.addStretch()

        avg_label = QLabel("AVG CURRENT")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setStyleSheet("color: #8ea6cf; font-size: 10px; font-weight: 600; border: none;")
        layout.addWidget(avg_label)

        value_label = QLabel("- - -")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"color: {colors['accent']}; font-size: 16px; font-weight: 700; letter-spacing: 3px;")
        layout.addWidget(value_label)

        layout.addStretch()

        key = (dev_label, ch_num)
        self.ct_channel_cards[key] = {
            "card": card, "checkbox": checkbox, "value_label": value_label,
        }
        return card

    def _channel_action_button_style(self, accent, accent_hover):
        return f"""
        QPushButton {{
            background-color: #0c1a38; color: {accent};
            border: 1px solid {accent}; border-radius: 6px;
            padding: 8px 16px; font-size: 11px; min-width: 88px; font-weight: 700;
        }}
        QPushButton:hover {{ background-color: #12213f; color: {accent_hover}; border: 1px solid {accent_hover}; }}
        QPushButton:disabled {{ background-color: #0D1734; color: #3a4a6a; border: 1px solid #18264A; }}
        """

    def _dirty_set_button_style(self, accent):
        return f"""
        QPushButton {{
            background-color: {accent}; color: #111111; border: none;
            border-radius: 6px; padding: 8px 16px; font-size: 11px;
            min-width: 88px; font-weight: 700;
        }}
        QPushButton:hover {{ background-color: {accent}; }}
        QPushButton:disabled {{ background-color: #0D1734; color: #3a4a6a; border: 1px solid #18264A; }}
        """

    def _build_channel_tab_style(self, dev_label, ch, checked=False):
        theme = CHANNEL_THEMES[ch]
        disabled_part = f"""
            QPushButton:disabled {{
                background-color: #0a1224;
                color: #3a4a6a;
                border: 1px solid #151f36;
                border-radius: 17px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 700;
            }}
        """
        if checked:
            return f"""
            QPushButton {{
                background-color: {theme['accent_soft']};
                color: {theme['accent']};
                border: 1px solid {theme['accent_border']};
                border-radius: 17px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            {disabled_part}
            """
        else:
            return f"""
            QPushButton {{
                background-color: #0b1730;
                color: {theme['text_dim']};
                border: 1px solid #1b2847;
                border-radius: 17px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #0f1f3a;
                color: #ffffff;
                border: 1px solid {theme['accent_border']};
            }}
            {disabled_part}
            """

    def _build_mode_button_style(self, active=False):
        theme = CHANNEL_THEMES[self.current_channel]
        disabled_part = """
            QPushButton:disabled {
                background-color: transparent; color: #3a4a6a;
                border: none; padding: 6px 14px; font-size: 12px; border-radius: 6px;
            }
        """
        if active:
            return f"""
            QPushButton {{
                background-color: {theme['accent']}; color: #111111;
                border: none; padding: 6px 14px; font-size: 12px;
                font-weight: 700; border-radius: 6px;
            }}
            {disabled_part}
            """
        else:
            return f"""
            QPushButton {{
                background-color: transparent; color: #7c8aac;
                border: none; padding: 6px 14px; font-size: 12px; border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: #0f1d35; color: #dbe6ff; }}
            {disabled_part}
            """

    def _apply_mode_button_styles(self):
        for btn in self.mode_buttons:
            btn.setStyleSheet(self._build_mode_button_style(btn.isChecked()))

    def _refresh_channel_tab_styles(self):
        idx = 0
        for dev_label in ["A", "B"]:
            for ch in range(1, 5):
                is_active = (dev_label == self.current_device and ch == self.current_channel)
                self.channel_tab_buttons[idx].setStyleSheet(
                    self._build_channel_tab_style(dev_label, ch, is_active)
                )
                self.channel_tab_buttons[idx].setChecked(is_active)
                idx += 1

    def _apply_channel_theme(self, dev_label, channel_num):
        theme = CHANNEL_THEMES[channel_num]
        self.channel_title_label.setText(f"{dev_label} - Channel {channel_num}")

        self.setting_frame.setStyleSheet(f"""
            QFrame {{ background-color: #0a1930; border: 1px solid {theme['accent_border']}; border-radius: 14px; }}
        """)

        self.output_toggle.setAccentColor(theme['accent'])

        btn_style = self._channel_action_button_style(theme['accent'], theme['accent_hover'])
        self.measure_btn.setStyleSheet(btn_style)
        self.set_btn.setStyleSheet(btn_style)

        self._refresh_channel_tab_styles()
        self._apply_mode_button_styles()
        self._update_output_visual_state()
        self._update_set_button_dirty_state()

    def _on_voltage_text_changed(self, text):
        self._dirty_voltage = True
        self._update_set_button_dirty_state()

    def _on_current_text_changed(self, text):
        self._dirty_current = True
        self._update_set_button_dirty_state()

    def _update_set_button_dirty_state(self):
        if (self._dirty_voltage or self._dirty_current) and self.set_btn.isEnabled():
            theme = CHANNEL_THEMES[self.current_channel]
            self.set_btn.setStyleSheet(self._dirty_set_button_style(theme['accent']))
        else:
            theme = CHANNEL_THEMES[self.current_channel]
            self.set_btn.setStyleSheet(self._channel_action_button_style(theme['accent'], theme['accent_hover']))

    def _update_output_visual_state(self):
        is_on = self.output_toggle.isChecked()
        theme = CHANNEL_THEMES[self.current_channel]
        accent = theme['accent']

        if is_on:
            self.accent_top_line.setStyleSheet(
                f"QFrame {{ background-color: {accent}; border: none; border-radius: 0px; }}"
            )
            value_color = accent
        else:
            self.accent_top_line.setStyleSheet(
                "QFrame { background-color: transparent; border: none; border-radius: 0px; }"
            )
            value_color = "#6d83b3"

        self.voltage_value.setStyleSheet(f"""
            QLineEdit {{ font-size: 22px; font-weight: bold; color: {value_color}; background: transparent; border: none; }}
        """)
        self.current_value.setStyleSheet(f"""
            QLineEdit {{ font-size: 22px; font-weight: bold; color: {value_color}; background-color: transparent; border: none; }}
        """)

    def _switch_channel(self, dev_label, ch):
        self.current_device = dev_label
        self.current_channel = ch
        self._dirty_voltage = False
        self._dirty_current = False
        self._apply_channel_theme(dev_label, ch)
        self._start_channel_sync()

    def _map_instrument_mode_to_ui_mode(self, inst_mode):
        mapping = {
            "PS2Q": "PS2Q", "CCL": "CC", "CCLOAD": "CC", "CCLoad": "CC",
            "VMET": "VMETer", "VMETER": "VMETer", "VMETer": "VMETer",
            "AMET": "AMETer", "AMETER": "AMETer", "AMETer": "AMETer",
        }
        return mapping.get(inst_mode, inst_mode)

    def _map_ui_mode_to_instrument_mode(self, ui_mode):
        return {"PS2Q": "PS2Q", "CC": "CCLoad", "VMETer": "VMETer", "AMETer": "AMETer"}.get(ui_mode, "PS2Q")

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

    def _update_labels_for_mode(self, ui_mode):
        if ui_mode == "PS2Q":
            self.voltage_set_label.setText("Set")
            self.current_set_label.setText("Lim")
            self.voltage_set_input.setEnabled(True)
            self.limit_current_value.setEnabled(True)
            self.voltage_input_container.setStyleSheet("""
                QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }
            """)
            self.current_input_container.setStyleSheet("""
                QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }
            """)
        elif ui_mode == "CC":
            self.voltage_set_label.setText("Lim")
            self.current_set_label.setText("Set")
            self.voltage_set_input.setEnabled(True)
            self.limit_current_value.setEnabled(True)
            self.voltage_input_container.setStyleSheet("""
                QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }
            """)
            self.current_input_container.setStyleSheet("""
                QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }
            """)
        else:
            self.voltage_set_label.setText("---")
            self.current_set_label.setText("---")
            self.voltage_set_input.setEnabled(False)
            self.limit_current_value.setEnabled(False)
            self.voltage_input_container.setStyleSheet("""
                QFrame { background-color: #070F28; border: 1px solid #131D3A; border-radius: 8px; }
            """)
            self.current_input_container.setStyleSheet("""
                QFrame { background-color: #070F28; border: 1px solid #131D3A; border-radius: 8px; }
            """)

    def _on_mode_button_clicked(self, clicked_button):
        for btn in self.mode_buttons:
            btn.setChecked(btn is clicked_button)
        self._apply_mode_button_styles()

        ui_mode = self._get_current_mode_text()
        self._update_labels_for_mode(ui_mode)

        dev = self.devices[self.current_device]
        if dev["is_connected"] and dev["n6705c"]:
            try:
                inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
                dev["n6705c"].set_mode(self.current_channel, inst_mode)
                logger.info("[%s] Channel %d mode set to: %s", self.current_device, self.current_channel, inst_mode)
                self._start_channel_sync()
            except Exception as e:
                logger.error("Failed to set mode: %s", e)

    def _on_output_toggle_clicked(self, checked):
        dev = self.devices[self.current_device]
        if dev["is_connected"] and dev["n6705c"]:
            try:
                if checked:
                    dev["n6705c"].channel_on(self.current_channel)
                else:
                    dev["n6705c"].channel_off(self.current_channel)
            except Exception as e:
                logger.error("Toggle failed: %s", e)
        self._update_output_visual_state()

    def _on_voltage_input_enter(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        try:
            value = float(self.voltage_set_input.text())
            ui_mode = self._get_current_mode_text()
            if ui_mode == "PS2Q":
                dev["n6705c"].set_voltage(self.current_channel, value)
            elif ui_mode == "CC":
                dev["n6705c"].set_voltage_limit(self.current_channel, value)
        except Exception as e:
            logger.error("Voltage set failed: %s", e)

    def _on_current_input_enter(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        try:
            value = float(self.limit_current_value.text())
            ui_mode = self._get_current_mode_text()
            if ui_mode == "PS2Q":
                dev["n6705c"].set_current_limit(self.current_channel, value)
            elif ui_mode == "CC":
                value = -abs(value)
                self.limit_current_value.setText(f"{value:.4f}")
                dev["n6705c"].set_current(self.current_channel, value)
        except Exception as e:
            logger.error("Current set failed: %s", e)

    def _on_measure_clicked(self):
        self._start_channel_sync()

    def _on_set_clicked(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        try:
            n6705c = dev["n6705c"]
            ch = self.current_channel
            ui_mode = self._get_current_mode_text()
            inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
            n6705c.set_mode(ch, inst_mode)

            if ui_mode == "PS2Q":
                n6705c.set_voltage(ch, float(self.voltage_set_input.text()))
                n6705c.set_current_limit(ch, float(self.limit_current_value.text()))
            elif ui_mode == "CC":
                n6705c.set_voltage_limit(ch, float(self.voltage_set_input.text()))
                cur = -abs(float(self.limit_current_value.text()))
                self.limit_current_value.setText(f"{cur:.4f}")
                n6705c.set_current(ch, cur)

            self._dirty_voltage = False
            self._dirty_current = False
            self._update_set_button_dirty_state()
            logger.info("[%s] Channel %d settings applied", self.current_device, ch)
        except Exception as e:
            logger.error("Set failed: %s", e)

    def update_channel_values(self, dev_label, channel_num, voltage, current, limit_current):
        if dev_label == self.current_device and channel_num == self.current_channel:
            self.voltage_value.setText(f"{voltage:.4f}")
            self.current_value.setText(f"{current:.4f}")
            self.limit_current_value.setText(f"{limit_current:.4f}")

    def _on_all_on_clicked(self):
        for label, dev in self.devices.items():
            if dev["is_connected"] and dev["n6705c"]:
                try:
                    for ch in range(1, 5):
                        dev["n6705c"].channel_on(ch)
                    logger.info("[%s] All channels on", label)
                except Exception as e:
                    logger.error("[%s] All On failed: %s", label, e)
        self.output_toggle.setChecked(True)
        self._update_output_visual_state()

    def _on_all_off_clicked(self):
        for label, dev in self.devices.items():
            if dev["is_connected"] and dev["n6705c"]:
                try:
                    for ch in range(1, 5):
                        dev["n6705c"].channel_off(ch)
                    logger.info("[%s] All channels off", label)
                except Exception as e:
                    logger.error("[%s] All Off failed: %s", label, e)
        self.output_toggle.setChecked(False)
        self._update_output_visual_state()

    def _on_search(self, label):
        w = self.conn_widgets[label]
        w["status"].setText("Searching...")
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
            seen = {}
            for res in resources:
                try:
                    instr = dev["rm"].open_resource(res, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    if "N6705C" in idn:
                        parts = idn.split(",")
                        serial = parts[2].strip() if len(parts) > 2 else res
                        if serial in seen:
                            if "hislip" in res and "hislip" not in seen[serial]:
                                seen[serial] = res
                        else:
                            seen[serial] = res
                except Exception:
                    pass

            found = list(seen.values())
            w["combo"].clear()
            if found:
                for d in found:
                    w["combo"].addItem(d)
                w["status"].setText(f"Found {len(found)} N6705C")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
            else:
                w["combo"].addItem("No N6705C found")
                w["status"].setText("No N6705C found")
                w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
        except Exception as e:
            w["status"].setText(f"Search failed")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            logger.error("[%s] Search error: %s", label, e)
        finally:
            w["search_btn"].setEnabled(True)

    def _on_toggle_connection(self, label):
        if self.devices[label]["is_connected"]:
            self._disconnect(label)
        else:
            self._connect(label)

    def _connect(self, label):
        w = self.conn_widgets[label]
        w["status"].setText("Connecting...")
        w["status"].setStyleSheet("color: #ff9800; font-weight:bold;")
        w["toggle_conn_btn"].setEnabled(False)

        try:
            address = w["combo"].currentText()
            n6705c = N6705C(address)
            idn = n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self.devices[label]["n6705c"] = n6705c
                self.devices[label]["is_connected"] = True

                if self._top:
                    idn_parts = idn.strip().split(",")
                    serial = idn_parts[2].strip() if len(idn_parts) >= 3 else ""
                    connect_fn = getattr(self._top, f"connect_{label.lower()}", None)
                    if connect_fn:
                        connect_fn(address, n6705c_instance=n6705c, serial=serial)

                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                w["toggle_conn_btn"].setText("Disconnect")
                w["toggle_conn_btn"].setStyleSheet(_disconnect_button_style())
                self._update_ui_connection_state(label, True)
                self.connection_status_changed.emit(True)

                if label == self.current_device:
                    self._start_channel_sync()
            else:
                w["status"].setText("Device mismatch")
                w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
        except Exception as e:
            w["status"].setText("Connection failed")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            logger.error("[%s] Connect error: %s", label, e)
        finally:
            w["toggle_conn_btn"].setEnabled(True)

    def _disconnect(self, label):
        w = self.conn_widgets[label]
        try:
            if self._top:
                disconnect_fn = getattr(self._top, f"disconnect_{label.lower()}", None)
                if disconnect_fn:
                    disconnect_fn()
            else:
                n6705c = self.devices[label]["n6705c"]
                if n6705c:
                    n6705c.disconnect()

            self.devices[label]["n6705c"] = None
            self.devices[label]["is_connected"] = False

            w["status"].setText("● Disconnected")
            w["status"].setStyleSheet("color: #8ea6cf; font-weight:bold;")
            w["toggle_conn_btn"].setText("Connect")
            w["toggle_conn_btn"].setStyleSheet(_connect_button_style())
            self._update_ui_connection_state(label, False)
            self.connection_status_changed.emit(False)
        except Exception as e:
            w["status"].setText("Disconnect failed")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            logger.error("[%s] Disconnect error: %s", label, e)

    def _update_ui_connection_state(self, label, connected):
        any_connected = any(d["is_connected"] for d in self.devices.values())

        self.all_on_btn.setEnabled(any_connected)
        self.all_off_btn.setEnabled(any_connected)
        disabled_btn = "QPushButton { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; border-radius: 8px; }"
        self.all_on_btn.setStyleSheet(_neon_on_button_style() if any_connected else disabled_btn)
        self.all_off_btn.setStyleSheet(_neon_off_button_style() if any_connected else disabled_btn)

        active_dev_connected = self.devices[self.current_device]["is_connected"]

        for btn in self.channel_tab_buttons:
            btn.setEnabled(any_connected)

        self.setting_frame.setEnabled(active_dev_connected)
        if not active_dev_connected:
            self.setting_frame.setStyleSheet("""
                QFrame { background-color: #070f1e; border: 1px solid #0d1a30; border-radius: 14px; }
            """)
        else:
            theme = CHANNEL_THEMES[self.current_channel]
            self.setting_frame.setStyleSheet(f"""
                QFrame {{ background-color: #0a1930; border: 1px solid {theme['accent_border']}; border-radius: 14px; }}
            """)

        for btn in self.mode_buttons:
            btn.setEnabled(active_dev_connected)
        self.output_toggle.setEnabled(active_dev_connected)
        self.measure_btn.setEnabled(active_dev_connected)
        self.set_btn.setEnabled(active_dev_connected)
        self.voltage_set_input.setEnabled(active_dev_connected)
        self.limit_current_value.setEnabled(active_dev_connected)
        self.voltage_value.setEnabled(active_dev_connected)
        self.current_value.setEnabled(active_dev_connected)

        if hasattr(self, 'consumption_test_panel'):
            self.consumption_test_panel.setEnabled(any_connected)
            if any_connected:
                self.consumption_test_panel.setStyleSheet("""
                    QFrame { background-color: #0a1930; border: 1px solid #132849; border-radius: 12px; }
                """)
            else:
                self.consumption_test_panel.setStyleSheet("""
                    QFrame { background-color: #070f1e; border: 1px solid #0d1a30; border-radius: 12px; }
                """)

    def _get_selected_batch_channels(self, dev_label):
        return [ch for dl, ch, cb in self.batch_channel_buttons if dl == dev_label and cb.isChecked()]

    def _on_batch_measure(self):
        for label, dev in self.devices.items():
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            channels = self._get_selected_batch_channels(label)
            for ch in channels:
                try:
                    dev["n6705c"].set_mode(ch, "VMETer")
                    dev["n6705c"].channel_on(ch)
                except Exception as e:
                    logger.error("[%s] CH%d VMeter failed: %s", label, ch, e)

    def _on_batch_set(self):
        for label, dev in self.devices.items():
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            channels = self._get_selected_batch_channels(label)
            voltages = [float(inp.text()) for inp in self.batch_voltage_inputs[label]]
            currents = [float(inp.text()) for inp in self.batch_current_inputs[label]]
            for ch in channels:
                try:
                    idx = ch - 1
                    dev["n6705c"].set_mode(ch, "PS2Q")
                    dev["n6705c"].set_voltage(ch, voltages[idx])
                    dev["n6705c"].set_current_limit(ch, currents[idx])
                    dev["n6705c"].channel_on(ch)
                except Exception as e:
                    logger.error("[%s] CH%d Set failed: %s", label, ch, e)

    def _on_batch_auto(self):
        for label, dev in self.devices.items():
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            channels = self._get_selected_batch_channels(label)
            for ch in channels:
                try:
                    dev["n6705c"].set_mode(ch, "VMETer")
                    v = float(dev["n6705c"].measure_voltage(ch))
                    new_v = v + 0.03
                    dev["n6705c"].set_mode(ch, "PS2Q")
                    dev["n6705c"].set_voltage(ch, new_v)
                    dev["n6705c"].channel_on(ch)
                except Exception as e:
                    logger.error("[%s] CH%d Auto failed: %s", label, ch, e)

    def _ct_start_test(self):
        if self.is_testing:
            return

        any_connected = any(d["is_connected"] for d in self.devices.values())
        if not any_connected:
            return

        try:
            test_time = float(self.ct_test_time_input.text())
            sample_period = float(self.ct_sample_period_input.text())
        except ValueError:
            return

        self.is_testing = True
        self.ct_start_btn.setEnabled(False)
        self.ct_stop_btn.setEnabled(True)

        for key in self.ct_channel_cards:
            self.ct_channel_cards[key]["value_label"].setText("- - -")

        self._test_finished_count = 0
        self._test_expected_count = 0

        for label, dev in self.devices.items():
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            channels = [ch for (dl, ch), card_data in self.ct_channel_cards.items()
                        if dl == label and card_data["checkbox"].isChecked()]
            if not channels:
                continue

            self._test_expected_count += 1
            worker = _ConsumptionTestWorker(dev["n6705c"], label, channels, test_time, sample_period)
            thread = QThread()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.channel_result.connect(self._ct_on_channel_result)
            worker.error.connect(self._ct_on_error)
            worker.finished.connect(thread.quit)
            worker.finished.connect(self._ct_on_one_finished)
            thread.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            self._test_threads[label] = thread
            self._test_workers[label] = worker
            thread.start()

        if self._test_expected_count == 0:
            self.is_testing = False
            self.ct_start_btn.setEnabled(True)
            self.ct_stop_btn.setEnabled(False)

    def _ct_on_channel_result(self, dev_label, ch, avg_current):
        key = (dev_label, ch)
        if key in self.ct_channel_cards:
            self.ct_channel_cards[key]["value_label"].setText(_format_current(avg_current))

    def _ct_on_error(self, err_msg):
        logger.error("Consumption test error: %s", err_msg)

    def _ct_on_one_finished(self):
        self._test_finished_count += 1
        if self._test_finished_count >= self._test_expected_count:
            self.is_testing = False
            self.ct_start_btn.setEnabled(True)
            self.ct_stop_btn.setEnabled(False)
            self._test_threads.clear()
            self._test_workers.clear()

    def _ct_stop_test(self):
        for worker in self._test_workers.values():
            worker.stop()
        self.is_testing = False
        self.ct_start_btn.setEnabled(True)
        self.ct_stop_btn.setEnabled(False)

    def _ct_save_datalog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DataLog", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            logger.info("Saving datalog to: %s", file_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = N6705CDoubleUI()
    win.setWindowTitle("N6705C × 2 DC Power Analyzer")
    win.setGeometry(100, 100, 1400, 900)
    win.show()

    sys.exit(app.exec())