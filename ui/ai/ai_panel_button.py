"""AI 面板开关按钮（顶栏右侧，checkable）。

控件高度单一权威：用 ID 选择器 #aiPanelButton 钉死 min-height: 22px，
不在页面父级 QSS 写裸 QPushButton{min-height}。
"""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QPushButton

from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon

_AI_SVG_DIR = os.path.join(get_resource_base(), "resources", "icons_svg", "ai")
_PANEL_ICON = os.path.join(_AI_SVG_DIR, "ai_panel.svg")

_STYLE = """
QPushButton#aiPanelButton {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
}
QPushButton#aiPanelButton:hover {
    background-color: #1b2640;
}
QPushButton#aiPanelButton:checked {
    background-color: #5b3df5;
}
"""


class AIPanelButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aiPanelButton")
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFocusPolicy(Qt.NoFocus)
        self.setToolTip("Open / close AI Assistant panel")
        self.setStyleSheet(_STYLE)
        if os.path.isfile(_PANEL_ICON):
            self.setIcon(tinted_svg_icon(_PANEL_ICON, "#c6d4f2", 16))
            self.setIconSize(QSize(16, 16))
