#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import re
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.pages.n6705c_power_analyzer.datalog.helpers import _make_svg_icon, _parse_ch_label

class TimeOffsetViewMixin:
    """Datalog 页时间对齐视图：B 机 / 导入文件时间偏移。"""

    def _is_b_label(self, label):
        _, _, is_b = _parse_ch_label(label)
        return is_b

    def _get_file_prefix(self, label):
        m = re.match(r'^(F\d+)-', str(label).strip())
        return m.group(1) if m else ""

    def _get_total_time_offset(self, label):
        off = 0.0
        if self._b_time_offset != 0.0 and self._is_b_label(label):
            off += self._b_time_offset
        prefix = self._get_file_prefix(label)
        if prefix and self._file_time_offsets.get(prefix):
            off += self._file_time_offsets[prefix]
        return off

    def _get_effective_times(self, label, times):
        off = self._get_total_time_offset(label)
        if off != 0.0:
            return np.asarray(times, dtype=np.float64) + off
        return times

    def _effective_x_for_lookup(self, label, x):
        off = self._get_total_time_offset(label)
        if off != 0.0:
            return x - off
        return x

    def _on_time_offset(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Time Offset for Instrument B")
        dialog.setFixedWidth(380)
        dialog.setStyleSheet(dss.dlg_style())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Time Offset for Instrument B")
        title.setStyleSheet(dss.DIALOG_TITLE_STYLE)
        layout.addWidget(title)

        desc = QLabel("Shift all Instrument B waveforms along the time axis.\n"
                       "Negative value moves B waveforms to the left (earlier),\n"
                       "positive value moves them to the right (later).")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        offset_label = QLabel("Time Offset (ms)")
        layout.addWidget(offset_label)
        offset_edit = QLineEdit()
        offset_edit.setPlaceholderText("e.g. -50 or -200")
        current_ms = self._b_time_offset * 1000.0
        display_text = f"{current_ms:.3f}".rstrip('0').rstrip('.')
        if current_ms == 0.0:
            display_text = "-0"
        offset_edit.setText(display_text)
        layout.addWidget(offset_edit)

        has_both_markers = self.marker_a_pos is not None and self.marker_b_pos is not None

        align_btn = QPushButton("Align From Markers")
        align_btn.setIcon(_make_svg_icon("map-pin.svg", "#ffffff", 14))
        align_btn.setToolTip("Auto-calculate offset from Marker A and Marker B positions.\n"
                             "Offset = Marker A - Marker B")
        align_btn.setEnabled(has_both_markers)
        if not has_both_markers:
            align_btn.setStyleSheet(dss.ALIGN_BTN_DISABLED_STYLE)
        else:
            align_btn.setStyleSheet(dss.ALIGN_BTN_ENABLED_STYLE)

        if has_both_markers:
            marker_delta_ms = (self.marker_a_pos - self.marker_b_pos) * 1000.0
            marker_info = QLabel(
                f"Marker A: {self.marker_a_pos:.6f}s    Marker B: {self.marker_b_pos:.6f}s\n"
                f"Calculated offset: {marker_delta_ms:+.3f} ms"
            )
            marker_info.setStyleSheet(dss.MARKER_INFO_STYLE)
            layout.addWidget(marker_info)
        else:
            marker_info = QLabel("Set both Marker A and Marker B on the chart to enable auto-align.")
            marker_info.setStyleSheet(dss.MARKER_INFO_DISABLED_STYLE)
            marker_info.setWordWrap(True)
            layout.addWidget(marker_info)

        def _on_align_from_markers():
            delta_s = self.marker_a_pos - self.marker_b_pos
            self._apply_b_time_offset(self._b_time_offset + delta_s)
            new_b_pos = self.marker_b_pos + delta_s
            self.marker_b_pos = new_b_pos
            if self.marker_b_line:
                self.marker_b_line.setValue(new_b_pos)
            self.marker_b_btn.setToolTip(f"Set Marker B ({new_b_pos:.4f}s)")
            self._update_marker_region()
            self._update_marker_analysis()
            dialog.done(QDialog.Rejected)

        align_btn.clicked.connect(_on_align_from_markers)
        layout.addWidget(align_btn)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        reset_btn = QPushButton("Reset to 0")
        reset_btn.clicked.connect(lambda: offset_edit.setText("0"))
        btn_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(dss.PRIMARY_BTN_STYLE)
        apply_btn.clicked.connect(dialog.accept)
        apply_btn.setDefault(True)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            try:
                new_offset_ms = float(offset_edit.text().strip())
            except ValueError:
                return
            self._apply_b_time_offset(new_offset_ms / 1000.0)

    def _apply_b_time_offset(self, offset_s):
        self._b_time_offset = offset_s
        if offset_s != 0.0:
            offset_ms = offset_s * 1000.0
            self.time_offset_btn.setChecked(True)
            self.time_offset_btn.setToolTip(f"时间偏移: {offset_ms:+.3f} ms")
        else:
            self.time_offset_btn.setChecked(False)
            self.time_offset_btn.setToolTip("时间偏移")
        self._on_channel_visibility_changed()

    def _on_file_time_offset(self, file_prefix):
        if not file_prefix:
            return

        tab_name = file_prefix
        for tc in self._imported_tab_configs:
            if tc.get("file_prefix") == file_prefix:
                tab_name = tc.get("tab_name") or file_prefix
                break

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Time Offset for {tab_name}")
        dialog.setFixedWidth(380)
        dialog.setStyleSheet(dss.dlg_style())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"Time Offset for {tab_name}")
        title.setStyleSheet(dss.DIALOG_TITLE_STYLE)
        layout.addWidget(title)

        desc = QLabel(f"Shift all waveforms of [{file_prefix}] along the time axis.\n"
                       "Negative value moves waveforms to the left (earlier),\n"
                       "positive value moves them to the right (later).")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        offset_label = QLabel("Time Offset (ms)")
        layout.addWidget(offset_label)
        offset_edit = QLineEdit()
        offset_edit.setPlaceholderText("e.g. -50 or -200")
        current_s = self._file_time_offsets.get(file_prefix, 0.0)
        current_ms = current_s * 1000.0
        display_text = f"{current_ms:.3f}".rstrip('0').rstrip('.')
        if current_ms == 0.0:
            display_text = "-0"
        offset_edit.setText(display_text)
        layout.addWidget(offset_edit)

        has_both_markers = self.marker_a_pos is not None and self.marker_b_pos is not None

        align_btn = QPushButton("Align From Markers")
        align_btn.setIcon(_make_svg_icon("map-pin.svg", "#ffffff", 14))
        align_btn.setToolTip("Auto-calculate offset from Marker A and Marker B positions.\n"
                             "Offset = Marker A - Marker B")
        align_btn.setEnabled(has_both_markers)
        if not has_both_markers:
            align_btn.setStyleSheet(dss.ALIGN_BTN_DISABLED_STYLE)
        else:
            align_btn.setStyleSheet(dss.ALIGN_BTN_ENABLED_STYLE)

        if has_both_markers:
            marker_delta_ms = (self.marker_a_pos - self.marker_b_pos) * 1000.0
            marker_info = QLabel(
                f"Marker A: {self.marker_a_pos:.6f}s    Marker B: {self.marker_b_pos:.6f}s\n"
                f"Calculated offset: {marker_delta_ms:+.3f} ms"
            )
            marker_info.setStyleSheet(dss.MARKER_INFO_STYLE)
            layout.addWidget(marker_info)
        else:
            marker_info = QLabel("Set both Marker A and Marker B on the chart to enable auto-align.")
            marker_info.setStyleSheet(dss.MARKER_INFO_DISABLED_STYLE)
            marker_info.setWordWrap(True)
            layout.addWidget(marker_info)

        def _on_align_from_markers():
            delta_s = self.marker_a_pos - self.marker_b_pos
            new_off = self._file_time_offsets.get(file_prefix, 0.0) + delta_s
            self._apply_file_time_offset(file_prefix, new_off)
            new_b_pos = self.marker_b_pos + delta_s
            self.marker_b_pos = new_b_pos
            if self.marker_b_line:
                self.marker_b_line.setValue(new_b_pos)
            self.marker_b_btn.setToolTip(f"Set Marker B ({new_b_pos:.4f}s)")
            self._update_marker_region()
            self._update_marker_analysis()
            dialog.done(QDialog.Rejected)

        align_btn.clicked.connect(_on_align_from_markers)
        layout.addWidget(align_btn)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        reset_btn = QPushButton("Reset to 0")
        reset_btn.clicked.connect(lambda: offset_edit.setText("0"))
        btn_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(dss.PRIMARY_BTN_STYLE)
        apply_btn.clicked.connect(dialog.accept)
        apply_btn.setDefault(True)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.Accepted:
            try:
                new_offset_ms = float(offset_edit.text().strip())
            except ValueError:
                return
            self._apply_file_time_offset(file_prefix, new_offset_ms / 1000.0)

    def _apply_file_time_offset(self, file_prefix, offset_s):
        if not file_prefix:
            return
        if offset_s == 0.0:
            self._file_time_offsets.pop(file_prefix, None)
        else:
            self._file_time_offsets[file_prefix] = offset_s
        self._on_channel_visibility_changed()

    def _update_time_offset_btn_visibility(self):
        multi = self.is_connected_a and self.is_connected_b
        self.time_offset_btn.setVisible(multi)
        if not multi and self._b_time_offset != 0.0:
            self._apply_b_time_offset(0.0)
