"""AI 对话框深色主题与防闪白工具。

统一解决两个问题：
1. 首帧闪白：QDialog 从创建到 exec() 显示之间，样式表 polish 尚未生效，
   首帧用系统默认（白色）调色板绘制，肉眼看到一下白闪。通过在显示前用调色板
   锁定深色背景并开启 WA_StyledBackground 消除。
2. 散落对话框未设样式靠继承导致观感不一致：提供通用 AI_DIALOG_STYLE。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog

# AI 对话框统一底色（与各 _DIALOG_STYLE 中 QDialog 背景一致）。
AI_DIALOG_BG = "#070709"

# 通用 AI 对话框样式：供原本未设样式、靠继承的对话框使用，统一深色观感。
AI_DIALOG_STYLE = """
QDialog { background-color: #070709; }
QLabel { color: #cbd5e1; font-size: 12px; background: transparent; border: none; }
QLineEdit, QPlainTextEdit, QComboBox {
    background-color: #04060f; color: #e2e8f0;
    border: 1px solid #1e293b; border-radius: 6px; padding: 4px 8px; font-size: 12px;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border: 1px solid #3b82f6; }
QComboBox QAbstractItemView {
    background-color: #04060f; color: #cbd5e1;
    border: 1px solid #1e293b; selection-background-color: #1d3a6e;
}
QListWidget {
    background-color: #04060f; color: #cbd5e1;
    border: 1px solid #1e293b; border-radius: 6px; font-size: 12px;
}
QListWidget::item { padding: 4px 6px; }
QListWidget::item:selected { background-color: #1d3a6e; color: #e2e8f0; }
QCheckBox { color: #cbd5e1; font-size: 12px; background: transparent; spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; }
QPushButton {
    min-height: 26px; padding: 4px 16px;
    border: 1px solid #1e293b; border-radius: 6px;
    background-color: #0f172a; color: #cbd5e1; font-size: 12px; font-weight: 600;
}
QPushButton:hover { background-color: #1e293b; border: 1px solid #334155; }
QPushButton:default { background-color: #2563eb; border: 1px solid #2563eb; color: #ffffff; }
QPushButton:default:hover { background-color: #1d4fd0; }
QMenu {
    background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px;
    padding: 4px; color: #cbd5e1; font-size: 12px;
}
QMenu::item { padding: 5px 14px; border-radius: 4px; background: transparent; }
QMenu::item:selected { background-color: #1e293b; color: #e2e8f0; }
"""


def apply_ai_dialog_theme(
    dialog: QDialog, style: str | None = None, bg: str = AI_DIALOG_BG
) -> None:
    """给 AI 对话框套深色样式并消除首帧闪白。

    先用调色板锁定深色底（首帧即深色），再开启样式背景绘制并应用样式表。
    style 为 None 时用通用 AI_DIALOG_STYLE。
    """
    dialog.setAttribute(Qt.WA_StyledBackground, True)
    palette = dialog.palette()
    palette.setColor(dialog.backgroundRole(), QColor(bg))
    dialog.setPalette(palette)
    dialog.setStyleSheet(style if style is not None else AI_DIALOG_STYLE)
