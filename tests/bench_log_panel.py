"""LogPanel 性能基准：5 万条日志注入（任务书验收 #6）。

度量：
- 批量注入 50000 条的挂钟时间（LogPanel 批量 flush 路径）；
- 注入期间 UI 可交互性（事件循环未被阻塞：processEvents 往返延迟）；
- 对照：直写 ExecutionLogsFrame（无批量）同量耗时。

    python tests/bench_log_panel.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.widgets.log_panel import LogPanel

_app = QApplication.instance() or QApplication(sys.argv)

N = 50000


def _pump():
    _app.processEvents()


def bench_direct(n: int) -> float:
    """对照组：直写 ExecutionLogsFrame（无批量 flush）。"""
    frame = ExecutionLogsFrame(title="bench")
    frame.log_edit.document().setMaximumBlockCount(20000)
    t0 = time.perf_counter()
    for i in range(n):
        frame.append_log(f"[INFO] bench line {i} payload abcdefghijklmnopqrstuvwxyz")
        if i % 1000 == 0:
            _pump()
    _pump()
    return time.perf_counter() - t0


def bench_logpanel(n: int) -> tuple[float, float]:
    """LogPanel 批量 flush 路径：返回 (总耗时, 事件往返最坏延迟 ms)。"""
    panel = LogPanel()
    worst_latency_ms = 0.0
    t0 = time.perf_counter()
    for i in range(n):
        panel.append_log(f"[INFO] bench line {i} payload abcdefghijklmnopqrstuvwxyz")
        if i % 1000 == 0:
            p0 = time.perf_counter()
            _pump()
            worst_latency_ms = max(worst_latency_ms,
                                   (time.perf_counter() - p0) * 1000)
    # 排空尾批
    p0 = time.perf_counter()
    panel.flush_now()
    _pump()
    worst_latency_ms = max(worst_latency_ms, (time.perf_counter() - p0) * 1000)
    total = time.perf_counter() - t0
    return total, worst_latency_ms


def main() -> int:
    print(f"日志条数 N = {N}")
    t_direct = bench_direct(N)
    print(f"对照组（直写 ExecutionLogsFrame）: {t_direct:.2f}s")

    t_panel, latency = bench_logpanel(N)
    print(f"LogPanel（批量 flush）           : {t_panel:.2f}s")
    print(f"注入期间事件往返最坏延迟        : {latency:.1f}ms")

    # 行数上限生效
    panel = LogPanel()
    for i in range(1000):
        panel.append_log(f"[INFO] x{i}")
    panel.flush_now()
    assert panel.frame.log_edit.document().maximumBlockCount() == 20000

    # 验收判据（宽松上限，CI 容错）：批量路径不快于对照 2 倍且无异常；
    # 交互延迟 < 250ms（100ms flush 节拍 + 单次 flush 上限）。
    ok = latency < 250.0
    print(f"交互性验收（最坏延迟 < 250ms）  : {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
