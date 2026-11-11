#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：真实 App 流程（自动连 A + 手动连 B）复现 A session 被杀。

运行：python tests\\_debug_app_connect_kill.py
"""

import os
import sys
import time
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyvisa  # noqa: E402
import pyvisa.highlevel as _hl  # noqa: E402

_orig_rm_close = _hl.ResourceManager.close


def _traced_rm_close(self):
    backend = getattr(getattr(self, "visalib", None), "library_path", "?")
    print(f"\n!!! ResourceManager.close() backend={backend} !!!", flush=True)
    traceback.print_stack()
    return _orig_rm_close(self)


_hl.ResourceManager.close = _traced_rm_close

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.instruments import InstrumentManager, InstrumentSpec  # noqa: E402
from ui.pages.power_analyzer.datalog.standalone import _StandaloneDatalogWindow  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def probe_a(win, tag):
    inst = win.n6705c_a
    if inst is None or getattr(inst, "instr", None) is None:
        print(f"[{tag}] A not connected", flush=True)
        return
    try:
        print(f"[{tag}] A *IDN? ->", inst.instr.query("*IDN?").strip()[:40], flush=True)
    except Exception as e:
        print(f"[{tag}] A *IDN? FAIL: {type(e).__name__}", flush=True)


def main():
    app = QApplication(sys.argv)
    manager = InstrumentManager()
    win = _StandaloneDatalogWindow(instrument_manager=manager)
    print("window created, auto-connect kicked", flush=True)

    # 等自动连接 A 完成（真实 App 启动路径）
    end = time.time() + 90
    while time.time() < end and not win.is_connected_a:
        pump(app, 0.2)
    print("A auto-connected:", win.is_connected_a, flush=True)
    probe_a(win, "A after auto-connect")

    # 用户手动连接 B=IT2705（manager 路径，与卡片 Connect 一致）
    print("\n=== connect B (IT2705) via manager ===", flush=True)
    manager.connect_async(InstrumentSpec(
        instrument_type="n6705c", role="power_analyzer",
        connection_kind="visa", slot="B", resource=IT2705_RES,
    ))
    end = time.time() + 60
    while time.time() < end and not win.is_connected_b:
        pump(app, 0.2)
    print("B connected:", win.is_connected_b, flush=True)
    probe_a(win, "A after B connect")

    if win.is_connected_a and win.is_connected_b:
        # 继续走 Start 验证
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
            print("Start recording OK, thread:", win._record_thread is not None, flush=True)
        except Exception:
            print("!!! _start_recording CRASH:", flush=True)
            traceback.print_exc()
    print("\n=== done ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
