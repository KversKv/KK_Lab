# -*- coding: utf-8 -*-
"""拓扑画布: VSYS 主母线 + 子母线级联 + 模块卡片连线。"""

from PySide6.QtCore import Qt, Signal, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget

from ui.pages.pmu.pmu_1811.constants import (
    COL_CANVAS_BG, COL_AMBER, COL_AMBER_LINE, COL_BLUE, COL_BLUE_LINE, COL_PAIR_LINE,
    COL_SW_LINE, FONT_MONO,
    VSYS_X, CARD_X_L1, CARD_X_L2, CARD_X_L3, SW_BUS_X,
    CARD_W, CARD_H, ROW_H, TOP_PAD,
    SUB_BUS_X, BUS_PILL_W, BUS_PILL_H, BUS_PILL_X,
)
from ui.pages.pmu.pmu_1811.models import _LAYOUT_ROWS, get_pair_partner
from chips.bes1811_pmu import is_sw
from ui.pages.pmu.pmu_1811.widgets.module_card import ModuleCard


class DiagramCanvas(QWidget):
    module_selected = Signal(str)
    module_right_clicked = Signal(str, QPoint)
    voltage_stepped = Signal(str, float)
    enable_toggled = Signal(str)       # SW 卡片开关拨动

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

    def _build(self):
        for i, row in enumerate(_LAYOUT_ROWS):
            y_center = TOP_PAD + i * ROW_H + CARD_H // 2
            self._rows.append((row, y_center))
            if row.kind == "module":
                mod = self._modules[row.id]
                card = ModuleCard(mod, self)
                x = self._card_x(row)
                card.move(x, TOP_PAD + i * ROW_H)
                card.clicked.connect(self.module_selected.emit)
                card.right_clicked.connect(self.module_right_clicked.emit)
                card.gear_clicked.connect(self.module_right_clicked.emit)
                card.voltage_stepped.connect(self.voltage_stepped.emit)
                card.enable_toggled.connect(self.enable_toggled.emit)
                self._cards[row.id] = card

        n = len(_LAYOUT_ROWS)
        self.setFixedSize(
            CARD_X_L3 + CARD_W + 36,
            TOP_PAD * 2 + n * ROW_H,
        )

    @staticmethod
    def _card_x(row) -> int:
        """模块卡片 x 坐标。

        L1 模块 → CARD_X_L1; L2 模块 / VIN 源为 L1 对偶的 SW → CARD_X_L2;
        VIN 源为 L2 单模块的 SW (第三级) → CARD_X_L3。
        """
        if is_sw(row.id):
            # SW 级别 = VIN 源级别 + 1; 源为 L2 (单模块) → SW 是 L3
            if "&" not in row.input:
                return CARD_X_L3
            return CARD_X_L2
        return CARD_X_L1 if row.level == 1 else CARD_X_L2

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

    def _find_row(self, mod_id: str):
        """按模块 id 查找 (LayoutRow, y_center), 无则返回 (None, None)。"""
        for r, yc in self._rows:
            if r.kind == "module" and r.id == mod_id:
                return r, yc
        return None, None

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
        # SW 模块 input 非 "VSYS" (取自 LDO/BUCK 输出轨), 不画 VSYS 连线
        pen = QPen(QColor(COL_AMBER_LINE), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        for r, yc in self._rows:
            if r.level == 1 and r.input == "VSYS":
                p.drawLine(VSYS_X, yc, CARD_X_L1 if r.kind == "module" else BUS_PILL_X, yc)

        # 子母线（蓝色）：对每个 bus 与级联父节点，画竖线 + 子节点连线
        # 有 SW 子模块的对偶源 (如 BUCK_01/BUCK_03) 由 _draw_vin_tree 统一渲染,
        # 此处跳过避免重复绘制干线。
        pair_with_sw = self._pair_ids_with_sw()
        self._draw_subtree(p, "vdd_l14_15")
        self._draw_subtree(p, "vdd_l5")
        if "BUCK_01" not in pair_with_sw:
            self._draw_subtree(p, "BUCK_01")
        if "BUCK_03" not in pair_with_sw:
            self._draw_subtree(p, "BUCK_03")

        # 并联对偶输出短接线（紫色）
        self._draw_pairs(p)

        # 对偶源统一 VIN 树: L2 (蓝) + SW (玫红) 共享同一干线
        self._draw_vin_tree(p)

        # SW VIN 连线 (玫红): 仅处理单模块源 (如 LDO_13), 对偶源由 _draw_vin_tree 处理
        self._draw_sw_connections(p)

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

    def _pair_ids_with_sw(self) -> set:
        """返回有 SW 子模块的对偶源半 id 集合 (如 {"BUCK_01", "LDO_01"})。"""
        result = set()
        for r, _ in self._rows:
            if r.kind == "module" and is_sw(r.id) and "&" in r.input:
                for half in r.input.split("&"):
                    result.add(half)
        return result

    def _draw_vin_tree(self, p):
        """绘制对偶并联轨的统一 VIN 树: L2 (蓝) + SW (玫红) 共享同一干线。

        对每个有 SW 子模块的对偶源 (如 "LDO_01&BUCK_01"), 从对偶短接点
        引出一条干线 (SUB_BUS_X), 所有子模块 (L2 + SW) 从干线分支。
        干线为蓝色 (电源轨主色), 各分支段用模块类型颜色 (L2 蓝 / SW 玫红)。
        """
        # 收集有 SW 子模块的对偶源
        pair_vins = set()
        for r, _ in self._rows:
            if r.kind == "module" and is_sw(r.id) and "&" in r.input:
                pair_vins.add(r.input)
        if not pair_vins:
            return

        pen = QPen(QColor(COL_BLUE_LINE), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        for vin in pair_vins:
            ids = vin.split("&")
            # 对偶中点 (短接竖线中点)
            ycs = []
            for mid in ids:
                _, yc = self._find_row(mid)
                if yc is not None:
                    ycs.append(yc)
            if not ycs:
                continue
            src_x = CARD_X_L1 + CARD_W + 14   # 对偶短接竖线 x
            src_y = sum(ycs) // len(ycs)

            # 收集所有子模块: L2 (input ∈ ids) + SW (input == vin)
            children = []  # (yc, color_str)
            for r, yc in self._rows:
                if r.kind != "module":
                    continue
                if is_sw(r.id):
                    if r.input == vin:
                        children.append((yc, COL_SW_LINE))
                else:
                    if r.input in ids:
                        children.append((yc, COL_BLUE_LINE))
            if not children:
                continue
            children.sort()

            # 干线: pair 中点 → SUB_BUS_X (水平, 蓝)
            pen.setColor(QColor(COL_BLUE_LINE))
            p.setPen(pen)
            p.drawLine(src_x, src_y, SUB_BUS_X, src_y)
            # 竖线: src_y → 最远子模块 (蓝)
            last_yc = children[-1][0]
            if last_yc != src_y:
                p.drawLine(SUB_BUS_X, src_y, SUB_BUS_X, last_yc)
            # 各分支: SUB_BUS_X → 卡片左边, 用各自类型颜色
            for yc, color in children:
                pen.setColor(QColor(color))
                p.setPen(pen)
                p.drawLine(SUB_BUS_X, yc, CARD_X_L2, yc)

    def _draw_pairs(self, p):
        """绘制 BUCK↔LDO 并联对偶的输出短接线 (紫色)。

        两个对偶卡片同列 (CARD_X_L1), 输出端用 bracket 短接:
        各自从卡片右边引出一段短横线, 再用竖线连接, 表示两路并联到同一轨。
        两卡片各自从 VSYS 取电 (琥珀横线)。
        """
        drawn = set()
        pen = QPen(QColor(COL_PAIR_LINE), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        bx = CARD_X_L1 + CARD_W + 14   # 短接竖线 x (卡片右边留 14px 间距)
        for r, yc in self._rows:
            if r.kind != "module" or not r.pair:
                continue
            key = tuple(sorted((r.id, r.pair)))
            if key in drawn:
                continue
            drawn.add(key)
            _, partner_yc = self._find_row(r.pair)
            if partner_yc is None:
                continue
            # 两卡片右边各引短横线 → 竖线短接
            p.drawLine(CARD_X_L1 + CARD_W, yc, bx, yc)
            p.drawLine(bx, yc, bx, partner_yc)
            p.drawLine(bx, partner_yc, CARD_X_L1 + CARD_W, partner_yc)

    def _draw_sw_connections(self, p):
        """绘制 SW 的 VIN 连线 (玫红): 仅处理单模块源 (如 LDO_13)。

        对偶源 (input 含 "&") 由 _draw_vin_tree 统一渲染, 此处跳过。
        单 L2 模块输出: 从 L2 卡片右边 (CARD_X_L2+CARD_W) 引出
        → SW_BUS_X 竖线 → L3 SW 卡片左边 (CARD_X_L3)。
        """
        # 按 VIN 源分组, 共享竖线段
        groups: dict[str, list[tuple[str, int]]] = {}
        for r, yc in self._rows:
            if r.kind == "module" and is_sw(r.id):
                groups.setdefault(r.input, []).append((r.id, yc))

        pen = QPen(QColor(COL_SW_LINE), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        for vin, sw_list in groups.items():
            if "&" in vin:
                continue   # 对偶源由 _draw_vin_tree 处理
            sw_ys = [yc for _, yc in sw_list]
            # 单 L2 模块输出: 从 L2 卡片右边 → SW_BUS_X → L3 SW 卡片左边
            _, src_y = self._find_row(vin)
            if src_y is None:
                continue
            src_x = CARD_X_L2 + CARD_W        # L2 卡片右边
            # L2 右边 → SW_BUS_X (水平)
            p.drawLine(src_x, src_y, SW_BUS_X, src_y)
            # SW_BUS_X 竖线: src_y 到最远 SW 行
            y_top = min(src_y, min(sw_ys))
            y_bot = max(src_y, max(sw_ys))
            if y_bot > y_top:
                p.drawLine(SW_BUS_X, y_top, SW_BUS_X, y_bot)
            # 各 SW 行 → L3 卡片左边 (水平)
            for sw_yc in sw_ys:
                p.drawLine(SW_BUS_X, sw_yc, CARD_X_L3, sw_yc)

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
        start_yc = p_yc   # 子母线竖线起点 y (有对偶时取两卡片中点)

        pen = QPen(QColor(COL_BLUE_LINE), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        # 父节点 → 子母线竖线起点（短横）
        if parent_id in ("vdd_l14_15", "vdd_l5"):
            p.drawLine(BUS_PILL_X + BUS_PILL_W, p_yc, SUB_BUS_X, p_yc)
        else:
            # 级联：从父卡片右边引出; 若父有对偶, 从对偶短接竖线中点引出
            # (避免与对偶短接横线重叠在卡片右边)
            start_x = CARD_X_L1 + CARD_W
            partner_id = get_pair_partner(parent_id)
            if partner_id:
                _, partner_yc = self._find_row(partner_id)
                if partner_yc is not None:
                    start_x = CARD_X_L1 + CARD_W + 14
                    start_yc = (p_yc + partner_yc) // 2
            p.drawLine(start_x, start_yc, SUB_BUS_X, start_yc)

        # 子母线竖线
        p.drawLine(SUB_BUS_X, start_yc, SUB_BUS_X, last_yc)
        # 各子节点横线
        for _, r, yc in children:
            p.drawLine(SUB_BUS_X, yc, CARD_X_L2, yc)

    def mousePressEvent(self, e):
        # 点击空白处取消选择
        if e.button() == Qt.LeftButton:
            self.module_selected.emit("")
        super().mousePressEvent(e)
