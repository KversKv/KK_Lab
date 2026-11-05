"""pytest 自动用例分类；手工 GUI 脚本不进自动收集。"""
from __future__ import annotations

import re

import pytest

collect_ignore = [
    "test_config_memory_smoke.py",
    "test_nav_layout_smoke.py",
]

_UI_IMPORT = re.compile(r"^\s*(?:from|import)\s+ui(?:\.|\s|$)", re.MULTILINE)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        source = item.path.read_text(encoding="utf-8")
        if "PySide6" in source or _UI_IMPORT.search(source):
            item.add_marker(pytest.mark.qt)
        else:
            item.add_marker(pytest.mark.unit)
