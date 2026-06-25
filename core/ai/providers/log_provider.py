"""LogContextProvider：把软件运行日志 + 当前页执行日志翻译成上下文文本。

来源（AIAssist_Architecture.md §11）：
  - 软件运行日志：log_ring 环形缓冲（挂 root logger）；
  - 执行日志：当前页 ExecutionLogsFrame 缓存，经 UI 注入的 execution_logs_getter 回调读取。

本类不直接 import ui / Qt，保持 core 不反向依赖 ui：
  执行日志通过轻量 Callable[[], list[str]] 注入。
"""
from __future__ import annotations

from typing import Callable

from core.ai.log_ring import get_log_ring
from core.ai.providers.base import ContextProvider
from log_config import get_logger

logger = get_logger(__name__)

ExecutionLogsGetter = Callable[[], list[str]]


class LogContextProvider(ContextProvider):
    def __init__(
        self,
        max_app_lines: int = 300,
        max_exec_lines: int = 200,
        execution_logs_getter: ExecutionLogsGetter | None = None,
    ):
        self._max_app = max_app_lines
        self._max_exec = max_exec_lines
        self._exec_getter = execution_logs_getter

    def name(self) -> str:
        return "log"

    def set_limits(self, max_app_lines: int, max_exec_lines: int) -> None:
        self._max_app = max(0, int(max_app_lines))
        self._max_exec = max(0, int(max_exec_lines))

    def recent_app_logs(self, lines: int | None = None) -> list[str]:
        ring = get_log_ring()
        if ring is None:
            return []
        return ring.recent(lines if lines is not None else self._max_app)

    def recent_execution_logs(self, lines: int | None = None) -> list[str]:
        if self._exec_getter is None:
            return []
        try:
            logs = self._exec_getter() or []
        except Exception:  # noqa: BLE001 - 取执行日志失败不应影响上下文构建
            logger.warning("读取执行日志失败", exc_info=True)
            return []
        limit = lines if lines is not None else self._max_exec
        if limit <= 0:
            return []
        return [str(x) for x in logs][-limit:]

    def build_context(self, page_key: str | None) -> str:
        parts: list[str] = []
        app_logs = self.recent_app_logs()
        if app_logs:
            parts.append(
                "[最近软件运行日志 %d 行]\n%s" % (len(app_logs), "\n".join(app_logs))
            )
        exec_logs = self.recent_execution_logs()
        if exec_logs:
            parts.append(
                "[当前页执行日志 %d 行]\n%s" % (len(exec_logs), "\n".join(exec_logs))
            )
        return "\n\n".join(parts)
