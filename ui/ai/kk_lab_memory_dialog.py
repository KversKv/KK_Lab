"""KK Lab AI 记忆归档草稿微调对话框（AIAssist_KKLabAIMemoryArchivePlan.md Phase 2）。

把 KKLabMemoryCurator 生成的草稿以可编辑表单呈现，用户微调后写入。
支持选择写入目标（本机私有层 / 项目级 docs）。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from core.ai import kk_lab_memory
from log_config import get_logger

logger = get_logger(__name__)

_KIND_TITLES = {
    kk_lab_memory.KIND_DRAFT_MEMORY: "归档为本页长期记忆",
    kk_lab_memory.KIND_DRAFT_LESSON: "归档为本页经验",
    kk_lab_memory.KIND_DRAFT_TEST_ITEM: "归档为本页测试项",
    kk_lab_memory.KIND_DRAFT_TEST_CASE: "归档为本页测试用例",
    kk_lab_memory.KIND_DRAFT_QUICK_ACTION: "归档为本页快捷指令",
}

_MULTILINE_KEYS = {
    "内容", "适用条件", "现象", "原因", "处理办法", "验证方式",
    "前置条件", "参数", "步骤", "期望结果", "数据记录", "适用范围",
    "输入", "执行步骤", "期望行为", "通过标准", "失败排查",
    "占位符", "执行预期", "摘要",
}


class KKLabMemoryDialog(QDialog):
    """草稿微调：返回编辑后的 draft（含 fields / target）。"""

    def __init__(self, draft: dict, parent=None):
        super().__init__(parent)
        self._draft = dict(draft or {})
        self._editors: dict[str, object] = {}

        draft_kind = self._draft.get("draft_kind", "")
        title = _KIND_TITLES.get(draft_kind, "归档到本页记忆")
        self.setWindowTitle(title)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        info = QLabel(
            f"页面：{self._draft.get('page_key', '')}    "
            f"类型：{kk_lab_memory.draft_kind_label(draft_kind)}    "
            f"ID：{self._draft.get('entry_id', '')}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        src = self._draft.get("_src", "")
        if src:
            tip = QLabel(f"来源：{src}")
            tip.setStyleSheet("color: #7b88a8; font-size: 12px;")
            tip.setWordWrap(True)
            layout.addWidget(tip)

        form = QFormLayout()
        form.setSpacing(8)

        title_editor = QLineEdit(self._draft.get("title", ""))
        self._editors["__title__"] = title_editor
        form.addRow("标题", title_editor)

        for label, value in self._draft.get("fields", []):
            if label in ("页面",):
                continue
            if label in _MULTILINE_KEYS:
                editor = QPlainTextEdit()
                editor.setPlainText(value)
                editor.setFixedHeight(80)
            else:
                editor = QLineEdit(value)
            self._editors[label] = editor
            form.addRow(label, editor)
        layout.addLayout(form)

        self._project_check = QCheckBox("写入项目级 docs（需二次确认，纳入版本控制）")
        self._project_check.setChecked(False)
        layout.addWidget(self._project_check)

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
        """收集编辑后的字段，返回新 draft（保留 entry_id / file_kind / _src 等）。"""
        result = dict(self._draft)
        title_editor = self._editors.get("__title__")
        if isinstance(title_editor, QLineEdit):
            result["title"] = title_editor.text().strip()

        new_fields: list[tuple[str, str]] = []
        page_key = self._draft.get("page_key", "")
        if page_key:
            new_fields.append(("页面", page_key))
        for label, _ in self._draft.get("fields", []):
            if label == "页面":
                continue
            editor = self._editors.get(label)
            if isinstance(editor, QLineEdit):
                new_fields.append((label, editor.text().strip()))
            elif isinstance(editor, QPlainTextEdit):
                new_fields.append((label, editor.toPlainText().strip()))
        result["fields"] = new_fields
        result["target"] = (
            kk_lab_memory.TARGET_PROJECT
            if self._project_check.isChecked()
            else kk_lab_memory.TARGET_LOCAL
        )
        return result
