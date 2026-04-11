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
    QSizePolicy, QFileDialog, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject, QPropertyAnimation, Property, QRectF, QEasingCurve
from PySide6.QtGui import QFont, QPainter, QColor, QPen
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from log_config import get_logger
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C

logger = get_logger(__name__)


class SlideToggle(QWidget):
    clicked = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._knob_x = 3.0
        self._accent_color = QColor("#d4a514")
        self._off_bg = QColor("#25314a")
        self._off_border = QColor("#3a4f75")
        self._knob_color = QColor("#ffffff")
        self.setFixedSize(64, 28)
        self.setCursor(Qt.PointingHandCursor)

        self._animation = QPropertyAnimation(self, b"knob_x", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_knob_x(self):
        return self._knob_x

    def _set_knob_x(self, val):
        self._knob_x = val
        self.update()

    knob_x = Property(float, _get_knob_x, _set_knob_x)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        end = self.width() - self.height() + 3.0 if checked else 3.0
        self._animation.stop()
        self._animation.setStartValue(self._knob_x)
        self._animation.setEndValue(end)
        self._animation.start()

    def setAccentColor(self, color_str):
        self._accent_color = QColor(color_str)
        self.update()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            return
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            self.clicked.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2.0
        knob_d = h - 6.0

        disabled = not self.isEnabled()

        if disabled:
            bg = QColor("#161e30")
            border = QColor("#1b2847")
            knob_color = QColor("#3a4a6a")
        elif self._checked:
            bg = self._accent_color
            border = self._accent_color.lighter(120)
            knob_color = self._knob_color
        else:
            bg = self._off_bg
            border = self._off_border
            knob_color = self._knob_color

        p.setPen(QPen(border, 1.0))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)

        font = p.font()
        font.setPixelSize(10)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        if disabled:
            p.setPen(QColor("#3a4a6a"))
            p.drawText(QRectF(knob_d + 6, 0, w - knob_d - 16, h), Qt.AlignVCenter | Qt.AlignRight, "OFF")
        elif self._checked:
            p.setPen(QColor("#111111"))
            p.drawText(QRectF(8, 0, w - knob_d - 10, h), Qt.AlignVCenter | Qt.AlignLeft, "ON")
        else:
            p.setPen(QColor("#8ea6cf"))
            p.drawText(QRectF(knob_d + 6, 0, w - knob_d - 16, h), Qt.AlignVCenter | Qt.AlignRight, "OFF")

        p.setPen(Qt.NoPen)
        p.setBrush(knob_color)
        p.drawEllipse(QRectF(self._knob_x, 3.0, knob_d, knob_d))

        p.end()


class _ChannelSyncWorker(QObject):
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
            data["voltage"] = float(self.n6705c.measure_voltage(self.channel_num))
        except Exception:
            data["voltage"] = None
        try:
            data["current"] = float(self.n6705c.measure_current(self.channel_num))
        except Exception:
            data["current"] = None
        try:
            data["limit_current"] = float(self.n6705c.get_current_limit(self.channel_num))
        except Exception:
            data["limit_current"] = None
        self.result.emit(data)
        self.finished.emit()


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

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._top = n6705c_top
        self.rm = None
        self.instrument = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []
        self.current_channel = 1
        self.is_testing = False
        self._test_thread = None
        self._test_worker = None
        self._sync_thread = None
        self._sync_worker = None
        self._dirty_voltage = False
        self._dirty_current = False

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

        if self._top:
            self._sync_from_top()

    def _sync_from_top(self):
        if not self._top:
            return
        if self._top.is_connected_a and self._top.n6705c_a:
            self.n6705c = self._top.n6705c_a
            self.is_connected = True
            self.connection_status.setText("● Connected")
            self.connection_status.setStyleSheet("color: #00a859; font-weight:bold;")
            self.toggle_conn_btn.setText("Disconnect")
            self.toggle_conn_btn.setStyleSheet(self._disconnect_button_style())
            if self._top.visa_resource_a:
                self.device_combo.clear()
                self.device_combo.addItem(self._top.visa_resource_a)
            self._update_ui_connection_state(True)
            self._start_channel_sync(self.current_channel)
        else:
            self._update_ui_connection_state(False)

    def _start_channel_sync(self, channel_num):
        if not self.is_connected or not self.n6705c:
            return
        if self._sync_thread is not None and self._sync_thread.isRunning():
            return
        worker = _ChannelSyncWorker(self.n6705c, channel_num)
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
            self.update_channel_values(self.current_channel, voltage, current, limit_current)

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
        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #091426;
            border: 1px solid #17345f;
            border-radius: 6px;
            padding: 4px 6px;
            color: #d7e3ff;
        }
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {
            background-color: #070F28;
            border: 1px solid #131D3A;
            color: #4a5a7a;
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
        QPushButton:disabled {
            background-color: #0b1730;
            color: #4a5a7a;
            border: 1px solid #1b2847;
        }
        QCheckBox:disabled {
            color: #4a5a7a;
        }
        """)

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
        header_widget.setStyleSheet("QWidget { background-color: #07111f; border: none; }")
        header_widget.setFixedHeight(54)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(10)

        icon_label = QLabel("⚡")
        icon_label.setStyleSheet("QLabel { color: #00f5c4; font-size: 24px; font-weight: bold; }")
        header_layout.addWidget(icon_label)

        title_label = QLabel("Keysight N6705C DC Power Analyzer")
        title_label.setStyleSheet("QLabel { color: #ffffff; font-size: 18px; font-weight: 800; }")
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
        top_layout = QGridLayout(content_widget)
        top_layout.setContentsMargins(16, 8, 16, 14)
        top_layout.setHorizontalSpacing(10)
        top_layout.setVerticalSpacing(8)

        self.connection_status = QLabel("● Disconnected")
        self.connection_status.setStyleSheet("color:#8ea6cf; font-weight:bold;")

        self.device_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.device_combo.setMinimumWidth(320)
        self.device_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")

        self.search_btn = QPushButton("Search")
        self.toggle_conn_btn = QPushButton("Connect")
        self.toggle_conn_btn.setStyleSheet(self._connect_button_style())

        top_layout.addWidget(QLabel("Status"), 0, 0)
        top_layout.addWidget(self.connection_status, 0, 1)

        top_layout.addWidget(QLabel("Resource"), 1, 0)
        top_layout.addWidget(self.device_combo, 1, 1, 1, 3)
        top_layout.addWidget(self.search_btn, 1, 4)
        top_layout.addWidget(self.toggle_conn_btn, 1, 5)

        self.search_btn.clicked.connect(self._on_search)
        self.toggle_conn_btn.clicked.connect(self._on_toggle_connection)
        self.all_on_btn.clicked.connect(self._on_all_on_clicked)
        self.all_off_btn.clicked.connect(self._on_all_off_clicked)

        outer_layout.addWidget(content_widget)
        return top_frame

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

        self.channels = []
        self.setting_widget = self._create_setting_widget()
        main_layout.addWidget(self.setting_widget, 1)

        self.consumption_test_panel = self._create_consumption_test_panel()
        main_layout.addWidget(self.consumption_test_panel)

    def _create_channel_tabs(self):
        tab_wrap = QWidget()
        tab_wrap.setAttribute(Qt.WA_StyledBackground, True)
        tab_wrap.setStyleSheet("QWidget { background-color: #07111f; border: none; }")

        layout = QHBoxLayout(tab_wrap)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        self.channel_tab_buttons = []
        for i in range(1, 5):
            btn = QPushButton(f"● Channel {i}")
            btn.setCheckable(True)
            btn.setMinimumSize(120, 36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, ch=i: self._switch_channel(ch))
            self.channel_tab_buttons.append(btn)
            layout.addWidget(btn)

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
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                padding: 0px;
            }
            QLineEdit:disabled {
                color: #4a5a7a;
                background: transparent;
                border: none;
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

        setting_header = QHBoxLayout()
        setting_header.setContentsMargins(0, 0, 0, 0)
        setting_header.setSpacing(12)

        self.channel_title_label = QLabel("Channel 1")
        self.channel_title_label.setStyleSheet("""
            QLabel {
                font-size: 16px; font-weight: 800; color: #ffffff;
                padding: 0px; margin: 0px; border: none; background: transparent;
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
            QFrame {
                background-color: #0a1930;
                border: 1px solid #132849;
                border-radius: 12px;
            }
        """)
        params_grid = QGridLayout(params_container)
        params_grid.setContentsMargins(8, 8, 8, 8)
        params_grid.setSpacing(12)

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
        voltage_label.setStyleSheet("QLabel { font-size: 14px; color: #97aed9; border: none; }")
        voltage_layout.addWidget(voltage_label)

        self.voltage_value = QLineEdit("0.0000")
        self.voltage_value.setFrame(False)
        self.voltage_value.setReadOnly(True)
        self.voltage_value.setStyleSheet("""
            QLineEdit {
                font-size: 22px; font-weight: bold; color: #6d83b3;
                background: transparent; border: none; padding: 0px; margin: 0px;
            }
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
        current_label.setStyleSheet("QLabel { font-size: 14px; color: #97aed9; border: none; }")
        current_layout.addWidget(current_label)

        self.current_value = QLineEdit("0.0000")
        self.current_value.setReadOnly(True)
        self.current_value.setStyleSheet("""
            QLineEdit {
                font-size: 22px; font-weight: bold; color: #6d83b3;
                background-color: transparent; border: none; padding: 0px;
            }
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
        self.measure_btn.setStyleSheet(self._outline_action_button_style())
        self.measure_btn.clicked.connect(self._on_measure_button_clicked)

        self.set_btn = QPushButton("SET")
        self.set_btn.setStyleSheet(self._outline_action_button_style())
        self.set_btn.clicked.connect(self._on_set_button_clicked)

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

    def _create_batch_tools_panel(self):
        self.batch_collapsed = True

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        toggle_row.setSpacing(8)

        self.batch_toggle_btn = QPushButton("▶  Quick Setup")
        self.batch_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a1930;
                color: #8ea6cf;
                border: 1px solid #132849;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 700;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #0e1f3d;
                color: #b8d0f0;
            }
        """)
        self.batch_toggle_btn.clicked.connect(self._toggle_batch_panel)
        toggle_row.addWidget(self.batch_toggle_btn)
        outer_layout.addLayout(toggle_row)

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

        channel_select_layout = QHBoxLayout()
        channel_select_layout.setSpacing(10)

        channel_select_label = QLabel("Channels:")
        channel_select_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
        channel_select_layout.addWidget(channel_select_label)

        self.channel_checkboxes = []
        for i in range(1, 5):
            checkbox = QPushButton(f"CH {i}")
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

        voltage_set_label = QLabel("Voltage (V):")
        voltage_set_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
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

        current_limit_label = QLabel("Current Limit (A):")
        current_limit_label.setStyleSheet("font-size: 11px; color: #8ea6cf; border: none;")
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
            btn.setStyleSheet(self._outline_action_button_style())
            buttons_layout.addWidget(btn)

        measure_all_btn.clicked.connect(self._on_measure_all_clicked)
        set_all_btn.clicked.connect(self._on_set_all_clicked)
        auto_btn.clicked.connect(self._on_auto_clicked)

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
                    background-color: #0a1930;
                    color: #8ea6cf;
                    border: 1px solid #132849;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: 700;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #0e1f3d;
                    color: #b8d0f0;
                }
            """)
        else:
            self.batch_toggle_btn.setText("▼  Quick Setup")
            self.batch_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930;
                    color: #b8d0f0;
                    border: 1px solid #132849;
                    border-bottom: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    border-bottom-left-radius: 0px;
                    border-bottom-right-radius: 0px;
                    padding: 8px 16px;
                    font-size: 12px;
                    font-weight: 700;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #0e1f3d;
                    color: #d0e4ff;
                }
            """)

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
            QPushButton:disabled {
                background-color: #0b1730; color: #4a5a7a;
                border: 1px solid #1b2847;
            }
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
            QPushButton:disabled {
                background-color: #0b1730; color: #4a5a7a;
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
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
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
                color: #ffffff; font-size: 13px; font-weight: 700;
                background: transparent; spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px; height: 18px;
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
        avg_label.setStyleSheet("color: #8ea6cf; font-size: 11px; font-weight: 600; border: none;")
        layout.addWidget(avg_label)

        value_label = QLabel("- - -")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['accent']}; font-size: 18px;
                font-weight: 700; letter-spacing: 4px;
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
            self.connection_status.setText("Please connect N6705C first")
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
        logger.error("Consumption test error: %s", err_msg)

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
            logger.info("Saving datalog to: %s", file_path)

    def _neon_on_button_style(self):
        return """
        QPushButton {
            background-color: #062b2b; color: #00f5c4;
            border: 1px solid #00cfa6; border-radius: 8px;
            padding: 8px 18px; min-width: 88px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover { background-color: #0a3a3a; border: 1px solid #00f5c4; color: #3fffd7; }
        QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
        """

    def _neon_off_button_style(self):
        return """
        QPushButton {
            background-color: #2a0a1c; color: #ff4fa3;
            border: 1px solid #d63384; border-radius: 8px;
            padding: 8px 18px; min-width: 88px; font-size: 12px; font-weight: 600;
        }
        QPushButton:hover { background-color: #3a1028; border: 1px solid #ff4fa3; color: #ff7dbd; }
        QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
        """

    def _connect_button_style(self):
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

    def _disconnect_button_style(self):
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

    def _outline_action_button_style(self):
        return """
        QPushButton {
            background-color: #0c1a38;
            color: #8eb4e8;
            border: 1px solid #23417a;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 11px;
            min-width: 88px;
            font-weight: 700;
        }
        QPushButton:hover {
            background-color: #122448;
            color: #b8d4ff;
            border: 1px solid #3a6cc8;
        }
        QPushButton:disabled {
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }
        """

    def _channel_action_button_style(self, accent, accent_hover):
        return f"""
        QPushButton {{
            background-color: #0c1a38;
            color: {accent};
            border: 1px solid {accent};
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 11px;
            min-width: 88px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background-color: #12213f;
            color: {accent_hover};
            border: 1px solid {accent_hover};
        }}
        QPushButton:disabled {{
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }}
        """

    def _dirty_set_button_style(self, accent):
        return f"""
        QPushButton {{
            background-color: {accent};
            color: #111111;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 11px;
            min-width: 88px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background-color: {accent};
        }}
        QPushButton:disabled {{
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }}
        """

    def _batch_channel_button_style(self):
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

    def _build_channel_tab_style(self, ch, checked=False):
        theme = self.channel_themes[ch]
        disabled_part = f"""
            QPushButton:disabled {{
                background-color: #0a1224;
                color: #3a4a6a;
                border: 1px solid #151f36;
                border-radius: 18px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: 700;
            }}
        """
        if checked:
            return f"""
            QPushButton {{
                background-color: {theme['accent_soft']};
                color: {theme['accent']};
                border: 1px solid {theme['accent_border']};
                border-radius: 18px;
                padding: 6px 16px;
                font-size: 12px;
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
                border-radius: 18px;
                padding: 6px 16px;
                font-size: 12px;
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
        theme = self.channel_themes[self.current_channel]
        disabled_part = """
            QPushButton:disabled {
                background-color: transparent;
                color: #3a4a6a;
                border: none;
                padding: 6px 14px;
                font-size: 12px;
                border-radius: 6px;
            }
        """
        if active:
            return f"""
            QPushButton {{
                background-color: {theme['accent']};
                color: #111111;
                border: none;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
                border-radius: 6px;
            }}
            {disabled_part}
            """
        else:
            return f"""
            QPushButton {{
                background-color: transparent;
                color: #7c8aac;
                border: none;
                padding: 6px 14px;
                font-size: 12px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #0f1d35;
                color: #dbe6ff;
            }}
            {disabled_part}
            """

    def _apply_mode_button_styles(self):
        for btn in self.mode_buttons:
            btn.setStyleSheet(self._build_mode_button_style(btn.isChecked()))

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
            theme = self.channel_themes[self.current_channel]
            self.set_btn.setStyleSheet(self._dirty_set_button_style(theme['accent']))
        else:
            theme = self.channel_themes[self.current_channel]
            self.set_btn.setStyleSheet(self._channel_action_button_style(theme['accent'], theme['accent_hover']))

    def _init_ui_elements(self):
        self._update_ui_connection_state(False)

    def _switch_channel(self, channel_num):
        self.current_channel = channel_num
        self._dirty_voltage = False
        self._dirty_current = False
        self._apply_channel_theme(channel_num)
        self._start_channel_sync(channel_num)

    def _sync_channel_mode(self, channel_num):
        if not self.is_connected or not self.n6705c:
            return
        try:
            inst_mode = self.n6705c.get_mode(channel_num)
            ui_mode = self._map_instrument_mode_to_ui_mode(inst_mode)
            for btn in self.mode_buttons:
                btn.setChecked(btn.text() == ui_mode)
            self._apply_mode_button_styles()
            self._update_labels_for_mode(ui_mode)
        except Exception as e:
            logger.error("Failed to get mode for channel %d: %s", channel_num, e)

    def _map_instrument_mode_to_ui_mode(self, inst_mode):
        mapping = {
            "PS2Q": "PS2Q",
            "CCL": "CC",
            "CCLOAD": "CC",
            "CCLoad": "CC",
            "VMET": "VMETer",
            "VMETER": "VMETer",
            "VMETer": "VMETer",
            "AMET": "AMETer",
            "AMETER": "AMETer",
            "AMETer": "AMETer",
        }
        return mapping.get(inst_mode, inst_mode)

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

    def _sync_channel_output_state(self, channel_num):
        if self.is_connected and self.n6705c:
            try:
                is_on = self.n6705c.get_channel_state(channel_num)
                self.output_toggle.setChecked(is_on)
            except Exception as e:
                logger.error("Failed to get channel %d state: %s", channel_num, e)
        self._update_output_visual_state()

    def _update_output_visual_state(self):
        is_on = self.output_toggle.isChecked()
        theme = self.channel_themes[self.current_channel]
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
            QLineEdit {{
                font-size: 22px; font-weight: bold; color: {value_color};
                background: transparent; border: none; padding: 0px; margin: 0px;
            }}
        """)
        self.current_value.setStyleSheet(f"""
            QLineEdit {{
                font-size: 22px; font-weight: bold; color: {value_color};
                background-color: transparent; border: none; padding: 0px;
            }}
        """)

    def _on_mode_button_clicked(self, clicked_button):
        for btn in self.mode_buttons:
            btn.setChecked(btn is clicked_button)
        self._apply_mode_button_styles()

        ui_mode = self._get_current_mode_text()
        self._update_labels_for_mode(ui_mode)

        if self.is_connected and self.n6705c:
            try:
                channel_num = self.current_channel
                inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
                self.n6705c.set_mode(channel_num, inst_mode)
                logger.info("Channel %d mode set to: %s", channel_num, inst_mode)
                self._start_channel_sync(channel_num)
            except Exception as e:
                logger.error("Failed to set mode: %s", e)

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

    def _on_search(self):
        self.connection_status.setText("Searching...")
        self.connection_status.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
        self.search_btn.setEnabled(False)
        self.search_timer.start(100)

    def _search_devices(self):
        if DEBUG_MOCK:
            self.device_combo.clear()
            self.device_combo.setEnabled(True)
            self.device_combo.addItem("MOCK::N6705C")
            self.connection_status.setText("Found Mock N6705C")
            self.connection_status.setStyleSheet("color: #00a859; padding: 10px; font-weight: bold;")
            self.toggle_conn_btn.setEnabled(True)
            self.search_btn.setEnabled(True)
            return
        try:
            if self.rm is None:
                try:
                    self.rm = pyvisa.ResourceManager()
                except Exception:
                    self.rm = pyvisa.ResourceManager('@ni')

            self.available_devices = list(self.rm.list_resources()) or []

            logger.info("Found %d devices", len(self.available_devices))
            for dev in self.available_devices:
                logger.debug("Device address: %s", dev)

            compatible_devices = self.available_devices.copy() if self.available_devices else []
            seen = {}

            for dev in compatible_devices:
                try:
                    instr = self.rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    logger.info("Device %s IDN: %s", dev, idn)
                    if "N6705C" in idn:
                        parts = idn.split(",")
                        serial = parts[2].strip() if len(parts) > 2 else dev
                        if serial in seen:
                            if "hislip" in dev and "hislip" not in seen[serial]:
                                seen[serial] = dev
                        else:
                            seen[serial] = dev
                except Exception as e:
                    logger.error("Failed to query device %s: %s", dev, e)

            n6705c_devices = list(seen.values())

            self.device_combo.clear()
            self.device_combo.setEnabled(True)

            if n6705c_devices:
                for dev in n6705c_devices:
                    self.device_combo.addItem(dev)

                self.connection_status.setText(f"Found {len(n6705c_devices)} N6705C device(s)")
                self.connection_status.setStyleSheet("color: #00a859; padding: 10px; font-weight: bold;")
                self.toggle_conn_btn.setEnabled(True)

                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    self.device_combo.setCurrentText(default_device)
                else:
                    self.device_combo.setCurrentIndex(0)
            else:
                self.device_combo.addItem("No N6705C device found")
                self.device_combo.setEnabled(False)
                self.connection_status.setText("No N6705C device found")
                self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
                self.toggle_conn_btn.setEnabled(False)

        except Exception as e:
            logger.error("Search error: %s", e)
            self.connection_status.setText(f"Search failed: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.toggle_conn_btn.setEnabled(False)
        finally:
            self.search_btn.setEnabled(True)

    def _on_toggle_connection(self):
        if self.is_connected:
            self._on_disconnect()
        else:
            self._on_connect()

    def _update_ui_connection_state(self, connected):
        disabled_btn_style = """
            QPushButton {
                background-color: #0b1730; color: #4a5a7a;
                border: 1px solid #1b2847; border-radius: 8px;
                padding: 6px 18px; font-size: 12px; font-weight: 700;
            }
        """

        self.all_on_btn.setEnabled(connected)
        self.all_off_btn.setEnabled(connected)
        if connected:
            self.all_on_btn.setStyleSheet(self._neon_on_button_style())
            self.all_off_btn.setStyleSheet(self._neon_off_button_style())
        else:
            self.all_on_btn.setStyleSheet(disabled_btn_style)
            self.all_off_btn.setStyleSheet(disabled_btn_style)

        for btn in self.channel_tab_buttons:
            btn.setEnabled(connected)

        self.setting_frame.setEnabled(connected)
        if not connected:
            self.setting_frame.setStyleSheet("""
                QFrame { background-color: #070f1e; border: 1px solid #0d1a30; border-radius: 14px; }
            """)
        else:
            theme = self.channel_themes[self.current_channel]
            self.setting_frame.setStyleSheet(f"""
                QFrame {{ background-color: #0a1930; border: 1px solid {theme['accent_border']}; border-radius: 14px; }}
            """)

        for btn in self.mode_buttons:
            btn.setEnabled(connected)
        self.output_toggle.setEnabled(connected)
        self.measure_btn.setEnabled(connected)
        self.set_btn.setEnabled(connected)
        self.voltage_set_input.setEnabled(connected)
        self.limit_current_value.setEnabled(connected)
        self.voltage_value.setEnabled(connected)
        self.current_value.setEnabled(connected)

        if hasattr(self, 'batch_content'):
            self.batch_content.setEnabled(connected)

        if hasattr(self, 'consumption_test_panel'):
            self.consumption_test_panel.setEnabled(connected)
            if connected:
                self.consumption_test_panel.setStyleSheet("""
                    QFrame { background-color: #0a1930; border: 1px solid #132849; border-radius: 12px; }
                """)
            else:
                self.consumption_test_panel.setStyleSheet("""
                    QFrame { background-color: #070f1e; border: 1px solid #0d1a30; border-radius: 12px; }
                """)

    def _on_connect(self):
        self.connection_status.setText("Connecting...")
        self.connection_status.setStyleSheet("color: #ff9800; font-weight:bold;")
        self.toggle_conn_btn.setEnabled(False)

        try:
            device_address = self.device_combo.currentText()
            if DEBUG_MOCK:
                self.n6705c = MockN6705C()
                serial = "MOCK-A"
                idn_match = True
            else:
                self.n6705c = N6705C(device_address)
                idn = self.n6705c.instr.query("*IDN?")
                idn_match = "N6705C" in idn
                idn_parts = idn.strip().split(",") if idn_match else []
                serial = idn_parts[2].strip() if len(idn_parts) >= 3 else ""

            if idn_match:
                self.is_connected = True
                if self._top:
                    self._top.connect_a(device_address, n6705c_instance=self.n6705c, serial=serial)
                self.connection_status.setText("● Connected")
                self.connection_status.setStyleSheet("color: #00a859; font-weight:bold;")
                self.toggle_conn_btn.setEnabled(True)
                self.toggle_conn_btn.setText("Disconnect")
                self.toggle_conn_btn.setStyleSheet(self._disconnect_button_style())
                self._update_ui_connection_state(True)
                self.connection_status_changed.emit(True)
                self._start_channel_sync(self.current_channel)
            else:
                self.connection_status.setText("Device mismatch")
                self.connection_status.setStyleSheet("color: #e53935; font-weight:bold;")
                self.toggle_conn_btn.setEnabled(True)

        except Exception as e:
            self.connection_status.setText(f"Connection failed: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; font-weight:bold;")
            self.toggle_conn_btn.setEnabled(True)

    def _on_disconnect(self):
        self.connection_status.setText("Disconnecting...")
        self.connection_status.setStyleSheet("color: #ff9800; font-weight:bold;")
        self.toggle_conn_btn.setEnabled(False)

        try:
            if self._top:
                self._top.disconnect_a()
            else:
                if self.n6705c:
                    self.n6705c.disconnect()

            self.instrument = None
            self.n6705c = None
            self.is_connected = False

            self.connection_status.setText("● Disconnected")
            self.connection_status.setStyleSheet("color: #8ea6cf; font-weight:bold;")
            self.toggle_conn_btn.setEnabled(True)
            self.toggle_conn_btn.setText("Connect")
            self.toggle_conn_btn.setStyleSheet(self._connect_button_style())
            self._update_ui_connection_state(False)
            self.connection_status_changed.emit(False)

        except Exception as e:
            self.connection_status.setText(f"Disconnect failed: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; font-weight:bold;")
            self.toggle_conn_btn.setEnabled(True)

    def _on_channel_toggle(self, unused_checked=False, channel_num=None):
        if channel_num is None:
            channel_num = self.current_channel

        if self.is_connected and self.n6705c:
            try:
                self.n6705c.channel_on(channel_num)
                self.output_toggle.setChecked(True)
                logger.info("Channel %d turned on", channel_num)
            except Exception as e:
                logger.error("Failed to turn on channel %d: %s", channel_num, e)
        else:
            self.output_toggle.setChecked(True)

    def _on_off_button_clicked(self):
        channel_num = self.current_channel
        if self.is_connected and self.n6705c:
            try:
                self.n6705c.channel_off(channel_num)
                logger.info("Channel %d turned off", channel_num)
            except Exception as e:
                logger.error("Failed to turn off channel %d: %s", channel_num, e)

        self.output_toggle.setChecked(False)

    def _on_output_toggle_clicked(self, checked):
        channel_num = self.current_channel
        if checked:
            self._on_channel_toggle(True, channel_num)
        else:
            self._on_off_button_clicked()
        self._update_output_visual_state()

    def _on_voltage_input_enter(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            channel_num = self.current_channel
            ui_mode = self._get_current_mode_text()
            value = float(self.voltage_set_input.text())
            if ui_mode == "PS2Q":
                self.n6705c.set_voltage(channel_num, value)
                logger.info("Channel %d voltage set: %sV", channel_num, value)
            elif ui_mode == "CC":
                self.n6705c.set_voltage_limit(channel_num, value)
                logger.info("Channel %d voltage limit set: %sV", channel_num, value)
        except Exception as e:
            logger.error("Voltage set failed: %s", e)

    def _on_current_input_enter(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            channel_num = self.current_channel
            ui_mode = self._get_current_mode_text()
            value = float(self.limit_current_value.text())
            if ui_mode == "PS2Q":
                self.n6705c.set_current_limit(channel_num, value)
                logger.info("Channel %d current limit set: %sA", channel_num, value)
            elif ui_mode == "CC":
                value = -abs(value)
                self.limit_current_value.setText(f"{value:.4f}")
                self.n6705c.set_current(channel_num, value)
                logger.info("Channel %d current set: %sA", channel_num, value)
        except Exception as e:
            logger.error("Current set failed: %s", e)

    def _on_set_button_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            channel_num = self.current_channel
            ui_mode = self._get_current_mode_text()
            inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
            self.n6705c.set_mode(channel_num, inst_mode)

            if ui_mode == "PS2Q":
                voltage_set = float(self.voltage_set_input.text())
                current_limit = float(self.limit_current_value.text())
                self.n6705c.set_voltage(channel_num, voltage_set)
                self.n6705c.set_current_limit(channel_num, current_limit)
                logger.info("Channel %d settings applied - Mode: %s, Voltage: %sV, Current Limit: %sA", channel_num, inst_mode, voltage_set, current_limit)
            elif ui_mode == "CC":
                voltage_limit = float(self.voltage_set_input.text())
                current_set = -abs(float(self.limit_current_value.text()))
                self.limit_current_value.setText(f"{current_set:.4f}")
                self.n6705c.set_voltage_limit(channel_num, voltage_limit)
                self.n6705c.set_current(channel_num, current_set)
                logger.info("Channel %d settings applied - Mode: %s, Voltage Limit: %sV, Current: %sA", channel_num, inst_mode, voltage_limit, current_set)
            else:
                logger.info("Channel %d mode: %s, no voltage/current parameters needed", channel_num, inst_mode)

            self._dirty_voltage = False
            self._dirty_current = False
            self._update_set_button_dirty_state()
        except Exception as e:
            logger.error("Set failed: %s", e)

    def _on_measure_button_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        self._start_channel_sync(self.current_channel)

    def _on_all_on_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            for ch in range(1, 5):
                self.n6705c.channel_on(ch)
            self.output_toggle.setChecked(True)
            self._update_output_visual_state()
            logger.info("All channels turned on")
        except Exception as e:
            logger.error("All On failed: %s", e)

    def _on_all_off_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            for ch in range(1, 5):
                self.n6705c.channel_off(ch)
            self.output_toggle.setChecked(False)
            self._update_output_visual_state()
            logger.info("All channels turned off")
        except Exception as e:
            logger.error("All Off failed: %s", e)

    def _on_measure_all_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            selected_channels = [i + 1 for i, checkbox in enumerate(self.channel_checkboxes) if checkbox.isChecked()]
            if not selected_channels:
                logger.warning("No channels selected")
                return
            for channel_num in selected_channels:
                self.n6705c.set_mode(channel_num, "VMETer")
                self.n6705c.channel_on(channel_num)
                logger.info("Channel %d set to VMeter mode", channel_num)
        except Exception as e:
            logger.error("VMeter mode set failed: %s", e)

    def _on_set_all_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            selected_channels = [i + 1 for i, checkbox in enumerate(self.channel_checkboxes) if checkbox.isChecked()]
            if not selected_channels:
                logger.warning("No channels selected")
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
                logger.info("Channel %d settings applied - Voltage: %sV, Current Limit: %sA", channel_num, voltage, current_limit)
        except Exception as e:
            logger.error("Set failed: %s", e)

    def _on_auto_clicked(self):
        if not self.is_connected or not self.n6705c:
            return
        try:
            selected_channels = [i + 1 for i, checkbox in enumerate(self.channel_checkboxes) if checkbox.isChecked()]
            if not selected_channels:
                logger.warning("No channels selected")
                return

            for channel_num in selected_channels:
                self.n6705c.set_mode(channel_num, "VMETer")
                measured_voltage = float(self.n6705c.measure_voltage(channel_num))
                logger.info("Channel %d measured voltage: %.4fV", channel_num, measured_voltage)

                new_voltage = measured_voltage + 0.03
                logger.info("Channel %d new voltage: %.4fV", channel_num, new_voltage)

                self.n6705c.set_mode(channel_num, "PS2Q")
                self.n6705c.set_voltage(channel_num, new_voltage)
                self.n6705c.channel_on(channel_num)
                logger.info("Channel %d turned on", channel_num)
        except Exception as e:
            logger.error("Auto operation failed: %s", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = N6705CUI()
    win.setWindowTitle("N6705C DC Power Analyzer")
    win.setGeometry(100, 100, 1200, 820)
    win.show()

    sys.exit(app.exec())