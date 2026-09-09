"""SavedResultsDialog — 导出已保存结果：勾选若干已保存测试项聚合导出报告。

数据源为 ``core.module_test.saved_results.list_saved_results`` 扫描到的条目
（同一「芯片 + 模块」下每项只维护一套，覆盖保存；由调用方按当前 DUT 配置
过滤后传入）。OK 后由调用方取 ``selected_dirs()`` 交给
``SavedResultsExportWorker`` 聚合导出。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout,
)

from ui.theme import apply_qss

_COL_NAME = 0
_COL_VERDICT = 1
_COL_CHIP = 2
_COL_MODULE = 3
_COL_SAVED_AT = 4


class SavedResultsDialog(QDialog):
    """已保存测试结果选择弹窗（复选，默认全勾）。"""

    def __init__(self, module_type: str, entries: list[dict],
                 registry_order: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"导出已保存结果 — {module_type.upper()}")
        self.setMinimumSize(640, 420)
        apply_qss(self, "dialog")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addWidget(QLabel(
            "勾选要聚合进报告的测试结果（已按当前芯片/模块加载，覆盖保存每项"
            "仅一套），确认后导出到 final 目录："))

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["测试项", "判定", "芯片", "模块", "保存时间"])
        self.tree.setColumnWidth(_COL_NAME, 220)
        self.tree.setColumnWidth(_COL_VERDICT, 60)
        self.tree.setColumnWidth(_COL_CHIP, 100)
        self.tree.setColumnWidth(_COL_MODULE, 100)
        self.tree.setRootIsDecorated(False)
        layout.addWidget(self.tree, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.select_all_btn = QPushButton("全选")
        self.select_none_btn = QPushButton("全不选")
        self.select_all_btn.clicked.connect(lambda: self._set_all(Qt.Checked))
        self.select_none_btn.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.select_none_btn)
        btn_row.addStretch()
        self.export_btn = QPushButton("导出")
        self.export_btn.setDefault(True)
        self.export_btn.setAutoDefault(True)
        self.export_btn.setMinimumWidth(88)
        self.export_btn.clicked.connect(self._on_export)
        cancel_btn = QPushButton("取消")
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setMinimumWidth(88)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.export_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self._populate(entries, registry_order or [])

    # ------------------------------------------------------------------ data
    def _populate(self, entries: list[dict], registry_order: list[str]) -> None:
        order = {k: i for i, k in enumerate(registry_order)}
        rows = sorted(
            entries,
            key=lambda e: (order.get(e["item_key"], len(order)), e["item_key"]))
        for e in rows:
            node = QTreeWidgetItem([e["name"], e["verdict"], e["chip_name"],
                                    e["module_name"], e["saved_at"]])
            node.setData(_COL_NAME, Qt.UserRole, e["dir"])
            node.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            node.setCheckState(_COL_NAME, Qt.Checked)
            node.setToolTip(_COL_NAME, e["dir"])
            self.tree.addTopLevelItem(node)
        self.export_btn.setEnabled(bool(rows))

    def _set_all(self, state: Qt.CheckState) -> None:
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(_COL_NAME, state)

    def _on_export(self) -> None:
        if self.selected_dirs():
            self.accept()

    def selected_dirs(self) -> list[str]:
        """勾选项的条目目录（按列表顺序 = 注册表顺序）。"""
        out: list[str] = []
        for i in range(self.tree.topLevelItemCount()):
            node = self.tree.topLevelItem(i)
            if node.checkState(_COL_NAME) == Qt.Checked:
                path = node.data(_COL_NAME, Qt.UserRole)
                if path:
                    out.append(path)
        return out
