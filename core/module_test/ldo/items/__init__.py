"""LDO 测试项实现集合（规划 §2.1）。

每个 item 为 ``run(ctx) -> ItemResult`` 纯逻辑函数：
  - n6705c 项：测量真实电压/电流；Mock 模式生成合理假数据。
  - scope 项：未接示波器时返回跳过结果（passed=None），不报错。
所有 item 禁阻塞 UI（由 runner 在 QThread 调用），禁裸 except。
"""
from __future__ import annotations

import os

from core.module_test._common import (
    ItemContext, linspace, mock_jitter, parse_channel, safe_measure, write_csv,
)
from core.module_test.result_model import ItemResult
from log_config import get_logger

logger = get_logger(__name__)


def _skipped(item_key: str, name: str, reason: str) -> ItemResult:
    return ItemResult(item_key=item_key, name=name, passed=None, notes=reason)


def vout_scan(ctx: ItemContext) -> ItemResult:
    """各挡位输出电压扫描（遍历寄存器全挡位）。"""
    item_key = "ldo_vout_scan"
    cfg = ctx.config
    dac_start = int(cfg.get("dac_start", 0))
    dac_end = int(cfg.get("dac_end", 255))
    dac_step = max(1, int(cfg.get("dac_step", 16)))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))

    codes = list(range(dac_start, dac_end + 1, dac_step))
    rows: list[list[float]] = []
    for i, code in enumerate(codes):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            # 线性：code 满量程对应 nominal_mv
            v = nominal_mv * (code / max(dac_end, 1)) * (1.0 + (i % 3 - 1) * 0.001)
            v = mock_jitter(v, 0.003)
        else:
            v = safe_measure(ctx.n6705c, "measure_voltage", vout_ch, nominal_mv) * 1000.0
        rows.append([code, round(v, 3)])
        ctx.progress_fn(int((i + 1) / len(codes) * 100), f"Vout scan {code}")
        ctx.log_fn(f"[{item_key}] DAC={code} -> Vout={v:.3f} mV")

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["DAC_code", "Vout (mV)"], rows)
    measured = {"points": len(rows), "vout_min_mv": min((r[1] for r in rows), default=0),
                "vout_max_mv": max((r[1] for r in rows), default=0)}
    return ItemResult(item_key=item_key, name="输出电压扫描", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path,
                      notes=f"扫描 {len(rows)} 个 DAC 挡位")


def load_line_reg(ctx: ItemContext) -> ItemResult:
    """负载调整率（1~200mA 扫描）。"""
    item_key = "ldo_load_reg"
    cfg = ctx.config
    i_start = float(cfg.get("iload_start_ma", 1))
    i_end = float(cfg.get("iload_end_ma", 200))
    i_step = float(cfg.get("iload_step_ma", 20))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))

    points = linspace(i_start, i_end, i_step)
    rows: list[list[float]] = []
    try:
        ctx.n6705c.set_mode(iload_ch, "CCLoad")
        ctx.n6705c.channel_on(iload_ch)
    except Exception:  # noqa: BLE001
        logger.debug("set CCLoad failed (mock may ignore)", exc_info=True)

    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        try:
            ctx.n6705c.set_current(iload_ch, il / 1000.0)
        except Exception:  # noqa: BLE001
            pass
        if ctx.is_mock:
            v = nominal_mv - il * 0.02  # 轻微跌落
            v = mock_jitter(v, 0.002)
        else:
            v = safe_measure(ctx.n6705c, "measure_voltage", vout_ch, nominal_mv) * 1000.0
        rows.append([il, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Load reg {il}mA")
        ctx.log_fn(f"[{item_key}] Iload={il}mA -> Vout={v:.4f} mV")
    try:
        ctx.n6705c.set_current(iload_ch, 0)
        ctx.n6705c.channel_off(iload_ch)
    except Exception:  # noqa: BLE001
        pass

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Vout (mV)"], rows)
    delta = (rows[-1][1] - rows[0][1]) if len(rows) >= 2 else 0.0
    measured = {"points": len(rows), "vout_drop_mv": round(delta, 4),
                "load_reg_mv_per_a": round(delta / max((i_end - i_start) / 1000.0, 1e-6), 4)}
    return ItemResult(item_key=item_key, name="负载调整率", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def line_reg(ctx: ItemContext) -> ItemResult:
    """线性调整率（Vin 3.2~4.2V 扫描）。"""
    item_key = "ldo_line_reg"
    cfg = ctx.config
    vin_start = float(cfg.get("vin_start_v", 3.2))
    vin_end = float(cfg.get("vin_end_v", 4.2))
    vin_step = float(cfg.get("vin_step_v", 0.2))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    vin_ch = parse_channel(cfg.get("vin_channel", 2))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))

    points = linspace(vin_start, vin_end, vin_step)
    rows: list[list[float]] = []
    try:
        ctx.n6705c.set_mode(vin_ch, "PS2Q")
        ctx.n6705c.channel_on(vin_ch)
    except Exception:  # noqa: BLE001
        logger.debug("set PS2Q failed (mock may ignore)", exc_info=True)

    for i, vin in enumerate(points):
        if ctx.stop_flag_fn():
            break
        try:
            ctx.n6705c.set_voltage(vin_ch, vin)
        except Exception:  # noqa: BLE001
            pass
        if ctx.is_mock:
            v = nominal_mv + (vin - 3.7) * 0.5  # 微弱跟随
            v = mock_jitter(v, 0.001)
        else:
            v = safe_measure(ctx.n6705c, "measure_voltage", vout_ch, nominal_mv) * 1000.0
        rows.append([vin, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Line reg {vin}V")
        ctx.log_fn(f"[{item_key}] Vin={vin}V -> Vout={v:.4f} mV")

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vin (V)", "Vout (mV)"], rows)
    delta = (max(r[1] for r in rows) - min(r[1] for r in rows)) if rows else 0.0
    measured = {"points": len(rows), "vout_span_mv": round(delta, 4)}
    return ItemResult(item_key=item_key, name="线性调整率", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def quiescent(ctx: ItemContext) -> ItemResult:
    """静态电流（Iq）。"""
    item_key = "ldo_quiescent"
    cfg = ctx.config
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    modes = cfg.get("iq_modes", ["NORMAL", "SLEEP"])
    rows: list[list] = []
    for i, mode in enumerate(modes):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            iq = 5.0 if mode == "SLEEP" else 80.0
            iq = mock_jitter(iq, 0.05)
        else:
            iq = safe_measure(ctx.n6705c, "measure_current", vin_ch, 0.0) * 1e6  # A -> uA
        rows.append([mode, round(iq, 3)])
        ctx.progress_fn(int((i + 1) / len(modes) * 100), f"Iq {mode}")
        ctx.log_fn(f"[{item_key}] mode={mode} -> Iq={iq:.3f} uA")

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Mode", "Iq (uA)"], rows)
    measured = {"rows": rows}
    return ItemResult(item_key=item_key, name="静态电流", unit="uA",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def ripple(ctx: ItemContext) -> ItemResult:
    """输出纹波（依赖示波器）。"""
    item_key = "ldo_ripple"
    if ctx.scope is None:
        return _skipped(item_key, "输出纹波", "未连接示波器，跳过")
    cfg = ctx.config
    vpp = mock_jitter(2.5, 0.1) if ctx.is_mock else 0.0
    rms = mock_jitter(0.4, 0.1) if ctx.is_mock else 0.0
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vpp (mV)", "RMS (mV)"], [[round(vpp, 4), round(rms, 4)]])
    ctx.log_fn(f"[{item_key}] Vpp={vpp:.3f} mV, RMS={rms:.3f} mV")
    return ItemResult(item_key=item_key, name="输出纹波", unit="mV",
                      passed=None, measured={"vpp_mv": round(vpp, 4), "rms_mv": round(rms, 4)},
                      raw_csv_path=csv_path)


def psrr(ctx: ItemContext) -> ItemResult:
    """电源抑制比（依赖示波器）。"""
    item_key = "ldo_psrr"
    if ctx.scope is None:
        return _skipped(item_key, "电源抑制比", "未连接示波器，跳过")
    freqs = ctx.config.get("psrr_freqs", ["1kHz", "10kHz", "100kHz"])
    rows: list[list] = []
    for i, f in enumerate(freqs):
        if ctx.stop_flag_fn():
            break
        db = mock_jitter(60.0, 0.03) if ctx.is_mock else 0.0
        rows.append([f, round(db, 3)])
        ctx.progress_fn(int((i + 1) / len(freqs) * 100), f"PSRR {f}")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Freq", "PSRR (dB)"], rows)
    return ItemResult(item_key=item_key, name="电源抑制比", unit="dB",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def load_transient(ctx: ItemContext) -> ItemResult:
    """负载瞬态响应（依赖示波器）。"""
    item_key = "ldo_load_transient"
    if ctx.scope is None:
        return _skipped(item_key, "负载瞬态响应", "未连接示波器，跳过")
    freqs = ctx.config.get("transient_freqs", ["10Hz", "100Hz", "1kHz"])
    rows: list[list] = []
    for i, f in enumerate(freqs):
        if ctx.stop_flag_fn():
            break
        overshoot = mock_jitter(30.0, 0.05) if ctx.is_mock else 0.0
        undershoot = mock_jitter(-25.0, 0.05) if ctx.is_mock else 0.0
        recover_us = mock_jitter(50.0, 0.1) if ctx.is_mock else 0.0
        rows.append([f, round(overshoot, 3), round(undershoot, 3), round(recover_us, 3)])
        ctx.progress_fn(int((i + 1) / len(freqs) * 100), f"Transient {f}")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Freq", "Overshoot (mV)", "Undershoot (mV)", "Recover (us)"], rows)
    return ItemResult(item_key=item_key, name="负载瞬态响应", unit="mV",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


# 测试项注册表：item_key -> (name, run_fn, needs_scope)
LDO_ITEMS: dict[str, tuple[str, object, bool]] = {
    "ldo_vout_scan": ("输出电压扫描", vout_scan, False),
    "ldo_load_reg": ("负载调整率", load_line_reg, False),
    "ldo_line_reg": ("线性调整率", line_reg, False),
    "ldo_quiescent": ("静态电流", quiescent, False),
    "ldo_ripple": ("输出纹波", ripple, True),
    "ldo_psrr": ("电源抑制比", psrr, True),
    "ldo_load_transient": ("负载瞬态响应", load_transient, True),
}
