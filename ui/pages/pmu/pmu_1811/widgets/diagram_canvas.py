# -*- coding: utf-8 -*-
"""拓扑画布: VSYS 主母线 + 子母线级联 + 模块卡片连线。"""

from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget

from ui.pages.pmu.pmu_1811.constants import (
    COL_CANVAS_BG, COL_AMBER, COL_AMBER_LINE, COL_BLUE, COL_BLUE_LINE, FONT_MONO,
    VSYS_X, CARD_X_L1, CARD_X_L2, CARD_W, CARD_H, ROW_H, TOP_PAD,
    SUB_BUS_X, BUS_PILL_W, BUS_PILL_H, BUS_PILL_X,
)
from ui.pages.pmu.pmu_1811.models import _LAYOUT_ROWS
from ui.pages.pmu.pmu_1811.widgets.module_card import ModuleCard


class DiagramCanvas(QWidget):
    module_selected = Signal(str)
    module_right_clicked = Signal(str, QPoint)
    voltage_stepped = Signal(str, float)

    def __init__(self, modules: dict, parent=None):
        super().__init__(parent)
        self._modules = modules
        self._cards = {}
        self._rows = []  # (row:LayoutRow, y_center)

        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(self.backgroundRole(), QColor(COL_CANVAS_BG))
        self.setPalette(pal)

        self._build()
        n = len(_LAYOUT_ROWS)
        self.setFixedSize(
            CARD_X_L2 + CARD_W + 36,
            TOP_PAD * 2 + n * ROW_H,
        )

    def _build(self):
        for i, row in enumerate(_LAYOUT_ROWS):
            y_center = TOP_PAD + i * ROW_H + CARD_H // 2
            self._rows.append((row, y_center))
            if row.kind == "module":
                mod = self._modules[row.id]
                card = ModuleCard(mod, self)
                x = CARD_X_L1 if row.level == 1 else CARD_X_L2
                card.move(x, TOP_PAD + i * ROW_H)
                card.clicked.connect(self.module_selected.emit)
                card.right_clicked.connect(self.module_right_clicked.emit)
                card.gear_clicked.connect(self.module_right_clicked.emit)
                card.voltage_stepped.connect(self.voltage_stepped.emit)
                self._cards[row.id] = card

    def get_card(self, mod_id: str):
        return self._cards.get(mod_id)

    def clear_selection(self):
        for c in self._cards.values():
            c.set_selected(False)

    def set_selected(self, mod_id: str):
        self.clear_selection()
        c = self._cards.get(mod_id)
        if c:
            c.set_selected(True)

    def refresh_card(self, mod_id: str):
        c = self._cards.get(mod_id)
        if c:
            c.refresh()

    def _row_index(self, pred):
        for i, (r, _) in enumerate(self._rows):
            if pred(r):
                return i
        return -1

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # VSYS 主母线（琥珀色），从第一个 VSYS 行到最后一个 VSYS 行
        vsys_rows = [yc for r, yc in self._rows if r.input == "VSYS" or r.kind == "bus"]
        if vsys_rows:
            pen = QPen(QColor(COL_AMBER), 3)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(VSYS_X, vsys_rows[0], VSYS_X, vsys_rows[-1])

        # VSYS 标签
        p.setPen(QColor(COL_AMBER))
        p.setFont(QFont(FONT_MONO, 9, QFont.Bold))
        p.drawText(QRect(VSYS_X - 16, vsys_rows[0] - 26, 48, 18),
                   Qt.AlignLeft, "VSYS")

        # 一级模块 / 母线 → VSYS 的横向连线（琥珀）
        pen = QPen(QColor(COL_AMBER_LINE), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        for r, yc in self._rows:
            if r.level == 1:
                p.drawLine(VSYS_X, yc, CARD_X_L1 if r.kind == "module" else BUS_PILL_X, yc)

        # 子母线（蓝色）：对每个 bus 与级联父节点，画竖线 + 子节点连线
        self._draw_subtree(p, "vdd_l14_15")
        self._draw_subtree(p, "vdd_l5")
        self._draw_subtree(p, "BUCK_01")

        # 母线药丸
        p.setFont(QFont(FONT_MONO, 9, QFont.Bold))
        for r, yc in self._rows:
            if r.kind == "bus":
                rect = QRect(BUS_PILL_X, yc - BUS_PILL_H // 2, BUS_PILL_W, BUS_PILL_H)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#1f2937"))
                p.drawRoundedRect(rect, 8, 8)
                p.setPen(QColor(COL_BLUE))
                p.drawText(rect, Qt.AlignCenter, r.bus_name)

    def _draw_subtree(self, p, parent_id: str):
        parent_idx = self._row_index(lambda r: (r.kind == "bus" and r.bus_name == parent_id) or
                                    (r.kind == "module" and r.id == parent_id))
        if parent_idx < 0:
            return
        children = [(i, r, yc) for i, (r, yc) in enumerate(self._rows)
                    if r.kind == "module" and r.input == parent_id]
        if not children:
            return
        _, p_yc = self._rows[parent_idx]
        last_yc = children[-1][2]

        pen = QPen(QColor(COL_BLUE_LINE), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        # 父节点 → 子母线竖线起点（短横）
        if parent_id in ("vdd_l14_15", "vdd_l5"):
            p.drawLine(BUS_PILL_X + BUS_PILL_W, p_yc, SUB_BUS_X, p_yc)
        else:
            # 级联：从父卡片右边引出
            p.drawLine(CARD_X_L1 + CARD_W, p_yc, SUB_BUS_X, p_yc)

        # 子母线竖线
        p.drawLine(SUB_BUS_X, p_yc, SUB_BUS_X, last_yc)
        # 各子节点横线
        for _, r, yc in children:
            p.drawLine(SUB_BUS_X, yc, CARD_X_L2, yc)

    def mousePressEvent(self, e):
        # 点击空白处取消选择
        if e.button() == Qt.LeftButton:
            self.module_selected.emit("")
        super().mousePressEvent(e)
