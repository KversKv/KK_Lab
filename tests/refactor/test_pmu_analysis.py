# -*- coding: utf-8 -*-
"""
Phase 1.2~1.5 — gpadc / dcdc / isgain / oscp 纯函数单测（无 pytest 也可独立运行）。

    python tests/refactor/test_pmu_analysis.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.pmu_test.gpadc import gpadc_analysis as ga
from core.pmu_test.dcdc import dcdc_analysis as da
from core.pmu_test.isgain import isgain_analysis as ia
from core.pmu_test.oscp import oscp_analysis as oa


# ── gpadc ──────────────────────────────────────────────

def test_gpadc_compute_reg_stats():
    avg, mx, mn = ga.compute_reg_stats([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    assert mn == 1
    assert mx == 10
    assert 4.0 <= avg <= 7.0


def test_gpadc_compute_reg_stats_return_raw():
    avg, mx, mn, raw = ga.compute_reg_stats([1, 2, 3, 4, 5], return_raw=True)
    assert raw == [1, 2, 3, 4, 5]
    assert mn == 1 and mx == 5


def test_gpadc_compute_calibration():
    k, b, mc, mic, mac, vl, ml, vh, mh = ga.compute_calibration(
        [1.0, 2.0, 3.0, 4.0],
        [10.0, 20.0, 30.0, 40.0],
        [9.0, 19.0, 29.0, 39.0],
        [11.0, 21.0, 31.0, 41.0],
    )
    assert k == 10.0
    assert b == 0.0
    assert mc == [1.0, 2.0, 3.0, 4.0]


def test_gpadc_generate_linearity_values():
    assert ga.generate_linearity_values(0.0, 10.0, 2.0) == [0, 2, 4, 6, 8, 10]
    assert ga.generate_linearity_values(0.0, 10.0, 3.0) == [0, 3, 6, 9, 10]
    assert ga.generate_linearity_values(0.0, 1.0, 0.1) == [0, 1]
    assert ga.generate_linearity_values(5.0, 5.0, 1.0) == [5]
    expected = [0x3B00 + index * 10 for index in range(34)] + [0x3C50]
    assert ga.generate_linearity_values(0x3B00, 0x3C50, 10) == expected
    for args in (
        (1.0, 0.0, 1.0),
        (0.0, 1.0, 0.0),
        (-1.0, 1.0, 1.0),
        (0.0, float("nan"), 1.0),
    ):
        try:
            ga.generate_linearity_values(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"非法线性度序列未拒绝: {args}")


def test_gpadc_generate_linearity_pairs():
    linked = {
        "linearity_link_np": True,
        "linearity_start": 0, "linearity_end": 2,
        "linearity_value_start": 0.0, "linearity_value_end": 2.0,
        "linearity_value_step": 1.0,
    }
    assert ga.generate_linearity_pairs(linked) == [(0, 0), (1, 1), (2, 2)]
    independent = {
        "linearity_link_np": False,
        "linearity_n_start": 0, "linearity_n_end": 2,
        "linearity_n_value_start": 0.0, "linearity_n_value_end": 2.0,
        "linearity_n_value_step": 2.0,
        "linearity_p_start": 1, "linearity_p_end": 3,
        "linearity_p_value_start": 1.0, "linearity_p_value_end": 3.0,
        "linearity_p_value_step": 1.0,
    }
    assert ga.generate_linearity_pairs(independent) == [
        (0, 1), (0, 2), (0, 3), (2, 1), (2, 2), (2, 3),
    ]


def test_gpadc_analyze_linearity_group_independent_calibration():
    mean = [11.0, 20.0, 31.0, 40.0]
    sweep = {
        "voltage": [1.0, 2.0, 3.0, 4.0],
        "mean": mean,
        "min": [value - 1.0 for value in mean],
        "max": [value + 1.0 for value in mean],
    }
    group = ga.analyze_linearity_group(0x12, 0x34, sweep)
    assert group["n_value"] == 0x12
    assert group["p_value"] == 0x34
    assert group["k"] == 10.0 and group["b"] == 0.0
    assert all(
        abs(actual - expected) < 1e-9
        for actual, expected in zip(group["error_mv"], [100.0, 0.0, 100.0, 0.0])
    )
    assert abs(group["max_abs_mv"] - 100.0) < 1e-9
    assert abs(group["rms_mv"] - (5000.0 ** 0.5)) < 1e-9
    assert group["raw"] is sweep


def test_gpadc_select_best_linearity_group_tie_breakers():
    groups = [
        {"n_value": 4, "p_value": 0, "max_abs_mv": 5.0, "rms_mv": 2.0, "error_mv": [5.0]},
        {"n_value": 1, "p_value": 9, "max_abs_mv": 5.0, "rms_mv": 1.0, "error_mv": [5.0]},
        {"n_value": 1, "p_value": 2, "max_abs_mv": 5.0, "rms_mv": 1.0, "error_mv": [5.0]},
        {"n_value": 0, "p_value": 1, "max_abs_mv": 6.0, "rms_mv": 0.1, "error_mv": [6.0]},
    ]
    assert ga.select_best_linearity_group(groups) == 2
    assert ga.select_best_linearity_group([]) is None


def _run_linearity_auto_search(low, high, metric):
    cache = {}
    evaluated = []
    for _ in range(100):
        step = ga.advance_linearity_auto_best(low, high, cache)
        low, high = step["low"], step["high"]
        value = step["evaluate_value"]
        if value is not None:
            assert value not in cache
            evaluated.append(value)
            score = float(metric(value))
            cache[value] = {
                "n_value": value, "p_value": value,
                "max_abs_mv": score, "rms_mv": score, "error_mv": [score],
            }
            continue
        if step["done"]:
            groups = [cache[value] for value in sorted(cache)]
            best = groups[ga.select_best_linearity_group(groups, noise_aware=True)]
            return best["n_value"], evaluated, cache
    raise AssertionError("自动二分未在限定次数内收敛")


def test_gpadc_normalize_linearity_auto_range():
    assert ga.normalize_linearity_auto_range(0.4, 2.5) == (0, 3)
    assert ga.normalize_linearity_auto_range(3, 3) == (3, 3)
    for args in ((-1, 2), (2, 1), (0, float("nan"))):
        try:
            ga.normalize_linearity_auto_range(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"非法自动寻优范围未拒绝: {args}")


def test_gpadc_auto_best_binary_boundaries_and_cache():
    low, evaluated, cache = _run_linearity_auto_search(3, 3, lambda value: value)
    assert low == 3 and evaluated == [3] and list(cache) == [3]

    low, evaluated, cache = _run_linearity_auto_search(4, 5, lambda value: value)
    assert low == 4 and evaluated == [4, 5]

    low, evaluated, cache = _run_linearity_auto_search(
        0, 20, lambda value: (value - 7) ** 2,
    )
    assert low == 7 and evaluated == [0, 20, 10, 5, 7, 6]
    groups = [cache[value] for value in sorted(cache)]
    best = groups[ga.select_best_linearity_group(groups, noise_aware=True)]
    assert best["n_value"] == 7

    low, _, _ = _run_linearity_auto_search(0, 20, lambda value: value)
    assert low == 0
    low, _, _ = _run_linearity_auto_search(0, 20, lambda value: 20 - value)
    assert low == 20


def test_gpadc_auto_best_non_unimodal_returns_best_evaluated():
    def metric(value):
        if value == 13:
            return -100.0
        return float((value - 7) ** 2)

    _, _, cache = _run_linearity_auto_search(0, 20, metric)
    assert 13 not in cache
    groups = [cache[value] for value in sorted(cache)]
    best_index = ga.select_best_linearity_group(groups, noise_aware=True)
    assert groups[best_index]["max_abs_mv"] == min(
        group["max_abs_mv"] for group in groups
    )


def test_gpadc_aggregate_linearity_repeats_and_noise_comparison():
    repeats = [
        {"n_value": 8, "p_value": 8, "max_abs_mv": 10.0, "rms_mv": 4.0,
         "error_mv": [10.0], "raw": {"id": 1}},
        {"n_value": 8, "p_value": 8, "max_abs_mv": 12.0, "rms_mv": 3.0,
         "error_mv": [12.0], "raw": {"id": 2}},
        {"n_value": 8, "p_value": 8, "max_abs_mv": 11.0, "rms_mv": 5.0,
         "error_mv": [11.0], "raw": {"id": 3}},
    ]
    group = ga.aggregate_linearity_repeats(repeats)
    assert group["max_abs_mv"] == 11.0 and group["rms_mv"] == 4.0
    assert group["max_abs_range_mv"] == 2.0 and group["rms_range_mv"] == 2.0
    assert group["representative_repeat"] == 3
    assert group["raw"] == {"id": 3} and group["repeat_count"] == 3
    assert [item["repeat_index"] for item in group["repeat_results"]] == [1, 2, 3]

    even = ga.aggregate_linearity_repeats(repeats[:2])
    assert even["max_abs_mv"] == 11.0 and even["rms_mv"] == 3.5

    left = dict(group, max_abs_mv=10.0, rms_mv=5.0,
                max_abs_range_mv=2.0, rms_range_mv=1.0)
    right = dict(group, max_abs_mv=11.0, rms_mv=3.0,
                 max_abs_range_mv=2.0, rms_range_mv=1.0)
    assert ga.compare_linearity_candidates(left, right)["order"] == 1
    right["rms_mv"] = 5.5
    comparison = ga.compare_linearity_candidates(left, right)
    assert comparison["order"] == 0 and comparison["ambiguous"]

    single_left = dict(group, max_abs_mv=10.0, rms_mv=5.0,
                       max_abs_range_mv=0.0, rms_range_mv=0.0)
    single_right = dict(group, max_abs_mv=11.0, rms_mv=3.0,
                        max_abs_range_mv=0.0, rms_range_mv=0.0)
    assert ga.compare_linearity_candidates(single_left, single_right)["order"] == -1


# ── dcdc ───────────────────────────────────────────────

def test_dcdc_polyfit_linear():
    coeffs = da.polyfit([0, 1, 2, 3], [1, 3, 5, 7], 1)
    assert abs(coeffs[0] - 1.0) < 1e-9
    assert abs(coeffs[1] - 2.0) < 1e-9


def test_dcdc_savgol_smooth_identity():
    data = [1.0] * 9
    result = da.savgol_smooth(data, window=5, poly_order=2)
    assert all(abs(r - 1.0) < 1e-9 for r in result)


def test_dcdc_generate_current_points_linear():
    cfg = {
        "start_current_a": 0.01,
        "end_current_a": 0.05,
        "sweep_mode": "Linear",
        "step_current_a": 0.01,
    }
    pts = da.generate_current_points(cfg)
    assert len(pts) == 5
    assert abs(pts[0] - 0.01) < 1e-9
    assert abs(pts[-1] - 0.05) < 1e-9


def test_dcdc_generate_current_points_log():
    cfg = {
        "start_current_a": 0.001,
        "end_current_a": 0.1,
        "sweep_mode": "Log",
        "points_per_dec": 3,
    }
    pts = da.generate_current_points(cfg)
    assert len(pts) > 0
    assert pts[0] >= 0.001
    assert pts[-1] <= 0.1


def test_dcdc_generate_current_points_log_includes_end():
    cfg = {
        "start_current_a": 0.001,
        "end_current_a": 3.0,
        "sweep_mode": "Log",
        "points_per_dec": 5,
    }
    pts = da.generate_current_points(cfg)
    assert pts[-1] == 3.0
    assert len([p for p in pts if abs(p - 3.0) < 1e-9]) == 1


def test_dcdc_generate_current_points_log_end_on_grid_not_duplicated():
    cfg = {
        "start_current_a": 0.001,
        "end_current_a": 0.1,
        "sweep_mode": "Log",
        "points_per_dec": 3,
    }
    pts = da.generate_current_points(cfg)
    assert abs(pts[-1] - 0.1) < 1e-12
    assert len([p for p in pts if abs(p - 0.1) < 1e-9]) == 1


def test_dcdc_generate_current_points_linear_includes_end():
    cfg = {
        "start_current_a": 0.001,
        "end_current_a": 3.0,
        "sweep_mode": "Linear",
        "step_current_a": 0.5,
    }
    pts = da.generate_current_points(cfg)
    assert pts[-1] == 3.0
    assert pts == sorted(pts)
    assert len([p for p in pts if abs(p - 3.0) < 1e-9]) == 1


def test_dcdc_generate_current_points_custom():
    cfg = {
        "start_current_a": 0.001,
        "end_current_a": 3.0,
        "sweep_mode": "Custom",
        "custom_points": [0.5, 0.1, 0.5, 0.0, -1.0],
    }
    pts = da.generate_current_points(cfg)
    assert pts == [0.1, 0.5, 1.0]


def test_dcdc_generate_current_points_custom_empty_fallback():
    cfg = {
        "start_current_a": 0.001,
        "end_current_a": 0.2,
        "sweep_mode": "Custom",
        "custom_points": [],
    }
    pts = da.generate_current_points(cfg)
    assert pts == [0.001, 0.2]


def test_dcdc_trimmed_mean():
    assert da.trimmed_mean([1.0, 2, 3, 4, 5, 6, 7, 8, 9.0]) == 5.0


# ── isgain ─────────────────────────────────────────────

def test_isgain_parse_channel():
    assert ia.parse_channel("CH 1") == 1
    assert ia.parse_channel("CH 4") == 4


def test_isgain_prev_scale():
    assert ia.prev_scale(0.100) == 0.050
    assert ia.prev_scale(0.001) is None


def test_isgain_analyze_results():
    results = [
        {"voltage": 3.30, "load_current": 0.1, "ripple": 5.0},
        {"voltage": 3.28, "load_current": 0.2, "ripple": 8.0},
        {"voltage": 3.25, "load_current": 0.3, "ripple": 3.0},
    ]
    r = ia.analyze_results(results, v0=3.30)
    assert r["max_ripple"] == 8.0
    assert r["max_ripple_current"] == 0.2
    assert r["max_load_current"] == 0.2


# ── oscp ───────────────────────────────────────────────

def test_oscp_parse_hex_address():
    val = oa.parse_hex_address("0xFF", "reg", 0xFFFF)
    assert val == 255


def test_oscp_parse_hex_address_invalid():
    try:
        oa.parse_hex_address("xyz", "reg", 0xFFFF)
        assert False, "Should have raised"
    except ValueError:
        pass


def test_oscp_get_changed_bits():
    bits = oa.get_changed_bits(0b00001111, 0b00010001)
    assert bits == [1, 2, 3, 4]


def test_oscp_format_changed_bits():
    text = oa.format_changed_bits([0, 4, 7])
    assert "Bit0" in text
    assert "Bit4" in text
    assert "Bit7" in text


def test_oscp_generate_sweep_points_ovp():
    pts = oa.generate_sweep_points(0.7, 1.0, 0.1, "OVP")
    assert pts == [0.7, 0.8, 0.9, 1.0]


def test_oscp_generate_sweep_points_uvp():
    pts = oa.generate_sweep_points(1.0, 0.7, 0.1, "UVP")
    assert pts[0] == 1.0
    assert pts[-1] == 0.7
    assert len(pts) == 4


# ── runner ─────────────────────────────────────────────

if __name__ == "__main__":
    _fails = 0
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            try:
                _fn()
                print(f"  PASS  {_name}")
            except Exception as _e:
                _fails += 1
                print(f"  FAIL  {_name}: {_e}")
    print(f"\n{'='*40}\nResult: {len([n for n in globals() if n.startswith('test_')]) - _fails} passed, {_fails} failed")
    sys.exit(1 if _fails else 0)
