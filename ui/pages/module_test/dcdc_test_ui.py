#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DCDC Module Test 子页面（绑定 DCDC items 注册表 + DCDCTestRunner）。"""
from __future__ import annotations

from core.module_test.dcdc.items import DCDC_ITEMS
from core.module_test.dcdc.dcdc_runner import DCDCTestRunner
from ui.pages.module_test._base_subpage import ModuleTestSubPageBase


class DCDCTestUI(ModuleTestSubPageBase):
    """DCDC 模块测试页（page_key=module_test_dcdc）。"""

    MODULE_TYPE = "dcdc"
    PAGE_KEY = "module_test_dcdc"
    ITEMS_REGISTRY = DCDC_ITEMS
    RUNNER_CLS = DCDCTestRunner
