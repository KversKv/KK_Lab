"""异步任务注册表（AIAssist_TaskSchedulingResumePlan.md §4 / S1）。

长任务 / 异步动作发起后立即返回 `{status:"pending", task_id}`，由本注册表登记
`task_id -> PendingTask`。后台执行（QThread worker / QTimer / executor）完成后，
UI 层发 `task_finished(task_id, result)` 信号，触发 `AIService.resume_with_task_result()`
按 task_id 取回 session_key 定位归属会话并主动续跑一轮。

约束（守铁律）：
  - 绑定 `session_key` 防串台（§5.1 会话归属隔离）；
  - `resumed` 幂等标志保证同一结果只续跑一次（§5.3）；
  - 线程安全（worker 线程登记 / 完成，UI 线程读取）；
  - FIFO 上限避免内存无限增长（仿 draft_registry）；
  - 本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from log_config import get_logger

logger = get_logger(__name__)

_MAX_TASKS = 100

# 任务状态
STATUS_PENDING = "pending"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_CONSUMED = "consumed"


@dataclass
class PendingTask:
    """一个进行中 / 已完成异步任务的句柄（§4.3）。"""

    task_id: str
    session_key: str
    kind: str
    status: str = STATUS_PENDING
    created_at: str = ""
    result: Optional[dict] = None
    resumed: bool = False
    title: str = ""

    def to_summary(self) -> dict[str, Any]:
        """只读摘要（供 list_pending_tasks / TaskTray 展示）。"""
        return {
            "task_id": self.task_id,
            "session_key": self.session_key,
            "kind": self.kind,
            "status": self.status,
            "created_at": self.created_at,
            "resumed": self.resumed,
            "title": self.title,
        }


class PendingTaskRegistry:
    """异步任务句柄登记表（线程安全 + FIFO 上限）。"""

    def __init__(self, *, max_tasks: int = _MAX_TASKS) -> None:
        self._tasks: dict[str, PendingTask] = {}
        self._counter = 0
        self._max_tasks = max_tasks
        self._lock = threading.Lock()

    def register(
        self, session_key: str, kind: str, *, title: str = ""
    ) -> str:
        """登记一个 pending 任务，返回稳定 task_id。"""
        with self._lock:
            self._counter += 1
            task_id = f"T-{self._counter:04d}"
            self._tasks[task_id] = PendingTask(
                task_id=task_id,
                session_key=session_key or "",
                kind=kind or "",
                status=STATUS_PENDING,
                created_at=datetime.now().isoformat(timespec="seconds"),
                title=title or "",
            )
            self._evict_if_needed()
        logger.debug("登记异步任务 %s（kind=%s, session=%s）", task_id, kind, session_key)
        return task_id

    def mark_done(
        self, task_id: str, result: dict | None, *, ok: bool = True
    ) -> Optional[PendingTask]:
        """标记任务完成并写入结果，返回更新后的快照（任务不存在则 None）。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.status = STATUS_DONE if ok else STATUS_FAILED
            task.result = dict(result) if isinstance(result, dict) else {"value": result}
            return self._snapshot(task)

    def mark_resumed(self, task_id: str) -> bool:
        """幂等闸：首次置 resumed 返回 True，重复返回 False（§5.3）。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.resumed:
                return False
            task.resumed = True
            return True

    def mark_consumed(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is not None:
                task.status = STATUS_CONSUMED

    def get(self, task_id: str) -> Optional[PendingTask]:
        if not task_id:
            return None
        with self._lock:
            task = self._tasks.get(task_id)
            return self._snapshot(task) if task else None

    def list(self, *, session_key: str | None = None) -> list[dict[str, Any]]:
        """列出任务摘要；指定 session_key 时仅返回该会话名下任务（§5.1）。"""
        with self._lock:
            return [
                t.to_summary()
                for t in self._tasks.values()
                if session_key is None or t.session_key == session_key
            ]

    def list_unconsumed_done(self, session_key: str) -> list[dict[str, Any]]:
        """列出已完成但未回灌（resumed=False）的任务（§8.5 降级"未回灌"提示）。"""
        with self._lock:
            return [
                t.to_summary()
                for t in self._tasks.values()
                if t.session_key == session_key
                and t.status in (STATUS_DONE, STATUS_FAILED)
                and not t.resumed
            ]

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()
            self._counter = 0

    @staticmethod
    def _snapshot(task: PendingTask) -> PendingTask:
        return PendingTask(
            task_id=task.task_id,
            session_key=task.session_key,
            kind=task.kind,
            status=task.status,
            created_at=task.created_at,
            result=dict(task.result) if isinstance(task.result, dict) else task.result,
            resumed=task.resumed,
            title=task.title,
        )

    def _evict_if_needed(self) -> None:
        """超过上限时按 FIFO 淘汰最旧任务，避免内存无限增长。"""
        while len(self._tasks) > self._max_tasks:
            oldest = next(iter(self._tasks))
            self._tasks.pop(oldest, None)
