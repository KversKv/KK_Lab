"""Module Test 报告构建（工程级单文件 HTML · 数据/视图解耦版）。

规划 §7.2 重构：Python 侧把 ``ModuleTestResult`` 序列化为 ``REPORT_DATA`` JSON
注入静态模板，页面全部内容由原生 JS 依 JSON 渲染（无 CDN / 无外链，离线双击可用）。
UI 只拿路径打开，不做 IO——本模块纯字符串生成，禁依赖 Qt。

============================= 数据 Schema（REPORT_DATA） =============================
{
  "meta":    {report_title, module_type, chip, operator, temperature_c,
              start_time, end_time, duration_s, generated_at(带时区), sw_version,
              instruments[], environment{}},          # 缺字段一律 None → UI 显示 "—"
  "summary": {verdict: PASS|FAIL|N/A, pass, fail, warn, na, total},
  "items": [{
    index, item_key, title, verdict, unit, note,
    metrics: [{key,label,value,unit,precision,spec_min,spec_max,margin_pct,verdict}],
    charts:  [{id,kind:xy,title,x{key,label,unit,log},series[{key,name,
              type:line|smooth|scatter|bar,axis:left|right}],mark_extrema,
              anomaly{key,op,value}}],
    table:   {file,rows,columns:[{key,label,unit,align,precision,kind:image?,
              fmt:vbit?}],   # kind:image 列单元格 = attachments 下标（截图入表末列）；
              data[[...]],   # fmt:vbit 列单元格仍为十进制 int，前端按 Vbit 进制切换显示
              rules:[{column,op:gt|lt|abs_gt|eq|outlier,value,k,level:warn|fail,hint}
                     | {type:constant,level,hint}]},
    attachments: [{type:image,label,full(dataURI)}]
  }]
}
后端生成约定：仅 ``build_module_html_report(result)`` / ``save_html_report(...)`` 对外；
JSON 经 ``json.dumps`` 并把 ``</`` 转义为 ``<\\/`` 防 script 逃逸。

============================= 设计令牌（CSS Custom Properties） =============================
--bg-base/--bg-raised/--bg-sunk 三层底色；--ink-1/2/3 三级文字；--accent #2F6FED；
语义色 --pass #12A150 / --fail #E5484D / --warn #F5A524 / --na #8B949E（各配 12% 底）；
图表色序 --c1..--c8（色盲安全，语义同时用图标/形状承载）；
--font-ui 系统栈 / --font-mono ui-monospace；数值一律 tabular-nums；
8px 栅格 --sp-1..8；圆角 --r-sm 8 / --r-md 12；阴影仅 --shadow-1/--shadow-2 两级；
正文 14px / 表格 13px / 行高 1.55；:root[data-theme] 深浅双主题。

============================= CHANGELOG（相对旧版关键改进） =============================
 1. 去除 CDN ECharts 依赖 → 纯 SVG 自绘图表引擎，单文件离线可用；
 2. 数据/视图彻底解耦：REPORT_DATA JSON 驱动全页渲染，后端只产 JSON；
 3. 新增 KPI 概览带（总项/PASS/FAIL/N-A/时长/异常点）+ 结论分布 stacked bar；
 4. 新增结论汇总矩阵：结论筛选 chips、行锚点跳转、异常点计数联动；
 5. 关键测量值升级为 MetricCard 网格（值+单位+规格+余量条+状态描边）；
 6. 表格规则引擎：效率>100% 红标、fsw 突变、Diff 跳变(5×MAD)、恒值列告警；
 7. 高级数据表：sticky 表头+首列冻结、排序、列筛选、密度切换、分页、
    >500 行虚拟滚动、当前视图导出 CSV、异常行筛选；
 8. 图表能力：框选缩放/重置、log 轴切换、规格带、参考线、Min/Max 标注、
    Catmull-Rom 平滑折线、十字准线 tooltip、图例点选、导出 PNG；
 9. 深浅双主题（跟随系统 + localStorage 记忆）、中/英一键切换；
10. 左侧固定目录 scroll-spy + 阅读进度条，移动端折叠；
11. 示波器截图缩略图网格 + 灯箱（←/→/Esc、滚轮缩放、测量条件 caption）；
12. 专门 @media print：A4/15mm、强制浅色、自动展开折叠区、表头跨页重复、
    大表截断提示、页眉页脚(机密标识)、签核区；
13. 键盘操作（/ j k e ?）、focus-visible 环、aria 语义、图表表格化替代数据；
14. 缺失字段全局优雅降级为 "—"，数值等宽对齐、单位独立小字、有效位统一；
15. 版式修订（2026-08）：Load/Line Regulation 散点+拟合线 → Catmull-Rom 平滑折线；
    Load Capability&Ripple 示波器截图并入完整数据表末列（附件下标，不重复内嵌）；
    Load/Line Transient 移除分组对比柱状图（数据表与截图网格保留）；
16. 版式修订（2026-08-04）：Output Voltage Scan 首列 DAC_code → Vbit 显示（列
    fmt:vbit，数据仍为十进制 int），表格工具条 BIN/HEX/DEC chips 全局切换进制
    （localStorage 记忆，联动表格/图表刻度/tooltip/图表数据）；Efficiency 移除
    100% 参考虚线（ref_y 已删），图表值域/刻度自适应（log 模式按对数空间留白，
    logTicks 窄域细分 1/2/5×10^e，手动切换 LOG X/Y 后自动贴合数据）；
17. 版式修订（2026-08-04 b）：Vbit 进制切换改到列标题下拉（BIN/HEX/DEC）；行首
    异常图标改固定槽位（未异常行补占位，不再顶错位宽对齐）；Vbit 与数值列统一
    右对齐；Vout Scan 异常 diff 柱标红（bar_anomaly，5×MAD 与表格规则一致）；
    右 Y 轴标题与图区留 26px 边距（左轴 16px）；移除无用的规格带
    （spec_band/spec.spec_band 渲染与 chart_band 切换按钮一并删除）。

============================= 已知限制 =============================
- Chrome 打印无法用 CSS 计数器输出"第 X/Y 页"，页脚仅含机密标识与生成时间；
- 图表为 SVG 原生打印（非 Canvas），无需位图转换；量纲开关作用于指标卡/表格，
  图表轴单位保持原始量纲；
- 当前 ItemResult 无规格上下限字段，metrics 的 spec_min/max 一律 None，
  UI 显示"未定义规格"灰标并计入 N/A（schema 已预留，后续接入判定规格即生效）。
"""
from __future__ import annotations

import base64
import csv
import html
import json
import os
import re
from datetime import datetime
from typing import Any

from log_config import get_logger

from core.module_test.result_model import ItemResult, ModuleTestResult

logger = get_logger(__name__)

try:  # 版本号唯一事实源 = version.py（硬红线 10）
    import version as _ver
    _SW_VERSION = getattr(_ver, "__version__", None) or getattr(_ver, "VERSION", None)
except Exception:  # noqa: BLE001 - 版本缺失不阻断报告
    _SW_VERSION = None


# ---------------------------------------------------------------------------
# 数据读取 helpers
# ---------------------------------------------------------------------------

def _csv_to_rows(path: str | None) -> list[list[str]]:
    """读取原始数据 CSV（utf-8-sig），返回含表头的二维行；失败返回空。"""
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as f:
            return [row for row in csv.reader(f) if row]
    except Exception:  # noqa: BLE001 - 读取失败不影响报告生成
        logger.warning("报告读取 CSV 失败: %s", path, exc_info=True)
        return []


def _img_data_uri(path: str | None) -> str:
    """读取 PNG 返回 base64 data URI；失败返回空串。"""
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{data}"
    except Exception:  # noqa: BLE001 - 内嵌失败不影响报告生成
        logger.warning("报告内嵌图片失败: %s", path, exc_info=True)
        return ""


def _num(value: Any) -> float | None:
    """转浮点；失败返回 None。"""
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _in(dict_val: dict, *keys: str) -> float | None:
    """从 dict 按 keys 顺序取首个可转浮点的值。"""
    for k in keys:
        v = _num(dict_val.get(k))
        if v is not None:
            return v
    return None


# ---------------------------------------------------------------------------
# REPORT_DATA 构建 —— table / metrics / charts / rules / attachments
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(r"^\s*(?P<label>.*?)\s*(?:\((?P<unit>[^()]*)\))?\s*$")


def _split_header(header: str) -> tuple[str, str]:
    """把 'Iload (mA)' 拆成 (label, unit)。"""
    m = _HEADER_RE.match(str(header))
    if not m:
        return str(header), ""
    return (m.group("label") or str(header)).strip(), (m.group("unit") or "").strip()


def _precision_of(values: list[Any], cap: int = 6) -> int:
    """由原始字符串推导列有效小数位（取最大，封顶 cap）。"""
    prec = 0
    for v in values:
        s = str(v)
        if "." in s and "e" not in s.lower():
            prec = max(prec, len(s.split(".", 1)[1].rstrip("0")) or 1)
    return min(prec, cap)


def _build_table(it: ItemResult) -> dict[str, Any] | None:
    """从原始 CSV（或 measured list[dict] 兜底）构建 table schema。"""
    rows = _csv_to_rows(it.raw_csv_path)
    source_file = os.path.basename(it.raw_csv_path) if it.raw_csv_path else ""
    if not rows and isinstance(it.measured, list) and it.measured \
            and isinstance(it.measured[0], dict):
        keys: list[str] = []
        for row in it.measured:
            for k in row:
                if k not in keys:
                    keys.append(k)
        rows = [keys] + [[str(r.get(k, "")) for k in keys] for r in it.measured]
        source_file = source_file or "(measured)"
    if not rows or len(rows) < 2:
        return None

    header = [str(c) for c in rows[0]]
    body = rows[1:]
    columns: list[dict[str, Any]] = []
    for i, h in enumerate(header):
        label, unit = _split_header(h)
        col_vals = [r[i] for r in body if i < len(r)]
        numeric = sum(1 for v in col_vals if _num(v) is not None)
        is_num = bool(col_vals) and numeric >= max(1, int(len(col_vals) * 0.6))
        columns.append({
            "key": f"c{i}", "label": label, "unit": unit,
            "align": "right" if is_num else "left",
            "precision": _precision_of(col_vals) if is_num else None,
            "numeric": is_num,
        })
    data: list[list[Any]] = []
    for r in body:
        row: list[Any] = []
        for i, col in enumerate(columns):
            raw = r[i] if i < len(r) else ""
            v = _num(raw) if col["numeric"] else None
            row.append(v if v is not None else (str(raw) if str(raw) != "" else None))
        data.append(row)
    return {"file": source_file, "rows": len(data),
            "columns": [{k: c[k] for k in ("key", "label", "unit", "align", "precision")}
                        for c in columns],
            "_numeric_cols": [c["key"] for c in columns if c["numeric"]],
            "data": data}


def _pick_col(table: dict[str, Any], *keywords: str,
              fallback: int | None = None) -> str | None:
    """按表头关键词（小写包含）挑列 key；fallback 为列下标。"""
    for kw in keywords:
        for c in table["columns"]:
            if kw in c["label"].lower() or kw in c["unit"].lower():
                return c["key"]
    if fallback is not None and 0 <= fallback < len(table["columns"]):
        return table["columns"][fallback]["key"]
    return None


def _col_label(table: dict[str, Any], key: str | None) -> tuple[str, str]:
    for c in table["columns"]:
        if c["key"] == key:
            return c["label"], c["unit"]
    return "", ""


def _build_rules(it: ItemResult, table: dict[str, Any] | None) -> list[dict[str, Any]]:
    """按测试项生成异常检测规则（JS 侧求值，对缺失列容错）。"""
    if not table:
        return []
    key = it.item_key
    rules: list[dict[str, Any]] = []
    if key.endswith("vout_scan"):
        diff = _pick_col(table, "diff")
        if diff:
            rules.append({"column": diff, "op": "outlier", "k": 5,
                          "level": "warn", "hint": "步进异常跳变(>5×MAD)"})
    elif key.endswith("efficiency"):
        eff = _pick_col(table, "eff", "η")
        if eff:
            rules.append({"column": eff, "op": "gt", "value": 100,
                          "level": "fail", "hint": "效率超过 100%"})
    elif key.endswith("switching_freq"):
        fsw = _pick_col(table, "fsw", "freq")
        if fsw:
            rules.append({"column": fsw, "op": "outlier", "k": 5,
                          "level": "warn", "hint": "开关频率异常突变"})
    elif key.endswith("current_limit"):
        numeric = [c["key"] for c in table["columns"] if c["align"] == "right"]
        if numeric:
            rules.append({"type": "constant", "columns": numeric,
                          "level": "warn", "hint": "列值恒定，疑似仪器/接线异常"})
    return rules


def _mk(key: str, label: str, value: Any, unit: str = "",
        precision: int = 3) -> dict[str, Any] | None:
    """构建单条 metric；value 缺失返回 None（调用方过滤）。"""
    v = _num(value)
    if v is None:
        return None
    return {"key": key, "label": label, "value": v, "unit": unit,
            "precision": precision, "spec_min": None, "spec_max": None,
            "margin_pct": None, "verdict": None}


def _build_metrics(it: ItemResult, table: dict[str, Any] | None) -> list[dict[str, Any]]:
    """按测试项语义生成结构化关键指标（规格字段预留为 None → UI 灰标）。"""
    key = it.item_key
    m = it.measured if isinstance(it.measured, dict) else {}
    out: list[dict[str, Any] | None] = []

    cols = table["columns"] if table else []
    body = table["data"] if table else []

    def col_values(idx: int) -> list[float]:
        return [r[idx] for r in body
                if idx < len(r) and isinstance(r[idx], (int, float))]

    if key.endswith("vout_scan"):
        vs = col_values(1)
        out = [
            _mk("default_mv", "Default", m.get("default_voltage_mv"), "mV"),
            _mk("vout_min", "Min", m.get("vout_min_mv") or (min(vs) if vs else None), "mV"),
            _mk("vout_max", "Max", m.get("vout_max_mv") or (max(vs) if vs else None), "mV"),
            _mk("step_mv", "Avg Step", m.get("step_mv"), "mV"),
        ]
    elif key.endswith("load_reg"):
        drop = _num(m.get("vout_drop_mv"))
        pct = None
        if len(cols) >= 2 and body:
            v0, v1 = _num(body[0][1]), _num(body[-1][1])
            if v0 is not None and v1 is not None and abs(v0) > 1e-9:
                pct = (v1 - v0) / v0 * 100.0
                if drop is None:
                    drop = v1 - v0
        out = [_mk("load_reg_pct", "Load Reg", pct, "%"),
               _mk("vout_drop", "ΔV", drop, "mV")]
    elif key.endswith("line_reg"):
        span = _num(m.get("vout_span_mv"))
        pct = None
        vs = col_values(1)
        if vs:
            if span is None:
                span = max(vs) - min(vs)
            mean_v = sum(vs) / len(vs)
            if abs(mean_v) > 1e-9:
                pct = (max(vs) - min(vs)) / mean_v * 100.0
        out = [_mk("line_reg_pct", "Line Reg", pct, "%"),
               _mk("vout_span", "ΔV", span, "mV")]
    elif key.endswith("efficiency"):
        effs = col_values(2)
        max_eff = _num(m.get("max_eff")) or (max(effs) if effs else None)
        avg_eff = _num(m.get("avg_eff")) or (sum(effs) / len(effs) if effs else None)
        at = None
        if effs and body:
            peak_i = max(range(len(body)),
                         key=lambda i: body[i][2] if isinstance(body[i][2], (int, float))
                         else float("-inf"))
            at = _num(body[peak_i][0])
        out = [_mk("max_eff", "Max η", max_eff, "%", 2),
               _mk("max_eff_at", "Peak @ Iload", at, "mA", 0),
               _mk("avg_eff", "Avg η", avg_eff, "%", 2)]
    elif key.endswith("quiescent"):
        out = [_mk("iq", "Iq", _in(m, "Iq (uA)", "Iq (A)"), "uA"),
               _mk("divin", "dIvin", m.get("dIvin (uA)"), "uA"),
               _mk("divout", "dIvout", m.get("dIvout (uA)"), "uA")]
    elif key.endswith("ripple"):
        if "max_vpp_mv" in m:
            out = [_mk("max_vpp", "Max Vpp", m.get("max_vpp_mv"), "mV", 2),
                   _mk("max_vpp_at", "@ Iload", m.get("max_vpp_at_ma"), "mA", 0)]
        else:
            out = [_mk("vpp", "Vpp", m.get("vpp_mv"), "mV", 2),
                   _mk("rms", "RMS", m.get("rms_mv"), "mV", 2)]
    elif key.endswith("current_limit"):
        out = [_mk("limit", "Current Limit", m.get("current_limit_ma"), "mA", 1),
               _mk("peak", "Peak", m.get("peak_current_ma"), "mA", 1)]
    elif key.endswith("switching_freq"):
        freqs: list[float] = []
        rows = it.measured if isinstance(it.measured, list) else []
        for r in rows:
            if isinstance(r, dict):
                v = _num(r.get("Fsw (kHz)"))
                if v and v > 0:
                    freqs.append(v)
        if not freqs:
            freqs = [v for v in col_values(1) if v > 0]
        out = [_mk("fsw_min", "Fsw Min", min(freqs) if freqs else None, "kHz"),
               _mk("fsw_max", "Fsw Max", max(freqs) if freqs else None, "kHz"),
               _mk("fsw_pts", "点数", len(freqs) if freqs else None, "", 0)]
    elif key.endswith("transient"):
        out = [_mk("max_over", "最大过冲", m.get("max_overshoot_mv"), "mV", 1),
               _mk("max_under", "最大欠冲", m.get("max_undershoot_mv"), "mV", 1),
               _mk("groups", "组数", m.get("groups"), "", 0)]
    elif key.endswith("dropout"):
        out = [_mk("dropout", "Dropout", m.get("dropout_mv"), "mV"),
               _mk("v0", "V0", m.get("v0_mv"), "mV")]
    elif key.endswith("startup"):
        out = [_mk("soft_start", "SoftStart", m.get("soft_start_ms"), "ms"),
               _mk("overshoot", "Overshoot", m.get("overshoot_mv"), "mV")]
    elif key.endswith("output_noise"):
        out = [_mk("center", "Center", m.get("center_freq_khz"), "kHz"),
               _mk("span", "Span", m.get("freq_span_khz"), "kHz")]
    elif isinstance(it.measured, dict):  # 通用兜底：前 4 个可数值化条目
        for k, v in list(it.measured.items())[:4]:
            if k == "screenshots":
                continue
            out.append(_mk(str(k), str(k), v, ""))
    elif isinstance(it.measured, list):
        out = [_mk("rows", "数据行数", len(it.measured), "", 0)]

    return [x for x in out if x is not None]


def _xy(x_key: str, series: list[dict[str, Any]], table: dict[str, Any],
        title: str, **extra: Any) -> dict[str, Any]:
    """组装 xy 图表 spec（轴标签自动从列定义带出）。"""
    xl, xu = _col_label(table, x_key)
    spec: dict[str, Any] = {
        "kind": "xy", "title": title,
        "x": {"key": x_key, "label": xl, "unit": xu},
        "series": series,
    }
    spec.update(extra)
    return spec


def _build_charts(it: ItemResult, table: dict[str, Any] | None) -> list[dict[str, Any]]:
    """按测试项生成图表 spec（数据不进 spec，JS 从 table.data 取列）。"""
    if not table or table["rows"] < 2:
        return []
    key = it.item_key
    t = table
    charts: list[dict[str, Any]] = []

    def ser(col_key: str | None, kind: str = "line",
            axis: str = "left") -> dict[str, Any] | None:
        if not col_key:
            return None
        lb, un = _col_label(t, col_key)
        return {"key": col_key, "name": f"{lb} ({un})" if un else lb,
                "type": kind, "axis": axis, "unit": un, "label": lb}

    if key.endswith("vout_scan"):
        t["columns"][0]["fmt"] = "vbit"  # 首列 DAC_code → Vbit 字符串（前端进制切换）
        xk = t["columns"][0]["key"]
        yk = _pick_col(t, "vout", fallback=1)
        diff = _pick_col(t, "diff")
        series = [s for s in (ser(yk), ser(diff, "bar", "right")) if s]
        spec = _xy(xk, series, t, "Vout vs Vbit",
                   mark_extrema=True, zoom=True)
        if diff:  # 异常 diff 柱标红（与表格 outlier 规则一致的 5×MAD）
            spec["bar_anomaly"] = {"key": diff, "op": "outlier", "k": 5}
        charts.append(spec)
    elif key.endswith("efficiency"):
        xk = _pick_col(t, "iload", fallback=0)
        ek = _pick_col(t, "eff", "η", fallback=2)
        s = ser(ek)
        if s:
            charts.append(_xy(xk, [s], t, "Efficiency vs Iload",
                              anomaly={"key": ek, "op": "gt", "value": 100}))
    elif key.endswith("load_reg"):
        xk = _pick_col(t, "iload", fallback=0)
        yk = _pick_col(t, "vout", fallback=1)
        s = ser(yk, "smooth")
        if s:
            charts.append(_xy(xk, [s], t, "Vout vs Iload"))
    elif key.endswith("line_reg"):
        xk = _pick_col(t, "vin", fallback=0)
        yk = _pick_col(t, "vout", fallback=1)
        s = ser(yk, "smooth")
        if s:
            charts.append(_xy(xk, [s], t, "Vout vs Vin"))
    elif key.endswith("ripple"):
        xk = _pick_col(t, "iload", fallback=0)
        vout = ser(_pick_col(t, "vout", fallback=1))
        vpp = ser(_pick_col(t, "vpp"), "bar", "right")
        series = [s for s in (vout, vpp) if s]
        if series:
            charts.append(_xy(xk, series, t, "Vout & Ripple Vpp vs Iload"))
    elif key.endswith("switching_freq"):
        xk = _pick_col(t, "iload", fallback=0)
        fk = _pick_col(t, "fsw", "freq", fallback=1)
        s = ser(fk)
        if s:
            charts.append(_xy(xk, [s], t, "Fsw vs Iload", logx=True, logy=True))
    elif key.endswith("current_limit"):
        xk = _pick_col(t, "iload", fallback=0)
        yk = _pick_col(t, "vout", fallback=1)
        s = ser(yk)
        if s:
            charts.append(_xy(xk, [s], t, "Vout vs Iload"))
    elif key.endswith("transient"):
        pass  # 分组对比图已移除（2026-08 需求），瞬态项不生成图表，仅保留数据表+截图
    else:  # 通用兜底：前两列数值列折线
        numeric = [c for c in t["columns"] if c["align"] == "right"]
        if len(numeric) >= 2:
            s = ser(numeric[1]["key"])
            if s:
                charts.append(_xy(numeric[0]["key"], [s], t,
                                  f"{s['label']} vs {numeric[0]['label']}"))
    for i, c in enumerate(charts):
        c["id"] = f"{it.item_key}_{i}"
    return charts


def _build_attachments(it: ItemResult) -> tuple[list[dict[str, Any]],
                                                list[float | None]]:
    """示波器逐点截图（screenshots 优先）或单波形图 → (dataURI 附件列表, 各附件对应 Iload)。

    返回的 keys 与附件同序：逐点截图为其 "Iload (mA)" 数值（缺失/单波形图为 None），
    供 ``_embed_shots_column`` 把截图按 Iload 匹配进数据表末列。
    """
    out: list[dict[str, Any]] = []
    keys: list[float | None] = []
    m = it.measured if isinstance(it.measured, dict) else {}
    shots = m.get("screenshots") if isinstance(m.get("screenshots"), list) else []
    for s in shots:
        if not isinstance(s, dict):
            continue
        uri = _img_data_uri(s.get("png"))
        if uri:
            iload = s.get("Iload (mA)", "")
            label = f"Iload={iload}mA" if str(iload).strip() else "scope shot"
            out.append({"type": "image", "label": label, "full": uri})
            keys.append(_num(iload))
    if not out:
        uri = _img_data_uri(it.waveform_png)
        if uri:
            out.append({"type": "image", "label": "waveform", "full": uri})
            keys.append(None)
    return out, keys


def _embed_shots_column(it: ItemResult, table: dict[str, Any] | None,
                        attachments: list[dict[str, Any]],
                        shot_keys: list[float | None]) -> None:
    """Ripple 项：把逐点示波器截图并入完整数据表最后一列。

    新列 ``kind:image``，单元格存 attachments 下标（JS 侧渲染缩略图、点击进灯箱，
    不重复内嵌 base64）；按首列 Iload 数值匹配，未匹配行补 None。
    """
    if table is None or not it.item_key.endswith("ripple") or not attachments:
        return
    by_iload = {k: i for i, k in enumerate(shot_keys) if k is not None}
    if not by_iload:
        return
    iload_idx = next((i for i, c in enumerate(table["columns"])
                      if "iload" in c["label"].lower()), 0)
    table["columns"].append({"key": "shot", "label": "Scope Shot", "unit": "",
                             "align": "left", "precision": None, "kind": "image"})
    for row in table["data"]:
        v = row[iload_idx] if iload_idx < len(row) else None
        row.append(by_iload.get(v) if isinstance(v, (int, float)) else None)


def _parse_dt(s: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            continue
    return None


def build_report_data(result: ModuleTestResult) -> dict[str, Any]:
    """把 ModuleTestResult 序列化为 REPORT_DATA dict（唯一数据出口）。"""
    summary = result.build_summary()
    module = result.module_type.upper()
    started, finished = _parse_dt(result.started_at), _parse_dt(result.finished_at)
    duration = ((finished - started).total_seconds()
                if started and finished else None)
    temp_c = _num(result.temperature)

    items: list[dict[str, Any]] = []
    for idx, it in enumerate(result.items, 1):
        table = _build_table(it)
        rules = _build_rules(it, table)
        if table:
            table.pop("_numeric_cols", None)
        metrics = _build_metrics(it, table)
        charts = _build_charts(it, table)
        attachments, shot_keys = _build_attachments(it)
        # 截图列最后并入（metrics/charts 按既有列构建，不受新列影响）
        _embed_shots_column(it, table, attachments, shot_keys)
        items.append({
            "index": idx,
            "item_key": it.item_key,
            "title": it.name,
            "verdict": "PASS" if it.passed is True else (
                "FAIL" if it.passed is False else "N/A"),
            "unit": it.unit or "",
            "ts": it.ts or "",
            "metrics": metrics,
            "charts": charts,
            "table": table,
            "attachments": attachments,
            "note": it.notes or "",
            "_rules": rules,  # 并入 table.rules，缺表时丢弃
        })
    for it_dict in items:  # rules 挂到 table 下（schema 约定）
        rules = it_dict.pop("_rules")
        if it_dict["table"] is not None:
            it_dict["table"]["rules"] = rules

    generated = datetime.now().astimezone().isoformat(sep=" ", timespec="seconds")
    return {
        "meta": {
            "report_title": f"Module Test Report — {module}",
            "module_type": module,
            "chip": result.chip_name or None,
            "sample_id": None,
            "operator": result.operator or None,
            "temperature_c": temp_c,
            "vin_nominal_v": None,
            "vout_nominal_mv": None,
            "start_time": result.started_at or None,
            "end_time": result.finished_at or None,
            "duration_s": duration,
            "generated_at": generated,
            "sw_version": _SW_VERSION,
            "hw_setup": None,
            "instruments": list(getattr(result, "instruments", []) or []),
            "environment": {"ta_c": temp_c, "humidity_pct": None},
        },
        "summary": {
            "verdict": summary.get("overall", "N/A"),
            "pass": summary.get("pass", 0),
            "fail": summary.get("fail", 0),
            "warn": 0,  # 异常点数由前端规则引擎求值后回填
            "na": summary.get("norec", 0),
            "total": summary.get("total", 0),
        },
        "items": items,
    }


# ---------------------------------------------------------------------------
# HTML 模板（占位符 __TITLE__ / __REPORT_DATA__，避免 f-string 花括号转义）
# ---------------------------------------------------------------------------

_HEAD_COMMENT = """<!--
  KK_Lab Module Test Report — 工程级单文件报告（离线可用，无 CDN/外链）
  数据 Schema / 设计令牌 / CHANGELOG / 已知限制：见 core/module_test/report.py 模块 docstring
  后端生成约定：Python 端 build_report_data(result) -> dict 后 json.dumps 注入
  const REPORT_DATA = {...}（</ 转义为 <\\/）；页面全部由原生 JS 依 JSON 渲染。
-->"""

_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
__HEAD_COMMENT__
<style>
/* ============================ tokens ============================ */
:root{
  --accent:#2F6FED; --accent-weak:rgba(47,111,237,.12);
  --pass:#12A150; --pass-bg:rgba(18,161,80,.13);
  --fail:#E5484D; --fail-bg:rgba(229,72,77,.13);
  --warn:#F5A524; --warn-bg:rgba(245,165,36,.16);
  --na:#8B949E;   --na-bg:rgba(139,148,158,.15);
  --c1:#2F6FED; --c2:#12A150; --c3:#F5A524; --c4:#8E5CF0;
  --c5:#0EA5B7; --c6:#E5484D; --c7:#5B7A99; --c8:#B7791F;
  --r-sm:8px; --r-md:12px;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:24px; --sp-6:32px; --sp-8:48px;
  --fs-body:14px; --fs-table:13px; --lh:1.55;
  --font-ui:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
  --font-mono:ui-monospace,SFMono-Regular,Consolas,"Cascadia Mono",monospace;
  --shadow-1:0 1px 3px rgba(16,24,40,.08);
  --shadow-2:0 8px 28px rgba(16,24,40,.16);
  --focus-ring:0 0 0 2px var(--accent);
}
:root[data-theme="light"]{
  --bg-base:#F7F8FA; --bg-raised:#FFFFFF; --bg-sunk:#EEF1F6;
  --ink-1:#1C2330; --ink-2:#4A5568; --ink-3:#8B949E;
  --line:#E3E8F0; --grid:#EDF1F7; color-scheme:light;
}
:root[data-theme="dark"]{
  --bg-base:#0E1116; --bg-raised:#161B22; --bg-sunk:#0A0D12;
  --ink-1:#E6EAF2; --ink-2:#9AA4B2; --ink-3:#6B7280;
  --line:#242C38; --grid:#1D2530;
  --shadow-1:0 1px 3px rgba(0,0,0,.4); --shadow-2:0 8px 28px rgba(0,0,0,.5);
  color-scheme:dark;
}
/* ============================ base ============================ */
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg-base);color:var(--ink-1);
  font:var(--fs-body)/var(--lh) var(--font-ui);}
.num,td[data-v],.metric-card__value,.kpi__value{font-variant-numeric:tabular-nums}
code,.mono,.item-key{font-family:var(--font-mono);font-size:.92em}
button{font:inherit;color:inherit;background:none;border:none;cursor:pointer}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
:focus-visible{outline:none;box-shadow:var(--focus-ring);border-radius:var(--sp-1)}
::placeholder{color:var(--ink-3)}
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}
}
/* ============================ layout ============================ */
.wrap{max-width:1240px;margin:0 auto;padding:0 var(--sp-5) var(--sp-8)}
.layout{display:grid;grid-template-columns:220px minmax(0,1fr);gap:var(--sp-5);
  max-width:1500px;margin:0 auto;padding:0 var(--sp-4)}
.maincol{min-width:0;padding-bottom:var(--sp-8)}
section.card,.card{background:var(--bg-raised);border:1px solid var(--line);
  border-radius:var(--r-md);box-shadow:var(--shadow-1)}
/* -------- cover -------- */
.cover{background:linear-gradient(180deg,var(--bg-raised),var(--bg-base));
  border-bottom:1px solid var(--line);padding:var(--sp-5) 0 var(--sp-4)}
.cover__row{display:flex;align-items:flex-start;justify-content:space-between;
  gap:var(--sp-4);flex-wrap:wrap}
.cover h1{margin:0;font-size:22px;letter-spacing:.2px}
.cover__sub{color:var(--ink-2);font-size:12.5px;margin-top:var(--sp-1)}
.cover__sub .mono{color:var(--ink-3)}
.cover__meta{display:flex;gap:var(--sp-4);flex-wrap:wrap;margin-top:var(--sp-3);
  color:var(--ink-2);font-size:12.5px}
.cover__meta b{color:var(--ink-1);font-weight:600}
.cover__actions{display:flex;gap:var(--sp-2);flex-wrap:wrap;align-items:center}
/* -------- buttons -------- */
.btn{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;
  border:1px solid var(--line);border-radius:var(--r-sm);background:var(--bg-raised);
  color:var(--ink-2);font-size:12.5px;white-space:nowrap;transition:border-color .15s,color .15s,background .15s}
.btn:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.btn:active{background:var(--accent-weak)}
.btn[disabled]{opacity:.45;cursor:not-allowed}
.btn--primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn--primary:hover{background:#2560d4;color:#fff}
.btn[aria-pressed="true"]{background:var(--accent-weak);border-color:var(--accent);color:var(--accent)}
/* -------- sticky toolbar -------- */
.toolbar{position:sticky;top:0;z-index:60;background:color-mix(in srgb,var(--bg-base) 88%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line);
  padding:var(--sp-2) 0;margin-bottom:var(--sp-4)}
.toolbar__row{display:flex;gap:var(--sp-2);align-items:center;flex-wrap:wrap}
.search{position:relative;flex:1 1 240px;max-width:420px}
.search input{width:100%;padding:7px 12px 7px 30px;border:1px solid var(--line);
  border-radius:var(--r-sm);background:var(--bg-raised);color:var(--ink-1);font-size:13px}
.search input:focus{outline:none;border-color:var(--accent);box-shadow:var(--focus-ring)}
.search::before{content:"/";position:absolute;left:10px;top:50%;transform:translateY(-50%);
  color:var(--ink-3);font-family:var(--font-mono);font-size:12px;
  border:1px solid var(--line);border-radius:4px;padding:0 5px}
.search__pop{position:absolute;top:calc(100% + 4px);left:0;right:0;z-index:70;
  background:var(--bg-raised);border:1px solid var(--line);border-radius:var(--r-sm);
  box-shadow:var(--shadow-2);max-height:300px;overflow:auto;display:none}
.search__pop.show{display:block}
.search__pop button{display:block;width:100%;text-align:left;padding:8px 12px;
  font-size:12.5px;color:var(--ink-2)}
.search__pop button:hover,.search__pop button.active{background:var(--accent-weak);color:var(--accent)}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{padding:5px 11px;border:1px solid var(--line);border-radius:999px;
  font-size:12px;color:var(--ink-2);transition:all .15s}
.chip:hover{border-color:var(--accent);color:var(--accent)}
.chip[aria-pressed="true"]{background:var(--accent-weak);border-color:var(--accent);color:var(--accent);font-weight:600}
/* -------- toc -------- */
.toc{position:sticky;top:57px;align-self:start;max-height:calc(100vh - 80px);
  overflow:auto;padding:var(--sp-3) var(--sp-2)}
.toc__title{font-size:11px;font-weight:700;letter-spacing:1.5px;color:var(--ink-3);
  padding:0 var(--sp-2) var(--sp-2);text-transform:uppercase}
.toc a{display:flex;align-items:center;gap:8px;padding:6px var(--sp-2);
  border-radius:var(--r-sm);color:var(--ink-2);font-size:12.5px;
  border-left:2px solid transparent}
.toc a:hover{background:var(--bg-sunk);text-decoration:none}
.toc a.active{background:var(--accent-weak);border-left-color:var(--accent);
  color:var(--accent);font-weight:600}
.toc .idx{color:var(--ink-3);font-size:11px;min-width:16px;text-align:right;
  font-variant-numeric:tabular-nums}
.toc .name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.progress{height:2px;background:var(--bg-sunk);border-radius:2px;margin:0 var(--sp-2) var(--sp-2)}
.progress i{display:block;height:100%;width:0;background:var(--accent);border-radius:2px}
.toc-toggle{display:none}
@media (max-width:1100px){
  .layout{grid-template-columns:1fr}
  .toc{position:fixed;inset:0 auto 0 0;width:260px;z-index:90;background:var(--bg-raised);
    border-right:1px solid var(--line);transform:translateX(-100%);
    transition:transform .2s ease;max-height:none;border-radius:0}
  .toc.open{transform:none;box-shadow:var(--shadow-2)}
  .toc-toggle{display:inline-flex}
}
/* ============================ components ============================ */
/* -------- Badge（色盲安全：色+文案+图标） -------- */
.badge{display:inline-flex;align-items:center;gap:5px;padding:3px 10px;
  border-radius:999px;font-size:11.5px;font-weight:700;letter-spacing:.4px;white-space:nowrap}
.badge::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.badge--pass{background:var(--pass-bg);color:var(--pass)}
.badge--fail{background:var(--fail-bg);color:var(--fail)}
.badge--warn{background:var(--warn-bg);color:var(--warn)}
.badge--na{background:var(--na-bg);color:var(--na)}
.badge--lg{padding:8px 20px;font-size:16px}
.badge--lg::before{width:9px;height:9px}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;background:var(--bg-sunk);
  color:var(--ink-3);font-size:11px}
/* -------- KPI -------- */
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:var(--sp-3);margin-bottom:var(--sp-4)}
@media (max-width:900px){.kpis{grid-template-columns:repeat(3,1fr)}}
@media (max-width:560px){.kpis{grid-template-columns:repeat(2,1fr)}}
.kpi{padding:var(--sp-3) var(--sp-4)}
.kpi__label{font-size:11px;color:var(--ink-3);letter-spacing:.6px;text-transform:uppercase}
.kpi__value{font-size:24px;font-weight:700;margin-top:2px}
.kpi__value small{font-size:12px;color:var(--ink-3);font-weight:500;margin-left:2px}
.kpi--pass .kpi__value{color:var(--pass)} .kpi--fail .kpi__value{color:var(--fail)}
.kpi--warn .kpi__value{color:var(--warn)} .kpi--na .kpi__value{color:var(--na)}
.stackbar{display:flex;height:10px;border-radius:6px;overflow:hidden;
  background:var(--bg-sunk);margin:var(--sp-3) 0 var(--sp-4)}
.stackbar i{display:block;height:100%;transition:width .3s ease}
.stackbar .s-pass{background:var(--pass)} .stackbar .s-fail{background:var(--fail)}
.stackbar .s-warn{background:var(--warn)} .stackbar .s-na{background:var(--na)}
.stackbar-legend{display:flex;gap:var(--sp-4);font-size:11.5px;color:var(--ink-2);flex-wrap:wrap}
.stackbar-legend b{font-variant-numeric:tabular-nums}
/* -------- meta panel -------- */
details.panel{margin-bottom:var(--sp-4)}
details.panel>summary{cursor:pointer;list-style:none;padding:var(--sp-3) var(--sp-4);
  font-weight:600;font-size:13.5px;display:flex;align-items:center;gap:var(--sp-2);
  user-select:none}
details.panel>summary::-webkit-details-marker{display:none}
details.panel>summary::before{content:"▸";color:var(--ink-3);transition:transform .15s}
details.panel[open]>summary::before{transform:rotate(90deg)}
details.panel>summary:hover{color:var(--accent)}
.panel__body{padding:0 var(--sp-4) var(--sp-4)}
.dl{display:grid;grid-template-columns:repeat(2,1fr);gap:var(--sp-2) var(--sp-5)}
@media (max-width:700px){.dl{grid-template-columns:1fr}}
.dl>div{display:flex;gap:var(--sp-2);font-size:12.5px;padding:4px 0;
  border-bottom:1px dashed var(--line)}
.dl dt{color:var(--ink-3);min-width:130px;flex:none}
.dl dd{margin:0;color:var(--ink-1);font-weight:500;word-break:break-all}
/* -------- matrix -------- */
.matrix{margin-bottom:var(--sp-5)}
.matrix h2,.block-title{font-size:15px;margin:0;padding:var(--sp-3) var(--sp-4) 0}
/* -------- DataTable -------- */
.tbl-tools{display:flex;gap:var(--sp-2);align-items:center;flex-wrap:wrap;
  padding:var(--sp-2) var(--sp-4);border-bottom:1px solid var(--line);font-size:12px;color:var(--ink-3)}
.tbl-tools select,.tbl-tools input{padding:4px 8px;border:1px solid var(--line);
  border-radius:6px;background:var(--bg-raised);color:var(--ink-1);font-size:12px}
.tbl-wrap{overflow:auto;max-height:520px;position:relative}
table.tbl{border-collapse:separate;border-spacing:0;width:100%;font-size:var(--fs-table)}
.tbl th,.tbl td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--line);
  white-space:nowrap}
.tbl thead th{position:sticky;top:0;z-index:3;background:var(--bg-sunk);
  color:var(--ink-2);font-weight:600;font-size:12px;cursor:pointer;user-select:none}
.tbl thead th .u{color:var(--ink-3);font-weight:400}
.tbl thead th .arrow{font-size:10px;margin-left:4px;color:var(--accent)}
.tbl tbody tr:nth-child(even){background:color-mix(in srgb,var(--bg-sunk) 45%,transparent)}
.tbl tbody tr:hover{background:var(--accent-weak)}
.tbl tbody tr.sel{background:var(--accent-weak)}
.tbl .fcol{position:sticky;left:0;z-index:2;background:var(--bg-raised)}
.tbl tbody tr:nth-child(even) .fcol{background:var(--bg-raised)}
.tbl thead .fcol{z-index:4;background:var(--bg-sunk)}
.tbl.compact th,.tbl.compact td{padding:4px 10px;font-size:12px}
.tbl td.r,.tbl th.r{text-align:right}
.tbl .flt input{width:100%;min-width:64px;padding:3px 6px;font-size:11px;
  border:1px solid var(--line);border-radius:5px;background:var(--bg-raised);color:var(--ink-1)}
.vbit-th{display:inline-flex;align-items:center;gap:5px}
.vbit-cap{font-weight:600}
.vbit-sel{padding:1px 4px;font-size:10.5px;border:1px solid var(--line);border-radius:5px;
  background:var(--bg-raised);color:var(--ink-2);font-family:var(--font-mono);cursor:pointer}
td.cell-warn{background:var(--warn-bg)!important}
td.cell-fail{background:var(--fail-bg)!important;color:var(--fail);font-weight:600}
.rowflag{display:inline-block;width:1.35em;text-align:center}
.rowflag--ph{visibility:hidden}
.pager{display:flex;gap:var(--sp-2);align-items:center;justify-content:flex-end;
  padding:var(--sp-2) var(--sp-4);font-size:12px;color:var(--ink-3)}
.pager button{padding:3px 9px;border:1px solid var(--line);border-radius:6px;color:var(--ink-2)}
.pager button:hover:not([disabled]){border-color:var(--accent);color:var(--accent)}
.pager button[disabled]{opacity:.4;cursor:default}
.tbl-banner{margin:var(--sp-2) var(--sp-4);padding:6px 12px;border-radius:var(--r-sm);
  background:var(--warn-bg);color:var(--warn);font-size:12px;font-weight:600}
/* -------- item card -------- */
.item{margin-bottom:var(--sp-4);scroll-margin-top:70px}
.item__head{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap;
  padding:var(--sp-3) var(--sp-4);border-bottom:1px solid var(--line)}
.item__head h3{margin:0;font-size:15.5px;font-weight:700}
.item__head .idx{color:var(--ink-3);font-family:var(--font-mono);font-size:13px}
.item-key{color:var(--ink-3);background:var(--bg-sunk);padding:2px 8px;border-radius:5px}
.item__spacer{flex:1}
.item__anom{font-size:12px;color:var(--warn);font-weight:600;cursor:pointer;
  padding:2px 8px;border-radius:6px}
.item__anom:hover{background:var(--warn-bg)}
.icon-btn{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;
  border-radius:6px;color:var(--ink-3);font-size:13px}
.icon-btn:hover{background:var(--bg-sunk);color:var(--accent)}
.item.flash{animation:flash 1.2s ease}
@keyframes flash{0%,100%{box-shadow:var(--shadow-1)}30%{box-shadow:0 0 0 3px var(--accent)}}
.item__body{padding:var(--sp-4)}
.item.collapsed .item__body{display:none}
/* -------- MetricCard -------- */
.metrics{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));
  gap:var(--sp-3);margin-bottom:var(--sp-4)}
.metric-card{border:1px solid var(--line);border-radius:var(--r-sm);
  padding:var(--sp-3);background:var(--bg-raised);position:relative;
  border-left:3px solid var(--na)}
.metric-card--pass{border-left-color:var(--pass)}
.metric-card--fail{border-left-color:var(--fail)}
.metric-card--warn{border-left-color:var(--warn)}
.metric-card__label{font-size:11px;color:var(--ink-3);letter-spacing:.4px}
.metric-card__value{font-size:19px;font-weight:700;margin:2px 0}
.metric-card__value .unit{font-size:11px;color:var(--ink-3);font-weight:500;margin-left:3px}
.metric-card__spec{font-size:11px;color:var(--ink-3)}
.metric-card__nospec{display:inline-block;font-size:10.5px;color:var(--na);
  background:var(--na-bg);border-radius:4px;padding:1px 6px;margin-top:4px}
.marginbar{height:4px;border-radius:3px;background:var(--bg-sunk);margin-top:8px;overflow:hidden}
.marginbar i{display:block;height:100%;background:var(--pass);border-radius:3px}
.marginbar.over i{background:var(--fail)}
/* -------- ChartCard -------- */
.chart-card{border:1px solid var(--line);border-radius:var(--r-sm);
  margin-bottom:var(--sp-3);overflow:hidden}
.chart-card__head{display:flex;align-items:center;gap:var(--sp-2);flex-wrap:wrap;
  padding:var(--sp-2) var(--sp-3);border-bottom:1px solid var(--line)}
.chart-card__head h4{margin:0;font-size:13px;font-weight:600}
.chart-card__head .sp{flex:1}
.chart-card__head .tbtn{font-size:11px;padding:3px 9px;border:1px solid var(--line);
  border-radius:6px;color:var(--ink-3)}
.chart-card__head .tbtn:hover{border-color:var(--accent);color:var(--accent)}
.chart-card__head .tbtn[aria-pressed="true"]{background:var(--accent-weak);color:var(--accent);border-color:var(--accent)}
.chart-legend{display:flex;gap:var(--sp-3);flex-wrap:wrap;padding:6px var(--sp-3) 0;font-size:11.5px}
.chart-legend button{display:inline-flex;align-items:center;gap:5px;color:var(--ink-2)}
.chart-legend button.off{color:var(--ink-3);text-decoration:line-through}
.chart-legend .sw{width:10px;height:10px;border-radius:3px;display:inline-block}
.chart-box{height:340px;position:relative;color:var(--ink-2)}
.chart-box svg{display:block;width:100%;height:100%}
.chart-tip{position:absolute;pointer-events:none;background:var(--bg-raised);
  border:1px solid var(--line);border-radius:6px;box-shadow:var(--shadow-2);
  padding:6px 10px;font-size:11.5px;display:none;z-index:5;white-space:nowrap}
.chart-tip .tt-x{color:var(--ink-3);margin-bottom:2px}
.chart-alt{margin:0 var(--sp-3) var(--sp-2);font-size:11.5px;color:var(--ink-3)}
.chart-alt summary{cursor:pointer}
.zoom-rect{fill:var(--accent);opacity:.15;stroke:var(--accent);stroke-width:1}
/* -------- attachments / lightbox -------- */
.shots{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
  gap:var(--sp-3);margin:var(--sp-3) 0}
.shot{border:1px solid var(--line);border-radius:var(--r-sm);overflow:hidden;
  background:var(--bg-sunk);cursor:zoom-in;padding:0;text-align:left}
.shot img{width:100%;display:block;aspect-ratio:4/3;object-fit:cover}
.shot span{display:block;font-size:11px;color:var(--ink-3);padding:4px 8px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.shot:hover{border-color:var(--accent)}
.tbl-shot{vertical-align:middle}
.tbl-shot img{width:96px;height:auto;aspect-ratio:auto;object-fit:fill;border-radius:4px}
.lightbox{position:fixed;inset:0;z-index:200;background:rgba(10,13,18,.92);
  display:none;align-items:center;justify-content:center;flex-direction:column}
.lightbox.show{display:flex}
.lightbox img{max-width:92vw;max-height:82vh;border-radius:6px;
  box-shadow:0 12px 48px rgba(0,0,0,.6);transition:transform .15s ease}
.lightbox__cap{color:#dce7ff;font-size:13px;margin-top:10px}
.lightbox__nav{position:absolute;top:50%;transform:translateY(-50%);
  color:#fff;font-size:26px;padding:10px 14px;border-radius:8px;background:rgba(255,255,255,.08)}
.lightbox__nav:hover{background:rgba(255,255,255,.2)}
.lightbox__close{position:absolute;top:16px;right:20px;color:#fff;font-size:22px;
  padding:6px 12px;border-radius:8px;background:rgba(255,255,255,.08)}
/* -------- note / empty / toast -------- */
.note{margin-top:var(--sp-3);padding:var(--sp-2) var(--sp-3);border-left:3px solid var(--accent);
  background:var(--accent-weak);border-radius:0 var(--r-sm) var(--r-sm) 0;
  font-size:12.5px;color:var(--ink-2)}
.empty{padding:var(--sp-4);text-align:center;color:var(--ink-3);font-size:12.5px}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(20px);
  background:var(--ink-1);color:var(--bg-base);padding:8px 18px;border-radius:999px;
  font-size:12.5px;opacity:0;transition:all .25s ease;z-index:300;pointer-events:none}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
mark{background:var(--warn-bg);color:inherit;border-radius:2px;padding:0 1px}
/* -------- appendix -------- */
.glossary{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:var(--sp-2) var(--sp-4);font-size:12.5px}
.glossary dt{color:var(--ink-1);font-weight:700;font-family:var(--font-mono);font-size:12px}
.glossary dd{margin:0 0 var(--sp-2);color:var(--ink-2)}
.signoff{display:grid;grid-template-columns:repeat(3,1fr);gap:var(--sp-4);margin-top:var(--sp-4)}
.signoff>div{border:1px solid var(--line);border-radius:var(--r-sm);padding:var(--sp-3);min-height:96px}
.signoff .role{font-size:12px;color:var(--ink-3)}
.signoff .line{border-bottom:1px solid var(--ink-3);margin-top:52px}
/* -------- shortcut modal -------- */
.modal{position:fixed;inset:0;z-index:250;background:rgba(10,13,18,.55);
  display:none;align-items:center;justify-content:center}
.modal.show{display:flex}
.modal__card{background:var(--bg-raised);border-radius:var(--r-md);box-shadow:var(--shadow-2);
  padding:var(--sp-5);min-width:300px}
.modal__card h3{margin:0 0 var(--sp-3);font-size:15px}
.modal__card table{font-size:12.5px;border-collapse:collapse}
.modal__card td{padding:4px 14px 4px 0;color:var(--ink-2)}
.modal__card td:first-child{font-family:var(--font-mono);color:var(--accent)}
/* -------- print header/footer（屏幕隐藏） -------- */
.print-only{display:none}
/* ============================ print ============================ */
@media print{
  @page{size:A4 portrait;margin:15mm}
  :root[data-theme]{--bg-base:#fff;--bg-raised:#fff;--bg-sunk:#f4f6f8;
    --ink-1:#1C2330;--ink-2:#4A5568;--ink-3:#8B949E;--line:#ddd;--grid:#eee;
    --shadow-1:none;--shadow-2:none}
  body{background:#fff}
  .toolbar,.toc,.cover__actions,.tbl-tools,.pager,.chart-card__head .tbtn,
  .icon-btn,.item__anom,.lightbox,.toast,.modal,.search{display:none!important}
  .layout{display:block;padding:0}
  .card,section.card,.item{box-shadow:none;border:1px solid #ddd;break-inside:avoid}
  .item{page-break-inside:avoid}
  .chart-card{break-inside:avoid}
  details.panel>summary::before{display:none}
  .tbl-wrap{max-height:none;overflow:visible}
  .tbl thead{display:table-header-group}
  .print-only{display:block}
  .print-header{position:fixed;top:0;left:0;right:0;font-size:10px;color:#666;
    border-bottom:1px solid #ccc;padding-bottom:2mm}
  .print-footer{position:fixed;bottom:0;left:0;right:0;font-size:10px;color:#666;
    border-top:1px solid #ccc;padding-top:2mm;display:flex;justify-content:space-between}
  a{color:inherit;text-decoration:none}
}
@media (max-width:640px){
  .cover h1{font-size:18px}
  .metrics{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
  .chart-box{height:260px}
  .signoff{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div class="print-only print-header" id="printHeader"></div>
<div class="print-only print-footer" id="printFooter"></div>

<!-- ============================ cover ============================ -->
<header class="cover">
  <div class="wrap cover__row">
    <div>
      <h1 id="rptTitle"></h1>
      <div class="cover__sub" id="rptSub"></div>
      <div class="cover__meta" id="rptMeta"></div>
    </div>
    <div class="cover__actions" role="toolbar" aria-label="report actions">
      <button class="btn btn--primary" id="btnPdf"></button>
      <button class="btn" id="btnTheme" aria-pressed="false"></button>
      <button class="btn" id="btnLang"></button>
      <button class="btn" id="btnUnit" aria-pressed="false"></button>
    </div>
  </div>
</header>

<!-- ============================ sticky toolbar ============================ -->
<div class="toolbar">
  <div class="wrap toolbar__row">
    <button class="btn toc-toggle" id="btnToc" aria-label="toggle toc">☰</button>
    <div class="search">
      <input id="searchInput" type="search" autocomplete="off" aria-label="global search">
      <div class="search__pop" id="searchPop" role="listbox"></div>
    </div>
    <div class="chips" id="verdictChips" role="group" aria-label="verdict filter"></div>
    <button class="btn" id="btnExpandAll" aria-pressed="false"></button>
    <button class="btn" id="btnTop"></button>
  </div>
</div>

<div class="layout">
  <!-- ============================ toc ============================ -->
  <nav class="toc" id="toc" aria-label="table of contents"></nav>

  <main class="maincol" id="main">
    <section class="kpis" id="kpis" aria-label="KPI"></section>
    <div id="stackbar"></div>
    <details class="card panel" id="metaPanel">
      <summary id="metaSummary"></summary>
      <div class="panel__body" id="metaBody"></div>
    </details>
    <section class="card matrix" id="matrix"></section>
    <div id="items"></div>
    <section class="card" id="appendix" style="padding:var(--sp-4)"></section>
  </main>
</div>

<!-- lightbox / toast / shortcut modal -->
<div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-label="image viewer">
  <button class="lightbox__close" id="lbClose" aria-label="close">✕</button>
  <button class="lightbox__nav" id="lbPrev" style="left:12px" aria-label="previous">‹</button>
  <img id="lbImg" alt="attachment">
  <div class="lightbox__cap" id="lbCap"></div>
  <button class="lightbox__nav" id="lbNext" style="right:12px" aria-label="next">›</button>
</div>
<div class="toast" id="toast" role="status"></div>
<div class="modal" id="kbdModal" role="dialog" aria-modal="true">
  <div class="modal__card"><h3 id="kbdTitle"></h3><table id="kbdTable"></table></div>
</div>

<script>
"use strict";
/* ================================================================
 * 数据（后端注入，唯一事实源）
 * ================================================================ */
const REPORT_DATA = __REPORT_DATA__;

/* ================================================================
 * i18n —— 中/英文案集中管理
 * ================================================================ */
const I18N = {
  zh:{pdf:"导出 PDF",theme_dark:"深色模式",theme_light:"浅色模式",lang:"EN",
      unit:"自动量纲",unit_on:"原始量纲",expand:"全部展开",collapse:"全部折叠",
      top:"返回顶部",search_ph:"搜索测试项 / 指标 / item_key …",
      chip_all:"全部",kpi_total:"总项数",kpi_pass:"PASS",kpi_fail:"FAIL",
      kpi_na:"WARN / N/A",kpi_dur:"测试总时长",kpi_anom:"异常点",
      sec:"秒",meta:"元信息（被测件 / 环境 / 仪器 / 软件）",
      matrix:"结论汇总表",col_idx:"#",col_item:"测试项",col_verdict:"结论",
      col_metric:"关键指标（实测）",col_spec:"规格",col_margin:"余量",
      col_note:"备注",col_anom:"异常",items_title:"测试项明细",
      nospec:"未定义规格",anomalies:"个异常点",only_anom:"只看异常行",
      all_rows:"全部行",full_data:"完整测试数据",rows:"行",download:"下载 CSV",
      note:"备注",shots:"示波器截图",no_data:"无数据",no_chart:"无可绘制数据",
      no_shots:"无截图",appendix:"附录",files:"原始文件清单",conds:"测试条件",
      glossary:"术语与缩写",revision:"修订历史",signoff:"签核区",
      sign_test:"测试",sign_review:"复核",sign_approve:"批准",
      sign_date:"日期",rev_a:"Rev A",rev_init:"初版发布",
      copy_link:"复制链接",copied:"链接已复制",chart_png:"导出 PNG",
      chart_reset:"重置缩放",chart_logx:"log X",chart_logy:"log Y",
      chart_data:"图表数据",
      page:"页",of:"/",density:"紧凑",per_page:"每页",
      render_all:"渲染全部（便于查找）",virtual_on:"虚拟滚动",
      truncated:"仅打印前",rows_omitted:"行，其余省略（屏幕版可查看全部）",
      filter:"列筛选",export_view:"导出当前视图 CSV",
      kbd:"快捷键",kbd_open:"显示快捷键面板",
      confidential:"机密 · Confidential",generated:"生成时间",
      footer_page:"KK_Lab Module Test Report",
      gl:{Iq:"静态电流（Quiescent Current）",Vpp:"峰峰值电压（纹波）",
          fsw:"开关频率",LoadReg:"负载调整率",LineReg:"线性调整率",
          DAC:"数模转换器编码",MAD:"中位数绝对偏差（异常检测）"}},
  en:{pdf:"Export PDF",theme_dark:"Dark",theme_light:"Light",lang:"中文",
      unit:"Auto scale",unit_on:"Raw units",expand:"Expand all",collapse:"Collapse all",
      top:"Back to top",search_ph:"Search items / metrics / item_key …",
      chip_all:"All",kpi_total:"Total",kpi_pass:"PASS",kpi_fail:"FAIL",
      kpi_na:"WARN / N/A",kpi_dur:"Duration",kpi_anom:"Anomalies",
      sec:"s",meta:"Meta (DUT / Environment / Instruments / SW)",
      matrix:"Verdict Matrix",col_idx:"#",col_item:"Test Item",col_verdict:"Verdict",
      col_metric:"Key Metrics",col_spec:"Spec",col_margin:"Margin",
      col_note:"Note",col_anom:"Anom.",items_title:"Test Item Details",
      nospec:"No spec defined",anomalies:"anomalies",only_anom:"Anomalies only",
      all_rows:"All rows",full_data:"Full test data",rows:"rows",download:"Download CSV",
      note:"Note",shots:"Scope shots",no_data:"No data",no_chart:"Nothing to plot",
      no_shots:"No shots",appendix:"Appendix",files:"Raw files",conds:"Test conditions",
      glossary:"Glossary",revision:"Revision history",signoff:"Sign-off",
      sign_test:"Tested by",sign_review:"Reviewed by",sign_approve:"Approved by",
      sign_date:"Date",rev_a:"Rev A",rev_init:"Initial release",
      copy_link:"Copy link",copied:"Link copied",chart_png:"Export PNG",
      chart_reset:"Reset zoom",chart_logx:"log X",chart_logy:"log Y",
      chart_data:"Chart data",
      page:"Page",of:"/",density:"Compact",per_page:"Per page",
      render_all:"Render all (for find)",virtual_on:"Virtual scroll",
      truncated:"Prints first",rows_omitted:"rows; remainder omitted (see on-screen)",
      filter:"Column filters",export_view:"Export view CSV",
      kbd:"Keyboard shortcuts",kbd_open:"Show shortcuts",
      confidential:"Confidential",generated:"Generated",
      footer_page:"KK_Lab Module Test Report",
      gl:{Iq:"Quiescent current",Vpp:"Peak-to-peak voltage (ripple)",
          fsw:"Switching frequency",LoadReg:"Load regulation",LineReg:"Line regulation",
          DAC:"DAC code",MAD:"Median absolute deviation (outlier detection)"}}
};
let S = {
  lang: localStorage.getItem("rpt.lang") || "zh",
  theme: localStorage.getItem("rpt.theme") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  unitScaled: localStorage.getItem("rpt.unit") === "1",
  expandedAll: true,
  chip: "ALL",
};
const T = () => I18N[S.lang];

/* ================================================================
 * utils —— 格式化 / 量纲 / DOM
 * ================================================================ */
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = text;
  return n;
};
const esc = s => String(s ?? "").replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const DASH = "—";
/* 有效位格式化（缺失 → —） */
function fmt(v, p) {
  if (v === null || v === undefined || v === "" || Number.isNaN(Number(v))) return DASH;
  const n = Number(v);
  if (p === null || p === undefined) return String(n);
  return n.toFixed(Math.min(Math.max(p, 0), 9));
}
/* 自动量纲映射（mV↔V, uA↔mA） */
const UNIT_MAP = {"mV":"V","uA":"mA","µA":"mA"};
/* 电压位（Vbit）进制：全局 chips 状态 + 持久化，位宽取全局最大码位宽 */
const VBIT = {fmt: localStorage.getItem("rpt.vbitfmt") || "hex"};
function vbitCols() {
  const out = [];
  (REPORT_DATA.items || []).forEach(it => {
    if (!it.table) return;
    it.table.columns.forEach((c, i) => { if (c.fmt === "vbit") out.push({table:it.table, i}); });
  });
  return out;
}
function vbitWidth() {
  let m = 0;
  vbitCols().forEach(o => o.table.data.forEach(r => {
    const v = r[o.i];
    if (typeof v === "number" && Number.isInteger(v) && v >= 0) m = Math.max(m, v);
  }));
  return Math.max(1, m.toString(2).length);
}
function fmtVbit(v, width) {
  if (typeof v !== "number" || !Number.isInteger(v) || v < 0) return null;
  const f = VBIT.fmt;
  if (f === "bin") return "0b" + v.toString(2).padStart(width, "0");
  if (f === "dec") return String(v);
  return "0x" + v.toString(16).toUpperCase().padStart(Math.ceil(width / 4), "0");
}
function scaleVal(v, unit) {
  if (!S.unitScaled || !UNIT_MAP[unit] || v === null || isNaN(Number(v))) return v;
  return Number(v) / 1000;
}
function scaleUnit(u) { return (S.unitScaled && UNIT_MAP[u]) ? UNIT_MAP[u] : u; }
function unitSpan(u) {
  if (!u) return "";
  return ' <span class="unit">' + esc(scaleUnit(u)) + "</span>";
}
/* 数值节点：值 + 独立小字单位（量纲开关重渲染时更新） */
function numHTML(v, p, u) {
  const sv = scaleVal(v, u);
  const pp = (S.unitScaled && UNIT_MAP[u] && p !== null) ? Math.min(p + 3, 9) : p;
  return '<span class="num">' + fmt(sv, pp) + "</span>" + unitSpan(u);
}
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1600);
}
/* 调色板：读 CSS 变量，保证图表导出 PNG 与主题一致 */
function pal() {
  const cs = getComputedStyle(document.documentElement);
  const g = k => cs.getPropertyValue(k).trim();
  return {accent:g("--accent"),pass:g("--pass"),fail:g("--fail"),warn:g("--warn"),
    na:g("--na"),ink2:g("--ink-2"),ink3:g("--ink-3"),grid:g("--grid"),
    raised:g("--bg-raised"),line:g("--line"),
    seq:[g("--c1"),g("--c2"),g("--c3"),g("--c4"),g("--c5"),g("--c6"),g("--c7"),g("--c8")]};
}
const VERDICT_CLS = v => v === "PASS" ? "pass" : v === "FAIL" ? "fail" : v === "WARN" ? "warn" : "na";
function badge(v, lg) {
  return '<span class="badge badge--' + VERDICT_CLS(v) + (lg ? " badge--lg" : "") +
    '" role="status">' + esc(v) + "</span>";
}

/* ================================================================
 * 规则引擎 —— 表格异常检测（gt/lt/abs_gt/eq/outlier/constant）
 * ================================================================ */
function evalRules(table) {
  const res = {cells:{}, rows:{}, count:0, banners:[]};
  if (!table || !table.rules) return res;
  const colIdx = {}; table.columns.forEach((c, i) => colIdx[c.key] = i);
  const flag = (r, c, level) => {
    const k = r + ":" + c;
    if (res.cells[k] !== "fail") res.cells[k] = level;
    res.rows[r] = res.rows[r] === "fail" ? "fail" : level;
  };
  for (const rule of table.rules) {
    if (rule.type === "constant") {
      for (const ck of (rule.columns || [])) {
        const ci = colIdx[ck]; if (ci === undefined) continue;
        const vals = table.data.map(r => r[ci]).filter(v => typeof v === "number");
        if (vals.length > 1 && vals.every(v => v === vals[0])) {
          res.banners.push("⚠ " + (table.columns[ci].label || ck) + ": " + rule.hint);
        }
      }
      continue;
    }
    const ci = colIdx[rule.column]; if (ci === undefined) continue;
    let thresh = rule.value;
    if (rule.op === "outlier") {  /* k × MAD（中位数绝对偏差） */
      const vals = table.data.map(r => r[ci])
        .filter(v => typeof v === "number").sort((a, b) => a - b);
      if (vals.length < 4) continue;
      const med = vals[Math.floor(vals.length / 2)];
      const mads = vals.map(v => Math.abs(v - med)).sort((a, b) => a - b);
      const mad = mads[Math.floor(mads.length / 2)];
      if (mad < 1e-12) continue;
      thresh = {med, lim: (rule.k || 5) * mad};
    }
    table.data.forEach((row, ri) => {
      const v = row[ci]; if (typeof v !== "number") return;
      let hit = false;
      switch (rule.op) {
        case "gt": hit = v > thresh; break;
        case "lt": hit = v < thresh; break;
        case "abs_gt": hit = Math.abs(v) > thresh; break;
        case "eq": hit = v === thresh; break;
        case "outlier": hit = Math.abs(v - thresh.med) > thresh.lim; break;
      }
      if (hit) flag(ri, ci, rule.level || "warn");
    });
  }
  res.count = Object.keys(res.rows).length;
  return res;
}

/* ================================================================
 * render: cover / KPI / meta / matrix
 * ================================================================ */
function renderCover() {
  const m = REPORT_DATA.meta || {}, t = T(), s = REPORT_DATA.summary || {};
  $("#rptTitle").textContent = m.report_title || "Module Test Report";
  $("#rptSub").innerHTML =
    (m.chip ? '<b class="mono">' + esc(m.chip) + "</b> · " : "") +
    esc(m.module_type || DASH) + " &nbsp; " + badge(s.verdict || "N/A", true);
  const dur = m.duration_s != null ? fmt(m.duration_s, 1) + " " + t.sec : DASH;
  $("#rptMeta").innerHTML =
    "<span>" + esc(t.generated) + "：<b>" + esc(m.generated_at || DASH) + "</b></span>" +
    "<span>SW：<b class='mono'>" + esc(m.sw_version || DASH) + "</b></span>" +
    "<span>" + (S.lang === "zh" ? "耗时" : "Duration") + "：<b class='num'>" + dur + "</b></span>";
  $("#printHeader").textContent =
    (m.chip ? m.chip + " · " : "") + (m.report_title || "");
  $("#printFooter").innerHTML =
    "<span>" + esc(t.footer_page) + "</span><span>" + esc(t.confidential) +
    " · " + esc(m.generated_at || "") + "</span>";
}
function renderKpis() {
  const t = T(), s = REPORT_DATA.summary || {};
  const m = REPORT_DATA.meta || {};
  const dur = m.duration_s != null ? fmt(m.duration_s, 1) : DASH;
  const cards = [
    ["", t.kpi_total, s.total, ""], ["kpi--pass", t.kpi_pass, s.pass, ""],
    ["kpi--fail", t.kpi_fail, s.fail, ""], ["kpi--na", t.kpi_na, s.na, ""],
    ["", t.kpi_dur, dur, t.sec], ["kpi--warn", t.kpi_anom, '<span id="kpiAnom">0</span>', ""],
  ];
  $("#kpis").innerHTML = cards.map(c =>
    '<div class="card kpi ' + c[0] + '"><div class="kpi__label">' + esc(c[1]) +
    '</div><div class="kpi__value">' + (String(c[2]).startsWith("<") ? c[2] : esc(c[2] ?? DASH)) +
    (c[3] ? "<small>" + esc(c[3]) + "</small>" : "") + "</div></div>").join("");
  const tot = Math.max(s.total || 0, 1);
  const seg = (cls, v) => '<i class="' + cls + '" style="width:' +
    (100 * (v || 0) / tot).toFixed(2) + '%"></i>';
  $("#stackbar").innerHTML =
    '<div class="stackbar" role="img" aria-label="verdict distribution">' +
    seg("s-pass", s.pass) + seg("s-fail", s.fail) + seg("s-na", s.na) + "</div>" +
    '<div class="stackbar-legend"><span style="color:var(--pass)">■ PASS <b>' + (s.pass || 0) +
    '</b></span><span style="color:var(--fail)">■ FAIL <b>' + (s.fail || 0) +
    '</b></span><span style="color:var(--na)">■ N/A <b>' + (s.na || 0) + "</b></span></div>";
}
function renderMeta() {
  const m = REPORT_DATA.meta || {}, t = T();
  $("#metaSummary").textContent = t.meta;
  const pair = (k, v) =>
    "<div><dt>" + esc(k) + '</dt><dd class="' +
    (typeof v === "number" ? "num" : "") + '">' +
    (v === null || v === undefined || v === "" ? DASH : esc(v)) + "</dd></div>";
  let html = '<dl class="dl">' +
    pair("Chip", m.chip) + pair("Module", m.module_type) +
    pair("Sample ID", m.sample_id) + pair("Operator", m.operator) +
    pair("Temperature (°C)", m.temperature_c) +
    pair("Start", m.start_time) + pair("End", m.end_time) +
    pair("SW Version", m.sw_version) + pair("HW Setup", m.hw_setup) +
    pair("Env TA (°C)", (m.environment || {}).ta_c) +
    pair("Humidity (%)", (m.environment || {}).humidity_pct) + "</dl>";
  const ins = m.instruments || [];
  html += '<dl class="dl" style="margin-top:8px">' +
    (ins.length ? ins.map(i =>
      pair(esc(i.name || "Instrument"),
        [i.model, i.sn, i.cal_due].filter(Boolean).join(" · ") || DASH)).join("")
      : pair("Instruments", DASH)) + "</dl>";
  $("#metaBody").innerHTML = html;
}
function metricText(it) {
  const ms = (it.metrics || []).slice(0, 2);
  if (!ms.length) return DASH;
  return ms.map(mm => '<span class="num">' + esc(mm.label) + " " +
    fmt(scaleVal(mm.value, mm.unit), mm.precision) +
    (mm.unit ? " " + esc(scaleUnit(mm.unit)) : "") + "</span>").join("；");
}
function renderMatrix() {
  const t = T(), items = REPORT_DATA.items || [];
  const rows = items.map(it => {
    const anom = (window._anom || {})[it.item_key] || 0;
    return "<tr data-v='" + it.verdict + "'>" +
      "<td class='num' style='color:var(--ink-3)'>" + it.index + "</td>" +
      "<td><a href='#item-" + it.index + "'>" + esc(it.title) + "</a>" +
      "<div class='mono' style='font-size:10.5px;color:var(--ink-3)'>" + esc(it.item_key) + "</div></td>" +
      "<td>" + badge(it.verdict) + "</td>" +
      "<td style='font-size:12px'>" + metricText(it) + "</td>" +
      "<td class='tag'>" + t.nospec + "</td><td class='num'>" + DASH + "</td>" +
      "<td style='font-size:12px;color:var(--ink-3);max-width:220px;overflow:hidden;" +
      "text-overflow:ellipsis;white-space:nowrap'>" + esc(it.note || DASH) + "</td>" +
      "<td class='num'>" + (anom ? '<span style="color:var(--warn)">⚠ ' + anom + "</span>" : DASH) +
      "</td></tr>";
  }).join("");
  $("#matrix").innerHTML =
    "<h2 class='block-title'>" + esc(t.matrix) + "</h2>" +
    "<div class='tbl-wrap'><table class='tbl compact'><thead><tr>" +
    ["col_idx","col_item","col_verdict","col_metric","col_spec","col_margin","col_note","col_anom"]
      .map(k => "<th scope='col'>" + esc(t[k]) + "</th>").join("") +
    "</tr></thead><tbody>" + rows + "</tbody></table></div>";
}

/* ================================================================
 * render: items（四段式 section）
 * ================================================================ */
function metricCard(mm) {
  const t = T();
  const hasSpec = mm.spec_min !== null && mm.spec_min !== undefined;
  const cls = mm.verdict ? " metric-card--" + VERDICT_CLS(mm.verdict) : "";
  let spec = '<span class="metric-card__nospec">' + esc(t.nospec) + "</span>";
  let bar = "";
  if (hasSpec) {
    spec = '<div class="metric-card__spec num">' + fmt(mm.spec_min, mm.precision) +
      " ~ " + fmt(mm.spec_max, mm.precision) + esc(scaleUnit(mm.unit)) + "</div>";
    const over = mm.margin_pct !== null && (mm.margin_pct < 0 || mm.margin_pct > 100);
    bar = '<div class="marginbar' + (over ? " over" : "") + '"><i style="width:' +
      Math.max(0, Math.min(100, mm.margin_pct || 0)) + '%"></i></div>';
  }
  return '<div class="metric-card' + cls + '">' +
    '<div class="metric-card__label">' + esc(mm.label) + "</div>" +
    '<div class="metric-card__value">' + numHTML(mm.value, mm.precision, mm.unit) + "</div>" +
    spec + bar + "</div>";
}
function renderItems() {
  const t = T();
  $("#items").innerHTML = (REPORT_DATA.items || []).map(it => {
    const hasTbl = !!it.table;
    const shots = (it.attachments || []).filter(a => a.type === "image");
    return '<section class="card item" id="item-' + it.index + '" data-key="' + esc(it.item_key) + '">' +
      '<div class="item__head">' +
      '<span class="idx">' + String(it.index).padStart(2, "0") + "</span>" +
      "<h3>" + esc(it.title) + "</h3>" + badge(it.verdict) +
      '<span class="item-key mono">' + esc(it.item_key) + "</span>" +
      (it.unit ? '<span class="tag">' + esc(scaleUnit(it.unit)) + "</span>" : "") +
      '<span class="item__anom" data-anom="' + it.item_key + '"></span>' +
      '<span class="item__spacer"></span>' +
      '<button class="icon-btn" data-act="link" title="' + esc(t.copy_link) + '" aria-label="' + esc(t.copy_link) + '">🔗</button>' +
      '<button class="icon-btn" data-act="fold" aria-label="collapse">▾</button></div>' +
      '<div class="item__body">' +
      ((it.metrics || []).length
        ? '<div class="metrics">' + it.metrics.map(metricCard).join("") + "</div>"
        : '<div class="empty">' + t.no_data + "</div>") +
      '<div class="charts">' + (it.charts || []).map((c, i) =>
        '<div class="chart-card"><div class="chart-card__head"><h4>' + esc(c.title) + "</h4>" +
        '<span class="sp"></span>' +
        '<button class="tbtn" data-cact="png">' + esc(t.chart_png) + "</button>" +
        (c.kind === "xy"
          ? '<button class="tbtn" data-cact="reset">' + esc(t.chart_reset) + "</button>" +
            '<button class="tbtn" data-cact="logx" aria-pressed="false">' + esc(t.chart_logx) + "</button>" +
            '<button class="tbtn" data-cact="logy" aria-pressed="false">' + esc(t.chart_logy) + "</button>"
          : "") +
        '</div><div class="chart-legend"></div>' +
        '<div class="chart-box" data-item="' + esc(it.item_key) + '" data-chart="' + i + '"></div>' +
        '<details class="chart-alt"><summary>' + esc(t.chart_data) + "</summary>" +
        '<div class="chart-alt-body"></div></details></div>').join("") + "</div>" +
      (hasTbl
        ? '<details class="panel"><summary>' + esc(t.full_data) +
          "（" + esc(it.table.file || "") + " · " + it.table.rows + " " + esc(t.rows) + "）" +
          '</summary><div class="tbl-host" data-item="' + esc(it.item_key) + '"></div></details>'
        : '<div class="empty">' + t.no_data + "</div>") +
      (shots.length
        ? '<div class="block-title" style="padding:0 0 4px;font-size:12.5px">' + esc(t.shots) +
          '</div><div class="shots">' + shots.map((a, i) =>
          '<button class="shot" data-item="' + esc(it.item_key) + '" data-shot="' + i + '">' +
          '<img loading="lazy" src="' + a.full + '" alt="' + esc(a.label || "shot") + '">' +
          "<span>" + esc(a.label || "") + "</span></button>").join("") + "</div>"
        : "") +
      (it.note ? '<div class="note">' + esc(t.note) + "：" + esc(it.note) + "</div>" : "") +
      "</div></section>";
  }).join("");
}

/* ================================================================
 * render: appendix / toc
 * ================================================================ */
function renderAppendix() {
  const t = T(), m = REPORT_DATA.meta || {};
  const files = (REPORT_DATA.items || []).filter(it => it.table && it.table.file)
    .map(it => "<tr><td class='mono' style='font-size:11.5px'>" + esc(it.table.file) +
      "</td><td>" + esc(it.title) + "</td><td class='num'>" + it.table.rows + "</td></tr>").join("");
  const gl = T().gl;
  $("#appendix").innerHTML =
    "<h2 class='block-title' style='padding:0 0 8px'>" + esc(t.appendix) + "</h2>" +
    "<h4 style='margin:12px 0 4px;font-size:13px'>" + esc(t.files) + "</h4>" +
    (files ? "<table class='tbl compact'><thead><tr><th>File</th><th>Item</th><th>" +
      esc(t.rows) + "</th></tr></thead><tbody>" + files + "</tbody></table>"
      : '<div class="empty">' + t.no_data + "</div>") +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.conds) + "</h4>" +
    '<dl class="dl">' +
    "<div><dt>Vin nominal (V)</dt><dd class='num'>" + (m.vin_nominal_v ?? DASH) + "</dd></div>" +
    "<div><dt>Vout nominal (mV)</dt><dd class='num'>" + (m.vout_nominal_mv ?? DASH) + "</dd></div>" +
    "<div><dt>Temperature (°C)</dt><dd class='num'>" + (m.temperature_c ?? DASH) + "</dd></div>" +
    "<div><dt>Operator</dt><dd>" + esc(m.operator || DASH) + "</dd></div></dl>" +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.glossary) + "</h4>" +
    '<dl class="glossary">' + Object.keys(gl).map(k =>
      "<div><dt>" + esc(k) + "</dt><dd>" + esc(gl[k]) + "</dd></div>").join("") + "</dl>" +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.revision) + "</h4>" +
    "<table class='tbl compact'><thead><tr><th>Rev</th><th>" + esc(t.generated) +
    "</th><th></th></tr></thead><tbody><tr><td class='mono'>" + esc(t.rev_a) + "</td><td>" +
    esc(m.generated_at || DASH) + "</td><td>" + esc(t.rev_init) + "</td></tr></tbody></table>" +
    "<h4 style='margin:16px 0 4px;font-size:13px'>" + esc(t.signoff) + "</h4>" +
    '<div class="signoff">' + [t.sign_test, t.sign_review, t.sign_approve].map(r =>
      "<div><div class='role'>" + esc(r) + "</div><div class='line'></div>" +
      "<div class='role' style='margin-top:4px'>" + esc(t.sign_date) + "</div></div>").join("") +
    "</div>";
}
function renderToc() {
  const t = T();
  $("#toc").innerHTML =
    '<div class="progress" aria-hidden="true"><i id="readBar"></i></div>' +
    '<div class="toc__title">' + esc(t.items_title) + "</div>" +
    (REPORT_DATA.items || []).map(it =>
      "<a href='#item-" + it.index + "' data-target='item-" + it.index + "'>" +
      "<span class='idx'>" + it.index + "</span>" +
      '<span class="badge badge--' + VERDICT_CLS(it.verdict) +
      '" style="padding:0;width:8px;height:8px;border-radius:50%"></span>' +
      "<span class='name'>" + esc(it.title) + "</span></a>").join("");
}

/* ================================================================
 * charts —— 纯 SVG 自绘引擎（懒渲染 / 缩放 / log / 拟合 / PNG）
 * ================================================================ */
const _chartState = new WeakMap();
function colArr(table, key) {
  const i = table.columns.findIndex(c => c.key === key);
  return i < 0 ? [] : table.data.map(r => (typeof r[i] === "number" ? r[i] : null));
}
function niceTicks(lo, hi, n) {
  if (!isFinite(lo) || !isFinite(hi)) return [0, 1];
  if (lo === hi) { lo -= 1; hi += 1; }
  const span = hi - lo, step0 = span / Math.max(n, 1);
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const norm = step0 / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const t0 = Math.ceil(lo / step) * step, out = [];
  for (let v = t0; v <= hi + 1e-12; v += step) out.push(Number(v.toPrecision(12)));
  return out.length ? out : [lo, hi];
}
function logTicks(lo, hi) {
  /* 自适应 log 刻度：跨 ≤1.5 个数量级时细分 (1/2/5)×10^e，否则按 10^e 主刻度 */
  lo = Math.max(lo, 1e-12); hi = Math.max(hi, lo * 1.0001);
  const out = [];
  if (hi / lo <= 30) {
    for (let e = Math.floor(Math.log10(lo)) - 1; e <= Math.ceil(Math.log10(hi)); e++) {
      [1, 2, 5].forEach(m => {
        const v = m * Math.pow(10, e);
        if (v >= lo * 0.999 && v <= hi * 1.001) out.push(Number(v.toPrecision(12)));
      });
    }
    return out.length ? out : [lo, hi];
  }
  for (let e = Math.ceil(Math.log10(lo)); e <= Math.floor(Math.log10(hi)); e++)
    out.push(Math.pow(10, e));
  return out.length ? out : [lo, hi];
}
function fmtTick(v) {
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e6 || a < 1e-3) return v.toExponential(0);
  return Number(v.toPrecision(4)).toString();
}
const SVGNS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs, parent) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in (attrs || {})) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}
function drawChart(box) {
  const item = (REPORT_DATA.items || []).find(it => it.item_key === box.dataset.item);
  if (!item || !item.table) return;
  const spec = item.charts[Number(box.dataset.chart)];
  if (!spec) return;
  let st = _chartState.get(box);
  if (!st) { st = {logx:false, logy:false, band:true, dom:null, hidden:{}, zoom:null};
    _chartState.set(box, st); }
  const P = pal(), table = item.table;
  const W = box.clientWidth || 720, H = box.clientHeight || 340;
  const M = {l:64, r:(spec.series || []).some(s => s.axis === "right") ? 64 : 20, t:14, b:46};
  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  box.innerHTML = "";
  const svg = svgEl("svg", {width:W, height:H, role:"img",
    "aria-label":spec.title + " — " + (item.title || "")}, box);
  svgEl("rect", {x:0, y:0, width:W, height:H, fill:"transparent"}, svg);
  const tip = el("div", "chart-tip"); box.appendChild(tip);

  const col = key => colArr(table, key);
  const xs = col(spec.x.key);
  const series = (spec.series || []).filter(s => !st.hidden[s.key]);
  if (!series.length) { box.appendChild(emptyNode(T().no_chart)); return; }
  const leftS = series.filter(s => s.axis !== "right"),
        rightS = series.filter(s => s.axis === "right");
  const pairs = s => {
    const ys = col(s.key), out = [];
    xs.forEach((x, i) => { if (x !== null && ys[i] !== null &&
      (!st.logx || x > 0) && (!st.logy || ys[i] > 0)) out.push([x, ys[i]]); });
    return out;
  };
  const allPts = series.map(pairs);
  /* 值域（含缩放状态）；log 模式下按对数空间留白，保证刻度/范围自适应 */
  const domOf = (pts, pad, log) => {
    let lo = Infinity, hi = -Infinity;
    pts.flat().forEach(p => { lo = Math.min(lo, p); hi = Math.max(hi, p); });
    if (!isFinite(lo)) { lo = 0; hi = 1; }
    if (lo === hi) { lo -= 1; hi += 1; }
    if (log) {
      const eLo = Math.log10(Math.max(lo, 1e-12)), eHi = Math.log10(Math.max(hi, 1e-12));
      if (eHi - eLo < 1e-9) return [lo / 1.12, hi * 1.12];
      const d = (eHi - eLo) * (pad || 0.06);
      return [Math.pow(10, eLo - d), Math.pow(10, eHi + d)];
    }
    const d = (hi - lo) * (pad || 0.06);
    return [lo - d, hi + d];
  };
  const xAll = allPts.map(p => p.map(q => q[0]));
  let xDom = st.dom ? st.dom.x : domOf(xAll, 0.04, st.logx);
  const yDomFor = ss => {
    const pts = allPts.filter((p, i) => ss.includes(series[i])).map(p => p.map(q => q[1]));
    return domOf(pts, 0.1, st.logy);
  };
  let yL = st.dom ? st.dom.yL : yDomFor(leftS.length ? leftS : series);
  let yR = rightS.length ? (st.dom && st.dom.yR ? st.dom.yR : yDomFor(rightS)) : null;
  const sx = v => {
    if (st.logx) v = Math.log10(Math.max(v, 1e-12));
    const lo = st.logx ? Math.log10(Math.max(xDom[0], 1e-12)) : xDom[0];
    const hi = st.logx ? Math.log10(Math.max(xDom[1], 1e-12)) : xDom[1];
    return M.l + (v - lo) / (hi - lo || 1) * iw;
  };
  const mkY = (dom, log) => v => {
    if (log) v = Math.log10(Math.max(v, 1e-12));
    const lo = log ? Math.log10(Math.max(dom[0], 1e-12)) : dom[0];
    const hi = log ? Math.log10(Math.max(dom[1], 1e-12)) : dom[1];
    return M.t + ih - (v - lo) / (hi - lo || 1) * ih;
  };
  const syL = mkY(yL, st.logy), syR = yR ? mkY(yR, st.logy) : null;
  /* 网格 + 轴 */
  const drawAxis = (dom, log, yFn, right, label) => {
    const ticks = log ? logTicks(dom[0], dom[1]) : niceTicks(dom[0], dom[1], 6);
    ticks.forEach(tv => {
      const y = yFn(tv);
      if (y < M.t - 1 || y > M.t + ih + 1) return;
      if (!right) svgEl("line", {x1:M.l, x2:M.l + iw, y1:y, y2:y, stroke:P.grid}, svg);
      const tx = svgEl("text", {x:right ? M.l + iw + 8 : M.l - 8, y:y + 4,
        "text-anchor":right ? "start" : "end", "font-size":10, fill:P.ink3}, svg);
      tx.textContent = fmtTick(tv);
    });
    if (label) {
      /* 轴标题与图区留边距：右侧 26px / 左侧 16px（原右侧贴边太挤） */
      const ax = right ? W - 26 : 16;
      const lb = svgEl("text", {x:ax, y:M.t + ih / 2,
        "text-anchor":"middle", "font-size":11, fill:P.ink3,
        transform:"rotate(" + (right ? 90 : -90) + " " + ax + " " + (M.t + ih / 2) + ")"}, svg);
      lb.textContent = label;
    }
  };
  /* X 轴：vbit 列按当前进制渲染刻度（仅整数），其余数值走 fmtTick */
  const xIsVbit = table.columns.some(c => c.key === spec.x.key && c.fmt === "vbit");
  const xTickTxt = v => (xIsVbit && Number.isInteger(v) && v >= 0)
    ? (fmtVbit(v, vbitWidth()) || fmtTick(v)) : fmtTick(v);
  const xt = st.logx ? logTicks(xDom[0], xDom[1]) : niceTicks(xDom[0], xDom[1], 8);
  xt.forEach(tv => {
    const x = sx(tv);
    if (x < M.l - 1 || x > M.l + iw + 1) return;
    svgEl("line", {x1:x, x2:x, y1:M.t, y2:M.t + ih, stroke:P.grid}, svg);
    const tx = svgEl("text", {x:x, y:M.t + ih + 16, "text-anchor":"middle",
      "font-size":10, fill:P.ink3}, svg);
    tx.textContent = xTickTxt(tv);
  });
  const xlab = svgEl("text", {x:M.l + iw / 2, y:H - 6, "text-anchor":"middle",
    "font-size":11, fill:P.ink3}, svg);
  xlab.textContent = (xIsVbit ? "Vbit" : spec.x.label) + (spec.x.unit ? " (" + spec.x.unit + ")" : "");
  drawAxis(yL, st.logy, syL, false,
    leftS[0] ? leftS[0].label + (leftS[0].unit ? " (" + leftS[0].unit + ")" : "") : "");
  if (yR) drawAxis(yR, st.logy, syR, true,
    rightS[0] ? rightS[0].label + (rightS[0].unit ? " (" + rightS[0].unit + ")" : "") : "");
  svgEl("rect", {x:M.l, y:M.t, width:iw, height:ih, fill:"none", stroke:P.line}, svg);
  /* 系列 */
  series.forEach((s, si) => {
    const pts = allPts[series.indexOf(s)];
    const color = P.seq[si % P.seq.length];
    const yFn = s.axis === "right" && syR ? syR : syL;
    if (s.type === "bar") {
      const bw = Math.max(2, Math.min(18, iw / Math.max(pts.length, 1) * 0.5));
      /* 异常柱标红：bar_anomaly 规则（outlier=k×MAD / gt） */
      let barThresh = null;
      const ba = spec.bar_anomaly;
      if (ba && ba.key === s.key && pts.length > 3) {
        if (ba.op === "outlier") {
          const vals = pts.map(p => p[1]).sort((a, b) => a - b);
          const med = vals[Math.floor(vals.length / 2)];
          const mads = vals.map(v => Math.abs(v - med)).sort((a, b) => a - b);
          const mad = mads[Math.floor(mads.length / 2)];
          if (mad >= 1e-12) barThresh = {med, lim:(ba.k || 5) * mad, op:"outlier"};
        } else if (ba.op === "gt") barThresh = {value:ba.value, op:"gt"};
      }
      const barBad = v => barThresh &&
        (barThresh.op === "gt" ? v > barThresh.value
         : Math.abs(v - barThresh.med) > barThresh.lim);
      pts.forEach(p => {
        const y0 = yFn(Math.max(0, yR ? yR[0] : yL[0])), y1 = yFn(p[1]);
        const bad = barBad(p[1]);
        svgEl("rect", {x:sx(p[0]) - bw / 2, y:Math.min(y0, y1), width:bw,
          height:Math.abs(y1 - y0), fill:bad ? P.fail : color,
          opacity:bad ? .85 : .55}, svg);
      });
    } else {
      if (s.type === "line" || s.type === "smooth") {
        let d = "";
        if (s.type === "smooth" && pts.length > 2) {
          /* Catmull-Rom → 三次贝塞尔平滑（过原数据点） */
          const X = p => sx(p[0]), Y = p => yFn(p[1]);
          d = "M" + X(pts[0]).toFixed(1) + " " + Y(pts[0]).toFixed(1);
          for (let i = 0; i < pts.length - 1; i++) {
            const p0 = pts[Math.max(0, i - 1)], p1 = pts[i],
                  p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
            d += "C" + (X(p1) + (X(p2) - X(p0)) / 6).toFixed(1) + " " +
                       (Y(p1) + (Y(p2) - Y(p0)) / 6).toFixed(1) + " " +
                       (X(p2) - (X(p3) - X(p1)) / 6).toFixed(1) + " " +
                       (Y(p2) - (Y(p3) - Y(p1)) / 6).toFixed(1) + " " +
                       X(p2).toFixed(1) + " " + Y(p2).toFixed(1);
          }
        } else {
          pts.forEach((p, i) => { d += (i ? "L" : "M") + sx(p[0]).toFixed(1) + " " + yFn(p[1]).toFixed(1); });
        }
        svgEl("path", {d:d, fill:"none", stroke:color, "stroke-width":2}, svg);
      }
      if (s.type === "scatter" || pts.length <= 80) {
        pts.forEach(p => svgEl("circle", {cx:sx(p[0]), cy:yFn(p[1]), r:3,
          fill:color}, svg));
      }
    }
    /* 异常点：红色菱形异形 marker（形状+颜色双编码） */
    if (spec.anomaly && spec.anomaly.key === s.key) {
      pts.forEach(p => {
        if (spec.anomaly.op === "gt" && p[1] > spec.anomaly.value) {
          const x = sx(p[0]), y = yFn(p[1]);
          svgEl("path", {d:"M" + x + " " + (y - 6) + "L" + (x + 5) + " " + y +
            "L" + x + " " + (y + 6) + "L" + (x - 5) + " " + y + "Z",
            fill:P.fail, stroke:"#fff", "stroke-width":1}, svg);
        }
      });
    }
    /* Min/Max 标注 */
    if (spec.mark_extrema && pts.length > 2 && s.type !== "bar") {
      let mn = pts[0], mx = pts[0];
      pts.forEach(p => { if (p[1] < mn[1]) mn = p; if (p[1] > mx[1]) mx = p; });
      [["Min", mn, P.fail], ["Max", mx, P.pass]].forEach(([tag, p, c2]) => {
        svgEl("circle", {cx:sx(p[0]), cy:yFn(p[1]), r:5, fill:"none",
          stroke:c2, "stroke-width":2}, svg);
        const tx = svgEl("text", {x:sx(p[0]) + 8, cy:0, y:yFn(p[1]) - 8,
          "font-size":10, fill:c2, "font-weight":600}, svg);
        tx.textContent = tag + " " + fmtTick(p[1]);
      });
    }
  });
  /* 图例 */
  const legend = box.parentElement.querySelector(".chart-legend");
  if (legend) {
    legend.innerHTML = "";
    (spec.series || []).forEach((s, i) => {
      const b = el("button", st.hidden[s.key] ? "off" : "");
      b.innerHTML = '<span class="sw" style="background:' +
        P.seq[i % P.seq.length] + '"></span>' + esc(s.name);
      b.setAttribute("aria-pressed", String(!st.hidden[s.key]));
      b.onclick = () => { st.hidden[s.key] = !st.hidden[s.key]; drawChart(box); };
      legend.appendChild(b);
    });
  }
  /* 十字准线 + tooltip */
  const cross = svgEl("line", {x1:0, x2:0, y1:M.t, y2:M.t + ih, stroke:P.ink3,
    "stroke-dasharray":"3 3", visibility:"hidden"}, svg);
  svg.addEventListener("mousemove", ev => {
    if (st.zoom) return;
    const r = svg.getBoundingClientRect();
    const mx = ev.clientX - r.left;
    if (mx < M.l || mx > M.l + iw) { cross.setAttribute("visibility", "hidden");
      tip.style.display = "none"; return; }
    cross.setAttribute("x1", mx); cross.setAttribute("x2", mx);
    cross.setAttribute("visibility", "visible");
    let best = null, bd = Infinity;
    series.forEach((s, i) => allPts[i].forEach(p => {
      const d = Math.abs(sx(p[0]) - mx);
      if (d < bd) { bd = d; best = p; }
    }));
    if (!best) return;
    const bxTxt = xIsVbit ? (fmtVbit(best[0], vbitWidth()) || fmtTick(best[0])) : fmtTick(best[0]);
    let h = '<div class="tt-x">' + esc(xIsVbit ? "Vbit" : spec.x.label) + " = " +
      bxTxt + (spec.x.unit ? " " + esc(spec.x.unit) : "") + "</div>";
    series.forEach((s, i) => {
      const p = allPts[i].reduce((a, q) =>
        Math.abs(q[0] - best[0]) < Math.abs((a || [Infinity])[0] - best[0]) ? q : a, null);
      if (p) h += "<div>" + esc(s.name) + ": <b class='num'>" + fmtTick(p[1]) + "</b></div>";
    });
    tip.innerHTML = h; tip.style.display = "block";
    tip.style.left = Math.min(mx + 14, W - 150) + "px"; tip.style.top = "16px";
  });
  svg.addEventListener("mouseleave", () => {
    cross.setAttribute("visibility", "hidden"); tip.style.display = "none"; });
  /* 框选缩放 */
  let zr = null, zx0 = 0;
  svg.addEventListener("pointerdown", ev => {
    if (ev.button !== 0) return;
    const r = svg.getBoundingClientRect();
    const x = ev.clientX - r.left, y = ev.clientY - r.top;
    if (x < M.l || x > M.l + iw || y < M.t || y > M.t + ih) return;
    zx0 = x; st.zoom = true;
    zr = svgEl("rect", {"class":"zoom-rect", x:x, y:M.t, width:0, height:ih}, svg);
    svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener("pointermove", ev => {
    if (!zr) return;
    const r = svg.getBoundingClientRect();
    const x = Math.max(M.l, Math.min(M.l + iw, ev.clientX - r.left));
    zr.setAttribute("x", Math.min(zx0, x));
    zr.setAttribute("width", Math.abs(x - zx0));
  });
  svg.addEventListener("pointerup", ev => {
    if (!zr) return;
    const r = svg.getBoundingClientRect();
    const x1 = Math.max(M.l, Math.min(M.l + iw, ev.clientX - r.left));
    const w = Math.abs(x1 - zx0); zr.remove(); zr = null; st.zoom = false;
    if (w > 12) {
      const inv = px => {
        const lo = st.logx ? Math.log10(Math.max(xDom[0], 1e-12)) : xDom[0];
        const hi = st.logx ? Math.log10(Math.max(xDom[1], 1e-12)) : xDom[1];
        const v = lo + (px - M.l) / iw * (hi - lo);
        return st.logx ? Math.pow(10, v) : v;
      };
      st.dom = {x:[inv(Math.min(zx0, x1)), inv(Math.max(zx0, x1))],
        yL:yL, yR:yR};
      drawChart(box);
    }
  });
  /* 图表数据替代表（无障碍） */
  const alt = box.parentElement.querySelector(".chart-alt-body");
  if (alt && !alt.dataset.done) {
    alt.dataset.done = "1";
    const cols = [spec.x].concat(spec.series || []);
    const ixs = cols.map(c => table.columns.findIndex(cc => cc.key === c.key));
    const vbW = vbitWidth();
    let h = "<table class='tbl compact'><thead><tr>" + cols.map((c, ci) => {
      const col = table.columns[ixs[ci]];
      const lab = col && col.fmt === "vbit" ? "Vbit" : (c.label || c.name || "");
      return "<th scope='col'>" + esc(lab) + "</th>";
    }).join("") + "</tr></thead><tbody>";
    table.data.slice(0, 50).forEach(row => {
      h += "<tr>" + ixs.map((i, ci) => {
        const col = i >= 0 ? table.columns[i] : null;
        const v = i >= 0 ? row[i] : null;
        const vb = col && col.fmt === "vbit" ? fmtVbit(v, vbW) : null;
        return "<td class='num'>" + (vb ? esc(vb) : (v !== null ? esc(v) : DASH)) + "</td>";
      }).join("") + "</tr>";
    });
    alt.innerHTML = h + "</tbody></table>";
  }
}
function emptyNode(msg) { return el("div", "empty", msg); }
/* 懒渲染：进入视口才实例化 */
let _chartIO = null;
function armLazyCharts() {
  if (_chartIO) _chartIO.disconnect();
  _chartIO = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting && !en.target.dataset.rendered) {
        en.target.dataset.rendered = "1";
        drawChart(en.target);
        _chartIO.unobserve(en.target);
      }
    });
  }, {rootMargin:"200px"});
  $$(".chart-box").forEach(b => { if (!b.dataset.rendered) _chartIO.observe(b); });
}
function renderAllCharts() {
  $$(".chart-box").forEach(b => { if (!b.dataset.rendered) {
    b.dataset.rendered = "1"; drawChart(b); } });
}
/* SVG → PNG 导出（内联属性保证离屏渲染一致） */
function exportChartPng(box, name) {
  const svg = box.querySelector("svg");
  if (!svg) return;
  const xml = new XMLSerializer().serializeToString(svg);
  const img = new Image();
  img.onload = () => {
    const cv = document.createElement("canvas");
    cv.width = svg.getAttribute("width") * 2; cv.height = svg.getAttribute("height") * 2;
    const cx = cv.getContext("2d");
    cx.fillStyle = pal().raised; cx.fillRect(0, 0, cv.width, cv.height);
    cx.drawImage(img, 0, 0, cv.width, cv.height);
    const a = document.createElement("a");
    a.download = (name || "chart") + ".png";
    a.href = cv.toDataURL("image/png"); a.click();
  };
  img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(xml);
}

/* ================================================================
 * DataTable —— 排序/列筛选/密度/分页/虚拟滚动/导出/异常高亮
 * ================================================================ */
const _tblState = new WeakMap();
function buildTable(host, item) {
  const table = item.table;
  if (!table) return;
  const t = T();
  const flags = evalRules(table);
  const vbW = vbitWidth();
  const vbitCell = v => fmtVbit(v, vbW);
  (window._anom = window._anom || {})[item.item_key] = flags.count;
  const st = {sort:null, filters:{}, page:1, per:25, compact:false,
    onlyAnom:host.dataset.onlyAnom === "1", renderAll:false, showFlt:false};
  _tblState.set(host, st);

  const view = () => {
    let rows = table.data.map((r, i) => ({r, i}));
    if (st.onlyAnom) rows = rows.filter(o => flags.rows[o.i]);
    const fi = Object.keys(st.filters).filter(k => st.filters[k]);
    if (fi.length) rows = rows.filter(o => fi.every(k => {
      const ci = table.columns.findIndex(c => c.key === k);
      const v = o.r[ci], f = st.filters[k].trim().toLowerCase();
      if (/^[<>]=?\s*[-\d.]/.test(f) && typeof v === "number") {
        const m = f.match(/^([<>]=?)\s*([-\d.e]+)/);
        if (m) { const rhs = parseFloat(m[2]);
          return m[1] === ">" ? v > rhs : m[1] === ">=" ? v >= rhs :
                 m[1] === "<" ? v < rhs : v <= rhs; }
      }
      return String(v ?? "").toLowerCase().includes(f);
    }));
    if (st.sort !== null) {
      const dir = st.sort.dir;
      rows = rows.slice().sort((a, b) => {
        const x = a.r[st.sort.col], y = b.r[st.sort.col];
        if (typeof x === "number" && typeof y === "number") return (x - y) * dir;
        return String(x ?? "").localeCompare(String(y ?? "")) * dir;
      });
    }
    return rows;
  };
  const cellHTML = (row, ri) => {
    let h = "";
    table.columns.forEach((c, ci) => {
      const v = row[ci];
      const fl = flags.cells[ri + ":" + ci];
      const isVb = c.fmt === "vbit";
      /* vbit 与数值列统一右对齐（vbit 补零等宽），异常不改对齐 */
      const cls = [(c.align === "right" || isVb) ? "r num" : "",
        fl ? "cell-" + fl : "", ci === 0 ? "fcol" : ""].join(" ").trim();
      if (c.kind === "image") {  /* 截图列：单元格 = attachments 下标 → 缩略图 */
        const att = typeof v === "number" ? (item.attachments || [])[v] : null;
        h += "<td class='" + cls + "'>" + (att
          ? "<button class='shot tbl-shot' data-item='" + esc(item.item_key) +
            "' data-shot='" + v + "' aria-label='" + esc(att.label || "shot") +
            "'><img loading='lazy' src='" + att.full + "' alt='" +
            esc(att.label || "shot") + "'></button>"
          : DASH) + "</td>";
        return;
      }
      const full = typeof v === "number" ? ' title="' + v + '"' : "";
      const vb = isVb ? vbitCell(v) : null;
      h += "<td class='" + cls + "'" + full + ">" +
        (vb ? esc(vb)
          : (typeof v === "number"
            ? esc(fmt(scaleVal(v, c.unit), S.unitScaled && UNIT_MAP[c.unit]
                ? Math.min((c.precision ?? 3) + 3, 9) : c.precision))
            : (v === null ? DASH : esc(v)))) + "</td>";
    });
    return h;
  };
  const headHTML = () => {
    let h = "<tr>";
    table.columns.forEach((c, ci) => {
      const sorted = st.sort && st.sort.col === ci;
      /* vbit 列：列标题 = 进制下拉（BIN/HEX/DEC），单元格与列均右对齐 */
      const hlabel = c.fmt === "vbit"
        ? "<span class='vbit-th'><span class='vbit-cap'>Vbit</span>" +
          "<select class='vbit-sel' data-vbsel aria-label='Vbit radix'>" +
          ["bin", "hex", "dec"].map(f =>
            "<option value='" + f + "'" + (VBIT.fmt === f ? " selected" : "") + ">" +
            f.toUpperCase() + "</option>").join("") + "</select></span>"
        : esc(c.label);
      h += "<th scope='col' class='r" + (ci === 0 ? " fcol" : "") + "' data-col='" + ci + "'>" +
        hlabel +
        (c.unit ? " <span class='u'>(" + esc(scaleUnit(c.unit)) + ")</span>" : "") +
        (sorted ? "<span class='arrow'>" + (st.sort.dir > 0 ? "▲" : "▼") + "</span>" : "") +
        "</th>";
    });
    h += "</tr>";
    if (st.showFlt) {
      h += "<tr class='flt'>" + table.columns.map((c, ci) =>
        "<th class='" + (ci === 0 ? "fcol" : "") + "'><input data-fcol='" + c.key +
        "' value='" + esc(st.filters[c.key] || "") + "' aria-label='filter " +
        esc(c.label) + "'></th>").join("") + "</tr>";
    }
    return h;
  };
  const render = () => {
    const rows = view();
    const useVirtual = rows.length > 500 && !st.renderAll;
    let bodyH = "", toolsH = "";
    flags.banners.forEach(b => { toolsH += "<div class='tbl-banner'>" + esc(b) + "</div>"; });
    const rh = st.compact ? 26 : 34;
    if (useVirtual) {
      st.per = 0;  /* 虚拟滚动时不分页 */
      bodyH = "__VIRTUAL__";
    } else {
      const per = st.per || rows.length || 1;
      const pages = Math.max(1, Math.ceil(rows.length / per));
      st.page = Math.min(st.page, pages);
      const slice = rows.slice((st.page - 1) * per, st.page * per);
      bodyH = slice.map(o =>
        "<tr data-ri='" + o.i + "'>" +
        (flags.rows[o.i] ? "" : "") + cellHTML(o.r, o.i) + "</tr>").join("");
      host._pages = pages;
    }
    host.innerHTML =
      '<div class="tbl-tools">' +
      "<span>" + rows.length + " " + esc(t.rows) + (useVirtual ? " · " + esc(t.virtual_on) : "") + "</span>" +
      '<button class="tbtn btn" data-tact="flt" aria-pressed="' + st.showFlt + '">' + esc(t.filter) + "</button>" +
      '<button class="tbtn btn" data-tact="density" aria-pressed="' + st.compact + '">' + esc(t.density) + "</button>" +
      (flags.count ? '<button class="tbtn btn" data-tact="anom" aria-pressed="' + st.onlyAnom +
        '">⚠ ' + flags.count + " " + esc(t.anomalies) + "</button>" : "") +
      (useVirtual ? '<button class="tbtn btn" data-tact="all">' + esc(t.render_all) + "</button>" : "") +
      '<span style="flex:1"></span>' +
      (useVirtual ? "" : '<label>' + esc(t.per_page) +
        " <select data-tact='per'>" + [25, 50, 100, 0].map(n =>
        "<option value='" + n + "'" + (st.per === n ? " selected" : "") + ">" +
        (n || esc(t.all_rows)) + "</option>").join("") + "</select></label>") +
      '<button class="tbtn btn" data-tact="csv">' + esc(t.export_view) + "</button>" +
      '<button class="tbtn btn" data-tact="csvfile">' + esc(t.download) + "</button>" +
      "</div>" + toolsH +
      "<div class='tbl-wrap'><table class='tbl" + (st.compact ? " compact" : "") +
      "'><thead>" + headHTML() + "</thead><tbody></tbody></table></div>" +
      (useVirtual ? "" : "<div class='pager'></div>");
    const tbody = host.querySelector("tbody");
    const wr = host.querySelector(".tbl-wrap");
    if (useVirtual) {
      const total = rows.length;
      const paint = () => {
        const st2 = wr.scrollTop;
        const vh = wr.clientHeight || 480;
        const start = Math.max(0, Math.floor(st2 / rh) - 10);
        const end = Math.min(total, Math.ceil((st2 + vh) / rh) + 10);
        let h = "<tr style='height:" + (start * rh) + "px'><td colspan='" +
          table.columns.length + "'></td></tr>";
        for (let i = start; i < end; i++) {
          const o = rows[i];
          h += "<tr data-ri='" + o.i + "'>" + cellHTML(o.r, o.i) + "</tr>";
        }
        h += "<tr style='height:" + ((total - end) * rh) + "px'><td colspan='" +
          table.columns.length + "'></td></tr>";
        tbody.innerHTML = h;
      };
      wr.onscroll = () => requestAnimationFrame(paint);
      paint();
    } else {
      tbody.innerHTML = bodyH;
      const pages = host._pages || 1;
      const pg = host.querySelector(".pager");
      if (pg) {
        pg.innerHTML =
          "<button data-pg='-1'" + (st.page <= 1 ? " disabled" : "") + ">‹</button>" +
          "<span class='num'>" + esc(t.page) + " " + st.page + " " + esc(t.of) + " " + pages + "</span>" +
          "<button data-pg='1'" + (st.page >= pages ? " disabled" : "") + ">›</button>";
      }
    }
    /* 事件委托 */
    host.querySelectorAll("thead th[data-col]").forEach(th => {
      th.onclick = () => {
        const ci = Number(th.dataset.col);
        st.sort = st.sort && st.sort.col === ci && st.sort.dir > 0
          ? {col:ci, dir:-1} : {col:ci, dir:1};
        render();
      };
    });
    host.querySelectorAll("input[data-fcol]").forEach(inp => {
      inp.oninput = () => { st.filters[inp.dataset.fcol] = inp.value;
        st.page = 1; clearTimeout(inp._h);
        inp._h = setTimeout(() => { render();
          const again = host.querySelector("input[data-fcol='" + inp.dataset.fcol + "']");
          if (again) { again.focus(); again.setSelectionRange(again.value.length, again.value.length); } }, 250); };
    });
    /* Vbit 列标题下拉：切换进制（全局），重绘表格与图表 */
    host.querySelectorAll("[data-vbsel]").forEach(sel => {
      sel.onclick = ev => ev.stopPropagation();
      sel.onchange = () => {
        VBIT.fmt = sel.value;
        localStorage.setItem("rpt.vbitfmt", VBIT.fmt);
        $$(".tbl-host").forEach(h => { delete h.dataset.done; h.innerHTML = ""; });
        armTables();
        $$(".chart-box").forEach(bx => { if (bx.dataset.rendered) drawChart(bx); });
      };
    });
    host.querySelectorAll("[data-tact]").forEach(b => {
      const act = b.dataset.tact;
      if (act === "per") { b.onchange = () => { st.per = Number(b.value); st.page = 1; render(); }; return; }
      b.onclick = () => {
        if (act === "flt") st.showFlt = !st.showFlt;
        if (act === "density") st.compact = !st.compact;
        if (act === "anom") { st.onlyAnom = !st.onlyAnom; st.page = 1; }
        if (act === "all") st.renderAll = true;
        if (act === "csv") exportCSV(item, rows);
        if (act === "csvfile") exportCSV(item, table.data.map((r, i) => ({r, i})), table.file);
        if (act !== "csv" && act !== "csvfile") render();
      };
    });
    const pg = host.querySelector(".pager");
    if (pg) pg.querySelectorAll("[data-pg]").forEach(b => {
      b.onclick = () => { st.page += Number(b.dataset.pg); render(); };
    });
    tbody.querySelectorAll("tr[data-ri]").forEach(tr => {
      tr.onclick = () => { tbody.querySelectorAll("tr.sel")
        .forEach(x => x.classList.remove("sel")); tr.classList.add("sel"); };
    });
    /* 异常标记：行首图标（固定槽位，未异常行补占位，保证列宽/对齐一致） */
    const anyFlag = Object.keys(flags.rows).length > 0;
    if (anyFlag) tbody.querySelectorAll("tr[data-ri]").forEach(tr => {
      const ri = Number(tr.dataset.ri);
      const td = tr.querySelector("td");
      if (!td) return;
      if (flags.rows[ri]) {
        td.insertAdjacentHTML("afterbegin",
          "<span class='rowflag' style='color:var(--" +
          (flags.rows[ri] === "fail" ? "fail'>✗" : "warn'>⚠") + ")</span>");
      } else {
        td.insertAdjacentHTML("afterbegin",
          "<span class='rowflag rowflag--ph' aria-hidden='true'>⚠</span>");
      }
    });
  };
  render();
}
function exportCSV(item, rows, fname) {
  const table = item.table;
  const head = table.columns.map(c =>
    c.label + (c.unit ? " (" + c.unit + ")" : ""));
  const lines = [head.join(",")].concat(rows.map(o =>
    o.r.map((v, ci) => {
      if (v === null || v === undefined) return "";
      let s = String(v);
      if (table.columns[ci] && table.columns[ci].kind === "image") {
        const att = (item.attachments || [])[v];
        s = att ? String(att.label || "") : "";
      }
      return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    }).join(",")));
  const blob = new Blob(["﻿" + lines.join("\r\n")], {type:"text/csv;charset=utf-8"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = fname || (item.item_key + "_view.csv");
  a.click(); URL.revokeObjectURL(a.href);
}
function armTables() {
  $$(".tbl-host").forEach(host => {
    if (host.dataset.done) return;
    const item = (REPORT_DATA.items || []).find(it => it.item_key === host.dataset.item);
    if (item) { host.dataset.done = "1"; buildTable(host, item); }
  });
  /* 更新 section 头部异常聚合 */
  const t = T();
  $$("[data-anom]").forEach(n => {
    const c = (window._anom || {})[n.dataset.anom] || 0;
    n.textContent = c ? "⚠ " + c + " " + t.anomalies : "";
    n.style.display = c ? "" : "none";
    n.onclick = () => {
      const item2 = (REPORT_DATA.items || [])
        .find(it => it.item_key === n.dataset.anom);
      const host = $(".tbl-host[data-item='" + n.dataset.anom + "']");
      if (!host || !item2) return;
      const det = host.closest("details");
      if (det) det.open = true;
      host.dataset.onlyAnom = "1";
      host.innerHTML = ""; host.dataset.done = "1";
      buildTable(host, item2);
    };
  });
  const k = $("#kpiAnom");
  if (k) k.textContent = Object.values(window._anom || {}).reduce((a, b) => a + b, 0);
}

/* ================================================================
 * lightbox —— 截图灯箱（←/→/Esc、滚轮缩放、caption）
 * ================================================================ */
const LB = {list:[], idx:0, scale:1};
function openLightbox(itemKey, shotIdx) {
  const item = (REPORT_DATA.items || []).find(it => it.item_key === itemKey);
  if (!item) return;
  LB.list = (item.attachments || []).filter(a => a.type === "image");
  LB.idx = Math.max(0, shotIdx); LB.scale = 1;
  paintLb();
  $("#lightbox").classList.add("show");
}
function paintLb() {
  const a = LB.list[LB.idx]; if (!a) return;
  const img = $("#lbImg");
  img.src = a.full; img.style.transform = "scale(" + LB.scale + ")";
  $("#lbCap").textContent = (a.label || "") + "  (" + (LB.idx + 1) + "/" + LB.list.length + ")";
}
function closeLightbox() { $("#lightbox").classList.remove("show"); }
function stepLb(d) {
  if (!LB.list.length) return;
  LB.idx = (LB.idx + d + LB.list.length) % LB.list.length; LB.scale = 1; paintLb();
}

/* ================================================================
 * search —— 跨测试项/指标/item_key 模糊匹配
 * ================================================================ */
function doSearch(q) {
  const pop = $("#searchPop");
  q = q.trim().toLowerCase();
  if (!q) { pop.classList.remove("show"); return; }
  const hits = [];
  (REPORT_DATA.items || []).forEach(it => {
    const hay = [it.title, it.item_key,
      ...(it.metrics || []).map(m => m.label)].join(" ").toLowerCase();
    if (hay.includes(q)) hits.push(it);
  });
  pop.innerHTML = hits.length
    ? hits.map(it => "<button role='option' data-jump='item-" + it.index + "'>" +
      "<b>" + esc(it.title) + "</b> <span class='mono' style='color:var(--ink-3)'>" +
      esc(it.item_key) + "</span></button>").join("")
    : "<button disabled>" + esc(T().no_data) + "</button>";
  pop.classList.add("show");
  pop.querySelectorAll("[data-jump]").forEach(b => {
    b.onclick = () => { jumpTo(b.dataset.jump); pop.classList.remove("show"); };
  });
}
function jumpTo(id) {
  const sec = document.getElementById(id);
  if (!sec) return;
  sec.classList.remove("collapsed");
  const det = sec.querySelector("details.panel");
  if (location.hash === "#" + id) {} else history.replaceState(null, "", "#" + id);
  sec.scrollIntoView({behavior:"smooth", block:"start"});
  sec.classList.remove("flash"); void sec.offsetWidth; sec.classList.add("flash");
}

/* ================================================================
 * scroll-spy + 阅读进度
 * ================================================================ */
function armSpy() {
  const links = $$("#toc a[data-target]");
  const bar = $("#readBar");
  let ticking = false;
  const onScroll = () => {
    if (ticking) return; ticking = true;
    requestAnimationFrame(() => {
      const pos = window.pageYOffset + 120;
      let id = null;
      $$(".item[id]").forEach(s2 => {
        if (s2.getBoundingClientRect().top + window.pageYOffset <= pos) id = s2.id;
      });
      links.forEach(l => l.classList.toggle("active", l.dataset.target === id));
      const h = document.documentElement;
      const p = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
      if (bar) bar.style.width = (p * 100).toFixed(1) + "%";
      ticking = false;
    });
  };
  window.addEventListener("scroll", onScroll, {passive:true});
  onScroll();
}

/* ================================================================
 * toolbar / 状态持久化 / 键盘 / 打印
 * ================================================================ */
function paintToolbar() {
  const t = T();
  $("#btnPdf").textContent = t.pdf;
  $("#btnTheme").textContent = S.theme === "dark" ? t.theme_light : t.theme_dark;
  $("#btnTheme").setAttribute("aria-pressed", String(S.theme === "dark"));
  $("#btnLang").textContent = t.lang;
  $("#btnUnit").textContent = S.unitScaled ? t.unit_on : t.unit;
  $("#btnUnit").setAttribute("aria-pressed", String(S.unitScaled));
  $("#btnExpandAll").textContent = S.expandedAll ? t.collapse : t.expand;
  $("#btnExpandAll").setAttribute("aria-pressed", String(S.expandedAll));
  $("#btnTop").textContent = t.top;
  $("#searchInput").placeholder = t.search_ph;
  const chips = [["ALL", t.chip_all], ["PASS", "PASS"], ["FAIL", "FAIL"], ["N/A", "N/A"]];
  $("#verdictChips").innerHTML = chips.map(c =>
    "<button class='chip' data-chip='" + c[0] + "' aria-pressed='" +
    String(S.chip === c[0]) + "'>" + esc(c[1]) + "</button>").join("");
  $$("#verdictChips .chip").forEach(b => {
    b.onclick = () => {
      S.chip = b.dataset.chip; paintToolbar();
      $$("#matrix tbody tr").forEach(tr => {
        tr.style.display = S.chip === "ALL" || tr.dataset.v === S.chip ? "" : "none";
      });
    };
  });
  document.title = (REPORT_DATA.meta || {}).report_title || "Report";
}
function rerender() {
  document.documentElement.dataset.theme = S.theme;
  document.documentElement.lang = S.lang === "zh" ? "zh-CN" : "en";
  paintToolbar(); renderCover(); renderKpis(); renderMeta();
  renderItems(); renderAppendix(); renderToc();
  armTables(); renderMatrix(); armLazyCharts(); armSpy();
}
function bindGlobal() {
  $("#btnPdf").onclick = () => window.print();
  $("#btnTheme").onclick = () => {
    S.theme = S.theme === "dark" ? "light" : "dark";
    localStorage.setItem("rpt.theme", S.theme);
    document.documentElement.dataset.theme = S.theme;
    paintToolbar();
    /* 图表颜色随主题：强制重绘已渲染图表 */
    $$(".chart-box").forEach(b => { if (b.dataset.rendered) drawChart(b); });
  };
  $("#btnLang").onclick = () => {
    S.lang = S.lang === "zh" ? "en" : "zh";
    localStorage.setItem("rpt.lang", S.lang);
    rerender();
  };
  $("#btnUnit").onclick = () => {
    S.unitScaled = !S.unitScaled;
    localStorage.setItem("rpt.unit", S.unitScaled ? "1" : "0");
    rerender();
  };
  $("#btnExpandAll").onclick = () => {
    S.expandedAll = !S.expandedAll;
    $$(".item").forEach(s2 => s2.classList.toggle("collapsed", !S.expandedAll));
    $$(".item details.panel").forEach(d => { d.open = S.expandedAll; });
    paintToolbar();
  };
  $("#btnTop").onclick = () => window.scrollTo({top:0, behavior:"smooth"});
  $("#btnToc").onclick = () => $("#toc").classList.toggle("open");
  $("#searchInput").addEventListener("input", e => doSearch(e.target.value));
  $("#searchInput").addEventListener("keydown", e => {
    if (e.key === "Enter") {
      const first = $("#searchPop [data-jump]");
      if (first) { jumpTo(first.dataset.jump); $("#searchPop").classList.remove("show"); }
    }
    if (e.key === "Escape") $("#searchPop").classList.remove("show");
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".search")) $("#searchPop").classList.remove("show");
  });
  /* item 卡片内按钮/图表工具条（事件委托） */
  $("#items").addEventListener("click", e => {
    const fold = e.target.closest("[data-act='fold']");
    if (fold) {
      const sec2 = fold.closest(".item");
      sec2.classList.toggle("collapsed");
      fold.textContent = sec2.classList.contains("collapsed") ? "▸" : "▾";
      return;
    }
    const link = e.target.closest("[data-act='link']");
    if (link) {
      const sec2 = link.closest(".item");
      const url = location.href.split("#")[0] + "#" + sec2.id;
      (navigator.clipboard ? navigator.clipboard.writeText(url)
        : Promise.reject()).then(() => toast(T().copied),
        () => toast(url));
      return;
    }
    const cb = e.target.closest("[data-cact]");
    if (cb) {
      const box = cb.closest(".chart-card").querySelector(".chart-box");
      const st = _chartState.get(box);
      const act = cb.dataset.cact;
      if (act === "png") exportChartPng(box,
        (REPORT_DATA.items.find(it => it.item_key === box.dataset.item) || {}).item_key);
      if (act === "reset" && st) { st.dom = null; drawChart(box); }
      if (act === "logx" && st) { st.logx = !st.logx; st.dom = null;
        cb.setAttribute("aria-pressed", String(st.logx)); drawChart(box); }
      if (act === "logy" && st) { st.logy = !st.logy; st.dom = null;
        cb.setAttribute("aria-pressed", String(st.logy)); drawChart(box); }
      return;
    }
    const shot = e.target.closest(".shot");
    if (shot) openLightbox(shot.dataset.item, Number(shot.dataset.shot));
  });
  /* lightbox */
  $("#lbClose").onclick = closeLightbox;
  $("#lbPrev").onclick = () => stepLb(-1);
  $("#lbNext").onclick = () => stepLb(1);
  $("#lightbox").addEventListener("click", e => {
    if (e.target.id === "lightbox") closeLightbox(); });
  $("#lightbox").addEventListener("wheel", e => {
    e.preventDefault();
    LB.scale = Math.max(0.4, Math.min(5, LB.scale * (e.deltaY < 0 ? 1.15 : 0.87)));
    paintLb();
  }, {passive:false});
  /* details 展开时武装表格（懒） */
  document.addEventListener("toggle", e => {
    if (e.target.matches("details") && e.target.open) armTables();
  }, true);
  /* 键盘 */
  document.addEventListener("keydown", e => {
    if (e.target.matches("input,textarea")) return;
    const items = $$(".item[id]");
    const cur = items.findIndex(s2 => {
      const r = s2.getBoundingClientRect();
      return r.top <= 140 && r.bottom > 140;
    });
    if (e.key === "/") { e.preventDefault(); $("#searchInput").focus(); }
    if (e.key === "?" ) { paintKbd(); $("#kbdModal").classList.add("show"); }
    if (e.key === "Escape") { closeLightbox(); $("#kbdModal").classList.remove("show"); }
    if (e.key === "ArrowLeft" && $("#lightbox").classList.contains("show")) stepLb(-1);
    if (e.key === "ArrowRight" && $("#lightbox").classList.contains("show")) stepLb(1);
    if (e.key === "j" || e.key === "k") {
      const nxt = items[Math.max(0, Math.min(items.length - 1,
        cur + (e.key === "j" ? 1 : -1)))];
      if (nxt) jumpTo(nxt.id);
    }
    if (e.key === "e" && cur >= 0) items[cur].classList.toggle("collapsed");
  });
  $("#kbdModal").addEventListener("click", e => {
    if (e.target.id === "kbdModal") $("#kbdModal").classList.remove("show"); });
  /* 打印前：强制浅色 + 展开全部 + 渲染全部图表；表格截断提示 */
  window.addEventListener("beforeprint", () => {
    document.documentElement.dataset.theme = "light";
    $$(".item").forEach(s2 => s2.classList.remove("collapsed"));
    $$("details").forEach(d => { d.dataset.wasOpen = d.open ? "1" : ""; d.open = true; });
    renderAllCharts(); armTables();
    $$(".tbl-wrap").forEach(w2 => {
      const rows = w2.querySelectorAll("tbody tr[data-ri]");
      if (rows.length > 200 && !w2.dataset.trimmed) {
        w2.dataset.trimmed = "1";
        rows.forEach((tr, i) => { if (i >= 100) tr.remove(); });
        const note = el("div", "tbl-banner",
          T().truncated + " 100 " + T().rows_omitted);
        w2.after(note);
      }
    });
  });
  window.addEventListener("afterprint", () => {
    document.documentElement.dataset.theme = S.theme;
    $$("details").forEach(d => { if (!d.dataset.wasOpen) d.open = false; });
  });
  window.addEventListener("resize", () => {
    $$(".chart-box").forEach(b => { if (b.dataset.rendered) drawChart(b); });
  });
}
function paintKbd() {
  const t = T();
  $("#kbdTitle").textContent = t.kbd;
  const rows = [["/", t.search_ph], ["j / k", "↑/↓ item"], ["e", "collapse"],
    ["?", t.kbd_open], ["Esc", "close"], ["← / →", "lightbox"]];
  $("#kbdTable").innerHTML = rows.map(r =>
    "<tr><td>" + esc(r[0]) + "</td><td>" + esc(r[1]) + "</td></tr>").join("");
}

/* ================================================================ boot */
rerender();
bindGlobal();
/* URL Hash 深链：#item-N 直达并展开数据表 */
if (location.hash) {
  const sec = document.querySelector(location.hash);
  if (sec && sec.classList.contains("item")) {
    sec.classList.remove("collapsed");
    const det = sec.querySelector("details.panel");
    if (det) det.open = true;
    setTimeout(() => sec.scrollIntoView({block:"start"}), 60);
  }
}
</script>
</body>
</html>
"""


def build_module_html_report(result: ModuleTestResult) -> str:
    """生成工程级单文件 HTML 报告字符串（数据=REPORT_DATA JSON，视图=原生JS）。"""
    data = build_report_data(result)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = data["meta"]["report_title"]
    return (_TEMPLATE
            .replace("__TITLE__", html.escape(title))
            .replace("__HEAD_COMMENT__", _HEAD_COMMENT)
            .replace("__REPORT_DATA__", payload))


def save_html_report(result: ModuleTestResult, out_dir: str) -> str:
    """生成 HTML 报告并落盘，返回文件路径。"""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "report.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_module_html_report(result))
    logger.info("模块测试报告已生成: %s", path)
    return path
