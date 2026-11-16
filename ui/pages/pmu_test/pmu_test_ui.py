#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU测试主UI组件 - 整合DCDC Efficiency、Output Voltage、OSCP子页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.widgets.config_memory import ConfigMemory
from ui.pages.pmu_test.pmu_dcdc_efficiency import PMUDCDCEfficiencyUI
from ui.pages.pmu_test.pmu_output_voltage import PMUOutputVoltageUI
from log_config import get_logger

logger = get_logger(__name__)
from ui.pages.pmu_test.pmu_isGain_ui import PMUIsGainUI
from ui.pages.pmu_test.pmu_oscp_ui import PMUOSCPUI
from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI
from ui.pages.pmu_test.clk_test_ui import CLKTestUI
from ui.pages.pmu_test.pmu_psrr_ui import PMUPSRRUI
from ui.pages.pmu_test.ft_calib_check_ui import FTCalibCheckUI


class PMUTestUI(QWidget):
    """PMU测试主UI组件"""

    TEST_TAB_MAP = {
        "dcdc_efficiency": 0,
        "output_voltage": 1,
        "is_gain": 2,
        "oscp": 3,
        "gpadc_test": 4,
        "clk_test": 5,
        "psrr": 6,
        "ft_calib_check": 7,
    }

    # 与 TEST_TAB_MAP 对齐的 tab 标签 / 子页属性名（声明顺序 = tab 顺序）
    _TAB_LABELS = {
        "dcdc_efficiency": "DCDC Efficiency",
        "output_voltage": "Output Voltage",
        "is_gain": "Is_gain",
        "oscp": "OSCP",
        "gpadc_test": "GPADC Test",
        "clk_test": "CLK Test",
        "psrr": "PSRR Test",
        "ft_calib_check": "FT Calibration Check",
    }
    _SUBPAGE_ATTRS = {
        "dcdc_efficiency": "dcdc_efficiency_ui",
        "output_voltage": "output_voltage_ui",
        "is_gain": "is_gain_ui",
        "oscp": "oscp_ui",
        "gpadc_test": "gpadc_test_ui",
        "clk_test": "clk_test_ui",
        "psrr": "psrr_ui",
        "ft_calib_check": "ft_calib_check_ui",
    }

    def __init__(self, n6705c_top=None, mso64b_top=None, chamber_ui=None, instrument_manager=None,
                 ui_action_registry=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._mso64b_top = mso64b_top
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

        self._config_memory = ConfigMemory("pmu_test/container", self)
        self._config_memory.bind("current_tab", self.tab_widget)
        self._config_memory.restore()
        # 只构建当前选中的子页，其余首次切到时再构建
        self._ensure_subpage(self.get_current_test())

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

        # 占位 widget 先占住 tab 槽位；子页在首次选中时构建（_ensure_subpage），
        # 避免首次进入 PMU Test 一次性构建全部子页造成长时间卡顿
        for label in self._TAB_LABELS.values():
            self.tab_widget.addTab(QWidget(), label)

        main_layout.addWidget(self.tab_widget)

    def _build_subpage(self, key):
        """按 key 构建子页实例（构造参数与原即时构建保持一致）"""
        if key == "dcdc_efficiency":
            return PMUDCDCEfficiencyUI(
                n6705c_top=self._n6705c_top,
                chamber_ui=self._chamber_ui,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        if key == "output_voltage":
            return PMUOutputVoltageUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
            )
        if key == "is_gain":
            return PMUIsGainUI(
                n6705c_top=self._n6705c_top,
                mso64b_top=self._mso64b_top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        if key == "oscp":
            return PMUOSCPUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
            )
        if key == "gpadc_test":
            return GPADCTestUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        if key == "clk_test":
            return CLKTestUI(
                mso64b_top=self._mso64b_top,
                chamber_ui=self._chamber_ui,
                instrument_manager=self._instrument_manager,
            )
        if key == "psrr":
            return PMUPSRRUI(
                n6705c_top=self._n6705c_top,
                mso64b_top=self._mso64b_top,
                instrument_manager=self._instrument_manager,
            )
        if key == "ft_calib_check":
            return FTCalibCheckUI(
                n6705c_top=self._n6705c_top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
        raise KeyError(f"未知 PMU 子页: {key}")

    def _ensure_subpage(self, key):
        """懒加载入口：子页未构建则构建并替换占位 tab，随后接信号与同步仪器状态"""
        if key not in self.TEST_TAB_MAP:
            key = "dcdc_efficiency"
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

        self._connect_subpage_signals(key, ui)
        if hasattr(ui, 'sync_n6705c_from_top'):
            ui.sync_n6705c_from_top()
        elif hasattr(ui, '_sync_from_top'):
            ui._sync_from_top()
        if hasattr(ui, 'sync_chamber_from_manager'):
            ui.sync_chamber_from_manager()
        if key == "psrr":
            ui.sync_oscilloscope_from_top()
        return ui

    def _init_ui_elements(self):
        """初始化UI元素（子页信号在各自构建时连接，见 _connect_subpage_signals）"""
        pass

    def _connect_subpage_signals(self, key, ui):
        """连接单个子页面的信号"""
        if key == "psrr":
            ui.start_test_btn.clicked.connect(
                lambda: self._on_test_started("psrr")
                if ui.is_test_running else None)
            ui.sequence_execution_finished.connect(
                lambda _success, _message: self._on_test_stopped("psrr"))
            return
        ui.start_test_btn.clicked.connect(
            lambda: self._on_test_btn_clicked(key, ui))
        ui.stop_test_btn.clicked.connect(
            lambda: self._on_test_stopped(key))

    def _on_test_btn_clicked(self, test_type, ui):
        is_running = getattr(ui, 'is_test_running', None)
        if is_running is None:
            is_running = getattr(ui, '_test_thread', None) is not None
        if not is_running:
            self._on_test_started(test_type)
        else:
            self._on_test_stopped(test_type)

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
            if hasattr(sub_ui, 'sync_chamber_from_manager'):
                sub_ui.sync_chamber_from_manager()
        if self.psrr_ui is not None:
            self.psrr_ui.sync_oscilloscope_from_top()

    def get_current_test(self):
        """获取当前测试key"""
        index = self.tab_widget.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "dcdc_efficiency")

    def _on_test_started(self, test_type):
        """处理测试开始事件"""
        ui = self._subpages.get(test_type)
        if ui is not None:
            ui.set_system_status("测试进行中")

        config = self.get_test_config(test_type)
        logger.info("开始%s测试，配置: %s", test_type, config)

    def _on_test_stopped(self, test_type):
        """处理测试停止事件"""
        ui = self._subpages.get(test_type)
        if ui is not None:
            ui.set_system_status("就绪")

        logger.info("停止%s测试", test_type)

    def get_test_config(self, test_type):
        """获取指定测试类型的配置（子页未构建时返回 None）"""
        ui = self._subpages.get(test_type)
        if ui is not None:
            return ui.get_test_config()
        return None

    def update_test_result(self, test_type, result):
        """更新测试结果"""
        ui = self._subpages.get(test_type)
        if ui is not None:
            ui.update_test_result(result)

    def clear_all_results(self):
        """清空所有测试结果"""
        for sub_ui in self._subpages.values():
            sub_ui.clear_results()

    def set_system_status(self, status, is_error=False):
        """设置所有子UI的系统状态"""
        for sub_ui in self._subpages.values():
            sub_ui.set_system_status(status, is_error)

    def update_instrument_info(self, instrument_info):
        """更新所有子UI的仪器信息"""
        for sub_ui in self._subpages.values():
            sub_ui.update_instrument_info(instrument_info)

    def get_test_mode(self):
        """获取当前测试模式"""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'get_test_mode'):
            return current_widget.get_test_mode()
        return "手动测试"

    def set_test_mode(self, mode):
        """设置所有子UI的测试模式"""
        for sub_ui in self._subpages.values():
            sub_ui.set_test_mode(mode)

    def get_test_id(self):
        """获取当前测试编号"""
        current_widget = self.tab_widget.currentWidget()
        if hasattr(current_widget, 'get_test_id'):
            return current_widget.get_test_id()
        return "PMU_TEST_001"

    def set_test_id(self, test_id):
        """设置所有子UI的测试编号"""
        for sub_ui in self._subpages.values():
            sub_ui.set_test_id(test_id)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from ui.standalone import apply_window_icon, resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pmu_test_ui = PMUTestUI()
    pmu_test_ui.setWindowTitle("PMU测试系统")
    apply_window_icon(pmu_test_ui, "pmu_test")
    resize_and_center_window(pmu_test_ui)
    pmu_test_ui.show()

    sys.exit(app.exec())
