#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test 主面板视图构建（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - _create_layout                   : 顶层布局（标题栏 / Config Import / 主体 splitter / 执行日志）
  - _create_connection_panel         : N6705C / Charger 连接面板
  - _create_firmware_panel           : 固件下载面板
  - _create_config_import_panel      : Config Import 面板（测试模式 + Chip + 5 电源 YAML）
  - _build_firmware_serial_widgets   : 固件串口控件组
  - _create_consumption_test_panel   : 功耗测试结果面板（结果卡片 + BIN 表 + Save DataLog）
  - _create_test_buttons_row         : Start / Auto 测试按钮行
  - _setup_bin_result_table          : BIN 结果表表头初始化
  - _add_bin_result_row              : 追加一行 BIN 结果

依赖宿主类（ConsumptionTestUI）提供其属性、信号槽方法（_on_device_search /
_download_to_dut / _export_bin_results_to_excel / _save_datalog 等）与其它 Mixin。
"""

import os

from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.progress_button import ProgressButton
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.pages.consumption_test.widgets import DownloadModeToggle, BinaryTextToggle
from ui.theme import Colors, FontSizes, Radius, Spacing, FONT_FAMILY, FONT_MONO
from chips.bes_chip_configs.bes_chip_configs import SUPPORTED_CHIPS
from ui.styles import SCROLLBAR_STYLE
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QPlainTextEdit,
    QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor


_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "consumption_test_SVGs"
)


class ConsumptionTestViewPanelsMixin:

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        icon_label = QLabel()
        icon_label.setPixmap(
            _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "zap.svg"), "#fbbf24", 22).pixmap(22, 22)
        )
        icon_label.setFixedSize(22, 22)
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.page_title = QLabel("Consumption Test")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("Measure average current consumption and manage DUT firmware/configuration.")
        self.page_subtitle.setObjectName("pageSubtitle")
        title_col.addWidget(self.page_title)
        title_col.addWidget(self.page_subtitle)
        header_layout.addWidget(icon_label, 0, Qt.AlignTop)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        # ---- 导入 / 导出 配置按钮(右上角) ----
        self.import_config_btn = QPushButton("Import Config")
        self.export_config_btn = QPushButton("Export Config")
        _io_btn_style = """
            QPushButton {
                background-color: #1a2750;
                color: #c8d8f8;
                border: 1px solid #22376a;
                border-radius: 6px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: 600;
                min-height: 24px;
                max-height: 28px;
            }
            QPushButton:hover { background-color: #243760; border: 1px solid #2f4a80; }
            QPushButton:pressed { background-color: #14203f; }
        """
        self.import_config_btn.setStyleSheet(_io_btn_style)
        self.export_config_btn.setStyleSheet(_io_btn_style)
        self.import_config_btn.setCursor(Qt.PointingHandCursor)
        self.export_config_btn.setCursor(Qt.PointingHandCursor)
        self.import_config_btn.setToolTip("Import test configuration from JSON file")
        self.export_config_btn.setToolTip("Export current test configuration to JSON file")
        self.import_config_btn.clicked.connect(self._import_config)
        self.export_config_btn.clicked.connect(self._export_config)
        header_layout.addWidget(self.import_config_btn, 0, Qt.AlignVCenter)
        header_layout.addWidget(self.export_config_btn, 0, Qt.AlignVCenter)

        main_layout.addLayout(header_layout)

        # ---- Config Import 面板(横跨顶部整个界面) ----
        main_layout.addWidget(self._create_config_import_panel())

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.addWidget(self._create_connection_panel())
        fw_panel = self._create_firmware_panel()
        left_column.addWidget(fw_panel)
        left_column.addWidget(self._create_test_config_panel())
        left_column.addStretch()

        left_inner = QWidget()
        left_inner.setStyleSheet("background: transparent; border: none;")
        left_inner.setLayout(left_column)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setFixedWidth(320)
        left_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
        """ + SCROLLBAR_STYLE)
        left_scroll.setWidget(left_inner)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(10)
        right_column.addWidget(self._create_channel_config_section())
        right_column.addWidget(self._create_test_buttons_row())
        right_column.addWidget(self._create_consumption_test_panel(), 1)

        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent; border: none;")
        right_widget.setLayout(right_column)

        body_layout.addWidget(left_scroll)
        body_layout.addWidget(right_widget, 1)

        body_widget = QWidget()
        body_widget.setStyleSheet("background: transparent; border: none;")
        body_widget.setLayout(body_layout)

        splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            body_widget, show_progress=False, stretch=(1, 0),
            sizes=[600, 120], min_log_height=40,
        )
        self.log_edit = self.execution_logs.log_edit
        self.clear_log_btn = self.execution_logs.clear_log_btn

        main_layout.addWidget(splitter, 1)

        # 首次打开自动搜索一次 MCU 串口
        QTimer.singleShot(0, self._on_mcu_search)

    def _create_connection_panel(self):
        panel = QFrame()
        panel.setObjectName("connectionPanel")
        panel.setStyleSheet("""
            QFrame#connectionPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self._n6705c_conn_widgets = {}
        _default_resources = {
            "B": "TCPIP0::K-N6705C-03845.local::hislip0::INSTR",
        }
        _tag_colors = {"A": "#00f5c4", "B": "#f2994a"}
        _border_colors = {"A": "#18284d", "B": "#18284d"}

        for label in ("A", "B"):
            tag_color = _tag_colors.get(label, "#00f5c4")
            border_color = _border_colors.get(label, "#18284d")
            default_res = _default_resources.get(label, "")

            sub_frame = QFrame()
            sub_frame.setObjectName(f"connSub{label}")
            sub_frame.setStyleSheet(f"""
                QFrame#connSub{label} {{
                    background-color: #0d1a38;
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            sub_layout = QVBoxLayout(sub_frame)
            sub_layout.setContentsMargins(8, 6, 8, 6)
            sub_layout.setSpacing(6)

            header = QHBoxLayout()
            header.setSpacing(4)
            header.setContentsMargins(0, 2, 0, 0)
            tag = QLabel(f"N6705C {label}")
            tag.setStyleSheet(
                f"color: {tag_color}; font-weight: 700; font-size: 11px;"
                " background: transparent; border: none;"
            )
            status_label = QLabel("● Disconnected")
            status_label.setStyleSheet(
                "color: #8ea6cf; font-size: 10px; font-weight: bold;"
                " background: transparent; border: none;"
            )
            header.addWidget(tag)
            header.addStretch()
            header.addWidget(status_label)
            sub_layout.addLayout(header)

            visa_combo = DarkComboBox(bg="#091426", border="#17345f")
            visa_combo.setSizeAdjustPolicy(
                DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            visa_combo.setMinimumContentsLength(10)
            visa_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            visa_combo.setFixedHeight(24)
            font = visa_combo.font()
            font.setPixelSize(10)
            visa_combo.setFont(font)
            visa_combo.addItem(default_res if default_res else "TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
            sub_layout.addWidget(visa_combo)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(6)
            btn_row.setContentsMargins(0, 2, 0, 0)
            _btn_h = 24
            _btn_height_fix = f"QPushButton {{ min-height: {_btn_h}px; max-height: {_btn_h}px; }}"
            search_btn = SpinningSearchButton(parent=sub_frame)
            search_btn.setFixedHeight(_btn_h)
            search_btn.setStyleSheet(search_btn.styleSheet() + _btn_height_fix)
            connect_btn = QPushButton()
            connect_btn.setFixedHeight(_btn_h)
            update_connect_button_state(connect_btn, connected=False)
            connect_btn.setStyleSheet(connect_btn.styleSheet() + _btn_height_fix)
            btn_row.addWidget(search_btn)
            btn_row.addWidget(connect_btn)
            sub_layout.addLayout(btn_row)

            layout.addWidget(sub_frame)

            widgets = {
                "tag": tag,
                "status": status_label,
                "combo": visa_combo,
                "search_btn": search_btn,
                "connect_btn": connect_btn,
            }
            self._n6705c_conn_widgets[label] = widgets
            search_btn.clicked.connect(lambda checked=False, lbl=label: self._on_device_search(lbl))
            connect_btn.clicked.connect(lambda checked=False, lbl=label: self._on_device_connect_or_disconnect(lbl))

        return panel

    def _create_firmware_panel(self):
        fw_panel = QFrame()
        fw_panel.setObjectName("fwPanel")
        fw_panel.setStyleSheet("""
            QFrame#fwPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        fw_layout = QVBoxLayout(fw_panel)
        fw_layout.setContentsMargins(12, 10, 12, 10)
        fw_layout.setSpacing(6)

        fw_title = QLabel("Firmware Download")
        fw_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
        fw_layout.addWidget(fw_title)

        self._build_firmware_serial_widgets(fw_layout)
        self.bind_serial_signals()

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_label = QLabel("Mode")
        mode_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.download_mode_toggle = DownloadModeToggle()
        self.download_mode_toggle.setFixedWidth(140)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.download_mode_toggle)
        mode_row.addStretch()
        fw_layout.addLayout(mode_row)

        fw_file_row = QHBoxLayout()
        fw_file_row.setSpacing(4)
        self.firmware_file_input = QLineEdit("No file selected...")
        self.firmware_file_input.setReadOnly(True)
        self.firmware_file_input.setStyleSheet("""
            QLineEdit {
                background-color: #020816;
                border: 1px solid #1c2f54;
                border-radius: 6px;
                padding: 4px 6px;
                color: #d7e3ff;
                min-height: 28px;
                font-size: 10px;
            }
        """)
        self.firmware_browse_btn = QPushButton("...")
        self.firmware_browse_btn.setFixedWidth(36)
        self.firmware_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d45ff;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #6d55ff; }
        """)
        fw_file_row.addWidget(self.firmware_file_input, 1)
        fw_file_row.addWidget(self.firmware_browse_btn)
        fw_layout.addLayout(fw_file_row)

        self.download_btn = ProgressButton()
        fw_layout.addWidget(self.download_btn)

        self.firmware_browse_btn.clicked.connect(self._browse_firmware)
        self.download_btn.clicked.connect(self._download_to_dut)
        self.download_btn.stop_clicked.connect(self._stop_download)

        return fw_panel

    # 5 个电源轨名称(顺序决定 UI 从左到右排列)
    _RAIL_NAMES = ["Vcore", "VcoreM", "VcoreL", "VANA", "VHPPA"]

    def _create_config_import_panel(self):
        """Config Import 面板(横跨顶部整个界面)。

        顶行: 测试模式切换(外供高压/标准电压) + Chip 下拉 + Check 按钮
        中部: 5 个独立电源轨列(Vcore/VcoreM/VcoreL/VANA/VHPPA)
              每列含 YAML 文本框 + 该轨独立的 Import/Exec 按钮
        """
        panel = QFrame()
        panel.setObjectName("configPanel")
        panel.setStyleSheet("""
            QFrame#configPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # ---- 顶行: 标题 + 测试模式 + Chip + Check ----
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        config_icon_label = QLabel()
        config_icon_label.setPixmap(
            _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "file-json.svg"), "#94a3b8", 16).pixmap(16, 16)
        )
        config_icon_label.setFixedSize(16, 16)
        config_title = QLabel("Config Import")
        config_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
        top_row.addWidget(config_icon_label)
        top_row.addWidget(config_title)

        # 测试模式切换: 外供高压(high_voltage) / 标准电压(standard)
        # 外供高压 → Channel Config 显示 Force Vol 控件, 跳过 I2C 配置
        # 标准电压 → 隐藏 Force Vol 控件, 走 I2C 配置流程
        self.test_mode_toggle = BinaryTextToggle(
            left_key="high_voltage", left_label="High V",
            right_key="standard", right_label="Std V",
            initial="high_voltage",
            fixed_height=24, fixed_width=150,
        )
        self.test_mode_toggle.setToolTip(
            "Test Mode:\n"
            "  · High V (外供高压): Channel Config 显示 Force Vol 控件;\n"
            "    Auto Test 跳过 I2C 配置, 直接走 Force Vol 参数。\n"
            "  · Std V (标准电压): 隐藏 Force Vol 控件;\n"
            "    Auto Test 走 I2C 配置流程, 按通道 Name 匹配对应电源配置。"
        )
        top_row.addWidget(self.test_mode_toggle)

        chip_label = QLabel("Chip")
        chip_label.setStyleSheet(
            "font-size: 10px; color: #7e96bf; background: transparent; border: none;"
        )
        top_row.addWidget(chip_label)

        self.chip_combo = DarkComboBox()
        self.chip_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.chip_combo.setMinimumContentsLength(12)
        self.chip_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.chip_combo.setFixedHeight(22)
        font = self.chip_combo.font()
        font.setPixelSize(11)
        self.chip_combo.setFont(font)
        self.chip_combo.addItem("-- Select Chip --")
        for chip_name in SUPPORTED_CHIPS:
            self.chip_combo.addItem(chip_name)
        top_row.addWidget(self.chip_combo, 1)

        self.chip_check_btn = QPushButton("Check")
        self.chip_check_btn.setFixedWidth(60)
        self.chip_check_btn.setFixedHeight(22)
        font_btn = self.chip_check_btn.font()
        font_btn.setPixelSize(11)
        self.chip_check_btn.setFont(font_btn)
        self.chip_check_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-weight: 600;
                min-height: 0px;
                padding: 2px 8px;
            }
            QPushButton:hover { background-color: #1c315b; }
            QPushButton:disabled {
                background-color: #0f1930;
                color: #5a6b8e;
                border: 1px solid #1b2847;
            }
        """)
        top_row.addWidget(self.chip_check_btn)

        layout.addLayout(top_row)

        # ---- 中部: 5 个电源轨列(横向排列), 每列含 YAML 文本框 + Import/Exec 按钮 ----
        rails_row = QHBoxLayout()
        rails_row.setSpacing(6)
        self._rail_config_edits = {}
        self._rail_import_btns = {}
        self._rail_exec_btns = {}

        _upload_svg = os.path.join(_PAGE_SVGS_DIR, "upload.svg")
        _exec_svg = os.path.join(_PAGE_SVGS_DIR, "settings.svg")

        for rail in self._RAIL_NAMES:
            col = QVBoxLayout()
            col.setSpacing(2)

            rail_label = QLabel(rail)
            rail_label.setStyleSheet(
                "font-size: 10px; color: #7e96bf; background: transparent; border: none;"
            )
            col.addWidget(rail_label)

            edit = QPlainTextEdit()
            edit.setPlaceholderText(f"{rail} config...")
            edit.setMinimumHeight(70)
            edit.setMaximumHeight(110)
            edit.setStyleSheet("""
                QPlainTextEdit {
                    background-color: #0d1b3e;
                    color: #dbe7ff;
                    border: 1px solid #25355c;
                    border-radius: 6px;
                    font-family: Consolas, monospace;
                    font-size: 10px;
                    padding: 4px;
                }
                QPlainTextEdit:focus {
                    border: 1px solid #5d45ff;
                }
            """)
            col.addWidget(edit, 1)
            self._rail_config_edits[rail] = edit

            # 每轨独立的 Import / Exec 按钮
            rail_btn_row = QHBoxLayout()
            rail_btn_row.setSpacing(3)
            rail_btn_row.setContentsMargins(0, 0, 0, 0)

            import_btn = QPushButton("Import")
            if os.path.isfile(_upload_svg):
                import_btn.setIcon(_tinted_svg_icon(_upload_svg, "#dbe7ff", 12))
                import_btn.setIconSize(QSize(12, 12))
            import_btn.setStyleSheet("""
                QPushButton {
                    background-color: #162544;
                    color: #dbe7ff;
                    border: 1px solid #25355c;
                    border-radius: 6px;
                    font-weight: 600;
                    min-height: 22px;
                    font-size: 10px;
                    padding: 2px 4px;
                }
                QPushButton:hover { background-color: #1c315b; }
                QPushButton:disabled {
                    background-color: #0f1930;
                    color: #5a6b8e;
                    border: 1px solid #1b2847;
                }
            """)
            rail_btn_row.addWidget(import_btn, 1)
            self._rail_import_btns[rail] = import_btn

            exec_btn = QPushButton("Exec")
            if os.path.isfile(_exec_svg):
                exec_btn.setIcon(_tinted_svg_icon(_exec_svg, "#ffffff", 12))
                exec_btn.setIconSize(QSize(12, 12))
            exec_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5d45ff;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    font-weight: 600;
                    min-height: 22px;
                    font-size: 10px;
                    padding: 2px 4px;
                }
                QPushButton:hover { background-color: #6d55ff; }
                QPushButton:disabled {
                    background-color: #0f1930;
                    color: #5a6b8e;
                    border: 1px solid #1b2847;
                }
            """)
            rail_btn_row.addWidget(exec_btn, 1)
            self._rail_exec_btns[rail] = exec_btn

            col.addLayout(rail_btn_row)

            col_w = QWidget()
            col_w.setLayout(col)
            rails_row.addWidget(col_w, 1)
        layout.addLayout(rails_row)

        # 信号连接
        self.chip_combo.currentIndexChanged.connect(self._on_chip_selected)
        self.chip_check_btn.clicked.connect(self._on_chip_check)
        # 每轨的 Import / Exec 连接到带 rail 参数的处理函数
        for rail in self._RAIL_NAMES:
            self._rail_import_btns[rail].clicked.connect(
                lambda _checked=False, r=rail: self._import_rail_configuration(r)
            )
            self._rail_exec_btns[rail].clicked.connect(
                lambda _checked=False, r=rail: self._execute_rail_configuration(r)
            )
        self.test_mode_toggle.toggled.connect(self._on_test_mode_changed)

        # 初始化测试模式状态(外供高压为默认)
        self._test_mode = "high_voltage"
        self._on_test_mode_changed(self._test_mode)

        return panel

    def _build_firmware_serial_widgets(self, layout):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setContentsMargins(0, 0, 0, 0)

        self.serial_label = QLabel("COM:")
        self.serial_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        row.addWidget(self.serial_label)

        self.serial_combo = DarkComboBox()
        self.serial_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.serial_combo.setMinimumContentsLength(10)
        self.serial_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.serial_combo.setFixedHeight(22)
        font = self.serial_combo.font()
        font.setPixelSize(12)
        self.serial_combo.setFont(font)
        row.addWidget(self.serial_combo, 1)

        self.serial_search_btn = SpinningSearchButton(parent=self, icon_size=12)
        self.serial_search_btn.setFixedSize(22, 22)
        row.addWidget(self.serial_search_btn)

        layout.addLayout(row)

    def _create_consumption_test_panel(self):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("consumptionPanel")
        panel.setStyleSheet("""
            QFrame#consumptionPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        self._consumption_panel = panel
        wrapper_layout.addWidget(panel)

        self._disabled_overlay = QWidget(wrapper)
        self._disabled_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(5, 11, 26, 180);
                border-radius: 12px;
            }
        """)
        self._disabled_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        overlay_layout = QVBoxLayout(self._disabled_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_hint = QLabel("Please connect N6705C first")
        overlay_hint.setAlignment(Qt.AlignCenter)
        overlay_hint.setStyleSheet("""
            QLabel {
                color: #5a6b8e;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        overlay_layout.addWidget(overlay_hint)
        self._disabled_overlay.raise_()
        self._disabled_overlay.show()

        def _resize_overlay(event):
            self._disabled_overlay.setGeometry(panel.geometry())
        wrapper.resizeEvent = _resize_overlay
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.result_cards_container = QWidget()
        self.result_cards_container.setStyleSheet("background: transparent; border: none;")
        self.result_cards_layout = QHBoxLayout(self.result_cards_container)
        self.result_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.result_cards_layout.setSpacing(10)
        self.channel_cards = {}
        layout.addWidget(self.result_cards_container, 0)

        # ---- BIN 结果表头部工具条:左侧标题 + 右侧 Export ----
        bin_header_row = QHBoxLayout()
        bin_header_row.setContentsMargins(0, 0, 0, 0)
        bin_header_row.setSpacing(8)

        self._bin_result_title = QLabel("BIN RESULTS")
        self._bin_result_title.setStyleSheet("""
            QLabel {
                color: #8eb0e3;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }
        """)
        bin_header_row.addWidget(self._bin_result_title, 0, Qt.AlignLeft)
        bin_header_row.addStretch(1)

        self.export_bin_result_btn = QPushButton("⤓ Export")
        self.export_bin_result_btn.setToolTip("Export current BIN results to an Excel (.xlsx) file")
        self.export_bin_result_btn.setCursor(Qt.PointingHandCursor)
        self.export_bin_result_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-size: 11px;
                padding: 3px 12px;
                min-height: 24px;
            }
            QPushButton:hover { background-color: #1c315b; }
            QPushButton:disabled {
                color: #4a5a7a;
                background-color: #0d1830;
                border-color: #1a2a48;
            }
        """)
        self.export_bin_result_btn.clicked.connect(self._export_bin_results_to_excel)
        bin_header_row.addWidget(self.export_bin_result_btn, 0, Qt.AlignRight)

        # 头部工具条作为独立容器,以便与 bin_result_table 一起控制显隐
        self._bin_result_header = QWidget()
        self._bin_result_header.setStyleSheet("background: transparent; border: none;")
        self._bin_result_header.setLayout(bin_header_row)
        self._bin_result_header.hide()
        layout.addWidget(self._bin_result_header, 0)

        self.bin_result_table = QTableWidget(0, 0)
        self.bin_result_table.setObjectName("binResultTable")
        self.bin_result_table.setStyleSheet("""
            QTableWidget#binResultTable {
                background-color: #060e22;
                border: 1px solid #1a2d57;
                border-radius: 8px;
                gridline-color: #15284f;
                color: #dbe7ff;
                font-size: 11px;
            }
            QTableWidget#binResultTable QHeaderView::section {
                background-color: #0b1630;
                color: #8eb0e3;
                border: none;
                border-bottom: 1px solid #1a2d57;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QTableWidget#binResultTable::item {
                padding: 4px 8px;
                border-bottom: 1px solid #102448;
            }
        """)
        self.bin_result_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.bin_result_table.verticalHeader().setVisible(False)
        self.bin_result_table.setAlternatingRowColors(False)
        self.bin_result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bin_result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bin_result_table.setShowGrid(False)
        self.bin_result_table.hide()
        layout.addWidget(self.bin_result_table, 1)

        self.save_datalog_btn = QPushButton("Save DataLog")
        _save_svg = os.path.join(_PAGE_SVGS_DIR, "save.svg")
        if os.path.isfile(_save_svg):
            self.save_datalog_btn.setIcon(_tinted_svg_icon(_save_svg, "#dbe7ff", 16))
            self.save_datalog_btn.setIconSize(QSize(16, 16))
        self.save_datalog_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 10px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #1c315b; }
        """)

        self.save_datalog_btn.clicked.connect(self._save_datalog)

        return wrapper

    def _create_test_buttons_row(self):
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background: transparent; border: none;")
        btn_row = QHBoxLayout(btn_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        start_test_style = {
            "bg": "#0d6b4f",
            "border": "#18a87a",
            "text_color": "#ffffff",
            "progress_color": (24, 168, 122, 60),
            "complete_bg": (13, 107, 79, 80),
            "complete_text_color": "#4ade80",
            "failed_bg": "#2a0f1a",
            "failed_border": "#6b2040",
            "failed_text_color": "#ff7593",
            "waiting_text_color": "#a0b4d8",
            "spinner_color": (24, 168, 122, 200),
            "separator_color": "#18a87a",
            "stop_color_normal": "#8a9bbe",
            "stop_color_hover": "#ff5a5a",
            "min_height": 36,
        }
        self.start_test_btn = ProgressButton(
            idle_text="▶ START TEST",
            waiting_text="Preparing...",
            programming_text="Testing",
            complete_text="✓  Test complete",
            failed_text="Test failed",
            icon_path=os.path.join(_PAGE_SVGS_DIR, "zap.svg"),
            style_overrides=start_test_style,
        )
        self.start_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        auto_test_style = {
            "bg": "#162544",
            "border": "#25355c",
            "text_color": "#dbe7ff",
            "progress_color": (93, 69, 255, 60),
            "complete_bg": (13, 107, 79, 80),
            "complete_text_color": "#4ade80",
            "failed_bg": "#2a0f1a",
            "failed_border": "#6b2040",
            "failed_text_color": "#ff7593",
            "waiting_text_color": "#a0b4d8",
            "spinner_color": (93, 69, 255, 200),
            "separator_color": "#25355c",
            "stop_color_normal": "#8a9bbe",
            "stop_color_hover": "#ff5a5a",
            "min_height": 36,
        }
        self.auto_test_btn = ProgressButton(
            idle_text="Auto Test",
            waiting_text="Preparing...",
            programming_text="Auto Testing",
            complete_text="✓  Auto test done",
            failed_text="Auto test failed",
            icon_path=os.path.join(_PAGE_SVGS_DIR, "activity.svg"),
            style_overrides=auto_test_style,
        )
        self.auto_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btn_row.addWidget(self.start_test_btn, 1)
        btn_row.addWidget(self.auto_test_btn, 1)

        self.start_test_btn.clicked.connect(self._on_start_test)
        self.start_test_btn.stop_clicked.connect(self._stop_test)
        self.auto_test_btn.clicked.connect(self._on_auto_test)
        self.auto_test_btn.stop_clicked.connect(self._stop_auto_test)

        return btn_widget

    def _setup_bin_result_table(self):
        self._bin_results_data = []
        self.bin_result_table.setRowCount(0)

        headers = ["BIN", "Voltage"]
        for i, cfg in enumerate(self._channel_configs):
            if cfg["enabled"]:
                headers.append(cfg["name"])
        has_sub = any(
            cfg["enabled"] and not cfg["name"].lower().startswith("vbat")
            for cfg in self._channel_configs
        )
        if has_sub:
            headers.append("Vbat_remain")

        self.bin_result_table.setColumnCount(len(headers))
        self.bin_result_table.setHorizontalHeaderLabels(headers)
        self.bin_result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bin_result_table.show()
        if hasattr(self, "_bin_result_header"):
            self._bin_result_header.show()

    def _add_bin_result_row(self, summary):
        row = self.bin_result_table.rowCount()
        self.bin_result_table.insertRow(row)

        bin_name = summary.get("bin_name", f"BIN-{row + 1}")
        col = 0
        bin_item = QTableWidgetItem(bin_name)
        bin_item.setTextAlignment(Qt.AlignCenter)
        bin_item.setForeground(QColor("#eaf2ff"))
        self.bin_result_table.setItem(row, col, bin_item)
        col += 1

        channel_voltages = summary.get("channel_voltages", {})
        v_parts = []
        for i, cfg in enumerate(self._channel_configs):
            if not cfg["enabled"]:
                continue
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            key = (device_label, hw_ch)
            v = channel_voltages.get(key)
            v_parts.append(f"{v:.4g}" if v is not None else "N/A")
        voltage_text = " | ".join(v_parts) if v_parts else "- - -"
        voltage_item = QTableWidgetItem(voltage_text)
        voltage_item.setTextAlignment(Qt.AlignCenter)
        voltage_item.setForeground(QColor("#8899bb"))
        self.bin_result_table.setItem(row, col, voltage_item)
        col += 1

        channels = summary.get("channels", {})
        vbat_current = summary.get("vbat")

        for i, cfg in enumerate(self._channel_configs):
            if not cfg["enabled"]:
                continue
            if cfg["name"].lower().startswith("vbat") and vbat_current is not None:
                val_text = self._format_current(vbat_current)
            else:
                device_label, hw_ch = self._parse_channel_key(cfg["channel"])
                key = (device_label, hw_ch)
                val = channels.get(key)
                val_text = self._format_current(val) if val is not None else "- - -"
            colors = self.CHANNEL_COLORS_LIST[i % len(self.CHANNEL_COLORS_LIST)]
            item = QTableWidgetItem(val_text)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(colors["accent"]))
            self.bin_result_table.setItem(row, col, item)
            col += 1

        has_sub = any(
            cfg["enabled"] and not cfg["name"].lower().startswith("vbat")
            for cfg in self._channel_configs
        )
        if has_sub:
            vbat_remain = summary.get("vbat_remain")
            remain_text = self._format_current(vbat_remain) if vbat_remain is not None else "- - -"
            remain_item = QTableWidgetItem(remain_text)
            remain_item.setTextAlignment(Qt.AlignCenter)
            remain_item.setForeground(QColor("#a0a0a0"))
            self.bin_result_table.setItem(row, col, remain_item)

        self.bin_result_table.scrollToBottom()
