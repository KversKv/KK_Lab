"""报告对外 API：HTML 生成 / 打印变体 / 落盘（原 report.py API 段）。"""
from __future__ import annotations

import html
import json
import os

from log_config import get_logger

import debug_config

from core.module_test.result_model import ModuleTestResult
from core.module_test.xlsx_export import export_items_xlsx_dir
from core.module_test.pdf_export import export_pdf_from_html
from core.module_test.report.data import build_report_data
from core.module_test.report.template import _HEAD_COMMENT, _TEMPLATE

logger = get_logger(__name__)


def build_module_html_report(result: ModuleTestResult,
                             xlsx_map: dict[str, str] | None = None) -> str:
    """生成工程级单文件 HTML 报告字符串（数据=REPORT_DATA JSON，视图=原生JS）。"""
    data = build_report_data(result, xlsx_map=xlsx_map)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = data["meta"]["report_title"]
    return (_TEMPLATE
            .replace("__TITLE__", html.escape(title))
            .replace("__HEAD_COMMENT__", _HEAD_COMMENT)
            .replace("__REPORT_DATA__", payload))


def _to_print_variant(html_text: str) -> str:
    """由最终 HTML 派生打印专用变体（无头打印用，不写盘，见 pdf_export）。

    - ``@media print{`` → ``@media all{``：打印版式提为基础版式，加载即按
      打印布局排版，打印时同版式分页，无重排失真；
    - 注入 ``body{width:180mm}``：锁版心宽 = A4 − 15mm×2 边距，drawChart
      按 clientWidth 画死像素的 SVG 一次即按最终打印宽度绘制；
    - 注入 ``window.__KK_PRINT__``：boot 同步 preparePrint 全量渲染（图表
      懒渲染 + beforeprint 在 headless --print-to-pdf 下触发不可靠）。
    模板中三个锚点均唯一（REPORT_DATA 内 "</" 已转义为 "<\\/"）。
    """
    out = html_text.replace("@media print{", "@media all{", 1)
    out = out.replace("</style>",
                      "</style>\n<style>body{width:180mm;margin:0 auto}</style>",
                      1)
    return out.replace(
        "<script>", "<script>window.__KK_PRINT__=1;</script>\n<script>", 1)


def save_html_report(result: ModuleTestResult,
                     out_dir: str) -> tuple[str, str | None]:
    """生成 HTML 报告并落盘，返回 ``(html_path, pdf_path)``。

    同时在 ``out_dir/XLSX/`` 下为每个有内容的测试项生成独立 XLSX
    （数据表 + 截图/波形入单元格；best-effort，失败不影响报告）。
    ``debug_config.REPORT_PDF_EXPORT`` 开启时再经系统 Edge/Chrome 无头打印
    打印变体（``_to_print_variant``）追加 ``report.pdf``（全量数据 +
    原尺寸截图；best-effort，关闭或失败时 pdf_path 为 None）。
    """
    os.makedirs(out_dir, exist_ok=True)
    xlsx_map = export_items_xlsx_dir(result, out_dir)
    path = os.path.join(out_dir, "report.html")
    html_text = build_module_html_report(result, xlsx_map=xlsx_map)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_text)
    logger.info("模块测试报告已生成: %s", path)
    pdf_path = None
    if getattr(debug_config, "REPORT_PDF_EXPORT", False):
        try:
            pdf_path = export_pdf_from_html(
                path, os.path.join(out_dir, "report.pdf"),
                html_text=_to_print_variant(html_text))
        except Exception:  # noqa: BLE001 - PDF 导出失败不影响 HTML/XLSX 报告
            logger.warning("PDF 报告导出失败（不影响 HTML 报告）", exc_info=True)
    return path, pdf_path
