#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 子页面基类（LDO / DCDC 共用）。

规划 §5：仪器连接区 + 通道/被测配置区 + 测试项清单区 + 统一参数区 +
执行/日志区（ExecutionLogsFrame + QSplitter）+ 报告区。
AI 契约（§8.1）与 UIActionSpec 白名单（§8.2）亦在此实现，两个子类仅绑定
module_type / page_key / items 注册表 / runner 类。
"""
from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core.ai.page_contract import (
    CAP_APPLY_CONFIG, CAP_GET_CONFIG, CAP_GET_RESULT, CAP_START_TEST, CAP_STOP_TEST,
)
from core.ai.ui_action_registry import UIActionSpec
from debug_config import DEBUG_MOCK
from log_config import get_logger
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.oscilloscope_module_frame import OscilloscopeConnectionMixin
from ui.pages.module_test.widgets import CollapsibleGroupBox
from ui.resource_path import get_resource_base
from ui.styles import START_BTN_STYLE, SCROLLBAR_STYLE
from ui.widgets.dark_combobox import DarkComboBox

_logger = get_logger(__name__)

_AI_HIGHLIGHT_QSS = "border: 1px solid #15d1a3;"
_AI_HIGHLIGHT_MS = 1500


class ModuleTestSubPageBase(QWidget, N6705CConnectionMixin, OscilloscopeConnectionMixin):
    """LDO/DCDC 子页面共用基类。

    子类须设置类属性：MODULE_TYPE / PAGE_KEY / ITEMS_REGISTRY / RUNNER_CLS。
    """

    MODULE_TYPE: str = ""
    PAGE_KEY: str = ""
    ITEMS_REGISTRY: dict[str, tuple[str, Any, bool, bool]] = {}
    RUNNER_CLS: type = None  # type: ignore[assignment]

    def __init__(self, *, n6705c_top=None, mso64b_top=None, chamber_ui=None,
                 instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._mso64b_top = mso64b_top
        self._chamber_ui = chamber_ui
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry

        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)
        self.init_oscilloscope_connection(mso64b_top, instrument_manager=instrument_manager)

        self._runner = None
        self.is_test_running = False
        self._last_result = None
        self._last_report_path: str | None = None

        self._setup_style()
        self._build_ui()
        self._populate_item_table()
        self.sync_n6705c_from_top()
        self.sync_oscilloscope_from_top()
        self._refresh_scope_item_state()
        self._register_ai_ui_actions()

    # ------------------------------------------------------------------ style
    def _setup_style(self):
        icons_dir = os.path.join(get_resource_base(), "resources", "icons")
        cb_checked = os.path.join(icons_dir, "checked_4f46e5.svg").replace("\\", "/")
        cb_unchecked = os.path.join(icons_dir, "unchecked_4f46e5.svg").replace("\\", "/")
        self.setStyleSheet(f"""
            QWidget #{self.__class__.__name__} {{
                background-color: #020618; color: #c8c8c8; border: none;
            }}
            QLabel {{ color: #c8c8c8; }}
            QLabel#fieldLabel {{ color: #9aa4bd; }}
            QLabel#cardTitle {{ color: #8eb0e3; font-weight: 700; background-color: transparent; }}
            QLabel#statusOk {{ color: #15d1a3; font-weight: 600; background-color: transparent; }}
            QLabel#statusWarn {{ color: #ffb84d; font-weight: 600; background-color: transparent; }}
            QLabel#statusErr {{ color: #ff5e7a; font-weight: 600; background-color: transparent; }}
            QLineEdit, QSpinBox {{
                border: 1px solid #2f374d; border-radius: 4px; padding: 3px 8px;
                background-color: #161b2e; color: #c8c8c8; min-height: 22px;
            }}
            QLineEdit:focus, QSpinBox:focus {{ border: 1px solid #4a6c9b; }}
            QLineEdit::placeholder {{ color: #5a6377; }}
            #actionRow {{ border-top: 1px solid #1c2438; }}
            #start_test_btn {{ {START_BTN_STYLE} }}
            #stop_test_btn {{
                border: 1px solid #555; border-radius: 4px; padding: 6px 14px;
                background-color: #3a2230; color: #e0a0b0; min-height: 22px;
            }}
            #stop_test_btn:hover {{ background-color: #4a2a3c; }}
            #stop_test_btn:disabled {{ background-color: #2a2d32; color: #666; }}
            #open_report_btn, #select_all_btn, #clear_results_btn {{
                border: 1px solid #3a4260; border-radius: 4px; padding: 5px 12px;
                background-color: #32353a; color: #c8c8c8; min-height: 22px;
            }}
            #open_report_btn:hover, #select_all_btn:hover, #clear_results_btn:hover {{
                background-color: #3a3d43;
            }}
            #open_report_btn:disabled {{ background-color: #2a2d32; color: #666; }}
            QTableWidget {{
                background-color: #0a0f1f; color: #c8c8c8;
                gridline-color: transparent; border: 1px solid #26304a;
                border-radius: 4px; alternate-background-color: #0e1526;
            }}
            QTableWidget::item {{ padding: 2px 6px; border: none; }}
            QTableWidget::item:hover {{ background-color: #14203a; }}
            QTableWidget::indicator {{
                width: 16px; height: 16px;
                image: url("{cb_unchecked}");
            }}
            QTableWidget::indicator:checked {{
                image: url("{cb_checked}");
            }}
            QHeaderView::section {{
                background-color: #161b2e; color: #8eb0e3; padding: 5px 6px;
                border: none; border-bottom: 1px solid #2a3148; font-weight: 600;
            }}
            QScrollBar:vertical {{ background: #0a0f1f; width: 10px; }}
            {SCROLLBAR_STYLE}
        """)
        self.setObjectName(self.__class__.__name__)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        content = QWidget()
        content.setObjectName("moduleTestContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)

        content_layout.addWidget(self._build_connection_group())
        content_layout.addWidget(self._build_config_group())
        content_layout.addWidget(self._build_items_group())
        content_layout.addWidget(self._build_params_group())
        content_layout.addWidget(self._build_action_row())
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        self._splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            scroll, title=f"{self.MODULE_TYPE.upper()} Module Test 执行日志", stretch=(5, 2),
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._splitter)

    def _build_connection_group(self) -> "CollapsibleGroupBox":
        box = CollapsibleGroupBox("仪器连接", expanded=True)
        lay = box.content_layout
        lay.setSpacing(4)

        n6705c_title_row = QHBoxLayout()
        n6705c_title_row.setSpacing(8)
        n6705c_title = QLabel("N6705C")
        n6705c_title.setObjectName("cardTitle")
        n6705c_title_row.addWidget(n6705c_title)
        n6705c_title_row.addStretch()
        lay.addLayout(n6705c_title_row)
        self.build_n6705c_connection_widgets(lay, title_row=n6705c_title_row)

        scope_title_row = QHBoxLayout()
        scope_title_row.setSpacing(8)
        scope_title = QLabel("Oscilloscope")
        scope_title.setObjectName("cardTitle")
        scope_title_row.addWidget(scope_title)
        scope_title_row.addStretch()
        lay.addLayout(scope_title_row)
        self.build_oscilloscope_connection_widgets(lay, title_row=scope_title_row)

        self.bind_n6705c_signals()
        self.bind_oscilloscope_signals()
        return box

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setMinimumWidth(84)
        return lbl

    def _build_config_group(self) -> "CollapsibleGroupBox":
        box = CollapsibleGroupBox("被测配置", expanded=True)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        grid.addWidget(self._field_label("芯片名称"), 0, 0)
        self.chip_name_edit = QLineEdit()
        self.chip_name_edit.setPlaceholderText("如 BES1307")
        grid.addWidget(self.chip_name_edit, 0, 1)

        grid.addWidget(self._field_label("操作员"), 0, 2)
        self.operator_edit = QLineEdit()
        grid.addWidget(self.operator_edit, 0, 3)

        grid.addWidget(self._field_label("Vin 通道"), 1, 0)
        self.vin_ch_combo = DarkComboBox()
        self.vin_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        grid.addWidget(self.vin_ch_combo, 1, 1)

        grid.addWidget(self._field_label("Vout 通道"), 1, 2)
        self.vout_ch_combo = DarkComboBox()
        self.vout_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        self.vout_ch_combo.setCurrentIndex(1)
        grid.addWidget(self.vout_ch_combo, 1, 3)

        grid.addWidget(self._field_label("Iload 通道"), 2, 0)
        self.iload_ch_combo = DarkComboBox()
        self.iload_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        self.iload_ch_combo.setCurrentIndex(2)
        grid.addWidget(self.iload_ch_combo, 2, 1)

        grid.addWidget(self._field_label("Vout 标称 (mV)"), 2, 2)
        self.vout_nominal_spin = QSpinBox()
        self.vout_nominal_spin.setRange(0, 6000)
        self.vout_nominal_spin.setValue(1800 if self.MODULE_TYPE == "ldo" else 1200)
        grid.addWidget(self.vout_nominal_spin, 2, 3)

        grid.addWidget(self._field_label("Code 起始"), 3, 0)
        self.min_code_spin = QSpinBox()
        self.min_code_spin.setRange(0, 65535)
        grid.addWidget(self.min_code_spin, 3, 1)

        grid.addWidget(self._field_label("Code 结束"), 3, 2)
        self.max_code_spin = QSpinBox()
        self.max_code_spin.setRange(0, 65535)
        self.max_code_spin.setValue(255)
        grid.addWidget(self.max_code_spin, 3, 3)

        grid.addWidget(self._field_label("温度点 (°C)"), 4, 0)
        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("常温留空")
        grid.addWidget(self.temperature_edit, 4, 1)

        grid.addWidget(self._field_label("Device 地址"), 5, 0)
        self.device_addr_edit = QLineEdit("0x00")
        self.device_addr_edit.setPlaceholderText("如 0x62")
        grid.addWidget(self.device_addr_edit, 5, 1)

        grid.addWidget(self._field_label("寄存器地址"), 5, 2)
        self.reg_addr_edit = QLineEdit("0x00")
        self.reg_addr_edit.setPlaceholderText("如 0x0132")
        grid.addWidget(self.reg_addr_edit, 5, 3)

        grid.addWidget(self._field_label("MSB"), 6, 0)
        self.msb_spin = QSpinBox()
        self.msb_spin.setRange(0, 31)
        self.msb_spin.setValue(7)
        grid.addWidget(self.msb_spin, 6, 1)

        grid.addWidget(self._field_label("LSB"), 6, 2)
        self.lsb_spin = QSpinBox()
        self.lsb_spin.setRange(0, 31)
        self.lsb_spin.setValue(0)
        grid.addWidget(self.lsb_spin, 6, 3)

        grid.addWidget(self._field_label("Width Flag"), 7, 0)
        self.width_flag_spin = QSpinBox()
        self.width_flag_spin.setRange(1, 4)
        self.width_flag_spin.setValue(1)
        grid.addWidget(self.width_flag_spin, 7, 1)
        box.content_layout.addLayout(grid)
        return box

    def _build_items_group(self) -> "CollapsibleGroupBox":
        box = CollapsibleGroupBox("测试项清单（勾选要执行的项）", expanded=True)
        lay = box.content_layout
        self.items_table = QTableWidget(0, 4)
        self.items_table.setHorizontalHeaderLabels(["选", "测试项", "主要仪器", "判定/记录"])
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(30)
        self.items_table.setSelectionMode(QTableWidget.NoSelection)
        self.items_table.setShowGrid(False)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setFocusPolicy(Qt.NoFocus)
        header = self.items_table.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.items_table.setColumnWidth(0, 44)
        # 给清单足够高度显示全部行（表头 + 各测试项行），避免被 stretch 压扁导致内容截断
        self.items_table.setMinimumHeight(
            self.items_table.horizontalHeader().sizeHint().height()
            + len(self.ITEMS_REGISTRY) * 30 + 8
        )
        self.items_table.setSizePolicy(self.items_table.sizePolicy().horizontalPolicy(),
                                       QSizePolicy.Expanding)
        self.items_table.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self.items_table)
        return box

    def _build_params_group(self) -> "CollapsibleGroupBox":
        box = CollapsibleGroupBox("统一参数", expanded=False)
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        grid.addWidget(self._field_label("负载起始 (mA)"), 0, 0)
        self.iload_start_spin = QSpinBox()
        self.iload_start_spin.setRange(0, 100000)
        self.iload_start_spin.setValue(1)
        grid.addWidget(self.iload_start_spin, 0, 1)

        grid.addWidget(self._field_label("负载结束 (mA)"), 0, 2)
        self.iload_end_spin = QSpinBox()
        self.iload_end_spin.setRange(0, 100000)
        self.iload_end_spin.setValue(200)
        grid.addWidget(self.iload_end_spin, 0, 3)

        grid.addWidget(self._field_label("负载步进 (mA)"), 1, 0)
        self.iload_step_spin = QSpinBox()
        self.iload_step_spin.setRange(1, 100000)
        self.iload_step_spin.setValue(20)
        grid.addWidget(self.iload_step_spin, 1, 1)

        grid.addWidget(self._field_label("Vin 起始 (V)"), 1, 2)
        self.vin_start_spin = QSpinBox()
        self.vin_start_spin.setRange(0, 60)
        self.vin_start_spin.setValue(3)
        grid.addWidget(self.vin_start_spin, 1, 3)

        grid.addWidget(self._field_label("Vin 结束 (V)"), 2, 0)
        self.vin_end_spin = QSpinBox()
        self.vin_end_spin.setRange(0, 60)
        self.vin_end_spin.setValue(4)
        grid.addWidget(self.vin_end_spin, 2, 1)

        grid.addWidget(self._field_label("Vin 步进 (V)"), 2, 2)
        self.vin_step_spin = QSpinBox()
        self.vin_step_spin.setRange(1, 60)
        self.vin_step_spin.setValue(2)
        grid.addWidget(self.vin_step_spin, 2, 3)

        grid.addWidget(self._field_label("PSRR 频点"), 3, 0)
        self.psrr_freqs_edit = QLineEdit("1kHz, 10kHz, 100kHz")
        grid.addWidget(self.psrr_freqs_edit, 3, 1)

        grid.addWidget(self._field_label("瞬态频率"), 3, 2)
        self.transient_freqs_edit = QLineEdit("10Hz, 100Hz, 1kHz")
        grid.addWidget(self.transient_freqs_edit, 3, 3)
        box.content_layout.addLayout(grid)
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget()
        row.setObjectName("actionRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(8)

        self.start_test_btn = QPushButton("▶ 开始测试")
        self.start_test_btn.setObjectName("start_test_btn")
        self.start_test_btn.setCursor(Qt.PointingHandCursor)
        self.stop_test_btn = QPushButton("■ 停止")
        self.stop_test_btn.setObjectName("stop_test_btn")
        self.stop_test_btn.setEnabled(False)
        self.select_all_btn = QPushButton("全选测试项")
        self.select_all_btn.setObjectName("select_all_btn")
        self.clear_results_btn = QPushButton("清空结果")
        self.clear_results_btn.setObjectName("clear_results_btn")
        self.open_report_btn = QPushButton("打开报告")
        self.open_report_btn.setObjectName("open_report_btn")
        self.open_report_btn.setEnabled(False)
        for _btn in (self.select_all_btn, self.clear_results_btn, self.open_report_btn):
            _btn.setMinimumWidth(88)
            _btn.setCursor(Qt.PointingHandCursor)

        self.start_test_btn.clicked.connect(self._on_start_test)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.select_all_btn.clicked.connect(self._on_select_all_items)
        self.clear_results_btn.clicked.connect(self._on_clear_results)
        self.open_report_btn.clicked.connect(self._on_open_report)

        lay.addWidget(self.start_test_btn)
        lay.addWidget(self.stop_test_btn)
        lay.addStretch()
        lay.addWidget(self.select_all_btn)
        lay.addWidget(self.clear_results_btn)
        lay.addWidget(self.open_report_btn)
        return row

    # ------------------------------------------------------------------ items table
    def _populate_item_table(self):
        self.items_table.setRowCount(0)
        for item_key, spec in self.ITEMS_REGISTRY.items():
            name, _run_fn, needs_scope, item_checked = spec
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setTextAlignment(Qt.AlignCenter)
            chk.setCheckState(Qt.Checked if item_checked else Qt.Unchecked)
            self.items_table.setItem(row, 0, chk)
            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemIsEnabled)
            name_item.setData(Qt.UserRole, item_key)
            self.items_table.setItem(row, 1, name_item)
            inst = "示波器" if needs_scope else "N6705C"
            inst_item = QTableWidgetItem(inst)
            inst_item.setFlags(Qt.ItemIsEnabled)
            inst_item.setTextAlignment(Qt.AlignCenter)
            inst_item.setForeground(QColor("#c99b5a" if needs_scope else "#6f9bd6"))
            inst_item.setData(Qt.UserRole, needs_scope)
            self.items_table.setItem(row, 2, inst_item)
            rec_item = QTableWidgetItem("记录")
            rec_item.setFlags(Qt.ItemIsEnabled)
            rec_item.setForeground(QColor("#7f889c"))
            self.items_table.setItem(row, 3, rec_item)

    def _on_item_changed(self, _item: QTableWidgetItem):
        pass

    def _selected_item_keys(self) -> list[str]:
        keys: list[str] = []
        for row in range(self.items_table.rowCount()):
            chk = self.items_table.item(row, 0)
            name_item = self.items_table.item(row, 1)
            if chk and chk.checkState() == Qt.Checked and name_item:
                keys.append(name_item.data(Qt.UserRole))
        return keys

    def _refresh_scope_item_state(self):
        """未接示波器时灰化 (scope) 项并提示。"""
        scope_ok = self.scope_connected
        for row in range(self.items_table.rowCount()):
            inst_item = self.items_table.item(row, 2)
            chk = self.items_table.item(row, 0)
            if inst_item is None or chk is None:
                continue
            needs_scope = bool(inst_item.data(Qt.UserRole))
            if needs_scope and not scope_ok:
                chk.setCheckState(Qt.Unchecked)
                chk.setFlags(Qt.ItemIsEnabled)
                rec = self.items_table.item(row, 3)
                rec.setText("未接示波器，跳过")
                rec.setForeground(QColor("#b0684f"))
            else:
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                rec = self.items_table.item(row, 3)
                if rec.text().startswith("未接示波器"):
                    rec.setText("记录")
                    rec.setForeground(QColor("#7f889c"))

    # ------------------------------------------------------------------ config IO
    def get_test_config(self) -> dict[str, Any]:
        return {
            "selected_items": self._selected_item_keys(),
            "chip_name": self.chip_name_edit.text().strip(),
            "operator": self.operator_edit.text().strip(),
            "temperature": self.temperature_edit.text().strip(),
            "vin_channel": self.vin_ch_combo.currentText(),
            "vout_channel": self.vout_ch_combo.currentText(),
            "iload_channel": self.iload_ch_combo.currentText(),
            "vout_nominal_mv": self.vout_nominal_spin.value(),
            "min_code": self.min_code_spin.value(),
            "max_code": self.max_code_spin.value(),
            "device_addr": self.device_addr_edit.text().strip(),
            "reg_addr": self.reg_addr_edit.text().strip(),
            "msb": self.msb_spin.value(),
            "lsb": self.lsb_spin.value(),
            "width_flag": self.width_flag_spin.value(),
            "iload_start_ma": self.iload_start_spin.value(),
            "iload_end_ma": self.iload_end_spin.value(),
            "iload_step_ma": self.iload_step_spin.value(),
            "vin_start_v": self.vin_start_spin.value(),
            "vin_end_v": self.vin_end_spin.value(),
            "vin_step_v": self.vin_step_spin.value() / 10.0,
            "vin_v": self.vin_start_spin.value(),
            "psrr_freqs": [s.strip() for s in self.psrr_freqs_edit.text().split(",") if s.strip()],
            "transient_freqs": [s.strip() for s in self.transient_freqs_edit.text().split(",") if s.strip()],
        }

    def apply_config_to_controls(self, cfg: dict) -> tuple[bool, str]:
        if not isinstance(cfg, dict):
            return False, "配置草案格式无效（期望 dict）。"
        changed: list[str] = []
        try:
            if "chip_name" in cfg:
                self.chip_name_edit.setText(str(cfg["chip_name"])); changed.append("chip_name")
            if "operator" in cfg:
                self.operator_edit.setText(str(cfg["operator"])); changed.append("operator")
            if "vout_nominal_mv" in cfg:
                self.vout_nominal_spin.setValue(int(cfg["vout_nominal_mv"])); changed.append("vout_nominal_mv")
            if "iload_start_ma" in cfg:
                self.iload_start_spin.setValue(int(cfg["iload_start_ma"])); changed.append("iload_start_ma")
            if "iload_end_ma" in cfg:
                self.iload_end_spin.setValue(int(cfg["iload_end_ma"])); changed.append("iload_end_ma")
            if "iload_step_ma" in cfg:
                self.iload_step_spin.setValue(int(cfg["iload_step_ma"])); changed.append("iload_step_ma")
            if "vin_start_v" in cfg:
                self.vin_start_spin.setValue(int(cfg["vin_start_v"])); changed.append("vin_start_v")
            if "vin_end_v" in cfg:
                self.vin_end_spin.setValue(int(cfg["vin_end_v"])); changed.append("vin_end_v")
        except Exception:  # noqa: BLE001
            _logger.error("apply_config 落地失败", exc_info=True)
            return False, "配置落地异常，见日志。"
        QTimer.singleShot(0, lambda: self._highlight_fields(changed))
        return True, f"已应用配置：{', '.join(changed) if changed else '无变更'}"

    def _highlight_fields(self, fields: list[str]):
        widget_map = {
            "chip_name": self.chip_name_edit, "operator": self.operator_edit,
            "vout_nominal_mv": self.vout_nominal_spin, "iload_start_ma": self.iload_start_spin,
            "iload_end_ma": self.iload_end_spin, "iload_step_ma": self.iload_step_spin,
            "vin_start_v": self.vin_start_spin, "vin_end_v": self.vin_end_spin,
        }
        for f in fields:
            w = widget_map.get(f)
            if w is None:
                continue
            orig = w.styleSheet()
            w.setStyleSheet(_AI_HIGHLIGHT_QSS)
            QTimer.singleShot(_AI_HIGHLIGHT_MS, lambda _w=w, _o=orig: _w.setStyleSheet(_o))

    # ------------------------------------------------------------------ test flow
    def _on_start_test(self):
        if self.is_test_running:
            return
        cfg = self.get_test_config()
        if not cfg["selected_items"]:
            self.execution_logs.append_log("[WARN] 未勾选任何测试项，无法启动。")
            return
        if not self.is_connected or self.n6705c is None:
            if not DEBUG_MOCK:
                self.execution_logs.append_log("[ERROR] 未连接 N6705C，请先连接。")
                return
        scope = self.Osc_ins if self.scope_connected else None
        self._runner = self.RUNNER_CLS(
            config=cfg, n6705c=self.n6705c, scope=scope, chamber=None,
        )
        self._runner.progress.connect(self._on_progress)
        self._runner.item_finished.connect(self._on_item_finished)
        self._runner.log.connect(self.execution_logs.append_log)
        self._runner.finished_result.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)
        self.is_test_running = True
        self.start_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)
        self.set_system_status("测试进行中")
        self.execution_logs.start_timer(len(cfg["selected_items"]))
        self.execution_logs.append_log(f"[START] {self.MODULE_TYPE.upper()} Module Test 启动")
        self._runner.start()

    def _on_stop_test(self):
        if self._runner is not None and self.is_test_running:
            self.execution_logs.append_log("[STOP] 请求停止测试...")
            self._runner.request_stop()

    def _on_progress(self, percent: int, label: str):
        self.execution_logs.set_progress(percent)

    def _on_item_finished(self, item_key: str, summary: dict):
        verdict = summary.get("passed", "N/A")
        self.execution_logs.append_log(f"[ITEM] {item_key} -> {verdict}")

    def _on_finished(self, result):
        self._last_result = result
        self.is_test_running = False
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self.execution_logs.stop_timer()
        self._last_report_path = result.summary.get("report_path")
        self.open_report_btn.setEnabled(self._last_report_path is not None)
        self.set_system_status("就绪")
        s = result.summary
        self.execution_logs.append_log(
            f"[DONE] 总体 {s.get('overall', 'N/A')}（PASS {s.get('pass', 0)}/"
            f"FAIL {s.get('fail', 0)}/N/A {s.get('norec', 0)}）"
        )

    def _on_failed(self, msg: str):
        self.is_test_running = False
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self.execution_logs.stop_timer()
        self.set_system_status("测试失败", is_error=True)
        self.execution_logs.append_log(f"[ERROR] {msg}")

    # ------------------------------------------------------------------ actions
    def _on_open_report(self):
        path = self._last_report_path
        if path and os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.execution_logs.append_log("[WARN] 报告文件不存在。")

    def _on_clear_results(self):
        self._last_result = None
        self._last_report_path = None
        self.open_report_btn.setEnabled(False)
        self.execution_logs.clear_log()
        self.execution_logs.set_progress(0)
        self.execution_logs.append_log("[INFO] 已清空结果。")

    def _on_select_all_items(self):
        for row in range(self.items_table.rowCount()):
            chk = self.items_table.item(row, 0)
            if chk and chk.flags() & Qt.ItemIsUserCheckable:
                chk.setCheckState(Qt.Checked)

    # ------------------------------------------------------------------ public API
    def update_test_result(self, result):
        self._last_result = result
        if result is not None and hasattr(result, "summary"):
            self._last_report_path = result.summary.get("report_path")
            self.open_report_btn.setEnabled(self._last_report_path is not None)

    def clear_results(self):
        self._on_clear_results()

    def set_system_status(self, status: str, is_error: bool = False):
        if hasattr(self, "system_status_label"):
            # 兼容 mixin 调用（已带 ● 前缀，如 "● Ready"）与本页调用（如 "就绪"），
            # 避免重复叠加导致 "● ● Ready"
            text = status if status.startswith("●") else f"● {status}"
            self.system_status_label.setText(text)
            # objectName 与全项目标准对齐：statusOk（绿）/statusWarn（黄）/statusErr（红）
            if is_error:
                obj_name = "statusErr"
            elif any(kw in status for kw in ("Searching", "Connecting", "Disconnecting",
                                              "Running", "进行中")):
                obj_name = "statusWarn"
            else:
                obj_name = "statusOk"
            self.system_status_label.setObjectName(obj_name)
            self.system_status_label.style().unpolish(self.system_status_label)
            self.system_status_label.style().polish(self.system_status_label)

    def update_instrument_info(self, instrument_info):
        pass

    def sync_n6705c_from_top(self):
        super().sync_n6705c_from_top()
        self._refresh_scope_item_state()

    def sync_oscilloscope_from_top(self):
        super().sync_oscilloscope_from_top()
        self._refresh_scope_item_state()

    # ------------------------------------------------------------------ AI contract
    def ai_capabilities(self) -> set[str]:
        return {CAP_GET_CONFIG, CAP_APPLY_CONFIG, CAP_START_TEST, CAP_STOP_TEST, CAP_GET_RESULT}

    def ai_get_config(self) -> dict[str, Any] | None:
        try:
            cfg = self.get_test_config()
            cfg["sweep_dimensions"] = ["load_current"]
            # 仅暴露当前勾选项会遍历的维度
            sel = set(cfg.get("selected_items", []))
            if any(k.endswith("_line_reg") for k in sel):
                cfg["sweep_dimensions"].append("vin")
            return cfg
        except Exception:  # noqa: BLE001
            _logger.error("AI 读取 %s 配置失败", self.PAGE_KEY, exc_info=True)
            return None

    def ai_apply_config(self, payload: Any) -> tuple[bool, str]:
        if self.is_test_running:
            return False, "测试运行中，无法修改配置，请先停止测试。"
        return self.apply_config_to_controls(payload if isinstance(payload, dict) else {})

    def ai_start_test(self) -> tuple[bool, str]:
        if not self.is_connected or self.n6705c is None:
            if not DEBUG_MOCK:
                return False, "未连接 N6705C 仪器，请先连接再启动测试。"
        if self.is_test_running:
            return False, "测试已在运行中。"
        cfg = self.get_test_config()
        if not cfg.get("selected_items"):
            return False, "未勾选任何测试项，请先勾选。"
        scope_items = [k for k in cfg["selected_items"]
                       if self.ITEMS_REGISTRY.get(k, (None, None, False, False))[2]]
        if scope_items and not self.scope_connected:
            self.execution_logs.append_log(
                f"[AI] 注意：勾选了示波器项 {scope_items}，但未连接示波器，这些项将跳过。"
            )
        self.execution_logs.append_log(
            f"[AI] 请求启动 {self.MODULE_TYPE.upper()} 测试，勾选 {len(cfg['selected_items'])} 项。"
        )
        try:
            self._on_start_test()
        except Exception:  # noqa: BLE001
            _logger.error("AI 启动 %s 测试失败", self.PAGE_KEY, exc_info=True)
            return False, "启动测试异常，请查看日志。"
        return (True, "已请求启动测试。") if self.is_test_running else (False, "启动未成功，请查看执行日志。")

    def ai_stop_test(self) -> tuple[bool, str]:
        if not self.is_test_running:
            return False, "当前未在运行测试。"
        self.execution_logs.append_log("[AI] 请求停止测试。")
        try:
            self._on_stop_test()
        except Exception:  # noqa: BLE001
            _logger.error("AI 停止 %s 测试失败", self.PAGE_KEY, exc_info=True)
            return False, "停止测试异常，请查看日志。"
        return True, "已发送停止请求。"

    def ai_get_result_summary(self) -> dict[str, Any] | None:
        if self._last_result is None:
            return None
        s = dict(self._last_result.summary)
        s["available"] = True
        s["running"] = self.is_test_running
        s["module_type"] = self._last_result.module_type
        return s

    # ------------------------------------------------------------------ UIActionSpec
    def _register_ai_ui_actions(self):
        if self._ui_action_registry is None:
            return
        self._ui_action_registry.register_many([
            UIActionSpec(
                id=f"{self.PAGE_KEY}.open_report", label="打开报告",
                page_key=self.PAGE_KEY, handler=self._ai_open_report,
                risk="low", confirm=False,
                enabled_when=lambda: self._last_report_path is not None,
                description="打开最近一次 Module Test 的 HTML 报告。",
            ),
            UIActionSpec(
                id=f"{self.PAGE_KEY}.clear_results", label="清空结果",
                page_key=self.PAGE_KEY, handler=self._ai_clear_results,
                risk="low", confirm=False,
            ),
            UIActionSpec(
                id=f"{self.PAGE_KEY}.select_all_items", label="全选测试项",
                page_key=self.PAGE_KEY, handler=self._on_select_all_items,
                risk="low", confirm=False,
            ),
        ])

    def _ai_open_report(self) -> tuple[bool, str]:
        if not self._last_report_path:
            return False, "暂无报告，请先执行测试。"
        self._on_open_report()
        return True, "已打开报告。"

    def _ai_clear_results(self) -> tuple[bool, str]:
        self._on_clear_results()
        return True, "已清空结果。"
