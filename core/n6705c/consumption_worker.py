# -*- coding: utf-8 -*-
"""
N6705C 消耗测试 Worker（仅依赖 QtCore，无 QtWidgets）。

从 ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py 平移而来，
行为零变更。
"""

from PySide6.QtCore import QObject, Signal


class ConsumptionTestWorker(QObject):
    channel_result = Signal(str, int, float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, n6705c, device_label, channels, test_time, sample_period):
        super().__init__()
        self.n6705c = n6705c
        self.device_label = device_label
        self.channels = channels
        self.test_time = test_time
        self.sample_period = sample_period
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            if self._is_stopped:
                self.finished.emit()
                return
            result = self.n6705c.fetch_current_by_datalog(
                self.channels, self.test_time, self.sample_period
            )
            for ch, avg_current in result.items():
                if self._is_stopped:
                    break
                self.channel_result.emit(self.device_label, ch, float(avg_current))
            self.finished.emit()
        except Exception as e:
            self.error.emit(f"[{self.device_label}] {e}")
            self.finished.emit()
