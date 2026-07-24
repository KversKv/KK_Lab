# -*- coding: utf-8 -*-
"""SW 物理开关模型: 左右连接端点 + 动态连杆 (拟物化)。

摒弃方框卡片, 直接绘制电路开关符号:
- 输入引线 (左缘 → 左端子) 与画布连线同高 (h//2), 保证与前级 LDO 连线零偏移衔接;
- 连杆以左端子为支点: 闭合时绿色水平搭到右端子, 开路时灰色上倾断开;
- 单击整个模型快速切换闭合/开路, 右键弹出上下文菜单。
"""

import math

from PySide6.QtCore import Qt, Signal, QPoint, QRect, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget

from ui.pages.pmu.pmu_1811.constants import (
    COL_SW, COL_EMERALD, COL_LED_OFF,
    COL_TEXT, COL_TEXT_MUTED, COL_TEXT_DIM, COL_BORDER_HOVER,
    FONT_MONO, CARD_W, CARD_H,
)
from ui.pages.pmu.pmu_1811.models import PmuModule

# 开关符号几何 (x 坐标, 引线 y 恒为 h//2 与画布行中心对齐)
_T1_X = 30        # 左端子 (连杆支点)
_T2_X = 72        # 右端子
_OUT_X = 92       # 输出引线短截终点
_LEVER_DEG = 28   # 开路时连杆上倾角度


class SwitchWidget(QWidget):
    clicked = Signal(str)
    right_clicked = Signal(str, QPoint)
    enable_toggled = Signal(str)      # 单击模型切换闭合/开路

    def __init__(self, mod: PmuModule, parent=None):
        super().__init__(parent)
        self._mod = mod
        self._selected = False
        self._hover = False
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.PointingHandCursor)

    @property
    def module(self) -> PmuModule:
        return self._mod

    def set_selected(self, selected: bool):
        self._selected = selected
        self.update()

    def refresh(self):
        """状态外部变更 (Check 回读 / 面板 / 菜单) 后重绘。"""
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # 单击开关模型: 切换闭合/开路, 同时选中让属性面板跟随
            self._mod.enabled = not self._mod.enabled
            self.update()
            self.clicked.emit(self._mod.id)
            self.enable_toggled.emit(self._mod.id)
            e.accept()
            return
        if e.button() == Qt.RightButton:
            self.right_clicked.emit(self._mod.id, e.globalPosition().toPoint())
            e.accept()
            return
        super().mousePressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cy = h // 2          # 引线 y: 与画布分支连线 (行中心) 精确对齐
        on = self._mod.enabled

        # 选中 / 悬停: 仅圆角边框高亮, 无背景填充保持画布感
        if self._selected or self._hover:
            if self._selected:
                p.setPen(QPen(QColor(COL_SW), 1.5))
            else:
                p.setPen(QPen(QColor(COL_BORDER_HOVER), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 10, 10)

        # 输入引线: 左缘 → 左端子 (玫红, 始终带电, 与上游 VIN 线同色衔接)
        pen = QPen(QColor(COL_SW), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(0, cy, _T1_X, cy)

        # 输出引线: 右端子 → 短截终点 (闭合带电绿 / 开路失电灰)
        pen.setColor(QColor(COL_EMERALD if on else COL_LED_OFF))
        p.setPen(pen)
        p.drawLine(_T2_X, cy, _OUT_X, cy)

        # 连杆: 左端子支点; 闭合绿色水平 / 开路灰色上倾 _LEVER_DEG
        pen = QPen(QColor(COL_EMERALD if on else COL_LED_OFF), 3)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        if on:
            p.drawLine(_T1_X, cy, _T2_X, cy)
        else:
            rad = math.radians(_LEVER_DEG)
            ex = _T1_X + (_T2_X - _T1_X) * math.cos(rad)
            ey = cy - (_T2_X - _T1_X) * math.sin(rad)
            p.drawLine(QPointF(_T1_X, cy), QPointF(ex, ey))

        # 左右连接端子: 玫红实心圆 (物理焊点)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(COL_SW))
        for tx in (_T1_X, _T2_X):
            p.drawEllipse(QPointF(tx, cy), 4, 4)

        # 开关状态文本 (符号右侧)
        p.setPen(QColor(COL_EMERALD if on else COL_TEXT_DIM))
        p.setFont(QFont(FONT_MONO, 9, QFont.Bold))
        p.drawText(QRect(_OUT_X + 10, cy - 8, 80, 16),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "CLOSED" if on else "OPEN")

        # 模块名 (符号下方, 避开连杆摆动区)
        p.setPen(QColor(COL_TEXT if on else COL_TEXT_MUTED))
        p.setFont(QFont(FONT_MONO, 10))
        p.drawText(QRect(2, cy + 8, w - 4, 14),
                   Qt.AlignLeft | Qt.AlignVCenter, self._mod.name)
