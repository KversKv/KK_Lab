#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：独立 datalog 入口 + MockIT2705 全链路（连接→通道重建→软件采样录制）。

运行：python tests\\_debug_datalog_it2705.py
验证点：
1. standalone `_StandaloneDatalogWindow(instrument_manager=...)` 经 manager 连 MOCK::IT2705；
2. 槽位 A 型号显示 IT2705、Channel Config 重建为 8 通道；
3. 勾选 I1/V2 后 _start_recording 走软件采样路径（非 debug mock 数据），
   datalog_data 含 "A CH1 I" / "A CH2 V" 且时间戳递增。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import debug_config  # noqa: E402

debug_config.DEBUG_MOCK = True

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.instruments import InstrumentManager, InstrumentSpec  # noqa: E402
from ui.pages.power_analyzer.datalog.standalone import _StandaloneDatalogWindow  # noqa: E402

PASS = []


def _check(name, cond, detail=""):
    PASS.append((name, bool(cond)))
    print(f"[{'OK' if cond else 'FAIL'}] {name} {detail}")


def main():
    app = QApplication(sys.argv)
    manager = InstrumentManager()
    w = _StandaloneDatalogWindow(instrument_manager=manager)

    def step_connect():
        resources = {c.property("visa_resource") for c in w.device_cards}
        _check("mock IT2705 debug card exists", "MOCK::IT2705" in resources,
               f"cards={sorted(resources)}")
        manager.connect_async(InstrumentSpec(
            instrument_type="n6705c",
            role="power_analyzer",
            connection_kind="visa",
            slot="A",
            resource="MOCK::IT2705",
        ))
        QTimer.singleShot(1500, step_verify_connection)

    def step_verify_connection():
        slot = w.slot_frames["A"]
        _check("slot A connected", w.is_connected_a)
        _check("slot A model IT2705", slot.property("assigned_model") == "IT2705",
               f"model={slot.property('assigned_model')!r}")
        _check("8 current cbs", len(w.ch_current_cbs_a) == 8,
               f"n={len(w.ch_current_cbs_a)}")
        _check("8 voltage cbs", len(w.ch_voltage_cbs_a) == 8)
        inst = w.n6705c_a
        _check("instance is software-sampling (no read_mmem_data)",
               not callable(getattr(inst, "read_mmem_data", None)))
        # 勾选 I1 + V2
        w.ch_current_cbs_a[0].setChecked(True)
        w.ch_voltage_cbs_a[1].setChecked(True)
        w.monitor_time_s_edit.setText("2")
        w._start_recording()
        _check("recording started", w.is_recording)
        QTimer.singleShot(6000, step_verify_data)

    def step_verify_data():
        data = w.datalog_data
        print("DATA KEYS:", sorted(data.keys()))
        i1 = data.get("A CH1 I") or data.get("CH1 I")
        v2 = data.get("A CH2 V") or data.get("CH2 V")
        _check("has A CH1 I", i1 is not None and len(i1["values"]) > 0,
               f"points={len(i1['values']) if i1 else 0}")
        _check("has A CH2 V", v2 is not None and len(v2["values"]) > 0)
        if i1:
            t = i1["time"]
            _check("timestamps non-decreasing", all(a <= b for a, b in zip(t, t[1:])))
        _check("recording finished", not w.is_recording)
        w.close()
        manager.shutdown()
        app.quit()

    QTimer.singleShot(100, step_connect)
    QTimer.singleShot(15000, app.quit)
    app.exec()

    failed = [n for n, ok in PASS if not ok]
    print("RESULT:", "ALL_OK" if not failed else f"FAILED={failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
