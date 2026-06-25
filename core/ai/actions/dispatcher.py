"""ActionDispatcher：按动作 name 路由到 handler 并执行（AIAssist_Architecture.md §8 / §10）。

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
from core.ai.actions.policy import PolicyStore
from core.ai.actions.registry import ActionRegistry, ActionSpec
from core.ai.response_parser import validate_against_schema
from log_config import get_logger

logger = get_logger(__name__)

Handler = Callable[[dict], "dict[str, Any]"]


@dataclass
class ConfirmResult:
    """确认回调返回结果（支持会话级/常驻白名单写回，AI_AssistNewFeature_V1 F2.4）。"""

    confirmed: bool
    remember_session: bool = False
    remember_resident: bool = False


# 确认回调可返回 bool（仅确认）或 ConfirmResult（含白名单写回）。
ConfirmCallback = Callable[[ActionSpec, dict, str], "bool | ConfirmResult"]


@dataclass
class ActionOutcome:
    """一次动作执行的结果。"""

    name: str
    status: str
    result: dict = field(default_factory=dict)
    message: str = ""
    risk_level: str = ""
    auto_approved: bool = False

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
        policy: PolicyStore | None = None,
    ) -> None:
        self._registry = registry
        self._permission = permission
        self._audit = audit or get_audit_log()
        self._policy = policy or PolicyStore.load()
        self._handlers: dict[str, Handler] = {}
        self._confirm_cb: ConfirmCallback | None = None
        self._implicit_whitelist_check: Callable[[], bool] | None = None

    @property
    def registry(self) -> ActionRegistry:
        return self._registry

    @property
    def policy(self) -> PolicyStore:
        return self._policy

    def set_implicit_whitelist_check(self, check: Callable[[], bool] | None) -> None:
        """注入序列运行隐式白名单判定回调（AI_AssistNewFeature_V1 §2.1③）。

        已过 preflight + 用户点 Run、序列运行中时，high 动作不再逐次打扰；
        critical 不受影响。回调返回 True 表示当前处于序列运行窗口。
        """
        self._implicit_whitelist_check = check

    def _in_implicit_whitelist(self) -> bool:
        if self._implicit_whitelist_check is None:
            return False
        try:
            return bool(self._implicit_whitelist_check())
        except Exception:  # noqa: BLE001 - 判定异常视为不在白名单窗口
            logger.error("序列运行隐式白名单判定异常", exc_info=True)
            return False

    def set_confirm_callback(self, callback: ConfirmCallback | None) -> None:
        """注入确认回调：callback(spec, arguments, reason) -> bool（True=用户确认）。"""
        self._confirm_cb = callback

    def register_handler(self, name: str, handler: Handler) -> None:
        self._handlers[name] = handler

    def register_handlers(self, mapping: dict[str, Handler]) -> None:
        self._handlers.update(mapping)

    def dispatch(
        self, name: str, arguments: dict | None = None, *, bypass_confirmation: bool = False
    ) -> ActionOutcome:
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

        policy_result = self._policy.evaluate(name, args)
        if policy_result.blocked:
            return self._deny(name, spec.risk_level, policy_result.reason, args)

        decision = self._permission.check(spec)
        if decision.blocked:
            return self._deny(name, spec.risk_level, decision.reason, args)

        auto_approved = False
        # 调度任务登记时已一次性授权（pre_authorized，§5.6）：到点免确认。
        # 安全：仅非 critical 动作可走此路径（critical 已在 permission.check 拦截）。
        if decision.require_confirmation and bypass_confirmation:
            auto_approved = True
        elif decision.require_confirmation:
            confirmed, auto_approved = self._resolve_confirmation(
                spec, args, decision.reason, policy_result
            )
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
        audit_message = message
        if auto_approved and status == STATUS_EXECUTED:
            audit_message = ("[白名单自动批准] " + message).strip()
        self._audit.record(
            action=name,
            status=status,
            risk_level=spec.risk_level,
            arguments=args,
            message=audit_message,
        )
        return ActionOutcome(
            name=name,
            status=status,
            result=result,
            message=message,
            risk_level=spec.risk_level,
            auto_approved=auto_approved and status == STATUS_EXECUTED,
        )

    def _resolve_confirmation(
        self, spec: ActionSpec, args: dict, reason: str, policy_result
    ) -> tuple[bool, bool]:
        """决策链确认环节（AI_AssistNewFeature_V1 §2.3）。

        命中白名单（护栏通过）-> 免确认；critical 不享白名单/隐式窗口；
        隐式窗口（序列运行中）对 high 免确认；否则弹确认框，
        确认回调可携带"记住本动作"以写回会话级/常驻白名单。

        返回 (confirmed, auto_approved)：auto_approved 表示命中白名单/隐式窗口
        而免确认（未弹卡片），供 UI 给出"已自动执行"提示。免确认时不在此处
        预写审计，统一由 dispatch() 在 handler 真正执行后落一条结果审计，避免重复。
        """
        if policy_result.auto_approve and spec.risk_level != "critical":
            return True, True

        if spec.risk_level == "high" and self._in_implicit_whitelist():
            return True, True

        if self._confirm_cb is None:
            return False, False
        try:
            result = self._confirm_cb(spec, args, reason)
        except Exception:  # noqa: BLE001 - 确认回调异常视为未确认
            logger.error("动作确认回调异常: %s", spec.name, exc_info=True)
            return False, False

        if isinstance(result, ConfirmResult):
            if result.confirmed:
                self._apply_grants(spec, args, result)
            return bool(result.confirmed), False
        return bool(result), False

    def _apply_grants(self, spec: ActionSpec, args: dict, result: ConfirmResult) -> None:
        """根据确认结果写回白名单（护栏取当前参数的标量值为边界）。"""
        if not (result.remember_session or result.remember_resident):
            return
        when = self._guardrail_from_args(spec, args)
        if result.remember_resident:
            self._policy.grant_resident(spec.name, when)
        elif result.remember_session:
            self._policy.grant_session(spec.name, when)

    @staticmethod
    def _guardrail_from_args(spec: ActionSpec, args: dict) -> dict[str, Any]:
        """high 动作记住时，按当前数值参数生成 *_max 护栏，避免无边界放行。"""
        if spec.risk_level != "high":
            return {}
        guardrail: dict[str, Any] = {}
        for key, value in (args or {}).items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                guardrail[f"{key}_max"] = value
        return guardrail

    def _deny(
        self, name: str, risk_level: str, reason: str, args: dict | None = None
    ) -> ActionOutcome:
        self._audit.record(
            action=name,
            status=STATUS_DENIED,
            risk_level=risk_level,
            arguments=args or {},
            message=reason,
        )
        return ActionOutcome(
            name=name, status=STATUS_DENIED, message=reason, risk_level=risk_level
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
