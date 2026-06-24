#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

import os
import sys
from ui.resource_path import get_resource_base

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QSplitter, QFrame, QDialog, QTextBrowser, QGraphicsOpacityEffect
)

from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QEvent, QEventLoop
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

    _DWMWA_WINDOW_CORNER_PREFERENCE = 33
    _DWMWA_BORDER_COLOR = 34
    _DWMWCP_ROUND = 2
    _WINDOW_BORDER_COLOR = 0x00403420  # COLORREF 0x00BBGGRR -> 边框 #203440
from PySide6.QtGui import QPalette, QColor, QFont
from ui.pages.oscilloscope.oscilloscope_base_ui import OscilloscopeBaseUI
from ui.pages.n6705c_power_analyzer.n6705c_analyser_ui import N6705CAnalyserUI
from ui.pages.n6705c_power_analyzer.n6705c_datalog_ui import N6705CDatalogUI
from ui.pages.n6705c_power_analyzer.n6705c_top import N6705CTop
from ui.pages.oscilloscope.mso64b_top import MSO64BTop
from ui.pages.pmu_test.pmu_test_ui import PMUTestUI
from ui.pages.chamber.chamber_control_ui import ChamberControlUI
from ui.pages.consumption_test.consumption_test_wrapper import ConsumptionTestWrapper
from ui.pages.charger_test.charger_test_ui import ChargerTestUI
from ui.pages.custom_test.custom_test_ui import CustomTestUI
from ui.pages.vmin_hunter.vmin_hunter_ui import VminHunterUI
from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin
from ui.modules.mcu_io_module_frame import McuIoConnectionMixin
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from core.test_manager import TestManager
from core.instruments import InstrumentManager, InstrumentSpec, ConnectionHub
from instruments.base.visa_instrument import VisaInstrument
from ui.styles import SCROLLBAR_STYLE
from ui.nav_controller import NavController
from ui.instrument_status import InstrumentStatusPanel
from ui.app_top_bar import AppTopBar
from ui.ai.ai_assist_panel import AIAssistPanel
from ui.ai.panel_state import load_panel_state, save_panel_state, clamp_width
from core.ai.config import AISettings
from core.ai.ai_service import AIService
from core.ai.log_ring import get_log_ring
from ui.cleanup_mixin import CleanupMixin
from ui.standalone import resize_and_center_window
from log_config import get_logger
from version import APP_NAME, __version__
from debug_config import DEBUG_MOCK

logger = get_logger(__name__)


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
        title_label = QLabel("MCU IO (YD RP2040)")
        title_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        title_row.addWidget(title_label)
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


class MainWindow(CleanupMixin, QMainWindow):

    def __init__(self, with_ai: bool = True):
        super().__init__()
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

        self.test_manager = TestManager()
        self.visa_instrument = VisaInstrument()
        self.chamber = None

        self.instrument_manager = InstrumentManager(parent=self)

        self.n6705c_top = N6705CTop(self)
        self.mso64b_top = MSO64BTop(self)
        self.connection_hub = ConnectionHub(
            self.instrument_manager,
            self.n6705c_top,
            self.mso64b_top,
            parent=self,
        )

        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C, MockMSO64B
            logger.info("[MOCK] Auto-connecting mock instruments...")
            mock_a = MockN6705C()
            mock_b = MockN6705C()
            mock_scope = MockMSO64B()
            self.n6705c_top.connect_a("MOCK::N6705C::A", mock_a, "MOCK-A")
            self.n6705c_top.connect_b("MOCK::N6705C::B", mock_b, "MOCK-B")
            self.mso64b_top.connect_instrument("MOCK::MSO64B", mock_scope, "MSO64B")

        self.n6705c_analyser_ui = None
        self.n6705c_datalog_ui = None
        self.oscilloscope_ui = None
        self.pmu_test_ui = None
        self.chamber_ui = None
        self.consumption_test_ui = None
        self.charger_test_ui = None
        self.custom_test_ui = None
        self.vmin_hunter_ui = None
        self.kk_serials_ui = None
        self.collection_ui = None
        self.current_instrument_ui = None
        self._page_switch_geometry = None
        self.channels = []

        self.nav = NavController(self)
        self.status_panel = InstrumentStatusPanel(self)

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
        self.ai_panel = None
        self.outer_splitter = None

        self._setup_style()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self._create_main_content()
        self.nav.create_submenus()
        self._connect_signals()

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
        main_splitter = QSplitter(Qt.Horizontal)

        left_nav, left_nav_layout = self.nav.create_left_nav()
        bottom_widget = self.status_panel.create_bottom_widget()
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

        self._create_power_analyser_ui()
        self.right_content_layout.addWidget(self.instrument_ui_container)

        main_splitter.addWidget(self.right_content)
        main_splitter.setSizes([187, 1013])
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setCollapsible(0, False)
        main_splitter.setCollapsible(1, False)
        self.main_splitter = main_splitter

        self.top_bar = AppTopBar(self)
        self.main_layout.addWidget(self.top_bar)

        self._setup_ai_panel(main_splitter)

    def _setup_ai_panel(self, main_splitter):
        if not self.with_ai:
            self.main_layout.addWidget(main_splitter)
            ai_button = getattr(self.top_bar, "ai_panel_button", None)
            if ai_button is not None:
                ai_button.setVisible(False)
            return

        outer_splitter = QSplitter(Qt.Horizontal)
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
        outer_splitter.setCollapsible(0, False)
        outer_splitter.setCollapsible(1, False)
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

    def _setup_ai_action_system(self):
        from core.ai.actions import ActionDeps, build_action_system

        deps = ActionDeps(
            instrument_manager=self.instrument_manager,
            page_key_getter=self._get_ai_page_key,
            serial_status_getter=self._get_ai_serial_status,
            serial_manager_getter=self._current_serial_manager,
            serial_ports_getter=self._ai_serial_list_ports,
            execution_logs_getter=self._get_ai_execution_logs,
            app_logs_getter=self._get_ai_app_logs,
            rx_recent_getter=self._get_ai_recent_rx,
            test_status_getter=self._get_ai_test_status,
            test_config_getter=self._get_ai_test_config,
            test_steps_getter=self._get_ai_test_steps,
            test_result_summary_getter=self._get_ai_test_result_summary,
            waveform_data_getter=self._provide_ai_waveform_windowed,
            waveform_full_data_getter=self._provide_ai_waveform_full,
            draft_registry=self.ai_service.draft_registry,
            artifact_registry=self.ai_service.artifact_registry,
            open_page_callback=self._ai_open_page,
            toggle_ai_panel_callback=self._ai_toggle_panel,
            serial_send_text_callback=self._ai_serial_send_text,
            serial_clear_callback=self._ai_serial_clear,
            test_run_callback=self._ai_test_run,
            test_pause_callback=self._ai_test_pause,
            test_stop_callback=self._ai_test_stop,
            test_set_variable_callback=self._ai_test_set_variable,
            test_run_single_step_callback=self._ai_test_run_single_step,
            config_apply_callback=self._apply_ai_config_draft,
            script_apply_callback=self._apply_ai_script_draft,
            chamber_wait_stable_callback=self._ai_chamber_wait_stable,
            datalog_export_callback=self._ai_export_datalog_csv,
        )
        registry, dispatcher = build_action_system(
            deps,
            require_confirm_high=self.ai_settings.require_confirm_high_risk_action,
            allow_critical=False,
        )
        dispatcher.set_confirm_callback(self.ai_panel.confirm_action)
        self.ai_service.set_action_system(registry, dispatcher)

    def _get_ai_app_logs(self, lines):
        ring = get_log_ring()
        if ring is None:
            return []
        return ring.recent(lines)

    def _get_ai_recent_rx(self, session_id, lines):
        service = getattr(self, "ai_service", None)
        if service is None:
            return []
        return service.rx_cache.recent(session_id, lines)

    def _get_ai_test_status(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return None
        canvas = getattr(ui, "canvas", None)
        running = bool(getattr(canvas, "_running", False)) if canvas else False
        steps = 0
        if canvas is not None:
            try:
                steps = len(canvas.get_sequence())
            except Exception:  # noqa: BLE001 - 状态查询失败不致命
                steps = 0
        return {"available": True, "running": running, "steps": steps}

    def _get_ai_test_config(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return None
        getter = getattr(ui, "get_ai_test_config", None)
        if not callable(getter):
            return None
        return getter()

    def _get_ai_test_steps(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return None
        getter = getattr(ui, "get_ai_test_steps", None)
        if not callable(getter):
            return None
        return getter()

    def _get_ai_test_result_summary(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return None
        getter = getattr(ui, "get_ai_test_result_summary", None)
        if not callable(getter):
            return None
        return getter()

    def _ai_test_set_variable(self, name, value):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return False, "请先切换到 Custom Test 页面。"
        setter = getattr(ui, "ai_set_test_variable", None)
        if not callable(setter):
            return False, "当前页面不支持设置测试变量。"
        try:
            return setter(name, value)
        except Exception:  # noqa: BLE001 - 设置异常转可读结果
            logger.error("AI 设置测试变量失败", exc_info=True)
            return False, "设置变量异常，请查看日志。"

    def _ai_test_run_single_step(self, step_id):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return False, "请先切换到 Custom Test 页面。"
        runner = getattr(ui, "ai_run_single_step", None)
        if not callable(runner):
            return False, "当前页面不支持单步执行。"
        try:
            return runner(step_id)
        except Exception:  # noqa: BLE001 - 单步异常转可读结果
            logger.error("AI 单步执行失败", exc_info=True)
            return False, "单步执行异常，请查看日志。"

    def _ai_open_page(self, page):
        button_map = {
            "power_analyser": self.nav.n6705c_power_analyzer_btn,
            "datalog": self.nav.n6705c_power_analyzer_btn,
            "oscilloscope": self.nav.oscilloscope_btn,
            "thermal_chamber": self.nav.chamber_btn,
            "pmu_test": self.nav.pmu_test_btn,
            "charger_test": self.nav.charger_test_btn,
            "consumption_test": self.nav.consumption_test_btn,
            "vmin_hunter": self.nav.vmin_hunter_btn,
            "custom_test": self.nav.custom_test_btn,
            "kk_serials": self.nav.kk_serials_btn,
            "collection": self.nav.collection_btn,
        }
        button = button_map.get(page)
        if button is None:
            return False, f"未知页面：{page}"
        self.nav.handle_nav_button_clicked(button)
        return True, f"已跳转到 {page}"

    def _ai_toggle_panel(self, want_open):
        button = getattr(self.top_bar, "ai_panel_button", None)
        if button is None:
            return False, "面板按钮不可用。"
        button.setChecked(bool(want_open))
        return True, "面板已打开。" if want_open else "面板已关闭。"

    def _ai_serial_send_text(self, text, newline):
        manager = self._current_serial_manager()
        if manager is None:
            return False, "当前无串口管理器。"
        session = manager.active_session
        if session is None or not getattr(session, "connected", False):
            return False, "当前无已连接的活动串口会话。"
        try:
            ok = manager.send_to_active_session((text + newline).encode("utf-8"))
        except Exception:  # noqa: BLE001 - 发送异常转可读结果
            logger.error("AI 串口发送失败", exc_info=True)
            return False, "串口发送异常，请查看日志。"
        return bool(ok), "已发送。" if ok else "发送失败。"

    def _ai_serial_clear(self):
        service = getattr(self, "ai_service", None)
        if service is not None:
            service.rx_cache.clear()
        return True, "已清空 AI 侧串口接收缓存。"

    def _ai_serial_list_ports(self):
        """枚举系统可用串口（供 AI list_serial_ports 动作调用）。

        经 pyserial 的 list_ports.comports() 本地枚举，返回设备名/描述/硬件 ID。
        UI 层负责实际 IO 枚举，core handler 不直连 serial 库。
        """
        try:
            import serial.tools.list_ports as list_ports

            ports = list_ports.comports()
            return [
                {
                    "device": p.device,
                    "description": getattr(p, "description", "") or "",
                    "hwid": getattr(p, "hwid", "") or "",
                }
                for p in ports
            ]
        except Exception:  # noqa: BLE001 - 枚举失败回空列表，不致命
            logger.error("AI 枚举串口失败", exc_info=True)
            return []

    def _ai_test_run(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return False, "请先切换到 Custom Test 页面。"
        try:
            ui._on_run()
        except Exception:  # noqa: BLE001 - 启动异常转可读结果
            logger.error("AI 启动测试序列失败", exc_info=True)
            return False, "启动测试序列异常，请查看日志。"
        return True, "已请求启动测试序列。"

    def _ai_test_pause(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return False, "请先切换到 Custom Test 页面。"
        try:
            ui._on_pause()
        except Exception:  # noqa: BLE001 - 暂停异常转可读结果
            logger.error("AI 暂停测试序列失败", exc_info=True)
            return False, "暂停测试序列异常，请查看日志。"
        return True, "已切换暂停/恢复。"

    def _ai_test_stop(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return False, "请先切换到 Custom Test 页面。"
        try:
            ui._on_stop()
        except Exception:  # noqa: BLE001 - 停止异常转可读结果
            logger.error("AI 停止测试序列失败", exc_info=True)
            return False, "停止测试序列异常，请查看日志。"
        return True, "已发送停止请求。"

    def _ai_chamber_wait_stable(self, session_id, target, tolerance, timeout):
        """温箱等待稳定：经 worker 线程运行 TemperatureStabilizer，QEventLoop 保持 UI 响应。

        执行期持 busy 租约，避免其它流程改温度；判稳跑在独立线程，主线程经
        QEventLoop + QTimer 轮询 future 完成状态，不阻塞 UI 事件循环。返回结果 dict
        供 chamber_wait_stable handler 回灌模型。
        """
        from concurrent.futures import ThreadPoolExecutor

        from instruments.chambers import TemperatureStabilizer

        manager = self.instrument_manager
        session = manager.get_session(session_id)
        if session is None or not session.connected:
            return {"ok": False, "_message": f"会话未连接：{session_id}"}
        chamber = manager.get_instance(session_id)
        if chamber is None:
            return {"ok": False, "_message": f"无法获取温箱实例：{session_id}"}
        if not manager.try_set_busy(session_id, True, owner="AIAssist"):
            owner = getattr(session, "busy_owner", "")
            return {
                "ok": False,
                "_message": f"温箱忙（owner={owner or '未知'}），拒绝等待以免冲突。",
            }

        stabilizer = TemperatureStabilizer(
            chamber,
            poll_interval=5.0,
            window_seconds=60.0,
            tolerance=tolerance,
            stable_hits=2,
            max_wait_s=timeout,
            arrive_tolerance=1.0,
            log_fn=lambda msg: logger.info("chamber_wait_stable[%s]: %s", session_id, msg),
            stop_check=None,
        )

        box: dict = {}

        def _run():
            try:
                box["result"] = stabilizer.wait_for_stable(target)
            except Exception as exc:  # noqa: BLE001 - 透传给主线程统一处理
                box["error"] = exc

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_run)

        loop = QEventLoop()

        def _on_poll():
            if future.done():
                poll.stop()
                loop.quit()

        poll = QTimer()
        poll.setInterval(100)
        poll.timeout.connect(_on_poll)
        poll.start()
        if not future.done():
            loop.exec()
        poll.stop()
        executor.shutdown(wait=False)

        try:
            manager.try_set_busy(session_id, False, owner="AIAssist")
        except Exception:  # noqa: BLE001 - 释放租约失败不掩盖主结果
            logger.error("释放温箱租约失败：%s", session_id, exc_info=True)

        if "error" in box:
            return {"ok": False, "_message": f"等待稳定异常：{box['error']}"}
        result = box.get("result")
        if result is None:
            return {"ok": False, "_message": "等待稳定未返回结果。"}

        actual = result.actual
        actual_txt = f"{actual:.2f}" if isinstance(actual, (int, float)) else str(actual)
        if result.stable:
            msg = f"温度已稳定：{actual_txt} °C（耗时 {result.waited_s:.0f}s）。"
        else:
            msg = (
                f"未稳定（{result.reason}）：当前 {actual_txt} °C，"
                f"已等待 {result.waited_s:.0f}s。"
            )
        return {
            "ok": bool(result.stable),
            "session_id": session_id,
            "stable": bool(result.stable),
            "reason": result.reason,
            "target": result.target,
            "actual": actual,
            "waited_s": round(result.waited_s, 1),
            "poll_count": result.poll_count,
            "_message": msg,
        }

    def _get_ai_page_key(self):
        return self._get_current_help_key()

    def _update_ai_apply_callbacks(self):
        panel = getattr(self, "ai_panel", None)
        if panel is None:
            return
        if self.current_instrument_ui == "custom_test":
            panel.set_script_apply_callback(self._apply_ai_script_draft)
        else:
            panel.set_script_apply_callback(None)
        panel.set_config_apply_callback(self._apply_ai_config_draft)

        service = getattr(self, "ai_service", None)
        if service is not None:
            if self.current_instrument_ui == "custom_test":
                service.set_sequence_data_getter(self._get_ai_sequence_data)
            else:
                service.set_sequence_data_getter(None)

        if self.current_instrument_ui == "datalog":
            panel.set_waveform_provider_callback(self._provide_ai_waveform_digest)
            panel.set_waveform_range_getter(self._provide_ai_waveform_range)
            panel.set_waveform_marker_getter(self._provide_ai_waveform_marker)
        else:
            panel.set_waveform_provider_callback(None)
            panel.set_waveform_range_getter(None)
            panel.set_waveform_marker_getter(None)

    def _get_ai_sequence_data(self):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or self.current_instrument_ui != "custom_test":
            return None
        return ui.get_ai_sequence_data()

    def _provide_ai_waveform_digest(self, x_range=None, marker=None):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None:
            return None
        return ui.build_waveform_digest(x_range=x_range, marker=marker)

    def _provide_ai_waveform_range(self):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None:
            return None
        return ui.get_visible_x_range()

    def _provide_ai_waveform_marker(self):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None:
            return None
        return ui.get_marker_window()

    def _provide_ai_waveform_windowed(self):
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None or self.current_instrument_ui != "datalog":
            return None
        return ui.get_waveform_data_windowed()

    def _provide_ai_waveform_full(self):
        """返回 Datalog 页全量波形数据（未按可见窗口裁剪），供 P6 波形 CSV 导出切片。"""
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None or self.current_instrument_ui != "datalog":
            return None
        getter = getattr(ui, "get_waveform_data", None)
        if not callable(getter):
            return None
        return getter()

    def _ai_export_datalog_csv(self, session_id, dir_path):
        """P6 Datalog CSV 导出回调：委托 Datalog 页非交互式导出到指定目录。

        session_id 仅用于审计追溯；实际导出的是当前 Datalog 页内存中的可见通道数据。
        返回 {ok, path, rows, channels, bytes, message} 供 export_datalog_csv handler 回灌。
        """
        ui = getattr(self, "n6705c_datalog_ui", None)
        if ui is None or self.current_instrument_ui != "datalog":
            return {"ok": False, "message": "当前不在 Datalog 页面，无法导出。"}
        exporter = getattr(ui, "export_combined_csv_to_path", None)
        if not callable(exporter):
            return {"ok": False, "message": "Datalog 页面不支持非交互式导出。"}
        try:
            return exporter(dir_path)
        except Exception:  # noqa: BLE001 - 导出异常转可读结果
            logger.error("AI Datalog CSV 导出失败", exc_info=True)
            return {"ok": False, "message": "导出异常，请查看日志。"}

    def _apply_ai_script_draft(self, nodes):
        ui = getattr(self, "custom_test_ui", None)
        if ui is None or getattr(ui, "canvas", None) is None:
            return False, "Custom Test 页面不可用。"
        if getattr(ui.canvas, "_running", False):
            return False, "序列运行中，无法应用草案。"
        try:
            ui.canvas.load_from_nodes(nodes)
        except Exception:
            logger.error("应用 AI 脚本草案到画布失败", exc_info=True)
            return False, "应用到画布失败，请查看日志。"
        return True, ""

    def _apply_ai_config_draft(self, draft):
        page = getattr(self, "current_instrument_ui", None)
        ui_map = {
            "custom_test": getattr(self, "custom_test_ui", None),
            "vmin_hunter": getattr(self, "vmin_hunter_ui", None),
            "pmu_test": getattr(self, "pmu_test_ui", None),
            "charger_test": getattr(self, "charger_test_ui", None),
            "consumption_test": getattr(self, "consumption_test_ui", None),
        }
        target = ui_map.get(page)
        if target is None:
            return False, "当前页面不支持应用配置草案。"
        importer = getattr(target, "apply_ai_config_draft", None)
        if not callable(importer):
            return False, "当前页面尚未实现配置草案导入接口。"
        try:
            ok = importer(draft.payload)
        except Exception:
            logger.error("应用 AI 配置草案失败", exc_info=True)
            return False, "应用配置失败，请查看日志。"
        if ok is False:
            return False, "页面拒绝了该配置草案。"
        return True, ""

    def _wire_serial_rx_to_ai(self, page):
        manager = getattr(page, "_sc_session_manager", None)
        if manager is None or getattr(self, "ai_service", None) is None:
            return
        manager.session_data_received.connect(self.ai_service.feed_serial_rx)

    def _current_serial_manager(self):
        page = getattr(self, "kk_serials_ui", None)
        if page is None:
            return None
        return getattr(page, "_sc_session_manager", None)

    def _get_ai_serial_status(self):
        manager = self._current_serial_manager()
        if manager is None:
            return None
        session = manager.active_session
        if session is None:
            return None
        return {
            "session_id": session.session_id,
            "port": getattr(session, "port", "") or "",
            "baudrate": getattr(session, "baudrate", 0),
            "connected": bool(getattr(session, "connected", False)),
            "rx_bytes": getattr(session, "rx_bytes", 0),
            "tx_bytes": getattr(session, "tx_bytes", 0),
        }

    def _get_ai_execution_logs(self):
        page = self._current_active_page()
        logs_frame = getattr(page, "logs_frame", None) if page is not None else None
        if logs_frame is None:
            return []
        raw_logs = getattr(logs_frame, "_all_logs", [])
        return [str(raw) for raw, _html in raw_logs]

    def _current_active_page(self):
        mapping = {
            "kk_serials": getattr(self, "kk_serials_ui", None),
            "custom_test": getattr(self, "custom_test_ui", None),
            "pmu_test": getattr(self, "pmu_test_ui", None),
            "charger_test": getattr(self, "charger_test_ui", None),
            "consumption_test": getattr(self, "consumption_test_ui", None),
        }
        return mapping.get(self.current_instrument_ui)

    def _connect_signals(self):
        self.nav.n6705c_power_analyzer_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.oscilloscope_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.chamber_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.pmu_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.charger_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.consumption_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.vmin_hunter_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.custom_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.kk_serials_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.collection_btn.clicked.connect(self._on_nav_button_clicked)

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

    def _switch_pa_mode(self, mode_key):
        if mode_key == "analyser":
            self._create_power_analyser_ui()
        elif mode_key == "datalog":
            self._create_datalog_ui()
        else:
            self._create_power_analyser_ui()

    def _create_power_analyser_ui(self):
        logger.debug("Switching to Power Analyser UI")
        self._hide_all_instrument_uis()
        if self.n6705c_analyser_ui is None:
            self.n6705c_analyser_ui = N6705CAnalyserUI(
                n6705c_top=self.n6705c_top,
                instrument_manager=self.instrument_manager,
            )
            self.instrument_ui_container_layout.addWidget(self.n6705c_analyser_ui)
        else:
            self.n6705c_analyser_ui._sync_from_top()
            self.n6705c_analyser_ui.show()
        self.current_instrument_ui = "power_analyser"
        self.channels = self.n6705c_analyser_ui.channels if hasattr(self.n6705c_analyser_ui, 'channels') else []
        self._fade_in_widget(self.n6705c_analyser_ui)

    def _create_datalog_ui(self):
        logger.debug("Switching to Datalog UI")
        self._hide_all_instrument_uis()
        if self.n6705c_datalog_ui is None:
            self.n6705c_datalog_ui = N6705CDatalogUI(
                n6705c_top=self.n6705c_top,
                instrument_manager=self.instrument_manager,
            )
            self.instrument_ui_container_layout.addWidget(self.n6705c_datalog_ui)
        else:
            self.n6705c_datalog_ui._sync_from_top()
            self.n6705c_datalog_ui.show()
        self.current_instrument_ui = "datalog"
        self._fade_in_widget(self.n6705c_datalog_ui)

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

    def _create_custom_test_ui(self):
        logger.debug("Switching to Custom Test UI")
        self._hide_all_instrument_uis()
        if self.custom_test_ui is None:
            self.custom_test_ui = CustomTestUI(
                n6705c_top=self.n6705c_top,
                mso64b_top=self.mso64b_top,
                chamber_ui=self.chamber_ui,
                instrument_manager=self.instrument_manager,
            )
            self.instrument_ui_container_layout.addWidget(self.custom_test_ui)
        else:
            self.custom_test_ui.sync_n6705c_from_top()
            self.custom_test_ui._sync_instruments()
            self.custom_test_ui.show()
        self.current_instrument_ui = "custom_test"
        self._fade_in_widget(self.custom_test_ui)

    def _create_vmin_hunter_ui(self):
        logger.debug("Switching to VminHunter UI")
        self._hide_all_instrument_uis()
        if self.vmin_hunter_ui is None:
            self.vmin_hunter_ui = VminHunterUI(
                n6705c_top=self.n6705c_top,
                instrument_manager=self.instrument_manager,
            )
            self.instrument_ui_container_layout.addWidget(self.vmin_hunter_ui)
        else:
            self.vmin_hunter_ui.sync_n6705c_from_top()
            self.vmin_hunter_ui.show()
        self.current_instrument_ui = "vmin_hunter"
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

    def _create_collection_ui(self):
        logger.debug("Switching to Collection UI")
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

    def _hide_all_instrument_uis(self):
        self._page_switch_geometry = self.geometry()
        for widget in [
            self.n6705c_analyser_ui, self.n6705c_datalog_ui,
            self.oscilloscope_ui, self.pmu_test_ui, self.chamber_ui,
            self.consumption_test_ui, self.charger_test_ui, self.custom_test_ui,
            self.vmin_hunter_ui, self.kk_serials_ui, self.collection_ui,
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
        if widget is None:
            return
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
        elif self.current_instrument_ui == "power_analyser":
            if self.nav.current_pa_mode == "datalog":
                return "datalog"
            return "power_analyser"
        elif self.current_instrument_ui == "datalog":
            return "datalog"
        elif self.current_instrument_ui:
            return self.current_instrument_ui
        return "power_analyser"

    def _current_module_version(self):
        module_map = {
            "pmu_test": "ui.pages.pmu_test",
            "charger_test": "ui.pages.charger_test",
            "power_analyser": "ui.pages.n6705c_power_analyzer",
            "datalog": "ui.pages.n6705c_power_analyzer",
            "oscilloscope": "ui.pages.oscilloscope",
            "consumption_test": "ui.pages.consumption_test",
            "custom_test": "ui.pages.custom_test",
            "chamber": "ui.pages.chamber",
            "vmin_hunter": "ui.pages.vmin_hunter",
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

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange and getattr(self, "top_bar", None) is not None:
            self.top_bar.sync_max_icon()

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
                    return True, 0
                return False, 0
            if msg.message == _WM_GETMINMAXINFO:
                if self._adjust_maximized_size(msg):
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

    def closeEvent(self, event):
        self.status_panel.suppress_toasts()
        self._save_ai_panel_state()
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
