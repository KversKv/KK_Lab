"""Structured preflight validation dialog for Custom Test."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ValidationIssuesDialog(QDialog):
    """Shows preflight issues and lets warnings continue after confirmation."""

    issue_activated = Signal(str)

    def __init__(self, issues: Iterable[object], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._issues = list(issues)
        self._has_errors = any(getattr(issue, "severity", "") == "error" for issue in self._issues)
        self.setWindowTitle("运行前校验")
        self.resize(780, 420)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        errors = sum(1 for issue in self._issues if getattr(issue, "severity", "") == "error")
        warnings = sum(1 for issue in self._issues if getattr(issue, "severity", "") == "warning")
        summary = QLabel(f"发现 {errors} 个错误，{warnings} 个警告。点击含节点的行可定位到对应节点。")
        summary.setWordWrap(True)
        layout.addWidget(summary)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["级别", "节点", "问题", "建议"])
        self._table.setRowCount(len(self._issues))
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.cellClicked.connect(self._on_row_activated)
        self._table.cellDoubleClicked.connect(self._on_row_activated)

        for row, issue in enumerate(self._issues):
            severity = getattr(issue, "severity", "")
            node_type = getattr(issue, "node_type", "")
            node_uid = getattr(issue, "node_uid", "")
            node_label = f"{node_type} ({node_uid[:8]})" if node_uid else node_type
            values = [
                severity.upper(),
                node_label,
                getattr(issue, "message", ""),
                getattr(issue, "fix_hint", ""),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignCenter if col == 0 else Qt.AlignLeft))
                item.setData(Qt.UserRole, node_uid)
                self._table.setItem(row, col, item)

        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, 1)

        if self._has_errors:
            buttons = QDialogButtonBox(QDialogButtonBox.Close)
            close_btn = buttons.button(QDialogButtonBox.Close)
            close_btn.setDefault(True)
            close_btn.setAutoDefault(True)
            buttons.rejected.connect(self.reject)
        else:
            buttons = QDialogButtonBox()
            continue_btn = buttons.addButton("继续运行", QDialogButtonBox.AcceptRole)
            cancel_btn = buttons.addButton("取消", QDialogButtonBox.RejectRole)
            continue_btn.setDefault(True)
            continue_btn.setAutoDefault(True)
            cancel_btn.setDefault(False)
            cancel_btn.setAutoDefault(False)
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_row_activated(self, row: int, column: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        node_uid = item.data(Qt.UserRole)
        if node_uid:
            self.issue_activated.emit(str(node_uid))

    @property
    def has_errors(self) -> bool:
        return self._has_errors
