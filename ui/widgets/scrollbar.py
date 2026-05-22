import os as _os
from ui.resource_path import get_resource_base as _get_resource_base

_ICONS_DIR = _os.path.join(
    _get_resource_base(),
    "resources", "icons"
)

_ARROW_UP = _os.path.join(_ICONS_DIR, "scrollbar-arrow-up.svg").replace("\\", "/")
_ARROW_DOWN = _os.path.join(_ICONS_DIR, "scrollbar-arrow-down.svg").replace("\\", "/")
_ARROW_LEFT = _os.path.join(_ICONS_DIR, "scrollbar-arrow-left.svg").replace("\\", "/")
_ARROW_RIGHT = _os.path.join(_ICONS_DIR, "scrollbar-arrow-right.svg").replace("\\", "/")

SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        background: #0C1017;
        width: 10px;
        margin: 14px 0px 14px 0px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: #334155;
        min-height: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #475569;
    }}
    QScrollBar::sub-line:vertical {{
        height: 14px;
        subcontrol-position: top;
        subcontrol-origin: margin;
        background: #141B24;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
    }}
    QScrollBar::sub-line:vertical:hover {{
        background: #1E293B;
    }}
    QScrollBar::add-line:vertical {{
        height: 14px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
        background: #141B24;
        border-bottom-left-radius: 5px;
        border-bottom-right-radius: 5px;
    }}
    QScrollBar::add-line:vertical:hover {{
        background: #1E293B;
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
        background: #0C1017;
        height: 10px;
        margin: 0px 14px 0px 14px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal {{
        background: #334155;
        min-width: 30px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: #475569;
    }}
    QScrollBar::sub-line:horizontal {{
        width: 14px;
        subcontrol-position: left;
        subcontrol-origin: margin;
        background: #141B24;
        border-top-left-radius: 5px;
        border-bottom-left-radius: 5px;
    }}
    QScrollBar::sub-line:horizontal:hover {{
        background: #1E293B;
    }}
    QScrollBar::add-line:horizontal {{
        width: 14px;
        subcontrol-position: right;
        subcontrol-origin: margin;
        background: #141B24;
        border-top-right-radius: 5px;
        border-bottom-right-radius: 5px;
    }}
    QScrollBar::add-line:horizontal:hover {{
        background: #1E293B;
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

SCROLL_AREA_STYLE = """
    QScrollArea {
        background: transparent;
        border: none;
    }
""" + SCROLLBAR_STYLE
