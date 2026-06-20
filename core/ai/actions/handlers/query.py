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
    ActionSpec(
        name="get_waveform_window",
        description=(
            "波形按需放大（drill-down）：截取指定通道在 [t0, t1] 时间窗内的"
            "高分辨率片段。先看过波形统计摘要后，定位到感兴趣区间再放大查看细节。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "通道标签，如 'CH1 I'。"},
                "t0": {"type": "number", "description": "时间窗起点（秒）。"},
                "t1": {"type": "number", "description": "时间窗终点（秒）。"},
                "max_points": {
                    "type": "integer",
                    "minimum": 10,
                    "maximum": 5000,
                    "description": "返回点数上限（默认 2500，超出做 LTTB 压缩）。",
                },
            },
            "required": ["label", "t0", "t1"],
        },
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_waveform_segments",
        description=(
            "波形段落子结构分析（PELT 双引擎 drill-down）：对一个已识别的尖峰/事件"
            "时间窗 [t0, t1] 用变点检测重扫，暴露窗内中幅平台/电平台阶等子结构"
            "（如 RX 平台串）。每段返回 形态标签/均值/峰值/宽度/电荷。"
            "当统计摘要里的尖峰事件可能内含更细结构时调用。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "通道标签，如 'CH1 I'。"},
                "t0": {"type": "number", "description": "时间窗起点（秒）。"},
                "t1": {"type": "number", "description": "时间窗终点（秒）。"},
                "pen": {
                    "type": "number",
                    "minimum": 0.1,
                    "maximum": 1000.0,
                    "description": "PELT 惩罚系数（默认 6.0，越大段越少越粗）。",
                },
            },
            "required": ["label", "t0", "t1"],
        },
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

    def get_waveform_window(args: dict) -> dict:
        from core.ai.providers.waveform_provider import slice_window

        all_data = deps.waveform_data_getter() if deps.waveform_data_getter else None
        if not all_data:
            return {"ok": False, "_message": "当前无可放大的波形数据。"}
        label = str(args.get("label", ""))
        if label not in all_data:
            return {
                "ok": False,
                "available_labels": list(all_data.keys()),
                "_message": f"通道 '{label}' 不存在，请从 available_labels 选择。",
            }
        try:
            t0 = float(args.get("t0"))
            t1 = float(args.get("t1"))
        except (TypeError, ValueError):
            return {"ok": False, "_message": "t0/t1 必须为数值。"}
        max_points = args.get("max_points", 2500)
        try:
            max_points = max(10, min(int(max_points), 5000))
        except (TypeError, ValueError):
            max_points = 2500
        segment = slice_window(all_data, label, t0, t1, max_points=max_points)
        point_count = len(segment.get("values", []))
        return {
            "label": label,
            "t0": t0,
            "t1": t1,
            "point_count": point_count,
            "time": segment.get("time", []),
            "values": segment.get("values", []),
            "_message": f"通道 {label} 在 [{t0}, {t1}] 窗口返回 {point_count} 点。",
        }

    def get_waveform_segments(args: dict) -> dict:
        from core.ai.providers.waveform_provider import analyze_window_segments

        all_data = deps.waveform_data_getter() if deps.waveform_data_getter else None
        if not all_data:
            return {"ok": False, "_message": "当前无可分析的波形数据。"}
        label = str(args.get("label", ""))
        if label not in all_data:
            return {
                "ok": False,
                "available_labels": list(all_data.keys()),
                "_message": f"通道 '{label}' 不存在，请从 available_labels 选择。",
            }
        try:
            t0 = float(args.get("t0"))
            t1 = float(args.get("t1"))
        except (TypeError, ValueError):
            return {"ok": False, "_message": "t0/t1 必须为数值。"}
        try:
            pen = float(args.get("pen", 6.0))
        except (TypeError, ValueError):
            pen = 6.0
        pen = max(0.1, min(pen, 1000.0))
        result = analyze_window_segments(all_data, label, t0, t1, pen=pen)
        segments = result.get("segments", [])
        return {
            "ok": True,
            "label": label,
            "t0": t0,
            "t1": t1,
            "engine": result.get("engine", "pelt"),
            "segment_count": len(segments),
            "segments": segments,
            "_message": (
                f"通道 {label} 在 [{t0}, {t1}] 窗口 PELT 切出 {len(segments)} 段。"
            ),
        }

    return {
        "get_current_page": get_current_page,
        "get_serial_status": get_serial_status,
        "get_recent_serial_logs": get_recent_serial_logs,
        "get_recent_app_logs": get_recent_app_logs,
        "get_instrument_status": get_instrument_status,
        "get_test_sequence_status": get_test_sequence_status,
        "get_waveform_window": get_waveform_window,
        "get_waveform_segments": get_waveform_segments,
    }
