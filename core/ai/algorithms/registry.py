"""波形算法注册表——按名字取算法，便于互换 / 调试 / 平滑新增。

新增算法只需 @register 一个 WaveformAlgorithm 子类，调用方用 get("名字") 取实例，
或 available(kind="event") 列出同类算法做参数对照实验。纯数据，禁 import Qt。
"""
from __future__ import annotations

from core.ai.algorithms.base import WaveformAlgorithm

_REGISTRY: dict[str, WaveformAlgorithm] = {}


def register(algo_cls: type[WaveformAlgorithm]) -> type[WaveformAlgorithm]:
    """装饰器：实例化并按 name 注册算法。"""
    instance = algo_cls()
    if not instance.name:
        raise ValueError(f"{algo_cls.__name__} 缺少 name")
    _REGISTRY[instance.name] = instance
    return algo_cls


def get(name: str) -> WaveformAlgorithm:
    """按名字取算法实例；未注册抛 KeyError。"""
    if name not in _REGISTRY:
        raise KeyError(f"未注册的波形算法: {name!r}（已注册: {list(_REGISTRY)}）")
    return _REGISTRY[name]


def available(kind: str | None = None) -> list[str]:
    """列出已注册算法名；kind 过滤同类（event/segment/downsample）。"""
    if kind is None:
        return sorted(_REGISTRY)
    return sorted(n for n, a in _REGISTRY.items() if a.kind == kind)
