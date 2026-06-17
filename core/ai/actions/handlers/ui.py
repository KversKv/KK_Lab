"""UI 类动作 handlers（AI_Assist.md §8）。

open_page：经 UI 注入的受控回调跳转页面（不直接操作 Qt）；
toggle_ai_panel：开关右侧 AI 面板。
风险等级 low（仅 UI 导航，不触碰仪器/串口/测试运行）。
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
    "custom_test",
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

    return {
        "open_page": open_page,
        "toggle_ai_panel": toggle_ai_panel,
    }
