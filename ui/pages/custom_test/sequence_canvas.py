"""中栏：序列画布（基于 QTreeWidget 的可视化测试流程）"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QFileDialog, QMessageBox,
    QAbstractItemView, QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QModelIndex, QSize
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QFontMetrics,
    QDragEnterEvent, QDragMoveEvent, QDropEvent,
)

from ui.pages.custom_test.nodes.base_node import BaseNode, get_node_class
from log_config import get_logger

logger = get_logger(__name__)

_DEPTH_COLORS = [
    "#2f80ed",
    "#e74c3c",
    "#27ae60",
    "#f2994a",
    "#9b59b6",
    "#16a085",
    "#e84393",
    "#00cec9",
]

_CANVAS_STYLE = """
    QTreeWidget {
        background-color: #060e20;
        border: 1px solid #1a2d57;
        border-radius: 10px;
        color: #dce7ff;
        font-size: 12px;
        outline: none;
        padding: 4px;
    }
    QTreeWidget::item {
        padding: 0px;
        border: none;
        min-height: 36px;
    }
    QTreeWidget::item:selected {
        background: transparent;
    }
    QTreeWidget::item:hover {
        background: transparent;
    }
    QTreeWidget::branch {
        background: transparent;
    }
    QTreeWidget::branch:has-children:!has-siblings:closed,
    QTreeWidget::branch:closed:has-children:has-siblings {
        image: none;
    }
    QTreeWidget::branch:open:has-children:!has-siblings,
    QTreeWidget::branch:open:has-children:has-siblings {
        image: none;
    }
    QHeaderView::section {
        background-color: #0b1428;
        color: #5f78a8;
        border: none;
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 700;
    }
"""

_TOOLBAR_BTN_STYLE = """
    QPushButton {
        background-color: #13254b;
        border: 1px solid #22376A;
        border-radius: 6px;
        color: #dce7ff;
        font-weight: 600;
        min-height: 28px;
        padding: 2px 10px;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: #1C2D55;
        border: 1px solid #3A5A9F;
    }
    QPushButton:pressed {
        background-color: #102040;
    }
    QPushButton:disabled {
        background-color: #0b1430;
        color: #5c7096;
        border: 1px solid #1a2850;
    }
"""

_EXEC_BTN_STYLE = """
    QPushButton {{
        background-color: {bg};
        border: 1px solid {border};
        border-radius: 6px;
        color: {fg};
        font-weight: 700;
        min-height: 30px;
        padding: 2px 14px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {hover};
    }}
    QPushButton:disabled {{
        background-color: #0b1430;
        color: #5c7096;
        border: 1px solid #1a2850;
    }}
"""

_DROP_MENU_STYLE = """
    QMenu {
        background-color: #0b1428;
        color: #dce7ff;
        border: 1px solid #1a2d57;
        border-radius: 6px;
        padding: 4px;
    }
    QMenu::item {
        padding: 8px 20px;
        border-radius: 4px;
        font-size: 12px;
    }
    QMenu::item:selected {
        background-color: #1a2d57;
    }
    QMenu::separator {
        height: 1px;
        background: #1a2d57;
        margin: 4px 8px;
    }
"""


def _get_item_depth(item: QTreeWidgetItem) -> int:
    depth = 0
    p = item.parent()
    while p:
        depth += 1
        p = p.parent()
    return depth


def _get_depth_color(depth: int) -> str:
    return _DEPTH_COLORS[depth % len(_DEPTH_COLORS)]


def _is_last_child(item: QTreeWidgetItem) -> bool:
    parent = item.parent()
    if parent is None:
        tree = item.treeWidget()
        if tree is None:
            return True
        return tree.indexOfTopLevelItem(item) == tree.topLevelItemCount() - 1
    return parent.indexOfChild(item) == parent.childCount() - 1


def _build_step_number(item: QTreeWidgetItem) -> str:
    parts: list[str] = []
    current = item
    while current:
        parent = current.parent()
        if parent:
            idx = parent.indexOfChild(current) + 1
        else:
            tree = current.treeWidget()
            idx = tree.indexOfTopLevelItem(current) + 1 if tree else 1
        parts.append(str(idx))
        current = parent
    parts.reverse()
    return ".".join(parts)


class SequenceItemDelegate(QStyledItemDelegate):
    """自定义绘制代理：为序列节点绘制层级可视化"""

    BAR_WIDTH = 3
    BAR_GAP = 10
    DEPTH_INDENT = 13
    ROW_MARGIN_V = 2
    CORNER_RADIUS = 6

    def __init__(self, tree: QTreeWidget, node_map: Dict[str, BaseNode],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tree = tree
        self._node_map = node_map

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        base = super().sizeHint(option, index)
        return QSize(base.width(), max(36, base.height()))

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        item = self._tree.itemFromIndex(index)
        col = index.column()
        rect = option.rect
        is_selected = bool(option.state & QStyle.State_Selected)

        uid = item.data(0, Qt.UserRole) if item else None
        node = self._node_map.get(uid) if uid else None
        depth = _get_item_depth(item) if item else 0
        is_container = node.accepts_children if node else False

        if col == 0:
            self._draw_depth_bars(painter, rect, item, depth)
            self._draw_row_background(painter, rect, item, depth, is_selected, is_container)
            self._draw_step_number(painter, rect, item, depth, is_container)
        elif col == 1:
            self._draw_row_background(painter, rect, item, depth, is_selected, is_container)
            self._draw_type_cell(painter, rect, item, node, is_container)
        elif col == 2:
            self._draw_row_background(painter, rect, item, depth, is_selected, is_container)
            self._draw_summary_cell(painter, rect, item, node)

        painter.restore()

    def _draw_depth_bars(self, painter: QPainter, rect: QRect,
                         item: QTreeWidgetItem, depth: int) -> None:
        if depth == 0:
            return
        ancestor = item.parent()
        for d in range(depth, 0, -1):
            if ancestor is None:
                break
            bar_color = QColor(_get_depth_color(d - 1))
            x = rect.left() + 4 + (d - 1) * self.DEPTH_INDENT
            is_last = _is_last_child(item) if d == depth else _is_last_child(ancestor)

            bar_color.setAlpha(80)
            pen = QPen(bar_color, self.BAR_WIDTH, Qt.SolidLine)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)

            if d == depth:
                top_y = rect.top()
                if is_last:
                    mid_y = rect.top() + rect.height() // 2
                    painter.drawLine(x, top_y, x, mid_y)
                    painter.drawLine(x, mid_y, x + 7, mid_y)
                else:
                    painter.drawLine(x, top_y, x, rect.bottom())
                    mid_y = rect.top() + rect.height() // 2
                    painter.drawLine(x, mid_y, x + 7, mid_y)
            else:
                if not is_last:
                    painter.drawLine(x, rect.top(), x, rect.bottom())

            ancestor = ancestor.parent() if ancestor else None

    def _draw_row_background(self, painter: QPainter, rect: QRect,
                             item: QTreeWidgetItem, depth: int,
                             is_selected: bool, is_container: bool) -> None:
        bg_rect = QRect(rect.left() + 1, rect.top() + self.ROW_MARGIN_V,
                        rect.width() - 2, rect.height() - 2 * self.ROW_MARGIN_V)

        if is_selected:
            sel_color = QColor("#1e3a6e")
            sel_color.setAlpha(180)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(sel_color))
            painter.drawRoundedRect(bg_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

            highlight = QColor("#5b5cf6")
            highlight.setAlpha(100)
            painter.setPen(QPen(highlight, 1.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(bg_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
        elif is_container:
            container_bg = QColor(_get_depth_color(depth))
            container_bg.setAlpha(20)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(container_bg))
            painter.drawRoundedRect(bg_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

            border_color = QColor(_get_depth_color(depth))
            border_color.setAlpha(60)
            painter.setPen(QPen(border_color, 1))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(bg_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)
        elif depth > 0:
            nested_bg = QColor(_get_depth_color(depth - 1))
            nested_bg.setAlpha(8)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(nested_bg))
            painter.drawRoundedRect(bg_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

    def _draw_step_number(self, painter: QPainter, rect: QRect,
                          item: QTreeWidgetItem, depth: int,
                          is_container: bool) -> None:
        step_str = _build_step_number(item) if item else "?"
        font = painter.font()
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)

        text_x = rect.left() + 4 + depth * self.DEPTH_INDENT + 12
        text_rect = QRect(text_x, rect.top(), rect.right() - text_x, rect.height())

        if is_container:
            painter.setPen(QColor(_get_depth_color(depth)))
        else:
            painter.setPen(QColor("#5f78a8"))

        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, step_str)

    def _draw_type_cell(self, painter: QPainter, rect: QRect,
                        item: QTreeWidgetItem, node: Optional[BaseNode],
                        is_container: bool) -> None:
        if node is None:
            return

        icon_str = node.icon
        name_str = node.display_name

        font = painter.font()
        font.setPixelSize(12)
        font.setBold(is_container)
        painter.setFont(font)

        icon_rect = QRect(rect.left() + 4, rect.top(), 20, rect.height())
        painter.setPen(QColor("#dce7ff"))
        painter.drawText(icon_rect, Qt.AlignVCenter | Qt.AlignCenter, icon_str)

        name_rect = QRect(rect.left() + 24, rect.top(), rect.width() - 28, rect.height())
        node_color = QColor(node.color) if node.color else QColor("#dce7ff")
        if is_container:
            node_color.setAlpha(255)
        painter.setPen(node_color)
        painter.drawText(name_rect, Qt.AlignVCenter | Qt.AlignLeft, name_str)

        if is_container:
            child_count = item.childCount() if item else 0
            badge_text = f"({child_count})"
            fm = QFontMetrics(font)
            name_width = fm.horizontalAdvance(name_str)
            badge_x = rect.left() + 24 + name_width + 6

            badge_font = painter.font()
            badge_font.setPixelSize(9)
            badge_font.setBold(False)
            painter.setFont(badge_font)

            badge_color = QColor(node.color) if node.color else QColor("#5f78a8")
            badge_color.setAlpha(140)
            painter.setPen(badge_color)
            painter.drawText(QRect(badge_x, rect.top(), 60, rect.height()),
                             Qt.AlignVCenter | Qt.AlignLeft, badge_text)

    def _draw_summary_cell(self, painter: QPainter, rect: QRect,
                           item: QTreeWidgetItem, node: Optional[BaseNode]) -> None:
        if node is None:
            return

        summary_parts = []
        for k, v in node.params.items():
            summary_parts.append(f"{k}={v}")
        text = ", ".join(summary_parts[:3])

        font = painter.font()
        font.setPixelSize(11)
        font.setBold(False)
        painter.setFont(font)

        text_rect = QRect(rect.left() + 4, rect.top(), rect.width() - 8, rect.height())
        painter.setPen(QColor("#7a90b8"))
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)


class DropAwareTreeWidget(QTreeWidget):
    """支持外部拖拽的 QTreeWidget"""

    external_node_dropped = Signal(str)
    instrument_dropped = Signal(str, QPoint)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime = event.mimeData()
        if mime.hasText() or mime.hasFormat("application/x-instrument-id"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        mime = event.mimeData()
        if mime.hasText() or mime.hasFormat("application/x-instrument-id"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        if mime.hasFormat("application/x-instrument-id"):
            instr_id = bytes(mime.data("application/x-instrument-id")).decode("utf-8")
            global_pos = self.mapToGlobal(event.position().toPoint())
            self.instrument_dropped.emit(instr_id, global_pos)
            event.acceptProposedAction()
        elif mime.hasText():
            node_type = mime.text()
            if get_node_class(node_type) is not None:
                self.external_node_dropped.emit(node_type)
                event.acceptProposedAction()
            else:
                super().dropEvent(event)
        else:
            super().dropEvent(event)


class SequenceCanvas(QWidget):
    """序列画布：用 QTreeWidget 可视化节点树"""

    node_selected = Signal(object)
    sequence_changed = Signal()
    run_requested = Signal()
    stop_requested = Signal()
    pause_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._uid_map: Dict[str, QTreeWidgetItem] = {}
        self._node_map: Dict[str, BaseNode] = {}
        self._running = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.add_btn = QPushButton("+ Add")
        self.add_btn.setStyleSheet(_TOOLBAR_BTN_STYLE)
        self.add_btn.setToolTip("在选中节点后添加新节点")
        toolbar.addWidget(self.add_btn)

        self.remove_btn = QPushButton("✕ Remove")
        self.remove_btn.setStyleSheet(_TOOLBAR_BTN_STYLE)
        toolbar.addWidget(self.remove_btn)

        self.move_up_btn = QPushButton("↑")
        self.move_up_btn.setStyleSheet(_TOOLBAR_BTN_STYLE)
        self.move_up_btn.setFixedWidth(32)
        toolbar.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("↓")
        self.move_down_btn.setStyleSheet(_TOOLBAR_BTN_STYLE)
        self.move_down_btn.setFixedWidth(32)
        toolbar.addWidget(self.move_down_btn)

        toolbar.addStretch()

        self.save_btn = QPushButton("💾 Save")
        self.save_btn.setStyleSheet(_TOOLBAR_BTN_STYLE)
        toolbar.addWidget(self.save_btn)

        self.load_btn = QPushButton("📂 Load")
        self.load_btn.setStyleSheet(_TOOLBAR_BTN_STYLE)
        toolbar.addWidget(self.load_btn)

        root_layout.addLayout(toolbar)

        self.tree = DropAwareTreeWidget()
        self.tree.setHeaderLabels(["Step", "Type", "Summary"])
        self.tree.setColumnCount(3)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setAnimated(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setStyleSheet(_CANVAS_STYLE)

        self._delegate = SequenceItemDelegate(self.tree, self._node_map, self)
        self.tree.setItemDelegate(self._delegate)

        header = self.tree.header()
        header.setStretchLastSection(True)
        header.resizeSection(0, 80)
        header.resizeSection(1, 180)

        root_layout.addWidget(self.tree, 1)

        exec_bar = QHBoxLayout()
        exec_bar.setSpacing(8)

        self.run_btn = QPushButton("▶ Run")
        self.run_btn.setStyleSheet(_EXEC_BTN_STYLE.format(
            bg="#053b38", border="#08c9a5", fg="#10e7bc", hover="#064744"
        ))
        exec_bar.addWidget(self.run_btn)

        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setStyleSheet(_EXEC_BTN_STYLE.format(
            bg="#2d2400", border="#f2b705", fg="#f2d605", hover="#3d3200"
        ))
        self.pause_btn.setEnabled(False)
        exec_bar.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet(_EXEC_BTN_STYLE.format(
            bg="#3a0828", border="#d61b67", fg="#ffb7d3", hover="#4a0b31"
        ))
        self.stop_btn.setEnabled(False)
        exec_bar.addWidget(self.stop_btn)

        exec_bar.addStretch()

        root_layout.addLayout(exec_bar)

        self.tree.currentItemChanged.connect(self._on_current_changed)
        self.tree.external_node_dropped.connect(self._on_external_node_dropped)
        self.tree.instrument_dropped.connect(self._on_instrument_dropped)
        self.remove_btn.clicked.connect(self._on_remove)
        self.move_up_btn.clicked.connect(self._on_move_up)
        self.move_down_btn.clicked.connect(self._on_move_down)
        self.run_btn.clicked.connect(self.run_requested.emit)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        self.pause_btn.clicked.connect(self.pause_requested.emit)
        self.save_btn.clicked.connect(self._on_save)
        self.load_btn.clicked.connect(self._on_load)

    def _on_external_node_dropped(self, node_type: str) -> None:
        cls = get_node_class(node_type)
        if cls is None:
            return
        node = cls()
        self.add_node(node)

    def _on_instrument_dropped(self, instr_id: str, global_pos: QPoint) -> None:
        from ui.pages.custom_test.node_palette import get_instrument_by_id
        instr = get_instrument_by_id(instr_id)
        if instr is None:
            return

        operations = instr.get("operations", [])
        if not operations:
            return

        if len(operations) == 1:
            node_type = operations[0]["node_type"]
            cls = get_node_class(node_type)
            if cls:
                self.add_node(cls())
            return

        menu = QMenu(self)
        menu.setStyleSheet(_DROP_MENU_STYLE)

        title_action = menu.addAction(f"🔬 {instr['name']} — Select Operation")
        title_action.setEnabled(False)
        menu.addSeparator()

        for op in operations:
            cls = get_node_class(op["node_type"])
            icon_text = cls.icon if cls else "▸"
            action = menu.addAction(f"{icon_text}  {op['label']}")
            action.setData(op["node_type"])

        chosen = menu.exec(global_pos)
        if chosen and chosen.data():
            node_type = chosen.data()
            cls = get_node_class(node_type)
            if cls:
                self.add_node(cls())

    def add_node(self, node: BaseNode, parent_item: Optional[QTreeWidgetItem] = None) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setData(0, Qt.UserRole, node.uid)

        self._uid_map[node.uid] = item
        self._node_map[node.uid] = node

        if parent_item is not None:
            parent_item.addChild(item)
        else:
            current = self.tree.currentItem()
            if current:
                parent_uid = current.data(0, Qt.UserRole)
                parent_node = self._node_map.get(parent_uid)
                if parent_node and parent_node.accepts_children:
                    current.addChild(item)
                    parent_node.children.append(node)
                else:
                    parent = current.parent()
                    if parent:
                        idx = parent.indexOfChild(current)
                        parent.insertChild(idx + 1, item)
                        p_uid = parent.data(0, Qt.UserRole)
                        p_node = self._node_map.get(p_uid)
                        if p_node:
                            p_node.children.insert(idx + 1, node)
                    else:
                        idx = self.tree.indexOfTopLevelItem(current)
                        self.tree.insertTopLevelItem(idx + 1, item)
            else:
                self.tree.addTopLevelItem(item)

        for child_node in node.children:
            self.add_node(child_node, item)

        item.setExpanded(True)
        self.tree.setCurrentItem(item)
        self.sequence_changed.emit()
        return item

    def refresh_item(self, uid: str) -> None:
        item = self._uid_map.get(uid)
        if item:
            self.tree.viewport().update()

    def get_node(self, uid: str) -> Optional[BaseNode]:
        return self._node_map.get(uid)

    def get_sequence(self) -> List[BaseNode]:
        nodes: List[BaseNode] = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            uid = item.data(0, Qt.UserRole)
            node = self._node_map.get(uid)
            if node:
                self._sync_children_from_tree(item, node)
                nodes.append(node)
        return nodes

    def _sync_children_from_tree(self, item: QTreeWidgetItem, node: BaseNode) -> None:
        node.children.clear()
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_uid = child_item.data(0, Qt.UserRole)
            child_node = self._node_map.get(child_uid)
            if child_node:
                self._sync_children_from_tree(child_item, child_node)
                node.children.append(child_node)

    def clear_all(self) -> None:
        self.tree.clear()
        self._uid_map.clear()
        self._node_map.clear()
        self.sequence_changed.emit()

    def load_from_nodes(self, nodes: List[BaseNode]) -> None:
        self.clear_all()
        for node in nodes:
            self.add_node(node)
        self.tree.expandAll()

    def set_running_state(self, running: bool) -> None:
        self._running = running
        self.run_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.stop_btn.setEnabled(running)
        self.add_btn.setEnabled(not running)
        self.remove_btn.setEnabled(not running)
        self.move_up_btn.setEnabled(not running)
        self.move_down_btn.setEnabled(not running)
        self.load_btn.setEnabled(not running)

    def highlight_step(self, uid: str) -> None:
        item = self._uid_map.get(uid)
        if item:
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)

    def _on_current_changed(self, current: QTreeWidgetItem, previous: QTreeWidgetItem) -> None:
        if current is None:
            self.node_selected.emit(None)
            return
        uid = current.data(0, Qt.UserRole)
        node = self._node_map.get(uid)
        self.node_selected.emit(node)

    def _on_remove(self) -> None:
        current = self.tree.currentItem()
        if current is None:
            return
        uid = current.data(0, Qt.UserRole)

        parent = current.parent()
        if parent:
            parent_uid = parent.data(0, Qt.UserRole)
            parent_node = self._node_map.get(parent_uid)
            idx = parent.indexOfChild(current)
            parent.takeChild(idx)
            if parent_node:
                parent_node.children = [c for c in parent_node.children if c.uid != uid]
        else:
            idx = self.tree.indexOfTopLevelItem(current)
            self.tree.takeTopLevelItem(idx)

        self._remove_from_maps(uid, current)
        self.sequence_changed.emit()

    def _remove_from_maps(self, uid: str, item: QTreeWidgetItem) -> None:
        self._uid_map.pop(uid, None)
        self._node_map.pop(uid, None)
        for i in range(item.childCount()):
            child = item.child(i)
            child_uid = child.data(0, Qt.UserRole)
            if child_uid:
                self._remove_from_maps(child_uid, child)

    def _take_children(self, item: QTreeWidgetItem) -> List[QTreeWidgetItem]:
        children = []
        while item.childCount():
            children.append(item.takeChild(0))
        return children

    def _restore_children(self, item: QTreeWidgetItem, children: List[QTreeWidgetItem]) -> None:
        for child in children:
            item.addChild(child)

    def _swap_node_in_parent(self, parent_node: Optional[BaseNode],
                             old_idx: int, new_idx: int) -> None:
        if parent_node is not None and 0 <= old_idx < len(parent_node.children) \
                and 0 <= new_idx < len(parent_node.children):
            parent_node.children.insert(new_idx, parent_node.children.pop(old_idx))

    def _on_move_up(self) -> None:
        current = self.tree.currentItem()
        if current is None:
            return
        saved_children = self._take_children(current)
        parent = current.parent()
        if parent:
            idx = parent.indexOfChild(current)
            if idx <= 0:
                self._restore_children(current, saved_children)
                return
            parent.takeChild(idx)
            parent.insertChild(idx - 1, current)
            parent_uid = parent.data(0, Qt.UserRole)
            self._swap_node_in_parent(self._node_map.get(parent_uid), idx, idx - 1)
        else:
            idx = self.tree.indexOfTopLevelItem(current)
            if idx <= 0:
                self._restore_children(current, saved_children)
                return
            self.tree.takeTopLevelItem(idx)
            self.tree.insertTopLevelItem(idx - 1, current)
        self._restore_children(current, saved_children)
        current.setExpanded(True)
        self.tree.setCurrentItem(current)
        self.sequence_changed.emit()

    def _on_move_down(self) -> None:
        current = self.tree.currentItem()
        if current is None:
            return
        saved_children = self._take_children(current)
        parent = current.parent()
        if parent:
            idx = parent.indexOfChild(current)
            if idx >= parent.childCount() - 1:
                self._restore_children(current, saved_children)
                return
            parent.takeChild(idx)
            parent.insertChild(idx + 1, current)
            parent_uid = parent.data(0, Qt.UserRole)
            self._swap_node_in_parent(self._node_map.get(parent_uid), idx, idx + 1)
        else:
            idx = self.tree.indexOfTopLevelItem(current)
            if idx >= self.tree.topLevelItemCount() - 1:
                self._restore_children(current, saved_children)
                return
            self.tree.takeTopLevelItem(idx)
            self.tree.insertTopLevelItem(idx + 1, current)
        self._restore_children(current, saved_children)
        current.setExpanded(True)
        self.tree.setCurrentItem(current)
        self.sequence_changed.emit()

    def _on_save(self) -> None:
        nodes = self.get_sequence()
        data = [n.to_dict() for n in nodes]
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存序列", "", "JSON Files (*.json)"
        )
        if not filepath:
            return
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("序列已保存: %s", filepath)

    def _on_load(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "加载序列", "", "JSON Files (*.json)"
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            nodes = [BaseNode.from_dict(d) for d in data]
            self.load_from_nodes(nodes)
            logger.info("序列已加载: %s", filepath)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"无法加载序列文件:\n{e}")