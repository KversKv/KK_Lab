# -*- coding: utf-8 -*-
"""发送区 + 快捷指令管理（项目/分组/按钮/拖拽/导入导出）+ 发送与 RX 行缓冲。"""

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


class SendMixin:
    """发送区 + 快捷指令管理（项目/分组/按钮/拖拽/导入导出）+ 发送与 RX 行缓冲。"""

    def _build_sc_send_area(self):
        widget = QWidget()
        widget.setStyleSheet(transparent_background_style())
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        send_row = QHBoxLayout()
        send_row.setContentsMargins(0, 0, 0, 0)
        send_row.setSpacing(8)

        self._sc_history_combo = SerialHistoryComboBox()
        self._sc_history_combo.setEditable(True)
        self._sc_history_combo.setInsertPolicy(SerialHistoryComboBox.NoInsert)
        self._sc_history_combo.setFixedHeight(34)
        self._sc_send_input = self._sc_history_combo.lineEdit()
        self._sc_send_input.setPlaceholderText(
            "Inject command... (Use \u2191/\u2193 arrow keys for command history)"
        )
        self._sc_send_input.setClearButtonEnabled(False)
        send_row.addWidget(self._sc_history_combo, 1)

        self._sc_send_btn = QPushButton("Send")
        self._sc_send_btn.setCursor(Qt.PointingHandCursor)
        self._sc_send_btn.setFixedHeight(34)
        self._sc_send_btn.setMinimumWidth(92)
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "send.svg"), _CLR_BG_MAIN, 11)
        if not icon.isNull():
            self._sc_send_btn.setIcon(icon)
        self._sc_send_btn.setStyleSheet(send_button_style())
        send_row.addWidget(self._sc_send_btn)

        layout.addLayout(send_row)

        return widget

    # --- quick commands ---

    def _build_sc_quick_commands(self):
        tabs = QTabWidget()
        tabs.setObjectName("scBottomTabs")
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(bottom_tabs_style())
        tabs.tabBar().setCursor(Qt.PointingHandCursor)
        self._sc_bottom_tabs = tabs

        qc_index = tabs.addTab(self._build_sc_qc_tab(), "Quick Commands")
        script_index = tabs.addTab(self._build_sc_script_tab(), "Scripts")
        tabs.setIconSize(QSize(13, 13))

        self._sc_bottom_tab_icons = {
            qc_index: os.path.join(_SVG_SERIAL_DIR, "zap.svg"),
            script_index: os.path.join(_SVG_LOGS_DIR, "logs.svg"),
        }
        tabs.currentChanged.connect(self._sc_refresh_bottom_tab_icons)
        self._sc_refresh_bottom_tab_icons(tabs.currentIndex())
        return tabs

    def _sc_refresh_bottom_tab_icons(self, current_index):
        tabs = getattr(self, "_sc_bottom_tabs", None)
        if tabs is None:
            return
        for index, icon_path in self._sc_bottom_tab_icons.items():
            color = _CLR_TEXT_TITLE if index == current_index else _CLR_TEXT_MUTED
            icon = _tinted_svg_icon(icon_path, color, 13)
            if not icon.isNull():
                tabs.setTabIcon(index, icon)

    def _sc_bind_toggle_icon(self, btn, svg_path, colors, size):
        normal_color = colors.get("normal")
        checked_color = colors.get("checked")

        def _apply(checked):
            color = checked_color if checked else normal_color
            icon = _tinted_svg_icon(svg_path, color, size)
            if not icon.isNull():
                btn.setIcon(icon)

        btn.toggled.connect(_apply)
        _apply(btn.isChecked())

    @staticmethod
    def _make_panel_divider():
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet(panel_divider_style())
        return divider

    def _build_sc_qc_tab(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _ProjectTabBar
        frame = QFrame()
        # 双 objectName 不可行：保留 scQuickFrame 给现有内嵌 QSS；面板级 QSS 通过 quickCommandsPanel 选择器命中
        frame.setObjectName("quickCommandsPanel")
        frame.setProperty("class", "scQuickFrame")
        # 外层面板 + 内部分隔条：背景柔和、低对比边框、圆角；不改变布局
        # 置于 scBottomTabs 的 pane 内，外框由 pane 提供，内层面板去边框避免双边框
        frame.setStyleSheet(quick_commands_panel_style() + "QFrame#quickCommandsPanel { border: none; background: transparent; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- header: 标题 + 项目 Tab 栏 ---
        header_frame = QFrame()
        header_frame.setObjectName("scQuickHeaderFrame")
        header_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(10, 8, 10, 0)
        header.setSpacing(6)

        zap_icon = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "zap.svg"), _CLR_WARN_ICON, 10)
        if not icon.isNull():
            zap_icon.setPixmap(icon.pixmap(10, 10))
        zap_icon.setFixedSize(10, 10)
        zap_icon.setStyleSheet(transparent_background_style())
        header.addWidget(zap_icon)

        # 项目 Tab 栏（最顶层分组），末尾内置 "+" 加号 tab，右键菜单 + 拖拽排序
        self._sc_qc_project_tabs = _ProjectTabBar()
        self._sc_qc_project_tabs.setExpanding(False)
        self._sc_qc_project_tabs.setDrawBase(False)
        self._sc_qc_project_tabs.setUsesScrollButtons(True)
        self._sc_qc_project_tabs.setStyleSheet(project_tabs_style())
        self._sc_qc_project_tabs.setMinimumHeight(24)
        self._sc_qc_project_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header.addWidget(self._sc_qc_project_tabs, 1)

        layout.addWidget(header_frame)
        layout.addWidget(self._make_panel_divider())

        # --- 工具栏:区域/分组下拉 + 操作按钮 ---
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("scQuickToolbar")
        toolbar_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(6)

        _combo_qss = quick_combo_style()

        group_lbl = QLabel("Group:")
        group_lbl.setStyleSheet(small_label_style(color="soft", size=11))
        toolbar.addWidget(group_lbl)
        self._sc_qc_group_combo = QComboBox()
        self._sc_qc_group_combo.setStyleSheet(_combo_qss + quick_group_combo_bg_style())
        toolbar.addWidget(self._sc_qc_group_combo)

        self._sc_qc_new_group_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "Group", tone="quick"
        )
        # 工具栏统一暗色按钮样式：覆盖 _make_sc_btn(quick) 的局部 setStyleSheet
        _toolbar_btn_qss = quick_toolbar_button_style()
        # "+ Group" 为白底按钮，仅文字与 "+" 图标呼应蓝色
        self._sc_qc_new_group_btn.setStyleSheet(quick_group_button_style())
        _group_plus_icon = _tinted_svg_icon(
            os.path.join(_SVG_SERIAL_DIR, "plus-bold.svg"), _CLR_BLUE, 11
        )
        if not _group_plus_icon.isNull():
            self._sc_qc_new_group_btn.setIcon(_group_plus_icon)
        toolbar.addWidget(self._sc_qc_new_group_btn)

        # "+ Group" 右侧两个小图标按钮：编辑 / 删除当前分组（替代下拉右键菜单）
        self._sc_qc_group_edit_btn = QToolButton(toolbar_frame)
        self._sc_qc_group_edit_btn.setObjectName("quickCmdAction")
        self._sc_qc_group_edit_btn.setCursor(Qt.PointingHandCursor)
        self._sc_qc_group_edit_btn.setFocusPolicy(Qt.NoFocus)
        self._sc_qc_group_edit_btn.setFixedSize(18, 18)
        self._sc_qc_group_edit_btn.setIconSize(QSize(11, 11))
        self._sc_qc_group_edit_btn.setToolTip("Edit group")
        self._sc_qc_group_edit_btn.setStyleSheet(quick_action_overlay_style())
        _gedit_icon = _tinted_svg_icon(
            os.path.join(_SVG_SERIAL_DIR, "edit.svg"), _CLR_TEXT_TITLE, 11
        )
        if not _gedit_icon.isNull():
            self._sc_qc_group_edit_btn.setIcon(_gedit_icon)
        toolbar.addWidget(self._sc_qc_group_edit_btn)

        self._sc_qc_group_delete_btn = QToolButton(toolbar_frame)
        self._sc_qc_group_delete_btn.setObjectName("quickCmdAction")
        self._sc_qc_group_delete_btn.setCursor(Qt.PointingHandCursor)
        self._sc_qc_group_delete_btn.setFocusPolicy(Qt.NoFocus)
        self._sc_qc_group_delete_btn.setFixedSize(18, 18)
        self._sc_qc_group_delete_btn.setIconSize(QSize(11, 11))
        self._sc_qc_group_delete_btn.setToolTip("Delete group")
        self._sc_qc_group_delete_btn.setStyleSheet(quick_action_overlay_style())
        _gdel_icon = _tinted_svg_icon(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), _CLR_TEXT_TITLE, 11
        )
        if not _gdel_icon.isNull():
            self._sc_qc_group_delete_btn.setIcon(_gdel_icon)
        toolbar.addWidget(self._sc_qc_group_delete_btn)

        toolbar.addStretch()

        self._sc_qc_add_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "Add", tone="quick"
        )
        # + Add 作为主操作按钮：蓝色突出
        self._sc_qc_add_btn.setObjectName("primaryButton")
        self._sc_qc_add_btn.setStyleSheet(quick_add_button_style())
        _add_plus_icon = _tinted_svg_icon(
            os.path.join(_SVG_SERIAL_DIR, "plus-bold.svg"), _CLR_TEXT_WHITE, 11
        )
        if not _add_plus_icon.isNull():
            self._sc_qc_add_btn.setIcon(_add_plus_icon)
        toolbar.addWidget(self._sc_qc_add_btn)

        self._sc_qc_import_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "import.svg"), "Import", tone="quick"
        )
        self._sc_qc_import_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_qc_import_btn)

        self._sc_qc_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="quick"
        )
        self._sc_qc_export_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_qc_export_btn)

        layout.addWidget(toolbar_frame)
        layout.addWidget(self._make_panel_divider())

        # --- 按钮区:QScrollArea + QGridLayout ---
        self._sc_qc_btn_scroll = QScrollArea()
        self._sc_qc_btn_scroll.setWidgetResizable(True)
        self._sc_qc_btn_scroll.setFrameShape(QFrame.NoFrame)
        self._sc_qc_btn_scroll.setStyleSheet(quick_button_scroll_style() + SERIAL_SCROLLBAR_STYLE)
        self._sc_qc_btn_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sc_qc_btn_scroll.setMinimumHeight(68)
        self._sc_qc_btn_scroll.setMaximumHeight(150)
        self._sc_qc_btn_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._sc_qc_btn_container = QWidget()
        self._sc_qc_btn_container.setObjectName("scQuickBtnContainer")
        self._sc_qc_btn_container.setStyleSheet(quick_button_container_style())
        # 接受拖拽：本控件作为快捷指令按钮的统一 drop 目标，事件经 eventFilter 派发
        self._sc_qc_btn_container.setAcceptDrops(True)
        self._sc_qc_btn_container.installEventFilter(self)
        self._sc_qc_btn_layout = QGridLayout(self._sc_qc_btn_container)
        self._sc_qc_btn_layout.setContentsMargins(10, 10, 10, 10)
        self._sc_qc_btn_layout.setHorizontalSpacing(8)
        self._sc_qc_btn_layout.setVerticalSpacing(8)

        self._sc_qc_btn_scroll.setWidget(self._sc_qc_btn_container)
        layout.addWidget(self._sc_qc_btn_scroll)

        return frame

    # --- scripts ---


    def _sc_on_send(self):
        text = self._sc_send_input.text()
        if not text:
            return

        if self._sc_line_by_line:
            lines = text.split("\\n")
        else:
            lines = [text]

        for line in lines:
            if self._sc_tx_display_hex:
                try:
                    data = bytes.fromhex(line.replace(" ", ""))
                except ValueError:
                    self._sc_append_system(f"[ERROR] Invalid HEX: {line}")
                    return
            else:
                data = (line + self._sc_line_ending).encode("utf-8")

            ok = self._sc_send_to_focused_panel(data)
            if ok:
                if self._sc_active_log_panel_index == 0:
                    self._sc_tx_bytes += len(data)
                    self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
                    if self._sc_show_send:
                        display = line if not self._sc_tx_display_hex else data.hex(' ')
                        self._sc_append_log(f"[TX] {display}", _CLR_TX)
            else:
                self._sc_append_system("[ERROR] Send failed, serial not connected")

        if text not in self._sc_send_history:
            self._sc_send_history.insert(0, text)
            if len(self._sc_send_history) > 50:
                self._sc_send_history.pop()
            self._sc_history_combo.blockSignals(True)
            self._sc_history_combo.clear()
            self._sc_history_combo.addItems(self._sc_send_history)
            self._sc_history_combo.setCurrentIndex(-1)
            self._sc_history_combo.blockSignals(False)

        self._sc_send_input.clear()

    def _sc_send_to_focused_panel(self, data) -> bool:
        if self._sc_active_log_panel_index == 0:
            return self.serial_send(data)

        panel_idx = self._sc_active_log_panel_index - 1
        if panel_idx < 0 or panel_idx >= len(self._sc_extra_log_panels):
            return self.serial_send(data)

        panel = self._sc_extra_log_panels[panel_idx]
        conn = panel.get("conn")

        if DEBUG_MOCK:
            panel["tx_bytes"] = panel.get("tx_bytes", 0) + len(data)
            panel["tx_label"].setText(self._sc_format_bytes("TX", panel["tx_bytes"]))
            self._sc_extra_panel_append_log(
                panel, f"[TX] {data.decode('utf-8', errors='replace')}", _CLR_TX
            )
            return True

        if conn is None or not conn.is_open:
            return False
        try:
            conn.write(data)
            panel["tx_bytes"] = panel.get("tx_bytes", 0) + len(data)
            panel["tx_label"].setText(self._sc_format_bytes("TX", panel["tx_bytes"]))
            self._sc_extra_panel_append_log(
                panel, f"[TX] {data.decode('utf-8', errors='replace')}", _CLR_TX
            )
            return True
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Send failed: {e}", extra_log_error_color())
            return False

    def _sc_on_data_received(self, data: bytes):
        if self._sc_paused:
            return
        if self._sc_script_wait_keyword:
            try:
                self._sc_script_feed_rx(data.decode("utf-8", errors="replace"))
            except Exception:
                pass
        self._sc_rx_bytes += len(data)
        self._sc_status_rx_label.setText(self._sc_format_bytes("RX", self._sc_rx_bytes))

        self._sc_chart_feed_bytes(data)

        if self._sc_rx_display_hex:
            display = data.hex(' ')
            for line in display.splitlines():
                if line.strip():
                    self._sc_append_log(f"[RX] {line}", _CLR_RX)
        else:
            display = data.decode("utf-8", errors="replace")
            display = display.replace("\x00", "")
            display = "".join(
                ch if ch == "\n" or ch == "\r" or ch == "\t" or (ord(ch) >= 0x20) else ""
                for ch in display
            )

            self._sc_rx_line_buf += display
            while "\n" in self._sc_rx_line_buf:
                line, self._sc_rx_line_buf = self._sc_rx_line_buf.split("\n", 1)
                line = line.rstrip("\r")
                if line.strip():
                    self._sc_chart_feed_line(line)
                    self._sc_append_log(f"[RX] {line}", _CLR_RX)

            if self._sc_rx_line_buf and self._sc_rx_auto_flush_cb.isChecked():
                self._sc_rx_flush_timer.start(self._sc_rx_auto_flush_spin.value())
            else:
                self._sc_rx_flush_timer.stop()

        self._sc_feed_auto_baud_monitor(data)

    def _sc_flush_rx_line_buf(self):
        if self._sc_rx_line_buf:
            line = self._sc_rx_line_buf.rstrip("\r")
            self._sc_rx_line_buf = ""
            if line.strip():
                self._sc_chart_feed_line(line)
                self._sc_append_log(f"[RX] {line}", _CLR_RX)

    # ==================== RX 数据可视化（Chart）====================


    @staticmethod
    def _sc_qc_default_data():
        return {
            "version": "1.0",
            "last_project_id": "project_default",
            "last_group_id": "group_default",
            "projects": [
                {
                    "id": "project_default",
                    "name": "默认项目",
                    "groups": [
                        {
                            "id": "group_default",
                            "name": "默认分组",
                            "commands": [],
                        }
                    ],
                }
            ],
        }

    @staticmethod
    def _sc_qc_gen_id(prefix: str) -> str:
        return f"{prefix}_{_uuid.uuid4().hex[:8]}"

    def _sc_qc_get_project(self, project_id):
        if not project_id:
            return None
        for p in self._sc_qc_data.get("projects", []):
            if p.get("id") == project_id:
                return p
        return None

    def _sc_qc_get_group(self, project, group_id):
        if not project or not group_id:
            return None
        for g in project.get("groups", []):
            if g.get("id") == group_id:
                return g
        return None

    def _sc_qc_current_project(self):
        return self._sc_qc_get_project(self._sc_qc_data.get("last_project_id"))

    def _sc_qc_current_group(self):
        return self._sc_qc_get_group(
            self._sc_qc_current_project(), self._sc_qc_data.get("last_group_id")
        )

    def _sc_qc_collect_all_commands(self):
        result = []
        for project in self._sc_qc_data.get("projects", []) or []:
            project_name = project.get("name", "")
            for group in project.get("groups", []) or []:
                group_name = group.get("name", "")
                for cmd in group.get("commands", []) or []:
                    content = cmd.get("content", "")
                    if not content:
                        continue
                    result.append({
                        "name": cmd.get("name", "") or content,
                        "content": content,
                        "send_type": cmd.get("send_type", "text"),
                        "line_ending": cmd.get("line_ending", "\r\n"),
                        "encoding": cmd.get("encoding", "ascii"),
                        "project": project_name,
                        "group": group_name,
                    })
        return result

    def _sc_qc_ensure_selection(self):
        projects = self._sc_qc_data.get("projects", [])
        if not projects:
            self._sc_qc_data = self._sc_qc_default_data()
            projects = self._sc_qc_data["projects"]

        project = self._sc_qc_current_project()
        if project is None:
            project = projects[0]
            self._sc_qc_data["last_project_id"] = project.get("id", "")

        groups = project.setdefault("groups", [])
        if not groups:
            groups.append({
                "id": self._sc_qc_gen_id("group"),
                "name": "默认分组",
                "commands": [],
            })
        group = self._sc_qc_get_group(project, self._sc_qc_data.get("last_group_id"))
        if group is None:
            group = groups[0]
            self._sc_qc_data["last_group_id"] = group.get("id", "")

    def _sc_qc_refresh_all(self):
        self._sc_qc_ensure_selection()
        self._sc_qc_refresh_project_tabs()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()

    _SC_QC_ADD_TAB_MARK = "__add__"

    def _sc_qc_refresh_project_tabs(self):
        tabs = self._sc_qc_project_tabs
        tabs.blockSignals(True)
        while tabs.count() > 0:
            tabs.removeTab(0)
        active_index = 0
        projects = self._sc_qc_data.get("projects", [])
        for i, p in enumerate(projects):
            tabs.addTab(p.get("name", "未命名"))
            tabs.setTabData(i, p.get("id", ""))
            if p.get("id") == self._sc_qc_data.get("last_project_id"):
                active_index = i
        # 末尾追加加号 tab（用 SVG 图标替代纯文字 "+"），单击即新增项目
        plus_index = tabs.addTab("")
        tabs.setTabData(plus_index, self._SC_QC_ADD_TAB_MARK)
        tabs.setTabToolTip(plus_index, "新增项目")
        _plus_tab_icon = _tinted_svg_icon(
            os.path.join(_SVG_SERIAL_DIR, "plus-tab.svg"), _CLR_TEXT_TITLE, 14
        )
        if not _plus_tab_icon.isNull():
            tabs.setTabIcon(plus_index, _plus_tab_icon)
            tabs.setIconSize(QSize(14, 14))
        if projects:
            tabs.setCurrentIndex(active_index)
        tabs.blockSignals(False)

    def _sc_qc_refresh_group_combo(self):
        combo = self._sc_qc_group_combo
        combo.blockSignals(True)
        combo.clear()
        project = self._sc_qc_current_project()
        active_index = 0
        if project:
            for i, g in enumerate(project.get("groups", [])):
                combo.addItem(g.get("name", "未命名"), g.get("id", ""))
                if g.get("id") == self._sc_qc_data.get("last_group_id"):
                    active_index = i
        if combo.count() > 0:
            combo.setCurrentIndex(active_index)
        combo.blockSignals(False)
        # 编辑/删除按钮可用性：无分组禁用编辑；仅剩一个分组禁用删除
        group_count = len(project.get("groups", [])) if project else 0
        if hasattr(self, "_sc_qc_group_edit_btn"):
            self._sc_qc_group_edit_btn.setEnabled(group_count > 0)
        if hasattr(self, "_sc_qc_group_delete_btn"):
            self._sc_qc_group_delete_btn.setEnabled(group_count > 1)

    def _sc_qc_clear_button_grid(self):
        layout = self._sc_qc_btn_layout
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                cleanup = getattr(w, "_cleanup_action_bar", None)
                if callable(cleanup):
                    cleanup()
                w.setParent(None)
                w.deleteLater()

    def _sc_refresh_quick_buttons(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickCmdButton
        self._sc_qc_clear_button_grid()
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        cols = 6
        for idx, entry in enumerate(commands):
            name = entry.get("name", "") or entry.get("content", "")
            content = entry.get("content", "")
            btn = _QuickCmdButton(name if name else content)
            btn.setObjectName("quickCommandButton")
            btn.set_command_index(idx)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.set_preview_data(
                name=name,
                content=content,
                send_type=entry.get('send_type', 'text'),
                encoding=entry.get('encoding', 'ascii'),
                line_ending=entry.get('line_ending', ''),
            )
            btn.clicked.connect(
                lambda checked=False, e=entry: self._sc_send_quick(e)
            )
            # 右键菜单：编辑 / 删除
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, i=idx: self._sc_qc_on_cmd_btn_context_menu(b, pos, i)
            )
            # 悬停浮出：左移 / 右移 / 编辑 / 删除
            btn.set_move_bounds(idx > 0, idx < len(commands) - 1)
            btn.move_requested.connect(self._sc_qc_move_command)
            btn.edit_requested.connect(self._sc_qc_edit_command)
            btn.delete_requested.connect(self._sc_qc_delete_command)
            btn.setStyleSheet(quick_command_button_style())
            row, col = divmod(idx, cols)
            self._sc_qc_btn_layout.addWidget(btn, row, col)
        self._sc_qc_btn_layout.setRowStretch(
            (len(commands) // cols) + 1, 1
        )
        self._sc_qc_btn_layout.setColumnStretch(cols, 1)

    # --- 切换 ---

    def _sc_qc_on_project_tab_changed(self, index):
        if index < 0 or index >= self._sc_qc_project_tabs.count():
            return
        project_id = self._sc_qc_project_tabs.tabData(index)
        # 命中末尾 "+" 加号 tab：触发新增项目；若用户取消则回切到原项目
        if project_id == self._SC_QC_ADD_TAB_MARK:
            prev_id = self._sc_qc_data.get("last_project_id", "")
            created = self._sc_qc_add_project()
            if not created:
                tabs = self._sc_qc_project_tabs
                tabs.blockSignals(True)
                restore_index = 0
                for i in range(tabs.count()):
                    if tabs.tabData(i) == prev_id:
                        restore_index = i
                        break
                tabs.setCurrentIndex(restore_index)
                tabs.blockSignals(False)
            return
        if not project_id or project_id == self._sc_qc_data.get("last_project_id"):
            return
        self._sc_qc_data["last_project_id"] = project_id
        project = self._sc_qc_get_project(project_id)
        if project is not None:
            groups = project.get("groups", [])
            self._sc_qc_data["last_group_id"] = groups[0].get("id", "") if groups else ""
        self._sc_qc_ensure_selection()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()
        self._sc_qc_save_data()

    def _sc_qc_on_group_changed(self, index):
        if index < 0:
            return
        group_id = self._sc_qc_group_combo.itemData(index)
        if not group_id or group_id == self._sc_qc_data.get("last_group_id"):
            return
        self._sc_qc_data["last_group_id"] = group_id
        self._sc_refresh_quick_buttons()
        self._sc_qc_save_data()

    # --- 项目 Tab 右键菜单 / 重命名 / 删除 / 拖拽排序 ---

    def _sc_qc_on_project_tab_context_menu(self, pos):
        tabs = self._sc_qc_project_tabs
        index = tabs.tabAt(pos)
        if index < 0:
            return
        project_id = tabs.tabData(index)
        if not project_id or project_id == self._SC_QC_ADD_TAB_MARK:
            return
        project = self._sc_qc_get_project(project_id)
        if project is None:
            return
        menu = QMenu(self)
        act_rename = menu.addAction("重命名")
        act_export = menu.addAction("导出")
        menu.addSeparator()
        act_delete = menu.addAction("删除")
        # 仅剩一个项目时禁止删除，防止数据完全清空
        if len(self._sc_qc_data.get("projects", [])) <= 1:
            act_delete.setEnabled(False)
        chosen = menu.exec(tabs.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_rename:
            self._sc_qc_rename_project(project)
        elif chosen is act_export:
            self._sc_qc_export_project(project)
        elif chosen is act_delete:
            self._sc_qc_delete_project(project)

    def _sc_qc_rename_project(self, project):
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickTextInputDialog
        if not isinstance(project, dict):
            return
        old_name = project.get("name", "")
        text, ok = _QuickTextInputDialog.get_input(
            self, title="重命名项目", label="项目名称", text=old_name,
            placeholder="如:主控测试",
        )
        if not ok:
            return
        new_name = text.strip()
        if not new_name or new_name == old_name:
            return
        project["name"] = new_name
        self._sc_qc_save_data()
        self._sc_qc_refresh_project_tabs()

    def _sc_qc_delete_project(self, project):
        if not isinstance(project, dict):
            return
        projects = self._sc_qc_data.get("projects", [])
        if len(projects) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个项目")
            return
        ret = QMessageBox.question(
            self, "删除项目",
            f"确定删除项目「{project.get('name', '')}」及其全部分组与指令？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            projects.remove(project)
        except ValueError:
            return
        # 若删的是当前项目，回退到第一个
        if self._sc_qc_data.get("last_project_id") == project.get("id"):
            first = projects[0]
            self._sc_qc_data["last_project_id"] = first.get("id", "")
            groups = first.get("groups", [])
            self._sc_qc_data["last_group_id"] = groups[0].get("id", "") if groups else ""
        self._sc_qc_save_data()
        self._sc_qc_refresh_all()

    def _sc_qc_on_project_reorder(self, source_index: int, target_index: int):
        projects = self._sc_qc_data.get("projects", [])
        n = len(projects)
        if n <= 1:
            return
        if source_index < 0 or source_index >= n:
            return
        # 钳制目标到合法范围（拖到 "+" tab 等价于挪到末尾）
        if target_index < 0:
            target_index = 0
        if target_index >= n:
            target_index = n - 1
        if source_index == target_index:
            return
        item = projects.pop(source_index)
        projects.insert(target_index, item)
        self._sc_qc_save_data()
        self._sc_qc_refresh_project_tabs()

    # --- 新增 ---

    def _sc_qc_prompt_text(self, title: str, label: str) -> str:
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickTextInputDialog
        clean_label = label.rstrip("：:").strip()
        text, ok = _QuickTextInputDialog.get_input(
            self, title=title, label=clean_label,
        )
        if not ok:
            return ""
        return text.strip()

    def _sc_qc_add_project(self) -> bool:
        name = self._sc_qc_prompt_text("新增项目", "项目名称:")
        if not name:
            return False
        project = {
            "id": self._sc_qc_gen_id("project"),
            "name": name,
            "groups": [
                {
                    "id": self._sc_qc_gen_id("group"),
                    "name": "默认分组",
                    "commands": [],
                }
            ],
        }
        self._sc_qc_data.setdefault("projects", []).append(project)
        self._sc_qc_data["last_project_id"] = project["id"]
        self._sc_qc_data["last_group_id"] = project["groups"][0]["id"]
        self._sc_qc_save_data()
        self._sc_qc_refresh_all()
        return True

    def _sc_qc_add_group(self):
        project = self._sc_qc_current_project()
        if project is None:
            QMessageBox.warning(self, "提示", "请先创建项目")
            return
        name = self._sc_qc_prompt_text("新增分组", "分组名称:")
        if not name:
            return
        group = {
            "id": self._sc_qc_gen_id("group"),
            "name": name,
            "commands": [],
        }
        project.setdefault("groups", []).append(group)
        self._sc_qc_data["last_group_id"] = group["id"]
        self._sc_qc_save_data()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()

    # --- 分组编辑 / 删除（"+ Group" 右侧图标按钮触发）---

    def _sc_qc_edit_current_group(self):
        index = self._sc_qc_group_combo.currentIndex()
        if index < 0:
            return
        group_id = self._sc_qc_group_combo.itemData(index)
        if not group_id:
            return
        project = self._sc_qc_current_project()
        group = self._sc_qc_get_group(project, group_id)
        if group is None:
            return
        self._sc_qc_rename_group(group)

    def _sc_qc_delete_current_group(self):
        index = self._sc_qc_group_combo.currentIndex()
        if index < 0:
            return
        group_id = self._sc_qc_group_combo.itemData(index)
        if not group_id:
            return
        project = self._sc_qc_current_project()
        group = self._sc_qc_get_group(project, group_id)
        if group is None:
            return
        self._sc_qc_delete_group(group)

    def _sc_qc_rename_group(self, group):
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickTextInputDialog
        if not isinstance(group, dict):
            return
        old_name = group.get("name", "")
        text, ok = _QuickTextInputDialog.get_input(
            self, title="重命名分组", label="分组名称", text=old_name,
            placeholder="如:基础指令",
        )
        if not ok:
            return
        new_name = text.strip()
        if not new_name or new_name == old_name:
            return
        group["name"] = new_name
        self._sc_qc_save_data()
        self._sc_qc_refresh_group_combo()

    def _sc_qc_delete_group(self, group):
        if not isinstance(group, dict):
            return
        project = self._sc_qc_current_project()
        if project is None:
            return
        groups = project.get("groups", [])
        if len(groups) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个分组")
            return
        ret = QMessageBox.question(
            self, "删除分组",
            f"确定删除分组「{group.get('name', '')}」及其全部指令？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            groups.remove(group)
        except ValueError:
            return
        # 若删的是当前分组，回退到第一个
        if self._sc_qc_data.get("last_group_id") == group.get("id"):
            self._sc_qc_data["last_group_id"] = groups[0].get("id", "") if groups else ""
        self._sc_qc_save_data()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()

    def _sc_add_quick_cmd(self):
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickCmdDialog
        group = self._sc_qc_current_group()
        if group is None:
            QMessageBox.warning(self, "提示", "请先创建项目和分组")
            return
        prefill_cmd = self._sc_send_input.text().strip()
        dlg = _QuickCmdDialog(parent=self, content=prefill_cmd)
        if dlg.exec() != QDialog.Accepted:
            return
        cmd = dlg.get_command()
        if not cmd or not cmd.get("content"):
            return
        cmd["id"] = self._sc_qc_gen_id("cmd")
        group.setdefault("commands", []).append(cmd)
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    # --- 快捷指令按钮：右键菜单（编辑 / 删除） ---

    def _sc_qc_on_cmd_btn_context_menu(self, btn, pos, idx):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        if not (0 <= idx < len(commands)):
            return
        menu = QMenu(self)
        act_edit = menu.addAction("编辑指令")
        act_del = menu.addAction("删除指令")
        act = menu.exec(btn.mapToGlobal(pos))
        if act is None:
            return
        if act == act_edit:
            self._sc_qc_edit_command(idx)
        elif act == act_del:
            self._sc_qc_delete_command(idx)

    def _sc_qc_move_command(self, idx, delta):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        target = idx + delta
        if not (0 <= idx < len(commands)) or not (0 <= target < len(commands)):
            return
        commands[idx], commands[target] = commands[target], commands[idx]
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    def _sc_qc_edit_command(self, idx):
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickCmdDialog
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        if not (0 <= idx < len(commands)):
            return
        entry = commands[idx]
        dlg = _QuickCmdDialog(
            parent=self,
            name=entry.get("name", ""),
            content=entry.get("content", ""),
            send_type=entry.get("send_type", "text"),
            line_ending=entry.get("line_ending", "\r\n"),
            encoding=entry.get("encoding", "ascii"),
        )
        if dlg.exec() != QDialog.Accepted:
            return
        new_cmd = dlg.get_command()
        if not new_cmd or not new_cmd.get("content"):
            return
        # 保留原 id，覆盖其它字段
        new_cmd["id"] = entry.get("id") or self._sc_qc_gen_id("cmd")
        commands[idx] = new_cmd
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    def _sc_qc_delete_command(self, idx):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        if not (0 <= idx < len(commands)):
            return
        entry = commands[idx]
        name = entry.get("name", "") or entry.get("content", "")
        ret = QMessageBox.question(
            self,
            "删除指令",
            f"确定要删除指令 \"{name}\" 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        commands.pop(idx)
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    def _sc_qc_reorder_command(self, source_idx, target_idx):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        n = len(commands)
        if not (0 <= source_idx < n):
            return
        # 目标越界则视为追加到末尾
        if target_idx < 0 or target_idx >= n:
            target_idx = n - 1
        if source_idx == target_idx:
            return
        item = commands.pop(source_idx)
        commands.insert(target_idx, item)
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    # --- 快捷指令按钮：拖拽排序（容器层 eventFilter） ---

    def eventFilter(self, obj, event):
        # 仅处理快捷指令容器上的拖拽事件；其它一律放行
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickCmdButton
        container = getattr(self, "_sc_qc_btn_container", None)
        if container is not None and obj is container:
            etype = event.type()
            from PySide6.QtCore import QEvent  # 局部引入，避免顶部冗余导入
            if etype == QEvent.DragEnter:
                if event.mimeData().hasFormat(_QuickCmdButton._MIME_TYPE):
                    event.acceptProposedAction()
                    return True
            elif etype == QEvent.DragMove:
                if event.mimeData().hasFormat(_QuickCmdButton._MIME_TYPE):
                    event.acceptProposedAction()
                    return True
            elif etype == QEvent.Drop:
                if event.mimeData().hasFormat(_QuickCmdButton._MIME_TYPE):
                    try:
                        source_idx = int(
                            bytes(event.mimeData().data(
                                _QuickCmdButton._MIME_TYPE
                            )).decode()
                        )
                    except (ValueError, UnicodeDecodeError):
                        return False
                    # 命中目标按钮：从落点反查最近的 _QuickCmdButton
                    pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                    target_idx = self._sc_qc_locate_drop_index(pos, source_idx)
                    event.acceptProposedAction()
                    self._sc_qc_reorder_command(source_idx, target_idx)
                    return True
        return super().eventFilter(obj, event)

    def _sc_qc_locate_drop_index(self, pos, source_idx):
        """根据落点定位目标插入索引：命中按钮取其 command_index；
        否则按 grid 行列估算最近按钮；都不命中则返回末尾。
        """
        from ui.modules.serialCom_module.serialCom_module_frame import _QuickCmdButton
        container = self._sc_qc_btn_container
        commands = (
            self._sc_qc_current_group() or {}
        ).get("commands", []) or []
        n = len(commands)
        if n == 0:
            return 0
        # 1) 直接命中：containerAt -> 反查 _QuickCmdButton
        child = container.childAt(pos)
        while child is not None and not isinstance(child, _QuickCmdButton):
            child = child.parentWidget()
            if child is container:
                child = None
                break
        if isinstance(child, _QuickCmdButton):
            ti = child.command_index()
            if 0 <= ti < n:
                return ti
        # 2) 未命中按钮：按 y 取最近一行的最后一个按钮所在索引
        layout = self._sc_qc_btn_layout
        nearest_idx = n - 1
        nearest_dy = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            w = item.widget() if item is not None else None
            if not isinstance(w, _QuickCmdButton):
                continue
            geo = w.geometry()
            if geo.top() <= pos.y() <= geo.bottom():
                # 同一行：取该行内 x 最接近的按钮
                if pos.x() <= geo.center().x():
                    return w.command_index()
                # 大于中心：插到该按钮之后（下一项的位置）
                ci = w.command_index()
                return min(ci + 1 if ci + 1 < n else ci, n - 1)
            dy = abs(geo.center().y() - pos.y())
            if nearest_dy is None or dy < nearest_dy:
                nearest_dy = dy
                nearest_idx = w.command_index()
        return nearest_idx

    # --- 发送 ---

    def _sc_send_quick(self, entry):
        if not isinstance(entry, dict):
            return
        content = entry.get("content", "")
        send_type = entry.get("send_type", "text")
        line_ending = entry.get("line_ending", "")
        encoding = entry.get("encoding", "ascii") or "ascii"
        target_session_id = entry.get("target_session_id", "")

        if send_type == "hex":
            try:
                data = bytes.fromhex(content.replace(" ", ""))
            except ValueError:
                self._sc_append_system(f"[ERROR] Invalid HEX: {content}")
                return
        else:
            text = content + (line_ending or "")
            try:
                data = text.encode(encoding)
            except (UnicodeEncodeError, LookupError) as e:
                self._sc_append_system(f"[ERROR] Encode failed ({encoding}): {e}")
                return

        if target_session_id:
            ok = self.send_to_session(target_session_id, data)
        else:
            ok = self._sc_send_to_focused_panel(data)
        if ok:
            if self._sc_active_log_panel_index == 0 and not target_session_id:
                self._sc_tx_bytes += len(data)
                self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
                if self._sc_show_send:
                    display = data.hex(' ') if send_type == "hex" else content
                    self._sc_append_log(f"[TX] {display}", _CLR_TX)
        else:
            target_info = f" (target: {target_session_id})" if target_session_id else ""
            self._sc_append_system(f"[ERROR] Send failed, serial not connected{target_info}")

    # --- 导入 / 导出 ---

    def _sc_qc_collect_existing_ids(self):
        ids = set()
        for p in self._sc_qc_data.get("projects", []):
            ids.add(p.get("id", ""))
            for g in p.get("groups", []):
                ids.add(g.get("id", ""))
                for c in g.get("commands", []):
                    ids.add(c.get("id", ""))
        ids.discard("")
        return ids

    @staticmethod
    def _sc_qc_unique_cmd_name(base: str, used_names: set) -> str:
        if base not in used_names:
            return base
        candidate = f"{base}_导入"
        if candidate not in used_names:
            return candidate
        i = 1
        while True:
            candidate = f"{base}_导入_{i}"
            if candidate not in used_names:
                return candidate
            i += 1

    def _sc_import_quick_cmds(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Quick Commands", "", "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法读取文件:\n{e}")
            return

        if not isinstance(data, dict):
            QMessageBox.critical(self, "导入失败", "JSON 格式不符合要求")
            return

        qc_payload = None
        if "quick_commands" in data and isinstance(data["quick_commands"], dict):
            qc_payload = data["quick_commands"]
        elif "projects" in data and isinstance(data["projects"], list):
            qc_payload = data
        else:
            QMessageBox.critical(self, "导入失败", "JSON 格式不符合要求 (需包含 quick_commands 或 projects)")
            return

        if not isinstance(qc_payload.get("projects"), list):
            QMessageBox.critical(self, "导入失败", "JSON 格式不符合要求 (需包含 projects 列表)")
            return

        self._sc_merge_quick_cmds(qc_payload)

    def _sc_merge_quick_cmds(self, data: dict):
        used_ids = self._sc_qc_collect_existing_ids()
        stat = {"project": 0, "group": 0, "cmd": 0, "renamed": 0}

        def fix_id(prefix, raw_id):
            if raw_id and raw_id not in used_ids:
                used_ids.add(raw_id)
                return raw_id
            new_id = self._sc_qc_gen_id(prefix)
            while new_id in used_ids:
                new_id = self._sc_qc_gen_id(prefix)
            used_ids.add(new_id)
            return new_id

        def iter_groups(ip):
            if isinstance(ip.get("regions"), list):
                for ir in ip.get("regions", []) or []:
                    if not isinstance(ir, dict):
                        continue
                    for ig in ir.get("groups", []) or []:
                        if isinstance(ig, dict):
                            yield ig
            for ig in ip.get("groups", []) or []:
                if isinstance(ig, dict):
                    yield ig

        existing_projects = self._sc_qc_data.setdefault("projects", [])
        for ip in data["projects"]:
            if not isinstance(ip, dict):
                continue
            pname = ip.get("name", "未命名项目")
            target_p = next((p for p in existing_projects if p.get("name") == pname), None)
            if target_p is None:
                target_p = {
                    "id": fix_id("project", ip.get("id", "")),
                    "name": pname,
                    "groups": [],
                }
                existing_projects.append(target_p)
                stat["project"] += 1

            for ig in iter_groups(ip):
                gname = ig.get("name", "未命名分组")
                target_g = next(
                    (g for g in target_p.setdefault("groups", []) if g.get("name") == gname),
                    None,
                )
                if target_g is None:
                    target_g = {
                        "id": fix_id("group", ig.get("id", "")),
                        "name": gname,
                        "commands": [],
                    }
                    target_p["groups"].append(target_g)
                    stat["group"] += 1

                existing_contents = {
                    (c.get("name", ""), c.get("content", ""))
                    for c in target_g.setdefault("commands", [])
                }
                used_names = {c.get("name", "") for c in target_g["commands"]}
                for ic in ig.get("commands", []) or []:
                    if not isinstance(ic, dict):
                        continue
                    ic_name = ic.get("name", "") or "未命名指令"
                    ic_content = ic.get("content", "")
                    if (ic_name, ic_content) in existing_contents:
                        continue
                    new_name = self._sc_qc_unique_cmd_name(ic_name, used_names)
                    if new_name != ic_name:
                        stat["renamed"] += 1
                    new_cmd = {
                        "id": fix_id("cmd", ic.get("id", "")),
                        "name": new_name,
                        "content": ic_content,
                        "send_type": ic.get("send_type", "text"),
                        "line_ending": ic.get("line_ending", ""),
                        "encoding": ic.get("encoding", "ascii"),
                    }
                    target_g["commands"].append(new_cmd)
                    used_names.add(new_name)
                    existing_contents.add((new_name, ic_content))
                    stat["cmd"] += 1

        self._sc_qc_save_data()
        self._sc_qc_refresh_all()
        QMessageBox.information(
            self, "导入完成",
            f"增量合入完成\n新增项目:{stat['project']}\n"
            f"新增分组:{stat['group']}\n新增指令:{stat['cmd']}\n重命名指令:{stat['renamed']}\n"
            f"(已跳过名称和内容完全相同的重复指令)",
        )

    def _sc_export_quick_cmds(self):
        project = self._sc_qc_current_project()
        if project is None:
            QMessageBox.warning(self, "提示", "当前没有可导出的项目")
            return
        self._sc_qc_export_project(project)

    def _sc_qc_export_project(self, project):
        if not isinstance(project, dict):
            return
        default_name = f"{project.get('name', 'project')}_快捷指令.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Quick Commands", default_name, "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        payload = {
            "version": "2.0",
            "quick_commands": {
                "version": "1.0",
                "projects": [
                    {
                        "id": project.get("id", ""),
                        "name": project.get("name", ""),
                        "groups": project.get("groups", []),
                    }
                ],
            },
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._sc_append_system(f"[INFO] Exported project: {project.get('name', '')}", force_primary=True)
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"写入失败:\n{e}")

    # --- persistence (unified config: KK_SerialConsole.json) ---
    #
    # 设计目标:
    #   - 所有串口工具配置（串口参数 / UI偏好 / 快捷指令）统一保存到单文件 KK_SerialConsole.json
    #   - 模块可能被**单独编译**分发, 因此用户目录不挂在 KK_Lab 应用名下,
    #     而是使用独立的 "SerialCom" 命名空间:
    #       打包态: %APPDATA%\SerialCom\
    #       开发态: <项目根>/user_data/SerialCom/
    #   - 严禁写到 EXE 同目录或 sys._MEIPASS, 兼容 Program Files / onefile 临时目录
    #   - 启动时自动加载, 优先顺序:
    #       1) 用户目录 (%APPDATA%\SerialCom\  /  user_data/SerialCom/)
    #       2) 回退: EXE 同目录 (打包态) / <项目根>/Results/ (开发态)
    #     回退来源仅做**只读**加载, 不会反写到用户目录, 避免污染系统配置.
    #   - 应用退出时由调用方触发 _sc_save_persisted_state()

    _SC_UNIFIED_FILENAME = "KK_SerialConsole.json"
    _SC_APP_NAMESPACE = "SerialCom"
    _SC_APP_VERSION = _APP_VERSION
    _SC_APP_AUTHOR = "KK_Lab Team"
    _SC_DEFAULT_WINDOW_SIZE = (1300, 850)
    _SC_WINDOW_MARGIN = 40


