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
    QPixmap, QShortcut, QTextCursor,
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
    _SC_HIGHLIGHT_PALETTE,
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

from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel

logger = get_logger(__name__)


class LogPanelMixin:
    """多 LOG 面板/独立窗口/面板设置 + 日志文件/自动保存/NTP + 日志核心追加与刷新。"""

    def _build_sc_log_area(self):
        """主日志面板：SerialLogPanel(full 过滤 + Save + 状态栏) + Mixin facade 别名。"""
        panel = SerialLogPanel(
            title="Serial Log",
            filter_mode="full",
            show_save_button=True,
            status_bar="primary",
            with_shadow=True,
            max_lines=self._sc_max_log_lines,
            show_timestamp=self._sc_show_timestamp,
        )
        panel.ntp_timestamp_provider = self._sc_ntp_timestamp
        panel.entry_renderer = self._sc_render_log_html
        panel.export_fast_path = self._sc_export_fast_path
        # 共享同一 list：兼容 Mixin/持久化层对 _sc_highlight_keywords 的既有引用
        panel.highlight_keywords = self._sc_highlight_keywords
        panel.raw_appended.connect(self._sc_write_to_log_files)
        panel.save_toggled.connect(self._sc_on_save_toggle)
        panel.cleared.connect(self._sc_on_primary_logs_cleared)
        panel.clicked.connect(self._sc_on_primary_panel_clicked)

        self._sc_log_panel = panel
        self._sc_log_area = panel
        self._sc_log_edit = panel.log_edit
        self._sc_all_logs = panel.all_logs
        self._sc_filter_btn = panel.filter_btn
        self._sc_filter_row = panel.filter_row
        self._sc_filter_input = panel.filter_input
        self._sc_filter_match_label = panel.filter_match_label
        self._sc_filter_regex_cb = panel.filter_regex_cb
        self._sc_filter_case_cb = panel.filter_case_cb
        self._sc_filter_invert_cb = panel.filter_invert_cb
        self._sc_filter_highlight_only_cb = panel.filter_highlight_only_cb
        self._sc_filter_before_spin = panel.filter_before_spin
        self._sc_filter_after_spin = panel.filter_after_spin
        self._sc_copy_btn = panel.copy_btn
        self._sc_export_btn = panel.export_btn
        self._sc_save_btn = panel.save_btn
        self._sc_clear_btn = panel.clear_btn
        self._sc_scroll_lock_btn = panel.scroll_lock_btn
        self._sc_status_bar = panel.status_bar
        self._sc_status_port_label = panel.status_port_label
        self._sc_status_baud_label = panel.status_baud_label
        self._sc_status_rx_label = panel.status_rx_label
        self._sc_status_tx_label = panel.status_tx_label
        self._sc_status_autobaud_label = panel.status_autobaud_label
        return panel

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
        """额外内嵌日志面板：SerialLogPanel(full 过滤 + basic 状态栏) + dict facade。"""
        comp = SerialLogPanel(
            title=config.get("title", "Serial Log"),
            filter_mode="full",
            status_bar="basic",
            compact_toolbar=True,
            with_border=True,
            max_lines=5000,
            notify_on_copy_export=True,
            port_text=f"Port: {config.get('port', 'Unconnected')}",
            baud_text=f"Baud rate: {config.get('baudrate', '-')}",
        )
        comp.setContextMenuPolicy(Qt.CustomContextMenu)

        panel = {
            "frame": comp,
            "log_edit": comp.log_edit,
            "clear_btn": comp.clear_btn,
            "scroll_btn": comp.scroll_lock_btn,
            "filter_btn": comp.filter_btn,
            "filter_row": comp.filter_row,
            "filter_input": comp.filter_input,
            "filter_match_label": comp.filter_match_label,
            "copy_btn": comp.copy_btn,
            "export_btn": comp.export_btn,
            "port_label": comp.status_port_label,
            "baud_label": comp.status_baud_label,
            "rx_label": comp.status_rx_label,
            "tx_label": comp.status_tx_label,
            "title_label": comp.title_label,
            "config": config,
            "conn": None,
            "read_thread": None,
            "read_worker": None,
            "paused": False,
            "stopped": False,
            "session_id": None,
        }

        # 面板管理项注入组件内置右键菜单（Highlight 项由组件统一提供）
        comp.context_menu_extra = lambda menu, p=panel: self._sc_extra_panel_menu_extra(p, menu)
        comp.customContextMenuRequested.connect(
            lambda pos, p=panel: self._sc_extra_panel_context_menu(p, comp.mapToGlobal(pos))
        )
        comp.clicked.connect(lambda p=panel: self._sc_on_log_panel_clicked(p, None))

        return panel

    def _sc_on_primary_panel_clicked(self):
        if self._sc_active_log_panel_index != 0:
            self._sc_active_log_panel_index = 0
            self._sc_active_session_id = "primary"
            self._sc_session_manager.set_active_session("primary")
            self._sc_update_panel_focus_style()

    def _sc_active_extra_panel(self):
        idx = getattr(self, "_sc_active_log_panel_index", 0)
        if 0 < idx <= len(self._sc_extra_log_panels):
            return self._sc_extra_log_panels[idx - 1]
        return None

    def _sc_extra_panel_is_connected(self, panel):
        if DEBUG_MOCK:
            session_id = panel.get("session_id")
            if session_id:
                session = self._sc_session_manager.get_session(session_id)
                return session is not None and session.connected
            return bool(panel.get("port_label") and "MOCK" in panel["port_label"].text())
        return panel.get("conn") is not None and panel["conn"].is_open

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

        self._sc_sync_top_control_state()

    def _sc_extra_panel_context_menu(self, panel, global_pos):
        """面板本体（日志编辑区以外）右键：仅弹面板管理菜单。"""
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
        self._sc_extra_panel_menu_extra(panel, menu)
        if menu.isEmpty():
            return
        menu.exec(global_pos)

    def _sc_extra_panel_menu_extra(self, panel, menu):
        """向右键菜单填充面板管理项（Connect/Disconnect、Settings、Remove）。"""
        is_connected = self._sc_extra_panel_is_connected(panel)

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

    def _sc_extra_panel_do_disconnect(self, panel):
        self._sc_extra_panel_disconnect(panel)
        # Disconnect 复位 Pause/Stop：重连后恢复正常的接收与显示
        panel["paused"] = False
        panel["stopped"] = False
        panel["frame"].set_display_paused(False)
        panel["port_label"].setText("Port: Disconnected")
        panel["port_label"].setStyleSheet(status_label_style("error", compact=True))
        self._sc_extra_panel_append_log(panel, "[INFO] Disconnected", _CLR_TEXT_INFO)
        self._sc_sync_top_control_state()

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
            self._sc_sync_top_control_state()
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
        self._sc_sync_top_control_state()

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
        # Stop 语义：保持连接但丢弃 RX 数据；Pause 由组件 display_paused 处理（数据保留）
        if panel.get("stopped"):
            return
        panel["frame"].append_rx_data(data)

    def _sc_extra_panel_append_log(self, panel, message, color=_CLR_TEXT_BODY):
        panel["frame"].append_log(message, color)

    def _sc_on_sidebar_toggle(self, checked):
        self._sc_sidebar_visible = checked
        self._sc_sidebar_widget.setVisible(checked)
        if checked:
            sizes = self._sc_body_splitter.sizes()
            if sizes and sizes[0] < self._sc_sidebar_min_width:
                center_width = max(sizes[1], 600) if len(sizes) > 1 else 600
                self._sc_body_splitter.setSizes([self._sc_sidebar_default_width, center_width])

    def _sc_on_footer_toggle(self, checked):
        """Footer 按钮：展开/隐藏底部 Quick Commands / Scripts 区域。"""
        self._sc_footer_visible = checked
        if not checked:
            sizes = self._sc_center_splitter.sizes()
            if sizes and sum(sizes) > 0:
                self._sc_center_splitter_sizes_before_hide = sizes
        self._sc_quick_area.setVisible(checked)
        if checked:
            restore = (
                getattr(self, "_sc_center_splitter_sizes_before_hide", None)
                or self._sc_center_splitter_default_sizes
            )
            self._sc_center_splitter.setSizes(list(restore))

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
        dlg.display_auto_scroll_cb.setChecked(self._sc_log_panel.auto_scroll)
        dlg.display_word_wrap_cb.setChecked(getattr(self, '_sc_word_wrap', True))
        dlg.display_show_line_num_cb.setChecked(getattr(self, '_sc_show_line_num', False))

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
            self._sc_log_panel.show_timestamp = self._sc_show_timestamp
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

            self._sc_log_panel.set_auto_scroll(dlg.display_auto_scroll_cb.isChecked())

            self._sc_word_wrap = dlg.display_word_wrap_cb.isChecked()
            from PySide6.QtWidgets import QTextEdit as _QTE
            self._sc_log_edit.setLineWrapMode(
                _QTE.WidgetWidth if self._sc_word_wrap else _QTE.NoWrap
            )

            new_show_line_num = dlg.display_show_line_num_cb.isChecked()
            if new_show_line_num != getattr(self, '_sc_show_line_num', False):
                self._sc_show_line_num = new_show_line_num
                self._sc_rebuild_log_view()

            self._sc_apply_auto_detect_settings(dlg)

    def _sc_apply_max_log_lines(self, value):
        value = max(500, min(int(value), self._SC_MAX_LOG_LINES_LIMIT))
        if value == getattr(self, '_sc_max_log_lines', self._SC_MAX_LOG_LINES_DEFAULT):
            return
        self._sc_max_log_lines = value
        self._sc_log_panel.set_max_lines(value)

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
        self._sc_log_panel.append_log(message, color)

    def _sc_export_fast_path(self):
        """导出优先路径：临时日志落盘文件（flush 后供组件直接复制）。"""
        temp_file = getattr(self, "_sc_log_temp_path", None)
        if temp_file and os.path.isfile(temp_file):
            handle = getattr(self, "_sc_log_temp_handle", None)
            if handle is not None:
                try:
                    handle.flush()
                except OSError:
                    pass
            return temp_file
        return None

    # --- 日志渲染：行号 + 右键高亮 + 过滤高亮 ---

    def _sc_render_log_html(self, base_html, line_no, apply_filter_highlight=False):
        """主面板 entry_renderer：过滤/关键词高亮复用组件统一实现，此处仅加行号前缀。"""
        panel = self._sc_log_panel
        html = panel.apply_highlights(base_html, apply_filter_highlight)
        if self._sc_show_line_num:
            lineno_html = f'<span style="color:{_CLR_TEXT_LINENO};">{line_no:>5} </span>'
            html = lineno_html + html
        return html

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

