#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 顶层容器（隐藏 tab 的 QTabWidget，切换 LDO/DCDC）。

规划 §5.1：仿 PMUTestUI，构造参数透传给两个子页；暴露 set_current_test /
get_current_test / _sync_from_top 供 nav_controller 与枢纽调用。
"""
from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget
from log_config import get_logger

from ui.pages.module_test.dcdc_test_ui import DCDCTestUI
from ui.pages.module_test.ldo_test_ui import LDOTestUI

logger = get_logger(__name__)


class ModuleTestUI(QWidget):
    """Module Test 顶层容器。"""

    TEST_TAB_MAP = {"ldo": 0, "dcdc": 1}

    def __init__(self, n6705c_top=None, mso64b_top=None, chamber_ui=None,
                 instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._mso64b_top = mso64b_top
        self._chamber_ui = chamber_ui
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry

        self._setup_style()
        self._create_layout()

    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setStyleSheet("""
            QWidget { background-color: #020618; color: #c8c8c8; border: none; }
            QTabWidget::pane { border: none; background-color: #16181c; }
        """)

    def _create_layout(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()

        self.ldo_test_ui = LDOTestUI(
            n6705c_top=self._n6705c_top,
            mso64b_top=self._mso64b_top,
            chamber_ui=self._chamber_ui,
            instrument_manager=self._instrument_manager,
            ui_action_registry=self._ui_action_registry,
        )
        self.tab_widget.addTab(self.ldo_test_ui, "LDO")

        self.dcdc_test_ui = DCDCTestUI(
            n6705c_top=self._n6705c_top,
            mso64b_top=self._mso64b_top,
            chamber_ui=self._chamber_ui,
            instrument_manager=self._instrument_manager,
            ui_action_registry=self._ui_action_registry,
        )
        self.tab_widget.addTab(self.dcdc_test_ui, "DCDC")

        layout.addWidget(self.tab_widget)

    def set_current_test(self, test_key: str):
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def get_current_test(self) -> str:
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "ldo")

    def _sync_from_top(self):
        for sub_ui in (self.ldo_test_ui, self.dcdc_test_ui):
            if hasattr(sub_ui, "sync_n6705c_from_top"):
                sub_ui.sync_n6705c_from_top()
            if hasattr(sub_ui, "sync_oscilloscope_from_top"):
                sub_ui.sync_oscilloscope_from_top()

    def get_test_config(self, test_type: str):
        sub = self.ldo_test_ui if test_type == "ldo" else self.dcdc_test_ui
        return sub.get_test_config()

    def update_test_result(self, test_type: str, result):
        sub = self.ldo_test_ui if test_type == "ldo" else self.dcdc_test_ui
        sub.update_test_result(result)

    def clear_all_results(self):
        self.ldo_test_ui.clear_results()
        self.dcdc_test_ui.clear_results()

    def set_system_status(self, status: str, is_error: bool = False):
        self.ldo_test_ui.set_system_status(status, is_error)
        self.dcdc_test_ui.set_system_status(status, is_error)
