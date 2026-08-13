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
    restore_vin, run_line_transient, run_load_capability_ripple,
    run_load_transient, run_vout_scan, set_load_current, settle,
    setup_load_channel, setup_meter_channel, setup_source_channel,
    teardown_load, write_csv,
)
from core.module_test.result_model import ItemResult
from core.module_test.param_spec import (
    ParamSpec, average_cnt, line_transient_groups, load_sweep,
    quiescent_params, reg_scan_params, settle_time, transient_groups,
    vin_bias, vin_sweep, vout_tol,
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
    vin_v = float(cfg.get("vin_v", 3.8))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 3))

    points = linspace(i_start, i_end, i_step)
    rows: list[list[float]] = []
    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch, initial_current_a=max(i_start, 0.001) / 1000.0)

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
    v0 = rows[0][1] if rows else 0.0
    load_reg_pct = (delta / v0 * 100.0) if abs(v0) > 1e-9 else 0.0
    measured = {"points": len(rows), "vout_drop_mv": round(delta, 4),
                "load_reg_mv_per_a": round(delta / max((i_end - i_start) / 1000.0, 1e-6), 4),
                "load_reg_pct": round(load_reg_pct, 4)}
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

    if not ctx.is_mock:
        restore_vin(ctx, vin_ch, float(cfg.get("vin_v", 3.8)))

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Vin (V)", "Vout (mV)"], rows)
    delta = (max(r[1] for r in rows) - min(r[1] for r in rows)) if rows else 0.0
    mean_v = (sum(r[1] for r in rows) / len(rows)) if rows else 0.0
    line_reg_pct = (delta / mean_v * 100.0) if abs(mean_v) > 1e-9 else 0.0
    measured = {"points": len(rows), "vout_span_mv": round(delta, 4),
                "line_reg_pct": round(line_reg_pct, 4)}
    return ItemResult(item_key=item_key, name="Line Regulation", unit="mV",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def quiescent(ctx: ItemContext) -> ItemResult:
    """静态电流（Iq），差分测法（默认工作态单次测量）。

    SOC 场景下不能把 Vin 电流直接当静态电流。测法：
      1. 外供 Vout 源通道 = 实测 Vout + 偏置（默认 +20mV）；
      2. 使能被测 LDO（写 ENABLE 双寄存器 on），记 Vin/Vout 两通道电流；
      3. 关断被测 LDO（写 ENABLE 双寄存器 off），再记 Vin/Vout 两通道电流；
      4. ΔI_vin、ΔI_vout 分列，Iq = ΔI_vin + ΔI_vout。
    未配 ENABLE 寄存器时退化为直接测 Vin 电流。
    """
    from core.module_test.mode_manager import iq_diff_measure, parse_enable_regs

    item_key = "ldo_quiescent"
    cfg = ctx.config
    vin_ch = parse_channel(cfg.get("vin_channel", 1))
    vout_src_ch = parse_channel(cfg.get("vout_channel", 2))
    vin_v = float(cfg.get("vin_v", 3.8))
    vout_nom = float(cfg.get("vout_nominal_mv", 1800)) / 1000.0
    vout_offset = float(cfg.get("iq_vout_offset_mv", 20.0)) / 1000.0
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 5))
    en_regs = parse_enable_regs(cfg)

    if not ctx.is_mock:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)

    header = ["dIvin (uA)", "dIvout (uA)", "Iq (uA)"]
    if en_regs is None:
        ctx.log_fn(f"[{item_key}] 未配置 ENABLE 寄存器，退化为直接测 Vin 电流")
        if ctx.is_mock:
            iq = mock_jitter(80.0, 0.05)
        else:
            settle(ctx, max(settle_s * 4, 0.2))
            iq = measure_avg(ctx, "measure_current", vin_ch,
                             count=avg_cnt, settle_s=settle_s) * 1e6
        row = [round(iq, 3), "", round(iq, 3)]
        ctx.log_fn(f"[{item_key}] (fallback) Ivin={iq:.3f} uA")
    else:
        d = iq_diff_measure(ctx, item_key, vin_ch, vout_src_ch,
                            vout_nom + vout_offset, en_regs, settle_s, avg_cnt,
                            mock_base_ua=80.0)
        row = [d[0], d[1], d[2]]
        ctx.log_fn(f"[{item_key}] dIvin={d[0]} dIvout={d[1]} Iq={d[2]} uA")
        # 关断外供前先把 ENABLE 寄存器还原回测量前状态
        from core.module_test.mode_manager import restore_dut_enable
        restore_dut_enable(ctx, en_regs, d[3])

    if not ctx.is_mock:
        try:
            ctx.n6705c.channel_off(vout_src_ch)  # 关断外供，设 0V 会把 DUT VOUT 拉低
        except Exception:  # noqa: BLE001
            logger.error("channel off vout_src ch%d failed", vout_src_ch, exc_info=True)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, header, [row])
    measured = dict(zip(header, row))
    return ItemResult(item_key=item_key, name="Quiescent Current", unit="uA",
                      passed=None, measured=measured, raw_csv_path=csv_path)


def ripple(ctx: ItemContext) -> ItemResult:
    """Load Capability & Ripple（依赖示波器，逻辑见 _common.run_load_capability_ripple）。

    从起始负载按步进扫到结束负载，逐点测输出电压与纹波并捕获示波器截图。
    """
    return run_load_capability_ripple(ctx, "ldo_ripple", "Load Capability&Ripple",
                                      mock_vpp_base=2.5, mock_rms_base=0.4)


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
    """负载瞬态响应（依赖示波器，逻辑见 _common.run_load_transient）。"""
    return run_load_transient(ctx, "ldo_load_transient", "Load Transient Response",
                              mock_over_mv=30.0, mock_under_mv=25.0)


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

    # dropout_mv: None=到下限仍正常; 0.0=中止未判定; >0=实测压差
    dropout_mv: float | None
    ok_at_min_vin = False
    if ctx.is_mock:
        v0_mv = mock_jitter(nominal_mv, 0.01)
        dropout_mv = mock_jitter(180.0, 0.05)
    else:
        setup_source_channel(ctx, vin_ch, vin_hi, current_limit=0.5)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch, initial_current_a=iload_ma / 1000.0)
        settle(ctx, max(settle_s * 4, 0.2))
        # 在 Vin 上限、加载稳定后实测一次 Vout 作为基准 V0
        v0_mv = measure_avg(ctx, "measure_voltage", vout_ch,
                            count=avg_cnt, settle_s=settle_s, default=nominal_mv / 1000.0) * 1000.0
        ctx.log_fn(f"[{item_key}] V0(基准)={v0_mv:.3f} mV @ Vin={vin_hi:.3f}V")
        # 从高到低扫描 Vin
        vin = vin_hi
        threshold_mv = v0_mv * (1.0 - tol)
        dropout_mv = None
        while vin >= vin_lo - 1e-9:
            if ctx.stop_flag_fn():
                dropout_mv = 0.0  # 中止，标记为未判定
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
            if vin <= vin_lo + 1e-9:  # 到下限仍正常
                ok_at_min_vin = True
            vin -= vin_step
        teardown_load(ctx, iload_ch)
        restore_vin(ctx, vin_ch, float(cfg.get("vin_v", 3.8)))
    if ok_at_min_vin:
        note = f"在最低 Vin={vin_lo:.3f}V 下仍正常输出（压差负载 {iload_ma:g}mA），未触发压差"
    elif dropout_mv is not None and dropout_mv > 0:
        note = f"Dropout={dropout_mv:.3f} mV @ Iload={iload_ma:g}mA"
    else:
        note = "未判定（中止）"
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    dropout_csv = round(dropout_mv, 3) if dropout_mv is not None else ""
    write_csv(csv_path, ["Iload (mA)", "V0 (mV)", "Dropout (mV)"],
              [[iload_ma, round(v0_mv, 3), dropout_csv]])
    ctx.log_fn(f"[{item_key}] Iload={iload_ma}mA V0={v0_mv:.3f}mV -> {note}")
    return ItemResult(item_key=item_key, name="Dropout Voltage", unit="mV",
                      passed=None, measured={"dropout_mv": dropout_csv,
                                             "ok_at_min_vin": ok_at_min_vin,
                                             "vin_lo_v": vin_lo,
                                             "v0_mv": round(v0_mv, 3),
                                             "iload_ma": iload_ma, "vout_nominal_mv": nominal_mv},
                      raw_csv_path=csv_path, notes=note)


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
    vin_v = float(cfg.get("vin_v", 3.8))
    ilim_start = float(cfg.get("ilim_start_ma", 50))
    ilim_end = float(cfg.get("ilim_end_ma", 500))
    ilim_step = float(cfg.get("ilim_step_ma", 20))
    tol = float(cfg.get("vout_tol", 0.02))
    settle_s = float(cfg.get("settle_time_s", 0.05))
    avg_cnt = int(cfg.get("average_cnt", 3))

    rows: list[list] = []
    if ctx.is_mock:
        iset = ilim_start
        while iset <= ilim_end + 1e-9:
            # 模拟 300mA 触发限流，之后 Vout 跌落
            v = nominal_mv if iset < 300 else nominal_mv * (300.0 / iset)
            v = mock_jitter(v, 0.003)
            iout = mock_jitter(min(iset, 400.0), 0.02)
            rows.append([round(iset, 3), round(v, 4), round(iout, 4)])
            iset += ilim_step
        ilim_ma = 300.0
        ipk_ma = max(r[2] for r in rows) if rows else ilim_ma
    else:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=1.0)
        setup_meter_channel(ctx, vout_ch)
        setup_load_channel(ctx, iload_ch, initial_current_a=ilim_start / 1000.0)
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
            rows.append([round(iset, 3), round(v, 4), round(iout, 4)])
            ctx.log_fn(f"[{item_key}] Iset={iset:.1f}mA -> Vout={v:.3f}mV, Iout={iout:.3f}mA")
            if v < threshold_mv:
                ilim_ma = iout
                break
            iset += ilim_step
        teardown_load(ctx, iload_ch)
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iset (mA)", "Vout (mV)", "Iout (mA)"], rows)
    ctx.log_fn(f"[{item_key}] Current limit={ilim_ma:.3f} mA")
    return ItemResult(item_key=item_key, name="Current Limit", unit="mA",
                      passed=None, measured={"current_limit_ma": round(ilim_ma, 3),
                                             "peak_current_ma": round(ipk_ma, 3),
                                             "vout_nominal_mv": nominal_mv},
                      raw_csv_path=csv_path)


def output_noise(ctx: ItemContext) -> ItemResult:
    """输出噪声 FFT 频谱分析（LDO 自身噪声，依赖示波器 MATH FFT 通道）。

    Vin=PS2Q 源上电后，示波器 MATH1 配成对 Vout 输入通道的 FFT 幅度分析
    （中心频率 / 频率范围可在项参数设置），采集稳定后捕获整屏截图作为结果进报告。
    """
    item_key = "ldo_output_noise"
    if ctx.scope is None:
        return _skipped(item_key, "Output Noise", "未连接示波器，跳过")
    cfg = ctx.config
    scope_ch = int(cfg.get("scope_vout_channel", 1))
    center_hz = float(cfg.get("noise_center_freq_khz", 50.0)) * 1e3
    span_hz = float(cfg.get("noise_freq_span_khz", 100.0)) * 1e3
    vin_ch = parse_channel(cfg.get("vin_channel", 2))
    vin_v = float(cfg.get("vin_v", 3.8))

    png_path = None
    if ctx.is_mock:
        ctx.log_fn(f"[{item_key}] [MOCK] FFT center={center_hz / 1e3:g}kHz, "
                   f"span={span_hz / 1e3:g}kHz")
    else:
        setup_source_channel(ctx, vin_ch, vin_v, current_limit=0.5)
        try:
            ctx.scope.set_channel_display(scope_ch, True)
            # 先做 Auto Ripple 通道配置（时基/档位/偏移），FFT 才有正确输入信号
            ctx.scope.set_AutoRipple_test(scope_ch)
            settle(ctx, 0.5)
            ctx.scope.setup_fft_display(scope_ch, center_hz, span_hz,
                                        offset_db=-80.0, scale_db=20.0)
        except Exception:  # noqa: BLE001 - FFT 配置失败降级为仅截图
            logger.error("scope setup_fft_display failed", exc_info=True)
            ctx.log_fn(f"[{item_key}] [WARN] FFT 通道配置失败，直接截取当前屏幕")
        # FFT 频谱需多次采集积累才能算完整，等待足够长再截图
        settle(ctx, 3.0)
        try:
            png = ctx.scope.capture_screen_png()
            if png:
                shot_dir = os.path.join(ctx.out_dir, "screenshots")
                os.makedirs(shot_dir, exist_ok=True)
                png_path = os.path.join(shot_dir, f"{item_key}_fft.png")
                with open(png_path, "wb") as f:
                    f.write(png)
        except Exception:  # noqa: BLE001 - 截图失败不阻断
            logger.error("scope fft capture failed", exc_info=True)
        try:
            ctx.scope.close_fft_display()
        except Exception:  # noqa: BLE001 - 关显示失败不阻断
            logger.error("scope close_fft_display failed", exc_info=True)

    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Center (kHz)", "Span (kHz)"],
              [[round(center_hz / 1e3, 3), round(span_hz / 1e3, 3)]])
    ctx.progress_fn(100, "Output Noise")
    ctx.log_fn(f"[{item_key}] FFT center={center_hz / 1e3:g}kHz, span={span_hz / 1e3:g}kHz"
               + (f", screenshot={png_path}" if png_path else ""))
    measured = {"center_freq_khz": round(center_hz / 1e3, 3),
                "freq_span_khz": round(span_hz / 1e3, 3),
                "scope_channel": scope_ch}
    result = ItemResult(item_key=item_key, name="Output Noise", unit="",
                        passed=None, measured=measured, raw_csv_path=csv_path)
    if png_path:
        result.waveform_png = png_path
    return result


def line_transient(ctx: ItemContext) -> ItemResult:
    """输入瞬态响应（Vin 电压脉冲下的恢复能力，逻辑见 _common.run_line_transient）。"""
    return run_line_transient(ctx, "ldo_line_transient", "Line Transient Response",
                              mock_over_mv=20.0, mock_under_mv=18.0)


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
        *reg_scan_params(),
        settle_time(), average_cnt(),
    )),
    "ldo_load_reg": ("Load Regulation", load_line_reg, False, False, (
        *load_sweep(1.0, 200.0, 10.0),
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
        vin_bias(), average_cnt(5), settle_time(), *quiescent_params(),
    )),
    "ldo_ripple": ("Load Capability&Ripple", ripple, True, False, (
        vin_bias(),
        *load_sweep(0.0, 200.0, 20.0),
        settle_time(), average_cnt(),
    )),
    "ldo_psrr": ("PSRR", psrr, True, False, (
        ParamSpec("psrr_freqs", "PSRR 频点", "text", "1kHz, 10kHz, 100kHz", "",
                  hint="逗号分隔"),
    )),
    "ldo_output_noise": ("Output Noise", output_noise, True, False, (
        vin_bias(),
        ParamSpec("noise_center_freq_khz", "中心频率", "float", 50.0, "kHz",
                  minimum=0.001, maximum=1e6, decimals=3),
        ParamSpec("noise_freq_span_khz", "频率范围", "float", 100.0, "kHz",
                  minimum=0.01, maximum=1e6, decimals=3),
    )),
    "ldo_load_transient": ("Load Transient Response", load_transient, True, False, (
        transient_groups(),
        settle_time(),
    )),
    "ldo_line_transient": ("Line Transient Response", line_transient, True, False, (
        line_transient_groups(),
        ParamSpec("transient_vspan_mv", "预期摆幅", "float", 200.0, "mV",
                  minimum=1.0, maximum=10000.0, decimals=1,
                  hint="示波器量程按此设置"),
        settle_time(),
    )),
    "ldo_protection": ("Protection", protection, False, False, (
        ParamSpec("protection_checks", "检查项", "text", "OCP, SCP, OTP, REVERSE", "",
                  hint="逗号分隔"),
    )),
}
