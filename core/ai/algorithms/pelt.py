"""PELT 均值变点分段算法（迁移自 waveform_provider，逻辑不变）。

C10：PELT 均值变点检测，把信号切成均质段（专抓 RX/电平/DVFS 平台）。
C11：classify_segment 按 宽度 + 峰均比 + 均值层级 给段贴标签。
C3：segment_features 对每段算 均值/峰值/峰均比/宽度/上升/积分电荷/能量并贴标签。

自研均值代价（SSE）实现，零依赖；复杂度近 O(n)（剪枝后），最坏 O(n^2)，
为保护性能仅对 max_n 内小窗启用（drill-down 子窗）。需 numpy。禁 import Qt。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from core.ai.algorithms.base import (
    Segment,
    SegmentResult,
    Signal,
    WaveformAlgorithm,
    statistics,
    trapezoid,
)
from core.ai.algorithms.registry import register

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


@dataclass
class PeltParams:
    """PELT 参数。"""

    pen: float = 6.0
    min_size: int = 3
    max_n: int = 4000
    auto_scale: bool = True
    factor: float = 1.0
    max_report: int = 40


def detect_change_points(
    values: list[float],
    *,
    pen: float = 6.0,
    min_size: int = 3,
    max_n: int = 4000,
    auto_scale: bool = True,
) -> list[int]:
    """返回变点索引列表（不含 0 与 N）。保留原 detect_segments_pelt 行为。

    auto_scale=True：按 BIC 把惩罚缩放为 pen · sigma² · log(n)，sigma² 取相邻差分
    的鲁棒噪声估计（MAD），使 pen 对量纲（A vs mA）鲁棒。
    """
    n = len(values)
    if not _HAS_NUMPY or n < 2 * min_size or n > max_n:
        return []
    v = np.asarray(values, dtype=float)
    if auto_scale:
        diffs = np.abs(np.diff(v))
        noise_mad = float(np.median(diffs)) if diffs.size else 0.0
        sigma = noise_mad * 1.4826 / math.sqrt(2.0)
        sigma2 = max(sigma * sigma, 1e-12)
        pen = pen * sigma2 * math.log(max(n, 2))
    cs = np.concatenate(([0.0], np.cumsum(v)))
    cs2 = np.concatenate(([0.0], np.cumsum(v * v)))

    def _cost(a: int, b: int) -> float:
        m = b - a
        if m <= 0:
            return 0.0
        s = cs[b] - cs[a]
        s2 = cs2[b] - cs2[a]
        return float(s2 - s * s / m)

    F = np.full(n + 1, np.inf)
    F[0] = -pen
    cp: list[list[int]] = [[] for _ in range(n + 1)]
    R = [0]
    for tau in range(min_size, n + 1):
        best = math.inf
        arg = 0
        for s in R:
            if tau - s < min_size:
                continue
            c = F[s] + _cost(s, tau) + pen
            if c < best:
                best, arg = c, s
        F[tau] = best
        cp[tau] = cp[arg] + [arg]
        R = [s for s in R if F[s] + _cost(s, tau) <= F[tau]] + [tau]
    return [c for c in cp[n] if c > 0]


def classify_segment(
    mean: float, peak: float, width_s: float, baseline: float, std: float
) -> str:
    """按 宽度 + 峰均比 + 均值层级 给段贴标签（保留原行为）。

    返回 spike（尖峰）/ plateau（平台）/ valley（低谷）/ ramp（缓变）。
    """
    pk_mean = (peak / mean) if mean > 1e-12 else float("inf")
    above = mean - baseline
    band = max(abs(baseline) * 0.2, 1e-9)
    peak_above = peak - baseline
    narrow = width_s <= 1e-3
    if narrow and peak_above >= 4.0 * max(band, 1e-9):
        return "spike"
    if pk_mean >= 1.8 and width_s <= 5e-3:
        return "spike"
    if above < -band:
        return "valley"
    if above > band and pk_mean < 1.5:
        return "plateau"
    if pk_mean >= 1.8:
        return "spike"
    return "ramp"


def segment_features(
    times: list[float],
    values: list[float],
    segments: list[tuple[int, int]],
    *,
    baseline: float | None = None,
    std: float = 0.0,
    max_report: int = 30,
) -> list[Segment]:
    """对每段算特征并贴标签，返回归一化 Segment 列表（不做量纲换算）。

    电荷 = ∫i·dt（梯形积分，A·s/3600 → mAh ×1000 → µAh）。量纲换算在 to_dict(factor)。
    """
    n = len(values)
    if n == 0 or not segments:
        return []
    if baseline is None:
        baseline = (sum(values) / n) if n else 0.0
    dt = abs(times[1] - times[0]) if n >= 2 else 0.0
    out: list[Segment] = []
    for i0, i1 in segments:
        i0 = max(0, i0)
        i1 = min(n - 1, i1)
        if i1 < i0:
            continue
        seg_v = values[i0:i1 + 1]
        m = len(seg_v)
        seg_mean = sum(seg_v) / m
        seg_peak = max(seg_v, key=abs)
        width_s = abs(times[i1] - times[i0])
        rise = seg_v[-1] - seg_v[0]
        charge_raw = trapezoid(values[i0:i1 + 1], dt)
        charge_uah = (charge_raw / 1000.0) / 3.6
        label = classify_segment(seg_mean, abs(seg_peak), width_s, baseline, std)
        pk_mean = (seg_peak / seg_mean) if abs(seg_mean) > 1e-12 else 0.0
        out.append(
            Segment(
                start=times[i0],
                end=times[i1],
                label=label,
                mean=seg_mean,
                peak=seg_peak,
                peak_to_mean=pk_mean,
                width_ms=width_s * 1e3,
                rise=rise,
                charge_uAh=charge_uah,
                point_count=m,
            )
        )
        if len(out) >= max_report:
            break
    return out


@register
class PeltAlgorithm(WaveformAlgorithm):
    name = "pelt"
    kind = "segment"
    params_cls = PeltParams

    def run(self, signal: Signal, params: PeltParams | None = None) -> SegmentResult:
        params = params or PeltParams()
        times = signal.times
        values = signal.values
        if not values:
            return SegmentResult(segments=[], info={"algorithm": self.name})
        _, _, avg, std = statistics(values)
        cps = detect_change_points(
            values,
            pen=params.pen,
            min_size=params.min_size,
            max_n=params.max_n,
            auto_scale=params.auto_scale,
        )
        bounds = [0] + cps + [len(values)]
        seg_ranges = [
            (bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)
        ]
        segments = segment_features(
            times, values, seg_ranges, baseline=avg, std=std,
            max_report=params.max_report,
        )
        info = {
            "algorithm": self.name,
            "change_points": len(cps),
            "segments": len(segments),
        }
        return SegmentResult(segments=segments, info=info)
