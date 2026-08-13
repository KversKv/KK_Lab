"""FormRow / FormGrid — 标准表单行与两列栅格。

- 行结构：label（右对齐）+ editor + unit（单位后置）+ helper/error 行内文本；
- 校验不弹窗：``set_error(msg)`` 给 editor 打 ``invalid`` 动态属性（QSS 红边）
  并把 helper 切为 error 角色（红字），``clear_error()`` 还原；
- ``FormGrid`` 按 columns 分列自动排位，保证整页表单列宽与对齐一致。

为什么这样拆：校验呈现（红边 + 行内文案）是跨页面通用交互，收敛进
FormRow 后页面只调 ``set_error``，不手写 QSS/属性切换。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.theme import refresh_style


class FormRow(QWidget):
    """label + editor + unit + helper/error 的标准表单行。"""

    def __init__(self, label: str, editor: QWidget, *,
                 unit: str = "", helper: str = "",
                 required: bool = False, label_width: int = 96,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._required = required
        self._default_helper = helper

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(6)
        # 先把子布局挂到 root（parent widget=self），再 addWidget：否则
        # 无 parent 的 layout 上 addWidget 不会设控件 parent，控件 isWindow=True，
        # setVisible(True) 时短暂成为独立顶层窗口闪现（standalone 运行时
        # 表现为多个小白框一闪而过）。
        root.addLayout(line)

        text = f"{label} *" if required else label
        self._label = QLabel(text)
        self._label.setObjectName("formLabel")
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.setFixedWidth(label_width)
        line.addWidget(self._label)

        self._editor = editor
        line.addWidget(editor, 1)

        self._unit = QLabel(unit)
        self._unit.setObjectName("formUnit")
        line.addWidget(self._unit)
        self._unit.setVisible(bool(unit))

        self._helper = QLabel(helper)
        self._helper.setProperty("role", "helper")
        helper_lay = QHBoxLayout()
        helper_lay.setContentsMargins(label_width + 6, 0, 0, 0)
        root.addLayout(helper_lay)
        helper_lay.addWidget(self._helper, 1)
        self._helper.setVisible(bool(helper))

    # ------------------------------------------------------------------ API
    @property
    def editor(self) -> QWidget:
        return self._editor

    def label_text(self) -> str:
        return self._label.text()

    def set_error(self, message: str) -> None:
        """行内校验失败：editor 红边 + helper 红字（不弹窗）。"""
        self._editor.setProperty("invalid", True)
        refresh_style(self._editor)
        self._helper.setText(message)
        self._helper.setProperty("role", "helper-error")
        refresh_style(self._helper)
        self._helper.setVisible(True)

    def clear_error(self) -> None:
        self._editor.setProperty("invalid", False)
        refresh_style(self._editor)
        self._helper.setProperty("role", "helper")
        refresh_style(self._helper)
        self._helper.setText(self._default_helper)
        self._helper.setVisible(bool(self._default_helper))

    def set_helper(self, text: str) -> None:
        self._default_helper = text
        if self._helper.property("role") != "helper-error":
            self._helper.setText(text)
            self._helper.setVisible(bool(text))

    def is_required(self) -> bool:
        return self._required


class FormGrid(QWidget):
    """多列表单栅格：按 columns 自动排位，列内对齐。"""

    def __init__(self, *, columns: int = 2, label_width: int = 96,
                 h_spacing: int = 12, v_spacing: int = 8,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._columns = max(1, columns)
        self._label_width = label_width
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(h_spacing)
        self._grid.setVerticalSpacing(v_spacing)
        for c in range(self._columns):
            self._grid.setColumnStretch(c, 1)
        self._rows: list[FormRow] = []

    def add(self, row: FormRow, *, column: int | None = None) -> FormRow:
        """添加一行；column 为空则按序自动排位。"""
        idx = len(self._rows)
        r, c = divmod(idx, self._columns)
        if column is not None:
            c = column % self._columns
        self._grid.addWidget(row, r, c)
        self._rows.append(row)
        return row

    def add_row(self, label: str, editor: QWidget, **kwargs) -> FormRow:
        """便捷入口：构造 FormRow 并添加。"""
        kwargs.setdefault("label_width", self._label_width)
        return self.add(FormRow(label, editor, **kwargs))

    def rows(self) -> list[FormRow]:
        return list(self._rows)

    def clear_errors(self) -> None:
        for row in self._rows:
            row.clear_error()


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QPushButton, QSpinBox, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("Form Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)

    grid = FormGrid(columns=2)
    row_chip = grid.add_row("芯片名称", QLineEdit(), helper="如 BES1307", required=True)
    grid.add_row("模块名称", QLineEdit(), required=True)
    grid.add_row("Vout 标称", QSpinBox(), unit="mV")
    combo = QComboBox()
    combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
    grid.add_row("Vin 通道", combo)
    lay.addWidget(grid)

    btn = QPushButton("模拟校验失败")
    btn.clicked.connect(lambda: row_chip.set_error("芯片名称为必填项"))
    lay.addWidget(btn)
    btn2 = QPushButton("清除校验")
    btn2.clicked.connect(grid.clear_errors)
    lay.addWidget(btn2)

    win.resize(560, 220)
    win.show()
    sys.exit(app.exec())
