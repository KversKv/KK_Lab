"""沉淀草稿微调对话框（AI_Assistant_MD §2.7.1）。

把 Curator 生成的草稿（AI 或规则来源）以可编辑表单呈现，用户微调后写入。
字符串字段用单行/多行编辑框；非字符串字段（list/dict）以只读 JSON 展示并可整体编辑。
"""
from __future__ import annotations

import json

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from log_config import get_logger

from ui.ai.dialog_theme import apply_ai_dialog_theme

logger = get_logger(__name__)

_KIND_TITLES = {
    "nudge": "沉淀为纠偏片段",
    "quick_action": "沉淀为快捷指令",
    "project_rule": "沉淀为项目规则",
    "eval_case": "沉淀为 eval 用例",
}

_MULTILINE_KEYS = {"text", "user", "assistant", "desc"}


class CurateDialog(QDialog):
    """草稿微调：返回编辑后的 draft（保留 _src 等内部键）。"""

    def __init__(self, kind: str, draft: dict, parent=None):
        super().__init__(parent)
        self._kind = kind
        self._draft = dict(draft or {})
        self._editors: dict[str, object] = {}

        self.setWindowTitle(_KIND_TITLES.get(kind, "沉淀草稿"))
        self.setMinimumWidth(460)
        apply_ai_dialog_theme(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        src = self._draft.get("_src", "")
        tip = QLabel(f"来源：{src}" if src else "请确认/微调草稿后写入。")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        form = QFormLayout()
        form.setSpacing(8)
        for key, value in self._draft.items():
            if key.startswith("_"):
                continue
            if isinstance(value, str) and key in _MULTILINE_KEYS:
                editor = QPlainTextEdit()
                editor.setPlainText(value)
                editor.setFixedHeight(80)
            elif isinstance(value, str):
                editor = QLineEdit(value)
            else:
                editor = QPlainTextEdit()
                editor.setPlainText(
                    json.dumps(value, ensure_ascii=False, indent=2)
                )
                editor.setFixedHeight(100)
            self._editors[key] = editor
            form.addRow(key, editor)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self
        )
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        ok_btn.setText("写入")
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_draft(self) -> dict:
        """收集编辑后的字段，原样保留 _src 等内部键。"""
        result = dict(self._draft)
        for key, editor in self._editors.items():
            original = self._draft.get(key)
            if isinstance(editor, QLineEdit):
                result[key] = editor.text().strip()
            elif isinstance(editor, QPlainTextEdit):
                text = editor.toPlainText()
                if isinstance(original, str):
                    result[key] = text.strip()
                else:
                    try:
                        result[key] = json.loads(text)
                    except json.JSONDecodeError:
                        logger.warning("字段 %s JSON 解析失败，保留原值", key)
                        result[key] = original
        return result
