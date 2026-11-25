# -*- coding: utf-8 -*-
"""
GPADC 测试纯算法/解析函数（无 PySide6，可 pytest 直测）。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
"""

import math
import re
import statistics

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


def _round_linearity_value(value):
    return int(math.floor(value + 0.5))


def generate_linearity_values(start_value, end_value, step_value):
    """按 Value 步进直接生成寄存器写入值，补入终点并对取整后的重复值去重。"""
    start_value, end_value, step_value = (
        float(start_value), float(end_value), float(step_value),
    )
    if not all(math.isfinite(value) for value in (start_value, end_value, step_value)):
        raise ValueError("线性度 Value 参数必须为有限数值")
    if start_value < 0 or end_value < 0:
        raise ValueError("线性度寄存器值不能为负数")
    if start_value > end_value:
        raise ValueError("线性度 Start (Value) <= End (Value) 必须成立")
    if step_value <= 0:
        raise ValueError("线性度 Step (Value) 必须大于 0")

    values = [start_value]
    tolerance = max(1e-12, step_value * 1e-9)
    index = 1
    while start_value < end_value:
        value = start_value + index * step_value
        if value >= end_value - tolerance:
            break
        values.append(value)
        index += 1
    if end_value != start_value:
        values.append(end_value)

    register_values = []
    for value in values:
        register_value = _round_linearity_value(value)
        if not register_values or register_value != register_values[-1]:
            register_values.append(register_value)
    return register_values


def normalize_linearity_auto_range(start_value, end_value):
    """将自动寻优范围规范化为非负整数闭区间。"""
    start_value, end_value = float(start_value), float(end_value)
    if not math.isfinite(start_value) or not math.isfinite(end_value):
        raise ValueError("线性度 Value 参数必须为有限数值")
    if start_value < 0 or end_value < 0:
        raise ValueError("线性度寄存器值不能为负数")
    if start_value > end_value:
        raise ValueError("线性度 Start (Value) <= End (Value) 必须成立")
    return _round_linearity_value(start_value), _round_linearity_value(end_value)


def aggregate_linearity_repeats(repeat_groups):
    """聚合同一候选的 Repeat 指标，并选择一次真实测量作为代表曲线。"""
    if not repeat_groups:
        raise ValueError("Repeat 结果为空，无法聚合")
    repeats = [
        dict(group, repeat_index=index)
        for index, group in enumerate(repeat_groups, 1)
    ]
    max_values = [float(group["max_abs_mv"]) for group in repeats]
    rms_values = [float(group["rms_mv"]) for group in repeats]
    max_median = statistics.median(max_values)
    rms_median = statistics.median(rms_values)
    representative_index = min(
        range(len(repeats)),
        key=lambda index: (
            abs(max_values[index] - max_median) + abs(rms_values[index] - rms_median),
            abs(max_values[index] - max_median),
            abs(rms_values[index] - rms_median),
            index,
        ),
    )
    group = dict(repeats[representative_index])
    group.update({
        "max_abs_mv": max_median,
        "rms_mv": rms_median,
        "max_abs_range_mv": max(max_values) - min(max_values),
        "rms_range_mv": max(rms_values) - min(rms_values),
        "repeat_count": len(repeats),
        "representative_repeat": representative_index + 1,
        "repeat_results": repeats,
    })
    return group


def compare_linearity_candidates(left, right):
    """按中位数指标和 Repeat 波动带比较两个候选；-1 左优、0 并列、1 右优。"""
    epsilon = 1e-12
    max_delta = float(left["max_abs_mv"]) - float(right["max_abs_mv"])
    rms_delta = float(left["rms_mv"]) - float(right["rms_mv"])
    max_band = max(
        epsilon,
        float(left.get("max_abs_range_mv", 0.0)),
        float(right.get("max_abs_range_mv", 0.0)),
    )
    rms_band = max(
        epsilon,
        float(left.get("rms_range_mv", 0.0)),
        float(right.get("rms_range_mv", 0.0)),
    )
    order = 0
    if abs(max_delta) > max_band:
        order = -1 if max_delta < 0 else 1
    elif abs(rms_delta) > rms_band:
        order = -1 if rms_delta < 0 else 1
    return {
        "order": order,
        "max_delta_mv": max_delta,
        "rms_delta_mv": rms_delta,
        "max_band_mv": max_band,
        "rms_band_mv": rms_band,
        "ambiguous": order == 0 and (max_band > epsilon or rms_band > epsilon),
    }


LINEARITY_AUTO_COARSE_STEP = 16
LINEARITY_AUTO_FINALIST_LIMIT = 3


def normalize_linearity_auto_strategy(value):
    strategy = str(value or "coarse_fine").strip().lower()
    if strategy not in ("coarse_fine", "unimodal"):
        raise ValueError(f"未知 Linearity Auto Strategy: {value}")
    return strategy


def _longest_uncached_midpoint(low, high, cache):
    """返回最长连续未测段的中点；等长时取最左段。"""
    best_start = best_end = None
    start = None
    for value in range(low, high + 2):
        if value <= high and value not in cache:
            if start is None:
                start = value
            continue
        if start is not None:
            end = value - 1
            if best_start is None or end - start > best_end - best_start:
                best_start, best_end = start, end
            start = None
    if best_start is None:
        return None
    return (best_start + best_end) // 2


def advance_linearity_auto_best(low, high, cache):
    """离散单峰搜索：比较相邻内部点，Tie 时保持区间并加密。"""
    low, high = int(low), int(high)
    if low < 0 or low > high:
        raise ValueError("自动寻优区间无效")

    def _result(evaluate_value=None, done=False, comparison=None):
        return {
            "low": low,
            "high": high,
            "evaluate_value": evaluate_value,
            "done": done,
            "comparison": comparison,
        }

    if high - low <= 3:
        for value in range(low, high + 1):
            if value not in cache:
                return _result(evaluate_value=value)
        return _result(done=True)

    mid = (low + high) // 2
    right = mid + 1
    for value in (mid, right):
        if value not in cache:
            return _result(evaluate_value=value)

    comparison = compare_linearity_candidates(cache[mid], cache[right])
    comparison.update({
        "left_value": mid,
        "right_value": right,
        "probe_values": (mid, right),
        "previous_low": low,
        "previous_high": high,
    })
    if comparison["order"] < 0:
        next_low, next_high = low, mid
        direction = "left"
    elif comparison["order"] > 0:
        next_low, next_high = right, high
        direction = "right"
    else:
        next_low, next_high = low, high
        direction = "hold"
    comparison.update({
        "direction": direction,
        "low": next_low,
        "high": next_high,
    })
    if direction != "hold":
        comparison["next_value"] = None
        return {
            "low": next_low,
            "high": next_high,
            "evaluate_value": None,
            "done": False,
            "comparison": comparison,
        }

    evaluate_value = _longest_uncached_midpoint(low, high, cache)
    comparison["next_value"] = evaluate_value
    return _result(
        evaluate_value=evaluate_value,
        done=evaluate_value is None,
        comparison=comparison,
    )


def generate_linearity_coarse_values(start_value, end_value, step=LINEARITY_AUTO_COARSE_STEP):
    """生成含端点的粗扫点；小范围直接退化为 Step=1 全扫。"""
    low, high = normalize_linearity_auto_range(start_value, end_value)
    step = int(step)
    if step <= 0:
        raise ValueError("Linearity coarse step must be positive")
    if high - low + 1 <= 2 * step + 1:
        return list(range(low, high + 1))
    return generate_linearity_values(low, high, step)


def _linearity_score(group):
    return float(group["max_abs_mv"]), float(group["rms_mv"])


def _linearity_rank(group):
    return (*_linearity_score(group), int(group["n_value"]), int(group["p_value"]))


def find_linearity_local_minima(values, cache):
    """识别粗扫边界/内部低谷；指标平台全部保留。"""
    values = sorted(int(value) for value in values)
    if not values:
        return []
    if len(set(values)) != len(values) or any(value not in cache for value in values):
        raise ValueError("粗扫低谷识别需要唯一且完整测量的候选")
    scores = [_linearity_score(cache[value]) for value in values]
    minima = []
    for index, value in enumerate(values):
        score = scores[index]
        if index > 0 and score > scores[index - 1]:
            continue
        if index + 1 < len(values) and score > scores[index + 1]:
            continue
        minima.append(value)
    return minima


def build_linearity_neighborhoods(low, high, minima, radius=LINEARITY_AUTO_COARSE_STEP):
    """将各低谷邻域裁剪到搜索范围，并合并重叠或相邻区间。"""
    low, high = int(low), int(high)
    radius = int(radius)
    if low < 0 or low > high or radius < 0:
        raise ValueError("Linearity 低谷邻域参数无效")
    intervals = sorted(
        (max(low, int(value) - radius), min(high, int(value) + radius))
        for value in minima
    )
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def select_linearity_finalists(cache, neighborhoods, limit=LINEARITY_AUTO_FINALIST_LIMIT):
    """每个细扫邻域优先推荐一名胜者，再从全部候选补足。"""
    limit = int(limit)
    if limit <= 0:
        return []
    winners = []
    for start, end in neighborhoods:
        values = [value for value in range(int(start), int(end) + 1) if value in cache]
        if values:
            winners.append(min((cache[value] for value in values), key=_linearity_rank))
    finalists = []
    for group in sorted(winners, key=_linearity_rank):
        value = int(group["n_value"])
        if value not in finalists:
            finalists.append(value)
        if len(finalists) == limit:
            return finalists
    for group in sorted(cache.values(), key=_linearity_rank):
        value = int(group["n_value"])
        if value not in finalists:
            finalists.append(value)
        if len(finalists) == limit:
            break
    return finalists


def generate_linearity_pairs(config):
    """生成 N/P 同值对角组合或 N 外层、P 内层的独立矩阵组合。"""
    if config["linearity_link_np"]:
        values = generate_linearity_values(
            config["linearity_value_start"], config["linearity_value_end"],
            config["linearity_value_step"],
        )
        return [(value, value) for value in values]
    n_values = generate_linearity_values(
        config["linearity_n_value_start"], config["linearity_n_value_end"],
        config["linearity_n_value_step"],
    )
    p_values = generate_linearity_values(
        config["linearity_p_value_start"], config["linearity_p_value_end"],
        config["linearity_p_value_step"],
    )
    return [(n_value, p_value) for n_value in n_values for p_value in p_values]


def analyze_linearity_group(n_value, p_value, sweep_result, calib_points=None):
    """对一组扫压结果独立两点校准，并计算电压误差及最佳值评选指标。"""
    pair_label = f"N=0x{int(n_value):X}, P=0x{int(p_value):X}"
    voltage = list(sweep_result.get("voltage") or [])
    adc_mean = list(sweep_result.get("mean") or [])
    adc_min = list(sweep_result.get("min") or [])
    adc_max = list(sweep_result.get("max") or [])
    if len(voltage) < 2:
        raise ValueError(f"{pair_label} 至少需要两个完整扫压点")
    if not (len(voltage) == len(adc_mean) == len(adc_min) == len(adc_max)):
        raise ValueError(f"{pair_label} 扫压数据长度不一致")

    k, b, mean_cali, _, _, v_low, m_low, v_high, m_high = compute_calibration(
        voltage, adc_mean, adc_min, adc_max, calib_points=calib_points,
    )
    if k == 0.0:
        raise ValueError(f"{pair_label} 标定斜率 k=0，无法计算 Error")

    error_mv = [(cali - vin) * 1000.0 for vin, cali in zip(voltage, mean_cali)]
    max_abs_mv = max(abs(error) for error in error_mv)
    rms_mv = math.sqrt(sum(error * error for error in error_mv) / len(error_mv))
    return {
        "n_value": int(n_value),
        "p_value": int(p_value),
        "k": k,
        "b": b,
        "mean_cali": mean_cali,
        "error_mv": error_mv,
        "max_abs_mv": max_abs_mv,
        "rms_mv": rms_mv,
        "calib_points": (v_low, m_low, v_high, m_high),
        "raw": sweep_result,
    }


def select_best_linearity_group(groups, noise_aware=False):
    """选择最佳组；自动模式用波动带比较，手动模式保持精确指标排序。"""
    valid = [
        (index, group) for index, group in enumerate(groups)
        if group.get("error_mv")
    ]
    if not valid:
        return None
    if not noise_aware:
        return min(
            valid,
            key=lambda item: (
                item[1]["max_abs_mv"], item[1]["rms_mv"],
                item[1]["n_value"], item[1]["p_value"],
            ),
        )[0]

    best_index, best = valid[0]
    for index, candidate in valid[1:]:
        comparison = compare_linearity_candidates(candidate, best)
        candidate_key = (candidate["n_value"], candidate["p_value"])
        best_key = (best["n_value"], best["p_value"])
        if comparison["order"] == -1 or (
                comparison["order"] == 0 and candidate_key < best_key):
            best_index, best = index, candidate
    return best_index


def build_linearity_auto_search_timeline(result):
    """按真实评价顺序重建 Auto Best 动画事件，不修改原结果。"""
    search = result.get("auto_search")
    if not isinstance(search, dict):
        raise ValueError("缺少 Auto Best 搜索结果，无法生成动画")
    groups = result.get("groups") or []
    group_by_value = {}
    for group in groups:
        value = int(group["n_value"])
        if value in group_by_value:
            raise ValueError("Auto Best 结果包含重复候选组")
        group_by_value[value] = group

    evaluated_values = [int(value) for value in search.get("evaluated_values") or []]
    if not evaluated_values:
        raise ValueError("Auto Best 没有已完成的候选，无法生成动画")
    if len(set(evaluated_values)) != len(evaluated_values):
        raise ValueError("Auto Best 评价顺序包含重复候选")
    missing = [value for value in evaluated_values if value not in group_by_value]
    if missing:
        raise ValueError("Auto Best 评价顺序与候选组不匹配")

    best_index = result.get("best_index")
    if not isinstance(best_index, int) or not 0 <= best_index < len(groups):
        raise ValueError("Auto Best 缺少有效最佳候选")
    final_best_value = int(groups[best_index]["n_value"])
    terminal_value = search.get("terminal_value")
    completed = bool(search.get("completed")) and not bool(result.get("stopped"))
    if completed and terminal_value is not None and int(terminal_value) != final_best_value:
        raise ValueError("Auto Best 终止值与最佳候选不一致")

    comparisons = list(search.get("comparisons") or [])
    strategy = search.get("strategy") or ("unimodal" if comparisons else "coarse_fine")
    interval = (int(search["start"]), int(search["end"]))
    fine_values = {int(value) for value in search.get("fine_values") or []}
    neighborhoods = [tuple(interval) for interval in search.get("neighborhoods") or []]
    comparison_index = 0
    visible_values = []
    events = []

    def _emit_comparison(comparison, best_value):
        nonlocal interval
        required = tuple(int(value) for value in comparison.get("probe_values") or (
            comparison["left_value"], comparison["right_value"],
        ))
        previous_interval = (
            int(comparison["previous_low"]), int(comparison["previous_high"]),
        )
        next_interval = (int(comparison["low"]), int(comparison["high"]))
        if previous_interval != interval or any(value not in visible_values for value in required):
            raise ValueError("Auto Best 比较记录与搜索区间不一致")
        if comparison.get("direction") not in ("left", "right", "hold"):
            raise ValueError("Auto Best 比较记录缺少有效收缩方向")
        events.append({
            "kind": "comparison",
            "evaluated_values": tuple(visible_values),
            "best_value": best_value,
            "previous_interval": interval,
            "interval": next_interval,
            "comparison": comparison,
        })
        interval = next_interval

    for value in evaluated_values:
        current_groups = [group_by_value[item] for item in visible_values]
        current_best_index = select_best_linearity_group(current_groups, noise_aware=True)
        current_best_value = (
            current_groups[current_best_index]["n_value"] if current_groups else final_best_value
        )
        while (comparison_index < len(comparisons)
               and comparisons[comparison_index].get("next_value") == value):
            _emit_comparison(comparisons[comparison_index], current_best_value)
            comparison_index += 1

        visible_values.append(value)
        visible_groups = [group_by_value[item] for item in visible_values]
        current_best_index = select_best_linearity_group(visible_groups, noise_aware=True)
        current_best_value = visible_groups[current_best_index]["n_value"]
        candidate_interval = interval
        phase = "search"
        if strategy == "coarse_fine":
            phase = "fine" if value in fine_values else "coarse"
            if phase == "fine":
                containing = [item for item in neighborhoods if item[0] <= value <= item[1]]
                if containing:
                    candidate_interval = containing[0]
        events.append({
            "kind": "candidate",
            "value": value,
            "group": group_by_value[value],
            "evaluated_values": tuple(visible_values),
            "best_value": current_best_value,
            "interval": candidate_interval,
            "phase": phase,
        })

        while comparison_index < len(comparisons):
            comparison = comparisons[comparison_index]
            if comparison.get("next_value") is not None:
                break
            required = tuple(int(item) for item in comparison.get("probe_values") or (
                comparison["left_value"], comparison["right_value"],
            ))
            if any(item not in visible_values for item in required):
                break
            _emit_comparison(comparison, current_best_value)
            comparison_index += 1

    if comparison_index != len(comparisons):
        raise ValueError("Auto Best 存在无法按评价顺序回放的比较记录")
    events[-1].update({
        "is_final": True,
        "best_value": final_best_value,
        "completed": completed,
    })
    return events


def sample_std(values):
    """样本标准差（ddof=1）；样本数 < 2 时返回 0.0。"""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))


def compute_detailed_stats(raw_data, *, n_bits=16, raw_before_filter=None,
                           outliers_removed=0):
    """1000CNT 详细统计（纯算法，无 Qt）。

    AVG 为全量算术平均（5% 截尾均值另存 trimmed_avg 供 tooltip 展示）；
    MIN / MAX 为全量极值；STD 为样本标准差（ddof=1，均值与 AVG 同一口径）；
    P-P 为峰峰噪声（MAX-MIN）；noise_free_bits = log2(fs_codes / (6.6*STD))。
    raw_before_filter 为离群筛选前的原始数据（供 Raw MIN/MAX），
    outliers_removed 为被离群筛选剔除的样本数。
    """
    if not raw_data:
        raise ValueError("raw_data 为空，无法统计")

    n = len(raw_data)
    mean_full = sum(raw_data) / n
    sorted_data = sorted(raw_data)
    reg_min, reg_max = sorted_data[0], sorted_data[-1]
    trim = max(1, int(n * 0.05))
    trimmed = sorted_data[trim:-trim] if n > 2 * trim else sorted_data
    trimmed_avg = sum(trimmed) / len(trimmed)
    std = sample_std(raw_data)
    fs_codes = 2 ** int(n_bits)
    before = raw_before_filter if raw_before_filter else raw_data

    return {
        'avg': mean_full,
        'trimmed_avg': trimmed_avg,
        'min': reg_min,
        'max': reg_max,
        'std': std,
        'pp': reg_max - reg_min,
        'count': n,
        'noise_free_bits': (math.log2(fs_codes / (6.6 * std)) if std > 0 else None),
        'raw_min': min(before),
        'raw_max': max(before),
        'outliers_removed': int(outliers_removed),
    }


def resolve_metric_reference(ref_mode="none", k_ideal=None, b_ideal=None,
                             batch_history=None):
    """解析 GAIN/OFFSET 参照来源，返回 (effective_mode, ref_k, ref_b)。

    - spec：k_ideal、b_ideal 都有值时采用（二者齐全且 ref_mode 未显式指定时自动采用）；
    - batch_nominal：取历史 (k_fit, b_fit) 各自的中位数，至少 3 颗 DUT，不足退回 none；
    - none：无参照（默认）。
    """
    mode = str(ref_mode or "none").lower()
    has_spec = k_ideal is not None and b_ideal is not None
    if mode == "batch_nominal":
        pairs = [
            (float(k), float(b)) for k, b in (batch_history or [])
            if k is not None and b is not None
        ]
        if len(pairs) >= 3:
            return (
                "batch_nominal",
                statistics.median(k for k, _ in pairs),
                statistics.median(b for _, b in pairs),
            )
        return "none", None, None
    if mode == "spec" or (mode == "none" and has_spec):
        if has_spec and float(k_ideal) != 0.0:
            return "spec", float(k_ideal), float(b_ideal)
        return "none", None, None
    return "none", None, None


def compute_force_voltage_metrics(
    voltage, mean, *, std=None, n=None, raw_samples=None,
    n_bits=16, v_spec_range=None, k_ideal=None, b_ideal=None,
    ref_mode="none", batch_history=None,
):
    """Force Voltage 性能指标（纯算法，无 Qt）。

    k_fit/b_fit 为 (voltage, mean) 的最小二乘拟合直线；
    INL = mean - (k_fit*v + b_fit)；Step NL = diff(mean)/(k_fit*diff(v)) - 1；
    σ noise = sqrt(mean(std²))；mean_noise = rms(std)/sqrt(mean(n))。
    ENOB 满量程取 fs_codes = 2**n_bits（不再使用 P-P 与扫描范围）：
      ENOB_noise = log2(fs_codes / (σ*sqrt(12)))
      ENOB_DC    = log2(fs_codes / (hypot(σ, rms(INL))*sqrt(12)))
    v_spec_range 有值时另算 ENOB_spec（满量程 = k_fit*v_spec_range）。
    std/n 缺省时从 raw_samples 逐点推导（ddof=1）。
    有效点数 < 3 时返回 {'valid': False, 'points': ...}，UI 显示 N/A。
    """
    points = [
        (float(v), float(m)) for v, m in zip(voltage, mean)
        if v is not None and m is not None
        and math.isfinite(float(v)) and math.isfinite(float(m))
    ]
    count = len(points)
    if count < 3:
        return {'valid': False, 'points': count}
    vs = [p[0] for p in points]
    ms = [p[1] for p in points]
    v_bar = sum(vs) / count
    m_bar = sum(ms) / count
    sxx = sum((v - v_bar) ** 2 for v in vs)
    if sxx <= 0:
        return {'valid': False, 'points': count}
    k_fit = sum((v - v_bar) * (m - m_bar) for v, m in points) / sxx
    b_fit = m_bar - k_fit * v_bar
    inl = [m - (k_fit * v + b_fit) for v, m in points]
    ss_res = sum(e * e for e in inl)
    ss_tot = sum((m - m_bar) ** 2 for m in ms)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0

    # 逐点样本标准差与样本数（优先 runner 记录，缺省从 raw_samples 推导）
    if std is None or n is None:
        std, n = [], []
        for samples in (raw_samples or [])[:count]:
            samples = list(samples or [])
            std.append(sample_std(samples))
            n.append(len(samples))
    std = [float(s) for s in list(std)[:count]]
    n = [int(x) for x in list(n)[:count]]
    have_noise = len(std) == count and len(n) == count and sum(n) > 0
    sigma = math.sqrt(sum(s * s for s in std) / count) if have_noise else None
    mean_n = sum(n) / count if have_noise else 0.0
    mean_noise = sigma / math.sqrt(mean_n) if have_noise and mean_n > 0 else None
    inl_abs_max = max(abs(e) for e in inl)
    inl_below_noise = bool(
        mean_noise is not None and mean_noise > 0 and inl_abs_max < 4 * mean_noise
    )

    step_nl = []
    for i in range(count - 1):
        denom = k_fit * (vs[i + 1] - vs[i])
        if denom != 0:
            step_nl.append((ms[i + 1] - ms[i]) / denom - 1.0)

    fs_codes = 2 ** int(n_bits)
    sqrt12 = math.sqrt(12.0)
    enob_noise = (math.log2(fs_codes / (sigma * sqrt12))
                  if sigma is not None and sigma > 0 else None)
    rms_inl = math.sqrt(ss_res / count)
    dc_noise = math.hypot(sigma, rms_inl) if sigma is not None else None
    enob_dc = (math.log2(fs_codes / (dc_noise * sqrt12))
               if dc_noise is not None and dc_noise > 0 else None)
    enob_spec = None
    if v_spec_range is not None and sigma is not None and sigma > 0:
        spec_fs = abs(k_fit * float(v_spec_range))
        if spec_fs > 0:
            enob_spec = math.log2(spec_fs / (sigma * sqrt12))

    eff_mode, ref_k, ref_b = resolve_metric_reference(
        ref_mode, k_ideal, b_ideal, batch_history,
    )
    gain_error_pct = ((k_fit / ref_k - 1.0) * 100.0
                      if eff_mode != "none" and ref_k else None)
    offset_error_lsb = b_fit - ref_b if eff_mode != "none" else None

    return {
        'valid': True,
        'points': count,
        'fs_codes': fs_codes,
        'k_fit': k_fit,
        'b_fit': b_fit,
        'linearity': r2,
        'inl': inl,
        'inl_max': max(inl),
        'inl_min': min(inl),
        'inl_below_noise': inl_below_noise,
        'mean_noise_lsb': mean_noise,
        'step_nl_max': max(step_nl) if step_nl else None,
        'step_nl_min': min(step_nl) if step_nl else None,
        'sigma_noise_lsb': sigma,
        'enob_noise': enob_noise,
        'enob_dc': enob_dc,
        'enob_spec': enob_spec,
        'ref_mode': eff_mode,
        'ref_k': ref_k,
        'ref_b': ref_b,
        'gain_error_pct': gain_error_pct,
        'offset_error_lsb': offset_error_lsb,
        'v_min': min(vs),
        'v_max': max(vs),
        'code_coverage_pct': (max(ms) - min(ms)) / fs_codes * 100.0,
    }


def histogram_dnl_inl(codes, code_lo, code_hi):
    """慢斜坡扫描的码级直方图 DNL/INL（纯算法，无 Qt）。

    统计 [code_lo, code_hi] 区间直方图 h，首尾各丢弃 1 个码；
    DNL = h/mean(h) - 1；INL = cumsum(DNL) 再去除线性趋势；
    平均每码命中数 < 20 时给出 warning；缺失码（h==0）DNL = -1。
    返回 {'codes', 'dnl', 'inl', 'missing_codes', 'mean_hits', 'warning'}。
    """
    code_lo, code_hi = int(code_lo), int(code_hi)
    if code_hi - code_lo < 2:
        raise ValueError("码区间至少需 3 个码（首尾各丢弃 1 个）")
    hist = [0] * (code_hi - code_lo + 1)
    for code in codes:
        c = int(code)
        if code_lo <= c <= code_hi:
            hist[c - code_lo] += 1
    interior = hist[1:-1]
    mean_hits = sum(interior) / len(interior)
    if mean_hits <= 0:
        raise ValueError("区间内无码命中，无法统计 DNL/INL")
    dnl = [h / mean_hits - 1.0 for h in interior]
    cum = []
    acc = 0.0
    for d in dnl:
        acc += d
        cum.append(acc)
    # 去除线性趋势（对码序号做最小二乘直线后扣除）
    m = len(cum)
    x_bar = (m - 1) / 2.0
    y_bar = sum(cum) / m
    sxx = sum((i - x_bar) ** 2 for i in range(m))
    slope = (sum((i - x_bar) * (y - y_bar) for i, y in enumerate(cum)) / sxx
             if sxx > 0 else 0.0)
    intercept = y_bar - slope * x_bar
    inl = [y - (slope * i + intercept) for i, y in enumerate(cum)]
    missing = [code_lo + 1 + i for i, h in enumerate(interior) if h == 0]
    warning = (
        f"Average hits per code {mean_hits:.1f} < 20; DNL/INL confidence is limited"
        if mean_hits < 20 else None
    )
    return {
        'codes': list(range(code_lo + 1, code_hi)),
        'dnl': dnl,
        'inl': inl,
        'missing_codes': missing,
        'mean_hits': mean_hits,
        'warning': warning,
    }


# ---------------------------------------------------------------------------
# FT Calibration Check（两点 FT 校准检查，纯函数）
# ---------------------------------------------------------------------------

# 校准码 base±offset 表达式，操作数为十进制（可小数）或 0x 十六进制整数
_RAW_LSB_EXPR_RE = re.compile(
    r"^\s*(0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?)\s*([+-])\s*"
    r"(0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?)\s*$"
)


def _raw_lsb_operand(token):
    if token.lower().startswith("0x"):
        return float(int(token, 16))
    return float(token)


def parse_raw_lsb_value(text):
    """解析 FT 校准码（LSB）输入：十进制 / 0x 十六进制，支持 base±offset 自动求值。

    例：``'319'`` / ``'0x13F'`` → 319.0；``'0x13F+2000'`` / ``'319+2000'`` → 2319.0。
    非法输入抛 ValueError。
    """
    s = str(text).strip()
    m = _RAW_LSB_EXPR_RE.match(s)
    if m:
        value = _raw_lsb_operand(m.group(1))
        offset = _raw_lsb_operand(m.group(3))
        return value + offset if m.group(2) == "+" else value - offset
    return _raw_lsb_operand(s)


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


def filter_mean_deviation(samples, pos_offset, neg_offset):
    """按与均值的正/负向最大偏移筛除离群样本（非对称阈值，单趟，保持顺序）。

    以全体样本均值为基准：偏差 > +pos_offset（正向超限）或 < -neg_offset
    （负向超限）的样本被剔除，其余原值保留（不聚合、长度仅减少）。
    返回 (kept, removed)——removed 为被剔除样本原值列表（保持原顺序）；
    阈值过严时 kept 可能为空列表，是否回退原始数据由调用方决定。
    """
    n = len(samples)
    if n == 0:
        return [], []
    avg = sum(samples) / n
    pos_offset = max(0.0, float(pos_offset))
    neg_offset = max(0.0, float(neg_offset))
    kept, removed = [], []
    for v in samples:
        if -neg_offset <= (v - avg) <= pos_offset:
            kept.append(v)
        else:
            removed.append(v)
    return kept, removed


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
        'length_divisor': {'param': 'count', 'min': 3},
        'params': {
            'count': {'label': 'Group Size', 'default': 10, 'min': 3, 'max': 10000,
                      'step': 1, 'decimals': 0},
        },
    },
    'deviation_trim_mean': {
        'name': 'Deviation Trim (偏差剔除平均)',
        'desc': '每 N 个连续样本先求均值，剔除偏差超过 Tolerance% 的样本后取平均（每组输出 1 个值）',
        'principle': '思路: 每 count 个连续样本为一组，先求组内均值，剔除与均值偏差超过 tolerance_pct% 的样本，剩余取平均作为该组输出（每组 1 值，长度缩为 1/count）',
        'func': algo_deviation_trim_mean,
        'length_divisor': {'param': 'count', 'min': 1},
        'params': {
            'count': {'label': 'Group Size', 'default': 10, 'min': 2, 'max': 10000,
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


def algorithm_length_divisor(algo_config):
    """分组聚合类算法的长度除数：原始采样数 = Points × 除数；非缩短类返回 1。

    除数元信息来自注册表 ``length_divisor``（param + min），新增分组类算法
    登记该键即可自动获得 Points 换算，无需改 UI。
    """
    if not algo_config:
        return 1
    spec = ALGORITHM_REGISTRY.get(algo_config.get('id'))
    if not spec:
        return 1
    meta = spec.get('length_divisor')
    if not meta:
        return 1
    params = algo_config.get('params') or {}
    default = spec['params'][meta['param']]['default']
    return max(meta['min'], int(params.get(meta['param'], default)))


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
    return f"噪声等级={level} (STD={std:.2f} code, P-P={pp:.0f} code)"


def format_log_table(headers, rows, sep=","):
    """日志表格按列对齐：每列取表头与数据的最大宽度，右对齐后以 sep 连接。

    单元格须为已格式化字符串（浮点最多两位小数由调用侧保证）；
    返回行不含 [DATA] 标签，由调用侧自行添加以触发日志区等宽渲染。
    """
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = [sep.join(h.rjust(w) for h, w in zip(headers, widths))]
    lines.extend(sep.join(c.rjust(w) for c, w in zip(row, widths)) for row in rows)
    return lines


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
