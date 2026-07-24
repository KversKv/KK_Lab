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
COL_SW_LINE = "#ec489980"    # SW VIN 连线 (玫红半透明, 与 SW 主题色一致)

# 模块类型主题色: BUCK 琥珀 (与 VSYS 同色系, 直连取电); LDO 天蓝 (区别于子母线蓝)
COL_BUCK = "#f59e0b"
COL_BUCK_SOFT = "#f59e0b33"
COL_BUCK_DIM = "#f59e0b59"   # disabled 时降饱和
COL_LDO = "#38bdf8"
COL_LDO_SOFT = "#38bdf833"
COL_LDO_DIM = "#38bdf859"
# SW (Power Switch) 玫红: 区别于 BUCK 琥珀 / LDO 天蓝 / 并联对偶紫
COL_SW = "#ec4899"
COL_SW_SOFT = "#ec489933"
COL_SW_DIM = "#ec489959"

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
CARD_X_L3 = 760             # L3 列 (第三级 SW, VIN 源为 L2 模块)
SW_BUS_X = 730              # SW VIN 右侧竖线 x (L2 源 → L3 SW)
SUB_BUS_X = 422
CARD_W = 256
CARD_H = 48
ROW_H = 62
TOP_PAD = 28
BUS_PILL_W = 112
BUS_PILL_H = 26
BUS_PILL_X = SUB_BUS_X - BUS_PILL_W // 2
