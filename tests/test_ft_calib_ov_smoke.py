# -*- coding: utf-8 -*-
"""FT Calibration Check - Output Voltage Check 冒烟与 DEBUG_MOCK 端到端。

Worker 同步 run() 注入 FakeI2C / 假仪器验证流程语义（判定/恢复/停止），
QThread 异步路径验证线程收尾；容器 offscreen 构建验证分发与中继信号。
"""

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QThread  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.pmu_test.ft_calib_ov.ft_calib_ov_worker import FtCalibOvWorker  # noqa: E402
from ui.pages.pmu_test.ft_calib_ov_chip_dialog import (  # noqa: E402
    ChipManagerDialog,
    RailEditDialog,
    default_rail,
)

_app = QApplication.instance() or QApplication([])


class _FakeTime:
    @staticmethod
    def sleep(_seconds):
        pass

    @staticmethod
    def time():
        return 0.0


class _FakeI2C:
    """寄存器映像 + 写入历史；efuse/vbit 原值预置。"""

    def __init__(self, regs=None, read_error=None):
        self.regs = dict(regs or {})
        self.writes = []
        self._read_error = read_error

    def read(self, dev, reg, width):
        if self._read_error is not None:
            raise self._read_error
        return self.regs.get((dev, reg), 0)

    def write(self, dev, reg, data, width):
        self.writes.append((dev, reg, data, width))
        self.regs[(dev, reg)] = data


class _FakeDmm:
    def __init__(self, averages):
        self._averages = list(averages)
        self.configured = []
        self.nplc = []

    def configure_voltage_dc(self, range_value=None, resolution=None):
        self.configured.append(range_value)

    def set_nplc(self, function, nplc):
        self.nplc.append((function, nplc))

    def measure_average(self, function, sample_count, range_value=None,
                        resolution=None):
        avg = self._averages.pop(0)
        return {"values": [avg], "average": avg, "min": avg, "max": avg,
                "stddev": 0.0, "ptp": 0.0, "count": sample_count}


class _FakeN6705C:
    def __init__(self, readings):
        self._readings = list(readings)
        self.calls = []

    def set_mode(self, ch, mode):
        self.calls.append(("set_mode", ch, mode))

    def channel_on(self, ch):
        self.calls.append(("channel_on", ch))

    def measure_voltage(self, ch):
        return self._readings.pop(0)


def _chip():
    return {
        "name": "FAKECHIP",
        "i2c": {"device_addr": "0x27", "width_flag": 10, "speed_khz": 100},
        "efuse": {"link": "i2c"},
        "rails": [
            {
                "name": "R1", "type": "DCDC", "enabled": True,
                "vbit": {"reg_addr": "0x35", "msb": 7, "lsb": 0, "width_flag": None},
                "efuse_field": {"reg_addr": "0x1", "msb": 7, "lsb": 0, "signed": False},
                "mode": "offset", "base_code": "0x80", "offset_lsb": 0,
                "step_mv": 6.25, "base_voltage_mv": 900.0,
                "target": {"source": "config", "voltage_mv": 1100.0},
                "tolerance_mv": 20.0, "settle_ms": 0,
            },
            {
                "name": "R2", "type": "LDO", "enabled": True,
                "vbit": {"reg_addr": "0x36", "msb": 7, "lsb": 0, "width_flag": None},
                "efuse_field": {"reg_addr": "0x2", "msb": 7, "lsb": 0, "signed": False},
                "mode": "absolute", "base_code": "0x0", "offset_lsb": 0,
                "step_mv": 6.25, "base_voltage_mv": 900.0,
                "target": {"source": "derived"},
                "tolerance_mv": 20.0, "settle_ms": 0,
            },
        ],
    }


def _regs():
    # efuse: R1=3, R2=0x55；vbit 原值高字节保留验证 RMW
    return {(0x27, 0x1): 0x03, (0x27, 0x2): 0x55,
            (0x27, 0x35): 0xAB00, (0x27, 0x36): 0xCD00}


def _options(**overrides):
    options = {
        "instrument": "dmm",
        "selected_rails": ["R1", "R2"],
        "vmeter_channel": 2,
        "dmm_samples": 5,
        "dmm_nplc": 1,
        "dmm_range": None,
        "restore_registers": True,
        "stop_on_fail": False,
    }
    options.update(overrides)
    return options


def _run_worker(chip, options, i2c, dmm=None, n6705c=None, debug=False):
    worker = FtCalibOvWorker(
        chip, options, n6705c=n6705c, dmm=dmm, debug_flag=debug,
        i2c_factory=lambda: i2c, mock_i2c_factory=lambda: i2c,
        time_module=_FakeTime,
    )
    logs, results, finished = [], [], []
    worker.log_message.connect(logs.append)
    worker.rail_result.connect(results.append)
    worker.test_finished.connect(lambda ok, reason: finished.append((ok, reason)))
    worker.run()
    return worker, logs, results, finished


def test_worker_dmm_end_to_end_pass_and_restore():
    i2c = _FakeI2C(_regs())
    dmm = _FakeDmm([1.100, 1.43125])
    _, logs, results, finished = _run_worker(_chip(), _options(), i2c, dmm=dmm)
    assert finished == [(True, "Test completed")]
    assert len(results) == 2
    assert results[0]["code"] == 0x83
    assert results[1]["code"] == 0x55
    assert results[0]["passed"] and results[1]["passed"]
    assert results[1]["target_mv"] == 900.0 + 0x55 * 6.25
    # RMW 保留高字节
    assert (0x27, 0x35, 0xAB83, 10) in i2c.writes
    assert (0x27, 0x36, 0xCD55, 10) in i2c.writes
    # finally 恢复原值
    assert i2c.regs[(0x27, 0x35)] == 0xAB00
    assert i2c.regs[(0x27, 0x36)] == 0xCD00
    assert any("[MEAS]" in line for line in logs)


def test_worker_vmeter_path():
    i2c = _FakeI2C(_regs())
    n6705c = _FakeN6705C([1.100] * 3 + [1.43125] * 3)
    _, _, results, finished = _run_worker(
        _chip(), _options(instrument="vmeter"), i2c, n6705c=n6705c)
    assert finished == [(True, "Test completed")]
    assert len(results) == 2
    assert ("set_mode", 2, "VMETer") in n6705c.calls
    assert ("channel_on", 2) in n6705c.calls


def test_worker_stop_after_first_rail_restores():
    i2c = _FakeI2C(_regs())
    dmm = _FakeDmm([1.100, 1.43125])
    worker = FtCalibOvWorker(
        _chip(), _options(), dmm=dmm,
        i2c_factory=lambda: i2c, mock_i2c_factory=lambda: i2c,
        time_module=_FakeTime,
    )
    results, finished = [], []
    worker.rail_result.connect(lambda rec: (results.append(rec), worker.request_stop()))
    worker.test_finished.connect(lambda ok, reason: finished.append((ok, reason)))
    worker.run()
    assert len(results) == 1
    assert finished == [(False, "Stopped by user")]
    assert i2c.regs[(0x27, 0x35)] == 0xAB00
    assert i2c.regs[(0x27, 0x36)] == 0xCD00


def test_worker_stop_on_fail():
    i2c = _FakeI2C(_regs())
    dmm = _FakeDmm([1.500, 1.43125])
    _, _, results, finished = _run_worker(
        _chip(), _options(stop_on_fail=True), i2c, dmm=dmm)
    assert len(results) == 1
    assert not results[0]["passed"]
    assert finished == [(True, "Stopped on FAIL")]
    assert i2c.regs[(0x27, 0x35)] == 0xAB00


def test_worker_no_restore_option():
    i2c = _FakeI2C(_regs())
    dmm = _FakeDmm([1.100, 1.43125])
    _run_worker(_chip(), _options(restore_registers=False), i2c, dmm=dmm)
    assert i2c.regs[(0x27, 0x35)] == 0xAB83
    assert i2c.regs[(0x27, 0x36)] == 0xCD55


def test_worker_script_link_mock_degrades():
    chip = _chip()
    chip["efuse"] = {"link": "script", "script_filename": "efuse_1307ph.py",
                     "chip_name": "fake"}
    i2c = _FakeI2C(_regs())
    dmm = _FakeDmm([1.100, 1.43125])
    _, logs, results, finished = _run_worker(chip, _options(), i2c, dmm=dmm, debug=True)
    assert finished == [(True, "Test completed")]
    assert len(results) == 2
    assert any("[MOCK]" in line for line in logs)


def test_worker_efuse_read_failure_aborts():
    i2c = _FakeI2C(_regs(), read_error=RuntimeError("i2c bus down"))
    dmm = _FakeDmm([1.100])
    _, _, results, finished = _run_worker(_chip(), _options(), i2c, dmm=dmm)
    assert results == []
    assert finished[0][0] is False
    assert "Test failed" in finished[0][1]


def test_worker_clamp_warns():
    chip = _chip()
    chip["rails"][0]["offset_lsb"] = 1000  # 0x80+3+1000 超出 8bit
    i2c = _FakeI2C(_regs())
    dmm = _FakeDmm([1.100, 1.43125])
    _, logs, results, _ = _run_worker(chip, _options(), i2c, dmm=dmm)
    assert results[0]["code"] == 0xFF
    assert results[0]["clamped"]
    assert any("clamped" in line for line in logs)


def test_worker_async_qthread_finishes():
    i2c = _FakeI2C(_regs())
    dmm = _FakeDmm([1.100, 1.43125])
    worker = FtCalibOvWorker(
        _chip(), _options(), dmm=dmm,
        i2c_factory=lambda: i2c, mock_i2c_factory=lambda: i2c,
        time_module=_FakeTime,
    )
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    finished = []
    worker.test_finished.connect(lambda ok, reason: finished.append((ok, reason)))
    worker.test_finished.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    deadline = time.monotonic() + 5.0
    while not finished and time.monotonic() < deadline:
        _app.processEvents()
        time.sleep(0.01)
    assert finished == [(True, "Test completed")]
    deadline = time.monotonic() + 2.0
    while thread.isRunning() and time.monotonic() < deadline:
        _app.processEvents()
        time.sleep(0.01)
    assert not thread.isRunning()


# ----------------------------------------------------------------------
# UI 冒烟（offscreen）
# ----------------------------------------------------------------------

def _build_container():
    from ui.pages.pmu_test.ft_calib_check_ui import FTCalibCheckUI
    return FTCalibCheckUI()


def test_container_dispatch_and_relay():
    ui = _build_container()
    try:
        assert ui.tab_widget.count() == 2
        ui.tab_widget.setCurrentIndex(1)
        ov = ui.output_voltage_check_ui
        assert ui._active_subpage() is ov
        cfg = ui.get_test_config()
        for key in ("chip_name", "selected_rails", "measure_instrument",
                    "vmeter_channel", "dmm_samples", "restore_registers"):
            assert key in cfg
        assert ui.start_test_btn is ov.start_test_btn
        assert ui.is_test_running is False

        start_events, stop_events = [], []
        ui.start_relay.connect(lambda: start_events.append(1))
        ui.stop_relay.connect(lambda: stop_events.append(1))
        ov.start_test_btn.click()  # 无芯片配置 → 校验拒绝，但中继仍发射
        ov.stop_test_btn.click()
        assert len(start_events) == 1
        assert len(stop_events) == 1
        assert not ov.is_test_running

        ok, _msg = ov.apply_config_to_controls({
            "measure_instrument": "vmeter",
            "restore_registers": False,
            "dmm_samples": 20,
        })
        assert ok
        assert ov.measure_instr_combo.currentData() == "vmeter"
        assert not ov.restore_registers_check.isChecked()
        assert ov.dmm_samples_spin.value() == 20
        assert ov.ai_capabilities()
        assert ui.ai_get_config() is not None
    finally:
        ui.cleanup_threads()
        ui.cleanup_threads()
        ui.deleteLater()
        _app.processEvents()


def test_chip_manager_and_rail_dialogs():
    ui = _build_container()
    try:
        dlg = ChipManagerDialog([_chip()], parent=ui)
        assert dlg.chip_list.count() == 1
        assert dlg.rail_table.rowCount() == 2
        dlg.reject()

        rail_dlg = RailEditDialog(default_rail(), parent=ui)
        rail_dlg._on_ok()
        assert rail_dlg.result() == RailEditDialog.Accepted
        assert rail_dlg.result_rail()["name"] == "NEW_RAIL"

        bad_dlg = RailEditDialog(default_rail(), parent=ui)
        bad_dlg.name_edit.setText("")
        bad_dlg._on_ok()
        assert bad_dlg.result() != RailEditDialog.Accepted
        assert bad_dlg.error_label.text()
        bad_dlg.reject()
    finally:
        ui.cleanup_threads()
        ui.deleteLater()
        _app.processEvents()
