"""Segmented — 分段选择控件（LDO / DCDC 模块切换）。

样式：容器 ``QFrame#Segmented`` + 选项 ``QPushButton#segmentItem:checked``
（controls.qss）。信号 ``currentChanged(str)`` 携带选中项 key。

为什么这样拆：选项只认 (key, label)，不知道"模块"语义；页面层注入
("ldo","LDO") / ("dcdc","DCDC")，组件保持纯展示与选择。
"""
from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QWidget


class Segmented(QFrame):
    """单选分段控件。"""

    currentChanged = Signal(str)

    def __init__(self, items: Sequence, parent: QWidget | None = None):
        """items: ``[(key, label), ...]`` 或 ``[key, ...]``（label 同 key）。"""
        super().__init__(parent)
        self.setObjectName("Segmented")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}

        for entry in items:
            key, label = entry if isinstance(entry, (tuple, list)) else (entry, str(entry))
            btn = QPushButton(str(label))
            btn.setObjectName("segmentItem")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            self._group.addButton(btn)
            self._buttons[str(key)] = btn
            lay.addWidget(btn)
            # 捕获 key，避免闭包晚绑定
            btn.clicked.connect(lambda _checked=False, k=str(key): self._on_clicked(k))

        if self._buttons:
            first = next(iter(self._buttons))
            self._buttons[first].setChecked(True)
            self._current = first
        else:
            self._current = ""

    def _on_clicked(self, key: str) -> None:
        if key == self._current:
            return
        self._current = key
        self.currentChanged.emit(key)

    def current_key(self) -> str:
        return self._current

    def set_current_key(self, key: str, *, emit: bool = True) -> None:
        """外部驱动切换（如 nav_controller 经 set_current_test）。"""
        btn = self._buttons.get(key)
        if btn is None:
            return
        changed = key != self._current
        self._current = key
        btn.setChecked(True)
        if changed and emit:
            self.currentChanged.emit(key)

    def keys(self) -> list[str]:
        return list(self._buttons)


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("Segmented Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)
    seg = Segmented([("ldo", "LDO"), ("dcdc", "DCDC")])
    hint = QLabel(f"当前: {seg.current_key()}")
    seg.currentChanged.connect(lambda k: hint.setText(f"当前: {k}"))
    lay.addWidget(seg)
    lay.addWidget(hint)
    win.show()
    sys.exit(app.exec())
