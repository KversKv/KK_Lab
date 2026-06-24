"""查询类动作 handlers（AI_Assist.md §8）。

全部为只读、low 风险：当前页 / 串口状态 / 串口最近日志 / 软件日志 / 仪器状态 / 测试状态。
仪器状态仅读 InstrumentManager.sessions() 快照，不主动 query 真机。
P7 诊断自检动作亦并入本模块（category=query）：
  get_instrument_errors   : low，读 SCPI 错误队列（驱动 get_errors）；
  run_instrument_selftest : medium，触发仪器自检（*TST?），持 busy 租约；
  ping_instrument         : low，连通性检查（ping / identify_instrument / *IDN?）；
  get_recent_audit_log    : low，回看 AI 历史动作审计（JSONL）；
  get_app_log_errors      : low，软件日志环形缓冲仅过滤 ERROR/WARN。
本模块禁 import Qt。
"""
from __future__ import annotations

import json
import os
from typing import Any

from core.ai.actions.audit import get_audit_log
from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.handlers.instrument import (
    _resolve_query_fn,
    _run_read_action,
    _run_write_action,
)
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
    ActionSpec(
        name="get_instrument_errors",
        description="读取已连接仪器 SCPI 错误队列（驱动 get_errors，low：只读）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="run_instrument_selftest",
        description=(
            "触发已连接仪器自检（*TST?，medium：自检期间持 busy 租约，避免抢占运行中测试）。"
            "返回结果码与 passed 标志（0=通过）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="medium",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="ping_instrument",
        description="检查已连接仪器连通性（ping / identify_instrument / *IDN?，low：只读）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_recent_audit_log",
        description="回看 AI 历史动作审计日志最近 N 行（JSONL，low：只读）。",
        parameters_schema=_LINES_SCHEMA,
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_app_log_errors",
        description="读取软件日志环形缓冲中最近 N 行 ERROR/WARN/CRITICAL 记录（low：只读）。",
        parameters_schema=_LINES_SCHEMA,
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="get_task_result",
        description=(
            "按 task_id 查询一个异步任务的结果（B 兜底：事件续跑未触发时主动查）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
        risk_level="low",
        category=CATEGORY_QUERY,
    ),
    ActionSpec(
        name="list_pending_tasks",
        description="列出当前会话进行中 / 已完成未消费的异步任务摘要。",
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


def _is_no_error(err: Any) -> bool:
    """判断 SCPI 错误队列条目是否表示「无错误」（如 '+0,"No error"'）。"""
    text = str(err).strip().lower()
    return text.startswith("+0") or "no error" in text or text.startswith("0,")


_ERROR_LEVEL_MARKERS = ("[error]", "[warning]", "[warn]", "[critical]")


def _is_log_error_line(line: str) -> bool:
    """判断格式化日志行是否为 ERROR/WARN/CRITICAL 级别。"""
    if not line:
        return False
    lowered = line.lower()
    return any(marker in lowered for marker in _ERROR_LEVEL_MARKERS)


def _read_recent_audit(lines: int) -> list[dict]:
    """读取审计日志 JSONL 文件最近 N 行并解析为 dict 列表。"""
    try:
        audit = get_audit_log()
    except Exception:  # noqa: BLE001 - 审计单例不可用不应阻断查询
        return []
    path = audit.path
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            all_lines = fh.readlines()
    except OSError:
        logger.error("读取审计日志失败: %s", path, exc_info=True)
        return []
    recent = all_lines[-lines:] if lines < len(all_lines) else all_lines
    entries: list[dict] = []
    for raw in recent:
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
            entries.append(entry if isinstance(entry, dict) else {"raw": str(entry)})
        except (TypeError, ValueError):
            entries.append({"raw": raw})
    return entries


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

    def get_instrument_errors(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "get_errors", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 get_errors（SCPI 错误队列）。")
            errors = fn()
            if not isinstance(errors, list):
                errors = [errors] if errors is not None else []
            errors = [str(e) for e in errors]
            has_errors = bool(errors) and not _is_no_error(errors[0])
            return {
                "errors": errors,
                "error_count": len(errors),
                "has_errors": has_errors,
            }

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            "仪器错误队列读取完成。",
        )

    def run_instrument_selftest(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "self_test", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 self_test（*TST?）。")
            result = fn()
            text = str(result).strip()
            try:
                code = int(text.lstrip("+").strip('"').strip("'"))
                passed = code == 0
            except (TypeError, ValueError):
                passed = False
            return {"self_test_result": text, "passed": passed}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            "仪器自检完成。",
        )

    def ping_instrument(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            ping_fn = getattr(instance, "ping", None)
            if callable(ping_fn):
                try:
                    alive = bool(ping_fn())
                except Exception:  # noqa: BLE001 - ping 应优雅返回未存活
                    alive = False
                idn = ""
                idn_fn = getattr(instance, "identify_instrument", None)
                if callable(idn_fn):
                    try:
                        idn = str(idn_fn())
                    except Exception:  # noqa: BLE001 - IDN 失败不致命
                        idn = ""
                return {"alive": alive, "idn": idn}
            idn_fn = getattr(instance, "identify_instrument", None)
            if callable(idn_fn):
                try:
                    idn = str(idn_fn())
                    return {"alive": bool(idn), "idn": idn}
                except Exception:  # noqa: BLE001 - ping 应优雅返回未存活
                    return {"alive": False, "idn": ""}
            query_fn = _resolve_query_fn(instance)
            if query_fn is not None:
                try:
                    idn = str(query_fn("*IDN?"))
                    return {"alive": bool(idn), "idn": idn}
                except Exception:  # noqa: BLE001 - ping 应优雅返回未存活
                    return {"alive": False, "idn": ""}
            raise AttributeError(
                "该仪器不支持 ping / identify_instrument / *IDN? 查询。"
            )

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            "仪器连通性检查完成。",
        )

    def get_recent_audit_log(args: dict) -> dict:
        lines = _clamp_lines(args, default=200)
        entries = _read_recent_audit(lines)
        return {
            "lines_returned": len(entries),
            "entries": entries,
            "truncated": len(entries) >= lines,
        }

    def get_app_log_errors(args: dict) -> dict:
        lines = _clamp_lines(args, default=300)
        getter = deps.app_logs_getter
        if getter is None:
            return {
                "lines_returned": 0,
                "logs": [],
                "_message": "日志环形缓冲不可用。",
            }
        window = getter(max(lines * 8, 2000))
        errors = [ln for ln in window if _is_log_error_line(ln)]
        errors = errors[-lines:]
        return {
            "lines_returned": len(errors),
            "logs": errors,
            "truncated": len(errors) >= lines,
        }

    def _session_key() -> str:
        if deps.session_key_getter is not None:
            try:
                return deps.session_key_getter() or ""
            except Exception:  # noqa: BLE001
                logger.error("session_key_getter 调用异常", exc_info=True)
        return ""

    def get_task_result(args: dict) -> dict:
        registry = deps.pending_task_registry
        if registry is None:
            return {"ok": False, "_message": "当前环境不支持异步任务查询。"}
        task_id = str(args.get("task_id", "")).strip()
        if not task_id:
            return {"ok": False, "_message": "缺少 task_id。"}
        task = registry.get(task_id)
        if task is None:
            return {"ok": False, "_message": f"未知 task_id：{task_id}"}
        return {
            "ok": True,
            "task_id": task.task_id,
            "status": task.status,
            "kind": task.kind,
            "result": task.result,
            "_message": f"任务 {task_id} 当前状态：{task.status}。",
        }

    def list_pending_tasks(_args: dict) -> dict:
        registry = deps.pending_task_registry
        if registry is None:
            return {"ok": False, "_message": "当前环境不支持异步任务查询。"}
        tasks = registry.list(session_key=_session_key() or None)
        return {
            "ok": True,
            "count": len(tasks),
            "tasks": tasks,
            "_message": f"当前共有 {len(tasks)} 个异步任务。",
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
        "get_instrument_errors": get_instrument_errors,
        "run_instrument_selftest": run_instrument_selftest,
        "ping_instrument": ping_instrument,
        "get_recent_audit_log": get_recent_audit_log,
        "get_app_log_errors": get_app_log_errors,
        "get_task_result": get_task_result,
        "list_pending_tasks": list_pending_tasks,
    }
