"""调度类动作 handlers（AI_Assistant_Plan.md §3 / S4）。

schedule_action     : high，登记「延迟/定时 + 目标动作」到 ScheduledTaskRegistry，
                      返回 task_id；不立即执行（Plan-then-Execute，§3.1）。
list_scheduled_tasks: low，列出待执行 / 历史调度任务摘要。
cancel_scheduled_task: medium，取消一个未触发的调度任务。

约束：
  - 目标 action.name 必须已注册（登记即校验，§3.3）；
  - 登记成功后经 UI 注入的 schedule_register_callback 起 QTimer（到点执行）；
  - 到点执行仍走 dispatcher 风险/确认/审计（§5.6），pre_authorized 仅非 critical。
  本模块禁 import Qt。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_SCHEDULE, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

# 登记时即拒绝的高危目标动作（pre_authorized 仅允许非 critical，§5.6）
_PRE_AUTH_FORBIDDEN_RISK = "critical"

_TRIGGER_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["delay", "at"]},
        "seconds": {
            "type": "number",
            "minimum": 0,
            "description": "type=delay 时：延迟秒数。",
        },
        "iso": {
            "type": "string",
            "description": "type=at 时：ISO 8601 触发时刻，如 2026-06-24T15:30:00。",
        },
    },
    "required": ["type"],
}

_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "已注册的受控动作名。"},
        "arguments": {"type": "object", "description": "目标动作的参数。"},
    },
    "required": ["name"],
}

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="schedule_action",
        description=(
            "登记一个定时/延迟任务：到点后自动执行指定的受控动作。"
            "trigger 支持 delay（N 秒后）或 at（指定时刻）；action 为已注册动作名+参数。"
            "本动作只登记不立即执行，返回 task_id。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "trigger": _TRIGGER_SCHEMA,
                "action": _ACTION_SCHEMA,
                "pre_authorized": {
                    "type": "boolean",
                    "description": (
                        "登记时一次性授权、到点免确认（仅允许非 critical 动作）。"
                        "默认 false：到点仍走目标动作自身的风险确认。"
                    ),
                },
            },
            "required": ["trigger", "action"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_SCHEDULE,
    ),
    ActionSpec(
        name="list_scheduled_tasks",
        description="列出当前会话待执行 / 历史调度任务摘要。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_SCHEDULE,
    ),
    ActionSpec(
        name="cancel_scheduled_task",
        description="取消一个尚未触发的调度任务。",
        parameters_schema={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
        risk_level="medium",
        require_confirmation=True,
        category=CATEGORY_SCHEDULE,
    ),
]


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def _session_key() -> str:
        if deps.session_key_getter is not None:
            try:
                return deps.session_key_getter() or ""
            except Exception:  # noqa: BLE001
                logger.error("session_key_getter 调用异常", exc_info=True)
        return ""

    def schedule_action(args: dict) -> dict:
        registry = deps.scheduled_task_registry
        if registry is None:
            return {"ok": False, "_message": "当前环境不支持任务调度。"}
        if deps.schedule_register_callback is None:
            return {"ok": False, "_message": "当前环境无法启动定时触发器。"}

        trigger = args.get("trigger") or {}
        action = args.get("action") or {}
        action_name = str(action.get("name", "")).strip()
        if not action_name:
            return {"ok": False, "_message": "缺少目标动作名（action.name）。"}

        # 登记即校验：目标动作必须已注册（§3.3）
        validator = deps.action_name_validator
        if validator is not None and not validator(action_name):
            return {"ok": False, "_message": f"目标动作未注册：{action_name}"}

        pre_authorized = bool(args.get("pre_authorized", False))

        task_id, delay_seconds, err = registry.register(
            _session_key(), trigger, action, pre_authorized=pre_authorized
        )
        if err or task_id is None:
            return {"ok": False, "_message": err or "登记调度任务失败。"}

        ok, msg = deps.schedule_register_callback(task_id, float(delay_seconds or 0.0))
        if not ok:
            # 起 QTimer 失败：取消已登记任务，避免悬挂
            registry.cancel(task_id)
            return {"ok": False, "_message": msg or "启动定时触发器失败。"}

        return {
            "ok": True,
            "task_id": task_id,
            "fire_in_seconds": round(float(delay_seconds or 0.0), 1),
            "action": action_name,
            "_message": (
                f"已登记调度任务 {task_id}：约 {round(float(delay_seconds or 0.0))} 秒后"
                f"执行 {action_name}。"
            ),
        }

    def list_scheduled_tasks(_args: dict) -> dict:
        registry = deps.scheduled_task_registry
        if registry is None:
            return {"ok": False, "_message": "当前环境不支持任务调度。"}
        tasks = registry.list(session_key=_session_key() or None)
        return {
            "ok": True,
            "count": len(tasks),
            "tasks": tasks,
            "_message": f"当前共有 {len(tasks)} 个调度任务。",
        }

    def cancel_scheduled_task(args: dict) -> dict:
        registry = deps.scheduled_task_registry
        if registry is None:
            return {"ok": False, "_message": "当前环境不支持任务调度。"}
        task_id = str(args.get("task_id", "")).strip()
        if not task_id:
            return {"ok": False, "_message": "缺少 task_id。"}
        ok, msg = registry.cancel(task_id)
        return {"ok": bool(ok), "_message": msg}

    return {
        "schedule_action": schedule_action,
        "list_scheduled_tasks": list_scheduled_tasks,
        "cancel_scheduled_task": cancel_scheduled_task,
    }
