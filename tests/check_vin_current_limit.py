#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Max Iload → Vin 限流 (Max Iload + 0.1) A 的 Mock 全流程校验。

覆盖三点：
  A. DUT 配置 Max Iload 输入框经 ModuleConfigStore collect/restore 往返；
  B. runner 测试开始前把 Vin 通道限流设为 (max_iload_ma/1000 + 0.1) A，
     且测试项 setup_source_channel 重配 Vin 时保持同一限流（MockN6705C
     记录的最终 _channel_current_limits 断言）；
  C. 旧配置缺 max_iload_ma 键时回落默认 400mA → 0.5A（与旧硬编码一致）。

用法：.venv\\Scripts\\python.exe tests\\check_vin_current_limit.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import debug_config  # noqa: E402

debug_config.DEBUG_MOCK = True

import core.module_test._runner_base as runner_base  # noqa: E402

runner_base.DEBUG_MOCK = True  # runner 模块内 from-import 的副本同步打开

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.module_test._common import vin_current_limit_a  # noqa: E402
from core.module_test.ldo.ldo_runner import LDOTestRunner  # noqa: E402
from instruments.mock.mock_instruments import MockN6705C  # noqa: E402
from ui.pages.module_test._sections.config_store import ModuleConfigStore  # noqa: E402
from ui.pages.module_test._sections.left_rail import DutConfigPanel  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


class _FakePlan:
    def selected_keys(self):
        return ["ldo_load_reg"]

    def set_checked_keys(self, _keys):
        pass

    def set_item_customized(self, _k, _v):
        pass


class _FakeModCfg:
    def is_enabled(self):
        return False

    def config_text(self):
        return ""

    def set_enabled(self, _v):
        pass

    def set_config_text(self, _t):
        pass


def _make_store(panel: DutConfigPanel) -> ModuleConfigStore:
    return ModuleConfigStore(
        module_type="ldo", dut_panel=panel, test_plan=_FakePlan(),
        item_overrides={}, items_registry={},
        module_config_panel=_FakeModCfg(), judge_criteria={})


def check_ui_roundtrip() -> None:
    panel = DutConfigPanel("ldo")
    store = _make_store(panel)
    cfg = store.collect()
    check("A1 collect 含 max_iload_ma 默认 400", cfg.get("max_iload_ma") == 400,
          f"got {cfg.get('max_iload_ma')!r}")

    panel.max_iload_spin.setValue(850)
    cfg = store.collect()
    check("A2 collect 采集改动后 850", cfg.get("max_iload_ma") == 850,
          f"got {cfg.get('max_iload_ma')!r}")

    panel2 = DutConfigPanel("dcdc")
    _make_store(panel2).restore(cfg)
    check("A3 restore 回填 850", panel2.max_iload_spin.value() == 850,
          f"got {panel2.max_iload_spin.value()!r}")

    cfg.pop("max_iload_ma")
    panel3 = DutConfigPanel("ldo")
    _make_store(panel3).restore(cfg)
    check("A4 旧配置缺键不覆盖默认值", panel3.max_iload_spin.value() == 400,
          f"got {panel3.max_iload_spin.value()!r}")


def check_helper() -> None:
    check("C1 缺键回落 0.5A", abs(vin_current_limit_a({}) - 0.5) < 1e-9,
          f"got {vin_current_limit_a({})}")
    check("C2 0mA -> 0.1A", abs(vin_current_limit_a({"max_iload_ma": 0}) - 0.1) < 1e-9)
    check("C3 2000mA -> 2.1A", abs(vin_current_limit_a({"max_iload_ma": 2000}) - 2.1) < 1e-9)


def check_runner(app: QApplication) -> None:
    mock = MockN6705C()
    logs: list[str] = []
    cfg = {
        "chip_name": "MOCKCHIP",
        "module_name": "LDO_X",
        "operator": "",
        "selected_items": ["ldo_load_reg"],
        "vin_channel": "CH 1",
        "vout_channel": "CH 2",
        "iload_channel": "CH 3",
        "max_iload_ma": 600,
        "item_overrides": {},
    }
    runner = LDOTestRunner(config=cfg, n6705c=mock, scope=None)
    runner.log.connect(logs.append)
    done = {"ok": False}

    def on_finished(_result):
        done["ok"] = True
        app.quit()

    def on_failed(msg):
        print(f"[RUNNER FAILED] {msg}")
        app.quit()

    runner.finished_result.connect(on_finished)
    runner.failed.connect(on_failed)
    runner.start()
    app.exec()

    check("B1 runner 跑完", done["ok"])
    limit = mock._channel_current_limits.get(1)
    check("B2 Vin ch1 最终限流 0.7A (600mA+0.1A)",
          limit is not None and abs(limit - 0.7) < 1e-9, f"got {limit!r}")
    pre = [m for m in logs if m.startswith("[PRE] Vin 通道")]
    check("B3 [PRE] 限流日志", bool(pre) and "0.700 A" in pre[0], f"got {pre!r}")


def main() -> int:
    app = QApplication(sys.argv)
    check_helper()
    check_ui_roundtrip()
    check_runner(app)
    if FAILURES:
        print(f"\n{len(FAILURES)} 项失败: {FAILURES}")
        return 1
    print("\n全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
