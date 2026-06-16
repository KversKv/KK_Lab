import json
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QFrame, QSplitter, QComboBox, QLineEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QFormLayout, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QColorDialog,
    QMessageBox, QFileDialog, QTabWidget, QWidget,
)

from log_config import get_logger
from ui.modules.serialCom_module.serial_chart_model import (
    ChartRule, ChartSeries, FieldSpec, ChartConfig,
    FIELD_TYPES, MATCH_MODES, INPUT_MODES, EMIT_POLICIES, TIMESTAMP_MODES,
    CHART_TYPES, GROUP_BY_OPTIONS, SOURCE_SESSIONS, DERIVED_OPERATIONS,
    PRESET_TEMPLATES, DEFAULT_COLORS, CHART_RULE_WARN_COUNT,
    CHART_REFRESH_INTERVAL_MS, new_id,
)
from ui.modules.serialCom_module.serial_chart_controller import SerialChartController

logger = get_logger(__name__)

_DIALOG_QSS = """
QDialog#scChartDialog, QDialog#scChartEditor { background-color: #0B1220; }
QDialog#scChartDialog QWidget, QDialog#scChartEditor QWidget {
    background-color: #0B1220; color: #C7D2E0;
}
QFrame#chartPanel { background-color: #0B1220; border: none; }
QSplitter { background-color: #0B1220; }
QSplitter::handle { background-color: #1E293B; }
QSplitter::handle:horizontal { width: 4px; }
QSplitter::handle:vertical { height: 4px; }
QLabel { background-color: transparent; color: #C7D2E0; font-size: 12px; }
QLabel#chartTitle { color: #E6EEF8; font-size: 15px; font-weight: 700; }
QLabel#chartHint { color: #64748B; font-size: 11px; }
QLabel#chartError { color: #F87171; font-size: 11px; }
QLabel#chartPanelTitle { color: #93A4BC; font-size: 12px; font-weight: 600; }
QScrollBar:vertical {
    background: #0B1220; width: 10px; margin: 0; border: none;
}
QScrollBar::handle:vertical {
    background: #1E293B; border-radius: 5px; min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #29374B; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
QScrollBar:horizontal {
    background: #0B1220; height: 10px; margin: 0; border: none;
}
QScrollBar::handle:horizontal {
    background: #1E293B; border-radius: 5px; min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #29374B; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QPushButton#chartToggle {
    background-color: #111c2e; border: 1px solid #1E293B; border-radius: 5px;
    color: #93A4BC; font-size: 12px; padding: 5px 12px; min-height: 22px;
}
QPushButton#chartToggle:hover { background-color: #1E293B; color: #E6EEF8; }
QPushButton#chartToggle:checked {
    background-color: #15806A; border-color: #15806A; color: #ECFDF5;
}
QPushButton#chartPanelBtn {
    background-color: #1E293B; border: 1px solid #29374B; border-radius: 5px;
    color: #C7D2E0; font-size: 12px; padding: 5px 2px; min-height: 22px;
}
QPushButton#chartPanelBtn:hover { background-color: #29374B; color: #E6EEF8; }
QListWidget {
    background-color: #0F172A; border: 1px solid #1E293B; border-radius: 6px;
    color: #C7D2E0; font-size: 12px; outline: none;
}
QListWidget::item { padding: 6px 8px; border-radius: 4px; }
QListWidget::item:selected { background-color: #1E293B; color: #E6EEF8; }
QPushButton {
    background-color: #1E293B; border: 1px solid #29374B; border-radius: 5px;
    color: #C7D2E0; font-size: 12px; padding: 5px 12px; min-height: 22px;
}
QPushButton:hover { background-color: #29374B; }
QPushButton#chartPrimary { background-color: #15806A; border-color: #15806A; color: #ECFDF5; }
QPushButton#chartPrimary:hover { background-color: #199e83; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background-color: #0F172A; border: 1px solid #1E293B; border-radius: 5px;
    color: #E2E8F0; font-size: 12px; padding: 4px 6px; min-height: 22px;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {
    border: 1px solid #15806A;
}
QComboBox QAbstractItemView {
    background-color: #0F172A; color: #E2E8F0; selection-background-color: #1E293B;
}
QCheckBox { color: #C7D2E0; font-size: 12px; }
QTableWidget {
    background-color: #0F172A; border: 1px solid #1E293B; color: #C7D2E0;
    gridline-color: #1E293B; font-size: 11px;
}
QHeaderView::section {
    background-color: #111c2e; color: #93A4BC; border: none;
    border-right: 1px solid #1E293B; padding: 4px;
}
QTabWidget::pane { border: 1px solid #1E293B; border-radius: 6px; background-color: #0B1220; }
QTabWidget > QWidget { background-color: #0B1220; }
QTabBar { background-color: #0B1220; }
QTableCornerButton::section { background-color: #111c2e; border: none; }
QTabBar::tab {
    background-color: #0F172A; color: #93A4BC; padding: 6px 14px;
    border: 1px solid #1E293B; border-bottom: none;
    border-top-left-radius: 5px; border-top-right-radius: 5px;
}
QTabBar::tab:selected { background-color: #1E293B; color: #E6EEF8; }
"""


def _styled_dialog(dlg):
    dlg.setStyleSheet(_DIALOG_QSS)


class _FieldSpecDialog(QDialog):
    def __init__(self, parent=None, spec: FieldSpec = None):
        super().__init__(parent)
        self.setObjectName("scChartEditor")
        self.setWindowTitle("Field")
        self.setMinimumWidth(420)
        _styled_dialog(self)
        self._spec = spec or FieldSpec()

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit(self._spec.name)
        self.name_edit.setPlaceholderText("regex group name, e.g. vbat")
        form.addRow("Field name", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(FIELD_TYPES)
        if self._spec.type in FIELD_TYPES:
            self.type_combo.setCurrentText(self._spec.type)
        form.addRow("Type", self.type_combo)

        self.unit_edit = QLineEdit(self._spec.unit)
        form.addRow("Unit", self.unit_edit)

        self.group_edit = QLineEdit(self._spec.group)
        form.addRow("Group", self.group_edit)

        self.enum_edit = QPlainTextEdit()
        self.enum_edit.setPlaceholderText("IDLE=0, CC=2, CV=3  (enum only)")
        self.enum_edit.setFixedHeight(54)
        self.enum_edit.setPlainText(self._enum_to_text())
        form.addRow("Enum map", self.enum_edit)

        self.pf_edit = QLineEdit()
        self.pf_edit.setPlaceholderText("GOOD=1, BAD=0  (pass_fail override)")
        self.pf_edit.setText(", ".join(f"{k}={v}" for k, v in self._spec.pass_fail_map.items()))
        form.addRow("Pass/Fail map", self.pf_edit)

        root.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.setObjectName("chartPrimary")
        ok.setAutoDefault(True)
        ok.setDefault(True)
        ok.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

    def _enum_to_text(self):
        values = self._spec.enum_map.get("values") if self._spec.enum_map else None
        if not values:
            return ""
        return ", ".join(f"{k}={v}" for k, v in values.items())

    @staticmethod
    def _parse_enum(text):
        labels, values = {}, {}
        tokens = text.replace("\n", ",").replace(";", ",").split(",")
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue
            if "=" in tok:
                k, v = tok.split("=", 1)
            else:
                parts = tok.split()
                if len(parts) != 2:
                    continue
                k, v = parts[0], parts[1]
            k = k.strip()
            try:
                num = float(v.strip())
            except ValueError:
                continue
            num_i = int(num) if num.is_integer() else num
            values[k] = num_i
            labels[str(num_i)] = k
        if not values:
            return {}
        return {"labels": labels, "values": values}

    @staticmethod
    def _parse_pf(text):
        result = {}
        for tok in text.replace(";", ",").split(","):
            tok = tok.strip()
            if "=" not in tok:
                continue
            k, v = tok.split("=", 1)
            try:
                result[k.strip().upper()] = int(float(v.strip()))
            except ValueError:
                continue
        return result

    def _on_ok(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Field", "Field name is required.")
            return
        self._spec.name = name
        self._spec.type = self.type_combo.currentText()
        self._spec.unit = self.unit_edit.text().strip()
        self._spec.group = self.group_edit.text().strip()
        self._spec.enum_map = self._parse_enum(self.enum_edit.toPlainText())
        self._spec.pass_fail_map = self._parse_pf(self.pf_edit.text())
        self.accept()

    def result_spec(self):
        return self._spec


class _RuleEditorDialog(QDialog):
    def __init__(self, parent=None, rule: ChartRule = None, parser=None):
        super().__init__(parent)
        self.setObjectName("scChartEditor")
        self.setWindowTitle("Rule")
        self.setMinimumSize(560, 620)
        _styled_dialog(self)
        self._rule = rule or ChartRule()
        self._parser = parser

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit(self._rule.name)
        form.addRow("Name", self.name_edit)

        self.enabled_cb = QCheckBox("Enabled")
        self.enabled_cb.setChecked(self._rule.enabled)
        form.addRow("", self.enabled_cb)

        self.session_combo = QComboBox()
        self.session_combo.addItems(SOURCE_SESSIONS)
        self.session_combo.setEditable(True)
        self.session_combo.setCurrentText(self._rule.source_session)
        form.addRow("Source session", self.session_combo)

        self.input_combo = QComboBox()
        self.input_combo.addItems(INPUT_MODES)
        self.input_combo.setCurrentText(self._rule.input_mode)
        form.addRow("Input mode", self.input_combo)

        self.match_combo = QComboBox()
        self.match_combo.addItems(MATCH_MODES)
        self.match_combo.setCurrentText(self._rule.match_mode)
        form.addRow("Match mode", self.match_combo)

        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- preset --")
        self.preset_combo.addItems(list(PRESET_TEMPLATES.keys()))
        apply_preset = QPushButton("Apply")
        apply_preset.setAutoDefault(False)
        apply_preset.clicked.connect(self._apply_preset)
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(apply_preset)
        form.addRow("Preset", preset_row)

        self.kw_before_edit = QLineEdit(self._rule.keyword_before)
        self.kw_before_edit.setPlaceholderText("keyword / prefix / frame start")
        form.addRow("Keyword before", self.kw_before_edit)

        self.kw_after_edit = QLineEdit(self._rule.keyword_after)
        self.kw_after_edit.setPlaceholderText("keyword / suffix / frame end")
        form.addRow("Keyword after", self.kw_after_edit)

        self.regex_edit = QLineEdit(self._rule.regex)
        self.regex_edit.setPlaceholderText(r"VBAT[=:]\s*(?P<vbat>[+-]?\d+(?:\.\d+)?)")
        self.regex_edit.textChanged.connect(self._validate_regex)
        form.addRow("Regex", self.regex_edit)

        self.case_cb = QCheckBox("Case sensitive")
        self.case_cb.setChecked(self._rule.case_sensitive)
        form.addRow("", self.case_cb)

        self.emit_combo = QComboBox()
        self.emit_combo.addItems(EMIT_POLICIES)
        self.emit_combo.setCurrentText(self._rule.emit_policy)
        form.addRow("Emit policy", self.emit_combo)

        self.ts_combo = QComboBox()
        self.ts_combo.addItems(TIMESTAMP_MODES)
        self.ts_combo.setCurrentText(self._rule.timestamp_mode)
        form.addRow("Timestamp", self.ts_combo)

        root.addLayout(form)

        self.regex_err = QLabel("")
        self.regex_err.setObjectName("chartError")
        root.addWidget(self.regex_err)

        field_header = QHBoxLayout()
        field_lbl = QLabel("Fields")
        field_header.addWidget(field_lbl)
        field_header.addStretch()
        add_field = QPushButton("+ Field")
        add_field.setAutoDefault(False)
        add_field.clicked.connect(self._add_field)
        edit_field = QPushButton("Edit")
        edit_field.setAutoDefault(False)
        edit_field.clicked.connect(self._edit_field)
        del_field = QPushButton("Delete")
        del_field.setAutoDefault(False)
        del_field.clicked.connect(self._del_field)
        field_header.addWidget(add_field)
        field_header.addWidget(edit_field)
        field_header.addWidget(del_field)
        root.addLayout(field_header)

        self.field_list = QListWidget()
        self.field_list.setFixedHeight(90)
        self.field_list.itemDoubleClicked.connect(lambda *_: self._edit_field())
        root.addWidget(self.field_list)
        self._field_specs = [FieldSpec.from_dict(f.to_dict()) for f in self._rule.field_specs]
        self._reload_fields()

        preview_lbl = QLabel("Preview")
        root.addWidget(preview_lbl)
        self.sample_edit = QLineEdit()
        self.sample_edit.setPlaceholderText("paste a sample RX line to test")
        self.sample_edit.textChanged.connect(self._update_preview)
        root.addWidget(self.sample_edit)
        self.preview_lbl = QLabel("")
        self.preview_lbl.setObjectName("chartHint")
        self.preview_lbl.setWordWrap(True)
        root.addWidget(self.preview_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.setObjectName("chartPrimary")
        ok.setAutoDefault(True)
        ok.setDefault(True)
        ok.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

        self._validate_regex()

    def _apply_preset(self):
        name = self.preset_combo.currentText()
        if name in PRESET_TEMPLATES:
            self.match_combo.setCurrentText("regex")
            self.regex_edit.setText(PRESET_TEMPLATES[name])

    def _validate_regex(self):
        pattern = self.regex_edit.text()
        if not pattern:
            self.regex_err.setText("")
            return True
        try:
            import re
            re.compile(pattern, 0 if self.case_cb.isChecked() else re.IGNORECASE)
            self.regex_err.setText("")
            return True
        except re.error as exc:
            self.regex_err.setText(f"Regex error: {exc}")
            return False

    def _reload_fields(self):
        self.field_list.clear()
        for fs in self._field_specs:
            self.field_list.addItem(f"{fs.name}  ({fs.type})")

    def _add_field(self):
        dlg = _FieldSpecDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._field_specs.append(dlg.result_spec())
            self._reload_fields()

    def _edit_field(self):
        idx = self.field_list.currentRow()
        if idx < 0:
            return
        dlg = _FieldSpecDialog(self, self._field_specs[idx])
        if dlg.exec() == QDialog.Accepted:
            self._field_specs[idx] = dlg.result_spec()
            self._reload_fields()

    def _del_field(self):
        idx = self.field_list.currentRow()
        if idx < 0:
            return
        del self._field_specs[idx]
        self._reload_fields()

    def _update_preview(self):
        sample = self.sample_edit.text()
        if not sample:
            self.preview_lbl.setText("")
            return
        tmp = self._collect_rule()
        cfg = ChartConfig()
        cfg.rules = [tmp]
        from ui.modules.serialCom_module.serial_chart_parser import SerialChartParser
        parser = SerialChartParser(cfg)
        err = parser.compile_error(tmp.rule_id)
        if err:
            self.preview_lbl.setText(f"Regex error: {err}")
            return
        events = parser.feed_line(sample, "active", 0.0)
        if not events:
            self.preview_lbl.setText("No match")
            return
        parts = []
        for ev in events:
            for k, v in ev["fields"].items():
                lbl = ev["labels"].get(k)
                parts.append(f"{k}={v}" + (f" ({lbl})" if lbl else ""))
        self.preview_lbl.setText("Matched: " + ", ".join(parts))

    def _collect_rule(self):
        r = ChartRule.from_dict(self._rule.to_dict())
        r.name = self.name_edit.text().strip() or "Rule"
        r.enabled = self.enabled_cb.isChecked()
        r.source_session = self.session_combo.currentText().strip() or "active"
        r.input_mode = self.input_combo.currentText()
        r.match_mode = self.match_combo.currentText()
        r.keyword_before = self.kw_before_edit.text()
        r.keyword_after = self.kw_after_edit.text()
        r.frame_start = self.kw_before_edit.text()
        r.frame_end = self.kw_after_edit.text()
        r.regex = self.regex_edit.text()
        r.case_sensitive = self.case_cb.isChecked()
        r.emit_policy = self.emit_combo.currentText()
        r.timestamp_mode = self.ts_combo.currentText()
        r.field_specs = [FieldSpec.from_dict(f.to_dict()) for f in self._field_specs]
        return r

    def _on_ok(self):
        if not self._validate_regex():
            QMessageBox.warning(self, "Rule", "Please fix the regex before saving.")
            return
        self._rule = self._collect_rule()
        self.accept()

    def result_rule(self):
        return self._rule


class _SeriesEditorDialog(QDialog):
    def __init__(self, parent=None, series: ChartSeries = None, config: ChartConfig = None):
        super().__init__(parent)
        self.setObjectName("scChartEditor")
        self.setWindowTitle("Series")
        self.setMinimumSize(460, 520)
        _styled_dialog(self)
        self._series = series or ChartSeries()
        self._config = config or ChartConfig()

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit(self._series.name)
        form.addRow("Name", self.name_edit)

        self.enabled_cb = QCheckBox("Enabled")
        self.enabled_cb.setChecked(self._series.enabled)
        form.addRow("", self.enabled_cb)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["field", "derived"])
        self.source_combo.setCurrentText(self._series.source_type)
        self.source_combo.currentTextChanged.connect(self._on_source_changed)
        form.addRow("Source type", self.source_combo)

        self.rule_combo = QComboBox()
        for r in self._config.rules:
            self.rule_combo.addItem(r.name, r.rule_id)
        self._select_data(self.rule_combo, self._series.rule_id)
        self.rule_combo.currentIndexChanged.connect(self._reload_fields)
        form.addRow("Rule", self.rule_combo)

        self.field_combo = QComboBox()
        self.field_combo.setEditable(True)
        form.addRow("Field", self.field_combo)
        self._reload_fields()
        if self._series.field_name:
            self.field_combo.setCurrentText(self._series.field_name)

        self.group_combo = QComboBox()
        self.group_combo.addItems(GROUP_BY_OPTIONS)
        self.group_combo.setCurrentText(self._series.group_by)
        form.addRow("Group by", self.group_combo)

        self.op_combo = QComboBox()
        self.op_combo.addItems(DERIVED_OPERATIONS)
        self.op_combo.setCurrentText(self._series.operation)
        form.addRow("Operation", self.op_combo)

        self.a_combo = QComboBox()
        self.b_combo = QComboBox()
        for s in self._config.series:
            if s.series_id == self._series.series_id:
                continue
            self.a_combo.addItem(s.name, s.series_id)
            self.b_combo.addItem(s.name, s.series_id)
        self._select_data(self.a_combo, self._series.source_a)
        self._select_data(self.b_combo, self._series.source_b)
        form.addRow("Source A", self.a_combo)
        form.addRow("Source B", self.b_combo)

        self.window_spin = QSpinBox()
        self.window_spin.setRange(1, 100000)
        self.window_spin.setValue(self._series.op_window)
        form.addRow("Window N", self.window_spin)

        self.value_spin = QDoubleSpinBox()
        self.value_spin.setRange(-1e9, 1e9)
        self.value_spin.setValue(self._series.op_value)
        form.addRow("Match value", self.value_spin)

        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(-1e9, 1e9)
        self.scale_spin.setDecimals(4)
        self.scale_spin.setValue(self._series.op_scale)
        form.addRow("Scale", self.scale_spin)

        self.chart_combo = QComboBox()
        self.chart_combo.addItems(CHART_TYPES)
        self.chart_combo.setCurrentText(self._series.chart_type)
        form.addRow("Chart type", self.chart_combo)

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["left", "right"])
        self.axis_combo.setCurrentText(self._series.axis)
        form.addRow("Y axis", self.axis_combo)

        color_row = QHBoxLayout()
        self.color_btn = QPushButton(self._series.color)
        self.color_btn.setAutoDefault(False)
        self._set_color(self._series.color)
        self.color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self.color_btn)
        form.addRow("Color", color_row)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(10, 1000000)
        self.max_spin.setValue(self._series.max_points)
        form.addRow("Max points", self.max_spin)

        self.window_s_spin = QDoubleSpinBox()
        self.window_s_spin.setRange(0, 1e6)
        self.window_s_spin.setValue(self._series.time_window_s)
        form.addRow("Time window (s)", self.window_s_spin)

        root.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        cancel.clicked.connect(self.reject)
        ok = QPushButton("OK")
        ok.setObjectName("chartPrimary")
        ok.setAutoDefault(True)
        ok.setDefault(True)
        ok.clicked.connect(self._on_ok)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        root.addLayout(btn_row)

        self._on_source_changed(self._series.source_type)

    @staticmethod
    def _select_data(combo, value):
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return

    def _set_color(self, color):
        self._color = color
        self.color_btn.setText(color)
        self.color_btn.setStyleSheet(
            f"QPushButton {{ background-color: {color}; color: #0B1220; border: none; border-radius: 5px; }}"
        )

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._color), self, "Series color")
        if col.isValid():
            self._set_color(col.name())

    def _on_source_changed(self, mode):
        is_field = mode == "field"
        for w in (self.rule_combo, self.field_combo, self.group_combo):
            w.setEnabled(is_field)
        for w in (self.op_combo, self.a_combo, self.b_combo,
                  self.window_spin, self.value_spin, self.scale_spin):
            w.setEnabled(not is_field)

    def _reload_fields(self):
        self.field_combo.clear()
        rule_id = self.rule_combo.currentData()
        rule = self._config.rule_by_id(rule_id) if rule_id else None
        if rule:
            for fs in rule.field_specs:
                self.field_combo.addItem(fs.name)

    def _on_ok(self):
        s = self._series
        s.name = self.name_edit.text().strip() or "Series"
        s.enabled = self.enabled_cb.isChecked()
        s.source_type = self.source_combo.currentText()
        s.rule_id = self.rule_combo.currentData() or ""
        s.field_name = self.field_combo.currentText().strip()
        s.group_by = self.group_combo.currentText()
        s.operation = self.op_combo.currentText()
        s.source_a = self.a_combo.currentData() or ""
        s.source_b = self.b_combo.currentData() or ""
        s.op_window = self.window_spin.value()
        s.op_value = self.value_spin.value()
        s.op_scale = self.scale_spin.value()
        s.chart_type = self.chart_combo.currentText()
        s.axis = self.axis_combo.currentText()
        s.color = self._color
        s.max_points = self.max_spin.value()
        s.time_window_s = self.window_s_spin.value()
        if s.source_type == "field" and not s.field_name:
            QMessageBox.warning(self, "Series", "Field is required for a field series.")
            return
        self.accept()

    def result_series(self):
        return self._series


class SerialChartDialog(QDialog):
    def __init__(self, parent=None, config: ChartConfig = None, on_config_changed=None):
        super().__init__(parent)
        self.setObjectName("scChartDialog")
        self.setWindowTitle("Serial RX Chart")
        self.setMinimumSize(1040, 660)
        _styled_dialog(self)

        self._config = config if config is not None else ChartConfig()
        self._on_config_changed = on_config_changed
        self._controller = SerialChartController(self._config, self)
        self._plot_items = {}
        self._color_cycle = 0

        import pyqtgraph as pg
        self._pg = pg
        pg.setConfigOptions(antialias=True)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        root.addLayout(self._build_header())

        self._rules_panel = self._build_rules_panel()
        self._series_panel = self._build_series_panel()

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.addWidget(self._rules_panel)
        self._splitter.addWidget(self._build_center())
        self._splitter.addWidget(self._series_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setStretchFactor(2, 0)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setSizes([260, 540, 270])
        root.addWidget(self._splitter, 1)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(CHART_REFRESH_INTERVAL_MS)
        self._refresh_timer.timeout.connect(self._refresh_plots)
        self._refresh_timer.start()

        self._reload_rules()
        self._reload_series()
        self._rebuild_plot_items()

    @property
    def controller(self):
        return self._controller

    def _build_header(self):
        row = QHBoxLayout()
        title = QLabel("Serial RX Chart")
        title.setObjectName("chartTitle")
        row.addWidget(title)

        self.rules_toggle_btn = QPushButton("Rules")
        self.rules_toggle_btn.setObjectName("chartToggle")
        self.rules_toggle_btn.setCheckable(True)
        self.rules_toggle_btn.setChecked(True)
        self.rules_toggle_btn.setAutoDefault(False)
        self.rules_toggle_btn.toggled.connect(self._on_toggle_rules_panel)
        row.addWidget(self.rules_toggle_btn)

        self.series_toggle_btn = QPushButton("Series")
        self.series_toggle_btn.setObjectName("chartToggle")
        self.series_toggle_btn.setCheckable(True)
        self.series_toggle_btn.setChecked(True)
        self.series_toggle_btn.setAutoDefault(False)
        self.series_toggle_btn.toggled.connect(self._on_toggle_series_panel)
        row.addWidget(self.series_toggle_btn)

        row.addStretch()

        self.run_btn = QPushButton("Pause")
        self.run_btn.setObjectName("chartPrimary")
        self.run_btn.setCheckable(True)
        self.run_btn.setAutoDefault(False)
        self.run_btn.clicked.connect(self._on_toggle_run)
        row.addWidget(self.run_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setAutoDefault(False)
        clear_btn.clicked.connect(self._on_clear)
        row.addWidget(clear_btn)

        export_btn = QPushButton("Export")
        export_btn.setAutoDefault(False)
        export_btn.clicked.connect(self._on_export)
        row.addWidget(export_btn)

        import_cfg = QPushButton("Import Cfg")
        import_cfg.setAutoDefault(False)
        import_cfg.clicked.connect(self._on_import_config)
        row.addWidget(import_cfg)

        export_cfg = QPushButton("Export Cfg")
        export_cfg.setAutoDefault(False)
        export_cfg.clicked.connect(self._on_export_config)
        row.addWidget(export_cfg)

        return row

    def _build_rules_panel(self):
        frame = QFrame()
        frame.setObjectName("chartPanel")
        frame.setMinimumWidth(250)
        col = QVBoxLayout(frame)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        title = QLabel("Rules")
        title.setObjectName("chartPanelTitle")
        col.addWidget(title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        for text, slot in (
            ("+", self._add_rule), ("Edit", self._edit_rule),
            ("Copy", self._dup_rule), ("Del", self._del_rule),
            ("On/Off", self._toggle_rule),
        ):
            b = QPushButton(text)
            b.setObjectName("chartPanelBtn")
            b.setAutoDefault(False)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        col.addLayout(btn_row)

        self.rule_list = QListWidget()
        self.rule_list.itemDoubleClicked.connect(lambda *_: self._edit_rule())
        col.addWidget(self.rule_list, 1)

        self.rule_warn = QLabel("")
        self.rule_warn.setObjectName("chartError")
        self.rule_warn.setWordWrap(True)
        col.addWidget(self.rule_warn)
        return frame

    def _build_center(self):
        tabs = QTabWidget()

        plot_host = QWidget()
        plot_layout = QVBoxLayout(plot_host)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_widget = self._pg.PlotWidget()
        self.plot_widget.setBackground("#0B1220")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.addLegend()
        self._plot_item = self.plot_widget.getPlotItem()
        self._right_vb = self._pg.ViewBox()
        self._plot_item.scene().addItem(self._right_vb)
        self._plot_item.getAxis("right").linkToView(self._right_vb)
        self._plot_item.showAxis("right")
        self._right_vb.setXLink(self._plot_item)
        self._plot_item.vb.sigResized.connect(self._sync_right_vb)
        plot_layout.addWidget(self.plot_widget)
        tabs.addTab(plot_host, "Plot")

        table_host = QWidget()
        table_layout = QVBoxLayout(table_host)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.event_table = QTableWidget(0, 3)
        self.event_table.setHorizontalHeaderLabels(["Time", "Rule", "Fields"])
        self.event_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.event_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table_layout.addWidget(self.event_table)
        tabs.addTab(table_host, "Events")
        return tabs

    def _sync_right_vb(self):
        self._right_vb.setGeometry(self._plot_item.vb.sceneBoundingRect())
        self._right_vb.linkedViewChanged(self._plot_item.vb, self._right_vb.XAxis)

    def _on_toggle_rules_panel(self, checked):
        self._rules_panel.setVisible(bool(checked))

    def _on_toggle_series_panel(self, checked):
        self._series_panel.setVisible(bool(checked))

    def _build_series_panel(self):
        frame = QFrame()
        frame.setObjectName("chartPanel")
        frame.setMinimumWidth(250)
        col = QVBoxLayout(frame)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(6)

        title = QLabel("Series")
        title.setObjectName("chartPanelTitle")
        col.addWidget(title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        for text, slot in (
            ("+", self._add_series), ("Edit", self._edit_series),
            ("Del", self._del_series), ("On/Off", self._toggle_series),
        ):
            b = QPushButton(text)
            b.setObjectName("chartPanelBtn")
            b.setAutoDefault(False)
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        col.addLayout(btn_row)

        self.series_list = QListWidget()
        self.series_list.itemDoubleClicked.connect(lambda *_: self._edit_series())
        col.addWidget(self.series_list, 1)
        return frame

    def _on_toggle_run(self, checked):
        self._controller.set_paused(checked)
        self.run_btn.setText("Run" if checked else "Pause")

    def _on_clear(self):
        self._controller.clear()
        for item in self._plot_items.values():
            item.setData([], [])
        self.event_table.setRowCount(0)

    def _next_color(self):
        c = DEFAULT_COLORS[self._color_cycle % len(DEFAULT_COLORS)]
        self._color_cycle += 1
        return c

    def _reload_rules(self):
        self.rule_list.clear()
        for r in self._config.rules:
            mark = "" if r.enabled else "  (off)"
            err = self._controller.parser.compile_error(r.rule_id)
            badge = "  [regex error]" if err else ""
            item = QListWidgetItem(f"{r.name}{mark}{badge}")
            item.setData(Qt.UserRole, r.rule_id)
            self.rule_list.addItem(item)
        if len(self._config.rules) > CHART_RULE_WARN_COUNT:
            self.rule_warn.setText(f"{len(self._config.rules)} rules enabled, performance may degrade.")
        else:
            self.rule_warn.setText("")

    def _reload_series(self):
        self.series_list.clear()
        for s in self._config.series:
            mark = "" if s.enabled else "  (off)"
            kind = s.operation if s.source_type == "derived" else s.field_name
            item = QListWidgetItem(f"{s.name}  [{kind}]{mark}")
            item.setData(Qt.UserRole, s.series_id)
            self.series_list.addItem(item)

    def _selected_rule(self):
        item = self.rule_list.currentItem()
        if not item:
            return None
        return self._config.rule_by_id(item.data(Qt.UserRole))

    def _selected_series(self):
        item = self.series_list.currentItem()
        if not item:
            return None
        return self._config.series_by_id(item.data(Qt.UserRole))

    def _add_rule(self):
        dlg = _RuleEditorDialog(self, ChartRule(), self._controller.parser)
        if dlg.exec() == QDialog.Accepted:
            self._config.rules.append(dlg.result_rule())
            self._commit_config()

    def _edit_rule(self):
        rule = self._selected_rule()
        if not rule:
            return
        dlg = _RuleEditorDialog(self, ChartRule.from_dict(rule.to_dict()), self._controller.parser)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.result_rule()
            for i, r in enumerate(self._config.rules):
                if r.rule_id == rule.rule_id:
                    self._config.rules[i] = updated
                    break
            self._commit_config()

    def _dup_rule(self):
        rule = self._selected_rule()
        if not rule:
            return
        clone = ChartRule.from_dict(rule.to_dict())
        clone.rule_id = new_id("rule")
        clone.name = rule.name + " copy"
        self._config.rules.append(clone)
        self._commit_config()

    def _del_rule(self):
        rule = self._selected_rule()
        if not rule:
            return
        self._config.rules = [r for r in self._config.rules if r.rule_id != rule.rule_id]
        self._commit_config()

    def _toggle_rule(self):
        rule = self._selected_rule()
        if not rule:
            return
        rule.enabled = not rule.enabled
        self._commit_config()

    def _add_series(self):
        s = ChartSeries()
        s.color = self._next_color()
        dlg = _SeriesEditorDialog(self, s, self._config)
        if dlg.exec() == QDialog.Accepted:
            self._config.series.append(dlg.result_series())
            self._commit_config()

    def _edit_series(self):
        series = self._selected_series()
        if not series:
            return
        dlg = _SeriesEditorDialog(self, ChartSeries.from_dict(series.to_dict()), self._config)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.result_series()
            for i, s in enumerate(self._config.series):
                if s.series_id == series.series_id:
                    self._config.series[i] = updated
                    break
            self._commit_config()

    def _del_series(self):
        series = self._selected_series()
        if not series:
            return
        self._config.series = [s for s in self._config.series if s.series_id != series.series_id]
        self._commit_config()

    def _toggle_series(self):
        series = self._selected_series()
        if not series:
            return
        series.enabled = not series.enabled
        self._commit_config()

    def _commit_config(self):
        self._controller.refresh_config()
        self._reload_rules()
        self._reload_series()
        self._rebuild_plot_items()
        if callable(self._on_config_changed):
            try:
                self._on_config_changed()
            except Exception:
                logger.error("chart config changed callback failed", exc_info=True)

    def _rebuild_plot_items(self):
        for item in list(self._plot_items.values()):
            try:
                if item.getViewBox() is self._right_vb:
                    self._right_vb.removeItem(item)
                else:
                    self._plot_item.removeItem(item)
            except Exception:
                pass
        legend = self._plot_item.legend
        if legend is not None:
            legend.clear()
        self._plot_items = {}

    def _ensure_plot_item(self, key, series, suffix=None):
        if key in self._plot_items:
            return self._plot_items[key]
        pg = self._pg
        name = series.name + (f" {suffix}" if suffix else "")
        pen = pg.mkPen(series.color, width=2)
        if series.chart_type == "scatter":
            item = pg.ScatterPlotItem(size=6, brush=pg.mkBrush(series.color), name=name)
        elif series.chart_type == "step":
            item = pg.PlotDataItem(pen=pen, stepMode="right", name=name)
        else:
            item = pg.PlotDataItem(pen=pen, name=name)
        if series.axis == "right":
            self._right_vb.addItem(item)
        else:
            self._plot_item.addItem(item)
        self._plot_items[key] = item
        return item

    def _refresh_plots(self):
        buffers = self._controller.buffers()
        for s in self._config.series:
            if not s.enabled:
                continue
            for key, buf in buffers.items():
                base_id = key.split("::", 1)[0]
                if base_id != s.series_id:
                    continue
                if not buf.dirty:
                    continue
                suffix = key.split("::", 1)[1] if "::" in key else None
                item = self._ensure_plot_item(key, s, suffix)
                xs, ys = buf.data()
                if s.chart_type == "step" and len(xs) >= 1:
                    item.setData(xs + [xs[-1]], ys)
                else:
                    item.setData(xs, ys)
                buf.dirty = False
        self._refresh_events()

    def _refresh_events(self):
        events = self._controller.recent_events
        if self.event_table.rowCount() == len(events):
            return
        self.event_table.setRowCount(0)
        for ev in events[-200:]:
            row = self.event_table.rowCount()
            self.event_table.insertRow(row)
            self.event_table.setItem(row, 0, QTableWidgetItem(f"{ev['rx_time']:.3f}"))
            rule = self._config.rule_by_id(ev["rule_id"])
            self.event_table.setItem(row, 1, QTableWidgetItem(rule.name if rule else ev["rule_id"]))
            fields = ", ".join(f"{k}={v}" for k, v in ev["fields"].items())
            self.event_table.setItem(row, 2, QTableWidgetItem(fields))

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export chart data", "chart_data.json", "JSON (*.json)")
        if not path:
            return
        snapshot = {}
        for key, buf in self._controller.buffers().items():
            xs, ys = buf.data()
            snapshot[key] = {"x": xs, "y": ys}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except OSError:
            logger.error("export chart data failed", exc_info=True)
            QMessageBox.warning(self, "Export", "Failed to write file.")

    def _on_export_config(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export chart config", "chart_config.json", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._config.to_dict(), f, indent=2)
        except OSError:
            logger.error("export chart config failed", exc_info=True)
            QMessageBox.warning(self, "Export", "Failed to write file.")

    def _on_import_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import chart config", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            logger.error("import chart config failed", exc_info=True)
            QMessageBox.warning(self, "Import", "Failed to read config file.")
            return
        new_cfg = ChartConfig.from_dict(data)
        self._config.rules = new_cfg.rules
        self._config.series = new_cfg.series
        self._config.enabled = new_cfg.enabled
        self._config.capture_when_dialog_closed = new_cfg.capture_when_dialog_closed
        self._config.max_points_default = new_cfg.max_points_default
        self._on_clear()
        self._commit_config()

    def closeEvent(self, event):
        try:
            self._refresh_timer.stop()
        except Exception:
            pass
        super().closeEvent(event)
