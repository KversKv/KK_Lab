# -*- coding: utf-8 -*-

import csv
import math
import os
import sys
import tempfile
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.consumption_test.workers.auto_test_worker import AutoTestWorker
from core.consumption_test.workers.common import require_channel_results
from core.consumption_test.workers.force_worker import ConsumptionTestForceHighWorker
from core.n6705c.consumption_worker import ConsumptionTestWorker
from instruments.power.keysight.n6705c_datalog_process import (
    calc_power_for_ch,
    import_csv_file,
    parse_csv_text,
)
from ui.pages.consumption_test.high_low_temp_test_ui import _HighLowTempTestWorker
from ui.pages.n6705c_power_analyzer.datalog.view_import_export import (
    ImportExportViewMixin,
    QFileDialog,
)


class _ExportHarness(ImportExportViewMixin):
    def __init__(self, data):
        self.datalog_data = data
        self.ch_name_renames = {}
        self.custom_labels = []
        self._file_time_offsets = {}
        self._b_time_offset = 0.0
        self._imported_tab_configs = []
        self._raw_dlog_list = []

    def _get_visible_keys(self):
        return list(self.datalog_data)

    def _get_total_time_offset(self, _label):
        return 0.0

    def _get_file_prefix(self, _label):
        return ""

    def _is_b_label(self, label):
        return label.startswith("B ")


def _make_auto_worker(instrument, **overrides):
    kwargs = {
        "com_port": "COM1",
        "firmware_paths": ["fw.bin"],
        "download_mode": None,
        "poweron_device_label": "A",
        "poweron_inst": instrument,
        "poweron_hw_ch": 1,
        "poweron_polarity": 1,
        "reset_device_label": "A",
        "reset_inst": instrument,
        "reset_hw_ch": 2,
        "reset_polarity": 1,
        "vbat_device_label": "A",
        "vbat_inst": instrument,
        "vbat_hw_ch": 3,
        "force_map": {},
        "test_time": 1.0,
        "sample_period": 20e-6,
        "stabilization_delay_sec": 0.0,
        "download_pgm_rate": 115200,
    }
    kwargs.update(overrides)
    return AutoTestWorker(**kwargs)


class ConsumptionGuardTests(unittest.TestCase):
    def test_invalid_n6705c_params_do_not_touch_instrument(self):
        for test_time, sample_period in [
            ("bad", 20e-6),
            (math.nan, 20e-6),
            (1.0, 19e-6),
            (1.0, 2.0),
        ]:
            with self.subTest(test_time=test_time, sample_period=sample_period):
                instrument = mock.Mock()
                worker = ConsumptionTestWorker(
                    instrument, "A", [1], test_time, sample_period
                )
                finished = []
                worker.finished.connect(lambda *args: finished.append(args))
                worker.run()
                self.assertEqual(instrument.mock_calls, [])
                self.assertEqual(finished[0][0], False)

    def test_invalid_force_config_does_not_touch_instrument(self):
        instrument = mock.Mock()
        worker = ConsumptionTestForceHighWorker(
            "A",
            instrument,
            1,
            {"A": (instrument, [2])},
            1.0,
            20e-6,
            channel_force_configs={
                ("A", 2): {
                    "force_mode": "force",
                    "force_value": math.inf,
                    "boost_mode": "constant",
                    "boost_value": 0.0,
                }
            },
        )
        finished = []
        worker.finished.connect(lambda *args: finished.append(args))
        worker.run()
        self.assertEqual(instrument.mock_calls, [])
        self.assertEqual(finished, [(False, "Force voltage for ('A', 2) must be finite and positive.")])

    def test_invalid_auto_params_do_not_start_flow_or_touch_instrument(self):
        for overrides in [
            {"stabilization_delay_sec": math.nan},
            {"download_pgm_rate": 0},
            {"download_pgm_rate": 1.5},
            {"test_time": math.inf},
        ]:
            with self.subTest(overrides=overrides):
                instrument = mock.Mock()
                worker = _make_auto_worker(instrument, **overrides)
                worker._auto_test = mock.Mock()
                finished = []
                worker.finished.connect(lambda *args: finished.append(args))
                worker.run()
                worker._auto_test.assert_not_called()
                self.assertEqual(instrument.mock_calls, [])
                self.assertFalse(finished[0][0])

    def test_n6705c_stop_exception_and_empty_results_fail(self):
        stopped_instrument = mock.Mock()
        stopped = ConsumptionTestWorker(stopped_instrument, "A", [1], 1.0, 20e-6)
        stopped.stop()
        stopped_finished = []
        stopped.finished.connect(lambda *args: stopped_finished.append(args))
        stopped.run()
        stopped_instrument.fetch_current_by_datalog.assert_not_called()
        self.assertFalse(stopped_finished[0][0])

        for result, side_effect in [({}, None), (None, RuntimeError("boom"))]:
            with self.subTest(result=result, side_effect=side_effect):
                instrument = mock.Mock()
                instrument.fetch_current_by_datalog.return_value = result
                instrument.fetch_current_by_datalog.side_effect = side_effect
                worker = ConsumptionTestWorker(instrument, "A", [1], 1.0, 20e-6)
                finished = []
                worker.finished.connect(lambda *args: finished.append(args))
                worker.run()
                self.assertEqual(finished[0][0], False)

    def test_force_and_auto_incomplete_results_fail(self):
        force = ConsumptionTestForceHighWorker(
            "A", mock.Mock(), 1, {}, 1.0, 20e-6
        )
        force._run_flow = mock.Mock(return_value={})
        force_finished = []
        force.finished.connect(lambda *args: force_finished.append(args))
        force.run()
        self.assertFalse(force_finished[0][0])

        auto = _make_auto_worker(mock.Mock())
        auto._auto_test = mock.Mock(return_value=[])
        auto_finished = []
        auto.finished.connect(lambda *args: auto_finished.append(args))
        auto.run()
        self.assertFalse(auto_finished[0][0])

    def test_missing_channel_is_not_zero_or_emitted(self):
        with self.assertRaises(RuntimeError):
            require_channel_results({1: 0.0}, [1, 2], "A")

        instrument = mock.Mock()
        instrument.fetch_current_by_datalog.return_value = {1: 0.0}
        worker = ConsumptionTestWorker(instrument, "A", [1, 2], 1.0, 20e-6)
        finished = []
        channel_results = []
        worker.finished.connect(lambda *args: finished.append(args))
        worker.channel_result.connect(lambda *args: channel_results.append(args))
        worker.run()
        self.assertFalse(finished[0][0])
        self.assertEqual(channel_results, [])

    def test_high_low_first_point_stop_empty_and_exception_fail(self):
        config = {
            "temp_start": 25,
            "temp_end": 25,
            "temp_step": 1,
            "soak_time": 0,
            "test_time": 1,
            "sample_period": 20e-6,
            "channels": [1],
        }
        stopped = _HighLowTempTestWorker(config, mock_mode=True)
        stopped.stop()
        stopped_finished = []
        stopped.finished.connect(stopped_finished.append)
        stopped.run()
        self.assertFalse(stopped_finished[0]["success"])
        self.assertEqual(stopped_finished[0]["data"], [])

        empty = _HighLowTempTestWorker(config, mock_mode=True)
        empty._run_temp_consumption = mock.Mock(
            return_value={"data": [], "channels": [1]}
        )
        empty_finished = []
        empty.finished.connect(empty_finished.append)
        empty.run()
        self.assertFalse(empty_finished[0]["success"])

        failed = _HighLowTempTestWorker(config, mock_mode=True)
        failed._run_temp_consumption = mock.Mock(side_effect=RuntimeError("boom"))
        failed_finished = []
        failed.finished.connect(failed_finished.append)
        failed.run()
        self.assertFalse(failed_finished[0]["success"])
        self.assertIn("boom", failed_finished[0]["message"])

    def test_high_low_descending_range_remains_valid(self):
        worker = _HighLowTempTestWorker({}, mock_mode=True)
        self.assertEqual(worker._float_range(30, 20, 5), [30, 25, 20])


class DatalogGuardTests(unittest.TestCase):
    def test_csv_import_skips_missing_values_without_zero_fill(self):
        content = (
            "Time_CH1 I(s),CH1 I\n"
            "0,1\n"
            "1,\n"
            "2,invalid\n"
            "3,4\n"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "missing.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(content)
            result = import_csv_file(path)
        self.assertIsNotNone(result)
        data = result[0]["CH1 I"]
        self.assertEqual(data, {"time": [0.0, 3.0], "values": [1.0, 4.0]})

    def test_stream_csv_parser_preserves_sample_positions(self):
        data = parse_csv_text(
            "Sample interval: 0.5\n0,0.001\n1,\n2,0.003\n",
            [1],
            [],
            "",
            20e-6,
        )
        self.assertEqual(data["CH1 I"]["time"], [0.0, 1.0])
        self.assertEqual(data["CH1 I"]["values"], [1.0, 3.0])

    def test_empty_csv_import_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("Time_CH1 I(s),CH1 I\n0,\n")
            self.assertIsNone(import_csv_file(path))
        self.assertEqual(parse_csv_text("", [1], [], "", 20e-6), {})

    def test_combined_export_uses_paired_samples_and_blank_padding(self):
        harness = _ExportHarness({
            "CH1 I": {"time": [0, 1, 2], "values": [1]},
            "B CH1 I": {"time": [0, 1], "values": [2, 3]},
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "combined.csv")
            result = harness._write_combined_csv(path)
            with open(path, "r", encoding="utf-8", newline="") as f:
                rows = [row for row in csv.reader(f) if row]
        self.assertTrue(result["ok"])
        header = rows[2]
        first = rows[3]
        second = rows[4]
        self.assertEqual(first[header.index("Time_A-I1(s)")], "0.000000")
        self.assertEqual(first[header.index("A-I1")], "1.000000000")
        self.assertEqual(second[header.index("Time_A-I1(s)")], "")
        self.assertEqual(second[header.index("A-I1")], "")
        self.assertEqual(second[header.index("Time_B-I1(s)")], "1.000000")
        self.assertEqual(second[header.index("B-I1")], "3.000000000")

    def test_standard_ab_export_does_not_index_short_reference_time(self):
        harness = _ExportHarness({
            "CH1 I": {"time": [0], "values": [1]},
            "CH2 I": {"time": [0, 1], "values": [2, 3]},
            "B CH1 I": {"time": [0], "values": [4, 5]},
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "standard.csv")
            with mock.patch.object(
                QFileDialog, "getSaveFileName", return_value=(path, "CSV Files (*.csv)")
            ):
                harness._export_standard()
            with open(path, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
        header, first, second = rows
        self.assertEqual(len(second), len(header))
        self.assertEqual(second[header.index("Time_A-I1(s)")], "")
        self.assertEqual(second[header.index("A-I1")], "")
        self.assertEqual(second[header.index("Time_A-I2(s)")], "1.000000")
        self.assertEqual(second[header.index("A-I2")], "3.000000000")
        self.assertEqual(second[header.index("Time_B-I1(s)")], "")
        self.assertEqual(second[header.index("B-I1")], "")
        self.assertEqual(first[header.index("B-I1")], "4.000000000")

    def test_empty_export_is_rejected_without_creating_file(self):
        harness = _ExportHarness({"CH1 I": {"time": [0], "values": []}})
        with tempfile.TemporaryDirectory() as tmpdir:
            combined_path = os.path.join(tmpdir, "empty_combined.csv")
            result = harness._write_combined_csv(combined_path)
            self.assertFalse(result["ok"])
            self.assertFalse(os.path.exists(combined_path))

            standard_path = os.path.join(tmpdir, "empty_standard.csv")
            with mock.patch.object(
                QFileDialog, "getSaveFileName", return_value=(standard_path, "CSV Files (*.csv)")
            ):
                harness._export_standard()
            self.assertFalse(os.path.exists(standard_path))

    def test_power_channel_time_and_values_stay_equal(self):
        data = {
            "CH1 V": {"time": [0], "values": [2.0, 3.0]},
            "CH1 I": {"time": [0, 1], "values": [4.0, 5.0]},
        }
        calc_power_for_ch(data, 1, "")
        self.assertEqual(data["CH1 P"], {"time": [0], "values": [0.008]})

    def test_power_channel_pairs_samples_by_timestamp(self):
        data = {
            "CH1 V": {"time": [0, 1, 2], "values": [2.0, 3.0, 4.0]},
            "CH1 I": {"time": [1, 2], "values": [5.0, 6.0]},
        }
        calc_power_for_ch(data, 1, "")
        self.assertEqual(data["CH1 P"], {"time": [1, 2], "values": [0.015, 0.024]})


if __name__ == "__main__":
    unittest.main()
