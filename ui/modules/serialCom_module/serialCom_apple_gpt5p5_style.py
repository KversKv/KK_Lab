import os

from PySide6.QtWidgets import (
    QComboBox, QStyle, QStyleOptionComboBox, QListView, QStyledItemDelegate
)
from PySide6.QtCore import Qt, QRect, QRectF, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFontMetrics, QPalette

from ui.resource_path import get_resource_base


# Apple-inspired light theme for the serial console.
# Keep the same public API as serialCom_dark_style.py so callers can switch
# by changing only the imported style module.
_SERIAL_BTN_HEIGHT = 26
_SERIAL_BTN_ICON_SIZE = 14
_SERIAL_BTN_RADIUS = 7
_TERM_FONT = '"JetBrains Mono", "Fira Code", Consolas, "Menlo", "Courier New", monospace'
_UI_FONT = '"Inter", "PingFang SC", "Microsoft YaHei", "Segoe UI", -apple-system, sans-serif'

_CLR_BG_MAIN = "#fcfdfe"
_CLR_BG_PANEL = "#fcfdfe"
_CLR_BG_CARD = "#FFFFFF"
_CLR_BG_LOG = "#FBFBFD"
_CLR_BORDER = "#D2D2D7"
_CLR_BORDER_HOVER = "#A1A1A6"
_CLR_TEXT_TITLE = "#1D1D1F"
_CLR_TEXT_ACCENT = "#FF9F0A"
_CLR_TEXT_SUBTITLE = "#0A84FF"
_CLR_TEXT_LABEL = "#515154"
_CLR_TEXT_BTN = "#0A84FF"
_CLR_TEXT_BTN_LOG = "#3A3A3C"
_CLR_TEXT_BODY = "#1D1D1F"
_CLR_TEXT_TIME = "#8E8E93"
_CLR_TEXT_LINENO = "#A1A1A6"
_CLR_TEXT_INFO = "#0A84FF"
_CLR_INPUT_BG = "#F2F2F7"
_CLR_INPUT_TEXT = "#1D1D1F"
_CLR_CURSOR = "#007AFF"
_CLR_SELECTION_BG = "#BBD7FF"
_CLR_SELECTION_TEXT = "#000000"
_CLR_SCROLLBAR = "#C7C7CC"
_CLR_SCROLLBAR_HV = "#AEAEB2"
_CLR_CONNECT_FG = "#30D158"
_CLR_CONNECT_BG = "#E8F8EE"
_CLR_SEND_BG = "#007AFF"
_CLR_SEND_HOVER = "#0A84FF"
_CLR_SEND_PRESS = "#0066CC"
_CLR_WARNING = "#FF9F0A"
_CLR_ERROR = "#FF3B30"
_CLR_RX = "#1D1D1F"
_CLR_TX = "#007AFF"
_CLR_FILTER_TEXT = "#5E5CE6"
_CLR_FILTER_BG = "#EFEFFF"
_CLR_FILTER_BORDER = "#0A84FF"
_CLR_TOGGLE_ON = "#34C759"

_CLR_TEXT_MUTED = "#6E6E73"
_CLR_TEXT_WHITE = "#FFFFFF"
_CLR_TEXT_SOFT = "#3A3A3C"
_CLR_TEXT_TAB = "#1D1D1F"
_CLR_DISABLED = "#AEAEB2"
_CLR_BORDER_SOFT = "#E5E5EA"
_CLR_BORDER_ACTIVE = "#007AFF"
_CLR_BLUE = "#007AFF"
_CLR_BLUE_HOVER = "#0A84FF"
_CLR_BLUE_PRESS = "#0066CC"
_CLR_BLUE_LIGHT = "#64D2FF"
_CLR_GREEN_OK = "#34C759"
_CLR_GREEN_OK_HOVER = "#30B650"
_CLR_ROSE_ICON = "#FF375F"
_CLR_WARN_ICON = "#FF9F0A"
_CLR_CONNECT_TEXT = "#248A3D"
_CLR_CONNECT_HOVER = "#DDF7E6"
_CLR_CONNECT_PRESS = "#CDEFD9"
_CLR_DISCONNECT_BG = "#FFECEA"
_CLR_DISCONNECT_HOVER = "#FFDAD6"
_CLR_DISCONNECT_PRESS = "#FFC8C2"
_CLR_DISCONNECT_TEXT = "#D70015"

_DLG_CHK_SVG = os.path.join(
    get_resource_base(), "resources", "modules", "SVG_Serial", "checkmark.svg"
).replace("\\", "/")
_SPIN_UP_SVG = os.path.join(
    get_resource_base(), "resources", "modules", "SVG_Serial", "spin_up.svg"
).replace("\\", "/")
_SPIN_DOWN_SVG = os.path.join(
    get_resource_base(), "resources", "modules", "SVG_Serial", "spin_down.svg"
).replace("\\", "/")


def _serial_search_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: transparent;
            border: 1px solid {_CLR_BORDER};
            border-radius: {r}px;
            color: {_CLR_TEXT_MUTED};
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 500;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            border: 1px solid {_CLR_BORDER_SOFT};
            color: {_CLR_TEXT_BTN_LOG};
            background-color: rgba(0, 122, 255, 0.08);
        }}
        QPushButton:pressed {{
            background-color: {_CLR_BG_CARD};
        }}
        QPushButton:disabled {{
            background-color: transparent;
            color: {_CLR_DISABLED};
            border: 1px solid {_CLR_BORDER};
        }}
    """


def _serial_connect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: {_CLR_CONNECT_BG};
            border: 1px solid rgba(52, 199, 89, 0.28);
            border-radius: {r}px;
            color: {_CLR_CONNECT_TEXT};
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 700;
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
            background-color: {_CLR_BORDER};
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
            font-weight: 700;
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
            background-color: {_CLR_BORDER};
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
            QSplitter::handle:hover {{ background-color: #D8E8FF; }}
        """


def center_vsplitter_style():
    return f"""
            QSplitter#scCenterVSplitter {{ background: transparent; }}
            QSplitter#scCenterVSplitter::handle {{
                background-color: transparent;
            }}
            QSplitter#scCenterVSplitter::handle:vertical {{
                height: 6px;
                margin: 1px 0;
                border-radius: 2px;
                background-color: transparent;
            }}
            QSplitter#scCenterVSplitter::handle:vertical:hover {{
                background-color: {_CLR_BORDER_HOVER};
            }}
        """


def center_widget_style():
    return f"""
            QFrame#scCenterWidget {{
                background-color: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(60, 60, 67, 0.16);
                border-radius: 12px;
            }}
        """


def toolbar_style():
    return f"""
            QFrame#scToolbar {{
                background-color: rgba(255, 255, 255, 0.86);
                border: 1px solid rgba(60, 60, 67, 0.14);
                border-radius: 12px;
            }}
        """


def main_connect_button_style(connected=False):
    if connected:
        return f"""
                QPushButton {{
                    min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                    background-color: {_CLR_DISCONNECT_BG}; color: {_CLR_DISCONNECT_TEXT}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 700; border: none;
                }}
                QPushButton:hover {{ background-color: {_CLR_DISCONNECT_HOVER}; }}
                QPushButton:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
                QPushButton:pressed {{ background-color: {_CLR_DISCONNECT_PRESS}; }}
            """
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                background-color: {_CLR_CONNECT_BG}; color: {_CLR_CONNECT_TEXT}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 700; border: none;
            }}
            QPushButton:hover {{ background-color: {_CLR_CONNECT_HOVER}; }}
            QPushButton:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
            QPushButton:pressed {{ background-color: {_CLR_CONNECT_PRESS}; }}
        """


def toolbar_connect_button_style():
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 14px; border-radius: 6px;
                background-color: {_CLR_CONNECT_BG}; color: {_CLR_CONNECT_TEXT}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 700; border: none;
            }}
            QPushButton:hover {{ background-color: {_CLR_CONNECT_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_CONNECT_PRESS}; }}
        """


def log_panel_button_style(disabled=False):
    disabled_qss = f"\n            QPushButton:disabled {{ background-color: transparent; border: none; }}" if disabled else ""
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; min-width: 28px; max-width: 28px;
                padding: 0px; border-radius: 7px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; border: none;
            }}
            QPushButton:hover {{ background-color: #F1F5F9; border: none; }}
            QPushButton:focus {{ background-color: {_CLR_INPUT_BG}; border: none; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; border: none; }}{disabled_qss}
        """


def separator_style(transparent=False):
    suffix = " background: transparent;" if transparent else ""
    return f"color: {_CLR_BORDER};{suffix}"


def sidebar_wrapper_style():
    return f"""
            QFrame#scSidebarWrapper {{
                background-color: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(60, 60, 67, 0.14);
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
                width: 4px;
                margin: 0px;
                background: transparent;
                border: none;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {_CLR_SCROLLBAR};
                min-height: 24px;
                border-radius: 2px;
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


def compact_spinbox_style(up_button_width=18, padding="1px 6px"):
    btn_w = max(16, int(up_button_width or 18))
    return f"""
            QSpinBox {{
                background-color: rgba(255, 255, 255, 0.86);
                border: 1px solid rgba(60, 60, 67, 0.16);
                border-radius: 8px;
                color: {_CLR_TEXT_BODY};
                font-size: 12px;
                font-family: {_UI_FONT};
                font-weight: 500;
                padding: {padding};
                padding-right: {btn_w + 4}px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
            QSpinBox:hover {{
                background-color: {_CLR_BG_CARD};
                border-color: rgba(0, 122, 255, 0.38);
            }}
            QSpinBox:focus {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_FILTER_BORDER};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                subcontrol-origin: border;
                width: {btn_w}px;
                background-color: rgba(242, 242, 247, 0.92);
                border-left: 1px solid rgba(60, 60, 67, 0.14);
            }}
            QSpinBox::up-button {{
                subcontrol-position: top right;
                border-top-right-radius: 7px;
                border-bottom: 1px solid rgba(60, 60, 67, 0.10);
            }}
            QSpinBox::down-button {{
                subcontrol-position: bottom right;
                border-bottom-right-radius: 7px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: #E8F2FF;
            }}
            QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
                background-color: rgba(0, 122, 255, 0.18);
            }}
            QSpinBox::up-arrow {{
                image: url({_SPIN_UP_SVG});
                width: 8px;
                height: 8px;
            }}
            QSpinBox::down-arrow {{
                image: url({_SPIN_DOWN_SVG});
                width: 8px;
                height: 8px;
            }}
        """


def unit_label_style(font="term", size=11):
    family = _TERM_FONT if font == "term" else _UI_FONT
    return f"color: {_CLR_TEXT_MUTED}; font-size: {size}px; font-family: {family}; background: transparent; border: none;"


def log_frame_style(with_border=False):
    border = f"1px solid rgba(60, 60, 67, 0.14)" if with_border else "1px solid rgba(60, 60, 67, 0.10)"
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
    return f"color: {_CLR_TEXT_TITLE}; font-size: 14px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;"


def log_toolbar_button_style(checked_variant=False, max_height=28, padding="5px 11px", radius=7):
    checked_qss = ""
    if checked_variant:
        checked_qss = f"""
            QPushButton:checked {{
                background-color: #E8F8EE; color: #248A3D; border: 1px solid #34C759;
                font-weight: 600;
            }}
            QPushButton:checked:hover {{
                background-color: #DDF7E6; color: #1F7A36; border: 1px solid #30D158;
            }}
            QPushButton:checked:pressed {{
                background-color: #C7F0D5; color: #1A6B30; border: 1px solid #248A3D;
            }}
        """
    else:
        checked_qss = f"""
            QPushButton:checked {{ background-color: #E8F2FF; color: {_CLR_BLUE}; border: 1px solid {_CLR_BORDER_ACTIVE}; }}
            QPushButton:checked:hover {{ background-color: #D6E7FF; color: {_CLR_BLUE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
            QPushButton:checked:pressed {{ background-color: #B9D4FF; color: {_CLR_BLUE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
        """
    return f"""
                QPushButton {{
                    min-height: 0px; max-height: {max_height}px; padding: {padding}; border-radius: {radius}px;
                    background-color: rgba(255, 255, 255, 0.74); color: {_CLR_TEXT_BTN_LOG}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 500; border: 1px solid {_CLR_BORDER_SOFT};
                }}
                QPushButton:focus {{ outline: none; }}
                QPushButton:hover {{ background-color: #E8F2FF; color: {_CLR_BLUE}; border: 1px solid {_CLR_BORDER_ACTIVE}; }}
                QPushButton:pressed {{ background-color: #CFE2FF; color: {_CLR_BLUE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
                {checked_qss}
            """


def log_icon_button_style(checked_variant="none", padding="7px"):
    if checked_variant == "blue":
        checked_qss = f"""
            QPushButton:checked {{ background-color: #E8F2FF; color: {_CLR_BLUE}; border: none; }}
            QPushButton:checked:hover {{ background-color: #D6E7FF; color: {_CLR_BLUE}; border: none; }}
            QPushButton:checked:pressed {{ background-color: #B9D4FF; color: {_CLR_BLUE}; border: none; }}
        """
    elif checked_variant == "green":
        checked_qss = f"""
            QPushButton:checked {{ background-color: #E8F8EE; color: #248A3D; border: none; }}
            QPushButton:checked:hover {{ background-color: #DDF7E6; color: #1F7A36; border: none; }}
            QPushButton:checked:pressed {{ background-color: #C7F0D5; color: #1A6B30; border: none; }}
        """
    else:
        checked_qss = ""
    return f"""
                QPushButton {{
                    min-height: 0px; max-height: 28px; padding: {padding}; border-radius: 7px;
                    background-color: transparent; color: {_CLR_TEXT_BTN_LOG}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 500; border: none;
                }}
                QPushButton:focus {{ outline: none; }}
                QPushButton:hover {{ background-color: #F1F5F9; color: {_CLR_TEXT_TITLE}; border: none; }}
                QPushButton:pressed {{ background-color: #E2E8F0; color: {_CLR_TEXT_TITLE}; border: none; }}
                {checked_qss}
            """


def filter_input_style():
    return f"""
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 7px;
                color: {_CLR_INPUT_TEXT}; font-size: 12px; font-family: {_UI_FONT}; padding: 4px 8px; min-height: 26px; max-height: 26px;
                selection-background-color: {_CLR_SELECTION_BG}; selection-color: {_CLR_SELECTION_TEXT};
            }}
            QLineEdit:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
        """


def filter_match_label_style():
    return f"color: {_CLR_FILTER_TEXT}; font-size: 11px; font-family: {_UI_FONT}; background: transparent; min-width: 60px;"


def small_label_style(size=12, font="ui", color=None):
    family = _TERM_FONT if font == "term" else _UI_FONT
    colors = {
        "soft": _CLR_TEXT_BTN_LOG,
        "muted": _CLR_TEXT_MUTED,
        "white": _CLR_TEXT_WHITE,
    }
    return f"color: {colors.get(color, color or _CLR_TEXT_MUTED)}; font-size: {size}px; font-family: {family}; background: transparent;"


def log_edit_style(font_family=None, font_size=14, padding="8px 10px", include_line_height=False):
    family = f"{font_family}, {_TERM_FONT}" if font_family else _TERM_FONT
    line_height = " line-height: 1.5;" if include_line_height else ""
    return f"""
                QTextEdit {{
                    background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid rgba(60, 60, 67, 0.10);
                    color: {_CLR_TEXT_BODY}; font-family: {family}; font-size: {font_size}px; font-weight: 400;
                    padding: {padding};{line_height}
                    selection-background-color: {_CLR_SELECTION_BG};
                    selection-color: {_CLR_SELECTION_TEXT};
                }}
            """


def log_document_style():
    return "p, div { line-height: 150%; margin: 0; padding: 0; }"


_CLR_HISTORY_COMBO_BG = "rgba(242, 242, 247, 0.64)"
_HISTORY_COMBO_FIELD_QCOLOR = QColor(242, 242, 247, 163)


def history_combo_style():
    return f"""
            QComboBox {{
                background-color: {_CLR_HISTORY_COMBO_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 7px;
                color: {_CLR_INPUT_TEXT}; font-size: 13px; font-family: {_TERM_FONT};
                padding: 3px 28px 3px 10px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
            QComboBox:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QComboBox QLineEdit {{
                background-color: transparent; border: none;
                color: {_CLR_INPUT_TEXT}; font-size: 13px; font-family: {_TERM_FONT};
                padding: 0px; margin: 0px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
        """


def transparent_toolbar_button_style():
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: none;
            }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:hover {{ border: 1px solid {_CLR_BORDER_SOFT}; color: {_CLR_TEXT_TITLE}; background-color: {_CLR_INPUT_BG}; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; }}
            QPushButton:checked {{ background-color: #E8F8EE; color: #248A3D; border: 1px solid #34C759; font-weight: 600; }}
            QPushButton:checked:hover {{ background-color: #DDF7E6; color: #1F7A36; border: 1px solid #30D158; }}
            QPushButton:checked:pressed {{ background-color: #C7F0D5; color: #1A6B30; border: 1px solid #248A3D; }}
        """


def sidebar_toggle_button_style():
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: none;
            }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:hover {{ color: {_CLR_TEXT_TITLE}; background-color: {_CLR_INPUT_BG}; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; }}
            QPushButton:checked {{ background-color: #E8F8EE; color: #248A3D; border: none; font-weight: 600; }}
            QPushButton:checked:hover {{ background-color: #DDF7E6; color: #1F7A36; border: none; }}
            QPushButton:checked:pressed {{ background-color: #C7F0D5; color: #1A6B30; border: none; }}
        """


def auto_scroll_button_style(padding="5px 11px"):
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; padding: {padding}; border-radius: 7px;
                background-color: rgba(255, 255, 255, 0.74); color: {_CLR_TEXT_BTN_LOG}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: 1px solid {_CLR_BORDER_SOFT};
            }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:hover {{ background-color: #E8F2FF; color: {_CLR_BLUE}; border: 1px solid {_CLR_BORDER_ACTIVE}; }}
            QPushButton:pressed {{ background-color: #CFE2FF; color: {_CLR_BLUE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
            QPushButton:checked {{ background-color: #E8F8EE; color: #248A3D; border: none; font-weight: 600; }}
            QPushButton:checked:hover {{ background-color: #DDF7E6; color: #1F7A36; border: none; }}
            QPushButton:checked:pressed {{ background-color: #C7F0D5; color: #1A6B30; border: none; }}
        """


def sidebar_toggle_icon_colors():
    return {"normal": _CLR_TEXT_MUTED, "checked": "#248A3D"}


def auto_scroll_icon_colors():
    return {"normal": _CLR_TEXT_BTN_LOG, "checked": "#248A3D"}


def send_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_SEND_BG}; border: none; border-radius: 8px;
                color: {_CLR_TEXT_WHITE}; font-weight: 700; font-size: 13px;
                font-family: {_UI_FONT}; padding: 3px 20px;
            }}
            QPushButton:hover {{ background-color: {_CLR_SEND_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_SEND_PRESS}; }}
            QPushButton:disabled {{ background-color: {_CLR_BORDER}; color: {_CLR_DISABLED}; }}
        """


def quick_commands_panel_style():
    return f"""
            QFrame#quickCommandsPanel {{
                background: transparent;
                border: none;
            }}
            QFrame#scQuickHeaderFrame {{
                background: transparent;
                border: none;
            }}
            QFrame#scQuickToolbar {{
                background: transparent;
                border: none;
            }}
            QLabel#quickCommandsTitle {{
                color: {_CLR_TEXT_TITLE};
                font-weight: 700;
                font-size: 12px;
                font-family: {_UI_FONT};
                background: transparent;
            }}
            QFrame#quickCommandsPanel QPushButton {{
                background-color: {_CLR_BORDER};
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER_SOFT};
                border-radius: 5px;
                padding: 3px 8px;
                min-height: 17px;
            }}
            QFrame#quickCommandsPanel QPushButton:hover {{
                background-color: {_CLR_BORDER_SOFT};
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_TEXT_WHITE};
            }}
            QFrame#quickCommandsPanel QPushButton:pressed {{
                background-color: {_CLR_BORDER_HOVER};
                border-color: {_CLR_DISABLED};
            }}
            QFrame#quickCommandsPanel QPushButton:disabled {{
                background-color: #E5E5EA;
                color: {_CLR_DISABLED};
                border-color: {_CLR_BORDER};
            }}
            QFrame#quickCommandsPanel QPushButton#primaryButton {{
                background-color: {_CLR_BLUE};
                color: {_CLR_TEXT_WHITE};
                border: 1px solid {_CLR_BORDER_ACTIVE};
            }}
            QFrame#quickCommandsPanel QPushButton#primaryButton:hover {{
                background-color: {_CLR_BLUE_HOVER};
                border-color: {_CLR_BLUE_LIGHT};
            }}
            QFrame#quickCommandsPanel QPushButton#primaryButton:pressed {{
                background-color: {_CLR_BLUE_PRESS};
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton {{
                background-color: #F2F2F7;
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER_SOFT};
                border-radius: 5px;
                padding: 4px 8px;
                min-height: 17px;
                min-width: 34px;
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton:hover {{
                background-color: #E8F2FF;
                border-color: {_CLR_BORDER_ACTIVE};
                color: {_CLR_BLUE};
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton:pressed {{
                background-color: {_CLR_BLUE};
                border-color: {_CLR_BLUE_LIGHT};
            }}
            QLabel#scQuickEmptyHint {{
                color: {_CLR_TEXT_MUTED};
                font-size: 12px;
                font-family: {_UI_FONT};
                background: transparent;
            }}
        """


def bottom_tabs_style():
    return f"""
            QTabWidget#scBottomTabs {{
                background: transparent;
                border: none;
            }}
            QTabWidget#scBottomTabs::pane {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_BORDER};
                border-radius: 10px;
                top: -1px;
            }}
            QTabWidget#scBottomTabs QTabBar {{
                background: transparent;
            }}
            QTabWidget#scBottomTabs QTabBar::tab {{
                background: transparent;
                color: {_CLR_TEXT_MUTED};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 5px 14px;
                margin-right: 2px;
                min-height: 18px;
                font-size: 12px;
                font-weight: 600;
                font-family: {_UI_FONT};
            }}
            QTabWidget#scBottomTabs QTabBar::tab:hover {{
                color: {_CLR_TEXT_TITLE};
            }}
            QTabWidget#scBottomTabs QTabBar::tab:selected {{
                color: {_CLR_TEXT_TITLE};
                border-bottom: 2px solid {_CLR_BLUE};
            }}
        """


def project_tabs_style():
    return f"""
            QTabBar {{
                background: transparent;
                border: none;
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {_CLR_TEXT_BTN_LOG};
                border: 1px solid transparent;
                border-radius: 7px;
                padding: 4px 12px;
                margin-right: 4px;
                margin-bottom: 0px;
                min-height: 16px;
                font-size: 11px;
                font-weight: 600;
                font-family: {_UI_FONT};
            }}
            QTabBar::tab:hover {{
                background-color: #F1F5F9;
                color: {_CLR_TEXT_TAB};
                border-color: transparent;
            }}
            QTabBar::tab:selected {{
                background-color: #F2F8FF;
                color: {_CLR_BLUE};
                border: 1px solid transparent;
                font-weight: 700;
            }}
            QTabBar::tab:selected:hover {{
                background-color: #F2F8FF;
                color: {_CLR_BLUE};
            }}
            QTabBar::tab:!selected {{
                margin-top: 0px;
            }}
            QTabBar::tear {{
                background: transparent;
                border: none;
                width: 0px;
            }}
            QTabBar QToolButton {{
                background-color: {_CLR_INPUT_BG};
                border: 1px solid {_CLR_BORDER_SOFT};
                border-radius: 3px;
                color: {_CLR_TEXT_MUTED};
                margin: 2px;
            }}
            QTabBar QToolButton:hover {{
                background-color: {_CLR_BORDER};
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_INPUT_TEXT};
            }}
        """


def quick_combo_style():
    return f"""
            QComboBox {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_SOFT};
                border: 1px solid rgba(60, 60, 67, 0.18);
                border-radius: 5px;
                padding: 2px 6px;
                min-height: 18px;
                font-size: 11px;
                font-family: {_UI_FONT};
                min-width: 63px;
            }}
            QComboBox:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
            QComboBox:focus {{ border-color: {_CLR_FILTER_BORDER}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER};
                selection-background-color: #E8F2FF;
                selection-color: {_CLR_BLUE};
                outline: 0;
            }}
        """


def quick_group_combo_bg_style():
    return """
            QComboBox { background-color: #FFFFFF; }
            QComboBox QAbstractItemView { background-color: #FFFFFF; }
        """


def quick_toolbar_button_style(max_height=None, padding="3px 8px", radius=5, min_height=18):
    max_height_qss = f" max-height: {max_height}px;" if max_height is not None else ""
    return f"""
            QPushButton {{
                min-height: {min_height}px;{max_height_qss}
                background-color: rgba(255, 255, 255, 0.72);
                color: {_CLR_TEXT_SOFT};
                border: 1px solid rgba(60, 60, 67, 0.18);
                border-radius: {radius}px;
                padding: {padding};
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #E8F2FF;
                border-color: {_CLR_BORDER_ACTIVE};
                color: {_CLR_BLUE};
            }}
            QPushButton:focus {{
                background-color: #E8F2FF;
                border-color: {_CLR_FILTER_BORDER};
                color: {_CLR_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {_CLR_BORDER_HOVER};
                border-color: {_CLR_DISABLED};
            }}
            QPushButton:checked {{
                background-color: #E8F2FF;
                color: {_CLR_BLUE};
                border: 1px solid {_CLR_BORDER_ACTIVE};
            }}
            QPushButton:disabled {{
                background-color: #E5E5EA;
                color: {_CLR_DISABLED};
                border-color: {_CLR_BORDER};
            }}
        """


def quick_group_button_style():
    return f"""
            QPushButton {{
                min-height: 18px;
                background-color: #FFFFFF;
                color: {_CLR_BLUE};
                border: 1px solid rgba(60, 60, 67, 0.18);
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #E8F2FF;
                border-color: {_CLR_BORDER_ACTIVE};
                color: {_CLR_BLUE};
            }}
            QPushButton:pressed {{
                background-color: {_CLR_BORDER_HOVER};
                border-color: {_CLR_DISABLED};
            }}
            QPushButton:disabled {{
                background-color: #E5E5EA;
                color: {_CLR_DISABLED};
                border-color: {_CLR_BORDER};
            }}
        """


def quick_add_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_BLUE};
                color: {_CLR_TEXT_WHITE};
                border: none;
                border-radius: 8px;
                padding: 3px 12px;
                min-height: 18px;
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {_CLR_BLUE_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {_CLR_BLUE_PRESS};
            }}
            QPushButton:disabled {{
                background-color: {_CLR_BORDER};
                color: {_CLR_DISABLED};
            }}
        """


def script_stop_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_DISCONNECT_TEXT};
                color: {_CLR_TEXT_WHITE};
                border: none;
                border-radius: 8px;
                padding: 3px 12px;
                min-height: 18px;
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #E0352B;
            }}
            QPushButton:pressed {{
                background-color: #C72A21;
            }}
            QPushButton:disabled {{
                background-color: {_CLR_BORDER};
                color: {_CLR_DISABLED};
            }}
        """


def script_add_step_button_style():
    return f"""
            QPushButton#scAddStepBtn {{
                background-color: #F2F2F7;
                color: {_CLR_TEXT_MUTED};
                border: 1px dashed {_CLR_BORDER};
                border-radius: 10px;
                padding: 7px 12px;
                font-size: 12px;
                font-family: {_UI_FONT};
                font-weight: 700;
            }}
            QPushButton#scAddStepBtn:hover {{
                background-color: #E8F2FF;
                color: {_CLR_SEND_BG};
                border: 1px dashed {_CLR_SEND_BG};
            }}
            QPushButton#scAddStepBtn:pressed {{
                background-color: #D7E8FF;
            }}
        """


def quick_button_scroll_style():
    return f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
        """


def quick_button_container_style():
    return "QWidget#scQuickBtnContainer { background: transparent; }"


def status_bar_style():
    return f"""
            QFrame#scStatusBar {{
                background-color: rgba(242, 242, 247, 0.72);
                border-top: 1px solid rgba(60, 60, 67, 0.10);
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }}
            QLabel {{ font-size: 11px; font-family: {_TERM_FONT}; background: transparent; }}
        """


def status_label_style(kind="muted", include_font=False, compact=False):
    colors = {
        "ok": "#34C759",
        "connected": _CLR_CONNECT_TEXT,
        "error": _CLR_DISCONNECT_TEXT,
        "warn": _CLR_WARNING,
        "locked": _CLR_FILTER_BORDER,
        "rx": _CLR_RX,
        "tx": _CLR_TX,
        "muted": _CLR_TEXT_MUTED,
        "accent": _CLR_FILTER_BORDER,
    }
    base = f"color: {colors.get(kind, kind)};"
    if include_font:
        base += f" font-size: 11px; font-family: {_TERM_FONT}; background: transparent;"
    return base


def extra_log_error_color():
    return _CLR_DISCONNECT_TEXT


def section_card_style():
    return f"""
            QFrame#scSectionCard {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid #E5E5EA;
                border-radius: 12px;
            }}
        """


def section_card_shadow():
    return {
        "blur_radius": 14,
        "offset_x": 0,
        "offset_y": 2,
        "color": (29, 29, 31, 18),
    }


def section_title_style():
    return (
        f"color: #374151; font-size: 11px; font-weight: 700; font-family: {_UI_FONT};"
        f" letter-spacing: 0.6px; background: transparent; border: none;"
    )


def section_header_divider_style():
    return "background-color: #F0F0F2; border: none;"


def field_label_style():
    return f"color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; border: none;"


def checkbox_style(checkmark_svg):
    return (
        f"QCheckBox {{ color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; spacing: 5px; }}"
        f"QCheckBox::indicator {{"
        f"  width: 13px; height: 13px;"
        f"  border: 1px solid {_CLR_BORDER}; border-radius: 3px;"
        f"  background-color: {_CLR_INPUT_BG};"
        f"}}"
        f"QCheckBox::indicator:hover {{"
        f"  border-color: {_CLR_BORDER_SOFT};"
        f"}}"
        f"QCheckBox::indicator:checked {{"
        f"  background-color: #007AFF; border-color: #007AFF;"
        f"  image: url({checkmark_svg});"
        f"}}"
    )


def toggle_colors():
    return {
        "border": _CLR_BORDER,
        "background": _CLR_INPUT_BG,
        "knob": "#007AFF",
        "active_text": _CLR_TEXT_WHITE,
        "inactive_text": _CLR_TEXT_MUTED,
    }


def dialog_line_edit_style(size=13, min_height=26, padding="5px 8px"):
    return f"""
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 7px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: {size}px; font-family: {_UI_FONT}; padding: {padding}; min-height: {min_height}px;
            }}
            QLineEdit:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
        """


def quick_preview_popup_shadow():
    return {
        "blur_radius": 24,
        "offset_x": 0,
        "offset_y": 10,
        "color": (29, 29, 31, 52),
    }


def quick_preview_popup_style():
    return f"""
            QFrame#quickCmdPreviewPopupWindow {{
                background-color: transparent;
                border: none;
            }}
            QFrame#quickCmdPreviewPopup {{
                background-color: rgba(255, 255, 255, 238);
                border: 1px solid rgba(60, 60, 67, 48);
                border-radius: 12px;
            }}
            QLabel#quickCmdPreviewBadge {{
                color: {_CLR_TEXT_WHITE};
                background-color: {_CLR_TEXT_ACCENT};
                border-radius: 5px;
                padding: 2px 5px;
                font-family: {_UI_FONT};
                font-size: 9px;
                font-weight: 800;
            }}
            QLabel#quickCmdPreviewTitle {{
                color: {_CLR_TEXT_TITLE};
                font-family: {_UI_FONT};
                font-size: 12px;
                font-weight: 700;
                background: transparent;
            }}
            QLabel#quickCmdPreviewContent {{
                color: {_CLR_INPUT_TEXT};
                background-color: rgba(242, 242, 247, 238);
                border: 1px solid rgba(60, 60, 67, 34);
                border-radius: 8px;
                padding: 7px 8px;
                font-family: {_TERM_FONT};
                font-size: 11px;
                line-height: 1.35;
            }}
            QLabel#quickCmdPreviewMeta {{
                color: {_CLR_TEXT_MUTED};
                font-family: {_UI_FONT};
                font-size: 10px;
                background: transparent;
            }}
        """


def quick_command_button_style():
    return f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    color: {_CLR_TEXT_SOFT};
                    border: 1px solid {_CLR_BORDER_SOFT};
                    border-radius: 10px;
                    padding: 8px 20px;
                    min-height: 30px;
                    min-width: 84px;
                    font-size: 12px;
                    font-weight: 700;
                    font-family: {_UI_FONT};
                }}
                QPushButton:hover {{
                    background-color: #E8F2FF;
                    border-color: #BBD7FF;
                    color: {_CLR_BLUE};
                }}
                QPushButton:focus {{
                    background-color: #E8F2FF;
                    border-color: #BBD7FF;
                    color: {_CLR_BLUE};
                }}
                QPushButton:pressed {{
                    background-color: {_CLR_BLUE};
                    border-color: {_CLR_BLUE_LIGHT};
                    color: {_CLR_TEXT_WHITE};
                }}
            """


def quick_action_overlay_style():
    return f"""
            QToolButton#quickCmdAction {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 1px;
            }}
            QToolButton#quickCmdAction:hover {{
                background-color: rgba(60, 60, 67, 28);
            }}
            QToolButton#quickCmdAction:disabled {{
                background-color: transparent;
            }}
        """


def quick_action_overlay_container_style():
    return f"""
            QFrame#quickCmdActionBar {{
                background-color: rgba(248, 248, 250, 0.97);
                border: 1px solid #CBD0D6;
                border-radius: 8px;
            }}
        """


def quick_cmd_dialog_style():
    return f"""
            QDialog {{
                background-color: {_CLR_BG_MAIN};
                color: {_CLR_TEXT_BTN_LOG};
            }}
            QLabel {{
                color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent;
            }}
            QLabel#qcTitle {{
                color: {_CLR_TEXT_TITLE}; font-size: 15px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;
            }}
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 8px;
                color: {_CLR_TEXT_BODY}; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 10px; min-height: 26px;
            }}
            QLineEdit:hover {{ border-color: rgba(0, 122, 255, 0.38); }}
            QLineEdit:focus {{ border: 1px solid {_CLR_BORDER_ACTIVE}; background-color: {_CLR_BG_CARD}; }}
            QLineEdit::placeholder {{ color: {_CLR_TEXT_MUTED}; }}
            QComboBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 8px;
                color: {_CLR_TEXT_BODY}; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 10px; min-height: 26px;
            }}
            QComboBox:hover {{ border-color: rgba(0, 122, 255, 0.38); }}
            QComboBox:focus {{ border: 1px solid {_CLR_BORDER_ACTIVE}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ image: url({_SPIN_DOWN_SVG}); width: 11px; height: 11px; }}
            QComboBox QAbstractItemView {{
                background-color: {_CLR_BG_CARD}; color: {_CLR_TEXT_BODY};
                border: 1px solid {_CLR_BORDER}; border-radius: 8px; padding: 4px;
                selection-background-color: {_CLR_INPUT_BG}; selection-color: {_CLR_BLUE};
                outline: 0;
            }}
            QCheckBox {{
                color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px; border: 1px solid {_CLR_BORDER}; border-radius: 4px;
                background-color: {_CLR_BG_CARD};
            }}
            QCheckBox::indicator:hover {{ border-color: {_CLR_BORDER_ACTIVE}; }}
            QCheckBox::indicator:checked {{
                background-color: {_CLR_BLUE}; border-color: {_CLR_BLUE}; image: url({_DLG_CHK_SVG});
            }}
        """


def dialog_cancel_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_BG_CARD}; border: 1px solid {_CLR_BORDER}; border-radius: 8px;
                color: {_CLR_TEXT_SOFT}; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 20px; min-height: 26px;
            }}
            QPushButton:hover {{ background-color: {_CLR_INPUT_BG}; border-color: {_CLR_BORDER_HOVER}; color: {_CLR_TEXT_BODY}; }}
            QPushButton:pressed {{ background-color: {_CLR_BORDER_SOFT}; }}
        """


def dialog_ok_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_BLUE}; border: none; border-radius: 8px;
                color: {_CLR_TEXT_WHITE}; font-weight: 700; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 20px; min-height: 26px;
            }}
            QPushButton:hover {{ background-color: {_CLR_BLUE_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_BLUE_PRESS}; }}
        """


def log_color_info_style():
    return f"color: {_CLR_TEXT_MUTED}; font-size: 11px; font-family: {_UI_FONT}; background: transparent;"


def log_color_info_text():
    return "RX -> Ink (#1d1d1f)    TX -> Apple Blue (#007aff)\nINFO -> Blue (#0a84ff)    WARN -> Orange (#ff9f0a)    ERROR -> Red (#ff3b30)"


_DLG_STYLE = f"""
    QDialog {{
        background-color: {_CLR_BG_CARD};
        color: {_CLR_TEXT_BTN_LOG};
    }}
    QLabel {{ color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; }}
    QLabel#qcTitle {{
        color: {_CLR_TEXT_TITLE}; font-size: 15px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;
    }}
    QLabel#dlgSectionTitle {{
        color: {_CLR_TEXT_TITLE}; font-size: 13px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;
        padding-bottom: 2px;
    }}
    QFrame#dlgSep {{ background-color: {_CLR_BORDER}; }}
    QCheckBox {{ color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; spacing: 4px; }}
    QCheckBox::indicator {{
        width: 13px; height: 13px;
        border: 1px solid {_CLR_BORDER}; border-radius: 3px;
        background-color: {_CLR_INPUT_BG};
    }}
    QCheckBox::indicator:hover {{ border-color: {_CLR_BORDER_SOFT}; }}
    QCheckBox::indicator:checked {{
        background-color: #007AFF; border-color: #007AFF;
        image: url({_DLG_CHK_SVG});
    }}
    QSpinBox {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 6px;
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 2px 6px; padding-right: 23px;
    }}
    QSpinBox:hover {{ border-color: rgba(0, 122, 255, 0.38); }}
    QSpinBox:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
    QSpinBox::up-button, QSpinBox::down-button {{
        subcontrol-origin: border;
        width: 18px;
        background-color: rgba(242, 242, 247, 0.92);
        border-left: 1px solid rgba(60, 60, 67, 0.14);
    }}
    QSpinBox::up-button {{
        subcontrol-position: top right;
        border-top-right-radius: 5px;
        border-bottom: 1px solid rgba(60, 60, 67, 0.10);
    }}
    QSpinBox::down-button {{
        subcontrol-position: bottom right;
        border-bottom-right-radius: 5px;
    }}
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
        background-color: #E8F2FF;
    }}
    QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
        background-color: rgba(0, 122, 255, 0.18);
    }}
    QSpinBox::up-arrow {{
        image: url({_SPIN_UP_SVG});
        width: 8px;
        height: 8px;
    }}
    QSpinBox::down-arrow {{
        image: url({_SPIN_DOWN_SVG});
        width: 8px;
        height: 8px;
    }}
    QLineEdit {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 6px;
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 5px 8px; min-height: 24px;
    }}
    QLineEdit:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
    QComboBox {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 6px;
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 3px 8px; min-height: 24px;
    }}
    QComboBox:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
    QComboBox:focus {{ border-color: {_CLR_FILTER_BORDER}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {_CLR_BG_CARD}; color: {_CLR_TEXT_BTN_LOG};
        border: 1px solid {_CLR_BORDER}; selection-background-color: {_CLR_INPUT_BG}; outline: 0;
    }}
    QPushButton#dlgOkBtn {{
        background-color: {_CLR_GREEN_OK}; border: none; border-radius: 6px;
        color: {_CLR_TEXT_WHITE}; font-weight: 700; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 20px;
    }}
    QPushButton#dlgOkBtn:hover {{ background-color: {_CLR_GREEN_OK_HOVER}; }}
    QPushButton#dlgCancelBtn {{
        background-color: transparent; border: 1px solid {_CLR_BORDER}; border-radius: 6px;
        color: {_CLR_TEXT_MUTED}; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 20px;
    }}
    QPushButton#dlgCancelBtn:hover {{ border-color: {_CLR_BORDER_SOFT}; color: {_CLR_TEXT_WHITE}; }}
    QTabWidget::pane {{
        background-color: {_CLR_BG_MAIN};
        border: 1px solid {_CLR_BORDER};
        border-radius: 6px;
        padding: 8px;
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: rgba(242, 242, 247, 0.68);
        color: {_CLR_TEXT_MUTED};
        padding: 7px 17px;
        border: 1px solid rgba(60, 60, 67, 0.12);
        border-bottom-color: {_CLR_BORDER};
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
        font-size: 13px;
        font-family: {_UI_FONT};
        font-weight: 600;
        margin-right: 4px;
    }}
    QTabBar::tab:hover {{
        background-color: rgba(232, 242, 255, 0.88);
        border-color: {_CLR_BORDER_SOFT};
        color: {_CLR_TEXT_BTN_LOG};
    }}
    QTabBar::tab:selected {{
        background-color: {_CLR_BG_CARD};
        color: {_CLR_TEXT_TITLE};
        border: 1px solid {_CLR_BORDER};
        border-bottom-color: {_CLR_BG_CARD};
        border-top: 2px solid #007AFF;
        padding-top: 6px;
    }}
    QTabBar::tab:!selected {{
        margin-top: 3px;
    }}
    QFrame#dlgGroupCard {{
        background: transparent;
        border: none;
        border-bottom: 1px solid {_CLR_BORDER};
    }}
    QLabel#dlgFieldLabel {{
        color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent;
    }}
    QLabel#dlgHint {{
        color: {_CLR_TEXT_MUTED}; font-size: 11px; font-family: {_UI_FONT}; background: transparent;
    }}
    QPushButton#dlgRowBtn {{
        background-color: {_CLR_INPUT_BG};
        color: {_CLR_TEXT_BTN_LOG};
        border: 1px solid {_CLR_BORDER};
        border-radius: 7px;
        font-size: 12px;
        font-family: {_UI_FONT};
        padding: 4px 12px;
        min-height: 20px;
    }}
    QPushButton#dlgRowBtn:hover {{
        background-color: rgba(232, 242, 255, 0.88);
        border-color: {_CLR_BORDER_HOVER};
        color: {_CLR_TEXT_TITLE};
    }}
    QPushButton#dlgRowBtn:pressed {{
        background-color: rgba(0, 122, 255, 0.14);
    }}
    QTableWidget#dlgStepTable {{
        background-color: {_CLR_INPUT_BG};
        color: {_CLR_TEXT_BTN_LOG};
        border: 1px solid {_CLR_BORDER};
        border-radius: 10px;
        gridline-color: transparent;
        font-size: 12px;
        font-family: {_UI_FONT};
        outline: none;
    }}
    QTableWidget#dlgStepTable::item {{
        padding: 3px 6px;
        border: none;
    }}
    QTableWidget#dlgStepTable::item:selected {{
        background-color: rgba(0, 122, 255, 0.16);
        color: {_CLR_TEXT_TITLE};
    }}
    QTableWidget#dlgStepTable QHeaderView::section {{
        background-color: {_CLR_INPUT_BG};
        color: {_CLR_TEXT_MUTED};
        border: none;
        border-bottom: 1px solid {_CLR_BORDER};
        padding: 6px 6px;
        font-size: 11px;
        font-weight: 600;
        font-family: {_UI_FONT};
    }}
    QTableWidget#dlgStepTable QTableCornerButton::section {{
        background-color: {_CLR_INPUT_BG};
        border: none;
    }}
"""


DARK_CARD_STYLE = f"""
    QWidget {{
        background-color: {_CLR_BG_MAIN};
        color: {_CLR_TEXT_BODY};
    }}
    QLabel {{
        background-color: transparent;
        color: {_CLR_TEXT_MUTED};
        border: none;
    }}
    QLabel#statusOk {{
        color: {_CLR_GREEN_OK};
        font-weight: 500;
        background-color: transparent;
    }}
    QLabel#statusWarn {{
        color: {_CLR_WARN_ICON};
        font-weight: 500;
        background-color: transparent;
    }}
    QLabel#statusErr {{
        color: {_CLR_DISCONNECT_TEXT};
        font-weight: 500;
        background-color: transparent;
    }}
    QFrame#cardFrame {{
        background-color: {_CLR_BG_CARD};
        border: 1px solid {_CLR_BORDER_SOFT};
        border-radius: 8px;
    }}
    QComboBox {{
        background-color: {_CLR_INPUT_BG};
        color: {_CLR_INPUT_TEXT};
        border: 1px solid {_CLR_BORDER_SOFT};
        border-radius: 7px;
        padding: 4px 8px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
        background: transparent;
    }}
    QComboBox QAbstractItemView {{
        background-color: {_CLR_BG_CARD};
        color: {_CLR_INPUT_TEXT};
        border: 1px solid {_CLR_BORDER};
        selection-background-color: {_CLR_SELECTION_BG};
        selection-color: {_CLR_SELECTION_TEXT};
    }}
"""

APPLE_CARD_STYLE = DARK_CARD_STYLE


_ICONS_DIR = os.path.join(get_resource_base(), "resources", "icons")
_ARROW_UP = os.path.join(_ICONS_DIR, "scrollbar-arrow-up.svg").replace("\\", "/")
_ARROW_DOWN = os.path.join(_ICONS_DIR, "scrollbar-arrow-down.svg").replace("\\", "/")
_ARROW_LEFT = os.path.join(_ICONS_DIR, "scrollbar-arrow-left.svg").replace("\\", "/")
_ARROW_RIGHT = os.path.join(_ICONS_DIR, "scrollbar-arrow-right.svg").replace("\\", "/")

SERIAL_SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        background: {_CLR_BG_MAIN};
        width: 10px;
        margin: 14px 0px 14px 0px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {_CLR_SCROLLBAR};
        min-height: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {_CLR_SCROLLBAR_HV};
    }}
    QScrollBar::sub-line:vertical {{
        height: 14px;
        subcontrol-position: top;
        subcontrol-origin: margin;
        background: {_CLR_BG_CARD};
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
    }}
    QScrollBar::sub-line:vertical:hover {{
        background: {_CLR_BORDER};
    }}
    QScrollBar::add-line:vertical {{
        height: 14px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
        background: {_CLR_BG_CARD};
        border-bottom-left-radius: 5px;
        border-bottom-right-radius: 5px;
    }}
    QScrollBar::add-line:vertical:hover {{
        background: {_CLR_BORDER};
    }}
    QScrollBar::up-arrow:vertical {{
        image: url("{_ARROW_UP}");
        width: 8px;
        height: 8px;
    }}
    QScrollBar::down-arrow:vertical {{
        image: url("{_ARROW_DOWN}");
        width: 8px;
        height: 8px;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: {_CLR_BG_MAIN};
        height: 10px;
        margin: 0px 14px 0px 14px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: {_CLR_SCROLLBAR};
        min-width: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {_CLR_SCROLLBAR_HV};
    }}
    QScrollBar::sub-line:horizontal {{
        width: 14px;
        subcontrol-position: left;
        subcontrol-origin: margin;
        background: {_CLR_BG_CARD};
        border-top-left-radius: 5px;
        border-bottom-left-radius: 5px;
    }}
    QScrollBar::sub-line:horizontal:hover {{
        background: {_CLR_BORDER};
    }}
    QScrollBar::add-line:horizontal {{
        width: 14px;
        subcontrol-position: right;
        subcontrol-origin: margin;
        background: {_CLR_BG_CARD};
        border-top-right-radius: 5px;
        border-bottom-right-radius: 5px;
    }}
    QScrollBar::add-line:horizontal:hover {{
        background: {_CLR_BORDER};
    }}
    QScrollBar::left-arrow:horizontal {{
        image: url("{_ARROW_LEFT}");
        width: 8px;
        height: 8px;
    }}
    QScrollBar::right-arrow:horizontal {{
        image: url("{_ARROW_RIGHT}");
        width: 8px;
        height: 8px;
    }}
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
"""


class _SerialComboItemDelegate(QStyledItemDelegate):
    def __init__(self, padding_v=4, parent=None):
        super().__init__(parent)
        self._padding_v = padding_v

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        min_h = option.fontMetrics.height() + self._padding_v * 2
        if size.height() < min_h:
            size.setHeight(min_h)
        return size


class SerialDarkComboBox(QComboBox):
    _ITEM_PADDING_V = 4

    def __init__(self, *args, bg=_CLR_INPUT_BG, border=_CLR_BORDER_SOFT, arrow_color="#6E6E73",
                 hover_color="#E8F2FF", **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_bg = bg
        self._popup_border = border
        self._arrow_color = arrow_color
        self._hover_color = hover_color
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        self.setMinimumWidth(0)
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 7px;
                padding: 4px 28px 4px 10px;
                color: {_CLR_INPUT_TEXT};
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QLineEdit {{
                background-color: transparent;
                border: none;
                color: {_CLR_INPUT_TEXT};
                font-size: 13px;
                padding: 0px;
                margin: 0px;
            }}
            QComboBox QLineEdit:disabled {{
                color: {_CLR_DISABLED};
            }}
        """)
        self._setup_view(bg, border, hover_color)
        self.setMaxVisibleItems(30)

    def _setup_view(self, bg, border, hover_color):
        list_view = QListView()
        list_view.setMouseTracking(True)
        list_view.setUniformItemSizes(True)
        list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        delegate = _SerialComboItemDelegate(
            padding_v=self._ITEM_PADDING_V, parent=list_view
        )
        list_view.setItemDelegate(delegate)
        palette = list_view.palette()
        palette.setColor(QPalette.Highlight, QColor(hover_color))
        palette.setColor(QPalette.HighlightedText, QColor(_CLR_BLUE))
        list_view.setPalette(palette)
        list_view.setStyleSheet(f"""
            QListView {{
                background-color: {bg};
                color: {_CLR_INPUT_TEXT};
                border: 1px solid {border};
                outline: 0;
            }}
            QListView::item {{
                padding: {self._ITEM_PADDING_V}px 10px;
                border: none;
            }}
            QListView::item:hover {{
                background-color: {hover_color};
                color: {_CLR_BLUE};
            }}
            QListView::item:selected {{
                background-color: {hover_color};
                color: {_CLR_BLUE};
                border: none;
                outline: none;
            }}
        """)
        self.setView(list_view)

    def _hide_popup_scrollers(self):
        popup = self.view().window()
        if not popup:
            return
        for child in popup.children():
            cls_name = child.metaObject().className()
            if "Scroller" in cls_name or "QComboBoxPrivateScroller" in cls_name:
                child.hide()
                child.setMaximumHeight(0)
                child.setMaximumWidth(0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        bg = QColor(self._popup_bg)
        bd = QColor(self._popup_border)
        if not self.isEnabled():
            bg = bg.darker(130)
            bd = bd.darker(130)
        painter.setPen(QPen(bd, 1.0))
        painter.setBrush(bg)
        painter.drawRoundedRect(r, 6, 6)

        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        if not self.isEditable():
            text_rect = QRect(10, 0, max(0, self.width() - 36), self.height())
            fm = QFontMetrics(self.font())
            elided = fm.elidedText(self.currentText(), Qt.ElideMiddle, text_rect.width())
            painter.setPen(QColor(_CLR_INPUT_TEXT) if self.isEnabled() else QColor(_CLR_DISABLED))
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        arrow_rect: QRect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

        color = QColor(self._arrow_color)
        if not self.isEnabled():
            color = QColor(_CLR_DISABLED)
        pen = QPen(color, 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        cx = arrow_rect.center().x()
        cy = arrow_rect.center().y()
        half_w = 4
        half_h = 3

        painter.drawLine(cx - half_w, cy - half_h, cx, cy + half_h)
        painter.drawLine(cx, cy + half_h, cx + half_w, cy - half_h)

        painter.end()

    def showPopup(self):
        view = self.view()
        fm = self.fontMetrics()
        max_w = self.width()
        for i in range(self.count()):
            w = fm.horizontalAdvance(self.itemText(i)) + 40
            if w > max_w:
                max_w = w
        view.setMinimumWidth(max_w)
        visible = min(self.count(), self.maxVisibleItems())
        if visible > 0:
            needs_scroll = self.count() > self.maxVisibleItems()
            view.setVerticalScrollBarPolicy(
                Qt.ScrollBarAsNeeded if needs_scroll else Qt.ScrollBarAlwaysOff
            )
            row_h = view.sizeHintForRow(0)
            if row_h <= 0:
                row_h = fm.height() + self._ITEM_PADDING_V * 2
            popup_h = visible * row_h + view.frameWidth() * 2 + 2
            view.setMinimumHeight(popup_h)
            view.setMaximumHeight(popup_h if not needs_scroll else 16777215)
        super().showPopup()
        popup = view.window()
        if popup:
            popup.setStyleSheet(
                f"background-color: {self._popup_bg}; "
                f"border: 1px solid {self._popup_border}; "
                f"padding: 0px; margin: 0px;"
            )
            if self.count() <= self.maxVisibleItems():
                self._hide_popup_scrollers()
                QTimer.singleShot(0, self._hide_popup_scrollers)


SerialAppleComboBox = SerialDarkComboBox


class SerialHistoryComboBox(SerialDarkComboBox):
    def __init__(self, *args, field_bg=_HISTORY_COMBO_FIELD_QCOLOR, popup_bg=_CLR_INPUT_BG,
                 border=_CLR_BORDER_SOFT, **kwargs):
        super().__init__(*args, bg=popup_bg, border=border, **kwargs)
        self._field_bg = QColor(field_bg)
        self.setStyleSheet(history_combo_style())

    def paintEvent(self, event):
        original_popup_bg = self._popup_bg
        self._popup_bg = self._field_bg
        try:
            super().paintEvent(event)
        finally:
            self._popup_bg = original_popup_bg


__all__ = [name for name in globals() if name.startswith("_CLR_")]
__all__ += [
    name for name, value in globals().items()
    if callable(value) and not name.startswith("__")
]
__all__ += [
    "_SERIAL_BTN_HEIGHT", "_SERIAL_BTN_ICON_SIZE", "_SERIAL_BTN_RADIUS",
    "_TERM_FONT", "_UI_FONT", "_DLG_STYLE", "DARK_CARD_STYLE",
    "APPLE_CARD_STYLE", "SERIAL_SCROLLBAR_STYLE", "SerialDarkComboBox",
    "SerialAppleComboBox", "SerialHistoryComboBox", "_CLR_HISTORY_COMBO_BG",
]
