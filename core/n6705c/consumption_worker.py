# -*- coding: utf-8 -*-
"""
N6705C 消耗测试 Worker（仅依赖 QtCore，无 QtWidgets）。

从 ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py 平移而来，
行为零变更。
"""

from PySide6.QtCore import QObject, Signal

from core.consumption_test.workers.common import (
    require_channel_results,
    validate_datalog_timing,
)


class ConsumptionTestWorker(QObject):
    channel_result = Signal(str, int, float)
    finished = Signal(bool, str)
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
        success = False
        message = ""
        try:
            self.test_time, self.sample_period = validate_datalog_timing(
                self.test_time, self.sample_period
            )
            if not self.channels:
                raise ValueError("No consumption channels selected.")
            if not self._is_stopped:
                result = self.n6705c.fetch_current_by_datalog(
                    self.channels, self.test_time, self.sample_period
                )
                values = require_channel_results(result, self.channels, self.device_label)
            if self._is_stopped:
                message = f"[{self.device_label}] Consumption test stopped."
            else:
                for ch in self.channels:
                    self.channel_result.emit(self.device_label, ch, values[ch])
                success = True
                message = f"[{self.device_label}] Consumption test completed."
        except Exception as e:
            message = f"[{self.device_label}] {e}"
            self.error.emit(message)
        finally:
            self.finished.emit(success, message)
