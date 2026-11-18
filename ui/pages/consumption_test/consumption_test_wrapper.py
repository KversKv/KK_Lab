#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget
)
from PySide6.QtGui import QFont
from ui.pages.consumption_test.consumption_test import ConsumptionTestUI
from ui.pages.consumption_test.high_low_temp_test_ui import HighLowTempConsumptionTestUI


class ConsumptionTestWrapper(QWidget):

    TEST_TAB_MAP = {
        "auto_test": 0,
        "high_low_temp": 1,
    }

    # 与 TEST_TAB_MAP 对齐的 tab 标签 / 子页属性名（声明顺序 = tab 顺序）
    _TAB_LABELS = {
        "auto_test": "Auto Test",
        "high_low_temp": "High-Low Temperature Test",
    }
    _SUBPAGE_ATTRS = {
        "auto_test": "auto_test_ui",
        "high_low_temp": "high_low_temp_ui",
    }

    def __init__(self, n6705c_top=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry
        # 子页懒加载：key → 实例（未构建为 None）；属性名兼容既有外部引用
        self._subpages: dict = {}
        for attr in self._SUBPAGE_ATTRS.values():
            setattr(self, attr, None)
        self._setup_style()
        self._create_layout()
        # 只构建当前选中的子页，其余首次切到时再构建
        self._ensure_subpage(self.get_current_test())

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)
        self.setStyleSheet("""
            QWidget {
                background-color: #020618;
                color: #c8c8c8;
                border: none;
            }
            QTabWidget::pane {
                border: none;
                background-color: #020618;
            }
        """)

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()

        # 占位 widget 先占住 tab 槽位；子页在首次选中时构建（_ensure_subpage），
        # 避免首次进入 Consumption Test 一次性构建全部子页造成长时间卡顿
        for label in self._TAB_LABELS.values():
            self.tab_widget.addTab(QWidget(), label)

        main_layout.addWidget(self.tab_widget)

    def _build_subpage(self, key):
        """按 key 构建子页实例（构造参数与原即时构建保持一致）"""
        if key == "auto_test":
            return ConsumptionTestUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        if key == "high_low_temp":
            return HighLowTempConsumptionTestUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
            )
        raise KeyError(f"未知 Consumption 子页: {key}")

    def _ensure_subpage(self, key):
        """懒加载入口：子页未构建则构建并替换占位 tab，随后同步仪器状态"""
        if key not in self.TEST_TAB_MAP:
            key = "auto_test"
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

        if hasattr(ui, 'sync_n6705c_from_top'):
            ui.sync_n6705c_from_top()
        return ui

    def set_current_test(self, test_key):
        self._ensure_subpage(test_key)
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def get_current_test(self):
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "auto_test")

    def sync_n6705c_from_top(self):
        for sub_ui in self._subpages.values():
            if hasattr(sub_ui, 'sync_n6705c_from_top'):
                sub_ui.sync_n6705c_from_top()

    def _sync_from_top(self):
        self.sync_n6705c_from_top()

    def _current_ai_subpage(self):
        """返回当前 Tab 的子页实例（供 AI 枢纽契约路由用）。"""
        return self.tab_widget.currentWidget() if self.tab_widget else None

    @property
    def logs_frame(self):
        """logs_frame 透传：把当前 Tab 子页的 execution_logs 暴露给 AI 枢纽。

        枢纽 _get_ai_execution_logs 经 page.logs_frame._all_logs 读取日志；
        wrapper 自身不持 logs 控件，按当前 Tab 下钻到子页。
        """
        sub = self._current_ai_subpage()
        if sub is None:
            return None
        return getattr(sub, "logs_frame", None) or getattr(sub, "execution_logs", None)

    def append_log(self, message):
        """append_log 透传：让 AI 枢纽 _ai_ui_invoke 的 [AI] 日志回填能落到子页日志区。

        枢纽 _current_active_page() 返回 wrapper（不下钻），它经 getattr(page,
        'append_log', None) 找不到时静默失败。这里透传到当前 Tab 子页，
        保证 [AI] 触发 XXX 日志条目能正确出现在 ExecutionLogsFrame。
        """
        sub = self._current_ai_subpage()
        if sub is None:
            return
        appender = getattr(sub, "append_log", None)
        if callable(appender):
            appender(message)


def main():
    from ui.standalone import run_standalone_widget

    return run_standalone_widget(
        lambda: ConsumptionTestWrapper(),
        "Consumption Test",
        icon_name="consumption_test",
    )


if __name__ == "__main__":
    raise SystemExit(main())
