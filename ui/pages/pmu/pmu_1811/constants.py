# -*- coding: utf-8 -*-
"""1811 PMU 配色 / 字体 / 画布几何常量。

独立于全局 theme，与 docs/NewPlan/1811_Tool_UI.md 一致。
"""

# ---------------------------------------------------------------------------
# 配色
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
COL_PAIR = "#a855f7"        # 并联对偶 (BUCK↔LDO 输出短接) 连线
COL_PAIR_LINE = "#a855f780"
COL_TEXT = "#e5e7eb"
COL_TEXT_MUTED = "#9ca3af"
COL_TEXT_DIM = "#6b7280"
COL_LED_OFF = "#4b5563"

FONT_MONO = '"JetBrains Mono", "Consolas", "Courier New", monospace'


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
