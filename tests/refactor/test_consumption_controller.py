# -*- coding: utf-8 -*-
"""
Phase 5 — consumption_controller mock 单测（无 pytest 也可独立运行）。

    python tests/refactor/test_consumption_controller.py

覆盖：
  - 控制器初始状态
  - start_download 信号编排（patch QThread / Worker / detect_chip_from_bin）
  - stop_download 空闲态 no-op
  - Worker 槽函数（state_changed / finished / error）信号转发
  - 线程清理回调
"""

import os
import sys
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

from core.consumption_test.consumption_controller import ConsumptionController
from lib.download_tools.download_script import DownloadMode

_APP = QApplication.instance() or QApplication([])


def test_controller_init():
    c = ConsumptionController()
    assert c.is_download_running() is False
    assert c._download_thread is None
    assert c._download_worker is None


def test_start_download_emits_signals():
    c = ConsumptionController()
    logs = []
    started_sizes = []
    c.log_message.connect(logs.append)
    c.download_started.connect(started_sizes.append)

    with mock.patch(
        "core.consumption_test.consumption_controller.detect_chip_from_bin",
        return_value="BES2700",
    ), mock.patch(
        "core.consumption_test.consumption_controller.DownloadWorker"
    ) as MockWorker, mock.patch(
        "core.consumption_test.consumption_controller.QThread"
    ) as MockThread:
        fake_thread = MockThread.return_value
        fake_thread.isRunning.return_value = True
        c.start_download("COM5", "/fake/path.bin", DownloadMode.FLASH)

    assert any("Starting download" in l for l in logs)
    assert any("COM5" in l for l in logs)
    assert any("BES2700" in l for l in logs)
    assert len(started_sizes) == 1
    MockWorker.assert_called_once_with("COM5", "/fake/path.bin", DownloadMode.FLASH)
    assert fake_thread.start.called
    assert c.is_download_running() is True


def test_start_download_chip_not_detected():
    c = ConsumptionController()
    logs = []
    c.log_message.connect(logs.append)

    with mock.patch(
        "core.consumption_test.consumption_controller.detect_chip_from_bin",
        return_value=None,
    ), mock.patch(
        "core.consumption_test.consumption_controller.DownloadWorker"
    ), mock.patch(
        "core.consumption_test.consumption_controller.QThread"
    ) as MockThread:
        MockThread.return_value.isRunning.return_value = True
        c.start_download("COM3", "/nope.bin", DownloadMode.RAMRUN)

    assert any("Could not detect chip model" in l for l in logs)
    assert any("ramrun" in l.lower() for l in logs)


def test_start_download_guard_when_running():
    c = ConsumptionController()
    with mock.patch.object(c, "is_download_running", return_value=True), \
         mock.patch("core.consumption_test.consumption_controller.DownloadWorker") as MockWorker:
        c.start_download("COM5", "/fake.bin", DownloadMode.FLASH)
        assert MockWorker.called is False


def test_stop_download_idle_noop():
    c = ConsumptionController()
    c.stop_download()
    assert c.is_download_running() is False


def test_on_worker_state_changed():
    c = ConsumptionController()
    logs = []
    states = []
    c.log_message.connect(logs.append)
    c.download_state_changed.connect(states.append)
    c._on_worker_state_changed("programming")
    assert states == ["programming"]
    assert any("State: programming" in l for l in logs)


def test_on_worker_finished_success():
    c = ConsumptionController()
    logs = []
    results = []
    c.log_message.connect(logs.append)
    c.download_finished.connect(results.append)
    result = mock.MagicMock()
    result.success = True
    result.error_message = ""
    c._on_worker_finished(result)
    assert len(results) == 1
    assert any("succeeded" in l for l in logs)


def test_on_worker_finished_failure():
    c = ConsumptionController()
    logs = []
    c.log_message.connect(logs.append)
    result = mock.MagicMock()
    result.success = False
    result.error_message = "timeout"
    c._on_worker_finished(result)
    assert any("timeout" in l for l in logs)


def test_on_worker_error():
    c = ConsumptionController()
    logs = []
    errors = []
    c.log_message.connect(logs.append)
    c.download_error.connect(errors.append)
    c._on_worker_error("boom")
    assert errors == ["boom"]
    assert any("boom" in l for l in logs)


def test_on_thread_cleaned():
    c = ConsumptionController()
    c._download_thread = mock.MagicMock()
    c._download_worker = mock.MagicMock()
    cleaned = []
    c.download_cleaned.connect(lambda: cleaned.append(True))
    c._on_thread_cleaned()
    assert c._download_thread is None
    assert c._download_worker is None
    assert len(cleaned) == 1


def test_auto_test_init():
    c = ConsumptionController()
    assert c.is_auto_test_running() is False
    assert c._auto_test_thread is None
    assert c._auto_test_worker is None


def test_start_auto_test_creates_worker():
    c = ConsumptionController()
    with mock.patch(
        "core.consumption_test.consumption_controller._AutoTestWorker"
    ) as MockWorker, mock.patch(
        "core.consumption_test.consumption_controller.QThread"
    ) as MockThread:
        fake_thread = MockThread.return_value
        fake_thread.isRunning.return_value = True
        c.start_auto_test({"com_port": "COM5", "test_time": 1.0})
    assert MockWorker.called
    assert fake_thread.start.called
    assert c.is_auto_test_running() is True


def test_start_auto_test_guard_when_running():
    c = ConsumptionController()
    with mock.patch.object(c, "is_auto_test_running", return_value=True), \
         mock.patch("core.consumption_test.consumption_controller._AutoTestWorker") as MockWorker:
        c.start_auto_test({})
        assert MockWorker.called is False


def test_stop_auto_test_idle_noop():
    c = ConsumptionController()
    c.stop_auto_test()
    assert c.is_auto_test_running() is False


def test_on_auto_channel_result():
    c = ConsumptionController()
    results = []
    c.auto_test_channel_result.connect(lambda *a: results.append(a))
    c._on_auto_channel_result("N6705C", 1, 0.5, "phase1")
    assert results == [("N6705C", 1, 0.5, "phase1")]


def test_on_auto_test_summary():
    c = ConsumptionController()
    summaries = []
    c.auto_test_summary.connect(summaries.append)
    c._on_auto_test_summary({"avg": 1.0})
    assert summaries == [{"avg": 1.0}]


def test_on_auto_progress():
    c = ConsumptionController()
    vals = []
    c.auto_test_progress.connect(vals.append)
    c._on_auto_progress(0.75)
    assert vals == [0.75]


def test_on_auto_download_state():
    c = ConsumptionController()
    logs = []
    states = []
    c.log_message.connect(logs.append)
    c.auto_test_download_state.connect(states.append)
    c._on_auto_download_state("syncing")
    assert states == ["syncing"]
    assert any("syncing" in l for l in logs)


def test_on_auto_error():
    c = ConsumptionController()
    logs = []
    errors = []
    c.log_message.connect(logs.append)
    c.auto_test_error.connect(errors.append)
    c._on_auto_error("crash")
    assert errors == ["crash"]
    assert any("crash" in l for l in logs)


def test_on_auto_finished():
    c = ConsumptionController()
    logs = []
    finished = []
    c.log_message.connect(logs.append)
    c.auto_test_finished.connect(lambda: finished.append(True))
    c._on_auto_finished()
    assert len(finished) == 1
    assert any("completed" in l for l in logs)


def test_on_auto_thread_cleaned():
    c = ConsumptionController()
    c._auto_test_thread = mock.MagicMock()
    c._auto_test_worker = mock.MagicMock()
    cleaned = []
    c.auto_test_cleaned.connect(lambda: cleaned.append(True))
    c._on_auto_thread_cleaned()
    assert c._auto_test_thread is None
    assert c._auto_test_worker is None
    assert len(cleaned) == 1


if __name__ == "__main__":
    _fails = 0
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            try:
                _fn()
                print(f"  PASS  {_name}")
            except Exception as _e:
                _fails += 1
                print(f"  FAIL  {_name}: {_e}")
    _total = len([n for n in globals() if n.startswith("test_")])
    print(f"\n{'='*40}\nResult: {_total - _fails} passed, {_fails} failed")
    sys.exit(1 if _fails else 0)
