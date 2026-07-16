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
    QLabel, QFrame, QSizePolicy, QToolTip, QCheckBox, QDoubleSpinBox,
    QScrollArea
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

# CH9114F 可用 GPIO 引脚（与 instruments/MCU_IO/ch9114f.py / ch9114f_gpio_module_frame.py 保持一致）
CH9114F_GPIO_PINS = (0, 1, 6, 7, 2, 8, 14, 20)
CH9114F_GPIO_OPTIONS = tuple(f"GPIO{i}" for i in CH9114F_GPIO_PINS)

MCU_TYPE_YD_RP2040 = "yd_rp2040"
MCU_TYPE_CH9114F = "ch9114f"
MCU_TYPE_LABELS = {
    MCU_TYPE_YD_RP2040: "YD-RP2040",
    MCU_TYPE_CH9114F: "CH9114F",
}

GPIO_STATE_HIGH = "High"
GPIO_STATE_LOW = "Low"
GPIO_STATE_HIGHZ = "HighZ"
GPIO_OUTPUT_STATES = (GPIO_STATE_HIGH, GPIO_STATE_LOW, GPIO_STATE_HIGHZ)

_GPIO_LEVEL_OPTIONS = [
    {"key": GPIO_STATE_HIGH, "label": "High", "svg": os.path.join(_PAGE_SVGS_DIR, "level_high.svg"), "active_color": "#34d399"},
    {"key": GPIO_STATE_LOW, "label": "Low", "svg": os.path.join(_PAGE_SVGS_DIR, "level_low.svg"), "active_color": "#fb7185"},
    {"key": GPIO_STATE_HIGHZ, "label": "High-Z", "svg": os.path.join(_PAGE_SVGS_DIR, "x-circle.svg"), "active_color": "#e2e8f0"},
]

MCU_PWR_RESET_GPIO_OPTIONS = tuple(f"GPIO{i}" for i in range(0, 30))

MCU_PWR_RESET_DEFAULTS = {
    "poweron": "GPIO0",
    "reset": "GPIO1",
    "status": "GPIO2",
    "ctrl": "GPIO3",
}

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

        self._bg_color = QColor("#020817")
        self._knob_color = QColor("#334155")
        self._icon_active_color = QColor("#F3F6FF")
        self._icon_inactive_color = QColor("#64748b")
        self._border_color = QColor("#1e293b")

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
            if is_active:
                color = QColor(opt.get("active_color", "#e2e8f0"))
            else:
                color = self._icon_inactive_color
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
    # Qt QSS box model: total = content(min-height) + padding(v)*2 + border*2
    # 想要 total = h, border=1px*2=2, padding(v)=0 => content = h - 2
    content_h = h - 2
    return f"""
        QPushButton {{
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            color: #e2e8f0;
            font-weight: 600;
            min-height: {content_h}px;
            max-height: {content_h}px;
            padding: 0px 8px;
        }}
        QPushButton:hover {{
            background-color: #334155;
            border: 1px solid #475569;
        }}
        QPushButton:pressed {{
            background-color: #0f172a;
        }}
        QPushButton:disabled {{
            background-color: #0b1430;
            color: #5c7096;
            border: 1px solid #1a2850;
        }}
    """


def _mcu_io_toggle_style(h=MCU_IO_BTN_HEIGHT):
    content_h = h - 2
    return f"""
        QPushButton {{
            background-color: rgba(99, 102, 241, 0.10);
            border: 1px solid rgba(99, 102, 241, 0.25);
            border-radius: 6px;
            color: #818cf8;
            font-weight: 600;
            min-height: {content_h}px;
            max-height: {content_h}px;
            padding: 0px 8px;
        }}
        QPushButton:hover {{
            background-color: rgba(99, 102, 241, 0.20);
            border: 1px solid rgba(99, 102, 241, 0.45);
            color: #a5b4fc;
        }}
        QPushButton:pressed {{
            background-color: rgba(99, 102, 241, 0.08);
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

    def __init__(self, mcu_type=MCU_TYPE_YD_RP2040):
        super().__init__()
        self._mcu_type = mcu_type

    def run(self):
        try:
            if self._mcu_type == MCU_TYPE_CH9114F:
                from instruments.MCU_IO.ch9114f import list_ch9114f_ports
                ports = list_ch9114f_ports() or []
                self.finished.emit(list(ports))
            else:
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                self.finished.emit(
                    [f"{p.device} - {p.description}" for p in ports]
                )
        except Exception as e:
            logger.error("MCU IO port scan failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _ConnectMcuIoWorker(QObject):
    finished = Signal(object, str)
    error = Signal(str)

    def __init__(self, port, mcu_type=MCU_TYPE_YD_RP2040,
                 baudrate=MCU_IO_DEFAULT_BAUDRATE):
        super().__init__()
        self._port = port
        self._mcu_type = mcu_type
        self._baudrate = baudrate

    def run(self):
        try:
            from instruments.factory import create_mcu_io
            inst = create_mcu_io(
                self._mcu_type, port=self._port, baudrate=self._baudrate
            )
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


class _GpioDefaultHighZWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, inst, pins):
        super().__init__()
        self._inst = inst
        self._pins = list(pins)

    def run(self):
        try:
            for pin in self._pins:
                self._inst.in_pull(pin, "none")
            self.finished.emit(self._pins)
        except Exception as e:
            logger.error("MCU IO default High-Z failed: %s", e, exc_info=True)
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

    def init_mcu_io_connection(self, baudrate=MCU_IO_DEFAULT_BAUDRATE,
                               instrument_manager=None):
        self.mcu_io = None
        self.is_mcu_io_connected = False
        self._mcu_io_baudrate = baudrate
        self._mcu_io_manager = instrument_manager
        self._mcu_io_session_id = "mcu_io:default"
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
        self._mcu_io_default_thread = None
        self._mcu_io_default_worker = None
        # MCU 类型默认 YD-RP2040；切换由 mcu_type_combo 触发
        self._mcu_io_type = MCU_TYPE_YD_RP2040

    def _current_mcu_io_type(self):
        """返回当前 MCU IO 类型 (yd_rp2040 / ch9114f)。

        优先读取 mcu_type_combo 的 currentData()，回退到 _mcu_io_type。
        """
        combo = getattr(self, "mcu_io_type_combo", None)
        if combo is not None:
            data = combo.currentData()
            if data in (MCU_TYPE_YD_RP2040, MCU_TYPE_CH9114F):
                return data
        return getattr(self, "_mcu_io_type", MCU_TYPE_YD_RP2040)

    def _get_mcu_io_gpio_pins(self):
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return CH9114F_GPIO_PINS
        return MCU_IO_GPIO_PINS

    def _get_mcu_io_gpio_options(self):
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return CH9114F_GPIO_OPTIONS
        return MCU_IO_GPIO_OPTIONS

    def _get_mcu_io_port_placeholder(self):
        return (
            "Select CH9114F COM..."
            if self._current_mcu_io_type() == MCU_TYPE_CH9114F
            else "Select MCU COM..."
        )

    def _get_mcu_io_not_found_text(self):
        return (
            "No CH9114F ports found"
            if self._current_mcu_io_type() == MCU_TYPE_CH9114F
            else "No serial ports found"
        )

    def build_mcu_io_connection_widgets(self, layout, title_row=None, with_gpio=True):
        # MCU Type 下拉（YD-RP2040 / CH9114F）
        type_row = QHBoxLayout()
        type_row.setSpacing(6)
        type_row.setContentsMargins(0, 2, 0, 0)
        type_label = QLabel("MCU Type")
        type_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        type_label.setFixedWidth(64)
        self.mcu_io_type_combo = DarkComboBox(bg="#020817", border="#1e293b")
        self.mcu_io_type_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_io_type_combo.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed
        )
        self.mcu_io_type_combo.addItem("YD-RP2040", userData=MCU_TYPE_YD_RP2040)
        self.mcu_io_type_combo.addItem("CH9114F", userData=MCU_TYPE_CH9114F)
        font = self.mcu_io_type_combo.font()
        font.setPixelSize(11)
        self.mcu_io_type_combo.setFont(font)
        type_row.addWidget(type_label, 0, Qt.AlignVCenter)
        type_row.addWidget(self.mcu_io_type_combo, 1)
        layout.addLayout(type_row)

        self.mcu_io_status_label = QLabel("● Disconnected")
        self.mcu_io_status_label.setObjectName("statusErr")
        if title_row is not None:
            title_row.addWidget(self.mcu_io_status_label)
        else:
            layout.addWidget(self.mcu_io_status_label)

        self.mcu_io_port_combo = DarkComboBox(bg="#020817", border="#1e293b")
        self.mcu_io_port_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.mcu_io_port_combo.setMinimumContentsLength(10)
        self.mcu_io_port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mcu_io_port_combo.addItem(self._get_mcu_io_port_placeholder())
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
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet(
                "QFrame { border: none; border-top: 1px solid #1e293b; "
                "background: transparent; max-height: 1px; }"
            )
            layout.addWidget(sep)
            self._build_mcu_io_gpio_widgets(layout)

    def _build_mcu_io_gpio_widgets(self, layout):
        # GPIO 行放进容器，便于切换 MCU 类型时整体重建
        self._mcu_io_gpio_parent_layout = layout
        self.mcu_io_gpio_container = QWidget()
        self.mcu_io_gpio_container.setStyleSheet("background: transparent; border: none;")
        self.mcu_io_gpio_container.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        container_layout = QVBoxLayout(self.mcu_io_gpio_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        self._populate_mcu_io_gpio_widgets(container_layout)
        layout.addWidget(self.mcu_io_gpio_container)
        self._set_mcu_io_gpio_controls_enabled(False)

    def _populate_mcu_io_gpio_widgets(self, container_layout):
        pins = self._get_mcu_io_gpio_pins()
        options = self._get_mcu_io_gpio_options()
        self.mcu_io_output_toggles = {}
        self.mcu_io_pulse_buttons = {}
        self.mcu_io_toggle_buttons = {}

        # ---- Pulse 宽度全局设置（置于 GPIO 列表上方）----
        pulse_width_row = QHBoxLayout()
        pulse_width_row.setSpacing(6)
        pulse_width_row.setContentsMargins(0, 2, 0, 4)
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
                background-color: #020817;
                border: 1px solid #1e293b;
                border-radius: 6px;
                color: #e2e8f0;
                padding: 0px 8px;
                min-height: {MCU_IO_BTN_HEIGHT - 2}px;
                max-height: {MCU_IO_BTN_HEIGHT - 2}px;
            }}
            QDoubleSpinBox#mcuIoPulseWidthSpin:focus {{
                border: 1px solid #34d399;
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
                border: 1px solid #1a2850;
            }}
        """)
        pulse_width_row.addWidget(self.mcu_io_pulse_width_spin, 1, Qt.AlignVCenter)
        container_layout.addLayout(pulse_width_row)

        # ---- GPIO 列表（可滚动区域）----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: #020817; width: 6px; border: none; }"
            "QScrollBar::handle:vertical { background: #334155; border-radius: 3px; }"
            "QScrollBar::handle:vertical:hover { background: #475569; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        list_widget = QWidget()
        list_widget.setStyleSheet("background: transparent;")
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        for pin in pins:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 2, 0, 2)

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
                "toggle (High/Low); width uses the Pulse (ms) value above."
            )
            pulse_btn.clicked.connect(lambda _=False, p=pin: self._on_mcu_io_pulse(p))
            row.addWidget(pulse_btn, 0, Qt.AlignVCenter)

            toggle_btn = QPushButton("Toggle")
            toggle_btn.setFixedHeight(MCU_IO_BTN_HEIGHT)
            toggle_btn.setFixedWidth(60)
            toggle_btn.setStyleSheet(_mcu_io_toggle_style())
            toggle_btn.setToolTip(
                "Toggle the GPIO output level between High and Low. "
                "If currently High, switches to Low; otherwise switches to High."
            )
            toggle_btn.clicked.connect(lambda _=False, p=pin: self._on_mcu_io_toggle(p))
            row.addWidget(toggle_btn, 0, Qt.AlignVCenter)

            row.addStretch(1)

            list_layout.addLayout(row)
            self.mcu_io_output_toggles[pin] = state_toggle
            self.mcu_io_pulse_buttons[pin] = pulse_btn
            self.mcu_io_toggle_buttons[pin] = toggle_btn

        scroll.setWidget(list_widget)
        container_layout.addWidget(scroll, 1)

        # ---- Footer 分隔线 ----
        footer_sep = QFrame()
        footer_sep.setFrameShape(QFrame.HLine)
        footer_sep.setStyleSheet(
            "QFrame { border: none; border-top: 1px solid #1e293b; "
            "background: transparent; max-height: 1px; }"
        )
        container_layout.addWidget(footer_sep)

        # ---- Footer: 读取区域 ----
        read_row = QHBoxLayout()
        read_row.setSpacing(6)
        read_row.setContentsMargins(0, 4, 0, 2)

        self.mcu_io_read_combo = DarkComboBox(bg="#020817", border="#1e293b")
        self.mcu_io_read_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mcu_io_read_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        for opt in options:
            self.mcu_io_read_combo.addItem(opt)
        read_row.addWidget(self.mcu_io_read_combo, 1, Qt.AlignVCenter)

        self.mcu_io_read_btn = QPushButton("Read")
        self.mcu_io_read_btn.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_io_read_btn.setFixedWidth(64)
        self.mcu_io_read_btn.setStyleSheet(_mcu_io_action_style())
        read_row.addWidget(self.mcu_io_read_btn, 0, Qt.AlignVCenter)

        self.mcu_io_read_value_label = QLabel("—")
        self.mcu_io_read_value_label.setFixedWidth(80)
        self.mcu_io_read_value_label.setObjectName("mcuReadDefault")
        self.mcu_io_read_value_label.setAlignment(Qt.AlignCenter)
        self.mcu_io_read_value_label.setStyleSheet(
            "color: #64748b; font-weight: 700; background: transparent;"
        )
        read_row.addWidget(self.mcu_io_read_value_label, 0, Qt.AlignVCenter)

        container_layout.addLayout(read_row)

    def _rebuild_mcu_io_gpio_widgets(self):
        """切换 MCU 类型后重建 GPIO 行：删除旧容器，新建容器加到原父 layout。"""
        parent_layout = getattr(self, "_mcu_io_gpio_parent_layout", None)
        if parent_layout is None:
            return
        old_container = getattr(self, "mcu_io_gpio_container", None)
        if old_container is not None:
            parent_layout.removeWidget(old_container)
            old_container.deleteLater()
        self.mcu_io_gpio_container = QWidget()
        self.mcu_io_gpio_container.setStyleSheet(
            "background: transparent; border: none;"
        )
        container_layout = QVBoxLayout(self.mcu_io_gpio_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        self._populate_mcu_io_gpio_widgets(container_layout)
        parent_layout.addWidget(self.mcu_io_gpio_container)
        self._set_mcu_io_gpio_controls_enabled(self.is_mcu_io_connected)

    def set_mcu_io_instrument_manager(self, instrument_manager):
        self._mcu_io_manager = instrument_manager
        self._bind_mcu_io_manager_signals()
        self._sync_mcu_io_from_manager()

    def _bind_mcu_io_manager_signals(self):
        manager = getattr(self, "_mcu_io_manager", None)
        if manager is None or getattr(self, "_mcu_io_manager_bound", False):
            return
        manager.session_connected.connect(self._on_mcu_io_manager_session_connected)
        manager.session_disconnected.connect(
            self._on_mcu_io_manager_session_disconnected
        )
        manager.connection_failed.connect(self._on_mcu_io_manager_connect_failed)
        manager.scan_finished.connect(self._on_mcu_io_manager_scan_finished)
        manager.scan_failed.connect(self._on_mcu_io_manager_scan_failed)
        self._mcu_io_manager_bound = True

    def bind_mcu_io_signals(self):
        self.mcu_io_search_btn.clicked.connect(self._on_mcu_io_search)
        self.mcu_io_connect_btn.clicked.connect(
            self._on_mcu_io_connect_or_disconnect
        )
        if getattr(self, "mcu_io_type_combo", None) is not None:
            self.mcu_io_type_combo.currentIndexChanged.connect(
                self._on_mcu_io_type_changed
            )
        if getattr(self, "mcu_io_read_btn", None) is not None:
            self.mcu_io_read_btn.clicked.connect(self._on_mcu_io_read)
        self._bind_mcu_io_manager_signals()
        self._sync_mcu_io_from_manager()

    def _on_mcu_io_type_changed(self, _idx=None):
        """切换 MCU 类型（YD-RP2040 / CH9114F）。"""
        if getattr(self, "is_mcu_io_connected", False) and self.mcu_io is not None:
            self._mcu_io_log(
                "[MCU] Type changed while connected. Please reconnect to apply."
            )
        # 刷新端口下拉占位符
        if hasattr(self, "mcu_io_port_combo") and self.mcu_io_port_combo is not None:
            self.mcu_io_port_combo.clear()
            self.mcu_io_port_combo.setEnabled(True)
            self.mcu_io_port_combo.addItem(self._get_mcu_io_port_placeholder())
            self.mcu_io_connect_btn.setEnabled(False)
        # 重建 GPIO 行
        self._rebuild_mcu_io_gpio_widgets()
        # 子类（McuPwrResetConfigMixin）可覆盖此钩子刷新 PwrON/Reset/Status
        hook = getattr(self, "_on_mcu_io_type_changed_extra", None)
        if callable(hook):
            hook()

    def _set_mcu_io_gpio_controls_enabled(self, enabled: bool):
        for toggle in getattr(self, "mcu_io_output_toggles", {}).values():
            toggle.setEnabled(enabled)
        for btn in getattr(self, "mcu_io_pulse_buttons", {}).values():
            btn.setEnabled(enabled)
        for btn in getattr(self, "mcu_io_toggle_buttons", {}).values():
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
        if not text:
            return None
        # 兼容占位符 / 未找到提示 / YD-RP2040 "COMxx - desc" / CH9114F "COMxx"
        placeholders = (
            "Select MCU COM...",
            "Select CH9114F COM...",
            "No serial ports found",
            "No CH9114F ports found",
        )
        if text in placeholders:
            return None
        return text.split()[0]

    def _on_mcu_io_search(self):
        mcu_type = self._current_mcu_io_type()
        type_label = MCU_TYPE_LABELS.get(mcu_type, mcu_type)
        is_ch9114f = mcu_type == MCU_TYPE_CH9114F

        if getattr(self, "_mcu_io_manager", None) is not None:
            self.set_mcu_io_status("● Searching")
            self._mcu_io_log(
                f"[MCU] Scanning for {type_label} ports..."
            )
            self.mcu_io_search_btn.setEnabled(False)
            self.mcu_io_connect_btn.setEnabled(False)
            # 走 InstrumentManager 时仅支持 YD-RP2040（serial_raw_repl）；
            # CH9114F 走本地 worker 扫描
            if not is_ch9114f:
                self._mcu_io_manager.scan_async("mcu_io")
                return

        if DEBUG_MOCK:
            self.mcu_io_port_combo.clear()
            mock_label = (
                "[MOCK] COM99 - Mock CH9114F"
                if is_ch9114f else "[MOCK] COM98 - Mock YD RP2040"
            )
            self.mcu_io_port_combo.addItem(mock_label)
            self.mcu_io_port_combo.setEnabled(True)
            self.set_mcu_io_status("● Mock Ready")
            self.mcu_io_connect_btn.setEnabled(True)
            self._mcu_io_log("[DEBUG] Mock MCU IO port loaded, skip real scan.")
            return

        if self._mcu_io_search_thread is not None and self._mcu_io_search_thread.isRunning():
            return

        self.set_mcu_io_status("● Searching")
        self._mcu_io_log(f"[MCU] Scanning for {type_label} ports...")
        self.mcu_io_search_btn.setEnabled(False)
        self.mcu_io_connect_btn.setEnabled(False)

        worker = _SearchMcuIoWorker(mcu_type=mcu_type)
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
        mcu_type = self._current_mcu_io_type()
        type_label = MCU_TYPE_LABELS.get(mcu_type, mcu_type)
        self.mcu_io_port_combo.clear()
        self.mcu_io_port_combo.setEnabled(True)
        if ports:
            for port in ports:
                self.mcu_io_port_combo.addItem(port)
            self.set_mcu_io_status(f"● Found {len(ports)}")
            self._mcu_io_log(f"[MCU] Found {len(ports)} {type_label} port(s).")
        else:
            self.mcu_io_port_combo.addItem(self._get_mcu_io_not_found_text())
            self.mcu_io_port_combo.setEnabled(False)
            self.set_mcu_io_status("● Not Found", is_error=True)
            self._mcu_io_log(f"[MCU] No {type_label} ports found.")
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

        mcu_type = self._current_mcu_io_type()
        type_label = MCU_TYPE_LABELS.get(mcu_type, mcu_type)

        manager = getattr(self, "_mcu_io_manager", None)
        if manager is not None and mcu_type == MCU_TYPE_YD_RP2040:
            # 走 InstrumentManager 仅支持 YD-RP2040（serial_raw_repl）；
            # CH9114F 走本地 worker
            existing = manager.get_session(self._mcu_io_session_id)
            if existing and existing.connected:
                self._sync_mcu_io_from_manager()
                return
            self.set_mcu_io_status("● Connecting")
            self.mcu_io_search_btn.setEnabled(False)
            self.mcu_io_connect_btn.setEnabled(False)
            self._mcu_io_log(f"[MCU] Connecting {type_label} on {port}...")
            from core.instruments import InstrumentSpec
            manager.connect_async(InstrumentSpec(
                instrument_type="mcu_io",
                role="mcu_io",
                connection_kind="serial_raw_repl",
                slot="default",
                resource=port,
            ))
            return

        if self._mcu_io_connect_thread is not None and self._mcu_io_connect_thread.isRunning():
            return

        self.set_mcu_io_status("● Connecting")
        self.mcu_io_search_btn.setEnabled(False)
        self.mcu_io_connect_btn.setEnabled(False)
        self._mcu_io_log(f"[MCU] Connecting {type_label} on {port}...")

        worker = _ConnectMcuIoWorker(
            port, mcu_type=mcu_type, baudrate=self._mcu_io_baudrate
        )
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
        self._apply_mcu_io_connected_ui()
        self._mcu_io_log(f"[MCU] Connected: {idn}")
        self.mcu_io_connection_status_changed.emit(True)
        self._apply_default_gpio_highz()

    def _apply_mcu_io_connected_ui(self):
        self.is_mcu_io_connected = True
        self.set_mcu_io_status("● Connected")
        self.mcu_io_search_btn.setEnabled(False)
        self.mcu_io_connect_btn.setEnabled(True)
        update_connect_button_state(self.mcu_io_connect_btn, connected=True)
        self._set_mcu_io_gpio_controls_enabled(True)

    def _apply_mcu_io_disconnected_ui(self):
        self.mcu_io = None
        self.is_mcu_io_connected = False
        self.set_mcu_io_status("● Disconnected", is_error=True)
        self.mcu_io_search_btn.setEnabled(True)
        self.mcu_io_connect_btn.setEnabled(True)
        update_connect_button_state(self.mcu_io_connect_btn, connected=False)
        self._set_mcu_io_gpio_controls_enabled(False)

    def _apply_default_gpio_highz(self):
        if not self.is_mcu_io_connected or self.mcu_io is None:
            return
        pins = self._get_mcu_io_gpio_pins()
        for pin in pins:
            toggle = getattr(self, "mcu_io_output_toggles", {}).get(pin)
            if toggle is not None:
                toggle.setValue(GPIO_STATE_HIGHZ)
        if self._mcu_io_default_thread is not None and self._mcu_io_default_thread.isRunning():
            return
        worker = _GpioDefaultHighZWorker(self.mcu_io, pins)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_io_default_done)
        worker.error.connect(self._on_mcu_io_default_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_mcu_io_default_thread_cleanup)

        self._mcu_io_default_worker = worker
        self._mcu_io_default_thread = thread
        pin_label = ", ".join(f"GPIO{p}" for p in pins)
        self._mcu_io_log(f"[MCU] Setting {pin_label} to High-Z (default)...")
        thread.start()

    def _on_mcu_io_default_thread_cleanup(self):
        self._mcu_io_default_thread = None
        self._mcu_io_default_worker = None

    def _on_mcu_io_default_done(self, pins):
        self._mcu_io_log(
            "[MCU] Default High-Z applied: "
            + ", ".join(f"GPIO{p}" for p in pins)
        )

    def _on_mcu_io_default_error(self, err):
        self._mcu_io_log(f"[MCU] Default High-Z failed: {err}")

    def _on_mcu_io_connect_error(self, err):
        self.set_mcu_io_status("● Failed", is_error=True)
        self.mcu_io_search_btn.setEnabled(True)
        self.mcu_io_connect_btn.setEnabled(True)
        self._mcu_io_log(f"[MCU] Connection failed: {err}")

    def _sync_mcu_io_from_manager(self):
        # CH9114F 不走 InstrumentManager，直接跳过避免误清空本地连接状态
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return
        manager = getattr(self, "_mcu_io_manager", None)
        if manager is None or not hasattr(self, "mcu_io_connect_btn"):
            return
        session = manager.get_session(self._mcu_io_session_id)
        if session and session.connected and session.instance:
            already = self.is_mcu_io_connected and self.mcu_io is session.instance
            self.mcu_io = session.instance
            self._apply_mcu_io_connected_ui()
            if session.resource and hasattr(self, "mcu_io_port_combo"):
                if self.mcu_io_port_combo.findText(session.resource) < 0:
                    self.mcu_io_port_combo.addItem(session.resource)
                self.mcu_io_port_combo.setCurrentText(session.resource)
            if not already:
                self.mcu_io_connection_status_changed.emit(True)
        else:
            if self.is_mcu_io_connected or self.mcu_io is not None:
                self._apply_mcu_io_disconnected_ui()
                self.mcu_io_connection_status_changed.emit(False)

    def _on_mcu_io_manager_session_connected(self, session_id):
        if session_id != self._mcu_io_session_id:
            return
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return
        was_connected = self.is_mcu_io_connected
        self._sync_mcu_io_from_manager()
        if not was_connected and self.is_mcu_io_connected:
            self._mcu_io_log("[MCU] Connected (shared session).")
            self._apply_default_gpio_highz()

    def _on_mcu_io_manager_session_disconnected(self, session_id):
        if session_id != self._mcu_io_session_id:
            return
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return
        self._sync_mcu_io_from_manager()
        self._mcu_io_log("[MCU] Disconnected (shared session).")

    def _on_mcu_io_manager_connect_failed(self, session_id, error):
        if session_id != self._mcu_io_session_id:
            return
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return
        self._on_mcu_io_connect_error(error)

    def _on_mcu_io_manager_scan_finished(self, instrument_type, candidates):
        if instrument_type != "mcu_io" or not hasattr(self, "mcu_io_port_combo"):
            return
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return
        self.mcu_io_port_combo.clear()
        self.mcu_io_port_combo.setEnabled(True)
        if candidates:
            for cand in candidates:
                label = cand.display_name or cand.resource
                self.mcu_io_port_combo.addItem(label)
            self.set_mcu_io_status(f"● Found {len(candidates)}")
            self._mcu_io_log(f"[MCU] Found {len(candidates)} serial port(s).")
        else:
            self.mcu_io_port_combo.addItem("No serial ports found")
            self.mcu_io_port_combo.setEnabled(False)
            self.set_mcu_io_status("● Not Found", is_error=True)
            self._mcu_io_log("[MCU] No serial ports found.")
        self.mcu_io_search_btn.setEnabled(True)
        self.mcu_io_connect_btn.setEnabled(bool(candidates))

    def _on_mcu_io_manager_scan_failed(self, instrument_type, error):
        if instrument_type != "mcu_io":
            return
        if self._current_mcu_io_type() == MCU_TYPE_CH9114F:
            return
        self.set_mcu_io_status("● Search Failed", is_error=True)
        self._mcu_io_log(f"[MCU] Search failed: {error}")
        self.mcu_io_search_btn.setEnabled(True)
        self.mcu_io_connect_btn.setEnabled(True)

    def _reset_gpio_highz_before_disconnect(self):
        inst = self.mcu_io
        if inst is None:
            return
        pins = self._get_mcu_io_gpio_pins()
        try:
            for pin in pins:
                inst.in_pull(pin, "none")
            pin_label = ", ".join(f"GPIO{p}" for p in pins)
            self._mcu_io_log(
                f"[MCU] Restored {pin_label} to High-Z before disconnect."
            )
            for pin in pins:
                toggle = getattr(self, "mcu_io_output_toggles", {}).get(pin)
                if toggle is not None:
                    toggle.setValue(GPIO_STATE_HIGHZ)
        except Exception as e:
            logger.error(
                "MCU IO restore High-Z before disconnect failed: %s",
                e, exc_info=True
            )
            self._mcu_io_log(f"[MCU] Restore High-Z failed: {e}")

    def _disconnect_mcu_io(self):
        mcu_type = self._current_mcu_io_type()
        manager = getattr(self, "_mcu_io_manager", None)
        # 仅 YD-RP2040 走 InstrumentManager；CH9114F 走本地断开
        if manager is not None and mcu_type == MCU_TYPE_YD_RP2040:
            session = manager.get_session(self._mcu_io_session_id)
            if session and session.connected:
                self.set_mcu_io_status("● Disconnecting")
                self.mcu_io_connect_btn.setEnabled(False)
                self._reset_gpio_highz_before_disconnect()
                manager.disconnect_async(self._mcu_io_session_id)
                return
            self._apply_mcu_io_disconnected_ui()
            self.mcu_io_connection_status_changed.emit(False)
            return

        self.set_mcu_io_status("● Disconnecting")
        self._reset_gpio_highz_before_disconnect()
        self.mcu_io_connect_btn.setEnabled(False)
        try:
            if self.mcu_io is not None:
                self.mcu_io.disconnect()
        except Exception as e:
            logger.error("MCU IO disconnect failed: %s", e, exc_info=True)
            self._mcu_io_log(f"[MCU] Disconnect failed: {e}")
        finally:
            self._apply_mcu_io_disconnected_ui()
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

    def _on_mcu_io_toggle(self, pin):
        """Toggle 按钮：翻转 GPIO 电平。High -> Low，其余 -> High。"""
        toggle = self.mcu_io_output_toggles.get(pin)
        if toggle is None:
            return
        current = toggle.value()
        new_state = GPIO_STATE_LOW if current == GPIO_STATE_HIGH else GPIO_STATE_HIGH
        toggle.setValue(new_state)
        self._on_mcu_io_set_output(pin, new_state)

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
        self.mcu_io_read_value_label.setText("...")
        self.mcu_io_read_value_label.setStyleSheet(
            "color: #94a3b8; font-weight: 700; background: transparent;"
        )
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
        self.mcu_io_read_value_label.setText(level)
        if value:
            self.mcu_io_read_value_label.setObjectName("mcuReadHigh")
            self.mcu_io_read_value_label.setStyleSheet(
                "color: #34d399; font-weight: 700; background: transparent;"
            )
        else:
            self.mcu_io_read_value_label.setObjectName("mcuReadLow")
            self.mcu_io_read_value_label.setStyleSheet(
                "color: #fb7185; font-weight: 700; background: transparent;"
            )
        self.set_mcu_io_status("● Connected")
        self._set_mcu_io_gpio_controls_enabled(True)
        self._mcu_io_log(f"[MCU] GPIO{pin} read = {value} ({level}).")

    def _on_mcu_io_read_error(self, err):
        self.set_mcu_io_status("● Read Failed", is_error=True)
        self._set_mcu_io_gpio_controls_enabled(True)
        self.mcu_io_read_value_label.setText("—")
        self.mcu_io_read_value_label.setStyleSheet(
            "color: #64748b; font-weight: 700; background: transparent;"
        )
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
    def init_mcu_pwr_reset_config(self, baudrate=MCU_IO_DEFAULT_BAUDRATE,
                                  instrument_manager=None):
        self.init_mcu_io_connection(
            baudrate=baudrate, instrument_manager=instrument_manager
        )
        self._mcu_pr_pulse_thread = None
        self._mcu_pr_pulse_worker = None

    def build_mcu_pwr_reset_config_widgets(self, layout, title_row=None):
        self.build_mcu_io_connection_widgets(
            layout, title_row=title_row, with_gpio=False
        )

        label_style_sm = "font-size: 10px; color: #94a3b8;"
        label_width = 48

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)

        poweron_label = QLabel("PwrON")
        poweron_label.setStyleSheet(label_style_sm)
        poweron_label.setFixedWidth(label_width)
        self.mcu_pr_poweron_combo = DarkComboBox(bg="#020817", border="#1e293b")
        self.mcu_pr_poweron_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_pr_poweron_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.mcu_pr_poweron_combo.font()
        font.setPixelSize(11)
        self.mcu_pr_poweron_combo.setFont(font)
        for opt in self._get_mcu_io_gpio_options():
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

        self.mcu_pr_reset_combo = DarkComboBox(bg="#020817", border="#1e293b")
        self.mcu_pr_reset_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_pr_reset_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.mcu_pr_reset_combo.font()
        font.setPixelSize(11)
        self.mcu_pr_reset_combo.setFont(font)
        for opt in self._get_mcu_io_gpio_options():
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

        self.mcu_pr_status_combo = DarkComboBox(bg="#020817", border="#1e293b")
        self.mcu_pr_status_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_pr_status_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.mcu_pr_status_combo.font()
        font.setPixelSize(11)
        self.mcu_pr_status_combo.setFont(font)
        for opt in self._get_mcu_io_gpio_options():
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

        # ---- Ctrl IO（通用控制 GPIO，行为同 Status：使能+极性+Pulse/Level）----
        ctrl_label_row = QHBoxLayout()
        ctrl_label_row.setContentsMargins(0, 0, 0, 0)
        ctrl_label_row.setSpacing(4)
        ctrl_label = QLabel("Ctrl")
        ctrl_label.setStyleSheet(label_style_sm)
        self.mcu_pr_ctrl_enable_cb = QCheckBox()
        self.mcu_pr_ctrl_enable_cb.setChecked(False)
        self.mcu_pr_ctrl_enable_cb.setToolTip(
            "Enable Ctrl GPIO for generic IO control (e.g. DUT mode switch). "
            "When unchecked, Ctrl step is skipped."
        )
        self.mcu_pr_ctrl_enable_cb.setStyleSheet("""
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
        ctrl_label_row.addWidget(ctrl_label)
        ctrl_label_row.addWidget(self.mcu_pr_ctrl_enable_cb)
        ctrl_label_row.addStretch()
        ctrl_label_container = QWidget()
        ctrl_label_container.setFixedWidth(label_width)
        ctrl_label_container.setStyleSheet("background: transparent;")
        ctrl_label_container.setLayout(ctrl_label_row)

        self.mcu_pr_ctrl_combo = DarkComboBox(bg="#020817", border="#1e293b")
        self.mcu_pr_ctrl_combo.setFixedHeight(MCU_IO_BTN_HEIGHT)
        self.mcu_pr_ctrl_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        font = self.mcu_pr_ctrl_combo.font()
        font.setPixelSize(11)
        self.mcu_pr_ctrl_combo.setFont(font)
        for opt in self._get_mcu_io_gpio_options():
            self.mcu_pr_ctrl_combo.addItem(opt)
        self._mcu_pr_select_combo(
            self.mcu_pr_ctrl_combo, MCU_PWR_RESET_DEFAULTS["ctrl"]
        )
        self.mcu_pr_ctrl_combo.setMinimumWidth(56)
        self.mcu_pr_ctrl_polarity_toggle = PolarityToggle()
        self.mcu_pr_ctrl_mode_toggle = ModeToggle()
        self.mcu_pr_ctrl_mode_toggle.setToolTip(
            "Pulse: send a single pulse. Level: hold the active level until changed."
        )
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.setSpacing(3)
        ctrl_row.addWidget(self.mcu_pr_ctrl_combo, 1)
        ctrl_row.addWidget(self.mcu_pr_ctrl_polarity_toggle, 0, Qt.AlignVCenter)
        ctrl_row.addWidget(self.mcu_pr_ctrl_mode_toggle, 0, Qt.AlignVCenter)
        grid.addWidget(ctrl_label_container, 3, 0, Qt.AlignVCenter)
        grid.addLayout(ctrl_row, 3, 1)

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
        grid.addWidget(pulse_width_label, 4, 0, Qt.AlignVCenter)
        grid.addLayout(pulse_width_row, 4, 1)

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
        self.mcu_pr_ctrl_enable_cb.toggled.connect(
            self._on_mcu_pr_ctrl_enable_toggled
        )
        self._on_mcu_pr_ctrl_enable_toggled(
            self.mcu_pr_ctrl_enable_cb.isChecked()
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

    def _on_mcu_pr_ctrl_enable_toggled(self, checked):
        if getattr(self, "mcu_pr_ctrl_combo", None) is not None:
            self.mcu_pr_ctrl_combo.setEnabled(checked)
        if getattr(self, "mcu_pr_ctrl_polarity_toggle", None) is not None:
            self.mcu_pr_ctrl_polarity_toggle.setEnabled(checked)
        if getattr(self, "mcu_pr_ctrl_mode_toggle", None) is not None:
            self.mcu_pr_ctrl_mode_toggle.setEnabled(checked)

    def _refresh_mcu_pr_gpio_options(self):
        """根据当前 MCU 类型刷新 PwrON/Reset/Status/Ctrl 四个 GPIO 下拉选项。

        尽量保留用户之前的选择；若旧选择在新类型中不存在则回退到默认。
        """
        options = self._get_mcu_io_gpio_options()
        defaults = MCU_PWR_RESET_DEFAULTS
        for name, combo, default_key in (
            ("poweron", "mcu_pr_poweron_combo", "poweron"),
            ("reset", "mcu_pr_reset_combo", "reset"),
            ("status", "mcu_pr_status_combo", "status"),
            ("ctrl", "mcu_pr_ctrl_combo", "ctrl"),
        ):
            widget = getattr(self, combo, None)
            if widget is None:
                continue
            prev = widget.currentText()
            widget.blockSignals(True)
            widget.clear()
            for opt in options:
                widget.addItem(opt)
            desired = prev if prev in options else defaults.get(default_key)
            self._mcu_pr_select_combo(widget, desired)
            widget.blockSignals(False)
        # 切换后 reset/status/ctrl 的使能状态保持一致
        self._on_mcu_pr_reset_enable_toggled(
            self.mcu_pr_reset_enable_cb.isChecked()
        )
        self._on_mcu_pr_status_enable_toggled(
            self.mcu_pr_status_enable_cb.isChecked()
        )
        self._on_mcu_pr_ctrl_enable_toggled(
            self.mcu_pr_ctrl_enable_cb.isChecked()
        )

    def _on_mcu_io_type_changed_extra(self):
        """McuIoConnectionMixin 在切换 MCU 类型时回调，刷新 Pwr/Reset/Status 选项。"""
        self._refresh_mcu_pr_gpio_options()

    def get_mcu_pwr_reset_config(self):
        reset_enabled = self.mcu_pr_reset_enable_cb.isChecked()
        status_enabled = self.mcu_pr_status_enable_cb.isChecked()
        ctrl_enabled = self.mcu_pr_ctrl_enable_cb.isChecked()
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
            "ctrl_enabled": ctrl_enabled,
            "ctrl_channel": (
                self.mcu_pr_ctrl_combo.currentText() if ctrl_enabled else None
            ),
            "ctrl_polarity": (
                self.mcu_pr_ctrl_polarity_toggle.value() if ctrl_enabled else None
            ),
            "ctrl_mode": (
                self.mcu_pr_ctrl_mode_toggle.value() if ctrl_enabled else None
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

    def mcu_ctrl_toggle(self, pulse_width=None, on_done=None):
        """Ctrl IO 脉冲触发（仅在 Pulse 模式下生效）。"""
        cfg = self.get_mcu_pwr_reset_config()
        if pulse_width is None:
            pulse_width = cfg["pulse_width"]
        if not cfg["ctrl_enabled"]:
            self._mcu_io_log("[MCU] Ctrl disabled, skipped.")
            return False
        pin = self._mcu_pr_pin_index(cfg["ctrl_channel"])
        if pin is None:
            self._mcu_io_log("[MCU] Invalid Ctrl channel.")
            return False
        if cfg["ctrl_mode"] == MCU_DRIVE_MODE_LEVEL:
            self._mcu_io_log(
                "[MCU] Ctrl is in Level mode; use mcu_set_ctrl(active=...) instead."
            )
            return False
        return self._mcu_pr_run_pulses(
            [("Ctrl", pin, cfg["ctrl_polarity"])],
            pulse_width=pulse_width,
            on_done=on_done,
        )

    def mcu_set_ctrl(self, active=True, on_done=None):
        """Ctrl IO 电平保持（Level 模式）。"""
        cfg = self.get_mcu_pwr_reset_config()
        if not cfg["ctrl_enabled"]:
            self._mcu_io_log("[MCU] Ctrl disabled, skipped.")
            return False
        pin = self._mcu_pr_pin_index(cfg["ctrl_channel"])
        if pin is None:
            self._mcu_io_log("[MCU] Invalid Ctrl channel.")
            return False
        active_level = 1 if cfg["ctrl_polarity"] == "rising" else 0
        level = active_level if active else (1 - active_level)
        return self._mcu_pr_run_level(
            "Ctrl", pin, level, on_done=on_done
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
            color: #e2e8f0;
        }
        QLabel {
            background-color: transparent;
            color: #e2e8f0;
            border: none;
        }
        QLabel#cardTitle {
            font-size: 12px;
            font-weight: 700;
            color: #f1f5f9;
            letter-spacing: 0.5px;
            background-color: transparent;
        }
        QLabel#statusOk {
            color: #34d399;
            font-weight: 600;
            background-color: transparent;
        }
        QLabel#statusWarn {
            color: #fbbf24;
            font-weight: 600;
            background-color: transparent;
        }
        QLabel#statusErr {
            color: #fb7185;
            font-weight: 600;
            background-color: transparent;
        }
        QFrame#cardFrame {
            background-color: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 16px;
        }
    """

    class _CardFrame(QFrame):
        def __init__(self, title="", parent=None, max_w=560):
            super().__init__(parent)
            self.setObjectName("cardFrame")
            self.setMaximumWidth(max_w)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(16, 14, 16, 16)
            self.main_layout.setSpacing(10)
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

            outer = QVBoxLayout(self)
            outer.setContentsMargins(24, 24, 24, 24)
            outer.setAlignment(Qt.AlignCenter)

            card = _CardFrame("MCU IO")
            self.build_mcu_io_connection_widgets(
                card.main_layout, title_row=card.title_row)
            outer.addWidget(card)

            self.bind_mcu_io_signals()

        def append_log(self, msg):
            logger.info(msg)

    class _DemoWindow(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setStyleSheet(DARK_CARD_STYLE)
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)
            root.addWidget(_DemoIoWidget(), 1)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = _DemoWindow()
    w.setWindowTitle("MCU IO Module")
    w.setFixedWidth(620)
    w.setFixedHeight(720)
    resize_and_center_window(w)
    w.show()

    sys.exit(app.exec())
