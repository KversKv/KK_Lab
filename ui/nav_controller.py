import os
from ui.resource_path import get_resource_base

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QButtonGroup,
)
from PySide6.QtCore import Qt, Signal, QEvent, QPoint, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from ui.widgets.sidebar_nav_button import SidebarNavButton
from ui.widgets.sidebar_submenu import SidebarSubMenu
from log_config import get_logger

logger = get_logger(__name__)

_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "main_window_SVGs"
)

_SUBMENU_HIDE_DELAY = 220


class NavController:
    nav_page_requested = None

    def __init__(self, host):
        self._host = host
        self._pmu_btn_hovered = False
        self._pa_btn_hovered = False
        self._charger_btn_hovered = False
        self._consumption_btn_hovered = False

        self.current_pa_mode = "analyser"
        self.current_pmu_test_key = None
        self.current_charger_test_key = None
        self.current_consumption_test_key = "auto_test"

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

        self.consumption_test_tab_map = {
            "auto_test": 0,
            "high_low_temp": 1,
        }

    def create_left_nav(self):
        left_nav = QFrame()
        left_nav.setFixedWidth(187)
        left_nav.setObjectName("leftNav")
        left_nav.setStyleSheet("""
            QFrame#leftNav {
                background-color: #0b1020;
                border: none;
                border-radius: 0px;
            }
        """)

        left_nav_layout = QVBoxLayout(left_nav)
        left_nav_layout.setContentsMargins(10, 14, 10, 14)
        left_nav_layout.setSpacing(6)

        logo_label = QLabel("LabControl Pro")
        logo_label.setStyleSheet("""
            QLabel {
                color: #7ea1ff;
                font-size: 14px;
                font-weight: 700;
                padding: 4px 4px 8px 4px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(logo_label)

        instruments_title = QLabel("INSTRUMENTS")
        instruments_title.setStyleSheet("""
            QLabel {
                color: #5f78a8;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 6px 4px 2px 4px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(instruments_title)

        self.n6705c_power_analyzer_btn = SidebarNavButton(
            "N6705C", "", os.path.join(_PAGE_SVGS_DIR, "zap.svg")
        )
        self.n6705c_power_analyzer_btn.setChecked(True)

        self.oscilloscope_btn = SidebarNavButton(
            "Oscilloscope", "", os.path.join(_PAGE_SVGS_DIR, "activity.svg")
        )

        self.chamber_btn = SidebarNavButton(
            "Chamber", "", os.path.join(_PAGE_SVGS_DIR, "thermometer.svg")
        )

        left_nav_layout.addWidget(self.n6705c_power_analyzer_btn)
        left_nav_layout.addWidget(self.oscilloscope_btn)
        left_nav_layout.addWidget(self.chamber_btn)

        automation_title = QLabel("AUTOMATION")
        automation_title.setStyleSheet("""
            QLabel {
                color: #7b93bf;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 4px 2px 4px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(automation_title)

        self.pmu_test_btn = SidebarNavButton(
            "PMU Test", "", os.path.join(_PAGE_SVGS_DIR, "settings.svg")
        )
        left_nav_layout.addWidget(self.pmu_test_btn)

        self.charger_test_btn = SidebarNavButton(
            "Charger Test", "", os.path.join(_PAGE_SVGS_DIR, "battery.svg")
        )
        left_nav_layout.addWidget(self.charger_test_btn)

        self.consumption_test_btn = SidebarNavButton(
            "Consumption Test", "", os.path.join(_PAGE_SVGS_DIR, "gauge.svg")
        )
        left_nav_layout.addWidget(self.consumption_test_btn)

        self.vmin_hunter_btn = SidebarNavButton(
            "VminHunter", "", os.path.join(_PAGE_SVGS_DIR, "crosshair.svg")
        )
        left_nav_layout.addWidget(self.vmin_hunter_btn)

        tools_title = QLabel("TOOLS")
        tools_title.setStyleSheet("""
            QLabel {
                color: #7b93bf;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 4px 2px 4px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(tools_title)

        self.kk_serials_btn = SidebarNavButton(
            "KK Serials", "", os.path.join(_PAGE_SVGS_DIR, "terminal.svg")
        )
        left_nav_layout.addWidget(self.kk_serials_btn)

        self.collection_btn = SidebarNavButton(
            "Collection", "", os.path.join(_PAGE_SVGS_DIR, "settings.svg")
        )
        left_nav_layout.addWidget(self.collection_btn)

        orchestration_title = QLabel("ORCHESTRATION")
        orchestration_title.setStyleSheet("""
            QLabel {
                color: #7b93bf;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 4px 2px 4px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(orchestration_title)

        self.orchestrator_btn = SidebarNavButton(
            "Orchestrator", "", os.path.join(_PAGE_SVGS_DIR, "network.svg")
        )
        left_nav_layout.addWidget(self.orchestrator_btn)

        self.nav_button_group = QButtonGroup(self._host)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.n6705c_power_analyzer_btn)
        self.nav_button_group.addButton(self.oscilloscope_btn)
        self.nav_button_group.addButton(self.chamber_btn)
        self.nav_button_group.addButton(self.pmu_test_btn)
        self.nav_button_group.addButton(self.charger_test_btn)
        self.nav_button_group.addButton(self.consumption_test_btn)
        self.nav_button_group.addButton(self.vmin_hunter_btn)
        self.nav_button_group.addButton(self.orchestrator_btn)
        self.nav_button_group.addButton(self.kk_serials_btn)
        self.nav_button_group.addButton(self.collection_btn)

        self._refresh_nav_arrow_state()

        left_nav_layout.addSpacing(20)
        left_nav_layout.addStretch()

        return left_nav, left_nav_layout

    def _refresh_nav_arrow_state(self):
        nav_buttons = [
            self.n6705c_power_analyzer_btn,
            self.oscilloscope_btn,
            self.chamber_btn,
            self.pmu_test_btn,
            self.charger_test_btn,
            self.consumption_test_btn,
            self.vmin_hunter_btn,
            self.orchestrator_btn,
            self.kk_serials_btn,
            self.collection_btn,
        ]
        for btn in nav_buttons:
            if hasattr(btn, "set_arrow_visible"):
                btn.set_arrow_visible(btn.isChecked())
            elif hasattr(btn, "arrow_label"):
                btn.arrow_label.setVisible(btn.isChecked())
            elif hasattr(btn, "right_arrow_label"):
                btn.right_arrow_label.setVisible(btn.isChecked())

    def create_submenus(self):
        self.pmu_submenu = SidebarSubMenu([
            ("dcdc_efficiency", "DCDC Efficiency"),
            ("output_voltage", "Output Voltage"),
            ("is_gain", "Is_gain"),
            ("oscp", "OSCP"),
            ("gpadc_test", "GPADC Test"),
            ("clk_test", "CLK Test"),
        ], parent=self._host)
        self.pmu_submenu.item_clicked.connect(self._on_pmu_submenu_clicked)
        self.pmu_test_btn.installEventFilter(self._host)
        self.pmu_submenu.installEventFilter(self._host)

        self.pa_submenu = SidebarSubMenu([
            ("analyser", "N6705C Analyser"),
            ("datalog", "N6705C Datalog"),
        ], parent=self._host)
        self.pa_submenu.item_clicked.connect(self._on_pa_submenu_clicked)
        self.n6705c_power_analyzer_btn.installEventFilter(self._host)
        self.pa_submenu.installEventFilter(self._host)

        self.charger_submenu = SidebarSubMenu([
            ("config_traverse", "Config Traverse Test"),
            ("status_register", "Status Register Test"),
            ("iterm", "Iterm Test"),
            ("regulation_voltage", "Regulation Voltage Test"),
        ], parent=self._host)
        self.charger_submenu.item_clicked.connect(self._on_charger_submenu_clicked)
        self.charger_test_btn.installEventFilter(self._host)
        self.charger_submenu.installEventFilter(self._host)

        self.consumption_submenu = SidebarSubMenu([
            ("auto_test", "Auto Test"),
            ("high_low_temp", "High-Low Temperature Test"),
        ], parent=self._host)
        self.consumption_submenu.item_clicked.connect(self._on_consumption_submenu_clicked)
        self.consumption_test_btn.installEventFilter(self._host)
        self.consumption_submenu.installEventFilter(self._host)

    def _hide_other_submenus(self, except_submenu):
        for submenu in (self.pa_submenu, self.pmu_submenu, self.charger_submenu, self.consumption_submenu):
            if submenu and submenu is not except_submenu and submenu.isVisible():
                submenu.force_hide()

    def _show_pa_submenu(self):
        if not self.pa_submenu:
            return
        self._hide_other_submenus(self.pa_submenu)
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
        logger.debug("PA submenu clicked: %s", mode_key)
        self.current_pa_mode = mode_key
        self.pa_submenu.set_current_item(mode_key)
        self.n6705c_power_analyzer_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._switch_pa_mode(mode_key)
        self.pa_submenu.hide()

    def _show_pmu_submenu(self):
        if not self.pmu_submenu:
            return
        self._hide_other_submenus(self.pmu_submenu)
        btn_global_pos = self.pmu_test_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.pmu_test_btn.width() + 8
        y = btn_global_pos.y()
        self.pmu_submenu.set_current_item(self.current_pmu_test_key)
        self.pmu_submenu.move(x, y)
        self.pmu_submenu.show()
        self.pmu_submenu.raise_()

    def _hide_pmu_submenu_if_needed(self):
        if self._pmu_btn_hovered:
            return
        if self.pmu_submenu and self.pmu_submenu.is_hovered():
            return
        if self.pmu_submenu:
            self.pmu_submenu.hide()

    def _on_pmu_submenu_clicked(self, test_key):
        logger.debug("PMU submenu clicked: %s", test_key)
        self.current_pmu_test_key = test_key
        self.pmu_submenu.set_current_item(test_key)
        self.pmu_test_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._create_pmu_test_ui(selected_test=test_key)
        self.pmu_submenu.hide()

    def _show_charger_submenu(self):
        if not self.charger_submenu:
            return
        self._hide_other_submenus(self.charger_submenu)
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
        logger.debug("Charger submenu clicked: %s", test_key)
        self.current_charger_test_key = test_key
        self.charger_submenu.set_current_item(test_key)
        self.charger_test_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._create_charger_test_ui(selected_test=test_key)
        self.charger_submenu.hide()

    def _show_consumption_submenu(self):
        if not self.consumption_submenu:
            return
        self._hide_other_submenus(self.consumption_submenu)
        btn_global_pos = self.consumption_test_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.consumption_test_btn.width() + 8
        y = btn_global_pos.y()
        self.consumption_submenu.set_current_item(self.current_consumption_test_key)
        self.consumption_submenu.move(x, y)
        self.consumption_submenu.show()
        self.consumption_submenu.raise_()

    def _hide_consumption_submenu_if_needed(self):
        if self._consumption_btn_hovered:
            return
        if self.consumption_submenu and self.consumption_submenu.is_hovered():
            return
        if self.consumption_submenu:
            self.consumption_submenu.hide()

    def _on_consumption_submenu_clicked(self, test_key):
        logger.debug("Consumption submenu clicked: %s", test_key)
        self.current_consumption_test_key = test_key
        self.consumption_submenu.set_current_item(test_key)
        self.consumption_test_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._create_consumption_test_ui(selected_test=test_key)
        self.consumption_submenu.hide()

    def handle_event_filter(self, obj, event):
        if obj == self.pmu_test_btn:
            if event.type() == QEvent.Enter:
                self._pmu_btn_hovered = True
                self._show_pmu_submenu()
            elif event.type() == QEvent.Leave:
                self._pmu_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_pmu_submenu_if_needed)
            return True

        elif obj == self.pmu_submenu:
            if event.type() == QEvent.Enter:
                self._show_pmu_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_pmu_submenu_if_needed)
            return True

        elif obj == self.n6705c_power_analyzer_btn:
            if event.type() == QEvent.Enter:
                self._pa_btn_hovered = True
                self._show_pa_submenu()
            elif event.type() == QEvent.Leave:
                self._pa_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_pa_submenu_if_needed)
            return True

        elif obj == self.pa_submenu:
            if event.type() == QEvent.Enter:
                self._show_pa_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_pa_submenu_if_needed)
            return True

        elif obj == self.charger_test_btn:
            if event.type() == QEvent.Enter:
                self._charger_btn_hovered = True
                self._show_charger_submenu()
            elif event.type() == QEvent.Leave:
                self._charger_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_charger_submenu_if_needed)
            return True

        elif obj == self.charger_submenu:
            if event.type() == QEvent.Enter:
                self._show_charger_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_charger_submenu_if_needed)
            return True

        elif obj == self.consumption_test_btn:
            if event.type() == QEvent.Enter:
                self._consumption_btn_hovered = True
                self._show_consumption_submenu()
            elif event.type() == QEvent.Leave:
                self._consumption_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_consumption_submenu_if_needed)
            return True

        elif obj == self.consumption_submenu:
            if event.type() == QEvent.Enter:
                self._show_consumption_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_consumption_submenu_if_needed)
            return True

        return False

    def handle_nav_button_clicked(self, sender):
        if sender == self.n6705c_power_analyzer_btn:
            self.pmu_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._show_pa_submenu()
            self._host._switch_pa_mode(self.current_pa_mode)

        elif sender == self.oscilloscope_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_oscilloscope_ui()

        elif sender == self.chamber_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_thermal_chamber_ui()

        elif sender == self.pmu_test_btn:
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_pmu_test_ui(selected_test=self.current_pmu_test_key)
            self._show_pmu_submenu()

        elif sender == self.charger_test_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_charger_test_ui(selected_test=self.current_charger_test_key)
            self._show_charger_submenu()

        elif sender == self.consumption_test_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self._host._create_consumption_test_ui(selected_test=self.current_consumption_test_key)
            self._show_consumption_submenu()

        elif sender == self.vmin_hunter_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_vmin_hunter_ui()

        elif sender == self.orchestrator_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_orchestrator_ui()

        elif sender == self.kk_serials_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_kk_serials_ui()

        elif sender == self.collection_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self._host._create_collection_ui()

        self._refresh_nav_arrow_state()

    def setup_shortcuts(self):
        shortcuts = [
            ("Ctrl+1", self.n6705c_power_analyzer_btn),
            ("Ctrl+2", self.oscilloscope_btn),
            ("Ctrl+3", self.chamber_btn),
            ("Ctrl+4", self.pmu_test_btn),
            ("Ctrl+5", self.charger_test_btn),
            ("Ctrl+6", self.consumption_test_btn),
            ("Ctrl+7", self.vmin_hunter_btn),
            ("Ctrl+8", self.orchestrator_btn),
            ("Ctrl+9", self.kk_serials_btn),
            ("Ctrl+0", self.collection_btn),
        ]
        for key_seq, btn in shortcuts:
            sc = QShortcut(QKeySequence(key_seq), self._host)
            sc.activated.connect(btn.click)
            tooltip = btn.toolTip()
            shortcut_hint = f"  [{key_seq}]"
            if shortcut_hint not in (tooltip or ""):
                btn.setToolTip((tooltip or btn.title_label.text()) + shortcut_hint)

    def hide_all_submenus(self):
        for submenu in (self.pa_submenu, self.pmu_submenu, self.charger_submenu, self.consumption_submenu):
            if submenu and submenu.isVisible():
                submenu.hide()
