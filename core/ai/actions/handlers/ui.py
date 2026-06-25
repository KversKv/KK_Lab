"""UI 类动作 handlers（AIAssist_Architecture.md §8 / AIAssist_PageScopedControlPlan.md §5b）。

open_page：经 UI 注入的受控回调跳转页面（不直接操作 Qt）；
toggle_ai_panel：开关右侧 AI 面板；
list_ui_actions：列当前页**可触发**的具名 UI 动作（经 UIActionRegistry + enabled_when 过滤）；
ui_invoke：触发指定 action_id 的 UI 动作（经 deps.ui_invoke_callback 委派枢纽执行）。

list_ui_actions 风险 low（只读列举）；ui_invoke 风险 medium + 需确认（AI 触发 UI 按钮
属特权操作，统一经 dispatcher 确认/审计，目标项 risk 仅作展示与引导）。
本模块禁 import Qt。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_UI, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

# 与 MainWindow.current_instrument_ui 一致的页面键
_PAGE_KEYS = [
    "power_analyser",
    "datalog",
    "oscilloscope",
    "thermal_chamber",
    "pmu_test",
    "consumption_test",
    "charger_test",
    "orchestrator",
    "vmin_hunter",
    "kk_serials",
    "collection",
]

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="open_page",
        description="切换到指定页面。page 取值见枚举。",
        parameters_schema={
            "type": "object",
            "properties": {"page": {"type": "string", "enum": _PAGE_KEYS}},
            "required": ["page"],
        },
        risk_level="low",
        category=CATEGORY_UI,
    ),
    ActionSpec(
        name="toggle_ai_panel",
        description="打开或关闭右侧 AI 助手面板。",
        parameters_schema={
            "type": "object",
            "properties": {"open": {"type": "boolean"}},
            "required": ["open"],
        },
        risk_level="low",
        category=CATEGORY_UI,
    ),
    ActionSpec(
        name="list_ui_actions",
        description=(
            "列出当前页面可由 AI 触发的具名 UI 动作（白名单制，仅返回 enabled 项）。"
            "用于无专用接口的页面按钮（如 Auto Set / Zero / Calibrate）。"
            "返回每项的 id/label/risk/confirm/description；触发用 ui_invoke。"
        ),
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_UI,
    ),
    ActionSpec(
        name="ui_invoke",
        description=(
            "触发当前页面已登记的具名 UI 动作（action_id 来自 list_ui_actions）。"
            "执行前会弹确认框；未登记或当前不可用的 action_id 将被拒绝。"
            "行为与用户点击按钮完全一致，UI 经原有信号/轮询自动刷新。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "action_id": {
                    "type": "string",
                    "description": "UI 动作 id，如 power_analyser.auto_set",
                }
            },
            "required": ["action_id"],
        },
        risk_level="medium",
        require_confirmation=True,
        category=CATEGORY_UI,
    ),
]


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def open_page(args: dict) -> dict:
        page = str(args.get("page", "")).strip()
        if page not in _PAGE_KEYS:
            return {"ok": False, "_message": f"未知页面：{page}"}
        if deps.open_page_callback is None:
            return {"ok": False, "_message": "当前环境不支持页面跳转。"}
        ok, message = deps.open_page_callback(page)
        return {"ok": bool(ok), "_message": message or (f"已跳转到 {page}" if ok else "跳转失败")}

    def toggle_ai_panel(args: dict) -> dict:
        want_open = bool(args.get("open", True))
        if deps.toggle_ai_panel_callback is None:
            return {"ok": False, "_message": "当前环境不支持面板开关。"}
        ok, message = deps.toggle_ai_panel_callback(want_open)
        return {"ok": bool(ok), "_message": message}

    def list_ui_actions(args: dict) -> dict:
        registry = deps.ui_action_registry
        if registry is None:
            return {"ok": True, "actions": [], "_message": "当前环境未启用 UI 动作注册表。"}
        if deps.page_key_getter is None:
            return {"ok": False, "_message": "无法确定当前页面。"}
        try:
            page_key = deps.page_key_getter()
        except Exception:  # noqa: BLE001
            logger.error("list_ui_actions 取 page_key 失败", exc_info=True)
            return {"ok": False, "_message": "无法确定当前页面。"}
        if not page_key:
            return {"ok": True, "actions": [], "_message": "当前页面无已登记的 UI 动作。"}
        try:
            specs = registry.list_for_page(page_key, only_enabled=True)
            actions = [s.to_view() for s in specs]
        except Exception:  # noqa: BLE001
            logger.error("list_ui_actions 列举失败: %s", page_key, exc_info=True)
            return {"ok": False, "_message": "列举 UI 动作失败，详见日志。"}
        if not actions:
            return {
                "ok": True,
                "actions": [],
                "_message": f"当前页面「{page_key}」无可用 UI 动作。",
            }
        labels = ", ".join(f"{a['id']}({a['label']})" for a in actions)
        return {
            "ok": True,
            "actions": actions,
            "_message": f"当前页可触发 {len(actions)} 个 UI 动作：{labels}",
        }

    def ui_invoke(args: dict) -> dict:
        action_id = str(args.get("action_id", "")).strip()
        if not action_id:
            return {"ok": False, "_message": "缺少 action_id。"}
        if deps.ui_invoke_callback is None:
            return {"ok": False, "_message": "当前环境不支持 UI 动作触发。"}
        try:
            ok, message = deps.ui_invoke_callback(action_id)
        except Exception:  # noqa: BLE001
            logger.error("ui_invoke 执行异常: %s", action_id, exc_info=True)
            return {"ok": False, "_message": "UI 动作执行异常，详见日志。"}
        return {"ok": bool(ok), "_message": message or ("已触发" if ok else "触发失败")}

    return {
        "open_page": open_page,
        "toggle_ai_panel": toggle_ai_panel,
        "list_ui_actions": list_ui_actions,
        "ui_invoke": ui_invoke,
    }
