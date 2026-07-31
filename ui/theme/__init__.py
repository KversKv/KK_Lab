"""ui.theme — 应用级设计 token 与主题运行时（包入口）.

新代码请使用：
- ``ui.theme.tokens``：语义 token（Tokens/StateSet/dark_tokens/light_tokens）
- ``ui.theme.theme``：Theme/apply/dp/refresh_style/load_qss/apply_qss
- ``ui.theme.theme.apply_qss``：全 ui/ 唯一 setStyleSheet 白名单点

兼容层（deprecated）：``Colors / FontSizes / Spacing / Radius / FONT_FAMILY /
FONT_MONO / CHANNEL_COLORS / CHANNEL_THEMES`` 经模块 ``__getattr__`` 转发到
``ui.theme.legacy``，首次访问发 DeprecationWarning，值与原单文件 1:1 一致。
"""
from __future__ import annotations

import warnings as _warnings

from ui.theme import legacy as _legacy
from ui.theme.theme import (
    Theme, apply, apply_qss, configure_high_dpi, current_theme, dp,
    load_qss, refresh_style, set_theme, token_map,
)
from ui.theme.tokens import (
    FontScale, StateSet, Tokens, dark_tokens, light_tokens,
)

_DEPRECATED = {
    "Colors": _legacy.Colors,
    "FontSizes": _legacy.FontSizes,
    "Spacing": _legacy.Spacing,
    "Radius": _legacy.Radius,
    "FONT_FAMILY": _legacy.FONT_FAMILY,
    "FONT_MONO": _legacy.FONT_MONO,
    "CHANNEL_COLORS": _legacy.CHANNEL_COLORS,
    "CHANNEL_THEMES": _legacy.CHANNEL_THEMES,
}


def __getattr__(name: str):
    if name in _DEPRECATED:
        _warnings.warn(
            f"ui.theme.{name} 已废弃，请迁移到 ui.theme.tokens / ui.theme.theme",
            DeprecationWarning,
            stacklevel=2,
        )
        return _DEPRECATED[name]
    raise AttributeError(f"module 'ui.theme' has no attribute {name!r}")


def __dir__():
    return sorted(__all__)


__all__ = [
    # 新 API
    "Theme", "Tokens", "StateSet", "FontScale",
    "dark_tokens", "light_tokens",
    "apply", "apply_qss", "configure_high_dpi", "current_theme", "dp",
    "load_qss", "refresh_style", "set_theme", "token_map",
    # 兼容层（deprecated）
    "Colors", "FontSizes", "Spacing", "Radius",
    "FONT_FAMILY", "FONT_MONO", "CHANNEL_COLORS", "CHANNEL_THEMES",
]
