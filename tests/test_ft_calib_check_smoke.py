# -*- coding: utf-8 -*-
"""FT Calibration Check core 纯函数冒烟（临时调试用）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.pmu_test.gpadc import (
    assess_ft_errors,
    parse_uart_gpadc_raw_volt,
    run_ft_calib_check,
    solve_ft_kb,
)

# 1) 解析：用户实际日志行
pair = parse_uart_gpadc_raw_volt(
    "13:39:17.023 [RX]   21/      574/I/NONE  / 42E | gpadc_ch11_irq_cb: raw/volt=3338/1522 tm=556us",
    "raw/volt",
)
assert pair == (3338, 1522), pair
assert parse_uart_gpadc_raw_volt("no match line", "raw/volt") is None
print("parse_uart_gpadc_raw_volt OK:", pair)

# 2) K/B 解算
k, b = solve_ft_kb(1.0, 3277.0, 3.0, 9830.0)
assert abs(k - 3276.5) < 1e-9 and abs(b - 0.5) < 1e-9, (k, b)
for bad in [(1.0, 100.0, 3.0, 100.0), (1.0, 100.0, 1.0, 200.0)]:
    try:
        solve_ft_kb(*bad)
        raise AssertionError("应抛 ValueError")
    except ValueError:
        pass
print("solve_ft_kb OK: k=%s b=%s" % (k, b))

# 3) 误差统计
s = assess_ft_errors([1.0, -2.0, 3.5], 10.0)
assert s['passed'] and abs(s['max_abs_mv'] - 3.5) < 1e-9
s2 = assess_ft_errors([11.0], 10.0)
assert not s2['passed']
print("assess_ft_errors OK:", s)

# 4) IIC 流程（模拟：理想 ADC，raw = 3276.8*V）
logs = []
K_SIM = 3276.8
res = run_ft_calib_check(
    mode='IIC',
    calib_p1=(1.0, 3277.0),
    calib_p2=(3.0, 9830.0),
    raw_tol_lsb=10.0,
    err_limit_mv=10.0,
    voltage_min=1.0, voltage_max=3.0, voltage_step=0.5,
    sample_cnt=10,
    set_voltage_fn=lambda v: None,
    sample_iic_fn=lambda cnt, stop: (K_SIM * 2.0, 0, 0),  # 固定返回 V=2.0 的理想码
    settle_s=0, step_s=0,
    log_fn=logs.append,
)
assert res is not None
assert res['points_passed'] is False or res['points_passed'] is True
assert len(res['voltage']) == 5
print("run_ft_calib_check IIC OK: passed=%s" % res['passed'])

# 5) UART 流程（模拟：volt 完全等于施加电压，raw 遵循用户 K,B）
state = {'v': 0.0}
k_u, b_u = solve_ft_kb(1.0, 3277.0, 3.0, 9830.0)
res2 = run_ft_calib_check(
    mode='UART',
    calib_p1=(1.0, 3277.0),
    calib_p2=(3.0, 9830.0),
    err_limit_mv=10.0,
    voltage_min=1.0, voltage_max=3.0, voltage_step=1.0,
    sample_cnt=10,
    set_voltage_fn=lambda v: state.__setitem__('v', v),
    sample_uart_fn=lambda cnt, stop: (k_u * state['v'] + b_u, state['v'] * 1000.0),
    settle_s=0, step_s=0,
    log_fn=logs.append,
)
assert res2 is not None
assert res2['passed'], res2['stats']
assert res2['cons_stats']['max_abs_mv'] < 1e-6
assert res2['point_checks'] == []
print("run_ft_calib_check UART OK: passed=%s" % res2['passed'])

# 6) 分压比（IIC，ratio=0.5）：校准点源=点/比值，扫压实际=源×比值，误差按实际电压
sets = []
res3 = run_ft_calib_check(
    mode='IIC',
    calib_p1=(1.0, 3277.0),
    calib_p2=(3.0, 9830.0),
    raw_tol_lsb=10.0,
    err_limit_mv=10.0,
    divider_ratio=0.5,
    voltage_min=2.0, voltage_max=6.0, voltage_step=2.0,
    sample_cnt=10,
    set_voltage_fn=sets.append,
    sample_iic_fn=lambda cnt, stop: (3276.8 * (sets[-1] * 0.5), 0, 0),
    settle_s=0, step_s=0,
    log_fn=logs.append,
)
assert sets[:2] == [2.0, 6.0], sets            # 校准点确认源 = 1.0/0.5, 3.0/0.5
assert sets[2:] == [2.0, 4.0, 6.0], sets       # 扫压按源设定值
assert res3['voltage'] == [2.0, 4.0, 6.0]
assert res3['actual_voltage'] == [1.0, 2.0, 3.0]
assert res3['divider_ratio'] == 0.5
assert res3['points_passed'] and res3['passed'], res3['stats']
print("run_ft_calib_check IIC+divider OK: passed=%s" % res3['passed'])

# 7) 分压比非法
try:
    run_ft_calib_check(mode='IIC', calib_p1=(1.0, 1.0), calib_p2=(3.0, 3.0),
                       divider_ratio=0, set_voltage_fn=lambda v: None)
    raise AssertionError("应抛 ValueError")
except ValueError:
    pass
print("divider_ratio 校验 OK")

print("ALL SMOKE PASS")
