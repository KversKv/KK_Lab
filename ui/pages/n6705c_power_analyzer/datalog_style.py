# -*- coding: utf-8 -*-
"""N6705C Datalog 页面的 QSS 样式集中管理。

所有对话框/菜单/按钮的可复用样式在此定义为常量，页面内通过
`_dlg_style(...)` / `_menu_style()` 等辅助函数拼装，避免散落各处的
复制粘贴样式串。仅样式文本搬运，不改任何视觉效果。
"""

# ---- 通用对话框 ----------------------------------------------------------

_DIALOG_BASE = """
    QDialog {
        background-color: #0a1628;
        color: #c8daf5;
    }
    QLabel {
        color: #8eb0e3;
        font-size: 12px;
    }
    QLineEdit {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        border-radius: 6px;
        color: #eaf2ff;
        padding: 6px 10px;
        font-size: 12px;
    }
    QLineEdit:focus {
        border-color: #3a6fd4;
    }
    QPushButton {
        background-color: #162d55;
        border: 1px solid #1e3460;
        border-radius: 6px;
        color: #c8daf5;
        padding: 6px 18px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #1e3460;
        border-color: #3a6fd4;
    }
"""

_DIALOG_COMBO = """
    QComboBox {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        border-radius: 6px;
        color: #eaf2ff;
        padding: 6px 10px;
        font-size: 12px;
    }
    QComboBox:focus {
        border-color: #3a6fd4;
    }
    QComboBox QAbstractItemView {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        color: #eaf2ff;
        selection-background-color: #1e3460;
    }
"""

_DIALOG_RADIO = """
    QRadioButton {
        color: #c8daf5;
        font-size: 12px;
        padding: 4px 0;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 14px;
        height: 14px;
    }
    QRadioButton:disabled {
        color: #3a5070;
    }
    QPushButton:disabled {
        background-color: #0c1a35;
        color: #3a5070;
        border-color: #142542;
    }
"""


def dlg_style(combo=False, radio=False):
    """返回通用对话框 QSS；按需追加下拉框 / 单选框样式段。"""
    style = _DIALOG_BASE
    if combo:
        style += _DIALOG_COMBO
    if radio:
        style += _DIALOG_RADIO
    return style


# ---- 通用菜单 ------------------------------------------------------------

_MENU_BASE = """
    QMenu {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        border-radius: 6px;
        color: #c8daf5;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 20px;
        border-radius: 4px;
    }
    QMenu::item:selected {
        background-color: #1e3460;
    }
"""

_MENU_SMALL = """
    QMenu {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        color: #c8daf5;
        font-size: 11px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 18px 6px 24px;
        border-radius: 3px;
    }
    QMenu::item:selected {
        background-color: #1e3460;
        color: #eaf2ff;
    }
    QMenu::item:disabled {
        color: #3a5070;
    }
    QMenu::separator {
        height: 1px;
        background-color: #1e3460;
        margin: 4px 6px;
    }
"""


def menu_style(small=False):
    """返回通用右键菜单 QSS；small=True 用于字号 11px 的紧凑菜单。"""
    return _MENU_SMALL if small else _MENU_BASE


# ---- 主按钮（对话框内强调按钮，蓝底） -------------------------------------

PRIMARY_BTN_STYLE = """
    QPushButton {
        background-color: #1a4b8c;
        border: 1px solid #3a6fd4;
        border-radius: 6px;
        color: #eaf2ff;
        padding: 6px 18px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #245bb5;
    }
"""

EXPORT_OK_BTN_STYLE = """
    QPushButton {
        background-color: #1a3a6e;
        border: 1px solid #3a6fd4;
        border-radius: 6px;
        color: #eaf2ff;
        padding: 6px 18px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #245b8e;
        border-color: #5a8fee;
    }
"""

# ---- 方形工具按钮（搜索 / 更多菜单，40x40） --------------------------------

_SQUARE_ICON_BTN_BASE = """
    {selector} {{
        background-color: #13254b;
        border: 1px solid #22376A;
        border-radius: 8px;
        color: #dce7ff;
        font-weight: 600;
        min-height: 0px;
        max-height: 40px;
        min-width: 0px;
        max-width: 40px;
        padding: 0px;
    }}
    {selector}:hover {{
        background-color: #1C2D55;
        border: 1px solid #3A5A9F;
    }}
    {selector}:pressed {{
        background-color: #102040;
    }}
"""

SEARCH_BTN_STYLE = _SQUARE_ICON_BTN_BASE.format(selector="QPushButton")

MORE_BTN_STYLE = (
    _SQUARE_ICON_BTN_BASE.format(selector="QToolButton").replace(
        "color: #dce7ff;", "color: #8eb0e3; font-size: 18px; font-weight: bold;"
    )
    + "\n    QToolButton::menu-indicator { image: none; }\n"
)

INSTR_MENU_STYLE = """
    QMenu {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        color: #c8daf5;
        font-size: 11px;
        padding: 4px;
    }
    QMenu::item {
        padding: 6px 16px;
    }
    QMenu::item:selected {
        background-color: #1e3460;
    }
"""

# ---- 通道配置面板 ----------------------------------------------------------

CH_CFG_TOGGLE_BTN_EXPANDED = """
    QPushButton {
        background-color: #0a1930; color: #b8d0f0;
        border: 1px solid #132849;
        border-top-left-radius: 8px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
        padding: 0px 14px; font-size: 11px; font-weight: 700;
        text-align: left;
    }
    QPushButton:hover { background-color: #0e1f3d; color: #d0e4ff; }
"""

CH_CFG_TOGGLE_BTN_COLLAPSED = """
    QPushButton {
        background-color: #0a1930; color: #8ea6cf;
        border: 1px solid #132849; border-radius: 8px;
        padding: 0px 14px; font-size: 11px; font-weight: 700; text-align: left;
    }
    QPushButton:hover { background-color: #0e1f3d; color: #b8d0f0; }
"""

CH_CFG_TABBAR_STYLE = """
    QTabBar {
        background: transparent;
        border: none;
    }
    QTabBar::tab {
        background-color: #0b1630;
        color: #4a6a96;
        border: 1px solid #1a2b52;
        border-bottom: none;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        padding: 4px 14px;
        margin-right: 1px;
        margin-bottom: 0px;
        font-size: 11px;
        font-weight: 600;
    }
    QTabBar::tab:selected {
        background-color: #071127;
        color: #dce7ff;
        border: 1px solid #1a2b52;
        border-bottom: none;
    }
    QTabBar::tab:hover:!selected {
        background-color: #0e1d40;
        color: #8eb0e3;
    }
    QTabBar::tab:!selected {
        margin-top: 2px;
    }
    QTabBar::close-button {
        image: none;
        border: none;
        background: transparent;
    }
"""

CH_CFG_CARD_STYLE = """
    #cardFrame {
        background-color: #0a1930;
        border: 1px solid #132849;
        border-top: none;
        border-top-left-radius: 0px;
        border-top-right-radius: 0px;
        border-bottom-left-radius: 12px;
        border-bottom-right-radius: 12px;
    }
"""

CH_CFG_TAB_CLOSE_BTN_STYLE = (
    "QPushButton { background: transparent; color: #4a6a96; font-size: 11px; "
    "border: none; border-radius: 3px; padding: 0; margin: 0; min-height: 0; }"
    "QPushButton:hover { background: #2a1525; color: #ff6b6b; }"
)

# 通道 Scale/Offset 输入框
SCALE_OFFSET_EDIT_STYLE = (
    "QLineEdit { background: #0c1a35; color: #8eb0e3; font-size: 10px; "
    "border: 1px solid #1e3460; border-radius: 2px; }"
    "QLineEdit:focus { border-color: #3a6aad; }"
)

SLOT_FRAME_STYLE = """
    QFrame {
        background-color: #071127;
        border: none;
    }
"""

OUT_FRAME_STYLE = (
    "QFrame { background-color: #0a1430; border: 1px solid #152040; border-radius: 4px; }"
)

SEP_LABEL_STYLE = "color: #3a5070; font-size: 10px; border: none;"

SLOT_TITLE_STYLE = "color: #667ba0; font-size: 10px; border: none; padding-bottom: 2px;"

CONTAINER_NO_BORDER_STYLE = "border: none;"

DUMMY_TOGGLE_STYLE = (
    "background-color: #0a1020; color: #2a3a55; "
    "font-size: 10px; font-weight: 700; "
    "border: 1px solid #121e38; border-radius: 2px;"
)

# ---- 通道开关按钮（ToggleLabel 激活/未激活） --------------------------------

CH_TOGGLE_INACTIVE_STYLE = (
    "background-color: #152040; color: #8eb0e3; "
    "font-size: 10px; font-weight: 700; "
    "border: 1px solid #1e3460; border-radius: 2px;"
)


def ch_toggle_style(color, active):
    """通道 I/V/P 开关按钮样式：active 时用通道色填充。"""
    if active:
        return (
            f"background-color: {color}; color: #ffffff; "
            f"font-size: 10px; font-weight: 800; "
            f"border: 1px solid {color}; border-radius: 2px;"
        )
    return CH_TOGGLE_INACTIVE_STYLE


def out_title_style(ch_color):
    """OUTPUT 通道标题样式。"""
    return (
        f"color: {ch_color}; font-size: 10px; font-weight: 700; "
        f"border: none; padding: 1px 0;"
    )


# ---- 测量表格 ----------------------------------------------------------------

MEAS_TABLE_STYLE = """
    QTableWidget#measTable {
        background-color: transparent;
        border: none;
        gridline-color: #152040;
        color: #c8daf5;
        font-size: 12px;
        font-family: 'Consolas', 'Courier New', monospace;
    }
    QTableWidget#measTable::item {
        padding: 2px 8px;
    }
    QTableWidget#measTable::item:selected {
        background-color: transparent;
        color: inherit;
    }
    QTableWidget#measTable QHeaderView::section {
        background-color: #0b1528;
        color: #5a7fad;
        font-weight: 600;
        font-size: 11px;
        font-family: 'Segoe UI', sans-serif;
        padding: 3px 8px;
        border: none;
        border-bottom: 2px solid #1a2b52;
        border-right: 1px solid #12203a;
    }
    QTableWidget#measTable QHeaderView::section:last {
        border-right: none;
    }
    QTableWidget#measTable QTableCornerButton::section {
        background-color: #0b1528;
        border: none;
        border-bottom: 1px solid #1e3460;
    }
    QTableWidget#measTable QScrollBar {
        width: 0px;
        height: 0px;
    }
"""

# ---- 进度遮罩 ------------------------------------------------------------------

PROGRESS_BAR_STYLE = """
    QProgressBar {
        background-color: #152749;
        border: 1px solid #27406f;
        border-radius: 9px;
        text-align: center;
        color: #b7c8ea;
        font-size: 11px;
    }
    QProgressBar::chunk {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #4f46e5, stop:1 #7c3aed);
        border-radius: 8px;
    }
"""

PROGRESS_OVERLAY_STYLE = (
    "QFrame { background-color: rgba(2, 8, 23, 200); border: none; border-radius: 12px; }"
)

CH_CFG_OVERLAY_STYLE = (
    "QFrame { background-color: rgba(2, 8, 23, 180); border: none; border-radius: 12px; }"
)

PROGRESS_STAGE_STYLE = "color: #c8daf5; font-size: 13px; font-weight: 600; background: transparent;"

PROGRESS_TIME_STYLE = "color: #5c7a9e; font-size: 11px; background: transparent;"

CH_LOCK_LABEL_STYLE = "color: #5c7a9e; font-size: 12px; font-weight: 600; background: transparent;"

# ---- 设备槽位 / 卡片 ------------------------------------------------------------

SLOT_ASSIGNED_STYLE = """
    QFrame#cardFrame {
        background-color: #0c2254;
        border: 1px solid #3a6fd4;
        border-radius: 12px;
    }
"""

SLOT_LETTER_CONNECTED_STYLE = "font-size: 18px; font-weight: bold; color: #4ae68a; border: none;"
SLOT_LETTER_DEFAULT_STYLE = "font-size: 18px; font-weight: bold; color: #3a6fd4; border: none;"
SLOT_NAME_CONNECTED_STYLE = "font-size: 10px; color: #8eb0e3; border: none;"
SLOT_NAME_DEFAULT_STYLE = "font-size: 11px; color: #667ba0; border: none;"

CARD_SERIAL_STYLE = "font-size: 9px; color: #667ba0; border: none;"
CARD_MODEL_STYLE = "font-size: 13px; font-weight: bold; color: #eaf2ff; border: none;"
CARD_IP_STYLE = "font-size: 11px; color: #8eb0e3; border: none;"
CARD_THUMB_STYLE = "border: none; border-radius: 4px;"

# ---- 采样周期 / 监控时长 -------------------------------------------------------

TIME_EDIT_STYLE = (
    "QLineEdit { padding: 2px 4px; border-radius: 3px; "
    "background-color: #0c1a35; border: 1px solid #1e3460; "
    "color: #eaf2ff; font-size: 11px; }"
    "QLineEdit:focus { border-color: #3a6fd4; }"
)

MIN_PERIOD_CB_STYLE = "font-size: 10px; color: #8eb0e3;"

SAMPLE_PERIOD_READONLY_STYLE = "QLineEdit { background: #1a2b52; color: #667ba0; }"

TIME_UNIT_LABEL_STYLE = "color: #8eb0e3; font-size: 10px; padding: 0px; border: none;"

TIME_COLON_STYLE = "color: #8eb0e3; font-size: 11px;"

# ---- 对话框杂项 ------------------------------------------------------------------

DIALOG_TITLE_STYLE = "font-size: 14px; font-weight: bold; color: #eaf2ff;"

HINT_TEXT_STYLE = "color: #667ba0; font-size: 10px;"

HINT_DISABLED_STYLE = "color: #3a5070; font-size: 10px;"

HINT_ERROR_STYLE = "color: #8a3a3a; font-size: 10px;"

MARKER_INFO_STYLE = "color: #667ba0; font-size: 10px;"

MARKER_INFO_DISABLED_STYLE = "color: #3a5070; font-size: 10px;"

SAVE_DEFAULT_CB_STYLE = """
    QCheckBox {
        color: #8eb0e3;
        font-size: 12px;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 15px;
        height: 15px;
        border: 1px solid #1e3460;
        border-radius: 3px;
        background-color: #0c1a35;
    }
    QCheckBox::indicator:checked {
        background-color: #1a4b8c;
        border-color: #3a6fd4;
    }
"""

# 时间偏移对话框 Align From Markers 按钮
ALIGN_BTN_ENABLED_STYLE = """
    QPushButton {
        background-color: #1a3a2e;
        border: 1px solid #2a8c5a;
        border-radius: 6px;
        color: #7fffcf;
        padding: 6px 18px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #245b3e;
        border-color: #3abf7a;
    }
"""

ALIGN_BTN_DISABLED_STYLE = """
    QPushButton {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        border-radius: 6px;
        color: #3a5070;
        padding: 6px 18px;
        font-size: 12px;
    }
"""

# ---- 透明背景通用 ------------------------------------------------------------------

TRANSPARENT_BG_STYLE = "background: transparent;"

TRANSPARENT_WIDGET_STYLE = "QWidget { background: transparent; }"

ICON_LBL_STYLE = "border: none; background: transparent;"

SEPARATOR_LINE_STYLE = "background-color: #1b2c4f;"

CH_CFG_INNER_BG_STYLE = "background: #071127;"

CH_CFG_TABBAR_HOLDER_STYLE = """
    #chConfigTabbarHolder {
        background-color: #0a1930;
        border-top: 1px solid #132849;
        border-right: 1px solid #132849;
        border-bottom: 1px solid #132849;
        border-left: none;
        border-top-right-radius: 8px;
    }
"""

CH_CFG_OUTER_STYLE = "#chConfigOuter { background: transparent; border: none; }"

CH_CFG_HEADER_ROW_STYLE = "#chConfigHeaderRow { background: transparent; border: none; }"

CHART_TITLE_STYLE = "font-size: 16px; font-weight: 700; color: #f4f7ff;"
