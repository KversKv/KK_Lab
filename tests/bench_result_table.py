"""ResultTable 性能基准：动态列结果表（贴合实际负载）。

真实场景：≤15 测试项 × 每项数十~数百行测量点 ≈ 数百~数千行。
基准取 2000 行（实际量级上沿）+ 20000 行压力参考。

    python tests/bench_result_table.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.models.result_model import LOG_KEY, STATUS_KEY
from ui.widgets.result_table import ResultTable

_app = QApplication.instance() or QApplication(sys.argv)

def _bench(n: int) -> tuple[float, float]:
    table = ResultTable()
    table.set_columns([(STATUS_KEY, "判定"), ("item", "测试项"),
                       ("vout_mv", "Vout (mV)"), ("vpp_mv", "Vpp (mV)")])
    rows = [
        {STATUS_KEY: "PASS" if i % 7 else "FAIL", "item": f"Item_{i % 50}",
         "vout_mv": 1800.0 + i * 0.001, "vpp_mv": 3.0 + i * 0.0001,
         LOG_KEY: f"item_{i % 50}"}
        for i in range(n)
    ]
    t0 = time.perf_counter()
    table.set_rows(rows)
    _app.processEvents()
    t_set = time.perf_counter() - t0
    t0 = time.perf_counter()
    table.view.sortByColumn(2, Qt.AscendingOrder)
    _app.processEvents()
    t_sort = time.perf_counter() - t0
    assert table.model.row_count() == n
    return t_set, t_sort


def main() -> int:
    t_set, t_sort = _bench(2000)
    print(f"实际量级 2000 行  : set {t_set*1000:.0f}ms / sort {t_sort*1000:.0f}ms")
    t_set2, t_sort2 = _bench(20000)
    print(f"压力参考 20000 行 : set {t_set2*1000:.0f}ms / sort {t_sort2*1000:.0f}ms")
    # 实际量级须流畅（<0.5s），压力量级仅记录不卡验收
    ok = t_set < 0.5 and t_sort < 0.5
    print(f"验收（2000 行 set/sort < 500ms）: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
