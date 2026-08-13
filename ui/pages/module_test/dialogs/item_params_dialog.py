"""ItemParamsDialog — 测试项参数设置弹窗（依 ParamSpec 序列自动生成表单）。

**语义契约（不可破坏，附 tests/test_item_params_dialog.py 覆盖）**：
1. ``ParamSpec.ptype ∈ {int, float, text(str), groups}``；``groups`` 用
   ``ParamSpec.columns`` 渲染 ``GroupsTableEditor``；
2. ``get_override()``：**无 base_key 的项级参数全量返回**（显示即生效）；
   **有 base_key 的参数做 diff**（与预填值相同则不返回，运行时回退基类 cfg）；
3. ``msb/lsb/max_code`` 三字段同时存在时，自动计算
   ``max_code = (1 << (msb-lsb+1)) - 1``。

为什么这样拆：弹窗语义曾踩坑（diff 误丢 max_code），独立成文件 + 单测
固化契约，groups 编辑器复用 P1 的 GroupsTableEditor（带校验高亮）。

弹窗以 QTabWidget 分页：「参数」页放 ParamSpec 表单；``item_key`` 命中
``JUDGE_METRICS`` 时追加「判断标准」页（JudgeCriteriaTab），编辑当前测试项
的 PASS/FAIL 规则（``get_judge_payload()`` 导出 ``{"enabled", "rules"}``，
持久化回 ``judge_criteria[item_key]``，与全模块判定表同源）。
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout, QLabel,
    QLineEdit, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from core.module_test.judge import JUDGE_METRICS
from ui.pages.module_test.dialogs.judge_dialog import JudgeCriteriaTab
from ui.theme import apply_qss
from ui.widgets.groups_editor import GroupColumn, GroupsTableEditor


def _switch_icon_overrides() -> dict[str, str]:
    """注入滑动开关 SVG 路径供 dialog.qss ``$switch_on_svg`` / ``$switch_off_svg``。"""
    from ui.resource_path import get_resource_base
    icons = os.path.join(get_resource_base(), "resources", "icons")
    return {f"{n}_svg": os.path.join(icons, f"{n}.svg").replace(os.sep, "/")
            for n in ("switch_on", "switch_off")}


class ItemParamsDialog(QDialog):
    """测试项参数设置弹窗（依 ParamSpec 序列自动生成表单）。

    基类参数经 ``base_value_fn(base_key)`` 预填且可编辑；OK 返回"与预填值不同"
    的键值 override（有 base_key 时），未改动项运行时回退基类 cfg。
    """

    def __init__(self, *, title: str, specs, current_override: dict,
                 base_value_fn, parent: QWidget | None = None,
                 item_key: str = "", judge_payload: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(360)
        apply_qss(self, "dialog", **_switch_icon_overrides())
        self._specs = specs
        self._editors: dict[str, QWidget] = {}
        self._prefill: dict[str, object] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        params_page = QWidget()
        params_lay = QVBoxLayout(params_page)
        params_lay.setContentsMargins(0, 10, 0, 0)
        params_lay.setSpacing(10)

        if not specs:
            params_lay.addWidget(QLabel("该测试项暂无可设置的参数。"))
        else:
            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(8)
            grid.setColumnStretch(1, 1)
            row = 0
            for spec in specs:
                prefill = self._resolve_prefill(spec, current_override, base_value_fn)
                self._prefill[spec.key] = prefill
                editor = self._make_editor(spec, prefill)
                self._editors[spec.key] = editor

                label_txt = f"{spec.label} ({spec.unit})" if spec.unit else spec.label
                lbl = QLabel(label_txt)
                lbl.setObjectName("dlgFieldLabel")

                if spec.ptype == "groups":
                    # 表格编辑器占整行（表头自带单位标签）
                    grid.addWidget(lbl, row, 0, 1, 2)
                    grid.addWidget(editor, row + 1, 0, 1, 2)
                    self.setMinimumWidth(460)
                    row += 2
                    continue

                lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                grid.addWidget(lbl, row, 0)
                grid.addWidget(editor, row, 1)
                row += 1
            params_lay.addLayout(grid)

        self._judge_tab: JudgeCriteriaTab | None = None
        if item_key and item_key in JUDGE_METRICS:
            tabs = QTabWidget()
            # pane 卡片已提供外框，参数页内容与边框留白保持一致
            params_lay.setContentsMargins(12, 10, 12, 12)
            tabs.addTab(params_page, "参数")
            self._judge_tab = JudgeCriteriaTab(item_key, judge_payload, parent=tabs)
            tabs.addTab(self._judge_tab, "判断标准")
            root.addWidget(tabs, 1)
            self.setMinimumWidth(560)
        else:
            root.addWidget(params_page, 1)

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

    # ------------------------------------------------------------------ 预填
    @staticmethod
    def _resolve_prefill(spec, current_override, base_value_fn):
        if spec.key in current_override:
            return current_override[spec.key]
        if spec.base_key:
            v = base_value_fn(spec.base_key)
            if v is not None:
                return v
        return spec.default

    # ------------------------------------------------------------------ 编辑器
    def _make_editor(self, spec, prefill) -> QWidget:
        if spec.ptype == "groups":
            columns = [
                GroupColumn(c.key, c.label, c.unit, c.minimum, c.maximum,
                            c.decimals, float(c.default))
                for c in spec.columns
            ]
            rows = prefill if isinstance(prefill, list) else []
            return GroupsTableEditor(columns, prefill=rows, parent=self)
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

    # ------------------------------------------------------------------ 导出
    def _editor_value(self, spec):
        w = self._editors[spec.key]
        if spec.ptype == "groups":
            return w.value()
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

    def get_judge_rules(self) -> list[dict]:
        """返回「判断标准」页编辑的规则列表（无该页时返回空）。"""
        if self._judge_tab is None:
            return []
        return self._judge_tab.get_rules()

    def get_judge_payload(self) -> dict:
        """返回「判断标准」页完整配置 ``{"enabled": bool, "rules": list}``。"""
        if self._judge_tab is None:
            return {}
        return self._judge_tab.get_payload()
