#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test 设备连接与通道管理（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - N6705C 搜索/连接/断开：_on_device_search / _on_device_search_done /
    _on_device_search_error / _on_device_connect_or_disconnect /
    _connect_device / _disconnect_device
  - Top 同步与 manager 信号：_sync_n6705c_dual_from_top / sync_n6705c_from_top /
    _label_from_n6705c_session_id / _on_mixin_manager_connected /
    _on_mixin_manager_connect_failed / _on_mixin_manager_disconnected
  - 通道选项管理：_get_available_channel_options / _connected_device_count /
    _update_available_channels / _apply_preset_channels /
    _clear_all_channel_configs / _update_test_panel_state / _get_checkmark_path

依赖宿主类（ConsumptionTestUI）与其它 Mixin 提供属性与槽。
"""

import os
from resource_path import get_resource_base
from PySide6.QtCore import QThread


class ConsumptionTestViewDeviceMixin:

    def _on_device_search(self, label):
        top = self._n6705c_top
        if top:
            is_conn = getattr(top, f"is_connected_{label.lower()}", False)
            if is_conn:
                return

        from debug_config import DEBUG_MOCK
        w = self._n6705c_conn_widgets[label]
        if DEBUG_MOCK:
            w["combo"].clear()
            w["combo"].addItem(f"DEBUG::MOCK::N6705C::{label}")
            w["status"].setText("● Mock Ready")
            w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[DEBUG] Mock device {label} loaded, skip real VISA scan.")
            return

        w["status"].setText("● Searching")
        w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
        w["search_btn"].setEnabled(False)
        w["connect_btn"].setEnabled(False)
        self.append_log(f"[SYSTEM] Scanning VISA resources for N6705C-{label}...")

        from ui.modules.n6705c_module_frame import _SearchN6705CWorker
        worker = _SearchN6705CWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda devs, lbl=label: self._on_device_search_done(lbl, devs))
        worker.error.connect(lambda err, lbl=label: self._on_device_search_error(lbl, err))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        setattr(self, f"_search_thread_{label}", thread)
        setattr(self, f"_search_worker_{label}", worker)
        thread.start()

    def _on_device_search_done(self, label, devices):
        w = self._n6705c_conn_widgets[label]
        w["combo"].setEnabled(True)
        w["combo"].clear()
        if devices:
            for dev in devices:
                w["combo"].addItem(dev)
            w["status"].setText(f"● Found {len(devices)}")
            w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[SYSTEM] Found {len(devices)} N6705C device(s) for slot {label}.")
        else:
            w["combo"].addItem("No N6705C device found")
            w["combo"].setEnabled(False)
            w["status"].setText("● Not Found")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
        w["search_btn"].setEnabled(True)
        w["connect_btn"].setEnabled(True)

    def _on_device_search_error(self, label, err):
        w = self._n6705c_conn_widgets[label]
        w["status"].setText("● Failed")
        w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
        self.append_log(f"[ERROR] Search failed for N6705C-{label}: {err}")
        w["search_btn"].setEnabled(True)
        w["connect_btn"].setEnabled(True)

    def _on_device_connect_or_disconnect(self, label):
        attr = label.lower()
        is_conn = getattr(self, f"is_connected_{attr}", False)
        if is_conn:
            self._disconnect_device(label)
        else:
            self._connect_device(label)

    def _connect_device(self, label):
        attr = label.lower()
        w = self._n6705c_conn_widgets[label]
        from debug_config import DEBUG_MOCK
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()

        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C
            inst = MockN6705C()
            setattr(self, f"n6705c_{attr}", inst)
            setattr(self, f"is_connected_{attr}", True)
            _update_n6705c_btn_state(w["connect_btn"], connected=True)
            w["search_btn"].setEnabled(False)
            w["status"].setText("● Connected")
            w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[DEBUG] Mock N6705C-{label} connected.")
            visa = w["combo"].currentText()
            self._syncing = True
            try:
                if self._n6705c_top:
                    getattr(self._n6705c_top, f"connect_{attr}")(visa, inst, f"MOCK-{label}")
            finally:
                self._syncing = False
            new_count = self._connected_device_count()
            self._apply_preset_channels(prev_count, new_count)
            self._update_available_channels()
            return

        w["status"].setText("● Connecting")
        w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
        w["connect_btn"].setEnabled(False)
        self.append_log(f"[SYSTEM] Connecting N6705C-{label}...")

        if self._instrument_manager:
            from core.instruments import InstrumentSpec
            visa = w["combo"].currentText()
            self._instrument_manager.connect_async(InstrumentSpec(
                instrument_type="n6705c",
                role="power_analyzer",
                connection_kind="visa",
                slot=label,
                resource=visa,
            ))
            return

        try:
            from instruments.power.keysight.n6705c import N6705C
            visa = w["combo"].currentText()
            inst = N6705C(visa)
            idn = inst.instr.query("*IDN?")
            if "N6705C" in idn:
                setattr(self, f"n6705c_{attr}", inst)
                setattr(self, f"is_connected_{attr}", True)
                _update_n6705c_btn_state(w["connect_btn"], connected=True)
                w["search_btn"].setEnabled(False)
                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
                self.append_log(f"[SYSTEM] N6705C-{label} connected. IDN: {idn.strip()}")
                self._syncing = True
                try:
                    if self._n6705c_top:
                        serial = ""
                        try:
                            serial = idn.strip().split(",")[2].strip()
                        except Exception:
                            pass
                        getattr(self._n6705c_top, f"connect_{attr}")(visa, inst, serial)
                finally:
                    self._syncing = False
                new_count = self._connected_device_count()
                self._apply_preset_channels(prev_count, new_count)
                self._update_available_channels()
            else:
                w["status"].setText("● Mismatch")
                w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
                self.append_log(f"[ERROR] Connected device on {label} is not N6705C.")
        except Exception as e:
            w["status"].setText("● Failed")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[ERROR] Connection failed for N6705C-{label}: {e}")
        finally:
            w["connect_btn"].setEnabled(True)

    def _disconnect_device(self, label):
        attr = label.lower()
        w = self._n6705c_conn_widgets[label]
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()

        try:
            self._syncing = True
            try:
                if self._n6705c_top:
                    getattr(self._n6705c_top, f"disconnect_{attr}")()
                else:
                    inst = getattr(self, f"n6705c_{attr}", None)
                    if inst:
                        if hasattr(inst, 'disconnect'):
                            inst.disconnect()
                        else:
                            if hasattr(inst, 'instr') and inst.instr:
                                inst.instr.close()
                            if hasattr(inst, 'rm') and inst.rm:
                                inst.rm.close()
            finally:
                self._syncing = False
            setattr(self, f"n6705c_{attr}", None)
            setattr(self, f"is_connected_{attr}", False)
            _update_n6705c_btn_state(w["connect_btn"], connected=False)
            w["search_btn"].setEnabled(True)
            w["combo"].setEnabled(True)
            w["status"].setText("● Disconnected")
            w["status"].setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[SYSTEM] N6705C-{label} disconnected.")
            new_count = self._connected_device_count()
            self._apply_preset_channels(prev_count, new_count)
            self._update_available_channels()
        except Exception as e:
            w["status"].setText("● Failed")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[ERROR] Disconnect failed for N6705C-{label}: {e}")

    def _sync_n6705c_dual_from_top(self):
        top = self._n6705c_top
        if not top:
            self._update_test_panel_state()
            return
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()
        for label, attr in [("A", "a"), ("B", "b")]:
            n6705c = getattr(top, f"n6705c_{attr}", None)
            is_conn = getattr(top, f"is_connected_{attr}", False)
            visa_res = getattr(top, f"visa_resource_{attr}", "")
            if label not in self._n6705c_conn_widgets:
                continue
            w = self._n6705c_conn_widgets[label]
            if is_conn and n6705c:
                setattr(self, f"n6705c_{attr}", n6705c)
                setattr(self, f"is_connected_{attr}", True)
                _update_n6705c_btn_state(w["connect_btn"], connected=True)
                w["search_btn"].setEnabled(False)
                if visa_res:
                    w["combo"].clear()
                    w["combo"].addItem(visa_res)
                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            else:
                setattr(self, f"n6705c_{attr}", None)
                setattr(self, f"is_connected_{attr}", False)
                _update_n6705c_btn_state(w["connect_btn"], connected=False)
                w["search_btn"].setEnabled(True)
                w["combo"].setEnabled(True)
                w["status"].setText("● Disconnected")
                w["status"].setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
        self.n6705c = self.n6705c_a
        self.is_connected = self.is_connected_a
        new_count = self._connected_device_count()
        self._apply_preset_channels(prev_count, new_count)
        self._update_available_channels()

    def sync_n6705c_from_top(self):
        if self._syncing:
            return
        self._sync_n6705c_dual_from_top()

    @staticmethod
    def _label_from_n6705c_session_id(session_id):
        # session_id 格式: "n6705c:A" / "n6705c:B"
        if not session_id or ":" not in session_id:
            return None
        prefix, slot = session_id.split(":", 1)
        if prefix != "n6705c" or slot not in ("A", "B"):
            return None
        return slot

    def _on_mixin_manager_connected(self, session_id: str):
        # ConsumptionTestUI 使用 per-label 控件字典(self._n6705c_conn_widgets),
        # 不使用基类的 self.connect_btn / self.search_btn, 故此处覆盖基类实现。
        label = self._label_from_n6705c_session_id(session_id)
        if label is None or label not in self._n6705c_conn_widgets:
            return
        if not self._n6705c_instrument_manager:
            return
        session = self._n6705c_instrument_manager.get_session(session_id)
        if not session or not session.connected:
            return

        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        attr = label.lower()
        prev_count = self._connected_device_count()

        setattr(self, f"n6705c_{attr}", session.instance)
        setattr(self, f"is_connected_{attr}", True)
        w = self._n6705c_conn_widgets[label]
        _update_n6705c_btn_state(w["connect_btn"], connected=True)
        w["connect_btn"].setEnabled(True)
        w["search_btn"].setEnabled(False)
        w["status"].setText("● Connected")
        w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
        self.append_log(f"[SYSTEM] N6705C-{label} connected via manager.")

        # N6705CTop 已通过自身 _on_session_connected 订阅同一 manager 的
        # session_connected 信号完成状态同步; 此处不可再调用 connect_a/connect_b,
        # 否则会触发 attach_external -> 重复 emit session_connected -> 无限递归。
        new_count = self._connected_device_count()
        self._apply_preset_channels(prev_count, new_count)
        self._update_available_channels()
        self.connection_status_changed.emit(True)

    def _on_mixin_manager_connect_failed(self, session_id: str, error: str):
        label = self._label_from_n6705c_session_id(session_id)
        if label is None or label not in self._n6705c_conn_widgets:
            return
        w = self._n6705c_conn_widgets[label]
        w["connect_btn"].setEnabled(True)
        w["status"].setText("● Failed")
        w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
        self.append_log(f"[ERROR] Connection failed for N6705C-{label}: {error}")

    def _on_mixin_manager_disconnected(self, session_id: str):
        label = self._label_from_n6705c_session_id(session_id)
        if label is None or label not in self._n6705c_conn_widgets:
            return

        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        attr = label.lower()
        prev_count = self._connected_device_count()

        setattr(self, f"n6705c_{attr}", None)
        setattr(self, f"is_connected_{attr}", False)
        w = self._n6705c_conn_widgets[label]
        _update_n6705c_btn_state(w["connect_btn"], connected=False)
        w["connect_btn"].setEnabled(True)
        w["search_btn"].setEnabled(True)
        w["combo"].setEnabled(True)
        w["status"].setText("● Disconnected")
        w["status"].setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
        self.append_log(f"[SYSTEM] N6705C-{label} disconnected.")
        new_count = self._connected_device_count()
        self._apply_preset_channels(prev_count, new_count)
        self._update_available_channels()
        self.connection_status_changed.emit(False)

    def _get_available_channel_options(self):
        options = []
        for label in ["A", "B"]:
            for ch in range(1, 5):
                options.append(f"{label}-CH{ch}")
        return options

    def _connected_device_count(self):
        count = 0
        if self.is_connected_a:
            count += 1
        if self.is_connected_b:
            count += 1
        return count

    def _update_available_channels(self):
        options = self._get_available_channel_options()
        pending_ch = self._pending_channel_selections or {}
        for i, wdata in enumerate(self._channel_config_widgets):
            combo = wdata["channel_combo"]
            # 目标值:优先使用待恢复的导入值,否则使用 _channel_configs 里记录的通道
            desired = None
            if i in pending_ch:
                desired = pending_ch[i]
            elif i < len(self._channel_configs):
                desired = self._channel_configs[i].get("channel", "")
            if not desired:
                desired = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            for opt in options:
                combo.addItem(opt)
            matched = False
            for j in range(combo.count()):
                if combo.itemText(j) == desired:
                    combo.setCurrentIndex(j)
                    matched = True
                    break
            combo.blockSignals(False)
            # 若期望值在选项里找到了,同步回 _channel_configs,并清理 pending
            if matched and i < len(self._channel_configs):
                self._channel_configs[i]["channel"] = desired
            if i in pending_ch and matched:
                pending_ch.pop(i, None)
        if self._pending_channel_selections is not None and not pending_ch:
            self._pending_channel_selections = None

        pending_aux = self._pending_aux_selections or {}
        aux_options = self._get_control_channel_options()
        for key, extra_combo in (("poweron", self.poweron_channel_combo),
                                 ("reset", self.reset_channel_combo)):
            if extra_combo is None:
                continue
            desired = pending_aux.get(key) if pending_aux else None
            if not desired:
                desired = extra_combo.currentText()
            extra_combo.blockSignals(True)
            extra_combo.clear()
            for opt in aux_options:
                extra_combo.addItem(opt)
            matched = False
            for j in range(extra_combo.count()):
                if extra_combo.itemText(j) == desired:
                    extra_combo.setCurrentIndex(j)
                    matched = True
                    break
            extra_combo.blockSignals(False)
            if matched and pending_aux:
                pending_aux.pop(key, None)
        if self._pending_aux_selections is not None and not pending_aux:
            self._pending_aux_selections = None

        self._refresh_result_cards()
        self._update_test_panel_state()

    def _apply_preset_channels(self, prev_count, new_count):
        if prev_count == new_count:
            return
        # 导入配置流程中不允许 preset 覆盖导入后的通道配置
        if getattr(self, "_suppress_preset_channels", False):
            return

        if new_count == 0:
            self._clear_all_channel_configs()
        elif new_count == 1:
            self._clear_all_channel_configs()
            for cfg in self.SINGLE_DEVICE_CHANNEL_CONFIGS:
                self._add_channel_config_card(cfg["name"], cfg["channel"], cfg["enabled"])
        elif new_count >= 2 and prev_count < 2:
            self._clear_all_channel_configs()
            for cfg in self.DUAL_DEVICE_CHANNEL_CONFIGS:
                self._add_channel_config_card(cfg["name"], cfg["channel"], cfg["enabled"])

    def _clear_all_channel_configs(self):
        for wdata in reversed(self._channel_config_widgets):
            wdata["card"].hide()
            wdata["card"].deleteLater()
        self._channel_configs.clear()
        self._channel_config_widgets.clear()
        while self.result_cards_layout.count():
            item = self.result_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()
        self.channel_cards = {}

    def _update_test_panel_state(self):
        has_device = self._connected_device_count() > 0
        if hasattr(self, '_disabled_overlay'):
            if has_device:
                self._disabled_overlay.hide()
            else:
                self._disabled_overlay.show()
                self._disabled_overlay.raise_()

    def _get_checkmark_path(self, accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            get_resource_base(),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }
