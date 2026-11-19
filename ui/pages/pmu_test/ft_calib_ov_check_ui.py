#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FT Calibration Check - Output Voltage Check 子页。

芯片管理（每芯片多 DCDC/LDO rail）→ 读 EFUSE → 偏移/绝对双模式校准码 →
写 Vbit 位域调压 → DMM / N6705C VMeter 测压 → 容差判定 PASS/FAIL。
业务在 core/pmu_test/ft_calib_ov（analysis + store + worker），UI 仅交互。
"""

import copy
import csv
import os
import threading
from datetime import datetime
from typing import Any

import pyqtgraph as pg
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QSpinBox, QCheckBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog,
)

from core.ai.page_contract import (
    CAP_APPLY_CONFIG,
    CAP_GET_CONFIG,
    CAP_GET_RESULT,
    CAP_START_TEST,
    CAP_STOP_TEST,
)
from core.pmu_test.ft_calib_ov.ft_calib_ov_analysis import validate_chip_config, validate_rail
from core.pmu_test.ft_calib_ov.ft_calib_ov_store import load_library, save_library
from core.pmu_test.ft_calib_ov.ft_calib_ov_worker import FtCalibOvWorker
from debug_config import DEBUG_MOCK
from log_config import get_logger
from resource_path import get_resource_base
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.pages.pmu_test.ft_calib_ov_chip_dialog import ChipManagerDialog
from ui.pages.pmu_test.ft_calib_ov_dmm_card import DmmConnectionCard
from ui.styles import SCROLLBAR_STYLE, START_BTN_STYLE, get_page_base_qss, get_table_qss
from ui.widgets.config_memory import ConfigMemory
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.start_sequence import update_start_btn_state
from ui.widgets.wheel_line_edit import HexWheelLineEdit, WheelLineEdit

_logger = get_logger(__name__)

_AI_HIGHLIGHT_QSS = "border: 1px solid #15d1a3;"
_AI_HIGHLIGHT_MS = 1500

_INSTR_DMM = "dmm"
_INSTR_VMETER = "vmeter"

# 线程收尾引用池：脱离页面父级，线程结束后由事件循环异步回收（禁 UI 线程 wait）
_RETIRED_THREADS = {}


def _retire_thread(thread, worker=None):
    _RETIRED_THREADS[thread] = worker
    thread.setParent(None)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(lambda: _RETIRED_THREADS.pop(thread, None))
    thread.quit()
    if not thread.isRunning():
        _RETIRED_THREADS.pop(thread, None)
        thread.deleteLater()


class _Card(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)
        self.title_row = None
        self.title_label = None
        if title:
            self.title_row = QHBoxLayout()
            self.title_row.setSpacing(8)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.title_row.addWidget(self.title_label)
            self.title_row.addStretch()
            self.main_layout.addLayout(self.title_row)


class FtCalibOvCheckUI(N6705CConnectionMixin, QWidget):
    """Output Voltage Check：EFUSE 校准码调压后的逐 rail 输出电压验证。"""

    sequence_execution_finished = Signal(bool, str)

    def __init__(self, n6705c_top=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._ui_action_registry = ui_action_registry
        self._instrument_manager = instrument_manager
        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)

        self.is_test_running = False
        self.test_thread = None
        self._test_worker = None
        self._test_stop_requested = False
        self._rail_results = []
        self._last_summary = None
        self._test_mode = "ft_calib_ov"
        self._test_id = ""
        self._chip_library = load_library()
        self._rail_loading = False

        self._setup_style()
        self._create_layout()
        self._bind_signals()
        self._refresh_chip_combo()
        self.sync_n6705c_from_top()
        self.append_log("[SYSTEM] Output Voltage Check ready.")

        self._config_memory = ConfigMemory("pmu_test/ft_calib_ov", self)
        self._config_memory.bind_interface(
            self.get_test_config,
            lambda cfg: self.apply_config_to_controls(cfg, silent=True),
        )
        self._config_memory.watch(self)
        self._config_memory.restore()

    # ------------------------------------------------------------------
    # 样式 / 布局
    # ------------------------------------------------------------------

    def _setup_style(self):
        page_extra = """
            QLabel#metricLabel {
                color: #9db6db;
                font-size: 12px;
                background-color: transparent;
            }
            QLabel#metricValue {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                background-color: transparent;
            }
            QFrame#miniStatCard {
                background-color: #0a1733;
                border: 1px solid #1b315f;
                border-radius: 12px;
            }
            QWidget#resultContainer {
                background-color: #020817;
            }
            QFrame#chartContainer {
                background-color: #09142e;
                border: 1px solid #1a2d57;
                border-radius: 16px;
            }
            QPushButton#manageChipsBtn {
                min-height: 22px;
                max-height: 22px;
                padding: 2px 10px;
            }
            QPushButton#exportBtn {
                min-height: 22px;
                max-height: 22px;
                padding: 2px 12px;
            }
        """
        self.setStyleSheet(get_page_base_qss() + START_BTN_STYLE + page_extra)

    def _create_layout(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ---- 左配置 / 右（Chip + 结果） ----
        content = QHBoxLayout()
        content.setSpacing(14)
        root.addLayout(content, 1)

        # ---- 左：仪器等配置 ----
        left_wrapper = QVBoxLayout()
        left_wrapper.setContentsMargins(0, 0, 0, 0)
        left_wrapper.setSpacing(8)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setFixedWidth(340)
        self.left_scroll.setObjectName("leftScrollArea")
        self.left_scroll.setStyleSheet("""
            QScrollArea#leftScrollArea {
                background-color: #08132d;
                border: 1px solid #16274d;
                border-radius: 16px;
            }
        """ + SCROLLBAR_STYLE)

        left_panel = QWidget()
        left_panel.setObjectName("leftPanelInner")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        self.measure_card = _Card("Measurement")
        self._build_measure_card()
        left_layout.addWidget(self.measure_card)

        self.options_card = _Card("Options")
        self._build_options_card()
        left_layout.addWidget(self.options_card)

        left_layout.addStretch()
        self.left_scroll.setWidget(left_panel)
        left_wrapper.addWidget(self.left_scroll, 1)

        self.start_test_btn = QPushButton("▷ Start Check")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_wrapper.addWidget(self.start_test_btn)
        self.stop_test_btn = QPushButton("■ Stop")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()
        content.addLayout(left_wrapper)

        # ---- 右：Chip（顶部） + 结果 ----
        right_wrapper = QVBoxLayout()
        right_wrapper.setContentsMargins(0, 0, 0, 0)
        right_wrapper.setSpacing(10)

        self.chip_card = _Card("Chip")
        self._build_chip_card()
        right_wrapper.addWidget(self.chip_card)

        # ---- 右：结果 ----
        self.result_container = QWidget()
        self.result_container.setObjectName("resultContainer")
        self.result_container.setAttribute(Qt.WA_StyledBackground, True)
        right_layout = QVBoxLayout(self.result_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(10)
        self.rails_card = self._create_mini_stat("Rails", "---")
        self.passed_card = self._create_mini_stat("Passed", "---")
        self.failed_card = self._create_mini_stat("Failed", "---")
        self.max_err_card = self._create_mini_stat("Max |Error| (mV)", "---")
        self.verdict_card = self._create_mini_stat("Result", "---")
        for card in (self.rails_card, self.passed_card, self.failed_card,
                     self.max_err_card, self.verdict_card):
            metrics_row.addWidget(card["frame"])
        right_layout.addLayout(metrics_row)

        table_header = QHBoxLayout()
        table_title = QLabel("Per-Rail Results")
        table_title.setObjectName("sectionTitle")
        table_header.addWidget(table_title)
        table_header.addStretch()
        self.export_csv_btn = QPushButton("⇩ Export CSV")
        self.export_csv_btn.setObjectName("exportBtn")
        table_header.addWidget(self.export_csv_btn)
        right_layout.addLayout(table_header)

        self.result_table = QTableWidget(0, 9)
        self.result_table.setHorizontalHeaderLabels(
            ["Rail", "Type", "EFUSE (LSB)", "Code", "Target (mV)",
             "Measured (mV)", "Error (mV)", "Tol (mV)", "Verdict"])
        self.result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setStyleSheet(get_table_qss())
        right_layout.addWidget(self.result_table, 2)

        self.error_plot = pg.PlotWidget()
        self.error_plot.setBackground("#09142e")
        self.error_plot.showGrid(x=True, y=True, alpha=0.25)
        self.error_plot.setLabel("left", "Error (mV)")
        self.error_plot.setLabel("bottom", "Rail")
        self._error_scatter = pg.ScatterPlotItem(size=9, brush=pg.mkBrush("#4cc9f0"))
        self._error_bars = pg.ErrorBarItem(pen=pg.mkPen("#8a93a6", width=1))
        self._zero_line = pg.InfiniteLine(angle=0, pen=pg.mkPen("#5b5cf6", style=Qt.DashLine))
        self.error_plot.addItem(self._error_scatter)
        self.error_plot.addItem(self._error_bars)
        self.error_plot.addItem(self._zero_line)
        right_layout.addWidget(self.error_plot, 2)

        splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            self.result_container, show_progress=True, stretch=(4, 1)
        )
        self.log_edit = self.execution_logs.log_edit
        self.progress_bar = self.execution_logs.progress_bar
        right_wrapper.addWidget(splitter, 1)
        content.addLayout(right_wrapper, 1)

    def _build_chip_card(self):
        layout = self.chip_card.main_layout
        row = QHBoxLayout()
        row.setSpacing(6)
        self.chip_combo = DarkComboBox()
        row.addWidget(self.chip_combo, 1)
        self.manage_chips_btn = QPushButton("Manage Chips...")
        self.manage_chips_btn.setObjectName("manageChipsBtn")
        row.addWidget(self.manage_chips_btn)
        layout.addLayout(row)

        # ---- DUT 单选（先只支持 1 路校准/测试） ----
        dut_row = QHBoxLayout()
        dut_row.setSpacing(6)
        dut_label = QLabel("DUT (Rail)")
        dut_label.setObjectName("fieldLabel")
        dut_row.addWidget(dut_label)
        self.dut_combo = DarkComboBox()
        dut_row.addWidget(self.dut_combo, 1)
        self.rail_meta_label = QLabel("")
        self.rail_meta_label.setObjectName("mutedLabel")
        dut_row.addWidget(self.rail_meta_label)
        layout.addLayout(dut_row)

        # ---- EFUSE / Vbit 地址与配置（可编辑，落库） ----
        self.efuse_addr_edit = HexWheelLineEdit()
        self.efuse_addr_edit.setPlaceholderText("0x0000")
        self.efuse_msb_spin = QSpinBox()
        self.efuse_msb_spin.setRange(0, 31)
        self.efuse_lsb_spin = QSpinBox()
        self.efuse_lsb_spin.setRange(0, 31)
        self.efuse_sign_bit_spin = QSpinBox()
        self.efuse_sign_bit_spin.setRange(-1, 31)
        self.efuse_sign_bit_spin.setToolTip(
            "-1 = no sign bit; >= 0 = sign-magnitude sign bit index")

        self.vbit_addr_edit = HexWheelLineEdit()
        self.vbit_addr_edit.setPlaceholderText("0x0000")
        self.vbit_msb_spin = QSpinBox()
        self.vbit_msb_spin.setRange(0, 31)
        self.vbit_lsb_spin = QSpinBox()
        self.vbit_lsb_spin.setRange(0, 31)
        self.mode_combo = DarkComboBox()
        self.mode_combo.addItem("offset", "offset")
        self.mode_combo.addItem("absolute", "absolute")

        self.base_code_edit = HexWheelLineEdit()
        self.base_code_edit.setPlaceholderText("0x00")
        self.offset_lsb_edit = WheelLineEdit(wheel_step=1)
        self.target_mv_edit = WheelLineEdit(wheel_step=1)
        self.tolerance_edit = WheelLineEdit(wheel_step=0.5)

        fields = [
            ("EFUSE Addr (hex)", self.efuse_addr_edit),
            ("EFUSE MSB", self.efuse_msb_spin),
            ("EFUSE LSB", self.efuse_lsb_spin),
            ("Sign Bit (-1 = none)", self.efuse_sign_bit_spin),
            ("Vbit Addr (hex)", self.vbit_addr_edit),
            ("Vbit MSB", self.vbit_msb_spin),
            ("Vbit LSB", self.vbit_lsb_spin),
            ("Mode", self.mode_combo),
            ("Base Code (hex)", self.base_code_edit),
            ("Offset (LSB)", self.offset_lsb_edit),
            ("Target (mV)", self.target_mv_edit),
            ("Tol (mV)", self.tolerance_edit),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(4)
        for index, (text, widget) in enumerate(fields):
            row_idx, col = divmod(index, 4)
            label = QLabel(text)
            label.setObjectName("fieldLabel")
            grid.addWidget(label, row_idx * 2, col)
            grid.addWidget(widget, row_idx * 2 + 1, col)
            grid.setColumnStretch(col, 1)
        layout.addLayout(grid)

        self.chip_hint_label = QLabel("No chips configured. Click Manage Chips to add.")
        self.chip_hint_label.setObjectName("mutedLabel")
        self.chip_hint_label.setWordWrap(True)
        layout.addWidget(self.chip_hint_label)

    def _config_editors(self):
        return (
            self.efuse_addr_edit, self.efuse_msb_spin, self.efuse_lsb_spin,
            self.efuse_sign_bit_spin, self.vbit_addr_edit, self.vbit_msb_spin,
            self.vbit_lsb_spin, self.mode_combo, self.base_code_edit,
            self.offset_lsb_edit, self.target_mv_edit, self.tolerance_edit,
        )

    def _build_measure_card(self):
        layout = self.measure_card.main_layout
        instr_label = QLabel("Measure Instrument")
        instr_label.setObjectName("fieldLabel")
        layout.addWidget(instr_label)
        self.measure_instr_combo = DarkComboBox()
        self.measure_instr_combo.addItem("Keysight 34461A (DMM)", _INSTR_DMM)
        self.measure_instr_combo.addItem("N6705C VMeter", _INSTR_VMETER)
        layout.addWidget(self.measure_instr_combo)

        self.dmm_card = DmmConnectionCard()
        layout.addWidget(self.dmm_card)

        self.n6705c_card = _Card("N6705C Power Supply")
        self.register_power_title_card(
            self.n6705c_card, default_title="N6705C Power Supply",
            connected_fmt="{model}",
        )
        self.build_n6705c_connection_widgets(
            self.n6705c_card.main_layout, title_row=self.n6705c_card.title_row,
        )
        ch_row = QHBoxLayout()
        ch_row.setSpacing(6)
        ch_label = QLabel("VMeter Channel")
        ch_label.setObjectName("fieldLabel")
        ch_row.addWidget(ch_label)
        self.vmeter_channel_combo = DarkComboBox()
        self.register_power_channel_combo(self.vmeter_channel_combo, text_fmt="CH {}")
        self.vmeter_channel_combo.setCurrentIndex(1)
        ch_row.addWidget(self.vmeter_channel_combo, 1)
        self.n6705c_card.main_layout.addLayout(ch_row)
        layout.addWidget(self.n6705c_card)

        self.dmm_params_frame = QFrame()
        dmm_grid = QGridLayout(self.dmm_params_frame)
        dmm_grid.setContentsMargins(0, 0, 0, 0)
        dmm_grid.setHorizontalSpacing(8)
        dmm_grid.setVerticalSpacing(6)
        samples_label = QLabel("Samples")
        samples_label.setObjectName("fieldLabel")
        self.dmm_samples_spin = QSpinBox()
        self.dmm_samples_spin.setRange(1, 100)
        self.dmm_samples_spin.setValue(10)
        nplc_label = QLabel("NPLC")
        nplc_label.setObjectName("fieldLabel")
        self.dmm_nplc_combo = DarkComboBox()
        for nplc in (0.02, 0.2, 1, 10, 100):
            self.dmm_nplc_combo.addItem(f"{nplc:g}", nplc)
        self.dmm_nplc_combo.setCurrentIndex(2)
        range_label = QLabel("Range (V)")
        range_label.setObjectName("fieldLabel")
        self.dmm_range_combo = DarkComboBox()
        self.dmm_range_combo.addItem("AUTO", None)
        for rng in (0.1, 1, 10, 100):
            self.dmm_range_combo.addItem(f"{rng:g}", rng)
        dmm_grid.addWidget(samples_label, 0, 0)
        dmm_grid.addWidget(self.dmm_samples_spin, 1, 0)
        dmm_grid.addWidget(nplc_label, 0, 1)
        dmm_grid.addWidget(self.dmm_nplc_combo, 1, 1)
        dmm_grid.addWidget(range_label, 2, 0)
        dmm_grid.addWidget(self.dmm_range_combo, 2, 1)
        layout.addWidget(self.dmm_params_frame)

        self.vmeter_hint_label = QLabel("VMeter: 3-shot MEAS:VOLT? average. Use DMM for tight tolerance.")
        self.vmeter_hint_label.setObjectName("mutedLabel")
        self.vmeter_hint_label.setWordWrap(True)
        layout.addWidget(self.vmeter_hint_label)

    def _build_options_card(self):
        layout = self.options_card.main_layout
        self.restore_registers_check = QCheckBox("Restore registers after check")
        self.restore_registers_check.setChecked(True)
        self.restore_registers_check.setToolTip(
            "Restore all written Vbit registers to original values on finish/stop/error.")
        layout.addWidget(self.restore_registers_check)
        self.stop_on_fail_check = QCheckBox("Stop on first FAIL")
        self.stop_on_fail_check.setChecked(False)
        layout.addWidget(self.stop_on_fail_check)

    def _create_mini_stat(self, title, value):
        frame = QFrame()
        frame.setObjectName("miniStatCard")
        frame.setMinimumHeight(64)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("metricLabel")
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return {"frame": frame, "title": title_label, "value": value_label}

    def _bind_signals(self):
        self.bind_n6705c_signals()
        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.manage_chips_btn.clicked.connect(self._on_manage_chips)
        self.chip_combo.currentIndexChanged.connect(self._on_chip_changed)
        self.measure_instr_combo.currentIndexChanged.connect(self._on_instrument_changed)
        self.dut_combo.currentIndexChanged.connect(self._on_dut_changed)
        for editor in self._config_editors():
            if isinstance(editor, DarkComboBox):
                editor.currentIndexChanged.connect(self._apply_rail_edits)
            elif isinstance(editor, QSpinBox):
                editor.valueChanged.connect(self._apply_rail_edits)
            else:
                editor.editingFinished.connect(self._apply_rail_edits)
        self.dmm_card.log_message.connect(self.append_log)
        self.execution_logs.clear_log_btn.clicked.connect(self.execution_logs.clear_log)
        self._on_instrument_changed()

    # ------------------------------------------------------------------
    # 芯片 / rail 展示
    # ------------------------------------------------------------------

    def _current_chip(self):
        name = self.chip_combo.currentText()
        for chip in self._chip_library:
            if chip.get("name") == name:
                return chip
        return None

    def _refresh_chip_combo(self, select_name=None):
        self.chip_combo.blockSignals(True)
        self.chip_combo.clear()
        for chip in self._chip_library:
            self.chip_combo.addItem(str(chip.get("name", "")))
        self.chip_combo.blockSignals(False)
        if select_name is not None:
            idx = self.chip_combo.findText(select_name)
            if idx >= 0:
                self.chip_combo.setCurrentIndex(idx)
        self._on_chip_changed()

    def _on_chip_changed(self):
        self._refresh_dut_combo()

    def _current_rail(self):
        chip = self._current_chip()
        if chip is None:
            return None
        name = self.dut_combo.currentText()
        for rail in chip.get("rails", []):
            if str(rail.get("name", "")) == name:
                return rail
        return None

    def _refresh_dut_combo(self, select_name=None):
        chip = self._current_chip()
        rails = [r for r in (chip.get("rails", []) if chip else [])
                 if r.get("enabled", True)]
        previous = select_name or self.dut_combo.currentText()
        self.dut_combo.blockSignals(True)
        self.dut_combo.clear()
        for rail in rails:
            self.dut_combo.addItem(str(rail.get("name", "")), rail.get("name"))
        self.dut_combo.blockSignals(False)
        if previous:
            idx = self.dut_combo.findText(previous)
            if idx >= 0:
                self.dut_combo.setCurrentIndex(idx)
        self.chip_hint_label.setVisible(chip is None or not rails)
        self._load_rail_fields()

    def _on_dut_changed(self):
        self._load_rail_fields()

    def _load_rail_fields(self):
        """把当前 DUT 的 EFUSE / Vbit / 校准配置回填到编辑区。"""
        rail = self._current_rail()
        self._rail_loading = True
        try:
            for editor in self._config_editors():
                editor.setEnabled(rail is not None)
            if rail is None:
                self.rail_meta_label.setText("")
                self.efuse_addr_edit.clear()
                self.vbit_addr_edit.clear()
                self.base_code_edit.clear()
                self.offset_lsb_edit.clear()
                self.target_mv_edit.clear()
                self.tolerance_edit.clear()
                return

            efuse = rail.get("efuse_field") or {}
            vbit = rail.get("vbit") or {}
            target = rail.get("target") or {}
            sign_bit = efuse.get("sign_bit")
            self.efuse_addr_edit.setText(str(efuse.get("reg_addr", "0x0000")))
            self.efuse_msb_spin.setValue(int(efuse.get("msb", 7)))
            self.efuse_lsb_spin.setValue(int(efuse.get("lsb", 0)))
            self.efuse_sign_bit_spin.setValue(
                -1 if sign_bit is None else int(sign_bit))
            self.vbit_addr_edit.setText(str(vbit.get("reg_addr", "0x0000")))
            self.vbit_msb_spin.setValue(int(vbit.get("msb", 7)))
            self.vbit_lsb_spin.setValue(int(vbit.get("lsb", 0)))
            idx = self.mode_combo.findData(str(rail.get("mode", "offset")))
            self.mode_combo.setCurrentIndex(max(idx, 0))
            self.base_code_edit.setText(str(rail.get("base_code", "0x0")))
            self.offset_lsb_edit.setText(str(rail.get("offset_lsb", 0)))
            if target.get("source") == "config":
                self.target_mv_edit.setText(f"{target.get('voltage_mv', 0):g}")
            else:
                self.target_mv_edit.setText("derived")
            self.tolerance_edit.setText(f"{rail.get('tolerance_mv', 0):g}")
            self.target_mv_edit.setReadOnly(target.get("source") != "config")
            self.rail_meta_label.setText(
                f"{rail.get('type', '')} | step {rail.get('step_mv', 0):g} mV/LSB"
                f" | base {rail.get('base_voltage_mv', 0):g} mV"
            )
        finally:
            self._rail_loading = False

    def _apply_rail_edits(self):
        """把编辑区改动写回芯片库并落盘（校验失败仅告警，不落库）。"""
        if self._rail_loading or self.is_test_running:
            return
        rail = self._current_rail()
        if rail is None:
            return
        try:
            efuse = dict(rail.get("efuse_field") or {})
            efuse["reg_addr"] = self.efuse_addr_edit.text().strip()
            efuse["msb"] = self.efuse_msb_spin.value()
            efuse["lsb"] = self.efuse_lsb_spin.value()
            sign_bit = self.efuse_sign_bit_spin.value()
            if sign_bit < 0:
                efuse.pop("sign_bit", None)
            else:
                efuse["sign_bit"] = sign_bit
                efuse["signed"] = False
            rail["efuse_field"] = efuse

            vbit = dict(rail.get("vbit") or {})
            vbit["reg_addr"] = self.vbit_addr_edit.text().strip()
            vbit["msb"] = self.vbit_msb_spin.value()
            vbit["lsb"] = self.vbit_lsb_spin.value()
            rail["vbit"] = vbit

            rail["mode"] = self.mode_combo.currentData() or "offset"
            rail["base_code"] = self.base_code_edit.text().strip() or "0x0"
            rail["offset_lsb"] = int(float(self.offset_lsb_edit.text() or 0))
            target = dict(rail.get("target") or {})
            if target.get("source", "config") == "config":
                target["voltage_mv"] = float(self.target_mv_edit.text())
            rail["target"] = target
            rail["tolerance_mv"] = float(self.tolerance_edit.text())
            validate_rail(rail)
        except (ValueError, TypeError) as e:
            self.append_log(f"[WARN] {rail.get('name')} config not saved: {e}")
            return
        try:
            save_library(self._chip_library)
        except OSError:
            self.append_log("[ERROR] Failed to save chip library.")
            _logger.error("保存芯片库失败", exc_info=True)
            return
        self.append_log(
            f"[CONFIG] {rail['name']}: EFUSE 0x{efuse['reg_addr']} "
            f"[{efuse['msb']}:{efuse['lsb']}] saved."
        )

    def _on_manage_chips(self):
        if self.is_test_running:
            return
        current = self.chip_combo.currentText()
        dlg = ChipManagerDialog(self._chip_library, parent=self)
        dlg.chips_changed.connect(self._on_chips_changed)
        dlg.exec()
        if dlg.result() == dlg.Accepted:
            self._chip_library = load_library()
            self._refresh_chip_combo(select_name=current)

    def _on_chips_changed(self):
        self._chip_library = load_library()
        self._refresh_chip_combo(select_name=self.chip_combo.currentText())

    def _on_instrument_changed(self):
        is_dmm = self.measure_instr_combo.currentData() == _INSTR_DMM
        self.dmm_card.setVisible(is_dmm)
        self.dmm_params_frame.setVisible(is_dmm)
        self.n6705c_card.setVisible(not is_dmm)
        self.vmeter_hint_label.setVisible(not is_dmm)

    # ------------------------------------------------------------------
    # 日志 / 进度 / 状态
    # ------------------------------------------------------------------

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def set_progress(self, value):
        self.execution_logs.set_progress(value)

    def update_instrument_info(self, instrument_info):
        if self.is_connected:
            self.set_system_status("● Connected")

    # ------------------------------------------------------------------
    # 启停编排
    # ------------------------------------------------------------------

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def _validate_before_test(self):
        chip = self._current_chip()
        if chip is None:
            return "No chip selected. Configure chips via Manage Chips."
        try:
            validate_chip_config(chip)
        except ValueError as e:
            return str(e)
        if self._current_rail() is None:
            return "No DUT selected. Pick a rail in the DUT dropdown."
        instrument = self.measure_instr_combo.currentData()
        if instrument == _INSTR_DMM:
            if not DEBUG_MOCK and (not self.dmm_card.is_connected
                                   or self.dmm_card.dmm is None):
                return "DMM not connected. Connect the multimeter first."
        else:
            if not DEBUG_MOCK and (not self.is_connected or self.n6705c is None):
                return "N6705C not connected. Connect the power supply first."
        return None

    def _resolve_instruments(self):
        """返回 (n6705c, dmm)；DEBUG_MOCK 未连接时就地创建 Mock 实例。"""
        instrument = self.measure_instr_combo.currentData()
        n6705c = None
        dmm = None
        if instrument == _INSTR_VMETER:
            n6705c = self.n6705c
            if n6705c is None and DEBUG_MOCK:
                from instruments.mock.mock_instruments import MockN6705C
                n6705c = MockN6705C()
        else:
            dmm = self.dmm_card.dmm
            if dmm is None and DEBUG_MOCK:
                from instruments.factory import create_digital_multimeter
                dmm = create_digital_multimeter("34461a", "")
        return n6705c, dmm

    def _on_start_test(self):
        if self.is_test_running:
            return
        error = self._validate_before_test()
        if error is not None:
            self.append_log(f"[ERROR] {error}")
            return
        rail = self._current_rail()
        chip = copy.deepcopy(self._current_chip())
        instrument = self.measure_instr_combo.currentData()
        options = {
            "instrument": instrument,
            "selected_rails": [rail["name"]],
            "vmeter_channel": int(
                self.vmeter_channel_combo.currentText().replace("CH ", "")),
            "dmm_samples": self.dmm_samples_spin.value(),
            "dmm_nplc": self.dmm_nplc_combo.currentData(),
            "dmm_range": self.dmm_range_combo.currentData(),
            "restore_registers": self.restore_registers_check.isChecked(),
            "stop_on_fail": self.stop_on_fail_check.isChecked(),
        }
        n6705c, dmm = self._resolve_instruments()

        self.clear_results()
        self._test_stop_requested = False
        self.set_test_running(True)

        thread = QThread()
        worker = FtCalibOvWorker(chip, options, n6705c=n6705c, dmm=dmm,
                                 debug_flag=DEBUG_MOCK)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.rail_result.connect(self._on_rail_result)
        worker.result_update.connect(self.update_test_result)
        worker.test_finished.connect(self._on_test_finished)
        worker.test_finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_test_thread_finished)
        self.test_thread = thread
        self._test_worker = worker
        thread.start()

    def _on_stop_test(self):
        if self._test_worker is not None:
            self._test_worker.request_stop()
        self._test_stop_requested = True
        if self.test_thread is not None and self.test_thread.isRunning():
            self.test_thread.quit()
        # 禁在 UI 线程 wait()：收尾交 thread.finished → _on_test_thread_finished
        self.append_log("[TEST] Stop requested...")

    def set_test_running(self, running):
        self.is_test_running = running
        update_start_btn_state(self.start_test_btn, running,
                               start_text="▷ Start Check", stop_text="■ Stop")
        self.stop_test_btn.setEnabled(running)
        widgets = [
            self.chip_combo, self.manage_chips_btn, self.dut_combo,
            *self._config_editors(),
            self.measure_instr_combo, self.vmeter_channel_combo,
            self.dmm_samples_spin, self.dmm_nplc_combo, self.dmm_range_combo,
            self.restore_registers_check, self.stop_on_fail_check,
            self.visa_resource_combo, self.search_btn, self.connect_btn,
        ]
        for widget in widgets:
            widget.setEnabled(not running)
        self.dmm_card.set_busy(running)
        if running:
            self.set_system_status("● Running")
            self.append_log("[TEST] Starting Output Voltage Check...")
        else:
            self.set_system_status("● Connected" if self.is_connected else "● Ready")

    def _on_rail_result(self, rec):
        self._rail_results.append(rec)
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        values = [
            rec["rail"],
            rec["type"],
            str(rec["efuse_value"]),
            f"0x{rec['code']:X}",
            f"{rec['target_mv']:.1f}",
            f"{rec['measured_mv']:.1f}",
            f"{rec['err_mv']:+.1f}",
            f"{rec['tolerance_mv']:.1f}",
            "PASS" if rec["passed"] else "FAIL",
        ]
        for col, text in enumerate(values):
            item = QTableWidgetItem(text)
            if col == 8:
                item.setForeground(Qt.green if rec["passed"] else Qt.red)
            self.result_table.setItem(row, col, item)
        self._update_error_plot()

    def _update_error_plot(self):
        if not self._rail_results:
            self._error_scatter.setData([], [])
            self._error_bars.setData(x=[], y=[], top=[], bottom=[])
            return
        xs = list(range(1, len(self._rail_results) + 1))
        ys = [r["err_mv"] for r in self._rail_results]
        tols = [r["tolerance_mv"] for r in self._rail_results]
        self._error_scatter.setData(xs, ys)
        self._error_bars.setData(x=xs, y=ys, top=tols, bottom=tols)
        axis = self.error_plot.getAxis("bottom")
        axis.setTicks([[(x, r["rail"]) for x, r in zip(xs, self._rail_results)]])
        span = max(max(abs(y) for y in ys), max(tols)) * 1.3 or 1.0
        self.error_plot.setYRange(-span, span)
        self.error_plot.setXRange(0.5, len(xs) + 0.5)

    def update_test_result(self, result):
        if not isinstance(result, dict):
            return
        self._last_summary = result
        if "total" in result:
            self.rails_card["value"].setText(str(result["total"]))
            self.passed_card["value"].setText(str(result["passed"]))
            self.failed_card["value"].setText(str(result["failed"]))
            self.max_err_card["value"].setText(f"{result['max_abs_err_mv']:.1f}")
            if result["total"] > 0:
                passed = result["overall_pass"]
                self.verdict_card["value"].setText("PASS" if passed else "FAIL")
                self.verdict_card["value"].setStyleSheet(
                    "color: #15d1a3;" if passed else "color: #ff5e7a;")
        if "progress" in result:
            self.set_progress(result["progress"])

    def _on_test_finished(self, success, reason):
        self.append_log(f"[RESULT] {reason}")
        summary = self._last_summary or {}
        if summary.get("total"):
            self.append_log(
                f"[RESULT] Verdict: {'PASS' if summary.get('overall_pass') else 'FAIL'} "
                f"({summary.get('passed', 0)}/{summary.get('total', 0)} rails, "
                f"max |error| = {summary.get('max_abs_err_mv', 0):.1f} mV)"
            )
        self.set_progress(100 if success else self.progress_bar.value())

    def _on_test_thread_finished(self):
        self._test_worker = None
        self.test_thread = None
        self.set_test_running(False)
        self.append_log("[TEST] Check sequence ended.")
        stopped = bool(self._test_stop_requested)
        summary = "测试被中止" if stopped else "测试完成"
        self.sequence_execution_finished.emit(not stopped, summary)

    def cleanup_threads(self):
        try:
            from shiboken6 import isValid
        except ImportError:
            def isValid(obj):
                return obj is not None
        worker = self._test_worker
        if worker is not None and isValid(worker):
            worker.request_stop()
        thread = self.test_thread
        if thread is not None and isValid(thread):
            _retire_thread(thread, worker if worker is None or isValid(worker) else None)
        self.test_thread = None
        for attr in ("_n6705c_search_thread",):
            search_thread = getattr(self, attr, None)
            if search_thread is not None and isValid(search_thread):
                _retire_thread(search_thread)
            setattr(self, attr, None)
        self.dmm_card.cleanup_threads()

    # ------------------------------------------------------------------
    # 结果 / 导出 / 截图
    # ------------------------------------------------------------------

    @property
    def has_results(self):
        return bool(self._rail_results)

    def clear_results(self):
        self._rail_results = []
        self._last_summary = None
        self.result_table.setRowCount(0)
        self._update_error_plot()
        for card in (self.rails_card, self.passed_card, self.failed_card,
                     self.max_err_card):
            card["value"].setText("---")
        self.verdict_card["value"].setText("---")
        self.verdict_card["value"].setStyleSheet("")
        self.set_progress(0)

    def export_csv(self):
        if not self._rail_results:
            self.append_log("[EXPORT] No data to export.")
            return
        chip_name = self.chip_combo.currentText() or "chip"
        results_dir = os.path.join(get_resource_base(), "Results")
        os.makedirs(results_dir, exist_ok=True)
        default_name = (
            f"ft_calib_ov_{chip_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", os.path.join(results_dir, default_name),
            "CSV Files (*.csv);;All Files (*)",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Rail", "Type", "EFUSE (LSB)", "Code", "Target (mV)",
                    "Measured (mV)", "Error (mV)", "Tolerance (mV)", "Verdict",
                ])
                for rec in self._rail_results:
                    writer.writerow([
                        rec["rail"], rec["type"], rec["efuse_value"],
                        f"0x{rec['code']:X}", f"{rec['target_mv']:.2f}",
                        f"{rec['measured_mv']:.2f}", f"{rec['err_mv']:.2f}",
                        f"{rec['tolerance_mv']:.2f}",
                        "PASS" if rec["passed"] else "FAIL",
                    ])
            self.append_log(f"[EXPORT] Data exported to {file_path}")
        except OSError as e:
            self.append_log(f"[ERROR] Export failed: {e}")
            _logger.error("FT calib OV export failed", exc_info=True)

    def get_capture_pixmap(self):
        return self.result_container.grab()

    # ------------------------------------------------------------------
    # 配置接口 / ConfigMemory
    # ------------------------------------------------------------------

    def get_test_config(self):
        rail = self._current_rail()
        return {
            "chip_name": self.chip_combo.currentText(),
            "selected_rails": [rail["name"]] if rail else [],
            "measure_instrument": self.measure_instr_combo.currentData(),
            "vmeter_channel": self.vmeter_channel_combo.currentText(),
            "dmm_resource": self.dmm_card.resource_text(),
            "dmm_samples": self.dmm_samples_spin.value(),
            "dmm_nplc": self.dmm_nplc_combo.currentData(),
            "dmm_range": self.dmm_range_combo.currentData(),
            "restore_registers": self.restore_registers_check.isChecked(),
            "stop_on_fail": self.stop_on_fail_check.isChecked(),
        }

    def apply_config_to_controls(self, cfg: dict, silent: bool = False) -> tuple[bool, str]:
        """配置回填单一写入口（AI / ConfigMemory 共用）。"""
        if not isinstance(cfg, dict):
            return False, "配置草案格式无效（期望 dict）。"
        if threading.current_thread() is not threading.main_thread():
            _logger.error("apply_config_to_controls 在非主线程被调用，拒绝回填")
            return False, "配置回填未在主线程执行，已拒绝。"

        applied = []
        touched = []

        chip_name = cfg.get("chip_name")
        if chip_name is not None:
            idx = self.chip_combo.findText(str(chip_name))
            if idx < 0 and self.chip_combo.count() > 0:
                _logger.warning("ConfigMemory 芯片 %s 不在库中，降级默认", chip_name)
                idx = 0
            if idx >= 0:
                self.chip_combo.setCurrentIndex(idx)
                applied.append("chip_name")
                touched.append(self.chip_combo)

        selected = cfg.get("selected_rails")
        if isinstance(selected, str):
            selected = [selected]
        if isinstance(selected, list) and selected:
            chip = self._current_chip()
            valid = {r["name"] for r in (chip.get("rails", []) if chip else [])}
            for name in selected:
                if str(name) in valid:
                    idx = self.dut_combo.findText(str(name))
                    if idx >= 0:
                        self.dut_combo.setCurrentIndex(idx)
                        break
            applied.append("selected_rails")

        instrument = cfg.get("measure_instrument")
        if instrument in (_INSTR_DMM, _INSTR_VMETER):
            idx = self.measure_instr_combo.findData(instrument)
            if idx >= 0:
                self.measure_instr_combo.setCurrentIndex(idx)
                applied.append("measure_instrument")
                touched.append(self.measure_instr_combo)

        channel = cfg.get("vmeter_channel")
        if channel is not None:
            text = str(channel).strip().upper()
            digits = "".join(ch for ch in text if ch.isdigit())
            if digits:
                idx = self.vmeter_channel_combo.findText(f"CH {digits}")
                if idx >= 0:
                    self.vmeter_channel_combo.setCurrentIndex(idx)
                    applied.append("vmeter_channel")
                    touched.append(self.vmeter_channel_combo)

        resource = cfg.get("dmm_resource")
        if resource:
            self.dmm_card.set_resource_text(str(resource))
            applied.append("dmm_resource")

        samples = cfg.get("dmm_samples")
        if samples is not None:
            try:
                self.dmm_samples_spin.setValue(int(float(samples)))
                applied.append("dmm_samples")
                touched.append(self.dmm_samples_spin)
            except (TypeError, ValueError):
                pass

        nplc = cfg.get("dmm_nplc")
        if nplc is not None:
            try:
                idx = self.dmm_nplc_combo.findData(float(nplc))
            except (TypeError, ValueError):
                idx = -1
            if idx >= 0:
                self.dmm_nplc_combo.setCurrentIndex(idx)
                applied.append("dmm_nplc")
                touched.append(self.dmm_nplc_combo)

        dmm_range = cfg.get("dmm_range")
        if "dmm_range" in cfg:
            try:
                idx = self.dmm_range_combo.findData(
                    None if dmm_range is None else float(dmm_range))
            except (TypeError, ValueError):
                idx = -1
            if idx >= 0:
                self.dmm_range_combo.setCurrentIndex(idx)
                applied.append("dmm_range")
                touched.append(self.dmm_range_combo)

        for key, check in (("restore_registers", self.restore_registers_check),
                           ("stop_on_fail", self.stop_on_fail_check)):
            if key in cfg:
                check.setChecked(bool(cfg[key]))
                applied.append(key)
                touched.append(check)

        if not applied:
            return False, "配置草案未包含任何可识别的配置项。"
        if not silent:
            self._highlight_widgets(touched)
            self.append_log(f"[AI] 已应用配置：{', '.join(applied)}")
        return True, f"已应用配置项：{', '.join(applied)}。"

    def _highlight_widgets(self, widgets):
        for widget in widgets:
            if widget is None:
                continue
            widget.setStyleSheet(_AI_HIGHLIGHT_QSS)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

            def _clear(_w=widget):
                try:
                    _w.setStyleSheet("")
                    _w.style().unpolish(_w)
                    _w.style().polish(_w)
                except RuntimeError:
                    pass
            QTimer.singleShot(_AI_HIGHLIGHT_MS, _clear)

    # ------------------------------------------------------------------
    # 容器透传辅助
    # ------------------------------------------------------------------

    def get_test_mode(self):
        return self._test_mode

    def set_test_mode(self, mode):
        self._test_mode = mode

    def get_test_id(self):
        return self._test_id

    def set_test_id(self, test_id):
        self._test_id = test_id

    # ------------------------------------------------------------------
    # AIControllablePage 契约
    # ------------------------------------------------------------------

    def ai_capabilities(self) -> set[str]:
        return {
            CAP_GET_CONFIG, CAP_APPLY_CONFIG, CAP_START_TEST,
            CAP_STOP_TEST, CAP_GET_RESULT,
        }

    def ai_get_config(self) -> dict[str, Any] | None:
        try:
            return self.get_test_config()
        except Exception:  # noqa: BLE001 - 快照失败降级为 None
            _logger.error("AI 读取 Output Voltage Check 配置失败", exc_info=True)
            return None

    def ai_apply_config(self, payload: Any) -> tuple[bool, str]:
        if self.is_test_running:
            return False, "测试运行中，无法修改配置，请先停止测试。"
        return self.apply_config_to_controls(payload if isinstance(payload, dict) else {})

    def ai_start_test(self) -> tuple[bool, str]:
        error = self._validate_before_test()
        if error is not None:
            return False, error
        if self.is_test_running:
            return False, "测试已在运行中。"
        self.append_log("[AI] 请求启动 Output Voltage Check。")
        try:
            self._on_start_test()
        except Exception:  # noqa: BLE001 - 启动异常转可读结果
            _logger.error("AI 启动 Output Voltage Check 失败", exc_info=True)
            return False, "启动测试异常，请查看日志。"
        if self.is_test_running:
            return True, "已请求启动 Output Voltage Check。"
        return False, "启动未成功，请查看执行日志。"

    def ai_stop_test(self) -> tuple[bool, str]:
        if not self.is_test_running:
            return False, "当前未在运行测试。"
        self.append_log("[AI] 请求停止测试。")
        try:
            self._on_stop_test()
        except Exception:  # noqa: BLE001 - 停止异常转可读结果
            _logger.error("AI 停止 Output Voltage Check 失败", exc_info=True)
            return False, "停止测试异常，请查看日志。"
        return True, "已发送停止请求。"

    def ai_get_result_summary(self) -> dict[str, Any] | None:
        summary: dict[str, Any] = {
            "available": True,
            "running": self.is_test_running,
            "chip": self.chip_combo.currentText(),
        }
        if self._last_summary:
            summary["summary"] = dict(self._last_summary)
        return summary


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from ui.standalone import apply_window_icon, resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FtCalibOvCheckUI()
    window.setWindowTitle("Output Voltage Check")
    apply_window_icon(window, "pmu_test")
    resize_and_center_window(window)
    window.show()
    sys.exit(app.exec())
