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


# ---------------------------------------------------------------------------
# GPADC 采样数据处理算法（注册表驱动，无 Qt）
#
# 新增算法只需：
#   1. 实现纯函数 ``def algo_xxx(samples, **params) -> list``；
#   2. 在 ALGORITHM_REGISTRY 登记（含参数元信息）；
#   3. UI 侧参数控件按注册表自动生成，无需改动界面代码。
# ---------------------------------------------------------------------------

def algo_moving_average(samples, window=8):
    """滑动平均（长度保持）：居中窗口均值，抑制随机噪声。"""
    n = len(samples)
    if n == 0 or window <= 1:
        return list(samples)
    half = window // 2
    result = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        seg = samples[lo:hi]
        result.append(sum(seg) / len(seg))
    return result


def algo_median_filter(samples, window=3):
    """中值滤波（长度保持）：居中窗口中值，剔除脉冲型毛刺。"""
    n = len(samples)
    if n == 0 or window <= 1:
        return list(samples)
    half = window // 2
    result = []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        result.append(sorted(samples[lo:hi])[(hi - lo) // 2])
    return result


def algo_debounce(samples, threshold=4):
    """去抖：剔除相对前一保留样本跳变超过 threshold 的抖动样本（长度可能缩短）。"""
    if not samples:
        return list(samples)
    kept = [samples[0]]
    for v in samples[1:]:
        if abs(v - kept[-1]) <= threshold:
            kept.append(v)
    return kept


def algo_offset_compensation(samples, offset=0.0):
    """偏移补偿：整体减去固定偏移（code）。"""
    return [v - offset for v in samples]


def algo_gain_compensation(samples, gain=1.0):
    """增益补偿：整体乘以增益系数。"""
    return [v * gain for v in samples]


ALGORITHM_REGISTRY = {
    'moving_average': {
        'name': 'Moving Average (滑动平均)',
        'desc': '滑动平均滤波，抑制随机噪声（保持样本长度）',
        'func': algo_moving_average,
        'params': {
            'window': {'label': 'Window', 'default': 8, 'min': 2, 'max': 1024,
                       'step': 1, 'decimals': 0},
        },
    },
    'median_filter': {
        'name': 'Median Filter (中值滤波)',
        'desc': '中值滤波，剔除脉冲型毛刺（保持样本长度）',
        'func': algo_median_filter,
        'params': {
            'window': {'label': 'Window', 'default': 3, 'min': 3, 'max': 21,
                       'step': 2, 'decimals': 0},
        },
    },
    'debounce': {
        'name': 'Debounce (去抖)',
        'desc': '剔除相对前一稳定样本跳变超阈值的抖动样本',
        'func': algo_debounce,
        'params': {
            'threshold': {'label': 'Threshold (code)', 'default': 4, 'min': 0,
                          'max': 1024, 'step': 1, 'decimals': 0},
        },
    },
    'offset_compensation': {
        'name': 'Offset Comp (偏移补偿)',
        'desc': '整体减去固定偏移（code）',
        'func': algo_offset_compensation,
        'params': {
            'offset': {'label': 'Offset (code)', 'default': 0.0, 'min': -4096.0,
                       'max': 4096.0, 'step': 1.0, 'decimals': 3},
        },
    },
    'gain_compensation': {
        'name': 'Gain Comp (增益补偿)',
        'desc': '整体乘以增益系数',
        'func': algo_gain_compensation,
        'params': {
            'gain': {'label': 'Gain', 'default': 1.0, 'min': 0.001, 'max': 100.0,
                     'step': 0.01, 'decimals': 4},
        },
    },
}


def apply_algorithm(samples, algo_config):
    """按配置应用采样算法（当前单算法）。

    algo_config 为 None / id 为空 / 未命中注册表时原样返回（等同未启用算法，
    与原始测试流程一致）。
    """
    if not algo_config:
        return samples
    spec = ALGORITHM_REGISTRY.get(algo_config.get('id'))
    if spec is None:
        return samples
    kwargs = algo_config.get('params') or {}
    return spec['func'](samples, **kwargs)


def describe_algorithm(algo_config):
    """生成算法配置的可读描述（用于日志 / 悬浮提示）；未启用返回 None。"""
    if not algo_config:
        return "None"
    spec = ALGORITHM_REGISTRY.get(algo_config.get('id'))
    if spec is None:
        return str(algo_config.get('id'))
    params = algo_config.get('params') or {}
    if params:
        param_text = ", ".join(f"{k}={v}" for k, v in params.items())
        return f"{spec['name']} ({param_text})"
    return spec['name']
