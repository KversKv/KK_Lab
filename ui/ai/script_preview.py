"""ScriptPreviewDialog：测试脚本（Custom Test 序列）草案预览 + 校验 + 应用。

AI_Assist.md §12，阶段 3 任务 3.3 + 3.4；F5.4 序列 before/after diff：
  - 预览 ScriptDraft 序列（JSON pretty）；
  - 当提供当前画布序列（before_sequence v2 dict）时，展示 before/after 文本 diff；
  - 本地校验：core/ai/draft_validation.validate_script_draft
    （= load_sequence_data 反序列化 + preflight_validate）；
  - error 阻止 apply、warning 可确认继续；
  - 用户确认 → 回调 apply（custom_test → canvas.load_from_nodes）。

遵守约定：parent 必传；OK/Cancel 按钮 default/autoDefault 显式二元化。
apply 回调入参为已反序列化的 nodes（list[BaseNode]），便于直接接 canvas.load_from_nodes。
"""
from __future__ import annotations

import difflib
import json
from typing import Any, Callable

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from core.ai.draft_validation import DraftValidationResult, validate_script_draft
from core.ai.schemas import ScriptDraft
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
QPushButton#aiOkBtn { background-color: #5b3df5; border: 1px solid #6548ff; color: #ffffff; }
QPushButton#aiOkBtn:disabled { background-color: #2a2f48; border: 1px solid #2a2f48; color: #7d86a3; }
QLabel#aiIssues { font-size: 11px; }
QTabWidget::pane { border: 1px solid #243152; border-radius: 6px; }
QTabBar::tab {
    background: #11182c; color: #9fb0d6; padding: 4px 14px;
    border: 1px solid #243152; border-bottom: none;
    border-top-left-radius: 6px; border-top-right-radius: 6px;
}
QTabBar::tab:selected { background: #1a2540; color: #e6eeff; }
QTextEdit {
    background-color: #11182c; color: #e6eeff;
    border: 1px solid #243152; border-radius: 6px; padding: 6px 8px;
    font-family: Consolas, "Courier New", monospace; font-size: 12px;
}
"""

ApplyCallback = Callable[[list[Any]], tuple[bool, str]]


class ScriptPreviewDialog(QDialog):
    def __init__(
        self,
        draft: ScriptDraft,
        apply_cb: ApplyCallback,
        parent=None,
        before_sequence: dict[str, Any] | None = None,
    ):
        super().__init__(parent)
        self._draft = draft
        self._apply_cb = apply_cb
        self._before_sequence = before_sequence
        self._result: DraftValidationResult | None = None
        self._confirmed_warnings = False
        self.setWindowTitle("测试脚本草案 - 预览与校验")
        self.setMinimumSize(560, 540)
        self.setStyleSheet(_DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = draft.title or "（未命名脚本草案）"
        head = QLabel(f"标题：{title}　节点数：{len(draft.sequence)}")
        head.setWordWrap(True)
        root.addWidget(head)

        if draft.notes:
            notes = QLabel(draft.notes)
            notes.setObjectName("aiIssues")
            notes.setWordWrap(True)
            root.addWidget(notes)

        root.addWidget(self._build_body(), 1)

        self._issues = QLabel("")
        self._issues.setObjectName("aiIssues")
        self._issues.setWordWrap(True)
        root.addWidget(self._issues)

        root.addLayout(self._build_button_bar())

        self._run_validation()

    def _build_body(self):
        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(True)
        self._editor.setPlainText(self._pretty(self._draft.sequence))

        if not self._before_sequence:
            return self._editor

        tabs = QTabWidget()
        tabs.addTab(self._editor, "草案 JSON")

        diff_view = QTextEdit()
        diff_view.setReadOnly(True)
        diff_view.setHtml(self._build_diff_html())
        tabs.addTab(diff_view, "对比当前画布 (diff)")
        tabs.setCurrentIndex(1)
        return tabs

    def _build_diff_html(self) -> str:
        before = self._summarize(self._before_sequence.get("sequence", []))
        after = self._summarize(self._draft.sequence)
        diff = difflib.unified_diff(
            before, after, fromfile="当前画布", tofile="AI 草案", lineterm=""
        )
        rows: list[str] = []
        for line in diff:
            safe = (
                line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            )
            if line.startswith("+") and not line.startswith("+++"):
                rows.append(f'<span style="color:#7ee0a0;">{safe}</span>')
            elif line.startswith("-") and not line.startswith("---"):
                rows.append(f'<span style="color:#ff8a8a;">{safe}</span>')
            elif line.startswith("@@"):
                rows.append(f'<span style="color:#7aa2f7;">{safe}</span>')
            else:
                rows.append(f'<span style="color:#9fb0d6;">{safe}</span>')
        if not rows:
            rows.append('<span style="color:#9fb0d6;">（与当前画布序列一致，无差异）</span>')
        return "<pre style='margin:0;'>" + "\n".join(rows) + "</pre>"

    @staticmethod
    def _summarize(nodes, depth: int = 0) -> list[str]:
        lines: list[str] = []
        indent = "  " * depth
        if not isinstance(nodes, list):
            return lines
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                continue
            node_type = str(node.get("node_type", "?"))
            params = node.get("params") or {}
            param_text = ""
            if isinstance(params, dict) and params:
                pairs = ", ".join(f"{k}={v}" for k, v in sorted(params.items()))
                param_text = f" ({pairs})"
            lines.append(f"{indent}[{index}] {node_type}{param_text}")
            children = node.get("children") or []
            if isinstance(children, list) and children:
                lines.extend(ScriptPreviewDialog._summarize(children, depth + 1))
        return lines

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

        self._ok = QPushButton("应用到画布")
        self._ok.setObjectName("aiOkBtn")
        self._ok.setAutoDefault(True)
        self._ok.setDefault(True)
        self._ok.clicked.connect(self._on_apply)
        bar.addWidget(self._ok)
        return bar

    def _run_validation(self) -> None:
        result = validate_script_draft(self._draft)
        self._result = result
        lines: list[str] = []
        for err in result.errors:
            lines.append(f"✗ [error] {err}")
        for warn in result.warnings:
            lines.append(f"! [warning] {warn}")

        if result.has_errors:
            self._issues.setStyleSheet("color: #ff8a8a;")
            self._ok.setEnabled(False)
            lines.append("存在 error，无法应用，请修正草案后重试。")
        elif result.warnings:
            self._issues.setStyleSheet("color: #ffce6a;")
            self._ok.setEnabled(True)
            self._ok.setText("仍要应用")
            lines.append("存在 warning，确认后可继续应用。")
        else:
            self._issues.setStyleSheet("color: #7ee0a0;")
            self._ok.setEnabled(True)
            lines.append("✓ 校验通过，可应用。")

        self._issues.setText("\n".join(lines))

    def _on_apply(self) -> None:
        result = self._result
        if result is None or result.has_errors:
            return
        if result.warnings and not self._confirmed_warnings:
            self._confirmed_warnings = True
            self._issues.setText(self._issues.text() + "\n再次点击确认应用。")
            return
        try:
            ok, message = self._apply_cb(result.nodes)
        except Exception as exc:  # noqa: BLE001 - apply 回调异常统一兜底提示
            logger.warning("应用脚本草案失败", exc_info=True)
            self._issues.setStyleSheet("color: #ff8a8a;")
            self._issues.setText(f"✗ 应用失败：{exc}")
            return
        if ok:
            self.accept()
        else:
            self._issues.setStyleSheet("color: #ff8a8a;")
            self._issues.setText(f"✗ {message or '应用被拒绝'}")
