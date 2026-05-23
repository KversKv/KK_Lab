import os
from ui.resource_path import get_resource_base

# Apple 风格核心几何与字体规范
_SERIAL_BTN_HEIGHT = 28          # 略微增加高度以提升呼吸感
_SERIAL_BTN_ICON_SIZE = 14
_SERIAL_BTN_RADIUS = 5           # macOS 标准控件圆角
_TERM_FONT = '"SF Mono", "JetBrains Mono", "Fira Code", Consolas, monospace'
_UI_FONT = '"SF Pro Text", "-apple-system", "BlinkMacSystemFont", "PingFang SC", "Helvetica Neue", sans-serif'

# Apple macOS 暗色模式官方色阶与微质感调色板
_CLR_BG_MAIN = "#1E1E1E"          # macOS 系统默认全局暗色背景
_CLR_BG_PANEL = "#252525"         # 次级控制面板背景
_CLR_BG_CARD = "#2D2D2D"          # 悬浮卡片/主容器背景
_CLR_BG_LOG = "#151515"           # 纯黑极客控制台终端背景
_CLR_BORDER = "rgba(255, 255, 255, 0.08)"       # 极其细腻的半透明微边框
_CLR_BORDER_HOVER = "rgba(255, 255, 255, 0.18)" # 悬停时微微点亮
_CLR_TEXT_TITLE = "#FFFFFF"       # 原生纯白
_CLR_TEXT_ACCENT = "#FF9500"      # Apple Orange 警告/高亮
_CLR_TEXT_SUBTITLE = "#AEAEB2"    # macOS 次要文本三级色
_CLR_TEXT_LABEL = "#E5E5EA"       # 核心标签二级色
_CLR_TEXT_BTN = "#FFFFFF"
_CLR_TEXT_BTN_LOG = "#E5E5EA"
_CLR_TEXT_BODY = "#F2F2F7"        # 主体文本一级色
_CLR_TEXT_TIME = "#8E8E93"        # macOS 时间轴灰色
_CLR_TEXT_LINENO = "#636366"      # 行号暗灰
_CLR_TEXT_INFO = "#64D2FF"        # Apple Light Blue
_CLR_INPUT_BG = "#1A1A1A"         # 输入框深内嵌色
_CLR_INPUT_TEXT = "#FFFFFF"
_CLR_CURSOR = "#007AFF"           # 经典 Apple Blue 光标
_CLR_SELECTION_BG = "rgba(0, 122, 255, 0.3)"    # 半透明高亮选中蓝
_CLR_SELECTION_TEXT = "#FFFFFF"
_CLR_SCROLLBAR = "rgba(255, 255, 255, 0.12)"    # 拟物化果冻滚动条
_CLR_SCROLLBAR_HV = "rgba(255, 255, 255, 0.22)"
_CLR_CONNECT_FG = "#30D158"       # Apple System Green (Dark Mode)
_CLR_CONNECT_BG = "rgba(48, 209, 88, 0.15)"    # 优雅的绿底半透明
_CLR_SEND_BG = "#007AFF"          # 主按钮全面采用 Apple Tint Blue
_CLR_SEND_HOVER = "#3498DB"
_CLR_SEND_PRESS = "#1A5276"
_CLR_WARNING = "#FFD60A"          # Apple System Yellow
_CLR_ERROR = "#FF453A"            # Apple System Red
_CLR_RX = "#30D158"               # 数据接收（绿）
_CLR_TX = "#BF5AF2"               # 数据发送（Apple System Purple 优雅高贵）
_CLR_FILTER_TEXT = "#FFFFFF"
_CLR_FILTER_BG = "#3A3A3C"          # 搜索过滤器独立灰色
_CLR_FILTER_BORDER = "#007AFF"
_CLR_TOGGLE_ON = "#30D158"

_CLR_TEXT_MUTED = "#8E8E93"
_CLR_TEXT_WHITE = "#FFFFFF"
_CLR_TEXT_SOFT = "#E5E5EA"
_CLR_TEXT_TAB = "#FFFFFF"
_CLR_DISABLED = "rgba(255, 255, 255, 0.25)"
_CLR_BORDER_SOFT = "rgba(255, 255, 255, 0.05)"
_CLR_BORDER_ACTIVE = "#007AFF"
_CLR_BLUE = "#007AFF"
_CLR_BLUE_HOVER = "#147CE5"
_CLR_BLUE_PRESS = "#0062CC"
_CLR_BLUE_LIGHT = "#64D2FF"
_CLR_GREEN_OK = "#30D158"
_CLR_GREEN_OK_HOVER = "#28B44F"
_CLR_ROSE_ICON = "#FF453A"
_CLR_WARN_ICON = "#FF9500"
_CLR_CONNECT_TEXT = "#30D158"
_CLR_CONNECT_HOVER = "rgba(48, 209, 88, 0.25)"
_CLR_CONNECT_PRESS = "rgba(48, 209, 88, 0.35)"
_CLR_DISCONNECT_BG = "rgba(255, 69, 58, 0.15)" # 半透明红底
_CLR_DISCONNECT_HOVER = "rgba(255, 69, 58, 0.25)"
_CLR_DISCONNECT_PRESS = "rgba(255, 69, 58, 0.35)"
_CLR_DISCONNECT_TEXT = "#FF453A"

_DLG_CHK_SVG = os.path.join(
    get_resource_base(), "resources", "modules", "SVG_Serial", "checkmark.svg"
).replace("\\", "/")


def _serial_search_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid {_CLR_BORDER};
            border-radius: {r}px;
            color: {_CLR_TEXT_SOFT};
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 500;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            border: 1px solid {_CLR_BORDER_HOVER};
            background-color: rgba(255, 255, 255, 0.08);
        }}
        QPushButton:pressed {{
            background-color: rgba(255, 255, 255, 0.12);
        }}
        QPushButton:disabled {{
            background-color: transparent;
            color: {_CLR_DISABLED};
            border: 1px solid {_CLR_BORDER_SOFT};
        }}
    """


def _serial_connect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: {_CLR_CONNECT_BG};
            border: none;
            border-radius: {r}px;
            color: {_CLR_CONNECT_TEXT};
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 600;
            min-height: {h}px;
            min-width: 96px;
        }}
        QPushButton:hover {{
            background-color: {_CLR_CONNECT_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {_CLR_CONNECT_PRESS};
        }}
        QPushButton:disabled {{
            background-color: rgba(255, 255, 255, 0.04);
            color: {_CLR_DISABLED};
            border: none;
        }}
    """


def _serial_disconnect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: {_CLR_DISCONNECT_BG};
            border: none;
            border-radius: {r}px;
            color: {_CLR_DISCONNECT_TEXT};
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 600;
            min-height: {h}px;
            min-width: 96px;
        }}
        QPushButton:hover {{
            background-color: {_CLR_DISCONNECT_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {_CLR_DISCONNECT_PRESS};
        }}
        QPushButton:disabled {{
            background-color: rgba(255, 255, 255, 0.04);
            color: {_CLR_DISABLED};
            border: none;
        }}
    """


def inline_serial_label_style():
    return f"font-size: 12px; color: {_CLR_TEXT_MUTED}; background: transparent; border: none; font-family: {_UI_FONT};"


def inline_serial_search_button_extra_style(size):
    return f"""
                QPushButton {{
                    padding: 0px;
                    margin: 0px;
                    min-width: {size}px;
                    max-width: {size}px;
                    min-height: {size}px;
                    max-height: {size}px;
                }}
            """


def body_splitter_style():
    return f"""
            QSplitter {{ background-color: {_CLR_BG_MAIN}; }}
            QSplitter::handle {{ background-color: {_CLR_BG_MAIN}; border: none; }}
            QSplitter::handle:hover {{ background-color: rgba(255, 255, 255, 0.03); }}
        """


def center_widget_style():
    return f"QFrame#scCenterWidget {{ background-color: {_CLR_BG_PANEL}; border: 1px solid {_CLR_BORDER}; border-radius: 12px; }}"


def toolbar_style():
    return f"""
            QFrame#scToolbar {{
                background-color: {_CLR_BG_CARD};
                border-bottom: 1px solid {_CLR_BORDER};
            }}
        """


def main_connect_button_style(connected=False):
    if connected:
        return f"""
                QPushButton {{
                    min-height: 0px; max-height: 28px; padding: 4px 12px; border-radius: {_SERIAL_BTN_RADIUS}px;
                    background-color: {_CLR_DISCONNECT_BG}; color: {_CLR_DISCONNECT_TEXT}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 600; border: none;
                }}
                QPushButton:hover {{ background-color: {_CLR_DISCONNECT_HOVER}; }}
                QPushButton:focus {{ border: 1px solid {_CLR_BLUE}; }}
                QPushButton:pressed {{ background-color: {_CLR_DISCONNECT_PRESS}; }}
            """
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; padding: 4px 12px; border-radius: {_SERIAL_BTN_RADIUS}px;
                background-color: {_CLR_CONNECT_BG}; color: {_CLR_CONNECT_TEXT}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 600; border: none;
            }}
            QPushButton:hover {{ background-color: {_CLR_CONNECT_HOVER}; }}
            QPushButton:focus {{ border: 1px solid {_CLR_BLUE}; }}
            QPushButton:pressed {{ background-color: {_CLR_CONNECT_PRESS}; }}
        """


def toolbar_connect_button_style():
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; padding: 4px 14px; border-radius: {_SERIAL_BTN_RADIUS}px;
                background-color: {_CLR_CONNECT_BG}; color: {_CLR_CONNECT_TEXT}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 600; border: none;
            }}
            QPushButton:hover {{ background-color: {_CLR_CONNECT_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_CONNECT_PRESS}; }}
        """


def log_panel_button_style(disabled=False):
    disabled_qss = f"\n            QPushButton:disabled {{ background-color: transparent; border-color: {_CLR_BORDER_SOFT}; }}" if disabled else ""
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 26px; min-width: 26px; max-width: 26px;
                padding: 0px; border-radius: 5px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; border: 1px solid {_CLR_BORDER};
            }}
            QPushButton:hover {{ border-color: {_CLR_BORDER_HOVER}; background-color: rgba(255, 255, 255, 0.04); }}
            QPushButton:focus {{ border-color: {_CLR_BLUE}; background-color: {_CLR_INPUT_BG}; }}
            QPushButton:pressed {{ background-color: rgba(255, 255, 255, 0.08); }}{disabled_qss}
        """


def separator_style(transparent=False):
    suffix = " background: transparent;" if transparent else ""
    return f"color: {_CLR_BORDER};{suffix}"


def sidebar_wrapper_style():
    return f"""
            QFrame#scSidebarWrapper {{
                background-color: {_CLR_BG_PANEL};
                border: 1px solid {_CLR_BORDER};
                border-radius: 12px;
            }}
        """


def transparent_scroll_area_style():
    return """
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
        """


def thin_scrollbar_style():
    return f"""
            QScrollBar:vertical {{
                width: 5px;
                margin: 0px;
                background: transparent;
                border: none;
                border-radius: 2.5px;
            }}
            QScrollBar::handle:vertical {{
                background: {_CLR_SCROLLBAR};
                min-height: 30px;
                border-radius: 2.5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {_CLR_SCROLLBAR_HV};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: transparent;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """


def compact_spinbox_style(up_button_width=12, padding="2px 4px"):
    return f"""
            QSpinBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
                color: {_CLR_TEXT_BODY}; font-size: 12px; font-family: {_UI_FONT}; padding: {padding};
            }}
            QSpinBox:focus {{ border: 1px solid {_CLR_BLUE}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: {up_button_width}px; border: none; background: transparent; }}
        """


def unit_label_style(font="term", size=11):
    family = _TERM_FONT if font == "term" else _UI_FONT
    return f"color: {_CLR_TEXT_MUTED}; font-size: {size}px; font-family: {family}; background: transparent; border: none;"


def log_frame_style(with_border=False):
    border = f"1px solid {_CLR_BORDER}" if with_border else "none"
    return f"""
            QFrame#scLogFrame {{
                background-color: {_CLR_BG_LOG};
                border: {border};
                border-radius: 10px;
            }}
        """


def transparent_background_style():
    return "background: transparent;"


def log_title_style():
    return f"color: {_CLR_TEXT_WHITE}; font-size: 13px; font-weight: 600; font-family: {_UI_FONT}; background: transparent;"


def log_toolbar_button_style(checked_variant=False, max_height=26, padding="4px 12px", radius=5):
    if checked_variant:
        checked_qss = f"""
            QPushButton:checked {{
                background-color: rgba(0, 122, 255, 0.15); color: {_CLR_BLUE_LIGHT}; border: 1px solid rgba(0, 122, 255, 0.4);
                font-weight: 600;
            }}
            QPushButton:checked:hover {{
                background-color: rgba(0, 122, 255, 0.25); color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BLUE};
            }}
        """
    else:
        checked_qss = f"QPushButton:checked {{ background-color: rgba(255,255,255,0.1); color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BORDER_HOVER}; }}"
    
    return f"""
                QPushButton {{
                    min-height: 0px; max-height: {max_height}px; padding: {padding}; border-radius: {radius}px;
                    background-color: rgba(255, 255, 255, 0.04); color: {_CLR_TEXT_BODY}; font-size: 11px;
                    font-family: {_UI_FONT}; font-weight: 500; border: 1px solid {_CLR_BORDER};
                }}
                QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.08); color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BORDER_HOVER}; }}
                QPushButton:focus {{ border: 1px solid {_CLR_BLUE}; }}
                QPushButton:pressed {{ background-color: rgba(255, 255, 255, 0.12); }}
                {checked_qss}
            """


def filter_input_style():
    return f"""
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
                color: {_CLR_INPUT_TEXT}; font-size: 12px; font-family: {_UI_FONT}; padding: 4px 8px; min-height: 24px; max-height: 24px;
                selection-background-color: {_CLR_SELECTION_BG}; selection-color: {_CLR_SELECTION_TEXT};
            }}
            QLineEdit:focus {{ border: 1px solid {_CLR_BLUE}; }}
        """


def filter_match_label_style():
    return f"color: {_CLR_TEXT_MUTED}; font-size: 11px; font-family: {_UI_FONT}; background: transparent; min-width: 60px;"


def small_label_style(size=12, font="ui", color=None):
    family = _TERM_FONT if font == "term" else _UI_FONT
    colors = {
        "soft": _CLR_TEXT_SOFT,
        "muted": _CLR_TEXT_MUTED,
        "white": _CLR_TEXT_WHITE,
    }
    return f"color: {colors.get(color, color or _CLR_TEXT_MUTED)}; font-size: {size}px; font-family: {family}; background: transparent;"


def log_edit_style(font_family=None, font_size=13, padding="10px 12px", include_line_height=False):
    family = f"{font_family}, {_TERM_FONT}" if font_family else _TERM_FONT
    line_height = " line-height: 1.4;" if include_line_height else ""
    return f"""
                QTextEdit {{
                    background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid {_CLR_BORDER};
                    color: {_CLR_TEXT_BODY}; font-family: {family}; font-size: {font_size}px; font-weight: 400;
                    padding: {padding};{line_height}
                    selection-background-color: {_CLR_SELECTION_BG};
                    selection-color: {_CLR_SELECTION_TEXT};
                }}
            """


def log_document_style():
    return "p, div { line-height: 140%; margin: 0; padding: 0; }"


def history_combo_style():
    return f"""
            QComboBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 6px;
                color: {_CLR_INPUT_TEXT}; font-size: 13px; font-family: {_UI_FONT};
                padding: 4px 28px 4px 10px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
            QComboBox:focus {{ border: 1px solid {_CLR_BLUE}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QComboBox QLineEdit {{
                background-color: transparent; border: none;
                color: {_CLR_INPUT_TEXT}; font-size: 13px; font-family: {_UI_FONT};
                padding: 0px; margin: 0px;
            }}
        """


def transparent_toolbar_button_style():
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; padding: 4px 12px; border-radius: 5px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: none;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.04); color: {_CLR_TEXT_WHITE}; }}
            QPushButton:focus {{ border: 1px solid {_CLR_BLUE}; background-color: {_CLR_INPUT_BG}; }}
            QPushButton:pressed {{ background-color: rgba(255, 255, 255, 0.08); }}
            QPushButton:checked {{ background-color: rgba(255, 255, 255, 0.06); color: {_CLR_TEXT_WHITE}; }}
        """


def send_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_SEND_BG}; border: none; border-radius: 5px;
                color: {_CLR_TEXT_WHITE}; font-weight: 600; font-size: 12px;
                font-family: {_UI_FONT}; padding: 4px 18px;
            }}
            QPushButton:hover {{ background-color: {_CLR_BLUE_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_BLUE_PRESS}; }}
            QPushButton:disabled {{ background-color: rgba(255, 255, 255, 0.05); color: {_CLR_DISABLED}; }}
        """


def quick_commands_panel_style():
    return f"""
            QFrame#quickCommandsPanel {{
                background-color: {_CLR_BG_PANEL};
                border: 1px solid {_CLR_BORDER};
                border-radius: 12px;
            }}
            QFrame#scQuickHeaderFrame {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {_CLR_BORDER};
            }}
            QFrame#scQuickToolbar {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {_CLR_BORDER};
            }}
            QLabel#quickCommandsTitle {{
                color: {_CLR_TEXT_BODY};
                font-weight: 600;
                font-size: 12px;
                font-family: {_UI_FONT};
                background: transparent;
            }}
            QFrame#quickCommandsPanel QPushButton {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER};
                border-radius: 4px;
                padding: 3px 8px;
                min-height: 18px;
            }}
            QFrame#quickCommandsPanel QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_TEXT_WHITE};
            }}
            QFrame#quickCommandsPanel QPushButton#primaryButton {{
                background-color: {_CLR_BLUE};
                color: {_CLR_TEXT_WHITE};
                border: none;
            }}
            QFrame#quickCommandsPanel QPushButton#primaryButton:hover {{
                background-color: {_CLR_BLUE_HOVER};
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton {{
                background-color: rgba(255, 255, 255, 0.03);
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border-color: {_CLR_BLUE};
                color: {_CLR_TEXT_WHITE};
            }}
        """


def project_tabs_style():
    return f"""
            QTabBar {{
                background: transparent;
                border-bottom: 1px solid {_CLR_BORDER};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {_CLR_TEXT_MUTED};
                border: none;
                padding: 6px 14px;
                font-size: 12px;
                font-family: {_UI_FONT};
                font-weight: 500;
            }}
            QTabBar::tab:hover {{
                color: {_CLR_TEXT_SOFT};
            }}
            QTabBar::tab:selected {{
                color: {_CLR_TEXT_WHITE};
                border-bottom: 2px solid {_CLR_BLUE};
                font-weight: 600;
            }}
        """


def quick_combo_style():
    return f"""
            QComboBox {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER};
                border-radius: 5px;
                padding: 2px 6px;
                min-height: 18px;
                font-size: 11px;
                font-family: {_UI_FONT};
            }}
            QComboBox:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
            QComboBox:focus {{ border-color: {_CLR_BLUE}; }}
            QComboBox QAbstractItemView {{
                background-color: {_CLR_BG_CARD};
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER};
                selection-background-color: {_CLR_BLUE};
                selection-color: {_CLR_TEXT_WHITE};
                outline: 0;
            }}
        """


def quick_toolbar_button_style(max_height=None, padding="3px 8px", radius=4, min_height=18):
    max_height_qss = f" max-height: {max_height}px;" if max_height is not None else ""
    return f"""
            QPushButton {{
                min-height: {min_height}px;{max_height_qss}
                background-color: rgba(255, 255, 255, 0.04);
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER};
                border-radius: {radius}px;
                padding: {padding};
                font-size: 11px;
                font-family: {_UI_FONT};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_TEXT_WHITE};
            }}
            QPushButton:focus {{ border-color: {_CLR_BLUE}; }}
            QPushButton:checked {{
                background-color: rgba(0, 122, 255, 0.15);
                color: {_CLR_BLUE_LIGHT};
                border: 1px solid rgba(0, 122, 255, 0.3);
            }}
        """


def quick_add_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_CONNECT_BG};
                color: {_CLR_CONNECT_TEXT};
                border: 1px solid rgba(48, 209, 88, 0.2);
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {_CLR_CONNECT_HOVER}; }}
        """


def quick_button_scroll_style():
    return "QScrollArea { background: transparent; border: none; }"


def quick_button_container_style():
    return "QWidget#scQuickBtnContainer { background: transparent; }"


def status_bar_style():
    return f"""
            QFrame#scStatusBar {{
                background-color: {_CLR_BG_MAIN};
                border-top: 1px solid {_CLR_BORDER};
            }}
            QLabel {{ font-size: 11px; font-family: {_UI_FONT}; background: transparent; }}
        """


def status_label_style(kind="muted", include_font=False, compact=False):
    colors = {
        "ok": "#30D158",
        "connected": _CLR_CONNECT_TEXT,
        "error": _CLR_DISCONNECT_TEXT,
        "warn": _CLR_WARNING,
        "locked": "#BF5AF2",
        "rx": _CLR_RX,
        "tx": _CLR_TX,
        "muted": _CLR_TEXT_MUTED,
        "accent": _CLR_BLUE,
    }
    base = f"color: {colors.get(kind, kind)};"
    if include_font:
        base += f" font-size: 11px; font-family: {_TERM_FONT}; background: transparent;"
    return base


def extra_log_error_color():
    return _CLR_DISCONNECT_TEXT


def section_card_style():
    return """
            QFrame#scSectionCard {
                background-color: transparent;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
        """


def section_title_style():
    return f"color: {_CLR_TEXT_MUTED}; font-size: 11px; font-weight: 700; font-family: {_UI_FONT}; background: transparent; border: none; margin-bottom: 4px; text-transform: uppercase;"


def field_label_style():
    return f"color: {_CLR_TEXT_LABEL}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; border: none;"


def checkbox_style(checkmark_svg):
    return (
        f"QCheckBox {{ color: {_CLR_TEXT_LABEL}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; spacing: 6px; }}"
        f"QCheckBox::indicator {{"
        f"  width: 14px; height: 14px;"
        f"  border: 1px solid {_CLR_BORDER}; border-radius: 4px;"
        f"  background-color: {_CLR_INPUT_BG};"
        f"}}"
        f"QCheckBox::indicator:hover {{"
        f"  border-color: {_CLR_BORDER_HOVER}; background-color: rgba(255,255,255,0.02);"
        f"}}"
        f"QCheckBox::indicator:checked {{"
        f"  background-color: {_CLR_BLUE}; border-color: {_CLR_BLUE};"
        f"  image: url({checkmark_svg});"
        f"}}"
    )


def toggle_colors():
    return {
        "border": _CLR_BORDER,
        "background": _CLR_INPUT_BG,
        "knob": _CLR_BLUE,
        "active_text": _CLR_TEXT_WHITE,
        "inactive_text": _CLR_TEXT_MUTED,
    }


def dialog_line_edit_style(size=13, min_height=26, padding="5px 8px"):
    return f"""
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
                color: {_CLR_TEXT_BODY}; font-size: {size}px; font-family: {_UI_FONT}; padding: {padding}; min-height: {min_height}px;
            }}
            QLineEdit:focus {{ border: 1px solid {_CLR_BLUE}; }}
        """


def quick_preview_popup_shadow():
    return {
        "blur_radius": 20,
        "offset_x": 0,
        "offset_y": 8,
        "color": (0, 0, 0, 180),
    }


def quick_preview_popup_style():
    return f"""
            QFrame#quickCmdPreviewPopupWindow {{
                background-color: transparent;
                border: none;
            }}
            QFrame#quickCmdPreviewPopup {{
                background-color: rgba(30, 30, 30, 240);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 10px;
            }}
            QLabel#quickCmdPreviewBadge {{
                color: #FFFFFF;
                background-color: {_CLR_BLUE};
                border-radius: 3px;
                padding: 1px 4px;
                font-family: {_UI_FONT};
                font-size: 9px;
                font-weight: 700;
            }}
            QLabel#quickCmdPreviewTitle {{
                color: {_CLR_TEXT_TITLE};
                font-family: {_UI_FONT};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }}
            QLabel#quickCmdPreviewContent {{
                color: {_CLR_TEXT_BODY};
                background-color: rgba(15, 15, 15, 200);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 6px;
                padding: 6px 8px;
                font-family: {_TERM_FONT};
                font-size: 11px;
            }}
        """


def quick_command_button_style():
    return f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.04);
                    color: {_CLR_TEXT_SOFT};
                    border: 1px solid {_CLR_BORDER};
                    border-radius: 4px;
                    padding: 3px 9px;
                    min-height: 16px;
                    font-size: 11px;
                    font-weight: 500;
                    font-family: {_UI_FONT};
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.08);
                    border-color: {_CLR_BORDER_HOVER};
                    color: {_CLR_TEXT_WHITE};
                }}
                QPushButton:pressed {{
                    background-color: rgba(255, 255, 255, 0.12);
                }}
            """


def quick_cmd_dialog_style():
    return f"""
            QDialog {{
                background-color: {_CLR_BG_MAIN};
                color: {_CLR_TEXT_BODY};
            }}
            QLabel {{
                color: {_CLR_TEXT_LABEL}; font-size: 12px; font-family: {_UI_FONT}; background: transparent;
            }}
            QComboBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
                color: {_CLR_TEXT_BODY}; font-size: 12px; font-family: {_UI_FONT}; padding: 4px 8px; min-height: 24px;
            }}
            QComboBox:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
            QComboBox:focus {{ border-color: {_CLR_BLUE}; }}
            QComboBox QAbstractItemView {{
                background-color: {_CLR_BG_CARD}; color: {_CLR_TEXT_BODY};
                border: 1px solid {_CLR_BORDER}; selection-background-color: {_CLR_BLUE};
                outline: 0;
            }}
        """


def dialog_cancel_button_style():
    return f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05); border: 1px solid {_CLR_BORDER}; border-radius: 5px;
                color: {_CLR_TEXT_SOFT}; font-size: 12px; font-family: {_UI_FONT}; padding: 5px 16px;
            }}
            QPushButton:hover {{ background-color: rgba(255, 255, 255, 0.1); color: {_CLR_TEXT_WHITE}; border-color: {_CLR_BORDER_HOVER}; }}
        """


def dialog_ok_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_BLUE}; border: none; border-radius: 5px;
                color: {_CLR_TEXT_WHITE}; font-weight: 500; font-size: 12px; font-family: {_UI_FONT}; padding: 5px 16px;
            }}
            QPushButton:hover {{ background-color: {_CLR_BLUE_HOVER}; }}
        """


def log_color_info_style():
    return f"color: {_CLR_TEXT_MUTED}; font-size: 11px; font-family: {_UI_FONT}; background: transparent;"


def log_color_info_text():
    return "RX → Green (#30D158)    TX → Purple (#BF5AF2)\nINFO → Blue (#64D2FF)    WARN → Yellow (#FFD60A)    ERROR → Red (#FF453A)"


_DLG_STYLE = f"""
    QDialog {{
        background-color: {_CLR_BG_MAIN};
        color: {_CLR_TEXT_BODY};
    }}
    QLabel {{ color: {_CLR_TEXT_LABEL}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; }}
    QLabel#dlgSectionTitle {{
        color: {_CLR_TEXT_WHITE}; font-size: 12px; font-weight: 600; font-family: {_UI_FONT}; background: transparent;
    }}
    QFrame#dlgSep {{ background-color: {_CLR_BORDER}; }}
    QCheckBox {{ color: {_CLR_TEXT_LABEL}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; }}
    QCheckBox::indicator {{
        width: 13px; height: 13px;
        border: 1px solid {_CLR_BORDER}; border-radius: 4px;
        background-color: {_CLR_INPUT_BG};
    }}
    QCheckBox::indicator:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
    QCheckBox::indicator:checked {{
        background-color: {_CLR_BLUE}; border-color: {_CLR_BLUE};
        image: url({_DLG_CHK_SVG});
    }}
    QSpinBox {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
        color: {_CLR_TEXT_BODY}; font-size: 12px; font-family: {_UI_FONT}; padding: 2px 6px;
    }}
    QSpinBox:focus {{ border: 1px solid {_CLR_BLUE}; }}
    QLineEdit {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid {_CLR_BORDER}; border-radius: 5px;
        color: {_CLR_TEXT_BODY}; font-size: 12px; font-family: {_UI_FONT}; padding: 4px 8px;
    }}
    QLineEdit:focus {{ border: 1px solid {_CLR_BLUE}; }}
    QPushButton#dlgOkBtn {{
        background-color: {_CLR_BLUE}; border: none; border-radius: 5px;
        color: {_CLR_TEXT_WHITE}; font-weight: 500; font-size: 12px; font-family: {_UI_FONT}; padding: 5px 18px;
    }}
    QPushButton#dlgOkBtn:hover {{ background-color: {_CLR_BLUE_HOVER}; }}
    QPushButton#dlgCancelBtn {{
        background-color: rgba(255, 255, 255, 0.05); border: 1px solid {_CLR_BORDER}; border-radius: 5px;
        color: {_CLR_TEXT_SOFT}; font-size: 12px; font-family: {_UI_FONT}; padding: 5px 18px;
    }}
    QPushButton#dlgCancelBtn:hover {{ border-color: {_CLR_BORDER_HOVER}; background-color: rgba(255, 255, 255, 0.1); color: {_CLR_TEXT_WHITE}; }}
    QTabWidget::pane {{
        background-color: {_CLR_BG_PANEL};
        border: 1px solid {_CLR_BORDER};
        border-radius: 8px;
        padding: 8px;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {_CLR_TEXT_MUTED};
        padding: 5px 14px;
        font-size: 12px;
        font-family: {_UI_FONT};
        font-weight: 500;
    }}
    QTabBar::tab:hover {{ color: {_CLR_TEXT_SOFT}; }}
    QTabBar::tab:selected {{
        color: {_CLR_TEXT_WHITE};
        border-bottom: 2px solid {_CLR_BLUE};
    }}
"""

DARK_CARD_STYLE = f"""
    QWidget {{
        background-color: {_CLR_BG_MAIN};
        color: {_CLR_TEXT_BODY};
    }}
    QLabel {{ background-color: transparent; color: {_CLR_TEXT_LABEL}; }}
    QLabel#statusOk {{ color: {_CLR_GREEN_OK}; font-weight: 600; }}
    QLabel#statusWarn {{ color: {_CLR_WARN_ICON}; font-weight: 600; }}
    QLabel#statusErr {{ color: {_CLR_DISCONNECT_TEXT}; font-weight: 600; }}
    QFrame#cardFrame {{
        background-color: {_CLR_BG_PANEL};
        border: 1px solid {_CLR_BORDER};
        border-radius: 8px;
    }}
    QComboBox {{
        background-color: {_CLR_INPUT_BG};
        color: {_CLR_TEXT_BODY};
        border: 1px solid {_CLR_BORDER};
        border-radius: 5px;
        padding: 4px 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {_CLR_BG_CARD};
        color: {_CLR_TEXT_BODY};
        border: 1px solid {_CLR_BORDER};
        selection-background-color: {_CLR_BLUE};
    }}
"""

__all__ = [name for name in globals() if name.startswith("_CLR_")]
__all__ += [
    name for name, value in globals().items()
    if callable(value) and not name.startswith("__")
]
__all__ += [
    "_SERIAL_BTN_HEIGHT", "_SERIAL_BTN_ICON_SIZE", "_SERIAL_BTN_RADIUS",
    "_TERM_FONT", "_UI_FONT", "_DLG_STYLE", "DARK_CARD_STYLE",
]