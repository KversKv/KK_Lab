"""RecordDataPoint 节点的专属属性编辑器

功能：
1. 扫描序列中位于当前 RecordDataPoint 节点之前的所有节点，自动识别其产生的变量；
2. 在属性面板中为每个变量生成一行（勾选框 + 字段名 + 表达式），
   并与 node.params["fields"] 双向同步；
3. 支持用户添加自定义字段、刷新变量列表、回到原生文本编辑。
"""

from __future__ import annotations

import os as _os
import re
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QFrame, QPushButton, QScrollArea, QSizePolicy,
)

from ui.pages.custom_test.nodes.base_node import BaseNode

_CHECK_ICON = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))),
    "resources", "icons", "check.svg"
).replace("\\", "/")


_VAR_PAT = re.compile(r"^\$\{(\w+)\}$")


def _detect_variables_in_node(node: BaseNode) -> List[Tuple[str, str, bool]]:
    """返回该节点产生的变量列表：[(var_name, description, export_default)]。

    description 仅用于 UI 提示，export_default 代表变量是否计入导出池。
    """
    produced: List[Tuple[str, str, bool]] = []
    nt = node.node_type
    params = node.params
    export = bool(params.get("export_var", True))

    if nt in ("LoopRange", "LoopList", "LoopCount"):
        name = str(params.get("var_name", "")).strip()
        if name:
            produced.append((name, f"{nt} 循环变量", export))
        return produced

    if nt == "SetVariable":
        name = str(params.get("var_name", "")).strip()
        if name:
            produced.append((name, "Set Variable", export))
        return produced

    if nt == "MathExpression":
        name = str(params.get("result_var", "")).strip()
        if name:
            produced.append((name, "Math Expression", True))
        return produced

    if nt == "N6705CMeasure":
        name = str(params.get("result_var", "")).strip()
        ch = params.get("channel", 1)
        mtype = str(params.get("measure_type", "current"))
        if name:
            produced.append((name, f"N6705C CH{ch} {mtype}", export))
        return produced

    if nt == "ScopeMeasure":
        name = str(params.get("result_var", "")).strip()
        ch = params.get("channel", 1)
        mtype = str(params.get("measure_type", "pk2pk"))
        if name:
            produced.append((name, f"Scope CH{ch} {mtype}", export))
        return produced

    if nt == "ScopeMeasureFreq":
        name = str(params.get("result_var", "")).strip()
        ch = params.get("channel", 1)
        if name:
            produced.append((name, f"Scope CH{ch} freq", export))
        return produced

    if nt in (
        "N6705CGetMode", "N6705CGetChannelState",
        "ScopeMeasureDCV",
        "ChamberGetTemp", "ChamberGetSetTemp", "ChamberGetHumidity",
        "RFAnalyzerMeasure",
        "I2CRead", "UARTReceive",
    ):
        name = str(params.get("result_var", "")).strip()
        if name:
            produced.append((name, node.display_name, export))
        return produced

    return produced


def _walk_sequence(nodes: List[BaseNode], target_uid: str,
                   out: List[Tuple[str, str, bool]]) -> bool:
    """深度优先遍历：收集 target 之前（含外层循环）所有节点产生的变量。

    返回 True 表示已在子树中找到 target，停止继续收集。
    """
    for node in nodes:
        if node.uid == target_uid:
            return True
        out.extend(_detect_variables_in_node(node))
        if node.children:
            if _walk_sequence(node.children, target_uid, out):
                return True
    return False


def detect_available_variables(sequence: List[BaseNode],
                               target_uid: str) -> List[Tuple[str, str, bool]]:
    """扫描整棵序列，返回目标节点之前可用的变量（去重，保持出现顺序）。"""
    raw: List[Tuple[str, str, bool]] = []
    _walk_sequence(sequence, target_uid, raw)

    seen = set()
    dedup: List[Tuple[str, str, bool]] = []
    for name, desc, export in raw:
        if name in seen:
            continue
        seen.add(name)
        dedup.append((name, desc, export))
    return dedup


def _parse_fields_string(raw: str) -> List[Tuple[str, str]]:
    """把 "k1=${v1}, k2=${v2}" 解析成 [(k1, ${v1}), (k2, ${v2})]。"""
    raw = (raw or "").strip()
    if not raw or raw.lower() == "auto":
        return []
    if raw.startswith("{"):
        try:
            import json
            data = json.loads(raw)
            return [(str(k), str(v)) for k, v in data.items()]
        except Exception:
            return []
    pairs: List[Tuple[str, str]] = []
    for seg in raw.split(","):
        seg = seg.strip()
        if "=" not in seg:
            continue
        k, v = seg.split("=", 1)
        pairs.append((k.strip(), v.strip()))
    return pairs


def _compose_fields_string(rows: List[Tuple[bool, str, str]]) -> str:
    """把 UI 行 [(export, key, expr), ...] 合成回 fields 字符串。"""
    parts = [f"{k}={v}" for export, k, v in rows if export and k and v]
    return ", ".join(parts)


_ROW_CB_STYLE = (
    "QCheckBox { color: #8eb0e3; font-size: 11px; background: transparent; border: none; spacing: 2px; }"
    "QCheckBox::indicator { width: 14px; height: 14px;"
    "  border-style: solid; border-width: 1.5px; border-color: #3a5a9f;"
    "  border-radius: 3px; background: #061022; }"
    "QCheckBox::indicator:hover { border-color: #5b5cf6; background: #0d1a3a; }"
    "QCheckBox::indicator:checked { border-color: #5b5cf6; background: #5b5cf6;"
    "  image: url(" + _CHECK_ICON + "); }"
    "QCheckBox::indicator:checked:hover { background: #7070ff; border-color: #7070ff; }"
)

_ROW_LINE_STYLE = (
    "QLineEdit { background-color: #061022; border: 1px solid #1f315d;"
    "  border-radius: 5px; color: #dce7ff; font-size: 11px; padding: 3px 6px; }"
    "QLineEdit:focus { border: 1px solid #5b5cf6; }"
    "QLineEdit[placeholderText] { color: #4e6494; }"
)

_HINT_STYLE = (
    "QLabel { color: #5f78a8; font-size: 10px; background: transparent; border: none; }"
)

_SMALL_BTN_STYLE = (
    "QPushButton { background-color: #132040; color: #8eb0e3;"
    "  border: 1px solid #1a2d57; border-radius: 5px; padding: 4px 10px;"
    "  font-size: 11px; font-weight: 600; }"
    "QPushButton:hover { background-color: #1a2d57; color: #dce7ff; }"
    "QPushButton:pressed { background-color: #0c1733; }"
)


class _FieldRow(QWidget):
    """字段映射单行：[checkbox] [key]=[expr] [✕]"""

    changed = Signal()

    def __init__(self, export: bool, key: str, expr: str,
                 description: str = "",
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._description = description

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.cb = QCheckBox()
        self.cb.setChecked(bool(export))
        self.cb.setToolTip("勾选则该字段写入 fields 映射")
        self.cb.setStyleSheet(_ROW_CB_STYLE)
        self.cb.toggled.connect(lambda _=False: self.changed.emit())
        layout.addWidget(self.cb)

        self.key_edit = QLineEdit(key)
        self.key_edit.setPlaceholderText("字段名")
        self.key_edit.setStyleSheet(_ROW_LINE_STYLE)
        self.key_edit.setMinimumWidth(60)
        self.key_edit.editingFinished.connect(lambda: self.changed.emit())
        layout.addWidget(self.key_edit, 3)

        eq = QLabel("=")
        eq.setStyleSheet("QLabel { color: #5f78a8; background: transparent; border: none; }")
        layout.addWidget(eq)

        self.expr_edit = QLineEdit(expr)
        self.expr_edit.setPlaceholderText("${var} 或 表达式")
        self.expr_edit.setStyleSheet(_ROW_LINE_STYLE)
        self.expr_edit.setMinimumWidth(80)
        self.expr_edit.editingFinished.connect(lambda: self.changed.emit())
        layout.addWidget(self.expr_edit, 4)

    def data(self) -> Tuple[bool, str, str]:
        return (
            bool(self.cb.isChecked()),
            self.key_edit.text().strip(),
            self.expr_edit.text().strip(),
        )


class RecordDataPointEditor(QWidget):
    """RecordDataPoint 节点的专属属性编辑器。"""

    params_changed = Signal(str, object)  # (key, value)

    def __init__(self, node: BaseNode, sequence: List[BaseNode],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._node = node
        self._sequence = sequence
        self._rows: List[_FieldRow] = []
        self._suppress_sync = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        hint = QLabel(
            "勾选需要记录的字段，字段名与表达式都可直接编辑。\n"
            "下方原始字符串会与上方表格保持同步。"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(_HINT_STYLE)
        root.addWidget(hint)

        self._rows_container = QWidget()
        self._rows_container.setStyleSheet("background: transparent;")
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(4)
        root.addWidget(self._rows_container)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(6)

        add_btn = QPushButton("+ 添加字段")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(_SMALL_BTN_STYLE)
        add_btn.clicked.connect(self._on_add_custom)
        btn_row.addWidget(add_btn)

        refresh_btn = QPushButton("↻ 刷新变量")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(_SMALL_BTN_STYLE)
        refresh_btn.setToolTip("重新扫描该节点之前出现的变量并合并到列表")
        refresh_btn.clicked.connect(self._on_refresh)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        adv_label = QLabel("原始 fields 字符串")
        adv_label.setStyleSheet(_HINT_STYLE)
        root.addWidget(adv_label)

        self._raw_edit = QLineEdit()
        self._raw_edit.setStyleSheet(
            "QLineEdit { background-color: #061022; border: 1px solid #1f315d;"
            "  border-radius: 6px; color: #dce7ff; font-size: 11px; padding: 5px 8px; }"
            "QLineEdit:focus { border: 1px solid #5b5cf6; }"
        )
        self._raw_edit.setPlaceholderText("k1=${v1}, k2=${v2}  或  auto")
        self._raw_edit.editingFinished.connect(self._on_raw_edited)
        root.addWidget(self._raw_edit)

        skip_lbl = QLabel("跳过未导出的变量")
        skip_lbl.setStyleSheet(_HINT_STYLE)
        root.addWidget(skip_lbl)
        self._skip_cb = QCheckBox("启用")
        self._skip_cb.setChecked(bool(node.params.get("skip_no_export", True)))
        self._skip_cb.setStyleSheet(_ROW_CB_STYLE)
        self._skip_cb.toggled.connect(
            lambda checked: self.params_changed.emit("skip_no_export", bool(checked))
        )
        root.addWidget(self._skip_cb)

        self._populate_initial_rows()

    def _populate_initial_rows(self) -> None:
        """首次构建：以 params["fields"] 为基准，合并自动检测到的变量。"""
        raw = str(self._node.params.get("fields", "")).strip()
        existing_pairs = _parse_fields_string(raw)

        auto_vars = detect_available_variables(self._sequence, self._node.uid)

        existing_keys = {k for k, _ in existing_pairs}
        existing_exprs = {v for _, v in existing_pairs}

        rows_spec: List[Tuple[bool, str, str, str]] = []
        # (export, key, expr, description)

        for k, v in existing_pairs:
            rows_spec.append((True, k, v, "已有字段"))

        for name, desc, export_default in auto_vars:
            placeholder = f"${{{name}}}"
            if name in existing_keys or placeholder in existing_exprs:
                continue
            rows_spec.append((False, name, placeholder, desc))

        if raw.lower() == "auto" or raw == "":
            for idx in range(len(rows_spec)):
                export, k, v, desc = rows_spec[idx]
                auto_match = next(
                    (av for av in auto_vars if av[0] == k), None
                )
                if auto_match and auto_match[2]:
                    rows_spec[idx] = (True, k, v, desc)

        for export, k, v, desc in rows_spec:
            self._append_row(export, k, v, desc)

        self._refresh_raw_edit()

    def _append_row(self, export: bool, key: str, expr: str,
                    description: str) -> None:
        row = _FieldRow(export, key, expr, description, self._rows_container)
        row.changed.connect(self._on_row_changed)
        self._rows_layout.addWidget(row)
        self._rows.append(row)

    def _on_row_changed(self) -> None:
        if self._suppress_sync:
            return
        self._refresh_raw_edit()
        self._emit_fields()

    def _on_add_custom(self) -> None:
        idx = sum(1 for r in self._rows if "custom" in r.key_edit.text())
        default_key = f"custom{idx + 1}"
        self._append_row(True, default_key, "${}", "自定义字段")
        self._refresh_raw_edit()
        self._emit_fields()

    def _on_refresh(self) -> None:
        """重新扫描：保留已有行，把新出现的变量追加到末尾。"""
        existing_keys = {r.key_edit.text().strip() for r in self._rows}
        auto_vars = detect_available_variables(self._sequence, self._node.uid)
        added = 0
        for name, desc, export_default in auto_vars:
            if name in existing_keys:
                continue
            self._append_row(False, name, f"${{{name}}}", desc)
            added += 1
        if added:
            self._refresh_raw_edit()

    def _on_raw_edited(self) -> None:
        """用户直接修改原始字符串：反向覆盖上面的行列表。"""
        if self._suppress_sync:
            return
        text = self._raw_edit.text().strip()
        self._node.params["fields"] = text if text else "auto"
        self.params_changed.emit("fields", self._node.params["fields"])
        self._rebuild_rows_from_raw(text)

    def _rebuild_rows_from_raw(self, text: str) -> None:
        """根据 raw 文本重置行列表。"""
        self._suppress_sync = True
        try:
            while self._rows:
                row = self._rows.pop()
                self._rows_layout.removeWidget(row)
                row.deleteLater()

            pairs = _parse_fields_string(text)
            for k, v in pairs:
                self._append_row(True, k, v, "已有字段")

            auto_vars = detect_available_variables(self._sequence, self._node.uid)
            existing_keys = {k for k, _ in pairs}
            for name, desc, export_default in auto_vars:
                if name in existing_keys:
                    continue
                self._append_row(False, name, f"${{{name}}}", desc)
        finally:
            self._suppress_sync = False

    def _refresh_raw_edit(self) -> None:
        rows_data = [r.data() for r in self._rows]
        text = _compose_fields_string(rows_data)
        self._suppress_sync = True
        self._raw_edit.setText(text if text else "auto")
        self._suppress_sync = False

    def _emit_fields(self) -> None:
        rows_data = [r.data() for r in self._rows]
        text = _compose_fields_string(rows_data)
        value = text if text else "auto"
        self._node.params["fields"] = value
        self.params_changed.emit("fields", value)
