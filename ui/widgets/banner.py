"""InfoBanner — 非模态行内提示条（配置缺失 / 仪器未连接 / precheck 失败）。

- severity ∈ info / warning / error / success，着色走
  ``QFrame#InfoBanner[severity=...]``（controls.qss）；
- actions 为 ``(key, label)`` 列表，点击发 ``actionTriggered(str)``；
- 可关闭（``dismissed`` 信号），默认自动 hide 而非销毁。

为什么这样拆：模块测试的"自动弹配置管理器"改为 Banner 后，同类行内
提示（precheck、仪器提醒）复用同一组件，交互语义统一。
"""
from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from ui.theme import refresh_style

_SEVERITIES = ("info", "warning", "error", "success")
_SEVERITY_DOT = {
    "info": "info",
    "warning": "warning",
    "error": "error",
    "success": "success",
}


class InfoBanner(QFrame):
    """非模态提示条。"""

    actionTriggered = Signal(str)
    dismissed = Signal()

    def __init__(self, text: str = "", *,
                 actions: Sequence[tuple[str, str]] = (),
                 severity: str = "info",
                 dismissible: bool = True,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("InfoBanner")
        self._severity = "info"

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 8, 6)
        lay.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setObjectName("bannerDot")
        lay.addWidget(self._dot)

        self._text = QLabel(text)
        self._text.setWordWrap(True)
        lay.addWidget(self._text, 1)

        for key, label in actions:
            btn = QPushButton(label)
            btn.setObjectName("bannerAction")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _c=False, k=key: self.actionTriggered.emit(k))
            lay.addWidget(btn)

        if dismissible:
            close = QPushButton("✕")
            close.setObjectName("bannerClose")
            close.setCursor(Qt.PointingHandCursor)
            close.setToolTip("关闭提示")
            close.clicked.connect(self._on_dismiss)
            lay.addWidget(close)

        self.set_severity(severity)

    def _on_dismiss(self) -> None:
        self.hide()
        self.dismissed.emit()

    def set_text(self, text: str) -> None:
        self._text.setText(text)

    def set_severity(self, severity: str) -> None:
        if severity not in _SEVERITIES:
            severity = "info"
        self._severity = severity
        self.setProperty("severity", severity)
        self._dot.setProperty("state", _SEVERITY_DOT[severity])
        refresh_style(self)
        refresh_style(self._dot)

    def severity(self) -> str:
        return self._severity


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("InfoBanner Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)

    b1 = InfoBanner("尚未加载配置。", severity="info",
                    actions=[("choose", "选择配置"), ("default", "使用默认")])
    b1.actionTriggered.connect(lambda k: print("action:", k))
    lay.addWidget(b1)
    lay.addWidget(InfoBanner("示波器未连接，3 个勾选项需要示波器。", severity="warning"))
    lay.addWidget(InfoBanner("必填字段缺失：芯片名称。", severity="error"))
    lay.addWidget(InfoBanner("配置已保存。", severity="success"))
    lay.addStretch()

    win.resize(560, 240)
    win.show()
    sys.exit(app.exec())
