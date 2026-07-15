#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PMU 1811 页面（占位）。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from log_config import get_logger

logger = get_logger(__name__)


class Pmu1811UI(QWidget):
    """PMU 1811 占位页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QWidget { background-color: #020817; color: #dbe7ff; }"
            "QLabel { background: transparent; color: #dbe7ff; border: none; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(8)

        title = QLabel("PMU 1811")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        hint = QLabel("（占位页面，待实现）")
        hint.setStyleSheet("color: #7b93bf; font-size: 12px;")
        root.addWidget(hint)
        root.addStretch(1)
