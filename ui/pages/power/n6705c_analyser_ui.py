#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ui.widgets.dark_combobox import DarkComboBox
from ui.styles.button import SpinningSearchButton, update_connect_button_state
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGridLayout, QFrame, QApplication, QCheckBox,
    QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject, QPropertyAnimation, Property, QRectF, QEasingCurve
from PySide6.QtGui import QFont, QPainter, QColor, QPen
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C
from log_config import get_logger

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
        return f"{current_A*1e6:.3f} \u00b5A"
    elif abs_i >= 1e-9:
        return f"{current_A*1e9:.3f} nA"
    else:
        return f"{current_A:.3e} A"


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
            background-color: #111d36; color: #7a8fb5;
            border: 1px solid #1e3050; border-radius: 6px;
            padding: 7px 0px; font-size: 12px; font-weight: 600;
        }
        QPushButton:checked { background-color: #1a2a50; color: #c0d0f0; border: 1px solid #3a5a90; }
        QPushButton:hover { background-color: #182844; }
        QPushButton:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
    """



class _SearchThread(QThread):
    search_result = Signal(str, list)

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self._label = label

    def run(self):
        found = []
        rm = None
        try:
            try:
                rm = pyvisa.ResourceManager()
            except Exception:
                rm = pyvisa.ResourceManager('@ni')
            resources = list(rm.list_resources()) or []
            seen = {}
            for res in resources:
                try:
                    instr = rm.open_resource(res, timeout=1000)
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
        except Exception:
            pass
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass
        self.search_result.emit(self._label, found)


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


class N6705CAnalyserUI(QWidget):
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
        self.channels = []
        self._prev_dual_mode = None

        self._setup_style()
        self._create_layout()

        self._search_threads = {}

        self._apply_channel_theme(self.current_device, self.current_channel)
        self._update_ui_connection_state("A", False)
        self._rebuild_dynamic_sections()

        if self._top:
            self._sync_from_top()

    def _connected_device_labels(self):
        return [label for label, dev in self.devices.items() if dev["is_connected"]]

    def _is_dual_mode(self):
        return len(self._connected_device_labels()) >= 2

    def _rebuild_dynamic_sections(self):
        dual = self._is_dual_mode()
        if dual == self._prev_dual_mode:
            return
        self._prev_dual_mode = dual

        connected = self._connected_device_labels()
        if connected and self.current_device not in connected:
            self.current_device = connected[0]
            self.current_channel = 1

        self._build_channel_tab_buttons()
        self._build_batch_columns()
        self._build_ct_cards()
        self._apply_channel_theme(self.current_device, self.current_channel)

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
                w["status"].setText("\u25cf Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                if visa_res:
                    w["combo"].clear()
                    w["combo"].addItem(visa_res)
                update_connect_button_state(w["toggle_conn_btn"], connected=True)
                self._update_ui_connection_state(label, True)
        self._rebuild_dynamic_sections()
        if self.devices[self.current_device]["is_connected"]:
            self._start_channel_sync()

    def _start_channel_sync(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        if self._sync_thread is not None and self._sync_thread.isRunning():
            return
        worker = _ChannelSyncWorker(dev["n6705c"], self.current_channel)
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
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            width: 0px; height: 0px; border: none;
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

        self.channel_interaction_frame = QFrame()
        self.channel_interaction_frame.setStyleSheet("""
            QFrame#ChannelInteractionFrame {
                background-color: #0a1930;
                border: 1px solid #14305e;
                border-radius: 14px;
            }
        """)
        self.channel_interaction_frame.setObjectName("ChannelInteractionFrame")
        ci_layout = QVBoxLayout(self.channel_interaction_frame)
        ci_layout.setContentsMargins(0, 0, 0, 0)
        ci_layout.setSpacing(0)

        self.channel_tabs = self._create_channel_tabs()
        ci_layout.addWidget(self.channel_tabs)

        self.setting_widget = self._create_setting_widget()
        ci_layout.addWidget(self.setting_widget)

        main_layout.addWidget(self.channel_interaction_frame)
        main_layout.addSpacing(8)

        self.batch_tools_panel = self._create_batch_tools_panel()
        main_layout.addWidget(self.batch_tools_panel)
        main_layout.addSpacing(8)

        self.consumption_test_panel = self._create_consumption_test_panel()
        main_layout.addWidget(self.consumption_test_panel)

        main_layout.addStretch()

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

        icon_label = QLabel("\u26a1")
        icon_label.setStyleSheet("QLabel { color: #00f5c4; font-size: 24px; font-weight: bold; }")
        header_layout.addWidget(icon_label)

        title_label = QLabel("Keysight N6705C DC Power Analyzer")
        title_label.setStyleSheet("QLabel { color: #ffffff; font-size: 18px; font-weight: 800; }")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
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
            "B": "TCPIP0::K-N6705C-03845.local::hislip0::INSTR",
        }

        self.conn_widgets = {}
        for row, (label, color) in enumerate([("A", "#00f5c4"), ("B", "#f2994a")]):
            tag = QLabel(f"  {label}  ")
            tag.setStyleSheet(f"color: {color}; font-weight: 900; font-size: 14px; min-width: 24px;")
            tag.setAlignment(Qt.AlignCenter)

            status = QLabel("\u25cf Disconnected")
            status.setStyleSheet("color:#8ea6cf; font-weight:bold;")

            combo = DarkComboBox(bg="#091426", border="#17345f")
            combo.setMinimumWidth(300)
            combo.addItem(default_addresses[label])

            search_btn = SpinningSearchButton()

            toggle_conn_btn = QPushButton()
            update_connect_button_state(toggle_conn_btn, connected=False)
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
        tab_wrap.setStyleSheet("""
            QWidget {
                background-color: #0c1628;
                border: none;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
        """)

        self._channel_tabs_layout = QHBoxLayout(tab_wrap)
        self._channel_tabs_layout.setContentsMargins(0, 0, 0, 0)
        self._channel_tabs_layout.setSpacing(0)

        self.channel_tab_buttons = []
        self._channel_tab_separator = None
        self._build_channel_tab_buttons()

        return tab_wrap

    def _build_channel_tab_buttons(self):
        for btn in self.channel_tab_buttons:
            self._channel_tabs_layout.removeWidget(btn)
            btn.deleteLater()
        self.channel_tab_buttons.clear()

        if self._channel_tab_separator is not None:
            self._channel_tabs_layout.removeWidget(self._channel_tab_separator)
            self._channel_tab_separator.deleteLater()
            self._channel_tab_separator = None

        while self._channel_tabs_layout.count():
            item = self._channel_tabs_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        dual = self._is_dual_mode()
        if dual:
            for dev_label in ["A", "B"]:
                for ch in range(1, 5):
                    btn = QPushButton(f"\u25cf {dev_label}-CH{ch}")
                    btn.setCheckable(True)
                    btn.setMinimumSize(90, 34)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.clicked.connect(
                        lambda checked=False, d=dev_label, c=ch: self._switch_channel(d, c)
                    )
                    self.channel_tab_buttons.append(btn)
                    self._channel_tabs_layout.addWidget(btn)
                if dev_label == "A":
                    sep = QFrame()
                    sep.setFixedWidth(2)
                    sep.setFixedHeight(24)
                    sep.setStyleSheet("QFrame { background: #1b2847; border: none; }")
                    self._channel_tab_separator = sep
                    self._channel_tabs_layout.addWidget(sep)
        else:
            for ch in range(1, 5):
                btn = QPushButton(f"\u25cf CH{ch}")
                btn.setCheckable(True)
                btn.setMinimumSize(90, 34)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(
                    lambda checked=False, c=ch: self._switch_channel(self._get_single_device_label(), c)
                )
                self.channel_tab_buttons.append(btn)
                self._channel_tabs_layout.addWidget(btn)

        self._channel_tabs_layout.addStretch()

        if self.channel_tab_buttons:
            self.channel_tab_buttons[0].setChecked(True)
        self._refresh_channel_tab_styles()

    def _get_single_device_label(self):
        connected = self._connected_device_labels()
        if connected:
            return connected[0]
        return "A"

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
            QFrame {
                background-color: #0a1930;
                border: none;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
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
        self.batch_collapsed = False

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.batch_toggle_btn = QPushButton("\u25bc  Quick Setup")
        self.batch_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a1930; color: #b8d0f0;
                border: 1px solid #132849; border-bottom: none;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
                border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
                padding: 8px 16px; font-size: 12px; font-weight: 700;
                text-align: left;
            }
            QPushButton:hover { background-color: #0e1f3d; color: #d0e4ff; }
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
        self.batch_content.setVisible(True)

        content_layout = QVBoxLayout(self.batch_content)
        content_layout.setContentsMargins(16, 10, 16, 14)
        content_layout.setSpacing(12)

        self.batch_channel_buttons = []
        self.batch_voltage_inputs = {}
        self.batch_current_inputs = {}

        self._batch_columns_widget = QWidget()
        self._batch_columns_widget.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._batch_columns_layout = QHBoxLayout(self._batch_columns_widget)
        self._batch_columns_layout.setContentsMargins(0, 0, 0, 0)
        self._batch_columns_layout.setSpacing(12)
        content_layout.addWidget(self._batch_columns_widget)

        self._build_batch_columns()

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #132849; border: none;")
        content_layout.addWidget(sep)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self._batch_measure_btn = QPushButton("⚡ Measure")
        self._batch_set_btn = QPushButton("⚙ Set")
        self._batch_auto_btn = QPushButton("▷ Auto Set")
        self._batch_auto_20mv_btn = QPushButton("▷ Auto Set(+20mV)")

        _batch_btn_base = """
            QPushButton {{
                background-color: {bg}; color: {fg};
                border: 1px solid {border}; border-radius: 8px;
                padding: 9px 18px; font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; color: {hover_fg}; border: 1px solid {hover_border}; }}
            QPushButton:disabled {{ background-color: #0D1734; color: #3a4a6a; border: 1px solid #18264A; }}
        """

        self._batch_measure_btn.setStyleSheet(_batch_btn_base.format(
            bg="#0c1a38", fg="#8eb4e8", border="#23417a",
            hover_bg="#122448", hover_fg="#b8d4ff", hover_border="#3a6cc8"
        ))
        self._batch_set_btn.setStyleSheet(_batch_btn_base.format(
            bg="#0c1a38", fg="#8eb4e8", border="#23417a",
            hover_bg="#122448", hover_fg="#b8d4ff", hover_border="#3a6cc8"
        ))
        _batch_auto_style = """
            QPushButton {
                background-color: #4318d9; color: #ffffff;
                border: 1px solid #5a2ef0; border-radius: 8px;
                padding: 9px 24px; font-size: 12px; font-weight: 700;
            }
            QPushButton:hover { background-color: #5628f0; color: #ffffff; border: 1px solid #7040ff; }
            QPushButton:disabled { background-color: #1a1040; color: #4a3a7a; border: 1px solid #2a1860; }
        """
        self._batch_auto_btn.setStyleSheet(_batch_auto_style)
        self._batch_auto_20mv_btn.setStyleSheet(_batch_auto_style)

        buttons_layout.addWidget(self._batch_measure_btn, 1)
        buttons_layout.addWidget(self._batch_set_btn, 1)
        buttons_layout.addWidget(self._batch_auto_btn, 1)
        buttons_layout.addWidget(self._batch_auto_20mv_btn, 1)

        self._batch_measure_btn.clicked.connect(self._on_batch_measure)
        self._batch_set_btn.clicked.connect(self._on_batch_set)
        self._batch_auto_btn.clicked.connect(self._on_batch_auto_set)
        self._batch_auto_20mv_btn.clicked.connect(self._on_batch_auto_20mv)

        content_layout.addLayout(buttons_layout)

        outer_layout.addWidget(self.batch_content)
        return outer

    def _toggle_batch_panel(self):
        self.batch_collapsed = not self.batch_collapsed
        self.batch_content.setVisible(not self.batch_collapsed)
        if self.batch_collapsed:
            self.batch_toggle_btn.setText("\u25b6  Quick Setup")
            self.batch_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930; color: #8ea6cf;
                    border: 1px solid #132849; border-radius: 8px;
                    padding: 8px 16px; font-size: 12px; font-weight: 700; text-align: left;
                }
                QPushButton:hover { background-color: #0e1f3d; color: #b8d0f0; }
            """)
        else:
            self.batch_toggle_btn.setText("\u25bc  Quick Setup")
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

    def _build_batch_columns(self):
        for i in reversed(range(self._batch_columns_layout.count())):
            item = self._batch_columns_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        self.batch_channel_buttons.clear()
        self.batch_voltage_inputs.clear()
        self.batch_current_inputs.clear()

        _label_style = "font-size: 12px; color: #6680aa; font-weight: 600; border: none; background: transparent;"
        _input_style = """
            QLineEdit {
                background-color: #111d36; color: #8899bb;
                border: 1px solid #1e3050; border-radius: 6px;
                padding: 7px 10px; font-size: 12px; font-weight: 600;
                text-align: center;
            }
            QLineEdit:focus { border: 1px solid #3a5a90; color: #b0c0e0; }
            QLineEdit:disabled { background-color: #0b1730; color: #4a5a7a; border: 1px solid #1b2847; }
        """

        dual = self._is_dual_mode()
        if dual:
            device_list = [("A", "#00f5c4"), ("B", "#f2994a")]
        else:
            single_label = self._get_single_device_label()
            device_list = [(single_label, "#00f5c4")]

        for dev_label, dev_color in device_list:
            dev_frame = QFrame()
            dev_frame.setStyleSheet("""
                QFrame {
                    background-color: #0b1b34;
                    border: 1px solid #102746;
                    border-radius: 10px;
                }
            """)
            grid = QGridLayout(dev_frame)
            grid.setContentsMargins(10, 8, 10, 8)
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(8)

            row = 0
            if dual:
                col_title = QLabel(f"Device {dev_label}")
                col_title.setStyleSheet(f"color: {dev_color}; font-weight: 800; font-size: 13px; border: none; background: transparent;")
                grid.addWidget(col_title, row, 0, 1, 5)
                row += 1

            ch_label = QLabel("通道选择")
            ch_label.setStyleSheet(_label_style)
            ch_label.setFixedWidth(70)
            grid.addWidget(ch_label, row, 0)
            for col_idx, ch_idx in enumerate(range(1, 5)):
                cb = QPushButton(f"CH {ch_idx}")
                cb.setCheckable(True)
                if ch_idx in [2, 3, 4]:
                    cb.setChecked(True)
                cb.setStyleSheet(_batch_channel_button_style())
                self.batch_channel_buttons.append((dev_label, ch_idx, cb))
                grid.addWidget(cb, row, col_idx + 1)
            row += 1

            v_label = QLabel("电压 (V)")
            v_label.setStyleSheet(_label_style)
            v_label.setFixedWidth(70)
            grid.addWidget(v_label, row, 0)
            self.batch_voltage_inputs[dev_label] = []
            for col_idx, v in enumerate([3.8, 0.8, 1.2, 1.8]):
                inp = QLineEdit(f"{v:.4f}")
                inp.setAlignment(Qt.AlignCenter)
                inp.setStyleSheet(_input_style)
                self.batch_voltage_inputs[dev_label].append(inp)
                grid.addWidget(inp, row, col_idx + 1)
            row += 1

            c_label = QLabel("限流 (A)")
            c_label.setStyleSheet(_label_style)
            c_label.setFixedWidth(70)
            grid.addWidget(c_label, row, 0)
            self.batch_current_inputs[dev_label] = []
            for col_idx, c in enumerate([0.2, 0.02, 0.02, 0.02]):
                inp = QLineEdit(f"{c:.4f}")
                inp.setAlignment(Qt.AlignCenter)
                inp.setStyleSheet(_input_style)
                self.batch_current_inputs[dev_label].append(inp)
                grid.addWidget(inp, row, col_idx + 1)

            for col in range(1, 5):
                grid.setColumnStretch(col, 1)

            self._batch_columns_layout.addWidget(dev_frame, 1)

    def _create_consumption_test_panel(self):
        self.ct_collapsed = True

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.ct_toggle_btn = QPushButton("\u25b6  Current Consumption Test")
        self.ct_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a1930; color: #8ea6cf;
                border: 1px solid #132849; border-radius: 8px;
                padding: 8px 16px; font-size: 12px; font-weight: 700;
                text-align: left;
            }
            QPushButton:hover { background-color: #0e1f3d; color: #b8d0f0; }
        """)
        self.ct_toggle_btn.clicked.connect(self._toggle_ct_panel)
        outer_layout.addWidget(self.ct_toggle_btn)

        self.ct_content = QFrame()
        self.ct_content.setStyleSheet("""
            QFrame {
                background-color: #0a1930;
                border: 1px solid #132849;
                border-top: none;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        self.ct_content.setVisible(False)

        layout = QVBoxLayout(self.ct_content)
        layout.setContentsMargins(16, 10, 16, 14)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        header_row.addStretch()

        self.ct_save_btn = QPushButton("\U0001f4be Save DataLog")
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

        self.ct_start_btn = QPushButton("\u25b6  START TEST")
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

        self.ct_stop_btn = QPushButton("\u25a0  STOP")
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

        self._ct_cards_widget = QWidget()
        self._ct_cards_widget.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._ct_cards_layout = QHBoxLayout(self._ct_cards_widget)
        self._ct_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._ct_cards_layout.setSpacing(12)
        self.ct_channel_cards = {}
        self._build_ct_cards()
        layout.addWidget(self._ct_cards_widget, 1)

        self.ct_start_btn.clicked.connect(self._ct_start_test)
        self.ct_stop_btn.clicked.connect(self._ct_stop_test)
        self.ct_save_btn.clicked.connect(self._ct_save_datalog)

        outer_layout.addWidget(self.ct_content)
        return outer

    def _toggle_ct_panel(self):
        self.ct_collapsed = not self.ct_collapsed
        self.ct_content.setVisible(not self.ct_collapsed)
        if self.ct_collapsed:
            self.ct_toggle_btn.setText("\u25b6  Current Consumption Test")
            self.ct_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930; color: #8ea6cf;
                    border: 1px solid #132849; border-radius: 8px;
                    padding: 8px 16px; font-size: 12px; font-weight: 700; text-align: left;
                }
                QPushButton:hover { background-color: #0e1f3d; color: #b8d0f0; }
            """)
        else:
            self.ct_toggle_btn.setText("\u25bc  Current Consumption Test")
            self.ct_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930; color: #b8d0f0;
                    border: 1px solid #132849; border-bottom: none;
                    border-top-left-radius: 8px; border-top-right-radius: 8px;
                    border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
                    padding: 8px 16px; font-size: 12px; font-weight: 700; text-align: left;
                }
                QPushButton:hover { background-color: #0e1f3d; color: #d0e4ff; }
            """)

    def _build_ct_cards(self):
        for i in reversed(range(self._ct_cards_layout.count())):
            item = self._ct_cards_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()
        self.ct_channel_cards.clear()

        dual = self._is_dual_mode()
        if dual:
            for dev_label, dev_color in [("A", "#00f5c4"), ("B", "#f2994a")]:
                dev_frame = QFrame()
                dev_frame.setStyleSheet("""
                    QFrame { background-color: #0b1b34; border: 1px solid #102746; border-radius: 10px; }
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

                self._ct_cards_layout.addWidget(dev_frame, 1)
        else:
            single_label = self._get_single_device_label()
            channels_row = QHBoxLayout()
            channels_row.setSpacing(10)
            ch_container = QWidget()
            ch_container.setStyleSheet("QWidget { background: transparent; border: none; }")
            ch_container_layout = QHBoxLayout(ch_container)
            ch_container_layout.setContentsMargins(0, 0, 0, 0)
            ch_container_layout.setSpacing(10)
            for ch in range(1, 5):
                card = self._create_ct_channel_card(single_label, ch)
                ch_container_layout.addWidget(card, 1)
            self._ct_cards_layout.addWidget(ch_container, 1)

    def _create_ct_channel_card(self, dev_label, ch_num):
        colors = CHANNEL_COLORS[ch_num]
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: {colors['bg']}; border: 1px solid {colors['border']}; border-radius: 10px; }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(100)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        icons = _get_checkmark_path(colors['accent'])
        checkbox = QCheckBox(f"CH {ch_num}")
        checkbox.setChecked(False)
        checkbox.setStyleSheet(f"""
            QCheckBox {{ color: #ffffff; font-size: 13px; font-weight: 700; background: transparent; spacing: 6px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; image: url("{icons['unchecked']}"); }}
            QCheckBox::indicator:checked {{ image: url("{icons['checked']}"); }}
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

    def _build_channel_tab_style(self, dev_label, ch, checked=False, position="middle"):
        theme = CHANNEL_THEMES[ch]
        dual = self._is_dual_mode()
        padding = "5px 12px" if dual else "6px 16px"
        font_size = "11px" if dual else "12px"
        corner = "12px"
        if position == "first":
            radius_str = f"border-top-left-radius: {corner}; border-top-right-radius: 0px; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;"
        elif position == "last":
            radius_str = f"border-top-left-radius: 0px; border-top-right-radius: {corner}; border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;"
        else:
            radius_str = "border-radius: 0px;"
        disabled_part = f"""
            QPushButton:disabled {{
                background-color: #0a1224; color: #3a4a6a;
                border: 1px solid #151f36; {radius_str}
                padding: {padding}; font-size: {font_size}; font-weight: 700;
            }}
        """
        if checked:
            return f"""
            QPushButton {{
                background-color: {theme['accent_soft']}; color: {theme['accent']};
                border: 1px solid {theme['accent_border']}; {radius_str}
                padding: {padding}; font-size: {font_size}; font-weight: 700;
            }}
            {disabled_part}
            """
        else:
            return f"""
            QPushButton {{
                background-color: #0b1730; color: {theme['text_dim']};
                border: 1px solid #1b2847; {radius_str}
                padding: {padding}; font-size: {font_size}; font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #0f1f3a; color: #ffffff;
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
        dual = self._is_dual_mode()
        total = len(self.channel_tab_buttons)
        idx = 0
        if dual:
            for dev_label in ["A", "B"]:
                for ch in range(1, 5):
                    if idx < total:
                        is_active = (dev_label == self.current_device and ch == self.current_channel)
                        if idx == 0:
                            pos = "first"
                        elif idx == total - 1:
                            pos = "last"
                        else:
                            pos = "middle"
                        self.channel_tab_buttons[idx].setStyleSheet(
                            self._build_channel_tab_style(dev_label, ch, is_active, pos)
                        )
                        self.channel_tab_buttons[idx].setChecked(is_active)
                        idx += 1
        else:
            single_label = self._get_single_device_label()
            for ch in range(1, 5):
                if idx < total:
                    is_active = (ch == self.current_channel)
                    if idx == 0:
                        pos = "first"
                    elif idx == total - 1:
                        pos = "last"
                    else:
                        pos = "middle"
                    self.channel_tab_buttons[idx].setStyleSheet(
                        self._build_channel_tab_style(single_label, ch, is_active, pos)
                    )
                    self.channel_tab_buttons[idx].setChecked(is_active)
                    idx += 1

    def _apply_channel_theme(self, dev_label, channel_num):
        theme = CHANNEL_THEMES[channel_num]
        dual = self._is_dual_mode()
        if dual:
            self.channel_title_label.setText(f"{dev_label} - Channel {channel_num}")
        else:
            self.channel_title_label.setText(f"Channel {channel_num}")

        self.setting_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #0a1930;
                border: none;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)

        self.channel_interaction_frame.setStyleSheet(f"""
            QFrame#ChannelInteractionFrame {{
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
            self.voltage_input_container.setStyleSheet(
                "QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }")
            self.current_input_container.setStyleSheet(
                "QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }")
        elif ui_mode == "CC":
            self.voltage_set_label.setText("Lim")
            self.current_set_label.setText("Set")
            self.voltage_set_input.setEnabled(True)
            self.limit_current_value.setEnabled(True)
            self.voltage_input_container.setStyleSheet(
                "QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }")
            self.current_input_container.setStyleSheet(
                "QFrame { background-color: #091426; border: 1px solid #17345f; border-radius: 8px; }")
        else:
            self.voltage_set_label.setText("---")
            self.current_set_label.setText("---")
            self.voltage_set_input.setEnabled(False)
            self.limit_current_value.setEnabled(False)
            self.voltage_input_container.setStyleSheet(
                "QFrame { background-color: #070F28; border: 1px solid #131D3A; border-radius: 8px; }")
            self.current_input_container.setStyleSheet(
                "QFrame { background-color: #070F28; border: 1px solid #131D3A; border-radius: 8px; }")

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

    def update_channel_values(self, dev_label, channel_num, voltage, current, limit_current=None):
        if dev_label == self.current_device and channel_num == self.current_channel:
            self.voltage_value.setText(f"{voltage:.4f}")
            self.current_value.setText(f"{current:.4f}")
            if limit_current is not None:
                self.limit_current_value.setText(f"{limit_current:.4f}")

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

    def get_channel_toggle(self, channel_num):
        if 1 <= channel_num <= 4 and self.channels:
            return self.channels[0]['toggle']
        return None

    def set_all_channels_enabled(self, enabled):
        for channel in self.channels:
            channel['toggle'].setChecked(enabled)

    def _on_search(self, label):
        if label in self._search_threads and self._search_threads[label].isRunning():
            return
        w = self.conn_widgets[label]
        w["status"].setText("Searching...")
        w["status"].setStyleSheet("color: #ff9800; font-weight:bold;")
        w["search_btn"].setEnabled(False)
        w["search_btn"].start_spinning()

        if DEBUG_MOCK:
            QTimer.singleShot(600, lambda: self._on_search_finished(label, ["MOCK::N6705C"]))
            return

        thread = _SearchThread(label, self)
        thread.search_result.connect(self._on_search_finished)
        thread.finished.connect(lambda: self._search_threads.pop(label, None))
        self._search_threads[label] = thread
        thread.start()

    def _on_search_finished(self, label, found):
        w = self.conn_widgets[label]
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
        w["search_btn"].stop_spinning()
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
            if DEBUG_MOCK:
                n6705c = MockN6705C()
                idn_match = True
                serial = "MOCK-" + label
            else:
                n6705c = N6705C(address)
                idn = n6705c.instr.query("*IDN?")
                idn_match = "N6705C" in idn
                idn_parts = idn.strip().split(",") if idn_match else []
                serial = idn_parts[2].strip() if len(idn_parts) >= 3 else ""

            if idn_match:
                self.devices[label]["n6705c"] = n6705c
                self.devices[label]["is_connected"] = True

                if self._top:
                    connect_fn = getattr(self._top, f"connect_{label.lower()}", None)
                    if connect_fn:
                        connect_fn(address, n6705c_instance=n6705c, serial=serial)

                w["status"].setText("\u25cf Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                update_connect_button_state(w["toggle_conn_btn"], connected=True)
                self._update_ui_connection_state(label, True)
                self._rebuild_dynamic_sections()
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

            w["status"].setText("\u25cf Disconnected")
            w["status"].setStyleSheet("color: #8ea6cf; font-weight:bold;")
            update_connect_button_state(w["toggle_conn_btn"], connected=False)
            self._update_ui_connection_state(label, False)
            self._rebuild_dynamic_sections()
            self.connection_status_changed.emit(False)
        except Exception as e:
            w["status"].setText("Disconnect failed")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            logger.error("[%s] Disconnect error: %s", label, e)

    def _update_ui_connection_state(self, label, connected):
        any_connected = any(d["is_connected"] for d in self.devices.values())

        active_dev_connected = self.devices[self.current_device]["is_connected"]

        for btn in self.channel_tab_buttons:
            btn.setEnabled(any_connected)

        self.setting_frame.setEnabled(active_dev_connected)
        if not active_dev_connected:
            self.setting_frame.setStyleSheet("""
                QFrame {
                    background-color: #070f1e;
                    border: none;
                    border-bottom-left-radius: 14px;
                    border-bottom-right-radius: 14px;
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                }
            """)
            self.channel_interaction_frame.setStyleSheet("""
                QFrame#ChannelInteractionFrame {
                    background-color: #070f1e;
                    border: 1px solid #0d1a30;
                    border-radius: 14px;
                }
            """)
        else:
            theme = CHANNEL_THEMES[self.current_channel]
            self.setting_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: #0a1930;
                    border: none;
                    border-bottom-left-radius: 14px;
                    border-bottom-right-radius: 14px;
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                }}
            """)
            self.channel_interaction_frame.setStyleSheet(f"""
                QFrame#ChannelInteractionFrame {{
                    background-color: #0a1930;
                    border: 1px solid {theme['accent_border']};
                    border-radius: 14px;
                }}
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

        if hasattr(self, 'batch_tools_panel'):
            self.batch_content.setEnabled(any_connected)
            self.batch_toggle_btn.setEnabled(any_connected)
            if any_connected:
                self.batch_content.setStyleSheet("""
                    QFrame {
                        background-color: #0a1930;
                        border: 1px solid #132849;
                        border-top: none;
                        border-bottom-left-radius: 12px;
                        border-bottom-right-radius: 12px;
                    }
                """)
            else:
                self.batch_content.setStyleSheet("""
                    QFrame {
                        background-color: #070f1e;
                        border: 1px solid #0d1a30;
                        border-top: none;
                        border-bottom-left-radius: 12px;
                        border-bottom-right-radius: 12px;
                    }
                """)

        if hasattr(self, 'consumption_test_panel'):
            self.ct_content.setEnabled(any_connected)
            self.ct_toggle_btn.setEnabled(any_connected)
            if any_connected:
                self.ct_content.setStyleSheet("""
                    QFrame {
                        background-color: #0a1930;
                        border: 1px solid #132849;
                        border-top: none;
                        border-bottom-left-radius: 12px;
                        border-bottom-right-radius: 12px;
                    }
                """)
            else:
                self.ct_content.setStyleSheet("""
                    QFrame {
                        background-color: #070f1e;
                        border: 1px solid #0d1a30;
                        border-top: none;
                        border-bottom-left-radius: 12px;
                        border-bottom-right-radius: 12px;
                    }
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
            if label not in self.batch_voltage_inputs:
                continue
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

    def _on_batch_auto_20mv(self):
        self._on_batch_auto_with_offset(0.02)

    _AUTO_SET_SPECIAL_VOLTAGES = [0.625, 0.67, 0.725, 0.78]

    @staticmethod
    def _align_voltage(v, special_values=None):
        if special_values is None:
            special_values = N6705CAnalyserUI._AUTO_SET_SPECIAL_VOLTAGES
        grid_v = round(round(v / 0.05) * 0.05, 4)
        best = grid_v
        best_dist = abs(v - grid_v)
        for sv in special_values:
            dist = abs(v - sv)
            if dist < best_dist:
                best = sv
                best_dist = dist
        return best

    def _on_batch_auto_set(self):
        for label, dev in self.devices.items():
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            channels = self._get_selected_batch_channels(label)
            for ch in channels:
                try:
                    dev["n6705c"].set_mode(ch, "VMETer")
                    v = float(dev["n6705c"].measure_voltage(ch))
                    new_v = self._align_voltage(v)
                    dev["n6705c"].set_mode(ch, "PS2Q")
                    dev["n6705c"].set_voltage(ch, new_v)
                    dev["n6705c"].channel_on(ch)
                except Exception as e:
                    logger.error("[%s] CH%d Auto Set failed: %s", label, ch, e)

    def _on_batch_auto_with_offset(self, offset):
        for label, dev in self.devices.items():
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            channels = self._get_selected_batch_channels(label)
            for ch in channels:
                try:
                    dev["n6705c"].set_mode(ch, "VMETer")
                    v = float(dev["n6705c"].measure_voltage(ch))
                    new_v = v + offset
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

    win = N6705CAnalyserUI()
    win.setWindowTitle("N6705C DC Power Analyzer")
    win.setGeometry(100, 100, 1400, 900)
    win.show()

    sys.exit(app.exec())
