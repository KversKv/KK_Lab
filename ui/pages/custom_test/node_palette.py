"""左栏：节点面板（可拖拽到序列画布）"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Type

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QGridLayout, QPushButton,
)
from PySide6.QtCore import Qt, Signal, QMimeData, QRectF
from PySide6.QtGui import QDrag, QPixmap, QImage, QPainter, QColor, QIcon
from PySide6.QtSvg import QSvgRenderer

from ui.pages.custom_test.nodes.base_node import BaseNode, get_nodes_by_category

from log_config import get_logger

logger = get_logger(__name__)

_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "resources", "icons"
)


def _tinted_svg_pixmap(svg_path: str, color: str, size: int = 16) -> QPixmap:
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return pixmap


_COLLAPSE_HEADER_STYLE = """
    QPushButton#collapseHeader {
        background-color: transparent;
        color: #5f78a8;
        border: none;
        border-bottom: 1px solid #111d3a;
        border-radius: 0px;
        padding: 6px 4px;
        font-size: 11px;
        font-weight: 700;
        text-align: left;
    }
    QPushButton#collapseHeader:hover {
        background-color: #0e1f3d;
        color: #8899bb;
    }
"""

_SECTION_FRAME_STYLE = """
    QFrame#collapsibleFrame {
        background-color: #0a1530;
        border: 1px solid #12234a;
        border-radius: 8px;
    }
"""


class CollapsibleSection(QWidget):

    def __init__(
        self,
        title: str,
        icon_svg: Optional[str] = None,
        expanded: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._expanded = expanded
        self.setStyleSheet("QWidget { background: transparent; border: none; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._frame = QFrame()
        self._frame.setObjectName("collapsibleFrame")
        self._frame.setStyleSheet(_SECTION_FRAME_STYLE)
        outer.addWidget(self._frame)

        root = QVBoxLayout(self._frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setObjectName("collapseHeader")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet(_COLLAPSE_HEADER_STYLE)
        self._toggle_btn.clicked.connect(self.toggle)

        btn_layout = QHBoxLayout(self._toggle_btn)
        btn_layout.setContentsMargins(8, 0, 8, 0)
        btn_layout.setSpacing(4)

        self._arrow_label = QLabel()
        self._arrow_label.setFixedSize(12, 12)
        self._arrow_label.setStyleSheet("background: transparent; border: none;")
        btn_layout.addWidget(self._arrow_label)

        if icon_svg and os.path.isfile(icon_svg):
            cat_icon = QLabel()
            cat_icon.setPixmap(_tinted_svg_pixmap(icon_svg, "#5f78a8", 12))
            cat_icon.setFixedSize(14, 14)
            cat_icon.setStyleSheet("background: transparent; border: none;")
            btn_layout.addWidget(cat_icon)

        text_label = QLabel(title)
        text_label.setStyleSheet(
            "color: #5f78a8; font-size: 11px; font-weight: 700; "
            "letter-spacing: 1px; padding: 0px; background: transparent; border: none;"
        )
        btn_layout.addWidget(text_label)
        btn_layout.addStretch()

        root.addWidget(self._toggle_btn)

        self._content = QWidget()
        self._content.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 6, 8, 8)
        self._content_layout.setSpacing(4)
        root.addWidget(self._content)

        self._update_state()

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._update_state()

    def _update_state(self) -> None:
        self._content.setVisible(self._expanded)
        if self._expanded:
            self._toggle_btn.setStyleSheet(_COLLAPSE_HEADER_STYLE)
        else:
            self._toggle_btn.setStyleSheet(
                _COLLAPSE_HEADER_STYLE.replace(
                    "border-bottom: 1px solid #111d3a;",
                    "border-bottom: none;"
                )
            )
        chevron_down = os.path.join(_ICONS_DIR, "chevron-down.svg")
        chevron_right = os.path.join(_ICONS_DIR, "chevron-right.svg")
        if self._expanded and os.path.isfile(chevron_down):
            self._arrow_label.setPixmap(_tinted_svg_pixmap(chevron_down, "#5f78a8", 12))
        elif not self._expanded and os.path.isfile(chevron_right):
            self._arrow_label.setPixmap(_tinted_svg_pixmap(chevron_right, "#5f78a8", 12))
        else:
            self._arrow_label.setText("▾" if self._expanded else "▸")

INSTRUMENT_REGISTRY: List[Dict] = [
    {
        "id": "n6705c",
        "name": "N6705C",
        "thumb": "n6705c_thumb.svg",
        "color": "#f2994a",
        "categories": [
            {"name": "Config", "ops": [
                {"node_type": "N6705CSetMode", "label": "Set Mode"},
                {"node_type": "N6705CSetRange", "label": "Set Range"},
                {"node_type": "N6705CChannelOn", "label": "Channel ON"},
                {"node_type": "N6705CChannelOff", "label": "Channel OFF"},
            ]},
            {"name": "Set", "ops": [
                {"node_type": "N6705CSetVoltage", "label": "Set Voltage"},
                {"node_type": "N6705CSetCurrent", "label": "Set Current"},
                {"node_type": "N6705CSetCurrentLimit", "label": "Set I Limit"},
            ]},
            {"name": "Get", "ops": [
                {"node_type": "N6705CMeasure", "label": "Measure V/I/P"},
                {"node_type": "N6705CGetMode", "label": "Get Mode"},
                {"node_type": "N6705CGetChannelState", "label": "Get CH State"},
            ]},
        ],
    },
    {
        "id": "mso64b",
        "name": "MSO64B",
        "thumb": "mso64b_thumb.svg",
        "color": "#3ade85",
        "categories": [
            {"name": "Config", "ops": [
                {"node_type": "ScopeSetChannel", "label": "Set Channel"},
                {"node_type": "ScopeSetScale", "label": "Set Scale"},
                {"node_type": "ScopeSetTimebase", "label": "Set Timebase"},
                {"node_type": "ScopeSetTrigger", "label": "Set Trigger"},
            ]},
            {"name": "Set", "ops": [
                {"node_type": "ScopeRunStop", "label": "Run / Stop"},
            ]},
            {"name": "Get", "ops": [
                {"node_type": "ScopeMeasure", "label": "Measure"},
                {"node_type": "ScopeMeasureFreq", "label": "Measure Freq"},
                {"node_type": "ScopeGetDvmDC", "label": "Get DVM DC"},
            ]},
        ],
    },
    {
        "id": "dsox4034a",
        "name": "DSOX4034A",
        "thumb": "dsox4034a_thumb.svg",
        "color": "#f59e0b",
        "categories": [
            {"name": "Config", "ops": [
                {"node_type": "ScopeSetChannel", "label": "Set Channel"},
                {"node_type": "ScopeSetScale", "label": "Set Scale"},
                {"node_type": "ScopeSetTimebase", "label": "Set Timebase"},
                {"node_type": "ScopeSetTrigger", "label": "Set Trigger"},
            ]},
            {"name": "Set", "ops": [
                {"node_type": "ScopeRunStop", "label": "Run / Stop"},
            ]},
            {"name": "Get", "ops": [
                {"node_type": "ScopeMeasure", "label": "Measure"},
                {"node_type": "ScopeMeasureFreq", "label": "Measure Freq"},
            ]},
        ],
    },
    {
        "id": "vt6002",
        "name": "VT6002",
        "thumb": "vt6002_thumb.svg",
        "color": "#e07b39",
        "categories": [
            {"name": "Config", "ops": [
                {"node_type": "ChamberStartStop", "label": "Start / Stop"},
            ]},
            {"name": "Set", "ops": [
                {"node_type": "ChamberSetTemp", "label": "Set Temperature"},
            ]},
            {"name": "Get", "ops": [
                {"node_type": "ChamberGetTemp", "label": "Get Temperature"},
                {"node_type": "ChamberGetSetTemp", "label": "Get Set Temp"},
                {"node_type": "ChamberGetHumidity", "label": "Get Humidity"},
            ]},
        ],
    },
    {
        "id": "cmw270",
        "name": "CMW270",
        "thumb": "cmw270_thumb.svg",
        "color": "#a78bfa",
        "categories": [
            {"name": "Get", "ops": [
                {"node_type": "RFAnalyzerMeasure", "label": "RF Measure"},
            ]},
        ],
    },
    {
        "id": "i2c",
        "name": "REG Ctrl",
        "thumb": "cpu.svg",
        "color": "#fb923c",
        "categories": [
            {"name": "Set", "ops": [
                {"node_type": "I2CWrite", "label": "I2C Write"},
            ]},
            {"name": "Get", "ops": [
                {"node_type": "I2CRead", "label": "I2C Read"},
                {"node_type": "I2CTraverse", "label": "I2C Traverse"},
            ]},
        ],
    },
    {
        "id": "uart",
        "name": "UART",
        "thumb": "terminal.svg",
        "color": "#94a3b8",
        "categories": [
            {"name": "Set", "ops": [
                {"node_type": "UARTSend", "label": "UART Send"},
            ]},
            {"name": "Get", "ops": [
                {"node_type": "UARTReceive", "label": "UART Receive"},
            ]},
        ],
    },
]

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

_INSTR_CARD_STYLE = """
    QFrame#instrCard {{
        background-color: #0d1a36;
        border: 1px solid #1a2d57;
        border-radius: 10px;
        padding: 0px;
    }}
    QFrame#instrCard:hover {{
        background-color: #132040;
        border: 1px solid {color};
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


class InstrumentCard(QFrame):
    """仪器缩略卡片：SVG 缩略图 + 居中仪器名"""

    double_clicked = Signal(str)

    def __init__(self, instr_info: Dict, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._instr = instr_info
        self.setObjectName("instrCard")
        self.setCursor(Qt.OpenHandCursor)
        self.setFixedSize(84, 82)
        self.setStyleSheet(_INSTR_CARD_STYLE.format(color=instr_info["color"]))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 6, 4, 4)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignCenter)

        svg_path = os.path.join(_ICONS_DIR, instr_info["thumb"])
        is_icon = not instr_info["thumb"].endswith("_thumb.svg")
        thumb_label = QLabel()
        thumb_label.setFixedSize(66, 40)
        thumb_label.setAlignment(Qt.AlignCenter)
        thumb_label.setStyleSheet("background: transparent; border: none;")
        if os.path.isfile(svg_path):
            if is_icon:
                icon_size = 22
                badge_size = 36
                badge = QPixmap(badge_size * 2, badge_size * 2)
                badge.fill(Qt.transparent)
                bp = QPainter(badge)
                bp.setRenderHint(QPainter.Antialiasing)
                bg_color = QColor(instr_info["color"])
                bg_color.setAlpha(38)
                bp.setBrush(bg_color)
                bp.setPen(Qt.NoPen)
                bp.drawEllipse(0, 0, badge_size * 2, badge_size * 2)
                tinted = _tinted_svg_pixmap(svg_path, instr_info["color"], icon_size * 2)
                offset = (badge_size * 2 - icon_size * 2) // 2
                bp.drawPixmap(offset, offset, tinted)
                bp.end()
                thumb_label.setPixmap(badge.scaled(
                    badge_size, badge_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            else:
                renderer = QSvgRenderer(svg_path)
                image = QImage(132, 80, QImage.Format_ARGB32_Premultiplied)
                image.fill(Qt.transparent)
                painter = QPainter(image)
                renderer.render(painter)
                painter.end()
                pixmap = QPixmap.fromImage(image).scaled(
                    66, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                thumb_label.setPixmap(pixmap)
        else:
            box_svg = os.path.join(_ICONS_DIR, "box.svg")
            if os.path.isfile(box_svg):
                thumb_label.setPixmap(_tinted_svg_pixmap(box_svg, instr_info["color"], 32))
            else:
                thumb_label.setText("?")
            thumb_label.setStyleSheet(
                "background: transparent; border: none; font-size: 24px;"
            )
        layout.addWidget(thumb_label, 0, Qt.AlignCenter)

        name_label = QLabel(instr_info["name"])
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet(
            f"color: {instr_info['color']}; font-size: 10px; font-weight: 700; "
            "background: transparent; border: none; padding: 0px;"
        )
        layout.addWidget(name_label, 0, Qt.AlignCenter)

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
            mime.setData("application/x-instrument-id", self._instr["id"].encode("utf-8"))
            pixmap = self.grab()
            drag.setPixmap(pixmap.scaled(84, 82, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.setMimeData(mime)
            drag.exec(Qt.CopyAction)
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit(self._instr["id"])
        super().mouseDoubleClickEvent(event)


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


def get_instrument_by_id(instr_id: str) -> Optional[Dict]:
    for info in INSTRUMENT_REGISTRY:
        if info["id"] == instr_id:
            return info
    return None


class NodePalette(QWidget):
    """左栏节点面板：仪器区域（缩略图网格）+ 逻辑/IO 区域"""

    node_requested = Signal(str)
    instrument_requested = Signal(str)

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
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #22345f;
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #30497f;
            }
            QScrollBar::sub-line:vertical,
            QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        inner = QWidget()
        inner.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._inner_layout = QVBoxLayout(inner)
        self._inner_layout.setContentsMargins(0, 4, 6, 8)
        self._inner_layout.setSpacing(6)

        self._build_instrument_section()
        self._build_category_sections()

        self._inner_layout.addStretch()
        scroll.setWidget(inner)
        root_layout.addWidget(scroll)

    def _build_instrument_section(self) -> None:
        microscope_path = os.path.join(_ICONS_DIR, "microscope.svg")
        section = CollapsibleSection(
            "Instruments",
            icon_svg=microscope_path,
            expanded=True,
            parent=self,
        )

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 4)

        for idx, instr in enumerate(INSTRUMENT_REGISTRY):
            card = InstrumentCard(instr, self)
            card.double_clicked.connect(self._on_instrument_double_clicked)
            row = idx // 2
            col = idx % 2
            grid.addWidget(card, row, col, Qt.AlignCenter)

        grid_widget = QWidget()
        grid_widget.setStyleSheet("QWidget { background: transparent; border: none; }")
        grid_widget.setLayout(grid)
        section.content_layout.addWidget(grid_widget)

        self._inner_layout.addWidget(section)

    def _build_category_sections(self) -> None:
        _HIDDEN_NODE_TYPES = {
            "IfElse", "IfThenElse", "IfBranch", "ElseIfBranch", "ElseBranch",
        }
        _cat_icons = {
            "value": ("tag.svg", "Value / Variables"),
            "logic": ("git-branch.svg", "Logic / Flow"),
            "io": ("hard-drive.svg", "Data I/O"),
        }
        for cat_key, (icon_file, cat_label) in _cat_icons.items():
            nodes = [
                cls for cls in get_nodes_by_category(cat_key)
                if cls.node_type not in _HIDDEN_NODE_TYPES
            ]
            if not nodes:
                continue

            svg_path = os.path.join(_ICONS_DIR, icon_file)
            section = CollapsibleSection(
                cat_label,
                icon_svg=svg_path if os.path.isfile(svg_path) else None,
                expanded=False,
                parent=self,
            )

            for node_cls in nodes:
                item = PaletteItem(node_cls, self)
                item.double_clicked.connect(self._on_item_double_clicked)
                section.content_layout.addWidget(item)

            self._inner_layout.addWidget(section)

    def insert_top_widget(self, widget: QWidget) -> None:
        self._inner_layout.insertWidget(0, widget)

    def _on_item_double_clicked(self, node_type: str) -> None:
        self.node_requested.emit(node_type)

    def _on_instrument_double_clicked(self, instr_id: str) -> None:
        self.instrument_requested.emit(instr_id)
