"""Custom Test results panel: logs, data table, chart and visible export."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pyqtgraph as pg
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QFileDialog,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.custom_test.result_store import ResultStore
from log_config import get_logger
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon

logger = get_logger(__name__)

_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "custom_test_SVGs"
)

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


class ResultPanel(QWidget):
    """Bottom panel for Custom Test run output."""

    def __init__(self, result_store: ResultStore | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._result_store = result_store or ResultStore()
        self._plot_curves: Dict[str, Any] = {}
        self._plot_data: Dict[str, List[float]] = {}
        self._rendering_result_table = False
        self._build_ui()

    def _build_ui(self) -> None:
        self.setObjectName("bottomPanel")
        self.setStyleSheet("QWidget#bottomPanel { background: transparent; border: none; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        tabs = QTabWidget()
        self._bottom_tabs = tabs

        self._export_btn = QPushButton("Export")
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.setToolTip("将当前 Data 表格导出为 Excel / CSV")
        self._export_btn.setStyleSheet(
            "QPushButton { background-color: #132040; color: #8eb0e3;"
            "  border: 1px solid #1a2d57; border-radius: 6px;"
            "  padding: 4px 12px; font-size: 11px; font-weight: 600; margin: 2px 6px; }"
            "QPushButton:hover { background-color: #1a2d57; color: #dce7ff; }"
            "QPushButton:pressed { background-color: #0c1733; }"
            "QPushButton:disabled { color: #3f5070; background-color: #0b1428;"
            "  border: 1px solid #132040; }"
        )
        self._export_btn.setVisible(False)
        self._export_btn.clicked.connect(self.export_visible_table)
        tabs.setCornerWidget(self._export_btn, Qt.TopRightCorner)
        tabs.currentChanged.connect(self._on_bottom_tab_changed)

        log_icon_path = os.path.join(_PAGE_SVGS_DIR, "clipboard-list.svg")
        table_icon_path = os.path.join(_PAGE_SVGS_DIR, "table.svg")
        chart_icon_path = os.path.join(_PAGE_SVGS_DIR, "line-chart.svg")

        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        log_layout.setContentsMargins(0, 0, 0, 0)
        self.logs_frame = ExecutionLogsFrame(title="Execution Logs", show_progress=True)
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
        self.result_table.horizontalHeader().setStretchLastSection(False)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.result_table.horizontalHeader().setDefaultSectionSize(120)
        self.result_table.horizontalHeader().setMinimumSectionSize(60)
        self.result_table.horizontalHeader().setSectionsMovable(True)
        self.result_table.horizontalHeader().setDragEnabled(True)
        self.result_table.horizontalHeader().setDragDropMode(QTableWidget.InternalMove)
        self.result_table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.result_table.horizontalHeader().customContextMenuRequested.connect(
            self._on_header_context_menu
        )
        self.result_table.horizontalHeader().sectionMoved.connect(
            self._on_result_section_moved
        )
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

    def set_result_store(self, store: ResultStore) -> None:
        self._result_store = store
        self.clear_results()

    def get_result_store(self) -> ResultStore:
        return self._result_store

    def append_log(self, message: str) -> None:
        self.logs_frame.append_log(message)

    def clear_log(self) -> None:
        self.logs_frame.clear_log()

    def set_progress(self, value: int) -> None:
        self.logs_frame.set_progress(value)

    def clear_results(self) -> None:
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self._table_empty_label.setVisible(True)
        self.plot_widget.clear()
        self._plot_curves = {}
        self._plot_data = {}

    def append_result_row(self, row: Dict[str, Any], append_to_store: bool = False) -> None:
        if not row:
            return
        if append_to_store:
            self._result_store.append(row)
        self.render_result_table()
        self.plot_result_fields()

    def export_visible_table(self) -> None:
        store = self._result_store
        if not store.records:
            QMessageBox.information(
                self, "无可导出的数据",
                "当前 Data 表格为空,请先运行一次测试采集数据。"
            )
            return

        default_name = f"custom_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出 Data 表格",
            default_name,
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )
        if not file_path:
            return

        lower = file_path.lower()
        if lower.endswith(".xlsx"):
            target = "xlsx"
        elif lower.endswith(".csv"):
            target = "csv"
        else:
            if "CSV" in (selected_filter or ""):
                target = "csv"
                file_path += ".csv"
            else:
                target = "xlsx"
                file_path += ".xlsx"

        try:
            if target == "xlsx":
                self.export_table_xlsx(file_path)
            else:
                self.export_table_csv(file_path)
        except Exception as exc:
            logger.exception("导出 Data 表格失败")
            self.append_log(f"[EXPORT] 导出失败: {exc}")
            QMessageBox.critical(
                self, "导出失败",
                f"导出 Data 表格失败:\n{exc}"
            )
            return

        self.append_log(f"[EXPORT] Data 表格已导出: {file_path}")
        QMessageBox.information(
            self, "导出成功",
            f"Data 表格已成功导出到:\n{file_path}"
        )

    def collect_table_rows(self) -> Tuple[List[str], List[List[str]]]:
        return self._result_store.view_table()

    def export_table_csv(self, file_path: str) -> None:
        self._result_store.export_csv(file_path, view=True)

    def export_table_xlsx(self, file_path: str) -> None:
        self._result_store.export_xlsx(file_path, view=True)

    def render_result_table(self) -> None:
        store = self._result_store
        fields = store.get_visible_fields()
        headers = [store.view_state.display_name(field.name) for field in fields]
        _, rows = store.view_table()

        self._rendering_result_table = True
        try:
            self.result_table.setRowCount(0)
            self.result_table.setColumnCount(len(headers))
            self.result_table.setHorizontalHeaderLabels(headers)
            for row_values in rows:
                row_idx = self.result_table.rowCount()
                self.result_table.insertRow(row_idx)
                for col, value in enumerate(row_values):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.result_table.setItem(row_idx, col, item)
        finally:
            self._rendering_result_table = False

        self._table_empty_label.setVisible(not rows)
        self.result_table.resizeColumnsToContents()
        header = self.result_table.horizontalHeader()
        for c in range(self.result_table.columnCount()):
            if header.sectionSize(c) < 80:
                header.resizeSection(c, 80)

    def plot_result_fields(self) -> None:
        series = self._result_store.plot_series()
        self.plot_widget.clear()
        self._plot_curves = {}
        self._plot_data = {}
        pen_colors = [
            "#5b5cf6", "#f2994a", "#27ae60", "#e74c3c",
            "#9b59b6", "#16a085", "#f39c12", "#2ecc71",
        ]
        for index, (field_name, values) in enumerate(series.items()):
            color = pen_colors[index % len(pen_colors)]
            curve = self.plot_widget.plot(
                [], [], pen=pg.mkPen(color=color, width=2), name=field_name
            )
            x_data = list(range(len(values)))
            curve.setData(x_data, values)
            self._plot_curves[field_name] = curve
            self._plot_data[field_name] = values

    def current_result_columns(self) -> List[str]:
        return [field.name for field in self._result_store.get_visible_fields()]

    def _on_bottom_tab_changed(self, index: int) -> None:
        try:
            tab_text = self._bottom_tabs.tabText(index)
        except Exception:
            tab_text = ""
        self._export_btn.setVisible(tab_text == "Data")

    def _on_result_section_moved(self, logical_idx: int, old_visual: int, new_visual: int) -> None:
        if self._rendering_result_table:
            return
        columns = self.current_result_columns()
        header = self.result_table.horizontalHeader()
        ordered = []
        for visual in range(self.result_table.columnCount()):
            logical = header.logicalIndex(visual)
            if 0 <= logical < len(columns):
                ordered.append(columns[logical])
        self._result_store.set_field_order(ordered)

    def _on_header_context_menu(self, pos) -> None:
        header = self.result_table.horizontalHeader()
        logical_idx = header.logicalIndexAt(pos)
        if logical_idx < 0 or logical_idx >= self.result_table.columnCount():
            return

        store = self._result_store
        columns = self.current_result_columns()
        if logical_idx >= len(columns):
            return
        field_name = columns[logical_idx]
        col_label = store.view_state.display_name(field_name)

        menu = QMenu(self)
        menu.setStyleSheet(_CONTEXT_MENU_STYLE)

        menu_icon_color = "#8eb0e3"
        bar_chart_icon = os.path.join(_PAGE_SVGS_DIR, "bar-chart.svg")
        pencil_icon = os.path.join(_PAGE_SVGS_DIR, "pencil.svg")
        hash_icon = os.path.join(_PAGE_SVGS_DIR, "hash.svg")
        trash_icon = os.path.join(_PAGE_SVGS_DIR, "trash.svg")

        if os.path.isfile(bar_chart_icon):
            title_action = menu.addAction(
                _tinted_svg_icon(bar_chart_icon, menu_icon_color, 16),
                f"  {col_label}",
            )
        else:
            title_action = menu.addAction(f"  {col_label}")
        title_action.setEnabled(False)
        menu.addSeparator()

        if os.path.isfile(pencil_icon):
            rename_action = menu.addAction(
                _tinted_svg_icon(pencil_icon, menu_icon_color, 16),
                "重命名列",
            )
        else:
            rename_action = menu.addAction("重命名列")
        menu.addSeparator()

        if os.path.isfile(hash_icon):
            fmt_menu = menu.addMenu(
                _tinted_svg_icon(hash_icon, menu_icon_color, 16),
                "数值格式",
            )
        else:
            fmt_menu = menu.addMenu("数值格式")
        fmt_menu.setStyleSheet(_CONTEXT_MENU_STYLE)
        fmt_auto = fmt_menu.addAction("自动")
        fmt_0 = fmt_menu.addAction("整数 (0)")
        fmt_2 = fmt_menu.addAction("2 位小数 (.00)")
        fmt_4 = fmt_menu.addAction("4 位小数 (.0000)")
        fmt_6 = fmt_menu.addAction("6 位小数 (.000000)")
        fmt_sci = fmt_menu.addAction("科学计数法 (1.23e+4)")
        fmt_hex = fmt_menu.addAction("十六进制 (0x1F3A)")

        menu.addSeparator()
        sort_asc_action = menu.addAction("⬆  升序排列")
        sort_desc_action = menu.addAction("⬇  降序排列")
        menu.addSeparator()

        if os.path.isfile(trash_icon):
            hide_action = menu.addAction(
                _tinted_svg_icon(trash_icon, menu_icon_color, 16),
                "删除列",
            )
        else:
            hide_action = menu.addAction("删除列")

        action = menu.exec(header.mapToGlobal(pos))
        if action is None:
            return

        if action == rename_action:
            new_name, ok = QInputDialog.getText(
                self, "重命名列", f"列 \"{col_label}\" 的新名称:", text=col_label
            )
            if ok and new_name.strip():
                store.set_display_name(field_name, new_name.strip())
                self.render_result_table()
        elif action == hide_action:
            store.hide_field(field_name)
            self.render_result_table()
            self.plot_result_fields()
        elif action == sort_asc_action:
            self._sort_column_numeric(logical_idx, ascending=True)
        elif action == sort_desc_action:
            self._sort_column_numeric(logical_idx, ascending=False)
        elif action in (fmt_auto, fmt_0, fmt_2, fmt_4, fmt_6, fmt_sci, fmt_hex):
            self._apply_column_format(logical_idx, action, {
                fmt_auto: "auto", fmt_0: "0", fmt_2: "2", fmt_4: "4",
                fmt_6: "6", fmt_sci: "sci", fmt_hex: "hex",
            })

    def _apply_column_format(self, col: int, action, fmt_map: dict) -> None:
        fmt = fmt_map.get(action, "auto")
        columns = self.current_result_columns()
        if col < 0 or col >= len(columns):
            return
        self._result_store.set_field_format(columns[col], fmt)
        self.render_result_table()

    def _sort_column_numeric(self, col: int, ascending: bool = True) -> None:
        columns = self.current_result_columns()
        if col < 0 or col >= len(columns):
            return
        self._result_store.sort_by(columns[col], ascending=ascending)
        self.render_result_table()
