#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Output Voltage Check 芯片库管理对话框。

ChipManagerDialog：芯片增删改 + rail 摘要表 + 导入/导出；
RailEditDialog：单 rail 表单编辑（Vbit / EFUSE Field / Calibration / Target）。
rail 字段 15+ 且跨字段校验，用嵌套表单对话框而非表格内联编辑。
"""

import copy

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QListWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog, QMessageBox, QFrame,
)

from core.pmu_test.ft_calib_ov.ft_calib_ov_analysis import (
    parse_int_value,
    validate_chip_config,
    validate_rail,
)
from core.pmu_test.ft_calib_ov.ft_calib_ov_store import (
    export_chips,
    import_library_file,
    list_efuse_scripts,
    merge_import,
    save_library,
)
from log_config import get_logger
from resource_path import get_user_data_dir
from ui.theme import apply_qss
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.wheel_line_edit import HexWheelLineEdit, WheelLineEdit

_logger = get_logger(__name__)

_WIDTH_ITEMS = (("8 BIT", 8), ("10 BIT", 10), ("32 BIT", 32), ("8x8 BIT", 88))
_SPEED_ITEMS = (("20 kHz", 20), ("100 kHz", 100), ("400 kHz", 400), ("750 kHz", 750))


def default_chip():
    return {
        "name": "New Chip",
        "i2c": {"device_addr": "0x27", "width_flag": 10, "speed_khz": 100},
        "efuse": {"link": "i2c", "script_filename": "", "chip_name": ""},
        "rails": [],
    }


def default_rail():
    return {
        "name": "NEW_RAIL",
        "type": "LDO",
        "enabled": True,
        "vbit": {"reg_addr": "0x0000", "msb": 7, "lsb": 0, "width_flag": None},
        "efuse_field": {"reg_addr": "0x0000", "msb": 7, "lsb": 0, "signed": False},
        "mode": "offset",
        "base_code": "0x80",
        "offset_lsb": 0,
        "step_mv": 6.25,
        "base_voltage_mv": 900.0,
        "target": {"source": "config", "voltage_mv": 1100.0},
        "tolerance_mv": 20.0,
        "settle_ms": 20,
    }


def _make_section(title):
    frame = QFrame()
    frame.setObjectName("cfgSection")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 8, 10, 10)
    layout.setSpacing(6)
    label = QLabel(title)
    label.setObjectName("cfgSectionTitle")
    layout.addWidget(label)
    return frame, layout


def _field_label(text):
    label = QLabel(text)
    label.setObjectName("fieldLabel")
    return label


def _fill_width_combo(combo, value, allow_inherit=False):
    combo.clear()
    if allow_inherit:
        combo.addItem("Inherit chip", None)
    for text, data in _WIDTH_ITEMS:
        combo.addItem(text, data)
    idx = combo.findData(value)
    combo.setCurrentIndex(idx if idx >= 0 else 0)


def _fill_speed_combo(combo, value):
    combo.clear()
    for text, data in _SPEED_ITEMS:
        combo.addItem(text, data)
    idx = combo.findData(value)
    combo.setCurrentIndex(idx if idx >= 0 else 1)


class RailEditDialog(QDialog):
    """单 rail 表单编辑；OK 时 validate_rail 校验，失败行内提示不关窗。"""

    def __init__(self, rail, efuse_link="i2c", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Rail")
        self.resize(480, 640)
        apply_qss(self, "dialog")
        self._rail = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ---- 基本 ----
        basic_sec, basic = _make_section("Basic")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_field_label("Rail Name"), 0, 0)
        grid.addWidget(_field_label("Type"), 0, 1)
        self.name_edit = QLineEdit(str(rail.get("name", "")))
        self.type_combo = DarkComboBox()
        self.type_combo.addItems(["DCDC", "LDO"])
        self.type_combo.setCurrentText(str(rail.get("type", "LDO")))
        grid.addWidget(self.name_edit, 1, 0)
        grid.addWidget(self.type_combo, 1, 1)
        self.enabled_check = QCheckBox("Enabled")
        self.enabled_check.setChecked(bool(rail.get("enabled", True)))
        grid.addWidget(self.enabled_check, 2, 0, 1, 2)
        basic.addLayout(grid)
        root.addWidget(basic_sec)

        # ---- Vbit ----
        vbit_sec, vbit_lay = _make_section("Vbit Field (output trim register)")
        vbit = rail.get("vbit") or {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_field_label("Reg Addr (hex)"), 0, 0)
        grid.addWidget(_field_label("Width Flag"), 0, 1)
        self.vbit_reg_edit = HexWheelLineEdit(str(vbit.get("reg_addr", "0x0000")))
        self.vbit_width_combo = DarkComboBox()
        _fill_width_combo(self.vbit_width_combo, vbit.get("width_flag"), allow_inherit=True)
        grid.addWidget(self.vbit_reg_edit, 1, 0)
        grid.addWidget(self.vbit_width_combo, 1, 1)
        grid.addWidget(_field_label("MSB"), 2, 0)
        grid.addWidget(_field_label("LSB"), 2, 1)
        self.vbit_msb_spin = QSpinBox()
        self.vbit_msb_spin.setRange(0, 31)
        self.vbit_msb_spin.setValue(int(vbit.get("msb", 7)))
        self.vbit_lsb_spin = QSpinBox()
        self.vbit_lsb_spin.setRange(0, 31)
        self.vbit_lsb_spin.setValue(int(vbit.get("lsb", 0)))
        grid.addWidget(self.vbit_msb_spin, 3, 0)
        grid.addWidget(self.vbit_lsb_spin, 3, 1)
        vbit_lay.addLayout(grid)
        root.addWidget(vbit_sec)

        # ---- EFUSE Field ----
        efuse_sec, efuse_lay = _make_section("EFUSE Field (calibration trim source)")
        field = rail.get("efuse_field") or {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        addr_label = ("EFUSE Offset (hex)" if efuse_link == "script"
                      else "Register Addr (hex)")
        grid.addWidget(_field_label(addr_label), 0, 0)
        grid.addWidget(_field_label("Signed (two's complement)"), 0, 1)
        self.efuse_reg_edit = HexWheelLineEdit(str(field.get("reg_addr", "0x0000")))
        self.efuse_signed_check = QCheckBox("Signed")
        self.efuse_signed_check.setChecked(bool(field.get("signed", False)))
        grid.addWidget(self.efuse_reg_edit, 1, 0)
        grid.addWidget(self.efuse_signed_check, 1, 1)
        grid.addWidget(_field_label("MSB"), 2, 0)
        grid.addWidget(_field_label("LSB"), 2, 1)
        self.efuse_msb_spin = QSpinBox()
        self.efuse_msb_spin.setRange(0, 31)
        self.efuse_msb_spin.setValue(int(field.get("msb", 7)))
        self.efuse_lsb_spin = QSpinBox()
        self.efuse_lsb_spin.setRange(0, 31)
        self.efuse_lsb_spin.setValue(int(field.get("lsb", 0)))
        grid.addWidget(self.efuse_msb_spin, 3, 0)
        grid.addWidget(self.efuse_lsb_spin, 3, 1)
        efuse_lay.addLayout(grid)
        root.addWidget(efuse_sec)

        # ---- Calibration ----
        cal_sec, cal_lay = _make_section("Calibration Code")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_field_label("Mode"), 0, 0)
        grid.addWidget(_field_label("Base Code (hex, offset mode)"), 0, 1)
        self.mode_combo = DarkComboBox()
        self.mode_combo.addItems(["offset", "absolute"])
        self.mode_combo.setCurrentText(str(rail.get("mode", "offset")))
        self.base_code_edit = HexWheelLineEdit(str(rail.get("base_code", "0x80")))
        grid.addWidget(self.mode_combo, 1, 0)
        grid.addWidget(self.base_code_edit, 1, 1)
        grid.addWidget(_field_label("Offset (LSB)"), 2, 0)
        grid.addWidget(_field_label("Step (mV/LSB)"), 2, 1)
        self.offset_edit = WheelLineEdit(str(rail.get("offset_lsb", 0)), wheel_step=1)
        self.step_edit = WheelLineEdit(str(rail.get("step_mv", 6.25)))
        grid.addWidget(self.offset_edit, 3, 0)
        grid.addWidget(self.step_edit, 3, 1)
        grid.addWidget(_field_label("Base Voltage (mV)"), 4, 0)
        self.base_voltage_edit = WheelLineEdit(str(rail.get("base_voltage_mv", 900.0)))
        grid.addWidget(self.base_voltage_edit, 5, 0)
        cal_lay.addLayout(grid)
        root.addWidget(cal_sec)

        # ---- Target & Judge ----
        tgt_sec, tgt_lay = _make_section("Target && Judge")
        target = rail.get("target") or {}
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_field_label("Target Source"), 0, 0)
        grid.addWidget(_field_label("Target Voltage (mV, config)"), 0, 1)
        self.target_source_combo = DarkComboBox()
        self.target_source_combo.addItems(["config", "derived"])
        self.target_source_combo.setCurrentText(str(target.get("source", "config")))
        self.target_voltage_edit = WheelLineEdit(str(target.get("voltage_mv", 1100.0)))
        grid.addWidget(self.target_source_combo, 1, 0)
        grid.addWidget(self.target_voltage_edit, 1, 1)
        grid.addWidget(_field_label("Tolerance (mV)"), 2, 0)
        grid.addWidget(_field_label("Settle Time (ms)"), 2, 1)
        self.tolerance_edit = WheelLineEdit(str(rail.get("tolerance_mv", 20.0)))
        self.settle_edit = WheelLineEdit(str(rail.get("settle_ms", 20)), wheel_step=1)
        grid.addWidget(self.tolerance_edit, 3, 0)
        grid.addWidget(self.settle_edit, 3, 1)
        hint = QLabel("derived target = code x Step + Base Voltage")
        hint.setObjectName("mutedLabel")
        grid.addWidget(hint, 4, 0, 1, 2)
        tgt_lay.addLayout(grid)
        root.addWidget(tgt_sec)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5e7a; border: none;")
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.setAutoDefault(False)
        self.cancel_btn.setAutoDefault(False)
        self.cancel_btn.setDefault(True)
        btn_row.addWidget(self.ok_btn)
        btn_row.addWidget(self.cancel_btn)
        root.addLayout(btn_row)

        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)
        self.mode_combo.currentTextChanged.connect(self._update_mode_visibility)
        self.target_source_combo.currentTextChanged.connect(self._update_target_visibility)
        self._update_mode_visibility()
        self._update_target_visibility()

    def _update_mode_visibility(self):
        self.base_code_edit.setEnabled(self.mode_combo.currentText() == "offset")

    def _update_target_visibility(self):
        self.target_voltage_edit.setEnabled(
            self.target_source_combo.currentText() == "config")

    def _collect(self):
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "enabled": self.enabled_check.isChecked(),
            "vbit": {
                "reg_addr": self.vbit_reg_edit.text().strip(),
                "msb": self.vbit_msb_spin.value(),
                "lsb": self.vbit_lsb_spin.value(),
                "width_flag": self.vbit_width_combo.currentData(),
            },
            "efuse_field": {
                "reg_addr": self.efuse_reg_edit.text().strip(),
                "msb": self.efuse_msb_spin.value(),
                "lsb": self.efuse_lsb_spin.value(),
                "signed": self.efuse_signed_check.isChecked(),
            },
            "mode": self.mode_combo.currentText(),
            "base_code": self.base_code_edit.text().strip(),
            "offset_lsb": int(float(self.offset_edit.text().strip() or 0)),
            "step_mv": float(self.step_edit.text().strip()),
            "base_voltage_mv": float(self.base_voltage_edit.text().strip()),
            "target": {
                "source": self.target_source_combo.currentText(),
                "voltage_mv": float(self.target_voltage_edit.text().strip() or 0),
            },
            "tolerance_mv": float(self.tolerance_edit.text().strip()),
            "settle_ms": int(float(self.settle_edit.text().strip() or 0)),
        }

    def _on_ok(self):
        try:
            rail = self._collect()
        except (TypeError, ValueError):
            self.error_label.setText("Invalid numeric input, please check all fields.")
            return
        try:
            validate_rail(rail)
        except ValueError as e:
            self.error_label.setText(str(e))
            return
        self._rail = rail
        self.accept()

    def result_rail(self):
        return self._rail


class ChipManagerDialog(QDialog):
    """芯片库管理：左芯片列表，右芯片级表单 + rail 摘要表，底部导入/导出。"""

    chips_changed = Signal()

    def __init__(self, chips, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chip Library Manager")
        self.resize(880, 620)
        apply_qss(self, "dialog")
        self._chips = copy.deepcopy(list(chips))
        self._current_idx = -1

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        body = QHBoxLayout()
        body.setSpacing(10)
        root.addLayout(body, 1)

        # ---- 左：芯片列表 ----
        left = QVBoxLayout()
        left.setSpacing(6)
        left.addWidget(_field_label("Chips"))
        self.chip_list = QListWidget()
        self.chip_list.setFixedWidth(190)
        left.addWidget(self.chip_list, 1)
        chip_btn_row = QHBoxLayout()
        chip_btn_row.setSpacing(6)
        self.add_chip_btn = QPushButton("Add")
        self.dup_chip_btn = QPushButton("Duplicate")
        self.remove_chip_btn = QPushButton("Remove")
        for btn in (self.add_chip_btn, self.dup_chip_btn, self.remove_chip_btn):
            chip_btn_row.addWidget(btn)
        left.addLayout(chip_btn_row)
        body.addLayout(left)

        # ---- 右：芯片表单 + rail 表 ----
        right = QVBoxLayout()
        right.setSpacing(8)
        body.addLayout(right, 1)

        chip_sec, chip_lay = _make_section("Chip Settings")
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.addWidget(_field_label("Chip Name"), 0, 0)
        grid.addWidget(_field_label("I2C Device Addr (hex)"), 0, 1)
        self.chip_name_edit = QLineEdit()
        self.dev_addr_edit = HexWheelLineEdit("0x27")
        grid.addWidget(self.chip_name_edit, 1, 0)
        grid.addWidget(self.dev_addr_edit, 1, 1)
        grid.addWidget(_field_label("I2C Width Flag"), 2, 0)
        grid.addWidget(_field_label("I2C Speed"), 2, 1)
        self.width_combo = DarkComboBox()
        _fill_width_combo(self.width_combo, 10)
        self.speed_combo = DarkComboBox()
        _fill_speed_combo(self.speed_combo, 100)
        grid.addWidget(self.width_combo, 3, 0)
        grid.addWidget(self.speed_combo, 3, 1)
        grid.addWidget(_field_label("EFUSE Link"), 4, 0)
        grid.addWidget(_field_label("EFUSE Script File"), 4, 1)
        self.efuse_link_combo = DarkComboBox()
        self.efuse_link_combo.addItems(["script", "i2c"])
        self.efuse_script_combo = DarkComboBox()
        self.efuse_script_combo.addItems(list_efuse_scripts())
        grid.addWidget(self.efuse_link_combo, 5, 0)
        grid.addWidget(self.efuse_script_combo, 5, 1)
        grid.addWidget(_field_label("EFUSE Chip Name (script inject)"), 6, 0)
        grid.addWidget(_field_label("EFUSE Device Addr (hex)"), 6, 1)
        self.efuse_chip_name_edit = QLineEdit()
        self.efuse_dev_addr_edit = HexWheelLineEdit("0x27")
        grid.addWidget(self.efuse_chip_name_edit, 7, 0)
        grid.addWidget(self.efuse_dev_addr_edit, 7, 1)
        chip_lay.addLayout(grid)
        right.addWidget(chip_sec)

        rail_sec, rail_lay = _make_section("Rails (DCDC / LDO)")
        self.rail_table = QTableWidget(0, 6)
        self.rail_table.setHorizontalHeaderLabels(
            ["Rail", "Type", "Mode", "Vbit", "Target (mV)", "Tol (mV)"])
        self.rail_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.rail_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.rail_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.rail_table.verticalHeader().setVisible(False)
        header = self.rail_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        rail_lay.addWidget(self.rail_table, 1)
        rail_btn_row = QHBoxLayout()
        rail_btn_row.setSpacing(6)
        self.add_rail_btn = QPushButton("Add Rail")
        self.edit_rail_btn = QPushButton("Edit Rail")
        self.remove_rail_btn = QPushButton("Remove Rail")
        rail_btn_row.addWidget(self.add_rail_btn)
        rail_btn_row.addWidget(self.edit_rail_btn)
        rail_btn_row.addWidget(self.remove_rail_btn)
        rail_btn_row.addStretch(1)
        rail_lay.addLayout(rail_btn_row)
        right.addWidget(rail_sec, 1)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #ff5e7a; border: none;")
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.import_btn = QPushButton("Import...")
        self.export_btn = QPushButton("Export...")
        bottom.addWidget(self.import_btn)
        bottom.addWidget(self.export_btn)
        bottom.addStretch(1)
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.setAutoDefault(False)
        self.cancel_btn.setAutoDefault(False)
        self.cancel_btn.setDefault(True)
        bottom.addWidget(self.ok_btn)
        bottom.addWidget(self.cancel_btn)
        root.addLayout(bottom)

        self.chip_list.currentRowChanged.connect(self._on_chip_selected)
        self.add_chip_btn.clicked.connect(self._on_add_chip)
        self.dup_chip_btn.clicked.connect(self._on_duplicate_chip)
        self.remove_chip_btn.clicked.connect(self._on_remove_chip)
        self.add_rail_btn.clicked.connect(self._on_add_rail)
        self.edit_rail_btn.clicked.connect(self._on_edit_rail)
        self.remove_rail_btn.clicked.connect(self._on_remove_rail)
        self.rail_table.cellDoubleClicked.connect(lambda _r, _c: self._on_edit_rail())
        self.efuse_link_combo.currentTextChanged.connect(self._update_efuse_visibility)
        self.import_btn.clicked.connect(self._on_import)
        self.export_btn.clicked.connect(self._on_export)
        self.ok_btn.clicked.connect(self._on_ok)
        self.cancel_btn.clicked.connect(self.reject)

        self._refresh_chip_list()
        if self._chips:
            self.chip_list.setCurrentRow(0)
        else:
            self._set_form_enabled(False)

    # ------------------------------------------------------------------
    # 芯片列表 / 表单
    # ------------------------------------------------------------------

    def _refresh_chip_list(self, select_name=None):
        self.chip_list.blockSignals(True)
        self.chip_list.clear()
        for chip in self._chips:
            self.chip_list.addItem(str(chip.get("name", "")))
        self.chip_list.blockSignals(False)
        if select_name is not None:
            for i, chip in enumerate(self._chips):
                if chip.get("name") == select_name:
                    self.chip_list.setCurrentRow(i)
                    return
        if self._chips and self._current_idx < 0:
            self.chip_list.setCurrentRow(0)

    def _set_form_enabled(self, enabled):
        for widget in (self.chip_name_edit, self.dev_addr_edit, self.width_combo,
                       self.speed_combo, self.efuse_link_combo, self.efuse_script_combo,
                       self.efuse_chip_name_edit, self.efuse_dev_addr_edit,
                       self.add_rail_btn, self.edit_rail_btn, self.remove_rail_btn,
                       self.dup_chip_btn, self.remove_chip_btn):
            widget.setEnabled(enabled)

    def _on_chip_selected(self, row):
        if row < 0 or row >= len(self._chips):
            self._current_idx = -1
            self._set_form_enabled(False)
            return
        if self._current_idx >= 0 and row != self._current_idx:
            self._store_form_to_chip()
        self._current_idx = row
        self._set_form_enabled(True)
        chip = self._chips[row]
        i2c = chip.get("i2c") or {}
        efuse = chip.get("efuse") or {}
        self.chip_name_edit.setText(str(chip.get("name", "")))
        self.dev_addr_edit.setText(str(i2c.get("device_addr", "0x27")))
        _fill_width_combo(self.width_combo, i2c.get("width_flag", 10))
        _fill_speed_combo(self.speed_combo, i2c.get("speed_khz", 100))
        self.efuse_link_combo.setCurrentText(str(efuse.get("link", "i2c")))
        script = str(efuse.get("script_filename", ""))
        idx = self.efuse_script_combo.findText(script)
        if idx >= 0:
            self.efuse_script_combo.setCurrentIndex(idx)
        self.efuse_chip_name_edit.setText(str(efuse.get("chip_name", "")))
        self.efuse_dev_addr_edit.setText(
            str(efuse.get("device_addr", i2c.get("device_addr", "0x27"))))
        self._update_efuse_visibility()
        self._refresh_rail_table()

    def _update_efuse_visibility(self):
        is_script = self.efuse_link_combo.currentText() == "script"
        self.efuse_script_combo.setEnabled(is_script)
        self.efuse_chip_name_edit.setEnabled(is_script)

    def _store_form_to_chip(self):
        if not (0 <= self._current_idx < len(self._chips)):
            return
        chip = self._chips[self._current_idx]
        chip["name"] = self.chip_name_edit.text().strip()
        chip["i2c"] = {
            "device_addr": self.dev_addr_edit.text().strip(),
            "width_flag": self.width_combo.currentData(),
            "speed_khz": self.speed_combo.currentData(),
        }
        efuse = chip.setdefault("efuse", {})
        efuse["link"] = self.efuse_link_combo.currentText()
        efuse["script_filename"] = self.efuse_script_combo.currentText()
        efuse["chip_name"] = self.efuse_chip_name_edit.text().strip()
        efuse["device_addr"] = self.efuse_dev_addr_edit.text().strip()
        efuse["width_flag"] = chip["i2c"]["width_flag"]
        efuse["speed_khz"] = chip["i2c"]["speed_khz"]

    def _on_add_chip(self):
        self._store_form_to_chip()
        chip = default_chip()
        base_name = chip["name"]
        existing = {str(c.get("name", "")) for c in self._chips}
        n = 1
        while chip["name"] in existing:
            n += 1
            chip["name"] = f"{base_name} {n}"
        self._chips.append(chip)
        self._refresh_chip_list(chip["name"])

    def _on_duplicate_chip(self):
        if not (0 <= self._current_idx < len(self._chips)):
            return
        self._store_form_to_chip()
        chip = copy.deepcopy(self._chips[self._current_idx])
        chip["name"] = f"{chip.get('name', '')} (copy)"
        self._chips.append(chip)
        self._refresh_chip_list(chip["name"])

    def _on_remove_chip(self):
        if not (0 <= self._current_idx < len(self._chips)):
            return
        chip = self._chips[self._current_idx]
        box = QMessageBox(self)
        box.setWindowTitle("Remove Chip")
        box.setIcon(QMessageBox.Question)
        box.setText(f"Remove chip '{chip.get('name', '')}' and all its rails?")
        yes_btn = box.addButton("Remove", QMessageBox.YesRole)
        no_btn = box.addButton("Cancel", QMessageBox.NoRole)
        box.setDefaultButton(no_btn)
        box.setEscapeButton(no_btn)
        apply_qss(box, "dialog")
        box.exec()
        if box.clickedButton() is not yes_btn:
            return
        del self._chips[self._current_idx]
        self._current_idx = -1
        self._refresh_chip_list()
        if not self._chips:
            self._set_form_enabled(False)
            self.rail_table.setRowCount(0)

    # ------------------------------------------------------------------
    # rail 表 / 编辑
    # ------------------------------------------------------------------

    def _refresh_rail_table(self):
        chip = self._chips[self._current_idx]
        rails = chip.get("rails") or []
        self.rail_table.setRowCount(len(rails))
        for row, rail in enumerate(rails):
            vbit = rail.get("vbit") or {}
            target = rail.get("target") or {}
            target_text = (f"{target.get('voltage_mv', 0):g}"
                           if target.get("source") == "config" else "derived")
            values = [
                str(rail.get("name", "")),
                str(rail.get("type", "")),
                str(rail.get("mode", "")),
                f"{vbit.get('reg_addr', '')} [{vbit.get('msb', '')}:{vbit.get('lsb', '')}]",
                target_text,
                f"{rail.get('tolerance_mv', 0):g}",
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                if col == 0 and not rail.get("enabled", True):
                    item.setForeground(Qt.gray)
                self.rail_table.setItem(row, col, item)

    def _current_rail_index(self):
        row = self.rail_table.currentRow()
        chip = self._chips[self._current_idx]
        rails = chip.get("rails") or []
        if 0 <= row < len(rails):
            return row
        return -1

    def _on_add_rail(self):
        if not (0 <= self._current_idx < len(self._chips)):
            return
        dlg = RailEditDialog(default_rail(),
                             efuse_link=self.efuse_link_combo.currentText(), parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._chips[self._current_idx].setdefault("rails", []).append(dlg.result_rail())
            self._refresh_rail_table()

    def _on_edit_rail(self):
        idx = self._current_rail_index()
        if idx < 0:
            return
        chip = self._chips[self._current_idx]
        dlg = RailEditDialog(copy.deepcopy(chip["rails"][idx]),
                             efuse_link=self.efuse_link_combo.currentText(), parent=self)
        if dlg.exec() == QDialog.Accepted:
            chip["rails"][idx] = dlg.result_rail()
            self._refresh_rail_table()

    def _on_remove_rail(self):
        idx = self._current_rail_index()
        if idx < 0:
            return
        chip = self._chips[self._current_idx]
        rail = chip["rails"][idx]
        box = QMessageBox(self)
        box.setWindowTitle("Remove Rail")
        box.setIcon(QMessageBox.Question)
        box.setText(f"Remove rail '{rail.get('name', '')}'?")
        yes_btn = box.addButton("Remove", QMessageBox.YesRole)
        no_btn = box.addButton("Cancel", QMessageBox.NoRole)
        box.setDefaultButton(no_btn)
        box.setEscapeButton(no_btn)
        apply_qss(box, "dialog")
        box.exec()
        if box.clickedButton() is yes_btn:
            del chip["rails"][idx]
            self._refresh_rail_table()

    # ------------------------------------------------------------------
    # 导入 / 导出 / 确认
    # ------------------------------------------------------------------

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Chip Library", get_user_data_dir("ft_calib_ov_chips"),
            "JSON Files (*.json)")
        if not path:
            return
        try:
            incoming = import_library_file(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Import Failed", f"Invalid chip library file:\n{e}")
            return
        self._store_form_to_chip()
        merged, conflicts = merge_import(self._chips, incoming)
        if conflicts:
            box = QMessageBox(self)
            box.setWindowTitle("Import Conflicts")
            box.setIcon(QMessageBox.Question)
            box.setText(
                "Chips with the same name will be overwritten:\n"
                + ", ".join(conflicts) + "\n\nContinue?")
            yes_btn = box.addButton("Overwrite", QMessageBox.YesRole)
            no_btn = box.addButton("Cancel", QMessageBox.NoRole)
            box.setDefaultButton(no_btn)
            box.setEscapeButton(no_btn)
            apply_qss(box, "dialog")
            box.exec()
            if box.clickedButton() is not yes_btn:
                return
        self._chips = merged
        self._current_idx = -1
        self._refresh_chip_list()

    def _on_export(self):
        self._store_form_to_chip()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chip Library",
            f"{get_user_data_dir('ft_calib_ov_chips')}/chip_library.json",
            "JSON Files (*.json)")
        if not path:
            return
        try:
            export_chips(self._chips, path)
        except (OSError, TypeError, ValueError) as e:
            QMessageBox.warning(self, "Export Failed", str(e))
            return
        self.error_label.setText("")

    def _on_ok(self):
        self._store_form_to_chip()
        names = set()
        for chip in self._chips:
            name = str(chip.get("name", "")).strip()
            if not name:
                self.error_label.setText("Chip name must not be empty.")
                return
            if name in names:
                self.error_label.setText(f"Duplicate chip name: {name}")
                return
            names.add(name)
            try:
                validate_chip_config(chip)
            except ValueError as e:
                self.error_label.setText(str(e))
                return
        try:
            save_library(self._chips)
        except (OSError, TypeError, ValueError) as e:
            self.error_label.setText(f"Failed to save chip library: {e}")
            return
        self.chips_changed.emit()
        self.accept()

    def result_chips(self):
        return self._chips
