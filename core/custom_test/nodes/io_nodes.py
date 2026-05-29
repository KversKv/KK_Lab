"""记录/导出节点"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Dict

from log_config import get_logger
from core.custom_test.nodes.base import BaseNode, register_node
from core.custom_test.result_store import build_default_result_path

logger = get_logger(__name__)


@register_node
class RecordDataPoint(BaseNode):
    """记录一行数据到结果集"""

    node_type = "RecordDataPoint"
    display_name = "Record Data"
    category = "io"
    icon = "◉"
    color = "#2ecc71"

    PARAM_SCHEMA = [
        {"key": "fields", "label": "字段映射 (auto=按导出顺序, 或 key=val)", "type": "str",
         "default": "auto"},
        {"key": "skip_no_export", "label": "跳过未导出的变量", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        raw = str(self.params["fields"]).strip()
        skip_no_export = bool(context.resolve_value(self.params.get("skip_no_export", True)))
        row: Dict[str, Any] = {}

        if raw.lower() == "auto" or raw == "":
            row = context.get_export_vars_ordered()
        elif raw.startswith("{"):
            import json
            try:
                template = json.loads(raw)
                for k, v in template.items():
                    resolved = context.resolve_value(v)
                    if isinstance(resolved, (list, tuple)):
                        resolved = resolved[-1] if resolved else None
                    row[k] = resolved
            except Exception:
                pass
        else:
            import re
            var_pat = re.compile(r"^\$\{(\w+)\}$")
            pairs = [p.strip() for p in raw.split(",")]
            for pair in pairs:
                if "=" not in pair:
                    continue
                key, val = pair.split("=", 1)
                val = val.strip()
                m = var_pat.match(val)
                if m and skip_no_export and not context.is_export_var(m.group(1)):
                    continue
                resolved = context.resolve_value(val)
                if isinstance(resolved, (list, tuple)):
                    resolved = resolved[-1] if resolved else None
                row[key.strip()] = resolved

        context.record_data(row)
        logger.info("RecordDataPoint: %s", row)


@register_node
class ExportResult(BaseNode):
    """导出结果到 CSV/Excel"""

    node_type = "ExportResult"
    display_name = "Export Result"
    category = "io"
    icon = "⇧"
    color = "#e67e22"

    PARAM_SCHEMA = [
        {"key": "format", "label": "导出格式", "type": "str", "default": "csv",
         "options": ["csv", "excel"]},
        {"key": "filename", "label": "文件名（不含后缀）", "type": "str",
         "default": ""},
        {"key": "output_dir", "label": "输出目录", "type": "str", "default": ""},
    ]

    def execute(self, context: Any) -> None:
        fmt = str(context.resolve_value(self.params["format"])).lower()
        filename = str(context.resolve_value(self.params["filename"]))
        output_dir = str(context.resolve_value(self.params["output_dir"])).strip()
        extension = "xlsx" if fmt in ("xlsx", "excel") else "csv"

        if not output_dir:
            if getattr(sys, 'frozen', False):
                project_root = os.path.dirname(sys.executable)
            else:
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )))
                )
            if not filename or filename == "custom_test_result":
                profile = str(context.get_variable("chip", context.get_variable("profile", "default")))
                filepath = build_default_result_path(
                    project_root,
                    chip_or_profile=profile,
                    fmt=extension,
                )
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = os.path.join(project_root, "Results", "custom_test", timestamp)
                filepath = os.path.join(output_dir, f"{filename}.{extension}")
        else:
            filepath = os.path.join(output_dir, f"{filename or 'custom_test_result'}.{extension}")

        if not context.records:
            logger.warning("没有数据可导出")
            return

        manifest = context.result_store.build_manifest(
            sequence_hash=getattr(context, "sequence_hash", ""),
            instrument_snapshot=_instrument_manifest(context),
            started_at=getattr(context, "run_started_at", None),
            finished_at=getattr(context, "run_finished_at", None),
            run_id=getattr(context, "run_id", ""),
            status=getattr(context, "run_status", ""),
        )
        try:
            filepath = context.result_store.export(
                filepath,
                fmt=fmt,
                view=False,
                manifest=manifest,
            )
        except RuntimeError:
            if fmt in ("excel", "xlsx"):
                logger.warning("XLSX 导出失败，回退为 CSV", exc_info=True)
                filepath = os.path.splitext(filepath)[0] + ".csv"
                filepath = context.result_store.export(
                    filepath,
                    fmt="csv",
                    view=False,
                    manifest=manifest,
                )
            else:
                raise
        logger.info("已导出结果: %s (%d 行)", filepath, len(context.records))

        context.set_variable("_export_path", filepath)
        context.set_variable("_export_dir", os.path.dirname(filepath))


def _instrument_manifest(context: Any) -> Dict[str, Dict[str, str]]:
    resolved = getattr(context, "resolved_instruments", None)
    if resolved is None:
        return {}
    instruments = getattr(resolved, "instruments", {})
    return {
        key: {
            "source": getattr(item, "source", ""),
            "session_id": getattr(item, "session_id", ""),
            "display_name": getattr(item, "display_name", ""),
        }
        for key, item in instruments.items()
    }


@register_node
class PrintLog(BaseNode):

    node_type = "PrintLog"
    display_name = "Print Log"
    category = "io"
    icon = "✎"
    color = "#3498db"

    PARAM_SCHEMA = [
        {"key": "message", "label": "日志消息 (支持 ${var} 表达式)", "type": "str",
         "default": "当前值: ${value}"},
        {"key": "level", "label": "日志级别", "type": "str", "default": "INFO",
         "options": ["INFO", "WARNING", "ERROR"]},
    ]

    def execute(self, context: Any) -> None:
        raw_message = str(self.params["message"])
        level = str(context.resolve_value(self.params.get("level", "INFO"))).upper()
        message = str(context.resolve_value(raw_message))

        if level not in ("INFO", "WARNING", "ERROR"):
            level = "INFO"

        tag = {"INFO": "INFO", "WARNING": "WARN", "ERROR": "ERROR"}.get(level, "INFO")
        formatted = f"[{tag}] {message}"

        if level == "ERROR":
            logger.error("PrintLog: %s", message)
        elif level == "WARNING":
            logger.warning("PrintLog: %s", message)
        else:
            logger.info("PrintLog: %s", message)

        context.log_output(formatted)
