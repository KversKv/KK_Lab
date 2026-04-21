"""右栏：属性面板（动态表单，编辑当前选中节点参数）"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

from ui.pages.custom_test.nodes.base_node import BaseNode
from ui.widgets.dark_combobox import DarkComboBox
from log_config import get_logger

logger = get_logger(__name__)

_PANEL_STYLE = """
    QWidget#propertyPanel {
        background-color: transparent;
        border: none;
    }
    QScrollArea {
        background: transparent;
        border: none;
    }
    QFrame#propCard {
        background-color: #09142e;
        border: 1px solid #1a2d57;
        border-radius: 12px;
    }
    QLabel#propTitle {
        color: #f4f7ff;
        font-size: 13px;
        font-weight: 700;
        background: transparent;
        border: none;
        padding: 4px 0;
    }
    QLabel#propNodeType {
        color: #5f78a8;
        font-size: 11px;
        background: transparent;
        border: none;
    }
    QLabel#fieldLabel {
        color: #8eb0e3;
        font-size: 11px;
        background: transparent;
        border: none;
    }
    QLineEdit {
        background-color: #061022;
        border: 1px solid #1f315d;
        border-radius: 6px;
        color: #dce7ff;
        font-size: 12px;
        padding: 5px 8px;
    }
    QLineEdit:focus {
        border: 1px solid #5b5cf6;
    }
    QCheckBox {
        color: #dce7ff;
        font-size: 12px;
        background: transparent;
        border: none;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
    }
"""

_EMPTY_HINT_STYLE = """
    QLabel {
        color: #3f5070;
        font-size: 13px;
        background: transparent;
        border: none;
    }
"""


class PropertyPanel(QWidget):
    """属性面板：根据选中节点动态生成表单"""

    param_changed = Signal(str, str, object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("propertyPanel")
        self.setStyleSheet(_PANEL_STYLE)
        self.setMinimumWidth(220)

        self._current_node: Optional[BaseNode] = None
        self._editors: Dict[str, QWidget] = {}

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._inner = QWidget()
        self._inner.setObjectName("propInner")
        self._inner.setStyleSheet("QWidget#propInner { background: transparent; border: none; }")
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(8, 8, 8, 8)
        self._inner_layout.setSpacing(8)

        self._empty_label = QLabel("选择一个节点\n查看/编辑参数")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet(_EMPTY_HINT_STYLE)
        self._inner_layout.addWidget(self._empty_label)
        self._inner_layout.addStretch()

        self._scroll.setWidget(self._inner)
        root_layout.addWidget(self._scroll)

    def set_node(self, node: Optional[BaseNode]) -> None:
        """设置当前编辑的节点"""
        self._current_node = node
        self._rebuild_form()

    def _rebuild_form(self) -> None:
        """根据当前节点的 PARAM_SCHEMA 动态构建表单"""
        self._editors.clear()
        while self._inner_layout.count():
            child = self._inner_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if self._current_node is None:
            self._empty_label = QLabel("选择一个节点\n查看/编辑参数")
            self._empty_label.setAlignment(Qt.AlignCenter)
            self._empty_label.setStyleSheet(_EMPTY_HINT_STYLE)
            self._inner_layout.addWidget(self._empty_label)
            self._inner_layout.addStretch()
            return

        node = self._current_node

        card = QFrame()
        card.setObjectName("propCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        title = QLabel(f"{node.icon}  {node.display_name}")
        title.setObjectName("propTitle")
        card_layout.addWidget(title)

        type_label = QLabel(f"Type: {node.node_type}  |  UID: {node.uid[:8]}")
        type_label.setObjectName("propNodeType")
        card_layout.addWidget(type_label)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("QFrame { background-color: #1a2d57; border: none; }")
        card_layout.addWidget(sep)

        schema_map = {s["key"]: s for s in node.PARAM_SCHEMA}

        for schema in node.PARAM_SCHEMA:
            key = schema["key"]
            label_text = schema.get("label", key)
            param_type = schema.get("type", "str")
            current_val = node.params.get(key, schema.get("default"))
            options = schema.get("options")

            if key == "export_var":
                continue

            field_label = QLabel(label_text)
            field_label.setObjectName("fieldLabel")
            card_layout.addWidget(field_label)

            if param_type == "bool":
                cb = QCheckBox()
                cb.setChecked(bool(current_val))
                cb.toggled.connect(lambda checked, k=key: self._on_param_changed(k, checked))
                card_layout.addWidget(cb)
                self._editors[key] = cb

            elif options and param_type != "bool":
                combo = DarkComboBox()
                for opt in options:
                    combo.addItem(str(opt))
                combo.setCurrentText(str(current_val))
                combo.currentTextChanged.connect(lambda text, k=key: self._on_param_changed(k, text))
                card_layout.addWidget(combo)
                self._editors[key] = combo

            else:
                has_export = "export_var" in schema_map
                show_inline_export = has_export and key in ("result_var", "var_name")
                if show_inline_export:
                    export_schema = schema_map["export_var"]
                    row_layout = QHBoxLayout()
                    row_layout.setSpacing(6)
                    row_layout.setContentsMargins(0, 0, 0, 0)

                    le = QLineEdit(str(current_val) if current_val is not None else "")
                    le.editingFinished.connect(lambda k=key, e=le: self._on_param_changed(k, e.text()))
                    row_layout.addWidget(le, 1)
                    self._editors[key] = le

                    export_val = node.params.get("export_var", export_schema.get("default", True))
                    export_cb = QCheckBox("导出")
                    export_cb.setChecked(bool(export_val))
                    export_cb.setToolTip("勾选则该变量参与数据记录导出")
                    export_cb.setStyleSheet(
                        "QCheckBox { color: #8eb0e3; font-size: 10px; background: transparent; border: none; }"
                    )
                    export_cb.toggled.connect(
                        lambda checked: self._on_param_changed("export_var", checked)
                    )
                    row_layout.addWidget(export_cb)
                    self._editors["export_var"] = export_cb

                    card_layout.addLayout(row_layout)
                else:
                    le = QLineEdit(str(current_val) if current_val is not None else "")
                    le.editingFinished.connect(lambda k=key, e=le: self._on_param_changed(k, e.text()))
                    card_layout.addWidget(le)
                    self._editors[key] = le

        self._inner_layout.addWidget(card)
        self._inner_layout.addStretch()

    def _on_param_changed(self, key: str, value: Any) -> None:
        """参数变更回调"""
        if self._current_node is None:
            return

        schema_map = {s["key"]: s for s in self._current_node.PARAM_SCHEMA}
        schema = schema_map.get(key, {})
        param_type = schema.get("type", "str")

        try:
            if param_type == "int":
                value = int(value)
            elif param_type == "float":
                value = float(value)
            elif param_type == "bool":
                value = bool(value)
            else:
                value = str(value)
        except (ValueError, TypeError):
            pass

        self._current_node.params[key] = value
        self.param_changed.emit(self._current_node.uid, key, value)
