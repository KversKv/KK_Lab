import os

from ui.resource_path import get_resource_base


# Apple-inspired light style for the serial console.
# The function names mirror serialCom_dark_style.py so this file can be
# swapped into serialCom_module_frame.py with only the import path changed.
_SERIAL_BTN_HEIGHT = 26
_SERIAL_BTN_ICON_SIZE = 14
_SERIAL_BTN_RADIUS = 7
_TERM_FONT = '"JetBrains Mono", "Fira Code", Consolas, "Menlo", "Courier New", monospace'
_UI_FONT = '"Inter", "PingFang SC", "Microsoft YaHei", "Segoe UI", -apple-system, sans-serif'

_CLR_BG_MAIN = "#F5F5F7"
_CLR_BG_PANEL = "#F5F5F7"
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
            QSplitter::handle:hover {{ background-color: #E5E5EA; }}
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
    disabled_qss = f"\n            QPushButton:disabled {{ background-color: transparent; border-color: {_CLR_BORDER}; }}" if disabled else ""
    return f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; min-width: 28px; max-width: 28px;
                padding: 0px; border-radius: 7px;
                background-color: transparent; color: {_CLR_TEXT_MUTED}; border: 1px solid {_CLR_BORDER};
            }}
            QPushButton:hover {{ border-color: {_CLR_BORDER_SOFT}; }}
            QPushButton:focus {{ border-color: {_CLR_FILTER_BORDER}; background-color: {_CLR_INPUT_BG}; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; }}{disabled_qss}
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
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 6px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: {padding};
            }}
            QSpinBox:focus {{ border: 1px solid {_CLR_CONNECT_FG}; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: {up_button_width}px; }}
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
        """
    else:
        checked_qss = f"QPushButton:checked {{ background-color: {_CLR_BORDER}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BORDER_HOVER}; }}"
    return f"""
                QPushButton {{
                    min-height: 0px; max-height: {max_height}px; padding: {padding}; border-radius: {radius}px;
                    background-color: rgba(255, 255, 255, 0.74); color: {_CLR_TEXT_BTN_LOG}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 500; border: 1px solid {_CLR_BORDER_SOFT};
                }}
                QPushButton:hover {{ background-color: {_CLR_BORDER}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_BORDER_HOVER}; }}
                QPushButton:focus {{ background-color: {_CLR_BORDER}; color: {_CLR_TEXT_WHITE}; border: 1px solid {_CLR_FILTER_BORDER}; }}
                QPushButton:pressed {{ background-color: {_CLR_INPUT_BG}; }}
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
                    background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid {_CLR_BORDER};
                    color: {_CLR_TEXT_BODY}; font-family: {family}; font-size: {font_size}px; font-weight: 400;
                    padding: {padding};{line_height}
                    selection-background-color: {_CLR_SELECTION_BG};
                    selection-color: {_CLR_SELECTION_TEXT};
                }}
            """


def log_document_style():
    return "p, div { line-height: 150%; margin: 0; padding: 0; }"


def history_combo_style():
    return f"""
            QComboBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 7px;
                color: {_CLR_INPUT_TEXT}; font-size: 14px; font-family: {_UI_FONT};
                padding: 3px 28px 3px 10px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
            QComboBox:focus {{ border: 1px solid {_CLR_CONNECT_FG}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QComboBox QLineEdit {{
                background-color: transparent; border: none;
                color: {_CLR_INPUT_TEXT}; font-size: 14px; font-family: {_UI_FONT};
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
            QPushButton:hover {{ border: 1px solid {_CLR_BORDER_SOFT}; color: {_CLR_TEXT_WHITE}; }}
            QPushButton:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; color: {_CLR_TEXT_WHITE}; background-color: {_CLR_INPUT_BG}; }}
            QPushButton:pressed {{ background-color: {_CLR_BG_CARD}; }}
            QPushButton:checked {{ border: 1px solid {_CLR_BORDER_SOFT}; color: {_CLR_TEXT_WHITE}; }}
        """


def send_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_SEND_BG}; border: none; border-radius: 6px;
                color: {_CLR_BG_MAIN}; font-weight: 700; font-size: 13px;
                font-family: {_UI_FONT}; padding: 3px 20px;
            }}
            QPushButton:hover {{ background-color: {_CLR_SEND_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_SEND_PRESS}; }}
            QPushButton:disabled {{ background-color: {_CLR_BORDER}; color: {_CLR_DISABLED}; }}
        """


def quick_commands_panel_style():
    return f"""
            QFrame#quickCommandsPanel {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_BORDER};
                border-radius: 8px;
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
                color: {_CLR_TEXT_WHITE};
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton:pressed {{
                background-color: {_CLR_BLUE};
                border-color: {_CLR_BLUE_LIGHT};
            }}
            QFrame#quickCommandsPanel QScrollArea {{
                background: transparent;
                border: none;
            }}
        """


def project_tabs_style():
    return f"""
            QTabBar {{
                background: transparent;
                border-bottom: 1px solid {_CLR_BORDER};
            }}
            QTabBar::tab {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_BTN_LOG};
                border: 1px solid {_CLR_BORDER_HOVER};
                border-top: 2px solid {_CLR_BORDER_HOVER};
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                padding: 3px 10px;
                margin-right: 1px;
                margin-bottom: 0px;
                min-height: 15px;
                font-size: 11px;
                font-family: {_UI_FONT};
            }}
            QTabBar::tab:hover {{
                background-color: {_CLR_BORDER};
                color: {_CLR_TEXT_TAB};
                border-color: {_CLR_DISABLED};
                border-top-color: {_CLR_DISABLED};
            }}
            QTabBar::tab:selected {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_TITLE};
                border: 1px solid {_CLR_BORDER_HOVER};
                border-top: 2px solid {_CLR_BORDER_ACTIVE};
                border-bottom: none;
            }}
            QTabBar::tab:selected:hover {{
                background-color: {_CLR_INPUT_BG};
                color: {_CLR_TEXT_WHITE};
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
                background-color: {_CLR_BORDER_SOFT};
                border-color: {_CLR_BORDER_HOVER};
                color: {_CLR_TEXT_WHITE};
            }}
            QPushButton:focus {{
                background-color: {_CLR_BORDER_SOFT};
                border-color: {_CLR_FILTER_BORDER};
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
                background-color: #E5E5EA;
                color: {_CLR_DISABLED};
                border-color: {_CLR_BORDER};
            }}
        """


def quick_add_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_CONNECT_BG};
                color: {_CLR_CONNECT_TEXT};
                border: 1px solid rgba(52, 199, 89, 0.28);
                border-radius: 5px;
                padding: 3px 8px;
                min-height: 18px;
                font-size: 11px;
                font-family: {_UI_FONT};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {_CLR_CONNECT_HOVER};
                border-color: rgba(52, 199, 89, 0.45);
            }}
            QPushButton:pressed {{
                background-color: {_CLR_CONNECT_PRESS};
                border-color: rgba(52, 199, 89, 0.56);
            }}
        """


def quick_button_scroll_style():
    return "QScrollArea { background: transparent; border: none; }"


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
    return """
            QFrame#scSectionCard {
                background-color: transparent;
                border: none;
                border-bottom: 1px solid rgba(60, 60, 67, 0.14);
                border-radius: 0px;
            }
        """


def section_title_style():
    return f"color: {_CLR_TEXT_MUTED}; font-size: 12px; font-weight: 700; font-family: {_UI_FONT}; background: transparent; border: none; margin-bottom: 4px;"


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
                    background-color: #F2F2F7;
                    color: {_CLR_TEXT_SOFT};
                    border: 1px solid {_CLR_BORDER_SOFT};
                    border-radius: 6px;
                    padding: 3px 9px;
                    min-height: 16px;
                    min-width: 39px;
                    font-size: 11px;
                    font-weight: 500;
                    font-family: {_UI_FONT};
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
                    background-color: {_CLR_BLUE};
                    border-color: {_CLR_BLUE_LIGHT};
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
                color: {_CLR_TEXT_MUTED}; font-size: 13px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;
            }}
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 7px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 8px; min-height: 26px;
            }}
            QLineEdit:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
            QComboBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 7px;
                color: {_CLR_TEXT_BTN_LOG}; font-size: 13px; font-family: {_UI_FONT}; padding: 4px 8px; min-height: 26px;
            }}
            QComboBox:hover {{ border-color: {_CLR_BORDER_SOFT}; }}
            QComboBox:focus {{ border-color: {_CLR_FILTER_BORDER}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox QAbstractItemView {{
                background-color: {_CLR_INPUT_BG}; color: {_CLR_TEXT_BTN_LOG};
                border: 1px solid {_CLR_BORDER}; selection-background-color: {_CLR_BORDER};
                outline: 0;
            }}
        """


def dialog_cancel_button_style():
    return f"""
            QPushButton {{
                background-color: transparent; border: 1px solid {_CLR_BORDER}; border-radius: 6px;
                color: {_CLR_TEXT_MUTED}; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 20px;
            }}
            QPushButton:hover {{ border-color: {_CLR_BORDER_SOFT}; color: {_CLR_TEXT_WHITE}; }}
        """


def dialog_ok_button_style():
    return f"""
            QPushButton {{
                background-color: {_CLR_GREEN_OK}; border: none; border-radius: 6px;
                color: {_CLR_TEXT_WHITE}; font-weight: 700; font-size: 13px; font-family: {_UI_FONT}; padding: 6px 20px;
            }}
            QPushButton:hover {{ background-color: {_CLR_GREEN_OK_HOVER}; }}
        """


def log_color_info_style():
    return f"color: {_CLR_TEXT_MUTED}; font-size: 11px; font-family: {_UI_FONT}; background: transparent;"


def log_color_info_text():
    return "RX -> Ink (#1d1d1f)    TX -> Apple Blue (#007aff)\nINFO -> Blue (#0a84ff)    WARN -> Orange (#ff9f0a)    ERROR -> Red (#ff3b30)"


_DLG_STYLE = f"""
    QDialog {{
        background-color: {_CLR_BG_MAIN};
        color: {_CLR_TEXT_BTN_LOG};
    }}
    QLabel {{ color: {_CLR_TEXT_MUTED}; font-size: 12px; font-family: {_UI_FONT}; background: transparent; }}
    QLabel#dlgSectionTitle {{
        color: {_CLR_TEXT_MUTED}; font-size: 13px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;
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
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 2px 6px;
    }}
    QSpinBox:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 12px; }}
    QLineEdit {{
        background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(60, 60, 67, 0.18); border-radius: 6px;
        color: {_CLR_TEXT_BTN_LOG}; font-size: 12px; font-family: {_UI_FONT}; padding: 5px 8px; min-height: 24px;
    }}
    QLineEdit:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
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
        color: {_CLR_TEXT_TITLE};
        border-bottom: 2px solid #007AFF;
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


__all__ = [name for name in globals() if name.startswith("_CLR_")]
__all__ += [
    name for name, value in globals().items()
    if callable(value) and not name.startswith("__")
]
__all__ += [
    "_SERIAL_BTN_HEIGHT", "_SERIAL_BTN_ICON_SIZE", "_SERIAL_BTN_RADIUS",
    "_TERM_FONT", "_UI_FONT", "_DLG_STYLE", "DARK_CARD_STYLE",
    "APPLE_CARD_STYLE",
]
