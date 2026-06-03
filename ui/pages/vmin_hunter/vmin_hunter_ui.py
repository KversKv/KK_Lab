#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VminHunter UI 页面

用于探测芯片能稳定工作的最低电压边界 (Vmin)。
布局参考 Consumption Test：
- 左侧配置列：设备连接 / Test Config / Channel Config
- 右侧监控区：电压点遍历结果表 + 死机记录
- 底部 Execution Logs (UART 日志 / 死机检测)

注意：本页面仅实现 UI 与交互层；真正的遍历引擎、校准、死机判定与恢复
属于 core 层编排，应通过 QThread + Signal/Slot 异步执行，UI 层不得阻塞 IO。
"""

import os
import json

from ui.resource_path import get_resource_base

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QFrame, QCheckBox,
    QScrollArea, QFileDialog,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import ChamberConnectionMixin
from ui.modules.serialCom_module.serialCom_module_frame import (
    SerialComMixin, MODE_FULL,
)
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.widgets.dark_combobox import DarkComboBox
from ui.styles import get_page_base_qss, SCROLLBAR_STYLE
from ui.theme import Colors, Radius
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from log_config import get_logger

logger = get_logger(__name__)


_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "vmin_hunter_SVGs"
)

_TEST_MODES = [
    ("internal", "Internal Voltage (IIC)"),
    ("external", "External Supply (N6705C)"),
]


class VminHunterUI(N6705CConnectionMixin, ChamberConnectionMixin, SerialComMixin, QWidget):
    """Vmin 探底测试页面。

    多继承 N6705CConnectionMixin / ChamberConnectionMixin / SerialComMixin
    复用仪器连接逻辑，与 GPADC / Consumption Test 保持一致的连接交互。
    """

    def __init__(self, n6705c_top=None, instrument_manager=None, parent=None):
        QWidget.__init__(self, parent)
        self.init_n6705c_connection(
            n6705c_top=n6705c_top,
            instrument_manager=instrument_manager,
        )
        self.init_chamber_connection(instrument_manager=instrument_manager)
        self.init_serial_connection(mode=MODE_FULL, baudrate=921600, prefix="DUT")

        self._vcorel_enabled = False
        self._temp_enabled = False

        self._setup_style()
        self._create_layout()
        self._bind_signals()

        self.sync_n6705c_from_top()

    # ------------------------------------------------------------------
    # 样式
    # ------------------------------------------------------------------
    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setObjectName("VminHunterRoot")
        cb_icons = self._get_checkmark_path("5d45ff")
        page_extra = f"""
        QWidget#VminHunterRoot {{
            background-color: {Colors.bg_secondary};
        }}

        QFrame#vhPanel {{
            background-color: {Colors.bg_card};
            border: 1px solid {Colors.border_primary};
            border-radius: {Radius.card}px;
        }}

        QFrame#vhSubCard {{
            background-color: {Colors.bg_panel};
            border: 1px solid {Colors.border_secondary};
            border-radius: {Radius.widget}px;
        }}

        QLineEdit {{
            background-color: #0a1733;
            color: #eaf2ff;
            border: 1px solid #27406f;
            border-radius: 8px;
            padding: 6px 10px;
            min-height: 22px;
            selection-background-color: #4f46e5;
        }}

        QLineEdit:hover {{
            border: 1px solid #3c5fa1;
        }}

        QLineEdit:focus {{
            border: 1px solid #4cc9f0;
            background-color: #0d1f42;
        }}

        QLineEdit:disabled {{
            background-color: {Colors.disabled_bg};
            border: 1px solid {Colors.disabled_border};
            color: {Colors.disabled_text};
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            image: url("__UNCHECKED__");
        }}

        QCheckBox::indicator:checked {{
            image: url("__CHECKED__");
        }}
        """.replace("__UNCHECKED__", cb_icons["unchecked"]).replace("__CHECKED__", cb_icons["checked"])
        self.setStyleSheet(get_page_base_qss() + page_extra)

    def _get_checkmark_path(self, accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(get_resource_base(), "resources", "icons")
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        main_layout.addLayout(self._create_header())

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.addWidget(self._create_connection_panel())
        left_column.addWidget(self._create_test_config_panel())
        left_column.addStretch()

        left_inner = QWidget()
        left_inner.setObjectName("vhLeftInner")
        left_inner.setStyleSheet(
            "QWidget#vhLeftInner { background: transparent; border: none; }"
        )
        left_inner.setLayout(left_column)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setFixedWidth(340)
        left_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }" + SCROLLBAR_STYLE
        )
        left_scroll.setWidget(left_inner)

        right_column = QVBoxLayout()
        right_column.setContentsMargins(0, 0, 0, 0)
        right_column.setSpacing(10)
        right_column.addWidget(self._create_channel_config_panel())
        right_column.addWidget(self._create_action_row())
        right_column.addWidget(self._create_result_panel(), 1)

        right_widget = QWidget()
        right_widget.setObjectName("vhRightWidget")
        right_widget.setStyleSheet(
            "QWidget#vhRightWidget { background: transparent; border: none; }"
        )
        right_widget.setLayout(right_column)

        body_layout.addWidget(left_scroll)
        body_layout.addWidget(right_widget, 1)

        body_widget = QWidget()
        body_widget.setObjectName("vhBodyWidget")
        body_widget.setStyleSheet(
            "QWidget#vhBodyWidget { background: transparent; border: none; }"
        )
        body_widget.setLayout(body_layout)

        splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            body_widget, show_progress=True, stretch=(1, 0), sizes=[600, 140]
        )
        self.log_edit = self.execution_logs.log_edit

        main_layout.addWidget(splitter, 1)

    def _create_header(self):
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(
            _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "crosshair.svg"), "#fbbf24", 22).pixmap(22, 22)
        )
        icon_label.setFixedSize(22, 22)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.page_title = QLabel("VminHunter")
        self.page_title.setObjectName("pageTitle")
        self.page_subtitle = QLabel("Hunt the lowest stable operating voltage (Vmin) of the chip.")
        self.page_subtitle.setObjectName("pageSubtitle")
        title_col.addWidget(self.page_title)
        title_col.addWidget(self.page_subtitle)

        header_layout.addWidget(icon_label, 0, Qt.AlignTop)
        header_layout.addLayout(title_col)
        header_layout.addStretch()

        self.import_config_btn = QPushButton("Import Config")
        self.export_config_btn = QPushButton("Export Config")
        io_btn_style = """
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
        for btn, tip in (
            (self.import_config_btn, "Import VminHunter configuration from JSON file"),
            (self.export_config_btn, "Export current VminHunter configuration to JSON file"),
        ):
            btn.setStyleSheet(io_btn_style)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            header_layout.addWidget(btn, 0, Qt.AlignVCenter)

        return header_layout

    # ------------------------------------------------------------------
    # 连接面板
    # ------------------------------------------------------------------
    def _create_connection_panel(self):
        panel = QFrame()
        panel.setObjectName("vhPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        layout.addLayout(self._section_title("settings.svg", "Device Connection", "#7da2d6"))

        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        tag = QLabel("N6705C")
        tag.setStyleSheet(
            "color: #00f5c4; font-weight: 700; font-size: 11px;"
            " background: transparent; border: none;"
        )
        title_row.addWidget(tag)
        title_row.addStretch()
        layout.addLayout(title_row)

        self.build_n6705c_connection_widgets(layout, title_row=title_row)

        uart_card = QFrame()
        uart_card.setObjectName("vhSubCard")
        uart_layout = QVBoxLayout(uart_card)
        uart_layout.setContentsMargins(8, 6, 8, 6)
        uart_layout.setSpacing(6)

        uart_header = QHBoxLayout()
        uart_tag = QLabel("UART (DUT Log) @ 921600")
        uart_tag.setStyleSheet(
            "color: #f2994a; font-weight: 700; font-size: 11px;"
            " background: transparent; border: none;"
        )
        uart_header.addWidget(uart_tag)
        uart_header.addStretch()
        uart_layout.addLayout(uart_header)

        self.build_serial_connection_widgets(uart_layout)

        layout.addWidget(uart_card)

        self.chamber_card = QFrame()
        self.chamber_card.setObjectName("vhSubCard")
        chamber_layout = QVBoxLayout(self.chamber_card)
        chamber_layout.setContentsMargins(8, 6, 8, 6)
        chamber_layout.setSpacing(6)

        chamber_header = QHBoxLayout()
        chamber_tag = QLabel("Chamber")
        chamber_tag.setStyleSheet(
            "color: #5b9cf5; font-weight: 700; font-size: 11px;"
            " background: transparent; border: none;"
        )
        chamber_header.addWidget(chamber_tag)
        chamber_header.addStretch()
        chamber_layout.addLayout(chamber_header)

        self.build_chamber_connection_widgets(chamber_layout)

        layout.addWidget(self.chamber_card)
        self.chamber_card.setVisible(False)
        return panel

    # ------------------------------------------------------------------
    # Test Config 面板
    # ------------------------------------------------------------------
    def _create_test_config_panel(self):
        panel = QFrame()
        panel.setObjectName("vhPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        layout.addLayout(self._section_title("activity.svg", "Test Config", "#5b9cf5"))

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)

        form.addWidget(self._field_label("Test CNT"), 0, 0)
        self.test_cnt_input = QLineEdit("100")
        self.test_cnt_input.setToolTip("Number of test iterations per condition")
        form.addWidget(self.test_cnt_input, 0, 1)

        form.addWidget(self._field_label("Test Mode"), 1, 0)
        self.test_mode_combo = DarkComboBox(bg="#091426", border="#17345f")
        for key, label in _TEST_MODES:
            self.test_mode_combo.addItem(label, key)
        form.addWidget(self.test_mode_combo, 1, 1)

        layout.addLayout(form)

        # ---- 温度控制 ----
        temp_row = QHBoxLayout()
        temp_row.setSpacing(6)
        self.temp_enable_cb = QCheckBox("Temperature Control")
        self.temp_enable_cb.setStyleSheet("color: #dbe7ff; font-size: 11px; font-weight: 600;")
        temp_row.addWidget(self.temp_enable_cb)
        temp_row.addStretch()
        layout.addLayout(temp_row)

        self.temp_points_input = QLineEdit("-40, 25, 85")
        self.temp_points_input.setToolTip("Temperature points (°C), comma separated")
        self.temp_points_input.setEnabled(False)
        layout.addWidget(self._labeled("Temp Points (°C)", self.temp_points_input))

        # ---- 监测通道 ----
        ch_title = QLabel("Monitor Channels")
        ch_title.setObjectName("fieldLabel")
        layout.addWidget(ch_title)

        ch_row = QHBoxLayout()
        ch_row.setSpacing(12)
        self.vcorem_cb = QCheckBox("VcoreM (required)")
        self.vcorem_cb.setChecked(True)
        self.vcorem_cb.setEnabled(False)
        self.vcorem_cb.setStyleSheet("color: #dbe7ff; font-size: 11px; font-weight: 600;")
        self.vcorel_cb = QCheckBox("VcoreL (optional)")
        self.vcorel_cb.setStyleSheet("color: #dbe7ff; font-size: 11px; font-weight: 600;")
        ch_row.addWidget(self.vcorem_cb)
        ch_row.addWidget(self.vcorel_cb)
        ch_row.addStretch()
        layout.addLayout(ch_row)

        # ---- 电压扫描区间 (Start / End / Step) ----
        vp_title = QLabel("Voltage Sweep")
        vp_title.setObjectName("fieldLabel")
        layout.addWidget(vp_title)

        vp_grid = QGridLayout()
        vp_grid.setHorizontalSpacing(8)
        vp_grid.setVerticalSpacing(4)

        self.voltage_start_input = QLineEdit("0.80")
        self.voltage_start_input.setToolTip("Sweep start voltage (V), typically the higher voltage")
        self.voltage_end_input = QLineEdit("0.60")
        self.voltage_end_input.setToolTip("Sweep end voltage (V), typically the lower voltage")
        self.voltage_step_input = QLineEdit("0.05")
        self.voltage_step_input.setToolTip("Sweep step (V), positive value; sweep direction is from Start to End")

        vp_grid.addWidget(self._field_label("Start (V)"), 0, 0)
        vp_grid.addWidget(self._field_label("End (V)"), 0, 1)
        vp_grid.addWidget(self._field_label("Step (V)"), 0, 2)
        vp_grid.addWidget(self.voltage_start_input, 1, 0)
        vp_grid.addWidget(self.voltage_end_input, 1, 1)
        vp_grid.addWidget(self.voltage_step_input, 1, 2)
        layout.addLayout(vp_grid)

        return panel

    # ------------------------------------------------------------------
    # Channel Config 面板 (IIC 控制字)
    # ------------------------------------------------------------------
    def _create_channel_config_panel(self):
        panel = QFrame()
        panel.setObjectName("vhPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        layout.addLayout(self._section_title("settings.svg", "Channel Config", "#15d1a3"))

        n6705c_row = QGridLayout()
        n6705c_row.setHorizontalSpacing(8)
        n6705c_row.setVerticalSpacing(6)
        n6705c_row.addWidget(self._field_label("VcoreM Ch"), 0, 0)
        self.vcorem_channel_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.vcorem_channel_combo.addItems(["1", "2", "3", "4"])
        n6705c_row.addWidget(self.vcorem_channel_combo, 0, 1)
        n6705c_row.addWidget(self._field_label("VcoreL Ch"), 0, 2)
        self.vcorel_channel_combo = DarkComboBox(bg="#091426", border="#17345f")
        self.vcorel_channel_combo.addItems(["1", "2", "3", "4"])
        self.vcorel_channel_combo.setCurrentIndex(1)
        n6705c_row.addWidget(self.vcorel_channel_combo, 0, 3)
        layout.addLayout(n6705c_row)

        self.iic_ctrl_word_input = QLineEdit("0x10")
        layout.addWidget(self._labeled("Voltage Ctrl Word Addr", self.iic_ctrl_word_input))

        self._vcorem_iic = self._create_iic_group("VcoreM", required=True,
                                                   defaults={"device": "0x60", "width": "8",
                                                             "sleep": "0x20", "wakeup": "0x22"})
        layout.addWidget(self._vcorem_iic["card"])

        self._vcorel_iic = self._create_iic_group("VcoreL", required=False,
                                                   defaults={"device": "0x62", "width": "8",
                                                             "sleep": "0x24", "wakeup": "0x26"})
        layout.addWidget(self._vcorel_iic["card"])
        self._set_iic_group_enabled(self._vcorel_iic, False)

        return panel

    def _create_iic_group(self, name, required, defaults):
        card = QFrame()
        card.setObjectName("vhSubCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        tag = QLabel(f"{name} IIC" + (" (required)" if required else " (optional)"))
        tag.setStyleSheet(
            "color: #9cabff; font-weight: 700; font-size: 11px;"
            " background: transparent; border: none;"
        )
        header.addWidget(tag)
        header.addStretch()
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        device_input = QLineEdit(defaults["device"])
        width_input = QLineEdit(defaults["width"])
        sleep_input = QLineEdit(defaults["sleep"])
        wakeup_input = QLineEdit(defaults["wakeup"])

        grid.addWidget(self._field_label("Device Addr"), 0, 0)
        grid.addWidget(device_input, 0, 1)
        grid.addWidget(self._field_label("Bit Width"), 0, 2)
        grid.addWidget(width_input, 0, 3)
        grid.addWidget(self._field_label("Sleep Ctrl Addr"), 1, 0)
        grid.addWidget(sleep_input, 1, 1)
        grid.addWidget(self._field_label("Wakeup Ctrl Addr"), 1, 2)
        grid.addWidget(wakeup_input, 1, 3)
        layout.addLayout(grid)

        return {
            "card": card,
            "device": device_input,
            "width": width_input,
            "sleep": sleep_input,
            "wakeup": wakeup_input,
        }

    def _set_iic_group_enabled(self, group, enabled):
        for key in ("device", "width", "sleep", "wakeup"):
            group[key].setEnabled(enabled)

    # ------------------------------------------------------------------
    # 右侧：操作按钮 + 结果表
    # ------------------------------------------------------------------
    def _create_action_row(self):
        panel = QFrame()
        panel.setObjectName("vhPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self.start_btn = QPushButton("Start Hunt")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.accent_primary};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {Colors.accent_hover}; }}
            QPushButton:pressed {{ background-color: {Colors.accent_pressed}; }}
            QPushButton:disabled {{ background-color: {Colors.disabled_btn_bg}; color: {Colors.disabled_text}; }}
        """)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setCursor(Qt.PointingHandCursor)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a1320;
                color: {Colors.error};
                border: 1px solid #4d2436;
                border-radius: 8px;
                padding: 8px 22px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: #3a1a2c; }}
            QPushButton:disabled {{ background-color: {Colors.disabled_btn_bg}; color: {Colors.disabled_text}; border: 1px solid {Colors.disabled_btn_border}; }}
        """)

        self.export_result_btn = QPushButton("⤓ Export Results")
        self.export_result_btn.setCursor(Qt.PointingHandCursor)
        self.export_result_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a2750;
                color: #c8d8f8;
                border: 1px solid #22376a;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #243760; }
        """)

        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()

        self.vmin_summary_label = QLabel("Vmin: --")
        self.vmin_summary_label.setStyleSheet(
            f"color: {Colors.success}; font-size: 13px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        layout.addWidget(self.vmin_summary_label)
        layout.addWidget(self.export_result_btn)

        return panel

    def _create_result_panel(self):
        panel = QFrame()
        panel.setObjectName("vhPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        layout.addLayout(self._section_title("crosshair.svg", "Sweep Results", "#fbbf24"))

        self.result_table = QTableWidget(0, 6)
        self.result_table.setHorizontalHeaderLabels([
            "Voltage (V)", "Temp (°C)", "Channel", "Iteration", "Status", "Note",
        ])
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.verticalHeader().setVisible(False)
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.result_table.setStyleSheet("""
            QTableWidget {
                background-color: #07111f;
                border: 1px solid #1a2d57;
                border-radius: 8px;
                gridline-color: #16274d;
                color: #dbe7ff;
            }
            QHeaderView::section {
                background-color: #0d1a38;
                color: #8eb0e3;
                border: none;
                border-bottom: 1px solid #1a2d57;
                padding: 6px;
                font-weight: 700;
            }
        """ + SCROLLBAR_STYLE)
        layout.addWidget(self.result_table, 1)

        return panel

    # ------------------------------------------------------------------
    # 小工具
    # ------------------------------------------------------------------
    def _section_title(self, svg_name, text, color):
        row = QHBoxLayout()
        row.setSpacing(6)
        icon = QLabel()
        icon.setPixmap(
            _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, svg_name), color, 16).pixmap(16, 16)
        )
        icon.setFixedSize(16, 16)
        title = QLabel(text)
        title.setObjectName("sectionTitle")
        row.addWidget(icon)
        row.addWidget(title)
        row.addStretch()
        return row

    def _field_label(self, text):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _labeled(self, text, widget):
        container = QWidget()
        container.setObjectName("vhLabeled")
        container.setStyleSheet(
            "QWidget#vhLabeled { background: transparent; border: none; }"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(self._field_label(text))
        layout.addWidget(widget)
        return container

    # ------------------------------------------------------------------
    # 信号绑定
    # ------------------------------------------------------------------
    def _bind_signals(self):
        self.bind_n6705c_signals()
        self.bind_chamber_signals()
        self.bind_serial_signals()
        self.serial_data_received.connect(self._on_uart_data_received)

        self.temp_enable_cb.toggled.connect(self._on_temp_toggled)
        self.vcorel_cb.toggled.connect(self._on_vcorel_toggled)
        self.test_mode_combo.currentIndexChanged.connect(self._on_test_mode_changed)

        self.import_config_btn.clicked.connect(self._import_config)
        self.export_config_btn.clicked.connect(self._export_config)
        self.export_result_btn.clicked.connect(self._export_results)

        self.start_btn.clicked.connect(self._on_start_clicked)
        self.stop_btn.clicked.connect(self._on_stop_clicked)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------
    def _on_temp_toggled(self, checked):
        self._temp_enabled = checked
        self.temp_points_input.setEnabled(checked)
        if hasattr(self, "chamber_card"):
            self.chamber_card.setVisible(checked)

    def _on_vcorel_toggled(self, checked):
        self._vcorel_enabled = checked
        self._set_iic_group_enabled(self._vcorel_iic, checked)
        self.vcorel_channel_combo.setEnabled(checked)

    def _on_test_mode_changed(self):
        mode = self.test_mode_combo.currentData()
        is_internal = mode == "internal"
        self._vcorem_iic["card"].setVisible(is_internal)
        self._vcorel_iic["card"].setVisible(is_internal)
        self.iic_ctrl_word_input.parentWidget().setVisible(is_internal)

    def _on_start_clicked(self):
        try:
            params = self._read_params()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Config", str(exc))
            return

        logger.info("VminHunter start requested: %s", params)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.result_table.setRowCount(0)
        self.vmin_summary_label.setText("Vmin: hunting...")
        self.execution_logs.append_log("[START] VminHunter sweep started")
        self.execution_logs.append_log(
            f"[INFO] mode={params['test_mode']} cnt={params['test_cnt']} "
            f"points={params['voltage_points']}"
        )
        # NOTE: 真正的遍历引擎应在 core 层用 QThread 执行，并通过 Signal/Slot
        #       回填结果。此处仅完成 UI 层交互与参数收集。
        self.execution_logs.append_log(
            "[WARN] Sweep engine (core) not wired yet; UI-only scaffold."
        )

    def _on_stop_clicked(self):
        logger.info("VminHunter stop requested")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.execution_logs.append_log("[STOP] VminHunter sweep stopped")

    # ------------------------------------------------------------------
    # UART 日志桥接（供 SerialComMixin 回调）
    # ------------------------------------------------------------------
    def append_log(self, message: str):
        if hasattr(self, "execution_logs") and self.execution_logs is not None:
            self.execution_logs.append_log(message)

    def _on_uart_data_received(self, data: bytes):
        try:
            text = data.decode("utf-8", errors="replace").rstrip("\r\n")
        except Exception:
            text = repr(data)
        if text:
            self.append_log(f"[DUT] {text}")

    # ------------------------------------------------------------------
    # 参数读取 / 配置导入导出
    # ------------------------------------------------------------------
    def _parse_float_list(self, text, field):
        items = [s.strip() for s in text.split(",") if s.strip()]
        result = []
        for item in items:
            try:
                result.append(float(item))
            except ValueError:
                raise ValueError(f"{field} contains invalid value: {item!r}")
        if not result:
            raise ValueError(f"{field} must not be empty")
        return result

    def _parse_voltage_sweep(self):
        def _to_float(text, field):
            try:
                return float(text.strip())
            except ValueError:
                raise ValueError(f"{field} must be a number")

        start = _to_float(self.voltage_start_input.text(), "Voltage Start")
        end = _to_float(self.voltage_end_input.text(), "Voltage End")
        step = _to_float(self.voltage_step_input.text(), "Voltage Step")

        if step <= 0:
            raise ValueError("Voltage Step must be positive")
        if start == end:
            raise ValueError("Voltage Start must differ from End")

        direction = -1.0 if start > end else 1.0
        signed_step = step * direction

        points = []
        eps = step / 1000.0
        v = start
        while (direction < 0 and v >= end - eps) or (direction > 0 and v <= end + eps):
            points.append(round(v, 6))
            v += signed_step
            if len(points) > 10000:
                raise ValueError("Voltage sweep range/step produces too many points (>10000)")

        if not points:
            raise ValueError("Voltage sweep produced no points")
        return start, end, step, points

    def _read_params(self):
        try:
            test_cnt = int(self.test_cnt_input.text().strip())
        except ValueError:
            raise ValueError("Test CNT must be an integer")
        if test_cnt <= 0:
            raise ValueError("Test CNT must be positive")

        v_start, v_end, v_step, voltage_points = self._parse_voltage_sweep()

        params = {
            "test_cnt": test_cnt,
            "test_mode": self.test_mode_combo.currentData(),
            "temperature": {
                "enable": self._temp_enabled,
                "points": self._parse_float_list(self.temp_points_input.text(), "Temp Points")
                if self._temp_enabled else [],
            },
            "monitor_channels": {
                "VcoreM": True,
                "VcoreL": self._vcorel_enabled,
            },
            "voltage_sweep": {
                "start": v_start,
                "end": v_end,
                "step": v_step,
            },
            "voltage_points": voltage_points,
            "channel_config": {
                "n6705c": {
                    "VcoreM_channel": int(self.vcorem_channel_combo.currentText()),
                    "VcoreL_channel": int(self.vcorel_channel_combo.currentText()),
                },
                "iic": {
                    "voltage_ctrl_word_addr": self.iic_ctrl_word_input.text().strip(),
                    "VcoreM": self._read_iic_group(self._vcorem_iic),
                    "VcoreL": self._read_iic_group(self._vcorel_iic),
                },
            },
            "uart": {
                "port": self.get_selected_serial_port() or "",
                "baudrate": int(self._serial_baudrate),
            },
        }
        return params

    def _read_iic_group(self, group):
        return {
            "device_addr": group["device"].text().strip(),
            "bit_width": group["width"].text().strip(),
            "sleep_ctrl_addr": group["sleep"].text().strip(),
            "wakeup_ctrl_addr": group["wakeup"].text().strip(),
        }

    def _export_config(self):
        try:
            params = self._read_params()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Config", str(exc))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export VminHunter Config", "vmin_hunter_config.json",
            "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(params, f, indent=2, ensure_ascii=False)
            self.execution_logs.append_log(f"[EXPORT] Config exported: {path}")
        except OSError:
            logger.error("Failed to export VminHunter config", exc_info=True)
            QMessageBox.critical(self, "Export Failed", "Unable to write config file.")

    def _import_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import VminHunter Config", "", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            logger.error("Failed to import VminHunter config", exc_info=True)
            QMessageBox.critical(self, "Import Failed", "Unable to read config file.")
            return
        self._apply_config(data)
        self.execution_logs.append_log(f"[INFO] Config imported: {path}")

    def _apply_config(self, data):
        try:
            self.test_cnt_input.setText(str(data.get("test_cnt", 100)))
            mode = data.get("test_mode", "internal")
            for i in range(self.test_mode_combo.count()):
                if self.test_mode_combo.itemData(i) == mode:
                    self.test_mode_combo.setCurrentIndex(i)
                    break

            temp = data.get("temperature", {})
            self.temp_enable_cb.setChecked(bool(temp.get("enable", False)))
            if temp.get("points"):
                self.temp_points_input.setText(", ".join(str(p) for p in temp["points"]))

            channels = data.get("monitor_channels", {})
            self.vcorel_cb.setChecked(bool(channels.get("VcoreL", False)))

            sweep = data.get("voltage_sweep")
            if isinstance(sweep, dict):
                if "start" in sweep:
                    self.voltage_start_input.setText(str(sweep["start"]))
                if "end" in sweep:
                    self.voltage_end_input.setText(str(sweep["end"]))
                if "step" in sweep:
                    self.voltage_step_input.setText(str(sweep["step"]))
            else:
                vp = data.get("voltage_points", [])
                if isinstance(vp, list) and len(vp) >= 2:
                    try:
                        floats = [float(v) for v in vp]
                        v_start = floats[0]
                        v_end = floats[-1]
                        if len(floats) >= 2:
                            v_step = abs(floats[1] - floats[0])
                        else:
                            v_step = abs(v_start - v_end)
                        if v_step <= 0:
                            v_step = abs(v_start - v_end) or 0.05
                        self.voltage_start_input.setText(str(v_start))
                        self.voltage_end_input.setText(str(v_end))
                        self.voltage_step_input.setText(str(round(v_step, 6)))
                    except (TypeError, ValueError):
                        logger.warning("Legacy voltage_points failed to convert", exc_info=True)

            ch_cfg = data.get("channel_config", {})
            iic = ch_cfg.get("iic", {})
            if iic.get("voltage_ctrl_word_addr"):
                self.iic_ctrl_word_input.setText(str(iic["voltage_ctrl_word_addr"]))
            self._apply_iic_group(self._vcorem_iic, iic.get("VcoreM", {}))
            self._apply_iic_group(self._vcorel_iic, iic.get("VcoreL", {}))

            uart = data.get("uart", {})
            if uart.get("port") and hasattr(self, "serial_combo"):
                port_text = str(uart["port"])
                idx = self.serial_combo.findText(port_text, Qt.MatchStartsWith)
                if idx >= 0:
                    self.serial_combo.setCurrentIndex(idx)
                else:
                    self.serial_combo.addItem(port_text)
                    self.serial_combo.setCurrentText(port_text)
            if uart.get("baudrate"):
                try:
                    self._serial_baudrate = int(uart["baudrate"])
                except (TypeError, ValueError):
                    pass
        except (TypeError, ValueError):
            logger.error("Failed to apply VminHunter config", exc_info=True)
            QMessageBox.warning(self, "Import Warning", "Config partially applied; some fields invalid.")

    def _apply_iic_group(self, group, data):
        if not isinstance(data, dict):
            return
        mapping = {
            "device": "device_addr",
            "width": "bit_width",
            "sleep": "sleep_ctrl_addr",
            "wakeup": "wakeup_ctrl_addr",
        }
        for widget_key, data_key in mapping.items():
            if data.get(data_key) is not None:
                group[widget_key].setText(str(data[data_key]))

    def _export_results(self):
        if self.result_table.rowCount() == 0:
            QMessageBox.information(self, "No Results", "There are no sweep results to export yet.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "vmin_hunter_results.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            import csv
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                headers = [
                    self.result_table.horizontalHeaderItem(c).text()
                    for c in range(self.result_table.columnCount())
                ]
                writer.writerow(headers)
                for r in range(self.result_table.rowCount()):
                    row = [
                        self.result_table.item(r, c).text() if self.result_table.item(r, c) else ""
                        for c in range(self.result_table.columnCount())
                    ]
                    writer.writerow(row)
            self.execution_logs.append_log(f"[EXPORT] Results exported: {path}")
        except OSError:
            logger.error("Failed to export VminHunter results", exc_info=True)
            QMessageBox.critical(self, "Export Failed", "Unable to write results file.")

    # ------------------------------------------------------------------
    # 结果回填 (供 core 层通过 Signal/Slot 调用)
    # ------------------------------------------------------------------
    def append_result_row(self, voltage, temp, channel, iteration, status, note=""):
        row = self.result_table.rowCount()
        self.result_table.insertRow(row)
        values = [
            f"{voltage:.3f}" if isinstance(voltage, (int, float)) else str(voltage),
            str(temp),
            str(channel),
            str(iteration),
            str(status),
            str(note),
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            if col == 4:
                if str(status).upper() in ("FAIL", "CRASH", "HANG"):
                    item.setForeground(Qt.red)
                elif str(status).upper() == "PASS":
                    item.setForeground(Qt.green)
            self.result_table.setItem(row, col, item)
        self.result_table.scrollToBottom()

    def set_vmin_summary(self, vmin):
        if vmin is None:
            self.vmin_summary_label.setText("Vmin: --")
        else:
            self.vmin_summary_label.setText(f"Vmin: {vmin:.3f} V")
