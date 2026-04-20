#python -m ui.modules.oscilloscope_module_frame
import os
import pyvisa
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal, QThread, QObject, QTimer, QRectF
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtSvg import QSvgRenderer

from ui.widgets.dark_combobox import DarkComboBox
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockMSO64B


_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "icons"
)
_SEARCH_ICON_PATH = os.path.join(_ICONS_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_ICONS_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_ICONS_DIR, "unlink.svg")

_SCOPE_BTN_HEIGHT = 24
_SCOPE_BTN_ICON_SIZE = 14
_SCOPE_BTN_RADIUS = 6


def _scope_search_style(h=_SCOPE_BTN_HEIGHT, r=_SCOPE_BTN_RADIUS):
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


def _scope_connect_style(h=_SCOPE_BTN_HEIGHT, r=_SCOPE_BTN_RADIUS):
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


def _scope_disconnect_style(h=_SCOPE_BTN_HEIGHT, r=_SCOPE_BTN_RADIUS):
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


class _ScopeSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=_SCOPE_BTN_ICON_SIZE,
                 btn_height=_SCOPE_BTN_HEIGHT, btn_radius=_SCOPE_BTN_RADIUS):
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
        self.setStyleSheet(_scope_search_style(h=btn_height, r=btn_radius))

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


def _update_scope_btn_state(btn, connected,
                            h=_SCOPE_BTN_HEIGHT, r=_SCOPE_BTN_RADIUS,
                            icon_size=_SCOPE_BTN_ICON_SIZE):
    from PySide6.QtCore import QSize as _QSize
    if connected:
        btn.setText("Disconnect")
        btn.setStyleSheet(_scope_disconnect_style(h=h, r=r))
        if os.path.isfile(_UNLINK_ICON_PATH):
            btn.setIcon(QIcon(_UNLINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
    else:
        btn.setText("Connect")
        btn.setStyleSheet(_scope_connect_style(h=h, r=r))
        if os.path.isfile(_LINK_ICON_PATH):
            btn.setIcon(QIcon(_LINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
        else:
            btn.setIcon(QIcon())


class _SearchScopeWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        rm = None
        try:
            rm = pyvisa.ResourceManager()
            all_resources = list(rm.list_resources()) or []
            scope_devices = []
            for dev in all_resources:
                instr = None
                try:
                    instr = rm.open_resource(dev, timeout=2000)
                    idn = instr.query('*IDN?').strip()
                    if any(kw in idn.upper() for kw in ["MSO", "DSO", "SCOPE", "OSCILLOSCOPE", "DSOX", "MSOX"]):
                        scope_devices.append(dev)
                except Exception:
                    pass
                finally:
                    if instr is not None:
                        try:
                            instr.close()
                        except Exception:
                            pass
            self.finished.emit(scope_devices)
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit([])
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass


class _ScopeInstrumentWorker(QObject):
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


class OscilloscopeConnectionMixin:
    scope_connection_changed = Signal(bool)

    def init_oscilloscope_connection(self, mso64b_top=None):
        self._mso64b_top = mso64b_top
        self._scope_rm = None
        self.Osc_ins = None
        self.scope_connected = False
        self.scope_resource = None
        self._scope_search_thread = None
        self._scope_search_worker = None
        self._scope_instr_thread = None
        self._scope_instr_worker = None

        if self._mso64b_top is not None and hasattr(self._mso64b_top, 'connection_changed'):
            self._mso64b_top.connection_changed.connect(self._on_mso64b_top_changed)

    def build_oscilloscope_connection_widgets(self, layout):
        scope_label = QLabel("Oscilloscope")
        scope_label.setObjectName("fieldLabel")
        layout.addWidget(scope_label)

        self.scope_type_combo = DarkComboBox()
        self.scope_type_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.scope_type_combo.setMinimumContentsLength(10)
        self.scope_type_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.scope_type_combo.addItems(["DSOX4034A", "MSO64B"])
        layout.addWidget(self.scope_type_combo)

        self.scope_resource_combo = DarkComboBox()
        self.scope_resource_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.scope_resource_combo.setMinimumContentsLength(10)
        self.scope_resource_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.scope_resource_combo.setEditable(True)
        self.scope_resource_combo.addItem("USB0::0x0957::0x17A4::MY61500152::INSTR")
        self.scope_resource_combo.lineEdit().setCursorPosition(0)
        self.scope_resource_combo.currentIndexChanged.connect(
            lambda: QTimer.singleShot(0, lambda: self.scope_resource_combo.lineEdit().setCursorPosition(0))
        )
        layout.addWidget(self.scope_resource_combo)

        scope_row = QHBoxLayout()
        scope_row.setSpacing(8)

        self.scope_search_btn = _ScopeSearchButton()

        self.scope_connect_btn = QPushButton()
        _update_scope_btn_state(self.scope_connect_btn, connected=False)

        scope_row.addWidget(self.scope_search_btn)
        scope_row.addWidget(self.scope_connect_btn)
        layout.addLayout(scope_row)

    def bind_oscilloscope_signals(self):
        self.scope_search_btn.clicked.connect(self._on_scope_search)
        self.scope_connect_btn.clicked.connect(self._on_connect_or_disconnect_scope)

    def sync_oscilloscope_from_top(self):
        if not self._mso64b_top:
            return
        if self._mso64b_top.is_connected and self._mso64b_top.mso64b:
            self.Osc_ins = self._mso64b_top.mso64b
            self.scope_resource = self._mso64b_top.visa_resource
            self.scope_connected = True
            _update_scope_btn_state(self.scope_connect_btn, True)
            self.scope_search_btn.setEnabled(False)
            scope_type = getattr(self._mso64b_top, 'scope_type', 'MSO64B') or 'MSO64B'
            idx = self.scope_type_combo.findText(scope_type)
            if idx >= 0:
                self.scope_type_combo.setCurrentIndex(idx)
            self.scope_type_combo.setEnabled(False)
            if self._mso64b_top.visa_resource:
                self.scope_resource_combo.clear()
                self.scope_resource_combo.addItem(self._mso64b_top.visa_resource)
        elif not self.scope_connected:
            _update_scope_btn_state(self.scope_connect_btn, False)

    def _on_mso64b_top_changed(self):
        if self._mso64b_top is None:
            return
        if hasattr(self, 'is_test_running') and self.is_test_running:
            return
        if self._mso64b_top.is_connected and self._mso64b_top.mso64b:
            if self.Osc_ins is self._mso64b_top.mso64b and self.scope_connected:
                return
            self.Osc_ins = self._mso64b_top.mso64b
            self.scope_resource = self._mso64b_top.visa_resource
            self.scope_connected = True
            _update_scope_btn_state(self.scope_connect_btn, True)
            self.scope_search_btn.setEnabled(False)
            scope_type = getattr(self._mso64b_top, 'scope_type', 'MSO64B') or 'MSO64B'
            idx = self.scope_type_combo.findText(scope_type)
            if idx >= 0:
                self.scope_type_combo.setCurrentIndex(idx)
            self.scope_type_combo.setEnabled(False)
            if self._mso64b_top.visa_resource:
                self.scope_resource_combo.clear()
                self.scope_resource_combo.addItem(self._mso64b_top.visa_resource)
            if hasattr(self, 'append_log'):
                self.append_log(f"[SYSTEM] {scope_type} synced from external connection.")
        else:
            if not self.scope_connected:
                return
            self.Osc_ins = None
            self.scope_resource = None
            self.scope_connected = False
            _update_scope_btn_state(self.scope_connect_btn, False)
            self.scope_type_combo.setEnabled(True)
            self.scope_search_btn.setEnabled(True)
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] Oscilloscope disconnected externally.")

    def _on_scope_search(self):
        if self._mso64b_top and self._mso64b_top.is_connected:
            return
        if hasattr(self, 'set_page_status'):
            self.set_page_status("Searching scope resources...")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Scanning for oscilloscope resources (LAN & USB)...")
        self.scope_search_btn.setEnabled(False)

        if self._scope_search_thread is not None and self._scope_search_thread.isRunning():
            return

        worker = _SearchScopeWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scope_search_finished)
        worker.error.connect(lambda e: (
            hasattr(self, 'append_log') and self.append_log(f"[WARN] Scope search: {e}")
        ))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_scope_search_thread_cleanup())

        self._scope_search_thread = thread
        self._scope_search_worker = worker
        thread.start()

    def _on_scope_search_thread_cleanup(self):
        self._scope_search_thread = None
        self._scope_search_worker = None

    def _on_scope_search_finished(self, scope_devices):
        self.scope_search_btn.setEnabled(True)
        self.scope_resource_combo.clear()

        if scope_devices:
            for dev in scope_devices:
                self.scope_resource_combo.addItem(dev)
            if hasattr(self, 'append_log'):
                self.append_log(f"[SYSTEM] Found {len(scope_devices)} oscilloscope(s).")
            if hasattr(self, 'set_page_status'):
                self.set_page_status(f"Found {len(scope_devices)} scope(s)")
        else:
            self.scope_resource_combo.addItem("USB0::0x0957::0x17A4::MY61500152::INSTR")
            if hasattr(self, 'set_page_status'):
                self.set_page_status("No oscilloscope found", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] No oscilloscope found. Default resource restored.")

    def _on_connect_or_disconnect_scope(self):
        if self.scope_connected:
            self._on_disconnect_scope()
        else:
            self._on_connect_scope()

    def _on_connect_scope(self):
        scope_type = self.scope_type_combo.currentText()
        resource = self.scope_resource_combo.currentText().strip()
        if not resource:
            if hasattr(self, 'set_page_status'):
                self.set_page_status("Invalid scope resource", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log("[ERROR] Invalid scope resource.")
            return

        if DEBUG_MOCK:
            self.Osc_ins = MockMSO64B()
            self.scope_connected = True
            _update_scope_btn_state(self.scope_connect_btn, True)
            self.scope_search_btn.setEnabled(False)
            if hasattr(self, 'append_log'):
                self.append_log("[DEBUG] Mock scope connected.")
            if hasattr(self, 'set_page_status'):
                self.set_page_status("Scope connected (Mock)")
            if self._mso64b_top:
                self._mso64b_top.connect_instrument(resource, self.Osc_ins, scope_type="MSO64B")
            self.scope_connection_changed.emit(True)
            return

        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"Connecting {scope_type}...")
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] Attempting {scope_type} connection...")
        self.scope_connect_btn.setEnabled(False)
        self._run_scope_instrument_task(
            self._connect_scope_task,
            self._on_connect_scope_finished,
            kwargs={"scope_type": scope_type, "resource": resource},
        )

    def _connect_scope_task(self, scope_type, resource):
        if scope_type == "MSO64B":
            from instruments.scopes.tektronix.mso64b import MSO64B
            osc = MSO64B(resource)
        elif scope_type == "DSOX4034A":
            from instruments.scopes.keysight.dsox4034a import DSOX4034A
            osc = DSOX4034A(resource)
        else:
            return {"error": f"Unknown scope type: {scope_type}"}

        idn = osc.identify_instrument()
        return {"osc": osc, "idn": idn, "resource": resource, "scope_type": scope_type}

    def _on_connect_scope_finished(self, result):
        self.scope_connect_btn.setEnabled(True)
        if "error" in result:
            scope_type = result.get("scope_type", self.scope_type_combo.currentText())
            self.Osc_ins = None
            if hasattr(self, 'set_page_status'):
                self.set_page_status(f"{scope_type} connection failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] {scope_type} connection failed: {result['error']}")
            return

        scope_type = result["scope_type"]
        self.Osc_ins = result["osc"]
        self.scope_resource = result["resource"]
        self.scope_connected = True
        _update_scope_btn_state(self.scope_connect_btn, True)
        self.scope_type_combo.setEnabled(False)
        self.scope_search_btn.setEnabled(False)
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] {scope_type} connected.")
            self.append_log(f"[IDN] {result['idn']}")
        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"{scope_type} connected")

        if self._mso64b_top:
            self._mso64b_top.connect_instrument(result["resource"], self.Osc_ins, scope_type=scope_type)

    def _on_disconnect_scope(self):
        scope_type = self.scope_type_combo.currentText()
        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"Disconnecting {scope_type}...")
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] Disconnecting {scope_type}...")
        self.scope_connect_btn.setEnabled(False)

        if self._mso64b_top and self._mso64b_top.is_connected:
            self._mso64b_top.disconnect()
            self.Osc_ins = None
            self._on_disconnect_scope_finished({"scope_type": scope_type})
        else:
            osc_ref = self.Osc_ins
            self.Osc_ins = None
            self._run_scope_instrument_task(
                self._disconnect_scope_task,
                self._on_disconnect_scope_finished,
                kwargs={"osc_ref": osc_ref, "scope_type": scope_type},
            )

    def _disconnect_scope_task(self, osc_ref, scope_type):
        if osc_ref is not None:
            if hasattr(osc_ref, 'disconnect'):
                osc_ref.disconnect()
            elif hasattr(osc_ref, 'instrument') and osc_ref.instrument:
                osc_ref.instrument.close()
        return {"scope_type": scope_type}

    def _on_disconnect_scope_finished(self, result):
        self.scope_connect_btn.setEnabled(True)
        scope_type = result.get("scope_type", self.scope_type_combo.currentText())
        if "error" in result:
            if hasattr(self, 'set_page_status'):
                self.set_page_status(f"{scope_type} disconnect failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] {scope_type} disconnect failed: {result['error']}")
            return

        self.scope_resource = None
        self.scope_connected = False
        _update_scope_btn_state(self.scope_connect_btn, False)
        self.scope_type_combo.setEnabled(True)
        self.scope_search_btn.setEnabled(True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[SYSTEM] {scope_type} disconnected.")
        if hasattr(self, 'set_page_status'):
            self.set_page_status(f"{scope_type} disconnected")

    def _run_scope_instrument_task(self, task_func, on_finished, kwargs=None):
        if self._scope_instr_thread is not None and self._scope_instr_thread.isRunning():
            if hasattr(self, 'append_log'):
                self.append_log("[WARN] Another scope operation is in progress.")
            return

        self._scope_instr_worker = _ScopeInstrumentWorker(task_func, kwargs)
        self._scope_instr_thread = QThread()
        self._scope_instr_worker.moveToThread(self._scope_instr_thread)

        self._scope_instr_thread.started.connect(self._scope_instr_worker.run)
        self._scope_instr_worker.finished.connect(on_finished)
        self._scope_instr_worker.finished.connect(self._scope_instr_thread.quit)
        self._scope_instr_thread.finished.connect(self._cleanup_scope_instr_thread)

        self._scope_instr_thread.start()

    def _cleanup_scope_instr_thread(self):
        if self._scope_instr_thread is not None:
            self._scope_instr_thread.wait(5000)
            self._scope_instr_thread.deleteLater()
            self._scope_instr_thread = None
        if self._scope_instr_worker is not None:
            self._scope_instr_worker.deleteLater()
            self._scope_instr_worker = None

    def get_scope_instance(self):
        return self.Osc_ins

    def is_scope_connected_status(self):
        return self.scope_connected


if __name__ == "__main__":
    #python -m ui.modules.oscilloscope_module_frame
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
            self.main_layout.setContentsMargins(10, 8, 10, 8)
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

    class _DemoScopeWidget(OscilloscopeConnectionMixin, QWidget):
        scope_connection_changed = Signal(bool)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_oscilloscope_connection()
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Oscilloscope Connection")
            self.build_oscilloscope_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_oscilloscope_signals()

        def append_log(self, msg):
            print(msg)

        def set_page_status(self, text, is_error=False):
            print(f"[STATUS] {text}" + (" (ERROR)" if is_error else ""))

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = _DemoScopeWidget()
    w.setWindowTitle("Oscilloscope Module Frame Demo")
    w.setFixedWidth(320)
    w.show()
    w.move(100, 200)

    sys.exit(app.exec())
