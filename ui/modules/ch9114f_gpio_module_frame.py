# CH9114F GPIO模块框架样式
#python -m ui.modules.ch9114f_gpio_module_frame

import os
import sys
import time

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from ui.resource_path import get_resource_base
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QToolTip, QDoubleSpinBox
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QObject, QSize, QRect, QRectF,
    QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from debug_config import DEBUG_MOCK
from log_config import get_logger

logger = get_logger(__name__)


_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "consumption_test_SVGs"
)

CH9114F_BTN_HEIGHT = 22

CH9114F_GPIO_PINS = (0, 1, 6, 7, 2, 8, 14, 20)

CH9114F_PULSE_WIDTH_DEFAULT_MS = 100.0
CH9114F_PULSE_WIDTH_MIN_MS = 1.0
CH9114F_PULSE_WIDTH_MAX_MS = 10000.0

GPIO_STATE_HIGH = "High"
GPIO_STATE_LOW = "Low"
GPIO_STATE_HIGHZ = "HighZ"

_GPIO_LEVEL_OPTIONS = [
    {"key": GPIO_STATE_HIGH, "label": "High",
     "svg": os.path.join(_PAGE_SVGS_DIR, "polarity_rising.svg")},
    {"key": GPIO_STATE_LOW, "label": "Low",
     "svg": os.path.join(_PAGE_SVGS_DIR, "polarity_falling.svg")},
    {"key": GPIO_STATE_HIGHZ, "label": "High-Z",
     "svg": os.path.join(_PAGE_SVGS_DIR, "x-circle.svg")},
]


class Ch9114HiLoToggle(QWidget):
    level_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._options = _GPIO_LEVEL_OPTIONS
        self._index = next(
            (i for i, opt in enumerate(self._options)
             if opt["key"] == GPIO_STATE_LOW),
            0,
        )
        self._anim_progress = float(self._index)
        self._n = len(self._options)

        self.setFixedHeight(CH9114F_BTN_HEIGHT)
        self.setFixedWidth(self._n * 34)
        self.setCursor(Qt.PointingHandCursor)

        self._bg_color = QColor("#1A2750")
        self._knob_color = QColor("#243760")
        self._icon_active_color = QColor("#F3F6FF")
        self._icon_inactive_color = QColor("#5F77AE")
        self._border_color = QColor("#22376A")

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._icon_cache = {}

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def _render_icon(self, svg_path, color, size=16):
        cache_key = (svg_path, color.name(), size)
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        renderer = QSvgRenderer(svg_path)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        self._icon_cache[cache_key] = pixmap
        return pixmap

    def value(self):
        return self._options[self._index]["key"]

    def setValue(self, key, emit=True):
        for i, opt in enumerate(self._options):
            if opt["key"] == key:
                if i == self._index:
                    return
                self._index = i
                target = float(i)
                self._anim.stop()
                self._anim.setStartValue(self._anim_progress)
                self._anim.setEndValue(target)
                self._anim.start()
                if emit:
                    self.level_changed.emit(key)
                return

    def mousePressEvent(self, event):
        if not self.isEnabled():
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            seg_w = self.width() / self._n
            clicked_idx = int(event.position().x() / seg_w)
            clicked_idx = max(0, min(clicked_idx, self._n - 1))
            if clicked_idx != self._index:
                self._index = clicked_idx
                target = float(clicked_idx)
                self._anim.stop()
                self._anim.setStartValue(self._anim_progress)
                self._anim.setEndValue(target)
                self._anim.start()
                self.level_changed.emit(self._options[self._index]["key"])
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)

        w, h = self.width(), self.height()
        radius = h / 2

        p.setPen(QPen(self._border_color, 1))
        p.setBrush(self._bg_color)
        p.drawRoundedRect(QRect(0, 0, w, h), radius, radius)

        margin = 3
        seg_w = w / self._n
        knob_w = seg_w - margin
        knob_h = h - margin * 2
        knob_x = margin + self._anim_progress * seg_w
        knob_y = margin

        p.setPen(Qt.NoPen)
        p.setBrush(self._knob_color)
        p.drawRoundedRect(QRectF(knob_x, knob_y, knob_w, knob_h),
                          knob_h / 2, knob_h / 2)

        icon_size = 16
        for i, opt in enumerate(self._options):
            cx = seg_w * i + seg_w / 2
            cy = h / 2
            dist = abs(self._anim_progress - i)
            is_active = dist < 0.5
            color = self._icon_active_color if is_active else self._icon_inactive_color
            pixmap = self._render_icon(opt["svg"], color, icon_size)
            ix = int(cx - icon_size / 2)
            iy = int(cy - icon_size / 2)
            p.drawPixmap(ix, iy, pixmap)

        p.end()

    def sizeHint(self):
        return QSize(self._n * 34, CH9114F_BTN_HEIGHT)

    def changeEvent(self, event):
        if event.type() == event.Type.EnabledChange:
            self.setCursor(Qt.PointingHandCursor if self.isEnabled() else Qt.ArrowCursor)
            self.update()
        super().changeEvent(event)

    def event(self, ev):
        if ev.type() == ev.Type.ToolTip:
            seg_w = self.width() / self._n
            x = ev.pos().x()
            idx = int(x / seg_w)
            idx = max(0, min(idx, self._n - 1))
            QToolTip.showText(ev.globalPos(), self._options[idx]["label"], self)
            return True
        return super().event(ev)


def _ch9114f_action_style(h=CH9114F_BTN_HEIGHT):
    return f"""
        QPushButton {{
            background-color: #13254b;
            border: 1px solid #22376A;
            border-radius: 6px;
            color: #dce7ff;
            font-weight: 600;
            min-height: {h}px;
            max-height: {h}px;
            padding: 2px 8px;
        }}
        QPushButton:hover {{
            background-color: #1C2D55;
            border: 1px solid #3A5A9F;
        }}
        QPushButton:pressed {{
            background-color: #102040;
        }}
        QPushButton:disabled {{
            background-color: #0b1430;
            color: #5c7096;
            border: 1px solid #1a2850;
        }}
    """


class _SearchCh9114fWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            from instruments.MCU_IO.ch9114f import list_ch9114f_ports
            ports = list_ch9114f_ports()
            self.finished.emit(list(ports))
        except Exception as e:
            logger.error("CH9114F port scan failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _ConnectCh9114fWorker(QObject):
    finished = Signal(object, str)
    error = Signal(str)

    def __init__(self, port):
        super().__init__()
        self._port = port

    def run(self):
        try:
            from instruments.factory import create_mcu_io
            inst = create_mcu_io("ch9114f", port=self._port)
            ok = inst.connect()
            if ok is False:
                self.error.emit(f"Failed to connect {self._port}")
                return
            self.finished.emit(inst, inst.identify())
        except Exception as e:
            logger.error("CH9114F connection failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _Ch9114fSetOutputWorker(QObject):
    finished = Signal(int, str)
    error = Signal(str)

    def __init__(self, inst, pin, state):
        super().__init__()
        self._inst = inst
        self._pin = pin
        self._state = state

    def run(self):
        try:
            if self._state == GPIO_STATE_HIGHZ:
                self._inst.set_input(self._pin)
            else:
                self._inst.set_output(self._pin)
                self._inst.out(
                    self._pin, 1 if self._state == GPIO_STATE_HIGH else 0
                )
            self.finished.emit(self._pin, self._state)
        except Exception as e:
            logger.error("CH9114F GPIO output failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _Ch9114fToggleWorker(QObject):
    finished = Signal(int, int)
    error = Signal(str)

    def __init__(self, inst, pin):
        super().__init__()
        self._inst = inst
        self._pin = pin

    def run(self):
        try:
            self._inst.set_output(self._pin)
            new_level = 0 if self._inst.read(self._pin) else 1
            self._inst.out(self._pin, new_level)
            self.finished.emit(self._pin, new_level)
        except Exception as e:
            logger.error("CH9114F GPIO toggle failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _Ch9114fPulseWorker(QObject):
    finished = Signal(int, int)
    error = Signal(str)

    def __init__(self, inst, pin, active, width_ms):
        super().__init__()
        self._inst = inst
        self._pin = pin
        self._active = active
        self._width_ms = width_ms

    def run(self):
        try:
            idle = 0 if self._active else 1
            self._inst.set_output(self._pin)
            self._inst.out(self._pin, idle)
            self._inst.out(self._pin, self._active)
            time.sleep(max(self._width_ms, 0) / 1000.0)
            self._inst.out(self._pin, idle)
            self.finished.emit(self._pin, idle)
        except Exception as e:
            logger.error("CH9114F GPIO pulse failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _Ch9114fReadWorker(QObject):
    finished = Signal(int, int)
    error = Signal(str)

    def __init__(self, inst, pin):
        super().__init__()
        self._inst = inst
        self._pin = pin

    def run(self):
        try:
            raw = self._inst.read(self._pin)
            if raw is None:
                self.error.emit(f"GPIO{self._pin} read timeout (no response)")
                return
            self.finished.emit(self._pin, int(raw))
        except Exception as e:
            logger.error("CH9114F GPIO read failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _Ch9114fReadAllWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, inst, pins):
        super().__init__()
        self._inst = inst
        self._pins = list(pins)

    def run(self):
        try:
            levels = {}
            for pin in self._pins:
                raw = self._inst.read(pin)
                levels[pin] = int(raw) if raw is not None else None
            self.finished.emit(levels)
        except Exception as e:
            logger.error("CH9114F GPIO read-all failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class Ch9114GpioMixin:
    ch9114f_connection_status_changed = Signal(bool)

    def init_ch9114f_gpio(self):
        self.ch9114f = None
        self.is_ch9114f_connected = False
        self._ch9114f_search_thread = None
        self._ch9114f_search_worker = None
        self._ch9114f_connect_thread = None
        self._ch9114f_connect_worker = None
        self._ch9114f_output_thread = None
        self._ch9114f_output_worker = None
        self._ch9114f_toggle_thread = None
        self._ch9114f_toggle_worker = None
        self._ch9114f_pulse_thread = None
        self._ch9114f_pulse_worker = None
        self._ch9114f_read_thread = None
        self._ch9114f_read_worker = None
        self._ch9114f_read_all_thread = None
        self._ch9114f_read_all_worker = None

    def build_ch9114f_gpio_widgets(self, layout, title_row=None):
        self.ch9114f_status_label = QLabel("● Disconnected")
        self.ch9114f_status_label.setObjectName("statusErr")
        if title_row is not None:
            title_row.addWidget(self.ch9114f_status_label)
        else:
            layout.addWidget(self.ch9114f_status_label)

        self.ch9114f_port_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.ch9114f_port_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.ch9114f_port_combo.setMinimumContentsLength(10)
        self.ch9114f_port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ch9114f_port_combo.addItem("Select CH9114F COM...")
        layout.addWidget(self.ch9114f_port_combo)

        conn_row = QHBoxLayout()
        conn_row.setSpacing(6)
        conn_row.setContentsMargins(0, 2, 0, 0)

        self.ch9114f_search_btn = SpinningSearchButton()
        self.ch9114f_search_btn.setFixedHeight(CH9114F_BTN_HEIGHT)

        self.ch9114f_connect_btn = QPushButton()
        self.ch9114f_connect_btn.setFixedHeight(CH9114F_BTN_HEIGHT)
        update_connect_button_state(self.ch9114f_connect_btn, connected=False)

        conn_row.addWidget(self.ch9114f_search_btn)
        conn_row.addWidget(self.ch9114f_connect_btn)
        layout.addLayout(conn_row)

        self._build_ch9114f_gpio_rows(layout)

    def _build_ch9114f_gpio_rows(self, layout):
        self.ch9114f_output_toggles = {}
        self.ch9114f_toggle_buttons = {}
        self.ch9114f_pulse_buttons = {}
        self.ch9114f_read_buttons = {}
        self.ch9114f_read_labels = {}
        for pin in CH9114F_GPIO_PINS:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 2, 0, 0)

            name_label = QLabel(f"GPIO{pin}")
            name_label.setFixedWidth(56)
            row.addWidget(name_label, 0, Qt.AlignVCenter)

            state_toggle = Ch9114HiLoToggle()
            state_toggle.setToolTip(
                "Set GPIO output level: High / Low / High-Z (input)."
            )
            state_toggle.level_changed.connect(
                lambda state, p=pin: self._on_ch9114f_set_output(p, state)
            )
            row.addWidget(state_toggle, 0, Qt.AlignVCenter)

            toggle_btn = QPushButton("Toggle")
            toggle_btn.setFixedHeight(CH9114F_BTN_HEIGHT)
            toggle_btn.setFixedWidth(56)
            toggle_btn.setStyleSheet(_ch9114f_action_style())
            toggle_btn.setToolTip("Flip this GPIO output level (High <-> Low).")
            toggle_btn.clicked.connect(
                lambda _=False, p=pin: self._on_ch9114f_toggle(p)
            )
            row.addWidget(toggle_btn, 0, Qt.AlignVCenter)

            pulse_btn = QPushButton("Pulse")
            pulse_btn.setFixedHeight(CH9114F_BTN_HEIGHT)
            pulse_btn.setFixedWidth(56)
            pulse_btn.setStyleSheet(_ch9114f_action_style())
            pulse_btn.setToolTip(
                "Send a single pulse on this GPIO. Active level follows the "
                "level toggle (High/Low); width uses the Pulse (ms) value below."
            )
            pulse_btn.clicked.connect(
                lambda _=False, p=pin: self._on_ch9114f_pulse(p)
            )
            row.addWidget(pulse_btn, 0, Qt.AlignVCenter)

            read_btn = QPushButton("Read")
            read_btn.setFixedHeight(CH9114F_BTN_HEIGHT)
            read_btn.setFixedWidth(56)
            read_btn.setStyleSheet(_ch9114f_action_style())
            read_btn.setToolTip(
                "Read current level of this GPIO without changing its direction."
            )
            read_btn.clicked.connect(lambda _=False, p=pin: self._on_ch9114f_read(p))
            row.addWidget(read_btn, 0, Qt.AlignVCenter)

            read_label = QLabel("Level: —")
            read_label.setFixedWidth(96)
            read_label.setObjectName("statusOk")
            row.addWidget(read_label, 0, Qt.AlignVCenter)

            row.addStretch(1)

            layout.addLayout(row)
            self.ch9114f_output_toggles[pin] = state_toggle
            self.ch9114f_toggle_buttons[pin] = toggle_btn
            self.ch9114f_pulse_buttons[pin] = pulse_btn
            self.ch9114f_read_buttons[pin] = read_btn
            self.ch9114f_read_labels[pin] = read_label

        pulse_width_row = QHBoxLayout()
        pulse_width_row.setSpacing(6)
        pulse_width_row.setContentsMargins(0, 2, 0, 0)
        pulse_width_label = QLabel("Pulse (ms)")
        pulse_width_label.setFixedWidth(56)
        pulse_width_row.addWidget(pulse_width_label, 0, Qt.AlignVCenter)
        self.ch9114f_pulse_width_spin = QDoubleSpinBox()
        self.ch9114f_pulse_width_spin.setObjectName("ch9114fPulseWidthSpin")
        self.ch9114f_pulse_width_spin.setDecimals(1)
        self.ch9114f_pulse_width_spin.setRange(
            CH9114F_PULSE_WIDTH_MIN_MS, CH9114F_PULSE_WIDTH_MAX_MS
        )
        self.ch9114f_pulse_width_spin.setSingleStep(10.0)
        self.ch9114f_pulse_width_spin.setValue(CH9114F_PULSE_WIDTH_DEFAULT_MS)
        self.ch9114f_pulse_width_spin.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.ch9114f_pulse_width_spin.setToolTip(
            "Pulse width in milliseconds, shared by all GPIO Pulse buttons."
        )
        self.ch9114f_pulse_width_spin.setStyleSheet(f"""
            QDoubleSpinBox#ch9114fPulseWidthSpin {{
                background-color: #091426;
                border: 1px solid #17345f;
                border-radius: 6px;
                color: #dce7ff;
                min-height: {CH9114F_BTN_HEIGHT}px;
                max-height: {CH9114F_BTN_HEIGHT}px;
                padding: 0px 6px;
            }}
            QDoubleSpinBox#ch9114fPulseWidthSpin:focus {{
                border: 1px solid #3A5A9F;
            }}
            QDoubleSpinBox#ch9114fPulseWidthSpin::up-button,
            QDoubleSpinBox#ch9114fPulseWidthSpin::down-button {{
                width: 0px;
                border: none;
            }}
            QDoubleSpinBox#ch9114fPulseWidthSpin:disabled {{
                background-color: #0b1430;
                color: #5c7096;
                border: 1px solid #1a2850;
            }}
        """)
        pulse_width_row.addWidget(self.ch9114f_pulse_width_spin, 1, Qt.AlignVCenter)
        layout.addLayout(pulse_width_row)

        self._set_ch9114f_gpio_controls_enabled(False)

    def bind_ch9114f_signals(self):
        self.ch9114f_search_btn.clicked.connect(self._on_ch9114f_search)
        self.ch9114f_connect_btn.clicked.connect(
            self._on_ch9114f_connect_or_disconnect
        )

    def _set_ch9114f_gpio_controls_enabled(self, enabled: bool):
        for toggle in getattr(self, "ch9114f_output_toggles", {}).values():
            toggle.setEnabled(enabled)
        for btn in getattr(self, "ch9114f_toggle_buttons", {}).values():
            btn.setEnabled(enabled)
        for btn in getattr(self, "ch9114f_pulse_buttons", {}).values():
            btn.setEnabled(enabled)
        for btn in getattr(self, "ch9114f_read_buttons", {}).values():
            btn.setEnabled(enabled)
        spin = getattr(self, "ch9114f_pulse_width_spin", None)
        if spin is not None:
            spin.setEnabled(enabled)

    def set_ch9114f_status(self, status, is_error=False):
        self.ch9114f_status_label.setText(status)
        if is_error:
            self.ch9114f_status_label.setObjectName("statusErr")
        elif any(kw in status for kw in
                 ["Searching", "Connecting", "Disconnecting", "Reading",
                  "Setting", "Pulsing"]):
            self.ch9114f_status_label.setObjectName("statusWarn")
        else:
            self.ch9114f_status_label.setObjectName("statusOk")
        self.ch9114f_status_label.style().unpolish(self.ch9114f_status_label)
        self.ch9114f_status_label.style().polish(self.ch9114f_status_label)
        self.ch9114f_status_label.update()

    def _ch9114f_log(self, msg):
        if hasattr(self, "append_log"):
            self.append_log(msg)

    def _selected_ch9114f_port(self):
        text = (
            self.ch9114f_port_combo.currentText()
            if getattr(self, "ch9114f_port_combo", None) else ""
        )
        if not text or text in ("Select CH9114F COM...", "No CH9114F found"):
            return None
        return text.split()[0]

    def _on_ch9114f_search(self):
        if DEBUG_MOCK:
            self.ch9114f_port_combo.clear()
            self.ch9114f_port_combo.addItem("[MOCK] COM98 - Mock CH9114F")
            self.ch9114f_port_combo.setEnabled(True)
            self.set_ch9114f_status("● Mock Ready")
            self.ch9114f_connect_btn.setEnabled(True)
            self._ch9114f_log("[DEBUG] Mock CH9114F port loaded, skip real scan.")
            return

        if (self._ch9114f_search_thread is not None
                and self._ch9114f_search_thread.isRunning()):
            return

        self.set_ch9114f_status("● Searching")
        self._ch9114f_log("[CH9114F] Scanning for CH9114F ports...")
        self.ch9114f_search_btn.setEnabled(False)
        self.ch9114f_connect_btn.setEnabled(False)

        worker = _SearchCh9114fWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ch9114f_search_done)
        worker.error.connect(self._on_ch9114f_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ch9114f_search_thread_cleanup)

        self._ch9114f_search_worker = worker
        self._ch9114f_search_thread = thread
        thread.start()

    def _on_ch9114f_search_thread_cleanup(self):
        self._ch9114f_search_thread = None
        self._ch9114f_search_worker = None

    def _on_ch9114f_search_done(self, ports):
        self.ch9114f_port_combo.clear()
        self.ch9114f_port_combo.setEnabled(True)
        if ports:
            for port in ports:
                self.ch9114f_port_combo.addItem(port)
            self.ch9114f_port_combo.setCurrentIndex(self.ch9114f_port_combo.count() - 1)
            self.set_ch9114f_status(f"● Found {len(ports)}")
            self._ch9114f_log(
                f"[CH9114F] Found {len(ports)} port(s): {', '.join(ports)}"
            )
        else:
            self.ch9114f_port_combo.addItem("No CH9114F found")
            self.ch9114f_port_combo.setEnabled(False)
            self.set_ch9114f_status("● Not Found", is_error=True)
            self._ch9114f_log("[CH9114F] No CH9114F ports found.")
        self.ch9114f_search_btn.setEnabled(True)
        self.ch9114f_connect_btn.setEnabled(bool(ports))

    def _on_ch9114f_search_error(self, err):
        self.set_ch9114f_status("● Search Failed", is_error=True)
        self._ch9114f_log(f"[CH9114F] Search failed: {err}")
        self.ch9114f_search_btn.setEnabled(True)
        self.ch9114f_connect_btn.setEnabled(True)

    def _on_ch9114f_connect_or_disconnect(self):
        if self.is_ch9114f_connected:
            self._disconnect_ch9114f()
        else:
            self._connect_ch9114f()

    def _connect_ch9114f(self):
        port = self._selected_ch9114f_port()
        if not port:
            self._ch9114f_log("[CH9114F] No valid port selected.")
            self.set_ch9114f_status("● Select port first", is_error=True)
            return

        if (self._ch9114f_connect_thread is not None
                and self._ch9114f_connect_thread.isRunning()):
            return

        self.set_ch9114f_status("● Connecting")
        self.ch9114f_search_btn.setEnabled(False)
        self.ch9114f_connect_btn.setEnabled(False)
        self._ch9114f_log(f"[CH9114F] Connecting on {port}...")

        worker = _ConnectCh9114fWorker(port)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ch9114f_connected)
        worker.error.connect(self._on_ch9114f_connect_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ch9114f_connect_thread_cleanup)

        self._ch9114f_connect_worker = worker
        self._ch9114f_connect_thread = thread
        thread.start()

    def _on_ch9114f_connect_thread_cleanup(self):
        self._ch9114f_connect_thread = None
        self._ch9114f_connect_worker = None

    def _on_ch9114f_connected(self, inst, idn):
        self.ch9114f = inst
        self.is_ch9114f_connected = True
        self.set_ch9114f_status("● Connected")
        self.ch9114f_search_btn.setEnabled(False)
        self.ch9114f_connect_btn.setEnabled(True)
        update_connect_button_state(self.ch9114f_connect_btn, connected=True)
        self._set_ch9114f_gpio_controls_enabled(True)
        self._ch9114f_log(f"[CH9114F] Connected: {idn}")
        self.ch9114f_connection_status_changed.emit(True)
        self._refresh_ch9114f_all_states()

    def _refresh_ch9114f_all_states(self):
        if not self.is_ch9114f_connected or self.ch9114f is None:
            return
        if (self._ch9114f_read_all_thread is not None
                and self._ch9114f_read_all_thread.isRunning()):
            return

        self.set_ch9114f_status("● Reading states")
        self._set_ch9114f_gpio_controls_enabled(False)
        self._ch9114f_log("[CH9114F] Reading all GPIO states for alignment...")

        worker = _Ch9114fReadAllWorker(self.ch9114f, CH9114F_GPIO_PINS)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ch9114f_read_all_done)
        worker.error.connect(self._on_ch9114f_read_all_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ch9114f_read_all_thread_cleanup)

        self._ch9114f_read_all_worker = worker
        self._ch9114f_read_all_thread = thread
        thread.start()

    def _on_ch9114f_read_all_thread_cleanup(self):
        self._ch9114f_read_all_thread = None
        self._ch9114f_read_all_worker = None

    def _on_ch9114f_read_all_done(self, levels):
        for pin, value in levels.items():
            toggle = getattr(self, "ch9114f_output_toggles", {}).get(pin)
            label = getattr(self, "ch9114f_read_labels", {}).get(pin)
            if value is None:
                if label is not None:
                    label.setText("Level: —")
                continue
            state = GPIO_STATE_HIGH if value else GPIO_STATE_LOW
            level_name = "High" if value else "Low"
            if toggle is not None:
                toggle.setValue(state, emit=False)
            if label is not None:
                label.setText(f"Level: {value} ({level_name})")
        self.set_ch9114f_status("● Connected")
        self._set_ch9114f_gpio_controls_enabled(True)
        self._ch9114f_log("[CH9114F] GPIO states aligned.")

    def _on_ch9114f_read_all_error(self, err):
        self.set_ch9114f_status("● Connected")
        self._set_ch9114f_gpio_controls_enabled(True)
        self._ch9114f_log(f"[CH9114F] Read all states failed: {err}")

    def _on_ch9114f_connect_error(self, err):
        self.set_ch9114f_status("● Failed", is_error=True)
        self.ch9114f_search_btn.setEnabled(True)
        self.ch9114f_connect_btn.setEnabled(True)
        self._ch9114f_log(f"[CH9114F] Connection failed: {err}")

    def _disconnect_ch9114f(self):
        self.set_ch9114f_status("● Disconnecting")
        self.ch9114f_connect_btn.setEnabled(False)
        try:
            if self.ch9114f is not None:
                self.ch9114f.disconnect()
        except Exception as e:
            logger.error("CH9114F disconnect failed: %s", e, exc_info=True)
            self._ch9114f_log(f"[CH9114F] Disconnect failed: {e}")
        finally:
            self.ch9114f = None
            self.is_ch9114f_connected = False
            self.set_ch9114f_status("● Disconnected", is_error=True)
            self.ch9114f_search_btn.setEnabled(True)
            self.ch9114f_connect_btn.setEnabled(True)
            update_connect_button_state(self.ch9114f_connect_btn, connected=False)
            self._set_ch9114f_gpio_controls_enabled(False)
            self._ch9114f_log("[CH9114F] Disconnected.")
            self.ch9114f_connection_status_changed.emit(False)

    def _on_ch9114f_set_output(self, pin, state=None):
        if not self.is_ch9114f_connected or self.ch9114f is None:
            self._ch9114f_log("[CH9114F] Not connected, cannot set GPIO output.")
            return
        if (self._ch9114f_output_thread is not None
                and self._ch9114f_output_thread.isRunning()):
            return
        if state is None:
            toggle = self.ch9114f_output_toggles.get(pin)
            state = toggle.value() if toggle else GPIO_STATE_LOW

        self.set_ch9114f_status(f"● Setting GPIO{pin}")
        self._ch9114f_log(f"[CH9114F] Setting GPIO{pin} -> {state}...")

        worker = _Ch9114fSetOutputWorker(self.ch9114f, pin, state)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ch9114f_output_done)
        worker.error.connect(self._on_ch9114f_output_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ch9114f_output_thread_cleanup)

        self._ch9114f_output_worker = worker
        self._ch9114f_output_thread = thread
        thread.start()

    def _on_ch9114f_output_thread_cleanup(self):
        self._ch9114f_output_thread = None
        self._ch9114f_output_worker = None

    def _on_ch9114f_output_done(self, pin, state):
        self.set_ch9114f_status("● Connected")
        self._ch9114f_log(f"[CH9114F] GPIO{pin} set to {state}.")

    def _on_ch9114f_output_error(self, err):
        self.set_ch9114f_status("● Set Failed", is_error=True)
        self._ch9114f_log(f"[CH9114F] Set GPIO output failed: {err}")

    def _on_ch9114f_toggle(self, pin):
        if not self.is_ch9114f_connected or self.ch9114f is None:
            self._ch9114f_log("[CH9114F] Not connected, cannot toggle GPIO.")
            return
        if (self._ch9114f_toggle_thread is not None
                and self._ch9114f_toggle_thread.isRunning()):
            return

        self.set_ch9114f_status(f"● Setting GPIO{pin}")
        self._ch9114f_log(f"[CH9114F] Toggling GPIO{pin}...")

        worker = _Ch9114fToggleWorker(self.ch9114f, pin)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ch9114f_toggle_done)
        worker.error.connect(self._on_ch9114f_toggle_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ch9114f_toggle_thread_cleanup)

        self._ch9114f_toggle_worker = worker
        self._ch9114f_toggle_thread = thread
        thread.start()

    def _on_ch9114f_toggle_thread_cleanup(self):
        self._ch9114f_toggle_thread = None
        self._ch9114f_toggle_worker = None

    def _on_ch9114f_toggle_done(self, pin, level):
        state = GPIO_STATE_HIGH if level else GPIO_STATE_LOW
        level_name = "High" if level else "Low"
        toggle = getattr(self, "ch9114f_output_toggles", {}).get(pin)
        if toggle is not None:
            toggle.setValue(state, emit=False)
        label = getattr(self, "ch9114f_read_labels", {}).get(pin)
        if label is not None:
            label.setText(f"Level: {level} ({level_name})")
        self.set_ch9114f_status("● Connected")
        self._ch9114f_log(f"[CH9114F] GPIO{pin} toggled to {level} ({state}).")

    def _on_ch9114f_toggle_error(self, err):
        self.set_ch9114f_status("● Toggle Failed", is_error=True)
        self._ch9114f_log(f"[CH9114F] Toggle GPIO failed: {err}")

    def _on_ch9114f_pulse(self, pin):
        if not self.is_ch9114f_connected or self.ch9114f is None:
            self._ch9114f_log("[CH9114F] Not connected, cannot pulse GPIO.")
            return
        if (self._ch9114f_pulse_thread is not None
                and self._ch9114f_pulse_thread.isRunning()):
            return

        toggle = self.ch9114f_output_toggles.get(pin)
        state = toggle.value() if toggle else GPIO_STATE_HIGH
        active = 0 if state == GPIO_STATE_LOW else 1
        width_ms = self.ch9114f_pulse_width_spin.value()

        self.set_ch9114f_status(f"● Pulsing GPIO{pin}")
        self._set_ch9114f_gpio_controls_enabled(False)
        self._ch9114f_log(
            f"[CH9114F] Pulsing GPIO{pin} active={active} width={width_ms}ms..."
        )

        worker = _Ch9114fPulseWorker(self.ch9114f, pin, active, width_ms)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ch9114f_pulse_done)
        worker.error.connect(self._on_ch9114f_pulse_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ch9114f_pulse_thread_cleanup)

        self._ch9114f_pulse_worker = worker
        self._ch9114f_pulse_thread = thread
        thread.start()

    def _on_ch9114f_pulse_thread_cleanup(self):
        self._ch9114f_pulse_thread = None
        self._ch9114f_pulse_worker = None

    def _on_ch9114f_pulse_done(self, pin, idle):
        state = GPIO_STATE_HIGH if idle else GPIO_STATE_LOW
        level_name = "High" if idle else "Low"
        toggle = getattr(self, "ch9114f_output_toggles", {}).get(pin)
        if toggle is not None:
            toggle.setValue(state, emit=False)
        label = getattr(self, "ch9114f_read_labels", {}).get(pin)
        if label is not None:
            label.setText(f"Level: {idle} ({level_name})")
        self.set_ch9114f_status("● Connected")
        self._set_ch9114f_gpio_controls_enabled(True)
        self._ch9114f_log(f"[CH9114F] GPIO{pin} pulse done (idle={idle}).")

    def _on_ch9114f_pulse_error(self, err):
        self.set_ch9114f_status("● Pulse Failed", is_error=True)
        self._set_ch9114f_gpio_controls_enabled(True)
        self._ch9114f_log(f"[CH9114F] Pulse GPIO failed: {err}")

    def _on_ch9114f_read(self, pin):
        if not self.is_ch9114f_connected or self.ch9114f is None:
            self._ch9114f_log("[CH9114F] Not connected, cannot read GPIO.")
            return
        if (self._ch9114f_read_thread is not None
                and self._ch9114f_read_thread.isRunning()):
            return

        self.set_ch9114f_status(f"● Reading GPIO{pin}")
        self._set_ch9114f_gpio_controls_enabled(False)
        self._ch9114f_log(f"[CH9114F] Reading GPIO{pin}...")

        worker = _Ch9114fReadWorker(self.ch9114f, pin)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_ch9114f_read_done)
        worker.error.connect(self._on_ch9114f_read_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_ch9114f_read_thread_cleanup)

        self._ch9114f_read_worker = worker
        self._ch9114f_read_thread = thread
        thread.start()

    def _on_ch9114f_read_thread_cleanup(self):
        self._ch9114f_read_thread = None
        self._ch9114f_read_worker = None

    def _on_ch9114f_read_done(self, pin, value):
        level = "High" if value else "Low"
        label = getattr(self, "ch9114f_read_labels", {}).get(pin)
        if label is not None:
            label.setText(f"Level: {value} ({level})")
        self.set_ch9114f_status("● Connected")
        self._set_ch9114f_gpio_controls_enabled(True)
        self._ch9114f_log(f"[CH9114F] GPIO{pin} read = {value} ({level}).")

    def _on_ch9114f_read_error(self, err):
        self.set_ch9114f_status("● Read Failed", is_error=True)
        self._set_ch9114f_gpio_controls_enabled(True)
        self._ch9114f_log(f"[CH9114F] Read GPIO failed: {err}")

    def get_ch9114f_instance(self):
        return self.ch9114f

    def is_ch9114f_device_connected(self):
        return self.is_ch9114f_connected


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer
    from ui.standalone import resize_and_center_window

    DARK_CARD_STYLE = """
        QWidget {
            background-color: #020817;
            color: #dbe7ff;
        }
        QLabel {
            background-color: transparent;
            color: #dbe7ff;
            border: none;
        }
        QLabel#cardTitle {
            font-size: 11px;
            font-weight: 700;
            color: #f4f7ff;
            letter-spacing: 0.5px;
            background-color: transparent;
        }
        QLabel#statusOk {
            color: #15d1a3;
            font-weight: 600;
            background-color: transparent;
        }
        QLabel#statusWarn {
            color: #ffb84d;
            font-weight: 600;
            background-color: transparent;
        }
        QLabel#statusErr {
            color: #ff5e7a;
            font-weight: 600;
            background-color: transparent;
        }
        QFrame#cardFrame {
            background-color: #071127;
            border: 1px solid #1a2b52;
            border-radius: 12px;
        }
    """

    class _CardFrame(QFrame):
        def __init__(self, title="", parent=None):
            super().__init__(parent)
            self.setObjectName("cardFrame")
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(12, 10, 12, 12)
            self.main_layout.setSpacing(8)
            if title:
                self.title_row = QHBoxLayout()
                self.title_row.setSpacing(8)
                self.title_label = QLabel(title)
                self.title_label.setObjectName("cardTitle")
                self.title_row.addWidget(self.title_label)
                self.title_row.addStretch()
                self.main_layout.addLayout(self.title_row)
            else:
                self.title_label = None
                self.title_row = None

    class _DemoCh9114fWidget(Ch9114GpioMixin, QWidget):
        ch9114f_connection_status_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_ch9114f_gpio()
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            card = _CardFrame("CH9114F GPIO")
            self.build_ch9114f_gpio_widgets(
                card.main_layout, title_row=card.title_row)
            root.addWidget(card)

            self.bind_ch9114f_signals()
            QTimer.singleShot(0, self._on_ch9114f_search)

        def append_log(self, msg):
            logger.info(msg)

        def _on_ch9114f_search_done(self, ports):
            super()._on_ch9114f_search_done(ports)
            if not ports:
                return
            combo = self.ch9114f_port_combo
            best_idx = 0
            best_num = -1
            for i in range(combo.count()):
                m = re.search(r'COM(\d+)', combo.itemText(i), re.IGNORECASE)
                num = int(m.group(1)) if m else -1
                if num > best_num:
                    best_num = num
                    best_idx = i
            combo.setCurrentIndex(best_idx)

    class _DemoWindow(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setStyleSheet(DARK_CARD_STYLE)
            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)
            root.setSpacing(12)
            root.addWidget(_DemoCh9114fWidget())
            root.addStretch()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = _DemoWindow()
    w.setWindowTitle("CH9114F GPIO Card")
    resize_and_center_window(w, size=(510, 510))
    w.show()

    sys.exit(app.exec())
