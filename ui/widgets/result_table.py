"""ResultTable — 测试结果表（动态列 + 排序 + 复制 + 导出 CSV + 双击定位日志）。

- 数据在 ``ui.models.result_model.ResultModel``，本类只做视图与交互；
- ``QSortFilterProxyModel`` 提供点击表头排序；
- 无数据时显示 ``EmptyState``（QStackedLayout 切换）；
- 双击行发 ``locateRequested(str)``：携带行内 ``_log_key``（日志定位关键字）。

为什么这样拆：排序/导出/复制/空态是结果区的通用交互，与"结果从哪来"
（ModuleTestResult）解耦；页面只负责把 result 摊平成 rows 喂进来。
"""
from __future__ import annotations

import csv
import os
from collections.abc import Sequence

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QPushButton, QStackedLayout,
    QTableView, QVBoxLayout, QWidget,
)

from log_config import get_logger
from ui.models.result_model import LOG_KEY, STATUS_KEY, ResultModel
from ui.widgets.empty_state import EmptyState

_logger = get_logger(__name__)


class ResultTable(QWidget):
    """测试结果表。"""

    locateRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # —— 工具行 ——
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(6)
        bar.addStretch()
        self.copy_btn = QPushButton("复制")
        self.copy_btn.setProperty("variant", "ghost")
        self.copy_btn.setToolTip("复制选中行（TSV，可粘贴到 Excel）")
        self.copy_btn.clicked.connect(self.copy_selection)
        bar.addWidget(self.copy_btn)
        self.export_btn = QPushButton("导出 CSV…")
        self.export_btn.setProperty("variant", "ghost")
        self.export_btn.clicked.connect(self.export_csv)
        bar.addWidget(self.export_btn)
        root.addLayout(bar)

        # —— 表 / 空态 ——
        self._stack = QStackedLayout()
        self.view = QTableView()
        self.model = ResultModel(self)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self.model)
        self.view.setModel(self._proxy)
        self.view.setSortingEnabled(True)
        self.view.setSelectionBehavior(QTableView.SelectRows)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().setVisible(False)
        self.view.doubleClicked.connect(self._on_double_clicked)
        self._stack.addWidget(self.view)

        self.empty = EmptyState(title="暂无测试结果",
                                hint="执行测试后，各测试项的测量结果将显示在这里。")
        self._stack.addWidget(self.empty)
        root.addLayout(self._stack, 1)
        self._stack.setCurrentWidget(self.empty)

    # ------------------------------------------------------------------ 数据
    def set_columns(self, columns: Sequence[tuple[str, str]]) -> None:
        """设置动态列；首列建议为 (STATUS_KEY, "判定")。"""
        self.model.set_columns(columns)

    def set_rows(self, rows: Sequence[dict]) -> None:
        self.model.set_rows(rows)
        self._refresh_empty()

    def append_row(self, row: dict) -> None:
        self.model.append_row(row)
        self._refresh_empty()

    def clear(self) -> None:
        self.model.clear()
        self._refresh_empty()

    def _refresh_empty(self) -> None:
        has = self.model.row_count() > 0
        self._stack.setCurrentWidget(self.view if has else self.empty)

    # ------------------------------------------------------------------ 交互
    def _on_double_clicked(self, proxy_index) -> None:
        src = self._proxy.mapToSource(proxy_index)
        row = self.model.row_at(src.row())
        if row:
            self.locateRequested.emit(str(row.get(LOG_KEY, "")))

    def copy_selection(self) -> None:
        """复制选中行为 TSV（含表头）。"""
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return
        cols = [self.model.headerData(c, Qt.Horizontal, Qt.DisplayRole)
                for c in range(self.model.columnCount())]
        lines = ["\t".join(str(c) for c in cols)]
        for proxy_idx in sorted(indexes, key=lambda i: i.row()):
            src = self._proxy.mapToSource(proxy_idx)
            row = self.model.row_at(src.row())
            if row is None:
                continue
            lines.append("\t".join(str(row.get(k, "")) for k, _l in
                                   self.model.columns()))
        QGuiApplication.clipboard().setText("\n".join(lines))

    def export_csv(self, path: str | None = None) -> str | None:
        """导出 CSV；path 为空时弹文件对话框。返回实际路径或 None。"""
        if self.model.row_count() == 0:
            return None
        if not path:
            path, _f = QFileDialog.getSaveFileName(
                self, "导出测试结果", "module_test_results.csv",
                "CSV 文件 (*.csv)")
        if not path:
            return None
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([self.model.headerData(c, Qt.Horizontal, Qt.DisplayRole)
                                 for c in range(self.model.columnCount())])
                for r in range(self.model.row_count()):
                    row = self.model.row_at(r) or {}
                    writer.writerow([row.get(k, "") for k, _l in self.model.columns()])
        except OSError:
            _logger.error("导出结果 CSV 失败：%s", path, exc_info=True)
            return None
        return path


if __name__ == "__main__":
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("ResultTable Demo")
    apply_qss(win, "controls")
    apply_qss(win, "table")
    lay = QVBoxLayout(win)

    table = ResultTable()
    lay.addWidget(table)
    table.set_columns([(STATUS_KEY, "判定"), ("item", "测试项"),
                       ("vout_mv", "Vout (mV)"), ("vpp_mv", "Vpp (mV)")])
    table.set_rows([
        {STATUS_KEY: "PASS", "item": "Line Regulation", "vout_mv": 1801.2, "vpp_mv": 3.1, LOG_KEY: "ldo_line_reg"},
        {STATUS_KEY: "FAIL", "item": "Load Transient", "vout_mv": 1750.0, "vpp_mv": 45.2, LOG_KEY: "ldo_load_transient"},
        {STATUS_KEY: "PASS", "item": "Quiescent Current", "vout_mv": 1800.0, "vpp_mv": 0, LOG_KEY: "ldo_quiescent"},
    ])
    table.locateRequested.connect(lambda k: print("定位日志:", k))

    win.resize(640, 400)
    win.show()
    sys.exit(app.exec())
