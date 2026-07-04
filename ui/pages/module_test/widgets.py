#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 页面复用控件：可折叠分组框。

复用既有 N6705CConnectionMixin / OscilloscopeConnectionMixin 构建的连接区
被包进可折叠容器，节省纵向空间。折叠通过点击标题栏切换内容可见性，
保持现有 QSS 风格（标题色/边框沿用页面样式）。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

_ARROW_EXPANDED = "▼"
_ARROW_COLLAPSED = "▶"


class CollapsibleGroupBox(QFrame):
    """带可折叠标题栏的分组容器（替代 QGroupBox，视觉一致 + 折叠能力）。

    用法：
        box = CollapsibleGroupBox("仪器连接", expanded=True)
        box.content_layout.addWidget(...)   # 把原 QGroupBox 内的控件加进去
    """

    def __init__(self, title: str, expanded: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._expanded = expanded
        self.setObjectName("collapsibleGroupBox")
        self.setStyleSheet("""
            QFrame#collapsibleGroupBox {
                border: 1px solid #333;
                border-radius: 6px;
                background-color: #0a0f1f;
            }
            QPushButton#collapseHeader {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #8eb0e3;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 700;
                text-align: left;
            }
            QPushButton#collapseHeader:hover {
                background-color: #161b2e;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toggle_btn = QPushButton(f"{_ARROW_EXPANDED if expanded else _ARROW_COLLAPSED}  {title}")
        self._toggle_btn.setObjectName("collapseHeader")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setCheckable(False)
        self._toggle_btn.setFlat(True)
        self._toggle_btn.clicked.connect(self.toggle)
        root.addWidget(self._toggle_btn)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(10, 4, 10, 8)
        self._content_layout.setSpacing(4)
        root.addWidget(self._content)

        self._content.setVisible(expanded)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def set_title(self, title: str) -> None:
        arrow = _ARROW_EXPANDED if self._expanded else _ARROW_COLLAPSED
        self._toggle_btn.setText(f"{arrow}  {title}")

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        title = self._toggle_btn.text()[2:]  # 去掉原箭头前缀
        arrow = _ARROW_EXPANDED if self._expanded else _ARROW_COLLAPSED
        self._toggle_btn.setText(f"{arrow}  {title}")

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded != expanded:
            self.toggle()


_DIALOG_QSS = """
    QDialog { background-color: #0a0f1f; color: #c8c8c8; }
    QLabel { color: #c8c8c8; background: transparent; }
    QLabel#dlgFieldLabel { color: #9aa4bd; }
    QLabel#dlgHint { color: #6f7688; }
    QLineEdit, QSpinBox, QDoubleSpinBox {
        border: 1px solid #2f374d; border-radius: 4px; padding: 3px 8px;
        background-color: #0e1526; color: #d8dce8; min-height: 22px;
    }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #4a6c9b; }
    QLineEdit::placeholder { color: #5a6377; }
    QPushButton {
        border: 1px solid #3a4260; border-radius: 4px; padding: 5px 16px;
        background-color: #1a2138; color: #d8dce8; min-height: 22px;
    }
    QPushButton:hover { background-color: #232c48; }
    QPushButton:default { border: 1px solid #4a6c9b; }
"""


class ItemParamsDialog(QDialog):
    """测试项参数设置弹窗（依 ParamSpec 序列自动生成表单）。

    基类参数经 ``base_value_fn(base_key)`` 预填且可编辑；OK 返回仅"与预填值不同"
    的键值 override，未改动项运行时回退基类 cfg。
    """

    def __init__(self, *, title: str, specs, current_override: dict,
                 base_value_fn, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setStyleSheet(_DIALOG_QSS)
        self._specs = specs
        self._editors: dict[str, QWidget] = {}
        self._prefill: dict[str, object] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        if not specs:
            root.addWidget(QLabel("该测试项暂无可设置的参数。"))
        else:
            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(8)
            grid.setColumnStretch(1, 1)
            for r, spec in enumerate(specs):
                label_txt = f"{spec.label} ({spec.unit})" if spec.unit else spec.label
                lbl = QLabel(label_txt)
                lbl.setObjectName("dlgFieldLabel")
                lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                grid.addWidget(lbl, r, 0)

                prefill = self._resolve_prefill(spec, current_override, base_value_fn)
                self._prefill[spec.key] = prefill
                editor = self._make_editor(spec, prefill)
                self._editors[spec.key] = editor
                grid.addWidget(editor, r, 1)
            root.addLayout(grid)

        self._wire_code_range_autocalc()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        ok_btn = btns.button(QDialogButtonBox.Ok)
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn = btns.button(QDialogButtonBox.Cancel)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    @staticmethod
    def _resolve_prefill(spec, current_override, base_value_fn):
        if spec.key in current_override:
            return current_override[spec.key]
        if spec.base_key:
            v = base_value_fn(spec.base_key)
            if v is not None:
                return v
        return spec.default

    def _make_editor(self, spec, prefill) -> QWidget:
        if spec.ptype == "int":
            w = QSpinBox()
            w.setRange(int(spec.minimum), int(spec.maximum))
            try:
                w.setValue(int(prefill))
            except (TypeError, ValueError):
                w.setValue(int(spec.default))
            return w
        if spec.ptype == "float":
            w = QDoubleSpinBox()
            w.setDecimals(spec.decimals)
            w.setRange(float(spec.minimum), float(spec.maximum))
            w.setSingleStep(10 ** (-spec.decimals))
            try:
                w.setValue(float(prefill))
            except (TypeError, ValueError):
                w.setValue(float(spec.default))
            return w
        w = QLineEdit()
        if isinstance(prefill, (list, tuple)):
            w.setText(", ".join(str(x) for x in prefill))
        else:
            w.setText(str(prefill))
        if spec.hint:
            w.setPlaceholderText(spec.hint)
        return w

    def _wire_code_range_autocalc(self) -> None:
        """当同时存在 msb/lsb 与 max_code 整数字段时，随 MSB/LSB 自动算出 Code 结束。

        取满量程 max_code = (1 << (msb - lsb + 1)) - 1，与 PMU Output Voltage 页面一致。
        """
        msb_w = self._editors.get("msb")
        lsb_w = self._editors.get("lsb")
        max_w = self._editors.get("max_code")
        if not (isinstance(msb_w, QSpinBox) and isinstance(lsb_w, QSpinBox)
                and isinstance(max_w, QSpinBox)):
            return

        def _update() -> None:
            msb = msb_w.value()
            lsb = lsb_w.value()
            if msb < lsb:
                return
            max_val = (1 << (msb - lsb + 1)) - 1
            max_w.setValue(min(max_val, max_w.maximum()))

        msb_w.valueChanged.connect(_update)
        lsb_w.valueChanged.connect(_update)

    def _editor_value(self, spec):
        w = self._editors[spec.key]
        if spec.ptype == "int":
            return w.value()
        if spec.ptype == "float":
            return round(w.value(), spec.decimals)
        return w.text().strip()

    def get_override(self) -> dict:
        """仅返回与预填值不同的键值（未改动项回退基类 cfg）。"""
        out: dict = {}
        for spec in self._specs:
            val = self._editor_value(spec)
            prefill = self._prefill.get(spec.key)
            base = ", ".join(str(x) for x in prefill) if isinstance(prefill, (list, tuple)) else prefill
            if spec.ptype in ("int", "float"):
                if val != prefill:
                    out[spec.key] = val
            else:
                if val != (base if base is not None else ""):
                    out[spec.key] = val
        return out
