#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：全动作真机流程 + 每秒探活 A + rm.close 追踪，抓杀 A 的现行犯。

动作序列（模拟真实用户）：
1. 启动（自动连 A）
2. 点 Scan（discover_n6705c_details）
3. 手动连 B（_on_device_connect 真实卡片入口）
4. Start 录制
全程每 0.5s 探活 A 的 *IDN?，死时打印时刻；任何 rm.close() 打调用栈。

运行：python tests\\_debug_app_full_flow_kill.py
"""

import os
import sys
import threading
import time
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyvisa  # noqa: E402
import pyvisa.highlevel as _hl  # noqa: E402

_orig_rm_close = _hl.ResourceManager.close


def _traced_rm_close(self):
    backend = getattr(getattr(self, "visalib", None), "library_path", "?")
    print(f"\n!!! ResourceManager.close() backend={backend} t={time.time():.1f} !!!", flush=True)
    traceback.print_stack()
    return _orig_rm_close(self)


_hl.ResourceManager.close = _traced_rm_close

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.instruments import InstrumentManager  # noqa: E402
from ui.pages.power_analyzer.datalog.standalone import _StandaloneDatalogWindow  # noqa: E402

N6705C_RES = "TCPIP0::10.31.71.98::hislip0::INSTR"
IT2705_RES = "TCPIP0::10.31.71.168::30000::SOCKET"

_t0 = time.time()
_alive = True
_last_ok = None


def probe_loop(win):
    global _last_ok
    while _alive:
        inst = win.n6705c_a
        if inst is not None and getattr(inst, "instr", None) is not None:
            try:
                inst.instr.query("*IDN?")
                ok = True
            except Exception:
                ok = False
            if ok != _last_ok:
                print(f"[t={time.time()-_t0:.1f}] A session -> {'ALIVE' if ok else 'DEAD'}", flush=True)
                _last_ok = ok
        time.sleep(0.5)


def pump(app, seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents()
        time.sleep(0.02)


def main():
    global _alive
    app = QApplication(sys.argv)
    manager = InstrumentManager()
    win = _StandaloneDatalogWindow(instrument_manager=manager)
    print("window created", flush=True)

    th = threading.Thread(target=probe_loop, args=(win,), daemon=True)
    th.start()

    # 1. 等 A 自动连接
    end = time.time() + 90
    while time.time() < end and not win.is_connected_a:
        pump(app, 0.2)
    print(f"[t={time.time()-_t0:.1f}] A connected: {win.is_connected_a}", flush=True)

    # 2. 点 Scan（与仪器面板扫描按钮同路径，后台线程）
    print(f"[t={time.time()-_t0:.1f}] scan start", flush=True)
    win._on_refresh_search()
    pump(app, 25)
    print(f"[t={time.time()-_t0:.1f}] scan done wait over", flush=True)

    # 3. 手动连 B（真实卡片入口）
    print(f"[t={time.time()-_t0:.1f}] connect B", flush=True)
    win._on_device_connect(IT2705_RES, "IT2705")
    end = time.time() + 60
    while time.time() < end and not win.is_connected_b:
        pump(app, 0.2)
    print(f"[t={time.time()-_t0:.1f}] B connected: {win.is_connected_b}", flush=True)

    # 4. 停留片刻（模拟用户设置通道）
    pump(app, 5)

    # 5. Start
    if win.is_connected_a and win.is_connected_b:
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
            print(f"[t={time.time()-_t0:.1f}] Start OK, thread: {win._record_thread is not None}", flush=True)
            for _ in range(100):
                pump(app, 0.1)
                if win._record_thread is None or not win._record_thread.isRunning():
                    break
            print("record keys:", list(win.datalog_data.keys()), flush=True)
            print("curves:", list(win.plot_curves.keys()), flush=True)
        except Exception:
            print(f"[t={time.time()-_t0:.1f}] !!! START CRASH", flush=True)
            traceback.print_exc()

    _alive = False
    print("=== done ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
