#python -m ui.modules.chamber_module_frame
import os
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

import serial.tools.list_ports
from PySide6.QtCore import QObject, QThread, QTimer, QRectF, Signal
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy

from debug_config import DEBUG_MOCK
from log_config import get_logger
from ui.resource_path import get_resource_base
from ui.widgets.dark_combobox import DarkComboBox

logger = get_logger(__name__)


CHAMBER_TYPES = {
    "vt6002": {
        "label": "VT6002",
        "display_name": "VT6002 Chamber",
        "connection_kind": "serial_modbus",
        "baudrate": 9600,
    },
    "mt3065": {
        "label": "MT3065",
        "display_name": "MT3065 Chamber",
        "connection_kind": "serial_ascii",
        "baudrate": 19200,
    },
}

_SVG_COMMON_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Common"
)
_SEARCH_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "unlink.svg")

_CHAMBER_BTN_HEIGHT = 24
_CHAMBER_BTN_ICON_SIZE = 14
_CHAMBER_BTN_RADIUS = 6


def chamber_display_name(chamber_type: str) -> str:
    meta = CHAMBER_TYPES.get(str(chamber_type).strip().lower(), {})
    return meta.get("display_name") or meta.get("label") or str(chamber_type)


def chamber_type_label(chamber_type: str) -> str:
    meta = CHAMBER_TYPES.get(str(chamber_type).strip().lower(), {})
    return meta.get("label") or str(chamber_type).upper()


def chamber_baudrate(chamber_type: str) -> int:
    meta = CHAMBER_TYPES.get(str(chamber_type).strip().lower(), {})
    return int(meta.get("baudrate", 9600))


def chamber_connection_kind(chamber_type: str) -> str:
    meta = CHAMBER_TYPES.get(str(chamber_type).strip().lower(), {})
    return meta.get("connection_kind", "serial")


def _search_style(h=_CHAMBER_BTN_HEIGHT, r=_CHAMBER_BTN_RADIUS):
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


def _connect_style(h=_CHAMBER_BTN_HEIGHT, r=_CHAMBER_BTN_RADIUS):
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


def _disconnect_style(h=_CHAMBER_BTN_HEIGHT, r=_CHAMBER_BTN_RADIUS):
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


class _ChamberSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=_CHAMBER_BTN_ICON_SIZE,
                 btn_height=_CHAMBER_BTN_HEIGHT, btn_radius=_CHAMBER_BTN_RADIUS):
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
        self.setStyleSheet(_search_style(h=btn_height, r=btn_radius))

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


def _update_chamber_btn_state(btn, connected,
                              h=_CHAMBER_BTN_HEIGHT, r=_CHAMBER_BTN_RADIUS,
                              icon_size=_CHAMBER_BTN_ICON_SIZE):
    from PySide6.QtCore import QSize as _QSize
    if connected:
        btn.setText("Disconnect")
        btn.setStyleSheet(_disconnect_style(h=h, r=r))
        if os.path.isfile(_UNLINK_ICON_PATH):
            btn.setIcon(QIcon(_UNLINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
    else:
        btn.setText("Connect")
        btn.setStyleSheet(_connect_style(h=h, r=r))
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


class ChamberConnectionMixin:
    chamber_connection_changed = Signal(bool)

    def init_chamber_connection(self, chamber_ui=None, instrument_manager=None, default_chamber_type="vt6002"):
        self._chamber_ui = chamber_ui
        self._chamber_instrument_manager = instrument_manager
        self.current_chamber_type = default_chamber_type
        self.current_chamber_session_id = None
        self.chamber = None
        self.is_chamber_connected = False
        self._chamber_syncing = False
        self._chamber_search_thread = None
        self._chamber_search_worker = None

        if self._chamber_ui is not None and hasattr(self._chamber_ui, "connection_changed"):
            self._chamber_ui.connection_changed.connect(self._on_chamber_external_changed)

        if self._chamber_instrument_manager is not None:
            self._chamber_instrument_manager.session_connected.connect(
                self._on_chamber_manager_connected
            )
            self._chamber_instrument_manager.session_disconnected.connect(
                self._on_chamber_manager_disconnected
            )
            self._chamber_instrument_manager.connection_failed.connect(
                self._on_chamber_manager_connection_failed
            )

    def build_chamber_connection_widgets(self, layout):
        self.chamber_status_label = QLabel("● Not Connected")
        self.chamber_status_label.setObjectName("statusErr")
        layout.addWidget(self.chamber_status_label)

        self.chamber_type_combo = DarkComboBox()
        for chamber_type, meta in CHAMBER_TYPES.items():
            self.chamber_type_combo.addItem(meta["label"], chamber_type)
        idx = self.chamber_type_combo.findData(self.current_chamber_type)
        if idx >= 0:
            self.chamber_type_combo.setCurrentIndex(idx)
        self.chamber_type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.chamber_type_combo)

        self.chamber_port_combo = DarkComboBox()
        self.chamber_port_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.chamber_port_combo.setMinimumContentsLength(10)
        self.chamber_port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.chamber_port_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 2, 0, 0)

        self.chamber_search_btn = _ChamberSearchButton()
        self.chamber_connect_btn = QPushButton()
        _update_chamber_btn_state(self.chamber_connect_btn, connected=False)

        btn_row.addWidget(self.chamber_search_btn)
        btn_row.addWidget(self.chamber_connect_btn)
        layout.addLayout(btn_row)

    def bind_chamber_signals(self):
        self.chamber_type_combo.currentIndexChanged.connect(self._on_chamber_type_changed)
        self.chamber_search_btn.clicked.connect(self._on_chamber_search)
        self.chamber_connect_btn.clicked.connect(self._on_chamber_toggle)

    def _selected_chamber_type(self):
        if hasattr(self, "chamber_type_combo"):
            data = self.chamber_type_combo.currentData()
            if data:
                return str(data)
        return self.current_chamber_type or "vt6002"

    def _selected_chamber_label(self):
        return chamber_type_label(self._selected_chamber_type())

    def _on_chamber_type_changed(self):
        self.current_chamber_type = self._selected_chamber_type()
        if hasattr(self, "chamber_port_combo") and not self.is_chamber_connected:
            self.chamber_port_combo.clear()

    def _on_chamber_external_changed(self):
        if self._chamber_syncing or self._chamber_ui is None:
            return
        chamber = getattr(self._chamber_ui, "chamber", None)
        if chamber is not None and self._is_chamber_open(chamber):
            self.chamber = chamber
            self.is_chamber_connected = True
            self.current_chamber_type = getattr(self._chamber_ui, "current_chamber_type", self.current_chamber_type)
            self.current_chamber_session_id = getattr(self._chamber_ui, "current_chamber_session_id", None)
            port = getattr(self._chamber_ui, "current_port", "Unknown")
            self._update_chamber_connection_ui(True, port)
            if hasattr(self, "append_log"):
                self.append_log(f"[Chamber] Synced {self._selected_chamber_label()}: {port}")
            return
        self.chamber = None
        self.is_chamber_connected = False
        self.current_chamber_session_id = None
        self._update_chamber_connection_ui(False, "Not Connected")
        if hasattr(self, "append_log"):
            self.append_log("[Chamber] Disconnected (synced).")

    def _is_chamber_session(self, session_id: str) -> bool:
        mgr = self._chamber_instrument_manager
        if not mgr:
            return False
        session = mgr.get_session(session_id)
        return bool(session and session.role == "chamber")

    def _on_chamber_manager_connected(self, session_id: str):
        if not self._is_chamber_session(session_id):
            return
        mgr = self._chamber_instrument_manager
        session = mgr.get_session(session_id)
        if session and session.connected:
            self.chamber = session.instance
            self.is_chamber_connected = True
            self.current_chamber_type = session.instrument_type
            self.current_chamber_session_id = session_id
            if hasattr(self, "chamber_type_combo"):
                idx = self.chamber_type_combo.findData(session.instrument_type)
                if idx >= 0:
                    self.chamber_type_combo.setCurrentIndex(idx)
            self._update_chamber_connection_ui(True, session.resource)
            if hasattr(self, "append_log"):
                self.append_log(
                    f"[Chamber] Connected via manager: {chamber_type_label(session.instrument_type)} {session.resource}"
                )
            self.chamber_connection_changed.emit(True)

    def _on_chamber_manager_disconnected(self, session_id: str):
        if session_id != self.current_chamber_session_id and not self._is_chamber_session(session_id):
            return
        self.chamber = None
        self.is_chamber_connected = False
        self.current_chamber_session_id = None
        self._update_chamber_connection_ui(False, "Not Connected")
        if hasattr(self, "append_log"):
            self.append_log("[Chamber] Disconnected via manager.")
        self.chamber_connection_changed.emit(False)

    def _on_chamber_manager_connection_failed(self, session_id: str, error: str):
        if session_id != self.current_chamber_session_id and not session_id.endswith(":chamber"):
            return
        if hasattr(self, "append_log"):
            self.append_log(f"[Chamber] Connection failed: {error}")
        self._update_chamber_connection_ui(False, "Error")
        self.chamber_connection_changed.emit(False)

    def _on_chamber_search(self):
        chamber_type = self._selected_chamber_type()
        if DEBUG_MOCK:
            self.chamber_port_combo.clear()
            self.chamber_port_combo.addItem(f"[MOCK] {chamber_type_label(chamber_type)} Chamber")
            return

        if self._chamber_search_thread is not None and self._chamber_search_thread.isRunning():
            return

        self.chamber_search_btn.setEnabled(False)
        self.chamber_connect_btn.setEnabled(False)
        self.chamber_search_btn.start_spinning()

        worker = _SearchSerialWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_chamber_search_done)
        worker.error.connect(self._on_chamber_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_chamber_thread_cleanup)

        self._chamber_search_thread = thread
        self._chamber_search_worker = worker
        thread.start()

    def _on_chamber_thread_cleanup(self):
        self._chamber_search_thread = None
        self._chamber_search_worker = None

    def _on_chamber_search_done(self, ports):
        self.chamber_search_btn.stop_spinning()
        self.chamber_port_combo.clear()
        if ports:
            for port in ports:
                self.chamber_port_combo.addItem(port)
            self.chamber_connect_btn.setEnabled(True)
        else:
            self.chamber_port_combo.addItem("No serial ports found")
            self.chamber_connect_btn.setEnabled(False)
        self.chamber_search_btn.setEnabled(True)

    def _on_chamber_search_error(self, err):
        self.chamber_search_btn.stop_spinning()
        if hasattr(self, "append_log"):
            self.append_log(f"[Chamber] Search error: {err}")
        self.chamber_search_btn.setEnabled(True)
        self.chamber_connect_btn.setEnabled(False)

    def _on_chamber_toggle(self):
        if self.is_chamber_connected:
            self._on_chamber_disconnect()
        else:
            self._on_chamber_connect()

    def _on_chamber_connect(self):
        self.chamber_connect_btn.setEnabled(False)
        chamber_type = self._selected_chamber_type()
        port_str = self.chamber_port_combo.currentText().strip()
        if not port_str or port_str in ("No serial ports found", "Scan Failed"):
            self._update_chamber_connection_ui(False, "No serial port selected")
            return

        if DEBUG_MOCK:
            port = f"MOCK::{chamber_type_label(chamber_type)}"
        else:
            port = port_str.split()[0]

        if self._chamber_instrument_manager:
            from core.instruments import InstrumentSpec
            spec = InstrumentSpec(
                instrument_type=chamber_type,
                role="chamber",
                connection_kind=chamber_connection_kind(chamber_type),
                slot="default",
                resource=port,
            )
            self.current_chamber_session_id = self._chamber_instrument_manager.connect_async(spec)
            return

        try:
            from instruments.factory import create_chamber
            chamber = create_chamber(
                chamber_type=chamber_type,
                port=port,
                baudrate=chamber_baudrate(chamber_type),
            )
        except Exception as e:
            logger.error("Chamber connection failed: %s", e, exc_info=True)
            if hasattr(self, "append_log"):
                self.append_log(f"[Chamber] Connection failed: {e}")
            self._update_chamber_connection_ui(False, "Error")
            return

        self.chamber = chamber
        self.is_chamber_connected = True
        self.current_chamber_type = chamber_type
        self.current_chamber_session_id = None
        self._update_chamber_connection_ui(True, port)
        if hasattr(self, "append_log"):
            self.append_log(f"[Chamber] Connected: {chamber_type_label(chamber_type)} {port}")

        if self._chamber_ui is not None:
            self._sync_connected_to_chamber_ui(chamber, chamber_type, port)

        self.chamber_connection_changed.emit(True)

    def _sync_connected_to_chamber_ui(self, chamber, chamber_type, port):
        self._chamber_syncing = True
        self._chamber_ui.chamber = chamber
        self._chamber_ui.current_chamber_type = chamber_type
        self._chamber_ui.current_port = port
        self._chamber_ui.current_chamber_session_id = self.current_chamber_session_id
        self._chamber_ui._set_connection_ui(True)
        self._chamber_ui._set_controls_enabled(True)
        self._chamber_ui.connection_changed.emit()
        self._chamber_syncing = False

    def _on_chamber_disconnect(self):
        self.chamber_connect_btn.setEnabled(False)
        if self._chamber_instrument_manager and self.current_chamber_session_id:
            self._chamber_instrument_manager.disconnect_async(self.current_chamber_session_id)
            return

        try:
            if self.chamber is not None:
                self.chamber.close()
        except Exception as e:
            logger.warning("Chamber close error: %s", e, exc_info=True)
            if hasattr(self, "append_log"):
                self.append_log(f"[Chamber] Close error: {e}")

        self.chamber = None
        self.is_chamber_connected = False
        self.current_chamber_session_id = None
        self._update_chamber_connection_ui(False, "Disconnected")
        if hasattr(self, "append_log"):
            self.append_log("[Chamber] Disconnected.")

        if self._chamber_ui is not None:
            self._chamber_syncing = True
            self._chamber_ui.chamber = None
            self._chamber_ui.current_port = None
            self._chamber_ui.current_chamber_session_id = None
            self._chamber_ui.is_chamber_on = False
            self._chamber_ui._set_connection_ui(False)
            self._chamber_ui._set_controls_enabled(False)
            self._chamber_ui._set_power_ui(False)
            self._chamber_ui.connection_changed.emit()
            self._chamber_syncing = False

        self.chamber_connection_changed.emit(False)

    def _is_chamber_open(self, chamber):
        if hasattr(chamber, "is_connected"):
            try:
                return bool(chamber.is_connected())
            except Exception:
                logger.debug("Chamber is_connected failed", exc_info=True)
        return bool(hasattr(chamber, "ser") and chamber.ser is not None and chamber.ser.is_open)

    def _update_chamber_connection_ui(self, connected, status_text):
        if connected:
            self.chamber_status_label.setText(f"● Connected to: {status_text}")
            self.chamber_status_label.setObjectName("statusOk")
        else:
            self.chamber_status_label.setText(f"● {status_text}")
            self.chamber_status_label.setObjectName("statusErr")
        self.chamber_status_label.style().unpolish(self.chamber_status_label)
        self.chamber_status_label.style().polish(self.chamber_status_label)
        self.chamber_status_label.update()
        _update_chamber_btn_state(self.chamber_connect_btn, connected)
        self.chamber_connect_btn.setEnabled(True)
        self.chamber_search_btn.setEnabled(not connected)
        self.chamber_port_combo.setEnabled(not connected)
        self.chamber_type_combo.setEnabled(not connected)

    def get_chamber_instance(self):
        return self.chamber

    def is_chamber_connected_status(self):
        return self.is_chamber_connected


if __name__ == "__main__":
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget

    class _DemoChamberWidget(ChamberConnectionMixin, QWidget):
        chamber_connection_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_chamber_connection()
            self.setStyleSheet("""
                QWidget { background-color: #020817; color: #dbe7ff; }
                QLabel { background-color: transparent; color: #dbe7ff; border: none; }
                QLabel#statusOk { color: #15d1a3; font-weight: 600; }
                QLabel#statusErr { color: #ff5e7a; font-weight: 600; }
                QFrame#cardFrame { background-color: #071127; border: 1px solid #1a2b52; border-radius: 12px; }
            """)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)
            card = QFrame()
            card.setObjectName("cardFrame")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 12)
            card_layout.setSpacing(8)
            card_layout.addWidget(QLabel("Chamber Connection"))
            self.build_chamber_connection_widgets(card_layout)
            root.addWidget(card)
            root.addStretch()
            self.bind_chamber_signals()

        def append_log(self, msg):
            logger.info(msg)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = _DemoChamberWidget()
    w.setWindowTitle("Chamber Module Frame Demo")
    w.setFixedWidth(340)
    w.show()
    w.move(100, 200)
    sys.exit(app.exec())
