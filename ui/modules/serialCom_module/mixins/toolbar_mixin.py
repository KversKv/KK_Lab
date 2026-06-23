# -*- coding: utf-8 -*-
"""工具栏/侧栏/端口与收发设置区/状态栏构建 + 信号绑定 + 工厂辅助方法。"""

import json
import os
import re
import time
import uuid as _uuid
from datetime import datetime

import serial
import serial.tools.list_ports

from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QFileDialog, QFrame, QGridLayout, QGraphicsBlurEffect,
    QGraphicsDropShadowEffect, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTabBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtCore import (
    Property, QEasingCurve, QMimeData, QObject, QPoint, QPropertyAnimation,
    QRect, QRectF, QSize, Qt, QThread, QTimer, Signal,
)
from PySide6.QtGui import (
    QAction, QColor, QCursor, QFont, QIcon, QKeySequence, QPainter, QPen,
    QPixmap, QShortcut,
)
from PySide6.QtSvg import QSvgRenderer

from debug_config import DEBUG_MOCK
from log_config import get_logger
from version import __version__ as _APP_VERSION
from ui.utils.icon_utils import (
    tinted_svg_icon as _tinted_svg_icon,
    tinted_svg_pixmap as _tinted_svg_pixmap,
)
from core.auto_baud_detector import (
    AUTO_BAUD_CONFIG, AutoBaudMonitor, AutoBaudScanWorker, AutoBaudState,
    score_rx_data,
)
from ui.modules.serialCom_module.widgets import (
    _FramelessChromeDialog,
    _MixinSerialSettingsDialog,
    _SERIAL_BTN_FIXED_WIDTH,
    _SearchSerialPortWorker,
    _SerialSearchButton,
    _update_serial_btn_state,
)
from ui.modules.serialCom_module.serialCom_module_frame import (
    MODE_FULL,
    MODE_INLINE,
    MODE_SEARCH_SELECT,
    _LINK_ICON_PATH,
    _SEARCH_ICON_PATH,
    _SERIAL_BTN_HEIGHT,
    _SERIAL_BTN_ICON_SIZE,
    _SERIAL_BTN_RADIUS,
    _SVG_COMMON_DIR,
    _SVG_LOGS_DIR,
    _SVG_SERIAL_DIR,
    _UNLINK_ICON_PATH,
    DARK_CARD_STYLE,
    _CLR_BG_CARD,
    _CLR_BG_LOG,
    _CLR_BG_MAIN,
    _CLR_BG_PANEL,
    _CLR_BLUE,
    _CLR_BORDER,
    _CLR_BORDER_HOVER,
    _CLR_BORDER_SOFT,
    _CLR_CONNECT_BG,
    _CLR_CONNECT_FG,
    _CLR_CONNECT_TEXT,
    _CLR_CURSOR,
    _CLR_DISCONNECT_TEXT,
    _CLR_ERROR,
    _CLR_FILTER_BG,
    _CLR_FILTER_BORDER,
    _CLR_FILTER_TEXT,
    _CLR_INPUT_BG,
    _CLR_INPUT_TEXT,
    _CLR_ROSE_ICON,
    _CLR_RX,
    _CLR_SCROLLBAR,
    _CLR_SCROLLBAR_HV,
    _CLR_SELECTION_BG,
    _CLR_SELECTION_TEXT,
    _CLR_SEND_BG,
    _CLR_SEND_HOVER,
    _CLR_SEND_PRESS,
    _CLR_TEXT_ACCENT,
    _CLR_TEXT_BODY,
    _CLR_TEXT_BTN,
    _CLR_TEXT_BTN_LOG,
    _CLR_TEXT_INFO,
    _CLR_TEXT_LABEL,
    _CLR_TEXT_LINENO,
    _CLR_TEXT_MUTED,
    _CLR_TEXT_SUBTITLE,
    _CLR_TEXT_TIME,
    _CLR_TEXT_TITLE,
    _CLR_TEXT_WHITE,
    _CLR_TOGGLE_ON,
    _CLR_TX,
    _CLR_WARN_ICON,
    _CLR_WARNING,
    _DLG_STYLE,
    _SERIAL_BTN_HEIGHT,
    _SERIAL_BTN_ICON_SIZE,
    _SERIAL_BTN_RADIUS,
    _TERM_FONT,
    _UI_FONT,
    _serial_connect_style,
    _serial_disconnect_style,
    _serial_search_style,
    body_splitter_style,
    center_vsplitter_style,
    center_widget_style,
    checkbox_style,
    compact_spinbox_style,
    dialog_backdrop_style,
    frameless_chrome_style,
    script_editor_dialog_style,
    dialog_cancel_button_style,
    dialog_line_edit_style,
    dialog_ok_button_style,
    extra_log_error_color,
    field_label_style,
    filter_input_style,
    filter_match_label_style,
    history_combo_style,
    inline_serial_label_style,
    inline_serial_search_button_extra_style,
    log_color_info_style,
    log_color_info_text,
    log_document_style,
    log_edit_style,
    log_frame_style,
    log_panel_button_style,
    log_title_style,
    log_title_icon_color,
    log_toolbar_button_style,
    log_icon_button_style,
    main_connect_button_style,
    project_tabs_style,
    quick_action_overlay_style,
    quick_action_overlay_container_style,
    quick_add_button_style,
    quick_group_button_style,
    quick_button_container_style,
    quick_button_scroll_style,
    quick_cmd_dialog_style,
    quick_command_button_style,
    quick_combo_style,
    quick_group_combo_bg_style,
    quick_commands_panel_style,
    quick_preview_popup_shadow,
    quick_preview_popup_style,
    quick_toolbar_button_style,
    bottom_tabs_style,
    section_card_style,
    section_card_shadow,
    section_header_divider_style,
    panel_divider_style,
    script_stop_button_style,
    script_add_step_button_style,
    section_title_style,
    send_button_style,
    separator_style,
    sidebar_toggle_button_style,
    auto_scroll_button_style,
    sidebar_toggle_icon_colors,
    auto_scroll_icon_colors,
    sidebar_wrapper_style,
    small_label_style,
    status_bar_style,
    status_label_style,
    thin_scrollbar_style,
    toolbar_connect_button_style,
    toolbar_style,
    toggle_colors,
    transparent_background_style,
    transparent_scroll_area_style,
    transparent_toolbar_button_style,
    unit_label_style,
    SERIAL_SCROLLBAR_STYLE,
    SerialDarkComboBox,
    SerialHistoryComboBox,
    _CLR_HISTORY_COMBO_BG
)

logger = get_logger(__name__)


class ToolbarMixin:
    """工具栏/侧栏/端口与收发设置区/状态栏构建 + 信号绑定 + 工厂辅助方法。"""

    def _build_sc_toolbar(self):
        frame = QFrame()
        frame.setObjectName("scToolbar")
        frame.setFixedHeight(48)
        frame.setStyleSheet(toolbar_style())
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        self._sc_connect_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "Connect"
        )
        self._sc_connect_btn.setStyleSheet(toolbar_connect_button_style())
        icon_conn = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), _CLR_CONNECT_TEXT, 13)
        if not icon_conn.isNull():
            self._sc_connect_btn.setIcon(icon_conn)
        layout.addWidget(self._sc_connect_btn)

        self._sc_pause_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "pause.svg"), "Pause"
        )
        self._sc_pause_btn.setCheckable(True)
        layout.addWidget(self._sc_pause_btn)

        self._sc_stop_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "stop.svg"), "Stop"
        )
        layout.addWidget(self._sc_stop_btn)

        self._sc_refresh_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "refresh.svg"), "Refresh"
        )
        layout.addWidget(self._sc_refresh_btn)

        layout.addSpacing(8)
        sep_conn = QFrame()
        sep_conn.setFrameShape(QFrame.VLine)
        sep_conn.setStyleSheet(separator_style())
        layout.addWidget(sep_conn)
        layout.addSpacing(8)

        self._sc_add_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "plus.svg"), ""
        )
        self._sc_add_log_btn.setFixedSize(28, 28)
        self._sc_add_log_btn.setToolTip("Add LOG panel")
        self._sc_add_log_btn.setStyleSheet(log_panel_button_style())
        icon_add = self._sc_make_enabled_disabled_icon(
            os.path.join(_SVG_LOGS_DIR, "plus.svg"), 14
        )
        if not icon_add.isNull():
            self._sc_add_log_btn.setIcon(icon_add)
        layout.addWidget(self._sc_add_log_btn)

        self._sc_remove_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "minus.svg"), ""
        )
        self._sc_remove_log_btn.setFixedSize(28, 28)
        self._sc_remove_log_btn.setToolTip("Remove current LOG panel")
        self._sc_remove_log_btn.setStyleSheet(log_panel_button_style(disabled=True))
        icon_remove = self._sc_make_enabled_disabled_icon(
            os.path.join(_SVG_LOGS_DIR, "minus.svg"), 14
        )
        if not icon_remove.isNull():
            self._sc_remove_log_btn.setIcon(icon_remove)
        self._sc_remove_log_btn.setEnabled(False)
        layout.addWidget(self._sc_remove_log_btn)

        layout.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(separator_style())
        layout.addWidget(sep)

        layout.addSpacing(8)

        self._sc_sidebar_toggle_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "sidebar.svg"), "Sidebar"
        )
        self._sc_sidebar_toggle_btn.setStyleSheet(sidebar_toggle_button_style())
        self._sc_sidebar_toggle_btn.setCheckable(True)
        self._sc_sidebar_toggle_btn.setChecked(True)
        self._sc_bind_toggle_icon(
            self._sc_sidebar_toggle_btn,
            os.path.join(_SVG_SERIAL_DIR, "sidebar.svg"),
            sidebar_toggle_icon_colors(),
            13,
        )
        layout.addWidget(self._sc_sidebar_toggle_btn)

        layout.addStretch()

        self._sc_chart_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "chart.svg"), "Chart"
        )
        layout.addWidget(self._sc_chart_btn)

        self._sc_settings_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "settings.svg"), "Settings"
        )
        layout.addWidget(self._sc_settings_btn)

        return frame

    # --- sidebar ---

    def _build_sc_sidebar(self):
        wrapper = QFrame()
        wrapper.setObjectName("scSidebarWrapper")
        wrapper.setMinimumWidth(self._sc_sidebar_min_width)
        wrapper.setMaximumWidth(298)
        wrapper.setStyleSheet(sidebar_wrapper_style())
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(transparent_scroll_area_style())

        vbar = scroll.verticalScrollBar()
        _vbar_width = 4
        vbar.setFixedWidth(_vbar_width)
        vbar.setStyleSheet(thin_scrollbar_style())

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_sc_section_port_settings())
        root.addWidget(self._build_sc_section_rx_settings())
        root.addWidget(self._build_sc_section_tx_settings())
        root.addStretch()

        scroll.setWidget(container)
        wrapper_layout.addWidget(scroll)
        return wrapper

    def _build_sc_section_port_settings(self):
        grp = self._make_sc_section(
            "Serial Config", os.path.join(_SVG_SERIAL_DIR, "sidebar.svg")
        )
        layout = grp.property("_inner_layout")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnMinimumWidth(0, 66)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._make_sc_label("Port"), 0, 0)
        self._sc_port_combo = SerialDarkComboBox()
        self._sc_port_combo.setFixedHeight(28)
        self._sc_port_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_port_combo.setMinimumWidth(60)
        f = self._sc_port_combo.font()
        f.setPixelSize(12)
        self._sc_port_combo.setFont(f)
        grid.addWidget(self._sc_port_combo, 0, 1)

        grid.addWidget(self._make_sc_label("Baudrate"), 1, 0)
        self._sc_baud_combo = SerialDarkComboBox()
        self._sc_baud_combo.setFixedHeight(28)
        self._sc_baud_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_baud_combo.setMinimumWidth(60)
        self._sc_baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "Custom"]:
            self._sc_baud_combo.addItem(br)
        self._sc_baud_combo.setCurrentIndex(0)
        f2 = self._sc_baud_combo.font()
        f2.setPixelSize(12)
        self._sc_baud_combo.setFont(f2)
        grid.addWidget(self._sc_baud_combo, 1, 1)

        self._sc_auto_detect_cb = QCheckBox("Auto-Detect")
        self._sc_auto_detect_cb.setChecked(True)
        self._sc_auto_detect_cb.setStyleSheet(self._sc_checkbox_style())
        grid.addWidget(self._sc_auto_detect_cb, 2, 1)
        self._sc_baud_combo.setEditable(False)
        self._sc_baud_combo.setEnabled(False)

        grid.addWidget(self._make_sc_label("Data bits"), 3, 0)
        self._sc_databit_combo = SerialDarkComboBox()
        self._sc_databit_combo.setFixedHeight(28)
        self._sc_databit_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_databit_combo.setMinimumWidth(60)
        for d in ["8", "7", "6", "5"]:
            self._sc_databit_combo.addItem(d)
        grid.addWidget(self._sc_databit_combo, 3, 1)

        grid.addWidget(self._make_sc_label("Flow Control"), 4, 0)
        self._sc_flow_combo = SerialDarkComboBox()
        self._sc_flow_combo.setFixedHeight(28)
        self._sc_flow_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_flow_combo.setMinimumWidth(60)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._sc_flow_combo.addItem(fc)
        grid.addWidget(self._sc_flow_combo, 4, 1)

        grid.addWidget(self._make_sc_label("Stop bits"), 5, 0)
        self._sc_stopbit_combo = SerialDarkComboBox()
        self._sc_stopbit_combo.setFixedHeight(28)
        self._sc_stopbit_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_stopbit_combo.setMinimumWidth(60)
        for s in ["1", "1.5", "2"]:
            self._sc_stopbit_combo.addItem(s)
        grid.addWidget(self._sc_stopbit_combo, 5, 1)

        grid.addWidget(self._make_sc_label("Parity"), 6, 0)
        self._sc_parity_combo = SerialDarkComboBox()
        self._sc_parity_combo.setFixedHeight(28)
        self._sc_parity_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_parity_combo.setMinimumWidth(60)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._sc_parity_combo.addItem(p)
        grid.addWidget(self._sc_parity_combo, 6, 1)

        layout.addLayout(grid)
        return grp

    _TOGGLE_W = 92
    _SPIN_W = _TOGGLE_W // 2
    _INTERVAL_SPIN_W = _TOGGLE_W
    _MS_LABEL_W = 16
    _COMBO_END_W = _TOGGLE_W

    def _build_sc_section_rx_settings(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _MiniSlideToggle
        grp = self._make_sc_section(
            "RX Config", os.path.join(_SVG_SERIAL_DIR, "zap.svg")
        )
        layout = grp.property("_inner_layout")

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.addWidget(self._make_sc_label("Format"))
        row1.addStretch()
        self._sc_rx_toggle = _MiniSlideToggle("ASCII", "HEX")
        self._sc_rx_toggle.toggled.connect(lambda v: setattr(self, '_sc_rx_display_hex', v == "HEX"))
        row1.addWidget(self._sc_rx_toggle)
        layout.addLayout(row1)

        row_af = QHBoxLayout()
        row_af.setSpacing(4)
        self._sc_rx_auto_flush_cb = QCheckBox("Auto Flush")
        self._sc_rx_auto_flush_cb.setToolTip("Flush RX data to the log after the configured idle interval")
        self._sc_rx_auto_flush_cb.setStyleSheet(self._sc_checkbox_style())
        row_af.addWidget(self._sc_rx_auto_flush_cb)
        row_af.addStretch()
        self._sc_rx_auto_flush_spin = QSpinBox()
        self._sc_rx_auto_flush_spin.setRange(10, 60000)
        self._sc_rx_auto_flush_spin.setValue(50)
        self._sc_rx_auto_flush_spin.setSingleStep(10)
        self._sc_rx_auto_flush_spin.setSuffix(" ms")
        self._sc_rx_auto_flush_spin.setAlignment(Qt.AlignCenter)
        self._sc_rx_auto_flush_spin.setFixedSize(self._INTERVAL_SPIN_W, 26)
        self._sc_rx_auto_flush_spin.setStyleSheet(
            compact_spinbox_style(up_button_width=0, padding="2px 8px")
        )
        row_af.addWidget(self._sc_rx_auto_flush_spin)
        layout.addLayout(row_af)

        self._sc_rx_show_time_cb = QCheckBox("Show Time (ms)")
        self._sc_rx_show_time_cb.setChecked(True)
        self._sc_rx_show_time_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_rx_show_time_cb.toggled.connect(lambda v: setattr(self, '_sc_show_timestamp', v))
        layout.addWidget(self._sc_rx_show_time_cb)

        self._sc_show_system_cb = QCheckBox("Show System Log")
        self._sc_show_system_cb.setChecked(False)
        self._sc_show_system_cb.setToolTip("Show blue system/info messages in log")
        self._sc_show_system_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_show_system_cb.toggled.connect(lambda v: setattr(self, '_sc_show_system_log', v))
        layout.addWidget(self._sc_show_system_cb)

        return grp

    def _build_sc_section_tx_settings(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _MiniSlideToggle
        grp = self._make_sc_section(
            "TX Config", os.path.join(_SVG_SERIAL_DIR, "send-outline.svg")
        )
        layout = grp.property("_inner_layout")

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.addWidget(self._make_sc_label("Format"))
        row1.addStretch()
        self._sc_tx_toggle = _MiniSlideToggle("ASCII", "HEX")
        self._sc_tx_toggle.toggled.connect(lambda v: setattr(self, '_sc_tx_display_hex', v == "HEX"))
        row1.addWidget(self._sc_tx_toggle)
        layout.addLayout(row1)

        row_ending = QHBoxLayout()
        row_ending.setSpacing(4)
        row_ending.addWidget(self._make_sc_label("Line Ending"))
        row_ending.addStretch()
        self._sc_ending_combo = SerialDarkComboBox()
        self._sc_ending_combo.setFixedHeight(26)
        self._sc_ending_combo.setFixedWidth(self._COMBO_END_W)
        for label, val in [("\\r\\n", "\r\n"), ("\\n", "\n"), ("\\r", "\r"), ("\\n\\r", "\n\r"), ("None", "")]:
            self._sc_ending_combo.addItem(label, val)
        self._sc_ending_combo.setCurrentIndex(0)
        f = self._sc_ending_combo.font()
        f.setPixelSize(12)
        self._sc_ending_combo.setFont(f)
        self._sc_ending_combo.currentIndexChanged.connect(
            lambda i: setattr(self, '_sc_line_ending', self._sc_ending_combo.itemData(i) or "")
        )
        row_ending.addWidget(self._sc_ending_combo)
        layout.addLayout(row_ending)

        self._sc_show_send_cb = QCheckBox("Show Sent Data")
        self._sc_show_send_cb.setChecked(True)
        self._sc_show_send_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_show_send_cb.toggled.connect(lambda v: setattr(self, '_sc_show_send', v))
        layout.addWidget(self._sc_show_send_cb)

        self._sc_line_by_line_cb = QCheckBox("Line by Line")
        self._sc_line_by_line_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_line_by_line_cb.toggled.connect(lambda v: setattr(self, '_sc_line_by_line', v))
        layout.addWidget(self._sc_line_by_line_cb)

        return grp

    # --- log area ---


    def _build_sc_status_bar(self):
        frame = QFrame()
        frame.setObjectName("scStatusBar")
        frame.setFixedHeight(32)
        frame.setStyleSheet(status_bar_style())
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 3, 12, 3)
        layout.setSpacing(18)

        self._sc_status_port_label = QLabel("\u2022 Port: Unconnected")
        self._sc_status_port_label.setStyleSheet(status_label_style("error", compact=True))
        layout.addWidget(self._sc_status_port_label)

        self._sc_status_baud_label = QLabel("Baud rate (bps): -")
        self._sc_status_baud_label.setStyleSheet(status_label_style("muted", compact=True))
        layout.addWidget(self._sc_status_baud_label)

        self._sc_status_rx_label = QLabel("RX: 0 B")
        self._sc_status_rx_label.setStyleSheet(status_label_style("rx", compact=True))
        layout.addWidget(self._sc_status_rx_label)

        self._sc_status_tx_label = QLabel("TX: 0 B")
        self._sc_status_tx_label.setStyleSheet(status_label_style("tx", compact=True))
        layout.addWidget(self._sc_status_tx_label)

        self._sc_status_autobaud_label = QLabel("")
        self._sc_status_autobaud_label.setStyleSheet(status_label_style("accent", compact=True))
        self._sc_status_autobaud_label.setVisible(False)
        layout.addWidget(self._sc_status_autobaud_label)

        layout.addStretch()

        return frame

    # --- signal binding ---

    def _bind_sc_signals(self):
        self._sc_connect_btn.clicked.connect(self._sc_on_connect_toggle)
        self._sc_pause_btn.clicked.connect(self._sc_on_pause)
        self._sc_stop_btn.clicked.connect(self._sc_on_stop)
        self._sc_refresh_btn.clicked.connect(self._sc_on_refresh)
        self._sc_add_log_btn.clicked.connect(self._sc_on_add_log_panel)
        self._sc_remove_log_btn.clicked.connect(self._sc_on_remove_log_panel)
        self._sc_sidebar_toggle_btn.clicked.connect(self._sc_on_sidebar_toggle)
        self._sc_settings_btn.clicked.connect(self._sc_open_settings_dialog)
        self._sc_chart_btn.clicked.connect(self._sc_open_chart_dialog)

        self._sc_filter_btn.clicked.connect(self._sc_on_filter_toggle)
        self._sc_filter_input.returnPressed.connect(self._sc_apply_filter)
        self._sc_filter_input.textChanged.connect(self._sc_on_filter_input_changed)
        self._sc_filter_regex_cb.toggled.connect(self._sc_on_filter_option_changed)
        self._sc_filter_case_cb.toggled.connect(self._sc_on_filter_option_changed)
        self._sc_filter_invert_cb.toggled.connect(self._sc_on_filter_option_changed)
        self._sc_filter_before_spin.valueChanged.connect(self._sc_on_filter_option_changed)
        self._sc_filter_after_spin.valueChanged.connect(self._sc_on_filter_option_changed)
        self._sc_copy_btn.clicked.connect(self._sc_copy_logs)
        self._sc_export_btn.clicked.connect(self._sc_export_logs)
        self._sc_save_btn.clicked.connect(self._sc_on_save_toggle)
        self._sc_clear_btn.clicked.connect(self._sc_clear_logs)
        self._sc_scroll_lock_btn.clicked.connect(
            lambda c: setattr(self, '_sc_auto_scroll', c)
        )

        self._sc_send_btn.clicked.connect(self._sc_on_send)
        self._sc_send_input.returnPressed.connect(self._sc_on_send)

        self._sc_qc_add_btn.clicked.connect(self._sc_add_quick_cmd)
        self._sc_qc_import_btn.clicked.connect(self._sc_import_quick_cmds)
        self._sc_qc_export_btn.clicked.connect(self._sc_export_quick_cmds)
        self._sc_qc_new_group_btn.clicked.connect(self._sc_qc_add_group)
        self._sc_qc_project_tabs.currentChanged.connect(self._sc_qc_on_project_tab_changed)
        self._sc_qc_project_tabs.customContextMenuRequested.connect(
            self._sc_qc_on_project_tab_context_menu
        )
        self._sc_qc_project_tabs.project_reorder_requested.connect(
            self._sc_qc_on_project_reorder
        )
        self._sc_qc_group_combo.currentIndexChanged.connect(self._sc_qc_on_group_changed)
        self._sc_qc_group_edit_btn.clicked.connect(self._sc_qc_edit_current_group)
        self._sc_qc_group_delete_btn.clicked.connect(self._sc_qc_delete_current_group)

        self._sc_baud_combo.activated.connect(lambda _idx: self._sc_on_baudrate_changed())
        _baud_line_edit = self._sc_baud_combo.lineEdit()
        if _baud_line_edit is not None:
            _baud_line_edit.editingFinished.connect(self._sc_on_baudrate_changed)

        self.serial_data_received.connect(self._sc_on_data_received)

        self._sc_auto_detect_cb.toggled.connect(self._sc_on_auto_detect_toggled)

        self._sc_rx_flush_timer = QTimer(self)
        self._sc_rx_flush_timer.setSingleShot(True)
        self._sc_rx_flush_timer.timeout.connect(self._sc_flush_rx_line_buf)

        self._sc_install_filter_shortcut()


    @staticmethod
    def _make_sc_btn(svg_path, text, tone="toolbar"):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        icon_size = 11
        if tone == "log":
            icon_color = _CLR_TEXT_BTN_LOG
            btn.setStyleSheet(log_toolbar_button_style())
        elif tone == "quick":
            icon_color = _CLR_TEXT_BTN_LOG
            btn.setStyleSheet(quick_toolbar_button_style(max_height=26, padding="4px 11px", radius=6, min_height=0))
        else:
            icon_color = _CLR_TEXT_MUTED
            icon_size = 13
            btn.setStyleSheet(transparent_toolbar_button_style())
        icon = _tinted_svg_icon(svg_path, icon_color, icon_size)
        if not icon.isNull():
            btn.setIcon(icon)
        return btn

    @staticmethod
    def _sc_make_enabled_disabled_icon(svg_path, size):
        icon = QIcon()
        normal_pix = _tinted_svg_pixmap(svg_path, _CLR_TEXT_TITLE, size)
        if not normal_pix.isNull():
            icon.addPixmap(normal_pix, QIcon.Normal, QIcon.On)
            icon.addPixmap(normal_pix, QIcon.Normal, QIcon.Off)
        disabled_pix = _tinted_svg_pixmap(svg_path, _CLR_TEXT_MUTED, size)
        if not disabled_pix.isNull():
            icon.addPixmap(disabled_pix, QIcon.Disabled, QIcon.On)
            icon.addPixmap(disabled_pix, QIcon.Disabled, QIcon.Off)
        return icon

    @staticmethod
    def _make_sc_section(title, icon_path=None):
        grp = QFrame()
        grp.setObjectName("scSectionCard")
        grp.setStyleSheet(section_card_style())

        shadow_cfg = section_card_shadow()
        if shadow_cfg:
            shadow = QGraphicsDropShadowEffect(grp)
            shadow.setBlurRadius(shadow_cfg["blur_radius"])
            shadow.setOffset(shadow_cfg["offset_x"], shadow_cfg["offset_y"])
            shadow.setColor(QColor(*shadow_cfg["color"]))
            grp.setGraphicsEffect(shadow)

        layout = QVBoxLayout(grp)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(7)

        if icon_path and os.path.isfile(icon_path):
            icon_lbl = QLabel()
            icon_lbl.setStyleSheet(transparent_background_style())
            icon_pm = _tinted_svg_icon(icon_path, _CLR_TEXT_LABEL, 14).pixmap(14, 14)
            if not icon_pm.isNull():
                icon_lbl.setPixmap(icon_pm)
                icon_lbl.setFixedSize(14, 14)
                header.addWidget(icon_lbl)

        lbl = QLabel(title.upper())
        lbl.setStyleSheet(section_title_style())
        header.addWidget(lbl)
        header.addStretch()

        header_wrap = QVBoxLayout()
        header_wrap.setContentsMargins(0, 0, 0, 0)
        header_wrap.setSpacing(7)
        header_wrap.addLayout(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(section_header_divider_style())
        header_wrap.addWidget(divider)

        layout.addLayout(header_wrap)

        grp.setProperty("_inner_layout", layout)
        return grp

    @staticmethod
    def _make_sc_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(field_label_style())
        return lbl

    @staticmethod
    def _sc_checkbox_style():
        _chk_svg = os.path.join(_SVG_SERIAL_DIR, "checkmark.svg").replace("\\", "/")
        return checkbox_style(_chk_svg)


