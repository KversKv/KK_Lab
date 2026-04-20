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

    def __init__(self, n6705c_top=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._setup_style()
        self._create_layout()

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

        self.auto_test_ui = ConsumptionTestUI(n6705c_top=self._n6705c_top)
        self.tab_widget.addTab(self.auto_test_ui, "Auto Test")

        self.high_low_temp_ui = HighLowTempConsumptionTestUI(n6705c_top=self._n6705c_top)
        self.tab_widget.addTab(self.high_low_temp_ui, "High-Low Temperature Test")

        main_layout.addWidget(self.tab_widget)

    def set_current_test(self, test_key):
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def get_current_test(self):
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "auto_test")

    def sync_n6705c_from_top(self):
        if hasattr(self.auto_test_ui, 'sync_n6705c_from_top'):
            self.auto_test_ui.sync_n6705c_from_top()
        if hasattr(self.high_low_temp_ui, 'sync_n6705c_from_top'):
            self.high_low_temp_ui.sync_n6705c_from_top()

    def _sync_from_top(self):
        self.sync_n6705c_from_top()
