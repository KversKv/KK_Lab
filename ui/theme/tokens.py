"""语义化设计 token（UI 样式单一数据源）.

设计原则：
- 只暴露**语义**（surface/text/border/accent/state），不暴露裸色值；
  组件与 QSS 一律经 token 取值，禁止再写 ``#RRGGBB``。
- dark 主题色值 1:1 沿用 legacy 调色板（本次迁移零视觉变化）；
  light 主题为新增能力，文本色一律按 ≥ 4.5:1 对比度取保守深色。
- 状态色（success/warning/error/info/running/skipped）统一 ``fg/bg/border``
  三件套，bg/border 由 fg 加透明度派生，保证同族一致。

尺寸 token（间距/圆角/控件高/行高）一律为**逻辑像素 int**，
注入 QSS 前由 ``ui.theme.theme.token_map()`` 经 ``dp()`` 换算并补 ``px`` 单位。
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _rgba(hex_color: str, alpha: float) -> str:
    """``#RRGGBB`` + 透明度(0~1) → QSS 可用的 ``rgba(r, g, b, a)``。"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    a = max(0, min(255, round(alpha * 255)))
    return f"rgba({r}, {g}, {b}, {a})"


@dataclass(frozen=True)
class StateSet:
    """状态色三件套：前景 / 浅底 / 描边（徽章、Banner、行内校验共用）。"""

    fg: str
    bg: str
    border: str


def _state(fg: str, bg_alpha: float = 0.12, border_alpha: float = 0.45) -> StateSet:
    return StateSet(fg=fg, bg=_rgba(fg, bg_alpha), border=_rgba(fg, border_alpha))


@dataclass(frozen=True)
class FontScale:
    """字号阶梯（单位 pt；pt→px 由 dp() 在注入 QSS 时换算）。"""

    caption: int = 11
    body: int = 12
    subtitle: int = 13
    title: int = 15
    display: int = 20


@dataclass(frozen=True)
class Tokens:
    """一套主题的完整 token 集合（dark / light 各一份实例）。"""

    name: str

    # —— 表面层级：页面底 / 卡片 / 浮起面板 / 输入框 ——
    surface_page: str
    surface_card: str
    surface_raised: str
    surface_input: str

    # —— 文本层级 ——
    text_primary: str
    text_secondary: str
    text_muted: str
    text_disabled: str
    text_on_accent: str

    # —— 描边层级：分隔线 / 默认边框 / 强边框(hover) / 焦点环 ——
    border_subtle: str
    border_default: str
    border_strong: str
    border_focus: str

    # —— 主强调色 ——
    accent_default: str
    accent_hover: str
    accent_pressed: str

    # —— 状态色三件套 ——
    state_success: StateSet
    state_warning: StateSet
    state_error: StateSet
    state_info: StateSet
    state_running: StateSet
    state_skipped: StateSet

    # —— 字体族（回退链）与字号阶梯 ——
    font_ui: str = '"Inter", "Segoe UI", "Microsoft YaHei UI", sans-serif'
    font_mono: str = '"JetBrains Mono", "Consolas", monospace'
    font_scale: FontScale = field(default_factory=FontScale)

    # —— 间距（4px 基准）/ 圆角 / 控件高度（均为逻辑像素 int）——
    space: tuple = (4, 8, 12, 16, 24, 32)
    radius_sm: int = 4
    radius_md: int = 6
    radius_lg: int = 8
    control_h_compact: int = 28
    control_h: int = 32
    table_row_h: int = 26
    icon_size: int = 16


def dark_tokens() -> Tokens:
    """暗色主题（默认）：色值与 legacy ``Colors`` 一一对应，零视觉变化。"""
    return Tokens(
        name="dark",
        surface_page="#050b1a",
        surface_card="#0b1630",
        surface_raised="#08132d",
        surface_input="#091426",
        text_primary="#f8fbff",
        text_secondary="#dbe7ff",
        text_muted="#8ea6cf",
        text_disabled="#4a5a7a",
        text_on_accent="#ffffff",
        border_subtle="#1f3262",
        border_default="#243a6e",
        border_strong="#2f4380",
        border_focus="#5b3df5",
        accent_default="#5b3df5",
        accent_hover="#6548ff",
        accent_pressed="#4a2fd4",
        state_success=_state("#15d1a3"),
        state_warning=_state("#ffb84d"),
        state_error=_state("#ff5e7a"),
        state_info=_state("#5b9cf5"),
        state_running=_state("#5b9cf5"),
        state_skipped=_state("#8ea6cf", bg_alpha=0.10, border_alpha=0.35),
    )


def light_tokens() -> Tokens:
    """浅色主题：文本/状态前景色均按白底 ≥ 4.5:1 对比度选取。"""
    return Tokens(
        name="light",
        surface_page="#eef1f6",
        surface_card="#ffffff",
        surface_raised="#f6f8fb",
        surface_input="#ffffff",
        text_primary="#17203a",
        text_secondary="#2c3852",
        text_muted="#56617a",
        text_disabled="#8b93a7",
        text_on_accent="#ffffff",
        border_subtle="#d9dee8",
        border_default="#c6cdda",
        border_strong="#a9b2c6",
        border_focus="#4a5fd9",
        accent_default="#4a5fd9",
        accent_hover="#3b4ec4",
        accent_pressed="#3244ae",
        state_success=_state("#0a6b4f", bg_alpha=0.10, border_alpha=0.40),
        state_warning=_state("#7a5200", bg_alpha=0.10, border_alpha=0.40),
        state_error=_state("#b3173a", bg_alpha=0.10, border_alpha=0.40),
        state_info=_state("#1a5fd0", bg_alpha=0.10, border_alpha=0.40),
        state_running=_state("#1a5fd0", bg_alpha=0.10, border_alpha=0.40),
        state_skipped=_state("#56617a", bg_alpha=0.08, border_alpha=0.30),
    )
