"""波形算法包——归一化输入输出，便于互换 / 调试 / 平滑新增。

统一契约（base）：
    Signal              归一化输入（times/values/dt）。
    Event / Segment     归一化输出单元（to_dict(factor) 出 JSON）。
    EventResult / SegmentResult   事件检测 / 变点分段统一返回。
    WaveformAlgorithm   算法抽象基类（name/kind/params_cls + run()）。

注册表（registry）：get("名字") 取算法，available(kind) 列同类做参数对照。
导入本包即触发各算法 @register（swed/stalta/pelt）。

已注册算法：
    swed   （event）   Sliding-Window Event Detection（睡眠门限 + 相对回落）。
    stalta （event）   STA-LTA 能量比 + MAD 闸门（迁移自 waveform_provider）。
    pelt   （segment） PELT 均值变点 + 段形态分类（迁移自 waveform_provider）。

降采样（downsample）：LTTB / adaptive_downsample（函数式，非算法对象）。
"""
from __future__ import annotations

from core.ai.algorithms.base import (
    Event,
    EventResult,
    Segment,
    SegmentResult,
    Signal,
    WaveformAlgorithm,
    statistics,
    trapezoid,
)
from core.ai.algorithms.downsample import adaptive_downsample, lttb_downsample
from core.ai.algorithms.pelt import (
    PeltAlgorithm,
    PeltParams,
    classify_segment,
    detect_change_points,
    segment_features,
)
from core.ai.algorithms.registry import available, get, register
from core.ai.algorithms.stalta import (
    StaLtaAlgorithm,
    StaLtaParams,
    detect_ranges_stalta,
)
from core.ai.algorithms.swed import SwedAlgorithm, SwedParams

__all__ = [
    "Signal",
    "Event",
    "Segment",
    "EventResult",
    "SegmentResult",
    "WaveformAlgorithm",
    "statistics",
    "trapezoid",
    "register",
    "get",
    "available",
    "SwedAlgorithm",
    "SwedParams",
    "StaLtaAlgorithm",
    "StaLtaParams",
    "detect_ranges_stalta",
    "PeltAlgorithm",
    "PeltParams",
    "detect_change_points",
    "classify_segment",
    "segment_features",
    "lttb_downsample",
    "adaptive_downsample",
]
