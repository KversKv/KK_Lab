#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VminHunter Tab 容器

子页：
- Vmin Hunt：电压遍历探底（vmin_hunter_ui.VminHunterUI）
- Single Vmin Test：在找到的 Vmin 电压点单次执行测试序列做流程确认
  （vmin_single_test_ui.VminSingleTestUI）

Tab 切换由侧边栏 VminHunter 悬停子菜单驱动（同 pmu_test / charger_test），
容器内 tabBar 隐藏。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtGui import QFont

from ui.pages.vmin_hunter.vmin_hunter_ui import VminHunterUI
from ui.pages.vmin_hunter.vmin_single_test_ui import VminSingleTestUI


class VminHunterContainerUI(QWidget):

    TEST_TAB_MAP = {
        "hunt": 0,
        "single_test": 1,
    }

    def __init__(self, n6705c_top=None, instrument_manager=None, parent=None):
        super().__init__(parent)
        self._n6705c_top = n6705c_top
        self._instrument_manager = instrument_manager
        self.setFont(QFont("Segoe UI", 9))
        self._create_layout()

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()

        self.hunt_ui = VminHunterUI(
            n6705c_top=self._n6705c_top,
            instrument_manager=self._instrument_manager,
        )
        self.tab_widget.addTab(self.hunt_ui, "Vmin Hunt")

        self.single_test_ui = VminSingleTestUI(
            n6705c_top=self._n6705c_top,
            instrument_manager=self._instrument_manager,
        )
        self.tab_widget.addTab(self.single_test_ui, "Single Vmin Test")

        main_layout.addWidget(self.tab_widget)

    def set_current_test(self, test_key):
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def get_current_test(self):
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "hunt")

    def sync_n6705c_from_top(self):
        for sub_ui in (self.hunt_ui, self.single_test_ui):
            sub_ui.sync_n6705c_from_top()
