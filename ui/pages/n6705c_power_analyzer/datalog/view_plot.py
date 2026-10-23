#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QCursor, QFont, QTransform
from bisect import bisect_left, bisect_right
from ui.pages.n6705c_power_analyzer.datalog.helpers import (
    _BAND_CEILING,
    _auto_format,
    _color_for_label,
    _display_label,
    _sort_key_for_label,
    _unit_for_label,
)

class PlotViewMixin:
    """Datalog 页波形视图：绘图区 / band 网格 / 十字线 / 缩放 / 零线。"""

    def _setup_plot(self):
        self.plot_widget.setBackground("#071127")
        self.plot_widget.showGrid(x=True, y=False, alpha=0.3)

        axis_pen = pg.mkPen(color="#2a4272", width=1)
        text_color = "#8eb0e3"

        bottom_axis = self.plot_widget.getPlotItem().getAxis("bottom")
        bottom_axis.setPen(axis_pen)
        bottom_axis.setTextPen(pg.mkPen(text_color))
        bottom_axis.setStyle(tickLength=-5)

        left_axis = self.plot_widget.getPlotItem().getAxis("left")
        left_axis.setPen(axis_pen)
        left_axis.setTextPen(pg.mkPen(text_color))
        left_axis.setTicks([])
        left_axis.setLabel("")
        left_axis.setWidth(0)
        left_tick_font = QFont()
        left_tick_font.setPixelSize(10)
        left_axis.setStyle(tickFont=left_tick_font, tickLength=-6)

        self.plot_widget.setLabel("bottom", "Time (s)", color=text_color)

        self.plot_widget.setXRange(0, 10)
        self.plot_widget.setYRange(-0.02, 1.02)

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.setMouseEnabled(x=True, y=False)
        vb.setMenuEnabled(False)

        self.legend = None

        self.crosshair_v = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color="#4a6a9e", width=1, style=Qt.DashLine)
        )
        self.crosshair_v.setVisible(False)
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)

        self._marker_follow_line = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color="#d4a514", width=1, style=Qt.DashLine)
        )
        self._marker_follow_line.setVisible(False)
        self.plot_widget.addItem(self._marker_follow_line, ignoreBounds=True)

        self.tooltip_text = pg.TextItem(
            text="", color="#dbe7ff",
            anchor=(1, 1),
            fill=pg.mkBrush(10, 20, 45, 220),
            border=pg.mkPen(color="#2a4272")
        )
        self.tooltip_text.setVisible(False)
        self.tooltip_text.setZValue(100)
        self.plot_widget.addItem(self.tooltip_text, ignoreBounds=True)

        self.plot_curves = {}

        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=30, slot=self._on_mouse_moved
        )

        self.plot_widget.scene().sigMouseClicked.connect(self._on_chart_clicked)

        self.plot_widget.sigRangeChanged.connect(self._on_range_changed)

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.installEventFilter(self)
        self.plot_widget.installEventFilter(self)

    def _hide_crosshair(self):
        self.crosshair_v.setVisible(False)
        self.tooltip_text.setVisible(False)
        if self._marker_follow_line is not None:
            self._marker_follow_line.setVisible(False)
        for dot in self.crosshair_dots:
            try:
                self.plot_widget.removeItem(dot)
            except Exception:
                pass
        self.crosshair_dots.clear()

    def _find_nearest_marker_at_scene(self, scene_pos):
        vb = self.plot_widget.getPlotItem().getViewBox()
        snap_px = self._marker_snap_px
        best = None
        best_dist = snap_px + 1

        candidates = [
            ("A", self.marker_a_line, self.marker_a_pos),
            ("B", self.marker_b_line, self.marker_b_pos),
        ]
        for i, em in enumerate(self._extra_markers):
            candidates.append((f"X{i}_1", em["line1"], em["pos1"]))
            candidates.append((f"X{i}_2", em["line2"], em["pos2"]))

        for tag, line, pos in candidates:
            if line is None or pos is None:
                continue
            line_scene_x = vb.mapViewToScene(pg.Point(pos, 0)).x()
            dist = abs(scene_pos.x() - line_scene_x)
            if dist < best_dist:
                best_dist = dist
                best = tag
        return best

    def eventFilter(self, obj, event):
        if obj is getattr(self, "clear_markers_btn", None):
            if event.type() == QEvent.Enter and obj.isEnabled():
                obj.setIcon(self._clear_markers_icon_hover)
            elif event.type() == QEvent.Leave:
                obj.setIcon(self._clear_markers_icon_normal)
            return False
        if obj is self.plot_widget and event.type() == QEvent.Leave:
            self._hide_crosshair()
            return False
        if obj is self.plot_widget and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.RightButton:
                view_pos = event.position().toPoint()
                scene_pos = self.plot_widget.mapToScene(view_pos)
                snap_marker = self._find_nearest_marker_at_scene(scene_pos)
                if snap_marker:
                    screen_pos = self.plot_widget.viewport().mapToGlobal(view_pos)
                    self._show_marker_context_menu_at(snap_marker, screen_pos)
                    return True
                vb = self.plot_widget.getPlotItem().getViewBox()
                if (self._find_annotation_at_scene(scene_pos) is None
                        and vb.sceneBoundingRect().contains(scene_pos)):
                    screen_pos = self.plot_widget.viewport().mapToGlobal(view_pos)
                    x_val = vb.mapSceneToView(scene_pos).x()
                    self._show_marker_move_here_menu(x_val, screen_pos)
                    return True
        vb = self.plot_widget.getPlotItem().getViewBox()
        if obj is not vb:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.GraphicsSceneWheel:
            if self._selected_ch_key and self._selected_ch_key in self._band_info:
                self._wheel_scale_channel(event)
                return True

        if event.type() == QEvent.GraphicsSceneMousePress:
            if event.button() == Qt.LeftButton and self._pending_marker is None and not self.box_zoom_enabled:
                scene_pos = event.scenePos()
                if self._find_annotation_at_scene(scene_pos) is not None:
                    # 按下点在 annotation 上：交给其自身的 pyqtgraph 拖拽分发，避免误触发通道拖拽
                    return super().eventFilter(obj, event)
                snap_marker = self._find_nearest_marker_at_scene(scene_pos)
                if snap_marker:
                    self._marker_drag_target = snap_marker
                    return True

                mouse_point = vb.mapSceneToView(scene_pos)
                x = mouse_point.x()
                y = mouse_point.y()
                clicked_key = self._find_band_at_y(y, x)
                if clicked_key:
                    self._select_channel(clicked_key)
                    self._ch_drag_active = True
                    self._ch_drag_last_y = y
                    return True
                else:
                    self._deselect_channel()

        if event.type() == QEvent.GraphicsSceneMouseMove:
            scene_pos = event.scenePos()

            if self._marker_drag_target:
                mouse_point = vb.mapSceneToView(scene_pos)
                x_val = mouse_point.x()
                if self._marker_drag_target == "A":
                    self._place_marker_a(x_val)
                elif self._marker_drag_target == "B":
                    self._place_marker_b(x_val)
                elif self._marker_drag_target.startswith("X"):
                    parts = self._marker_drag_target[1:].split("_")
                    pi = int(parts[0])
                    w = parts[1]
                    if pi < len(self._extra_markers):
                        em = self._extra_markers[pi]
                        em[f"pos{w}"] = x_val
                        if em[f"line{w}"]:
                            em[f"line{w}"].setValue(x_val)
                self._update_marker_region()
                self._update_marker_analysis()
                return True

            if self._ch_drag_active and self._selected_ch_key:
                mouse_point = vb.mapSceneToView(scene_pos)
                y = mouse_point.y()
                self._drag_offset_channel(y)
                return True

            snap_marker = self._find_nearest_marker_at_scene(scene_pos)
            widget = self.plot_widget.viewport() if hasattr(self.plot_widget, 'viewport') else self.plot_widget
            if snap_marker:
                widget.setCursor(Qt.SizeHorCursor)
            else:
                widget.unsetCursor()

        if event.type() == QEvent.GraphicsSceneMouseRelease:
            if event.button() == Qt.LeftButton:
                if self._marker_drag_target:
                    self._marker_drag_target = None
                    return True
                if self._ch_drag_active:
                    self._ch_drag_active = False
                    self._ch_drag_last_y = None
                    return True

        return super().eventFilter(obj, event)

    def _compute_band_edges(self, n):
        """计算 n 个均分 band 的 (band_top, band_bottom) 列表（自顶向下累计）。"""
        if n <= 0:
            return []
        edges = []
        top = _BAND_CEILING
        frac = _BAND_CEILING / n
        for _ in range(n):
            bottom = top - frac
            edges.append((top, bottom))
            top = bottom
        return edges

    def _rebuild_band_grid_lines(self):
        """纵轴点线网格：8 格均分整个图表区域纵向高度（与通道 band 划分无关）。"""
        for line in self._band_grid_lines:
            try:
                self.plot_widget.removeItem(line)
            except Exception:
                pass
        self._band_grid_lines.clear()
        for _ in range(7):
            grid_line = pg.InfiniteLine(
                pos=0, angle=0, movable=False,
                pen=pg.mkPen(color=(142, 176, 227, 100), width=1, style=Qt.DotLine),
            )
            grid_line.setZValue(-11)
            self.plot_widget.addItem(grid_line, ignoreBounds=True)
            self._band_grid_lines.append(grid_line)
        self._update_grid_line_positions()

    def _update_grid_line_positions(self):
        """按当前可见 Y 范围 8 格均分重定位网格线（挂入 _on_range_changed 实时跟随）。"""
        if not self._band_grid_lines:
            return
        y_min, y_max = self.plot_widget.getPlotItem().getViewBox().viewRange()[1]
        step = (y_max - y_min) / 8
        for k, line in enumerate(self._band_grid_lines, start=1):
            line.setPos(y_min + k * step)

    def _find_band_at_y(self, y, x=None):
        vb = self.plot_widget.getPlotItem().getViewBox()
        view_height_px = vb.screenGeometry().height() or 1
        view_width_px = vb.screenGeometry().width() or 1
        y_min, y_max = vb.viewRange()[1]
        x_min, x_max = vb.viewRange()[0]
        y_range = y_max - y_min if y_max > y_min else 1.0
        x_range = x_max - x_min if x_max > x_min else 1.0
        px_to_view_y = y_range / view_height_px
        px_to_view_x = x_range / view_width_px
        snap_view = px_to_view_y * 20
        half_px_x = px_to_view_x * 3

        best_key = None
        best_dist = snap_view + 1

        for key, band in self._band_info.items():
            curve = self.plot_curves.get(key)
            if curve is None or not curve.isVisible():
                continue

            if x is None:
                if band["band_bottom"] <= y <= band["band_top"]:
                    return key
                continue

            xData = curve.xData
            yData = curve.yData
            if xData is None or yData is None or len(xData) == 0:
                continue

            i_lo = bisect_left(xData, x - half_px_x)
            i_hi = bisect_right(xData, x + half_px_x)
            if i_hi <= i_lo:
                idx = bisect_left(xData, x)
                i_lo = max(0, idx - 1)
                i_hi = min(len(yData), idx + 2)
            nearby_y = yData[i_lo:i_hi]
            if len(nearby_y) == 0:
                continue

            t = curve.transform()
            sy = t.m22()
            ty = t.dy()
            y_near_min = float(min(nearby_y)) * sy + ty
            y_near_max = float(max(nearby_y)) * sy + ty
            if y_near_min > y_near_max:
                y_near_min, y_near_max = y_near_max, y_near_min

            if y < y_near_min - snap_view or y > y_near_max + snap_view:
                continue

            mid = (y_near_min + y_near_max) / 2.0
            dist = abs(y - mid)
            if dist < best_dist:
                best_dist = dist
                best_key = key

        return best_key

    def _select_channel(self, key):
        if self._selected_ch_key == key:
            return
        self._deselect_channel()
        self._selected_ch_key = key
        curve = self.plot_curves.get(key)
        if not curve:
            return
        pen = curve.opts.get("pen")
        if pen:
            self._selected_orig_pen = pg.mkPen(pen)
            color = _color_for_label(key)
            curve.setPen(pg.mkPen(color=color, width=3))

    def _deselect_channel(self):
        if self._selected_ch_key and hasattr(self, '_selected_orig_pen') and self._selected_orig_pen:
            curve = self.plot_curves.get(self._selected_ch_key)
            if curve:
                curve.setPen(self._selected_orig_pen)
        self._selected_ch_key = None
        self._selected_orig_pen = None
        self._ch_drag_active = False
        self._ch_drag_last_y = None

    def _wheel_scale_channel(self, event):
        key = self._selected_ch_key
        band = self._band_info.get(key)
        if not band:
            return

        delta = event.delta()
        factor = 0.9 if delta > 0 else 1.1

        raw_min = band["raw_min"]
        raw_range = band["raw_range"]
        raw_center = raw_min + raw_range / 2.0

        new_range = raw_range * factor
        new_min = raw_center - new_range / 2.0
        new_max = raw_center + new_range / 2.0

        band["raw_min"] = new_min
        band["raw_max"] = new_max
        band["raw_range"] = new_range

        self._redraw_single_channel(key)
        self._update_ch_scale_offset_display(key)

    def _drag_offset_channel(self, y):
        key = self._selected_ch_key
        band = self._band_info.get(key)
        if not band or self._ch_drag_last_y is None:
            self._ch_drag_last_y = y
            return

        dy = y - self._ch_drag_last_y
        self._ch_drag_last_y = y

        plot_range = band["plot_range"]
        if plot_range == 0:
            return

        raw_range = band["raw_range"]
        raw_shift = -dy / plot_range * raw_range

        band["raw_min"] += raw_shift
        band["raw_max"] += raw_shift

        self._redraw_single_channel(key)
        self._update_ch_scale_offset_display(key)

    def _redraw_single_channel(self, key):
        band = self._band_info.get(key)
        curve = self.plot_curves.get(key)
        if not band or not curve:
            return

        raw_min = band["raw_min"]
        raw_range = band["raw_range"]
        plot_bottom = band["plot_bottom"]
        plot_range = band["plot_range"]
        init_min = band.get("init_raw_min", raw_min)
        init_range = band.get("init_raw_range", raw_range)

        if raw_range == 0:
            raw_range = 1.0
        if init_range == 0:
            init_range = 1.0

        sy = init_range / raw_range
        ty = plot_bottom * (1.0 - sy) + (init_min - raw_min) * plot_range / raw_range

        curve.setTransform(QTransform(1.0, 0.0, 0.0, sy, 0.0, ty))
        self._update_ch_label_positions()
        self._update_band_zero_lines()

    def _update_ch_scale_offset_display(self, key):
        band = self._band_info.get(key)
        if not band:
            return
        raw_min = band["raw_min"]
        raw_range = band["raw_range"]
        raw_center = raw_min + raw_range / 2.0
        raw_div = raw_range / 5.0

        ch_unit = _unit_for_label(key)
        scale_str = _auto_format(raw_div, ch_unit)
        offset_str = _auto_format(raw_center, ch_unit)
        self._set_ch_scale_offset_text(key.strip(), scale_str, offset_str)

    def _on_mouse_moved(self, evt):
        pos = evt[0]
        vb = self.plot_widget.getPlotItem().getViewBox()
        # SignalProxy(rateLimit=30) 会延迟投递最后一个 sigMouseMoved（慢速移出时），
        # 在 Leave 隐藏之后才触发导致预览线残留，须以真实光标位置为准
        cursor_inside = self.plot_widget.rect().contains(
            self.plot_widget.mapFromGlobal(QCursor.pos())
        )
        if not cursor_inside or not self.plot_widget.sceneBoundingRect().contains(pos):
            self._hide_crosshair()
            return

        mouse_point = vb.mapSceneToView(pos)
        x = mouse_point.x()

        if self._pending_marker is not None:
            self._marker_follow_line.setPos(x)
            self._marker_follow_line.setVisible(True)

        self.crosshair_v.setPos(x)
        self.crosshair_v.setVisible(True)

        for dot in self.crosshair_dots:
            try:
                self.plot_widget.removeItem(dot)
            except Exception:
                pass
        self.crosshair_dots.clear()

        if not self.datalog_data:
            self.tooltip_text.setVisible(False)
            return

        visible_keys = self._get_visible_keys()
        if not visible_keys:
            visible_keys = set(self.datalog_data.keys())

        lines = [f"Time: {x:.4f} s"]

        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        for idx, label in enumerate(sorted_keys):
            if label not in visible_keys:
                continue
            ch_data = self.datalog_data[label]
            raw_times = ch_data["time"]
            eff_times = self._get_effective_times(label, raw_times)
            values = ch_data["values"]
            if not raw_times:
                continue

            lookup_x = self._effective_x_for_lookup(label, x)
            i = self._find_nearest_index(raw_times, lookup_x)
            if i is not None:
                val = values[i]
                color = _color_for_label(label)
                ch_unit = _unit_for_label(label)
                lines.append(f"<span style='color:{color}'>{_display_label(label)} : {_auto_format(val, ch_unit)}</span>")

                band = self._band_info.get(label)
                if band:
                    norm_y = band["plot_bottom"] + (val - band["raw_min"]) / band["raw_range"] * band["plot_range"]
                else:
                    norm_y = val

                dot = pg.ScatterPlotItem(
                    [eff_times[i]], [norm_y], size=10,
                    pen=pg.mkPen(color=color, width=2),
                    brush=pg.mkBrush(color="#071127"),
                    symbol='o'
                )
                self.plot_widget.addItem(dot)
                self.crosshair_dots.append(dot)

        html = "<br>".join(lines)
        self.tooltip_text.setHtml(
            f"<div style='padding:4px; font-size:11px;'>{html}</div>"
        )
        self.tooltip_text.setPos(mouse_point)
        self.tooltip_text.setVisible(True)

    def _find_nearest_index(self, times, x):
        if not times:
            return None
        if x <= times[0]:
            return 0
        if x >= times[-1]:
            return len(times) - 1
        lo, hi = 0, len(times) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if times[mid] <= x:
                lo = mid
            else:
                hi = mid
        if abs(times[lo] - x) <= abs(times[hi] - x):
            return lo
        return hi

    def _refresh_plot(self):
        self.plot_widget.clear()
        self.plot_curves.clear()
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_region = None
        for em in self._extra_markers:
            em["line1"] = None
            em["line2"] = None
        self._extra_marker_regions = []
        self._extra_marker_text_items = []
        self._marker_ab_text_item = None
        self._band_info = {}
        self._band_grid_lines = []
        self._band_zero_lines = {}
        self._selected_ch_key = None
        self._selected_orig_pen = None
        self._selected_highlight = None
        self._ch_drag_active = False
        self._ch_drag_last_y = None
        self._marker_drag_target = None
        self._update_x_limits()

        self.crosshair_v = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color="#4a6a9e", width=1, style=Qt.DashLine)
        )
        self.crosshair_v.setVisible(False)
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)

        self.tooltip_text = pg.TextItem(
            text="", color="#dbe7ff",
            anchor=(1, 1),
            fill=pg.mkBrush(10, 20, 45, 220),
            border=pg.mkPen(color="#2a4272")
        )
        self.tooltip_text.setVisible(False)
        self.tooltip_text.setZValue(100)
        self.plot_widget.addItem(self.tooltip_text, ignoreBounds=True)

        self.legend = None

        n = len(self.datalog_data)
        if n == 0:
            self._rebuild_ch_name_panel([])
            self._update_marker_analysis()
            return

        all_sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        visible_keys = self._get_visible_keys()
        sorted_keys = [k for k in all_sorted_keys if k in visible_keys]
        n = len(sorted_keys)

        left_axis = self.plot_widget.getPlotItem().getAxis("left")
        left_axis.setTicks([])
        left_axis.setLabel("")
        left_axis.setWidth(0)

        panel_entries = []

        if n == 0:
            self._rebuild_ch_name_panel([])
            self._update_marker_analysis()
            return

        band_edges = self._compute_band_edges(n)

        for idx, label in enumerate(sorted_keys):
            ch_data = self.datalog_data[label]
            color = _color_for_label(label)
            times = self._get_effective_times(label, ch_data["time"])
            raw_vals = ch_data["values"]

            if not raw_vals:
                continue

            raw_min = min(raw_vals)
            raw_max = max(raw_vals)
            raw_range = raw_max - raw_min if raw_max > raw_min else 1.0

            band_top, band_bottom = band_edges[idx]
            margin = (band_top - band_bottom) * 0.08
            plot_top = band_top - margin
            plot_bottom = band_bottom + margin
            plot_range = plot_top - plot_bottom

            norm_vals = plot_bottom + (np.asarray(raw_vals, dtype=np.float64) - raw_min) * (plot_range / raw_range)

            self._band_info[label] = {
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

            pen = pg.mkPen(color=color, width=1.5)
            curve = self.plot_widget.plot(
                times, norm_vals,
                pen=pen
            )
            curve.setClipToView(True)
            curve.setDownsampling(auto=True, method='peak')
            self.plot_curves[label] = curve

            panel_entries.append((label, color))

            raw_center = (raw_min + raw_max) / 2
            raw_div = raw_range / 5
            ch_unit = _unit_for_label(label)
            scale_str = _auto_format(raw_div, ch_unit)
            offset_str = _auto_format(raw_center, ch_unit)
            self._set_ch_scale_offset_text(label.strip(), scale_str, offset_str)

        if self.datalog_data:
            all_times = []
            for lbl, ch_data in self.datalog_data.items():
                all_times.extend(self._get_effective_times(lbl, ch_data["time"]))
            if all_times:
                self.plot_widget.setXRange(min(all_times), max(all_times))
            y_bottom, y_top = self._compute_y_range_with_labels()
            self.plot_widget.setYRange(y_bottom, y_top)

        self._rebuild_ch_name_panel(panel_entries)

        self._restore_markers()
        self._restore_label_lines()
        self._update_marker_analysis()
        self._refresh_label_ch_combo()

    def _update_x_limits(self):
        # 横轴视图限制在数据时间范围内（含 B 机/文件对齐时差），
        # 防止以鼠标为中心缩放或平移时出现数据范围外的无意义空白区
        vb = self.plot_widget.getPlotItem().getViewBox()
        x_min = None
        x_max = None
        for lbl, ch_data in self.datalog_data.items():
            times = ch_data["time"]
            if not times:
                continue
            off = self._get_total_time_offset(lbl)
            t0 = times[0] + off
            t1 = times[-1] + off
            x_min = t0 if x_min is None else min(x_min, t0)
            x_max = t1 if x_max is None else max(x_max, t1)
        if x_min is None or x_max - x_min <= 0:
            vb.setLimits(xMin=None, xMax=None, maxXRange=None)
            return
        vb.setLimits(xMin=x_min, xMax=x_max, maxXRange=x_max - x_min)

    def _reset_view(self):
        if not self.datalog_data:
            self.plot_widget.setXRange(0, 10)
            self.plot_widget.setYRange(-0.02, 1.02)
            return

        if self.box_zoom_enabled:
            self.box_zoom_enabled = False
            self._box_zoom_auto_off_timer.stop()
            self.box_zoom_btn.setChecked(False)
            self.box_zoom_btn.setToolTip("框选缩放: OFF")
        if self._pending_marker is not None:
            self._clear_marker_mode()

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.setMouseMode(vb.PanMode)
        self.plot_widget.setMouseEnabled(x=True, y=False)

        visible_keys = self._get_visible_keys()
        if not visible_keys:
            visible_keys = set(self.datalog_data.keys())

        all_times = []
        for key in visible_keys:
            ch_data = self.datalog_data.get(key)
            if ch_data and ch_data["time"]:
                all_times.extend(self._get_effective_times(key, ch_data["time"]))

        if all_times:
            self.plot_widget.setXRange(min(all_times), max(all_times))

        self._on_channel_visibility_changed()

    def _toggle_box_zoom(self):
        self.box_zoom_enabled = not self.box_zoom_enabled
        if self.box_zoom_enabled:
            if self._pending_marker is not None:
                self._clear_marker_mode()
            self.box_zoom_btn.setChecked(True)
            self.box_zoom_btn.setToolTip("框选缩放: ON - 请在图表上拖拽")
            self.plot_widget.setMouseEnabled(x=True, y=True)
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.RectMode)
            self._box_zoom_auto_off_timer.start()
        else:
            self._box_zoom_auto_off_timer.stop()
            self.box_zoom_btn.setChecked(False)
            self.box_zoom_btn.setToolTip("框选缩放: OFF")
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.PanMode)
            self.plot_widget.setMouseEnabled(x=True, y=False)
            y_bottom, y_top = self._compute_y_range_with_labels()
            self.plot_widget.setYRange(y_bottom, y_top)

    def _auto_off_box_zoom(self):
        if self.box_zoom_enabled:
            self.box_zoom_enabled = False
            self.box_zoom_btn.setChecked(False)
            self.box_zoom_btn.setToolTip("框选缩放: OFF")
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.PanMode)
            self.plot_widget.setMouseEnabled(x=True, y=False)
            y_bottom, y_top = self._compute_y_range_with_labels()
            self.plot_widget.setYRange(y_bottom, y_top)

    def _on_range_changed(self):
        self._update_ch_label_positions()
        self._update_custom_label_positions()
        self._update_grid_line_positions()
        self._update_scale_offset_from_view()
        if self.box_zoom_enabled and self._box_zoom_auto_off_timer.isActive():
            self._box_zoom_auto_off_timer.start()

    def _update_scale_offset_from_view(self):
        if not self.datalog_data or not self._band_info:
            return

        vb = self.plot_widget.getPlotItem().getViewBox()
        y_min, y_max = vb.viewRange()[1]
        y_span = y_max - y_min

        for key, band in self._band_info.items():
            plot_top = band["plot_top"]
            plot_bottom = band["plot_bottom"]
            plot_range = band["plot_range"]
            raw_min = band["raw_min"]
            raw_range = band["raw_range"]

            if plot_range == 0:
                continue

            visible_data_min = raw_min + (y_min - plot_bottom) / plot_range * raw_range
            visible_data_max = raw_min + (y_max - plot_bottom) / plot_range * raw_range
            visible_data_range = visible_data_max - visible_data_min
            visible_center = (visible_data_min + visible_data_max) / 2
            visible_div = visible_data_range / 10

            ch_unit = _unit_for_label(key)
            scale_str = _auto_format(visible_div, ch_unit)
            offset_str = _auto_format(visible_center, ch_unit)
            self._set_ch_scale_offset_text(key.strip(), scale_str, offset_str)

    def _update_band_zero_lines(self):
        # 每通道纵向 0 刻度强调线：0 落在该通道当前显示量程内时显示，
        # 位置随拖动/滚轮/Scale 编辑后的 raw 映射实时更新
        for key in list(self._band_zero_lines):
            if key not in self._band_info:
                try:
                    self.plot_widget.removeItem(self._band_zero_lines[key])
                except Exception:
                    pass
                self._band_zero_lines.pop(key, None)
        for key, band in self._band_info.items():
            line = self._band_zero_lines.get(key)
            if line is None:
                line = pg.InfiniteLine(
                    angle=0, movable=False,
                    pen=pg.mkPen(color=(190, 212, 245, 130), width=1),
                )
                line.setZValue(-9)
                self.plot_widget.addItem(line, ignoreBounds=True)
                self._band_zero_lines[key] = line
            raw_min = band["raw_min"]
            raw_max = band["raw_max"]
            if raw_min < 0.0 < raw_max:
                zero_y = band["plot_bottom"] + (0.0 - raw_min) * band["plot_range"] / band["raw_range"]
                line.setPos(zero_y)
                line.setVisible(True)
            else:
                line.setVisible(False)

    def _is_8ch_mode(self):
        return self.is_connected_b
