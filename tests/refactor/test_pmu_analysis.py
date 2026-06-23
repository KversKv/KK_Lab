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
