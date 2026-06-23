# -*- coding: utf-8 -*-
"""
N6705C 通道同步 Worker（仅依赖 QtCore，无 QtWidgets）。

从 ui/pages/n6705c_power_analyzer/n6705c_analyser_ui.py 平移而来，
行为零变更。
"""

from PySide6.QtCore import QObject, Signal


class ChannelSyncWorker(QObject):
    result = Signal(dict)
    finished = Signal()

    def __init__(self, n6705c, channel_num):
        super().__init__()
        self.n6705c = n6705c
        self.channel_num = channel_num

    def run(self):
        data = {}
        try:
            data["channel_state"] = self.n6705c.get_channel_state(self.channel_num)
        except Exception:
            data["channel_state"] = None
        try:
            data["mode"] = self.n6705c.get_mode(self.channel_num)
        except Exception:
            data["mode"] = None
        try:
            data["voltage"] = float(self.n6705c.measure_voltage(self.channel_num))
        except Exception:
            data["voltage"] = None
        try:
            data["current"] = float(self.n6705c.measure_current(self.channel_num))
        except Exception:
            data["current"] = None
        try:
            data["limit_current"] = float(self.n6705c.get_current_limit(self.channel_num))
        except Exception:
            data["limit_current"] = None
        self.result.emit(data)
        self.finished.emit()
