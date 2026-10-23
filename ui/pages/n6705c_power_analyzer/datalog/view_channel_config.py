#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pyqtgraph as pg
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QTabBar,
    QVBoxLayout,
    QWidget,
)
from instruments.power.keysight.n6705c_datalog_process import calc_power_for_ch
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.pages.n6705c_power_analyzer.datalog.helpers import (
    CHANNEL_COLORS,
    _display_label,
    _make_svg_icon,
    _parse_ch_label,
    _parse_value_with_unit,
    _sort_key_for_label,
    _unit_for_label,
)
from ui.pages.n6705c_power_analyzer.datalog.widgets import ScaleOffsetEdit, ToggleLabel

class ChannelConfigViewMixin:
    """Datalog 页通道配置视图：Active/导入页签 / 通道开关 / Scale-Offset / 通道名面板。"""

    def _add_channel_config_import_tab(self):
        tab_idx = self.channel_config_tabbar.addTab(_make_svg_icon("plus.svg", "#8eb0e3", 16), "")
        self.channel_config_tabbar.setTabData(tab_idx, "import_plus")
        self.channel_config_tabbar.setTabToolTip(tab_idx, "Import Datalog")
        self._channel_config_import_tab_idx = tab_idx

    def _is_channel_config_import_tab(self, index):
        if index < 0:
            return False
        return self.channel_config_tabbar.tabData(index) == "import_plus"

    def _on_channel_config_tab_changed(self, index):
        if self._is_channel_config_import_tab(index):
            previous = getattr(self, "_channel_config_last_tab_index", 0)
            if previous >= self.channel_config_tabbar.count() or self._is_channel_config_import_tab(previous):
                previous = 0
            self.channel_config_tabbar.blockSignals(True)
            self.channel_config_tabbar.setCurrentIndex(previous)
            self.channel_config_tabbar.blockSignals(False)
            if previous < self.channel_config_stack.count():
                self.channel_config_stack.setCurrentIndex(previous)
            self._on_import()
            return
        if 0 <= index < self.channel_config_stack.count():
            self.channel_config_stack.setCurrentIndex(index)
            self._channel_config_last_tab_index = index

    def _refresh_channel_config(self, force=False):
        connected_slots = []
        for label_char in ["A", "B"]:
            slot = self.slot_frames[label_char]
            if slot.property("assigned_serial"):
                connected_slots.append(label_char)

        signature = tuple(
            (lc, self.slot_frames[lc].property("assigned_serial") or "")
            for lc in connected_slots
        )
        prev_signature = getattr(self, "_ch_cfg_slots_signature", None)
        if not force and prev_signature is not None and prev_signature == signature:
            return
        self._ch_cfg_slots_signature = signature

        preserved_state = self._snapshot_native_channel_state()

        old_inner = self.channel_config_inner
        self._instruments_tab_layout.removeWidget(old_inner)
        old_inner.deleteLater()

        self.channel_config_inner = QWidget()
        self.channel_config_inner.setStyleSheet("background: #071127;")
        inner_layout = QHBoxLayout(self.channel_config_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        self.channel_config_inner_layout = inner_layout

        self.ch_checkboxes_a = []
        self.ch_voltage_cbs_a = []
        self.ch_current_cbs_a = []
        self.ch_power_cbs_a = []
        self.ch_checkboxes_b = []
        self.ch_voltage_cbs_b = []
        self.ch_current_cbs_b = []
        self.ch_power_cbs_b = []

        if not connected_slots:
            self.no_instrument_label.show()
            self._instruments_tab_layout.insertWidget(0, self.channel_config_inner)
            self._instruments_tab_layout.invalidate()
            self._instruments_tab_layout.activate()
            self._instruments_tab.updateGeometry()
            self._instruments_tab.update()
            if self.channel_config_tabbar.count() > 0:
                self.channel_config_tabbar.setCurrentIndex(0)
            return

        self.no_instrument_label.hide()

        for slot_char in connected_slots:
            slot = self.slot_frames[slot_char]
            serial = slot.property("assigned_serial")

            slot_frame = QFrame()
            slot_frame.setStyleSheet(dss.SLOT_FRAME_STYLE)
            slot_layout = QVBoxLayout(slot_frame)
            slot_layout.setContentsMargins(6, 1, 6, 4)
            slot_layout.setSpacing(0)

            slot_title = QLabel(f"Slot {slot_char}  ─  {serial}")
            slot_title.setStyleSheet(dss.SLOT_TITLE_STYLE)
            slot_layout.addWidget(slot_title)

            outputs_row = QHBoxLayout()
            outputs_row.setContentsMargins(0, 0, 0, 0)
            outputs_row.setSpacing(4)
            slot_layout.addLayout(outputs_row)

            voltage_cbs = []
            current_cbs = []
            power_cbs = []

            edit_style = dss.SCALE_OFFSET_EDIT_STYLE

            for ch in range(4):
                ch_color = CHANNEL_COLORS[ch % len(CHANNEL_COLORS)]

                out_frame = QFrame()
                # 仅整行最末槽的最末通道单元格去掉右边框，避免与卡片右边框形成"双线"
                out_frame.setStyleSheet(
                    dss.OUT_FRAME_LAST_STYLE if (ch == 3 and slot_char == connected_slots[-1])
                    else dss.OUT_FRAME_STYLE)
                out_vbox = QVBoxLayout(out_frame)
                out_vbox.setContentsMargins(4, 1, 4, 1)
                out_vbox.setSpacing(2)

                title_lbl = QLabel(f"OUTPUT {ch + 1}")
                title_lbl.setAlignment(Qt.AlignCenter)
                title_lbl.setStyleSheet(dss.out_title_style(ch_color))
                out_vbox.addWidget(title_lbl)

                for row_idx, (prefix, default_scale, default_offset, unit) in enumerate([
                    ("V", "1V", "0V", "V"),
                    ("I", "1mA", "0mA", "mA"),
                    ("P", "1W", "0W", "W"),
                ]):
                    btn = ToggleLabel(f"{prefix}{ch+1}")
                    btn.setFixedWidth(30)
                    btn.setProperty("ch_color", ch_color)
                    btn.setProperty("ch_idx", ch)
                    btn.setProperty("meas_type", prefix)
                    btn.setStyleSheet(self._ch_toggle_style(ch_color, False))
                    btn.toggled.connect(lambda checked, b=btn: self._on_ch_toggle(b, checked))

                    base_unit = {"V": "mV", "I": "mA", "P": "mW"}.get(prefix, "mA")

                    scale_edit = ScaleOffsetEdit(default_scale)
                    scale_edit.setMinimumWidth(38)
                    scale_edit.setAlignment(Qt.AlignCenter)
                    scale_edit.setStyleSheet(edit_style)
                    scale_edit.setProperty("ch_idx", ch)
                    scale_edit.setProperty("meas_type", prefix)
                    scale_edit.setProperty("field", "scale")
                    scale_edit.setProperty("base_unit", base_unit)

                    sep = QLabel("/")
                    sep.setFixedWidth(8)
                    sep.setAlignment(Qt.AlignCenter)
                    sep.setStyleSheet(dss.SEP_LABEL_STYLE)

                    offset_edit = ScaleOffsetEdit(default_offset)
                    offset_edit.setMinimumWidth(38)
                    offset_edit.setAlignment(Qt.AlignCenter)
                    offset_edit.setStyleSheet(edit_style)
                    offset_edit.setProperty("ch_idx", ch)
                    offset_edit.setProperty("meas_type", prefix)
                    offset_edit.setProperty("field", "offset")
                    offset_edit.setProperty("base_unit", base_unit)

                    row_layout = QHBoxLayout()
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(1)
                    row_layout.addWidget(btn)
                    row_layout.addWidget(scale_edit)
                    row_layout.addWidget(sep)
                    row_layout.addWidget(offset_edit)

                    container = QWidget()
                    container.setStyleSheet(dss.CONTAINER_NO_BORDER_STYLE)
                    container.setLayout(row_layout)
                    out_vbox.addWidget(container)

                    scale_edit.returnPressed.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.returnPressed.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))
                    scale_edit.wheel_adjusted.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.wheel_adjusted.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))

                    btn.setProperty("scale_edit", scale_edit)
                    btn.setProperty("offset_edit", offset_edit)
                    btn.setProperty("slot_char", slot_char)
                    btn.setProperty("user_edited", False)

                    if prefix == "V":
                        voltage_cbs.append(btn)
                    elif prefix == "I":
                        current_cbs.append(btn)
                    else:
                        power_cbs.append(btn)

                outputs_row.addWidget(out_frame, 1)

            if slot_char == "A":
                self.ch_checkboxes_a = current_cbs
                self.ch_voltage_cbs_a = voltage_cbs
                self.ch_current_cbs_a = current_cbs
                self.ch_power_cbs_a = power_cbs
            elif slot_char == "B":
                self.ch_checkboxes_b = current_cbs
                self.ch_voltage_cbs_b = voltage_cbs
                self.ch_current_cbs_b = current_cbs
                self.ch_power_cbs_b = power_cbs

            inner_layout.addWidget(slot_frame)

        self._instruments_tab_layout.insertWidget(0, self.channel_config_inner)
        self._instruments_tab_layout.invalidate()
        self._instruments_tab_layout.activate()
        self._instruments_tab.updateGeometry()
        self._instruments_tab.update()
        self.channel_config_stack.updateGeometry()
        self.channel_config_stack.update()
        if self.channel_config_tabbar.count() > 0:
            self.channel_config_tabbar.setCurrentIndex(0)

        self._restore_native_channel_state(preserved_state)

    def _snapshot_native_channel_state(self):
        snapshot = {}
        groups = [
            ("A", "I", self.ch_current_cbs_a),
            ("A", "V", self.ch_voltage_cbs_a),
            ("A", "P", self.ch_power_cbs_a),
            ("B", "I", self.ch_current_cbs_b),
            ("B", "V", self.ch_voltage_cbs_b),
            ("B", "P", self.ch_power_cbs_b),
        ]
        for slot_char, meas_type, buttons in groups:
            for idx, btn in enumerate(buttons):
                try:
                    scale_edit = btn.property("scale_edit")
                    offset_edit = btn.property("offset_edit")
                    snapshot[(slot_char, meas_type, idx)] = {
                        "checked": btn.isChecked(),
                        "user_edited": bool(btn.property("user_edited")),
                        "scale_text": scale_edit.text() if scale_edit else None,
                        "offset_text": offset_edit.text() if offset_edit else None,
                    }
                except RuntimeError:
                    continue
        return snapshot

    def _restore_native_channel_state(self, snapshot):
        if not snapshot:
            return
        groups = [
            ("A", "I", self.ch_current_cbs_a),
            ("A", "V", self.ch_voltage_cbs_a),
            ("A", "P", self.ch_power_cbs_a),
            ("B", "I", self.ch_current_cbs_b),
            ("B", "V", self.ch_voltage_cbs_b),
            ("B", "P", self.ch_power_cbs_b),
        ]
        for slot_char, meas_type, buttons in groups:
            for idx, btn in enumerate(buttons):
                state = snapshot.get((slot_char, meas_type, idx))
                if not state:
                    continue
                scale_edit = btn.property("scale_edit")
                offset_edit = btn.property("offset_edit")
                if scale_edit and state.get("scale_text") is not None:
                    scale_edit.setText(state["scale_text"])
                if offset_edit and state.get("offset_text") is not None:
                    offset_edit.setText(state["offset_text"])
                if state.get("user_edited"):
                    btn.setProperty("user_edited", True)
                if state.get("checked"):
                    btn.blockSignals(True)
                    btn.setChecked(True)
                    ch_color = btn.property("ch_color")
                    if ch_color:
                        btn.setStyleSheet(self._ch_toggle_style(ch_color, True))
                    btn.blockSignals(False)

    def _build_imported_channel_config(self, tab_name=None, data_keys=None, file_prefix=None):
        if data_keys is None:
            data_keys = set(self.datalog_data.keys())

        groups = {}
        for key in data_keys:
            ch_num, mtype, is_b = _parse_ch_label(key)
            if ch_num is None:
                continue
            slot = "B" if is_b else "A"
            groups.setdefault(slot, {})
            groups[slot].setdefault(ch_num, set())
            groups[slot][ch_num].add(mtype)

        if not groups:
            return

        if tab_name is None:
            tab_name = "Imported"

        if file_prefix is None:
            for k in data_keys:
                p = self._get_file_prefix(k)
                if p:
                    file_prefix = p
                    break
            if file_prefix is None:
                file_prefix = ""
        file_prefix = file_prefix.rstrip("-")

        tab_widget = QWidget()
        tab_widget.setStyleSheet("background: #071127;")
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 2, 0, 0)
        tab_layout.setSpacing(0)

        inner = QWidget()
        inner.setStyleSheet("background: #071127;")
        inner_layout = QHBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        tab_config = {
            "tab_name": tab_name,
            "tab_widget": tab_widget,
            "data_keys": set(data_keys),
            "file_prefix": file_prefix,
            "voltage_cbs_a": [],
            "current_cbs_a": [],
            "power_cbs_a": [],
            "voltage_cbs_b": [],
            "current_cbs_b": [],
            "power_cbs_b": [],
        }

        edit_style = dss.SCALE_OFFSET_EDIT_STYLE

        for slot_char in sorted(groups.keys()):
            ch_map = groups[slot_char]
            max_ch = max(ch_map.keys())

            slot_frame = QFrame()
            slot_frame.setStyleSheet(dss.SLOT_FRAME_STYLE)
            slot_layout = QVBoxLayout(slot_frame)
            slot_layout.setContentsMargins(6, 1, 6, 4)
            slot_layout.setSpacing(0)

            slot_title = QLabel(f"{tab_name}  ─  Slot {slot_char}")
            slot_title.setStyleSheet(dss.SLOT_TITLE_STYLE)
            slot_layout.addWidget(slot_title)

            outputs_row = QHBoxLayout()
            outputs_row.setContentsMargins(0, 0, 0, 0)
            outputs_row.setSpacing(4)
            slot_layout.addLayout(outputs_row)

            voltage_cbs = []
            current_cbs = []
            power_cbs = []

            for ch in range(1, max_ch + 1):
                ch_color = CHANNEL_COLORS[(ch - 1) % len(CHANNEL_COLORS)]
                available_types = ch_map.get(ch, set())

                out_frame = QFrame()
                out_frame.setMaximumWidth(260)
                out_frame.setStyleSheet(dss.OUT_FRAME_STYLE)
                out_vbox = QVBoxLayout(out_frame)
                out_vbox.setContentsMargins(4, 1, 4, 1)
                out_vbox.setSpacing(2)

                title_lbl = QLabel(f"OUTPUT {ch}")
                title_lbl.setAlignment(Qt.AlignCenter)
                title_lbl.setStyleSheet(dss.out_title_style(ch_color))
                out_vbox.addWidget(title_lbl)

                for prefix, default_scale, default_offset, unit in [
                    ("V", "1V", "0V", "V"),
                    ("I", "1mA", "0mA", "mA"),
                    ("P", "1W", "0W", "W"),
                ]:
                    if prefix not in available_types:
                        dummy = ToggleLabel(f"{prefix}{ch}")
                        dummy.setFixedWidth(30)
                        dummy.setProperty("ch_color", ch_color)
                        dummy.setProperty("ch_idx", ch - 1)
                        dummy.setProperty("meas_type", prefix)
                        dummy.setStyleSheet(self._ch_toggle_style(ch_color, False))
                        dummy.setEnabled(False)
                        dummy.setStyleSheet(dss.DUMMY_TOGGLE_STYLE)
                        dummy_scale = QLineEdit(default_scale)
                        dummy_scale.setMinimumWidth(38)
                        dummy_scale.setAlignment(Qt.AlignCenter)
                        dummy_scale.setStyleSheet(edit_style)
                        dummy_scale.setEnabled(False)
                        dummy_scale.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        dummy_sep = QLabel("/")
                        dummy_sep.setFixedWidth(8)
                        dummy_sep.setAlignment(Qt.AlignCenter)
                        dummy_sep.setStyleSheet(dss.SEP_LABEL_STYLE)
                        dummy_offset = QLineEdit(default_offset)
                        dummy_offset.setMinimumWidth(38)
                        dummy_offset.setAlignment(Qt.AlignCenter)
                        dummy_offset.setStyleSheet(edit_style)
                        dummy_offset.setEnabled(False)
                        dummy_offset.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                        row_layout = QHBoxLayout()
                        row_layout.setContentsMargins(0, 0, 0, 0)
                        row_layout.setSpacing(1)
                        row_layout.addWidget(dummy)
                        row_layout.addWidget(dummy_scale)
                        row_layout.addWidget(dummy_sep)
                        row_layout.addWidget(dummy_offset)
                        container = QWidget()
                        container.setStyleSheet(dss.CONTAINER_NO_BORDER_STYLE)
                        container.setLayout(row_layout)
                        out_vbox.addWidget(container)
                        if prefix == "V":
                            voltage_cbs.append(dummy)
                        elif prefix == "I":
                            current_cbs.append(dummy)
                        else:
                            power_cbs.append(dummy)
                        dummy.setProperty("scale_edit", dummy_scale)
                        dummy.setProperty("offset_edit", dummy_offset)
                        dummy.setProperty("slot_char", slot_char)
                        dummy.setProperty("user_edited", False)
                        continue

                    btn = ToggleLabel(f"{prefix}{ch}")
                    btn.setFixedWidth(30)
                    btn.setProperty("ch_color", ch_color)
                    btn.setProperty("ch_idx", ch - 1)
                    btn.setProperty("meas_type", prefix)
                    btn.setStyleSheet(self._ch_toggle_style(ch_color, False))
                    btn.toggled.connect(lambda checked, b=btn: self._on_ch_toggle(b, checked))

                    base_unit = {"V": "mV", "I": "mA", "P": "mW"}.get(prefix, "mA")

                    scale_edit = ScaleOffsetEdit(default_scale)
                    scale_edit.setMinimumWidth(38)
                    scale_edit.setAlignment(Qt.AlignCenter)
                    scale_edit.setStyleSheet(edit_style)
                    scale_edit.setProperty("ch_idx", ch - 1)
                    scale_edit.setProperty("meas_type", prefix)
                    scale_edit.setProperty("field", "scale")
                    scale_edit.setProperty("base_unit", base_unit)

                    sep = QLabel("/")
                    sep.setFixedWidth(8)
                    sep.setAlignment(Qt.AlignCenter)
                    sep.setStyleSheet(dss.SEP_LABEL_STYLE)

                    offset_edit = ScaleOffsetEdit(default_offset)
                    offset_edit.setMinimumWidth(38)
                    offset_edit.setAlignment(Qt.AlignCenter)
                    offset_edit.setStyleSheet(edit_style)
                    offset_edit.setProperty("ch_idx", ch - 1)
                    offset_edit.setProperty("meas_type", prefix)
                    offset_edit.setProperty("field", "offset")
                    offset_edit.setProperty("base_unit", base_unit)

                    row_layout = QHBoxLayout()
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(1)
                    row_layout.addWidget(btn)
                    row_layout.addWidget(scale_edit)
                    row_layout.addWidget(sep)
                    row_layout.addWidget(offset_edit)

                    container = QWidget()
                    container.setStyleSheet(dss.CONTAINER_NO_BORDER_STYLE)
                    container.setLayout(row_layout)
                    out_vbox.addWidget(container)

                    scale_edit.returnPressed.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.returnPressed.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))
                    scale_edit.wheel_adjusted.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.wheel_adjusted.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))

                    btn.setProperty("scale_edit", scale_edit)
                    btn.setProperty("offset_edit", offset_edit)
                    btn.setProperty("slot_char", slot_char)
                    btn.setProperty("user_edited", False)

                    if prefix == "V":
                        voltage_cbs.append(btn)
                    elif prefix == "I":
                        current_cbs.append(btn)
                    else:
                        power_cbs.append(btn)

                outputs_row.addWidget(out_frame)

            outputs_row.addStretch()

            if slot_char == "A":
                tab_config["voltage_cbs_a"] = voltage_cbs
                tab_config["current_cbs_a"] = current_cbs
                tab_config["power_cbs_a"] = power_cbs
            elif slot_char == "B":
                tab_config["voltage_cbs_b"] = voltage_cbs
                tab_config["current_cbs_b"] = current_cbs
                tab_config["power_cbs_b"] = power_cbs

            inner_layout.addWidget(slot_frame)

        tab_layout.addWidget(inner)
        tab_layout.addStretch()

        self._imported_tab_configs.append(tab_config)
        tab_idx = self.channel_config_tabbar.count()
        if self._is_channel_config_import_tab(tab_idx - 1):
            tab_idx -= 1
        tab_idx = self.channel_config_tabbar.insertTab(tab_idx, f"{tab_name}")
        self.channel_config_tabbar.setTabData(tab_idx, "imported")
        self.channel_config_tabbar.setTabIcon(tab_idx, _make_svg_icon("file-text.svg", "#8eb0e3", 14))
        self.channel_config_stack.insertWidget(tab_idx, tab_widget)
        close_btn = QPushButton()
        close_btn.setIcon(_make_svg_icon("x-close.svg", "#4a6a96", 12))
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(dss.CH_CFG_TAB_CLOSE_BTN_STYLE)
        close_btn.clicked.connect(lambda _checked=False, w=tab_widget: self._on_config_tab_close(
            self.channel_config_stack.indexOf(w)))
        self.channel_config_tabbar.setTabButton(tab_idx, QTabBar.RightSide, close_btn)
        tab_config["close_btn"] = close_btn
        self.channel_config_tabbar.setCurrentIndex(tab_idx)

    def _on_config_tab_close(self, index):
        if index <= 0 or self._is_channel_config_import_tab(index):
            return
        widget = self.channel_config_stack.widget(index)
        if widget is None:
            return
        tc_to_remove = None
        for tc in self._imported_tab_configs:
            if tc.get("tab_widget") is widget:
                tc_to_remove = tc
                break
        if tc_to_remove:
            removed_keys = tc_to_remove.get("data_keys", set())
            removed_prefix = tc_to_remove.get("file_prefix", "")
            self._imported_tab_configs.remove(tc_to_remove)
            if removed_prefix:
                still_used_prefix = any(
                    tc.get("file_prefix") == removed_prefix for tc in self._imported_tab_configs
                )
                if not still_used_prefix:
                    self._file_time_offsets.pop(removed_prefix, None)
                    self._tab_hidden_snapshot.pop(f"__file__:{removed_prefix}", None)
            still_used = set()
            for tc in self._imported_tab_configs:
                still_used |= tc.get("data_keys", set())
            actually_removed = set()
            for k in removed_keys:
                if k not in still_used:
                    self.datalog_data.pop(k, None)
                    self.ch_name_renames.pop(k, None)
                    self._known_data_keys.discard(k)
                    actually_removed.add(k)
            if actually_removed:
                self.custom_labels = [
                    lbl for lbl in self.custom_labels
                    if lbl.get("channel", "") not in actually_removed
                ]
        target_index = index - 1
        if target_index < 0 or self._is_channel_config_import_tab(target_index):
            target_index = 0
        self.channel_config_tabbar.blockSignals(True)
        self.channel_config_tabbar.setCurrentIndex(target_index)
        self.channel_config_tabbar.removeTab(index)
        self.channel_config_tabbar.blockSignals(False)
        self.channel_config_stack.removeWidget(widget)
        if widget:
            widget.deleteLater()
        current_index = self.channel_config_tabbar.currentIndex()
        if self._is_channel_config_import_tab(current_index):
            current_index = 0
            self.channel_config_tabbar.blockSignals(True)
            self.channel_config_tabbar.setCurrentIndex(current_index)
            self.channel_config_tabbar.blockSignals(False)
        if 0 <= current_index < self.channel_config_stack.count():
            self.channel_config_stack.setCurrentIndex(current_index)
        self._channel_config_last_tab_index = current_index
        self._refresh_plot()

    def _get_tab_cbs(self, index):
        if index <= 0:
            return (
                list(self.ch_current_cbs_a)
                + list(self.ch_voltage_cbs_a)
                + list(self.ch_power_cbs_a)
                + list(self.ch_current_cbs_b)
                + list(self.ch_voltage_cbs_b)
                + list(self.ch_power_cbs_b)
            )
        widget = self.channel_config_stack.widget(index)
        if widget is None:
            return []
        for tc in self._imported_tab_configs:
            if tc.get("tab_widget") is widget:
                return (
                    list(tc.get("current_cbs_a", []))
                    + list(tc.get("voltage_cbs_a", []))
                    + list(tc.get("power_cbs_a", []))
                    + list(tc.get("current_cbs_b", []))
                    + list(tc.get("voltage_cbs_b", []))
                    + list(tc.get("power_cbs_b", []))
                )
        return []

    def _get_tab_file_prefix(self, index):
        if index <= 0:
            return ""
        widget = self.channel_config_stack.widget(index)
        if widget is None:
            return ""
        for tc in self._imported_tab_configs:
            if tc.get("tab_widget") is widget:
                return tc.get("file_prefix", "") or ""
        return ""

    def _get_tab_data_keys(self, index):
        if index <= 0:
            imported_keys = set()
            for tc in self._imported_tab_configs:
                imported_keys |= tc.get("data_keys", set())
            return set(self.datalog_data.keys()) - imported_keys
        widget = self.channel_config_stack.widget(index)
        if widget is None:
            return set()
        for tc in self._imported_tab_configs:
            if tc.get("tab_widget") is widget:
                return set(tc.get("data_keys", set())) & set(self.datalog_data.keys())
        return set()

    def _get_tab_snapshot_key(self, index):
        if index <= 0:
            return "__active__"
        widget = self.channel_config_stack.widget(index)
        if widget is None:
            return None
        for tc in self._imported_tab_configs:
            if tc.get("tab_widget") is widget:
                prefix = tc.get("file_prefix") or ""
                return f"__file__:{prefix}" if prefix else None
        return None

    def _is_tab_any_channel_visible(self, index):
        cbs = self._get_tab_cbs(index)
        for cb in cbs:
            if cb.isChecked():
                return True
        return False

    def _capture_tab_checked_cbs(self, index):
        cbs = self._get_tab_cbs(index)
        captured = set()
        for cb in cbs:
            if cb.isChecked():
                ch_idx = cb.property("ch_idx")
                mtype = cb.property("meas_type")
                if ch_idx is None or mtype is None:
                    continue
                is_b_cb = self._cb_is_b(cb)
                captured.add((int(ch_idx), str(mtype), bool(is_b_cb)))
        return captured

    def _cb_is_b(self, cb):
        if cb in (
            list(self.ch_current_cbs_b)
            + list(self.ch_voltage_cbs_b)
            + list(self.ch_power_cbs_b)
        ):
            return True
        for tc in self._imported_tab_configs:
            if cb in (
                list(tc.get("current_cbs_b", []))
                + list(tc.get("voltage_cbs_b", []))
                + list(tc.get("power_cbs_b", []))
            ):
                return True
        return False

    def _hide_tab_channels(self, index):
        cbs = self._get_tab_cbs(index)
        if not cbs:
            return
        snapshot_key = self._get_tab_snapshot_key(index)
        if snapshot_key:
            self._tab_hidden_snapshot[snapshot_key] = self._capture_tab_checked_cbs(index)
        changed = False
        for cb in cbs:
            if cb.isChecked():
                cb.blockSignals(True)
                cb.setChecked(False)
                ch_color = cb.property("ch_color")
                if ch_color:
                    cb.setStyleSheet(self._ch_toggle_style(ch_color, False))
                cb.blockSignals(False)
                changed = True
        if changed:
            self._on_channel_visibility_changed()

    def _hide_other_tab_channels(self, keep_index):
        total = self.channel_config_tabbar.count()
        if total <= 1:
            return
        changed_any = False
        for i in range(total):
            if i == keep_index:
                continue
            cbs = self._get_tab_cbs(i)
            if not cbs:
                continue
            snapshot_key = self._get_tab_snapshot_key(i)
            if snapshot_key:
                captured = self._capture_tab_checked_cbs(i)
                if captured:
                    self._tab_hidden_snapshot[snapshot_key] = captured
            changed = False
            for cb in cbs:
                if cb.isChecked():
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    ch_color = cb.property("ch_color")
                    if ch_color:
                        cb.setStyleSheet(self._ch_toggle_style(ch_color, False))
                    cb.blockSignals(False)
                    changed = True
            if changed:
                changed_any = True
        if changed_any:
            self._on_channel_visibility_changed()

    def _show_tab_channels(self, index):
        cbs = self._get_tab_cbs(index)
        if not cbs:
            return
        data_keys = self._get_tab_data_keys(index)
        active_combos = set()
        for key in data_keys:
            ch_num, mtype, is_b = _parse_ch_label(key)
            if ch_num is None or ch_num < 1 or ch_num > 4:
                continue
            active_combos.add((ch_num - 1, mtype, is_b))

        snapshot_key = self._get_tab_snapshot_key(index)
        snapshot = self._tab_hidden_snapshot.get(snapshot_key) if snapshot_key else None
        if snapshot:
            target = snapshot & active_combos
        else:
            target = active_combos

        if snapshot_key:
            self._tab_hidden_snapshot.pop(snapshot_key, None)

        changed = False
        for cb in cbs:
            ch_idx = cb.property("ch_idx")
            mtype = cb.property("meas_type")
            if ch_idx is None or mtype is None:
                continue
            combo = (int(ch_idx), str(mtype), bool(self._cb_is_b(cb)))
            want = combo in target
            if cb.isChecked() != want:
                cb.blockSignals(True)
                cb.setChecked(want)
                ch_color = cb.property("ch_color")
                if ch_color:
                    cb.setStyleSheet(self._ch_toggle_style(ch_color, want))
                cb.blockSignals(False)
                changed = True
        if changed:
            self._on_channel_visibility_changed()

    def _on_ch_tabbar_context_menu(self, pos):
        index = self.channel_config_tabbar.tabAt(pos)
        if index < 0 or self._is_channel_config_import_tab(index):
            return

        data_keys = self._get_tab_data_keys(index)
        if not data_keys:
            return

        any_visible = self._is_tab_any_channel_visible(index)

        menu = QMenu(self)
        menu.setStyleSheet(dss.menu_style(small=True))

        tab_text = self.channel_config_tabbar.tabText(index)
        title_action = menu.addAction(tab_text or "Tab")
        title_action.setEnabled(False)
        menu.addSeparator()

        if any_visible:
            toggle_action = menu.addAction("Hide Channels")
        else:
            toggle_action = menu.addAction("Show Channels")

        hide_others_action = None
        if self.channel_config_tabbar.count() > 1:
            any_other_visible = False
            for i in range(self.channel_config_tabbar.count()):
                if i == index:
                    continue
                if self._is_tab_any_channel_visible(i):
                    any_other_visible = True
                    break
            hide_others_action = menu.addAction("Hide Others")
            hide_others_action.setEnabled(any_other_visible)

        offset_action = None
        file_prefix = self._get_tab_file_prefix(index)
        if file_prefix:
            menu.addSeparator()
            offset_action = menu.addAction("Time Offset...")
            current_off_s = self._file_time_offsets.get(file_prefix, 0.0)
            if current_off_s != 0.0:
                offset_action.setText(f"Time Offset...  ({current_off_s * 1000.0:+.3f} ms)")

        global_pos = self.channel_config_tabbar.mapToGlobal(pos)
        action = menu.exec(global_pos)
        if action is None:
            return
        if action is toggle_action:
            if any_visible:
                self._hide_tab_channels(index)
            else:
                self._show_tab_channels(index)
        elif hide_others_action is not None and action is hide_others_action:
            self._hide_other_tab_channels(index)
        elif offset_action is not None and action is offset_action:
            self._on_file_time_offset(file_prefix)

    def _ch_toggle_style(self, color, active):
        if active:
            return (
                f"background-color: {color}; color: #ffffff; "
                f"font-size: 10px; font-weight: 800; "
                f"border: 1px solid {color}; border-radius: 1px;"
            )
        else:
            return (
                "background-color: #152040; color: #8eb0e3; "
                "font-size: 10px; font-weight: 700; "
                "border: 1px solid #1e3460; border-radius: 1px;"
            )

    def _on_ch_toggle(self, btn, checked):
        ch_color = btn.property("ch_color")
        btn.setStyleSheet(self._ch_toggle_style(ch_color, checked))
        self._validate_sample_period()

        if checked and btn.property("meas_type") == "P" and self.datalog_data:
            ch_idx = btn.property("ch_idx")
            ch = ch_idx + 1
            slot_char = btn.property("slot_char") or "A"
            is_b_target = (slot_char == "B")
            matched = False
            for key in list(self.datalog_data.keys()):
                c_num, c_type, c_is_b = _parse_ch_label(key)
                if c_num == ch and c_type == "V" and c_is_b == is_b_target:
                    pfx_m = re.match(r'^(F\d+-)?', key.strip())
                    pfx = pfx_m.group(1) if pfx_m and pfx_m.group(1) else ""
                    raw_part = key.strip()[len(pfx):]
                    if "CH" in raw_part:
                        p_key = f"{pfx}{raw_part.replace(' V', ' P')}"
                        if p_key not in self.datalog_data:
                            calc_power_for_ch(self.datalog_data, ch,
                                              raw_part.split("CH")[0].strip(),
                                              key_prefix=pfx)
                    else:
                        dm = re.match(r'^([AB])\s*[-_]\s*V(\d+)$', raw_part)
                        if dm:
                            p_key = f"{pfx}{dm.group(1)}-P{dm.group(2)}"
                            if p_key not in self.datalog_data:
                                v_key_int = None
                                i_key_int = None
                                for dk in self.datalog_data:
                                    dn, dt, db = _parse_ch_label(dk)
                                    if dn == ch and db == is_b_target:
                                        if dt == "V":
                                            v_key_int = dk
                                        elif dt == "I":
                                            i_key_int = dk
                                if v_key_int and i_key_int:
                                    v_vals = self.datalog_data[v_key_int]["values"]
                                    i_vals = self.datalog_data[i_key_int]["values"]
                                    t = self.datalog_data[v_key_int]["time"]
                                    p_vals = [v * i / 1000.0 for v, i in zip(v_vals, i_vals)]
                                    self.datalog_data[p_key] = {"time": t, "values": p_vals}
                        else:
                            p_key = None
                    if p_key and p_key in self.datalog_data:
                        matched = True
            if matched:
                self._refresh_plot()
                return

        self._on_channel_visibility_changed()

    def _find_all_cbs_for_key(self, data_key):
        ch_num, mtype, is_b = _parse_ch_label(data_key)
        if ch_num is None:
            return []
        slot_char = "B" if is_b else "A"
        prefix = mtype if mtype else "I"
        idx = ch_num - 1

        imported_keys = set()
        for tc in self._imported_tab_configs:
            imported_keys |= tc.get("data_keys", set())

        results = []

        if data_key not in imported_keys:
            src = {
                "voltage_a": self.ch_voltage_cbs_a,
                "current_a": self.ch_current_cbs_a,
                "power_a": self.ch_power_cbs_a,
                "voltage_b": self.ch_voltage_cbs_b,
                "current_b": self.ch_current_cbs_b,
                "power_b": self.ch_power_cbs_b,
            }
            cbs = self._pick_cbs_from_src(src, slot_char, prefix)
            if 0 <= idx < len(cbs):
                results.append(cbs[idx])

        for tc in self._imported_tab_configs:
            if data_key in tc.get("data_keys", set()):
                src = {
                    "voltage_a": tc.get("voltage_cbs_a", []),
                    "current_a": tc.get("current_cbs_a", []),
                    "power_a": tc.get("power_cbs_a", []),
                    "voltage_b": tc.get("voltage_cbs_b", []),
                    "current_b": tc.get("current_cbs_b", []),
                    "power_b": tc.get("power_cbs_b", []),
                }
                cbs = self._pick_cbs_from_src(src, slot_char, prefix)
                if 0 <= idx < len(cbs):
                    results.append(cbs[idx])
        return results

    @staticmethod
    def _pick_cbs_from_src(src, slot_char, prefix):
        if slot_char == "A":
            if prefix == "V":
                return src["voltage_a"]
            elif prefix == "P":
                return src["power_a"]
            else:
                return src["current_a"]
        else:
            if prefix == "V":
                return src["voltage_b"]
            elif prefix == "P":
                return src["power_b"]
            else:
                return src["current_b"]

    def _get_ch_scale_offset(self, data_key):
        btns = self._find_all_cbs_for_key(data_key)
        if not btns:
            return None, None, False

        btn = btns[0]
        user_edited = btn.property("user_edited") or False
        scale_edit = btn.property("scale_edit")
        offset_edit = btn.property("offset_edit")
        if not scale_edit or not offset_edit:
            return None, None, False

        scale_val = _parse_value_with_unit(scale_edit.text(), _unit_for_label(data_key))
        offset_val = _parse_value_with_unit(offset_edit.text(), _unit_for_label(data_key))
        return scale_val, offset_val, user_edited

    def _set_ch_scale_offset_text(self, data_key, scale_text, offset_text):
        btns = self._find_all_cbs_for_key(data_key)
        for btn in btns:
            scale_edit = btn.property("scale_edit")
            offset_edit = btn.property("offset_edit")
            if scale_edit:
                scale_edit.setText(scale_text)
            if offset_edit:
                offset_edit.setText(offset_text)
            btn.setProperty("user_edited", False)

    def _on_scale_offset_edited(self, edit_widget):
        ch_idx = edit_widget.property("ch_idx")
        meas_type = edit_widget.property("meas_type")
        field = edit_widget.property("field")

        all_btn_lists = [
            self.ch_voltage_cbs_a,
            self.ch_current_cbs_a,
            self.ch_power_cbs_a,
            self.ch_voltage_cbs_b,
            self.ch_current_cbs_b,
            self.ch_power_cbs_b,
        ]
        for tc in self._imported_tab_configs:
            for suffix in ["voltage_cbs_a", "current_cbs_a", "power_cbs_a",
                           "voltage_cbs_b", "current_cbs_b", "power_cbs_b"]:
                all_btn_lists.append(tc.get(suffix, []))
        for btn_list in all_btn_lists:
            for btn in btn_list:
                if btn.property("ch_idx") == ch_idx and btn.property("meas_type") == meas_type:
                    btn.setProperty("user_edited", True)
                    break

        self._on_scale_offset_changed()

    def _on_scale_offset_changed(self):
        if not self.datalog_data:
            return

        visible_keys = self._get_visible_keys()
        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        visible_sorted = [k for k in sorted_keys if k in visible_keys]
        n = len(visible_sorted)
        if n == 0:
            return

        band_edges = self._compute_band_edges(n)

        for idx, key in enumerate(visible_sorted):
            ch_data = self.datalog_data[key]
            raw_vals = ch_data["values"]
            if not raw_vals:
                continue

            scale_val, offset_val, user_edited = self._get_ch_scale_offset(key)

            band_top, band_bottom = band_edges[idx]
            margin = (band_top - band_bottom) * 0.08
            plot_top = band_top - margin
            plot_bottom = band_bottom + margin
            plot_range = plot_top - plot_bottom

            if user_edited and scale_val and scale_val > 0 and offset_val is not None:
                num_divs = 5
                half_range = scale_val * num_divs
                display_min = offset_val - half_range
                display_max = offset_val + half_range
                display_range = display_max - display_min
                if display_range == 0:
                    display_range = 1.0

                norm_vals = plot_bottom + (np.asarray(raw_vals, dtype=np.float64) - display_min) * (plot_range / display_range)

                self._band_info[key] = {
                    "raw_min": display_min,
                    "raw_max": display_max,
                    "raw_range": display_range,
                    "band_top": band_top,
                    "band_bottom": band_bottom,
                    "plot_top": plot_top,
                    "plot_bottom": plot_bottom,
                    "plot_range": plot_range,
                    "init_raw_min": display_min,
                    "init_raw_range": display_range,
                }
            else:
                raw_min = min(raw_vals)
                raw_max = max(raw_vals)
                raw_range = raw_max - raw_min
                if raw_range == 0:
                    raw_range = 1.0

                norm_vals = plot_bottom + (np.asarray(raw_vals, dtype=np.float64) - raw_min) * (plot_range / raw_range)

                self._band_info[key] = {
                    "raw_min": raw_min,
                    "raw_max": raw_max,
                    "raw_range": raw_range,
                    "band_top": band_top,
                    "band_bottom": band_bottom,
                    "plot_top": plot_top,
                    "plot_bottom": plot_bottom,
                    "plot_range": plot_range,
                    "init_raw_min": raw_min,
                    "init_raw_range": raw_range,
                }

            curve = self.plot_curves.get(key)
            if curve:
                times = self._get_effective_times(key, ch_data["time"])
                curve.setData(times, norm_vals)
                curve.resetTransform()

        self._update_band_zero_lines()
        self._update_marker_analysis()

    def _rebuild_ch_name_panel(self, entries):
        for item in self._ch_label_items:
            try:
                self.plot_widget.removeItem(item)
            except Exception:
                pass
        self._ch_label_items.clear()
        for line in self._band_grid_lines:
            try:
                self.plot_widget.removeItem(line)
            except Exception:
                pass
        self._band_grid_lines.clear()
        for line in self._band_zero_lines.values():
            try:
                self.plot_widget.removeItem(line)
            except Exception:
                pass
        self._band_zero_lines.clear()

        left_axis = self.plot_widget.getPlotItem().getAxis("left")
        left_axis.setWidth(0)
        left_axis.setTicks([])

        if not entries:
            return

        for key, color in entries:
            display = self.ch_name_renames.get(key, _display_label(key))
            band = self._band_info.get(key)
            if band:
                y_center = (band["plot_top"] + band["plot_bottom"]) / 2
            else:
                y_center = 0.5

            text_item = pg.TextItem(
                html=f"<div style='background:#071127; padding:1px 6px 1px 2px; border-radius:1px;'>"
                     f"<span style='color:{color}; font-size:12px; font-weight:700;'>"
                     f"{display}</span></div>",
                anchor=(0, 0.5),
            )
            text_item.setZValue(200)
            self.plot_widget.addItem(text_item, ignoreBounds=True)
            text_item.setProperty("y_center", y_center)
            text_item.setProperty("ch_key", key)
            self._ch_label_items.append(text_item)

        # 纵轴 scale 网格：8 格均分点线
        self._rebuild_band_grid_lines()

        vb = self.plot_widget.getPlotItem().getViewBox()
        # pyqtgraph 对未连接的 slot 调 disconnect 不抛异常而是 RuntimeWarning，
        # 首次 rebuild 时 slot 尚未连接，用标志位跳过无效 disconnect。
        if self._ch_label_range_connected:
            try:
                vb.sigRangeChanged.disconnect(self._update_ch_label_positions)
            except Exception:
                pass
            self._ch_label_range_connected = False
        vb.sigRangeChanged.connect(self._update_ch_label_positions)
        self._ch_label_range_connected = True
        self._update_ch_label_positions()
        self._update_band_zero_lines()

    def _update_ch_label_positions(self, *args):
        vb = self.plot_widget.getPlotItem().getViewBox()
        x_min, _ = vb.viewRange()[0]
        for item in self._ch_label_items:
            try:
                y_center = item.property("y_center")
            except Exception:
                y_center = 0.5
            key = item.property("ch_key")
            if key:
                curve = self.plot_curves.get(key)
                if curve:
                    t = curve.transform()
                    y_center = t.m22() * y_center + t.dy()
            item.setPos(x_min, y_center)

    def _on_ch_name_renamed(self, key, new_name):
        self.ch_name_renames[key] = new_name
