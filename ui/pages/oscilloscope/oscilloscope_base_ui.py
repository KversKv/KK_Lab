#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFrame, QSizePolicy,
    QStackedWidget, QApplication, QTextEdit, QMenu, QFileDialog,
    QScrollArea, QGridLayout, QSplitter, QGraphicsOpacityEffect, QLayout
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QThread, QObject,
    QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup,
    QSize, QRect, QPoint, Property
)
from PySide6.QtGui import QFont, QPixmap, QImage, QPainter, QColor, QPen, QIcon
from PySide6.QtSvg import QSvgRenderer
from ui.widgets.dark_combobox import DarkComboBox
from ui.styles import SCROLL_AREA_STYLE
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from instruments.scopes.base import OscilloscopeController
from log_config import get_logger
from debug_config import DEBUG_MOCK

DEBUG_MSO64B_FLAG = True
DEBUG_DSOX4034A_FLAG = True

import os as _os
_CAMERA_SVG_PATH = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))),
    "resources", "icons", "camera.svg"
)


def _render_camera_icon(size: int, color: str) -> QPixmap:
    svg_data = b""
    if _os.path.isfile(_CAMERA_SVG_PATH):
        with open(_CAMERA_SVG_PATH, "r", encoding="utf-8") as f:
            svg_data = f.read().replace('stroke="currentColor"', f'stroke="{color}"').encode("utf-8")
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    if svg_data:
        renderer = QSvgRenderer(svg_data)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
    return pixmap


logger = get_logger(__name__)

CHANNEL_TEXT_COLORS = {
    "#d4a514": "#1A1400",
    "#18b67a": "#001A12",
    "#2f6fed": "#FFFFFF",
    "#d14b72": "#FFFFFF",
    "#7B8CB7": "#081126",
}


class _OscSearchThread(QThread):
    search_result = Signal(list)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self._controller = controller

    def run(self):
        try:
            found = self._controller.search_visa_devices()
        except Exception:
            found = []
        self.search_result.emit(found)


class CaptureLoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.setInterval(30)

    def start(self):
        self._angle = 0
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _rotate(self):
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0, 140))

        cx, cy = self.width() / 2, self.height() / 2
        radius = min(self.width(), self.height()) / 6
        pen = QPen(QColor("#7B7DFF"), 3.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.translate(cx, cy)
        p.rotate(self._angle)
        p.drawArc(int(-radius), int(-radius), int(radius * 2), int(radius * 2), 0, 270 * 16)
        p.resetTransform()

        p.setPen(QColor("#A8BBDB"))
        f = p.font()
        f.setPointSize(10)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.drawText(self.rect().adjusted(0, int(radius + cy / 2 + 10), 0, 0), Qt.AlignHCenter | Qt.AlignTop, "Capturing...")
        p.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)


class TruncatedComboBox(DarkComboBox):
    MAX_DISPLAY_LEN = 32

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumWidth(100)

    def addItem(self, text, userData=None):
        super().addItem(text, userData)
        idx = self.count() - 1
        self.setItemData(idx, text, Qt.ToolTipRole)

    def paintEvent(self, event):
        current = self.currentText()
        if len(current) > self.MAX_DISPLAY_LEN:
            prefix_len = 14
            suffix_len = 14
            display = current[:prefix_len] + "..." + current[-suffix_len:]
            self.lineEdit().setToolTip(current) if self.isEditable() and self.lineEdit() else None
        super().paintEvent(event)


# ---------------------------------------------------------------------------
# TimeScale 序列输入框：支持鼠标滚轮按 1-2-4-10 序列在 ns/us/ms/s 单位间切换
# ---------------------------------------------------------------------------
class CouplingToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._value = "DC"
        self._anim_progress = 0.0

        self._bg_off = QColor("#1A2750")
        self._bg_on = QColor("#1A2750")
        self._knob_color = QColor("#DDE6FF")
        self._text_active = QColor("#F3F6FF")
        self._text_inactive = QColor("#5F77AE")
        self._border_color = QColor("#22376A")

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.setCursor(Qt.PointingHandCursor)

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def value(self):
        return self._value

    def setValue(self, val):
        val = val.upper()
        if val not in ("DC", "AC"):
            return
        if val == self._value:
            return
        self._value = val
        target = 0.0 if val == "DC" else 1.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled.emit(self._value)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = "AC" if self._value == "DC" else "DC"
            self.setValue(new_val)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2

        p.setPen(QPen(self._border_color, 1))
        p.setBrush(self._bg_off)
        p.drawRoundedRect(QRect(0, 0, w, h), radius, radius)

        knob_margin = 3
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_y = knob_margin

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#243760"))
        p.drawRoundedRect(QRect(int(knob_x), int(knob_y), int(knob_w), int(knob_h)),
                          knob_h / 2, knob_h / 2)

        font = p.font()
        font.setWeight(QFont.Bold)
        font.setPointSize(9)
        p.setFont(font)

        left_rect = QRect(0, 0, w // 2, h)
        right_rect = QRect(w // 2, 0, w // 2, h)

        p.setPen(self._text_active if self._anim_progress < 0.5 else self._text_inactive)
        p.drawText(left_rect, Qt.AlignCenter, "DC")

        p.setPen(self._text_active if self._anim_progress >= 0.5 else self._text_inactive)
        p.drawText(right_rect, Qt.AlignCenter, "AC")

        p.end()

    def sizeHint(self):
        return QSize(100, 32)


class TimeScaleEdit(QLineEdit):
    """A QLineEdit that supports mouse wheel to cycle through a
    predefined time-scale sequence (1-2-4-10 pattern across ns/us/ms/s),
    while also allowing arbitrary text input.

    When Enter is pressed, the *returnPressed* signal fires so the
    parent UI can apply the value to the instrument.
    """

    SCALE_SEQUENCE = [
        1e-9, 2e-9, 4e-9, 10e-9, 20e-9, 40e-9, 100e-9, 200e-9, 400e-9,
        1e-6, 2e-6, 4e-6, 10e-6, 20e-6, 40e-6, 100e-6, 200e-6, 400e-6,
        1e-3, 2e-3, 4e-3, 10e-3, 20e-3, 40e-3, 100e-3, 200e-3, 400e-3,
        1.0, 2.0, 4.0, 10.0,
    ]

    _UNIT_MAP = {
        'ns': 1e-9,
        'us': 1e-6,
        'ms': 1e-3,
        's':  1.0,
    }

    _UNIT_SHORT_MAP = {
        'n': 1e-9,
        'u': 1e-6,
        'm': 1e-3,
    }

    _MULT_TO_UNIT = {
        1e-9: 'ns',
        1e-6: 'us',
        1e-3: 'ms',
        1.0:  's',
    }

    def __init__(self, default_text="1us", parent=None):
        super().__init__(default_text, parent)
        self._last_unit_mult = 1e-6
        parsed_mult = self._extract_unit_mult(default_text)
        if parsed_mult is not None:
            self._last_unit_mult = parsed_mult
        self._current_index = self._find_nearest_index(self.parse_to_seconds(default_text))

    def _extract_unit_mult(self, text: str):
        t = text.strip().lower()
        for suffix, mult in sorted(self._UNIT_MAP.items(), key=lambda x: -len(x[0])):
            if t.endswith(suffix):
                num_str = t[:-len(suffix)].strip()
                try:
                    float(num_str)
                    return mult
                except ValueError:
                    return None
        for suffix, mult in sorted(self._UNIT_SHORT_MAP.items(), key=lambda x: -len(x[0])):
            if t.endswith(suffix):
                num_str = t[:-len(suffix)].strip()
                try:
                    float(num_str)
                    return mult
                except ValueError:
                    return None
        return None

    def value_in_seconds(self) -> float:
        text = self.text()
        unit_mult = self._extract_unit_mult(text)
        if unit_mult is not None:
            self._last_unit_mult = unit_mult
        seconds = self.parse_to_seconds(text, fallback_mult=self._last_unit_mult)
        display = self.seconds_to_display(seconds)
        self.blockSignals(True)
        self.setText(display)
        self.blockSignals(False)
        return seconds

    @classmethod
    def parse_to_seconds(cls, text: str, fallback_mult: float = 1e-6) -> float:
        t = text.strip().lower()
        for suffix, mult in sorted(cls._UNIT_MAP.items(), key=lambda x: -len(x[0])):
            if t.endswith(suffix):
                num_str = t[:-len(suffix)].strip()
                try:
                    return float(num_str) * mult
                except ValueError:
                    return 1e-6
        for suffix, mult in sorted(cls._UNIT_SHORT_MAP.items(), key=lambda x: -len(x[0])):
            if t.endswith(suffix):
                num_str = t[:-len(suffix)].strip()
                try:
                    return float(num_str) * mult
                except ValueError:
                    return 1e-6
        try:
            return float(t) * fallback_mult
        except ValueError:
            return 1e-6

    @classmethod
    def seconds_to_display(cls, seconds: float) -> str:
        abs_val = abs(seconds)
        if abs_val < 1e-6:
            val = seconds / 1e-9
            unit = 'ns'
        elif abs_val < 1e-3:
            val = seconds / 1e-6
            unit = 'us'
        elif abs_val < 1.0:
            val = seconds / 1e-3
            unit = 'ms'
        else:
            val = seconds
            unit = 's'
        if val == int(val):
            return f"{int(val)}{unit}"
        return f"{val:g}{unit}"

    def _find_nearest_index(self, seconds: float) -> int:
        best = 0
        best_diff = abs(self.SCALE_SEQUENCE[0] - seconds)
        for i, v in enumerate(self.SCALE_SEQUENCE):
            diff = abs(v - seconds)
            if diff < best_diff:
                best = i
                best_diff = diff
        return best

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            return

        current_seconds = self.parse_to_seconds(self.text(), fallback_mult=self._last_unit_mult)
        self._current_index = self._find_nearest_index(current_seconds)

        if delta > 0:
            self._current_index = min(self._current_index + 1, len(self.SCALE_SEQUENCE) - 1)
        else:
            self._current_index = max(self._current_index - 1, 0)

        new_val = self.SCALE_SEQUENCE[self._current_index]
        display = self.seconds_to_display(new_val)
        self.setText(display)
        unit_mult = self._extract_unit_mult(display)
        if unit_mult is not None:
            self._last_unit_mult = unit_mult
        event.accept()


class MeasurementPollingWorker(QObject):
    results_ready = Signal(list)
    finished = Signal()

    def __init__(self, controller, interval_s=0.5):
        super().__init__()
        self._controller = controller
        self._measurement_items = []
        self._interval_s = interval_s
        self._running = False
        import threading
        self._lock = threading.Lock()

    def update_items(self, items):
        with self._lock:
            self._measurement_items = list(items)

    def set_interval(self, interval_s):
        self._interval_s = interval_s

    def start_polling(self):
        self._running = True
        while self._running:
            with self._lock:
                snapshot = list(self._measurement_items)
            if not snapshot:
                QThread.msleep(int(self._interval_s * 1000))
                continue
            results = []
            for item in snapshot:
                if not self._running:
                    break
                mtype = item["type"]
                channel = item["channel"]
                try:
                    value = self._query_measurement(channel, mtype)
                    results.append({"type": mtype, "channel": channel, "value": value, "error": None})
                except Exception as e:
                    results.append({"type": mtype, "channel": channel, "value": None, "error": str(e)})
            if self._running and results:
                self.results_ready.emit(results)
            if not self._running:
                break
            QThread.msleep(int(self._interval_s * 1000))
        self.finished.emit()

    def stop(self):
        self._running = False

    @property
    def is_running(self):
        return self._running

    def _query_measurement(self, channel, mtype):
        inst = self._controller.instrument
        if inst is None:
            raise RuntimeError("Instrument not connected")
        func_map = {
            "PK2PK": inst.get_channel_pk2pk,
            "FREQUENCY": inst.get_channel_frequency,
            "MEAN": inst.get_channel_mean,
            "VMAX": inst.get_channel_max,
            "VMIN": inst.get_channel_min,
            "RMS": inst.get_channel_rms,
        }
        func = func_map.get(mtype)
        if func is None:
            raise ValueError(f"Unknown measurement type: {mtype}")
        return func(channel)


class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=10):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def spacing(self):
        return self._spacing

    def setSpacing(self, spacing):
        self._spacing = spacing

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        row_height = 0

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._spacing
            if next_x - self._spacing > effective.right() + 1 and row_height > 0:
                x = effective.x()
                y = y + row_height + self._spacing
                next_x = x + item_size.width() + self._spacing
                row_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            row_height = max(row_height, item_size.height())

        return y + row_height - rect.y() + m.bottom()


class OscilloscopeBaseUI(QWidget):

    timebase_apply_requested = Signal()
    connection_changed = Signal()

    INSTRUMENT_TITLE = "Oscilloscope"
    NUM_CHANNELS = 4
    RESOURCE_PLACEHOLDER = "VISA Resource / IP Address"
    TIMESCALE_DEFAULT = "1us"
    TRIGGER_LEVEL_DEFAULT = "1.25"
    CHANNEL_SCALE_DEFAULT = "1"
    CHANNEL_OFFSET_DEFAULT = "0"
    CHANNEL_OFFSET_LABEL = "Offset (V)"
    TRIGGER_SLOPE_OPTIONS = ["POS", "NEG", "EITH"]

    MEASUREMENT_TYPES = ["PK2PK", "FREQUENCY", "MEAN", "VMAX", "VMIN", "RMS"]
    MEASUREMENT_POLL_INTERVAL_S = 0.5

    CHANNEL_COLORS_DEFAULT = {
        1: "#7B8CB7",
        2: "#7B8CB7",
        3: "#7B8CB7",
        4: "#7B8CB7",
    }

    CHANNEL_COLORS_TEKTRONIX = {
        1: "#d4a514",
        2: "#2f6fed",
        3: "#d14b72",
        4: "#18b67a",
    }

    CHANNEL_COLORS_KEYSIGHT = {
        1: "#d4a514",
        2: "#18b67a",
        3: "#2f6fed",
        4: "#d14b72",
    }

    CHANNEL_COLORS = CHANNEL_COLORS_DEFAULT

    _APPLY_BTN_DEFAULT_STYLE = """
        QPushButton#primaryBtn {
            background-color: #3D33A6;
            border: none;
            color: #E8E9FF;
            padding: 10px 18px;
            font-weight: 700;
            border-radius: 10px;
        }
        QPushButton#primaryBtn:hover {
            background-color: #4B40BF;
        }
        QPushButton#primaryBtn:disabled {
            background-color: #1A1540;
            color: #3A4563;
        }
    """

    _APPLY_BTN_DIRTY_STYLE = """
        QPushButton#primaryBtn {
            background-color: #6B30DD;
            border: 2px solid #A06EFF;
            color: #FFFFFF;
            padding: 10px 18px;
            font-weight: 700;
            border-radius: 10px;
        }
        QPushButton#primaryBtn:hover {
            background-color: #7B40EE;
            border: 2px solid #B88AFF;
        }
        QPushButton#primaryBtn:disabled {
            background-color: #1A1540;
            color: #3A4563;
            border: none;
        }
    """

    def __init__(self, mso64b_top=None, parent=None):
        super().__init__(parent)
        self.channels = []
        self.channel_cards = []
        self.channel_tab_buttons = []
        self._selected_channel_index = 0
        self.is_connected = False

        self.mso64b_top = mso64b_top
        self.controller = OscilloscopeController()
        self.controller.set_log_callback(self.append_log)

        self._measurement_items = []
        self._measurement_result_cards = []
        self._polling_thread = None
        self._polling_worker = None

        self._settings_dirty = False
        self._apply_pulse_timer = None

        self._osc_search_thread = None

        self._setup_fonts()
        self._setup_style()
        self._init_layout()
        self._init_ui_elements()
        self._connect_dirty_tracking()

        if self.mso64b_top is not None:
            self.mso64b_top.connection_changed.connect(self._on_mso64b_top_changed)

    def _setup_fonts(self):
        self.base_font = QFont("Segoe UI", 10)
        self.title_font = QFont("Segoe UI", 18, QFont.Bold)
        self.section_font = QFont("Segoe UI", 12, QFont.Bold)
        self.value_font = QFont("Segoe UI", 11)

    def _setup_style(self):
        self.setObjectName("rootWidget")
        self.setStyleSheet("""
            QWidget#rootWidget {
                background-color: #020B2D;
                color: #D6DEF7;
                font-family: "Segoe UI";
                font-size: 10pt;
            }

            QLabel {
                color: #D6DEF7;
                background: transparent;
                border: none;
            }

            QFrame#card {
                background-color: #0B1638;
                border: 1px solid #16254A;
                border-radius: 16px;
            }

            QFrame#innerCard {
                background-color: #06112E;
                border: 1px solid #1A2A54;
                border-radius: 12px;
            }

            QFrame#captureArea {
                background-color: #000000;
                border: 1px solid #1B2E57;
                border-radius: 12px;
            }

            QLabel#pageTitle {
                color: #F3F6FF;
                font-size: 20pt;
                font-weight: 700;
            }

            QLabel#sectionTitle {
                color: #F0F4FF;
                font-size: 12pt;
                font-weight: 700;
            }

            QLabel#subTitle {
                color: #7F96C7;
                font-size: 9pt;
                font-weight: 700;
                letter-spacing: 1px;
            }

            QLabel#mutedText {
                color: #7B8CB7;
            }

            QLabel#statusDot {
                color: #5E719B;
                font-size: 11pt;
            }

            QLineEdit, QComboBox {
                background-color: #091735;
                border: 1px solid #1A2D57;
                border-radius: 8px;
                padding: 8px 10px;
                color: #DDE6FF;
                min-height: 20px;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4C6FFF;
            }

            QLineEdit:disabled, QComboBox:disabled {
                background-color: #070F28;
                border: 1px solid #131D3A;
                color: #3A4563;
            }

            QPushButton {
                background-color: #13244A;
                color: #DDE6FF;
                border: 1px solid #22376A;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #182D5C;
            }

            QPushButton:pressed {
                background-color: #102040;
            }

            QPushButton:disabled {
                background-color: #0D1734;
                color: #5C6B95;
                border: 1px solid #18264A;
            }

            QLabel#statusOk {
                color: #10e7bc;
                font-weight: 700;
                font-size: 10pt;
            }

            QLabel#statusErr {
                color: #ff6b8a;
                font-weight: 700;
                font-size: 10pt;
            }

            QLabel#statusWarn {
                color: #f0b400;
                font-weight: 700;
                font-size: 10pt;
            }

            QPushButton#ghostBtn {
                background-color: #1A2750;
                border: 1px solid #22376A;
                color: #7F96C7;
                padding: 7px 14px;
                border-radius: 8px;
            }

            QPushButton#ghostBtn:hover {
                background-color: #243B6E;
                border: 1px solid #3A5A9F;
                color: #A8BBDB;
            }

            QPushButton#ghostBtn:pressed {
                background-color: #162040;
            }

            QPushButton#ghostBtn:disabled {
                background-color: #0E1628;
                border: 1px solid #151E35;
                color: #3A4563;
            }

            QPushButton#primaryBtn {
                background-color: #3D33A6;
                border: none;
                color: #E8E9FF;
                padding: 10px 18px;
                font-weight: 700;
                border-radius: 10px;
            }

            QPushButton#primaryBtn:hover {
                background-color: #4B40BF;
            }

            QPushButton#primaryBtn:disabled {
                background-color: #1A1540;
                color: #3A4563;
            }

            QPushButton#channelTab {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px 8px;
                color: #5F77AE;
                font-weight: 700;
            }

            QPushButton#channelTab:checked {
                background-color: #d4a514;
                color: #081126;
            }

            QPushButton#channelTab:disabled {
                background-color: transparent;
                color: #3A4563;
            }

            QPushButton#channelTab:checked:disabled {
                background-color: #1A2240;
                color: #3A4563;
            }

            QPushButton#segBtn {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px 8px;
                color: #6E84B5;
                font-weight: 700;
            }

            QPushButton#segBtn:checked {
                background-color: #243760;
                color: #DDE6FF;
            }

            QPushButton#segBtn:disabled {
                background-color: transparent;
                color: #3A4563;
            }

            QPushButton#segBtn:checked:disabled {
                background-color: #131D3A;
                color: #3A4563;
            }

            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
                background: #2A3557;
            }

            QSlider::sub-page:horizontal {
                height: 6px;
                border-radius: 3px;
                background: #6E7A9C;
            }

            QSlider::handle:horizontal {
                background: #9AA6C5;
                border: none;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }

            QFrame#metricCard {
                background-color: #070E28;
                border: 1px solid #263A6A;
                border-radius: 12px;
            }

            QFrame#metricCard:hover {
                border: 1px solid #3A5A9F;
            }

            QLabel#metricTitle {
                color: #8FA4C8;
                font-size: 10pt;
                font-weight: 600;
            }

            QLabel#metricValue {
                color: #A0B0CC;
                font-size: 11pt;
                font-weight: 600;
            }

            QLabel#metricUnit {
                color: #90A7D8;
                font-size: 9pt;
                font-weight: 600;
            }

            QFrame#toggleTrack {
                background-color: #6D5710;
                border-radius: 10px;
            }

            QLabel#toggleKnob {
                background-color: #A0A9C6;
                border-radius: 7px;
                min-width: 14px;
                min-height: 14px;
                max-width: 14px;
                max-height: 14px;
            }

            QFrame#logContainer {
                background-color: #0B1638;
                border: 1px solid #16254A;
                border-radius: 16px;
            }

            QTextEdit#logEdit {
                background-color: #060E28;
                border: 1px solid #1A2A54;
                border-radius: 10px;
                color: #A8BBDB;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 9pt;
                padding: 8px;
            }

            QPushButton#smallActionBtn {
                background-color: #162340;
                border: 1px solid #22376A;
                border-radius: 6px;
                color: #7F96C7;
                padding: 4px 10px;
                font-size: 9pt;
                font-weight: 600;
            }

            QPushButton#smallActionBtn:hover {
                background-color: #1C2D55;
            }

            QPushButton#deleteCardBtn {
                background-color: transparent;
                border: none;
                color: #5E6E8F;
                font-size: 12pt;
                padding: 2px 6px;
                border-radius: 4px;
            }

            QPushButton#deleteCardBtn:hover {
                background-color: #3A0820;
                color: #FF6B8A;
            }

            QPushButton#logToggleBtn {
                background-color: transparent;
                border: 1px solid #22376A;
                border-radius: 6px;
                color: #7F96C7;
                padding: 4px 10px;
                font-size: 9pt;
                font-weight: 600;
            }

            QPushButton#logToggleBtn:hover {
                background-color: #1C2D55;
                color: #A8BBDB;
            }
        """ + SCROLL_AREA_STYLE)

    def _init_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(14)

        root_layout.addLayout(self._create_top_bar())

        content_grid = QGridLayout()
        content_grid.setSpacing(16)
        content_grid.setColumnStretch(0, 75)
        content_grid.setColumnStretch(1, 25)

        self._create_control_row(content_grid)

        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setChildrenCollapsible(True)
        left_splitter.setHandleWidth(6)
        left_splitter.setStyleSheet("""
            QSplitter { background: transparent; border: none; }
            QSplitter::handle { background-color: #16254A; height: 4px; border-radius: 2px; }
            QSplitter::handle:hover { background-color: #4C6FFF; }
        """)

        left_upper_widget = QWidget()
        left_upper_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        left_upper = QVBoxLayout(left_upper_widget)
        left_upper.setContentsMargins(0, 0, 0, 0)
        left_upper.setSpacing(16)
        left_upper.addWidget(self._create_display_card(), 3)
        left_upper.addWidget(self._create_measurements_card(), 1)

        left_splitter.addWidget(left_upper_widget)
        left_splitter.addWidget(self._create_log_card())
        left_splitter.setStretchFactor(0, 4)
        left_splitter.setStretchFactor(1, 1)
        left_splitter.setSizes([600, 120])

        content_grid.addWidget(left_splitter, 1, 0, 2, 1)

        right_upper = QVBoxLayout()
        right_upper.setSpacing(16)
        right_upper.addWidget(self._create_settings_card())
        content_grid.addLayout(right_upper, 1, 1)

        content_grid.addWidget(self._create_quick_function_card(), 2, 1, Qt.AlignTop)

        root_layout.addLayout(content_grid)

    def _create_top_bar(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        icon_label = QLabel("∿")
        icon_label.setStyleSheet("color:#7B7DFF; font-size:20px; font-weight:700;")
        title_row.addWidget(icon_label)

        self.title_label = QLabel(self.INSTRUMENT_TITLE)
        self.title_label.setObjectName("pageTitle")
        title_row.addWidget(self.title_label)
        title_row.addStretch()

        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        title_row.addWidget(self.system_status_label)

        layout.addLayout(title_row)

        self.instrument_info_label = QLabel("")
        self.instrument_info_label.setObjectName("mutedText")
        self.instrument_info_label.setWordWrap(True)
        layout.addWidget(self.instrument_info_label)

        return layout

    def _create_control_row(self, grid):
        self.visa_resource_combo = TruncatedComboBox(bg="#091735", border="#1A2D57")
        self.visa_resource_combo.setFixedHeight(36)
        self.visa_resource_combo.setEditable(True)
        if DEBUG_MOCK:
            self.visa_resource_combo.addItem("192.168.3.27")
        if DEBUG_MSO64B_FLAG:
            self.visa_resource_combo.addItem("192.168.3.27")
        if DEBUG_DSOX4034A_FLAG:
            self.visa_resource_combo.addItem("USB0::0x0957::0x17A4::MY61500152::INSTR")
        if self.visa_resource_combo.isEditable() and self.visa_resource_combo.lineEdit():
            self.visa_resource_combo.lineEdit().setToolTip(self.visa_resource_combo.currentText())
            self.visa_resource_combo.currentTextChanged.connect(
                lambda text: self.visa_resource_combo.lineEdit().setToolTip(text) if self.visa_resource_combo.lineEdit() else None
            )
        grid.addWidget(self.visa_resource_combo, 0, 0)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.search_btn = SpinningSearchButton()
        self.search_btn.setFixedHeight(36)
        self.search_btn.clicked.connect(self._on_search)
        btn_row.addWidget(self.search_btn)

        self.connect_btn = QPushButton()
        update_connect_button_state(self.connect_btn, connected=False)
        self.connect_btn.setFixedHeight(36)
        btn_row.addWidget(self.connect_btn)

        grid.addLayout(btn_row, 0, 1)

    def _create_display_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        _title_cam_icon = QLabel()
        _title_cam_icon.setPixmap(_render_camera_icon(20, "#F0F4FF"))
        _title_cam_icon.setFixedSize(20, 20)
        header.addWidget(_title_cam_icon)
        title = QLabel("Display Capture")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self.capture_btn = QPushButton("  Capture")
        self.capture_btn.setIcon(QIcon(_render_camera_icon(16, "#10e7bc")))
        self.capture_btn.setIconSize(QSize(16, 16))
        self.capture_btn.setObjectName("dynamicConnectBtn")
        self.capture_btn.setProperty("connected", "false")
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #053b38;
                border: 1px solid #08c9a5;
                color: #10e7bc;
                padding: 7px 16px;
                border-radius: 8px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #064744;
                border: 1px solid #19f0c5;
                color: #43f3d0;
            }
            QPushButton:pressed {
                background-color: #042f2d;
            }
            QPushButton:disabled {
                background-color: #0E1628;
                border: 1px solid #151E35;
                color: #3A4563;
            }
        """)
        header.addWidget(self.capture_btn)

        self.invert_btn = QPushButton("◑  Invert")
        self.invert_btn.setCheckable(True)
        self.invert_btn.setChecked(False)
        self.invert_btn.setObjectName("ghostBtn")
        self.invert_btn.setToolTip("Invert screenshot background (white background, black text)")
        self.invert_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A2750;
                border: 1px solid #22376A;
                color: #7F96C7;
                padding: 7px 14px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #243B6E;
                border: 1px solid #3A5A9F;
                color: #A8BBDB;
            }
            QPushButton:checked {
                background-color: #2A1A60;
                border: 1px solid #5B3FBF;
                color: #C4A8FF;
            }
            QPushButton:checked:hover {
                background-color: #351F75;
                border: 1px solid #6E4FD9;
                color: #D8C0FF;
            }
            QPushButton:disabled {
                background-color: #0E1628;
                border: 1px solid #151E35;
                color: #3A4563;
            }
        """)
        header.addWidget(self.invert_btn)

        layout.addLayout(header)

        self.display_placeholder = QFrame()
        self.display_placeholder.setObjectName("captureArea")
        capture_layout = QVBoxLayout(self.display_placeholder)
        capture_layout.setContentsMargins(0, 0, 0, 0)

        self.capture_image_label = QLabel()
        self.capture_image_label.setAlignment(Qt.AlignCenter)
        self.capture_image_label.setStyleSheet("background: transparent;")
        self.capture_image_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.capture_image_label.customContextMenuRequested.connect(self._on_capture_context_menu)
        self.capture_image_label.hide()
        self._current_pixmap = None
        capture_layout.addWidget(self.capture_image_label)

        self.capture_placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.capture_placeholder_widget)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.setSpacing(10)
        placeholder_layout.setAlignment(Qt.AlignCenter)

        camera_icon = QLabel()
        camera_icon.setAlignment(Qt.AlignCenter)
        camera_icon.setPixmap(_render_camera_icon(48, "#22355D"))
        camera_icon.setFixedSize(48, 48)
        placeholder_layout.addWidget(camera_icon, 0, Qt.AlignCenter)

        self.capture_hint_label = QLabel("No screenshot captured")
        self.capture_hint_label.setAlignment(Qt.AlignCenter)
        self.capture_hint_label.setStyleSheet("color: #314A7A; font-size: 11pt;")
        placeholder_layout.addWidget(self.capture_hint_label)

        capture_layout.addWidget(self.capture_placeholder_widget)

        self._capture_overlay = CaptureLoadingOverlay(self.display_placeholder)
        self._capture_overlay.hide()

        self.display_placeholder.setMinimumHeight(220)
        layout.addWidget(self.display_placeholder)

        return card

    def _create_measurements_card(self):
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet("""
            QFrame#card {
                background-color: #0B1638;
                border: 1px solid #263A6A;
                border-radius: 16px;
            }
            QScrollArea#measResultsScroll {
                background: transparent;
                border: none;
            }
            QWidget#measResultsContainer {
                background: transparent;
            }
            QFrame#metricCard {
                background-color: #070E28;
                border: 1px solid #263A6A;
                border-radius: 12px;
            }
            QFrame#metricCard:hover {
                border: 1px solid #3A5A9F;
            }
            QLabel#metricTitle {
                color: #8FA4C8;
                font-size: 10pt;
                font-weight: 600;
            }
            QLabel#metricValue {
                color: #A0B0CC;
                font-size: 11pt;
                font-weight: 600;
            }
            QLabel#metricUnit {
                color: #90A7D8;
                font-size: 9pt;
                font-weight: 600;
            }
            QLabel#sectionTitle {
                color: #F0F4FF;
                font-size: 12pt;
                font-weight: 700;
            }
            QPushButton#deleteCardBtn {
                background-color: transparent;
                border: none;
                color: #5E6E8F;
                font-size: 12pt;
                padding: 2px 6px;
                border-radius: 4px;
            }
            QPushButton#deleteCardBtn:hover {
                background-color: #3A0820;
                color: #FF6B8A;
            }
        """ + SCROLL_AREA_STYLE)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("∿  Measurements")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)

        type_label = QLabel("Type")
        type_label.setStyleSheet("color:#AFC0E8; font-weight:600;")
        add_row.addWidget(type_label)

        self.meas_type_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        self.meas_type_combo.addItems(self.MEASUREMENT_TYPES)
        self.meas_type_combo.setFixedWidth(140)
        add_row.addWidget(self.meas_type_combo)

        src_label = QLabel("Source")
        src_label.setStyleSheet("color:#AFC0E8; font-weight:600;")
        add_row.addWidget(src_label)

        self.meas_source_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        self.meas_source_combo.addItems([f"CH{i+1}" for i in range(self.NUM_CHANNELS)])
        self.meas_source_combo.setFixedWidth(110)
        add_row.addWidget(self.meas_source_combo)

        self.add_meas_btn = QPushButton("+ Add")
        self.add_meas_btn.setObjectName("ghostBtn")
        self.add_meas_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A2750;
                border: 1px solid #3A5A9F;
                color: #7F96C7;
                padding: 7px 14px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #243B6E;
                border: 1px solid #4C6FFF;
                color: #A8BBDB;
            }
            QPushButton:pressed {
                background-color: #162040;
            }
            QPushButton:disabled {
                background-color: #0E1628;
                border: 1px solid #151E35;
                color: #3A4563;
            }
        """)
        self.add_meas_btn.clicked.connect(self._on_add_measurement)
        add_row.addWidget(self.add_meas_btn)

        self.clear_meas_btn = QPushButton("✕  Clear All")
        self.clear_meas_btn.setObjectName("ghostBtn")
        self.clear_meas_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A2750;
                border: 1px solid #3A5A9F;
                color: #7F96C7;
                padding: 7px 14px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #243B6E;
                border: 1px solid #4C6FFF;
                color: #A8BBDB;
            }
            QPushButton:pressed {
                background-color: #162040;
            }
            QPushButton:disabled {
                background-color: #0E1628;
                border: 1px solid #151E35;
                color: #3A4563;
            }
        """)
        self.clear_meas_btn.clicked.connect(self._on_clear_measurements)
        add_row.addWidget(self.clear_meas_btn)

        add_row.addStretch()
        layout.addLayout(add_row)

        self._results_scroll = QScrollArea()
        self._results_scroll.setWidgetResizable(True)
        self._results_scroll.setFrameShape(QFrame.NoFrame)
        self._results_scroll.setObjectName("measResultsScroll")

        self._results_container = QWidget()
        self._results_container.setObjectName("measResultsContainer")
        self._results_flow = FlowLayout(self._results_container, spacing=10)
        self._results_flow.setContentsMargins(0, 0, 0, 0)

        self._results_scroll.setWidget(self._results_container)
        layout.addWidget(self._results_scroll)

        return card

    def _create_metric_card(self, title_text, value_text, unit_text=""):
        logger.debug("[MEAS] _create_metric_card('%s', '%s') enter", title_text, value_text)
        card = QFrame()
        card.setObjectName("metricCard")
        card.setFixedWidth(170)
        card.setMinimumHeight(60)
        logger.debug("[MEAS] QFrame created: %s", card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        title = QLabel(title_text)
        title.setObjectName("metricTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        value_row = QHBoxLayout()
        value_row.setContentsMargins(0, 0, 0, 0)
        value_row.setSpacing(4)
        value_row.setAlignment(Qt.AlignCenter)

        value = QLabel(value_text)
        value.setObjectName("metricValue")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_row.addWidget(value)

        unit = QLabel(unit_text)
        unit.setObjectName("metricUnit")
        unit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        unit.setVisible(bool(unit_text))
        value_row.addWidget(unit)

        layout.addLayout(value_row)

        delete_btn = QPushButton("✕")
        delete_btn.setObjectName("deleteCardBtn")
        delete_btn.setFixedSize(20, 20)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setToolTip("Remove this measurement")
        delete_btn.setVisible(False)
        delete_btn.setParent(card)
        delete_btn.move(card.width() - 22, 2)

        card.title_label = title
        card.value_label = value
        card.unit_label = unit
        card.delete_btn = delete_btn
        card._delete_btn = delete_btn

        original_enter = card.enterEvent
        original_leave = card.leaveEvent

        def _enter(event):
            delete_btn.move(card.width() - 22, 2)
            delete_btn.setVisible(True)
            if original_enter:
                original_enter(event)

        def _leave(event):
            delete_btn.setVisible(False)
            if original_leave:
                original_leave(event)

        card.enterEvent = _enter
        card.leaveEvent = _leave

        logger.debug("[MEAS] _create_metric_card done: %s", card)
        return card

    def _create_settings_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(18)

        title = QLabel("\u2630  Oscilloscope Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        layout.addWidget(self._create_small_section_title("HORIZONTAL"))
        h_box = QVBoxLayout()
        h_box.setSpacing(6)

        h_title = QLabel("TimeScale (s/div)")
        h_title.setStyleSheet("font-weight: 600; color:#B8C7EA;")
        h_box.addWidget(h_title)

        self.timebase_edit = TimeScaleEdit(self.TIMESCALE_DEFAULT)
        self.timebase_edit.setPlaceholderText("e.g. 1us, 400ns, 10ms ...")
        self.timebase_edit.setToolTip("Scroll to adjust timescale, or type value and press Enter")
        h_box.addWidget(self.timebase_edit)

        layout.addLayout(h_box)

        layout.addWidget(self._create_small_section_title("VERTICAL"))

        tab_bar = QFrame()
        tab_bar.setObjectName("innerCard")
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)

        for i in range(self.NUM_CHANNELS):
            btn = QPushButton(f"CH{i+1}")
            btn.setObjectName("channelTab")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, idx=i: self._on_channel_tab_clicked(idx))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.channel_tab_buttons.append(btn)
            tab_layout.addWidget(btn)

        layout.addWidget(tab_bar)

        self.channel_stack = QStackedWidget()
        self.channel_stack.setFrameShape(QFrame.NoFrame)
        self.channel_stack.setStyleSheet("QStackedWidget { background: transparent; border: none; }")
        for i in range(self.NUM_CHANNELS):
            page = self._create_channel_card(i + 1)
            pal = page.palette()
            pal.setColor(page.backgroundRole(), QColor("#0B1638"))
            page.setPalette(pal)
            page.setAutoFillBackground(True)
            self.channel_stack.addWidget(page)
        layout.addWidget(self.channel_stack)

        layout.addSpacing(6)
        layout.addWidget(self._create_small_section_title("TRIGGER"))

        trigger_layout = QVBoxLayout()
        trigger_layout.setSpacing(10)

        trigger_layout.addWidget(self._labeled_widget("Source", self._create_trigger_source()))

        trigger_layout.addWidget(self._labeled_widget("Level (V)", self._create_trigger_level()))

        self.trigger_slope_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        self.trigger_slope_combo.addItems(self.TRIGGER_SLOPE_OPTIONS)
        trigger_layout.addWidget(self._labeled_widget("Slope", self.trigger_slope_combo))

        layout.addLayout(trigger_layout)

        self.apply_btn = QPushButton("Apply Settings to Instrument")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.setMinimumHeight(36)
        layout.addSpacing(6)
        layout.addWidget(self.apply_btn)

        self._apply_opacity_effect = QGraphicsOpacityEffect(self.apply_btn)
        self._apply_opacity_effect.setOpacity(1.0)
        self.apply_btn.setGraphicsEffect(self._apply_opacity_effect)

        self.timebase_edit.returnPressed.connect(self.timebase_apply_requested.emit)

        for btn in self.channel_tab_buttons:
            btn.setChecked(False)
        self._selected_channel_index = 0
        self._switch_channel_card(0)

        return card

    def _create_quick_function_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)

        title = QLabel("⚡  Quick Function")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.all_ch_default_btn = QPushButton("All Channel Set Default")
        self.all_ch_default_btn.setObjectName("ghostBtn")
        self.all_ch_default_btn.clicked.connect(self._on_all_channel_set_default)
        layout.addWidget(self.all_ch_default_btn)

        ripple_row = QHBoxLayout()
        ripple_row.setSpacing(8)

        self.quick_channel_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        self.quick_channel_combo.addItems([f"CH{i+1}" for i in range(self.NUM_CHANNELS)])
        ripple_row.addWidget(self.quick_channel_combo, 1)

        self.ripple_set_btn = QPushButton("RippleSet")
        self.ripple_set_btn.setObjectName("ghostBtn")
        self.ripple_set_btn.clicked.connect(self._on_ripple_set)
        ripple_row.addWidget(self.ripple_set_btn, 1)

        layout.addLayout(ripple_row)

        return card

    def _on_all_channel_set_default(self):
        if not self.controller.is_connected:
            self.append_log("[WARN] Instrument not connected.")
            return

        inst = self.controller.instrument
        try:
            from instruments.scopes.tektronix.mso64b import MSO64B
            from instruments.scopes.keysight.dsox4034a import DSOX4034A

            if not isinstance(inst, (MSO64B, DSOX4034A)):
                self.append_log("[WARN] This function is only available for Tektronix MSO64B / Keysight DSO-X 4034A.")
                return

            self.append_log("[QUICK] Setting all channels to default ripple config...")
            for ch in range(1, self.NUM_CHANNELS + 1):
                inst.set_channel_display(ch, True)
                if hasattr(inst, 'set_channel_bandwidth'):
                    inst.set_channel_bandwidth(ch, '20E+6')
                inst.set_channel_scale(ch, 0.5)
                inst.set_channel_offset(ch, 1.8)
            inst.set_timebase_scale(0.001)
            if hasattr(inst, 'set_timebase_position'):
                inst.set_timebase_position(50 if isinstance(inst, MSO64B) else 0.0)

            for i, channel_data in enumerate(self.channels):
                self.channel_tab_buttons[i].setChecked(True)
                channel_data['scale_edit'].setText("0.5")
                channel_data['offset_edit'].setText("1.8")
            self.timebase_edit.setText("1ms")

            self.append_log("[QUICK] All channels set: ON, BW=20MHz, Scale=500mV/div, Offset=1.8V; TimeScale=1ms/div")
        except Exception as e:
            self.append_log(f"[ERROR] All Channel Set Default failed: {e}")

    def _on_ripple_set(self):
        if not self.controller.is_connected:
            self.append_log("[WARN] Instrument not connected.")
            return

        inst = self.controller.instrument
        try:
            from instruments.scopes.tektronix.mso64b import MSO64B
            from instruments.scopes.keysight.dsox4034a import DSOX4034A

            if not isinstance(inst, (MSO64B, DSOX4034A)):
                self.append_log("[WARN] This function is only available for Tektronix MSO64B / Keysight DSO-X 4034A.")
                return

            ch_text = self.quick_channel_combo.currentText()
            channel = int(ch_text.replace("CH", ""))
            self.append_log(f"[QUICK] Running RippleSet on {ch_text}...")
            inst.set_AutoRipple_test(channel)
            self.append_log(f"[QUICK] RippleSet on {ch_text} completed.")
        except Exception as e:
            self.append_log(f"[ERROR] RippleSet failed: {e}")

    def _create_small_section_title(self, text):
        label = QLabel(text)
        label.setObjectName("subTitle")
        return label

    def _create_trigger_source(self):
        self.trigger_source_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        items = [f"CH{i+1}" for i in range(self.NUM_CHANNELS)] + ["EXT"]
        self.trigger_source_combo.addItems(items)
        return self.trigger_source_combo

    def _create_trigger_level(self):
        self.trigger_level_edit = QLineEdit(self.TRIGGER_LEVEL_DEFAULT)
        return self.trigger_level_edit

    def _labeled_widget(self, label_text, widget):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setStyleSheet("color:#AFC0E8; font-weight:600;")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def _create_channel_card(self, channel_num):
        frame = QFrame()
        frame.setObjectName("innerCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()

        channel_label = QLabel(f"CH{channel_num}")
        channel_label.setStyleSheet(
            f"font-weight: 800; font-size: 12pt; color: {self.CHANNEL_COLORS.get(channel_num, '#DDE6FF')};"
        )
        header.addWidget(channel_label)
        header.addStretch()

        layout.addLayout(header)

        coupling_title = QLabel("Coupling")
        coupling_title.setStyleSheet("color:#AFC0E8; font-weight:600;")
        layout.addWidget(coupling_title)

        coupling_toggle = CouplingToggle()
        layout.addWidget(coupling_toggle)

        channel_data = {
            'channel_label': channel_label,
            'coupling_toggle': coupling_toggle,
        }

        scale_widget = self._labeled_line_edit("Scale (V/div)", self.CHANNEL_SCALE_DEFAULT)
        offset_widget = self._labeled_line_edit(self.CHANNEL_OFFSET_LABEL, self.CHANNEL_OFFSET_DEFAULT)

        layout.addWidget(scale_widget["widget"])
        layout.addWidget(offset_widget["widget"])

        channel_data['scale_edit'] = scale_widget["edit"]
        channel_data['offset_edit'] = offset_widget["edit"]

        self.channels.append(channel_data)
        self.channel_cards.append(frame)
        return frame

    def _labeled_line_edit(self, label_text, default_text):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setStyleSheet("color:#AFC0E8; font-weight:600;")

        edit = QLineEdit(default_text)

        layout.addWidget(label)
        layout.addWidget(edit)

        return {"widget": wrapper, "edit": edit}

    def _switch_channel_card(self, index):
        self._selected_channel_index = index
        self.channel_stack.setCurrentIndex(index)

    def _on_channel_tab_clicked(self, index):
        btn = self.channel_tab_buttons[index]
        was_selected = (self._selected_channel_index == index)

        if btn.isChecked():
            self._switch_channel_card(index)
            if self.is_connected:
                self._apply_channel_display(index + 1, True)
        else:
            if not was_selected:
                btn.setChecked(True)
                self._switch_channel_card(index)
            else:
                if self.is_connected:
                    self._apply_channel_display(index + 1, False)

    def _init_ui_elements(self):
        for channel in self.channels:
            channel['scale_edit'].setText(self.CHANNEL_SCALE_DEFAULT)
            channel['offset_edit'].setText(self.CHANNEL_OFFSET_DEFAULT)

        self.connect_btn.clicked.connect(self._on_connect_toggle)
        self.capture_btn.clicked.connect(self._on_capture)
        self.apply_btn.clicked.connect(self._on_apply_settings)
        self.timebase_apply_requested.connect(self._on_apply_timebase_only)

        for i, ch in enumerate(self.channels):
            ch_num = i + 1
            ch['scale_edit'].returnPressed.connect(
                lambda n=ch_num: self._apply_channel_scale_offset(n)
            )
            ch['offset_edit'].returnPressed.connect(
                lambda n=ch_num: self._apply_channel_scale_offset(n)
            )
            ch['coupling_toggle'].toggled.connect(
                lambda val, n=ch_num: self._apply_channel_coupling(n, val)
            )

        self.trigger_level_edit.returnPressed.connect(self._apply_trigger_immediate)
        self.trigger_source_combo.currentIndexChanged.connect(
            lambda: self._apply_trigger_immediate()
        )
        self.trigger_slope_combo.currentIndexChanged.connect(
            lambda: self._apply_trigger_immediate()
        )

        self._set_interactive_enabled(False)
        self.append_log("[SYSTEM] Ready. Waiting for instrument connection.")

    def _create_log_card(self):
        card = QFrame()
        card.setObjectName("logContainer")
        log_layout = QVBoxLayout(card)
        log_layout.setContentsMargins(18, 12, 18, 12)
        log_layout.setSpacing(8)

        log_header = QHBoxLayout()

        self.log_toggle_btn = QPushButton("▾  Execution Logs")
        self.log_toggle_btn.setObjectName("logToggleBtn")
        self.log_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.log_toggle_btn.clicked.connect(self._toggle_log_panel)
        log_header.addWidget(self.log_toggle_btn)
        log_header.addStretch()

        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("smallActionBtn")
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        log_header.addWidget(self.clear_log_btn)

        log_layout.addLayout(log_header)

        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(60)
        self.log_edit.setMaximumHeight(300)
        self._log_expanded = True
        log_layout.addWidget(self.log_edit)

        return card

    def _toggle_log_panel(self):
        if self._log_expanded:
            self.log_edit.hide()
            self.clear_log_btn.hide()
            self.log_toggle_btn.setText("▸  Execution Logs")
            self._log_expanded = False
        else:
            self.log_edit.show()
            self.clear_log_btn.show()
            self.log_toggle_btn.setText("▾  Execution Logs")
            self._log_expanded = True

    def append_log(self, message):
        self.log_edit.append(message)

    def _on_clear_log(self):
        self.log_edit.clear()

    # ------------------------------------------------------------------
    # Smart Apply: dirty tracking
    # ------------------------------------------------------------------

    def _connect_dirty_tracking(self):
        self.timebase_edit.textChanged.connect(self._mark_settings_dirty)
        self.trigger_level_edit.textChanged.connect(self._mark_settings_dirty)
        self.trigger_source_combo.currentIndexChanged.connect(self._mark_settings_dirty)
        self.trigger_slope_combo.currentIndexChanged.connect(self._mark_settings_dirty)

        for ch in self.channels:
            ch['scale_edit'].textChanged.connect(self._mark_settings_dirty)
            ch['offset_edit'].textChanged.connect(self._mark_settings_dirty)
            ch['coupling_toggle'].toggled.connect(lambda _: self._mark_settings_dirty())

    def _mark_settings_dirty(self):
        if not self._settings_dirty and self.is_connected:
            self._settings_dirty = True
            self.apply_btn.setStyleSheet(self._APPLY_BTN_DIRTY_STYLE)
            self._start_apply_pulse()

    def _clear_settings_dirty(self):
        self._settings_dirty = False
        self.apply_btn.setStyleSheet(self._APPLY_BTN_DEFAULT_STYLE)
        self._stop_apply_pulse()

    def _start_apply_pulse(self):
        if self._apply_pulse_timer is not None:
            return
        self._apply_pulse_timer = QTimer(self)
        self._apply_pulse_dir = -1
        self._apply_pulse_val = 1.0
        self._apply_pulse_timer.timeout.connect(self._apply_pulse_step)
        self._apply_pulse_timer.start(50)

    def _stop_apply_pulse(self):
        if self._apply_pulse_timer is not None:
            self._apply_pulse_timer.stop()
            self._apply_pulse_timer = None
        self._apply_opacity_effect.setOpacity(1.0)

    def _apply_pulse_step(self):
        self._apply_pulse_val += self._apply_pulse_dir * 0.02
        if self._apply_pulse_val <= 0.55:
            self._apply_pulse_dir = 1
        elif self._apply_pulse_val >= 1.0:
            self._apply_pulse_dir = -1
        self._apply_opacity_effect.setOpacity(self._apply_pulse_val)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_connection_info(self):
        return {
            'resource': self.visa_resource_combo.currentText()
        }

    def get_channel_settings(self, channel_num):
        if 1 <= channel_num <= self.NUM_CHANNELS:
            channel = self.channels[channel_num - 1]
            coupling = channel['coupling_toggle'].value()

            btn = self.channel_tab_buttons[channel_num - 1]
            result = {
                'enabled': btn.isChecked(),
                'scale': float(channel['scale_edit'].text()),
                'offset': float(channel['offset_edit'].text()),
                'coupling': coupling,
            }

            return result
        return None

    def get_trigger_settings(self):
        return {
            'source': self.trigger_source_combo.currentText(),
            'level': float(self.trigger_level_edit.text()),
            'slope': self.trigger_slope_combo.currentText(),
        }

    def get_measure_settings(self):
        return {
            'items': list(self._measurement_items),
        }

    def update_measure_result(self, measure_type, channel, value):
        for card_info in self._measurement_result_cards:
            if card_info["type"] == measure_type and card_info["channel"] == channel:
                if value is not None:
                    val_str, unit_str = self._format_measurement_value_split(measure_type, value)
                    card_info["card"].value_label.setText(val_str)
                    card_info["card"].unit_label.setText(unit_str)
                    card_info["card"].unit_label.setVisible(bool(unit_str))
                else:
                    card_info["card"].value_label.setText("ERR")
                    card_info["card"].unit_label.setText("")
                    card_info["card"].unit_label.setVisible(False)
                return

    def update_connection_status(self, connected, instrument_info=None):
        self._update_connect_button_state(connected)
        self._set_interactive_enabled(connected)
        if connected:
            self.search_btn.setEnabled(False)
            text = instrument_info if instrument_info else "Connected"
            self.instrument_info_label.setText(text)
            self.set_system_status("● Connected")
            self.append_log(f"[SYSTEM] Connected: {text}")
            self._sync_channel_states_from_instrument()
            if self._measurement_items:
                self._start_polling()
        else:
            self._stop_polling()
            self.search_btn.setEnabled(True)
            self.instrument_info_label.setText("")
            self.set_system_status("● Ready")
            self._update_channel_colors(self.CHANNEL_COLORS_DEFAULT)
            for btn in self.channel_tab_buttons:
                btn.setChecked(False)
            self.append_log("[SYSTEM] Disconnected.")

    def update_display_image(self, png_bytes: bytes):
        if not png_bytes:
            return
        img = QImage()
        img.loadFromData(png_bytes, "PNG")
        if img.isNull():
            self.append_log("[ERROR] Failed to decode screenshot image.")
            return
        pixmap = QPixmap.fromImage(img)
        self._current_pixmap = pixmap
        scaled = pixmap.scaled(
            self.display_placeholder.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.capture_image_label.setPixmap(scaled)
        self.capture_image_label.show()
        self.capture_placeholder_widget.hide()
        self.append_log("[INFO] Screenshot captured and displayed.")

    def _on_capture_context_menu(self, pos):
        if self._current_pixmap is None:
            return
        menu = QMenu(self)
        copy_action = menu.addAction("📋  Copy to Clipboard")
        save_action = menu.addAction("💾  Save As...")
        action = menu.exec(self.capture_image_label.mapToGlobal(pos))
        if action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self._current_pixmap)
            self.append_log("[INFO] Screenshot copied to clipboard.")
        elif action == save_action:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Screenshot", "screenshot.png",
                "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
            )
            if file_path:
                self._current_pixmap.save(file_path)
                self.append_log(f"[INFO] Screenshot saved to: {file_path}")

    def set_invert_enabled(self, enabled: bool):
        self.invert_btn.setEnabled(enabled)
        if not enabled:
            self.invert_btn.setChecked(False)

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        update_connect_button_state(self.connect_btn, connected)

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Warning" in status or "Searching" in status:
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def _set_interactive_enabled(self, enabled: bool):
        self.capture_btn.setEnabled(enabled)
        self.invert_btn.setEnabled(enabled)
        self.add_meas_btn.setEnabled(enabled)
        self.clear_meas_btn.setEnabled(enabled)
        self.meas_type_combo.setEnabled(enabled)
        self.meas_source_combo.setEnabled(enabled)
        self.apply_btn.setEnabled(enabled)
        self.timebase_edit.setEnabled(enabled)
        self.trigger_source_combo.setEnabled(enabled)
        self.trigger_level_edit.setEnabled(enabled)
        self.trigger_slope_combo.setEnabled(enabled)
        self.all_ch_default_btn.setEnabled(enabled)
        self.ripple_set_btn.setEnabled(enabled)
        self.quick_channel_combo.setEnabled(enabled)

        for btn in self.channel_tab_buttons:
            btn.setEnabled(enabled)

        for channel in self.channels:
            channel['scale_edit'].setEnabled(enabled)
            channel['offset_edit'].setEnabled(enabled)
            channel['coupling_toggle'].setEnabled(enabled)

    def _update_channel_colors(self, color_map: dict):
        self.CHANNEL_COLORS = color_map

        for i, btn in enumerate(self.channel_tab_buttons):
            ch_num = i + 1
            color = color_map.get(ch_num, "#5F77AE")
            text_color = CHANNEL_TEXT_COLORS.get(color, "#081126")
            btn.setStyleSheet(f"""
                QPushButton#channelTab {{
                    background-color: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 8px;
                    color: {color};
                    font-weight: 700;
                }}
                QPushButton#channelTab:checked {{
                    background-color: {color};
                    color: {text_color};
                }}
                QPushButton#channelTab:disabled {{
                    background-color: transparent;
                    color: #3A4563;
                }}
                QPushButton#channelTab:checked:disabled {{
                    background-color: #1A2240;
                    color: #3A4563;
                }}
            """)

        for i, channel_data in enumerate(self.channels):
            ch_num = i + 1
            color = color_map.get(ch_num, "#DDE6FF")
            channel_data['channel_label'].setStyleSheet(
                f"font-weight: 800; font-size: 12pt; color: {color};"
            )

    def _on_search(self):
        if self._osc_search_thread is not None and self._osc_search_thread.isRunning():
            return
        self.set_system_status("● Searching")
        self.append_log("[SYSTEM] Scanning VISA / network resources...")
        self.search_btn.setEnabled(False)
        self.search_btn.start_spinning()

        thread = _OscSearchThread(self.controller, self)
        thread.search_result.connect(self._on_search_finished)
        thread.finished.connect(lambda: setattr(self, '_osc_search_thread', None))
        self._osc_search_thread = thread
        thread.start()

    def _on_search_finished(self, scope_devices):
        self.visa_resource_combo.setEnabled(True)
        self.visa_resource_combo.clear()
        if scope_devices:
            for dev in scope_devices:
                self.visa_resource_combo.addItem(dev)
            count = len(scope_devices)
            self.set_system_status(f"● Found {count} device(s)")
            self.visa_resource_combo.setCurrentIndex(0)
        else:
            self.visa_resource_combo.addItem("No device found")
            self.visa_resource_combo.setEnabled(False)
            self.set_system_status("● No device found", is_error=True)
        self.search_btn.stop_spinning()
        self.search_btn.setEnabled(True)

    def set_title(self, title):
        self.title_label.setText(title)

    # ------------------------------------------------------------------
    # UI Event Handlers → delegate to OscilloscopeController
    # ------------------------------------------------------------------

    def _on_connect_toggle(self):
        if self.is_connected:
            self._disconnect_instrument()
        else:
            self._connect_instrument()

    def _connect_instrument(self):
        resource = self.visa_resource_combo.currentText().strip()
        if not resource or resource == "No device found":
            self.append_log("[ERROR] Please enter a VISA resource or IP address.")
            self.set_system_status("● No resource", is_error=True)
            return

        self.set_system_status("● Connecting")
        self.connect_btn.setEnabled(False)

        try:
            if DEBUG_MOCK:
                from instruments.mock.mock_instruments import MockMSO64B
                mock = MockMSO64B()
                self.controller._instrument = mock
                self.controller._instrument_info = "MOCK,MSO64B,MOCK000,FW1.0"
                info = self.controller._instrument_info
                result = {
                    "info": info,
                    "title": "MSO64B (Mock)",
                    "is_dsox": False,
                    "is_mso64b": True,
                }
            else:
                result = self.controller.connect_instrument(resource)
            self.update_connection_status(True, result["info"])
            self.set_title(result["title"])
            self.set_invert_enabled(result["is_dsox"])

            if result["is_dsox"]:
                self._update_channel_colors(self.CHANNEL_COLORS_KEYSIGHT)
            elif result["is_mso64b"]:
                self._update_channel_colors(self.CHANNEL_COLORS_TEKTRONIX)

            if self.mso64b_top is not None:
                if result["is_mso64b"]:
                    self.mso64b_top.connect_instrument(resource, self.controller.instrument, scope_type="MSO64B")
                elif result["is_dsox"]:
                    self.mso64b_top.connect_instrument(resource, self.controller.instrument, scope_type="DSOX4034A")
            self.connection_changed.emit()
        except Exception as e:
            logger.error("Connect oscilloscope failed: %s", e)
            self.update_connection_status(False)
            self.set_system_status("● Connection failed", is_error=True)
            self.append_log(f"[ERROR] Connection failed: {e}")
            self.connection_changed.emit()
        finally:
            self.connect_btn.setEnabled(True)

    def _disconnect_instrument(self):
        self.set_system_status("● Disconnecting")
        self.connect_btn.setEnabled(False)

        try:
            result = self.controller.disconnect_instrument()

            if self.mso64b_top is not None and self.mso64b_top.is_connected:
                self.mso64b_top.mso64b = None
                self.mso64b_top.is_connected = False
                self.mso64b_top.visa_resource = ""
                self.mso64b_top.scope_type = ""
                self.mso64b_top.connection_changed.emit()

            self.update_connection_status(False)
            self.set_invert_enabled(True)
            self.connection_changed.emit()
        except Exception as e:
            self.set_system_status("● Disconnect failed", is_error=True)
            self.append_log(f"[ERROR] Disconnect failed: {str(e)}")
            self.connection_changed.emit()
        finally:
            self.connect_btn.setEnabled(True)

    def _on_mso64b_top_changed(self):
        if self.mso64b_top is None:
            return
        if self.mso64b_top.is_connected and self.mso64b_top.mso64b:
            if self.controller.is_connected and self.controller.instrument is self.mso64b_top.mso64b:
                return
            self._sync_from_top()
        else:
            if not self.controller.is_connected:
                return
            self.controller._instrument = None
            self.controller._instrument_info = ""
            self.update_connection_status(False)
            self.set_invert_enabled(True)
            self.connection_changed.emit()

    def _sync_from_top(self):
        if self.mso64b_top is None:
            return
        if not self.mso64b_top.is_connected or self.mso64b_top.mso64b is None:
            return
        if self.controller.is_connected:
            return

        from instruments.scopes.keysight.dsox4034a import DSOX4034A
        from instruments.scopes.tektronix.mso64b import MSO64B

        instrument = self.mso64b_top.mso64b
        resource = self.mso64b_top.visa_resource
        scope_type = getattr(self.mso64b_top, 'scope_type', '') or ''

        self.controller._instrument = instrument
        try:
            info = instrument.identify_instrument()
            self.controller._instrument_info = info
        except Exception:
            info = f"{scope_type} Connected"
            self.controller._instrument_info = info

        is_dsox = isinstance(instrument, DSOX4034A)
        is_mso64b = isinstance(instrument, MSO64B)

        self.update_connection_status(True, info)
        title = info.split(",")[1].strip() if "," in info else info
        self.set_title(title)
        self.set_invert_enabled(is_dsox)

        if is_dsox:
            self._update_channel_colors(self.CHANNEL_COLORS_KEYSIGHT)
        elif is_mso64b:
            self._update_channel_colors(self.CHANNEL_COLORS_TEKTRONIX)

        idx = self.visa_resource_combo.findText(resource)
        if idx >= 0:
            self.visa_resource_combo.setCurrentIndex(idx)
        else:
            self.visa_resource_combo.setEditText(resource)

        self.connection_changed.emit()

    def _on_add_measurement(self):
        logger.debug("[MEAS] _on_add_measurement called")
        mtype = self.meas_type_combo.currentText()
        source_text = self.meas_source_combo.currentText()
        logger.debug("[MEAS] selected type=%s, source=%s", mtype, source_text)
        channel = int(source_text.replace("CH", ""))

        for item in self._measurement_items:
            if item["type"] == mtype and item["channel"] == channel:
                self.append_log(f"[WARN] {source_text} {mtype} already added.")
                return

        item = {"type": mtype, "channel": channel}
        self._measurement_items.append(item)
        logger.debug("[MEAS] items count after append: %d", len(self._measurement_items))

        title_text = f"CH{channel}  {mtype}"
        logger.debug("[MEAS] creating metric card: %s", title_text)
        mc = self._create_metric_card(title_text, "– –", "")
        logger.debug("[MEAS] metric card created: %s", mc)

        mc.delete_btn.clicked.connect(lambda checked=False, mt=mtype, ch=channel: self._on_delete_single_measurement(mt, ch))

        logger.debug("[MEAS] adding to flow layout, flow.count=%d", self._results_flow.count())
        self._results_flow.addWidget(mc)
        logger.debug("[MEAS] flow.addWidget done, flow.count=%d", self._results_flow.count())

        self._measurement_result_cards.append({
            "type": mtype,
            "channel": channel,
            "card": mc,
        })
        logger.debug("[MEAS] result_cards count: %d", len(self._measurement_result_cards))

        self.append_log(f"[MEASURE] Added: {source_text} {mtype}")

        if self.is_connected:
            self._sync_polling_items()

        logger.debug("[MEAS] _on_add_measurement finished")

    def _on_delete_single_measurement(self, mtype, channel):
        logger.debug("[MEAS] _on_delete_single_measurement type=%s ch=%d", mtype, channel)
        target_idx = None
        for i, card_info in enumerate(self._measurement_result_cards):
            if card_info["type"] == mtype and card_info["channel"] == channel:
                target_idx = i
                break
        if target_idx is None:
            return

        card_info = self._measurement_result_cards.pop(target_idx)
        w = card_info["card"]
        self._results_flow.removeWidget(w)
        w.setParent(None)
        w.deleteLater()

        self._measurement_items = [
            it for it in self._measurement_items
            if not (it["type"] == mtype and it["channel"] == channel)
        ]

        self._rebuild_measurement_grid()

        if self._polling_worker is not None:
            self._polling_worker.update_items(self._measurement_items)

        self.append_log(f"[MEASURE] Removed: CH{channel} {mtype}")

    def _rebuild_measurement_grid(self):
        for card_info in self._measurement_result_cards:
            w = card_info["card"]
            self._results_flow.removeWidget(w)
        for card_info in self._measurement_result_cards:
            self._results_flow.addWidget(card_info["card"])

    def _on_clear_measurements(self):
        logger.debug("[MEAS] _on_clear_measurements called")
        self._measurement_items.clear()
        self._clear_result_cards()
        if self._polling_worker is not None:
            self._polling_worker.update_items([])
        self.append_log("[MEASURE] All measurements cleared.")
        logger.debug("[MEAS] _on_clear_measurements finished")

    def _clear_result_cards(self):
        logger.debug("[MEAS] _clear_result_cards called, count=%d", len(self._measurement_result_cards))
        for i, card_info in enumerate(self._measurement_result_cards):
            w = card_info["card"]
            logger.debug("[MEAS] removing card %d: %s", i, w)
            self._results_flow.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
        self._measurement_result_cards.clear()
        logger.debug("[MEAS] _clear_result_cards finished")

    def _start_polling(self):
        if not self.is_connected or not self._measurement_items:
            return
        if self._polling_thread is not None and self._polling_thread.isRunning():
            return

        logger.debug("[MEAS] _start_polling: creating worker and thread")
        self._polling_worker = MeasurementPollingWorker(
            self.controller, self.MEASUREMENT_POLL_INTERVAL_S
        )
        self._polling_worker.update_items(self._measurement_items)
        self._polling_thread = QThread()
        self._polling_worker.moveToThread(self._polling_thread)
        self._polling_thread.started.connect(self._polling_worker.start_polling)
        self._polling_worker.results_ready.connect(self._on_polling_results)
        self._polling_worker.finished.connect(self._polling_thread.quit)
        self._polling_thread.finished.connect(self._polling_worker.deleteLater)
        self._polling_thread.finished.connect(self._polling_thread.deleteLater)
        self._polling_thread.finished.connect(self._on_polling_done)
        self._polling_thread.start()
        logger.debug("[MEAS] _start_polling: thread started")

    def _stop_polling(self):
        logger.debug("[MEAS] _stop_polling called")
        if self._polling_worker is not None:
            self._polling_worker.stop()
        if self._polling_thread is not None and self._polling_thread.isRunning():
            logger.debug("[MEAS] _stop_polling: waiting for thread...")
            self._polling_thread.quit()
            self._polling_thread.wait()
            logger.debug("[MEAS] _stop_polling: thread finished")
        self._polling_worker = None
        self._polling_thread = None

    def _sync_polling_items(self):
        logger.debug("[MEAS] _sync_polling_items: items=%d", len(self._measurement_items))
        if self._polling_worker is not None and self._polling_thread is not None and self._polling_thread.isRunning():
            self._polling_worker.update_items(self._measurement_items)
            logger.debug("[MEAS] _sync_polling_items: updated existing worker")
        elif self._measurement_items:
            self._start_polling()

    def _on_polling_done(self):
        logger.debug("[MEAS] _on_polling_done called")
        self._polling_worker = None
        self._polling_thread = None

    def _on_polling_results(self, results):
        for r in results:
            self.update_measure_result(r["type"], r["channel"], r["value"])

    @staticmethod
    def _format_measurement_value(mtype, value):
        val_str, unit_str = OscilloscopeBaseUI._format_measurement_value_split(mtype, value)
        return f"{val_str} {unit_str}"

    @staticmethod
    def _format_measurement_value_split(mtype, value):
        if mtype == "FREQUENCY":
            abs_v = abs(value)
            if abs_v >= 1e9:
                return f"{value / 1e9:.4f}", "GHz"
            elif abs_v >= 1e6:
                return f"{value / 1e6:.4f}", "MHz"
            elif abs_v >= 1e3:
                return f"{value / 1e3:.4f}", "kHz"
            return f"{value:.2f}", "Hz"
        abs_v = abs(value)
        if abs_v >= 1:
            return f"{value:.4f}", "V"
        elif abs_v >= 1e-3:
            return f"{value / 1e-3:.4f}", "mV"
        elif abs_v >= 1e-6:
            return f"{value / 1e-6:.4f}", "µV"
        elif abs_v == 0:
            return "0.0000", "V"
        else:
            return f"{value / 1e-9:.4f}", "nV"

    def _on_capture(self):
        if not self.controller.is_connected:
            self.append_log("[WARN] Instrument not connected.")
            return

        self.capture_btn.setEnabled(False)
        self._capture_overlay.resize(self.display_placeholder.size())
        self._capture_overlay.start()

        try:
            invert_checked = self.invert_btn.isChecked()
            png_data = self.controller.capture_screen(invert=invert_checked)

            if png_data:
                self.update_display_image(png_data)
        except Exception as e:
            self.append_log(f"[ERROR] Screenshot capture failed: {e}")
        finally:
            self._capture_overlay.stop()
            self.capture_btn.setEnabled(True)

    def _on_apply_settings(self):
        if not self.controller.is_connected:
            self.append_log("[WARN] Instrument not connected.")
            return

        try:
            timebase_val = self.timebase_edit.value_in_seconds()
            channel_settings = [
                self.get_channel_settings(ch_num)
                for ch_num in range(1, self.NUM_CHANNELS + 1)
            ]
            trigger_settings = self.get_trigger_settings()

            self.controller.apply_settings(
                timebase_seconds=timebase_val,
                channel_settings=channel_settings,
                trigger_settings=trigger_settings,
                num_channels=self.NUM_CHANNELS,
            )
            self._clear_settings_dirty()
        except Exception as e:
            self.append_log(f"[ERROR] Apply settings failed: {e}")

    def _on_apply_timebase_only(self):
        if not self.controller.is_connected:
            self.append_log("[WARN] Instrument not connected.")
            return

        try:
            timebase_val = self.timebase_edit.value_in_seconds()
            self.controller.apply_timebase_only(timebase_val)
            self._clear_settings_dirty()
        except (ValueError, Exception) as e:
            self.append_log(f"[ERROR] Timebase setting failed: {e}")

    def _apply_channel_scale_offset(self, channel_num):
        if not self.controller.is_connected:
            return
        inst = self.controller.instrument
        ch = self.channels[channel_num - 1]
        try:
            scale = float(ch['scale_edit'].text())
            offset = float(ch['offset_edit'].text())
            inst.set_channel_scale(channel_num, scale)
            inst.set_channel_offset(channel_num, offset)
            self.append_log(
                f"[SETTING] CH{channel_num}: Scale={scale} V/div, Offset={offset} V"
            )
            self._clear_settings_dirty()
        except Exception as e:
            self.append_log(f"[ERROR] CH{channel_num} setting failed: {e}")

    def _apply_channel_coupling(self, channel_num, coupling_value):
        if not self.controller.is_connected:
            return
        inst = self.controller.instrument
        try:
            if hasattr(inst, 'set_channel_coupling'):
                inst.set_channel_coupling(channel_num, coupling_value)
                self.append_log(f"[SETTING] CH{channel_num}: Coupling={coupling_value}")
            else:
                self.append_log(f"[SETTING] CH{channel_num}: Coupling={coupling_value} (not supported by this instrument)")
            self._clear_settings_dirty()
        except Exception as e:
            self.append_log(f"[ERROR] CH{channel_num} coupling failed: {e}")

    def _apply_channel_display(self, channel_num, enabled):
        if not self.controller.is_connected:
            return
        inst = self.controller.instrument
        try:
            inst.set_channel_display(channel_num, enabled)
            self.append_log(
                f"[SETTING] CH{channel_num}: {'ON' if enabled else 'OFF'}"
            )
        except Exception as e:
            self.append_log(f"[ERROR] CH{channel_num} display toggle failed: {e}")

    def _apply_trigger_immediate(self):
        if not self.controller.is_connected:
            return
        try:
            trigger_settings = self.get_trigger_settings()
            source_text = trigger_settings['source']
            trigger_level = trigger_settings['level']
            slope = trigger_settings['slope']

            if source_text.startswith("CH"):
                trigger_ch = int(source_text[2:])
                self.controller.instrument.set_trigger_edge(trigger_ch, trigger_level, slope)
                self.append_log(
                    f"[SETTING] Trigger: {source_text}, Level={trigger_level} V, Slope={slope}"
                )
            self._clear_settings_dirty()
        except Exception as e:
            self.append_log(f"[ERROR] Trigger setting failed: {e}")

    def _sync_channel_states_from_instrument(self):
        if not self.controller.is_connected:
            return
        inst = self.controller.instrument
        for i in range(self.NUM_CHANNELS):
            ch_num = i + 1
            try:
                if hasattr(inst, 'is_channel_displayed'):
                    on = inst.is_channel_displayed(ch_num)
                elif hasattr(inst, 'get_channel_display'):
                    on = inst.get_channel_display(ch_num)
                else:
                    on = True
                self.channel_tab_buttons[i].setChecked(on)
            except Exception:
                self.channel_tab_buttons[i].setChecked(True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_capture_overlay') and self._capture_overlay.isVisible():
            self._capture_overlay.resize(self.display_placeholder.size())
