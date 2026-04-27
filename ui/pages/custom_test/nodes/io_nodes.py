"""记录/导出节点"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from log_config import get_logger
from ui.pages.custom_test.nodes.base_node import BaseNode, register_node

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
         "default": "custom_test_result"},
        {"key": "output_dir", "label": "输出目录", "type": "str", "default": ""},
    ]

    def execute(self, context: Any) -> None:
        fmt = str(context.resolve_value(self.params["format"])).lower()
        filename = str(context.resolve_value(self.params["filename"]))
        output_dir = str(context.resolve_value(self.params["output_dir"])).strip()

        if not output_dir:
            if getattr(sys, 'frozen', False):
                project_root = os.path.dirname(sys.executable)
            else:
                project_root = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )))
                )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(project_root, "Results", "custom_test", timestamp)

        os.makedirs(output_dir, exist_ok=True)

        records = context.records
        if not records:
            logger.warning("没有数据可导出")
            return

        all_keys: List[str] = []
        seen = set()
        for row in records:
            for k in row.keys():
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)

        if fmt == "csv":
            filepath = os.path.join(output_dir, f"{filename}.csv")
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=all_keys)
                writer.writeheader()
                writer.writerows(records)
            logger.info("已导出 CSV: %s (%d 行)", filepath, len(records))

        elif fmt == "excel":
            filepath = os.path.join(output_dir, f"{filename}.xlsx")
            try:
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Results"
                ws.append(all_keys)
                for row in records:
                    ws.append([row.get(k, "") for k in all_keys])
                wb.save(filepath)
                logger.info("已导出 Excel: %s (%d 行)", filepath, len(records))
            except ImportError:
                logger.warning("openpyxl 未安装，回退为 CSV 导出")
                filepath = os.path.join(output_dir, f"{filename}.csv")
                with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=all_keys)
                    writer.writeheader()
                    writer.writerows(records)
                logger.info("已导出 CSV (fallback): %s", filepath)

        context.set_variable("_export_path", filepath)
        context.set_variable("_export_dir", output_dir)


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
