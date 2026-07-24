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
from ui.pages.pmu.pmu_1811.widgets.switch_widget import SwitchWidget


class DiagramCanvas(QWidget):
    module_selected = Signal(str)
    module_right_clicked = Signal(str, QPoint)
    voltage_stepped = Signal(str, float)
    enable_toggled = Signal(str)       # SW 开关模型单击切换

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
        max_x = 0
        for i, row in enumerate(_LAYOUT_ROWS):
            y_center = TOP_PAD + i * ROW_H + CARD_H // 2
            self._rows.append((row, y_center))
            if row.kind == "module":
                mod = self._modules[row.id]
                x = self._card_x(row)
                max_x = max(max_x, x + CARD_W)
                if is_sw(row.id):
                    # SW: 物理开关模型 (无端电压步进/齿轮, 单击切换闭合/开路)
                    card = SwitchWidget(mod, self)
                    card.move(x, TOP_PAD + i * ROW_H)
                    card.clicked.connect(self.module_selected.emit)
                    card.right_clicked.connect(self.module_right_clicked.emit)
                    card.enable_toggled.connect(self.enable_toggled.emit)
                else:
                    card = ModuleCard(mod, self)
                    card.move(x, TOP_PAD + i * ROW_H)
                    card.clicked.connect(self.module_selected.emit)
                    card.right_clicked.connect(self.module_right_clicked.emit)
                    card.gear_clicked.connect(self.module_right_clicked.emit)
                    card.voltage_stepped.connect(self.voltage_stepped.emit)
                self._cards[row.id] = card

        n = len(_LAYOUT_ROWS)
        self.setFixedSize(
            max_x + 36,
            TOP_PAD * 2 + n * ROW_H,
        )

    def _card_x(self, row) -> int:
        """模块卡片 x 坐标。

        L1 模块 → CARD_X_L1; L2 模块 / VIN 源为 L1 的 SW → CARD_X_L2;
        VIN 源为 L2 单模块的 SW (第三级) → CARD_X_L3。
        """
        if is_sw(row.id):
            # SW 级别 = VIN 源级别 + 1
            if "&" in row.input:
                return CARD_X_L2       # 对偶源 (L1) → SW 是 L2
            src_row, _ = self._find_row(row.input)
            if src_row is not None and src_row.level == 1:
                return CARD_X_L2       # 单模块源 L1 → SW 是 L2
            return CARD_X_L3           # 单模块源 L2 → SW 是 L3
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

        # vin_sw5_6 标签: SW5/SW6 共享输入总节点 (L1 单模块源 LDO_13 → SUB_BUS_X 干线)
        # 样式与 vdd_l5 母线药丸一致, 标记 SW 输入母线节点
        sw5_row, _ = self._find_row("SW5")
        if sw5_row is not None:
            src_mod, src_y = self._find_row(sw5_row.input)
            if src_mod is not None and src_y is not None:
                trunk_x = SUB_BUS_X if src_mod.level == 1 else SW_BUS_X
                rect = QRect(trunk_x - BUS_PILL_W // 2, src_y - BUS_PILL_H // 2,
                             BUS_PILL_W, BUS_PILL_H)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor("#1f2937"))
                p.drawRoundedRect(rect, 8, 8)
                p.setPen(QColor(COL_BLUE))
                p.drawText(rect, Qt.AlignCenter, "vin_sw5_6")

    def _pair_ids_with_sw(self) -> set:
        """返回有 SW 子模块的对偶源半 id 集合 (如 {"BUCK_01", "LDO_01"})。"""
        result = set()
        for r, _ in self._rows:
            if r.kind == "module" and is_sw(r.id) and "&" in r.input:
                for half in r.input.split("&"):
                    result.add(half)
        return result

    def _draw_wire_tree(self, p, src_x, src_y, bus_x, children, trunk_color):
        """通用树状连线: 源点 → bus_x 水平干线 → 竖直干线 → 各分支水平到目标列。

        children: [(yc, target_x, color), ...]。竖直干线覆盖 src_y 与所有分支
        的 min/max 范围, 保证每个分支都挂在干线上 (无悬空端点); 分支终点即
        子模块控件左缘 (卡片边 / 开关模型输入引线起点), 连线无缝衔接。
        """
        if not children:
            return
        children = sorted(children, key=lambda c: c[0])
        pen = QPen(QColor(trunk_color), 2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        if src_x != bus_x:
            p.drawLine(src_x, src_y, bus_x, src_y)
        y_top = min(src_y, children[0][0])
        y_bot = max(src_y, children[-1][0])
        if y_bot > y_top:
            p.drawLine(bus_x, y_top, bus_x, y_bot)
        for yc, tx, color in children:
            pen.setColor(QColor(color))
            p.setPen(pen)
            p.drawLine(bus_x, yc, tx, yc)

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
            children = []  # (yc, target_x, color_str)
            for r, yc in self._rows:
                if r.kind != "module":
                    continue
                if is_sw(r.id):
                    if r.input == vin:
                        children.append((yc, CARD_X_L2, COL_SW_LINE))
                else:
                    if r.input in ids:
                        children.append((yc, CARD_X_L2, COL_BLUE_LINE))
            self._draw_wire_tree(p, src_x, src_y, SUB_BUS_X, children, COL_BLUE_LINE)

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
        单模块源: 从源卡片右边引出 (L1→CARD_X_L1+CARD_W / L2→CARD_X_L2+CARD_W)
        → 干线 (L1 源→SUB_BUS_X / L2 源→SW_BUS_X) → SW 开关模型左缘
        (L1 源→CARD_X_L2 / L2 源→CARD_X_L3)。
        """
        # 按 VIN 源分组, 共享同一干线 (树状分支)
        groups: dict[str, list[tuple[int, int, str]]] = {}
        for r, yc in self._rows:
            if r.kind == "module" and is_sw(r.id) and "&" not in r.input:
                src_row, _ = self._find_row(r.input)
                if src_row is not None and src_row.level == 1:
                    target_x = CARD_X_L2       # 源 L1 → SW L2
                else:
                    target_x = CARD_X_L3       # 源 L2 → SW L3
                groups.setdefault(r.input, []).append((yc, target_x, COL_SW_LINE))

        for vin, children in groups.items():
            src_row, src_y = self._find_row(vin)
            if src_y is None:
                continue
            src_x = (CARD_X_L1 if src_row.level == 1 else CARD_X_L2) + CARD_W
            trunk_x = SUB_BUS_X if src_row.level == 1 else SW_BUS_X
            self._draw_wire_tree(p, src_x, src_y,
                                 trunk_x, children, COL_SW_LINE)

    def _draw_subtree(self, p, parent_id: str):
        parent_idx = self._row_index(lambda r: (r.kind == "bus" and r.bus_name == parent_id) or
                                    (r.kind == "module" and r.id == parent_id))
        if parent_idx < 0:
            return
        children = [(yc, CARD_X_L2, COL_BLUE_LINE)
                    for r, yc in self._rows
                    if r.kind == "module" and r.input == parent_id]
        if not children:
            return
        _, p_yc = self._rows[parent_idx]

        # 干线起点: 母线药丸右边 / 父卡片右边; 若父有对偶, 从对偶短接竖线
        # 中点引出 (避免与对偶短接横线重叠在卡片右边)
        if parent_id in ("vdd_l14_15", "vdd_l5"):
            src_x, src_y = BUS_PILL_X + BUS_PILL_W, p_yc
        else:
            src_x, src_y = CARD_X_L1 + CARD_W, p_yc
            partner_id = get_pair_partner(parent_id)
            if partner_id:
                _, partner_yc = self._find_row(partner_id)
                if partner_yc is not None:
                    src_x = CARD_X_L1 + CARD_W + 14
                    src_y = (p_yc + partner_yc) // 2
        self._draw_wire_tree(p, src_x, src_y, SUB_BUS_X, children, COL_BLUE_LINE)

    def mousePressEvent(self, e):
        # 点击空白处取消选择
        if e.button() == Qt.LeftButton:
            self.module_selected.emit("")
        super().mousePressEvent(e)
