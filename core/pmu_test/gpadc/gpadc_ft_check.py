# -*- coding: utf-8 -*-
"""GPADC FT Calibration Check（两点 FT 校准检查）流程纯函数。

无 Qt、无仪器依赖：所有副作用（扫压 / IIC 采样 / UART 采样 / 日志 / 状态 /
停止 / 进度）全部经回调注入，UI 层仅做装配，pytest 可直测。

两种检查方式：
- IIC：先在两个校准电压点实时采样 GPADC raw，与用户提供的校准码比对
  （容差 raw_tol_lsb）；再用用户两点解出 K/B（code = K*V + B），对用户设定
  的输入电压遍历范围逐点采样并校准，评估校准电压与施加电压的误差。
- UART：DUT 内部已带校准，逐点从日志解析 raw/volt，校验 volt 与施加电压
  的误差，同时用用户两点 K/B 反推电压校验与 DUT volt 的一致性。
"""

import time

from .gpadc_analysis import assess_ft_errors, solve_ft_kb


def run_ft_calib_check(
    mode,
    calib_p1,
    calib_p2,
    raw_tol_lsb=10.0,
    err_limit_mv=10.0,
    divider_ratio=1.0,
    voltage_min=0.1,
    voltage_max=1.8,
    voltage_step=0.05,
    sample_cnt=1000,
    set_voltage_fn=None,
    sample_iic_fn=None,
    sample_uart_fn=None,
    settle_s=0.5,
    step_s=0.2,
    log_fn=None,
    status_fn=None,
    stop_check=None,
    progress_callback=None,
):
    """执行 FT Calibration Check，返回结果 dict；用户提前停止且无数据时返回 None。

    mode: 'IIC' | 'UART'
    calib_p1/calib_p2: (电压 V, 校准码 LSB)，两点电压不可相同；电压为 DUT 引脚
        电压（FT 标称值），IIC 确认时源输出自动按分压比折算（源 = 点 / 比值）。
    divider_ratio: 外部分压比 = DUT 引脚电压 / 源设定电压，默认 1（无分压）。
        扫压 Start/End/Step 为源设定电压，误差评估按 设定 × 比值 的实际电压。
    set_voltage_fn(v): N6705C 施加电压（V，源设定值）。
    sample_iic_fn(cnt, stop_check) -> (avg, max, min): IIC 实时采样 GPADC raw。
    sample_uart_fn(cnt, stop_check) -> (raw_avg, volt_avg): UART 日志解析
        raw/volt 对的截尾均值（volt 单位 mV）。
    """
    log = log_fn or (lambda msg: None)
    status = status_fn or (lambda msg, is_err=False: None)
    stopped = lambda: bool(stop_check and stop_check())

    mode = str(mode).upper()
    if mode not in ('IIC', 'UART'):
        raise ValueError(f"未知 FT 检查方式: {mode}")
    if set_voltage_fn is None:
        raise ValueError("缺少 set_voltage_fn（FT 检查需要 N6705C 扫压）")
    if divider_ratio <= 0:
        raise ValueError("分压比必须为正数")

    (v1, c1), (v2, c2) = sorted((tuple(calib_p1), tuple(calib_p2)), key=lambda p: p[0])
    k, b = solve_ft_kb(v1, c1, v2, c2)

    log(f"===== FT CALIBRATION CHECK ({mode}) =====")
    log(f"[INFO] 校准点: P1=({v1:.3f} V, {c1:.1f} LSB), P2=({v2:.3f} V, {c2:.1f} LSB)")
    log(f"[INFO] 由用户两点解得 K={k:.4f} LSB/V, B={b:.2f} LSB")
    log(f"[INFO] 误差限 ±{err_limit_mv:.1f} mV, 校准码容差 ±{raw_tol_lsb:.1f} LSB, "
        f"每点采样 {sample_cnt} 次, 分压比={divider_ratio:g}")
    if divider_ratio != 1.0:
        log("[INFO] 外部分压生效：DUT 实际电压 = 源设定 × 分压比；"
            "校准点确认时源输出 = 点电压 / 分压比")

    # 扫描点清单（与 Force Voltage 同语义：含端点，末点容差半步）
    sweep_voltages = []
    v = voltage_min
    while v <= voltage_max + voltage_step * 0.001:
        sweep_voltages.append(round(v, 6))
        v = round(v + voltage_step, 6)
    if not sweep_voltages:
        raise ValueError("电压遍历范围为空，请检查 Start/End/Step 配置")

    n_sweep = len(sweep_voltages)
    point_checks = []
    done = 0
    # IIC 方式先做两点确认，进度分母 +2
    total = n_sweep + (2 if mode == 'IIC' else 0)

    def _tick():
        nonlocal done
        done += 1
        if progress_callback:
            progress_callback(int(done * 100 / total))

    # ------------------------------------------------------------------
    # IIC 第一步：校准点确认（实时采样值 vs 用户校准码）
    # ------------------------------------------------------------------
    if mode == 'IIC':
        if sample_iic_fn is None:
            raise ValueError("IIC 方式缺少 sample_iic_fn")
        log("[INFO] 第一步：校准点确认（IIC 实时采样 vs 用户校准码）")
        status("FT Check: 校准点确认中...")
        first = True
        for v_pt, c_pt in ((v1, c1), (v2, c2)):
            if stopped():
                log("[INFO] FT Calibration Check 已被用户停止")
                return None
            # 校准点电压为 DUT 引脚电压（FT 标称值），源输出按分压比折算
            v_set = v_pt / divider_ratio
            set_voltage_fn(v_set)
            time.sleep(settle_s if first else step_s)
            first = False
            avg, _, _ = sample_iic_fn(sample_cnt, stop_check)
            dev = avg - c_pt
            ok = abs(dev) <= raw_tol_lsb
            point_checks.append({
                'voltage': v_pt,
                'set_voltage': v_set,
                'calib_code': c_pt,
                'measured': avg,
                'dev_lsb': dev,
                'passed': ok,
            })
            src_note = f"（源={v_set:.3f} V）" if divider_ratio != 1.0 else ""
            log(f"[CHECK] V={v_pt:.3f}{src_note} 校准码={c_pt:.1f} 实测={avg:.2f} "
                f"偏差={dev:+.2f} LSB → {'PASS' if ok else 'FAIL'}")
            _tick()

    if mode == 'UART' and sample_uart_fn is None:
        raise ValueError("UART 方式缺少 sample_uart_fn")

    # ------------------------------------------------------------------
    # 第二步：遍历电压范围，评估校准结果
    # ------------------------------------------------------------------
    log("[INFO] 第二步：输入电压遍历校准评估")
    status("FT Check: 电压遍历评估中...")
    voltage_data = []
    actual_voltage = []
    raw_mean = []
    cal_volt = []
    err_mv = []
    dut_volt_mv = [] if mode == 'UART' else None
    cons_mv = [] if mode == 'UART' else None

    first = mode != 'IIC'  # IIC 第一步已施加了电压，首点用 step_s
    for v_pt in sweep_voltages:
        if stopped():
            log("[INFO] FT Calibration Check 已被用户停止，保留已测数据")
            break
        set_voltage_fn(v_pt)
        time.sleep(settle_s if first else step_s)
        first = False

        # DUT 引脚实际电压 = 源设定 × 分压比，误差按实际电压评估
        actual_v = v_pt * divider_ratio
        if mode == 'IIC':
            avg, _, _ = sample_iic_fn(sample_cnt, stop_check)
            cal_v = (avg - b) / k
            err = (cal_v - actual_v) * 1000.0
            log(f"[MEAS] V={v_pt:.3f}（实际={actual_v:.3f}） raw={avg:.2f} "
                f"cal={cal_v:.4f} V err={err:+.2f} mV")
        else:
            raw_avg, volt_avg = sample_uart_fn(sample_cnt, stop_check)
            cal_v = volt_avg / 1000.0
            err = volt_avg - actual_v * 1000.0
            cons = (raw_avg - b) / k * 1000.0 - volt_avg
            dut_volt_mv.append(volt_avg)
            cons_mv.append(cons)
            log(f"[MEAS] V={v_pt:.3f}（实际={actual_v:.3f}） raw={raw_avg:.2f} "
                f"volt={volt_avg:.1f} mV err={err:+.2f} mV cons={cons:+.2f} mV")

        voltage_data.append(v_pt)
        actual_voltage.append(actual_v)
        raw_mean.append(avg if mode == 'IIC' else raw_avg)
        cal_volt.append(cal_v)
        err_mv.append(err)
        _tick()

    if not voltage_data:
        return None

    stats = assess_ft_errors(err_mv, err_limit_mv)
    cons_stats = assess_ft_errors(cons_mv, err_limit_mv) if cons_mv else None
    points_passed = all(p['passed'] for p in point_checks) if point_checks else None

    passed = stats['passed']
    if points_passed is not None:
        passed = passed and points_passed
    if cons_stats is not None:
        passed = passed and cons_stats['passed']

    log(f"[RESULT] 校准误差: Max={stats['max_abs_mv']:.2f} mV, "
        f"Avg={stats['avg_mv']:+.2f} mV, RMS={stats['rms_mv']:.2f} mV, "
        f"N={stats['count']} (限 ±{err_limit_mv:.1f} mV)")
    if cons_stats is not None:
        log(f"[RESULT] 一致性误差(用户K,B vs DUT): Max={cons_stats['max_abs_mv']:.2f} mV, "
            f"Avg={cons_stats['avg_mv']:+.2f} mV, RMS={cons_stats['rms_mv']:.2f} mV")

    return {
        'mode': mode,
        'k': k,
        'b': b,
        'calib_points': [(v1, c1), (v2, c2)],
        'point_checks': point_checks,
        'points_passed': points_passed,
        'divider_ratio': divider_ratio,
        'voltage': voltage_data,
        'actual_voltage': actual_voltage,
        'raw_mean': raw_mean,
        'cal_volt': cal_volt,
        'err_mv': err_mv,
        'dut_volt_mv': dut_volt_mv,
        'cons_mv': cons_mv,
        'stats': stats,
        'cons_stats': cons_stats,
        'err_limit_mv': err_limit_mv,
        'raw_tol_lsb': raw_tol_lsb,
        'passed': passed,
    }
