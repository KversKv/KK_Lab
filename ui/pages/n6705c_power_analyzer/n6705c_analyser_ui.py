#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from ui.resource_path import get_resource_base

sys.path.append(get_resource_base())

from ui.widgets.button import update_connect_button_state
from ui.widgets.instrument_state_poller import InstrumentStatePoller
from ui.modules.n6705c_module_frame import build_n6705c_inline_row
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QFrame, QApplication,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPixmap
from PySide6.QtSvg import QSvgRenderer

from instruments.power.keysight.n6705c import N6705C
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C
from core.ai.ui_action_registry import UIActionSpec
from log_config import get_logger
from ui.theme import FONT_MONO
from core.n6705c import SearchThread as _SearchThread
from ui.pages.n6705c_power_analyzer.widgets import (
    ChannelTabBar, _ZAP_ICON_PATH,
    CHANNEL_THEMES, CONTENT_BG, ROOT_BG, PANEL_BG, PANEL_BORDER,
    INPUT_BG, INPUT_BORDER,
    DISABLED_BG, DISABLED_BORDER, DISABLED_TEXT,
    DISABLED_BTN_BG, DISABLED_BTN_BORDER,
    INACTIVE_TAB_BG, INACTIVE_TAB_HOVER_BG,
    VALUE_OFF_COLOR, MODE_INACTIVE_TEXT,
    WIDGET_RADIUS, CONTAINER_RADIUS,
)
from ui.pages.n6705c_power_analyzer.analyser_view_setting import SettingViewMixin
from ui.pages.n6705c_power_analyzer.analyser_view_batch import BatchViewMixin
from ui.pages.n6705c_power_analyzer.analyser_view_consumption import ConsumptionViewMixin

logger = get_logger(__name__)


class N6705CAnalyserUI(QWidget, SettingViewMixin, BatchViewMixin, ConsumptionViewMixin):
    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()

        self._top = n6705c_top
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry
        self.devices = {
            "A": {"rm": None, "n6705c": None, "is_connected": False},
            "B": {"rm": None, "n6705c": None, "is_connected": False},
        }

        self.current_device = "A"
        self.current_channel = 1
        self.is_testing = False
        self._test_threads = {}
        self._test_workers = {}
        self._sync_thread = None
        self._sync_worker = None
        self._dirty_voltage = False
        self._dirty_current = False
        self.channels = []
        self._prev_dual_mode = None

        self._state_poller = InstrumentStatePoller(
            read_state_fn=self._read_channel_snapshot,
            apply_state_fn=self._apply_channel_snapshot,
            interval_s=1.0,
            busy_check_fn=self._is_active_session_busy,
            io_lock_provider=self._active_session_io_lock,
            parent=self,
        )

        self._setup_style()
        self._create_layout()

        self._search_threads = {}

        self._apply_channel_theme(self.current_device, self.current_channel)
        self._rebuild_dynamic_sections()
        self._update_ui_connection_state("A", False)

        if self._top:
            self._sync_from_top()
            if hasattr(self._top, 'connection_changed'):
                self._top.connection_changed.connect(self._sync_from_top)

        if self._instrument_manager:
            self._instrument_manager.sessions_changed.connect(self._on_manager_sessions_changed)
            self._instrument_manager.connection_failed.connect(self._on_manager_connection_failed)

        # §5b：登记本页无专用接口的按钮为具名 UI 动作（白名单制，handler 复用原槽）
        self._register_ai_ui_actions()

    def _register_ai_ui_actions(self):
        """§5b.5：登记本页无专用接口的按钮（Auto Set 系列）为 AI 可触发的具名 UI 动作。

        handler 直接复用按钮原 clicked.connect 的槽（_on_batch_auto_set 等），
        行为与人点按钮完全一致；enabled_when 校验至少一台 N6705C 已连接，
        不满足时 list_ui_actions 不返回、ui_invoke 明示不可用（不盲点）。
        """
        registry = self._ui_action_registry
        if registry is None:
            return

        def _any_connected() -> bool:
            return any(d.get("is_connected") for d in self.devices.values())

        def _wrap(label, fn):
            def _run() -> tuple[bool, str]:
                try:
                    fn()
                    return True, f"{label} 已执行（按所选通道/设备生效）。"
                except Exception as exc:  # noqa: BLE001
                    logger.error("%s 执行失败", label, exc_info=True)
                    return False, f"{label} 执行失败：{exc}"
            return _run

        registry.register_many([
            UIActionSpec(
                id="power_analyser.auto_set",
                label="Auto Set",
                page_key="power_analyser",
                handler=_wrap("Auto Set", self._on_batch_auto_set),
                risk="high",
                confirm=True,
                enabled_when=_any_connected,
                description=(
                    "批量自动设置：测当前电压并对齐到 50mV 网格（含特殊电压），"
                    "设电流限值并打开通道输出。需至少一台 N6705C 已连接并选中通道。"
                ),
            ),
            UIActionSpec(
                id="power_analyser.auto_set_20mv",
                label="Auto Set (+20mV)",
                page_key="power_analyser",
                handler=_wrap("Auto Set (+20mV)", self._on_batch_auto_20mv),
                risk="high",
                confirm=True,
                enabled_when=_any_connected,
                description=(
                    "批量自动设置（+20mV 偏移）：测当前电压后 +20mV 设为目标，"
                    "设电流限值并打开通道输出。需至少一台 N6705C 已连接并选中通道。"
                ),
            ),
        ])

    def _on_manager_connection_failed(self, session_id: str, error: str):
        if not session_id.startswith("n6705c:"):
            return
        label = session_id.split(":")[1].upper() if ":" in session_id else None
        if label is None or label not in self.conn_widgets:
            return
        w = self.conn_widgets[label]
        w["status"].setText("Connection failed")
        w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
        w["connect_btn"].setEnabled(True)
        logger.error("[%s] Manager connection failed: %s", label, error)

    def _on_manager_sessions_changed(self):
        if not self._instrument_manager:
            return
        sessions = self._instrument_manager.sessions(instrument_type="n6705c")
        for snap in sessions:
            label = snap.slot.upper() if snap.slot in ("A", "B", "a", "b") else None
            if label is None:
                continue
            w = self.conn_widgets.get(label)
            if w is None:
                continue
            if snap.connected:
                instance = self._instrument_manager.get_instance(snap.session_id)
                self.devices[label]["n6705c"] = instance
                self.devices[label]["is_connected"] = True
                w["status"].setText("\u25cf Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                if snap.resource:
                    w["combo"].clear()
                    w["combo"].addItem(snap.resource)
                update_connect_button_state(w["connect_btn"], connected=True)
                w["connect_btn"].setEnabled(True)
                self._update_ui_connection_state(label, True)
            else:
                if self.devices[label]["is_connected"]:
                    self.devices[label]["n6705c"] = None
                    self.devices[label]["is_connected"] = False
                    w["status"].setText("\u25cf Disconnected")
                    w["status"].setStyleSheet("color: #8ea6cf; font-weight:bold;")
                    update_connect_button_state(w["connect_btn"], connected=False)
                    w["connect_btn"].setEnabled(True)
                    self._update_ui_connection_state(label, False)
        self._rebuild_dynamic_sections()
        if self.devices[self.current_device]["is_connected"]:
            self._start_channel_sync()
        else:
            self._state_poller.pause()

    def _connected_device_labels(self):
        return [label for label, dev in self.devices.items() if dev["is_connected"]]

    def _is_dual_mode(self):
        return len(self._connected_device_labels()) >= 2

    def _rebuild_dynamic_sections(self):
        dual = self._is_dual_mode()
        if dual == self._prev_dual_mode:
            return
        self._prev_dual_mode = dual

        connected = self._connected_device_labels()
        if connected and self.current_device not in connected:
            self.current_device = connected[0]
            self.current_channel = 1

        self._build_channel_tab_buttons()
        self._build_batch_columns()
        self._build_ct_cards()
        self._apply_channel_theme(self.current_device, self.current_channel)

    def _sync_from_top(self):
        if not self._top:
            return
        for label, attr_suffix in [("A", "a"), ("B", "b")]:
            n6705c = getattr(self._top, f"n6705c_{attr_suffix}", None)
            is_conn = getattr(self._top, f"is_connected_{attr_suffix}", False)
            visa_res = getattr(self._top, f"visa_resource_{attr_suffix}", "")
            w = self.conn_widgets[label]
            if is_conn and n6705c:
                self.devices[label]["n6705c"] = n6705c
                self.devices[label]["is_connected"] = True
                w["status"].setText("\u25cf Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                if visa_res:
                    w["combo"].clear()
                    w["combo"].addItem(visa_res)
                update_connect_button_state(w["connect_btn"], connected=True)
                self._update_ui_connection_state(label, True)
            else:
                if self.devices[label]["is_connected"]:
                    self.devices[label]["n6705c"] = None
                    self.devices[label]["is_connected"] = False
                    w["status"].setText("\u25cf Disconnected")
                    w["status"].setStyleSheet("color: #8ea6cf; font-weight:bold;")
                    update_connect_button_state(w["connect_btn"], connected=False)
                    self._update_ui_connection_state(label, False)
        self._rebuild_dynamic_sections()
        if self.devices[self.current_device]["is_connected"]:
            self._start_channel_sync()
        else:
            self._state_poller.pause()

    def _is_active_session_busy(self):
        if not self._instrument_manager:
            return False
        session = self._instrument_manager.get_session(f"n6705c:{self.current_device}")
        if session and session.connected:
            return bool(session.busy)
        return False

    def _active_session_io_lock(self):
        """返回当前设备会话的共享 IO 锁，与 AI 读/写动作串行化同一会话的总线访问。

        无 manager（页面独立运行）时返回 None，poller 回退到自带的本地锁。
        """
        if not self._instrument_manager:
            return None
        getter = getattr(self._instrument_manager, "io_lock", None)
        if not callable(getter):
            return None
        return getter(f"n6705c:{self.current_device}")

    def _start_channel_sync(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        if self.isVisible():
            self._state_poller.resume()

    def _read_channel_snapshot(self):
        dev = self.devices.get(self.current_device)
        if not dev or not dev["is_connected"] or not dev["n6705c"]:
            return None
        n6705c = dev["n6705c"]
        channel_num = self.current_channel
        data = {"device": self.current_device, "channel": channel_num}
        try:
            data["channel_state"] = n6705c.get_channel_state(channel_num)
        except Exception:
            data["channel_state"] = None
        try:
            data["mode"] = n6705c.get_mode(channel_num)
        except Exception:
            data["mode"] = None
        try:
            data["voltage"] = float(n6705c.measure_voltage(channel_num))
        except Exception:
            data["voltage"] = None
        try:
            data["current"] = float(n6705c.measure_current(channel_num))
        except Exception:
            data["current"] = None
        try:
            data["limit_current"] = float(n6705c.get_current_limit(channel_num))
        except Exception:
            data["limit_current"] = None
        return data

    def _apply_channel_snapshot(self, data):
        if data.get("device") != self.current_device or data.get("channel") != self.current_channel:
            return

        if data.get("channel_state") is not None:
            self.output_toggle.blockSignals(True)
            self.output_toggle.setChecked(data["channel_state"])
            self.output_toggle.blockSignals(False)
        self._update_output_visual_state()

        mode_raw = data.get("mode")
        if mode_raw is not None:
            ui_mode = self._map_instrument_mode_to_ui_mode(mode_raw)
            for btn in self.mode_buttons:
                btn.setChecked(btn.text() == ui_mode)
            self._apply_mode_button_styles()
            self._update_labels_for_mode(ui_mode)

        if self._dirty_voltage or self._dirty_current:
            return

        voltage = data.get("voltage")
        current = data.get("current")
        limit_current = data.get("limit_current")
        if voltage is not None and current is not None and limit_current is not None:
            self.update_channel_values(self.current_device, self.current_channel, voltage, current, limit_current)

        self._dirty_voltage = False
        self._dirty_current = False
        self._update_set_button_dirty_state()

    def showEvent(self, event):
        super().showEvent(event)
        if self.devices[self.current_device]["is_connected"]:
            self._state_poller.resume()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._state_poller.pause()

    def closeEvent(self, event):
        self._state_poller.stop()
        super().closeEvent(event)

    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setObjectName("RootWidget")
        self.setStyleSheet(f"""
        QWidget#RootWidget {{ background-color: {ROOT_BG}; }}
        QWidget {{ background-color: {ROOT_BG}; color: #d6e2ff; }}
        QLabel {{ color: #c8d6f0; background: transparent; border: none; }}
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {INPUT_BG}; border: 1px solid {INPUT_BORDER};
            border-radius: {WIDGET_RADIUS}; padding: 4px 6px; color: #d7e3ff;
        }}
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid #3a6cc8;
        }}
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            width: 0px; height: 0px; border: none;
        }}
        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
            background-color: #070F28; border: 1px solid #131D3A; color: {DISABLED_TEXT};
        }}
        QPushButton {{
            background-color: #0b1730; border: 1px solid #23417a;
            border-radius: {WIDGET_RADIUS}; padding: 6px 14px; color: #dbe6ff;
        }}
        QPushButton:hover {{ background-color: #10203e; }}
        QPushButton:disabled {{
            background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER};
        }}
        QCheckBox:disabled {{ color: {DISABLED_TEXT}; }}
        """)

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(12, 12, 12, 12)

        self.top_bar = self._create_top_bar()
        main_layout.addWidget(self.top_bar)
        main_layout.addSpacing(8)

        self.channel_interaction_frame = QFrame()
        self.channel_interaction_frame.setStyleSheet("""
            QFrame#ChannelInteractionFrame {
                background-color: transparent;
                border: none;
            }
        """)
        self.channel_interaction_frame.setObjectName("ChannelInteractionFrame")
        ci_layout = QVBoxLayout(self.channel_interaction_frame)
        ci_layout.setContentsMargins(0, 0, 0, 0)
        ci_layout.setSpacing(0)

        self.channel_tabs = self._create_channel_tabs()
        ci_layout.addWidget(self.channel_tabs)

        self.setting_widget = self._create_setting_widget()
        ci_layout.addWidget(self.setting_widget)

        main_layout.addWidget(self.channel_interaction_frame)
        main_layout.addSpacing(8)

        self.batch_tools_panel = self._create_batch_tools_panel()
        main_layout.addWidget(self.batch_tools_panel)
        main_layout.addSpacing(8)

        self.consumption_test_panel = self._create_consumption_test_panel()
        main_layout.addWidget(self.consumption_test_panel)

        main_layout.addStretch()

    def _create_top_bar(self):
        top_frame = QFrame()
        top_frame.setStyleSheet(f"""
            QFrame {{ background-color: {ROOT_BG}; border: 1px solid {PANEL_BORDER}; border-radius: {CONTAINER_RADIUS}; }}
        """)
        outer_layout = QVBoxLayout(top_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        header_widget = QWidget()
        header_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {ROOT_BG}; border: none;
                border-top-left-radius: {CONTAINER_RADIUS};
                border-top-right-radius: {CONTAINER_RADIUS};
            }}
        """)
        header_widget.setFixedHeight(54)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        if os.path.isfile(_ZAP_ICON_PATH):
            renderer = QSvgRenderer(_ZAP_ICON_PATH)
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            renderer.render(painter)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor("#10b981"))
            painter.end()
            icon_label.setPixmap(pixmap)
        icon_label.setStyleSheet("QLabel { background: transparent; border: none; }")
        header_layout.addWidget(icon_label)

        title_label = QLabel("Keysight N6705C DC Power Analyzer")
        title_label.setStyleSheet("QLabel { color: #ffffff; font-size: 18px; font-weight: 800; }")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        outer_layout.addWidget(header_widget)

        header_sep = QFrame()
        header_sep.setFixedHeight(1)
        header_sep.setStyleSheet(f"background-color: {PANEL_BORDER}; border: none;")
        outer_layout.addWidget(header_sep)

        content_widget = QWidget()
        content_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {ROOT_BG}; border: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
            }}
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 4, 16, 10)
        content_layout.setSpacing(2)

        default_addresses = {
            "A": "TCPIP0::K-N6705C-06098.local::hislip0::INSTR",
            "B": "TCPIP0::K-N6705C-03845.local::hislip0::INSTR",
        }

        self.conn_widgets = {}
        for label in ["A", "B"]:
            row_layout, widgets = build_n6705c_inline_row(
                label, parent=self, default_resource=default_addresses[label]
            )
            widgets["connect_btn"].clicked.connect(
                lambda _checked=False, lb=label: self._on_toggle_connection(lb)
            )
            widgets["search_btn"].clicked.connect(
                lambda _checked=False, lb=label: self._on_search(lb)
            )
            content_layout.addLayout(row_layout)
            self.conn_widgets[label] = widgets

        outer_layout.addWidget(content_widget)
        return top_frame

    def _create_channel_tabs(self):
        self._tab_bar = ChannelTabBar()

        self._channel_tabs_layout = self._tab_bar.layout()

        self.channel_tab_buttons = []
        self._channel_tab_separator = None
        self._build_channel_tab_buttons()

        return self._tab_bar

    def _build_channel_tab_buttons(self):
        for btn in self.channel_tab_buttons:
            self._channel_tabs_layout.removeWidget(btn)
            btn.deleteLater()
        self.channel_tab_buttons.clear()

        if self._channel_tab_separator is not None:
            self._channel_tabs_layout.removeWidget(self._channel_tab_separator)
            self._channel_tab_separator.deleteLater()
            self._channel_tab_separator = None

        while self._channel_tabs_layout.count():
            item = self._channel_tabs_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._channel_tabs_layout.setContentsMargins(0, 4, 0, 0)
        self._channel_tabs_layout.setSpacing(2)

        dual = self._is_dual_mode()
        if dual:
            for dev_label in ["A", "B"]:
                for ch in range(1, 5):
                    btn = QPushButton(f"\u25cf {dev_label}-CH{ch}")
                    btn.setCheckable(True)
                    btn.setMinimumSize(90, 36)
                    btn.setCursor(Qt.PointingHandCursor)
                    btn.clicked.connect(
                        lambda checked=False, d=dev_label, c=ch: self._switch_channel(d, c)
                    )
                    self.channel_tab_buttons.append(btn)
                    self._channel_tabs_layout.addWidget(btn)
                if dev_label == "A":
                    sep = QFrame()
                    sep.setFixedWidth(2)
                    sep.setFixedHeight(24)
                    sep.setStyleSheet("QFrame { background: #1b2847; border: none; }")
                    self._channel_tab_separator = sep
                    self._channel_tabs_layout.addWidget(sep)
        else:
            for ch in range(1, 5):
                btn = QPushButton(f"\u25cf CH{ch}")
                btn.setCheckable(True)
                btn.setMinimumSize(90, 36)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(
                    lambda checked=False, c=ch: self._switch_channel(self._get_single_device_label(), c)
                )
                self.channel_tab_buttons.append(btn)
                self._channel_tabs_layout.addWidget(btn)

        self._channel_tabs_layout.addStretch()

        any_connected = any(d["is_connected"] for d in self.devices.values())
        for btn in self.channel_tab_buttons:
            btn.setEnabled(any_connected)

        if self.channel_tab_buttons:
            self.channel_tab_buttons[0].setChecked(True)
        self._refresh_channel_tab_styles()

    def _get_single_device_label(self):
        connected = self._connected_device_labels()
        if connected:
            return connected[0]
        return "A"

    def _channel_action_button_style(self, accent, accent_hover):
        return f"""
        QPushButton {{
            background-color: #0c1a38; color: {accent};
            border: 1px solid {accent}; border-radius: {WIDGET_RADIUS};
            padding: 9px 18px; font-size: 12px; min-width: 88px; min-height: 36px; font-weight: 700;
        }}
        QPushButton:hover {{ background-color: #12213f; color: {accent_hover}; border: 1px solid {accent_hover}; }}
        QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """

    def _dirty_set_button_style(self, accent):
        theme = CHANNEL_THEMES[self.current_channel]
        hover = theme['accent_hover']
        return f"""
        QPushButton {{
            background-color: {accent}; color: #111111; border: none;
            border-radius: {WIDGET_RADIUS}; padding: 9px 18px; font-size: 12px;
            min-width: 88px; min-height: 36px; font-weight: 700;
        }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """

    def _build_channel_tab_style(self, dev_label, ch, checked=False):
        theme = CHANNEL_THEMES[ch]
        border_color = theme['accent_border'] if checked else "#14305e"
        dual = self._is_dual_mode()
        font_size = "11px" if dual else "12px"
        corner = WIDGET_RADIUS

        top_radius = f"border-top-left-radius: {corner}; border-top-right-radius: {corner};"
        bottom_radius = "border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;"
        radius_str = f"{top_radius} {bottom_radius}"

        disabled_part = f"""
            QPushButton:disabled {{
                background-color: #0a1224; color: #3a4a6a;
                border: 1px solid #151f36;
                border-bottom: 1px solid #151f36;
                {radius_str}
                padding: 9px 12px; font-size: {font_size}; font-weight: 700;
            }}
        """
        if checked:
            active_pad = "9px 12px" if dual else "10px 18px"
            return f"""
            QPushButton {{
                background-color: {CONTENT_BG}; color: {theme['accent']};
                border: 1px solid {border_color};
                border-bottom: 1px solid {CONTENT_BG};
                {radius_str}
                padding: {active_pad}; font-size: {font_size}; font-weight: 700;
                margin-bottom: 0px;
            }}
            {disabled_part}
            """
        else:
            inactive_pad = "9px 12px" if dual else "10px 18px"
            return f"""
            QPushButton {{
                background-color: {INACTIVE_TAB_BG}; color: {theme['text_dim']};
                border: 1px solid #1b2847;
                border-bottom: 1px solid {self._get_current_border_color()};
                {radius_str}
                padding: {inactive_pad}; font-size: {font_size}; font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {INACTIVE_TAB_HOVER_BG}; color: #ffffff;
                border: 1px solid {theme['accent_border']};
                border-bottom: 1px solid {self._get_current_border_color()};
            }}
            {disabled_part}
            """

    def _get_current_border_color(self):
        theme = CHANNEL_THEMES.get(self.current_channel, CHANNEL_THEMES[1])
        return theme['accent_border']

    def _build_mode_button_style(self, active=False):
        theme = CHANNEL_THEMES[self.current_channel]
        disabled_part = f"""
            QPushButton:disabled {{
                background-color: transparent; color: #3a4a6a;
                border: none; padding: 6px 14px; font-size: 12px; border-radius: {WIDGET_RADIUS};
            }}
        """
        if active:
            return f"""
            QPushButton {{
                background-color: {theme['accent']}; color: #111111;
                border: none; padding: 6px 14px; font-size: 12px;
                font-weight: 700; border-radius: {WIDGET_RADIUS};
            }}
            {disabled_part}
            """
        else:
            return f"""
            QPushButton {{
                background-color: transparent; color: {MODE_INACTIVE_TEXT};
                border: none; padding: 6px 14px; font-size: 12px; border-radius: {WIDGET_RADIUS};
            }}
            QPushButton:hover {{ background-color: #0f1d35; color: #dbe6ff; }}
            {disabled_part}
            """

    def _apply_mode_button_styles(self):
        for btn in self.mode_buttons:
            btn.setStyleSheet(self._build_mode_button_style(btn.isChecked()))

    def _refresh_channel_tab_styles(self):
        dual = self._is_dual_mode()
        total = len(self.channel_tab_buttons)
        idx = 0
        active_btn = None
        if dual:
            for dev_label in ["A", "B"]:
                for ch in range(1, 5):
                    if idx < total:
                        is_active = (dev_label == self.current_device and ch == self.current_channel)
                        self.channel_tab_buttons[idx].setStyleSheet(
                            self._build_channel_tab_style(dev_label, ch, is_active)
                        )
                        self.channel_tab_buttons[idx].setChecked(is_active)
                        if is_active:
                            active_btn = self.channel_tab_buttons[idx]
                        idx += 1
        else:
            single_label = self._get_single_device_label()
            for ch in range(1, 5):
                if idx < total:
                    is_active = (ch == self.current_channel)
                    self.channel_tab_buttons[idx].setStyleSheet(
                        self._build_channel_tab_style(single_label, ch, is_active)
                    )
                    self.channel_tab_buttons[idx].setChecked(is_active)
                    if is_active:
                        active_btn = self.channel_tab_buttons[idx]
                    idx += 1

        QTimer.singleShot(0, lambda: self._update_tab_bar_active_rect(active_btn))

    def _update_tab_bar_active_rect(self, active_btn):
        if active_btn and hasattr(self, '_tab_bar'):
            rect = active_btn.geometry()
            self._tab_bar.set_active_tab_rect(rect)
        elif hasattr(self, '_tab_bar'):
            self._tab_bar.set_active_tab_rect(None)

    def _apply_channel_theme(self, dev_label, channel_num):
        theme = CHANNEL_THEMES[channel_num]
        dual = self._is_dual_mode()
        if dual:
            self.channel_title_label.setText(f"{dev_label} - Channel {channel_num}")
        else:
            self.channel_title_label.setText(f"Channel {channel_num}")

        border_color = theme['accent_border']

        self.setting_frame.setStyleSheet(f"""
            QFrame#SettingContentFrame {{
                background-color: {CONTENT_BG};
                border: 1px solid {border_color};
                border-top: none;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)

        self.channel_interaction_frame.setStyleSheet(f"""
            QFrame#ChannelInteractionFrame {{
                background-color: transparent;
                border: none;
            }}
        """)

        if hasattr(self, '_tab_bar'):
            self._tab_bar.set_border_color(border_color)

        self.output_toggle.setAccentColor(theme['accent'])

        btn_style = self._channel_action_button_style(theme['accent'], theme['accent_hover'])
        self.measure_btn.setStyleSheet(btn_style)
        self.set_btn.setStyleSheet(btn_style)

        self._refresh_channel_tab_styles()
        self._apply_mode_button_styles()
        self._update_output_visual_state()
        self._update_set_button_dirty_state()

    def _on_voltage_text_changed(self, text):
        self._dirty_voltage = True
        self._update_set_button_dirty_state()

    def _on_current_text_changed(self, text):
        self._dirty_current = True
        self._update_set_button_dirty_state()

    def _update_set_button_dirty_state(self):
        if (self._dirty_voltage or self._dirty_current) and self.set_btn.isEnabled():
            theme = CHANNEL_THEMES[self.current_channel]
            self.set_btn.setStyleSheet(self._dirty_set_button_style(theme['accent']))
        else:
            theme = CHANNEL_THEMES[self.current_channel]
            self.set_btn.setStyleSheet(self._channel_action_button_style(theme['accent'], theme['accent_hover']))

    def _update_output_visual_state(self):
        is_on = self.output_toggle.isChecked()
        theme = CHANNEL_THEMES[self.current_channel]
        accent = theme['accent']

        value_color = accent if is_on else VALUE_OFF_COLOR

        self.voltage_value.setStyleSheet(f"""
            QLineEdit {{ font-family: {FONT_MONO}; font-size: 26px; font-weight: bold; color: {value_color}; background: transparent; border: none; letter-spacing: 1px; }}
        """)
        self.current_value.setStyleSheet(f"""
            QLineEdit {{ font-family: {FONT_MONO}; font-size: 26px; font-weight: bold; color: {value_color}; background-color: transparent; border: none; letter-spacing: 1px; }}
        """)

    def _switch_channel(self, dev_label, ch):
        logger.debug("Switch channel: dev=%s, CH%s", dev_label, ch)
        self.current_device = dev_label
        self.current_channel = ch
        self._dirty_voltage = False
        self._dirty_current = False
        self._apply_channel_theme(dev_label, ch)
        self._start_channel_sync()

    def _map_instrument_mode_to_ui_mode(self, inst_mode):
        mapping = {
            "PS2Q": "PS2Q", "CCL": "CC", "CCLOAD": "CC", "CCLoad": "CC",
            "VMET": "VMETer", "VMETER": "VMETer", "VMETer": "VMETer",
            "AMET": "AMETer", "AMETER": "AMETer", "AMETer": "AMETer",
        }
        return mapping.get(inst_mode, inst_mode)

    def _map_ui_mode_to_instrument_mode(self, ui_mode):
        return {"PS2Q": "PS2Q", "CC": "CCLoad", "VMETer": "VMETer", "AMETer": "AMETer"}.get(ui_mode, "PS2Q")

    def _get_current_mode_text(self):
        if self.cv_btn.isChecked():
            return "PS2Q"
        if self.cc_btn.isChecked():
            return "CC"
        if self.cr_btn.isChecked():
            return "VMETer"
        if self.cp_btn.isChecked():
            return "AMETer"
        return "PS2Q"

    def _update_labels_for_mode(self, ui_mode):
        if ui_mode == "PS2Q":
            self.voltage_set_label.setText("Set")
            self.current_set_label.setText("Lim")
            self.voltage_set_input.setEnabled(True)
            self.limit_current_value.setEnabled(True)
            self.voltage_input_container.setStyleSheet(
                f"QFrame {{ background-color: {INPUT_BG}; border: 1px solid {INPUT_BORDER}; border-radius: {WIDGET_RADIUS}; }}")
            self.current_input_container.setStyleSheet(
                f"QFrame {{ background-color: {INPUT_BG}; border: 1px solid {INPUT_BORDER}; border-radius: {WIDGET_RADIUS}; }}")
        elif ui_mode == "CC":
            self.voltage_set_label.setText("Lim")
            self.current_set_label.setText("Set")
            self.voltage_set_input.setEnabled(True)
            self.limit_current_value.setEnabled(True)
            self.voltage_input_container.setStyleSheet(
                f"QFrame {{ background-color: {INPUT_BG}; border: 1px solid {INPUT_BORDER}; border-radius: {WIDGET_RADIUS}; }}")
            self.current_input_container.setStyleSheet(
                f"QFrame {{ background-color: {INPUT_BG}; border: 1px solid {INPUT_BORDER}; border-radius: {WIDGET_RADIUS}; }}")
        else:
            self.voltage_set_label.setText("---")
            self.current_set_label.setText("---")
            self.voltage_set_input.setEnabled(False)
            self.limit_current_value.setEnabled(False)
            self.voltage_input_container.setStyleSheet(
                f"QFrame {{ background-color: #070F28; border: 1px solid #131D3A; border-radius: {WIDGET_RADIUS}; }}")
            self.current_input_container.setStyleSheet(
                f"QFrame {{ background-color: #070F28; border: 1px solid #131D3A; border-radius: {WIDGET_RADIUS}; }}")

    def _on_mode_button_clicked(self, clicked_button):
        for btn in self.mode_buttons:
            btn.setChecked(btn is clicked_button)
        self._apply_mode_button_styles()

        ui_mode = self._get_current_mode_text()
        self._update_labels_for_mode(ui_mode)

        dev = self.devices[self.current_device]
        if dev["is_connected"] and dev["n6705c"]:
            try:
                inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
                with self._state_poller.writing():
                    dev["n6705c"].set_mode(self.current_channel, inst_mode)
                logger.info("[%s] Channel %d mode set to: %s", self.current_device, self.current_channel, inst_mode)
                self._start_channel_sync()
            except Exception as e:
                logger.error("Failed to set mode: %s", e)

    def _on_output_toggle_clicked(self, checked):
        dev = self.devices[self.current_device]
        if dev["is_connected"] and dev["n6705c"]:
            try:
                with self._state_poller.writing():
                    if checked:
                        dev["n6705c"].channel_on(self.current_channel)
                    else:
                        dev["n6705c"].channel_off(self.current_channel)
            except Exception as e:
                logger.error("Toggle failed: %s", e)
        self._update_output_visual_state()

    def _on_voltage_input_enter(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        try:
            value = float(self.voltage_set_input.text())
            ui_mode = self._get_current_mode_text()
            with self._state_poller.writing():
                if ui_mode == "PS2Q":
                    dev["n6705c"].set_voltage(self.current_channel, value)
                elif ui_mode == "CC":
                    dev["n6705c"].set_voltage_limit(self.current_channel, value)
        except Exception as e:
            logger.error("Voltage set failed: %s", e)
        self.voltage_set_input.selectAll()

    def _on_current_input_enter(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        try:
            value = float(self.limit_current_value.text())
            ui_mode = self._get_current_mode_text()
            with self._state_poller.writing():
                if ui_mode == "PS2Q":
                    dev["n6705c"].set_current_limit(self.current_channel, value)
                elif ui_mode == "CC":
                    value = -abs(value)
                    self.limit_current_value.setText(f"{value:.4f}")
                    dev["n6705c"].set_current(self.current_channel, value)
        except Exception as e:
            logger.error("Current set failed: %s", e)
        self.limit_current_value.selectAll()

    def _on_measure_clicked(self):
        self._start_channel_sync()

    def _on_set_clicked(self):
        dev = self.devices[self.current_device]
        if not dev["is_connected"] or not dev["n6705c"]:
            return
        try:
            n6705c = dev["n6705c"]
            ch = self.current_channel
            ui_mode = self._get_current_mode_text()
            inst_mode = self._map_ui_mode_to_instrument_mode(ui_mode)
            with self._state_poller.writing():
                n6705c.set_mode(ch, inst_mode)

                if ui_mode == "PS2Q":
                    n6705c.set_voltage(ch, float(self.voltage_set_input.text()))
                    n6705c.set_current_limit(ch, float(self.limit_current_value.text()))
                elif ui_mode == "CC":
                    n6705c.set_voltage_limit(ch, float(self.voltage_set_input.text()))
                    cur = -abs(float(self.limit_current_value.text()))
                    self.limit_current_value.setText(f"{cur:.4f}")
                    n6705c.set_current(ch, cur)

            self._dirty_voltage = False
            self._dirty_current = False
            self._update_set_button_dirty_state()
            logger.info("[%s] Channel %d settings applied", self.current_device, ch)
        except Exception as e:
            logger.error("Set failed: %s", e)

    def update_channel_values(self, dev_label, channel_num, voltage, current, limit_current=None):
        if dev_label == self.current_device and channel_num == self.current_channel:
            self.voltage_value.setText(f"{voltage:.4f}")
            self.current_value.setText(f"{current:.4f}")
            if limit_current is not None:
                self.limit_current_value.setText(f"{limit_current:.4f}")

    def get_channel_settings(self, channel_num):
        if 1 <= channel_num <= 4 and self.channels:
            channel = self.channels[0]
            return {
                'enabled': channel['toggle'].isChecked(),
                'voltage_set': float(channel['voltage_set_input'].text()),
                'current_set': float(channel['current_value'].text()),
                'current_limit': float(channel['limit_current_value'].text())
            }
        return None

    def get_channel_toggle(self, channel_num):
        if 1 <= channel_num <= 4 and self.channels:
            return self.channels[0]['toggle']
        return None

    def set_all_channels_enabled(self, enabled):
        for channel in self.channels:
            channel['toggle'].setChecked(enabled)

    def _on_search(self, label):
        if label in self._search_threads and self._search_threads[label].isRunning():
            return
        logger.debug("N6705C search started: label=%s", label)
        w = self.conn_widgets[label]
        w["status"].setText("Searching...")
        w["status"].setStyleSheet("color: #ff9800; font-weight:bold;")
        w["search_btn"].setEnabled(False)
        w["search_btn"].start_spinning()

        if DEBUG_MOCK:
            QTimer.singleShot(600, lambda: self._on_search_finished(label, ["MOCK::N6705C"]))
            return

        thread = _SearchThread(label, self)
        thread.search_result.connect(self._on_search_finished)
        thread.finished.connect(lambda: self._search_threads.pop(label, None))
        self._search_threads[label] = thread
        thread.start()

    def _on_search_finished(self, label, found):
        logger.debug("N6705C search finished: label=%s, found=%s", label, found)
        w = self.conn_widgets[label]
        w["combo"].clear()
        if found:
            for d in found:
                w["combo"].addItem(d)
            w["status"].setText(f"Found {len(found)} N6705C")
            w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
        else:
            w["combo"].addItem("No N6705C found")
            w["status"].setText("No N6705C found")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
        w["search_btn"].stop_spinning()
        w["search_btn"].setEnabled(True)

    def _on_toggle_connection(self, label):
        if self.devices[label]["is_connected"]:
            self._disconnect(label)
        else:
            self._connect(label)

    def _connect(self, label):
        logger.debug("N6705C connecting: label=%s", label)
        w = self.conn_widgets[label]
        w["status"].setText("Connecting...")
        w["status"].setStyleSheet("color: #ff9800; font-weight:bold;")
        w["connect_btn"].setEnabled(False)

        if self._instrument_manager:
            from core.instruments import InstrumentSpec
            address = w["combo"].currentText()
            self._instrument_manager.connect_async(InstrumentSpec(
                instrument_type="n6705c",
                role="power_analyzer",
                connection_kind="visa",
                slot=label,
                resource=address,
            ))
            return

        try:
            address = w["combo"].currentText()
            if DEBUG_MOCK:
                n6705c = MockN6705C()
                idn_match = True
                serial = "MOCK-" + label
            else:
                n6705c = N6705C(address)
                idn = n6705c.instr.query("*IDN?")
                idn_match = "N6705C" in idn
                idn_parts = idn.strip().split(",") if idn_match else []
                serial = idn_parts[2].strip() if len(idn_parts) >= 3 else ""

            if idn_match:
                self.devices[label]["n6705c"] = n6705c
                self.devices[label]["is_connected"] = True

                if self._top:
                    connect_fn = getattr(self._top, f"connect_{label.lower()}", None)
                    if connect_fn:
                        connect_fn(address, n6705c_instance=n6705c, serial=serial)

                w["status"].setText("\u25cf Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
                update_connect_button_state(w["connect_btn"], connected=True)
                self._update_ui_connection_state(label, True)
                self._rebuild_dynamic_sections()
                self.connection_status_changed.emit(True)

                if label == self.current_device:
                    self._start_channel_sync()
            else:
                w["status"].setText("Device mismatch")
                w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
        except Exception as e:
            w["status"].setText("Connection failed")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            logger.error("[%s] Connect error: %s", label, e)
        finally:
            w["connect_btn"].setEnabled(True)

    def _disconnect(self, label):
        logger.debug("N6705C disconnecting: label=%s", label)
        w = self.conn_widgets[label]
        try:
            if self._instrument_manager:
                session_id = f"n6705c:{label}"
                self._instrument_manager.disconnect_async(session_id)
                return
            elif self._top:
                disconnect_fn = getattr(self._top, f"disconnect_{label.lower()}", None)
                if disconnect_fn:
                    disconnect_fn()
            else:
                n6705c = self.devices[label]["n6705c"]
                if n6705c:
                    n6705c.disconnect()

            self.devices[label]["n6705c"] = None
            self.devices[label]["is_connected"] = False

            w["status"].setText("\u25cf Disconnected")
            w["status"].setStyleSheet("color: #8ea6cf; font-weight:bold;")
            update_connect_button_state(w["connect_btn"], connected=False)
            self._update_ui_connection_state(label, False)
            self._rebuild_dynamic_sections()
            self.connection_status_changed.emit(False)
        except Exception as e:
            w["status"].setText("Disconnect failed")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            logger.error("[%s] Disconnect error: %s", label, e)

    def _update_ui_connection_state(self, label, connected):
        any_connected = any(d["is_connected"] for d in self.devices.values())

        active_dev_connected = self.devices[self.current_device]["is_connected"]

        for btn in self.channel_tab_buttons:
            btn.setEnabled(any_connected)

        self.setting_frame.setEnabled(active_dev_connected)

        disabled_border = DISABLED_BORDER
        disabled_bg = DISABLED_BG

        if not active_dev_connected:
            self.setting_frame.setStyleSheet(f"""
                QFrame#SettingContentFrame {{
                    background-color: {disabled_bg};
                    border: 1px solid {disabled_border};
                    border-top: none;
                    border-bottom-left-radius: {CONTAINER_RADIUS};
                    border-bottom-right-radius: {CONTAINER_RADIUS};
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                }}
            """)
            self.channel_interaction_frame.setStyleSheet("""
                QFrame#ChannelInteractionFrame {
                    background-color: transparent;
                    border: none;
                }
            """)
            if hasattr(self, '_tab_bar'):
                self._tab_bar.set_border_color(disabled_border)
        else:
            theme = CHANNEL_THEMES[self.current_channel]
            border_color = theme['accent_border']
            self.setting_frame.setStyleSheet(f"""
                QFrame#SettingContentFrame {{
                    background-color: {CONTENT_BG};
                    border: 1px solid {border_color};
                    border-top: none;
                    border-bottom-left-radius: {CONTAINER_RADIUS};
                    border-bottom-right-radius: {CONTAINER_RADIUS};
                    border-top-left-radius: 0px;
                    border-top-right-radius: 0px;
                }}
            """)
            self.channel_interaction_frame.setStyleSheet("""
                QFrame#ChannelInteractionFrame {
                    background-color: transparent;
                    border: none;
                }
            """)
            if hasattr(self, '_tab_bar'):
                self._tab_bar.set_border_color(border_color)

        self._refresh_channel_tab_styles()

        for btn in self.mode_buttons:
            btn.setEnabled(active_dev_connected)
        self.output_toggle.setEnabled(active_dev_connected)
        self.measure_btn.setEnabled(active_dev_connected)
        self.set_btn.setEnabled(active_dev_connected)
        self.voltage_set_input.setEnabled(active_dev_connected)
        self.limit_current_value.setEnabled(active_dev_connected)
        self.voltage_value.setEnabled(active_dev_connected)
        self.current_value.setEnabled(active_dev_connected)

        if hasattr(self, 'batch_tools_panel'):
            self.batch_content.setEnabled(any_connected)
            self.batch_toggle_btn.setEnabled(any_connected)
            if any_connected:
                self.batch_content.setStyleSheet(f"""
                    QFrame {{
                        background-color: {PANEL_BG};
                        border: 1px solid {PANEL_BORDER};
                        border-top: none;
                        border-bottom-left-radius: {CONTAINER_RADIUS};
                        border-bottom-right-radius: {CONTAINER_RADIUS};
                    }}
                """)
            else:
                self.batch_content.setStyleSheet(f"""
                    QFrame {{
                        background-color: {DISABLED_BG};
                        border: 1px solid {DISABLED_BORDER};
                        border-top: none;
                        border-bottom-left-radius: {CONTAINER_RADIUS};
                        border-bottom-right-radius: {CONTAINER_RADIUS};
                    }}
                """)

        if hasattr(self, 'consumption_test_panel'):
            self.ct_content.setEnabled(any_connected)
            self.ct_toggle_btn.setEnabled(any_connected)
            if any_connected:
                self.ct_content.setStyleSheet(f"""
                    QFrame {{
                        background-color: {PANEL_BG};
                        border: 1px solid {PANEL_BORDER};
                        border-top: none;
                        border-bottom-left-radius: {CONTAINER_RADIUS};
                        border-bottom-right-radius: {CONTAINER_RADIUS};
                    }}
                """)
            else:
                self.ct_content.setStyleSheet(f"""
                    QFrame {{
                        background-color: {DISABLED_BG};
                        border: 1px solid {DISABLED_BORDER};
                        border-top: none;
                        border-bottom-left-radius: {CONTAINER_RADIUS};
                        border-bottom-right-radius: {CONTAINER_RADIUS};
                    }}
                """)

if __name__ == "__main__":
    from ui.standalone import resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = N6705CAnalyserUI()
    win.setWindowTitle("N6705C DC Power Analyzer")
    resize_and_center_window(win)
    win.show()

    sys.exit(app.exec())
