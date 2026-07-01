"""LDO Module Test Runner（绑定 LDO items 注册表）。"""
from __future__ import annotations

from core.module_test._runner_base import ModuleTestRunner
from core.module_test.ldo.items import LDO_ITEMS


class LDOTestRunner(ModuleTestRunner):
    """LDO 模块测试编排线程。"""

    def __init__(self, *, config, n6705c, scope=None, chamber=None, out_dir="", parent=None):
        super().__init__(
            module_type="ldo",
            items_registry=LDO_ITEMS,
            config=config,
            n6705c=n6705c,
            scope=scope,
            chamber=chamber,
            out_dir=out_dir,
            parent=parent,
        )
