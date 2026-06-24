"""build_action_system：装配 ActionRegistry + ActionDispatcher（AI_Assist.md §8）。

把各 handlers 模块的 SPECS 注册进 registry，build_handlers(deps) 注册进 dispatcher，
返回 (registry, dispatcher)。UI 注入 ActionDeps 与确认回调即可闭环。
本模块禁 import Qt。
"""
from __future__ import annotations

from core.ai.actions.dispatcher import ActionDispatcher
from core.ai.actions.handlers import deps as _deps_mod
from core.ai.actions.handlers import (
    instrument as _instrument,
    query as _query,
    scope as _scope,
    serial as _serial,
    test as _test,
    ui as _ui,
)
from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.permission import PermissionChecker
from core.ai.actions.policy import PolicyStore
from core.ai.actions.registry import ActionRegistry
from log_config import get_logger

logger = get_logger(__name__)

_HANDLER_MODULES = (_query, _ui, _serial, _instrument, _scope, _test)


def build_registry() -> ActionRegistry:
    registry = ActionRegistry()
    for module in _HANDLER_MODULES:
        registry.register_many(module.SPECS)
    return registry


def build_action_system(
    deps: ActionDeps,
    *,
    require_confirm_high: bool = True,
    allow_critical: bool = False,
) -> tuple[ActionRegistry, ActionDispatcher]:
    registry = build_registry()
    permission = PermissionChecker(
        require_confirm_high=require_confirm_high,
        allow_critical=allow_critical,
    )
    policy = PolicyStore.load()
    dispatcher = ActionDispatcher(registry, permission, policy=policy)
    for module in _HANDLER_MODULES:
        dispatcher.register_handlers(module.build_handlers(deps))
    logger.debug("Action system 装配完成：%d 个动作", len(registry.names()))
    return registry, dispatcher
