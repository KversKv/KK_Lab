# -*- coding: utf-8 -*-
"""Vmin Hunter 与 Orchestrator 失败/停止传播回归测试。"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.orchestrator.context import ExecutionContext, TestResultException
from core.orchestrator.executor import OrchestratorExecutor
from core.orchestrator.nodes.base import BaseNode
from core.orchestrator.nodes.instrument_nodes import I2CTraverse
from core.vmin_hunter import EngineHooks, SleepVminConfig, SleepVminEngine
from ui.pages.vmin_hunter.vmin_hunter_ui import VminHunterUI


class _HookRecorder:
    def __init__(self):
        self.calls = []

    def set_voltage(self, channel, voltage):
        self.calls.append(("set_voltage", channel, voltage))

    def output_on(self, channel):
        self.calls.append(("output_on", channel))

    def status_sleep(self):
        self.calls.append(("status_sleep",))

    def status_wake(self):
        self.calls.append(("status_wake",))

    def as_hooks(self):
        return EngineHooks(
            set_voltage=self.set_voltage,
            output_on=self.output_on,
            status_sleep=self.status_sleep,
            status_wake=self.status_wake,
        )


def _vmin_engine(points=None):
    recorder = _HookRecorder()
    config = SleepVminConfig(
        wake_voltage=1.2,
        default_voltage=1.2,
        sleep_points=[1.0] if points is None else points,
        wake_settle_s=0.0,
        pre_drop_delay_s=0.0,
        sleep_hold_s=0.0,
        status_settle_s=0.0,
        alive_toggle_interval_s=0.0,
        alive_poll_interval_s=0.001,
        ensure_state_timeout_s=0.001,
    )
    engine = SleepVminEngine(config, recorder.as_hooks())
    finished = []
    engine.finished.connect(lambda ok, message: finished.append((ok, message)))
    return engine, recorder, finished


def test_vmin_rejects_invalid_scan_before_instrument():
    for points in ([], [None], [float("nan")]):
        engine, recorder, finished = _vmin_engine(points)
        engine.run()
        assert len(finished) == 1
        assert finished[0][0] is False
        assert recorder.calls == []


def test_vmin_initialization_failure_is_finished_false():
    engine, _recorder, finished = _vmin_engine()
    engine._ensure_wake_state = lambda: False

    engine.run()

    assert len(finished) == 1
    assert finished[0][0] is False
    assert "Initialization failed" in finished[0][1]
    assert engine.result.stopped is False
    assert engine.result.rows == []


def test_vmin_stop_at_first_point_is_finished_false():
    engine, _recorder, finished = _vmin_engine([1.0, 0.9])
    engine._ensure_wake_state = lambda: True

    def _stop_first_point(_sleep_v):
        engine.stop()
        return False

    engine._run_one_sleep_point = _stop_first_point
    engine.run()

    assert len(finished) == 1
    assert finished[0] == (False, "Stopped by user.")
    assert engine.result.stopped is True
    assert len(engine.result.rows) == 1


def test_vmin_completed_scan_without_pass_is_success():
    engine, _recorder, finished = _vmin_engine()
    engine._ensure_wake_state = lambda: True
    engine._run_one_sleep_point = lambda _sleep_v: ("FAIL", "DUT abnormal")

    engine.run()

    assert finished == [(True, "")]
    assert engine.result.stopped is False
    assert engine.result.vmin is None
    assert len(engine.result.rows) == 1


class _BatchHarness:
    _on_phase_finished = VminHunterUI._on_phase_finished

    def __init__(self, stop_requested=False):
        self._sweep_context = {
            "phase_index": 0,
            "phases": [{}, {}],
            "stop_requested": stop_requested,
        }
        self._runner = object()
        self.started = []
        self.completed = []

    def _start_sweep_phase(self, phase_index):
        self.started.append(phase_index)

    def _on_engine_finished(self, ok, message):
        self.completed.append((ok, message))


def test_vmin_batch_does_not_continue_after_failure_or_stop():
    failure = _BatchHarness()
    failure._on_phase_finished(False, "init failed")
    assert failure.started == []
    assert failure.completed == [(False, "init failed")]

    stopped = _BatchHarness(stop_requested=True)
    stopped._on_phase_finished(True, "")
    assert stopped.started == []
    assert stopped.completed == [(False, "Stopped by user.")]


_USE_REG_VALUE = object()


class _RecordingI2C:
    def __init__(self, value=_USE_REG_VALUE):
        self.value = value
        self.read_regs = []

    def read(self, _dev, reg, _width):
        self.read_regs.append(reg)
        return reg + 1 if self.value is _USE_REG_VALUE else self.value


class _FailChild(BaseNode):
    node_type = "GuardFailChild"
    display_name = "Guard Fail Child"

    def execute(self, _context):
        raise TestResultException(False, "child failed")


class _StopChild(BaseNode):
    node_type = "GuardStopChild"
    display_name = "Guard Stop Child"

    def execute(self, context):
        context.request_stop()


class _MarkerNode(BaseNode):
    node_type = "GuardMarker"
    display_name = "Guard Marker"

    def __init__(self):
        super().__init__()
        self.ran = False

    def execute(self, _context):
        self.ran = True


def _traverse(child=None, **overrides):
    params = {
        "device_addr": "0x17",
        "reg_start": "0x00",
        "reg_end": "0x02",
        "width": 10,
        "auto_record": False,
    }
    params.update(overrides)
    node = I2CTraverse(**params)
    if child is not None:
        node.children = [child]
    return node


def _run_orchestrator(traverse, i2c):
    marker = _MarkerNode()
    context = ExecutionContext(instruments={"i2c": i2c})
    executor = OrchestratorExecutor()
    executor.set_sequence([traverse, marker])
    executor.set_context(context)
    finished = []
    executor.finished.connect(lambda ok, message: finished.append((ok, message)))
    executor.run()
    return context, marker, finished


def test_i2c_traverse_child_failure_reaches_top_and_stops_sequence():
    i2c = _RecordingI2C()
    context, marker, finished = _run_orchestrator(_traverse(_FailChild()), i2c)

    assert len(finished) == 1
    assert finished[0] == (False, "测试失败: child failed")
    assert i2c.read_regs == [0]
    assert marker.ran is False
    assert context.should_stop is False


def test_i2c_traverse_user_stop_reaches_top_and_stops_sequence():
    i2c = _RecordingI2C()
    context, marker, finished = _run_orchestrator(_traverse(_StopChild()), i2c)

    assert len(finished) == 1
    assert finished[0][0] is False
    assert "stop" in finished[0][1].lower()
    assert context.should_stop is True
    assert i2c.read_regs == [0]
    assert marker.ran is False


def test_i2c_traverse_rejects_bad_range_and_handles_empty_read():
    i2c = _RecordingI2C()
    _context, marker, finished = _run_orchestrator(
        _traverse(reg_start="0x02", reg_end="0x01"), i2c
    )
    assert len(finished) == 1
    assert finished[0][0] is False
    assert "start reg" in finished[0][1]
    assert i2c.read_regs == []
    assert marker.ran is False

    empty_i2c = _RecordingI2C(value=None)
    empty_context = ExecutionContext(instruments={"i2c": empty_i2c})
    traverse = _traverse(reg_end="0x00", auto_record=True)
    traverse.execute(empty_context)
    assert empty_context.variables["i2c_traverse"] == {0: None}
    assert empty_context.records == []


class _PauseButton:
    def setText(self, _text):
        pass


class _Canvas:
    pause_btn = _PauseButton()


class _FinishedSignal:
    def __init__(self):
        self.events = []

    def emit(self, ok, message):
        self.events.append((ok, message))


class _ExecutionFinishedHarness:
    from ui.pages.orchestrator.orchestrator_ui import OrchestratorUI

    _on_execution_finished = OrchestratorUI._on_execution_finished

    def __init__(self):
        self._context = ExecutionContext()
        self.canvas = _Canvas()
        self.sequence_execution_finished = _FinishedSignal()
        self.running_states = []

    def _set_running_state(self, running):
        self.running_states.append(running)


def test_orchestrator_top_ui_state_matches_failure_payload():
    harness = _ExecutionFinishedHarness()
    harness._on_execution_finished(False, "测试失败: child failed")

    assert harness.running_states == [False]
    assert harness._context.run_status == "failed"
    assert harness._context.run_finished_at is not None
    assert len(harness.sequence_execution_finished.events) == 1
    ok, message = harness.sequence_execution_finished.events[0]
    assert ok is False
    assert message.startswith("测试失败: child failed")
