# -*- coding: utf-8 -*-
"""_MiniSlideToggle — ASCII/HEX 迷你滑动开关（原 serialCom_module_frame.py 拆出）。"""

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QWidget
from ui.modules.serialCom_module.serial_style import toggle_colors

class _MiniSlideToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, left="ASCII", right="HEX", parent=None):
        super().__init__(parent)
        self._left = left
        self._right = right
        self._value = left
        self._anim_progress = 0.0

        # 运行期懒导入避免循环依赖；_TOGGLE_W 为 ToolbarMixin 类属性，经继承解析
        from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin
        self.setFixedSize(SerialComMixin._TOGGLE_W, 24)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def value(self):
        return self._value

    def set_value(self, val):
        if val not in (self._left, self._right):
            return
        if val == self._value:
            return
        self._value = val
        target = 1.0 if val == self._right else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = self._right if self._value == self._left else self._left
            self._value = new_val
            target = 1.0 if new_val == self._right else 0.0
            self._anim.stop()
            self._anim.setStartValue(self._anim_progress)
            self._anim.setEndValue(target)
            self._anim.start()
            self.toggled.emit(self._value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        outer_r = 6

        colors = toggle_colors()
        p.setPen(QPen(QColor(colors["border"]), 1))
        p.setBrush(QColor(colors["background"]))
        p.drawRoundedRect(QRectF(0, 0, w, h), outer_r, outer_r)

        knob_margin = 2
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_r = 3

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(colors["knob"]))
        p.drawRoundedRect(QRectF(knob_x, knob_margin, knob_w, knob_h),
                          knob_r, knob_r)

        font = p.font()
        font.setPixelSize(10)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        left_rect = QRectF(0, 0, w / 2, h)
        right_rect = QRectF(w / 2, 0, w / 2, h)

        p.setPen(QColor(colors["active_text"]) if self._anim_progress < 0.5 else QColor(colors["inactive_text"]))
        p.drawText(left_rect, Qt.AlignCenter, self._left)

        p.setPen(QColor(colors["active_text"]) if self._anim_progress >= 0.5 else QColor(colors["inactive_text"]))
        p.drawText(right_rect, Qt.AlignCenter, self._right)

        p.end()
