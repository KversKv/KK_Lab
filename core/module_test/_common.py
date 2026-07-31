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
    """把通道配成电压表（VMETer）并上电，参考 PMU DCDC worker。

    全自动流程下通道可能是关闭状态，须显式 channel_on，
    否则 measure_voltage 读不到值。
    """
    try:
        ctx.n6705c.set_mode(channel, "VMETer")
        ctx.n6705c.set_channel_range(channel)
        ctx.n6705c.channel_on(channel)
    except Exception:  # noqa: BLE001
        logger.error("setup meter ch%d failed", channel, exc_info=True)


def setup_load_channel(ctx: "ItemContext", channel: int,
                       initial_current_a: float | None = None) -> None:
    """把通道配成电子负载（CCLoad）并上电，参考 PMU DCDC worker。

    通道关闭状态下可先写电流再开启，避免 channel_on 瞬间沿用
    上一项遗留的末点电流值。initial_current_a 为 None 时直接开启。
    注意：CCLoad 开启状态下禁止设 0mA（硬红线 12）。
    """
    try:
        ctx.n6705c.set_mode(channel, "CCLoad")
        ctx.n6705c.set_channel_range(channel)
        if initial_current_a is not None and initial_current_a > 0:
            set_load_current(ctx, channel, initial_current_a)
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
    """收尾：关断负载通道（参考 PMU DCDC worker finally 块）。

    禁止在 CCLoad 开启状态下设 0mA（硬红线 12），故直接 channel_off。
    """
    try:
        ctx.n6705c.channel_off(channel)
    except Exception:  # noqa: BLE001
        logger.error("teardown load ch%d failed", channel, exc_info=True)


def restore_vin(ctx: "ItemContext", channel: int, voltage: float) -> None:
    """扫 Vin 类测试项收尾：把 VIN 通道还原回标称电压（DUT 供电态）。

    line_reg / dropout 等项把 Vin 扫到非默认值后直接返回，通道停在末点电压
    会污染后续测试项 / 让 DUT 掉电。仅回写电压，不关通道（VIN 是 DUT 电源）。
    """
    try:
        ctx.n6705c.set_voltage(channel, voltage)
    except Exception:  # noqa: BLE001
        logger.error("restore vin ch%d failed", channel, exc_info=True)


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
    iload_ch = parse_channel(cfg.get("iload_channel", 3))

    i2c = create_i2c(ctx)
    if ctx.is_mock:
        ctx.log_fn(f"[{item_key}] [DEBUG] Using Mock I2C interface.")

    setup_meter_channel(ctx, vmeter_ch)

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

    # 扫描全程挂 1mA 轻载（先写电流再开通道，结束后关断）
    setup_load_channel(ctx, iload_ch, initial_current_a=0.001)

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
            teardown_load(ctx, iload_ch)
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

        diff_mv = "" if len(voltages) < 2 else (f"{(measured_v - voltages[-2]) * 1000.0:+.3f}mV")
        ctx.log_fn(f"[{item_key}] [MEAS] Code=0x{code:0{hex_width}X}  "
                   f"Measured={measured_v:>8.4f}V  Diff={diff_mv}")
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

    # 收尾关断负载通道（CCLoad 开启态禁设 0mA，直接 channel_off）
    teardown_load(ctx, iload_ch)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["DAC_code", "Vout (mV)", "Diff (mV)"],
              [row + ["" if i == 0 else round(row[1] - rows[i - 1][1], 3)]
               for i, row in enumerate(rows)])
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


def _arb_stop_and_wait(ctx: "ItemContext", channel: int) -> None:
    """停 ARB 并轮询等 initiated 位真正清零（ABOR:TRAN 后状态非立即可改）。

    Mock / 无 wait_arb_idle 接口时退化为固定 0.5s 等待。
    """
    ctx.n6705c.arb_stop()
    if ctx.is_mock or not hasattr(ctx.n6705c, "wait_arb_idle"):
        settle(ctx, 0.5)
        return
    if not ctx.n6705c.wait_arb_idle(channel, timeout_s=3.0):
        ctx.log_fn(f"[N6705C] CH{channel} 等待 ARB 空闲超时，继续执行")


def _reset_arb_state(ctx: "ItemContext", channels: list[int]) -> None:
    """彻底清 ARB 残留：停 ARB + 等空闲 + 逐通道退出电压/电流 ARB 模式。

    clear_arb_all_channels 的 ABOR:TRAN 被裸 except 吞掉，且未等 initiated
    清零就写 VOLT/CURR:MODE FIX（连续脉冲时清除慢，此时写 FIX 报 +308 被忽略），
    导致上一项 Load Transient 的 CURR:MODE ARB 残留到下一项。本函数先等空闲
    再显式逐通道退出两种 ARB 模式，保证通道回到固定输出态。
    """
    if ctx.is_mock:
        return
    try:
        ctx.n6705c.arb_stop()
    except Exception:  # noqa: BLE001 - 停止失败降级记录，继续清理
        logger.error("arb_stop failed in _reset_arb_state", exc_info=True)
    for ch in channels:
        if hasattr(ctx.n6705c, "wait_arb_idle"):
            try:
                ctx.n6705c.wait_arb_idle(ch, timeout_s=3.0)
            except Exception:  # noqa: BLE001
                logger.error("wait_arb_idle ch%d failed", ch, exc_info=True)
    for ch in channels:
        try:
            ctx.n6705c.exit_arb_voltage(ch)
        except Exception:  # noqa: BLE001
            logger.error("exit_arb_voltage ch%d failed", ch, exc_info=True)
        try:
            ctx.n6705c.exit_arb_current(ch)
        except Exception:  # noqa: BLE001
            logger.error("exit_arb_current ch%d failed", ch, exc_info=True)


def _n6705c_err_check(ctx: "ItemContext", tag: str) -> None:
    """查询 N6705C 错误队列，非 +0 即经 log_fn 上抛 UI 日志（真机调试用）。

    读取 SYST:ERR? 会弹出并清除队首错误；循环读到 +0 为止以清空队列。
    任何查询异常都静默忽略，不阻断主流程。
    """
    if ctx.is_mock:
        return
    instr = getattr(ctx.n6705c, "instr", None)
    if instr is None:
        return
    try:
        for _ in range(8):
            err = instr.query("SYST:ERR?").strip()
            if err.startswith("+0") or err.startswith("0,"):
                break
            ctx.log_fn(f"[N6705C][{tag}] {err}")
            logger.warning("N6705C err @%s: %s", tag, err)
    except Exception:  # noqa: BLE001 - 查错失败不影响流程
        logger.debug("SYST:ERR? query failed @%s", tag, exc_info=True)


def _measure_with_autoscale(ctx: "ItemContext", scope_ch: int, nominal_v: float,
                            scale_v: float, settle_s: float,
                            timebase_s: float = 0.0,
                            max_tries: int = 4) -> tuple[float, float, float, float, float]:
    """设量程后测 Vmax/Vmin/Vmean/Vpp；波形削波（9.9e37 无效值）时量程翻倍重试。

    返回 (vmax, vmin, vmean, vpp, 实际量程)。重试前须 run() 恢复采集再 settle，
    否则停采状态下改量程拿不到新波形。全部尝试耗尽后抛最后一次异常。

    timebase_s 为示波器时基（s/div），采集稳定等待取 max(1s, 6×时基)，
    确保 stop 时屏幕已显示≥1 帧完整波形（低频大时基时 1s 不够）。
    成功返回时屏幕处于 stop 态，调用方可直接用该帧截图。
    """
    # 每次改量程后统一等 6×时基（含 1s 下限），让示波器采满一整屏新波形
    acq_settle = max(1.0, 6.0 * timebase_s)
    last_err: Exception | None = None
    for attempt in range(max_tries):
        ctx.scope.set_channel_scale(scope_ch, scale_v)
        ctx.scope.set_channel_offset(scope_ch, nominal_v)
        settle(ctx, acq_settle)
        ctx.scope.stop()
        try:
            vmax = float(ctx.scope.get_channel_max(scope_ch))
            vmin = float(ctx.scope.get_channel_min(scope_ch))
            vbase = float(ctx.scope.get_channel_mean(scope_ch))
            vpp = float(ctx.scope.get_channel_pk2pk(scope_ch))
            return vmax, vmin, vbase, vpp, scale_v
        except Exception as e:  # noqa: BLE001 - 无效测量值，扩量程重试
            last_err = e
            logger.info("autoscale attempt %d failed (scale=%.4f V/div): %s",
                        attempt + 1, scale_v, e)
            scale_v *= 2.0
            # 恢复采集并等满一整屏，否则下一轮改量程时波形尚未重建
            ctx.scope.run()
            settle(ctx, acq_settle)
    raise last_err  # type: ignore[misc]


def _capture_scope_png(ctx: "ItemContext", item_key: str, load_ma: float,
                       shot_dir: str, tag: str | None = None) -> str | None:
    """捕获当前负载点的示波器截图，落盘 PNG，返回路径（Mock/失败返回 None）。"""
    if ctx.is_mock or ctx.scope is None:
        return None
    try:
        png = ctx.scope.capture_screen_png()
    except Exception:  # noqa: BLE001 - 截图失败不阻断扫描
        logger.error("scope capture_screen_png failed @%gmA", load_ma, exc_info=True)
        return None
    if not png:
        return None
    try:
        os.makedirs(shot_dir, exist_ok=True)
        suffix = tag if tag else f"{load_ma:g}mA"
        path = os.path.join(shot_dir, f"{item_key}_{suffix}.png")
        with open(path, "wb") as f:
            f.write(png)
        return path
    except Exception:  # noqa: BLE001
        logger.error("save scope png failed @%gmA", load_ma, exc_info=True)
        return None


def run_load_capability_ripple(ctx: "ItemContext", item_key: str, name: str,
                               mock_vpp_base: float,
                               mock_rms_base: float) -> "ItemResult":
    """Load Capability & Ripple（LDO / DCDC 共用，依赖示波器）。

    流程：Vin=PS2Q 源上电，CCLoad 从起始负载按步进扫到结束负载；
    每个负载点测输出电压（N6705C 电压表）与纹波（示波器 AC 耦合 Vpp/RMS，
    set_AutoRipple_test 自动优化档位），并逐点捕获示波器截图进报告。
    负载通道 / 输出（电压表）通道复用被测配置；示波器通道由项级参数设置。
    """
    from core.module_test.result_model import ItemResult

    if ctx.scope is None:
        return ItemResult(item_key=item_key, name=name, passed=None,
                          notes="未连接示波器，跳过")

    cfg = ctx.config
    scope_ch = int(cfg.get("scope_vout_channel", 1))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.8))
    i_start = float(cfg.get("iload_start_ma", 0))
    i_end = float(cfg.get("iload_end_ma", 200))
    i_step = float(cfg.get("iload_step_ma", 20))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))

    points = linspace(i_start, i_end, i_step)
    rows: list[list[Any]] = []
    screenshots: list[dict[str, Any]] = []
    shot_dir = os.path.join(ctx.out_dir, "screenshots")

    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch, initial_current_a=max(i_start, 0.001) / 1000.0)
        # 上一项可能调过 close_all_channels()（transient 流程），须显式开显示
        ctx.scope.set_channel_display(scope_ch, True)

    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            vout = mock_jitter(nominal_mv - il * 0.02, 0.002)
            vpp = mock_jitter(mock_vpp_base + il * 0.005, 0.08)
            rms = mock_jitter(mock_rms_base + il * 0.001, 0.08)
            shot = None
        else:
            set_load_current(ctx, iload_ch, il / 1000.0)
            settle(ctx, max(settle_s * 8, 0.4))
            try:
                ctx.scope.set_AutoRipple_test(scope_ch)
                settle(ctx, 0.3)
                vpp = float(ctx.scope.get_channel_pk2pk(scope_ch)) * 1000.0  # V->mV
                rms = float(ctx.scope.get_channel_rms(scope_ch)) * 1000.0
            except Exception:  # noqa: BLE001 - 单点读数失败降级，继续扫描
                logger.error("scope ripple read failed @%gmA", il, exc_info=True)
                vpp = 0.0
                rms = 0.0
            vout = measure_avg(ctx, "measure_voltage", vout_ch,
                               count=1, settle_s=settle_s,
                               default=nominal_mv / 1000.0) * 1000.0
            shot = _capture_scope_png(ctx, item_key, il, shot_dir)
        rows.append([il, round(vout, 4), round(vpp, 4), round(rms, 4)])
        if shot:
            screenshots.append({"Iload (mA)": il, "png": shot})
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"{name} {il:g}mA")
        ctx.log_fn(f"[{item_key}] Iload={il:g}mA -> Vout={vout:.4f} mV, "
                   f"Vpp={vpp:.3f} mV, RMS={rms:.3f} mV")
    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Vout (mV)", "Vpp (mV)", "RMS (mV)"], rows)

    max_row = max(rows, key=lambda r: r[2], default=None)
    measured: dict[str, Any] = {
        "points": len(rows),
        "i_start_ma": i_start,
        "i_end_ma": i_end,
        "i_step_ma": i_step,
        "max_vpp_mv": max_row[2] if max_row else "",
        "max_vpp_at_ma": max_row[0] if max_row else "",
    }
    if screenshots:
        measured["screenshots"] = screenshots
    result = ItemResult(item_key=item_key, name=name, unit="mV",
                        passed=None, measured=measured, raw_csv_path=csv_path)
    if screenshots:
        result.waveform_png = screenshots[0]["png"]
    return result


def run_line_transient(ctx: "ItemContext", item_key: str, name: str,
                       mock_over_mv: float, mock_under_mv: float) -> "ItemResult":
    """Line Transient Response（LDO / DCDC 共用，依赖示波器）。

    流程（对齐手动测试，逐组执行）：
      0. 开局 clear_arb_all_channels()：ABOR:TRAN + 全通道 VOLT/CURR:MODE FIX，
         去掉其它通道遗留 ARB，避免 BUS 触发误带起旧通道脉冲；
      1. Vin 通道置 PS2Q 源；
      2. Arb Type=Voltage / Shape=Pulse，Vin0/Vin1 为电压（正），
         t0=半周期、t1=0、t2=半周期（50% 占空；真机强制 t0+t1+t2=1/freq）；
      3. 勾选 Continuous（ARB:TERM:LAST ON）+ TRIG:ARB:SOUR IMM（须在 INIT:TRAN 之前写）
         + INIT:TRAN 立即启动连续 Vin 脉冲（armed 后写源报 +308，BUS+*TRG 后置不触发）；
      4. 示波器按频率设 timebase（整屏约 2 周期），量程/偏置按预期摆幅与标称 Vout 设置；
      5. 稳定后暂停采集，截图并测 Vmax/Vmin/Vmean/Vpp，
         过冲=Vmax-Vmean、欠冲=Vmean-Vmin（mV）；
      每组测完 ABOR:TRAN + VOLT:MODE FIX 复位 Vin 通道，再换下一组。
    """
    from core.module_test.param_spec import DEFAULT_LINE_TRANSIENT_GROUPS
    from core.module_test.result_model import ItemResult

    if ctx.scope is None:
        return ItemResult(item_key=item_key, name=name, passed=None,
                          notes="未连接示波器，跳过")

    cfg = ctx.config
    groups = cfg.get("line_transient_groups") or DEFAULT_LINE_TRANSIENT_GROUPS
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    scope_ch = int(cfg.get("scope_vout_channel", 1))
    nominal_v = float(cfg.get("vout_nominal_mv", 1800)) / 1000.0
    vspan_v = float(cfg.get("transient_vspan_mv", 200)) / 1000.0
    settle_s = float(cfg.get("settle_time_s", 0.05))

    rows: list[list[Any]] = []
    screenshots: list[dict[str, Any]] = []
    shot_dir = os.path.join(ctx.out_dir, "screenshots")

    if not ctx.is_mock:
        _reset_arb_state(ctx, [vin_ch])

    for idx, g in enumerate(groups):
        if ctx.stop_flag_fn():
            break
        vin0_v = float(g.get("vin0_v", 3.2))
        vin1_v = float(g.get("vin1_v", 4.2))
        freq = float(g.get("freq_hz", 10.0))
        if freq <= 0:
            ctx.log_fn(f"[{item_key}] 组{idx + 1} 频率无效（{freq:g}Hz），跳过")
            continue
        period = 1.0 / freq
        label = f"组{idx + 1} {vin0_v:g}->{vin1_v:g}V @{freq:g}Hz"

        if ctx.is_mock:
            over = mock_jitter(mock_over_mv, 0.05)
            under = mock_jitter(mock_under_mv, 0.05)
            vpp = over + under
            shot = None
        else:
            over = under = vpp = 0.0
            shot = None
            try:
                # 先停掉上一轮遗留 ARB 并等 initiated 清零，否则改参数报 +308
                try:
                    _arb_stop_and_wait(ctx, vin_ch)
                except Exception:  # noqa: BLE001
                    logger.error("arb_stop before group %d failed", idx + 1,
                                 exc_info=True)
                ctx.n6705c.set_mode(vin_ch, "PS2Q")
                ctx.n6705c.channel_on(vin_ch)
                ctx.n6705c.set_arb_pulse(vin_ch, vin0_v, vin1_v,
                                         period / 2.0, 0.0, period / 2.0, freq)
                # 勾选 Continuous（ARB:TERM:LAST ON）：须在形状配置后、arb_on 前
                ctx.n6705c.set_arb_continuous(vin_ch, True)
                ctx.n6705c.restore_arb_trigger_source()
                ctx.n6705c.arb_on(vin_ch)

                # 先关闭其它通道、波形强度设 100%（便于看清过冲/欠冲）
                if hasattr(ctx.scope, "close_all_channels"):
                    ctx.scope.close_all_channels()
                if hasattr(ctx.scope, "set_waveform_intensity"):
                    ctx.scope.set_waveform_intensity(100)
                # 初始 scale=vspan/3 留余量；时基=period/2，10 格整屏约 5 周期
                ctx.scope.set_timebase_scale(period / 2.0)
                ctx.scope.set_channel_display(scope_ch, True)
                # 测量无效（削波 9.9e37）时量程自动翻倍重试直至波形完整入屏；
                # timebase=period/2 传入，采集稳定等待取 max(1s, 6×时基)
                try:
                    vmax, vmin, vbase, vpp_v, used_scale = _measure_with_autoscale(
                        ctx, scope_ch, nominal_v, vspan_v / 3.0, settle_s,
                        timebase_s=period / 2.0)
                except Exception:  # noqa: BLE001 - 量程耗尽仍削波，恢复采集再降级
                    logger.error("autoscale exhausted, re-run acquisition", exc_info=True)
                    ctx.scope.run()
                    raise
                if used_scale > vspan_v / 3.0:
                    ctx.log_fn(f"[{item_key}] {label} 量程自动扩至 "
                               f"{used_scale * 1000:g} mV/div")
                vpp = vpp_v * 1000.0
                over = (vmax - vbase) * 1000.0
                under = (vbase - vmin) * 1000.0
                # autoscale 返回时屏幕已定格在稳定 stop 帧，直接用该帧截图
                shot = _capture_scope_png(ctx, item_key, vin1_v, shot_dir,
                                          tag=f"g{idx + 1}_{freq:g}Hz")
                ctx.scope.run()
            except Exception:  # noqa: BLE001 - 单组失败降级，继续下一组
                logger.error("line transient group %d failed", idx + 1, exc_info=True)
                ctx.log_fn(f"[{item_key}] [ERROR] {label} 执行异常，记 0 继续")
            finally:
                try:
                    # 停 ARB 并轮询 initiated 清零，否则紧跟的
                    # ARB:COUN/VOLT:MODE FIX 报 +308（连续脉冲时清除较慢）
                    _arb_stop_and_wait(ctx, vin_ch)
                    ctx.n6705c.set_arb_continuous(vin_ch, False)
                    ctx.n6705c.exit_arb_voltage(vin_ch)
                except Exception:  # noqa: BLE001
                    logger.error("exit arb ch%d failed", vin_ch, exc_info=True)

        rows.append([idx + 1, vin0_v, vin1_v, freq,
                     round(over, 3), round(under, 3), round(vpp, 3)])
        if shot:
            screenshots.append({"Iload (mA)": str(idx + 1), "png": shot})
        ctx.progress_fn(int((idx + 1) / len(groups) * 100), f"{name} {label}")
        ctx.log_fn(f"[{item_key}] {label} -> Overshoot={over:.3f} mV, "
                   f"Undershoot={under:.3f} mV, Vpp={vpp:.3f} mV")

    if not ctx.is_mock:
        # 恢复 Vin 正常输出（全自动流程后续项默认 DUT 有电，VIN 通道不干预）
        restore_vin(ctx, vin_ch, float(cfg.get("vin_v", 3.8)))

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path,
              ["Group", "Vin0 (V)", "Vin1 (V)", "Freq (Hz)",
               "Overshoot (mV)", "Undershoot (mV)", "Vpp (mV)"], rows)

    max_over = max(rows, key=lambda r: r[4], default=None)
    max_under = max(rows, key=lambda r: r[5], default=None)
    measured: dict[str, Any] = {
        "groups": len(rows),
        "max_overshoot_mv": max_over[4] if max_over else "",
        "max_overshoot_group": max_over[0] if max_over else "",
        "max_undershoot_mv": max_under[5] if max_under else "",
        "max_undershoot_group": max_under[0] if max_under else "",
    }
    if screenshots:
        measured["screenshots"] = screenshots
    result = ItemResult(item_key=item_key, name=name, unit="mV",
                        passed=None, measured=measured, raw_csv_path=csv_path)
    if screenshots:
        result.waveform_png = screenshots[0]["png"]
    return result


def run_load_transient(ctx: "ItemContext", item_key: str, name: str,
                       mock_over_mv: float, mock_under_mv: float) -> "ItemResult":
    """Load Transient Response（LDO / DCDC 共用，依赖示波器）。

    流程（对齐手动测试，逐组执行）：
      0. 开局 clear_arb_all_channels()：ABOR:TRAN + 全通道 VOLT/CURR:MODE FIX，
         去掉其它通道遗留 ARB，避免 BUS 触发误带起旧通道脉冲；
      1. 负载通道置 CCLoad，Current Slew=MAX；
      2. Arb Type=Current / Shape=Pulse，I0/I1 取负（拉载），
         t0=半周期、t1=0、t2=半周期（50% 占空；真机强制 t0+t1+t2=1/freq，
         t2=0 会得到零顶部宽度，见 n6705c.set_arb_current_pulse docstring）；
      3. 勾选 Continuous（ARB:TERM:LAST ON）+ TRIG:ARB:SOUR IMM（须在 INIT:TRAN 之前写）
         + INIT:TRAN 立即启动连续脉冲（armed 后写源报 +308，BUS+*TRG 后置不触发）；
      4. 示波器按频率设 timebase（整屏约 2 周期），量程/偏置按预期摆幅与标称 Vout 设置；
      5. 稳定后暂停采集，截图并测 Vmax/Vmin/Vmean/Vpp，
         过冲=Vmax-Vmean、欠冲=Vmean-Vmin（mV）；
      每组测完 ABOR:TRAN + CURR:MODE FIX 复位负载通道，再换下一组。
    """
    from core.module_test.param_spec import DEFAULT_TRANSIENT_GROUPS
    from core.module_test.result_model import ItemResult

    if ctx.scope is None:
        return ItemResult(item_key=item_key, name=name, passed=None,
                          notes="未连接示波器，跳过")

    cfg = ctx.config
    groups = cfg.get("transient_groups") or DEFAULT_TRANSIENT_GROUPS
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    scope_ch = int(cfg.get("scope_vout_channel", 1))
    nominal_v = float(cfg.get("vout_nominal_mv", 1800)) / 1000.0
    vspan_v = float(cfg.get("transient_vspan_mv", 200)) / 1000.0
    settle_s = float(cfg.get("settle_time_s", 0.05))

    rows: list[list[Any]] = []
    screenshots: list[dict[str, Any]] = []
    shot_dir = os.path.join(ctx.out_dir, "screenshots")

    if not ctx.is_mock:
        _reset_arb_state(ctx, [iload_ch])
        # 首组 i0 作为初始电流，避免 channel_on 瞬间沿用遗留值
        first_i0_ma = max(float(g.get("i0_ma", 10.0)) for g in groups) if groups else 10.0
        setup_load_channel(ctx, iload_ch, initial_current_a=first_i0_ma / 1000.0)

    for idx, g in enumerate(groups):
        if ctx.stop_flag_fn():
            break
        i0_ma = float(g.get("i0_ma", 10.0))
        i1_ma = float(g.get("i1_ma", 100.0))
        freq = float(g.get("freq_hz", 100.0))
        if freq <= 0:
            ctx.log_fn(f"[{item_key}] 组{idx + 1} 频率无效（{freq:g}Hz），跳过")
            continue
        period = 1.0 / freq
        label = f"组{idx + 1} {i0_ma:g}->{i1_ma:g}mA @{freq:g}Hz"

        if ctx.is_mock:
            over = mock_jitter(mock_over_mv, 0.05)
            under = mock_jitter(mock_under_mv, 0.05)
            vpp = over + under
            shot = None
        else:
            over = under = vpp = 0.0
            shot = None
            try:
                # 先停掉上一轮遗留 ARB 并等 initiated 清零，否则改参数报 +308
                try:
                    _arb_stop_and_wait(ctx, iload_ch)
                except Exception:  # noqa: BLE001
                    logger.error("arb_stop before group %d failed", idx + 1,
                                 exc_info=True)
                _n6705c_err_check(ctx, f"g{idx + 1} arb_stop")
                ctx.n6705c.set_current_slew(iload_ch, "MAX")
                _n6705c_err_check(ctx, f"g{idx + 1} set_slew")
                ctx.n6705c.set_arb_current_pulse(
                    iload_ch, -abs(i0_ma) / 1000.0, -abs(i1_ma) / 1000.0,
                    period / 2.0, 0.0, period / 2.0, freq)
                _n6705c_err_check(ctx, f"g{idx + 1} set_arb_pulse")
                # 勾选 Continuous（ARB:TERM:LAST ON）：须在形状配置后、arb_on 前
                ctx.n6705c.set_arb_continuous(iload_ch, True)
                _n6705c_err_check(ctx, f"g{idx + 1} set_continuous")
                ctx.n6705c.restore_arb_trigger_source()
                _n6705c_err_check(ctx, f"g{idx + 1} trig_src")
                ctx.n6705c.arb_on(iload_ch)
                _n6705c_err_check(ctx, f"g{idx + 1} arb_on")

                # 先关闭其它通道、波形强度设 100%（便于看清过冲/欠冲）
                if hasattr(ctx.scope, "close_all_channels"):
                    ctx.scope.close_all_channels()
                if hasattr(ctx.scope, "set_waveform_intensity"):
                    ctx.scope.set_waveform_intensity(100)
                # 先强制 run：示波器可能停在上一项的 stop 态，停采态下改
                # 时基/量程只会重绘旧帧，settle 再久也采不到新波形
                ctx.scope.run()
                # 初始 scale=vspan/3 留余量；时基=period/2，10 格整屏约 5 周期
                ctx.scope.set_timebase_scale(period / 2.0)
                ctx.scope.set_channel_display(scope_ch, True)
                # 改时基/通道后须先等示波器采满一屏新波形，否则后续测量/截图
                # 抓到的是旧时基下的过渡帧（首组时基突变最明显）。
                # 等待 60×时基：低频大时基（如 10Hz=50ms/div）需足够时长让 DSOX
                # 在新时基下采满一屏并刷新显示，短 settle 会让 autoscale stop
                # 定格在未采满的帧上（1s 下限保证高频组时基过小时仍有 ≥1s）
                settle(ctx, max(1.0, 60.0 * (period / 2.0)))
                # 测量无效（削波 9.9e37）时量程自动翻倍重试直至波形完整入屏；
                # timebase=period/2 传入，采集稳定等待取 max(1s, 6×时基)
                try:
                    vmax, vmin, vbase, vpp_v, used_scale = _measure_with_autoscale(
                        ctx, scope_ch, nominal_v, vspan_v / 3.0, settle_s,
                        timebase_s=period / 2.0)
                except Exception:  # noqa: BLE001 - 量程耗尽仍削波，恢复采集再降级
                    logger.error("autoscale exhausted, re-run acquisition", exc_info=True)
                    ctx.scope.run()
                    raise
                if used_scale > vspan_v / 3.0:
                    ctx.log_fn(f"[{item_key}] {label} 量程自动扩至 "
                               f"{used_scale * 1000:g} mV/div")
                vpp = vpp_v * 1000.0
                over = (vmax - vbase) * 1000.0
                under = (vbase - vmin) * 1000.0
                # autoscale 返回时屏幕定格在刚验证过测量值的稳定 stop 帧，
                # 直接截图；不要再 run/stop，否则会把已验证帧冲掉重采
                shot = _capture_scope_png(ctx, item_key, i1_ma, shot_dir,
                                          tag=f"g{idx + 1}_{freq:g}Hz")
                ctx.scope.run()
            except Exception as e:  # noqa: BLE001 - 单组失败降级，继续下一组
                logger.error("load transient group %d failed", idx + 1, exc_info=True)
                ctx.log_fn(f"[{item_key}] [ERROR] {label} 执行异常"
                           f"（{type(e).__name__}: {e}），记 0 继续")
            finally:
                try:
                    # 停 ARB 并轮询 initiated 清零，否则紧跟的
                    # ARB:COUN/CURR:MODE FIX 报 +308（连续脉冲时清除较慢）
                    _arb_stop_and_wait(ctx, iload_ch)
                    _n6705c_err_check(ctx, f"g{idx + 1} end arb_stop")
                    ctx.n6705c.set_arb_continuous(iload_ch, False)
                    _n6705c_err_check(ctx, f"g{idx + 1} end set_continuous_off")
                    ctx.n6705c.exit_arb_current(iload_ch)
                    _n6705c_err_check(ctx, f"g{idx + 1} end exit_arb_current")
                except Exception as e:  # noqa: BLE001
                    logger.error("exit arb ch%d failed", iload_ch, exc_info=True)
                    ctx.log_fn(f"[{item_key}] [ERROR] {label} 收尾异常"
                               f"（{type(e).__name__}: {e}）")

        rows.append([idx + 1, i0_ma, i1_ma, freq,
                     round(over, 3), round(under, 3), round(vpp, 3)])
        if shot:
            screenshots.append({"Iload (mA)": str(idx + 1), "png": shot})
        ctx.progress_fn(int((idx + 1) / len(groups) * 100), f"{name} {label}")
        ctx.log_fn(f"[{item_key}] {label} -> Overshoot={over:.3f} mV, "
                   f"Undershoot={under:.3f} mV, Vpp={vpp:.3f} mV")

    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path,
              ["Group", "I0 (mA)", "I1 (mA)", "Freq (Hz)",
               "Overshoot (mV)", "Undershoot (mV)", "Vpp (mV)"], rows)

    max_over = max(rows, key=lambda r: r[4], default=None)
    max_under = max(rows, key=lambda r: r[5], default=None)
    measured: dict[str, Any] = {
        "groups": len(rows),
        "max_overshoot_mv": max_over[4] if max_over else "",
        "max_overshoot_group": max_over[0] if max_over else "",
        "max_undershoot_mv": max_under[5] if max_under else "",
        "max_undershoot_group": max_under[0] if max_under else "",
    }
    if screenshots:
        measured["screenshots"] = screenshots
    result = ItemResult(item_key=item_key, name=name, unit="mV",
                        passed=None, measured=measured, raw_csv_path=csv_path)
    if screenshots:
        result.waveform_png = screenshots[0]["png"]
    return result
