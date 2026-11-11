#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：mock 三形态回归（A-only / B-only / A+B），验证波形 key 链路修复。

运行：python tests\\_debug_datalog_modes_mock.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import debug_config  # noqa: E402
debug_config.DEBUG_MOCK = True  # 须在导入 datalog 模块前置位

from PySide6.QtWidgets import QApplication  # noqa: E402

from instruments.mock.mock_instruments import MockIT2705, MockN6705C  # noqa: E402
from ui.pages.power_analyzer.datalog.datalog_ui import N6705CDatalogUI  # noqa: E402

PASS = []


def _check(name, cond, detail=""):
    PASS.append(bool(cond))
    print(f"[{'OK' if cond else 'FAIL'}] {name} {detail}")


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def run_mode(mode):
    app = QApplication.instance() or QApplication(sys.argv)
    ui = N6705CDatalogUI()
    if mode in ("a_only", "mixed"):
        ui._apply_slot_state("A", True, instance=MockN6705C(), serial="MA",
                             visa_resource="MOCK::N6705C", model="N6705C")
    if mode in ("b_only", "mixed"):
        it = MockIT2705()
        it.refresh_channel_modules()
        ui._apply_slot_state("B", True, instance=it, serial="MB",
                             visa_resource="MOCK::IT2705", model="IT2705")
    ui._after_slot_states_synced()
    if ui.ch_current_cbs_a:
        ui.ch_current_cbs_a[0].setChecked(True)
        ui.ch_voltage_cbs_a[0].setChecked(True)
    if ui.ch_current_cbs_b:
        ui.ch_current_cbs_b[0].setChecked(True)
        ui.ch_voltage_cbs_b[0].setChecked(True)

    ui.monitor_time_s_edit.setText("1")
    ui.sample_period_edit.setText("1000")
    ui.min_period_cb.setChecked(False)
    ui._start_recording()
    for _ in range(300):
        pump(app, 0.1)
        if ui._record_thread is None or not ui._record_thread.isRunning():
            break
    pump(app, 0.5)

    keys = list(ui.datalog_data.keys())
    curves = set(ui.plot_curves.keys())
    non_empty = {k for k, v in ui.datalog_data.items() if v["values"]}
    print(f"  keys={keys}")
    print(f"  curves={sorted(curves)} non_empty={sorted(non_empty)}")
    return ui, keys, curves, non_empty


def main():
    print("=== a_only ===")
    _, keys, curves, non_empty = run_mode("a_only")
    _check("a_only keys unprefixed", all(k.startswith("CH1") for k in keys), f"{keys}")
    _check("a_only curves cover data", curves == non_empty and bool(curves))

    print("=== b_only ===")
    _, keys, curves, non_empty = run_mode("b_only")
    _check("b_only keys keep B prefix", all(k.startswith("B CH1") for k in keys), f"{keys}")
    _check("b_only curves cover data", curves == non_empty and bool(curves))

    print("=== mixed ===")
    _, keys, curves, non_empty = run_mode("mixed")
    _check("mixed keys A+B", any(k.startswith("A CH1") for k in keys)
           and any(k.startswith("B CH1") for k in keys), f"{keys}")
    _check("mixed curves cover data", curves == non_empty and bool(curves))

    print("RESULT:", "ALL_OK" if all(PASS) else "FAILED")
    return 0 if all(PASS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
