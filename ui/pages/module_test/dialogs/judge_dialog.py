"""JudgeCriteriaDialog — Module Test 判定标准编辑弹窗。

按当前模块 ITEMS_REGISTRY 中有可判定指标（``core.module_test.judge``
的 ``JUDGE_METRICS``）的测试项逐行生成：每个（测试项 × 指标）一行，
勾选「启用」并设定条件即构成一条判定规则；``get_criteria()`` 返回可
JSON 序列化的 dict，随模块配置保存 / 加载，runner 完成测试项时据此判
PASS/FAIL（与报告异常点标红相互独立）。

行结构：测试项 | 指标 (单位) | 启用 | 条件 | 阈值/下限 | 上限（仅「介于」）。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from core.module_test.judge import JUDGE_METRICS, JUDGE_OPS
from ui.theme import apply_qss

_COL_ITEM, _COL_METRIC, _COL_ENABLE, _COL_OP, _COL_V1, _COL_V2 = range(6)


class JudgeCriteriaDialog(QDialog):
    """判定标准编辑弹窗（按测试项 × 指标逐行启用/设条件）。"""

    def __init__(self, items_registry: dict, criteria: dict,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("判断标准（PASS/FAIL Criteria）")
        self.setModal(True)
        self.setMinimumWidth(760)
        self.setMinimumHeight(420)
        # 只用 dialog.qss：其表格段自带 color/表头色；再叠 table.qss 会顶掉
        # 文字色（table.qss 防"盖掉逐项 setForeground"不设 color），致黑字叠深底看不清
        apply_qss(self, "dialog")

        # 展平为行：(item_key, item_name, MetricSpec)，仅收录有指标的项
        self._rows: list[tuple[str, str, object]] = []
        for item_key, entry in items_registry.items():
            metrics = JUDGE_METRICS.get(item_key)
            if not metrics:
                continue
            name = entry[0]
            for metric in metrics:
                self._rows.append((item_key, name, metric))

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        hint = QLabel(
            "勾选「启用」并设定条件后，测试项完成时按标准判定 PASS/FAIL；"
            "未启用或无测量数据的项保持 N/A。与报告中的异常点标红互不影响。")
        hint.setProperty("role", "caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._table = QTableWidget(len(self._rows), 6, self)
        self._table.setHorizontalHeaderLabels(
            ["测试项", "指标 (单位)", "启用", "条件", "阈值 / 下限", "上限"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._editors: list[dict] = []
        self._fill_rows(criteria or {})
        root.addWidget(self._table, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                                parent=self)
        ok_btn = btns.button(QDialogButtonBox.Ok)
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn = btns.button(QDialogButtonBox.Cancel)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ------------------------------------------------------------------ 行装配
    def _fill_rows(self, criteria: dict) -> None:
        # 索引现有规则：{(item_key, metric_key): rule}
        existing: dict[tuple[str, str], dict] = {}
        for item_key, payload in criteria.items():
            for rule in (payload or {}).get("rules") or []:
                existing[(item_key, str(rule.get("metric", "")))] = rule

        for row, (item_key, name, metric) in enumerate(self._rows):
            rule = existing.get((item_key, metric.key))

            item_cell = QTableWidgetItem(name)
            item_cell.setFlags(item_cell.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, _COL_ITEM, item_cell)
            metric_text = (f"{metric.label} ({metric.unit})"
                           if metric.unit else metric.label)
            metric_cell = QTableWidgetItem(metric_text)
            metric_cell.setFlags(metric_cell.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, _COL_METRIC, metric_cell)

            check = QCheckBox()
            check.setChecked(rule is not None)
            check_wrap = QWidget()
            check_lay = QHBoxLayout(check_wrap)
            check_lay.setContentsMargins(0, 0, 0, 0)
            check_lay.addWidget(check)
            check_lay.setAlignment(Qt.AlignCenter)
            self._table.setCellWidget(row, _COL_ENABLE, check_wrap)

            op_combo = QComboBox()
            for op_value, op_label in JUDGE_OPS:
                op_combo.addItem(op_label, op_value)
            if rule is not None:
                idx = op_combo.findData(str(rule.get("op", "<")))
                if idx >= 0:
                    op_combo.setCurrentIndex(idx)
            self._table.setCellWidget(row, _COL_OP, op_combo)

            v1_spin = self._make_spin(rule.get("v1") if rule else None)
            v2_spin = self._make_spin(rule.get("v2") if rule else None)
            self._table.setCellWidget(row, _COL_V1, v1_spin)
            self._table.setCellWidget(row, _COL_V2, v2_spin)

            op_combo.currentIndexChanged.connect(
                lambda _i, s=v2_spin, c=op_combo:
                s.setEnabled(c.currentData() == "range"))
            v2_spin.setEnabled(op_combo.currentData() == "range")

            self._editors.append({
                "item_key": item_key, "metric": metric.key,
                "check": check, "op": op_combo, "v1": v1_spin, "v2": v2_spin,
            })
        self._table.resizeRowsToContents()

    @staticmethod
    def _make_spin(value) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(-1e12, 1e12)
        spin.setDecimals(4)
        try:
            spin.setValue(float(value))
        except (TypeError, ValueError):
            spin.setValue(0.0)
        return spin

    # ------------------------------------------------------------------ 导出
    def get_criteria(self) -> dict:
        """导出判定标准：``{item_key: {"rules": [...]}}``（仅启用行）。"""
        criteria: dict[str, dict] = {}
        for ed in self._editors:
            if not ed["check"].isChecked():
                continue
            rule = {
                "metric": ed["metric"],
                "op": ed["op"].currentData(),
                "v1": ed["v1"].value(),
                "v2": (ed["v2"].value()
                       if ed["op"].currentData() == "range" else None),
            }
            criteria.setdefault(ed["item_key"], {"rules": []})["rules"].append(rule)
        return criteria
