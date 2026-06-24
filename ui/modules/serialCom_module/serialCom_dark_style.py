import os

from PySide6.QtWidgets import (
    QComboBox, QStyle, QStyleOptionComboBox, QListView, QStyledItemDelegate
)
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFontMetrics, QPalette

from ui.resource_path import get_resource_base


from ui.styles.serial_tokens import (
    DARK_TOKENS as _T,
    SERIAL_BTN_HEIGHT,
    SERIAL_BTN_ICON_SIZE,
    TERM_FONT,
    UI_FONT,
    dlg_check_svg,
)

_SERIAL_BTN_HEIGHT = SERIAL_BTN_HEIGHT
_SERIAL_BTN_ICON_SIZE = SERIAL_BTN_ICON_SIZE
_SERIAL_BTN_RADIUS = _T.btn_radius
_TERM_FONT = TERM_FONT
_UI_FONT = UI_FONT

_CLR_BG_MAIN = _T.bg_main
_CLR_BG_PANEL = _T.bg_panel
_CLR_BG_CARD = _T.bg_card
_CLR_BG_LOG = _T.bg_log
_CLR_BORDER = _T.border
_CLR_BORDER_HOVER = _T.border_hover
_CLR_TEXT_TITLE = _T.text_title
_CLR_TEXT_ACCENT = _T.text_accent
_CLR_TEXT_SUBTITLE = _T.text_subtitle
_CLR_TEXT_LABEL = _T.text_label
_CLR_TEXT_BTN = _T.text_btn
_CLR_TEXT_BTN_LOG = _T.text_btn_log
_CLR_TEXT_BODY = _T.text_body
_CLR_TEXT_TIME = _T.text_time
_CLR_TEXT_LINENO = _T.text_lineno
_CLR_TEXT_INFO = _T.text_info
_CLR_INPUT_BG = _T.input_bg
_CLR_INPUT_TEXT = _T.input_text
_CLR_CURSOR = _T.cursor
_CLR_SELECTION_BG = _T.selection_bg
_CLR_SELECTION_TEXT = _T.selection_text
_CLR_SCROLLBAR = _T.scrollbar
_CLR_SCROLLBAR_HV = _T.scrollbar_hv
_CLR_CONNECT_FG = _T.connect_fg
_CLR_CONNECT_BG = _T.connect_bg
_CLR_SEND_BG = _T.send_bg
_CLR_SEND_HOVER = _T.send_hover
_CLR_SEND_PRESS = _T.send_press
_CLR_WARNING = _T.warning
_CLR_ERROR = _T.error
_CLR_RX = _T.rx
_CLR_TX = _T.tx
_CLR_FILTER_TEXT = _T.filter_text
_CLR_FILTER_BG = _T.filter_bg
_CLR_FILTER_BORDER = _T.filter_border
_CLR_TOGGLE_ON = _T.toggle_on

_CLR_TEXT_MUTED = _T.text_muted
_CLR_TEXT_WHITE = _T.text_white
_CLR_TEXT_SOFT = _T.text_soft
_CLR_TEXT_TAB = _T.text_tab
_CLR_DISABLED = _T.disabled
_CLR_BORDER_SOFT = _T.border_soft
_CLR_BORDER_ACTIVE = _T.border_active
_CLR_BLUE = _T.blue
_CLR_BLUE_HOVER = _T.blue_hover
_CLR_BLUE_PRESS = _T.blue_press
_CLR_BLUE_LIGHT = _T.blue_light
_CLR_GREEN_OK = _T.green_ok
_CLR_GREEN_OK_HOVER = _T.green_ok_hover
_CLR_ROSE_ICON = _T.rose_icon
_CLR_WARN_ICON = _T.warn_icon
_CLR_CONNECT_TEXT = _T.connect_text
_CLR_CONNECT_HOVER = _T.connect_hover
_CLR_CONNECT_PRESS = _T.connect_press
_CLR_DISCONNECT_BG = _T.disconnect_bg
_CLR_DISCONNECT_HOVER = _T.disconnect_hover
_CLR_DISCONNECT_PRESS = _T.disconnect_press
_CLR_DISCONNECT_TEXT = _T.disconnect_text

_DLG_CHK_SVG = dlg_check_svg()


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
            background-color: #1E293B;
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
            border: 1px solid rgba(16, 185, 129, 0.20);
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
            background-color: #0B1220;
            color: {_CLR_DISABLED};
            border: 1px solid #1A2436;
        }}
    """


def _serial_disconnect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: {_CLR_DISCONNECT_BG};
            border: 1px solid rgba(244, 63, 94, 0.20);
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
            background-color: #0B1220;
            color: {_CLR_DISABLED};
            border: 1px solid #1A2436;
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
            QSplitter::handle:hover {{ background-color: #1E293B; }}
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
    return f"QFrame#scCenterWidget {{ background-color: {_CLR_BG_CARD}; border: 1px solid {_CLR_BORDER}; border-radius: 8px; }}"


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
                    min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                    background-color: {_CLR_DISCONNECT_BG}; color: {_CLR_DISCONNECT_TEXT}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 700; border: 1px solid rgba(244, 63, 94, 0.20);
                }}
                QPushButton:hover {{ background-color: {_CLR_DISCONNECT_HOVER}; }}
                QPushButton:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
                QPushButton:pressed {{ background-color: {_CLR_DISCONNECT_PRESS}; }}
            """
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                background-color: {_CLR_CONNECT_BG}; color: {_CLR_CONNECT_TEXT}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.20);
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
                font-family: {_UI_FONT}; font-weight: 700; border: 1px solid rgba(16, 185, 129, 0.20);
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
            QPushButton:hover {{ background-color: {_CLR_BORDER_SOFT}; border: none; }}
            QPushButton:focus {{ background-color: transparent; border: none; }}
            QPushButton:hover:focus {{ background-color: {_CLR_BORDER_SOFT}; border: none; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; border: none; }}{disabled_qss}
        """


def separator_style(transparent=False):
    suffix = " background: transparent;" if transparent else ""
    return f"color: {_CLR_BORDER};{suffix}"


def sidebar_wrapper_style():
    return f"""
            QFrame#scSidebarWrapper {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_BORDER};
                border-radius: 8px;
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


def compact_spinbox_style(up_button_width=10, padding="1px 2px"):
    return f"""
            QSpinBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 4px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: {padding};
            }}
            QSpinBox:focus {{ border: 1px solid {_CLR_CONNECT_FG}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: {up_button_width}px; }}
            QSpinBox:disabled {{
                background-color: #0B1220; color: #475569; border-color: #1A2436;
            }}
            QSpinBox::up-button:disabled, QSpinBox::down-button:disabled {{
                background-color: #0E1626;
            }}
            QSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled {{
                image: none;
            }}
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
                border-radius: 6px;
            }}
        """


def transparent_background_style():
    return "background: transparent;"


def log_title_style():
    return f"color: {_CLR_TEXT_WHITE}; font-size: 14px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;"


def log_title_icon_color():
    return _CLR_TEXT_WHITE


def log_toolbar_button_style(checked_variant=False, max_height=28, padding="5px 11px", radius=7):
    checked_qss = ""
    if checked_variant:
        checked_qss = f"""
            QPushButton:checked {{
                background-color: #172554; color: #60A5FA; border: 1px solid #1E3A8A;
                font-weight: 600;
            }}
            QPushButton:checked:hover {{
                background-color: #1E3A8A; color: #93C5FD; border: 1px solid #2563EB;
            }}
            QPushButton:checked:pressed {{
                background-color: #172554; color: #60A5FA; border: 1px solid #2563EB;
            }}
        """
    else:
        checked_qss = f"""
            QPushButton:checked {{ background-color: {_CLR_BORDER}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BORDER_HOVER}; }}
            QPushButton:checked:hover {{ background-color: #334155; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
            QPushButton:checked:pressed {{ background-color: {_CLR_BG_PANEL}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
        """
    return f"""
                QPushButton {{
                    min-height: 0px; max-height: {max_height}px; padding: {padding}; border-radius: {radius}px;
                    background-color: #0F172A; color: {_CLR_TEXT_BTN_LOG}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 500; border: 1px solid {_CLR_BORDER_SOFT};
                }}
                QPushButton:focus {{ outline: none; }}
                QPushButton:hover {{ background-color: {_CLR_BORDER}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BORDER_HOVER}; }}
                QPushButton:pressed {{ background-color: {_CLR_BG_PANEL}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
                {checked_qss}
            """


def log_icon_button_style(checked_variant="none", padding="7px"):
    if checked_variant == "blue":
        checked_qss = f"""
            QPushButton:checked {{ background-color: #172554; color: {_CLR_BLUE_HOVER}; border: none; }}
            QPushButton:checked:hover {{ background-color: #1E3A8A; color: {_CLR_BLUE_HOVER}; border: none; }}
            QPushButton:checked:pressed {{ background-color: #1E40AF; color: {_CLR_BLUE_HOVER}; border: none; }}
        """
    elif checked_variant == "green":
        checked_qss = f"""
            QPushButton:checked {{ background-color: #10291F; color: #34D399; border: none; }}
            QPushButton:checked:hover {{ background-color: #15311F; color: #6EE7B7; border: none; }}
            QPushButton:checked:pressed {{ background-color: #0E2618; color: #10B981; border: none; }}
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
                QPushButton:hover {{ background-color: {_CLR_BORDER_SOFT}; color: {_CLR_TEXT_WHITE}; border: none; }}
                QPushButton:pressed {{ background-color: {_CLR_BORDER}; color: {_CLR_TEXT_WHITE}; border: none; }}
                {checked_qss}
            """


def filter_input_style():
    return f"""
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 5px;
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
                    background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid {_CLR_BORDER};
                    color: {_CLR_TEXT_BODY}; font-family: {family}; font-size: {font_size}px; font-weight: 400;
                    padding: {padding};{line_height}
                    selection-background-color: {_CLR_SELECTION_BG};
                    selection-color: {_CLR_SELECTION_TEXT};
                }}
            """


def log_document_style():
    return "p, div { line-height: 150%; margin: 0; padding: 0; }"


def transparent_toolbar_button_style():
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: none;
            }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:hover {{ border: 1px solid {_CLR_BORDER_SOFT}; color: {_CLR_TEXT_WHITE}; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; }}
            QPushButton:checked {{ background-color: #172554; color: #60A5FA; border: 1px solid #1E3A8A; font-weight: 600; }}
            QPushButton:checked:hover {{ background-color: #1E3A8A; color: #93C5FD; border: 1px solid #2563EB; }}
            QPushButton:checked:pressed {{ background-color: #172554; color: #60A5FA; border: 1px solid #2563EB; }}
        """


def sidebar_toggle_button_style():
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: none;
            }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:hover {{ color: {_CLR_TEXT_WHITE}; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; }}
            QPushButton:checked {{ background-color: #172554; color: #60A5FA; border: none; font-weight: 600; }}
            QPushButton:checked:hover {{ background-color: #1E3A8A; color: #93C5FD; border: none; }}
            QPushButton:checked:pressed {{ background-color: #172554; color: #60A5FA; border: none; }}
        """


def auto_scroll_button_style(padding="5px 11px"):
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; padding: {padding}; border-radius: 7px;
                background-color: #0F172A; color: {_CLR_TEXT_BTN_LOG}; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: 1px solid {_CLR_BORDER_SOFT};
            }}
            QPushButton:focus {{ outline: none; }}
            QPushButton:hover {{ background-color: {_CLR_BORDER}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BORDER_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_PANEL}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
            QPushButton:checked {{ background-color: #172554; color: #60A5FA; border: none; font-weight: 600; }}
            QPushButton:checked:hover {{ background-color: #1E3A8A; color: #93C5FD; border: none; }}
            QPushButton:checked:pressed {{ background-color: #172554; color: #60A5FA; border: none; }}
        """


def sidebar_toggle_icon_colors():
    return {"normal": _CLR_TEXT_MUTED, "checked": "#60A5FA"}


def auto_scroll_icon_colors():
    return {"normal": _CLR_TEXT_BTN_LOG, "checked": "#60A5FA"}


def send_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_SEND_BG}; border: none; border-radius: 6px;
                color: {_CLR_TEXT_WHITE}; font-weight: 700; font-size: 13px;
                font-family: {_UI_FONT}; padding: 3px 20px;
            }}
            QPushButton:hover {{ background-color: {_CLR_SEND_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_SEND_PRESS}; }}
            QPushButton:disabled {{ background-color: #0B1220; color: {_CLR_DISABLED}; border: 1px solid #1A2436; }}
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
                color: {_CLR_TEXT_ACCENT};
                font-weight: 600;
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
                background-color: #0F172A;
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
                background-color: #0F172A;
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER_SOFT};
                border-radius: 5px;
                padding: 4px 8px;
                min-height: 17px;
                min-width: 34px;
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton:hover {{
                background-color: #334155;
                border-color: {_CLR_BORDER_ACTIVE};
                color: {_CLR_TEXT_WHITE};
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
                border-radius: 8px;
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
                color: {_CLR_TEXT_BTN_LOG};
            }}
            QTabWidget#scBottomTabs QTabBar::tab:selected {{
                color: {_CLR_TEXT_TITLE};
                border-bottom: 2px solid {_CLR_TEXT_ACCENT};
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
                background-color: {_CLR_BORDER_SOFT};
                color: {_CLR_TEXT_TAB};
                border-color: transparent;
            }}
            QTabBar::tab:selected {{
                background-color: #172554;
                color: {_CLR_BLUE_HOVER};
                border: 1px solid transparent;
                font-weight: 700;
            }}
            QTabBar::tab:selected:hover {{
                background-color: #172554;
                color: {_CLR_BLUE_HOVER};
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


def quick_group_combo_bg_style():
    return ""


def quick_combo_style():
    return f"""
            QComboBox {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_SOFT};
                border: 1px solid #1E293B;
                border-radius: 5px;
                padding: 2px 6px;
                min-height: 18px;
                font-size: 11px;
                font-family: {_UI_FONT};
                min-width: 63px;
            }}
            QComboBox:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
            QComboBox:focus {{ border-color: {_CLR_CONNECT_FG}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_SOFT};
                border: 1px solid {_CLR_BORDER};
                selection-background-color: {_CLR_BORDER};
                selection-color: {_CLR_TEXT_WHITE};
                outline: 0;
            }}
        """


def quick_toolbar_button_style(max_height=None, padding="3px 8px", radius=5, min_height=18):
    max_height_qss = f" max-height: {max_height}px;" if max_height is not None else ""
    return f"""
            QPushButton {{
                min-height: {min_height}px;{max_height_qss}
                background-color: #0F172A;
                color: {_CLR_TEXT_SOFT};
                border: 1px solid #1E293B;
                border-radius: {radius}px;
                padding: {padding};
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {_CLR_BORDER_SOFT};
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_TEXT_WHITE};
            }}
            QPushButton:focus {{
                background-color: #0F172A;
                color: {_CLR_TEXT_SOFT};
                border: 1px solid #1E293B;
            }}
            QPushButton:hover:focus {{
                background-color: {_CLR_BORDER_SOFT};
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_TEXT_WHITE};
            }}
            QPushButton:pressed {{
                background-color: {_CLR_BORDER_HOVER};
                border-color: {_CLR_DISABLED};
            }}
            QPushButton:checked {{
                background-color: {_CLR_BORDER_SOFT};
                color: {_CLR_TEXT_WHITE};
                border: 1px solid {_CLR_BORDER_HOVER};
            }}
            QPushButton:disabled {{
                background-color: #0F172A;
                color: {_CLR_DISABLED};
                border-color: {_CLR_BORDER};
            }}
        """


def quick_group_button_style():
    return f"""
            QPushButton {{
                min-height: 18px;
                background-color: #0F172A;
                color: {_CLR_BLUE};
                border: 1px solid #1E293B;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {_CLR_BORDER_SOFT};
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_BLUE_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {_CLR_BORDER_HOVER};
                border-color: {_CLR_DISABLED};
            }}
            QPushButton:disabled {{
                background-color: #0F172A;
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
                background-color: #0B1220;
                color: {_CLR_DISABLED};
                border: 1px solid #1A2436;
            }}
        """


def script_stop_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_ERROR};
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
                background-color: #FF6961;
            }}
            QPushButton:pressed {{
                background-color: #E0352B;
            }}
            QPushButton:disabled {{
                background-color: #0B1220;
                color: {_CLR_DISABLED};
                border: 1px solid #1A2436;
            }}
        """


def script_add_step_button_style():
    return f"""
            QPushButton#scAddStepBtn {{
                background-color: #0F172A;
                color: {_CLR_TEXT_MUTED};
                border: 1px dashed {_CLR_BORDER};
                border-radius: 10px;
                padding: 7px 12px;
                font-size: 12px;
                font-family: {_UI_FONT};
                font-weight: 700;
            }}
            QPushButton#scAddStepBtn:hover {{
                background-color: #172554;
                color: {_CLR_SEND_BG};
                border: 1px dashed {_CLR_SEND_BG};
            }}
            QPushButton#scAddStepBtn:pressed {{
                background-color: #1E3A8A;
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
                background-color: {_CLR_BG_CARD};
                border-top: 1px solid {_CLR_BORDER};
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }}
            QLabel {{ font-size: 11px; font-family: {_TERM_FONT}; background: transparent; }}
        """


def status_label_style(kind="muted", include_font=False, compact=False):
    colors = {
        "ok": "#34D399",
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
                border: 1px solid {_CLR_BORDER};
                border-radius: 12px;
            }}
        """


def section_card_shadow():
    return {
        "blur_radius": 14,
        "offset_x": 0,
        "offset_y": 2,
        "color": (0, 0, 0, 90),
    }


def section_title_style():
    return (
        f"color: {_CLR_TEXT_MUTED}; font-size: 11px; font-weight: 700; font-family: {_UI_FONT};"
        f" letter-spacing: 0.6px; background: transparent; border: none;"
    )


def section_header_divider_style():
    return f"background-color: {_CLR_BORDER}; border: none;"


def panel_divider_style():
    return "background-color: rgba(148, 163, 184, 0.10); border: none;"


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
        f"QCheckBox:disabled {{ color: #475569; }}"
        f"QCheckBox::indicator:disabled {{"
        f"  background-color: #0B1220; border-color: #1A2436;"
        f"}}"
        f"QCheckBox::indicator:checked:disabled {{"
        f"  background-color: #334155; border-color: #334155;"
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
                background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 5px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: {size}px; font-family: {_UI_FONT}; padding: {padding}; min-height: {min_height}px;
            }}
            QLineEdit:focus {{ border: 1px solid {_CLR_CONNECT_FG}; }}
        """


def quick_preview_popup_shadow():
    return {
        "blur_radius": 18,
        "offset_x": 0,
        "offset_y": 5,
        "color": (0, 0, 0, 145),
    }


def quick_preview_popup_style():
    return f"""
            QFrame#quickCmdPreviewPopupWindow {{
                background-color: transparent;
                border: none;
            }}
            QFrame#quickCmdPreviewPopup {{
                background-color: #0F172A;
                border: 1px solid #1E293B;
                border-radius: 9px;
            }}
            QLabel#quickCmdPreviewBadge {{
                color: {_CLR_INPUT_BG};
                background-color: {_CLR_TEXT_ACCENT};
                border-radius: 4px;
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
                background-color: #020617;
                border: 1px solid #1E293B;
                border-radius: 6px;
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
                    background-color: #0F172A;
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
                    background-color: #334155;
                    border-color: {_CLR_BORDER_HOVER};
                    color: {_CLR_BLUE_HOVER};
                }}
                QPushButton:focus {{
                    background-color: #334155;
                    border-color: {_CLR_BORDER_HOVER};
                    color: {_CLR_BLUE_HOVER};
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
                background-color: #3F3F46;
            }}
            QToolButton#quickCmdAction:disabled {{
                background-color: transparent;
            }}
        """


def quick_action_overlay_container_style():
    return f"""
            QFrame#quickCmdActionBar {{
                background-color: rgba(24, 24, 27, 0.94);
                border: 1px solid {_CLR_BORDER_HOVER};
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
                background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 8px;
                color: {_CLR_TEXT_BODY}; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 10px; min-height: 26px;
            }}
            QLineEdit:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
            QLineEdit:focus {{ border: 1px solid {_CLR_BORDER_ACTIVE}; }}
            QComboBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 8px;
                color: {_CLR_TEXT_BODY}; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 10px; min-height: 26px;
            }}
            QComboBox:hover {{ border-color: {_CLR_BORDER_HOVER}; }}
            QComboBox:focus {{ border: 1px solid {_CLR_BORDER_ACTIVE}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox QAbstractItemView {{
                background-color: {_CLR_BG_CARD}; color: {_CLR_TEXT_BODY};
                border: 1px solid {_CLR_BORDER}; border-radius: 8px; padding: 4px;
                selection-background-color: {_CLR_BORDER}; selection-color: {_CLR_TEXT_BODY};
                outline: 0;
            }}
            QCheckBox {{
                color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px; border: 1px solid {_CLR_BORDER}; border-radius: 4px;
                background-color: {_CLR_INPUT_BG};
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
            QPushButton:hover {{ background-color: {_CLR_BORDER}; border-color: {_CLR_BORDER_HOVER}; color: {_CLR_TEXT_WHITE}; }}
            QPushButton:pressed {{ background-color: {_CLR_BORDER_HOVER}; }}
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
    return "RX: White (#E5E5EA)    TX: Blue (#409EFF)\nINFO: Blue (#409EFF)    WARN: Amber (#FF9F0A)    ERROR: Red (#FF453A)"


def dialog_backdrop_style():
    return "QWidget#scEditorBackdrop { background-color: rgba(2, 6, 23, 110); }"


def frameless_chrome_style(dialog_id="scChromeDialog"):
    return f"""
            QDialog#{dialog_id} {{ background: transparent; }}
            QFrame#scEditorContainer {{
                background-color: {_CLR_BG_MAIN};
                border: 1px solid {_CLR_BORDER};
                border-radius: 14px;
            }}
            QFrame#scChromeBody {{
                background-color: {_CLR_BG_MAIN};
                border-bottom-left-radius: 13px;
                border-bottom-right-radius: 13px;
            }}
            QFrame#scEditorHeader {{
                background-color: {_CLR_BG_CARD};
                border-bottom: 1px solid {_CLR_BORDER};
                border-top-left-radius: 13px;
                border-top-right-radius: 13px;
            }}
            QLabel#scEditorTitle {{
                color: {_CLR_TEXT_TITLE}; font-size: 14px; font-weight: 700;
                font-family: {_UI_FONT}; letter-spacing: 0.6px; background: transparent;
            }}
            QPushButton#scEditorClose {{
                background: transparent; border: none; border-radius: 6px;
                color: {_CLR_TEXT_MUTED}; font-size: 15px; font-family: {_UI_FONT};
            }}
            QPushButton#scEditorClose:hover {{
                background-color: {_CLR_INPUT_BG}; color: {_CLR_TEXT_TITLE};
            }}
        """


def script_editor_dialog_style():
    return frameless_chrome_style("scEditorDialog") + f"""
            QFrame#scEditorCard {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_BORDER};
                border-radius: 12px;
            }}
            QLabel#scEditorFieldLabel {{
                color: {_CLR_TEXT_MUTED}; font-size: 11px; font-weight: 700;
                font-family: {_UI_FONT}; letter-spacing: 0.5px; background: transparent;
            }}
            QLabel#scEditorInlineLabel {{
                color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT};
                background: transparent;
            }}
            QLabel#scEditorSectionTitle {{
                color: {_CLR_TEXT_TITLE}; font-size: 14px; font-weight: 700;
                font-family: {_UI_FONT}; background: transparent;
            }}
            QPushButton#scEditorAddBtn {{
                background-color: rgba(0, 122, 255, 0.10);
                border: none; border-radius: 8px;
                color: {_CLR_SEND_BG}; font-size: 12px; font-weight: 700;
                font-family: {_UI_FONT}; padding: 7px 14px;
            }}
            QPushButton#scEditorAddBtn:hover {{
                background-color: rgba(0, 122, 255, 0.18);
            }}
            QFrame#scEditorFooter {{
                background-color: {_CLR_BG_MAIN};
                border-top: 1px solid {_CLR_BORDER};
                border-bottom-left-radius: 13px;
                border-bottom-right-radius: 13px;
            }}
            QPushButton#scEditorCancelBtn {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_BORDER}; border-radius: 8px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: 13px; font-weight: 600;
                font-family: {_UI_FONT}; padding: 8px 22px;
            }}
            QPushButton#scEditorCancelBtn:hover {{
                background-color: {_CLR_INPUT_BG}; border-color: {_CLR_BORDER_SOFT};
            }}
            QPushButton#scEditorSaveBtn {{
                background-color: {_CLR_SEND_BG};
                border: none; border-radius: 8px;
                color: #FFFFFF; font-size: 13px; font-weight: 700;
                font-family: {_UI_FONT}; padding: 8px 22px;
            }}
            QPushButton#scEditorSaveBtn:hover {{
                background-color: #0A6FE0;
            }}
            QPushButton#scEditorRowIcon {{
                background: transparent; border: none; border-radius: 6px;
            }}
            QPushButton#scEditorRowIcon:hover {{
                background-color: {_CLR_INPUT_BG};
            }}
            QPushButton#scEditorRowIcon:disabled {{
                background: transparent;
            }}
            QLabel#scEditorRowIndex {{
                color: {_CLR_TEXT_MUTED}; font-size: 13px; font-weight: 600;
                font-family: {_UI_FONT}; background: transparent;
            }}
            QTableWidget#dlgStepTable {{
                background-color: #0B1220;
            }}
            QTableWidget#dlgStepTable::item:selected {{
                background-color: transparent;
                color: {_CLR_TEXT_BTN_LOG};
            }}
            QTableWidget#dlgStepTable::item:hover {{
                background-color: #152135;
            }}
            QTableWidget#dlgStepTable QHeaderView::section {{
                background-color: #111c30;
                color: {_CLR_TEXT_MUTED};
                border: none;
                border-bottom: 1px solid {_CLR_BORDER};
                padding: 6px 6px;
                font-size: 11px;
                font-weight: 600;
                font-family: {_UI_FONT};
            }}
            QTableWidget#dlgStepTable QLineEdit {{
                background-color: {_CLR_INPUT_BG};
                border: 1px solid {_CLR_BORDER}; border-radius: 7px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: 13px; font-family: {_TERM_FONT};
                padding: 5px 8px; min-height: 26px;
            }}
            QTableWidget#dlgStepTable QLineEdit:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
            QTableWidget#dlgStepTable QSpinBox {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_BTN_LOG}; font-family: {_TERM_FONT};
            }}
            QFrame#scEditorCard QLineEdit {{
                background-color: {_CLR_INPUT_BG}; font-family: {_UI_FONT};
            }}
            QFrame#scEditorCard QComboBox {{
                background-color: {_CLR_INPUT_BG}; font-family: {_UI_FONT};
            }}
            QFrame#scEditorCard QSpinBox {{
                background-color: {_CLR_INPUT_BG}; font-family: {_UI_FONT};
            }}
            QFrame#scEditorCard QSpinBox:disabled {{
                background-color: #0B1220; color: #475569;
                border-color: #1A2436;
            }}
            QFrame#scEditorCard QSpinBox::up-button:disabled,
            QFrame#scEditorCard QSpinBox::down-button:disabled {{
                background-color: #0E1626;
                border-left-color: #1A2436;
                border-bottom-color: #1A2436;
            }}
            QFrame#scEditorCard QSpinBox::up-arrow:disabled,
            QFrame#scEditorCard QSpinBox::down-arrow:disabled {{
                image: none;
            }}
            QFrame#scEditorCard QCheckBox {{
                font-family: {_UI_FONT};
            }}
            QFrame#scEditorCard QCheckBox:disabled {{
                color: #475569;
            }}
            QFrame#scEditorCard QCheckBox::indicator {{
                background-color: {_CLR_INPUT_BG};
            }}
            QFrame#scEditorCard QCheckBox::indicator:disabled {{
                background-color: #0B1220;
                border-color: #1A2436;
            }}
            QFrame#scEditorCard QCheckBox::indicator:checked:disabled {{
                background-color: #334155;
                border-color: #334155;
            }}
        """


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
        background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 4px;
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 2px 6px;
    }}
    QSpinBox:focus {{ border: 1px solid {_CLR_CONNECT_FG}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 12px; }}
    QLineEdit {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 4px;
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 5px 8px; min-height: 24px;
    }}
    QLineEdit:focus {{ border: 1px solid {_CLR_CONNECT_FG}; }}
    QComboBox {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid #1E293B; border-radius: 4px;
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 3px 8px; min-height: 24px;
    }}
    QComboBox:hover {{ border-color: {_CLR_BORDER_SOFT}; }}
    QComboBox:focus {{ border-color: {_CLR_CONNECT_FG}; }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QComboBox QAbstractItemView {{
        background-color: {_CLR_INPUT_BG}; color: {_CLR_TEXT_BTN_LOG};
        border: 1px solid {_CLR_BORDER}; selection-background-color: {_CLR_BORDER}; outline: 0;
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
        padding: 6px;
    }}
    QTabBar::tab {{
        background-color: {_CLR_BG_MAIN};
        color: {_CLR_TEXT_MUTED};
        padding: 6px 16px;
        border: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-size: 13px;
        font-family: {_UI_FONT};
        font-weight: 500;
        margin-right: 2px;
    }}
    QTabBar::tab:hover {{
        background-color: {_CLR_BG_CARD};
        color: {_CLR_TEXT_BTN_LOG};
    }}
    QTabBar::tab:selected {{
        background-color: {_CLR_BG_CARD};
        color: {_CLR_TEXT_WHITE};
        border-bottom: 2px solid #007AFF;
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
        border-radius: 6px;
        font-size: 12px;
        font-family: {_UI_FONT};
        padding: 4px 12px;
        min-height: 20px;
    }}
    QPushButton#dlgRowBtn:hover {{
        background-color: {_CLR_BORDER};
        border-color: {_CLR_BORDER_HOVER};
        color: {_CLR_TEXT_WHITE};
    }}
    QPushButton#dlgRowBtn:pressed {{
        background-color: {_CLR_BORDER_SOFT};
    }}
    QTableWidget#dlgStepTable {{
        background-color: {_CLR_INPUT_BG};
        color: {_CLR_TEXT_BTN_LOG};
        border: 1px solid {_CLR_BORDER};
        border-radius: 8px;
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
        background-color: rgba(0, 122, 255, 0.22);
        color: {_CLR_TEXT_WHITE};
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
        background-color: #020617;
        color: #E5E5EA;
    }}
    QLabel {{
        background-color: transparent;
        color: #E5E5EA;
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
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 4px;
    }}
    QComboBox {{
        background-color: #020617;
        color: #E5E5EA;
        border: 1px solid #1E293B;
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
        background: transparent;
    }}
    QComboBox QAbstractItemView {{
        background-color: #020617;
        color: #E5E5EA;
        border: 1px solid #1E293B;
        selection-background-color: #334155;
    }}
"""


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

    def __init__(self, *args, bg=_CLR_INPUT_BG, border=_CLR_BORDER, arrow_color="#A1A1AA",
                 hover_color="#007AFF", **kwargs):
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
                border: 1.5px solid {border};
                border-radius: 6px;
                padding: 4px 28px 4px 10px;
                color: #E5E5EA;
                font-size: 13px;
            }}
            QComboBox:disabled {{
                background-color: #0B1220;
                color: {_CLR_DISABLED};
                border: 1.5px solid #1A2436;
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
                color: #E5E5EA;
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
        delegate = _SerialComboItemDelegate(
            padding_v=self._ITEM_PADDING_V, parent=list_view
        )
        list_view.setItemDelegate(delegate)
        palette = list_view.palette()
        palette.setColor(QPalette.Highlight, QColor(hover_color))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        list_view.setPalette(palette)
        list_view.setStyleSheet(f"""
            QListView {{
                background-color: {bg};
                color: #F4F4F5;
                border: 1px solid {border};
                outline: 0;
            }}
            QListView::item {{
                padding: {self._ITEM_PADDING_V}px 10px;
                border: none;
            }}
            QListView::item:hover {{
                background-color: {hover_color};
                color: white;
            }}
            QListView::item:selected {{
                background-color: {hover_color};
                color: white;
                border: none;
                outline: none;
            }}
        """)
        self.setView(list_view)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        bg = QColor(self._popup_bg)
        bd = QColor(self._popup_border)
        if not self.isEnabled():
            bg = bg.darker(130)
            bd = bd.darker(130)
        painter.setPen(QPen(bd, 1.5))
        painter.setBrush(bg)
        painter.drawRoundedRect(r, 6, 6)

        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        if not self.isEditable():
            text_rect: QRect = self.style().subControlRect(
                QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self
            )
            fm = QFontMetrics(self.font())
            elided = fm.elidedText(self.currentText(), Qt.ElideMiddle, text_rect.width())
            painter.setPen(QColor("#E5E5EA") if self.isEnabled() else QColor("#52525B"))
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        arrow_rect: QRect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

        color = QColor(self._arrow_color)
        if not self.isEnabled():
            color = QColor("#3F3F46")
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
            row_h = view.sizeHintForRow(0)
            if row_h <= 0:
                row_h = fm.height() + self._ITEM_PADDING_V * 2
            view.setMinimumHeight(visible * row_h)
        super().showPopup()
        popup = view.window()
        if popup:
            popup.setStyleSheet(
                f"background-color: {self._popup_bg}; "
                f"border: 1px solid {self._popup_border}; "
                f"padding: 0px; margin: 0px;"
            )
            if self.count() <= self.maxVisibleItems():
                for child in popup.children():
                    cls_name = child.metaObject().className()
                    if "Scroller" in cls_name or "QComboBoxPrivateScroller" in cls_name:
                        child.hide()
                        child.setMaximumHeight(0)


_CLR_HISTORY_COMBO_BG = _T.history_combo_bg
_HISTORY_COMBO_FIELD_QCOLOR = _T.history_combo_qcolor


def history_combo_style():
    return f"""
            QComboBox {{
                background-color: {_CLR_HISTORY_COMBO_BG}; border: 1px solid #1E293B; border-radius: 6px;
                color: {_CLR_INPUT_TEXT}; font-size: 13px; font-family: {_TERM_FONT};
                padding: 3px 28px 3px 10px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
            QComboBox:focus {{ border: 1px solid {_CLR_CONNECT_FG}; }}
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


class SerialHistoryComboBox(SerialDarkComboBox):
    def __init__(self, *args, field_bg=_HISTORY_COMBO_FIELD_QCOLOR, popup_bg=_CLR_INPUT_BG,
                 border=_CLR_BORDER, **kwargs):
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
    "SERIAL_SCROLLBAR_STYLE", "SerialDarkComboBox", "SerialHistoryComboBox",
    "_CLR_HISTORY_COMBO_BG",
]
