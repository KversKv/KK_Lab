#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KK'1811 PMU 配置工具页面。

图形化配置 1811 PMIC：通过 USB 转 I2C（设备地址 0x17，10 位寄存器地址，16 位数据）
控制各 LDO / BUCK 的使能、模式与输出电压。

已接入真实 I2C 读写: 连接后 UI 操作经 QThread 异步下发到硬件。
"""

import os
import sys

if not getattr(sys, "frozen", False):
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal, QPoint, QRect, QThread
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QScrollArea, QSlider, QDoubleSpinBox, QButtonGroup,
    QGraphicsDropShadowEffect,
)
from log_config import get_logger

from chips.bes1811_pmu import (
    get_voltage_range, get_reg_map, is_ldo_controllable, LDO_REG_MAPS,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 配色（与 docs/NewPlan/1811_Tool_UI.md 一致，独立于全局 theme）
# ---------------------------------------------------------------------------
COL_CANVAS_BG = "#030712"
COL_PANEL_BG = "#0b1220"
COL_CARD_BG = "#111827"
COL_CARD_BG_SELECTED = "#0f2a22"
COL_BORDER = "#1f2937"
COL_BORDER_HOVER = "#374151"
COL_BORDER_SELECTED = "#10B981"
COL_EMERALD = "#10B981"
COL_EMERALD_SOFT = "#10B98133"
COL_AMBER = "#f59e0b"
COL_AMBER_LINE = "#f59e0b80"
COL_BLUE = "#3b82f6"
COL_BLUE_LINE = "#3b82f680"
COL_TEXT = "#e5e7eb"
COL_TEXT_MUTED = "#9ca3af"
COL_TEXT_DIM = "#6b7280"
COL_LED_OFF = "#4b5563"

FONT_MONO = '"JetBrains Mono", "Consolas", "Courier New", monospace'


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------
@dataclass
class PmuModule:
    id: str
    name: str
    type: str  # "LDO" / "BUCK"
    enabled: bool = True
    mode: str = "Normal"
    voltage: float = 1.8
    min_voltage: float = 0.5
    max_voltage: float = 3.3
    step: float = 0.05
    input: str = "VSYS"
    controllable: bool = True   # 是否支持 I2C 寄存器控制

    @property
    def modes(self):
        return ["Normal", "LP", "ULP"] if self.type == "BUCK" else ["Normal", "LP"]

    @property
    def reg_map(self):
        """返回芯片寄存器映射 (LdoRegMap 或 None)。"""
        return get_reg_map(self.id) if self.controllable else None


# 布局行：id / level(1=主轨,2=二级) / input / bus(虚拟母线名)
@dataclass
class LayoutRow:
    kind: str  # "module" / "bus"
    id: str    # 模块 id 或母线名
    level: int
    input: str
    bus_name: str = ""


_LAYOUT_ROWS = [
    LayoutRow("module", "BUCK_04", 1, "VSYS"),
    LayoutRow("module", "BUCK_05", 1, "VSYS"),
    LayoutRow("module", "BUCK_01", 1, "VSYS"),
    LayoutRow("module", "LDO_12", 2, "BUCK_01"),
    LayoutRow("module", "BUCK_02", 1, "VSYS"),
    LayoutRow("module", "BUCK_06", 1, "VSYS"),
    LayoutRow("module", "BUCK_03", 1, "VSYS"),
    LayoutRow("module", "LDO_01", 1, "VSYS"),
    LayoutRow("module", "LDO_02", 1, "VSYS"),
    LayoutRow("module", "LDO_06", 1, "VSYS"),
    LayoutRow("module", "LDO_07", 1, "VSYS"),
    LayoutRow("module", "LDO_08", 1, "VSYS"),
    LayoutRow("module", "LDO_09", 1, "VSYS"),
    LayoutRow("module", "LDO_10", 1, "VSYS"),
    LayoutRow("module", "LDO_11", 1, "VSYS"),
    LayoutRow("module", "LDO_03", 1, "VSYS"),
    LayoutRow("bus", "vdd_l14_15", 1, "VSYS", "vdd_l14_15"),
    LayoutRow("module", "LDO_VMIC1", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_VMIC2", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_14", 2, "vdd_l14_15"),
    LayoutRow("module", "LDO_15", 2, "vdd_l14_15"),
    LayoutRow("bus", "vdd_l5", 1, "VSYS", "vdd_l5"),
    LayoutRow("module", "LDO_13", 2, "vdd_l5"),
    LayoutRow("module", "LDO_05", 2, "vdd_l5"),
]


def _default_modules() -> dict:
    mods = {}
    buck_ids = {"BUCK_01", "BUCK_02", "BUCK_03", "BUCK_04", "BUCK_05", "BUCK_06"}
    for row in _LAYOUT_ROWS:
        if row.kind != "module":
            continue
        is_buck = row.id in buck_ids
        controllable = is_ldo_controllable(row.id)
        # 从芯片数据获取实际电压范围
        v_min, v_max = (None, None)
        if controllable:
            v_min, v_max = get_voltage_range(row.id)
        if v_min is None:
            v_min = 0.5
            v_max = 1.5 if is_buck else 3.3
        # 默认电压: BUCK 1.0V, LDO 取范围中点偏下
        if is_buck:
            default_v = 1.0
        elif controllable:
            default_v = v_min + (v_max - v_min) * 0.3
        else:
            default_v = 1.8
        mods[row.id] = PmuModule(
            id=row.id,
            name=row.id.replace("_", " "),
            type="BUCK" if is_buck else "LDO",
            enabled=True,
            mode="Normal",
            voltage=round(default_v, 4),
            min_voltage=v_min,
            max_voltage=v_max,
            step=0.01,
            input=row.input,
            controllable=controllable,
        )
    return mods


# ---------------------------------------------------------------------------
# 画布几何常量
# ---------------------------------------------------------------------------
VSYS_X = 48
CARD_X_L1 = 96
CARD_X_L2 = 452
SUB_BUS_X = 422
CARD_W = 256
CARD_H = 48
ROW_H = 62
TOP_PAD = 28
BUS_PILL_W = 112
BUS_PILL_H = 26
BUS_PILL_X = SUB_BUS_X - BUS_PILL_W // 2


# ---------------------------------------------------------------------------
# iOS 风格拨动开关
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 模块卡片
# ---------------------------------------------------------------------------
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
        self.volt_lbl.setText(f"{self._mod.voltage:.2f} V")
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


# ---------------------------------------------------------------------------
# 拓扑画布
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 属性面板
# ---------------------------------------------------------------------------
class PropertyPanel(QFrame):
    enable_changed = Signal(str, bool)
    mode_changed = Signal(str, str)
    voltage_changed = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("propertyPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(320)
        self.setStyleSheet(
            f"QFrame#propertyPanel {{ background:{COL_PANEL_BG};"
            f" border-left:1px solid {COL_BORDER}; }}"
            f"QLabel {{ background:transparent; border:none; color:{COL_TEXT_MUTED}; }}"
            f"QFrame#sectionCard {{ background:{COL_CARD_BG};"
            f" border:1px solid {COL_BORDER}; border-radius:10px; }}"
            f"QPushButton#modeBtn {{ background:{COL_BORDER}; color:{COL_TEXT_MUTED};"
            f" border:1px solid {COL_BORDER}; border-radius:6px; padding:6px 0;"
            f" font-size:12px; }}"
            f"QPushButton#modeBtn:checked {{ background:{COL_EMERALD_SOFT};"
            f" color:{COL_EMERALD}; border:1px solid {COL_EMERALD}; font-weight:700; }}"
            f"QPushButton#modeBtn:hover {{ border:1px solid {COL_BORDER_HOVER}; }}"
            f"QSlider::groove:horizontal {{ background:{COL_BORDER}; height:4px;"
            f" border-radius:2px; }}"
            f"QSlider::sub-page:horizontal {{ background:{COL_EMERALD};"
            f" border-radius:2px; }}"
            f"QSlider::handle:horizontal {{ background:{COL_EMERALD}; width:14px;"
            f" margin:-6px 0; border-radius:7px; }}"
        )

        self._mod: PmuModule | None = None
        self._syncing = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 头部
        self.title_lbl = QLabel("—")
        self.title_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-size:16px; font-weight:700;"
        )
        self.type_lbl = QLabel("Type: —")
        self.type_lbl.setStyleSheet(
            f"color:{COL_TEXT_MUTED}; font-family:{FONT_MONO}; font-size:11px;"
        )
        root.addWidget(self.title_lbl)
        root.addWidget(self.type_lbl)

        # Status
        root.addWidget(self._section_label("Status"))
        status_card = QFrame(self)
        status_card.setObjectName("sectionCard")
        sl = QHBoxLayout(status_card)
        sl.setContentsMargins(12, 8, 12, 8)
        sl.addWidget(self._muted_label("Output Enable"))
        sl.addStretch(1)
        self.toggle = ToggleSwitch(self)
        self.toggle.toggled.connect(self._on_toggle)
        sl.addWidget(self.toggle)
        root.addWidget(status_card)

        # Mode
        self.mode_label = self._section_label("Mode")
        root.addWidget(self.mode_label)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_row = QFrame(self)
        self.mode_layout = QHBoxLayout(self.mode_row)
        self.mode_layout.setContentsMargins(0, 0, 0, 0)
        self.mode_layout.setSpacing(6)
        root.addWidget(self.mode_row)

        # Voltage
        root.addWidget(self._section_label("Voltage (V)"))
        v_card = QFrame(self)
        v_card.setObjectName("sectionCard")
        vl = QVBoxLayout(v_card)
        vl.setContentsMargins(12, 10, 12, 12)
        vl.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(self._muted_label("Target (V)"))
        top.addStretch(1)
        self.spin = QDoubleSpinBox(self)
        self.spin.setDecimals(2)
        self.spin.setSingleStep(0.05)
        self.spin.setMinimumWidth(90)
        self.spin.setAlignment(Qt.AlignRight)
        self.spin.valueChanged.connect(self._on_spin)
        top.addWidget(self.spin)
        vl.addLayout(top)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setFocusPolicy(Qt.NoFocus)
        self.slider.valueChanged.connect(self._on_slider)
        vl.addWidget(self.slider)

        rng = QHBoxLayout()
        self.min_lbl = self._muted_label("—")
        self.max_lbl = self._muted_label("—")
        self.max_lbl.setAlignment(Qt.AlignRight)
        rng.addWidget(self.min_lbl)
        rng.addStretch(1)
        rng.addWidget(self.max_lbl)
        vl.addLayout(rng)
        root.addWidget(v_card)

        # I2C
        root.addWidget(self._section_label("I2C Registers"))
        i2c_card = QFrame(self)
        i2c_card.setObjectName("sectionCard")
        il = QVBoxLayout(i2c_card)
        il.setContentsMargins(12, 10, 12, 10)
        il.setSpacing(6)
        self.addr_lbl = QLabel("Address: —")
        self.addr_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px;"
        )
        self.value_lbl = QLabel("Value: —")
        self.value_lbl.setStyleSheet(
            f"color:{COL_EMERALD}; font-family:{FONT_MONO}; font-size:12px;"
        )
        il.addWidget(self.addr_lbl)
        il.addWidget(self.value_lbl)
        root.addWidget(i2c_card)

        # Connection
        root.addWidget(self._section_label("Connection Info"))
        self.conn_lbl = QLabel("Input Source: —")
        self.conn_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px;"
        )
        root.addWidget(self.conn_lbl)

        root.addStretch(1)

        for child in self.findChildren(QFrame):
            child.setAttribute(Qt.WA_StyledBackground, True)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{COL_TEXT_DIM}; font-size:11px; font-weight:700;"
            f" letter-spacing:0.5px; text-transform:uppercase;"
        )
        return lbl

    @staticmethod
    def _muted_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{COL_TEXT_MUTED}; font-size:12px;")
        return lbl

    def _rebuild_mode_buttons(self):
        for btn in list(self.mode_group.buttons()):
            self.mode_group.removeButton(btn)
            self.mode_layout.removeWidget(btn)
            btn.deleteLater()
        if self._mod is None:
            return
        for m in self._mod.modes:
            b = QPushButton(m, self)
            b.setObjectName("modeBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            if m == self._mod.mode:
                b.setChecked(True)
            b.clicked.connect(lambda _=False, mm=m: self._on_mode(mm))
            self.mode_group.addButton(b)
            self.mode_layout.addWidget(b)

    def load(self, mod: PmuModule):
        self._mod = mod
        self._syncing = True
        self.title_lbl.setText(mod.name)
        self.type_lbl.setText(f"Type: {mod.type}")
        self.toggle.set_checked(mod.enabled)
        self._rebuild_mode_buttons()

        self.spin.setRange(mod.min_voltage, mod.max_voltage)
        self.spin.setSingleStep(mod.step)
        self.spin.setValue(mod.voltage)

        smin = int(round(mod.min_voltage / mod.step))
        smax = int(round(mod.max_voltage / mod.step))
        sval = int(round(mod.voltage / mod.step))
        self.slider.setRange(smin, smax)
        self.slider.setValue(sval)

        self.min_lbl.setText(f"{mod.min_voltage:.2f} V")
        self.max_lbl.setText(f"{mod.max_voltage:.2f} V")
        self.conn_lbl.setText(f"Input Source: {mod.input}")
        self._syncing = False
        self._refresh_i2c()

    def _refresh_i2c(self):
        if self._mod is None:
            return
        rm = self._mod.reg_map
        if rm is not None:
            self.addr_lbl.setText(
                f"Ctrl: 0x{rm.pu.reg_addr:03X}  Vbit: 0x{rm.vbit_normal.reg_addr:03X}"
            )
            self.value_lbl.setText(
                f"pu={int(self._mod.enabled)}  mode={self._mod.mode}  "
                f"vbit_n=?  (需读取)"
            )
        else:
            self.addr_lbl.setText("Address: — (无寄存器映射)")
            self.value_lbl.setText("Value: —")

    def _on_toggle(self, checked: bool):
        if self._mod is None or self._syncing:
            return
        self._mod.enabled = checked
        self._refresh_i2c()
        self.enable_changed.emit(self._mod.id, checked)

    def _on_mode(self, mode: str):
        if self._mod is None or self._syncing:
            return
        if mode == self._mod.mode:
            return
        self._mod.mode = mode
        self._refresh_i2c()
        self.mode_changed.emit(self._mod.id, mode)

    def _on_spin(self, v: float):
        if self._mod is None or self._syncing:
            return
        self._syncing = True
        self.slider.setValue(int(round(v / self._mod.step)))
        self._syncing = False
        self._mod.voltage = v
        self._refresh_i2c()
        self.voltage_changed.emit(self._mod.id, v)

    def _on_slider(self, val: int):
        if self._mod is None or self._syncing:
            return
        v = val * self._mod.step
        self._syncing = True
        self.spin.setValue(v)
        self._syncing = False
        self._mod.voltage = v
        self._refresh_i2c()
        self.voltage_changed.emit(self._mod.id, v)


# ---------------------------------------------------------------------------
# 右键菜单
# ---------------------------------------------------------------------------
class ContextMenu(QFrame):
    enable_toggled = Signal(str)
    mode_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._mod: PmuModule | None = None
        self.setStyleSheet(
            f"QFrame {{ background:{COL_CARD_BG}; border:1px solid {COL_BORDER};"
            f" border-radius:8px; }}"
            f"QLabel#menuHeader {{ color:{COL_TEXT_MUTED}; font-size:11px;"
            f" padding:6px 12px; }}"
            f"QPushButton#menuBtn {{ background:transparent; color:{COL_TEXT};"
            f" border:none; padding:8px 12px; text-align:left; font-size:12px; }}"
            f"QPushButton#menuBtn:hover {{ background:{COL_BORDER}; }}"
            f"QPushButton#menuBtn:checked {{ color:{COL_EMERALD}; font-weight:700; }}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.header = QLabel("—", self)
        self.header.setObjectName("menuHeader")
        self._layout.addWidget(self.header)
        self.toggle_btn = QPushButton("Enable Output", self)
        self.toggle_btn.setObjectName("menuBtn")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._on_toggle)
        self._layout.addWidget(self.toggle_btn)
        self._sep = QFrame(self)
        self._sep.setFixedHeight(1)
        self._sep.setStyleSheet(f"background:{COL_BORDER}; border:none;")
        self._layout.addWidget(self._sep)
        self._mode_btns = []

    def popup(self, mod: PmuModule, pos: QPoint):
        self._mod = mod
        self.header.setText(mod.name)
        self.toggle_btn.setText("Disable Output" if mod.enabled else "Enable Output")
        for b in self._mode_btns:
            self._layout.removeWidget(b)
            b.deleteLater()
        self._mode_btns.clear()
        for m in mod.modes:
            b = QPushButton(m, self)
            b.setObjectName("menuBtn")
            b.setCheckable(True)
            b.setChecked(m == mod.mode)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, mm=m: self._on_mode(mm))
            self._layout.addWidget(b)
            self._mode_btns.append(b)
        self.adjustSize()
        self.move(pos)
        self.show()

    def _on_toggle(self):
        if self._mod is not None:
            self.enable_toggled.emit(self._mod.id)
        self.close()

    def _on_mode(self, mode: str):
        if self._mod is not None:
            self.mode_changed.emit(self._mod.id, mode)
        self.close()


# ---------------------------------------------------------------------------
# 主页面
# ---------------------------------------------------------------------------
class Pmu1811UI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("pmu1811Page")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#pmu1811Page {{ background:{COL_CANVAS_BG}; }}"
            f"QLabel {{ background:transparent; border:none; color:{COL_TEXT}; }}"
            f"QScrollBar:vertical {{ background:{COL_CANVAS_BG}; width:10px; margin:0; }}"
            f"QScrollBar::handle:vertical {{ background:{COL_BORDER};"
            f" min-height:30px; border-radius:4px; }}"
            f"QScrollBar::handle:vertical:hover {{ background:{COL_BORDER_HOVER}; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}"
            f"QScrollBar:horizontal {{ background:{COL_CANVAS_BG}; height:10px; margin:0; }}"
            f"QScrollBar::handle:horizontal {{ background:{COL_BORDER};"
            f" min-width:30px; border-radius:4px; }}"
            f"QScrollBar::handle:horizontal:hover {{ background:{COL_BORDER_HOVER}; }}"
            f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}"
            f"QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background:transparent; }}"
            f"QDoubleSpinBox, QSpinBox {{ background:{COL_CARD_BG};"
            f" border:1px solid {COL_BORDER_HOVER}; border-radius:6px;"
            f" padding:4px 8px; color:{COL_TEXT};"
            f" selection-background-color:{COL_EMERALD}; selection-color:#06281d; }}"
            f"QDoubleSpinBox:focus, QSpinBox:focus {{ border:1px solid {COL_EMERALD}; }}"
            f"QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,"
            f" QSpinBox::up-button, QSpinBox::down-button {{ width:0; height:0; border:none; }}"
            f"QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow,"
            f" QSpinBox::up-arrow, QSpinBox::down-arrow {{ width:0; height:0; }}"
        )

        self._modules = _default_modules()
        self._selected_id: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.canvas = DiagramCanvas(self._modules, self)
        self.scroll = QScrollArea(self)
        self.scroll.setWidget(self.canvas)
        self.scroll.setWidgetResizable(False)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(
            f"QScrollArea {{ background:{COL_CANVAS_BG}; border:none; }}"
            f"QScrollArea > QWidget > QWidget {{ background:{COL_CANVAS_BG}; }}"
        )
        body.addWidget(self.scroll, 1)

        self.panel = PropertyPanel(self)
        self.panel.setVisible(False)
        body.addWidget(self.panel)

        root.addLayout(body, 1)

        self.menu = ContextMenu(self)

        # I2C 连接状态与 Worker 线程
        self._i2c_connected = False
        self._dll_path = None       # None → 使用默认 DLL
        self._speed_mode = None     # None → 默认 100K
        self._worker_thread = None
        self._worker = None

        # 信号连接
        self.canvas.module_selected.connect(self._on_select)
        self.canvas.module_right_clicked.connect(self._on_context)
        self.canvas.voltage_stepped.connect(self._on_card_voltage)
        self.panel.enable_changed.connect(self._on_panel_enable)
        self.panel.mode_changed.connect(self._on_panel_mode)
        self.panel.voltage_changed.connect(self._on_panel_voltage)
        self.menu.enable_toggled.connect(self._on_menu_enable)
        self.menu.mode_changed.connect(self._on_menu_mode)

    # ---- 头部 ----
    def _build_header(self) -> QFrame:
        header = QFrame(self)
        header.setFixedHeight(56)
        header.setStyleSheet(
            f"QFrame {{ background:{COL_PANEL_BG}; border-bottom:1px solid {COL_BORDER}; }}"
        )
        h = QHBoxLayout(header)
        h.setContentsMargins(20, 0, 20, 0)
        h.setSpacing(12)

        icon_lbl = QLabel("▣", header)
        icon_lbl.setStyleSheet(f"color:{COL_EMERALD}; font-size:18px;")
        title = QLabel("KK'1811 PMU Configuration Tool", header)
        title.setStyleSheet(f"color:{COL_TEXT}; font-size:15px; font-weight:700;")
        h.addWidget(icon_lbl)
        h.addWidget(title)
        h.addStretch(1)

        info = QLabel("DUT: 1811  |  I2C: 0x17", header)
        info.setStyleSheet(f"color:{COL_TEXT_MUTED}; font-family:{FONT_MONO}; font-size:12px;")
        h.addWidget(info)

        self.check_btn = QPushButton("Check", header)
        self.check_btn.setObjectName("checkBtn")
        self.check_btn.setCursor(Qt.PointingHandCursor)
        self.check_btn.setStyleSheet(
            f"QPushButton#checkBtn {{ background:{COL_EMERALD_SOFT}; color:{COL_EMERALD};"
            f" border:1px solid {COL_EMERALD}; border-radius:6px;"
            f" padding:6px 16px; font-weight:700; font-size:12px; }}"
            f"QPushButton#checkBtn:hover {{ background:{COL_EMERALD}; color:#06281d; }}"
        )
        self.check_btn.clicked.connect(self._on_check)
        h.addWidget(self.check_btn)
        return header

    def _on_check(self):
        """Check 按钮: 读取所有 LDO 状态并刷新 UI。"""
        if self._worker_thread is not None:
            logger.warning("1811 PMU: 上一次操作尚未完成")
            return
        self.check_btn.setEnabled(False)
        self.check_btn.setText("Reading...")
        from ui.pages.pmu.pmu_1811_workers import LdoReadAllWorker
        self._worker = LdoReadAllWorker(
            dll_path=self._dll_path, speed_mode=self._speed_mode)
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker.finished.connect(self._on_read_all_done)
        self._worker.error.connect(self._on_i2c_error)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()

    def _on_read_all_done(self, states: dict):
        """读取全部 LDO 完成, 刷新 UI。"""
        self._cleanup_worker()
        self._i2c_connected = True
        for ldo_id, st in states.items():
            mod = self._modules.get(ldo_id)
            if mod is None:
                continue
            mod.enabled = st.enabled
            mod.mode = st.mode if st.mode in ("Normal", "LP") else "Normal"
            if st.voltage is not None:
                mod.voltage = st.voltage
            self.canvas.refresh_card(ldo_id)
        if self._selected_id and self._selected_id in self._modules:
            self.panel.load(self._modules[self._selected_id])
        logger.info("1811 PMU: 读取完成, %d 个 LDO", len(states))

    def _on_i2c_error(self, msg: str):
        """I2C 操作出错。"""
        self._cleanup_worker()
        self._i2c_connected = False
        logger.error("1811 PMU I2C 错误: %s", msg)

    def _cleanup_worker(self):
        """清理 Worker 线程。"""
        if self._worker_thread is not None:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
            self._worker = None
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Check")

    # ---- 异步写入 ----
    def _start_write(self, ldo_id: str, action: str, value):
        """启动异步写入 (若已连接)。"""
        if not self._modules[ldo_id].controllable:
            return
        if not self._i2c_connected:
            logger.debug("1811 PMU: 未连接, 仅本地更新 %s", ldo_id)
            return
        if self._worker_thread is not None:
            logger.warning("1811 PMU:忙碌, 丢弃 %s/%s", ldo_id, action)
            return
        from ui.pages.pmu.pmu_1811_workers import LdoWriteWorker
        self._worker = LdoWriteWorker(
            ldo_id, action, value,
            dll_path=self._dll_path, speed_mode=self._speed_mode,
        )
        self._worker_thread = QThread()
        self._worker.moveToThread(self._worker_thread)
        self._worker.finished.connect(self._on_write_done)
        self._worker.error.connect(self._on_i2c_error)
        self._worker_thread.started.connect(self._worker.run)
        self._worker_thread.start()

    def _on_write_done(self, ldo_id: str):
        """单次写入完成。"""
        self._cleanup_worker()

    # ---- 选择 ----
    def _on_select(self, mod_id: str):
        if not mod_id:
            self._selected_id = None
            self.canvas.clear_selection()
            self.panel.setVisible(False)
            return
        self._selected_id = mod_id
        self.canvas.set_selected(mod_id)
        self.panel.load(self._modules[mod_id])
        self.panel.setVisible(True)

    def _on_context(self, mod_id: str, pos: QPoint):
        self.menu.popup(self._modules[mod_id], pos)

    # ---- 状态联动 ----
    def _on_card_voltage(self, mod_id: str, _v: float):
        if mod_id == self._selected_id:
            self.panel.load(self._modules[mod_id])

    def _on_panel_enable(self, mod_id: str, enabled: bool):
        self.canvas.refresh_card(mod_id)
        if mod_id == self._selected_id:
            self.panel._refresh_i2c()
        self._start_write(mod_id, "enable", enabled)

    def _on_panel_mode(self, mod_id: str, mode: str):
        self.canvas.refresh_card(mod_id)
        self._start_write(mod_id, "mode", mode)

    def _on_panel_voltage(self, mod_id: str, v: float):
        self.canvas.refresh_card(mod_id)
        self._start_write(mod_id, "voltage", v)

    def _on_menu_enable(self, mod_id: str):
        mod = self._modules[mod_id]
        mod.enabled = not mod.enabled
        self.canvas.refresh_card(mod_id)
        if mod_id == self._selected_id:
            self.panel.load(mod)
        self._start_write(mod_id, "enable", mod.enabled)

    def _on_menu_mode(self, mod_id: str, mode: str):
        mod = self._modules[mod_id]
        mod.mode = mode
        self.canvas.refresh_card(mod_id)
        if mod_id == self._selected_id:
            self.panel.load(mod)
        self._start_write(mod_id, "mode", mode)


if __name__ == "__main__":
    """独立预览 1811 PMU 配置工具界面。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = Pmu1811UI()
    window.setWindowTitle("KK'1811 PMU Configuration Tool")
    window.resize(1080, 720)
    window.show()
    sys.exit(app.exec())

