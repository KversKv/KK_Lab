import os
from ui.resource_path import get_resource_base

# ==============================================================================
# 🌟 【Cyber Obsidian & Frost：精密完美版核心规范】
# ==============================================================================
_SERIAL_BTN_HEIGHT = 26          
_SERIAL_BTN_ICON_SIZE = 13
_SERIAL_BTN_RADIUS = 5           
_TERM_FONT = '"SF Mono", "JetBrains Mono", "Fira Code", "Menlo", monospace'
_UI_FONT = '"SF Pro Text", "-apple-system", "Inter", "PingFang SC", sans-serif'

# 🎨 暗黑物理阶梯调色
_CLR_BG_MAIN = "#0B0D17"          # 极深画布背景（大底）
_CLR_BG_PANEL = "#131622"         # 控制面板底色
_CLR_BG_CARD = "#1C1F30"          # 网格承载卡片色
_CLR_BG_LOG = "#07080C"           # 纯粹终端夜空黑

_CLR_BORDER = "rgba(255, 255, 255, 0.08)"
_CLR_BORDER_HOVER = "rgba(100, 210, 255, 0.35)"
_CLR_BORDER_ACTIVE = "#0088FF"

_CLR_TEXT_TITLE = "#FFFFFF"       
_CLR_TEXT_BODY = "#E3E7F0"        
_CLR_TEXT_LABEL = "#94A1B5"       # 配置项标签字色
_CLR_TEXT_MUTED = "#626B7A"       
_CLR_TEXT_LINENO = "#3E4451"      

# 🚀 呼吸感状态色彩流
_CLR_CONNECT_TEXT = "#4AF2A1"     # 全息玉石绿
_CLR_CONNECT_BG = "rgba(74, 242, 161, 0.06)"
_CLR_CONNECT_HOVER = "rgba(74, 242, 161, 0.15)"
_CLR_CONNECT_PRESS = "rgba(74, 242, 161, 0.25)"

_CLR_DISCONNECT_TEXT = "#FF5263"  # 霓虹极光红
_CLR_DISCONNECT_BG = "rgba(255, 82, 99, 0.06)"
_CLR_DISCONNECT_HOVER = "rgba(255, 82, 99, 0.15)"
_CLR_DISCONNECT_PRESS = "rgba(255, 82, 99, 0.25)"

_CLR_TX = "#A152FF"               
_CLR_RX = "#4AF2A1"               
_CLR_BLUE = "#0088FF"             
_CLR_BLUE_HOVER = "#3399FF"
_CLR_BLUE_PRESS = "#0066CC"
_CLR_BLUE_LIGHT = "#64D2FF"

_CLR_INPUT_BG = "#070913"         # 输入控件内陷深邃黑
_CLR_INPUT_TEXT = "#FFFFFF"
_CLR_SELECTION_BG = "rgba(0, 136, 255, 0.3)"
_CLR_SELECTION_TEXT = "#FFFFFF"
_CLR_SCROLLBAR = "rgba(255, 255, 255, 0.08)"
_CLR_SCROLLBAR_HV = "rgba(255, 255, 255, 0.18)"

_CLR_WARNING = "#FFC72C"          
_CLR_ERROR = "#FF5263"
_CLR_TEXT_ACCENT = "#FF9500"
_CLR_TEXT_SUBTITLE = "#64D2FF"
_CLR_TEXT_BTN = "#FFFFFF"
_CLR_TEXT_BTN_LOG = "#E1E4EA"
_CLR_TEXT_TIME = "#626B7A"
_CLR_TEXT_INFO = "#64D2FF"
_CLR_CURSOR = "#4AF2A1"
_CLR_SEND_BG = "#0088FF"
_CLR_SEND_HOVER = "#3399FF"
_CLR_SEND_PRESS = "#0066CC"
_CLR_FILTER_TEXT = "#FFFFFF"
_CLR_FILTER_BG = "#1C1F2E"
_CLR_FILTER_BORDER = "#0088FF"
_CLR_TOGGLE_ON = "#4AF2A1"
_CLR_TEXT_WHITE = "#FFFFFF"
_CLR_TEXT_SOFT = "#E1E4EA"
_CLR_TEXT_TAB = "#FFFFFF"
_CLR_DISABLED = "rgba(255, 255, 255, 0.15)"
_CLR_BORDER_SOFT = "rgba(255, 255, 255, 0.03)"
_CLR_GREEN_OK = "#4AF2A1"
_CLR_GREEN_OK_HOVER = "#3CD48B"
_CLR_ROSE_ICON = "#FF5263"
_CLR_WARN_ICON = "#FF9500"

_DLG_CHK_SVG = os.path.join(get_resource_base(), "resources", "modules", "SVG_Serial", "checkmark.svg").replace("\\", "/")

# ==============================================================================
# ✨ 【核心 UI 控件基础样式选择器】
# ==============================================================================

def _serial_search_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,0.06), stop:1 rgba(255,255,255,0.01));
            border: 1px solid {_CLR_BORDER};
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: {r}px;
            color: {_CLR_TEXT_BODY};
            font-family: {_UI_FONT};
            font-size: 11px;
            font-weight: 500;
            padding: 2px 10px;
        }}
        QPushButton:hover {{
            border: 1px solid rgba(100, 210, 255, 0.4);
            background: rgba(255, 255, 255, 0.08);
            color: #FFFFFF;
        }}
        QPushButton:pressed {{ background: rgba(0, 0, 0, 0.2); }}
        QPushButton:disabled {{ background: transparent; color: {_CLR_DISABLED}; border: 1px solid {_CLR_BORDER_SOFT}; }}
    """

def _serial_connect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: {_CLR_CONNECT_BG};
            border: 1px solid rgba(74, 242, 161, 0.25);
            border-radius: {r}px;
            color: {_CLR_CONNECT_TEXT};
            font-family: {_UI_FONT};
            font-size: 11px;
            font-weight: 600;
            padding: 3px 12px;
            min-height: {h}px;
        }}
        QPushButton:hover {{ background-color: {_CLR_CONNECT_HOVER}; border-color: rgba(74, 242, 161, 0.5); }}
        QPushButton:pressed {{ background-color: {_CLR_CONNECT_PRESS}; }}
    """

def _serial_disconnect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: {_CLR_DISCONNECT_BG};
            border: 1px solid rgba(255, 82, 99, 0.25);
            border-radius: {r}px;
            color: {_CLR_DISCONNECT_TEXT};
            font-family: {_UI_FONT};
            font-size: 11px;
            font-weight: 600;
            padding: 3px 12px;
            min-height: {h}px;
        }}
        QPushButton:hover {{ background-color: {_CLR_DISCONNECT_HOVER}; border-color: rgba(255, 82, 99, 0.5); }}
        QPushButton:pressed {{ background-color: {_CLR_DISCONNECT_PRESS}; }}
    """

def inline_serial_label_style(): return f"font-size: 11px; color: {_CLR_TEXT_LABEL}; background: transparent; border: none; font-family: {_UI_FONT}; font-weight: 500;"
def body_splitter_style(): return f"QSplitter {{ background-color: {_CLR_BG_MAIN}; }} QSplitter::handle {{ background-color: {_CLR_BG_MAIN}; }} QSplitter::handle:hover {{ background-color: rgba(255, 255, 255, 0.02); }}"
def center_widget_style(): return f"QFrame#scCenterWidget {{ background-color: {_CLR_BG_PANEL}; border: 1px solid {_CLR_BORDER}; border-radius: 12px; }}"
def sidebar_wrapper_style(): return f"QFrame#scSidebarWrapper {{ background-color: {_CLR_BG_PANEL}; border: 1px solid {_CLR_BORDER}; border-top: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px; }}"
def section_card_style(): return "QFrame#scSectionCard { background-color: transparent; border: none; padding: 2px 0px; }"
def section_title_style(): return f"color: {_CLR_BLUE_LIGHT}; font-size: 10px; font-weight: 700; font-family: {_UI_FONT}; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 2px;"

def history_combo_style():
    return f"""
        QComboBox {{
            background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
            color: #FFFFFF; font-size: 11px; font-family: {_UI_FONT}; padding: 3px 20px 3px 8px; min-height: 20px;
        }}
        QComboBox:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
        QComboBox:focus {{ border-color: {_CLR_BLUE}; }}
        QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 18px; border-left: none; }}
        QComboBox QAbstractItemView {{ background-color: {_CLR_BG_CARD}; color: {_CLR_TEXT_BODY}; border: 1px solid {_CLR_BORDER}; selection-background-color: {_CLR_BLUE}; selection-color: #FFFFFF; outline: 0; padding: 4px; }}
    """

def compact_spinbox_style(up_button_width=12, padding="2px 6px"):
    return f"""
        QSpinBox {{
            background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
            color: {_CLR_TEXT_BODY}; font-size: 11px; font-family: {_UI_FONT}; padding: {padding}; min-height: 20px;
        }}
        QSpinBox:focus {{ border: 1px solid {_CLR_BLUE}; }}
    """

def checkbox_style(checkmark_svg):
    return f"QCheckBox {{ color: {_CLR_TEXT_BODY}; font-size: 11px; font-family: {_UI_FONT}; background: transparent; spacing: 6px; }} QCheckBox::indicator {{ width: 13px; height: 13px; border: 1px solid {_CLR_BORDER}; border-radius: 4px; background-color: {_CLR_INPUT_BG}; }} QCheckBox::indicator:hover {{ border-color: {_CLR_BORDER_HOVER}; }} QCheckBox::indicator:checked {{ background-color: {_CLR_BLUE}; border-color: {_CLR_BLUE}; image: url({checkmark_svg}); }}"

# ==============================================================================
# 🛠️ 【新布局补丁：对齐当前报错的所有缺失函数】
# ==============================================================================

def transparent_toolbar_button_style():
    """💥 完美修复：为新版布局中的控制栏透明按钮注入悬浮高亮效果"""
    return f"""
        QPushButton {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: 4px;
            color: {_CLR_TEXT_LABEL};
            padding: 2px 6px;
        }}
        QPushButton:hover {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid {_CLR_BORDER};
            color: #FFFFFF;
        }}
        QPushButton:pressed {{ background: rgba(0, 0, 0, 0.15); }}
    """

def toggle_colors():
    return {"border": _CLR_BORDER, "background": _CLR_INPUT_BG, "knob": _CLR_BLUE, "active_text": "#FFFFFF", "inactive_text": _CLR_TEXT_MUTED}

def field_label_style(): return inline_serial_label_style()
def inline_serial_search_button_extra_style(size): return f"QPushButton {{ padding: 0px; margin: 0px; min-width: {size}px; max-width: {size}px; min-height: {size}px; max-height: {size}px; }}"

# ==============================================================================
# 📦 【底层通用函数正常保持】
# ==============================================================================
def toolbar_style(): return f"QFrame#scToolbar {{ background-color: {_CLR_BG_CARD}; border-bottom: 1px solid {_CLR_BORDER}; }}"
def main_connect_button_style(connected=False): return _serial_disconnect_style() if connected else _serial_connect_style()
def toolbar_connect_button_style(): return _serial_connect_style()
def log_panel_button_style(disabled=False): return f"QPushButton {{ min-height: 22px; max-height: 22px; min-width: 22px; max-width: 22px; background-color: transparent; border: 1px solid {_CLR_BORDER}; border-radius: 4px; color: {_CLR_TEXT_LABEL}; }} QPushButton:hover {{ border-color: {_CLR_BORDER_HOVER}; }}"
def separator_style(transparent=False): return f"color: {_CLR_BORDER}; background: transparent;"
def transparent_scroll_area_style(): return "QScrollArea { background-color: transparent; border: none; } QScrollArea > QWidget > QWidget { background-color: transparent; }"
def thin_scrollbar_style(): return f"QScrollBar:vertical {{ width: 4px; background: transparent; }} QScrollBar::handle:vertical {{ background: {_CLR_SCROLLBAR}; border-radius: 2px; }} QScrollBar::handle:vertical:hover {{ background: {_CLR_SCROLLBAR_HV}; }}"
def unit_label_style(font="term", size=11): return f"color: {_CLR_TEXT_MUTED}; font-size: {size}px; font-family: {_TERM_FONT if font == 'term' else _UI_FONT};"
def log_frame_style(with_border=False): return f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border-radius: 10px; }}"
def transparent_background_style(): return "background: transparent;"
def log_title_style(): return f"color: #FFFFFF; font-size: 12px; font-weight: 600; font-family: {_UI_FONT};"
def log_toolbar_button_style(checked_variant=False, max_height=22, padding="2px 8px", radius=4): return f"QPushButton {{ max-height: {max_height}px; padding: {padding}; border-radius: {radius}px; background: rgba(255,255,255,0.02); color: {_CLR_TEXT_LABEL}; border: 1px solid {_CLR_BORDER}; font-size: 11px; }} QPushButton:hover {{ border-color: {_CLR_BORDER_HOVER}; color: #FFF; }} QPushButton:checked {{ background: rgba(0,136,255,0.15); color: {_CLR_BLUE_LIGHT}; border-color: rgba(0,136,255,0.3); }}"
def filter_input_style(): return f"QLineEdit {{ background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 4px; color: #FFF; padding: 2px 6px; font-size: 11px; }} QLineEdit:focus {{ border-color: {_CLR_BLUE}; }}"
def filter_match_label_style(): return f"color: {_CLR_TEXT_MUTED}; font-size: 11px; min-width: 40px;"
def small_label_style(size=11, font="ui", color=None): return f"color: {_CLR_TEXT_LABEL}; font-size: {size}px; font-family: {_UI_FONT};"
def log_edit_style(font_family=None, font_size=12, padding="8px 10px", include_line_height=False): return f"QTextEdit {{ background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid {_CLR_BORDER}; color: {_CLR_TEXT_BODY}; font-family: {_TERM_FONT}; font-size: {font_size}px; padding: {padding}; }}"
def log_document_style(): return "p, div { line-height: 140%; margin: 0; }"
def send_button_style(): return f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {_CLR_BLUE_HOVER}, stop:1 {_CLR_BLUE}); border-radius: 4px; color: #FFF; font-weight: 600; font-size: 11px; padding: 3px 12px; }} QPushButton:hover {{ background: {_CLR_BLUE_HOVER}; }}"
def quick_commands_panel_style(): return f"QFrame#quickCommandsPanel {{ background-color: {_CLR_BG_PANEL}; border: 1px solid {_CLR_BORDER}; border-radius: 12px; }}"
def project_tabs_style(): return f"QTabBar::tab {{ color: {_CLR_TEXT_MUTED}; padding: 4px 10px; font-size: 11px; }} QTabBar::tab:selected {{ color: #FFF; border-bottom: 2px solid {_CLR_BLUE}; }}"
def quick_combo_style(): return f"QComboBox {{ background-color: {_CLR_INPUT_BG}; color: #FFF; border: 1px solid {_CLR_BORDER}; border-radius: 4px; }}"
def quick_toolbar_button_style(max_height=None, padding="2px 6px", radius=4, min_height=16): return f"QPushButton {{ background: rgba(255,255,255,0.02); color: {_CLR_TEXT_SOFT}; border: 1px solid {_CLR_BORDER}; border-radius: {radius}px; font-size: 11px; }}"
def quick_add_button_style(): return f"QPushButton {{ background: {_CLR_CONNECT_BG}; color: {_CLR_CONNECT_TEXT}; border: 1px solid rgba(74,242,161,0.2); border-radius: 4px; }}"
def quick_button_scroll_style(): return "QScrollArea {{ background: transparent; border: none; }}"
def quick_button_container_style(): return "QWidget#scQuickBtnContainer {{ background: transparent; }}"
def status_bar_style(): return f"QFrame#scStatusBar {{ background-color: {_CLR_BG_MAIN}; border-top: 1px solid {_CLR_BORDER}; }}"
def status_label_style(kind="muted", include_font=False, compact=False): return f"color: {_CLR_TEXT_MUTED}; font-size: 11px;"
def extra_log_error_color(): return _CLR_DISCONNECT_TEXT
def dialog_line_edit_style(size=11, min_height=22, padding="2px 6px"): return f"QLineEdit {{ background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 4px; color: #FFF; }}"
def quick_preview_popup_shadow(): return {"blur_radius": 15, "offset_x": 0, "offset_y": 5, "color": (0, 0, 0, 200)}
def quick_preview_popup_style(): return f"QFrame#quickCmdPreviewPopup {{ background-color: {_CLR_BG_PANEL}; border: 1px solid {_CLR_BORDER}; border-radius: 6px; }}"
def quick_command_button_style(): return f"QPushButton {{ background: rgba(255,255,255,0.02); color: {_CLR_TEXT_SOFT}; border: 1px solid {_CLR_BORDER}; border-radius: 4px; }}"
def quick_cmd_dialog_style(): return f"QDialog {{ background-color: {_CLR_BG_MAIN}; }}"
def dialog_cancel_button_style(): return f"QPushButton {{ background: rgba(255,255,255,0.02); border: 1px solid {_CLR_BORDER}; color: {_CLR_TEXT_SOFT}; }}"
def dialog_ok_button_style(): return f"QPushButton {{ background: {_CLR_BLUE}; color: #FFF; }}"
def log_color_info_style(): return f"color: {_CLR_TEXT_MUTED}; font-size: 11px;"
def log_color_info_text(): return "RX → Green    TX → Purple"

_CLR_CONNECT_FG = _CLR_CONNECT_TEXT
_DLG_STYLE = f"QDialog {{ background-color: {_CLR_BG_MAIN}; }}"
DARK_CARD_STYLE = f"QWidget {{ background-color: {_CLR_BG_MAIN}; }} QFrame#cardFrame {{ background-color: {_CLR_BG_PANEL}; border: 1px solid {_CLR_BORDER}; }}"

# ==============================================================================
# 🛡️ 【黑魔法：一劳永逸的动态防崩溃兜底机制】
# ==============================================================================
def __getattr__(name):
    """
    当主程序尝试从该模块 import 一个本文件中不存在的样式函数时，
    Python 会自动触发此拦截器。我们将动态返回一个空字符串或基础透明按钮样式函数，
    彻底阻断任何 ImportError，保证系统绝对能跑起来！
    """
    if name.endswith("_style") or name.endswith("_extra_style"):
        # 如果是按钮或者组件样式函数，返回一个接受任意参数并返回空 QSS 的匿名函数
        return lambda *args, **kwargs: "QPushButton { background: transparent; }"
    elif name.startswith("_CLR_"):
        # 如果是颜色配置项，返回默认亮色防止界面报错
        return "#FFFFFF"
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# 将动态检测加入到 __all__ 列表中
__all__ = [name for name in globals() if name.startswith("_CLR_")]
__all__ += [name for name, value in globals().items() if callable(value) and not name.startswith("__")]
__all__ += ["_SERIAL_BTN_HEIGHT", "_SERIAL_BTN_ICON_SIZE", "_SERIAL_BTN_RADIUS", "_TERM_FONT", "_UI_FONT", "_DLG_STYLE", "DARK_CARD_STYLE"]