"""测试序列类动作 handlers（AI_Assist.md §8 / §10）。

start_test_sequence / pause_test_sequence / stop_test_sequence：
  均为 high 风险，经 UI 注入的受控回调（最终走 custom_test runner），
  start/pause 需确认；stop 作为安全操作不强制确认（仍写审计）。
本模块禁 import Qt。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_TEST_SEQUENCE, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

_EMPTY_SCHEMA = {"type": "object", "properties": {}}

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="start_test_sequence",
        description="启动当前页面的测试序列（高风险，需确认；经 custom_test runner）。",
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_TEST_SEQUENCE,
    ),
    ActionSpec(
        name="pause_test_sequence",
        description="暂停/恢复当前运行的测试序列（高风险，需确认）。",
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_TEST_SEQUENCE,
    ),
    ActionSpec(
        name="stop_test_sequence",
        description="停止当前运行的测试序列（安全操作）。",
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="high",
        require_confirmation=False,
        category=CATEGORY_TEST_SEQUENCE,
    ),
]


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def start_test_sequence(_args: dict) -> dict:
        if deps.test_run_callback is None:
            return {"ok": False, "_message": "当前页面不支持启动测试序列（请切到 Custom Test）。"}
        ok, message = deps.test_run_callback()
        return {"ok": bool(ok), "_message": message or ("已启动测试序列。" if ok else "启动失败。")}

    def pause_test_sequence(_args: dict) -> dict:
        if deps.test_pause_callback is None:
            return {"ok": False, "_message": "当前页面不支持暂停测试序列。"}
        ok, message = deps.test_pause_callback()
        return {"ok": bool(ok), "_message": message or "已切换暂停/恢复。"}

    def stop_test_sequence(_args: dict) -> dict:
        if deps.test_stop_callback is None:
            return {"ok": False, "_message": "当前页面不支持停止测试序列。"}
        ok, message = deps.test_stop_callback()
        return {"ok": bool(ok), "_message": message or "已发送停止请求。"}

    return {
        "start_test_sequence": start_test_sequence,
        "pause_test_sequence": pause_test_sequence,
        "stop_test_sequence": stop_test_sequence,
    }
