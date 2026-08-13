"""BadgeDelegate — 状态列 Pill 徽章绘制委托（仅负责绘制，不改模型/交互）。

Pill 规格（2026-08 暗色重构，色值全部取自 ``ui.theme.tokens``）：
- 高 20px、圆角 10px（胶囊）、字号 11px；
- 底色 = 语义色 12% 透明、1px 描边 = 语义色 20% 透明、文字 = 语义色；
- 状态 → 语义色映射由调用方经 ``state_map`` 提供（映射到 ``Tokens``
  的 ``state_*`` 属性名），组件内零裸色值。

复用方式：
- ``draw_pill_badge()``：裸绘制函数，供已有委托（如 TestPlanPanel 的
  ``_StatusBadgeDelegate``）在自己的 ``paint()`` 内调用；
- ``StatusPillDelegate``：开箱即用的列委托（任意 ``QTreeView/QTableView``）。
- ``paint_item_background()``：自定义委托覆盖 ``paint()`` 前先由 QStyle
  绘制选中/hover 背景（否则 ``::item:selected`` 背景在该列不生效）。

主题说明（2026-08）：Module Test 用独立 ``module_dark_tokens()``（**不改全局**
``dark_tokens()``）。委托经 ``_badge_theme()`` 解析——优先本页 token，失败回退
``current_theme()``（保证委托在任何页面自包含可用、且本页用对色板）。
"""
from __future__ import annotations

import re

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication, QStyle, QStyleOptionViewItem, QStyledItemDelegate,
)

from ui.theme import dp
from ui.theme.tokens import StateSet

# PySide6 的 QColor 字符串构造不支持 'rgba(r,g,b,a)' 文本（返回 invalid → 纯黑），
# tokens 中 state.bg/border 均为该格式，需手动解析为 QColor(r,g,b,a)。
_RGBA_RE = re.compile(r'rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')


def parse_qcolor(color_str: str) -> QColor:
    """从颜色字符串构造 QColor；兼容 ``rgba(r,g,b,a)``（alpha 0-255 整数）。"""
    m = _RGBA_RE.match(color_str)
    if m:
        r, g, b, a = map(int, m.groups())
        return QColor(r, g, b, a)
    return QColor(color_str)


def _badge_theme():
    """解析徽章用主题：优先 Module Test 专属 token，失败回退全局当前主题。

    Module Test 经独立 ``module_dark_tokens()`` 换肤（不改全局 dark_tokens），
    故这里显式优先取它，保证本页徽章用对新色板；其它页面回退 ``current_theme``。
    """
    try:
        from ui.theme.tokens import module_dark_tokens
        return module_dark_tokens()
    except Exception:  # noqa: BLE001 - 回退兜底，不阻断绘制
        from ui.theme import current_theme
        return current_theme()


def paint_item_background(painter: QPainter, option: QStyleOptionViewItem) -> None:
    """用 QStyle 绘制 item 背景面板（含选中/hover 态），与 QSS ``::item`` 对齐。"""
    opt = QStyleOptionViewItem(option)
    opt.text = ""
    opt.icon = QIcon()
    opt.viewItemPosition = QStyleOptionViewItem.ViewItemPosition.OnlyOne
    style = opt.widget.style() if opt.widget else QApplication.style()
    style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)


def draw_pill_badge(painter: QPainter, rect: QRect, text: str,
                    state: StateSet, *, pulse: bool = False) -> QRect:
    """在 ``rect`` 内左对齐、垂直居中绘制一枚语义 Pill 徽章。

    ``pulse=True`` 时在徽章右侧叠加一个 6px 呼吸点（运行中态）。
    返回徽章实际占用的矩形。
    """
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    h = min(dp(20), max(rect.height() - dp(4), dp(12)))
    # Pill 字号 11px（独立于视图正文字号）
    font = QFont(painter.font())
    font.setPixelSize(dp(11))
    painter.setFont(font)
    w = min(painter.fontMetrics().horizontalAdvance(text) + dp(16),
            rect.width() - dp(8))
    badge = QRect(rect.left() + dp(4), rect.center().y() - h // 2, w, h)
    painter.setPen(QPen(parse_qcolor(state.border), 1))
    painter.setBrush(parse_qcolor(state.bg))
    painter.drawRoundedRect(badge, h / 2.0, h / 2.0)
    painter.setPen(parse_qcolor(state.fg))
    painter.drawText(badge, Qt.AlignCenter, text)
    if pulse:
        cx = badge.right() + dp(6)
        if cx + dp(6) < rect.right():
            painter.setPen(Qt.NoPen)
            painter.setBrush(parse_qcolor(state.fg))
            painter.drawEllipse(cx, badge.center().y() - dp(3), dp(6), dp(6))
    painter.restore()
    return badge


class StatusPillDelegate(QStyledItemDelegate):
    """通用状态列 Pill 委托（仅绘制）。

    :param state_map: 状态键 → ``Tokens`` 状态属性名
        （如 ``{"pass": "state_success"}``）；未命中回退 ``state_skipped``。
    :param status_role: 读取状态键的 ``ItemDataRole``。
    :param column: 限定列号（-1 = 所有列）。
    :param group_role: 分组行判定 Role（非空命中时回退默认绘制）。
    """

    def __init__(self, state_map: dict[str, str] | None = None, *,
                 status_role: int = int(Qt.UserRole),
                 column: int = -1, group_role: int | None = None,
                 parent=None):
        super().__init__(parent)
        self._state_map = state_map or {}
        self._status_role = status_role
        self._column = column
        self._group_role = group_role
        self.pulse = False  # 呼吸点开关（由宿主 QTimer 翻转，可选）

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        if (self._column >= 0 and index.column() != self._column) or (
                self._group_role is not None and index.data(self._group_role)):
            super().paint(painter, option, index)
            return
        status = index.data(self._status_role) or ""
        text = index.data(Qt.DisplayRole) or ""
        theme = _badge_theme()
        state = getattr(theme, self._state_map.get(status, "state_skipped"),
                        theme.state_skipped)
        paint_item_background(painter, option)
        draw_pill_badge(painter, option.rect, str(text), state,
                        pulse=self.pulse)

    def sizeHint(self, option: QStyleOptionViewItem,
                 index: QModelIndex) -> QSize:
        hint = super().sizeHint(option, index)
        hint.setHeight(max(hint.height(), dp(20) + dp(6)))
        return hint
