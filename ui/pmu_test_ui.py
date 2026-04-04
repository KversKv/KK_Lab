#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU测试主UI组件 - 整合DCDC Efficiency、Output Voltage、Threshold、OSCP子页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.pmu_dcdc_efficiency import PMUDCDCEfficiencyUI
from ui.pmu_output_voltage import PMUOutputVoltageUI
from ui.pmu_threshold import PMUThresholdUI
from ui.pmu_isGain_ui import PMUIsGainUI
from ui.pmu_oscp_ui import PMUOSCPUI
from ui.gpadc_test_ui import GPADCTestUI
from ui.clk_test_ui import CLKTestUI


class PMUTestUI(QWidget):
    """PMU测试主UI组件"""

    TEST_TAB_MAP = {
        "dcdc_efficiency": 0,
        "output_voltage": 1,
        "threshold": 2,
        "is_gain": 3,
        "oscp": 4,
        "gpadc_test": 5,
        "clk_test": 6,
    }

    def __init__(self):
        super().__init__()
        self._setup_style()
        self._create_layout()
        self._init_ui_elements()

    def _setup_style(self):
        """设置界面样式"""
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        self.setStyleSheet("""
            QWidget {
                background-color: #020618;
                color: #c8c8c8;
                border: none;
            }
            QGroupBox {
                border: 1px solid #333;
                border-radius: 6px;
                margin-top: 6px;
                background-color: #020618;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #c8c8c8;
            }
            QPushButton {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QPushButton:hover {
                background-color: #3a3d43;
            }
            QPushButton:pressed {
                background-color: #2a2d32;
            }
            QPushButton:disabled {
                background-color: #2a2d32;
                color: #666;
            }
            QComboBox {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 20px 4px 8px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QComboBox QAbstractItemView {
                background-color: #32353a;
                color: #c8c8c8;
                border: 1px solid #555;
                selection-background-color: #4a4d52;
                outline: 0px;
            }
            QComboBox QAbstractItemView::item {
                background-color: #32353a;
                color: #c8c8c8;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #4a4d52;
            }
            QComboBox QFrame {
                background-color: #32353a;
                border: 1px solid #555;
            }
            QLineEdit {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QLabel {
                color: #c8c8c8;
            }
            QTabWidget::pane {
                border: none;
                background-color: #16181c;
            }
        """)

    def _create_layout(self):
        """创建布局"""
        main_layout = QVBoxLayout(self)

        # 仍然使用 QTabWidget 作为页面切换容器，但隐藏顶部 tab
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()

        # 创建DCDC Efficiency页面
        self.dcdc_efficiency_ui = PMUDCDCEfficiencyUI()
        self.tab_widget.addTab(self.dcdc_efficiency_ui, "DCDC Efficiency")

        # 创建Output Voltage页面
        self.output_voltage_ui = PMUOutputVoltageUI()
        self.tab_widget.addTab(self.output_voltage_ui, "Output Voltage")

        # 创建Threshold页面
        self.threshold_ui = PMUThresholdUI()
        self.tab_widget.addTab(self.threshold_ui, "Threshold")

        self.is_gain_ui = PMUIsGainUI()
        self.tab_widget.addTab(self.is_gain_ui, "Is_gain")

        self.oscp_ui = PMUOSCPUI()
        self.tab_widget.addTab(self.oscp_ui, "OSCP")
        
        # 创建GPADC测试页面
        self.gpadc_test_ui = GPADCTestUI()
        self.tab_widget.addTab(self.gpadc_test_ui, "GPADC Test")

        # 创建CLK测试页面
        self.clk_test_ui = CLKTestUI()
        self.tab_widget.addTab(self.clk_test_ui, "CLK Test")

        main_layout.addWidget(self.tab_widget)


    def _init_ui_elements(self):
        """初始化UI元素"""
        self._connect_child_signals()

    def _connect_child_signals(self):
        """连接子页面的信号"""
        self.dcdc_efficiency_ui.start_test_btn.clicked.connect(
            lambda: self._on_test_started("dcdc_efficiency"))
        self.dcdc_efficiency_ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped("dcdc_efficiency"))

        self.output_voltage_ui.start_test_btn.clicked.connect(
            lambda: self._on_test_started("output_voltage"))
        self.output_voltage_ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped("output_voltage"))

        self.threshold_ui.start_test_btn.clicked.connect(
            lambda: self._on_test_started("threshold"))
        self.threshold_ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped("threshold"))

        self.is_gain_ui.start_test_btn.clicked.connect(
            lambda: self._on_test_started("is_gain"))
        self.is_gain_ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped("is_gain"))

        self.oscp_ui.start_test_btn.clicked.connect(
            lambda: self._on_test_started("oscp"))
        self.oscp_ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped("oscp"))
        
        self.gpadc_test_ui.start_test_btn.clicked.connect(
            lambda: self._on_test_started("gpadc_test"))
        self.gpadc_test_ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped("gpadc_test"))

        self.clk_test_ui.start_test_btn.clicked.connect(
            lambda: self._on_test_started("clk_test"))
        self.clk_test_ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped("clk_test"))

    def set_current_test(self, test_key):
        """切换当前测试页"""
        index = self.TEST_TAB_MAP.get(test_key, 0)
        self.tab_widget.setCurrentIndex(index)

    def get_current_test(self):
        """获取当前测试key"""
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "dcdc_efficiency")

    def _on_test_started(self, test_type):
        """处理测试开始事件"""
        if test_type == "dcdc_efficiency":
            self.dcdc_efficiency_ui.set_system_status("测试进行中")
        elif test_type == "output_voltage":
            self.output_voltage_ui.set_system_status("测试进行中")
        elif test_type == "threshold":
            self.threshold_ui.set_system_status("测试进行中")
        elif test_type == "is_gain":
            self.is_gain_ui.set_system_status("测试进行中")
        elif test_type == "oscp":
            self.oscp_ui.set_system_status("测试进行中")
        elif test_type == "gpadc_test":
            self.gpadc_test_ui.set_system_status("测试进行中")

        config = self.get_test_config(test_type)
        print(f"开始{test_type}测试，配置: {config}")

    def _on_test_stopped(self, test_type):
        """处理测试停止事件"""
        if test_type == "dcdc_efficiency":
            self.dcdc_efficiency_ui.set_system_status("就绪")
        elif test_type == "output_voltage":
            self.output_voltage_ui.set_system_status("就绪")
        elif test_type == "threshold":
            self.threshold_ui.set_system_status("就绪")
        elif test_type == "is_gain":
            self.is_gain_ui.set_system_status("就绪")
        elif test_type == "oscp":
            self.oscp_ui.set_system_status("就绪")
        elif test_type == "gpadc_test":
            self.gpadc_test_ui.set_system_status("就绪")

        print(f"停止{test_type}测试")

    def get_test_config(self, test_type):
        """获取指定测试类型的配置"""
        if test_type == "dcdc_efficiency":
            return self.dcdc_efficiency_ui.get_test_config()
        elif test_type == "output_voltage":
            return self.output_voltage_ui.get_test_config()
        elif test_type == "threshold":
            return self.threshold_ui.get_test_config()
        elif test_type == "is_gain":
            return self.is_gain_ui.get_test_config()
        elif test_type == "oscp":
            return self.oscp_ui.get_test_config()
        elif test_type == "gpadc_test":
            return self.gpadc_test_ui.get_test_config()
        return None

    def update_test_result(self, test_type, result):
        """更新测试结果"""
        if test_type == "dcdc_efficiency":
            self.dcdc_efficiency_ui.update_test_result(result)
        elif test_type == "output_voltage":
            self.output_voltage_ui.update_test_result(result)
        elif test_type == "threshold":
            self.threshold_ui.update_test_result(result)
        elif test_type == "is_gain":
            self.is_gain_ui.update_test_result(result)
        elif test_type == "oscp":
            self.oscp_ui.update_test_result(result)
        elif test_type == "gpadc_test":
            self.gpadc_test_ui.update_test_result(result)

    def clear_all_results(self):
        """清空所有测试结果"""
        self.dcdc_efficiency_ui.clear_results()
        self.output_voltage_ui.clear_results()
        self.threshold_ui.clear_results()
        self.is_gain_ui.clear_results()
        self.oscp_ui.clear_results()
        self.gpadc_test_ui.clear_results()

    def set_system_status(self, status, is_error=False):
        """设置所有子UI的系统状态"""
        self.dcdc_efficiency_ui.set_system_status(status, is_error)
        self.output_voltage_ui.set_system_status(status, is_error)
        self.threshold_ui.set_system_status(status, is_error)
        self.is_gain_ui.set_system_status(status, is_error)
        self.oscp_ui.set_system_status(status, is_error)
        self.gpadc_test_ui.set_system_status(status, is_error)

    def update_instrument_info(self, instrument_info):
        """更新所有子UI的仪器信息"""
        self.dcdc_efficiency_ui.update_instrument_info(instrument_info)
        self.output_voltage_ui.update_instrument_info(instrument_info)
        self.threshold_ui.update_instrument_info(instrument_info)
        self.is_gain_ui.update_instrument_info(instrument_info)
        self.oscp_ui.update_instrument_info(instrument_info)
        self.gpadc_test_ui.update_instrument_info(instrument_info)

    def get_test_mode(self):
        """获取当前测试模式"""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'get_test_mode'):
            return current_widget.get_test_mode()
        return "手动测试"

    def set_test_mode(self, mode):
        """设置所有子UI的测试模式"""
        self.dcdc_efficiency_ui.set_test_mode(mode)
        self.output_voltage_ui.set_test_mode(mode)
        self.threshold_ui.set_test_mode(mode)
        self.is_gain_ui.set_test_mode(mode)
        self.oscp_ui.set_test_mode(mode)
        self.gpadc_test_ui.set_test_mode(mode)

    def get_test_id(self):
        """获取当前测试编号"""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'get_test_id'):
            return current_widget.get_test_id()
        return "PMU_TEST_001"

    def set_test_id(self, test_id):
        """设置所有子UI的测试编号"""
        self.dcdc_efficiency_ui.set_test_id(test_id)
        self.output_voltage_ui.set_test_id(test_id)
        self.threshold_ui.set_test_id(test_id)
        self.is_gain_ui.set_test_id(test_id)
        self.oscp_ui.set_test_id(test_id)
        self.gpadc_test_ui.set_test_id(test_id)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pmu_test_ui = PMUTestUI()
    pmu_test_ui.setWindowTitle("PMU测试系统")
    pmu_test_ui.setGeometry(100, 100, 1200, 800)
    pmu_test_ui.show()

    sys.exit(app.exec())
    