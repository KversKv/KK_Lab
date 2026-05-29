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

if _PYSIDE_AVAILABLE:
    from ui.pages.custom_test.context import ExecutionContext
    from ui.pages.custom_test.executor import CustomTestExecutor
from ui.pages.custom_test.node_metadata import (
    STABLE,
    UNSUPPORTED,
    build_node_inventory,
    get_node_status,
    get_required_instruments,
    is_node_selectable,
)
from ui.pages.custom_test.sequence_io import load_sequence_data, load_sequence_file
from core.custom_test.paths import iter_template_files


@unittest.skipUnless(_PYSIDE_AVAILABLE, "PySide6 is required for Custom Test executor smoke tests")
class CustomTestPhase0Test(unittest.TestCase):

    def test_load_sequence_data_supports_list_and_dict(self):
        list_data = [
            {
                "node_type": "SetVariable",
                "params": {"var_name": "value", "value": 1, "export_var": True},
            }
        ]
        list_result = load_sequence_data(list_data)
        self.assertEqual(list_result.source_format, "list")
        self.assertEqual(len(list_result.nodes), 1)
        self.assertEqual(list_result.instruments, {})

        dict_result = load_sequence_data({
            "version": 1,
            "sequence": list_data,
            "instruments": {"n6705c": {"visa": "MOCK::N6705C"}},
        })
        self.assertEqual(dict_result.source_format, "dict")
        self.assertEqual(dict_result.version, 1)
        self.assertEqual(dict_result.instruments["n6705c"]["visa"], "MOCK::N6705C")

    def test_all_builtin_templates_load_through_shared_entry(self):
        loaded = []
        for path in iter_template_files():
            name = os.path.basename(path)
            result = load_sequence_file(path)
            self.assertGreater(len(result.nodes), 0, name)
            self.assertIn(result.source_format, {"list", "dict"})
            loaded.append(name)
        self.assertGreaterEqual(len(loaded), 1)

    def test_logic_record_export_smoke_runs_without_ui(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sequence = load_sequence_data([
                {
                    "node_type": "SetVariable",
                    "params": {"var_name": "seed", "value": 2, "export_var": True},
                },
                {
                    "node_type": "LoopCount",
                    "params": {"count": 3, "var_name": "n"},
                    "children": [
                        {
                            "node_type": "IfBlock",
                            "children": [
                                {
                                    "node_type": "IfBranch",
                                    "params": {"condition": "${n} >= 1"},
                                    "children": [
                                        {
                                            "node_type": "RecordDataPoint",
                                            "params": {
                                                "fields": "n=${n}, seed=${seed}",
                                                "skip_no_export": True,
                                            },
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                },
                {
                    "node_type": "ExportResult",
                    "params": {
                        "format": "csv",
                        "filename": "phase0_smoke",
                        "output_dir": tmpdir,
                    },
                },
            ]).nodes

            context = ExecutionContext()
            finished = []
            executor = CustomTestExecutor()
            executor.finished.connect(lambda success, message: finished.append((success, message)))
            executor.set_sequence(sequence)
            executor.set_context(context)
            executor.run()

            self.assertEqual(finished, [(True, "执行完成")])
            self.assertEqual([row["n"] for row in context.records], [1, 2])
            self.assertEqual([row["seed"] for row in context.records], [2, 2])
            export_path = context.get_variable("_export_path")
            self.assertTrue(export_path.endswith("phase0_smoke.csv"))
            self.assertTrue(os.path.isfile(export_path))

    def test_context_pause_stop_state(self):
        context = ExecutionContext()
        self.assertFalse(context.should_pause)
        self.assertFalse(context.should_stop)

        context.request_pause()
        self.assertTrue(context.should_pause)

        context.request_resume()
        self.assertFalse(context.should_pause)

        context.request_stop()
        self.assertTrue(context.should_stop)

    def test_node_inventory_marks_phase0_decisions(self):
        inventory = {row["node_type"]: row for row in build_node_inventory()}
        self.assertIn("N6705CMeasure", inventory)
        self.assertEqual(get_required_instruments("N6705CMeasure"), ["n6705c"])
        self.assertTrue(inventory["RecordDataPoint"]["record_data"])

        self.assertEqual(get_node_status("RFAnalyzerMeasure"), UNSUPPORTED)
        self.assertEqual(get_node_status("PromptUser"), STABLE)
        self.assertFalse(is_node_selectable("RFAnalyzerMeasure"))
        self.assertTrue(is_node_selectable("PromptUser"))


if __name__ == "__main__":
    unittest.main()
