"""波形算法归一化契约（输入 / 输出 / 算法基类）。

所有波形算法（事件检测 / 变点分段 / 降采样）共用同一套输入输出数据结构，
使算法可互换、可调试、可平滑新增。本模块纯数据 + 抽象基类，禁 import Qt。

归一化设计：
    输入  Signal           ——（times, values, dt）一次封装，避免各算法重复推断 dt。
    参数  *Params          —— 每类算法一个参数 dataclass，默认值即推荐值。
    输出  Event/Segment    —— 统一字段（start/end/peak/...），to_dict() 出 JSON。
          EventResult      —— events + info（算法元信息：窗口宽度/闸门/原始事件数）。
          SegmentResult    —— segments + info。

数据约定（与 waveform_provider 同源）：
    times/values 为同长度序列；values 单位由调用方决定（本项目 Datalog 内存值
    = 真实值×1000，即电流 mA / 电压 mV / 功率 mW）。算法内部不做单位换算，
    展示量纲换算交由调用方（_pick_scale / factor）。
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

try:
    import numpy as np

    _HAS_NUMPY = True
except ImportError:  # pragma: no cover - numpy 缺失时回退纯 Python
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False


def _median(xs: list[float]) -> float:
    n = len(xs)
    if n == 0:
        return 0.0
    s = sorted(xs)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) * 0.5


def infer_dt(times: list[float], sample_cap: int = 1000) -> float:
    """推断采样周期 dt（取前 sample_cap 点相邻差分的中位数，抗抖动）。"""
    n = len(times)
    if n < 2:
        return 0.0
    cap = min(n, sample_cap)
    if _HAS_NUMPY:
        return float(np.median(np.diff(np.asarray(times[:cap], dtype=float))))
    diffs = [times[i + 1] - times[i] for i in range(cap - 1)]
    return _median(diffs)


@dataclass
class Signal:
    """归一化输入：一段波形（times/values 同长度），dt 自动推断一次。"""

    times: list[float]
    values: list[float]
    dt: float = 0.0

    def __post_init__(self) -> None:
        if len(self.times) != len(self.values):
            self.times = list(range(len(self.values)))
        if self.dt <= 0.0:
            self.dt = infer_dt(self.times)

    @property
    def n(self) -> int:
        return len(self.values)

    @classmethod
    def from_channel(cls, channel: dict) -> "Signal":
        """从 all_data 单通道结构 {"time":[...], "values":[...]} 构造。"""
        values = list(channel.get("values") or [])
        times = list(channel.get("time") or [])
        return cls(times=times, values=values)


@dataclass
class Event:
    """归一化事件输出（尖峰 / 电平台阶 / 低谷）。

    start/end 为时间（秒）；peak/minimum 为窗口内极值；avg 为事件均值；
    type ∈ {spike, dip, level}；trigger 标注触发判据（算法相关，可空）。
    """

    start: float = 0.0
    end: float = 0.0
    type: str = "spike"
    trigger: str = ""
    avg: float = 0.0
    peak: float = 0.0
    minimum: float = 0.0
    duration_ms: float = 0.0
    i0: int = -1
    i1: int = -1
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, factor: float = 1.0, ndigits: int = 6) -> dict[str, Any]:
        """出 JSON；factor 把内存值换算为展示量纲（peak/avg/minimum 三个幅值）。"""
        d = {
            "start": round(self.start, ndigits),
            "end": round(self.end, ndigits),
            "type": self.type,
            "avg": round(self.avg * factor, ndigits),
            "peak": round(self.peak * factor, ndigits),
            "minimum": round(self.minimum * factor, ndigits),
            "duration_ms": round(self.duration_ms, 4),
        }
        if self.trigger:
            d["trigger"] = self.trigger
        if self.extra:
            d.update(self.extra)
        return d


@dataclass
class Segment:
    """归一化分段输出（PELT 变点切分后每段的形态特征）。"""

    start: float = 0.0
    end: float = 0.0
    label: str = "ramp"
    mean: float = 0.0
    peak: float = 0.0
    peak_to_mean: float = 0.0
    width_ms: float = 0.0
    rise: float = 0.0
    charge_uAh: float = 0.0
    point_count: int = 0

    def to_dict(self, *, factor: float = 1.0, ndigits: int = 6) -> dict[str, Any]:
        return {
            "start": round(self.start, ndigits),
            "end": round(self.end, ndigits),
            "label": self.label,
            "mean": round(self.mean * factor, ndigits),
            "peak": round(self.peak * factor, ndigits),
            "peak_to_mean": round(self.peak_to_mean, 3),
            "width_ms": round(self.width_ms, 4),
            "rise": round(self.rise * factor, ndigits),
            "charge_uAh": round(self.charge_uAh, ndigits),
            "point_count": self.point_count,
        }


@dataclass
class EventResult:
    """事件检测统一返回：归一化事件列表 + 算法元信息。"""

    events: list[Event] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def to_index_ranges(self) -> list[tuple[int, int]]:
        """转成 [(i0, i1), ...] 索引区间（供 segment_features / 降采样消费）。"""
        return [
            (e.i0, e.i1)
            for e in self.events
            if e.i0 >= 0 and e.i1 >= e.i0
        ]

    def to_dict(self, *, factor: float = 1.0) -> dict[str, Any]:
        return {
            "events": [e.to_dict(factor=factor) for e in self.events],
            "info": dict(self.info),
        }


@dataclass
class SegmentResult:
    """变点分段统一返回：归一化段列表 + 算法元信息。"""

    segments: list[Segment] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, *, factor: float = 1.0) -> dict[str, Any]:
        return {
            "segments": [s.to_dict(factor=factor) for s in self.segments],
            "info": dict(self.info),
        }


class WaveformAlgorithm(ABC):
    """波形算法抽象基类——所有算法的统一调用面。

    子类声明 name / kind / Params dataclass，并实现 run()。
    kind ∈ {"event", "segment", "downsample"}，用于注册表分类与调试筛选。
    """

    name: str = ""
    kind: str = "event"
    params_cls: type | None = None

    @abstractmethod
    def run(self, signal: Signal, params: Any = None) -> Any:
        """对 signal 执行算法，返回 EventResult / SegmentResult / 降采样元组。"""
        raise NotImplementedError

    def make_params(self, **overrides: Any) -> Any:
        """构造默认参数并按 overrides 覆盖（便于调试单参扫描）。"""
        if self.params_cls is None:
            return None
        return self.params_cls(**overrides)


def trapezoid(seg_values: Any, dx: float) -> float:
    """梯形积分，兼容新旧 numpy（trapezoid/trapz）；无 numpy 走纯 Python。"""
    if _HAS_NUMPY and not isinstance(seg_values, list):
        integ = getattr(np, "trapezoid", None) or getattr(np, "trapz")
        return float(integ(seg_values, dx=dx))
    vals = list(seg_values)
    n = len(vals)
    if n < 2:
        return 0.0
    total = 0.0
    for i in range(n - 1):
        total += (vals[i] + vals[i + 1]) * 0.5 * dx
    return total


def statistics(values: list[float]) -> tuple[float, float, float, float]:
    """返回 (minimum, maximum, average, std)。"""
    n = len(values)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    vmin = min(values)
    vmax = max(values)
    avg = sum(values) / n
    var = sum((v - avg) ** 2 for v in values) / n
    return vmin, vmax, avg, math.sqrt(var)
