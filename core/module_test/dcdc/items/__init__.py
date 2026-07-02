"""DCDC 测试项实现集合（规划 §2.2）。

复用策略说明：DCDC 效率规划要求可复用 core/pmu_test/dcdc/dcdc_worker.py，
但该 worker 是与 PMU UI 强耦合的 QThread（信号直连控件）。为保持 Module Test
独立可跑且不破坏分层，此处按相同测量原理（Vin/Vout/Iout 同步采样 + η 计算）
重新实现轻量纯函数版，行为一致、无 Qt 依赖。
"""
from __future__ import annotations

import os

from core.module_test._common import (
    ItemContext, linspace, measure_avg, mock_jitter, parse_channel,
    run_vout_scan, set_load_current, settle, setup_load_channel,
    setup_meter_channel, setup_source_channel, teardown_load, write_csv,
)
from core.module_test.result_model import ItemResult
from core.module_test.param_spec import (
    ParamSpec, average_cnt, load_sweep, settle_time, vin_bias, vin_sweep, vout_tol,
)
from log_config import get_logger

logger = get_logger(__name__)


def _skipped(item_key: str, name: str, reason: str) -> ItemResult:
    return ItemResult(item_key=item_key, name=name, passed=None, notes=reason)


def vout_scan(ctx: ItemContext) -> ItemResult:
    """各挡位输出电压扫描（寄存器驱动，逻辑见 _common.run_vout_scan）。"""
    return run_vout_scan(ctx, "dcdc_vout_scan", "Output Voltage Scan")


def efficiency(ctx: ItemContext) -> ItemResult:
    """效率（1~200mA ramp）。

    流程参考 PMU core/pmu_test/dcdc/dcdc_worker.py：
      1. Vin=PS2Q 源、Vout=VMETer、Iload=CCLoad；
      2. 空载测 baseline（去极值均值 Iin_base）；
      3. 逐点拉载（CCLoad 负电流）+ settle + 多次采样均值；
      4. η = Vout·Iout / (Vin·(Iin−Iin_base))；
      5. 收尾负载归零关断。
    """
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
    avg_cnt = int(cfg.get("average_cnt", 3))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    points = linspace(i_start, i_end, i_step)
    rows: list[list] = []

    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)

    # 空载 baseline（扣除源侧自身电流），参考 PMU baseline 逻辑
    if ctx.is_mock:
        iin_base = 0.0
    else:
        set_load_current(ctx, iload_ch, 0.0)
        settle(ctx, max(settle_s * 4, 0.2))
        iin_base = measure_avg(ctx, "measure_current", vin_ch, count=5, settle_s=settle_s)
    ctx.log_fn(f"[{item_key}] baseline Iin={iin_base * 1e6:.3f} uA")

    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            iin = il / 1000.0 * vout_v_nom / vin_v / 0.9  # 假设 90% 效率
            vout = vout_v_nom - il * 0.0005
            eff = (vout * il / 1000.0) / (vin_v * iin) * 100 if iin > 0 else 0
            eff = mock_jitter(min(eff, 95.0), 0.01)
        else:
            set_load_current(ctx, iload_ch, il / 1000.0)
            settle(ctx, settle_s)
            vout = measure_avg(ctx, "measure_voltage", vout_ch, count=avg_cnt, settle_s=settle_s,
                               default=vout_v_nom)
            iout = abs(measure_avg(ctx, "measure_current", iload_ch, count=avg_cnt, settle_s=settle_s))
            iin = measure_avg(ctx, "measure_current", vin_ch, count=avg_cnt, settle_s=settle_s)
            vin_meas = measure_avg(ctx, "measure_voltage", vin_ch, count=avg_cnt, settle_s=settle_s,
                                   default=vin_v)
            denom = vin_meas * max(iin - iin_base, 1e-9)
            eff = (vout * iout) / denom * 100 if denom > 0 else 0
            eff = max(min(eff, 120.0), 0.0)
        rows.append([il, round(vout * 1000.0, 4), round(eff, 3)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Eff {il}mA")
        ctx.log_fn(f"[{item_key}] Iload={il}mA -> η={eff:.3f} %")

    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Vout (mV)", "Efficiency (%)"], rows)
    effs = [r[2] for r in rows]
    measured = {"points": len(rows), "max_eff": round(max(effs), 3) if effs else 0,
                "avg_eff": round(sum(effs) / len(effs), 3) if effs else 0}
    return ItemResult(item_key=item_key, name="Efficiency", unit="%",
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
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vin_v = float(cfg.get("vin_v", 3.7))
    avg_cnt = int(cfg.get("average_cnt", 3))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)
    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            v = nominal_mv - il * 0.01
            v = mock_jitter(v, 0.002)
        else:
            set_load_current(ctx, iload_ch, il / 1000.0)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch, count=avg_cnt, settle_s=settle_s,
                            default=nominal_mv / 1000.0) * 1000.0
        rows.append([il, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Load reg {il}mA")
    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Vout (mV)"], rows)
    delta = (rows[-1][1] - rows[0][1]) if len(rows) >= 2 else 0.0
    measured = {"points": len(rows), "vout_drop_mv": round(delta, 4)}
    return ItemResult(item_key=item_key, name="Load Regulation", unit="mV",
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
    avg_cnt = int(cfg.get("average_cnt", 3))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_start, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
    for i, vin in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            v = nominal_mv + (vin - 3.7) * 0.3
            v = mock_jitter(v, 0.001)
        else:
            try:
                ctx.n6705c.set_voltage(vin_ch, vin)
            except Exception:  # noqa: BLE001
                logger.error("set Vin failed", exc_info=True)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch, count=avg_cnt, settle_s=settle_s,
                            default=nominal_mv / 1000.0) * 1000.0
        rows.append([vin, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Line reg {vin}V")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vin (V)", "Vout (mV)"], rows)
    delta = (max(r[1] for r in rows) - min(r[1] for r in rows)) if rows else 0.0
    measured = {"points": len(rows), "vout_span_mv": round(delta, 4)}
    return ItemResult(item_key=item_key, name="Line Regulation", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def quiescent(ctx: ItemContext) -> ItemResult:
    """静态电流（PWM/BURST/ULP 分模式）。

    流程：Vin=PS2Q 源上电、输出空载（负载归零），逐模式测 Vin 端电流均值。
    模式切换需外部配置芯片寄存器（真机由测试台完成），此处仅逐模式采集 Iin。
    """
    item_key = "dcdc_quiescent"
    cfg = ctx.config
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    modes = cfg.get("iq_modes", ["PWM", "BURST", "ULP"])
    avg_cnt = int(cfg.get("average_cnt", 5))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    rows: list[list] = []

    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_load_channel(ctx, iload_ch)
        set_load_current(ctx, iload_ch, 0.0)  # 空载
        settle(ctx, max(settle_s * 4, 0.2))
    for i, mode in enumerate(modes):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            iq = {"PWM": 200.0, "BURST": 60.0, "ULP": 8.0}.get(mode, 100.0)
            iq = mock_jitter(iq, 0.05)
        else:
            settle(ctx, settle_s)
            iq = measure_avg(ctx, "measure_current", vin_ch, count=avg_cnt, settle_s=settle_s) * 1e6
        rows.append([mode, round(iq, 3)])
        ctx.progress_fn(int((i + 1) / len(modes) * 100), f"Iq {mode}")
        ctx.log_fn(f"[{item_key}] mode={mode} -> Iq={iq:.3f} uA")
    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Mode", "Iq (uA)"], rows)
    measured = {"rows": rows}
    return ItemResult(item_key=item_key, name="Quiescent Current", unit="uA",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def ripple(ctx: ItemContext) -> ItemResult:
    """BUCK 纹波（依赖示波器）。

    流程：Vin=PS2Q 源上电、带额定负载，示波器 AC 耦合测 Vout 纹波，
    调用 set_AutoRipple_test 自动优化档位后读 Vpp / RMS。
    """
    item_key = "dcdc_ripple"
    if ctx.scope is None:
        return _skipped(item_key, "Buck Ripple", "未连接示波器，跳过")
    cfg = ctx.config
    scope_ch = int(cfg.get("scope_vout_channel", 1))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    load_ma = float(cfg.get("ripple_load_ma", 100))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    if ctx.is_mock:
        vpp = mock_jitter(15.0, 0.1)
        rms = mock_jitter(3.0, 0.1)
    else:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_load_channel(ctx, iload_ch)
        set_load_current(ctx, iload_ch, load_ma / 1000.0)
        settle(ctx, max(settle_s * 8, 0.5))
        try:
            ctx.scope.set_AutoRipple_test(scope_ch)
            settle(ctx, 0.3)
            vpp = float(ctx.scope.get_channel_pk2pk(scope_ch)) * 1000.0  # V->mV
            rms = float(ctx.scope.get_channel_rms(scope_ch)) * 1000.0
        except Exception:  # noqa: BLE001
            logger.error("scope ripple read failed", exc_info=True)
            vpp = 0.0
            rms = 0.0
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vpp (mV)", "RMS (mV)"], [[round(vpp, 4), round(rms, 4)]])
    ctx.log_fn(f"[{item_key}] Vpp={vpp:.3f} mV, RMS={rms:.3f} mV")
    return ItemResult(item_key=item_key, name="Buck Ripple", unit="mV",
                      passed=None, measured={"vpp_mv": round(vpp, 4), "rms_mv": round(rms, 4)},
                      raw_csv_path=csv_path)


def psrr(ctx: ItemContext) -> ItemResult:
    """DCDC PSRR（依赖示波器）。"""
    item_key = "dcdc_psrr"
    if ctx.scope is None:
        return _skipped(item_key, "PSRR", "未连接示波器，跳过")
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
    return ItemResult(item_key=item_key, name="PSRR", unit="dB",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def load_transient(ctx: ItemContext) -> ItemResult:
    """负载瞬态响应（依赖示波器）。"""
    item_key = "dcdc_load_transient"
    if ctx.scope is None:
        return _skipped(item_key, "Load Transient Response", "未连接示波器，跳过")
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
    return ItemResult(item_key=item_key, name="Load Transient Response", unit="mV",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def inductor_current(ctx: ItemContext) -> ItemResult:
    """不同负载下电感电流（依赖示波器）。"""
    item_key = "dcdc_inductor_current"
    if ctx.scope is None:
        return _skipped(item_key, "Inductor Current", "未连接示波器，跳过")
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
    return ItemResult(item_key=item_key, name="Inductor Current", unit="mA",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def vin_range(ctx: ItemContext) -> ItemResult:
    """输入电压范围（Vin min/max，能正常稳压的下限/上限）。

    流程（参考 PMU VIN sweep 思路）：Vin=PS2Q 从低到高步进，带轻载，
    逐点测 Vout；当 Vout 首次进入标称容差带记为下限 UVLO，最后一个仍在
    容差带内的 Vin 记为上限。全程 settle + 多次采样均值。
    """
    item_key = "dcdc_vin_range"
    cfg = ctx.config
    vin_lo = float(cfg.get("vin_start_v", 2.5))
    vin_hi = float(cfg.get("vin_end_v", 5.5))
    vin_step = float(cfg.get("vin_step_v", 0.1))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vout_ch = parse_channel(cfg.get("vout_channel", 2))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    nominal_v = float(cfg.get("vout_nominal_mv", 1200)) / 1000.0
    tol = float(cfg.get("vout_tol_ratio", 0.05))  # ±5% 视为有效稳压
    light_load_ma = float(cfg.get("vin_range_load_ma", 10))
    avg_cnt = int(cfg.get("average_cnt", 3))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    points = linspace(vin_lo, vin_hi, vin_step)
    rows: list[list] = []

    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_lo, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)
        set_load_current(ctx, iload_ch, light_load_ma / 1000.0)

    lo_edge = 0.0
    hi_edge = 0.0
    for i, vin in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            # 假设 2.7V 起稳压、5.3V 仍正常
            v = nominal_v if 2.7 <= vin <= 5.3 else nominal_v * (vin / 2.7) * 0.4
            v = mock_jitter(v, 0.003)
        else:
            try:
                ctx.n6705c.set_voltage(vin_ch, vin)
            except Exception:  # noqa: BLE001
                logger.error("set Vin failed", exc_info=True)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch, count=avg_cnt, settle_s=settle_s,
                            default=0.0)
        in_band = abs(v - nominal_v) <= nominal_v * tol
        if in_band:
            if lo_edge == 0.0:
                lo_edge = vin
            hi_edge = vin
        rows.append([round(vin, 4), round(v * 1000.0, 4), "IN" if in_band else "OUT"])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Vin {vin:.2f}V")
        ctx.log_fn(f"[{item_key}] Vin={vin:.3f}V -> Vout={v * 1000:.3f}mV {'IN' if in_band else 'OUT'}")

    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vin (V)", "Vout (mV)", "Regulated"], rows)
    ctx.log_fn(f"[{item_key}] Vin range = {lo_edge:.4f} ~ {hi_edge:.4f} V")
    return ItemResult(item_key=item_key, name="Input Voltage Range", unit="V",
                      passed=None, measured={"vin_min_v": round(lo_edge, 4),
                                             "vin_max_v": round(hi_edge, 4),
                                             "sweep_range_v": [vin_lo, vin_hi]},
                      raw_csv_path=csv_path)


def output_power(ctx: ItemContext) -> ItemResult:
    """输出电流 / 输出功率（Iout、Pout 随负载）。

    流程参考 PMU DCDC worker：Vin=PS2Q 源、Vout=VMETer、Iload=CCLoad，
    逐点拉载 + settle + 多次采样均值，同步测 Vout/Iout 计算 Pout=Vout·Iout。
    """
    item_key = "dcdc_output_power"
    cfg = ctx.config
    i_start = float(cfg.get("iload_start_ma", 1))
    i_end = float(cfg.get("iload_end_ma", 200))
    i_step = float(cfg.get("iload_step_ma", 20))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vout_ch = parse_channel(cfg.get("vout_channel", 2))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1200))
    avg_cnt = int(cfg.get("average_cnt", 3))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    points = linspace(i_start, i_end, i_step)
    rows: list[list] = []
    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)
    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            v = mock_jitter(nominal_mv - il * 0.01, 0.002)
            iout = mock_jitter(il, 0.01)
        else:
            set_load_current(ctx, iload_ch, il / 1000.0)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch, count=avg_cnt, settle_s=settle_s,
                            default=nominal_mv / 1000.0) * 1000.0
            iout = abs(measure_avg(ctx, "measure_current", iload_ch, count=avg_cnt,
                                   settle_s=settle_s)) * 1000.0
        pout_mw = v / 1000.0 * iout  # mV*mA/1000 -> mW
        rows.append([round(iout, 4), round(v, 4), round(pout_mw, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Pout {il}mA")
        ctx.log_fn(f"[{item_key}] Iout={iout:.3f}mA Vout={v:.3f}mV Pout={pout_mw:.3f}mW")
    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iout (mA)", "Vout (mV)", "Pout (mW)"], rows)
    pmax = max((r[2] for r in rows), default=0.0)
    iout_max = max((r[0] for r in rows), default=0.0)
    return ItemResult(item_key=item_key, name="Output Power", unit="mW",
                      passed=None, measured={"points": len(rows), "pout_max_mw": round(pmax, 4),
                                             "iout_max_ma": round(iout_max, 4)},
                      raw_csv_path=csv_path)


def switching_freq(ctx: ItemContext) -> ItemResult:
    """开关频率（固定 / 可调，依赖示波器）。

    流程：Vin=PS2Q 源上电、带额定负载，示波器探 SW 节点，读开关频率。
    """
    item_key = "dcdc_switching_freq"
    if ctx.scope is None:
        return _skipped(item_key, "Switching Frequency", "未连接示波器，跳过")
    cfg = ctx.config
    scope_sw_ch = int(cfg.get("scope_sw_channel", 2))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    load_ma = float(cfg.get("fsw_load_ma", 100))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    if ctx.is_mock:
        fsw_khz = mock_jitter(1200.0, 0.02)
    else:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_load_channel(ctx, iload_ch)
        set_load_current(ctx, iload_ch, load_ma / 1000.0)
        settle(ctx, max(settle_s * 8, 0.5))
        try:
            fsw_khz = float(ctx.scope.get_channel_frequency(scope_sw_ch)) / 1000.0  # Hz->kHz
        except Exception:  # noqa: BLE001
            logger.error("scope Fsw read failed", exc_info=True)
            fsw_khz = 0.0
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Fsw (kHz)"], [[round(fsw_khz, 3)]])
    ctx.log_fn(f"[{item_key}] Fsw = {fsw_khz:.3f} kHz")
    return ItemResult(item_key=item_key, name="Switching Frequency", unit="kHz",
                      passed=None, measured={"fsw_khz": round(fsw_khz, 3)},
                      raw_csv_path=csv_path)


def shutdown_current(ctx: ItemContext) -> ItemResult:
    """待机 / 关断电流（Shutdown current）。

    流程：Vin=PS2Q 源上电、EN 拉低（真机由测试台完成，芯片进入关断），
    输出空载后测 Vin 端电流均值。EN 控制信号后续接入测试台时补自动化。
    """
    item_key = "dcdc_shutdown_current"
    cfg = ctx.config
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vin_v = float(cfg.get("vin_v", 3.7))
    avg_cnt = int(cfg.get("average_cnt", 5))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    if ctx.is_mock:
        ish_ua = mock_jitter(1.5, 0.1)
    else:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.1)
        settle(ctx, max(settle_s * 4, 0.2))
        # EN 拉低须外部完成，此处直接测关断态 Vin 端电流均值
        ish_ua = measure_avg(ctx, "measure_current", vin_ch, count=avg_cnt, settle_s=settle_s) * 1e6
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Shutdown current (uA)"], [[round(ish_ua, 4)]])
    ctx.log_fn(f"[{item_key}] Shutdown current = {ish_ua:.4f} uA")
    return ItemResult(item_key=item_key, name="Standby/Shutdown Current", unit="uA",
                      passed=None, measured={"shutdown_current_ua": round(ish_ua, 4)},
                      raw_csv_path=csv_path)


def current_limit(ctx: ItemContext) -> ItemResult:
    """限流能力（峰值电流 / 过流保护触发点）。

    流程：Vin=PS2Q 源、Vout=VMETer、Iload=CCLoad，负载电流从额定逐步递增，
    每点 settle + 均值测 Vout；当 Vout 首次跌破标称的 (1−tol) 时记为限流点，
    记录该点实测负载电流与到目前为止的峰值输出电流。
    """
    item_key = "dcdc_current_limit"
    cfg = ctx.config
    nominal_mv = float(cfg.get("vout_nominal_mv", 1200))
    nominal_v = nominal_mv / 1000.0
    tol = float(cfg.get("vout_tol_ratio", 0.05))
    i_start = float(cfg.get("ilim_start_ma", 100))
    i_end = float(cfg.get("ilim_end_ma", 800))
    i_step = float(cfg.get("ilim_step_ma", 20))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vout_ch = parse_channel(cfg.get("vout_channel", 2))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    avg_cnt = int(cfg.get("average_cnt", 3))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    points = linspace(i_start, i_end, i_step)
    rows: list[list] = []
    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=1.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)

    ilim_ma = 0.0
    ipk_ma = 0.0
    threshold = nominal_v * (1.0 - tol)
    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            # 假设 500mA 触发限流，之后 Vout 跌落
            v = nominal_v if il < 500 else nominal_v * (500.0 / il)
            v = mock_jitter(v, 0.003)
            iout = mock_jitter(min(il, 650.0), 0.02)
        else:
            set_load_current(ctx, iload_ch, il / 1000.0)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch, count=avg_cnt, settle_s=settle_s,
                            default=0.0)
            iout = abs(measure_avg(ctx, "measure_current", iload_ch, count=avg_cnt,
                                   settle_s=settle_s)) * 1000.0
        ipk_ma = max(ipk_ma, iout)
        rows.append([round(il, 3), round(v * 1000.0, 4), round(iout, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Ilim {il}mA")
        ctx.log_fn(f"[{item_key}] Iset={il}mA Vout={v * 1000:.3f}mV Iout={iout:.3f}mA")
        if v < threshold and ilim_ma == 0.0:
            ilim_ma = iout
            ctx.log_fn(f"[{item_key}] current limit hit @ Iout={iout:.3f}mA")
            break

    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iset (mA)", "Vout (mV)", "Iout (mA)"], rows)
    ctx.log_fn(f"[{item_key}] Ilimit={ilim_ma:.3f} mA, Ipeak={ipk_ma:.3f} mA")
    return ItemResult(item_key=item_key, name="Current Limit", unit="mA",
                      passed=None, measured={"current_limit_ma": round(ilim_ma, 3),
                                             "peak_current_ma": round(ipk_ma, 3),
                                             "vout_nominal_mv": nominal_mv},
                      raw_csv_path=csv_path)


def startup(ctx: ItemContext) -> ItemResult:
    """启动特性（软启动 / 启动时间 / 浪涌电流，依赖示波器）。

    大框架占位：Mock 生成合理数据；真机捕获上电到 Vout 稳定的时间与浪涌峰值。
    触发与测量方法后续迭代。
    """
    item_key = "dcdc_startup"
    if ctx.scope is None:
        return _skipped(item_key, "Startup Behavior", "未连接示波器，跳过")
    if ctx.is_mock:
        soft_start_ms = mock_jitter(1.5, 0.1)
        rise_time_ms = mock_jitter(1.2, 0.1)
        inrush_ma = mock_jitter(400.0, 0.1)
    else:
        soft_start_ms = 0.0  # TODO(迭代): 软启动斜坡时间
        rise_time_ms = 0.0   # TODO(迭代): Vout 10%~90% 上升时间
        inrush_ma = 0.0      # TODO(迭代): 上电浪涌电流峰值
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Soft start (ms)", "Rise time (ms)", "Inrush (mA)"],
              [[round(soft_start_ms, 4), round(rise_time_ms, 4), round(inrush_ma, 3)]])
    ctx.log_fn(f"[{item_key}] soft_start={soft_start_ms:.4f}ms rise={rise_time_ms:.4f}ms "
               f"inrush={inrush_ma:.3f}mA")
    return ItemResult(item_key=item_key, name="Startup Behavior", unit="ms",
                      passed=None, measured={"soft_start_ms": round(soft_start_ms, 4),
                                             "rise_time_ms": round(rise_time_ms, 4),
                                             "inrush_ma": round(inrush_ma, 3)},
                      raw_csv_path=csv_path)


def protection(ctx: ItemContext) -> ItemResult:
    """保护功能（过流 / 短路 / 过压 / 欠压 / 过温）。

    大框架占位：Mock 生成合理数据；真机逐项触发保护并记录动作与恢复。
    各保护触发条件与安全边界后续迭代。
    """
    item_key = "dcdc_protection"
    checks = ctx.config.get("protection_checks", ["OCP", "SCP", "OVP", "UVP", "OTP"])
    rows: list[list] = []
    for i, c in enumerate(checks):
        if ctx.stop_flag_fn():
            break
        # TODO(迭代): 真机逐项触发对应保护，判定动作是否符合预期
        triggered = "YES" if ctx.is_mock else "N/A"
        rows.append([c, triggered])
        ctx.progress_fn(int((i + 1) / len(checks) * 100), f"Protection {c}")
        ctx.log_fn(f"[{item_key}] {c} -> {triggered}")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Protection", "Triggered"], rows)
    return ItemResult(item_key=item_key, name="Protection", unit="",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def topology(ctx: ItemContext) -> ItemResult:
    """拓扑类型（Buck / Boost / Buck-Boost / 隔离-非隔离）。

    流程：拓扑主要为配置项（隔离性、外部拓扑无法纯电测判定），从 config 读取；
    同时实测 Vin/Vout 比值做一次辅助辨识（Vout<Vin→Buck，Vout>Vin→Boost，
    近似相等→Buck-Boost），结果与配置一并记录供报告核对。
    """
    item_key = "dcdc_topology"
    cfg = ctx.config
    topo = str(cfg.get("topology", "Buck"))
    isolated = bool(cfg.get("isolated", False))
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vout_ch = parse_channel(cfg.get("vout_channel", 2))
    vin_v = float(cfg.get("vin_v", 3.7))
    nominal_v = float(cfg.get("vout_nominal_mv", 1200)) / 1000.0
    settle_s = float(cfg.get("settle_time_s", 0.05))

    if ctx.is_mock:
        vin_meas = mock_jitter(vin_v, 0.005)
        vout_meas = mock_jitter(nominal_v, 0.005)
    else:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        settle(ctx, max(settle_s * 4, 0.2))
        vin_meas = measure_avg(ctx, "measure_voltage", vin_ch, count=3, settle_s=settle_s,
                               default=vin_v)
        vout_meas = measure_avg(ctx, "measure_voltage", vout_ch, count=3, settle_s=settle_s,
                                default=nominal_v)
    ratio = vout_meas / vin_meas if vin_meas > 1e-6 else 0.0
    if ratio < 0.9:
        detected = "Buck"
    elif ratio > 1.1:
        detected = "Boost"
    else:
        detected = "Buck-Boost"

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Topology(cfg)", "Isolated", "Detected", "Vout/Vin"],
              [[topo, "YES" if isolated else "NO", detected, round(ratio, 4)]])
    ctx.log_fn(f"[{item_key}] cfg={topo} isolated={isolated} detected={detected} "
               f"(Vout/Vin={ratio:.4f})")
    return ItemResult(item_key=item_key, name="Topology", unit="",
                      passed=None, measured={"topology": topo, "isolated": isolated,
                                             "detected": detected, "vout_vin_ratio": round(ratio, 4)},
                      raw_csv_path=csv_path)


def stability(ctx: ItemContext) -> ItemResult:
    """稳定性与补偿要求（环路稳定 / 外部补偿，依赖示波器）。

    大框架占位：Mock 生成合理数据；真机测环路相位/增益裕度或瞬态振铃评估。
    环路测量方法与补偿参数后续迭代。
    """
    item_key = "dcdc_stability"
    if ctx.scope is None:
        return _skipped(item_key, "Stability & Compensation", "未连接示波器，跳过")
    if ctx.is_mock:
        phase_margin_deg = mock_jitter(55.0, 0.05)
        gain_margin_db = mock_jitter(12.0, 0.05)
    else:
        phase_margin_deg = 0.0  # TODO(迭代): 环路相位裕度
        gain_margin_db = 0.0    # TODO(迭代): 环路增益裕度
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Phase margin (deg)", "Gain margin (dB)"],
              [[round(phase_margin_deg, 3), round(gain_margin_db, 3)]])
    ctx.log_fn(f"[{item_key}] PM={phase_margin_deg:.3f}deg GM={gain_margin_db:.3f}dB")
    return ItemResult(item_key=item_key, name="Stability & Compensation", unit="deg",
                      passed=None, measured={"phase_margin_deg": round(phase_margin_deg, 3),
                                             "gain_margin_db": round(gain_margin_db, 3)},
                      raw_csv_path=csv_path)


# 测试项注册表：item_key -> (name, run_fn, needs_scope, default_checked, params)
DCDC_ITEMS: dict[str, tuple[str, object, bool, bool, tuple[ParamSpec, ...]]] = {
    "dcdc_vin_range": ("Input Voltage Range", vin_range, False, True, (
        *vin_sweep(2.5, 5.5, 0.1),
        ParamSpec("vout_tol_ratio", "输出容差", "float", 0.05, "", maximum=1.0, decimals=4,
                  hint="如 0.05 表示 ±5%"),
        ParamSpec("vin_range_load_ma", "轻载电流", "float", 10.0, "mA", maximum=100000.0),
        average_cnt(), settle_time(),
    )),
    "dcdc_vout_scan": ("Output Voltage Scan", vout_scan, False, True, (
        settle_time(), average_cnt(),
    )),
    "dcdc_output_power": ("Output Power", output_power, False, True, (
        *load_sweep(1.0, 200.0, 20.0),
        vin_bias(), average_cnt(), settle_time(),
    )),
    "dcdc_efficiency": ("Efficiency", efficiency, False, True, (
        *load_sweep(1.0, 200.0, 20.0),
        vin_bias(), average_cnt(), settle_time(),
    )),
    "dcdc_load_reg": ("Load Regulation", load_line_reg, False, True, (
        *load_sweep(1.0, 200.0, 20.0),
        vin_bias(), average_cnt(), settle_time(),
    )),
    "dcdc_line_reg": ("Line Regulation", line_reg, False, True, (
        *vin_sweep(3.2, 4.2, 0.2),
        average_cnt(), settle_time(),
    )),
    "dcdc_quiescent": ("Quiescent Current", quiescent, False, True, (
        vin_bias(), average_cnt(5), settle_time(),
        ParamSpec("iq_modes", "工作模式", "text", "PWM, BURST, ULP", "", hint="逗号分隔"),
    )),
    "dcdc_shutdown_current": ("Standby/Shutdown Current", shutdown_current, False, True, (
        vin_bias(), average_cnt(5), settle_time(),
    )),
    "dcdc_ripple": ("Buck Ripple", ripple, True, True, (
        ParamSpec("scope_vout_channel", "示波器通道", "int", 1, "", minimum=1, maximum=4),
        vin_bias(),
        ParamSpec("ripple_load_ma", "纹波负载", "float", 100.0, "mA", maximum=100000.0),
        settle_time(),
    )),
    "dcdc_psrr": ("PSRR", psrr, True, True, (
        ParamSpec("psrr_freqs", "PSRR 频点", "text", "1kHz, 10kHz, 100kHz", "",
                  base_key="psrr_freqs", hint="逗号分隔"),
    )),
    "dcdc_switching_freq": ("Switching Frequency", switching_freq, True, True, (
        ParamSpec("scope_sw_channel", "SW 通道", "int", 2, "", minimum=1, maximum=4),
        vin_bias(),
        ParamSpec("fsw_load_ma", "测试负载", "float", 100.0, "mA", maximum=100000.0),
        settle_time(),
    )),
    "dcdc_load_transient": ("Load Transient Response", load_transient, True, True, (
        ParamSpec("transient_freqs", "瞬态频率", "text", "10Hz, 100Hz, 1kHz", "",
                  base_key="transient_freqs", hint="逗号分隔"),
    )),
    "dcdc_inductor_current": ("Inductor Current", inductor_current, True, True, (
        *load_sweep(10.0, 200.0, 50.0),
    )),
    "dcdc_current_limit": ("Current Limit", current_limit, False, True, (
        vout_tol("vout_tol_ratio", 0.05),
        ParamSpec("ilim_start_ma", "限流起始", "float", 100.0, "mA", maximum=100000.0),
        ParamSpec("ilim_end_ma", "限流结束", "float", 800.0, "mA", maximum=100000.0),
        ParamSpec("ilim_step_ma", "限流步进", "float", 20.0, "mA", minimum=0.1, maximum=100000.0),
        vin_bias(), average_cnt(), settle_time(),
    )),
    "dcdc_startup": ("Startup Behavior", startup, True, True, ()),
    "dcdc_protection": ("Protection", protection, False, True, (
        ParamSpec("protection_checks", "检查项", "text", "OCP, SCP, OVP, UVP, OTP", "",
                  hint="逗号分隔"),
    )),
    "dcdc_topology": ("Topology", topology, False, True, (
        ParamSpec("topology", "拓扑", "text", "Buck", "", hint="如 Buck / Boost / Buck-Boost"),
        vin_bias(), settle_time(),
    )),
    "dcdc_stability": ("Stability & Compensation", stability, True, True, ()),
}
