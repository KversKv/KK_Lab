"""EmptyState — 空态占位（结果区 / 日志区无数据时）。

图标（文本字形）+ 标题 + 提示 + 可选动作按钮。

为什么这样拆：空态是"有数据前的默认视图"，独立组件让 ResultTable /
LogPanel 等处不必各自拼 QLabel 堆叠。
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyState(QWidget):
    """空态占位组件。"""

    def __init__(self, icon: str = "▦", title: str = "", hint: str = "",
                 action: tuple[str, Callable[[], None]] | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 24, 0, 24)
        lay.setSpacing(6)

        self._icon = QLabel(icon)
        self._icon.setObjectName("emptyIcon")
        self._icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._icon)

        self._title = QLabel(title)
        self._title.setObjectName("emptyTitle")
        self._title.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._title)

        self._hint = QLabel(hint)
        self._hint.setObjectName("emptyHint")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setWordWrap(True)
        lay.addWidget(self._hint)
        # setVisible 必须在 addWidget（设 parent）之后，避免无 parent 的 QLabel
        # 短暂成为独立顶层窗口闪现（见 form.py 同类注释）。
        self._hint.setVisible(bool(hint))

        if action is not None:
            text, handler = action
            btn = QPushButton(text)
            btn.setProperty("variant", "ghost")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(handler)
            lay.addWidget(btn, alignment=Qt.AlignCenter)

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_hint(self, text: str) -> None:
        self._hint.setText(text)
        self._hint.setVisible(bool(text))


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("EmptyState Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)
    lay.addWidget(EmptyState(
        icon="▦", title="暂无测试结果",
        hint="勾选测试项并点击「开始测试」后，结果将显示在这里。",
        action=("开始测试", lambda: print("start")),
    ))
    win.resize(420, 260)
    win.show()
    sys.exit(app.exec())
