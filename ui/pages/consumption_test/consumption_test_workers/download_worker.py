#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""固件下载 Worker。"""

from PySide6.QtCore import QObject, Signal

from lib.download_tools.download_script import download_bin, DownloadState
from log_config import get_logger

logger = get_logger(__name__)


class DownloadWorker(QObject):
    state_changed = Signal(str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, com_port, bin_file, mode, timeout=120):
        super().__init__()
        self.com_port = com_port
        self.bin_file = bin_file
        self.mode = mode
        self.timeout = timeout

    def run(self):
        try:
            logger.debug("DownloadWorker run: port=%s, bin=%s, mode=%s, timeout=%s",
                         self.com_port, self.bin_file, self.mode, self.timeout)

            def _on_state(state: DownloadState):
                self.state_changed.emit(state.value)

            result = download_bin(
                com_port=self.com_port,
                bin_file=self.bin_file,
                mode=self.mode,
                timeout=self.timeout,
                on_state_change=_on_state,
            )
            logger.debug("DownloadWorker finished: success=%s, state=%s",
                         result.success, result.state.value)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


__all__ = ["DownloadWorker"]
