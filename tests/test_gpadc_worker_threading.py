# -*- coding: utf-8 -*-
"""GPADC worker 真实 QThread、页面销毁与 UI 线程亲和性回归。"""

import ast
import os
import sys
import threading
import time
from pathlib import Path
from types import MappingProxyType, MethodType

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from PySide6.QtCore import QObject, QThread, Slot
from PySide6.QtWidgets import QApplication
from shiboken6 import isValid

from core.pmu_test.gpadc import TestWorker


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _drain_until(app, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("等待 Qt 线程/事件收尾超时")
        app.processEvents()
        time.sleep(0.001)
    app.processEvents()


class _Probe(QObject):
    def __init__(self):
        super().__init__()
        self.gui_thread = QThread.currentThread()
        self.slot_threads = []
        self.finished = []
        self.errors = []
        self.logs = []
        self.statuses = []

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


class _AcquisitionHarness:
    """只混入采样职责；任何绕开信号的直接 UI 调用都立即失败。"""

    def __init__(self):
        self._test_worker = None
        self._acq_mode_snapshot = "IIC"
        self._uart_keyword_snapshot = ""
        self._calib_points_snapshot = None
        self._algorithm_snapshot = None
        self._outlier_filter_snapshot = None
        self._last_algo_effect = None
        self._last_raw_before_algo = None

    def _append_log(self, message):
        raise AssertionError(f"后台直接写日志 UI: {message}")

    def set_system_status(self, message, is_error=False):
        raise AssertionError(f"后台直接写状态 UI: {message}")

    @staticmethod
    def _fmt_data_value(value):
        return str(value)


def test_temp_consistency_calibration_uses_worker_signals(
    app, worker_threads, monkeypatch,
):
    import debug_config
    from ui.pages.pmu_test.gpadc_test.mixins import acquisition_mixin
    from ui.pages.pmu_test.gpadc_test.mixins.acquisition_mixin import _AcquisitionMixin

    monkeypatch.setattr(debug_config, "DEBUG_MOCK", True)
    monkeypatch.setattr(acquisition_mixin, "DEBUG_MOCK", True)

    class Harness(_AcquisitionMixin, _AcquisitionHarness):
        pass

    harness = Harness()
    worker = TestWorker(harness.gpadc_temp_consistency_test, {
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
    })
    harness._test_worker = worker
    probe = _Probe()
    worker.finished.connect(probe.on_finished)
    worker.error.connect(probe.on_error)
    worker.log.connect(probe.on_log)
    worker.status.connect(probe.on_status)
    _launch(worker, worker_threads)
    _drain_until(app, lambda: probe.finished or probe.errors)

    assert probe.errors == []
    result = probe.finished[0]
    assert len(result["mean_cali"]) == 1
    assert len(result["mean_cali"][0]) == 2
    assert any(line.startswith("[INFO] Calibration: k=") for line in probe.logs)
    assert any(line.startswith("Voltage,RawMean,mean_cali") for line in probe.logs)
    assert ("设置温箱温度到 25.0°C", False) in probe.statuses
    probe.assert_slots_in_gui_thread()


def test_page_delete_during_running_worker_is_nonblocking(app, monkeypatch):
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

    def blocking_test(self, stop_check=None, **kwargs):
        started.set()
        while not stop_check():
            time.sleep(0.005)
        return None

    page = GPADCTestUI()
    page._run_1000cnt_test = MethodType(blocking_test, page)
    worker = None
    test_thread = None
    search_thread = None
    cleanup_seconds = None
    parents_detached = False
    try:
        page._start_test()
        worker = page._test_worker
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
        _drain_until(
            app,
            lambda: (
                not isValid(page)
                and all(
                    thread is None or not isValid(thread) or not thread.isRunning()
                    for thread in (test_thread, search_thread)
                )
            ),
        )

    assert cleanup_seconds is not None and cleanup_seconds < 0.5
    assert parents_detached


def test_core_worker_has_no_qwidgets_dependency():
    path = _ROOT / "core" / "pmu_test" / "gpadc" / "gpadc_worker.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("PySide6.QtWidgets") for alias in node.names)
            assert all(alias.name != "QWidget" for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "PySide6.QtWidgets"
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
