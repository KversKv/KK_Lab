"""应用级暗色主题入口（2026-08 视觉重构）.

提供两个函数：
- ``apply_dark_theme(app)``：应用入口统一调用——设定当前 dark token、
  全局 UI 字体（逻辑像素）、注入 ``base.qss`` + ``dark.qss``（滚动条 /
  ToolTip 等真正全局安全的规则）。页面/组件级样式仍走 ``apply_qss``
  局部注入，不在 app 级铺开。
- ``set_state(widget, state)``：动态状态色辅助——``setProperty("state", ...)``
  + ``refresh_style`` 重匹配 QSS 选择器。供页面在**既有状态赋值处追加一行**
  使用，不侵入原状态更新逻辑。
"""
from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget

from ui.theme.theme import dp, load_qss, refresh_style, set_theme
from ui.theme.tokens import Tokens, dark_tokens


def apply_dark_theme(app: QApplication, theme: Tokens | None = None) -> Tokens:
    """在 QApplication 创建后、主窗口构建前调用：统一注入暗色主题。

    返回生效的 Tokens（默认 ``dark_tokens()``，可传入定制实例）。
    """
    t = theme or dark_tokens()
    set_theme(t)
    families = [f.strip().strip('"') for f in t.font_ui.split(",")]
    font = QFont()
    font.setFamilies(families)
    font.setPixelSize(dp(t.font_scale.body))
    app.setFont(font)
    app.setStyleSheet(load_qss("base", t) + "\n" + load_qss("dark", t))
    return t


def set_state(widget: QWidget, state: str | None) -> None:
    """设置语义状态动态属性并重匹配 QSS（``[state="pass"]`` 等选择器）。

    ``state=None`` 清除属性（回到无状态默认外观）。
    """
    widget.setProperty("state", state)
    refresh_style(widget)
