#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget
)
from PySide6.QtGui import QFont
from ui.widgets.config_memory import ConfigMemory
from ui.pages.charger_test.config_traverse_test import ConfigTraverseTestUI
from ui.pages.charger_test.status_register_test import StatusRegisterTestUI
from ui.pages.charger_test.iterm_test import ItermTestUI
from ui.pages.charger_test.regulation_voltage_ui import RegulationVoltageTestUI


class ChargerTestUI(QWidget):

    TEST_TAB_MAP = {
        "config_traverse": 0,
        "status_register": 1,
        "iterm": 2,
        "regulation_voltage": 3,
    }

    # 与 TEST_TAB_MAP 对齐的 tab 标签 / 子页属性名（声明顺序 = tab 顺序）
    _TAB_LABELS = {
        "config_traverse": "Config Traverse Test",
        "status_register": "Status Register Test",
        "iterm": "Iterm Test",
        "regulation_voltage": "Regulation Voltage Test",
    }
    _SUBPAGE_ATTRS = {
        "config_traverse": "config_traverse_ui",
        "status_register": "status_register_ui",
        "iterm": "iterm_ui",
        "regulation_voltage": "regulation_voltage_ui",
    }

    def __init__(self, n6705c_top=None, chamber_ui=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._chamber_ui = chamber_ui
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry
        # 子页懒加载：key → 实例（未构建为 None）；属性名兼容既有外部引用
        self._subpages: dict = {}
        for attr in self._SUBPAGE_ATTRS.values():
            setattr(self, attr, None)
        self._setup_style()
        self._create_layout()
        self._init_ui_elements()

        self._config_memory = ConfigMemory("charger_test/container", self)
        self._config_memory.bind("current_tab", self.tab_widget)
        self._config_memory.restore()
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
                background-color: #16181c;
            }
        """)

    def _create_layout(self):
        main_layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()

        # 占位 widget 先占住 tab 槽位；子页在首次选中时构建（_ensure_subpage），
        # 避免首次进入 Charger Test 一次性构建全部子页造成长时间卡顿
        for label in self._TAB_LABELS.values():
            self.tab_widget.addTab(QWidget(), label)

        main_layout.addWidget(self.tab_widget)

    def _build_subpage(self, key):
        """按 key 构建子页实例（构造参数与原即时构建保持一致）"""
        if key == "config_traverse":
            return ConfigTraverseTestUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        if key == "status_register":
            return StatusRegisterTestUI(
                n6705c_top=self._n6705c_top,
                chamber_ui=self._chamber_ui,
                instrument_manager=self._instrument_manager,
            )
        if key == "iterm":
            return ItermTestUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        if key == "regulation_voltage":
            return RegulationVoltageTestUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        raise KeyError(f"未知 Charger 子页: {key}")

    def _ensure_subpage(self, key):
        """懒加载入口：子页未构建则构建并替换占位 tab，随后同步仪器状态"""
        if key not in self.TEST_TAB_MAP:
            key = "config_traverse"
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
        elif hasattr(ui, '_sync_from_top'):
            ui._sync_from_top()
        return ui

    def _init_ui_elements(self):
        pass

    def set_current_test(self, test_key):
        self._ensure_subpage(test_key)
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def _sync_from_top(self):
        for sub_ui in self._subpages.values():
            if hasattr(sub_ui, 'sync_n6705c_from_top'):
                sub_ui.sync_n6705c_from_top()
            elif hasattr(sub_ui, '_sync_from_top'):
                sub_ui._sync_from_top()

    def get_current_test(self):
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "config_traverse")

    def get_test_config(self, test_type):
        """获取指定测试类型的配置（子页未构建时返回 None）"""
        ui = self._subpages.get(test_type)
        if ui is not None:
            return ui.get_test_config()
        return None

    def update_test_result(self, test_type, result):
        ui = self._subpages.get(test_type)
        if ui is not None:
            ui.update_test_result(result)

    def clear_all_results(self):
        for sub_ui in self._subpages.values():
            sub_ui.clear_results()

    def set_system_status(self, status, is_error=False):
        for sub_ui in self._subpages.values():
            sub_ui.set_system_status(status, is_error)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from ui.standalone import apply_window_icon, resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ChargerTestUI()
    window.setWindowTitle("Charger Test")
    apply_window_icon(window, "charger_test")
    resize_and_center_window(window)
    window.show()

    sys.exit(app.exec())
