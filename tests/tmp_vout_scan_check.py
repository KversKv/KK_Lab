# -*- coding: utf-8 -*-
"""临时验证脚本：run_vout_scan 弹窗确认逻辑（前置校验/尾部饱和）+ finally 兜底恢复。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.module_test._common as C
from core.module_test._common import ItemContext, run_vout_scan


class FakeI2C:
    def __init__(self, reg=0x1234):
        self.reg = reg
        self.writes = []

    def read(self, addr, reg, w):
        return self.reg

    def write(self, addr, reg, val, w):
        self.writes.append((addr, reg, val, w))


class FakeN:
    def __init__(self, fn):
        self.fn = fn

    def measure_voltage(self, ch):
        return self.fn()


class FakeTime:
    def time(self):
        return 0.0

    def sleep(self, s):
        pass


C.time = FakeTime()
fake_i2c = FakeI2C()
C.create_i2c = lambda ctx: fake_i2c
C.setup_meter_channel = lambda ctx, ch: None
C.setup_load_channel = lambda ctx, ch, initial_current_a=None: None
C.teardown_load = lambda ctx, ch: None

CFG = {"device_addr": "0x10", "reg_addr": "0x0", "msb": 7, "lsb": 0,
       "width_flag": 1, "min_code": 0, "max_code": 30,
       "vout_channel": 1, "iload_channel": 3}


def assert_eq(a, b, what):
    assert a == b, f"{what}: {a!r} != {b!r}"


def assert_true(v, what):
    assert v, f"{what}: 断言为假"


def make_ctx(confirm, vfn):
    logs = []
    ctx = ItemContext(
        n6705c=FakeN(vfn), scope=None, chamber=None, config=dict(CFG),
        out_dir=tempfile.mkdtemp(), is_mock=False,
        stop_flag_fn=lambda: False, log_fn=logs.append,
        progress_fn=lambda p, l: None, confirm_fn=confirm)
    return ctx, logs


def run_case(name, confirm, vfn, checks):
    global fake_i2c
    fake_i2c = FakeI2C()
    C.create_i2c = lambda ctx: fake_i2c
    calls = []
    ctx, logs = make_ctx(lambda t, m: (calls.append(t), confirm(t, m))[1], vfn)
    r = run_vout_scan(ctx, "ldo_vout_scan", "Output Voltage Scan")
    try:
        checks(name, r, calls, fake_i2c, logs)
        print(f"[PASS] {name}")
    except AssertionError as e:
        print(f"[FAIL] {name}: {e}")


def v_ramp():
    if not fake_i2c.writes:
        return 0.123
    return 0.002 * (fake_i2c.writes[-1][2] & 0xFF)


def v_prefix_flat():
    if not fake_i2c.writes:
        return 0.123
    code = fake_i2c.writes[-1][2] & 0xFF
    if code <= 4:
        return 0.5
    return 0.5 + 0.002 * (code - 5)


def v_tail_sat():
    if not fake_i2c.writes:
        return 0.123
    code = fake_i2c.writes[-1][2] & 0xFF
    if code >= 16:
        return 0.032
    return 0.002 * code


# A: 线性扫描，无弹窗
run_case(
    "A 线性无弹窗",
    lambda t, m: (_ for _ in ()).throw(AssertionError("不应弹窗")),
    v_ramp,
    lambda n, r, calls, i2c, logs: (
        assert_eq(calls, [], "confirm 调用"),
        assert_eq(r.measured["valid_min_code"], 1, "valid_min"),
        assert_eq(r.measured["valid_max_code"], 29, "valid_max"),
        assert_eq(i2c.writes[-1][2], 0x1234, "恢复默认值"),
    ),
)

# B: 前置校验失败 → 继续（剔除异常前缀）
run_case(
    "B 前置校验失败-继续",
    lambda t, m: (True, True),
    v_prefix_flat,
    lambda n, r, calls, i2c, logs: (
        assert_eq(calls, ["前置校验失败"], "confirm 调用"),
        assert_eq(r.measured["valid_min_code"], 6, "valid_min（剔除前缀）"),
        assert_eq(r.measured["valid_max_code"], 29, "valid_max"),
        assert_eq(r.measured["points"], 31, "CSV 保留全部点"),
        assert_eq(i2c.writes[-1][2], 0x1234, "恢复默认值"),
    ),
)

# C: 前置校验失败 → 中止（precheck_failed，无指标）
run_case(
    "C 前置校验失败-中止",
    lambda t, m: (True, False),
    v_prefix_flat,
    lambda n, r, calls, i2c, logs: (
        assert_eq(calls, ["前置校验失败"], "confirm 调用"),
        assert_eq(r.passed, None, "passed"),
        assert_true("前置校验失败" in r.notes, "notes"),
        assert_true(r.raw_csv_path and os.path.exists(r.raw_csv_path), "CSV 已落盘"),
        assert_eq(i2c.writes[-1][2], 0x1234, "恢复默认值"),
    ),
)

# D: 尾部饱和 → 中止（截断平台）
run_case(
    "D 尾部饱和-中止",
    lambda t, m: (True, False),
    v_tail_sat,
    lambda n, r, calls, i2c, logs: (
        assert_eq(calls, ["输出饱和确认"], "confirm 调用"),
        assert_eq(r.measured["valid_max_code"], 14, "valid_max（截断平台）"),
        assert_eq(r.measured["points"], 21, "CSV 保留全部点"),
        assert_eq(i2c.writes[-1][2], 0x1234, "恢复默认值"),
    ),
)

# E: 尾部饱和 → 继续（本次不再触发，平坦段由后处理剔除）
run_case(
    "E 尾部饱和-继续",
    lambda t, m: (True, True),
    v_tail_sat,
    lambda n, r, calls, i2c, logs: (
        assert_eq(calls, ["输出饱和确认"], "confirm 仅一次"),
        assert_eq(r.measured["valid_max_code"], 15, "valid_max（后处理剔除平坦）"),
        assert_eq(r.measured["points"], 31, "扫描完整"),
        assert_eq(i2c.writes[-1][2], 0x1234, "恢复默认值"),
    ),
)
