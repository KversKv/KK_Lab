"""Module Test 判定标准（PASS/FAIL Criteria）——指标注册表 + 判定引擎。

纯函数模块（无 Qt），供 runner 在测试项完成后按用户标准判定
``ItemResult.passed``。与报告里的**异常点标红**（report.py ``table.rules``
前端规则引擎）是两套独立机制：本模块决定测试项 verdict（PASS/FAIL/N/A），
异常标红仅视觉提示、不参与判定。

数据结构（可 JSON 序列化，随模块配置持久化）：

.. code-block:: python

    judge_criteria = {
        "ldo_ripple": {"rules": [
            {"metric": "max_vpp_mv", "op": "<", "v1": 10.0, "v2": None},
        ]},
    }

判定语义：
- 指标提取出多个测量值时，**全部值满足条件**才算该规则通过；
- 任一规则不通过 → 项 FAIL；全部规则通过 → 项 PASS；
- 无规则 / 规则全部无测量数据（如示波器未接跳过）→ 返回 None（保持 N/A）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MetricSpec:
    """可判定指标描述。

    Attributes:
        key: measured 中的键名（dict 标量键 / list[dict] 行键）。
        label: 可读名称（不含单位，单位单列）。
        unit: 单位字符串。
        col: measured 为 ``{"rows": [[...], ...]}``（无键行）时的列下标；
            为 None 时按 key 提取。
    """

    key: str
    label: str
    unit: str
    col: int | None = None


# 判定条件操作符（存储值 → 显示文本）
JUDGE_OPS: tuple[tuple[str, str], ...] = (
    ("<", "<"),
    ("<=", "≤"),
    (">", ">"),
    (">=", "≥"),
    ("range", "介于 [min, max]"),
)


def _m(key: str, label: str, unit: str, col: int | None = None) -> MetricSpec:
    return MetricSpec(key=key, label=label, unit=unit, col=col)


_VOUT_SCAN_METRICS = (
    _m("step_error_mv", "Step Error", "mV"),
    _m("linearity_pct", "Linearity", "%"),
)
_LINE_REG_METRICS = (
    _m("vout_span_mv", "Vout Span", "mV"),
    _m("line_reg_pct", "Line Reg", "%"),
)
_LOAD_REG_METRICS = (
    _m("vout_drop_mv", "Vout Drop", "mV"),
    _m("load_reg_pct", "Load Reg", "%"),
)
_QUIESCENT_METRICS = (
    _m("Iq (uA)", "Iq", "uA"),
    _m("dIvin (uA)", "dIvin", "uA"),
    _m("dIvout (uA)", "dIvout", "uA"),
)
_RIPPLE_METRICS = (
    _m("max_vpp_mv", "Max Vpp", "mV"),
    _m("max_vout_drop_mv", "Max Vout Drop", "mV"),
)
_TRANSIENT_METRICS = (
    _m("max_overshoot_mv", "Max Overshoot", "mV"),
    _m("max_undershoot_mv", "Max Undershoot", "mV"),
)
_PSRR_METRICS = (_m("psrr_db", "PSRR", "dB", col=1),)  # rows=[Freq, PSRR]
_CURRENT_LIMIT_METRICS = (_m("current_limit_ma", "Current Limit", "mA"),)

#: 各测试项可判定指标（键 = ITEMS_REGISTRY 的 item_key）。
#: measured 结构以 core/module_test/{ldo,dcdc}/items 与 _common.py 实际产出为准；
#: 无数值指标的项（protection / topology / output_noise）不列出。
JUDGE_METRICS: dict[str, tuple[MetricSpec, ...]] = {
    # ---- LDO / DCDC 共用项 ----
    "ldo_vout_scan": _VOUT_SCAN_METRICS,
    "dcdc_vout_scan": _VOUT_SCAN_METRICS,
    "ldo_load_reg": (
        _m("vout_drop_mv", "Vout Drop", "mV"),
        _m("load_reg_mv_per_a", "Load Reg", "mV/A"),
        _m("load_reg_pct", "Load Reg", "%"),
    ),
    "dcdc_load_reg": _LOAD_REG_METRICS,
    "ldo_line_reg": _LINE_REG_METRICS,
    "dcdc_line_reg": _LINE_REG_METRICS,
    "ldo_quiescent": _QUIESCENT_METRICS,
    "dcdc_quiescent": _QUIESCENT_METRICS,
    "ldo_ripple": _RIPPLE_METRICS,
    "dcdc_ripple": _RIPPLE_METRICS,
    "ldo_psrr": _PSRR_METRICS,
    "dcdc_psrr": _PSRR_METRICS,
    "ldo_load_transient": _TRANSIENT_METRICS,
    "dcdc_load_transient": _TRANSIENT_METRICS,
    "ldo_line_transient": _TRANSIENT_METRICS,
    "dcdc_line_transient": _TRANSIENT_METRICS,
    "ldo_current_limit": _CURRENT_LIMIT_METRICS,
    "dcdc_current_limit": _CURRENT_LIMIT_METRICS,
    # ---- LDO 专有 ----
    "ldo_dropout": (_m("dropout_mv", "Dropout", "mV"),),
    # ---- DCDC 专有 ----
    "dcdc_efficiency": (
        _m("max_eff", "Max Efficiency", "%"),
        _m("avg_eff", "Avg Efficiency", "%"),
    ),
    "dcdc_switching_freq": (_m("Fsw (kHz)", "Fsw", "kHz"),),  # list[dict]
    "dcdc_inductor_current": (  # rows=[Iload, Ipeak, Ivalley]
        _m("ipeak_ma", "Ipeak", "mA", col=1),
        _m("ivalley_ma", "Ivalley", "mA", col=2),
    ),
    "dcdc_startup": (_m("soft_start_ms", "Soft Start", "ms"),),
}


# ---------------------------------------------------------------------- 提取
def _to_float(value: Any) -> float | None:
    """宽松转 float；空串 / None / 非数值返回 None（跳过，不产生误判）。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_values(measured: Any, metric: MetricSpec) -> list[float]:
    """从 ItemResult.measured 提取指标的全部数值（无法提取返回空列表）。"""
    values: list[float] = []
    if metric.col is not None:
        rows = measured.get("rows") if isinstance(measured, dict) else None
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, (list, tuple)) and len(row) > metric.col:
                    v = _to_float(row[metric.col])
                    if v is not None:
                        values.append(v)
        return values

    if isinstance(measured, list):  # list[dict]（如 dcdc_switching_freq）
        candidates: Iterable[Any] = (
            r.get(metric.key) for r in measured if isinstance(r, dict))
    elif isinstance(measured, dict):
        if metric.key in measured:
            candidates = (measured[metric.key],)
        else:  # {"rows": [dict, ...]} 兜底
            rows = measured.get("rows")
            if isinstance(rows, list):
                candidates = (r.get(metric.key) for r in rows
                              if isinstance(r, dict))
            else:
                candidates = ()
    else:
        candidates = ()

    for raw in candidates:
        v = _to_float(raw)
        if v is not None:
            values.append(v)
    return values


# ---------------------------------------------------------------------- 判定
def _check(op: str, value: float, v1: float, v2: float | None) -> bool:
    if op == "<":
        return value < v1
    if op == "<=":
        return value <= v1
    if op == ">":
        return value > v1
    if op == ">=":
        return value >= v1
    if op == "range":
        lo, hi = v1, (v2 if v2 is not None else v1)
        return min(lo, hi) <= value <= max(lo, hi)
    return True  # 未知 op 不误判


def _op_text(op: str, v1: float, v2: float | None) -> str:
    if op == "range":
        return f"∈ [{v1:g}, {v2 if v2 is not None else v1:g}]"
    return f"{op} {v1:g}"


def evaluate_item(item_key: str, item_criteria: dict,
                  measured: Any) -> tuple[bool | None, str]:
    """按判定标准评估单个测试项。

    Returns:
        (passed, note)：passed=True/False 判定通过/失败；None 表示无法判定
        （无规则或规则全部无测量数据，保持 N/A）。note 为可读说明。
    """
    if not item_criteria:
        return None, ""
    # master 开关关闭时跳过判定（保持 N/A，规则仍保留在配置中）
    if item_criteria.get("enabled", True) is False:
        return None, "判定标准已关闭，跳过判定"
    rules = item_criteria.get("rules") or []
    if not rules:
        return None, ""
    specs = {m.key: m for m in JUDGE_METRICS.get(item_key, ())}

    evaluated = 0
    failures: list[str] = []
    for rule in rules:
        spec = specs.get(rule.get("metric", ""))
        if spec is None:
            continue
        values = extract_values(measured, spec)
        if not values:
            continue
        evaluated += 1
        try:
            v1 = float(rule.get("v1"))
            v2 = rule.get("v2")
            v2 = float(v2) if v2 is not None else None
        except (TypeError, ValueError):
            continue
        op = str(rule.get("op", "<"))
        bad = [v for v in values if not _check(op, v, v1, v2)]
        if bad:
            label = f"{spec.label} ({spec.unit})" if spec.unit else spec.label
            failures.append(
                f"{label} 超规格：{max(bad, key=abs):g} 不满足 "
                f"{_op_text(op, v1, v2)}")

    if evaluated == 0:
        return None, "判定标准无可用测量数据，保持 N/A"
    if failures:
        return False, "；".join(failures)
    return True, f"判定标准通过（{evaluated} 项指标均在规格内）"
