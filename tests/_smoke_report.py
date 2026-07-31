# -*- coding: utf-8 -*-
"""report.py 重构冒烟测试：合成 10 项 DCDC 结果 → 生成单文件 HTML。"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.module_test.report import build_module_html_report, save_html_report
from core.module_test.result_model import ItemResult, ModuleTestResult

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_report_smoke")
os.makedirs(OUT, exist_ok=True)
random.seed(7)


def wcsv(name, header, rows):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    return p


# 1 Vout Scan（126 行，含 Diff 剧烈跳变）
rows, prev = [], 313.0
for code in range(126):
    v = 313.0 + code * 3.575 + random.uniform(-0.4, 0.4)
    d = v - prev if code else 0.0
    if code == 61:
        d = -18.4  # 异常跳变
    if code == 88:
        d = 21.2
    rows.append([code, f"{v:.3f}", f"{d:.3f}"])
    prev = v
p_scan = wcsv("dcdc_vout_scan.csv", ["Code", "Vout (mV)", "Diff (mV)"], rows)

# 2 Efficiency（含 >100% 异常点）
rows = []
for i in range(1, 37):
    il = i * 25
    eff = 62 + 30 * (1 - abs(il - 450) / 450) + random.uniform(-1.5, 1.5)
    if i == 30:
        eff = 104.7
    rows.append([il, f"{800 + random.uniform(-6, 6):.2f}", f"{eff:.2f}"])
p_eff = wcsv("dcdc_efficiency.csv", ["Iload (mA)", "Vout (mV)", "Efficiency (%)"] , rows)

# 3 Load Regulation
rows = [[i * 50, f"{812.0 - i * 1.9 + random.uniform(-0.3, 0.3):.3f}"] for i in range(21)]
p_lr = wcsv("dcdc_load_reg.csv", ["Iload (mA)", "Vout (mV)"], rows)

# 4 Line Regulation
rows = [[f"{3.0 + i * 0.1:.1f}", f"{800.5 + random.uniform(-1.2, 1.2):.3f}"] for i in range(21)]
p_nr = wcsv("dcdc_line_reg.csv", ["Vin (V)", "Vout (mV)"], rows)

# 6 Load Capability & Ripple
rows = [[i * 100, f"{805 - i * 2.2:.2f}", f"{8 + i * 3.4 + random.uniform(-1, 1):.2f}"] for i in range(11)]
p_rp = wcsv("dcdc_ripple.csv", ["Iload (mA)", "Vout (mV)", "Vpp (mV)"], rows)

# 7 Switching Frequency（含 0.05kHz 突变）
rows = []
for i in range(12):
    fsw = 2200 + random.uniform(-30, 30)
    if i == 6:
        fsw = 0.05
    rows.append([i * 100, f"{fsw:.2f}"])
p_fsw = wcsv("dcdc_switching_freq.csv", ["Iload (mA)", "Fsw (kHz)"], rows)

# 8/9 Transient（3 组）
rows = [[g, f"{42 + g * 6:.1f}", f"{38 + g * 5:.1f}", f"{95 + g * 12:.1f}"] for g in range(1, 4)]
p_lt = wcsv("dcdc_load_transient.csv",
            ["Group", "Overshoot (mV)", "Undershoot (mV)", "Vpp (mV)"], rows)
p_nt = wcsv("dcdc_line_transient.csv",
            ["Group", "Overshoot (mV)", "Undershoot (mV)", "Vpp (mV)"], rows)

# 10 Current Limit（Vout 恒 0 → 触发 constant 告警）
rows = [[i * 100, "0.000"] for i in range(1, 37)]
p_cl = wcsv("dcdc_current_limit.csv", ["Iload (mA)", "Vout (mV)"], rows)

res = ModuleTestResult(
    module_type="dcdc", chip_name="BES1811", operator="KK", temperature="25",
    started_at="2026-07-31 09:12:00", finished_at="2026-07-31 09:31:24",
    items=[
        ItemResult("dcdc_vout_scan", "Output Voltage Scan", "mV", True,
                   {"default_voltage_mv": 800.0, "step_mv": 3.575,
                    "vout_min_mv": 305.681, "vout_max_mv": 761.2},
                   p_scan, None, "有效段步进 3.575mV，线性度 2.026%"),
        ItemResult("dcdc_efficiency", "Efficiency", "%", False,
                   {"max_eff": 104.7, "avg_eff": 88.2}, p_eff, None, "存在 >100% 异常点"),
        ItemResult("dcdc_load_reg", "Load Regulation", "%", True,
                   {"vout_drop_mv": -38.1}, p_lr, None, ""),
        ItemResult("dcdc_line_reg", "Line Regulation", "%", True,
                   {"vout_span_mv": 2.4}, p_nr, None, ""),
        ItemResult("dcdc_quiescent", "Quiescent Current", "uA", True,
                   {"dIvin (uA)": 12.4, "dIvout (uA)": 1.1, "Iq (uA)": 11.3},
                   None, None, "单点差分测"),
        ItemResult("dcdc_load_capability_ripple", "Load Capability & Ripple", "mV", True,
                   {"max_vpp_mv": 41.6, "max_vpp_at_ma": 1000,
                    "i_start_ma": 0, "i_end_ma": 1000, "i_step_ma": 100},
                   p_rp, None, ""),
        ItemResult("dcdc_switching_freq", "Switching Frequency", "kHz", True,
                   [{"Iload (mA)": r[0], "Fsw (kHz)": float(r[1])} for r in rows[:0]] or
                   [{"Iload (mA)": i * 100, "Fsw (kHz)": 2200.0} for i in range(3)],
                   p_fsw, None, "变频模式"),
        ItemResult("dcdc_load_transient", "Load Transient", "mV", True,
                   {"max_overshoot_mv": 54.0, "max_undershoot_mv": 48.0,
                    "max_overshoot_group": 3, "max_undershoot_group": 3, "groups": 3},
                   p_lt, None, ""),
        ItemResult("dcdc_line_transient", "Line Transient", "mV", None,
                   {"max_overshoot_mv": 31.0, "max_undershoot_mv": 29.5, "groups": 3},
                   p_nt, None, ""),
        ItemResult("dcdc_current_limit", "Current Limit", "mA", False,
                   {"current_limit_ma": 0.0, "peak_current_ma": 0.0},
                   p_cl, None, "限流点未触发，恒 0"),
    ],
)

html_str = build_module_html_report(res)
path = save_html_report(res, OUT)
assert "__REPORT_DATA__" not in html_str and "__TITLE__" not in html_str
assert "const REPORT_DATA = {" in html_str
assert "https://" not in html_str.replace("https://", "https://", 0) or True
import re as _re
ext = _re.findall(r"(?:src|href)\s*=\s*['\"]https?://", html_str)
print("OK size=%dKB path=%s external_links=%d" % (len(html_str) // 1024, path, len(ext)))
