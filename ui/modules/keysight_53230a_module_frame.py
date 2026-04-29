#python -m ui.modules.keysight_53230a_module_frame
import os
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from ui.resource_path import get_resource_base
import pyvisa
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal, QThread, QObject, QTimer, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtSvg import QSvgRenderer

from ui.widgets.dark_combobox import DarkComboBox
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockKeysight53230A


_SVG_COMMON_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Common"
)
_SEARCH_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "unlink.svg")

_CNT_BTN_HEIGHT = 24
_CNT_BTN_ICON_SIZE = 14
_CNT_BTN_RADIUS = 6


def _cnt_search_style(h=_CNT_BTN_HEIGHT, r=_CNT_BTN_RADIUS):
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


def _cnt_connect_style(h=_CNT_BTN_HEIGHT, r=_CNT_BTN_RADIUS):
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


def _cnt_disconnect_style(h=_CNT_BTN_HEIGHT, r=_CNT_BTN_RADIUS):
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


class _CounterSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=_CNT_BTN_ICON_SIZE,
                 btn_height=_CNT_BTN_HEIGHT, btn_radius=_CNT_BTN_RADIUS):
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
        self.setStyleSheet(_cnt_search_style(h=btn_height, r=btn_radius))

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


def _update_cnt_btn_state(btn, connected,
                          h=_CNT_BTN_HEIGHT, r=_CNT_BTN_RADIUS,
                          icon_size=_CNT_BTN_ICON_SIZE):
    from PySide6.QtCore import QSize as _QSize
    if connected:
        btn.setText("Disconnect")
        btn.setStyleSheet(_cnt_disconnect_style(h=h, r=r))
        if os.path.isfile(_UNLINK_ICON_PATH):
            btn.setIcon(QIcon(_UNLINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
    else:
        btn.setText("Connect")
        btn.setStyleSheet(_cnt_connect_style(h=h, r=r))
        if os.path.isfile(_LINK_ICON_PATH):
            btn.setIcon(QIcon(_LINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
        else:
            btn.setIcon(QIcon())


class _SearchCounterWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        rm = None
        try:
            rm = pyvisa.ResourceManager()
            all_resources = list(rm.list_resources()) or []
            counter_devices = []
            for dev in all_resources:
                instr = None
                try:
                    instr = rm.open_resource(dev, timeout=2000)
                    idn = instr.query('*IDN?').strip()
                    idn_up = idn.upper()
                    if ("53230" in idn_up) or ("53220" in idn_up) or \
                       ("COUNTER" in idn_up) or ("FREQUENCY" in idn_up):
                        counter_devices.append(dev)
                except Exception:
                    pass
                finally:
                    if instr is not None:
                        try:
                            instr.close()
                        except Exception:
                            pass
            self.finished.emit(counter_devices)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit([])
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass


class _CounterInstrumentWorker(QObject):
    finished = Signal(dict)

    def __init__(self, task, kwargs=None):
        super().__init__()
        self._task = task
        self._kwargs = kwargs or {}

    def run(self):
        try:
            result = self._task(**self._kwargs)
            self.finished.emit(result if isinstance(result, dict) else {})
        except Exception as e:
            self.finished.emit({"error": str(e)})


SUPPORTED_COUNTER_MODELS = ("53230A",)
DEFAULT_COUNTER_TYPE = "53230A"


def _match_counter_type_from_idn(idn: str) -> str:
    if not idn:
        return DEFAULT_COUNTER_TYPE
    idn_up = idn.upper()
    for model in SUPPORTED_COUNTER_MODELS:
        if model.upper() in idn_up:
            return model
    return DEFAULT_COUNTER_TYPE


class Keysight53230AConnectionMixin:
    counter_connection_changed = Signal(bool)

    def init_counter_connection(self, counter_top=None):
        self._counter_top = counter_top
        self._counter_rm = None
        self.Counter_ins = None
        self.counter_connected = False
        self.counter_resource = None
        self._current_counter_type = DEFAULT_COUNTER_TYPE
        self._counter_search_thread = None
        self._counter_search_worker = None
        self._counter_instr_thread = None
        self._counter_instr_worker = None

        if self._counter_top is not None and hasattr(self._counter_top, 'connection_changed'):
            self._counter_top.connection_changed.connect(self._on_counter_top_changed)

    def build_counter_connection_widgets(self, layout, title_row=None):
        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        if title_row is not None:
            title_row.addWidget(self.system_status_label)
        else:
            layout.addWidget(self.system_status_label)

        self.counter_resource_combo = DarkComboBox()
        self.counter_resource_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.counter_resource_combo.setMinimumContentsLength(10)
        self.counter_resource_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.counter_resource_combo.setEditable(True)
        self.counter_resource_combo.addItem("USB0::0x0957::0x1907::MY62340214::INSTR")
        self.counter_resource_combo.lineEdit().setCursorPosition(0)
        self.counter_resource_combo.currentIndexChanged.connect(
            lambda: QTimer.singleShot(0, lambda: self.counter_resource_combo.lineEdit().setCursorPosition(0))
        )
        layout.addWidget(self.counter_resource_combo)

        counter_row = QHBoxLayout()
        counter_row.setSpacing(6)
        counter_row.setContentsMargins(0, 2, 0, 0)

        self.counter_search_btn = _CounterSearchButton()

        self.counter_connect_btn = QPushButton()
        _update_cnt_btn_state(self.counter_connect_btn, connected=False)

        counter_row.addWidget(self.counter_search_btn)
        counter_row.addWidget(self.counter_connect_btn)
        layout.addLayout(counter_row)

    def set_system_status(self, status, is_error=False):
        if not hasattr(self, 'system_status_label') or self.system_status_label is None:
            return
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif any(kw in status for kw in ["Running", "Searching", "Connecting", "Disconnecting"]):
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def bind_counter_signals(self):
        self.counter_search_btn.clicked.connect(self._on_counter_search)
        self.counter_connect_btn.clicked.connect(self._on_connect_or_disconnect_counter)

    def sync_counter_from_top(self):
        if not self._counter_top:
            return
        if self._counter_top.is_connected and getattr(self._counter_top, 'counter', None):
            self.Counter_ins = self._counter_top.counter
            self.counter_resource = self._counter_top.visa_resource
            self.counter_connected = True
            _update_cnt_btn_state(self.counter_connect_btn, True)
            self.counter_search_btn.setEnabled(False)
            counter_type = getattr(self._counter_top, 'counter_type', DEFAULT_COUNTER_TYPE) or DEFAULT_COUNTER_TYPE
            self._current_counter_type = counter_type
            if self._counter_top.visa_resource:
                self.counter_resource_combo.clear()
                self.counter_resource_combo.addItem(self._counter_top.visa_resource)
            self.set_system_status("● Connected")
        elif not self.counter_connected:
            _update_cnt_btn_state(self.counter_connect_btn, False)

    def _on_counter_top_changed(self):
        if self._counter_top is None:
            return
        if hasattr(self, 'is_test_running') and self.is_test_running:
            return
        if self._counter_top.is_connected and getattr(self._counter_top, 'counter', None):
            if self.Counter_ins is self._counter_top.counter and self.counter_connected:
                return
            self.Counter_ins = self._counter_top.counter
            self.counter_resource = self._counter_top.visa_resource
            self.counter_connected = True
            _update_cnt_btn_state(self.counter_connect_btn, True)
            self.counter_search_btn.setEnabled(False)
            counter_type = getattr(self._counter_top, 'counter_type', DEFAULT_COUNTER_TYPE) or DEFAULT_COUNTER_TYPE
            self._current_counter_type = counter_type
            if self._counter_top.visa_resource:
                self.counter_resource_combo.clear()
                self.counter_resource_combo.addItem(self._counter_top.visa_resource)
            self.set_system_status("● Connected")
            if hasattr(self, 'append_log'):
                self.append_log(f"[SYSTEM] {counter_type} synced from external connection.")
        else:
            if not self.counter_connected:
                return
            self.Counter_ins = None
            self.counter_resource = None
            self.counter_connected = False
            _update_cnt_btn_state(self.counter_connect_btn, False)
            self.counter_search_btn.setEnabled(True)
            self.set_system_status("● Ready")
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] Frequency counter disconnected externally.")

    def _on_counter_search(self):
        if self._counter_top and self._counter_top.is_connected:
            return
        if hasattr(self, 'set_page_status'):
            self.set_page_status("Searching counter resources...")
        self.set_system_status("● Searching")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Scanning for frequency counter resources (LAN & USB)...")
        self.counter_search_btn.setEnabled(False)

        if self._counter_search_thread is not None and self._counter_search_thread.isRunning():
            return

        worker = _SearchCounterWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_counter_search_finished)
        worker.error.connect(lambda e: (
            hasattr(self, 'append_log') and self.append_log(f"[WARN] Counter search: {e}")
        ))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_counter_search_thread_cleanup())

        self._counter_search_thread = thread
        self._counter_search_worker = worker
        thread.start()

    def _on_counter_search_thread_cleanup(self):
        self._counter_search_thread = None
        self._counter_search_worker = None

    def _on_counter_search_finished(self, counter_devices):
        self.counter_search_btn.setEnabled(True)
        self.counter_resource_combo.clear()

        if counter_devices:
            for dev in counter_devices:
                self.counter_resource_combo.addItem(dev)
            if hasattr(self, 'append_log'):
                self.append_log(f"[SYSTEM] Found {len(counter_devices)} counter(s).")
            if hasattr(self, 'set_page_status'):
                self.set_page_status(f"Found {len(counter_devices)} counter(s)")
            self.set_system_status(f"● Found {len(counter_devices)} device(s)")
        else:
            self.counter_resource_combo.addItem("USB0::0x0957::0x1907::MY00000000::INSTR")
            if hasattr(self, 'set_page_status'):
                self.set_page_status("No counter found", is_error=True)
            self.set_system_status("● No device found", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] No counter found. Default resource restored.")

    def _on_connect_or_disconnect_counter(self):
        if self.counter_connected:
            self._on_disconnect_counter()
        else:
            self._on_connect_counter()

    def _on_connect_counter(self):
        counter_type = self._current_counter_type
        resource = self.counter_resource_combo.currentText().strip()
        if not resource:
            if hasattr(self, 'set_page_status'):
                self.set_page_status("Invalid counter resource", is_error=True)
            self.set_system_status("● Invalid resource", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log("[ERROR] Invalid counter resource.")
            return

        if DEBUG_MOCK:
            self.Counter_ins = MockKeysight53230A()
            self.counter_connected = True
            self._current_counter_type = DEFAULT_COUNTER_TYPE
            _update_cnt_btn_state(self.counter_connect_btn, True)
            self.counter_search_btn.setEnabled(False)
            if hasattr(self, 'append_log'):
                self.append_log("[DEBUG] Mock counter connected.")
            if hasattr(self, 'set_page_status'):
                self.set_page_status("Counter connected (Mock)")
            self.set_system_status("● Mock device ready")
            if self._counter_top and hasattr(self._counter_top, 'connect_instrument'):
                self._counter_top.connect_instrument(resource, self.Counter_ins, counter_type=counter_type)
            self.counter_connection_changed.emit(True)
            return

        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"Connecting {counter_type}...")
        self.set_system_status(f"● Connecting {counter_type}")
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] Attempting {counter_type} connection...")
        self.counter_connect_btn.setEnabled(False)
        self._run_counter_instrument_task(
            self._connect_counter_task,
            self._on_connect_counter_finished,
            kwargs={"counter_type": counter_type, "resource": resource},
        )

    def _connect_counter_task(self, counter_type, resource):
        from instruments.factory import create_frequency_counter
        try:
            counter = create_frequency_counter(counter_type, resource)
        except Exception as e:
            return {"error": str(e), "counter_type": counter_type}

        idn = counter.identify()
        matched_type = _match_counter_type_from_idn(idn)
        return {"counter": counter, "idn": idn, "resource": resource, "counter_type": matched_type}

    def _on_connect_counter_finished(self, result):
        self.counter_connect_btn.setEnabled(True)
        if "error" in result:
            counter_type = result.get("counter_type", self._current_counter_type)
            self.Counter_ins = None
            if hasattr(self, 'set_page_status'):
                self.set_page_status(f"{counter_type} connection failed", is_error=True)
            self.set_system_status("● Connection failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] {counter_type} connection failed: {result['error']}")
            return

        counter_type = result["counter_type"]
        self._current_counter_type = counter_type
        self.Counter_ins = result["counter"]
        self.counter_resource = result["resource"]
        self.counter_connected = True
        _update_cnt_btn_state(self.counter_connect_btn, True)
        self.counter_search_btn.setEnabled(False)
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] {counter_type} connected.")
            self.append_log(f"[IDN] {result['idn']}")
        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"{counter_type} connected")
        self.set_system_status("● Connected")

        if self._counter_top and hasattr(self._counter_top, 'connect_instrument'):
            self._counter_top.connect_instrument(result["resource"], self.Counter_ins, counter_type=counter_type)

        self.counter_connection_changed.emit(True)

    def _on_disconnect_counter(self):
        counter_type = self._current_counter_type
        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"Disconnecting {counter_type}...")
        self.set_system_status(f"● Disconnecting {counter_type}")
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] Disconnecting {counter_type}...")
        self.counter_connect_btn.setEnabled(False)

        if self._counter_top and self._counter_top.is_connected:
            self._counter_top.disconnect()
            self.Counter_ins = None
            self._on_disconnect_counter_finished({"counter_type": counter_type})
        else:
            counter_ref = self.Counter_ins
            self.Counter_ins = None
            self._run_counter_instrument_task(
                self._disconnect_counter_task,
                self._on_disconnect_counter_finished,
                kwargs={"counter_ref": counter_ref, "counter_type": counter_type},
            )

    def _disconnect_counter_task(self, counter_ref, counter_type):
        if counter_ref is not None:
            if hasattr(counter_ref, 'disconnect'):
                counter_ref.disconnect()
            elif hasattr(counter_ref, 'instr') and counter_ref.instr:
                try:
                    counter_ref.instr.close()
                except Exception:
                    pass
        return {"counter_type": counter_type}

    def _on_disconnect_counter_finished(self, result):
        self.counter_connect_btn.setEnabled(True)
        counter_type = result.get("counter_type", self._current_counter_type)
        if "error" in result:
            if hasattr(self, 'set_page_status'):
                self.set_page_status(f"{counter_type} disconnect failed", is_error=True)
            self.set_system_status("● Disconnect failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] {counter_type} disconnect failed: {result['error']}")
            return

        self.counter_resource = None
        self.counter_connected = False
        _update_cnt_btn_state(self.counter_connect_btn, False)
        self.counter_search_btn.setEnabled(True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] {counter_type} disconnected.")
        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"{counter_type} disconnected")
        self.set_system_status("● Ready")

        self.counter_connection_changed.emit(False)

    def _run_counter_instrument_task(self, task_func, on_finished, kwargs=None):
        if self._counter_instr_thread is not None and self._counter_instr_thread.isRunning():
            if hasattr(self, 'append_log'):
                self.append_log("[WARN] Another counter operation is in progress.")
            return

        self._counter_instr_worker = _CounterInstrumentWorker(task_func, kwargs)
        self._counter_instr_thread = QThread()
        self._counter_instr_worker.moveToThread(self._counter_instr_thread)

        self._counter_instr_thread.started.connect(self._counter_instr_worker.run)
        self._counter_instr_worker.finished.connect(on_finished)
        self._counter_instr_worker.finished.connect(self._counter_instr_thread.quit)
        self._counter_instr_thread.finished.connect(self._cleanup_counter_instr_thread)

        self._counter_instr_thread.start()

    def _cleanup_counter_instr_thread(self):
        if self._counter_instr_thread is not None:
            self._counter_instr_thread.wait(5000)
            self._counter_instr_thread.deleteLater()
            self._counter_instr_thread = None
        if self._counter_instr_worker is not None:
            self._counter_instr_worker.deleteLater()
            self._counter_instr_worker = None

    def get_counter_instance(self):
        return self.Counter_ins

    def is_counter_connected_status(self):
        return self.counter_connected


if __name__ == "__main__":
    #python -m ui.modules.keysight_53230a_module_frame
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
        QLabel#fieldLabel {
            color: #8eb0e3;
            font-size: 11px;
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
                self.title_row.setContentsMargins(0, 0, 0, 0)
                self.title_label = QLabel(title)
                self.title_label.setObjectName("cardTitle")
                self.title_row.addWidget(self.title_label, 0, Qt.AlignVCenter)
                self.title_row.addStretch(1)
                self.main_layout.addLayout(self.title_row)
            else:
                self.title_label = None
                self.title_row = None

    class _DemoCounterWidget(Keysight53230AConnectionMixin, QWidget):
        counter_connection_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_counter_connection()
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Frequency Counter")
            self.build_counter_connection_widgets(card.main_layout, title_row=card.title_row)
            root.addWidget(card)
            root.addStretch()

            self.bind_counter_signals()

        def append_log(self, msg):
            print(msg)

        def set_page_status(self, text, is_error=False):
            print(f"[STATUS] {text}" + (" (ERROR)" if is_error else ""))

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = _DemoCounterWidget()
    w.setWindowTitle("Keysight 53230A Module Frame Demo")
    w.setFixedWidth(320)
    w.show()
    w.move(100, 200)

    sys.exit(app.exec())
