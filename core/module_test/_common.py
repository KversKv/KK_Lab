"""Module Test items 共用工具：CSV 落盘、Mock 数据生成、通道解析。

纯函数，禁依赖 Qt；供 items/* 与 runner 复用。
"""
from __future__ import annotations

import csv
import os
import random
from dataclasses import dataclass
from typing import Any, Callable

from log_config import get_logger

logger = get_logger(__name__)


@dataclass
class ItemContext:
    """单测试项执行上下文（由 runner 构造后传入 item.run）。"""

    n6705c: Any                      # N6705C 实例或 MockN6705C
    scope: Any | None                # 示波器实例或 None
    chamber: Any | None              # 温箱实例或 None
    config: dict                     # 参数 + 通道映射
    out_dir: str                     # 本次结果落盘目录
    is_mock: bool                    # 是否 Mock 模式
    stop_flag_fn: Callable[[], bool]  # 协作式中断检查
    log_fn: Callable[[str], None]    # 日志回调（已切回 UI 线程）
    progress_fn: Callable[[int, str], None]  # 进度回调 (percent, label)


def parse_channel(value: Any) -> int:
    """把 'CH 1' / 'CH1' / 1 统一解析为整数通道号。"""
    if isinstance(value, int):
        return value
    s = str(value).strip().upper().replace("CH", "").strip()
    return int(s)


def write_csv(path: str, header: list[str], rows: list[list[Any]]) -> None:
    """写 CSV（utf-8-sig，Excel 友好）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)


def safe_measure(n6705c: Any, method: str, channel: int, default: float = 0.0) -> float:
    """防御性测量封装：异常返回 default 并记日志，禁裸 except 传播。"""
    try:
        fn = getattr(n6705c, method)
        val = fn(channel)
        return float(val) if val is not None else default
    except Exception:  # noqa: BLE001 - 测量异常降级为默认值，保证流程不中断
        logger.error("measure %s ch%d failed", method, channel, exc_info=True)
        return default


def mock_jitter(base: float, ratio: float = 0.02) -> float:
    """给 Mock 测量值叠加小幅抖动（ratio=2%）。"""
    return base * (1.0 + random.uniform(-ratio, ratio))


def linspace(start: float, end: float, step: float) -> list[float]:
    """等步进序列（含 end，step>0）。"""
    if step <= 0 or end < start:
        return [start]
    pts = []
    v = start
    while v <= end + 1e-9:
        pts.append(round(v, 6))
        v += step
    return pts
