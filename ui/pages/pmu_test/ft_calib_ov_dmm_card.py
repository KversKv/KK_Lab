#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Output Voltage Check 页内私有 DMM（Keysight 34461A）连接卡。

34461A 构造即连接（无 connect()/is_connected()），连接/断开必须走后台
Worker；VISA 扫描经 core.instruments.visa_scan（UI 禁 import pyvisa）。
当前唯一真实消费者为本子页，暂不抽 ui/modules Mixin。
"""

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
)

from core.instruments.address_presets import get_address_preset
from debug_config import DEBUG_MOCK
from log_config import get_logger
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from ui.widgets.dark_combobox import DarkComboBox

_logger = get_logger(__name__)

_MOCK_RESOURCE = "[MOCK] USB0::DMM::INSTR"
_ROW_HEIGHT = 26


class _DmmTaskWorker(QObject):
    """通用后台任务 Worker：连接/断开等阻塞 VISA 操作统一异步执行。"""

    finished = Signal(dict)

    def __init__(self, task, **kwargs):
        super().__init__()
        self._task = task
        self._kwargs = kwargs

    def run(self):
        try:
            payload = self._task(**self._kwargs) or {}
            payload["ok"] = True
            self.finished.emit(payload)
        except Exception as e:  # noqa: BLE001 - 任务异常转可读结果
            _logger.error("DMM task failed", exc_info=True)
            self.finished.emit({"ok": False, "error": str(e)})


def _connect_task(resource):
    from instruments.factory import create_digital_multimeter
    instrument = create_digital_multimeter("34461a", resource)
    idn = instrument.identify()
    return {"instrument": instrument, "idn": idn}


def _disconnect_task(instrument):
    instrument.disconnect()
    return {}


class DmmConnectionCard(QWidget):
    """DMM 连接卡：资源扫描/手填 + 异步连接/断开 + 状态指示。"""

    connection_changed = Signal(bool)
    log_message = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dmm = None
        self.is_connected = False
        self._scan_thread = None
        self._scan_worker = None
        self._task_thread = None
        self._task_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("Keysight 34461A (DMM)")
        title.setObjectName("cardTitle")
        title_row.addWidget(title)
        title_row.addStretch(1)
        self.status_label = QLabel("● Disconnected")
        self.status_label.setObjectName("statusOk")
        title_row.addWidget(self.status_label)
        layout.addLayout(title_row)

        self.resource_combo = DarkComboBox()
        self.resource_combo.setEditable(True)
        self.resource_combo.setFixedHeight(_ROW_HEIGHT)
        preset = get_address_preset("digital_multimeter", "keysight_34461a")
        if preset:
            self.resource_combo.addItem(preset)
        layout.addWidget(self.resource_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.search_btn = SpinningSearchButton()
        self.search_btn.setFixedHeight(_ROW_HEIGHT)
        self.connect_btn = QPushButton()
        self.connect_btn.setFixedHeight(_ROW_HEIGHT)
        update_connect_button_state(self.connect_btn, connected=False)
        btn_row.addWidget(self.search_btn)
        btn_row.addWidget(self.connect_btn, 1)
        layout.addLayout(btn_row)

        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)

    # ------------------------------------------------------------------
    # 扫描
    # ------------------------------------------------------------------

    def _on_search(self):
        if self._scan_thread is not None:
            return
        if DEBUG_MOCK:
            self._fill_resources([_MOCK_RESOURCE])
            self.log_message.emit("[DMM] Mock resource filled (DEBUG_MOCK).")
            return
        from core.instruments.visa_scan import VisaIdnScanWorker
        self.search_btn.start_spinning()
        self.search_btn.setEnabled(False)
        thread = QThread(self)
        worker = VisaIdnScanWorker(("34461", "34460", "MULTIMETER"))
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scan_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_scan_thread_finished)
        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    def _on_scan_finished(self, resources):
        self._fill_resources(list(resources))
        if resources:
            self.log_message.emit(f"[DMM] Scan found {len(resources)} resource(s).")
        else:
            self.log_message.emit("[DMM] Scan found no matching resource.")

    def _on_scan_thread_finished(self):
        self.search_btn.stop_spinning()
        self.search_btn.setEnabled(True)
        self._scan_thread = None
        self._scan_worker = None

    def _fill_resources(self, resources):
        current = self.resource_combo.currentText().strip()
        self.resource_combo.clear()
        for res in resources:
            self.resource_combo.addItem(res)
        if current:
            idx = self.resource_combo.findText(current)
            if idx >= 0:
                self.resource_combo.setCurrentIndex(idx)
            else:
                self.resource_combo.setCurrentText(current)

    # ------------------------------------------------------------------
    # 连接 / 断开
    # ------------------------------------------------------------------

    def _on_connect_or_disconnect(self):
        if self._task_thread is not None:
            return
        if self.is_connected:
            self._start_task(_disconnect_task, instrument=self.dmm)
            return
        resource = self.resource_combo.currentText().strip()
        if not resource and not DEBUG_MOCK:
            self.log_message.emit("[ERROR] DMM VISA resource is empty.")
            return
        self.connect_btn.setEnabled(False)
        self.status_label.setText("● Connecting...")
        self.status_label.setObjectName("statusWarn")
        self._repolish_status()
        self._start_task(_connect_task, resource=resource)

    def _start_task(self, task, **kwargs):
        thread = QThread(self)
        worker = _DmmTaskWorker(task, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_task_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_task_thread_finished)
        self._task_thread = thread
        self._task_worker = worker
        thread.start()

    def _on_task_finished(self, payload):
        if not payload.get("ok"):
            self.log_message.emit(f"[ERROR] DMM operation failed: {payload.get('error')}")
            self._set_connected(False)
            return
        if "instrument" in payload:
            self.dmm = payload["instrument"]
            self._set_connected(True)
            self.log_message.emit(f"[DMM] Connected: {payload.get('idn', '')}")
        else:
            self.dmm = None
            self._set_connected(False)
            self.log_message.emit("[DMM] Disconnected.")

    def _on_task_thread_finished(self):
        self.connect_btn.setEnabled(True)
        self._task_thread = None
        self._task_worker = None

    def _set_connected(self, connected):
        self.is_connected = connected
        update_connect_button_state(self.connect_btn, connected)
        if connected:
            self.status_label.setText("● Connected")
            self.status_label.setObjectName("statusOk")
        else:
            self.status_label.setText("● Disconnected")
            self.status_label.setObjectName("statusErr")
        self._repolish_status()
        self.connection_changed.emit(connected)

    def _repolish_status(self):
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    # ------------------------------------------------------------------
    # 页面协作
    # ------------------------------------------------------------------

    def set_busy(self, busy):
        """测试运行中锁定连接卡。"""
        self.resource_combo.setEnabled(not busy)
        self.search_btn.setEnabled(not busy and self._scan_thread is None)
        self.connect_btn.setEnabled(not busy and self._task_thread is None)

    def resource_text(self):
        return self.resource_combo.currentText().strip()

    def set_resource_text(self, text):
        if not text:
            return
        idx = self.resource_combo.findText(str(text))
        if idx >= 0:
            self.resource_combo.setCurrentIndex(idx)
        else:
            self.resource_combo.setCurrentText(str(text))

    def cleanup_threads(self):
        for thread in (self._scan_thread, self._task_thread):
            if thread is not None:
                thread.quit()
        self._scan_thread = None
        self._scan_worker = None
        self._task_thread = None
        self._task_worker = None
        if self.dmm is not None:
            try:
                self.dmm.disconnect()
            except Exception:  # noqa: BLE001 - 关闭清理不阻断
                _logger.error("DMM disconnect on cleanup failed", exc_info=True)
            self.dmm = None
            self.is_connected = False
