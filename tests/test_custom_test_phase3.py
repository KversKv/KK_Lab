import csv
import json
import os
import sys
import tempfile
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    __import__("PySide6.QtCore")
except ModuleNotFoundError:
    _PYSIDE_AVAILABLE = False
else:
    _PYSIDE_AVAILABLE = True

from core.custom_test.result_store import ResultStore, build_default_result_path

if _PYSIDE_AVAILABLE:
    from core.custom_test.context import ExecutionContext
    from core.custom_test.executor import CustomTestExecutor
    from ui.pages.custom_test.sequence_io import load_sequence_data


class ResultStorePhase3Test(unittest.TestCase):

    def test_dynamic_fields_view_state_and_plot_filter(self):
        store = ResultStore()
        store.append({"value": 1.2345, "reg_addr": "0x10"})
        store.append({"value": 2.0, "value_dec": 31, "status": "OK"})

        self.assertEqual(list(store.fields.keys()), ["value", "reg_addr", "value_dec", "status"])
        self.assertIn("value", store.plot_series())
        self.assertIn("value_dec", store.plot_series())
        self.assertNotIn("reg_addr", store.plot_series())
        self.assertNotIn("status", store.plot_series())

        store.set_display_name("value", "Measured Value")
        store.set_field_format("value", "2")
        store.hide_field("status")
        headers, rows = store.view_table()

        self.assertEqual(headers, ["Measured Value", "reg_addr", "value_dec"])
        self.assertEqual(rows[0][0], "1.23")
        self.assertEqual(rows[1][2], "31")

    def test_visible_csv_export_uses_view_state_without_mutating_records(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore()
            store.append({"a": 2, "b": 10})
            store.append({"a": 1, "b": 20})
            store.set_display_name("a", "A Display")
            store.hide_field("b")
            store.sort_by("a", ascending=True)

            path = os.path.join(tmpdir, "visible.csv")
            store.export_csv(path, view=True)

            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))

            self.assertEqual(rows, [["A Display"], ["1"], ["2"]])
            self.assertEqual(store.records[0], {"a": 2, "b": 10})

    def test_default_result_path_uses_unified_name(self):
        path = build_default_result_path(
            "C:\\Project",
            chip_or_profile="BES 1505",
            fmt="csv",
        )
        self.assertRegex(
            path.replace("\\", "/"),
            r"Results/custom_test/\d{8}_\d{6}/custom_test_BES_1505_\d{8}_\d{6}\.csv$",
        )


@unittest.skipUnless(_PYSIDE_AVAILABLE, "PySide6 is required for Custom Test executor smoke tests")
class ExecutorResultStorePhase3Test(unittest.TestCase):

    def test_executor_records_source_node_and_export_result_uses_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_sequence_data([
                {
                    "node_type": "SetVariable",
                    "params": {"var_name": "seed", "value": 7, "export_var": True},
                },
                {
                    "node_type": "RecordDataPoint",
                    "uid": "record-node-1",
                    "params": {"fields": "seed=${seed}, extra=3.14", "skip_no_export": True},
                },
                {
                    "node_type": "ExportResult",
                    "params": {
                        "format": "csv",
                        "filename": "phase3_smoke",
                        "output_dir": tmpdir,
                    },
                },
            ])

            context = ExecutionContext()
            finished = []
            executor = CustomTestExecutor()
            executor.finished.connect(lambda success, message: finished.append((success, message)))
            executor.set_sequence(result.nodes)
            executor.set_context(context)
            executor.run()

            self.assertEqual(finished, [(True, "执行完成")])
            self.assertEqual(context.records, [{"seed": 7, "extra": 3.14}])
            self.assertEqual(context.result_store.rows[0].source_node_uid, "record-node-1")

            export_path = context.get_variable("_export_path")
            manifest_path = os.path.join(tmpdir, "phase3_smoke.manifest.json")
            self.assertEqual(export_path, os.path.join(tmpdir, "phase3_smoke.csv"))
            self.assertTrue(os.path.isfile(export_path))
            self.assertTrue(os.path.isfile(manifest_path))

            with open(export_path, newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[0], ["seed", "extra"])
            self.assertEqual(rows[1], ["7", "3.14"])

            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["row_count"], 1)


if __name__ == "__main__":
    unittest.main()
