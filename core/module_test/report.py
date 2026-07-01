"""Module Test 报告构建（HTML 主 + CSV 已由 items 落盘）。

规划 §7.2：参照 orchestrator/reports.py 的 build_html_report 风格，
含标题、元信息、逐项 PASS/FAIL 表、关键数值、内嵌波形图（base64 或文件链接）。
UI 只拿路径打开，不做 IO——本模块纯字符串生成，禁依赖 Qt。
"""
from __future__ import annotations

import base64
import html
import os
from datetime import datetime
from typing import Any

from core.module_test.result_model import ItemResult, ModuleTestResult


def _verdict_badge(passed: bool | None) -> str:
    if passed is True:
        return '<span class="badge pass">PASS</span>'
    if passed is False:
        return '<span class="badge fail">FAIL</span>'
    return '<span class="badge norec">N/A</span>'


def _measured_to_rows(measured: Any) -> list[list[str]]:
    """把 measured（dict 或 list[dict]）渲染为二维表格行。"""
    if measured is None:
        return []
    if isinstance(measured, dict):
        return [[k, str(v)] for k, v in measured.items()]
    if isinstance(measured, list) and measured and isinstance(measured[0], dict):
        keys: list[str] = []
        for row in measured:
            for k in row:
                if k not in keys:
                    keys.append(k)
        return [keys] + [[str(row.get(k, "")) for k in keys] for row in measured]
    return [["value", str(measured)]]


def _embed_image(path: str | None) -> str:
    """把波形 PNG 内嵌为 base64（找不到文件则返回空）。"""
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f'<img class="wave" alt="waveform" src="data:image/png;base64,{data}"/>'
    except Exception:  # noqa: BLE001 - 内嵌失败不影响报告生成
        return ""


def build_module_html_report(result: ModuleTestResult) -> str:
    """生成 HTML 报告字符串。"""
    summary = result.build_summary()
    title = f"Module Test Report — {result.module_type.upper()}"

    meta_rows = [
        ("模块类型", result.module_type.upper()),
        ("芯片名称", result.chip_name or "-"),
        ("操作员", result.operator or "-"),
        ("温度点", result.temperature or "-"),
        ("开始时间", result.started_at or "-"),
        ("结束时间", result.finished_at or "-"),
        ("总体结论", summary.get("overall", "N/A")),
        ("统计", f"PASS {summary.get('pass', 0)} / FAIL {summary.get('fail', 0)} / "
                 f"N/A {summary.get('norec', 0)} / 共 {summary.get('total', 0)}"),
    ]
    meta_html = "<table class='meta'><tbody>" + "".join(
        f"<tr><th>{html.escape(k)}</th><td>{html.escape(str(v))}</td></tr>"
        for k, v in meta_rows
    ) + "</tbody></table>"

    item_blocks: list[str] = []
    for idx, it in enumerate(result.items, 1):
        rows = _measured_to_rows(it.measured)
        if rows:
            head = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
            body = "".join(
                "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>"
                for r in rows[1:]
            )
            table = f"<table class='data'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
        else:
            table = "<p class='empty'>无测量数据。</p>"

        img = _embed_image(it.waveform_png)
        csv_link = (
            f"<div class='csv'>原始数据：{html.escape(os.path.basename(it.raw_csv_path))}</div>"
            if it.raw_csv_path else ""
        )
        item_blocks.append(f"""
<section class='item'>
  <h3>{idx}. {html.escape(it.name)} {_verdict_badge(it.passed)}</h3>
  <div class='itemkey'>item_key: {html.escape(it.item_key)} | 单位: {html.escape(it.unit or '-')}</div>
  {table}
  {img}
  {csv_link}
  {f"<div class='notes'>备注：{html.escape(it.notes)}</div>" if it.notes else ""}
</section>""")

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 24px; color: #172033; }}
    h1 {{ margin: 0 0 8px; font-size: 22px; }}
    h2 {{ margin-top: 24px; font-size: 16px; border-bottom: 2px solid #d6deeb; padding-bottom: 4px; }}
    h3 {{ margin: 16px 0 6px; font-size: 14px; }}
    .generated {{ color: #6b7a99; font-size: 12px; margin-bottom: 16px; }}
    table {{ border-collapse: collapse; width: 100%; font-size: 12px; margin: 6px 0; }}
    th, td {{ border: 1px solid #d6deeb; padding: 6px 8px; text-align: left; }}
    th {{ background: #edf2fb; }}
    table.meta {{ width: auto; }}
    table.meta th {{ width: 120px; }}
    .badge {{ display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 11px; font-weight: 700; }}
    .badge.pass {{ background: #d4edda; color: #155724; }}
    .badge.fail {{ background: #f8d7da; color: #721c24; }}
    .badge.norec {{ background: #e2e3e5; color: #383d41; }}
    .item {{ border: 1px solid #e3e8f0; border-radius: 6px; padding: 10px 14px; margin: 12px 0; background: #fbfcfe; }}
    .itemkey {{ color: #6b7a99; font-size: 11px; margin-bottom: 6px; }}
    .wave {{ max-width: 100%; border: 1px solid #d6deeb; margin: 6px 0; }}
    .csv, .notes {{ font-size: 11px; color: #4a5a7a; margin-top: 4px; }}
    .empty {{ color: #6b7a99; font-size: 12px; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <div class="generated">生成时间：{generated}</div>
  <h2>元信息</h2>
  {meta_html}
  <h2>测试项明细（共 {len(result.items)} 项）</h2>
  {''.join(item_blocks) if item_blocks else '<p class="empty">无测试项。</p>'}
</body>
</html>
"""


def save_html_report(result: ModuleTestResult, out_dir: str) -> str:
    """生成 HTML 报告并落盘，返回文件路径。"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_module_html_report(result))
    return path
