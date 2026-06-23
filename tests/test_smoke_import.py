#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 0 安全网：遍历 import / py_compile 所有页面与模块，
确保重构搬运后不破导入链。

可独立运行（无 pytest 也能跑）：
    python tests/test_smoke_import.py
也可被 pytest 收集：
    pytest tests/test_smoke_import.py
"""

import os
import py_compile
import sys
import importlib
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_SCAN_DIRS = [
    "core",
    "ui/pages",
    "ui/modules",
    "ui/widgets",
    "ui/styles",
    "ui/ai",
    "instruments",
    "chips",
    "lib",
]

_SKIP_PATTERNS = (
    "__pycache__",
    os.sep + "mock" + os.sep,
    "test_",
    "_tmp",
)


def _iter_py_files(root_rel):
    root_abs = os.path.join(_ROOT, root_rel)
    if not os.path.isdir(root_abs):
        return
    for dirpath, dirnames, filenames in os.walk(root_abs):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__",)]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, _ROOT)
            if any(p in rel for p in _SKIP_PATTERNS):
                continue
            yield full, rel


def test_compile_all():
    errors = []
    for scan_dir in _SCAN_DIRS:
        for full, rel in _iter_py_files(scan_dir):
            try:
                py_compile.compile(full, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"[COMPILE FAIL] {rel}\n    {e}")
    assert not errors, "语法编译失败:\n" + "\n".join(errors)


def test_import_core_modules():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    errors = []
    core_targets = [
        "core.custom_test.document",
        "core.custom_test.executor",
        "core.custom_test.compiler",
        "core.custom_test.result_store",
        "core.ai.ai_service",
        "core.instruments.instrument_manager",
        "core.instruments.registry",
    ]
    for mod in core_targets:
        try:
            importlib.import_module(mod)
        except Exception:
            errors.append(f"[IMPORT FAIL] {mod}\n    {traceback.format_exc()}")
    assert not errors, "core 导入失败:\n" + "\n".join(errors)


def _run_standalone():
    failed = False
    for name, fn in [
        ("test_compile_all", test_compile_all),
        ("test_import_core_modules", test_import_core_modules),
    ]:
        try:
            fn()
            print(f"  [PASS] {name}")
        except AssertionError as e:
            print(f"  [FAIL] {name}")
            print(str(e)[:2000])
            failed = True
    return failed


if __name__ == "__main__":
    print("=== Smoke Import Test (standalone) ===")
    sys.exit(1 if _run_standalone() else 0)
