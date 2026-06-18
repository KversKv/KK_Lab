"""波形摘要 Provider（F1）：把海量原始波形点压成可喂 AI 的三层结构。

设计（AI_Assist_NewFeature_V1 §1）：
  第 1 层 统计摘要：均值/最值/峰峰/标准差 + 采样率/点数 + 异常点 + 稳态段；
  第 2 层 LTTB 降采样：把数百万点降到 ~1500 点，保留视觉峰谷；
  第 3 层 按需放大：slice_window() 按时间窗切高分辨率片段。

原始点永远留在调用方内存，本模块只产出摘要/降采样/切片。
纯算法，禁 import Qt（遵守 instruments/core 分层铁律，可在 worker 中安全使用）。

输入 all_data 结构（与 n6705c_datalog_process 一致）：
    {label: {"time": [float, ...], "values": [float, ...]}}
"""
from __future__ import annotations

import math

from core.ai.schemas import WaveformDigest, WaveformStat
from log_config import get_logger

logger = get_logger(__name__)


_BASE_UNIT_BY_TOKEN = {"I": "A", "V": "V", "P": "W"}

_UNIT_PREFIXES = (
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "u"),
    (1e-9, "n"),
)


def _infer_base_unit(label: str) -> str:
    """从通道标签尾部推断基本单位（CH1 I -> A，CH1 V -> V，CH1 P -> W）。"""
    token = (label or "").strip().rsplit(" ", 1)[-1].upper()
    return _BASE_UNIT_BY_TOKEN.get(token, "")


def _pick_scale(values: list[float], base_unit: str) -> tuple[float, str]:
    """按通道整体量级选档，返回 (倍率, 单位字符串)。

    Datalog 内存值统一为「真实值 × 1000」（电流 mA / 电压 mV / 功率 mW）。
    先把代表幅值（最大绝对值）还原为基本单位下的真实值，再按 SI 前缀选档，
    使整条通道的所有标量共用同一量纲（避免 avg 用 mA、max 用 A 的混乱）。
    无法识别单位（如时间轴）时不换算。
    """
    if not base_unit:
        return 1.0, ""
    peak_real = max((abs(v) for v in values), default=0.0) / 1000.0
    threshold, prefix = _UNIT_PREFIXES[1]
    if peak_real > 0.0:
        for thr, pfx in _UNIT_PREFIXES:
            if peak_real >= thr:
                threshold, prefix = thr, pfx
                break
        else:
            threshold, prefix = _UNIT_PREFIXES[-1]
    factor = 1.0 / (1000.0 * threshold)
    return factor, f"{prefix}{base_unit}"


def lttb_downsample(
    times: list[float], values: list[float], threshold: int
) -> tuple[list[float], list[float]]:
    """Largest-Triangle-Three-Buckets 降采样。

    把 (times, values) 降到约 threshold 个点，保留视觉峰谷。
    threshold >= 数据点数或 < 3 时原样返回。
    """
    n = len(values)
    if threshold >= n or threshold < 3 or n == 0:
        return list(times), list(values)

    sampled_t: list[float] = [times[0]]
    sampled_v: list[float] = [values[0]]

    bucket_size = (n - 2) / (threshold - 2)
    a = 0  # 上一个被选中的点索引

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


def _statistics(values: list[float]) -> tuple[float, float, float, float]:
    """返回 (minimum, maximum, average, std)。"""
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    vmin = min(values)
    vmax = max(values)
    avg = sum(values) / n
    var = sum((v - avg) ** 2 for v in values) / n
    return vmin, vmax, avg, math.sqrt(var)


def _detect_anomalies(
    times: list[float],
    values: list[float],
    average: float,
    std: float,
    sigma: float,
    max_report: int = 20,
) -> list[dict]:
    """阈值穿越（|v - mean| > sigma*std）异常点列表，限量上报。"""
    if std <= 0.0:
        return []
    threshold = sigma * std
    anomalies: list[dict] = []
    for t, v in zip(times, values):
        if abs(v - average) > threshold:
            anomalies.append(
                {
                    "t": round(t, 6),
                    "value": round(v, 6),
                    "type": "spike" if v > average else "dip",
                }
            )
            if len(anomalies) >= max_report:
                break
    return anomalies


def _detect_steady_segments(
    times: list[float],
    values: list[float],
    average: float,
    std: float,
    max_report: int = 5,
) -> list[dict]:
    """识别稳态段：连续点局部波动 < 0.5*std 视为稳态，合并相邻区间。"""
    n = len(values)
    if n < 10 or std <= 0.0:
        return []
    band = 0.5 * std
    segments: list[dict] = []
    seg_start = None
    seg_vals: list[float] = []
    for i in range(n):
        is_steady = abs(values[i] - average) < band
        if is_steady:
            if seg_start is None:
                seg_start = i
                seg_vals = []
            seg_vals.append(values[i])
        else:
            if seg_start is not None and (i - seg_start) >= max(10, n // 50):
                seg_avg = sum(seg_vals) / len(seg_vals)
                _, _, _, seg_std = _statistics(seg_vals)
                segments.append(
                    {
                        "start": round(times[seg_start], 6),
                        "end": round(times[i - 1], 6),
                        "avg": round(seg_avg, 6),
                        "std": round(seg_std, 6),
                    }
                )
            seg_start = None
    if seg_start is not None and (n - seg_start) >= max(10, n // 50):
        seg_avg = sum(seg_vals) / len(seg_vals)
        _, _, _, seg_std = _statistics(seg_vals)
        segments.append(
            {
                "start": round(times[seg_start], 6),
                "end": round(times[-1], 6),
                "avg": round(seg_avg, 6),
                "std": round(seg_std, 6),
            }
        )
    return segments[:max_report]


def _channel_stat(
    label: str, channel: dict, anomaly_sigma: float
) -> WaveformStat | None:
    values = channel.get("values") or []
    times = channel.get("time") or []
    if not values:
        return None
    if len(times) != len(values):
        times = list(range(len(values)))
    vmin, vmax, avg, std = _statistics(values)
    sample_period = 0.0
    if len(times) >= 2:
        sample_period = abs(times[1] - times[0])

    factor, unit = _pick_scale(values, _infer_base_unit(label))

    anomalies = _detect_anomalies(times, values, avg, std, anomaly_sigma)
    steady_segments = _detect_steady_segments(times, values, avg, std)
    if factor != 1.0:
        for a in anomalies:
            a["value"] = round(a["value"] * factor, 6)
        for s in steady_segments:
            s["avg"] = round(s["avg"] * factor, 6)
            s["std"] = round(s["std"] * factor, 6)

    return WaveformStat(
        label=label,
        unit=unit,
        sample_period_s=sample_period,
        point_count=len(values),
        minimum=round(vmin * factor, 6),
        maximum=round(vmax * factor, 6),
        average=round(avg * factor, 6),
        peak_to_peak=round((vmax - vmin) * factor, 6),
        std=round(std * factor, 6),
        anomalies=anomalies,
        steady_segments=steady_segments,
    )


def build_digest(
    all_data: dict,
    *,
    max_points: int = 1500,
    anomaly_sigma: float = 3.0,
    include_downsampled: bool = True,
) -> WaveformDigest:
    """把 all_data 压成 WaveformDigest（统计摘要 + 可选 LTTB 降采样）。"""
    if not all_data:
        return WaveformDigest(note="无波形数据")

    stats: list[WaveformStat] = []
    downsampled: dict[str, dict[str, list[float]]] = {}
    total_points = 0

    for label, channel in all_data.items():
        if not isinstance(channel, dict):
            continue
        stat = _channel_stat(str(label), channel, anomaly_sigma)
        if stat is None:
            continue
        stats.append(stat)
        total_points += stat.point_count

        if include_downsampled:
            times = channel.get("time") or list(range(stat.point_count))
            values = channel.get("values") or []
            ds_t, ds_v = lttb_downsample(list(times), list(values), max_points)
            factor, _ = _pick_scale(values, _infer_base_unit(str(label)))
            downsampled[str(label)] = {
                "time": [round(x, 6) for x in ds_t],
                "values": [round(x * factor, 6) for x in ds_v],
            }

    ds_count = max((len(v["values"]) for v in downsampled.values()), default=0)
    note = (
        f"原始 {total_points} 点（{len(stats)} 通道）"
        + (f"，已 LTTB 降采样至每通道约 {ds_count} 点" if include_downsampled else "")
    )
    return WaveformDigest(stats=stats, downsampled=downsampled, note=note)


def slice_window(
    all_data: dict, label: str, t0: float, t1: float, *, max_points: int = 2500
) -> dict:
    """第 3 层按需放大：截取 [t0, t1] 时间窗的高分辨率片段。

    返回 {"time": [...], "values": [...]}；超过 max_points 仍做 LTTB 压缩。
    """
    channel = (all_data or {}).get(label)
    if not isinstance(channel, dict):
        return {"time": [], "values": []}
    times = channel.get("time") or []
    values = channel.get("values") or []
    lo, hi = (t0, t1) if t0 <= t1 else (t1, t0)
    sel_t: list[float] = []
    sel_v: list[float] = []
    for t, v in zip(times, values):
        if lo <= t <= hi:
            sel_t.append(t)
            sel_v.append(v)
    if len(sel_v) > max_points:
        sel_t, sel_v = lttb_downsample(sel_t, sel_v, max_points)
    return {"time": sel_t, "values": sel_v}
