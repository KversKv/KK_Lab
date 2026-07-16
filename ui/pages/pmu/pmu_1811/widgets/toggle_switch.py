# -*- coding: utf-8 -*-
"""iOS 风格拨动开关。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QWidget

from ui.pages.pmu.pmu_1811.constants import COL_EMERALD


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked

    def checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(checked)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.set_checked(not self._checked)
        super().mousePressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h // 2
        if self._checked:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(COL_EMERALD))
            p.drawRoundedRect(0, 0, w, h, r, r)
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(w - h + 2, 2, h - 4, h - 4)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#374151"))
            p.drawRoundedRect(0, 0, w, h, r, r)
            p.setBrush(QColor("#9ca3af"))
            p.drawEllipse(2, 2, h - 4, h - 4)
