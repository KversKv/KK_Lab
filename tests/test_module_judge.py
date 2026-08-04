#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core.module_test.judge 判定引擎单测（纯函数，无 Qt）。

固化契约：
- 全部测量值满足条件 → PASS；任一不满足 → FAIL；
- 无规则 / 规则全部无测量数据 → None（保持 N/A）；
- 指标提取覆盖 dict 标量 / list[dict] / {"rows": 无键行} 三种 measured 结构。
"""
from __future__ import annotations

import pytest

from core.module_test.judge import JUDGE_METRICS, MetricSpec, evaluate_item, extract_values


def _crit(metric: str, op: str, v1: float, v2: float | None = None) -> dict:
    return {"rules": [{"metric": metric, "op": op, "v1": v1, "v2": v2}]}


# ---------------------------------------------------------------------- 提取
def test_extract_scalar_dict():
    spec = MetricSpec("max_vpp_mv", "Max Vpp", "mV")
    assert extract_values({"max_vpp_mv": 8.5, "points": 3}, spec) == [8.5]


def test_extract_list_of_dict():
    spec = MetricSpec("Fsw (kHz)", "Fsw", "kHz")
    measured = [{"Iload (mA)": 0, "Fsw (kHz)": 1000.0},
                {"Iload (mA)": 100, "Fsw (kHz)": ""}]  # 空串跳过
    assert extract_values(measured, spec) == [1000.0]


def test_extract_rows_by_col():
    spec = MetricSpec("psrr_db", "PSRR", "dB", col=1)
    measured = {"rows": [[100, 60.0], [1000, 55.5]]}
    assert extract_values(measured, spec) == [60.0, 55.5]


# ---------------------------------------------------------------------- 判定
def test_pass_when_all_values_satisfy():
    passed, note = evaluate_item(
        "ldo_ripple", _crit("max_vpp_mv", "<", 10.0),
        {"max_vpp_mv": 8.5})
    assert passed is True
    assert "通过" in note


def test_fail_when_value_violates():
    passed, note = evaluate_item(
        "ldo_ripple", _crit("max_vpp_mv", "<", 10.0),
        {"max_vpp_mv": 12.3})
    assert passed is False
    assert "超规格" in note


def test_range_op():
    crit = _crit("Fsw (kHz)", "range", 900.0, 1100.0)
    assert evaluate_item("dcdc_switching_freq", crit,
                         [{"Fsw (kHz)": 1000.0}])[0] is True
    assert evaluate_item("dcdc_switching_freq", crit,
                         [{"Fsw (kHz)": 1200.0}])[0] is False


def test_all_values_must_satisfy():
    crit = _crit("psrr_db", ">", 50.0)
    measured = {"rows": [[100, 60.0], [1000, 40.0]]}
    assert evaluate_item("ldo_psrr", crit, measured)[0] is False


def test_no_rules_returns_none():
    assert evaluate_item("ldo_ripple", {"rules": []}, {"max_vpp_mv": 1.0})[0] is None
    assert evaluate_item("ldo_ripple", {}, {"max_vpp_mv": 1.0})[0] is None


def test_no_measurement_data_returns_none():
    # 示波器未接跳过等场景：无测量数据保持 N/A，不误判 FAIL
    passed, note = evaluate_item(
        "ldo_ripple", _crit("max_vpp_mv", "<", 10.0), {"points": 0})
    assert passed is None
    assert "N/A" in note


def test_unknown_metric_ignored():
    assert evaluate_item("ldo_ripple", _crit("not_a_metric", "<", 1.0),
                         {"max_vpp_mv": 1.0})[0] is None


def test_metrics_registry_covers_real_keys():
    # 抽样核对注册表指标键与 items 实际产出的 measured 键一致
    ldo_ripple = {m.key for m in JUDGE_METRICS["ldo_ripple"]}
    assert "max_vpp_mv" in ldo_ripple
    dcdc_eff = {m.key for m in JUDGE_METRICS["dcdc_efficiency"]}
    assert {"max_eff", "avg_eff"} <= dcdc_eff


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
