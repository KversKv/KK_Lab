from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from ui.widgets.dark_combobox import DarkComboBox
from ui.styles.button import SpinningSearchButton, update_connect_button_state
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C


class _SearchN6705CWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        rm = None
        try:
            rm = pyvisa.ResourceManager()
            resources = list(rm.list_resources()) or []
            n6705c_devices = []
            for dev in resources:
                instr = None
                try:
                    instr = rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception:
                    pass
                finally:
                    if instr is not None:
                        try:
                            instr.close()
                        except Exception:
                            pass
            self.finished.emit(n6705c_devices)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass


DEFAULT_VISA_RESOURCE = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"


class N6705CConnectionMixin:
    connection_status_changed = Signal(bool)

    def init_n6705c_connection(self, n6705c_top=None):
        self._n6705c_top = n6705c_top
        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []
        self._n6705c_search_thread = None
        self._n6705c_search_worker = None

    def build_n6705c_connection_widgets(self, layout):
        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        layout.addWidget(self.system_status_label)

        self.visa_resource_combo = DarkComboBox()
        self.visa_resource_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.visa_resource_combo.setMinimumContentsLength(10)
        self.visa_resource_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.visa_resource_combo.addItem(DEFAULT_VISA_RESOURCE)
        layout.addWidget(self.visa_resource_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.search_btn = SpinningSearchButton()

        self.connect_btn = QPushButton()
        update_connect_button_state(self.connect_btn, connected=False)

        btn_row.addWidget(self.search_btn)
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

    def bind_n6705c_signals(self):
        self.search_btn.clicked.connect(self._on_n6705c_search)
        self.connect_btn.clicked.connect(self._on_n6705c_connect_or_disconnect)

    def _update_n6705c_connect_button_state(self, connected: bool):
        self.is_connected = connected
        update_connect_button_state(self.connect_btn, connected)

    def sync_n6705c_from_top(self):
        if not self._n6705c_top:
            return
        if self._n6705c_top.is_connected_a and self._n6705c_top.n6705c_a:
            self.n6705c = self._n6705c_top.n6705c_a
            self._update_n6705c_connect_button_state(True)
            self.search_btn.setEnabled(False)
            if self._n6705c_top.visa_resource_a:
                self.visa_resource_combo.clear()
                self.visa_resource_combo.addItem(self._n6705c_top.visa_resource_a)
                pretty_name = self._n6705c_top.visa_resource_a
                try:
                    pretty_name = self._n6705c_top.visa_resource_a.split("::")[1]
                except Exception:
                    pass
                self.set_system_status(f"● Connected to: {pretty_name}")
        elif not self.is_connected:
            self._update_n6705c_connect_button_state(False)

    def set_system_status(self, status, is_error=False):
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

    def _on_n6705c_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        if DEBUG_MOCK:
            self.visa_resource_combo.clear()
            self.visa_resource_combo.addItem("DEBUG::MOCK::N6705C")
            self.set_system_status("● Mock device ready")
            if hasattr(self, 'append_log'):
                self.append_log("[DEBUG] Mock device loaded, skip real VISA scan.")
            return
        self.set_system_status("● Searching")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Scanning VISA resources...")
        self.search_btn.setEnabled(False)
        self.connect_btn.setEnabled(False)

        if self._n6705c_search_thread is not None and self._n6705c_search_thread.isRunning():
            return

        worker = _SearchN6705CWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_n6705c_search_done)
        worker.error.connect(self._on_n6705c_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_n6705c_search_thread_cleanup())

        self._n6705c_search_thread = thread
        self._n6705c_search_worker = worker
        thread.start()

    def _on_n6705c_search_thread_cleanup(self):
        self._n6705c_search_thread = None
        self._n6705c_search_worker = None

    def _on_n6705c_search_done(self, n6705c_devices):
        self.visa_resource_combo.setEnabled(True)
        self.visa_resource_combo.clear()

        if n6705c_devices:
            for dev in n6705c_devices:
                self.visa_resource_combo.addItem(dev)
            count = len(n6705c_devices)
            self.set_system_status(f"● Found {count} device(s)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[SYSTEM] Found {count} compatible N6705C device(s).")
            if DEFAULT_VISA_RESOURCE in n6705c_devices:
                self.visa_resource_combo.setCurrentText(DEFAULT_VISA_RESOURCE)
            else:
                self.visa_resource_combo.setCurrentIndex(0)
        else:
            self.visa_resource_combo.addItem("No N6705C device found")
            self.visa_resource_combo.setEnabled(False)
            self.set_system_status("● No device found", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] No compatible N6705C instrument found.")

        self.search_btn.setEnabled(True)
        self.connect_btn.setEnabled(True)

    def _on_n6705c_search_error(self, err):
        self.set_system_status("● Search failed", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[ERROR] Search failed: {err}")
        self.search_btn.setEnabled(True)
        self.connect_btn.setEnabled(True)

    def _on_n6705c_connect_or_disconnect(self):
        if self.is_connected:
            self._on_n6705c_disconnect()
        else:
            self._on_n6705c_connect()

    def _on_n6705c_connect(self):
        if DEBUG_MOCK:
            self.n6705c = MockN6705C()
            self._update_n6705c_connect_button_state(True)
            self.set_system_status("● Connected to: Mock N6705C (DEBUG)")
            self.search_btn.setEnabled(False)
            if hasattr(self, 'append_log'):
                self.append_log("[DEBUG] Mock N6705C connected.")
            device_address = self.visa_resource_combo.currentText()
            if self._n6705c_top:
                self._n6705c_top.connect_a(device_address, self.n6705c)
            self.connection_status_changed.emit(True)
            return

        self.set_system_status("● Connecting")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Attempting instrument connection...")
        self.connect_btn.setEnabled(False)

        try:
            device_address = self.visa_resource_combo.currentText()
            self.n6705c = N6705C(device_address)

            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self._update_n6705c_connect_button_state(True)
                self.search_btn.setEnabled(False)

                pretty_name = device_address
                try:
                    pretty_name = device_address.split("::")[1]
                except Exception:
                    pass

                self.set_system_status(f"● Connected to: {pretty_name}")
                if hasattr(self, 'append_log'):
                    self.append_log("[SYSTEM] N6705C connected successfully.")
                    self.append_log(f"[IDN] {idn.strip()}")

                if self._n6705c_top:
                    self._n6705c_top.connect_a(device_address, self.n6705c)

                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("● Device mismatch", is_error=True)
                if hasattr(self, 'append_log'):
                    self.append_log("[ERROR] Connected device is not N6705C.")
        except Exception as e:
            self.set_system_status("● Connection failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] Connection failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_n6705c_disconnect(self):
        self.set_system_status("● Disconnecting")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Disconnecting instrument...")
        self.connect_btn.setEnabled(False)

        try:
            if self._n6705c_top:
                self._n6705c_top.disconnect_a()
                self.n6705c = None
            else:
                if self.n6705c is not None:
                    if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                        self.n6705c.instr.close()
                    if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                        self.n6705c.rm.close()
                self.n6705c = None

            self._update_n6705c_connect_button_state(False)
            self.set_system_status("● Ready")
            self.search_btn.setEnabled(True)
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] Instrument disconnected.")
            self.connection_status_changed.emit(False)
        except Exception as e:
            self.set_system_status("● Disconnect failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] Disconnect failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def get_n6705c_instance(self):
        return self.n6705c

    def is_n6705c_connected(self):
        return self.is_connected
