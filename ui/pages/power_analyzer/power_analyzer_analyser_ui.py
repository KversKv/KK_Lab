#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from resource_path import get_resource_base

sys.path.append(get_resource_base())

from ui.widgets.button import update_connect_button_state
from ui.widgets.config_memory import ConfigMemory
from ui.widgets.instrument_state_poller import InstrumentStatePoller
from ui.modules.n6705c_module_frame import build_n6705c_inline_row
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QFrame, QApplication, QMessageBox, QSpacerItem,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtGui import QFont, QPainter, QColor, QPixmap
from PySide6.QtSvg import QSvgRenderer

from instruments.factory import create_power_analyzer, get_power_analyzer_idn
from debug_config import DEBUG_MOCK
from core.ai.ui_action_registry import UIActionSpec
from log_config import get_logger
from ui.theme import FONT_MONO
from core.n6705c import SearchThread as _SearchThread
from core.instruments.address_presets import get_address_preset
from ui.pages.power_analyzer.widgets import (
    ChannelTabBar, SlideToggle, _ZAP_ICON_PATH,
    channel_theme_for_instrument,
    CONTENT_BG, ROOT_BG, PANEL_BG, PANEL_BORDER,
    INPUT_BG, INPUT_BORDER,
    DISABLED_BG, DISABLED_BORDER, DISABLED_TEXT,
    DISABLED_BTN_BG, DISABLED_BTN_BORDER,
    INACTIVE_TAB_BG, INACTIVE_TAB_HOVER_BG,
    VALUE_OFF_COLOR, MODE_INACTIVE_TEXT,
    WIDGET_RADIUS, CONTAINER_RADIUS,
)
from ui.pages.power_analyzer.analyser_view_setting import SettingViewMixin
from ui.pages.power_analyzer.analyser_view_batch import BatchViewMixin
from ui.pages.power_analyzer.analyser_view_consumption import ConsumptionViewMixin
from ui.pages.power_analyzer.analyser_view_arb import ArbViewMixin

logger = get_logger(__name__)


class _ConnectWorker(QObject):
    success = Signal(object, str, str)
    error = Signal(str)
    finished = Signal()

    def __init__(self, resource):
        super().__init__()
        self._resource = resource

    def run(self):
        instance = None
        try:
            instance = create_power_analyzer(self._resource, analyzer_type="auto")
            idn = get_power_analyzer_idn(instance)
            self.success.emit(instance, idn, self._resource)
        except Exception as exc:
            if instance is not None:
                try:
                    instance.disconnect()
                except Exception:
                    logger.debug("Analyser connect cleanup failed", exc_info=True)
            self.error.emit(str(exc))
        finally:
            self.finished.emit()


class N6705CAnalyserUI(QWidget, SettingViewMixin, BatchViewMixin, ConsumptionViewMixin, ArbViewMixin):
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
        self._polling_enabled = False
        self._connect_threads = {}
        self._connect_workers = {}

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

        # 上次配置自动记忆（仅回填控件值，不触发仪器连接）；
        # Batch 矩阵 / Consumption 通道卡随单双机模式动态重建，
        # 其绑定键登记在 _dynamic_cfg_keys，重建后由 _rebind_dynamic_config_memory 重绑回填。
        self._config_memory = ConfigMemory("n6705c/analyser", self)
        self._dynamic_cfg_keys = []
        self._bind_config_memory()
        self._config_memory.restore()
        self._apply_dynamic_channel_constraints()
        self._update_ui_connection_state(
            self.current_device,
            self.devices[self.current_device]["is_connected"],
        )
        self._refresh_current_channel_once()

    def _bind_config_memory(self):
        """绑定静态区（Setting 视图、Consumption 参数）并首次绑定动态区。"""
        cm = self._config_memory
        cm.bind("setting_voltage_set", self.voltage_set_input)
        cm.bind("setting_current_limit", self.limit_current_value)
        cm.bind("consumption_test_time_s", self.ct_test_time_input)
        cm.bind("consumption_sample_period_us", self.ct_sample_period_input)
        self._bind_dynamic_config_memory()

    def _bind_dynamic_config_memory(self):
        """绑定 Batch 电压/电流矩阵与 Consumption 通道勾选（控件由重建产生）。"""
        for dev_label, inputs in self.batch_voltage_inputs.items():
            for idx, inp in enumerate(inputs, start=1):
                self._bind_dynamic(f"batch_{dev_label.lower()}_ch{idx}_voltage", inp)
        for dev_label, inputs in self.batch_current_inputs.items():
            for idx, inp in enumerate(inputs, start=1):
                self._bind_dynamic(f"batch_{dev_label.lower()}_ch{idx}_current", inp)
        for (dev_label, ch), card in self.ct_channel_cards.items():
            self._bind_dynamic(f"consumption_{dev_label.lower()}_ch{ch}_enable", card["checkbox"])

    def _bind_dynamic(self, key, widget):
        self._config_memory.bind(key, widget)
        self._dynamic_cfg_keys.append(key)

    def _rebind_dynamic_config_memory(self):
        """动态控件重建后调用：剔除指向旧控件的绑定，重新 bind 并回填上次值。"""
        cm = getattr(self, "_config_memory", None)
        if cm is None:
            return
        stale = set(self._dynamic_cfg_keys)
        cm._bindings = [b for b in cm._bindings if b[0] not in stale]
        self._dynamic_cfg_keys = []
        self._bind_dynamic_config_memory()
        cm.restore()

    def _register_ai_ui_actions(self):
        """§5b.5：登记本页无专用接口的按钮（Auto Set 系列）为 AI 可触发的具名 UI 动作。

        handler 直接复用按钮原 clicked.connect 的槽（_on_batch_auto_set 等），
        行为与人点按钮完全一致；enabled_when 校验至少一台电源已连接，
        不满足时 list_ui_actions 不返回、ui_invoke 明示不可用（不盲点）。
        """
        registry = self._ui_action_registry
        if registry is None:
            return

        def _any_connected() -> bool:
            return any(
                self._supported_channels_for_device(label)
                for label in self._connected_device_labels()
            )

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
                    "设电流限值并打开通道输出。需至少一台电源已连接并选中通道。"
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
                    "设电流限值并打开通道输出。需至少一台电源已连接并选中通道。"
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
                w["status"].setText(
                    f"\u25cf Connected: {snap.model or 'Power Supply'}"
                )
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
            self._refresh_current_channel_once()
        else:
            self._state_poller.pause()
        self._update_polling_switch_state()

    def _connected_device_labels(self):
        return [label for label, dev in self.devices.items() if dev["is_connected"]]

    def _is_dual_mode(self):
        return len(self._connected_device_labels()) >= 2

    def _channels_for_device(self, label):
        instance = self.devices.get(label, {}).get("n6705c")
        channels = getattr(instance, "VALID_CHANNELS", (1, 2, 3, 4))
        return tuple(int(ch) for ch in channels)

    def _channel_module_model(self, label, channel):
        instance = self.devices.get(label, {}).get("n6705c")
        models = getattr(instance, "channel_module_models", {})
        return str(models.get(int(channel), "") or "").strip().upper()

    def _channel_theme(self, label, channel):
        instance = self.devices.get(label, {}).get("n6705c")
        return channel_theme_for_instrument(instance, channel)

    def _current_channel_theme(self):
        return self._channel_theme(self.current_device, self.current_channel)

    def _is_channel_supported(self, label, channel):
        device = self.devices.get(label, {})
        instance = device.get("n6705c")
        if not device.get("is_connected") or instance is None:
            return False
        checker = getattr(instance, "is_channel_supported", None)
        return bool(callable(checker) and checker(int(channel)))

    def _supported_channels_for_device(self, label):
        return tuple(
            ch for ch in self._channels_for_device(label)
            if self._is_channel_supported(label, ch)
        )

    def _channel_module_tooltip(self, label, channel):
        model = self._channel_module_model(label, channel)
        if self._is_channel_supported(label, channel):
            return f"Supported module: {model}"
        return f"Unsupported module: {model or 'EMPTY'}"

    def _dynamic_layout_signature(self):
        return (
            self._is_dual_mode(),
            tuple(
                (
                    label,
                    self._channels_for_device(label),
                    self._channel_theme(label, 1)["accent"],
                    tuple(
                        self._channel_module_model(label, ch)
                        for ch in self._channels_for_device(label)
                    ),
                )
                for label in ("A", "B")
            ),
        )

    def _rebuild_dynamic_sections(self):
        signature = self._dynamic_layout_signature()
        if signature == self._prev_dual_mode:
            self._apply_dynamic_channel_constraints()
            self._update_ui_connection_state(
                self.current_device,
                self.devices[self.current_device]["is_connected"],
            )
            return
        self._prev_dual_mode = signature

        connected = self._connected_device_labels()
        if connected and (
            self.current_device not in connected
            or not self._is_channel_supported(self.current_device, self.current_channel)
        ):
            selected = next(
                (
                    (label, ch)
                    for label in connected
                    for ch in self._supported_channels_for_device(label)
                ),
                None,
            )
            if selected is not None:
                self.current_device, self.current_channel = selected
            elif self.current_device not in connected:
                self.current_device = connected[0]
        channels = self._channels_for_device(self.current_device)
        if channels and self.current_channel not in channels:
            self.current_channel = channels[0]

        self._build_channel_tab_buttons()
        self._build_batch_columns()
        self._build_ct_cards()
        self._build_arb_tab_buttons()
        # Batch/Consumption 控件已重建，配置记忆需重绑新控件并回填
        self._rebind_dynamic_config_memory()
        self._apply_dynamic_channel_constraints()
        self._apply_channel_theme(self.current_device, self.current_channel)
        self._update_ui_connection_state(
            self.current_device,
            self.devices[self.current_device]["is_connected"],
        )

    def _apply_dynamic_channel_constraints(self):
        for dev_label, ch, button in getattr(self, "batch_channel_buttons", []):
            supported = self._is_channel_supported(dev_label, ch)
            button.setEnabled(supported)
            button.setVisible(supported)
            button.setToolTip(self._channel_module_tooltip(dev_label, ch))
            channels = self._channels_for_device(dev_label)
            grid = button.parentWidget().layout()
            if grid is not None and ch in channels:
                grid.setColumnStretch(channels.index(ch) + 1, int(supported))
            if not supported:
                button.setChecked(False)
        for input_group in ("batch_voltage_inputs", "batch_current_inputs"):
            for dev_label, inputs in getattr(self, input_group, {}).items():
                channels = self._channels_for_device(dev_label)
                for idx, edit in enumerate(inputs):
                    if idx < len(channels):
                        supported = self._is_channel_supported(dev_label, channels[idx])
                        edit.setEnabled(supported)
                        edit.setVisible(supported)
                        edit.setToolTip(self._channel_module_tooltip(dev_label, channels[idx]))
        for (dev_label, ch), card_data in getattr(self, "ct_channel_cards", {}).items():
            supported = self._is_channel_supported(dev_label, ch)
            card_data["card"].setEnabled(supported)
            card_data["card"].setVisible(supported)
            checkbox = card_data["checkbox"]
            checkbox.setEnabled(supported)
            checkbox.setToolTip(self._channel_module_tooltip(dev_label, ch))
            if not supported:
                checkbox.setChecked(False)
        for btn in getattr(self, "arb_tab_buttons", []):
            dev_label = btn.property("device_label")
            ch = btn.property("channel")
            if not dev_label or ch is None:
                continue
            supported = self._is_channel_supported(dev_label, int(ch))
            btn.setEnabled(supported)
            btn.setVisible(supported)
            btn.setToolTip(self._channel_module_tooltip(dev_label, int(ch)))
        if hasattr(self, "arb_toggle_btn"):
            self._arb_refresh_action_state()
        # 同步组覆盖态（从通道输入禁用 + 高亮）须最后施加，避免被上面的 supported 复位
        self._apply_batch_sync_ui()

    def _sync_from_top(self):
        if not self._top:
            return
        for label, attr_suffix in [("A", "a"), ("B", "b")]:
            n6705c = getattr(self._top, f"n6705c_{attr_suffix}", None)
            is_conn = getattr(self._top, f"is_connected_{attr_suffix}", False)
            visa_res = getattr(self._top, f"visa_resource_{attr_suffix}", "")
            model = getattr(self._top, f"model_{attr_suffix}", "") or "Power Supply"
            w = self.conn_widgets[label]
            if is_conn and n6705c:
                self.devices[label]["n6705c"] = n6705c
                self.devices[label]["is_connected"] = True
                w["status"].setText(f"\u25cf Connected: {model}")
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
            self._refresh_current_channel_once()
        else:
            self._state_poller.pause()
        self._update_polling_switch_state()

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

    def _refresh_current_channel_once(self):
        if self._is_channel_supported(self.current_device, self.current_channel):
            self._state_poller.refresh_once()

    def _start_channel_sync(self):
        dev = self.devices[self.current_device]
        if (
            not dev["is_connected"]
            or not dev["n6705c"]
            or not self._is_channel_supported(self.current_device, self.current_channel)
            or not self._polling_enabled
        ):
            self._state_poller.pause()
            self._update_polling_switch_state()
            return
        if self.isVisible():
            self._state_poller.resume()
        self._update_polling_switch_state()

    def _set_polling_enabled(self, enabled):
        self._polling_enabled = enabled
        if enabled:
            self._start_channel_sync()
        else:
            self._state_poller.pause()
        self._update_polling_switch_state()

    def _on_polling_toggle_clicked(self, checked):
        self._set_polling_enabled(checked)
        logger.info("Power supply 状态轮询%s", "已启用" if checked else "已暂停")

    def _update_polling_switch_state(self):
        if not hasattr(self, "polling_switch"):
            return
        has_connected = self._is_channel_supported(
            self.current_device, self.current_channel
        )
        switch_checked = self._polling_enabled and has_connected
        if self.polling_switch.isChecked() != switch_checked:
            self.polling_switch.blockSignals(True)
            self.polling_switch.setChecked(switch_checked)
            self.polling_switch.blockSignals(False)
        self.polling_switch.setEnabled(has_connected)

    def _read_channel_snapshot(self):
        device_label = self.current_device
        channel_num = self.current_channel
        dev = self.devices.get(device_label)
        if (
            not dev
            or not dev["is_connected"]
            or not dev["n6705c"]
            or not self._is_channel_supported(device_label, channel_num)
        ):
            return None
        n6705c = dev["n6705c"]
        data = {"device": device_label, "channel": channel_num}
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
            data["voltage_setpoint"] = float(n6705c.get_voltage_setpoint(channel_num))
        except Exception:
            data["voltage_setpoint"] = None
        try:
            data["current_setpoint"] = float(n6705c.get_current_setpoint(channel_num))
        except Exception:
            data["current_setpoint"] = None
        try:
            data["voltage_limit"] = float(n6705c.get_voltage_limit(channel_num))
        except Exception:
            data["voltage_limit"] = None
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

        ui_mode = self._get_current_mode_text()
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
        if voltage is not None and current is not None:
            self.update_channel_values(self.current_device, self.current_channel, voltage, current)

        if ui_mode == "CC":
            voltage_setting = data.get("voltage_limit")
            current_setting = data.get("current_setpoint")
        else:
            voltage_setting = data.get("voltage_setpoint")
            current_setting = data.get("limit_current")

        self.voltage_set_input.blockSignals(True)
        self.limit_current_value.blockSignals(True)
        if voltage_setting is not None:
            self.voltage_set_input.setText(f"{voltage_setting:.4f}")
        if current_setting is not None:
            self.limit_current_value.setText(f"{current_setting:.4f}")
        self.voltage_set_input.blockSignals(False)
        self.limit_current_value.blockSignals(False)

        self._dirty_voltage = False
        self._dirty_current = False
        self._update_set_button_dirty_state()

    def showEvent(self, event):
        super().showEvent(event)
        if self.devices[self.current_device]["is_connected"]:
            self._start_channel_sync()
            self._refresh_current_channel_once()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._state_poller.pause()

    def closeEvent(self, event):
        self._state_poller.stop()
        for thread in list(self._connect_threads.values()):
            if thread.isRunning():
                thread.quit()
                thread.wait()
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
        self._main_layout = QVBoxLayout(self)
        main_layout = self._main_layout
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(12, 12, 12, 12)
        # 区块间固定间距保留引用，紧凑模式下归零以压到 ~600x200
        self._block_spacers = []

        self.top_bar = self._create_top_bar()
        main_layout.addWidget(self.top_bar)
        self._block_spacers.append(QSpacerItem(0, 8))
        main_layout.addItem(self._block_spacers[-1])

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
        self._block_spacers.append(QSpacerItem(0, 8))
        main_layout.addItem(self._block_spacers[-1])

        self.batch_tools_panel = self._create_batch_tools_panel()
        main_layout.addWidget(self.batch_tools_panel)
        self._block_spacers.append(QSpacerItem(0, 8))
        main_layout.addItem(self._block_spacers[-1])

        self.consumption_test_panel = self._create_consumption_test_panel()
        main_layout.addWidget(self.consumption_test_panel)
        self._block_spacers.append(QSpacerItem(0, 8))
        main_layout.addItem(self._block_spacers[-1])

        self.arb_panel = self._create_arb_panel()
        main_layout.addWidget(self.arb_panel)

        main_layout.addStretch()

    def set_compact_mode(self, compact: bool):
        """紧凑（最小）视图：仅显示 Quick Setup 面板，隐藏其余区块。

        由主窗口顶栏按钮触发；进入时若 Quick Setup 处于收起状态则自动展开。
        紧凑态额外隐藏折叠头并归零区块间距 / 收窄页边距，配合主窗口
        压到 ~600x200。
        """
        for widget in (
            self.top_bar,
            self.channel_interaction_frame,
            self.consumption_test_panel,
            self.arb_panel,
        ):
            if widget is not None:
                widget.setVisible(not compact)
        if compact and self.batch_collapsed:
            self._toggle_batch_panel()
        # 紧凑态下面板是唯一内容，折叠无意义，隐藏折叠头省一行高度
        self.batch_toggle_btn.setVisible(not compact)
        for spacer in self._block_spacers:
            spacer.changeSize(0, 0 if compact else 8)
        if compact:
            self._main_layout.setContentsMargins(6, 6, 6, 6)
        else:
            self._main_layout.setContentsMargins(12, 12, 12, 12)
        self._main_layout.invalidate()

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

        title_label = QLabel("Power Control")
        title_label.setStyleSheet("QLabel { color: #ffffff; font-size: 18px; font-weight: 800; }")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        polling_label = QLabel("轮询")
        polling_label.setStyleSheet("QLabel { color: #8ea6cf; font-size: 12px; font-weight: 700; background: transparent; border: none; }")
        header_layout.addWidget(polling_label)

        self.polling_switch = SlideToggle(self)
        self.polling_switch.setFixedSize(52, 22)
        self.polling_switch.setChecked(False)
        self.polling_switch.setToolTip("Poll the active power supply channel; disable to avoid state-read races during page switches")
        self.polling_switch.clicked.connect(self._on_polling_toggle_clicked)
        header_layout.addWidget(self.polling_switch)
        self._update_polling_switch_state()
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

        # 实验室预填地址（resources/instrument_addresses.json，缺失为空串）
        default_addresses = {
            "A": get_address_preset("n6705c", "A"),
            "B": get_address_preset("n6705c", "B"),
        }

        self.conn_widgets = {}
        for label in ["A", "B"]:
            row_layout, widgets = build_n6705c_inline_row(
                label, parent=self, default_resource=default_addresses[label]
            )
            widgets["combo"].setEditable(True)
            widgets["combo"].lineEdit().setPlaceholderText("Select or enter a VISA address")
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
                for ch in self._channels_for_device(dev_label):
                    btn = QPushButton(f"\u25cf {dev_label}-CH{ch}")
                    btn.setCheckable(True)
                    btn.setProperty("device_label", dev_label)
                    btn.setProperty("channel", ch)
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
            single_label = self._get_single_device_label()
            for ch in self._channels_for_device(single_label):
                btn = QPushButton(f"\u25cf CH{ch}")
                btn.setCheckable(True)
                btn.setProperty("device_label", single_label)
                btn.setProperty("channel", ch)
                btn.setMinimumSize(90, 36)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(
                    lambda checked=False, d=single_label, c=ch: self._switch_channel(d, c)
                )
                self.channel_tab_buttons.append(btn)
                self._channel_tabs_layout.addWidget(btn)

        self._channel_tabs_layout.addStretch()

        for btn in self.channel_tab_buttons:
            dev_label = btn.property("device_label")
            ch = int(btn.property("channel"))
            btn.setEnabled(self._is_channel_supported(dev_label, ch))
            btn.setToolTip(self._channel_module_tooltip(dev_label, ch))

        for btn in self.channel_tab_buttons:
            dev_label = btn.property("device_label")
            ch = int(btn.property("channel"))
            btn.setChecked(
                dev_label == self.current_device
                and ch == self.current_channel
                and self._is_channel_supported(dev_label, ch)
            )
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
        theme = self._current_channel_theme()
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

    def _build_channel_tab_style(self, dev_label, ch, checked=False, bar_border_color=None):
        theme = self._channel_theme(dev_label, ch)
        border_color = theme['accent_border'] if checked else "#14305e"
        if bar_border_color is None:
            bar_border_color = self._get_current_border_color()
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
                border-bottom: 1px solid {bar_border_color};
                {radius_str}
                padding: {inactive_pad}; font-size: {font_size}; font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {INACTIVE_TAB_HOVER_BG}; color: #ffffff;
                border: 1px solid {theme['accent_border']};
                border-bottom: 1px solid {bar_border_color};
            }}
            {disabled_part}
            """

    def _get_current_border_color(self):
        theme = self._current_channel_theme()
        return theme['accent_border']

    def _build_mode_button_style(self, active=False):
        theme = self._current_channel_theme()
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
                for ch in self._channels_for_device(dev_label):
                    if idx < total:
                        is_active = (
                            dev_label == self.current_device
                            and ch == self.current_channel
                            and self._is_channel_supported(dev_label, ch)
                        )
                        self.channel_tab_buttons[idx].setStyleSheet(
                            self._build_channel_tab_style(dev_label, ch, is_active)
                        )
                        self.channel_tab_buttons[idx].setChecked(is_active)
                        if is_active:
                            active_btn = self.channel_tab_buttons[idx]
                        idx += 1
        else:
            single_label = self._get_single_device_label()
            for ch in self._channels_for_device(single_label):
                if idx < total:
                    is_active = (
                        ch == self.current_channel
                        and self._is_channel_supported(single_label, ch)
                    )
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
        theme = self._channel_theme(dev_label, channel_num)
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
            theme = self._current_channel_theme()
            self.set_btn.setStyleSheet(self._dirty_set_button_style(theme['accent']))
        else:
            theme = self._current_channel_theme()
            self.set_btn.setStyleSheet(self._channel_action_button_style(theme['accent'], theme['accent_hover']))

    def _update_output_visual_state(self):
        is_on = self.output_toggle.isChecked()
        theme = self._current_channel_theme()
        accent = theme['accent']

        value_color = accent if is_on else VALUE_OFF_COLOR

        self.voltage_value.setStyleSheet(f"""
            QLineEdit {{ font-family: {FONT_MONO}; font-size: 26px; font-weight: bold; color: {value_color}; background: transparent; border: none; letter-spacing: 1px; }}
        """)
        self.current_value.setStyleSheet(f"""
            QLineEdit {{ font-family: {FONT_MONO}; font-size: 26px; font-weight: bold; color: {value_color}; background-color: transparent; border: none; letter-spacing: 1px; }}
        """)

    def _switch_channel(self, dev_label, ch):
        if not self._is_channel_supported(dev_label, ch):
            return
        logger.debug("Switch channel: dev=%s, CH%s", dev_label, ch)
        self.current_device = dev_label
        self.current_channel = ch
        self._dirty_voltage = False
        self._dirty_current = False
        self._apply_channel_theme(dev_label, ch)
        self._start_channel_sync()
        self._state_poller.refresh_once()

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
            abs_current = abs(current)
            if abs_current < 1e-6:
                current_scale, current_unit = 1e9, "nA"
            elif abs_current < 1e-3:
                current_scale, current_unit = 1e6, "µA"
            elif abs_current < 1:
                current_scale, current_unit = 1e3, "mA"
            else:
                current_scale, current_unit = 1, "A"
            self.current_value.setText(f"{current * current_scale:.4f}")
            self.current_value_label.setText(f"CURRENT ({current_unit})")
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
            w["status"].setText(f"Found {len(found)} instrument(s)")
            w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
        else:
            w["combo"].addItem("No power supply found")
            w["status"].setText("No power supply found")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
        w["search_btn"].stop_spinning()
        w["search_btn"].setEnabled(True)
        if not DEBUG_MOCK:
            self._maybe_show_scope_hint()

    def _maybe_show_scope_hint(self):
        """搜索完成后提示搜索作用域（每次运行仅弹一次，未配置跨网段时才弹）。"""
        if getattr(self, "_scope_hint_shown", False):
            return
        from core.n6705c.search_worker import discovery_scope_hint
        hint = discovery_scope_hint()
        if not hint:
            return
        self._scope_hint_shown = True
        QMessageBox.information(self, "搜索范围提示", hint)

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

        address = w["combo"].currentText()
        thread = QThread(self)
        worker = _ConnectWorker(address)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.success.connect(
            lambda instance, idn, resource, lb=label: self._on_local_connect_success(
                lb, instance, idn, resource
            )
        )
        worker.error.connect(
            lambda message, lb=label: self._on_local_connect_error(lb, message)
        )
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda lb=label: self._on_local_connect_finished(lb))
        self._connect_threads[label] = thread
        self._connect_workers[label] = worker
        thread.start()

    def _on_local_connect_success(self, label, n6705c, idn, address):
        w = self.conn_widgets[label]
        idn_parts = idn.split(",")
        serial = idn_parts[2].strip() if len(idn_parts) >= 3 else ""
        model = idn_parts[1].strip() if len(idn_parts) >= 2 else "Power Supply"

        self.devices[label]["n6705c"] = n6705c
        self.devices[label]["is_connected"] = True

        if self._top:
            connect_fn = getattr(self._top, f"connect_{label.lower()}", None)
            if connect_fn:
                connect_fn(address, n6705c_instance=n6705c, serial=serial)

        w["status"].setText(f"\u25cf Connected: {model}")
        w["status"].setStyleSheet("color: #00a859; font-weight:bold;")
        update_connect_button_state(w["connect_btn"], connected=True)
        w["connect_btn"].setEnabled(True)
        self._update_ui_connection_state(label, True)
        self._rebuild_dynamic_sections()
        self.connection_status_changed.emit(True)

        if label == self.current_device:
            self._start_channel_sync()
            self._refresh_current_channel_once()
        else:
            self._update_polling_switch_state()

    def _on_local_connect_error(self, label, message):
        w = self.conn_widgets[label]
        w["status"].setText("Connection failed")
        w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
        w["connect_btn"].setEnabled(True)
        logger.error("[%s] Connect error: %s", label, message)

    def _on_local_connect_finished(self, label):
        self._connect_workers.pop(label, None)
        self._connect_threads.pop(label, None)

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
            self._update_polling_switch_state()
            self.connection_status_changed.emit(False)
        except Exception as e:
            w["status"].setText("Disconnect failed")
            w["status"].setStyleSheet("color: #e53935; font-weight:bold;")
            logger.error("[%s] Disconnect error: %s", label, e)

    def _update_ui_connection_state(self, label, connected):
        any_connected = any(
            self._supported_channels_for_device(device_label)
            for device_label in self._connected_device_labels()
        )

        active_channel_enabled = self._is_channel_supported(
            self.current_device, self.current_channel
        )

        for btn in self.channel_tab_buttons:
            dev_label = btn.property("device_label")
            ch = btn.property("channel")
            supported = bool(
                dev_label and ch is not None
                and self._is_channel_supported(dev_label, int(ch))
            )
            btn.setEnabled(supported)
            btn.setVisible(supported)
            if dev_label and ch is not None:
                btn.setToolTip(self._channel_module_tooltip(dev_label, int(ch)))

        if self._channel_tab_separator is not None:
            self._channel_tab_separator.setVisible(all(
                any(self._is_channel_supported(label, ch)
                    for ch in self._channels_for_device(label))
                for label in ("A", "B")
            ))

        self.setting_frame.setEnabled(active_channel_enabled)
        self.setting_frame.setVisible(active_channel_enabled)

        disabled_border = DISABLED_BORDER
        disabled_bg = DISABLED_BG

        if not active_channel_enabled:
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
            theme = self._current_channel_theme()
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
            btn.setEnabled(active_channel_enabled)
        self.output_toggle.setEnabled(active_channel_enabled)
        self.measure_btn.setEnabled(active_channel_enabled)
        self.set_btn.setEnabled(active_channel_enabled)
        self.voltage_set_input.setEnabled(active_channel_enabled)
        self.limit_current_value.setEnabled(active_channel_enabled)
        self.voltage_value.setEnabled(active_channel_enabled)
        self.current_value.setEnabled(active_channel_enabled)

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
            self.ct_start_btn.setEnabled(any_connected and not self.is_testing)
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
        if hasattr(self, 'arb_toggle_btn'):
            self.arb_content.setEnabled(any_connected)
            self.arb_toggle_btn.setEnabled(any_connected)
            self._arb_refresh_action_state()
            if any_connected:
                self.arb_content.setStyleSheet(f"""
                    QFrame {{
                        background-color: {PANEL_BG};
                        border: 1px solid {PANEL_BORDER};
                        border-top: none;
                        border-bottom-left-radius: {CONTAINER_RADIUS};
                        border-bottom-right-radius: {CONTAINER_RADIUS};
                    }}
                """)
            else:
                self.arb_content.setStyleSheet(f"""
                    QFrame {{
                        background-color: {DISABLED_BG};
                        border: 1px solid {DISABLED_BORDER};
                        border-top: none;
                        border-bottom-left-radius: {CONTAINER_RADIUS};
                        border-bottom-right-radius: {CONTAINER_RADIUS};
                    }}
                """)

if __name__ == "__main__":
    from ui.standalone import apply_window_icon, resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = N6705CAnalyserUI()
    win.setWindowTitle("Power Control")
    apply_window_icon(win, "n6705c_analyser")
    resize_and_center_window(win)
    win.show()

    sys.exit(app.exec())
