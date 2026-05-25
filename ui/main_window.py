#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

import os
from ui.resource_path import get_resource_base

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QSplitter, QFrame, QDialog, QTextBrowser, QGraphicsOpacityEffect
)

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPalette, QColor, QFont
from ui.pages.oscilloscope.oscilloscope_base_ui import OscilloscopeBaseUI
from ui.pages.n6705c_power_analyzer.n6705c_analyser_ui import N6705CAnalyserUI
from ui.pages.n6705c_power_analyzer.n6705c_datalog_ui import N6705CDatalogUI
from ui.pages.n6705c_power_analyzer.n6705c_top import N6705CTop
from ui.pages.oscilloscope.mso64b_top import MSO64BTop
from ui.pages.pmu_test.pmu_test_ui import PMUTestUI
from ui.pages.chamber.vt6002_chamber_ui import VT6002ChamberUI
from ui.pages.consumption_test.consumption_test_wrapper import ConsumptionTestWrapper
from ui.pages.charger_test.charger_test_ui import ChargerTestUI
from ui.pages.custom_test.custom_test_ui import CustomTestUI
from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin
from core.test_manager import TestManager
from core.instruments import InstrumentManager, InstrumentSpec
from instruments.base.visa_instrument import VisaInstrument
from instruments.chambers.vt6002_chamber import VT6002
from ui.styles import SCROLLBAR_STYLE
from ui.nav_controller import NavController
from ui.instrument_status import InstrumentStatusPanel
from ui.cleanup_mixin import CleanupMixin
from log_config import get_logger
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


class MainWindow(CleanupMixin, QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("功耗测试工具")
        self.setGeometry(100, 100, 1200, 800)

        self.test_manager = TestManager()
        self.visa_instrument = VisaInstrument()
        self.vt6002_chamber = None

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
        self.vt6002_chamber_ui = None
        self.consumption_test_ui = None
        self.charger_test_ui = None
        self.custom_test_ui = None
        self.kk_serials_ui = None
        self.current_instrument_ui = None
        self.channels = []

        self.nav = NavController(self)
        self.status_panel = InstrumentStatusPanel(self)

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

        self.main_layout.addWidget(main_splitter)

    def _connect_signals(self):
        self.nav.n6705c_power_analyzer_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.oscilloscope_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.chamber_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.pmu_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.charger_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.consumption_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.custom_test_btn.clicked.connect(self._on_nav_button_clicked)
        self.nav.kk_serials_btn.clicked.connect(self._on_nav_button_clicked)

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
        if self.vt6002_chamber_ui is None:
            self.vt6002_chamber_ui = VT6002ChamberUI(
                instrument_manager=self.instrument_manager,
            )
            self.vt6002_chamber_ui.connection_changed.connect(self._update_instrument_status)
            self.instrument_ui_container_layout.addWidget(self.vt6002_chamber_ui)
        else:
            self.vt6002_chamber_ui.show()
        self.current_instrument_ui = "thermal_chamber"
        self._fade_in_widget(self.vt6002_chamber_ui)

    def _create_pmu_test_ui(self, selected_test=None):
        logger.debug("Switching to PMU Test UI: selected_test=%s", selected_test)
        self._hide_all_instrument_uis()
        if self.pmu_test_ui is None:
            self.pmu_test_ui = PMUTestUI(
                n6705c_top=self.n6705c_top,
                mso64b_top=self.mso64b_top,
                vt6002_chamber_ui=self.vt6002_chamber_ui,
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
                vt6002_chamber_ui=self.vt6002_chamber_ui,
                instrument_manager=self.instrument_manager,
            )
            self.instrument_ui_container_layout.addWidget(self.custom_test_ui)
        else:
            self.custom_test_ui.sync_n6705c_from_top()
            self.custom_test_ui.show()
        self.current_instrument_ui = "custom_test"
        self._fade_in_widget(self.custom_test_ui)

    def _create_kk_serials_ui(self):
        logger.debug("Switching to KK Serials UI")
        self._hide_all_instrument_uis()
        if self.kk_serials_ui is None:
            self.kk_serials_ui = _KKSerialsPage()
            self.instrument_ui_container_layout.addWidget(self.kk_serials_ui)
        else:
            self.kk_serials_ui.show()
        self.current_instrument_ui = "kk_serials"
        self._fade_in_widget(self.kk_serials_ui)

    def _hide_all_instrument_uis(self):
        for widget in [
            self.n6705c_analyser_ui, self.n6705c_datalog_ui,
            self.oscilloscope_ui, self.pmu_test_ui, self.vt6002_chamber_ui,
            self.consumption_test_ui, self.charger_test_ui, self.custom_test_ui,
            self.kk_serials_ui,
        ]:
            if widget is not None:
                widget.setGraphicsEffect(None)
                widget.hide()

    def _fade_in_widget(self, widget):
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

    def _on_help(self):
        help_key = self._get_current_help_key()
        helps_dir = os.path.join(get_resource_base(), "helps")
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

    def closeEvent(self, event):
        self.status_panel.suppress_toasts()
        self.instrument_manager.shutdown()
        self._perform_close_cleanup()
        super().closeEvent(event)
