import serial
import serial.tools.list_ports
from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal, QThread, QObject

from ui.styles.button import SpinningSearchButton, update_connect_button_state
from ui.widgets.dark_combobox import DarkComboBox
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockVT6002


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
        self.vt6002_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        layout.addWidget(self.vt6002_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.vt6002_search_btn = SpinningSearchButton()

        self.vt6002_connect_btn = QPushButton()
        update_connect_button_state(self.vt6002_connect_btn, connected=False)

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
        update_connect_button_state(self.vt6002_connect_btn, connected)
        self.vt6002_search_btn.setEnabled(not connected)
        self.vt6002_combo.setEnabled(not connected)

    def get_vt6002_instance(self):
        return self.vt6002

    def is_vt6002_connected_status(self):
        return self.is_vt6002_connected
