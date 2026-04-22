"""Custom Test 主页面 —— 三栏布局可视化自定义测试序列编辑器"""

from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame,
    QLabel, QTableWidget, QTableWidgetItem, QTabWidget, QStackedLayout,
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
import pyqtgraph as pg

from ui.pages.custom_test.node_palette import NodePalette, CollapsibleSection
from ui.pages.custom_test.sequence_canvas import SequenceCanvas
from ui.pages.custom_test.property_panel import PropertyPanel
from ui.pages.custom_test.nodes.base_node import BaseNode, get_node_class
from ui.pages.custom_test.context import ExecutionContext
from ui.pages.custom_test.executor import ExecutorThread
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import VT6002ConnectionMixin
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.widgets.scrollbar import SCROLLBAR_STYLE
from log_config import get_logger

logger = get_logger(__name__)

_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "resources", "icons"
)

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_CHEVRON_DOWN_PATH = os.path.join(_ICONS_DIR, "chevron-down.svg").replace("\\", "/")


def _tinted_svg_icon(svg_path: str, color: str, size: int = 16) -> QIcon:
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
    return QIcon(pixmap)


_CONTEXT_MENU_STYLE = """
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

_PAGE_STYLE = """
    QWidget#customTestPage {
        background-color: #020618;
        border: none;
    }
    QSplitter::handle {
        background-color: #0b1428;
        width: 4px;
        border-radius: 2px;
    }
    QSplitter::handle:hover {
        background-color: #5b5cf6;
    }
    QFrame#sectionFrame {
        background-color: #09142e;
        border: 1px solid #1a2d57;
        border-radius: 14px;
    }
    QFrame#innerCard {
        background-color: #0b1933;
        border: none;
        border-radius: 10px;
    }
    QLabel#sectionTitle {
        font-size: 12px;
        font-weight: 700;
        color: #f4f7ff;
        background-color: transparent;
        padding: 0px;
        margin: 0px;
        border: none;
    }
    QLabel#fieldLabel {
        color: #8eb0e3;
        font-size: 11px;
        background-color: transparent;
        border: none;
    }
    QLabel#placeholderText {
        color: #3f5070;
        font-size: 11px;
        background-color: transparent;
        border: none;
    }
    QLabel#statusOk {
        color: #15d1a3;
        font-weight: 600;
        font-size: 11px;
        background-color: transparent;
        border: none;
    }
    QLabel#statusWarn {
        color: #ffb84d;
        font-weight: 600;
        font-size: 11px;
        background-color: transparent;
        border: none;
    }
    QLabel#statusErr {
        color: #ff5e7a;
        font-weight: 600;
        font-size: 11px;
        background-color: transparent;
        border: none;
    }
    QComboBox {
        background-color: #0a1733;
        color: #eaf2ff;
        border: 1px solid #27406f;
        border-radius: 8px;
        padding: 6px 10px;
    }
    QComboBox::drop-down {
        border: none;
        width: 22px;
        background: transparent;
    }
    QComboBox::down-arrow {
        image: url(""" + _CHEVRON_DOWN_PATH + """);
        width: 12px;
        height: 12px;
    }
    QComboBox QAbstractItemView {
        background-color: #0a1733;
        color: #eaf2ff;
        border: 1px solid #27406f;
        selection-background-color: #334a7d;
    }
    QTabWidget::pane {
        background-color: #060e20;
        border: 1px solid #1a2d57;
        border-radius: 6px;
    }
    QTabBar::tab {
        background-color: #0b1428;
        color: #5f78a8;
        padding: 6px 14px;
        border: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }
    QTabBar::tab:hover {
        background-color: #0f1c38;
        color: #8899bb;
    }
    QTabBar::tab:selected {
        background-color: #132040;
        color: #dce7ff;
        border-bottom: 2px solid #5b5cf6;
    }
    QTableWidget {
        background-color: #060e20;
        border: 1px solid #1a2d57;
        border-radius: 6px;
        color: #dce7ff;
        font-size: 11px;
        gridline-color: #1a2d57;
    }
    QTableWidget::item {
        padding: 2px 6px;
    }
    QTableWidget::item:selected {
        background-color: #1a2d57;
    }
    QHeaderView::section {
        background-color: #0b1428;
        color: #5f78a8;
        border: none;
        padding: 4px 6px;
        font-size: 11px;
        font-weight: 700;
    }
""" + SCROLLBAR_STYLE


class CustomTestUI(N6705CConnectionMixin, VT6002ConnectionMixin, QWidget):
    """Custom Test 主界面"""

    connection_status_changed = Signal(bool)
    vt6002_connection_changed = Signal(bool)

    def __init__(self, n6705c_top=None, mso64b_top=None,
                 vt6002_chamber_ui=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("customTestPage")
        self.setStyleSheet(_PAGE_STYLE)

        self._n6705c_top_ref = n6705c_top
        self._mso64b_top_ref = mso64b_top
        self._vt6002_chamber_ui_ref = vt6002_chamber_ui

        self.init_n6705c_connection(n6705c_top)
        self.init_vt6002_connection(vt6002_chamber_ui)

        self._n6705c_widgets_built = False
        self._vt6002_widgets_built = False
        self._i2c_interface = None

        self._executor_thread = ExecutorThread(self)
        self._context: Optional[ExecutionContext] = None

        self._build_ui()
        self._connect_signals()
        self._sync_instruments()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        main_splitter = QSplitter(Qt.Vertical)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setHandleWidth(6)

        left_panel = self._build_left_panel()
        top_splitter.addWidget(left_panel)

        center_frame = QFrame()
        center_frame.setObjectName("sectionFrame")
        center_layout = QVBoxLayout(center_frame)
        center_layout.setContentsMargins(12, 10, 12, 12)
        center_layout.setSpacing(6)
        center_title = QLabel("Sequence Canvas")
        center_title.setObjectName("sectionTitle")
        center_layout.addWidget(center_title)
        self.canvas = SequenceCanvas()
        center_layout.addWidget(self.canvas, 1)
        top_splitter.addWidget(center_frame)

        right_frame = QFrame()
        right_frame.setObjectName("sectionFrame")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(12, 10, 12, 12)
        right_layout.setSpacing(6)
        right_title = QLabel("Property Panel")
        right_title.setObjectName("sectionTitle")
        right_layout.addWidget(right_title)
        self.property_panel = PropertyPanel()
        right_layout.addWidget(self.property_panel, 1)
        top_splitter.addWidget(right_frame)

        top_splitter.setSizes([220, 520, 260])
        main_splitter.addWidget(top_splitter)

        bottom_widget = self._build_bottom_panel()
        main_splitter.addWidget(bottom_widget)

        main_splitter.setSizes([500, 280])
        root.addWidget(main_splitter)

    def _build_left_panel(self) -> QWidget:
        outer_frame = QFrame()
        outer_frame.setObjectName("sectionFrame")
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(12, 10, 12, 12)
        outer_layout.setSpacing(8)

        left_title = QLabel("Instruments / Nodes")
        left_title.setObjectName("sectionTitle")
        outer_layout.addWidget(left_title)

        link_svg = os.path.join(_ICONS_DIR, "activity.svg")
        self._conn_section = CollapsibleSection(
            "Instrument Connections",
            icon_svg=link_svg if os.path.isfile(link_svg) else None,
            expanded=False,
            parent=self,
        )

        self._instr_conn_frame = QWidget()
        self._instr_conn_frame.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._instr_conn_layout = QVBoxLayout(self._instr_conn_frame)
        self._instr_conn_layout.setContentsMargins(0, 0, 0, 0)
        self._instr_conn_layout.setSpacing(6)

        self._instr_conn_placeholder = QLabel("No instruments in sequence")
        self._instr_conn_placeholder.setObjectName("placeholderText")
        self._instr_conn_layout.addWidget(self._instr_conn_placeholder)

        self._conn_section.content_layout.addWidget(self._instr_conn_frame)
        outer_layout.addWidget(self._conn_section)

        self.palette = NodePalette()
        outer_layout.addWidget(self.palette, 1)

        return outer_frame

    def _get_used_instrument_ids(self) -> set:
        from ui.pages.custom_test.node_palette import INSTRUMENT_REGISTRY
        node_type_to_instr: Dict[str, str] = {}
        for instr in INSTRUMENT_REGISTRY:
            for op in instr.get("operations", []):
                node_type_to_instr[op["node_type"]] = instr["id"]

        used = set()

        def _scan_nodes(nodes):
            for node in nodes:
                instr_id = node_type_to_instr.get(node.node_type)
                if instr_id:
                    used.add(instr_id)
                if node.children:
                    _scan_nodes(node.children)

        sequence = self.canvas.get_sequence()
        _scan_nodes(sequence)
        return used

    def _refresh_instrument_connections(self) -> None:
        while self._instr_conn_layout.count() > 0:
            child = self._instr_conn_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

        used_ids = self._get_used_instrument_ids()
        used_ids.discard("i2c")

        self._n6705c_widgets_built = False
        self._vt6002_widgets_built = False

        if not used_ids:
            self._instr_conn_placeholder = QLabel("No instruments in sequence")
            self._instr_conn_placeholder.setObjectName("placeholderText")
            self._instr_conn_layout.addWidget(self._instr_conn_placeholder)
            return

        if "n6705c" in used_ids:
            lbl = QLabel("N6705C Power Analyzer")
            lbl.setObjectName("fieldLabel")
            self._instr_conn_layout.addWidget(lbl)
            title_row = QHBoxLayout()
            title_row.setSpacing(8)
            self.build_n6705c_connection_widgets(self._instr_conn_layout, title_row=title_row)
            self.bind_n6705c_signals()
            self._n6705c_widgets_built = True
            if self._n6705c_top_ref:
                self.sync_n6705c_from_top()

        if "vt6002" in used_ids:
            lbl = QLabel("VT6002 Chamber")
            lbl.setObjectName("fieldLabel")
            self._instr_conn_layout.addWidget(lbl)
            self.build_vt6002_connection_widgets(self._instr_conn_layout)
            self.bind_vt6002_signals()
            self._vt6002_widgets_built = True
            if self._vt6002_chamber_ui_ref and self._vt6002_chamber_ui_ref.vt6002:
                self._on_vt6002_external_changed()

        if "mso64b" in used_ids or "dsox4034a" in used_ids:
            lbl = QLabel("Oscilloscope")
            lbl.setObjectName("fieldLabel")
            self._instr_conn_layout.addWidget(lbl)
            self._scope_status = QLabel(
                "● Synced from main" if self._mso64b_top_ref else "● Not available"
            )
            self._scope_status.setObjectName(
                "statusOk" if self._mso64b_top_ref else "statusErr"
            )
            self._instr_conn_layout.addWidget(self._scope_status)

        if "cmw270" in used_ids:
            lbl = QLabel("CMW270 RF Analyzer")
            lbl.setObjectName("fieldLabel")
            self._instr_conn_layout.addWidget(lbl)
            status = QLabel("● Not implemented")
            status.setObjectName("statusWarn")
            self._instr_conn_layout.addWidget(status)

    def _build_bottom_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("bottomPanel")
        widget.setStyleSheet("QWidget#bottomPanel { background: transparent; border: none; }")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        tabs = QTabWidget()

        log_icon_path = os.path.join(_ICONS_DIR, "clipboard-list.svg")
        table_icon_path = os.path.join(_ICONS_DIR, "table.svg")
        chart_icon_path = os.path.join(_ICONS_DIR, "line-chart.svg")

        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.logs_frame = ExecutionLogsFrame(
            title="⊙ Execution Logs", show_progress=True
        )
        log_layout.addWidget(self.logs_frame)
        tabs.addTab(log_tab, "Logs")
        if os.path.isfile(log_icon_path):
            tabs.setTabIcon(0, _tinted_svg_icon(log_icon_path, "#5f78a8"))
            tabs.setIconSize(QSize(14, 14))

        table_tab = QWidget()
        table_tab_layout = QVBoxLayout(table_tab)
        table_tab_layout.setContentsMargins(0, 0, 0, 0)

        self._table_stack = QWidget()
        stack_layout = QStackedLayout(self._table_stack)
        stack_layout.setStackingMode(QStackedLayout.StackAll)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(0)
        self.result_table.setRowCount(0)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        stack_layout.addWidget(self.result_table)

        self._table_empty_label = QLabel("No data recorded yet")
        self._table_empty_label.setAlignment(Qt.AlignCenter)
        self._table_empty_label.setObjectName("placeholderText")
        stack_layout.addWidget(self._table_empty_label)
        stack_layout.setCurrentIndex(1)

        table_tab_layout.addWidget(self._table_stack)
        tabs.addTab(table_tab, "Data")
        if os.path.isfile(table_icon_path):
            tabs.setTabIcon(1, _tinted_svg_icon(table_icon_path, "#5f78a8"))

        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#060e20")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setLabel("bottom", "Index", color="#5f78a8")
        self.plot_widget.setLabel("left", "Value", color="#5f78a8")
        axis_pen = pg.mkPen(color="#1a2d57", width=1)
        for axis_name in ("bottom", "left"):
            ax = self.plot_widget.getAxis(axis_name)
            ax.setPen(axis_pen)
            ax.setTextPen(pg.mkPen(color="#5f78a8"))
        self.plot_widget.addLegend(offset=(-10, 10))
        chart_layout.addWidget(self.plot_widget)
        tabs.addTab(chart_tab, "Chart")
        if os.path.isfile(chart_icon_path):
            tabs.setTabIcon(2, _tinted_svg_icon(chart_icon_path, "#5f78a8"))

        layout.addWidget(tabs)
        return widget

    def _connect_signals(self) -> None:
        self.palette.node_requested.connect(self._on_add_node)
        self.palette.instrument_requested.connect(self._on_instrument_requested)
        self.canvas.add_btn.clicked.connect(self._on_add_btn_clicked)
        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.run_requested.connect(self._on_run)
        self.canvas.stop_requested.connect(self._on_stop)
        self.canvas.pause_requested.connect(self._on_pause)
        self.canvas.sequence_changed.connect(self._refresh_instrument_connections)

        self.property_panel.param_changed.connect(self._on_param_changed)
        self.property_panel.add_else_if_requested.connect(self._on_add_else_if)

        self._executor_thread.finished.connect(self._on_execution_finished)

    def _sync_instruments(self) -> None:
        if self._n6705c_top_ref:
            self.sync_n6705c_from_top()
        if self._vt6002_chamber_ui_ref and self._vt6002_chamber_ui_ref.vt6002:
            self._on_vt6002_external_changed()

    def _on_vt6002_external_changed(self) -> None:
        if not self._vt6002_widgets_built:
            if self._vt6002_chamber_ui_ref and self._vt6002_chamber_ui_ref.vt6002:
                from instruments.mock.mock_instruments import MockVT6002
                vt = self._vt6002_chamber_ui_ref.vt6002
                is_open = isinstance(vt, MockVT6002) or (hasattr(vt, 'ser') and vt.ser.is_open)
                if is_open:
                    self.vt6002 = vt
                    self.is_vt6002_connected = True
            return
        super()._on_vt6002_external_changed()

    def sync_n6705c_from_top(self) -> None:
        if not self._n6705c_widgets_built:
            if self._n6705c_top_ref and hasattr(self._n6705c_top_ref, 'is_connected_a'):
                if self._n6705c_top_ref.is_connected_a and self._n6705c_top_ref.n6705c_a:
                    self.n6705c = self._n6705c_top_ref.n6705c_a
                    self.is_connected = True
            return
        super().sync_n6705c_from_top()

    def _on_add_node(self, node_type: str) -> None:
        """从面板添加节点"""
        cls = get_node_class(node_type)
        if cls is None:
            self.logs_frame.append_log(f"[ERROR] 未知节点类型: {node_type}")
            return
        node = cls()
        self.canvas.add_node(node)

    def _on_add_btn_clicked(self) -> None:
        """工具栏 Add 按钮"""
        from PySide6.QtWidgets import QMenu
        from ui.pages.custom_test.nodes.base_node import get_nodes_by_category
        from ui.pages.custom_test.node_palette import INSTRUMENT_REGISTRY

        menu = QMenu(self)
        menu.setStyleSheet(_CONTEXT_MENU_STYLE)

        microscope_path = os.path.join(_ICONS_DIR, "microscope.svg")
        instr_icon = _tinted_svg_icon(microscope_path, "#dce7ff") if os.path.isfile(microscope_path) else QIcon()
        instr_submenu = menu.addMenu(instr_icon, "Instruments")
        instr_submenu.setStyleSheet(_CONTEXT_MENU_STYLE)
        for instr in INSTRUMENT_REGISTRY:
            sub = instr_submenu.addMenu(f"{instr['name']}")
            sub.setStyleSheet(_CONTEXT_MENU_STYLE)
            for op in instr["operations"]:
                cls = get_node_class(op["node_type"])
                icon_text = cls.icon if cls else "▸"
                action = sub.addAction(f"{icon_text} {op['label']}")
                action.triggered.connect(
                    lambda checked=False, nt=op["node_type"]: self._on_add_node(nt)
                )
        menu.addSeparator()

        for cat in ["value", "logic", "io"]:
            nodes = get_nodes_by_category(cat)
            for node_cls in nodes:
                action = menu.addAction(f"{node_cls.icon} {node_cls.display_name}")
                action.triggered.connect(
                    lambda checked=False, nt=node_cls.node_type: self._on_add_node(nt)
                )
            menu.addSeparator()
        menu.exec(self.canvas.add_btn.mapToGlobal(self.canvas.add_btn.rect().bottomLeft()))

    def _on_instrument_requested(self, instr_id: str) -> None:
        """仪器双击回调：弹出操作选择菜单"""
        from PySide6.QtWidgets import QMenu, QCursor
        from ui.pages.custom_test.node_palette import get_instrument_by_id

        instr = get_instrument_by_id(instr_id)
        if instr is None:
            return

        operations = instr.get("operations", [])
        if not operations:
            return

        if len(operations) == 1:
            self._on_add_node(operations[0]["node_type"])
            return

        menu = QMenu(self)
        menu.setStyleSheet(_CONTEXT_MENU_STYLE)

        microscope_path = os.path.join(_ICONS_DIR, "microscope.svg")
        title_icon = _tinted_svg_icon(microscope_path, "#5f78a8") if os.path.isfile(microscope_path) else QIcon()
        title_action = menu.addAction(title_icon, f"{instr['name']} — Select Operation")
        title_action.setEnabled(False)
        menu.addSeparator()

        for op in operations:
            cls = get_node_class(op["node_type"])
            icon_text = cls.icon if cls else "▸"
            action = menu.addAction(f"{icon_text}  {op['label']}")
            action.triggered.connect(
                lambda checked=False, nt=op["node_type"]: self._on_add_node(nt)
            )

        menu.exec(QCursor.pos())

    def _on_node_selected(self, node: Optional[BaseNode]) -> None:
        """节点选中回调"""
        self.property_panel.set_node(node)

    def _on_param_changed(self, uid: str, key: str, value: Any) -> None:
        """参数变更回调"""
        self.canvas.refresh_item(uid)

    def _on_add_else_if(self, uid: str) -> None:
        from ui.pages.custom_test.nodes.logic_nodes import (
            IfBlock, IfBranch, ElseIfBranch, ElseBranch,
        )
        node = self.canvas._node_map.get(uid)
        tree_item = self.canvas._uid_map.get(uid)
        if node is None or tree_item is None:
            return

        if isinstance(node, IfBranch):
            parent_item = tree_item.parent()
            if parent_item is None:
                return
            parent_uid = parent_item.data(0, Qt.UserRole)
            block_node = self.canvas._node_map.get(parent_uid)
            if not isinstance(block_node, IfBlock):
                return
            block_item = parent_item
        elif isinstance(node, IfBlock):
            block_node = node
            block_item = tree_item
        else:
            return

        insert_idx = block_node.children.__len__()
        for i, child in enumerate(block_node.children):
            if isinstance(child, ElseBranch):
                insert_idx = i
                break

        new_branch = ElseIfBranch()
        new_branch.params["condition"] = "${value} > 0"
        block_node.children.insert(insert_idx, new_branch)
        self.canvas.add_node(new_branch, block_item, _batch=True)

        branch_item = self.canvas._uid_map.get(new_branch.uid)
        if branch_item:
            block_item.removeChild(branch_item)
            block_item.insertChild(insert_idx, branch_item)

        block_item.setExpanded(True)
        self.canvas.tree.setCurrentItem(branch_item or tree_item)
        self.canvas.sequence_changed.emit()

    def _on_run(self) -> None:
        sequence = self.canvas.get_sequence()
        if not sequence:
            self.logs_frame.append_log("[WARN] 序列为空，请先添加节点")
            return

        used_ids = self._get_used_instrument_ids()

        self._context = ExecutionContext()
        if "n6705c" in used_ids:
            self._context.instruments["n6705c"] = self.n6705c
        if "vt6002" in used_ids:
            self._context.instruments["chamber"] = self.vt6002
        if ("mso64b" in used_ids or "dsox4034a" in used_ids) \
                and self._mso64b_top_ref and self._mso64b_top_ref.is_connected:
            self._context.instruments["scope"] = self._mso64b_top_ref.mso64b

        if "i2c" in used_ids:
            if self._i2c_interface is None:
                try:
                    from lib.i2c.i2c_interface_x64 import I2CInterface
                    i2c = I2CInterface()
                    if i2c.initialize():
                        self._i2c_interface = i2c
                        logger.info("[I2C] Auto-connected for execution.")
                    else:
                        logger.error("[I2C] Auto-init failed")
                except Exception as e:
                    logger.error("[I2C] Auto-connect error: %s", e)
            if self._i2c_interface is not None:
                self._context.instruments["i2c"] = self._i2c_interface

        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self._table_empty_label.setVisible(True)
        self.plot_widget.clear()
        self._plot_curves = {}
        self._plot_data = {}

        self.canvas.set_running_state(True)
        self.logs_frame.set_progress(0)
        self.logs_frame.clear_log()

        executor = self._executor_thread.start(sequence, self._context)

        executor.log_message.connect(self.logs_frame.append_log)
        executor.progress_updated.connect(self._on_progress)
        executor.step_started.connect(self._on_step_started)
        executor.data_recorded.connect(self._on_data_recorded)

    def _on_stop(self) -> None:
        """停止执行"""
        self._executor_thread.stop()
        self.logs_frame.append_log("[USER] 执行停止请求已发送")

    def _on_pause(self) -> None:
        """暂停/恢复"""
        if self._executor_thread.executor:
            ctx = self._executor_thread.executor.context
            if ctx and ctx.should_pause:
                ctx.request_resume()
                self.canvas.pause_btn.setText("∥ Pause")
                self.logs_frame.append_log("[USER] 已恢复执行")
            elif ctx:
                ctx.request_pause()
                self.canvas.pause_btn.setText("▶ Resume")
                self.logs_frame.append_log("[USER] 已暂停执行")

    def _on_progress(self, current: int, total: int) -> None:
        """进度更新"""
        if total > 0:
            pct = int(current / total * 100)
            self.logs_frame.set_progress(pct)

    def _on_step_started(self, uid: str, name: str) -> None:
        """步骤开始"""
        self.canvas.highlight_step(uid)

    def _on_data_recorded(self, row: Dict[str, Any]) -> None:
        """数据记录回调 —— 更新表格和图表"""
        if not row:
            return

        self._table_empty_label.setVisible(False)

        keys = list(row.keys())
        if self.result_table.columnCount() == 0:
            self.result_table.setColumnCount(len(keys))
            self.result_table.setHorizontalHeaderLabels(keys)

        row_idx = self.result_table.rowCount()
        self.result_table.insertRow(row_idx)
        for col, key in enumerate(keys):
            val = row.get(key, "")
            item = QTableWidgetItem(str(val))
            self.result_table.setItem(row_idx, col, item)

        for key, val in row.items():
            try:
                fval = float(val)
            except (ValueError, TypeError):
                continue

            if key not in self._plot_data:
                self._plot_data[key] = []
                pen_colors = ["#5b5cf6", "#f2994a", "#27ae60", "#e74c3c", "#9b59b6",
                              "#16a085", "#f39c12", "#2ecc71"]
                color = pen_colors[len(self._plot_curves) % len(pen_colors)]
                self._plot_curves[key] = self.plot_widget.plot(
                    [], [], pen=pg.mkPen(color=color, width=2), name=key
                )
            self._plot_data[key].append(fval)
            curve = self._plot_curves[key]
            x_data = list(range(len(self._plot_data[key])))
            curve.setData(x_data, self._plot_data[key])

    def _on_execution_finished(self, success: bool, message: str) -> None:
        """执行完成回调"""
        self.canvas.set_running_state(False)
        self.canvas.pause_btn.setText("∥ Pause")

        if success and self._context and self._context.records:
            self._auto_export_csv()

    def _auto_export_csv(self) -> None:
        """自动导出 CSV"""
        if not self._context or not self._context.records:
            return

        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(project_root, "Results", "custom_test", timestamp)
        os.makedirs(output_dir, exist_ok=True)

        import csv
        records = self._context.records
        all_keys = []
        seen = set()
        for r in records:
            for k in r.keys():
                if k not in seen:
                    all_keys.append(k)
                    seen.add(k)

        filepath = os.path.join(output_dir, "custom_test_result.csv")
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(records)

        self.logs_frame.append_log(f"[EXPORT] CSV 已自动导出: {filepath}")

    def load_template(self, template_name: str) -> None:
        """加载内置模板"""
        filepath = os.path.join(_TEMPLATES_DIR, template_name)
        if not os.path.isfile(filepath):
            self.logs_frame.append_log(f"[ERROR] 模板文件不存在: {filepath}")
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            nodes = [BaseNode.from_dict(d) for d in data]
            self.canvas.load_from_nodes(nodes)
            self.logs_frame.append_log(f"[TEMPLATE] 已加载模板: {template_name}")
        except Exception as e:
            self.logs_frame.append_log(f"[ERROR] 加载模板失败: {e}")

    def append_log(self, message: str) -> None:
        """统一的日志接口"""
        self.logs_frame.append_log(message)

    def cleanup_threads(self) -> None:
        """清理工作线程"""
        self._executor_thread.stop()
        if self._i2c_interface is not None:
            self._i2c_interface.close()
            self._i2c_interface = None
