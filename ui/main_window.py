#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QLineEdit, QGridLayout,
    QTabWidget, QCheckBox, QSplitter, QFrame, QButtonGroup,
    QGraphicsDropShadowEffect, QDialog, QTextBrowser
)

from PySide6.QtCore import Qt, Signal, QEvent, QPoint, QTimer
from PySide6.QtGui import QPalette, QColor, QFont
from ui.widgets.plot_widget import PlotWidget
from ui.pages.oscilloscope.oscilloscope_base_ui import OscilloscopeBaseUI
from ui.pages.n6705c_power_analyzer.n6705c_analyser_ui import N6705CAnalyserUI
from ui.pages.n6705c_power_analyzer.n6705c_datalog_ui import N6705CDatalogUI
from ui.pages.n6705c_power_analyzer.n6705c_top import N6705CTop
from ui.pages.oscilloscope.mso64b_top import MSO64BTop
from ui.pages.pmu_test.pmu_test_ui import PMUTestUI
from ui.pages.chamber.vt6002_chamber_ui import VT6002ChamberUI
from ui.widgets.sidebar_nav_button import SidebarNavButton
from ui.pages.consumption_test.consumption_test import ConsumptionTestUI
from ui.pages.charger_test.charger_test_ui import ChargerTestUI
from core.test_manager import TestManager
from instruments.base.visa_instrument import VisaInstrument

_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources", "icons"
)
from instruments.chambers.vt6002_chamber import VT6002
from ui.styles import SCROLLBAR_STYLE
from log_config import get_logger
from debug_config import DEBUG_MOCK

logger = get_logger(__name__)


class PMUSubMenuItem(QPushButton):
    """PMU二级菜单项"""

    def __init__(self, text, key, position="middle", parent=None):
        super().__init__(text, parent)
        self.key = key
        self.position = position
        self.selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self._apply_style()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._apply_style()

    def _apply_style(self):
        radius_top = "12px" if self.position == "top" else "0px"
        radius_bottom = "12px" if self.position == "bottom" else "0px"

        if self.selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    border: none;
                    background-color: #3f3a8a;
                    color: #9cabff;
                    text-align: left;
                    padding: 0 18px;
                    font-size: 14px;
                    border-top-left-radius: {radius_top};
                    border-top-right-radius: {radius_top};
                    border-bottom-left-radius: {radius_bottom};
                    border-bottom-right-radius: {radius_bottom};
                }}
                QPushButton:hover {{
                    background-color: #4942a0;
                    color: #ffffff;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    border: none;
                    background-color: transparent;
                    color: #d5d9e3;
                    text-align: left;
                    padding: 0 18px;
                    font-size: 14px;
                    border-top-left-radius: {radius_top};
                    border-top-right-radius: {radius_top};
                    border-bottom-left-radius: {radius_bottom};
                    border-bottom-right-radius: {radius_bottom};
                }}
                QPushButton:hover {{
                    background-color: #24314a;
                    color: #ffffff;
                }}
                QWidget {{
                    background-color: #020618;
                    color: #c8c8c8;
                }}
            """)


class PMUSubMenu(QWidget):
    """PMU Auto Test 右侧悬浮二级菜单"""

    item_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._hovered = False
        self.current_key = None
        self.buttons = {}

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(10, 10, 10, 10)
        self.outer_layout.setSpacing(0)

        self.panel = QFrame(self)
        self.panel.setObjectName("pmuSubMenuPanel")
        self.panel.setStyleSheet("""
            QFrame#pmuSubMenuPanel {
                background-color: #1b2233;
                border: none;
                border-radius: 12px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.panel.setGraphicsEffect(shadow)

        self.outer_layout.addWidget(self.panel)

        self.layout = QVBoxLayout(self.panel)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.menu_items = [
            ("dcdc_efficiency", "DCDC Efficiency"),
            ("output_voltage", "Output Voltage"),
            ("is_gain", "Is_gain"),
            ("oscp", "OSCP"),
            ("gpadc_test", "GPADC Test"),
            ("clk_test", "CLK Test"),
        ]

        total = len(self.menu_items)
        for i, (key, text) in enumerate(self.menu_items):
            if i == 0:
                position = "top"
            elif i == total - 1:
                position = "bottom"
            else:
                position = "middle"

            btn = PMUSubMenuItem(text, key, position=position, parent=self.panel)
            btn.clicked.connect(lambda checked=False, k=key: self.item_clicked.emit(k))
            self.layout.addWidget(btn)
            self.buttons[key] = btn

        self.hide()

    def set_current_item(self, key: str):
        self.current_key = key
        for item_key, btn in self.buttons.items():
            btn.set_selected(item_key == key)

    def enterEvent(self, event):
        self._hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        super().leaveEvent(event)

    def is_hovered(self):
        return self._hovered


class PowerAnalyzerSubMenu(QWidget):

    item_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._hovered = False
        self.current_key = None
        self.buttons = {}

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(10, 10, 10, 10)
        self.outer_layout.setSpacing(0)

        self.panel = QFrame(self)
        self.panel.setObjectName("paSubMenuPanel")
        self.panel.setStyleSheet("""
            QFrame#paSubMenuPanel {
                background-color: #1b2233;
                border: none;
                border-radius: 12px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.panel.setGraphicsEffect(shadow)

        self.outer_layout.addWidget(self.panel)

        self.layout = QVBoxLayout(self.panel)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.menu_items = [
            ("analyser", "N6705C Analyser"),
            ("datalog", "N6705C Datalog"),
        ]

        total = len(self.menu_items)
        for i, (key, text) in enumerate(self.menu_items):
            if i == 0:
                position = "top"
            elif i == total - 1:
                position = "bottom"
            else:
                position = "middle"

            btn = PMUSubMenuItem(text, key, position=position, parent=self.panel)
            btn.clicked.connect(lambda checked=False, k=key: self.item_clicked.emit(k))
            self.layout.addWidget(btn)
            self.buttons[key] = btn

        self.hide()

    def set_current_item(self, key: str):
        self.current_key = key
        for item_key, btn in self.buttons.items():
            btn.set_selected(item_key == key)

    def enterEvent(self, event):
        self._hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        super().leaveEvent(event)

    def is_hovered(self):
        return self._hovered


class ChargerSubMenu(QWidget):

    item_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._hovered = False
        self.current_key = None
        self.buttons = {}

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(10, 10, 10, 10)
        self.outer_layout.setSpacing(0)

        self.panel = QFrame(self)
        self.panel.setObjectName("chargerSubMenuPanel")
        self.panel.setStyleSheet("""
            QFrame#chargerSubMenuPanel {
                background-color: #1b2233;
                border: none;
                border-radius: 12px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.panel.setGraphicsEffect(shadow)

        self.outer_layout.addWidget(self.panel)

        self.layout = QVBoxLayout(self.panel)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.menu_items = [
            ("config_traverse", "Config Traverse Test"),
            ("status_register", "Status Register Test"),
            ("iterm", "Iterm Test"),
            ("regulation_voltage", "Regulation Voltage Test"),
        ]

        total = len(self.menu_items)
        for i, (key, text) in enumerate(self.menu_items):
            if i == 0:
                position = "top"
            elif i == total - 1:
                position = "bottom"
            else:
                position = "middle"

            btn = PMUSubMenuItem(text, key, position=position, parent=self.panel)
            btn.clicked.connect(lambda checked=False, k=key: self.item_clicked.emit(k))
            self.layout.addWidget(btn)
            self.buttons[key] = btn

        self.hide()

    def set_current_item(self, key: str):
        self.current_key = key
        for item_key, btn in self.buttons.items():
            btn.set_selected(item_key == key)

    def enterEvent(self, event):
        self._hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        super().leaveEvent(event)

    def is_hovered(self):
        return self._hovered


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("功耗测试工具")
        self.setGeometry(100, 100, 1200, 800)

        # 初始化测试管理器
        self.test_manager = TestManager()

        # 初始化仪器
        self.visa_instrument = VisaInstrument()
        self.vt6002_chamber = None

        self.n6705c_top = N6705CTop(self)
        self.mso64b_top = MSO64BTop(self)

        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C, MockMSO64B
            logger.info("[MOCK] Auto-connecting mock instruments...")
            self.n6705c_top.connect_a("MOCK::N6705C::A", MockN6705C(), "MOCK-A")
            self.n6705c_top.connect_b("MOCK::N6705C::B", MockN6705C(), "MOCK-B")
            self.mso64b_top.connect_instrument("MOCK::MSO64B", MockMSO64B(), "MSO64B")

        self.n6705c_analyser_ui = None
        self.n6705c_datalog_ui = None
        self.oscilloscope_ui = None
        self.pmu_test_ui = None
        self.vt6002_chamber_ui = None
        self.consumption_test_ui = None
        self.charger_test_ui = None
        self.current_instrument_ui = None
        self.channels = []

        # PMU菜单状态
        self.pmu_submenu = None
        self._pmu_btn_hovered = False
        self.current_pmu_test_key = None

        self.pa_submenu = None
        self._pa_btn_hovered = False
        self.current_pa_mode = "analyser"

        self.charger_submenu = None
        self._charger_btn_hovered = False
        self.current_charger_test_key = None

        self.pmu_test_tab_map = {
            "dcdc_efficiency": 0,
            "output_voltage": 1,
            "is_gain": 2,
            "oscp": 3,
            "gpadc_test": 4,
            "clk_test": 5,
        }

        self.charger_test_tab_map = {
            "config_traverse": 0,
            "status_register": 1,
            "iterm": 2,
            "regulation_voltage": 3,
        }

        # 设置样式
        self._setup_style()

        # 创建主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建主内容区域
        self._create_main_content()

        # 创建PMU二级菜单
        self._create_pmu_submenu()

        self._create_pa_submenu()

        self._create_charger_submenu()

        self._connect_signals()

    def _setup_style(self):
        """设置界面样式"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(2, 6, 24))
        palette.setColor(QPalette.WindowText, QColor(200, 200, 200))
        palette.setColor(QPalette.Base, QColor(32, 35, 40))
        palette.setColor(QPalette.AlternateBase, QColor(40, 43, 48))
        palette.setColor(QPalette.ToolTipBase, QColor(40, 43, 48))
        palette.setColor(QPalette.ToolTipText, QColor(200, 200, 200))
        palette.setColor(QPalette.Text, QColor(200, 200, 200))
        palette.setColor(QPalette.Button, QColor(50, 53, 58))
        palette.setColor(QPalette.ButtonText, QColor(200, 200, 200))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(30, 30, 30))
        self.setPalette(palette)

        font = QFont("Segoe UI", 9)
        self.setFont(font)

        self.setWindowTitle("LabControl Pro")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #020618;
            }
            QWidget#rootWidget {
                background-color: #030b23;
                color: #eaf1ff;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
                font-size: 14px;
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
            QCheckBox {
                color: #c8c8c8;
            }
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #020618;
            }
            QTabBar::tab {
                background-color: #2a2d32;
                color: #c8c8c8;
                padding: 6px 12px;
                border: 1px solid #333;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #32353a;
                border-top: 2px solid #2a82da;
            }
            QFrame {
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #020618;
            }
            QSpinBox, QDoubleSpinBox {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px;
                height: 0px;
                border: none;
            }
        """ + SCROLLBAR_STYLE)

    def _create_main_content(self):
        """创建主内容区域"""
        main_splitter = QSplitter(Qt.Horizontal)

        # 左侧导航栏
        self.left_nav = QFrame()
        self.left_nav.setFixedWidth(280)
        self.left_nav.setObjectName("leftNav")
        self.left_nav.setStyleSheet("""
            QFrame#leftNav {
                background-color: #0b1020;
                border: none;
                border-radius: 0px;
            }
        """)

        left_nav_layout = QVBoxLayout(self.left_nav)
        left_nav_layout.setContentsMargins(14, 18, 14, 18)
        left_nav_layout.setSpacing(10)

        # 顶部标题
        logo_label = QLabel("LabControl Pro")
        logo_label.setStyleSheet("""
            QLabel {
                color: #7ea1ff;
                font-size: 18px;
                font-weight: 700;
                padding: 6px 4px 12px 4px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(logo_label)

        # 分组标题：INSTRUMENTS
        instruments_title = QLabel("INSTRUMENTS")
        instruments_title.setStyleSheet("""
            QLabel {
                color: #5f78a8;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 6px 4px 6px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(instruments_title)

        # 导航按钮
        self.n6705c_power_analyzer_btn = SidebarNavButton(
            "N6705C",
            "",
            os.path.join(_ICONS_DIR, "zap.svg")
        )
        self.n6705c_power_analyzer_btn.setChecked(True)

        self.oscilloscope_btn = SidebarNavButton(
            "Oscilloscope",
            "",
            os.path.join(_ICONS_DIR, "activity.svg")
        )

        self.chamber_btn = SidebarNavButton(
            "Chamber",
            "",
            os.path.join(_ICONS_DIR, "thermometer.svg")
        )

        left_nav_layout.addWidget(self.n6705c_power_analyzer_btn)
        left_nav_layout.addWidget(self.oscilloscope_btn)
        left_nav_layout.addWidget(self.chamber_btn)

        # 分组标题：AUTOMATION
        automation_title = QLabel("AUTOMATION")
        automation_title.setStyleSheet("""
            QLabel {
                color: #5f78a8;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 18px 6px 4px 6px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(automation_title)

        self.pmu_test_btn = SidebarNavButton(
            "PMU Test",
            "",
            "⚙"
        )
        left_nav_layout.addWidget(self.pmu_test_btn)

        self.charger_test_btn = SidebarNavButton(
            "Charger Test",
            "",
            "🔋"
        )
        left_nav_layout.addWidget(self.charger_test_btn)

        self.consumption_test_btn = SidebarNavButton(
            "Consumption Test",
            "",
            os.path.join(_ICONS_DIR, "zap.svg")
        )
        left_nav_layout.addWidget(self.consumption_test_btn)

        # 单选组
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.n6705c_power_analyzer_btn)
        self.nav_button_group.addButton(self.oscilloscope_btn)
        self.nav_button_group.addButton(self.chamber_btn)
        self.nav_button_group.addButton(self.pmu_test_btn)
        self.nav_button_group.addButton(self.charger_test_btn)
        self.nav_button_group.addButton(self.consumption_test_btn)

        # 关键：初始化一次箭头显示状态
        self._refresh_nav_arrow_state()

        left_nav_layout.addStretch()

        # 底部容器
        bottom_widget = QWidget()
        bottom_widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("""
            QFrame {
                background-color: #1a2238;
                border: none;
            }
        """)
        bottom_layout.addWidget(divider)

        self.help_btn = QPushButton("？ Help")
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.setStyleSheet("""
            QPushButton {
                min-height: 42px;
                background-color: #4f3df0;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                text-align: center;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #5b49ff;
            }
            QPushButton:pressed {
                background-color: #4534dd;
            }
        """)
        bottom_layout.addWidget(self.help_btn)

        self.instrument_status_container = QWidget()
        self.instrument_status_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        self.instrument_status_layout = QVBoxLayout(self.instrument_status_container)
        self.instrument_status_layout.setContentsMargins(0, 0, 0, 0)
        self.instrument_status_layout.setSpacing(4)
        self.instrument_status_items = {}
        bottom_layout.addWidget(self.instrument_status_container)

        left_nav_layout.addWidget(bottom_widget)

        main_splitter.addWidget(self.left_nav)

        # 右侧主内容区域
        self.right_content = QWidget()
        self.right_content_layout = QVBoxLayout(self.right_content)
        self.right_content_layout.setContentsMargins(0, 0, 0, 0)

        self.instrument_ui_container = QWidget()
        self.instrument_ui_container_layout = QVBoxLayout(self.instrument_ui_container)
        self.instrument_ui_container_layout.setContentsMargins(0, 0, 0, 0)

        self._create_power_analyser_ui()
        self.right_content_layout.addWidget(self.instrument_ui_container)

        main_splitter.addWidget(self.right_content)
        main_splitter.setSizes([280, 920])

        self.main_layout.addWidget(main_splitter)

    def _refresh_nav_arrow_state(self):
        """刷新左侧导航按钮最右侧箭头显示状态：只有选中项显示"""
        nav_buttons = [
            self.n6705c_power_analyzer_btn,
            self.oscilloscope_btn,
            self.chamber_btn,
            self.pmu_test_btn,
            self.charger_test_btn,
            self.consumption_test_btn
        ]

        for btn in nav_buttons:
            if hasattr(btn, "set_arrow_visible"):
                btn.set_arrow_visible(btn.isChecked())
            elif hasattr(btn, "arrow_label"):
                btn.arrow_label.setVisible(btn.isChecked())
            elif hasattr(btn, "right_arrow_label"):
                btn.right_arrow_label.setVisible(btn.isChecked())

    def _create_pmu_submenu(self):
        self.pmu_submenu = PMUSubMenu(self)
        self.pmu_submenu.item_clicked.connect(self._on_pmu_submenu_clicked)

        self.pmu_test_btn.installEventFilter(self)
        self.pmu_submenu.installEventFilter(self)

    def _create_pa_submenu(self):
        self.pa_submenu = PowerAnalyzerSubMenu(self)
        self.pa_submenu.item_clicked.connect(self._on_pa_submenu_clicked)

        self.n6705c_power_analyzer_btn.installEventFilter(self)
        self.pa_submenu.installEventFilter(self)

    def _create_charger_submenu(self):
        self.charger_submenu = ChargerSubMenu(self)
        self.charger_submenu.item_clicked.connect(self._on_charger_submenu_clicked)

        self.charger_test_btn.installEventFilter(self)
        self.charger_submenu.installEventFilter(self)

    def _show_pa_submenu(self):
        if not self.pa_submenu:
            return

        btn_global_pos = self.n6705c_power_analyzer_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.n6705c_power_analyzer_btn.width() + 8
        y = btn_global_pos.y()

        self.pa_submenu.set_current_item(self.current_pa_mode)
        self.pa_submenu.move(x, y)
        self.pa_submenu.show()
        self.pa_submenu.raise_()

    def _hide_pa_submenu_if_needed(self):
        if self._pa_btn_hovered:
            return
        if self.pa_submenu and self.pa_submenu.is_hovered():
            return
        if self.pa_submenu:
            self.pa_submenu.hide()

    def _on_pa_submenu_clicked(self, mode_key):
        self.current_pa_mode = mode_key
        self.pa_submenu.set_current_item(mode_key)
        self.n6705c_power_analyzer_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        if mode_key == "analyser":
            self._create_power_analyser_ui()
        elif mode_key == "datalog":
            self._create_datalog_ui()
        self.pa_submenu.hide()

    def _show_pmu_submenu(self):
        """显示PMU二级菜单"""
        if not self.pmu_submenu:
            return

        btn_global_pos = self.pmu_test_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.pmu_test_btn.width() + 8
        y = btn_global_pos.y()

        self.pmu_submenu.set_current_item(self.current_pmu_test_key)
        self.pmu_submenu.move(x, y)
        self.pmu_submenu.show()
        self.pmu_submenu.raise_()

    def _hide_pmu_submenu_if_needed(self):
        """按需隐藏PMU二级菜单"""
        if self._pmu_btn_hovered:
            return
        if self.pmu_submenu and self.pmu_submenu.is_hovered():
            return
        if self.pmu_submenu:
            self.pmu_submenu.hide()

    def _on_pmu_submenu_clicked(self, test_key):
        self.current_pmu_test_key = test_key
        self.pmu_submenu.set_current_item(test_key)
        self.pmu_test_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._create_pmu_test_ui(selected_test=test_key)
        self.pmu_submenu.hide()

    def _show_charger_submenu(self):
        if not self.charger_submenu:
            return

        btn_global_pos = self.charger_test_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.charger_test_btn.width() + 8
        y = btn_global_pos.y()

        self.charger_submenu.set_current_item(self.current_charger_test_key)
        self.charger_submenu.move(x, y)
        self.charger_submenu.show()
        self.charger_submenu.raise_()

    def _hide_charger_submenu_if_needed(self):
        if self._charger_btn_hovered:
            return
        if self.charger_submenu and self.charger_submenu.is_hovered():
            return
        if self.charger_submenu:
            self.charger_submenu.hide()

    def _on_charger_submenu_clicked(self, test_key):
        self.current_charger_test_key = test_key
        self.charger_submenu.set_current_item(test_key)
        self.charger_test_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._create_charger_test_ui(selected_test=test_key)
        self.charger_submenu.hide()

    def eventFilter(self, obj, event):
        if obj == self.pmu_test_btn:
            if event.type() == QEvent.Enter:
                self._pmu_btn_hovered = True
                self._show_pmu_submenu()
            elif event.type() == QEvent.Leave:
                self._pmu_btn_hovered = False
                QTimer.singleShot(120, self._hide_pmu_submenu_if_needed)

        elif obj == self.pmu_submenu:
            if event.type() == QEvent.Enter:
                self._show_pmu_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(120, self._hide_pmu_submenu_if_needed)

        elif obj == self.n6705c_power_analyzer_btn:
            if event.type() == QEvent.Enter:
                self._pa_btn_hovered = True
                self._show_pa_submenu()
            elif event.type() == QEvent.Leave:
                self._pa_btn_hovered = False
                QTimer.singleShot(120, self._hide_pa_submenu_if_needed)

        elif obj == self.pa_submenu:
            if event.type() == QEvent.Enter:
                self._show_pa_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(120, self._hide_pa_submenu_if_needed)

        elif obj == self.charger_test_btn:
            if event.type() == QEvent.Enter:
                self._charger_btn_hovered = True
                self._show_charger_submenu()
            elif event.type() == QEvent.Leave:
                self._charger_btn_hovered = False
                QTimer.singleShot(120, self._hide_charger_submenu_if_needed)

        elif obj == self.charger_submenu:
            if event.type() == QEvent.Enter:
                self._show_charger_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(120, self._hide_charger_submenu_if_needed)

        return super().eventFilter(obj, event)

    def _create_power_analyser_ui(self):
        self._hide_all_instrument_uis()
        if self.n6705c_analyser_ui is None:
            self.n6705c_analyser_ui = N6705CAnalyserUI(n6705c_top=self.n6705c_top)
            self.instrument_ui_container_layout.addWidget(self.n6705c_analyser_ui)
        else:
            self.n6705c_analyser_ui._sync_from_top()
            self.n6705c_analyser_ui.show()
        self.current_instrument_ui = "power_analyser"
        self.channels = self.n6705c_analyser_ui.channels if hasattr(self.n6705c_analyser_ui, 'channels') else []

    def _create_datalog_ui(self):
        self._hide_all_instrument_uis()
        if self.n6705c_datalog_ui is None:
            self.n6705c_datalog_ui = N6705CDatalogUI(n6705c_top=self.n6705c_top)
            self.instrument_ui_container_layout.addWidget(self.n6705c_datalog_ui)
        else:
            self.n6705c_datalog_ui._sync_from_top()
            self.n6705c_datalog_ui.show()
        self.current_instrument_ui = "datalog"

    def _create_oscilloscope_ui(self):
        self._hide_all_instrument_uis()
        if self.oscilloscope_ui is None:
            self.oscilloscope_ui = OscilloscopeBaseUI(mso64b_top=self.mso64b_top)
            self.oscilloscope_ui.connection_changed.connect(self._update_instrument_status)
            self.instrument_ui_container_layout.addWidget(self.oscilloscope_ui)
        else:
            self.oscilloscope_ui.show()
        self.current_instrument_ui = "oscilloscope"

    def _create_thermal_chamber_ui(self):
        self._hide_all_instrument_uis()
        if self.vt6002_chamber_ui is None:
            self.vt6002_chamber_ui = VT6002ChamberUI()
            self.vt6002_chamber_ui.connection_changed.connect(self._update_instrument_status)
            self.instrument_ui_container_layout.addWidget(self.vt6002_chamber_ui)
        else:
            self.vt6002_chamber_ui.show()
        self.current_instrument_ui = "thermal_chamber"

    def _create_pmu_test_ui(self, selected_test=None):
        self._hide_all_instrument_uis()
        if self.pmu_test_ui is None:
            self.pmu_test_ui = PMUTestUI(
                n6705c_top=self.n6705c_top,
                mso64b_top=self.mso64b_top,
                vt6002_chamber_ui=self.vt6002_chamber_ui,
            )
            self.instrument_ui_container_layout.addWidget(self.pmu_test_ui)
        else:
            self.pmu_test_ui._sync_from_top()
            self.pmu_test_ui.show()
        self.current_instrument_ui = "pmu_test"
        if selected_test in self.pmu_test_tab_map:
            self.current_pmu_test_key = selected_test
            if hasattr(self.pmu_test_ui, "set_current_test"):
                self.pmu_test_ui.set_current_test(selected_test)

    def _create_consumption_test_ui(self):
        self._hide_all_instrument_uis()
        if self.consumption_test_ui is None:
            self.consumption_test_ui = ConsumptionTestUI(n6705c_top=self.n6705c_top)
            self.instrument_ui_container_layout.addWidget(self.consumption_test_ui)
        else:
            self.consumption_test_ui.sync_n6705c_from_top()
            self.consumption_test_ui.show()
        self.current_instrument_ui = "consumption_test"

    def _create_charger_test_ui(self, selected_test=None):
        self._hide_all_instrument_uis()
        if self.charger_test_ui is None:
            self.charger_test_ui = ChargerTestUI(n6705c_top=self.n6705c_top)
            self.instrument_ui_container_layout.addWidget(self.charger_test_ui)
        else:
            self.charger_test_ui._sync_from_top()
            self.charger_test_ui.show()
        self.current_instrument_ui = "charger_test"
        if selected_test in self.charger_test_tab_map:
            self.current_charger_test_key = selected_test
            if hasattr(self.charger_test_ui, "set_current_test"):
                self.charger_test_ui.set_current_test(selected_test)

    def _hide_all_instrument_uis(self):
        for widget in [
            self.n6705c_analyser_ui, self.n6705c_datalog_ui,
            self.oscilloscope_ui, self.pmu_test_ui, self.vt6002_chamber_ui,
            self.consumption_test_ui, self.charger_test_ui,
        ]:
            if widget is not None:
                widget.hide()

    def _connect_signals(self):
        """连接信号槽"""
        self.n6705c_power_analyzer_btn.clicked.connect(self._on_nav_button_clicked)
        self.oscilloscope_btn.clicked.connect(self._on_nav_button_clicked)
        self.chamber_btn.clicked.connect(self._on_nav_button_clicked)
        self.pmu_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.charger_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.consumption_test_btn.clicked.connect(self._on_nav_button_clicked)

        self.help_btn.clicked.connect(self._on_help)
        self.test_manager.data_updated.connect(self._update_data)

        self.n6705c_top.connection_changed.connect(self._update_instrument_status)
        self.mso64b_top.connection_changed.connect(self._update_instrument_status)

    def _add_instrument_status(self, key: str, text: str):
        if key in self.instrument_status_items:
            return
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        dot = QLabel("●")
        dot.setStyleSheet("""
            QLabel {
                color: #00d38a;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)

        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: #9fd3c7;
                font-size: 11px;
                border: none;
                background: transparent;
            }
        """)

        layout.addWidget(dot)
        layout.addWidget(label)
        layout.addStretch()

        self.instrument_status_layout.addWidget(widget)
        self.instrument_status_items[key] = widget

    def _remove_instrument_status(self, key: str):
        widget = self.instrument_status_items.pop(key, None)
        if widget is not None:
            self.instrument_status_layout.removeWidget(widget)
            widget.deleteLater()

    def _update_instrument_status(self):
        if self.n6705c_top.is_connected_a:
            name = f"N6705C-A  {self.n6705c_top.serial_a}" if self.n6705c_top.serial_a else "N6705C-A Connected"
            self._remove_instrument_status("n6705c_a")
            self._add_instrument_status("n6705c_a", name)
        else:
            self._remove_instrument_status("n6705c_a")

        if self.n6705c_top.is_connected_b:
            name = f"N6705C-B  {self.n6705c_top.serial_b}" if self.n6705c_top.serial_b else "N6705C-B Connected"
            self._remove_instrument_status("n6705c_b")
            self._add_instrument_status("n6705c_b", name)
        else:
            self._remove_instrument_status("n6705c_b")

        scope_shown = False
        if self.oscilloscope_ui is not None and self.oscilloscope_ui.controller.is_connected and self.oscilloscope_ui.controller.instrument_info:
            parts = [p.strip() for p in self.oscilloscope_ui.controller.instrument_info.split(",")]
            if len(parts) >= 3:
                name = f"{parts[1]}  {parts[2]}"
            elif len(parts) >= 2:
                name = parts[1]
            else:
                name = self.oscilloscope_ui.controller.instrument_info
            self._remove_instrument_status("oscilloscope")
            self._add_instrument_status("oscilloscope", name)
            scope_shown = True
        elif self.mso64b_top and self.mso64b_top.is_connected and self.mso64b_top.mso64b:
            scope_type = getattr(self.mso64b_top, 'scope_type', '') or 'Oscilloscope'
            try:
                idn = self.mso64b_top.mso64b.identify_instrument()
                parts = [p.strip() for p in idn.split(",")]
                if len(parts) >= 3:
                    name = f"{parts[1]}  {parts[2]}"
                elif len(parts) >= 2:
                    name = parts[1]
                else:
                    name = idn
            except Exception:
                name = f"{scope_type} Connected"
            self._remove_instrument_status("oscilloscope")
            self._add_instrument_status("oscilloscope", name)
            scope_shown = True

        if not scope_shown:
            self._remove_instrument_status("oscilloscope")

        if self.vt6002_chamber_ui is not None and self.vt6002_chamber_ui.vt6002 is not None:
            self._remove_instrument_status("vt6002")
            self._add_instrument_status("vt6002", "VT6002 Chamber Connected")
        else:
            self._remove_instrument_status("vt6002")

    def _on_nav_button_clicked(self):
        sender = self.sender()

        if sender == self.n6705c_power_analyzer_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.charger_submenu:
                self.charger_submenu.hide()
            self._show_pa_submenu()
            if self.current_pa_mode == "analyser":
                self._create_power_analyser_ui()
            elif self.current_pa_mode == "datalog":
                self._create_datalog_ui()
            else:
                self._create_power_analyser_ui()

        elif sender == self.oscilloscope_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.pa_submenu:
                self.pa_submenu.hide()
            if self.charger_submenu:
                self.charger_submenu.hide()
            self._create_oscilloscope_ui()

        elif sender == self.chamber_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.pa_submenu:
                self.pa_submenu.hide()
            if self.charger_submenu:
                self.charger_submenu.hide()
            self._create_thermal_chamber_ui()

        elif sender == self.pmu_test_btn:
            if self.pa_submenu:
                self.pa_submenu.hide()
            if self.charger_submenu:
                self.charger_submenu.hide()
            self._create_pmu_test_ui(selected_test=self.current_pmu_test_key)
            self._show_pmu_submenu()

        elif sender == self.charger_test_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.pa_submenu:
                self.pa_submenu.hide()
            self._create_charger_test_ui(selected_test=self.current_charger_test_key)
            self._show_charger_submenu()

        elif sender == self.consumption_test_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.pa_submenu:
                self.pa_submenu.hide()
            if self.charger_submenu:
                self.charger_submenu.hide()
            self._create_consumption_test_ui()

        self._refresh_nav_arrow_state()

    def _get_current_help_key(self):
        if self.current_instrument_ui == "pmu_test":
            key_map = {
                "dcdc_efficiency": "pmu_dcdc_efficiency",
                "output_voltage": "pmu_output_voltage",
                "is_gain": "pmu_is_gain",
                "oscp": "pmu_oscp",
                "gpadc_test": "pmu_gpadc",
                "clk_test": "pmu_clk",
            }
            return key_map.get(self.current_pmu_test_key, "pmu_dcdc_efficiency")
        elif self.current_instrument_ui == "charger_test":
            key_map = {
                "config_traverse": "charger_config_traverse",
                "status_register": "charger_status_register",
                "iterm": "charger_iterm",
                "regulation_voltage": "charger_regulation_voltage",
            }
            return key_map.get(self.current_charger_test_key, "charger_config_traverse")
        elif self.current_instrument_ui == "power_analyser":
            if self.current_pa_mode == "datalog":
                return "datalog"
            return "power_analyser"
        elif self.current_instrument_ui == "datalog":
            return "datalog"
        elif self.current_instrument_ui:
            return self.current_instrument_ui
        return "power_analyser"

    def _on_help(self):
        help_key = self._get_current_help_key()
        helps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "helps")
        help_file = os.path.join(helps_dir, f"{help_key}.html")

        if os.path.exists(help_file):
            with open(help_file, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "<h2>帮助</h2><p>当前页面暂无帮助文档。</p>"

        dialog = QDialog(self)
        dialog.setWindowTitle("帮助")
        dialog.setMinimumSize(560, 480)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0e1525;
            }
            QTextBrowser {
                background-color: #0e1525;
                color: #d0d0d0;
                border: none;
                font-size: 14px;
                padding: 16px;
            }
            QPushButton {
                min-height: 36px;
                min-width: 80px;
                background-color: #4f3df0;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover {
                background-color: #5b49ff;
            }
            QPushButton:pressed {
                background-color: #4534dd;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 8)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(content)
        layout.addWidget(browser)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        btn_layout.setContentsMargins(0, 0, 12, 0)
        layout.addLayout(btn_layout)
        dialog.exec()

    def _scan_visa(self):
        """扫描 VISA 设备"""
        devices = self.visa_instrument.scan_devices()
        self.visa_combo.clear()
        self.visa_combo.addItems(devices)

    def _connect_visa(self):
        """连接 VISA 设备"""
        device = self.visa_combo.currentText()
        if device:
            success = self.visa_instrument.connect(device)
            if success:
                self.connect_visa_btn.setText("断开")
        else:
            if self.visa_instrument.is_connected():
                self.visa_instrument.disconnect()
                self.connect_visa_btn.setText("连接")

    def _start_test(self):
        """开始测试"""
        channel = int(self.channel_combo.currentText())
        voltage = float(self.voltage_edit.text())
        current_limit = float(self.current_limit_edit.text())
        sampling_rate = int(self.sampling_rate_edit.text())

        self.visa_instrument.set_channel(channel)
        self.visa_instrument.set_voltage(voltage)
        self.visa_instrument.set_current_limit(current_limit)

        self.test_manager.start_test(
            visa_instrument=self.visa_instrument,
            sampling_rate=sampling_rate
        )

        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(True)

    def _stop_test(self):
        """停止测试"""
        self.test_manager.stop_test()
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)

    def _export_data(self):
        """导出数据"""
        self.test_manager.export_data()

    def _update_data(self, data):
        if self.current_instrument_ui == "power_analyser" and self.n6705c_analyser_ui:
            if data and isinstance(data, list) and len(data) == 4:
                dev_label = self.n6705c_analyser_ui.current_device
                for i, channel_data in enumerate(data):
                    voltage = channel_data.get('voltage', 0.0)
                    current = channel_data.get('current', 0.0)
                    self.n6705c_analyser_ui.update_channel_values(dev_label, i + 1, voltage, current)
            elif data and 'current' in data:
                dev_label = self.n6705c_analyser_ui.current_device
                current = data['current'][-1] if data['current'] else 0.0
                voltage = data['voltage'][-1] if data['voltage'] else 0.0
                self.n6705c_analyser_ui.update_channel_values(dev_label, 1, voltage, current)

        elif self.current_instrument_ui == "pmu_test" and self.pmu_test_ui:
            if data and isinstance(data, dict):
                test_type = data.get('test_type')
                result = data.get('result', {})
                if test_type:
                    self.pmu_test_ui.update_test_result(test_type, result)

        else:
            if data and isinstance(data, list) and len(data) == 4:
                for i, channel_data in enumerate(data):
                    if i < len(self.channels):
                        voltage = channel_data.get('voltage', 0.0)
                        current = channel_data.get('current', 0.0)
                        self.channels[i]['voltage_value'].setText(f"{voltage:.4f}")
                        self.channels[i]['current_value'].setText(f"{current:.4f}")
            elif data and 'current' in data:
                if self.channels:
                    current = data['current'][-1] if data['current'] else 0.0
                    voltage = data['voltage'][-1] if data['voltage'] else 0.0
                    self.channels[0]['voltage_value'].setText(f"{voltage:.4f}")
                    self.channels[0]['current_value'].setText(f"{current:.4f}")

    def _cleanup_sub_ui(self, sub_ui, name):
        try:
            if hasattr(sub_ui, 'cleanup_threads') and callable(sub_ui.cleanup_threads):
                logger.info(f"[CloseEvent] Cleaning up threads: {name}")
                sub_ui.cleanup_threads()
        except Exception as e:
            logger.warning(f"[CloseEvent] Error cleaning up threads for {name}: {e}")

        try:
            if hasattr(sub_ui, 'test_worker') and sub_ui.test_worker is not None:
                logger.info(f"[CloseEvent] Stopping test worker: {name}")
                if hasattr(sub_ui.test_worker, 'request_stop'):
                    sub_ui.test_worker.request_stop()
                elif hasattr(sub_ui.test_worker, 'stop'):
                    sub_ui.test_worker.stop()
            if hasattr(sub_ui, '_test_worker') and sub_ui._test_worker is not None:
                logger.info(f"[CloseEvent] Stopping test worker: {name}")
                if hasattr(sub_ui._test_worker, 'request_stop'):
                    sub_ui._test_worker.request_stop()
                elif hasattr(sub_ui._test_worker, 'stop'):
                    sub_ui._test_worker.stop()
            if hasattr(sub_ui, 'test_thread') and sub_ui.test_thread is not None:
                logger.info(f"[CloseEvent] Waiting for test thread to finish: {name}")
                sub_ui.test_thread.quit()
                sub_ui.test_thread.wait(3000)
                sub_ui.test_thread = None
        except Exception as e:
            logger.warning(f"[CloseEvent] Error stopping test thread for {name}: {e}")

        try:
            if hasattr(sub_ui, 'n6705c') and sub_ui.n6705c is not None:
                logger.info(f"[CloseEvent] Disconnecting N6705C instrument: {name}")
                if hasattr(sub_ui.n6705c, 'instr') and sub_ui.n6705c.instr:
                    sub_ui.n6705c.instr.close()
                sub_ui.n6705c = None
        except Exception as e:
            logger.warning(f"[CloseEvent] Error disconnecting N6705C for {name}: {e}")

        try:
            if hasattr(sub_ui, 'Osc_ins') and sub_ui.Osc_ins is not None:
                logger.info(f"[CloseEvent] Disconnecting oscilloscope instrument: {name}")
                osc = sub_ui.Osc_ins
                sub_ui.Osc_ins = None
                sub_ui.scope_connected = False
                if hasattr(osc, 'disconnect'):
                    osc.disconnect()
                elif hasattr(osc, 'instrument') and osc.instrument:
                    osc.instrument.close()
        except Exception as e:
            logger.warning(f"[CloseEvent] Error disconnecting oscilloscope for {name}: {e}")

        try:
            if hasattr(sub_ui, 'rm') and sub_ui.rm is not None:
                logger.info(f"[CloseEvent] Closing VISA ResourceManager: {name}")
                sub_ui.rm.close()
                sub_ui.rm = None
        except Exception as e:
            logger.warning(f"[CloseEvent] Error closing ResourceManager for {name}: {e}")

    def closeEvent(self, event):
        logger.info("[CloseEvent] Window close requested, disconnecting all instruments...")

        if self.n6705c_top:
            logger.info("[CloseEvent] Disconnecting N6705C Top (all channels)...")
            try:
                self.n6705c_top.disconnect_all()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting N6705C Top: {e}")

        if self.mso64b_top and self.mso64b_top.is_connected:
            scope_type = getattr(self.mso64b_top, 'scope_type', 'MSO64B') or 'oscilloscope'
            logger.info(f"[CloseEvent] Disconnecting {scope_type} oscilloscope...")
            try:
                self.mso64b_top.disconnect()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting {scope_type}: {e}")

        if self.oscilloscope_ui and self.oscilloscope_ui.controller.is_connected:
            logger.info("[CloseEvent] Disconnecting oscilloscope controller...")
            try:
                self.oscilloscope_ui.controller.disconnect_instrument()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting oscilloscope controller: {e}")

        if self.visa_instrument:
            logger.info("[CloseEvent] Disconnecting VISA instrument...")
            try:
                self.visa_instrument.disconnect()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error disconnecting VISA instrument: {e}")

        if self.vt6002_chamber:
            logger.info("[CloseEvent] Closing VT6002 chamber...")
            try:
                self.vt6002_chamber.close()
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing VT6002 chamber: {e}")
            self.vt6002_chamber = None

        if self.vt6002_chamber_ui is not None:
            try:
                if self.vt6002_chamber_ui.vt6002 is not None:
                    logger.info("[CloseEvent] Closing VT6002 chamber UI instrument...")
                    self.vt6002_chamber_ui.vt6002.close()
                    self.vt6002_chamber_ui.vt6002 = None
            except Exception as e:
                logger.warning(f"[CloseEvent] Error closing VT6002 chamber UI: {e}")

        if self.consumption_test_ui is not None:
            self._cleanup_sub_ui(self.consumption_test_ui, "ConsumptionTestUI")

        for ui_name, ui_widget in [
            ("N6705CAnalyserUI", self.n6705c_analyser_ui),
            ("N6705CDatalogUI", self.n6705c_datalog_ui),
        ]:
            if ui_widget is not None and hasattr(ui_widget, 'rm') and ui_widget.rm is not None:
                logger.info(f"[CloseEvent] Closing VISA ResourceManager: {ui_name}")
                try:
                    ui_widget.rm.close()
                except Exception as e:
                    logger.warning(f"[CloseEvent] Error closing ResourceManager for {ui_name}: {e}")
                ui_widget.rm = None

        if self.pmu_test_ui is not None:
            for attr in [
                'dcdc_efficiency_ui', 'output_voltage_ui',
                'is_gain_ui', 'oscp_ui', 'gpadc_test_ui', 'clk_test_ui',
            ]:
                sub_ui = getattr(self.pmu_test_ui, attr, None)
                if sub_ui is not None:
                    self._cleanup_sub_ui(sub_ui, f"PMU.{attr}")

        if self.charger_test_ui is not None:
            for attr in [
                'config_traverse_ui', 'status_register_ui',
                'iterm_ui', 'regulation_voltage_ui',
            ]:
                sub_ui = getattr(self.charger_test_ui, attr, None)
                if sub_ui is not None:
                    self._cleanup_sub_ui(sub_ui, f"Charger.{attr}")

        logger.info("[CloseEvent] All instruments disconnected, closing window.")
        super().closeEvent(event)
