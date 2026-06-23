# -*- coding: utf-8 -*-
"""
Phase 1.1 — clk_analysis 纯函数单测（无 pytest 也可独立运行）。

    python tests/refactor/test_clk_analysis.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.pmu_test.clk import clk_analysis as ca


def test_simulate_frequency():
    assert ca.simulate_frequency(0) == 32768.0
    val = ca.simulate_frequency(10, nominal=1000.0, gain=2.0, noise=0.0)
    assert val == 1020.0


def test_float_range_ascending():
    result = ca.float_range(0, 1, 0.5)
    assert result == [0.0, 0.5, 1.0]


def test_float_range_descending():
    result = ca.float_range(10, 0, 5)
    assert result == [10.0, 5.0, 0.0]


def test_float_range_zero_step():
    assert ca.float_range(0, 10, 0) == []


def test_parse_tek_csv():
    lines = [
        "Name,Type,Source,Time,Delta\n",
        "Edge,Rise,CH1,0.000000,0.0000305\n",
        "Edge,Fall,CH1,0.0000305,0.0000305\n",
        "Edge,Rise,CH1,0.0000610,0.0000305\n",
        "Edge,Fall,CH1,0.0000610,0.0000305\n",
        "Edge,Rise,CH1,0.0000915,0.0000305\n",
        "Edge,Fall,CH1,0.0000915,0.0000305\n",
    ]
    samples = ca.parse_tek_csv(lines)
    assert len(samples) >= 1
    for t, p in samples:
        assert p > 0
        assert t >= 0


def test_parse_tek_csv_insufficient():
    try:
        ca.parse_tek_csv(["Name,Type,Source,Time,Delta\n", "Edge,Rise,CH1,0,1\n"])
        assert False, "Should have raised"
    except ValueError:
        pass


def test_parse_generic_csv():
    lines = ["0.0,0.0000305\n", "0.0000305,0.0000305\n", "0.0000610,0.0000305\n"]
    samples = ca.parse_generic_csv(lines)
    assert len(samples) == 3
    assert samples[0] == (0.0, 0.0000305)


def test_parse_dslogic_csv():
    lines = [
        "; Sample rate: 1 MHz\n",
        "Time,Value\n",
        "0.0,0\n",
        "0.000001,1\n",
        "0.000002,0\n",
        "0.000003,1\n",
        "0.000004,0\n",
        "0.000005,1\n",
    ]
    samples = ca.parse_dslogic_csv(lines)
    assert len(samples) >= 1
    for t, p in samples:
        assert p > 0


def test_analyze_clk_perf_basic():
    nominal = 32768.0
    period = 1.0 / nominal
    samples = [(i * period, period) for i in range(100)]
    result = ca.analyze_clk_perf(samples, ble_min_time=0.0, log_fn=None)
    assert result["mode"] == "clk_perf"
    assert "summary" in result
    s = result["summary"]
    assert abs(s["avg_freq"] - nominal) < 1.0
    assert s["period_jitter_pp_ns"] >= 0.0
    assert len(result["data"]) == 100


def test_analyze_clk_perf_empty():
    try:
        ca.analyze_clk_perf([])
        assert False, "Should have raised"
    except ValueError:
        pass


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  [PASS] {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\n  {passed} passed, {failed} failed, {len(tests)} total")
    return failed


if __name__ == "__main__":
    print("=== test_clk_analysis (standalone) ===")
    sys.exit(1 if _run_all() else 0)
