"""ChatView：聊天消息列表展示（只读滚动区）。"""
from __future__ import annotations

import html as _html_mod

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.scrollbar import SCROLLBAR_STYLE

_BUBBLE_STYLE_USER = """
QLabel#aiBubbleUser {
    background-color: #1d3a6e;
    color: #eaf1ff;
    border: 1px solid #2a4d8f;
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 12px;
}
"""

_BUBBLE_STYLE_AI = """
QLabel#aiBubbleAI {
    background-color: #141b2c;
    color: #d7e3ff;
    border: 1px solid #243152;
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 12px;
}
"""

_BUBBLE_STYLE_SYS = """
QLabel#aiBubbleSys {
    background-color: transparent;
    color: #8fa3c2;
    font-size: 11px;
    padding: 2px 4px;
}
"""

_SEVERITY_COLORS = {
    "info": "#7aa2ff",
    "low": "#5fcf80",
    "medium": "#e6c23c",
    "high": "#ef8f4b",
    "critical": "#ef5a5a",
}


def _esc(text) -> str:
    return _html_mod.escape(str(text))


def _html_list(title: str, items) -> str:
    items = [i for i in (items or []) if str(i).strip()]
    if not items:
        return ""
    lis = "".join(f"<li>{_esc(i)}</li>" for i in items)
    return (
        f'<div style="margin-top:6px;font-weight:600;">{title}</div>'
        f'<ul style="margin:2px 0 0 16px;padding:0;">{lis}</ul>'
    )


class ChatView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(SCROLLBAR_STYLE + "QScrollArea { background: transparent; border: none; }")

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)
        self.setWidget(self._container)

        self._stream_label: QLabel | None = None
        self._stream_text = ""

    def _append_bubble(self, text: str, object_name: str, style: str, align) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        label.setStyleSheet(style)
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(label, 0, align)
        self._layout.insertWidget(self._layout.count() - 1, row)
        self._scroll_to_bottom()
        return label

    def add_user_message(self, text: str) -> None:
        self._append_bubble(text, "aiBubbleUser", _BUBBLE_STYLE_USER, Qt.AlignRight)

    def add_ai_message(self, text: str) -> QLabel:
        return self._append_bubble(text, "aiBubbleAI", _BUBBLE_STYLE_AI, Qt.AlignLeft)

    def begin_stream_message(self) -> QLabel:
        """开始一条流式 AI 气泡，返回 QLabel 供增量更新。"""
        self._stream_label = self._append_bubble(
            "▍", "aiBubbleAI", _BUBBLE_STYLE_AI, Qt.AlignLeft
        )
        self._stream_text = ""
        return self._stream_label

    def append_stream_delta(self, chunk: str) -> None:
        """向当前流式气泡追加增量文本。"""
        label = getattr(self, "_stream_label", None)
        if label is None:
            return
        self._stream_text = getattr(self, "_stream_text", "") + (chunk or "")
        label.setText(self._stream_text + "▍")
        self._scroll_to_bottom()

    def end_stream_message(self, final_text: str = "") -> None:
        """结束流式气泡：写入最终全文（去掉光标），清理状态。"""
        label = getattr(self, "_stream_label", None)
        if label is None:
            return
        text = final_text if final_text else getattr(self, "_stream_text", "")
        label.setText(text or "（无内容）")
        self._stream_label = None
        self._stream_text = ""
        self._scroll_to_bottom()

    def add_analysis_message(self, result) -> QLabel:
        """渲染结构化日志分析结果（summary/severity/证据/原因/建议）。"""
        severity = (getattr(result, "severity", "info") or "info").lower()
        color = _SEVERITY_COLORS.get(severity, "#8fa3c2")
        parts = [
            f'<div style="color:{color};font-weight:700;">'
            f'日志分析 · 严重度 {severity.upper()}'
            f'（置信度 {getattr(result, "confidence", 0.0):.0%}）</div>'
        ]
        summary = getattr(result, "summary", "")
        if summary:
            parts.append(f'<div style="margin-top:4px;">{_esc(summary)}</div>')
        parts.append(_html_list("证据", getattr(result, "evidence", [])))
        parts.append(_html_list("可能原因", getattr(result, "possible_causes", [])))
        parts.append(_html_list("建议", getattr(result, "suggested_actions", [])))
        html = "".join(p for p in parts if p)
        return self._append_bubble(html, "aiBubbleAI", _BUBBLE_STYLE_AI, Qt.AlignLeft)

    def add_system_message(self, text: str) -> None:
        self._append_bubble(text, "aiBubbleSys", _BUBBLE_STYLE_SYS, Qt.AlignHCenter)

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
