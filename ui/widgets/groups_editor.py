"""GroupsTableEditor — 分组参数表格编辑器（替换旧 _GroupsEditor）。

- ``QTableView + QAbstractTableModel + QDoubleSpinBox`` 委托；
- 输入即校验：越界/无法解析的单元格红底 + tooltip，``value()`` 仍返回
  ``list[dict]`` 并跳过含无效值的行（与旧行为一致，差异是 UI 会高亮提示）；
- 支持行拖拽排序（InternalMove）、上/下移、删除、清空、从 Excel 粘贴 TSV
  （Ctrl+V 或「粘贴」按钮，自动按当前行插入）。

为什么这样拆：旧 _GroupsEditor 用 QTableWidget 裸文本，无校验无排序；
校验/排序/粘贴是数据行为，下沉到 Model，View 只负责渲染与交互，
组件也因此与 ParamSpec 解耦（只认本文件的 GroupColumn）。
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QDoubleSpinBox, QHBoxLayout, QHeaderView, QPushButton,
    QStyledItemDelegate, QTableView, QVBoxLayout, QWidget,
)

from ui.theme import current_theme


@dataclass(frozen=True)
class GroupColumn:
    """分组编辑器列定义（与业务 ParamSpec 解耦，由调用方适配）。"""

    key: str
    label: str
    unit: str = ""
    minimum: float = 0.0
    maximum: float = 1_000_000.0
    decimals: int = 3
    default: float = 0.0


class _GroupsModel(QAbstractTableModel):
    """行 = 一组参数；单元格存 float，无效输入存 None（红底提示）。"""

    def __init__(self, columns: Sequence[GroupColumn], parent=None):
        super().__init__(parent)
        self._columns = list(columns)
        self._rows: list[list[float | None]] = []

    # -------------------------------------------------------------- 结构
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            col = self._columns[section]
            return f"{col.label} ({col.unit})" if col.unit else col.label
        return str(section + 1)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled
        if not index.isValid():
            return Qt.ItemIsDropEnabled
        return base

    def supportedDropActions(self):
        return Qt.MoveAction

    # -------------------------------------------------------------- 数据
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        value = self._rows[index.row()][index.column()]
        col = self._columns[index.column()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            return "" if value is None else f"{value:g}"
        if role == Qt.BackgroundRole and value is None:
            return QColor(current_theme().state_error.bg)
        if role == Qt.ToolTipRole:
            if value is None:
                return "无效值：无法解析或越界，该行将被跳过"
            if not (col.minimum <= value <= col.maximum):
                return f"越界提示：允许范围 [{col.minimum:g}, {col.maximum:g}]"
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
        try:
            v = float(str(value).strip())
        except (TypeError, ValueError):
            v = None
        self._rows[index.row()][index.column()] = v
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.BackgroundRole, Qt.ToolTipRole])
        return True

    # -------------------------------------------------------------- 行操作
    def insert_row(self, at: int, values: Sequence[float | None] | None = None) -> None:
        at = max(0, min(at, len(self._rows)))
        self.beginInsertRows(QModelIndex(), at, at)
        if values is None:
            values = [c.default for c in self._columns]
        row = [(float(v) if v is not None else None) for v in values]
        row += [c.default for c in self._columns[len(row):]]
        self._rows.insert(at, row[: len(self._columns)])
        self.endInsertRows()

    def remove_rows(self, rows: Sequence[int]) -> None:
        for r in sorted(set(rows), reverse=True):
            if 0 <= r < len(self._rows):
                self.beginRemoveRows(QModelIndex(), r, r)
                self._rows.pop(r)
                self.endRemoveRows()

    def move_row(self, src: int, dst: int) -> None:
        if not (0 <= src < len(self._rows)) or not (0 <= dst < len(self._rows)) or src == dst:
            return
        if self.beginMoveRows(QModelIndex(), src, src, QModelIndex(), dst + (dst > src)):
            self._rows.insert(dst, self._rows.pop(src))
            self.endMoveRows()

    def clear_rows(self) -> None:
        if not self._rows:
            return
        self.beginResetModel()
        self._rows.clear()
        self.endResetModel()

    def raw_rows(self) -> list[list[float | None]]:
        return self._rows


class _SpinDelegate(QStyledItemDelegate):
    """数值单元格委托：QDoubleSpinBox，范围/小数位按列定义。"""

    def __init__(self, columns: Sequence[GroupColumn], parent=None):
        super().__init__(parent)
        self._columns = list(columns)

    def createEditor(self, parent, option, index):
        col = self._columns[index.column()]
        editor = QDoubleSpinBox(parent)
        editor.setDecimals(col.decimals)
        editor.setRange(col.minimum, col.maximum)
        editor.setSingleStep(10 ** (-col.decimals))
        editor.setKeyboardTracking(False)
        return editor

    def setEditorData(self, editor, index) -> None:
        text = index.data(Qt.EditRole)
        try:
            editor.setValue(float(text))
        except (TypeError, ValueError):
            editor.setValue(self._columns[index.column()].default)

    def setModelData(self, editor, model, index) -> None:
        model.setData(index, editor.value(), Qt.EditRole)


class GroupsTableEditor(QWidget):
    """分组参数编辑器（ptype="groups" 的通用实现）。"""

    def __init__(self, columns: Sequence[GroupColumn],
                 prefill: Sequence[dict] | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._columns = list(columns)
        self._model = _GroupsModel(self._columns, self)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setItemDelegate(_SpinDelegate(self._columns, self.table))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setDragDropMode(QTableView.InternalMove)
        self.table.setDefaultDropAction(Qt.MoveAction)
        self.table.setDragDropOverwriteMode(False)
        root.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(6)
        for text, handler in (
            ("添加组", self._on_add),
            ("删除选中", self._on_remove),
            ("上移", lambda: self._on_move(-1)),
            ("下移", lambda: self._on_move(1)),
            ("粘贴", self._on_paste),
            ("清空", self._on_clear),
        ):
            btn = QPushButton(text)
            btn.clicked.connect(handler)
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        rows = [r for r in (prefill or []) if isinstance(r, dict)]
        if not rows:
            rows = [{}]
        for row in rows:
            self._model.insert_row(
                self._model.rowCount(),
                [row.get(c.key, c.default) for c in self._columns])

    # ------------------------------------------------------------------ 交互
    def _selected_rows(self) -> list[int]:
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def _on_add(self) -> None:
        rows = self._selected_rows()
        at = rows[-1] + 1 if rows else self._model.rowCount()
        self._model.insert_row(at, None)

    def _on_remove(self) -> None:
        rows = self._selected_rows()
        if not rows and self._model.rowCount():
            rows = [self._model.rowCount() - 1]
        self._model.remove_rows(rows)

    def _on_move(self, delta: int) -> None:
        rows = self._selected_rows()
        if len(rows) != 1:
            return
        src = rows[0]
        self._model.move_row(src, src + delta)

    def _on_clear(self) -> None:
        self._model.clear_rows()

    def _on_paste(self) -> None:
        self.paste_tsv(QApplication.clipboard().text())

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.StandardKey.Paste):
            self._on_paste()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------ API
    def paste_tsv(self, text: str) -> int:
        """粘贴 TSV（Excel 多行多列），返回成功导入行数。"""
        lines = [ln for ln in (text or "").splitlines() if ln.strip()]
        if not lines:
            return 0
        rows = self._selected_rows()
        at = rows[0] if rows else self._model.rowCount()
        imported = 0
        for line in lines:
            cells = line.split("\t")
            values: list[float | None] = []
            for i in range(len(self._columns)):
                try:
                    values.append(float(cells[i].strip()) if i < len(cells) else None)
                except ValueError:
                    values.append(None)
            self._model.insert_row(at, values)
            at += 1
            imported += 1
        return imported

    def value(self) -> list[dict]:
        """导出 list[dict]；含无效值（None）的行整行跳过（旧行为保持）。"""
        out: list[dict] = []
        for raw in self._model.raw_rows():
            if any(v is None for v in raw):
                continue
            out.append({c.key: v for c, v in zip(self._columns, raw)})
        return out

    def invalid_row_count(self) -> int:
        """含无效值的行数（用于 UI 提示"N 行被跳过"）。"""
        return sum(1 for raw in self._model.raw_rows() if any(v is None for v in raw))


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("GroupsTableEditor Demo")
    apply_qss(win, "controls")
    apply_qss(win, "table")
    lay = QVBoxLayout(win)

    cols = [
        GroupColumn("i0_ma", "I0", "mA", 0.0, 500.0, 1, 10.0),
        GroupColumn("i1_ma", "I1", "mA", 0.0, 500.0, 1, 100.0),
        GroupColumn("freq_hz", "频率", "Hz", 0.1, 10000.0, 1, 100.0),
    ]
    editor = GroupsTableEditor(cols, prefill=[{"i0_ma": 5, "i1_ma": 50, "freq_hz": 10}])
    lay.addWidget(editor)

    dump = QPushButton("打印 value()")
    dump.clicked.connect(lambda: print(editor.value(), "invalid:", editor.invalid_row_count()))
    lay.addWidget(dump)

    win.resize(520, 360)
    win.show()
    sys.exit(app.exec())
