# -*- coding: utf-8 -*-
"""GPADC worker 真实 QThread、页面销毁与 UI 线程亲和性回归。"""

import ast
import os
import sys
import threading
import time
from pathlib import Path
from types import MappingProxyType

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from PySide6.QtCore import QEvent, QObject, QThread, Slot
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from core.pmu_test.gpadc import GPADCAcquisition, GPADCTestRunner, TestWorker
from instruments.mock.mock_instruments import MockChamber, MockI2C, MockN6705C


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _drain_until(app, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("等待 Qt 线程/事件收尾超时")
        app.processEvents()
        app.sendPostedEvents(None, QEvent.DeferredDelete)
        time.sleep(0.001)
    app.processEvents()
    app.sendPostedEvents(None, QEvent.DeferredDelete)


class _Probe(QObject):
    def __init__(self):
        super().__init__()
        self.gui_thread = QThread.currentThread()
        self.slot_threads = []
        self.finished = []
        self.errors = []
        self.logs = []
        self.statuses = []
        self.confirm_requests = []
        self.confirm_responder = None
        self.confirm_response = False

    def _record_thread(self):
        self.slot_threads.append(QThread.currentThread())

    @Slot(object)
    def on_finished(self, value):
        self._record_thread()
        self.finished.append(value)

    @Slot(str)
    def on_error(self, message):
        self._record_thread()
        self.errors.append(message)

    @Slot(str)
    def on_log(self, message):
        self._record_thread()
        self.logs.append(message)

    @Slot(str, bool)
    def on_status(self, message, is_error):
        self._record_thread()
        self.statuses.append((message, is_error))

    @Slot(str, str)
    def on_confirm(self, title, message):
        self._record_thread()
        self.confirm_requests.append((title, message))
        if self.confirm_responder is not None:
            self.confirm_responder(self.confirm_response)

    def assert_slots_in_gui_thread(self):
        assert self.slot_threads
        assert all(thread == self.gui_thread for thread in self.slot_threads)


@pytest.fixture
def worker_threads(app):
    running = []
    yield running
    for thread, worker in running:
        if isValid(worker):
            worker.request_stop()
            worker.respond_confirm(False)
        if isValid(thread):
            thread.quit()
    _drain_until(
        app,
        lambda: all(not isValid(thread) or not thread.isRunning() for thread, _ in running),
    )
    for thread, worker in running:
        if isValid(worker):
            worker.deleteLater()
        if isValid(thread):
            thread.deleteLater()
    app.processEvents()


def _launch(worker, running):
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.error.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    running.append((thread, worker))
    thread.start()
    return thread


def test_worker_start_freezes_config_and_slots_run_in_gui(app, worker_threads):
    holder = {}
    config = {"channels": [{"name": "CH1"}], "params": [1, 2]}

    def fn(config, stop_check):
        assert isinstance(config, MappingProxyType)
        assert isinstance(config["channels"], tuple)
        assert isinstance(config["channels"][0], MappingProxyType)
        assert isinstance(config["params"], tuple)
        try:
            config["new_key"] = True
        except TypeError:
            pass
        else:
            raise AssertionError("worker 配置仍可变")
        holder["worker"].log.emit("worker log")
        holder["worker"].status.emit("worker status", True)
        return {
            "name": config["channels"][0]["name"],
            "params": config["params"],
        }

    worker = TestWorker(fn, {"config": config})
    holder["worker"] = worker
    config["channels"][0]["name"] = "CHANGED"
    config["params"].append(3)

    probe = _Probe()
    worker.finished.connect(probe.on_finished)
    worker.error.connect(probe.on_error)
    worker.log.connect(probe.on_log)
    worker.status.connect(probe.on_status)
    _launch(worker, worker_threads)
    _drain_until(app, lambda: probe.finished or probe.errors)

    assert probe.errors == []
    assert probe.finished == [{"name": "CH1", "params": (1, 2)}]
    assert probe.logs == ["worker log"]
    assert probe.statuses == [("worker status", True)]
    probe.assert_slots_in_gui_thread()


def test_worker_cooperative_stop(app, worker_threads):
    started = threading.Event()

    def fn(stop_check):
        started.set()
        while not stop_check():
            time.sleep(0.005)
        return "stopped"

    worker = TestWorker(fn, {})
    probe = _Probe()
    worker.finished.connect(probe.on_finished)
    worker.error.connect(probe.on_error)
    _launch(worker, worker_threads)
    assert started.wait(2.0)

    worker.request_stop()
    _drain_until(app, lambda: probe.finished or probe.errors)
    assert probe.errors == []
    assert probe.finished == ["stopped"]


def test_worker_exception_goes_to_error_signal(app, worker_threads):
    def fn(stop_check):
        raise RuntimeError("mock boom")

    worker = TestWorker(fn, {})
    probe = _Probe()
    worker.finished.connect(probe.on_finished)
    worker.error.connect(probe.on_error)
    _launch(worker, worker_threads)
    _drain_until(app, lambda: probe.errors)

    app.processEvents()
    assert probe.errors == ["mock boom"]
    assert probe.finished == []
    probe.assert_slots_in_gui_thread()


def test_worker_confirm_request_and_response(app, worker_threads):
    holder = {}

    def fn(stop_check):
        return holder["worker"].wait_user_confirm("温箱通信失败", "是否重试当前温度点")

    worker = TestWorker(fn, {})
    holder["worker"] = worker
    probe = _Probe()
    probe.confirm_responder = worker.respond_confirm
    probe.confirm_response = True
    worker.finished.connect(probe.on_finished)
    worker.error.connect(probe.on_error)
    worker.confirm_request.connect(probe.on_confirm)
    _launch(worker, worker_threads)
    _drain_until(app, lambda: probe.finished or probe.errors)

    assert probe.errors == []
    assert probe.finished == [(True, True)]
    assert probe.confirm_requests == [("温箱通信失败", "是否重试当前温度点")]
    probe.assert_slots_in_gui_thread()


def _make_mock_runner(**callbacks):
    i2c = MockI2C()
    n6705c = MockN6705C()
    n6705c._mock_i2c = i2c
    acquisition = GPADCAcquisition(
        mode="IIC",
        mock_i2c=i2c,
        mock_mode=True,
        log_fn=callbacks.get("log_fn"),
        status_fn=callbacks.get("status_fn"),
    )
    return GPADCTestRunner(
        acquisition=acquisition,
        n6705c=n6705c,
        chamber=MockChamber(),
        n6705c_connected=True,
        chamber_connected=True,
        mock_mode=True,
        **callbacks,
    )


def test_temp_consistency_calibration_uses_worker_signals(app, worker_threads):
    holder = {}

    def emit_log(message):
        holder["worker"].log.emit(message)

    def emit_status(message, is_error=False):
        holder["worker"].status.emit(message, is_error)

    runner = _make_mock_runner(log_fn=emit_log, status_fn=emit_status)
    worker = TestWorker(runner.run, {
        "kind": "temp_consistency",
        "config": {
            "device_addr": 0x17,
            "reg_addr": 0x56,
            "iic_weight": 12,
            "temp_min": 25.0,
            "temp_max": 25.0,
            "temp_step": 1.0,
            "voltage_min": 0.1,
            "voltage_max": 0.2,
            "voltage_step": 0.1,
            "voltage_channel": 1,
            "soak_time": 0,
            "sample_cnt": 4,
        },
    })
    holder["worker"] = worker
    probe = _Probe()
    worker.finished.connect(probe.on_finished)
    worker.error.connect(probe.on_error)
    worker.log.connect(probe.on_log)
    worker.status.connect(probe.on_status)
    _launch(worker, worker_threads)
    _drain_until(app, lambda: probe.finished or probe.errors)

    assert probe.errors == []
    kind, result = probe.finished[0]
    assert kind == "temp_consistency"
    assert len(result["mean_cali"]) == 1
    assert len(result["mean_cali"][0]) == 2
    assert any(line.startswith("[INFO] Calibration: k=") for line in probe.logs)
    assert any(line.startswith("[DATA]") and "Voltage" in line and "RawMean" in line
               for line in probe.logs)
    assert ("设置温箱温度到 25.0°C", False) in probe.statuses
    probe.assert_slots_in_gui_thread()


_BASE_RUNNER_CONFIG = {
    "device_addr": 0x17,
    "reg_addr": 0x56,
    "iic_weight": 12,
    "sample_cnt": 4,
    "voltage_min": 0.1,
    "voltage_max": 0.2,
    "voltage_step": 0.1,
    "voltage_channel": 1,
    "temp_min": 25.0,
    "temp_max": 25.0,
    "temp_step": 1.0,
    "soak_time": 0,
}


@pytest.mark.parametrize(
    "kind, extra, expected_keys",
    [
        ("1000cnt", {}, {"avg", "min", "max", "std", "pp", "count", "raw",
                          "algo_effect", "raw_before_algo"}),
        ("force_voltage", {}, {"voltage", "mean", "min", "max", "raw_samples",
                                "raw_before_samples"}),
        ("linearity_traverse", {
            "linearity_n_reg_addr": 0x60, "linearity_p_reg_addr": 0x61,
            "linearity_link_np": True, "linearity_start": 0,
            "linearity_end": 2, "linearity_value_start": 0.0,
            "linearity_value_end": 2.0, "linearity_value_step": 1.0,
        }, {"voltage", "groups", "best_index", "stopped", "original_n", "original_p",
            "linearity"}),
        ("high_low_temp", {}, {"voltage", "mean", "min", "max"}),
        ("temp_consistency", {}, {"temp", "voltage", "mean", "min", "max",
                                   "mean_cali", "min_cali", "max_cali"}),
        ("multi_ch_temp", {
            "channels": [{
                "enabled": True, "name": "CH1", "sweep_enabled": False,
                "switch_writes_text": "",
            }],
            "pre_config": {"restore_after": True, "writes": []},
        }, {"temp", "sample_cnt", "channels"}),
        ("ft_calib_check", {
            "calib_p1": (0.1, 327.68),
            "calib_p2": (0.2, 655.36),
            "raw_tol_lsb": 100.0,
            "err_limit_mv": 100.0,
            "divider_ratio": 1.0,
        }, {"mode", "k", "b", "calib_points", "point_checks", "voltage",
            "actual_voltage", "raw_mean", "cal_volt", "err_mv", "stats",
            "err_limit_mv", "raw_tol_lsb", "passed"}),
    ],
)
def test_runner_preserves_seven_result_protocols(
    kind, extra, expected_keys, monkeypatch,
):
    from core.pmu_test.gpadc import gpadc_runner

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    payload = _make_mock_runner().run(kind, {**_BASE_RUNNER_CONFIG, **extra})

    assert isinstance(payload, tuple) and len(payload) == 2
    assert payload[0] == kind
    result = payload[1]
    assert isinstance(result, dict)
    assert expected_keys <= result.keys()
    if kind == "1000cnt":
        assert len(result["raw"]) == _BASE_RUNNER_CONFIG["sample_cnt"]
    elif kind == "linearity_traverse":
        assert len(result["groups"]) == 3
        assert [(group["n_value"], group["p_value"]) for group in result["groups"]] == [
            (0, 0), (1, 1), (2, 2),
        ]
        assert result["best_index"] in range(3)
        assert not result["stopped"]
    elif kind == "multi_ch_temp":
        assert len(result["channels"]) == 1
        assert {"name", "sweep", "voltage", "mean", "min", "max"} <= result["channels"][0].keys()


class _VoltageSource:
    def __init__(self, snapshot_error=None, restore_error=None, initial_enabled=False):
        self.snapshot_error = snapshot_error
        self.restore_error = restore_error
        self.set_calls = []
        self.set_mode_calls = []
        self.channel_state_calls = []
        self.mode = "VMETer"
        self.channel_enabled = initial_enabled

    def measure_voltage(self, channel):
        if self.snapshot_error is not None:
            raise self.snapshot_error
        return 3.3

    def set_voltage(self, channel, voltage):
        self.set_calls.append((channel, voltage))
        if voltage == 3.3 and self.restore_error is not None:
            raise self.restore_error

    def get_mode(self, channel):
        return self.mode

    def set_mode(self, channel, mode):
        self.set_mode_calls.append((channel, mode))
        self.mode = mode

    def get_channel_state(self, channel):
        return self.channel_enabled

    def channel_on(self, channel):
        self.channel_state_calls.append((channel, True))
        self.channel_enabled = True

    def channel_off(self, channel):
        self.channel_state_calls.append((channel, False))
        self.channel_enabled = False


class _SweepAcquisition:
    mode = "IIC"
    last_raw_before_algo = None
    last_algo_effect = None

    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def read_by_cnts(self, *args, **kwargs):
        if self.error is not None:
            raise self.error
        self.calls += 1
        value = 1000.0 + self.calls * 20.0
        return value, value + 1.0, value - 1.0, [value]


def _make_sweep_runner(source, acquisition, logs, statuses, progress_callback=None):
    return GPADCTestRunner(
        acquisition=acquisition,
        n6705c=source,
        n6705c_connected=True,
        mock_mode=False,
        log_fn=logs.append,
        status_fn=lambda message, is_error=False: statuses.append((message, is_error)),
        progress_callback=progress_callback,
    )


_N_REG = 0x60
_P_REG = 0x61


class _LinearityAcquisition(_SweepAcquisition):
    def __init__(self, error=None, original_n=0x0A, original_p=0x0B, restore_error=None):
        super().__init__(error=error)
        self.original_n = original_n
        self.original_p = original_p
        self.restore_error = restore_error
        self.regs = {(0x17, _N_REG): original_n, (0x17, _P_REG): original_p}
        self.weight_writes = []

    def read_reg(self, dev, reg, width):
        return self.regs.get((dev, reg), 0)

    def write_reg(self, dev, reg, val, width):
        self.weight_writes.append((reg, val))
        if reg == _P_REG and val == self.original_p and self.restore_error is not None:
            raise self.restore_error
        self.regs[(dev, reg)] = val


def _linearity_runner_config():
    return {
        **_BASE_RUNNER_CONFIG,
        "linearity_n_reg_addr": _N_REG,
        "linearity_p_reg_addr": _P_REG,
        "linearity_link_np": False,
        "linearity_n_start": 1,
        "linearity_n_end": 2,
        "linearity_n_value_start": 1.0,
        "linearity_n_value_end": 2.0,
        "linearity_n_value_step": 1.0,
        "linearity_p_start": 3,
        "linearity_p_end": 4,
        "linearity_p_value_start": 3.0,
        "linearity_p_value_end": 4.0,
        "linearity_p_value_step": 1.0,
    }


def _np_restore_writes():
    return [(_P_REG, 0x0B), (_N_REG, 0x0A)]


@pytest.mark.parametrize("outcome", ["success", "stop", "error"])
def test_linearity_traverse_restores_np_and_power_on_all_paths(outcome, monkeypatch):
    from core.pmu_test.gpadc import gpadc_runner

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    original_error = RuntimeError("linearity sample boom") if outcome == "error" else None
    source = _VoltageSource()
    acquisition = _LinearityAcquisition(error=original_error)
    logs, statuses, progress = [], [], []
    runner = _make_sweep_runner(
        source, acquisition, logs, statuses, progress_callback=progress.append,
    )
    stop_check = (lambda: acquisition.calls >= 5) if outcome == "stop" else None

    if outcome == "error":
        with pytest.raises(RuntimeError) as caught:
            runner.run("linearity_traverse", _linearity_runner_config())
        assert caught.value is original_error
        assert acquisition.weight_writes == [
            (_N_REG, 1), (_P_REG, 3), *_np_restore_writes(),
        ]
    else:
        kind, result = runner.run(
            "linearity_traverse", _linearity_runner_config(), stop_check=stop_check,
        )
        assert kind == "linearity_traverse"
        assert acquisition.weight_writes[-2:] == _np_restore_writes()
        if outcome == "success":
            assert [(group["n_value"], group["p_value"]) for group in result["groups"]] == [
                (1, 3), (1, 4), (2, 3), (2, 4),
            ]
            assert result["best_index"] == 0
            assert not result["stopped"]
            assert acquisition.calls == 8
            assert acquisition.weight_writes[:-2] == [
                (_N_REG, 1), (_P_REG, 3), (_N_REG, 1), (_P_REG, 4),
                (_N_REG, 2), (_P_REG, 3), (_N_REG, 2), (_P_REG, 4),
            ]
            assert progress == sorted(progress) and progress[-1] == 100
        else:
            assert len(result["groups"]) == 2
            assert result["stopped"]
            assert acquisition.calls == 5
    assert source.set_calls[-1] == (1, 3.3)
    assert source.mode == "VMETer"
    assert not source.channel_enabled


def test_linearity_stop_before_first_group_returns_empty_and_restores_np(monkeypatch):
    from core.pmu_test.gpadc import gpadc_runner

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    acquisition = _LinearityAcquisition()
    runner = _make_sweep_runner(_VoltageSource(), acquisition, [], [])
    kind, result = runner.run(
        "linearity_traverse", _linearity_runner_config(), stop_check=lambda: True,
    )
    assert kind == "linearity_traverse"
    assert result["groups"] == [] and result["best_index"] is None
    assert result["stopped"]
    assert acquisition.calls == 0
    assert acquisition.weight_writes == _np_restore_writes()


@pytest.mark.parametrize("outcome", ["success", "error"])
def test_linearity_p_restore_failure_still_restores_n(outcome, monkeypatch):
    from core.pmu_test.gpadc import gpadc_runner

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    original_error = RuntimeError("original linearity boom") if outcome == "error" else None
    restore_error = RuntimeError("p restore boom")
    acquisition = _LinearityAcquisition(error=original_error, restore_error=restore_error)
    logs, statuses = [], []
    runner = _make_sweep_runner(_VoltageSource(), acquisition, logs, statuses)

    if outcome == "error":
        with pytest.raises(RuntimeError) as caught:
            runner.run("linearity_traverse", _linearity_runner_config())
        assert caught.value is original_error
    else:
        kind, result = runner.run("linearity_traverse", _linearity_runner_config())
        assert kind == "linearity_traverse" and len(result["groups"]) == 4
    assert acquisition.weight_writes[-2:] == _np_restore_writes()
    assert acquisition.regs[(0x17, _N_REG)] == 0x0A
    assert any("P Weight 寄存器恢复失败" in line and "p restore boom" in line for line in logs)
    assert any(is_error and "P Weight 寄存器恢复失败" in message for message, is_error in statuses)


@pytest.mark.parametrize("outcome", ["success", "stop", "error"])
@pytest.mark.parametrize("initial_enabled", [False, True])
def test_force_voltage_restores_snapshot_on_all_paths(outcome, initial_enabled, monkeypatch):
    from core.pmu_test.gpadc import gpadc_runner

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    original_error = RuntimeError("sample boom") if outcome == "error" else None
    source = _VoltageSource(initial_enabled=initial_enabled)
    acquisition = _SweepAcquisition(original_error)
    runner = _make_sweep_runner(source, acquisition, [], [])
    stop_check = (lambda: True) if outcome == "stop" else None

    if outcome == "error":
        with pytest.raises(RuntimeError) as caught:
            runner.run("force_voltage", _BASE_RUNNER_CONFIG, stop_check=stop_check)
        assert caught.value is original_error
    else:
        kind, result = runner.run("force_voltage", _BASE_RUNNER_CONFIG, stop_check=stop_check)
        assert kind == "force_voltage"
        assert bool(result["voltage"]) is (outcome == "success")
    assert source.set_calls[-1] == (1, 3.3)
    assert source.set_mode_calls == [(1, "PS2Q"), (1, "VMETer")]
    assert source.channel_state_calls == [(1, True), (1, initial_enabled)]
    assert source.mode == "VMETer"
    assert source.channel_enabled is initial_enabled


@pytest.mark.parametrize("outcome", ["success", "error"])
def test_restore_failure_does_not_replace_result_or_original_exception(outcome, monkeypatch):
    from core.pmu_test.gpadc import gpadc_runner

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    original_error = RuntimeError("original sample boom") if outcome == "error" else None
    source = _VoltageSource(restore_error=RuntimeError("restore boom"))
    acquisition = _SweepAcquisition(original_error)
    logs, statuses = [], []
    runner = _make_sweep_runner(source, acquisition, logs, statuses)

    if outcome == "error":
        with pytest.raises(RuntimeError) as caught:
            runner.run("force_voltage", _BASE_RUNNER_CONFIG)
        assert caught.value is original_error
    else:
        kind, result = runner.run("force_voltage", _BASE_RUNNER_CONFIG)
        assert kind == "force_voltage" and len(result["voltage"]) == 2
    assert any("CH1 电压恢复失败" in line and "restore boom" in line for line in logs)
    assert any(is_error and "CH1 电压恢复失败" in message for message, is_error in statuses)
    assert source.mode == "VMETer"
    assert source.channel_enabled is False


def test_voltage_snapshot_failure_propagates_before_test():
    original_error = RuntimeError("snapshot boom")
    source = _VoltageSource(snapshot_error=original_error)
    acquisition = _SweepAcquisition()
    runner = _make_sweep_runner(source, acquisition, [], [])

    with pytest.raises(RuntimeError) as caught:
        runner.run("force_voltage", _BASE_RUNNER_CONFIG)
    assert caught.value is original_error
    assert acquisition.calls == 0
    assert source.set_calls == []


def test_high_low_temp_current_monitoring_records_each_temperature(monkeypatch):
    from core.pmu_test.gpadc import gpadc_runner

    class CurrentSource(MockN6705C):
        def __init__(self):
            super().__init__()
            self.calls = []

        def measure_current(self, channel):
            self.calls.append(channel)
            return 0.001 * len(self.calls)

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    source = CurrentSource()
    logs = []
    runner = _make_mock_runner(log_fn=logs.append)
    runner.n6705c = source
    config = {
        **_BASE_RUNNER_CONFIG,
        "temp_min": 20.0,
        "temp_max": 60.0,
        "temp_step": 20.0,
        "current_monitor_enabled": True,
        "current_monitor_channel": 3,
    }

    kind, result = runner.run("high_low_temp", config)

    assert kind == "high_low_temp"
    assert source.calls == [3, 3, 3]
    assert result["current_channel"] == 3
    assert result["current_a"] == pytest.approx([0.001, 0.002, 0.003])
    assert len(result["current_a"]) == len(result["voltage"])
    assert any(line.startswith("[DATA]") and "RawMean" in line and "CH3 Current (A)" in line
               for line in logs)

    source.calls.clear()
    config["current_monitor_enabled"] = False
    _, result_without_monitor = runner.run("high_low_temp", config)
    assert source.calls == []
    assert "current_a" not in result_without_monitor
    assert "current_channel" not in result_without_monitor


def test_high_low_temp_confirm_abort_preserves_result_and_restores_chamber():
    class FailingChamber(MockChamber):
        def __init__(self):
            super().__init__()
            self.failed = False

        def set_temperature(self, temp):
            if temp == 40.0 and not self.failed:
                self.failed = True
                raise RuntimeError("chamber offline")
            super().set_temperature(temp)

    confirmations = []

    def confirm(title, message):
        confirmations.append((title, message))
        return True, False

    runner = _make_mock_runner(confirm_fn=confirm)
    runner.mock_mode = False
    runner.chamber = FailingChamber()
    config = {**_BASE_RUNNER_CONFIG, "temp_min": 40.0, "temp_max": 40.0}

    kind, result = runner.run("high_low_temp", config)

    assert kind == "high_low_temp"
    assert result == {"voltage": [], "mean": [], "min": [], "max": []}
    assert len(confirmations) == 1 and confirmations[0][0] == "温箱通信失败"
    assert runner.chamber.get_current_temp() == 25.0


def test_page_high_low_temp_current_monitor_controls_and_config(app, monkeypatch):
    from ui.widgets.config_memory import ConfigMemory

    monkeypatch.setattr(ConfigMemory, "watch", lambda self, widget: None)
    monkeypatch.setattr(ConfigMemory, "restore", lambda self: None)

    from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI

    page = GPADCTestUI()
    try:
        high_low_index = page.test_item_combo.findData(page.TEST_HIGH_LOW_TEMP)
        page.test_item_combo.setCurrentIndex(high_low_index)
        app.processEvents()

        assert not page.current_monitor_frame.isHidden()
        assert page.n6705c_card.isHidden()
        assert not page.chamber_card.isHidden()
        assert page.current_monitor_channel.isHidden()

        page.current_monitor_switch.setChecked(True)
        channel_index = page.current_monitor_channel.findData(3)
        page.current_monitor_channel.setCurrentIndex(channel_index)
        app.processEvents()

        assert not page.n6705c_card.isHidden()
        assert not page.current_monitor_channel.isHidden()
        assert page.current_monitor_channel.isEnabled()
        assert page._required_instruments() == ["chamber", "n6705c"]
        assert page.get_test_config()["current_monitor"] == {
            "enabled": True, "channel": 3,
        }

        page.current_monitor_switch.setChecked(False)
        assert page.n6705c_card.isHidden()
        ok, _ = page.apply_config_to_controls({
            "current_monitor": {"enabled": True, "channel": 3},
        }, silent=True)
        assert ok
        assert page.current_monitor_switch.isChecked()
        assert page.current_monitor_channel.currentData() == 3
        assert not page.n6705c_card.isHidden()

        page._set_ui_enabled(False)
        assert not page.current_monitor_switch.isEnabled()
        assert not page.current_monitor_channel.isEnabled()
        page._set_ui_enabled(True)
        assert page.current_monitor_switch.isEnabled()
        assert page.current_monitor_channel.isEnabled()

        page.test_item_combo.setCurrentIndex(
            page.test_item_combo.findData(page.TEST_1000CNT)
        )
        assert page.current_monitor_frame.isHidden()
        assert page.instruments_panel.isHidden()
    finally:
        if isValid(page):
            page.cleanup_threads()
            page.deleteLater()
        app.processEvents()
        _drain_until(app, lambda: not isValid(page))


def test_page_linearity_controls_config_and_validation(app, monkeypatch):
    from ui.widgets.config_memory import ConfigMemory

    monkeypatch.setattr(ConfigMemory, "watch", lambda self, widget: None)
    monkeypatch.setattr(ConfigMemory, "restore", lambda self: None)
    monkeypatch.setattr(ConfigMemory, "save_now", lambda self: None)

    from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI

    page = GPADCTestUI()
    try:
        page.toggle_recent_btn.setChecked(True)
        page.test_item_combo.setCurrentIndex(
            page.test_item_combo.findData(page.TEST_LINEARITY_TRAVERSE)
        )
        app.processEvents()

        assert not page.linearity_params_frame.isHidden()
        assert not page.voltage_params_frame.isHidden()
        assert page.metrics_row.isHidden()
        assert page.toggle_recent_btn.isHidden()
        assert page.recent_curve_splitter.widget(1).isHidden()
        assert not page.n6705c_card.isHidden()

        assert page.linearity_link_np.isChecked()
        assert not page.linearity_shared_range_frame.isHidden()
        assert page.linearity_independent_range_frame.isHidden()
        page.linearity_n_reg_addr.setText("0x60")
        page.linearity_p_reg_addr.setText("0x61")
        page.linearity_start.setText("0x0")
        page.linearity_end.setText("13")
        page.linearity_value_start.setText("0x3b00")
        page.linearity_value_end.setText("0x3c50")
        page.linearity_value_step.setText("10")
        config = page.get_test_config()
        assert config["linearity_n_reg_addr"] == "0x60"
        assert config["linearity_p_reg_addr"] == "0x61"
        assert config["linearity_link_np"] is True
        assert config["linearity_start"] == "0x0"
        assert config["linearity_end"] == "13"
        assert config["linearity_value_start"] == "0x3b00"
        assert config["linearity_value_end"] == "0x3c50"
        assert config["linearity_value_step"] == "10"
        assert page._parse_linearity_inputs() == {
            "linearity_n_reg_addr": 0x60,
            "linearity_p_reg_addr": 0x61,
            "linearity_link_np": True,
            "linearity_start": 0,
            "linearity_end": 13,
            "linearity_value_start": float(0x3B00),
            "linearity_value_end": float(0x3C50),
            "linearity_value_step": 10.0,
        }

        ok, _ = page.apply_config_to_controls({
            "linearity_n_reg_addr": "0x62",
            "linearity_p_reg_addr": "0x63",
            "linearity_link_np": False,
            "linearity_n_start": "2",
            "linearity_n_end": "4",
            "linearity_n_value_start": "2",
            "linearity_n_value_end": "4",
            "linearity_n_value_step": "2",
            "linearity_p_start": "1",
            "linearity_p_end": "3",
            "linearity_p_value_start": "1",
            "linearity_p_value_end": "3",
            "linearity_p_value_step": "1",
        }, silent=True)
        assert ok
        assert not page.linearity_link_np.isChecked()
        assert page.linearity_shared_range_frame.isHidden()
        assert not page.linearity_independent_range_frame.isHidden()
        assert page.linearity_n_reg_addr.text() == "0x62"
        assert page.linearity_p_reg_addr.text() == "0x63"
        assert page._parse_linearity_inputs() == {
            "linearity_n_reg_addr": 0x62,
            "linearity_p_reg_addr": 0x63,
            "linearity_link_np": False,
            "linearity_n_start": 2,
            "linearity_n_end": 4,
            "linearity_n_value_start": 2.0,
            "linearity_n_value_end": 4.0,
            "linearity_n_value_step": 2.0,
            "linearity_p_start": 1,
            "linearity_p_end": 3,
            "linearity_p_value_start": 1.0,
            "linearity_p_value_end": 3.0,
            "linearity_p_value_step": 1.0,
        }

        page._set_ui_enabled(False)
        assert not page.linearity_link_np.isEnabled()
        assert not page.linearity_n_reg_addr.isEnabled()
        assert not page.linearity_p_reg_addr.isEnabled()
        assert not page.linearity_n_start.isEnabled()
        assert not page.linearity_p_value_step.isEnabled()
        page._set_ui_enabled(True)
        assert page.linearity_link_np.isEnabled()

        page.linearity_n_value_step.setText("0")
        assert page._parse_linearity_inputs() is None
        page._start_test()
        assert not page.is_test_running and page.test_thread is None
        page.linearity_n_value_step.setText("2")
        page.uart_radio.setChecked(True)
        assert page._parse_linearity_inputs() is None
        page.iic_radio.setChecked(True)
        page.linearity_link_np.setChecked(True)
        assert not page.linearity_shared_range_frame.isHidden()
        assert page.linearity_independent_range_frame.isHidden()
        assert page.linearity_start.text() == "0x0"

        page.test_item_combo.setCurrentIndex(
            page.test_item_combo.findData(page.TEST_FORCE_VOLTAGE)
        )
        assert page.linearity_params_frame.isHidden()
        assert not page.metrics_row.isHidden()
        assert not page.toggle_recent_btn.isHidden()
    finally:
        if isValid(page):
            page.cleanup_threads()
            page.deleteLater()
        app.processEvents()
        _drain_until(app, lambda: not isValid(page))


@pytest.mark.parametrize(
    "link_np, expected_pairs",
    [
        (True, [(0, 0), (1, 1)]),
        (False, [(0, 2), (0, 3), (1, 2), (1, 3)]),
    ],
)
def test_page_mock_linearity_traverse_plots_best_and_exports(
    app, monkeypatch, link_np, expected_pairs,
):
    import debug_config
    import openpyxl
    import pyqtgraph as pg
    from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin, execution_mixin
    from ui.widgets.config_memory import ConfigMemory

    monkeypatch.setattr(debug_config, "DEBUG_MOCK", True)
    monkeypatch.setattr(acquisition_mixin, "DEBUG_MOCK", True)
    monkeypatch.setattr(execution_mixin, "DEBUG_MOCK", True)
    monkeypatch.setattr(ConfigMemory, "watch", lambda self, widget: None)
    monkeypatch.setattr(ConfigMemory, "restore", lambda self: None)
    monkeypatch.setattr(ConfigMemory, "save_now", lambda self: None)

    from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI

    page = GPADCTestUI()
    errors = []
    worker = None
    thread = None
    exported = []
    try:
        page._on_test_error = errors.append
        page.test_item_combo.setCurrentIndex(
            page.test_item_combo.findData(page.TEST_LINEARITY_TRAVERSE)
        )
        page.sample_count.setValue(4)
        page.voltage_min.setValue(0.1)
        page.voltage_max.setValue(0.3)
        page.voltage_step.setValue(0.1)
        page.linearity_n_reg_addr.setText("0x60")
        page.linearity_p_reg_addr.setText("0x61")
        page.linearity_link_np.setChecked(link_np)
        if link_np:
            page.linearity_start.setText("0")
            page.linearity_end.setText("1")
            page.linearity_value_start.setText("0")
            page.linearity_value_end.setText("1")
            page.linearity_value_step.setText("1")
        else:
            page.linearity_n_start.setText("0")
            page.linearity_n_end.setText("1")
            page.linearity_n_value_start.setText("0")
            page.linearity_n_value_end.setText("1")
            page.linearity_n_value_step.setText("1")
            page.linearity_p_start.setText("2")
            page.linearity_p_end.setText("3")
            page.linearity_p_value_start.setText("2")
            page.linearity_p_value_end.setText("3")
            page.linearity_p_value_step.setText("1")
        page._start_test()
        worker = page._test_worker
        thread = page.test_thread
        assert worker is not None and thread is not None
        _drain_until(app, lambda: not page.is_test_running)

        assert errors == []
        result = page._export_data["linearity_traverse"]
        assert [(group["n_value"], group["p_value"]) for group in result["groups"]] == expected_pairs
        assert result["best_index"] in range(len(expected_pairs))
        assert page._export_data["params"]["group_count"] == len(expected_pairs)
        assert "best_n" in page._export_data["params"]
        assert "best_p" in page._export_data["params"]
        assert page._recent_test_records == []
        assert page._loaded_record is None
        assert page._chart_image_bytes is not None

        plots = page.chart_placeholder.findChildren(pg.PlotWidget)
        assert len(plots) == 1
        curves = [
            item for item in plots[0].plotItem.items
            if isinstance(item, pg.PlotDataItem)
        ]
        assert len(curves) == len(expected_pairs)
        best_curves = [curve for curve in curves if curve.opts["pen"].width() == 3]
        assert len(best_curves) == 1
        assert best_curves[0].name().startswith("BEST N=0x")

        results_dir = Path(__file__).resolve().parents[1] / "Results"
        before = set(results_dir.glob("GPADC_LinearityTraverse_*.xlsx"))
        page.export_result()
        exported = list(set(results_dir.glob("GPADC_LinearityTraverse_*.xlsx")) - before)
        assert len(exported) == 1
        workbook = openpyxl.load_workbook(exported[0], read_only=True, data_only=True)
        try:
            assert workbook.sheetnames == ["Summary", "Sweep Data"]
            sweep = workbook["Sweep Data"]
            assert sweep.max_row == 1 + 3 * len(expected_pairs)
            assert [sweep.cell(1, 1).value, sweep.cell(1, 2).value] == [
                "N Weight", "P Weight",
            ]
            expected_mode = "Link N = P" if link_np else "Independent N/P Matrix"
            assert workbook["Summary"]["B6"].value == expected_mode
        finally:
            workbook.close()
    finally:
        for path in exported:
            path.unlink(missing_ok=True)
        if isValid(page):
            page.cleanup_threads()
            page.deleteLater()
        if worker is not None and isValid(worker):
            worker.request_stop()
            worker.respond_confirm(False)
        if thread is not None and isValid(thread):
            thread.quit()
        app.processEvents()
        _drain_until(app, lambda: not isValid(page))
        _drain_until(app, lambda: not isValid(thread) or not thread.isRunning())


def test_page_mock_1000cnt_runs_core_runner_to_completion(app, monkeypatch):
    import debug_config
    from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin, execution_mixin
    from ui.widgets.config_memory import ConfigMemory

    monkeypatch.setattr(debug_config, "DEBUG_MOCK", True)
    monkeypatch.setattr(acquisition_mixin, "DEBUG_MOCK", True)
    monkeypatch.setattr(execution_mixin, "DEBUG_MOCK", True)
    monkeypatch.setattr(ConfigMemory, "watch", lambda self, widget: None)
    monkeypatch.setattr(ConfigMemory, "restore", lambda self: None)

    from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI

    page = GPADCTestUI()
    errors = []
    worker = None
    thread = None
    try:
        page._on_test_error = errors.append
        page.sample_count.setValue(8)
        page._start_test()
        worker = page._test_worker
        thread = page.test_thread
        assert worker is not None and thread is not None
        _drain_until(app, lambda: not page.is_test_running)

        assert errors == []
        assert page._test_runner is None
        assert page._test_worker is None
        assert page._recent_test_records[-1]["kind"] == "1000cnt"
        assert page._recent_test_records[-1]["params"]["count"] == 8
    finally:
        if isValid(page):
            page.cleanup_threads()
            page.deleteLater()
        if worker is not None and isValid(worker):
            worker.request_stop()
            worker.respond_confirm(False)
        if thread is not None and isValid(thread):
            thread.quit()
        app.processEvents()
        _drain_until(app, lambda: not isValid(page))
        _drain_until(app, lambda: not isValid(thread) or not thread.isRunning())


def test_page_start_uses_core_runner_and_delete_is_nonblocking(app, monkeypatch):
    import debug_config
    from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin, execution_mixin
    from ui.widgets.config_memory import ConfigMemory

    monkeypatch.setattr(debug_config, "DEBUG_MOCK", True)
    monkeypatch.setattr(acquisition_mixin, "DEBUG_MOCK", True)
    monkeypatch.setattr(execution_mixin, "DEBUG_MOCK", True)
    monkeypatch.setattr(ConfigMemory, "watch", lambda self, widget: None)
    monkeypatch.setattr(ConfigMemory, "restore", lambda self: None)

    from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI

    started = threading.Event()

    def blocking_test(self, kind, config, stop_check=None):
        started.set()
        while not stop_check():
            time.sleep(0.005)
        return None

    monkeypatch.setattr(GPADCTestRunner, "run", blocking_test)
    page = GPADCTestUI()
    worker = None
    test_thread = None
    search_thread = None
    cleanup_seconds = None
    parents_detached = False
    try:
        page._start_test()
        worker = page._test_worker
        bound_runner = worker._fn.__self__
        assert isinstance(bound_runner, GPADCTestRunner)
        assert bound_runner is page._test_runner
        assert not isinstance(bound_runner, GPADCTestUI)
        assert not isinstance(
            bound_runner,
            (execution_mixin._ExecutionMixin, acquisition_mixin._AcquisitionMixin),
        )
        test_thread = page.test_thread
        search_thread = QThread(page)
        page._serial_search_thread = search_thread
        page._serial_search_worker = None
        search_thread.start()
        assert started.wait(2.0)
        assert test_thread.isRunning()

        begin = time.monotonic()
        page.cleanup_threads()
        cleanup_seconds = time.monotonic() - begin
        parents_detached = test_thread.parent() is None and search_thread.parent() is None
        assert page.test_thread is None
        page.deleteLater()
        app.processEvents()
    finally:
        if isValid(page):
            page.cleanup_threads()
            page.deleteLater()
        if worker is not None and isValid(worker):
            worker.request_stop()
            worker.respond_confirm(False)
        for thread in (test_thread, search_thread):
            if thread is not None and isValid(thread):
                thread.quit()
        app.processEvents()
        _drain_until(app, lambda: not isValid(page))
        _drain_until(
            app,
            lambda: not isValid(test_thread) or not test_thread.isRunning(),
        )
        _drain_until(
            app,
            lambda: not isValid(search_thread) or not search_thread.isRunning(),
        )

    assert cleanup_seconds is not None and cleanup_seconds < 0.5
    assert parents_detached


@pytest.mark.parametrize(
    "path",
    sorted((_ROOT / "core" / "pmu_test" / "gpadc").glob("*.py")),
    ids=lambda path: path.name,
)
def test_core_gpadc_has_no_ui_or_qwidgets_dependency(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] != "ui"
                assert not alias.name.startswith("PySide6.QtWidgets")
                assert alias.name != "QWidget"
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert module.split(".")[0] != "ui"
            assert not module.startswith("PySide6.QtWidgets")
            assert all(alias.name != "QWidget" for alias in node.names)
        elif isinstance(node, ast.Name):
            assert node.id != "QWidget"
        elif isinstance(node, ast.Attribute):
            assert node.attr != "QWidget"


def test_gpadc_cleanup_has_no_blocking_wait():
    path = (
        _ROOT / "ui" / "pages" / "pmu_test" / "gpadc_test" /
        "mixins" / "execution_mixin.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    waits = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "wait"
    ]
    assert waits == []
