#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：真机复现 Datalog 两问题。

运行：python tests\\_debug_datalog_mixed_real.py [a_only|b_only|mixed]
真机：N6705C = TCPIP0::10.31.71.98::hislip0::INSTR
      IT2705 = TCPIP0::10.31.71.168::30000::SOCKET
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from instruments.factory import create_power_analyzer, get_power_analyzer_idn  # noqa: E402
from ui.pages.power_analyzer.datalog.datalog_ui import N6705CDatalogUI  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def connect(addr):
    inst = create_power_analyzer(addr, analyzer_type="auto")
    idn = get_power_analyzer_idn(inst)
    print(f"connected {addr} -> {idn}")
    return inst


def dump(ui, tag):
    print(f"\n--- {tag} ---")
    print("datalog_data keys:", list(ui.datalog_data.keys()))
    print("plot_curves:", list(ui.plot_curves.keys()))
    print("visible keys:", sorted(ui._get_visible_keys()))
    print("meas_table rows:", ui.meas_table.rowCount())
    print("overlay visible:", ui._progress_overlay.isVisible(),
          "| is_recording:", ui.is_recording)
    for slot, cbs in (("A-I", ui.ch_current_cbs_a), ("A-V", ui.ch_voltage_cbs_a),
                      ("B-I", ui.ch_current_cbs_b), ("B-V", ui.ch_voltage_cbs_b)):
        if cbs:
            print(slot, [(b.text(), b.isEnabled(), b.isChecked()) for b in cbs])


def run_record(ui, app):
    ui.monitor_time_s_edit.setText("1")
    ui.sample_period_edit.setText("1000")
    ui.min_period_cb.setChecked(False)

    orig_err = ui._on_recording_error
    ui._on_recording_error = lambda msg: (print("!!! RECORDING ERROR:", msg), orig_err(msg))

    ui._start_recording()
    if ui._record_thread is None:
        print("!!! _start_recording 未创建线程（静默返回）")
        return
    for _ in range(300):
        pump(app, 0.1)
        if ui._record_thread is None or not ui._record_thread.isRunning():
            break
    pump(app, 0.5)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "mixed"
    app = QApplication(sys.argv)
    ui = N6705CDatalogUI()

    if mode in ("a_only", "mixed"):
        inst_a = connect(N6705C_RES)
        ui._apply_slot_state("A", True, instance=inst_a, serial="A98",
                             visa_resource=N6705C_RES, model="N6705C")
    if mode in ("b_only", "mixed"):
        inst_b = connect(IT2705_RES)
        ui._apply_slot_state("B", True, instance=inst_b, serial="B168",
                             visa_resource=IT2705_RES, model="IT2705")
    ui._after_slot_states_synced()
    dump(ui, "after connect")

    # 勾选 CH1 V/I（存在的槽）
    if mode in ("a_only", "mixed") and ui.ch_current_cbs_a:
        ui.ch_current_cbs_a[0].setChecked(True)
        ui.ch_voltage_cbs_a[0].setChecked(True)
    if mode in ("b_only", "mixed") and ui.ch_current_cbs_b:
        ui.ch_current_cbs_b[0].setChecked(True)
        ui.ch_voltage_cbs_b[0].setChecked(True)
    dump(ui, "after user check")

    ui.resize(1280, 800)
    ui.show()
    pump(app, 0.3)
    run_record(ui, app)
    dump(ui, "after record")

    out = os.path.join(os.path.dirname(__file__), f"_datalog_{mode}_grab.png")
    ui.plot_widget.grab().save(out)
    print("saved:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
