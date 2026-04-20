#python -m ui.modules.chamber_module_frame
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
from instruments.mock.mock_instruments import MockVT6002


_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "icons"
)
_SEARCH_ICON_PATH = os.path.join(_ICONS_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_ICONS_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_ICONS_DIR, "unlink.svg")

_VT6002_BTN_HEIGHT = 24
_VT6002_BTN_ICON_SIZE = 14
_VT6002_BTN_RADIUS = 6


def _vt6002_search_style(h=_VT6002_BTN_HEIGHT, r=_VT6002_BTN_RADIUS):
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


def _vt6002_connect_style(h=_VT6002_BTN_HEIGHT, r=_VT6002_BTN_RADIUS):
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


def _vt6002_disconnect_style(h=_VT6002_BTN_HEIGHT, r=_VT6002_BTN_RADIUS):
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


class _VT6002SearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=_VT6002_BTN_ICON_SIZE,
                 btn_height=_VT6002_BTN_HEIGHT, btn_radius=_VT6002_BTN_RADIUS):
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
        self.setStyleSheet(_vt6002_search_style(h=btn_height, r=btn_radius))

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


def _update_vt6002_btn_state(btn, connected,
                             h=_VT6002_BTN_HEIGHT, r=_VT6002_BTN_RADIUS,
                             icon_size=_VT6002_BTN_ICON_SIZE):
    from PySide6.QtCore import QSize as _QSize
    if connected:
        btn.setText("Disconnect")
        btn.setStyleSheet(_vt6002_disconnect_style(h=h, r=r))
        if os.path.isfile(_UNLINK_ICON_PATH):
            btn.setIcon(QIcon(_UNLINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
    else:
        btn.setText("Connect")
        btn.setStyleSheet(_vt6002_connect_style(h=h, r=r))
        if os.path.isfile(_LINK_ICON_PATH):
            btn.setIcon(QIcon(_LINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
        else:
            btn.setIcon(QIcon())


class _SearchSerialWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            ports = serial.tools.list_ports.comports()
            result = [f"{p.device} - {p.description}" for p in ports]
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class VT6002ConnectionMixin:
    vt6002_connection_changed = Signal(bool)

    def init_vt6002_connection(self, vt6002_chamber_ui=None):
        self._vt6002_chamber_ui = vt6002_chamber_ui
        self.vt6002 = None
        self.is_vt6002_connected = False
        self._vt6002_syncing = False
        self._vt6002_search_thread = None
        self._vt6002_search_worker = None

        if self._vt6002_chamber_ui is not None and hasattr(self._vt6002_chamber_ui, 'connection_changed'):
            self._vt6002_chamber_ui.connection_changed.connect(self._on_vt6002_external_changed)

    def build_vt6002_connection_widgets(self, layout):
        self.vt6002_status_label = QLabel("● Not Connected")
        self.vt6002_status_label.setObjectName("statusErr")
        layout.addWidget(self.vt6002_status_label)

        self.vt6002_combo = DarkComboBox()
        self.vt6002_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.vt6002_combo.setMinimumContentsLength(10)
        self.vt6002_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.vt6002_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 2, 0, 0)

        self.vt6002_search_btn = _VT6002SearchButton()

        self.vt6002_connect_btn = QPushButton()
        _update_vt6002_btn_state(self.vt6002_connect_btn, connected=False)

        btn_row.addWidget(self.vt6002_search_btn)
        btn_row.addWidget(self.vt6002_connect_btn)
        layout.addLayout(btn_row)

    def bind_vt6002_signals(self):
        self.vt6002_search_btn.clicked.connect(self._on_vt6002_search)
        self.vt6002_connect_btn.clicked.connect(self._on_vt6002_toggle)

    def _on_vt6002_external_changed(self):
        if self._vt6002_syncing:
            return
        if self._vt6002_chamber_ui is None:
            return
        vt = self._vt6002_chamber_ui.vt6002
        if vt is not None:
            is_open = isinstance(vt, MockVT6002) or (hasattr(vt, 'ser') and vt.ser.is_open)
            if is_open:
                self.vt6002 = vt
                self.is_vt6002_connected = True
                port = getattr(self._vt6002_chamber_ui, 'current_port', 'Unknown')
                self._update_vt6002_connection_ui(True, port)
                if hasattr(self, 'append_log'):
                    self.append_log(f"[VT6002] Synced: {port}")
                return
        self.vt6002 = None
        self.is_vt6002_connected = False
        self._update_vt6002_connection_ui(False, "Not Connected")
        if hasattr(self, 'append_log'):
            self.append_log("[VT6002] Disconnected (synced).")

    def _on_vt6002_search(self):
        if DEBUG_MOCK:
            self.vt6002_combo.clear()
            self.vt6002_combo.addItem("[MOCK] COM3 - VT6002 Chamber")
            return

        if self._vt6002_search_thread is not None and self._vt6002_search_thread.isRunning():
            return

        self.vt6002_search_btn.setEnabled(False)
        self.vt6002_connect_btn.setEnabled(False)

        worker = _SearchSerialWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_vt6002_search_done)
        worker.error.connect(self._on_vt6002_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_vt6002_thread_cleanup())

        self._vt6002_search_thread = thread
        self._vt6002_search_worker = worker
        thread.start()

    def _on_vt6002_thread_cleanup(self):
        self._vt6002_search_thread = None
        self._vt6002_search_worker = None

    def _on_vt6002_search_done(self, ports):
        self.vt6002_combo.clear()
        if ports:
            for port in ports:
                self.vt6002_combo.addItem(port)
            self.vt6002_connect_btn.setEnabled(True)
        else:
            self.vt6002_combo.addItem("No serial ports found")
            self.vt6002_connect_btn.setEnabled(False)
        self.vt6002_search_btn.setEnabled(True)

    def _on_vt6002_search_error(self, err):
        if hasattr(self, 'append_log'):
            self.append_log(f"[VT6002] Search error: {err}")
        self.vt6002_search_btn.setEnabled(True)
        self.vt6002_connect_btn.setEnabled(False)

    def _on_vt6002_toggle(self):
        if self.is_vt6002_connected:
            self._on_vt6002_disconnect()
        else:
            self._on_vt6002_connect()

    def _on_vt6002_connect(self):
        self.vt6002_connect_btn.setEnabled(False)
        if DEBUG_MOCK:
            vt = MockVT6002()
            port = "MOCK"
        else:
            try:
                from instruments.chambers.vt6002_chamber import VT6002
                port_str = self.vt6002_combo.currentText()
                port = port_str.split()[0]
                vt = VT6002(port)
            except Exception as e:
                if hasattr(self, 'append_log'):
                    self.append_log(f"[VT6002] Connection failed: {e}")
                self._update_vt6002_connection_ui(False, "Error")
                return

        self.vt6002 = vt
        self.is_vt6002_connected = True
        self._update_vt6002_connection_ui(True, port)
        if hasattr(self, 'append_log'):
            self.append_log(f"[VT6002] Connected: {port}")

        if self._vt6002_chamber_ui is not None:
            self._vt6002_syncing = True
            self._vt6002_chamber_ui.vt6002 = vt
            self._vt6002_chamber_ui.current_port = port
            self._vt6002_chamber_ui._set_connection_ui(True)
            self._vt6002_chamber_ui._set_controls_enabled(True)
            self._vt6002_chamber_ui.connection_changed.emit()
            self._vt6002_syncing = False

        self.vt6002_connection_changed.emit(True)

    def _on_vt6002_disconnect(self):
        self.vt6002_connect_btn.setEnabled(False)
        try:
            if self.vt6002 is not None:
                self.vt6002.close()
        except Exception as e:
            if hasattr(self, 'append_log'):
                self.append_log(f"[VT6002] Close error: {e}")

        self.vt6002 = None
        self.is_vt6002_connected = False
        self._update_vt6002_connection_ui(False, "Disconnected")
        if hasattr(self, 'append_log'):
            self.append_log("[VT6002] Disconnected.")

        if self._vt6002_chamber_ui is not None:
            self._vt6002_syncing = True
            self._vt6002_chamber_ui.vt6002 = None
            self._vt6002_chamber_ui.current_port = None
            self._vt6002_chamber_ui.is_chamber_on = False
            self._vt6002_chamber_ui._set_connection_ui(False)
            self._vt6002_chamber_ui._set_controls_enabled(False)
            self._vt6002_chamber_ui._set_power_ui(False)
            self._vt6002_chamber_ui.connection_changed.emit()
            self._vt6002_syncing = False

        self.vt6002_connection_changed.emit(False)

    def _update_vt6002_connection_ui(self, connected, status_text):
        if connected:
            self.vt6002_status_label.setText(f"● Connected to: {status_text}")
            self.vt6002_status_label.setObjectName("statusOk")
        else:
            self.vt6002_status_label.setText(f"● {status_text}")
            self.vt6002_status_label.setObjectName("statusErr")
        self.vt6002_status_label.style().unpolish(self.vt6002_status_label)
        self.vt6002_status_label.style().polish(self.vt6002_status_label)
        self.vt6002_status_label.update()
        _update_vt6002_btn_state(self.vt6002_connect_btn, connected)
        self.vt6002_search_btn.setEnabled(not connected)
        self.vt6002_combo.setEnabled(not connected)

    def get_vt6002_instance(self):
        return self.vt6002

    def is_vt6002_connected_status(self):
        return self.is_vt6002_connected


if __name__ == "__main__":
    #python -m ui.modules.chamber_module_frame
    import sys
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QFrame, QSizePolicy
    )

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
            border-radius: 14px;
        }
        QComboBox {
            background-color: #0a1733;
            color: #eaf2ff;
            border: 1px solid #27406f;
            border-radius: 8px;
            padding: 6px 10px;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
            background: transparent;
        }
        QComboBox QAbstractItemView {
            background-color: #0a1733;
            color: #eaf2ff;
            border: 1px solid #27406f;
            selection-background-color: #334a7d;
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

    class _DemoVT6002Widget(VT6002ConnectionMixin, QWidget):
        vt6002_connection_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_vt6002_connection()
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("VT6002 Chamber Connection")
            self.build_vt6002_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_vt6002_signals()

        def append_log(self, msg):
            print(msg)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = _DemoVT6002Widget()
    w.setWindowTitle("VT6002 Chamber Module Frame Demo")
    w.setFixedWidth(320)
    w.show()
    w.move(100, 200)

    sys.exit(app.exec())
