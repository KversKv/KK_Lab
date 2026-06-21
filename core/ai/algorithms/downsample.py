"""波形降采样算法（迁移自 waveform_provider，逻辑不变）。

LTTB（Largest-Triangle-Three-Buckets）：把数百万点降到 ~1500 点，保留视觉峰谷。
adaptive_downsample（C2）：事件感知非均匀降采样——平稳段 min-max 稀疏、事件段高密度保留，
                           并产出 density_map 显式标注各区段采样密度（C7 配套）。

纯 Python；adaptive 在缺 numpy 或无事件时回退 LTTB。禁 import Qt。
"""
from __future__ import annotations

import math

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


def lttb_downsample(
    times: list[float], values: list[float], threshold: int
) -> tuple[list[float], list[float]]:
    """Largest-Triangle-Three-Buckets 降采样到约 threshold 点，保留视觉峰谷。

    threshold >= 数据点数或 < 3 时原样返回。
    """
    n = len(values)
    if threshold >= n or threshold < 3 or n == 0:
        return list(times), list(values)

    sampled_t: list[float] = [times[0]]
    sampled_v: list[float] = [values[0]]

    bucket_size = (n - 2) / (threshold - 2)
    a = 0

    for i in range(threshold - 2):
        next_start = int(math.floor((i + 1) * bucket_size) + 1)
        next_end = int(math.floor((i + 2) * bucket_size) + 1)
        next_end = min(next_end, n)
        if next_start >= next_end:
            next_start = max(0, next_end - 1)

        avg_x = 0.0
        avg_y = 0.0
        avg_count = next_end - next_start
        if avg_count <= 0:
            avg_count = 1
        for j in range(next_start, next_start + avg_count):
            idx = min(j, n - 1)
            avg_x += times[idx]
            avg_y += values[idx]
        avg_x /= avg_count
        avg_y /= avg_count

        range_start = int(math.floor(i * bucket_size) + 1)
        range_end = int(math.floor((i + 1) * bucket_size) + 1)
        range_end = min(range_end, n)

        point_ax = times[a]
        point_ay = values[a]

        max_area = -1.0
        chosen = range_start
        for j in range(range_start, range_end):
            area = abs(
                (point_ax - avg_x) * (values[j] - point_ay)
                - (point_ax - times[j]) * (avg_y - point_ay)
            ) * 0.5
            if area > max_area:
                max_area = area
                chosen = j

        sampled_t.append(times[chosen])
        sampled_v.append(values[chosen])
        a = chosen

    sampled_t.append(times[-1])
    sampled_v.append(values[-1])
    return sampled_t, sampled_v


def adaptive_downsample(
    times: list[float],
    values: list[float],
    events: list[tuple[int, int]],
    *,
    base_points: int = 1200,
    event_keep: int = 60,
) -> tuple[list[float], list[float], list[dict]]:
    """C2：事件感知非均匀降采样。返回 (ds_times, ds_values, density_map)。

    density_map 显式标注各区段采样密度，供 AI 正确解读时间轴为"非均匀采样"。
    """
    n = len(values)
    if n == 0:
        return [], [], []
    if not _HAS_NUMPY or not events:
        ds_t, ds_v = lttb_downsample(list(times), list(values), base_points)
        return ds_t, ds_v, [{"kind": "uniform", "points": len(ds_v)}]

    keep = [False] * n
    density: list[dict] = []
    for i0, i1 in events:
        i0 = max(0, i0)
        i1 = min(n - 1, i1)
        lo = max(0, i0 - 2)
        hi = min(n - 1, i1 + 2)
        for j in range(lo, hi + 1):
            keep[j] = True
        density.append(
            {
                "start": round(times[i0], 6),
                "end": round(times[i1], 6),
                "density": "full",
                "points": hi - lo + 1,
            }
        )

    bucket = max(1, n // max(1, base_points))
    ds_idx: list[int] = []
    for b in range(0, n, bucket):
        end = min(n, b + bucket)
        seg = values[b:end]
        lo_off = min(range(len(seg)), key=lambda k: seg[k])
        hi_off = max(range(len(seg)), key=lambda k: seg[k])
        ds_idx.append(b + min(lo_off, hi_off))
        if hi_off != lo_off:
            ds_idx.append(b + max(lo_off, hi_off))
    for i, flag in enumerate(keep):
        if flag:
            ds_idx.append(i)
    ds_idx = sorted(set(ds_idx))
    ds_t = [round(times[i], 6) for i in ds_idx]
    ds_v = [values[i] for i in ds_idx]
    density.insert(0, {"kind": "minmax_baseline", "bucket_points": bucket})
    return ds_t, ds_v, density
