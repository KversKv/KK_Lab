# -*- coding: utf-8 -*-
"""S1 注册表底座单测：PendingTaskRegistry + ScheduledTaskRegistry。

可独立运行（无 pytest 也能跑）：
    python tests/core/ai/test_task_registries.py
也可被 pytest 收集：
    pytest tests/core/ai/test_task_registries.py
"""
from __future__ import annotations

import os
import sys
import threading
from datetime import datetime, timedelta

_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.ai.pending_task_registry import (  # noqa: E402
    STATUS_DONE,
    STATUS_PENDING,
    PendingTaskRegistry,
)
from core.ai.scheduled_task_registry import ScheduledTaskRegistry  # noqa: E402


def test_pending_register_and_get():
    reg = PendingTaskRegistry()
    tid = reg.register("sess_a", "scan", title="扫描仪器")
    assert tid.startswith("T-")
    task = reg.get(tid)
    assert task is not None
    assert task.session_key == "sess_a"
    assert task.kind == "scan"
    assert task.status == STATUS_PENDING
    assert task.resumed is False


def test_pending_mark_done_and_resume_idempotent():
    reg = PendingTaskRegistry()
    tid = reg.register("sess_a", "scan")
    snap = reg.mark_done(tid, {"count": 3})
    assert snap is not None
    assert snap.status == STATUS_DONE
    assert snap.result == {"count": 3}
    # 幂等：首次 True，二次 False
    assert reg.mark_resumed(tid) is True
    assert reg.mark_resumed(tid) is False
    assert reg.get(tid).resumed is True


def test_pending_session_isolation():
    reg = PendingTaskRegistry()
    reg.register("sess_a", "scan")
    reg.register("sess_b", "scan")
    assert len(reg.list(session_key="sess_a")) == 1
    assert len(reg.list(session_key="sess_b")) == 1
    assert len(reg.list()) == 2


def test_pending_unconsumed_done():
    reg = PendingTaskRegistry()
    t1 = reg.register("sess_a", "scan")
    t2 = reg.register("sess_a", "seq")
    reg.mark_done(t1, {"ok": True})
    reg.mark_done(t2, {"ok": True})
    reg.mark_resumed(t1)
    unconsumed = reg.list_unconsumed_done("sess_a")
    assert len(unconsumed) == 1
    assert unconsumed[0]["task_id"] == t2


def test_pending_fifo_eviction():
    reg = PendingTaskRegistry(max_tasks=5)
    ids = [reg.register("s", "k") for _ in range(8)]
    remaining = {t["task_id"] for t in reg.list()}
    assert len(remaining) == 5
    # 最旧 3 个被淘汰
    assert ids[0] not in remaining
    assert ids[-1] in remaining


def test_pending_thread_safe():
    reg = PendingTaskRegistry(max_tasks=1000)

    def worker():
        for _ in range(50):
            tid = reg.register("s", "k")
            reg.mark_done(tid, {"v": 1})

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(reg.list()) == 400


def test_scheduled_register_delay():
    reg = ScheduledTaskRegistry()
    tid, delay, err = reg.register(
        "sess_a",
        {"type": "delay", "seconds": 1800},
        {"name": "set_instrument_output", "arguments": {"channel": 1}},
    )
    assert err == ""
    assert tid.startswith("sched_")
    assert 1799 <= delay <= 1800
    task = reg.get(tid)
    assert task.status == STATUS_PENDING
    assert task.action["name"] == "set_instrument_output"


def test_scheduled_register_at():
    reg = ScheduledTaskRegistry()
    future = (datetime.now() + timedelta(seconds=60)).isoformat()
    tid, delay, err = reg.register(
        "s", {"type": "at", "iso": future}, {"name": "x"}
    )
    assert err == ""
    assert 55 <= delay <= 61


def test_scheduled_register_invalid():
    reg = ScheduledTaskRegistry()
    tid, delay, err = reg.register("s", {"type": "delay"}, {"name": "x"})
    assert tid is None and err
    tid, delay, err = reg.register("s", {"type": "bogus"}, {"name": "x"})
    assert tid is None and err


def test_scheduled_cancel():
    reg = ScheduledTaskRegistry()
    tid, _, _ = reg.register("s", {"type": "delay", "seconds": 10}, {"name": "x"})
    ok, msg = reg.cancel(tid)
    assert ok
    assert reg.get(tid).status == "cancelled"
    # 重复取消失败
    ok2, _ = reg.cancel(tid)
    assert ok2 is False


def test_scheduled_running_done():
    reg = ScheduledTaskRegistry()
    tid, _, _ = reg.register("s", {"type": "delay", "seconds": 10}, {"name": "x"})
    assert reg.mark_running(tid) is not None
    # 非 pending 不能再 running
    assert reg.mark_running(tid) is None
    snap = reg.mark_done(tid, {"status": "executed"})
    assert snap.status == "done"


def test_scheduled_session_isolation():
    reg = ScheduledTaskRegistry()
    reg.register("a", {"type": "delay", "seconds": 1}, {"name": "x"})
    reg.register("b", {"type": "delay", "seconds": 1}, {"name": "x"})
    assert len(reg.list(session_key="a")) == 1
    assert len(reg.list_pending(session_key="b")) == 1


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
