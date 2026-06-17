"""ActionDispatcher：按动作 name 路由到 handler 并执行（AI_Assist.md §8 / §10）。

职责：
  - 持有 ActionRegistry / PermissionChecker / AuditLog；
  - 注册 name -> handler 可调用（handler(arguments: dict) -> dict）；
  - 执行前：校验动作存在、参数过 JSON Schema 子集校验、过权限判定；
  - 需确认的动作：由 dispatcher 调用注入的 confirm_callback（UI 弹窗）；
  - 执行后：写审计（含拒绝/取消/失败）。

本模块禁 import Qt。confirm_callback 由 UI 注入（线程在调用方负责，dispatcher 同步执行）。
handler 内部只能调已注入的受控操作（UI/串口/仪器/测试回调），不可执行任意代码。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from core.ai.actions.audit import (
    STATUS_CANCELLED,
    STATUS_DENIED,
    STATUS_EXECUTED,
    STATUS_FAILED,
    AuditLog,
    get_audit_log,
)
from core.ai.actions.permission import PermissionChecker
from core.ai.actions.registry import ActionRegistry, ActionSpec
from core.ai.response_parser import validate_against_schema
from log_config import get_logger

logger = get_logger(__name__)

Handler = Callable[[dict], "dict[str, Any]"]
ConfirmCallback = Callable[[ActionSpec, dict, str], bool]


@dataclass
class ActionOutcome:
    """一次动作执行的结果。"""

    name: str
    status: str
    result: dict = field(default_factory=dict)
    message: str = ""
    risk_level: str = ""

    @property
    def ok(self) -> bool:
        return self.status == STATUS_EXECUTED

    def to_tool_payload(self) -> dict[str, Any]:
        """回灌模型用的结果载荷（tool 消息 content）。"""
        return {
            "status": self.status,
            "message": self.message,
            "result": self.result,
        }


class ActionDispatcher:
    def __init__(
        self,
        registry: ActionRegistry,
        permission: PermissionChecker,
        audit: AuditLog | None = None,
    ) -> None:
        self._registry = registry
        self._permission = permission
        self._audit = audit or get_audit_log()
        self._handlers: dict[str, Handler] = {}
        self._confirm_cb: ConfirmCallback | None = None

    @property
    def registry(self) -> ActionRegistry:
        return self._registry

    def set_confirm_callback(self, callback: ConfirmCallback | None) -> None:
        """注入确认回调：callback(spec, arguments, reason) -> bool（True=用户确认）。"""
        self._confirm_cb = callback

    def register_handler(self, name: str, handler: Handler) -> None:
        self._handlers[name] = handler

    def register_handlers(self, mapping: dict[str, Handler]) -> None:
        self._handlers.update(mapping)

    def dispatch(self, name: str, arguments: dict | None = None) -> ActionOutcome:
        args = arguments or {}
        spec = self._registry.get(name)
        if spec is None:
            return self._fail(name, "", STATUS_FAILED, "动作不存在或未注册。")

        schema = spec.parameters_schema or {}
        if schema:
            errors = validate_against_schema(args, schema)
            if errors:
                msg = "参数校验失败：" + "；".join(errors)
                return self._fail(name, spec.risk_level, STATUS_FAILED, msg, args)

        decision = self._permission.check(spec)
        if decision.blocked:
            self._audit.record(
                action=name,
                status=STATUS_DENIED,
                risk_level=spec.risk_level,
                arguments=args,
                message=decision.reason,
            )
            return ActionOutcome(
                name=name,
                status=STATUS_DENIED,
                message=decision.reason,
                risk_level=spec.risk_level,
            )

        if decision.require_confirmation:
            confirmed = False
            if self._confirm_cb is not None:
                try:
                    confirmed = bool(self._confirm_cb(spec, args, decision.reason))
                except Exception:  # noqa: BLE001 - 确认回调异常视为未确认
                    logger.error("动作确认回调异常: %s", name, exc_info=True)
                    confirmed = False
            if not confirmed:
                self._audit.record(
                    action=name,
                    status=STATUS_CANCELLED,
                    risk_level=spec.risk_level,
                    arguments=args,
                    message="用户取消或未确认。",
                )
                return ActionOutcome(
                    name=name,
                    status=STATUS_CANCELLED,
                    message="用户取消操作。",
                    risk_level=spec.risk_level,
                )

        handler = self._handlers.get(name)
        if handler is None:
            return self._fail(
                name, spec.risk_level, STATUS_FAILED, "动作未实现 handler。", args
            )

        try:
            result = handler(args) or {}
        except Exception as exc:  # noqa: BLE001 - 转为可读结果回灌模型
            logger.error("动作执行异常: %s", name, exc_info=True)
            return self._fail(
                name, spec.risk_level, STATUS_FAILED, f"执行异常：{exc}", args
            )

        if not isinstance(result, dict):
            result = {"value": result}

        message = str(result.pop("_message", "")) if "_message" in result else ""
        # handler 显式返回 ok=False 视为失败：须如实回灌模型，
        # 否则模型会误判成功而反复重试直至达到工具调用上限。
        ok = result.get("ok", True)
        status = STATUS_EXECUTED if ok else STATUS_FAILED
        self._audit.record(
            action=name,
            status=status,
            risk_level=spec.risk_level,
            arguments=args,
            message=message,
        )
        return ActionOutcome(
            name=name,
            status=status,
            result=result,
            message=message,
            risk_level=spec.risk_level,
        )

    def _fail(
        self,
        name: str,
        risk_level: str,
        status: str,
        message: str,
        args: dict | None = None,
    ) -> ActionOutcome:
        self._audit.record(
            action=name,
            status=status,
            risk_level=risk_level,
            arguments=args or {},
            message=message,
        )
        return ActionOutcome(
            name=name, status=status, message=message, risk_level=risk_level
        )
