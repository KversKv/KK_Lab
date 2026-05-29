import os
import sys
import threading
import time
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

from core.custom_test.context import ExecutionContext
from core.custom_test.compiler import build_dry_run_summary, compile_sequence
from core.custom_test.breakpoints import BreakpointSet, StepRunState
from core.custom_test.document import CustomTestDocument
from core.custom_test.macros import CustomTestMacro
from core.custom_test.paths import resolve_template_path
from core.custom_test.remote import HeadlessRunRequest
from core.custom_test.resolver import InstrumentResolver
from core.custom_test.serialization import (
    load_sequence_data,
    load_sequence_file,
    migrate_sequence,
    save_sequence_data,
)
from core.custom_test.snapshot import build_sequence_hash, clone_sequence
from core.custom_test.sweep import SweepAxis, SweepPlan

if _PYSIDE_AVAILABLE:
    from core.custom_test.executor import CustomTestExecutor


class CustomTestPhase5CoreTest(unittest.TestCase):

    def test_context_sleep_can_be_cancelled(self):
        context = ExecutionContext()
        result = []

        worker = threading.Thread(
            target=lambda: result.append(context.sleep(5.0, poll=0.01)),
            daemon=True,
        )
        worker.start()
        time.sleep(0.05)
        context.request_stop()
        worker.join(timeout=1.0)

        self.assertFalse(worker.is_alive())
        self.assertEqual(result, [False])

    def test_sequence_migration_reports_unknown_nodes_and_missing_params(self):
        migrated, issues = migrate_sequence([
            {"node_type": "SetVariable", "params": {"var_name": "x"}},
            {"node_type": "UnknownNode", "params": {}},
        ])

        self.assertEqual(migrated["version"], 2)
        self.assertEqual(migrated["metadata"]["migrated_from"], "legacy_list")
        self.assertTrue(any(issue.severity == "warning" and "value" in issue.message for issue in issues))
        self.assertTrue(any(issue.severity == "error" and "UnknownNode" in issue.message for issue in issues))

    def test_save_sequence_writes_v2_and_required_capabilities(self):
        result = load_sequence_data([
            {
                "node_type": "N6705CMeasure",
                "params": {
                    "channel": 1,
                    "measure_type": "current",
                    "result_var": "ibat_a",
                    "export_var": True,
                },
            }
        ])

        saved = save_sequence_data(result.nodes, instruments={"n6705c": {"session": "mock"}})

        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["instruments"]["n6705c"]["session"], "mock")
        self.assertEqual(saved["metadata"]["required_capabilities"], ["power_analyzer.measure"])

    def test_snapshot_clone_and_hash_are_run_stable(self):
        result = load_sequence_data([
            {
                "node_type": "SetVariable",
                "params": {"var_name": "x", "value": 1, "export_var": True},
            }
        ])

        snapshot = clone_sequence(result.nodes)
        before_hash = build_sequence_hash(snapshot)
        result.nodes[0].params["value"] = 2

        self.assertEqual(snapshot[0].params["value"], 1)
        self.assertEqual(before_hash, build_sequence_hash(snapshot))
        self.assertNotEqual(before_hash, build_sequence_hash(result.nodes))

    def test_document_v3_migrates_v2_and_dry_run_plan_compiles(self):
        loaded = load_sequence_data([
            {
                "node_type": "LoopCount",
                "params": {"count": 2, "var_name": "n"},
                "children": [
                    {
                        "node_type": "RecordDataPoint",
                        "params": {"fields": "n=${n}", "skip_no_export": True},
                    }
                ],
            }
        ])

        doc = CustomTestDocument.from_data(save_sequence_data(loaded.nodes))
        plan = compile_sequence(doc.nodes)
        dry_run = build_dry_run_summary(doc.nodes)

        self.assertTrue(doc.dirty)
        self.assertEqual(doc.version, 3)
        self.assertEqual(plan.total_steps, 2)
        self.assertEqual(dry_run["total_steps"], 2)

    def test_phase5_long_term_models_are_available(self):
        loaded = load_sequence_data([
            {
                "node_type": "SetVariable",
                "uid": "set-seed",
                "params": {"var_name": "seed", "value": 1, "export_var": True},
            }
        ])

        breakpoints = BreakpointSet.from_iterable(["set-seed"])
        step_state = StepRunState()
        macro = CustomTestMacro("seed", loaded.nodes)
        sweep = SweepPlan([
            SweepAxis("temp", [25, 40]),
            SweepAxis("vbat", [3.7, 4.2]),
        ])
        request = HeadlessRunRequest(save_sequence_data(loaded.nodes), allow_mock=True)

        self.assertTrue(step_state.stop_before("set-seed", breakpoints))
        self.assertNotEqual(macro.instantiate()[0].uid, loaded.nodes[0].uid)
        self.assertEqual(sweep.total_points, 4)
        self.assertEqual(len(list(sweep.iter_points())), 4)
        self.assertEqual(len(request.load_document().nodes), 1)

    def test_sample_templates_are_v2_with_capabilities(self):
        sample_names = [
            "sample_n6705c_voltage_sweep.json",
            "sample_i2c_register_sweep.json",
            "sample_chamber_n6705c_loop.json",
            "sample_uart_send_receive.json",
        ]

        for name in sample_names:
            result = load_sequence_file(resolve_template_path(name))
            self.assertEqual(result.version, 2, name)
            self.assertGreater(len(result.nodes), 0, name)
            self.assertGreater(len(result.metadata.get("required_capabilities", [])), 0, name)


@unittest.skipUnless(_PYSIDE_AVAILABLE, "PySide6 is required for Custom Test executor smoke tests")
class CustomTestPhase5ExecutorSmokeTest(unittest.TestCase):

    def _run_with_mock_resolver(self, sequence_data):
        loaded = load_sequence_data(sequence_data)
        resolver = InstrumentResolver(allow_mock=True, allow_i2c_autoconnect=False)
        resolved = resolver.resolve(loaded.nodes)
        self.assertEqual(resolved.missing, [])

        context = ExecutionContext(
            instruments=resolved.as_instrument_dict(),
            resolved_instruments=resolved,
        )
        finished = []
        executor = CustomTestExecutor()
        executor.finished.connect(lambda success, message: finished.append((success, message)))
        executor.set_sequence(loaded.nodes)
        executor.set_context(context)
        executor.run()

        self.assertEqual(finished, [(True, "执行完成")])
        return context, resolved

    def test_pure_logic_smoke_sequence(self):
        context, _ = self._run_with_mock_resolver([
            {
                "node_type": "SetVariable",
                "params": {"var_name": "seed", "value": 3, "export_var": True},
            },
            {
                "node_type": "LoopCount",
                "params": {"count": 2, "var_name": "n"},
                "children": [
                    {
                        "node_type": "MathExpression",
                        "params": {"expression": "${seed} + ${n}", "result_var": "value"},
                    },
                    {
                        "node_type": "RecordDataPoint",
                        "params": {"fields": "n=${n}, value=${value}", "skip_no_export": True},
                    },
                ],
            },
        ])

        self.assertEqual([row["value"] for row in context.records], [3, 4])

    def test_mock_instrument_adapter_smoke_sequence(self):
        context, resolved = self._run_with_mock_resolver([
            {
                "node_type": "N6705CSetVoltage",
                "params": {"channel": 1, "voltage": 3.8, "current_limit": 0.5, "output_on": True},
            },
            {
                "node_type": "N6705CMeasure",
                "params": {
                    "channel": 1,
                    "measure_type": "voltage",
                    "result_var": "vbat_v",
                    "export_var": True,
                },
            },
            {
                "node_type": "ScopeMeasure",
                "params": {
                    "channel": 1,
                    "measure_type": "frequency",
                    "result_var": "scope_freq_hz",
                    "export_var": True,
                },
            },
            {
                "node_type": "I2CWrite",
                "params": {"device_addr": "0x17", "reg_addr": "0x0010", "write_data": "0x55", "width": 10},
            },
            {
                "node_type": "I2CRead",
                "params": {
                    "device_addr": "0x17",
                    "reg_addr": "0x0010",
                    "width": 10,
                    "result_var": "reg_val",
                    "export_var": True,
                    "auto_record": False,
                },
            },
            {
                "node_type": "MCUIOPulse",
                "params": {
                    "pin": 1,
                    "active_level": 1,
                    "inactive_level": 0,
                    "duration_s": 0.01,
                    "release_high_z": True,
                },
            },
            {
                "node_type": "MCUIORead",
                "params": {"pin": 1, "pull": "none", "result_var": "gpio_val", "auto_record": False},
            },
            {
                "node_type": "UARTSend",
                "params": {"data": "AT\\r\\n", "hex_mode": False},
            },
            {
                "node_type": "UARTReceive",
                "params": {"timeout_s": 0.5, "expect": "OK", "result_var": "uart_rx", "auto_record": False},
            },
            {
                "node_type": "RecordDataPoint",
                "params": {
                    "fields": (
                        "vbat_v=${vbat_v}, scope_freq_hz=${scope_freq_hz}, "
                        "reg_val=${reg_val}, gpio_val=${gpio_val}, uart_rx=${uart_rx}"
                    ),
                    "skip_no_export": True,
                },
            },
        ])

        self.assertEqual(
            {key: item.source for key, item in resolved.instruments.items()},
            {
                "i2c": "mock",
                "mcu_io": "mock",
                "n6705c": "mock",
                "scope": "mock",
                "uart": "mock",
            },
        )
        self.assertEqual(context.get_variable("reg_val"), 0x55)
        self.assertIn("OK", context.get_variable("uart_rx"))
        self.assertEqual(len(context.records), 1)

    def test_mock_chamber_loop_smoke_sequence(self):
        template_path = resolve_template_path("sample_chamber_n6705c_loop.json")
        loaded = load_sequence_file(template_path)
        context, resolved = self._run_with_mock_resolver([node.to_dict() for node in loaded.nodes])

        self.assertEqual(resolved.instruments["chamber"].source, "mock")
        self.assertEqual(len(context.records), 2)
        self.assertEqual([row["temp_c"] for row in context.records], [25, 40])


if __name__ == "__main__":
    unittest.main()
