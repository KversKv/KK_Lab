"""查询类动作 handlers（AI_Assist.md §8）。

全部为只读、low 风险：当前页 / 串口状态 / 串口最近日志 / 软件日志 / 仪器状态 / 测试状态。
仪器状态仅读 InstrumentManager.sessions() 快照，不主动 query 真机。
本模块禁 import Qt。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_QUERY, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

_LINES_SCHEMA = {
    "type": "object",
    "properties": {
        "lines": {"type": "integer", "minimum": 1, "maximum": 1000},
    },
}

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="get_current_page",
        description="获取当前所在页面标识（page_key）。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_serial_status",
        description="获取当前活动串口会话状态（端口/波特率/连接/收发字节）。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_recent_serial_logs",
        description="读取当前活动串口会话最近 N 行接收日志（受脱敏与上限保护）。",
        parameters_schema=_LINES_SCHEMA,
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_recent_app_logs",
        description="读取软件运行日志最近 N 行（环形缓冲）。",
        parameters_schema=_LINES_SCHEMA,
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_instrument_status",
        description="读取已注册仪器会话状态快照（不主动 query 真机）。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_test_sequence_status",
        description="获取当前测试序列运行状态（是否运行/暂停/步骤数）。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
]


def _clamp_lines(args: dict, default: int = 200) -> int:
    try:
        value = int(args.get("lines", default))
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, 1000))


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def get_current_page(_args: dict) -> dict:
        page = deps.page_key_getter() if deps.page_key_getter else None
        return {"page_key": page or "", "_message": f"当前页面：{page or '未知'}"}

    def get_serial_status(_args: dict) -> dict:
        status = deps.serial_status_getter() if deps.serial_status_getter else None
        if not status:
            return {"connected": False, "_message": "当前无活动串口会话。"}
        return dict(status)

    def get_recent_serial_logs(args: dict) -> dict:
        lines = _clamp_lines(args)
        status = deps.serial_status_getter() if deps.serial_status_getter else None
        session_id = status.get("session_id") if status else None
        logs: list[str] = []
        if deps.rx_recent_getter is not None:
            logs = deps.rx_recent_getter(session_id, lines)
        return {
            "session_id": session_id or "",
            "lines_returned": len(logs),
            "logs": logs,
            "truncated": len(logs) >= lines,
        }

    def get_recent_app_logs(args: dict) -> dict:
        lines = _clamp_lines(args, default=300)
        logs = deps.app_logs_getter(lines) if deps.app_logs_getter else []
        return {
            "lines_returned": len(logs),
            "logs": logs,
            "truncated": len(logs) >= lines,
        }

    def get_instrument_status(_args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"instruments": [], "_message": "InstrumentManager 不可用。"}
        items = []
        for snap in manager.sessions():
            items.append(
                {
                    "session_id": snap.session_id,
                    "instrument_type": snap.instrument_type,
                    "role": snap.role,
                    "model": snap.model,
                    "connected": bool(snap.connected),
                    "busy": bool(snap.busy),
                }
            )
        return {
            "count": len(items),
            "instruments": items,
            "_message": f"共 {len(items)} 个仪器会话。",
        }

    def get_test_sequence_status(_args: dict) -> dict:
        status = deps.test_status_getter() if deps.test_status_getter else None
        if not status:
            return {"available": False, "_message": "当前页面无测试序列。"}
        return dict(status)

    return {
        "get_current_page": get_current_page,
        "get_serial_status": get_serial_status,
        "get_recent_serial_logs": get_recent_serial_logs,
        "get_recent_app_logs": get_recent_app_logs,
        "get_instrument_status": get_instrument_status,
        "get_test_sequence_status": get_test_sequence_status,
    }
