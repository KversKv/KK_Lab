"""AppTopBar：自绘标题栏（无边框窗口的客户端装饰 / CSD）。

参考 VSCode / 飞书做法：窗口设 FramelessWindowHint 后，由本控件统一绘制
左侧应用图标 + 名称、右侧 AI 面板按钮、窗口控制按钮（最小化 / 最大化-还原 / 关闭）。
标题栏与窗体同色融合；空白区域支持拖动窗口、双击最大化 / 还原。

控件高度单一权威：窗口控制按钮用 ID 选择器钉死尺寸，不在父级 QSS 写裸规则。
"""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ui.ai.ai_panel_button import AIPanelButton
from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_pixmap

_TITLE_BAR_HEIGHT = 32

_APP_ICON_SVG = os.path.join(get_resource_base(), "resources", "icons", "kk_lab.svg")

_BAR_STYLE = """
QWidget#appTopBar {
    background-color: #020618;
}
QWidget#appTopBar QLabel {
    background: transparent;
    border: none;
}
QLabel#appTitleText {
    color: #c6d4f2;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    background: transparent;
    border: none;
}
QPushButton#winCtrlBtn,
QPushButton#winCloseBtn {
    min-width: 46px;
    max-width: 46px;
    min-height: 32px;
    max-height: 32px;
    padding: 0px;
    border: none;
    border-radius: 0px;
    background-color: transparent;
}
QPushButton#winCtrlBtn:hover {
    background-color: #1b2640;
}
QPushButton#winCloseBtn:hover {
    background-color: #e81123;
}
"""


def _caption_icon(kind: str, color: str = "#c6d4f2", size: int = 12) -> QIcon:
    """绘制 TRAE / Windows 11 风格的窗口控制图标（细线条、1px 描边、无填充）。

    图形绘制在 size×size 画布的居中内框（四周留 1px 边距），保证 QIcon 在
    按钮内垂直 / 水平居中，不出现偏上 / 偏下。
    """
    from PySide6.QtCore import QRectF

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(1.0)
    pen.setCosmetic(True)
    painter.setPen(pen)

    pad = 1.5
    x0 = pad
    y0 = pad
    x1 = size - pad
    y1 = size - pad
    cy = size / 2.0
    if kind == "min":
        painter.drawLine(QRectF(x0, cy, x1 - x0, 0).topLeft(),
                         QRectF(x1, cy, 0, 0).topLeft())
    elif kind == "max":
        painter.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))
    elif kind == "restore":
        off = 3.0
        rect_w = (x1 - x0) - off
        rect_h = (y1 - y0) - off
        painter.drawRect(QRectF(x0, y0 + off, rect_w, rect_h))
        painter.drawLine(QRectF(x0 + off, y0, 0, 0).topLeft(),
                         QRectF(x1, y0, 0, 0).topLeft())
        painter.drawLine(QRectF(x1, y0, 0, 0).topLeft(),
                         QRectF(x1, y1 - off, 0, 0).topLeft())
    elif kind == "close":
        painter.drawLine(QRectF(x0, y0, 0, 0).topLeft(),
                         QRectF(x1, y1, 0, 0).topLeft())
        painter.drawLine(QRectF(x1, y0, 0, 0).topLeft(),
                         QRectF(x0, y1, 0, 0).topLeft())
    painter.end()
    return QIcon(pixmap)


class AppTopBar(QWidget):
    """自绘标题栏。承载应用标识、AI 面板按钮、窗口控制按钮，并代理窗口拖动 / 最大化。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("appTopBar")
        self.setFixedHeight(_TITLE_BAR_HEIGHT)
        self.setStyleSheet(_BAR_STYLE)

        self._window = self.window()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(8)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(16, 16)
        if os.path.isfile(_APP_ICON_SVG):
            self._icon_label.setPixmap(tinted_svg_pixmap(_APP_ICON_SVG, "#15d1a3", 16))
        layout.addWidget(self._icon_label, 0, Qt.AlignVCenter)

        self._title_label = QLabel("KK LAB")
        self._title_label.setObjectName("appTitleText")
        layout.addWidget(self._title_label, 0, Qt.AlignVCenter)

        layout.addStretch(1)

        self.ai_panel_button = AIPanelButton(self)
        layout.addWidget(self.ai_panel_button, 0, Qt.AlignVCenter)

        layout.addSpacing(6)

        self._min_btn = self._make_caption_button("winCtrlBtn", "min", "最小化", self._on_minimize)
        layout.addWidget(self._min_btn, 0, Qt.AlignVCenter)

        self._max_btn = self._make_caption_button("winCtrlBtn", "max", "最大化", self._on_toggle_max)
        layout.addWidget(self._max_btn, 0, Qt.AlignVCenter)

        self._close_btn = self._make_caption_button("winCloseBtn", "close", "关闭", self._on_close)
        layout.addWidget(self._close_btn, 0, Qt.AlignVCenter)

        self._interactive_widgets = [
            self.ai_panel_button,
            self._min_btn,
            self._max_btn,
            self._close_btn,
        ]

    def _make_caption_button(self, object_name, kind, tooltip, slot):
        btn = QPushButton(self)
        btn.setObjectName(object_name)
        btn.setIcon(_caption_icon(kind))
        btn.setIconSize(QSize(12, 12))
        btn.setCursor(QCursor(Qt.ArrowCursor))
        btn.setToolTip(tooltip)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.clicked.connect(slot)
        return btn

    def sync_max_icon(self):
        if self._window is not None and self._window.isMaximized():
            self._max_btn.setIcon(_caption_icon("restore"))
            self._max_btn.setToolTip("还原")
        else:
            self._max_btn.setIcon(_caption_icon("max"))
            self._max_btn.setToolTip("最大化")

    def _on_minimize(self):
        if self._window is not None:
            self._window.showMinimized()

    def _on_toggle_max(self):
        if self._window is None:
            return
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()
        self.sync_max_icon()

    def _on_close(self):
        if self._window is not None:
            self._window.close()

    def is_caption_window_point(self, win_x, win_y, dpr) -> bool:
        """判断窗口内物理偏移坐标是否落在标题栏可拖动区域（不在交互控件上）。

        win_x / win_y 为相对宿主窗口左上角的物理像素偏移，与宿主窗口
        WM_NCHITTEST 中使用的坐标系完全一致，避免高 DPI 下的换算偏移。
        返回 True 时，宿主窗口将该点报告为 HTCAPTION。
        """
        dpr = dpr or 1.0
        window = self.window()
        for widget in self._interactive_widgets:
            if widget is None or not widget.isVisible():
                continue
            top_left = widget.mapTo(window, widget.rect().topLeft())
            left = top_left.x() * dpr
            top = top_left.y() * dpr
            right = left + widget.width() * dpr
            bottom = top + widget.height() * dpr
            if left <= win_x <= right and top <= win_y <= bottom:
                return False
        return True
