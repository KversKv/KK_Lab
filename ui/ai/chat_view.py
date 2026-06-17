"""ChatView：聊天消息列表展示（只读滚动区）。

助手消息走 Markdown 渲染（QTextBrowser.setMarkdown，F6）；代码块单独抽出为
带"复制"按钮的代码块控件；用户/系统消息保持纯文本气泡；结构化日志分析仍走固定
HTML 组件（F6.4，不混入自由 Markdown）。
"""
from __future__ import annotations

import html as _html_mod
import re

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from log_config import get_logger
from ui.widgets.scrollbar import SCROLLBAR_STYLE

logger = get_logger(__name__)

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
QTextBrowser#aiBubbleAI {
    background-color: #141b2c;
    color: #d7e3ff;
    border: 1px solid #243152;
    border-radius: 10px;
    padding: 6px 10px;
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

_CODE_FRAME_STYLE = """
QFrame#aiCodeFrame {
    background-color: #0d1322;
    border: 1px solid #243152;
    border-radius: 8px;
}
QPlainTextEdit#aiCodeText {
    background-color: transparent;
    color: #cfe1ff;
    border: none;
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
}
QLabel#aiCodeLang {
    color: #7e93b8;
    font-size: 10px;
    background: transparent;
    padding: 2px 6px;
}
QPushButton#aiCopyBtn {
    min-height: 20px;
    padding: 1px 10px;
    border: 1px solid #22376A;
    border-radius: 6px;
    background-color: #13254b;
    color: #cfe1ff;
    font-size: 10px;
}
QPushButton#aiCopyBtn:hover {
    background-color: #1C2D55;
    border: 1px solid #3A5A9F;
}
"""

_SEVERITY_COLORS = {
    "info": "#7aa2ff",
    "low": "#5fcf80",
    "medium": "#e6c23c",
    "high": "#ef8f4b",
    "critical": "#ef5a5a",
}

_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)


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


def _split_markdown_blocks(text: str) -> list[tuple[str, str, str]]:
    """把 Markdown 拆为 (kind, lang, content) 序列。

    kind ∈ {"md", "code"}；code 块附带语言名（可能为空）。
    """
    blocks: list[tuple[str, str, str]] = []
    last = 0
    for match in _FENCE_RE.finditer(text):
        if match.start() > last:
            md = text[last:match.start()].strip("\n")
            if md.strip():
                blocks.append(("md", "", md))
        lang = (match.group(1) or "").strip()
        code = match.group(2)
        blocks.append(("code", lang, code))
        last = match.end()
    tail = text[last:].strip("\n")
    if tail.strip():
        blocks.append(("md", "", tail))
    if not blocks:
        blocks.append(("md", "", text))
    return blocks


class _MarkdownBubble(QWidget):
    """一条 AI 气泡：Markdown 段 + 代码块（带复制）混排。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._raw_text = ""

    def set_markdown(self, text: str) -> None:
        self._raw_text = text or ""
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for kind, lang, content in _split_markdown_blocks(self._raw_text):
            if kind == "code":
                self._layout.addWidget(self._make_code_block(lang, content))
            else:
                self._layout.addWidget(self._make_md_block(content))

    def _make_md_block(self, md_text: str) -> QTextBrowser:
        view = QTextBrowser()
        view.setObjectName("aiBubbleAI")
        view.setStyleSheet(_BUBBLE_STYLE_AI)
        view.setOpenLinks(False)
        view.setOpenExternalLinks(False)
        view.anchorClicked.connect(self._on_anchor_clicked)
        view.setFrameShape(QFrame.NoFrame)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        view.setMarkdown(md_text)
        view.document().setTextWidth(view.viewport().width())
        view.document().contentsChanged.connect(lambda v=view: self._fit_height(v))
        self._fit_height(view)
        return view

    @staticmethod
    def _fit_height(view: QTextBrowser) -> None:
        doc = view.document()
        doc.setTextWidth(view.viewport().width())
        height = int(doc.size().height()) + 8
        view.setFixedHeight(max(24, height))

    def _make_code_block(self, lang: str, code: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("aiCodeFrame")
        frame.setStyleSheet(_CODE_FRAME_STYLE)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        header = QWidget()
        header.setStyleSheet("background: transparent;")
        from PySide6.QtWidgets import QHBoxLayout

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        lang_label = QLabel(lang or "code")
        lang_label.setObjectName("aiCodeLang")
        header_layout.addWidget(lang_label)
        header_layout.addStretch(1)
        copy_btn = QPushButton("复制")
        copy_btn.setObjectName("aiCopyBtn")
        copy_btn.setCursor(Qt.PointingHandCursor)
        code_text = code.rstrip("\n")
        copy_btn.clicked.connect(lambda _=False, t=code_text: self._copy_code(t))
        header_layout.addWidget(copy_btn)
        layout.addWidget(header)

        editor = QPlainTextEdit()
        editor.setObjectName("aiCodeText")
        editor.setReadOnly(True)
        editor.setPlainText(code_text)
        editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        editor.setStyleSheet(_CODE_FRAME_STYLE)
        line_count = code_text.count("\n") + 1
        editor.setFixedHeight(min(320, 18 * line_count + 12))
        layout.addWidget(editor)
        return frame

    @staticmethod
    def _copy_code(text: str) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)

    @staticmethod
    def _on_anchor_clicked(url: QUrl) -> None:
        scheme = (url.scheme() or "").lower()
        if scheme in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)
        else:
            logger.debug("AI 消息内部/未知链接已忽略: %s", url.toString())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        for i in range(self._layout.count()):
            widget = self._layout.itemAt(i).widget()
            if isinstance(widget, QTextBrowser):
                self._fit_height(widget)


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

        self._stream_bubble: _MarkdownBubble | None = None
        self._stream_text = ""

    def _insert_row(self, widget: QWidget, align) -> None:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(widget, 0, align)
        self._layout.insertWidget(self._layout.count() - 1, row)
        self._scroll_to_bottom()

    def _append_bubble(self, text: str, object_name: str, style: str, align) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        label.setStyleSheet(style)
        self._insert_row(label, align)
        return label

    def _append_html_bubble(self, html: str) -> QTextBrowser:
        view = QTextBrowser()
        view.setObjectName("aiBubbleAI")
        view.setStyleSheet(_BUBBLE_STYLE_AI)
        view.setOpenExternalLinks(True)
        view.setFrameShape(QFrame.NoFrame)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        view.setHtml(html)
        doc = view.document()
        doc.setTextWidth(view.viewport().width())
        view.setMinimumHeight(int(doc.size().height()) + 12)
        self._insert_row(view, Qt.AlignLeft)
        return view

    def _append_markdown_bubble(self, text: str) -> _MarkdownBubble:
        bubble = _MarkdownBubble()
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        bubble.set_markdown(text)
        self._insert_row(bubble, Qt.AlignLeft)
        return bubble

    def add_user_message(self, text: str) -> None:
        self._append_bubble(text, "aiBubbleUser", _BUBBLE_STYLE_USER, Qt.AlignRight)

    def add_ai_message(self, text: str) -> _MarkdownBubble:
        return self._append_markdown_bubble(text or "（无内容）")

    def begin_stream_message(self) -> _MarkdownBubble:
        """开始一条流式 AI 气泡，返回气泡供增量更新。"""
        self._stream_bubble = self._append_markdown_bubble("▍")
        self._stream_text = ""
        return self._stream_bubble

    def append_stream_delta(self, chunk: str) -> None:
        """向当前流式气泡追加增量文本（整段重渲染 Markdown）。"""
        bubble = getattr(self, "_stream_bubble", None)
        if bubble is None:
            return
        self._stream_text = getattr(self, "_stream_text", "") + (chunk or "")
        bubble.set_markdown(self._stream_text + " ▍")
        self._scroll_to_bottom()

    def end_stream_message(self, final_text: str = "") -> None:
        """结束流式气泡：写入最终全文（去掉光标），清理状态。"""
        bubble = getattr(self, "_stream_bubble", None)
        if bubble is None:
            return
        text = final_text if final_text else getattr(self, "_stream_text", "")
        bubble.set_markdown(text or "（无内容）")
        self._stream_bubble = None
        self._stream_text = ""
        self._scroll_to_bottom()

    def add_analysis_message(self, result) -> QTextBrowser:
        """渲染结构化日志分析结果（F6.4：固定 HTML 组件，不走自由 Markdown）。"""
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
        return self._append_html_bubble(html)

    def add_system_message(self, text: str) -> None:
        self._append_bubble(text, "aiBubbleSys", _BUBBLE_STYLE_SYS, Qt.AlignHCenter)

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
