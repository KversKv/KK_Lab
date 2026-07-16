# -*- coding: utf-8 -*-
"""模块卡片: LED + 名称 + 电压步进 (+/−) + 齿轮按钮。"""

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QHBoxLayout, QGraphicsDropShadowEffect,
)

from ui.pages.pmu.pmu_1811.constants import (
    COL_TEXT, COL_TEXT_DIM, COL_TEXT_MUTED, COL_CARD_BG, COL_CARD_BG_SELECTED,
    COL_BORDER, COL_BORDER_HOVER, COL_BORDER_SELECTED, COL_EMERALD, COL_LED_OFF,
    FONT_MONO, CARD_W, CARD_H,
)
from ui.pages.pmu.pmu_1811.models import PmuModule


class ModuleCard(QFrame):
    clicked = Signal(str)
    right_clicked = Signal(str, QPoint)
    gear_clicked = Signal(str, QPoint)
    voltage_stepped = Signal(str, float)

    def __init__(self, mod: PmuModule, parent=None):
        super().__init__(parent)
        self._mod = mod
        self._selected = False
        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("moduleCard")

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(QColor(COL_BORDER_SELECTED))
        self._shadow.setEnabled(True)
        self.setGraphicsEffect(self._shadow)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(8)

        self.led = QLabel(self)
        self.led.setFixedSize(10, 10)
        self.led.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.name_lbl = QLabel(mod.name, self)
        self.name_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px; font-weight:600; background:transparent;"
        )
        self.name_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.minus_btn = QPushButton("−", self)
        self.minus_btn.setFixedSize(22, 22)
        self.minus_btn.setObjectName("cardStepBtn")
        self.minus_btn.setCursor(Qt.PointingHandCursor)
        self.minus_btn.setFocusPolicy(Qt.NoFocus)

        self.volt_lbl = QLabel(self)
        self.volt_lbl.setStyleSheet(
            f"color:{COL_EMERALD}; font-family:{FONT_MONO}; font-size:12px; font-weight:700; background:transparent;"
        )
        self.volt_lbl.setMinimumWidth(52)
        self.volt_lbl.setAlignment(Qt.AlignCenter)

        self.plus_btn = QPushButton("+", self)
        self.plus_btn.setFixedSize(22, 22)
        self.plus_btn.setObjectName("cardStepBtn")
        self.plus_btn.setCursor(Qt.PointingHandCursor)
        self.plus_btn.setFocusPolicy(Qt.NoFocus)

        self.gear_btn = QPushButton("⚙", self)
        self.gear_btn.setFixedSize(22, 22)
        self.gear_btn.setObjectName("cardGearBtn")
        self.gear_btn.setCursor(Qt.PointingHandCursor)
        self.gear_btn.setFocusPolicy(Qt.NoFocus)
        self.gear_btn.setVisible(False)

        lay.addWidget(self.led)
        lay.addWidget(self.name_lbl)
        lay.addStretch(1)
        lay.addWidget(self.minus_btn)
        lay.addWidget(self.volt_lbl)
        lay.addWidget(self.plus_btn)
        lay.addWidget(self.gear_btn)

        self.minus_btn.clicked.connect(lambda: self._step(-1))
        self.plus_btn.clicked.connect(lambda: self._step(1))
        self.gear_btn.clicked.connect(
            lambda: self.gear_clicked.emit(self._mod.id, self.gear_btn.mapToGlobal(QPoint(0, 0)))
        )

        self.refresh()

    @property
    def module(self) -> PmuModule:
        return self._mod

    def _step(self, dir_: int):
        v = self._mod.voltage + dir_ * self._mod.step
        v = max(self._mod.min_voltage, min(self._mod.max_voltage, v))
        if abs(v - self._mod.voltage) < 1e-9:
            return
        self._mod.voltage = v
        self.refresh()
        self.voltage_stepped.emit(self._mod.id, v)

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self._shadow.setBlurRadius(18)
        else:
            self._shadow.setBlurRadius(0)
        self.refresh()

    def refresh(self):
        self.volt_lbl.setText(f"{self._mod.voltage:.3f} V")
        led_col = COL_EMERALD if self._mod.enabled else COL_LED_OFF
        self.led.setStyleSheet(
            f"background:{led_col}; border-radius:5px; border:none;"
        )
        if self._mod.enabled:
            fg, bg, border = COL_TEXT, COL_CARD_BG, COL_BORDER
            if self._selected:
                fg, bg, border = COL_TEXT, COL_CARD_BG_SELECTED, COL_BORDER_SELECTED
        else:
            base_bg = COL_CARD_BG_SELECTED if self._selected else COL_CARD_BG
            base_border = COL_BORDER_SELECTED if self._selected else COL_BORDER
            fg, bg, border = COL_TEXT_DIM, base_bg, base_border
        # disabled 整体降透明度：用半透明背景模拟
        if not self._mod.enabled:
            bg = "#11182799"
        self.setStyleSheet(
            f"QFrame#moduleCard {{ background:{bg}; border:1px solid {border};"
            f" border-radius:10px; }}"
            f"QFrame#moduleCard:hover {{ border:1px solid {COL_BORDER_HOVER}; }}"
            f"QPushButton#cardStepBtn {{ background:{COL_BORDER}; color:{COL_TEXT};"
            f" border:none; border-radius:6px; font-weight:700; }}"
            f"QPushButton#cardStepBtn:hover {{ background:{COL_BORDER_HOVER}; }}"
            f"QPushButton#cardGearBtn {{ background:{COL_BORDER}; color:{COL_TEXT_MUTED};"
            f" border:none; border-radius:6px; font-size:13px; }}"
            f"QPushButton#cardGearBtn:hover {{ background:{COL_BORDER_HOVER}; color:{COL_EMERALD}; }}"
        )
        self.name_lbl.setStyleSheet(
            f"color:{fg}; font-family:{FONT_MONO}; font-size:12px; font-weight:600; background:transparent;"
        )
        self.volt_lbl.setStyleSheet(
            f"color:{COL_EMERALD if self._mod.enabled else COL_TEXT_DIM};"
            f" font-family:{FONT_MONO}; font-size:12px; font-weight:700; background:transparent;"
        )

    def enterEvent(self, e):
        self.gear_btn.setVisible(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.gear_btn.setVisible(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self._mod.id)
            e.accept()
            return
        elif e.button() == Qt.RightButton:
            self.right_clicked.emit(self._mod.id, e.globalPosition().toPoint())
            e.accept()
            return
        super().mousePressEvent(e)
