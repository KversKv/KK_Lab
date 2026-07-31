"""Card — 可折叠卡片容器（替代旧 CollapsibleGroupBox）。

- 标题栏右侧可放操作控件（``actions``）；
- 折叠动画：``QPropertyAnimation`` 作用于内容区 ``maximumHeight``
  （180ms / OutCubic），展开结束后解除高度上限，避免内容变化被裁；
- 折叠状态可用 ``settings_key`` 持久化到 QSettings；
- 旧类兼容：``CollapsibleGroupBox = Card`` 由引用方 shim 提供（P3）。

为什么这样拆：折叠/持久化/动画全部收敛在 Card 内部，页面只面对
``content_layout`` 填内容；动画目标高度统一由本类计算，避免各处手写。
"""
from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

_ARROW_EXPANDED = "▼"
_ARROW_COLLAPSED = "▶"
_ANIM_MS = 180


class Card(QFrame):
    """带标题栏（可选折叠）的卡片容器。"""

    toggled = Signal(bool)  # True = 展开

    def __init__(self, title: str = "", *,
                 actions: Sequence[QWidget] = (),
                 collapsible: bool = False,
                 collapsed: bool = False,
                 settings_key: str | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._title = title
        self._collapsible = collapsible
        self._settings_key = settings_key
        self._expanded = not collapsed

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # —— 标题栏：左侧标题按钮（折叠开关），右侧 actions ——
        header = QWidget()
        header.setObjectName("cardHeaderRow")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(4, 4, 8, 4)
        header_lay.setSpacing(4)

        self._header_btn = QPushButton()
        self._header_btn.setObjectName("cardHeader")
        self._header_btn.setFlat(True)
        self._header_btn.setCursor(
            Qt.PointingHandCursor if collapsible else Qt.ArrowCursor)
        if collapsible:
            self._header_btn.clicked.connect(self.toggle)
        header_lay.addWidget(self._header_btn, 1)
        for w in actions:
            header_lay.addWidget(w)
        root.addWidget(header)

        # —— 内容区 ——
        self._content = QFrame()
        self._content.setObjectName("cardContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(10, 8, 10, 10)
        self._content_layout.setSpacing(6)
        root.addWidget(self._content)

        self._anim = QPropertyAnimation(self._content, b"maximumHeight", self)
        self._anim.setDuration(_ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        if settings_key:
            saved = QSettings().value(
                f"card/{settings_key}/collapsed", None)
            if saved is not None:
                self._expanded = str(saved).lower() not in ("true", "1")
        self._apply_expanded_immediate()
        self._refresh_title()

    # ------------------------------------------------------------------ API
    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def content_widget(self) -> QFrame:
        return self._content

    def set_title(self, title: str) -> None:
        self._title = title
        self._refresh_title()

    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool, *, animated: bool = True) -> None:
        if expanded == self._expanded and not self._anim.state():
            return
        self._expanded = expanded
        self._save_state()
        if animated:
            self._start_anim(expanded)
        else:
            self._anim.stop()
            self._apply_expanded_immediate()
        self._refresh_title()
        self.toggled.emit(expanded)

    # ------------------------------------------------------------------ 内部
    def _refresh_title(self) -> None:
        if self._collapsible:
            arrow = _ARROW_EXPANDED if self._expanded else _ARROW_COLLAPSED
            self._header_btn.setText(f"{arrow}  {self._title}")
        else:
            self._header_btn.setText(self._title)

    def _apply_expanded_immediate(self) -> None:
        self._content.setVisible(self._expanded)
        self._content.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX

    def _start_anim(self, expanding: bool) -> None:
        self._anim.stop()
        content = self._content
        content.setVisible(True)
        target_h = content.sizeHint().height()
        if expanding:
            content.setMaximumHeight(0)
            self._anim.setStartValue(0)
            self._anim.setEndValue(max(target_h, 1))
        else:
            self._anim.setStartValue(content.height())
            self._anim.setEndValue(0)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._expanded:
            self._content.setMaximumHeight(16777215)
        else:
            self._content.setVisible(False)
            self._content.setMaximumHeight(16777215)

    def _save_state(self) -> None:
        if self._settings_key:
            QSettings().setValue(
                f"card/{self._settings_key}/collapsed", not self._expanded)


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

    from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout

    from ui.theme import apply_qss

    app = QApplication(sys.argv)
    win = QWidget()
    win.setWindowTitle("Card Demo")
    apply_qss(win, "controls")
    lay = QVBoxLayout(win)

    act = QPushButton("打开")
    act.setProperty("variant", "ghost")
    card1 = Card("DUT 配置", actions=[act], collapsible=True,
                 settings_key="demo/dut")
    card1.content_layout.addWidget(QLabel("芯片名称: BES1307"))
    card1.content_layout.addWidget(QLabel("模块名称: LDO1"))
    lay.addWidget(card1)

    card2 = Card("不可折叠卡片", collapsible=False)
    card2.content_layout.addWidget(QLabel("固定内容"))
    lay.addWidget(card2)
    lay.addStretch()

    win.resize(420, 300)
    win.show()
    sys.exit(app.exec())
