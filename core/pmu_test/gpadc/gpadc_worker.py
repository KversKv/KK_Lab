# -*- coding: utf-8 -*-
"""
GPADC 测试 Worker（仅依赖 PySide6.QtCore，不依赖 QtWidgets）。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
"""

import threading
from collections.abc import Mapping
from types import MappingProxyType

from PySide6.QtCore import QObject, Signal


def freeze_config(value):
    """递归冻结测试配置，避免 worker 与 UI 共享可变 dict/list。"""
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_config(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_config(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_config(item) for item in value)
    return value


class TestWorker(QObject):
    finished = Signal(object)
    error = Signal(str)
    log = Signal(str)
    status = Signal(str, bool)
    progress = Signal(int)
    # 可恢复错误（如温箱串口瞬时中断）→ 请求 UI 弹窗让用户决定重试/中止
    confirm_request = Signal(str, str)

    def __init__(self, fn, kwargs):
        super().__init__()
        self._fn = fn
        self._kwargs = freeze_config(kwargs)
        self._stop_requested = False
        self._confirm_reply = threading.Event()
        self._confirm_continue = False

    def request_stop(self):
        self._stop_requested = True

    def is_stop_requested(self):
        return self._stop_requested

    def respond_confirm(self, continue_test):
        """UI 弹窗应答：是否重试。"""
        self._confirm_continue = bool(continue_test)
        self._confirm_reply.set()

    def wait_user_confirm(self, title, message):
        """请求 UI 弹窗确认并阻塞等待应答（期间可响应停止请求）。

        返回 (是否已应答, 是否重试)：等待期间用户停止时返回 (False, False)。
        """
        self._confirm_reply.clear()
        self._confirm_continue = False
        self.confirm_request.emit(title, message)
        while not self._confirm_reply.wait(0.1):
            if self._stop_requested:
                return False, False
        return True, self._confirm_continue

    def run(self):
        try:
            result = self._fn(stop_check=self.is_stop_requested, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
