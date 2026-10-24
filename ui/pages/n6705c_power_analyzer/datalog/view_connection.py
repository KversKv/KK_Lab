#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import threading
from PySide6.QtCore import QThread, QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from debug_config import DEBUG_MOCK
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.pages.n6705c_power_analyzer.n6705c_settings_dialog import load_datalog_app_settings
from resource_path import get_resource_base
from ui.widgets.button import update_connect_button_state
from ui.pages.n6705c_power_analyzer.datalog.helpers import _make_svg_icon
from ui.pages.n6705c_power_analyzer.datalog.workers import _ConnectWorker, _ScanWorker
from log_config import get_logger

logger = get_logger(__name__)

class ConnectionViewMixin:
    """Datalog 页连接管理视图：设备卡片 / 槽位 / 扫描 / 连接 / 默认设备。"""

    def _apply_slot_state(self, label, connected, instance=None,
                          serial="", visa_resource=""):
        """把 A/B 槽位的连接态应用到本页（两个同步入口共用）。

        connected=True 时登记实例、分配槽位并确保设备卡片存在；
        connected=False 时仅在当前已连接的情况下清空槽位。
        面板折叠不在此做：仅用户本页点击 Connect 成功时折叠（见
        _on_connect_success / _on_manager_sessions_changed 的 pending 分支）。
        """
        if connected:
            if label == "A":
                self.n6705c_a = instance
                self.is_connected_a = True
            elif label == "B":
                self.n6705c_b = instance
                self.is_connected_b = True
            self._assign_slot(label, serial, "N6705C", visa_resource)
            self._ensure_device_card_exists(serial, "N6705C", visa_resource)
        else:
            if label == "A" and self.is_connected_a:
                self.n6705c_a = None
                self.is_connected_a = False
                self._clear_slot(label)
            elif label == "B" and self.is_connected_b:
                self.n6705c_b = None
                self.is_connected_b = False
                self._clear_slot(label)

    def _after_slot_states_synced(self):
        """槽位同步完成后的统一收尾（两个同步入口共用）。

        按槽位签名去重：top 与 manager 双路同步、以及 manager 无关 session
        事件（其它仪器 / busy 标记）都会走到这里，签名不变时直接跳过，
        避免重复全量重建通道配置区；connection_status_changed 也仅在值变化时发出。
        """
        sig = (
            self.is_connected_a,
            self.slot_frames["A"].property("assigned_serial") or "",
            self.is_connected_b,
            self.slot_frames["B"].property("assigned_serial") or "",
            # pending 必须纳入签名：top 路同步（session_connected→connection_changed
            # →_sync_from_top）先于 manager 对账（sessions_changed 清 pending）到达，
            # 否则 pending 清除时签名不变被去重跳过，设备卡片永久卡 "Connecting..."
            tuple(sorted(self._pending_connects.items())),
        )
        if sig == self._last_slot_sync_sig:
            return
        self._last_slot_sync_sig = sig
        if self.is_connected_a != self._last_conn_status_emitted:
            self._last_conn_status_emitted = self.is_connected_a
            self.connection_status_changed.emit(self.is_connected_a)
        self._refresh_channel_config(force=True)
        self._sync_device_card_states()
        self._update_time_offset_btn_visibility()

    def _on_manager_sessions_changed(self):
        """仪器管理器 sessions 变化时同步本页连接状态与设备卡片。"""
        if not self._instrument_manager:
            return
        sessions = self._instrument_manager.sessions(instrument_type="n6705c")
        seen_labels = set()
        for snap in sessions:
            label = snap.slot.upper() if snap.slot in ("A", "B", "a", "b") else None
            if label is None:
                continue
            seen_labels.add(label)
            if snap.disconnecting:
                # 异步断连过渡态：快照仍 connected=True，但本地已先行清理，
                # 跳过避免被重新套用而误判为新连接（会误折叠仪器面板）；
                # 断连失败时下一次 sessions_changed 会以 connected 快照回弹状态
                continue
            if snap.connected:
                if self._pending_connects.get(label) == snap.resource:
                    # 本页发起的连接成功：清除 pending 并折叠仪器面板；
                    # 门禁用 isHidden() 而非 isVisible()——启动自动连接完成时本页
                    # 常非 QStackedWidget 当前页，isVisible() 受祖先隐藏影响恒为
                    # False 会跳过折叠，切回本页时仪器面板仍展开
                    self._pending_connects.pop(label, None)
                    if not self.instrument_panel.isHidden():
                        self._collapse_instrument_panel()
                instance = self._instrument_manager.get_instance(snap.session_id)
                display_serial = snap.serial if snap.serial else snap.resource
                self._apply_slot_state(
                    label, True, instance=instance,
                    serial=display_serial, visa_resource=snap.resource,
                )
            else:
                self._apply_slot_state(label, False)
        # 对账：manager 中已不存在（如被他页 remove_session）而本地仍连接的槽位，清掉
        for label in ("A", "B"):
            locally_connected = self.is_connected_a if label == "A" else self.is_connected_b
            if locally_connected and label not in seen_labels:
                self._apply_slot_state(label, False)
        self._after_slot_states_synced()

    @staticmethod
    def _slot_label_from_session_id(session_id):
        """从 'n6705c:A' 形式的 session_id 解析槽位字母，非本页槽位返回 None。"""
        if not isinstance(session_id, str) or ":" not in session_id:
            return None
        instr_type, _, slot = session_id.partition(":")
        if instr_type != "n6705c":
            return None
        label = slot.upper()
        return label if label in ("A", "B") else None

    def _on_manager_connection_failed(self, session_id, error):
        """manager 连接失败（含同槽并发被拒）：清除 pending、恢复卡片按钮并提示。"""
        label = self._slot_label_from_session_id(session_id)
        if label is None:
            return
        self._pending_connects.pop(label, None)
        self._sync_device_card_states()
        QMessageBox.warning(self, "连接失败", f"仪器连接失败：{error}")

    def _on_manager_disconnect_failed(self, session_id, error):
        """manager 异步断连失败：状态由 sessions_changed 自动回弹，这里提示用户。"""
        label = self._slot_label_from_session_id(session_id)
        if label is None:
            return
        QMessageBox.warning(self, "断开失败", f"仪器断开失败：{error}")

    def _sync_from_top(self):
        if not self._top:
            return
        for label, attr_suffix in [("A", "a"), ("B", "b")]:
            n6705c = getattr(self._top, f"n6705c_{attr_suffix}", None)
            is_conn = getattr(self._top, f"is_connected_{attr_suffix}", False)
            visa_res = getattr(self._top, f"visa_resource_{attr_suffix}", "")
            serial = getattr(self._top, f"serial_{attr_suffix}", "")
            if is_conn and n6705c:
                display_serial = serial if serial else (
                    visa_res.split("::")[1] if "::" in visa_res else visa_res
                )
                self._apply_slot_state(
                    label, True, instance=n6705c,
                    serial=display_serial, visa_resource=visa_res,
                )
            else:
                self._apply_slot_state(label, False)
        self._after_slot_states_synced()

    def _ensure_device_card_exists(self, serial, model, visa_resource):
        existing_serials = {c.property("serial") for c in self.device_cards}
        if serial in existing_serials:
            return
        display_ip = visa_resource
        if "TCPIP" in visa_resource and "::" in visa_resource:
            parts = visa_resource.split("::")
            if len(parts) >= 2:
                display_ip = parts[1]
        # 同一 VISA 资源已存在卡片（如手动/默认添加时 serial 回退为资源串），
        # 连接后拿到真实序列号，应就地替换该卡片而非新增，避免出现重复卡片。
        for idx, existing_card in enumerate(self.device_cards):
            if existing_card.property("visa_resource") == visa_resource:
                new_card = self._create_device_card(
                    serial, model, display_ip, visa_resource,
                    auto_connect=existing_card.property("auto_connect"),
                )
                layout_idx = self.device_list_layout.indexOf(existing_card)
                self.device_list_layout.removeWidget(existing_card)
                existing_card.deleteLater()
                self.device_list_layout.insertWidget(layout_idx, new_card)
                self.device_cards[idx] = new_card
                return
        card = self._create_device_card(serial, model, display_ip, visa_resource)
        self.device_list_layout.insertWidget(
            self.device_list_layout.count() - 1, card
        )
        self.device_cards.append(card)

    @staticmethod
    def _get_checkmark_path(accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            get_resource_base(),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

    def _create_slot_widget(self, label_char):
        frame = QFrame()
        frame.setObjectName("cardFrame")
        frame.setFixedHeight(66)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        letter = QLabel(label_char)
        letter.setStyleSheet(dss.SLOT_LETTER_DEFAULT_STYLE)
        letter.setFixedWidth(24)
        layout.addWidget(letter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel("Not Supported")
        name_label.setStyleSheet(dss.SLOT_NAME_DEFAULT_STYLE)
        info_layout.addWidget(name_label)
        layout.addLayout(info_layout, 1)

        frame.setProperty("slot_label", label_char)
        frame.setProperty("name_label", name_label)
        frame.setProperty("assigned_serial", "")
        frame.setProperty("connected", False)
        frame.setContextMenuPolicy(Qt.CustomContextMenu)
        frame.customContextMenuRequested.connect(
            lambda pos, f=frame: self._on_slot_context_menu(f, pos)
        )

        return frame

    def _create_device_card(self, serial, model, ip_addr, visa_resource, auto_connect=False):
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setFixedHeight(72)
        card_layout = QGridLayout(card)
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setHorizontalSpacing(8)
        card_layout.setVerticalSpacing(2)

        # 左侧图标列（跨第 0、1 行）：仅缩略图，垂直居中
        icon_widget = QWidget()
        icon_widget.setStyleSheet("background: transparent; border: none;")
        icon_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        icon_layout = QVBoxLayout(icon_widget)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)
        thumb_label = QLabel()
        thumb_label.setStyleSheet(dss.CARD_THUMB_STYLE)
        thumb_label.setFixedSize(48, 30)
        svg_path = os.path.join(get_resource_base(), "resources", "pages", "n6705c_power_analyzer_SVGs", "n6705c_thumb.svg")
        if os.path.exists(svg_path):
            pixmap = QPixmap(48, 30)
            pixmap.fill(QColor(0, 0, 0, 0))
            renderer = QSvgRenderer(svg_path)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            thumb_label.setPixmap(pixmap)
        icon_layout.addStretch()
        icon_layout.addWidget(thumb_label)
        icon_layout.addStretch()
        card_layout.addWidget(icon_widget, 0, 0, 2, 1)

        # 中间信息列（跨第 0、1 行）：型号 + IP
        info_widget = QWidget()
        info_widget.setStyleSheet("background: transparent; border: none;")
        info_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        # 上下 addStretch 让 model+ip 在跨两行的空间内垂直居中，与图标对齐
        info_layout.addStretch()
        model_label = QLabel(model)
        model_label.setStyleSheet(dss.CARD_MODEL_STYLE)
        ip_label = QLabel(ip_addr)
        ip_label.setStyleSheet(dss.CARD_IP_STYLE)
        info_layout.addWidget(model_label)
        info_layout.addWidget(ip_label)
        info_layout.addStretch()
        card_layout.addWidget(info_widget, 0, 1, 2, 1)

        # 第 2 行：完整 VISA 地址（跨越图标列 + 信息列）。
        # 用 QLineEdit(ReadOnly) 而非 QLabel：QLabel 的 minimumSizeHint 由文本宽度决定，
        # 长 VISA 串会撑开 QGridLayout 列宽；QLineEdit 的 minimumSizeHint 很小，不会撑开。
        visa_label = QLineEdit(visa_resource)
        visa_label.setReadOnly(True)
        visa_label.setStyleSheet(dss.CARD_VISA_STYLE)
        visa_label.setToolTip(visa_resource)
        visa_label.setCursor(Qt.IBeamCursor)
        visa_label.setFrame(False)
        card_layout.addWidget(visa_label, 2, 0, 1, 2)

        # 右侧按钮列（跨全部 3 行）
        connect_btn = QPushButton()
        update_connect_button_state(connect_btn, connected=False)
        connect_btn.setFixedWidth(116)
        connect_btn.clicked.connect(lambda: self._on_device_connect(visa_resource, serial))
        card_layout.addWidget(connect_btn, 0, 2, 3, 1)

        disconnect_btn = QPushButton()
        update_connect_button_state(disconnect_btn, connected=True)
        disconnect_btn.setFixedWidth(116)
        disconnect_btn.clicked.connect(lambda: self._on_device_disconnect(serial))
        disconnect_btn.hide()
        card_layout.addWidget(disconnect_btn, 0, 2, 3, 1)

        card_layout.setColumnStretch(1, 1)

        card.setProperty("visa_resource", visa_resource)
        card.setProperty("serial", serial)
        card.setProperty("auto_connect", bool(auto_connect))
        card.setProperty("connect_btn", connect_btn)
        card.setProperty("disconnect_btn", disconnect_btn)
        card.setProperty("model_label", model_label)
        card.setProperty("ip_label", ip_label)

        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, c=card: self._on_device_card_context_menu(c, pos)
        )

        return card

    def _on_refresh_search(self):
        # 已连接或连接进行中的卡片保留：hislip 占用时扫描可能发现不了
        # 已连接设备，无条件删卡会让其永久失去卡片入口
        kept_serials = set()
        kept_resources = set(self._pending_connects.values())
        for label_char in ["A", "B"]:
            slot = self.slot_frames[label_char]
            s = slot.property("assigned_serial")
            if s:
                kept_serials.add(s.strip())
                kept_resources.add(slot.property("assigned_resource"))
        kept_cards = []
        for card in self.device_cards:
            if (card.property("serial") or "").strip() in kept_serials \
                    or card.property("visa_resource") in kept_resources:
                kept_cards.append(card)
                continue
            self.device_list_layout.removeWidget(card)
            card.deleteLater()
        self.device_cards[:] = kept_cards

        if DEBUG_MOCK:
            self._add_default_debug_device()
        else:
            self._add_default_saved_devices()

        self.refresh_search_btn.setEnabled(False)
        self.refresh_search_btn.start_spinning()

        self._scan_thread = QThread()
        self._scan_worker = _ScanWorker()
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_worker.device_found.connect(self._on_scan_device_found)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_worker.error.connect(lambda e: None)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_thread.finished.connect(self._scan_thread.deleteLater)
        self._scan_thread.finished.connect(self._on_scan_thread_done)

        self._scan_thread.start()

    def _on_scan_device_found(self, serial, model, ip, visa_resource):
        existing = {c.property("serial") for c in self.device_cards}
        existing |= {c.property("visa_resource") for c in self.device_cards}
        if serial in existing or visa_resource in existing:
            return
        card = self._create_device_card(serial, model, ip, visa_resource)
        self.device_list_layout.insertWidget(
            self.device_list_layout.count() - 1, card
        )
        self.device_cards.append(card)

    def _on_scan_finished(self):
        self.refresh_search_btn.stop_spinning()
        self.refresh_search_btn.setEnabled(True)
        # 自愈补卡：已连接设备因 hislip 占用未被扫描发现时，按槽位信息补回卡片
        for label_char in ["A", "B"]:
            slot = self.slot_frames[label_char]
            serial = slot.property("assigned_serial")
            resource = slot.property("assigned_resource")
            if serial and resource:
                self._ensure_device_card_exists(serial, "N6705C", resource)
        self._sync_device_card_states()
        self._maybe_show_scope_hint()
        self._auto_connect_enabled_cards()

    def _maybe_show_scope_hint(self):
        """搜索完成后提示搜索作用域（每次运行仅弹一次，未配置跨网段时才弹）。"""
        if getattr(self, "_scope_hint_shown", False):
            return
        try:
            from core.n6705c.search_worker import discovery_scope_hint
            hint = discovery_scope_hint()
        except Exception:
            hint = None
        if not hint:
            return
        self._scope_hint_shown = True
        QMessageBox.information(self, "搜索范围提示", hint)

    def _on_scan_thread_done(self):
        self._scan_thread = None
        self._scan_worker = None

    def _sync_device_card_states(self):
        connected_serials = set()
        for label_char in ["A", "B", "C", "D"]:
            s = self.slot_frames[label_char].property("assigned_serial")
            if s:
                connected_serials.add(s.strip())

        pending_resources = set(self._pending_connects.values())
        for card in self.device_cards:
            card_serial = (card.property("serial") or "").strip()
            connect_btn = card.property("connect_btn")
            disconnect_btn = card.property("disconnect_btn")
            if card.property("visa_resource") in pending_resources:
                # 连接进行中：保持禁用态，避免任何同步路径把按钮重新启用
                if connect_btn:
                    connect_btn.setEnabled(False)
                    connect_btn.setText("Connecting...")
                    connect_btn.show()
                if disconnect_btn:
                    disconnect_btn.hide()
            elif card_serial in connected_serials:
                if connect_btn:
                    connect_btn.hide()
                if disconnect_btn:
                    disconnect_btn.show()
            else:
                if connect_btn:
                    connect_btn.setEnabled(True)
                    update_connect_button_state(connect_btn, connected=False)
                    connect_btn.show()
                if disconnect_btn:
                    disconnect_btn.hide()

    def _find_next_free_slot(self):
        for label_char in ["A", "B"]:
            if label_char in self._pending_connects:
                continue
            slot = self.slot_frames[label_char]
            if not slot.property("assigned_serial"):
                return label_char
        return None

    def _on_device_connect(self, visa_resource, serial):
        logger.debug("Datalog UI _on_device_connect: resource=%s, serial=%s", visa_resource, serial)
        # 重复连接守卫：同一 VISA 资源已占用某个槽位
        for label_char in ["A", "B"]:
            slot = self.slot_frames[label_char]
            if slot.property("assigned_serial") and \
                    slot.property("assigned_resource") == visa_resource:
                QMessageBox.information(self, "重复连接", "该仪器已连接。")
                return
        # 同一资源正在连接中：按钮已是禁用态，静默忽略重复触发
        if visa_resource in self._pending_connects.values():
            return
        slot_label = self._find_next_free_slot()
        if slot_label is None:
            QMessageBox.information(
                self, "无可用槽位", "两个仪器槽位均已占用，请先断开一台仪器。"
            )
            return

        for card in self.device_cards:
            if card.property("serial") == serial:
                btn = card.property("connect_btn")
                if btn:
                    btn.setEnabled(False)
                    btn.setText("Connecting...")
                break

        self._pending_connects[slot_label] = visa_resource

        if self._instrument_manager:
            from core.instruments import InstrumentSpec
            try:
                self._instrument_manager.connect_async(InstrumentSpec(
                    instrument_type="n6705c",
                    role="power_analyzer",
                    connection_kind="visa",
                    slot=slot_label,
                    resource=visa_resource,
                ))
            except Exception as e:
                # 同步抛错（如 profile 未注册）时恢复 pending 与按钮态
                self._pending_connects.pop(slot_label, None)
                self._sync_device_card_states()
                QMessageBox.warning(self, "连接失败", f"仪器连接失败：{e}")
            return

        self._connect_thread = QThread()
        self._connect_worker = _ConnectWorker(visa_resource, serial, DEBUG_MOCK)
        self._connect_worker.moveToThread(self._connect_thread)

        self._connect_worker.success.connect(
            lambda n6705c, s, r: self._on_connect_success(n6705c, s, r, slot_label)
        )
        self._connect_worker.error.connect(
            lambda e: self._on_connect_error(serial, slot_label, e)
        )
        self._connect_worker.finished.connect(self._connect_thread.quit)
        self._connect_worker.finished.connect(self._connect_worker.deleteLater)
        self._connect_thread.started.connect(self._connect_worker.run)
        self._connect_thread.finished.connect(self._connect_thread.deleteLater)
        self._connect_thread.finished.connect(self._on_connect_thread_done)

        self._connect_thread.start()

    def _on_connect_success(self, n6705c, serial, visa_resource, slot_label):
        logger.debug("Datalog UI connect success: slot=%s, serial=%s", slot_label, serial)
        self._last_connect_succeeded = True
        self._pending_connects.pop(slot_label, None)
        if slot_label == "A":
            self.n6705c_a = n6705c
            self.is_connected_a = True
            if self._top:
                self._top.connect_a(visa_resource, n6705c_instance=n6705c, serial=serial)
        elif slot_label == "B":
            self.n6705c_b = n6705c
            self.is_connected_b = True
            if self._top:
                self._top.connect_b(visa_resource, n6705c_instance=n6705c, serial=serial)

        self._assign_slot(slot_label, serial, "N6705C", visa_resource)
        self._ensure_device_card_exists(serial, "N6705C", visa_resource)
        self._after_slot_states_synced()

        # 同 manager 路：门禁用 isHidden()（启动自动连接时本页可能非当前页）
        if not self.instrument_panel.isHidden():
            self._collapse_instrument_panel()

    def _on_connect_error(self, serial, slot_label, error_msg=None):
        logger.error("Datalog UI connect failed: serial=%s, error=%s", serial, error_msg)
        self._last_connect_succeeded = False
        self._pending_connects.pop(slot_label, None)
        self._sync_device_card_states()
        QMessageBox.warning(self, "连接失败", f"仪器连接失败：{error_msg}")

    def _on_connect_thread_done(self):
        self._connect_thread = None
        self._connect_worker = None
        # 仅连接成功才链式补连其余 auto_connect 卡片，失败即终止，避免无限重试；
        # §26：finished 槽链里延后 50ms 再起新 QThread，避开上一轮线程清理竞态
        if getattr(self, "_last_connect_succeeded", False):
            self._last_connect_succeeded = False
            QTimer.singleShot(50, self._auto_connect_enabled_cards)

    def _on_slot_context_menu(self, frame, pos):
        serial = frame.property("assigned_serial")
        if not serial:
            return

        menu = QMenu(self)
        menu.setStyleSheet(dss.INSTR_MENU_STYLE)
        disconnect_action = menu.addAction("Disconnect")
        action = menu.exec(frame.mapToGlobal(pos))
        if action == disconnect_action:
            self._on_device_disconnect(serial)

    def _on_device_card_context_menu(self, card, pos):
        serial = (card.property("serial") or "").strip()
        visa_resource = card.property("visa_resource") or ""
        for slot in self.slot_frames.values():
            if (slot.property("assigned_serial") or "").strip() == serial \
                    or slot.property("assigned_resource") == visa_resource:
                QMessageBox.information(self, "无法删除", "该仪器已连接，请先断开连接后再删除。")
                return
        if visa_resource in self._pending_connects.values():
            QMessageBox.information(self, "无法删除", "该仪器正在连接中，请稍后再试。")
            return

        menu = QMenu(self)
        menu.setStyleSheet(dss.INSTR_MENU_STYLE)
        auto_action = menu.addAction(
            _make_svg_icon("zap.svg", "#d4a514", 14), "Auto Connect"
        )
        auto_action.setCheckable(True)
        auto_action.setChecked(bool(card.property("auto_connect")))
        menu.addSeparator()
        remove_action = menu.addAction(
            _make_svg_icon("x-close.svg", "#d14b72", 14), "Remove"
        )
        action = menu.exec(card.mapToGlobal(pos))
        if action == auto_action:
            self._set_device_auto_connect(card, auto_action.isChecked())
        elif action == remove_action:
            self._remove_device_card(card)

    def _set_device_auto_connect(self, card, enabled):
        enabled = bool(enabled)
        card.setProperty("auto_connect", enabled)
        visa_resource = card.property("visa_resource") or ""
        devices = self._load_default_devices()
        changed = False
        for d in devices:
            if d.get("visa_resource") == visa_resource \
                    and bool(d.get("auto_connect", False)) != enabled:
                d["auto_connect"] = enabled
                changed = True
        if changed:
            path = self._default_devices_path()
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"devices": devices}, f, ensure_ascii=False, indent=2)
            except Exception:
                logger.warning("Update auto_connect in default_devices.json failed", exc_info=True)
        if enabled:
            self._auto_connect_enabled_cards()

    def _auto_connect_enabled_cards(self):
        if not load_datalog_app_settings().get("auto_connect_enabled", True):
            return
        for card in list(self.device_cards):
            if not card.property("auto_connect"):
                continue
            visa_resource = card.property("visa_resource") or ""
            serial = card.property("serial") or ""
            if not visa_resource or visa_resource in self._pending_connects.values():
                continue
            already = any(
                self.slot_frames[l].property("assigned_serial")
                and self.slot_frames[l].property("assigned_resource") == visa_resource
                for l in ["A", "B"]
            )
            if already or self._find_next_free_slot() is None:
                continue
            # 本地连接路径仅单实例线程，等本轮完成后由 _on_connect_thread_done 链式补连
            if self._instrument_manager is None \
                    and getattr(self, "_connect_thread", None) is not None:
                break
            self._on_device_connect(visa_resource, serial)

    def _remove_device_card(self, card):
        visa_resource = card.property("visa_resource") or ""
        if card in self.device_cards:
            self.device_cards.remove(card)
        self.device_list_layout.removeWidget(card)
        card.deleteLater()
        self._remove_default_device(visa_resource)
        self._sync_device_card_states()

    def is_instrument_busy(self, serial, visa_resource):
        """设备已连接或连接中（设置对话框据此禁止删除 / 改地址）。"""
        serial = (serial or "").strip()
        for slot in self.slot_frames.values():
            s = (slot.property("assigned_serial") or "").strip()
            if s and (s == serial or slot.property("assigned_resource") == visa_resource):
                return True
        return visa_resource in self._pending_connects.values()

    def apply_instrument_settings(self, devices, auto_connect_enabled=None):
        """设置对话框提交仪器列表：同步设备卡片（增/删/改属性）并按需触发自动连接。

        devices 为 default_devices.json 的完整新列表；已连接 / 连接中的卡片
        仅更新 auto_connect 属性，不删卡、不改地址。
        """
        new_by_res = {
            d.get("visa_resource"): d for d in devices if d.get("visa_resource")
        }
        busy_serials = set()
        busy_resources = set(self._pending_connects.values())
        for label_char in ["A", "B"]:
            slot = self.slot_frames[label_char]
            s = (slot.property("assigned_serial") or "").strip()
            if s:
                busy_serials.add(s)
                busy_resources.add(slot.property("assigned_resource"))

        for card in list(self.device_cards):
            res = card.property("visa_resource") or ""
            serial = (card.property("serial") or "").strip()
            busy = serial in busy_serials or res in busy_resources
            dev = new_by_res.get(res)
            if dev is None:
                if busy:
                    continue
                self.device_cards.remove(card)
                self.device_list_layout.removeWidget(card)
                card.deleteLater()
                continue
            card.setProperty("auto_connect", bool(dev.get("auto_connect", False)))
            if not busy:
                card.setProperty("serial", dev.get("serial") or res)
                model_label = card.property("model_label")
                ip_label = card.property("ip_label")
                if model_label is not None:
                    model_label.setText(dev.get("model", "N6705C"))
                if ip_label is not None:
                    ip_label.setText(dev.get("display_ip", ""))

        existing_resources = {c.property("visa_resource") for c in self.device_cards}
        for dev in devices:
            res = dev.get("visa_resource")
            if not res or res in existing_resources:
                continue
            card = self._create_device_card(
                dev.get("serial") or res, dev.get("model", "N6705C"),
                dev.get("display_ip", ""), res,
                auto_connect=bool(dev.get("auto_connect", False)),
            )
            self.device_list_layout.insertWidget(
                self.device_list_layout.count() - 1, card
            )
            self.device_cards.append(card)
            existing_resources.add(res)

        self._sync_device_card_states()
        if auto_connect_enabled:
            self._auto_connect_enabled_cards()

    def _on_device_disconnect(self, serial):
        logger.debug("Datalog UI _on_device_disconnect: serial=%s", serial)
        n6705c_to_close = None
        should_close_locally = True
        for label_char in ["A", "B"]:
            slot = self.slot_frames[label_char]
            if slot.property("assigned_serial") == serial:
                self._clear_slot(label_char)

                if label_char == "A":
                    n6705c_to_close = self.n6705c_a
                    self.n6705c_a = None
                    self.is_connected_a = False
                    if self._top:
                        self._top.disconnect_a()
                        should_close_locally = False
                    elif self._instrument_manager:
                        self._instrument_manager.disconnect_async("n6705c:A")
                        should_close_locally = False
                elif label_char == "B":
                    n6705c_to_close = self.n6705c_b
                    self.n6705c_b = None
                    self.is_connected_b = False
                    if self._top:
                        self._top.disconnect_b()
                        should_close_locally = False
                    elif self._instrument_manager:
                        self._instrument_manager.disconnect_async("n6705c:B")
                        should_close_locally = False
                break

        self._after_slot_states_synced()

        if n6705c_to_close and should_close_locally:
            threading.Thread(
                target=self._close_instrument, args=(n6705c_to_close,), daemon=True
            ).start()

    @staticmethod
    def _close_instrument(n6705c):
        try:
            n6705c.disconnect()
        except Exception:
            logger.debug("Close instrument failed", exc_info=True)

    def _assign_slot(self, label_char, serial, model, visa_resource):
        slot = self.slot_frames[label_char]
        slot.setProperty("assigned_serial", serial)
        slot.setProperty("assigned_resource", visa_resource)
        slot.setProperty("connected", True)
        slot.setStyleSheet(dss.SLOT_ASSIGNED_STYLE)
        name_label = slot.property("name_label")
        name_label.setText(f"{model}\n{serial}\n{visa_resource.split('::')[1] if '::' in visa_resource else ''}")
        name_label.setStyleSheet(dss.SLOT_NAME_CONNECTED_STYLE)

        letter = slot.findChildren(QLabel)[0]
        letter.setStyleSheet(dss.SLOT_LETTER_CONNECTED_STYLE)

    def _clear_slot(self, label_char):
        slot = self.slot_frames[label_char]
        slot.setProperty("assigned_serial", "")
        slot.setProperty("assigned_resource", "")
        slot.setProperty("connected", False)
        slot.setStyleSheet("")
        name_label = slot.property("name_label")
        name_label.setText("Not Supported")
        name_label.setStyleSheet(dss.SLOT_NAME_DEFAULT_STYLE)

        letter = slot.findChildren(QLabel)[0]
        letter.setStyleSheet(dss.SLOT_LETTER_DEFAULT_STYLE)

    def _on_add_instrument_manually(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Instrument Manually")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet(dss.dlg_style(combo=True))

        form_layout = QVBoxLayout(dialog)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        title = QLabel("Add Instrument Manually")
        title.setStyleSheet(dss.DIALOG_TITLE_STYLE)
        form_layout.addWidget(title)

        conn_type_label = QLabel("Connection Type")
        form_layout.addWidget(conn_type_label)
        conn_type_combo = QComboBox()
        conn_type_combo.addItems(["TCP/IP (LAN)", "USB"])
        form_layout.addWidget(conn_type_combo)

        ip_label = QLabel("IP Address")
        form_layout.addWidget(ip_label)
        ip_edit = QLineEdit()
        ip_edit.setPlaceholderText("e.g. 192.168.3.99")
        form_layout.addWidget(ip_edit)

        usb_label = QLabel("USB Resource String")
        usb_edit = QLineEdit()
        usb_edit.setPlaceholderText("e.g. USB0::0x2A8D::0x1802::MY56006098::INSTR")
        form_layout.addWidget(usb_label)
        form_layout.addWidget(usb_edit)
        usb_label.hide()
        usb_edit.hide()

        serial_label = QLabel("Serial Number (optional)")
        form_layout.addWidget(serial_label)
        serial_edit = QLineEdit()
        serial_edit.setPlaceholderText("e.g. MY56006098")
        form_layout.addWidget(serial_edit)

        save_default_check = QCheckBox("Save to Default")
        save_default_check.setToolTip(
            "勾选后保存当前地址为默认仪器，下次打开时自动加载常用仪器。"
        )
        save_default_check.setStyleSheet(dss.SAVE_DEFAULT_CB_STYLE)
        form_layout.addWidget(save_default_check)

        def _on_conn_type_changed(index):
            if index == 0:
                ip_label.show()
                ip_edit.show()
                usb_label.hide()
                usb_edit.hide()
            else:
                ip_label.hide()
                ip_edit.hide()
                usb_label.show()
                usb_edit.show()

        conn_type_combo.currentIndexChanged.connect(_on_conn_type_changed)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        connect_btn = QPushButton("Connect")
        connect_btn.setIcon(_make_svg_icon("link-connect.svg", "#ffffff", 14))
        connect_btn.setStyleSheet(dss.PRIMARY_BTN_STYLE)
        connect_btn.clicked.connect(dialog.accept)
        connect_btn.setDefault(True)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(connect_btn)
        form_layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.Accepted:
            return

        conn_index = conn_type_combo.currentIndex()
        serial = serial_edit.text().strip()

        if conn_index == 0:
            ip = ip_edit.text().strip()
            if not ip:
                return
            visa_resource = f"TCPIP0::{ip}::hislip0::INSTR"
            display_ip = ip
        else:
            usb_str = usb_edit.text().strip()
            if not usb_str:
                return
            visa_resource = usb_str
            display_ip = usb_str

        if not serial:
            serial = visa_resource

        existing_serials = {c.property("serial") for c in self.device_cards}
        if serial in existing_serials:
            return

        card = self._create_device_card(serial, "N6705C", display_ip, visa_resource)
        self.device_list_layout.insertWidget(
            self.device_list_layout.count() - 1, card
        )
        self.device_cards.append(card)
        self._sync_device_card_states()

        if save_default_check.isChecked():
            self._save_default_device(serial, "N6705C", display_ip, visa_resource)

    def _add_default_debug_device(self):
        existing_serials = {c.property("serial") for c in self.device_cards}
        if "MY56006098" not in existing_serials:
            card = self._create_device_card(
                "MY56006098", "N6705C", "192.168.3.99",
                "TCPIP0::192.168.3.99::hislip0::INSTR"
            )
            self.device_list_layout.insertWidget(self.device_list_layout.count() - 1, card)
            self.device_cards.append(card)

    # ---- 默认设备持久化（Save to Default）----
    def _default_devices_path(self):
        from resource_path import get_user_data_dir
        return os.path.join(get_user_data_dir("n6705c"), "default_devices.json")

    def _load_default_devices(self):
        path = self._default_devices_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            devices = data.get("devices", []) if isinstance(data, dict) else []
            return [d for d in devices if isinstance(d, dict) and d.get("visa_resource")]
        except Exception:
            logger.debug("Load default_devices.json failed", exc_info=True)
            return []

    def _save_default_device(self, serial, model, display_ip, visa_resource):
        path = self._default_devices_path()
        devices = self._load_default_devices()
        if any(d.get("visa_resource") == visa_resource for d in devices):
            return
        devices.append({
            "serial": serial,
            "model": model,
            "display_ip": display_ip,
            "visa_resource": visa_resource,
            "auto_connect": False,
        })
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"devices": devices}, f, ensure_ascii=False, indent=2)
            logger.debug("Saved default device: %s", visa_resource)
        except Exception:
            logger.warning("Save default_devices.json failed", exc_info=True)

    def _remove_default_device(self, visa_resource):
        if not visa_resource:
            return
        path = self._default_devices_path()
        devices = self._load_default_devices()
        remaining = [d for d in devices if d.get("visa_resource") != visa_resource]
        if len(remaining) == len(devices):
            return
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"devices": remaining}, f, ensure_ascii=False, indent=2)
            logger.debug("Removed default device: %s", visa_resource)
        except Exception:
            logger.warning("Remove default_devices.json failed", exc_info=True)

    def _add_default_saved_devices(self):
        existing_serials = {c.property("serial") for c in self.device_cards}
        existing_resources = {c.property("visa_resource") for c in self.device_cards}
        for d in self._load_default_devices():
            serial = d.get("serial") or d.get("visa_resource")
            # 序列号 + VISA 资源双重去重：连接成功后卡片 serial 已被替换为
            # 真实序列号，仅按 serial 去重会把 serial 回退为资源串的默认
            # 设备重复建卡（已连接设备旁多出一张 Connect 态重复卡）
            if serial in existing_serials \
                    or d["visa_resource"] in existing_resources:
                continue
            card = self._create_device_card(
                serial, d.get("model", "N6705C"),
                d.get("display_ip", ""), d["visa_resource"],
                auto_connect=d.get("auto_connect", False),
            )
            self.device_list_layout.insertWidget(
                self.device_list_layout.count() - 1, card
            )
            self.device_cards.append(card)
            existing_serials.add(serial)
            existing_resources.add(d["visa_resource"])
