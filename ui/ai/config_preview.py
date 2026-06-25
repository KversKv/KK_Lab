"""ConfigPreviewDialog：测试配置草案预览 + 应用（AIAssist_Architecture.md §12，阶段 3 任务 3.2）。

流程：AI 生成 ConfigDraft 草案 → 本对话框预览（JSON pretty）→ 用户确认 → 回调 apply。
草案的"具体校验"交给目标页面自身的 import/校验逻辑（任务 3.5）：
  - apply 回调返回 (ok, message)；ok=False 时阻止关闭并提示。

遵守约定：parent 必传；OK/Cancel 按钮 default/autoDefault 显式二元化；数值不涉及单位。
"""
from __future__ import annotations

import json
from typing import Callable

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from core.ai.schemas import ConfigDraft
from log_config import get_logger

logger = get_logger(__name__)

_DIALOG_STYLE = """
QDialog { background-color: #070709; }
QLabel { color: #cbd5e1; font-size: 12px; background: transparent; }
QPlainTextEdit {
    background-color: #070709; color: #cbd5e1;
    border: 1px solid #1e293b; border-radius: 12px; padding: 8px 10px;
    font-family: Consolas, "Courier New", monospace; font-size: 11px;
}
QPlainTextEdit:focus { border: 1px solid #3b82f6; }
QPushButton {
    min-height: 28px; padding: 4px 16px;
    border: 1px solid #1e293b; border-radius: 6px;
    background-color: #0f172a; color: #cbd5e1; font-weight: 600; font-size: 12px;
}
QPushButton:hover { background-color: #1e293b; border: 1px solid #334155; }
QPushButton#aiOkBtn { background-color: #5b3df5; border: 1px solid #5b3df5; color: #ffffff; }
QPushButton#aiOkBtn:disabled { background-color: #0f172a; border: 1px solid #1e293b; color: #64748b; }
QLabel#aiHint { color: #94a3b8; font-size: 11px; }
"""

ApplyCallback = Callable[[ConfigDraft], tuple[bool, str]]


class ConfigPreviewDialog(QDialog):
    def __init__(self, draft: ConfigDraft, apply_cb: ApplyCallback, parent=None):
        super().__init__(parent)
        self._draft = draft
        self._apply_cb = apply_cb
        self.setWindowTitle("测试配置草案 - 预览")
        self.setMinimumSize(520, 480)
        self.setStyleSheet(_DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = draft.title or "（未命名配置草案）"
        target = draft.target_page or "（当前页面）"
        head = QLabel(f"目标页面：{target}　标题：{title}")
        head.setWordWrap(True)
        root.addWidget(head)

        if draft.notes:
            notes = QLabel(draft.notes)
            notes.setObjectName("aiHint")
            notes.setWordWrap(True)
            root.addWidget(notes)

        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(True)
        self._editor.setPlainText(self._pretty(draft.payload))
        root.addWidget(self._editor, 1)

        self._hint = QLabel("")
        self._hint.setObjectName("aiHint")
        self._hint.setWordWrap(True)
        root.addWidget(self._hint)

        root.addLayout(self._build_button_bar())

    @staticmethod
    def _pretty(payload) -> str:
        try:
            return json.dumps(payload, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return str(payload)

    def _build_button_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addStretch(1)

        cancel = QPushButton("取消")
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        cancel.clicked.connect(self.reject)
        bar.addWidget(cancel)

        self._ok = QPushButton("应用配置")
        self._ok.setObjectName("aiOkBtn")
        self._ok.setAutoDefault(True)
        self._ok.setDefault(True)
        self._ok.clicked.connect(self._on_apply)
        bar.addWidget(self._ok)
        return bar

    def _on_apply(self) -> None:
        try:
            ok, message = self._apply_cb(self._draft)
        except Exception as exc:  # noqa: BLE001 - apply 回调异常统一兜底提示
            logger.warning("应用配置草案失败", exc_info=True)
            self._hint.setText(f"✗ 应用失败：{exc}")
            self._hint.setStyleSheet("color: #ff8a8a;")
            return
        if ok:
            self.accept()
        else:
            self._hint.setText(f"✗ {message or '目标页面拒绝了该配置'}")
            self._hint.setStyleSheet("color: #ff8a8a;")
