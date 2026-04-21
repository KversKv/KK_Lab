"""左栏：节点面板（可拖拽到序列画布）"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QMimeData
from PySide6.QtGui import QDrag, QFont

from ui.pages.custom_test.nodes.base_node import BaseNode, get_nodes_by_category

from log_config import get_logger

logger = get_logger(__name__)

_CATEGORY_META = {
    "instrument": {"title": "📦 Instruments", "order": 0},
    "logic":      {"title": "🔀 Logic / Flow", "order": 1},
    "io":         {"title": "💾 Data I/O", "order": 2},
}

_PALETTE_ITEM_STYLE = """
    QFrame#paletteItem {{
        background-color: {bg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 6px 10px;
    }}
    QFrame#paletteItem:hover {{
        background-color: {hover_bg};
        border: 1px solid {hover_border};
    }}
"""

_PALETTE_STYLE = """
    QWidget#nodePalette {
        background-color: transparent;
        border: none;
    }
    QScrollArea {
        background-color: transparent;
        border: none;
    }
    QLabel#categoryTitle {
        color: #5f78a8;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 8px 4px 4px 4px;
        background: transparent;
        border: none;
    }
"""


class PaletteItem(QFrame):
    """面板中可拖拽的节点项"""

    double_clicked = Signal(str)

    def __init__(self, node_cls: Type[BaseNode], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._node_cls = node_cls
        self.setObjectName("paletteItem")
        self.setCursor(Qt.OpenHandCursor)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        color = node_cls.color or "#5b5cf6"
        self.setStyleSheet(_PALETTE_ITEM_STYLE.format(
            bg="#0d1a36",
            border="#1a2d57",
            hover_bg="#132040",
            hover_border=color,
        ))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(1)

        title = QLabel(f"{node_cls.icon}  {node_cls.display_name}")
        title.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600; "
                            "background: transparent; border: none;")
        layout.addWidget(title)

        sub = QLabel(node_cls.node_type)
        sub.setStyleSheet("color: #5f6f8f; font-size: 10px; background: transparent; border: none;")
        layout.addWidget(sub)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self._node_cls.node_type)
            drag.setMimeData(mime)
            drag.exec(Qt.CopyAction)
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit(self._node_cls.node_type)
        super().mouseDoubleClickEvent(event)


class NodePalette(QWidget):
    """左栏节点面板"""

    node_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("nodePalette")
        self.setStyleSheet(_PALETTE_STYLE)
        self.setMinimumWidth(200)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        inner = QWidget()
        inner.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(8, 4, 8, 8)
        self._inner_layout.setSpacing(4)

        sorted_cats = sorted(_CATEGORY_META.items(), key=lambda x: x[1]["order"])
        for cat_key, meta in sorted_cats:
            nodes = get_nodes_by_category(cat_key)
            if not nodes:
                continue

            title_label = QLabel(meta["title"])
            title_label.setObjectName("categoryTitle")
            self._inner_layout.addWidget(title_label)

            for node_cls in nodes:
                item = PaletteItem(node_cls, self)
                item.double_clicked.connect(self._on_item_double_clicked)
                self._inner_layout.addWidget(item)

        self._inner_layout.addStretch()
        scroll.setWidget(inner)
        root_layout.addWidget(scroll)

    def _on_item_double_clicked(self, node_type: str) -> None:
        self.node_requested.emit(node_type)
