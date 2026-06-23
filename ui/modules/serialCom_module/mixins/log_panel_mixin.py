# -*- coding: utf-8 -*-
"""多 LOG 面板/独立窗口/面板设置 + 日志文件/自动保存/NTP + 日志核心追加与刷新。"""

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


class LogPanelMixin:
    """多 LOG 面板/独立窗口/面板设置 + 日志文件/自动保存/NTP + 日志核心追加与刷新。"""

    def _build_sc_log_area(self):
        frame = QFrame()
        frame.setObjectName("scLogFrame")
        frame.setStyleSheet(log_frame_style())
        frame.setProperty("_is_primary", True)

        shadow_cfg = section_card_shadow()
        if shadow_cfg:
            shadow = QGraphicsDropShadowEffect(frame)
            shadow.setBlurRadius(shadow_cfg["blur_radius"])
            shadow.setOffset(shadow_cfg["offset_x"], shadow_cfg["offset_y"])
            shadow.setColor(QColor(*shadow_cfg["color"]))
            frame.setGraphicsEffect(shadow)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 10, 12, 8)
        toolbar.setSpacing(8)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), log_title_icon_color(), 14)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(14, 14))
        icon_label.setFixedSize(16, 16)
        icon_label.setStyleSheet(transparent_background_style())
        toolbar.addWidget(icon_label)

        title = QLabel("Serial Log")
        title.setStyleSheet(log_title_style())
        toolbar.addWidget(title)

        toolbar.addStretch()

        _icon_btn_pad = "6px"
        _icon_btn_size = 14

        def _to_icon_only(btn, svg_name, color):
            btn.setText("")
            _icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, svg_name), color, _icon_btn_size)
            if not _icon.isNull():
                btn.setIcon(_icon)
            btn.setIconSize(QSize(_icon_btn_size, _icon_btn_size))

        self._sc_filter_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "filter.svg"), "Filter", tone="log"
        )
        _to_icon_only(self._sc_filter_btn, "filter.svg", _CLR_TEXT_BTN_LOG)
        self._sc_filter_btn.setCheckable(True)
        self._sc_filter_btn.setStyleSheet(
            log_icon_button_style(checked_variant="blue", padding=_icon_btn_pad)
        )
        self._sc_filter_btn.setToolTip("Filter\nShow only log lines matching a keyword or regex")
        toolbar.addWidget(self._sc_filter_btn)

        self._sc_copy_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "copy.svg"), "Copy", tone="log"
        )
        _to_icon_only(self._sc_copy_btn, "copy.svg", _CLR_TEXT_BTN_LOG)
        self._sc_copy_btn.setStyleSheet(log_icon_button_style(padding=_icon_btn_pad))
        self._sc_copy_btn.setToolTip("Copy\nCopy all current log content to the clipboard")
        toolbar.addWidget(self._sc_copy_btn)

        self._sc_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="log"
        )
        _to_icon_only(self._sc_export_btn, "export.svg", _CLR_TEXT_BTN_LOG)
        self._sc_export_btn.setStyleSheet(log_icon_button_style(padding=_icon_btn_pad))
        self._sc_export_btn.setToolTip("Export\nSave the current log content as a file")
        toolbar.addWidget(self._sc_export_btn)

        self._sc_save_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "save.svg"), "Save", tone="log"
        )
        _to_icon_only(self._sc_save_btn, "save.svg", _CLR_TEXT_BTN_LOG)
        self._sc_save_btn.setCheckable(True)
        self._sc_save_btn.setStyleSheet(
            log_icon_button_style(checked_variant="blue", padding=_icon_btn_pad)
        )
        self._sc_save_btn.setToolTip("Save\nSave logs to a file and keep appending new logs")
        toolbar.addWidget(self._sc_save_btn)

        self._sc_clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear", tone="log"
        )
        _to_icon_only(self._sc_clear_btn, "trash.svg", _CLR_TEXT_BTN_LOG)
        self._sc_clear_btn.setStyleSheet(log_icon_button_style(padding=_icon_btn_pad))
        self._sc_clear_btn.setToolTip("Clear\nClear all log content in the console")
        toolbar.addWidget(self._sc_clear_btn)

        self._sc_scroll_lock_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll", tone="log"
        )
        self._sc_scroll_lock_btn.setText("")
        self._sc_scroll_lock_btn.setIconSize(QSize(_icon_btn_size, _icon_btn_size))
        self._sc_scroll_lock_btn.setCheckable(True)
        self._sc_scroll_lock_btn.setChecked(True)
        self._sc_scroll_lock_btn.setStyleSheet(
            log_icon_button_style(checked_variant="green", padding=_icon_btn_pad)
        )
        self._sc_scroll_lock_btn.setToolTip(
            "Auto-scroll\nAutomatically scroll to the latest log line"
        )
        self._sc_bind_toggle_icon(
            self._sc_scroll_lock_btn,
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"),
            auto_scroll_icon_colors(),
            _icon_btn_size,
        )
        toolbar.addWidget(self._sc_scroll_lock_btn)

        layout.addLayout(toolbar)

        self._sc_filter_row = QWidget()
        self._sc_filter_row.setVisible(False)
        self._sc_filter_row.setStyleSheet(transparent_background_style())
        filter_root = QVBoxLayout(self._sc_filter_row)
        filter_root.setContentsMargins(12, 0, 12, 8)
        filter_root.setSpacing(6)

        fl = QHBoxLayout()
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(8)
        self._sc_filter_input = QLineEdit()
        self._sc_filter_input.setPlaceholderText("Enter keyword or regex, press Enter to filter...")
        self._sc_filter_input.setStyleSheet(filter_input_style())
        fl.addWidget(self._sc_filter_input, 1)

        self._sc_filter_match_label = QLabel("")
        self._sc_filter_match_label.setStyleSheet(filter_match_label_style())
        fl.addWidget(self._sc_filter_match_label)
        filter_root.addLayout(fl)

        opts = QHBoxLayout()
        opts.setContentsMargins(0, 0, 0, 0)
        opts.setSpacing(10)

        self._sc_filter_regex_cb = QCheckBox("Regex")
        self._sc_filter_regex_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_filter_regex_cb.setToolTip("Enable regex matching")
        opts.addWidget(self._sc_filter_regex_cb)

        self._sc_filter_case_cb = QCheckBox("Match Case")
        self._sc_filter_case_cb.setStyleSheet(self._sc_checkbox_style())
        opts.addWidget(self._sc_filter_case_cb)

        self._sc_filter_invert_cb = QCheckBox("Invert")
        self._sc_filter_invert_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_filter_invert_cb.setToolTip("Show non-matching lines")
        opts.addWidget(self._sc_filter_invert_cb)

        opts.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedHeight(14)
        sep.setStyleSheet(separator_style(transparent=True))
        opts.addWidget(sep)

        opts.addSpacing(4)

        before_lbl = QLabel("Before")
        before_lbl.setStyleSheet(small_label_style())
        opts.addWidget(before_lbl)
        self._sc_filter_before_spin = QSpinBox()
        self._sc_filter_before_spin.setRange(0, 999)
        self._sc_filter_before_spin.setValue(0)
        self._sc_filter_before_spin.setFixedSize(56, 24)
        self._sc_filter_before_spin.setToolTip("Show N lines before matched lines")
        self._sc_filter_before_spin.setStyleSheet(compact_spinbox_style(padding="0px 2px"))
        opts.addWidget(self._sc_filter_before_spin)
        before_unit = QLabel("lines")
        before_unit.setStyleSheet(small_label_style(size=11))
        opts.addWidget(before_unit)

        opts.addSpacing(4)

        after_lbl = QLabel("After")
        after_lbl.setStyleSheet(small_label_style())
        opts.addWidget(after_lbl)
        self._sc_filter_after_spin = QSpinBox()
        self._sc_filter_after_spin.setRange(0, 999)
        self._sc_filter_after_spin.setValue(0)
        self._sc_filter_after_spin.setFixedSize(56, 24)
        self._sc_filter_after_spin.setToolTip("Show N lines after matched lines")
        self._sc_filter_after_spin.setStyleSheet(compact_spinbox_style(padding="0px 2px"))
        opts.addWidget(self._sc_filter_after_spin)
        after_unit = QLabel("lines")
        after_unit.setStyleSheet(small_label_style(size=11))
        opts.addWidget(after_unit)

        opts.addStretch()
        filter_root.addLayout(opts)

        layout.addWidget(self._sc_filter_row)

        self._sc_log_edit = QTextEdit()
        self._sc_log_edit.setReadOnly(True)
        self._sc_log_edit.setStyleSheet(log_edit_style() + SERIAL_SCROLLBAR_STYLE)
        self._sc_log_edit.document().setDefaultStyleSheet(log_document_style())
        self._sc_log_edit.document().setMaximumBlockCount(self._sc_max_log_lines)
        layout.addWidget(self._sc_log_edit, 1)

        if self._sc_log_edit.verticalScrollBar():
            self._sc_log_edit.verticalScrollBar().valueChanged.connect(self._sc_on_user_scroll)

        self._sc_status_bar = self._build_sc_status_bar()
        layout.addWidget(self._sc_status_bar)

        frame.mousePressEvent = lambda event: self._sc_on_primary_panel_clicked(event)
        self._sc_log_edit.mousePressEvent = lambda event, orig=self._sc_log_edit.mousePressEvent: (
            self._sc_on_primary_panel_clicked(event), orig(event)
        )

        return frame

    # --- send area ---


    def _sc_on_add_log_panel(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _AddLogPanelDialog
        if len(self._sc_extra_log_panels) >= 3:
            self._sc_append_system("[WARN] Maximum 4 LOG panels supported", force_primary=True)
            return
        dlg = _AddLogPanelDialog(panel_index=len(self._sc_extra_log_panels) + 2, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        panel_info = dlg.get_config()

        if panel_info.get("independent_window", False):
            self._sc_open_independent_window(panel_info)
            return

        panel = self._build_extra_log_panel(panel_info)
        self._sc_extra_log_panels.append(panel)
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(True)
        self._sc_append_system(
            f"[INFO] New LOG panel: {panel_info.get('title', 'Log')} "
            f"({panel_info.get('port', 'N/A')} @ {panel_info.get('baudrate', 'N/A')})",
            force_primary=True,
        )
        if panel_info.get("auto_connect", False):
            self._sc_extra_panel_connect(panel)

    def _sc_open_independent_window(self, panel_info):
        from ui.modules.serialCom_module.serialCom_module_frame import _IndependentSerialWindow
        win = _IndependentSerialWindow(panel_info, parent=None)
        if not hasattr(self, "_sc_independent_windows"):
            self._sc_independent_windows = []
        self._sc_independent_windows.append(win)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.destroyed.connect(lambda: self._sc_independent_windows.remove(win) if win in self._sc_independent_windows else None)
        win.show()
        self._sc_append_system(
            f"[INFO] Independent window opened: {panel_info.get('title', 'Log')} "
            f"({panel_info.get('port', 'N/A')} @ {panel_info.get('baudrate', 'N/A')})",
            force_primary=True,
        )

    def _sc_on_remove_log_panel(self):
        if not self._sc_extra_log_panels:
            return
        panel = self._sc_extra_log_panels.pop()
        self._sc_extra_panel_disconnect(panel)
        panel["frame"].setParent(None)
        panel["frame"].deleteLater()
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(len(self._sc_extra_log_panels) > 0)
        self._sc_append_system("[INFO] LOG panel removed", force_primary=True)

    def _sc_relayout_log_panels(self):
        while self._sc_log_grid.count():
            item = self._sc_log_grid.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        self._sc_log_grid.setRowStretch(0, 0)
        self._sc_log_grid.setRowStretch(1, 0)
        self._sc_log_grid.setColumnStretch(0, 0)
        self._sc_log_grid.setColumnStretch(1, 0)

        total = 1 + len(self._sc_extra_log_panels)

        if total == 1:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
        elif total == 2:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
        elif total == 3:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[1]["frame"], 1, 0)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
            self._sc_log_grid.setRowStretch(0, 1)
            self._sc_log_grid.setRowStretch(1, 1)
        elif total == 4:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[1]["frame"], 1, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[2]["frame"], 1, 1)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
            self._sc_log_grid.setRowStretch(0, 1)
            self._sc_log_grid.setRowStretch(1, 1)

        self._sc_log_area.show()
        for p in self._sc_extra_log_panels:
            p["frame"].show()

    def _build_extra_log_panel(self, config):
        frame = QFrame()
        frame.setObjectName("scLogFrame")
        frame.setStyleSheet(log_frame_style(with_border=True))
        frame.setContextMenuPolicy(Qt.CustomContextMenu)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 4, 6, 2)
        toolbar.setSpacing(4)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), log_title_icon_color(), 14)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(14, 14))
        icon_label.setFixedSize(16, 16)
        icon_label.setStyleSheet(transparent_background_style())
        toolbar.addWidget(icon_label)

        title_text = config.get("title", "Serial Log")
        title = QLabel(title_text)
        title.setStyleSheet(log_title_style())
        toolbar.addWidget(title)

        toolbar.addStretch()

        filter_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "filter.svg"), "Filter", tone="log"
        )
        filter_btn.setCheckable(True)
        toolbar.addWidget(filter_btn)

        copy_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "copy.svg"), "Copy", tone="log"
        )
        toolbar.addWidget(copy_btn)

        export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="log"
        )
        toolbar.addWidget(export_btn)

        clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear", tone="log"
        )
        toolbar.addWidget(clear_btn)

        scroll_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll", tone="log"
        )
        scroll_btn.setCheckable(True)
        scroll_btn.setChecked(True)
        scroll_btn.setStyleSheet(auto_scroll_button_style())
        self._sc_bind_toggle_icon(
            scroll_btn,
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"),
            auto_scroll_icon_colors(),
            11,
        )
        toolbar.addWidget(scroll_btn)

        layout.addLayout(toolbar)

        filter_row = QWidget()
        filter_row.setVisible(False)
        filter_row.setStyleSheet(transparent_background_style())
        filter_layout = QHBoxLayout(filter_row)
        filter_layout.setContentsMargins(6, 0, 6, 4)
        filter_layout.setSpacing(6)
        filter_input = QLineEdit()
        filter_input.setPlaceholderText("Enter keyword or regex...")
        filter_input.setStyleSheet(filter_input_style())
        filter_layout.addWidget(filter_input, 1)
        filter_match_label = QLabel("")
        filter_match_label.setStyleSheet(filter_match_label_style())
        filter_layout.addWidget(filter_match_label)
        layout.addWidget(filter_row)

        log_edit = QTextEdit()
        log_edit.setReadOnly(True)
        log_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        log_edit.setStyleSheet(log_edit_style(padding="6px 8px") + SERIAL_SCROLLBAR_STYLE)
        log_edit.document().setDefaultStyleSheet(log_document_style())
        log_edit.document().setMaximumBlockCount(5000)
        layout.addWidget(log_edit, 1)

        status_bar = QFrame()
        status_bar.setObjectName("scStatusBar")
        status_bar.setFixedHeight(30)
        status_bar.setStyleSheet(status_bar_style())
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(12, 2, 12, 2)
        sb_layout.setSpacing(16)

        port_label = QLabel(f"Port: {config.get('port', 'Unconnected')}")
        port_label.setStyleSheet(status_label_style("error", compact=True))
        sb_layout.addWidget(port_label)

        baud_label = QLabel(f"Baud rate: {config.get('baudrate', '-')}")
        baud_label.setStyleSheet(status_label_style("muted"))
        sb_layout.addWidget(baud_label)

        rx_label = QLabel("RX: 0 B")
        rx_label.setStyleSheet(status_label_style("rx", compact=True))
        sb_layout.addWidget(rx_label)

        tx_label = QLabel("TX: 0 B")
        tx_label.setStyleSheet(status_label_style("tx", compact=True))
        sb_layout.addWidget(tx_label)

        sb_layout.addStretch()
        layout.addWidget(status_bar)

        panel = {
            "frame": frame,
            "log_edit": log_edit,
            "clear_btn": clear_btn,
            "scroll_btn": scroll_btn,
            "filter_btn": filter_btn,
            "filter_row": filter_row,
            "filter_input": filter_input,
            "filter_match_label": filter_match_label,
            "copy_btn": copy_btn,
            "export_btn": export_btn,
            "port_label": port_label,
            "baud_label": baud_label,
            "rx_label": rx_label,
            "tx_label": tx_label,
            "title_label": title,
            "config": config,
            "conn": None,
            "read_thread": None,
            "read_worker": None,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "auto_scroll": True,
            "all_logs": [],
            "pending_html": [],
            "session_id": None,
        }

        clear_btn.clicked.connect(lambda _=None, p=panel: self._sc_extra_panel_clear(p))
        scroll_btn.clicked.connect(lambda checked, p=panel: self._sc_extra_panel_toggle_scroll(p, checked))
        filter_btn.clicked.connect(lambda checked, p=panel: self._sc_extra_panel_toggle_filter(p, checked))
        copy_btn.clicked.connect(lambda _=None, p=panel: self._sc_extra_panel_copy(p))
        export_btn.clicked.connect(lambda _=None, p=panel: self._sc_extra_panel_export(p))
        filter_input.returnPressed.connect(lambda p=panel: self._sc_extra_panel_apply_filter(p))

        frame.customContextMenuRequested.connect(
            lambda pos, p=panel: self._sc_extra_panel_context_menu(p, frame.mapToGlobal(pos))
        )
        log_edit.customContextMenuRequested.connect(
            lambda pos, p=panel: self._sc_extra_panel_context_menu(p, log_edit.mapToGlobal(pos))
        )
        frame.mousePressEvent = lambda event, p=panel: self._sc_on_log_panel_clicked(p, event)
        log_edit.mouseReleaseEvent = lambda event, p=panel, orig=log_edit.mouseReleaseEvent: (
            self._sc_on_log_panel_clicked(p, event), orig(event)
        )

        if log_edit.verticalScrollBar():
            log_edit.verticalScrollBar().valueChanged.connect(
                lambda val, p=panel: self._sc_extra_panel_on_scroll(p, val)
            )

        return panel

    def _sc_extra_panel_clear(self, panel):
        panel["all_logs"].clear()
        panel["pending_html"].clear()
        panel["log_edit"].clear()
        panel["rx_bytes"] = 0
        panel["tx_bytes"] = 0
        panel["rx_label"].setText("RX: 0 B")
        panel["tx_label"].setText("TX: 0 B")
        panel["auto_scroll"] = True
        panel["scroll_btn"].setChecked(True)

    def _sc_extra_panel_toggle_scroll(self, panel, checked):
        panel["auto_scroll"] = checked
        if checked:
            sb = panel["log_edit"].verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def _sc_extra_panel_toggle_filter(self, panel, checked):
        panel["filter_row"].setVisible(checked)
        if not checked:
            panel["filter_input"].clear()
            panel["filter_match_label"].setText("")
            self._sc_extra_panel_show_all_logs(panel)
        else:
            panel["filter_input"].setFocus()

    def _sc_extra_panel_copy(self, panel):
        from PySide6.QtWidgets import QApplication
        text = panel["log_edit"].toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._sc_extra_panel_append_log(panel, "[INFO] Log copied to clipboard", _CLR_TEXT_INFO)

    def _sc_extra_panel_export(self, panel):
        from PySide6.QtWidgets import QFileDialog
        title_text = panel.get("title_label")
        default_name = title_text.text() if title_text else "serial_log"
        default_name = default_name.replace(" ", "_").lower()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", f"{default_name}.log", "Log Files (*.log);;Text Files (*.txt);;All (*.*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(panel["log_edit"].toPlainText())
            self._sc_extra_panel_append_log(panel, f"[INFO] Log exported: {file_path}", _CLR_TEXT_INFO)
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Export failed: {e}", extra_log_error_color())

    def _sc_extra_panel_apply_filter(self, panel):
        keyword = panel["filter_input"].text().strip()
        if not keyword:
            self._sc_extra_panel_show_all_logs(panel)
            panel["filter_match_label"].setText("")
            return
        log_edit = panel["log_edit"]
        log_edit.clear()
        count = 0
        for msg, html in panel["all_logs"]:
            if keyword.lower() in msg.lower():
                log_edit.append(html)
                count += 1
        panel["filter_match_label"].setText(f"{count} match{'es' if count != 1 else ''}")
        if panel["auto_scroll"]:
            sb = log_edit.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def _sc_extra_panel_show_all_logs(self, panel):
        log_edit = panel["log_edit"]
        log_edit.clear()
        for _, html in panel["all_logs"]:
            log_edit.append(html)
        if panel["auto_scroll"]:
            sb = log_edit.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def _sc_extra_panel_on_scroll(self, panel, value):
        sb = panel["log_edit"].verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and panel["auto_scroll"]:
                panel["auto_scroll"] = False
                panel["scroll_btn"].setChecked(False)
            elif at_bottom and not panel["auto_scroll"]:
                panel["auto_scroll"] = True
                panel["scroll_btn"].setChecked(True)

    def _sc_on_primary_panel_clicked(self, event):
        if self._sc_active_log_panel_index != 0:
            self._sc_active_log_panel_index = 0
            self._sc_active_session_id = "primary"
            self._sc_session_manager.set_active_session("primary")
            self._sc_update_panel_focus_style()

    def _sc_on_log_panel_clicked(self, panel, event):
        try:
            idx = self._sc_extra_log_panels.index(panel) + 1
        except ValueError:
            return
        if self._sc_active_log_panel_index != idx:
            self._sc_active_log_panel_index = idx
            session_id = panel.get("session_id")
            if session_id:
                self._sc_active_session_id = session_id
                self._sc_session_manager.set_active_session(session_id)
            self._sc_update_panel_focus_style()

    def _sc_update_panel_focus_style(self):
        active_border = f"2px solid {_CLR_CONNECT_FG}"
        inactive_border = f"2px solid {_CLR_BG_LOG}"

        if self._sc_active_log_panel_index == 0:
            self._sc_log_area.setStyleSheet(
                f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {active_border}; border-radius: 6px; }}"
            )
        else:
            self._sc_log_area.setStyleSheet(
                f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {inactive_border}; border-radius: 6px; }}"
            )

        for i, p in enumerate(self._sc_extra_log_panels):
            if self._sc_active_log_panel_index == i + 1:
                p["frame"].setStyleSheet(
                    f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {active_border}; border-radius: 6px; }}"
                )
            else:
                p["frame"].setStyleSheet(
                    f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {inactive_border}; border-radius: 6px; }}"
                )

    def _sc_extra_panel_context_menu(self, panel, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {_CLR_BG_CARD}; border: 1px solid {_CLR_BORDER_HOVER};
                border-radius: 6px; padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 20px; color: {_CLR_INPUT_TEXT}; font-size: 12px; font-family: {_UI_FONT};
            }}
            QMenu::item:selected {{
                background-color: {_CLR_BORDER}; color: #ffffff;
            }}
            QMenu::separator {{
                height: 1px; background: {_CLR_BORDER}; margin: 4px 8px;
            }}
        """)

        is_connected = False
        if DEBUG_MOCK:
            session_id = panel.get("session_id")
            if session_id:
                session = self._sc_session_manager.get_session(session_id)
                is_connected = session is not None and session.connected
            else:
                is_connected = panel.get("port_label") and "MOCK" in panel["port_label"].text()
        else:
            is_connected = panel.get("conn") is not None and panel["conn"].is_open

        if is_connected:
            disconnect_act = QAction("Disconnect", self)
            disconnect_act.triggered.connect(lambda: self._sc_extra_panel_do_disconnect(panel))
            menu.addAction(disconnect_act)
        else:
            connect_act = QAction("Connect", self)
            connect_act.triggered.connect(lambda: self._sc_extra_panel_connect(panel))
            menu.addAction(connect_act)

        menu.addSeparator()

        settings_act = QAction("Settings...", self)
        settings_act.triggered.connect(lambda: self._sc_extra_panel_settings(panel))
        menu.addAction(settings_act)

        menu.addSeparator()

        remove_act = QAction("Remove Panel", self)
        remove_act.triggered.connect(lambda: self._sc_remove_specific_panel(panel))
        menu.addAction(remove_act)

        menu.exec(global_pos)

    def _sc_extra_panel_do_disconnect(self, panel):
        self._sc_extra_panel_disconnect(panel)
        panel["port_label"].setText("Port: Disconnected")
        panel["port_label"].setStyleSheet(status_label_style("error", compact=True))
        self._sc_extra_panel_append_log(panel, "[INFO] Disconnected", _CLR_TEXT_INFO)

    def _sc_extra_panel_settings(self, panel):
        from ui.modules.serialCom_module.serialCom_module_frame import _PanelSettingsDialog
        dlg = _PanelSettingsDialog(panel["config"], parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        new_config = dlg.get_config()

        if DEBUG_MOCK:
            session_id = panel.get("session_id")
            session = self._sc_session_manager.get_session(session_id) if session_id else None
            was_connected = session is not None and session.connected
        else:
            was_connected = panel.get("conn") is not None and panel["conn"].is_open
        if was_connected:
            self._sc_extra_panel_do_disconnect(panel)

        panel["config"] = new_config
        panel["title_label"].setText(new_config.get("title", "Serial Log"))
        panel["baud_label"].setText(f"Baud rate: {new_config.get('baudrate', '-')}")
        panel["port_label"].setText(f"Port: {new_config.get('port', 'Unconnected')}")
        panel["port_label"].setStyleSheet(status_label_style("error", compact=True))

        self._sc_extra_panel_append_log(
            panel,
            f"[INFO] Settings updated: {new_config.get('port', 'N/A')} @ {new_config.get('baudrate', 'N/A')}",
            _CLR_TEXT_INFO,
        )

        if new_config.get("auto_connect", False):
            self._sc_extra_panel_connect(panel)

    def _sc_remove_specific_panel(self, panel):
        if panel not in self._sc_extra_log_panels:
            return
        idx = self._sc_extra_log_panels.index(panel)
        self._sc_extra_log_panels.remove(panel)
        self._sc_extra_panel_disconnect(panel)
        panel["frame"].setParent(None)
        panel["frame"].deleteLater()
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(len(self._sc_extra_log_panels) > 0)
        if self._sc_active_log_panel_index == idx + 1:
            self._sc_active_log_panel_index = 0
            self._sc_active_session_id = "primary"
            self._sc_session_manager.set_active_session("primary")
            self._sc_update_panel_focus_style()
        elif self._sc_active_log_panel_index > idx + 1:
            self._sc_active_log_panel_index -= 1
        self._sc_append_system("[INFO] LOG panel removed", force_primary=True)

    def _sc_extra_panel_connect(self, panel):
        config = panel["config"]
        port = config.get("port", "")
        baudrate = config.get("baudrate", 115200)

        if not port:
            return

        panel_idx = self._sc_extra_log_panels.index(panel) if panel in self._sc_extra_log_panels else 0
        session_id = f"extra_{panel_idx}_{port}"
        panel["session_id"] = session_id

        session = self._sc_session_manager.get_session(session_id)
        if session is None:
            session = self._sc_session_manager.create_session(
                session_id=session_id,
                display_name=config.get("title", f"LOG-{panel_idx + 2}"),
                auto_activate=False,
            )
        session.configure(
            port=port, baudrate=baudrate,
            bytesize=config.get("databit", 8),
            stopbits={"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}.get(
                config.get("stopbit", "1"), serial.STOPBITS_ONE
            ),
            parity={"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}.get(
                config.get("parity", "None"), serial.PARITY_NONE
            ),
            xonxoff=(config.get("flow", "None") == "XON/XOFF"),
            rtscts=(config.get("flow", "None") == "RTS/CTS"),
        )

        if DEBUG_MOCK:
            panel["conn"] = None
            session._connected = True
            panel["port_label"].setText("Port: MOCK")
            panel["port_label"].setStyleSheet(status_label_style("connected", include_font=True))
            self._sc_extra_panel_append_log(panel, "[INFO] Mock connected", _CLR_TEXT_INFO)
            return

        try:
            databit = config.get("databit", 8)
            stopbit_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
            stopbits = stopbit_map.get(config.get("stopbit", "1"), serial.STOPBITS_ONE)
            parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
                          "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
            parity = parity_map.get(config.get("parity", "None"), serial.PARITY_NONE)
            flow = config.get("flow", "None")

            conn = serial.Serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=stopbits, parity=parity,
                xonxoff=(flow == "XON/XOFF"), rtscts=(flow == "RTS/CTS"),
                timeout=0.1,
            )
            panel["conn"] = conn
            session._serial_conn = conn
            session._connected = True
            panel["port_label"].setText(f"Port: {port}")
            panel["port_label"].setStyleSheet(status_label_style("connected", include_font=True))
            self._sc_extra_panel_append_log(panel, f"[INFO] Connected: {port} @ {baudrate}", _CLR_TEXT_INFO)
            self._sc_extra_panel_start_read(panel)
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Connection failed: {e}", extra_log_error_color())

    def _sc_extra_panel_disconnect(self, panel):
        if panel.get("read_worker"):
            panel["read_worker"].stop()
        if panel.get("read_thread") and panel["read_thread"].isRunning():
            panel["read_thread"].quit()
            panel["read_thread"].wait(2000)
        panel["read_thread"] = None
        panel["read_worker"] = None
        try:
            if panel["conn"] and panel["conn"].is_open:
                panel["conn"].close()
        except Exception:
            pass
        panel["conn"] = None
        session_id = panel.get("session_id")
        if session_id:
            self._sc_session_manager.remove_session(session_id)
            panel["session_id"] = None

    def _sc_extra_panel_start_read(self, panel):
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialReadWorker
        if panel["conn"] is None or not panel["conn"].is_open:
            return
        worker = _SerialReadWorker(panel["conn"])
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.data_received.connect(lambda data, p=panel: self._sc_extra_panel_on_data(p, data))
        worker.error.connect(lambda err, p=panel: self._sc_extra_panel_append_log(p, f"[ERROR] {err}", _CLR_ERROR))
        panel["read_thread"] = thread
        panel["read_worker"] = worker
        thread.start()

    def _sc_extra_panel_on_data(self, panel, data: bytes):
        panel["rx_bytes"] += len(data)
        panel["rx_label"].setText(self._sc_format_bytes("RX", panel["rx_bytes"]))
        display = data.decode("utf-8", errors="replace")
        for line in display.splitlines():
            if line.strip():
                self._sc_extra_panel_append_log(panel, f"[RX] {line}", _CLR_RX)

    def _sc_extra_panel_append_log(self, panel, message, color=_CLR_TEXT_BODY):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> '
        html = f'{ts_html}<span style="color:{color};">{escaped}</span>'
        panel["all_logs"].append((message, html))
        panel["pending_html"].append(html)

    def _sc_flush_extra_panels(self):
        for panel in self._sc_extra_log_panels:
            if not panel["pending_html"]:
                continue
            batch = panel["pending_html"][:200]
            panel["pending_html"] = panel["pending_html"][200:]
            log_edit = panel["log_edit"]
            log_edit.setUpdatesEnabled(False)
            cursor = log_edit.textCursor()
            cursor.beginEditBlock()
            for html in batch:
                log_edit.append(html)
            cursor.endEditBlock()
            log_edit.setUpdatesEnabled(True)
            if panel["auto_scroll"]:
                sb = log_edit.verticalScrollBar()
                if sb:
                    sb.setValue(sb.maximum())

    def _sc_on_sidebar_toggle(self, checked):
        self._sc_sidebar_visible = checked
        self._sc_sidebar_widget.setVisible(checked)
        if checked:
            sizes = self._sc_body_splitter.sizes()
            if sizes and sizes[0] < self._sc_sidebar_min_width:
                center_width = max(sizes[1], 600) if len(sizes) > 1 else 600
                self._sc_body_splitter.setSizes([self._sc_sidebar_default_width, center_width])

    def _sc_open_settings_dialog(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialSettingsDialog
        dlg = _SerialSettingsDialog(self)

        dlg.port_combo.clear()
        for i in range(self._sc_port_combo.count()):
            dlg.port_combo.addItem(self._sc_port_combo.itemText(i))
        dlg.port_combo.setCurrentIndex(self._sc_port_combo.currentIndex())

        dlg.baud_combo.setCurrentText(self._sc_baud_combo.currentText())

        dlg.databit_combo.setCurrentText(self._sc_databit_combo.currentText())
        dlg.flow_combo.setCurrentText(self._sc_flow_combo.currentText())
        dlg.stopbit_combo.setCurrentText(self._sc_stopbit_combo.currentText())
        dlg.parity_combo.setCurrentText(self._sc_parity_combo.currentText())

        dlg.rx_hex_toggle.set_value("HEX" if self._sc_rx_display_hex else "ASCII")
        dlg.show_time_cb.setChecked(self._sc_show_timestamp)
        dlg.rx_use_ntp_cb.setChecked(self._sc_use_ntp)
        dlg.rx_max_lines_spin.setValue(getattr(self, '_sc_max_log_lines', 10000))

        dlg.tx_hex_toggle.set_value("HEX" if self._sc_tx_display_hex else "ASCII")
        idx = self._sc_ending_combo.currentIndex()
        if 0 <= idx < dlg.ending_combo.count():
            dlg.ending_combo.setCurrentIndex(idx)
        dlg.show_send_cb.setChecked(self._sc_show_send)
        dlg.line_by_line_cb.setChecked(self._sc_line_by_line)

        dlg.log_auto_save_cb.setChecked(getattr(self, '_sc_log_auto_save', False))
        dlg.log_save_path_edit.setText(getattr(self, '_sc_log_save_path', ''))

        dlg.display_font_combo.setCurrentText(getattr(self, '_sc_display_font', 'Consolas'))
        dlg.display_font_size_spin.setValue(getattr(self, '_sc_display_font_size', 11))
        dlg.display_auto_scroll_cb.setChecked(self._sc_auto_scroll)
        dlg.display_word_wrap_cb.setChecked(getattr(self, '_sc_word_wrap', True))

        dlg.auto_detect_enable_cb.setChecked(self._sc_auto_detect_cb.isChecked())
        dlg.auto_detect_runtime_cb.setChecked(self._sc_auto_baud_monitor.runtime_redetect_enabled)
        dlg.auto_detect_candidates_edit.setText(
            ", ".join(str(b) for b in self._sc_auto_baud_monitor._config["candidate_baudrates"])
        )
        dlg.auto_detect_lock_spin.setValue(self._sc_auto_baud_monitor._config["lock_threshold"])
        dlg.auto_detect_bad_spin.setValue(self._sc_auto_baud_monitor._config["bad_threshold"])
        dlg.auto_detect_bad_windows_spin.setValue(self._sc_auto_baud_monitor._config["bad_windows_to_suspect"])
        dlg.auto_detect_suspect_windows_spin.setValue(self._sc_auto_baud_monitor._config["suspect_windows_to_scan"])
        dlg.auto_detect_window_ms_spin.setValue(self._sc_auto_baud_monitor._config["monitor_window_max_time_ms"])
        dlg.auto_detect_cooldown_spin.setValue(self._sc_auto_baud_monitor._config["switch_cooldown_ms"])
        dlg.auto_detect_margin_spin.setValue(self._sc_auto_baud_monitor._config["switch_score_margin"])
        dlg.auto_detect_confirm_spin.setValue(self._sc_auto_baud_monitor._config["confirm_scan_rounds"])

        if dlg.exec() == QDialog.Accepted:
            self._sc_port_combo.setCurrentIndex(dlg.port_combo.currentIndex())
            self._sc_baud_combo.setCurrentText(dlg.baud_combo.currentText())
            self._sc_databit_combo.setCurrentText(dlg.databit_combo.currentText())
            self._sc_flow_combo.setCurrentText(dlg.flow_combo.currentText())
            self._sc_stopbit_combo.setCurrentText(dlg.stopbit_combo.currentText())
            self._sc_parity_combo.setCurrentText(dlg.parity_combo.currentText())

            rx_val = dlg.rx_hex_toggle.value()
            self._sc_rx_display_hex = rx_val == "HEX"
            self._sc_rx_toggle.set_value(rx_val)

            self._sc_show_timestamp = dlg.show_time_cb.isChecked()
            self._sc_rx_show_time_cb.setChecked(self._sc_show_timestamp)
            self._sc_apply_ntp_setting(dlg.rx_use_ntp_cb.isChecked())
            self._sc_apply_max_log_lines(dlg.rx_max_lines_spin.value())

            tx_val = dlg.tx_hex_toggle.value()
            self._sc_tx_display_hex = tx_val == "HEX"
            self._sc_tx_toggle.set_value(tx_val)

            ending_idx = dlg.ending_combo.currentIndex()
            self._sc_ending_combo.setCurrentIndex(ending_idx)

            self._sc_show_send_cb.setChecked(dlg.show_send_cb.isChecked())
            self._sc_line_by_line_cb.setChecked(dlg.line_by_line_cb.isChecked())

            self._sc_log_auto_save = dlg.log_auto_save_cb.isChecked()
            self._sc_log_save_path = dlg.log_save_path_edit.text()
            if self._sc_log_auto_save and self._serial_connected:
                if self._sc_log_file_handle is None:
                    self._sc_start_auto_save()
            elif not self._sc_log_auto_save:
                self._sc_stop_auto_save()

            font_family = dlg.display_font_combo.currentText()
            font_size = dlg.display_font_size_spin.value()
            if (font_family != getattr(self, '_sc_display_font', 'Consolas')
                    or font_size != getattr(self, '_sc_display_font_size', 11)):
                self._sc_display_font = font_family
                self._sc_display_font_size = font_size
                self._sc_log_edit.setStyleSheet(
                    log_edit_style(
                        font_family=font_family,
                        font_size=font_size,
                        padding="4px 6px",
                        include_line_height=True,
                    ) + SERIAL_SCROLLBAR_STYLE
                )

            self._sc_auto_scroll = dlg.display_auto_scroll_cb.isChecked()
            self._sc_scroll_lock_btn.setChecked(self._sc_auto_scroll)

            self._sc_word_wrap = dlg.display_word_wrap_cb.isChecked()
            from PySide6.QtWidgets import QTextEdit as _QTE
            self._sc_log_edit.setLineWrapMode(
                _QTE.WidgetWidth if self._sc_word_wrap else _QTE.NoWrap
            )

            self._sc_apply_auto_detect_settings(dlg)

    def _sc_apply_max_log_lines(self, value):
        value = max(500, min(int(value), self._SC_MAX_LOG_LINES_LIMIT))
        if value == getattr(self, '_sc_max_log_lines', self._SC_MAX_LOG_LINES_DEFAULT):
            return
        self._sc_max_log_lines = value
        self._sc_log_edit.document().setMaximumBlockCount(value)
        if len(self._sc_all_logs) > value:
            self._sc_all_logs = self._sc_all_logs[-value:]
            if not self._sc_is_filter_active():
                self._sc_rebuild_log_view()

    def _sc_apply_auto_detect_settings(self, dlg):
        enable = dlg.auto_detect_enable_cb.isChecked()
        runtime = dlg.auto_detect_runtime_cb.isChecked()

        candidates_text = dlg.auto_detect_candidates_edit.text().strip()
        candidates = []
        for part in candidates_text.replace(";", ",").split(","):
            part = part.strip()
            if part.isdigit():
                candidates.append(int(part))
        if not candidates:
            candidates = list(AUTO_BAUD_CONFIG["candidate_baudrates"])

        config = dict(self._sc_auto_baud_monitor._config)
        config["candidate_baudrates"] = candidates
        config["lock_threshold"] = dlg.auto_detect_lock_spin.value()
        config["bad_threshold"] = dlg.auto_detect_bad_spin.value()
        config["bad_windows_to_suspect"] = dlg.auto_detect_bad_windows_spin.value()
        config["suspect_windows_to_scan"] = dlg.auto_detect_suspect_windows_spin.value()
        config["monitor_window_max_time_ms"] = dlg.auto_detect_window_ms_spin.value()
        config["switch_cooldown_ms"] = dlg.auto_detect_cooldown_spin.value()
        config["switch_score_margin"] = dlg.auto_detect_margin_spin.value()
        config["confirm_scan_rounds"] = dlg.auto_detect_confirm_spin.value()

        self._sc_auto_baud_monitor.update_config(config)
        self._sc_auto_baud_monitor.runtime_redetect_enabled = runtime

        if enable != self._sc_auto_detect_cb.isChecked():
            self._sc_auto_detect_cb.setChecked(enable)


    def _sc_start_temp_log(self):
        self._sc_close_temp_log(delete=True)
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), "kk_serial_logs")
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except OSError:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"sc_temp_{ts}.txt"
        file_path = os.path.join(temp_dir, filename)
        try:
            self._sc_log_temp_handle = open(file_path, "a", encoding="utf-8")
            self._sc_log_temp_path = file_path
        except OSError:
            self._sc_log_temp_handle = None
            self._sc_log_temp_path = None

    def _sc_close_temp_log(self, delete: bool = False):
        if self._sc_log_temp_handle is not None:
            try:
                self._sc_log_temp_handle.close()
            except OSError:
                pass
            self._sc_log_temp_handle = None
        if delete and self._sc_log_temp_path:
            try:
                os.remove(self._sc_log_temp_path)
            except OSError:
                pass
            self._sc_log_temp_path = None

    def _sc_start_auto_save(self):
        if self._sc_log_file_handle is not None:
            return
        save_dir = getattr(self, '_sc_log_save_path', '')
        if not save_dir:
            save_dir = self._sc_fallback_dir()
        try:
            os.makedirs(save_dir, exist_ok=True)
        except OSError:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        port = getattr(self, '_serial_port', '') or 'unknown'
        port_safe = re.sub(r'[^\w\-.]', '_', port)
        filename = f"serial_log_{port_safe}_{ts}.txt"
        file_path = os.path.join(save_dir, filename)
        try:
            self._sc_log_file_handle = open(file_path, "a", encoding="utf-8")
            self._sc_log_file_path = file_path
            self._sc_append_system(f"[INFO] Auto-save started: {file_path}", force_primary=True)
        except OSError:
            self._sc_log_file_handle = None
            self._sc_log_file_path = None

    def _sc_stop_auto_save(self):
        if self._sc_log_file_handle is not None:
            try:
                self._sc_log_file_handle.close()
            except OSError:
                pass
            self._sc_log_file_handle = None

    def _sc_write_to_log_files(self, raw: str):
        for fh_attr in ("_sc_log_temp_handle", "_sc_log_file_handle"):
            fh = getattr(self, fh_attr, None)
            if fh is not None:
                try:
                    fh.write(raw + "\n")
                    fh.flush()
                except OSError:
                    try:
                        fh.close()
                    except OSError:
                        pass
                    setattr(self, fh_attr, None)
        save_fh = getattr(self, "_sc_save_handle", None)
        if save_fh is not None:
            line = raw if self._sc_save_keep_timestamp else self._sc_strip_timestamp(raw)
            try:
                save_fh.write(line + "\n")
                save_fh.flush()
            except OSError:
                try:
                    save_fh.close()
                except OSError:
                    pass
                self._sc_save_handle = None
                if hasattr(self, "_sc_save_btn"):
                    self._sc_save_btn.setChecked(False)

    # --- NTP network time ---

    def _sc_start_ntp_sync(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _NtpSyncWorker
        if self._sc_ntp_thread is not None:
            return
        self._sc_ntp_synced = False
        worker = _NtpSyncWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.synced.connect(self._sc_on_ntp_synced)
        worker.failed.connect(self._sc_on_ntp_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._sc_ntp_thread = thread
        self._sc_ntp_worker = worker
        thread.start()

    def _sc_stop_ntp_sync(self):
        worker = getattr(self, "_sc_ntp_worker", None)
        thread = getattr(self, "_sc_ntp_thread", None)
        self._sc_ntp_worker = None
        self._sc_ntp_thread = None
        self._sc_ntp_synced = False
        if worker is not None:
            worker.stop()
        if thread is not None:
            thread.quit()
            thread.wait(2000)

    def _sc_on_ntp_synced(self, offset: float, rtt: float):
        self._sc_ntp_offset = offset
        self._sc_ntp_synced = True
        if hasattr(self, "_sc_append_system"):
            self._sc_append_system(
                f"[INFO] NTP synced: offset={offset * 1000:.1f} ms, rtt={rtt * 1000:.1f} ms",
                force_primary=True,
            )

    def _sc_on_ntp_failed(self, reason: str):
        self._sc_ntp_synced = False
        logger.warning("NTP sync failed: %s", reason)
        if hasattr(self, "_sc_append_system"):
            self._sc_append_system(f"[WARN] NTP sync failed: {reason}", force_primary=True)

    def _sc_ntp_timestamp(self):
        if not (self._sc_use_ntp and self._sc_ntp_synced):
            return ""
        ntp_dt = datetime.fromtimestamp(time.time() + self._sc_ntp_offset)
        return ntp_dt.strftime("%H:%M:%S.%f")[:-3]

    def _sc_apply_ntp_setting(self, enabled: bool):
        self._sc_use_ntp = bool(enabled)
        if self._sc_use_ntp:
            self._sc_start_ntp_sync()
        else:
            self._sc_stop_ntp_sync()

    def _sc_append_log(self, message: str, color: str = _CLR_TEXT_BODY):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3] if self._sc_show_timestamp else ""
        ntp_ts = self._sc_ntp_timestamp()
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> ' if ts else ""
        ntp_html = (
            f'<span style="color:{_CLR_TEXT_ACCENT};">[NTP]</span> '
            f'<span style="color:{_CLR_TEXT_TIME};">{ntp_ts}</span> '
            if ntp_ts else ""
        )
        html = f'{ts_html}{ntp_html}<span style="color:{color};">{escaped}</span>'
        prefix = ts
        if ntp_ts:
            prefix = f"{prefix} [NTP] {ntp_ts}" if prefix else f"[NTP] {ntp_ts}"
        raw = f"{prefix} {message}" if prefix else message
        self._sc_all_logs.append((raw, html))
        if len(self._sc_all_logs) > self._sc_max_log_lines:
            self._sc_all_logs = self._sc_all_logs[-self._sc_max_log_lines:]
        self._sc_write_to_log_files(raw)
        if self._sc_is_filter_active():
            self._sc_filter_dirty = True
        else:
            self._sc_pending_html.append(html)

    def _sc_flush_pending_logs(self):
        if self._sc_is_filter_active():
            if getattr(self, '_sc_filter_dirty', False):
                self._sc_filter_dirty = False
                before = self._sc_filter_applied_before
                after = self._sc_filter_applied_after
                if before == 0 and after == 0:
                    self._sc_flush_filter_incremental()
                else:
                    self._sc_apply_filter()
        elif self._sc_pending_html:
            batch = self._sc_pending_html[:200]
            self._sc_pending_html = self._sc_pending_html[200:]
            self._sc_log_edit.setUpdatesEnabled(False)
            cursor = self._sc_log_edit.textCursor()
            cursor.beginEditBlock()
            for html in batch:
                self._sc_log_edit.append(html)
            cursor.endEditBlock()
            self._sc_log_edit.setUpdatesEnabled(True)
            if self._sc_auto_scroll:
                self._sc_scroll_to_bottom()
        self._sc_flush_extra_panels()

    def _sc_flush_filter_incremental(self):
        pattern = self._sc_filter_applied_pattern
        if not pattern:
            return
        use_regex = self._sc_filter_applied_use_regex
        case_sensitive = self._sc_filter_applied_case
        invert = self._sc_filter_applied_invert

        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return

        start_idx = self._sc_filter_last_count
        new_html = []
        new_match_count = 0

        for i in range(start_idx, len(self._sc_all_logs)):
            raw = self._sc_all_logs[i][0]
            if compiled is not None:
                hit = bool(compiled.search(raw))
            elif case_sensitive:
                hit = pattern in raw
            else:
                hit = pattern.lower() in raw.lower()
            if invert:
                hit = not hit
            if hit:
                new_match_count += 1
                base_html = self._sc_all_logs[i][1]
                if not invert:
                    base_html = self._sc_html_with_filter_highlight(
                        base_html, pattern, use_regex, case_sensitive
                    )
                new_html.append(base_html)

        self._sc_filter_last_count = len(self._sc_all_logs)
        prev_text = self._sc_filter_match_label.text()
        prev_count = 0
        if prev_text.startswith("Matched: "):
            try:
                prev_count = int(prev_text.split(":")[1].strip().split()[0])
            except (ValueError, IndexError):
                pass
        total_match = prev_count + new_match_count
        self._sc_filter_match_label.setText(f"Matched: {total_match} lines")

        if new_html:
            self._sc_log_edit.setUpdatesEnabled(False)
            cursor = self._sc_log_edit.textCursor()
            cursor.beginEditBlock()
            for html in new_html:
                self._sc_log_edit.append(html)
            cursor.endEditBlock()
            self._sc_log_edit.setUpdatesEnabled(True)
            if self._sc_auto_scroll:
                self._sc_scroll_to_bottom()

    def _sc_append_system(self, message: str, force_primary: bool = False):
        color_map = {"INFO": _CLR_TEXT_INFO, "WARN": _CLR_WARNING, "ERROR": _CLR_ERROR}
        tag = ""
        for t in color_map:
            if f"[{t}]" in message:
                tag = t
                break
        color = color_map.get(tag, _CLR_TEXT_INFO)
        if tag in ("", "INFO") and not getattr(self, "_sc_show_system_log", False):
            return
        if not force_primary and self._sc_active_log_panel_index > 0:
            panel_idx = self._sc_active_log_panel_index - 1
            if 0 <= panel_idx < len(self._sc_extra_log_panels):
                self._sc_extra_panel_append_log(
                    self._sc_extra_log_panels[panel_idx], message, color
                )
                return
        self._sc_append_log(message, color)

    @staticmethod
    def _sc_format_bytes(prefix, n):
        if n < 1024:
            return f"{prefix}: {n} B"
        elif n < 1024 * 1024:
            return f"{prefix}: {n / 1024:.1f} KB"
        else:
            return f"{prefix}: {n / (1024 * 1024):.2f} MB"

    # --- ui helpers ---


