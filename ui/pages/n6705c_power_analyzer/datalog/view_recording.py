#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import os
import time
from PySide6.QtCore import QThread, QTimer
from debug_config import DEBUG_MOCK
from instruments.power.keysight.n6705c_datalog_process import compute_power_channels
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.pages.n6705c_power_analyzer.n6705c_settings_dialog import build_auto_save_paths, load_datalog_app_settings, save_datalog_app_settings
from ui.widgets.toast_notification import ToastNotification
from ui.pages.n6705c_power_analyzer.datalog.helpers import (
    _auto_format,
    _color_for_label,
    _make_svg_icon,
    _parse_ch_label,
    _sort_key_for_label,
    _unit_for_label,
)
from ui.pages.n6705c_power_analyzer.datalog.workers import _DatalogWorker
from log_config import get_logger

logger = get_logger(__name__)

class RecordingViewMixin:
    """Datalog 页录制视图：录制启停 / Worker 接线 / 通道可见性 / 波形数据访问。"""

    def _update_recording_button_state(self, recording):
        self.is_recording = recording
        self.start_btn.setProperty("running", "true" if recording else "false")
        if recording:
            self.start_btn.setIcon(_make_svg_icon("square.svg", "#ffd9e6", 14))
            self.start_btn.setText("Stop Recording")
        else:
            self.start_btn.setIcon(_make_svg_icon("play.svg", "#ffffff", 16))
            self.start_btn.setText("Start Recording")
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        self.start_btn.update()

    def _show_progress_overlay(self, total_seconds):
        self._progress_bar.setValue(0)
        self._progress_stage_label.setText("Preparing...")
        self._progress_time_label.setText(f"Estimated total: {total_seconds:.0f}s")
        self._progress_total_s = total_seconds
        self._progress_start_time = time.time()
        self._progress_overlay.setGeometry(self.chart_frame.rect())
        self._progress_overlay.raise_()
        self._progress_overlay.show()

        self.plot_widget.setEnabled(False)
        self.channel_config_toggle_btn.setEnabled(False)
        self.channel_config_card.setEnabled(False)
        self._channel_config_overlay.setGeometry(self.channel_config_card.rect())
        self._channel_config_overlay.raise_()
        self._channel_config_overlay.show()

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(500)
        self._progress_timer.timeout.connect(self._update_progress_elapsed)
        self._progress_timer.start()

    def _update_progress_elapsed(self):
        elapsed = time.time() - self._progress_start_time
        remaining = max(0, self._progress_total_s - elapsed)
        if remaining > 0:
            self._progress_time_label.setText(
                f"Elapsed: {elapsed:.0f}s / ~{self._progress_total_s:.0f}s  |  Remaining: ~{remaining:.0f}s"
            )
        else:
            self._progress_time_label.setText(
                f"Elapsed: {elapsed:.0f}s / ~{self._progress_total_s:.0f}s  |  Finishing..."
            )

    def _hide_progress_overlay(self):
        if hasattr(self, '_progress_timer') and self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer = None
        self._progress_overlay.hide()
        self._channel_config_overlay.hide()
        self.plot_widget.setEnabled(True)
        self.channel_config_toggle_btn.setEnabled(True)
        self.channel_config_card.setEnabled(True)

    def _on_worker_progress(self, pct, stage):
        self._progress_bar.setValue(pct)
        self._progress_stage_label.setText(stage)

    def _on_record_type_changed(self):
        if self.type_current.isChecked():
            self.plot_widget.setLabel("left", "", color="#8eb0e3")
        else:
            self.plot_widget.setLabel("left", "", color="#8eb0e3")
        self._clear_analysis_card_cache()
        self._update_marker_analysis()

    def _get_visible_keys(self):
        imported_keys = set()
        for tc in self._imported_tab_configs:
            imported_keys |= tc.get("data_keys", set())
        active_data = {k: v for k, v in self.datalog_data.items() if k not in imported_keys}

        visible_keys = set()
        self._collect_visible_keys_from_cbs(
            visible_keys,
            self.ch_current_cbs_a, self.ch_voltage_cbs_a,
            self.ch_power_cbs_a,
            self.ch_current_cbs_b,
            self.ch_voltage_cbs_b,
            self.ch_power_cbs_b,
            active_data,
        )
        for tc in self._imported_tab_configs:
            tc_keys = tc.get("data_keys", set())
            sub_data = {k: v for k, v in self.datalog_data.items() if k in tc_keys}
            self._collect_visible_keys_from_cbs(
                visible_keys,
                tc.get("current_cbs_a", []), tc.get("voltage_cbs_a", []),
                tc.get("power_cbs_a", []),
                tc.get("current_cbs_b", []), tc.get("voltage_cbs_b", []),
                tc.get("power_cbs_b", []),
                sub_data,
            )
        return visible_keys

    def _collect_visible_keys_from_cbs(self, visible_keys,
                                        current_a, voltage_a, power_a,
                                        current_b, voltage_b, power_b,
                                        data_dict):
        cb_groups = [
            (current_a, "I", False),
            (voltage_a, "V", False),
            (power_a, "P", False),
            (current_b, "I", True),
            (voltage_b, "V", True),
            (power_b, "P", True),
        ]
        for cbs, target_mtype, target_is_b in cb_groups:
            for i, cb in enumerate(cbs):
                if cb.isChecked():
                    ch = i + 1
                    for key in data_dict:
                        ch_num, mtype, is_b = _parse_ch_label(key)
                        if ch_num == ch and mtype == target_mtype and is_b == target_is_b:
                            visible_keys.add(key)

    def _on_channel_visibility_changed(self):
        if not self.datalog_data:
            return

        self._deselect_channel()

        visible_keys = self._get_visible_keys()
        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        visible_sorted = [k for k in sorted_keys if k in visible_keys]
        n = len(visible_sorted)

        for key, curve in self.plot_curves.items():
            curve.setVisible(key in visible_keys)

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

        self._band_info = {}

        if n == 0:
            for item in self._ch_label_items:
                item.setVisible(False)
            return

        band_edges = self._compute_band_edges(n)

        for idx, key in enumerate(visible_sorted):
            ch_data = self.datalog_data[key]
            raw_vals = ch_data["values"]
            if not raw_vals:
                continue

            raw_min = min(raw_vals)
            raw_max = max(raw_vals)
            raw_range = raw_max - raw_min
            if raw_range == 0:
                raw_range = 1.0

            band_top, band_bottom = band_edges[idx]
            margin = (band_top - band_bottom) * 0.08
            plot_top = band_top - margin
            plot_bottom = band_bottom + margin
            plot_range = plot_top - plot_bottom

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

            raw_center = (raw_min + raw_max) / 2
            raw_div = raw_range / 5
            ch_unit = _unit_for_label(key)
            scale_str = _auto_format(raw_div, ch_unit)
            offset_str = _auto_format(raw_center, ch_unit)
            self._set_ch_scale_offset_text(key.strip(), scale_str, offset_str)

        panel_entries = [(k, _color_for_label(k)) for k in visible_sorted]
        self._rebuild_ch_name_panel(panel_entries)
        y_bottom, y_top = self._compute_y_range_with_labels()
        self.plot_widget.setYRange(y_bottom, y_top)
        self._update_marker_analysis()
        self._update_x_limits()

    def _sync_checkboxes_to_data(self):
        all_cbs = (
            list(self.ch_current_cbs_a) +
            list(self.ch_voltage_cbs_a) +
            list(self.ch_power_cbs_a) +
            list(self.ch_current_cbs_b) +
            list(self.ch_voltage_cbs_b) +
            list(self.ch_power_cbs_b)
        )
        for tc in self._imported_tab_configs:
            for suffix in ["current_cbs_a", "voltage_cbs_a", "power_cbs_a",
                           "current_cbs_b", "voltage_cbs_b", "power_cbs_b"]:
                all_cbs += list(tc.get(suffix, []))

        current_keys = set(self.datalog_data.keys())
        new_keys = current_keys - self._known_data_keys

        imported_keys = set()
        for tc in self._imported_tab_configs:
            imported_keys |= tc.get("data_keys", set())
        active_data = {k: v for k, v in self.datalog_data.items() if k not in imported_keys}

        active_new_keys = {k for k in active_data.keys() if k in new_keys}
        self._sync_cbs_for_data(
            active_data,
            self.ch_current_cbs_a, self.ch_voltage_cbs_a,
            self.ch_power_cbs_a,
            self.ch_current_cbs_b,
            self.ch_voltage_cbs_b,
            self.ch_power_cbs_b,
            new_keys=active_new_keys,
        )

        for tc in self._imported_tab_configs:
            tc_keys = tc.get("data_keys", set())
            sub_data = {k: v for k, v in self.datalog_data.items() if k in tc_keys}
            sub_new_keys = {k for k in sub_data.keys() if k in new_keys}
            self._sync_cbs_for_data(
                sub_data,
                tc.get("current_cbs_a", []), tc.get("voltage_cbs_a", []),
                tc.get("power_cbs_a", []),
                tc.get("current_cbs_b", []), tc.get("voltage_cbs_b", []),
                tc.get("power_cbs_b", []),
                new_keys=sub_new_keys,
            )

        self._known_data_keys = current_keys

    def _iter_channel_toggle_buttons(self):
        groups = [
            ("A", "I", self.ch_current_cbs_a),
            ("A", "V", self.ch_voltage_cbs_a),
            ("A", "P", self.ch_power_cbs_a),
            ("B", "I", self.ch_current_cbs_b),
            ("B", "V", self.ch_voltage_cbs_b),
            ("B", "P", self.ch_power_cbs_b),
        ]
        for tab_idx, tc in enumerate(getattr(self, '_imported_tab_configs', [])):
            groups.extend([
                (f"F{tab_idx}:A", "I", tc.get("current_cbs_a", [])),
                (f"F{tab_idx}:A", "V", tc.get("voltage_cbs_a", [])),
                (f"F{tab_idx}:A", "P", tc.get("power_cbs_a", [])),
                (f"F{tab_idx}:B", "I", tc.get("current_cbs_b", [])),
                (f"F{tab_idx}:B", "V", tc.get("voltage_cbs_b", [])),
                (f"F{tab_idx}:B", "P", tc.get("power_cbs_b", [])),
            ])
        for slot_key, meas_type, buttons in groups:
            for idx, btn in enumerate(buttons):
                yield (slot_key, meas_type, idx), btn

    def _snapshot_channel_toggle_states(self):
        return {
            key: btn.isChecked()
            for key, btn in self._iter_channel_toggle_buttons()
        }

    def _restore_channel_toggle_states(self, snapshot):
        if not snapshot:
            return
        for key, btn in self._iter_channel_toggle_buttons():
            if key not in snapshot:
                continue
            checked = snapshot[key]
            btn.blockSignals(True)
            btn.setChecked(checked)
            ch_color = btn.property("ch_color")
            if ch_color:
                btn.setStyleSheet(self._ch_toggle_style(ch_color, checked))
            btn.blockSignals(False)

    def _sync_cbs_for_data(self, data_dict, current_a, voltage_a, power_a,
                           current_b, voltage_b, power_b, new_keys=None):
        if new_keys is None:
            new_keys = set(data_dict.keys())
        for key, ch_data in data_dict.items():
            ch_num, mtype, is_b = _parse_ch_label(key)
            if ch_num is None:
                continue

            if ch_num < 1 or ch_num > 4:
                continue

            idx = ch_num - 1
            if is_b:
                if mtype == "I":
                    cbs = current_b
                elif mtype == "V":
                    cbs = voltage_b
                else:
                    cbs = power_b
            else:
                if mtype == "I":
                    cbs = current_a
                elif mtype == "V":
                    cbs = voltage_a
                else:
                    cbs = power_a

            if idx < len(cbs):
                btn = cbs[idx]
                if key in new_keys:
                    btn.blockSignals(True)
                    btn.setChecked(True)
                    ch_color = btn.property("ch_color")
                    if ch_color:
                        btn.setStyleSheet(self._ch_toggle_style(ch_color, True))
                    btn.blockSignals(False)

                    values = ch_data.get("values", [])
                    if values:
                        v_min = min(values)
                        v_max = max(values)
                        v_range = v_max - v_min
                        if v_range < 1e-9:
                            v_range = abs(v_max) * 0.1 if abs(v_max) > 1e-9 else 1.0
                        scale_val = v_range
                        offset_val = (v_max + v_min) / 2.0

                        unit = "mA" if mtype == "I" else ("mW" if mtype == "P" else "mV")
                        scale_str = _auto_format(scale_val, unit)
                        offset_str = _auto_format(offset_val, unit)

                        scale_edit = btn.property("scale_edit")
                        offset_edit = btn.property("offset_edit")
                        if scale_edit:
                            scale_edit.setText(scale_str)
                        if offset_edit:
                            offset_edit.setText(offset_str)

    def _get_active_dlog_channel_count(self):
        count_a = 0
        for cb in self.ch_current_cbs_a:
            if cb.isChecked():
                count_a += 1
        for cb in self.ch_voltage_cbs_a:
            if cb.isChecked():
                count_a += 1

        count_b = 0
        for cb in self.ch_current_cbs_b:
            if cb.isChecked():
                count_b += 1
        for cb in self.ch_voltage_cbs_b:
            if cb.isChecked():
                count_b += 1

        return max(count_a, count_b, 1)

    def _get_min_period_per_unit(self):
        count_a = 0
        for cb in self.ch_current_cbs_a:
            if cb.isChecked():
                count_a += 1
        for cb in self.ch_voltage_cbs_a:
            if cb.isChecked():
                count_a += 1

        count_b = 0
        for cb in self.ch_current_cbs_b:
            if cb.isChecked():
                count_b += 1
        for cb in self.ch_voltage_cbs_b:
            if cb.isChecked():
                count_b += 1

        min_a = max(count_a, 1) * 20
        min_b = max(count_b, 1) * 20 if count_b > 0 else 0
        return min_a, min_b

    def _on_min_period_toggled(self, state):
        is_min = self.min_period_cb.isChecked()
        self.sample_period_edit.setReadOnly(is_min)
        self.sample_period_edit.setStyleSheet(
            dss.SAMPLE_PERIOD_READONLY_STYLE if is_min else dss.SAMPLE_PERIOD_EDIT_STYLE
        )
        if is_min:
            self._apply_minimum_period()

    def _apply_minimum_period(self):
        min_a, min_b = self._get_min_period_per_unit()
        min_period = max(min_a, min_b, 20)
        self.sample_period_edit.setText(str(int(min_period)))

    def _validate_sample_period(self):
        if self.min_period_cb.isChecked():
            self._apply_minimum_period()
            return

        try:
            val = float(self.sample_period_edit.text())
        except ValueError:
            val = 20.0

        num_ch = self._get_active_dlog_channel_count()
        min_period = num_ch * 20.0

        val = round(val / 20.0) * 20.0
        if val < min_period:
            val = min_period
        val = max(val, 20.0)

        self.sample_period_edit.setText(str(int(val)))

    def _get_monitor_time_seconds(self):
        def _parse_int(edit, default=0):
            try:
                return max(0, int(edit.text().strip() or "0"))
            except ValueError:
                return default

        d = _parse_int(self.monitor_time_d_edit)
        h = _parse_int(self.monitor_time_h_edit)
        m = _parse_int(self.monitor_time_m_edit)
        s = _parse_int(self.monitor_time_s_edit)
        total = d * 86400 + h * 3600 + m * 60 + s
        if total <= 0:
            total = 1
        return float(total)

    def _validate_monitor_time(self):
        def _parse_int(edit, default=0):
            try:
                return max(0, int(edit.text().strip() or "0"))
            except ValueError:
                return default

        d = _parse_int(self.monitor_time_d_edit)
        h = _parse_int(self.monitor_time_h_edit)
        m = _parse_int(self.monitor_time_m_edit)
        s = _parse_int(self.monitor_time_s_edit)

        total = d * 86400 + h * 3600 + m * 60 + s
        if total <= 0:
            total = 1

        max_total = 99 * 86400 + 23 * 3600 + 59 * 60 + 59
        if total > max_total:
            total = max_total

        d_new = total // 86400
        rem = total % 86400
        h_new = rem // 3600
        m_new = (rem % 3600) // 60
        s_new = rem % 60

        if self.monitor_time_d_edit.text() != str(d_new):
            self.monitor_time_d_edit.setText(str(d_new))
        if self.monitor_time_h_edit.text() != str(h_new):
            self.monitor_time_h_edit.setText(str(h_new))
        if self.monitor_time_m_edit.text() != str(m_new):
            self.monitor_time_m_edit.setText(str(m_new))
        if self.monitor_time_s_edit.text() != str(s_new):
            self.monitor_time_s_edit.setText(str(s_new))

    def _on_start_or_stop_recording(self):
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self._record_thread and self._record_thread.isRunning():
            if self._record_worker:
                self._record_worker.stop()
            self._record_thread.quit()
            self._record_thread.wait(5000)
            self._record_worker = None
            self._record_thread = None

        self._recording_channel_toggle_snapshot = self._snapshot_channel_toggle_states()
        self._validate_sample_period()

        n6705c_list = []
        channels_per_unit = []
        voltage_channels_per_unit = []
        unit_labels = []

        if self.is_connected_a and self.n6705c_a:
            active_a = [i + 1 for i, cb in enumerate(self.ch_current_cbs_a) if cb.isChecked()]
            voltage_a = [i + 1 for i, cb in enumerate(self.ch_voltage_cbs_a) if cb.isChecked()]
            power_a = [i + 1 for i, cb in enumerate(self.ch_power_cbs_a) if cb.isChecked()]
            for ch in power_a:
                if ch not in voltage_a:
                    voltage_a.append(ch)
                if ch not in active_a:
                    active_a.append(ch)
            voltage_a.sort()
            active_a.sort()
            if active_a or voltage_a:
                n6705c_list.append(self.n6705c_a)
                channels_per_unit.append(active_a)
                voltage_channels_per_unit.append(voltage_a)
                unit_labels.append("A")

        if self.is_connected_b and self.n6705c_b:
            active_b = [i + 1 for i, cb in enumerate(self.ch_current_cbs_b) if cb.isChecked()]
            voltage_b = [i + 1 for i, cb in enumerate(self.ch_voltage_cbs_b) if cb.isChecked()]
            power_b = [i + 1 for i, cb in enumerate(self.ch_power_cbs_b) if cb.isChecked()]
            for ch in power_b:
                if ch not in voltage_b:
                    voltage_b.append(ch)
                if ch not in active_b:
                    active_b.append(ch)
            voltage_b.sort()
            active_b.sort()
            if active_b or voltage_b:
                n6705c_list.append(self.n6705c_b)
                channels_per_unit.append(active_b)
                voltage_channels_per_unit.append(voltage_b)
                unit_labels.append("B")

        total_active = sum(len(c) for c in channels_per_unit) + sum(len(c) for c in voltage_channels_per_unit)
        if total_active == 0:
            return

        self._datalog_leases = []
        self._raw_dlog_list = []
        self._recording_had_error = False
        if self._instrument_manager:
            if self.is_connected_a and self.n6705c_a:
                lease_a = self._instrument_manager.create_lease("n6705c:A", "datalog")
                if lease_a.acquire():
                    self._datalog_leases.append(lease_a)
                else:
                    logger.warning("Cannot acquire busy for n6705c:A (datalog)")
            if self.is_connected_b and self.n6705c_b:
                lease_b = self._instrument_manager.create_lease("n6705c:B", "datalog")
                if lease_b.acquire():
                    self._datalog_leases.append(lease_b)
                else:
                    logger.warning("Cannot acquire busy for n6705c:B (datalog)")

        if len(n6705c_list) == 1:
            unit_labels = [""]

        record_type = "current" if self.type_current.isChecked() else "voltage"

        try:
            sample_period = float(self.sample_period_edit.text())
        except ValueError:
            sample_period = 1000.0

        try:
            monitor_time = self._get_monitor_time_seconds()
        except Exception:
            monitor_time = 5.0

        timeout_ms = int((monitor_time + 600) * 1000)
        for n6705c in n6705c_list:
            n6705c.instr.timeout = max(timeout_ms, 600000)

        imported_keys = set()
        for tc in self._imported_tab_configs:
            imported_keys |= tc.get("data_keys", set())
        for k in list(self.datalog_data.keys()):
            if k not in imported_keys:
                del self.datalog_data[k]
                self._known_data_keys.discard(k)

        self._update_recording_button_state(True)
        self._restore_channel_toggle_states(
            getattr(self, '_recording_channel_toggle_snapshot', None)
        )

        sample_period_s = sample_period / 1_000_000.0
        total_points = monitor_time / sample_period_s if sample_period_s > 0 else 0
        estimated_export_time = total_points * 1.2e-6 + 0.3
        safety_buffer = max(0.5, min(5.0, monitor_time * 0.3))
        total_estimated = monitor_time + safety_buffer + estimated_export_time
        logger.debug("[Datalog][Progress] Estimated total time: %.1fs (monitoring=%.1fs + wait=%.1fs + export=%.1fs, points=%.0f, interval=%.0fus)",
                    total_estimated, monitor_time, safety_buffer, estimated_export_time, total_points, sample_period)
        self._show_progress_overlay(total_estimated)

        self._record_thread = QThread()
        self._record_worker = _DatalogWorker(
            n6705c_list, channels_per_unit, unit_labels,
            record_type, sample_period, monitor_time,
            debug=DEBUG_MOCK,
            voltage_channels_per_unit=voltage_channels_per_unit
        )
        self._record_worker.moveToThread(self._record_thread)

        self._record_thread.started.connect(self._record_worker.run)
        self._record_worker.data_ready.connect(self._on_data_ready)
        self._record_worker.dlog_raw_ready.connect(self._on_dlog_raw_ready)
        self._record_worker.progress_update.connect(self._on_worker_progress)
        self._record_worker.finished.connect(self._record_thread.quit)
        self._record_worker.error.connect(self._on_recording_error)
        self._record_thread.finished.connect(self._on_recording_finished)
        self._record_thread.finished.connect(self._record_worker.deleteLater)
        self._record_thread.finished.connect(self._record_thread.deleteLater)

        self._record_thread.start()

    def _stop_recording(self):
        if self._record_worker:
            self._record_worker.stop()
            self.start_btn.setEnabled(False)

    def get_waveform_data(self):
        """返回当前内存中的波形数据（供 AI 摘要），结构 {label: {time, values}}。"""
        return self.datalog_data

    def _data_time_extent(self):
        """返回当前内存波形的整体时间范围 (t_min, t_max)，无数据返回 None。"""
        t_min = None
        t_max = None
        for channel in self.datalog_data.values():
            if not isinstance(channel, dict):
                continue
            times = channel.get("time") or []
            if not times:
                continue
            c_min = times[0]
            c_max = times[-1]
            t_min = c_min if t_min is None else min(t_min, c_min)
            t_max = c_max if t_max is None else max(t_max, c_max)
        if t_min is None or t_max is None:
            return None
        return t_min, t_max

    def get_visible_x_range(self):
        """读当前图表可见 X 范围（UI 线程，禁子线程调用）。

        与数据整体范围求交并裁剪；可见区基本覆盖全程时返回 None（等价全量）。
        """
        extent = self._data_time_extent()
        if extent is None:
            return None
        t_min, t_max = extent
        try:
            vb = self.plot_widget.getPlotItem().getViewBox()
            x_min, x_max = vb.viewRange()[0]
        except Exception:  # noqa: BLE001 - 读视图失败退回全量
            logger.error("读取可见 X 范围失败", exc_info=True)
            return None
        lo = max(t_min, min(x_min, x_max))
        hi = min(t_max, max(x_min, x_max))
        if hi <= lo:
            return None
        span = t_max - t_min
        if span <= 0:
            return None
        if (hi - lo) / span >= 0.99:
            return None
        return lo, hi

    def get_marker_window(self):
        """A/B 标记都放置时返回 {"a":..., "b":...}（UI 线程读 marker 位置）。"""
        a = self.marker_a_pos
        b = self.marker_b_pos
        if a is None or b is None:
            return None
        return {"a": float(a), "b": float(b)}

    def build_waveform_digest(self, x_range=None, marker=None):
        """构建波形摘要（F1.7）：按可见窗口裁剪 + 附带 Marker 区间统计。

        x_range=None → 全量；否则按 [x0, x1] 快速切片后构建摘要。
        marker={"a","b"} → 附带 Marker A→B 区间派生统计。
        """
        from core.ai.config import AISettings
        from core.ai.providers.waveform_provider import (
            build_digest,
            build_window_digest,
            marker_segment_stats,
        )

        if not self.datalog_data:
            return None
        data = dict(self.datalog_data)
        settings = AISettings.load()
        algo = settings.waveform_event_algo
        algo_params = settings.waveform_algo_params.get(algo, {})
        if x_range is None:
            digest = build_digest(
                data, event_aware=True, algo=algo, algo_params=algo_params
            )
            digest.window = {"full": True}
        else:
            digest = build_window_digest(
                data,
                float(x_range[0]),
                float(x_range[1]),
                event_aware=True,
                algo=algo,
                algo_params=algo_params,
            )
            if not getattr(digest, "stats", None):
                logger.warning(
                    "波形窗口 [%s, %s] 内无任何通道命中（可能为导入数据与可见区时间轴不重叠），"
                    "回退为全量摘要以确保导入波形可被识别。",
                    x_range[0],
                    x_range[1],
                )
                digest = build_digest(
                    data, event_aware=True, algo=algo, algo_params=algo_params
                )
                digest.window = {"full": True}
        if marker:
            digest.marker_segment = marker_segment_stats(
                data, marker.get("a"), marker.get("b")
            )
        return digest

    def get_waveform_data_windowed(self):
        """返回按当前可见窗口裁剪后的波形数据，供 AI drill-down 钳制范围。

        未缩放（看全程）时返回完整数据。仅在 UI 线程调用。
        """
        if not self.datalog_data:
            return None
        x_range = self.get_visible_x_range()
        if x_range is None:
            return dict(self.datalog_data)
        from core.ai.providers.waveform_provider import slice_channel_fast

        lo, hi = x_range
        windowed = {}
        for label, channel in self.datalog_data.items():
            if not isinstance(channel, dict):
                continue
            times = channel.get("time") or []
            values = channel.get("values") or []
            sel_t, sel_v = slice_channel_fast(list(times), list(values), lo, hi)
            if not sel_v:
                continue
            windowed[label] = {"time": sel_t, "values": sel_v}
        if not windowed:
            logger.warning(
                "可见窗口 [%s, %s] 内无任何通道命中（可能为导入数据时间轴与可见区不重叠），"
                "回退为全量数据供 AI drill-down。",
                lo,
                hi,
            )
            return dict(self.datalog_data)
        return windowed

    def _on_data_ready(self, data):
        power_chs_a = [cb.isChecked() for cb in self.ch_power_cbs_a]
        power_chs_b = [cb.isChecked() for cb in self.ch_power_cbs_b]
        compute_power_channels(data, power_chs_a, power_chs_b)
        self.datalog_data.update(data)
        self._clear_analysis_card_cache()
        self._sync_checkboxes_to_data()
        if self.is_recording:
            self._restore_channel_toggle_states(
                getattr(self, '_recording_channel_toggle_snapshot', None)
            )
        self._refresh_plot()

    def _on_dlog_raw_ready(self, dlog_list):
        self._raw_dlog_list = dlog_list

    def _on_recording_finished(self):
        self._maybe_auto_save_dlog()
        self.start_btn.setEnabled(True)
        self._update_recording_button_state(False)
        self._release_datalog_leases()
        self._hide_progress_overlay()
        self._record_worker = None
        self._record_thread = None

    def _maybe_auto_save_dlog(self):
        """录制正常结束（含手动停止）后按 DLog Save 设置自动保存原始 .dlog。"""
        try:
            cfg = load_datalog_app_settings()
        except Exception:
            logger.error("读取 DLog Save 设置失败", exc_info=True)
            return
        save_cfg = cfg.get("dlog_save", {})
        if not save_cfg.get("auto_save"):
            return
        # 出错路径（_on_recording_error 先于 finished）不自动保存，避免误存残缺数据
        if getattr(self, "_recording_had_error", False):
            return
        if not self._raw_dlog_list:
            return
        try:
            paths, next_seq = build_auto_save_paths(cfg, len(self._raw_dlog_list))
            for path, blob in zip(paths, self._raw_dlog_list):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as f:
                    f.write(blob)
            if next_seq is not None:
                cfg["dlog_save"]["next_seq"] = next_seq
                save_datalog_app_settings(cfg)
            logger.info("Datalog 自动保存完成: %s", paths[0])
            self._show_capture_toast(
                f"Datalog 已自动保存: {os.path.basename(paths[0])}",
                ToastNotification.TYPE_SUCCESS,
            )
        except Exception:
            logger.error("Datalog 自动保存失败", exc_info=True)
            self._show_capture_toast(
                "Datalog 自动保存失败，请查看日志", ToastNotification.TYPE_ERROR
            )

    def _on_recording_error(self, msg):
        logger.error("[Datalog] Recording error: %s", msg)
        self._recording_had_error = True
        self.start_btn.setEnabled(True)
        self._update_recording_button_state(False)
        self._hide_progress_overlay()
        self._release_datalog_leases()

    def _release_datalog_leases(self):
        for lease in getattr(self, '_datalog_leases', []):
            lease.release()
        self._datalog_leases = []
