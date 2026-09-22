# -*- coding: utf-8 -*-
"""gpadc_analysis 波动评估与算法效果对比纯函数测试。"""

import random

from core.pmu_test.gpadc.gpadc_analysis import (
    algo_moving_average,
    algo_debounce,
    algo_gain_compensation,
    apply_algorithm,
    assess_fluctuation,
    compare_algorithm_effect,
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
