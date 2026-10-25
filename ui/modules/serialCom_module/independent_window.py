# -*- coding: utf-8 -*-
"""_IndependentSerialWindow — 独立串口浮窗（原 serialCom_module_frame.py 拆出）。"""

import os
import re

from datetime import datetime
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import (
    QThread,
    Qt,
    Signal,
)
from debug_config import DEBUG_MOCK
from log_config import get_logger
from core.serial_io import SerialReadWorker as _SerialReadWorker
from core.serial_io.serial_backend import open_serial
from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel
from ui.modules.serialCom_module.serial_style import (
    _CLR_BG_LOG,
    _CLR_CONNECT_FG,
    _CLR_INPUT_TEXT,
    _CLR_TEXT_MUTED,
    filter_input_style,
)
from ui.modules.serialCom_module.dialogs.save_dialog import _SerialSaveDialog

logger = get_logger(__name__)

class _IndependentSerialWindow(QWidget):

    connection_changed = Signal()

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._conn = None
        self._read_thread = None
        self._read_worker = None

        title = config.get("title", "Serial Log")
        self.setWindowTitle(f"Serial Console - {title}")
        self.setMinimumSize(600, 400)
        self.resize(750, 500)
        self.setStyleSheet(f"background-color: {_CLR_BG_LOG}; color: {_CLR_INPUT_TEXT};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        # 统一日志面板（full 过滤 + Save + RX/TX 状态栏 + Copy/Export 通知）
        self._panel = SerialLogPanel(
            title=title,
            filter_mode="full",
            show_title=False,
            show_save_button=True,
            status_bar="rxtx",
            max_lines=5000,
            notify_on_copy_export=True,
        )
        self._save_handle = None
        self._save_path = None
        self._save_keep_timestamp = True
        self._panel.save_toggled.connect(self._on_save_toggle)
        self._panel.raw_appended.connect(self._write_save_line)

        port_text = config.get("port", "N/A")
        baud_text = str(config.get("baudrate", "N/A"))
        self._status_label = QLabel(f"{port_text} @ {baud_text}")
        self._status_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 12px;")
        self._panel.add_toolbar_leading(self._status_label)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setCursor(Qt.PointingHandCursor)
        self._connect_btn.clicked.connect(self._toggle_connect)
        self._panel.add_toolbar_leading(self._connect_btn)

        root.addWidget(self._panel, 1)

        send_row = QHBoxLayout()
        send_row.setSpacing(4)
        self._send_input = QLineEdit()
        self._send_input.setPlaceholderText("Enter command...")
        self._send_input.setStyleSheet(filter_input_style())
        self._send_input.returnPressed.connect(self._on_send)
        send_row.addWidget(self._send_input, 1)
        send_btn = QPushButton("Send")
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.clicked.connect(self._on_send)
        send_row.addWidget(send_btn)
        root.addLayout(send_row)

        if config.get("auto_connect", False):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, self, self._do_connect)

    def _toggle_connect(self):
        if DEBUG_MOCK and self._connect_btn.text() == "Disconnect":
            self._do_disconnect()
        elif self._conn is not None and self._conn.is_open:
            self._do_disconnect()
        else:
            self._do_connect()

    def is_connected(self) -> bool:
        if DEBUG_MOCK:
            return self._connect_btn.text() == "Disconnect"
        return self._conn is not None and self._conn.is_open

    def clear_logs(self):
        """供 Clear All 统一调用：清空本浮窗日志面板。"""
        self._panel.clear_logs()

    def _do_connect(self):
        port = self._config.get("port", "")
        baudrate = self._config.get("baudrate", 115200)
        if not port:
            self._panel.append_log("[ERROR] No port configured")
            return

        if DEBUG_MOCK:
            self._conn = None
            self._connect_btn.setText("Disconnect")
            self._status_label.setText(f"MOCK @ {baudrate}")
            self._status_label.setStyleSheet(f"color: {_CLR_CONNECT_FG}; font-size: 12px;")
            self._panel.append_log(f"[INFO] Mock connected: {port} @ {baudrate}")
            self.connection_changed.emit()
            return

        try:
            databit = int(self._config.get("databit", 8))
            flow = self._config.get("flow", "None")
            conn = open_serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=str(self._config.get("stopbit", "1")),
                parity=self._config.get("parity", "None"),
                xonxoff=(flow == "XON/XOFF"), rtscts=(flow == "RTS/CTS"),
                timeout=0.1,
            )
            self._conn = conn
            self._connect_btn.setText("Disconnect")
            self._status_label.setText(f"{port} @ {baudrate}")
            self._status_label.setStyleSheet(f"color: {_CLR_CONNECT_FG}; font-size: 12px;")
            self._panel.append_log(f"[INFO] Connected: {port} @ {baudrate}")
            self._start_read()
            self.connection_changed.emit()
        except Exception as e:
            self._panel.append_log(f"[ERROR] Connection failed: {e}")

    def _do_disconnect(self):
        self._stop_read()
        try:
            if self._conn is not None and self._conn.is_open:
                self._conn.close()
        except Exception:
            pass
        self._conn = None
        self._connect_btn.setText("Connect")
        self._status_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 12px;")
        self._panel.append_log("[INFO] Disconnected")
        self.connection_changed.emit()

    def disconnect_on_port_removed(self, port: str) -> bool:
        """热插拔移除当前连接端口时自动断开；返回是否真正触发了断开。"""
        if self._config.get("port") != port or not self.is_connected():
            return False
        self._panel.append_log(f"[WARN] Port {port} removed, auto disconnected")
        self._do_disconnect()
        return True

    def _on_send(self):
        text = self._send_input.text()
        if not text:
            return
        data = (text + "\r\n").encode("utf-8")

        if DEBUG_MOCK:
            self._panel.add_tx_bytes(len(data))
            self._panel.append_log(f"[TX] {text}")
            self._send_input.clear()
            return

        if self._conn is None or not self._conn.is_open:
            self._panel.append_log("[ERROR] Not connected")
            return
        try:
            self._conn.write(data)
            self._panel.add_tx_bytes(len(data))
            self._panel.append_log(f"[TX] {text}")
            self._send_input.clear()
        except Exception as e:
            self._panel.append_log(f"[ERROR] Send failed: {e}")

    def _start_read(self):
        if self._conn is None:
            return
        worker = _SerialReadWorker(self._conn)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.data_received.connect(self._on_data_received)
        worker.error.connect(lambda err: self._panel.append_log(f"[ERROR] {err}"))
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        self._read_thread = thread
        self._read_worker = worker
        thread.start()

    def _stop_read(self):
        if self._read_worker:
            self._read_worker.stop()
        if self._read_thread and self._read_thread.isRunning():
            self._read_thread.quit()
            self._read_thread.wait(3000)
        self._read_thread = None
        self._read_worker = None

    def _on_data_received(self, data: bytes):
        self._panel.append_rx_data(data)

    # --- 保存到文件（与主面板语义一致：先写已有缓冲，再持续追加） ---

    @staticmethod
    def _strip_timestamp(raw: str) -> str:
        return re.sub(r'^\d{2}:\d{2}:\d{2}\.\d{3}\s', '', raw)

    def _on_save_toggle(self, checked: bool):
        if checked:
            if not self._start_save():
                btn = self._panel.save_btn
                if btn is not None:
                    btn.setChecked(False)
        else:
            self._stop_save()

    def _start_save(self) -> bool:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        title_safe = re.sub(r'[^\w\-.]', '_', str(self._config.get("title", "") or "window"))
        dlg = _SerialSaveDialog(
            self,
            default_dir="",
            default_name=f"serial_log_{title_safe}_{ts}.txt",
            keep_timestamp=self._save_keep_timestamp,
        )
        if dlg.exec() != QDialog.Accepted:
            return False
        cfg = dlg.get_config()
        save_dir = cfg["directory"]
        name = cfg["name"]
        keep_ts = cfg["keep_timestamp"]
        if not name:
            name = f"serial_log_{title_safe}_{ts}.txt"
        if not name.lower().endswith(".txt"):
            name += ".txt"
        if not save_dir:
            self._panel.append_log("[ERROR] Save: no directory selected")
            return False
        try:
            os.makedirs(save_dir, exist_ok=True)
        except OSError as exc:
            logger.error("Save: cannot create directory %s", save_dir, exc_info=True)
            QMessageBox.warning(self, "Save", f"Cannot create directory:\n{exc}")
            return False
        file_path = os.path.join(save_dir, name)
        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "Save",
                f"File already exists:\n{file_path}\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return False
        try:
            handle = open(file_path, "w", encoding="utf-8")
        except OSError as exc:
            logger.error("Save: cannot open file %s", file_path, exc_info=True)
            QMessageBox.warning(self, "Save", f"Cannot open file:\n{exc}")
            return False

        self._save_keep_timestamp = keep_ts
        try:
            for raw, _html, _no in self._panel.all_logs:
                out = raw if keep_ts else self._strip_timestamp(raw)
                handle.write(out + "\n")
            handle.flush()
        except OSError:
            logger.error("Save: failed writing buffer to %s", file_path, exc_info=True)
            try:
                handle.close()
            except OSError:
                pass
            QMessageBox.warning(self, "Save", "Failed to write existing buffer.")
            return False

        self._save_handle = handle
        self._save_path = file_path
        self._panel.append_log(f"[INFO] Save started: {file_path}")
        return True

    def _stop_save(self):
        if self._save_handle is None:
            return
        try:
            self._save_handle.flush()
            self._save_handle.close()
        except OSError:
            pass
        self._save_handle = None
        if self._save_path:
            self._panel.append_log(f"[INFO] Save stopped: {self._save_path}")
        self._save_path = None
        btn = self._panel.save_btn
        if btn is not None and btn.isChecked():
            btn.setChecked(False)

    def _write_save_line(self, raw: str):
        if self._save_handle is None:
            return
        line = raw if self._save_keep_timestamp else self._strip_timestamp(raw)
        try:
            self._save_handle.write(line + "\n")
            self._save_handle.flush()
        except OSError:
            try:
                self._save_handle.close()
            except OSError:
                pass
            self._save_handle = None
            self._save_path = None
            btn = self._panel.save_btn
            if btn is not None:
                btn.setChecked(False)

    def closeEvent(self, event):
        self._stop_save()
        self._do_disconnect()
        super().closeEvent(event)
