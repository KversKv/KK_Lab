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
    assert any(line.startswith("Voltage,RawMean,mean_cali") for line in probe.logs)
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
def test_runner_preserves_six_result_protocols(
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
    elif kind == "multi_ch_temp":
        assert len(result["channels"]) == 1
        assert {"name", "sweep", "voltage", "mean", "min", "max"} <= result["channels"][0].keys()


class _VoltageSource:
    def __init__(self, snapshot_error=None, restore_error=None):
        self.snapshot_error = snapshot_error
        self.restore_error = restore_error
        self.set_calls = []

    def measure_voltage(self, channel):
        if self.snapshot_error is not None:
            raise self.snapshot_error
        return 3.3

    def set_voltage(self, channel, voltage):
        self.set_calls.append((channel, voltage))
        if voltage == 3.3 and self.restore_error is not None:
            raise self.restore_error


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


def _make_sweep_runner(source, acquisition, logs, statuses):
    return GPADCTestRunner(
        acquisition=acquisition,
        n6705c=source,
        n6705c_connected=True,
        mock_mode=False,
        log_fn=logs.append,
        status_fn=lambda message, is_error=False: statuses.append((message, is_error)),
    )


@pytest.mark.parametrize("outcome", ["success", "stop", "error"])
def test_force_voltage_restores_snapshot_on_all_paths(outcome, monkeypatch):
    from core.pmu_test.gpadc import gpadc_runner

    monkeypatch.setattr(gpadc_runner.time, "sleep", lambda seconds: None)
    original_error = RuntimeError("sample boom") if outcome == "error" else None
    source = _VoltageSource()
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
    assert "Temp, RawMean, RawMin, RawMax, CH3 Current (A)" in logs

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
