"""中栏：序列画布（基于 QTreeWidget 的可视化测试流程）"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QMenu, QFileDialog, QMessageBox, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QAction

from ui.pages.custom_test.nodes.base_node import BaseNode, get_node_class
from log_config import get_logger

logger = get_logger(__name__)

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
        padding: 4px 6px;
        border-radius: 4px;
        min-height: 28px;
    }
    QTreeWidget::item:selected {
        background-color: #1a2d57;
        color: #ffffff;
    }
    QTreeWidget::item:hover {
        background-color: #0f1c38;
    }
    QTreeWidget::branch {
        background: transparent;
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

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Step", "Type", "Summary"])
        self.tree.setColumnCount(3)
        self.tree.setRootIsDecorated(True)
        self.tree.setAnimated(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setStyleSheet(_CANVAS_STYLE)
        self.tree.setAcceptDrops(True)

        header = self.tree.header()
        header.setStretchLastSection(True)
        header.resizeSection(0, 40)
        header.resizeSection(1, 140)

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
        self.remove_btn.clicked.connect(self._on_remove)
        self.move_up_btn.clicked.connect(self._on_move_up)
        self.move_down_btn.clicked.connect(self._on_move_down)
        self.run_btn.clicked.connect(self.run_requested.emit)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        self.pause_btn.clicked.connect(self.pause_requested.emit)
        self.save_btn.clicked.connect(self._on_save)
        self.load_btn.clicked.connect(self._on_load)

    def add_node(self, node: BaseNode, parent_item: Optional[QTreeWidgetItem] = None) -> QTreeWidgetItem:
        """添加节点到树"""
        item = QTreeWidgetItem()
        self._update_item_display(item, node)
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

    def _update_item_display(self, item: QTreeWidgetItem, node: BaseNode) -> None:
        """更新树节点的显示"""
        item.setText(0, node.icon)
        item.setText(1, node.display_name)
        summary_parts = []
        for k, v in node.params.items():
            summary_parts.append(f"{k}={v}")
        item.setText(2, ", ".join(summary_parts[:3]))
        item.setForeground(1, QColor(node.color))

    def refresh_item(self, uid: str) -> None:
        """刷新指定节点的显示"""
        item = self._uid_map.get(uid)
        node = self._node_map.get(uid)
        if item and node:
            self._update_item_display(item, node)

    def get_node(self, uid: str) -> Optional[BaseNode]:
        """根据 uid 获取节点"""
        return self._node_map.get(uid)

    def get_sequence(self) -> List[BaseNode]:
        """获取顶层节点列表（完整树结构）"""
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
        """从树的 UI 结构同步子节点顺序到 node.children"""
        node.children.clear()
        for i in range(item.childCount()):
            child_item = item.child(i)
            child_uid = child_item.data(0, Qt.UserRole)
            child_node = self._node_map.get(child_uid)
            if child_node:
                self._sync_children_from_tree(child_item, child_node)
                node.children.append(child_node)

    def clear_all(self) -> None:
        """清空所有节点"""
        self.tree.clear()
        self._uid_map.clear()
        self._node_map.clear()
        self.sequence_changed.emit()

    def load_from_nodes(self, nodes: List[BaseNode]) -> None:
        """从节点列表加载序列"""
        self.clear_all()
        for node in nodes:
            self.add_node(node)
        self.tree.expandAll()

    def set_running_state(self, running: bool) -> None:
        """设置运行状态"""
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
        """高亮当前正在执行的步骤"""
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
        """递归从映射中删除节点"""
        self._uid_map.pop(uid, None)
        self._node_map.pop(uid, None)
        for i in range(item.childCount()):
            child = item.child(i)
            child_uid = child.data(0, Qt.UserRole)
            if child_uid:
                self._remove_from_maps(child_uid, child)

    def _on_move_up(self) -> None:
        current = self.tree.currentItem()
        if current is None:
            return
        parent = current.parent()
        if parent:
            idx = parent.indexOfChild(current)
            if idx <= 0:
                return
            parent.takeChild(idx)
            parent.insertChild(idx - 1, current)
        else:
            idx = self.tree.indexOfTopLevelItem(current)
            if idx <= 0:
                return
            self.tree.takeTopLevelItem(idx)
            self.tree.insertTopLevelItem(idx - 1, current)
        self.tree.setCurrentItem(current)
        self.sequence_changed.emit()

    def _on_move_down(self) -> None:
        current = self.tree.currentItem()
        if current is None:
            return
        parent = current.parent()
        if parent:
            idx = parent.indexOfChild(current)
            if idx >= parent.childCount() - 1:
                return
            parent.takeChild(idx)
            parent.insertChild(idx + 1, current)
        else:
            idx = self.tree.indexOfTopLevelItem(current)
            if idx >= self.tree.topLevelItemCount() - 1:
                return
            self.tree.takeTopLevelItem(idx)
            self.tree.insertTopLevelItem(idx + 1, current)
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
