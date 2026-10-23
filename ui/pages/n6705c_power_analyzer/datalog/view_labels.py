#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyqtgraph as pg
import re
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from ui.pages.n6705c_power_analyzer.datalog.helpers import (
    _auto_format,
    _color_for_label,
    _display_label,
    _make_svg_icon,
    _sort_key_for_label,
    _unit_for_label,
)

class LabelsViewMixin:
    """Datalog 页自定义标签视图：标签添加 / 绘制 / 定位 / 列表面板。"""

    def _refresh_label_ch_combo(self):
        current = self.label_ch_combo.currentText()
        self.label_ch_combo.clear()
        for label in sorted(self.datalog_data.keys(), key=_sort_key_for_label):
            self.label_ch_combo.addItem(_display_label(label), label)
        idx = self.label_ch_combo.findText(current)
        if idx >= 0:
            self.label_ch_combo.setCurrentIndex(idx)
        elif self.label_ch_combo.count() > 0:
            self.label_ch_combo.setCurrentIndex(0)

    def _add_custom_label(self):
        idx = self.label_ch_combo.currentIndex()
        if idx < 0:
            return
        ch_name = self.label_ch_combo.itemData(idx) or self.label_ch_combo.currentText().strip()
        time_str = self.label_time_edit.text().strip()
        text = self.label_text_edit.text().strip()
        if not time_str or not text or not ch_name:
            return
        parsed = self._parse_label_time_input(time_str)
        if parsed is None:
            return
        t, unit = parsed
        self._label_time_last_unit = unit

        self.custom_labels.append({"time": t, "text": text, "channel": ch_name})
        self._refresh_labels_display()
        self._draw_label_item(t, text, ch_name)
        self._auto_fit_y_axis()

        self.label_time_edit.clear()
        self.label_text_edit.clear()

    def _parse_label_time_input(self, raw_text):
        s = (raw_text or "").strip().lower().replace("µ", "u")
        if not s:
            return None
        m = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?|[+-]?\.\d+)\s*([a-z]*)\s*", s)
        if not m:
            return None
        try:
            value = float(m.group(1))
        except ValueError:
            return None
        unit_raw = m.group(2).strip()
        unit_map = {
            "": None,
            "s": "s", "sec": "s", "secs": "s", "second": "s", "seconds": "s",
            "ms": "ms", "msec": "ms", "msecs": "ms", "millisecond": "ms", "milliseconds": "ms",
            "us": "us", "usec": "us", "usecs": "us", "microsecond": "us", "microseconds": "us",
            "ns": "ns", "nsec": "ns", "nsecs": "ns", "nanosecond": "ns", "nanoseconds": "ns",
            "m": "min", "min": "min", "mins": "min", "minute": "min", "minutes": "min",
            "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
        }
        if unit_raw not in unit_map:
            return None
        unit = unit_map[unit_raw]
        if unit is None:
            unit = self._label_time_last_unit or "s"
        factor = {
            "s": 1.0,
            "ms": 1e-3,
            "us": 1e-6,
            "ns": 1e-9,
            "min": 60.0,
            "h": 3600.0,
        }.get(unit, 1.0)
        return value * factor, unit

    def _format_label_time_display(self, seconds, unit):
        factor = {
            "s": 1.0,
            "ms": 1e-3,
            "us": 1e-6,
            "ns": 1e-9,
            "min": 60.0,
            "h": 3600.0,
        }.get(unit, 1.0)
        display_unit = {"min": "min", "us": "us"}.get(unit, unit)
        value = seconds / factor
        if abs(value - round(value)) < 1e-9:
            txt = f"{int(round(value))}"
        else:
            txt = f"{value:g}"
        return f"{txt} {display_unit}"

    def _on_label_time_editing_finished(self):
        raw = self.label_time_edit.text().strip()
        if not raw:
            return
        parsed = self._parse_label_time_input(raw)
        if parsed is None:
            return
        seconds, unit = parsed
        self._label_time_last_unit = unit
        self.label_time_edit.blockSignals(True)
        try:
            self.label_time_edit.setText(self._format_label_time_display(seconds, unit))
        finally:
            self.label_time_edit.blockSignals(False)

    def _get_value_at_time(self, ch_name, t):
        for label, ch_data in self.datalog_data.items():
            if label.strip() == ch_name:
                times = ch_data["time"]
                values = ch_data["values"]
                if not times:
                    return None
                lookup_t = self._effective_x_for_lookup(label, t)
                idx = self._find_nearest_index(times, lookup_t)
                if idx is not None:
                    raw_val = values[idx]
                    band = self._band_info.get(label)
                    if band:
                        return band["plot_bottom"] + (raw_val - band["raw_min"]) / band["raw_range"] * band["plot_range"]
                    return raw_val
        return None

    def _get_channel_color(self, ch_name):
        color = _color_for_label(ch_name)
        return (color, color)

    def _find_local_peak_y(self, t, ch_name):
        vb = self.plot_widget.getPlotItem().getViewBox()
        x_min, x_max = vb.viewRange()[0]
        view_span = x_max - x_min
        half_window = view_span * 0.03

        for label, ch_data in self.datalog_data.items():
            if label.strip() != ch_name:
                continue
            band = self._band_info.get(label)
            if not band:
                return None
            times = ch_data["time"]
            vals = ch_data["values"]
            if not times:
                return None
            lookup_t = self._effective_x_for_lookup(label, t)
            lo = self._find_nearest_index(times, lookup_t - half_window)
            hi = self._find_nearest_index(times, lookup_t + half_window)
            if lo is None or hi is None:
                return None
            if lo > hi:
                lo, hi = hi, lo
            segment = vals[lo:hi + 1]
            if not segment:
                return None
            local_max_raw = max(segment)
            return band["plot_bottom"] + (local_max_raw - band["raw_min"]) / band["raw_range"] * band["plot_range"]
        return None

    def _draw_label_item(self, t, text, ch_name):
        color, _ = self._get_channel_color(ch_name)

        raw_val = None
        band = None
        for label in self.datalog_data:
            if label.strip() == ch_name:
                band = self._band_info.get(label)
                ch_data = self.datalog_data[label]
                times = ch_data["time"]
                lookup_t = self._effective_x_for_lookup(label, t)
                idx = self._find_nearest_index(times, lookup_t)
                if idx is not None:
                    raw_val = ch_data["values"][idx]
                break

        ch_unit = _unit_for_label(ch_name)
        val_str = _auto_format(raw_val, ch_unit) if raw_val is not None else "—"

        label_item = pg.TextItem(
            html=f"<div style='background:#0a1733ee; padding:2px 5px; "
                 f"border: 1px solid {color}; border-radius:1.5px; "
                 f"font-size:10px; font-weight:700; color:{color};'>"
                 f"{text}: {val_str}</div>",
            anchor=(0.5, 1),
        )
        label_item.setZValue(55)
        label_item.setProperty("label_time", t)
        label_item.setProperty("label_ch", ch_name)

        label_y = self._compute_custom_label_y(t, ch_name)
        label_item.setPos(t, label_y)
        self.plot_widget.addItem(label_item)

        self.custom_label_lines.append({"text_item": label_item})

    def _compute_custom_label_y(self, t, ch_name):
        vb = self.plot_widget.getPlotItem().getViewBox()
        y_min, y_max = vb.viewRange()[1]
        view_y_span = y_max - y_min

        peak_y = self._find_local_peak_y(t, ch_name)
        if peak_y is not None:
            label_y = peak_y + view_y_span * 0.03
        else:
            y_val = self._get_value_at_time(ch_name, t)
            if y_val is None:
                y_val = 0.5
            label_y = y_val + view_y_span * 0.05
        return label_y

    def _update_custom_label_positions(self):
        for entry in self.custom_label_lines:
            item = entry.get("text_item") if isinstance(entry, dict) else None
            if item is None:
                continue
            t = item.property("label_time")
            ch_name = item.property("label_ch")
            if t is None or ch_name is None:
                continue
            label_y = self._compute_custom_label_y(t, ch_name)
            item.setPos(t, label_y)

    def _get_max_custom_label_y(self):
        max_y = None
        for lbl in self.custom_labels:
            t = lbl["time"]
            ch_name = lbl.get("channel", "")
            peak_y = self._find_local_peak_y(t, ch_name)
            if peak_y is not None:
                label_y = peak_y + 0.06
            else:
                y_val = self._get_value_at_time(ch_name, t)
                label_y = (y_val if y_val is not None else 0.5) + 0.06
            if max_y is None or label_y > max_y:
                max_y = label_y
        return max_y

    def _compute_y_range_with_labels(self):
        y_bottom = -0.02
        y_top = 1.02
        max_label_y = self._get_max_custom_label_y()
        if max_label_y is not None and max_label_y + 0.04 > y_top:
            y_top = max_label_y + 0.04
        return y_bottom, y_top

    def _auto_fit_y_axis(self):
        y_bottom, y_top = self._compute_y_range_with_labels()
        self.plot_widget.setYRange(y_bottom, y_top)

    def _restore_label_lines(self):
        for item in self.custom_label_lines:
            try:
                if isinstance(item, dict):
                    for key in ["vline", "dot", "text_item", "arrow"]:
                        if key in item:
                            self.plot_widget.removeItem(item[key])
                else:
                    self.plot_widget.removeItem(item)
            except Exception:
                pass
        self.custom_label_lines.clear()
        for lbl in self.custom_labels:
            self._draw_label_item(lbl["time"], lbl["text"], lbl.get("channel", ""))

    def _refresh_labels_display(self):
        while self.labels_list_layout_inner.count() > 0:
            item = self.labels_list_layout_inner.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.custom_labels:
            self.labels_list_label = QLabel("No labels added.")
            self.labels_list_label.setObjectName("hintLabel")
            self.labels_list_layout_inner.addWidget(self.labels_list_label)
            self.labels_list_layout_inner.addStretch()
            return

        for i, lbl in enumerate(self.custom_labels):
            ch = lbl.get("channel", "")
            color = _color_for_label(ch) if ch else "#8eb0e3"

            row_frame = QFrame()
            row_frame.setStyleSheet(
                f"QFrame {{ background-color: #0c1a35; border-left: 3px solid {color}; "
                f"border-radius: 1.5px; padding: 0px; }}"
            )
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(6, 3, 4, 3)
            row_layout.setSpacing(6)

            info_layout = QVBoxLayout()
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(0)

            ch_lbl = QLabel(ch if ch else "—")
            ch_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700; border: none;")
            info_layout.addWidget(ch_lbl)

            detail_lbl = QLabel(f"{lbl['time']}s  ·  {lbl['text']}")
            detail_lbl.setStyleSheet("color: #667ba0; font-size: 10px; border: none;")
            info_layout.addWidget(detail_lbl)

            row_layout.addLayout(info_layout, 1)

            del_btn = QPushButton()
            del_btn.setIcon(_make_svg_icon("x-close.svg", "#3a5070", 12))
            del_btn.setFixedSize(22, 22)
            del_btn.setStyleSheet(
                "QPushButton { background: transparent; color: #3a5070; font-size: 12px; "
                "border: none; border-radius: 1px; }"
                "QPushButton:hover { background: #1e3460; color: #ff6b6b; }"
            )
            del_btn.clicked.connect(lambda checked=False, idx=i: self._delete_custom_label(idx))
            row_layout.addWidget(del_btn)

            self.labels_list_layout_inner.addWidget(row_frame)

        self.labels_list_layout_inner.addStretch()

    def _delete_custom_label(self, idx):
        if 0 <= idx < len(self.custom_labels):
            self.custom_labels.pop(idx)
            self._refresh_labels_display()
            self._restore_label_lines()
            self._auto_fit_y_axis()
