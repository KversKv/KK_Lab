"""P3 重构冒烟：ModuleTestUI 布局 / 契约 / 状态机 / precheck（offscreen）。

    python tests/test_p3_smoke.py
    pytest tests/test_p3_smoke.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.pages.module_test.module_test_ui import ModuleTestUI
from ui.pages.module_test.ldo_test_ui import LDOTestUI
from ui.pages.module_test.dcdc_test_ui import DCDCTestUI
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
    assert LDOTestUI.STANDALONE_ITEMS == ("ldo_psrr", "ldo_protection")
    assert LDOTestUI.RUNNER_CLS is not None and DCDCTestUI.RUNNER_CLS is not None
    assert LDOTestUI.ITEMS_REGISTRY and DCDCTestUI.ITEMS_REGISTRY


def test_get_test_config_keys_and_defaults():
    ui = _make()
    cfg = ui.ldo_test_ui.get_test_config()
    expected = {"selected_items", "chip_name", "module_name", "operator",
                "temp_test_enabled", "temperature", "temp_soak_s",
                "temp_tolerance_c", "temp_wait_s", "vin_channel", "vout_channel",
                "iload_channel", "vout_nominal_mv", "device_addr", "width_flag",
                "scope_vout_channel", "item_overrides"}
    assert set(cfg.keys()) == expected
    assert cfg["vout_nominal_mv"] == 1800
    assert ui.dcdc_test_ui.get_test_config()["vout_nominal_mv"] == 1200


def test_ai_contract_behaviour():
    sub = _make().ldo_test_ui
    assert len(sub.ai_capabilities()) == 5
    ok, _msg = sub.ai_apply_config({"chip_name": "BES1307"})
    assert ok
    assert sub.left_rail.dut_panel.chip_name_edit.text() == "BES1307"
    # LDO 注册表默认全不勾选 → 未勾选拦截
    ok2, msg2 = sub.ai_start_test()
    assert ok2 is False and "勾选" in msg2
    assert sub.ai_get_result_summary() is None


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
