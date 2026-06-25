"""串口类动作 handlers（AIAssist_Architecture.md §8）。

clear_serial_log  : low，清空 AI 侧 RX 缓存日志；
send_serial_text  : high，向活动会话发送文本（必须确认，经 SerialSessionManager）。
P4 扩展：
list_serial_sessions     : low，列出所有串口会话（经 serial_manager_getter）；
list_serial_ports        : low，枚举系统可用 COM 口（经 serial_ports_getter）；
send_serial_hex          : high，向指定会话发送 HEX（必须确认）；
send_serial_to_session   : high，向指定会话发送文本（必须确认）；
set_active_serial_session: medium，切换活动会话。
不直连串口设备，一律经 UI 注入的受控回调 / SerialSessionManager 访问器。
本模块禁 import Qt。
"""
from __future__ import annotations

import re
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
    ActionSpec(
        name="list_serial_sessions",
        description="列出当前串口管理器中所有会话（含活动标记/端口/波特率/连接/收发字节）。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_SERIAL,
    ),
    ActionSpec(
        name="list_serial_ports",
        description="枚举系统可用串口（COM 口设备名/描述/硬件 ID）。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_SERIAL,
    ),
    ActionSpec(
        name="send_serial_hex",
        description="向指定串口会话发送一段 HEX 数据（高风险，需确认）。hex 仅允许 0-9/a-f/A-F 与空白。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "hex": {"type": "string", "description": "十六进制字符串，如 'A5 0B 00' 或 'A50B00'。"},
            },
            "required": ["session_id", "hex"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_SERIAL,
    ),
    ActionSpec(
        name="send_serial_to_session",
        description="向指定串口会话发送一段文本（高风险，需确认）。用于多会话场景定向发送。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "text": {"type": "string"},
                "append_newline": {"type": "boolean"},
            },
            "required": ["session_id", "text"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_SERIAL,
    ),
    ActionSpec(
        name="set_active_serial_session",
        description="切换当前活动串口会话（影响后续 send_serial_text / get_serial_status 的目标）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
            },
            "required": ["session_id"],
        },
        risk_level="medium",
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

    def _get_manager():
        return deps.serial_manager_getter() if deps.serial_manager_getter else None

    def list_serial_sessions(_args: dict) -> dict:
        manager = _get_manager()
        if manager is None:
            return {"ok": False, "_message": "当前无串口管理器。"}
        sessions = manager.sessions
        active_id = manager.active_session_id
        items: list[dict[str, Any]] = []
        for sid, sess in sessions.items():
            items.append(
                {
                    "session_id": sid,
                    "display_name": getattr(sess, "display_name", "") or sid,
                    "port": getattr(sess, "port", "") or "",
                    "baudrate": getattr(sess, "baudrate", 0),
                    "connected": bool(getattr(sess, "connected", False)),
                    "rx_bytes": getattr(sess, "rx_bytes", 0),
                    "tx_bytes": getattr(sess, "tx_bytes", 0),
                    "is_active": sid == active_id,
                }
            )
        return {
            "ok": True,
            "count": len(items),
            "active_session_id": active_id or "",
            "sessions": items,
            "_message": f"共 {len(items)} 个串口会话。",
        }

    def list_serial_ports(_args: dict) -> dict:
        if deps.serial_ports_getter is None:
            return {"ok": False, "_message": "当前环境不支持串口枚举。"}
        try:
            ports = deps.serial_ports_getter()
        except Exception:  # noqa: BLE001 - 枚举异常转可读结果
            logger.error("AI 枚举串口失败", exc_info=True)
            return {"ok": False, "_message": "串口枚举异常，请查看日志。"}
        return {
            "ok": True,
            "count": len(ports),
            "ports": ports,
            "_message": f"共发现 {len(ports)} 个可用串口。",
        }

    def send_serial_hex(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        hex_str = str(args.get("hex", ""))
        if not session_id:
            return {"ok": False, "_message": "缺少 session_id。"}
        if not hex_str:
            return {"ok": False, "_message": "HEX 内容为空。"}
        manager = _get_manager()
        if manager is None:
            return {"ok": False, "_message": "当前无串口管理器。"}
        session = manager.get_session(session_id)
        if session is None:
            return {"ok": False, "_message": f"会话不存在：{session_id}"}
        if not getattr(session, "connected", False):
            return {"ok": False, "_message": f"会话未连接：{session_id}"}
        cleaned = re.sub(r"\s+", "", hex_str)
        try:
            data = bytes.fromhex(cleaned)
        except ValueError:
            return {
                "ok": False,
                "_message": "HEX 字符串无效（仅允许 0-9/a-f/A-F 与空白）。",
            }
        if not data:
            return {"ok": False, "_message": "HEX 解析后为空。"}
        try:
            ok = manager.send_to_session(session_id, data)
        except Exception:  # noqa: BLE001 - 发送异常转可读结果
            logger.error("AI 串口 HEX 发送失败", exc_info=True)
            return {"ok": False, "_message": "串口发送异常，请查看日志。"}
        return {
            "ok": bool(ok),
            "session_id": session_id,
            "bytes_sent": len(data),
            "_message": "已发送 HEX 数据。" if ok else "发送失败。",
        }

    def send_serial_to_session(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        text = str(args.get("text", ""))
        if not session_id:
            return {"ok": False, "_message": "缺少 session_id。"}
        if not text:
            return {"ok": False, "_message": "发送内容为空。"}
        manager = _get_manager()
        if manager is None:
            return {"ok": False, "_message": "当前无串口管理器。"}
        session = manager.get_session(session_id)
        if session is None:
            return {"ok": False, "_message": f"会话不存在：{session_id}"}
        if not getattr(session, "connected", False):
            return {"ok": False, "_message": f"会话未连接：{session_id}"}
        newline = "\r\n" if args.get("append_newline", True) else ""
        payload = (text + newline).encode("utf-8", errors="ignore")
        try:
            ok = manager.send_to_session(session_id, payload)
        except Exception:  # noqa: BLE001 - 发送异常转可读结果
            logger.error("AI 串口定向发送失败", exc_info=True)
            return {"ok": False, "_message": "串口发送异常，请查看日志。"}
        return {
            "ok": bool(ok),
            "session_id": session_id,
            "bytes_sent": len(payload),
            "_message": "已发送。" if ok else "发送失败。",
        }

    def set_active_serial_session(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        if not session_id:
            return {"ok": False, "_message": "缺少 session_id。"}
        manager = _get_manager()
        if manager is None:
            return {"ok": False, "_message": "当前无串口管理器。"}
        try:
            ok = manager.set_active_session(session_id)
        except Exception:  # noqa: BLE001 - 切换异常转可读结果
            logger.error("AI 切换活动串口会话失败", exc_info=True)
            return {"ok": False, "_message": "切换会话异常，请查看日志。"}
        active_id = manager.active_session_id or ""
        return {
            "ok": bool(ok),
            "active_session_id": active_id,
            "_message": (
                f"已切换活动会话：{session_id}。"
                if ok
                else f"会话不存在：{session_id}。"
            ),
        }

    return {
        "clear_serial_log": clear_serial_log,
        "send_serial_text": send_serial_text,
        "list_serial_sessions": list_serial_sessions,
        "list_serial_ports": list_serial_ports,
        "send_serial_hex": send_serial_hex,
        "send_serial_to_session": send_serial_to_session,
        "set_active_serial_session": set_active_serial_session,
    }
