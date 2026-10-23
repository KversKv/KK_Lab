"""REPORT_DATA 数据构建：ModuleTestResult -> dict（原 report.py 数据段，纯函数，禁 Qt）。"""
from __future__ import annotations

import base64
import csv
import os
import re
from datetime import datetime
from typing import Any

from log_config import get_logger

import debug_config

from core.module_test.result_model import ItemResult, ModuleTestResult
from core.module_test._common import load_reg_summary

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


def _vout_step_rule_params(it: ItemResult) -> tuple[float, float] | None:
    """Vout Scan 异常判定参数 (参考步进, 容差)。

    基线必须取有效段平均步进（step_mv）：全段算术均值会被死区/饱和平台
    拉偏（曾致整列正常步进全部误报为异常）。容差 = 5% 平均步进（实测
    线性段步进噪声约 ±1.5%，5% 兼顾抗噪与捕捉饱和起始点的步进压缩）。
    """
    m = it.measured if isinstance(it.measured, dict) else {}
    step_mv = _num(m.get("step_mv"))
    if step_mv is None or abs(step_mv) <= 1e-9:
        return None
    return step_mv, 0.05 * abs(step_mv)


def _build_rules(it: ItemResult, table: dict[str, Any] | None) -> list[dict[str, Any]]:
    """按测试项生成异常检测规则（JS 侧求值，对缺失列容错）。"""
    if not table:
        return []
    key = it.item_key
    rules: list[dict[str, Any]] = []
    if key.endswith("vout_scan"):
        diff = _pick_col(table, "diff")
        params = _vout_step_rule_params(it)
        if diff and params is not None:
            step_mv, tol = params
            rules.append({"column": diff, "op": "dev_gt",
                          "ref": step_mv, "value": tol,
                          "level": "warn",
                          "hint": "步进偏离有效段平均步进超出容差（死区/饱和/孤立毛刺）"})
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
    elif key.endswith("ripple"):
        # 带载拐点后 Vout 崩溃的行整行标红（无效数据，已排除出性能计算）；
        # 阈值 = 拐点前后 Vout 中点（core 侧已判定，前端仅按 lt 规则着色）
        m = it.measured if isinstance(it.measured, dict) else {}
        thr = _num(m.get("collapse_vout_threshold_mv"))
        vout = _pick_col(table, "vout")
        if thr is not None and vout:
            rules.append({"column": vout, "op": "lt", "value": thr,
                          "level": "fail",
                          "hint": "超出 Max Load 带载拐点，Vout 崩溃，数据无效不参与性能计算"})
    return rules


def _mk(key: str, label: str, value: Any, unit: str = "",
        precision: int = 3) -> dict[str, Any] | None:
    """构建单条 metric；value 缺失返回 None（调用方过滤）。"""
    v = _num(value)
    if v is None:
        return None
    return {"key": key, "label": label, "value": v, "unit": unit,
            "precision": precision}


def _build_metrics(it: ItemResult, table: dict[str, Any] | None) -> list[dict[str, Any]]:
    """按测试项语义生成结构化关键指标。"""
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
        # Avg Step 计算范围 = 有效线性段（与 step_mv 口径一致），标签注明 Vbit 区间
        vmin, vmax = _num(m.get("valid_min_code")), _num(m.get("valid_max_code"))
        step_label = ("Avg Step" if vmin is None or vmax is None
                      else f"Avg Step (Vbit {int(vmin):#04x}~{int(vmax):#04x})")
        def _hex(code: Any) -> str:
            c = _num(code)
            return f" (0x{int(c):02X})" if c is not None else ""
        # 顺序即结论汇总表「关键指标」取舍依据（前端取前 2 条）：Default + 有效步进优先
        out = [
            _mk("default_mv", f"Default{_hex(m.get('default_code'))}",
                m.get("default_voltage_mv"), "mV"),
            _mk("step_mv", step_label, m.get("step_mv"), "mV"),
            _mk("vout_min", f"Min{_hex(m.get('valid_min_code'))}",
                m.get("vout_min_mv") or (min(vs) if vs else None), "mV"),
            _mk("vout_max", f"Max{_hex(m.get('valid_max_code'))}",
                m.get("vout_max_mv") or (max(vs) if vs else None), "mV"),
            _mk("linearity_pct", "Linearity", m.get("linearity_pct"), "%"),
        ]
    elif key.endswith("load_reg"):
        # 双区间指标：线性区（≤拐点）与全段，标签标明电流条件
        knee = _num(m.get("knee_ma"))
        lin_d = _num(m.get("vout_drop_linear_mv"))
        lin_p = _num(m.get("load_reg_linear_pct"))
        drop = _num(m.get("vout_drop_mv"))
        pct = _num(m.get("load_reg_pct"))
        i0 = i1 = None
        if len(cols) >= 2 and body:
            rows = [[_num(r[0]), _num(r[1])] for r in body
                    if _num(r[0]) is not None and _num(r[1]) is not None]
            if len(rows) >= 2:
                i0, i1 = rows[0][0], rows[-1][0]
                if knee is None or lin_d is None or lin_p is None \
                        or drop is None or pct is None:
                    s = load_reg_summary(rows)  # 旧结果兜底：从 CSV 重算
                    knee = knee if knee is not None else s["knee_ma"]
                    lin_d = lin_d if lin_d is not None else s["vout_drop_linear_mv"]
                    lin_p = lin_p if lin_p is not None else s["load_reg_linear_pct"]
                    drop = drop if drop is not None else s["vout_drop_mv"]
                    pct = pct if pct is not None else s["load_reg_pct"]
        rng = f"{i0:g}~{i1:g}mA" if (i0 is not None and i1 is not None) else "全段"
        out = [
            _mk("load_reg_linear_pct",
                f"Load Reg (≤{knee:g}mA)" if knee is not None
                else "Load Reg (线性区)", lin_p, "%"),
            _mk("vout_drop_linear",
                f"ΔV (≤{knee:g}mA)" if knee is not None
                else "ΔV (线性区)", lin_d, "mV"),
            _mk("load_reg_pct", f"Load Reg ({rng})", pct, "%"),
            _mk("vout_drop", f"ΔV ({rng})", drop, "mV"),
        ]
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
        out = [_mk("divin", "dIvin", m.get("dIvin (uA)"), "uA"),
               _mk("divout", "dIvout", m.get("dIvout (uA)"), "uA"),
               _mk("vin", "Vin", m.get("Vin (V)"), "V"),
               _mk("vout", "Vout", m.get("Vout (V)"), "V")]
    elif key.endswith("ripple"):
        if "max_vpp_mv" in m:
            out = [_mk("max_vpp", "Max Vpp", m.get("max_vpp_mv"), "mV", 2),
                   _mk("max_vpp_at", "@ Iload", m.get("max_vpp_at_ma"), "mA", 0),
                   _mk("max_load", "Max Load", m.get("max_load_ma"), "mA", 0)]
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
        if diff:  # 异常 diff 柱标红（与表格 dev_gt 规则一致：偏离有效段平均步进超容差）
            params = _vout_step_rule_params(it)
            if params is not None:
                step_mv, tol = params
                spec["bar_anomaly"] = {"key": diff, "op": "dev_gt",
                                       "ref": step_mv, "value": tol}
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

    返回的 keys 与附件同序：逐点截图为其 "Iload (mA)"（瞬态项为 "Group" 组号）
    数值（缺失/单波形图为 None），供 ``_embed_shots_column`` 把截图按 Iload 匹配进数据表末列。
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
            group = s.get("Group", "")
            iload = s.get("Iload (mA)", "")
            if str(group).strip():
                # Transient 项按组截图，键为组号（非 Iload 数值）
                label = f"Group {group}"
                keys.append(_num(group))
            else:
                label = f"Iload={iload}mA" if str(iload).strip() else "scope shot"
                keys.append(_num(iload))
            out.append({"type": "image", "label": label, "full": uri})
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


def build_report_data(result: ModuleTestResult,
                      xlsx_map: dict[str, str] | None = None) -> dict[str, Any]:
    """把 ModuleTestResult 序列化为 REPORT_DATA dict（唯一数据出口）。

    ``xlsx_map``：``{item_key: 报告目录相对路径}``（``XLSX/xxx.xlsx``），
    已生成单项 XLSX 的项在其工具条渲染「下载 XLSX」按钮；None = 全无。
    """
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
            # 单项 XLSX 相对路径（报告目录 XLSX/ 下，有则前端出「下载 XLSX」）
            "xlsx": (xlsx_map or {}).get(it.item_key) or None,
            "_rules": rules,  # 并入 table.rules，缺表时丢弃
        })
    for it_dict in items:  # rules 挂到 table 下（schema 约定）
        rules = it_dict.pop("_rules")
        if it_dict["table"] is not None:
            it_dict["table"]["rules"] = rules

    generated = datetime.now().astimezone().isoformat(sep=" ", timespec="seconds")
    # 各测试项耗时汇总（仅 debug_config.REPORT_ITEM_TIMING 开启时注入；性能调试用）
    item_timing = None
    if debug_config.REPORT_ITEM_TIMING:
        item_timing = [{
            "index": i,
            "item_key": it.item_key,
            "title": it.name,
            "duration_s": it.duration_s,
        } for i, it in enumerate(result.items, 1)
            if it.duration_s is not None] or None
    return {
        "meta": {
            "report_title": f"Module Test Report — {module}",
            "module_type": module,
            "chip": result.chip_name or None,
            "module_name": result.module_name or None,
            "test_condition": result.test_condition or None,
            "sample_id": None,
            "operator": result.operator or None,
            "temperature_c": temp_c,
            "vin_nominal_v": None,
            "vout_nominal_mv": None,
            "start_time": result.started_at or None,
            "end_time": result.finished_at or None,
            "duration_s": duration,
            "item_timing": item_timing,
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
