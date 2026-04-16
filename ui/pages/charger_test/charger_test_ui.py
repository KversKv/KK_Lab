#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget
)
from PySide6.QtGui import QFont
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

    def __init__(self, n6705c_top=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._setup_style()
        self._create_layout()
        self._init_ui_elements()

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

        self.config_traverse_ui = ConfigTraverseTestUI(n6705c_top=self._n6705c_top)
        self.tab_widget.addTab(self.config_traverse_ui, "Config Traverse Test")

        self.status_register_ui = StatusRegisterTestUI(n6705c_top=self._n6705c_top)
        self.tab_widget.addTab(self.status_register_ui, "Status Register Test")

        self.iterm_ui = ItermTestUI(n6705c_top=self._n6705c_top)
        self.tab_widget.addTab(self.iterm_ui, "Iterm Test")

        self.regulation_voltage_ui = RegulationVoltageTestUI(n6705c_top=self._n6705c_top)
        self.tab_widget.addTab(self.regulation_voltage_ui, "Regulation Voltage Test")

        main_layout.addWidget(self.tab_widget)

    def _init_ui_elements(self):
        pass

    def set_current_test(self, test_key):
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def _sync_from_top(self):
        for sub_ui in [
            self.config_traverse_ui, self.status_register_ui, self.iterm_ui,
            self.regulation_voltage_ui,
        ]:
            if hasattr(sub_ui, 'sync_n6705c_from_top'):
                sub_ui.sync_n6705c_from_top()
            elif hasattr(sub_ui, '_sync_from_top'):
                sub_ui._sync_from_top()

    def get_current_test(self):
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "config_traverse")

    def get_test_config(self, test_type):
        if test_type == "config_traverse":
            return self.config_traverse_ui.get_test_config()
        elif test_type == "status_register":
            return self.status_register_ui.get_test_config()
        elif test_type == "iterm":
            return self.iterm_ui.get_test_config()
        elif test_type == "regulation_voltage":
            return self.regulation_voltage_ui.get_test_config()
        return None

    def update_test_result(self, test_type, result):
        if test_type == "config_traverse":
            self.config_traverse_ui.update_test_result(result)
        elif test_type == "status_register":
            self.status_register_ui.update_test_result(result)
        elif test_type == "iterm":
            self.iterm_ui.update_test_result(result)
        elif test_type == "regulation_voltage":
            self.regulation_voltage_ui.update_test_result(result)

    def clear_all_results(self):
        self.config_traverse_ui.clear_results()
        self.status_register_ui.clear_results()
        self.iterm_ui.clear_results()
        self.regulation_voltage_ui.clear_results()

    def set_system_status(self, status, is_error=False):
        self.config_traverse_ui.set_system_status(status, is_error)
        self.status_register_ui.set_system_status(status, is_error)
        self.iterm_ui.set_system_status(status, is_error)
        self.regulation_voltage_ui.set_system_status(status, is_error)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ChargerTestUI()
    window.setWindowTitle("Charger Test")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())
