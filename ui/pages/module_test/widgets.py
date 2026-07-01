#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 页面复用控件：可折叠分组框。

复用既有 N6705CConnectionMixin / OscilloscopeConnectionMixin 构建的连接区
被包进可折叠容器，节省纵向空间。折叠通过点击标题栏切换内容可见性，
保持现有 QSS 风格（标题色/边框沿用页面样式）。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

_ARROW_EXPANDED = "▼"
_ARROW_COLLAPSED = "▶"


class CollapsibleGroupBox(QFrame):
    """带可折叠标题栏的分组容器（替代 QGroupBox，视觉一致 + 折叠能力）。

    用法：
        box = CollapsibleGroupBox("仪器连接", expanded=True)
        box.content_layout.addWidget(...)   # 把原 QGroupBox 内的控件加进去
    """

    def __init__(self, title: str, expanded: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._expanded = expanded
        self.setObjectName("collapsibleGroupBox")
        self.setStyleSheet("""
            QFrame#collapsibleGroupBox {
                border: 1px solid #333;
                border-radius: 6px;
                background-color: #0a0f1f;
            }
            QPushButton#collapseHeader {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #8eb0e3;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 700;
                text-align: left;
            }
            QPushButton#collapseHeader:hover {
                background-color: #161b2e;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toggle_btn = QPushButton(f"{_ARROW_EXPANDED if expanded else _ARROW_COLLAPSED}  {title}")
        self._toggle_btn.setObjectName("collapseHeader")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setCheckable(False)
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self.toggle)
        root.addWidget(self._toggle_btn)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(10, 4, 10, 8)
        self._content_layout.setSpacing(4)
        root.addWidget(self._content)

        self._content.setVisible(expanded)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def set_title(self, title: str) -> None:
        arrow = _ARROW_EXPANDED if self._expanded else _ARROW_COLLAPSED
        self._toggle_btn.setText(f"{arrow}  {title}")

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        title = self._toggle_btn.text()[2:]  # 去掉原箭头前缀
        arrow = _ARROW_EXPANDED if self._expanded else _ARROW_COLLAPSED
        self._toggle_btn.setText(f"{arrow}  {title}")

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded != expanded:
            self.toggle()
