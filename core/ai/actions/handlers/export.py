"""数据导出与产物类动作 handlers（AIAssist_ActionCatalog.md §5.7 P6）。

新增 category=export，统一管理 AI 落盘产物（截图 / Datalog CSV / 波形 CSV）：
  save_scope_screenshot  : medium，截取已连接示波器屏幕 PNG 导出到指定目录；
  export_datalog_csv     : medium，把当前 Datalog 页内存数据导出为合并 CSV
                           （经 UI 注入的 datalog_export_callback，非交互）；
  export_waveform_csv    : low，把指定通道 [t0, t1] 片段导出为 CSV
                           （经 waveform_full_data_getter 取全量数据 + slice_channel_fast 切片）；
  get_artifact_list      : low，列出本次会话产生的所有产物路径与元信息。

产物路径安全（AIAssist_ActionCatalog.md §5.7 / §6）：
  - 导出目录限定在用户数据目录（user_data/ 或打包态 %APPDATA%/KK_Lab/）之下，
    禁止任意路径写入与路径穿越；dir 留空则用默认 ai/exports/；
  - 二进制/大产物只回灌「路径 + 元信息 + artifact_id」，不回灌内容本身
    （防撑爆 token），内容经 artifact_registry 句柄登记供后续引用。

示波器截图复用 instrument 模块的 _run_read_action 骨架（capture_screen_png 为只读）。
本模块禁 import Qt。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.handlers.instrument import _run_read_action
from core.ai.actions.registry import CATEGORY_EXPORT, ActionSpec
from log_config import get_logger
from ui.resource_path import get_user_data_dir

logger = get_logger(__name__)


SPECS: list[ActionSpec] = [
    ActionSpec(
        name="save_scope_screenshot",
        description=(
            "截取已连接示波器屏幕 PNG 并导出到指定目录（默认用户数据目录下 ai/exports/），"
            "返回文件路径/字节数/产物句柄。dir 须位于用户数据目录下，留空用默认。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "dir": {
                    "type": "string",
                    "description": "导出目录（须位于用户数据目录下，留空则用默认 ai/exports/）。",
                },
            },
            "required": ["session_id"],
        },
        risk_level="medium",
        category=CATEGORY_EXPORT,
    ),
    ActionSpec(
        name="export_datalog_csv",
        description=(
            "把当前 Datalog 页面内存中的波形数据导出为合并 CSV（可见通道的时间+值），"
            "返回路径/行数/通道数/产物句柄。须在 Datalog 页面调用；"
            "session_id 可选用于审计追溯；dir 须位于用户数据目录下，留空用默认。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "N6705C 会话标识（可选，用于审计追溯）。",
                },
                "dir": {
                    "type": "string",
                    "description": "导出目录（须位于用户数据目录下，留空则用默认 ai/exports/）。",
                },
            },
        },
        risk_level="medium",
        category=CATEGORY_EXPORT,
    ),
    ActionSpec(
        name="export_waveform_csv",
        description=(
            "把指定通道在 [t0, t1] 时间窗内的波形片段导出为 CSV（time_s,value 两列），"
            "返回路径/点数/产物句柄。dir 须位于用户数据目录下，留空用默认。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "通道标签，如 'CH1 I'。"},
                "t0": {"type": "number", "description": "时间窗起点（秒）。"},
                "t1": {"type": "number", "description": "时间窗终点（秒）。"},
                "dir": {
                    "type": "string",
                    "description": "导出目录（须位于用户数据目录下，留空则用默认 ai/exports/）。",
                },
            },
            "required": ["label", "t0", "t1"],
        },
        risk_level="low",
        category=CATEGORY_EXPORT,
    ),
    ActionSpec(
        name="get_artifact_list",
        description=(
            "列出本次 AI 会话产生的所有产物（截图/CSV 等）的路径与元信息"
            "（artifact_id/kind/path/label/bytes/created_at），便于后续查看或引用。"
        ),
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_EXPORT,
    ),
]


def _safe_name(name: str) -> str:
    """把任意字符串压成文件名安全形式（字母/数字/下划线/连字符）。"""
    keep = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))
    return keep or "ch"


def _resolve_export_dir(dir_arg: str) -> tuple[str | None, str]:
    """解析导出目录（AIAssist_ActionCatalog.md §5.7 P6 路径安全约束）。

    - dir_arg 为空 → 默认 user_data/ai/exports/；
    - dir_arg 非空 → 须解析后落在用户数据根目录之下（防路径穿越/任意写入）。
    返回 (resolved_abs_dir, error)；成功时 error 为空字符串。
    """
    default_dir = get_user_data_dir("ai", "exports")
    raw = (dir_arg or "").strip()
    if not raw:
        return default_dir, ""
    allowed_root = os.path.normpath(get_user_data_dir())
    try:
        candidate = os.path.abspath(os.path.normpath(raw))
    except (ValueError, OSError):
        return None, f"导出目录路径非法：{raw}"
    if not (candidate == allowed_root or candidate.startswith(allowed_root + os.sep)):
        return None, (
            f"导出目录须位于用户数据目录下（{allowed_root}），拒绝任意路径写入：{raw}"
        )
    try:
        os.makedirs(candidate, exist_ok=True)
    except OSError as exc:
        return None, f"无法创建导出目录 {candidate}：{exc}"
    return candidate, ""


def _write_png(out_dir: str, session_id: str, png_data: bytes) -> str:
    safe_sid = _safe_name(session_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"scope_{safe_sid}_{ts}.png")
    with open(path, "wb") as fh:
        fh.write(png_data)
    return path


def _write_waveform_csv(
    out_dir: str, label: str, times: list[float], values: list[float]
) -> str:
    safe = _safe_name(label)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"waveform_{safe}_{ts}.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write("time_s,value\n")
        for t, v in zip(times, values):
            fh.write(f"{t:.6f},{v:.9f}\n")
    return path


def _file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def save_scope_screenshot(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        dir_arg = str(args.get("dir", ""))
        resolved, err = _resolve_export_dir(dir_arg)
        if err:
            return {"ok": False, "_message": err}

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "capture_screen_png", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持截屏。")
            png_data = fn(invert=False)
            if not png_data:
                return {
                    "captured": False,
                    "bytes": 0,
                    "_message": "仪器未返回截图数据（可能是 Mock 模式或采集未就绪）。",
                }
            path = _write_png(resolved, session_id, png_data)
            return {"captured": True, "bytes": len(png_data), "path": path}

        result = _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"示波器 {session_id} 截屏已导出。",
        )
        if not result.get("ok"):
            return result
        path = result.get("path")
        nbytes = int(result.get("bytes", 0))
        artifact_id = None
        if path and deps.artifact_registry is not None:
            artifact_id = deps.artifact_registry.register(
                "scope_screenshot",
                path,
                session_id=session_id,
                bytes=nbytes,
            )
        result["artifact_id"] = artifact_id
        result["dir"] = resolved
        if path:
            result["_message"] = f"截屏已导出：{path}"
        return result

    def export_datalog_csv(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        dir_arg = str(args.get("dir", ""))
        resolved, err = _resolve_export_dir(dir_arg)
        if err:
            return {"ok": False, "_message": err}
        callback = deps.datalog_export_callback
        if callback is None:
            return {
                "ok": False,
                "_message": "当前页面不支持 Datalog CSV 导出（请切到 Datalog 页）。",
            }
        try:
            outcome = callback(session_id, resolved)
        except Exception:  # noqa: BLE001 - 导出异常转可读结果
            logger.error("Datalog CSV 导出失败", exc_info=True)
            return {"ok": False, "_message": "Datalog CSV 导出异常，请查看日志。"}
        if not isinstance(outcome, dict) or not outcome.get("ok"):
            msg = outcome.get("message") if isinstance(outcome, dict) else ""
            return {"ok": False, "_message": msg or "Datalog CSV 导出失败。"}
        path = outcome.get("path", "")
        artifact_id = None
        if path and deps.artifact_registry is not None:
            artifact_id = deps.artifact_registry.register(
                "datalog_csv",
                path,
                session_id=session_id,
                bytes=int(outcome.get("bytes", 0)),
                meta={
                    "rows": outcome.get("rows"),
                    "channels": outcome.get("channels"),
                },
            )
        outcome["artifact_id"] = artifact_id
        outcome["dir"] = resolved
        outcome.setdefault("_message", f"Datalog CSV 已导出：{path}")
        return outcome

    def export_waveform_csv(args: dict) -> dict:
        label = str(args.get("label", "")).strip()
        dir_arg = str(args.get("dir", ""))
        try:
            t0 = float(args.get("t0"))
            t1 = float(args.get("t1"))
        except (TypeError, ValueError):
            return {"ok": False, "_message": "t0/t1 必须为数值。"}
        getter = deps.waveform_full_data_getter
        data = getter() if getter else None
        if not data:
            return {
                "ok": False,
                "_message": "当前无可导出的波形数据（请切到 Datalog 页并加载数据）。",
            }
        if label not in data:
            return {
                "ok": False,
                "available_labels": list(data.keys()),
                "_message": f"通道 '{label}' 不存在，请从 available_labels 选择。",
            }
        resolved, err = _resolve_export_dir(dir_arg)
        if err:
            return {"ok": False, "_message": err}
        from core.ai.providers.waveform_provider import slice_channel_fast

        channel = data[label]
        times = channel.get("time") or []
        values = channel.get("values") or []
        sel_t, sel_v = slice_channel_fast(list(times), list(values), t0, t1)
        if not sel_v:
            return {"ok": False, "_message": f"窗口 [{t0}, {t1}] 内无数据点。"}
        try:
            path = _write_waveform_csv(resolved, label, sel_t, sel_v)
        except OSError as exc:
            logger.error("波形 CSV 写盘失败：%s", exc, exc_info=True)
            return {"ok": False, "_message": f"写盘失败：{exc}"}
        nbytes = _file_size(path)
        artifact_id = None
        if deps.artifact_registry is not None:
            artifact_id = deps.artifact_registry.register(
                "waveform_csv",
                path,
                label=label,
                bytes=nbytes,
                meta={"point_count": len(sel_v), "t0": t0, "t1": t1},
            )
        return {
            "ok": True,
            "path": path,
            "label": label,
            "t0": t0,
            "t1": t1,
            "point_count": len(sel_v),
            "bytes": nbytes,
            "artifact_id": artifact_id,
            "dir": resolved,
            "_message": f"通道 {label} 在 [{t0}, {t1}] 导出 {len(sel_v)} 点：{path}",
        }

    def get_artifact_list(_args: dict) -> dict:
        registry = deps.artifact_registry
        if registry is None:
            return {
                "available": False,
                "artifacts": [],
                "_message": "产物注册表不可用。",
            }
        items = registry.list()
        summary = [
            {
                "artifact_id": it.get("artifact_id"),
                "kind": it.get("kind"),
                "path": it.get("path"),
                "label": it.get("label"),
                "bytes": it.get("bytes"),
                "created_at": it.get("created_at"),
            }
            for it in items
        ]
        return {
            "available": True,
            "count": len(summary),
            "artifacts": summary,
            "_message": f"本次会话共产生 {len(summary)} 个产物。",
        }

    return {
        "save_scope_screenshot": save_scope_screenshot,
        "export_datalog_csv": export_datalog_csv,
        "export_waveform_csv": export_waveform_csv,
        "get_artifact_list": get_artifact_list,
    }
