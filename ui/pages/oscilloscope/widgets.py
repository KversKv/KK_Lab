#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget, QLineEdit, QLayout
from PySide6.QtCore import (
    Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve,
    QSize, QRect, QPoint, Property,
)
from PySide6.QtGui import QFont, QPainter, QColor, QPen

from ui.widgets.dark_combobox import DarkComboBox


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


class TriggerModeToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._value = "AUTO"
        self._anim_progress = 0.0

        self._bg = QColor("#1A2750")
        self._knob_color = QColor("#243760")
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
        if val not in ("AUTO", "NORMAL"):
            return
        if val == self._value:
            return
        self._value = val
        target = 0.0 if val == "AUTO" else 1.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled.emit(self._value)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = "NORMAL" if self._value == "AUTO" else "AUTO"
            self.setValue(new_val)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2

        p.setPen(QPen(self._border_color, 1))
        p.setBrush(self._bg)
        p.drawRoundedRect(QRect(0, 0, w, h), radius, radius)

        knob_margin = 3
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_y = knob_margin

        p.setPen(Qt.NoPen)
        p.setBrush(self._knob_color)
        p.drawRoundedRect(QRect(int(knob_x), int(knob_y), int(knob_w), int(knob_h)),
                          knob_h / 2, knob_h / 2)

        font = p.font()
        font.setWeight(QFont.Bold)
        font.setPointSize(9)
        p.setFont(font)

        left_rect = QRect(0, 0, w // 2, h)
        right_rect = QRect(w // 2, 0, w // 2, h)

        p.setPen(self._text_active if self._anim_progress < 0.5 else self._text_inactive)
        p.drawText(left_rect, Qt.AlignCenter, "Auto")

        p.setPen(self._text_active if self._anim_progress >= 0.5 else self._text_inactive)
        p.drawText(right_rect, Qt.AlignCenter, "Normal")

        p.end()

    def sizeHint(self):
        return QSize(160, 32)


class RunStopToggle(QWidget):
    clicked = Signal()

    COLOR_RUN_ACTIVE = QColor("#10e7bc")
    COLOR_RUN_ACTIVE_BG = QColor("#053b38")
    COLOR_RUN_ACTIVE_BORDER = QColor("#08c9a5")

    COLOR_STOP_ACTIVE = QColor("#ff4d6d")
    COLOR_STOP_ACTIVE_BG = QColor("#3A0820")
    COLOR_STOP_ACTIVE_BORDER = QColor("#FF6B8A")

    COLOR_DIM_TEXT = QColor("#3A4563")
    COLOR_DIM_BG = QColor("#0B1638")
    COLOR_DIM_BORDER = QColor("#16254A")

    COLOR_WAITING_BG = QColor("#101A33")
    COLOR_WAITING_BORDER = QColor("#2A3A66")

    COLOR_DIVIDER = QColor("#22376A")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._waiting = False
        self._enabled = True
        self._pulse_phase = 0
        self._hover = False

        self.setFixedHeight(40)
        self.setCursor(Qt.PointingHandCursor)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(550)
        self._pulse_timer.timeout.connect(self._on_pulse)

    def isRunning(self) -> bool:
        return self._running

    def isWaiting(self) -> bool:
        return self._waiting

    def setRunning(self, running: bool):
        changed = (running != self._running) or self._waiting
        self._waiting = False
        if running == self._running and not changed:
            return
        self._running = running
        if running:
            self._pulse_phase = 0
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self._pulse_phase = 0
        self.update()

    def setWaiting(self, waiting: bool):
        if waiting == self._waiting:
            return
        self._waiting = waiting
        if waiting:
            self._pulse_timer.stop()
            self._pulse_phase = 0
        elif self._running and self._enabled:
            self._pulse_timer.start()
        self.update()

    def setEnabled(self, enabled: bool):
        self._enabled = enabled
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ArrowCursor)
        if not enabled:
            self._pulse_timer.stop()
        elif self._running and not self._waiting:
            self._pulse_timer.start()
        super().setEnabled(enabled)
        self.update()

    def _on_pulse(self):
        self._pulse_phase = (self._pulse_phase + 1) % 2
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._enabled:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def sizeHint(self):
        return QSize(110, 40)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = 7

        if self._running:
            bg = self.COLOR_RUN_ACTIVE_BG
            border = self.COLOR_RUN_ACTIVE_BORDER
        else:
            bg = self.COLOR_STOP_ACTIVE_BG
            border = self.COLOR_STOP_ACTIVE_BORDER

        if self._waiting:
            bg = self.COLOR_WAITING_BG
            border = self.COLOR_WAITING_BORDER

        if not self._enabled:
            bg = self.COLOR_DIM_BG
            border = self.COLOR_DIM_BORDER

        if self._hover and self._enabled:
            bg = bg.lighter(115)

        p.setPen(QPen(border, 1.2))
        p.setBrush(bg)
        p.drawRoundedRect(QRect(0, 0, w - 1, h - 1), radius, radius)

        run_rect = QRect(0, 0, w, h // 2)
        stop_rect = QRect(0, h // 2, w, h - h // 2)

        font = p.font()
        font.setPointSize(8)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        if not self._enabled:
            run_color = self.COLOR_DIM_TEXT
            stop_color = self.COLOR_DIM_TEXT
        elif self._waiting:
            run_color = self.COLOR_DIM_TEXT
            stop_color = self.COLOR_DIM_TEXT
        elif self._running:
            run_color = self.COLOR_RUN_ACTIVE
            if self._pulse_phase == 1:
                run_color = run_color.lighter(130)
            stop_color = self.COLOR_DIM_TEXT
        else:
            run_color = self.COLOR_DIM_TEXT
            stop_color = self.COLOR_STOP_ACTIVE
            if self._pulse_phase == 1:
                stop_color = stop_color.lighter(130)

        p.setPen(run_color)
        p.drawText(run_rect, Qt.AlignCenter, "Run")

        p.setPen(stop_color)
        p.drawText(stop_rect, Qt.AlignCenter, "Stop")

        divider_pen = QPen(self.COLOR_DIVIDER, 1)
        p.setPen(divider_pen)
        margin_x = 8
        y = h // 2
        p.drawLine(margin_x, y, w - margin_x, y)

        p.end()


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

    unitChanged = Signal(str)

    def __init__(self, default_text="1us", parent=None):
        super().__init__(default_text, parent)
        self._last_unit_mult = 1e-6
        parsed_mult = self._extract_unit_mult(default_text)
        if parsed_mult is not None:
            self._last_unit_mult = parsed_mult
        self._current_index = self._find_nearest_index(self.parse_to_seconds(default_text))
        self._last_emitted_unit = self._MULT_TO_UNIT.get(self._last_unit_mult, 'us')
        self.textChanged.connect(self._maybe_emit_unit_changed)

    def _maybe_emit_unit_changed(self, _text: str = ""):
        mult = self._extract_unit_mult(self.text())
        if mult is None:
            return
        unit = self._MULT_TO_UNIT.get(mult)
        if unit and unit != self._last_emitted_unit:
            self._last_emitted_unit = unit
            self.unitChanged.emit(unit)

    def current_unit(self) -> str:
        mult = self._extract_unit_mult(self.text())
        if mult is None:
            mult = self._last_unit_mult
        return self._MULT_TO_UNIT.get(mult, 'us')

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
