"""Module Test 报告构建（HTML 主 + CSV 已由 items 落盘）。

规划 §7.2：参照 orchestrator/reports.py 的 build_html_report 风格，
含标题、元信息、逐项 PASS/FAIL 表、关键数值、内嵌波形图（base64 或文件链接）。
UI 只拿路径打开，不做 IO——本模块纯字符串生成，禁依赖 Qt。
"""
from __future__ import annotations

import base64
import csv
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


def _csv_to_rows(path: str | None) -> list[list[str]]:
    """读取原始数据 CSV（utf-8-sig），返回含表头的二维行；失败返回空。"""
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as f:
            return [row for row in csv.reader(f) if row]
    except Exception:  # noqa: BLE001 - 读取失败不影响报告生成
        return []


def _rows_to_table(rows: list[list[str]], css_class: str = "data") -> str:
    """把二维行渲染为 HTML 表格（首行作表头）。"""
    if not rows:
        return ""
    head = "".join(f"<th>{html.escape(c)}</th>" for c in rows[0])
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>"
        for r in rows[1:]
    )
    return (f"<table class='{css_class}'><thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table>")


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


def _f(value: Any) -> str | None:
    """转浮点字符串；失败返回 None。"""
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return None


def _in(dict_val: dict, *keys: str) -> str:
    """从 dict 按 keys 顺序取首个非 None 值并格式化。"""
    for k in keys:
        s = _f(dict_val.get(k))
        if s is not None:
            return s
    return "-"


def _summary_metrics(it: ItemResult) -> str:
    """按测试项语义生成汇总指标（measured / 内嵌 CSV 推导）。

    各测试项定制字段，缺失自动降级；异常点 = 相邻点变化 >5×|中位步进|。
    """
    key = it.item_key
    m = it.measured if isinstance(it.measured, dict) else {}
    csv = _csv_to_rows(it.raw_csv_path)
    body = csv[1:] if len(csv) > 1 else []

    if key.endswith("vout_scan"):
        default_mv = _f(m.get("default_voltage_mv"))
        vmin_mv = _f(m.get("vout_min_mv"))
        vmax_mv = _f(m.get("vout_max_mv"))
        step_mv = _f(m.get("step_mv"))
        if csv and len(csv[0]) >= 2:  # CSV 兜底
            try:
                vs = [float(r[1]) for r in body if len(r) > 1 and r[1] != ""]
                if vs:
                    vmin_mv = vmin_mv or f"{min(vs):g}"
                    vmax_mv = vmax_mv or f"{max(vs):g}"
            except (TypeError, ValueError):
                pass
        parts = [
            f"Default={default_mv or '-'} mV",
            f"Min={vmin_mv or '-'} mV",
            f"Max={vmax_mv or '-'} mV",
            f"Avg_Step={step_mv or '-'} mV",
        ]
        anomalies = 0
        if csv and len(csv[0]) >= 3 and len(body) > 2:
            try:
                diffs = sorted(abs(float(r[2])) for r in body[1:]
                               if len(r) > 2 and r[2] != "")
                if diffs:
                    med = diffs[len(diffs) // 2]
                    if med > 1e-9:
                        anomalies = sum(1 for r in body[1:]
                                        if len(r) > 2 and r[2] != ""
                                        and abs(float(r[2])) > 5.0 * med)
            except (TypeError, ValueError):
                anomalies = 0
        parts.append("无异常点" if anomalies == 0 else f"异常点 {anomalies}")
        return "; ".join(parts)

    if key.endswith("load_reg"):
        drop_mv = _f(m.get("vout_drop_mv"))
        pct = "-"
        curve = "-"
        if csv and len(csv[0]) >= 2 and body:
            try:
                v0 = float(body[0][1])
                v1 = float(body[-1][1])
                i0 = float(body[0][0])
                i1 = float(body[-1][0])
                if abs(v0) > 1e-9:
                    pct = f"{(v1 - v0) / v0 * 100.0:.3f}"
                if drop_mv is None:
                    drop_mv = f"{v1 - v0:g}"
                curve = f"{i0:g}→{i1:g} mA: {v0:g}→{v1:g} mV"
            except (TypeError, ValueError, IndexError):
                pass
        return f"LoadReg={pct} %; ΔV={drop_mv or '-'} mV; {curve}"

    if key.endswith("line_reg"):
        span_mv = _f(m.get("vout_span_mv"))
        pct = "-"
        curve = "-"
        if csv and len(csv[0]) >= 2 and body:
            try:
                vs = [float(r[1]) for r in body if len(r) > 1]
                vins = [float(r[0]) for r in body if len(r) > 1]
                if vs:
                    if span_mv is None:
                        span_mv = f"{max(vs) - min(vs):g}"
                    mean_v = sum(vs) / len(vs)
                    if abs(mean_v) > 1e-9:
                        pct = f"{(max(vs) - min(vs)) / mean_v * 100.0:.3f}"
                    curve = f"{min(vins):g}→{max(vins):g} V: {min(vs):g}→{max(vs):g} mV"
            except (TypeError, ValueError, IndexError):
                pass
        return f"LineReg={pct} %; ΔV={span_mv or '-'} mV; {curve}"

    if key.endswith("efficiency"):
        max_eff = _f(m.get("max_eff"))
        avg_eff = _f(m.get("avg_eff"))
        at = "-"
        if csv and len(csv[0]) >= 3 and body:
            try:
                peak = max(body, key=lambda r: float(r[2]))
                at = f"@ {float(peak[0]):g} mA"
                if max_eff is None:
                    max_eff = f"{float(peak[2]):g}"
                if avg_eff is None:
                    avg_eff = f"{sum(float(r[2]) for r in body) / len(body):g}"
            except (TypeError, ValueError, IndexError):
                pass
        return f"Max η={max_eff or '-'} % {at}; Avg η={avg_eff or '-'} %"

    if key.endswith("quiescent"):
        rows = it.measured if isinstance(it.measured, list) else []
        parts = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            mode = r.get("Mode", "?")
            iq = r.get("Iq (uA)", r.get("Iq (A)", "-"))
            parts.append(f"{mode}: {iq} uA")
        return "; ".join(parts) if parts else "-"

    if key.endswith("ripple"):
        return f"Vpp={_in(m, 'vpp_mv')} mV; RMS={_in(m, 'rms_mv')} mV"

    if key.endswith("dropout"):
        return (f"Dropout={_in(m, 'dropout_mv')} mV "
                f"@ Iload={_in(m, 'iload_ma')} mA; V0={_in(m, 'v0_mv')} mV")

    if key.endswith("current_limit"):
        return (f"Limit={_in(m, 'current_limit_ma')} mA; "
                f"Peak={_in(m, 'peak_current_ma')} mA")

    if key.endswith("vout_accuracy"):
        return (f"InitErr={_in(m, 'init_error_pct')} %; "
                f"Tempco={_in(m, 'tempco_ppm_c')} ppm/°C")

    if key.endswith("output_noise"):
        return f"Noise={_in(m, 'noise_uv_rms')} uVrms"

    if key.endswith("vin_range"):
        return f"Vin={_in(m, 'vin_min_v')} ~ {_in(m, 'vin_max_v')} V"

    if key.endswith("output_power"):
        return f"Pout_max={_in(m, 'pout_max_mw')} mW"

    if key.endswith("switching_freq"):
        return f"fsw={_in(m, 'fsw_khz')} kHz"

    if key.endswith("shutdown_current"):
        return f"Ish={_in(m, 'shutdown_current_ua')} uA"

    if key.endswith("startup"):
        return (f"SoftStart={_in(m, 'soft_start_ms')} ms; "
                f"Overshoot={_in(m, 'overshoot_mv')} mV")

    if key.endswith("topology"):
        topo = m.get("topology", "-")
        iso = m.get("isolated")
        return f"{topo} ({'隔离' if iso else '非隔离'})"

    if key.endswith("stability"):
        return f"PM={_in(m, 'phase_margin_deg')} °"

    if isinstance(it.measured, dict):  # 通用兜底
        parts = [f"{k}={v}" for k, v in list(it.measured.items())[:4]]
        return "; ".join(parts) if parts else "-"
    if isinstance(it.measured, list):
        return f"{len(it.measured)} 行数据"
    return "-"


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

    summary_rows = "".join(
        "<tr>"
        f"<td>{idx}</td>"
        f"<td>{html.escape(it.name)}</td>"
        f"<td>{_verdict_badge(it.passed)}</td>"
        f"<td>{html.escape(_summary_metrics(it))}</td>"
        f"<td>{html.escape(it.notes or '-')}</td>"
        "</tr>"
        for idx, it in enumerate(result.items, 1)
    )
    summary_table = (
        "<table class='data summary'><thead><tr>"
        "<th>#</th><th>测试项</th><th>结论</th><th>主要性能</th><th>备注</th>"
        f"</tr></thead><tbody>{summary_rows}</tbody></table>"
        if result.items else "<p class='empty'>无测试项。</p>"
    )

    item_blocks: list[str] = []
    for idx, it in enumerate(result.items, 1):
        rows = _measured_to_rows(it.measured)
        if rows:
            table = f"<h4>关键测量值</h4>{_rows_to_table(rows)}"
        else:
            table = "<p class='empty'>无测量数据。</p>"

        csv_rows = _csv_to_rows(it.raw_csv_path)
        full_table = ""
        if csv_rows:
            csv_name = html.escape(os.path.basename(it.raw_csv_path or ""))
            full_table = f"<h4>完整测试数据（{csv_name}）</h4>{_rows_to_table(csv_rows)}"

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
  {full_table}
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
    h4 {{ margin: 10px 0 4px; font-size: 12px; color: #4a5a7a; }}
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
  <h2>测试结论汇总</h2>
  {summary_table}
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
