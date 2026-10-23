# -*- coding: utf-8 -*-
"""持久化 Mixin：_sc_* persisted state / 窗口几何 / 配置迁移 / About（原 serialCom_module_frame.py 拆出）。"""

import os as _os
import sys as _sys
import json
import os

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)
from PySide6.QtCore import (
    QRect,
    QTimer,
)
from log_config import get_logger
from ui.resource_path import get_resource_base
from core.auto_baud_detector import AUTO_BAUD_CONFIG

logger = get_logger(__name__)

# 原 serialCom_module_frame 顶层 _PROJECT_ROOT（最终被 get_resource_base() 覆盖，保持一致）
_PROJECT_ROOT = get_resource_base()

class PersistenceMixin:
    """持久化 / 窗口几何 / 配置迁移 / About（原 SerialComMixin 拆出）。"""

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
                "footer_visible": True,
                "show_line_num": False,
                "primary_panel_title": "Serial Log",
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

        # 恢复只截断"超出可用区域"部分；禁按 margin 压尺寸
        # （对齐 n6705c_datalog 修复：150% DPI 下 margin 40 逻辑 px = 60 物理 px 空白）
        available = self._sc_screen_available_geometry_for(saved.center())
        width = min(saved.width(), available.width())
        height = min(saved.height(), available.height())

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
        # 主面板 Serial 真值在 _sc_primary_serial_cfg（侧栏会随聚焦面板切换显示值）；
        # 仅在真值不存在（未初始化）时回退读控件
        pcfg = getattr(self, "_sc_primary_serial_cfg", None)
        if isinstance(pcfg, dict):
            port_text = str(pcfg.get("port", "") or "")
            baud_text = str(pcfg.get("baudrate", "921600"))
            auto_detect = bool(pcfg.get("auto_detect", False))
            databit = str(pcfg.get("databit", "8"))
            stopbit = str(pcfg.get("stopbit", "1"))
            parity = str(pcfg.get("parity", "None"))
            flow_ctrl = str(pcfg.get("flow", "None"))
        else:
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
            "footer_visible": getattr(self, "_sc_footer_visible", True),
            "show_line_num": getattr(self, "_sc_show_line_num", False),
            "primary_panel_title": getattr(self, "_sc_primary_panel_title", "Serial Log"),
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

        extra_panels = []
        for panel in getattr(self, "_sc_extra_log_panels", []) or []:
            cfg = panel.get("config")
            if not isinstance(cfg, dict):
                continue
            panel_cfg = dict(cfg)
            panel_cfg.pop("connected", None)
            panel_cfg["independent_window"] = False
            panel_cfg["connected"] = bool(self._sc_extra_panel_is_connected(panel))
            extra_panels.append(panel_cfg)
        if extra_panels:
            persisted["extra_panels"] = extra_panels

        independent_windows = []
        for win in list(getattr(self, "_sc_independent_windows", []) or []):
            cfg = getattr(win, "_config", None)
            if not isinstance(cfg, dict):
                continue
            win_cfg = dict(cfg)
            win_cfg.pop("geometry", None)
            win_cfg.pop("connected", None)
            win_cfg["independent_window"] = True
            win_cfg["connected"] = bool(win.is_connected())
            geom = win.normalGeometry() if win.isMaximized() else win.geometry()
            if geom.width() > 0 and geom.height() > 0:
                win_cfg["geometry"] = {
                    "x": int(geom.x()),
                    "y": int(geom.y()),
                    "width": int(geom.width()),
                    "height": int(geom.height()),
                    "maximized": bool(win.isMaximized()),
                }
            independent_windows.append(win_cfg)
        if independent_windows:
            persisted["independent_windows"] = independent_windows
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

                # 恢复后把控件值回写主面板 Serial 真值，避免焦点切回时 Port 被空真值清空
                self._sc_primary_serial_cfg = self._sc_sidebar_serial_cfg_from_controls()

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
                    ("footer_visible", "_sc_footer_visible"),
                    ("show_line_num", "_sc_show_line_num"),
                    ("log_auto_save", "_sc_log_auto_save"),
                    ("log_save_path", "_sc_log_save_path"),
                ):
                    if key in ui_cfg:
                        setattr(self, attr, ui_cfg[key])
                if "primary_panel_title" in ui_cfg:
                    title = str(ui_cfg.get("primary_panel_title") or "Serial Log")
                    self._sc_primary_panel_title = title
                    if getattr(self, "_sc_log_panel", None) is not None:
                        self._sc_log_panel.title_label.setText(title)
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
                self._sc_hist_nav_reset()

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

            self._sc_restore_persisted_panels(data)
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
                ("footer_visible", "_sc_footer_visible"),
                ("show_line_num", "_sc_show_line_num"),
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
                self._sc_hist_nav_reset()

        # 同步 RX/TX Format 滑动开关的视觉态，避免重启后 UI 显示与实际解析格式不一致
        if hasattr(self, "_sc_rx_toggle"):
            self._sc_rx_toggle.set_value("HEX" if getattr(self, "_sc_rx_display_hex", False) else "ASCII")
        if hasattr(self, "_sc_tx_toggle"):
            self._sc_tx_toggle.set_value("HEX" if getattr(self, "_sc_tx_display_hex", False) else "ASCII")

        # 回放侧栏勾选/选中态（属性已恢复，控件默认态需对齐）：Show Time / Show Send / Line by Line / Line Ending
        if hasattr(self, "_sc_rx_show_time_cb"):
            self._sc_rx_show_time_cb.setChecked(bool(getattr(self, "_sc_show_timestamp", True)))
        if hasattr(self, "_sc_show_send_cb"):
            self._sc_show_send_cb.setChecked(bool(getattr(self, "_sc_show_send", True)))
        if hasattr(self, "_sc_line_by_line_cb"):
            self._sc_line_by_line_cb.setChecked(bool(getattr(self, "_sc_line_by_line", False)))
        if hasattr(self, "_sc_ending_combo"):
            _le = getattr(self, "_sc_line_ending", "\r\n")
            for _i in range(self._sc_ending_combo.count()):
                if (self._sc_ending_combo.itemData(_i) or "") == _le:
                    self._sc_ending_combo.setCurrentIndex(_i)
                    break
        # 主面板组件时间戳开关与真值对齐（组件 append_log 用自身 show_timestamp）
        if getattr(self, "_sc_log_panel", None) is not None:
            self._sc_log_panel.show_timestamp = bool(getattr(self, "_sc_show_timestamp", True))

        # 回放 Sidebar 显隐（按钮为 clicked 绑定，setChecked 不触发，须显式驱动）
        if hasattr(self, "_sc_sidebar_toggle_btn"):
            _sb_visible = bool(getattr(self, "_sc_sidebar_visible", True))
            self._sc_sidebar_toggle_btn.setChecked(_sb_visible)
            self._sc_on_sidebar_toggle(_sb_visible)

        # 回放 Footer 显隐（toggled 绑定，setChecked 即驱动 _sc_on_footer_toggle）
        if hasattr(self, "_sc_footer_toggle_btn"):
            self._sc_footer_toggle_btn.setChecked(
                bool(getattr(self, "_sc_footer_visible", True))
            )

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
        self._sc_hist_nav_reset()

        self._sc_sidebar_visible = True
        if hasattr(self, "_sc_sidebar_widget"):
            self._sc_sidebar_widget.setVisible(True)
        if hasattr(self, "_sc_sidebar_toggle_btn"):
            self._sc_sidebar_toggle_btn.setChecked(True)

        self._sc_primary_panel_title = "Serial Log"
        if getattr(self, "_sc_log_panel", None) is not None:
            self._sc_log_panel.title_label.setText("Serial Log")

        self._sc_footer_visible = True
        if hasattr(self, "_sc_quick_area"):
            self._sc_quick_area.setVisible(True)
        if hasattr(self, "_sc_footer_toggle_btn"):
            self._sc_footer_toggle_btn.setChecked(True)

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
