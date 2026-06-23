# -*- coding: utf-8 -*-
"""SerialComMixin 连接职责拆分：端口搜索 / 连接 / 断开 / 自动波特率 / 读线程。

由 serialCom_module_frame.py 抽取，供 SerialComMixin 多继承装配。
"""

import os
import time

import serial
import serial.tools.list_ports

from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget,
)
from PySide6.QtCore import Qt, QSize, QThread

from debug_config import DEBUG_MOCK
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from core.auto_baud_detector import (
    AUTO_BAUD_CONFIG, AutoBaudScanWorker, AutoBaudState,
)
from ui.modules.serialCom_module.widgets import (
    _MixinSerialSettingsDialog,
    _SearchSerialPortWorker,
    _SerialSearchButton,
    _update_serial_btn_state,
)
from ui.modules.serialCom_module.serialCom_module_frame import (
    MODE_FULL,
    MODE_INLINE,
    _CLR_CONNECT_TEXT,
    _CLR_DISCONNECT_TEXT,
    _SERIAL_BTN_HEIGHT,
    _SERIAL_BTN_ICON_SIZE,
    _SERIAL_BTN_RADIUS,
    _SVG_SERIAL_DIR,
    SerialDarkComboBox,
    inline_serial_label_style,
    inline_serial_search_button_extra_style,
    main_connect_button_style,
    status_label_style,
)


class ConnectionMixin:
    """连接相关方法：端口搜索、连接/断开、自动波特率、读线程、会话管理。"""

    def init_serial_connection(self, mode=MODE_FULL, baudrate=115200, prefix="Serial"):
        from ui.modules.serialCom_module.serial_session_manager import SerialSessionManager
        self._serial_mode = mode
        self._serial_baudrate = baudrate
        self._serial_bytesize = 8
        self._serial_stopbits = serial.STOPBITS_ONE
        self._serial_parity = serial.PARITY_NONE
        self._serial_xonxoff = False
        self._serial_rtscts = False
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

        self._sc_session_manager = SerialSessionManager(parent=self)
        self._sc_sessions: dict[str, "SerialSession"] = self._sc_session_manager._sessions
        self._sc_active_session_id: str | None = None

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
            self.serial_label.setStyleSheet(inline_serial_label_style())
            row.addWidget(self.serial_label)

            self.serial_combo = SerialDarkComboBox()
            self.serial_combo.setSizeAdjustPolicy(
                SerialDarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            self.serial_combo.setMinimumContentsLength(10)
            self.serial_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.serial_combo.setFixedHeight(_inline_h)
            _font = self.serial_combo.font()
            _font.setPixelSize(12)
            self.serial_combo.setFont(_font)
            row.addWidget(self.serial_combo, 1)

            self.serial_search_btn = _SerialSearchButton(
                icon_size=_inline_icon,
                btn_height=_inline_h,
                btn_radius=_inline_r,
            )
            self.serial_search_btn.setFixedSize(_inline_h, _inline_h)
            self.serial_search_btn.setStyleSheet(
                self.serial_search_btn.styleSheet() + inline_serial_search_button_extra_style(_inline_h)
            )
            row.addWidget(self.serial_search_btn)

            layout.addLayout(row)
            return

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        status_row.setContentsMargins(0, 0, 0, 0)

        self.serial_status_label = QLabel("Not Connected")
        self.serial_status_label.setObjectName("statusErr")
        status_row.addWidget(self.serial_status_label, 1)

        self.serial_settings_btn = QPushButton()
        self.serial_settings_btn.setIcon(
            _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "settings.svg"), "#8ea6cf", 14)
        )
        self.serial_settings_btn.setIconSize(QSize(14, 14))
        self.serial_settings_btn.setToolTip("Serial port settings")
        self.serial_settings_btn.setFocusPolicy(Qt.NoFocus)
        self.serial_settings_btn.setCursor(Qt.PointingHandCursor)
        self.serial_settings_btn.setFixedSize(btn_height, btn_height)
        self.serial_settings_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:#8ea6cf;border:1px solid #2b466f;"
            f"border-radius:{btn_radius}px;padding:0;}}"
            f"QPushButton:hover{{color:#e9eef7;border-color:#3a5a8a;background:#162a4a;}}"
            f"QPushButton:pressed{{background:#0f1f3a;}}"
            f"QPushButton:disabled{{color:#4a5b78;border-color:#1f3262;}}"
        )
        status_row.addWidget(self.serial_settings_btn, 0)

        layout.addLayout(status_row)

        self.serial_combo = SerialDarkComboBox()
        self.serial_combo.setSizeAdjustPolicy(
            SerialDarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
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
        if hasattr(self, 'serial_settings_btn'):
            self.serial_settings_btn.clicked.connect(self._on_serial_settings)

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
            self._set_serial_status("Mock port ready")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Mock port loaded.")
            return

        if self._serial_search_thread is not None and self._serial_search_thread.isRunning():
            return

        self._set_serial_status("Searching")
        self.serial_search_btn.setEnabled(False)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(False)

        worker = _SearchSerialPortWorker()
        thread = QThread(self)
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
            self._set_serial_status(f"Found {count} port(s)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Found {count} serial port(s).")
        else:
            self.serial_combo.addItem("No serial ports found")
            self.serial_combo.setEnabled(False)
            self._set_serial_status("No port found", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] No serial ports found.")

        self.serial_search_btn.setEnabled(True)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(bool(ports))

    def _on_serial_search_error(self, err):
        self._set_serial_status("Search failed", is_error=True)
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

            session_id = "primary"
            session = self._sc_session_manager.get_session(session_id)
            if session is None:
                session = self._sc_session_manager.create_session(
                    session_id=session_id, display_name=self._serial_prefix, auto_activate=True
                )
            session.configure(port=port, baudrate=br)
            session._serial_conn = conn
            session._connected = True
            self._sc_active_session_id = session_id

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
            self._set_serial_status("No valid port selected", is_error=True)
            self.serial_connect_btn.setEnabled(True)
            return

        session_id = "primary"
        session = self._sc_session_manager.get_session(session_id)
        if session is None:
            session = self._sc_session_manager.create_session(
                session_id=session_id, display_name=self._serial_prefix, auto_activate=True
            )
        session.configure(
            port=port,
            baudrate=self._serial_baudrate,
            bytesize=self._serial_bytesize,
            stopbits=self._serial_stopbits,
            parity=self._serial_parity,
            xonxoff=self._serial_xonxoff,
            rtscts=self._serial_rtscts,
        )

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_connected = True
            session._connected = True
            self._sc_active_session_id = session_id
            self._update_serial_connect_ui(True)
            self._set_serial_status(f"Connected to: MOCK (DEBUG)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Mock serial connected.")
            self.serial_connection_changed.emit(True)
            return

        self._set_serial_status("Connecting")
        try:
            conn = serial.Serial(
                port,
                self._serial_baudrate,
                bytesize=self._serial_bytesize,
                stopbits=self._serial_stopbits,
                parity=self._serial_parity,
                xonxoff=self._serial_xonxoff,
                rtscts=self._serial_rtscts,
                timeout=1,
            )
            self._serial_conn = conn
            self._serial_port = port
            self._serial_connected = True
            session._serial_conn = conn
            session._connected = True
            self._sc_active_session_id = session_id
            self._update_serial_connect_ui(True)
            self._set_serial_status(f"Connected to: {port}")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Connected: {port} @ {self._serial_baudrate}")
            self.serial_connection_changed.emit(True)
            self._start_serial_read()
        except Exception as e:
            self._set_serial_status("Connection failed", is_error=True)
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
        session = self._sc_session_manager.get_session("primary")
        if session is not None:
            session._serial_conn = None
            session._connected = False
        self._update_serial_connect_ui(False)
        self._set_serial_status("Not Connected", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Disconnected.")
        self.serial_connection_changed.emit(False)
        self.serial_connect_btn.setEnabled(True)

    def _on_serial_settings(self):
        dlg = _MixinSerialSettingsDialog(
            parent=self if isinstance(self, QWidget) else None,
            baudrate=self._serial_baudrate,
            bytesize=self._serial_bytesize,
            stopbits=self._serial_stopbits,
            parity=self._serial_parity,
            xonxoff=self._serial_xonxoff,
            rtscts=self._serial_rtscts,
            connected=self._serial_connected,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        cfg = dlg.result_config()
        self._serial_baudrate = cfg["baudrate"]
        self._serial_bytesize = cfg["bytesize"]
        self._serial_stopbits = cfg["stopbits"]
        self._serial_parity = cfg["parity"]
        self._serial_xonxoff = cfg["xonxoff"]
        self._serial_rtscts = cfg["rtscts"]

        session = self._sc_session_manager.get_session("primary") \
            if hasattr(self, "_sc_session_manager") else None
        if session is not None:
            session.configure(
                port=session.port or (self._serial_port or ""),
                baudrate=self._serial_baudrate,
                bytesize=self._serial_bytesize,
                stopbits=self._serial_stopbits,
                parity=self._serial_parity,
                xonxoff=self._serial_xonxoff,
                rtscts=self._serial_rtscts,
            )

        if hasattr(self, "append_log"):
            self.append_log(
                f"[{self._serial_prefix}] Settings updated: "
                f"{self._serial_baudrate} {self._serial_bytesize}"
                f"{self._serial_parity}{self._serial_stopbits} "
                f"flow={'XON' if self._serial_xonxoff else ('RTS' if self._serial_rtscts else 'None')}"
            )

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
        if hasattr(self, 'serial_settings_btn'):
            self.serial_settings_btn.setEnabled(not connected)

    def _start_serial_read(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialReadWorker
        if self._serial_conn is None or not self._serial_conn.is_open:
            return
        if self._serial_read_thread is not None and self._serial_read_thread.isRunning():
            return

        worker = _SerialReadWorker(self._serial_conn)
        thread = QThread(self)
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
        active = self._sc_session_manager.active_session
        if active is not None and active.connected:
            return active.send(data)
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

    def send_to_session(self, session_id: str, data) -> bool:
        return self._sc_session_manager.send_to_session(session_id, data)

    def send_to_active_session(self, data) -> bool:
        return self._sc_session_manager.send_to_active_session(data)

    def broadcast_send(self, data, session_ids=None) -> dict:
        return self._sc_session_manager.broadcast_send(data, session_ids)

    def get_serial_connection(self):
        active = self._sc_session_manager.active_session
        if active is not None:
            return active.serial_conn
        return self._serial_conn

    def is_serial_connected(self):
        active = self._sc_session_manager.active_session
        if active is not None:
            return active.connected
        return self._serial_connected

    def close_serial(self):
        if hasattr(self, "_sc_stop_ntp_sync"):
            self._sc_stop_ntp_sync()
        if getattr(self, "_sc_script_running", False):
            self._sc_script_stop()
        self._sc_session_manager.cleanup_all()
        self._stop_serial_read()
        if hasattr(self, '_sc_extra_log_panels'):
            for panel in self._sc_extra_log_panels:
                if panel.get("read_worker"):
                    panel["read_worker"].stop()
                if panel.get("read_thread") and panel["read_thread"].isRunning():
                    panel["read_thread"].quit()
                    panel["read_thread"].wait(2000)
                panel["read_thread"] = None
                panel["read_worker"] = None
                try:
                    if panel.get("conn") and panel["conn"].is_open:
                        panel["conn"].close()
                except Exception:
                    pass
                panel["conn"] = None
        if hasattr(self, '_sc_log_file_handle'):
            self._sc_stop_auto_save()
        if hasattr(self, '_sc_save_handle'):
            self._sc_stop_manual_save()
        if hasattr(self, '_sc_log_temp_handle'):
            self._sc_close_temp_log(delete=True)
        try:
            if self._serial_conn is not None and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception:
            pass
        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False


    def _sc_on_connect_toggle(self):
        if self._serial_connected:
            self._sc_do_disconnect()
        else:
            self._sc_do_connect()

    def _sc_do_connect(self):
        port_text = self._sc_port_combo.currentText()
        if not port_text or port_text.startswith("No "):
            self._sc_append_system("[ERROR] No valid port selected", force_primary=True)
            return

        port = port_text.split()[0]

        baud_text = self._sc_baud_combo.currentText().strip()
        try:
            baudrate = int(baud_text)
        except ValueError:
            self._sc_append_system(f"[ERROR] Invalid baud rate: {baud_text}", force_primary=True)
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

        session_id = "primary"
        session = self._sc_session_manager.get_session(session_id)
        if session is None:
            session = self._sc_session_manager.create_session(
                session_id=session_id, display_name=self._serial_prefix, auto_activate=True
            )
        session.configure(
            port=port, baudrate=baudrate, bytesize=databit,
            stopbits=stopbits, parity=parity, xonxoff=xonxoff, rtscts=rtscts,
        )

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_baudrate = baudrate
            self._serial_connected = True
            session._connected = True
            self._sc_active_session_id = session_id
            self._sc_update_connect_ui(True)
            self._sc_start_temp_log()
            self._sc_append_system(f"[INFO] Mock connected: {port} @ {baudrate}", force_primary=True)
            self.serial_connection_changed.emit(True)
            if getattr(self, '_sc_log_auto_save', False):
                self._sc_start_auto_save()
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
            session._serial_conn = conn
            session._connected = True
            self._sc_active_session_id = session_id
            self._sc_update_connect_ui(True)
            self._sc_start_temp_log()
            self._sc_append_system(f"[INFO] Connected: {port} @ {baudrate}", force_primary=True)
            self.serial_connection_changed.emit(True)
            if getattr(self, '_sc_log_auto_save', False):
                self._sc_start_auto_save()
            if self._sc_auto_detect_cb.isChecked():
                self._sc_auto_baud_monitor.enabled = True
                self._sc_auto_baud_monitor.runtime_redetect_enabled = True
                self._sc_auto_baud_pending_first_rx = True
                self._sc_auto_baud_initial_buf = bytearray()
                self._sc_auto_baud_initial_ts = time.perf_counter()
                self._sc_append_system("[INFO] Auto-detect enabled, waiting for RX data...", force_primary=True)
            self._start_serial_read()
        except Exception as e:
            self._sc_append_system(f"[ERROR] Connection failed: {e}", force_primary=True)

    def _sc_do_disconnect(self):
        self._stop_serial_read()
        self._sc_stop_auto_baud_scan()
        self._sc_stop_auto_save()
        self._sc_close_temp_log(delete=True)
        try:
            if self._serial_conn and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception as e:
            self._sc_append_system(f"[WARN] Close error: {e}", force_primary=True)
        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False
        session = self._sc_session_manager.get_session("primary")
        if session is not None:
            session._serial_conn = None
            session._connected = False
        self._sc_update_connect_ui(False)
        self._sc_append_system("[INFO] Disconnected", force_primary=True)
        self.serial_connection_changed.emit(False)

    def _sc_update_connect_ui(self, connected):
        if not hasattr(self, '_sc_connect_btn_fixed_width_applied'):
            self._sc_connect_btn.setFixedWidth(96)
            self._sc_connect_btn_fixed_width_applied = True
        if connected:
            self._sc_connect_btn.setText("Disconnect")
            self._sc_connect_btn.setStyleSheet(main_connect_button_style(connected=True))
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "disconnect.svg"), _CLR_DISCONNECT_TEXT, 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText(f"\u2022 Port: {self._serial_port}")
            self._sc_status_port_label.setStyleSheet(status_label_style("ok", include_font=True))
            baud = getattr(self, '_serial_baudrate', '-')
            self._sc_status_baud_label.setText(f"Baud rate (bps): {baud}")
        else:
            self._sc_connect_btn.setText("Connect")
            self._sc_connect_btn.setStyleSheet(main_connect_button_style(connected=False))
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), _CLR_CONNECT_TEXT, 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText("\u2022 Port: Unconnected")
            self._sc_status_port_label.setStyleSheet(status_label_style("error", include_font=True))
            self._sc_status_baud_label.setText("Baud rate (bps): -")

        self._sc_port_combo.setEnabled(not connected)
        auto_detect_on = getattr(self, '_sc_auto_detect_cb', None) and self._sc_auto_detect_cb.isChecked()
        self._sc_baud_combo.setEditable(not auto_detect_on)
        self._sc_baud_combo.setEnabled(not auto_detect_on)

    def _sc_on_baudrate_changed(self):
        baud_text = self._sc_baud_combo.currentText().strip()
        try:
            baudrate = int(baud_text)
        except ValueError:
            if self._serial_connected:
                self._sc_append_system(f"[ERROR] Invalid baud rate: {baud_text}", force_primary=True)
            return

        if baudrate == getattr(self, '_serial_baudrate', None):
            return

        if not self._serial_connected:
            self._serial_baudrate = baudrate
            return

        if DEBUG_MOCK or self._serial_conn is None:
            self._serial_baudrate = baudrate
            if hasattr(self, '_sc_status_baud_label'):
                self._sc_status_baud_label.setText(f"Baud rate (bps): {baudrate}")
            self._sc_append_system(f"[INFO] Baud rate updated: {baudrate}", force_primary=True)
            return

        try:
            self._serial_conn.baudrate = baudrate
            self._serial_baudrate = baudrate
            if hasattr(self, '_sc_status_baud_label'):
                self._sc_status_baud_label.setText(f"Baud rate (bps): {baudrate}")
            self._sc_append_system(f"[INFO] Baud rate updated: {baudrate}", force_primary=True)
        except Exception as e:
            self._sc_append_system(f"[ERROR] Failed to set baud rate: {e}", force_primary=True)

    def _sc_on_auto_detect_toggled(self, checked):
        self._sc_baud_combo.setEditable(not checked)
        self._sc_baud_combo.setEnabled(not checked)
        self._sc_auto_baud_monitor.enabled = checked
        self._sc_auto_baud_monitor.runtime_redetect_enabled = checked
        if checked:
            self._sc_status_autobaud_label.setVisible(True)
            self._sc_status_autobaud_label.setText("AutoBaud: ON")
            if self._serial_connected:
                self._sc_auto_baud_pending_first_rx = True
                self._sc_auto_baud_initial_buf = bytearray()
                self._sc_auto_baud_initial_ts = time.perf_counter()
                self._sc_append_system("[INFO] Auto-detect enabled, waiting for RX data...", force_primary=True)
        else:
            self._sc_status_autobaud_label.setVisible(False)
            self._sc_auto_baud_monitor.reset()
            self._sc_auto_baud_monitor.state = AutoBaudState.UNKNOWN
            self._sc_stop_auto_baud_scan()
            self._sc_auto_baud_pending_first_rx = False

    def _sc_start_auto_baud_scan(self, reason="initial"):
        if self._serial_conn is None or not self._serial_conn.is_open:
            self._sc_append_system("[WARN] Cannot auto-detect: serial not connected", force_primary=True)
            return
        if self._sc_auto_baud_scan_thread is not None and self._sc_auto_baud_scan_thread.isRunning():
            return

        self._stop_serial_read()

        config = dict(AUTO_BAUD_CONFIG)
        worker = AutoBaudScanWorker(
            self._serial_conn, config, self._serial_baudrate
        )
        worker.set_recent_score_avg(self._sc_auto_baud_monitor.recent_score_avg)
        thread = QThread(self)
        worker.moveToThread(thread)

        if reason == "initial":
            thread.started.connect(worker.run_initial_scan)
        else:
            thread.started.connect(worker.run_runtime_rescan)

        worker.scan_finished.connect(self._sc_on_auto_baud_scan_finished)
        worker.scan_progress.connect(self._sc_on_auto_baud_progress)
        worker.state_changed.connect(self._sc_on_auto_baud_state_changed)
        worker.baudrate_changed.connect(self._sc_on_auto_baud_baudrate_changed)
        worker.scan_finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._sc_on_auto_baud_thread_cleanup)

        self._sc_auto_baud_scan_thread = thread
        self._sc_auto_baud_scan_worker = worker
        thread.start()

    def _sc_stop_auto_baud_scan(self):
        if self._sc_auto_baud_scan_worker is not None:
            self._sc_auto_baud_scan_worker.stop()
        if self._sc_auto_baud_scan_thread is not None and self._sc_auto_baud_scan_thread.isRunning():
            self._sc_auto_baud_scan_thread.quit()
            self._sc_auto_baud_scan_thread.wait(2000)
        self._sc_auto_baud_scan_thread = None
        self._sc_auto_baud_scan_worker = None

    def _sc_on_auto_baud_thread_cleanup(self):
        self._sc_auto_baud_scan_thread = None
        self._sc_auto_baud_scan_worker = None
        if self._serial_connected:
            self._start_serial_read()

    def _sc_on_auto_baud_scan_finished(self, result):
        if result.get("success"):
            baud = result["baudrate"]
            self._sc_auto_baud_monitor.state = AutoBaudState.LOCKED
            self._sc_auto_baud_monitor.reset()
            self._sc_auto_baud_monitor.mark_switch()
        else:
            reason = result.get("reason", "unknown")
            if reason == "no_baudrate_above_threshold":
                best = result.get("best")
                if best:
                    self._sc_append_system(
                        f"[WARN] No baudrate scored above threshold. Best: {best['baudrate']} score={best['score']}",
                        force_primary=True,
                    )
            self._sc_auto_baud_monitor.state = AutoBaudState.LOCKED
            self._sc_auto_baud_monitor.reset()

    def _sc_on_auto_baud_progress(self, msg):
        self._sc_append_system(msg, force_primary=True)

    def _sc_on_auto_baud_state_changed(self, state_str):
        self._sc_auto_baud_monitor.state = AutoBaudState(state_str)
        label = self._sc_status_autobaud_label
        if state_str == AutoBaudState.SCANNING.value:
            label.setText("AutoBaud: SCANNING")
            label.setStyleSheet(status_label_style("warn"))
        elif state_str == AutoBaudState.SUSPECT.value:
            label.setText("AutoBaud: SUSPECT")
            label.setStyleSheet(status_label_style("error"))
        elif state_str == AutoBaudState.LOCKED.value:
            label.setText("AutoBaud: LOCKED")
            label.setStyleSheet(status_label_style("accent"))
        else:
            label.setText(f"AutoBaud: {state_str}")
            label.setStyleSheet(status_label_style("muted"))

    def _sc_on_auto_baud_baudrate_changed(self, baudrate):
        self._serial_baudrate = baudrate
        self._sc_baud_combo.setCurrentText(str(baudrate))
        if hasattr(self, '_sc_status_baud_label'):
            self._sc_status_baud_label.setText(f"Baud rate (bps): {baudrate}")

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
            self._sc_append_system("[INFO] Mock port refreshed", force_primary=True)
            self._sc_try_restore_last_port()
            return
        try:
            ports = serial.tools.list_ports.comports()
            if ports:
                for p in ports:
                    self._sc_port_combo.addItem(f"{p.device} - {p.description}")
                self._sc_append_system(f"[INFO] Found {len(ports)} serial port(s)", force_primary=True)
            else:
                self._sc_port_combo.addItem("No serial ports found")
                self._sc_append_system("[WARN] No serial ports found", force_primary=True)
        except Exception as e:
            self._sc_append_system(f"[ERROR] Refresh failed: {e}", force_primary=True)
        self._sc_try_restore_last_port()

    def _sc_try_restore_last_port(self):
        last_port = getattr(self, "_sc_last_port", "")
        if not last_port:
            return
        for i in range(self._sc_port_combo.count()):
            if self._sc_port_combo.itemText(i).startswith(last_port.split(" - ")[0].split()[0]):
                self._sc_port_combo.setCurrentIndex(i)
                break
            if last_port in self._sc_port_combo.itemText(i):
                self._sc_port_combo.setCurrentIndex(i)
                break

