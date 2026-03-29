#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QLineEdit, QGridLayout,
    QTabWidget, QStatusBar, QCheckBox, QSplitter, QFrame, QButtonGroup,
    QGraphicsDropShadowEffect
)

from PySide6.QtCore import Qt, Signal, QEvent, QPoint, QTimer
from PySide6.QtGui import QPalette, QColor, QFont
from ui.plot_widget import PlotWidget
from ui.mso64b_ui import MSO64BUI
from ui.n6705c_ui import N6705CUI
from ui.n6705c_double_ui import N6705CDoubleUI
from ui.n6705c_datalog_ui import N6705CDatalogUI
from ui.pmu_test_ui import PMUTestUI
from ui.vt6002_chamber_ui import VT6002ChamberUI
from ui.sidebar_nav_button import SidebarNavButton
from ui.consumption_test import ConsumptionTestUI
from core.test_manager import TestManager
from instruments.visa_instrument import VisaInstrument
from instruments.ch341t import CH341T
from instruments.mso64b import MSO64B
from instruments.vt6002_chamber import VT6002


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
            ("threshold", "Threshold"),
            ("is_gain", "Is_gain"),
            ("oscp", "OSCP"),
            ("gpadc_test", "GPADC Test"),
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
            ("single", "Single N6705C"),
            ("double", "Double N6705C (A+B)"),
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
        self.ch341t = CH341T()
        self.mso64b_instrument = None
        self.vt6002_chamber = None

        # 初始化UI组件
        self.n6705c_ui = None
        self.n6705c_double_ui = None
        self.n6705c_datalog_ui = None
        self.mso64b_ui = None
        self.pmu_test_ui = None
        self.vt6002_chamber_ui = None
        self.consumption_test_ui = None
        self.current_instrument_ui = None
        self.channels = []

        # PMU菜单状态
        self.pmu_submenu = None
        self._pmu_btn_hovered = False
        self.current_pmu_test_key = None

        self.pa_submenu = None
        self._pa_btn_hovered = False
        self.current_pa_mode = "single"
        self.pmu_test_tab_map = {
            "dcdc_efficiency": 0,
            "output_voltage": 1,
            "threshold": 2,
            "is_gain": 3,
            "oscp": 4,
            "gpadc_test": 5,
        }

        # 设置样式
        self._setup_style()

        # 创建主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建顶部状态栏
        self._create_status_bar()

        # 创建主内容区域
        self._create_main_content()

        # 创建PMU二级菜单
        self._create_pmu_submenu()

        self._create_pa_submenu()

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
            QCheckBox {
                color: #c8c8c8;
            }
            QStatusBar {
                background-color: #16181c;
                color: #c8c8c8;
                border-top: 1px solid #333;
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
        """)

    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.visa_status = QLabel("VISA: 未连接")
        self.ch341t_status = QLabel("CH341T: 未连接")

        self.status_bar.addWidget(self.visa_status)
        self.status_bar.addWidget(self.ch341t_status)

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
        self.power_analyzer_btn = SidebarNavButton(
            "N6705C Power\nAnalyzer",
            "",
            "⚡"
        )
        self.power_analyzer_btn.setChecked(True)

        self.oscilloscope_btn = SidebarNavButton(
            "MSO64B Oscilloscope",
            "",
            "∿"
        )

        self.thermal_chamber_btn = SidebarNavButton(
            "VT6002 Thermal\nChamber",
            "",
            "🔥"
        )

        left_nav_layout.addWidget(self.power_analyzer_btn)
        left_nav_layout.addWidget(self.oscilloscope_btn)
        left_nav_layout.addWidget(self.thermal_chamber_btn)

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

        self.pmu_auto_test_btn = SidebarNavButton(
            "PMU Auto Test",
            "",
            "⚙"
        )
        left_nav_layout.addWidget(self.pmu_auto_test_btn)

        self.consumption_test_btn = SidebarNavButton(
            "Consumption Test",
            "",
            "⚡"
        )
        left_nav_layout.addWidget(self.consumption_test_btn)

        # 单选组
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.power_analyzer_btn)
        self.nav_button_group.addButton(self.oscilloscope_btn)
        self.nav_button_group.addButton(self.thermal_chamber_btn)
        self.nav_button_group.addButton(self.pmu_auto_test_btn)
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

        self.download_btn = QPushButton("〉_ Download Python Code")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet("""
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
        bottom_layout.addWidget(self.download_btn)

        visa_status_widget = QWidget()
        visa_status_widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        visa_status_layout = QHBoxLayout(visa_status_widget)
        visa_status_layout.setContentsMargins(0, 0, 0, 0)
        visa_status_layout.setSpacing(8)

        self.visa_status_dot = QLabel("●")
        self.visa_status_dot.setStyleSheet("""
            QLabel {
                color: #00d38a;
                font-size: 16px;
                border: none;
                background: transparent;
            }
        """)

        self.visa_status_label = QLabel("VISA Server Connected")
        self.visa_status_label.setStyleSheet("""
            QLabel {
                color: #9fd3c7;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)

        visa_status_layout.addWidget(self.visa_status_dot)
        visa_status_layout.addWidget(self.visa_status_label)
        visa_status_layout.addStretch()
        bottom_layout.addWidget(visa_status_widget)
        left_nav_layout.addWidget(bottom_widget)

        main_splitter.addWidget(self.left_nav)

        # 右侧主内容区域
        self.right_content = QWidget()
        self.right_content_layout = QVBoxLayout(self.right_content)
        self.right_content_layout.setContentsMargins(0, 0, 0, 0)

        self.instrument_ui_container = QWidget()
        self.instrument_ui_container_layout = QVBoxLayout(self.instrument_ui_container)
        self.instrument_ui_container_layout.setContentsMargins(0, 0, 0, 0)

        self._create_power_analyzer_ui()
        self.right_content_layout.addWidget(self.instrument_ui_container)

        main_splitter.addWidget(self.right_content)
        main_splitter.setSizes([280, 920])

        self.main_layout.addWidget(main_splitter)

    def _refresh_nav_arrow_state(self):
        """刷新左侧导航按钮最右侧箭头显示状态：只有选中项显示"""
        nav_buttons = [
            self.power_analyzer_btn,
            self.oscilloscope_btn,
            self.thermal_chamber_btn,
            self.pmu_auto_test_btn,
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

        self.pmu_auto_test_btn.installEventFilter(self)
        self.pmu_submenu.installEventFilter(self)

    def _create_pa_submenu(self):
        self.pa_submenu = PowerAnalyzerSubMenu(self)
        self.pa_submenu.item_clicked.connect(self._on_pa_submenu_clicked)

        self.power_analyzer_btn.installEventFilter(self)
        self.pa_submenu.installEventFilter(self)

    def _show_pa_submenu(self):
        if not self.pa_submenu:
            return

        btn_global_pos = self.power_analyzer_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.power_analyzer_btn.width() + 8
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
        self.power_analyzer_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        if mode_key == "single":
            self._create_power_analyzer_ui()
        elif mode_key == "double":
            self._create_power_analyzer_double_ui()
        elif mode_key == "datalog":
            self._create_datalog_ui()
        self.pa_submenu.hide()

    def _show_pmu_submenu(self):
        """显示PMU二级菜单"""
        if not self.pmu_submenu:
            return

        btn_global_pos = self.pmu_auto_test_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.pmu_auto_test_btn.width() + 8
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

    def eventFilter(self, obj, event):
        if obj == self.pmu_auto_test_btn:
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

        elif obj == self.power_analyzer_btn:
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

        return super().eventFilter(obj, event)

    def _create_power_analyzer_ui(self):
        self._clear_instrument_ui_container()

        self.n6705c_ui = N6705CUI()
        self.instrument_ui_container_layout.addWidget(self.n6705c_ui)
        self.current_instrument_ui = "power_analyzer"

        self.channels = self.n6705c_ui.channels if hasattr(self.n6705c_ui, 'channels') else []

    def _create_power_analyzer_double_ui(self):
        self._clear_instrument_ui_container()

        self.n6705c_double_ui = N6705CDoubleUI()
        self.instrument_ui_container_layout.addWidget(self.n6705c_double_ui)
        self.current_instrument_ui = "power_analyzer_double"

    def _create_datalog_ui(self):
        self._clear_instrument_ui_container()

        self.n6705c_datalog_ui = N6705CDatalogUI()
        self.instrument_ui_container_layout.addWidget(self.n6705c_datalog_ui)
        self.current_instrument_ui = "datalog"

    def _create_oscilloscope_ui(self):
        """创建示波器UI"""
        self._clear_instrument_ui_container()

        self.mso64b_ui = MSO64BUI()
        self.mso64b_ui.connect_btn.clicked.connect(self._connect_mso64b)
        self.mso64b_ui.disconnect_btn.clicked.connect(self._disconnect_mso64b)
        self.mso64b_ui.measure_btn.clicked.connect(self._measure_mso64b)

        self.instrument_ui_container_layout.addWidget(self.mso64b_ui)
        self.current_instrument_ui = "oscilloscope"

    def _create_thermal_chamber_ui(self):
        """创建温箱UI"""
        self._clear_instrument_ui_container()

        self.vt6002_chamber_ui = VT6002ChamberUI()
        self.instrument_ui_container_layout.addWidget(self.vt6002_chamber_ui)
        self.current_instrument_ui = "thermal_chamber"

    def _create_pmu_test_ui(self, selected_test=None):
        """创建PMU测试UI，并切换到指定测试页"""
        if self.current_instrument_ui != "pmu_test" or self.pmu_test_ui is None:
            self._clear_instrument_ui_container()
            self.pmu_test_ui = PMUTestUI()
            self.instrument_ui_container_layout.addWidget(self.pmu_test_ui)
            self.current_instrument_ui = "pmu_test"
        if selected_test in self.pmu_test_tab_map:
            self.current_pmu_test_key = selected_test
            if hasattr(self.pmu_test_ui, "set_current_test"):
                self.pmu_test_ui.set_current_test(selected_test)

    def _create_consumption_test_ui(self):
        """创建功耗测试UI"""
        self._clear_instrument_ui_container()

        self.consumption_test_ui = ConsumptionTestUI()
        self.instrument_ui_container_layout.addWidget(self.consumption_test_ui)
        self.current_instrument_ui = "consumption_test"

    def _on_pmu_submenu_clicked(self, test_key):
        """点击PMU二级菜单项"""
        self.current_pmu_test_key = test_key
        self.pmu_submenu.set_current_item(test_key)
        self.pmu_auto_test_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._create_pmu_test_ui(selected_test=test_key)
        self.pmu_submenu.hide()

    def _clear_instrument_ui_container(self):
        """清空仪器UI容器"""
        while self.instrument_ui_container_layout.count() > 0:
            widget = self.instrument_ui_container_layout.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()

    def _connect_signals(self):
        """连接信号槽"""
        self.power_analyzer_btn.clicked.connect(self._on_nav_button_clicked)
        self.oscilloscope_btn.clicked.connect(self._on_nav_button_clicked)
        self.thermal_chamber_btn.clicked.connect(self._on_nav_button_clicked)
        self.pmu_auto_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.consumption_test_btn.clicked.connect(self._on_nav_button_clicked)

        self.download_btn.clicked.connect(self._on_download_code)
        self.test_manager.data_updated.connect(self._update_data)

    def _on_nav_button_clicked(self):
        sender = self.sender()

        if sender == self.power_analyzer_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            self._show_pa_submenu()
            if self.current_pa_mode == "double":
                self._create_power_analyzer_double_ui()
            elif self.current_pa_mode == "datalog":
                self._create_datalog_ui()
            else:
                self._create_power_analyzer_ui()

        elif sender == self.oscilloscope_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.pa_submenu:
                self.pa_submenu.hide()
            self._create_oscilloscope_ui()

        elif sender == self.thermal_chamber_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.pa_submenu:
                self.pa_submenu.hide()
            self._create_thermal_chamber_ui()

        elif sender == self.pmu_auto_test_btn:
            if self.pa_submenu:
                self.pa_submenu.hide()
            self._create_pmu_test_ui(selected_test=self.current_pmu_test_key)
            self._show_pmu_submenu()

        elif sender == self.consumption_test_btn:
            if self.pmu_submenu:
                self.pmu_submenu.hide()
            if self.pa_submenu:
                self.pa_submenu.hide()
            self._create_consumption_test_ui()

        self._refresh_nav_arrow_state()

    def _on_download_code(self):
        """下载代码按钮点击事件"""
        print("Download Python Code clicked")

    def _connect_mso64b(self):
        """连接MSO64B示波器"""
        if not self.mso64b_ui:
            return

        connection_info = self.mso64b_ui.get_connection_info()
        ip_address = connection_info.get('ip_address')

        try:
            self.mso64b_instrument = MSO64B(ip_address)
            instrument_info = self.mso64b_instrument.identify_instrument()
            self.mso64b_ui.update_connection_status(True, instrument_info)
            self.visa_status.setText(f"示波器: 已连接 - {ip_address}")
        except Exception as e:
            print(f"连接示波器失败: {str(e)}")
            self.mso64b_ui.update_connection_status(False)
            self.visa_status.setText("示波器: 连接失败")

    def _disconnect_mso64b(self):
        """断开MSO64B示波器"""
        if self.mso64b_instrument:
            self.mso64b_instrument.disconnect()
            self.mso64b_instrument = None

        if self.mso64b_ui:
            self.mso64b_ui.update_connection_status(False)

        self.visa_status.setText("示波器: 未连接")

    def _measure_mso64b(self):
        """执行MSO64B测量"""
        if not self.mso64b_instrument or not self.mso64b_ui:
            return

        try:
            measure_settings = self.mso64b_ui.get_measure_settings()
            channel = measure_settings.get('channel')
            measure_type = measure_settings.get('type')

            if measure_type == 'MEAN':
                result = self.mso64b_instrument.get_channel_mean(channel)
            elif measure_type == 'PK2PK':
                result = self.mso64b_instrument.get_channel_pk2pk(channel)
            else:
                return

            self.mso64b_ui.update_measure_result(measure_type, result)
        except Exception as e:
            print(f"测量失败: {str(e)}")

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
                self.visa_status.setText(f"VISA: 已连接 - {device}")
                self.connect_visa_btn.setText("断开")
            else:
                self.visa_status.setText("VISA: 连接失败")
        else:
            if self.visa_instrument.is_connected():
                self.visa_instrument.disconnect()
                self.visa_status.setText("VISA: 未连接")
                self.connect_visa_btn.setText("连接")

    def _scan_ch341t(self):
        """扫描 CH341T 端口"""
        ports = self.ch341t.scan_ports()
        self.ch341t_combo.clear()
        self.ch341t_combo.addItems(ports)

    def _connect_ch341t(self):
        """连接 CH341T"""
        port = self.ch341t_combo.currentText()
        if port:
            success = self.ch341t.connect(port)
            if success:
                self.ch341t_status.setText(f"CH341T: 已连接 - {port}")
                self.connect_ch341t_btn.setText("断开")
            else:
                self.ch341t_status.setText("CH341T: 连接失败")
        else:
            if self.ch341t.is_connected():
                self.ch341t.disconnect()
                self.ch341t_status.setText("CH341T: 未连接")
                self.connect_ch341t_btn.setText("连接")

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

        self.start_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)

    def _stop_test(self):
        """停止测试"""
        self.test_manager.stop_test()
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)

    def _send_iic_command(self):
        """发送 IIC 指令"""
        command = self.iic_command_edit.text()
        if self.ch341t.is_connected():
            self.ch341t.send_command(command)

    def _export_data(self):
        """导出数据"""
        self.test_manager.export_data()

    def _update_data(self, data):
        """更新数据"""
        if self.current_instrument_ui == "power_analyzer" and self.n6705c_ui:
            if data and isinstance(data, list) and len(data) == 4:
                for i, channel_data in enumerate(data):
                    voltage = channel_data.get('voltage', 0.0)
                    current = channel_data.get('current', 0.0)
                    self.n6705c_ui.update_channel_values(i + 1, voltage, current)
            elif data and 'current' in data:
                current = data['current'][-1] if data['current'] else 0.0
                voltage = data['voltage'][-1] if data['voltage'] else 0.0
                self.n6705c_ui.update_channel_values(1, voltage, current)

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
                    