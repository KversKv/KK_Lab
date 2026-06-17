"""ChatView：聊天消息列表展示（只读滚动区）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.scrollbar import SCROLLBAR_STYLE

_BUBBLE_STYLE_USER = """
QLabel#aiBubbleUser {
    background-color: #1d3a6e;
    color: #eaf1ff;
    border: 1px solid #2a4d8f;
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 12px;
}
"""

_BUBBLE_STYLE_AI = """
QLabel#aiBubbleAI {
    background-color: #141b2c;
    color: #d7e3ff;
    border: 1px solid #243152;
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 12px;
}
"""

_BUBBLE_STYLE_SYS = """
QLabel#aiBubbleSys {
    background-color: transparent;
    color: #8fa3c2;
    font-size: 11px;
    padding: 2px 4px;
}
"""


class ChatView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(SCROLLBAR_STYLE + "QScrollArea { background: transparent; border: none; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)
        self.setWidget(self._container)

    def _append_bubble(self, text: str, object_name: str, style: str, align) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        label.setStyleSheet(style)
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(label, 0, align)
        self._layout.insertWidget(self._layout.count() - 1, row)
        self._scroll_to_bottom()
        return label

    def add_user_message(self, text: str) -> None:
        self._append_bubble(text, "aiBubbleUser", _BUBBLE_STYLE_USER, Qt.AlignRight)

    def add_ai_message(self, text: str) -> QLabel:
        return self._append_bubble(text, "aiBubbleAI", _BUBBLE_STYLE_AI, Qt.AlignLeft)

    def add_system_message(self, text: str) -> None:
        self._append_bubble(text, "aiBubbleSys", _BUBBLE_STYLE_SYS, Qt.AlignHCenter)

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
