"""串口类动作 handlers（AI_Assist.md §8）。

clear_serial_log  : low，清空 AI 侧 RX 缓存日志；
send_serial_text  : high，向活动会话发送文本（必须确认，经 SerialSessionManager）。
不直连串口设备，一律经 UI 注入的受控回调（最终走 SerialSessionManager.send_to_active_session）。
本模块禁 import Qt。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_SERIAL, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="clear_serial_log",
        description="清空 AI 侧串口接收日志缓存。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_SERIAL,
    ),
    ActionSpec(
        name="send_serial_text",
        description="向当前活动串口会话发送一段文本（高风险，需确认）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "append_newline": {"type": "boolean"},
            },
            "required": ["text"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_SERIAL,
    ),
]


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def clear_serial_log(_args: dict) -> dict:
        if deps.serial_clear_callback is None:
            return {"ok": False, "_message": "当前环境不支持清空串口日志。"}
        ok, message = deps.serial_clear_callback()
        return {"ok": bool(ok), "_message": message or "已清空串口日志缓存。"}

    def send_serial_text(args: dict) -> dict:
        text = str(args.get("text", ""))
        if not text:
            return {"ok": False, "_message": "发送内容为空。"}
        if deps.serial_send_text_callback is None:
            return {"ok": False, "_message": "当前环境不支持串口发送。"}
        newline = "\r\n" if args.get("append_newline", True) else ""
        ok, message = deps.serial_send_text_callback(text, newline)
        return {
            "ok": bool(ok),
            "bytes_sent": len(text.encode("utf-8", errors="ignore")),
            "_message": message or ("已发送。" if ok else "发送失败（串口未连接？）。"),
        }

    return {
        "clear_serial_log": clear_serial_log,
        "send_serial_text": send_serial_text,
    }
