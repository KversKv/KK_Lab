import os
from ui.resource_path import get_resource_base

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QButtonGroup,
    QScrollArea, QSizePolicy, QSpacerItem,
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

# ── 密度令牌（按窗口高度切换，逻辑像素）──
_DENSITY_COMFORTABLE_MIN = 760
_DENSITY_COMPACT_MIN = 700
_DENSITY_HYSTERESIS = 12  # 滞回带，避免阈值附近来回抖动

# 密度 → 按钮内部布局 margins（内容区恒定 24px，容纳 18px 图标 + 文字行）
_DENSITY_BUTTON_MARGINS = {
    "comfortable": (10, 6, 10, 6),
    "compact": (10, 4, 10, 4),
    "dense": (10, 2, 10, 2),
}

# 密度 → 导航容器 layout spacing
_DENSITY_LAYOUT_SPACING = {"comfortable": 6, "compact": 4, "dense": 3}

# 密度 → 分组间距（标题前置 QSpacerItem 高度；不用 QSS padding 实现，原因见下）
_DENSITY_GROUP_GAP = {"comfortable": 20, "compact": 14, "dense": 8}

# left_nav 三段式 + 密度令牌 QSS。
# 按钮/标题高度一律 QSS min-height == max-height 钉死（盒模型：总高 =
# content(min/max-height) + 上下 padding + 2×border；按钮 border:none、
# padding:0）。
# 坑：QLabel 的 QSS padding 会在 polish 时写入 QWidget::contentsMargins，
# 密度属性切换重 polish 后，min/max 尺寸约束按新规则更新、contentsMargins
# 却仍按旧值扣减（实测 dense 下标题总高 24 而 contentsRect 仅 2px，文字
# 被裁）。故分组标题不设随密度变化的 padding，组间距改由布局内
# QSpacerItem 承担，标题 QSS padding 保持恒定。
_LEFT_NAV_QSS = """
QFrame#leftNav {
    background-color: #0b1020;
    border: none;
    border-radius: 0px;
}
QLabel#navLogo {
    color: #7ea1ff;
    font-size: 14px;
    font-weight: 700;
    padding: 4px 4px 8px 4px;
    border: none;
    background: transparent;
}
QScrollArea#navScrollArea {
    background: transparent;
    border: none;
}
QWidget#navScrollContent {
    background: transparent;
}
QLabel#navGroupTitle {
    color: #7b93bf;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    border: none;
    background: transparent;
    min-height: 14px;
    max-height: 14px;
    padding: 0px 4px;
}
SidebarNavButton[density="comfortable"] {
    min-height: 36px;
    max-height: 36px;
    padding: 0px;
}
SidebarNavButton[density="compact"] {
    min-height: 32px;
    max-height: 32px;
    padding: 0px;
}
SidebarNavButton[density="dense"] {
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
}
"""


class NavController:
    nav_page_requested = None

    def __init__(self, host):
        self._host = host
        self._pmu_btn_hovered = False
        self._pa_btn_hovered = False
        self._charger_btn_hovered = False
        self._consumption_btn_hovered = False
        self._module_test_btn_hovered = False
        self._collection_btn_hovered = False
        self._pmu_tool_btn_hovered = False
        self._vmin_hunter_btn_hovered = False

        # 密度令牌状态：comfortable / compact / dense（由 update_density 驱动）
        self._density = "comfortable"
        self._density_widgets = []
        self._group_gap_items = []
        self._nav_layout = None
        self.nav_scroll_area = None

        self.current_pa_mode = "analyser"
        self.current_pmu_test_key = None
        self.current_charger_test_key = None
        self.current_consumption_test_key = "auto_test"
        self.current_module_test_key = "ldo"
        self.current_collection_key = "mcu_io"
        self.current_pmu_tool_key = "1811"
        self.current_vmin_hunter_key = "hunt"

        self.module_test_tab_map = {"ldo": 0, "dcdc": 1}

        self.vmin_hunter_tab_map = {"hunt": 0, "single_test": 1}

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
        """构建 left_nav 三段式：Logo（固定）/ 导航滚动区（唯一伸缩）/ 底部状态面板。

        底部状态面板由 MainWindow 向返回的 root_layout 末尾追加（固定段，
        不压缩、不进滚动区）。导航按钮/分组标题高度由密度令牌 QSS
        （min-height == max-height）钉死；高度不足时滚动区出纵向滚动条，
        而非整体等比压缩控件。
        """
        left_nav = QFrame()
        left_nav.setFixedWidth(187)
        left_nav.setObjectName("leftNav")
        left_nav.setStyleSheet(_LEFT_NAV_QSS)

        root_layout = QVBoxLayout(left_nav)
        root_layout.setContentsMargins(10, 14, 10, 14)
        root_layout.setSpacing(6)

        # ── 段 1：Logo（垂直 Fixed，永不压缩、不进滚动区）
        logo_label = QLabel("LabControl Pro")
        logo_label.setObjectName("navLogo")
        logo_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        root_layout.addWidget(logo_label)

        # ── 段 2：导航滚动区（唯一伸缩段；横向 AlwaysOff + widgetResizable，
        #    滚动条 gutter 稳定，不引起横向抖动）
        scroll_area = QScrollArea()
        scroll_area.setObjectName("navScrollArea")
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        nav_container = QWidget()
        nav_container.setObjectName("navScrollContent")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(_DENSITY_LAYOUT_SPACING[self._density])
        self._nav_layout = nav_layout

        self._add_group_title("INSTRUMENTS", nav_layout, first=True)

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

        self._register_nav_button(self.n6705c_power_analyzer_btn, nav_layout)
        self._register_nav_button(self.oscilloscope_btn, nav_layout)
        self._register_nav_button(self.chamber_btn, nav_layout)

        self._add_group_title("AUTOMATION", nav_layout)

        self.pmu_test_btn = SidebarNavButton(
            "PMU Test", "", os.path.join(_PAGE_SVGS_DIR, "settings.svg")
        )
        self._register_nav_button(self.pmu_test_btn, nav_layout)

        self.charger_test_btn = SidebarNavButton(
            "Charger Test", "", os.path.join(_PAGE_SVGS_DIR, "battery.svg")
        )
        self._register_nav_button(self.charger_test_btn, nav_layout)

        self.module_test_btn = SidebarNavButton(
            "Module Test", "", os.path.join(_PAGE_SVGS_DIR, "module_test.svg")
        )
        self._register_nav_button(self.module_test_btn, nav_layout)

        self.consumption_test_btn = SidebarNavButton(
            "Consumption Test", "", os.path.join(_PAGE_SVGS_DIR, "gauge.svg")
        )
        self._register_nav_button(self.consumption_test_btn, nav_layout)

        self.vmin_hunter_btn = SidebarNavButton(
            "VminHunter", "", os.path.join(_PAGE_SVGS_DIR, "crosshair.svg")
        )
        self._register_nav_button(self.vmin_hunter_btn, nav_layout)

        self._add_group_title("TOOLS", nav_layout)

        self.pmu_btn = SidebarNavButton(
            "PMU", "", os.path.join(_PAGE_SVGS_DIR, "zap.svg")
        )
        self._register_nav_button(self.pmu_btn, nav_layout)

        self.collection_btn = SidebarNavButton(
            "Collection", "", os.path.join(_PAGE_SVGS_DIR, "settings.svg")
        )
        self._register_nav_button(self.collection_btn, nav_layout)

        self._add_group_title("ORCHESTRATION", nav_layout)

        self.orchestrator_btn = SidebarNavButton(
            "Orchestrator", "", os.path.join(_PAGE_SVGS_DIR, "network.svg")
        )
        self._register_nav_button(self.orchestrator_btn, nav_layout)

        self.nav_button_group = QButtonGroup(self._host)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.n6705c_power_analyzer_btn)
        self.nav_button_group.addButton(self.oscilloscope_btn)
        self.nav_button_group.addButton(self.chamber_btn)
        self.nav_button_group.addButton(self.pmu_test_btn)
        self.nav_button_group.addButton(self.charger_test_btn)
        self.nav_button_group.addButton(self.module_test_btn)
        self.nav_button_group.addButton(self.consumption_test_btn)
        self.nav_button_group.addButton(self.vmin_hunter_btn)
        self.nav_button_group.addButton(self.orchestrator_btn)
        self.nav_button_group.addButton(self.pmu_btn)
        self.nav_button_group.addButton(self.collection_btn)

        self._refresh_nav_arrow_state()

        # 末尾 stretch 把按钮顶到上方；高度不足时由滚动条接管而非压缩按钮
        nav_layout.addStretch(1)
        scroll_area.setWidget(nav_container)
        root_layout.addWidget(scroll_area, 1)
        self.nav_scroll_area = scroll_area

        return left_nav, root_layout

    def _add_group_title(self, text, layout, first=False):
        """添加分组标题；组间距由前置 QSpacerItem 承担（密度令牌驱动）。

        标题高度恒 14px（QSS min==max + 恒定 padding），不设随密度变化的
        QSS padding：QLabel 的 QSS padding 会写入 contentsMargins，动态
        属性重 polish 后与尺寸约束不同步（实测 dense 下标题内容区仅 2px）。
        """
        if not first:
            gap = _DENSITY_GROUP_GAP[self._density]
            spacer = QSpacerItem(0, gap, QSizePolicy.Fixed, QSizePolicy.Fixed)
            layout.addItem(spacer)
            self._group_gap_items.append(spacer)
        label = QLabel(text)
        label.setObjectName("navGroupTitle")
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(label)

    def _register_nav_button(self, btn, layout):
        """登记导航按钮：垂直 Fixed + 密度属性。

        解除 SidebarNavButton 构造里 setFixedHeight(48) 的硬约束
        （QWIDGETSIZE_MAX = 16777215），高度统一交给密度 QSS
        （min-height == max-height），保证 28/32/36px 档位不被压缩。
        """
        btn.setProperty("density", self._density)
        btn.setMinimumHeight(0)
        btn.setMaximumHeight(16777215)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._density_widgets.append(btn)
        layout.addWidget(btn)

    def update_density(self, height):
        """按窗口高度切换密度令牌（阈值 760/700，带 12px 滞回防临界抖动）。"""
        cur = self._density
        h = int(height)
        if cur == "comfortable":
            if h < _DENSITY_COMFORTABLE_MIN - _DENSITY_HYSTERESIS:
                new = "compact" if h >= _DENSITY_COMPACT_MIN else "dense"
            else:
                new = cur
        elif cur == "dense":
            if h >= _DENSITY_COMPACT_MIN + _DENSITY_HYSTERESIS:
                new = "comfortable" if h >= _DENSITY_COMFORTABLE_MIN else "compact"
            else:
                new = cur
        else:  # compact
            if h >= _DENSITY_COMFORTABLE_MIN + _DENSITY_HYSTERESIS:
                new = "comfortable"
            elif h < _DENSITY_COMPACT_MIN - _DENSITY_HYSTERESIS:
                new = "dense"
            else:
                new = cur
        if new != cur:
            self._apply_density(new)

    def _apply_density(self, density):
        """应用密度：刷新按钮的 density 属性并 polish 重刷 QSS；组间距
        spacer、按钮内边距、容器 spacing 同步切档，保证内容区可读。"""
        self._density = density
        margins = _DENSITY_BUTTON_MARGINS[density]
        gap = _DENSITY_GROUP_GAP[density]
        for item in self._group_gap_items:
            item.changeSize(0, gap, QSizePolicy.Fixed, QSizePolicy.Fixed)
        if self._nav_layout is not None:
            self._nav_layout.setSpacing(_DENSITY_LAYOUT_SPACING[density])
            self._nav_layout.invalidate()
        for w in self._density_widgets:
            w.setProperty("density", density)
            if isinstance(w, SidebarNavButton):
                inner = w.layout()
                if inner is not None:
                    inner.setContentsMargins(*margins)
            w.style().unpolish(w)
            w.style().polish(w)
            w.updateGeometry()

    def _refresh_nav_arrow_state(self):
        nav_buttons = [
            self.n6705c_power_analyzer_btn,
            self.oscilloscope_btn,
            self.chamber_btn,
            self.pmu_test_btn,
            self.charger_test_btn,
            self.consumption_test_btn,
            self.module_test_btn,
            self.vmin_hunter_btn,
            self.orchestrator_btn,
            self.pmu_btn,
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

        self.module_test_submenu = SidebarSubMenu([
            ("ldo", "LDO"),
            ("dcdc", "DCDC"),
        ], parent=self._host)
        self.module_test_submenu.item_clicked.connect(self._on_module_test_submenu_clicked)
        self.module_test_btn.installEventFilter(self._host)
        self.module_test_submenu.installEventFilter(self._host)

        self.collection_submenu = SidebarSubMenu([
            ("mcu_io", "MCU IO"),
            ("kk_serials", "KK Serials"),
            ("i2c_control", "IIC Control"),
        ], parent=self._host)
        self.collection_submenu.item_clicked.connect(self._on_collection_submenu_clicked)
        self.collection_btn.installEventFilter(self._host)
        self.collection_submenu.installEventFilter(self._host)

        self.pmu_tool_submenu = SidebarSubMenu([
            ("1811", "1811"),
            ("1860", "1860"),
        ], parent=self._host)
        self.pmu_tool_submenu.item_clicked.connect(self._on_pmu_tool_submenu_clicked)
        self.pmu_btn.installEventFilter(self._host)
        self.pmu_tool_submenu.installEventFilter(self._host)

        self.vmin_hunter_submenu = SidebarSubMenu([
            ("hunt", "Vmin Hunt"),
            ("single_test", "Single Vmin Test"),
        ], parent=self._host)
        self.vmin_hunter_submenu.item_clicked.connect(self._on_vmin_hunter_submenu_clicked)
        self.vmin_hunter_btn.installEventFilter(self._host)
        self.vmin_hunter_submenu.installEventFilter(self._host)

    def _hide_other_submenus(self, except_submenu):
        for submenu in (self.pa_submenu, self.pmu_submenu, self.charger_submenu,
                        self.consumption_submenu, self.module_test_submenu,
                        self.collection_submenu, self.pmu_tool_submenu,
                        self.vmin_hunter_submenu):
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

    def _show_module_test_submenu(self):
        if not self.module_test_submenu:
            return
        self._hide_other_submenus(self.module_test_submenu)
        btn_global_pos = self.module_test_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.module_test_btn.width() + 8
        y = btn_global_pos.y()
        self.module_test_submenu.set_current_item(self.current_module_test_key)
        self.module_test_submenu.move(x, y)
        self.module_test_submenu.show()
        self.module_test_submenu.raise_()

    def _hide_module_test_submenu_if_needed(self):
        if self._module_test_btn_hovered:
            return
        if self.module_test_submenu and self.module_test_submenu.is_hovered():
            return
        if self.module_test_submenu:
            self.module_test_submenu.hide()

    def _on_module_test_submenu_clicked(self, test_key):
        logger.debug("Module Test submenu clicked: %s", test_key)
        self.current_module_test_key = test_key
        self.module_test_submenu.set_current_item(test_key)
        self.module_test_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._create_module_test_ui(selected_test=test_key)
        self.module_test_submenu.hide()

    def _show_collection_submenu(self):
        if not self.collection_submenu:
            return
        self._hide_other_submenus(self.collection_submenu)
        btn_global_pos = self.collection_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.collection_btn.width() + 8
        y = btn_global_pos.y()
        self.collection_submenu.set_current_item(self.current_collection_key)
        self.collection_submenu.move(x, y)
        self.collection_submenu.show()
        self.collection_submenu.raise_()

    def _hide_collection_submenu_if_needed(self):
        if self._collection_btn_hovered:
            return
        if self.collection_submenu and self.collection_submenu.is_hovered():
            return
        if self.collection_submenu:
            self.collection_submenu.hide()

    def _on_collection_submenu_clicked(self, sub_key):
        logger.debug("Collection submenu clicked: %s", sub_key)
        self.current_collection_key = sub_key
        self.collection_submenu.set_current_item(sub_key)
        self.collection_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._create_collection_ui(selected_key=sub_key)
        self.collection_submenu.hide()

    def _show_pmu_tool_submenu(self):
        if not self.pmu_tool_submenu:
            return
        self._hide_other_submenus(self.pmu_tool_submenu)
        btn_global_pos = self.pmu_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.pmu_btn.width() + 8
        y = btn_global_pos.y()
        self.pmu_tool_submenu.set_current_item(self.current_pmu_tool_key)
        self.pmu_tool_submenu.move(x, y)
        self.pmu_tool_submenu.show()
        self.pmu_tool_submenu.raise_()

    def _hide_pmu_tool_submenu_if_needed(self):
        if self._pmu_tool_btn_hovered:
            return
        if self.pmu_tool_submenu and self.pmu_tool_submenu.is_hovered():
            return
        if self.pmu_tool_submenu:
            self.pmu_tool_submenu.hide()

    def _on_pmu_tool_submenu_clicked(self, sub_key):
        logger.debug("PMU tool submenu clicked: %s", sub_key)
        self.current_pmu_tool_key = sub_key
        self.pmu_tool_submenu.set_current_item(sub_key)
        self.pmu_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._create_pmu_ui(selected_key=sub_key)
        self.pmu_tool_submenu.hide()

    def _show_vmin_hunter_submenu(self):
        if not self.vmin_hunter_submenu:
            return
        self._hide_other_submenus(self.vmin_hunter_submenu)
        btn_global_pos = self.vmin_hunter_btn.mapToGlobal(QPoint(0, 0))
        x = btn_global_pos.x() + self.vmin_hunter_btn.width() + 8
        y = btn_global_pos.y()
        self.vmin_hunter_submenu.set_current_item(self.current_vmin_hunter_key)
        self.vmin_hunter_submenu.move(x, y)
        self.vmin_hunter_submenu.show()
        self.vmin_hunter_submenu.raise_()

    def _hide_vmin_hunter_submenu_if_needed(self):
        if self._vmin_hunter_btn_hovered:
            return
        if self.vmin_hunter_submenu and self.vmin_hunter_submenu.is_hovered():
            return
        if self.vmin_hunter_submenu:
            self.vmin_hunter_submenu.hide()

    def _on_vmin_hunter_submenu_clicked(self, test_key):
        logger.debug("VminHunter submenu clicked: %s", test_key)
        self.current_vmin_hunter_key = test_key
        self.vmin_hunter_submenu.set_current_item(test_key)
        self.vmin_hunter_btn.setChecked(True)
        self._refresh_nav_arrow_state()
        self._host._create_vmin_hunter_ui(selected_test=test_key)
        self.vmin_hunter_submenu.hide()

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

        elif obj == self.module_test_btn:
            if event.type() == QEvent.Enter:
                self._module_test_btn_hovered = True
                self._show_module_test_submenu()
            elif event.type() == QEvent.Leave:
                self._module_test_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_module_test_submenu_if_needed)
            return True

        elif obj == self.module_test_submenu:
            if event.type() == QEvent.Enter:
                self._show_module_test_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_module_test_submenu_if_needed)
            return True

        elif obj == self.collection_btn:
            if event.type() == QEvent.Enter:
                self._collection_btn_hovered = True
                self._show_collection_submenu()
            elif event.type() == QEvent.Leave:
                self._collection_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_collection_submenu_if_needed)
            return True

        elif obj == self.collection_submenu:
            if event.type() == QEvent.Enter:
                self._show_collection_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_collection_submenu_if_needed)
            return True

        elif obj == self.pmu_btn:
            if event.type() == QEvent.Enter:
                self._pmu_tool_btn_hovered = True
                self._show_pmu_tool_submenu()
            elif event.type() == QEvent.Leave:
                self._pmu_tool_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_pmu_tool_submenu_if_needed)
            return True

        elif obj == self.pmu_tool_submenu:
            if event.type() == QEvent.Enter:
                self._show_pmu_tool_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_pmu_tool_submenu_if_needed)
            return True

        elif obj == self.vmin_hunter_btn:
            if event.type() == QEvent.Enter:
                self._vmin_hunter_btn_hovered = True
                self._show_vmin_hunter_submenu()
            elif event.type() == QEvent.Leave:
                self._vmin_hunter_btn_hovered = False
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_vmin_hunter_submenu_if_needed)
            return True

        elif obj == self.vmin_hunter_submenu:
            if event.type() == QEvent.Enter:
                self._show_vmin_hunter_submenu()
            elif event.type() == QEvent.Leave:
                QTimer.singleShot(_SUBMENU_HIDE_DELAY, self._hide_vmin_hunter_submenu_if_needed)
            return True

        return False

    def handle_nav_button_clicked(self, sender):
        if sender == self.n6705c_power_analyzer_btn:
            self.pmu_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._show_pa_submenu()
            self._host._switch_pa_mode(self.current_pa_mode)

        elif sender == self.oscilloscope_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_oscilloscope_ui()

        elif sender == self.chamber_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_thermal_chamber_ui()

        elif sender == self.pmu_test_btn:
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_pmu_test_ui(selected_test=self.current_pmu_test_key)
            self._show_pmu_submenu()

        elif sender == self.charger_test_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_charger_test_ui(selected_test=self.current_charger_test_key)
            self._show_charger_submenu()

        elif sender == self.module_test_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_module_test_ui(selected_test=self.current_module_test_key)
            self._show_module_test_submenu()

        elif sender == self.consumption_test_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_consumption_test_ui(selected_test=self.current_consumption_test_key)
            self._show_consumption_submenu()

        elif sender == self.vmin_hunter_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self._host._create_vmin_hunter_ui(selected_test=self.current_vmin_hunter_key)
            self._show_vmin_hunter_submenu()

        elif sender == self.orchestrator_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_orchestrator_ui()

        elif sender == self.pmu_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.collection_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_pmu_ui(selected_key=self.current_pmu_tool_key)
            self._show_pmu_tool_submenu()

        elif sender == self.collection_btn:
            self.pmu_submenu.hide()
            self.pa_submenu.hide()
            self.charger_submenu.hide()
            self.consumption_submenu.hide()
            self.module_test_submenu.hide()
            self.pmu_tool_submenu.hide()
            self.vmin_hunter_submenu.hide()
            self._host._create_collection_ui(selected_key=self.current_collection_key)
            self._show_collection_submenu()

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
        for submenu in (self.pa_submenu, self.pmu_submenu, self.charger_submenu,
                        self.consumption_submenu, self.module_test_submenu,
                        self.collection_submenu, self.pmu_tool_submenu,
                        self.vmin_hunter_submenu):
            if submenu and submenu.isVisible():
                submenu.hide()
