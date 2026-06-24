#
# python -m ui.modules.serialCom_module_frame
#

import os as _os
import sys as _sys
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)
from ui.resource_path import get_resource_base as _get_resource_base
from ui.resource_path import get_resource_base
_PROJECT_ROOT = _get_resource_base()
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

import json
import importlib as _importlib
import os
import re
import time
import serial
import serial.tools.list_ports
from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy,
    QFrame, QWidget, QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QScrollArea, QSplitter, QApplication, QMenu, QFileDialog, QGridLayout,
    QSpinBox, QDialog, QDialogButtonBox, QTabWidget,
    QMessageBox, QTabBar, QGraphicsDropShadowEffect, QGraphicsBlurEffect,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPlainTextEdit, QTreeWidget, QTreeWidgetItem, QToolButton,
    QListWidget, QListWidgetItem,
)
import uuid as _uuid
from PySide6.QtCore import (
    Signal, QThread, QObject, QTimer, QRectF, Qt, QSize, QRect, QPoint,
    QPropertyAnimation, QEasingCurve, Property, QMimeData,
)
from PySide6.QtGui import (
    QIcon, QPainter, QPixmap, QColor, QAction, QPen, QFont,
    QShortcut, QKeySequence, QCursor,
)
from PySide6.QtSvg import QSvgRenderer

from debug_config import DEBUG_MOCK
from version import __version__ as _APP_VERSION
from log_config import get_logger
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.utils.icon_utils import tinted_svg_pixmap as _tinted_svg_pixmap
from core.serial_io import SerialReadWorker as _SerialReadWorker
from core.serial_io import NtpSyncWorker as _NtpSyncWorker


def _select_serialcom_style_module():
    override = _os.environ.get("KK_SERIALCOM_STYLE", "").strip().lower()
    if override in ("apple", "light", "standalone"):
        return "ui.modules.serialCom_module.serialCom_apple_gpt5p5_style"
    if override in ("dark", "main"):
        return "ui.modules.serialCom_module.serialCom_dark_style"

    exe_name = _os.path.splitext(_os.path.basename(getattr(_sys, "executable", "")))[0].lower()
    if __name__ == "__main__" or (getattr(_sys, "frozen", False) and exe_name == "serialcom_module"):
        _os.environ["KK_SERIALCOM_STYLE"] = "light"
        return "ui.modules.serialCom_module.serialCom_apple_gpt5p5_style"
    return "ui.modules.serialCom_module.serialCom_dark_style"


_SERIALCOM_STYLE_EXPORTS = (
    "DARK_CARD_STYLE", "_CLR_BG_CARD", "_CLR_BG_LOG", "_CLR_BG_MAIN", "_CLR_BG_PANEL",
    "_CLR_BLUE",
    "_CLR_BORDER", "_CLR_BORDER_HOVER", "_CLR_BORDER_SOFT", "_CLR_CONNECT_BG", "_CLR_CONNECT_FG",
    "_CLR_CONNECT_TEXT", "_CLR_CURSOR", "_CLR_DISCONNECT_TEXT", "_CLR_ERROR",
    "_CLR_FILTER_BG", "_CLR_FILTER_BORDER", "_CLR_FILTER_TEXT", "_CLR_INPUT_BG",
    "_CLR_INPUT_TEXT", "_CLR_ROSE_ICON", "_CLR_RX", "_CLR_SCROLLBAR",
    "_CLR_SCROLLBAR_HV", "_CLR_SELECTION_BG", "_CLR_SELECTION_TEXT", "_CLR_SEND_BG",
    "_CLR_SEND_HOVER", "_CLR_SEND_PRESS", "_CLR_TEXT_ACCENT", "_CLR_TEXT_BODY",
    "_CLR_TEXT_BTN", "_CLR_TEXT_BTN_LOG", "_CLR_TEXT_INFO", "_CLR_TEXT_LABEL",
    "_CLR_TEXT_LINENO", "_CLR_TEXT_MUTED", "_CLR_TEXT_SUBTITLE", "_CLR_TEXT_TIME",
    "_CLR_TEXT_TITLE", "_CLR_TEXT_WHITE", "_CLR_TOGGLE_ON", "_CLR_TX", "_CLR_WARN_ICON", "_CLR_WARNING",
    "_DLG_STYLE", "_SERIAL_BTN_HEIGHT", "_SERIAL_BTN_ICON_SIZE", "_SERIAL_BTN_RADIUS",
    "_TERM_FONT", "_UI_FONT", "_serial_connect_style", "_serial_disconnect_style",
    "_serial_search_style", "body_splitter_style", "center_vsplitter_style",
    "center_widget_style",
    "checkbox_style", "compact_spinbox_style", "dialog_backdrop_style",
    "frameless_chrome_style", "script_editor_dialog_style", "dialog_cancel_button_style",
    "dialog_line_edit_style", "dialog_ok_button_style", "extra_log_error_color",
    "field_label_style", "filter_input_style", "filter_match_label_style",
    "history_combo_style", "inline_serial_label_style",
    "inline_serial_search_button_extra_style", "log_color_info_style",
    "log_color_info_text", "log_document_style", "log_edit_style", "log_frame_style",
    "log_panel_button_style", "log_title_style", "log_title_icon_color", "log_toolbar_button_style",
    "log_icon_button_style",
    "main_connect_button_style", "project_tabs_style", "quick_action_overlay_style",
    "quick_action_overlay_container_style",
    "quick_add_button_style", "quick_group_button_style",
    "quick_button_container_style", "quick_button_scroll_style", "quick_cmd_dialog_style",
    "quick_command_button_style", "quick_combo_style", "quick_group_combo_bg_style",
    "quick_commands_panel_style",
    "quick_preview_popup_shadow", "quick_preview_popup_style", "quick_toolbar_button_style",
    "bottom_tabs_style",
    "section_card_style", "section_card_shadow", "section_header_divider_style",
    "panel_divider_style",
    "script_stop_button_style", "script_add_step_button_style",
    "section_title_style", "send_button_style", "separator_style",
    "sidebar_toggle_button_style", "auto_scroll_button_style",
    "sidebar_toggle_icon_colors", "auto_scroll_icon_colors",
    "sidebar_wrapper_style", "small_label_style", "status_bar_style", "status_label_style",
    "thin_scrollbar_style", "toolbar_connect_button_style", "toolbar_style", "toggle_colors",
    "transparent_background_style", "transparent_scroll_area_style",
    "transparent_toolbar_button_style", "unit_label_style", "SERIAL_SCROLLBAR_STYLE",
    "SerialDarkComboBox", "SerialHistoryComboBox", "_CLR_HISTORY_COMBO_BG",
)

_SERIALCOM_STYLE_MODULE = _select_serialcom_style_module()
_serialcom_style = _importlib.import_module(_SERIALCOM_STYLE_MODULE)
globals().update({
    _name: getattr(_serialcom_style, _name)
    for _name in _SERIALCOM_STYLE_EXPORTS
})
del _serialcom_style
from core.auto_baud_detector import (
    AutoBaudState, AutoBaudMonitor, AutoBaudScanWorker,
    AUTO_BAUD_CONFIG, score_rx_data,
)


logger = get_logger(__name__)


_SVG_COMMON_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Common"
)
_SVG_SERIAL_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Serial",
)
_SVG_LOGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Logs",
)
_SEARCH_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "unlink.svg")

from ui.modules.serialCom_module.widgets import (
    _SerialSearchButton,
    _SearchSerialPortWorker,
    _FramelessChromeDialog,
    _MixinSerialSettingsDialog,
    _update_serial_btn_state,
    _SERIAL_BTN_FIXED_WIDTH,
)

MODE_SEARCH_SELECT = "search_and_select"
MODE_FULL = "full"
MODE_INLINE = "inline"


from ui.modules.serialCom_module.mixins.connection_mixin import ConnectionMixin
from ui.modules.serialCom_module.mixins.toolbar_mixin import ToolbarMixin
from ui.modules.serialCom_module.mixins.log_panel_mixin import LogPanelMixin
from ui.modules.serialCom_module.mixins.filter_save_mixin import FilterSaveMixin
from ui.modules.serialCom_module.mixins.send_mixin import SendMixin
from ui.modules.serialCom_module.mixins.chart_mixin import ChartMixin
from ui.modules.serialCom_module.mixins.script_mixin import ScriptMixin


class SerialComMixin(ConnectionMixin, ToolbarMixin, LogPanelMixin, FilterSaveMixin, SendMixin, ChartMixin, ScriptMixin):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def complete_serialComWidget(self, parent_layout):
        self._sc_rx_bytes = 0
        self._sc_tx_bytes = 0
        self._sc_paused = False
        self._sc_auto_scroll = True
        self._sc_rx_line_buf = ""
        self._sc_rx_flush_timer = None
        self._sc_all_logs = []
        self._sc_max_log_lines = self._SC_MAX_LOG_LINES_DEFAULT
        self._sc_log_auto_save = False
        self._sc_log_save_path = ''
        self._sc_log_file_handle = None
        self._sc_log_file_path = None
        self._sc_log_temp_handle = None
        self._sc_log_temp_path = None
        self._sc_save_handle = None
        self._sc_save_path = None
        self._sc_save_keep_timestamp = True
        self._sc_rx_display_hex = False
        self._sc_tx_display_hex = False
        self._sc_show_timestamp = True
        self._sc_use_ntp = False
        self._sc_ntp_offset = 0.0
        self._sc_ntp_synced = False
        self._sc_ntp_thread = None
        self._sc_ntp_worker = None
        self._sc_line_ending = "\r\n"
        self._sc_show_send = True
        self._sc_show_system_log = False
        self._sc_line_by_line = False
        self._sc_send_history = []
        self._sc_quick_commands = []  # 兼容占位，已不再使用
        self._sc_qc_data = self._sc_qc_default_data()
        self._sc_script_data = self._sc_script_default_data()
        self._sc_script_running = False
        self._sc_script_paused = False
        self._sc_script_steps = []
        self._sc_script_step_index = 0
        self._sc_script_loop_remaining = 0
        self._sc_script_wait_keyword = ""
        self._sc_script_wait_buffer = ""
        self._sc_script_timer = QTimer(self)
        self._sc_script_timer.setSingleShot(True)
        self._sc_script_timer.timeout.connect(self._sc_script_on_timeout)
        self._sc_sidebar_visible = True
        self._sc_extra_log_panels = []
        self._sc_active_log_panel_index = 0
        self._sc_filter_dirty = False
        self._sc_filter_last_count = 0
        self._sc_filter_applied_pattern = ""
        self._sc_filter_applied_use_regex = False
        self._sc_filter_applied_case = False
        self._sc_filter_applied_invert = False
        self._sc_filter_applied_before = 0
        self._sc_filter_applied_after = 0

        self._sc_chart_config = None
        self._sc_chart_controller = None
        self._sc_chart_dialog = None

        self._sc_auto_baud_monitor = AutoBaudMonitor()
        self._sc_auto_baud_monitor.enabled = True
        self._sc_auto_baud_monitor.runtime_redetect_enabled = True
        self._sc_auto_baud_scan_thread = None
        self._sc_auto_baud_scan_worker = None
        self._sc_auto_baud_pending_first_rx = False
        self._sc_auto_baud_initial_buf = bytearray()
        self._sc_auto_baud_initial_ts = 0.0

        outer = QVBoxLayout()
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        self._sc_toolbar = self._build_sc_toolbar()
        outer.addWidget(self._sc_toolbar)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setHandleWidth(10)
        body_splitter.setStyleSheet(body_splitter_style())

        self._sc_body_splitter = body_splitter
        self._sc_sidebar_default_width = 250
        self._sc_sidebar_min_width = 237
        self._sc_sidebar_widget = self._build_sc_sidebar()
        body_splitter.addWidget(self._sc_sidebar_widget)

        center_widget = QFrame()
        center_widget.setObjectName("scCenterWidget")
        center_widget.setFrameShape(QFrame.NoFrame)
        center_widget.setAutoFillBackground(True)
        center_widget.setStyleSheet(center_widget_style())
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.setSpacing(10)

        center_splitter = QSplitter(Qt.Vertical)
        center_splitter.setObjectName("scCenterVSplitter")
        center_splitter.setHandleWidth(6)
        center_splitter.setChildrenCollapsible(False)
        center_splitter.setStyleSheet(center_vsplitter_style())
        self._sc_center_splitter = center_splitter

        top_section = QWidget()
        top_section_layout = QVBoxLayout(top_section)
        top_section_layout.setContentsMargins(0, 0, 0, 0)
        top_section_layout.setSpacing(10)

        self._sc_log_container = QWidget()
        self._sc_log_grid = QGridLayout(self._sc_log_container)
        self._sc_log_grid.setContentsMargins(0, 0, 0, 0)
        self._sc_log_grid.setSpacing(10)

        self._sc_log_area = self._build_sc_log_area()
        self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
        top_section_layout.addWidget(self._sc_log_container, 1)

        self._sc_send_area = self._build_sc_send_area()
        top_section_layout.addWidget(self._sc_send_area)

        self._sc_quick_area = self._build_sc_quick_commands()
        self._sc_quick_area.setMinimumHeight(178)

        center_splitter.addWidget(top_section)
        center_splitter.addWidget(self._sc_quick_area)
        center_splitter.setStretchFactor(0, 1)
        center_splitter.setStretchFactor(1, 0)
        self._sc_center_splitter_default_sizes = [680, 185]
        center_splitter.setSizes(self._sc_center_splitter_default_sizes)

        self._sc_center_split_save_timer = QTimer(self)
        self._sc_center_split_save_timer.setSingleShot(True)
        self._sc_center_split_save_timer.setInterval(400)
        self._sc_center_split_save_timer.timeout.connect(self._sc_save_persisted_state)
        center_splitter.splitterMoved.connect(
            lambda *_: self._sc_center_split_save_timer.start()
        )

        center_layout.addWidget(center_splitter, 1)

        body_splitter.addWidget(center_widget)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setSizes([self._sc_sidebar_default_width, 900])

        outer.addWidget(body_splitter, 1)

        parent_layout.addLayout(outer)

        self._bind_sc_signals()

        self._sc_pending_html = []
        self._sc_flush_timer = QTimer()
        self._sc_flush_timer.setInterval(100)
        self._sc_flush_timer.timeout.connect(self._sc_flush_pending_logs)
        self._sc_flush_timer.start()

        self._sc_load_persisted_state()
        self._sc_start_temp_log()

    # --- toolbar ---

    def _sc_default_persisted_state(self, quick_commands=None, scripts=None) -> dict:
        return {
            "version": "2.0",
            "serial": {
                "port": "",
                "baudrate": "921600",
                "auto_detect": True,
                "databits": "8",
                "stopbits": "1",
                "parity": "None",
                "flow_control": "None",
                "auto_detect_config": dict(AUTO_BAUD_CONFIG),
            },
            "ui": {
                "rx_display_hex": False,
                "tx_display_hex": False,
                "show_timestamp": True,
                "use_ntp": False,
                "line_ending": "\r\n",
                "show_send": True,
                "show_system_log": False,
                "line_by_line": False,
                "sidebar_visible": True,
                "center_split_sizes": [680, 185],
            },
            "send_history": [],
            "quick_commands": quick_commands or self._sc_qc_default_data(),
            "scripts": scripts or self._sc_script_default_data(),
            "chart": {},
        }

    def _sc_user_config_dir(self) -> str:
        if getattr(_sys, "frozen", False):
            base = _os.environ.get("APPDATA")
            if not base:
                base = _os.path.join(_os.path.expanduser("~"), "AppData", "Roaming")
            root = _os.path.join(base, self._SC_APP_NAMESPACE)
        else:
            root = _os.path.join(_PROJECT_ROOT, "user_data", self._SC_APP_NAMESPACE)
        try:
            _os.makedirs(root, exist_ok=True)
        except OSError:
            pass
        return root

    def _sc_persisted_path(self) -> str:
        return os.path.join(self._sc_user_config_dir(), self._SC_UNIFIED_FILENAME)

    def _sc_fallback_dir(self) -> str:
        if getattr(_sys, "frozen", False):
            return _os.path.dirname(_sys.executable)
        return _os.path.join(_PROJECT_ROOT, "Results")

    def _sc_fallback_path(self) -> str:
        return os.path.join(self._sc_fallback_dir(), self._SC_UNIFIED_FILENAME)

    def _sc_screen_available_geometry_for(self, point=None) -> QRect:
        app = QApplication.instance()
        screen = None
        if app is not None and point is not None:
            screen = app.screenAt(point)
        if screen is None and app is not None:
            screen = app.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
        return QRect(0, 0, 1280, 720)

    def _sc_default_window_geometry(self) -> QRect:
        available = self._sc_screen_available_geometry_for()
        target_w, target_h = self._SC_DEFAULT_WINDOW_SIZE
        margin = self._SC_WINDOW_MARGIN
        width = min(target_w, max(640, available.width() - margin), int(available.width() * 0.88))
        height = min(target_h, max(480, available.height() - margin), int(available.height() * 0.88))
        x = available.x() + max(0, (available.width() - width) // 2)
        y = available.y() + max(0, (available.height() - height) // 2)
        return QRect(x, y, width, height)

    def _sc_collect_window_state(self) -> dict:
        if not self.isWindow() or not self.isVisible() or self.isMinimized():
            return {}

        geom = self.normalGeometry() if self.isMaximized() else self.geometry()
        if geom.width() <= 0 or geom.height() <= 0:
            return {}

        return {
            "x": int(geom.x()),
            "y": int(geom.y()),
            "width": int(geom.width()),
            "height": int(geom.height()),
            "maximized": bool(self.isMaximized()),
        }

    def _sc_clamped_window_geometry(self, window_cfg: dict) -> QRect:
        saved = QRect(
            int(window_cfg.get("x", 0)),
            int(window_cfg.get("y", 0)),
            int(window_cfg.get("width", 0)),
            int(window_cfg.get("height", 0)),
        )
        if saved.width() <= 0 or saved.height() <= 0:
            return self._sc_default_window_geometry()

        available = self._sc_screen_available_geometry_for(saved.center())
        margin = self._SC_WINDOW_MARGIN
        max_w = max(1, available.width() - margin)
        max_h = max(1, available.height() - margin)
        width = min(saved.width(), max_w)
        height = min(saved.height(), max_h)

        x = min(max(saved.x(), available.x()), available.right() - width + 1)
        y = min(max(saved.y(), available.y()), available.bottom() - height + 1)
        return QRect(x, y, width, height)

    def _sc_apply_window_geometry(self) -> None:
        window_cfg = getattr(self, "_sc_window_geometry", None)
        if isinstance(window_cfg, dict):
            self.setGeometry(self._sc_clamped_window_geometry(window_cfg))
            self._sc_restore_maximized = bool(window_cfg.get("maximized", False))
            return

        self.setGeometry(self._sc_default_window_geometry())
        self._sc_restore_maximized = False

    def _sc_about_info(self) -> dict:
        mode = "Packaged" if getattr(_sys, "frozen", False) else "Development"
        app = QApplication.instance()
        screen_text = "Unknown"
        if app is not None and app.primaryScreen() is not None:
            geo = app.primaryScreen().availableGeometry()
            screen_text = f"{geo.width()} x {geo.height()} available"
        quick_count = 0
        qc_data = getattr(self, "_sc_qc_data", {})
        if isinstance(qc_data, dict):
            quick_count = sum(
                len(g.get("commands", []))
                for p in qc_data.get("projects", [])
                for g in p.get("groups", [])
            )
        try:
            from ui.modules.serialCom_module import MODULE_VERSION as module_version
        except Exception:
            module_version = "0.0.0"
        return {
            "Application": "KK Serial Console",
            "Version": self._SC_APP_VERSION,
            "Module version": module_version,
            "Author": self._SC_APP_AUTHOR,
            "Config schema": "2.0",
            "Config file": self._sc_persisted_path(),
            "Config directory": self._sc_user_config_dir(),
            "Quick Commands": str(quick_count),
            "Runtime mode": mode,
            "Primary screen": screen_text,
        }

    def _sc_migrate_legacy_config(self):
        base = self._sc_user_config_dir()
        legacy_cfg = os.path.join(base, "config.json")
        legacy_qc = os.path.join(base, "quick_commands.json")
        migrated = False

        if os.path.isfile(legacy_cfg):
            try:
                with open(legacy_cfg, "r", encoding="utf-8") as f:
                    self._sc_apply_persisted_state(json.load(f))
                migrated = True
            except Exception:
                pass

        if os.path.isfile(legacy_qc):
            try:
                with open(legacy_qc, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                parsed = self._sc_parse_quick_cmds_payload(raw)
                if parsed is not None:
                    self._sc_qc_data = parsed
                    migrated = True
            except Exception:
                pass

        if not migrated:
            fb_dir = self._sc_fallback_dir()
            fb_cfg = os.path.join(fb_dir, "config.json")
            fb_qc = os.path.join(fb_dir, "quick_commands.json")
            if os.path.isfile(fb_cfg):
                try:
                    with open(fb_cfg, "r", encoding="utf-8") as f:
                        self._sc_apply_persisted_state(json.load(f))
                except Exception:
                    pass
            if os.path.isfile(fb_qc):
                try:
                    with open(fb_qc, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    parsed = self._sc_parse_quick_cmds_payload(raw)
                    if parsed is not None:
                        self._sc_qc_data = parsed
                except Exception:
                    pass

    def _sc_parse_quick_cmds_payload(self, data):
        """校验并标准化快捷指令 JSON; 不符合新格式返回 None."""
        if not isinstance(data, dict):
            return None
        if "projects" not in data or not isinstance(data["projects"], list):
            return None
        normalized = {
            "version": str(data.get("version", "1.0")),
            "last_project_id": str(data.get("last_project_id", "")),
            "last_group_id": str(data.get("last_group_id", "")),
            "projects": [],
        }
        for p in data["projects"]:
            if not isinstance(p, dict):
                continue
            np = {
                "id": str(p.get("id") or self._sc_qc_gen_id("project")),
                "name": str(p.get("name", "未命名项目")),
                "groups": [],
            }

            def _norm_group(g):
                ng = {
                    "id": str(g.get("id") or self._sc_qc_gen_id("group")),
                    "name": str(g.get("name", "未命名分组")),
                    "commands": [],
                }
                for c in g.get("commands", []) or []:
                    if not isinstance(c, dict):
                        continue
                    ng["commands"].append({
                        "id": str(c.get("id") or self._sc_qc_gen_id("cmd")),
                        "name": str(c.get("name", "")),
                        "content": str(c.get("content", "")),
                        "send_type": str(c.get("send_type", "text")),
                        "line_ending": str(c.get("line_ending", "")),
                        "encoding": str(c.get("encoding", "ascii")),
                    })
                return ng

            # 兼容旧格式：projects[].regions[].groups[] -> 拍平为 groups[]，分组重名加 _合并 后缀
            used_names = set()

            def _uniq_name(base):
                if base not in used_names:
                    used_names.add(base)
                    return base
                cand = f"{base}_合并"
                idx = 1
                while cand in used_names:
                    cand = f"{base}_合并_{idx}"
                    idx += 1
                used_names.add(cand)
                return cand

            if isinstance(p.get("regions"), list):
                for r in p.get("regions", []) or []:
                    if not isinstance(r, dict):
                        continue
                    for g in r.get("groups", []) or []:
                        if not isinstance(g, dict):
                            continue
                        ng = _norm_group(g)
                        ng["name"] = _uniq_name(ng["name"])
                        np["groups"].append(ng)
            for g in p.get("groups", []) or []:
                if not isinstance(g, dict):
                    continue
                ng = _norm_group(g)
                ng["name"] = _uniq_name(ng["name"])
                np["groups"].append(ng)
            normalized["projects"].append(np)
        return normalized

    def _sc_collect_persisted_state(self) -> dict:
        port_text = ""
        if hasattr(self, "_sc_port_combo"):
            port_text = self._sc_port_combo.currentText()
        baud_text = "921600"
        if hasattr(self, "_sc_baud_combo"):
            baud_text = self._sc_baud_combo.currentText()
        auto_detect = False
        if hasattr(self, "_sc_auto_detect_cb"):
            auto_detect = self._sc_auto_detect_cb.isChecked()
        databit = "8"
        if hasattr(self, "_sc_databit_combo"):
            databit = self._sc_databit_combo.currentText()
        stopbit = "1"
        if hasattr(self, "_sc_stopbit_combo"):
            stopbit = self._sc_stopbit_combo.currentText()
        parity = "None"
        if hasattr(self, "_sc_parity_combo"):
            parity = self._sc_parity_combo.currentText()
        flow_ctrl = "None"
        if hasattr(self, "_sc_flow_combo"):
            flow_ctrl = self._sc_flow_combo.currentText()

        auto_detect_config = {}
        if hasattr(self, "_sc_auto_baud_monitor"):
            m = self._sc_auto_baud_monitor
            auto_detect_config = {
                "runtime_redetect_enabled": m.runtime_redetect_enabled,
                "candidate_baudrates": list(m._config.get("candidate_baudrates", [])),
                "lock_threshold": m._config.get("lock_threshold", 85),
                "bad_threshold": m._config.get("bad_threshold", 40),
                "bad_windows_to_suspect": m._config.get("bad_windows_to_suspect", 3),
                "suspect_windows_to_scan": m._config.get("suspect_windows_to_scan", 2),
                "monitor_window_max_time_ms": m._config.get("monitor_window_max_time_ms", 500),
                "switch_cooldown_ms": m._config.get("switch_cooldown_ms", 5000),
                "switch_score_margin": m._config.get("switch_score_margin", 15),
                "confirm_scan_rounds": m._config.get("confirm_scan_rounds", 2),
            }

        persisted = self._sc_default_persisted_state(
            quick_commands=getattr(self, "_sc_qc_data", self._sc_qc_default_data()),
            scripts=getattr(self, "_sc_script_data", self._sc_script_default_data()),
        )
        persisted["serial"].update({
            "port": port_text,
            "baudrate": baud_text,
            "auto_detect": auto_detect,
            "databits": databit,
            "stopbits": stopbit,
            "parity": parity,
            "flow_control": flow_ctrl,
            "auto_detect_config": auto_detect_config,
        })
        persisted["ui"].update({
            "rx_display_hex": getattr(self, "_sc_rx_display_hex", False),
            "tx_display_hex": getattr(self, "_sc_tx_display_hex", False),
            "show_timestamp": getattr(self, "_sc_show_timestamp", True),
            "use_ntp": getattr(self, "_sc_use_ntp", False),
            "line_ending": getattr(self, "_sc_line_ending", "\r\n"),
            "show_send": getattr(self, "_sc_show_send", True),
            "show_system_log": getattr(self, "_sc_show_system_log", False),
            "line_by_line": getattr(self, "_sc_line_by_line", False),
            "sidebar_visible": getattr(self, "_sc_sidebar_visible", True),
            "log_auto_save": getattr(self, "_sc_log_auto_save", False),
            "log_save_path": getattr(self, "_sc_log_save_path", ""),
            "center_split_sizes": (
                list(self._sc_center_splitter.sizes())
                if hasattr(self, "_sc_center_splitter")
                else []
            ),
        })
        persisted["send_history"] = list(getattr(self, "_sc_send_history", []))[-50:]
        if getattr(self, "_sc_chart_config", None) is not None:
            try:
                persisted["chart"] = self._sc_chart_config.to_dict()
            except Exception:
                logger.error("收集 chart 配置失败", exc_info=True)
        window_state = self._sc_collect_window_state()
        if window_state:
            persisted["window"] = window_state
        elif isinstance(getattr(self, "_sc_window_geometry", None), dict):
            persisted["window"] = self._sc_window_geometry
        return persisted

    def _sc_apply_persisted_state(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        is_v2 = data.get("version") == "2.0" or "serial" in data

        if is_v2:
            serial_cfg = data.get("serial", {})
            if isinstance(serial_cfg, dict):
                port = serial_cfg.get("port", "")
                if port and hasattr(self, "_sc_port_combo"):
                    idx = self._sc_port_combo.findText(port)
                    if idx >= 0:
                        self._sc_port_combo.setCurrentIndex(idx)
                    else:
                        self._sc_last_port = port

                baud = serial_cfg.get("baudrate", "")
                if baud and hasattr(self, "_sc_baud_combo"):
                    idx = self._sc_baud_combo.findText(str(baud))
                    if idx >= 0:
                        self._sc_baud_combo.setCurrentIndex(idx)
                    else:
                        self._sc_baud_combo.setCurrentText(str(baud))

                if hasattr(self, "_sc_auto_detect_cb"):
                    self._sc_auto_detect_cb.setChecked(bool(serial_cfg.get("auto_detect", False)))

                if hasattr(self, "_sc_databit_combo"):
                    db = serial_cfg.get("databits", "8")
                    idx = self._sc_databit_combo.findText(str(db))
                    if idx >= 0:
                        self._sc_databit_combo.setCurrentIndex(idx)

                if hasattr(self, "_sc_stopbit_combo"):
                    sb = serial_cfg.get("stopbits", "1")
                    idx = self._sc_stopbit_combo.findText(str(sb))
                    if idx >= 0:
                        self._sc_stopbit_combo.setCurrentIndex(idx)

                if hasattr(self, "_sc_parity_combo"):
                    pa = serial_cfg.get("parity", "None")
                    idx = self._sc_parity_combo.findText(str(pa))
                    if idx >= 0:
                        self._sc_parity_combo.setCurrentIndex(idx)

                if hasattr(self, "_sc_flow_combo"):
                    fc = serial_cfg.get("flow_control", "None")
                    idx = self._sc_flow_combo.findText(str(fc))
                    if idx >= 0:
                        self._sc_flow_combo.setCurrentIndex(idx)

                ad_cfg = serial_cfg.get("auto_detect_config", {})
                if isinstance(ad_cfg, dict) and hasattr(self, "_sc_auto_baud_monitor"):
                    m = self._sc_auto_baud_monitor
                    if "runtime_redetect_enabled" in ad_cfg:
                        m.runtime_redetect_enabled = bool(ad_cfg["runtime_redetect_enabled"])
                    for k in ("candidate_baudrates", "lock_threshold", "bad_threshold",
                              "bad_windows_to_suspect", "suspect_windows_to_scan",
                              "monitor_window_max_time_ms", "switch_cooldown_ms",
                              "switch_score_margin", "confirm_scan_rounds"):
                        if k in ad_cfg:
                            m._config[k] = ad_cfg[k]

            ui_cfg = data.get("ui", {})
            if isinstance(ui_cfg, dict):
                for key, attr in (
                    ("rx_display_hex", "_sc_rx_display_hex"),
                    ("tx_display_hex", "_sc_tx_display_hex"),
                    ("show_timestamp", "_sc_show_timestamp"),
                    ("use_ntp", "_sc_use_ntp"),
                    ("line_ending", "_sc_line_ending"),
                    ("show_send", "_sc_show_send"),
                    ("show_system_log", "_sc_show_system_log"),
                    ("line_by_line", "_sc_line_by_line"),
                    ("sidebar_visible", "_sc_sidebar_visible"),
                    ("log_auto_save", "_sc_log_auto_save"),
                    ("log_save_path", "_sc_log_save_path"),
                ):
                    if key in ui_cfg:
                        setattr(self, attr, ui_cfg[key])
                if "show_system_log" in ui_cfg and hasattr(self, "_sc_show_system_cb"):
                    self._sc_show_system_cb.blockSignals(True)
                    self._sc_show_system_cb.setChecked(bool(ui_cfg["show_system_log"]))
                    self._sc_show_system_cb.blockSignals(False)
                if getattr(self, "_sc_use_ntp", False):
                    self._sc_apply_ntp_setting(True)

                split_sizes = ui_cfg.get("center_split_sizes")
                if (
                    isinstance(split_sizes, list)
                    and len(split_sizes) == 2
                    and all(isinstance(x, (int, float)) and x > 0 for x in split_sizes)
                    and hasattr(self, "_sc_center_splitter")
                ):
                    self._sc_center_splitter.setSizes([int(x) for x in split_sizes])

            if isinstance(data.get("send_history"), list):
                self._sc_send_history = [str(x) for x in data["send_history"]]
                if hasattr(self, "_sc_history_combo"):
                    self._sc_history_combo.blockSignals(True)
                    self._sc_history_combo.clear()
                    self._sc_history_combo.addItems(self._sc_send_history)
                    self._sc_history_combo.setCurrentIndex(-1)
                    self._sc_history_combo.blockSignals(False)

            qc = data.get("quick_commands")
            if isinstance(qc, dict):
                parsed = self._sc_parse_quick_cmds_payload(qc)
                if parsed is not None:
                    self._sc_qc_data = parsed

            scripts = data.get("scripts")
            if isinstance(scripts, dict) and isinstance(scripts.get("scripts"), list):
                self._sc_script_data = scripts
                if hasattr(self, "_sc_script_combo"):
                    self._sc_script_refresh_all()

            window_cfg = data.get("window")
            if isinstance(window_cfg, dict):
                self._sc_window_geometry = window_cfg

            chart_cfg = data.get("chart")
            if isinstance(chart_cfg, dict) and chart_cfg:
                try:
                    from ui.modules.serialCom_module.serial_chart_model import ChartConfig
                    self._sc_chart_config = ChartConfig.from_dict(chart_cfg)
                except Exception:
                    logger.error("恢复 chart 配置失败", exc_info=True)
        else:
            for key, attr in (
                ("rx_display_hex", "_sc_rx_display_hex"),
                ("tx_display_hex", "_sc_tx_display_hex"),
                ("show_timestamp", "_sc_show_timestamp"),
                ("line_ending", "_sc_line_ending"),
                ("show_send", "_sc_show_send"),
                ("show_system_log", "_sc_show_system_log"),
                ("line_by_line", "_sc_line_by_line"),
                ("sidebar_visible", "_sc_sidebar_visible"),
            ):
                if key in data:
                    setattr(self, attr, data[key])
            if isinstance(data.get("send_history"), list):
                self._sc_send_history = [str(x) for x in data["send_history"]]
                if hasattr(self, "_sc_history_combo"):
                    self._sc_history_combo.blockSignals(True)
                    self._sc_history_combo.clear()
                    self._sc_history_combo.addItems(self._sc_send_history)
                    self._sc_history_combo.setCurrentIndex(-1)
                    self._sc_history_combo.blockSignals(False)

    def _sc_load_persisted_state(self) -> None:
        try:
            cfg_path = self._sc_persisted_path()
            fb_path = self._sc_fallback_path()

            source = None
            if os.path.isfile(cfg_path):
                source = cfg_path
            elif os.path.isfile(fb_path) and os.path.abspath(fb_path) != os.path.abspath(cfg_path):
                source = fb_path

            if source:
                load_err = None
                raw = None
                try:
                    with open(source, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                except Exception as e:
                    load_err = e

                if load_err is not None:
                    try:
                        QMessageBox.warning(
                            self, "配置文件损坏",
                            f"无法解析 {source}:\n{load_err}\n\n已恢复为默认配置。",
                        )
                    except Exception:
                        pass
                    self._sc_qc_data = self._sc_qc_default_data()
                    if hasattr(self, "_sc_append_system"):
                        self._sc_append_system(f"[WARN] Config corrupted, using defaults. Path: {source}", force_primary=True)
                elif not isinstance(raw, dict):
                    self._sc_qc_data = self._sc_qc_default_data()
                    if hasattr(self, "_sc_append_system"):
                        self._sc_append_system(f"[WARN] Config invalid format, using defaults. Path: {source}", force_primary=True)
                else:
                    self._sc_apply_persisted_state(raw)
                    if not hasattr(self, "_sc_qc_data") or not self._sc_qc_data:
                        self._sc_qc_data = self._sc_qc_default_data()

                    if hasattr(self, "_sc_append_system"):
                        try:
                            origin = "user" if source == cfg_path else "fallback"
                            total = sum(
                                len(g.get("commands", []))
                                for p in self._sc_qc_data.get("projects", [])
                                for g in p.get("groups", [])
                            )
                            self._sc_append_system(
                                f"[INFO] Loaded config from {origin}: {source} ({total} quick commands)",
                                force_primary=True,
                            )
                        except Exception:
                            pass
            else:
                self._sc_migrate_legacy_config()
                if not hasattr(self, "_sc_qc_data") or not self._sc_qc_data:
                    self._sc_qc_data = self._sc_qc_default_data()
                try:
                    self._sc_save_persisted_state()
                except Exception:
                    pass
                if hasattr(self, "_sc_append_system"):
                    self._sc_append_system(f"[INFO] Config path: {cfg_path}", force_primary=True)

            try:
                self._sc_qc_refresh_all()
            except Exception:
                pass
        except Exception:
            pass

    def _sc_save_persisted_state(self) -> None:
        if getattr(self, "_sc_skip_next_persist_save", False):
            self._sc_skip_next_persist_save = False
            return
        try:
            cfg_path = self._sc_persisted_path()
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(self._sc_collect_persisted_state(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _sc_apply_reset_defaults_to_widgets(self) -> None:
        if hasattr(self, "_sc_port_combo"):
            self._sc_port_combo.setCurrentIndex(-1)
        if hasattr(self, "_sc_baud_combo"):
            self._sc_baud_combo.setCurrentText("921600")
        if hasattr(self, "_sc_auto_detect_cb"):
            self._sc_auto_detect_cb.setChecked(True)
        if hasattr(self, "_sc_databit_combo"):
            self._sc_databit_combo.setCurrentText("8")
        if hasattr(self, "_sc_stopbit_combo"):
            self._sc_stopbit_combo.setCurrentText("1")
        if hasattr(self, "_sc_parity_combo"):
            self._sc_parity_combo.setCurrentText("None")
        if hasattr(self, "_sc_flow_combo"):
            self._sc_flow_combo.setCurrentText("None")

        self._sc_rx_display_hex = False
        if hasattr(self, "_sc_rx_toggle"):
            self._sc_rx_toggle.set_value("ASCII")
        self._sc_tx_display_hex = False
        if hasattr(self, "_sc_tx_toggle"):
            self._sc_tx_toggle.set_value("ASCII")

        self._sc_show_timestamp = True
        if hasattr(self, "_sc_rx_show_time_cb"):
            self._sc_rx_show_time_cb.setChecked(True)
        self._sc_apply_ntp_setting(False)
        self._sc_line_ending = "\r\n"
        if hasattr(self, "_sc_ending_combo"):
            self._sc_ending_combo.setCurrentIndex(0)
        self._sc_show_send = True
        if hasattr(self, "_sc_show_send_cb"):
            self._sc_show_send_cb.setChecked(True)
        self._sc_show_system_log = False
        if hasattr(self, "_sc_show_system_cb"):
            self._sc_show_system_cb.setChecked(False)
        self._sc_line_by_line = False
        if hasattr(self, "_sc_line_by_line_cb"):
            self._sc_line_by_line_cb.setChecked(False)

        self._sc_send_history = []
        if hasattr(self, "_sc_history_combo"):
            self._sc_history_combo.blockSignals(True)
            self._sc_history_combo.clear()
            self._sc_history_combo.setCurrentIndex(-1)
            self._sc_history_combo.blockSignals(False)

        self._sc_sidebar_visible = True
        if hasattr(self, "_sc_sidebar_widget"):
            self._sc_sidebar_widget.setVisible(True)
        if hasattr(self, "_sc_sidebar_toggle_btn"):
            self._sc_sidebar_toggle_btn.setChecked(True)

        if hasattr(self, "_sc_center_splitter"):
            self._sc_center_splitter.setSizes(
                list(getattr(self, "_sc_center_splitter_default_sizes", [680, 185]))
            )

        if hasattr(self, "_sc_auto_baud_monitor"):
            self._sc_auto_baud_monitor.update_config(dict(AUTO_BAUD_CONFIG))
            self._sc_auto_baud_monitor.runtime_redetect_enabled = True

    def _sc_reset_user_config_keep_quick_commands(self, dialog_parent=None) -> bool:
        cfg_path = self._sc_persisted_path()
        ret = QMessageBox.question(
            dialog_parent or self,
            "Reset user config",
            "This will reset the user JSON to default settings, while keeping Quick Commands unchanged.\n\n"
            f"Before continuing, please back up this JSON file if needed:\n{cfg_path}\n\n"
            "Continue reset?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return False

        quick_commands = getattr(self, "_sc_qc_data", self._sc_qc_default_data())
        scripts = getattr(self, "_sc_script_data", self._sc_script_default_data())
        reset_state = self._sc_default_persisted_state(
            quick_commands=quick_commands, scripts=scripts
        )
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(reset_state, f, ensure_ascii=False, indent=2)
            self._sc_window_geometry = None
            self._sc_apply_persisted_state(reset_state)
            self._sc_apply_reset_defaults_to_widgets()
            self._sc_skip_next_persist_save = True
            if hasattr(self, "_sc_append_system"):
                self._sc_append_system(f"[INFO] User config reset to defaults. Quick Commands kept. Path: {cfg_path}", force_primary=True)
            QMessageBox.information(
                dialog_parent or self,
                "Reset complete",
                "User JSON has been reset to default settings.\nQuick Commands were kept unchanged.",
            )
            if self.isWindow():
                QTimer.singleShot(0, self.close)
            return True
        except Exception as e:
            logger.error("Reset Serial Console config failed: %s", e, exc_info=True)
            QMessageBox.critical(dialog_parent or self, "Reset failed", f"Failed to reset config:\n{e}")
            return False

    def _sc_qc_save_data(self) -> None:
        self._sc_save_persisted_state()

    # --- log helpers ---

    _SC_MAX_LOG_LINES_DEFAULT = 10000
    _SC_MAX_LOG_LINES_LIMIT = 500000

class _MiniSlideToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, left="ASCII", right="HEX", parent=None):
        super().__init__(parent)
        self._left = left
        self._right = right
        self._value = left
        self._anim_progress = 0.0

        self.setFixedSize(SerialComMixin._TOGGLE_W, 24)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def value(self):
        return self._value

    def set_value(self, val):
        if val not in (self._left, self._right):
            return
        if val == self._value:
            return
        self._value = val
        target = 1.0 if val == self._right else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = self._right if self._value == self._left else self._left
            self._value = new_val
            target = 1.0 if new_val == self._right else 0.0
            self._anim.stop()
            self._anim.setStartValue(self._anim_progress)
            self._anim.setEndValue(target)
            self._anim.start()
            self.toggled.emit(self._value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        outer_r = 6

        colors = toggle_colors()
        p.setPen(QPen(QColor(colors["border"]), 1))
        p.setBrush(QColor(colors["background"]))
        p.drawRoundedRect(QRectF(0, 0, w, h), outer_r, outer_r)

        knob_margin = 2
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_r = 3

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(colors["knob"]))
        p.drawRoundedRect(QRectF(knob_x, knob_margin, knob_w, knob_h),
                          knob_r, knob_r)

        font = p.font()
        font.setPixelSize(10)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        left_rect = QRectF(0, 0, w / 2, h)
        right_rect = QRectF(w / 2, 0, w / 2, h)

        p.setPen(QColor(colors["active_text"]) if self._anim_progress < 0.5 else QColor(colors["inactive_text"]))
        p.drawText(left_rect, Qt.AlignCenter, self._left)

        p.setPen(QColor(colors["active_text"]) if self._anim_progress >= 0.5 else QColor(colors["inactive_text"]))
        p.drawText(right_rect, Qt.AlignCenter, self._right)

        p.end()


class _AddLogPanelDialog(_FramelessChromeDialog):

    def __init__(self, panel_index: int = 2, parent=None):
        super().__init__(parent, title="ADD LOG PANEL", icon_name="plus.svg")
        self._panel_index = panel_index
        self._apply_content_style(_DLG_STYLE)

        root = self._content
        root.setSpacing(12)

        title = QLabel("New Serial LOG")
        title.setObjectName("dlgSectionTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Panel Name"), 0, 0)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. LOG-2")
        self._title_edit.setText(f"Serial Log {self._panel_index}")
        self._title_edit.setStyleSheet(dialog_line_edit_style())
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = SerialDarkComboBox()
        self._port_combo.setFixedHeight(26)
        self._port_combo.setEditable(True)
        try:
            ports = serial.tools.list_ports.comports()
            for p in ports:
                self._port_combo.addItem(f"{p.device} - {p.description}")
        except Exception:
            pass
        if self._port_combo.count() == 0:
            if DEBUG_MOCK:
                self._port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            else:
                self._port_combo.addItem("No serial ports found")
        grid.addWidget(self._port_combo, 1, 1)

        grid.addWidget(QLabel("Baudrate"), 2, 0)
        self._baud_combo = SerialDarkComboBox()
        self._baud_combo.setFixedHeight(26)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000"]:
            self._baud_combo.addItem(br)
        self._baud_combo.setCurrentIndex(0)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = SerialDarkComboBox()
        self._databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = SerialDarkComboBox()
        self._stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = SerialDarkComboBox()
        self._parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow Control"), 6, 0)
        self._flow_combo = SerialDarkComboBox()
        self._flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)

        mode_grp = QHBoxLayout()
        mode_grp.setSpacing(16)
        mode_label = QLabel("Open in:")
        mode_grp.addWidget(mode_label)
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self._mode_same_window = QRadioButton("Same Window")
        self._mode_same_window.setChecked(True)
        self._mode_independent = QRadioButton("Independent Window")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_same_window, 0)
        self._mode_group.addButton(self._mode_independent, 1)
        mode_grp.addWidget(self._mode_same_window)
        mode_grp.addWidget(self._mode_independent)
        mode_grp.addStretch()
        root.addLayout(mode_grp)

        self._auto_connect_cb = QCheckBox("Auto connect after creation")
        self._auto_connect_cb.setChecked(True)
        root.addWidget(self._auto_connect_cb)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(508)

    def get_config(self):
        port_text = self._port_combo.currentText()
        port = port_text.split()[0] if port_text and not port_text.startswith("No ") else ""
        try:
            baudrate = int(self._baud_combo.currentText().strip())
        except ValueError:
            baudrate = 115200
        return {
            "title": self._title_edit.text().strip() or "Serial Log",
            "port": port,
            "baudrate": baudrate,
            "databit": int(self._databit_combo.currentText()),
            "stopbit": self._stopbit_combo.currentText(),
            "parity": self._parity_combo.currentText(),
            "flow": self._flow_combo.currentText(),
            "auto_connect": self._auto_connect_cb.isChecked(),
            "independent_window": self._mode_independent.isChecked(),
        }


class _PanelSettingsDialog(_FramelessChromeDialog):

    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent, title="PANEL SETTINGS", icon_name="settings.svg")
        self._apply_content_style(_DLG_STYLE)

        root = self._content
        root.setSpacing(12)

        title = QLabel("Serial Port Settings")
        title.setObjectName("dlgSectionTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Panel Name"), 0, 0)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. LOG-2")
        self._title_edit.setText(current_config.get("title", "Serial Log"))
        self._title_edit.setStyleSheet(dialog_line_edit_style())
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = SerialDarkComboBox()
        self._port_combo.setFixedHeight(26)
        self._port_combo.setEditable(True)
        try:
            ports = serial.tools.list_ports.comports()
            for p in ports:
                self._port_combo.addItem(f"{p.device} - {p.description}")
        except Exception:
            pass
        if self._port_combo.count() == 0:
            if DEBUG_MOCK:
                self._port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            else:
                self._port_combo.addItem("No serial ports found")
        cur_port = current_config.get("port", "")
        if cur_port:
            for i in range(self._port_combo.count()):
                if self._port_combo.itemText(i).startswith(cur_port):
                    self._port_combo.setCurrentIndex(i)
                    break
            else:
                self._port_combo.setEditText(cur_port)
        grid.addWidget(self._port_combo, 1, 1)

        grid.addWidget(QLabel("Baudrate"), 2, 0)
        self._baud_combo = SerialDarkComboBox()
        self._baud_combo.setFixedHeight(26)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "115200", "9600"]:
            self._baud_combo.addItem(br)
        cur_baud = str(current_config.get("baudrate", 921600))
        idx = self._baud_combo.findText(cur_baud)
        if idx >= 0:
            self._baud_combo.setCurrentIndex(idx)
        else:
            self._baud_combo.setEditText(cur_baud)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = SerialDarkComboBox()
        self._databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        cur_databit = str(current_config.get("databit", 8))
        idx = self._databit_combo.findText(cur_databit)
        if idx >= 0:
            self._databit_combo.setCurrentIndex(idx)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = SerialDarkComboBox()
        self._stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        cur_stopbit = str(current_config.get("stopbit", "1"))
        idx = self._stopbit_combo.findText(cur_stopbit)
        if idx >= 0:
            self._stopbit_combo.setCurrentIndex(idx)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = SerialDarkComboBox()
        self._parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        cur_parity = current_config.get("parity", "None")
        idx = self._parity_combo.findText(cur_parity)
        if idx >= 0:
            self._parity_combo.setCurrentIndex(idx)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow Control"), 6, 0)
        self._flow_combo = SerialDarkComboBox()
        self._flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        cur_flow = current_config.get("flow", "None")
        idx = self._flow_combo.findText(cur_flow)
        if idx >= 0:
            self._flow_combo.setCurrentIndex(idx)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)

        self._auto_connect_cb = QCheckBox("Auto connect after apply")
        self._auto_connect_cb.setChecked(True)
        root.addWidget(self._auto_connect_cb)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Apply")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(508)

    def get_config(self):
        port_text = self._port_combo.currentText()
        port = port_text.split()[0] if port_text and not port_text.startswith("No ") else ""
        try:
            baudrate = int(self._baud_combo.currentText().strip())
        except ValueError:
            baudrate = 115200
        return {
            "title": self._title_edit.text().strip() or "Serial Log",
            "port": port,
            "baudrate": baudrate,
            "databit": int(self._databit_combo.currentText()),
            "stopbit": self._stopbit_combo.currentText(),
            "parity": self._parity_combo.currentText(),
            "flow": self._flow_combo.currentText(),
            "auto_connect": self._auto_connect_cb.isChecked(),
        }


class _IndependentSerialWindow(QWidget):

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._conn = None
        self._read_thread = None
        self._read_worker = None
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._auto_scroll = True

        title = config.get("title", "Serial Log")
        self.setWindowTitle(f"Serial Console - {title}")
        self.setMinimumSize(600, 400)
        self.resize(750, 500)
        self.setStyleSheet(f"background-color: {_CLR_BG_LOG}; color: {_CLR_INPUT_TEXT};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        port_text = config.get("port", "N/A")
        baud_text = str(config.get("baudrate", "N/A"))
        self._status_label = QLabel(f"{port_text} @ {baud_text}")
        self._status_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 12px;")
        toolbar.addWidget(self._status_label)

        toolbar.addStretch()

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setCursor(Qt.PointingHandCursor)
        self._connect_btn.clicked.connect(self._toggle_connect)
        toolbar.addWidget(self._connect_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_log)
        toolbar.addWidget(clear_btn)

        root.addLayout(toolbar)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setStyleSheet(log_edit_style(padding="6px 8px") + SERIAL_SCROLLBAR_STYLE)
        self._log_edit.document().setDefaultStyleSheet(log_document_style())
        self._log_edit.document().setMaximumBlockCount(5000)
        root.addWidget(self._log_edit, 1)

        send_row = QHBoxLayout()
        send_row.setSpacing(4)
        self._send_input = QLineEdit()
        self._send_input.setPlaceholderText("Enter command...")
        self._send_input.setStyleSheet(filter_input_style())
        self._send_input.returnPressed.connect(self._on_send)
        send_row.addWidget(self._send_input, 1)
        send_btn = QPushButton("Send")
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.clicked.connect(self._on_send)
        send_row.addWidget(send_btn)
        root.addLayout(send_row)

        status_bar = QHBoxLayout()
        self._rx_label = QLabel("RX: 0 B")
        self._rx_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 11px;")
        self._tx_label = QLabel("TX: 0 B")
        self._tx_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 11px;")
        status_bar.addWidget(self._rx_label)
        status_bar.addWidget(self._tx_label)
        status_bar.addStretch()
        root.addLayout(status_bar)

        if config.get("auto_connect", False):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, self._do_connect)

    def _toggle_connect(self):
        if DEBUG_MOCK and self._connect_btn.text() == "Disconnect":
            self._do_disconnect()
        elif self._conn is not None and self._conn.is_open:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        port = self._config.get("port", "")
        baudrate = self._config.get("baudrate", 115200)
        if not port:
            self._append("[ERROR] No port configured")
            return

        if DEBUG_MOCK:
            self._conn = None
            self._connect_btn.setText("Disconnect")
            self._status_label.setText(f"MOCK @ {baudrate}")
            self._status_label.setStyleSheet(f"color: {_CLR_CONNECT_FG}; font-size: 12px;")
            self._append(f"[INFO] Mock connected: {port} @ {baudrate}")
            return

        try:
            databit = self._config.get("databit", 8)
            stopbit_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
            stopbits = stopbit_map.get(str(self._config.get("stopbit", "1")), serial.STOPBITS_ONE)
            parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
            parity = parity_map.get(self._config.get("parity", "None"), serial.PARITY_NONE)
            flow = self._config.get("flow", "None")
            conn = serial.Serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=stopbits, parity=parity,
                xonxoff=(flow == "XON/XOFF"), rtscts=(flow == "RTS/CTS"),
                timeout=0.1,
            )
            self._conn = conn
            self._connect_btn.setText("Disconnect")
            self._status_label.setText(f"{port} @ {baudrate}")
            self._status_label.setStyleSheet(f"color: {_CLR_CONNECT_FG}; font-size: 12px;")
            self._append(f"[INFO] Connected: {port} @ {baudrate}")
            self._start_read()
        except Exception as e:
            self._append(f"[ERROR] Connection failed: {e}")

    def _do_disconnect(self):
        self._stop_read()
        try:
            if self._conn is not None and self._conn.is_open:
                self._conn.close()
        except Exception:
            pass
        self._conn = None
        self._connect_btn.setText("Connect")
        self._status_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 12px;")
        self._append("[INFO] Disconnected")

    def _on_send(self):
        text = self._send_input.text()
        if not text:
            return
        data = (text + "\r\n").encode("utf-8")

        if DEBUG_MOCK:
            self._tx_bytes += len(data)
            self._tx_label.setText(f"TX: {self._tx_bytes} B")
            self._append(f"[TX] {text}")
            self._send_input.clear()
            return

        if self._conn is None or not self._conn.is_open:
            self._append("[ERROR] Not connected")
            return
        try:
            self._conn.write(data)
            self._tx_bytes += len(data)
            self._tx_label.setText(f"TX: {self._tx_bytes} B")
            self._append(f"[TX] {text}")
            self._send_input.clear()
        except Exception as e:
            self._append(f"[ERROR] Send failed: {e}")

    def _clear_log(self):
        self._log_edit.clear()
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._rx_label.setText("RX: 0 B")
        self._tx_label.setText("TX: 0 B")

    def _append(self, message):
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%H:%M:%S.%f")[:-3]
        color = _CLR_TEXT_BODY
        if "[ERROR]" in message:
            color = _CLR_ERROR
        elif "[INFO]" in message:
            color = _CLR_TEXT_INFO
        elif "[TX]" in message:
            color = _CLR_TX
        elif "[RX]" in message:
            color = _CLR_RX
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> <span style="color:{color};">{escaped}</span>'
        self._log_edit.append(html)
        if self._auto_scroll:
            sb = self._log_edit.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def _start_read(self):
        if self._conn is None:
            return
        worker = _SerialReadWorker(self._conn)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.data_received.connect(self._on_data_received)
        self._read_thread = thread
        self._read_worker = worker
        thread.start()

    def _stop_read(self):
        if self._read_worker:
            self._read_worker.stop()
        if self._read_thread and self._read_thread.isRunning():
            self._read_thread.quit()
            self._read_thread.wait(3000)
        self._read_thread = None
        self._read_worker = None

    def _on_data_received(self, data: bytes):
        self._rx_bytes += len(data)
        self._rx_label.setText(f"RX: {self._rx_bytes} B")
        try:
            text = data.decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line.strip():
                    self._append(f"[RX] {line}")
        except Exception:
            self._append(f"[RX] {data.hex(' ')}")

    def closeEvent(self, event):
        self._sc_stop_ntp_sync()
        self._do_disconnect()
        super().closeEvent(event)


class _QuickCmdPreviewPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setObjectName("quickCmdPreviewPopupWindow")
        self._card = QFrame(self)
        self._card.setObjectName("quickCmdPreviewPopup")
        self._badge_label = QLabel("QUICK CMD")
        self._badge_label.setObjectName("quickCmdPreviewBadge")
        self._title_label = QLabel()
        self._title_label.setObjectName("quickCmdPreviewTitle")
        self._title_label.setTextFormat(Qt.PlainText)
        self._content_label = QLabel()
        self._content_label.setObjectName("quickCmdPreviewContent")
        self._content_label.setWordWrap(True)
        self._content_label.setTextFormat(Qt.PlainText)
        self._content_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self._meta_label = QLabel()
        self._meta_label.setObjectName("quickCmdPreviewMeta")
        self._meta_label.setWordWrap(True)
        self._meta_label.setTextFormat(Qt.PlainText)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(7)
        header_layout.addWidget(self._badge_label, 0, Qt.AlignVCenter)
        header_layout.addWidget(self._title_label, 1, Qt.AlignVCenter)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(6)
        card_layout.addLayout(header_layout)
        card_layout.addWidget(self._content_label)
        card_layout.addWidget(self._meta_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(0)
        layout.addWidget(self._card)
        shadow_style = quick_preview_popup_shadow()
        shadow = QGraphicsDropShadowEffect(self._card)
        shadow.setBlurRadius(shadow_style["blur_radius"])
        shadow.setOffset(shadow_style["offset_x"], shadow_style["offset_y"])
        shadow.setColor(QColor(*shadow_style["color"]))
        self._card.setGraphicsEffect(shadow)
        self.setStyleSheet(quick_preview_popup_style())

    def set_preview_data(self, name: str, content: str, send_type: str, encoding: str, line_ending: str):
        display_name = str(name or "Untitled")
        display_content = str(content or "")
        display_type = str(send_type or "text")
        display_encoding = str(encoding or "ascii")
        display_line_ending = repr(line_ending or "")
        if len(display_content) > 360:
            display_content = f"{display_content[:360]}..."
        self._title_label.setText(display_name)
        self._content_label.setText(display_content if display_content else " ")
        self._meta_label.setText(
            f"Type: {display_type}   Encoding: {display_encoding}   Line: {display_line_ending}"
        )
        self.setFixedWidth(368)
        self.adjustSize()


class _QuickCmdButton(QPushButton):
    """支持右键菜单 + 拖拽排序的快捷指令按钮。

    - 左键短按 → 触发 ``clicked``（发送指令，逻辑在宿主信号槽里）；
    - 左键拖动超过阈值 → 启动 ``QDrag``，mime 携带源索引；
    - 右键 → 通过 ``Qt.CustomContextMenu`` 上抛给宿主弹出 Edit / Delete 菜单。

    数据流：源索引由宿主在创建按钮时通过 ``set_command_index`` 注入。
    """

    _MIME_TYPE = "application/x-kklab-quickcmd"

    move_requested = Signal(int, int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(False)  # 容器统一接收 drop，按钮自身不参与
        self._press_pos = None
        self._cmd_index = -1
        self._dragging = False
        self._preview_data = None
        self._preview_popup = _QuickCmdPreviewPopup()
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(80)
        self._preview_timer.timeout.connect(self._show_preview)
        self._build_action_overlay()
        self._hide_actions_timer = QTimer(self)
        self._hide_actions_timer.setSingleShot(True)
        self._hide_actions_timer.setInterval(60)
        self._hide_actions_timer.timeout.connect(self._maybe_hide_actions)

    def _build_action_overlay(self):
        # 悬浮操作条：用独立的无边框顶层窗口承载，溢出在按钮顶部（参考 -top-2.5）。
        # 不能作为按钮或网格容器的子控件——前者会被裁剪、后者会被 QScrollArea
        # 视口边界裁掉，因此顶层窗口才能真正浮在按钮上边缘之上。
        # 顶层窗口本身保持透明，真正带"整体外边框"的胶囊是其内部子控件，
        # 这样 QSS 的 border/background 才能在半透明顶层窗口上稳定渲染。
        self._action_bar = QFrame(None)
        self._action_bar.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self._action_bar.setAttribute(Qt.WA_TranslucentBackground, True)
        self._action_bar.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._action_bar.setStyleSheet("QFrame { background: transparent; border: none; }")
        self._action_bar.setCursor(Qt.ArrowCursor)
        self._action_bar.setAttribute(Qt.WA_Hover, True)
        self._action_bar.installEventFilter(self)
        outer_lay = QHBoxLayout(self._action_bar)
        outer_lay.setContentsMargins(2, 2, 2, 2)
        outer_lay.setSpacing(0)
        self._action_pill = QFrame(self._action_bar)
        self._action_pill.setObjectName("quickCmdActionBar")
        self._action_pill.setStyleSheet(quick_action_overlay_container_style())
        outer_lay.addWidget(self._action_pill)
        bar_lay = QHBoxLayout(self._action_pill)
        bar_lay.setContentsMargins(5, 4, 5, 4)
        bar_lay.setSpacing(2)
        self._action_left = self._make_action_btn(
            os.path.join(_SVG_SERIAL_DIR, "chevron-left.svg"), _CLR_TEXT_MUTED, "Move Left"
        )
        self._action_right = self._make_action_btn(
            os.path.join(_SVG_SERIAL_DIR, "chevron-right.svg"), _CLR_TEXT_MUTED, "Move Right"
        )
        self._action_edit = self._make_action_btn(
            os.path.join(_SVG_SERIAL_DIR, "edit.svg"), _CLR_SEND_BG, "Edit macro"
        )
        self._action_delete = self._make_action_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), _CLR_ERROR, "Delete macro"
        )
        self._action_btns = [
            self._action_left,
            self._action_right,
            self._action_edit,
            self._action_delete,
        ]
        for b in self._action_btns:
            bar_lay.addWidget(b)
        self._action_bar.hide()
        self._action_left.clicked.connect(
            lambda: self.move_requested.emit(self._cmd_index, -1)
        )
        self._action_right.clicked.connect(
            lambda: self.move_requested.emit(self._cmd_index, 1)
        )
        self._action_edit.clicked.connect(
            lambda: self.edit_requested.emit(self._cmd_index)
        )
        self._action_delete.clicked.connect(
            lambda: self.delete_requested.emit(self._cmd_index)
        )

    def _make_action_btn(self, svg_path, color, tip):
        btn = QToolButton(self._action_pill)
        btn.setObjectName("quickCmdAction")
        btn.setStyleSheet(quick_action_overlay_style())
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFixedSize(18, 18)
        btn.setIconSize(QSize(12, 12))
        btn.setToolTip(tip)
        icon = _tinted_svg_icon(svg_path, color, 12)
        if not icon.isNull():
            btn.setIcon(icon)
        return btn

    def set_move_bounds(self, can_left: bool, can_right: bool):
        self._action_left.setEnabled(can_left)
        self._action_right.setEnabled(can_right)

    def _position_action_bar(self):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        bar.adjustSize()
        bar_w = bar.sizeHint().width()
        bar_h = bar.sizeHint().height()
        # 顶层窗口用全局坐标定位：右侧与按钮右边缘对齐，整体向上溢出按钮顶部
        # （参考 -top-2.5：操作条底部压在按钮上边缘上方约一半处）。
        top_right = self.mapToGlobal(QPoint(self.width(), 0))
        x = top_right.x() - bar_w - 4
        y = top_right.y() - bar_h + bar_h // 2
        bar.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_action_bar", None) is not None and self._action_bar.isVisible():
            self._position_action_bar()

    def _set_actions_visible(self, visible: bool):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        if visible:
            self._hide_actions_timer.stop()
            self._position_action_bar()
            bar.raise_()
            bar.show()
        else:
            bar.hide()

    def _cleanup_action_bar(self):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        bar.hide()
        bar.removeEventFilter(self)
        bar.setParent(None)
        bar.deleteLater()
        self._action_bar = None

    def _maybe_hide_actions(self):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        if self.underMouse() or bar.underMouse():
            return
        bar.hide()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent  # 局部引入，避免顶部冗余导入
        if obj is getattr(self, "_action_bar", None):
            if event.type() == QEvent.Enter:
                self._hide_actions_timer.stop()
            elif event.type() == QEvent.Leave:
                self._hide_actions_timer.start()
        return super().eventFilter(obj, event)

    def set_command_index(self, idx: int):
        self._cmd_index = idx

    def command_index(self) -> int:
        return self._cmd_index

    def set_preview_data(self, name: str, content: str, send_type: str, encoding: str, line_ending: str):
        self._preview_data = {
            "name": name,
            "content": content,
            "send_type": send_type,
            "encoding": encoding,
            "line_ending": line_ending,
        }

    def enterEvent(self, event):
        super().enterEvent(event)
        self._set_actions_visible(True)
        self._preview_timer.start()

    def leaveEvent(self, event):
        self._preview_timer.stop()
        self._preview_popup.hide()
        self._hide_actions_timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._preview_popup.hide()
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and not self._dragging
            and self._cmd_index >= 0
        ):
            if (
                event.position().toPoint() - self._press_pos
            ).manhattanLength() >= QApplication.startDragDistance():
                self._preview_timer.stop()
                self._preview_popup.hide()
                self._dragging = True
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def _show_preview(self):
        if not self._preview_data or self._dragging or not self.underMouse():
            return
        self._preview_popup.set_preview_data(**self._preview_data)
        self._preview_popup.ensurePolished()
        pos = self._bounded_preview_pos()
        self._preview_popup.move(pos)
        self._preview_popup.show()

    def _bounded_preview_pos(self) -> QPoint:
        pos = self.mapToGlobal(QPoint(0, self.height() + 8))
        popup_size = self._preview_popup.sizeHint()
        screen = QApplication.screenAt(pos) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return pos
        available = screen.availableGeometry()
        safe_margin = 24
        x = min(
            max(pos.x(), available.left() + safe_margin),
            available.right() - popup_size.width() - safe_margin,
        )
        y = pos.y()
        if y + popup_size.height() + safe_margin > available.bottom():
            y = self.mapToGlobal(QPoint(0, -popup_size.height() - 8)).y()
        y = min(
            max(y, available.top() + safe_margin),
            available.bottom() - popup_size.height() - safe_margin,
        )
        return QPoint(x, y)

    def mouseReleaseEvent(self, event):
        # 拖拽中按下释放不触发 click（Qt 会自动把 release 派发给 drop 目标）
        was_dragging = self._dragging
        self._press_pos = None
        self._dragging = False
        if was_dragging:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        from PySide6.QtGui import QDrag  # 局部引入
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME_TYPE, str(self._cmd_index).encode())
        drag.setMimeData(mime)
        pixmap = self.grab()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.MoveAction)


class _ProjectTabBar(QTabBar):
    """支持右键菜单 + 项目 Tab 拖拽排序的 QTabBar 子类。

    - 拖拽：按下左键 + 移动超过阈值则启动；放下时计算源 / 目标 index 并通过
      ``project_reorder_requested(source, target)`` 发射给宿主，由宿主修改
      数据模型后重建 Tab。
    - 拖拽时排除末尾的 "+" 加号 tab（最后一项）。
    - 右键菜单：通过 ``Qt.CustomContextMenu`` 上抛给宿主统一处理。
    """

    project_reorder_requested = Signal(int, int)
    _MIME_TYPE = "application/x-kklab-project-tab"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMovable(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self._press_pos = None
        self._press_index = -1

    def _is_real_tab(self, index: int) -> bool:
        # 约定：最后一个 tab 为 "+" 加号，不参与拖拽
        return 0 <= index < self.count() - 1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self.tabAt(event.position().toPoint())
            if self._is_real_tab(idx):
                self._press_pos = event.position().toPoint()
                self._press_index = idx
            else:
                self._press_pos = None
                self._press_index = -1
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and self._press_index >= 0
        ):
            if (
                event.position().toPoint() - self._press_pos
            ).manhattanLength() >= QApplication.startDragDistance():
                self._start_drag(self._press_index)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self._press_index = -1
        super().mouseReleaseEvent(event)

    def _start_drag(self, source_index: int):
        from PySide6.QtGui import QDrag  # 局部引入，避免顶部模块持有未用符号
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME_TYPE, str(source_index).encode())
        drag.setMimeData(mime)
        rect = self.tabRect(source_index)
        if not rect.isEmpty():
            pixmap = self.grab(rect)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(rect.width() // 2, rect.height() // 2))
        drag.exec(Qt.MoveAction)
        self._press_pos = None
        self._press_index = -1

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self._MIME_TYPE):
            return
        try:
            source_index = int(
                bytes(event.mimeData().data(self._MIME_TYPE)).decode()
            )
        except (ValueError, UnicodeDecodeError):
            return
        target_index = self.tabAt(event.position().toPoint())
        # 拖到 "+" tab 或外部 → 视为挪到末尾真实项目
        last_real = self.count() - 2
        if not self._is_real_tab(target_index):
            target_index = last_real if last_real >= 0 else 0
        if source_index == target_index:
            return
        event.acceptProposedAction()
        self.project_reorder_requested.emit(source_index, target_index)


class _QuickCommandPickerPopup(QFrame):
    _ENTRY_ROLE = Qt.UserRole + 1
    _KEY_ROLE = Qt.UserRole + 2

    def __init__(self, parent=None, quick_commands=None, on_pick=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("pkPopup")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet(self._picker_style())
        self._entries = list(quick_commands or [])
        self._on_pick = on_pick
        self.setFixedWidth(540)

        self._tree_data = {}
        self._order = []
        for entry in self._entries:
            project = entry.get("project") or "未分组项目"
            group = entry.get("group") or "默认分组"
            if project not in self._tree_data:
                self._tree_data[project] = {}
                self._order.append(project)
            self._tree_data[project].setdefault(group, []).append(entry)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._search = QLineEdit()
        self._search.setObjectName("pkSearch")
        self._search.setPlaceholderText("搜索指令 / 分组 / 项目…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        self._search.returnPressed.connect(self._activate_current)
        root.addWidget(self._search)

        cols = QHBoxLayout()
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(6)

        self._proj_list = self._make_column("pkColProject")
        self._group_list = self._make_column("pkColGroup")
        self._cmd_list = self._make_column("pkColCmd")
        cols.addWidget(self._proj_list, 1)
        cols.addWidget(self._group_list, 1)
        cols.addWidget(self._cmd_list, 1)
        root.addLayout(cols, 1)

        self._search_list = QListWidget()
        self._search_list.setObjectName("pkSearchList")
        self._search_list.setMouseTracking(True)
        self._search_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._search_list.setMaximumHeight(320)
        self._search_list.setMinimumHeight(220)
        self._search_list.itemClicked.connect(self._on_search_clicked)
        self._search_list.hide()
        root.addWidget(self._search_list, 1)

        self._proj_list.itemEntered.connect(self._on_project_changed)
        self._proj_list.currentItemChanged.connect(
            lambda cur, _prev: self._on_project_changed(cur)
        )
        self._group_list.itemEntered.connect(self._on_group_changed)
        self._group_list.currentItemChanged.connect(
            lambda cur, _prev: self._on_group_changed(cur)
        )
        self._cmd_list.itemClicked.connect(self._on_cmd_clicked)

        self._build_projects()

    def _make_column(self, name):
        lst = QListWidget()
        lst.setObjectName(name)
        lst.setMouseTracking(True)
        lst.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lst.setMaximumHeight(320)
        lst.setMinimumHeight(220)
        return lst

    def popup_at(self, anchor):
        self.adjustSize()
        screen = self.screen() or QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        if anchor is not None:
            below = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
            pos = below
            if avail is not None:
                if pos.x() + self.width() > avail.right():
                    pos.setX(avail.right() - self.width())
                if pos.x() < avail.left():
                    pos.setX(avail.left())
                if pos.y() + self.height() > avail.bottom():
                    above = anchor.mapToGlobal(QPoint(0, -self.height() - 4))
                    pos = above
            self.move(pos)
        else:
            self.move(QCursor.pos())
        self.show()
        self._search.setFocus()

    def _picker_style(self) -> str:
        return f"""
            QFrame#pkPopup {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_BORDER_HOVER};
                border-radius: 12px;
            }}
            QLineEdit#pkSearch {{
                background-color: {_CLR_INPUT_BG};
                border: 1px solid {_CLR_BORDER};
                border-radius: 8px;
                color: {_CLR_TEXT_BTN_LOG};
                font-size: 12px; font-family: {_UI_FONT};
                padding: 6px 9px;
                min-height: 22px;
            }}
            QLineEdit#pkSearch:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
            QListWidget#pkColProject, QListWidget#pkColGroup,
            QListWidget#pkColCmd, QListWidget#pkSearchList {{
                background-color: {_CLR_INPUT_BG};
                border: 1px solid {_CLR_BORDER};
                border-radius: 10px;
                color: {_CLR_TEXT_BTN_LOG};
                font-size: 12px; font-family: {_UI_FONT};
                outline: none;
                padding: 4px;
            }}
            QListWidget#pkColProject::item, QListWidget#pkColGroup::item,
            QListWidget#pkColCmd::item, QListWidget#pkSearchList::item {{
                min-height: 25px;
                padding: 3px 6px;
                border-radius: 6px;
            }}
            QListWidget#pkColProject::item:hover, QListWidget#pkColGroup::item:hover,
            QListWidget#pkColCmd::item:hover, QListWidget#pkSearchList::item:hover {{
                background-color: {_CLR_BORDER};
            }}
            QListWidget#pkColProject::item:selected, QListWidget#pkColGroup::item:selected,
            QListWidget#pkColCmd::item:selected, QListWidget#pkSearchList::item:selected {{
                background-color: {_CLR_SELECTION_BG};
                color: {_CLR_TEXT_TITLE};
            }}
        """

    def _build_projects(self):
        title_font = QFont(self._proj_list.font())
        title_font.setBold(True)
        self._proj_list.clear()
        for project in self._order:
            item = QListWidgetItem(f"{project}  ›")
            item.setData(self._KEY_ROLE, project)
            item.setFont(title_font)
            item.setForeground(QColor(_CLR_TEXT_TITLE))
            self._proj_list.addItem(item)
        self._group_list.clear()
        self._cmd_list.clear()
        if self._proj_list.count() == 1:
            self._on_project_changed(self._proj_list.item(0))

    def _on_project_changed(self, item):
        self._group_list.clear()
        self._cmd_list.clear()
        if item is None:
            return
        project = item.data(self._KEY_ROLE)
        if project is None:
            return
        groups = self._tree_data.get(project, {})
        for group in groups:
            g_item = QListWidgetItem(f"{group}  ›")
            g_item.setData(self._KEY_ROLE, (project, group))
            g_item.setForeground(QColor(_CLR_TEXT_MUTED))
            self._group_list.addItem(g_item)
        if self._group_list.count() == 1:
            self._on_group_changed(self._group_list.item(0))

    def _on_group_changed(self, item):
        self._cmd_list.clear()
        if item is None:
            return
        key = item.data(self._KEY_ROLE)
        if not key:
            return
        project, group = key
        for entry in self._tree_data.get(project, {}).get(group, []):
            label = entry.get("name", "") or entry.get("content", "")
            c_item = QListWidgetItem(label)
            c_item.setData(self._ENTRY_ROLE, entry)
            c_item.setToolTip(entry.get("content", ""))
            self._cmd_list.addItem(c_item)

    def _on_cmd_clicked(self, item):
        if item is None:
            return
        entry = item.data(self._ENTRY_ROLE)
        if not entry:
            return
        if callable(self._on_pick):
            self._on_pick(entry)
        self.close()

    def _apply_filter(self, text):
        needle = (text or "").strip().lower()
        if not needle:
            self._search_list.hide()
            self._proj_list.show()
            self._group_list.show()
            self._cmd_list.show()
            return
        self._proj_list.hide()
        self._group_list.hide()
        self._cmd_list.hide()
        self._search_list.show()
        self._search_list.clear()
        for entry in self._entries:
            haystack = " ".join(str(entry.get(k, "")) for k in
                                 ("name", "content", "group", "project")).lower()
            if needle not in haystack:
                continue
            project = entry.get("project") or "未分组项目"
            group = entry.get("group") or "默认分组"
            name = entry.get("name", "") or entry.get("content", "")
            item = QListWidgetItem(f"{project} / {group} / {name}")
            item.setData(self._ENTRY_ROLE, entry)
            item.setToolTip(entry.get("content", ""))
            self._search_list.addItem(item)
        if self._search_list.count() > 0:
            self._search_list.setCurrentRow(0)

    def _on_search_clicked(self, item):
        self._on_cmd_clicked(item)

    def _activate_current(self):
        if self._search_list.isVisible():
            item = self._search_list.currentItem() or (
                self._search_list.item(0) if self._search_list.count() else None
            )
            if item is not None:
                self._on_cmd_clicked(item)
            return
        item = self._cmd_list.currentItem()
        if item is None and self._cmd_list.count() > 0:
            item = self._cmd_list.item(0)
        if item is not None:
            self._on_cmd_clicked(item)


class _SerialScriptStepDialog(_FramelessChromeDialog):
    def __init__(self, parent=None, step: dict = None, mode: str = "create"):
        step = step or {}
        super().__init__(
            parent,
            title="ADD EXECUTION COMMAND" if mode == "create" else "EDIT STEP DIRECTIVE",
            icon_name="edit.svg",
        )
        self._apply_content_style(_DLG_STYLE)

        root = self._content
        root.setSpacing(14)

        card = QFrame()
        card.setObjectName("dlgGroupCard")
        form = QVBoxLayout(card)
        form.setContentsMargins(14, 12, 14, 12)
        form.setSpacing(8)

        cmd_lbl = QLabel("Step Command (TEXT/HEX payload)")
        cmd_lbl.setObjectName("dlgFieldLabel")
        form.addWidget(cmd_lbl)
        self._cmd_edit = QLineEdit(step.get("cmd", ""))
        self._cmd_edit.setPlaceholderText("e.g. AT+CWCAP")
        self._cmd_edit.setStyleSheet(dialog_line_edit_style())
        form.addWidget(self._cmd_edit)

        pw_row = QHBoxLayout()
        pw_row.setSpacing(8)
        prio_box = QVBoxLayout()
        prio_box.setSpacing(4)
        prio_lbl = QLabel("Priority Ordering")
        prio_lbl.setObjectName("dlgFieldLabel")
        prio_box.addWidget(prio_lbl)
        self._prio_spin = QSpinBox()
        self._prio_spin.setRange(1, 99999)
        self._prio_spin.setValue(int(step.get("priority", 1)) or 1)
        prio_box.addWidget(self._prio_spin)
        pw_row.addLayout(prio_box, 1)

        wait_box = QVBoxLayout()
        wait_box.setSpacing(4)
        wait_lbl = QLabel("Step Wait Delay (ms)")
        wait_lbl.setObjectName("dlgFieldLabel")
        wait_box.addWidget(wait_lbl)
        self._wait_spin = QSpinBox()
        self._wait_spin.setRange(0, 999999)
        self._wait_spin.setValue(int(step.get("wait_ms", 0)))
        wait_box.addWidget(self._wait_spin)
        pw_row.addLayout(wait_box, 1)
        form.addLayout(pw_row)

        kw_lbl = QLabel("Expected Wait Keyword (Optional)")
        kw_lbl.setObjectName("dlgFieldLabel")
        form.addWidget(kw_lbl)
        self._kw_edit = QLineEdit(step.get("wait_keyword", ""))
        self._kw_edit.setPlaceholderText("e.g. OK, READY, or SUCCESS")
        self._kw_edit.setStyleSheet(dialog_line_edit_style())
        form.addWidget(self._kw_edit)

        to_lbl = QLabel("Keyword Timeout (ms - default is Wait Delay)")
        to_lbl.setObjectName("dlgFieldLabel")
        form.addWidget(to_lbl)
        self._to_spin = QSpinBox()
        self._to_spin.setRange(0, 999999)
        self._to_spin.setValue(int(step.get("wait_timeout_ms", 0)))
        form.addWidget(self._to_spin)
        root.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(488)

    def _on_accept(self):
        if not self._cmd_edit.text().strip():
            QMessageBox.warning(self, "提示", "指令不能为空")
            return
        self.accept()

    def result_step(self) -> dict:
        return {
            "cmd": self._cmd_edit.text().strip(),
            "priority": int(self._prio_spin.value()),
            "wait_ms": int(self._wait_spin.value()),
            "wait_keyword": self._kw_edit.text().strip(),
            "wait_timeout_ms": int(self._to_spin.value()),
        }


class _SerialScriptEditorDialog(QDialog):
    _COLS = ["#", "COMMAND PAYLOAD", "WAIT (MS)", "WAIT KEYWORD", "TIMEOUT (MS)", "ACTIONS"]

    def __init__(self, parent=None, script: dict = None, quick_commands: list = None):
        super().__init__(parent)
        self.setWindowTitle("脚本编辑器")
        self.setObjectName("scEditorDialog")
        self.setMinimumSize(1008, 672)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(_DLG_STYLE + script_editor_dialog_style())
        script = script or {}
        self._quick_commands = list(quick_commands or [])
        self._drag_pos = None
        self._backdrop = None
        self._blur_effect = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(54, 50, 54, 62)
        outer.setSpacing(0)

        container = QFrame()
        container.setObjectName("scEditorContainer")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(15, 23, 42, 50))
        container.setGraphicsEffect(shadow)
        outer.addWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- 标题栏 ---
        header = QFrame()
        header.setObjectName("scEditorHeader")
        header.installEventFilter(self)
        self._header = header
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(24, 16, 20, 16)
        header_row.setSpacing(10)
        title_icon = QLabel()
        _ico = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "edit.svg"), _CLR_SEND_BG, 18)
        if not _ico.isNull():
            title_icon.setPixmap(_ico.pixmap(18, 18))
        header_row.addWidget(title_icon)
        title = QLabel("EDIT SUITE & SEQUENCE STEPS")
        title.setObjectName("scEditorTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        close_btn = QPushButton("\u2715")
        close_btn.setObjectName("scEditorClose")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(28, 28)
        close_btn.setAutoDefault(False)
        close_btn.setDefault(False)
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)
        root.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(24, 18, 24, 4)
        body.setSpacing(16)

        # --- SUITE NAME 卡片 ---
        prop_card = QFrame()
        prop_card.setObjectName("scEditorCard")
        prop_form = QVBoxLayout(prop_card)
        prop_form.setContentsMargins(20, 16, 20, 16)
        prop_form.setSpacing(8)

        name_lbl = QLabel("SUITE NAME")
        name_lbl.setObjectName("scEditorFieldLabel")
        prop_form.addWidget(name_lbl)

        prop_row = QHBoxLayout()
        prop_row.setSpacing(16)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. ESP32 WiFi Handshake Suite")
        self._name_edit.setText(script.get("name", ""))
        self._name_edit.setMinimumWidth(260)
        prop_row.addWidget(self._name_edit, 0)

        self._loop_cb = QCheckBox("Loop Sequence Execution")
        self._loop_cb.setChecked(bool(script.get("loop", False)))
        prop_row.addWidget(self._loop_cb)

        count_lbl = QLabel("Count")
        count_lbl.setObjectName("scEditorInlineLabel")
        prop_row.addWidget(count_lbl)
        self._loop_spin = QSpinBox()
        self._loop_spin.setRange(1, 99999)
        self._loop_spin.setValue(int(script.get("loop_count", 1)) or 1)
        self._loop_spin.setFixedWidth(78)
        prop_row.addWidget(self._loop_spin)

        self._loop_inf_cb = QCheckBox("\u221e")
        self._loop_inf_cb.setChecked(bool(script.get("loop_infinite", False)))
        self._loop_inf_cb.setToolTip("Loop forever until manually stopped")
        prop_row.addWidget(self._loop_inf_cb)

        self._loop_cb.toggled.connect(self._sync_loop_widgets)
        self._loop_inf_cb.toggled.connect(self._sync_loop_widgets)
        self._sync_loop_widgets()
        prop_row.addStretch()
        prop_form.addLayout(prop_row)
        body.addWidget(prop_card)

        # --- 步骤区标题 + Add Step ---
        steps_head = QHBoxLayout()
        steps_head.setSpacing(8)
        self._steps_title = QLabel("Sequence Directives (0)")
        self._steps_title.setObjectName("scEditorSectionTitle")
        steps_head.addWidget(self._steps_title)
        steps_head.addStretch()

        add_btn = QPushButton("  Add Step")
        add_btn.setObjectName("scEditorAddBtn")
        add_btn.setCursor(Qt.PointingHandCursor)
        _plus_icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "plus.svg"), _CLR_SEND_BG, 12)
        if not _plus_icon.isNull():
            add_btn.setIcon(_plus_icon)
        add_btn.setAutoDefault(False)
        add_btn.setDefault(False)
        add_btn.clicked.connect(lambda: self._add_row())
        steps_head.addWidget(add_btn)
        body.addLayout(steps_head)

        # --- 步骤表 ---
        self._table = QTableWidget(0, len(self._COLS))
        self._table.setObjectName("dlgStepTable")
        self._table.setHorizontalHeaderLabels(self._COLS)
        _kw_header_item = self._table.horizontalHeaderItem(3)
        if _kw_header_item is not None:
            _kw_header_item.setForeground(QColor("#9898ed"))
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setWordWrap(False)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.verticalHeader().setDefaultSectionSize(52)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        hdr = self._table.horizontalHeader()
        hdr.setMinimumSectionSize(64)
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (2, 3, 4, 5):
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 48)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 150)
        self._table.setColumnWidth(4, 120)
        self._table.setColumnWidth(5, 110)
        body.addWidget(self._table, 1)

        root.addLayout(body, 1)

        for step in script.get("steps", []):
            self._add_row(step)
        if self._table.rowCount() == 0:
            self._add_row()
        self._refresh_index_column()

        # --- 底部 Cancel / Save ---
        footer = QFrame()
        footer.setObjectName("scEditorFooter")
        btn_row = QHBoxLayout(footer)
        btn_row.setContentsMargins(24, 14, 24, 16)
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("scEditorCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Save Suite Configuration")
        ok_btn.setObjectName("scEditorSaveBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(ok_btn)
        root.addWidget(footer)

        self._script_id = script.get("id", "")

    def _target_window(self):
        parent = self.parent()
        if parent is None:
            return None
        return parent.window()

    def _install_backdrop(self):
        win = self._target_window()
        if win is None:
            return
        try:
            blur = QGraphicsBlurEffect(win)
            blur.setBlurRadius(9)
            win.setGraphicsEffect(blur)
            self._blur_effect = blur
        except Exception:
            self._blur_effect = None
        backdrop = QWidget(win)
        backdrop.setObjectName("scEditorBackdrop")
        backdrop.setStyleSheet(dialog_backdrop_style())
        backdrop.setGeometry(win.rect())
        backdrop.show()
        backdrop.raise_()
        self._backdrop = backdrop

    def _remove_backdrop(self):
        if self._backdrop is not None:
            self._backdrop.deleteLater()
            self._backdrop = None
        win = self._target_window()
        if win is not None:
            win.setGraphicsEffect(None)
        self._blur_effect = None

    def exec(self):
        self._install_backdrop()
        try:
            return super().exec()
        finally:
            self._remove_backdrop()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent  # 局部引入，避免顶部冗余导入
        if obj is getattr(self, "_header", None):
            et = event.type()
            if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if et == QEvent.MouseMove and self._drag_pos is not None and (event.buttons() & Qt.LeftButton):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                return True
            if et == QEvent.MouseButtonRelease:
                self._drag_pos = None
        return super().eventFilter(obj, event)

    def _wrap_cell(self, widget) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignVCenter)
        lay.addWidget(widget, 0, Qt.AlignVCenter)
        return holder

    def _make_cmd_cell(self, text: str) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignVCenter)
        edit = QLineEdit(text)
        edit.setPlaceholderText("如：AT+RST")
        holder._cmd_edit = edit
        lay.addWidget(edit, 1, Qt.AlignVCenter)
        pick_btn = QPushButton("选择")
        pick_btn.setObjectName("dlgRowBtn")
        pick_btn.setCursor(Qt.PointingHandCursor)
        pick_btn.setToolTip("从 Quick Commands 选择指令")
        pick_btn.clicked.connect(lambda: self._pick_quick_command(holder, pick_btn))
        if not self._quick_commands:
            pick_btn.setEnabled(False)
            pick_btn.setToolTip("暂无可选的 Quick Commands")
        lay.addWidget(pick_btn)
        return holder

    def _pick_quick_command(self, holder, anchor=None):
        if not self._quick_commands:
            return

        def _on_pick(entry):
            edit = getattr(holder, "_cmd_edit", None)
            if isinstance(edit, QLineEdit):
                edit.setText(entry.get("content", ""))

        popup = _QuickCommandPickerPopup(self, self._quick_commands, _on_pick)
        popup.popup_at(anchor)

    def _make_index_cell(self, row: int) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)
        lbl = QLabel(str(row + 1))
        lbl.setObjectName("scEditorRowIndex")
        lbl.setAlignment(Qt.AlignCenter)
        holder._index_label = lbl
        lay.addWidget(lbl)
        return holder

    def _make_keyword_cell(self, text: str) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignVCenter)
        edit = QLineEdit(text)
        edit.setPlaceholderText("如：OK")
        holder._kw_edit = edit
        lay.addWidget(edit, 1, Qt.AlignVCenter)
        return holder

    def _make_actions_cell(self, row: int) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignCenter)

        def _icon_btn(svg_name: str, tip: str, slot):
            btn = QPushButton()
            btn.setObjectName("scEditorRowIcon")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            ico = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, svg_name), _CLR_TEXT_MUTED, 15)
            if not ico.isNull():
                btn.setIcon(ico)
            btn.clicked.connect(slot)
            return btn

        up_btn = _icon_btn("arrow-up.svg", "上移", lambda: self._move_holder(holder, -1))
        down_btn = _icon_btn("arrow-down.svg", "下移", lambda: self._move_holder(holder, 1))
        del_btn = _icon_btn("trash.svg", "删除", lambda: self._del_holder(holder))
        lay.addWidget(up_btn)
        lay.addWidget(down_btn)
        lay.addWidget(del_btn)
        return holder

    def _add_row(self, step: dict = None):
        step = step or {
            "cmd": "", "priority": self._table.rowCount() + 1, "wait_ms": 1000,
            "wait_keyword": "", "wait_timeout_ms": 0,
        }
        row = self._table.rowCount()
        self._table.insertRow(row)

        self._table.setCellWidget(row, 0, self._make_index_cell(row))
        self._table.setCellWidget(row, 1, self._make_cmd_cell(step.get("cmd", "")))

        wait_spin = QSpinBox()
        wait_spin.setRange(0, 3600000)
        wait_spin.setSingleStep(100)
        wait_spin.setValue(int(step.get("wait_ms", 1000)))
        self._table.setCellWidget(row, 2, self._wrap_cell(wait_spin))

        self._table.setCellWidget(row, 3, self._make_keyword_cell(step.get("wait_keyword", "")))

        to_spin = QSpinBox()
        to_spin.setRange(0, 3600000)
        to_spin.setSingleStep(100)
        to_spin.setValue(int(step.get("wait_timeout_ms", 0)))
        self._table.setCellWidget(row, 4, self._wrap_cell(to_spin))

        self._table.setCellWidget(row, 5, self._make_actions_cell(row))
        self._refresh_index_column()

    def _refresh_index_column(self):
        count = self._table.rowCount()
        for row in range(count):
            holder = self._table.cellWidget(row, 0)
            lbl = getattr(holder, "_index_label", None) if holder else None
            if isinstance(lbl, QLabel):
                lbl.setText(str(row + 1))
        self._steps_title.setText(f"Sequence Directives ({count})")

    def _row_of_holder(self, holder) -> int:
        for row in range(self._table.rowCount()):
            for col in range(self._table.columnCount()):
                if self._table.cellWidget(row, col) is holder:
                    return row
        return -1

    def _move_holder(self, holder, delta: int):
        row = self._row_of_holder(holder)
        if row < 0:
            return
        self._table.setCurrentCell(row, 1)
        self._move_row(delta)

    def _del_holder(self, holder):
        row = self._row_of_holder(holder)
        if row < 0:
            return
        self._table.removeRow(row)
        self._refresh_index_column()

    def _del_row(self):
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def _move_row(self, delta: int):
        row = self._table.currentRow()
        if row < 0:
            return
        target = row + delta
        if target < 0 or target >= self._table.rowCount():
            return
        steps = self._collect_steps()
        steps[row], steps[target] = steps[target], steps[row]
        self._reload_steps(steps)
        self._table.setCurrentCell(target, 1)

    def _inner_widget(self, row: int, col: int):
        holder = self._table.cellWidget(row, col)
        if holder is None:
            return None
        lay = holder.layout()
        if lay is not None and lay.count() > 0:
            return lay.itemAt(0).widget()
        return holder

    def _renumber_priority(self):
        self._refresh_index_column()

    def _reload_steps(self, steps: list):
        self._table.setRowCount(0)
        for step in steps:
            self._add_row(step)
        self._refresh_index_column()

    def _collect_steps(self) -> list:
        steps = []
        for row in range(self._table.rowCount()):
            cmd_holder = self._table.cellWidget(row, 1)
            cmd_edit = getattr(cmd_holder, "_cmd_edit", None) if cmd_holder else None
            kw_holder = self._table.cellWidget(row, 3)
            kw_edit = getattr(kw_holder, "_kw_edit", None) if kw_holder else None
            wait = self._inner_widget(row, 2)
            to = self._inner_widget(row, 4)
            steps.append({
                "cmd": cmd_edit.text() if isinstance(cmd_edit, QLineEdit) else "",
                "priority": row + 1,
                "wait_ms": wait.value() if isinstance(wait, QSpinBox) else 0,
                "wait_keyword": kw_edit.text() if isinstance(kw_edit, QLineEdit) else "",
                "wait_timeout_ms": to.value() if isinstance(to, QSpinBox) else 0,
            })
        return steps

    def _on_accept(self):
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写脚本名称")
            return
        steps = [s for s in self._collect_steps() if s["cmd"].strip()]
        if not steps:
            QMessageBox.warning(self, "提示", "至少需要一个有内容的步骤")
            return
        self.accept()

    def _sync_loop_widgets(self, *args):
        loop_on = self._loop_cb.isChecked()
        loop_inf = self._loop_inf_cb.isChecked()
        self._loop_inf_cb.setEnabled(loop_on)
        self._loop_spin.setEnabled(loop_on and not loop_inf)

    def get_script(self) -> dict:
        return {
            "id": self._script_id,
            "name": self._name_edit.text().strip(),
            "loop": self._loop_cb.isChecked(),
            "loop_count": self._loop_spin.value(),
            "loop_infinite": self._loop_cb.isChecked() and self._loop_inf_cb.isChecked(),
            "steps": [s for s in self._collect_steps() if s["cmd"].strip()],
        }


class _QuickTextInputDialog(_FramelessChromeDialog):

    def __init__(self, parent=None, title="", label="", text="",
                 placeholder="", ok_text="OK"):
        super().__init__(parent, title=(title or "").upper(), icon_name="edit.svg")
        self._apply_content_style(quick_cmd_dialog_style())

        root = self._content
        root.setSpacing(10)

        if label:
            root.addWidget(QLabel(label))

        self._edit = QLineEdit()
        self._edit.setText(text)
        if placeholder:
            self._edit.setPlaceholderText(placeholder)
        self._edit.selectAll()
        self._edit.returnPressed.connect(self.accept)
        root.addWidget(self._edit)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton(ok_text)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(468)
        self._edit.setFocus()

    def get_text(self) -> str:
        return self._edit.text().strip()

    @staticmethod
    def get_input(parent=None, title="", label="", text="",
                  placeholder="", ok_text="OK"):
        dlg = _QuickTextInputDialog(
            parent=parent, title=title, label=label, text=text,
            placeholder=placeholder, ok_text=ok_text,
        )
        accepted = dlg.exec() == QDialog.Accepted
        return dlg.get_text(), accepted


class _QuickCmdDialog(_FramelessChromeDialog):

    def __init__(self, parent=None, name="", content="", send_type="text",
                 line_ending="\r\n", encoding="ascii"):
        is_edit = bool(name or content)
        super().__init__(
            parent,
            title="EDIT QUICK COMMAND" if is_edit else "NEW QUICK COMMAND",
            icon_name="edit.svg",
        )
        self._apply_content_style(quick_cmd_dialog_style())

        root = self._content
        root.setSpacing(10)

        root.addWidget(QLabel("指令名称"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如:查询版本")
        self._name_edit.setText(name)
        root.addWidget(self._name_edit)

        root.addWidget(QLabel("指令内容"))
        self._cmd_edit = QLineEdit()
        self._cmd_edit.setPlaceholderText("如:AT+GMR")
        self._cmd_edit.setText(content)
        root.addWidget(self._cmd_edit)

        root.addWidget(QLabel("发送方式"))
        self._send_type_combo = QComboBox()
        # 显示文案大写（TEXT / HEX），userData 保持小写以兼容旧数据
        self._send_type_combo.addItem("TEXT", "text")
        self._send_type_combo.addItem("HEX", "hex")
        idx = self._send_type_combo.findData(send_type)
        self._send_type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        root.addWidget(self._send_type_combo)

        root.addWidget(QLabel("结尾符"))
        self._line_ending_combo = QComboBox()
        self._line_ending_combo.addItem("无", "")
        self._line_ending_combo.addItem("\\r", "\r")
        self._line_ending_combo.addItem("\\n", "\n")
        self._line_ending_combo.addItem("\\r\\n", "\r\n")
        idx = self._line_ending_combo.findData(line_ending)
        self._line_ending_combo.setCurrentIndex(idx if idx >= 0 else 3)
        root.addWidget(self._line_ending_combo)

        root.addWidget(QLabel("编码"))
        self._encoding_combo = QComboBox()
        # 默认 ascii，放在第一位以便 setCurrentIndex(0) 兜底命中
        # 显示文案大写（ASCII / UTF-8 / GBK），userData 保持小写以兼容旧数据
        for enc_label, enc_value in (("ASCII", "ascii"), ("UTF-8", "utf-8"), ("GBK", "gbk")):
            self._encoding_combo.addItem(enc_label, enc_value)
        idx = self._encoding_combo.findData(encoding)
        self._encoding_combo.setCurrentIndex(idx if idx >= 0 else 0)
        root.addWidget(self._encoding_combo)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(488)

    def get_command(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "content": self._cmd_edit.text(),
            "send_type": self._send_type_combo.currentData() or "text",
            "line_ending": self._line_ending_combo.currentData() or "",
            "encoding": self._encoding_combo.currentData() or "ascii",
        }

    # 兼容老调用 (已无人使用)
    def get_name(self):
        return self._name_edit.text().strip()

    def get_cmd(self):
        return self._cmd_edit.text().strip()


class _SerialSaveDialog(_FramelessChromeDialog):

    def __init__(self, parent=None, default_dir="", default_name="", keep_timestamp=True):
        super().__init__(parent, title="SAVE LOGS", icon_name="edit.svg")
        self._apply_content_style(quick_cmd_dialog_style())

        root = self._content
        root.setSpacing(10)

        root.addWidget(QLabel("保存位置"))
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText("选择保存目录")
        self._dir_edit.setText(default_dir)
        dir_row.addWidget(self._dir_edit, 1)
        browse_btn = QPushButton("浏览…")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(dialog_cancel_button_style())
        browse_btn.setAutoDefault(False)
        browse_btn.setDefault(False)
        browse_btn.clicked.connect(self._on_browse)
        dir_row.addWidget(browse_btn)
        root.addLayout(dir_row)

        root.addWidget(QLabel("文件名"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如:serial_log.txt")
        self._name_edit.setText(default_name)
        root.addWidget(self._name_edit)

        self._keep_ts_cb = QCheckBox("保留系统时间戳（每行前缀 HH:MM:SS.fff）")
        self._keep_ts_cb.setChecked(keep_timestamp)
        root.addWidget(self._keep_ts_cb)

        hint = QLabel("点击保存后将写入当前完整日志，并持续追加后续新日志。")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Save")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(548)

    def _on_browse(self):
        current = self._dir_edit.text().strip()
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", current)
        if directory:
            self._dir_edit.setText(directory)

    def get_config(self) -> dict:
        return {
            "directory": self._dir_edit.text().strip(),
            "name": self._name_edit.text().strip(),
            "keep_timestamp": self._keep_ts_cb.isChecked(),
        }


class _SerialSettingsDialog(_FramelessChromeDialog):

    def __init__(self, parent=None):
        super().__init__(parent, title="SERIAL SETTINGS", icon_name="settings.svg")
        self._apply_content_style(_DLG_STYLE)
        self.setMinimumSize(720 + 108, 500 + 112)

        root = self._content
        root.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.setUsesScrollButtons(False)
        self._tabs.tabBar().setExpanding(False)
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_tab_serial(), "Serial")
        self._tabs.addTab(self._build_tab_rx(), "RX")
        self._tabs.addTab(self._build_tab_tx(), "TX")
        self._tabs.addTab(self._build_tab_log(), "Log")
        self._tabs.addTab(self._build_tab_display(), "Display")
        self._tabs.addTab(self._build_tab_auto_detect(), "Auto-Detect")
        self._tabs.addTab(self._build_tab_about(), "About")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    # ---- tab: Serial ----

    def _build_tab_serial(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Connection"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Port"), 0, 0)
        self.port_combo = SerialDarkComboBox()
        self.port_combo.setFixedHeight(26)
        grid.addWidget(self.port_combo, 0, 1)

        grid.addWidget(QLabel("Baudrate"), 1, 0)
        self.baud_combo = SerialDarkComboBox()
        self.baud_combo.setFixedHeight(26)
        self.baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "Custom"]:
            self.baud_combo.addItem(br)
        grid.addWidget(self.baud_combo, 1, 1)

        layout.addLayout(grid)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Advanced"))

        adv_grid = QGridLayout()
        adv_grid.setHorizontalSpacing(12)
        adv_grid.setVerticalSpacing(8)

        adv_grid.addWidget(QLabel("Data bits"), 0, 0)
        self.databit_combo = SerialDarkComboBox()
        self.databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self.databit_combo.addItem(d)
        adv_grid.addWidget(self.databit_combo, 0, 1)

        adv_grid.addWidget(QLabel("Stop bits"), 0, 2)
        self.stopbit_combo = SerialDarkComboBox()
        self.stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self.stopbit_combo.addItem(s)
        adv_grid.addWidget(self.stopbit_combo, 0, 3)

        adv_grid.addWidget(QLabel("Parity"), 1, 0)
        self.parity_combo = SerialDarkComboBox()
        self.parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self.parity_combo.addItem(p)
        adv_grid.addWidget(self.parity_combo, 1, 1)

        adv_grid.addWidget(QLabel("Flow Control"), 1, 2)
        self.flow_combo = SerialDarkComboBox()
        self.flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self.flow_combo.addItem(fc)
        adv_grid.addWidget(self.flow_combo, 1, 3)

        layout.addLayout(adv_grid)
        layout.addStretch()
        return page

    # ---- tab: RX ----

    def _build_tab_rx(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Data Format"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Encoding"))
        self.rx_hex_toggle = _MiniSlideToggle("ASCII", "HEX")
        row.addWidget(self.rx_hex_toggle)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Timestamp"))

        self.show_time_cb = QCheckBox("Show timestamp (ms precision)")
        layout.addWidget(self.show_time_cb)

        self.rx_use_ntp_cb = QCheckBox("Use network time (NTP calibrated)")
        layout.addWidget(self.rx_use_ntp_cb)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Buffer"))

        buf_row = QHBoxLayout()
        buf_row.setSpacing(8)
        buf_row.addWidget(QLabel("Max lines"))
        self.rx_max_lines_spin = QSpinBox()
        self.rx_max_lines_spin.setRange(500, 500000)
        self.rx_max_lines_spin.setValue(10000)
        self.rx_max_lines_spin.setSingleStep(1000)
        self.rx_max_lines_spin.setFixedHeight(26)
        self.rx_max_lines_spin.setToolTip(
            "RX log buffer size (lines). Higher values use more memory; "
            "500000 lines is about 100-300 MB depending on line length."
        )
        buf_row.addWidget(self.rx_max_lines_spin)
        buf_row.addStretch()
        layout.addLayout(buf_row)

        layout.addStretch()
        return page

    # ---- tab: TX ----

    def _build_tab_tx(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Data Format"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Encoding"))
        self.tx_hex_toggle = _MiniSlideToggle("ASCII", "HEX")
        row.addWidget(self.tx_hex_toggle)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Line Ending"))

        ending_row = QHBoxLayout()
        ending_row.setSpacing(8)
        ending_row.addWidget(QLabel("Line ending"))
        self.ending_combo = SerialDarkComboBox()
        self.ending_combo.setFixedHeight(26)
        for label, val in [("\\r\\n", "\r\n"), ("\\n", "\n"), ("\\r", "\r"), ("\\n\\r", "\n\r"), ("None", "")]:
            self.ending_combo.addItem(label, val)
        ending_row.addWidget(self.ending_combo)
        ending_row.addStretch()
        layout.addLayout(ending_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Other"))

        self.show_send_cb = QCheckBox("Show sent data in log")
        layout.addWidget(self.show_send_cb)

        self.line_by_line_cb = QCheckBox("Line by Line (split by \\n for multi-line send)")
        layout.addWidget(self.line_by_line_cb)

        layout.addStretch()
        return page

    # ---- tab: Log ----

    def _build_tab_log(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Log File"))

        self.log_auto_save_cb = QCheckBox("Auto save log to file")
        layout.addWidget(self.log_auto_save_cb)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        path_row.addWidget(QLabel("Save path"))
        self.log_save_path_edit = QLineEdit()
        self.log_save_path_edit.setPlaceholderText("Select log save directory...")
        self.log_save_path_edit.setStyleSheet(
            dialog_line_edit_style(size=12, min_height=24, padding="3px 6px")
        )
        path_row.addWidget(self.log_save_path_edit, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setObjectName("dlgCancelBtn")
        browse_btn.setAutoDefault(False)
        browse_btn.setDefault(False)
        browse_btn.clicked.connect(self._browse_log_path)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Log Level Colors"))

        color_info = QLabel(log_color_info_text())
        color_info.setStyleSheet(log_color_info_style())
        color_info.setWordWrap(True)
        layout.addWidget(color_info)

        layout.addStretch()
        return page

    # ---- tab: Display ----

    def _build_tab_display(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Font"))

        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_row.addWidget(QLabel("Font family"))
        self.display_font_combo = SerialDarkComboBox()
        self.display_font_combo.setFixedHeight(26)
        for f in ["Consolas", "Courier New", "Fira Code", "JetBrains Mono", "Cascadia Code", "Lucida Console"]:
            self.display_font_combo.addItem(f)
        font_row.addWidget(self.display_font_combo)
        font_row.addStretch()
        layout.addLayout(font_row)

        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        size_row.addWidget(QLabel("Font size"))
        self.display_font_size_spin = QSpinBox()
        self.display_font_size_spin.setRange(8, 24)
        self.display_font_size_spin.setValue(11)
        self.display_font_size_spin.setFixedHeight(26)
        size_row.addWidget(self.display_font_size_spin)
        size_row.addStretch()
        layout.addLayout(size_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Behavior"))

        self.display_auto_scroll_cb = QCheckBox("Enable auto-scroll by default")
        self.display_auto_scroll_cb.setChecked(True)
        layout.addWidget(self.display_auto_scroll_cb)

        self.display_word_wrap_cb = QCheckBox("Word Wrap")
        self.display_word_wrap_cb.setChecked(True)
        layout.addWidget(self.display_word_wrap_cb)

        self.display_show_line_num_cb = QCheckBox("Show line numbers")
        layout.addWidget(self.display_show_line_num_cb)

        layout.addStretch()
        return page

    # ---- tab: Auto-Detect ----

    def _build_tab_auto_detect(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Auto Baudrate Detection"))

        self.auto_detect_enable_cb = QCheckBox("Enable auto baudrate detection")
        layout.addWidget(self.auto_detect_enable_cb)

        self.auto_detect_runtime_cb = QCheckBox("Allow runtime auto re-detection")
        layout.addWidget(self.auto_detect_runtime_cb)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Candidate Baudrates"))

        self.auto_detect_candidates_edit = QLineEdit()
        self.auto_detect_candidates_edit.setPlaceholderText("e.g. 921600, 1152000, 2000000, 3000000")
        self.auto_detect_candidates_edit.setText(
            ", ".join(str(b) for b in AUTO_BAUD_CONFIG["candidate_baudrates"])
        )
        layout.addWidget(self.auto_detect_candidates_edit)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Thresholds"))

        thresh_grid = QGridLayout()
        thresh_grid.setHorizontalSpacing(12)
        thresh_grid.setVerticalSpacing(8)

        thresh_grid.addWidget(QLabel("Lock threshold"), 0, 0)
        self.auto_detect_lock_spin = QSpinBox()
        self.auto_detect_lock_spin.setRange(50, 100)
        self.auto_detect_lock_spin.setValue(AUTO_BAUD_CONFIG["lock_threshold"])
        self.auto_detect_lock_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_lock_spin, 0, 1)

        thresh_grid.addWidget(QLabel("Bad threshold"), 0, 2)
        self.auto_detect_bad_spin = QSpinBox()
        self.auto_detect_bad_spin.setRange(10, 80)
        self.auto_detect_bad_spin.setValue(AUTO_BAUD_CONFIG["bad_threshold"])
        self.auto_detect_bad_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_bad_spin, 0, 3)

        thresh_grid.addWidget(QLabel("Bad windows to suspect"), 1, 0)
        self.auto_detect_bad_windows_spin = QSpinBox()
        self.auto_detect_bad_windows_spin.setRange(1, 10)
        self.auto_detect_bad_windows_spin.setValue(AUTO_BAUD_CONFIG["bad_windows_to_suspect"])
        self.auto_detect_bad_windows_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_bad_windows_spin, 1, 1)

        thresh_grid.addWidget(QLabel("Suspect windows to scan"), 1, 2)
        self.auto_detect_suspect_windows_spin = QSpinBox()
        self.auto_detect_suspect_windows_spin.setRange(1, 10)
        self.auto_detect_suspect_windows_spin.setValue(AUTO_BAUD_CONFIG["suspect_windows_to_scan"])
        self.auto_detect_suspect_windows_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_suspect_windows_spin, 1, 3)

        layout.addLayout(thresh_grid)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Timing"))

        time_grid = QGridLayout()
        time_grid.setHorizontalSpacing(12)
        time_grid.setVerticalSpacing(8)

        time_grid.addWidget(QLabel("Monitor window (ms)"), 0, 0)
        self.auto_detect_window_ms_spin = QSpinBox()
        self.auto_detect_window_ms_spin.setRange(100, 2000)
        self.auto_detect_window_ms_spin.setValue(AUTO_BAUD_CONFIG["monitor_window_max_time_ms"])
        self.auto_detect_window_ms_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_window_ms_spin, 0, 1)

        time_grid.addWidget(QLabel("Switch cooldown (ms)"), 0, 2)
        self.auto_detect_cooldown_spin = QSpinBox()
        self.auto_detect_cooldown_spin.setRange(1000, 30000)
        self.auto_detect_cooldown_spin.setSingleStep(500)
        self.auto_detect_cooldown_spin.setValue(AUTO_BAUD_CONFIG["switch_cooldown_ms"])
        self.auto_detect_cooldown_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_cooldown_spin, 0, 3)

        time_grid.addWidget(QLabel("Score margin"), 1, 0)
        self.auto_detect_margin_spin = QSpinBox()
        self.auto_detect_margin_spin.setRange(5, 60)
        self.auto_detect_margin_spin.setValue(AUTO_BAUD_CONFIG["switch_score_margin"])
        self.auto_detect_margin_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_margin_spin, 1, 1)

        time_grid.addWidget(QLabel("Confirm rounds"), 1, 2)
        self.auto_detect_confirm_spin = QSpinBox()
        self.auto_detect_confirm_spin.setRange(1, 5)
        self.auto_detect_confirm_spin.setValue(AUTO_BAUD_CONFIG["confirm_scan_rounds"])
        self.auto_detect_confirm_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_confirm_spin, 1, 3)

        layout.addLayout(time_grid)

        layout.addStretch()
        return page

    # ---- tab: About ----

    def _build_tab_about(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(transparent_scroll_area_style() + SERIAL_SCROLLBAR_STYLE)

        content = QWidget()
        content.setObjectName("aboutPage")
        content.setStyleSheet("""
            QWidget#aboutPage QLabel#aboutHeroTitle {
                color: #1d1d1f;
                font-size: 19px;
                font-weight: 800;
            }
            QWidget#aboutPage QLabel#aboutHeroSub {
                color: #6e6e73;
                font-size: 12px;
            }
            QWidget#aboutPage QLabel#aboutCardTitle {
                color: #4f5b6b;
                font-size: 12px;
                font-weight: 800;
            }
            QWidget#aboutPage QLabel#aboutKey {
                color: #7a8290;
                font-size: 11px;
            }
            QWidget#aboutPage QLabel#aboutValue {
                color: #263245;
                font-size: 12px;
                font-weight: 600;
            }
            QWidget#aboutPage QLabel#aboutResetHint {
                color: #5d6675;
                font-size: 12px;
                line-height: 1.35;
            }
        """)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        about_info = {}
        parent = self.parent()
        if parent is not None and hasattr(parent, "_sc_about_info"):
            about_info = parent._sc_about_info()

        hero = QFrame()
        hero.setObjectName("scSectionCard")
        hero.setStyleSheet(section_card_style())
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(5)

        title = QLabel(about_info.get("Application", "KK Serial Console"))
        title.setObjectName("aboutHeroTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            f"App v{about_info.get('Version', '0.0.0')}  |  "
            f"Module v{about_info.get('Module version', '0.0.0')}  |  "
            f"Author: {about_info.get('Author', 'KK_Lab Team')}"
        )
        subtitle.setObjectName("aboutHeroSub")
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        info_card = QFrame()
        info_card.setObjectName("scSectionCard")
        info_card.setStyleSheet(section_card_style())
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(9)

        info_title = QLabel("Software Information")
        info_title.setObjectName("aboutCardTitle")
        info_layout.addWidget(info_title)

        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(14)
        info_grid.setVerticalSpacing(7)
        display_items = [
            ("Config schema", about_info.get("Config schema", "")),
            ("Quick Commands", about_info.get("Quick Commands", "0")),
            ("Runtime mode", about_info.get("Runtime mode", "")),
            ("Primary screen", about_info.get("Primary screen", "")),
        ]
        for row, (key, value) in enumerate(display_items):
            key_label = QLabel(key)
            key_label.setObjectName("aboutKey")
            info_grid.addWidget(key_label, row, 0)

            value_label = QLabel(str(value))
            value_label.setObjectName("aboutValue")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            info_grid.addWidget(value_label, row, 1)
        info_grid.setColumnStretch(1, 1)
        info_layout.addLayout(info_grid)
        layout.addWidget(info_card)

        config_card = QFrame()
        config_card.setObjectName("scSectionCard")
        config_card.setStyleSheet(section_card_style())
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(14, 12, 14, 12)
        config_layout.setSpacing(9)

        config_title = QLabel("User Configuration")
        config_title.setObjectName("aboutCardTitle")
        config_layout.addWidget(config_title)

        for key, value in (
            ("JSON file", about_info.get("Config file", "")),
            ("Directory", about_info.get("Config directory", "")),
        ):
            key_label = QLabel(key)
            key_label.setObjectName("aboutKey")
            config_layout.addWidget(key_label)

            path_edit = QLineEdit(str(value))
            path_edit.setReadOnly(True)
            path_edit.setCursorPosition(0)
            path_edit.setStyleSheet(dialog_line_edit_style(size=11, min_height=22, padding="3px 7px"))
            path_edit.setFixedHeight(28)
            config_layout.addWidget(path_edit)
            config_layout.addSpacing(4)

        reset_info = QLabel(
            "Reset restores Serial, RX/TX, display, history, and window settings to defaults. "
            "Quick Commands are kept unchanged."
        )
        reset_info.setObjectName("aboutResetHint")
        reset_info.setWordWrap(True)
        config_layout.addWidget(reset_info)

        reset_btn = QPushButton("Reset User JSON...")
        reset_btn.setObjectName("dlgCancelBtn")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setAutoDefault(False)
        reset_btn.setDefault(False)
        reset_btn.clicked.connect(self._on_reset_user_json_clicked)

        reset_row = QHBoxLayout()
        reset_row.addWidget(reset_btn)
        reset_row.addStretch()
        config_layout.addLayout(reset_row)

        layout.addWidget(config_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ---- helpers ----

    def _on_reset_user_json_clicked(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "_sc_reset_user_config_keep_quick_commands"):
            if parent._sc_reset_user_config_keep_quick_commands(self):
                self.reject()

    def _browse_log_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Log Save Directory")
        if path:
            self.log_save_path_edit.setText(path)

    @staticmethod
    def _section_title(text):
        lbl = QLabel(text)
        lbl.setObjectName("dlgSectionTitle")
        return lbl

    @staticmethod
    def _separator():
        sep = QFrame()
        sep.setObjectName("dlgSep")
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        return sep


if __name__ == "__main__":
    #python -m ui.modules.serialCom_module_frame
    import sys
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QFrame, QSizePolicy
    )

    class _CardFrame(QFrame):
        def __init__(self, title="", parent=None):
            super().__init__(parent)
            self.setObjectName("cardFrame")
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(12, 10, 12, 12)
            self.main_layout.setSpacing(8)
            if title:
                self.title_row = QHBoxLayout()
                self.title_row.setSpacing(8)
                self.title_label = QLabel(title)
                self.title_label.setObjectName("cardTitle")
                self.title_row.addWidget(self.title_label)
                self.title_row.addStretch()
                self.main_layout.addLayout(self.title_row)
            else:
                self.title_label = None
                self.title_row = None

    demo_logger = get_logger(f"{__name__}.demo")

    class _DemoSerialFullWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_FULL, prefix="FullDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Full Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            demo_logger.info(msg)

    class _DemoSerialSearchWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_SEARCH_SELECT, prefix="SearchDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Search & Select Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            demo_logger.info(msg)

    class _DemoSerialInlineWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_INLINE, prefix="InlineDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Inline Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            demo_logger.info(msg)

    class _DemoCompleteSerialWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_FULL, prefix="Complete")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            self.complete_serialComWidget(root)

            self._sc_on_refresh()
            self._sc_append_system("[INFO] KK Serials initialized", force_primary=True)

        def append_log(self, msg):
            self._sc_append_system(msg, force_primary=True)

        def closeEvent(self, event):
            try:
                self._sc_save_persisted_state()
            except Exception:
                pass
            self.close_serial()
            if hasattr(self, '_sc_independent_windows'):
                for win in list(self._sc_independent_windows):
                    win.close()
            super().closeEvent(event)

    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    def _custom_message_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return
        demo_logger.warning(message)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    qInstallMessageHandler(_custom_message_handler)

    _ICON_PATH = os.path.join(
        get_resource_base(), "resources", "icons", "serialcom_module.ico"
    )
    if os.path.isfile(_ICON_PATH):
        app.setWindowIcon(QIcon(_ICON_PATH))

    w4 = _DemoCompleteSerialWidget()
    w4.setWindowTitle("KK Serial Console")
    if os.path.isfile(_ICON_PATH):
        w4.setWindowIcon(QIcon(_ICON_PATH))
    w4._sc_apply_window_geometry()
    if getattr(w4, "_sc_restore_maximized", False):
        w4.showMaximized()
    else:
        w4.show()

    sys.exit(app.exec())
