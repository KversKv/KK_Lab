# MCU IO模块框架样式
#python -m ui.modules.mcu_io_module_frame

import os
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from ui.resource_path import get_resource_base
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QToolTip, QCheckBox, QDoubleSpinBox
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

MCU_IO_BTN_HEIGHT = 22
MCU_IO_DEFAULT_BAUDRATE = 921600
MCU_IO_GPIO_PINS = (0, 1)
MCU_IO_GPIO_OPTIONS = tuple(f"GPIO{i}" for i in range(0, 30))

GPIO_STATE_HIGH = "High"
GPIO_STATE_LOW = "Low"
GPIO_STATE_HIGHZ = "HighZ"
GPIO_OUTPUT_STATES = (GPIO_STATE_HIGH, GPIO_STATE_LOW, GPIO_STATE_HIGHZ)

_GPIO_LEVEL_OPTIONS = [
    {"key": GPIO_STATE_HIGH, "label": "High", "svg": os.path.join(_PAGE_SVGS_DIR, "polarity_rising.svg")},
    {"key": GPIO_STATE_LOW, "label": "Low", "svg": os.path.join(_PAGE_SVGS_DIR, "polarity_falling.svg")},
    {"key": GPIO_STATE_HIGHZ, "label": "High-Z", "svg": os.path.join(_PAGE_SVGS_DIR, "x-circle.svg")},
]

MCU_PWR_RESET_GPIO_OPTIONS = tuple(f"GPIO{i}" for i in range(0, 30))

MCU_PWR_RESET_DEFAULTS = {"poweron": "GPIO0", "reset": "GPIO1", "status": "GPIO2"}

_POLARITY_OPTIONS = [
    {"key": "rising", "label": "Rising Edge", "svg": os.path.join(_PAGE_SVGS_DIR, "polarity_rising.svg")},
    {"key": "falling", "label": "Falling Edge", "svg": os.path.join(_PAGE_SVGS_DIR, "polarity_falling.svg")},
]

MCU_DRIVE_MODE_PULSE = "pulse"
MCU_DRIVE_MODE_LEVEL = "level"

MCU_PWR_RESET_PULSE_WIDTH_DEFAULT_MS = 100.0
MCU_PWR_RESET_PULSE_WIDTH_MIN_MS = 1.0
MCU_PWR_RESET_PULSE_WIDTH_MAX_MS = 60000.0

_DRIVE_MODE_OPTIONS = [
    {"key": MCU_DRIVE_MODE_PULSE, "label": "Pulse"},
    {"key": MCU_DRIVE_MODE_LEVEL, "label": "Level"},
]


class GpioLevelToggle(QWidget):
    level_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._options = _GPIO_LEVEL_OPTIONS
        self._index = next(
            (i for i, opt in enumerate(self._options)
             if opt["key"] == GPIO_STATE_HIGHZ),
            0,
        )
        self._anim_progress = float(self._index)
        self._n = len(self._options)

        self.setFixedHeight(MCU_IO_BTN_HEIGHT)
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

    def setValue(self, key):
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
        return QSize(self._n * 34, MCU_IO_BTN_HEIGHT)

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


def _mcu_io_action_style(h=MCU_IO_BTN_HEIGHT):
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


class _SearchMcuIoWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            self.finished.emit([f"{p.device} - {p.description}" for p in ports])
        except Exception as e:
            logger.error("MCU IO port scan failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _ConnectMcuIoWorker(QObject):
    finished = Signal(object, str)
    error = Signal(str)

    def __init__(self, port, baudrate=MCU_IO_DEFAULT_BAUDRATE):
        super().__init__()
        self._port = port
        self._baudrate = baudrate

    def run(self):
        try:
            from instruments.factory import create_mcu_io
            inst = create_mcu_io("yd_rp2040", port=self._port, baudrate=self._baudrate)
            ok = inst.connect()
            if ok is False:
                self.error.emit(f"Failed to connect {self._port}")
                return
            self.finished.emit(inst, inst.identify())
        except Exception as e:
            logger.error("MCU IO connection failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _GpioOutputWorker(QObject):
    finished = Signal(int, str)
    error = Signal(str)

    def __init__(self, inst, pin, state):
        super().__init__()
        self._inst = inst
        self._pin = pin
        self._state = state

    def run(self):
        try:
            if self._state == GPIO_STATE_HIGH:
                self._inst.out(self._pin, 1)
            elif self._state == GPIO_STATE_LOW:
                self._inst.out(self._pin, 0)
            else:
                self._inst.in_pull(self._pin, "none")
            self.finished.emit(self._pin, self._state)
        except Exception as e:
            logger.error("MCU IO GPIO output failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _GpioPulseWorker(QObject):
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, inst, pin, active, width_ms):
        super().__init__()
        self._inst = inst
        self._pin = pin
        self._active = active
        self._width_ms = width_ms

    def run(self):
        try:
            self._inst.pulse(
                self._pin, width_ms=self._width_ms, active=self._active
            )
            self.finished.emit(self._pin)
        except Exception as e:
            logger.error("MCU IO GPIO pulse failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _GpioReadWorker(QObject):
    finished = Signal(int, int)
    error = Signal(str)

    def __init__(self, inst, pin, pull="none"):
        super().__init__()
        self._inst = inst
        self._pin = pin
        self._pull = pull

    def run(self):
        try:
            raw = self._inst.read(self._pin)
            if raw is None:
                self.error.emit(f"GPIO{self._pin} read timeout (no response)")
                return
            self.finished.emit(self._pin, int(raw))
        except Exception as e:
            logger.error("MCU IO GPIO read failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _PwrResetPulseWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, inst, actions, pulse_width=0.1):
        super().__init__()
        self._inst = inst
        self._actions = actions
        self._pulse_width = pulse_width

    def run(self):
        try:
            width_ms = int(round(self._pulse_width * 1000))
            for name, pin, polarity in self._actions:
                active = 1 if polarity == "rising" else 0
                self._inst.pulse(pin, width_ms=width_ms, active=active)
            self.finished.emit("done")
        except Exception as e:
            logger.error("MCU PWR/RESET pulse failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _LevelSetWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, inst, name, pin, level):
        super().__init__()
        self._inst = inst
        self._name = name
        self._pin = pin
        self._level = level

    def run(self):
        try:
            self._inst.out(self._pin, self._level)
            self.finished.emit("done")
        except Exception as e:
            logger.error("MCU level set failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class McuIoConnectionMixin:
    mcu_io_connection_status_changed = Signal(bool)

    def init_mcu_io_connection(self, baudrate=MCU_IO_DEFAULT_BAUDRATE):
        self.mcu_io = None
        self.is_mcu_io_connected = False
        self._mcu_io_baudrate = baudrate
        self._mcu_io_search_thread = None
        self._mcu_io_search_worker = None
        self._mcu_io_connect_thread = None
        self._mcu_io_connect_worker = None
        self._mcu_io_output_thread = None
        self._mcu_io_output_worker = None
        self._mcu_io_read_thread = None
        self._mcu_io_read_worker = None
        self._mcu_io_pulse_thread = None
        self._mcu_io_pulse_worker = None

    def build_mcu_io_connection_widgets(self, layout, title_row=None, with_gpio=True):
        self.mcu_io_status_label = QLabel("● Disconnected")
        self.mcu_io_status_label.setObjectName("statusErr")
        if title_row is not None:
            title_row.addWidget(self.mcu_io_status_label)
        else:
            layout.addWidget(self.mcu_io_status_label)

        self.mcu_io_port_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.mcu_io_port_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.mcu_io_port_combo.setMinimumContentsLength(10)
        self.mcu_io_port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mcu_io_port_combo.addItem("Select MCU COM...")
        layout.addWidget(self.mcu_io_port_combo)

        conn_row = QHBoxLayout()
        conn_row.setSpacing(6)
        conn_row.setContentsMargins(0, 2, 0, 0)

        self.mcu_io_search_btn = SpinningSearchButton()
        self.mcu_io_search_btn.setFixedHeight(MCU_IO_BTN_HEIGHT)

        self.mcu_io_connect_btn = QPushButton()
        self.mcu_io_connect_btn.setFixedHeight(MCU_IO_BTN_HEIGHT)
        update_connect_button_state(self.mcu_io_connect_btn, connected=False)

        conn_row.addWidget(self.mcu_io_search_btn)
        conn_row.addWidget(self.mcu_io_connect_btn)
        layout.addLayout(conn_row)

        if with_gpio:
            self._build_mcu_io_gpio_widgets(layout)

    def _build_mcu_io_gpio_widgets(self, layout):
        self.mcu_io_output_toggles = {}
        self.mcu_io_pulse_buttons = {}
        for pin in MCU_IO_GPIO_PINS:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 2, 0, 0)

            name_label = QLabel(f"GPIO{pin}")
            name_label.setFixedWidth(56)
            row.addWidget(name_label, 0, Qt.AlignVCenter)

            state_toggle = GpioLevelToggle()
            state_toggle.level_changed.connect(
                lambda state, p=pin: self._on_mcu_io_set_output(p, state)
            )
            row.addWidget(state_toggle, 0, Qt.AlignVCenter)

            pulse_btn = QPushButton("Pulse")
            pulse_btn.setFixedHeight(MCU_IO_BTN_HEIGHT)
            pulse_btn.setFixedWidth(56)
            pulse_btn.setStyleSheet(_mcu_io_action_style())
            pulse_btn.setToolTip(
                "Send a single pulse on this GPIO. Active level follows the level "
                "toggle (High/Low); width uses the Pulse (ms) value below."
            )
            pulse_btn.clicked.connect(lambda _=False, p=pin: self._on_mcu_io_pulse(p))
            row.addWidget(pulse_btn, 0, Qt.AlignVCenter)

            row.addStretch(1)

            layout.addLayout(row)
            self.mcu_io_output_toggles[pin] = state_toggle
            self.mcu_io_pulse_buttons[pin] = pulse_btn

        pulse_width_row = QHBoxLayout()
        pulse_width_row.setSpacing(6)
        pulse_width_row.setContentsMargins(0, 2, 0, 0)
        pulse_width_label = QLabel("Pulse (ms)")
        pulse_width_label.setFixedWidth(56)
        pulse_width_row.addWidget(pulse_width_label, 0, Qt.AlignVCenter)
        self.mcu_io_pulse_width_spin = QDoubleSpinBox()
        self.mcu_io_pulse_width_spin.setObjectName("mcuIoPulseWidthSpin")
        self.mcu_io_pulse_width_spin.setDecimals(1)
        self.mcu_io_pulse_width_spin.setRange(
            MCU_PWR_RESET_PULSE_WIDTH_MIN_MS, MCU_PWR_RESET_PULSE_WIDTH_MAX_MS
        )
        self.mcu_io_pulse_width_spin.setSingleStep(10.0)
        self.mcu_io_pulse_width_spin.setValue(MCU_PWR_RESET_PULSE_WIDTH_DEFAULT_MS)
        self.mcu_io_pulse_width_spin.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.mcu_io_pulse_width_spin.setToolTip(
            "Pulse width in milliseconds, shared by all GPIO Pulse buttons."
        )
        self.mcu_io_pulse_width_spin.setStyleSheet(f"""
            QDoubleSpinBox#mcuIoPulseWidthSpin {{
                background-color: #091426;
                border: 1.5px solid #17345f;
                border-radius: 6px;
                color: #c8d5e2;
                padding: 2px 8px;
                min-height: {MCU_IO_BTN_HEIGHT}px;
                max-height: {MCU_IO_BTN_HEIGHT}px;
            }}
            QDoubleSpinBox#mcuIoPulseWidthSpin:focus {{
                border: 1.5px solid #2dd4ff;
            }}
            QDoubleSpinBox#mcuIoPulseWidthSpin::up-button,
            QDoubleSpinBox#mcuIoPulseWidthSpin::down-button {{
                width: 0px;
                height: 0px;
                border: none;
            }}
            QDoubleSpinBox#mcuIoPulseWidthSpin:disabled {{
                background-color: #0b1430;
                color: #5c7096;
                border: 1.5px solid #1a2850;
            }}
        """)
        pulse_width_row.addWidget(self.mcu_io_pulse_width_spin, 1, Qt.AlignVCenter)
        layout.addLayout(pulse_width_row)

        read_row = QHBoxLayout()
        read_row.setSpacing(6)
        read_row.setContentsMargins(0, 2, 0, 0)

        self.mcu_io_read_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.mcu_io_read_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mcu_io_read_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        for opt in MCU_IO_GPIO_OPTIONS:
            self.mcu_io_read_combo.addItem(opt)
        read_row.addWidget(self.mcu_io_read_combo, 1, Qt.AlignVCenter)

        self.mcu_io_read_btn = QPushButton("Read")
        self.mcu_io_read_btn.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_io_read_btn.setFixedWidth(64)
        self.mcu_io_read_btn.setStyleSheet(_mcu_io_action_style())
        read_row.addWidget(self.mcu_io_read_btn, 0, Qt.AlignVCenter)

        self.mcu_io_read_value_label = QLabel("Level: —")
        self.mcu_io_read_value_label.setFixedWidth(80)
        self.mcu_io_read_value_label.setObjectName("statusOk")
        read_row.addWidget(self.mcu_io_read_value_label, 0, Qt.AlignVCenter)

        layout.addLayout(read_row)

        self._set_mcu_io_gpio_controls_enabled(False)

    def bind_mcu_io_signals(self):
        self.mcu_io_search_btn.clicked.connect(self._on_mcu_io_search)
        self.mcu_io_connect_btn.clicked.connect(
            self._on_mcu_io_connect_or_disconnect
        )
        if getattr(self, "mcu_io_read_btn", None) is not None:
            self.mcu_io_read_btn.clicked.connect(self._on_mcu_io_read)

    def _set_mcu_io_gpio_controls_enabled(self, enabled: bool):
        for toggle in getattr(self, "mcu_io_output_toggles", {}).values():
            toggle.setEnabled(enabled)
        for btn in getattr(self, "mcu_io_pulse_buttons", {}).values():
            btn.setEnabled(enabled)
        if getattr(self, "mcu_io_pulse_width_spin", None) is not None:
            self.mcu_io_pulse_width_spin.setEnabled(enabled)
        if hasattr(self, "mcu_io_read_combo"):
            self.mcu_io_read_combo.setEnabled(enabled)
        if hasattr(self, "mcu_io_read_btn"):
            self.mcu_io_read_btn.setEnabled(enabled)

    def set_mcu_io_status(self, status, is_error=False):
        self.mcu_io_status_label.setText(status)
        if is_error:
            self.mcu_io_status_label.setObjectName("statusErr")
        elif any(kw in status for kw in
                 ["Searching", "Connecting", "Disconnecting", "Reading", "Setting"]):
            self.mcu_io_status_label.setObjectName("statusWarn")
        else:
            self.mcu_io_status_label.setObjectName("statusOk")
        self.mcu_io_status_label.style().unpolish(self.mcu_io_status_label)
        self.mcu_io_status_label.style().polish(self.mcu_io_status_label)
        self.mcu_io_status_label.update()

    def _mcu_io_log(self, msg):
        if hasattr(self, "append_log"):
            self.append_log(msg)

    def _selected_mcu_io_port(self):
        text = (
            self.mcu_io_port_combo.currentText()
            if getattr(self, "mcu_io_port_combo", None) else ""
        )
        if not text or text in ("Select MCU COM...", "No serial ports found"):
            return None
        return text.split()[0]

    def _on_mcu_io_search(self):
        if DEBUG_MOCK:
            self.mcu_io_port_combo.clear()
            self.mcu_io_port_combo.addItem("[MOCK] COM98 - Mock YD RP2040")
            self.mcu_io_port_combo.setEnabled(True)
            self.set_mcu_io_status("● Mock Ready")
            self.mcu_io_connect_btn.setEnabled(True)
            self._mcu_io_log("[DEBUG] Mock MCU IO port loaded, skip real scan.")
            return

        if self._mcu_io_search_thread is not None and self._mcu_io_search_thread.isRunning():
            return

        self.set_mcu_io_status("● Searching")
        self._mcu_io_log("[MCU] Scanning serial ports for YD RP2040...")
        self.mcu_io_search_btn.setEnabled(False)
        self.mcu_io_connect_btn.setEnabled(False)

        worker = _SearchMcuIoWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_io_search_done)
        worker.error.connect(self._on_mcu_io_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_io_search_thread_cleanup)

        self._mcu_io_search_worker = worker
        self._mcu_io_search_thread = thread
        thread.start()

    def _on_mcu_io_search_thread_cleanup(self):
        self._mcu_io_search_thread = None
        self._mcu_io_search_worker = None

    def _on_mcu_io_search_done(self, ports):
        self.mcu_io_port_combo.clear()
        self.mcu_io_port_combo.setEnabled(True)
        if ports:
            for port in ports:
                self.mcu_io_port_combo.addItem(port)
            self.set_mcu_io_status(f"● Found {len(ports)}")
            self._mcu_io_log(f"[MCU] Found {len(ports)} serial port(s).")
        else:
            self.mcu_io_port_combo.addItem("No serial ports found")
            self.mcu_io_port_combo.setEnabled(False)
            self.set_mcu_io_status("● Not Found", is_error=True)
            self._mcu_io_log("[MCU] No serial ports found.")
        self.mcu_io_search_btn.setEnabled(True)
        self.mcu_io_connect_btn.setEnabled(bool(ports))

    def _on_mcu_io_search_error(self, err):
        self.set_mcu_io_status("● Search Failed", is_error=True)
        self._mcu_io_log(f"[MCU] Search failed: {err}")
        self.mcu_io_search_btn.setEnabled(True)
        self.mcu_io_connect_btn.setEnabled(True)

    def _on_mcu_io_connect_or_disconnect(self):
        if self.is_mcu_io_connected:
            self._disconnect_mcu_io()
        else:
            self._connect_mcu_io()

    def _connect_mcu_io(self):
        port = self._selected_mcu_io_port()
        if not port:
            self._mcu_io_log("[MCU] No valid MCU port selected.")
            self.set_mcu_io_status("● Select port first", is_error=True)
            return
        if self._mcu_io_connect_thread is not None and self._mcu_io_connect_thread.isRunning():
            return

        self.set_mcu_io_status("● Connecting")
        self.mcu_io_search_btn.setEnabled(False)
        self.mcu_io_connect_btn.setEnabled(False)
        self._mcu_io_log(f"[MCU] Connecting YD RP2040 on {port}...")

        worker = _ConnectMcuIoWorker(port, self._mcu_io_baudrate)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_io_connected)
        worker.error.connect(self._on_mcu_io_connect_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_io_connect_thread_cleanup)

        self._mcu_io_connect_worker = worker
        self._mcu_io_connect_thread = thread
        thread.start()

    def _on_mcu_io_connect_thread_cleanup(self):
        self._mcu_io_connect_thread = None
        self._mcu_io_connect_worker = None

    def _on_mcu_io_connected(self, inst, idn):
        self.mcu_io = inst
        self.is_mcu_io_connected = True
        self.set_mcu_io_status("● Connected")
        self.mcu_io_search_btn.setEnabled(False)
        self.mcu_io_connect_btn.setEnabled(True)
        update_connect_button_state(self.mcu_io_connect_btn, connected=True)
        self._set_mcu_io_gpio_controls_enabled(True)
        self._mcu_io_log(f"[MCU] Connected: {idn}")
        self.mcu_io_connection_status_changed.emit(True)

    def _on_mcu_io_connect_error(self, err):
        self.set_mcu_io_status("● Failed", is_error=True)
        self.mcu_io_search_btn.setEnabled(True)
        self.mcu_io_connect_btn.setEnabled(True)
        self._mcu_io_log(f"[MCU] Connection failed: {err}")

    def _disconnect_mcu_io(self):
        self.set_mcu_io_status("● Disconnecting")
        self.mcu_io_connect_btn.setEnabled(False)
        try:
            if self.mcu_io is not None:
                self.mcu_io.disconnect()
        except Exception as e:
            logger.error("MCU IO disconnect failed: %s", e, exc_info=True)
            self._mcu_io_log(f"[MCU] Disconnect failed: {e}")
        finally:
            self.mcu_io = None
            self.is_mcu_io_connected = False
            self.set_mcu_io_status("● Disconnected", is_error=True)
            self.mcu_io_search_btn.setEnabled(True)
            self.mcu_io_connect_btn.setEnabled(True)
            update_connect_button_state(self.mcu_io_connect_btn, connected=False)
            self._set_mcu_io_gpio_controls_enabled(False)
            self._mcu_io_log("[MCU] Disconnected.")
            self.mcu_io_connection_status_changed.emit(False)

    def _on_mcu_io_set_output(self, pin, state=None):
        if not self.is_mcu_io_connected or self.mcu_io is None:
            self._mcu_io_log("[MCU] Not connected, cannot set GPIO output.")
            return
        if self._mcu_io_output_thread is not None and self._mcu_io_output_thread.isRunning():
            return
        if state is None:
            toggle = self.mcu_io_output_toggles.get(pin)
            state = toggle.value() if toggle else GPIO_STATE_HIGHZ

        self.set_mcu_io_status(f"● Setting GPIO{pin}")
        self._mcu_io_log(f"[MCU] Setting GPIO{pin} -> {state}...")

        worker = _GpioOutputWorker(self.mcu_io, pin, state)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_io_output_done)
        worker.error.connect(self._on_mcu_io_output_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_io_output_thread_cleanup)

        self._mcu_io_output_worker = worker
        self._mcu_io_output_thread = thread
        thread.start()

    def _on_mcu_io_output_thread_cleanup(self):
        self._mcu_io_output_thread = None
        self._mcu_io_output_worker = None

    def _on_mcu_io_output_done(self, pin, state):
        self.set_mcu_io_status("● Connected")
        self._mcu_io_log(f"[MCU] GPIO{pin} set to {state}.")

    def _on_mcu_io_output_error(self, err):
        self.set_mcu_io_status("● Set Failed", is_error=True)
        self._mcu_io_log(f"[MCU] Set GPIO output failed: {err}")

    def _on_mcu_io_pulse(self, pin):
        if not self.is_mcu_io_connected or self.mcu_io is None:
            self._mcu_io_log("[MCU] Not connected, cannot pulse GPIO.")
            return
        if self._mcu_io_pulse_thread is not None and self._mcu_io_pulse_thread.isRunning():
            return

        toggle = self.mcu_io_output_toggles.get(pin)
        state = toggle.value() if toggle else GPIO_STATE_HIGH
        active = 0 if state == GPIO_STATE_LOW else 1

        spin = getattr(self, "mcu_io_pulse_width_spin", None)
        width_ms = int(round(
            spin.value() if spin else MCU_PWR_RESET_PULSE_WIDTH_DEFAULT_MS
        ))

        self.set_mcu_io_status(f"● Pulsing GPIO{pin}")
        self._mcu_io_log(
            f"[MCU] Pulsing GPIO{pin} active={active} width={width_ms}ms..."
        )

        worker = _GpioPulseWorker(self.mcu_io, pin, active, width_ms)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_io_pulse_done)
        worker.error.connect(self._on_mcu_io_pulse_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_io_pulse_thread_cleanup)

        self._mcu_io_pulse_worker = worker
        self._mcu_io_pulse_thread = thread
        thread.start()

    def _on_mcu_io_pulse_thread_cleanup(self):
        self._mcu_io_pulse_thread = None
        self._mcu_io_pulse_worker = None

    def _on_mcu_io_pulse_done(self, pin):
        self.set_mcu_io_status("● Connected")
        self._mcu_io_log(f"[MCU] GPIO{pin} pulse done.")

    def _on_mcu_io_pulse_error(self, err):
        self.set_mcu_io_status("● Pulse Failed", is_error=True)
        self._mcu_io_log(f"[MCU] Pulse GPIO failed: {err}")

    def _selected_mcu_io_read_pin(self):
        text = (
            self.mcu_io_read_combo.currentText()
            if getattr(self, "mcu_io_read_combo", None) else ""
        )
        if text and text.upper().startswith("GPIO"):
            try:
                return int(text[4:])
            except ValueError:
                return None
        return None

    def _on_mcu_io_read(self):
        if not self.is_mcu_io_connected or self.mcu_io is None:
            self._mcu_io_log("[MCU] Not connected, cannot read GPIO.")
            return
        if self._mcu_io_read_thread is not None and self._mcu_io_read_thread.isRunning():
            return
        pin = self._selected_mcu_io_read_pin()
        if pin is None:
            self._mcu_io_log("[MCU] No valid GPIO selected to read.")
            return

        self.set_mcu_io_status(f"● Reading GPIO{pin}")
        self._set_mcu_io_gpio_controls_enabled(False)
        self._mcu_io_log(f"[MCU] Reading GPIO{pin}...")

        worker = _GpioReadWorker(self.mcu_io, pin, "none")
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_io_read_done)
        worker.error.connect(self._on_mcu_io_read_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_io_read_thread_cleanup)

        self._mcu_io_read_worker = worker
        self._mcu_io_read_thread = thread
        thread.start()

    def _on_mcu_io_read_thread_cleanup(self):
        self._mcu_io_read_thread = None
        self._mcu_io_read_worker = None

    def _on_mcu_io_read_done(self, pin, value):
        level = "High" if value else "Low"
        self.mcu_io_read_value_label.setText(f"Level: {value} ({level})")
        self.set_mcu_io_status("● Connected")
        self._set_mcu_io_gpio_controls_enabled(True)
        self._mcu_io_log(f"[MCU] GPIO{pin} read = {value} ({level}).")

    def _on_mcu_io_read_error(self, err):
        self.set_mcu_io_status("● Read Failed", is_error=True)
        self._set_mcu_io_gpio_controls_enabled(True)
        self._mcu_io_log(f"[MCU] Read GPIO failed: {err}")

    def get_mcu_io_instance(self):
        return self.mcu_io

    def is_mcu_io_device_connected(self):
        return self.is_mcu_io_connected


class PolarityToggle(QWidget):
    polarity_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._options = _POLARITY_OPTIONS
        self._index = 0
        self._anim_progress = 0.0
        self._n = len(self._options)

        self.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.setFixedWidth(self._n * 26)
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

    def setValue(self, key):
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
                self.polarity_changed.emit(key)
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
                self.polarity_changed.emit(self._options[self._index]["key"])
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
        return QSize(self._n * 26, MCU_IO_BTN_HEIGHT)

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


class ModeToggle(QWidget):
    mode_changed = Signal(str)

    def __init__(self, options=None, parent=None):
        super().__init__(parent)
        self._options = options or _DRIVE_MODE_OPTIONS
        self._index = 0
        self._anim_progress = 0.0
        self._n = len(self._options)

        self.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.setFixedWidth(self._n * 36)
        self.setCursor(Qt.PointingHandCursor)

        self._bg_color = QColor("#1A2750")
        self._knob_color = QColor("#243760")
        self._text_active_color = QColor("#F3F6FF")
        self._text_inactive_color = QColor("#5F77AE")
        self._border_color = QColor("#22376A")

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def value(self):
        return self._options[self._index]["key"]

    def setValue(self, key):
        for i, opt in enumerate(self._options):
            if opt["key"] == key:
                if i == self._index:
                    return
                self._index = i
                self._anim.stop()
                self._anim.setStartValue(self._anim_progress)
                self._anim.setEndValue(float(i))
                self._anim.start()
                self.mode_changed.emit(key)
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
                self._anim.stop()
                self._anim.setStartValue(self._anim_progress)
                self._anim.setEndValue(float(clicked_idx))
                self._anim.start()
                self.mode_changed.emit(self._options[self._index]["key"])
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

        font = p.font()
        font.setPixelSize(10)
        p.setFont(font)
        for i, opt in enumerate(self._options):
            dist = abs(self._anim_progress - i)
            is_active = dist < 0.5
            color = self._text_active_color if is_active else self._text_inactive_color
            p.setPen(color)
            seg_rect = QRectF(seg_w * i, 0, seg_w, h)
            p.drawText(seg_rect, Qt.AlignCenter, opt["label"])

        p.end()

    def sizeHint(self):
        return QSize(self._n * 36, MCU_IO_BTN_HEIGHT)

    def changeEvent(self, event):
        if event.type() == event.Type.EnabledChange:
            self.setCursor(Qt.PointingHandCursor if self.isEnabled() else Qt.ArrowCursor)
            self.update()
        super().changeEvent(event)


class McuPwrResetConfigMixin(McuIoConnectionMixin):
    def init_mcu_pwr_reset_config(self, baudrate=MCU_IO_DEFAULT_BAUDRATE):
        self.init_mcu_io_connection(baudrate=baudrate)
        self._mcu_pr_pulse_thread = None
        self._mcu_pr_pulse_worker = None

    def build_mcu_pwr_reset_config_widgets(self, layout, title_row=None):
        self.build_mcu_io_connection_widgets(
            layout, title_row=title_row, with_gpio=False
        )

        label_style_sm = "font-size: 10px; color: #7e96bf;"
        label_width = 48

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)

        poweron_label = QLabel("PwrON")
        poweron_label.setStyleSheet(label_style_sm)
        poweron_label.setFixedWidth(label_width)
        self.mcu_pr_poweron_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.mcu_pr_poweron_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_pr_poweron_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.mcu_pr_poweron_combo.font()
        font.setPixelSize(11)
        self.mcu_pr_poweron_combo.setFont(font)
        for opt in MCU_PWR_RESET_GPIO_OPTIONS:
            self.mcu_pr_poweron_combo.addItem(opt)
        self._mcu_pr_select_combo(
            self.mcu_pr_poweron_combo, MCU_PWR_RESET_DEFAULTS["poweron"]
        )
        self.mcu_pr_poweron_combo.setMinimumWidth(56)
        self.mcu_pr_poweron_polarity_toggle = PolarityToggle()
        poweron_row = QHBoxLayout()
        poweron_row.setContentsMargins(0, 0, 0, 0)
        poweron_row.setSpacing(3)
        poweron_row.addWidget(self.mcu_pr_poweron_combo, 1)
        poweron_row.addWidget(self.mcu_pr_poweron_polarity_toggle, 0, Qt.AlignVCenter)
        grid.addWidget(poweron_label, 0, 0, Qt.AlignVCenter)
        grid.addLayout(poweron_row, 0, 1)

        reset_label_row = QHBoxLayout()
        reset_label_row.setContentsMargins(0, 0, 0, 0)
        reset_label_row.setSpacing(4)
        reset_label = QLabel("Reset")
        reset_label.setStyleSheet(label_style_sm)
        self.mcu_pr_reset_enable_cb = QCheckBox()
        self.mcu_pr_reset_enable_cb.setChecked(False)
        self.mcu_pr_reset_enable_cb.setToolTip(
            "Enable Reset GPIO. When unchecked, RESET step is skipped."
        )
        _cb_icons_dir = os.path.join(get_resource_base(), "resources", "icons")
        _cb_unchecked = os.path.join(
            _cb_icons_dir, "unchecked_5d45ff.svg"
        ).replace("\\", "/")
        _cb_checked = os.path.join(
            _cb_icons_dir, "checked_5d45ff.svg"
        ).replace("\\", "/")
        self.mcu_pr_reset_enable_cb.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                image: url("%s");
            }
            QCheckBox::indicator:checked {
                image: url("%s");
            }
        """ % (_cb_unchecked, _cb_checked))
        reset_label_row.addWidget(reset_label)
        reset_label_row.addWidget(self.mcu_pr_reset_enable_cb)
        reset_label_row.addStretch()
        reset_label_container = QWidget()
        reset_label_container.setFixedWidth(label_width)
        reset_label_container.setStyleSheet("background: transparent;")
        reset_label_container.setLayout(reset_label_row)

        self.mcu_pr_reset_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.mcu_pr_reset_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_pr_reset_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.mcu_pr_reset_combo.font()
        font.setPixelSize(11)
        self.mcu_pr_reset_combo.setFont(font)
        for opt in MCU_PWR_RESET_GPIO_OPTIONS:
            self.mcu_pr_reset_combo.addItem(opt)
        self._mcu_pr_select_combo(
            self.mcu_pr_reset_combo, MCU_PWR_RESET_DEFAULTS["reset"]
        )
        self.mcu_pr_reset_combo.setMinimumWidth(56)
        self.mcu_pr_reset_polarity_toggle = PolarityToggle()
        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 0, 0, 0)
        reset_row.setSpacing(3)
        reset_row.addWidget(self.mcu_pr_reset_combo, 1)
        reset_row.addWidget(self.mcu_pr_reset_polarity_toggle, 0, Qt.AlignVCenter)
        grid.addWidget(reset_label_container, 1, 0, Qt.AlignVCenter)
        grid.addLayout(reset_row, 1, 1)

        status_label_row = QHBoxLayout()
        status_label_row.setContentsMargins(0, 0, 0, 0)
        status_label_row.setSpacing(4)
        status_label = QLabel("Status")
        status_label.setStyleSheet(label_style_sm)
        self.mcu_pr_status_enable_cb = QCheckBox()
        self.mcu_pr_status_enable_cb.setChecked(False)
        self.mcu_pr_status_enable_cb.setToolTip(
            "Enable Status GPIO to control DUT sleep/wakeup state. "
            "When unchecked, Status step is skipped."
        )
        self.mcu_pr_status_enable_cb.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                image: url("%s");
            }
            QCheckBox::indicator:checked {
                image: url("%s");
            }
        """ % (_cb_unchecked, _cb_checked))
        status_label_row.addWidget(status_label)
        status_label_row.addWidget(self.mcu_pr_status_enable_cb)
        status_label_row.addStretch()
        status_label_container = QWidget()
        status_label_container.setFixedWidth(label_width)
        status_label_container.setStyleSheet("background: transparent;")
        status_label_container.setLayout(status_label_row)

        self.mcu_pr_status_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.mcu_pr_status_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_pr_status_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.mcu_pr_status_combo.font()
        font.setPixelSize(11)
        self.mcu_pr_status_combo.setFont(font)
        for opt in MCU_PWR_RESET_GPIO_OPTIONS:
            self.mcu_pr_status_combo.addItem(opt)
        self._mcu_pr_select_combo(
            self.mcu_pr_status_combo, MCU_PWR_RESET_DEFAULTS["status"]
        )
        self.mcu_pr_status_combo.setMinimumWidth(56)
        self.mcu_pr_status_polarity_toggle = PolarityToggle()
        self.mcu_pr_status_mode_toggle = ModeToggle()
        self.mcu_pr_status_mode_toggle.setToolTip(
            "Pulse: send a single pulse. Level: hold the active level until changed."
        )
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(3)
        status_row.addWidget(self.mcu_pr_status_combo, 1)
        status_row.addWidget(self.mcu_pr_status_polarity_toggle, 0, Qt.AlignVCenter)
        status_row.addWidget(self.mcu_pr_status_mode_toggle, 0, Qt.AlignVCenter)
        grid.addWidget(status_label_container, 2, 0, Qt.AlignVCenter)
        grid.addLayout(status_row, 2, 1)

        pulse_width_label = QLabel("Pulse (ms)")
        pulse_width_label.setStyleSheet(label_style_sm)
        pulse_width_label.setFixedWidth(label_width)
        self.mcu_pr_pulse_width_spin = QDoubleSpinBox()
        self.mcu_pr_pulse_width_spin.setObjectName("mcuPrPulseWidthSpin")
        self.mcu_pr_pulse_width_spin.setDecimals(1)
        self.mcu_pr_pulse_width_spin.setRange(
            MCU_PWR_RESET_PULSE_WIDTH_MIN_MS, MCU_PWR_RESET_PULSE_WIDTH_MAX_MS
        )
        self.mcu_pr_pulse_width_spin.setSingleStep(10.0)
        self.mcu_pr_pulse_width_spin.setValue(MCU_PWR_RESET_PULSE_WIDTH_DEFAULT_MS)
        self.mcu_pr_pulse_width_spin.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        font = self.mcu_pr_pulse_width_spin.font()
        font.setPixelSize(11)
        self.mcu_pr_pulse_width_spin.setFont(font)
        self.mcu_pr_pulse_width_spin.setToolTip(
            "Pulse width in milliseconds. Applies to PowerON / RESET / Status "
            "pulse actions."
        )
        self.mcu_pr_pulse_width_spin.setStyleSheet(f"""
            QDoubleSpinBox#mcuPrPulseWidthSpin {{
                background-color: #091426;
                border: 1.5px solid #17345f;
                border-radius: 6px;
                color: #c8d5e2;
                padding: 2px 8px;
                min-height: {MCU_IO_BTN_HEIGHT}px;
                max-height: {MCU_IO_BTN_HEIGHT}px;
            }}
            QDoubleSpinBox#mcuPrPulseWidthSpin:focus {{
                border: 1.5px solid #2dd4ff;
            }}
            QDoubleSpinBox#mcuPrPulseWidthSpin::up-button,
            QDoubleSpinBox#mcuPrPulseWidthSpin::down-button {{
                width: 0px;
                height: 0px;
                border: none;
            }}
            QDoubleSpinBox#mcuPrPulseWidthSpin:disabled {{
                background-color: #0b1430;
                color: #5c7096;
                border: 1.5px solid #1a2850;
            }}
        """)
        pulse_width_row = QHBoxLayout()
        pulse_width_row.setContentsMargins(0, 0, 0, 0)
        pulse_width_row.setSpacing(3)
        pulse_width_row.addWidget(self.mcu_pr_pulse_width_spin, 1)
        grid.addWidget(pulse_width_label, 3, 0, Qt.AlignVCenter)
        grid.addLayout(pulse_width_row, 3, 1)

        layout.addLayout(grid)

        self.mcu_pr_reset_enable_cb.toggled.connect(
            self._on_mcu_pr_reset_enable_toggled
        )
        self._on_mcu_pr_reset_enable_toggled(self.mcu_pr_reset_enable_cb.isChecked())
        self.mcu_pr_status_enable_cb.toggled.connect(
            self._on_mcu_pr_status_enable_toggled
        )
        self._on_mcu_pr_status_enable_toggled(
            self.mcu_pr_status_enable_cb.isChecked()
        )

        self.bind_mcu_io_signals()

    @staticmethod
    def _mcu_pr_select_combo(combo, desired):
        if combo is None or not desired:
            return
        for i in range(combo.count()):
            if combo.itemText(i) == desired:
                combo.setCurrentIndex(i)
                return

    def _on_mcu_pr_reset_enable_toggled(self, checked):
        if getattr(self, "mcu_pr_reset_combo", None) is not None:
            self.mcu_pr_reset_combo.setEnabled(checked)
        if getattr(self, "mcu_pr_reset_polarity_toggle", None) is not None:
            self.mcu_pr_reset_polarity_toggle.setEnabled(checked)

    def _on_mcu_pr_status_enable_toggled(self, checked):
        if getattr(self, "mcu_pr_status_combo", None) is not None:
            self.mcu_pr_status_combo.setEnabled(checked)
        if getattr(self, "mcu_pr_status_polarity_toggle", None) is not None:
            self.mcu_pr_status_polarity_toggle.setEnabled(checked)
        if getattr(self, "mcu_pr_status_mode_toggle", None) is not None:
            self.mcu_pr_status_mode_toggle.setEnabled(checked)

    def get_mcu_pwr_reset_config(self):
        reset_enabled = self.mcu_pr_reset_enable_cb.isChecked()
        status_enabled = self.mcu_pr_status_enable_cb.isChecked()
        return {
            "poweron_channel": self.mcu_pr_poweron_combo.currentText(),
            "poweron_polarity": self.mcu_pr_poweron_polarity_toggle.value(),
            "reset_enabled": reset_enabled,
            "reset_channel": (
                self.mcu_pr_reset_combo.currentText() if reset_enabled else None
            ),
            "reset_polarity": (
                self.mcu_pr_reset_polarity_toggle.value() if reset_enabled else None
            ),
            "status_enabled": status_enabled,
            "status_channel": (
                self.mcu_pr_status_combo.currentText() if status_enabled else None
            ),
            "status_polarity": (
                self.mcu_pr_status_polarity_toggle.value() if status_enabled else None
            ),
            "status_mode": (
                self.mcu_pr_status_mode_toggle.value() if status_enabled else None
            ),
            "pulse_width": self.get_mcu_pr_pulse_width(),
        }

    def get_mcu_pr_pulse_width(self):
        spin = getattr(self, "mcu_pr_pulse_width_spin", None)
        if spin is None:
            return MCU_PWR_RESET_PULSE_WIDTH_DEFAULT_MS / 1000.0
        return spin.value() / 1000.0

    @staticmethod
    def _mcu_pr_pin_index(channel):
        if not channel:
            return None
        try:
            return int(str(channel).upper().replace("GPIO", "").strip())
        except (ValueError, AttributeError):
            return None

    def _mcu_pr_run_pulses(self, actions, pulse_width=0.1, on_done=None):
        if not self.is_mcu_io_connected or self.mcu_io is None:
            self._mcu_io_log("[MCU] Not connected, cannot drive PWR/RESET.")
            return False
        if (
            self._mcu_pr_pulse_thread is not None
            and self._mcu_pr_pulse_thread.isRunning()
        ):
            self._mcu_io_log("[MCU] PWR/RESET pulse busy, ignored.")
            return False

        names = ", ".join(f"{n}(GPIO{p},{pol})" for n, p, pol in actions)
        self.set_mcu_io_status("● Pulsing PWR/RESET")
        self._mcu_io_log(f"[MCU] PWR/RESET pulse: {names}")

        worker = _PwrResetPulseWorker(self.mcu_io, actions, pulse_width=pulse_width)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_pr_pulse_done)
        worker.error.connect(self._on_mcu_pr_pulse_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_pr_pulse_thread_cleanup)
        if on_done is not None:
            worker.finished.connect(lambda _result: on_done())

        self._mcu_pr_pulse_worker = worker
        self._mcu_pr_pulse_thread = thread
        thread.start()
        return True

    def _on_mcu_pr_pulse_thread_cleanup(self):
        self._mcu_pr_pulse_thread = None
        self._mcu_pr_pulse_worker = None

    def _on_mcu_pr_pulse_done(self, _result):
        self.set_mcu_io_status("● Connected")
        self._mcu_io_log("[MCU] PWR/RESET pulse done.")

    def _on_mcu_pr_pulse_error(self, err):
        self.set_mcu_io_status("● Pulse Failed", is_error=True)
        self._mcu_io_log(f"[MCU] PWR/RESET pulse failed: {err}")

    def _mcu_pr_run_level(self, name, pin, level, on_done=None):
        if not self.is_mcu_io_connected or self.mcu_io is None:
            self._mcu_io_log("[MCU] Not connected, cannot set level.")
            return False
        if (
            self._mcu_pr_pulse_thread is not None
            and self._mcu_pr_pulse_thread.isRunning()
        ):
            self._mcu_io_log("[MCU] PWR/RESET busy, ignored.")
            return False

        self.set_mcu_io_status(f"● Setting {name}")
        self._mcu_io_log(f"[MCU] {name} hold level GPIO{pin} -> {level}")

        worker = _LevelSetWorker(self.mcu_io, name, pin, level)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_pr_pulse_done)
        worker.error.connect(self._on_mcu_pr_pulse_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_pr_pulse_thread_cleanup)
        if on_done is not None:
            worker.finished.connect(lambda _result: on_done())

        self._mcu_pr_pulse_worker = worker
        self._mcu_pr_pulse_thread = thread
        thread.start()
        return True

    def mcu_power_on(self, pulse_width=None, on_done=None):
        cfg = self.get_mcu_pwr_reset_config()
        if pulse_width is None:
            pulse_width = cfg["pulse_width"]
        pin = self._mcu_pr_pin_index(cfg["poweron_channel"])
        if pin is None:
            self._mcu_io_log("[MCU] Invalid PowerON channel.")
            return False
        return self._mcu_pr_run_pulses(
            [("PowerON", pin, cfg["poweron_polarity"])],
            pulse_width=pulse_width,
            on_done=on_done,
        )

    def mcu_reset(self, pulse_width=None, on_done=None):
        cfg = self.get_mcu_pwr_reset_config()
        if pulse_width is None:
            pulse_width = cfg["pulse_width"]
        if not cfg["reset_enabled"]:
            self._mcu_io_log("[MCU] RESET disabled, skipped.")
            return False
        pin = self._mcu_pr_pin_index(cfg["reset_channel"])
        if pin is None:
            self._mcu_io_log("[MCU] Invalid RESET channel.")
            return False
        return self._mcu_pr_run_pulses(
            [("RESET", pin, cfg["reset_polarity"])],
            pulse_width=pulse_width,
            on_done=on_done,
        )

    def mcu_status_toggle(self, pulse_width=None, on_done=None):
        cfg = self.get_mcu_pwr_reset_config()
        if pulse_width is None:
            pulse_width = cfg["pulse_width"]
        if not cfg["status_enabled"]:
            self._mcu_io_log("[MCU] Status disabled, skipped.")
            return False
        pin = self._mcu_pr_pin_index(cfg["status_channel"])
        if pin is None:
            self._mcu_io_log("[MCU] Invalid Status channel.")
            return False
        if cfg["status_mode"] == MCU_DRIVE_MODE_LEVEL:
            self._mcu_io_log(
                "[MCU] Status is in Level mode; use mcu_set_status(active=...) instead."
            )
            return False
        return self._mcu_pr_run_pulses(
            [("Status", pin, cfg["status_polarity"])],
            pulse_width=pulse_width,
            on_done=on_done,
        )

    def mcu_set_status(self, active=True, on_done=None):
        cfg = self.get_mcu_pwr_reset_config()
        if not cfg["status_enabled"]:
            self._mcu_io_log("[MCU] Status disabled, skipped.")
            return False
        pin = self._mcu_pr_pin_index(cfg["status_channel"])
        if pin is None:
            self._mcu_io_log("[MCU] Invalid Status channel.")
            return False
        active_level = 1 if cfg["status_polarity"] == "rising" else 0
        level = active_level if active else (1 - active_level)
        return self._mcu_pr_run_level(
            "Status", pin, level, on_done=on_done
        )

    def mcu_power_on_reset_sequence(self, pulse_width=None, on_done=None):
        cfg = self.get_mcu_pwr_reset_config()
        if pulse_width is None:
            pulse_width = cfg["pulse_width"]
        poweron_pin = self._mcu_pr_pin_index(cfg["poweron_channel"])
        if poweron_pin is None:
            self._mcu_io_log("[MCU] Invalid PowerON channel.")
            return False
        actions = [("PowerON", poweron_pin, cfg["poweron_polarity"])]
        if cfg["reset_enabled"]:
            reset_pin = self._mcu_pr_pin_index(cfg["reset_channel"])
            if reset_pin is not None:
                actions.append(("RESET", reset_pin, cfg["reset_polarity"]))
        return self._mcu_pr_run_pulses(
            actions, pulse_width=pulse_width, on_done=on_done
        )


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
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

    class _DemoIoWidget(McuIoConnectionMixin, QWidget):
        mcu_io_connection_status_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_mcu_io_connection()
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            card = _CardFrame("MCU IO")
            self.build_mcu_io_connection_widgets(
                card.main_layout, title_row=card.title_row)
            root.addWidget(card)

            self.bind_mcu_io_signals()

        def append_log(self, msg):
            logger.info(msg)

    class _DemoPwrResetWidget(McuPwrResetConfigMixin, QWidget):
        mcu_io_connection_status_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_mcu_pwr_reset_config()
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            card = _CardFrame("MCU PWR / RESET")
            self.build_mcu_pwr_reset_config_widgets(
                card.main_layout, title_row=card.title_row)
            root.addWidget(card)

        def append_log(self, msg):
            logger.info(msg)

    class _DemoWindow(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setStyleSheet(DARK_CARD_STYLE)
            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)
            root.setSpacing(12)
            root.addWidget(_DemoIoWidget())
            root.addWidget(_DemoPwrResetWidget())
            root.addStretch()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = _DemoWindow()
    w.setWindowTitle("MCU IO Mixin Card")
    resize_and_center_window(w)
    w.show()

    sys.exit(app.exec())
