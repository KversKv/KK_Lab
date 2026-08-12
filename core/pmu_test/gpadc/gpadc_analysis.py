# -*- coding: utf-8 -*-
"""
GPADC 测试纯算法/解析函数（无 PySide6，可 pytest 直测）。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
"""

import math
import re

# 匹配 UART 日志中的 GPADC raw/volt 行，如：
#   gpadc_ch1_irq_cb: raw/volt=2844/1248 sample_time=575us
_GPADC_RAW_VOLT_RE = re.compile(r"raw/volt=\s*(\d+)\s*/\s*(\d+)")


def parse_uart_gpadc_raw(line, keyword=""):
    """从一行 UART 日志提取 GPADC raw 值。

    keyword 非空时，行内必须先包含该关键字；命中后按 ``raw/volt=<raw>/<volt>``
    提取 raw 整数返回，未命中或格式不匹配返回 None。
    """
    if keyword and keyword not in line:
        return None
    m = _GPADC_RAW_VOLT_RE.search(line)
    if m is None:
        return None
    return int(m.group(1))


def compute_reg_stats(raw_data, return_raw=False):
    sorted_data = sorted(raw_data)

    reg_min = sorted_data[0]
    reg_max = sorted_data[-1]

    trim = max(1, int(len(sorted_data) * 0.05))
    trimmed = sorted_data[trim:-trim] if len(sorted_data) > 2 * trim else sorted_data

    avg = sum(trimmed) / len(trimmed)

    if return_raw:
        return avg, reg_max, reg_min, raw_data
    else:
        return avg, reg_max, reg_min


def compute_calibration(adc_raw_data, adc_mean, adc_min, adc_max, calib_points=None):
    n = len(adc_raw_data)
    if calib_points is not None:
        # 用户手动指定两个校准点（x 轴物理量）：取扫描曲线上距其最近的实测点均值
        v_low, v_high = calib_points
        idx_low = min(range(n), key=lambda i: abs(adc_raw_data[i] - v_low))
        idx_high = min(range(n), key=lambda i: abs(adc_raw_data[i] - v_high))
        m_low, m_high = adc_mean[idx_low], adc_mean[idx_high]
    else:
        idx_low = n // 4
        idx_high = (3 * n) // 4
        v_low, m_low = adc_raw_data[idx_low], adc_mean[idx_low]
        v_high, m_high = adc_raw_data[idx_high], adc_mean[idx_high]

    # 退化场景保护：两点电压相同或 ADC 读数无变化时，斜率不可解，
    # 跳过标定，返回原始数据避免 ZeroDivisionError。
    if v_high == v_low or m_high == m_low:
        k = 0.0
        b = 0.0
        mean_cali = list(adc_mean)
        adc_min_cali = list(adc_min)
        adc_max_cali = list(adc_max)
    else:
        k = (m_high - m_low) / (v_high - v_low)
        b = m_low - k * v_low

        mean_cali = [(adc - b) / k for adc in adc_mean]
        adc_min_cali = [(adc - b) / k for adc in adc_min]
        adc_max_cali = [(adc - b) / k for adc in adc_max]

    return k, b, mean_cali, adc_min_cali, adc_max_cali, v_low, m_low, v_high, m_high


def compute_detailed_stats(raw_data):
    """1000CNT 详细统计（纯算法，无 Qt）。

    AVG / MIN / MAX 沿用 ``compute_reg_stats``（5% 截尾均值、全量极值），
    另补充全量样本的 STD（样本标准差，code）、P-P（峰峰噪声，code）与
    实际样本数 count。
    """
    if not raw_data:
        raise ValueError("raw_data 为空，无法统计")

    avg, reg_max, reg_min = compute_reg_stats(raw_data)

    n = len(raw_data)
    mean_full = sum(raw_data) / n
    if n > 1:
        std = math.sqrt(sum((v - mean_full) ** 2 for v in raw_data) / (n - 1))
    else:
        std = 0.0

    return {
        'avg': avg,
        'min': reg_min,
        'max': reg_max,
        'std': std,
        'pp': reg_max - reg_min,
        'count': n,
    }
