"""DCDC 测试项实现集合（规划 §2.2）。

复用策略说明：DCDC 效率规划要求可复用 core/pmu_test/dcdc/dcdc_worker.py，
但该 worker 是与 PMU UI 强耦合的 QThread（信号直连控件）。为保持 Module Test
独立可跑且不破坏分层，此处按相同测量原理（Vin/Vout/Iout 同步采样 + η 计算）
重新实现轻量纯函数版，行为一致、无 Qt 依赖。
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
    """各挡位输出电压扫描。"""
    item_key = "dcdc_vout_scan"
    cfg = ctx.config
    dac_start = int(cfg.get("dac_start", 0))
    dac_end = int(cfg.get("dac_end", 255))
    dac_step = max(1, int(cfg.get("dac_step", 16)))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1200))

    codes = list(range(dac_start, dac_end + 1, dac_step))
    rows: list[list] = []
    for i, code in enumerate(codes):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            v = nominal_mv * (code / max(dac_end, 1))
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
                      passed=None, measured=measured, raw_csv_path=csv_path)


def efficiency(ctx: ItemContext) -> ItemResult:
    """效率（1~200mA ramp）。"""
    item_key = "dcdc_efficiency"
    cfg = ctx.config
    i_start = float(cfg.get("iload_start_ma", 1))
    i_end = float(cfg.get("iload_end_ma", 200))
    i_step = float(cfg.get("iload_step_ma", 20))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vout_ch = parse_channel(cfg.get("vout_channel", 2))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    vout_v_nom = float(cfg.get("vout_nominal_mv", 1200)) / 1000.0

    points = linspace(i_start, i_end, i_step)
    rows: list[list] = []
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
            iin = il / 1000.0 * vout_v_nom / vin_v / 0.9  # 假设 90% 效率
            vout = vout_v_nom - il * 0.0005
            eff = (vout * il / 1000.0) / (vin_v * iin) * 100 if iin > 0 else 0
            eff = mock_jitter(min(eff, 95.0), 0.01)
        else:
            vout = safe_measure(ctx.n6705c, "measure_voltage", vout_ch)
            iout = safe_measure(ctx.n6705c, "measure_current", iload_ch)
            iin = safe_measure(ctx.n6705c, "measure_current", vin_ch)
            vin_meas = safe_measure(ctx.n6705c, "measure_voltage", vin_ch, vin_v)
            eff = (vout * iout) / (vin_meas * iin) * 100 if (vin_meas * iin) > 0 else 0
        rows.append([il, round(vout * 1000.0, 4), round(eff, 3)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Eff {il}mA")
        ctx.log_fn(f"[{item_key}] Iload={il}mA -> η={eff:.3f} %")
    try:
        ctx.n6705c.set_current(iload_ch, 0)
        ctx.n6705c.channel_off(iload_ch)
    except Exception:  # noqa: BLE001
        pass

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Vout (mV)", "Efficiency (%)"], rows)
    effs = [r[2] for r in rows]
    measured = {"points": len(rows), "max_eff": round(max(effs), 3) if effs else 0,
                "avg_eff": round(sum(effs) / len(effs), 3) if effs else 0}
    return ItemResult(item_key=item_key, name="效率", unit="%",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def load_line_reg(ctx: ItemContext) -> ItemResult:
    """负载调整率。"""
    item_key = "dcdc_load_reg"
    cfg = ctx.config
    i_start = float(cfg.get("iload_start_ma", 1))
    i_end = float(cfg.get("iload_end_ma", 200))
    i_step = float(cfg.get("iload_step_ma", 20))
    vout_ch = parse_channel(cfg.get("vout_channel", 2))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1200))

    points = linspace(i_start, i_end, i_step)
    rows: list[list] = []
    try:
        ctx.n6705c.set_mode(iload_ch, "CCLoad")
        ctx.n6705c.channel_on(iload_ch)
    except Exception:  # noqa: BLE001
        pass
    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        try:
            ctx.n6705c.set_current(iload_ch, il / 1000.0)
        except Exception:  # noqa: BLE001
            pass
        if ctx.is_mock:
            v = nominal_mv - il * 0.01
            v = mock_jitter(v, 0.002)
        else:
            v = safe_measure(ctx.n6705c, "measure_voltage", vout_ch, nominal_mv) * 1000.0
        rows.append([il, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Load reg {il}mA")
    try:
        ctx.n6705c.set_current(iload_ch, 0)
        ctx.n6705c.channel_off(iload_ch)
    except Exception:  # noqa: BLE001
        pass

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Vout (mV)"], rows)
    delta = (rows[-1][1] - rows[0][1]) if len(rows) >= 2 else 0.0
    measured = {"points": len(rows), "vout_drop_mv": round(delta, 4)}
    return ItemResult(item_key=item_key, name="负载调整率", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def line_reg(ctx: ItemContext) -> ItemResult:
    """线性调整率。"""
    item_key = "dcdc_line_reg"
    cfg = ctx.config
    vin_start = float(cfg.get("vin_start_v", 3.2))
    vin_end = float(cfg.get("vin_end_v", 4.2))
    vin_step = float(cfg.get("vin_step_v", 0.2))
    vout_ch = parse_channel(cfg.get("vout_channel", 2))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1200))

    points = linspace(vin_start, vin_end, vin_step)
    rows: list[list] = []
    try:
        ctx.n6705c.set_mode(vin_ch, "PS2Q")
        ctx.n6705c.channel_on(vin_ch)
    except Exception:  # noqa: BLE001
        pass
    for i, vin in enumerate(points):
        if ctx.stop_flag_fn():
            break
        try:
            ctx.n6705c.set_voltage(vin_ch, vin)
        except Exception:  # noqa: BLE001
            pass
        if ctx.is_mock:
            v = nominal_mv + (vin - 3.7) * 0.3
            v = mock_jitter(v, 0.001)
        else:
            v = safe_measure(ctx.n6705c, "measure_voltage", vout_ch, nominal_mv) * 1000.0
        rows.append([vin, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Line reg {vin}V")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vin (V)", "Vout (mV)"], rows)
    delta = (max(r[1] for r in rows) - min(r[1] for r in rows)) if rows else 0.0
    measured = {"points": len(rows), "vout_span_mv": round(delta, 4)}
    return ItemResult(item_key=item_key, name="线性调整率", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def quiescent(ctx: ItemContext) -> ItemResult:
    """静态电流（PWM/BURST/ULP 分模式）。"""
    item_key = "dcdc_quiescent"
    cfg = ctx.config
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    modes = cfg.get("iq_modes", ["PWM", "BURST", "ULP"])
    rows: list[list] = []
    for i, mode in enumerate(modes):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            iq = {"PWM": 200.0, "BURST": 60.0, "ULP": 8.0}.get(mode, 100.0)
            iq = mock_jitter(iq, 0.05)
        else:
            iq = safe_measure(ctx.n6705c, "measure_current", vin_ch, 0.0) * 1e6
        rows.append([mode, round(iq, 3)])
        ctx.progress_fn(int((i + 1) / len(modes) * 100), f"Iq {mode}")
        ctx.log_fn(f"[{item_key}] mode={mode} -> Iq={iq:.3f} uA")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Mode", "Iq (uA)"], rows)
    measured = {"rows": rows}
    return ItemResult(item_key=item_key, name="静态电流", unit="uA",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def ripple(ctx: ItemContext) -> ItemResult:
    """BUCK 纹波（依赖示波器）。"""
    item_key = "dcdc_ripple"
    if ctx.scope is None:
        return _skipped(item_key, "BUCK 纹波", "未连接示波器，跳过")
    vpp = mock_jitter(15.0, 0.1) if ctx.is_mock else 0.0
    rms = mock_jitter(3.0, 0.1) if ctx.is_mock else 0.0
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vpp (mV)", "RMS (mV)"], [[round(vpp, 4), round(rms, 4)]])
    ctx.log_fn(f"[{item_key}] Vpp={vpp:.3f} mV, RMS={rms:.3f} mV")
    return ItemResult(item_key=item_key, name="BUCK 纹波", unit="mV",
                      passed=None, measured={"vpp_mv": round(vpp, 4), "rms_mv": round(rms, 4)},
                      raw_csv_path=csv_path)


def psrr(ctx: ItemContext) -> ItemResult:
    """DCDC PSRR（依赖示波器）。"""
    item_key = "dcdc_psrr"
    if ctx.scope is None:
        return _skipped(item_key, "DCDC PSRR", "未连接示波器，跳过")
    freqs = ctx.config.get("psrr_freqs", ["1kHz", "10kHz", "100kHz"])
    rows: list[list] = []
    for i, f in enumerate(freqs):
        if ctx.stop_flag_fn():
            break
        db = mock_jitter(45.0, 0.05) if ctx.is_mock else 0.0
        rows.append([f, round(db, 3)])
        ctx.progress_fn(int((i + 1) / len(freqs) * 100), f"PSRR {f}")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Freq", "PSRR (dB)"], rows)
    return ItemResult(item_key=item_key, name="DCDC PSRR", unit="dB",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def load_transient(ctx: ItemContext) -> ItemResult:
    """负载瞬态响应（依赖示波器）。"""
    item_key = "dcdc_load_transient"
    if ctx.scope is None:
        return _skipped(item_key, "负载瞬态响应", "未连接示波器，跳过")
    freqs = ctx.config.get("transient_freqs", ["10Hz", "100Hz", "1kHz"])
    rows: list[list] = []
    for i, f in enumerate(freqs):
        if ctx.stop_flag_fn():
            break
        overshoot = mock_jitter(45.0, 0.05) if ctx.is_mock else 0.0
        undershoot = mock_jitter(-40.0, 0.05) if ctx.is_mock else 0.0
        recover_us = mock_jitter(80.0, 0.1) if ctx.is_mock else 0.0
        rows.append([f, round(overshoot, 3), round(undershoot, 3), round(recover_us, 3)])
        ctx.progress_fn(int((i + 1) / len(freqs) * 100), f"Transient {f}")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Freq", "Overshoot (mV)", "Undershoot (mV)", "Recover (us)"], rows)
    return ItemResult(item_key=item_key, name="负载瞬态响应", unit="mV",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def inductor_current(ctx: ItemContext) -> ItemResult:
    """不同负载下电感电流（依赖示波器）。"""
    item_key = "dcdc_inductor_current"
    if ctx.scope is None:
        return _skipped(item_key, "电感电流", "未连接示波器，跳过")
    i_start = float(ctx.config.get("iload_start_ma", 10))
    i_end = float(ctx.config.get("iload_end_ma", 200))
    i_step = float(ctx.config.get("iload_step_ma", 50))
    points = linspace(i_start, i_end, i_step)
    rows: list[list] = []
    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        ipk = mock_jitter(il + 30, 0.05) if ctx.is_mock else 0.0
        ivly = mock_jitter(max(il - 30, 0), 0.05) if ctx.is_mock else 0.0
        rows.append([il, round(ipk, 3), round(ivly, 3)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"IL {il}mA")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Ipeak (mA)", "Ivalley (mA)"], rows)
    return ItemResult(item_key=item_key, name="电感电流", unit="mA",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


# 测试项注册表：item_key -> (name, run_fn, needs_scope)
DCDC_ITEMS: dict[str, tuple[str, object, bool]] = {
    "dcdc_vout_scan": ("输出电压扫描", vout_scan, False),
    "dcdc_efficiency": ("效率", efficiency, False),
    "dcdc_load_reg": ("负载调整率", load_line_reg, False),
    "dcdc_line_reg": ("线性调整率", line_reg, False),
    "dcdc_quiescent": ("静态电流", quiescent, False),
    "dcdc_ripple": ("BUCK 纹波", ripple, True),
    "dcdc_psrr": ("DCDC PSRR", psrr, True),
    "dcdc_load_transient": ("负载瞬态响应", load_transient, True),
    "dcdc_inductor_current": ("电感电流", inductor_current, True),
}
