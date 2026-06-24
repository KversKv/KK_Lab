"""定时 / 延迟任务调度注册表（AI_Assistant_Plan.md §3 / S1）。

AI 经 `schedule_action` 把「触发器 + 目标动作」编译成一份计划，登记进本注册表后
本轮立即结束（0 token 等待）。UI 层 `QTimer` 到点回调 → 经 `ActionDispatcher`
执行已登记的目标动作 → 完成后发 `task_finished` 经 §4 回灌 AI（可选）。

约束（守铁律）：
  - `action` 必须是注册表中已存在的受控动作名 + 参数（登记时校验，§3.3）；
  - 到点执行仍走 dispatcher 风险 / 确认 / 审计闭环（§5.6），除非显式 pre_authorized；
  - 绑定 `session_key`（回灌定位用，§5.1）；
  - 线程安全 + FIFO 上限（仿 draft_registry）；
  - 本模块纯逻辑，禁 import Qt。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from log_config import get_logger

logger = get_logger(__name__)

_MAX_TASKS = 100

# 任务状态
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """一个定时 / 延迟调度任务（§3.2）。"""

    task_id: str
    session_key: str
    trigger: dict
    action: dict
    status: str = STATUS_PENDING
    created_at: str = ""
    fire_at: str = ""
    pre_authorized: bool = False
    result: Optional[dict] = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "session_key": self.session_key,
            "trigger": dict(self.trigger),
            "action": {"name": self.action.get("name", "")},
            "status": self.status,
            "created_at": self.created_at,
            "fire_at": self.fire_at,
            "pre_authorized": self.pre_authorized,
        }


def _compute_fire_at(trigger: dict, now: datetime | None = None) -> tuple[Optional[datetime], str]:
    """根据触发器计算触发时刻；返回 (fire_at_datetime | None, error)。"""
    now = now or datetime.now()
    ttype = str((trigger or {}).get("type", "")).strip().lower()
    if ttype == "delay":
        seconds = trigger.get("seconds")
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            return None, "delay 触发器缺少有效的 seconds。"
        if seconds < 0:
            return None, "delay 的 seconds 不能为负。"
        return now + timedelta(seconds=seconds), ""
    if ttype == "at":
        iso = str(trigger.get("iso", "")).strip()
        try:
            fire = datetime.fromisoformat(iso)
        except (TypeError, ValueError):
            return None, "at 触发器缺少有效的 iso 时间字符串。"
        return fire, ""
    return None, f"不支持的触发器类型：{ttype or '(空)'}"


class ScheduledTaskRegistry:
    """调度任务登记表（线程安全 + FIFO 上限）。"""

    def __init__(self, *, max_tasks: int = _MAX_TASKS) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._counter = 0
        self._max_tasks = max_tasks
        self._lock = threading.Lock()

    def register(
        self,
        session_key: str,
        trigger: dict,
        action: dict,
        *,
        pre_authorized: bool = False,
    ) -> tuple[Optional[str], Optional[float], str]:
        """登记一个调度任务。

        返回 (task_id, delay_seconds, error)：
          - 成功：task_id + 距触发的秒数（供 UI 起 QTimer），error 为空；
          - 失败：(None, None, error)。
        """
        fire_at, err = _compute_fire_at(trigger)
        if err:
            return None, None, err
        now = datetime.now()
        delay_seconds = max(0.0, (fire_at - now).total_seconds())
        with self._lock:
            self._counter += 1
            task_id = f"sched_{self._counter:03d}"
            self._tasks[task_id] = ScheduledTask(
                task_id=task_id,
                session_key=session_key or "",
                trigger=dict(trigger),
                action=dict(action),
                status=STATUS_PENDING,
                created_at=now.isoformat(timespec="seconds"),
                fire_at=fire_at.isoformat(timespec="seconds"),
                pre_authorized=bool(pre_authorized),
            )
            self._evict_if_needed()
        logger.debug(
            "登记调度任务 %s（fire_at=%s, action=%s）",
            task_id,
            fire_at.isoformat(timespec="seconds"),
            action.get("name", ""),
        )
        return task_id, delay_seconds, ""

    def mark_running(self, task_id: str) -> Optional[ScheduledTask]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status != STATUS_PENDING:
                return None
            task.status = STATUS_RUNNING
            return self._snapshot(task)

    def mark_done(
        self, task_id: str, result: dict | None, *, ok: bool = True
    ) -> Optional[ScheduledTask]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.status = STATUS_DONE if ok else STATUS_FAILED
            task.result = dict(result) if isinstance(result, dict) else {"value": result}
            return self._snapshot(task)

    def cancel(self, task_id: str) -> tuple[bool, str]:
        """取消一个未触发的调度任务。"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False, f"调度任务不存在：{task_id}"
            if task.status != STATUS_PENDING:
                return False, f"任务 {task_id} 当前状态为 {task.status}，无法取消。"
            task.status = STATUS_CANCELLED
            return True, f"已取消调度任务 {task_id}。"

    def get(self, task_id: str) -> Optional[ScheduledTask]:
        if not task_id:
            return None
        with self._lock:
            task = self._tasks.get(task_id)
            return self._snapshot(task) if task else None

    def list(self, *, session_key: str | None = None) -> list[dict[str, Any]]:
        """列出调度任务摘要；指定 session_key 时仅返回该会话名下任务（§5.1）。"""
        with self._lock:
            return [
                t.to_summary()
                for t in self._tasks.values()
                if session_key is None or t.session_key == session_key
            ]

    def list_pending(self, *, session_key: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            return [
                t.to_summary()
                for t in self._tasks.values()
                if t.status == STATUS_PENDING
                and (session_key is None or t.session_key == session_key)
            ]

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()
            self._counter = 0

    @staticmethod
    def _snapshot(task: ScheduledTask) -> ScheduledTask:
        return ScheduledTask(
            task_id=task.task_id,
            session_key=task.session_key,
            trigger=dict(task.trigger),
            action=dict(task.action),
            status=task.status,
            created_at=task.created_at,
            fire_at=task.fire_at,
            pre_authorized=task.pre_authorized,
            result=dict(task.result) if isinstance(task.result, dict) else task.result,
        )

    def _evict_if_needed(self) -> None:
        while len(self._tasks) > self._max_tasks:
            oldest = next(iter(self._tasks))
            self._tasks.pop(oldest, None)
