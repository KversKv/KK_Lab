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

from ui.widgets.config_memory import ConfigMemory

from ui.pages.vmin_hunter.vmin_hunter_ui import VminHunterUI
from ui.pages.vmin_hunter.vmin_single_test_ui import VminSingleTestUI


class VminHunterContainerUI(QWidget):

    TEST_TAB_MAP = {
        "hunt": 0,
        "single_test": 1,
    }

    # 与 TEST_TAB_MAP 对齐的 tab 标签 / 子页属性名（声明顺序 = tab 顺序）
    _TAB_LABELS = {
        "hunt": "Vmin Hunt",
        "single_test": "Single Vmin Test",
    }
    _SUBPAGE_ATTRS = {
        "hunt": "hunt_ui",
        "single_test": "single_test_ui",
    }

    def __init__(self, n6705c_top=None, instrument_manager=None, parent=None):
        super().__init__(parent)
        self._n6705c_top = n6705c_top
        self._instrument_manager = instrument_manager
        # 子页懒加载：key → 实例（未构建为 None）；属性名兼容既有外部引用
        self._subpages: dict = {}
        for attr in self._SUBPAGE_ATTRS.values():
            setattr(self, attr, None)
        self.setFont(QFont("Segoe UI", 9))
        self._create_layout()

        self._config_memory = ConfigMemory("vmin_hunter/container", self)
        self._config_memory.bind("current_tab", self.tab_widget)
        self._config_memory.restore()
        # 只构建当前选中的子页，其余首次切到时再构建
        self._ensure_subpage(self.get_current_test())

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()

        # 占位 widget 先占住 tab 槽位；子页在首次选中时构建（_ensure_subpage），
        # 避免首次进入 VminHunter 一次性构建全部子页造成长时间卡顿
        for label in self._TAB_LABELS.values():
            self.tab_widget.addTab(QWidget(), label)

        main_layout.addWidget(self.tab_widget)

    def _build_subpage(self, key):
        """按 key 构建子页实例（构造参数与原即时构建保持一致）"""
        if key == "hunt":
            return VminHunterUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
            )
        if key == "single_test":
            return VminSingleTestUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
            )
        raise KeyError(f"未知 VminHunter 子页: {key}")

    def _ensure_subpage(self, key):
        """懒加载入口：子页未构建则构建并替换占位 tab，随后同步仪器状态"""
        if key not in self.TEST_TAB_MAP:
            key = "hunt"
        ui = self._subpages.get(key)
        if ui is not None:
            return ui
        ui = self._build_subpage(key)
        self._subpages[key] = ui
        setattr(self, self._SUBPAGE_ATTRS[key], ui)

        index = self.TEST_TAB_MAP[key]
        current = self.tab_widget.currentIndex()
        self.tab_widget.removeTab(index)
        self.tab_widget.insertTab(index, ui, self._TAB_LABELS[key])
        self.tab_widget.setCurrentIndex(current)

        ui.sync_n6705c_from_top()
        return ui

    def set_current_test(self, test_key):
        self._ensure_subpage(test_key)
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def get_current_test(self):
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "hunt")

    def sync_n6705c_from_top(self):
        for sub_ui in self._subpages.values():
            sub_ui.sync_n6705c_from_top()
