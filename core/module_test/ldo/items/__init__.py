"""LDO 测试项实现集合（规划 §2.1）。

每个 item 为 ``run(ctx) -> ItemResult`` 纯逻辑函数：
  - n6705c 项：测量真实电压/电流；Mock 模式生成合理假数据。
  - scope 项：未接示波器时返回跳过结果（passed=None），不报错。
所有 item 禁阻塞 UI（由 runner 在 QThread 调用），禁裸 except。
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
    return run_vout_scan(ctx, "ldo_vout_scan", "Output Voltage Scan")


def load_line_reg(ctx: ItemContext) -> ItemResult:
    """负载调整率（1~200mA 扫描）。"""
    item_key = "ldo_load_reg"
    cfg = ctx.config
    i_start = float(cfg.get("iload_start_ma", 1))
    i_end = float(cfg.get("iload_end_ma", 200))
    i_step = float(cfg.get("iload_step_ma", 20))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    vin_ch = parse_channel(cfg.get("vin_channel", 2))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))
    vin_v = float(cfg.get("vin_v", 3.7))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 3))

    points = linspace(i_start, i_end, i_step)
    rows: list[list[float]] = []
    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)

    for i, il in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            v = nominal_mv - il * 0.02  # 轻微跌落
            v = mock_jitter(v, 0.002)
        else:
            set_load_current(ctx, iload_ch, il / 1000.0)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch,
                            count=avg_cnt, settle_s=settle_s, default=nominal_mv / 1000.0) * 1000.0
        rows.append([il, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Load reg {il}mA")
        ctx.log_fn(f"[{item_key}] Iload={il}mA -> Vout={v:.4f} mV")
    if not ctx.is_mock:
        teardown_load(ctx, iload_ch)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Vout (mV)"], rows)
    delta = (rows[-1][1] - rows[0][1]) if len(rows) >= 2 else 0.0
    measured = {"points": len(rows), "vout_drop_mv": round(delta, 4),
                "load_reg_mv_per_a": round(delta / max((i_end - i_start) / 1000.0, 1e-6), 4)}
    return ItemResult(item_key=item_key, name="Load Regulation", unit="mV",
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
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 3))

    points = linspace(vin_start, vin_end, vin_step)
    rows: list[list[float]] = []
    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_start, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)

    for i, vin in enumerate(points):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            v = nominal_mv + (vin - 3.7) * 0.5  # 微弱跟随
            v = mock_jitter(v, 0.001)
        else:
            try:
                ctx.n6705c.set_voltage(vin_ch, vin)
            except Exception:  # noqa: BLE001
                logger.error("set Vin failed", exc_info=True)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch,
                            count=avg_cnt, settle_s=settle_s, default=nominal_mv / 1000.0) * 1000.0
        rows.append([vin, round(v, 4)])
        ctx.progress_fn(int((i + 1) / len(points) * 100), f"Line reg {vin}V")
        ctx.log_fn(f"[{item_key}] Vin={vin}V -> Vout={v:.4f} mV")

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vin (V)", "Vout (mV)"], rows)
    delta = (max(r[1] for r in rows) - min(r[1] for r in rows)) if rows else 0.0
    measured = {"points": len(rows), "vout_span_mv": round(delta, 4)}
    return ItemResult(item_key=item_key, name="Line Regulation", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def quiescent(ctx: ItemContext) -> ItemResult:
    """静态电流（Iq）。"""
    item_key = "ldo_quiescent"
    cfg = ctx.config
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vin_v = float(cfg.get("vin_v", 3.7))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    modes = cfg.get("iq_modes", ["NORMAL", "SLEEP"])
    rows: list[list] = []
    if not ctx.is_mock:
        # 空载测静态电流：源上电、不接负载
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
    for i, mode in enumerate(modes):
        if ctx.stop_flag_fn():
            break
        if ctx.is_mock:
            iq = 5.0 if mode == "SLEEP" else 80.0
            iq = mock_jitter(iq, 0.05)
        else:
            # 注：工作模式切换由寄存器外部设置，此处稳定后测源侧输入电流
            settle(ctx, max(settle_s * 4, 0.2))
            iq = measure_avg(ctx, "measure_current", vin_ch,
                             count=5, settle_s=settle_s, default=0.0) * 1e6  # A -> uA
        rows.append([mode, round(iq, 3)])
        ctx.progress_fn(int((i + 1) / len(modes) * 100), f"Iq {mode}")
        ctx.log_fn(f"[{item_key}] mode={mode} -> Iq={iq:.3f} uA")

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Mode", "Iq (uA)"], rows)
    measured = {"rows": rows}
    return ItemResult(item_key=item_key, name="Quiescent Current", unit="uA",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def ripple(ctx: ItemContext) -> ItemResult:
    """输出纹波（依赖示波器）。

    流程：Vin=PS2Q 源上电、带额定负载，示波器 AC 耦合测 Vout 纹波，
    调用 set_AutoRipple_test 自动优化档位后读 Vpp / RMS。
    """
    item_key = "ldo_ripple"
    if ctx.scope is None:
        return _skipped(item_key, "Output Ripple", "未连接示波器，跳过")
    cfg = ctx.config
    scope_ch = int(cfg.get("scope_vout_channel", 1))
    vin_ch = parse_channel(cfg.get("vin_channel", 2))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    load_ma = float(cfg.get("ripple_load_ma", 100))
    settle_s = float(cfg.get("settle_time_s", 0.05))

    if ctx.is_mock:
        vpp = mock_jitter(2.5, 0.1)
        rms = mock_jitter(0.4, 0.1)
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
    return ItemResult(item_key=item_key, name="Output Ripple", unit="mV",
                      passed=None, measured={"vpp_mv": round(vpp, 4), "rms_mv": round(rms, 4)},
                      raw_csv_path=csv_path)


def psrr(ctx: ItemContext) -> ItemResult:
    """电源抑制比（依赖示波器）。"""
    item_key = "ldo_psrr"
    if ctx.scope is None:
        return _skipped(item_key, "PSRR", "未连接示波器，跳过")
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
    return ItemResult(item_key=item_key, name="PSRR", unit="dB",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def load_transient(ctx: ItemContext) -> ItemResult:
    """负载瞬态响应（依赖示波器）。"""
    item_key = "ldo_load_transient"
    if ctx.scope is None:
        return _skipped(item_key, "Load Transient Response", "未连接示波器，跳过")
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
    return ItemResult(item_key=item_key, name="Load Transient Response", unit="mV",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def dropout(ctx: ItemContext) -> ItemResult:
    """压差电压 Dropout（维持稳压所需最小 Vin-Vout）。

    流程：Vin=PS2Q 源、带固定负载，先在 Vin 上限、加载稳定后实测 Vout 作为基准 V0，
    再从 Vin 上限逐步降低，当 Vout 跌出容差（低于 V0*(1-tol)）时，记录此时的 Vin-Vout 即为压差。
    """
    item_key = "ldo_dropout"
    cfg = ctx.config
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))
    iload_ma = float(cfg.get("dropout_iload_ma", 100))
    vin_ch = parse_channel(cfg.get("vin_channel", 2))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_hi = float(cfg.get("dropout_vin_hi_v", nominal_mv / 1000.0 + 1.0))
    vin_lo = float(cfg.get("dropout_vin_lo_v", nominal_mv / 1000.0))
    vin_step = float(cfg.get("dropout_vin_step_v", 0.02))
    tol = float(cfg.get("vout_tol", 0.02))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 3))

    if ctx.is_mock:
        v0_mv = mock_jitter(nominal_mv, 0.01)
        dropout_mv = mock_jitter(180.0, 0.05)
    else:
        setup_source_channel(ctx, vin_ch, vin_hi, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)
        set_load_current(ctx, iload_ch, iload_ma / 1000.0)
        settle(ctx, max(settle_s * 4, 0.2))
        # 在 Vin 上限、加载稳定后实测一次 Vout 作为基准 V0
        v0_mv = measure_avg(ctx, "measure_voltage", vout_ch,
                            count=avg_cnt, settle_s=settle_s, default=nominal_mv / 1000.0) * 1000.0
        ctx.log_fn(f"[{item_key}] V0(基准)={v0_mv:.3f} mV @ Vin={vin_hi:.3f}V")
        # 从高到低扫描 Vin
        vin = vin_hi
        threshold_mv = v0_mv * (1.0 - tol)
        dropout_mv = 0.0
        while vin >= vin_lo - 1e-9:
            if ctx.stop_flag_fn():
                break
            try:
                ctx.n6705c.set_voltage(vin_ch, vin)
            except Exception:  # noqa: BLE001
                logger.error("set Vin failed", exc_info=True)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch,
                            count=avg_cnt, settle_s=settle_s, default=nominal_mv / 1000.0) * 1000.0
            ctx.log_fn(f"[{item_key}] Vin={vin:.3f}V -> Vout={v:.3f} mV")
            if v < threshold_mv:
                dropout_mv = max(vin * 1000.0 - v, 0.0)
                break
            vin -= vin_step
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "V0 (mV)", "Dropout (mV)"],
              [[iload_ma, round(v0_mv, 3), round(dropout_mv, 3)]])
    ctx.log_fn(f"[{item_key}] Iload={iload_ma}mA V0={v0_mv:.3f}mV -> Dropout={dropout_mv:.3f} mV")
    return ItemResult(item_key=item_key, name="Dropout Voltage", unit="mV",
                      passed=None, measured={"dropout_mv": round(dropout_mv, 3),
                                             "v0_mv": round(v0_mv, 3),
                                             "iload_ma": iload_ma, "vout_nominal_mv": nominal_mv},
                      raw_csv_path=csv_path)


def vout_accuracy(ctx: ItemContext) -> ItemResult:
    """输出电压精度（初始精度 / 温漂 / 全范围精度）。

    流程：Vin=PS2Q 源、Vout 电压表。接温箱时逐温度点 set_temperature 并等待稳定，
    每点测 Vout 与偏差；多温度点线性拟合温漂系数 (ppm/C)。未接温箱仅测常温初始精度。
    """
    item_key = "ldo_vout_accuracy"
    cfg = ctx.config
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    vin_ch = parse_channel(cfg.get("vin_channel", 2))
    vin_v = float(cfg.get("vin_v", 3.7))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 3))
    temp_soak_s = float(cfg.get("temp_soak_s", 60.0))
    temps = cfg.get("accuracy_temps", ["-40", "25", "85"]) if ctx.chamber is not None else ["25"]
    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
    rows: list[list] = []
    for i, t in enumerate(temps):
        if ctx.stop_flag_fn():
            break
        if not ctx.is_mock and ctx.chamber is not None:
            try:
                ctx.chamber.set_temperature(float(t))
            except Exception:  # noqa: BLE001
                logger.error("set_temperature failed", exc_info=True)
            settle(ctx, temp_soak_s)  # 等待温度稳定
        if ctx.is_mock:
            v = mock_jitter(nominal_mv, 0.005)
        else:
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch,
                            count=avg_cnt, settle_s=settle_s, default=nominal_mv / 1000.0) * 1000.0
        err_pct = (v - nominal_mv) / nominal_mv * 100.0
        rows.append([t, round(v, 3), round(err_pct, 4)])
        ctx.progress_fn(int((i + 1) / len(temps) * 100), f"Accuracy {t}C")
        ctx.log_fn(f"[{item_key}] T={t}C -> Vout={v:.3f} mV, err={err_pct:.4f}%")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Temp (C)", "Vout (mV)", "Error (%)"], rows)
    # 找常温（25C）作为初始精度基准
    init_err = next((r[2] for r in rows if str(r[0]) == "25"), rows[0][2] if rows else 0.0)
    # 多温度点线性拟合温漂：ppm/C = (dVout/dT)/nominal * 1e6
    tempco = 0.0
    if len(rows) >= 2:
        try:
            xs = [float(r[0]) for r in rows]
            ys = [float(r[1]) for r in rows]
            n = len(xs)
            mx = sum(xs) / n
            my = sum(ys) / n
            denom = sum((x - mx) ** 2 for x in xs)
            if denom > 1e-12:
                slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom  # mV/C
                tempco = slope / nominal_mv * 1e6  # ppm/C
        except Exception:  # noqa: BLE001
            logger.error("tempco fit failed", exc_info=True)
    return ItemResult(item_key=item_key, name="Output Voltage Accuracy", unit="%",
                      passed=None, measured={"init_error_pct": round(init_err, 4),
                                             "tempco_ppm_c": round(tempco, 3),
                                             "rows": rows}, raw_csv_path=csv_path)


def current_limit(ctx: ItemContext) -> ItemResult:
    """输出电流能力 / 限流点（最大负载电流）。

    流程：Vin=PS2Q 源、Vout 电压表、CCLoad 负载从起始电流递增拉载，
    当 Vout 首次跌出容差（低于 nominal*(1-tol)）时记录该电流为限流点，同时追踪峰值电流。
    """
    item_key = "ldo_current_limit"
    cfg = ctx.config
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))
    vin_ch = parse_channel(cfg.get("vin_channel", 2))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    iload_ch = parse_channel(cfg.get("iload_channel", 3))
    vin_v = float(cfg.get("vin_v", 3.7))
    ilim_start = float(cfg.get("ilim_start_ma", 50))
    ilim_end = float(cfg.get("ilim_end_ma", 500))
    ilim_step = float(cfg.get("ilim_step_ma", 20))
    tol = float(cfg.get("vout_tol", 0.02))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 3))

    if ctx.is_mock:
        ilim_ma = mock_jitter(300.0, 0.05)
        ipk_ma = ilim_ma
    else:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=1.0)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch)
        threshold_mv = nominal_mv * (1.0 - tol)
        ilim_ma = 0.0
        ipk_ma = 0.0
        iset = ilim_start
        while iset <= ilim_end + 1e-9:
            if ctx.stop_flag_fn():
                break
            set_load_current(ctx, iload_ch, iset / 1000.0)
            settle(ctx, settle_s)
            v = measure_avg(ctx, "measure_voltage", vout_ch,
                            count=avg_cnt, settle_s=settle_s, default=nominal_mv / 1000.0) * 1000.0
            iout = abs(measure_avg(ctx, "measure_current", iload_ch,
                                   count=avg_cnt, settle_s=settle_s, default=0.0)) * 1000.0
            ipk_ma = max(ipk_ma, iout)
            ctx.log_fn(f"[{item_key}] Iset={iset:.1f}mA -> Vout={v:.3f}mV, Iout={iout:.3f}mA")
            if v < threshold_mv:
                ilim_ma = iout
                break
            iset += ilim_step
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Current limit (mA)", "Peak current (mA)"],
              [[round(ilim_ma, 3), round(ipk_ma, 3)]])
    ctx.log_fn(f"[{item_key}] Current limit={ilim_ma:.3f} mA")
    return ItemResult(item_key=item_key, name="Current Limit", unit="mA",
                      passed=None, measured={"current_limit_ma": round(ilim_ma, 3),
                                             "peak_current_ma": round(ipk_ma, 3),
                                             "vout_nominal_mv": nominal_mv},
                      raw_csv_path=csv_path)


def output_noise(ctx: ItemContext) -> ItemResult:
    """输出噪声（LDO 自身噪声，依赖示波器/频谱）。

    大框架占位：Mock 生成合理数据；真机通过示波器/频谱在带宽内积分噪声。
    积分带宽与 RMS 计算后续迭代。
    """
    item_key = "ldo_output_noise"
    if ctx.scope is None:
        return _skipped(item_key, "Output Noise", "未连接示波器，跳过")
    if ctx.is_mock:
        noise_uv_rms = mock_jitter(30.0, 0.1)
    else:
        noise_uv_rms = 0.0  # TODO(迭代): 10Hz~100kHz 带宽积分噪声
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Noise (uVrms)"], [[round(noise_uv_rms, 3)]])
    ctx.log_fn(f"[{item_key}] Output noise={noise_uv_rms:.3f} uVrms")
    return ItemResult(item_key=item_key, name="Output Noise", unit="uVrms",
                      passed=None, measured={"noise_uv_rms": round(noise_uv_rms, 3)},
                      raw_csv_path=csv_path)


def line_transient(ctx: ItemContext) -> ItemResult:
    """输入瞬态响应（Vin 突变时的恢复能力，依赖示波器）。

    大框架占位：Mock 生成合理数据；真机在 Vin 阶跃下捕获 Vout 过冲/恢复时间。
    阶跃幅度与斜率后续迭代。
    """
    item_key = "ldo_line_transient"
    if ctx.scope is None:
        return _skipped(item_key, "Line Transient Response", "未连接示波器，跳过")
    steps = ctx.config.get("line_transient_steps", ["3.2->4.2V", "4.2->3.2V"])
    rows: list[list] = []
    for i, s in enumerate(steps):
        if ctx.stop_flag_fn():
            break
        overshoot = mock_jitter(20.0, 0.05) if ctx.is_mock else 0.0
        undershoot = mock_jitter(-18.0, 0.05) if ctx.is_mock else 0.0
        recover_us = mock_jitter(40.0, 0.1) if ctx.is_mock else 0.0
        rows.append([s, round(overshoot, 3), round(undershoot, 3), round(recover_us, 3)])
        ctx.progress_fn(int((i + 1) / len(steps) * 100), f"Line transient {s}")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Step", "Overshoot (mV)", "Undershoot (mV)", "Recover (us)"], rows)
    return ItemResult(item_key=item_key, name="Line Transient Response", unit="mV",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def stability(ctx: ItemContext) -> ItemResult:
    """稳定性要求（输出电容容量 / ESR / 类型，依赖示波器）。

    大框架占位：Mock 生成合理数据；真机在不同 Cout/ESR 下测相位裕度或瞬态振铃。
    相位裕度测量方法后续迭代。
    """
    item_key = "ldo_stability"
    if ctx.scope is None:
        return _skipped(item_key, "Stability", "未连接示波器，跳过")
    cfg = ctx.config
    cout_uf = float(cfg.get("stability_cout_uf", 1.0))
    esr_mohm = float(cfg.get("stability_esr_mohm", 50.0))
    if ctx.is_mock:
        phase_margin_deg = mock_jitter(60.0, 0.05)
    else:
        phase_margin_deg = 0.0  # TODO(迭代): 环路相位裕度 / 瞬态振铃评估
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Cout (uF)", "ESR (mohm)", "Phase margin (deg)"],
              [[cout_uf, esr_mohm, round(phase_margin_deg, 3)]])
    ctx.log_fn(f"[{item_key}] Cout={cout_uf}uF ESR={esr_mohm}mohm -> PM={phase_margin_deg:.3f} deg")
    return ItemResult(item_key=item_key, name="Stability", unit="deg",
                      passed=None, measured={"cout_uf": cout_uf, "esr_mohm": esr_mohm,
                                             "phase_margin_deg": round(phase_margin_deg, 3)},
                      raw_csv_path=csv_path)


def protection(ctx: ItemContext) -> ItemResult:
    """保护功能（限流 / 短路 / 过温 / 反灌保护）。

    大框架占位：Mock 生成合理数据；真机逐项触发保护并记录动作与恢复。
    各保护触发条件与安全边界后续迭代。
    """
    item_key = "ldo_protection"
    checks = ctx.config.get("protection_checks", ["OCP", "SCP", "OTP", "REVERSE"])
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


# 测试项注册表：item_key -> (name, run_fn, needs_scope, default_checked, params)
LDO_ITEMS: dict[str, tuple[str, object, bool, bool, tuple[ParamSpec, ...]]] = {
    "ldo_vout_scan": ("Output Voltage Scan", vout_scan, False, False, (
        settle_time(), average_cnt(),
    )),
    "ldo_load_reg": ("Load Regulation", load_line_reg, False, False, (
        *load_sweep(1.0, 200.0, 20.0),
        vin_bias(), settle_time(), average_cnt(),
    )),
    "ldo_line_reg": ("Line Regulation", line_reg, False, False, (
        *vin_sweep(3.2, 4.2, 0.2),
        settle_time(), average_cnt(),
    )),
    "ldo_dropout": ("Dropout Voltage", dropout, False, False, (
        ParamSpec("dropout_iload_ma", "压差负载", "float", 100.0, "mA", maximum=100000.0),
        ParamSpec("dropout_vin_hi_v", "Vin 上限", "float", 3.0, "V", maximum=60.0),
        ParamSpec("dropout_vin_lo_v", "Vin 下限", "float", 1.8, "V", maximum=60.0),
        ParamSpec("dropout_vin_step_v", "Vin 步进", "float", 0.02, "V", minimum=0.001, maximum=60.0),
        vout_tol(), settle_time(), average_cnt(),
    )),
    "ldo_current_limit": ("Current Limit", current_limit, False, False, (
        vin_bias(),
        ParamSpec("ilim_start_ma", "限流起始", "float", 50.0, "mA", maximum=100000.0),
        ParamSpec("ilim_end_ma", "限流结束", "float", 500.0, "mA", maximum=100000.0),
        ParamSpec("ilim_step_ma", "限流步进", "float", 20.0, "mA", minimum=0.1, maximum=100000.0),
        vout_tol(), settle_time(), average_cnt(),
    )),
    "ldo_quiescent": ("Quiescent Current", quiescent, False, False, (
        vin_bias(), settle_time(),
        ParamSpec("iq_modes", "工作模式", "text", "NORMAL, SLEEP", "",
                  hint="逗号分隔，如 NORMAL, SLEEP"),
    )),
    "ldo_ripple": ("Output Ripple", ripple, True, False, (
        ParamSpec("scope_vout_channel", "示波器通道", "int", 1, "", minimum=1, maximum=4),
        vin_bias(),
        ParamSpec("ripple_load_ma", "纹波负载", "float", 100.0, "mA", maximum=100000.0),
        settle_time(),
    )),
    "ldo_psrr": ("PSRR", psrr, True, False, (
        ParamSpec("psrr_freqs", "PSRR 频点", "text", "1kHz, 10kHz, 100kHz", "",
                  base_key="psrr_freqs", hint="逗号分隔"),
    )),
    "ldo_output_noise": ("Output Noise", output_noise, True, False, ()),
    "ldo_load_transient": ("Load Transient Response", load_transient, True, False, (
        ParamSpec("transient_freqs", "瞬态频率", "text", "10Hz, 100Hz, 1kHz", "",
                  base_key="transient_freqs", hint="逗号分隔"),
    )),
    "ldo_line_transient": ("Line Transient Response", line_transient, True, False, (
        ParamSpec("line_transient_steps", "阶跃序列", "text", "3.2->4.2V, 4.2->3.2V", "",
                  hint="逗号分隔，如 3.2->4.2V"),
    )),
    "ldo_stability": ("Stability", stability, True, False, (
        ParamSpec("stability_cout_uf", "输出电容", "float", 1.0, "uF", maximum=10000.0),
        ParamSpec("stability_esr_mohm", "ESR", "float", 50.0, "mΩ", maximum=100000.0),
    )),
    "ldo_protection": ("Protection", protection, False, False, (
        ParamSpec("protection_checks", "检查项", "text", "OCP, SCP, OTP, REVERSE", "",
                  hint="逗号分隔"),
    )),
    "ldo_vout_accuracy": ("Output Voltage Accuracy", vout_accuracy, False, False, (
        vin_bias(), settle_time(), average_cnt(),
        ParamSpec("temp_soak_s", "温度稳定时间", "float", 60.0, "s", maximum=3600.0),
        ParamSpec("accuracy_temps", "温度点", "text", "-40, 25, 85", "",
                  hint="逗号分隔，接温箱生效"),
    )),
}
