"""JudgeCriteriaTab — 单个测试项的判定标准编辑控件（内嵌 ItemParamsDialog 标签页）。

仅收录当前测试项在 ``core.module_test.judge`` 的 ``JUDGE_METRICS`` 中注册
的指标，每个指标一行：勾选「启用」并设定「通过条件」即构成一条判定规则；
``get_payload()`` 返回 ``{"enabled": bool, "rules": list}``，随模块配置
保存 / 加载，runner 完成测试项时据此判 PASS/FAIL（与报告异常点标红相互独立）。

顶部 master 滑动开关控制「是否对本项执行判定」：关闭时保留已配置规则但
跳过判定（结果保持 N/A），便于调试阈值时临时停用判定。

行结构：指标 (单位) | 启用 | 通过条件 | 下限/阈值 | 上限（仅 range 启用）。
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QHBoxLayout, QHeaderView,
    QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.module_test.judge import JUDGE_METRICS, JUDGE_OPS

_COL_METRIC, _COL_ENABLE, _COL_OP, _COL_V1, _COL_V2 = range(5)


class JudgeCriteriaTab(QWidget):
    """单个测试项的判定标准编辑控件（按指标逐行启用/设条件）。"""

    def __init__(self, item_key: str, payload: dict | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._metrics = JUDGE_METRICS.get(item_key, ())

        root = QVBoxLayout(self)
        # pane 卡片已提供外框，内容与边框留白保持一致
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(8)

        # —— master 滑动开关：是否对本项执行判定 ——
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        self._master_switch = QCheckBox("启用判定标准")
        # 缺省 True（向后兼容旧配置无 enabled 键时仍判定）；有规则时默认开
        payload_dict = payload or {}
        has_rules = bool(payload_dict.get("rules"))
        default_on = payload_dict.get("enabled", has_rules)
        self._master_switch.setChecked(bool(default_on))
        self._master_switch.setProperty("switch", "true")
        header.addWidget(self._master_switch)
        header.addStretch(1)
        root.addLayout(header)

        hint = QLabel(
            "勾选「启用」并设定「通过条件」后，本测试项完成时按标准判定 PASS/FAIL；"
            "测量值满足「通过条件」即 PASS，否则 FAIL。未启用或无测量数据的指标"
            "保持 N/A。与报告中的异常点标红互不影响。顶部开关关闭时保留规则但"
            "跳过判定。")
        hint.setProperty("role", "caption")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self._table = QTableWidget(len(self._metrics), 5, self)
        # dialog.qss 专用段落：透底去框、单元格编辑器去框（防边框交叠）
        self._table.setObjectName("judgeCriteriaTable")
        # 「通过条件」列表达：测量值满足该条件才算 PASS
        # 「下限」列在 range 时填下限，其余操作符填阈值（上限/下限由操作符决定）
        # 「上限」列仅 range 时启用
        self._table.setHorizontalHeaderLabels(
            ["指标 (单位)", "启用", "通过条件", "下限 / 阈值", "上限"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._editors: list[dict] = []
        self._fill_rows(payload or {})
        root.addWidget(self._table, 1)

        self._master_switch.toggled.connect(self._on_master_toggled)
        self._on_master_toggled()

    # ------------------------------------------------------------------ master 开关联动
    def _on_master_toggled(self) -> None:
        enabled = self._master_switch.isChecked()
        self._table.setEnabled(enabled)

    # ------------------------------------------------------------------ 行装配
    def _fill_rows(self, payload: dict) -> None:
        # 索引现有规则：{metric_key: rule}
        existing: dict[str, dict] = {}
        for rule in (payload or {}).get("rules") or []:
            existing[str(rule.get("metric", ""))] = rule

        for row, metric in enumerate(self._metrics):
            rule = existing.get(metric.key)

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
            op_combo.setObjectName("judgeCellEditor")
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
                "metric": metric.key,
                "check": check, "op": op_combo, "v1": v1_spin, "v2": v2_spin,
            })
        # 行高钉 32px（紧凑、与编辑器对齐），避免默认行高把表格撑散
        for row in range(self._table.rowCount()):
            self._table.setRowHeight(row, 32)

    @staticmethod
    def _make_spin(value) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setObjectName("judgeCellEditor")
        spin.setRange(-1e12, 1e12)
        spin.setDecimals(4)
        try:
            spin.setValue(float(value))
        except (TypeError, ValueError):
            spin.setValue(0.0)
        return spin

    # ------------------------------------------------------------------ 导出
    def is_enabled(self) -> bool:
        """master 开关是否开启（是否对本项执行判定）。"""
        return self._master_switch.isChecked()

    def get_rules(self) -> list[dict]:
        """导出本测试项的判定规则列表（仅启用行）。"""
        rules: list[dict] = []
        for ed in self._editors:
            if not ed["check"].isChecked():
                continue
            rules.append({
                "metric": ed["metric"],
                "op": ed["op"].currentData(),
                "v1": ed["v1"].value(),
                "v2": (ed["v2"].value()
                       if ed["op"].currentData() == "range" else None),
            })
        return rules

    def get_payload(self) -> dict:
        """导出完整判定配置：``{"enabled": bool, "rules": list}``。"""
        return {"enabled": self.is_enabled(), "rules": self.get_rules()}
