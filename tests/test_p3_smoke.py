"""P3 重构冒烟：ModuleTestUI 布局 / 契约 / 状态机 / precheck（offscreen）。

    python tests/test_p3_smoke.py
    pytest tests/test_p3_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.pages.module_test.module_test_ui import ModuleTestUI
from ui.pages.module_test.ldo_test_ui import LDOTestUI
from ui.pages.module_test.dcdc_test_ui import DCDCTestUI
from ui.pages.module_test.dialogs.config_manager_dialog import ConfigManagerDialog
from ui.widgets.run_control_bar import RunState

_app = QApplication.instance() or QApplication(sys.argv)


def _make() -> ModuleTestUI:
    return ModuleTestUI()


def test_top_level_contract_and_switching():
    ui = _make()
    assert ui.get_current_test() == "ldo"
    ui.set_current_test("dcdc")
    assert ui.get_current_test() == "dcdc"
    assert ui.command_bar.current_module() == "dcdc"
    ui.set_current_test("ldo")
    assert ui.get_current_test() == "ldo"
    assert ui.TEST_TAB_MAP == {"ldo": 0, "dcdc": 1}


def test_subpage_public_api_present():
    sub = _make().ldo_test_ui
    for m in ("get_test_config", "update_test_result", "clear_results",
              "set_system_status", "prompt_config_manager_once",
              "sync_n6705c_from_top", "sync_oscilloscope_from_top",
              "ai_capabilities", "ai_get_config", "ai_apply_config",
              "ai_start_test", "ai_stop_test", "ai_get_result_summary"):
        assert hasattr(sub, m), m


def test_class_attr_differentiation():
    assert LDOTestUI.MODULE_TYPE == "ldo" and DCDCTestUI.MODULE_TYPE == "dcdc"
    assert LDOTestUI.PAGE_KEY == "module_test_ldo"
    assert LDOTestUI.STANDALONE_ITEMS == (
        "ldo_psrr", "ldo_protection", "ldo_dropout", "ldo_current_limit")
    assert LDOTestUI.RUNNER_CLS is not None and DCDCTestUI.RUNNER_CLS is not None
    assert LDOTestUI.ITEMS_REGISTRY and DCDCTestUI.ITEMS_REGISTRY
    keys = list(LDOTestUI.ITEMS_REGISTRY)
    assert keys.index("ldo_ripple") == keys.index("ldo_load_reg") - 1


def test_get_test_config_keys_and_defaults():
    ui = _make()
    ui.ldo_test_ui._store.restore(
        {"chip_name": "BES1307", "chip_version": "", "vin_v": 4.2,
         "vout_nominal_mv": 1800, "judge_enabled": True})
    cfg = ui.ldo_test_ui.get_test_config()
    expected = {"selected_items", "chip_name", "chip_version", "module_name", "test_condition",
                "operator",
                "temp_test_enabled", "temperature", "temp_soak_s",
                "temp_tolerance_c", "temp_wait_s", "vbat_channel", "vin_channel",
                "vout_channel", "force_channel", "volt_method",
                "iload_channel", "vin_v", "vout_nominal_mv", "max_iload_ma",
                "device_addr", "width_flag",
                "scope_vout_channel", "item_overrides",
                "module_config_enabled", "module_config_yaml", "judge_enabled",
                "judge_criteria"}
    assert set(cfg.keys()) == expected
    assert cfg["chip_version"] == ""
    assert cfg["vin_v"] == 4.2
    assert cfg["vout_nominal_mv"] == 1800
    assert cfg["judge_enabled"] is True
    ui.ldo_test_ui.test_plan.set_judge_enabled(False)
    assert ui.ldo_test_ui.get_test_config()["judge_enabled"] is False
    ui.ldo_test_ui._store.restore({"judge_enabled": True})
    assert ui.ldo_test_ui.test_plan.judge_enabled() is True
    assert ui.dcdc_test_ui.get_test_config()["vout_nominal_mv"] == 1200
    assert "vin_v" not in ui.dcdc_test_ui.get_test_config()


def test_ldo_shared_vin_and_legacy_override_cleanup():
    shared_keys = ("ldo_ripple", "ldo_load_reg", "ldo_current_limit",
                   "ldo_quiescent", "ldo_output_noise")
    for key in shared_keys:
        assert all(p.key != "vin_v" for p in LDOTestUI.ITEMS_REGISTRY[key][4])
    assert any(p.key == "vin_v" for p in LDOTestUI.ITEMS_REGISTRY["ldo_vout_scan"][4])
    assert any(p.key == "vin_v" for p in DCDCTestUI.ITEMS_REGISTRY["dcdc_ripple"][4])

    sub = _make().ldo_test_ui
    sub._store.restore({
        "vin_v": 4.1,
        "item_overrides": {
            "ldo_ripple": {"vin_v": 5.0},
            "ldo_load_reg": {"vin_v": 4.9, "settle_time_s": 0.02},
            "ldo_vout_scan": {"vin_v": 4.8},
        },
    })
    cfg = sub.get_test_config()
    assert cfg["vin_v"] == 4.1
    assert "ldo_ripple" not in cfg["item_overrides"]
    assert cfg["item_overrides"]["ldo_load_reg"] == {"settle_time_s": 0.02}
    assert cfg["item_overrides"]["ldo_vout_scan"] == {"vin_v": 4.8}


def test_legacy_1860_chip_version_restore():
    sub = _make().ldo_test_ui
    dut = sub.left_rail.dut_panel
    sub._store.restore({"chip_name": "BES1860verB"})
    assert dut.chip_name_edit.text() == "BES1860"
    assert dut.chip_version_edit.text() == "B版"
    sub._store.restore({"chip_name": "BES1860"})
    assert dut.chip_version_edit.text() == "A版"
    sub._store.restore({"chip_name": "BES1310"})
    assert dut.chip_version_edit.text() == ""


def test_config_manager_groups_1860_versions():
    with tempfile.TemporaryDirectory() as root:
        for directory, chip in (("BES1860", "BES1860"),
                                ("BES1860verB", "BES1860verB")):
            target_dir = os.path.join(root, directory)
            os.makedirs(target_dir)
            payload = {"schema_version": 1, "module_type": "ldo",
                       "config": {"chip_name": chip, "module_name": "LDO_01"}}
            with open(os.path.join(target_dir, "LDO_01.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        dlg = ConfigManagerDialog(root, "ldo")
        chip_node = next(dlg.tree.topLevelItem(i) for i in range(dlg.tree.topLevelItemCount())
                         if dlg.tree.topLevelItem(i).text(0) == "BES1860")
        assert chip_node.childCount() == 2
        assert [chip_node.child(i).text(0) for i in range(2)] == ["A版", "B版"]
        assert not chip_node.isExpanded()
        assert not dlg.expand_btn.text()
        assert dlg.expand_btn.parentWidget() is dlg.tree.header()
        assert not dlg.expand_btn.icon().isNull()
        assert dlg.expand_btn.toolTip() == "全部展开"
        dlg.expand_btn.click()
        assert chip_node.isExpanded()
        assert all(chip_node.child(i).isExpanded() for i in range(2))
        assert dlg.expand_btn.toolTip() == "全部折叠"
        dlg._populate()
        chip_node = next(dlg.tree.topLevelItem(i) for i in range(dlg.tree.topLevelItemCount())
                         if dlg.tree.topLevelItem(i).text(0) == "BES1860")
        assert chip_node.isExpanded()
        dlg.expand_btn.click()
        assert not chip_node.isExpanded()
        for i, version in enumerate(("A版", "B版")):
            path = os.path.join(root, "BES1860", version, "LDO_01.json")
            assert os.path.isfile(path)
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)["config"]
            assert cfg["chip_name"] == "BES1860"
            assert cfg["chip_version"] == version
        assert not os.path.exists(os.path.join(root, "BES1860verB"))
        dlg.close()


def test_ai_contract_behaviour():
    sub = _make().ldo_test_ui
    assert len(sub.ai_capabilities()) == 5
    ok, _msg = sub.ai_apply_config({"chip_name": "BES1307", "chip_version": "A版"})
    assert ok
    assert sub.left_rail.dut_panel.chip_name_edit.text() == "BES1307"
    assert sub.left_rail.dut_panel.chip_version_edit.text() == "A版"
    # LDO 注册表默认全不勾选 → 未勾选拦截
    sub.test_plan.set_checked_keys(set())
    ok2, msg2 = sub.ai_start_test()
    assert ok2 is False and "勾选" in msg2
    # 无结果时返回最小摘要（available=False），而非 None——让 AI 能区分"未跑过"
    summary = sub.ai_get_result_summary()
    assert summary is not None
    assert summary["available"] is False
    assert summary["module_type"] == "ldo"
    assert summary["running"] is False


def test_run_state_machine_toggle():
    sub = _make().ldo_test_ui
    assert sub._run_state is RunState.IDLE
    assert sub.run_bar.state() is RunState.IDLE
    sub._apply_run_state(RunState.RUNNING)
    assert sub.is_test_running
    assert not sub.left_rail.config_card.isEnabled()
    # offscreen 下父级未 show，isVisible() 恒 False；用 isHidden 断逻辑可见性
    assert not sub.left_rail._summary_bar.isHidden()
    sub._apply_run_state(RunState.IDLE)
    assert not sub.is_test_running
    assert sub.left_rail.config_card.isEnabled()


def test_judge_switch_run_lock():
    sub = _make().ldo_test_ui
    sub.test_plan.enter_run_state(["ldo_vout_scan"])
    assert not sub.test_plan.judge_enabled_check.isEnabled()
    sub.test_plan.exit_run_state()
    assert sub.test_plan.judge_enabled_check.isEnabled()


def test_precheck_rules():
    sub = _make().ldo_test_ui
    # 未勾选 → 拦截
    sub.test_plan.set_checked_keys(set())
    assert sub._precheck(sub.get_test_config()) is False
    # 勾选 + 必填缺失 → 拦截（行内校验）
    sub.test_plan.set_checked_keys({"ldo_vout_scan"})
    sub.left_rail.dut_panel.chip_name_edit.clear()
    assert sub._precheck(sub.get_test_config()) is False
    # 勾选 + 必填齐 + 缺仪器 → 拦截
    sub.left_rail.dut_panel.chip_name_edit.setText("BES1307")
    assert sub._precheck(sub.get_test_config()) is False


def test_top_level_proxy_apis():
    ui = _make()
    ui.update_test_result("ldo", None)
    ui.clear_all_results()
    ui.set_system_status("就绪")
    ui.command_bar.set_config_name("demo.json")
    assert ui.command_bar.config_name_label.text() == "demo.json"


def test_widgets_shim_compat():
    import warnings
    from ui.pages.module_test import widgets
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        box = widgets.CollapsibleGroupBox("旧接口", expanded=True)
        assert box.is_expanded()
        assert "QDialog" in widgets.DIALOG_QSS


def test_ldo_dropout_steps_logs_and_report():
    import csv
    from core.module_test._common import ItemContext
    from core.module_test.ldo.items import dropout
    from core.module_test.report import build_report_data
    from core.module_test.result_model import ModuleTestResult

    logs = []
    with tempfile.TemporaryDirectory() as out_dir:
        ctx = ItemContext(
            n6705c=None, scope=None, chamber=None,
            config={"vout_nominal_mv": 1800, "dropout_vin_hi_v": 2.0,
                    "dropout_vin_lo_v": 1.7, "dropout_vin_step_v": 0.05,
                    "dropout_iload_ma": 100, "vout_tol": 0.02},
            out_dir=out_dir, is_mock=True, stop_flag_fn=lambda: False,
            log_fn=logs.append, progress_fn=lambda _percent, _label: None,
        )
        result = dropout(ctx)
        with open(result.raw_csv_path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

        assert rows[0] == ["Step", "Iload Set (mA)", "Vin Set (V)",
                           "Vin Measured (V)", "Vout (mV)", "Threshold (mV)",
                           "Vin-Vout (mV)", "Iload Measured (mA)",
                           "Data / Calculation"]
        body = rows[1:]
        assert body[0][0] == "1. 配置"
        assert body[1][0] == "2. 基准"
        scan_rows = [row for row in body if row[0].startswith("3. 扫描")]
        assert len(scan_rows) == result.measured["scan_points"]
        assert body[-1][0] == "4. 计算"
        calc = body[-1]
        expected_mv = round(round(float(calc[2]) * 1000.0, 3) - float(calc[4]), 3)
        assert float(calc[6]) == expected_mv == result.measured["dropout_mv"]
        assert "Dropout=Vin-Vout=" in calc[8]
        assert calc[8] in result.notes

        log_text = "\n".join(logs)
        for step in ("步骤1/4", "步骤2/4", "步骤3/4", "步骤4/4"):
            assert step in log_text
        assert calc[8] in log_text

        report = build_report_data(ModuleTestResult(module_type="ldo", items=[result]))
        report_item = report["items"][0]
        assert report_item["note"] == result.notes
        assert report_item["table"]["rows"] == len(body)
        assert report_item["table"]["data"][-1][0] == "4. 计算"
        assert report_item["table"]["data"][-1][-1] == calc[8]
        metric_keys = {metric["key"] for metric in report_item["metrics"]}
        assert {"dropout", "v0", "dropout_vin", "dropout_vout",
                "threshold", "iload"} <= metric_keys


def test_ldo_dropout_auto_optimal_refines_at_1mv():
    import csv
    from unittest.mock import patch

    from core.module_test._common import ItemContext
    from core.module_test.ldo.items import dropout

    logs = []
    with patch("core.module_test.ldo.items.mock_jitter",
               side_effect=lambda base, ratio=0.02: base):
        with tempfile.TemporaryDirectory() as out_dir:
            ctx = ItemContext(
                n6705c=None, scope=None, chamber=None,
                config={"vout_nominal_mv": 1800, "dropout_vin_hi_v": 2.0,
                        "dropout_vin_lo_v": 1.7, "dropout_vin_step_v": 0.05,
                        "dropout_iload_ma": 100, "vout_tol": 0.02,
                        "dropout_auto_optimal": True},
                out_dir=out_dir, is_mock=True, stop_flag_fn=lambda: False,
                log_fn=logs.append, progress_fn=lambda _percent, _label: None,
            )
            result = dropout(ctx)
            with open(result.raw_csv_path, encoding="utf-8-sig", newline="") as f:
                rows = list(csv.reader(f))

    coarse_rows = [row for row in rows if row[0].startswith("3. 扫描")]
    fine_rows = [row for row in rows if row[0].startswith("3. 精扫")]
    assert coarse_rows and fine_rows
    coarse_trigger_vin = float(coarse_rows[-1][2])
    assert coarse_trigger_vin == 1.9
    assert float(fine_rows[0][2]) == coarse_trigger_vin + 0.05
    for previous, current in zip(fine_rows, fine_rows[1:]):
        assert round(float(previous[2]) - float(current[2]), 6) == 0.001
    assert float(fine_rows[-1][2]) == 1.943
    assert rows[-1][0] == "4. 计算"
    assert float(rows[-1][2]) == result.measured["dropout_vin_v"] == 1.943
    assert result.measured["dropout_mv"] == 180.0
    assert "1mV 精扫" in result.notes
    assert any("回退一个用户步进" in line for line in logs)


def test_ldo_dropout_step_supports_multiple_loads():
    import csv
    from core.module_test._common import ItemContext
    from core.module_test.ldo.items import dropout

    with tempfile.TemporaryDirectory() as out_dir:
        ctx = ItemContext(
            n6705c=None, scope=None, chamber=None,
            config={"vout_nominal_mv": 1800, "dropout_method": "step",
                    "dropout_vin_hi_v": 2.0, "dropout_vin_lo_v": 1.7,
                    "dropout_vin_step_v": 0.05,
                    "dropout_iload_ma": "100, 300, 500", "vout_tol": 0.02},
            out_dir=out_dir, is_mock=True, stop_flag_fn=lambda: False,
            log_fn=lambda _line: None, progress_fn=lambda _percent, _label: None,
        )
        result = dropout(ctx)
        with open(result.raw_csv_path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

    assert [load["iload_ma"] for load in result.measured["load_results"]] == [100, 300, 500]
    assert len(result.measured["dropout_mv"]) == 3
    config_rows = [row for row in rows if row[0] == "1. 配置"]
    assert [float(row[1]) for row in config_rows] == [100, 300, 500]
    assert len([row for row in rows if row[0] == "4. 计算"]) == 3


def test_ldo_dropout_direct_uses_four_wire_and_measured_values():
    import csv
    from core.module_test._common import ItemContext
    from core.module_test.judge import JUDGE_METRICS, extract_values
    from core.module_test.ldo.items import dropout
    from core.module_test.report import build_report_data
    from core.module_test.result_model import ModuleTestResult

    class FakeN6705C:
        def __init__(self):
            self.vin = 2.0
            self.iload_a = 0.1
            self.sense_calls = []
            self.load_settings = []

        def set_mode(self, _channel, _mode):
            pass

        def set_channel_range(self, _channel):
            pass

        def set_current_limit(self, _channel, _limit):
            pass

        def set_voltage(self, channel, voltage):
            if channel == 2:
                self.vin = voltage

        def set_current(self, _channel, current):
            self.iload_a = abs(current)
            self.load_settings.append(current)

        def set_sense_mode(self, channel, mode):
            self.sense_calls.append((channel, mode))

        def channel_on(self, _channel):
            pass

        def channel_off(self, _channel):
            pass

        def measure_voltage(self, channel):
            if channel == 2:
                return self.vin - 0.003
            return 1.8 if self.vin >= 1.98 else self.vin - 0.18

        def measure_current(self, _channel):
            return -(self.iload_a - 0.0002)

    logs = []
    fake = FakeN6705C()
    with tempfile.TemporaryDirectory() as out_dir:
        ctx = ItemContext(
            n6705c=fake, scope=None, chamber=None,
            config={"vout_nominal_mv": 1800, "dropout_method": "direct",
                    "dropout_vin_hi_v": 2.0, "dropout_vin_lo_v": 1.7,
                    "dropout_vin_step_v": 0.05,
                    "dropout_iload_ma": "100, 300", "vbat_channel": 1,
                    "vin_channel": 2, "vout_channel": 1, "iload_channel": 3,
                    "settle_time_s": 0.0, "average_cnt": 1},
            out_dir=out_dir, is_mock=False, stop_flag_fn=lambda: False,
            log_fn=logs.append, progress_fn=lambda _percent, _label: None,
        )
        result = dropout(ctx)
        with open(result.raw_csv_path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f))

    assert fake.sense_calls == [(2, "4 Wire"), (2, "4 Wire")]
    assert fake.load_settings == [-0.1, -0.3]
    assert result.measured["dropout_mv"] == [177.0, 177.0]
    assert [load["iload_measured_ma"] for load in result.measured["load_results"]] == [99.8, 299.8]
    calc_rows = [row for row in rows if row[0] == "4. 计算"]
    assert len(calc_rows) == 2
    assert all(float(row[3]) == 1.947 for row in calc_rows)
    assert all(float(row[4]) == 1770.0 for row in calc_rows)
    assert all(float(row[6]) == 177.0 for row in calc_rows)
    assert any("四线 Sense" in line for line in logs)
    metric = JUDGE_METRICS["ldo_dropout"][0]
    assert extract_values(result.measured, metric) == [177.0, 177.0]
    report = build_report_data(ModuleTestResult(module_type="ldo", items=[result]))
    metric_keys = {metric["key"] for metric in report["items"][0]["metrics"]}
    assert {"dropout_load_0", "dropout_load_1"} <= metric_keys


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_")}.items()):
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
