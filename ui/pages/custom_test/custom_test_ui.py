"""Custom Test 主页面 —— 三栏布局可视化自定义测试序列编辑器"""

from __future__ import annotations

import os
import threading
import time
from ui.resource_path import get_resource_base
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame,
    QLabel, QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer

from ui.pages.custom_test.node_palette import NodePalette, CollapsibleSection
from ui.pages.custom_test.sequence_canvas import SequenceCanvas
from ui.pages.custom_test.sequence_io import load_sequence_file
from ui.pages.custom_test.property_panel import PropertyPanel
from core.custom_test.nodes.base import BaseNode, get_node_class
from ui.pages.custom_test.node_metadata import filter_selectable_ops, is_node_selectable
from core.custom_test.context import ExecutionContext, StopExecution
from core.custom_test.executor import ExecutorThread
from core.custom_test.resolver import InstrumentResolver, collect_required_instrument_keys
from core.custom_test.result_store import ResultStore, build_default_result_path
from core.custom_test.validation import preflight_validate
from ui.pages.custom_test.instrument_connection_panel import InstrumentConnectionPanel
from ui.pages.custom_test.result_panel import ResultPanel
from ui.pages.custom_test.validation_panel import ValidationIssuesDialog
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import ChamberConnectionMixin
from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin, MODE_FULL
from ui.widgets.scrollbar import SCROLLBAR_STYLE
from log_config import get_logger

logger = get_logger(__name__)

_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "custom_test_SVGs"
)

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_CHEVRON_DOWN_PATH = os.path.join(_PAGE_SVGS_DIR, "chevron-down.svg").replace("\\", "/")

from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon


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
    QFrame {
        border: none;
        background-color: transparent;
    }
    QSplitter::handle {
        background-color: transparent;
        width: 3px;
        height: 4px;
        border-radius: 0px;
    }
    QSplitter::handle:hover {
        background-color: #18284d;
    }
    QSplitter::handle:pressed {
        background-color: #5b7cff;
    }
    QFrame#sectionFrame {
        background-color: #09142e;
        border: none;
        border-radius: 12px;
    }
    QFrame#regionFrame {
        background-color: #08122a;
        border: 1px solid #1a2d57;
        border-radius: 12px;
    }
    QFrame#regionFrame:hover {
        border: 1px solid #27406f;
    }
    QSplitter#workspaceSplitter::handle {
        background-color: transparent;
    }
    QSplitter#workspaceSplitter::handle:horizontal {
        width: 4px;
        background-color: transparent;
    }
    QSplitter#workspaceSplitter::handle:horizontal:hover {
        background-color: transparent;
    }
    QFrame#innerCard {
        background-color: #0b1933;
        border: none;
        border-radius: 12px;
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
    QLabel#pageTitle {
        font-size: 18px;
        font-weight: 700;
        color: #f8fbff;
        background-color: transparent;
        border: none;
    }
    QLabel#pageSubtitle {
        font-size: 12px;
        color: #7da2d6;
        background-color: transparent;
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
        background-color: transparent;
        border: none;
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
        border-right: 1px solid #1a2d57;
        padding: 4px 6px;
        font-size: 11px;
        font-weight: 700;
    }
    QHeaderView::section:hover {
        background-color: #112040;
        color: #8eb0e3;
    }
    QHeaderView::section:pressed {
        background-color: #1a2d57;
    }
    QTableCornerButton::section {
        background-color: #0b1428;
        border: none;
        border-right: 1px solid #1a2d57;
        border-bottom: 1px solid #1a2d57;
    }
    QTableCornerButton::section:hover {
        background-color: #112040;
    }
""" + SCROLLBAR_STYLE


class _PromptRequest:
    def __init__(self, message: str, timeout_s: float) -> None:
        self.message = message
        self.timeout_s = max(0.0, float(timeout_s))
        self.response: Optional[str] = None
        self.reason = ""
        self.cancelled = False
        self.timed_out = False
        self._event = threading.Event()
        self._lock = threading.Lock()

    def set_response(self, response: str) -> None:
        with self._lock:
            if self._event.is_set():
                return
            self.response = response
            self._event.set()

    def cancel(self, reason: str = "") -> None:
        with self._lock:
            if self._event.is_set():
                return
            self.cancelled = True
            self.reason = reason
            self._event.set()

    def timeout(self) -> None:
        with self._lock:
            if self._event.is_set():
                return
            self.timed_out = True
            self.reason = "PromptUser 等待超时"
            self._event.set()

    def wait(self, timeout_s: float) -> bool:
        return self._event.wait(timeout_s)

    @property
    def is_done(self) -> bool:
        return self._event.is_set()


class CustomTestUI(N6705CConnectionMixin, ChamberConnectionMixin, SerialComMixin, QWidget):
    """Custom Test 主界面"""

    connection_status_changed = Signal(bool)
    chamber_connection_changed = Signal(bool)
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)
    prompt_requested = Signal(object)

    def __init__(self, n6705c_top=None, mso64b_top=None,
                 chamber_ui=None, instrument_manager=None, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("customTestPage")
        self.setStyleSheet(_PAGE_STYLE)

        self._n6705c_top_ref = n6705c_top
        self._mso64b_top_ref = mso64b_top
        self._chamber_ui_ref = chamber_ui
        self._instrument_manager = instrument_manager

        self.init_n6705c_connection(n6705c_top)
        self.init_chamber_connection(chamber_ui, instrument_manager=instrument_manager)
        self.init_serial_connection(mode=MODE_FULL, baudrate=115200, prefix="UART")

        self._n6705c_widgets_built = False
        self._chamber_widgets_built = False
        self._uart_widgets_built = False
        self._mcu_io_widgets_built = False
        self.mcu_io = None
        self.is_mcu_io_connected = False
        self._i2c_interface = None

        self._executor_thread = ExecutorThread(self)
        self._context: Optional[ExecutionContext] = None
        self._result_store = ResultStore()
        self._active_prompt_box: Optional[QMessageBox] = None
        self._active_prompt_request: Optional[_PromptRequest] = None

        self._build_ui()
        self._connect_signals()
        self._sync_instruments()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title_icon_label = QLabel()
        title_icon_label.setFixedSize(22, 22)
        title_icon_label.setAlignment(Qt.AlignCenter)
        title_icon_label.setStyleSheet("background: transparent; border: none;")
        network_icon_path = os.path.join(_PAGE_SVGS_DIR, "network.svg")
        if os.path.isfile(network_icon_path):
            icon_pixmap = QPixmap(22, 22)
            icon_pixmap.fill(Qt.transparent)
            painter = QPainter(icon_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            QSvgRenderer(network_icon_path).render(painter)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(icon_pixmap.rect(), QColor("#6366f1"))
            painter.end()
            title_icon_label.setPixmap(icon_pixmap)
        title_row.addWidget(title_icon_label)

        self.page_title = QLabel("Custom Test")
        self.page_title.setObjectName("pageTitle")
        title_row.addWidget(self.page_title)
        title_row.addStretch(1)

        self.page_subtitle = QLabel("Build and run custom test sequences with visual node-based editor.")
        self.page_subtitle.setObjectName("pageSubtitle")
        header_layout.addLayout(title_row)
        header_layout.addWidget(self.page_subtitle)
        root.addLayout(header_layout)

        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setHandleWidth(5)
        main_splitter.setChildrenCollapsible(False)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setObjectName("workspaceSplitter")
        top_splitter.setHandleWidth(5)
        top_splitter.setChildrenCollapsible(False)

        left_panel = self._build_left_panel()
        top_splitter.addWidget(left_panel)

        self.canvas = SequenceCanvas()
        canvas_region = QFrame()
        canvas_region.setObjectName("regionFrame")
        canvas_region.setMinimumWidth(300)
        canvas_region_layout = QVBoxLayout(canvas_region)
        canvas_region_layout.setContentsMargins(6, 6, 6, 6)
        canvas_region_layout.setSpacing(0)
        canvas_region_layout.addWidget(self.canvas)
        top_splitter.addWidget(canvas_region)

        self.property_panel = PropertyPanel()
        self.property_panel.set_canvas(self.canvas)
        property_region = QFrame()
        property_region.setObjectName("regionFrame")
        property_region.setMinimumWidth(200)
        property_region_layout = QVBoxLayout(property_region)
        property_region_layout.setContentsMargins(6, 6, 6, 6)
        property_region_layout.setSpacing(0)
        property_region_layout.addWidget(self.property_panel)
        top_splitter.addWidget(property_region)

        top_splitter.setSizes([220, 520, 260])
        main_splitter.addWidget(top_splitter)

        bottom_region = QFrame()
        bottom_region.setObjectName("regionFrame")
        bottom_region_layout = QVBoxLayout(bottom_region)
        bottom_region_layout.setContentsMargins(8, 8, 8, 8)
        bottom_region_layout.setSpacing(0)
        bottom_widget = self._build_bottom_panel()
        bottom_region_layout.addWidget(bottom_widget)
        main_splitter.addWidget(bottom_region)

        main_splitter.setSizes([500, 280])
        root.addWidget(main_splitter)

    def _build_left_panel(self) -> QWidget:
        outer_frame = QFrame()
        outer_frame.setObjectName("sectionFrame")
        outer_frame.setMinimumWidth(220)
        outer_layout = QVBoxLayout(outer_frame)
        outer_layout.setContentsMargins(6, 10, 2, 12)
        outer_layout.setSpacing(8)

        left_title = QLabel("Instruments / Nodes")
        left_title.setObjectName("sectionTitle")
        outer_layout.addWidget(left_title)

        link_svg = os.path.join(_PAGE_SVGS_DIR, "activity.svg")
        self._conn_section = CollapsibleSection(
            "Instrument Connections",
            icon_svg=link_svg if os.path.isfile(link_svg) else None,
            expanded=False,
            parent=self,
        )

        self.instrument_panel = InstrumentConnectionPanel(self, parent=self)
        self._conn_section.content_layout.addWidget(self.instrument_panel)

        self.palette = NodePalette()
        self.palette.insert_top_widget(self._conn_section)
        outer_layout.addWidget(self.palette, 1)

        return outer_frame

    def _get_used_instrument_ids(self) -> set:
        return collect_required_instrument_keys(self.canvas.get_sequence())

    def _refresh_instrument_connections(self) -> None:
        self.instrument_panel.refresh(self._get_used_instrument_ids())

    def _collect_instrument_meta(self) -> dict:
        return self.instrument_panel.collect_meta()

    def _on_metadata_loaded(self, meta: dict) -> None:
        self.instrument_panel.on_metadata_loaded(meta)

    def _apply_instrument_meta(self) -> None:
        self.instrument_panel.apply_instrument_meta()

    def _try_auto_connect_instruments(self, meta: dict) -> None:
        self.instrument_panel._try_auto_connect_instruments(meta)

    def _build_bottom_panel(self) -> QWidget:
        self.result_panel = ResultPanel(self._result_store, parent=self)
        self.logs_frame = self.result_panel.logs_frame
        return self.result_panel

    def _connect_signals(self) -> None:
        self.palette.node_requested.connect(self._on_add_node)
        self.palette.instrument_requested.connect(self._on_instrument_requested)
        self.canvas.add_btn.clicked.connect(self._on_add_btn_clicked)
        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.run_requested.connect(self._on_run)
        self.canvas.stop_requested.connect(self._on_stop)
        self.canvas.pause_requested.connect(self._on_pause)
        self.canvas.sequence_changed.connect(self._refresh_instrument_connections)
        self.canvas.metadata_loaded.connect(self._on_metadata_loaded)
        self.canvas._collect_instrument_meta = self._collect_instrument_meta

        self.property_panel.param_changed.connect(self._on_param_changed)
        self.property_panel.add_else_if_requested.connect(self._on_add_else_if)

        self._executor_thread.finished.connect(self._on_execution_finished)
        self.prompt_requested.connect(self._on_prompt_requested, Qt.QueuedConnection)

        if self._instrument_manager is not None:
            self._instrument_manager.scan_finished.connect(self.instrument_panel.on_manager_scan_finished)
            self._instrument_manager.scan_failed.connect(self.instrument_panel.on_manager_scan_failed)
            self._instrument_manager.session_connected.connect(self.instrument_panel.on_manager_session_connected)
            self._instrument_manager.connection_failed.connect(self.instrument_panel.on_manager_connection_failed)
            self._instrument_manager.session_disconnected.connect(self.instrument_panel.on_manager_session_disconnected)

    def _sync_instruments(self) -> None:
        self.instrument_panel.sync_external()

    def _sync_n6705c_from_top_mixin(self) -> None:
        N6705CConnectionMixin.sync_n6705c_from_top(self)

    def _on_chamber_external_changed_mixin(self) -> None:
        ChamberConnectionMixin._on_chamber_external_changed(self)

    def _on_chamber_external_changed(self) -> None:
        self.instrument_panel.on_chamber_external_changed()

    def sync_n6705c_from_top(self) -> None:
        self.instrument_panel.sync_n6705c_from_top()

    def _on_add_node(self, node_type: str) -> None:
        """从面板添加节点"""
        if not is_node_selectable(node_type):
            self.logs_frame.append_log(f"[WARN] 节点暂不可用或仅用于兼容加载: {node_type}")
            return
        cls = get_node_class(node_type)
        if cls is None:
            self.logs_frame.append_log(f"[ERROR] 未知节点类型: {node_type}")
            return
        node = cls()
        self.canvas.add_node(node)

    def _on_add_btn_clicked(self) -> None:
        """工具栏 Add 按钮"""
        from PySide6.QtWidgets import QMenu
        from core.custom_test.nodes.base import get_nodes_by_category
        from ui.pages.custom_test.node_palette import INSTRUMENT_REGISTRY

        menu = QMenu(self)
        menu.setStyleSheet(_CONTEXT_MENU_STYLE)

        microscope_path = os.path.join(_PAGE_SVGS_DIR, "microscope.svg")
        instr_icon = _tinted_svg_icon(microscope_path, "#dce7ff") if os.path.isfile(microscope_path) else QIcon()
        instr_submenu = menu.addMenu(instr_icon, "Instruments")
        instr_submenu.setStyleSheet(_CONTEXT_MENU_STYLE)
        _cat_icons_add = {
            "Config": _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "settings.svg"), "#8ea8d4") if os.path.isfile(os.path.join(_PAGE_SVGS_DIR, "settings.svg")) else QIcon(),
            "Set": _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "edit.svg"), "#8ea8d4") if os.path.isfile(os.path.join(_PAGE_SVGS_DIR, "edit.svg")) else QIcon(),
            "Get": _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "list.svg"), "#8ea8d4") if os.path.isfile(os.path.join(_PAGE_SVGS_DIR, "list.svg")) else QIcon(),
        }
        for instr in INSTRUMENT_REGISTRY:
            cats = []
            for cat in instr.get("categories", []):
                ops = filter_selectable_ops(cat.get("ops", []))
                if ops:
                    visible_cat = dict(cat)
                    visible_cat["ops"] = ops
                    cats.append(visible_cat)
            if not cats:
                continue
            sub = instr_submenu.addMenu(f"{instr['name']}")
            sub.setStyleSheet(_CONTEXT_MENU_STYLE)
            flat = len(cats) == 1
            for cat in cats:
                cat_name = cat["name"]
                ops = cat.get("ops", [])
                if not ops:
                    continue
                cat_icon = _cat_icons_add.get(cat_name, QIcon())
                if flat:
                    for op in ops:
                        cls = get_node_class(op["node_type"])
                        icon_text = cls.icon if cls else ""
                        action = sub.addAction(f"{icon_text} {op['label']}")
                        action.triggered.connect(
                            lambda checked=False, nt=op["node_type"]: self._on_add_node(nt)
                        )
                elif len(ops) == 1:
                    op = ops[0]
                    cls = get_node_class(op["node_type"])
                    icon_text = cls.icon if cls else ""
                    action = sub.addAction(f"{icon_text} [{cat_name}] {op['label']}")
                    action.triggered.connect(
                        lambda checked=False, nt=op["node_type"]: self._on_add_node(nt)
                    )
                else:
                    cat_sub = sub.addMenu(cat_icon, cat_name)
                    cat_sub.setStyleSheet(_CONTEXT_MENU_STYLE)
                    for op in ops:
                        cls = get_node_class(op["node_type"])
                        icon_text = cls.icon if cls else ""
                        action = cat_sub.addAction(f"{icon_text} {op['label']}")
                        action.triggered.connect(
                            lambda checked=False, nt=op["node_type"]: self._on_add_node(nt)
                        )
        menu.addSeparator()

        _non_instr_cats = [
            ("value", "tag.svg", "Value / Variables"),
            ("logic", "git-branch.svg", "Logic / Flow"),
            ("io", "hard-drive.svg", "Data I/O"),
        ]
        for cat_key, icon_file, cat_label in _non_instr_cats:
            nodes = [
                cls for cls in get_nodes_by_category(cat_key)
                if is_node_selectable(cls.node_type)
            ]
            if not nodes:
                continue
            svg_path = os.path.join(_PAGE_SVGS_DIR, icon_file)
            cat_qicon = _tinted_svg_icon(svg_path, "#dce7ff") if os.path.isfile(svg_path) else QIcon()
            sub = menu.addMenu(cat_qicon, cat_label)
            sub.setStyleSheet(_CONTEXT_MENU_STYLE)
            for node_cls in nodes:
                action = sub.addAction(f"{node_cls.icon} {node_cls.display_name}")
                action.triggered.connect(
                    lambda checked=False, nt=node_cls.node_type: self._on_add_node(nt)
                )

        menu.exec(self.canvas.add_btn.mapToGlobal(self.canvas.add_btn.rect().bottomLeft()))

    def _on_instrument_requested(self, instr_id: str) -> None:
        from PySide6.QtWidgets import QMenu, QCursor
        from ui.pages.custom_test.node_palette import get_instrument_by_id

        instr = get_instrument_by_id(instr_id)
        if instr is None:
            return

        categories = []
        for cat in instr.get("categories", []):
            ops = filter_selectable_ops(cat.get("ops", []))
            if ops:
                visible_cat = dict(cat)
                visible_cat["ops"] = ops
                categories.append(visible_cat)
        if not categories:
            self.logs_frame.append_log(f"[WARN] 仪器节点暂不可用: {instr.get('name', instr_id)}")
            return

        all_ops = [op for cat in categories for op in cat.get("ops", [])]
        if len(all_ops) == 1:
            self._on_add_node(all_ops[0]["node_type"])
            return

        _cat_icons = {
            "Config": _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "settings.svg"), "#8ea8d4") if os.path.isfile(os.path.join(_PAGE_SVGS_DIR, "settings.svg")) else QIcon(),
            "Set": _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "edit.svg"), "#8ea8d4") if os.path.isfile(os.path.join(_PAGE_SVGS_DIR, "edit.svg")) else QIcon(),
            "Get": _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "list.svg"), "#8ea8d4") if os.path.isfile(os.path.join(_PAGE_SVGS_DIR, "list.svg")) else QIcon(),
        }

        menu = QMenu(self)
        menu.setStyleSheet(_CONTEXT_MENU_STYLE)

        microscope_path = os.path.join(_PAGE_SVGS_DIR, "microscope.svg")
        title_icon = _tinted_svg_icon(microscope_path, "#5f78a8") if os.path.isfile(microscope_path) else QIcon()
        title_action = menu.addAction(title_icon, f"{instr['name']} — Select Operation")
        title_action.setEnabled(False)
        menu.addSeparator()

        flat_mode = len(categories) == 1
        for cat in categories:
            cat_name = cat["name"]
            ops = cat.get("ops", [])
            if not ops:
                continue
            cat_icon = _cat_icons.get(cat_name, QIcon())
            if flat_mode:
                for op in ops:
                    cls = get_node_class(op["node_type"])
                    icon_text = cls.icon if cls else ""
                    action = menu.addAction(f"{icon_text}  {op['label']}")
                    action.triggered.connect(
                        lambda checked=False, nt=op["node_type"]: self._on_add_node(nt)
                    )
            elif len(ops) == 1:
                op = ops[0]
                cls = get_node_class(op["node_type"])
                icon_text = cls.icon if cls else ""
                action = menu.addAction(f"{icon_text}  [{cat_name}] {op['label']}")
                action.triggered.connect(
                    lambda checked=False, nt=op["node_type"]: self._on_add_node(nt)
                )
            else:
                submenu = menu.addMenu(cat_icon, cat_name)
                submenu.setStyleSheet(_CONTEXT_MENU_STYLE)
                for op in ops:
                    cls = get_node_class(op["node_type"])
                    icon_text = cls.icon if cls else ""
                    action = submenu.addAction(f"{icon_text}  {op['label']}")
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
        from core.custom_test.nodes.logic_nodes import (
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

    def _build_instrument_resolver(self) -> InstrumentResolver:
        legacy_sources: Dict[str, object] = {}
        legacy_labels: Dict[str, str] = {}

        if getattr(self, "n6705c", None) is not None:
            legacy_sources["n6705c"] = self.n6705c
            legacy_labels["n6705c"] = "legacy_n6705c_mixin"
        if getattr(self, "chamber", None) is not None:
            legacy_sources["chamber"] = self.chamber
            legacy_labels["chamber"] = "legacy_chamber_mixin"
        if self._mso64b_top_ref and getattr(self._mso64b_top_ref, "is_connected", False):
            scope = getattr(self._mso64b_top_ref, "mso64b", None)
            if scope is not None:
                legacy_sources["scope"] = scope
                legacy_labels["scope"] = "legacy_scope_top"
        if getattr(self, "_i2c_interface", None) is not None:
            legacy_sources["i2c"] = self._i2c_interface
            legacy_labels["i2c"] = "legacy_i2c_cached"
        if getattr(self, "_serial_connected", False):
            legacy_sources["uart"] = self
            legacy_labels["uart"] = "legacy_uart_mixin"
        if getattr(self, "is_mcu_io_connected", False) and getattr(self, "mcu_io", None) is not None:
            legacy_sources["mcu_io"] = self.mcu_io
            legacy_labels["mcu_io"] = "legacy_mcu_io_mixin"

        return InstrumentResolver(
            instrument_manager=self._instrument_manager,
            legacy_sources=legacy_sources,
            legacy_source_labels=legacy_labels,
            owner="custom_test",
            allow_i2c_autoconnect=True,
        )

    def _show_preflight_issues(self, issues: List[Any]) -> bool:
        for issue in issues:
            self.logs_frame.append_log(issue.format())
            if issue.fix_hint:
                self.logs_frame.append_log(f"        hint: {issue.fix_hint}")

        dialog = ValidationIssuesDialog(issues, parent=self)
        dialog.issue_activated.connect(self._locate_validation_issue)
        if dialog.has_errors:
            dialog.exec()
            return False
        return dialog.exec() == ValidationIssuesDialog.Accepted

    def _locate_validation_issue(self, node_uid: str) -> None:
        if node_uid and hasattr(self.canvas, "locate_node"):
            self.canvas.locate_node(node_uid)
        elif node_uid:
            self.canvas.highlight_step(node_uid)

    def _on_run(self) -> None:
        sequence = self.canvas.get_sequence()
        resolver = self._build_instrument_resolver()
        preflight = preflight_validate(sequence, resolver=resolver)

        self.logs_frame.clear_log()
        if preflight.issues and not self._show_preflight_issues(preflight.issues):
            if preflight.resolved is not None:
                preflight.resolved.close_owned()
            return

        resolved = preflight.resolved or resolver.resolve(sequence)
        if resolved.missing:
            for missing in resolved.missing:
                self.logs_frame.append_log(f"[ERROR] {missing.message}")
            resolved.close_owned()
            return

        self._context = ExecutionContext(
            instrument_manager=self._instrument_manager,
            instruments=resolved.as_instrument_dict(),
            resolved_instruments=resolved,
            lease_session_ids=resolved.lease_session_ids,
        )
        self._context.set_prompt_handler(self._request_user_prompt)
        self._result_store = self._context.result_store
        self.result_panel.set_result_store(self._result_store)
        try:
            self._context.acquire_leases(owner="custom_test")
        except Exception as exc:
            self._context.release_runtime_resources()
            self.logs_frame.append_log(f"[ERROR] InstrumentLease 申请失败: {exc}")
            QMessageBox.critical(self, "仪器占用", f"InstrumentLease 申请失败:\n{exc}")
            return

        self.result_panel.clear_results()

        self.canvas.set_running_state(True)
        self.logs_frame.set_progress(0)

        executor = self._executor_thread.start(sequence, self._context)

        executor.log_message.connect(self.logs_frame.append_log, Qt.QueuedConnection)
        executor.progress_updated.connect(self._on_progress, Qt.QueuedConnection)
        executor.step_started.connect(self._on_step_started, Qt.QueuedConnection)
        executor.data_recorded.connect(self._on_data_recorded, Qt.QueuedConnection)

    def _get_result_store(self) -> ResultStore:
        if self._context is not None:
            return self._context.result_store
        return self._result_store

    def _reset_result_view(self) -> None:
        self.result_panel.clear_results()

    def _render_result_table(self) -> None:
        self.result_panel.render_result_table()

    def _refresh_result_plot(self) -> None:
        self.result_panel.plot_result_fields()

    def _current_result_columns(self) -> List[str]:
        return self.result_panel.current_result_columns()

    def _on_stop(self) -> None:
        """停止执行"""
        self._executor_thread.stop()
        if self._active_prompt_request is not None:
            self._active_prompt_request.cancel("PromptUser 已被停止")
        if self._active_prompt_box is not None:
            self._active_prompt_box.reject()
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

    def _request_user_prompt(self, message: str, timeout_s: float = 300.0) -> Optional[str]:
        request = _PromptRequest(message, timeout_s)
        self.prompt_requested.emit(request)
        deadline = time.monotonic() + request.timeout_s if request.timeout_s > 0 else None

        while True:
            wait_s = 0.1
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    request.timeout()
                    raise StopExecution(request.reason)
                wait_s = min(wait_s, remaining)

            if request.wait(wait_s):
                break
            if self._context is not None and self._context.should_stop:
                request.cancel("PromptUser 已被停止")
                raise StopExecution(request.reason)

        if request.timed_out:
            raise StopExecution(request.reason)
        if request.cancelled:
            raise StopExecution(request.reason or "PromptUser 已取消")
        return request.response or "confirmed"

    def _on_prompt_requested(self, request: _PromptRequest) -> None:
        if request.is_done:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Custom Test Prompt")
        box.setText(request.message)
        box.setInformativeText("确认后测试流程将继续执行。")
        confirm_btn = box.addButton("继续", QMessageBox.AcceptRole)
        cancel_btn = box.addButton("取消", QMessageBox.RejectRole)
        confirm_btn.setDefault(True)
        confirm_btn.setAutoDefault(True)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)

        timer = QTimer(box)
        timer.setSingleShot(True)
        if request.timeout_s > 0:
            timer.timeout.connect(lambda: self._expire_prompt_request(request, box))
            timer.start(int(request.timeout_s * 1000))

        self._active_prompt_box = box
        self._active_prompt_request = request
        try:
            box.exec()
            if not request.is_done:
                if box.clickedButton() == confirm_btn:
                    request.set_response("confirmed")
                else:
                    request.cancel("PromptUser 已取消")
        finally:
            timer.stop()
            if self._active_prompt_box is box:
                self._active_prompt_box = None
            if self._active_prompt_request is request:
                self._active_prompt_request = None

    def _expire_prompt_request(self, request: _PromptRequest, box: QMessageBox) -> None:
        request.timeout()
        box.reject()

    def _on_progress(self, current: int, total: int) -> None:
        """进度更新"""
        if total > 0:
            pct = int(current / total * 100)
            self.logs_frame.set_progress(pct)

    def _on_step_started(self, uid: str, name: str) -> None:
        """步骤开始"""
        self.canvas.highlight_step(uid)

    def _on_data_recorded(self, row: Dict[str, Any]) -> None:
        self.result_panel.append_result_row(row, append_to_store=self._context is None)

    def _on_result_section_moved(self, logical_idx: int, old_visual: int, new_visual: int) -> None:
        self.result_panel._on_result_section_moved(logical_idx, old_visual, new_visual)

    def _on_header_context_menu(self, pos) -> None:
        self.result_panel._on_header_context_menu(pos)

    def _apply_column_format(self, col: int, action, fmt_map: dict) -> None:
        self.result_panel._apply_column_format(col, action, fmt_map)

    def _sort_column_numeric(self, col: int, ascending: bool = True) -> None:
        self.result_panel._sort_column_numeric(col, ascending=ascending)

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
            get_resource_base()
        )
        profile = str(self._context.get_variable("chip", self._context.get_variable("profile", "default")))
        filepath = build_default_result_path(
            project_root,
            chip_or_profile=profile,
            fmt="csv",
        )
        manifest = self._context.result_store.build_manifest(
            instrument_snapshot=self._collect_result_instrument_manifest(),
        )
        self._context.result_store.export_csv(filepath, view=False, manifest=manifest)

        self.logs_frame.append_log(f"[EXPORT] CSV 已自动导出: {filepath}")

    def _collect_result_instrument_manifest(self) -> Dict[str, Dict[str, str]]:
        if self._context is None or self._context.resolved_instruments is None:
            return {}
        return {
            key: {
                "source": getattr(item, "source", ""),
                "session_id": getattr(item, "session_id", ""),
                "display_name": getattr(item, "display_name", ""),
            }
            for key, item in self._context.resolved_instruments.instruments.items()
        }

    def load_template(self, template_name: str) -> None:
        """加载内置模板"""
        filepath = os.path.join(_TEMPLATES_DIR, template_name)
        if not os.path.isfile(filepath):
            self.logs_frame.append_log(f"[ERROR] 模板文件不存在: {filepath}")
            return
        try:
            result = load_sequence_file(filepath)
            self.canvas.load_from_nodes(result.nodes)
            if result.instruments:
                self._on_metadata_loaded(result.instruments)
            for issue in result.issues:
                self.logs_frame.append_log(issue.format())
            self.logs_frame.append_log(f"[TEMPLATE] 已加载模板: {template_name}")
        except Exception as e:
            self.logs_frame.append_log(f"[ERROR] 加载模板失败: {e}")

    def append_log(self, message: str) -> None:
        """统一的日志接口"""
        self.logs_frame.append_log(message)

    def cleanup_threads(self) -> None:
        """清理工作线程"""
        if self._active_prompt_request is not None:
            self._active_prompt_request.cancel("Custom Test 页面关闭")
        if self._active_prompt_box is not None:
            self._active_prompt_box.reject()
        self._executor_thread._force_stop()
        if self._i2c_interface is not None:
            self._i2c_interface.close()
            self._i2c_interface = None
        self.close_serial()


def main():
    from ui.standalone import run_standalone_widget

    return run_standalone_widget(
        lambda: CustomTestUI(),
        "Custom Test",
        size=(1400, 900),
    )


if __name__ == "__main__":
    raise SystemExit(main())
