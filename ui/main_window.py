#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

import os
import sys
import time
from resource_path import get_resource_base

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QSplitter, QFrame, QDialog, QTextBrowser, QGraphicsOpacityEffect,
    QApplication
)

from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QEvent,
    QSettings, QRect,
)

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    _WM_NCHITTEST = 0x0084
    _WM_NCCALCSIZE = 0x0083
    _WM_GETMINMAXINFO = 0x0024
    _WM_SYSCOMMAND = 0x0112
    _WM_NCRBUTTONUP = 0x00A5
    _TPM_RETURNCMD = 0x0100
    _TPM_LEFTALIGN = 0x0000
    _TPM_TOPALIGN = 0x0000
    _HTCLIENT = 1
    _HTCAPTION = 2
    _HTLEFT = 10
    _HTRIGHT = 11
    _HTTOP = 12
    _HTTOPLEFT = 13
    _HTTOPRIGHT = 14
    _HTBOTTOM = 15
    _HTBOTTOMLEFT = 16
    _HTBOTTOMRIGHT = 17

    _GWL_STYLE = -16
    _WS_CAPTION = 0x00C00000
    _WS_THICKFRAME = 0x00040000
    _WS_MINIMIZEBOX = 0x00020000
    _WS_MAXIMIZEBOX = 0x00010000
    _WS_SYSMENU = 0x00080000

    _MONITOR_DEFAULTTONEAREST = 0x00000002

    _SWP_NOSIZE = 0x0001
    _SWP_NOMOVE = 0x0002
    _SWP_NOZORDER = 0x0004
    _SWP_NOACTIVATE = 0x0010
    _SWP_FRAMECHANGED = 0x0020

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class _MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", _RECT),
            ("rcWork", _RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    class _MINMAXINFO(ctypes.Structure):
        _fields_ = [
            ("ptReserved", ctypes.wintypes.POINT),
            ("ptMaxSize", ctypes.wintypes.POINT),
            ("ptMaxPosition", ctypes.wintypes.POINT),
            ("ptMinTrackSize", ctypes.wintypes.POINT),
            ("ptMaxTrackSize", ctypes.wintypes.POINT),
        ]

    class _NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [("rgrc", _RECT * 3)]

    _DWMWA_WINDOW_CORNER_PREFERENCE = 33
    _DWMWA_BORDER_COLOR = 34
    _DWMWCP_ROUND = 2
    _WINDOW_BORDER_COLOR = 0x00403420  # COLORREF 0x00BBGGRR -> 边框 #203440
from PySide6.QtGui import QPalette, QColor, QFont, QPixmap
from ui.pages.oscilloscope.oscilloscope_base_ui import OscilloscopeBaseUI
from ui.pages.power_analyzer.power_analyzer_suite_ui import N6705CSuiteWindow
from ui.pages.power_analyzer.power_analyzer_top import N6705CTop
from ui.pages.oscilloscope.mso64b_top import MSO64BTop
from ui.pages.pmu_test.pmu_test_ui import PMUTestUI
from ui.pages.chamber.chamber_control_ui import ChamberControlUI
from ui.pages.consumption_test.consumption_test_wrapper import ConsumptionTestWrapper
from ui.pages.charger_test.charger_test_ui import ChargerTestUI
from ui.pages.module_test.module_test_ui import ModuleTestUI
from ui.pages.orchestrator.orchestrator_ui import OrchestratorUI
from ui.pages.vmin_hunter.vmin_hunter_container import VminHunterContainerUI
from ui.pages.pmu.pmu_1811 import Pmu1811UI
from ui.pages.pmu.pmu_1860_ui import Pmu1860UI
from ui.pages.gpio.gpio_control_ui import GpioControlUI
from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin
from ui.modules.mcu_io_module_frame import McuIoConnectionMixin
from ui.modules.IIC_Module.i2c_mixin import I2cMixin
from ui.modules.IIC_Module.i2c_styles import _I2C_DARK_STYLE
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from core.test_manager import TestManager
from core.instruments import InstrumentManager, InstrumentSpec, ConnectionHub
from instruments.base.visa_instrument import VisaInstrument
from ui.styles import SCROLLBAR_STYLE
from ui.nav_controller import NavController
from ui.instrument_status import InstrumentStatusPanel
from ui.app_top_bar import AppTopBar
from ui.widgets.toast_notification import ToastNotification
from ui.ai.ai_assist_panel import AIAssistPanel
from ui.ai.panel_state import load_panel_state, save_panel_state, clamp_width
from core.ai.config import AISettings
from core.ai.ai_service import AIService
from ui.cleanup_mixin import CleanupMixin
from ui.main_window_ai_mixin import MainWindowAiMixin
from ui.standalone import resize_and_center_window
from log_config import get_logger
from version import APP_NAME, __version__
from debug_config import DEBUG_MOCK

logger = get_logger(__name__)

# 紧凑（最小）视图窗口尺寸：仅容纳 Quick Setup 面板（双设备列收紧后 ~590 + 页边距）
_COMPACT_VIEW_SIZE = (600, 200)

# 最小窗口尺寸（逻辑像素）：left_nav(187) + right_content(min 400) + AI 面板
# 可放的底线；低于 640 高时 left_nav 三段式（Logo/滚动区/状态面板）无法保证可读。
_MIN_WINDOW_SIZE = (966, 640)


class _KKSerialsPage(SerialComMixin, QWidget):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        from ui.modules.serialCom_module.serialCom_module_frame import MODE_FULL
        self.init_serial_connection(mode=MODE_FULL, prefix="KKSerials")
        self.setStyleSheet("""
            QWidget {
                background-color: #020817;
                color: #dbe7ff;
            }
            QLabel {
                background-color: transparent;
                color: #dbe7ff;
                border: none;
            }
            QLabel#statusOk {
                color: #15d1a3;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusWarn {
                color: #ffb84d;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusErr {
                color: #ff5e7a;
                font-weight: 600;
                background-color: transparent;
            }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.complete_serialComWidget(root)
        self._sc_on_refresh()
        self._sc_append_system("[INFO] KK Serials 已初始化")

    def append_log(self, msg):
        self._sc_append_system(msg)


class _I2cControlPage(I2cMixin, QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.init_i2c()
        self.setStyleSheet(_I2C_DARK_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.build_i2c_widgets(root)
        self.bind_i2c_signals()

    def closeEvent(self, event):
        try:
            self.close_i2c()
        except Exception:
            logger.error("I2C close failed", exc_info=True)
        super().closeEvent(event)


class _CollectionPage(McuIoConnectionMixin, QWidget):
    def __init__(self, parent=None, instrument_manager=None):
        QWidget.__init__(self, parent)
        self.init_mcu_io_connection(instrument_manager=instrument_manager)
        self.setStyleSheet("""
            QWidget {
                background-color: #020817;
                color: #dbe7ff;
            }
            QLabel {
                background-color: transparent;
                color: #dbe7ff;
                border: none;
            }
            QLabel#statusOk {
                color: #15d1a3;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusWarn {
                color: #ffb84d;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusErr {
                color: #ff5e7a;
                font-weight: 600;
                background-color: transparent;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(8)

        body_layout = QVBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.mcu_io_title_label = QLabel("MCU IO (CH9114F)")
        self.mcu_io_title_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        title_row.addWidget(self.mcu_io_title_label)
        title_row.addStretch(1)
        body_layout.addLayout(title_row)

        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background-color: #060f24; border: 1px solid #17345f;"
            " border-radius: 8px; }"
        )
        panel.setMaximumWidth(380)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(6)
        self.build_mcu_io_connection_widgets(panel_layout, title_row=title_row)

        content_row = QHBoxLayout()
        content_row.addWidget(panel, 0, Qt.AlignTop)
        content_row.addStretch(1)
        body_layout.addLayout(content_row)
        body_layout.addStretch(1)

        body_widget = QWidget()
        body_widget.setStyleSheet("background: transparent; border: none;")
        body_widget.setLayout(body_layout)

        self.execution_logs = ExecutionLogsFrame(
            title="MCU IO Logs", show_progress=False
        )

        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: transparent; }
            QSplitter::handle:hover { background-color: #18284d; }
            QSplitter::handle:pressed { background-color: #5b7cff; }
        """)
        splitter.addWidget(body_widget)
        splitter.addWidget(self.execution_logs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([600, 140])

        root.addWidget(splitter, 1)

        self.bind_mcu_io_signals()

    def append_log(self, msg):
        self.execution_logs.append_log(msg)

    def _on_mcu_io_type_changed_extra(self):
        # MCU 类型切换时同步页面标题
        mcu_type = self._current_mcu_io_type()
        label = "YD-RP2040" if mcu_type == "yd_rp2040" else "CH9114F"
        if hasattr(self, "mcu_io_title_label"):
            self.mcu_io_title_label.setText(f"MCU IO ({label})")


class MainWindow(MainWindowAiMixin, CleanupMixin, QMainWindow):

    def __init__(self, with_ai: bool = True):
        super().__init__()
        _init_t0 = time.perf_counter()
        _init_last = [_init_t0]

        def _init_tick(label):
            now = time.perf_counter()
            logger.info("[STARTUP]   MainWindow: %-28s +%7.3f s (ctor %6.3f s)",
                        label, now - _init_last[0], now - _init_t0)
            _init_last[0] = now

        self.with_ai = with_ai
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        if sys.platform == "win32":
            self.setWindowFlags(Qt.Window)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._resize_border = 6
        self._resize_edge = None
        self._resize_origin = None
        self.setMouseTracking(True)
        resize_and_center_window(self)
        self.setMinimumSize(*_MIN_WINDOW_SIZE)
        self._restore_window_geometry()

        _init_tick("窗口标志/几何初始化")

        self.test_manager = TestManager()
        self.visa_instrument = VisaInstrument()
        self.chamber = None

        self.instrument_manager = InstrumentManager(parent=self)
        _init_tick("TestManager/VisaInstrument/InstrumentManager")

        self.n6705c_top = N6705CTop(self)
        self.mso64b_top = MSO64BTop(self)
        _init_tick("N6705CTop/MSO64BTop")
        self.connection_hub = ConnectionHub(
            self.instrument_manager,
            self.n6705c_top,
            self.mso64b_top,
            parent=self,
        )
        _init_tick("ConnectionHub")

        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C, MockMSO64B
            logger.info("[MOCK] Auto-connecting mock instruments...")
            mock_a = MockN6705C()
            mock_b = MockN6705C()
            mock_scope = MockMSO64B()
            self.n6705c_top.connect_a("MOCK::N6705C::A", mock_a, "MOCK-A")
            self.n6705c_top.connect_b("MOCK::N6705C::B", mock_b, "MOCK-B")
            self.mso64b_top.connect_instrument("MOCK::MSO64B", mock_scope, "MSO64B")
            _init_tick("DEBUG_MOCK 自动连接")

        self.n6705c_suite_ui = None
        self.n6705c_analyser_ui = None
        self.n6705c_datalog_ui = None
        self.oscilloscope_ui = None
        self.pmu_test_ui = None
        self.chamber_ui = None
        self.consumption_test_ui = None
        self.charger_test_ui = None
        self.module_test_ui = None
        self.orchestrator_ui = None
        self.vmin_hunter_ui = None
        self.kk_serials_ui = None
        self.collection_ui = None
        self.i2c_control_ui = None
        self.pmu_1811_ui = None
        self.pmu_1860_ui = None
        self.gpio_ui = None
        self.current_instrument_ui = None
        self._page_switch_geometry = None
        # 紧凑（最小）视图状态：True = 仅 Quick Setup 小窗
        self._compact_view = False
        self._pre_compact_state = None
        self._compact_ai_was_open = False
        self.channels = []

        self.nav = NavController(self)
        self.status_panel = InstrumentStatusPanel(self)
        _init_tick("NavController/InstrumentStatusPanel")

        if self.with_ai:
            self.ai_settings = AISettings.load()
            self.ai_service = AIService(
                self.ai_settings,
                page_key_getter=self._get_ai_page_key,
                parent=self,
            )
            self.ai_service.set_serial_status_getter(self._get_ai_serial_status)
            self.ai_service.set_execution_logs_getter(self._get_ai_execution_logs)
        else:
            self.ai_settings = None
            self.ai_service = None
        _init_tick("AISettings/AIService")
        self.ai_panel = None
        self.outer_splitter = None

        self._setup_style()
        _init_tick("_setup_style")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._create_main_content()
        _init_tick("_create_main_content")
        self.nav.create_submenus()
        _init_tick("nav.create_submenus")
        self._connect_signals()
        _init_tick("_connect_signals")

    def _setup_style(self):
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
                border-radius: 8px;
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
                border-radius: 6px;
                padding: 6px 12px;
                background-color: #32353a;
                color: #c8c8c8;
                outline: none;
            }
            QPushButton:hover {
                background-color: #3a3d43;
            }
            QPushButton:focus {
                outline: none;
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
                border-radius: 6px;
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
                border-radius: 6px;
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
                border-radius: 6px;
                background-color: #020618;
            }
            QSpinBox, QDoubleSpinBox {
                border: 1px solid #555;
                border-radius: 6px;
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
        _cmc_t0 = time.perf_counter()
        _cmc_last = [_cmc_t0]

        def _cmc_tick(label):
            now = time.perf_counter()
            logger.info("[STARTUP]     _create_main_content: %-24s +%7.3f s (total %6.3f s)",
                        label, now - _cmc_last[0], now - _cmc_t0)
            _cmc_last[0] = now

        main_splitter = QSplitter(Qt.Horizontal)

        left_nav, left_nav_layout = self.nav.create_left_nav()
        bottom_widget = self.status_panel.create_bottom_widget()
        _cmc_tick("create_left_nav/bottom_widget")
        left_nav_layout.addWidget(bottom_widget)
        self.left_nav = left_nav

        main_splitter.addWidget(self.left_nav)

        self.right_content = QWidget()
        self.right_content.setMinimumWidth(400)
        self.right_content_layout = QVBoxLayout(self.right_content)
        self.right_content_layout.setContentsMargins(0, 0, 0, 0)

        self.instrument_ui_container = QWidget()
        self.instrument_ui_container_layout = QVBoxLayout(self.instrument_ui_container)
        self.instrument_ui_container_layout.setContentsMargins(0, 0, 0, 0)

        self._create_n6705c_suite_ui()
        _cmc_tick("_create_n6705c_suite_ui (N6705C首页)")
        self.right_content_layout.addWidget(self.instrument_ui_container)

        main_splitter.addWidget(self.right_content)
        # 初始比例 187 : 剩余（默认窗口 1600 宽 → 1413），不依赖内容撑开
        main_splitter.setSizes([187, 1413])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)
        self.main_splitter = main_splitter

        self.top_bar = AppTopBar(self)
        _cmc_tick("AppTopBar")
        self.top_bar.compact_view_button.toggled.connect(self._on_compact_view_toggled)
        self.top_bar.pin_button.toggled.connect(self._on_pin_toggled)
        self.top_bar.capture_chart_button.clicked.connect(self._on_capture_chart)
        self.top_bar.labels_button.clicked.connect(self._on_labels_button_toggled)
        self.main_layout.addWidget(self.top_bar)
        # 默认首页（N6705C）装载早于 top_bar 创建，_fade_in_widget 时
        # top_bar 尚不存在会跳过同步，此处补一次让缩略按钮正确显示
        self._sync_compact_view_button()
        self._sync_labels_toggle_button()

        self._setup_ai_panel(main_splitter)
        _cmc_tick("_setup_ai_panel")

    def _setup_ai_panel(self, main_splitter):
        if not self.with_ai:
            self.main_layout.addWidget(main_splitter)
            ai_button = getattr(self.top_bar, "ai_panel_button", None)
            if ai_button is not None:
                ai_button.setVisible(False)
            return

        outer_splitter = QSplitter(Qt.Horizontal)
        outer_splitter.setHandleWidth(1)
        outer_splitter.setStyleSheet("""
        QSplitter::handle {
            background-color: #1e293b;
        }
        QSplitter::handle:hover {
            background-color: #3b82f6;
        }
        """)
        outer_splitter.addWidget(main_splitter)

        self.ai_panel = AIAssistPanel(self.ai_service, parent=self)
        self.ai_panel.request_close.connect(self._on_ai_panel_close_requested)
        self.ai_panel.request_open.connect(self._on_ai_panel_open_requested)
        self.ai_panel.pick_requested.connect(self._on_pick_requested)
        self.ai_panel.set_config_apply_callback(self._apply_ai_config_draft)
        self._setup_ai_action_system()
        outer_splitter.addWidget(self.ai_panel)

        outer_splitter.setStretchFactor(0, 1)
        outer_splitter.setStretchFactor(1, 0)
        outer_splitter.setChildrenCollapsible(False)
        outer_splitter.setCollapsible(0, False)
        outer_splitter.setCollapsible(1, False)
        self.ai_panel.setMinimumWidth(260)
        self.outer_splitter = outer_splitter
        self.main_layout.addWidget(outer_splitter)

        panel_open, panel_width = load_panel_state()
        self._ai_panel_width = clamp_width(panel_width)

        if not self.ai_settings.enabled:
            self.top_bar.ai_panel_button.setVisible(False)
            self.ai_panel.setVisible(False)
        else:
            self.top_bar.ai_panel_button.toggled.connect(self._on_ai_panel_toggled)
            self.top_bar.ai_panel_button.setChecked(panel_open)
            self._apply_ai_panel_visibility(panel_open)
            self._setup_element_picker()

    def _setup_element_picker(self):
        from ui.ai.element_picker import ElementPicker

        self.element_picker = ElementPicker(
            self, on_pick=self._on_element_picked, parent=self
        )

    def _on_element_picked(self, label, content):
        if getattr(self, "ai_panel", None) is None:
            return
        self.ai_panel.attach_picked_context(label, content)

    def _on_pick_requested(self):
        if getattr(self, "element_picker", None) is None:
            return
        self.element_picker.start()

    def _on_ai_panel_open_requested(self):
        button = self.top_bar.ai_panel_button
        if button.isChecked():
            self._apply_ai_panel_visibility(True)
        else:
            button.setChecked(True)

    def _apply_ai_panel_visibility(self, visible):
        self.ai_panel.setVisible(visible)
        if visible:
            total = max(self.outer_splitter.width(), 800)
            self.outer_splitter.setSizes([total - self._ai_panel_width, self._ai_panel_width])

    def _on_ai_panel_toggled(self, checked):
        self._apply_ai_panel_visibility(checked)

    def _on_ai_panel_close_requested(self):
        self.top_bar.ai_panel_button.setChecked(False)

    def _current_active_page(self):
        mapping = {
            "kk_serials": getattr(self, "kk_serials_ui", None),
            "i2c_control": getattr(self, "i2c_control_ui", None),
            "pmu_1811": getattr(self, "pmu_1811_ui", None),
            "pmu_1860": getattr(self, "pmu_1860_ui", None),
            "orchestrator": getattr(self, "orchestrator_ui", None),
            "pmu_test": getattr(self, "pmu_test_ui", None),
            "charger_test": getattr(self, "charger_test_ui", None),
            "module_test": getattr(self, "module_test_ui", None),
            "consumption_test": getattr(self, "consumption_test_ui", None),
            "gpio": getattr(self, "gpio_ui", None),
        }
        return mapping.get(self.current_instrument_ui)

    # ------------------------------------------------------------------
    # 一键截图：当前页图表区域 → 系统剪贴板（顶栏截图按钮）
    #
    # 截图目标按鸭子类型解析，页面无需注册即可接入：
    #   0. 页面实现 get_capture_pixmap() → 返回页面自定义合成 QPixmap
    #      （最高优先级，适合"多区域合成"场景，如 GPADC 页性能指标+图表）；
    #   1. 页面实现 get_capture_widget() → 显式返回截图控件；
    #   2. 页面持有 chart_frame 属性（QWidget）→ 图表卡片区域
    #      （pmu_output_voltage / pmu_dcdc_efficiency / charger_test 各子页、
    #        n6705c_datalog 等均为此约定）；
    #   3. 兜底：整页截图。
    # ------------------------------------------------------------------
    def _resolve_capture_page(self):
        """返回当前活动页面对象（含 Tab 子页下钻），供图表截图定位控件。"""
        page = self.resolve_active_ai_page()
        if page is not None:
            return page
        attr_map = {
            "power_analyser": "n6705c_analyser_ui",
            "datalog": "n6705c_datalog_ui",
            "oscilloscope": "oscilloscope_ui",
            "chamber": "chamber_ui",
            "collection": "collection_ui",
            "kk_serials": "kk_serials_ui",
            "i2c_control": "i2c_control_ui",
            "pmu_1811": "pmu_1811_ui",
            "pmu_1860": "pmu_1860_ui",
        }
        key = self.current_instrument_ui
        return getattr(self, attr_map.get(key, f"{key}_ui"), None)

    def _on_capture_chart(self):
        page = self._resolve_capture_page()
        if page is None:
            self._show_capture_toast("当前无活动页面可截图", ToastNotification.TYPE_ERROR)
            return

        pixmap = None
        pixmap_getter = getattr(page, "get_capture_pixmap", None)
        if callable(pixmap_getter):
            try:
                pixmap = pixmap_getter()
            except Exception:  # noqa: BLE001 - 页面自定义合成异常时降级
                logger.error("get_capture_pixmap 执行失败", exc_info=True)
        if not isinstance(pixmap, QPixmap) or pixmap.isNull():
            pixmap = None
            target = None
            getter = getattr(page, "get_capture_widget", None)
            if callable(getter):
                try:
                    target = getter()
                except Exception:  # noqa: BLE001 - 页面自定义 getter 异常时降级
                    logger.error("get_capture_widget 执行失败", exc_info=True)
            if not isinstance(target, QWidget):
                target = getattr(page, "chart_frame", None)
            if not isinstance(target, QWidget):
                target = page
            try:
                pixmap = target.grab()
            except Exception:  # noqa: BLE001 - 截图/剪贴板失败转用户可读提示
                logger.error("图表截图复制到剪贴板失败", exc_info=True)
                self._show_capture_toast("截图失败，请查看日志", ToastNotification.TYPE_ERROR)
                return

        try:
            QApplication.clipboard().setPixmap(pixmap)
        except Exception:  # noqa: BLE001 - 剪贴板失败转用户可读提示
            logger.error("图表截图复制到剪贴板失败", exc_info=True)
            self._show_capture_toast("截图失败，请查看日志", ToastNotification.TYPE_ERROR)
            return

        logger.debug("Chart area captured: page=%s pixmap=%s size=%dx%d",
                     type(page).__name__, type(pixmap).__name__,
                     pixmap.width(), pixmap.height())
        self._show_capture_toast(
            "图表区域已复制到剪贴板", ToastNotification.TYPE_SUCCESS)

    def _show_capture_toast(self, message, toast_type):
        if not hasattr(self, "_capture_toast"):
            self._capture_toast = ToastNotification()
        self._capture_toast.show_toast(message, toast_type, self)

    def _connect_signals(self):
        self.nav.n6705c_power_analyzer_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.oscilloscope_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.chamber_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.pmu_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.charger_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.module_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.consumption_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.vmin_hunter_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.orchestrator_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.pmu_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.collection_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.gpio_btn.clicked.connect(self._on_nav_button_clicked)

        self.status_panel.help_btn.clicked.connect(self._on_help)
        self.test_manager.data_updated.connect(self._update_data)

        self.connection_hub.connection_changed.connect(self._update_instrument_status)

        self.nav.setup_shortcuts()

    def _on_nav_button_clicked(self):
        self.nav.handle_nav_button_clicked(self.sender())

    def eventFilter(self, obj, event):
        if self.nav.handle_event_filter(obj, event):
            return super().eventFilter(obj, event)
        return super().eventFilter(obj, event)

    def _create_n6705c_suite_ui(self):
        logger.debug("Switching to N6705C Suite UI")
        self._hide_all_instrument_uis()
        if self.n6705c_suite_ui is None:
            self.n6705c_suite_ui = N6705CSuiteWindow(
                n6705c_top=self.n6705c_top,
                instrument_manager=self.instrument_manager,
                ui_action_registry=getattr(self, "_ui_action_registry", None),
                standalone=False,
            )
            self.n6705c_suite_ui.page_changed.connect(self._on_suite_page_changed)
            self.instrument_ui_container_layout.addWidget(self.n6705c_suite_ui)
            # 子页引用：compact / AI 回调 / 截图链 / 功耗更新等既有代码直连
            self.n6705c_analyser_ui = self.n6705c_suite_ui.analyser_page
            self.n6705c_datalog_ui = self.n6705c_suite_ui.datalog_page
            self.n6705c_datalog_ui.labels_panel_toggled.connect(self._on_datalog_labels_toggled)
            self.n6705c_analyser_ui._sync_from_top()
            self.n6705c_datalog_ui._sync_from_top()
        else:
            self.n6705c_suite_ui.show()
        key = self.n6705c_suite_ui.current_page_key()
        self.current_instrument_ui = "power_analyser" if key == "analyser" else "datalog"
        self.channels = self.n6705c_analyser_ui.channels if hasattr(self.n6705c_analyser_ui, 'channels') else []
        self._fade_in_widget(self.n6705c_suite_ui)

    def _on_suite_page_changed(self, key):
        """suite 内 tab 切换：同步页面键（compact 按钮 / AI 上下文 / 帮助页随动）。"""
        self.current_instrument_ui = "power_analyser" if key == "analyser" else "datalog"
        if key == "analyser" and hasattr(self.n6705c_analyser_ui, 'channels'):
            self.channels = self.n6705c_analyser_ui.channels
        self._sync_compact_view_button()
        self._sync_labels_toggle_button()
        if getattr(self, "ai_service", None) is not None:
            self.ai_service.set_page_context(self._get_current_help_key())
            self._update_ai_apply_callbacks()
            if getattr(self, "ai_panel", None) is not None:
                self.ai_panel.refresh_quick_actions()
                self.ai_panel.on_page_changed()

    def _create_oscilloscope_ui(self):
        logger.debug("Switching to Oscilloscope UI")
        self._hide_all_instrument_uis()
        if self.oscilloscope_ui is None:
            self.oscilloscope_ui = OscilloscopeBaseUI(
                mso64b_top=self.mso64b_top,
                instrument_manager=self.instrument_manager,
            )
            self.oscilloscope_ui.connection_changed.connect(self._update_instrument_status)
            self.instrument_ui_container_layout.addWidget(self.oscilloscope_ui)
        else:
            self.oscilloscope_ui._sync_from_top()
            self.oscilloscope_ui.show()
        self.current_instrument_ui = "oscilloscope"
        self._fade_in_widget(self.oscilloscope_ui)

    def _create_thermal_chamber_ui(self):
        logger.debug("Switching to Thermal Chamber UI")
        self._hide_all_instrument_uis()
        if self.chamber_ui is None:
            self.chamber_ui = ChamberControlUI(
                instrument_manager=self.instrument_manager,
            )
            self.chamber_ui.connection_changed.connect(self._update_instrument_status)
            self.instrument_ui_container_layout.addWidget(self.chamber_ui)
        else:
            self.chamber_ui.show()
        self.current_instrument_ui = "thermal_chamber"
        self._fade_in_widget(self.chamber_ui)

    def _create_pmu_test_ui(self, selected_test=None):
        logger.debug("Switching to PMU Test UI: selected_test=%s", selected_test)
        self._hide_all_instrument_uis()
        if self.pmu_test_ui is None:
            self.pmu_test_ui = PMUTestUI(
                n6705c_top=self.n6705c_top,
                mso64b_top=self.mso64b_top,
                chamber_ui=self.chamber_ui,
                instrument_manager=self.instrument_manager,
                ui_action_registry=getattr(self, "_ui_action_registry", None),
            )
            self.instrument_ui_container_layout.addWidget(self.pmu_test_ui)
        else:
            self.pmu_test_ui._sync_from_top()
            self.pmu_test_ui.show()
        self.current_instrument_ui = "pmu_test"
        if selected_test in self.nav.pmu_test_tab_map:
            self.nav.current_pmu_test_key = selected_test
            if hasattr(self.pmu_test_ui, "set_current_test"):
                self.pmu_test_ui.set_current_test(selected_test)
        self._fade_in_widget(self.pmu_test_ui)

    def _create_consumption_test_ui(self, selected_test=None):
        logger.debug("Switching to Consumption Test UI: selected_test=%s", selected_test)
        self._hide_all_instrument_uis()
        if self.consumption_test_ui is None:
            try:
                self.consumption_test_ui = ConsumptionTestWrapper(
                    n6705c_top=self.n6705c_top,
                    instrument_manager=self.instrument_manager,
                    ui_action_registry=getattr(self, "_ui_action_registry", None),
                )
            except Exception:
                logger.error("Failed to create ConsumptionTestWrapper", exc_info=True)
                return
            self.instrument_ui_container_layout.addWidget(self.consumption_test_ui)
        else:
            self.consumption_test_ui.sync_n6705c_from_top()
            self.consumption_test_ui.show()
        self.current_instrument_ui = "consumption_test"
        if selected_test in self.nav.consumption_test_tab_map:
            self.nav.current_consumption_test_key = selected_test
            if hasattr(self.consumption_test_ui, "set_current_test"):
                self.consumption_test_ui.set_current_test(selected_test)
        self._fade_in_widget(self.consumption_test_ui)

    def _create_charger_test_ui(self, selected_test=None):
        logger.debug("Switching to Charger Test UI: selected_test=%s", selected_test)
        self._hide_all_instrument_uis()
        if self.charger_test_ui is None:
            self.charger_test_ui = ChargerTestUI(
                n6705c_top=self.n6705c_top,
                chamber_ui=self.chamber_ui,
                instrument_manager=self.instrument_manager,
                ui_action_registry=getattr(self, "_ui_action_registry", None),
            )
            self.instrument_ui_container_layout.addWidget(self.charger_test_ui)
        else:
            self.charger_test_ui._sync_from_top()
            self.charger_test_ui.show()
        self.current_instrument_ui = "charger_test"
        if selected_test in self.nav.charger_test_tab_map:
            self.nav.current_charger_test_key = selected_test
            if hasattr(self.charger_test_ui, "set_current_test"):
                self.charger_test_ui.set_current_test(selected_test)
        self._fade_in_widget(self.charger_test_ui)

    def _create_module_test_ui(self, selected_test=None):
        logger.debug("Switching to Module Test UI: selected_test=%s", selected_test)
        self._hide_all_instrument_uis()
        if self.module_test_ui is None:
            self.module_test_ui = ModuleTestUI(
                n6705c_top=self.n6705c_top,
                mso64b_top=self.mso64b_top,
                chamber_ui=self.chamber_ui,
                instrument_manager=self.instrument_manager,
                ui_action_registry=getattr(self, "_ui_action_registry", None),
            )
            self.instrument_ui_container_layout.addWidget(self.module_test_ui)
        else:
            self.module_test_ui._sync_from_top()
            self.module_test_ui.show()
        self.current_instrument_ui = "module_test"
        if selected_test in self.nav.module_test_tab_map:
            self.nav.current_module_test_key = selected_test
            if hasattr(self.module_test_ui, "set_current_test"):
                self.module_test_ui.set_current_test(selected_test)
        self._fade_in_widget(self.module_test_ui)

    def _create_orchestrator_ui(self):
        logger.debug("Switching to Orchestrator UI")
        self._hide_all_instrument_uis()
        if self.orchestrator_ui is None:
            self.orchestrator_ui = OrchestratorUI(
                n6705c_top=self.n6705c_top,
                mso64b_top=self.mso64b_top,
                chamber_ui=self.chamber_ui,
                instrument_manager=self.instrument_manager,
            )
            self.instrument_ui_container_layout.addWidget(self.orchestrator_ui)
            # 测试序列完成 → AI 异步动作回灌续跑（§4 / S3-2）
            try:
                self.orchestrator_ui.sequence_execution_finished.connect(
                    self._ai_on_sequence_finished_resume
                )
            except Exception:  # noqa: BLE001
                logger.error("连接序列完成回灌信号失败", exc_info=True)
            self.orchestrator_ui._sync_instruments()
            self.orchestrator_ui.show()
        else:
            self.orchestrator_ui.sync_n6705c_from_top()
            self.orchestrator_ui._sync_instruments()
            self.orchestrator_ui.show()
        self.current_instrument_ui = "orchestrator"
        self._fade_in_widget(self.orchestrator_ui)

    def _create_vmin_hunter_ui(self, selected_test=None):
        logger.debug("Switching to VminHunter UI: selected_test=%s", selected_test)
        self._hide_all_instrument_uis()
        if self.vmin_hunter_ui is None:
            self.vmin_hunter_ui = VminHunterContainerUI(
                n6705c_top=self.n6705c_top,
                instrument_manager=self.instrument_manager,
            )
            self.instrument_ui_container_layout.addWidget(self.vmin_hunter_ui)
        else:
            self.vmin_hunter_ui.sync_n6705c_from_top()
            self.vmin_hunter_ui.show()
        self.current_instrument_ui = "vmin_hunter"
        if selected_test in self.nav.vmin_hunter_tab_map:
            self.nav.current_vmin_hunter_key = selected_test
            if hasattr(self.vmin_hunter_ui, "set_current_test"):
                self.vmin_hunter_ui.set_current_test(selected_test)
        self._fade_in_widget(self.vmin_hunter_ui)

    def _create_kk_serials_ui(self):
        logger.debug("Switching to KK Serials UI")
        self._hide_all_instrument_uis()
        if self.kk_serials_ui is None:
            self.kk_serials_ui = _KKSerialsPage()
            self.instrument_ui_container_layout.addWidget(self.kk_serials_ui)
            self._wire_serial_rx_to_ai(self.kk_serials_ui)
        else:
            self.kk_serials_ui.show()
        self.current_instrument_ui = "kk_serials"
        self._fade_in_widget(self.kk_serials_ui)

    def _create_collection_ui(self, selected_key=None):
        if selected_key is None:
            selected_key = self.nav.current_collection_key
        if selected_key == "kk_serials":
            self._create_kk_serials_ui()
            return
        if selected_key == "i2c_control":
            self._create_i2c_control_ui()
            return
        logger.debug("Switching to Collection (MCU IO) UI")
        self._hide_all_instrument_uis()
        if self.collection_ui is None:
            self.collection_ui = _CollectionPage(
                instrument_manager=self.instrument_manager
            )
            self.instrument_ui_container_layout.addWidget(self.collection_ui)
        else:
            self.collection_ui.show()
        self.current_instrument_ui = "collection"
        self._fade_in_widget(self.collection_ui)

    def _create_i2c_control_ui(self):
        logger.debug("Switching to IIC Control UI")
        self._hide_all_instrument_uis()
        if self.i2c_control_ui is None:
            self.i2c_control_ui = _I2cControlPage()
            self.instrument_ui_container_layout.addWidget(self.i2c_control_ui)
        else:
            self.i2c_control_ui.show()
        self.current_instrument_ui = "i2c_control"
        self._fade_in_widget(self.i2c_control_ui)

    def _create_pmu_ui(self, selected_key=None):
        if selected_key is None:
            selected_key = self.nav.current_pmu_tool_key
        if selected_key == "1860":
            logger.debug("Switching to PMU 1860 UI")
            self._hide_all_instrument_uis()
            if self.pmu_1860_ui is None:
                self.pmu_1860_ui = Pmu1860UI()
                self.instrument_ui_container_layout.addWidget(self.pmu_1860_ui)
            else:
                self.pmu_1860_ui.show()
            self.current_instrument_ui = "pmu_1860"
            self._fade_in_widget(self.pmu_1860_ui)
            return
        logger.debug("Switching to PMU 1811 UI")
        self._hide_all_instrument_uis()
        if self.pmu_1811_ui is None:
            self.pmu_1811_ui = Pmu1811UI()
            self.instrument_ui_container_layout.addWidget(self.pmu_1811_ui)
        else:
            self.pmu_1811_ui.show()
        self.current_instrument_ui = "pmu_1811"
        self._fade_in_widget(self.pmu_1811_ui)

    def _create_gpio_ui(self):
        logger.debug("Switching to GPIO UI")
        self._hide_all_instrument_uis()
        if self.gpio_ui is None:
            self.gpio_ui = GpioControlUI(
                ui_action_registry=getattr(self, "_ui_action_registry", None),
            )
            self.instrument_ui_container_layout.addWidget(self.gpio_ui)
        else:
            self.gpio_ui.show()
        self.current_instrument_ui = "gpio"
        self._fade_in_widget(self.gpio_ui)

    def _hide_all_instrument_uis(self):
        self._page_switch_geometry = self.geometry()
        for widget in [
            self.n6705c_suite_ui,
            self.oscilloscope_ui, self.pmu_test_ui, self.chamber_ui,
            self.consumption_test_ui, self.charger_test_ui, self.module_test_ui,
            self.orchestrator_ui,
            self.vmin_hunter_ui, self.kk_serials_ui, self.collection_ui,
            self.i2c_control_ui, self.pmu_1811_ui, self.pmu_1860_ui,
            self.gpio_ui,
        ]:
            if widget is not None:
                widget.setGraphicsEffect(None)
                widget.hide()

    def _fade_in_widget(self, widget):
        if getattr(self, "ai_service", None) is not None:
            self.ai_service.set_page_context(self._get_current_help_key())
            self._update_ai_apply_callbacks()
            if getattr(self, "ai_panel", None) is not None:
                self.ai_panel.refresh_quick_actions()
                self.ai_panel.on_page_changed()
        if widget is None:
            return
        self._sync_compact_view_button()
        self._sync_labels_toggle_button()
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        QTimer.singleShot(0, self._restore_page_switch_geometry)

    def _restore_page_switch_geometry(self):
        if self._page_switch_geometry is None:
            return
        geometry = self._page_switch_geometry
        self._page_switch_geometry = None
        if self.isMaximized() or self.isFullScreen():
            return
        self.setGeometry(geometry)

    def _sync_compact_view_button(self):
        """紧凑视图按钮仅在 N6705C Analyser 页可见；切离该页时自动退出紧凑态。"""
        top_bar = getattr(self, "top_bar", None)
        if top_bar is None:
            return
        btn = top_bar.compact_view_button
        btn.setVisible(self.current_instrument_ui == "power_analyser")
        if not btn.isVisible() and btn.isChecked():
            btn.setChecked(False)

    def _sync_labels_toggle_button(self):
        """Custom Labels 按钮仅在 N6705C Datalog 页可见，并同步面板展开态。"""
        top_bar = getattr(self, "top_bar", None)
        if top_bar is None:
            return
        visible = self.current_instrument_ui == "datalog"
        top_bar.labels_separator.setVisible(visible)
        top_bar.labels_button.setVisible(visible)
        page = getattr(self, "n6705c_datalog_ui", None)
        if visible and page is not None:
            top_bar.labels_button.setChecked(page.is_labels_panel_visible())

    def _on_labels_button_toggled(self, checked):
        page = getattr(self, "n6705c_datalog_ui", None)
        if page is not None:
            page.set_labels_panel_visible(checked)

    def _on_datalog_labels_toggled(self, visible):
        top_bar = getattr(self, "top_bar", None)
        if top_bar is not None:
            top_bar.labels_button.setChecked(visible)

    def _on_compact_view_toggled(self, checked):
        if checked == self._compact_view:
            return
        self._compact_view = checked
        page = self.n6705c_analyser_ui
        if checked:
            # 记忆原窗口状态（是否最大化 + geometry），退出时还原
            self._pre_compact_state = (
                self.isMaximized(), self.saveGeometry(), self._collect_window_state()
            )
            self.left_nav.setVisible(False)
            self._compact_ai_was_open = False
            ai_btn = getattr(self.top_bar, "ai_panel_button", None)
            if ai_btn is not None and ai_btn.isChecked():
                self._compact_ai_was_open = True
                ai_btn.setChecked(False)
            # 紧凑态顶栏精简：隐藏截图 / AI 按钮，露出置顶按钮
            self.top_bar.capture_chart_button.setVisible(False)
            self.top_bar.ai_panel_button.setVisible(False)
            self.top_bar.pin_button.setVisible(True)
            if page is not None:
                page.set_compact_mode(True)
            if self.isMaximized():
                self.showNormal()
            # 直接 resize 会被旧布局 minimum（≈原窗口高）顶回（缓存要等
            # posted 布局事件才刷新），先 setFixedSize 钉住过渡尺寸；
            # 布局缓存刷新后按可见页面内容二次自适应（_fit_compact_size），
            # 消除固定高度多出的底部空白。
            self.setFixedSize(*_COMPACT_VIEW_SIZE)
            QTimer.singleShot(80, self._fit_compact_size)
        else:
            # 还原顶栏按钮；退出紧凑态强制取消置顶
            self.top_bar.pin_button.setChecked(False)
            self.top_bar.pin_button.setVisible(False)
            self.top_bar.capture_chart_button.setVisible(True)
            if self.with_ai and self.ai_settings is not None and self.ai_settings.enabled:
                self.top_bar.ai_panel_button.setVisible(True)
            if page is not None:
                page.set_compact_mode(False)
            self.left_nav.setVisible(True)
            # 解除紧凑视图的固定尺寸约束（QWIDGETSIZE_MAX = 16777215），
            # 并还原全局最小窗口约束（紧凑态 setFixedSize 曾将其覆盖）
            self.setMinimumSize(*_MIN_WINDOW_SIZE)
            self.setMaximumSize(16777215, 16777215)
            # 紧凑还原的 geometry 优先于切页时的 geometry 记忆
            # （紧凑态下切页会在 _hide_all_instrument_uis 记录紧凑尺寸）
            self._page_switch_geometry = None
            maximized, geometry = (self._pre_compact_state or (False, None, None))[:2]
            if geometry is not None:
                self.restoreGeometry(geometry)
            if maximized:
                self.showMaximized()
            if self._compact_ai_was_open:
                ai_btn = getattr(self.top_bar, "ai_panel_button", None)
                if ai_btn is not None:
                    ai_btn.setChecked(True)
            self._compact_ai_was_open = False

    def _on_pin_toggled(self, checked):
        """紧凑视图置顶按钮：切换 WindowStaysOnTopHint。

        setWindowFlags 会隐藏窗口，须保存 geometry 并重新 show。
        """
        flags = self.windowFlags()
        if checked:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint
        if flags == self.windowFlags():
            return
        geometry = self.geometry()
        self.setWindowFlags(flags)
        self.setGeometry(geometry)
        self.show()

    def _fit_compact_size(self):
        """紧凑视图尺寸自适应：按当前可见页面内容收缩窗口。

        须在布局 minimum 缓存刷新后（posted LayoutRequest 已处理，进入
        紧凑后 ≥80ms）调用。窗口级 hint 会包含 Suite 内隐藏的 Datalog 页，
        因此按 Analyser 当前尺寸与其 minimumSizeHint 的差值调整窗口。
        """
        if not self._compact_view:
            return
        self.layout().activate()
        page = self.n6705c_analyser_ui
        page_min_hint = page.minimumSizeHint()
        width = max(
            _COMPACT_VIEW_SIZE[0],
            self.width() + page_min_hint.width() - page.width(),
        )
        height = self.height() + page_min_hint.height() - page.height()
        self.setFixedSize(width, height)

    def _update_instrument_status(self):
        self.status_panel.update_instrument_status()

    def _get_current_help_key(self):
        if self.current_instrument_ui == "pmu_test":
            key_map = {
                "dcdc_efficiency": "pmu_dcdc_efficiency",
                "output_voltage": "pmu_output_voltage",
                "is_gain": "pmu_is_gain",
                "oscp": "pmu_oscp",
                "gpadc_test": "pmu_gpadc",
                "clk_test": "pmu_clk",
                "psrr": "pmu_psrr",
            }
            return key_map.get(self.nav.current_pmu_test_key, "pmu_dcdc_efficiency")
        elif self.current_instrument_ui == "charger_test":
            key_map = {
                "config_traverse": "charger_config_traverse",
                "status_register": "charger_status_register",
                "iterm": "charger_iterm",
                "regulation_voltage": "charger_regulation_voltage",
            }
            return key_map.get(self.nav.current_charger_test_key, "charger_config_traverse")
        elif self.current_instrument_ui == "module_test":
            key_map = {"ldo": "module_test_ldo", "dcdc": "module_test_dcdc"}
            return key_map.get(self.nav.current_module_test_key, "module_test_ldo")
        elif self.current_instrument_ui == "vmin_hunter":
            key_map = {"hunt": "vmin_hunter", "single_test": "vmin_single_test"}
            return key_map.get(self.nav.current_vmin_hunter_key, "vmin_hunter")
        elif self.current_instrument_ui:
            return self.current_instrument_ui
        return "power_analyser"

    def _current_module_version(self):
        module_map = {
            "pmu_test": "ui.pages.pmu_test",
            "charger_test": "ui.pages.charger_test",
            "module_test": "ui.pages.module_test",
            "power_analyser": "ui.pages.power_analyzer",
            "datalog": "ui.pages.power_analyzer",
            "oscilloscope": "ui.pages.oscilloscope",
            "consumption_test": "ui.pages.consumption_test",
            "orchestrator": "ui.pages.orchestrator",
            "chamber": "ui.pages.chamber",
            "vmin_hunter": "ui.pages.vmin_hunter",
            "i2c_control": "ui.modules.IIC_Module",
            "pmu_1811": "ui.pages.pmu",
            "pmu_1860": "ui.pages.pmu",
            "gpio": "ui.pages.gpio",
        }
        module_path = module_map.get(self.current_instrument_ui)
        if not module_path:
            return None
        try:
            import importlib
            mod = importlib.import_module(module_path)
            return getattr(mod, "MODULE_VERSION", None)
        except Exception:
            logger.debug("read MODULE_VERSION failed for %s", module_path, exc_info=True)
            return None

    def _build_help_version_footer(self):
        module_version = self._current_module_version()
        module_part = f"  |  模块版本 v{module_version}" if module_version else ""
        return (
            "<hr style='border:none;border-top:1px solid #2a3656;margin-top:18px;'>"
            f"<p style='color:#7b88a8;font-size:12px;'>{APP_NAME} v{__version__}{module_part}</p>"
        )

    def _on_help(self):
        help_key = self._get_current_help_key()
        helps_dir = os.path.join(get_resource_base(), "helps")
        help_file = os.path.join(helps_dir, f"{help_key}.html")

        if os.path.exists(help_file):
            with open(help_file, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = "<h2>帮助</h2><p>当前页面暂无帮助文档。</p>"

        content += self._build_help_version_footer()

        dialog = QDialog(self)
        dialog.setWindowTitle("帮助")
        dialog.setMinimumSize(560, 480)
        # 首帧防闪白：样式表 polish 前用调色板锁定深色背景，避免默认白底闪一下。
        dialog.setAttribute(Qt.WA_StyledBackground, True)
        _pal = dialog.palette()
        _pal.setColor(dialog.backgroundRole(), QColor("#0e1525"))
        dialog.setPalette(_pal)
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

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32" and not getattr(self, "_dwm_applied", False):
            self._enable_native_window_frame()
            self._apply_dwm_round_corners()
            self._dwm_applied = True

    def _enable_native_window_frame(self):
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
            style |= (
                _WS_CAPTION
                | _WS_THICKFRAME
                | _WS_MINIMIZEBOX
                | _WS_MAXIMIZEBOX
                | _WS_SYSMENU
            )
            user32.SetWindowLongW(hwnd, _GWL_STYLE, style)
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        except Exception:  # noqa: BLE001
            logger.debug("原生窗口样式注入失败", exc_info=True)

    def _apply_dwm_round_corners(self):
        try:
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi
            pref = ctypes.c_int(_DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                _DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(pref),
                ctypes.sizeof(pref),
            )
            color = ctypes.c_uint(_WINDOW_BORDER_COLOR)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                _DWMWA_BORDER_COLOR,
                ctypes.byref(color),
                ctypes.sizeof(color),
            )
        except Exception:  # noqa: BLE001
            logger.debug("DWM 圆角设置失败（系统不支持，忽略）", exc_info=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 按窗口高度切换 left_nav 密度令牌（阈值/滞回见 NavController）
        nav = getattr(self, "nav", None)
        if nav is not None:
            nav.update_density(self.height())

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and getattr(self, "top_bar", None) is not None:
            self.top_bar.sync_max_icon()
            self._refresh_nc_frame()

    def _refresh_nc_frame(self):
        """窗口状态落定后强制重算非客户区（重发 WM_NCCALCSIZE），
        防止状态切换途中基于过期状态算出的客户区内缩残留（还原后顶部白条）。"""
        if sys.platform != "win32":
            return
        try:
            # 窗口状态变化只在已创建窗口上触发，winId() 此处安全
            ctypes.windll.user32.SetWindowPos(
                int(self.winId()), 0, 0, 0, 0, 0,
                _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER
                | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
            )
        except Exception:  # noqa: BLE001
            logger.debug("非客户区重算失败", exc_info=True)

    def show_system_menu(self, global_pos):
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            hmenu = user32.GetSystemMenu(hwnd, False)
            if not hmenu:
                return False
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            flags = _TPM_RETURNCMD | _TPM_LEFTALIGN | _TPM_TOPALIGN
            user32.SetForegroundWindow(hwnd)
            cmd = user32.TrackPopupMenu(
                hmenu, flags, pt.x, pt.y, 0, hwnd, None
            )
            if cmd:
                user32.PostMessageW(hwnd, _WM_SYSCOMMAND, cmd, 0)
            return True
        except Exception:  # noqa: BLE001
            logger.debug("系统菜单弹出失败", exc_info=True)
            return False

    def _apply_minmax_info(self, msg):
        """WM_GETMINMAXINFO：把最小/最大轨迹尺寸与 Qt 尺寸约束同步。

        WM_NCCALCSIZE 返回 0 使客户区 == 窗口矩形（无原生非客户区），故
        ptMinTrackSize = minimumSize × DPR（物理像素）即可，无需标题栏/边框
        补偿；防止经原生边框拖拽绕过 Qt setMinimumSize。固定尺寸态（紧凑
        视图）同步钳制 ptMaxTrackSize，使原生拖拽同样不可改变窗口大小。
        """
        applied = False
        try:
            mmi = _MINMAXINFO.from_address(int(msg.lParam))
            dpr = self.devicePixelRatioF() or 1.0
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()
            if min_w > 0 and min_h > 0:
                mmi.ptMinTrackSize.x = int(round(min_w * dpr))
                mmi.ptMinTrackSize.y = int(round(min_h * dpr))
                applied = True
            max_w = self.maximumWidth()
            max_h = self.maximumHeight()
            if 0 < max_w < 16777215 and 0 < max_h < 16777215:
                mmi.ptMaxTrackSize.x = int(round(max_w * dpr))
                mmi.ptMaxTrackSize.y = int(round(max_h * dpr))
        except Exception:  # noqa: BLE001
            logger.debug("最小轨迹尺寸写入失败", exc_info=True)
        return self._adjust_maximized_size(msg) or applied

    def _adjust_maximized_size(self, msg):
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            monitor = user32.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
            if not monitor:
                return False
            info = _MONITORINFO()
            info.cbSize = ctypes.sizeof(_MONITORINFO)
            if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return False
            work = info.rcWork
            mon = info.rcMonitor
            mmi = _MINMAXINFO.from_address(int(msg.lParam))
            mmi.ptMaxPosition.x = work.left - mon.left
            mmi.ptMaxPosition.y = work.top - mon.top
            mmi.ptMaxSize.x = work.right - work.left
            mmi.ptMaxSize.y = work.bottom - work.top
            mmi.ptMaxTrackSize.x = work.right - work.left
            mmi.ptMaxTrackSize.y = work.bottom - work.top
            return True
        except Exception:  # noqa: BLE001
            logger.debug("最大化尺寸校正失败", exc_info=True)
            return False

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
            except (TypeError, ValueError):
                return False, 0
            if msg.message == _WM_NCCALCSIZE:
                if msg.wParam:
                    if self.isMaximized():
                        # 最大化时 Windows 会将窗口向外扩展 resize border 厚度以隐藏边框，
                        # 由于此处返回 0（client = window rect），client 顶部会超出可视工作区，
                        # 导致标题栏顶部被裁切。把 proposed client rect 向内收缩 border，
                        # 保证标题栏完整可见。
                        params = _NCCALCSIZE_PARAMS.from_address(int(msg.lParam))
                        dpr = self.devicePixelRatioF() or 1.0
                        border = int(round(self._resize_border * dpr))
                        params.rgrc[0].left += border
                        params.rgrc[0].top += border
                        params.rgrc[0].right -= border
                        params.rgrc[0].bottom -= border
                    return True, 0
                return False, 0
            if msg.message == _WM_GETMINMAXINFO:
                if self._apply_minmax_info(msg):
                    return True, 0
                return False, 0
            if msg.message == _WM_NCRBUTTONUP and msg.wParam == _HTCAPTION:
                if self.show_system_menu(None):
                    return True, 0
            if msg.message == _WM_NCHITTEST:
                global_x = ctypes.c_int16(msg.lParam & 0xFFFF).value
                global_y = ctypes.c_int16((msg.lParam >> 16) & 0xFFFF).value
                hit = self._hit_test_native(global_x, global_y)
                if hit is not None:
                    return True, hit
        return super().nativeEvent(event_type, message)

    def _hit_test_native(self, screen_x, screen_y):
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            rect = _RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return None
            win_w = rect.right - rect.left
            win_h = rect.bottom - rect.top
            x = screen_x - rect.left
            y = screen_y - rect.top
            dpr = self.devicePixelRatioF() or 1.0
            b = int(round(self._resize_border * dpr))
            if not (self.isMaximized() or self._is_snapped()):
                left, right = x < b, x > win_w - b
                top, bottom = y < b, y > win_h - b
                if top and left:
                    return _HTTOPLEFT
                if top and right:
                    return _HTTOPRIGHT
                if bottom and left:
                    return _HTBOTTOMLEFT
                if bottom and right:
                    return _HTBOTTOMRIGHT
                if left:
                    return _HTLEFT
                if right:
                    return _HTRIGHT
                if top:
                    return _HTTOP
                if bottom:
                    return _HTBOTTOM
            bar_h = int(round(self._caption_height_px() * dpr))
            if 0 <= y <= bar_h:
                top_bar = getattr(self, "top_bar", None)
                if top_bar is not None and top_bar.is_caption_window_point(
                    x, y, dpr
                ):
                    return _HTCAPTION
            return None
        except Exception:  # noqa: BLE001
            logger.debug("命中测试失败", exc_info=True)
            return None

    def _caption_height_px(self):
        top_bar = getattr(self, "top_bar", None)
        if top_bar is not None:
            return top_bar.height()
        return 36

    def _is_snapped(self):
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            monitor = user32.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
            if not monitor:
                return False
            info = _MONITORINFO()
            info.cbSize = ctypes.sizeof(_MONITORINFO)
            if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return False
            rect = _RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False
            work = info.rcWork
            touch_left = rect.left <= work.left
            touch_right = rect.right >= work.right
            touch_top = rect.top <= work.top
            touch_bottom = rect.bottom >= work.bottom
            full_height = touch_top and touch_bottom
            half_width = (rect.right - rect.left) < (work.right - work.left)
            return full_height and half_width and (touch_left or touch_right)
        except Exception:  # noqa: BLE001
            logger.debug("Snap 状态检测失败", exc_info=True)
            return False

    def _main_window_settings(self):
        return QSettings("KK_Lab", "MainWindow")

    def _screen_available_geometry_for(self, point=None):
        app = QApplication.instance()
        screen = app.screenAt(point) if app is not None and point is not None else None
        if screen is None and app is not None:
            screen = app.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
        return QRect(0, 0, 1280, 720)

    def _clamped_window_geometry(self, window_cfg):
        saved = QRect(
            int(window_cfg.get("x", 0)),
            int(window_cfg.get("y", 0)),
            int(window_cfg.get("width", 0)),
            int(window_cfg.get("height", 0)),
        )
        if saved.width() <= 0 or saved.height() <= 0:
            return self.geometry()

        available = self._screen_available_geometry_for(saved.center())
        width = min(saved.width(), available.width())
        height = min(saved.height(), available.height())
        x = min(max(saved.x(), available.x()), available.right() - width + 1)
        y = min(max(saved.y(), available.y()), available.bottom() - height + 1)
        return QRect(x, y, width, height)

    def _load_window_geometry(self):
        settings = self._main_window_settings()
        if not settings.contains("geometry/x"):
            return None
        return {
            "x": settings.value("geometry/x", type=int),
            "y": settings.value("geometry/y", type=int),
            "width": settings.value("geometry/width", type=int),
            "height": settings.value("geometry/height", type=int),
            "maximized": settings.value("geometry/maximized", False, type=bool),
        }

    def _collect_window_state(self):
        if not self.isWindow() or not self.isVisible() or self.isMinimized():
            return {}
        geom = self.normalGeometry() if self.isMaximized() else self.geometry()
        if geom.width() <= 0 or geom.height() <= 0:
            return {}
        return {
            "x": int(geom.x()),
            "y": int(geom.y()),
            "width": int(geom.width()),
            "height": int(geom.height()),
            "maximized": bool(self.isMaximized()),
        }

    def _restore_window_geometry(self):
        self._restore_maximized = False
        try:
            window_cfg = self._load_window_geometry()
            if window_cfg is None:
                return
            self.setGeometry(self._clamped_window_geometry(window_cfg))
            self._restore_maximized = bool(window_cfg.get("maximized", False))
        except Exception:
            logger.warning("Restore main window geometry failed", exc_info=True)

    def _save_window_geometry(self):
        try:
            state = self._collect_window_state()
            pre_compact = getattr(self, "_pre_compact_state", None)
            if getattr(self, "_compact_view", False) and pre_compact is not None:
                state = pre_compact[2]
            if not state:
                return
            settings = self._main_window_settings()
            settings.remove("geometry")
            for key, value in state.items():
                settings.setValue(f"geometry/{key}", value)
            settings.sync()
        except Exception:
            logger.warning("Save main window geometry failed", exc_info=True)

    def closeEvent(self, event):
        self.status_panel.suppress_toasts()
        self._save_window_geometry()
        self._save_ai_panel_state()
        # 关闭即清理调度定时器（§5.4）
        for timer in list(getattr(self, "_scheduled_timers", {}).values()):
            try:
                timer.stop()
                timer.deleteLater()
            except Exception:  # noqa: BLE001
                pass
        if hasattr(self, "_scheduled_timers"):
            self._scheduled_timers.clear()
        if getattr(self, "ai_service", None) is not None:
            self.ai_service.shutdown()
        self.connection_hub.shutdown()
        self._perform_close_cleanup()
        super().closeEvent(event)

    def _save_ai_panel_state(self):
        if self.outer_splitter is None or self.ai_panel is None:
            return
        panel_open = self.ai_panel.isVisible()
        if panel_open:
            sizes = self.outer_splitter.sizes()
            if len(sizes) == 2 and sizes[1] > 0:
                self._ai_panel_width = clamp_width(sizes[1])
        save_panel_state(panel_open, self._ai_panel_width)
