#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyqtgraph as pg
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
)
from bisect import bisect_left, bisect_right
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.pages.n6705c_power_analyzer.widgets import SelectAllLineEdit
from ui.pages.n6705c_power_analyzer.datalog.helpers import (
    EXTRA_MARKER_COLORS,
    _ANN_DEFAULT_FONT,
    _ANN_FONT_SIZES,
    _MEAS_AVG_BG,
    _MEAS_AVG_FG,
    _auto_format,
    _color_for_label,
    _display_label,
    _format_time,
    _parse_ch_label,
    _sort_key_for_label,
)
from ui.pages.n6705c_power_analyzer.datalog.widgets import PairAnnotationItem

class MarkersViewMixin:
    """Datalog 页 Marker 视图：A/B 与额外成对 Marker / 区间注释 / Measurement 表。"""

    def _set_marker_mode(self, marker):
        if self._pending_marker == marker:
            self._clear_marker_mode()
            return
        self.marker_a_btn.setChecked(False)
        self.marker_b_btn.setChecked(False)
        if self._marker_follow_line is not None:
            self._marker_follow_line.setVisible(False)
        self._pending_marker = marker
        btn = self.marker_a_btn if marker == "A" else self.marker_b_btn
        btn.setChecked(True)
        btn.setToolTip(f"Marker {marker}: 请点击图表放置")
        if self._marker_follow_line is not None:
            color = "#d4a514" if marker == "A" else "#22d3ee"
            self._marker_follow_line.setPen(pg.mkPen(color=color, width=1, style=Qt.DashLine))
        if self.box_zoom_enabled:
            self._toggle_box_zoom()

    def _clear_marker_mode(self):
        self._pending_marker = None
        self.marker_a_btn.setChecked(False)
        self.marker_b_btn.setChecked(False)
        if self._marker_follow_line is not None:
            self._marker_follow_line.setVisible(False)
        self._update_marker_btn_tooltips()

    def _update_marker_btn_tooltips(self):
        if self._pending_marker == "A":
            self.marker_a_btn.setToolTip("Marker A: 请点击图表放置")
        elif self.marker_a_pos is not None:
            self.marker_a_btn.setToolTip(f"Marker A: 已放置 ({self.marker_a_pos:.4f}s)")
        else:
            self.marker_a_btn.setToolTip("Marker A: 点击进入放置模式")

        if self._pending_marker == "B":
            self.marker_b_btn.setToolTip("Marker B: 请点击图表放置")
        elif self.marker_b_pos is not None:
            self.marker_b_btn.setToolTip(f"Marker B: 已放置 ({self.marker_b_pos:.4f}s)")
        else:
            self.marker_b_btn.setToolTip("Marker B: 点击进入放置模式")

    def _update_clear_markers_btn(self):
        has_any = (
            self.marker_a_pos is not None
            or self.marker_b_pos is not None
            or bool(self._extra_markers)
        )
        self.clear_markers_btn.setEnabled(has_any)
        if not has_any:
            self.clear_markers_btn.setIcon(self._clear_markers_icon_normal)

    def _show_marker_btn_menu(self, which, pos):
        """右键 Set Marker A/B 按钮：设置坐标位置 或 冻结/解冻 该 marker。"""
        btn = self.marker_a_btn if which == "A" else self.marker_b_btn
        frozen = self.marker_a_frozen if which == "A" else self.marker_b_frozen

        menu = QMenu(self)
        menu.setStyleSheet(dss.menu_style())
        set_pos_action = menu.addAction(f"设置 Marker {which} 位置…")
        freeze_action = menu.addAction(
            f"解冻 Marker {which}" if frozen else f"冻结 Marker {which}"
        )

        chosen = menu.exec(btn.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == set_pos_action:
            self._set_marker_position_dialog(which)
        elif chosen == freeze_action:
            self._toggle_marker_freeze(which)

    @staticmethod
    def _parse_extra_marker_tag(tag):
        """解析 'X{pair_idx}_{which}' 形式的 extra marker 标签，返回 (pair_idx, which)。"""
        if not isinstance(tag, str) or not tag.startswith("X"):
            return None, None
        try:
            pi_str, w = tag[1:].split("_")
            return int(pi_str), w
        except ValueError:
            return None, None

    def _marker_display_label(self, tag):
        """Marker 内部标签（A/B 或 extra 的 X{pi}_{w}）→ 界面显示用字母。"""
        if tag in ("A", "B"):
            return tag
        pi, w = self._parse_extra_marker_tag(tag)
        if pi is not None and pi < len(self._extra_markers):
            return self._extra_markers[pi][f"label{w}"]
        return tag

    def _get_marker_pos(self, tag):
        if tag == "A":
            return self.marker_a_pos
        if tag == "B":
            return self.marker_b_pos
        pi, w = self._parse_extra_marker_tag(tag)
        if pi is not None and pi < len(self._extra_markers):
            return self._extra_markers[pi].get(f"pos{w}")
        return None

    def _set_marker_pos(self, tag, x):
        if tag == "A":
            self._place_marker_a(x)
            return
        if tag == "B":
            self._place_marker_b(x)
            return
        pi, w = self._parse_extra_marker_tag(tag)
        if pi is not None and pi < len(self._extra_markers):
            em = self._extra_markers[pi]
            em[f"pos{w}"] = x
            line = em.get(f"line{w}")
            if line is not None:
                line.setValue(x)
            else:
                self._place_extra_marker_line(em, w)

    def _set_marker_position_dialog(self, which):
        """弹窗直接输入横坐标（单位 s）来设置 Marker 位置。"""
        cur = self._get_marker_pos(which)
        which_label = self._marker_display_label(which)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Set Marker {which_label} Position")
        dialog.setFixedWidth(320)
        dialog.setStyleSheet(dss.dlg_style())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"Set Marker {which_label} Position")
        title.setStyleSheet(dss.DIALOG_TITLE_STYLE)
        layout.addWidget(title)

        x_label = QLabel("X 坐标 (s)")
        layout.addWidget(x_label)
        x_edit = SelectAllLineEdit()
        x_edit.setPlaceholderText("e.g. 1.25")
        if cur is not None:
            x_edit.setText(f"{cur:.6f}".rstrip('0').rstrip('.'))
        x_edit.setFocus(Qt.PopupFocusReason)
        x_edit.selectAll()
        layout.addWidget(x_edit)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        ok_btn = QPushButton("OK")
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.Accepted:
            return

        text = x_edit.text().strip()
        try:
            x_val = float(text)
        except ValueError:
            QMessageBox.warning(self, "无效输入", f"无法解析 X 坐标：{text!r}")
            return

        self._set_marker_pos(which, x_val)
        self._update_marker_region()
        self._update_marker_analysis()

    def _move_marker_delta_dialog(self, which, other):
        """弹窗输入相对另一 Marker 的时间距离（单位 ms）来移动 Marker。"""
        other_pos = self._get_marker_pos(other)
        which_label = self._marker_display_label(which)
        other_label = self._marker_display_label(other)
        if other_pos is None:
            QMessageBox.warning(self, "无法移动", f"Marker {other_label} 尚未放置，无法使用 Δ 定位。")
            return
        cur = self._get_marker_pos(which)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Move Marker {which_label} (Δ to {other_label})")
        dialog.setFixedWidth(320)
        dialog.setStyleSheet(dss.dlg_style())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(f"Move Marker {which_label} (Δ to {other_label})")
        title.setStyleSheet(dss.DIALOG_TITLE_STYLE)
        layout.addWidget(title)

        ref_label = QLabel(f"Marker {other_label} 当前位置: {other_pos:.6f} s")
        ref_label.setWordWrap(True)
        layout.addWidget(ref_label)

        delta_label = QLabel(f"Δ to {other_label} (ms)")
        layout.addWidget(delta_label)
        delta_edit = SelectAllLineEdit()
        delta_edit.setPlaceholderText("e.g. 2.5")
        if cur is not None:
            default_ms = (cur - other_pos) * 1000.0
            delta_edit.setText(f"{default_ms:.6f}".rstrip('0').rstrip('.'))
        delta_edit.setFocus(Qt.PopupFocusReason)
        delta_edit.selectAll()
        layout.addWidget(delta_edit)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        ok_btn = QPushButton("OK")
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        cancel_btn.clicked.connect(dialog.reject)
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.Accepted:
            return

        text = delta_edit.text().strip()
        try:
            delta_ms = float(text)
        except ValueError:
            QMessageBox.warning(self, "无效输入", f"无法解析 Δ 值：{text!r}")
            return

        x_val = other_pos + delta_ms / 1000.0
        self._set_marker_pos(which, x_val)
        self._update_marker_region()
        self._update_marker_analysis()

    def _toggle_marker_freeze(self, which):
        """切换 Marker A/B 的冻结状态（冻结后不可拖动）。"""
        if which == "A":
            self.marker_a_frozen = not self.marker_a_frozen
            if self.marker_a_line is not None:
                self.marker_a_line.setMovable(not self.marker_a_frozen)
        else:
            self.marker_b_frozen = not self.marker_b_frozen
            if self.marker_b_line is not None:
                self.marker_b_line.setMovable(not self.marker_b_frozen)

    def _on_chart_clicked(self, event):
        if event.button() == Qt.RightButton:
            scene_pos = event.scenePos()
            snap_marker = self._find_nearest_marker_at_scene(scene_pos)
            if snap_marker:
                self._show_marker_context_menu(snap_marker, event)
                event.accept()
            return

        if self._pending_marker is None:
            return

        pos = event.scenePos()
        vb = self.plot_widget.getPlotItem().getViewBox()
        mouse_point = vb.mapSceneToView(pos)
        x_val = mouse_point.x()

        if self._pending_marker == "A":
            self._place_marker_a(x_val)
        elif self._pending_marker == "B":
            self._place_marker_b(x_val)

        self._clear_marker_mode()
        self._update_marker_region()
        self._update_marker_analysis()

    def _place_marker_a(self, x):
        if self.marker_a_line:
            self.plot_widget.removeItem(self.marker_a_line)
        self.marker_a_pos = x
        self.marker_a_line = pg.InfiniteLine(
            pos=x, angle=90, movable=not self.marker_a_frozen,
            pen=pg.mkPen(color="#d4a514", width=2, style=Qt.DashLine),
            label=f"A",
            labelOpts={"color": "#d4a514", "position": 0.98}
        )
        self.marker_a_line.sigPositionChanged.connect(
            lambda line: self._on_marker_moved("A", line.value())
        )
        self.marker_a_line.sigClicked.connect(
            lambda line, ev: self._on_marker_line_clicked("A", ev)
        )
        self.plot_widget.addItem(self.marker_a_line)
        self.marker_a_btn.setToolTip(f"Marker A: 已放置 ({x:.4f}s)")
        self._update_clear_markers_btn()

    def _place_marker_b(self, x):
        if self.marker_b_line:
            self.plot_widget.removeItem(self.marker_b_line)
        self.marker_b_pos = x
        self.marker_b_line = pg.InfiniteLine(
            pos=x, angle=90, movable=not self.marker_b_frozen,
            pen=pg.mkPen(color="#4cc9f0", width=2, style=Qt.DashLine),
            label=f"B",
            labelOpts={"color": "#4cc9f0", "position": 0.98}
        )
        self.marker_b_line.sigPositionChanged.connect(
            lambda line: self._on_marker_moved("B", line.value())
        )
        self.marker_b_line.sigClicked.connect(
            lambda line, ev: self._on_marker_line_clicked("B", ev)
        )
        self.plot_widget.addItem(self.marker_b_line)
        self.marker_b_btn.setToolTip(f"Marker B: 已放置 ({x:.4f}s)")
        self._update_clear_markers_btn()

    def _on_marker_moved(self, which, value):
        if which == "A":
            self.marker_a_pos = value
            self.marker_a_btn.setToolTip(f"Marker A: 已放置 ({value:.4f}s)")
        else:
            self.marker_b_pos = value
            self.marker_b_btn.setToolTip(f"Marker B: 已放置 ({value:.4f}s)")
        self._update_marker_region()
        self._update_marker_analysis()

    def _on_marker_line_clicked(self, marker_tag, event):
        if event.button() == Qt.RightButton:
            self._show_marker_context_menu(marker_tag, event)

    def _update_marker_region(self):
        if self.marker_region:
            self.plot_widget.removeItem(self.marker_region)
            self.marker_region = None

        if self._marker_ab_text_item:
            self.plot_widget.removeItem(self._marker_ab_text_item)
            self._marker_ab_text_item = None

        if self.marker_a_pos is not None and self.marker_b_pos is not None:
            t1 = min(self.marker_a_pos, self.marker_b_pos)
            t2 = max(self.marker_a_pos, self.marker_b_pos)
            self.marker_region = pg.LinearRegionItem(
                values=[t1, t2], movable=False,
                brush=pg.mkBrush(40, 80, 180, 50),
                pen=pg.mkPen(None)
            )
            self.plot_widget.addItem(self.marker_region)
            self.marker_region.setZValue(-10)
            self._marker_ab_text_item = self._create_pair_annotation(
                t1, t2, "#d4a514", self._ab_ann_dx, self._ab_ann_dy, self._ab_ann_font)
            if self._marker_ab_text_item:
                self._marker_ab_text_item.pair_ref = ("AB", None)
                self.plot_widget.addItem(self._marker_ab_text_item, ignoreBounds=True)

        for region in self._extra_marker_regions:
            try:
                self.plot_widget.removeItem(region)
            except Exception:
                pass
        self._extra_marker_regions.clear()
        for item in self._extra_marker_text_items:
            try:
                self.plot_widget.removeItem(item)
            except Exception:
                pass
        self._extra_marker_text_items.clear()

        for pair_idx, em in enumerate(self._extra_markers):
            if em["pos1"] is not None and em["pos2"] is not None:
                t1 = min(em["pos1"], em["pos2"])
                t2 = max(em["pos1"], em["pos2"])
                region = pg.LinearRegionItem(
                    values=[t1, t2], movable=False,
                    brush=pg.mkBrush(40, 80, 180, 50),
                    pen=pg.mkPen(None)
                )
                self.plot_widget.addItem(region)
                region.setZValue(-10)
                self._extra_marker_regions.append(region)
                text_item = self._create_pair_annotation(
                    t1, t2, em["color1"],
                    em.get("ann_dx", 0.0), em.get("ann_dy", 0.0),
                    em.get("ann_font", _ANN_DEFAULT_FONT))
                if text_item:
                    text_item.pair_ref = ("X", pair_idx)
                    self.plot_widget.addItem(text_item, ignoreBounds=True)
                    self._extra_marker_text_items.append(text_item)

    def _create_pair_annotation(self, t1, t2, color, dx=0.0, dy=0.0, font_size=_ANN_DEFAULT_FONT):
        delta = t2 - t1
        if delta <= 0:
            return None
        delta_str = _format_time(delta)
        avg_str = self._compute_pair_avg_str(t1, t2)
        mid_x = (t1 + t2) / 2
        base_y = 1.0
        text_item = PairAnnotationItem(
            html=f"<div style='background:#0a1733dd; padding:2px 6px; "
                 f"border: 1px solid {color}; border-radius:1.5px; "
                 f"font-size:{font_size}px; font-weight:600; color:{color};'>"
                 f"\u0394t={delta_str}"
                 f"{avg_str}</div>",
            moved_callback=self._on_annotation_moved,
            context_callback=self._show_annotation_menu_at,
            anchor=(0.5, 0),
        )
        text_item.setZValue(90)
        text_item.default_pos = (mid_x, base_y)
        text_item.setPos(mid_x + dx, base_y + dy)
        return text_item

    def _on_annotation_moved(self, item):
        """annotation 拖拽结束：记录相对默认锚点的偏移，重建时保持位置。"""
        if item.default_pos is None or item.pair_ref is None:
            return
        dx = item.x() - item.default_pos[0]
        dy = item.y() - item.default_pos[1]
        scope, idx = item.pair_ref
        if scope == "AB":
            self._ab_ann_dx = dx
            self._ab_ann_dy = dy
        elif idx < len(self._extra_markers):
            em = self._extra_markers[idx]
            em["ann_dx"] = dx
            em["ann_dy"] = dy

    def _find_annotation_at_scene(self, scene_pos):
        """返回 scene_pos 命中的成对 Marker annotation（未命中返回 None）。"""
        candidates = []
        if self._marker_ab_text_item is not None:
            candidates.append(self._marker_ab_text_item)
        candidates.extend(self._extra_marker_text_items)
        for item in candidates:
            try:
                if item.sceneBoundingRect().contains(scene_pos):
                    return item
            except Exception:
                continue
        return None

    def _show_annotation_menu_at(self, item, screen_pos):
        """右键 annotation：更改字体大小。"""
        if item.pair_ref is None:
            return
        # ev.screenPos() 返回 pg.Point(QPointF)，QMenu.exec 只接受 QPoint
        screen_pos = QPoint(int(screen_pos.x()), int(screen_pos.y()))
        scope, idx = item.pair_ref
        if scope == "AB":
            cur_size = self._ab_ann_font
        elif idx < len(self._extra_markers):
            cur_size = self._extra_markers[idx].get("ann_font", _ANN_DEFAULT_FONT)
        else:
            return

        menu = QMenu(self)
        menu.setStyleSheet(dss.menu_style())
        size_menu = menu.addMenu("字体大小")
        size_actions = {}
        for size in _ANN_FONT_SIZES:
            act = size_menu.addAction(f"{size} px")
            act.setCheckable(True)
            act.setChecked(size == cur_size)
            size_actions[act] = size

        chosen = menu.exec(screen_pos)
        if chosen is None or chosen not in size_actions:
            return
        new_size = size_actions[chosen]
        if scope == "AB":
            self._ab_ann_font = new_size
        else:
            self._extra_markers[idx]["ann_font"] = new_size
        self._update_marker_region()

    def _compute_pair_avg_str(self, t1, t2):
        if not self.datalog_data:
            return ""
        is_current = self.type_current.isChecked()
        visible_keys = self._get_visible_keys()
        if not visible_keys:
            visible_keys = set(self.datalog_data.keys())
        parts = []
        for key in sorted(self.datalog_data.keys(), key=_sort_key_for_label):
            if key not in visible_keys:
                continue
            ch_data = self.datalog_data[key]
            times = ch_data["time"]
            values = ch_data["values"]
            lookup_t1 = min(self._effective_x_for_lookup(key, t1), self._effective_x_for_lookup(key, t2))
            lookup_t2 = max(self._effective_x_for_lookup(key, t1), self._effective_x_for_lookup(key, t2))
            i_start = bisect_left(times, lookup_t1)
            i_end = bisect_right(times, lookup_t2)
            segment = values[i_start:i_end]
            if not segment:
                continue
            seg_avg = sum(segment) / len(segment)
            ch_num, mtype, _ = _parse_ch_label(key)
            ch_is_current = (mtype == "I") if mtype else is_current
            ch_is_power = (mtype == "P") if mtype else False
            val_unit = "mW" if ch_is_power else ("mA" if ch_is_current else "mV")
            color_hex = _color_for_label(key)
            parts.append(f"<br><span style='color:{color_hex};'>{_display_label(key)} avg={_auto_format(seg_avg, val_unit)}</span>")
        return "".join(parts)

    def _clear_markers(self):
        self._marker_drag_target = None
        if self.marker_a_line:
            self.plot_widget.removeItem(self.marker_a_line)
            self.marker_a_line = None
        if self.marker_b_line:
            self.plot_widget.removeItem(self.marker_b_line)
            self.marker_b_line = None
        if self.marker_region:
            self.plot_widget.removeItem(self.marker_region)
            self.marker_region = None
        if self._marker_ab_text_item:
            self.plot_widget.removeItem(self._marker_ab_text_item)
            self._marker_ab_text_item = None
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_btn.setToolTip("Marker A: 点击进入放置模式")
        self.marker_b_btn.setToolTip("Marker B: 点击进入放置模式")
        self.add_markers_btn.setToolTip("添加标记 (当前已加: 0 组)")
        self._update_clear_markers_btn()

        for em in self._extra_markers:
            if em["line1"]:
                try:
                    self.plot_widget.removeItem(em["line1"])
                except Exception:
                    pass
            if em["line2"]:
                try:
                    self.plot_widget.removeItem(em["line2"])
                except Exception:
                    pass
        self._extra_markers.clear()
        for region in self._extra_marker_regions:
            try:
                self.plot_widget.removeItem(region)
            except Exception:
                pass
        self._extra_marker_regions.clear()
        for item in self._extra_marker_text_items:
            try:
                self.plot_widget.removeItem(item)
            except Exception:
                pass
        self._extra_marker_text_items.clear()

        self._clear_analysis_card_cache()
        self._update_marker_analysis()

    def _clear_analysis_card_cache(self):
        pass

    def _get_next_marker_labels(self):
        if self.marker_a_pos is None and self.marker_b_pos is None and not self._extra_markers:
            return "A", "B"
        used = set()
        if self.marker_a_pos is not None:
            used.add("A")
        if self.marker_b_pos is not None:
            used.add("B")
        for em in self._extra_markers:
            used.add(em["label1"])
            used.add(em["label2"])
        all_labels = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        available = [l for l in all_labels if l not in used]
        if len(available) >= 2:
            return available[0], available[1]
        return None, None

    def _extra_marker_color(self, pair_index):
        idx = (pair_index * 2) % len(EXTRA_MARKER_COLORS)
        return EXTRA_MARKER_COLORS[idx], EXTRA_MARKER_COLORS[(idx + 1) % len(EXTRA_MARKER_COLORS)]

    def _on_add_markers(self):
        if not self.datalog_data:
            return
        label1, label2 = self._get_next_marker_labels()
        if label1 is None:
            return

        vb = self.plot_widget.getPlotItem().getViewBox()
        x_min, x_max = vb.viewRange()[0]
        x_range = x_max - x_min

        last_marker_x = None
        if self.marker_b_pos is not None:
            last_marker_x = max(self.marker_a_pos or 0, self.marker_b_pos)
        elif self.marker_a_pos is not None:
            last_marker_x = self.marker_a_pos
        for em in self._extra_markers:
            if em["pos1"] is not None:
                last_marker_x = max(last_marker_x or em["pos1"], em["pos1"])
            if em["pos2"] is not None:
                last_marker_x = max(last_marker_x or em["pos2"], em["pos2"])

        if last_marker_x is not None:
            gap = x_range * 0.05
            span = x_range * 0.15
            x1 = last_marker_x + gap
            x2 = x1 + span
            if x2 > x_max:
                x1 = x_min + x_range * 0.35
                x2 = x_min + x_range * 0.65
        else:
            x1 = x_min + x_range * 0.35
            x2 = x_min + x_range * 0.65

        if label1 == "A" and label2 == "B":
            self._place_marker_a(x1)
            self._place_marker_b(x2)
            self._update_marker_region()
            self._update_marker_analysis()
            return

        pair_index = len(self._extra_markers)
        color1, color2 = self._extra_marker_color(pair_index)

        em = {
            "label1": label1,
            "label2": label2,
            "pos1": x1,
            "pos2": x2,
            "line1": None,
            "line2": None,
            "color1": color1,
            "color2": color2,
            "ann_dx": 0.0,
            "ann_dy": 0.0,
            "ann_font": _ANN_DEFAULT_FONT,
        }
        self._extra_markers.append(em)
        self._place_extra_marker_line(em, "1")
        self._place_extra_marker_line(em, "2")
        self._update_marker_region()
        self._update_marker_analysis()
        self._update_clear_markers_btn()
        self.add_markers_btn.setToolTip(f"添加标记 (当前已加: {len(self._extra_markers)} 组)")

    def _place_extra_marker_line(self, em, which):
        key = f"pos{which}"
        line_key = f"line{which}"
        label_key = f"label{which}"
        color_key = f"color{which}"

        if em[line_key]:
            try:
                self.plot_widget.removeItem(em[line_key])
            except Exception:
                pass

        x = em[key]
        color = em[color_key]
        label = em[label_key]

        line = pg.InfiniteLine(
            pos=x, angle=90, movable=True,
            pen=pg.mkPen(color=color, width=2, style=Qt.DashLine),
            label=label,
            labelOpts={"color": color, "position": 0.98}
        )
        pair_idx = self._extra_markers.index(em)
        tag = f"X{pair_idx}_{which}"
        line.sigPositionChanged.connect(
            lambda l, pi=pair_idx, w=which: self._on_extra_marker_moved(pi, w, l.value())
        )
        line.sigClicked.connect(
            lambda l, ev, t=tag: self._on_marker_line_clicked(t, ev)
        )
        self.plot_widget.addItem(line)
        em[line_key] = line

    def _on_extra_marker_moved(self, pair_idx, which, value):
        if pair_idx >= len(self._extra_markers):
            return
        em = self._extra_markers[pair_idx]
        em[f"pos{which}"] = value
        self._update_marker_region()
        self._update_marker_analysis()

    def _delete_marker_pair(self, pair_idx):
        if pair_idx >= len(self._extra_markers):
            return
        em = self._extra_markers[pair_idx]
        if em["line1"]:
            try:
                self.plot_widget.removeItem(em["line1"])
            except Exception:
                pass
        if em["line2"]:
            try:
                self.plot_widget.removeItem(em["line2"])
            except Exception:
                pass
        self._extra_markers.pop(pair_idx)
        self._relabel_extra_markers()
        self._update_marker_region()
        self._update_marker_analysis()
        self._update_clear_markers_btn()
        self.add_markers_btn.setToolTip(f"添加标记 (当前已加: {len(self._extra_markers)} 组)")

    def _delete_ab_markers(self):
        if self.marker_a_line:
            self.plot_widget.removeItem(self.marker_a_line)
            self.marker_a_line = None
        if self.marker_b_line:
            self.plot_widget.removeItem(self.marker_b_line)
            self.marker_b_line = None
        if self.marker_region:
            self.plot_widget.removeItem(self.marker_region)
            self.marker_region = None
        if self._marker_ab_text_item:
            self.plot_widget.removeItem(self._marker_ab_text_item)
            self._marker_ab_text_item = None
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_btn.setToolTip("Marker A: 点击进入放置模式")
        self.marker_b_btn.setToolTip("Marker B: 点击进入放置模式")

        if self._extra_markers:
            first = self._extra_markers.pop(0)
            if first["line1"]:
                try:
                    self.plot_widget.removeItem(first["line1"])
                except Exception:
                    pass
            if first["line2"]:
                try:
                    self.plot_widget.removeItem(first["line2"])
                except Exception:
                    pass
            self.marker_a_pos = first["pos1"]
            self.marker_b_pos = first["pos2"]
            self._ab_ann_dx = first.get("ann_dx", 0.0)
            self._ab_ann_dy = first.get("ann_dy", 0.0)
            self._ab_ann_font = first.get("ann_font", _ANN_DEFAULT_FONT)
            self._place_marker_a(self.marker_a_pos)
            self._place_marker_b(self.marker_b_pos)

        self._relabel_extra_markers()
        self._update_marker_region()
        self._update_marker_analysis()
        self._update_clear_markers_btn()
        self._update_marker_btn_tooltips()
        self.add_markers_btn.setToolTip(f"添加标记 (当前已加: {len(self._extra_markers)} 组)")

    def _relabel_extra_markers(self):
        used = set()
        if self.marker_a_pos is not None:
            used.add("A")
        if self.marker_b_pos is not None:
            used.add("B")
        all_labels = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
        available = [l for l in all_labels if l not in used]

        for i, em in enumerate(self._extra_markers):
            if i * 2 + 1 >= len(available):
                break
            new_label1 = available[i * 2]
            new_label2 = available[i * 2 + 1]
            em["label1"] = new_label1
            em["label2"] = new_label2
            new_color1, new_color2 = self._extra_marker_color(i)
            em["color1"] = new_color1
            em["color2"] = new_color2

            if em["line1"]:
                try:
                    self.plot_widget.removeItem(em["line1"])
                except Exception:
                    pass
                em["line1"] = None
            if em["line2"]:
                try:
                    self.plot_widget.removeItem(em["line2"])
                except Exception:
                    pass
                em["line2"] = None

            self._place_extra_marker_line(em, "1")
            self._place_extra_marker_line(em, "2")

    def _show_marker_context_menu(self, marker_tag, event):
        screen_pos = event.screenPos()
        self._show_marker_context_menu_at(marker_tag, QPoint(int(screen_pos.x()), int(screen_pos.y())))

    def _show_marker_context_menu_at(self, marker_tag, screen_pos):
        menu = QMenu(self)
        menu.setStyleSheet(dss.menu_style())

        delete_action = None
        pair_type = None
        pair_idx = -1
        move_abs_action = None
        move_delta_action = None
        other = None

        if marker_tag in ("A", "B"):
            other = "B" if marker_tag == "A" else "A"
            other_pos = self.marker_b_pos if other == "B" else self.marker_a_pos
            move_abs_action = menu.addAction(f"Move To (Abs : s)")
            move_delta_action = menu.addAction(f"Move To (Δ to {other} : ms)")
            move_delta_action.setEnabled(other_pos is not None)
            menu.addSeparator()
            delete_action = menu.addAction("Delete Marker A && B")
            pair_type = "AB"
        elif marker_tag.startswith("X"):
            pi, which_w = self._parse_extra_marker_tag(marker_tag)
            if pi is not None and pi < len(self._extra_markers):
                em = self._extra_markers[pi]
                other_w = "2" if which_w == "1" else "1"
                other = f"X{pi}_{other_w}"
                other_pos = em.get(f"pos{other_w}")
                move_abs_action = menu.addAction(f"Move To (Abs : s)")
                move_delta_action = menu.addAction(f"Move To (Δ to {em[f'label{other_w}']} : ms)")
                move_delta_action.setEnabled(other_pos is not None)
                menu.addSeparator()
                delete_action = menu.addAction(f"Delete Marker {em['label1']} && {em['label2']}")
                pair_type = "EXTRA"
                pair_idx = pi

        chosen = menu.exec(screen_pos)

        if chosen is None:
            return
        if chosen == move_abs_action:
            self._set_marker_position_dialog(marker_tag)
        elif chosen == move_delta_action:
            self._move_marker_delta_dialog(marker_tag, other)
        elif chosen == delete_action:
            if pair_type == "AB":
                self._delete_ab_markers()
            elif pair_type == "EXTRA" and pair_idx >= 0:
                self._delete_marker_pair(pair_idx)

    def _show_marker_move_here_menu(self, x_val, screen_pos):
        """图表空白处右键：列出全部 Marker（A/B 及额外标记对，随新增自动拓展），由用户选择移动到此处。"""
        tags = ["A", "B"]
        for i in range(len(self._extra_markers)):
            tags.append(f"X{i}_1")
            tags.append(f"X{i}_2")

        menu = QMenu(self)
        menu.setStyleSheet(dss.menu_style())
        actions = {}
        for tag in tags:
            label = self._marker_display_label(tag)
            actions[menu.addAction(f"将 Marker {label} 移动到此处")] = tag

        chosen = menu.exec(screen_pos)
        if chosen is None:
            return
        self._set_marker_pos(actions[chosen], x_val)
        self._update_marker_region()
        self._update_marker_analysis()

    def _restore_markers(self):
        if self.marker_a_pos is not None:
            self._place_marker_a(self.marker_a_pos)
        if self.marker_b_pos is not None:
            self._place_marker_b(self.marker_b_pos)
        for em in self._extra_markers:
            em["line1"] = None
            em["line2"] = None
            self._place_extra_marker_line(em, "1")
            self._place_extra_marker_line(em, "2")
        self._update_marker_region()

    def _update_marker_analysis(self):
        has_both_markers = self.marker_a_pos is not None and self.marker_b_pos is not None
        has_data = bool(self.datalog_data)

        if not has_both_markers and not has_data:
            self.analysis_hint_label.setVisible(True)
            self.meas_table.setVisible(False)
            return

        self.analysis_hint_label.setVisible(False)
        self.meas_table.setVisible(True)

        is_current = self.type_current.isChecked()

        visible_keys = self._get_visible_keys()
        if not visible_keys:
            visible_keys = set(self.datalog_data.keys())
        ch_list = [(k, self.datalog_data[k]) for k in sorted(self.datalog_data.keys(), key=_sort_key_for_label) if k in visible_keys]

        if has_both_markers:
            self._update_marker_analysis_with_markers(ch_list, is_current)
        else:
            self._update_marker_analysis_full_wave(ch_list, is_current)

    def _update_marker_analysis_full_wave(self, ch_list, is_current):
        headers = ["", "Avg"]
        num_rows = len(ch_list)
        num_cols = len(headers)

        self.meas_table.blockSignals(True)
        self.meas_table.clearSpans()
        self.meas_table.setRowCount(num_rows)
        self.meas_table.setColumnCount(num_cols)
        self.meas_table.setHorizontalHeaderLabels(headers)
        self._apply_meas_corner_title()

        ROW_BG = ["#080f22", "#0c1838"]

        for ch_idx, (label, ch_data) in enumerate(ch_list):
            color_hex = _color_for_label(label)
            row_bg = ROW_BG[ch_idx % 2]

            ch_num, mtype, _ = _parse_ch_label(label)
            ch_is_current = (mtype == "I") if mtype else is_current
            ch_is_power = (mtype == "P") if mtype else False
            val_unit = "mW" if ch_is_power else ("mA" if ch_is_current else "mV")

            values = ch_data["values"]
            if values:
                seg_avg = sum(values) / len(values)
            else:
                seg_avg = 0.0

            self._set_meas_cell(ch_idx, 0, _display_label(label), color_hex, bg=row_bg)
            self._set_meas_cell(ch_idx, 1, _auto_format(seg_avg, val_unit), color_hex, bg=row_bg)

        row_h = 28
        total_h = (num_rows + 1) * row_h + 4
        self.meas_table.setFixedHeight(min(total_h, 200))
        for r in range(num_rows):
            self.meas_table.setRowHeight(r, row_h)

        self.meas_table.blockSignals(False)

    def _update_marker_analysis_with_markers(self, ch_list, is_current):
        t_a = self.marker_a_pos
        t_b = self.marker_b_pos
        t1 = min(t_a, t_b)
        t2 = max(t_a, t_b)
        delta = t2 - t1
        freq = 1.0 / delta if delta > 0 else 0.0

        METRIC_DEFS = [
            ("min", self.meas_minimum_cb, "Min"),
            ("avg", self.meas_average_cb, "Avg"),
            ("max", self.meas_maximum_cb, "Max"),
            ("p2p", self.meas_peak2peak_cb, "P2P"),
            ("charge_ah", self.meas_charge_ah_cb, "Ah/Wh"),
            ("charge_c", self.meas_charge_c_cb, "C/J"),
        ]
        selected = [(k, hdr) for k, cb, hdr in METRIC_DEFS if cb.isChecked()]

        headers = [""]
        headers.append("Marker A")
        for _, hdr in selected:
            headers.append(hdr)
        headers.append("Marker B")

        num_rows = 1 + len(ch_list)
        num_cols = len(headers)

        self.meas_table.blockSignals(True)
        self.meas_table.clearSpans()
        self.meas_table.setRowCount(num_rows)
        self.meas_table.setColumnCount(num_cols)
        self.meas_table.setHorizontalHeaderLabels(headers)
        self._apply_meas_corner_title()

        for ci, h in enumerate(headers):
            if h == "Avg":
                hi = self.meas_table.horizontalHeaderItem(ci)
                if hi:
                    f = hi.font()
                    f.setBold(True)
                    hi.setFont(f)
                    hi.setForeground(QColor(_MEAS_AVG_FG))
                    hi.setBackground(QColor(_MEAS_AVG_BG))

        if freq >= 1.0:
            freq_str = f"{freq:.3f} Hz"
        else:
            freq_str = f"{freq * 1000:.3f} mHz"

        info_text = f"\u0394 = {_format_time(delta)}    Freq = {freq_str}"

        self._set_meas_cell(0, 0, "Time", "#5a7fad", bg="#0b1528")
        self._set_meas_cell(0, 1, _format_time(t_a), "#8eb0e3", bg="#0b1528")

        mid_col = 2
        if selected:
            mid_span = len(selected)
            self.meas_table.setSpan(0, mid_col, 1, mid_span)
            self._set_meas_cell(0, mid_col, info_text, "#5a7fad", align=Qt.AlignCenter, bg="#0b1528")
        else:
            self._set_meas_cell(0, mid_col, info_text, "#5a7fad", align=Qt.AlignCenter, bg="#0b1528")

        self._set_meas_cell(0, num_cols - 1, _format_time(t_b), "#8eb0e3", bg="#0b1528")

        ROW_BG = ["#080f22", "#0c1838"]

        for ch_idx, (label, ch_data) in enumerate(ch_list):
            row = 1 + ch_idx
            color_hex = _color_for_label(label)
            row_bg = ROW_BG[ch_idx % 2]

            ch_num, mtype, _ = _parse_ch_label(label)
            ch_is_current = (mtype == "I") if mtype else is_current
            ch_is_power = (mtype == "P") if mtype else False
            val_unit = "mW" if ch_is_power else ("mA" if ch_is_current else "mV")

            times = ch_data["time"]
            values = ch_data["values"]

            lookup_t_a = self._effective_x_for_lookup(label, t_a)
            lookup_t_b = self._effective_x_for_lookup(label, t_b)
            lookup_t1 = min(lookup_t_a, lookup_t_b)
            lookup_t2 = max(lookup_t_a, lookup_t_b)

            idx_a = self._find_nearest_index(times, lookup_t_a)
            idx_b = self._find_nearest_index(times, lookup_t_b)
            val_a = values[idx_a] if idx_a is not None else 0.0
            val_b = values[idx_b] if idx_b is not None else 0.0

            i_start = bisect_left(times, lookup_t1)
            i_end = bisect_right(times, lookup_t2)
            segment = values[i_start:i_end]

            if segment:
                time_seg = times[i_start:i_end]
                dt = (time_seg[-1] - time_seg[0]) if len(time_seg) >= 2 else delta
                seg_min = min(segment)
                seg_max = max(segment)
                seg_avg = sum(segment) / len(segment)
            else:
                dt = delta
                seg_min = seg_max = seg_avg = 0.0

            self._set_meas_cell(row, 0, _display_label(label), color_hex, bg=row_bg)
            self._set_meas_cell(row, 1, _auto_format(val_a, val_unit), color_hex, bg=row_bg)

            col = 2
            for metric_key, _ in selected:
                if metric_key == "min":
                    val_str = _auto_format(seg_min, val_unit)
                elif metric_key == "avg":
                    val_str = _auto_format(seg_avg, val_unit)
                elif metric_key == "max":
                    val_str = _auto_format(seg_max, val_unit)
                elif metric_key == "p2p":
                    val_str = _auto_format(seg_max - seg_min, val_unit)
                elif metric_key == "charge_ah":
                    c = seg_avg * dt / 3600.0
                    val_str = _auto_format(c, "mWh" if ch_is_power else ("mAh" if ch_is_current else "mWh"))
                elif metric_key == "charge_c":
                    c = seg_avg * dt / 1000.0
                    val_str = _auto_format(c, "J" if ch_is_power else ("C" if ch_is_current else "J"))
                else:
                    val_str = ""
                if metric_key == "avg":
                    self._set_meas_cell(row, col, val_str, color_hex, bg=_MEAS_AVG_BG, bold=True)
                else:
                    self._set_meas_cell(row, col, val_str, color_hex, bg=row_bg)
                col += 1

            self._set_meas_cell(row, num_cols - 1, _auto_format(val_b, val_unit), color_hex, bg=row_bg)

        row_h = 28
        total_h = (num_rows + 1) * row_h + 4
        self.meas_table.setFixedHeight(min(total_h, 200))
        for r in range(num_rows):
            self.meas_table.setRowHeight(r, row_h)

        self.meas_table.blockSignals(False)

    def _set_meas_cell(self, row, col, text, color_hex, align=Qt.AlignCenter, bg=None, bold=False):
        item = self.meas_table.item(row, col)
        if item is None:
            item = QTableWidgetItem(text)
            item.setTextAlignment(align)
            item.setForeground(QColor(color_hex))
            if bg:
                item.setBackground(QColor(bg))
            if bold:
                f = item.font()
                f.setBold(True)
                item.setFont(f)
            self.meas_table.setItem(row, col, item)
        else:
            item.setText(text)
            item.setForeground(QColor(color_hex))
            if bg:
                item.setBackground(QColor(bg))
            f = item.font()
            f.setBold(bold)
            item.setFont(f)
