# -*- coding: utf-8 -*-
"""GPIO 页 UI 构建 Mixin（顶栏 / DUT 面板 / 批处理工具条 / 5 大视图）。"""

import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy, QStackedWidget,
    QPlainTextEdit, QTextEdit, QLineEdit, QButtonGroup
)
from PySide6.QtCore import Qt, QTimer

from ui.utils.icon_utils import tinted_svg_pixmap
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.wheel_line_edit import HexWheelLineEdit
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from core.gpio.gpio_config import list_gpio_config_chips

from ui.pages.gpio.gpio_control.style import _GPIO_PAGE_QSS, _ICONS_DIR
from ui.pages.gpio.gpio_control.utils import _speed_options, _icon

class ViewBuildMixin:
    """UI 构建：_build_* 工厂集合（顶栏/DUT 面板/批处理工具条/5 大视图）。"""

    # ================================================================ UI 构建

    def _build_ui(self):
        self.setStyleSheet(_GPIO_PAGE_QSS)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        content = QWidget()
        content.setObjectName("gpioContent")
        clay = QVBoxLayout(content)
        clay.setContentsMargins(0, 0, 0, 0)
        clay.setSpacing(6)

        clay.addLayout(self._build_top_bar())
        clay.addWidget(self._build_dut_panel())
        clay.addWidget(self._build_batch_toolbar())

        self._stack = QStackedWidget()
        clay.addWidget(self._stack, 1)
        self._build_views()

        self._splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            content, title="Activity Logs", show_progress=False,
            stretch=(5, 1))
        root.addWidget(self._splitter, 1)
        # AI 枢纽日志契约：_get_ai_execution_logs 经 page.logs_frame._all_logs 读取
        self.logs_frame = self.execution_logs

        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._on_poll_tick)

        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(100)
        self._spin_timer.timeout.connect(self._on_spin_tick)

        # 延迟读定时器：页内子对象（页面销毁自动失效），重复延迟合并为最后一次
        self._deferred_read_fn = None
        self._deferred_timer = QTimer(self)
        self._deferred_timer.setSingleShot(True)
        self._deferred_timer.timeout.connect(self._on_deferred_read)

        self.append_log("[INFO] BES GPIO Workbench ready. "
                        "Click i2c.bes_chip_check() to connect DUT")
        self._refresh_all_views()

        # §5b：登记本页按钮为 AI 具名 UI 动作（白名单制，handler 复用原槽）
        self._register_ai_ui_actions()

    def _build_top_bar(self):
        row = QHBoxLayout()
        row.setSpacing(6)

        chip_icon = QLabel()
        pm = tinted_svg_pixmap(os.path.join(_ICONS_DIR, "gpio-pins.svg"), "#22D3EE", 18)
        if not pm.isNull():
            chip_icon.setPixmap(pm)
        row.addWidget(chip_icon)

        title = QLabel("BES GPIO Workbench")
        title.setObjectName("gpioTitle")
        self.dut_sub = QLabel("DUT: --")
        self.dut_sub.setObjectName("gpioSub")
        head = QVBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(0)
        head.addWidget(title)
        head.addWidget(self.dut_sub)
        row.addLayout(head)
        row.addSpacing(8)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_buttons = []
        for idx, (short, full) in enumerate(self.VIEW_TITLES):
            btn = QPushButton(short)
            btn.setObjectName("gpioTab")
            btn.setCheckable(True)
            btn.setToolTip(full)
            # 垂直撑满顶栏（高度 = 标题 + DUT 副标题两行），勿在 QSS 钉死
            btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
            self._tab_group.addButton(btn, idx)
            row.addWidget(btn)
            self._tab_buttons.append(btn)
        self._tab_group.idClicked.connect(self._on_tab_changed)
        self._tab_buttons[0].setChecked(True)

        row.addStretch(1)

        row.addWidget(QLabel("Speed"))
        self.speed_combo = DarkComboBox()
        for mode, label in _speed_options():
            self.speed_combo.addItem(label, mode)
        self.speed_combo.setCurrentIndex(1)  # 100 kHz
        self.speed_combo.setToolTip("USB-I2C bridge speed")
        row.addWidget(self.speed_combo)

        self.detect_btn = QPushButton("i2c.bes_chip_check()")
        self.detect_btn.setObjectName("gpioPrimary")
        self.detect_btn.setIcon(_icon("refresh-cw.svg", "#22D3EE", 13))
        self.detect_btn.clicked.connect(self._on_detect_clicked)
        row.addWidget(self.detect_btn)
        return row

    def _build_dut_panel(self):
        panel = QFrame()
        panel.setObjectName("gpioPanel")
        lay = QHBoxLayout(panel)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        dut_key = QLabel("DUT")
        dut_key.setObjectName("gpioPanelKey")
        lay.addWidget(dut_key)
        self.profile_combo = DarkComboBox()
        self.profile_combo.setToolTip(
            "DUT Profile (chips/gpio_configs/*.json presets)")
        for name in list_gpio_config_chips():
            self.profile_combo.addItem(name.upper(), name)
        lay.addWidget(self.profile_combo)
        self.load_btn = QPushButton("Load")
        self.load_btn.setObjectName("gpioBtn")
        self.load_btn.setToolTip(
            "Load selected DUT Profile (requires i2c.bes_chip_check() first)")
        self.load_btn.clicked.connect(self._on_load_profile_clicked)
        lay.addWidget(self.load_btn)

        lay.addWidget(self._make_vsep())

        bank_key = QLabel("Bank")
        bank_key.setObjectName("gpioPanelKey")
        lay.addWidget(bank_key)
        self._bank_group = QButtonGroup(self)
        self._bank_group.setExclusive(True)
        self._bank_buttons = []
        self._bank_box = QHBoxLayout()
        self._bank_box.setContentsMargins(0, 0, 0, 0)
        self._bank_box.setSpacing(4)
        lay.addLayout(self._bank_box)
        self._bank_group.idClicked.connect(self._on_bank_changed)

        lay.addWidget(self._make_vsep())

        addr_box = QVBoxLayout()
        addr_box.setContentsMargins(0, 0, 0, 0)
        addr_box.setSpacing(0)
        self.addr_label = QLabel("Base --")
        self.addr_label.setObjectName("gpioAddr")
        addr_box.addWidget(self.addr_label)
        self.bank_label = QLabel("Bank --")
        self.bank_label.setObjectName("gpioBankInfo")
        addr_box.addWidget(self.bank_label)
        lay.addLayout(addr_box)

        lay.addWidget(self._make_vsep())

        self._stat_vals = {}
        for key, label in (("out", "OUT"), ("in", "IN"), ("high", "HIGH"),
                           ("low", "LOW"), ("pu", "PU"), ("pd", "PD")):
            box = QVBoxLayout()
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(0)
            k = QLabel(label)
            k.setObjectName("gpioStatKey")
            k.setAlignment(Qt.AlignCenter)
            v = QLabel("-")
            v.setObjectName("gpioStatVal")
            v.setProperty("k", key)
            v.setAlignment(Qt.AlignCenter)
            box.addWidget(k)
            box.addWidget(v)
            lay.addLayout(box)
            self._stat_vals[key] = v

        lay.addStretch(1)

        self.status_label = QLabel("Not Detected")
        self.status_label.setObjectName("gpioStatus")
        lay.addWidget(self.status_label)
        return panel

    def _build_batch_toolbar(self):
        bar = QFrame()
        bar.setObjectName("gpioPanel")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 5, 10, 5)
        lay.setSpacing(6)

        batch_defs = [
            ("All OUT HIGH", self._on_batch_out_high,
             "Set all pins of current Bank to output HIGH "
             "(DIR_SET+VAL_SET = valid pin mask)"),
            ("All OUT LOW", self._on_batch_out_low,
             "Set all pins of current Bank to output LOW "
             "(DIR_SET+VAL_CLR = valid pin mask)"),
            ("All IN Hi-Z", self._on_batch_in_hiz,
             "Set all pins of current Bank to Hi-Z input "
             "(DIR_CLR = valid pin mask, PU/PD off)"),
            ("All PU", lambda: self._on_batch_pull(True),
             "Pull up all pins of current Bank (OP_BITS bitfield write)"),
            ("All PD", lambda: self._on_batch_pull(False),
             "Pull down all pins of current Bank (OP_BITS bitfield write)"),
            ("Invert OUT", self._on_batch_invert,
             "Invert HIGH/LOW level of all output pins in current Bank"),
        ]
        self._batch_buttons = []
        for text, slot, tip in batch_defs:
            btn = QPushButton(text)
            btn.setObjectName("gpioBatch")
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
            self._batch_buttons.append(btn)

        lay.addWidget(self._make_vsep())

        mask_key = QLabel("Mask")
        mask_key.setObjectName("gpioPanelKey")
        lay.addWidget(mask_key)
        self.mask_edit = HexWheelLineEdit()
        self.mask_edit.setObjectName("gpioHexEdit")
        self.mask_edit.setPlaceholderText("0x000000FF")
        self.mask_edit.setFixedWidth(110)
        self.mask_edit.setToolTip("32-bit hex mask (wheel to adjust)")
        lay.addWidget(self.mask_edit)
        self.mask_target = DarkComboBox()
        for label, off in self.MASK_TARGETS:
            self.mask_target.addItem(label, off)
        lay.addWidget(self.mask_target)
        self.mask_btn = QPushButton("Write Mask")
        self.mask_btn.setObjectName("gpioBtn")
        self.mask_btn.setToolTip("Write mask into the selected SET/CLR register")
        self.mask_btn.clicked.connect(self._on_mask_write_clicked)
        lay.addWidget(self.mask_btn)

        lay.addStretch(1)
        return bar

    def _make_vsep(self):
        sep = QFrame()
        sep.setObjectName("gpioSep")
        return sep

    # ------------------------------------------------------------ 5 大视图

    def _build_views(self):
        self._stack.addWidget(self._build_matrix_view())   # 0
        self._stack.addWidget(self._build_regmap_view())   # 1
        self._stack.addWidget(self._build_sniffer_view())  # 2
        self._stack.addWidget(self._build_json_view())     # 3
        self._stack.addWidget(self._build_notes_view())    # 4

    # 视图 1：Pin Matrix Grid + Inspector
    def _build_matrix_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._matrix_scroll = QScrollArea()
        self._matrix_scroll.setObjectName("gpioScroll")
        self._matrix_scroll.setWidgetResizable(True)
        self._matrix_scroll.setFrameShape(QFrame.NoFrame)
        self._matrix_container = QWidget()
        self._matrix_container.setObjectName("gpioViewPage")
        cols = QHBoxLayout(self._matrix_container)
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(6)
        self._matrix_col_l = QVBoxLayout()
        self._matrix_col_l.setContentsMargins(0, 0, 0, 0)
        self._matrix_col_l.setSpacing(0)
        self._matrix_col_r = QVBoxLayout()
        self._matrix_col_r.setContentsMargins(0, 0, 0, 0)
        self._matrix_col_r.setSpacing(0)
        divider = QFrame()
        divider.setObjectName("matrixDivider")
        cols.addLayout(self._matrix_col_l, 1)
        cols.addWidget(divider)
        cols.addLayout(self._matrix_col_r, 1)
        self._matrix_placeholder = QLabel(
            "Run i2c.bes_chip_check() or load a DUT Profile first")
        self._matrix_placeholder.setObjectName("gpioStatus")
        self._matrix_placeholder.setAlignment(Qt.AlignCenter)
        self._matrix_col_l.addWidget(self._matrix_placeholder)
        self._matrix_scroll.setWidget(self._matrix_container)
        left = QVBoxLayout()
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(6)
        left.addWidget(self._matrix_scroll, 1)
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(6)
        self.read_btn = QPushButton("READ")
        self.read_btn.setObjectName("gpioReadBtn")
        self.read_btn.setToolTip(
            "Read current Bank input status register Base + 0x50 now")
        self.read_btn.clicked.connect(self._on_read_bank_clicked)
        bottom.addWidget(self.read_btn, 1)
        poll_key = QLabel("Poll 0x50")
        poll_key.setObjectName("gpioPanelKey")
        bottom.addWidget(poll_key)
        self.poll_combo = DarkComboBox()
        for ms, label in self.POLL_INTERVALS:
            self.poll_combo.addItem(label, ms)
        self.poll_combo.setCurrentIndex(1)  # 500 ms
        self.poll_combo.currentIndexChanged.connect(self._on_poll_interval_changed)
        bottom.addWidget(self.poll_combo)
        self.poll_btn = QPushButton("Start Poll")
        self.poll_btn.setObjectName("gpioBtn")
        self.poll_btn.setProperty("on", "0")
        self.poll_btn.setToolTip(
            "Periodically poll current Bank input status register Base + 0x50")
        self.poll_btn.clicked.connect(self._on_poll_toggled)
        bottom.addWidget(self.poll_btn)
        left.addLayout(bottom)
        lay.addLayout(left, 1)

        lay.addWidget(self._build_inspector())
        self._export_panel = self._build_export_manager()
        self._export_panel.hide()   # 至少一个导出条目时才显示
        lay.addWidget(self._export_panel)
        return page

    def _build_inspector(self):
        panel = QFrame()
        panel.setObjectName("gpioInspector")
        panel.setFixedWidth(300)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(6)
        self.insp_name = QLabel("GPIO--")
        self.insp_name.setObjectName("gpioPinName")
        head.addWidget(self.insp_name)
        head.addStretch(1)
        lay.addLayout(head)

        # 单选信息区（别名 + 脚位信息）；多选时隐藏
        self._insp_single_box = QWidget()
        single_lay = QVBoxLayout(self._insp_single_box)
        single_lay.setContentsMargins(0, 0, 0, 0)
        single_lay.setSpacing(6)
        alias_row = QHBoxLayout()
        alias_row.setSpacing(6)
        alias_key = QLabel("Alias")
        alias_key.setObjectName("gpioPanelKey")
        alias_row.addWidget(alias_key)
        self.alias_edit = QLineEdit()
        self.alias_edit.setObjectName("gpioAliasEdit")
        self.alias_edit.setPlaceholderText("Signal alias, e.g. LED_PWR / I2C_SDA")
        self.alias_edit.editingFinished.connect(self._on_alias_edited)
        alias_row.addWidget(self.alias_edit, 1)
        single_lay.addLayout(alias_row)
        self.insp_info = QLabel("-")
        self.insp_info.setObjectName("gpioPinInfo")
        single_lay.addWidget(self.insp_info)
        lay.addWidget(self._insp_single_box)

        # 多选列表区（Ctrl+Click 累加，配置区对全部选中脚统一生效）；单选时隐藏
        self._insp_multi_box = QWidget()
        multi_lay = QVBoxLayout(self._insp_multi_box)
        multi_lay.setContentsMargins(0, 0, 0, 0)
        multi_lay.setSpacing(4)
        hint = QLabel("Ctrl+Click toggles pins; config below applies to all")
        hint.setObjectName("gpioDim")
        multi_lay.addWidget(hint)
        self._multi_list_area = QScrollArea()
        self._multi_list_area.setObjectName("multiSelList")
        self._multi_list_area.setWidgetResizable(True)
        self._multi_list_area.setFrameShape(QFrame.NoFrame)
        self._multi_list_host = QWidget()
        self._multi_list_host.setObjectName("gpioViewPage")
        self._multi_list_lay = QVBoxLayout(self._multi_list_host)
        self._multi_list_lay.setContentsMargins(0, 0, 0, 0)
        self._multi_list_lay.setSpacing(3)
        self._multi_list_lay.addStretch(1)
        self._multi_list_area.setWidget(self._multi_list_host)
        multi_lay.addWidget(self._multi_list_area)
        lay.addWidget(self._insp_multi_box)

        lay.addWidget(self._make_hsep())

        dir_key = QLabel("Direction")
        dir_key.setObjectName("gpioSection")
        lay.addWidget(dir_key)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(6)
        self.insp_dir_out = QPushButton("OUTPUT")
        self.insp_dir_out.setObjectName("gpioAction")
        self.insp_dir_out.clicked.connect(lambda: self._on_insp_dir(True))
        dir_row.addWidget(self.insp_dir_out)
        self.insp_dir_in = QPushButton("INPUT")
        self.insp_dir_in.setObjectName("gpioAction")
        self.insp_dir_in.clicked.connect(lambda: self._on_insp_dir(False))
        dir_row.addWidget(self.insp_dir_in)
        lay.addLayout(dir_row)

        lvl_key = QLabel("Output Level")
        lvl_key.setObjectName("gpioSection")
        lay.addWidget(lvl_key)
        lvl_row = QHBoxLayout()
        lvl_row.setSpacing(6)
        self.insp_lvl_h = QPushButton("HIGH")
        self.insp_lvl_h.setObjectName("gpioAction")
        self.insp_lvl_h.clicked.connect(lambda: self._on_insp_level(True))
        lvl_row.addWidget(self.insp_lvl_h)
        self.insp_lvl_l = QPushButton("LOW")
        self.insp_lvl_l.setObjectName("gpioAction")
        self.insp_lvl_l.clicked.connect(lambda: self._on_insp_level(False))
        lvl_row.addWidget(self.insp_lvl_l)
        lay.addLayout(lvl_row)

        self.insp_pull_key = QLabel("Pull Tri-State (PU/PD are RW registers, bitfield write)")
        self.insp_pull_key.setObjectName("gpioSection")
        lay.addWidget(self.insp_pull_key)
        pull_row = QHBoxLayout()
        pull_row.setSpacing(6)
        self.insp_pull_hiz = QPushButton("High-Z")
        self.insp_pull_hiz.setObjectName("gpioAction")
        self.insp_pull_hiz.clicked.connect(lambda: self._on_insp_pull(0))
        pull_row.addWidget(self.insp_pull_hiz)
        self.insp_pull_pu = QPushButton("Pull-Up")
        self.insp_pull_pu.setObjectName("gpioAction")
        self.insp_pull_pu.clicked.connect(lambda: self._on_insp_pull(1))
        pull_row.addWidget(self.insp_pull_pu)
        self.insp_pull_pd = QPushButton("Pull-Down")
        self.insp_pull_pd.setObjectName("gpioAction")
        self.insp_pull_pd.clicked.connect(lambda: self._on_insp_pull(2))
        pull_row.addWidget(self.insp_pull_pd)
        lay.addLayout(pull_row)

        self.insp_drv_key = QLabel("Drive Strength")
        self.insp_drv_key.setObjectName("gpioSection")
        lay.addWidget(self.insp_drv_key)
        drv_row = QHBoxLayout()
        drv_row.setSpacing(6)
        self.insp_drv_dec = QPushButton("-")
        self.insp_drv_dec.setObjectName("gpioAction")
        self.insp_drv_dec.clicked.connect(lambda: self._on_drv_step(-1))
        drv_row.addWidget(self.insp_drv_dec)
        self.insp_drv_val = QLabel("Lv --")
        self.insp_drv_val.setObjectName("gpioMono")
        self.insp_drv_val.setAlignment(Qt.AlignCenter)
        drv_row.addWidget(self.insp_drv_val, 1)
        self.insp_drv_inc = QPushButton("+")
        self.insp_drv_inc.setObjectName("gpioAction")
        self.insp_drv_inc.clicked.connect(lambda: self._on_drv_step(1))
        drv_row.addWidget(self.insp_drv_inc)
        lay.addLayout(drv_row)

        # 单选状态区（0x50 大字电平 + mask 信息）；多选时隐藏
        self._insp_state_box = QWidget()
        state_lay = QVBoxLayout(self._insp_state_box)
        state_lay.setContentsMargins(0, 0, 0, 0)
        state_lay.setSpacing(6)
        state_lay.addWidget(self._make_hsep())
        read_row = QHBoxLayout()
        read_row.setSpacing(6)
        self.insp_big_state = QLabel("LOGIC --")
        self.insp_big_state.setObjectName("gpioBigState")
        read_row.addWidget(self.insp_big_state, 1)
        self.insp_read_btn = QPushButton("Read 0x50")
        self.insp_read_btn.setObjectName("gpioBtn")
        self.insp_read_btn.clicked.connect(self._on_read_bank_clicked)
        read_row.addWidget(self.insp_read_btn)
        state_lay.addLayout(read_row)
        self.insp_mask = QLabel("Mask --")
        self.insp_mask.setObjectName("gpioPinInfo")
        state_lay.addWidget(self.insp_mask)
        lay.addWidget(self._insp_state_box)

        lay.addStretch(1)
        return panel

    # Pin Matrix 右侧：Export Manager（右键 Export Config 收集，合并导出）
    def _build_export_manager(self):
        panel = QFrame()
        panel.setObjectName("gpioPanel")
        panel.setFixedWidth(340)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(8, 6, 8, 8)
        lay.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(6)
        title = QLabel("Export Manager")
        title.setObjectName("gpioSection")
        head.addWidget(title)
        self._export_count = QLabel("(0)")
        self._export_count.setObjectName("gpioDim")
        head.addWidget(self._export_count)
        head.addStretch(1)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("gpioBtn")
        clear_btn.setIcon(_icon("trash.svg", "#94A3B8", 12))
        clear_btn.setToolTip("Clear export list")
        clear_btn.clicked.connect(self._clear_export_items)
        head.addWidget(clear_btn)
        lay.addLayout(head)

        hint = QLabel("Right-click a pin in Pin Matrix -> Export Config to add")
        hint.setObjectName("gpioDim")
        lay.addWidget(hint)

        self._export_list_area = QScrollArea()
        self._export_list_area.setObjectName("exportList")
        self._export_list_area.setWidgetResizable(True)
        self._export_list_area.setFrameShape(QFrame.NoFrame)
        self._export_list_host = QWidget()
        self._export_list_host.setObjectName("gpioViewPage")
        self._export_list_lay = QVBoxLayout(self._export_list_host)
        self._export_list_lay.setContentsMargins(0, 0, 0, 0)
        self._export_list_lay.setSpacing(3)
        self._export_list_lay.addStretch(1)
        self._export_list_area.setWidget(self._export_list_host)
        lay.addWidget(self._export_list_area)

        preview_key = QLabel("Merged Script Preview (WRITE_BITS)")
        preview_key.setObjectName("gpioSection")
        lay.addWidget(preview_key)
        self._export_preview = QPlainTextEdit()
        self._export_preview.setObjectName("gpioMonoEdit")
        self._export_preview.setReadOnly(True)
        lay.addWidget(self._export_preview, 1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(6)
        self._exec_btn = QPushButton("Exec")
        self._exec_btn.setObjectName("gpioExec")
        self._exec_btn.setIcon(_icon("play.svg", "#BBF7D0", 12))
        self._exec_btn.setToolTip(
            "Apply all listed GPIO states to the DUT once "
            "(func_sel + mode, via I2C)")
        self._exec_btn.clicked.connect(self._on_export_exec)
        btn_row.addWidget(self._exec_btn)
        export_btn = QPushButton("Export")
        export_btn.setObjectName("gpioPrimary")
        export_btn.setIcon(_icon("copy.svg", "#E2E8F0", 12))
        export_btn.setToolTip(
            "Merge all GPIO configs into a WRITE_BITS script and copy to clipboard")
        export_btn.clicked.connect(self._on_export_copy)
        btn_row.addWidget(export_btn)
        lay.addLayout(btn_row)
        return panel

    def _make_hsep(self):
        sep = QFrame()
        sep.setObjectName("gpioHSep")
        sep.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        return sep

    # 视图 2：Register Map
    def _build_regmap_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QFrame()
        bar.setObjectName("gpioPanel")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(10, 5, 10, 5)
        bl.setSpacing(6)
        raw_key = QLabel("Raw Access")
        raw_key.setObjectName("gpioPanelKey")
        bl.addWidget(raw_key)
        self.raw_addr = HexWheelLineEdit()
        self.raw_addr.setObjectName("gpioHexEdit")
        self.raw_addr.setPlaceholderText("ADDR 0x40081000")
        self.raw_addr.setFixedWidth(150)
        bl.addWidget(self.raw_addr)
        self.raw_data = HexWheelLineEdit()
        self.raw_data.setObjectName("gpioHexEdit")
        self.raw_data.setPlaceholderText("DATA 0x00000001")
        self.raw_data.setFixedWidth(140)
        bl.addWidget(self.raw_data)
        self.raw_write_btn = QPushButton("Write32")
        self.raw_write_btn.setObjectName("gpioBtn")
        self.raw_write_btn.clicked.connect(self._on_raw_write)
        bl.addWidget(self.raw_write_btn)
        self.raw_read_btn = QPushButton("Read32")
        self.raw_read_btn.setObjectName("gpioBtn")
        self.raw_read_btn.clicked.connect(self._on_raw_read)
        bl.addWidget(self.raw_read_btn)
        self.raw_result = QLabel("--")
        self.raw_result.setObjectName("gpioAddr")
        bl.addWidget(self.raw_result)
        bl.addStretch(1)
        self.reg_refresh_btn = QPushButton("Refresh Readable")
        self.reg_refresh_btn.setObjectName("gpioBtn")
        self.reg_refresh_btn.setToolTip(
            "Read back readable registers: VAL_IN / PU / PD / DRV")
        self.reg_refresh_btn.clicked.connect(self._on_refresh_readable)
        bl.addWidget(self.reg_refresh_btn)
        lay.addWidget(bar)

        self._regmap_scroll = QScrollArea()
        self._regmap_scroll.setObjectName("gpioScroll")
        self._regmap_scroll.setWidgetResizable(True)
        self._regmap_scroll.setFrameShape(QFrame.NoFrame)
        self._regmap_container = QWidget()
        self._regmap_container.setObjectName("gpioViewPage")
        self._regmap_grid = QGridLayout(self._regmap_container)
        self._regmap_grid.setContentsMargins(2, 2, 2, 2)
        self._regmap_grid.setSpacing(6)
        self._regmap_placeholder = QLabel(
            "Load a DUT config to show the register map")
        self._regmap_placeholder.setObjectName("gpioStatus")
        self._regmap_placeholder.setAlignment(Qt.AlignCenter)
        self._regmap_grid.addWidget(self._regmap_placeholder, 0, 0)
        self._regmap_scroll.setWidget(self._regmap_container)
        lay.addWidget(self._regmap_scroll, 1)
        return page

    # 视图 3：I2C Bus Sniffer
    def _build_sniffer_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(4)
        self._sniff_chip_group = QButtonGroup(self)
        self._sniff_chip_group.setExclusive(True)
        all_btn = QPushButton("All")
        all_btn.setObjectName("gpioChip")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        self._sniff_chip_group.addButton(all_btn, -1)
        bar.addWidget(all_btn)
        for i, kind in enumerate(self.SNIFF_KINDS):
            btn = QPushButton(kind)
            btn.setObjectName("gpioChip")
            btn.setCheckable(True)
            self._sniff_chip_group.addButton(btn, i)
            bar.addWidget(btn)
        self._sniff_chip_group.idClicked.connect(self._on_sniff_kind_changed)

        bar.addSpacing(6)
        self.sniff_search = QLineEdit()
        self.sniff_search.setObjectName("gpioSearch")
        self.sniff_search.setPlaceholderText("Search address / semantic keyword")
        self.sniff_search.textChanged.connect(self._render_sniffer)
        bar.addWidget(self.sniff_search, 1)

        self.sniff_pause_btn = QPushButton("Pause")
        self.sniff_pause_btn.setObjectName("gpioBtn")
        self.sniff_pause_btn.setCheckable(True)
        self.sniff_pause_btn.setToolTip("Pause / resume auto-scroll refresh")
        self.sniff_pause_btn.toggled.connect(self._on_sniff_pause)
        bar.addWidget(self.sniff_pause_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("gpioBtn")
        clear_btn.setIcon(_icon("trash.svg", "#94A3B8", 12))
        clear_btn.clicked.connect(self._on_sniff_clear)
        bar.addWidget(clear_btn)

        export_btn = QPushButton("Export .log")
        export_btn.setObjectName("gpioBtn")
        export_btn.setIcon(_icon("download.svg", "#94A3B8", 12))
        export_btn.clicked.connect(self._on_sniff_export)
        bar.addWidget(export_btn)
        lay.addLayout(bar)

        self.sniff_view = QTextEdit()
        self.sniff_view.setObjectName("gpioSniff")
        self.sniff_view.setReadOnly(True)
        lay.addWidget(self.sniff_view, 1)
        return page

    # 视图 4：DUT JSON Config
    def _build_json_view(self):
        page = QWidget()
        page.setObjectName("gpioViewPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.json_file_label = QLabel("chips/gpio_configs/--.json")
        self.json_file_label.setObjectName("gpioMono")
        bar.addWidget(self.json_file_label)
        bar.addStretch(1)
        for text, slot, tip in (
            ("Import JSON", self._on_json_import,
             "Load chip JSON file from local disk"),
            ("Export JSON", self._on_json_export,
             "Export editor content to a JSON file"),
            ("Reload", self._on_json_reload,
             "Discard changes and reload current config from disk"),
            ("Apply Config", self._on_json_apply,
             "Validate and write back to chips/gpio_configs/, effective immediately"),
        ):
            btn = QPushButton(text)
            btn.setObjectName("gpioBtn")
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            bar.addWidget(btn)
        lay.addLayout(bar)

        self.json_err_label = QLabel("")
        self.json_err_label.setObjectName("gpioJsonErr")
        lay.addWidget(self.json_err_label)

        self.json_edit = QPlainTextEdit()
        self.json_edit.setObjectName("gpioMonoEdit")
        self.json_edit.setPlaceholderText(
            "DUT JSON config: gpio_banks base addresses / drv_sel / "
            "pull_up_bases / pull_down_bases ...")
        lay.addWidget(self.json_edit, 1)
        return page

    # 视图 5：DUT Confirmation Note
    def _build_notes_view(self):
        page = QScrollArea()
        page.setObjectName("gpioScroll")
        page.setWidgetResizable(True)
        page.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        container.setObjectName("gpioViewPage")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(6)

        self._note_status_labels = []
        self._note_bodies = []
        for i, title in enumerate((
            "1. PU / PD pull register addresses",
            "2. Drive strength levels and impedance (drv_sel)",
            "3. I2C 7-bit device address and width",
            "4. Communication bridge",
            "5. Pin function sel (mux as GPIO)",
        )):
            card = QFrame()
            card.setObjectName("noteCard")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(4)
            head = QHBoxLayout()
            t = QLabel(title)
            t.setObjectName("noteTitle")
            head.addWidget(t)
            head.addStretch(1)
            st = QLabel("--")
            st.setObjectName("noteStatus")
            head.addWidget(st)
            cl.addLayout(head)
            body = QLabel("-")
            body.setObjectName("noteBody")
            body.setWordWrap(True)
            cl.addWidget(body)
            lay.addWidget(card)
            self._note_status_labels.append(st)
            self._note_bodies.append(body)
        lay.addStretch(1)
        page.setWidget(container)
        return page

    # ================================================================ 状态访问
