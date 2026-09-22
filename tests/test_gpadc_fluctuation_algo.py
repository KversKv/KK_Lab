# -*- coding: utf-8 -*-
"""gpadc_analysis 波动评估与算法效果对比纯函数测试。"""

import random

from core.pmu_test.gpadc.gpadc_analysis import (
    algo_moving_average,
    algo_debounce,
    algo_gain_compensation,
    algo_trimmed_mean,
    algo_deviation_trim_mean,
    apply_algorithm,
    assess_fluctuation,
    compare_algorithm_effect,
    ALGORITHM_REGISTRY,
)


def test_assess_fluctuation_levels():
    assert "优秀" in assess_fluctuation(0.5, 3)
    assert "良好" in assess_fluctuation(1.5, 6)
    assert "一般" in assess_fluctuation(3.0, 12)
    assert "明显波动" in assess_fluctuation(5.0, 20)
    # 边界值：STD=1.0 仍属优秀
    assert "优秀" in assess_fluctuation(1.0, 4)


def test_compare_algorithm_effect_moving_average_reduces_noise():
    rng = random.Random(42)
    raw = [max(0, int(rng.gauss(2844, 3.0))) for _ in range(1000)]
    processed = algo_moving_average(raw, window=8)
    effect = compare_algorithm_effect(raw, processed)
    assert effect is not None
    assert effect['std_after'] < effect['std_before']
    assert effect['pp_after'] <= effect['pp_before']
    assert effect['count_before'] == effect['count_after'] == 1000
    assert effect['std_improve_pct'] > 0


def test_compare_algorithm_effect_debounce_count_shrink():
    raw = [100, 101, 150, 102, 103]  # 150 相对前一保留样本跳变超阈值被剔除
    processed = algo_debounce(raw, threshold=4)
    effect = compare_algorithm_effect(raw, processed)
    assert effect is not None
    assert effect['count_after'] < effect['count_before']


def test_compare_algorithm_effect_gain_amplifies_noise():
    rng = random.Random(7)
    raw = [rng.gauss(1000, 2.0) for _ in range(500)]
    processed = algo_gain_compensation(raw, gain=2.0)
    effect = compare_algorithm_effect(raw, processed)
    assert effect is not None
    assert effect['std_after'] > effect['std_before']
    assert effect['std_improve_pct'] < 0  # 负值 = 噪声放大


def test_compare_algorithm_effect_empty_and_zero_before():
    assert compare_algorithm_effect([], [1, 2]) is None
    assert compare_algorithm_effect([1, 2], []) is None
    # before 完全平坦（std=0, pp=0）时百分比为 None
    effect = compare_algorithm_effect([5, 5, 5, 5], [5, 5, 5, 5])
    assert effect is not None
    assert effect['std_improve_pct'] is None
    assert effect['pp_improve_pct'] is None


def test_apply_algorithm_none_passthrough():
    raw = [1, 2, 3]
    assert apply_algorithm(raw, None) == raw
    assert apply_algorithm(raw, {'id': 'not_exist'}) == raw


def test_trimmed_mean_basic():
    # 单组 5 点：去掉 max=100 / min=1，剩余 [2,3,4] 平均 = 3.0
    assert algo_trimmed_mean([1, 2, 3, 100, 4], count=5) == [3.0]
    # 两组各 5 点 → 2 个输出
    raw = [1, 2, 3, 100, 4, 10, 11, 12, 13, 999]
    assert algo_trimmed_mean(raw, count=5) == [3.0, 12.0]


def test_trimmed_mean_partial_tail_and_clamp():
    # 7 点 count=5：第 2 组仅 2 点（<3）退化为直接平均
    raw = [1, 2, 3, 100, 4, 10, 20]
    assert algo_trimmed_mean(raw, count=5) == [3.0, 15.0]
    # count 小于 3 时被钳到 3
    assert algo_trimmed_mean([1, 100, 2], count=1) == [2.0]
    assert algo_trimmed_mean([], count=5) == []


def test_deviation_trim_mean_basic():
    # 均值 1100，10% 容差=110，1500 偏差 400 被剔除，剩余平均 1000
    raw = [1000, 1001, 999, 1000, 1500]
    assert algo_deviation_trim_mean(raw, count=5, tolerance_pct=10.0) == [1000.0]


def test_deviation_trim_mean_fallback_and_blocks():
    # 均值 120、10% 容差=12，所有点偏差均超限被剔除 → 退化为原均值 120
    assert algo_deviation_trim_mean([100, 101, 99, 100, 200], count=5,
                                    tolerance_pct=10.0) == [120.0]
    # 分块：每 2 点一组 → 5 个输出
    raw = [1000, 1001, 999, 1000, 1500]
    out = algo_deviation_trim_mean(raw, count=2, tolerance_pct=10.0)
    assert len(out) == 3  # 2+2+1
    assert algo_deviation_trim_mean([], count=5) == []


def test_new_algorithms_registered():
    for algo_id in ('trimmed_mean', 'deviation_trim_mean'):
        spec = ALGORITHM_REGISTRY.get(algo_id)
        assert spec is not None and callable(spec['func'])
        assert 'count' in spec['params']
    assert 'tolerance_pct' in ALGORITHM_REGISTRY['deviation_trim_mean']['params']
    # 经注册表 apply 通路生效
    out = apply_algorithm([1, 2, 3, 100, 4], {'id': 'trimmed_mean', 'params': {'count': 5}})
    assert out == [3.0]
