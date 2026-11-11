#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时 DEBUG：_DatalogWorker 真实路径（debug=False）跑 MockIT2705 软件采样。

运行：python tests\\_debug_datalog_worker_it2705.py
断言：
1. I1/V2 有数据（基础软件采样）；
2. 同通道 V/I 时间戳 100% 一致（P 通道配对前提），calc_power_for_ch 能算出 P；
3. 某通道测量抛错时录制不中断，其余通道数据完整（逐点容错）。
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from instruments.mock.mock_instruments import MockIT2705  # noqa: E402
from instruments.power.keysight.n6705c_datalog_process import calc_power_for_ch  # noqa: E402
from ui.pages.power_analyzer.datalog.workers import _DatalogWorker  # noqa: E402

PASS = []


def _check(name, cond, detail=""):
    PASS.append(bool(cond))
    print(f"[{'OK' if cond else 'FAIL'}] {name} {detail}")


def main():
    app = QApplication(sys.argv)
    inst = MockIT2705("MOCK::IT2705")
    # 通道 2 电压测量恒失败（模拟输出 OFF 返回 nan / 单次超时）
    inst.measure_voltage = lambda ch: (_ for _ in ()).throw(
        ValueError("IT2705: 无有效测量值 nan")
    ) if ch == 2 else MockIT2705.measure_voltage(inst, ch)

    worker = _DatalogWorker(
        [inst], [[1]], ["A"], "current", 20.0, 0.5,
        debug=False, voltage_channels_per_unit=[[1, 2]],
    )
    result = {}
    errors = []
    worker.data_ready.connect(lambda d: result.update(d))
    worker.error.connect(lambda e: errors.append(e))
    worker.run()  # 同步执行

    i1 = result.get("A CH1 I")
    v1 = result.get("A CH1 V")
    v2 = result.get("A CH2 V")
    _check("no worker error", not errors, f"errors={errors}")
    _check("I1 has data", i1 and len(i1["values"]) > 5,
           f"pts={len(i1['values']) if i1 else 0}")
    _check("V1 has data", v1 and len(v1["values"]) > 5)
    _check("V1/I1 timestamps identical", v1 and i1 and v1["time"] == i1["time"])
    calc_power_for_ch(result, 1, "A")
    _check("P1 computed", "A CH1 P" in result
           and len(result["A CH1 P"]["values"]) > 5)
    _check("V2 series exists (empty after failures)", v2 is not None
           and len(v2["values"]) == 0, f"pts={len(v2['values']) if v2 else None}")
    _check("failure counted", worker._sample_failures.get(("A", 2, "V"), 0) > 0,
           f"count={worker._sample_failures.get(('A', 2, 'V'), 0)}")

    print("RESULT:", "ALL_OK" if all(PASS) else "FAILED")
    return 0 if all(PASS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
