#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test MCU 管理（Mixin）。

从 consumption_test.py 平移而来，行为零变更：
  - 会话解析与信号绑定：_current_mcu_type / _mcu_target_instrument_type /
    _mcu_target_session_id / _is_mcu_family_session / _resolve_mcu_session_id /
    _bind_mcu_manager_signals 及五个 manager 信号槽
  - 共享会话同步与高阻初始化：_sync_mcu_from_manager / _apply_mcu_gpio_highz /
    _on_mcu_highz_thread_cleanup / _on_mcu_highz_done / _on_mcu_highz_error
  - 端口搜索/连接/断开（本地 Worker 回退路径）：_on_mcu_search /
    _on_mcu_search_done / _on_mcu_search_error / _on_mcu_connect_or_disconnect /
    _connect_mcu / _on_mcu_connected / _disconnect_mcu 等
  - PwrON/Reset IO 快捷设置：_on_io_state_quick_set / _run_io_state_set /
    _on_io_state_set_done / _on_io_state_set_error / _on_io_state_thread_cleanup
  - 选项构建：_get_mcu_gpio_options / _get_control_channel_options /
    _set_combo_options / _selected_mcu_port

依赖宿主类（ConsumptionTestUI）与其它 Mixin 提供属性与槽；
后台 Worker 来自 core.consumption_test.workers（mcu_workers）。
"""

from ui.widgets.button import update_connect_button_state
from PySide6.QtCore import QThread
from log_config import get_logger
from core.consumption_test.workers import (
    _SearchMcuPortWorker,
    _ConnectMcuWorker,
    _McuPinsHighZWorker,
    _IoStateSetWorker,
)

logger = get_logger(__name__)


class ConsumptionTestViewMcuMixin:

    def _current_mcu_type(self):
        if hasattr(self, "mcu_type_combo") and self.mcu_type_combo is not None:
            data = self.mcu_type_combo.currentData()
            if data in ("yd_rp2040", "ch9114f"):
                return data
        return getattr(self, "_default_mcu_type", "ch9114f")

    def _mcu_target_instrument_type(self):
        """按当前 MCU 类型返回 InstrumentManager 的 instrument_type。"""
        if self._current_mcu_type() == "ch9114f":
            return "ch9114f"
        return "mcu_io"

    def _mcu_target_session_id(self):
        """按当前 MCU 类型返回共享会话 id（ch9114f:default / mcu_io:default）。"""
        if self._current_mcu_type() == "ch9114f":
            return "ch9114f:default"
        return "mcu_io:default"

    def _is_mcu_family_session(self, session_id):
        """CH9114F 与 YD-RP2040 共享会话均属 MCU 家族，状态变更需联动。"""
        return session_id in ("mcu_io:default", "ch9114f:default")

    def _resolve_mcu_session_id(self):
        """解析断开时应操作的 MCU 共享会话 id。

        默认取当前类型的目标会话；类型切换后目标会话与已持实例不符时，
        按实例反查实际会话，确保断开的是当前持有的连接。
        """
        manager = getattr(self, "_instrument_manager", None)
        if manager is None:
            return None
        target = self._mcu_target_session_id()
        session = manager.get_session(target)
        if session and session.connected:
            if self.mcu_io is None or session.instance is self.mcu_io:
                return target
        inst = getattr(self, "mcu_io", None)
        if inst is not None:
            for snap in manager.sessions():
                if manager.get_instance(snap.session_id) is inst:
                    return snap.session_id
        return target

    def _bind_mcu_manager_signals(self):
        """CH9114F / YD-RP2040 共享会话变更时同步本页 MCU 连接状态。"""
        manager = getattr(self, "_instrument_manager", None)
        if manager is None or getattr(self, "_mcu_manager_bound", False):
            return
        manager.session_connected.connect(self._on_mcu_manager_session_connected)
        manager.session_disconnected.connect(self._on_mcu_manager_session_disconnected)
        manager.connection_failed.connect(self._on_mcu_manager_connect_failed)
        manager.scan_finished.connect(self._on_mcu_manager_scan_finished)
        manager.scan_failed.connect(self._on_mcu_manager_scan_failed)
        manager.disconnect_failed.connect(self._on_mcu_manager_disconnect_failed)
        self._mcu_manager_bound = True

    def _on_mcu_manager_session_connected(self, session_id):
        if not self._is_mcu_family_session(session_id):
            return
        was_connected = self.is_mcu_connected
        self._sync_mcu_from_manager()
        if not was_connected and self.is_mcu_connected:
            self._apply_mcu_gpio_highz()

    def _on_mcu_manager_session_disconnected(self, session_id):
        if not self._is_mcu_family_session(session_id):
            return
        self._sync_mcu_from_manager()

    def _on_mcu_manager_connect_failed(self, session_id, error):
        if session_id != self._mcu_target_session_id():
            return
        self.mcu_status_label.setText("● Failed")
        self.mcu_status_label.setStyleSheet(
            "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(True)
        self.append_log(f"[MCU] Connection failed: {error}")

    def _on_mcu_manager_disconnect_failed(self, session_id, error):
        if not self._is_mcu_family_session(session_id):
            return
        # 会话仍处于连接态，恢复为已连接 UI（search 禁用、connect 可点）
        self.mcu_status_label.setText("● Disconnect Failed")
        self.mcu_status_label.setStyleSheet(
            "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(False)
        self.mcu_connect_btn.setEnabled(True)
        self.append_log(f"[MCU] Disconnect failed: {error}")

    def _on_mcu_manager_scan_finished(self, instrument_type, candidates):
        if instrument_type != self._mcu_target_instrument_type() \
                or not hasattr(self, "mcu_port_combo"):
            return
        mcu_type = self._current_mcu_type()
        self.mcu_port_combo.clear()
        self.mcu_port_combo.setEnabled(True)
        if candidates:
            for cand in candidates:
                self.mcu_port_combo.addItem(cand.display_name or cand.resource)
            self.mcu_status_label.setText(f"● Found {len(candidates)}")
            self.mcu_status_label.setStyleSheet(
                "color: #00a859; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            label = "CH9114F port(s)" if mcu_type == "ch9114f" else "serial port(s)"
            self.append_log(f"[MCU] Found {len(candidates)} {label}.")
        else:
            if mcu_type == "ch9114f":
                self.mcu_port_combo.addItem("No CH9114F ports found")
            else:
                self.mcu_port_combo.addItem("No serial ports found")
            self.mcu_port_combo.setEnabled(False)
            self.mcu_status_label.setText("● Not Found")
            self.mcu_status_label.setStyleSheet(
                "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(bool(candidates))

    def _on_mcu_manager_scan_failed(self, instrument_type, error):
        if instrument_type != self._mcu_target_instrument_type():
            return
        self.mcu_status_label.setText("● Search Failed")
        self.mcu_status_label.setStyleSheet(
            "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.append_log(f"[MCU] Search failed: {error}")
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(True)

    def _sync_mcu_from_manager(self):
        manager = getattr(self, "_instrument_manager", None)
        if manager is None or not hasattr(self, "mcu_connect_btn"):
            return
        session = manager.get_session(self._mcu_target_session_id())
        if session and session.connected and session.instance:
            already = self.is_mcu_connected and self.mcu_io is session.instance
            self.mcu_io = session.instance
            self.is_mcu_connected = True
            self.mcu_status_label.setText("● Connected")
            self.mcu_status_label.setStyleSheet(
                "color: #00a859; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_search_btn.setEnabled(False)
            self.mcu_connect_btn.setEnabled(True)
            update_connect_button_state(self.mcu_connect_btn, True)
            if session.resource and hasattr(self, "mcu_port_combo"):
                if self.mcu_port_combo.findText(session.resource) < 0:
                    self.mcu_port_combo.addItem(session.resource)
                self.mcu_port_combo.setCurrentText(session.resource)
            if not already:
                self.append_log("[MCU] Connected (shared session).")
        else:
            if self.is_mcu_connected or self.mcu_io is not None:
                self.mcu_io = None
                self.is_mcu_connected = False
                self.mcu_status_label.setText("● Disconnected")
                self.mcu_status_label.setStyleSheet(
                    "color: #8ea6cf; font-size: 10px; font-weight: bold; background: transparent; border: none;"
                )
                self.mcu_search_btn.setEnabled(True)
                self.mcu_connect_btn.setEnabled(True)
                update_connect_button_state(self.mcu_connect_btn, False)
                self.append_log("[MCU] Disconnected (shared session).")

    def _apply_mcu_gpio_highz(self):
        if not self.is_mcu_connected or self.mcu_io is None:
            return
        if self._mcu_highz_thread is not None and self._mcu_highz_thread.isRunning():
            return
        pins = [int(opt[4:]) for opt in self._get_mcu_gpio_options()]
        worker = _McuPinsHighZWorker(self.mcu_io, pins)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_highz_done)
        worker.error.connect(self._on_mcu_highz_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_mcu_highz_thread_cleanup())
        self._mcu_highz_worker = worker
        self._mcu_highz_thread = thread
        thread.start()

    def _on_mcu_highz_thread_cleanup(self):
        self._mcu_highz_thread = None
        self._mcu_highz_worker = None

    def _on_mcu_highz_done(self, failed_pins):
        if failed_pins:
            self.append_log(f"[MCU] GPIO high-Z init failed on pin(s): {failed_pins}")
        else:
            self.append_log("[MCU] All GPIO pins initialized to high-impedance (input).")

    def _on_mcu_highz_error(self, err):
        self.append_log(f"[MCU] GPIO high-Z init failed: {err}")

    def _get_mcu_gpio_options(self):
        if self._current_mcu_type() == "ch9114f":
            return [f"GPIO{i}" for i in (0, 1, 6, 7, 2, 8, 14, 20)]
        return [f"GPIO{i}" for i in range(0, 30)]

    def _get_control_channel_options(self, method=None):
        method = method or (
            self.control_method_toggle.value()
            if getattr(self, "control_method_toggle", None) else "N6705C"
        )
        if method == "MCU":
            return self._get_mcu_gpio_options()
        return self._get_available_channel_options()

    @staticmethod
    def _set_combo_options(combo, options, desired=None):
        if combo is None:
            return False
        if desired is None:
            desired = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for opt in options:
            combo.addItem(opt)
        matched = False
        if desired:
            for i in range(combo.count()):
                if combo.itemText(i) == desired:
                    combo.setCurrentIndex(i)
                    matched = True
                    break
        if not matched and combo.count() > 0:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)
        return matched

    def _selected_mcu_port(self):
        text = self.mcu_port_combo.currentText() if getattr(self, "mcu_port_combo", None) else ""
        if not text or text in (
            "No serial ports found",
            "No CH9114F ports found",
            "Select MCU COM...",
            "Select CH9114F COM...",
        ):
            return None
        return text.split()[0]

    def _on_mcu_search(self):
        from debug_config import DEBUG_MOCK
        mcu_type = self._current_mcu_type()
        if DEBUG_MOCK:
            self.mcu_port_combo.clear()
            if mcu_type == "ch9114f":
                self.mcu_port_combo.addItem("[MOCK] COM99 - Mock CH9114F")
            else:
                self.mcu_port_combo.addItem("[MOCK] COM98 - Mock YD RP2040")
            self.mcu_status_label.setText("● Mock Ready")
            self.mcu_status_label.setStyleSheet(
                "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_connect_btn.setEnabled(True)
            self.append_log(f"[DEBUG] Mock {mcu_type} port loaded.")
            return

        manager = getattr(self, "_instrument_manager", None)
        if manager is not None:
            self.mcu_status_label.setText("● Searching")
            self.mcu_status_label.setStyleSheet(
                "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_search_btn.setEnabled(False)
            self.mcu_connect_btn.setEnabled(False)
            if mcu_type == "ch9114f":
                self.append_log("[MCU] Scanning for CH9114F ports...")
            else:
                self.append_log("[MCU] Scanning serial ports for YD RP2040...")
            # YD-RP2040 走 "mcu_io"、CH9114F 走 "ch9114f"，均经
            # InstrumentManager 共享扫描结果
            manager.scan_async(self._mcu_target_instrument_type())
            return

        if self._mcu_search_thread is not None and self._mcu_search_thread.isRunning():
            return
        self.mcu_status_label.setText("● Searching")
        self.mcu_status_label.setStyleSheet(
            "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(False)
        self.mcu_connect_btn.setEnabled(False)
        if mcu_type == "ch9114f":
            self.append_log("[MCU] Scanning for CH9114F ports...")
        else:
            self.append_log("[MCU] Scanning serial ports for YD RP2040...")

        worker = _SearchMcuPortWorker(mcu_type)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_search_done)
        worker.error.connect(self._on_mcu_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_mcu_search_thread_cleanup())
        self._mcu_search_worker = worker
        self._mcu_search_thread = thread
        thread.start()

    def _on_mcu_search_done(self, ports):
        mcu_type = self._current_mcu_type()
        self.mcu_port_combo.clear()
        self.mcu_port_combo.setEnabled(True)
        if ports:
            for port in ports:
                self.mcu_port_combo.addItem(port)
            self.mcu_status_label.setText(f"● Found {len(ports)}")
            self.mcu_status_label.setStyleSheet(
                "color: #00a859; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            label = "CH9114F port(s)" if mcu_type == "ch9114f" else "serial port(s)"
            self.append_log(f"[MCU] Found {len(ports)} {label}.")
        else:
            if mcu_type == "ch9114f":
                self.mcu_port_combo.addItem("No CH9114F ports found")
            else:
                self.mcu_port_combo.addItem("No serial ports found")
            self.mcu_port_combo.setEnabled(False)
            self.mcu_status_label.setText("● Not Found")
            self.mcu_status_label.setStyleSheet(
                "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(bool(ports))

    def _on_mcu_search_error(self, err):
        self.mcu_status_label.setText("● Search Failed")
        self.mcu_status_label.setStyleSheet(
            "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.append_log(f"[MCU] Search failed: {err}")
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(True)

    def _on_mcu_search_thread_cleanup(self):
        self._mcu_search_thread = None
        self._mcu_search_worker = None

    def _on_mcu_connect_or_disconnect(self):
        if self.is_mcu_connected:
            self._disconnect_mcu()
        else:
            self._connect_mcu()

    def _connect_mcu(self):
        port = self._selected_mcu_port()
        if not port:
            self.append_log("[MCU] No valid MCU port selected.")
            return
        mcu_type = self._current_mcu_type()

        manager = getattr(self, "_instrument_manager", None)
        if manager is not None:
            # YD-RP2040 与 CH9114F 均经 InstrumentManager 建立共享会话
            session_id = self._mcu_target_session_id()
            existing = manager.get_session(session_id)
            if existing and existing.connected:
                self._sync_mcu_from_manager()
                return
            self.mcu_status_label.setText("● Connecting")
            self.mcu_status_label.setStyleSheet(
                "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_search_btn.setEnabled(False)
            self.mcu_connect_btn.setEnabled(False)
            type_label = "CH9114F" if mcu_type == "ch9114f" else "YD RP2040"
            self.append_log(f"[MCU] Connecting {type_label} on {port}...")
            from core.instruments import InstrumentSpec
            instrument_type = self._mcu_target_instrument_type()
            manager.connect_async(InstrumentSpec(
                instrument_type=instrument_type,
                role=instrument_type,
                connection_kind="serial_raw_repl",
                slot="default",
                resource=port,
            ))
            return

        if self._mcu_connect_thread is not None and self._mcu_connect_thread.isRunning():
            return
        self.mcu_status_label.setText("● Connecting")
        self.mcu_status_label.setStyleSheet(
            "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(False)
        self.mcu_connect_btn.setEnabled(False)
        type_label = "CH9114F" if mcu_type == "ch9114f" else "YD RP2040"
        self.append_log(f"[MCU] Connecting {type_label} on {port}...")

        hiz_pins = [int(opt[4:]) for opt in self._get_mcu_gpio_options()]
        worker = _ConnectMcuWorker(port, mcu_type=mcu_type, hiz_pins=hiz_pins)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.gpio_init_done.connect(self._on_mcu_gpio_init_done)
        worker.finished.connect(self._on_mcu_connected)
        worker.error.connect(self._on_mcu_connect_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_mcu_connect_thread_cleanup())
        self._mcu_connect_worker = worker
        self._mcu_connect_thread = thread
        thread.start()

    def _on_mcu_connected(self, inst, idn):
        self.mcu_io = inst
        self.is_mcu_connected = True
        self.mcu_status_label.setText("● Connected")
        self.mcu_status_label.setStyleSheet(
            "color: #00a859; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(False)
        self.mcu_connect_btn.setEnabled(True)
        update_connect_button_state(self.mcu_connect_btn, True)
        self.append_log(f"[MCU] Connected: {idn}")
        self._suppress_preset_channels = False

    def _on_mcu_gpio_init_done(self, failed_pins):
        if failed_pins:
            self.append_log(f"[MCU] GPIO high-Z init failed on pin(s): {failed_pins}")
        else:
            self.append_log("[MCU] All GPIO pins initialized to high-impedance (input).")

    def _on_mcu_connect_error(self, err):
        self.mcu_status_label.setText("● Failed")
        self.mcu_status_label.setStyleSheet(
            "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(True)
        self.append_log(f"[MCU] Connection failed: {err}")
        self._suppress_preset_channels = False

    def _on_mcu_connect_thread_cleanup(self):
        self._mcu_connect_thread = None
        self._mcu_connect_worker = None

    def _disconnect_mcu(self):
        manager = getattr(self, "_instrument_manager", None)
        if manager is not None:
            # YD-RP2040 与 CH9114F 均经 InstrumentManager 断开共享会话
            session_id = self._resolve_mcu_session_id()
            session = manager.get_session(session_id)
            if session and session.connected:
                self.mcu_status_label.setText("● Disconnecting")
                self.mcu_status_label.setStyleSheet(
                    "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
                )
                self.mcu_connect_btn.setEnabled(False)
                manager.disconnect_async(session_id)
                return
            self.mcu_io = None
            self.is_mcu_connected = False
            self.mcu_status_label.setText("● Disconnected")
            self.mcu_status_label.setStyleSheet(
                "color: #8ea6cf; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_search_btn.setEnabled(True)
            self.mcu_connect_btn.setEnabled(True)
            update_connect_button_state(self.mcu_connect_btn, False)
            self.append_log("[MCU] Disconnected.")
            return

        try:
            if self.mcu_io is not None:
                self.mcu_io.disconnect()
        except Exception as e:
            logger.error("MCU disconnect failed: %s", e, exc_info=True)
            self.append_log(f"[MCU] Disconnect failed: {e}")
        finally:
            self.mcu_io = None
            self.is_mcu_connected = False
            self.mcu_status_label.setText("● Disconnected")
            self.mcu_status_label.setStyleSheet(
                "color: #8ea6cf; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_search_btn.setEnabled(True)
            self.mcu_connect_btn.setEnabled(True)
            update_connect_button_state(self.mcu_connect_btn, False)
            self.append_log("[MCU] Disconnected.")

    # ---- PwrON/RESET IO 快捷设置（"⋯" 菜单, 参考 vmin_hunter MCU PWR/RESET）----

    def _on_io_state_quick_set(self, name, state):
        """菜单回调：把 PwrON/RESET 行当前选中的 IO 快捷设为 输出高/输出低/高阻。

        Reset 未勾选 enable 时仍可手动设置（勾选仅控制自动流程是否执行该步骤）。
        """
        label = "PwrON" if name == "poweron" else "Reset"
        if self.is_testing:
            self.append_log(f"[IO] Test running, {label} manual set ignored.")
            return
        combo = (
            self.poweron_channel_combo if name == "poweron"
            else self.reset_channel_combo
        )
        channel_key = combo.currentText() if combo is not None else ""
        if not channel_key:
            self.append_log(f"[IO] {label} channel not configured, quick set skipped.")
            return
        device_label, hw_ch = self._parse_channel_key(channel_key)
        if device_label is None or hw_ch is None:
            self.append_log(f"[IO] Invalid {label} channel key: {channel_key}")
            return

        if device_label == "MCU":
            if not self.is_mcu_connected or self.mcu_io is None:
                self.append_log("[IO] MCU is not connected, cannot set IO state.")
                return
            inst = self.mcu_io
        else:
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            if not getattr(self, f"is_connected_{attr}", False) or inst is None:
                self.append_log(f"[IO] N6705C-{device_label} is not connected.")
                return
        self._run_io_state_set(label, channel_key, inst, hw_ch,
                               device_label == "MCU", state)

    def _run_io_state_set(self, label, channel_key, inst, hw_ch, is_mcu, state):
        """起后台线程把指定 IO 设为 High/Low/HighZ，避免阻塞 UI。"""
        if self._io_state_thread is not None and self._io_state_thread.isRunning():
            self.append_log("[IO] Another IO state set is running, ignored.")
            return

        if is_mcu:
            self.append_log(f"[IO] {label} quick set {channel_key} -> {state}")
        else:
            level_desc = {"High": "2.3V", "Low": "0.1V", "HighZ": "OFF (High-Z)"}.get(state, state)
            self.append_log(f"[IO] {label} quick set {channel_key} -> {state} ({level_desc})")

        worker = _IoStateSetWorker(inst, label, hw_ch, is_mcu, state)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_io_state_set_done)
        worker.error.connect(self._on_io_state_set_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_io_state_thread_cleanup)
        self._io_state_worker = worker
        self._io_state_thread = thread
        thread.start()

    def _on_io_state_set_done(self, label, state):
        self.append_log(f"[IO] {label} -> {state} done.")

    def _on_io_state_set_error(self, err):
        self.append_log(f"[IO] Set IO state failed: {err}")

    def _on_io_state_thread_cleanup(self):
        self._io_state_thread = None
        self._io_state_worker = None
