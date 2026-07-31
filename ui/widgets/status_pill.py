"""StatusPill — 连接/运行状态徽标（圆点 + 文案 + tooltip）。

状态语义：idle(灰) / connecting(黄) / connected(绿) / error(红) / warning(黄)。
颜色走 QSS ``QLabel[state=...]``（controls.qss），组件内零色值。
tooltip 用于展示 VISA 地址、型号、固件等详情（调用方组字符串传入）。

为什么这样拆：状态着色全部交给 QSS 动态属性选择器，组件只维护 state 属性
与文案，换主题/加状态都不动 Python。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui.theme import refresh_style

_STATES = ("idle", "connecting", "connected", "error", "warning")
# 组件状态 → QSS 选择器 state 值（QLabel[state=...] 规则）
_QSS_STATE = {
    "idle": "muted",
    "connecting": "warning",
    "connected": "success",
    "error": "error",
    "warning": "warning",
}


class StatusPill(QWidget):
    """圆点 + 文案的状态徽标。"""

    def __init__(self, text: str = "", state: str = "idle",
                 tooltip: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("StatusPill")
        self._state = "idle"

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self._dot = QLabel("●")
        self._dot.setObjectName("pillDot")
        self._text = QLabel(text)
        self._text.setObjectName("pillText")
        lay.addWidget(self._dot)
        lay.addWidget(self._text)

        self.set_state(state)
        if tooltip:
            self.setToolTip(tooltip)

    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        """切换状态（未知值回退 idle），并刷新 QSS 选择器匹配。"""
        if state not in _STATES:
            state = "idle"
        self._state = state
        qss_state = _QSS_STATE[state]
        self._dot.setProperty("state", qss_state)
        refresh_style(self._dot)
        self.setProperty("status", state)  # 供容器级 QSS/测试断言
        self.setToolTip(self.toolTip())  # 触发 tooltip 区域更新

    def set_text(self, text: str) -> None:
        self._text.setText(text)

    def text(self) -> str:
        return self._text.text()

    def set_tooltip(self, text: str) -> None:
        self.setToolTip(text)


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("StatusPill Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)
    for state in ("idle", "connecting", "connected", "error", "warning"):
        pill = StatusPill(f"N6705C — {state}", state,
                          tooltip="TCPIP0::K-N6705C-06098::hislip0\n型号: N6705C\n固件: D.04.08")
        lay.addWidget(pill)
    win.show()
    sys.exit(app.exec())
