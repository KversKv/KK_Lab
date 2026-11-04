# -*- coding: utf-8 -*-
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

import pytest

from ui.pages.pmu_test import pmu_output_voltage as pmu
from ui.pages.charger_test import config_traverse_test as config_traverse
from ui.pages.charger_test import regulation_voltage_ui as regulation
from ui.pages.charger_test import iterm_test as iterm


class _Instrument:
    def __init__(self):
        self.calls = []
        self.measure_count = 0
        self.stop_worker = None
        self.stop_after = None

    def set_mode(self, *args):
        self.calls.append(("set_mode", args))

    def channel_on(self, *args):
        self.calls.append(("channel_on", args))

    def channel_off(self, *args):
        self.calls.append(("channel_off", args))

    def measure_voltage(self, *args):
        self.calls.append(("measure_voltage", args))
        self.measure_count += 1
        if self.stop_worker is not None and self.measure_count == self.stop_after:
            self.stop_worker.request_stop()
        return 1.0

    def measure_current(self, *args):
        self.calls.append(("measure_current", args))
        return 0.01


def _install_i2c(monkeypatch, module, default=0, read_error=None):
    instances = []

    class FakeI2C:
        def __init__(self):
            self.writes = []
            instances.append(self)

        def read(self, *args):
            if read_error is not None:
                raise read_error
            return default

        def write(self, *args):
            self.writes.append(args)

    monkeypatch.setattr(module, "I2CInterface", FakeI2C)
    return instances


def _pmu_config():
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
        "close_channel_after": True,
    }


def _traverse_config():
    return {
        "device_addr": 0x50,
        "reg_addr": 1,
        "msb": 0,
        "lsb": 0,
        "min_code": 0,
        "max_code": 0,
        "iic_width": 1,
        "test_mode": "Voltage",
        "vmeter_channel": "CH 1",
    }


def _regulation_config():
    return {
        "device_addr": 0x50,
        "reg_addr": 1,
        "msb": 0,
        "lsb": 0,
        "min_code": 0,
        "max_code": 0,
        "iic_width": 1,
        "vmeter_channel": "CH 1",
    }


def _iterm_config(test_item="Traverse Iterm Test"):
    return {
        "test_item": test_item,
        "device_addr": 0x50,
        "iterm_reg": 1,
        "iic_width": 1,
        "vbat_channel": 1,
        "measure_channel": 2,
        "average_time_ms": 100,
        "voreg": 4.2,
        "msb": 0,
        "lsb": 0,
        "min_code": 0,
        "max_code": 0,
    }


@pytest.mark.parametrize("validator", [
    pmu._validate_code_range,
    config_traverse._validate_code_range,
    regulation._validate_code_range,
    iterm._validate_code_range,
])
@pytest.mark.parametrize("values", [
    (-1, 0, 0, 0),
    (0, 1, 0, 0),
    (0, 0, -1, 0),
    (0, 0, 1, 0),
    (0, 0, 0, 2),
])
def test_code_range_guard_rejects_invalid_values(validator, values):
    with pytest.raises(ValueError):
        validator(*values)


@pytest.mark.parametrize("validator", [
    pmu._validate_code_range,
    config_traverse._validate_code_range,
    regulation._validate_code_range,
    iterm._validate_code_range,
])
def test_code_range_guard_accepts_legal_single_point(validator):
    validator(3, 2, 1, 1)


@pytest.mark.parametrize("module,worker_cls,config_factory", [
    (pmu, pmu.OutputVoltageTestThread, _pmu_config),
    (config_traverse, config_traverse._ConfigTraverseWorker, _traverse_config),
    (regulation, regulation._RegulationVoltageWorker, _regulation_config),
    (iterm, iterm._ItermTestWorker, _iterm_config),
])
def test_invalid_worker_config_has_no_instrument_or_i2c_calls(
        monkeypatch, module, worker_cls, config_factory):
    instances = _install_i2c(monkeypatch, module)
    instrument = _Instrument()
    config = config_factory()
    config["max_code"] = "2" if worker_cls is pmu.OutputVoltageTestThread else 2
    worker = worker_cls(instrument, config)
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert len(finished) == 1
    assert finished[0][0] is False
    assert instances == []
    assert instrument.calls == []


def test_pmu_single_point_success_and_register_restore(monkeypatch):
    instances = _install_i2c(monkeypatch, pmu, default=0xA5)
    monkeypatch.setattr(pmu.time, "sleep", lambda *_: None)
    config = _pmu_config()
    config["close_channel_after"] = False
    worker = pmu.OutputVoltageTestThread(_Instrument(), config)
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert finished == [(True, "测试完成")]
    assert instances[0].writes[-1][2] == 0xA5


def test_pmu_stop_before_first_sample_is_not_success(monkeypatch):
    instances = _install_i2c(monkeypatch, pmu, default=0xA5)
    monkeypatch.setattr(pmu.time, "sleep", lambda *_: None)
    instrument = _Instrument()
    config = _pmu_config()
    config["close_channel_after"] = False
    worker = pmu.OutputVoltageTestThread(instrument, config)
    instrument.stop_worker = worker
    instrument.stop_after = 4
    finished = []
    points = []
    worker.test_finished.connect(lambda *args: finished.append(args))
    worker.chart_point.connect(lambda *args: points.append(args))

    worker.run()

    assert finished == [(False, "测试被中止")]
    assert points == []
    assert instances[0].writes[-1][2] == 0xA5


def test_pmu_exception_has_failed_finish_reason(monkeypatch):
    _install_i2c(monkeypatch, pmu, read_error=RuntimeError("read failed"))
    worker = pmu.OutputVoltageTestThread(_Instrument(), _pmu_config())
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert len(finished) == 1
    assert finished[0][0] is False
    assert "测试失败" in finished[0][1]


@pytest.mark.parametrize("module,worker_cls,config_factory", [
    (config_traverse, config_traverse._ConfigTraverseWorker, _traverse_config),
    (regulation, regulation._RegulationVoltageWorker, _regulation_config),
])
def test_charger_single_point_success(monkeypatch, module, worker_cls, config_factory):
    instances = _install_i2c(monkeypatch, module, default=0xA5)
    monkeypatch.setattr(module.time, "sleep", lambda *_: None)
    worker = worker_cls(_Instrument(), config_factory())
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert finished == [(True,)]
    assert instances[0].writes[-1][2] == 0xA5


@pytest.mark.parametrize("module,worker_cls,config_factory", [
    (config_traverse, config_traverse._ConfigTraverseWorker, _traverse_config),
    (regulation, regulation._RegulationVoltageWorker, _regulation_config),
])
def test_charger_stop_before_first_sample_is_not_success(
        monkeypatch, module, worker_cls, config_factory):
    _install_i2c(monkeypatch, module)
    monkeypatch.setattr(module.time, "sleep", lambda *_: None)
    instrument = _Instrument()
    worker = worker_cls(instrument, config_factory())
    instrument.stop_worker = worker
    instrument.stop_after = 4
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert finished == [(False,)]


def test_iterm_single_none_is_not_success(monkeypatch):
    worker = iterm._ItermTestWorker(_Instrument(), _iterm_config("Single Iterm Test"))
    monkeypatch.setattr(worker, "single_iterm_test", lambda *args: None)
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert finished == [(False,)]


def test_iterm_traverse_without_valid_points_is_not_success(monkeypatch):
    instances = _install_i2c(monkeypatch, iterm, default=0xA5)
    monkeypatch.setattr(iterm.time, "sleep", lambda *_: None)
    worker = iterm._ItermTestWorker(_Instrument(), _iterm_config())
    monkeypatch.setattr(worker, "single_iterm_test", lambda *args: None)
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert finished == [(False,)]
    assert instances[0].writes[-1][2] == 0xA5


def test_iterm_traverse_stop_is_not_success(monkeypatch):
    _install_i2c(monkeypatch, iterm)
    monkeypatch.setattr(iterm.time, "sleep", lambda *_: None)
    worker = iterm._ItermTestWorker(_Instrument(), _iterm_config())
    monkeypatch.setattr(worker, "single_iterm_test", lambda *args: 0.01)
    worker.request_stop()
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert finished == [(False,)]


def test_iterm_traverse_valid_point_is_success(monkeypatch):
    _install_i2c(monkeypatch, iterm)
    monkeypatch.setattr(iterm.time, "sleep", lambda *_: None)
    worker = iterm._ItermTestWorker(_Instrument(), _iterm_config())
    monkeypatch.setattr(worker, "single_iterm_test", lambda *args: 0.01)
    finished = []
    worker.test_finished.connect(lambda *args: finished.append(args))

    worker.run()

    assert finished == [(True,)]


class _Emitter:
    def __init__(self):
        self.args = None

    def emit(self, *args):
        self.args = args


class _FinishHarness:
    def __init__(self, stopped=False):
        self.test_thread = None
        self.test_worker = None
        self._stop_requested = stopped
        self.sequence_execution_finished = _Emitter()
        self.logs = []

    def set_test_running(self, _running):
        pass

    def append_log(self, message):
        self.logs.append(message)

    def _append_to_log(self, message):
        self.logs.append(message)


def test_pmu_finish_slot_distinguishes_abort_and_failure():
    aborted = _FinishHarness()
    pmu.PMUOutputVoltageUI._on_test_finished(aborted, False, "测试被中止")
    assert aborted.sequence_execution_finished.args == (False, "测试被中止")

    failed = _FinishHarness()
    pmu.PMUOutputVoltageUI._on_test_finished(failed, False, "测试失败：read failed")
    assert failed.sequence_execution_finished.args == (False, "测试失败：read failed")


@pytest.mark.parametrize("ui_cls", [
    config_traverse.ConfigTraverseTestUI,
    regulation.RegulationVoltageTestUI,
    iterm.ItermTestUI,
])
def test_charger_finish_slot_distinguishes_stop_from_error(ui_cls):
    harness = _FinishHarness(stopped=True)

    ui_cls._on_test_finished(harness, False)

    assert harness.sequence_execution_finished.args == (False, "测试被中止")


class _Text:
    def setText(self, _value):
        pass


class _Axis:
    def setRange(self, *_args):
        pass


class _Series:
    def __init__(self):
        self.clear_count = 0
        self.points = []

    def clear(self):
        self.clear_count += 1
        self.points = []

    def replace(self, points):
        self.points = list(points)

    def append(self, *args):
        self.points.append(args)


class _ChartHarness(_FinishHarness):
    def __init__(self):
        super().__init__()
        self._export_data = []
        self._total_count = 0
        self._pass_count = 0
        self._fail_count = 0
        self.current_series = _Series()
        self.term_marker_series = _Series()
        self.axis_x = _Axis()
        self.axis_y = _Axis()
        self.iterm_card = {"value": _Text()}
        self.voreg_card = {"value": _Text()}


def test_iterm_chart_rows_do_not_duplicate_export_data(monkeypatch):
    monkeypatch.setattr(iterm, "HAS_QTCHARTS", True)
    harness = _ChartHarness()

    iterm.ItermTestUI._on_chart_series_data(
        harness, [0.0, 1.0], [0.1, 0.2], -1.0, 0.0, 0.0,
    )
    iterm.ItermTestUI._on_result_row(harness, {
        "code": "---", "measured_ma": "100.0", "result": "DONE",
    })

    assert harness._export_data == [(0.0, 0.1), (1.0, 0.2)]
    assert harness._total_count == 1


def test_iterm_empty_curve_does_not_clear_or_export(monkeypatch):
    monkeypatch.setattr(iterm, "HAS_QTCHARTS", True)
    harness = _ChartHarness()

    iterm.ItermTestUI._on_chart_series_data(harness, [], [], -1.0, 0.0, 0.0)

    assert harness.current_series.clear_count == 0
    assert harness._export_data == []


def test_iterm_export_accepts_legacy_dicts_and_tuples(monkeypatch, tmp_path):
    harness = _FinishHarness()
    harness._export_data = [
        {"code": "0x02", "measured_ma": "12.5"},
        (3, 15.0),
        {"code": "---", "measured_ma": "100.0"},
    ]
    output = tmp_path / "iterm.csv"
    monkeypatch.setattr(
        iterm.QFileDialog, "getSaveFileName", lambda *args: (str(output), "CSV Files (*.csv)"),
    )

    iterm.ItermTestUI._on_export_csv(harness)

    assert output.read_text(encoding="utf-8") == "X,Y\n2,12.5\n3,15\n"
