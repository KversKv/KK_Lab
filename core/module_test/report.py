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


def _measured_to_rows(measured: Any) -> list[list[str]]:
    """把 measured（dict 或 list[dict]）渲染为二维表格行。"""
    if measured is None:
        return []
    if isinstance(measured, dict):
        # screenshots 为示波器逐点截图列表，单独渲染为多图，不进表格
        return [[k, str(v)] for k, v in measured.items() if k != "screenshots"]
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
    return (f"<table><thead><tr>{head}</tr></thead>"
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


def _img_data_uri(path: str | None) -> str:
    """读取 PNG 返回 base64 data URI；失败返回空串。"""
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{data}"
    except Exception:  # noqa: BLE001 - 内嵌失败不影响报告生成
        return ""


def _shots_table_html(csv_rows: list[list[str]], measured: Any) -> str:
    """把逐负载点示波器截图作为最后一列并入数据表，缩略图可点击看原图。

    按 'Iload (mA)' 列把 measured['screenshots'] 的 png 匹配到 CSV 行；
    无截图列时退化为普通表格。
    """
    if not csv_rows:
        return ""
    shots: dict[str, str] = {}
    if isinstance(measured, dict) and isinstance(measured.get("screenshots"), list):
        for s in measured["screenshots"]:
            if isinstance(s, dict):
                uri = _img_data_uri(s.get("png"))
                if uri:
                    shots[str(s.get("Iload (mA)", "")).strip()] = uri

    header = list(csv_rows[0])
    try:
        iload_idx = next(i for i, c in enumerate(header)
                         if "iload" in str(c).lower())
    except StopIteration:
        iload_idx = 0
    has_shot = bool(shots)
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in header)
    if has_shot:
        head += "<th>示波器截图</th>"

    body_rows: list[str] = []
    for r in csv_rows[1:]:
        cells = list(r) + [""] * (len(header) - len(r))
        tds = "".join(f"<td>{html.escape(str(c))}</td>" for c in cells[:len(header)])
        if has_shot:
            key = str(cells[iload_idx]).strip()
            uri = shots.get(key)
            if uri:
                cap = f"{header[iload_idx]} = {html.escape(key)}"
                tds += (f"<td class='shotcell'><img class='shot-thumb' "
                        f"src='{uri}' data-full='{uri}' data-cap='{cap}' "
                        f"alt='shot {html.escape(key)}'/></td>")
            else:
                tds += "<td class='shotcell'>-</td>"
        body_rows.append(f"<tr>{tds}</tr>")
    return (f"<table><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody></table>")


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
        # quiescent measured 为 dict：{"dIvin (uA)":.., "dIvout (uA)":.., "Iq (uA)":..}
        iq = _f(m.get("Iq (uA)"))
        divin = _f(m.get("dIvin (uA)"))
        divout = _f(m.get("dIvout (uA)"))
        if iq is not None:
            parts = [f"Iq = {iq} uA"]
            subs = []
            if divin not in (None, ""):
                subs.append(f"dIvin={divin} uA")
            if divout not in (None, ""):
                subs.append(f"dIvout={divout} uA")
            if subs:
                parts.append(f"({' / '.join(subs)})")
            return " ".join(parts)
        # 兜底：list[dict]（多模式）
        rows = it.measured if isinstance(it.measured, list) else []
        lst = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            mode = r.get("Mode", "?")
            v = r.get("Iq (uA)", r.get("Iq (A)", "-"))
            lst.append(f"{mode}: {v} uA")
        return "; ".join(lst) if lst else "-"

    if key.endswith("ripple"):
        # Load Capability & Ripple：负载扫描测纹波
        if "max_vpp_mv" in m:
            return (f"Max Vpp={_in(m, 'max_vpp_mv')} mV "
                    f"@ {_in(m, 'max_vpp_at_ma')} mA; "
                    f"Iload={_in(m, 'i_start_ma')}~{_in(m, 'i_end_ma')} mA "
                    f"(step {_in(m, 'i_step_ma')} mA)")
        return f"Vpp={_in(m, 'vpp_mv')} mV; RMS={_in(m, 'rms_mv')} mV"

    if key.endswith("dropout"):
        if m.get("ok_at_min_vin"):
            return (f"最低 Vin={_in(m, 'vin_lo_v')} V 仍正常 "
                    f"@ Iload={_in(m, 'iload_ma')} mA; V0={_in(m, 'v0_mv')} mV")
        return (f"Dropout={_in(m, 'dropout_mv')} mV "
                f"@ Iload={_in(m, 'iload_ma')} mA; V0={_in(m, 'v0_mv')} mV")

    if key.endswith("current_limit"):
        return (f"Limit={_in(m, 'current_limit_ma')} mA; "
                f"Peak={_in(m, 'peak_current_ma')} mA")

    if key.endswith("output_noise"):
        return (f"Center={_in(m, 'center_freq_khz')} kHz; "
                f"Span={_in(m, 'freq_span_khz')} kHz")

    if key.endswith("switching_freq"):
        # 扫负载变频：自动汇总频率范围（随 Iload 变化）
        rows = it.measured if isinstance(it.measured, list) else []
        freqs: list[float] = []
        for r in rows:
            if isinstance(r, dict):
                v = r.get("Fsw (kHz)")
                try:
                    f = float(v)
                    if f > 0:
                        freqs.append(f)
                except (TypeError, ValueError):
                    continue
        if not freqs and csv and len(csv[0]) >= 2 and body:
            try:
                freqs = [float(r[1]) for r in body
                         if len(r) > 1 and r[1] != "" and float(r[1]) > 0]
            except (TypeError, ValueError):
                freqs = []
        if freqs:
            f0, f1 = min(freqs), max(freqs)
            if abs(f1 - f0) < 1e-9:
                return f"fsw = {f0:g} kHz（恒定）"
            return (f"fsw 范围: {f0:g} ~ {f1:g} kHz "
                    f"（随 Iload 变频，{len(freqs)} 点）")
        return "fsw: 未测得有效值"

    if key.endswith("transient"):
        over = _f(m.get("max_overshoot_mv"))
        under = _f(m.get("max_undershoot_mv"))
        g_over = m.get("max_overshoot_group", "")
        g_under = m.get("max_undershoot_group", "")
        groups = m.get("groups", "")
        parts = []
        if over is not None:
            s = f"最大过冲 = {over} mV"
            if g_over != "":
                s += f"（Group {g_over}）"
            parts.append(s)
        if under is not None:
            s = f"最大欠冲 = {under} mV"
            if g_under != "":
                s += f"（Group {g_under}）"
            parts.append(s)
        if not parts:
            return "-"
        suffix = f"；共 {groups} 组" if groups != "" else ""
        return "；".join(parts) + suffix

    if key.endswith("startup"):
        return (f"SoftStart={_in(m, 'soft_start_ms')} ms; "
                f"Overshoot={_in(m, 'overshoot_mv')} mV")

    if key.endswith("topology"):
        topo = m.get("topology", "-")
        iso = m.get("isolated")
        return f"{topo} ({'隔离' if iso else '非隔离'})"

    if isinstance(it.measured, dict):  # 通用兜底
        parts = [f"{k}={v}" for k, v in list(it.measured.items())[:4]]
        return "; ".join(parts) if parts else "-"
    if isinstance(it.measured, list):
        return f"{len(it.measured)} 行数据"
    return "-"


def _verdict_class(passed: bool | None) -> str:
    if passed is True:
        return "pass"
    if passed is False:
        return "fail"
    return "na"


def _verdict_text(passed: bool | None) -> str:
    if passed is True:
        return "PASS"
    if passed is False:
        return "FAIL"
    return "N/A"


def _chart_spec(it: ItemResult) -> list[dict[str, Any]]:
    """按测试项返回需渲染的折线图规格（ECharts）。"""
    key = it.item_key
    if key.endswith("efficiency"):
        return [{"x": 0, "y": 2, "x_label": "Iload (mA)",
                 "y_label": "Efficiency (%)", "title": "Efficiency vs Iload"}]
    if key.endswith("load_reg"):
        return [{"x": 0, "y": 1, "x_label": "Iload (mA)",
                 "y_label": "Vout (mV)", "title": "Vout vs Iload"}]
    if key.endswith("line_reg"):
        return [{"x": 0, "y": 1, "x_label": "Vin (V)",
                 "y_label": "Vout (mV)", "title": "Vout vs Vin"}]
    if key.endswith("current_limit"):
        return [{"x": 0, "y": 1, "x_label": "Iload (mA)",
                 "y_label": "Vout (mV)", "title": "Vout vs Iload"}]
    if key.endswith("switching_freq"):
        return [{"x": 0, "y": 1, "x_label": "Iload (mA)",
                 "y_label": "Fsw (kHz)", "title": "Fsw vs Iload"}]
    if key.endswith("ripple"):
        return [
            {"x": 0, "y": 1, "x_label": "Iload (mA)",
             "y_label": "Vout (mV)", "title": "Vout vs Iload"},
            {"x": 0, "y": 2, "x_label": "Iload (mA)",
             "y_label": "Vpp (mV)", "title": "Ripple Vpp vs Iload"},
        ]
    if key.endswith("vout_scan"):
        return [{"x": 0, "y": 1, "x_label": "Code",
                 "y_label": "Vout (mV)", "title": "Vout vs Code"}]
    return []


def _chart_data_json(csv_rows: list[list[str]], x_col: int, y_col: int) -> str:
    """把 CSV 两列转成 ECharts data 的 JSON 数组字符串 [[x,y],...]。"""
    import json
    pts: list[list[float]] = []
    for r in csv_rows[1:]:
        try:
            pts.append([float(r[x_col]), float(r[y_col])])
        except (TypeError, ValueError, IndexError):
            continue
    return json.dumps(pts)


def build_module_html_report(result: ModuleTestResult) -> str:
    """生成现代化单文件 HTML 报告字符串。"""
    summary = result.build_summary()
    title = f"Module Test Report — {result.module_type.upper()}"
    overall = summary.get("overall", "N/A")
    overall_cls = {"PASS": "pass", "FAIL": "fail"}.get(overall, "na")

    meta_pairs = [
        ("模块类型", result.module_type.upper()),
        ("芯片名称", result.chip_name or "-"),
        ("操作员", result.operator or "-"),
        ("温度点", result.temperature or "-"),
        ("开始时间", result.started_at or "-"),
        ("结束时间", result.finished_at or "-"),
    ]
    meta_html = "".join(
        f"<div class='meta-item'><div class='meta-k'>{html.escape(k)}</div>"
        f"<div class='meta-v'>{html.escape(str(v))}</div></div>"
        for k, v in meta_pairs
    )
    stat_html = (
        f"<span class='status-badge status-pass'>PASS {summary.get('pass', 0)}</span>"
        f"<span class='status-badge status-fail'>FAIL {summary.get('fail', 0)}</span>"
        f"<span class='status-badge status-na'>N/A {summary.get('norec', 0)}</span>"
        f"<span class='stat-total'>共 {summary.get('total', 0)} 项</span>"
    )

    summary_rows = "".join(
        "<tr>"
        f"<td class='c'>{idx}</td>"
        f"<td><a class='jump' href='#item-{idx}'>{html.escape(it.name)}</a></td>"
        f"<td><span class='status-badge status-{_verdict_class(it.passed)}'>"
        f"{_verdict_text(it.passed)}</span></td>"
        f"<td class='metric'>{html.escape(_summary_metrics(it))}</td>"
        f"<td class='muted'>{html.escape(it.notes or '-')}</td>"
        "</tr>"
        for idx, it in enumerate(result.items, 1)
    )
    summary_table = (
        "<table><thead><tr>"
        "<th>#</th><th>测试项</th><th>结论</th><th>主要性能</th><th>备注</th>"
        f"</tr></thead><tbody>{summary_rows}</tbody></table>"
        if result.items else "<p class='empty'>无测试项。</p>"
    )

    item_blocks: list[str] = []
    charts_js: list[str] = []
    toc_items: list[str] = []
    for idx, it in enumerate(result.items, 1):
        toc_items.append(
            f"<a class='toc-link' href='#item-{idx}' data-target='item-{idx}'>"
            f"<span class='toc-idx'>{idx}</span>"
            f"<span class='toc-dot status-{_verdict_class(it.passed)}'></span>"
            f"<span class='toc-name'>{html.escape(it.name)}</span></a>")
        rows = _measured_to_rows(it.measured)
        if rows:
            key_table = f"<h4>关键测量值</h4>{_rows_to_table(rows)}"
        else:
            key_table = "<p class='empty'>无测量数据。</p>"

        csv_rows = _csv_to_rows(it.raw_csv_path)
        full_table = ""
        if csv_rows:
            csv_name = html.escape(os.path.basename(it.raw_csv_path or ""))
            # 有逐点截图时把截图作为最后一列并入数据表；长表默认折叠
            full_table = (
                f"<details class='fold'><summary>展开完整测试数据"
                f"（{csv_name}，{len(csv_rows) - 1} 行）</summary>"
                f"{_shots_table_html(csv_rows, it.measured)}</details>")

        chart_html = ""
        for ci, spec in enumerate(_chart_spec(it)):
            if not csv_rows:
                break
            data = _chart_data_json(csv_rows, spec["x"], spec["y"])
            if data == "[]":
                continue
            cid = f"chart_{idx}_{ci}"
            chart_html += (f"<h4>{html.escape(spec['title'])}</h4>"
                           f"<div id='{cid}' class='echart'></div>")
            charts_js.append(
                "_mkChart('%s', %s, %s, %s, %s);" % (
                    cid, data,
                    _js_str(spec["x_label"]),
                    _js_str(spec["y_label"]),
                    _js_str(spec["title"])))

        # 截图已并入折叠数据表；仅当无逐点截图时回退显示 waveform_png 单图
        has_shots = (isinstance(it.measured, dict)
                     and bool(it.measured.get("screenshots")))
        img = "" if has_shots else _embed_image(it.waveform_png)
        csv_link = (
            f"<div class='csv'>原始数据：{html.escape(os.path.basename(it.raw_csv_path))}</div>"
            if it.raw_csv_path else ""
        )
        notes = (f"<div class='notes'>备注：{html.escape(it.notes)}</div>"
                 if it.notes else "")
        item_blocks.append(f"""
<div class='report-card item' id='item-{idx}'>
  <div class='item-head'>
    <span class='item-title'>{idx}. {html.escape(it.name)}</span>
    <span class='status-badge status-{_verdict_class(it.passed)}'>{_verdict_text(it.passed)}</span>
  </div>
  <div class='itemkey'>item_key: {html.escape(it.item_key)} &nbsp;|&nbsp; 单位: {html.escape(it.unit or '-')}</div>
  {key_table}
  {chart_html}
  {full_table}
  {img}
  {csv_link}
  {notes}
</div>""")

    toc_html = (
        "<nav id='toc'><div class='toc-title'>目录</div>"
        + "".join(toc_items) + "</nav>"
        if toc_items else ""
    )

    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    charts_block = "\n    ".join(charts_js)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <style>
    :root {{
      --ink: #2b2c34; --muted: #6b7280; --line: #eef1f6;
      --pass-bg: #d3f9d8; --pass-fg: #2b8a3e;
      --fail-bg: #ffe3e3; --fail-fg: #c92a2a;
      --na-bg: #e9ecef; --na-fg: #495057;
      --accent: #1c7ed6;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--ink); background-color: #f4f6f8; margin: 0; padding: 24px;
    }}
    .wrap {{ max-width: 1180px; margin: 0 auto; }}
    h1 {{ margin: 0 0 4px; font-size: 24px; font-weight: 700; letter-spacing: .2px; }}
    .generated {{ color: var(--muted); font-size: 12.5px; margin-bottom: 20px; }}
    .report-card {{
      background: #ffffff; border-radius: 10px; padding: 20px 24px;
      margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }}
    .dash {{ display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; }}
    @media (max-width: 900px) {{ .dash {{ grid-template-columns: 1fr; }} }}
    .dash h2 {{ margin: 0 0 14px; font-size: 15px; font-weight: 700; }}
    .meta-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px 20px; }}
    @media (max-width: 640px) {{ .meta-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    .meta-k {{ font-size: 11.5px; color: var(--muted); margin-bottom: 2px; }}
    .meta-v {{ font-size: 13.5px; font-weight: 600; }}
    .verdict-box {{ display: flex; flex-direction: column; gap: 14px; }}
    .verdict-main {{ display: flex; align-items: center; gap: 12px; }}
    .verdict-main .big {{ font-size: 15px; font-weight: 700; color: var(--muted); }}
    .stat-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
    .stat-total {{ font-size: 12.5px; color: var(--muted); margin-left: 4px; }}
    .status-badge {{
      display: inline-block; padding: 4px 12px; border-radius: 12px;
      font-size: 0.85rem; font-weight: 600; white-space: nowrap;
    }}
    .status-pass {{ background: var(--pass-bg); color: var(--pass-fg); }}
    .status-fail {{ background: var(--fail-bg); color: var(--fail-fg); }}
    .status-na {{ background: var(--na-bg); color: var(--na-fg); }}
    .status-badge.lg {{ padding: 6px 18px; font-size: 1.05rem; border-radius: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }}
    th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid var(--line); }}
    th {{ background-color: #f8f9fa; color: #495057; font-weight: 600; font-size: 12.5px; }}
    tbody tr:hover {{ background-color: #f8f9fa; }}
    td.c {{ text-align: center; color: var(--muted); }}
    td.metric {{ font-variant-numeric: tabular-nums; }}
    td.muted {{ color: var(--muted); }}
    .item-head {{ display: flex; align-items: center; justify-content: space-between;
      gap: 12px; margin-bottom: 4px; }}
    .item-title {{ font-size: 16px; font-weight: 700; }}
    .itemkey {{ color: var(--muted); font-size: 11.5px; margin-bottom: 8px; }}
    h4 {{ margin: 16px 0 6px; font-size: 13px; color: #495057; font-weight: 600; }}
    .echart {{ width: 100%; height: 340px; }}
    .wave {{ max-width: 100%; border: 1px solid var(--line); border-radius: 6px; margin-top: 8px; }}
    details.fold summary {{
      cursor: pointer; color: var(--accent); font-weight: 500; margin: 12px 0;
      font-size: 13px; user-select: none;
    }}
    details.fold summary:hover {{ text-decoration: underline; }}
    details.fold[open] summary {{ margin-bottom: 4px; }}
    td.shotcell {{ text-align: center; }}
    img.shot-thumb {{
      width: 120px; border: 1px solid var(--line); border-radius: 4px;
      cursor: zoom-in; transition: transform .12s ease, box-shadow .12s ease;
    }}
    img.shot-thumb:hover {{ transform: scale(1.06); box-shadow: 0 4px 14px rgba(0,0,0,.18); }}
    #shotbox {{
      display: none; position: fixed; inset: 0; background: rgba(12, 16, 24, 0.88);
      z-index: 999; cursor: zoom-out;
    }}
    #shotbox img {{
      position: absolute; inset: 0; margin: auto; max-width: 94vw; max-height: 92vh;
      border-radius: 6px; box-shadow: 0 12px 48px rgba(0, 0, 0, 0.6);
    }}
    #shotbox .cap {{
      position: absolute; top: 14px; left: 0; right: 0; text-align: center;
      color: #dce7ff; font-size: 14px;
    }}
    .csv, .notes {{ font-size: 12px; color: var(--muted); margin-top: 10px; }}
    .empty {{ color: var(--muted); font-size: 12.5px; }}
    a.jump {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
    a.jump:hover {{ text-decoration: underline; }}
    /* 左侧悬浮目录 */
    #toc {{
      position: fixed; left: 16px; top: 50%; transform: translateY(-50%);
      width: 208px; max-height: 72vh; overflow-y: auto;
      background: rgba(255, 255, 255, 0.96); backdrop-filter: blur(6px);
      border: 1px solid var(--line); border-radius: 10px;
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
      padding: 12px 8px; z-index: 100;
      opacity: 0; visibility: hidden; transition: opacity .25s ease, visibility .25s;
    }}
    #toc.show {{ opacity: 1; visibility: visible; }}
    #toc .toc-title {{
      font-size: 12px; font-weight: 700; color: var(--muted);
      padding: 2px 10px 8px; letter-spacing: 1px;
    }}
    #toc a.toc-link {{
      display: flex; align-items: center; gap: 7px;
      padding: 6px 10px; border-radius: 6px; text-decoration: none;
      color: var(--ink); font-size: 12.5px; line-height: 1.3;
      border-left: 2px solid transparent;
    }}
    #toc a.toc-link:hover {{ background: #f1f5fb; }}
    #toc a.toc-link.active {{
      background: #e7f1fc; border-left-color: var(--accent);
      color: var(--accent); font-weight: 600;
    }}
    #toc .toc-idx {{ color: var(--muted); font-size: 11px; min-width: 16px; text-align: right; }}
    #toc a.toc-link.active .toc-idx {{ color: var(--accent); }}
    #toc .toc-dot {{ width: 7px; height: 7px; border-radius: 50%; flex: none; }}
    #toc .toc-dot.status-pass {{ background: var(--pass-fg); }}
    #toc .toc-dot.status-fail {{ background: var(--fail-fg); }}
    #toc .toc-dot.status-na {{ background: #adb5bd; }}
    #toc .toc-name {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    @media (max-width: 1460px) {{ #toc {{ display: none; }} }}
    @media print {{
      body {{ padding: 0; background: #fff; }}
      .report-card {{ box-shadow: none; border: 1px solid #ddd; page-break-inside: avoid; }}
      details.fold {{ display: block !important; }}
      details.fold:not([open]) > *:not(summary) {{ display: block !important; }}
    }}
  </style>
</head>
<body id="top">
{toc_html}
<div class="wrap">
  <h1>{html.escape(title)}</h1>
  <div class="generated">生成时间：{generated}</div>

  <div class="report-card dash">
    <div>
      <h2>元信息</h2>
      <div class="meta-grid">{meta_html}</div>
    </div>
    <div class="verdict-box">
      <h2>总体结论</h2>
      <div class="verdict-main">
        <span class="status-badge lg status-{overall_cls}">{overall}</span>
      </div>
      <div class="stat-row">{stat_html}</div>
    </div>
  </div>

  <div class="report-card">
    <h2 style="margin:0 0 6px;font-size:15px;">测试结论汇总</h2>
    {summary_table}
  </div>

  <h2 style="font-size:16px;margin:4px 0 14px;">测试项明细（共 {len(result.items)} 项）</h2>
  {''.join(item_blocks) if item_blocks else '<div class="report-card"><p class="empty">无测试项。</p></div>'}
</div>

<div id="shotbox" onclick="this.style.display='none'">
  <div class="cap"></div><img alt="scope shot"/>
</div>

<script>
  function _mkChart(cid, data, xLabel, yLabel, title) {{
    if (typeof echarts === 'undefined') {{ return; }}
    var el = document.getElementById(cid);
    if (!el) {{ return; }}
    var ch = echarts.init(el, null, {{renderer: 'canvas'}});
    ch.setOption({{
      animation: false,
      grid: {{left: 64, right: 24, top: 40, bottom: 52, containLabel: false}},
      title: {{text: title, left: 'center',
               textStyle: {{fontSize: 13, fontWeight: 600, color: '#2b2c34'}}}},
      tooltip: {{
        trigger: 'axis',
        axisPointer: {{type: 'cross'}},
        valueFormatter: function (v) {{ return v; }}
      }},
      xAxis: {{
        type: 'value', name: xLabel, nameLocation: 'middle', nameGap: 30,
        nameTextStyle: {{color: '#495057', fontSize: 12}},
        axisLabel: {{color: '#6b7280'}},
        splitLine: {{lineStyle: {{color: '#eef1f6'}}}}
      }},
      yAxis: {{
        type: 'value', name: yLabel, nameLocation: 'middle', nameGap: 46,
        nameTextStyle: {{color: '#495057', fontSize: 12}},
        axisLabel: {{color: '#6b7280'}},
        splitLine: {{lineStyle: {{color: '#eef1f6'}}}}
      }},
      series: [{{
        type: 'line', data: data, showSymbol: data.length <= 60,
        symbolSize: 6, smooth: false,
        lineStyle: {{width: 2, color: '#1c7ed6'}},
        itemStyle: {{color: '#1c7ed6'}},
        emphasis: {{focus: 'series'}}
      }}]
    }});
    window.addEventListener('resize', function () {{ ch.resize(); }});
  }}

  {charts_block}

  (function () {{
    var box = document.getElementById('shotbox');
    var img = box.querySelector('img');
    var cap = box.querySelector('.cap');
    document.querySelectorAll('img.shot-thumb').forEach(function (t) {{
      t.addEventListener('click', function () {{
        img.src = t.getAttribute('data-full') || t.src;
        cap.textContent = t.getAttribute('data-cap') || '';
        box.style.display = 'block';
      }});
    }});
    document.addEventListener('keydown', function (e) {{
      if (e.key === 'Escape') {{ box.style.display = 'none'; }}
    }});
  }})();

  /* 悬浮目录：滚过汇总区后显示，滚动时高亮当前测试项 */
  (function () {{
    var toc = document.getElementById('toc');
    if (!toc) {{ return; }}
    var links = Array.prototype.slice.call(toc.querySelectorAll('a.toc-link'));
    var detailHead = null;
    document.querySelectorAll('h2').forEach(function (h) {{
      if (!detailHead && h.textContent.indexOf('测试项明细') === 0) {{ detailHead = h; }}
    }});
    function threshold() {{
      return detailHead ? detailHead.getBoundingClientRect().top
                        + window.pageYOffset - 80 : 300;
    }}
    function currentId() {{
      var pos = window.pageYOffset + 140, id = null;
      document.querySelectorAll('.item[id]').forEach(function (el) {{
        if (el.getBoundingClientRect().top + window.pageYOffset <= pos) {{
          id = el.id;
        }}
      }});
      return id;
    }}
    var ticking = false;
    function onScroll() {{
      if (ticking) {{ return; }}
      ticking = true;
      window.requestAnimationFrame(function () {{
        toc.classList.toggle('show', window.pageYOffset > threshold());
        var id = currentId();
        links.forEach(function (l) {{
          l.classList.toggle('active', l.getAttribute('data-target') === id);
        }});
        ticking = false;
      }});
    }}
    window.addEventListener('scroll', onScroll, {{passive: true}});
    window.addEventListener('resize', onScroll);
    onScroll();
  }})();
</script>
</body>
</html>
"""


def _js_str(s: str) -> str:
    """转成 JS 字符串字面量（双引号 + 转义）。"""
    import json
    return json.dumps(s, ensure_ascii=False)


def save_html_report(result: ModuleTestResult, out_dir: str) -> str:
    """生成 HTML 报告并落盘，返回文件路径。"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_module_html_report(result))
    return path
