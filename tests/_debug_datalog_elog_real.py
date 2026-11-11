#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：_DatalogWorker + 真机 IT2705 ELOG 端到端验证。

运行：python tests\\_debug_datalog_elog_real.py
断言（20us × 1.0s，CH1 V+I）：
1. V/I 点数 ≈ 时长/20us（允许启动延迟损耗）；
2. 时间轴中位步长 == 20us；
3. V/I 时间戳一致（P 可配对）；
4. worker 无 error。
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from instruments.factory import create_power_analyzer  # noqa: E402
from ui.pages.power_analyzer.datalog.workers import _DatalogWorker  # noqa: E402

RESOURCE = os.environ.get(
    "KK_LAB_IT2705_RESOURCE", "TCPIP0::10.31.71.168::30000::SOCKET"
)
PASS = []


def _check(name, cond, detail=""):
    PASS.append(bool(cond))
    print(f"[{'OK' if cond else 'FAIL'}] {name} {detail}")


def main():
    app = QApplication(sys.argv)
    inst = create_power_analyzer(RESOURCE, analyzer_type="auto")
    print(f"connected: {type(inst).__name__}, modules={inst.channel_module_models}")
    try:
        duration = 1.0
        period_us = 20.0
        worker = _DatalogWorker(
            [inst], [[1]], ["A"], "current", period_us, duration,
            debug=False, voltage_channels_per_unit=[[1]],
        )
        result = {}
        errors = []
        worker.data_ready.connect(lambda d: result.update(d))
        worker.error.connect(lambda e: errors.append(e))
        worker.run()

        v1 = result.get("A CH1 V")
        i1 = result.get("A CH1 I")
        expect = duration / (period_us / 1e6)
        _check("no worker error", not errors, f"errors={errors}")
        _check("V1 has data", bool(v1 and v1["values"]),
               f"pts={len(v1['values']) if v1 else 0}, expect~{int(expect)}")
        _check("I1 has data", bool(i1 and i1["values"]),
               f"pts={len(i1['values']) if i1 else 0}")
        if v1 and i1:
            ratio = len(v1["values"]) / expect
            _check("V1 count within 30% of expect", ratio > 0.7,
                   f"ratio={ratio:.2f}")
            dts = [b - a for a, b in zip(v1["time"][:2000], v1["time"][1:2001])]
            med = statistics.median(dts) if dts else 0
            _check("median dt == 20us", abs(med - 20e-6) < 1e-9,
                   f"median={med * 1e6:.3f}us")
            _check("V/I timestamps identical", v1["time"] == i1["time"])
            print(f"  V1 head: {[round(x, 4) for x in v1['values'][:5]]} mV")
            print(f"  I1 head: {[round(x, 4) for x in i1['values'][:5]]} mA")
            print(f"  t range: {v1['time'][0]:.6f} .. {v1['time'][-1]:.6f} s")
        print("sample failures:", dict(worker._sample_failures))
    finally:
        try:
            inst.stop_elog()
        except Exception:
            pass
        inst.disconnect()
    print("RESULT:", "ALL_OK" if all(PASS) else "FAILED")
    return 0 if all(PASS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
