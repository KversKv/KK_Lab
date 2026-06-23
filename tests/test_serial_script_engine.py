#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 4-8 单元测试：core.serial_script.script_engine 纯逻辑。

可独立运行：
    python tests/test_serial_script_engine.py
也可被 pytest 收集：
    pytest tests/test_serial_script_engine.py
"""

import os
import sys
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.serial_script.script_engine import (
    decide_loop_next,
    match_wait_keyword,
    ordered_steps,
)


def test_ordered_steps_filters_and_sorts():
    script = {
        "steps": [
            {"cmd": "c", "priority": 0},
            {"cmd": "b", "priority": 2},
            {"cmd": "a", "priority": 1},
            {"cmd": "d", "priority": 3},
        ]
    }
    result = ordered_steps(script)
    assert [s["cmd"] for s in result] == ["a", "b", "d"], result


def test_ordered_steps_empty():
    assert ordered_steps(None) == []
    assert ordered_steps({}) == []
    assert ordered_steps({"steps": []}) == []


def test_match_wait_keyword_hit():
    matched, buf = match_wait_keyword("hello OK world", "OK")
    assert matched is True
    assert buf == "hello OK world"


def test_match_wait_keyword_miss():
    matched, buf = match_wait_keyword("hello world", "OK")
    assert matched is False
    assert buf == "hello world"


def test_match_wait_keyword_empty_keyword_never_matches():
    matched, _ = match_wait_keyword("anything", "")
    assert matched is False


def test_match_wait_keyword_truncates_long_buffer():
    long_buf = "x" * 5000
    matched, buf = match_wait_keyword(long_buf, "OK")
    assert matched is False
    assert len(buf) == 4096
    assert buf == "x" * 4096


def test_decide_loop_next_exec_when_step_in_range():
    assert decide_loop_next(0, 3, 2, False) == ("exec", 0, 2)
    assert decide_loop_next(2, 3, 2, False) == ("exec", 2, 2)


def test_decide_loop_next_finite_loops_exact_count():
    assert decide_loop_next(3, 3, 1, False) == ("done", 0, 0)
    assert decide_loop_next(3, 3, 2, False) == ("loop_restart", 0, 1)
    assert decide_loop_next(3, 3, 3, False) == ("loop_restart", 0, 2)


def test_decide_loop_next_infinite_never_exhausts():
    assert decide_loop_next(3, 3, 999, True) == ("loop_restart", 0, 999)
    assert decide_loop_next(3, 3, 1, True) == ("loop_restart", 0, 1)


def _run_standalone():
    failed = False
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  [PASS] {name}")
            except Exception:
                print(f"  [FAIL] {name}")
                print(traceback.format_exc()[:2000])
                failed = True
    return failed


if __name__ == "__main__":
    print("=== Serial Script Engine Unit Test (standalone) ===")
    sys.exit(1 if _run_standalone() else 0)
