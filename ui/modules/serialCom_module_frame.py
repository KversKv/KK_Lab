#
# python -m ui.modules.serialCom_module_frame
#

import os as _os
import sys as _sys
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)
from ui.resource_path import get_resource_base as _get_resource_base
from ui.resource_path import get_resource_base
_PROJECT_ROOT = _get_resource_base()
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

import json
import os
import re
import time
import serial
import serial.tools.list_ports
from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy,
    QFrame, QWidget, QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QScrollArea, QSplitter, QApplication, QMenu, QFileDialog, QGridLayout,
    QSpinBox, QDialog, QDialogButtonBox, QTabWidget, QLayout,
)
from PySide6.QtCore import (
    Signal, QThread, QObject, QTimer, QRectF, Qt, QSize, QRect, QPoint,
    QPropertyAnimation, QEasingCurve, Property, QMimeData,
)
from PySide6.QtGui import (
    QIcon, QPainter, QPixmap, QColor, QAction, QPen, QFont, QDrag,
)
from PySide6.QtSvg import QSvgRenderer

from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.scrollbar import SCROLLBAR_STYLE
from debug_config import DEBUG_MOCK


_SVG_COMMON_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Common"
)
_SVG_SERIAL_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Serial",
)
_SVG_LOGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Logs",
)
_SEARCH_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "unlink.svg")


def _tinted_svg_icon(svg_path: str, color: str, size: int = 14) -> QIcon:
    if not os.path.isfile(svg_path):
        return QIcon()
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)

_SERIAL_BTN_HEIGHT = 24
_SERIAL_BTN_ICON_SIZE = 14
_SERIAL_BTN_RADIUS = 6


def _serial_search_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #0e1a35;
            border: 1px solid #1f315d;
            border-radius: {r}px;
            color: #c8d5e2;
            font-weight: 600;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            background-color: #152045;
            border: 1px solid #2a3a6a;
        }}
        QPushButton:pressed {{
            background-color: #0a1228;
        }}
        QPushButton:disabled {{
            background-color: #080e22;
            color: #3a4a6a;
            border: 1px solid #1a2d57;
        }}
    """


def _serial_connect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #064e3b;
            border: none;
            border-radius: {r}px;
            color: #4ade80;
            font-weight: 700;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            background-color: #065f46;
            color: #6ee7a0;
        }}
        QPushButton:pressed {{
            background-color: #053f30;
        }}
        QPushButton:disabled {{
            background-color: #080e22;
            color: #3a4a6a;
            border: none;
        }}
    """


def _serial_disconnect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #4c1d2e;
            border: none;
            border-radius: {r}px;
            color: #f87171;
            font-weight: 700;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            background-color: #5c2438;
            color: #fca5a5;
        }}
        QPushButton:pressed {{
            background-color: #3b1525;
        }}
        QPushButton:disabled {{
            background-color: #080e22;
            color: #3a4a6a;
            border: none;
        }}
    """


class _SerialSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=_SERIAL_BTN_ICON_SIZE,
                 btn_height=_SERIAL_BTN_HEIGHT, btn_radius=_SERIAL_BTN_RADIUS):
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)
        self._icon_size = icon_size
        self._angle = 0.0
        self._spinning = False
        self._icon_pixmap = None

        if os.path.isfile(_SEARCH_ICON_PATH):
            renderer = QSvgRenderer(_SEARCH_ICON_PATH)
            pm = QPixmap(icon_size, icon_size)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            renderer.render(p, QRectF(0, 0, icon_size, icon_size))
            p.end()
            self._icon_pixmap = pm

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._on_tick)

        self.setText("")
        self.setStyleSheet(_serial_search_style(h=btn_height, r=btn_radius))

    def start_spinning(self):
        if self._spinning:
            return
        self._spinning = True
        self._angle = 0.0
        self._timer.start()
        self.update()

    def stop_spinning(self):
        if not self._spinning:
            return
        self._spinning = False
        self._timer.stop()
        self._angle = 0.0
        self.update()

    def _on_tick(self):
        self._angle = (self._angle + 10.0) % 360.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._icon_pixmap is None:
            return

        s = self._icon_size
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.translate(cx, cy)
        if self._spinning:
            painter.rotate(self._angle)
        painter.drawPixmap(int(-s / 2.0), int(-s / 2.0), self._icon_pixmap)
        painter.end()


def _update_serial_btn_state(btn, connected,
                             h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS,
                             icon_size=_SERIAL_BTN_ICON_SIZE):
    from PySide6.QtCore import QSize as _QSize
    if connected:
        btn.setText("Disconnect")
        btn.setStyleSheet(_serial_disconnect_style(h=h, r=r))
        if os.path.isfile(_UNLINK_ICON_PATH):
            btn.setIcon(QIcon(_UNLINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
    else:
        btn.setText("Connect")
        btn.setStyleSheet(_serial_connect_style(h=h, r=r))
        if os.path.isfile(_LINK_ICON_PATH):
            btn.setIcon(QIcon(_LINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
        else:
            btn.setIcon(QIcon())


class _SearchSerialPortWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            ports = serial.tools.list_ports.comports()
            result = [f"{p.device} - {p.description}" for p in ports]
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


MODE_SEARCH_SELECT = "search_and_select"
MODE_FULL = "full"
MODE_INLINE = "inline"


class SerialComMixin:
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def init_serial_connection(self, mode=MODE_FULL, baudrate=115200, prefix="Serial"):
        self._serial_mode = mode
        self._serial_baudrate = baudrate
        self._serial_prefix = prefix
        self._serial_port = None
        self._serial_conn = None
        self._serial_connected = False
        self._serial_search_thread = None
        self._serial_search_worker = None
        self._serial_read_thread = None
        self._serial_read_worker = None
        self._serial_btn_height = _SERIAL_BTN_HEIGHT
        self._serial_btn_radius = _SERIAL_BTN_RADIUS
        self._serial_btn_icon_size = _SERIAL_BTN_ICON_SIZE

    def build_serial_connection_widgets(self, layout,
                                        btn_height=_SERIAL_BTN_HEIGHT,
                                        btn_radius=_SERIAL_BTN_RADIUS,
                                        btn_icon_size=_SERIAL_BTN_ICON_SIZE):
        self._serial_btn_height = btn_height
        self._serial_btn_radius = btn_radius
        self._serial_btn_icon_size = btn_icon_size

        if self._serial_mode == MODE_INLINE:
            _inline_h = 22
            _inline_icon = 12
            _inline_r = 4

            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            self.serial_label = QLabel("COM:")
            self.serial_label.setStyleSheet(
                "font-size: 11px; color: #7e96bf; background: transparent; border: none;"
            )
            row.addWidget(self.serial_label)

            self.serial_combo = DarkComboBox()
            self.serial_combo.setSizeAdjustPolicy(
                DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            self.serial_combo.setMinimumContentsLength(10)
            self.serial_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.serial_combo.setFixedHeight(_inline_h)
            _font = self.serial_combo.font()
            _font.setPixelSize(11)
            self.serial_combo.setFont(_font)
            row.addWidget(self.serial_combo, 1)

            self.serial_search_btn = _SerialSearchButton(
                icon_size=_inline_icon,
                btn_height=_inline_h,
                btn_radius=_inline_r,
            )
            self.serial_search_btn.setFixedSize(_inline_h, _inline_h)
            self.serial_search_btn.setStyleSheet(
                self.serial_search_btn.styleSheet() + f"""
                QPushButton {{
                    padding: 0px;
                    margin: 0px;
                    min-width: {_inline_h}px;
                    max-width: {_inline_h}px;
                    min-height: {_inline_h}px;
                    max-height: {_inline_h}px;
                }}
            """
            )
            row.addWidget(self.serial_search_btn)

            layout.addLayout(row)
            return

        self.serial_status_label = QLabel("● Not Connected")
        self.serial_status_label.setObjectName("statusErr")
        layout.addWidget(self.serial_status_label)

        self.serial_combo = DarkComboBox()
        self.serial_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.serial_combo.setMinimumContentsLength(10)
        self.serial_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.serial_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 2, 0, 0)

        self.serial_search_btn = _SerialSearchButton(
            icon_size=btn_icon_size,
            btn_height=btn_height,
            btn_radius=btn_radius,
        )
        btn_row.addWidget(self.serial_search_btn)

        if self._serial_mode == MODE_FULL:
            self.serial_connect_btn = QPushButton()
            _update_serial_btn_state(
                self.serial_connect_btn, connected=False,
                h=btn_height, r=btn_radius, icon_size=btn_icon_size,
            )
            btn_row.addWidget(self.serial_connect_btn)

        layout.addLayout(btn_row)

    def bind_serial_signals(self):
        self.serial_search_btn.clicked.connect(self._on_serial_search)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.clicked.connect(self._on_serial_toggle)

    def _set_serial_status(self, text, is_error=False):
        if not hasattr(self, 'serial_status_label'):
            return
        self.serial_status_label.setText(text)
        if is_error:
            self.serial_status_label.setObjectName("statusErr")
        elif any(kw in text for kw in ["Searching", "Connecting", "Disconnecting"]):
            self.serial_status_label.setObjectName("statusWarn")
        else:
            self.serial_status_label.setObjectName("statusOk")
        self.serial_status_label.style().unpolish(self.serial_status_label)
        self.serial_status_label.style().polish(self.serial_status_label)
        self.serial_status_label.update()

    def _on_serial_search(self):
        if DEBUG_MOCK:
            self.serial_combo.clear()
            self.serial_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            self._set_serial_status("● Mock port ready")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Mock port loaded.")
            return

        if self._serial_search_thread is not None and self._serial_search_thread.isRunning():
            return

        self._set_serial_status("● Searching")
        self.serial_search_btn.setEnabled(False)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(False)

        worker = _SearchSerialPortWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_serial_search_done)
        worker.error.connect(self._on_serial_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_serial_search_thread_cleanup())

        self._serial_search_thread = thread
        self._serial_search_worker = worker
        thread.start()

    def _on_serial_search_thread_cleanup(self):
        self._serial_search_thread = None
        self._serial_search_worker = None

    def _on_serial_search_done(self, ports):
        self.serial_combo.clear()
        if ports:
            for port in ports:
                self.serial_combo.addItem(port)
            count = len(ports)
            self._set_serial_status(f"● Found {count} port(s)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Found {count} serial port(s).")
        else:
            self.serial_combo.addItem("No serial ports found")
            self.serial_combo.setEnabled(False)
            self._set_serial_status("● No port found", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] No serial ports found.")

        self.serial_search_btn.setEnabled(True)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(bool(ports))

    def _on_serial_search_error(self, err):
        self._set_serial_status("● Search failed", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Search error: {err}")
        self.serial_search_btn.setEnabled(True)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(False)

    def _on_serial_toggle(self):
        if self._serial_connected:
            self._on_serial_disconnect()
        else:
            self._on_serial_connect()

    def get_selected_serial_port(self):
        text = self.serial_combo.currentText()
        if not text or text in ("No serial ports found",):
            return None
        return text.split()[0]

    def connect_selected_serial(self, baudrate=None):
        port = self.get_selected_serial_port()
        if port is None:
            return None
        br = baudrate if baudrate is not None else self._serial_baudrate
        try:
            conn = serial.Serial(port, br, timeout=1)
            self._serial_conn = conn
            self._serial_port = port
            self._serial_connected = True
            self.serial_connection_changed.emit(True)
            return conn
        except Exception:
            return None

    def _on_serial_connect(self):
        if self._serial_mode != MODE_FULL:
            return
        self.serial_connect_btn.setEnabled(False)

        port = self.get_selected_serial_port()
        if port is None:
            self._set_serial_status("● No valid port selected", is_error=True)
            self.serial_connect_btn.setEnabled(True)
            return

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_connected = True
            self._update_serial_connect_ui(True)
            self._set_serial_status(f"● Connected to: MOCK (DEBUG)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Mock serial connected.")
            self.serial_connection_changed.emit(True)
            return

        self._set_serial_status("● Connecting")
        try:
            conn = serial.Serial(port, self._serial_baudrate, timeout=1)
            self._serial_conn = conn
            self._serial_port = port
            self._serial_connected = True
            self._update_serial_connect_ui(True)
            self._set_serial_status(f"● Connected to: {port}")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Connected: {port} @ {self._serial_baudrate}")
            self.serial_connection_changed.emit(True)
            self._start_serial_read()
        except Exception as e:
            self._set_serial_status("● Connection failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Connection failed: {e}")
        finally:
            self.serial_connect_btn.setEnabled(True)

    def _on_serial_disconnect(self):
        if self._serial_mode != MODE_FULL:
            return
        self.serial_connect_btn.setEnabled(False)
        self._stop_serial_read()
        try:
            if self._serial_conn is not None and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception as e:
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Close error: {e}")

        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False
        self._update_serial_connect_ui(False)
        self._set_serial_status("● Not Connected", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Disconnected.")
        self.serial_connection_changed.emit(False)
        self.serial_connect_btn.setEnabled(True)

    def _update_serial_connect_ui(self, connected):
        if not hasattr(self, 'serial_connect_btn'):
            return
        _update_serial_btn_state(
            self.serial_connect_btn, connected,
            h=self._serial_btn_height,
            r=self._serial_btn_radius,
            icon_size=self._serial_btn_icon_size,
        )
        self.serial_search_btn.setEnabled(not connected)
        self.serial_combo.setEnabled(not connected)

    def _start_serial_read(self):
        if self._serial_conn is None or not self._serial_conn.is_open:
            return
        if self._serial_read_thread is not None and self._serial_read_thread.isRunning():
            return

        worker = _SerialReadWorker(self._serial_conn)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.data_received.connect(self._on_serial_data_received)
        worker.error.connect(self._on_serial_read_error)

        self._serial_read_thread = thread
        self._serial_read_worker = worker
        thread.start()

    def _stop_serial_read(self):
        if self._serial_read_worker is not None:
            self._serial_read_worker.stop()
        if self._serial_read_thread is not None and self._serial_read_thread.isRunning():
            self._serial_read_thread.quit()
            self._serial_read_thread.wait(2000)
        self._serial_read_thread = None
        self._serial_read_worker = None

    def _on_serial_data_received(self, data):
        self.serial_data_received.emit(data)

    def _on_serial_read_error(self, err):
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Read error: {err}")

    def serial_send(self, data):
        if self._serial_conn is None or not self._serial_conn.is_open:
            return False
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            self._serial_conn.write(data)
            return True
        except Exception as e:
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Send error: {e}")
            return False

    def get_serial_connection(self):
        return self._serial_conn

    def is_serial_connected(self):
        return self._serial_connected

    def close_serial(self):
        self._stop_serial_read()
        try:
            if self._serial_conn is not None and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception:
            pass
        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False

    # ------------------------------------------------------------------
    #  complete_serialComWidget  —  Full Serial Console Builder
    # ------------------------------------------------------------------

    def complete_serialComWidget(self, parent_layout):
        self._sc_rx_bytes = 0
        self._sc_tx_bytes = 0
        self._sc_paused = False
        self._sc_auto_scroll = True
        self._sc_all_logs = []
        self._sc_rx_display_hex = False
        self._sc_tx_display_hex = False
        self._sc_show_timestamp = True
        self._sc_auto_resend = False
        self._sc_resend_interval = 1000
        self._sc_line_ending = "\r\n"
        self._sc_show_send = True
        self._sc_line_by_line = False
        self._sc_send_history = []
        self._sc_quick_commands = []
        self._sc_sidebar_visible = True
        self._sc_extra_log_panels = []
        self._sc_active_log_panel_index = 0
        self._sc_filter_dirty = False
        self._sc_filter_last_count = 0

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._sc_toolbar = self._build_sc_toolbar()
        outer.addWidget(self._sc_toolbar)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setHandleWidth(3)
        body_splitter.setStyleSheet("""
            QSplitter::handle { background-color: #1a2d57; }
            QSplitter::handle:hover { background-color: #6366f1; }
        """)

        self._sc_sidebar_widget = self._build_sc_sidebar()
        body_splitter.addWidget(self._sc_sidebar_widget)

        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        self._sc_log_container = QWidget()
        self._sc_log_grid = QGridLayout(self._sc_log_container)
        self._sc_log_grid.setContentsMargins(0, 0, 0, 0)
        self._sc_log_grid.setSpacing(2)

        self._sc_log_area = self._build_sc_log_area()
        self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
        center_layout.addWidget(self._sc_log_container, 1)

        self._sc_send_area = self._build_sc_send_area()
        center_layout.addWidget(self._sc_send_area)

        self._sc_quick_area = self._build_sc_quick_commands()
        center_layout.addWidget(self._sc_quick_area)

        body_splitter.addWidget(center_widget)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setSizes([220, 600])

        outer.addWidget(body_splitter, 1)

        parent_layout.addLayout(outer)

        self._bind_sc_signals()

        self._sc_resend_timer = QTimer()
        self._sc_resend_timer.timeout.connect(self._sc_on_resend_tick)

        self._sc_pending_html = []
        self._sc_flush_timer = QTimer()
        self._sc_flush_timer.setInterval(60)
        self._sc_flush_timer.timeout.connect(self._sc_flush_pending_logs)
        self._sc_flush_timer.start()

    # --- toolbar ---

    def _build_sc_toolbar(self):
        frame = QFrame()
        frame.setObjectName("scToolbar")
        frame.setFixedHeight(34)
        frame.setStyleSheet("""
            QFrame#scToolbar {
                background-color: #080e22;
                border-bottom: 1px solid #1a2d57;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self._sc_connect_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "Connect"
        )
        self._sc_connect_btn.setStyleSheet("""
            QPushButton {
                min-height: 0px; max-height: 20px; padding: 2px 8px; border-radius: 6px;
                background-color: transparent; color: #4ade80; font-size: 10px;
                border: none;
            }
            QPushButton:hover { background-color: #0a2818; }
            QPushButton:pressed { background-color: #071e12; }
        """)
        icon_conn = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "#4ade80", 12)
        if not icon_conn.isNull():
            self._sc_connect_btn.setIcon(icon_conn)
        layout.addWidget(self._sc_connect_btn)

        self._sc_pause_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "pause.svg"), "Pause"
        )
        self._sc_pause_btn.setCheckable(True)
        layout.addWidget(self._sc_pause_btn)

        self._sc_stop_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "stop.svg"), "Stop"
        )
        layout.addWidget(self._sc_stop_btn)

        self._sc_refresh_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "refresh.svg"), "Refresh"
        )
        layout.addWidget(self._sc_refresh_btn)

        self._sc_add_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "plus.svg"), ""
        )
        self._sc_add_log_btn.setFixedSize(20, 20)
        self._sc_add_log_btn.setToolTip("Add LOG panel")
        self._sc_add_log_btn.setStyleSheet("""
            QPushButton {
                min-height: 0px; max-height: 20px; min-width: 20px; max-width: 20px;
                padding: 0px; border-radius: 6px;
                background-color: #0e1a35; color: #c8d5e2; border: none;
            }
            QPushButton:hover { background-color: #152045; }
            QPushButton:pressed { background-color: #0a1228; }
        """)
        icon_add = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "plus.svg"), "#4ade80", 12)
        if not icon_add.isNull():
            self._sc_add_log_btn.setIcon(icon_add)
        layout.addWidget(self._sc_add_log_btn)

        self._sc_remove_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "minus.svg"), ""
        )
        self._sc_remove_log_btn.setFixedSize(20, 20)
        self._sc_remove_log_btn.setToolTip("Remove current LOG panel")
        self._sc_remove_log_btn.setStyleSheet("""
            QPushButton {
                min-height: 0px; max-height: 20px; min-width: 20px; max-width: 20px;
                padding: 0px; border-radius: 6px;
                background-color: #0e1a35; color: #c8d5e2; border: none;
            }
            QPushButton:hover { background-color: #152045; }
            QPushButton:pressed { background-color: #0a1228; }
            QPushButton:disabled { background-color: #080e22; }
        """)
        icon_remove = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "minus.svg"), "#ff5e7a", 12)
        if not icon_remove.isNull():
            self._sc_remove_log_btn.setIcon(icon_remove)
        self._sc_remove_log_btn.setEnabled(False)
        layout.addWidget(self._sc_remove_log_btn)

        layout.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #1a2d57;")
        layout.addWidget(sep)

        layout.addSpacing(8)

        self._sc_sidebar_toggle_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "sidebar.svg"), "Sidebar"
        )
        self._sc_sidebar_toggle_btn.setCheckable(True)
        self._sc_sidebar_toggle_btn.setChecked(True)
        layout.addWidget(self._sc_sidebar_toggle_btn)

        layout.addStretch()

        self._sc_settings_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "settings.svg"), "Settings"
        )
        layout.addWidget(self._sc_settings_btn)

        return frame

    # --- sidebar ---

    def _build_sc_sidebar(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(210)
        scroll.setMaximumWidth(280)
        scroll.setStyleSheet("""
            QScrollArea { background-color: #050b1e; border: none; border-right: 1px solid #1a2d57; }
            QScrollArea > QWidget > QWidget { background-color: #050b1e; }
        """ + SCROLLBAR_STYLE)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        root.addWidget(self._build_sc_section_port_settings())
        root.addWidget(self._build_sc_section_rx_settings())
        root.addWidget(self._build_sc_section_tx_settings())
        root.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_sc_section_port_settings(self):
        grp = self._make_sc_section("Serial Config")
        layout = grp.property("_inner_layout")

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)

        grid.addWidget(self._make_sc_label("Port"), 0, 0)
        self._sc_port_combo = DarkComboBox()
        self._sc_port_combo.setFixedHeight(24)
        self._sc_port_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_port_combo.setMinimumWidth(60)
        f = self._sc_port_combo.font()
        f.setPixelSize(11)
        self._sc_port_combo.setFont(f)
        grid.addWidget(self._sc_port_combo, 0, 1)

        grid.addWidget(self._make_sc_label("Baudrate"), 1, 0)
        self._sc_baud_combo = DarkComboBox()
        self._sc_baud_combo.setFixedHeight(24)
        self._sc_baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "115200", "9600", "Custom"]:
            self._sc_baud_combo.addItem(br)
        self._sc_baud_combo.setCurrentIndex(0)
        f2 = self._sc_baud_combo.font()
        f2.setPixelSize(11)
        self._sc_baud_combo.setFont(f2)
        grid.addWidget(self._sc_baud_combo, 1, 1)

        grid.addWidget(self._make_sc_label("Data bits"), 2, 0)
        self._sc_databit_combo = DarkComboBox()
        self._sc_databit_combo.setFixedHeight(24)
        for d in ["8", "7", "6", "5"]:
            self._sc_databit_combo.addItem(d)
        grid.addWidget(self._sc_databit_combo, 2, 1)

        grid.addWidget(self._make_sc_label("Flow ctrl"), 3, 0)
        self._sc_flow_combo = DarkComboBox()
        self._sc_flow_combo.setFixedHeight(24)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._sc_flow_combo.addItem(fc)
        grid.addWidget(self._sc_flow_combo, 3, 1)

        grid.addWidget(self._make_sc_label("Stop bits"), 4, 0)
        self._sc_stopbit_combo = DarkComboBox()
        self._sc_stopbit_combo.setFixedHeight(24)
        for s in ["1", "1.5", "2"]:
            self._sc_stopbit_combo.addItem(s)
        grid.addWidget(self._sc_stopbit_combo, 4, 1)

        grid.addWidget(self._make_sc_label("Parity"), 5, 0)
        self._sc_parity_combo = DarkComboBox()
        self._sc_parity_combo.setFixedHeight(24)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._sc_parity_combo.addItem(p)
        grid.addWidget(self._sc_parity_combo, 5, 1)

        layout.addLayout(grid)
        return grp

    _TOGGLE_W = 80
    _SPIN_W = _TOGGLE_W // 2
    _MS_LABEL_W = 16
    _COMBO_END_W = _SPIN_W + 4 + _MS_LABEL_W

    def _build_sc_section_rx_settings(self):
        grp = self._make_sc_section("RX Config")
        layout = grp.property("_inner_layout")

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.addWidget(self._make_sc_label("Format"))
        row1.addStretch()
        self._sc_rx_toggle = _MiniSlideToggle("ASCII", "HEX")
        self._sc_rx_toggle.toggled.connect(lambda v: setattr(self, '_sc_rx_display_hex', v == "HEX"))
        row1.addWidget(self._sc_rx_toggle)
        layout.addLayout(row1)

        row_af = QHBoxLayout()
        row_af.setSpacing(4)
        self._sc_rx_auto_flush_cb = QCheckBox("Auto Fl")
        self._sc_rx_auto_flush_cb.setStyleSheet(self._sc_checkbox_style())
        row_af.addWidget(self._sc_rx_auto_flush_cb)
        row_af.addStretch()
        self._sc_rx_auto_flush_spin = QSpinBox()
        self._sc_rx_auto_flush_spin.setRange(10, 60000)
        self._sc_rx_auto_flush_spin.setValue(50)
        self._sc_rx_auto_flush_spin.setSingleStep(10)
        self._sc_rx_auto_flush_spin.setFixedSize(self._SPIN_W, 20)
        self._sc_rx_auto_flush_spin.setStyleSheet("""
            QSpinBox {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 4px;
                color: #c8d5e2; font-size: 10px; padding: 1px 2px;
            }
            QSpinBox::up-button, QSpinBox::down-button { width: 12px; }
        """)
        row_af.addWidget(self._sc_rx_auto_flush_spin)
        af_unit = QLabel("ms")
        af_unit.setFixedWidth(self._MS_LABEL_W)
        af_unit.setStyleSheet("color: #7b8fa5; font-size: 10px; background: transparent; border: none;")
        row_af.addWidget(af_unit)
        layout.addLayout(row_af)

        self._sc_rx_show_time_cb = QCheckBox("Show Time (ms)")
        self._sc_rx_show_time_cb.setChecked(True)
        self._sc_rx_show_time_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_rx_show_time_cb.toggled.connect(lambda v: setattr(self, '_sc_show_timestamp', v))
        layout.addWidget(self._sc_rx_show_time_cb)

        return grp

    def _build_sc_section_tx_settings(self):
        grp = self._make_sc_section("TX Config")
        layout = grp.property("_inner_layout")

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.addWidget(self._make_sc_label("Format"))
        row1.addStretch()
        self._sc_tx_toggle = _MiniSlideToggle("ASCII", "HEX")
        self._sc_tx_toggle.toggled.connect(lambda v: setattr(self, '_sc_tx_display_hex', v == "HEX"))
        row1.addWidget(self._sc_tx_toggle)
        layout.addLayout(row1)

        row_auto = QHBoxLayout()
        row_auto.setSpacing(4)
        self._sc_auto_resend_cb = QCheckBox("Auto\nSend")
        self._sc_auto_resend_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_auto_resend_cb.toggled.connect(self._sc_on_auto_resend_toggled)
        row_auto.addWidget(self._sc_auto_resend_cb)
        row_auto.addStretch()
        self._sc_resend_spin = QSpinBox()
        self._sc_resend_spin.setRange(100, 60000)
        self._sc_resend_spin.setValue(1000)
        self._sc_resend_spin.setSingleStep(100)
        self._sc_resend_spin.setFixedSize(self._SPIN_W, 20)
        self._sc_resend_spin.setStyleSheet("""
            QSpinBox {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 4px;
                color: #c8d5e2; font-size: 10px; padding: 1px 2px;
            }
            QSpinBox::up-button, QSpinBox::down-button { width: 12px; }
        """)
        row_auto.addWidget(self._sc_resend_spin)
        auto_unit = QLabel("ms")
        auto_unit.setFixedWidth(self._MS_LABEL_W)
        auto_unit.setStyleSheet("color: #7b8fa5; font-size: 10px; background: transparent; border: none;")
        row_auto.addWidget(auto_unit)
        layout.addLayout(row_auto)

        row_ending = QHBoxLayout()
        row_ending.setSpacing(4)
        row_ending.addWidget(self._make_sc_label("Line End"))
        row_ending.addStretch()
        self._sc_ending_combo = DarkComboBox()
        self._sc_ending_combo.setFixedHeight(22)
        self._sc_ending_combo.setFixedWidth(self._COMBO_END_W)
        for label, val in [("\\r\\n", "\r\n"), ("\\n", "\n"), ("\\r", "\r"), ("\\n\\r", "\n\r"), ("None", "")]:
            self._sc_ending_combo.addItem(label, val)
        self._sc_ending_combo.setCurrentIndex(0)
        f = self._sc_ending_combo.font()
        f.setPixelSize(10)
        self._sc_ending_combo.setFont(f)
        self._sc_ending_combo.currentIndexChanged.connect(
            lambda i: setattr(self, '_sc_line_ending', self._sc_ending_combo.itemData(i) or "")
        )
        row_ending.addWidget(self._sc_ending_combo)
        layout.addLayout(row_ending)

        self._sc_show_send_cb = QCheckBox("Show Sent Data")
        self._sc_show_send_cb.setChecked(True)
        self._sc_show_send_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_show_send_cb.toggled.connect(lambda v: setattr(self, '_sc_show_send', v))
        layout.addWidget(self._sc_show_send_cb)

        self._sc_line_by_line_cb = QCheckBox("Line by Line")
        self._sc_line_by_line_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_line_by_line_cb.toggled.connect(lambda v: setattr(self, '_sc_line_by_line', v))
        layout.addWidget(self._sc_line_by_line_cb)

        return grp

    # --- log area ---

    def _build_sc_log_area(self):
        frame = QFrame()
        frame.setObjectName("scLogFrame")
        frame.setStyleSheet("""
            QFrame#scLogFrame {
                background-color: #091023;
                border: 1px solid #1a2d57;
                border-radius: 8px;
            }
        """)
        frame.setProperty("_is_primary", True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 4)
        toolbar.setSpacing(6)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), "#7b8fa5", 14)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(14, 14))
        icon_label.setFixedSize(16, 16)
        icon_label.setStyleSheet("background: transparent;")
        toolbar.addWidget(icon_label)

        title = QLabel("Serial Log")
        title.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 700; background: transparent;")
        toolbar.addWidget(title)

        toolbar.addStretch()

        self._sc_filter_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "filter.svg"), "Filter"
        )
        self._sc_filter_btn.setCheckable(True)
        toolbar.addWidget(self._sc_filter_btn)

        self._sc_copy_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "copy.svg"), "Copy"
        )
        toolbar.addWidget(self._sc_copy_btn)

        self._sc_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export"
        )
        toolbar.addWidget(self._sc_export_btn)

        self._sc_clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear"
        )
        toolbar.addWidget(self._sc_clear_btn)

        self._sc_scroll_lock_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll"
        )
        self._sc_scroll_lock_btn.setCheckable(True)
        self._sc_scroll_lock_btn.setChecked(True)
        toolbar.addWidget(self._sc_scroll_lock_btn)

        layout.addLayout(toolbar)

        self._sc_filter_row = QWidget()
        self._sc_filter_row.setVisible(False)
        self._sc_filter_row.setStyleSheet("background: transparent;")
        filter_root = QVBoxLayout(self._sc_filter_row)
        filter_root.setContentsMargins(8, 0, 8, 4)
        filter_root.setSpacing(4)

        fl = QHBoxLayout()
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(4)
        self._sc_filter_input = QLineEdit()
        self._sc_filter_input.setPlaceholderText("Enter keyword or regex to filter logs...")
        self._sc_filter_input.setStyleSheet("""
            QLineEdit {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 6px;
                color: #c8d5e2; font-size: 10px; padding: 2px 6px; min-height: 18px; max-height: 18px;
            }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """)
        fl.addWidget(self._sc_filter_input, 1)

        self._sc_filter_match_label = QLabel("")
        self._sc_filter_match_label.setStyleSheet(
            "color: #7b8fa5; font-size: 9px; background: transparent; min-width: 60px;"
        )
        fl.addWidget(self._sc_filter_match_label)
        filter_root.addLayout(fl)

        opts = QHBoxLayout()
        opts.setContentsMargins(0, 0, 0, 0)
        opts.setSpacing(8)

        self._sc_filter_regex_cb = QCheckBox("Regex")
        self._sc_filter_regex_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_filter_regex_cb.setToolTip("Enable regex matching")
        opts.addWidget(self._sc_filter_regex_cb)

        self._sc_filter_case_cb = QCheckBox("Match Case")
        self._sc_filter_case_cb.setStyleSheet(self._sc_checkbox_style())
        opts.addWidget(self._sc_filter_case_cb)

        self._sc_filter_invert_cb = QCheckBox("Invert")
        self._sc_filter_invert_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_filter_invert_cb.setToolTip("Show non-matching lines")
        opts.addWidget(self._sc_filter_invert_cb)

        opts.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedHeight(14)
        sep.setStyleSheet("color: #1a2d57; background: transparent;")
        opts.addWidget(sep)

        opts.addSpacing(4)

        before_lbl = QLabel("Before")
        before_lbl.setStyleSheet("color: #7b8fa5; font-size: 10px; background: transparent;")
        opts.addWidget(before_lbl)
        self._sc_filter_before_spin = QSpinBox()
        self._sc_filter_before_spin.setRange(0, 999)
        self._sc_filter_before_spin.setValue(0)
        self._sc_filter_before_spin.setFixedSize(52, 18)
        self._sc_filter_before_spin.setToolTip("Show N lines before matched lines")
        self._sc_filter_before_spin.setStyleSheet("""
            QSpinBox {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 4px;
                color: #c8d5e2; font-size: 9px; padding: 0px 2px;
            }
            QSpinBox::up-button, QSpinBox::down-button { width: 10px; }
        """)
        opts.addWidget(self._sc_filter_before_spin)
        before_unit = QLabel("lines")
        before_unit.setStyleSheet("color: #7b8fa5; font-size: 10px; background: transparent;")
        opts.addWidget(before_unit)

        opts.addSpacing(4)

        after_lbl = QLabel("After")
        after_lbl.setStyleSheet("color: #7b8fa5; font-size: 10px; background: transparent;")
        opts.addWidget(after_lbl)
        self._sc_filter_after_spin = QSpinBox()
        self._sc_filter_after_spin.setRange(0, 999)
        self._sc_filter_after_spin.setValue(0)
        self._sc_filter_after_spin.setFixedSize(52, 18)
        self._sc_filter_after_spin.setToolTip("Show N lines after matched lines")
        self._sc_filter_after_spin.setStyleSheet("""
            QSpinBox {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 4px;
                color: #c8d5e2; font-size: 9px; padding: 0px 2px;
            }
            QSpinBox::up-button, QSpinBox::down-button { width: 10px; }
        """)
        opts.addWidget(self._sc_filter_after_spin)
        after_unit = QLabel("lines")
        after_unit.setStyleSheet("color: #7b8fa5; font-size: 10px; background: transparent;")
        opts.addWidget(after_unit)

        opts.addStretch()
        filter_root.addLayout(opts)

        layout.addWidget(self._sc_filter_row)

        self._sc_log_edit = QTextEdit()
        self._sc_log_edit.setReadOnly(True)
        self._sc_log_edit.setStyleSheet("""
            QTextEdit {
                background-color: #020618; border: none; border-top: 1px solid #1a2d57;
                color: #7cecc8; font-family: Consolas, "Courier New", monospace; font-size: 11px;
                padding: 6px 8px;
            }
        """ + SCROLLBAR_STYLE)
        layout.addWidget(self._sc_log_edit, 1)

        if self._sc_log_edit.verticalScrollBar():
            self._sc_log_edit.verticalScrollBar().valueChanged.connect(self._sc_on_user_scroll)

        self._sc_status_bar = self._build_sc_status_bar()
        layout.addWidget(self._sc_status_bar)

        return frame

    # --- send area ---

    def _build_sc_send_area(self):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        send_row = QHBoxLayout()
        send_row.setSpacing(4)

        self._sc_send_input = QLineEdit()
        self._sc_send_input.setPlaceholderText("Enter text to send...")
        self._sc_send_input.setStyleSheet("""
            QLineEdit {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 6px;
                color: #c8d5e2; font-size: 11px; padding: 4px 8px; min-height: 26px;
            }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """)
        send_row.addWidget(self._sc_send_input, 1)

        self._sc_send_btn = QPushButton("Send")
        self._sc_send_btn.setCursor(Qt.PointingHandCursor)
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "send.svg"), "#ffffff", 12)
        if not icon.isNull():
            self._sc_send_btn.setIcon(icon)
        self._sc_send_btn.setStyleSheet("""
            QPushButton {
                background-color: #064e3b; border: none; border-radius: 6px;
                color: #4ade80; font-weight: 700; font-size: 11px;
                padding: 4px 14px; min-height: 26px;
            }
            QPushButton:hover { background-color: #065f46; }
            QPushButton:pressed { background-color: #053f30; }
        """)
        send_row.addWidget(self._sc_send_btn)

        layout.addLayout(send_row)

        self._sc_history_combo = DarkComboBox()
        self._sc_history_combo.setFixedHeight(22)
        self._sc_history_combo.setPlaceholderText("Recently sent commands...")
        f = self._sc_history_combo.font()
        f.setPixelSize(10)
        self._sc_history_combo.setFont(f)
        self._sc_history_combo.activated.connect(
            lambda i: self._sc_send_input.setText(self._sc_history_combo.itemText(i))
        )
        layout.addWidget(self._sc_history_combo)

        return widget

    # --- quick commands ---

    def _build_sc_quick_commands(self):
        frame = QFrame()
        frame.setObjectName("scQuickFrame")
        frame.setStyleSheet("""
            QFrame#scQuickFrame {
                background-color: #0b1227; border-top: 1px solid #1a2d57;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(4)

        zap_icon = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "zap.svg"), "#facc15", 12)
        if not icon.isNull():
            zap_icon.setPixmap(icon.pixmap(12, 12))
        zap_icon.setFixedSize(14, 14)
        zap_icon.setStyleSheet("background: transparent;")
        header.addWidget(zap_icon)

        lbl = QLabel("Quick Commands")
        lbl.setStyleSheet("color: #9bafc5; font-size: 10px; font-weight: 600; background: transparent;")
        header.addWidget(lbl)

        header.addStretch()

        self._sc_qc_add_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "Add"
        )
        header.addWidget(self._sc_qc_add_btn)

        self._sc_qc_import_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "import.svg"), "Import"
        )
        header.addWidget(self._sc_qc_import_btn)

        self._sc_qc_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export"
        )
        header.addWidget(self._sc_qc_export_btn)

        layout.addLayout(header)

        self._sc_qc_btn_container = _DropContainer()
        self._sc_qc_btn_container.setStyleSheet("background: transparent;")
        self._sc_qc_btn_layout = _FlowLayout(self._sc_qc_btn_container, spacing=4)
        self._sc_qc_btn_layout.setContentsMargins(0, 0, 0, 0)
        self._sc_qc_btn_container.set_flow_layout(self._sc_qc_btn_layout)
        self._sc_qc_btn_container.order_changed.connect(self._sc_on_quick_cmd_reorder)
        layout.addWidget(self._sc_qc_btn_container)

        return frame

    # --- status bar ---

    def _build_sc_status_bar(self):
        frame = QFrame()
        frame.setObjectName("scStatusBar")
        frame.setFixedHeight(24)
        frame.setStyleSheet("""
            QFrame#scStatusBar {
                background-color: #050a1d;
                border-top: 1px solid #1a2d57;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QLabel { font-size: 10px; background: transparent; }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(16)

        self._sc_status_port_label = QLabel("● Port: Unconnected")
        self._sc_status_port_label.setStyleSheet("color: #f87171;")
        layout.addWidget(self._sc_status_port_label)

        self._sc_status_baud_label = QLabel("Baud rate: -")
        self._sc_status_baud_label.setStyleSheet("color: #7b8fa5;")
        layout.addWidget(self._sc_status_baud_label)

        self._sc_status_rx_label = QLabel("RX: 0 B")
        self._sc_status_rx_label.setStyleSheet("color: #2dd4bf;")
        layout.addWidget(self._sc_status_rx_label)

        self._sc_status_tx_label = QLabel("TX: 0 B")
        self._sc_status_tx_label.setStyleSheet("color: #2dd4bf;")
        layout.addWidget(self._sc_status_tx_label)

        layout.addStretch()

        return frame

    # --- signal binding ---

    def _bind_sc_signals(self):
        self._sc_connect_btn.clicked.connect(self._sc_on_connect_toggle)
        self._sc_pause_btn.clicked.connect(self._sc_on_pause)
        self._sc_stop_btn.clicked.connect(self._sc_on_stop)
        self._sc_refresh_btn.clicked.connect(self._sc_on_refresh)
        self._sc_add_log_btn.clicked.connect(self._sc_on_add_log_panel)
        self._sc_remove_log_btn.clicked.connect(self._sc_on_remove_log_panel)
        self._sc_sidebar_toggle_btn.clicked.connect(self._sc_on_sidebar_toggle)
        self._sc_settings_btn.clicked.connect(self._sc_open_settings_dialog)

        self._sc_filter_btn.clicked.connect(self._sc_on_filter_toggle)
        self._sc_filter_input.textChanged.connect(self._sc_apply_filter)
        self._sc_filter_regex_cb.toggled.connect(lambda: self._sc_apply_filter())
        self._sc_filter_case_cb.toggled.connect(lambda: self._sc_apply_filter())
        self._sc_filter_invert_cb.toggled.connect(lambda: self._sc_apply_filter())
        self._sc_filter_before_spin.valueChanged.connect(lambda: self._sc_apply_filter())
        self._sc_filter_after_spin.valueChanged.connect(lambda: self._sc_apply_filter())
        self._sc_copy_btn.clicked.connect(self._sc_copy_logs)
        self._sc_export_btn.clicked.connect(self._sc_export_logs)
        self._sc_clear_btn.clicked.connect(self._sc_clear_logs)
        self._sc_scroll_lock_btn.clicked.connect(
            lambda c: setattr(self, '_sc_auto_scroll', c)
        )

        self._sc_send_btn.clicked.connect(self._sc_on_send)
        self._sc_send_input.returnPressed.connect(self._sc_on_send)

        self._sc_qc_add_btn.clicked.connect(self._sc_add_quick_cmd)
        self._sc_qc_import_btn.clicked.connect(self._sc_import_quick_cmds)
        self._sc_qc_export_btn.clicked.connect(self._sc_export_quick_cmds)

        self.serial_data_received.connect(self._sc_on_data_received)

    # --- action handlers ---

    def _sc_on_connect_toggle(self):
        if self._serial_connected:
            self._sc_do_disconnect()
        else:
            self._sc_do_connect()

    def _sc_do_connect(self):
        port_text = self._sc_port_combo.currentText()
        if not port_text or port_text.startswith("No "):
            self._sc_append_system("[ERROR] No valid port selected")
            return

        port = port_text.split()[0]

        baud_text = self._sc_baud_combo.currentText().strip()
        try:
            baudrate = int(baud_text)
        except ValueError:
            self._sc_append_system(f"[ERROR] Invalid baud rate: {baud_text}")
            return

        databit = int(self._sc_databit_combo.currentText())
        stopbit_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
        stopbits = stopbit_map.get(self._sc_stopbit_combo.currentText(), serial.STOPBITS_ONE)
        parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
                       "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
        parity = parity_map.get(self._sc_parity_combo.currentText(), serial.PARITY_NONE)
        flow = self._sc_flow_combo.currentText()
        xonxoff = flow == "XON/XOFF"
        rtscts = flow == "RTS/CTS"

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_baudrate = baudrate
            self._serial_connected = True
            self._sc_update_connect_ui(True)
            self._sc_append_system(f"[INFO] Mock connected: {port} @ {baudrate}")
            self.serial_connection_changed.emit(True)
            return

        try:
            conn = serial.Serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=stopbits, parity=parity, xonxoff=xonxoff,
                rtscts=rtscts, timeout=0.1,
            )
            self._serial_conn = conn
            self._serial_port = port
            self._serial_baudrate = baudrate
            self._serial_connected = True
            self._sc_update_connect_ui(True)
            self._sc_append_system(f"[INFO] Connected: {port} @ {baudrate}")
            self.serial_connection_changed.emit(True)
            self._start_serial_read()
        except Exception as e:
            self._sc_append_system(f"[ERROR] Connection failed: {e}")

    def _sc_do_disconnect(self):
        self._stop_serial_read()
        try:
            if self._serial_conn and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception as e:
            self._sc_append_system(f"[WARN] Close error: {e}")
        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False
        self._sc_update_connect_ui(False)
        self._sc_append_system("[INFO] Disconnected")
        self.serial_connection_changed.emit(False)

    def _sc_update_connect_ui(self, connected):
        if connected:
            self._sc_connect_btn.setText("Disconnect")
            self._sc_connect_btn.setStyleSheet("""
                QPushButton {
                    min-height: 0px; max-height: 20px; padding: 2px 8px; border-radius: 6px;
                    background-color: transparent; color: #f87171; font-size: 10px;
                    border: none;
                }
                QPushButton:hover { background-color: #2a0f1a; }
                QPushButton:pressed { background-color: #1e0a12; }
            """)
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "disconnect.svg"), "#f87171", 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText(f"● Port: {self._serial_port}")
            self._sc_status_port_label.setStyleSheet("color: #4ade80; font-size: 10px; background: transparent;")
            baud = getattr(self, '_serial_baudrate', '-')
            self._sc_status_baud_label.setText(f"Baud rate: {baud}")
        else:
            self._sc_connect_btn.setText("Connect")
            self._sc_connect_btn.setStyleSheet("""
                QPushButton {
                    min-height: 0px; max-height: 20px; padding: 2px 8px; border-radius: 6px;
                    background-color: transparent; color: #4ade80; font-size: 10px;
                    border: none;
                }
                QPushButton:hover { background-color: #0a2818; }
                QPushButton:pressed { background-color: #071e12; }
            """)
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "#4ade80", 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText("● Port: Unconnected")
            self._sc_status_port_label.setStyleSheet("color: #f87171; font-size: 10px; background: transparent;")
            self._sc_status_baud_label.setText("Baud rate: -")

        self._sc_port_combo.setEnabled(not connected)
        self._sc_baud_combo.setEnabled(not connected)

    def _sc_on_pause(self, checked):
        self._sc_paused = checked
        self._sc_pause_btn.setText("Resume" if checked else "Pause")

    def _sc_on_stop(self):
        if self._serial_connected:
            self._sc_do_disconnect()

    def _sc_on_refresh(self):
        self._sc_port_combo.clear()
        if DEBUG_MOCK:
            self._sc_port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            self._sc_append_system("[INFO] Mock port refreshed")
            return
        try:
            ports = serial.tools.list_ports.comports()
            if ports:
                for p in ports:
                    self._sc_port_combo.addItem(f"{p.device} - {p.description}")
                self._sc_append_system(f"[INFO] Found {len(ports)} serial port(s)")
            else:
                self._sc_port_combo.addItem("No serial ports found")
                self._sc_append_system("[WARN] No serial ports found")
        except Exception as e:
            self._sc_append_system(f"[ERROR] Refresh failed: {e}")

    def _sc_on_add_log_panel(self):
        if len(self._sc_extra_log_panels) >= 3:
            self._sc_append_system("[WARN] Maximum 4 LOG panels supported")
            return
        dlg = _AddLogPanelDialog(parent=None)
        if dlg.exec() != QDialog.Accepted:
            return
        panel_info = dlg.get_config()
        panel = self._build_extra_log_panel(panel_info)
        self._sc_extra_log_panels.append(panel)
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(True)
        self._sc_append_system(
            f"[INFO] New LOG panel: {panel_info.get('title', 'Log')} "
            f"({panel_info.get('port', 'N/A')} @ {panel_info.get('baudrate', 'N/A')})"
        )
        if panel_info.get("auto_connect", False):
            self._sc_extra_panel_connect(panel)

    def _sc_on_remove_log_panel(self):
        if not self._sc_extra_log_panels:
            return
        panel = self._sc_extra_log_panels.pop()
        self._sc_extra_panel_disconnect(panel)
        panel["frame"].setParent(None)
        panel["frame"].deleteLater()
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(len(self._sc_extra_log_panels) > 0)
        self._sc_append_system("[INFO] LOG panel removed")

    def _sc_relayout_log_panels(self):
        while self._sc_log_grid.count():
            item = self._sc_log_grid.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        self._sc_log_grid.setRowStretch(0, 0)
        self._sc_log_grid.setRowStretch(1, 0)
        self._sc_log_grid.setColumnStretch(0, 0)
        self._sc_log_grid.setColumnStretch(1, 0)

        total = 1 + len(self._sc_extra_log_panels)

        if total == 1:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
        elif total == 2:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
        elif total == 3:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[1]["frame"], 1, 0)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
            self._sc_log_grid.setRowStretch(0, 1)
            self._sc_log_grid.setRowStretch(1, 1)
        elif total == 4:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[1]["frame"], 1, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[2]["frame"], 1, 1)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
            self._sc_log_grid.setRowStretch(0, 1)
            self._sc_log_grid.setRowStretch(1, 1)

        self._sc_log_area.show()
        for p in self._sc_extra_log_panels:
            p["frame"].show()

    def _build_extra_log_panel(self, config):
        frame = QFrame()
        frame.setObjectName("scLogFrame")
        frame.setStyleSheet("""
            QFrame#scLogFrame {
                background-color: #09142e;
                border: 1px solid #1a2d57;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(8, 6, 8, 4)
        toolbar.setSpacing(6)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), "#7b8fa5", 14)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(14, 14))
        icon_label.setFixedSize(16, 16)
        icon_label.setStyleSheet("background: transparent;")
        toolbar.addWidget(icon_label)

        title_text = config.get("title", "Serial Log")
        title = QLabel(title_text)
        title.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 700; background: transparent;")
        toolbar.addWidget(title)

        toolbar.addStretch()

        clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear"
        )
        toolbar.addWidget(clear_btn)

        scroll_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll"
        )
        scroll_btn.setCheckable(True)
        scroll_btn.setChecked(True)
        toolbar.addWidget(scroll_btn)

        layout.addLayout(toolbar)

        log_edit = QTextEdit()
        log_edit.setReadOnly(True)
        log_edit.setStyleSheet("""
            QTextEdit {
                background-color: #020618; border: none; border-top: 1px solid #1a2d57;
                color: #7cecc8; font-family: Consolas, "Courier New", monospace; font-size: 11px;
                padding: 6px 8px;
            }
        """ + SCROLLBAR_STYLE)
        layout.addWidget(log_edit, 1)

        status_bar = QFrame()
        status_bar.setObjectName("scStatusBar")
        status_bar.setFixedHeight(24)
        status_bar.setStyleSheet("""
            QFrame#scStatusBar {
                background-color: #050a1d;
                border-top: 1px solid #1a2d57;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QLabel { font-size: 10px; background: transparent; }
        """)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(10, 0, 10, 0)
        sb_layout.setSpacing(16)

        port_label = QLabel(f"Port: {config.get('port', 'Unconnected')}")
        port_label.setStyleSheet("color: #f87171;")
        sb_layout.addWidget(port_label)

        baud_label = QLabel(f"Baud rate: {config.get('baudrate', '-')}")
        baud_label.setStyleSheet("color: #7b8fa5;")
        sb_layout.addWidget(baud_label)

        rx_label = QLabel("RX: 0 B")
        rx_label.setStyleSheet("color: #2dd4bf;")
        sb_layout.addWidget(rx_label)

        tx_label = QLabel("TX: 0 B")
        tx_label.setStyleSheet("color: #2dd4bf;")
        sb_layout.addWidget(tx_label)

        sb_layout.addStretch()
        layout.addWidget(status_bar)

        panel = {
            "frame": frame,
            "log_edit": log_edit,
            "clear_btn": clear_btn,
            "scroll_btn": scroll_btn,
            "port_label": port_label,
            "baud_label": baud_label,
            "rx_label": rx_label,
            "tx_label": tx_label,
            "config": config,
            "conn": None,
            "read_thread": None,
            "read_worker": None,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "auto_scroll": True,
            "all_logs": [],
            "pending_html": [],
        }

        clear_btn.clicked.connect(lambda: self._sc_extra_panel_clear(panel))
        scroll_btn.clicked.connect(lambda c: panel.__setitem__("auto_scroll", c))

        if log_edit.verticalScrollBar():
            log_edit.verticalScrollBar().valueChanged.connect(
                lambda val, p=panel: self._sc_extra_panel_on_scroll(p, val)
            )

        return panel

    def _sc_extra_panel_clear(self, panel):
        panel["all_logs"].clear()
        panel["pending_html"].clear()
        panel["log_edit"].clear()
        panel["rx_bytes"] = 0
        panel["tx_bytes"] = 0
        panel["rx_label"].setText("RX: 0 B")
        panel["tx_label"].setText("TX: 0 B")

    def _sc_extra_panel_on_scroll(self, panel, value):
        sb = panel["log_edit"].verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and panel["auto_scroll"]:
                panel["auto_scroll"] = False
                panel["scroll_btn"].setChecked(False)
            elif at_bottom and not panel["auto_scroll"]:
                panel["auto_scroll"] = True
                panel["scroll_btn"].setChecked(True)

    def _sc_extra_panel_connect(self, panel):
        config = panel["config"]
        port = config.get("port", "")
        baudrate = config.get("baudrate", 115200)

        if not port:
            return

        if DEBUG_MOCK:
            panel["conn"] = None
            panel["port_label"].setText(f"Port: MOCK")
            panel["port_label"].setStyleSheet("color: #4ade80; font-size: 10px; background: transparent;")
            self._sc_extra_panel_append_log(panel, "[INFO] Mock connected", "#60a5fa")
            return

        try:
            databit = config.get("databit", 8)
            stopbit_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
            stopbits = stopbit_map.get(config.get("stopbit", "1"), serial.STOPBITS_ONE)
            parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
                          "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
            parity = parity_map.get(config.get("parity", "None"), serial.PARITY_NONE)
            flow = config.get("flow", "None")

            conn = serial.Serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=stopbits, parity=parity,
                xonxoff=(flow == "XON/XOFF"), rtscts=(flow == "RTS/CTS"),
                timeout=0.1,
            )
            panel["conn"] = conn
            panel["port_label"].setText(f"Port: {port}")
            panel["port_label"].setStyleSheet("color: #4ade80; font-size: 10px; background: transparent;")
            self._sc_extra_panel_append_log(panel, f"[INFO] Connected: {port} @ {baudrate}", "#60a5fa")
            self._sc_extra_panel_start_read(panel)
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Connection failed: {e}", "#f87171")

    def _sc_extra_panel_disconnect(self, panel):
        if panel.get("read_worker"):
            panel["read_worker"].stop()
        if panel.get("read_thread") and panel["read_thread"].isRunning():
            panel["read_thread"].quit()
            panel["read_thread"].wait(2000)
        panel["read_thread"] = None
        panel["read_worker"] = None
        try:
            if panel["conn"] and panel["conn"].is_open:
                panel["conn"].close()
        except Exception:
            pass
        panel["conn"] = None

    def _sc_extra_panel_start_read(self, panel):
        if panel["conn"] is None or not panel["conn"].is_open:
            return
        worker = _SerialReadWorker(panel["conn"])
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.data_received.connect(lambda data, p=panel: self._sc_extra_panel_on_data(p, data))
        worker.error.connect(lambda err, p=panel: self._sc_extra_panel_append_log(p, f"[ERROR] {err}", "#f87171"))
        panel["read_thread"] = thread
        panel["read_worker"] = worker
        thread.start()

    def _sc_extra_panel_on_data(self, panel, data: bytes):
        panel["rx_bytes"] += len(data)
        panel["rx_label"].setText(self._sc_format_bytes("RX", panel["rx_bytes"]))
        display = data.decode("utf-8", errors="replace")
        for line in display.splitlines():
            if line.strip():
                self._sc_extra_panel_append_log(panel, f"[RX] {line}", "#4ade80")

    def _sc_extra_panel_append_log(self, panel, message, color="#7cecc8"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:#4a5e82;">{ts}</span> '
        html = f'{ts_html}<span style="color:{color};">{escaped}</span>'
        panel["all_logs"].append((message, html))
        panel["pending_html"].append(html)

    def _sc_flush_extra_panels(self):
        for panel in self._sc_extra_log_panels:
            if not panel["pending_html"]:
                continue
            batch = panel["pending_html"]
            panel["pending_html"] = []
            for html in batch:
                panel["log_edit"].append(html)
            if panel["auto_scroll"]:
                sb = panel["log_edit"].verticalScrollBar()
                if sb:
                    sb.setValue(sb.maximum())

    def _sc_on_sidebar_toggle(self, checked):
        self._sc_sidebar_visible = checked
        self._sc_sidebar_widget.setVisible(checked)

    def _sc_open_settings_dialog(self):
        dlg = _SerialSettingsDialog(self)

        dlg.port_combo.clear()
        for i in range(self._sc_port_combo.count()):
            dlg.port_combo.addItem(self._sc_port_combo.itemText(i))
        dlg.port_combo.setCurrentIndex(self._sc_port_combo.currentIndex())

        dlg.baud_combo.setCurrentText(self._sc_baud_combo.currentText())

        dlg.databit_combo.setCurrentText(self._sc_databit_combo.currentText())
        dlg.flow_combo.setCurrentText(self._sc_flow_combo.currentText())
        dlg.stopbit_combo.setCurrentText(self._sc_stopbit_combo.currentText())
        dlg.parity_combo.setCurrentText(self._sc_parity_combo.currentText())

        dlg.rx_hex_toggle.set_value("HEX" if self._sc_rx_display_hex else "ASCII")
        dlg.show_time_cb.setChecked(self._sc_show_timestamp)
        dlg.rx_max_lines_spin.setValue(getattr(self, '_sc_max_log_lines', 10000))

        dlg.tx_hex_toggle.set_value("HEX" if self._sc_tx_display_hex else "ASCII")
        dlg.auto_resend_cb.setChecked(self._sc_auto_resend)
        dlg.resend_spin.setValue(self._sc_resend_spin.value())
        idx = self._sc_ending_combo.currentIndex()
        if 0 <= idx < dlg.ending_combo.count():
            dlg.ending_combo.setCurrentIndex(idx)
        dlg.show_send_cb.setChecked(self._sc_show_send)
        dlg.line_by_line_cb.setChecked(self._sc_line_by_line)

        dlg.log_auto_save_cb.setChecked(getattr(self, '_sc_log_auto_save', False))
        dlg.log_save_path_edit.setText(getattr(self, '_sc_log_save_path', ''))

        dlg.display_font_combo.setCurrentText(getattr(self, '_sc_display_font', 'Consolas'))
        dlg.display_font_size_spin.setValue(getattr(self, '_sc_display_font_size', 11))
        dlg.display_auto_scroll_cb.setChecked(self._sc_auto_scroll)
        dlg.display_word_wrap_cb.setChecked(getattr(self, '_sc_word_wrap', True))

        if dlg.exec() == QDialog.Accepted:
            self._sc_port_combo.setCurrentIndex(dlg.port_combo.currentIndex())
            self._sc_baud_combo.setCurrentText(dlg.baud_combo.currentText())
            self._sc_databit_combo.setCurrentText(dlg.databit_combo.currentText())
            self._sc_flow_combo.setCurrentText(dlg.flow_combo.currentText())
            self._sc_stopbit_combo.setCurrentText(dlg.stopbit_combo.currentText())
            self._sc_parity_combo.setCurrentText(dlg.parity_combo.currentText())

            rx_val = dlg.rx_hex_toggle.value()
            self._sc_rx_display_hex = rx_val == "HEX"
            self._sc_rx_toggle.set_value(rx_val)

            self._sc_show_timestamp = dlg.show_time_cb.isChecked()
            self._sc_rx_show_time_cb.setChecked(self._sc_show_timestamp)
            self._sc_max_log_lines = dlg.rx_max_lines_spin.value()

            tx_val = dlg.tx_hex_toggle.value()
            self._sc_tx_display_hex = tx_val == "HEX"
            self._sc_tx_toggle.set_value(tx_val)

            self._sc_auto_resend_cb.setChecked(dlg.auto_resend_cb.isChecked())
            self._sc_resend_spin.setValue(dlg.resend_spin.value())

            ending_idx = dlg.ending_combo.currentIndex()
            self._sc_ending_combo.setCurrentIndex(ending_idx)

            self._sc_show_send_cb.setChecked(dlg.show_send_cb.isChecked())
            self._sc_line_by_line_cb.setChecked(dlg.line_by_line_cb.isChecked())

            self._sc_log_auto_save = dlg.log_auto_save_cb.isChecked()
            self._sc_log_save_path = dlg.log_save_path_edit.text()

            font_family = dlg.display_font_combo.currentText()
            font_size = dlg.display_font_size_spin.value()
            self._sc_display_font = font_family
            self._sc_display_font_size = font_size
            self._sc_log_edit.setStyleSheet(f"""
                QTextEdit {{
                    background-color: #020618; border: none; border-top: 1px solid #1a2d57;
                    color: #7cecc8; font-family: {font_family}, monospace; font-size: {font_size}px;
                    padding: 6px 8px;
                }}
            """ + SCROLLBAR_STYLE)

            self._sc_auto_scroll = dlg.display_auto_scroll_cb.isChecked()
            self._sc_scroll_lock_btn.setChecked(self._sc_auto_scroll)

            self._sc_word_wrap = dlg.display_word_wrap_cb.isChecked()
            from PySide6.QtWidgets import QTextEdit as _QTE
            self._sc_log_edit.setLineWrapMode(
                _QTE.WidgetWidth if self._sc_word_wrap else _QTE.NoWrap
            )

    def _sc_on_filter_toggle(self, checked):
        self._sc_filter_row.setVisible(checked)
        if not checked:
            self._sc_filter_input.clear()
            self._sc_filter_match_label.setText("")
            self._sc_filter_dirty = False
            self._sc_filter_last_count = len(self._sc_all_logs)
            self._sc_rebuild_log_view()

    def _sc_apply_filter(self, _text=None):
        self._sc_filter_dirty = False
        pattern = self._sc_filter_input.text().strip()
        if not pattern:
            self._sc_filter_last_count = len(self._sc_all_logs)
            self._sc_rebuild_log_view()
            self._sc_filter_match_label.setText("")
            return

        use_regex = self._sc_filter_regex_cb.isChecked()
        case_sensitive = self._sc_filter_case_cb.isChecked()
        invert = self._sc_filter_invert_cb.isChecked()
        before = self._sc_filter_before_spin.value()
        after = self._sc_filter_after_spin.value()

        matched_indices = self._sc_get_matched_indices(
            pattern, use_regex, case_sensitive, invert
        )
        self._sc_filter_match_label.setText(f"Matched: {len(matched_indices)} lines")

        visible = set()
        for idx in matched_indices:
            start = max(0, idx - before)
            end = min(len(self._sc_all_logs) - 1, idx + after)
            for i in range(start, end + 1):
                visible.add(i)

        self._sc_log_edit.clear()
        prev_shown = -2
        for i in sorted(visible):
            if before > 0 or after > 0:
                if prev_shown >= 0 and i - prev_shown > 1:
                    self._sc_log_edit.append(
                        '<span style="color:#3a4a6a;">  ───</span>'
                    )
            self._sc_log_edit.append(self._sc_all_logs[i][1])
            prev_shown = i
        self._sc_filter_last_count = len(self._sc_all_logs)
        if self._sc_auto_scroll:
            self._sc_scroll_to_bottom()

    def _sc_rebuild_log_view(self):
        self._sc_log_edit.clear()
        cursor = self._sc_log_edit.textCursor()
        cursor.beginEditBlock()
        for _raw, html in self._sc_all_logs:
            self._sc_log_edit.append(html)
        cursor.endEditBlock()
        if self._sc_auto_scroll:
            self._sc_scroll_to_bottom()

    def _sc_is_filter_active(self):
        return (self._sc_filter_row.isVisible()
                and bool(self._sc_filter_input.text().strip()))

    def _sc_get_matched_indices(self, pattern, use_regex, case_sensitive, invert):
        matched = []
        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return matched

        for i, (raw, _html) in enumerate(self._sc_all_logs):
            if compiled is not None:
                hit = bool(compiled.search(raw))
            elif case_sensitive:
                hit = pattern in raw
            else:
                hit = pattern.lower() in raw.lower()
            if invert:
                hit = not hit
            if hit:
                matched.append(i)
        return matched

    def _sc_copy_logs(self):
        cb = QApplication.clipboard()
        if not cb:
            return
        lines = []
        if self._sc_filter_row.isVisible() and self._sc_filter_input.text().strip():
            pattern = self._sc_filter_input.text().strip()
            use_regex = self._sc_filter_regex_cb.isChecked()
            case_sensitive = self._sc_filter_case_cb.isChecked()
            invert = self._sc_filter_invert_cb.isChecked()
            before = self._sc_filter_before_spin.value()
            after = self._sc_filter_after_spin.value()
            matched_indices = self._sc_get_matched_indices(
                pattern, use_regex, case_sensitive, invert
            )
            visible = set()
            for idx in matched_indices:
                start = max(0, idx - before)
                end = min(len(self._sc_all_logs) - 1, idx + after)
                for i in range(start, end + 1):
                    visible.add(i)
            prev_shown = -2
            for i in sorted(visible):
                if (before > 0 or after > 0) and prev_shown >= 0 and i - prev_shown > 1:
                    lines.append("  ───")
                lines.append(self._sc_all_logs[i][0])
                prev_shown = i
        else:
            for raw, _html in self._sc_all_logs:
                lines.append(raw)
        cb.setText("\n".join(lines))

    def _sc_export_logs(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            None, "Export Logs", f"serial_log_{ts}.txt", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                for raw, _ in self._sc_all_logs:
                    f.write(raw + "\n")

    def _sc_clear_logs(self):
        self._sc_all_logs.clear()
        self._sc_log_edit.clear()
        self._sc_rx_bytes = 0
        self._sc_tx_bytes = 0
        self._sc_status_rx_label.setText("RX: 0 B")
        self._sc_status_tx_label.setText("TX: 0 B")
        self._sc_filter_last_count = 0
        self._sc_filter_dirty = False
        self._sc_filter_match_label.setText("")

    def _sc_on_user_scroll(self, value):
        sb = self._sc_log_edit.verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and self._sc_auto_scroll:
                self._sc_auto_scroll = False
                self._sc_scroll_lock_btn.setChecked(False)
            elif at_bottom and not self._sc_auto_scroll:
                self._sc_auto_scroll = True
                self._sc_scroll_lock_btn.setChecked(True)

    def _sc_scroll_to_bottom(self):
        sb = self._sc_log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _sc_on_send(self):
        text = self._sc_send_input.text()
        if not text:
            return

        if self._sc_line_by_line:
            lines = text.split("\\n")
        else:
            lines = [text]

        for line in lines:
            if self._sc_tx_display_hex:
                try:
                    data = bytes.fromhex(line.replace(" ", ""))
                except ValueError:
                    self._sc_append_system(f"[ERROR] Invalid HEX: {line}")
                    return
            else:
                data = (line + self._sc_line_ending).encode("utf-8")

            ok = self.serial_send(data)
            if ok:
                self._sc_tx_bytes += len(data)
                self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
                if self._sc_show_send:
                    display = line if not self._sc_tx_display_hex else data.hex(' ')
                    self._sc_append_log(f"[TX] {display}", "#60a5fa")
            else:
                self._sc_append_system("[ERROR] Send failed, serial not connected")

        if text not in self._sc_send_history:
            self._sc_send_history.insert(0, text)
            if len(self._sc_send_history) > 50:
                self._sc_send_history.pop()
            self._sc_history_combo.clear()
            self._sc_history_combo.addItems(self._sc_send_history)

        self._sc_send_input.clear()

    def _sc_on_data_received(self, data: bytes):
        if self._sc_paused:
            return
        self._sc_rx_bytes += len(data)
        self._sc_status_rx_label.setText(self._sc_format_bytes("RX", self._sc_rx_bytes))

        if self._sc_rx_display_hex:
            display = data.hex(' ')
        else:
            display = data.decode("utf-8", errors="replace")
            display = display.replace("\x00", "")
            display = "".join(
                ch if ch == "\n" or ch == "\r" or ch == "\t" or (ord(ch) >= 0x20) else ""
                for ch in display
            )

        for line in display.splitlines():
            if line.strip():
                self._sc_append_log(f"[RX] {line}", "#4ade80")

    def _sc_on_auto_resend_toggled(self, checked):
        self._sc_auto_resend = checked
        if checked:
            self._sc_resend_timer.setInterval(self._sc_resend_spin.value())
            self._sc_resend_timer.start()
        else:
            self._sc_resend_timer.stop()

    def _sc_on_resend_tick(self):
        text = self._sc_send_input.text()
        if text and self._serial_connected:
            if self._sc_tx_display_hex:
                try:
                    data = bytes.fromhex(text.replace(" ", ""))
                except ValueError:
                    return
            else:
                data = (text + self._sc_line_ending).encode("utf-8")
            ok = self.serial_send(data)
            if ok:
                self._sc_tx_bytes += len(data)
                self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))

    # --- quick commands ---

    def _sc_add_quick_cmd(self):
        prefill_cmd = self._sc_send_input.text().strip()
        dlg = _QuickCmdDialog(name="", cmd=prefill_cmd, parent=None)
        if dlg.exec() != QDialog.Accepted:
            return
        name = dlg.get_name()
        cmd = dlg.get_cmd()
        if not cmd:
            return
        for item in self._sc_quick_commands:
            if item["name"] == name and item["cmd"] == cmd:
                return
        self._sc_quick_commands.append({"name": name, "cmd": cmd})
        self._sc_refresh_quick_buttons()

    def _sc_refresh_quick_buttons(self):
        self._sc_qc_btn_layout.clear()
        for idx, entry in enumerate(self._sc_quick_commands):
            name = entry.get("name", "")
            cmd = entry.get("cmd", "")
            label = name if name else cmd
            btn = _DraggableQuickButton(label, idx)
            btn.setToolTip(f"Command: {cmd}\n(Drag to reorder)")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0e1a35; border: 1px solid #1f315d; border-radius: 4px;
                    color: #c8d5e2; font-size: 10px; padding: 2px 8px; min-height: 18px;
                }
                QPushButton:hover { background-color: #152045; }
                QPushButton:pressed { background-color: #0a1228; }
                QToolTip {
                    background-color: #091023; border: 1px solid #1f315d;
                    color: #c8d5e2; font-size: 10px; padding: 4px 8px;
                }
            """)
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, e=entry, b=btn: self._sc_qc_context_menu(e, b, pos)
            )
            btn.clicked.connect(lambda checked=False, c=cmd: self._sc_send_quick(c))
            self._sc_qc_btn_layout.addWidget(btn)

    def _sc_on_quick_cmd_reorder(self):
        src = self._sc_qc_btn_container.property("_drag_source")
        dst = self._sc_qc_btn_container.property("_drag_target")
        if src is None or dst is None:
            return
        cmds = self._sc_quick_commands
        if 0 <= src < len(cmds) and 0 <= dst < len(cmds):
            item = cmds.pop(src)
            cmds.insert(dst, item)
            self._sc_refresh_quick_buttons()

    def _sc_send_quick(self, cmd):
        if self._sc_tx_display_hex:
            try:
                data = bytes.fromhex(cmd.replace(" ", ""))
            except ValueError:
                self._sc_append_system(f"[ERROR] Invalid HEX: {cmd}")
                return
        else:
            data = (cmd + self._sc_line_ending).encode("utf-8")
        ok = self.serial_send(data)
        if ok:
            self._sc_tx_bytes += len(data)
            self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
            if self._sc_show_send:
                self._sc_append_log(f"[TX] {cmd}", "#60a5fa")

    def _sc_qc_context_menu(self, entry, btn, pos):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background-color: #091023; border: 1px solid #1f315d; border-radius: 6px; color: #c8d5e2; font-size: 10px; }
            QMenu::item { padding: 4px 16px; }
            QMenu::item:selected { background-color: #152045; }
        """)
        edit_action = menu.addAction("Edit")
        del_action = menu.addAction("Delete")
        action = menu.exec(btn.mapToGlobal(pos))
        if action == del_action:
            if entry in self._sc_quick_commands:
                self._sc_quick_commands.remove(entry)
                self._sc_refresh_quick_buttons()
        elif action == edit_action:
            dlg = _QuickCmdDialog(
                name=entry.get("name", ""),
                cmd=entry.get("cmd", ""),
                parent=None,
            )
            if dlg.exec() == QDialog.Accepted:
                entry["name"] = dlg.get_name()
                entry["cmd"] = dlg.get_cmd()
                self._sc_refresh_quick_buttons()

    def _sc_import_quick_cmds(self):
        path, _ = QFileDialog.getOpenFileName(
            None, "Import Quick Commands", "", "JSON Files (*.json);;All Files (*)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    cmds = []
                    for item in data:
                        if isinstance(item, dict) and "cmd" in item:
                            cmds.append({"name": item.get("name", ""), "cmd": item["cmd"]})
                        elif isinstance(item, str):
                            cmds.append({"name": "", "cmd": item})
                    self._sc_quick_commands = cmds
                    self._sc_refresh_quick_buttons()
                    self._sc_append_system(f"[INFO] Imported {len(self._sc_quick_commands)} command(s)")
            except Exception as e:
                self._sc_append_system(f"[ERROR] Import failed: {e}")

    def _sc_export_quick_cmds(self):
        if not self._sc_quick_commands:
            return
        path, _ = QFileDialog.getSaveFileName(
            None, "Export Quick Commands", "quick_commands.json", "JSON Files (*.json);;All Files (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._sc_quick_commands, f, ensure_ascii=False, indent=2)
            self._sc_append_system(f"[INFO] Exported {len(self._sc_quick_commands)} command(s)")

    # --- log helpers ---

    def _sc_append_log(self, message: str, color: str = "#7cecc8"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3] if self._sc_show_timestamp else ""
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:#4a5e82;">{ts}</span> ' if ts else ""
        html = f'{ts_html}<span style="color:{color};">{escaped}</span>'
        self._sc_all_logs.append((message, html))
        if self._sc_is_filter_active():
            self._sc_filter_dirty = True
        else:
            self._sc_pending_html.append(html)

    def _sc_flush_pending_logs(self):
        if self._sc_is_filter_active():
            if getattr(self, '_sc_filter_dirty', False):
                self._sc_filter_dirty = False
                before = self._sc_filter_before_spin.value()
                after = self._sc_filter_after_spin.value()
                if before == 0 and after == 0:
                    self._sc_flush_filter_incremental()
                else:
                    self._sc_apply_filter()
        elif self._sc_pending_html:
            batch = self._sc_pending_html
            self._sc_pending_html = []
            cursor = self._sc_log_edit.textCursor()
            cursor.beginEditBlock()
            for html in batch:
                self._sc_log_edit.append(html)
            cursor.endEditBlock()
            if self._sc_auto_scroll:
                self._sc_scroll_to_bottom()
        self._sc_flush_extra_panels()

    def _sc_flush_filter_incremental(self):
        pattern = self._sc_filter_input.text().strip()
        if not pattern:
            return
        use_regex = self._sc_filter_regex_cb.isChecked()
        case_sensitive = self._sc_filter_case_cb.isChecked()
        invert = self._sc_filter_invert_cb.isChecked()

        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return

        start_idx = self._sc_filter_last_count
        new_html = []
        total_match = 0

        for i in range(len(self._sc_all_logs)):
            raw = self._sc_all_logs[i][0]
            if compiled is not None:
                hit = bool(compiled.search(raw))
            elif case_sensitive:
                hit = pattern in raw
            else:
                hit = pattern.lower() in raw.lower()
            if invert:
                hit = not hit
            if hit:
                total_match += 1
                if i >= start_idx:
                    new_html.append(self._sc_all_logs[i][1])

        self._sc_filter_last_count = len(self._sc_all_logs)
        self._sc_filter_match_label.setText(f"Matched: {total_match} lines")

        if new_html:
            cursor = self._sc_log_edit.textCursor()
            cursor.beginEditBlock()
            for html in new_html:
                self._sc_log_edit.append(html)
            cursor.endEditBlock()
            if self._sc_auto_scroll:
                self._sc_scroll_to_bottom()

    def _sc_append_system(self, message: str):
        color_map = {"INFO": "#60a5fa", "WARN": "#facc15", "ERROR": "#f87171"}
        tag = ""
        for t in color_map:
            if f"[{t}]" in message:
                tag = t
                break
        color = color_map.get(tag, "#6b83b0")
        self._sc_append_log(message, color)

    @staticmethod
    def _sc_format_bytes(prefix, n):
        if n < 1024:
            return f"{prefix}: {n} B"
        elif n < 1024 * 1024:
            return f"{prefix}: {n / 1024:.1f} KB"
        else:
            return f"{prefix}: {n / (1024 * 1024):.2f} MB"

    # --- ui helpers ---

    @staticmethod
    def _make_sc_btn(svg_path, text):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                min-height: 0px; max-height: 20px; padding: 2px 8px; border-radius: 6px;
                background-color: #0e1a35; color: #c8d5e2; font-size: 10px; border: none;
            }
            QPushButton:hover { background-color: #152045; }
            QPushButton:pressed { background-color: #0a1228; }
            QPushButton:checked { background-color: #152045; border: 1px solid #6366f1; color: #c8d5e2; }
        """)
        icon = _tinted_svg_icon(svg_path, "#7b8fa5", 12)
        if not icon.isNull():
            btn.setIcon(icon)
        return btn

    @staticmethod
    def _make_sc_section(title):
        grp = QFrame()
        grp.setStyleSheet("""
            QFrame {
                background-color: #091023; border: 1px solid #1a2d57; border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        lbl = QLabel(title)
        lbl.setStyleSheet("color: #9bafc5; font-size: 10px; font-weight: 700; border: none;")
        layout.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1a2d57; border: none;")
        layout.addWidget(sep)

        grp.setProperty("_inner_layout", layout)
        return grp

    @staticmethod
    def _make_sc_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #7b8fa5; font-size: 10px; background: transparent; border: none;")
        return lbl

    @staticmethod
    def _sc_checkbox_style():
        return """
            QCheckBox { color: #9bafc5; font-size: 10px; background: transparent; spacing: 4px; }
            QCheckBox::indicator {
                width: 14px; height: 14px;
                border: 1px solid #1f315d; border-radius: 3px;
                background-color: #050a1d;
            }
            QCheckBox::indicator:hover {
                border-color: #6366f1;
            }
            QCheckBox::indicator:checked {
                background-color: #6366f1; border-color: #6366f1;
                image: url(""" + os.path.join(_SVG_SERIAL_DIR, "checkmark.svg").replace("\\", "/") + """);
            }
        """


class _DraggableQuickButton(QPushButton):

    _MIME_TYPE = "application/x-quickcmd-index"

    def __init__(self, text, index, parent=None):
        super().__init__(text, parent)
        self._drag_index = index
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._drag_start_pos is None:
            return
        if (event.position().toPoint() - self._drag_start_pos).manhattanLength() < 10:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME_TYPE, str(self._drag_index).encode())
        drag.setMimeData(mime)

        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())

        drag.exec(Qt.MoveAction)
        self._drag_start_pos = None

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)


class _DropContainer(QWidget):

    order_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._flow_layout = None

    def set_flow_layout(self, layout):
        self._flow_layout = layout

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(_DraggableQuickButton._MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(_DraggableQuickButton._MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(_DraggableQuickButton._MIME_TYPE):
            return
        source_index = int(event.mimeData().data(_DraggableQuickButton._MIME_TYPE).data().decode())
        drop_pos = event.position().toPoint()
        target_index = self._index_at_pos(drop_pos)
        if target_index < 0:
            target_index = self._flow_layout.count() - 1 if self._flow_layout else 0
        if source_index != target_index:
            event.acceptProposedAction()
            self.setProperty("_drag_source", source_index)
            self.setProperty("_drag_target", target_index)
            self.order_changed.emit()

    def _index_at_pos(self, pos):
        if not self._flow_layout:
            return -1
        for i in range(self._flow_layout.count()):
            item = self._flow_layout.itemAt(i)
            if item and item.widget() and item.widget().geometry().contains(pos):
                return i
        return -1


class _FlowLayout(QLayout):

    def __init__(self, parent=None, spacing=4):
        super().__init__(parent)
        self._items = []
        self._h_spacing = spacing
        self._v_spacing = spacing

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

    def expandingDirections(self):
        return Qt.Orientation(0)

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
        line_height = 0

        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()

            if x + w > effective.right() + 1 and line_height > 0:
                x = effective.x()
                y = y + line_height + self._v_spacing
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = x + w + self._h_spacing
            line_height = max(line_height, h)

        return y + line_height - rect.y() + m.bottom()

    def clear(self):
        while self._items:
            item = self._items.pop()
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()


class _MiniSlideToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, left="ASCII", right="HEX", parent=None):
        super().__init__(parent)
        self._left = left
        self._right = right
        self._value = left
        self._anim_progress = 0.0

        self.setFixedSize(80, 22)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def value(self):
        return self._value

    def set_value(self, val):
        if val not in (self._left, self._right):
            return
        if val == self._value:
            return
        self._value = val
        target = 1.0 if val == self._right else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = self._right if self._value == self._left else self._left
            self._value = new_val
            target = 1.0 if new_val == self._right else 0.0
            self._anim.stop()
            self._anim.setStartValue(self._anim_progress)
            self._anim.setEndValue(target)
            self._anim.start()
            self.toggled.emit(self._value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        outer_r = 4

        p.setPen(QPen(QColor("#1a2d57"), 1))
        p.setBrush(QColor("#091023"))
        p.drawRoundedRect(QRectF(0, 0, w, h), outer_r, outer_r)

        knob_margin = 2
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_r = 3

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#6366f1"))
        p.drawRoundedRect(QRectF(knob_x, knob_margin, knob_w, knob_h),
                          knob_r, knob_r)

        font = p.font()
        font.setPixelSize(9)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        left_rect = QRectF(0, 0, w / 2, h)
        right_rect = QRectF(w / 2, 0, w / 2, h)

        p.setPen(QColor("#FFFFFF") if self._anim_progress < 0.5 else QColor("#7b8fa5"))
        p.drawText(left_rect, Qt.AlignCenter, self._left)

        p.setPen(QColor("#FFFFFF") if self._anim_progress >= 0.5 else QColor("#7b8fa5"))
        p.drawText(right_rect, Qt.AlignCenter, self._right)

        p.end()


_DLG_STYLE = """
    QDialog {
        background-color: #050b1e;
        color: #c8d5e2;
    }
    QLabel { color: #9bafc5; font-size: 11px; background: transparent; }
    QLabel#dlgSectionTitle {
        color: #e2e8f0; font-size: 12px; font-weight: 700; background: transparent;
        padding-bottom: 2px;
    }
    QFrame#dlgSep { background-color: #1a2d57; }
    QCheckBox { color: #9bafc5; font-size: 11px; background: transparent; spacing: 4px; }
    QCheckBox::indicator {
        width: 15px; height: 15px;
        border: 1px solid #1f315d; border-radius: 3px;
        background-color: #050a1d;
    }
    QCheckBox::indicator:hover { border-color: #6366f1; }
    QCheckBox::indicator:checked {
        background-color: #6366f1; border-color: #6366f1;
        image: url(""" + os.path.join(_SVG_SERIAL_DIR, "checkmark.svg").replace("\\", "/") + """);
    }
    QSpinBox {
        background-color: #050a1d; border: 1px solid #1f315d; border-radius: 4px;
        color: #c8d5e2; font-size: 11px; padding: 2px 6px;
    }
    QSpinBox::up-button, QSpinBox::down-button { width: 14px; }
    QPushButton#dlgOkBtn {
        background-color: #064e3b; border: none; border-radius: 6px;
        color: #4ade80; font-weight: 700; font-size: 11px; padding: 6px 20px;
    }
    QPushButton#dlgOkBtn:hover { background-color: #065f46; }
    QPushButton#dlgCancelBtn {
        background-color: #0e1a35; border: 1px solid #1f315d; border-radius: 6px;
        color: #c8d5e2; font-size: 11px; padding: 6px 20px;
    }
    QPushButton#dlgCancelBtn:hover { background-color: #152045; }
    QTabWidget::pane {
        background-color: #091023;
        border: 1px solid #1a2d57;
        border-radius: 6px;
        padding: 4px;
    }
    QTabBar::tab {
        background-color: #050b1e;
        color: #7b8fa5;
        padding: 7px 16px;
        border: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        margin-right: 2px;
    }
    QTabBar::tab:hover {
        background-color: #091023;
        color: #9bafc5;
    }
    QTabBar::tab:selected {
        background-color: #091023;
        color: #e2e8f0;
        border-bottom: 2px solid #6366f1;
    }
"""


class _AddLogPanelDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add LOG Panel")
        self.setFixedWidth(400)
        self.setStyleSheet(_DLG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("New Serial LOG")
        title.setObjectName("dlgSectionTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Panel Name"), 0, 0)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. LOG-2")
        self._title_edit.setText("Serial Log 2")
        self._title_edit.setStyleSheet("""
            QLineEdit {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 6px;
                color: #c8d5e2; font-size: 11px; padding: 6px 10px; min-height: 28px;
            }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """)
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = DarkComboBox()
        self._port_combo.setFixedHeight(28)
        self._port_combo.setEditable(True)
        try:
            ports = serial.tools.list_ports.comports()
            for p in ports:
                self._port_combo.addItem(f"{p.device} - {p.description}")
        except Exception:
            pass
        if self._port_combo.count() == 0:
            if DEBUG_MOCK:
                self._port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            else:
                self._port_combo.addItem("No serial ports found")
        grid.addWidget(self._port_combo, 1, 1)

        grid.addWidget(QLabel("Baudrate"), 2, 0)
        self._baud_combo = DarkComboBox()
        self._baud_combo.setFixedHeight(28)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "115200", "9600"]:
            self._baud_combo.addItem(br)
        self._baud_combo.setCurrentIndex(0)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = DarkComboBox()
        self._databit_combo.setFixedHeight(28)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = DarkComboBox()
        self._stopbit_combo.setFixedHeight(28)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = DarkComboBox()
        self._parity_combo.setFixedHeight(28)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow ctrl"), 6, 0)
        self._flow_combo = DarkComboBox()
        self._flow_combo.setFixedHeight(28)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)

        self._auto_connect_cb = QCheckBox("Auto connect after creation")
        self._auto_connect_cb.setChecked(True)
        root.addWidget(self._auto_connect_cb)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def get_config(self):
        port_text = self._port_combo.currentText()
        port = port_text.split()[0] if port_text and not port_text.startswith("No ") else ""
        try:
            baudrate = int(self._baud_combo.currentText().strip())
        except ValueError:
            baudrate = 115200
        return {
            "title": self._title_edit.text().strip() or "Serial Log",
            "port": port,
            "baudrate": baudrate,
            "databit": int(self._databit_combo.currentText()),
            "stopbit": self._stopbit_combo.currentText(),
            "parity": self._parity_combo.currentText(),
            "flow": self._flow_combo.currentText(),
            "auto_connect": self._auto_connect_cb.isChecked(),
        }


class _QuickCmdDialog(QDialog):

    def __init__(self, name="", cmd="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Command")
        self.setFixedWidth(360)
        self.setStyleSheet("""
            QDialog {
                background-color: #050b1e;
                color: #c8d5e2;
            }
            QLabel {
                color: #9bafc5; font-size: 11px; background: transparent;
            }
            QLabel#qcTitle {
                color: #e2e8f0; font-size: 13px; font-weight: 700; background: transparent;
            }
            QLineEdit {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 6px;
                color: #c8d5e2; font-size: 11px; padding: 6px 10px; min-height: 28px;
            }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("New Quick Command" if not name and not cmd else "Edit Quick Command")
        title.setObjectName("qcTitle")
        root.addWidget(title)

        root.addWidget(QLabel("Command name (button label, optional)"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Reset, Query Version...")
        self._name_edit.setText(name)
        root.addWidget(self._name_edit)

        root.addWidget(QLabel("Command content (data to send)"))
        self._cmd_edit = QLineEdit()
        self._cmd_edit.setPlaceholderText("e.g. AT+RST")
        self._cmd_edit.setText(cmd)
        root.addWidget(self._cmd_edit)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e1a35; border: 1px solid #1f315d; border-radius: 6px;
                color: #c8d5e2; font-size: 11px; padding: 6px 20px;
            }
            QPushButton:hover { background-color: #152045; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #064e3b; border: none; border-radius: 6px;
                color: #4ade80; font-weight: 700; font-size: 11px; padding: 6px 20px;
            }
            QPushButton:hover { background-color: #065f46; }
        """)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def get_name(self):
        return self._name_edit.text().strip()

    def get_cmd(self):
        return self._cmd_edit.text().strip()


class _SerialSettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Settings")
        self.setMinimumSize(480, 420)
        self.setStyleSheet(_DLG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_tab_serial(), "Serial")
        self._tabs.addTab(self._build_tab_rx(), "RX")
        self._tabs.addTab(self._build_tab_tx(), "TX")
        self._tabs.addTab(self._build_tab_log(), "Log")
        self._tabs.addTab(self._build_tab_display(), "Display")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    # ---- tab: Serial ----

    def _build_tab_serial(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Connection"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Port"), 0, 0)
        self.port_combo = DarkComboBox()
        self.port_combo.setFixedHeight(28)
        grid.addWidget(self.port_combo, 0, 1)

        grid.addWidget(QLabel("Baudrate"), 1, 0)
        self.baud_combo = DarkComboBox()
        self.baud_combo.setFixedHeight(28)
        self.baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "115200", "9600", "Custom"]:
            self.baud_combo.addItem(br)
        grid.addWidget(self.baud_combo, 1, 1)

        layout.addLayout(grid)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Advanced"))

        adv_grid = QGridLayout()
        adv_grid.setHorizontalSpacing(12)
        adv_grid.setVerticalSpacing(8)

        adv_grid.addWidget(QLabel("Data bits"), 0, 0)
        self.databit_combo = DarkComboBox()
        self.databit_combo.setFixedHeight(28)
        for d in ["8", "7", "6", "5"]:
            self.databit_combo.addItem(d)
        adv_grid.addWidget(self.databit_combo, 0, 1)

        adv_grid.addWidget(QLabel("Stop bits"), 0, 2)
        self.stopbit_combo = DarkComboBox()
        self.stopbit_combo.setFixedHeight(28)
        for s in ["1", "1.5", "2"]:
            self.stopbit_combo.addItem(s)
        adv_grid.addWidget(self.stopbit_combo, 0, 3)

        adv_grid.addWidget(QLabel("Parity"), 1, 0)
        self.parity_combo = DarkComboBox()
        self.parity_combo.setFixedHeight(28)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self.parity_combo.addItem(p)
        adv_grid.addWidget(self.parity_combo, 1, 1)

        adv_grid.addWidget(QLabel("Flow ctrl"), 1, 2)
        self.flow_combo = DarkComboBox()
        self.flow_combo.setFixedHeight(28)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self.flow_combo.addItem(fc)
        adv_grid.addWidget(self.flow_combo, 1, 3)

        layout.addLayout(adv_grid)
        layout.addStretch()
        return page

    # ---- tab: RX ----

    def _build_tab_rx(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Data Format"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Encoding"))
        self.rx_hex_toggle = _MiniSlideToggle("ASCII", "HEX")
        row.addWidget(self.rx_hex_toggle)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Timestamp"))

        self.show_time_cb = QCheckBox("Show timestamp (ms precision)")
        layout.addWidget(self.show_time_cb)

        self.rx_use_ntp_cb = QCheckBox("Use network time (NTP calibrated)")
        layout.addWidget(self.rx_use_ntp_cb)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Buffer"))

        buf_row = QHBoxLayout()
        buf_row.setSpacing(8)
        buf_row.addWidget(QLabel("Max lines"))
        self.rx_max_lines_spin = QSpinBox()
        self.rx_max_lines_spin.setRange(500, 100000)
        self.rx_max_lines_spin.setValue(10000)
        self.rx_max_lines_spin.setSingleStep(1000)
        self.rx_max_lines_spin.setFixedHeight(26)
        buf_row.addWidget(self.rx_max_lines_spin)
        buf_row.addStretch()
        layout.addLayout(buf_row)

        layout.addStretch()
        return page

    # ---- tab: TX ----

    def _build_tab_tx(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Data Format"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Encoding"))
        self.tx_hex_toggle = _MiniSlideToggle("ASCII", "HEX")
        row.addWidget(self.tx_hex_toggle)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Line Ending & Auto Resend"))

        ending_row = QHBoxLayout()
        ending_row.setSpacing(8)
        ending_row.addWidget(QLabel("Line ending"))
        self.ending_combo = DarkComboBox()
        self.ending_combo.setFixedHeight(28)
        for label, val in [("\\r\\n", "\r\n"), ("\\n", "\n"), ("\\r", "\r"), ("\\n\\r", "\n\r"), ("None", "")]:
            self.ending_combo.addItem(label, val)
        ending_row.addWidget(self.ending_combo)
        ending_row.addStretch()
        layout.addLayout(ending_row)

        self.auto_resend_cb = QCheckBox("Enable auto resend")
        layout.addWidget(self.auto_resend_cb)

        resend_row = QHBoxLayout()
        resend_row.setSpacing(8)
        resend_row.addWidget(QLabel("Resend interval (ms)"))
        self.resend_spin = QSpinBox()
        self.resend_spin.setRange(100, 60000)
        self.resend_spin.setValue(1000)
        self.resend_spin.setSingleStep(100)
        self.resend_spin.setFixedHeight(26)
        resend_row.addWidget(self.resend_spin)
        resend_row.addStretch()
        layout.addLayout(resend_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Other"))

        self.show_send_cb = QCheckBox("Show sent data in log")
        layout.addWidget(self.show_send_cb)

        self.line_by_line_cb = QCheckBox("Line by Line (split by \\n for multi-line send)")
        layout.addWidget(self.line_by_line_cb)

        layout.addStretch()
        return page

    # ---- tab: Log ----

    def _build_tab_log(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Log File"))

        self.log_auto_save_cb = QCheckBox("Auto save log to file")
        layout.addWidget(self.log_auto_save_cb)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        path_row.addWidget(QLabel("Save path"))
        self.log_save_path_edit = QLineEdit()
        self.log_save_path_edit.setPlaceholderText("Select log save directory...")
        self.log_save_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #050a1d; border: 1px solid #1f315d; border-radius: 4px;
                color: #c8d5e2; font-size: 11px; padding: 4px 8px; min-height: 24px;
            }
            QLineEdit:focus { border: 1px solid #6366f1; }
        """)
        path_row.addWidget(self.log_save_path_edit, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setObjectName("dlgCancelBtn")
        browse_btn.clicked.connect(self._browse_log_path)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Log Level Colors"))

        color_info = QLabel(
            "RX → Green (#4ade80)    TX → Blue (#60a5fa)\n"
            "INFO → Blue    WARN → Yellow (#facc15)    ERROR → Red (#f87171)"
        )
        color_info.setStyleSheet("color: #5f78a8; font-size: 10px; background: transparent;")
        color_info.setWordWrap(True)
        layout.addWidget(color_info)

        layout.addStretch()
        return page

    # ---- tab: Display ----

    def _build_tab_display(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Font"))

        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_row.addWidget(QLabel("Font family"))
        self.display_font_combo = DarkComboBox()
        self.display_font_combo.setFixedHeight(28)
        for f in ["Consolas", "Courier New", "Fira Code", "JetBrains Mono", "Cascadia Code", "Lucida Console"]:
            self.display_font_combo.addItem(f)
        font_row.addWidget(self.display_font_combo)
        font_row.addStretch()
        layout.addLayout(font_row)

        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        size_row.addWidget(QLabel("Font size"))
        self.display_font_size_spin = QSpinBox()
        self.display_font_size_spin.setRange(8, 24)
        self.display_font_size_spin.setValue(11)
        self.display_font_size_spin.setFixedHeight(26)
        size_row.addWidget(self.display_font_size_spin)
        size_row.addStretch()
        layout.addLayout(size_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Behavior"))

        self.display_auto_scroll_cb = QCheckBox("Enable auto-scroll by default")
        self.display_auto_scroll_cb.setChecked(True)
        layout.addWidget(self.display_auto_scroll_cb)

        self.display_word_wrap_cb = QCheckBox("Word Wrap")
        self.display_word_wrap_cb.setChecked(True)
        layout.addWidget(self.display_word_wrap_cb)

        self.display_show_line_num_cb = QCheckBox("Show line numbers")
        layout.addWidget(self.display_show_line_num_cb)

        layout.addStretch()
        return page

    # ---- helpers ----

    def _browse_log_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Log Save Directory")
        if path:
            self.log_save_path_edit.setText(path)

    @staticmethod
    def _section_title(text):
        lbl = QLabel(text)
        lbl.setObjectName("dlgSectionTitle")
        return lbl

    @staticmethod
    def _separator():
        sep = QFrame()
        sep.setObjectName("dlgSep")
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        return sep


class _SerialReadWorker(QObject):
    data_received = Signal(bytes)
    error = Signal(str)

    def __init__(self, serial_conn):
        super().__init__()
        self._serial_conn = serial_conn
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                if self._serial_conn is None or not self._serial_conn.is_open:
                    break
                if self._serial_conn.in_waiting > 0:
                    data = self._serial_conn.read(self._serial_conn.in_waiting)
                    if data:
                        self.data_received.emit(data)
                else:
                    QThread.msleep(50)
            except Exception as e:
                if self._running:
                    self.error.emit(str(e))
                break


if __name__ == "__main__":
    #python -m ui.modules.serialCom_module_frame
    import sys
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QFrame, QSizePolicy
    )

    DARK_CARD_STYLE = """
        QWidget {
            background-color: #020618;
            color: #c8d5e2;
        }
        QLabel {
            background-color: transparent;
            color: #c8d5e2;
            border: none;
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
            background-color: #050b1e;
            border: 1px solid #1a2d57;
            border-radius: 14px;
        }
        QComboBox {
            background-color: #050a1d;
            color: #c8d5e2;
            border: 1px solid #1f315d;
            border-radius: 8px;
            padding: 6px 10px;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
            background: transparent;
        }
        QComboBox QAbstractItemView {
            background-color: #050a1d;
            color: #c8d5e2;
            border: 1px solid #1f315d;
            selection-background-color: #6366f1;
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

    class _DemoSerialFullWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_FULL, prefix="FullDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Full Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            print(msg)

    class _DemoSerialSearchWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_SEARCH_SELECT, prefix="SearchDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Search & Select Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            print(msg)

    class _DemoSerialInlineWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_INLINE, prefix="InlineDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Inline Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            print(msg)

    class _DemoCompleteSerialWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_FULL, prefix="Complete")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            self.complete_serialComWidget(root)

            self._sc_on_refresh()
            self._sc_append_system("[INFO] KK Serials initialized")

        def append_log(self, msg):
            self._sc_append_system(msg)

    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    def _custom_message_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return
        print(message)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    qInstallMessageHandler(_custom_message_handler)

    w4 = _DemoCompleteSerialWidget()
    w4.setWindowTitle("Complete Serial Console")
    w4.resize(900, 600)
    w4.show()
    w4.move(50, 100)

    sys.exit(app.exec())
