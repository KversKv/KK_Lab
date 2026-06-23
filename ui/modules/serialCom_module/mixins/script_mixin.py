# -*- coding: utf-8 -*-
"""脚本编辑/运行/循环/超时/导入导出 + 脚本表格构建。"""

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
from core.serial_script.script_engine import (
    decide_loop_next as _script_decide_loop_next,
    match_wait_keyword as _script_match_wait_keyword,
    ordered_steps as _script_ordered_steps,
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


class ScriptMixin:
    """脚本编辑/运行/循环/超时/导入导出 + 脚本表格构建。"""

    def _build_sc_script_tab(self):
        frame = QFrame()
        frame.setObjectName("quickCommandsPanel")
        frame.setProperty("class", "scQuickFrame")
        # 置于 scBottomTabs 的 pane 内，外框由 pane 提供，内层面板去边框避免双边框
        frame.setStyleSheet(quick_commands_panel_style() + "QFrame#quickCommandsPanel { border: none; background: transparent; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- 工具栏：脚本选择 + 运行控制 ---
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("scQuickToolbar")
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(6)

        _combo_qss = quick_combo_style()
        _toolbar_btn_qss = quick_toolbar_button_style()

        script_lbl = QLabel("Run File:")
        script_lbl.setStyleSheet(small_label_style(color="soft", size=11))
        toolbar.addWidget(script_lbl)

        self._sc_script_combo = QComboBox()
        self._sc_script_combo.setStyleSheet(_combo_qss)
        self._sc_script_combo.setMinimumWidth(160)
        toolbar.addWidget(self._sc_script_combo)

        self._sc_script_run_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "send.svg"), "Run", tone="quick"
        )
        self._sc_script_run_btn.setObjectName("primaryButton")
        self._sc_script_run_btn.setStyleSheet(quick_add_button_style())
        _run_icon = _tinted_svg_icon(
            os.path.join(_SVG_SERIAL_DIR, "send.svg"), _CLR_TEXT_WHITE, 11
        )
        if not _run_icon.isNull():
            self._sc_script_run_btn.setIcon(_run_icon)
        toolbar.addWidget(self._sc_script_run_btn)

        self._sc_script_stop_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "stop.svg"), "Stop", tone="quick"
        )
        self._sc_script_stop_btn.setStyleSheet(script_stop_button_style())
        self._sc_script_stop_btn.setEnabled(False)
        toolbar.addWidget(self._sc_script_stop_btn)

        toolbar.addSpacing(8)
        self._sc_script_loop_cb = QCheckBox("Loop")
        self._sc_script_loop_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_script_loop_cb.setToolTip("Repeat the script for the configured number of times")
        toolbar.addWidget(self._sc_script_loop_cb)

        self._sc_script_loop_spin = QSpinBox()
        self._sc_script_loop_spin.setObjectName("scIntervalSpin")
        self._sc_script_loop_spin.setRange(1, 99999)
        self._sc_script_loop_spin.setValue(1)
        self._sc_script_loop_spin.setFixedWidth(self._INTERVAL_SPIN_W)
        self._sc_script_loop_spin.setToolTip("Number of times to repeat the script")
        self._sc_script_loop_spin.setStyleSheet(
            compact_spinbox_style(up_button_width=0, padding="2px 8px")
        )
        toolbar.addWidget(self._sc_script_loop_spin)

        self._sc_script_loop_inf_cb = QCheckBox("\u221e")
        self._sc_script_loop_inf_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_script_loop_inf_cb.setToolTip("Loop forever until manually stopped")
        toolbar.addWidget(self._sc_script_loop_inf_cb)

        toolbar.addStretch()

        self._sc_script_new_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "New", tone="quick"
        )
        self._sc_script_new_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_new_btn)

        self._sc_script_edit_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "settings.svg"), "Edit", tone="quick"
        )
        self._sc_script_edit_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_edit_btn)

        self._sc_script_del_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Delete", tone="quick"
        )
        self._sc_script_del_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_del_btn)

        self._sc_script_import_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "import.svg"), "Import", tone="quick"
        )
        self._sc_script_import_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_import_btn)

        self._sc_script_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="quick"
        )
        self._sc_script_export_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_export_btn)

        layout.addWidget(toolbar_frame)
        layout.addWidget(self._make_panel_divider())

        # --- 状态栏 ---
        status_frame = QFrame()
        status_frame.setObjectName("scQuickToolbar")
        status_row = QHBoxLayout(status_frame)
        status_row.setContentsMargins(10, 0, 10, 6)
        status_row.setSpacing(6)
        self._sc_script_status_dot = QLabel()
        self._sc_script_status_dot.setFixedSize(8, 8)
        self._sc_script_set_status_dot(False)
        status_row.addWidget(self._sc_script_status_dot)
        self._sc_script_status_label = QLabel("Status: \u2022 Idle")
        self._sc_script_status_label.setStyleSheet(status_label_style("muted", include_font=True))
        status_row.addWidget(self._sc_script_status_label)
        self._sc_script_loop_label = QLabel("")
        self._sc_script_loop_label.setStyleSheet(status_label_style("muted", include_font=True))
        self._sc_script_loop_label.setVisible(False)
        status_row.addSpacing(12)
        status_row.addWidget(self._sc_script_loop_label)
        status_row.addStretch()
        self._sc_script_count_label = QLabel("Steps count (\u6b65): 0")
        self._sc_script_count_label.setStyleSheet(status_label_style("muted", include_font=True))
        status_row.addWidget(self._sc_script_count_label)
        layout.addWidget(status_frame)

        # --- 步骤预览表 ---
        self._sc_script_table = QTableWidget(0, 6)
        self._sc_script_table.setHorizontalHeaderLabels(
            ["#", "Command / Instructions Directive", "Priority",
             "Wait (ms)", "Status Condition", "Actions"]
        )
        self._sc_script_table.verticalHeader().setVisible(False)
        self._sc_script_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._sc_script_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._sc_script_table.setFocusPolicy(Qt.NoFocus)
        self._sc_script_table.setStyleSheet(self._sc_script_table_qss() + SERIAL_SCROLLBAR_STYLE)
        self._sc_script_table.setMinimumHeight(54)
        self._sc_script_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sc_script_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        hdr = self._sc_script_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self._sc_script_add_step_btn = QPushButton("+ Add Sequence Step Directive")
        self._sc_script_add_step_btn.setObjectName("scAddStepBtn")
        self._sc_script_add_step_btn.setCursor(Qt.PointingHandCursor)
        self._sc_script_add_step_btn.setStyleSheet(script_add_step_button_style())
        self._sc_script_add_step_btn.clicked.connect(self._sc_script_add_step)
        add_step_wrap = QFrame()
        add_step_wrap.setObjectName("scQuickToolbar")
        add_step_wrap.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        add_step_row = QHBoxLayout(add_step_wrap)
        add_step_row.setContentsMargins(10, 8, 10, 8)
        add_step_row.setSpacing(0)
        add_step_row.addWidget(self._sc_script_add_step_btn)

        # --- 内容区:QScrollArea 包裹步骤表 + 新增按钮，新增按钮位于可滚动内容最底部；
        #     区域高度偏低时整体自适应滚动，滚到底可见完整按钮 ---
        body_container = QWidget()
        body_container.setObjectName("scScriptBody")
        body_container.setStyleSheet(transparent_background_style())
        body_layout = QVBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        body_layout.addWidget(self._sc_script_table)
        body_layout.addWidget(add_step_wrap)
        body_layout.addStretch()

        self._sc_script_body_scroll = QScrollArea()
        self._sc_script_body_scroll.setWidgetResizable(True)
        self._sc_script_body_scroll.setFrameShape(QFrame.NoFrame)
        self._sc_script_body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sc_script_body_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._sc_script_body_scroll.setStyleSheet(
            transparent_scroll_area_style() + SERIAL_SCROLLBAR_STYLE
        )
        self._sc_script_body_scroll.verticalScrollBar().setStyleSheet(thin_scrollbar_style())
        self._sc_script_body_scroll.setMinimumHeight(54)
        self._sc_script_body_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._sc_script_body_scroll.setWidget(body_container)
        layout.addWidget(self._sc_script_body_scroll)

        self._sc_script_combo.currentIndexChanged.connect(self._sc_script_on_combo_changed)
        self._sc_script_run_btn.clicked.connect(self._sc_script_run)
        self._sc_script_stop_btn.clicked.connect(self._sc_script_stop)
        self._sc_script_loop_cb.toggled.connect(self._sc_script_on_loop_toggled)
        self._sc_script_loop_spin.valueChanged.connect(self._sc_script_on_loop_count_changed)
        self._sc_script_loop_inf_cb.toggled.connect(self._sc_script_on_loop_inf_toggled)
        self._sc_script_new_btn.clicked.connect(self._sc_script_new)
        self._sc_script_edit_btn.clicked.connect(self._sc_script_edit)
        self._sc_script_del_btn.clicked.connect(self._sc_script_delete)
        self._sc_script_import_btn.clicked.connect(self._sc_script_import_txt)
        self._sc_script_export_btn.clicked.connect(self._sc_script_export_txt)

        QTimer.singleShot(0, self._sc_script_refresh_all)
        return frame

    # --- status bar ---


    @staticmethod
    def _sc_script_default_data():
        return {
            "version": "1.0",
            "last_script_id": "",
            "scripts": [],
        }

    @staticmethod
    def _sc_script_default_step():
        return {
            "cmd": "",
            "priority": 1,
            "wait_ms": 1000,
            "wait_keyword": "",
            "wait_timeout_ms": 0,
        }

    def _sc_script_table_qss(self) -> str:
        return (
            f"QTableWidget {{"
            f"  background: transparent;"
            f"  color: {_CLR_TEXT_BODY};"
            f"  border: none;"
            f"  gridline-color: transparent;"
            f"  font-size: 12px;"
            f"  outline: none;"
            f"}}"
            f"QTableWidget::item {{ padding: 4px 6px; border: none; }}"
            f"QHeaderView::section {{"
            f"  background: transparent;"
            f"  color: {_CLR_TEXT_MUTED};"
            f"  border: none;"
            f"  border-bottom: 1px solid {_CLR_BORDER};"
            f"  padding: 5px 6px;"
            f"  font-size: 11px;"
            f"  font-weight: 600;"
            f"}}"
            f"QTableCornerButton::section {{"
            f"  background: transparent;"
            f"  border: none;"
            f"}}"
        )

    def _sc_script_current(self):
        sid = self._sc_script_data.get("last_script_id", "")
        for s in self._sc_script_data.get("scripts", []):
            if s.get("id") == sid:
                return s
        scripts = self._sc_script_data.get("scripts", [])
        return scripts[0] if scripts else None

    def _sc_script_refresh_all(self):
        if not hasattr(self, "_sc_script_combo"):
            return
        combo = self._sc_script_combo
        combo.blockSignals(True)
        combo.clear()
        scripts = self._sc_script_data.get("scripts", [])
        for s in scripts:
            combo.addItem(s.get("name", "未命名"), s.get("id", ""))
        cur = self._sc_script_current()
        if cur is not None:
            idx = combo.findData(cur.get("id", ""))
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            self._sc_script_data["last_script_id"] = cur.get("id", "")
        combo.blockSignals(False)
        self._sc_script_sync_loop_widgets()
        self._sc_script_refresh_table()

    def _sc_script_sync_loop_widgets(self):
        cur = self._sc_script_current()
        if cur is None:
            return
        self._sc_script_loop_cb.blockSignals(True)
        self._sc_script_loop_spin.blockSignals(True)
        self._sc_script_loop_inf_cb.blockSignals(True)
        loop_on = bool(cur.get("loop", False))
        loop_inf = bool(cur.get("loop_infinite", False))
        self._sc_script_loop_cb.setChecked(loop_on)
        self._sc_script_loop_spin.setValue(int(cur.get("loop_count", 1)) or 1)
        self._sc_script_loop_inf_cb.setChecked(loop_inf)
        self._sc_script_loop_cb.blockSignals(False)
        self._sc_script_loop_spin.blockSignals(False)
        self._sc_script_loop_inf_cb.blockSignals(False)
        self._sc_script_update_loop_widgets_enabled()

    def _sc_script_update_loop_widgets_enabled(self):
        loop_on = self._sc_script_loop_cb.isChecked()
        loop_inf = self._sc_script_loop_inf_cb.isChecked()
        self._sc_script_loop_inf_cb.setEnabled(loop_on)
        self._sc_script_loop_spin.setEnabled(loop_on and not loop_inf)

    def _sc_script_set_status_dot(self, running: bool):
        if not hasattr(self, "_sc_script_status_dot"):
            return
        color = "#34C759" if running else "#AEAEB2"
        self._sc_script_status_dot.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )

    def _sc_script_refresh_table(self, running_index: int = -1):
        table = self._sc_script_table
        cur = self._sc_script_current()
        steps = self._sc_script_ordered_steps(cur) if cur else []
        table.setRowCount(len(steps))
        if hasattr(self, "_sc_script_count_label"):
            self._sc_script_count_label.setText(f"Steps count (\u6b65): {len(steps)}")
        self._sc_script_set_status_dot(running_index >= 0)
        light = _CLR_BG_MAIN.upper() == "#F5F5F7"
        for row, step in enumerate(steps):
            cmd = step.get("cmd", "")
            prio = str(step.get("priority", 1))
            wait = f"{step.get('wait_ms', 0)} ms"
            keyword = step.get("wait_keyword", "")
            timeout = step.get("wait_timeout_ms", 0) or step.get("wait_ms", 0)
            if running_index < 0:
                state = "pending"
            elif row < running_index:
                state = "done"
            elif row == running_index:
                state = "running"
            else:
                state = "pending"
            if state == "running":
                row_fg = QColor(_CLR_SEND_BG)
                row_bg = QColor("#E8F2FF") if light else QColor("#172554")
            elif state == "done":
                row_fg = QColor(_CLR_TEXT_MUTED)
                row_bg = None
            else:
                row_fg = QColor(_CLR_TEXT_BODY)
                row_bg = None
            row_done = state == "done"
            for col, text in ((0, str(row + 1)), (2, prio), (3, wait)):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(row_fg)
                if row_bg is not None:
                    item.setBackground(row_bg)
                if row_done:
                    f = item.font()
                    f.setStrikeOut(True)
                    item.setFont(f)
                table.setItem(row, col, item)
            cmd_widget = self._sc_script_make_cmd_cell(
                cmd, keyword, timeout, row_fg, row_done, row_bg
            )
            table.setCellWidget(row, 1, cmd_widget)
            badge = self._sc_script_make_status_badge(state, light)
            table.setCellWidget(row, 4, badge)
            actions = self._sc_script_make_actions_cell(
                row, len(steps), running_index >= 0
            )
            table.setCellWidget(row, 5, actions)
        table.resizeRowsToContents()
        for col in (2, 3, 4):
            table.resizeColumnToContents(col)
        self._sc_script_adjust_table_height()

    def _sc_script_adjust_table_height(self):
        table = getattr(self, "_sc_script_table", None)
        if table is None:
            return
        header_h = table.horizontalHeader().height()
        rows_h = sum(
            table.rowHeight(r) for r in range(table.rowCount())
        )
        frame = 2 * table.frameWidth()
        total = header_h + rows_h + frame
        table.setMinimumHeight(max(54, total))
        table.setMaximumHeight(max(54, total))

    def _sc_script_make_cmd_cell(self, cmd, keyword, timeout, row_fg, strike, row_bg):
        w = QFrame()
        w.setStyleSheet(
            f"background-color: {row_bg.name()};" if row_bg is not None
            else "background: transparent;"
        )
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(1)
        deco = "text-decoration: line-through;" if strike else ""
        cmd_lbl = QLabel(cmd)
        cmd_lbl.setStyleSheet(
            f"color: {row_fg.name()}; font-family: {_TERM_FONT}; "
            f"font-size: 12px; font-weight: 700; background: transparent; {deco}"
        )
        cmd_lbl.setWordWrap(True)
        lay.addWidget(cmd_lbl)
        if keyword:
            sub = QLabel(f"\u27f6 wait keyword: \"{keyword}\" (timeout: {timeout}ms)")
            sub.setStyleSheet(
                "color: #7C6CF0; font-size: 9px; font-weight: 700; background: transparent;"
            )
            lay.addWidget(sub)
        return w

    def _sc_script_make_status_badge(self, state, light):
        if state == "running":
            text, fg, bg = "\u25b6 Running", ("#1D4ED8" if light else "#93C5FD"), ("#DBEAFE" if light else "#1E3A8A")
        elif state == "done":
            text, fg, bg = "\u2713 Done", ("#6B7280" if light else "#A1A1AA"), ("#F3F4F6" if light else "#27272A")
        else:
            text, fg, bg = "Pending", ("#6B7280" if light else "#A1A1AA"), ("#F1F5F9" if light else "#27272A")
        wrap = QFrame()
        wrap.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(0)
        badge = QLabel(text)
        badge.setStyleSheet(
            f"color: {fg}; background-color: {bg}; border-radius: 4px; "
            f"padding: 1px 7px; font-size: 10px; font-weight: 700; "
            f"font-family: {_UI_FONT};"
        )
        lay.addWidget(badge)
        lay.addStretch()
        return wrap

    def _sc_script_make_actions_cell(self, row, total, running):
        wrap = QFrame()
        wrap.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(6, 4, 8, 4)
        lay.setSpacing(3)
        lay.addStretch()
        specs = [
            (os.path.join(_SVG_LOGS_DIR, "arrow-up.svg"), _CLR_TEXT_MUTED,
             "Move Up", lambda: self._sc_script_move_step(row, -1),
             not running and row > 0),
            (os.path.join(_SVG_LOGS_DIR, "arrow-down.svg"), _CLR_TEXT_MUTED,
             "Move Down", lambda: self._sc_script_move_step(row, 1),
             not running and row < total - 1),
            (os.path.join(_SVG_SERIAL_DIR, "edit.svg"), _CLR_SEND_BG,
             "Edit step", lambda: self._sc_script_edit_step(row), not running),
            (os.path.join(_SVG_LOGS_DIR, "trash.svg"), _CLR_ERROR,
             "Delete step", lambda: self._sc_script_delete_step(row),
             not running and total > 1),
        ]
        for svg, color, tip, cb, enabled in specs:
            btn = QToolButton(wrap)
            btn.setObjectName("quickCmdAction")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setFixedSize(18, 18)
            btn.setIconSize(QSize(12, 12))
            btn.setToolTip(tip)
            btn.setStyleSheet(quick_action_overlay_style())
            icon = _tinted_svg_icon(svg, color, 12)
            if not icon.isNull():
                btn.setIcon(icon)
            btn.setEnabled(enabled)
            btn.clicked.connect(lambda checked=False, fn=cb: fn())
            lay.addWidget(btn)
        return wrap

    @staticmethod
    def _sc_script_ordered_steps(script) -> list:
        return _script_ordered_steps(script)

    def _sc_script_move_step(self, row: int, delta: int):
        cur = self._sc_script_current()
        if cur is None:
            return
        ordered = self._sc_script_ordered_steps(cur)
        target = row + delta
        if not (0 <= row < len(ordered)) or not (0 <= target < len(ordered)):
            return
        ordered[row], ordered[target] = ordered[target], ordered[row]
        for i, step in enumerate(ordered):
            step["priority"] = i + 1
        self._sc_save_persisted_state()
        self._sc_script_refresh_table()

    def _sc_script_edit_step(self, row: int):
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialScriptStepDialog
        cur = self._sc_script_current()
        if cur is None:
            return
        ordered = self._sc_script_ordered_steps(cur)
        if not (0 <= row < len(ordered)):
            return
        step = ordered[row]
        dlg = _SerialScriptStepDialog(self, step=step, mode="edit")
        if dlg.exec() == QDialog.Accepted:
            step.update(dlg.result_step())
            self._sc_save_persisted_state()
            self._sc_script_refresh_table()

    def _sc_script_delete_step(self, row: int):
        cur = self._sc_script_current()
        if cur is None:
            return
        ordered = self._sc_script_ordered_steps(cur)
        if not (0 <= row < len(ordered)):
            return
        step = ordered[row]
        if QMessageBox.question(
            self, "删除步骤",
            f"确定删除步骤 “{step.get('cmd', '')}” ?"
        ) != QMessageBox.Yes:
            return
        try:
            cur.get("steps", []).remove(step)
        except ValueError:
            return
        for i, s in enumerate(self._sc_script_ordered_steps(cur)):
            s["priority"] = i + 1
        self._sc_save_persisted_state()
        self._sc_script_refresh_table()

    def _sc_script_add_step(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialScriptStepDialog
        cur = self._sc_script_current()
        if cur is None:
            QMessageBox.information(self, "提示", "请先新建或选择一个脚本")
            return
        step = self._sc_script_default_step()
        step["priority"] = len(self._sc_script_ordered_steps(cur)) + 1
        dlg = _SerialScriptStepDialog(self, step=step, mode="create")
        if dlg.exec() == QDialog.Accepted:
            step.update(dlg.result_step())
            cur.setdefault("steps", []).append(step)
            self._sc_save_persisted_state()
            self._sc_script_refresh_table()

    def _sc_script_on_combo_changed(self, _index: int):
        sid = self._sc_script_combo.currentData()
        if sid:
            self._sc_script_data["last_script_id"] = sid
            self._sc_script_sync_loop_widgets()
            self._sc_script_refresh_table()

    def _sc_script_on_loop_toggled(self, checked: bool):
        self._sc_script_update_loop_widgets_enabled()
        cur = self._sc_script_current()
        if cur is not None:
            cur["loop"] = bool(checked)
            self._sc_save_persisted_state()

    def _sc_script_on_loop_inf_toggled(self, checked: bool):
        self._sc_script_update_loop_widgets_enabled()
        cur = self._sc_script_current()
        if cur is not None:
            cur["loop_infinite"] = bool(checked)
            self._sc_save_persisted_state()

    def _sc_script_on_loop_count_changed(self, value: int):
        cur = self._sc_script_current()
        if cur is not None:
            cur["loop_count"] = int(value)
            self._sc_save_persisted_state()

    # ---- 编辑 / 增删 ----

    def _sc_script_new(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialScriptEditorDialog
        script = {
            "id": self._sc_qc_gen_id("script"),
            "name": "新脚本",
            "loop": False,
            "loop_count": 1,
            "loop_infinite": False,
            "steps": [self._sc_script_default_step()],
        }
        dlg = _SerialScriptEditorDialog(
            self, script, quick_commands=self._sc_qc_collect_all_commands()
        )
        if dlg.exec() == QDialog.Accepted:
            self._sc_script_data.setdefault("scripts", []).append(dlg.get_script())
            self._sc_script_data["last_script_id"] = script["id"]
            self._sc_save_persisted_state()
            self._sc_script_refresh_all()

    def _sc_script_edit(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialScriptEditorDialog
        cur = self._sc_script_current()
        if cur is None:
            QMessageBox.information(self, "提示", "请先新建一个脚本")
            return
        dlg = _SerialScriptEditorDialog(
            self, cur, quick_commands=self._sc_qc_collect_all_commands()
        )
        if dlg.exec() == QDialog.Accepted:
            edited = dlg.get_script()
            cur.update(edited)
            self._sc_save_persisted_state()
            self._sc_script_refresh_all()

    def _sc_script_delete(self):
        cur = self._sc_script_current()
        if cur is None:
            return
        if QMessageBox.question(
            self, "删除脚本", f"确定删除脚本 “{cur.get('name', '')}” ?"
        ) != QMessageBox.Yes:
            return
        scripts = self._sc_script_data.get("scripts", [])
        scripts.remove(cur)
        self._sc_script_data["last_script_id"] = scripts[0]["id"] if scripts else ""
        self._sc_save_persisted_state()
        self._sc_script_refresh_all()

    # ---- txt 导入 / 导出 ----

    def _sc_script_import_txt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入脚本 (.txt)", "", "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))
            return
        steps = []
        priority = 1
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            step = self._sc_script_default_step()
            step["cmd"] = parts[0]
            if len(parts) >= 2 and parts[1]:
                try:
                    step["priority"] = int(parts[1])
                except ValueError:
                    step["priority"] = priority
            else:
                step["priority"] = priority
            if len(parts) >= 3 and parts[2]:
                try:
                    step["wait_ms"] = int(parts[2])
                except ValueError:
                    pass
            steps.append(step)
            priority += 1
        if not steps:
            QMessageBox.warning(self, "导入失败", "未解析到有效指令行")
            return
        name = os.path.splitext(os.path.basename(path))[0]
        script = {
            "id": self._sc_qc_gen_id("script"),
            "name": name,
            "loop": False,
            "loop_count": 1,
            "steps": steps,
        }
        self._sc_script_data.setdefault("scripts", []).append(script)
        self._sc_script_data["last_script_id"] = script["id"]
        self._sc_save_persisted_state()
        self._sc_script_refresh_all()
        self._sc_append_system(f"[SCRIPT] 已导入脚本 “{name}” ({len(steps)} 步)")

    def _sc_script_export_txt(self):
        cur = self._sc_script_current()
        if cur is None:
            QMessageBox.information(self, "提示", "没有可导出的脚本")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出脚本 (.txt)", f"{cur.get('name', 'script')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        lines = [
            "# 格式: 指令,优先级,等待ms  (优先级=0 表示跳过)",
            f"# 脚本: {cur.get('name', '')}",
        ]
        for step in cur.get("steps", []):
            lines.append(
                f"{step.get('cmd', '')},{step.get('priority', 1)},{step.get('wait_ms', 0)}"
            )
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
            return
        self._sc_append_system(f"[SCRIPT] 已导出脚本到 {path}")

    # ---- 运行引擎 ----

    def _sc_script_run(self):
        if self._sc_script_running:
            return
        cur = self._sc_script_current()
        if cur is None:
            QMessageBox.information(self, "提示", "请先新建或选择一个脚本")
            return
        steps = self._sc_script_ordered_steps(cur)
        if not steps:
            QMessageBox.warning(self, "提示", "脚本没有可执行的步骤 (优先级需 > 0)")
            return

        self._sc_script_steps = steps
        self._sc_script_step_index = 0
        loop_on = self._sc_script_loop_cb.isChecked()
        loop_inf = loop_on and self._sc_script_loop_inf_cb.isChecked()
        self._sc_script_loop_infinite = loop_inf
        if loop_inf:
            self._sc_script_loop_total = -1
            self._sc_script_loop_remaining = -1
        else:
            self._sc_script_loop_total = (
                int(self._sc_script_loop_spin.value()) if loop_on else 1
            )
            self._sc_script_loop_remaining = self._sc_script_loop_total
        self._sc_script_loop_done = 0
        self._sc_script_running = True
        self._sc_script_set_controls_enabled(False)
        loop_desc = "x\u221e" if loop_inf else f"x{self._sc_script_loop_total}"
        self._sc_append_system(
            f"[SCRIPT] 开始执行 “{cur.get('name', '')}” "
            f"({len(steps)} 步, 循环 {loop_desc})"
        )
        self._sc_script_update_loop_label()
        self._sc_script_refresh_table(running_index=0)
        self._sc_script_exec_current_step()

    def _sc_script_update_loop_label(self):
        if not hasattr(self, "_sc_script_loop_label"):
            return
        if not self._sc_script_running:
            self._sc_script_loop_label.setVisible(False)
            return
        done = getattr(self, "_sc_script_loop_done", 0)
        if getattr(self, "_sc_script_loop_infinite", False):
            self._sc_script_loop_label.setText(f"Loop: {done + 1}/\u221e")
        else:
            total = getattr(self, "_sc_script_loop_total", 1)
            self._sc_script_loop_label.setText(f"Loop: {min(done + 1, total)}/{total}")
        self._sc_script_loop_label.setVisible(True)

    def _sc_script_set_controls_enabled(self, enabled: bool):
        self._sc_script_run_btn.setEnabled(enabled)
        self._sc_script_stop_btn.setEnabled(not enabled)
        self._sc_script_combo.setEnabled(enabled)
        self._sc_script_new_btn.setEnabled(enabled)
        self._sc_script_edit_btn.setEnabled(enabled)
        self._sc_script_del_btn.setEnabled(enabled)
        self._sc_script_import_btn.setEnabled(enabled)
        self._sc_script_export_btn.setEnabled(enabled)
        self._sc_script_loop_cb.setEnabled(enabled)
        self._sc_script_loop_inf_cb.setEnabled(enabled)
        self._sc_script_loop_spin.setEnabled(enabled)
        if enabled:
            self._sc_script_update_loop_widgets_enabled()
        if hasattr(self, "_sc_script_add_step_btn"):
            self._sc_script_add_step_btn.setEnabled(enabled)

    def _sc_script_exec_current_step(self):
        if not self._sc_script_running:
            return
        idx = self._sc_script_step_index
        steps = self._sc_script_steps
        if idx >= len(steps):
            self._sc_script_on_loop_end()
            return

        step = steps[idx]
        self._sc_script_refresh_table(running_index=idx)
        self._sc_script_status_label.setText(
            f"Status: \u2022 Running (Step {idx + 1}/{len(steps)})"
        )
        self._sc_script_status_label.setStyleSheet(status_label_style("ok", include_font=True))

        cmd = step.get("cmd", "")
        ok = self._sc_script_send_step(step)
        if not ok:
            self._sc_append_system("[SCRIPT] 发送失败，串口未连接，已停止")
            self._sc_script_stop()
            return

        keyword = step.get("wait_keyword", "").strip()
        wait_ms = max(0, int(step.get("wait_ms", 0)))
        if keyword:
            self._sc_script_wait_keyword = keyword
            self._sc_script_wait_buffer = ""
            timeout = int(step.get("wait_timeout_ms", 0)) or wait_ms or 5000
            self._sc_script_timer.start(timeout)
        else:
            self._sc_script_wait_keyword = ""
            self._sc_script_timer.start(wait_ms)

    def _sc_script_send_step(self, step) -> bool:
        cmd = step.get("cmd", "")
        send_hex = step.get("send_type")
        if send_hex is None:
            send_hex = bool(getattr(self, "_sc_tx_display_hex", False))
        else:
            send_hex = send_hex == "hex"
        if send_hex:
            try:
                data = bytes.fromhex(cmd.replace(" ", ""))
            except ValueError:
                self._sc_append_system(f"[SCRIPT][ERROR] Invalid HEX: {cmd}")
                return False
        else:
            line_ending = step.get("line_ending")
            if line_ending is None:
                line_ending = getattr(self, "_sc_line_ending", "\r\n")
            data = (cmd + line_ending).encode("utf-8")

        ok = self._sc_send_to_focused_panel(data)
        if ok and self._sc_active_log_panel_index == 0:
            self._sc_tx_bytes += len(data)
            self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
            if self._sc_show_send:
                display = data.hex(' ') if send_hex else cmd
                self._sc_append_log(f"[TX] {display}", _CLR_TX)
        return ok

    def _sc_script_feed_rx(self, text: str):
        if not self._sc_script_wait_keyword:
            return
        self._sc_script_wait_buffer += text
        matched, self._sc_script_wait_buffer = _script_match_wait_keyword(
            self._sc_script_wait_buffer, self._sc_script_wait_keyword
        )
        if matched:
            self._sc_script_wait_keyword = ""
            self._sc_script_wait_buffer = ""
            self._sc_script_timer.stop()
            QTimer.singleShot(0, self._sc_script_advance)

    def _sc_script_on_timeout(self):
        if not self._sc_script_running:
            return
        if self._sc_script_wait_keyword:
            self._sc_append_system(
                f"[SCRIPT] 等待关键字 “{self._sc_script_wait_keyword}” 超时，继续下一步"
            )
            self._sc_script_wait_keyword = ""
            self._sc_script_wait_buffer = ""
        self._sc_script_advance()

    def _sc_script_advance(self):
        if not self._sc_script_running:
            return
        self._sc_script_step_index += 1
        self._sc_script_exec_current_step()

    def _sc_script_on_loop_end(self):
        self._sc_script_loop_done = getattr(self, "_sc_script_loop_done", 0) + 1
        action, new_idx, new_rem = _script_decide_loop_next(
            self._sc_script_step_index,
            len(self._sc_script_steps),
            self._sc_script_loop_remaining,
            getattr(self, "_sc_script_loop_infinite", False),
        )
        self._sc_script_step_index = new_idx
        self._sc_script_loop_remaining = new_rem
        if action == "loop_restart":
            self._sc_script_update_loop_label()
            if getattr(self, "_sc_script_loop_infinite", False):
                self._sc_append_system(
                    f"[SCRIPT] 进入下一轮循环 (已完成 {self._sc_script_loop_done} 轮, \u221e)"
                )
            else:
                self._sc_append_system(
                    f"[SCRIPT] 进入下一轮循环 (剩余 {self._sc_script_loop_remaining} 轮)"
                )
            self._sc_script_exec_current_step()
        else:
            self._sc_append_system("[SCRIPT] 执行完成")
            self._sc_script_finish()

    def _sc_script_stop(self):
        if not self._sc_script_running:
            return
        self._sc_append_system("[SCRIPT] 已手动停止")
        self._sc_script_finish()

    def _sc_script_finish(self):
        self._sc_script_running = False
        self._sc_script_wait_keyword = ""
        self._sc_script_wait_buffer = ""
        self._sc_script_timer.stop()
        self._sc_script_set_controls_enabled(True)
        self._sc_script_status_label.setText("Status: \u2022 Idle")
        self._sc_script_status_label.setStyleSheet(status_label_style("muted", include_font=True))
        if hasattr(self, "_sc_script_loop_label"):
            self._sc_script_loop_label.setVisible(False)
        self._sc_script_refresh_table(running_index=-1)


