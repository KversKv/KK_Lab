"""Module Test items 共用工具：CSV 落盘、Mock 数据生成、通道解析。

纯函数，禁依赖 Qt；供 items/* 与 runner 复用。
"""
from __future__ import annotations

import csv
import os
import random
import time
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


def settle(ctx: "ItemContext", seconds: float) -> None:
    """稳定等待（Mock 模式跳过；真机 time.sleep，禁 QThread 依赖）。

    真机测量前需等待电源/负载建立稳态，参考 PMU DCDC worker 的 settle 逻辑。
    """
    if ctx.is_mock or seconds <= 0:
        return
    time.sleep(seconds)


def trimmed_mean(samples: list[float]) -> float:
    """去极值均值：样本 >=3 时剔除最大最小各一，参考 PMU baseline 逻辑。"""
    if not samples:
        return 0.0
    if len(samples) < 3:
        return sum(samples) / len(samples)
    s = sorted(samples)[1:-1]
    return sum(s) / len(s)


def measure_avg(ctx: "ItemContext", method: str, channel: int, *,
                count: int = 1, settle_s: float = 0.0, default: float = 0.0) -> float:
    """多次采样去极值均值（参考 PMU average_cnt + settle）。

    Args:
        method: 'measure_voltage' / 'measure_current'。
        count: 采样次数（<=1 时单次）。
        settle_s: 每次采样间稳定等待秒数（Mock 跳过）。
    """
    n = max(1, int(count))
    samples: list[float] = []
    for i in range(n):
        samples.append(safe_measure(ctx.n6705c, method, channel, default))
        if i < n - 1:
            settle(ctx, settle_s)
    return trimmed_mean(samples)


def setup_source_channel(ctx: "ItemContext", channel: int, voltage: float, *,
                         current_limit: float | None = None) -> None:
    """把通道配成电压源（PS2Q）并上电，参考 PMU DCDC worker。

    真机执行；Mock 下相关调用被安全忽略（各方法为 no-op）。
    """
    try:
        ctx.n6705c.set_mode(channel, "PS2Q")
        ctx.n6705c.set_channel_range(channel)
        if current_limit is not None:
            ctx.n6705c.set_current_limit(channel, current_limit)
        ctx.n6705c.set_voltage(channel, voltage)
        ctx.n6705c.channel_on(channel)
    except Exception:  # noqa: BLE001 - 配置失败降级记录，保证流程不中断
        logger.error("setup source ch%d failed", channel, exc_info=True)


def setup_meter_channel(ctx: "ItemContext", channel: int) -> None:
    """把通道配成电压表（VMETer），参考 PMU DCDC worker。"""
    try:
        ctx.n6705c.set_mode(channel, "VMETer")
        ctx.n6705c.set_channel_range(channel)
    except Exception:  # noqa: BLE001
        logger.error("setup meter ch%d failed", channel, exc_info=True)


def setup_load_channel(ctx: "ItemContext", channel: int) -> None:
    """把通道配成电子负载（CCLoad）并上电，参考 PMU DCDC worker。"""
    try:
        ctx.n6705c.set_mode(channel, "CCLoad")
        ctx.n6705c.set_channel_range(channel)
        ctx.n6705c.channel_on(channel)
    except Exception:  # noqa: BLE001
        logger.error("setup load ch%d failed", channel, exc_info=True)


def set_load_current(ctx: "ItemContext", channel: int, current_a: float) -> None:
    """设置电子负载电流（CCLoad 用负电流拉载，参考 PMU DCDC worker）。"""
    try:
        ctx.n6705c.set_current(channel, -abs(current_a))
    except Exception:  # noqa: BLE001
        logger.error("set load current ch%d failed", channel, exc_info=True)


def teardown_load(ctx: "ItemContext", channel: int) -> None:
    """收尾：负载归零并关断（参考 PMU DCDC worker finally 块）。"""
    try:
        ctx.n6705c.set_current(channel, 0)
        ctx.n6705c.channel_off(channel)
    except Exception:  # noqa: BLE001
        logger.error("teardown load ch%d failed", channel, exc_info=True)
