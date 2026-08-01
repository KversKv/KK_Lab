"""主题运行时：主题获取 / 应用 / 尺寸换算 / QSS 加载与注入.

职责边界：
- ``Theme.dark() / Theme.light()`` 返回 ``Tokens`` 实例；``current_theme()``
  返回当前生效主题（默认 dark）。
- ``apply(app, theme)`` 在启动时统一注入全局字体与基础 QSS。
- ``load_qss(name)`` 读取 ``qss/<name>.qss`` 并用 ``string.Template`` 注入
  token（``$surface_card`` 形式）；``apply_qss(widget, name)`` 是**全 ui/ 唯一
  允许调用 ``setStyleSheet`` 的白名单点**（验收 grep 以此为豁免）。
- 所有尺寸经 ``dp(n)`` 按屏幕逻辑 DPI 换算，控件代码禁止裸像素常量。
"""
from __future__ import annotations

from pathlib import Path
from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QApplication

from ui.theme.tokens import Tokens, dark_tokens, light_tokens

_QSS_DIR = Path(__file__).resolve().parent / "qss"

_current: Tokens = dark_tokens()


class Theme:
    """主题工厂（语义入口，避免页面直接调 tokens 模块函数）。"""

    @staticmethod
    def dark() -> Tokens:
        return dark_tokens()

    @staticmethod
    def light() -> Tokens:
        return light_tokens()


def current_theme() -> Tokens:
    """当前生效主题（未调用 apply 前为 dark）。"""
    return _current


def set_theme(theme: Tokens) -> None:
    """仅切换当前主题记录，不触碰已创建控件（配合 refresh_style 逐个刷新）。"""
    global _current
    _current = theme


# ------------------------------------------------------------------ 尺寸换算
def dp(n: float) -> int:
    """逻辑像素 → 物理像素（按主屏逻辑 DPI 缩放，失败时返回原值取整）。"""
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return int(round(n))
    factor = screen.logicalDotsPerInch() / 96.0
    return int(round(n * factor))


def configure_high_dpi() -> None:
    """在 QApplication 创建前调用：高 DPI 取整策略 PassThrough（Qt6 默认值，显式声明）。

    必须在 ``QApplication`` 实例化之前调用才生效。
    """
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def refresh_style(widget) -> None:
    """动态属性（如 ``[state="error"]``）变更后强制重匹配 QSS 选择器。"""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


# ------------------------------------------------------------------ QSS 加载
def token_map(theme: Tokens | None = None) -> dict[str, str]:
    """把 Tokens 展平为 ``string.Template`` 替换映射（尺寸经 dp() 并补 px）。

    键命名约定：``$surface_card`` / ``$state_error_fg`` / ``$font_body`` /
    ``$space_2`` / ``$radius_sm`` / ``$control_h`` …
    控件高度额外给出 ``*_box`` 变体（已扣除 2×1px border 的 content 高，
    配合 ``padding:0`` 实现总高钉死，见 AGENTS.md 硬红线 §8 盒模型）。
    """
    t = theme or _current
    fs = t.font_scale
    space = t.space
    m: dict[str, str] = {
        "surface_page": t.surface_page,
        "surface_card": t.surface_card,
        "surface_raised": t.surface_raised,
        "surface_input": t.surface_input,
        "text_primary": t.text_primary,
        "text_secondary": t.text_secondary,
        "text_muted": t.text_muted,
        "text_disabled": t.text_disabled,
        "text_on_accent": t.text_on_accent,
        "border_subtle": t.border_subtle,
        "border_default": t.border_default,
        "border_strong": t.border_strong,
        "border_focus": t.border_focus,
        "accent_default": t.accent_default,
        "accent_hover": t.accent_hover,
        "accent_pressed": t.accent_pressed,
        "font_ui": t.font_ui,
        "font_mono": t.font_mono,
        "font_caption": f"{dp(fs.caption)}px",
        "font_body": f"{dp(fs.body)}px",
        "font_subtitle": f"{dp(fs.subtitle)}px",
        "font_title": f"{dp(fs.title)}px",
        "font_display": f"{dp(fs.display)}px",
        "radius_sm": f"{dp(t.radius_sm)}px",
        "radius_md": f"{dp(t.radius_md)}px",
        "radius_lg": f"{dp(t.radius_lg)}px",
        "control_h": f"{dp(t.control_h)}px",
        "control_h_box": f"{dp(t.control_h) - 2}px",
        "control_h_compact": f"{dp(t.control_h_compact)}px",
        "control_h_compact_box": f"{dp(t.control_h_compact) - 2}px",
        "table_row_h": f"{dp(t.table_row_h)}px",
        "icon_size": f"{dp(t.icon_size)}px",
    }
    for i, v in enumerate(space, start=1):
        m[f"space_{i}"] = f"{dp(v)}px"
    for state in ("success", "warning", "error", "info", "running", "skipped"):
        s = getattr(t, f"state_{state}")
        m[f"state_{state}_fg"] = s.fg
        m[f"state_{state}_bg"] = s.bg
        m[f"state_{state}_border"] = s.border
    # 勾选框 SVG（与当前 accent 同色系；资源命名 checked_<accent-hex>.svg）
    m.update(_checkbox_icon_map(t))
    return m


# accent hex（去 #）→ 已存在的勾选 SVG 资源后缀；未命中回退主色
_CHECK_ICON_FILES = ("5d45ff", "4f46e5", "d14b72", "2f6fed", "18b67a", "d4a514")


def _checkbox_icon_map(theme: Tokens) -> dict[str, str]:
    """按主题 accent 匹配 resources/icons 下勾选 SVG（绝对路径，QSS url() 用）。"""
    from ui.resource_path import get_resource_base
    icons = Path(get_resource_base()) / "resources" / "icons"
    accent = theme.accent_default.lstrip("#").lower()
    # 就近取已知资源里与 accent 同色系者；无匹配用 accent 自身（约定命名）
    name = accent if accent in _CHECK_ICON_FILES else _nearest_check_icon(accent)
    checked = (icons / f"checked_{name}.svg").as_posix()
    unchecked = (icons / f"unchecked_{name}.svg").as_posix()
    return {"check_svg": checked, "uncheck_svg": unchecked}


def _nearest_check_icon(accent: str) -> str:
    """在已存在的资源后缀中挑与 accent 最接近的（简单 RGB 距离）。"""
    def _rgb(h: str) -> tuple[int, int, int]:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    try:
        target = _rgb(accent)
    except (ValueError, IndexError):
        return "5d45ff"
    return min(_CHECK_ICON_FILES,
               key=lambda c: sum((a - b) ** 2 for a, b in zip(_rgb(c), target)))


def load_qss(name: str, theme: Tokens | None = None, **overrides: str) -> str:
    """渲染 ``qss/<name>.qss``：token 注入 + 调用方局部覆盖（``$`` 占位）。"""
    path = _QSS_DIR / f"{name}.qss"
    text = path.read_text(encoding="utf-8")
    mapping = token_map(theme)
    mapping.update(overrides)
    return Template(text).safe_substitute(mapping)


def apply_qss(widget, name: str, theme: Tokens | None = None, **overrides: str) -> None:
    """白名单样式注入点：全 ui/ 唯一允许调 ``setStyleSheet`` 的地方。

    组件/页面一律 ``apply_qss(self, "controls")`` 等，禁止直接 setStyleSheet。
    """
    widget.setStyleSheet(load_qss(name, theme, **overrides))  # noqa: whitelist


# ------------------------------------------------------------------ 应用入口
def apply(app: QApplication, theme: Tokens | None = None) -> None:
    """启动时统一注入：全局字体 + 基础 QSS（tooltip 等真正全局安全的规则）。

    页面/组件级样式由各处 ``apply_qss`` 按需注入，不在此全局铺开，
    避免 app 级通配选择器干扰存量页面（Qt 层叠规则：widget 级优先于 app 级）。
    """
    global _current
    _current = theme or dark_tokens()
    families = [f.strip().strip('"') for f in _current.font_ui.split(",")]
    font = QFont()
    font.setFamilies(families)
    font.setPointSize(_current.font_scale.body)
    app.setFont(font)
    app.setStyleSheet(load_qss("base", _current))
