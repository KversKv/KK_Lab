# -*- coding: utf-8 -*-
"""serialCom_module 样式与共享常量叶子模块。

集中承载样式模块动态选择/装载（globals 导出全部样式常量）、SVG 资源目录、
MODE_* 模式常量、右键高亮调色板与 add_serial_port_item()，
供 frame / mixins / widgets / serial_log_panel / dialogs / controls /
independent_window 单向导入（本模块不依赖包内任何其它模块，无循环导入）。
"""

import importlib as _importlib
import os as _os
import re as _re
import sys as _sys

from PySide6.QtCore import Qt

from resource_path import get_resource_base


def _is_serialcom_frame_main() -> bool:
    """等价于原 frame 内 `__name__ == "__main__"`：入口脚本为 serialCom_module_frame。"""
    main_mod = _sys.modules.get("__main__")
    main_file = getattr(main_mod, "__file__", "") or ""
    return _os.path.splitext(_os.path.basename(main_file))[0].lower() == "serialcom_module_frame"


def _select_serialcom_style_module():
    override = _os.environ.get("KK_SERIALCOM_STYLE", "").strip().lower()
    if override in ("apple", "light", "standalone"):
        return "ui.modules.serialCom_module.serialCom_apple_gpt5p5_style"
    if override in ("dark", "main"):
        return "ui.modules.serialCom_module.serialCom_dark_style"

    exe_name = _os.path.splitext(_os.path.basename(getattr(_sys, "executable", "")))[0].lower()
    if _is_serialcom_frame_main() or (getattr(_sys, "frozen", False) and exe_name == "serialcom_module"):
        _os.environ["KK_SERIALCOM_STYLE"] = "light"
        return "ui.modules.serialCom_module.serialCom_apple_gpt5p5_style"
    return "ui.modules.serialCom_module.serialCom_dark_style"


_SERIALCOM_STYLE_EXPORTS = (
    "DARK_CARD_STYLE", "_CLR_BG_CARD", "_CLR_BG_LOG", "_CLR_BG_MAIN", "_CLR_BG_PANEL",
    "_CLR_BLUE",
    "_CLR_BORDER", "_CLR_BORDER_HOVER", "_CLR_BORDER_SOFT", "_CLR_CONNECT_BG", "_CLR_CONNECT_FG",
    "_CLR_CONNECT_TEXT", "_CLR_CURSOR", "_CLR_DISCONNECT_TEXT", "_CLR_ERROR",
    "_CLR_FILTER_BG", "_CLR_FILTER_BORDER", "_CLR_FILTER_TEXT", "_CLR_INPUT_BG",
    "_CLR_INPUT_TEXT", "_CLR_ROSE_ICON", "_CLR_RX", "_CLR_SCROLLBAR",
    "_CLR_SCROLLBAR_HV", "_CLR_SELECTION_BG", "_CLR_SELECTION_TEXT", "_CLR_SEND_BG",
    "_CLR_SEND_HOVER", "_CLR_SEND_PRESS", "_CLR_TEXT_ACCENT", "_CLR_TEXT_BODY",
    "_CLR_TEXT_BTN", "_CLR_TEXT_BTN_LOG", "_CLR_TEXT_INFO", "_CLR_TEXT_LABEL",
    "_CLR_TEXT_LINENO", "_CLR_TEXT_MUTED", "_CLR_TEXT_SUBTITLE", "_CLR_TEXT_TIME",
    "_CLR_TEXT_TITLE", "_CLR_TEXT_WHITE", "_CLR_TOGGLE_ON", "_CLR_TX", "_CLR_WARN_ICON", "_CLR_WARNING",
    "_DLG_STYLE", "_SERIAL_BTN_HEIGHT", "_SERIAL_BTN_ICON_SIZE", "_SERIAL_BTN_RADIUS",
    "_TERM_FONT", "_UI_FONT", "_serial_connect_style", "_serial_disconnect_style",
    "_serial_search_style", "body_splitter_style", "center_vsplitter_style",
    "center_widget_style",
    "checkbox_style", "compact_spinbox_style", "dialog_backdrop_style",
    "frameless_chrome_style", "script_editor_dialog_style", "dialog_cancel_button_style",
    "dialog_line_edit_style", "dialog_ok_button_style", "extra_log_error_color",
    "field_label_style", "filter_input_style", "filter_match_label_style",
    "history_combo_style", "inline_serial_label_style",
    "inline_serial_search_button_extra_style", "log_color_info_style",
    "log_color_info_text", "log_document_style", "log_edit_style", "log_frame_style",
    "log_panel_button_style", "log_title_style", "log_title_icon_color", "log_toolbar_button_style",
    "log_icon_button_style",
    "main_connect_button_style", "project_tabs_style", "quick_action_overlay_style",
    "quick_action_overlay_container_style",
    "quick_add_button_style", "quick_group_button_style",
    "quick_button_container_style", "quick_button_scroll_style", "quick_cmd_dialog_style",
    "quick_command_button_style", "quick_combo_style", "quick_group_combo_bg_style",
    "quick_commands_panel_style",
    "quick_preview_popup_shadow", "quick_preview_popup_style", "quick_toolbar_button_style",
    "bottom_tabs_style",
    "section_card_style", "section_card_shadow", "section_header_divider_style",
    "panel_divider_style",
    "script_stop_button_style", "script_add_step_button_style",
    "section_title_style", "send_button_style", "separator_style",
    "sidebar_toggle_button_style", "auto_scroll_button_style",
    "sidebar_toggle_icon_colors", "auto_scroll_icon_colors",
    "sidebar_wrapper_style", "small_label_style", "status_bar_style", "status_label_style",
    "thin_scrollbar_style", "toolbar_connect_button_style", "toolbar_style", "toggle_colors",
    "transparent_background_style", "transparent_scroll_area_style",
    "transparent_toolbar_button_style", "unit_label_style", "SERIAL_SCROLLBAR_STYLE",
    "SerialDarkComboBox", "SerialHistoryComboBox", "_CLR_HISTORY_COMBO_BG",
)

_SERIALCOM_STYLE_MODULE = _select_serialcom_style_module()
_serialcom_style = _importlib.import_module(_SERIALCOM_STYLE_MODULE)
globals().update({
    _name: getattr(_serialcom_style, _name)
    for _name in _SERIALCOM_STYLE_EXPORTS
})
del _serialcom_style


_SVG_COMMON_DIR = _os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Common"
)
_SVG_SERIAL_DIR = _os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Serial",
)
_SVG_LOGS_DIR = _os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Logs",
)
_SEARCH_ICON_PATH = _os.path.join(_SVG_COMMON_DIR, "search.svg")
_LINK_ICON_PATH = _os.path.join(_SVG_COMMON_DIR, "link.svg")
_UNLINK_ICON_PATH = _os.path.join(_SVG_COMMON_DIR, "unlink.svg")

MODE_SEARCH_SELECT = "search_and_select"
MODE_FULL = "full"
MODE_INLINE = "inline"

_PORT_FULL_TEXT_RE = _re.compile(r"^(COM\d+)\s+-\s+.+$", _re.IGNORECASE)


def add_serial_port_item(combo, full_text):
    """串口下拉项：DisplayRole 只存端口号（收起态显示），完整 '设备 - 描述' 存 UserRole/ToolTipRole 供下拉渲染与弹层取宽。"""
    text = (full_text or "").strip()
    m = _PORT_FULL_TEXT_RE.match(text)
    if m:
        idx = combo.count()
        combo.addItem(m.group(1).upper(), text)
        combo.setItemData(idx, text, Qt.ToolTipRole)
    else:
        combo.addItem(text)

# 右键高亮多色调色板：(背景色, 前景色)
_SC_HIGHLIGHT_PALETTE = [
    ("#FFD60A", "#1d1d1f"),  # yellow
    ("#FF9F0A", "#1d1d1f"),  # orange
    ("#FF375F", "#ffffff"),  # pink
    ("#BF5AF2", "#ffffff"),  # purple
    ("#0A84FF", "#ffffff"),  # blue
    ("#30D158", "#1d1d1f"),  # green
    ("#64D2FF", "#1d1d1f"),  # cyan
    ("#FF6482", "#ffffff"),  # rose
]
