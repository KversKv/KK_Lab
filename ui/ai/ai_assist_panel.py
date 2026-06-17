"""AIAssistPanel：右侧 AI 助手面板。

组成：标题栏 + ChatView + 输入框 + 发送/分析日志按钮。
通过 AIService 信号驱动 UI，自身不做阻塞 IO。
"""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core.ai.ai_service import AIService
from ui.ai.chat_view import ChatView
from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon
from log_config import get_logger

logger = get_logger(__name__)

_AI_SVG_DIR = os.path.join(get_resource_base(), "resources", "icons_svg", "ai")
_SEND_ICON = os.path.join(_AI_SVG_DIR, "send.svg")

_PANEL_STYLE = """
QFrame#aiAssistPanel {
    background-color: #0b1020;
    border-left: 1px solid #1a2440;
}
QLabel#aiPanelTitle {
    color: #d7e3ff;
    font-size: 13px;
    font-weight: 700;
    background: transparent;
}
QPlainTextEdit#aiInput {
    background-color: #11182c;
    color: #e6eeff;
    border: 1px solid #243152;
    border-radius: 8px;
    padding: 6px 8px;
    font-size: 12px;
}
QPushButton#aiSendBtn, QPushButton#aiAnalyzeBtn, QPushButton#aiSettingsBtn {
    min-height: 22px;
    padding: 2px 10px;
    border: 1px solid #22376A;
    border-radius: 8px;
    background-color: #13254b;
    color: #dce7ff;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#aiSendBtn:hover, QPushButton#aiAnalyzeBtn:hover, QPushButton#aiSettingsBtn:hover {
    background-color: #1C2D55;
    border: 1px solid #3A5A9F;
}
QPushButton#aiSendBtn:disabled, QPushButton#aiAnalyzeBtn:disabled {
    background-color: #0b1430;
    color: #5c7096;
    border: 1px solid #1a2850;
}
"""


class _InputEdit(QPlainTextEdit):
    """Enter 发送，Shift+Enter 换行。"""

    submitted = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
            event.modifiers() & Qt.ShiftModifier
        ):
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class AIAssistPanel(QFrame):
    request_close = Signal()

    def __init__(self, service: AIService, parent=None):
        super().__init__(parent)
        self._service = service
        self.setObjectName("aiAssistPanel")
        self.setStyleSheet(_PANEL_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addLayout(self._build_header())

        self._chat = ChatView()
        root.addWidget(self._chat, 1)

        self._input = _InputEdit()
        self._input.setObjectName("aiInput")
        self._input.setPlaceholderText("输入问题，Enter 发送 / Shift+Enter 换行")
        self._input.setFixedHeight(72)
        self._input.submitted.connect(self._on_send_clicked)
        root.addWidget(self._input)

        root.addLayout(self._build_action_bar())

        self._chat.add_system_message("AI 助手已就绪。")
        self._wire_service()

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("AI 助手")
        title.setObjectName("aiPanelTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self._settings_btn = QPushButton("设置")
        self._settings_btn.setObjectName("aiSettingsBtn")
        self._settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("aiSettingsBtn")
        close_btn.setFixedWidth(28)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setToolTip("关闭面板")
        close_btn.clicked.connect(self.request_close.emit)
        layout.addWidget(close_btn)
        return layout

    def _build_action_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._analyze_btn = QPushButton("分析日志")
        self._analyze_btn.setObjectName("aiAnalyzeBtn")
        self._analyze_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._analyze_btn.setToolTip("基于最近运行日志进行分析")
        self._analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._analyze_btn)

        layout.addStretch(1)

        self._send_btn = QPushButton("发送")
        self._send_btn.setObjectName("aiSendBtn")
        self._send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        if os.path.isfile(_SEND_ICON):
            self._send_btn.setIcon(tinted_svg_icon(_SEND_ICON, "#dce7ff", 14))
            self._send_btn.setIconSize(QSize(14, 14))
        self._send_btn.clicked.connect(self._on_send_clicked)
        layout.addWidget(self._send_btn)
        return layout

    def _wire_service(self) -> None:
        self._service.response_ready.connect(self._on_response)
        self._service.error_occurred.connect(self._on_error)
        self._service.busy_changed.connect(self._on_busy_changed)
        self._service.connection_tested.connect(self._on_connection_tested)

    def _on_send_clicked(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._chat.add_user_message(text)
        self._input.clear()
        self._service.send(text)

    def _on_analyze_clicked(self) -> None:
        self._chat.add_user_message("分析最近运行日志")
        self._service.analyze_recent_logs()

    def _on_response(self, content: str) -> None:
        self._chat.add_ai_message(content)

    def _on_error(self, message: str) -> None:
        self._chat.add_system_message(f"错误：{message}")

    def _on_busy_changed(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        self._analyze_btn.setEnabled(not busy)
        self._send_btn.setText("处理中…" if busy else "发送")

    def _on_connection_tested(self, ok: bool, message: str) -> None:
        if ok:
            self._chat.add_system_message(f"测试连接：{message}")
        else:
            self._chat.add_system_message(f"测试连接失败：{message}")

    def _open_settings(self) -> None:
        from ui.ai.ai_settings_dialog import AISettingsDialog

        dialog = AISettingsDialog(self._service, parent=self)
        dialog.exec()
