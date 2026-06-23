# -*- coding: utf-8 -*-
"""
Consumption Test 流程编排控制器（仅依赖 QtCore + lib + workers，无 QtWidgets）。

从 ui/pages/consumption_test/consumption_test.py 平移下载流程编排而来，
行为零变更：
  - start_download: 固件下载 Worker 生命周期管理（创建/连线/启动）
  - stop_download: 取消并回收下载线程

UI 仅负责收集输入（端口/固件路径/模式）并订阅控制器信号更新视图，
不再直接持有 QThread / Worker 引用。
"""

import os

from PySide6.QtCore import QObject, Signal, QThread

from lib.download_tools.download_script import detect_chip_from_bin
from log_config import get_logger
from core.consumption_test.workers.download_worker import DownloadWorker
from core.consumption_test.workers import _AutoTestWorker

logger = get_logger(__name__)


class ConsumptionController(QObject):
    log_message = Signal(str)
    download_started = Signal(int)
    download_state_changed = Signal(str)
    download_finished = Signal(object)
    download_error = Signal(str)
    download_cleaned = Signal()

    auto_test_channel_result = Signal(str, int, float, str)
    auto_test_summary = Signal(dict)
    auto_test_progress = Signal(float)
    auto_test_download_state = Signal(str)
    auto_test_finished = Signal()
    auto_test_error = Signal(str)
    auto_test_cleaned = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._download_thread = None
        self._download_worker = None
        self._auto_test_thread = None
        self._auto_test_worker = None

    def is_download_running(self):
        return self._download_thread is not None and self._download_thread.isRunning()

    def start_download(self, com_port, firmware_path, mode):
        if self.is_download_running():
            return

        logger.info("Downloading firmware to DUT: port=%s, file=%s, mode=%s",
                     com_port, firmware_path, mode.value)
        self.log_message.emit(
            f"[DOWNLOAD] Starting download: port={com_port}, "
            f"file={os.path.basename(firmware_path)}, mode={mode.value}"
        )

        chip = detect_chip_from_bin(firmware_path)
        if chip:
            logger.info("Detected chip model: %s", chip)
            self.log_message.emit(f"[DOWNLOAD] Detected chip model: {chip}")
        else:
            logger.warning("Could not detect chip model from firmware file")
            self.log_message.emit("[DOWNLOAD] Could not detect chip model from firmware file")

        try:
            file_size = os.path.getsize(firmware_path)
        except OSError:
            file_size = 0
        self.download_started.emit(file_size)

        worker = DownloadWorker(com_port, firmware_path, mode)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.state_changed.connect(self._on_worker_state_changed)
        worker.finished.connect(self._on_worker_finished)
        worker.error.connect(self._on_worker_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._on_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._download_thread = thread
        self._download_worker = worker
        thread.start()

    def stop_download(self):
        if self._download_worker is not None:
            try:
                from lib.download_tools.download_script import DldTool
                proc = getattr(self._download_worker, '_dld', None)
                if proc and hasattr(proc, 'cancel'):
                    proc.cancel()
            except Exception:
                pass
        if self._download_thread is not None and self._download_thread.isRunning():
            self._download_thread.quit()
            self._download_thread.wait(3000)

    def _on_worker_state_changed(self, state_value):
        logger.info("Download state: %s", state_value)
        self.log_message.emit(f"[DOWNLOAD] State: {state_value}")
        self.download_state_changed.emit(state_value)

    def _on_worker_finished(self, result):
        if result.success:
            logger.info("Download succeeded")
            self.log_message.emit("[DOWNLOAD] ✅ Download succeeded.")
        else:
            logger.error("Download failed: %s", result.error_message)
            self.log_message.emit(f"[ERROR] Download failed: {result.error_message}")
        self.download_finished.emit(result)

    def _on_worker_error(self, err_msg):
        logger.error("Download error: %s", err_msg)
        self.log_message.emit(f"[ERROR] Download error: {err_msg}")
        self.download_error.emit(err_msg)

    def _on_thread_cleaned(self):
        self._download_worker = None
        self._download_thread = None
        self.download_cleaned.emit()

    def is_auto_test_running(self):
        return self._auto_test_thread is not None and self._auto_test_thread.isRunning()

    def start_auto_test(self, worker_kwargs):
        if self.is_auto_test_running():
            return

        worker = _AutoTestWorker(**worker_kwargs)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.log_message)
        worker.channel_result.connect(self._on_auto_channel_result)
        worker.test_summary.connect(self._on_auto_test_summary)
        worker.progress.connect(self._on_auto_progress)
        worker.download_state_changed.connect(self._on_auto_download_state)
        worker.error.connect(self._on_auto_error)
        worker.finished.connect(self._on_auto_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_auto_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._auto_test_thread = thread
        self._auto_test_worker = worker
        thread.start()

    def stop_auto_test(self):
        if self._auto_test_worker is not None:
            try:
                self._auto_test_worker.stop()
            except Exception:
                logger.error("Failed to stop auto test worker", exc_info=True)
        if self._auto_test_thread is not None and self._auto_test_thread.isRunning():
            self._auto_test_thread.quit()
            self._auto_test_thread.wait(3000)

    def _on_auto_channel_result(self, device_label, hw_channel, avg_current, phase):
        self.auto_test_channel_result.emit(device_label, hw_channel, avg_current, phase)

    def _on_auto_test_summary(self, summary):
        self.auto_test_summary.emit(summary)

    def _on_auto_progress(self, value):
        self.auto_test_progress.emit(value)

    def _on_auto_download_state(self, state):
        self.log_message.emit(f"[AUTO_TEST] Download state: {state}")
        self.auto_test_download_state.emit(state)

    def _on_auto_error(self, err_msg):
        logger.error("Auto test error: %s", err_msg)
        self.log_message.emit(f"[AUTO_TEST] Error: {err_msg}")
        self.auto_test_error.emit(err_msg)

    def _on_auto_finished(self):
        logger.info("Auto test completed")
        self.log_message.emit("[AUTO_TEST] Auto test completed.")
        self.auto_test_finished.emit()

    def _on_auto_thread_cleaned(self):
        self._auto_test_worker = None
        self._auto_test_thread = None
        self.auto_test_cleaned.emit()


__all__ = ["ConsumptionController"]
