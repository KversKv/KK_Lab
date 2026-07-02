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


def dropout(ctx: ItemContext) -> ItemResult:
    """压差电压 Dropout（维持稳压所需最小 Vin-Vout）。

    大框架占位：Mock 生成合理数据；真机逐步降低 Vin 直至 Vout 跌出容差，
    记录临界 Vin-Vout。具体扫描与判定后续迭代。
    """
    item_key = "ldo_dropout"
    cfg = ctx.config
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))
    iload_ma = float(cfg.get("dropout_iload_ma", 100))
    if ctx.is_mock:
        dropout_mv = mock_jitter(180.0, 0.05)
    else:
        # TODO(迭代): 逐步降低 Vin，检测 Vout 跌落 2% 临界点
        dropout_mv = 0.0
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Iload (mA)", "Dropout (mV)"], [[iload_ma, round(dropout_mv, 3)]])
    ctx.log_fn(f"[{item_key}] Iload={iload_ma}mA -> Dropout={dropout_mv:.3f} mV")
    return ItemResult(item_key=item_key, name="压差电压", unit="mV",
                      passed=None, measured={"dropout_mv": round(dropout_mv, 3),
                                             "iload_ma": iload_ma, "vout_nominal_mv": nominal_mv},
                      raw_csv_path=csv_path)


def vout_accuracy(ctx: ItemContext) -> ItemResult:
    """输出电压精度（初始精度 / 温漂 / 全范围精度）。

    大框架占位：Mock 生成合理数据；接温箱时按温度点采样计算温漂，
    未接温箱仅测常温初始精度。全范围精度与温漂系数后续迭代。
    """
    item_key = "ldo_vout_accuracy"
    cfg = ctx.config
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))
    vout_ch = parse_channel(cfg.get("vout_channel", 1))
    temps = cfg.get("accuracy_temps", ["25"]) if ctx.chamber is not None else ["25"]
    rows: list[list] = []
    for i, t in enumerate(temps):
        if ctx.stop_flag_fn():
            break
        # TODO(迭代): 接温箱时 set_temperature(t) 并等待稳定
        if ctx.is_mock:
            v = mock_jitter(nominal_mv, 0.005)
        else:
            v = safe_measure(ctx.n6705c, "measure_voltage", vout_ch, nominal_mv) * 1000.0
        err_pct = (v - nominal_mv) / nominal_mv * 100.0
        rows.append([t, round(v, 3), round(err_pct, 4)])
        ctx.progress_fn(int((i + 1) / len(temps) * 100), f"Accuracy {t}C")
        ctx.log_fn(f"[{item_key}] T={t}C -> Vout={v:.3f} mV, err={err_pct:.4f}%")
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Temp (C)", "Vout (mV)", "Error (%)"], rows)
    init_err = rows[0][2] if rows else 0.0
    tempco = 0.0  # TODO(迭代): 多温度点拟合温漂 ppm/C
    return ItemResult(item_key=item_key, name="输出电压精度", unit="%",
                      passed=None, measured={"init_error_pct": init_err, "tempco_ppm_c": tempco,
                                             "rows": rows}, raw_csv_path=csv_path)


def current_limit(ctx: ItemContext) -> ItemResult:
    """输出电流能力 / 限流点（最大负载电流）。

    大框架占位：Mock 生成合理数据；真机逐步加大负载直至 Vout 跌落，
    记录限流触发电流。具体扫描步进与判定后续迭代。
    """
    item_key = "ldo_current_limit"
    cfg = ctx.config
    nominal_mv = float(cfg.get("vout_nominal_mv", 1800))
    if ctx.is_mock:
        ilim_ma = mock_jitter(300.0, 0.05)
    else:
        # TODO(迭代): 递增负载电流，检测 Vout 跌出容差的临界电流
        ilim_ma = 0.0
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Current limit (mA)"], [[round(ilim_ma, 3)]])
    ctx.log_fn(f"[{item_key}] Current limit={ilim_ma:.3f} mA")
    return ItemResult(item_key=item_key, name="输出电流能力", unit="mA",
                      passed=None, measured={"current_limit_ma": round(ilim_ma, 3),
                                             "vout_nominal_mv": nominal_mv},
                      raw_csv_path=csv_path)


def output_noise(ctx: ItemContext) -> ItemResult:
    """输出噪声（LDO 自身噪声，依赖示波器/频谱）。

    大框架占位：Mock 生成合理数据；真机通过示波器/频谱在带宽内积分噪声。
    积分带宽与 RMS 计算后续迭代。
    """
    item_key = "ldo_output_noise"
    if ctx.scope is None:
        return _skipped(item_key, "输出噪声", "未连接示波器，跳过")
    if ctx.is_mock:
        noise_uv_rms = mock_jitter(30.0, 0.1)
    else:
        noise_uv_rms = 0.0  # TODO(迭代): 10Hz~100kHz 带宽积分噪声
    csv_path = os.path.join(ctx.out_dir, f"{item_key}.csv")
    write_csv(csv_path, ["Noise (uVrms)"], [[round(noise_uv_rms, 3)]])
    ctx.log_fn(f"[{item_key}] Output noise={noise_uv_rms:.3f} uVrms")
    return ItemResult(item_key=item_key, name="输出噪声", unit="uVrms",
                      passed=None, measured={"noise_uv_rms": round(noise_uv_rms, 3)},
                      raw_csv_path=csv_path)


def line_transient(ctx: ItemContext) -> ItemResult:
    """输入瞬态响应（Vin 突变时的恢复能力，依赖示波器）。

    大框架占位：Mock 生成合理数据；真机在 Vin 阶跃下捕获 Vout 过冲/恢复时间。
    阶跃幅度与斜率后续迭代。
    """
    item_key = "ldo_line_transient"
    if ctx.scope is None:
        return _skipped(item_key, "输入瞬态响应", "未连接示波器，跳过")
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
    return ItemResult(item_key=item_key, name="输入瞬态响应", unit="mV",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


def stability(ctx: ItemContext) -> ItemResult:
    """稳定性要求（输出电容容量 / ESR / 类型，依赖示波器）。

    大框架占位：Mock 生成合理数据；真机在不同 Cout/ESR 下测相位裕度或瞬态振铃。
    相位裕度测量方法后续迭代。
    """
    item_key = "ldo_stability"
    if ctx.scope is None:
        return _skipped(item_key, "稳定性", "未连接示波器，跳过")
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
    return ItemResult(item_key=item_key, name="稳定性", unit="deg",
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
    return ItemResult(item_key=item_key, name="保护功能", unit="",
                      passed=None, measured={"rows": rows}, raw_csv_path=csv_path)


# 测试项注册表：item_key -> (name, run_fn, needs_scope)
LDO_ITEMS: dict[str, tuple[str, object, bool]] = {
    "ldo_vout_scan": ("输出电压扫描", vout_scan, False),
    "ldo_vout_accuracy": ("输出电压精度", vout_accuracy, False),
    "ldo_load_reg": ("负载调整率", load_line_reg, False),
    "ldo_line_reg": ("线性调整率", line_reg, False),
    "ldo_dropout": ("压差电压", dropout, False),
    "ldo_current_limit": ("输出电流能力", current_limit, False),
    "ldo_quiescent": ("静态电流", quiescent, False),
    "ldo_ripple": ("输出纹波", ripple, True),
    "ldo_psrr": ("电源抑制比", psrr, True),
    "ldo_output_noise": ("输出噪声", output_noise, True),
    "ldo_load_transient": ("负载瞬态响应", load_transient, True),
    "ldo_line_transient": ("输入瞬态响应", line_transient, True),
    "ldo_stability": ("稳定性", stability, True),
    "ldo_protection": ("保护功能", protection, False),
}
