"""STA-LTA 事件检测算法（迁移自 waveform_provider.detect_events_stalta，逻辑不变）。

C1：STA-LTA 能量比定位窄尖峰/突发事件 + MAD 绝对幅值闸门滤伪事件。
能量比定位"哪里有突变"（对相对变化敏感），MAD 闸门裁定"突变够不够大"
（绝对幅值，抗 99% 睡眠基线下 std 塌陷）。参数默认值与原实测一致（§9.7）。

需 numpy（向量化前缀和 O(N) 单趟）；缺 numpy 时返回空结果（调用方回退旧逻辑）。
禁 import Qt。
"""
from __future__ import annotations

from dataclasses import dataclass

from core.ai.algorithms.base import (
    Event,
    EventResult,
    Signal,
    WaveformAlgorithm,
)
from core.ai.algorithms.registry import register

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


@dataclass
class StaLtaParams:
    """STA-LTA 参数（默认值与原实测一致，§9.7）。"""

    sta_s: float = 1e-4
    lta_s: float = 5e-3
    on: float = 4.0
    off: float = 1.5
    merge_gap_s: float = 2e-4
    mad_k: float = 6.0


def detect_ranges_stalta(
    times: list[float],
    values: list[float],
    params: StaLtaParams | None = None,
) -> list[tuple[int, int]]:
    """返回事件索引区间列表 [(i0, i1), ...]（保留原 detect_events_stalta 行为）。"""
    params = params or StaLtaParams()
    n = len(values)
    if not _HAS_NUMPY or n < 4:
        return []
    t = np.asarray(times, dtype=float)
    v = np.asarray(values, dtype=float)
    dt = float(np.median(np.diff(t))) if n >= 2 else 0.0
    if dt <= 0.0:
        return []

    sta_n = max(1, int(round(params.sta_s / dt)))
    lta_n = max(2, int(round(params.lta_s / dt)))
    if lta_n >= n:
        return []

    char = v * v
    cum = np.concatenate(([0.0], np.cumsum(char)))

    def _win_mean(win_n: int):
        s = cum[win_n:] - cum[:-win_n]
        out = np.full(v.shape, np.nan)
        out[win_n - 1:] = s / win_n
        return out

    sta = _win_mean(sta_n)
    lta = _win_mean(lta_n)
    ratio = np.zeros(v.shape, dtype=float)
    valid = lta > 0
    ratio[valid] = np.nan_to_num(sta[valid]) / lta[valid]

    raw: list[list[int]] = []
    active = False
    start = 0
    for i in range(n):
        r = ratio[i]
        if not active and r >= params.on:
            active = True
            start = i
        elif active and r <= params.off:
            active = False
            raw.append([start, i])
    if active:
        raw.append([start, n - 1])

    if not raw:
        return []
    gap = int(round(params.merge_gap_s / dt))
    merged = [list(raw[0])]
    for s, e in raw[1:]:
        if s - merged[-1][1] <= gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])

    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    floor = med + params.mad_k * mad * 1.4826
    kept: list[tuple[int, int]] = []
    for i0, i1 in merged:
        if float(v[i0:i1 + 1].max()) >= floor:
            kept.append((i0, i1))
    return kept


@register
class StaLtaAlgorithm(WaveformAlgorithm):
    name = "stalta"
    kind = "event"
    params_cls = StaLtaParams

    def run(self, signal: Signal, params: StaLtaParams | None = None) -> EventResult:
        params = params or StaLtaParams()
        ranges = detect_ranges_stalta(signal.times, signal.values, params)
        times = signal.times
        values = signal.values
        events: list[Event] = []
        for i0, i1 in ranges:
            seg = values[i0:i1 + 1]
            if not seg:
                continue
            seg_min = min(seg)
            seg_max = max(seg)
            seg_avg = sum(seg) / len(seg)
            peak = seg_max if abs(seg_max) >= abs(seg_min) else seg_min
            events.append(
                Event(
                    start=times[i0],
                    end=times[i1],
                    type="spike" if peak >= seg_avg else "dip",
                    trigger="stalta",
                    avg=seg_avg,
                    peak=peak,
                    minimum=seg_min,
                    duration_ms=(times[i1] - times[i0]) * 1e3,
                    i0=i0,
                    i1=i1,
                )
            )
        info = {"algorithm": self.name, "raw_events": len(ranges)}
        return EventResult(events=events, info=info)
