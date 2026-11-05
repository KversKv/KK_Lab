# -*- coding: utf-8 -*-
"""Module Test 非法参数、测量异常、停止与空数据防线回归测试。"""
from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from core.module_test import _common
from core.module_test._common import (
    ItemContext, linspace, load_reg_summary, measure_avg, run_load_capability_ripple,
    run_line_transient, run_load_transient, run_vout_scan, safe_measure,
)
from core.module_test._runner_base import ModuleTestRunner
from core.module_test.dcdc.items import DCDC_ITEMS, current_limit as dcdc_current_limit
from core.module_test.judge import evaluate_item
from core.module_test.ldo.items import LDO_ITEMS, current_limit as ldo_current_limit
from core.module_test.ldo.items import dropout
from core.module_test.report import build_report_data
from core.module_test.result_model import ItemResult, ModuleTestResult
from ui.pages.module_test._base_subpage import ModuleTestSubPageBase


def _ctx(tmp_path, **kwargs) -> ItemContext:
    return ItemContext(
        n6705c=kwargs.get("n6705c"),
        scope=kwargs.get("scope"),
        chamber=None,
        config=kwargs.get("config", {}),
        out_dir=str(tmp_path),
        is_mock=kwargs.get("is_mock", True),
        stop_flag_fn=kwargs.get("stop_flag_fn", lambda: False),
        log_fn=lambda _line: None,
        progress_fn=lambda _percent, _label: None,
    )


class _ForbiddenInstrument:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        self.calls.append(name)
        raise AssertionError(f"非法参数校验前调用了仪器方法 {name}")


class _ZeroThenFailInstrument:
    def __init__(self):
        self.fail = False

    def measure_voltage(self, _channel):
        if self.fail:
            raise RuntimeError("read failed")
        return 0.0


class _FailOnInstrument:
    def __init__(self, fail_method: str):
        self.fail_method = fail_method
        self.calls = []

    def __getattr__(self, name):
        if name == "instr":
            return None

        def _call(*args, **_kwargs):
            self.calls.append((name, args))
            if name == self.fail_method:
                raise RuntimeError(f"{name} failed")
            return None

        return _call


def test_safe_measure_preserves_real_zero_and_marks_failure(tmp_path):
    inst = _ZeroThenFailInstrument()
    assert safe_measure(inst, "measure_voltage", 1) == 0.0
    inst.fail = True
    assert math.isnan(safe_measure(inst, "measure_voltage", 1))
    ctx = _ctx(tmp_path, n6705c=inst, is_mock=False)
    assert math.isnan(measure_avg(ctx, "measure_voltage", 1))
    assert ctx.measurement_failed is True


def test_linspace_rejects_invalid_values_and_supports_descending():
    assert linspace(5, 1, 2) == [5.0, 3.0, 1.0]
    for start, end, step in ((1, 2, 0), (1, 2, -1), (1, math.nan, 0.1)):
        with pytest.raises(ValueError):
            linspace(start, end, step)


@pytest.mark.parametrize("step", [0, -0.01, math.nan])
def test_ldo_current_limit_rejects_step_before_instrument(tmp_path, step):
    inst = _ForbiddenInstrument()
    ctx = _ctx(tmp_path, n6705c=inst, is_mock=False,
               config={"ilim_start_ma": 50, "ilim_end_ma": 500,
                       "ilim_step_ma": step})
    with pytest.raises(ValueError):
        ldo_current_limit(ctx)
    assert inst.calls == []


def test_dcdc_current_limit_rejects_range_values_before_instrument(tmp_path):
    inst = _ForbiddenInstrument()
    ctx = _ctx(tmp_path, n6705c=inst, is_mock=False,
               config={"ilim_start_ma": 100, "ilim_end_ma": math.inf,
                       "ilim_step_ma": 20})
    with pytest.raises(ValueError):
        dcdc_current_limit(ctx)
    assert inst.calls == []


@pytest.mark.parametrize("config", [
    {"dropout_vin_step_v": 0},
    {"dropout_vin_step_v": -0.02},
    {"dropout_vin_hi_v": 1.7, "dropout_vin_lo_v": 2.0},
    {"dropout_vin_lo_v": math.nan},
])
def test_dropout_rejects_invalid_scan_before_instrument(tmp_path, config):
    inst = _ForbiddenInstrument()
    ctx = _ctx(tmp_path, n6705c=inst, is_mock=False, config=config)
    with pytest.raises(ValueError):
        dropout(ctx)
    assert inst.calls == []


def test_empty_and_single_point_load_reg_have_no_performance_result():
    for rows in ([], [[100, 1800.0]]):
        summary = load_reg_summary(rows)
        assert summary["vout_drop_mv"] == ""
        assert summary["load_reg_pct"] == ""
    passed, _ = evaluate_item(
        "ldo_load_reg", {"rules": [{"metric": "load_reg_pct", "op": "<", "v1": 1.0}]},
        load_reg_summary([]))
    assert passed is None


def test_first_point_stop_produces_empty_current_limit(tmp_path):
    ctx = _ctx(tmp_path, stop_flag_fn=lambda: True,
               config={"ilim_start_ma": 50, "ilim_end_ma": 500,
                       "ilim_step_ma": 20})
    result = ldo_current_limit(ctx)
    assert result.measured["current_limit_ma"] == ""
    assert result.measured["peak_current_ma"] == ""


def test_ripple_first_point_stop_has_no_zero_metrics(tmp_path):
    ctx = _ctx(tmp_path, scope=object(), stop_flag_fn=lambda: True,
               config={"iload_start_ma": 0, "iload_end_ma": 200,
                       "iload_step_ma": 20})
    result = run_load_capability_ripple(ctx, "ldo_ripple", "Ripple", 10.0, 2.0)
    assert result.measured["points"] == 0
    assert result.measured["max_vpp_mv"] == ""
    assert result.measured["max_vout_drop_mv"] == ""
    assert result.measured["max_load_ma"] == ""


def test_ripple_scope_exception_does_not_become_zero(tmp_path, monkeypatch):
    scope = _FailOnInstrument("set_AutoRipple_test")
    for name in ("setup_source_channel", "setup_vout_meter", "setup_load_channel",
                 "setup_scope_timebase", "apply_load_current", "teardown_load",
                 "settle"):
        monkeypatch.setattr(_common, name, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_common, "measure_vout", lambda *_args, **_kwargs: 1.8)
    monkeypatch.setattr(_common, "_capture_scope_png", lambda *_args, **_kwargs: None)
    ctx = _ctx(tmp_path, n6705c=object(), scope=scope, is_mock=False,
               config={"iload_start_ma": 0, "iload_end_ma": 0,
                       "iload_step_ma": 20, "vout_nominal_mv": 1800})
    result = run_load_capability_ripple(ctx, "ldo_ripple", "Ripple", 10.0, 2.0)
    assert ctx.measurement_failed is True
    assert result.measured["max_vpp_mv"] == ""
    assert result.raw_csv_path


@pytest.mark.parametrize("kind", ["line", "load"])
def test_transient_group_exception_has_no_zero_metrics(tmp_path, monkeypatch, kind):
    fail_method = "set_mode" if kind == "line" else "set_current_slew"
    inst = _FailOnInstrument(fail_method)
    for name in ("_reset_arb_state", "_arb_stop_and_wait", "teardown_load",
                 "restore_vin", "setup_load_channel"):
        monkeypatch.setattr(_common, name, lambda *_args, **_kwargs: None)
    ctx = _ctx(tmp_path, n6705c=inst, scope=object(), is_mock=False)
    if kind == "line":
        result = run_line_transient(ctx, "ldo_line_transient", "Line Transient", 1.0, 1.0)
    else:
        result = run_load_transient(ctx, "ldo_load_transient", "Load Transient", 1.0, 1.0)
    assert ctx.measurement_failed is True
    assert result.measured["max_overshoot_mv"] == ""
    assert result.measured["max_undershoot_mv"] == ""


def test_vout_scan_measurement_failure_does_not_spin_or_emit_metrics(tmp_path, monkeypatch):
    class _I2C:
        def __init__(self):
            self.writes = []

        def read(self, *_args):
            return 0

        def write(self, *args):
            self.writes.append(args)

    i2c = _I2C()
    inst = _ZeroThenFailInstrument()
    inst.fail = True
    monkeypatch.setattr(_common, "create_i2c", lambda _ctx: i2c)
    for name in ("setup_source_channel", "setup_load_channel", "teardown_load",
                 "teardown_vin"):
        monkeypatch.setattr(_common, name, lambda *_args, **_kwargs: None)
    ctx = _ctx(tmp_path, n6705c=inst, is_mock=False,
               config={"min_code": 0, "max_code": 2})
    result = run_vout_scan(ctx, "ldo_vout_scan", "Output Voltage Scan")
    assert ctx.measurement_failed is True
    assert result.passed is not True
    assert not result.measured
    assert i2c.writes[-1][-2] == 0  # 恢复默认寄存器值


def _run_single_item(tmp_path, monkeypatch, run_fn):
    key = "ldo_line_reg"
    runner = ModuleTestRunner(
        module_type="ldo",
        items_registry={key: ("Line Regulation", run_fn, False, True, ())},
        config={"selected_items": [key], "judge_enabled": True,
                "judge_criteria": {key: {"rules": [
                    {"metric": "line_reg_pct", "op": "<", "v1": 1.0}
                ]}}},
        n6705c=None, out_dir=str(tmp_path),
    )
    monkeypatch.setattr(runner, "_setup_vin_current_limit", lambda: None)
    monkeypatch.setattr(runner, "_preload_iload", lambda: None)
    monkeypatch.setattr(runner, "_record_vout_baseline", lambda: None)
    monkeypatch.setattr(runner, "_check_vout_deviation", lambda *_args: True)
    monkeypatch.setattr("core.module_test._runner_base.save_html_report",
                        lambda *_args, **_kwargs: (str(tmp_path / "report.html"), None))
    finished = []
    runner.finished_result.connect(finished.append)
    runner._run_impl()
    assert len(finished) == 1
    return finished[0]


def test_runner_measurement_failure_cannot_judge_pass(tmp_path, monkeypatch):
    def _run(ctx):
        ctx.measurement_failed = True
        return ItemResult(item_key="ldo_line_reg", name="Line Regulation",
                          measured={"line_reg_pct": 0.0})

    result = _run_single_item(tmp_path, monkeypatch, _run)
    assert result.items[0].passed is False
    assert "测量异常" in result.items[0].notes
    assert result.summary["overall"] == "FAIL"


def test_runner_load_control_failure_stops_remaining_items(tmp_path, monkeypatch):
    first_key = "ldo_line_reg"
    second_key = "ldo_load_reg"
    calls = []

    def _fail_load(_ctx):
        calls.append(first_key)
        raise _common.LoadControlError("set_current failed")

    def _should_not_run(_ctx):
        calls.append(second_key)
        return ItemResult(item_key=second_key, name="Load Regulation", passed=True)

    runner = ModuleTestRunner(
        module_type="ldo",
        items_registry={
            first_key: ("Line Regulation", _fail_load, False, True, ()),
            second_key: ("Load Regulation", _should_not_run, False, True, ()),
        },
        config={"selected_items": [first_key, second_key]},
        n6705c=None, out_dir=str(tmp_path),
    )
    monkeypatch.setattr(runner, "_setup_vin_current_limit", lambda: None)
    monkeypatch.setattr(runner, "_preload_iload", lambda: None)
    monkeypatch.setattr(runner, "_record_vout_baseline", lambda: None)

    def _forbidden_follow_up(*_args, **_kwargs):
        raise AssertionError("负载控制失败后仍执行了后续测量")

    monkeypatch.setattr(runner, "_check_vout_deviation", _forbidden_follow_up)
    monkeypatch.setattr("core.module_test._runner_base.save_html_report",
                        lambda *_args, **_kwargs: (str(tmp_path / "report.html"), None))
    finished = []
    runner.finished_result.connect(finished.append)

    runner._run_impl()

    assert calls == [first_key]
    assert len(finished) == 1
    result = finished[0]
    assert [item.item_key for item in result.items] == [first_key]
    assert result.items[0].passed is False
    assert "set_current failed" in result.items[0].notes
    assert result.summary["aborted"] == f"{first_key} 负载控制失败"


def test_runner_stop_is_checked_before_judge(tmp_path, monkeypatch):
    holder = {}

    def _run(_ctx):
        holder["runner"].request_stop()
        return ItemResult(item_key="ldo_line_reg", name="Line Regulation",
                          measured={"line_reg_pct": 0.0})

    original_init = ModuleTestRunner.__init__

    def _capture_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        holder["runner"] = self

    monkeypatch.setattr(ModuleTestRunner, "__init__", _capture_init)
    result = _run_single_item(tmp_path, monkeypatch, _run)
    assert result.items[0].passed is None
    assert result.summary["aborted"] == "用户请求停止"
    assert "不参与判定" in result.items[0].notes


def test_repeated_summary_and_report_keep_aborted_state():
    result = ModuleTestResult(module_type="ldo", items=[
        ItemResult(item_key="ldo_line_reg", name="Line Regulation", passed=None)
    ])
    result.summary["aborted"] = "用户请求停止"
    result.build_summary()
    report = build_report_data(result)
    result.build_summary()
    assert result.summary["aborted"] == "用户请求停止"
    assert report["summary"]["aborted"] == "用户请求停止"


@pytest.mark.parametrize("config", [
    {"msb": 3, "lsb": 7},
    {"msb": 7, "lsb": 0, "max_code": 256},
    {"min_code": -1},
])
def test_vout_scan_rejects_invalid_code_range_before_i2c_or_instrument(
        tmp_path, monkeypatch, config):
    inst = _ForbiddenInstrument()

    def _forbidden_i2c(_ctx):
        raise AssertionError("非法参数校验前创建了 I2C 接口")

    monkeypatch.setattr(_common, "create_i2c", _forbidden_i2c)
    ctx = _ctx(tmp_path, n6705c=inst, is_mock=False, config=config)
    with pytest.raises(ValueError):
        run_vout_scan(ctx, "ldo_vout_scan", "Output Voltage Scan")
    assert inst.calls == []


@pytest.mark.parametrize("module_type,registry,item_key,override", [
    ("ldo", LDO_ITEMS, "ldo_ripple", {"iload_step_ma": 0}),
    ("dcdc", DCDC_ITEMS, "dcdc_line_reg", {"vin_step_v": math.nan}),
    ("dcdc", DCDC_ITEMS, "dcdc_current_limit", {"ilim_end_ma": math.inf}),
    ("ldo", LDO_ITEMS, "ldo_dropout", {
        "dropout_vin_hi_v": 1.0, "dropout_vin_lo_v": 2.0,
    }),
    ("ldo", LDO_ITEMS, "ldo_vout_scan", {"msb": 3, "lsb": 7}),
    ("dcdc", DCDC_ITEMS, "dcdc_vout_scan", {"max_code": 256}),
])
def test_runner_invalid_item_params_fail_before_any_io(
        tmp_path, monkeypatch, module_type, registry, item_key, override):
    out_dir = tmp_path / "must_not_be_created"
    inst = _ForbiddenInstrument()
    runner = ModuleTestRunner(
        module_type=module_type,
        items_registry=registry,
        config={"selected_items": [item_key],
                "item_overrides": {item_key: override}},
        n6705c=inst,
        out_dir=str(out_dir),
    )
    pre_calls = []
    for name in ("_setup_vin_current_limit", "_preload_iload", "_record_vout_baseline"):
        monkeypatch.setattr(
            runner, name, lambda name=name: pre_calls.append(name))
    failed = []
    finished = []
    runner.failed.connect(failed.append)
    runner.finished_result.connect(finished.append)

    runner._run_impl()

    assert len(failed) == 1
    assert "测试参数无效" in failed[0]
    assert item_key in failed[0]
    assert pre_calls == []
    assert inst.calls == []
    assert finished == []
    assert not out_dir.exists()


def test_ui_invalid_override_blocks_module_config_and_runner():
    cfg = {
        "selected_items": ["ldo_ripple"],
        "item_overrides": {"ldo_ripple": {"iload_step_ma": 0}},
        "module_config_enabled": True,
        "module_config_yaml": "WRITE 0x00 0x01",
    }
    alerts = []
    states = []
    modcfg_calls = []
    runner_calls = []
    page = SimpleNamespace(
        ITEMS_REGISTRY=LDO_ITEMS,
        is_test_running=False,
        get_test_config=lambda: cfg,
        left_rail=SimpleNamespace(
            dut_panel=SimpleNamespace(validate=lambda: None)),
        _alert_banner=SimpleNamespace(hide=lambda: None),
    )
    page._show_alert = lambda text, severity="warning": alerts.append((text, severity))
    page._missing_instruments = lambda _cfg: []
    page._apply_run_state = states.append
    page._run_module_config = modcfg_calls.append
    page._proceed_start_test = runner_calls.append
    page._precheck = lambda value: ModuleTestSubPageBase._precheck(page, value)

    ModuleTestSubPageBase._on_start_test(page)

    assert [state.name for state in states] == ["PRECHECK", "IDLE"]
    assert len(alerts) == 1
    assert "测试参数无效" in alerts[0][0]
    assert "ldo_ripple" in alerts[0][0]
    assert modcfg_calls == []
    assert runner_calls == []


@pytest.mark.parametrize("module_name,item_name", [
    ("dcdc", "psrr"),
    ("dcdc", "inductor_current"),
    ("dcdc", "startup"),
    ("dcdc", "protection"),
    ("ldo", "psrr"),
    ("ldo", "protection"),
])
def test_unimplemented_real_measurements_are_skipped_without_csv(
        tmp_path, module_name, item_name):
    from importlib import import_module

    items = import_module(f"core.module_test.{module_name}.items")
    ctx = _ctx(tmp_path, n6705c=object(), scope=object(), is_mock=False)

    result = getattr(items, item_name)(ctx)

    assert result.passed is None
    assert result.measured is None
    assert result.raw_csv_path is None
    assert "未实现" in result.notes
    assert list(tmp_path.glob("*.csv")) == []
    report = build_report_data(ModuleTestResult(module_type=module_name, items=[result]))
    assert report["items"][0]["verdict"] == "N/A"
    assert report["items"][0]["note"] == result.notes
    assert report["summary"]["na"] == 1


@pytest.mark.parametrize("module_name,item_name", [
    ("dcdc", "psrr"),
    ("dcdc", "inductor_current"),
    ("dcdc", "startup"),
    ("dcdc", "protection"),
    ("ldo", "psrr"),
    ("ldo", "protection"),
])
def test_unimplemented_items_keep_mock_measurements(tmp_path, module_name, item_name):
    from importlib import import_module

    items = import_module(f"core.module_test.{module_name}.items")
    ctx = _ctx(tmp_path, n6705c=object(), scope=object(), is_mock=True)

    result = getattr(items, item_name)(ctx)

    assert result.measured is not None
    assert result.raw_csv_path is not None
    assert (tmp_path / f"{result.item_key}.csv").is_file()


def test_dcdc_topology_invalid_measurement_uses_empty_value(tmp_path):
    from core.module_test.dcdc.items import topology

    inst = _FailOnInstrument("measure_voltage")
    ctx = _ctx(tmp_path, n6705c=inst, scope=None, is_mock=False)

    result = topology(ctx)

    assert result.measured["vout_vin_ratio"] == ""
    assert result.measured["detected"] == "N/A"
    assert "无法判定拓扑" in result.notes
    assert ctx.measurement_failed is True
    csv_lines = (tmp_path / "dcdc_topology.csv").read_text(encoding="utf-8-sig").splitlines()
    assert csv_lines[1].endswith(",")


@pytest.mark.parametrize("function_name,args,fail_method", [
    ("setup_source_channel", (1, 3.8), "set_voltage"),
    ("setup_meter_channel", (1,), "set_mode"),
])
def test_common_instrument_failures_mark_measurement_invalid(
        tmp_path, function_name, args, fail_method):
    ctx = _ctx(tmp_path, n6705c=_FailOnInstrument(fail_method), is_mock=False)

    getattr(_common, function_name)(ctx, *args)

    assert ctx.measurement_failed is True


@pytest.mark.parametrize("function_name,args,fail_method", [
    ("setup_load_channel", (3, 0.001), "set_current"),
    ("setup_load_channel", (3, 0.001), "channel_on"),
    ("set_load_current", (3, 0.1), "set_current"),
    ("apply_load_current", (3, 0.1, {"on": True}), "set_current"),
])
def test_load_control_failures_shutdown_and_raise(
        tmp_path, function_name, args, fail_method):
    inst = _FailOnInstrument(fail_method)
    ctx = _ctx(tmp_path, n6705c=inst, is_mock=False)

    with pytest.raises(_common.LoadControlError, match="ch3"):
        getattr(_common, function_name)(ctx, *args)

    names = [name for name, _args in inst.calls]
    assert ctx.measurement_failed is True
    assert names.count("channel_off") == 1
    if fail_method == "set_current":
        assert "channel_on" not in names


def test_load_control_cleanup_failure_preserves_original_error(tmp_path):
    class _WriteAndCleanupFailInstrument(_FailOnInstrument):
        def channel_off(self, channel):
            self.calls.append(("channel_off", (channel,)))
            raise RuntimeError("channel_off failed")

    ctx = _ctx(tmp_path, n6705c=_WriteAndCleanupFailInstrument("set_current"),
               is_mock=False)

    with pytest.raises(_common.LoadControlError) as caught:
        _common.set_load_current(ctx, 3, 0.1)

    assert isinstance(caught.value.__cause__, RuntimeError)
    assert str(caught.value.__cause__) == "set_current failed"
    assert ctx.measurement_failed is True


def test_scope_timebase_failure_marks_measurement_invalid(tmp_path):
    ctx = _ctx(tmp_path, scope=_FailOnInstrument("set_timebase_scale"), is_mock=False)

    _common.setup_scope_timebase(ctx)

    assert ctx.measurement_failed is True


def test_ripple_unexpected_error_cleans_up_without_masking(tmp_path):
    class _CleanupFailInstrument:
        def __init__(self):
            self.off_calls = []

        def channel_off(self, channel):
            self.off_calls.append(channel)
            raise RuntimeError("channel_off failed")

        def __getattr__(self, name):
            if name == "instr":
                return None
            return lambda *_args, **_kwargs: None

    inst = _CleanupFailInstrument()
    ctx = _ctx(
        tmp_path, n6705c=inst,
        scope=_FailOnInstrument("set_channel_display"), is_mock=False,
        config={"iload_channel": 3, "iload_start_ma": 0,
                "iload_end_ma": 0, "iload_step_ma": 20},
    )

    with pytest.raises(RuntimeError, match="set_channel_display failed"):
        run_load_capability_ripple(ctx, "ldo_ripple", "Ripple", 10.0, 2.0)

    assert inst.off_calls == [3]
    assert ctx.measurement_failed is True


def test_runner_main_report_failure_emits_failed_not_finished(tmp_path, monkeypatch):
    key = "ldo_line_reg"

    def _run(_ctx):
        return ItemResult(item_key=key, name="Line Regulation", passed=True)

    def _fail_report(*_args, **_kwargs):
        raise OSError("disk full")

    runner = ModuleTestRunner(
        module_type="ldo",
        items_registry={key: ("Line Regulation", _run, False, True, ())},
        config={"selected_items": [key]},
        n6705c=None, out_dir=str(tmp_path),
    )
    monkeypatch.setattr(runner, "_setup_vin_current_limit", lambda: None)
    monkeypatch.setattr(runner, "_preload_iload", lambda: None)
    monkeypatch.setattr(runner, "_record_vout_baseline", lambda: None)
    monkeypatch.setattr(runner, "_check_vout_deviation", lambda *_args: True)
    monkeypatch.setattr("core.module_test._runner_base.save_html_report", _fail_report)
    failed = []
    finished = []
    runner.failed.connect(failed.append)
    runner.finished_result.connect(finished.append)

    runner._run_impl()

    assert len(failed) == 1
    assert "生成报告失败" in failed[0]
    assert "disk full" in failed[0]
    assert finished == []


def test_report_existing_csv_read_error_does_not_drop_points(tmp_path, monkeypatch):
    csv_path = tmp_path / "line_reg.csv"
    csv_path.write_text("Iload (mA),Vout (mV)\n100,1800\n", encoding="utf-8")
    result = ModuleTestResult(module_type="ldo", items=[
        ItemResult(item_key="ldo_line_reg", name="Line Regulation",
                   raw_csv_path=str(csv_path)),
    ])

    def _fail_open(*_args, **_kwargs):
        raise OSError("read denied")

    monkeypatch.setattr("builtins.open", _fail_open)
    with pytest.raises(OSError, match="read denied"):
        build_report_data(result)
