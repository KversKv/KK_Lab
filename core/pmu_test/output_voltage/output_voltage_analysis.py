# -*- coding: utf-8 -*-
"""PMU 输出电压测试纯算法（无 Qt 依赖）。"""

import math
import statistics

# 前置校验：前 N 点首尾差值低于阈值视为输出无响应；
# 相邻步进差值偏离均值超过该比例视为非等差异常
_PRECHECK_POINTS = 5
_PRECHECK_MIN_SPAN = 0.002  # V
_PRECHECK_DIFF_TOL = 0.5

# 尾部饱和提前终止：连续 N 点电压极差低于阈值（如受限于前级电压卡住）时结束扫描
_TAIL_STOP_POINTS = 5
_TAIL_STOP_SPAN = 0.002  # V

# 有效线性区间判据：以相邻压差中位数为参考步进，
# 连续 N 点压差低于参考步进的指定比例即判为死区/饱和段（软饱和缓变与平坦段同覆盖）
_VALID_STEP_RATIO = 0.85
_VALID_STEP_CONSEC = 2


def validate_code_range(msb, lsb, min_code, max_code):
    if lsb < 0 or msb < lsb:
        raise ValueError("Invalid bit range: require 0 <= LSB <= MSB.")
    mask = (1 << (msb - lsb + 1)) - 1
    if min_code < 0 or max_code < min_code or max_code > mask:
        raise ValueError(
            f"Invalid code range: require 0 <= Min Code <= Max Code <= 0x{mask:X}."
        )


def compute_valid_range(voltages):
    """计算有效线性区间索引 (low_valid, high_valid)。

    以相邻压差的中位数为参考步进（抗毛刺/饱和段污染），双向剔除死区/
    饱和段：低端取首个连续 N 个正常步进段的前一保留点（基线值 = 线性段
    起点），高端取首个连续 N 点跌破参考步进指定比例处的前一保留点
    （线性段终点）。MSB 位加权不匹配等孤立毛刺（如 0x80 处约 2 倍步进
    的单点跳变）不构成连续跌破而被保留；平坦段（压差≈0）同样低于阈值，
    故本判据天然覆盖旧平坦检测。
    """
    n = len(voltages)
    if n < 3:
        return 0, n - 1

    diffs = [abs(voltages[k + 1] - voltages[k]) for k in range(n - 1)]
    ref = statistics.median(diffs)
    if ref <= 0:
        return 0, n - 1
    threshold = ref * _VALID_STEP_RATIO
    m = len(diffs)

    # 低端：首个连续 N 个正常步进的起点即死区末点（其值 = 线性段起点）
    low_valid = 0
    run = 0
    for i in range(m):
        run = run + 1 if diffs[i] >= threshold else 0
        if run >= _VALID_STEP_CONSEC:
            low_valid = i - _VALID_STEP_CONSEC + 1
            break

    # 高端：low_valid 之后首个连续 N 点跌破处的前一保留点为线性段终点
    high_valid = n - 1
    run = 0
    for i in range(low_valid, m):
        run = run + 1 if diffs[i] < threshold else 0
        if run >= _VALID_STEP_CONSEC:
            high_valid = i - _VALID_STEP_CONSEC + 1
            break

    if high_valid < low_valid:
        low_valid, high_valid = 0, n - 1
    return low_valid, high_valid


def build_result(voltages, codes, default_voltage, default_code, progress):
    """基于有效区间计算结果指标（min/max/步进/线性度）。"""
    result = {"progress": progress, "default_voltage": default_voltage, "default_code": default_code}
    low_valid, high_valid = compute_valid_range(voltages)
    valid_voltages = voltages[low_valid:high_valid + 1]
    valid_codes = codes[low_valid:high_valid + 1]
    if len(valid_voltages) >= 1:
        result["min_voltage"] = min(valid_voltages)
        result["max_voltage"] = max(valid_voltages)
        result["valid_min_code"] = valid_codes[0]
        result["valid_max_code"] = valid_codes[-1]
    if len(valid_voltages) >= 2:
        avg_step = (valid_voltages[-1] - valid_voltages[0]) / (len(valid_voltages) - 1) * 1000.0
        result["step_voltage"] = avg_step

        full_scale = valid_voltages[-1] - valid_voltages[0]
        if abs(full_scale) > 1e-9:
            n = len(valid_voltages)
            ideal_step = full_scale / (n - 1)
            max_dev = 0.0
            for j in range(n):
                ideal_v = valid_voltages[0] + ideal_step * j
                dev = abs(valid_voltages[j] - ideal_v)
                if dev > max_dev:
                    max_dev = dev
            result["linearity"] = max_dev / abs(full_scale) * 100.0
        else:
            result["linearity"] = 0.0
    return result


def precheck_first_points(voltages):
    """前 N 点前置校验：首尾差值过小 / 步进不等差（波动>50%）/ 读数异常时返回 (False, 原因)。"""
    for v in voltages:
        if not math.isfinite(v):
            return False, f"读数异常（{v}）"
        if v < 0:
            return False, f"测得负电压（{v:.4f}V）"

    span = voltages[-1] - voltages[0]
    if abs(span) <= _PRECHECK_MIN_SPAN:
        vals = ", ".join(f"{v:.4f}" for v in voltages)
        return False, f"电压无变化（span={span * 1000:.2f}mV，读数=[{vals}]V）"

    # 等差校验：各相邻步进差值应接近均值（允许 ±50% 波动），偏离过大视为异常
    mean_diff = span / (len(voltages) - 1)
    diffs = [voltages[i + 1] - voltages[i] for i in range(len(voltages) - 1)]
    for i, d in enumerate(diffs):
        if abs(d - mean_diff) > _PRECHECK_DIFF_TOL * abs(mean_diff):
            diff_str = ", ".join(f"{d * 1000:.2f}" for d in diffs)
            return False, (
                f"第 {i + 1} 步步进不等差（diff={d * 1000:.2f}mV，"
                f"期望≈{mean_diff * 1000:.2f}mV，容差=±{_PRECHECK_DIFF_TOL * 100:.0f}%，"
                f"diffs=[{diff_str}]mV）"
            )
    return True, ""
