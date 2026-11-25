# -*- coding: utf-8 -*-
"""GPADC 指标卡新口径纯函数验收（合成数据，无 Qt）。

合成数据：mean = 16228*v + 15370 + 高斯噪声（σ=20 LSB，每点 n=100），
可选叠加锯齿（幅度 ±25 LSB，周期 7600 码）；v 取 0~1.5 V，步进 1 mV。
"""

import math
import random

from core.pmu_test.gpadc.gpadc_analysis import (
    compute_detailed_stats,
    compute_force_voltage_metrics,
    histogram_dnl_inl,
    resolve_metric_reference,
    sample_std,
)

_K_TRUE = 16228.0
_B_TRUE = 15370.0
_SIGMA = 20.0
_N_PER_POINT = 100


def _synth_sweep(sawtooth=False, seed=42):
    rng = random.Random(seed)
    steps = int(round(1.5 / 0.001))
    voltage = [round(i * 0.001, 6) for i in range(steps + 1)]
    # 锯齿非线性（峰值 25 LSB，周期 7600 码）：扫描不足整周期，
    # 先扣除自身线性趋势再按峰值归一到 25 LSB（INL 定义即去趋势残差）
    saw = [25.0 * (2.0 * (((_K_TRUE * v + _B_TRUE) % 7600.0) / 7600.0) - 1.0)
           for v in voltage]
    if sawtooth:
        cnt = len(voltage)
        v_bar = sum(voltage) / cnt
        s_bar = sum(saw) / cnt
        sxx = sum((v - v_bar) ** 2 for v in voltage)
        slope = sum((v - v_bar) * (s - s_bar) for v, s in zip(voltage, saw)) / sxx
        intercept = s_bar - slope * v_bar
        saw = [s - (slope * v + intercept) for v, s in zip(voltage, saw)]
        peak = max(abs(s) for s in saw)
        saw = [s * (25.0 / peak) for s in saw]
    else:
        saw = [0.0] * len(voltage)
    mean, std, n = [], [], []
    for v, offset in zip(voltage, saw):
        code = _K_TRUE * v + _B_TRUE
        samples = [code + offset + rng.gauss(0.0, _SIGMA)
                   for _ in range(_N_PER_POINT)]
        mean.append(sum(samples) / len(samples))
        std.append(sample_std(samples))
        n.append(len(samples))
    return voltage, mean, std, n


# ---------------------------------------------------------------------------
# 1. ENOB 新口径
# ---------------------------------------------------------------------------

def test_enob_noise_matches_sigma_formula():
    v, m, s, n = _synth_sweep()
    p = compute_force_voltage_metrics(v, m, std=s, n=n)
    assert p['valid']
    expected = math.log2(65536 / (_SIGMA * math.sqrt(12)))
    assert abs(p['enob_noise'] - expected) < 0.05
    assert abs(p['enob_dc'] - p['enob_noise']) < 0.05


def test_enob_spec_uses_kfit_times_spec_range():
    v, m, s, n = _synth_sweep()
    p = compute_force_voltage_metrics(v, m, std=s, n=n, v_spec_range=2.0)
    expected = math.log2(abs(p['k_fit'] * 2.0) / (p['sigma_noise_lsb'] * math.sqrt(12)))
    assert p['enob_spec'] is not None
    assert abs(p['enob_spec'] - expected) < 1e-9
    # 未提供 v_spec_range 时不产生 spec 变体
    p2 = compute_force_voltage_metrics(v, m, std=s, n=n)
    assert p2['enob_spec'] is None


# ---------------------------------------------------------------------------
# 2. spec 参照：Gain Err / Offset Err
# ---------------------------------------------------------------------------

def test_gain_offset_vs_spec():
    v, m, s, n = _synth_sweep()
    p = compute_force_voltage_metrics(
        v, m, std=s, n=n, k_ideal=16000.0, b_ideal=15000.0,
    )
    # k_ideal/b_ideal 齐全时自动采用 spec 参照
    assert p['ref_mode'] == 'spec'
    assert abs(p['gain_error_pct'] - 1.425) / 1.425 < 0.01
    assert abs(p['offset_error_lsb'] - 370.0) / 370.0 < 0.01


# ---------------------------------------------------------------------------
# 4. batch_nominal 参照：中位数 / 不足 3 组退回 none
# ---------------------------------------------------------------------------

def test_batch_reference_median_and_fallback():
    history = [(16000.0, 15000.0), (16100.0, 15100.0), (16200.0, 15200.0),
               (16300.0, 15300.0), (16400.0, 15400.0)]
    mode, ref_k, ref_b = resolve_metric_reference(
        'batch_nominal', batch_history=history,
    )
    assert mode == 'batch_nominal'
    assert ref_k == 16200.0
    assert ref_b == 15200.0
    # 少于 3 组退回 none
    mode2, k2, b2 = resolve_metric_reference(
        'batch_nominal', batch_history=history[:2],
    )
    assert mode2 == 'none' and k2 is None and b2 is None


def test_batch_reference_in_metrics():
    v, m, s, n = _synth_sweep()
    history = [(16000.0, 15000.0), (16100.0, 15100.0), (16200.0, 15200.0),
               (16300.0, 15300.0), (16400.0, 15400.0)]
    p = compute_force_voltage_metrics(
        v, m, std=s, n=n, ref_mode='batch_nominal', batch_history=history,
    )
    assert p['ref_mode'] == 'batch_nominal'
    assert abs(p['gain_error_pct'] - (_K_TRUE / 16200.0 - 1) * 100) < 0.05
    assert abs(p['offset_error_lsb'] - (_B_TRUE - 15200.0)) < 5.0
    p2 = compute_force_voltage_metrics(
        v, m, std=s, n=n, ref_mode='batch_nominal', batch_history=history[:2],
    )
    assert p2['ref_mode'] == 'none'
    assert p2['gain_error_pct'] is None and p2['offset_error_lsb'] is None


# ---------------------------------------------------------------------------
# 5. INL：锯齿峰值 / 无锯齿低于噪声底
# ---------------------------------------------------------------------------

def test_inl_sawtooth_peak():
    # 固定种子：近峰多点均值噪声（σ≈2 LSB）会叠加 ~2 LSB，峰值落在 25±3 内
    v, m, s, n = _synth_sweep(sawtooth=True, seed=2)
    p = compute_force_voltage_metrics(v, m, std=s, n=n)
    peak = max(abs(p['inl_max']), abs(p['inl_min']))
    assert 22.0 <= peak <= 28.0
    assert not p['inl_below_noise']


def test_inl_below_noise_floor_without_sawtooth():
    v, m, s, n = _synth_sweep()
    p = compute_force_voltage_metrics(v, m, std=s, n=n)
    assert p['inl_below_noise']
    # mean_noise = rms(std)/sqrt(mean(n)) ≈ 20/10 = 2 LSB
    assert abs(p['mean_noise_lsb'] - 2.0) < 0.2


def test_step_nl_signed_and_small_for_linear_data():
    v, m, s, n = _synth_sweep()
    p = compute_force_voltage_metrics(v, m, std=s, n=n)
    assert p['step_nl_max'] > 0 > p['step_nl_min']
    # 纯线性 + 噪声：步进偏差量级 ~ 噪声/(k_fit*Δv) ≈ 2.8/16.2 ≈ 0.17
    assert abs(p['step_nl_max']) < 1.0
    assert abs(p['step_nl_min']) < 1.0


# ---------------------------------------------------------------------------
# 6. 码级直方图 DNL/INL
# ---------------------------------------------------------------------------

def test_histogram_dnl_uniform_ramp():
    codes = [c for c in range(1000, 1101) for _ in range(50)]
    r = histogram_dnl_inl(codes, 1000, 1100)
    assert all(abs(d) < 0.5 for d in r['dnl'])
    assert r['missing_codes'] == []
    assert r['warning'] is None
    # 首尾各丢弃 1 个码
    assert r['codes'][0] == 1001 and r['codes'][-1] == 1099


def test_histogram_dnl_missing_code():
    codes = [c for c in range(1000, 1101) if c != 1050 for _ in range(50)]
    r = histogram_dnl_inl(codes, 1000, 1100)
    assert 1050 in r['missing_codes']
    idx = r['codes'].index(1050)
    assert r['dnl'][idx] == -1.0


def test_histogram_low_hits_warning():
    codes = [c for c in range(1000, 1021) for _ in range(10)]
    r = histogram_dnl_inl(codes, 1000, 1020)
    assert r['warning'] is not None


# ---------------------------------------------------------------------------
# 7. 有效点数 < 3 → invalid（UI 显示 N/A）
# ---------------------------------------------------------------------------

def test_fewer_than_3_points_invalid():
    p = compute_force_voltage_metrics([0.0, 0.1], [100.0, 200.0])
    assert p['valid'] is False
    assert p['points'] == 2
    p2 = compute_force_voltage_metrics([], [])
    assert p2['valid'] is False


# ---------------------------------------------------------------------------
# 1000CNT 统计口径
# ---------------------------------------------------------------------------

def test_detailed_stats_full_mean_and_trimmed_tooltip():
    rng = random.Random(7)
    raw = [rng.gauss(2844.0, 3.0) for _ in range(1000)]
    stats = compute_detailed_stats(raw)
    assert abs(stats['avg'] - sum(raw) / len(raw)) < 1e-9
    # 截尾均值与全量均值不同但接近
    assert stats['trimmed_avg'] != stats['avg']
    assert abs(stats['trimmed_avg'] - stats['avg']) < 1.0
    # STD 与 AVG 同一均值口径（ddof=1）
    mean_full = sum(raw) / len(raw)
    expected_std = math.sqrt(sum((x - mean_full) ** 2 for x in raw) / (len(raw) - 1))
    assert abs(stats['std'] - expected_std) < 1e-9
    assert stats['pp'] == stats['max'] - stats['min']
    assert stats['count'] == 1000


def test_detailed_stats_noise_free_bits_and_raw_extremes():
    raw = [100, 102, 98, 101, 99] * 20
    before = raw + [50000, 0]
    stats = compute_detailed_stats(raw, raw_before_filter=before, outliers_removed=2)
    expected = math.log2(65536 / (6.6 * stats['std']))
    assert abs(stats['noise_free_bits'] - expected) < 1e-9
    assert stats['raw_min'] == 0 and stats['raw_max'] == 50000
    assert stats['outliers_removed'] == 2
    # n_bits 可配
    stats12 = compute_detailed_stats(raw, n_bits=12)
    assert abs(stats12['noise_free_bits'] - math.log2(4096 / (6.6 * stats['std']))) < 1e-9


def test_detailed_stats_zero_std_noise_free_none():
    stats = compute_detailed_stats([1234] * 50)
    assert stats['std'] == 0.0
    assert stats['noise_free_bits'] is None