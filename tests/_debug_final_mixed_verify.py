#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：最终真机回归——当前修复代码下 A+B 全流程。

流程：启动(自动连A) → Scan → 卡片入口连B → Start → 等录制完成 → 校验。
运行：python tests\\_debug_final_mixed_verify.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.instruments import InstrumentManager  # noqa: E402
from ui.pages.power_analyzer.datalog.standalone import _StandaloneDatalogWindow  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def main():
    app = QApplication(sys.argv)
    manager = InstrumentManager()
    win = _StandaloneDatalogWindow(instrument_manager=manager)

    end = time.time() + 90
    while time.time() < end and not win.is_connected_a:
        pump(app, 0.2)
    print("A auto-connected:", win.is_connected_a, flush=True)

    win._on_refresh_search()
    pump(app, 20)

    win._on_device_connect(IT2705_RES, "IT2705")
    end = time.time() + 60
    while time.time() < end and not win.is_connected_b:
        pump(app, 0.2)
    print("B connected:", win.is_connected_b, flush=True)

    # Start 前确认 A session 本地存活
    a_ok = win.n6705c_a is not None and win.n6705c_a.instr is not None
    try:
        win.n6705c_a.instr.session
    except Exception as e:
        a_ok = False
        print("A session pre-start DEAD:", type(e).__name__, flush=True)
    print("A session alive pre-start:", a_ok, flush=True)

    win.ch_current_cbs_a[0].setChecked(True)
    win.ch_voltage_cbs_a[0].setChecked(True)
    if win.ch_current_cbs_b:
        win.ch_current_cbs_b[0].setChecked(True)
        win.ch_voltage_cbs_b[0].setChecked(True)
    win.monitor_time_s_edit.setText("1")
    win.sample_period_edit.setText("1000")
    win.min_period_cb.setChecked(False)

    try:
        win._start_recording()
        print("Start OK, thread:", win._record_thread is not None, flush=True)
    except Exception as e:
        print("!!! START CRASH:", type(e).__name__, e, flush=True)
        return 1

    for _ in range(300):
        pump(app, 0.1)
        if win._record_thread is None or not win._record_thread.isRunning():
            break
    pump(app, 0.5)

    keys = list(win.datalog_data.keys())
    curves = list(win.plot_curves.keys())
    non_empty = [k for k, v in win.datalog_data.items() if v["values"]]
    print("keys:", keys, flush=True)
    print("curves:", curves, flush=True)
    print("non_empty:", non_empty, flush=True)
    print("meas rows:", win.meas_table.rowCount(), flush=True)
    ok = ("A CH1 V" in curves) and ("A CH1 I" in curves)
    print("RESULT:", "ALL_OK" if ok else "FAILED", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
