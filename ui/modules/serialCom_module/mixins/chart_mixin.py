# -*- coding: utf-8 -*-
"""图表配置/控制器/喂线/图表对话框 + 自动波特率 RX 喂入。"""

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


class ChartMixin:
    """图表配置/控制器/喂线/图表对话框 + 自动波特率 RX 喂入。"""

    def _sc_ensure_chart_config(self):
        if self._sc_chart_config is None:
            from ui.modules.serialCom_module.serial_chart_model import ChartConfig
            self._sc_chart_config = ChartConfig()
        return self._sc_chart_config

    def _sc_ensure_chart_controller(self):
        if self._sc_chart_controller is None:
            from ui.modules.serialCom_module.serial_chart_controller import (
                SerialChartController,
            )
            self._sc_chart_controller = SerialChartController(
                self._sc_ensure_chart_config()
            )
        return self._sc_chart_controller

    def _sc_chart_feed_line(self, line, session_id="active", rx_time=None):
        controller = self._sc_chart_controller
        if controller is None:
            return
        try:
            controller.feed_line(line, session_id=session_id, rx_time=rx_time)
        except Exception:
            logger.error("chart feed_line failed", exc_info=True)

    def _sc_chart_feed_bytes(self, data, session_id="active", rx_time=None):
        controller = self._sc_chart_controller
        if controller is None:
            return
        try:
            controller.feed_bytes(data, session_id=session_id, rx_time=rx_time)
        except Exception:
            logger.error("chart feed_bytes failed", exc_info=True)

    def _sc_open_chart_dialog(self):
        try:
            import pyqtgraph  # noqa: F401
        except Exception:
            logger.error("pyqtgraph unavailable", exc_info=True)
            QMessageBox.warning(self, "Chart", "pyqtgraph is not available.")
            return

        self._sc_ensure_chart_controller()

        if self._sc_chart_dialog is not None:
            try:
                self._sc_chart_dialog.raise_()
                self._sc_chart_dialog.activateWindow()
                return
            except RuntimeError:
                self._sc_chart_dialog = None

        from ui.modules.serialCom_module.serial_chart_dialog import SerialChartDialog

        dlg = SerialChartDialog(
            self,
            config=self._sc_ensure_chart_config(),
            on_config_changed=self._sc_on_chart_config_changed,
        )
        # 让宿主 feed 直接走对话框内置 controller，避免双份缓存
        self._sc_chart_controller = dlg.controller
        self._sc_chart_dialog = dlg
        dlg.finished.connect(self._sc_on_chart_dialog_finished)
        dlg.show()

    def _sc_on_chart_dialog_finished(self, *_):
        dlg = self._sc_chart_dialog
        self._sc_chart_dialog = None
        cfg = self._sc_ensure_chart_config()
        if not cfg.capture_when_dialog_closed:
            self._sc_chart_controller = None
        else:
            from ui.modules.serialCom_module.serial_chart_controller import (
                SerialChartController,
            )
            self._sc_chart_controller = SerialChartController(cfg)
        self._sc_on_chart_config_changed()
        if dlg is not None:
            dlg.deleteLater()

    def _sc_on_chart_config_changed(self):
        try:
            self._sc_save_persisted_state()
        except Exception:
            logger.error("save chart config failed", exc_info=True)

    def _sc_feed_auto_baud_monitor(self, data: bytes):
        monitor = self._sc_auto_baud_monitor
        if not monitor.enabled:
            return
        if self._sc_auto_baud_pending_first_rx:
            self._sc_auto_baud_initial_buf.extend(data)
            cfg = monitor._config
            buf_len = len(self._sc_auto_baud_initial_buf)
            elapsed_ms = (time.perf_counter() - self._sc_auto_baud_initial_ts) * 1000
            if buf_len >= cfg["scan_sample_bytes"] or elapsed_ms >= cfg["scan_timeout_ms"]:
                self._sc_auto_baud_pending_first_rx = False
                sample = bytes(self._sc_auto_baud_initial_buf)
                self._sc_auto_baud_initial_buf = bytearray()
                s = score_rx_data(sample)
                if s is not None and s >= cfg["lock_threshold"]:
                    self._sc_append_system(
                        f"[INFO] Current baudrate {self._serial_baudrate} score={s}, locked.",
                        force_primary=True,
                    )
                    monitor.state = AutoBaudState.LOCKED
                    monitor.reset()
                    self._sc_on_auto_baud_state_changed(AutoBaudState.LOCKED.value)
                else:
                    score_info = f"score={s}" if s is not None else "no data"
                    self._sc_append_system(
                        f"[INFO] Current baudrate {self._serial_baudrate} {score_info}, scanning candidates...",
                        force_primary=True,
                    )
                    self._sc_start_auto_baud_scan("initial")
            return
        monitor.hex_mode = self._sc_rx_display_hex
        result = monitor.on_rx_data(data)
        if result is None:
            return
        action = result.get("action")
        if action == "suspect":
            self._sc_append_system("[INFO] RX quality degraded. Enter SUSPECT state.", force_primary=True)
            self._sc_on_auto_baud_state_changed(AutoBaudState.SUSPECT.value)
        elif action == "recovered":
            self._sc_append_system("[INFO] RX quality recovered.", force_primary=True)
            self._sc_on_auto_baud_state_changed(AutoBaudState.LOCKED.value)
        elif action == "scan_needed":
            self._sc_append_system("[INFO] Sustained RX quality issue. Starting rescan...", force_primary=True)
            self._sc_start_auto_baud_scan("runtime")

    # --- quick commands (项目 -> 分组 -> 指令) ---

    # ==================== Scripts 子系统 ====================


