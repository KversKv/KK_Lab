"""ActionConfirmDialog：AI 受控动作执行前确认（AI_Assist.md §10 / §13）。

high / critical 动作执行前弹此对话框，展示动作名 / 风险等级 / 参数 / 风险提示，
用户显式确认后才执行。遵守约定：parent 必传；OK/Cancel default/autoDefault 二元化。

返回：dialog.exec() == QDialog.Accepted 表示用户确认。
"""
from __future__ import annotations

import json
from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from log_config import get_logger

logger = get_logger(__name__)

_DIALOG_STYLE = """
QDialog { background-color: #0e1525; }
QLabel { color: #c8d4ee; font-size: 12px; background: transparent; }
QPlainTextEdit {
    background-color: #11182c; color: #e6eeff;
    border: 1px solid #243152; border-radius: 6px; padding: 6px 8px;
    font-family: Consolas, "Courier New", monospace; font-size: 12px;
}
QPushButton {
    min-height: 22px; padding: 4px 16px;
    border: 1px solid #22376A; border-radius: 8px;
    background-color: #13254b; color: #dce7ff; font-weight: 600; font-size: 12px;
}
QPushButton:hover { background-color: #1C2D55; border: 1px solid #3A5A9F; }
QPushButton#aiOkBtn { background-color: #b3422f; border: 1px solid #d4503a; color: #ffffff; }
QLabel#aiRisk { font-weight: 700; }
QLabel#aiHint { font-size: 11px; color: #ffb27a; }
"""

_RISK_LABEL = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "critical": "危险（critical）",
}
_RISK_COLOR = {
    "low": "#8fd19e",
    "medium": "#f0c674",
    "high": "#ff9b6a",
    "critical": "#ff6a6a",
}


class ActionConfirmDialog(QDialog):
    def __init__(
        self,
        action_name: str,
        description: str,
        risk_level: str,
        arguments: dict[str, Any] | None = None,
        reason: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("AI 动作确认")
        self.setMinimumSize(460, 380)
        self.setStyleSheet(_DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        head = QLabel(f"AI 请求执行动作：{action_name}")
        head.setWordWrap(True)
        root.addWidget(head)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            root.addWidget(desc)

        risk = QLabel(f"风险等级：{_RISK_LABEL.get(risk_level, risk_level)}")
        risk.setObjectName("aiRisk")
        risk.setStyleSheet(f"color: {_RISK_COLOR.get(risk_level, '#c8d4ee')};")
        root.addWidget(risk)

        if reason:
            hint = QLabel(reason)
            hint.setObjectName("aiHint")
            hint.setWordWrap(True)
            root.addWidget(hint)

        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(self._pretty(arguments or {}))
        root.addWidget(editor, 1)

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
        cancel.setAutoDefault(True)
        cancel.setDefault(True)
        cancel.clicked.connect(self.reject)
        bar.addWidget(cancel)

        ok = QPushButton("确认执行")
        ok.setObjectName("aiOkBtn")
        ok.setAutoDefault(False)
        ok.setDefault(False)
        ok.clicked.connect(self.accept)
        bar.addWidget(ok)
        return bar
