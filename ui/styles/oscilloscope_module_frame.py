import pyvisa
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal, QThread, QObject

from ui.styles.button import SpinningSearchButton, update_connect_button_state
from ui.widgets.dark_combobox import DarkComboBox
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockMSO64B


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
        layout.addWidget(self.scope_resource_combo)

        scope_row = QHBoxLayout()
        scope_row.setSpacing(8)

        self.scope_search_btn = SpinningSearchButton()

        self.scope_connect_btn = QPushButton()
        update_connect_button_state(self.scope_connect_btn, connected=False)

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
            update_connect_button_state(self.scope_connect_btn, True)
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
            update_connect_button_state(self.scope_connect_btn, False)

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
            update_connect_button_state(self.scope_connect_btn, True)
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
            update_connect_button_state(self.scope_connect_btn, False)
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
            update_connect_button_state(self.scope_connect_btn, True)
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
        update_connect_button_state(self.scope_connect_btn, True)
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
        update_connect_button_state(self.scope_connect_btn, False)
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
