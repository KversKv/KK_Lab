"""Custom Test 主页面 —— 三栏布局可视化自定义测试序列编辑器"""

from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QFrame,
    QLabel, QSizePolicy, QFileDialog, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
)
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg

from ui.pages.custom_test.node_palette import NodePalette
from ui.pages.custom_test.sequence_canvas import SequenceCanvas
from ui.pages.custom_test.property_panel import PropertyPanel
from ui.pages.custom_test.nodes.base_node import BaseNode, get_node_class
from ui.pages.custom_test.context import ExecutionContext
from ui.pages.custom_test.executor import ExecutorThread
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import VT6002ConnectionMixin
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from debug_config import DEBUG_MOCK
from log_config import get_logger

logger = get_logger(__name__)

_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "resources", "icons"
)

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

_PAGE_STYLE = """
    QWidget#customTestPage {
        background-color: #020618;
        border: none;
    }
    QSplitter::handle {
        background-color: #0b1428;
        width: 3px;
    }
    QSplitter::handle:hover {
        background-color: #5b5cf6;
    }
    QFrame#sectionFrame {
        background-color: #09142e;
        border: 1px solid #1a2d57;
        border-radius: 14px;
    }
    QLabel#sectionTitle {
        font-size: 11px;
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
    QLabel#statusOk {
        color: #15d1a3;
        font-weight: 600;
        background-color: transparent;
        border: none;
    }
    QLabel#statusWarn {
        color: #ffb84d;
        font-weight: 600;
        background-color: transparent;
        border: none;
    }
    QLabel#statusErr {
        color: #ff5e7a;
        font-weight: 600;
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
"""


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

        self._executor_thread = ExecutorThread(self)
        self._context: Optional[ExecutionContext] = None

        self._build_ui()
        self._connect_signals()
        self._sync_instruments()

    def _build_ui(self) -> None:
        """构建三栏布局 + 底部日志/图表"""
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        main_splitter = QSplitter(Qt.Vertical)

        top_splitter = QSplitter(Qt.Horizontal)

        left_panel = self._build_left_panel()
        top_splitter.addWidget(left_panel)

        self.canvas = SequenceCanvas()
        top_splitter.addWidget(self.canvas)

        self.property_panel = PropertyPanel()
        top_splitter.addWidget(self.property_panel)

        top_splitter.setSizes([220, 520, 260])
        main_splitter.addWidget(top_splitter)

        bottom_widget = self._build_bottom_panel()
        main_splitter.addWidget(bottom_widget)

        main_splitter.setSizes([500, 280])
        root.addWidget(main_splitter)

    def _build_left_panel(self) -> QWidget:
        """构建左栏：仪器连接 + 节点面板"""
        panel = QWidget()
        panel.setStyleSheet("QWidget { background: transparent; border: none; }")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        instr_frame = QFrame()
        instr_frame.setObjectName("sectionFrame")
        instr_layout = QVBoxLayout(instr_frame)
        instr_layout.setContentsMargins(12, 10, 12, 12)
        instr_layout.setSpacing(6)

        instr_title = QLabel("⚙ Instrument Connections")
        instr_title.setObjectName("sectionTitle")
        instr_layout.addWidget(instr_title)

        n6705c_label = QLabel("N6705C Power Analyzer")
        n6705c_label.setObjectName("fieldLabel")
        instr_layout.addWidget(n6705c_label)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.build_n6705c_connection_widgets(instr_layout, title_row=title_row)

        chamber_label = QLabel("VT6002 Chamber")
        chamber_label.setObjectName("fieldLabel")
        instr_layout.addWidget(chamber_label)
        self.build_vt6002_connection_widgets(instr_layout)

        scope_label = QLabel("Oscilloscope")
        scope_label.setObjectName("fieldLabel")
        instr_layout.addWidget(scope_label)
        self._scope_status = QLabel("● Synced from main" if self._mso64b_top_ref else "● Not available")
        self._scope_status.setObjectName("statusOk" if self._mso64b_top_ref else "statusErr")
        self._scope_status.setStyleSheet("background: transparent; border: none;")
        instr_layout.addWidget(self._scope_status)

        layout.addWidget(instr_frame)

        self.palette = NodePalette()
        layout.addWidget(self.palette, 1)

        return panel

    def _build_bottom_panel(self) -> QWidget:
        """构建底部面板：日志 + 实时数据表 + 图表"""
        widget = QWidget()
        widget.setStyleSheet("QWidget { background: transparent; border: none; }")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        tabs = QTabWidget()

        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.logs_frame = ExecutionLogsFrame(
            title="⊙ Execution Logs", show_progress=True
        )
        log_layout.addWidget(self.logs_frame)
        tabs.addTab(log_tab, "📋 Logs")

        table_tab = QWidget()
        table_layout = QVBoxLayout(table_tab)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(0)
        self.result_table.setRowCount(0)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        table_layout.addWidget(self.result_table)
        tabs.addTab(table_tab, "📊 Data")

        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#060e20")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setLabel("bottom", "Index", color="#5f78a8")
        self.plot_widget.setLabel("left", "Value", color="#5f78a8")
        self.plot_widget.addLegend(offset=(-10, 10))
        chart_layout.addWidget(self.plot_widget)
        tabs.addTab(chart_tab, "📈 Chart")

        layout.addWidget(tabs)
        return widget

    def _connect_signals(self) -> None:
        """连接所有信号/槽"""
        self.bind_n6705c_signals()
        self.bind_vt6002_signals()

        self.palette.node_requested.connect(self._on_add_node)
        self.canvas.add_btn.clicked.connect(self._on_add_btn_clicked)
        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.run_requested.connect(self._on_run)
        self.canvas.stop_requested.connect(self._on_stop)
        self.canvas.pause_requested.connect(self._on_pause)

        self.property_panel.param_changed.connect(self._on_param_changed)

        self._executor_thread.finished.connect(self._on_execution_finished)

    def _sync_instruments(self) -> None:
        """同步仪器状态"""
        if self._n6705c_top_ref:
            self.sync_n6705c_from_top()
        if self._vt6002_chamber_ui_ref and self._vt6002_chamber_ui_ref.vt6002:
            self._on_vt6002_external_changed()

    def sync_n6705c_from_top(self) -> None:
        """重载：从 Top 同步 N6705C"""
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

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0b1428;
                color: #dce7ff;
                border: 1px solid #1a2d57;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1a2d57;
            }
        """)
        for cat in ["instrument", "logic", "io"]:
            nodes = get_nodes_by_category(cat)
            for node_cls in nodes:
                action = menu.addAction(f"{node_cls.icon} {node_cls.display_name}")
                action.triggered.connect(
                    lambda checked=False, nt=node_cls.node_type: self._on_add_node(nt)
                )
            menu.addSeparator()
        menu.exec(self.canvas.add_btn.mapToGlobal(self.canvas.add_btn.rect().bottomLeft()))

    def _on_node_selected(self, node: Optional[BaseNode]) -> None:
        """节点选中回调"""
        self.property_panel.set_node(node)

    def _on_param_changed(self, uid: str, key: str, value: Any) -> None:
        """参数变更回调"""
        self.canvas.refresh_item(uid)

    def _on_run(self) -> None:
        """开始执行"""
        sequence = self.canvas.get_sequence()
        if not sequence:
            self.logs_frame.append_log("[WARN] 序列为空，请先添加节点")
            return

        self._context = ExecutionContext()
        self._context.instruments["n6705c"] = self.n6705c
        self._context.instruments["chamber"] = self.vt6002
        if self._mso64b_top_ref and self._mso64b_top_ref.is_connected:
            self._context.instruments["scope"] = self._mso64b_top_ref.mso64b

        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
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
                self.canvas.pause_btn.setText("⏸ Pause")
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
        self.canvas.pause_btn.setText("⏸ Pause")

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
