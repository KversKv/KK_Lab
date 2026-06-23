# -*- coding: utf-8 -*-
"""
IsGain 测试纯算法/解析函数（无 PySide6，可 pytest 直测）。

从 ui/pages/pmu_test/pmu_isGain_ui.py 的 _IsGainTestWorker 平移而来，
行为零变更。
"""

YSCALE_SEQUENCE = [
    0.001, 0.002, 0.005,
    0.010, 0.020, 0.050,
    0.100, 0.200, 0.500,
    1.000, 2.000, 5.000,
]

RECOVERY_SCALE = 1.0


def parse_channel(ch_text):
    return int(ch_text.replace("CH ", "").strip())


def prev_scale(current_scale, yscale_sequence=None):
    if yscale_sequence is None:
        yscale_sequence = YSCALE_SEQUENCE
    prev = None
    for s in yscale_sequence:
        if s >= current_scale * 0.99:
            return prev
        prev = s
    return prev


def analyze_results(results, v0):
    max_ripple = None
    max_ripple_current = None
    max_load_current = None

    if v0 is not None:
        for r in results:
            v = r.get("voltage")
            cur = r.get("load_current", 0)
            rp = r.get("ripple")

            if rp is not None:
                if max_ripple is None or rp > max_ripple:
                    max_ripple = rp
                    max_ripple_current = cur

            if v is not None and cur > 0:
                drop = v0 - v
                if drop <= 0.030:
                    max_load_current = cur

    return {
        "v0": v0,
        "max_load_current": max_load_current,
        "max_ripple": max_ripple,
        "max_ripple_current": max_ripple_current,
    }
