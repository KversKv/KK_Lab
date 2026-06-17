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
    Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QEvent, QPoint
)

if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    _WM_NCHITTEST = 0x0084
    _HTLEFT = 10
    _HTRIGHT = 11
    _HTTOP = 12
    _HTTOPLEFT = 13
    _HTTOPRIGHT = 14
    _HTBOTTOM = 15
    _HTBOTTOMLEFT = 16
    _HTBOTTOMRIGHT = 17

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
from core.instruments import InstrumentManager, InstrumentSpec
from instruments.base.visa_instrument import VisaInstrument
from ui.styles import SCROLLBAR_STYLE
from ui.nav_controller import NavController
from ui.instrument_status import InstrumentStatusPanel
from ui.app_top_bar import AppTopBar
from ui.ai.ai_assist_panel import AIAssistPanel
from ui.ai.panel_state import load_panel_state, save_panel_state, clamp_width
from core.ai.config import AISettings
from core.ai.ai_service import AIService
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

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
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
        self.n6705c_top.set_instrument_manager(self.instrument_manager)
        self.mso64b_top = MSO64BTop(self)
        self.mso64b_top.set_instrument_manager(self.instrument_manager)

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

        self.ai_settings = AISettings.load()
        self.ai_service = AIService(
            self.ai_settings,
            page_key_getter=self._get_ai_page_key,
            parent=self,
        )
        self.ai_service.set_serial_status_getter(self._get_ai_serial_status)
        self.ai_service.set_execution_logs_getter(self._get_ai_execution_logs)
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
        outer_splitter = QSplitter(Qt.Horizontal)
        outer_splitter.addWidget(main_splitter)

        self.ai_panel = AIAssistPanel(self.ai_service, parent=self)
        self.ai_panel.request_close.connect(self._on_ai_panel_close_requested)
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

    def _apply_ai_panel_visibility(self, visible):
        self.ai_panel.setVisible(visible)
        if visible:
            total = max(self.outer_splitter.width(), 800)
            self.outer_splitter.setSizes([total - self._ai_panel_width, self._ai_panel_width])

    def _on_ai_panel_toggled(self, checked):
        self._apply_ai_panel_visibility(checked)

    def _on_ai_panel_close_requested(self):
        self.top_bar.ai_panel_button.setChecked(False)

    def _get_ai_page_key(self):
        return self._get_current_help_key()

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

        self.n6705c_top.connection_changed.connect(self._update_instrument_status)
        self.mso64b_top.connection_changed.connect(self._update_instrument_status)
        self.instrument_manager.sessions_changed.connect(self._update_instrument_status)

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
            self._apply_dwm_round_corners()
            self._dwm_applied = True

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

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG" and not self.isMaximized():
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
            except (TypeError, ValueError):
                return False, 0
            if msg.message == _WM_NCHITTEST:
                global_x = ctypes.c_int16(msg.lParam & 0xFFFF).value
                global_y = ctypes.c_int16((msg.lParam >> 16) & 0xFFFF).value
                pos = self.mapFromGlobal(QPoint(global_x, global_y))
                x, y = pos.x(), pos.y()
                w, h = self.width(), self.height()
                b = self._resize_border
                left, right = x < b, x > w - b
                top, bottom = y < b, y > h - b
                if top and left:
                    return True, _HTTOPLEFT
                if top and right:
                    return True, _HTTOPRIGHT
                if bottom and left:
                    return True, _HTBOTTOMLEFT
                if bottom and right:
                    return True, _HTBOTTOMRIGHT
                if left:
                    return True, _HTLEFT
                if right:
                    return True, _HTRIGHT
                if top:
                    return True, _HTTOP
                if bottom:
                    return True, _HTBOTTOM
        return super().nativeEvent(event_type, message)

    def closeEvent(self, event):
        self.status_panel.suppress_toasts()
        self._save_ai_panel_state()
        if getattr(self, "ai_service", None) is not None:
            self.ai_service.shutdown()
        self.instrument_manager.shutdown()
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
