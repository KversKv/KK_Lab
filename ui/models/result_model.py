"""ResultModel — 测试结果表模型（列随测试项动态）。

- 列由 ``set_columns([(key, label), ...])`` 动态定义；行是 ``list[dict]``；
- 行 dict 的 ``"_status"`` 键（PASS/FAIL/N-A 等）触发状态着色
  （ForegroundRole 取 theme token，model 不 import QtWidgets）；
- ``"_log_key"`` 键携带日志定位关键字（双击定位日志用，不显示）。

为什么这样拆：结果列结构随测试项变化（不同 item measured 键不同），
列定义放 model 数据里，View/页面无需关心列布局。
"""
from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from ui.theme import current_theme

STATUS_KEY = "_status"
LOG_KEY = "_log_key"


class ResultModel(QAbstractTableModel):
    """动态列结果表模型。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._columns: list[tuple[str, str]] = []
        self._rows: list[dict] = []

    # ------------------------------------------------------------------ 结构
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._columns[section][1]
        return None

    # ------------------------------------------------------------------ 数据
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        key = self._columns[index.column()][0]
        if role == Qt.DisplayRole:
            value = row.get(key, "")
            if isinstance(value, float):
                return f"{value:g}"
            return str(value)
        if role == Qt.ForegroundRole and key == STATUS_KEY:
            return self._status_color(str(row.get(STATUS_KEY, "")))
        if role == Qt.TextAlignmentRole and key == STATUS_KEY:
            return int(Qt.AlignCenter)
        return None

    @staticmethod
    def _status_color(status: str) -> QColor | None:
        t = current_theme()
        s = status.upper()
        if s.startswith("PASS") or s.startswith("✓"):
            return QColor(t.state_success.fg)
        if s.startswith("FAIL") or s.startswith("✗"):
            return QColor(t.state_error.fg)
        if not status:
            return None
        return QColor(t.text_muted)

    # ------------------------------------------------------------------ 维护
    def set_columns(self, columns: Sequence[tuple[str, str]]) -> None:
        self.beginResetModel()
        self._columns = list(columns)
        self.endResetModel()

    def set_rows(self, rows: Sequence[dict]) -> None:
        self.beginResetModel()
        self._rows = [dict(r) for r in rows]
        self.endResetModel()

    def append_row(self, row: dict) -> None:
        at = len(self._rows)
        self.beginInsertRows(QModelIndex(), at, at)
        self._rows.append(dict(row))
        self.endInsertRows()

    def clear(self) -> None:
        self.set_rows([])

    def columns(self) -> list[tuple[str, str]]:
        return list(self._columns)

    def row_at(self, row: int) -> dict | None:
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def row_count(self) -> int:
        return len(self._rows)
