#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 子页面基类（LDO / DCDC 共用）。

规划 §5：仪器连接区 + 通道/被测配置区 + 测试项清单区 + 统一参数区 +
执行/日志区（ExecutionLogsFrame + QSplitter）+ 报告区。
AI 契约（§8.1）与 UIActionSpec 白名单（§8.2）亦在此实现，两个子类仅绑定
module_type / page_key / items 注册表 / runner 类。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout,
    QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
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
from ui.pages.module_test.widgets import CollapsibleGroupBox, DutModeDialog, ItemParamsDialog
from ui.resource_path import get_resource_base, get_user_data_dir
from ui.styles import START_BTN_STYLE, SCROLLBAR_STYLE
from ui.widgets.dark_combobox import DarkComboBox

from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag

_logger = get_logger(__name__)

_AI_HIGHLIGHT_QSS = "border: 1px solid #15d1a3;"
_AI_HIGHLIGHT_MS = 1500
_CONFIG_SCHEMA_VERSION = 1


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
        self._item_overrides: dict[str, dict] = {}
        self._current_config_path: str | None = None

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
            #actionRow {{ border-top: 1px solid #1c2438; background-color: #0a0f1f; }}
            #itemSettingsBtn {{
                border: 1px solid #3a4260; border-radius: 4px; padding: 1px 10px;
                background-color: #1a2138; color: #9aa4bd; font-size: 11px; min-height: 22px;
            }}
            #itemSettingsBtn:hover {{ background-color: #232c48; color: #d8dce8; }}
            #itemSettingsBtn:disabled {{ background-color: #171b28; color: #4a5166; border-color: #262c3e; }}
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
            #save_config_btn, #save_as_config_btn, #open_config_btn {{
                border: 1px solid #35507a; border-radius: 4px; padding: 5px 12px;
                background-color: #1a2942; color: #a9c4ef; min-height: 22px;
            }}
            #save_config_btn:hover, #save_as_config_btn:hover, #open_config_btn:hover {{
                background-color: #223458; color: #d8e4f8;
            }}
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
            QCheckBox {{ color: #c8c8c8; spacing: 6px; background: transparent; }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                image: url("{cb_unchecked}");
            }}
            QCheckBox::indicator:checked {{
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
        content_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(content)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")

        # 顶部 = 可滚动配置区 + 始终可见的操作按钮排（固定在滚动区下方，不随内容滚动）
        top_pane = QWidget()
        top_layout = QVBoxLayout(top_pane)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addWidget(scroll, 1)
        top_layout.addWidget(self._build_action_row(), 0)

        self._splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            top_pane, title=f"{self.MODULE_TYPE.upper()} Module Test 执行日志", stretch=(5, 2),
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

        grid.addWidget(self._field_label("模块名称"), 0, 2)
        self.module_name_edit = QLineEdit()
        self.module_name_edit.setPlaceholderText("如 LDO1 / DCDC_CORE")
        grid.addWidget(self.module_name_edit, 0, 3)

        grid.addWidget(self._field_label("操作员"), 1, 0)
        self.operator_edit = QLineEdit()
        grid.addWidget(self.operator_edit, 1, 1)

        grid.addWidget(self._field_label("Vin 通道"), 2, 0)
        self.vin_ch_combo = DarkComboBox()
        self.vin_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        grid.addWidget(self.vin_ch_combo, 2, 1)

        grid.addWidget(self._field_label("Vout 通道"), 2, 2)
        self.vout_ch_combo = DarkComboBox()
        self.vout_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        self.vout_ch_combo.setCurrentIndex(1)
        grid.addWidget(self.vout_ch_combo, 2, 3)

        grid.addWidget(self._field_label("Iload 通道"), 3, 0)
        self.iload_ch_combo = DarkComboBox()
        self.iload_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        self.iload_ch_combo.setCurrentIndex(2)
        grid.addWidget(self.iload_ch_combo, 3, 1)

        grid.addWidget(self._field_label("Vout 标称 (mV)"), 3, 2)
        self.vout_nominal_spin = QSpinBox()
        self.vout_nominal_spin.setRange(0, 6000)
        self.vout_nominal_spin.setValue(1800 if self.MODULE_TYPE == "ldo" else 1200)
        grid.addWidget(self.vout_nominal_spin, 3, 3)

        grid.addWidget(self._field_label("Device 地址"), 4, 0)
        self.device_addr_edit = QLineEdit("0x00")
        self.device_addr_edit.setPlaceholderText("如 0x62")
        grid.addWidget(self.device_addr_edit, 4, 1)

        grid.addWidget(self._field_label("Width Flag"), 4, 2)
        self.width_flag_combo = DarkComboBox()
        self.width_flag_combo.addItem("8-bit", int(I2CWidthFlag.BIT_8))
        self.width_flag_combo.addItem("10-bit", int(I2CWidthFlag.BIT_10))
        self.width_flag_combo.addItem("32-bit", int(I2CWidthFlag.BIT_32))
        self.width_flag_combo.setCurrentIndex(1)
        grid.addWidget(self.width_flag_combo, 4, 3)

        # —— 高低温测试（勾选后展开温度相关设置）——
        self.temp_test_check = QCheckBox("高低温测试")
        self.temp_test_check.setChecked(False)
        self.temp_test_check.toggled.connect(self._on_temp_test_toggled)
        grid.addWidget(self.temp_test_check, 5, 0, 1, 4)

        self._temp_label = self._field_label("温度点 (°C)")
        grid.addWidget(self._temp_label, 6, 0)
        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("逗号分隔，如 -40, 25, 85")
        grid.addWidget(self.temperature_edit, 6, 1)

        self._temp_soak_label = self._field_label("等待时间 (s)")
        grid.addWidget(self._temp_soak_label, 6, 2)
        self.temp_soak_spin = QSpinBox()
        self.temp_soak_spin.setRange(0, 36000)
        self.temp_soak_spin.setValue(300)
        grid.addWidget(self.temp_soak_spin, 6, 3)

        self._temp_tol_label = self._field_label("稳定条件 (°C)")
        grid.addWidget(self._temp_tol_label, 7, 0)
        self.temp_tolerance_spin = QSpinBox()
        self.temp_tolerance_spin.setRange(1, 20)
        self.temp_tolerance_spin.setValue(2)
        grid.addWidget(self.temp_tolerance_spin, 7, 1)

        self._temp_wait_label = self._field_label("稳定超时 (s)")
        grid.addWidget(self._temp_wait_label, 7, 2)
        self.temp_wait_spin = QSpinBox()
        self.temp_wait_spin.setRange(0, 36000)
        self.temp_wait_spin.setValue(1800)
        grid.addWidget(self.temp_wait_spin, 7, 3)

        self._temp_widgets = [
            self._temp_label, self.temperature_edit,
            self._temp_soak_label, self.temp_soak_spin,
            self._temp_tol_label, self.temp_tolerance_spin,
            self._temp_wait_label, self.temp_wait_spin,
        ]
        self._on_temp_test_toggled(False)
        box.content_layout.addLayout(grid)
        box.content_layout.addWidget(self._build_dut_modes_area())
        return box

    def _build_dut_modes_area(self) -> "CollapsibleGroupBox":
        """DUT 工作模式管理区（跨测试项共享的模式声明源）。"""
        self._dut_modes: list[dict] = []
        area = CollapsibleGroupBox("DUT 工作模式管理", expanded=False)
        lay = area.content_layout

        self.dut_modes_table = QTableWidget(0, 4)
        self.dut_modes_table.setObjectName("dutModesTable")
        self.dut_modes_table.setHorizontalHeaderLabels(["模式名", "进入方式", "关键参数摘要", ""])
        self.dut_modes_table.verticalHeader().setVisible(False)
        self.dut_modes_table.verticalHeader().setDefaultSectionSize(26)
        self.dut_modes_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.dut_modes_table.setSelectionMode(QTableWidget.SingleSelection)
        self.dut_modes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.dut_modes_table.setShowGrid(False)
        self.dut_modes_table.setAlternatingRowColors(True)
        self.dut_modes_table.setMaximumHeight(150)
        mh = self.dut_modes_table.horizontalHeader()
        mh.setHighlightSections(False)
        mh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        mh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        mh.setSectionResizeMode(2, QHeaderView.Stretch)
        mh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.dut_modes_table.doubleClicked.connect(lambda _idx: self._on_edit_dut_mode())
        lay.addWidget(self.dut_modes_table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.dut_mode_add_btn = QPushButton("+ 添加模式")
        self.dut_mode_add_btn.setObjectName("dutModeBtn")
        self.dut_mode_add_btn.clicked.connect(self._on_add_dut_mode)
        self.dut_mode_edit_btn = QPushButton("编辑")
        self.dut_mode_edit_btn.setObjectName("dutModeBtn")
        self.dut_mode_edit_btn.clicked.connect(self._on_edit_dut_mode)
        self.dut_mode_del_btn = QPushButton("删除")
        self.dut_mode_del_btn.setObjectName("dutModeBtn")
        self.dut_mode_del_btn.clicked.connect(self._on_delete_dut_mode)
        btn_row.addWidget(self.dut_mode_add_btn)
        btn_row.addWidget(self.dut_mode_edit_btn)
        btn_row.addWidget(self.dut_mode_del_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self._field_label("默认基准模式"))
        self.default_mode_combo = DarkComboBox()
        self.default_mode_combo.setObjectName("defaultModeCombo")
        self.default_mode_combo.setMinimumWidth(140)
        btn_row.addWidget(self.default_mode_combo)
        lay.addLayout(btn_row)

        area.setStyleSheet(area.styleSheet() + """
            QPushButton#dutModeBtn { min-height: 22px; padding: 2px 10px; }
            QComboBox#defaultModeCombo { min-height: 22px; padding: 1px 6px; }
            QTableWidget#dutModesTable { background-color: #0e1526; border: 1px solid #2f374d; }
        """)
        return area

    # ------------------------------------------------------------------ DUT modes
    @staticmethod
    def _dut_mode_summary(mode: dict) -> str:
        """生成模式关键参数摘要文本（表格第 3 列）。"""
        enter = str(mode.get("enter", "reg"))
        if enter == "reg":
            writes = mode.get("reg_writes") or []
            parts = [f"{w.get('addr', '?')}={w.get('value', '?')}" for w in writes
                     if isinstance(w, dict)]
            return "; ".join(parts) if parts else "无寄存器写入"
        if enter == "load":
            txt = f"{float(mode.get('load_ma', 0.0)):g} mA"
            rb = mode.get("mode_readback")
            if isinstance(rb, dict):
                txt += f"  回读 {rb.get('addr', '?')}[{rb.get('msb', '?')}:{rb.get('lsb', '?')}]=={rb.get('expect', '?')}"
            return txt
        return f"提示: {mode.get('prompt', '') or '手动切换后确认'}"

    def _refresh_dut_modes_table(self) -> None:
        self.dut_modes_table.setRowCount(0)
        for mode in self._dut_modes:
            row = self.dut_modes_table.rowCount()
            self.dut_modes_table.insertRow(row)
            self.dut_modes_table.setItem(row, 0, QTableWidgetItem(str(mode.get("name", ""))))
            self.dut_modes_table.setItem(row, 1, QTableWidgetItem(str(mode.get("enter", "reg"))))
            self.dut_modes_table.setItem(row, 2, QTableWidgetItem(self._dut_mode_summary(mode)))
            self.dut_modes_table.setItem(row, 3, QTableWidgetItem(""))
        # 刷新默认基准模式下拉，尽量保留原选择
        prev = self.default_mode_combo.currentText()
        self.default_mode_combo.blockSignals(True)
        self.default_mode_combo.clear()
        names = [str(m.get("name", "")) for m in self._dut_modes]
        self.default_mode_combo.addItems(names)
        if prev in names:
            self.default_mode_combo.setCurrentText(prev)
        self.default_mode_combo.blockSignals(False)

    def _selected_dut_mode_row(self) -> int:
        rows = self.dut_modes_table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _on_add_dut_mode(self) -> None:
        dlg = DutModeDialog(existing_names=[m.get("name") for m in self._dut_modes], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._dut_modes.append(dlg.get_mode())
            self._refresh_dut_modes_table()

    def _on_edit_dut_mode(self) -> None:
        row = self._selected_dut_mode_row()
        if row < 0:
            self.execution_logs.append_log("[WARN] 请先选中要编辑的模式。")
            return
        others = [m.get("name") for i, m in enumerate(self._dut_modes) if i != row]
        dlg = DutModeDialog(existing_names=others, mode=self._dut_modes[row], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._dut_modes[row] = dlg.get_mode()
            self._refresh_dut_modes_table()

    def _on_delete_dut_mode(self) -> None:
        row = self._selected_dut_mode_row()
        if row < 0:
            self.execution_logs.append_log("[WARN] 请先选中要删除的模式。")
            return
        del self._dut_modes[row]
        self._refresh_dut_modes_table()

    def _apply_dut_modes(self, cfg: dict) -> None:
        """把配置里的 dut_modes / default_mode 回填到控件（配置加载 & AI 共用）。"""
        modes = cfg.get("dut_modes")
        if isinstance(modes, list):
            self._dut_modes = [dict(m) for m in modes if isinstance(m, dict)]
            self._refresh_dut_modes_table()
        default_mode = cfg.get("default_mode")
        if isinstance(default_mode, str) and default_mode:
            idx = self.default_mode_combo.findText(default_mode)
            if idx >= 0:
                self.default_mode_combo.setCurrentIndex(idx)

    def _on_temp_test_toggled(self, checked: bool) -> None:
        """高低温测试勾选联动：勾选后才显示温度相关设置。"""
        for w in self._temp_widgets:
            w.setVisible(checked)

    def _build_items_group(self) -> "CollapsibleGroupBox":
        box = CollapsibleGroupBox("测试项清单（勾选要执行的项）", expanded=True)
        lay = box.content_layout
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["选", "测试项", "主要仪器", "判定/记录", "参数"])
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
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.items_table.setColumnWidth(0, 44)
        self.items_table.setColumnWidth(4, 64)
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

    def _build_action_row(self) -> QWidget:
        row = QWidget()
        row.setObjectName("actionRow")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        self.start_test_btn = QPushButton("▶ 开始测试")
        self.start_test_btn.setObjectName("start_test_btn")
        self.start_test_btn.setCursor(Qt.PointingHandCursor)
        self.stop_test_btn = QPushButton("■ 停止")
        self.stop_test_btn.setObjectName("stop_test_btn")
        self.stop_test_btn.setEnabled(False)
        self.save_config_btn = QPushButton("保存")
        self.save_config_btn.setObjectName("save_config_btn")
        self.save_config_btn.setToolTip("保存当前完整配置（设置 + 测试项）；已加载的配置直接覆盖，否则等同另存为")
        self.save_as_config_btn = QPushButton("另存为")
        self.save_as_config_btn.setObjectName("save_as_config_btn")
        self.save_as_config_btn.setToolTip("基于当前设置生成新的配置文件，便于快速派生相似但有区别的配置")
        self.open_config_btn = QPushButton("打开")
        self.open_config_btn.setObjectName("open_config_btn")
        self.open_config_btn.setToolTip("按芯片名称分类浏览并加载已保存的配置")
        self.select_all_btn = QPushButton("全选测试项")
        self.select_all_btn.setObjectName("select_all_btn")
        self.clear_results_btn = QPushButton("清空结果")
        self.clear_results_btn.setObjectName("clear_results_btn")
        self.open_report_btn = QPushButton("打开报告")
        self.open_report_btn.setObjectName("open_report_btn")
        self.open_report_btn.setEnabled(False)
        for _btn in (self.save_config_btn, self.save_as_config_btn, self.open_config_btn,
                     self.select_all_btn, self.clear_results_btn, self.open_report_btn):
            _btn.setMinimumWidth(64)
            _btn.setCursor(Qt.PointingHandCursor)

        self.start_test_btn.clicked.connect(self._on_start_test)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.save_config_btn.clicked.connect(self._on_save_config)
        self.save_as_config_btn.clicked.connect(self._on_save_config_as)
        self.open_config_btn.clicked.connect(self._on_open_config)
        self.select_all_btn.clicked.connect(self._on_select_all_items)
        self.clear_results_btn.clicked.connect(self._on_clear_results)
        self.open_report_btn.clicked.connect(self._on_open_report)

        lay.addWidget(self.start_test_btn)
        lay.addWidget(self.stop_test_btn)
        lay.addStretch()
        lay.addWidget(self.save_config_btn)
        lay.addWidget(self.save_as_config_btn)
        lay.addWidget(self.open_config_btn)
        lay.addWidget(self.select_all_btn)
        lay.addWidget(self.clear_results_btn)
        lay.addWidget(self.open_report_btn)
        return row

    # ------------------------------------------------------------------ items table
    def _populate_item_table(self):
        self.items_table.setRowCount(0)
        for item_key, spec in self.ITEMS_REGISTRY.items():
            name, _run_fn, needs_scope, item_checked, _params = spec
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
            self.items_table.setCellWidget(row, 4, self._make_settings_cell(item_key, _params))

    def _make_settings_cell(self, item_key: str, params) -> QWidget:
        cell = QWidget()
        cell.setStyleSheet("background: transparent;")
        h = QHBoxLayout(cell)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        btn = QPushButton("设置")
        btn.setObjectName("itemSettingsBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(22)
        if not params:
            btn.setEnabled(False)
            btn.setToolTip("该测试项暂无可设置参数")
        else:
            btn.clicked.connect(lambda _=False, k=item_key: self._open_item_params(k))
        h.addWidget(btn, alignment=Qt.AlignCenter)
        return cell

    def _open_item_params(self, item_key: str):
        spec = self.ITEMS_REGISTRY.get(item_key)
        if not spec:
            return
        name, _run_fn, _needs_scope, _checked, params = spec
        dlg = ItemParamsDialog(
            title=f"参数设置 - {name}",
            specs=params,
            current_override=self._item_overrides.get(item_key, {}),
            base_value_fn=self._base_param_value,
            parent=self,
        )
        if dlg.exec():
            override = dlg.get_override()
            if override:
                self._item_overrides[item_key] = override
            else:
                self._item_overrides.pop(item_key, None)
            self._mark_item_customized(item_key)

    def _mark_item_customized(self, item_key: str):
        """在测试项名后打标，直观区分已自定义参数的项。"""
        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 1)
            if name_item and name_item.data(Qt.UserRole) == item_key:
                base_name = self.ITEMS_REGISTRY[item_key][0]
                if item_key in self._item_overrides:
                    name_item.setText(f"{base_name}  ●")
                    name_item.setForeground(QColor("#8eb0e3"))
                else:
                    name_item.setText(base_name)
                    name_item.setForeground(QColor("#c8c8c8"))
                break

    def _base_param_value(self, base_key: str):
        """按 ParamSpec.base_key 从被测配置界面取当前值作弹窗预填。"""
        cfg = self.get_test_config()
        return cfg.get(base_key)

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
        temp_enabled = self.temp_test_check.isChecked()
        return {
            "selected_items": self._selected_item_keys(),
            "chip_name": self.chip_name_edit.text().strip(),
            "module_name": self.module_name_edit.text().strip(),
            "operator": self.operator_edit.text().strip(),
            "temp_test_enabled": temp_enabled,
            "temperature": self.temperature_edit.text().strip() if temp_enabled else "",
            "temp_soak_s": self.temp_soak_spin.value(),
            "temp_tolerance_c": self.temp_tolerance_spin.value(),
            "temp_wait_s": self.temp_wait_spin.value(),
            "vin_channel": self.vin_ch_combo.currentText(),
            "vout_channel": self.vout_ch_combo.currentText(),
            "iload_channel": self.iload_ch_combo.currentText(),
            "vout_nominal_mv": self.vout_nominal_spin.value(),
            "device_addr": self.device_addr_edit.text().strip(),
            "width_flag": self.width_flag_combo.currentData(),
            "dut_modes": [dict(m) for m in self._dut_modes],
            "default_mode": self.default_mode_combo.currentText(),
            "item_overrides": {k: dict(v) for k, v in self._item_overrides.items()},
        }

    def apply_config_to_controls(self, cfg: dict) -> tuple[bool, str]:
        if not isinstance(cfg, dict):
            return False, "配置草案格式无效（期望 dict）。"
        changed: list[str] = []
        try:
            if "chip_name" in cfg:
                self.chip_name_edit.setText(str(cfg["chip_name"])); changed.append("chip_name")
            if "module_name" in cfg:
                self.module_name_edit.setText(str(cfg["module_name"])); changed.append("module_name")
            if "operator" in cfg:
                self.operator_edit.setText(str(cfg["operator"])); changed.append("operator")
            if "vout_nominal_mv" in cfg:
                self.vout_nominal_spin.setValue(int(cfg["vout_nominal_mv"])); changed.append("vout_nominal_mv")
            if "dut_modes" in cfg or "default_mode" in cfg:
                self._apply_dut_modes(cfg); changed.append("dut_modes")
        except Exception:  # noqa: BLE001
            _logger.error("apply_config 落地失败", exc_info=True)
            return False, "配置落地异常，见日志。"
        QTimer.singleShot(0, lambda: self._highlight_fields(changed))
        return True, f"已应用配置：{', '.join(changed) if changed else '无变更'}"

    def _highlight_fields(self, fields: list[str]):
        widget_map = {
            "chip_name": self.chip_name_edit, "module_name": self.module_name_edit,
            "operator": self.operator_edit,
            "vout_nominal_mv": self.vout_nominal_spin,
            "dut_modes": self.dut_modes_table,
        }
        for f in fields:
            w = widget_map.get(f)
            if w is None:
                continue
            orig = w.styleSheet()
            w.setStyleSheet(_AI_HIGHLIGHT_QSS)
            QTimer.singleShot(_AI_HIGHLIGHT_MS, lambda _w=w, _o=orig: _w.setStyleSheet(_o))

    # ------------------------------------------------------------------ config file IO
    def _configs_root(self) -> str:
        """配置文件根目录：user_data/module_test_configs/<module_type>。"""
        return get_user_data_dir("module_test_configs", self.MODULE_TYPE)

    @staticmethod
    def _safe_name(text: str, fallback: str) -> str:
        """把用户输入清洗成合法文件/目录名。"""
        cleaned = re.sub(r'[\\/:*?"<>|]+', "_", (text or "").strip()).strip(" .")
        return cleaned or fallback

    def _restore_full_config(self, cfg: dict) -> None:
        """把一份完整配置回填到所有控件（含通道 / 温度 / 频点 / 测试项勾选 / 参数覆写）。"""
        def _set_combo(combo, value):
            if value is None:
                return
            idx = combo.findText(str(value))
            if idx >= 0:
                combo.setCurrentIndex(idx)

        if "chip_name" in cfg:
            self.chip_name_edit.setText(str(cfg["chip_name"]))
        if "module_name" in cfg:
            self.module_name_edit.setText(str(cfg["module_name"]))
        if "operator" in cfg:
            self.operator_edit.setText(str(cfg["operator"]))
        _set_combo(self.vin_ch_combo, cfg.get("vin_channel"))
        _set_combo(self.vout_ch_combo, cfg.get("vout_channel"))
        _set_combo(self.iload_ch_combo, cfg.get("iload_channel"))
        if "vout_nominal_mv" in cfg:
            self.vout_nominal_spin.setValue(int(cfg["vout_nominal_mv"]))
        if "device_addr" in cfg:
            self.device_addr_edit.setText(str(cfg["device_addr"]))
        if "width_flag" in cfg:
            idx = self.width_flag_combo.findData(int(cfg["width_flag"]))
            if idx >= 0:
                self.width_flag_combo.setCurrentIndex(idx)

        self._apply_dut_modes(cfg)
        if "temp_test_enabled" in cfg:
            self.temp_test_check.setChecked(bool(cfg["temp_test_enabled"]))
        if "temperature" in cfg:
            self.temperature_edit.setText(str(cfg["temperature"]))
        if "temp_soak_s" in cfg:
            self.temp_soak_spin.setValue(int(cfg["temp_soak_s"]))
        if "temp_tolerance_c" in cfg:
            self.temp_tolerance_spin.setValue(int(cfg["temp_tolerance_c"]))
        if "temp_wait_s" in cfg:
            self.temp_wait_spin.setValue(int(cfg["temp_wait_s"]))

        # 测试项勾选
        selected = cfg.get("selected_items")
        if isinstance(selected, list):
            sel_set = set(selected)
            for row in range(self.items_table.rowCount()):
                chk = self.items_table.item(row, 0)
                name_item = self.items_table.item(row, 1)
                if chk is None or name_item is None:
                    continue
                if not (chk.flags() & Qt.ItemIsUserCheckable):
                    continue  # 未接示波器等被禁用的项不强行勾选
                key = name_item.data(Qt.UserRole)
                chk.setCheckState(Qt.Checked if key in sel_set else Qt.Unchecked)

        # 参数覆写
        overrides = cfg.get("item_overrides")
        if isinstance(overrides, dict):
            self._item_overrides = {k: dict(v) for k, v in overrides.items()
                                    if k in self.ITEMS_REGISTRY and isinstance(v, dict)}
            for k in self.ITEMS_REGISTRY:
                self._mark_item_customized(k)

        self._refresh_scope_item_state()

    def _write_config_file(self, path: str, cfg: dict) -> bool:
        payload = {
            "schema_version": _CONFIG_SCHEMA_VERSION,
            "module_type": self.MODULE_TYPE,
            "config": cfg,
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            _logger.error("写入配置文件失败：%s", path, exc_info=True)
            return False

    def _read_config_file(self, path: str) -> dict | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            _logger.error("读取配置文件失败：%s", path, exc_info=True)
            return None
        if not isinstance(payload, dict):
            return None
        cfg = payload.get("config")
        return cfg if isinstance(cfg, dict) else None

    def _save_config_to(self, path: str) -> None:
        cfg = self.get_test_config()
        if self._write_config_file(path, cfg):
            self._current_config_path = path
            self.execution_logs.append_log(f"[INFO] 配置已保存：{os.path.basename(path)}")
        else:
            QMessageBox.warning(self, "保存失败", "配置写入失败，详见日志。")

    def _prompt_save_path(self) -> str | None:
        """弹出命名对话框，按芯片名分类到子目录，返回目标路径。"""
        cfg = self.get_test_config()
        chip = self._safe_name(cfg.get("chip_name", ""), "未分类芯片")
        default_name = self._safe_name(
            cfg.get("module_name", "") or self.MODULE_TYPE, self.MODULE_TYPE)
        name, ok = QInputDialog.getText(
            self, "另存配置", f"配置名称（将归入芯片「{chip}」分类）：", text=default_name)
        if not ok:
            return None
        name = self._safe_name(name, default_name)
        target_dir = os.path.join(self._configs_root(), chip)
        path = os.path.join(target_dir, f"{name}.json")
        if os.path.exists(path):
            resp = QMessageBox.question(
                self, "覆盖确认", f"配置「{name}」已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                return None
        return path

    def _on_save_config(self) -> None:
        """保存：已加载/已保存过则直接覆盖当前文件；否则等同另存为。"""
        if self._current_config_path:
            self._save_config_to(self._current_config_path)
        else:
            self._on_save_config_as()

    def _on_save_config_as(self) -> None:
        """另存为：基于当前设置生成新配置文件，便于派生相似配置。"""
        path = self._prompt_save_path()
        if path:
            self._save_config_to(path)

    def _on_open_config(self) -> None:
        dlg = _ConfigPickerDialog(self._configs_root(), self.MODULE_TYPE, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        path = dlg.selected_path()
        if not path:
            return
        cfg = self._read_config_file(path)
        if cfg is None:
            QMessageBox.warning(self, "打开失败", "配置文件无效或损坏，详见日志。")
            return
        self._restore_full_config(cfg)
        self._current_config_path = path
        self.execution_logs.append_log(f"[INFO] 已加载配置：{os.path.basename(path)}")

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
        self._runner.mode_confirm_required.connect(self._on_mode_confirm_required)
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

    def _on_mode_confirm_required(self, prompt: str):
        """手动模式暂停：弹确认框，用户确认/取消后唤醒测试线程。"""
        if self._runner is None:
            return
        self.execution_logs.append_log(f"[PAUSE] {prompt}")
        resp = QMessageBox.question(
            self, "手动切换 DUT 模式", prompt,
            QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)
        confirmed = resp == QMessageBox.Ok
        self.execution_logs.append_log(
            "[RESUME] 已确认，继续测试" if confirmed else "[RESUME] 已取消该模式")
        self._runner.confirm_mode(confirmed)

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
            # 仅当勾选了 quiescent（会遍历 dut_modes）时才计入模式维度，避免误导 AI 臆造组合
            if any(k.endswith("_quiescent") for k in sel) and cfg.get("dut_modes"):
                cfg["sweep_dimensions"].append("dut_modes")
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


class _ConfigPickerDialog(QDialog):
    """按芯片名称分类展示已保存配置的选择对话框。

    目录结构：<root>/<芯片名>/<配置名>.json；顶层节点为芯片分类，子节点为配置。
    """

    def __init__(self, root: str, module_type: str, parent=None):
        super().__init__(parent)
        self._root = root
        self.setWindowTitle(f"打开 {module_type.upper()} 配置")
        self.setMinimumSize(420, 420)
        self._selected_path: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel("按芯片名称分类，双击或选中后点“打开”："))

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.currentItemChanged.connect(self._on_current_changed)
        layout.addWidget(self.tree, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel, parent=self)
        self._open_btn = buttons.button(QDialogButtonBox.Open)
        self._open_btn.setText("打开")
        self._open_btn.setDefault(True)
        self._open_btn.setAutoDefault(True)
        self._open_btn.setEnabled(False)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        cancel_btn.setText("取消")
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        self.tree.clear()
        if not os.path.isdir(self._root):
            placeholder = QTreeWidgetItem(["（暂无已保存的配置）"])
            placeholder.setFlags(Qt.ItemIsEnabled)
            self.tree.addTopLevelItem(placeholder)
            return
        chip_dirs = sorted(
            d for d in os.listdir(self._root)
            if os.path.isdir(os.path.join(self._root, d))
        )
        has_any = False
        for chip in chip_dirs:
            chip_path = os.path.join(self._root, chip)
            files = sorted(
                f for f in os.listdir(chip_path)
                if f.lower().endswith(".json")
            )
            if not files:
                continue
            chip_node = QTreeWidgetItem([chip])
            chip_node.setFlags(Qt.ItemIsEnabled)
            self.tree.addTopLevelItem(chip_node)
            for f in files:
                cfg_node = QTreeWidgetItem([os.path.splitext(f)[0]])
                cfg_node.setData(0, Qt.UserRole, os.path.join(chip_path, f))
                chip_node.addChild(cfg_node)
            chip_node.setExpanded(True)
            has_any = True
        if not has_any:
            placeholder = QTreeWidgetItem(["（暂无已保存的配置）"])
            placeholder.setFlags(Qt.ItemIsEnabled)
            self.tree.addTopLevelItem(placeholder)

    def _on_current_changed(self, current: QTreeWidgetItem, _prev) -> None:
        path = current.data(0, Qt.UserRole) if current else None
        self._open_btn.setEnabled(bool(path))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        if item and item.data(0, Qt.UserRole):
            self._selected_path = item.data(0, Qt.UserRole)
            self.accept()

    def _accept_selection(self) -> None:
        item = self.tree.currentItem()
        path = item.data(0, Qt.UserRole) if item else None
        if path:
            self._selected_path = path
            self.accept()

    def selected_path(self) -> str | None:
        return self._selected_path
