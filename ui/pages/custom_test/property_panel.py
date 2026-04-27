"""右栏：属性面板（动态表单，编辑当前选中节点参数）"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QFrame, QScrollArea, QSizePolicy, QPushButton,
)
from PySide6.QtCore import Qt, Signal

from ui.pages.custom_test.nodes.base_node import BaseNode
from ui.widgets.dark_combobox import DarkComboBox
from log_config import get_logger

logger = get_logger(__name__)

import os as _os
_CHECK_ICON = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))),
    "resources", "icons", "check.svg"
).replace("\\", "/")

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
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border-style: solid;
        border-width: 1.5px;
        border-color: #3a5a9f;
        border-radius: 4px;
        background: #061022;
    }
    QCheckBox::indicator:hover {
        border-color: #5b5cf6;
        background: #0d1a3a;
    }
    QCheckBox::indicator:checked {
        border-color: #5b5cf6;
        background: #5b5cf6;
        image: url(""" + _CHECK_ICON + """);
    }
    QCheckBox::indicator:checked:hover {
        background: #7070ff;
        border-color: #7070ff;
    }
    QToolTip {
        background-color: #0d1f42;
        border: 1px solid #2a4684;
        border-radius: 4px;
        color: #dce7ff;
        font-size: 11px;
        padding: 5px 8px;
        opacity: 230;
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
    add_else_if_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("propertyPanel")
        self.setStyleSheet(_PANEL_STYLE)
        self.setMinimumWidth(220)

        self._current_node: Optional[BaseNode] = None
        self._editors: Dict[str, QWidget] = {}
        self._canvas: Any = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #22345f;
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #30497f;
            }
            QScrollBar::sub-line:vertical,
            QScrollBar::add-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        self._inner = QWidget()
        self._inner.setObjectName("propInner")
        self._inner.setStyleSheet("QWidget#propInner { background: transparent; border: none; }")
        self._inner_layout = QVBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(8, 8, 14, 8)
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

    def set_canvas(self, canvas: Any) -> None:
        """注入序列画布，用于 RecordDataPoint 自动扫描已有变量"""
        self._canvas = canvas

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

        if node.node_type == "RecordDataPoint":
            self._build_record_data_editor(node, card_layout)
            self._inner_layout.addWidget(card)
            self._inner_layout.addStretch()
            return

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
                combo.setEditable(True)
                for opt in options:
                    combo.addItem(str(opt))
                combo.setCurrentText(str(current_val))
                combo.currentTextChanged.connect(lambda text, k=key: self._on_param_changed(k, text))
                if combo.lineEdit():
                    combo.lineEdit().setPlaceholderText("值 或 ${var}")
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
                        "QCheckBox::indicator { width: 14px; height: 14px;"
                        "  border-style: solid; border-width: 1.5px; border-color: #3a5a9f;"
                        "  border-radius: 3px; background: #061022; }"
                        "QCheckBox::indicator:hover { border-color: #5b5cf6; background: #0d1a3a; }"
                        "QCheckBox::indicator:checked { border-color: #5b5cf6; background: #5b5cf6;"
                        "  image: url(" + _CHECK_ICON + "); }"
                        "QCheckBox::indicator:checked:hover { background: #7070ff; border-color: #7070ff; }"
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

        if hasattr(node, "get_shadow_key"):
            try:
                shadow_key = node.get_shadow_key()
            except Exception as exc:
                logger.warning("get_shadow_key failed: %s", exc)
                shadow_key = ""
            if shadow_key:
                shadow_sep = QFrame()
                shadow_sep.setFixedHeight(1)
                shadow_sep.setStyleSheet("QFrame { background-color: #1a2d57; border: none; }")
                card_layout.addWidget(shadow_sep)

                shadow_title = QLabel("隐式变量(影子键)")
                shadow_title.setObjectName("fieldLabel")
                card_layout.addWidget(shadow_title)

                shadow_label = QLabel(f"💡 {shadow_key}")
                shadow_label.setObjectName("shadowKeyLabel")
                shadow_label.setWordWrap(True)
                shadow_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                shadow_label.setStyleSheet(
                    "QLabel#shadowKeyLabel { color: #ffc978; font-size: 11px;"
                    "  background-color: #0c1733; border: 1px dashed #3a5a9f;"
                    "  border-radius: 5px; padding: 5px 8px; }"
                )
                shadow_label.setToolTip(
                    "执行时,除了上面的『结果存入变量』,该节点还会额外写入这个隐式变量名。\n"
                    "通常你不需要使用它;仅在需要按 通道/类型 直接索引结果时引用。"
                )
                card_layout.addWidget(shadow_label)
                self._editors["__shadow_key_label__"] = shadow_label

        self._inner_layout.addWidget(card)

        from ui.pages.custom_test.nodes.logic_nodes import IfBlock, IfBranch
        target_uid = None
        if isinstance(node, IfBlock):
            target_uid = node.uid
        elif isinstance(node, IfBranch):
            target_uid = node.uid

        if target_uid is not None:
            btn_frame = QFrame()
            btn_frame.setObjectName("propCard")
            btn_layout = QVBoxLayout(btn_frame)
            btn_layout.setContentsMargins(12, 8, 12, 8)
            btn_layout.setSpacing(6)

            hint = QLabel("分支管理")
            hint.setObjectName("fieldLabel")
            btn_layout.addWidget(hint)

            add_btn = QPushButton("+ Add Else If")
            add_btn.setCursor(Qt.PointingHandCursor)
            add_btn.setStyleSheet(
                "QPushButton { background-color: #132040; color: #8eb0e3; "
                "border: 1px solid #1a2d57; border-radius: 6px; padding: 6px 12px; "
                "font-size: 11px; font-weight: 600; }"
                "QPushButton:hover { background-color: #1a2d57; color: #dce7ff; }"
            )
            add_btn.clicked.connect(lambda: self.add_else_if_requested.emit(target_uid))
            btn_layout.addWidget(add_btn)

            self._inner_layout.addWidget(btn_frame)

        self._inner_layout.addStretch()

    def _build_record_data_editor(self, node: BaseNode, card_layout: QVBoxLayout) -> None:
        """为 RecordDataPoint 节点构建自定义表单：自动扫描变量 + 勾选/编辑/自定义。"""
        from ui.pages.custom_test.record_data_editor import RecordDataPointEditor

        sequence: List[BaseNode] = []
        if self._canvas is not None and hasattr(self._canvas, "get_sequence"):
            try:
                sequence = self._canvas.get_sequence()
            except Exception as exc:
                logger.warning("get_sequence failed: %s", exc)

        editor = RecordDataPointEditor(node, sequence)
        editor.params_changed.connect(
            lambda key, value, n=node: self._on_record_param_changed(n, key, value)
        )
        card_layout.addWidget(editor)
        self._editors["__record_editor__"] = editor

    def _on_record_param_changed(self, node: BaseNode, key: str, value: Any) -> None:
        """RecordDataPoint 专属编辑器的回调。"""
        node.params[key] = value
        self.param_changed.emit(node.uid, key, value)

    def _on_param_changed(self, key: str, value: Any) -> None:
        if self._current_node is None:
            return

        schema_map = {s["key"]: s for s in self._current_node.PARAM_SCHEMA}
        schema = schema_map.get(key, {})
        param_type = schema.get("type", "str")

        str_val = str(value) if value is not None else ""
        is_var_ref = "${" in str_val

        try:
            if is_var_ref:
                value = str_val
            elif param_type == "int":
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

        if key in ("channel", "measure_type"):
            self._refresh_shadow_key_label()

    def _refresh_shadow_key_label(self) -> None:
        """channel/measure_type 变化时,刷新隐式变量(影子键)提示文本。"""
        node = self._current_node
        if node is None or not hasattr(node, "get_shadow_key"):
            return
        label = self._editors.get("__shadow_key_label__")
        if label is None:
            return
        try:
            shadow_key = node.get_shadow_key()
        except Exception:
            return
        if shadow_key:
            label.setText(f"💡 {shadow_key}")
