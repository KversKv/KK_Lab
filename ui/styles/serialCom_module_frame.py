import os
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal, QThread, QObject, QTimer, QRectF
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtSvg import QSvgRenderer

from ui.widgets.dark_combobox import DarkComboBox
from debug_config import DEBUG_MOCK


_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "icons"
)
_SEARCH_ICON_PATH = os.path.join(_ICONS_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_ICONS_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_ICONS_DIR, "unlink.svg")

_SERIAL_BTN_HEIGHT = 24
_SERIAL_BTN_ICON_SIZE = 14
_SERIAL_BTN_RADIUS = 6


def _serial_search_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #13254b;
            border: 1px solid #22376A;
            border-radius: {r}px;
            color: #dce7ff;
            font-weight: 600;
            min-height: {h}px;
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


def _serial_connect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #053b38;
            border: 1px solid #08c9a5;
            border-radius: {r}px;
            color: #10e7bc;
            font-weight: 700;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            background-color: #064744;
            border: 1px solid #19f0c5;
            color: #43f3d0;
        }}
        QPushButton:pressed {{
            background-color: #042f2d;
        }}
        QPushButton:disabled {{
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }}
    """


def _serial_disconnect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #3a0828;
            border: 1px solid #d61b67;
            border-radius: {r}px;
            color: #ffb7d3;
            font-weight: 700;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            background-color: #4a0b31;
            border: 1px solid #f0287b;
            color: #ffd0e2;
        }}
        QPushButton:pressed {{
            background-color: #330722;
        }}
        QPushButton:disabled {{
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }}
    """


class _SerialSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=_SERIAL_BTN_ICON_SIZE,
                 btn_height=_SERIAL_BTN_HEIGHT, btn_radius=_SERIAL_BTN_RADIUS):
        super().__init__(parent)
        self._icon_size = icon_size
        self._angle = 0.0
        self._spinning = False
        self._svg_renderer = None

        if os.path.isfile(_SEARCH_ICON_PATH):
            self._svg_renderer = QSvgRenderer(_SEARCH_ICON_PATH)

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
        if not self._svg_renderer:
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
        painter.translate(-s / 2.0, -s / 2.0)

        self._svg_renderer.render(painter, QRectF(0, 0, s, s))
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

        self.serial_status_label = QLabel("● Not Connected")
        self.serial_status_label.setObjectName("statusErr")
        layout.addWidget(self.serial_status_label)

        self.serial_combo = DarkComboBox()
        self.serial_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.serial_combo.setMinimumContentsLength(10)
        self.serial_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        layout.addWidget(self.serial_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

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
