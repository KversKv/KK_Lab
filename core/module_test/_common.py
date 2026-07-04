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


def create_i2c(ctx: "ItemContext"):
    """创建 I2C 接口（Mock 模式复用 n6705c 上挂载的 MockI2C，参考 oscp_worker）。"""
    if ctx.is_mock:
        from instruments.mock.mock_instruments import MockI2C
        if getattr(ctx.n6705c, "_mock_i2c", None) is not None:
            return ctx.n6705c._mock_i2c
        i2c = MockI2C()
        if hasattr(ctx.n6705c, "_mock_i2c"):
            ctx.n6705c._mock_i2c = i2c
        return i2c
    from lib.i2c.i2c_interface_x64 import I2CInterface
    return I2CInterface()


def cfg_int(cfg: dict, key: str, default: int) -> int:
    """从 config 取整型（支持十六进制字符串 '0x..' 与十进制字符串/整数）。"""
    val = cfg.get(key, default)
    if isinstance(val, str):
        return int(val, 16) if val.strip().lower().startswith("0x") else int(val, 0)
    return int(val)


def run_vout_scan(ctx: "ItemContext", item_key: str, name: str) -> "ItemResult":
    """各挡位输出电压扫描（LDO / DCDC 共用）。

    严格对齐 ui/pages/pmu_test/pmu_output_voltage.py 的逻辑：
      1. N6705C 通道置 VMETer；
      2. 读默认寄存器，按 [msb:lsb] 位段计算掩码与 data_base；
      3. 写 min_code 后等待输出稳定（最近 3 次电压极差 ≤ 5mV）；
      4. 逐挡（min_code..max_code，步进 1）写寄存器 → 测电压；
      5. 用饱和阈值 0.001V 剔除首尾平台，取有效段算范围/步进/线性度；
      6. 结束恢复寄存器默认值。
    """
    from core.module_test.result_model import ItemResult

    def _skipped(reason: str) -> "ItemResult":
        return ItemResult(item_key=item_key, name=name, passed=None, notes=reason)

    cfg = ctx.config
    device_addr = cfg_int(cfg, "device_addr", 0x00)
    reg_addr = cfg_int(cfg, "reg_addr", 0x00)
    msb = cfg_int(cfg, "msb", 7)
    lsb = cfg_int(cfg, "lsb", 0)
    width_flag = cfg_int(cfg, "width_flag", 1)  # I2CWidthFlag.BIT_10
    min_code = cfg_int(cfg, "min_code", 0)
    max_code = cfg_int(cfg, "max_code", 255)
    vmeter_ch = parse_channel(cfg.get("vout_channel", 1))

    i2c = create_i2c(ctx)
    if ctx.is_mock:
        ctx.log_fn(f"[{item_key}] [DEBUG] Using Mock I2C interface.")

    try:
        ctx.n6705c.set_mode(vmeter_ch, "VMETer")
    except Exception:  # noqa: BLE001 - 配置失败降级记录，保证流程不中断
        logger.error("set VMETer ch%d failed", vmeter_ch, exc_info=True)

    bit_count = msb - lsb + 1
    mask = (1 << bit_count) - 1

    default_reg = i2c.read(device_addr, reg_addr, width_flag)
    data_base = default_reg & (~(mask << lsb))

    max_code = min(max_code, mask)
    min_code = max(min_code, 0)

    total_points = max_code - min_code + 1
    if total_points <= 0:
        ctx.log_fn(f"[{item_key}] [ERROR] Invalid code range (min >= max).")
        return _skipped("无效的 code 范围（min >= max）")

    ctx.log_fn(f"[{item_key}] [TEST] Device=0x{device_addr:02X}, Reg=0x{reg_addr:04X}, "
               f"MSB={msb}, LSB={lsb}, WidthFlag={width_flag}")
    ctx.log_fn(f"[{item_key}] [TEST] Code range: 0x{min_code:X} ~ 0x{max_code:X} "
               f"({total_points} points)")

    hex_width = len(f"{max_code:X}")
    sleep_time = 0.0 if ctx.is_mock else 0.05

    default_voltage = float(ctx.n6705c.measure_voltage(vmeter_ch))
    default_code = (default_reg >> lsb) & mask
    ctx.log_fn(f"[{item_key}] [TEST] Default voltage: {default_voltage:.4f}V (0x{default_code:X})")

    voltages: list[float] = []
    codes: list[int] = []

    settle_start = time.time()
    write_reg = data_base | (min_code << lsb)
    i2c.write(device_addr, reg_addr, write_reg, width_flag)
    ctx.log_fn(f"[{item_key}] [TEST] Setting min_code=0x{min_code:X}, "
               f"waiting for output to stabilize...")

    recent_voltages: list[float] = []
    while True:
        if ctx.stop_flag_fn():
            ctx.log_fn(f"[{item_key}] [TEST] Stopped by user during stabilization.")
            i2c.write(device_addr, reg_addr, default_reg, width_flag)
            return _skipped("稳定阶段被用户停止")
        v = float(ctx.n6705c.measure_voltage(vmeter_ch))
        recent_voltages.append(v)
        if len(recent_voltages) >= 3:
            last3 = recent_voltages[-3:]
            if (max(last3) - min(last3)) <= 0.005:
                break
        time.sleep(sleep_time)

    time.sleep(0.1)
    settle_elapsed_ms = (time.time() - settle_start) * 1000.0
    ctx.log_fn(f"[{item_key}] [TEST] Wait for mincode output cose: {settle_elapsed_ms:.0f}ms")

    rows: list[list[float]] = []
    code = min_code
    while code <= max_code:
        if ctx.stop_flag_fn():
            ctx.log_fn(f"[{item_key}] [TEST] Stopped by user.")
            break

        write_reg = data_base | (code << lsb)
        i2c.write(device_addr, reg_addr, write_reg, width_flag)
        time.sleep(sleep_time)

        measured_v = float(ctx.n6705c.measure_voltage(vmeter_ch))
        voltages.append(measured_v)
        codes.append(code)
        rows.append([code, round(measured_v * 1000.0, 3)])

        ctx.log_fn(f"[{item_key}] [MEAS] Code=0x{code:0{hex_width}X}  "
                   f"Measured={measured_v:>8.4f}V")
        idx = code - min_code
        ctx.progress_fn(int((idx + 1) / total_points * 100), f"Vout scan 0x{code:X}")
        code += 1

    # 饱和阈值剔除首尾平台，取有效段
    sat_threshold = 0.001
    min_voltage = max_voltage = 0.0
    valid_min_code = valid_max_code = 0
    step_voltage_mv = 0.0
    linearity_pct = 0.0
    if len(voltages) >= 2:
        low_valid = 0
        for k in range(1, len(voltages)):
            if abs(voltages[k] - voltages[k - 1]) > sat_threshold:
                low_valid = k
                break
        else:
            low_valid = len(voltages) - 1

        high_valid = len(voltages) - 1
        for k in range(len(voltages) - 1, 0, -1):
            if abs(voltages[k] - voltages[k - 1]) > sat_threshold:
                high_valid = k - 1
                break
        else:
            high_valid = 0

        if high_valid <= low_valid:
            high_valid = len(voltages) - 1
            low_valid = 0

        valid_voltages = voltages[low_valid:high_valid + 1]
        valid_codes = codes[low_valid:high_valid + 1]
        min_voltage = min(valid_voltages)
        max_voltage = max(valid_voltages)
        valid_min_code = valid_codes[0]
        valid_max_code = valid_codes[-1]
        if len(valid_voltages) >= 2:
            step_voltage_mv = (valid_voltages[-1] - valid_voltages[0]) / (len(valid_voltages) - 1) * 1000.0
            full_scale = valid_voltages[-1] - valid_voltages[0]
            if abs(full_scale) > 1e-9:
                n = len(valid_voltages)
                ideal_step = full_scale / (n - 1)
                max_dev = 0.0
                for j in range(n):
                    ideal_v = valid_voltages[0] + ideal_step * j
                    max_dev = max(max_dev, abs(valid_voltages[j] - ideal_v))
                linearity_pct = max_dev / abs(full_scale) * 100.0
        if not ctx.stop_flag_fn():
            ctx.log_fn(f"[{item_key}] [TEST] Valid code range: 0x{valid_min_code:0{hex_width}X} ~ "
                       f"0x{valid_max_code:0{hex_width}X} "
                       f"({valid_max_code - valid_min_code + 1} effective points out of "
                       f"{len(voltages)} total)")

    # 恢复寄存器默认值
    i2c.write(device_addr, reg_addr, default_reg, width_flag)
    ctx.log_fn(f"[{item_key}] [TEST] Register restored to default value.")

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["DAC_code", "Vout (mV)"], rows)
    measured = {
        "points": len(rows),
        "default_voltage_mv": round(default_voltage * 1000.0, 3),
        "default_code": default_code,
        "vout_min_mv": round(min_voltage * 1000.0, 3),
        "vout_max_mv": round(max_voltage * 1000.0, 3),
        "valid_min_code": valid_min_code,
        "valid_max_code": valid_max_code,
        "step_mv": round(step_voltage_mv, 3),
        "linearity_pct": round(linearity_pct, 3),
    }
    return ItemResult(item_key=item_key, name=name, unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path,
                      notes=f"有效段步进 {step_voltage_mv:.3f}mV，线性度 {linearity_pct:.3f}%")
