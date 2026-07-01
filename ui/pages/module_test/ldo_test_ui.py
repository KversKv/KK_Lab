#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LDO Module Test 子页面（绑定 LDO items 注册表 + LDOTestRunner）。"""
from __future__ import annotations

from core.module_test.ldo.items import LDO_ITEMS
from core.module_test.ldo.ldo_runner import LDOTestRunner
from ui.pages.module_test._base_subpage import ModuleTestSubPageBase


class LDOTestUI(ModuleTestSubPageBase):
    """LDO 模块测试页（page_key=module_test_ldo）。"""

    MODULE_TYPE = "ldo"
    PAGE_KEY = "module_test_ldo"
    ITEMS_REGISTRY = LDO_ITEMS
    RUNNER_CLS = LDOTestRunner
