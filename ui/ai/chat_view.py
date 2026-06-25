"""ChatView：聊天消息列表展示（只读滚动区）。

助手消息走 Markdown 渲染（QTextBrowser.setMarkdown，F6）；代码块单独抽出为
带"复制"按钮的代码块控件；用户/系统消息保持纯文本气泡；结构化日志分析仍走固定
HTML 组件（F6.4，不混入自由 Markdown）。
"""
from __future__ import annotations

import html as _html_mod
import os
import re

from PySide6.QtCore import QSize, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from log_config import get_logger
from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon
from ui.widgets.scrollbar import SCROLLBAR_STYLE

logger = get_logger(__name__)

_ICONS_DIR = os.path.join(get_resource_base(), "resources", "icons")
_THUMBS_UP_ICON = os.path.join(_ICONS_DIR, "thumbs-up.svg")
_THUMBS_DOWN_ICON = os.path.join(_ICONS_DIR, "thumbs-down.svg")
_MORE_ICON = os.path.join(_ICONS_DIR, "more-horizontal.svg")

_BUBBLE_STYLE_USER = """
QLabel#aiBubbleUser {
    background-color: #18397a;
    color: #eff6ff;
    border: none;
    border-radius: 16px;
    border-bottom-right-radius: 2px;
    padding: 12px 16px;
    font-size: 12px;
    font-weight: 400;
}
"""

_BUBBLE_STYLE_AI = """
QTextBrowser#aiBubbleAI {
    background-color: #121629;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 16px;
    border-bottom-left-radius: 2px;
    padding: 12px 16px;
    font-size: 12px;
    font-weight: 400;
}
"""

_BUBBLE_PAD_V = 28
_BUBBLE_PAD_H = 36
_BUBBLE_MIN_H = 40

_BUBBLE_STYLE_SYS = """
QLabel#aiBubbleSys {
    background-color: transparent;
    color: #64748b;
    font-size: 11px;
    padding: 2px 4px;
}
"""

# 任务卡片（S7-3 / S8）：定时/异步任务状态展示，居中、可原地更新。
_TASK_CARD_STYLE = """
QFrame#aiTaskCard {
    background-color: #0b1428;
    border: 1px solid #1e293b;
    border-radius: 12px;
}
QLabel#aiTaskCardText {
    background: transparent;
    color: #cbd5e1;
    font-size: 11px;
}
QLabel#aiTaskCardBadge {
    background-color: #122a1c;
    color: #4ade80;
    border: 1px solid #14532d;
    border-radius: 8px;
    padding: 1px 8px;
    font-size: 10px;
}
"""

_CODE_FRAME_STYLE = """
QFrame#aiCodeFrame {
    background-color: #070709;
    border: 1px solid #1e293b;
    border-radius: 12px;
}
QPlainTextEdit#aiCodeText {
    background-color: transparent;
    color: #cbd5e1;
    border: none;
    font-family: Consolas, "Courier New", monospace;
    font-size: 12px;
}
QLabel#aiCodeLang {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    background: transparent;
    padding: 2px 6px;
}
QPushButton#aiCopyBtn {
    min-height: 20px;
    padding: 1px 10px;
    border: 1px solid #1e293b;
    border-radius: 6px;
    background-color: #1e293b;
    color: #cbd5e1;
    font-size: 10px;
    font-weight: 600;
}
QPushButton#aiCopyBtn:hover {
    background-color: #334155;
    border: 1px solid #475569;
}
"""

_SEVERITY_COLORS = {
    "info": "#7aa2ff",
    "low": "#5fcf80",
    "medium": "#e6c23c",
    "high": "#ef8f4b",
    "critical": "#ef5a5a",
}

_CONFIRM_FRAME_STYLE = """
QFrame#aiConfirmFrame {
    background-color: #121629;
    border: 1px solid #1e293b;
    border-radius: 12px;
}
QLabel#aiConfirmTitle {
    color: #fbbf77;
    font-size: 12px;
    font-weight: 700;
    background: transparent;
}
QLabel#aiConfirmDesc {
    color: #cbd5e1;
    font-size: 11px;
    background: transparent;
}
QPlainTextEdit#aiConfirmArgs {
    background-color: #070709;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 8px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 11px;
}
QPushButton#aiConfirmRun {
    min-height: 22px; padding: 4px 14px;
    border: none; border-radius: 8px;
    background-color: #16a34a; color: #ffffff; font-weight: 700; font-size: 11px;
}
QPushButton#aiConfirmRun:hover { background-color: #15803d; }
QPushButton#aiConfirmRun:disabled { background-color: #0f172a; color: #475569; }
QPushButton#aiConfirmReject {
    min-height: 22px; padding: 4px 14px;
    border: 1px solid #7f1d1d; border-radius: 8px;
    background-color: #2a1414; color: #fca5a5; font-weight: 700; font-size: 11px;
}
QPushButton#aiConfirmReject:hover { background-color: #3a1a1a; }
QPushButton#aiConfirmReject:disabled { background-color: #0f172a; color: #475569; border: 1px solid #1e293b; }
QPushButton#aiConfirmAllow {
    min-height: 22px; padding: 4px 14px;
    border: 1px solid #1d2f52; border-radius: 8px;
    background-color: #0e1b33; color: #3b82f6; font-weight: 700; font-size: 11px;
}
QPushButton#aiConfirmAllow:hover { background-color: #14264a; }
QPushButton#aiConfirmAllow:disabled { background-color: #0f172a; color: #475569; border: 1px solid #1e293b; }
"""

_RISK_LABEL_CN = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "危险",
}


class ActionConfirmCard(QFrame):
    """聊天内联动作确认卡片：运行 / 拒绝 / 添加到白名单。

    仅用于需要确认的动作（high/critical）。三个按钮通过信号回报用户选择：
      - run_clicked     : 直接运行（不写白名单）；
      - reject_clicked  : 拒绝执行；
      - allow_clicked   : 添加到白名单（由面板弹会话/永久二选一）。
    回报后卡片自动禁用所有按钮并显示最终状态文案，避免重复点击。
    """

    run_clicked = Signal()
    reject_clicked = Signal()
    allow_clicked = Signal()

    def __init__(self, action_name: str, description: str, risk_level: str,
                 arguments: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("aiConfirmFrame")
        self.setStyleSheet(_CONFIRM_FRAME_STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        risk_cn = _RISK_LABEL_CN.get(risk_level, risk_level)
        title = QLabel(f"待确认动作 · {risk_cn} · {action_name}")
        title.setObjectName("aiConfirmTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        if description:
            desc = QLabel(description)
            desc.setObjectName("aiConfirmDesc")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        if arguments:
            args_view = QPlainTextEdit()
            args_view.setObjectName("aiConfirmArgs")
            args_view.setReadOnly(True)
            try:
                import json as _json

                args_text = _json.dumps(arguments, ensure_ascii=False, indent=2)
            except (TypeError, ValueError):
                args_text = str(arguments)
            args_view.setPlainText(args_text)
            lines = args_text.count("\n") + 1
            args_view.setFixedHeight(min(140, 18 * lines + 14))
            layout.addWidget(args_view)

        self._status = QLabel("")
        self._status.setObjectName("aiConfirmDesc")
        self._status.setWordWrap(True)
        self._status.setVisible(False)
        layout.addWidget(self._status)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self._run_btn = QPushButton("运行")
        self._run_btn.setObjectName("aiConfirmRun")
        self._run_btn.setCursor(Qt.PointingHandCursor)
        self._run_btn.clicked.connect(self._on_run)
        bar.addWidget(self._run_btn)

        self._reject_btn = QPushButton("拒绝")
        self._reject_btn.setObjectName("aiConfirmReject")
        self._reject_btn.setCursor(Qt.PointingHandCursor)
        self._reject_btn.clicked.connect(self._on_reject)
        bar.addWidget(self._reject_btn)

        self._allow_btn = QPushButton("添加到白名单")
        self._allow_btn.setObjectName("aiConfirmAllow")
        self._allow_btn.setCursor(Qt.PointingHandCursor)
        self._allow_btn.clicked.connect(self.allow_clicked.emit)
        # 仅 high 风险动作可写白名单；critical 不可白名单，故隐藏该按钮。
        self._allow_btn.setVisible(risk_level == "high")
        bar.addWidget(self._allow_btn)

        bar.addStretch(1)
        layout.addLayout(bar)

    def _on_run(self) -> None:
        self.run_clicked.emit()

    def _on_reject(self) -> None:
        self.reject_clicked.emit()

    def set_buttons_enabled(self, enabled: bool) -> None:
        self._run_btn.setEnabled(enabled)
        self._reject_btn.setEnabled(enabled)
        self._allow_btn.setEnabled(enabled)

    def finalize(self, status_text: str) -> None:
        """收尾：禁用按钮并显示最终状态文案。"""
        self.set_buttons_enabled(False)
        self._status.setText(status_text)
        self._status.setVisible(True)

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
        view.document().setDocumentMargin(0)
        view.setMarkdown(md_text)
        view.document().contentsChanged.connect(lambda v=view: self._fit_height(v))
        QTimer.singleShot(0, lambda v=view: self._fit_height(v))
        self._fit_height(view)
        return view

    @staticmethod
    def _fit_height(view: QTextBrowser) -> None:
        doc = view.document()
        width = view.viewport().width()
        if width <= 0:
            width = max(0, view.width() - _BUBBLE_PAD_H)
        doc.setTextWidth(width)
        height = int(doc.size().height()) + _BUBBLE_PAD_V
        view.setFixedHeight(max(_BUBBLE_MIN_H, height))

    def _make_code_block(self, lang: str, code: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("aiCodeFrame")
        frame.setStyleSheet(_CODE_FRAME_STYLE)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)

        header = QWidget()
        header.setStyleSheet("background: transparent;")
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


_CHAT_VIEW_RESET_STYLE = """
QScrollArea { background: transparent; border: none; }
QFrame { border: none; background: transparent; }
QLabel { border: none; background: transparent; }
QTextBrowser { border: none; }
QPlainTextEdit { border: none; }
QPushButton { border: none; }
"""


class ChatView(QScrollArea):
    feedback_submitted = Signal(str, str)
    curate_requested = Signal(str, str)
    manage_memory_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet(SCROLLBAR_STYLE + _CHAT_VIEW_RESET_STYLE)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(20)
        self._layout.addStretch(1)
        self.setWidget(self._container)

        self._stream_bubble: _MarkdownBubble | None = None
        self._stream_text = ""
        self._user_bubbles: list[QLabel] = []
        self._msg_seq = 0
        # task_id -> (card_frame, text_label, badge_label) 供原地更新（S7-3）
        self._task_cards: dict[str, tuple] = {}

    def _next_msg_id(self) -> str:
        self._msg_seq += 1
        return f"msg_{self._msg_seq}"

    def clear(self) -> None:
        """清空所有已显示的消息气泡，恢复到空白会话状态。"""
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._stream_bubble = None
        self._stream_text = ""
        self._user_bubbles = []
        self._task_cards = {}

    def _make_ai_footer(self, msg_id: str) -> QWidget:
        """AI 气泡下方动作条：👍/👎 反馈 + ⋯ 沉淀菜单。"""
        bar = QWidget()
        bar.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(2, 0, 0, 0)
        layout.setSpacing(4)

        up = QPushButton()
        down = QPushButton()
        more = QPushButton()
        for btn, icon_path, size in (
            (up, _THUMBS_UP_ICON, 12),
            (down, _THUMBS_DOWN_ICON, 12),
            (more, _MORE_ICON, 14),
        ):
            btn.setObjectName("aiCopyBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(22)
            if os.path.isfile(icon_path):
                btn.setIcon(tinted_svg_icon(icon_path, "#cbd5e1", size))
                btn.setIconSize(QSize(size, size))
            layout.addWidget(btn)
        layout.addStretch(1)

        up.clicked.connect(lambda _=False: self.feedback_submitted.emit(msg_id, "up"))
        down.clicked.connect(lambda _=False: self.feedback_submitted.emit(msg_id, "down"))
        more.clicked.connect(lambda _=False, b=more: self._show_curate_menu(b))
        return bar

    def _show_curate_menu(self, anchor: QPushButton) -> None:
        menu = QMenu(self)
        menu.addAction("沉淀为纠偏", lambda: self.curate_requested.emit("nudge", ""))
        menu.addAction(
            "沉淀为快捷指令", lambda: self.curate_requested.emit("quick_action", "")
        )
        menu.addAction(
            "沉淀为项目规则", lambda: self.curate_requested.emit("project_rule", "")
        )
        menu.addAction(
            "沉淀为 eval 用例", lambda: self.curate_requested.emit("eval_case", "")
        )
        menu.addSeparator()
        kk_menu = menu.addMenu("归档到本页记忆")
        kk_menu.addAction(
            "本页长期记忆", lambda: self.curate_requested.emit("kk_memory", "")
        )
        kk_menu.addAction(
            "本页经验/排障", lambda: self.curate_requested.emit("kk_lesson", "")
        )
        kk_menu.addAction(
            "本页测试项", lambda: self.curate_requested.emit("kk_test_item", "")
        )
        kk_menu.addAction(
            "本页测试用例", lambda: self.curate_requested.emit("kk_test_case", "")
        )
        kk_menu.addAction(
            "本页快捷指令", lambda: self.curate_requested.emit("kk_quick_action", "")
        )
        menu.addSeparator()
        menu.addAction("管理本页记忆…", self.manage_memory_requested.emit)
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _available_width(self) -> int:
        return max(120, self.viewport().width() - 32)

    def _fit_user_bubble(self, label: QLabel) -> None:
        label.setMaximumWidth(int(self._available_width() * 0.88))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        for label in self._user_bubbles:
            if label is not None:
                self._fit_user_bubble(label)

    def _insert_row(self, widget: QWidget, align=None) -> None:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        if align is None:
            row_layout.addWidget(widget)
        else:
            row_layout.addWidget(widget, 0, align)
        self._layout.insertWidget(self._layout.count() - 1, row)
        self._scroll_to_bottom()

    def _append_bubble(self, text: str, object_name: str, style: str, align) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet(style)
        if align == Qt.AlignHCenter:
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            label.setAlignment(Qt.AlignHCenter)
            self._insert_row(label)
        else:
            label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
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
        view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        view.setHtml(html)
        doc = view.document()
        doc.setTextWidth(view.viewport().width())
        view.setMinimumHeight(int(doc.size().height()) + 12)
        self._insert_row(view)
        return view

    def _append_markdown_bubble(self, text: str) -> _MarkdownBubble:
        bubble = _MarkdownBubble()
        bubble.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        bubble.set_markdown(text)
        self._insert_row(bubble)
        return bubble

    def add_user_message(self, text: str) -> None:
        label = QLabel(text)
        label.setObjectName("aiBubbleUser")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        label.setStyleSheet(_BUBBLE_STYLE_USER)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addStretch(1)
        row_layout.addWidget(label, 0, Qt.AlignTop)
        self._user_bubbles.append(label)
        self._fit_user_bubble(label)
        self._layout.insertWidget(self._layout.count() - 1, row)
        QTimer.singleShot(0, lambda lb=label: self._fit_user_bubble(lb))
        self._scroll_to_bottom()

    def add_ai_message(self, text: str) -> _MarkdownBubble:
        bubble = self._append_markdown_bubble(text or "（无内容）")
        self._insert_row(self._make_ai_footer(self._next_msg_id()))
        return bubble

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

    def discard_stream_message(self) -> None:
        """出错时清理未完成的流式气泡：保留已收到的文本，去掉光标，不再追加。"""
        bubble = getattr(self, "_stream_bubble", None)
        if bubble is None:
            return
        text = getattr(self, "_stream_text", "")
        bubble.set_markdown(text or "（已中断）")
        self._stream_bubble = None
        self._stream_text = ""

    def end_stream_message(self, final_text: str = "") -> None:
        """结束流式气泡：写入最终全文（去掉光标），清理状态。"""
        bubble = getattr(self, "_stream_bubble", None)
        if bubble is None:
            return
        text = final_text if final_text else getattr(self, "_stream_text", "")
        bubble.set_markdown(text or "（无内容）")
        self._stream_bubble = None
        self._stream_text = ""
        self._insert_row(self._make_ai_footer(self._next_msg_id()))
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

    def add_system_action(self, text: str, button_text: str, callback) -> QPushButton:
        """系统消息 + 内联动作按钮（F5.5：应用后提供"撤销"入口）。

        返回按钮供调用方在动作完成后禁用/改文案。
        """
        container = QWidget()
        container.setObjectName("aiBubbleSys")
        container.setStyleSheet(_BUBBLE_STYLE_SYS)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(label)

        button = QPushButton(button_text)
        button.setObjectName("aiCopyBtn")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(callback)
        layout.addWidget(button, 0, Qt.AlignLeft)

        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._insert_row(container)
        return button

    def add_action_confirm(
        self, action_name: str, description: str, risk_level: str, arguments: dict
    ) -> ActionConfirmCard:
        """插入内联动作确认卡片（运行/拒绝/添加到白名单），返回卡片供面板接线。"""
        card = ActionConfirmCard(action_name, description, risk_level, arguments)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self._insert_row(card)
        return card

    def add_task_card(
        self, task_id: str, status: str, text: str, *, auto_resume: bool = False
    ) -> None:
        """插入/更新一张任务状态卡片（S7-3 / S8）。

        同一 task_id 重复调用为原地更新（status/text 变化即刷新），不重复插入；
        auto_resume=True 时显示"自动续跑"角标（S8-3）。
        """
        existing = self._task_cards.get(task_id)
        if existing is not None:
            _card, text_label, badge_label = existing
            text_label.setText(text)
            if auto_resume:
                badge_label.setText("自动续跑")
                badge_label.setVisible(True)
            return

        card = QFrame()
        card.setObjectName("aiTaskCard")
        card.setStyleSheet(_TASK_CARD_STYLE)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        text_label = QLabel(text)
        text_label.setObjectName("aiTaskCardText")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(text_label, 1)

        badge_label = QLabel("自动续跑")
        badge_label.setObjectName("aiTaskCardBadge")
        badge_label.setVisible(auto_resume)
        layout.addWidget(badge_label, 0, Qt.AlignTop)

        self._task_cards[task_id] = (card, text_label, badge_label)
        self._insert_row(card)

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
        QTimer.singleShot(0, self._scroll_to_bottom_deferred)
        QTimer.singleShot(30, self._scroll_to_bottom_deferred)

    def _scroll_to_bottom_deferred(self) -> None:
        self._container.updateGeometry()
        self._layout.activate()
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
