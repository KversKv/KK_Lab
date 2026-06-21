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

import bisect
import math

from core.ai.algorithms import (
    Signal,
    adaptive_downsample,
    detect_change_points,
    detect_ranges_stalta,
    get as get_algorithm,
    lttb_downsample,
    segment_features as _segment_features_obj,
)
from core.ai.schemas import WaveformDigest, WaveformStat
from instruments.power.keysight.n6705c_datalog_process import base_unit_for_label
from log_config import get_logger

logger = get_logger(__name__)


_UNIT_PREFIXES = (
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "u"),
    (1e-9, "n"),
)


def _infer_base_unit(label: str) -> str:
    """推断通道基本单位（电流 -> A，电压 -> V，功率 -> W）。

    委托 n6705c_datalog_process.base_unit_for_label，兼容 "CH1 I" 与
    "F1-A-I1" 两种命名（与 Datalog Viewer 单位语义同源）。
    """
    return base_unit_for_label(label)


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


def _cluster_spike_events(
    times: list[float],
    values: list[float],
    average: float,
    std: float,
    sigma: float,
    gap_s: float,
    max_report: int = 20,
) -> tuple[list[dict], int]:
    """把超阈采样点按时间邻近聚成尖峰事件簇。

    返回 (事件簇列表, 超阈采样点总数)。相邻超阈点时间间隔 <= gap_s 视为同一
    事件；每簇取簇内绝对偏离最大的点为峰值。用于避免把"一簇内多个采样点"
    误读成多个独立脉冲。
    """
    if std <= 0.0:
        return [], 0
    threshold = sigma * std
    over: list[tuple[float, float]] = [
        (t, v) for t, v in zip(times, values) if abs(v - average) > threshold
    ]
    total_over = len(over)
    if not over:
        return [], 0

    if gap_s <= 0.0:
        gap_s = 0.0

    events: list[dict] = []
    cluster: list[tuple[float, float]] = [over[0]]
    for t, v in over[1:]:
        if t - cluster[-1][0] <= gap_s:
            cluster.append((t, v))
        else:
            events.append(_build_event(cluster, average))
            cluster = [(t, v)]
    events.append(_build_event(cluster, average))
    return events[:max_report], total_over


def _build_event(cluster: list[tuple[float, float]], average: float) -> dict:
    peak_t, peak_v = max(cluster, key=lambda tv: abs(tv[1] - average))
    return {
        "start": round(cluster[0][0], 6),
        "end": round(cluster[-1][0], 6),
        "peak_t": round(peak_t, 6),
        "peak_value": round(peak_v, 6),
        "point_count": len(cluster),
        "type": "spike" if peak_v > average else "dip",
    }


def detect_events_stalta(
    times: list[float],
    values: list[float],
    *,
    sta_s: float = 1e-4,
    lta_s: float = 5e-3,
    on: float = 4.0,
    off: float = 1.5,
    merge_gap_s: float = 2e-4,
    mad_k: float = 6.0,
) -> list[tuple[int, int]]:
    """C1：STA-LTA 事件检测（薄适配，算法已迁移至 core.ai.algorithms.stalta）。

    返回事件索引区间列表 [(i0, i1), ...]，行为与原实现一致。
    """
    algo = get_algorithm("stalta")
    params = algo.make_params(
        sta_s=sta_s, lta_s=lta_s, on=on, off=off,
        merge_gap_s=merge_gap_s, mad_k=mad_k,
    )
    return detect_ranges_stalta(times, values, params)


def detect_event_ranges(
    times: list[float],
    values: list[float],
    *,
    algo: str = "stalta",
    algo_params: dict | None = None,
) -> list[tuple[int, int]]:
    """按注册名取事件检测算法，返回索引区间 [(i0, i1), ...]（可切换入口）。

    algo：注册表中 kind=="event" 的算法名（如 "stalta" / "swed"）；
    algo_params：覆盖该算法默认参数的字段字典（仅取合法字段）。
    取算法失败或非事件类时回退 STA-LTA，保证调用方不中断。
    """
    try:
        instance = get_algorithm(algo)
    except KeyError:
        logger.warning("未知波形事件算法 %r，回退 stalta", algo)
        instance = get_algorithm("stalta")
    if getattr(instance, "kind", "event") != "event":
        logger.warning("算法 %r 非事件类，回退 stalta", algo)
        instance = get_algorithm("stalta")
    overrides = _sanitize_algo_params(instance, algo_params)
    params = instance.make_params(**overrides)
    result = instance.run(Signal(times=list(times), values=list(values)), params)
    return result.to_index_ranges()


def _sanitize_algo_params(instance, algo_params: dict | None) -> dict:
    """只保留 params_cls 中存在的字段，过滤掉历史/非法键。"""
    if not algo_params:
        return {}
    params_cls = getattr(instance, "params_cls", None)
    if params_cls is None:
        return {}
    import dataclasses

    valid = {f.name for f in dataclasses.fields(params_cls)}
    return {k: v for k, v in algo_params.items() if k in valid}


def detect_segments_pelt(
    values: list[float],
    *,
    pen: float = 6.0,
    min_size: int = 3,
    max_n: int = 4000,
    auto_scale: bool = True,
) -> list[int]:
    """C10：PELT 变点检测（薄适配，算法已迁移至 core.ai.algorithms.pelt）。

    返回变点索引列表（不含 0 与 N），行为与原实现一致。
    """
    return detect_change_points(
        values, pen=pen, min_size=min_size, max_n=max_n, auto_scale=auto_scale,
    )


def segment_features(
    times: list[float],
    values: list[float],
    segments: list[tuple[int, int]],
    *,
    factor: float = 1.0,
    baseline: float | None = None,
    std: float = 0.0,
    max_report: int = 30,
) -> list[dict]:
    """C3：段特征（薄适配，算法已迁移至 core.ai.algorithms.pelt.segment_features）。

    内部用归一化 Segment 计算，再按 factor 换算量纲输出旧版 dict（行为不变）。
    """
    segs = _segment_features_obj(
        times, values, segments, baseline=baseline, std=std,
        max_report=max_report,
    )
    return [s.to_dict(factor=factor) for s in segs]


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
    label: str,
    channel: dict,
    anomaly_sigma: float,
    *,
    event_aware: bool = False,
    algo: str = "stalta",
    algo_params: dict | None = None,
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
    gap_s = max(sample_period * 5.0, 5e-4) if sample_period > 0 else 5e-4
    spike_events, over_count = _cluster_spike_events(
        times, values, avg, std, anomaly_sigma, gap_s
    )
    steady_segments = _detect_steady_segments(times, values, avg, std)
    if factor != 1.0:
        for a in anomalies:
            a["value"] = round(a["value"] * factor, 6)
        for e in spike_events:
            e["peak_value"] = round(e["peak_value"] * factor, 6)
        for s in steady_segments:
            s["avg"] = round(s["avg"] * factor, 6)
            s["std"] = round(s["std"] * factor, 6)
    for e in spike_events:
        e["over_threshold_total"] = over_count

    segments: list[dict] = []
    if event_aware:
        events = detect_event_ranges(
            times, values, algo=algo, algo_params=algo_params
        )
        segments = segment_features(
            times, values, events, factor=factor, baseline=avg, std=std
        )

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
        spike_events=spike_events,
        steady_segments=steady_segments,
        segments=segments,
    )


def build_digest(
    all_data: dict,
    *,
    max_points: int = 1500,
    anomaly_sigma: float = 3.0,
    include_downsampled: bool = True,
    event_aware: bool = False,
    algo: str = "stalta",
    algo_params: dict | None = None,
) -> WaveformDigest:
    """把 all_data 压成 WaveformDigest（统计摘要 + 可选 LTTB 降采样）。

    event_aware=False（默认）：行为与改造前完全一致（LTTB 降采样 + σ·std 尖峰聚簇）。
    event_aware=True：额外走 STA-LTA+MAD 事件检测 → 段落特征化（segments）+ 事件感知
    非均匀降采样（density_map 标注密度，平稳段 min-max 稀疏、事件段高密度保留）。
    """
    if not all_data:
        return WaveformDigest(note="无波形数据")

    stats: list[WaveformStat] = []
    downsampled: dict[str, dict[str, list[float]]] = {}
    total_points = 0

    for label, channel in all_data.items():
        if not isinstance(channel, dict):
            continue
        stat = _channel_stat(
            str(label),
            channel,
            anomaly_sigma,
            event_aware=event_aware,
            algo=algo,
            algo_params=algo_params,
        )
        if stat is None:
            continue
        stats.append(stat)
        total_points += stat.point_count

        if include_downsampled:
            times = channel.get("time") or list(range(stat.point_count))
            values = channel.get("values") or []
            factor, _ = _pick_scale(values, _infer_base_unit(str(label)))
            if event_aware:
                events = detect_event_ranges(
                    list(times), list(values), algo=algo, algo_params=algo_params
                )
                ds_t, ds_v, density = adaptive_downsample(
                    list(times), list(values), events, base_points=max_points
                )
                stat.density_map = density
            else:
                ds_t, ds_v = lttb_downsample(
                    list(times), list(values), max_points
                )
            downsampled[str(label)] = {
                "time": [round(x, 6) for x in ds_t],
                "values": [round(x * factor, 6) for x in ds_v],
            }

    ds_count = max((len(v["values"]) for v in downsampled.values()), default=0)
    ds_note = ""
    if include_downsampled:
        if event_aware:
            ds_note = (
                f"，已事件感知非均匀降采样至每通道约 {ds_count} 点"
                "（平稳段 min-max 稀疏 + 事件段高密度，时间轴非均匀，见 density_map）"
            )
        else:
            ds_note = f"，已 LTTB 降采样至每通道约 {ds_count} 点"
    note = f"原始 {total_points} 点（{len(stats)} 通道）" + ds_note
    return WaveformDigest(stats=stats, downsampled=downsampled, note=note)


def _locate_index_bounds(times: list[float], lo: float, hi: float) -> tuple[int, int]:
    """定位 [lo, hi] 对应的索引闭区间 [i0, i1]，避免 O(n) 全遍历。

    times 必须递增。等步长时走算术 O(1) 定位，否则走 bisect O(log n)。
    返回 (i0, i1)；窗口外或空数据返回 (0, -1)（表示空选区）。
    """
    n = len(times)
    if n == 0:
        return 0, -1
    t_first = times[0]
    t_last = times[-1]
    if hi < t_first or lo > t_last:
        return 0, -1

    period = 0.0
    if n >= 2:
        period = times[1] - times[0]
    is_uniform = period > 0.0 and n >= 2 and (
        abs((t_last - t_first) - period * (n - 1)) <= abs(period) * 1e-6
    )

    if is_uniform:
        i0 = int(math.ceil((lo - t_first) / period))
        i1 = int(math.floor((hi - t_first) / period))
    else:
        i0 = bisect.bisect_left(times, lo)
        i1 = bisect.bisect_right(times, hi) - 1

    i0 = max(0, i0)
    i1 = min(n - 1, i1)
    return i0, i1


def slice_channel_fast(
    times: list[float], values: list[float], x0: float, x1: float
) -> tuple[list[float], list[float]]:
    """按 [x0, x1] 时间窗快速切片（不重新采数）。

    等步长走算术 O(1) 定位，非等步长走 bisect O(log n)，禁 O(n) 全遍历。
    """
    if not times or not values:
        return [], []
    lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
    i0, i1 = _locate_index_bounds(times, lo, hi)
    if i1 < i0:
        return [], []
    return times[i0 : i1 + 1], values[i0 : i1 + 1]


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
    sel_t, sel_v = slice_channel_fast(list(times), list(values), t0, t1)
    if len(sel_v) > max_points:
        sel_t, sel_v = lttb_downsample(sel_t, sel_v, max_points)
    return {"time": sel_t, "values": sel_v}


def analyze_window_segments(
    all_data: dict,
    label: str,
    t0: float,
    t1: float,
    *,
    pen: float = 6.0,
    max_n: int = 4000,
) -> dict:
    """C12 drill-down：对一个已识别"尖峰事件"窗口用 PELT 重扫，暴露窗内子结构。

    当 AI 对某尖峰窗口请求放大时，窗内可能含 RX 平台串等中幅子结构——STA-LTA 对其
    结构性失明，必须改用 PELT 均值变点切分 + 段形态分类（§9.8 双引擎铁证）。
    返回 {"label","t0","t1","segments":[...]}；segments 每段含 label/mean/peak/...
    """
    channel = (all_data or {}).get(label)
    if not isinstance(channel, dict):
        return {"label": label, "t0": t0, "t1": t1, "segments": []}
    times = channel.get("time") or []
    values = channel.get("values") or []
    sel_t, sel_v = slice_channel_fast(list(times), list(values), t0, t1)
    if not sel_v:
        return {"label": label, "t0": t0, "t1": t1, "segments": []}
    if len(sel_v) > max_n:
        sel_t, sel_v = lttb_downsample(sel_t, sel_v, max_n)
    factor, _ = _pick_scale(values, _infer_base_unit(str(label)))
    _, _, avg, std = _statistics(sel_v)
    cps = detect_segments_pelt(sel_v, pen=pen, max_n=max_n)
    bounds = [0] + cps + [len(sel_v)]
    seg_ranges = [
        (bounds[i], bounds[i + 1] - 1) for i in range(len(bounds) - 1)
    ]
    segments = segment_features(
        sel_t, sel_v, seg_ranges, factor=factor, baseline=avg, std=std,
        max_report=40,
    )
    return {
        "label": label,
        "t0": t0,
        "t1": t1,
        "engine": "pelt",
        "segments": segments,
    }


def build_window_digest(
    all_data: dict,
    x0: float,
    x1: float,
    *,
    max_points: int = 1500,
    anomaly_sigma: float = 3.0,
    include_downsampled: bool = True,
    event_aware: bool = False,
    algo: str = "stalta",
    algo_params: dict | None = None,
) -> WaveformDigest:
    """按可见窗口 [x0, x1] 快速切片后构建摘要（不重新采数）。

    各通道按同一 [x0, x1] 独立切片，复用 build_digest 做统计与 LTTB 降采样。
    digest.window 记录分析范围（full=False）。
    event_aware 透传给 build_digest（C12：窗口级也支持事件感知）。
    """
    if not all_data:
        return WaveformDigest(note="无波形数据", window={"x0": x0, "x1": x1, "full": False})

    lo, hi = (x0, x1) if x0 <= x1 else (x1, x0)
    windowed: dict[str, dict[str, list[float]]] = {}
    for label, channel in all_data.items():
        if not isinstance(channel, dict):
            continue
        times = channel.get("time") or []
        values = channel.get("values") or []
        sel_t, sel_v = slice_channel_fast(list(times), list(values), lo, hi)
        if not sel_v:
            continue
        windowed[str(label)] = {"time": sel_t, "values": sel_v}

    if not windowed:
        return WaveformDigest(
            note=f"窗口 [{round(lo, 6)}, {round(hi, 6)}] s 内无数据",
            window={"x0": round(lo, 6), "x1": round(hi, 6), "full": False},
        )

    digest = build_digest(
        windowed,
        max_points=max_points,
        anomaly_sigma=anomaly_sigma,
        include_downsampled=include_downsampled,
        event_aware=event_aware,
        algo=algo,
        algo_params=algo_params,
    )
    digest.window = {"x0": round(lo, 6), "x1": round(hi, 6), "full": False}
    digest.note = f"分析范围 [{round(lo, 6)}, {round(hi, 6)}] s（屏幕可见区）：" + digest.note
    return digest


def marker_segment_stats(all_data: dict, a: float, b: float) -> dict | None:
    """计算 Marker A→B 区间各通道统计（时长 + 均值/最值/峰峰）。

    走快速切片定位区间，纯标量输出；量纲与 build_digest 的 stats 一致。
    A/B 缺失或区间内无数据时返回 None。
    """
    if not all_data or a is None or b is None:
        return None
    lo, hi = (a, b) if a <= b else (b, a)
    per_channel: list[dict] = []
    for label, channel in all_data.items():
        if not isinstance(channel, dict):
            continue
        times = channel.get("time") or []
        values = channel.get("values") or []
        _, sel_v = slice_channel_fast(list(times), list(values), lo, hi)
        if not sel_v:
            continue
        vmin, vmax, avg, _ = _statistics(sel_v)
        factor, unit = _pick_scale(sel_v, _infer_base_unit(str(label)))
        per_channel.append(
            {
                "label": str(label),
                "unit": unit,
                "point_count": len(sel_v),
                "minimum": round(vmin * factor, 6),
                "maximum": round(vmax * factor, 6),
                "average": round(avg * factor, 6),
                "peak_to_peak": round((vmax - vmin) * factor, 6),
            }
        )
    if not per_channel:
        return None
    return {
        "a": round(lo, 6),
        "b": round(hi, 6),
        "duration_s": round(abs(hi - lo), 6),
        "per_channel": per_channel,
    }
