# I2C 主 Mixin：按需初始化 I2C / 寄存器读写 / 位宽切换 /
# 位域合并 / 寄存器映射 / 模板持久化 / 顶部导航 + 工作区布局。

import os
import json
import copy

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox, QMenu, QScrollArea, QStackedWidget,
    QButtonGroup, QPlainTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QColor, QAction

from ui.widgets.dark_combobox import DarkComboBox
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from log_config import get_logger

from ui.modules.IIC_Module import i2c_constants as _i2c_const
from ui.modules.IIC_Module.i2c_constants import (
    I2C_BTN_HEIGHT, SLATE_950, SLATE_900, SLATE_800,
    INDIGO, INDIGO_LIGHT, TEXT_MAIN, TEXT_MUTED,
    _I2C_UI_WIDTHS, _ui_width_to_flag, _infer_reg_bits, _width_label,
    _fmt_hex, _fmt_bin_grouped, _parse_hex_int, _i2c_template_dir,
)
from ui.modules.IIC_Module.i2c_styles import (
    _i2c_input_style, _i2c_read_btn_style, _i2c_write_btn_style,
    _i2c_subtle_btn_style, _i2c_collapse_arrow_style, _i2c_table_qss,
    _nav_tab_style,
)
from ui.modules.IIC_Module.i2c_workers import (
    _I2cReadWorker, _I2cWriteWorker, _I2cChipCheckWorker, _I2cSequenceWorker,
)
from ui.modules.IIC_Module.i2c_dsl import (
    _seq_bold_font, _seq_italic_font, _seq_action_color, _parse_dsl_for_display,
)
from ui.modules.IIC_Module.i2c_persistence import (
    _load_all_sequences, _save_sequence_file, _delete_sequence_file,
    _serialize_script_yaml, _parse_script_yaml,
    _load_all_templates, _save_template_file,
    _load_i2c_state, _save_i2c_state, _tpl_filename_for,
)
from ui.modules.IIC_Module.i2c_widgets import (
    HexLineEdit, RegAddrInput, DataValueInput, BitsTableContainer, _ToggleSwitch,
)

logger = get_logger(__name__)


class I2cMixin:
    """通用 I2C 控制 Mixin：按需初始化 I2C / 寄存器读写 / 位宽切换 /
    位域合并 / 寄存器映射 / 模板持久化 / 顶部导航 + 工作区布局。"""

    def init_i2c(self):
        if not _i2c_const._I2C_WIDTH_META:
            _i2c_const._I2C_WIDTH_META = _i2c_const._load_width_meta()
        self._i2c_speed_options = _i2c_const._load_speed_options()

        self._i2c_read_thread = None
        self._i2c_read_worker = None
        self._i2c_write_thread = None
        self._i2c_write_worker = None
        self._i2c_chipcheck_thread = None
        self._i2c_chipcheck_worker = None
        self._i2c_script_thread = None
        self._i2c_script_worker = None
        self._i2c_custom_dll = None

        # 序列脚本管理器状态
        self._i2c_sequences = []          # [(filepath, script_dict), ...]
        self._i2c_seq_current_index = None  # 当前选中的列表项索引
        self._i2c_seq_suppress_sync = False  # 防止表/YAML 互相同步时递归

        # 模板（Register Map）持久化状态
        self._i2c_templates = []             # [(filepath, template_dict), ...]
        self._i2c_tpl_combo_index = None     # 当前模板 combo 索引
        self._i2c_active_template_name = ""  # 当前活动模板名称
        self._i2c_filter_scripts_by_template = True  # 脚本列表是否按模板过滤

        # 持久化状态（尚未应用到 UI）
        self._i2c_pending_state = _load_i2c_state()

        self._i2c_width = _ui_width_to_flag(16)
        self._i2c_data_bits = 16
        self._i2c_reg_bits = 16
        self._i2c_speed_mode = self._i2c_speed_options[1][0]  # 100K
        self._i2c_data_value = 0

        self._i2c_registers = []
        self._i2c_active_reg_index = None
        self._i2c_fields = []

    def _i2c_dll_path(self):
        return getattr(self, "_i2c_custom_dll", None)

    # ---- UI 构建：整体框架（顶部导航 + 配置卡片 + 工作区） ----

    def build_i2c_widgets(self, layout, title_row=None):
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self._build_i2c_nav_bar(root)

        self.i2c_stack = QStackedWidget()
        self.i2c_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.i2c_ctrl_page = self._build_i2c_control_page()
        self.i2c_set_page = self._build_i2c_settings_page()
        self.i2c_stack.addWidget(self.i2c_ctrl_page)
        self.i2c_stack.addWidget(self.i2c_set_page)
        # 用 ExecutionLogsFrame 包裹 stack：日志固定在窗口底部
        self.i2c_splitter, self.i2c_logs = ExecutionLogsFrame.wrap_with(
            self.i2c_stack, title="Activity Logs", show_progress=False,
            stretch=(4, 1)
        )
        root.addWidget(self.i2c_splitter, 1)

        layout.addLayout(root)
        self._i2c_sync_width_ui()

    def _build_i2c_nav_bar(self, layout):
        bar = QFrame()
        bar.setObjectName("navBar")
        bar.setFixedHeight(48)
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 6, 10, 6)
        row.setSpacing(12)

        badge = QLabel("I2C")
        badge.setObjectName("appBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(26)
        badge.setFixedWidth(40)
        row.addWidget(badge)

        title = QLabel("I2C Console")
        title.setObjectName("appTitle")
        row.addWidget(title)
        row.addStretch()

        self.i2c_nav_group = QButtonGroup(self)
        self.i2c_nav_group.setExclusive(True)
        self.i2c_nav_tabs = []
        for text, idx in (("Control", 0), ("Settings", 1)):
            btn = QPushButton(text)
            btn.setObjectName("navTab")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_nav_tab_style())
            btn.clicked.connect(lambda _=False, i=idx: self._on_i2c_nav_tab(i))
            self.i2c_nav_group.addButton(btn, idx)
            row.addWidget(btn)
            self.i2c_nav_tabs.append(btn)
        self.i2c_nav_tabs[0].setChecked(True)
        layout.addWidget(bar)

    def _on_i2c_nav_tab(self, idx):
        self.i2c_stack.setCurrentIndex(idx)

    # ---- 控制页：顶部配置卡片组 + 主工作区 ----

    def _build_i2c_control_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self._build_i2c_top_cards(root)
        self._build_i2c_workspace(root)
        self._build_i2c_script_card(root)
        root.addStretch(0)
        return page

    def _build_i2c_top_cards(self, layout):
        row = QHBoxLayout()
        row.setSpacing(10)
        row.setContentsMargins(0, 0, 0, 0)
        self._build_i2c_device_config_card(row)
        self._build_i2c_template_card(row)
        layout.addLayout(row)

    def _build_i2c_device_config_card(self, layout):
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        t = QLabel("Device Config")
        t.setObjectName("cardTitle")
        v.addWidget(t)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(8)
        dev_lbl = QLabel("Device Addr")
        dev_lbl.setObjectName("muted")
        dev_lbl.setFixedWidth(80)
        dev_row.addWidget(dev_lbl)
        # I2C 设备地址固定为 7-bit（2 位十六进制）
        self.i2c_dev_edit = HexLineEdit(7)
        self.i2c_dev_edit.setStyleSheet(_i2c_input_style())
        self.i2c_dev_edit.set_value(0x27)
        dev_row.addWidget(self.i2c_dev_edit, 1)
        v.addLayout(dev_row)

        w_row = QHBoxLayout()
        w_row.setSpacing(8)
        w_lbl = QLabel("Data Width")
        w_lbl.setObjectName("muted")
        w_lbl.setFixedWidth(80)
        w_row.addWidget(w_lbl)
        self.i2c_width_combo = DarkComboBox(bg=SLATE_950, border=SLATE_800,
                                            hover_color=INDIGO)
        self.i2c_width_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_width_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for (reg_bits, data_bits), text in _I2C_UI_WIDTHS:
            self.i2c_width_combo.addItem(text, userData=(reg_bits, data_bits))
        self.i2c_width_combo.setCurrentIndex(2)
        w_row.addWidget(self.i2c_width_combo, 1)
        v.addLayout(w_row)

        layout.addWidget(card, 1)

    # ---- Template 卡片（位于 Device Config 右侧） ----

    def _build_i2c_template_card(self, layout):
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        # 标题行：Template + Edit 滑动开关（右对齐）
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setContentsMargins(0, 0, 0, 0)
        t = QLabel("Template")
        t.setObjectName("cardTitle")
        title_row.addWidget(t)
        title_row.addStretch()
        edit_lbl = QLabel("Edit")
        edit_lbl.setObjectName("muted")
        title_row.addWidget(edit_lbl)
        self.i2c_edit_toggle = _ToggleSwitch()
        title_row.addWidget(self.i2c_edit_toggle)
        v.addLayout(title_row)

        # 模板下拉菜单：直接选中已保存的 Template
        self.i2c_tpl_combo = DarkComboBox(
            bg=SLATE_950, border=SLATE_800, hover_color=INDIGO)
        self.i2c_tpl_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_tpl_combo.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        v.addWidget(self.i2c_tpl_combo)

        # 按钮行：Save / Open / Export
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 0, 0, 0)
        self.i2c_tpl_save_btn = QPushButton("Save")
        self.i2c_tpl_open_btn = QPushButton("Open")
        self.i2c_tpl_export_btn = QPushButton("Export")
        for btn in (self.i2c_tpl_save_btn, self.i2c_tpl_open_btn,
                    self.i2c_tpl_export_btn):
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_i2c_subtle_btn_style())
            btn_row.addWidget(btn)
        v.addLayout(btn_row)

        layout.addWidget(card, 1)

    # ---- 主工作区：Header（标题 + 二进制预览） + Body（位表） + Footer（操作栏） ----

    def _build_i2c_workspace(self, layout):
        ws = QFrame()
        ws.setObjectName("workspace")
        ws.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v = QVBoxLayout(ws)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)

        # Header
        header = QHBoxLayout()
        header.setSpacing(10)
        h_title = QLabel("Payload Data Bits")
        h_title.setObjectName("cardTitle")
        header.addWidget(h_title)
        # + Field 按钮（仅 Edit 模式可见）
        self.i2c_add_field_btn = QPushButton("+ Field")
        self.i2c_add_field_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_add_field_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_add_field_btn.setStyleSheet(_i2c_subtle_btn_style())
        self.i2c_add_field_btn.setVisible(False)
        header.addWidget(self.i2c_add_field_btn)
        header.addStretch()
        bin_lbl = QLabel("BIN")
        bin_lbl.setObjectName("muted")
        bin_lbl.setFixedWidth(30)
        header.addWidget(bin_lbl, 0, Qt.AlignVCenter)
        self.i2c_bin_label = QLabel("")
        self.i2c_bin_label.setObjectName("mono")
        self.i2c_bin_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.i2c_bin_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        header.addWidget(self.i2c_bin_label, 1)
        v.addLayout(header)

        # Body：位操作表格
        body_wrap = QWidget()
        body_wrap.setStyleSheet("background:transparent;")
        bv = QVBoxLayout(body_wrap)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(6)
        self.i2c_bits = BitsTableContainer()
        self.i2c_bits.set_bit_count(self._i2c_data_bits)
        bv.addWidget(self.i2c_bits, 1)
        v.addWidget(body_wrap, 1)

        # Footer：Register Addr + Data Value + Read/Write
        footer = QFrame()
        footer.setObjectName("footer")
        f_row = QHBoxLayout(footer)
        f_row.setContentsMargins(12, 8, 12, 8)
        f_row.setSpacing(10)

        reg_lbl = QLabel("Reg Addr")
        reg_lbl.setObjectName("muted")
        f_row.addWidget(reg_lbl)
        self.i2c_reg_edit = RegAddrInput(self._i2c_reg_bits)
        self.i2c_reg_edit.set_value(0x0000)
        self.i2c_reg_edit.setMinimumWidth(110)
        self.i2c_reg_edit.setMaximumWidth(160)
        f_row.addWidget(self.i2c_reg_edit)

        dv_lbl = QLabel("Data Value")
        dv_lbl.setObjectName("muted")
        f_row.addWidget(dv_lbl)
        self.i2c_data_edit = DataValueInput(self._i2c_data_bits)
        f_row.addWidget(self.i2c_data_edit, 1)

        self.i2c_read_btn = QPushButton("Read")
        self.i2c_read_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_read_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_read_btn.setStyleSheet(_i2c_read_btn_style())
        self.i2c_write_btn = QPushButton("Write")
        self.i2c_write_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_write_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_write_btn.setStyleSheet(_i2c_write_btn_style())
        f_row.addWidget(self.i2c_read_btn)
        f_row.addWidget(self.i2c_write_btn)
        v.addWidget(footer)

        layout.addWidget(ws, 1)

    def _build_i2c_script_card(self, layout):
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        title_row.setContentsMargins(0, 0, 0, 0)
        self._i2c_seq_collapse_btn = QPushButton("▼")
        self._i2c_seq_collapse_btn.setObjectName("i2cCollapseArrow")
        self._i2c_seq_collapse_btn.setCursor(Qt.PointingHandCursor)
        self._i2c_seq_collapse_btn.setFixedWidth(16)
        self._i2c_seq_collapse_btn.setStyleSheet(_i2c_collapse_arrow_style())
        self._i2c_seq_collapse_btn.clicked.connect(self._i2c_toggle_seq_card)
        title_row.addWidget(self._i2c_seq_collapse_btn)
        t = QLabel("Sequence Script Manager")
        t.setObjectName("cardTitle")
        title_row.addWidget(t)
        title_row.addStretch()
        v.addLayout(title_row)

        self._i2c_seq_content = QWidget()
        self._i2c_seq_content.setStyleSheet("background:transparent;")
        content_v = QVBoxLayout(self._i2c_seq_content)
        content_v.setContentsMargins(0, 0, 0, 0)
        content_v.setSpacing(8)

        hint = QLabel(
            "寄存器操作序列脚本管理 · 双击列表项执行 · Table 只读展示 / YAML 编辑 · "
            "Action: W/R/WR · 指令: WRITE/READ/WRITE_BITS/DELAY/READ_RANGE/LOOP/IF")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        content_v.addWidget(hint)

        # 主区域：左列表 + 右编辑器
        main_row = QHBoxLayout()
        main_row.setSpacing(8)

        # ---- 左侧：脚本列表 ----
        left = QVBoxLayout()
        left.setSpacing(6)
        list_title_row = QHBoxLayout()
        list_title_row.setSpacing(6)
        list_title = QLabel("Scripts")
        list_title.setObjectName("sectionTitle")
        list_title_row.addWidget(list_title)
        list_title_row.addStretch()
        self.i2c_seq_filter_btn = QPushButton("Linked Only")
        self.i2c_seq_filter_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_filter_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_filter_btn.setCheckable(True)
        self.i2c_seq_filter_btn.setChecked(True)
        self.i2c_seq_filter_btn.setStyleSheet(_i2c_subtle_btn_style())
        list_title_row.addWidget(self.i2c_seq_filter_btn)
        left.addLayout(list_title_row)
        list_btn_row = QHBoxLayout()
        list_btn_row.setSpacing(4)
        self.i2c_seq_new_btn = QPushButton("New")
        self.i2c_seq_dup_btn = QPushButton("Dup")
        self.i2c_seq_del_btn = QPushButton("Del")
        for btn in (self.i2c_seq_new_btn, self.i2c_seq_dup_btn,
                    self.i2c_seq_del_btn):
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_i2c_subtle_btn_style())
            list_btn_row.addWidget(btn)
        left.addLayout(list_btn_row)
        self.i2c_seq_list = QTableWidget(0, 3)
        self.i2c_seq_list.setHorizontalHeaderLabels(["Name", "Tpl", "Cmds"])
        self.i2c_seq_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_seq_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.i2c_seq_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.i2c_seq_list.verticalHeader().setVisible(False)
        self.i2c_seq_list.setStyleSheet(_i2c_table_qss())
        lh = self.i2c_seq_list.horizontalHeader()
        lh.setSectionResizeMode(0, QHeaderView.Stretch)
        lh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        lh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.i2c_seq_list.setMinimumWidth(200)
        left.addWidget(self.i2c_seq_list, 1)
        main_row.addLayout(left, 0)

        # ---- 右侧：编辑器（Tab: GUI 表格 / YAML） ----
        right = QVBoxLayout()
        right.setSpacing(6)

        # 名称 / 模板 / 描述行
        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        name_lbl = QLabel("Name")
        name_lbl.setObjectName("muted")
        name_lbl.setFixedWidth(50)
        meta_row.addWidget(name_lbl)
        self.i2c_seq_name_edit = QLineEdit()
        self.i2c_seq_name_edit.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_name_edit.setStyleSheet(_i2c_input_style())
        self.i2c_seq_name_edit.setPlaceholderText("脚本名称")
        meta_row.addWidget(self.i2c_seq_name_edit, 1)
        tpl_lbl = QLabel("Tpl")
        tpl_lbl.setObjectName("muted")
        tpl_lbl.setFixedWidth(28)
        meta_row.addWidget(tpl_lbl)
        self.i2c_seq_tpl_combo = DarkComboBox(
            bg=SLATE_950, border=SLATE_800, hover_color=INDIGO)
        self.i2c_seq_tpl_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_tpl_combo.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Fixed)
        meta_row.addWidget(self.i2c_seq_tpl_combo, 1)
        desc_lbl = QLabel("Desc")
        desc_lbl.setObjectName("muted")
        desc_lbl.setFixedWidth(40)
        meta_row.addWidget(desc_lbl)
        self.i2c_seq_desc_edit = QLineEdit()
        self.i2c_seq_desc_edit.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_desc_edit.setStyleSheet(_i2c_input_style())
        self.i2c_seq_desc_edit.setPlaceholderText("描述（可选）")
        meta_row.addWidget(self.i2c_seq_desc_edit, 1)
        right.addLayout(meta_row)

        # Tab 切换
        self.i2c_seq_tabs = QStackedWidget()
        # -- 表格编辑器 --
        table_page = QWidget()
        table_page.setStyleSheet("background:transparent;")
        tv = QVBoxLayout(table_page)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.setSpacing(4)
        self.i2c_seq_cmd_table = QTableWidget(0, 7)
        self.i2c_seq_cmd_table.setHorizontalHeaderLabels(
            ["#", "Action", "Addr", "MSB", "LSB", "Value", "Desc"])
        self.i2c_seq_cmd_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.i2c_seq_cmd_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.i2c_seq_cmd_table.verticalHeader().setVisible(False)
        self.i2c_seq_cmd_table.setStyleSheet(_i2c_table_qss())
        ch = self.i2c_seq_cmd_table.horizontalHeader()
        ch.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(6, QHeaderView.Stretch)
        tv.addWidget(self.i2c_seq_cmd_table, 1)
        cmd_btn_row = QHBoxLayout()
        cmd_btn_row.setSpacing(4)
        self.i2c_seq_add_cmd_btn = QPushButton("+ Cmd")
        self.i2c_seq_del_cmd_btn = QPushButton("- Cmd")
        for btn in (self.i2c_seq_add_cmd_btn, self.i2c_seq_del_cmd_btn):
            btn.setFixedHeight(I2C_BTN_HEIGHT)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(_i2c_subtle_btn_style())
            cmd_btn_row.addWidget(btn)
        cmd_btn_row.addStretch()
        tv.addLayout(cmd_btn_row)
        self.i2c_seq_tabs.addWidget(table_page)
        # -- YAML 编辑器 --
        yaml_page = QWidget()
        yaml_page.setStyleSheet("background:transparent;")
        yv = QVBoxLayout(yaml_page)
        yv.setContentsMargins(0, 0, 0, 0)
        self.i2c_seq_yaml_edit = QPlainTextEdit()
        self.i2c_seq_yaml_edit.setObjectName("i2cSeqYamlEdit")
        self.i2c_seq_yaml_edit.setStyleSheet(
            "QPlainTextEdit#i2cSeqYamlEdit {"
            f" background-color:{SLATE_950}; border:1px solid {SLATE_800};"
            " border-radius:6px; color:#e2e8f0;"
            " font-family:Consolas,'Cascadia Mono',monospace;"
            " font-size:12px; padding:6px;"
            " selection-background-color:#4f46e5;"
            "}"
            f" QPlainTextEdit#i2cSeqYamlEdit:focus"
            f" {{ border:1px solid {INDIGO}; }}"
        )
        yv.addWidget(self.i2c_seq_yaml_edit)
        self.i2c_seq_tabs.addWidget(yaml_page)
        right.addWidget(self.i2c_seq_tabs, 1)

        # 模式切换按钮 + 执行按钮
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        self.i2c_seq_mode_btn = QPushButton("YAML")
        self.i2c_seq_mode_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_mode_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_mode_btn.setStyleSheet(_i2c_subtle_btn_style())
        bottom_row.addWidget(self.i2c_seq_mode_btn)
        bottom_row.addStretch()
        self.i2c_seq_save_btn = QPushButton("Save")
        self.i2c_seq_save_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_save_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_save_btn.setStyleSheet(_i2c_subtle_btn_style())
        bottom_row.addWidget(self.i2c_seq_save_btn)
        self.i2c_seq_stop_btn = QPushButton("Stop")
        self.i2c_seq_stop_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_stop_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_stop_btn.setStyleSheet(_i2c_subtle_btn_style())
        self.i2c_seq_stop_btn.setEnabled(False)
        bottom_row.addWidget(self.i2c_seq_stop_btn)
        self.i2c_seq_run_btn = QPushButton("Run")
        self.i2c_seq_run_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_seq_run_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_seq_run_btn.setStyleSheet(_i2c_write_btn_style())
        bottom_row.addWidget(self.i2c_seq_run_btn)
        right.addLayout(bottom_row)

        main_row.addLayout(right, 1)
        content_v.addLayout(main_row)

        v.addWidget(self._i2c_seq_content)

        # 加载已存脚本
        self._i2c_seq_reload_list()
        layout.addWidget(card)

    # ---- 设置页：DLL + 速率 + 芯片检测 ----

    def _build_i2c_settings_page(self):
        page = QWidget()
        page.setStyleSheet("background:transparent;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(14, 12, 14, 12)
        cv.setSpacing(8)

        dt = QLabel("DLL Path")
        dt.setObjectName("cardTitle")
        cv.addWidget(dt)
        dll_row = QHBoxLayout()
        dll_row.setSpacing(6)
        self.i2c_dll_edit = QLineEdit()
        self.i2c_dll_edit.setReadOnly(True)
        self.i2c_dll_edit.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_edit.setStyleSheet(_i2c_input_style())
        self.i2c_dll_edit.setPlaceholderText("Auto resolve DLL path")
        self._i2c_refresh_dll_display()
        dll_row.addWidget(self.i2c_dll_edit, 1)
        self.i2c_dll_browse_btn = QPushButton("Browse")
        self.i2c_dll_browse_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_browse_btn.setStyleSheet(_i2c_subtle_btn_style())
        dll_row.addWidget(self.i2c_dll_browse_btn)
        self.i2c_dll_reset_btn = QPushButton("Reset")
        self.i2c_dll_reset_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_dll_reset_btn.setStyleSheet(_i2c_subtle_btn_style())
        dll_row.addWidget(self.i2c_dll_reset_btn)
        cv.addLayout(dll_row)

        st = QLabel("Default Speed")
        st.setObjectName("cardTitle")
        cv.addWidget(st)
        self.i2c_speed_combo = DarkComboBox(bg=SLATE_950, border=SLATE_800,
                                            hover_color=INDIGO)
        self.i2c_speed_combo.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_speed_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for mode, text in self._i2c_speed_options:
            self.i2c_speed_combo.addItem(text, userData=mode)
        self.i2c_speed_combo.setCurrentIndex(1)
        cv.addWidget(self.i2c_speed_combo)

        ct = QLabel("Chip Check")
        ct.setObjectName("cardTitle")
        cv.addWidget(ct)
        self.i2c_chipcheck_btn = QPushButton("BES Chip Check")
        self.i2c_chipcheck_btn.setFixedHeight(I2C_BTN_HEIGHT)
        self.i2c_chipcheck_btn.setCursor(Qt.PointingHandCursor)
        self.i2c_chipcheck_btn.setStyleSheet(_i2c_read_btn_style())
        cv.addWidget(self.i2c_chipcheck_btn)

        root.addWidget(card)
        root.addStretch()
        scroll.setWidget(inner)
        wrap = QVBoxLayout(page)
        wrap.setContentsMargins(0, 0, 0, 0)
        wrap.addWidget(scroll)
        return page

    # ---- 信号绑定 ----

    def bind_i2c_signals(self):
        self.i2c_dll_browse_btn.clicked.connect(self._on_i2c_browse_dll)
        self.i2c_dll_reset_btn.clicked.connect(self._on_i2c_reset_dll)
        self.i2c_chipcheck_btn.clicked.connect(self._on_i2c_chip_check)
        self.i2c_read_btn.clicked.connect(self._on_i2c_read)
        self.i2c_write_btn.clicked.connect(self._on_i2c_write)
        self.i2c_data_edit.value_changed.connect(self._on_i2c_data_edited)
        self.i2c_bits.bit_toggled.connect(self._on_i2c_bit_toggled)
        self.i2c_bits.field_edited.connect(self._on_i2c_field_edited)
        self.i2c_bits.field_context_menu.connect(self._on_i2c_bits_context_menu)
        self.i2c_width_combo.currentIndexChanged.connect(
            self._on_i2c_width_changed)
        self.i2c_speed_combo.currentIndexChanged.connect(
            self._on_i2c_default_speed_changed)
        self.i2c_add_field_btn.clicked.connect(self._on_i2c_add_field)
        # 模板管理信号
        self.i2c_tpl_combo.currentIndexChanged.connect(
            self._on_i2c_tpl_combo_changed)
        self.i2c_tpl_save_btn.clicked.connect(self._on_i2c_tpl_save)
        self.i2c_tpl_open_btn.clicked.connect(self._on_i2c_tpl_import)
        self.i2c_tpl_export_btn.clicked.connect(self._on_i2c_tpl_export)
        self.i2c_edit_toggle.toggled.connect(self._on_i2c_edit_toggled)
        self.i2c_seq_new_btn.clicked.connect(self._on_i2c_seq_new)
        self.i2c_seq_dup_btn.clicked.connect(self._on_i2c_seq_duplicate)
        self.i2c_seq_del_btn.clicked.connect(self._on_i2c_seq_delete)
        self.i2c_seq_list.itemSelectionChanged.connect(
            self._on_i2c_seq_list_selected)
        self.i2c_seq_list.doubleClicked.connect(
            self._on_i2c_seq_list_double_clicked)
        self.i2c_seq_add_cmd_btn.clicked.connect(self._on_i2c_seq_add_cmd)
        self.i2c_seq_del_cmd_btn.clicked.connect(self._on_i2c_seq_del_cmd)
        self.i2c_seq_mode_btn.clicked.connect(self._on_i2c_seq_toggle_mode)
        self.i2c_seq_save_btn.clicked.connect(self._on_i2c_seq_save)
        self.i2c_seq_run_btn.clicked.connect(self._on_i2c_seq_run)
        self.i2c_seq_stop_btn.clicked.connect(self._on_i2c_seq_stop)
        # 脚本编辑器中的模板 combo + 过滤按钮
        self.i2c_seq_tpl_combo.currentIndexChanged.connect(
            self._on_i2c_seq_tpl_combo_changed)
        self.i2c_seq_filter_btn.toggled.connect(
            self._on_i2c_seq_filter_toggled)
        # 应用持久化状态（必须在所有信号绑定完成后调用）
        self._i2c_restore_state()

    # ---- 状态反馈 ----

    def _i2c_set_result(self, text, ok=True):
        level = "DONE" if ok else "ERROR"
        self.append_log(f"[{level}] {text}")

    def append_log(self, msg):
        """供页面覆写：默认转发到 logger 与底部 ExecutionLogsFrame。"""
        logger.info(msg)
        logs = getattr(self, "i2c_logs", None)
        if logs is not None:
            logs.append_log(msg)

    def _i2c_set_busy(self, busy):
        for attr in ("i2c_read_btn", "i2c_write_btn", "i2c_chipcheck_btn",
                     "i2c_seq_run_btn"):
            w = getattr(self, attr, None)
            if w is not None:
                w.setEnabled(not busy)
        # Stop 按钮只在序列执行中可用
        stop_btn = getattr(self, "i2c_seq_stop_btn", None)
        if stop_btn is not None:
            stop_btn.setEnabled(busy and self._i2c_script_thread is not None)

    def _i2c_set_activity(self, op, value=None, ok=True):
        if value is not None:
            bits = self._i2c_data_bits
            level = "DONE" if ok else "ERROR"
            self.append_log(
                f"[{level}] {op}: {_fmt_hex(value, bits)} ({value})")
        elif op.endswith("…"):
            self.append_log(f"[INFO] {op}")
        else:
            level = "DONE" if ok else "ERROR"
            self.append_log(f"[{level}] {op}")

    def _i2c_toggle_seq_card(self):
        visible = self._i2c_seq_content.isVisible()
        self._i2c_seq_content.setVisible(not visible)
        self._i2c_seq_collapse_btn.setText("▶" if visible else "▼")

    # ---- DLL 路径 ----

    def _i2c_refresh_dll_display(self):
        display = getattr(self, "_i2c_custom_dll", None)
        if not display:
            try:
                from lib.i2c.i2c_interface_x64 import _resolve_default_dll_path
                display = _resolve_default_dll_path() or "(auto, not found)"
            except Exception:
                display = "(auto)"
        self.i2c_dll_edit.setText(display)

    def _on_i2c_browse_dll(self):
        start = getattr(self, "_i2c_custom_dll", None) or ""
        start_dir = os.path.dirname(start) if start else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 I2C DLL", start_dir, "DLL (*.dll);;All (*.*)")
        if path:
            self._i2c_custom_dll = path
            self.i2c_dll_edit.setText(path)
            self.append_log(f"[I2C] DLL 路径已设为: {path}")
            self._i2c_save_state()

    def _on_i2c_reset_dll(self):
        self._i2c_custom_dll = None
        self._i2c_refresh_dll_display()
        self.append_log("[I2C] DLL 路径已重置为自动查找")
        self._i2c_save_state()

    # ---- 速率 / 位宽 ----

    def _on_i2c_default_speed_changed(self, _idx):
        mode = self.i2c_speed_combo.currentData()
        if mode is None:
            return
        self._i2c_speed_mode = mode
        self.append_log(f"[I2C] 默认速率切换为 {self.i2c_speed_combo.currentText()}")
        self._i2c_save_state()

    def _on_i2c_width_changed(self, _idx):
        data = self.i2c_width_combo.currentData()
        if data is None:
            return
        reg_bits, data_bits = data
        self._i2c_reg_bits = int(reg_bits)
        self._i2c_data_bits = int(data_bits)
        self._i2c_width = _ui_width_to_flag(int(reg_bits))
        self._i2c_sync_width_ui()
        self.append_log(f"[I2C] 位宽切换为 {reg_bits}R / {data_bits}D")
        self._i2c_save_state()

    def _i2c_sync_width_ui(self):
        reg_bits = self._i2c_reg_bits
        # Device Addr 固定 7-bit，不随位宽切换
        self.i2c_reg_edit.set_bit_count(reg_bits)
        self.i2c_data_edit.set_bit_count(self._i2c_data_bits)
        self.i2c_bits.set_bit_count(self._i2c_data_bits)
        self._i2c_data_value &= (1 << self._i2c_data_bits) - 1
        self.i2c_data_edit.set_value(self._i2c_data_value)
        self.i2c_bits.set_value(self._i2c_data_value)
        self.i2c_bits.set_fields(self._i2c_fields)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    # ---- 双向数据绑定 ----

    def _on_i2c_data_edited(self, value):
        self._i2c_data_value = int(value) & ((1 << self._i2c_data_bits) - 1)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    def _on_i2c_bit_toggled(self, bit_idx):
        mask = (1 << self._i2c_data_bits) - 1
        self._i2c_data_value = (self._i2c_data_value ^ (1 << bit_idx)) & mask
        self.i2c_data_edit.set_value(self._i2c_data_value)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()

    def _i2c_refresh_bin_label(self):
        v = self._i2c_data_value
        self.i2c_bin_label.setText(
            f"{_fmt_bin_grouped(v, self._i2c_data_bits)}    ({v})")

    # ---- 读写操作（按需初始化 I2C） ----

    def _i2c_current_dev(self):
        return self.i2c_dev_edit.value()

    def _i2c_current_reg(self):
        return self.i2c_reg_edit.value()

    def _start_i2c_read(self, dev, reg, use_raw, tag=""):
        if (self._i2c_read_thread is not None
                and self._i2c_read_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        self._i2c_set_activity("Reading…", ok=True)
        self.append_log(
            f"[I2C] Read{tag} dev=0x{dev:02X} reg=0x{reg:X} "
            f"width={_width_label(self._i2c_width)} raw={use_raw}")
        worker = _I2cReadWorker(
            self._i2c_dll_path(), self._i2c_speed_mode, dev, reg,
            self._i2c_width, use_raw)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_i2c_read_done)
        worker.error.connect(self._on_i2c_read_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_read_thread_cleanup)
        self._i2c_read_worker = worker
        self._i2c_read_thread = thread
        thread.start()

    def _on_i2c_read(self):
        if (self._i2c_read_thread is not None
                and self._i2c_read_thread.isRunning()):
            return
        self._start_i2c_read(self._i2c_current_dev(),
                             self._i2c_current_reg(), False)

    def _on_i2c_read_thread_cleanup(self):
        self._i2c_read_thread = None
        self._i2c_read_worker = None

    def _on_i2c_read_done(self, value):
        bits = self._i2c_data_bits
        value = int(value) & ((1 << bits) - 1)
        self._i2c_data_value = value
        self.i2c_data_edit.set_value(value)
        self.i2c_bits.set_value(value)
        self._i2c_refresh_bin_label()
        self._i2c_refresh_field_values()
        self._i2c_set_activity("Read", value=value, ok=True)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Read => {_fmt_hex(value, bits)} ({value})")

    def _on_i2c_read_error(self, err):
        self._i2c_set_activity("Read", ok=False)
        self._i2c_set_result(f"Read Failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Read 失败: {err}")

    def _start_i2c_write(self, dev, reg, data, high, low, use_raw, tag=""):
        if (self._i2c_write_thread is not None
                and self._i2c_write_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        bit_desc = "full" if high < 0 else f"[{high}:{low}]"
        self._i2c_set_activity("Writing…", ok=True)
        self.append_log(
            f"[I2C] Write{tag} dev=0x{dev:02X} reg=0x{reg:X} "
            f"data={_fmt_hex(data, self._i2c_data_bits)} "
            f"width={_width_label(self._i2c_width)} bits={bit_desc} raw={use_raw}")
        worker = _I2cWriteWorker(
            self._i2c_dll_path(), self._i2c_speed_mode, dev, reg, data,
            self._i2c_width, high, low, use_raw)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_i2c_write_done)
        worker.error.connect(self._on_i2c_write_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_write_thread_cleanup)
        self._i2c_write_worker = worker
        self._i2c_write_thread = thread
        thread.start()

    def _on_i2c_write_thread_cleanup(self):
        self._i2c_write_thread = None
        self._i2c_write_worker = None

    def _on_i2c_write(self):
        if (self._i2c_write_thread is not None
                and self._i2c_write_thread.isRunning()):
            return
        dev = self._i2c_current_dev()
        reg = self._i2c_current_reg()
        data = self._i2c_data_value
        self._start_i2c_write(dev, reg, data, -1, -1, False)

    def _on_i2c_write_done(self):
        self._i2c_set_activity("Write", value=self._i2c_data_value, ok=True)
        self._i2c_set_busy(False)
        self.append_log("[I2C] Write 完成")

    def _on_i2c_write_error(self, err):
        self._i2c_set_activity("Write", ok=False)
        self._i2c_set_result(f"Write Failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] Write 失败: {err}")

    # ---- 位字段管理（直接在 Payload Data Bits 位表上编辑） ----

    def _on_i2c_add_field(self):
        """在位表上新增一个默认字段（覆盖 [7:0] 或剩余可用范围）。"""
        bits = self._i2c_data_bits
        self._i2c_fields.append({
            "name": f"FIELD{len(self._i2c_fields)}",
            "high_bit": min(7, bits - 1),
            "low_bit": 0,
            "description": "",
        })
        self.i2c_bits.set_fields(self._i2c_fields)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_sync_active_register_fields()

    def _on_i2c_field_edited(self, field_idx, col, text):
        """位表 Field(col 2) / Desc(col 3) 内联编辑 → 更新字段数据。"""
        if field_idx is None or field_idx >= len(self._i2c_fields):
            return
        if col == 2:
            self._i2c_fields[field_idx]["name"] = text
        elif col == 3:
            self._i2c_fields[field_idx]["description"] = text
        self._i2c_sync_active_register_fields()

    def _on_i2c_bits_context_menu(self, bits_table, row):
        """位表右键菜单：Edit 模式下可创建/编辑/删除字段。"""
        if not self.i2c_edit_toggle.isChecked():
            return
        abs_bit = bits_table.abs_bit_at_row(row)
        if abs_bit is None:
            return
        fidx, field = bits_table.field_at_row(row)
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background-color:{SLATE_950}; color:{TEXT_MAIN};"
            f" border:1px solid {SLATE_800}; }}"
            "QMenu::item:selected { background-color: rgba(99,102,241,0.35); }")
        if field is not None:
            act_edit_range = QAction(
                f"Edit Range [{field['high_bit']}:{field['low_bit']}]", self)
            act_edit_range.triggered.connect(
                lambda _=False, i=fidx: self._i2c_edit_field_range(i))
            menu.addAction(act_edit_range)
            act_del = QAction("Delete Field", self)
            act_del.triggered.connect(
                lambda _=False, i=fidx: self._i2c_delete_field(i))
            menu.addAction(act_del)
        else:
            act_create = QAction(f"Create Field [bit {abs_bit}]", self)
            act_create.triggered.connect(
                lambda _=False, b=abs_bit: self._i2c_create_field_at(b))
            menu.addAction(act_create)
        menu.exec(bits_table.viewport().mapToGlobal(
            bits_table.visualItemRect(bits_table.item(row, 0)).center()))

    def _i2c_create_field_at(self, bit):
        """在指定位上创建单 bit 字段。"""
        self._i2c_fields.append({
            "name": f"FIELD{len(self._i2c_fields)}",
            "high_bit": bit,
            "low_bit": bit,
            "description": "",
        })
        self.i2c_bits.set_fields(self._i2c_fields)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_sync_active_register_fields()
        self.append_log(f"[I2C] 新建字段 @ bit {bit}")

    def _i2c_edit_field_range(self, fidx):
        """通过对话框编辑字段的高/低位。"""
        if fidx < 0 or fidx >= len(self._i2c_fields):
            return
        from PySide6.QtWidgets import QInputDialog
        f = self._i2c_fields[fidx]
        hi, ok = QInputDialog.getInt(
            self, "编辑字段高位", f"High Bit (0-{self._i2c_data_bits - 1}):",
            int(f["high_bit"]), 0, self._i2c_data_bits - 1)
        if not ok:
            return
        lo, ok = QInputDialog.getInt(
            self, "编辑字段低位", f"Low Bit (0-{self._i2c_data_bits - 1}):",
            int(f["low_bit"]), 0, self._i2c_data_bits - 1)
        if not ok:
            return
        f["high_bit"] = hi
        f["low_bit"] = lo
        self.i2c_bits.set_fields(self._i2c_fields)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_sync_active_register_fields()
        self.append_log(f"[I2C] 字段 {f['name']} 范围改为 [{hi}:{lo}]")

    def _i2c_delete_field(self, fidx):
        """删除指定字段。"""
        if fidx < 0 or fidx >= len(self._i2c_fields):
            return
        name = self._i2c_fields[fidx]["name"]
        self._i2c_fields.pop(fidx)
        self.i2c_bits.set_fields(self._i2c_fields)
        self.i2c_bits.set_value(self._i2c_data_value)
        self._i2c_sync_active_register_fields()
        self.append_log(f"[I2C] 删除字段 {name}")

    def _i2c_refresh_field_values(self):
        """数据值变化后刷新位表上的字段 Hex 显示。"""
        if not hasattr(self, "i2c_bits"):
            return
        self.i2c_bits.set_value(self._i2c_data_value)

    def _i2c_sync_active_register_fields(self):
        """将当前字段同步到活动寄存器（若有）。"""
        if (self._i2c_active_reg_index is not None
                and 0 <= self._i2c_active_reg_index < len(self._i2c_registers)):
            self._i2c_registers[self._i2c_active_reg_index]["bit_fields"] = \
                copy.deepcopy(self._i2c_fields)

    def _i2c_set_width(self, reg_bits, data_bits):
        target = (int(reg_bits), int(data_bits))
        for i in range(self.i2c_width_combo.count()):
            if self.i2c_width_combo.itemData(i) == target:
                self.i2c_width_combo.blockSignals(True)
                self.i2c_width_combo.setCurrentIndex(i)
                self.i2c_width_combo.blockSignals(False)
                break
        self._i2c_reg_bits = int(reg_bits)
        self._i2c_data_bits = int(data_bits)
        self._i2c_width = _ui_width_to_flag(int(reg_bits))
        self._i2c_sync_width_ui()

    # ---- 芯片检测 ----

    def _on_i2c_chip_check(self):
        if (self._i2c_chipcheck_thread is not None
                and self._i2c_chipcheck_thread.isRunning()):
            return
        self._i2c_set_busy(True)
        self._i2c_set_activity("Chip check…", ok=True)
        self.append_log("[I2C] BES 芯片检测中...")
        worker = _I2cChipCheckWorker(self._i2c_dll_path(), self._i2c_speed_mode)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_i2c_chipcheck_done)
        worker.error.connect(self._on_i2c_chipcheck_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_chipcheck_thread_cleanup)
        self._i2c_chipcheck_worker = worker
        self._i2c_chipcheck_thread = thread
        thread.start()

    def _on_i2c_chipcheck_thread_cleanup(self):
        self._i2c_chipcheck_thread = None
        self._i2c_chipcheck_worker = None

    def _on_i2c_chipcheck_done(self, result):
        self._i2c_set_activity("Chip check", ok=True)
        self._i2c_set_result("Chip check OK", ok=True)
        self._i2c_set_busy(False)
        lines = ["[I2C] 芯片检测结果:"]
        for k, v in result.items():
            lines.append(f"  {k}: {v}")
        self.append_log("\n".join(lines))
        QMessageBox.information(
            self, "BES 芯片检测",
            "\n".join(f"{k}: {v}" for k, v in result.items()))

    def _on_i2c_chipcheck_error(self, err):
        self._i2c_set_activity("Chip check", ok=False)
        self._i2c_set_result(f"Chip check failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] 芯片检测失败: {err}")

    # ---- 序列脚本管理器（列表 + GUI 表格 / YAML 双模式编辑 + 执行） ----

    def _i2c_seq_reload_list(self, template_name=None):
        """重新扫描序列目录并刷新左侧列表。

        template_name: 若提供且 _i2c_filter_scripts_by_template 为真，仅显示
                       匹配该模板名的脚本；为 None 或空时显示全部。
        """
        all_seqs = _load_all_sequences()
        active_tpl = template_name if template_name is not None \
            else self._i2c_active_template_name
        if (active_tpl and getattr(self, "_i2c_filter_scripts_by_template", True)
                and self.i2c_seq_filter_btn.isChecked()):
            self._i2c_sequences = [
                (p, s) for p, s in all_seqs
                if str(s.get("template", "")) == active_tpl
            ]
        else:
            self._i2c_sequences = all_seqs
        self.i2c_seq_list.setRowCount(0)
        for _path, script in self._i2c_sequences:
            row = self.i2c_seq_list.rowCount()
            self.i2c_seq_list.insertRow(row)
            name_item = QTableWidgetItem(str(script.get("name", "")))
            tpl_item = QTableWidgetItem(str(script.get("template", "")))
            tpl_item.setTextAlignment(Qt.AlignCenter)
            tpl_item.setForeground(QColor(TEXT_MUTED))
            cmds = script.get("commands", []) or []
            cnt_item = QTableWidgetItem(str(len(cmds)))
            cnt_item.setTextAlignment(Qt.AlignCenter)
            self.i2c_seq_list.setItem(row, 0, name_item)
            self.i2c_seq_list.setItem(row, 1, tpl_item)
            self.i2c_seq_list.setItem(row, 2, cnt_item)
        self._i2c_seq_current_index = None
        self._i2c_seq_clear_editor()

    def _i2c_seq_clear_editor(self):
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_name_edit.setText("")
        self.i2c_seq_desc_edit.setText("")
        self.i2c_seq_cmd_table.setRowCount(0)
        self.i2c_seq_yaml_edit.setPlainText("")
        # 重置脚本模板 combo 到当前活动模板
        if hasattr(self, "i2c_seq_tpl_combo"):
            self._i2c_seq_set_tpl_combo(self._i2c_active_template_name)
        self._i2c_seq_suppress_sync = False

    def _on_i2c_seq_list_selected(self):
        """列表选中 → 加载到右侧编辑器 + 保存状态。"""
        rows = self.i2c_seq_list.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._i2c_sequences):
            return
        self._i2c_seq_current_index = row
        _path, script = self._i2c_sequences[row]
        self._i2c_seq_load_to_editor(script)
        self._i2c_save_state()

    def _on_i2c_seq_list_double_clicked(self, _index):
        """双击列表项 → 直接执行该脚本。"""
        rows = self.i2c_seq_list.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if row < 0 or row >= len(self._i2c_sequences):
            return
        _path, script = self._i2c_sequences[row]
        self._i2c_seq_execute(script)

    def _i2c_seq_load_to_editor(self, script):
        """将脚本 dict 载入右侧编辑器（表格 + YAML 同步）。"""
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_name_edit.setText(str(script.get("name", "")))
        self.i2c_seq_desc_edit.setText(str(script.get("description", "")))
        self._i2c_seq_set_tpl_combo(str(script.get("template", "")))
        cmds = [str(c) for c in (script.get("commands", []) or [])]
        self._i2c_seq_refresh_table(cmds)
        self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
        self._i2c_seq_suppress_sync = False

    def _i2c_seq_refresh_table(self, command_lines):
        """根据 DSL 指令字符串列表刷新表格显示。"""
        self._i2c_seq_suppress_sync = True
        table = self.i2c_seq_cmd_table
        table.setRowCount(0)
        table.clearSpans()
        bold = _seq_bold_font()
        italic = _seq_italic_font()
        muted = QColor(TEXT_MUTED)
        for i, raw in enumerate(command_lines):
            parsed = _parse_dsl_for_display(raw)
            row = table.rowCount()
            table.insertRow(row)

            idx_item = QTableWidgetItem(str(row + 1))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 0, idx_item)

            if parsed["is_comment"]:
                item = QTableWidgetItem(parsed["full_text"])
                item.setForeground(muted)
                item.setFont(italic)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(row, 1, item)
                table.setSpan(row, 1, 1, 6)
                continue

            if parsed["is_control"]:
                action = parsed["action"]
                item = QTableWidgetItem(parsed["full_text"])
                item.setForeground(_seq_action_color(action))
                item.setFont(bold)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(row, 1, item)
                table.setSpan(row, 1, 1, 4)
                val_item = QTableWidgetItem("")
                val_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(row, 5, val_item)
                desc_item = QTableWidgetItem(parsed.get("desc", ""))
                desc_item.setForeground(muted)
                desc_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(row, 6, desc_item)
                continue

            action = parsed["action"]
            action_item = QTableWidgetItem(action if action else "")
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setForeground(_seq_action_color(action))
            action_item.setFont(bold)
            action_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 1, action_item)

            for col, key in [(2, "addr"), (3, "msb"), (4, "lsb"), (5, "value")]:
                cell = QTableWidgetItem(parsed.get(key, ""))
                cell.setTextAlignment(Qt.AlignCenter)
                cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(row, col, cell)

            desc_item = QTableWidgetItem(parsed.get("desc", ""))
            desc_item.setForeground(muted)
            desc_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 6, desc_item)
        self._i2c_seq_suppress_sync = False

    def _i2c_seq_current_script(self):
        """从 YAML 编辑器获取当前脚本 dict。"""
        try:
            return _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
        except Exception:
            return {
                "name": self.i2c_seq_name_edit.text().strip(),
                "description": self.i2c_seq_desc_edit.text().strip(),
                "commands": [],
            }

    def _i2c_seq_sync_from_yaml(self):
        """从 YAML 解析并刷新表格 + Name/Desc/Tpl 输入框。"""
        try:
            script = _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "YAML 解析失败", str(e))
            return False
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_name_edit.setText(str(script.get("name", "")))
        self.i2c_seq_desc_edit.setText(str(script.get("description", "")))
        self._i2c_seq_set_tpl_combo(str(script.get("template", "")))
        cmds = [str(c) for c in (script.get("commands", []) or [])]
        self._i2c_seq_refresh_table(cmds)
        self._i2c_seq_suppress_sync = False
        return True

    def _i2c_seq_sync_to_yaml(self):
        """将 Name/Desc/Tpl + 当前 commands 刷回 YAML 编辑器。"""
        script = self._i2c_seq_current_script()
        script["name"] = self.i2c_seq_name_edit.text().strip()
        script["description"] = self.i2c_seq_desc_edit.text().strip()
        script["template"] = self._i2c_seq_tpl_combo_current()
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
        self._i2c_seq_suppress_sync = False

    def _on_i2c_seq_toggle_mode(self):
        """切换 表格 ↔ YAML 模式。"""
        if self.i2c_seq_tabs.currentIndex() == 0:
            self.i2c_seq_tabs.setCurrentIndex(1)
            self.i2c_seq_mode_btn.setText("Table")
        else:
            if not self._i2c_seq_sync_from_yaml():
                return
            self.i2c_seq_tabs.setCurrentIndex(0)
            self.i2c_seq_mode_btn.setText("YAML")

    def _on_i2c_seq_new(self):
        """新建空脚本（默认关联当前活动模板）。"""
        self.i2c_seq_list.clearSelection()
        self._i2c_seq_current_index = None
        self._i2c_seq_clear_editor()
        self.i2c_seq_name_edit.setText("NewSequence")
        # 默认关联当前活动模板
        self._i2c_seq_set_tpl_combo(self._i2c_active_template_name)
        # 同步到 YAML
        script = self._i2c_seq_current_script()
        script["name"] = "NewSequence"
        script["template"] = self._i2c_active_template_name
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
        self._i2c_seq_suppress_sync = False
        self.i2c_seq_name_edit.setFocus()
        self.i2c_seq_name_edit.selectAll()
        self.append_log(
            f"[I2C] 新建序列脚本（未保存，关联模板: "
            f"{self._i2c_active_template_name or '(none)'}）")

    def _on_i2c_seq_duplicate(self):
        """复制当前选中脚本。"""
        if self._i2c_seq_current_index is None:
            QMessageBox.information(self, "提示", "请先在列表中选择一个脚本")
            return
        _path, script = self._i2c_sequences[self._i2c_seq_current_index]
        new_script = copy.deepcopy(script)
        new_script["name"] = str(script.get("name", "")) + "_copy"
        self.i2c_seq_list.clearSelection()
        self._i2c_seq_current_index = None
        self._i2c_seq_load_to_editor(new_script)
        self.append_log("[I2C] 已复制脚本，请修改名称后保存")

    def _on_i2c_seq_delete(self):
        """删除当前选中脚本文件。"""
        if self._i2c_seq_current_index is None:
            QMessageBox.information(self, "提示", "请先在列表中选择一个脚本")
            return
        path, script = self._i2c_sequences[self._i2c_seq_current_index]
        name = script.get("name", "")
        ret = QMessageBox.question(
            self, "删除确认", "确定删除脚本 '{0}'?".format(name))
        if ret != QMessageBox.Yes:
            return
        _delete_sequence_file(path)
        self.append_log(f"[I2C] 已删除脚本: {name}")
        self._i2c_seq_current_index = None
        self._i2c_seq_reload_list()
        self._i2c_save_state()

    def _on_i2c_seq_add_cmd(self):
        """新增一行指令（修改 YAML 并刷新表格）。"""
        script = self._i2c_seq_current_script()
        script["name"] = self.i2c_seq_name_edit.text().strip()
        script["description"] = self.i2c_seq_desc_edit.text().strip()
        script["template"] = self._i2c_seq_tpl_combo_current()
        script.setdefault("commands", []).append("WRITE 0x00 0x00")
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
        self._i2c_seq_refresh_table(script.get("commands", []))
        self._i2c_seq_suppress_sync = False
        new_row = self.i2c_seq_cmd_table.rowCount() - 1
        if new_row >= 0:
            self.i2c_seq_cmd_table.selectRow(new_row)

    def _on_i2c_seq_del_cmd(self):
        """删除选中的指令行（修改 YAML 并刷新表格）。"""
        rows = self.i2c_seq_cmd_table.selectionModel().selectedRows()
        if not rows:
            return
        script = self._i2c_seq_current_script()
        script["name"] = self.i2c_seq_name_edit.text().strip()
        script["description"] = self.i2c_seq_desc_edit.text().strip()
        script["template"] = self._i2c_seq_tpl_combo_current()
        cmds = script.get("commands", []) or []
        indices = sorted([r.row() for r in rows], reverse=True)
        for idx in indices:
            if 0 <= idx < len(cmds):
                del cmds[idx]
        script["commands"] = cmds
        self._i2c_seq_suppress_sync = True
        self.i2c_seq_yaml_edit.setPlainText(_serialize_script_yaml(script))
        self._i2c_seq_refresh_table(cmds)
        self._i2c_seq_suppress_sync = False

    def _on_i2c_seq_save(self):
        """保存当前编辑器内容到 YAML 文件。"""
        try:
            script = _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "YAML 解析失败", str(e))
            return
        script["name"] = self.i2c_seq_name_edit.text().strip()
        script["description"] = self.i2c_seq_desc_edit.text().strip()
        script["template"] = self._i2c_seq_tpl_combo_current()
        name = script.get("name", "").strip()
        if not name:
            QMessageBox.warning(self, "名称无效", "请填写脚本名称")
            return
        try:
            path = _save_sequence_file(script)
            self.append_log(f"[I2C] 序列脚本已保存: {path}")
            # 保存后刷新列表并选中新保存的项
            self._i2c_seq_reload_list()
            for i, (_p, s) in enumerate(self._i2c_sequences):
                if s.get("name") == name:
                    self.i2c_seq_list.selectRow(i)
                    break
            self._i2c_save_state()
        except Exception as e:
            logger.error("I2C save sequence failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "保存失败", str(e))

    def _i2c_seq_execute(self, script):
        """执行指定脚本 dict。"""
        if (self._i2c_script_thread is not None
                and self._i2c_script_thread.isRunning()):
            QMessageBox.information(self, "正在执行", "请等待当前序列执行结束")
            return
        commands = script.get("commands", []) or []
        if not commands:
            QMessageBox.information(self, "脚本为空", "该脚本没有可执行指令")
            return
        dev = self._i2c_current_dev()
        name = script.get("name", "")
        self._i2c_set_busy(True)
        self._i2c_set_activity("Sequence…", ok=True)
        self.append_log(
            f"[I2C] Sequence '{name}' 开始 dev=0x{dev:02X} "
            f"width={_width_label(self._i2c_width)} 指令数={len(commands)}")
        worker = _I2cSequenceWorker(
            self._i2c_dll_path(), self._i2c_speed_mode, dev,
            self._i2c_width, commands, script_name=name,
            data_bits=self._i2c_data_bits)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_i2c_seq_progress)
        worker.finished.connect(self._on_i2c_seq_finished)
        worker.error.connect(self._on_i2c_seq_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_i2c_seq_thread_cleanup)
        self._i2c_script_worker = worker
        self._i2c_script_thread = thread
        self.i2c_seq_stop_btn.setEnabled(True)
        thread.start()

    def _on_i2c_seq_run(self):
        """Run 按钮：执行当前编辑器中的脚本。"""
        try:
            script = _parse_script_yaml(self.i2c_seq_yaml_edit.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "YAML 解析失败", str(e))
            return
        self._i2c_seq_execute(script)

    def _on_i2c_seq_stop(self):
        worker = getattr(self, "_i2c_script_worker", None)
        if worker is not None:
            worker.request_stop()
            self.append_log("[I2C] 已请求停止序列执行")
        self.i2c_seq_stop_btn.setEnabled(False)

    def _on_i2c_seq_progress(self, text):
        self.append_log(f"[I2C] {text}")

    def _on_i2c_seq_thread_cleanup(self):
        self._i2c_script_thread = None
        self._i2c_script_worker = None

    def _on_i2c_seq_finished(self):
        self._i2c_set_activity("Sequence", ok=True)
        self._i2c_set_result("Sequence Done", ok=True)
        self._i2c_set_busy(False)
        self.append_log("[I2C] 序列执行结束")

    def _on_i2c_seq_error(self, err):
        self._i2c_set_activity("Sequence", ok=False)
        self._i2c_set_result(f"Sequence Failed: {err}", ok=False)
        self._i2c_set_busy(False)
        self.append_log(f"[I2C] 序列执行失败: {err}")

    # ---- 模板管理（列表 + 持久化 + 与脚本联动） ----

    def _i2c_serialize_template(self):
        """将当前 UI 状态序列化为模板 dict。

        当 _i2c_registers 非空时保留原有寄存器列表；否则将当前工作区状态
        序列化为单个寄存器，保证模板始终有至少一条寄存器。
        """
        registers = copy.deepcopy(self._i2c_registers)
        if not registers:
            registers = [{
                "name": "REG0",
                "reg_addr": _fmt_hex(self._i2c_current_reg(),
                                     self._i2c_reg_bits),
                "data_bits": self._i2c_data_bits,
                "reg_bits": self._i2c_reg_bits,
                "description": "",
                "bit_fields": copy.deepcopy(self._i2c_fields),
            }]
        return {
            "name": self._i2c_active_template_name or "I2C Template",
            "device_addr": _fmt_hex(self._i2c_current_dev(),
                                    self._i2c_reg_bits),
            "speed_mode": int(self._i2c_speed_mode),
            "data_bits": self._i2c_data_bits,
            "reg_bits": self._i2c_reg_bits,
            "registers": registers,
        }

    def _i2c_tpl_reload_combo(self):
        """重新扫描模板目录并刷新模板 combo。"""
        self._i2c_templates = _load_all_templates()
        combo = self.i2c_tpl_combo
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(none)", userData="")
        for _path, tpl in self._i2c_templates:
            combo.addItem(str(tpl.get("name", "")), userData=str(tpl.get("name", "")))
        combo.blockSignals(False)
        # 同步刷新脚本编辑器中的模板 combo
        if hasattr(self, "i2c_seq_tpl_combo"):
            sc = self.i2c_seq_tpl_combo
            sc.blockSignals(True)
            sc.clear()
            sc.addItem("(none)", userData="")
            for _path, tpl in self._i2c_templates:
                sc.addItem(str(tpl.get("name", "")),
                           userData=str(tpl.get("name", "")))
            sc.blockSignals(False)

    def _i2c_tpl_combo_current_name(self):
        """获取模板 combo 当前选中的模板名称。"""
        idx = self.i2c_tpl_combo.currentIndex()
        if idx <= 0:
            return ""
        name = self.i2c_tpl_combo.currentData()
        return str(name) if name else ""

    def _i2c_select_template_by_name(self, name):
        """在模板 combo 中按名称选中模板（不触发信号副作用）。"""
        combo = self.i2c_tpl_combo
        combo.blockSignals(True)
        target_idx = 0
        for i in range(combo.count()):
            if str(combo.itemData(i)) == str(name):
                target_idx = i
                break
        combo.setCurrentIndex(target_idx)
        combo.blockSignals(False)

    def _i2c_apply_template_to_ui(self, template_dict):
        """将模板 dict 应用到 UI（位宽 + 速率 + 设备地址 + 第一个寄存器的字段）。"""
        from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
        self._i2c_registers = copy.deepcopy(template_dict.get("registers", []))
        self._i2c_active_reg_index = None

        try:
            speed = I2CSpeedMode(int(template_dict.get("speed_mode", 1)))
            for i in range(self.i2c_speed_combo.count()):
                if self.i2c_speed_combo.itemData(i) == speed:
                    self.i2c_speed_combo.blockSignals(True)
                    self.i2c_speed_combo.setCurrentIndex(i)
                    self.i2c_speed_combo.blockSignals(False)
                    break
            self._i2c_speed_mode = speed
        except Exception:
            pass
        data_bits = int(template_dict.get("data_bits", 16))
        reg_bits = int(template_dict.get("reg_bits", _infer_reg_bits(data_bits)))
        self._i2c_set_width(reg_bits, data_bits)
        dev = template_dict.get("device_addr")
        if dev is not None:
            self.i2c_dev_edit.set_value(_parse_hex_int(dev) or 0)

        # 加载第一个寄存器的地址与字段到工作区
        if self._i2c_registers:
            reg = self._i2c_registers[0]
            self._i2c_active_reg_index = 0
            reg_addr = _parse_hex_int(reg.get("reg_addr", "0x0")) or 0
            self.i2c_reg_edit.set_value(reg_addr)
            self._i2c_fields = copy.deepcopy(reg.get("bit_fields", []))
            self.i2c_bits.set_fields(self._i2c_fields)
            self.i2c_bits.set_value(self._i2c_data_value)
        else:
            self._i2c_fields = []
            self.i2c_bits.set_fields([])

    def _on_i2c_tpl_combo_changed(self, _idx):
        """模板 combo 选择变化 → 加载模板 + 刷新脚本列表。"""
        name = self._i2c_tpl_combo_current_name()
        self._i2c_active_template_name = name
        if not name:
            # 切到 (none)：清空当前字段
            self._i2c_registers = []
            self._i2c_active_reg_index = None
            self._i2c_fields = []
            self.i2c_bits.set_fields([])
            self.i2c_bits.set_value(self._i2c_data_value)
        else:
            for _path, tpl in self._i2c_templates:
                if str(tpl.get("name", "")) == name:
                    self._i2c_apply_template_to_ui(tpl)
                    break
        # 刷新脚本列表（按新模板过滤）
        if hasattr(self, "i2c_seq_list"):
            self._i2c_seq_reload_list()
        self.append_log(f"[I2C] 切换模板: {name or '(none)'}")
        self._i2c_save_state()

    def _on_i2c_edit_toggled(self, checked):
        """Edit 滑动开关：开启/关闭 Payload Data Bits 位表的内联编辑模式。

        ON  → 位表的 Field/Desc 列可双击编辑，+ Field 按钮可见，
              右键可创建/编辑/删除字段。
        OFF → 位表只读，+ Field 按钮隐藏，右键无效。
        """
        self.i2c_bits.set_edit_mode(checked)
        self.i2c_add_field_btn.setVisible(checked)
        self.append_log(
            f"[I2C] 模板编辑模式: {'ON' if checked else 'OFF'}")

    def _on_i2c_tpl_save(self):
        """保存当前 UI 状态到模板文件（按名称）。"""
        name = self._i2c_active_template_name.strip()
        if not name:
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(
                self, "保存模板", "模板名称:", text="NewTemplate")
            if not ok or not name.strip():
                return
            name = name.strip()
            self._i2c_active_template_name = name
        data = self._i2c_serialize_template()
        data["name"] = name
        try:
            path = _save_template_file(data)
            self.append_log(f"[I2C] 模板已保存: {path}")
            self._i2c_tpl_reload_combo()
            self._i2c_select_template_by_name(name)
            # 模板列表变化后，刷新脚本编辑器中的模板 combo
            if hasattr(self, "i2c_seq_tpl_combo"):
                self._i2c_seq_set_tpl_combo(name)
            self._i2c_save_state()
        except Exception as e:
            logger.error("I2C save template failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "保存失败", str(e))

    def _on_i2c_tpl_export(self):
        """通过 FileDialog 导出到任意 JSON 文件（备用）。"""
        data = self._i2c_serialize_template()
        default_path = os.path.join(_i2c_template_dir(),
                                   _tpl_filename_for(data["name"]) + ".json")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 I2C 模板", default_path, "JSON (*.json);;All (*.*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.append_log(f"[I2C] 模板已导出: {path}")
        except Exception as e:
            logger.error("I2C export template failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "导出失败", str(e))

    def _on_i2c_tpl_import(self):
        """通过 FileDialog 从任意 JSON 文件导入模板。"""
        start_dir = _i2c_template_dir()
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 I2C 模板", start_dir, "JSON (*.json);;All (*.*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("I2C import template failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "导入失败", str(e))
            return
        if not isinstance(data, dict):
            QMessageBox.critical(self, "导入失败", "JSON 顶层必须为字典")
            return
        # 保存到模板目录
        name = str(data.get("name", "")).strip()
        if not name:
            name = "ImportedTemplate"
            data["name"] = name
        try:
            _save_template_file(data)
            self._i2c_tpl_reload_combo()
            self._i2c_select_template_by_name(name)
            self._i2c_active_template_name = name
            self._i2c_apply_template_to_ui(data)
            self.append_log(f"[I2C] 模板已导入: {name}")
            self._i2c_save_state()
        except Exception as e:
            logger.error("I2C import template save failed: %s", e, exc_info=True)
            QMessageBox.critical(self, "导入失败", str(e))

    # ---- 脚本编辑器中的模板 combo 辅助 ----

    def _i2c_seq_tpl_combo_current(self):
        """获取脚本编辑器中模板 combo 的当前值。"""
        idx = self.i2c_seq_tpl_combo.currentIndex()
        if idx <= 0:
            return ""
        data = self.i2c_seq_tpl_combo.currentData()
        return str(data) if data else ""

    def _i2c_seq_set_tpl_combo(self, name):
        """设置脚本编辑器中的模板 combo（不触发信号副作用）。"""
        sc = self.i2c_seq_tpl_combo
        sc.blockSignals(True)
        target_idx = 0
        for i in range(sc.count()):
            if str(sc.itemData(i)) == str(name):
                target_idx = i
                break
        sc.setCurrentIndex(target_idx)
        sc.blockSignals(False)

    def _on_i2c_seq_tpl_combo_changed(self, _idx):
        """脚本编辑器中的模板 combo 变化 → 刷新 YAML。"""
        if self._i2c_seq_suppress_sync:
            return
        self._i2c_seq_sync_to_yaml()

    def _on_i2c_seq_filter_toggled(self, _checked):
        """脚本列表过滤按钮切换 → 刷新列表。"""
        self._i2c_filter_scripts_by_template = \
            self.i2c_seq_filter_btn.isChecked()
        self._i2c_seq_reload_list()
        self._i2c_save_state()

    # ---- I2C 模块状态持久化 ----

    def _i2c_save_state(self):
        """保存当前状态到 i2c_state.json。"""
        state = {
            "version": "1.0",
            "last_template": self._i2c_active_template_name,
            "last_script": "",
            "filter_scripts_by_template": bool(
                self._i2c_filter_scripts_by_template),
            "settings": {
                "dll_path": getattr(self, "_i2c_custom_dll", None) or "",
                "default_speed_mode": int(self._i2c_speed_mode),
                "default_data_bits": int(self._i2c_data_bits),
                "default_reg_bits": int(self._i2c_reg_bits),
            },
        }
        # 记录当前选中的脚本名
        if getattr(self, "_i2c_seq_current_index", None) is not None:
            idx = self._i2c_seq_current_index
            if 0 <= idx < len(self._i2c_sequences):
                _p, s = self._i2c_sequences[idx]
                state["last_script"] = str(s.get("name", ""))
        _save_i2c_state(state)

    def _i2c_restore_state(self):
        """应用持久化状态到 UI（在 UI 构建完成后调用）。"""
        state = getattr(self, "_i2c_pending_state", None) or {}
        if not state:
            # 无状态文件：仅刷新模板列表与脚本列表
            self._i2c_tpl_reload_combo()
            self._i2c_seq_reload_list()
            return
        # 1. 应用设置（DLL / 默认速率 / 默认位宽）
        settings = state.get("settings", {}) or {}
        dll = settings.get("dll_path", "")
        if dll:
            self._i2c_custom_dll = dll
            if hasattr(self, "i2c_dll_edit"):
                self._i2c_refresh_dll_display()
        speed_mode = settings.get("default_speed_mode")
        if speed_mode is not None and hasattr(self, "i2c_speed_combo"):
            try:
                from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
                speed = I2CSpeedMode(int(speed_mode))
                for i in range(self.i2c_speed_combo.count()):
                    if self.i2c_speed_combo.itemData(i) == speed:
                        self.i2c_speed_combo.blockSignals(True)
                        self.i2c_speed_combo.setCurrentIndex(i)
                        self.i2c_speed_combo.blockSignals(False)
                        break
                self._i2c_speed_mode = speed
            except Exception:
                pass
        bits = settings.get("default_data_bits", 16)
        reg_bits = settings.get("default_reg_bits", _infer_reg_bits(bits))
        self._i2c_set_width(int(reg_bits), int(bits))
        # 2. 应用过滤开关
        filter_flag = state.get("filter_scripts_by_template", True)
        if hasattr(self, "i2c_seq_filter_btn"):
            self.i2c_seq_filter_btn.blockSignals(True)
            self.i2c_seq_filter_btn.setChecked(bool(filter_flag))
            self.i2c_seq_filter_btn.blockSignals(False)
            self._i2c_filter_scripts_by_template = bool(filter_flag)
        # 3. 刷新模板 combo
        self._i2c_tpl_reload_combo()
        # 4. 应用上次活动模板
        last_tpl = str(state.get("last_template", ""))
        if last_tpl:
            self._i2c_select_template_by_name(last_tpl)
            self._i2c_active_template_name = last_tpl
            # 加载模板数据到 UI
            for _path, tpl in self._i2c_templates:
                if str(tpl.get("name", "")) == last_tpl:
                    self._i2c_apply_template_to_ui(tpl)
                    break
        # 5. 刷新脚本列表（按模板过滤）
        self._i2c_seq_reload_list()
        # 6. 应用上次选中的脚本
        last_script = str(state.get("last_script", ""))
        if last_script:
            for i, (_p, s) in enumerate(self._i2c_sequences):
                if str(s.get("name", "")) == last_script:
                    self.i2c_seq_list.selectRow(i)
                    break
        self.append_log(
            f"[I2C] 状态已恢复: 模板={last_tpl or '(none)'} "
            f"脚本={last_script or '(none)'}")

    # ---- 资源释放 ----

    def close_i2c(self):
        """关闭 I2C 模块时保存持久化状态。"""
        try:
            self._i2c_save_state()
        except Exception:
            logger.error("I2C save state on close failed", exc_info=True)
