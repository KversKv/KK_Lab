#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基础功耗测试 Worker(仅 datalog,不做 force)。"""

from PySide6.QtCore import QObject, Signal

from log_config import get_logger

logger = get_logger(__name__)


class ConsumptionTestWorker(QObject):
    channel_result = Signal(str, int, float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, device_channel_map, test_time, sample_period):
        super().__init__()
        self.device_channel_map = device_channel_map
        self.test_time = test_time
        self.sample_period = sample_period
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            logger.debug(
                "ConsumptionTestWorker run: test_time=%s, sample_period=%s, devices=%s",
                self.test_time, self.sample_period,
                list(self.device_channel_map.keys()),
            )
            if self._is_stopped:
                self.finished.emit()
                return
            for device_label, (n6705c_inst, hw_channels) in self.device_channel_map.items():
                if self._is_stopped:
                    break
                result = n6705c_inst.fetch_current_by_datalog(
                    hw_channels, self.test_time, self.sample_period
                )
                for ch, avg_current in result.items():
                    if self._is_stopped:
                        break
                    logger.debug(
                        "ConsumptionTestWorker result: %s CH%s = %.6e A",
                        device_label, ch, float(avg_current),
                    )
                    self.channel_result.emit(device_label, ch, float(avg_current))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


__all__ = ["ConsumptionTestWorker"]
