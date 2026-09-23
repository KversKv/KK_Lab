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


def parse_uart_gpadc_raw_volt(line, keyword=""):
    """从一行 UART 日志同时提取 GPADC raw 与 volt（DUT 已校准电压，mV）。

    keyword 非空时，行内必须先包含该关键字；命中后按 ``raw/volt=<raw>/<volt>``
    提取并返回 ``(raw, volt)`` 整数元组，未命中或格式不匹配返回 None。
    """
    if keyword and keyword not in line:
        return None
    m = _GPADC_RAW_VOLT_RE.search(line)
    if m is None:
        return None
    return int(m.group(1)), int(m.group(2))


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
# FT Calibration Check（两点 FT 校准检查，纯函数）
# ---------------------------------------------------------------------------

def solve_ft_kb(v1, c1, v2, c2):
    """由两个 FT 校准点解出线性转换 K/B：``code = k * voltage + b``。

    返回 ``(k, b)``；两点电压相同或校准码相同（斜率不可解/为零）时抛 ValueError。
    """
    if v1 == v2:
        raise ValueError("两个 FT 校准点的电压相同，无法解算 K/B")
    if c1 == c2:
        raise ValueError("两个 FT 校准点的校准码相同，K 为 0 无法校准")
    k = (c2 - c1) / (v2 - v1)
    b = c1 - k * v1
    return k, b


def assess_ft_errors(err_list_mv, limit_mv):
    """FT 校准误差统计（纯算法，无 Qt）。

    err_list_mv 为逐点误差序列（mV），limit_mv 为可配误差限（±mV）。
    判定规则：max(|err|) <= limit_mv 即 PASS。空序列抛 ValueError。
    """
    if not err_list_mv:
        raise ValueError("err_list_mv 为空，无法统计")
    n = len(err_list_mv)
    abs_max = max(abs(e) for e in err_list_mv)
    avg = sum(err_list_mv) / n
    rms = math.sqrt(sum(e * e for e in err_list_mv) / n)
    return {
        'max_abs_mv': abs_max,
        'avg_mv': avg,
        'rms_mv': rms,
        'count': n,
        'limit_mv': limit_mv,
        'passed': abs_max <= limit_mv,
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


def algo_trimmed_mean(samples, count=10):
    """去极值平均（长度缩短为 1/count）：每 count 个连续样本为一组，
    去掉最大值与最小值后取平均作为该组结果；不足 3 点的尾组退化为直接平均。
    """
    n = len(samples)
    if n == 0:
        return []
    count = max(3, int(count))
    result = []
    for i in range(0, n, count):
        block = samples[i:i + count]
        if len(block) >= 3:
            ordered = sorted(block)
            seg = ordered[1:-1]
            result.append(sum(seg) / len(seg))
        else:
            result.append(sum(block) / len(block))
    return result


def algo_deviation_trim_mean(samples, count=10, tolerance_pct=5.0):
    """偏差剔除平均（长度缩短为 1/count）：每 count 个连续样本为一组，
    先求均值，剔除与均值偏差超过 tolerance_pct% 的样本，剩余取平均作为该组结果；
    单趟剔除（不重算均值），全部被剔除时退化为原均值。
    """
    n = len(samples)
    if n == 0:
        return []
    count = max(1, int(count))
    result = []
    for i in range(0, n, count):
        block = samples[i:i + count]
        avg = sum(block) / len(block)
        limit = abs(avg) * tolerance_pct / 100.0
        kept = [v for v in block if abs(v - avg) <= limit]
        result.append(sum(kept) / len(kept) if kept else avg)
    return result


ALGORITHM_REGISTRY = {
    'moving_average': {
        'name': 'Moving Average (滑动平均)',
        'desc': '滑动平均滤波，抑制随机噪声（保持样本长度）',
        'principle': '思路: 逐点取居中 window 窗口内样本的均值作为输出，随机噪声在平均中相互抵消（长度不变）',
        'func': algo_moving_average,
        'params': {
            'window': {'label': 'Window', 'default': 8, 'min': 2, 'max': 1024,
                       'step': 1, 'decimals': 0},
        },
    },
    'median_filter': {
        'name': 'Median Filter (中值滤波)',
        'desc': '中值滤波，剔除脉冲型毛刺（保持样本长度）',
        'principle': '思路: 逐点取居中 window 窗口内样本的中值作为输出，脉冲型毛刺被中值天然剔除（长度不变）',
        'func': algo_median_filter,
        'params': {
            'window': {'label': 'Window', 'default': 3, 'min': 3, 'max': 21,
                       'step': 2, 'decimals': 0},
        },
    },
    'debounce': {
        'name': 'Debounce (去抖)',
        'desc': '剔除相对前一稳定样本跳变超阈值的抖动样本',
        'principle': '思路: 顺序扫描，相对上一保留样本跳变超过 threshold 的点视为抖动丢弃，保留样本原值输出（长度可能缩短）',
        'func': algo_debounce,
        'params': {
            'threshold': {'label': 'Threshold (code)', 'default': 4, 'min': 0,
                          'max': 1024, 'step': 1, 'decimals': 0},
        },
    },
    'offset_compensation': {
        'name': 'Offset Comp (偏移补偿)',
        'desc': '整体减去固定偏移（code）',
        'principle': '思路: 全体样本统一减去 offset，修正系统固定零偏（长度不变）',
        'func': algo_offset_compensation,
        'params': {
            'offset': {'label': 'Offset (code)', 'default': 0.0, 'min': -4096.0,
                       'max': 4096.0, 'step': 1.0, 'decimals': 3},
        },
    },
    'gain_compensation': {
        'name': 'Gain Comp (增益补偿)',
        'desc': '整体乘以增益系数',
        'principle': '思路: 全体样本统一乘以 gain，修正系统增益误差（长度不变）',
        'func': algo_gain_compensation,
        'params': {
            'gain': {'label': 'Gain', 'default': 1.0, 'min': 0.001, 'max': 100.0,
                     'step': 0.01, 'decimals': 4},
        },
    },
    'trimmed_mean': {
        'name': 'Trimmed Mean (去极值平均)',
        'desc': '每 N 个连续样本去掉最大/最小值后取平均（每组输出 1 个值，长度缩短为 1/N）',
        'principle': '思路: 每 count 个连续样本为一组，排序后去掉最大值与最小值，剩余取平均作为该组输出（每组 1 值，长度缩为 1/count）',
        'func': algo_trimmed_mean,
        'params': {
            'count': {'label': 'Sample Count', 'default': 10, 'min': 3, 'max': 10000,
                      'step': 1, 'decimals': 0},
        },
    },
    'deviation_trim_mean': {
        'name': 'Deviation Trim (偏差剔除平均)',
        'desc': '每 N 个连续样本先求均值，剔除偏差超过 Tolerance% 的样本后取平均（每组输出 1 个值）',
        'principle': '思路: 每 count 个连续样本为一组，先求组内均值，剔除与均值偏差超过 tolerance_pct% 的样本，剩余取平均作为该组输出（每组 1 值，长度缩为 1/count）',
        'func': algo_deviation_trim_mean,
        'params': {
            'count': {'label': 'Sample Count', 'default': 10, 'min': 2, 'max': 10000,
                      'step': 1, 'decimals': 0},
            'tolerance_pct': {'label': 'Tolerance (%)', 'default': 5.0, 'min': 0.1,
                              'max': 100.0, 'step': 0.5, 'decimals': 1},
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


# ---------------------------------------------------------------------------
# 1000CNT 波动评估与算法效果对比（纯算法）
# ---------------------------------------------------------------------------

# 波动分级阈值（STD，单位 code；12-bit GPADC 经验值，可按芯片实测调整）
FLUCT_STD_EXCELLENT = 1.0
FLUCT_STD_GOOD = 2.0
FLUCT_STD_FAIR = 4.0


def assess_fluctuation(std, pp):
    """1000CNT 样本波动评估：按 STD（code）分级，返回中文描述文本。"""
    if std <= FLUCT_STD_EXCELLENT:
        level = "优秀"
    elif std <= FLUCT_STD_GOOD:
        level = "良好"
    elif std <= FLUCT_STD_FAIR:
        level = "一般"
    else:
        level = "明显波动"
    return f"噪声等级={level} (STD={std:.3f} code, P-P={pp:.0f} code)"


def _improve_pct(before, after):
    """改善百分比：正值=降低/改善，负值=放大；before 为 0 时返回 None。"""
    if before == 0:
        return None
    return (before - after) / before * 100.0


def compare_algorithm_effect(raw_before, raw_after):
    """对比算法应用前后的样本统计（纯算法）。

    返回 dict：前后 std/pp/count 及 std/pp 改善百分比（before 为 0 时
    百分比为 None）；任一侧样本为空时返回 None。
    """
    if not raw_before or not raw_after:
        return None
    sb = compute_detailed_stats(raw_before)
    sa = compute_detailed_stats(raw_after)
    return {
        'std_before': sb['std'],
        'std_after': sa['std'],
        'pp_before': sb['pp'],
        'pp_after': sa['pp'],
        'count_before': sb['count'],
        'count_after': sa['count'],
        'std_improve_pct': _improve_pct(sb['std'], sa['std']),
        'pp_improve_pct': _improve_pct(sb['pp'], sa['pp']),
    }
