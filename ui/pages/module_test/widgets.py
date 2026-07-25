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
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ui.theme import Colors, FontSizes, Radius

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
        self.setStyleSheet(f"""
            QFrame#collapsibleGroupBox {{
                background-color: {Colors.bg_card};
                border: 1px solid {Colors.border_primary};
                border-radius: {Radius.card}px;
            }}
            QPushButton#collapseHeader {{
                background-color: transparent;
                border: none;
                border-radius: {Radius.card}px;
                color: {Colors.text_primary};
                padding: 6px 10px;
                font-size: {FontSizes.caption};
                font-weight: 700;
                letter-spacing: 0.5px;
                text-align: left;
            }}
            QPushButton#collapseHeader:hover {{
                background-color: {Colors.submenu_item_hover_bg};
            }}
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


DIALOG_QSS = f"""
    QDialog {{
        background-color: {Colors.bg_secondary};
        color: {Colors.text_secondary};
    }}
    QLabel {{
        color: {Colors.text_secondary};
        background: transparent;
    }}
    QLabel#dlgFieldLabel {{
        color: {Colors.text_muted};
        font-size: {FontSizes.caption};
    }}
    QLabel#dlgHint {{
        color: {Colors.text_dim};
        font-size: {FontSizes.caption};
    }}
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {Colors.bg_input};
        border: 1px solid {Colors.border_input};
        border-radius: {Radius.small}px;
        padding: 4px 8px;
        color: {Colors.text_secondary};
        min-height: 22px;
    }}
    QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border: 1px solid {Colors.border_accent};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {Colors.accent_primary};
    }}
    QLineEdit::placeholder {{
        color: {Colors.text_disabled};
    }}
    QComboBox {{
        background-color: {Colors.bg_input};
        border: 1px solid {Colors.border_input};
        border-radius: {Radius.small}px;
        padding: 4px 8px;
        color: {Colors.text_secondary};
        min-height: 22px;
    }}
    QComboBox:hover {{
        border: 1px solid {Colors.border_accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {Colors.bg_input};
        border: 1px solid {Colors.border_secondary};
        color: {Colors.text_secondary};
        selection-background-color: {Colors.submenu_item_hover_bg};
    }}
    QPushButton {{
        background-color: {Colors.bg_card};
        border: 1px solid {Colors.border_accent};
        border-radius: {Radius.widget}px;
        padding: 6px 14px;
        color: {Colors.text_secondary};
        min-height: 22px;
    }}
    QPushButton:hover {{
        background-color: {Colors.submenu_item_hover_bg};
    }}
    QPushButton:default {{
        border: 1px solid {Colors.accent_primary};
    }}
    QTableWidget, QTreeWidget {{
        background-color: {Colors.bg_input};
        border: 1px solid {Colors.border_secondary};
        border-radius: {Radius.widget}px;
        color: {Colors.text_secondary};
        font-size: {FontSizes.caption};
        gridline-color: {Colors.border_secondary};
    }}
    QHeaderView::section {{
        background-color: {Colors.bg_input};
        color: {Colors.text_dim};
        border: none;
        border-right: 1px solid {Colors.border_secondary};
        padding: 4px 6px;
        font-size: {FontSizes.caption};
        font-weight: 700;
    }}
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
        self.setStyleSheet(DIALOG_QSS)
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
        """返回 override 键值。

        无 base_key 的项级参数（如寄存器扫描的 reg_addr/msb/lsb/min/max_code）
        直接全量返回——弹窗显示什么就生效什么，避免 diff 语义把它当"未改动"
        静默丢弃（曾致 Output Voltage Scan 误用默认 reg_addr=0x0 扫错寄存器）。
        有 base_key 的基类参数保持 diff：与预填值不同才计入，未改动回退基类 cfg。
        """
        out: dict = {}
        for spec in self._specs:
            val = self._editor_value(spec)
            if not spec.base_key:
                out[spec.key] = val
                continue
            prefill = self._prefill.get(spec.key)
            base = ", ".join(str(x) for x in prefill) if isinstance(prefill, (list, tuple)) else prefill
            if spec.ptype in ("int", "float"):
                if val != prefill:
                    out[spec.key] = val
            else:
                if val != (base if base is not None else ""):
                    out[spec.key] = val
        return out


class DutModeDialog(QDialog):
    """DUT 工作模式编辑弹窗：按进入方式（reg/load/manual）动态显示字段。

    结构对齐方案 §4 的 ``dut_modes`` 元素：name / enter / reg_writes / load_ma /
    mode_readback / prompt / settle_s。OK 返回一份纯 dict。
    """

    _ENTER_LABELS = (("寄存器 (reg)", "reg"), ("负载自动切换 (load)", "load"),
                     ("手动台架 (manual)", "manual"))

    def __init__(self, *, existing_names, mode: dict | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("编辑 DUT 工作模式" if mode else "添加 DUT 工作模式")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setStyleSheet(DIALOG_QSS)
        self._existing = {str(n).strip() for n in (existing_names or []) if n}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        head = QGridLayout()
        head.setHorizontalSpacing(10)
        head.setVerticalSpacing(8)
        head.setColumnStretch(1, 1)
        head.addWidget(self._flabel("模式名"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("唯一名，如 Normal_biasH")
        head.addWidget(self.name_edit, 0, 1)
        head.addWidget(self._flabel("进入方式"), 1, 0)
        self.enter_combo = QComboBox()
        for text, _ in self._ENTER_LABELS:
            self.enter_combo.addItem(text)
        head.addWidget(self.enter_combo, 1, 1)
        head.addWidget(self._flabel("稳定时间 (s)"), 2, 0)
        self.settle_spin = QDoubleSpinBox()
        self.settle_spin.setDecimals(3)
        self.settle_spin.setRange(0.0, 600.0)
        self.settle_spin.setSingleStep(0.05)
        head.addWidget(self.settle_spin, 2, 1)
        root.addLayout(head)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_reg_page())
        self._stack.addWidget(self._build_load_page())
        self._stack.addWidget(self._build_manual_page())
        root.addWidget(self._stack)
        self.enter_combo.currentIndexChanged.connect(self._stack.setCurrentIndex)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        ok_btn = btns.button(QDialogButtonBox.Ok)
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn = btns.button(QDialogButtonBox.Cancel)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        if mode:
            self._load_mode(mode)

    @staticmethod
    def _flabel(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("dlgFieldLabel")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return lbl

    def _build_reg_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.reg_table = QTableWidget(0, 2)
        self.reg_table.setHorizontalHeaderLabels(["寄存器地址", "写入值"])
        self.reg_table.verticalHeader().setVisible(False)
        self.reg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reg_table.setMaximumHeight(140)
        lay.addWidget(self.reg_table)
        row = QHBoxLayout()
        add_btn = QPushButton("+ 行")
        add_btn.clicked.connect(lambda: self._reg_add_row("0x00", "0x00"))
        del_btn = QPushButton("- 行")
        del_btn.clicked.connect(self._reg_del_row)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        row.addStretch(1)
        lay.addLayout(row)
        return page

    def _reg_add_row(self, addr: str, value: str) -> None:
        r = self.reg_table.rowCount()
        self.reg_table.insertRow(r)
        self.reg_table.setItem(r, 0, QTableWidgetItem(str(addr)))
        self.reg_table.setItem(r, 1, QTableWidgetItem(str(value)))

    def _reg_del_row(self) -> None:
        r = self.reg_table.currentRow()
        if r >= 0:
            self.reg_table.removeRow(r)

    def _build_load_page(self) -> QWidget:
        page = QWidget()
        grid = QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self._flabel("负载电流 (mA)"), 0, 0)
        self.load_ma_spin = QDoubleSpinBox()
        self.load_ma_spin.setDecimals(3)
        self.load_ma_spin.setRange(0.0, 100000.0)
        grid.addWidget(self.load_ma_spin, 0, 1)
        grid.addWidget(self._flabel("回读地址"), 1, 0)
        self.rb_addr_edit = QLineEdit()
        self.rb_addr_edit.setPlaceholderText("留空则不回读，如 0x40")
        grid.addWidget(self.rb_addr_edit, 1, 1)
        grid.addWidget(self._flabel("MSB"), 2, 0)
        self.rb_msb_spin = QSpinBox()
        self.rb_msb_spin.setRange(0, 31)
        grid.addWidget(self.rb_msb_spin, 2, 1)
        grid.addWidget(self._flabel("LSB"), 3, 0)
        self.rb_lsb_spin = QSpinBox()
        self.rb_lsb_spin.setRange(0, 31)
        grid.addWidget(self.rb_lsb_spin, 3, 1)
        grid.addWidget(self._flabel("期望值"), 4, 0)
        self.rb_expect_spin = QSpinBox()
        self.rb_expect_spin.setRange(0, 65535)
        grid.addWidget(self.rb_expect_spin, 4, 1)
        return page

    def _build_manual_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._flabel("暂停提示语"))
        self.prompt_edit = QLineEdit()
        self.prompt_edit.setPlaceholderText("如 请手动将 DUT 切到 PWM 模式后点击确认")
        lay.addWidget(self.prompt_edit)
        return page

    def _load_mode(self, mode: dict) -> None:
        self.name_edit.setText(str(mode.get("name", "")))
        enter = str(mode.get("enter", "reg"))
        idx = {"reg": 0, "load": 1, "manual": 2}.get(enter, 0)
        self.enter_combo.setCurrentIndex(idx)
        self._stack.setCurrentIndex(idx)
        settle_s = mode.get("settle_s")
        if isinstance(settle_s, (int, float)):
            self.settle_spin.setValue(float(settle_s))
        for w in (mode.get("reg_writes") or []):
            if isinstance(w, dict):
                self._reg_add_row(w.get("addr", "0x00"), w.get("value", "0x00"))
        self.load_ma_spin.setValue(float(mode.get("load_ma", 0.0) or 0.0))
        rb = mode.get("mode_readback")
        if isinstance(rb, dict):
            self.rb_addr_edit.setText(str(rb.get("addr", "")))
            self.rb_msb_spin.setValue(int(rb.get("msb", 0)))
            self.rb_lsb_spin.setValue(int(rb.get("lsb", 0)))
            self.rb_expect_spin.setValue(int(rb.get("expect", 0)))
        self.prompt_edit.setText(str(mode.get("prompt", "")))

    def _on_accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "校验失败", "模式名不能为空。")
            return
        if name in self._existing:
            QMessageBox.warning(self, "校验失败", f"模式名「{name}」已存在，请改用唯一名。")
            return
        self.accept()

    def get_mode(self) -> dict:
        enter = self._ENTER_LABELS[self.enter_combo.currentIndex()][1]
        mode: dict = {
            "name": self.name_edit.text().strip(),
            "enter": enter,
            "settle_s": round(self.settle_spin.value(), 3),
        }
        if enter == "reg":
            writes = []
            for r in range(self.reg_table.rowCount()):
                addr_item = self.reg_table.item(r, 0)
                val_item = self.reg_table.item(r, 1)
                addr = addr_item.text().strip() if addr_item else ""
                value = val_item.text().strip() if val_item else ""
                if addr:
                    writes.append({"addr": addr, "value": value or "0x00"})
            mode["reg_writes"] = writes
        elif enter == "load":
            mode["load_ma"] = round(self.load_ma_spin.value(), 3)
            rb_addr = self.rb_addr_edit.text().strip()
            if rb_addr:
                mode["mode_readback"] = {
                    "addr": rb_addr,
                    "msb": self.rb_msb_spin.value(),
                    "lsb": self.rb_lsb_spin.value(),
                    "expect": self.rb_expect_spin.value(),
                }
        else:
            mode["prompt"] = self.prompt_edit.text().strip()
        return mode
