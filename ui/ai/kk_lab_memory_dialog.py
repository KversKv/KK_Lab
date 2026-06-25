"""KK Lab AI 记忆归档草稿微调对话框（AIAssist_KKLabAIMemoryArchivePlan.md Phase 2 + Phase 3）。

把 KKLabMemoryCurator 生成的草稿以可编辑表单呈现，用户微调后写入。
支持选择写入目标（本机私有层 / 项目级 docs）。

Phase 3：KKLabMemoryManagerDialog 提供记忆管理入口（查看/删除/提升/转快捷指令/导出eval）。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QComboBox,
    QVBoxLayout,
    QMessageBox,
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


_KIND_LABELS: dict[str, str] = {
    kk_lab_memory.KIND_MEMORY: "长期记忆",
    kk_lab_memory.KIND_LESSONS: "经验/排障",
    kk_lab_memory.KIND_TEST_ITEMS: "测试项",
    kk_lab_memory.KIND_TEST_CASES: "测试用例",
    kk_lab_memory.KIND_QUICK_ACTIONS: "快捷指令",
}


class KKLabMemoryManagerDialog(QDialog):
    """KK Lab AI 记忆管理入口：查看 / 删除 / 提升 / 转快捷指令 / 导出 eval。

    Phase 3：列出当前页面 + _shared 的全部条目，右键或按钮触发管理操作。
    """

    def __init__(self, page_key: str, parent=None):
        super().__init__(parent)
        self._page_key = page_key or ""
        self.setWindowTitle("KK Lab AI 记忆管理")
        self.setMinimumSize(640, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        info = QLabel(
            f"页面：{self._page_key}    "
            f"项目级 docs + 本机私有层合并展示，来源层见条目标签"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        filter_layout = QFormLayout()
        self._kind_filter = QComboBox()
        self._kind_filter.addItem("全部 5 类", "")
        for kind in kk_lab_memory.KINDS:
            self._kind_filter.addItem(_KIND_LABELS.get(kind, kind), kind)
        self._kind_filter.currentIndexChanged.connect(self._refresh_list)
        filter_layout.addRow("类型筛选", self._kind_filter)
        layout.addLayout(filter_layout)

        self._list = QListWidget()
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemSelectionChanged.connect(self._update_button_state)
        layout.addWidget(self._list, 1)

        btn_row = QVBoxLayout()
        self._btn_delete = QPushButton("删除选中条目")
        self._btn_promote = QPushButton("提升本机条目到项目级")
        self._btn_to_qa = QPushButton("从测试项生成快捷指令")
        self._btn_to_eval = QPushButton("导出测试用例为 eval 草稿")
        self._btn_refresh = QPushButton("刷新")
        for btn in (
            self._btn_delete,
            self._btn_promote,
            self._btn_to_qa,
            self._btn_to_eval,
            self._btn_refresh,
        ):
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn_row.addWidget(btn)
        self._btn_delete.clicked.connect(self._delete_selected)
        self._btn_promote.clicked.connect(self._promote_selected)
        self._btn_to_qa.clicked.connect(self._test_item_to_quick_action)
        self._btn_to_eval.clicked.connect(self._test_case_to_eval)
        self._btn_refresh.clicked.connect(self._refresh_list)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        close_btn = buttons.button(QDialogButtonBox.Close)
        close_btn.setAutoDefault(False)
        close_btn.setDefault(False)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._refresh_list()

    def _current_kind_filter(self) -> str:
        data = self._kind_filter.currentData()
        return str(data or "")

    def _refresh_list(self) -> None:
        self._list.clear()
        kind = self._current_kind_filter() or None
        entries = kk_lab_memory.build_index(
            self._page_key or None, kind, include_shared=True
        )
        for ent in entries:
            tags_text = " ".join(ent.get("tags", []))
            target_label = "本机" if ent.get("target") == kk_lab_memory.TARGET_LOCAL else "项目"
            label = (
                f"[{ent.get('kind', '')}] [{target_label}] "
                f"{ent.get('entry_id', '')} - {ent.get('title', '')}"
            )
            if tags_text:
                label += f"  ({tags_text})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, ent)
            self._list.addItem(item)
        self._update_button_state()

    def _selected_entry(self) -> dict | None:
        items = self._list.selectedItems()
        if not items:
            return None
        return items[0].data(Qt.UserRole)

    def _update_button_state(self) -> None:
        ent = self._selected_entry()
        has_sel = ent is not None
        self._btn_delete.setEnabled(has_sel)
        self._btn_promote.setEnabled(
            has_sel and ent.get("target") == kk_lab_memory.TARGET_LOCAL
        )
        self._btn_to_qa.setEnabled(
            has_sel and ent.get("kind") == kk_lab_memory.KIND_TEST_ITEMS
        )
        self._btn_to_eval.setEnabled(
            has_sel and ent.get("kind") == kk_lab_memory.KIND_TEST_CASES
        )

    def _show_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        ent = item.data(Qt.UserRole)
        if not ent:
            return
        menu = QMenu(self)
        menu.addAction("删除", lambda: self._delete_entry(ent))
        if ent.get("target") == kk_lab_memory.TARGET_LOCAL:
            menu.addAction("提升到项目级", lambda: self._promote_entry(ent))
        if ent.get("kind") == kk_lab_memory.KIND_TEST_ITEMS:
            menu.addAction("生成快捷指令", lambda: self._convert_test_item(ent))
        if ent.get("kind") == kk_lab_memory.KIND_TEST_CASES:
            menu.addAction("导出 eval 草稿", lambda: self._export_test_case(ent))
        menu.exec(self._list.mapToGlobal(pos))

    def _delete_selected(self) -> None:
        ent = self._selected_entry()
        if ent:
            self._delete_entry(ent)

    def _promote_selected(self) -> None:
        ent = self._selected_entry()
        if ent:
            self._promote_entry(ent)

    def _test_item_to_quick_action(self) -> None:
        ent = self._selected_entry()
        if ent:
            self._convert_test_item(ent)

    def _test_case_to_eval(self) -> None:
        ent = self._selected_entry()
        if ent:
            self._export_test_case(ent)

    def _delete_entry(self, ent: dict) -> None:
        entry_id = ent.get("entry_id", "")
        kind = ent.get("kind", "")
        target = ent.get("target", kk_lab_memory.TARGET_LOCAL)
        target_label = "项目级 docs" if target == kk_lab_memory.TARGET_PROJECT else "本机私有层"
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定从{target_label}删除条目？\n{entry_id} - {ent.get('title', '')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        ok, message = kk_lab_memory.delete_entry(
            self._page_key, kind, entry_id, target=target
        )
        if ok:
            self._refresh_list()
        else:
            QMessageBox.warning(self, "删除失败", message)

    def _promote_entry(self, ent: dict) -> None:
        entry_id = ent.get("entry_id", "")
        kind = ent.get("kind", "")
        reply = QMessageBox.question(
            self,
            "确认提升",
            f"把本机条目提升到项目级 docs？\n{entry_id} - {ent.get('title', '')}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        ok, message = kk_lab_memory.promote_local_to_project(
            self._page_key, kind, entry_id
        )
        if ok:
            self._refresh_list()
        else:
            QMessageBox.warning(self, "提升失败", message)

    def _convert_test_item(self, ent: dict) -> None:
        entry_id = ent.get("entry_id", "")
        entries = kk_lab_memory.read_entries(
            self._page_key, kk_lab_memory.KIND_TEST_ITEMS
        )
        source = next((e for e in entries if e.entry_id == entry_id), None)
        if source is None:
            QMessageBox.warning(self, "转换失败", f"未找到测试项 {entry_id}")
            return
        draft = kk_lab_memory.test_item_to_quick_action_draft(source, self._page_key)
        dialog = KKLabMemoryDialog(draft, parent=self)
        if not dialog.exec():
            return
        final_draft = dialog.result_draft()
        entry_text = kk_lab_memory.render_draft_entry(final_draft)
        target = final_draft.get("target", kk_lab_memory.TARGET_LOCAL)
        title = final_draft.get("title", "")
        existing = kk_lab_memory.read_entries(
            self._page_key, kk_lab_memory.KIND_QUICK_ACTIONS
        )
        dup = kk_lab_memory.find_duplicate(existing, title)
        if dup is not None:
            entry_text = kk_lab_memory.render_entry(
                kk_lab_memory.KIND_QUICK_ACTIONS,
                dup.entry_id,
                title,
                final_draft.get("fields", []),
            )
        ok, message = kk_lab_memory.append_entry(
            self._page_key,
            kk_lab_memory.KIND_QUICK_ACTIONS,
            entry_text,
            target=target,
        )
        if ok:
            self._refresh_list()
        else:
            QMessageBox.warning(self, "写入失败", message)

    def _export_test_case(self, ent: dict) -> None:
        entry_id = ent.get("entry_id", "")
        entries = kk_lab_memory.read_entries(
            self._page_key, kk_lab_memory.KIND_TEST_CASES
        )
        source = next((e for e in entries if e.entry_id == entry_id), None)
        if source is None:
            QMessageBox.warning(self, "导出失败", f"未找到测试用例 {entry_id}")
            return
        draft = kk_lab_memory.test_case_to_eval_draft(source, self._page_key)
        if draft is None:
            QMessageBox.information(
                self,
                "不适用",
                f"用例 {entry_id} 可自动化程度不是 full/partial，不导出。",
            )
            return
        ok, path_or_msg = kk_lab_memory.write_eval_draft(draft)
        if ok:
            QMessageBox.information(
                self, "导出成功", f"已导出 eval 草稿：\n{path_or_msg}"
            )
        else:
            QMessageBox.warning(self, "导出失败", path_or_msg)
