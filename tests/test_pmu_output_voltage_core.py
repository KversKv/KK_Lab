# -*- coding: utf-8 -*-
import time

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QThread

from core.pmu_test.output_voltage.output_voltage_analysis import (
    build_result,
    compute_valid_range,
    precheck_first_points,
    validate_code_range,
)
from core.pmu_test.output_voltage.output_voltage_worker import (
    OutputVoltageTestThread,
    OutputVoltageWorker,
)


class _Instrument:
    def __init__(self):
        self.calls = []
        self.measure_count = 0

    def set_mode(self, *args):
        self.calls.append(("set_mode", args))

    def channel_on(self, *args):
        self.calls.append(("channel_on", args))

    def channel_off(self, *args):
        self.calls.append(("channel_off", args))

    def measure_voltage(self, *args):
        self.calls.append(("measure_voltage", args))
        self.measure_count += 1
        return 1.0


class _Time:
    @staticmethod
    def sleep(_seconds):
        pass

    @staticmethod
    def time():
        return 0.0


def _config():
    return {
        "device_addr": "50",
        "reg_addr": "01",
        "msb": 0,
        "lsb": 0,
        "width_flag": 1,
        "min_code": "0",
        "max_code": "0",
        "vmeter_channel": "CH 1",
        "vmeter_mode": "VMETer",
        "close_channel_after": False,
    }


def _i2c_factory(instances, read_error=None):
    class FakeI2C:
        def __init__(self):
            self.writes = []
            instances.append(self)

        def read(self, *args):
            if read_error is not None:
                raise read_error
            return 0xA5

        def write(self, *args):
            self.writes.append(args)

    return FakeI2C


def _runner(instrument, config, instances, read_error=None):
    return OutputVoltageTestThread(
        instrument,
        config,
        i2c_factory=_i2c_factory(instances, read_error),
        time_module=_Time,
    )


def test_valid_range_and_result_use_core_analysis():
    voltages = [1.0] * 5 + [1.005 + 0.005 * i for i in range(50)] + [1.3] * 5
    assert compute_valid_range(voltages) == (4, 55)

    result = build_result([1.0, 1.01, 1.02], [0, 1, 2], 0.5, 0, 100)
    assert result["min_voltage"] == 1.0
    assert result["max_voltage"] == 1.02
    assert result["step_voltage"] == pytest.approx(10.0)
    assert result["linearity"] == 0.0


def test_precheck_and_code_range_keep_legacy_messages():
    assert precheck_first_points([1.0, 1.01, 1.02]) == (True, "")
    ok, reason = precheck_first_points([1.0, 1.0, 1.0])
    assert not ok
    assert reason.startswith("电压无变化（span=0.00mV")
    with pytest.raises(ValueError, match="Invalid code range"):
        validate_code_range(0, 0, 0, 2)


def test_core_confirm_response_aborts_precheck_and_restores_register():
    instances = []
    config = _config()
    config["msb"] = 2
    config["max_code"] = "4"
    runner = _runner(_Instrument(), config, instances)
    finished = []
    confirmations = []
    runner.test_finished.connect(lambda *args: finished.append(args))

    def abort(title, message):
        confirmations.append((title, message))
        runner.respond_confirm(False)

    runner.confirm_request.connect(abort)
    runner.run()

    assert finished == [(False, "测试被中止")]
    assert len(confirmations) == 1
    assert confirmations[0][0] == "前置校验失败"
    assert "前 5 个测量点校验失败" in confirmations[0][1]
    assert "是否继续扫描？" in confirmations[0][1]
    assert instances[0].writes[-1][2] == 0xA5


def test_core_stop_and_exception_have_failed_finish_reasons():
    instances = []
    runner = _runner(_Instrument(), _config(), instances)
    runner.request_stop()
    stopped = []
    runner.test_finished.connect(lambda *args: stopped.append(args))
    runner.run()
    assert stopped == [(False, "测试被中止")]

    failed_runner = _runner(
        _Instrument(), _config(), [], read_error=RuntimeError("read failed"),
    )
    failed = []
    failed_runner.test_finished.connect(lambda *args: failed.append(args))
    failed_runner.run()
    assert len(failed) == 1
    assert failed[0][0] is False
    assert "测试失败：read failed" in failed[0][1]


@pytest.mark.qt
def test_legacy_start_uses_qobject_worker_and_cleans_up_thread():
    app = QCoreApplication.instance() or QCoreApplication([])
    instances = []
    runner = _runner(_Instrument(), _config(), instances)
    finished = []
    runner.test_finished.connect(lambda *args: finished.append(args))

    assert isinstance(runner, QObject)
    assert not isinstance(runner, QThread)
    assert isinstance(runner._worker, OutputVoltageWorker)

    runner.start()
    deadline = time.monotonic() + 2.0
    while (not finished or runner._thread is not None) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.001)

    assert finished == [(True, "测试完成")]
    assert runner._thread is None
    assert instances[0].writes[-1][2] == 0xA5
