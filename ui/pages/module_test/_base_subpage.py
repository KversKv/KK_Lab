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
import shutil
from typing import Any

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont
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
from ui.pages.module_test.widgets import (
    CollapsibleGroupBox, DIALOG_QSS, ItemParamsDialog,
)
from ui.resource_path import get_resource_base, get_user_data_dir
from ui.styles import START_BTN_STYLE, get_page_base_qss, get_table_qss
from ui.theme import Colors, FontSizes, Radius
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
        """页面样式 = 全局基础 QSS + 表格 QSS + START/STOP 按钮样式 + 本页增量。

        与 GPADC / VminHunter 等页面保持一致：色板只取 ui.theme token，
        控件高度只用 ID 选择器钉死（§24.1），不手写页面级色值。
        """
        self.setFont(QFont("Segoe UI", 9))
        self.setObjectName("moduleTestRoot")
        icons_dir = os.path.join(get_resource_base(), "resources", "icons")
        cb_checked = os.path.join(icons_dir, "checked_4f46e5.svg").replace("\\", "/")
        cb_unchecked = os.path.join(icons_dir, "unchecked_4f46e5.svg").replace("\\", "/")
        page_extra = f"""
            QWidget#moduleTestRoot {{
                background-color: {Colors.bg_secondary};
            }}
            QWidget#moduleTestContent {{
                background: transparent;
            }}
            QWidget#actionRow {{
                background-color: {Colors.bg_panel};
                border-top: 1px solid {Colors.border_primary};
            }}
            QCheckBox::indicator, QTableWidget::indicator {{
                width: 16px;
                height: 16px;
                image: url("{cb_unchecked}");
            }}
            QCheckBox::indicator:checked, QTableWidget::indicator:checked {{
                image: url("{cb_checked}");
            }}
            QTableWidget {{
                alternate-background-color: {Colors.bg_panel};
            }}
            QPushButton#stopBtn:disabled {{
                background-color: {Colors.disabled_btn_bg};
                color: {Colors.disabled_text};
                border: 1px solid {Colors.disabled_btn_border};
            }}
            /* 操作行按钮统一 35px：Qt QSS 盒模型 total = content(min/max-height) + 上下padding + 2×border(1px)。
               目标 35 = content 33 + padding 0 + border 2，故 min/max-height 取 33 */
            QPushButton#primaryStartBtn, QPushButton#stopBtn,
            QPushButton#select_all_btn, QPushButton#clear_results_btn, QPushButton#open_report_btn {{
                min-height: 33px;
                max-height: 33px;
                padding-top: 0px;
                padding-bottom: 0px;
            }}
            QPushButton#itemSettingsBtn {{
                min-height: 22px;
                padding: 1px 10px;
                font-size: {FontSizes.caption};
            }}
            QPushButton#dutModeBtn {{
                min-height: 22px;
                padding: 2px 10px;
            }}
            QComboBox#defaultModeCombo {{
                min-height: 22px;
                padding: 1px 6px;
            }}
        """
        self.setStyleSheet(
            get_page_base_qss() + get_table_qss() + START_BTN_STYLE + page_extra
        )

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        content = QWidget()
        content.setObjectName("moduleTestContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)

        # 仪器连接 + 被测配置 并排一行，测试项清单整宽置于下方
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.addWidget(self._build_connection_group(), 1)
        top_row.addWidget(self._build_config_group(), 1)
        content_layout.addLayout(top_row)
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
        box = CollapsibleGroupBox("Instrument Connection", expanded=True)
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
        box = CollapsibleGroupBox("DUT Configuration", expanded=True)

        # 配置管理按钮行（打开 / 保存 / 另存为），置于配置区最上方
        cfg_btn_row = QHBoxLayout()
        cfg_btn_row.setSpacing(8)
        self.open_config_btn = QPushButton("打开")
        self.open_config_btn.setObjectName("open_config_btn")
        self.open_config_btn.setToolTip("按芯片名称分类浏览并加载已保存的配置")
        self.save_config_btn = QPushButton("保存")
        self.save_config_btn.setObjectName("save_config_btn")
        self.save_config_btn.setToolTip("保存当前完整配置（设置 + 测试项）；已加载的配置直接覆盖，否则等同另存为")
        self.save_as_config_btn = QPushButton("另存为")
        self.save_as_config_btn.setObjectName("save_as_config_btn")
        self.save_as_config_btn.setToolTip("基于当前设置生成新的配置文件，便于快速派生相似但有区别的配置")
        for _btn in (self.open_config_btn, self.save_config_btn, self.save_as_config_btn):
            _btn.setMinimumWidth(64)
            _btn.setCursor(Qt.PointingHandCursor)
        self.open_config_btn.clicked.connect(self._on_open_config)
        self.save_config_btn.clicked.connect(self._on_save_config)
        self.save_as_config_btn.clicked.connect(self._on_save_config_as)
        cfg_btn_row.addWidget(self.open_config_btn)
        cfg_btn_row.addWidget(self.save_config_btn)
        cfg_btn_row.addWidget(self.save_as_config_btn)
        cfg_btn_row.addStretch()
        box.content_layout.addLayout(cfg_btn_row)

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

        # —— Vout 外供源通道（静态电流差分测法用，供 Vout+偏置）——
        grid.addWidget(self._field_label("Vout 源通道"), 5, 0)
        self.vout_src_ch_combo = DarkComboBox()
        self.vout_src_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        self.vout_src_ch_combo.setCurrentIndex(1)
        grid.addWidget(self.vout_src_ch_combo, 5, 1)

        # —— 示波器输出电压通道（各 scope 测试项共用的 Vout 测量通道）——
        grid.addWidget(self._field_label("示波器通道"), 5, 2)
        self.scope_vout_ch_combo = DarkComboBox()
        self.scope_vout_ch_combo.addItems([f"CH {i}" for i in range(1, 5)])
        self.scope_vout_ch_combo.setCurrentIndex(0)
        grid.addWidget(self.scope_vout_ch_combo, 5, 3)

        # —— 高低温测试（勾选后展开温度相关设置）——
        self.temp_test_check = QCheckBox("高低温测试")
        self.temp_test_check.setChecked(False)
        self.temp_test_check.toggled.connect(self._on_temp_test_toggled)
        grid.addWidget(self.temp_test_check, 6, 0, 1, 4)

        self._temp_label = self._field_label("温度点 (°C)")
        grid.addWidget(self._temp_label, 7, 0)
        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("逗号分隔，如 -40, 25, 85")
        grid.addWidget(self.temperature_edit, 7, 1)

        self._temp_soak_label = self._field_label("等待时间 (s)")
        grid.addWidget(self._temp_soak_label, 7, 2)
        self.temp_soak_spin = QSpinBox()
        self.temp_soak_spin.setRange(0, 36000)
        self.temp_soak_spin.setValue(300)
        grid.addWidget(self.temp_soak_spin, 7, 3)

        self._temp_tol_label = self._field_label("稳定条件 (°C)")
        grid.addWidget(self._temp_tol_label, 8, 0)
        self.temp_tolerance_spin = QSpinBox()
        self.temp_tolerance_spin.setRange(1, 20)
        self.temp_tolerance_spin.setValue(2)
        grid.addWidget(self.temp_tolerance_spin, 8, 1)

        self._temp_wait_label = self._field_label("稳定超时 (s)")
        grid.addWidget(self._temp_wait_label, 8, 2)
        self.temp_wait_spin = QSpinBox()
        self.temp_wait_spin.setRange(0, 36000)
        self.temp_wait_spin.setValue(1800)
        grid.addWidget(self.temp_wait_spin, 8, 3)

        self._temp_widgets = [
            self._temp_label, self.temperature_edit,
            self._temp_soak_label, self.temp_soak_spin,
            self._temp_tol_label, self.temp_tolerance_spin,
            self._temp_wait_label, self.temp_wait_spin,
        ]
        self._on_temp_test_toggled(False)
        box.content_layout.addLayout(grid)
        return box

    def _on_temp_test_toggled(self, checked: bool) -> None:
        """高低温测试勾选联动：勾选后才显示温度相关设置。"""
        for w in self._temp_widgets:
            w.setVisible(checked)

    def _build_items_group(self) -> "CollapsibleGroupBox":
        box = CollapsibleGroupBox("Test Items (check to run)", expanded=True)
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
        self.start_test_btn.setObjectName("primaryStartBtn")
        self.start_test_btn.setCursor(Qt.PointingHandCursor)
        self.stop_test_btn = QPushButton("■ 停止")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.setEnabled(False)
        self.select_all_btn = QPushButton("全选测试项")
        self.select_all_btn.setObjectName("select_all_btn")
        self.clear_results_btn = QPushButton("清空结果")
        self.clear_results_btn.setObjectName("clear_results_btn")
        self.open_report_btn = QPushButton("打开报告")
        self.open_report_btn.setObjectName("open_report_btn")
        self.open_report_btn.setEnabled(False)
        for _btn in (self.select_all_btn, self.clear_results_btn, self.open_report_btn):
            _btn.setMinimumWidth(64)
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
            inst_item.setForeground(QColor(Colors.warning if needs_scope else Colors.info))
            inst_item.setData(Qt.UserRole, needs_scope)
            self.items_table.setItem(row, 2, inst_item)
            rec_item = QTableWidgetItem("记录")
            rec_item.setFlags(Qt.ItemIsEnabled)
            rec_item.setForeground(QColor(Colors.text_muted))
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
                    name_item.setForeground(QColor(Colors.text_accent))
                else:
                    name_item.setText(base_name)
                    name_item.setForeground(QColor(Colors.text_secondary))
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
                rec.setForeground(QColor(Colors.warning))
            else:
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                rec = self.items_table.item(row, 3)
                if rec.text().startswith("未接示波器"):
                    rec.setText("记录")
                    rec.setForeground(QColor(Colors.text_muted))

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
            "vout_source_channel": self.vout_src_ch_combo.currentText(),
            "iload_channel": self.iload_ch_combo.currentText(),
            "vout_nominal_mv": self.vout_nominal_spin.value(),
            "device_addr": self.device_addr_edit.text().strip(),
            "width_flag": self.width_flag_combo.currentData(),
            # 示波器输出电压通道：控件为 "CH n"，存整数 n 供 core cfg 直接 int 用
            "scope_vout_channel": self.scope_vout_ch_combo.currentIndex() + 1,
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
        _set_combo(self.vout_src_ch_combo, cfg.get("vout_source_channel"))
        _set_combo(self.iload_ch_combo, cfg.get("iload_channel"))
        if "scope_vout_channel" in cfg:
            _idx = int(cfg["scope_vout_channel"]) - 1
            if 0 <= _idx < self.scope_vout_ch_combo.count():
                self.scope_vout_ch_combo.setCurrentIndex(_idx)
        if "vout_nominal_mv" in cfg:
            self.vout_nominal_spin.setValue(int(cfg["vout_nominal_mv"]))
        if "device_addr" in cfg:
            self.device_addr_edit.setText(str(cfg["device_addr"]))
        if "width_flag" in cfg:
            idx = self.width_flag_combo.findData(int(cfg["width_flag"]))
            if idx >= 0:
                self.width_flag_combo.setCurrentIndex(idx)

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
        dlg = _ConfigManagerDialog(self._configs_root(), self.MODULE_TYPE, parent=self)
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

    def prompt_config_manager_once(self) -> None:
        """首次进入本模块测试页时自动弹出配置管理器（每子页一次）。"""
        if getattr(self, "_config_prompted", False):
            return
        self._config_prompted = True
        QTimer.singleShot(0, self._on_open_config)

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
        # 切换：存在未勾选项 → 全选；已全部勾选 → 取消全选
        rows = [
            self.items_table.item(r, 0)
            for r in range(self.items_table.rowCount())
        ]
        checkable = [
            c for c in rows
            if c and (c.flags() & Qt.ItemIsUserCheckable) and (c.flags() & Qt.ItemIsEnabled)
        ]
        all_checked = bool(checkable) and all(
            c.checkState() == Qt.Checked for c in checkable
        )
        target = Qt.Unchecked if all_checked else Qt.Checked
        for c in checkable:
            c.setCheckState(target)
        self.select_all_btn.setText("取消全选" if not all_checked else "全选测试项")

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

    def _on_mso64b_top_changed(self):
        """顶层示波器连接状态变化时联动刷新 (scope) 项。

        mixin 只更新 scope_connected，不触碰测试项表；不覆盖则连接示波器后
        (scope) 项仍显示"未接示波器，跳过"且保持禁用（需切换页面才恢复）。
        """
        super()._on_mso64b_top_changed()
        if getattr(self, "is_test_running", False):
            return
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


class _ConfigManagerDialog(QDialog):
    """配置管理器：按芯片分类管理（打开 / 新增 / 重命名 / 移动归属 / 删除）配置。

    目录结构：<root>/<芯片名>/<配置名>.json；顶层节点为芯片分类，子节点为配置。
    """

    def __init__(self, root: str, module_type: str, parent=None):
        super().__init__(parent)
        self._root = root
        self._module_type = module_type
        self.setWindowTitle(f"{module_type.upper()} Config Manager")
        self.setMinimumSize(520, 480)
        self.setStyleSheet(DIALOG_QSS)
        self._selected_path: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel("按芯片分类管理配置，双击打开；右侧按钮进行管理："))

        body = QHBoxLayout()
        body.setSpacing(8)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "归属芯片"])
        self.tree.setColumnWidth(0, 220)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.currentItemChanged.connect(self._on_current_changed)
        body.addWidget(self.tree, 1)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(6)
        self.open_btn = QPushButton("打开")
        self.open_btn.setDefault(True)
        self.open_btn.setAutoDefault(True)
        self.new_btn = QPushButton("新增配置…")
        self.rename_btn = QPushButton("重命名…")
        self.move_btn = QPushButton("移动归属…")
        self.delete_btn = QPushButton("删除")
        for _b in (self.open_btn, self.new_btn, self.rename_btn, self.move_btn, self.delete_btn):
            _b.setMinimumWidth(88)
            _b.setCursor(Qt.PointingHandCursor)
        self.open_btn.clicked.connect(self._accept_selection)
        self.new_btn.clicked.connect(self._on_new_config)
        self.rename_btn.clicked.connect(self._on_rename)
        self.move_btn.clicked.connect(self._on_move)
        self.delete_btn.clicked.connect(self._on_delete)
        btn_col.addWidget(self.open_btn)
        btn_col.addWidget(self.new_btn)
        btn_col.addWidget(self.rename_btn)
        btn_col.addWidget(self.move_btn)
        btn_col.addWidget(self.delete_btn)
        btn_col.addStretch()
        body.addLayout(btn_col)
        layout.addLayout(body, 1)

        close_btn = QPushButton("关闭")
        close_btn.setDefault(False)
        close_btn.setAutoDefault(False)
        close_btn.setMinimumWidth(88)
        close_btn.clicked.connect(self.reject)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

        self._populate()
        self._on_current_changed(self.tree.currentItem(), None)

    # ------------------------------------------------------------------ data
    @staticmethod
    def _safe(text: str, fallback: str) -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]+', "_", (text or "").strip()).strip(" .")
        return cleaned or fallback

    def _chip_names(self) -> list[str]:
        if not os.path.isdir(self._root):
            return []
        return sorted(
            d for d in os.listdir(self._root)
            if os.path.isdir(os.path.join(self._root, d))
        )

    def _populate(self, select_path: str | None = None) -> None:
        self.tree.clear()
        chip_dirs = self._chip_names()
        has_any = False
        select_item: QTreeWidgetItem | None = None
        for chip in chip_dirs:
            chip_path = os.path.join(self._root, chip)
            files = sorted(
                f for f in os.listdir(chip_path)
                if f.lower().endswith(".json")
            )
            if not files:
                continue
            chip_node = QTreeWidgetItem([chip, ""])
            chip_node.setFlags(Qt.ItemIsEnabled)
            chip_node.setData(0, Qt.UserRole, None)
            chip_node.setData(1, Qt.UserRole, chip)
            self.tree.addTopLevelItem(chip_node)
            for f in files:
                cfg_path = os.path.join(chip_path, f)
                cfg_node = QTreeWidgetItem([os.path.splitext(f)[0], chip])
                cfg_node.setData(0, Qt.UserRole, cfg_path)
                cfg_node.setData(1, Qt.UserRole, chip)
                chip_node.addChild(cfg_node)
                if select_path and os.path.normpath(cfg_path) == os.path.normpath(select_path):
                    select_item = cfg_node
            chip_node.setExpanded(True)
            has_any = True
        if not has_any:
            placeholder = QTreeWidgetItem(["（暂无已保存的配置）", ""])
            placeholder.setFlags(Qt.ItemIsEnabled)
            placeholder.setData(0, Qt.UserRole, None)
            self.tree.addTopLevelItem(placeholder)
        if select_item is not None:
            self.tree.setCurrentItem(select_item)

    def _current_cfg(self) -> tuple[str | None, str | None]:
        """返回 (配置路径, 归属芯片)，未选中配置返回 (None, None)。"""
        item = self.tree.currentItem()
        if not item:
            return None, None
        path = item.data(0, Qt.UserRole)
        chip = item.data(1, Qt.UserRole)
        if not path:
            return None, None
        return path, chip

    def _on_current_changed(self, current: QTreeWidgetItem, _prev) -> None:
        is_cfg = bool(current and current.data(0, Qt.UserRole))
        self.open_btn.setEnabled(is_cfg)
        self.rename_btn.setEnabled(is_cfg)
        self.move_btn.setEnabled(is_cfg)
        self.delete_btn.setEnabled(is_cfg)

    # ------------------------------------------------------------------ open
    def _on_item_double_clicked(self, item: QTreeWidgetItem, _col: int) -> None:
        if item and item.data(0, Qt.UserRole):
            self._selected_path = item.data(0, Qt.UserRole)
            self.accept()

    def _accept_selection(self) -> None:
        path, _chip = self._current_cfg()
        if path:
            self._selected_path = path
            self.accept()

    def selected_path(self) -> str | None:
        return self._selected_path

    # ------------------------------------------------------------------ manage
    def _on_new_config(self) -> None:
        chips = self._chip_names()
        chip, ok = QInputDialog.getItem(
            self, "新增配置", "归属芯片（可输入新名称新建分类）：",
            chips, 0, True)
        if not ok or not chip.strip():
            return
        chip = self._safe(chip, "未分类芯片")
        name, ok = QInputDialog.getText(
            self, "新增配置", f"配置名称（归入芯片「{chip}」）：",
            text=self._module_type)
        if not ok:
            return
        name = self._safe(name, self._module_type)
        target_dir = os.path.join(self._root, chip)
        path = os.path.join(target_dir, f"{name}.json")
        if os.path.exists(path):
            QMessageBox.warning(self, "新增失败", f"配置「{name}」已存在。")
            return
        default_cfg = self._default_config(chip)
        payload = {
            "schema_version": _CONFIG_SCHEMA_VERSION,
            "module_type": self._module_type,
            "config": default_cfg,
        }
        try:
            os.makedirs(target_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except OSError:
            _logger.error("新增配置文件失败：%s", path, exc_info=True)
            QMessageBox.warning(self, "新增失败", "配置写入失败，详见日志。")
            return
        self._populate(select_path=path)

    def _default_config(self, chip: str) -> dict:
        return {
            "selected_items": [],
            "chip_name": chip,
            "module_name": "",
            "operator": "",
            "temp_test_enabled": False,
            "temperature": "",
            "temp_soak_s": 300,
            "temp_tolerance_c": 2,
            "temp_wait_s": 1800,
            "vin_channel": "CH 1",
            "vout_channel": "CH 2",
            "vout_source_channel": "CH 2",
            "iload_channel": "CH 3",
            "vout_nominal_mv": 1800 if self._module_type == "ldo" else 1200,
            "device_addr": "0x00",
            "width_flag": int(I2CWidthFlag.BIT_10),
            "scope_vout_channel": 1,
            "item_overrides": {},
        }

    def _on_rename(self) -> None:
        path, chip = self._current_cfg()
        if not path:
            return
        old_name = os.path.splitext(os.path.basename(path))[0]
        name, ok = QInputDialog.getText(
            self, "重命名配置", "新的配置名称：", text=old_name)
        if not ok:
            return
        name = self._safe(name, old_name)
        if name == old_name:
            return
        new_path = os.path.join(os.path.dirname(path), f"{name}.json")
        if os.path.exists(new_path):
            QMessageBox.warning(self, "重命名失败", f"配置「{name}」已存在。")
            return
        try:
            os.replace(path, new_path)
        except OSError:
            _logger.error("重命名配置失败：%s -> %s", path, new_path, exc_info=True)
            QMessageBox.warning(self, "重命名失败", "无法重命名，详见日志。")
            return
        self._populate(select_path=new_path)

    def _on_move(self) -> None:
        path, chip = self._current_cfg()
        if not path:
            return
        chips = self._chip_names()
        current_idx = chips.index(chip) if chip in chips else 0
        target, ok = QInputDialog.getItem(
            self, "移动归属", f"将配置移到哪个芯片分类（可输入新名称）：",
            chips, current_idx, True)
        if not ok or not target.strip():
            return
        target = self._safe(target, chip)
        if target == chip:
            return
        fname = os.path.basename(path)
        target_dir = os.path.join(self._root, target)
        new_path = os.path.join(target_dir, fname)
        if os.path.exists(new_path):
            QMessageBox.warning(
                self, "移动失败",
                f"芯片「{target}」下已存在同名配置「{os.path.splitext(fname)[0]}」。")
            return
        try:
            os.makedirs(target_dir, exist_ok=True)
            shutil.move(path, new_path)
        except OSError:
            _logger.error("移动配置失败：%s -> %s", path, new_path, exc_info=True)
            QMessageBox.warning(self, "移动失败", "无法移动配置，详见日志。")
            return
        self._populate(select_path=new_path)

    def _on_delete(self) -> None:
        path, chip = self._current_cfg()
        if not path:
            return
        name = os.path.splitext(os.path.basename(path))[0]
        resp = QMessageBox.question(
            self, "删除确认",
            f"确定删除配置「{name}」（芯片「{chip}」）？此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        try:
            os.remove(path)
        except OSError:
            _logger.error("删除配置失败：%s", path, exc_info=True)
            QMessageBox.warning(self, "删除失败", "无法删除配置，详见日志。")
            return
        self._populate()
