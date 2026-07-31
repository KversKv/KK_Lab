"""Toast — 右下角轻提示（3s 自动消失）。

用法：``Toast.popup(parent, "配置已保存", severity="success")``。
- 作为 parent 的无框子控件浮于右下角，不抢焦点、不阻塞；
- 跟随 parent 移动/缩放（eventFilter 重定位）；
- 多条 Toast 依次向上堆叠（按同类现存实例数偏移）。

为什么这样拆：保存成功/报告生成这类"确认型反馈"不需要模态，Toast
语义最轻；堆叠与定位逻辑收敛此处，调用方一行搞定。
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

_MARGIN = 16
_SPACING = 8


class Toast(QFrame):
    """右下角自动消失的轻提示。"""

    def __init__(self, parent: QWidget, text: str, *,
                 severity: str = "info", duration_ms: int = 3000):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setProperty("severity", severity if severity in
                         ("info", "success", "warning", "error") else "info")
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)
        dot = QLabel("●")
        dot.setProperty("state", {
            "info": "info", "success": "success",
            "warning": "warning", "error": "error",
        }.get(self.property("severity"), "info"))
        lay.addWidget(dot)
        label = QLabel(text)
        lay.addWidget(label)

        parent.installEventFilter(self)
        self.adjustSize()
        self._reposition()
        QTimer.singleShot(duration_ms, self._expire)

    # ------------------------------------------------------------------ API
    @staticmethod
    def popup(parent: QWidget, text: str, *, severity: str = "info",
              duration_ms: int = 3000) -> "Toast":
        """创建并展示一条 Toast（命名 popup 避免遮蔽 QWidget.show 实例方法）。"""
        toast = Toast(parent, text, severity=severity, duration_ms=duration_ms)
        toast.show()
        toast.raise_()
        return toast

    # ------------------------------------------------------------------ 内部
    def _expire(self) -> None:
        self.hide()
        self.deleteLater()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        # 现存同类实例数量决定向上偏移（先建的更靠下，保持时序可读）
        siblings = [w for w in parent.findChildren(Toast) if w is not self and w.isVisible()]
        offset = sum(w.height() + _SPACING for w in siblings)
        x = parent.width() - self.width() - _MARGIN
        y = parent.height() - self.height() - _MARGIN - offset
        self.move(max(x, _MARGIN), max(y, _MARGIN))

    def eventFilter(self, watched, event) -> bool:
        if watched is self.parentWidget() and event.type() in (
                QEvent.Resize, QEvent.Move):
            self._reposition()
        return super().eventFilter(watched, event)


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("Toast Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)
    for sev in ("info", "success", "warning", "error"):
        btn = QPushButton(f"弹出 {sev} Toast")
        btn.clicked.connect(
            lambda _c=False, s=sev: Toast.popup(win, f"这是一条 {s} 提示", severity=s))
        lay.addWidget(btn)
    lay.addStretch()
    win.resize(480, 320)
    win.show()
    sys.exit(app.exec())
