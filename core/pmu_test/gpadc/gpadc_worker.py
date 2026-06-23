# -*- coding: utf-8 -*-
"""
GPADC 测试 Worker（仅依赖 PySide6.QtCore，不依赖 QtWidgets）。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
"""

from PySide6.QtCore import QObject, Signal


class TestWorker(QObject):
    finished = Signal(object)
    error = Signal(str)
    log = Signal(str)
    progress = Signal(int)

    def __init__(self, fn, kwargs):
        super().__init__()
        self._fn = fn
        self._kwargs = kwargs
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def is_stop_requested(self):
        return self._stop_requested

    def run(self):
        try:
            result = self._fn(stop_check=self.is_stop_requested, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
