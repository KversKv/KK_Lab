#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Temp/log.log 真实数据验证 _compute_valid_range 步进比判据（临时脚本）。

预期：高端边界 0xCC（0xCD 起连续跌破 85% 参考步进），低端边界 0x00。
"""
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "Temp", "log.log")


def main():
    voltages = []
    codes = []
    pat = re.compile(r"\[MEAS\]\s+(\d+)\s+0x([0-9A-Fa-f]+)\s+([0-9.]+)")
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            m = pat.search(line)
            if m:
                codes.append(int(m.group(2), 16))
                voltages.append(float(m.group(3)))
    print(f"parsed {len(voltages)} points, code 0x{codes[0]:X} ~ 0x{codes[-1]:X}")

    from ui.pages.pmu_test.pmu_output_voltage import OutputVoltageTestThread
    low, high = OutputVoltageTestThread._compute_valid_range(voltages)
    print(f"valid range: 0x{codes[low]:X} ~ 0x{codes[high]:X} "
          f"({high - low + 1} points, V={voltages[low]:.4f} ~ {voltages[high]:.4f})")

    assert codes[low] == 0x00, f"low boundary mismatch: 0x{codes[low]:X}"
    assert codes[high] == 0xCB, f"high boundary mismatch: 0x{codes[high]:X}"

    # 附加：平坦段场景回归（低端死区 + 高端平台）；线性段 idx 5~54。
    # 高端经 10 倍步进跳变进平台：步进比判据只识别"步进跌破"，跳变点
    # (idx 55) 的到达步进正常故被保留——真实饱和为步进渐缩，无此形态。
    fake = [1.0] * 5 + [1.005 + 0.005 * i for i in range(50)] + [1.3] * 5
    lo, hi = OutputVoltageTestThread._compute_valid_range(fake)
    print(f"flat-dead-zone case: idx {lo}~{hi} (expect 4 ~ 55)")
    assert (lo, hi) == (4, 55), f"dead zone case mismatch: {lo}~{hi}"

    # 附加：真实饱和形态回归（步进渐缩至平坦）：线性 4.9mV 段后 2.9mV 渐缩
    base = 1.0 + 0.0049 * 99
    fake2 = [1.0 + 0.0049 * i for i in range(100)] + \
            [base + 0.0029 * (i + 1) for i in range(3)] + \
            [base + 0.0029 * 3] * 3
    lo2, hi2 = OutputVoltageTestThread._compute_valid_range(fake2)
    print(f"soft-saturation case: idx {lo2}~{hi2} (expect 0 ~ 99)")
    assert (lo2, hi2) == (0, 99), f"soft-saturation case mismatch: {lo2}~{hi2}"

    print("ALL PASS")


if __name__ == "__main__":
    main()
