"""AI 受控动作层（AI_Assist.md §8 / §10）。

AI 一切落地动作必须经此层：注册 -> 权限/风险判定 -> 必要时确认 -> 执行 -> 审计。
本层禁 import Qt Widgets（dispatcher/handlers 通过 UI 注入的回调间接操作 UI/仪器）。
"""
from __future__ import annotations

MODULE_VERSION = "0.1.0"

from core.ai.actions.audit import AuditLog, get_audit_log
from core.ai.actions.dispatcher import ActionDispatcher, ActionOutcome, ConfirmResult
from core.ai.actions.permission import (
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    PermissionChecker,
    RiskDecision,
)
from core.ai.actions.policy import PolicyResult, PolicyStore
from core.ai.actions.registry import ActionRegistry, ActionSpec
from core.ai.actions.builder import build_action_system, build_registry
from core.ai.actions.handlers.deps import ActionDeps

__all__ = [
    "MODULE_VERSION",
    "ActionSpec",
    "ActionRegistry",
    "ActionDispatcher",
    "ActionOutcome",
    "ConfirmResult",
    "PermissionChecker",
    "RiskDecision",
    "PolicyStore",
    "PolicyResult",
    "RISK_LOW",
    "RISK_MEDIUM",
    "RISK_HIGH",
    "RISK_CRITICAL",
    "AuditLog",
    "get_audit_log",
    "ActionDeps",
    "build_action_system",
    "build_registry",
]
