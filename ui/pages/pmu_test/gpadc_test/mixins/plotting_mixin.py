"""GPADCTestUI 曲线绘制 / 悬浮预览 / 空占位 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
类装配见 gpadc_test_ui.py。"""

from ui.styles import SCROLL_AREA_STYLE
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QApplication, QSizePolicy,
    QScrollArea, QMenu, QTabWidget
)
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QAction, QPainter, QCursor
import math
from log_config import get_logger
from ui.theme import FONT_MONO
from core.pmu_test.gpadc import compute_detailed_stats, describe_algorithm

logger = get_logger(__name__)

# Force Voltage 曲线悬浮命中半径（x/y 归一化到各自轴量程后的欧氏距离阈值）
_FV_HOVER_RADIUS = 0.015


class _PlottingMixin:
    """曲线绘制 / 悬浮预览 / 空占位 Mixin"""

    def _is_curve_view_enabled(self, name: str) -> bool:
        """Curve View 选项开关：mean / band / error。"""
        mapping = {
            'mean': self.show_mean_btn,
            'band': self.show_band_btn,
            'error': self.show_error_btn,
        }
        btn = mapping.get(name)
        return btn is not None and btn.isChecked()

    def _set_curve_view_all(self, enabled: bool = True):
        """一次性设置全部 Curve View 选项（blockSignals 防止自动重绘副作用）。"""
        for btn in (self.show_mean_btn, self.show_band_btn, self.show_error_btn):
            btn.blockSignals(True)
            btn.setChecked(enabled)
            btn.blockSignals(False)

    def _attach_curve_context_menu(self, pw):
        """给 PlotWidget 挂 Curve View 右键菜单（同时禁用 pyqtgraph 自带菜单避免冲突）。"""
        pw.setContextMenuPolicy(Qt.CustomContextMenu)
        pw.customContextMenuRequested.connect(self._show_curve_view_menu)
        try:
            pw.plotItem.vb.setMenuEnabled(False)
        except Exception:
            pass

    def _show_curve_view_menu(self, pos):
        """图表右键菜单：勾选启用单次数据显示项（与 Curve View 按钮同步）。"""
        sender = self.sender()
        menu = QMenu("Curve View", self)
        entries = (
            ("Voltage / Mean", self.show_mean_btn),
            ("Min-Max Band", self.show_band_btn),
            ("Error", self.show_error_btn),
        )
        for text, btn in entries:
            act = QAction(text, menu)
            act.setCheckable(True)
            act.setChecked(btn.isChecked())
            # 勾选变化直接同步按钮状态（按钮 toggled 会触发自动重绘）
            act.toggled.connect(btn.setChecked)
            menu.addAction(act)
        global_pos = sender.mapToGlobal(pos) if sender is not None else pos
        menu.exec(global_pos)

    def _on_curve_view_changed(self):
        """Curve View 选项切换后按当前显示内容重绘（优先对比图，其次载入记录）。"""
        checked = self._get_checked_records()
        curve_records = [r for r in checked if r['kind'] in self._CURVE_KINDS]
        if len(curve_records) >= 2:
            self._plot_comparison_curves(curve_records)
            return
        if self._loaded_record is not None and self._loaded_record['kind'] in self._CURVE_KINDS:
            self._load_recent_record(self._loaded_record)

    def _plot_comparison_curves(self, records):
        """把勾选的多条记录曲线画到同一张对比图上（按 Curve View 选项过滤）。"""
        try:
            import pyqtgraph as pg
            import numpy as np

            self._clear_chart_placeholder()
            layout = self.chart_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(self.chart_placeholder)
            layout.setContentsMargins(14, 14, 14, 10)
            layout.setSpacing(8)

            show_mean = self._is_curve_view_enabled('mean')
            show_band = self._is_curve_view_enabled('band')
            show_error = self._is_curve_view_enabled('error')
            if not (show_mean or show_band or show_error):
                self._append_log("[WARN] Curve View 未勾选任何曲线类型，请至少勾选 Mean / Min-Max / Error 之一")
                return

            first_kind = records[0]['kind']
            if first_kind == 'high_low_temp':
                x_title, y_title = "Input Temperature (°C)", "Calibrated Temperature (°C)"
            elif first_kind == 'temp_consistency':
                x_title, y_title = "Input Voltage (V)", "ADC Code"
            else:
                x_title, y_title = "Input Voltage (V)", "Calibrated Voltage (V)"
            kinds = {r['kind'] for r in records}
            if len(kinds) > 1:
                self._append_log("[WARN] 所选记录测试类型不一致，坐标轴单位按首条记录显示，请谨慎解读")

            # 选中高亮：目标记录加粗，其余淡化（未选中任何记录时全部正常显示）
            highlight_id = self._highlight_record_id
            dim_others = highlight_id is not None and any(r['id'] == highlight_id for r in records)

            legend_row = QHBoxLayout()
            legend_row.addStretch()
            for r in records:
                color = self._record_color(r['id'])
                is_hl = dim_others and r['id'] == highlight_id
                lbl = QLabel(
                    f"● #{r['id']} {self._record_display_name(r)} {r['time'].strftime('%m-%d %H:%M')}"
                )
                style = f"color: {color}; font-size: 11px;"
                if is_hl:
                    style += " font-weight: bold;"
                lbl.setStyleSheet(style)
                legend_row.addWidget(lbl)
                legend_row.addSpacing(12)
            legend_row.addStretch()
            layout.addLayout(legend_row)

            pw = pg.PlotWidget()
            pw.setBackground("#0a1735")
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.setLabel("left", y_title, color="#a0b4d8")
            pw.setLabel("bottom", x_title, color="#a0b4d8")
            for axis_name in ("left", "bottom"):
                axis = pw.getAxis(axis_name)
                axis.setTextPen(pg.mkPen("#a0b4d8"))
                axis.setPen(pg.mkPen("#3a4f7a"))
            self._attach_curve_context_menu(pw)

            plotted = 0
            for r in records:
                plotted += self._plot_comparison_record(
                    pw, r, self._record_color(r['id']),
                    show_mean=show_mean, show_band=show_band, show_error=show_error,
                    dimmed=dim_others and r['id'] != highlight_id,
                )

            layout.addWidget(pw, 1)

            x_label = QLabel(x_title)
            x_label.setAlignment(Qt.AlignCenter)
            x_label.setObjectName("muted_label")
            layout.addWidget(x_label)

            self._append_log(f"[INFO] 对比图已绘制：{len(records)} 条记录共 {plotted} 条曲线")
        except Exception as e:
            self._append_log(f"[ERROR] 绘制对比曲线失败: {e}")
            logger.error("绘制对比曲线失败: %s", e, exc_info=True)

    def _plot_comparison_record(self, pw, record, color, show_mean=True, show_band=False, show_error=False, dimmed=False):
        """把单条记录的曲线画到对比图上，返回绘制的曲线条数。

        dimmed=True 时曲线/符号/包络带半透明（用于选中高亮时淡化其它记录）。
        """
        import pyqtgraph as pg
        import numpy as np

        line_color = QColor(color)
        sym_color = QColor(color)
        if dimmed:
            line_color.setAlpha(90)
            sym_color.setAlpha(90)

        kind = record['kind']
        if kind in ('force_voltage', 'high_low_temp'):
            calib = record.get('calibration') or {}
            raw = record.get('raw') or {}
            x_data = calib.get('voltage')
            y_mean = calib.get('mean_cali')
            y_min = calib.get('min_cali')
            y_max = calib.get('max_cali')
            x_raw = raw.get('voltage')
            y_raw_mean = raw.get('mean')
            y_raw_min = raw.get('min')
            y_raw_max = raw.get('max')
            if not x_data or not y_mean:
                x_data, y_mean, y_min, y_max = x_raw, y_raw_mean, y_raw_min, y_raw_max
            if not x_data or not y_mean:
                self._append_log(f"[WARN] 记录 #{record['id']} 缺少曲线数据，已跳过")
                return 0
            x = np.array(x_data, dtype=float)
            y = np.array(y_mean, dtype=float)
            n = min(len(x), len(y))
            x, y = x[:n], y[:n]
            count = 0
            if show_band and y_min and y_max:
                y_min_arr = np.array(y_min, dtype=float)[:n]
                y_max_arr = np.array(y_max, dtype=float)[:n]
                band_alpha = 15 if dimmed else 35
                pw.addItem(pg.FillBetweenItem(
                    pg.PlotDataItem(x, y_max_arr),
                    pg.PlotDataItem(x, y_min_arr),
                    brush=pg.mkBrush(240, 160, 64, band_alpha),
                ))
                pw.plot(x, y_max_arr, pen=pg.mkPen(line_color, width=1, style=pg.QtCore.Qt.DashLine))
                pw.plot(x, y_min_arr, pen=pg.mkPen(line_color, width=1, style=pg.QtCore.Qt.DashLine))
                count += 1
            if show_mean:
                pw.plot(x, y, pen=pg.mkPen(line_color, width=2),
                        symbol="o", symbolSize=4, symbolBrush=sym_color, symbolPen=None)
                count += 1
            if show_error:
                diff = y - x
                pw.plot(x, diff, pen=pg.mkPen(line_color, width=2, style=pg.QtCore.Qt.DashLine),
                        symbol="t", symbolSize=5, symbolBrush=sym_color, symbolPen=None)
                count += 1
            return count

        # temp_consistency：每个温度一条线（同一记录统一用其专属色）
        raw = record.get('raw') or {}
        voltage_pts = raw.get('voltage')
        mean_matrix = raw.get('mean')
        if not voltage_pts or not mean_matrix:
            self._append_log(f"[WARN] 记录 #{record['id']} 缺少曲线数据，已跳过")
            return 0
        x = np.array(voltage_pts, dtype=float)
        count = 0
        for row in mean_matrix:
            y = np.array(row, dtype=float)
            n = min(len(x), len(y))
            if n == 0:
                continue
            pw.plot(x[:n], y[:n], pen=pg.mkPen(line_color, width=1),
                    symbol="o", symbolSize=3, symbolBrush=sym_color, symbolPen=None)
            count += 1
        return count

    def _build_default_chart_placeholder(self):
        """构建/重置图表占位符为初始空坐标系（新测试开始时复用）。"""
        self._clear_chart_placeholder()
        layout = self.chart_placeholder.layout()
        if layout is None:
            layout = QVBoxLayout(self.chart_placeholder)
        layout.setContentsMargins(22, 22, 22, 18)
        layout.setSpacing(12)

        legend_row = QHBoxLayout()
        legend_row.addStretch()

        is_cnt_test = self.current_test_item == self.TEST_1000CNT
        is_ft_test = self.current_test_item == self.TEST_FT_CALIB_CHECK

        if is_cnt_test:
            actual_text, ideal_text = "● Deviation from AVG", "─ AVG Level"
        elif is_ft_test:
            actual_text, ideal_text = "● Calib Error (mV)", "┄ Limit Lines"
        else:
            actual_text, ideal_text = "↔ Actual Code", "↔ Ideal Code"
        actual_legend = QLabel(actual_text)
        actual_legend.setStyleSheet("color: #00d39a; font-size: 12px;")
        ideal_legend = QLabel(ideal_text)
        ideal_legend.setStyleSheet("color: #7e96bf; font-size: 12px;")

        legend_row.addWidget(actual_legend)
        legend_row.addWidget(ideal_legend)
        legend_row.addStretch()
        layout.addLayout(legend_row)

        plot_area = QFrame()
        plot_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        plot_area.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-left: 1px solid #6f7fa5;
                border-bottom: 1px solid #6f7fa5;
                border-top: 1px dashed rgba(126,150,191,0.18);
                border-right: none;
                border-radius: 0px;
            }
        """)
        layout.addWidget(plot_area, 1)

        x_label = QLabel("Sample Index" if is_cnt_test else "Input Voltage (V)")
        x_label.setAlignment(Qt.AlignCenter)
        x_label.setObjectName("muted_label")
        layout.addWidget(x_label)

    def _reset_result_display(self):
        """新测试开始时清除上一次的曲线与结果，避免新旧数据混显。"""
        self.clear_results()
        self._export_data = None
        self._chart_image_bytes = None
        self._loaded_record = None
        self._fv_hover_data = None
        self._fv_hover_last_idx = -1
        self._build_default_chart_placeholder()

    def _clear_chart_placeholder(self):
        # 重绘/清空图表前隐藏悬浮预览，避免旧预览残留
        self._fv_preview_hide()
        existing = self.chart_placeholder.layout()
        if existing is not None:
            while existing.count():
                item = existing.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    sub = item.layout()
                    if sub is not None:
                        while sub.count():
                            sub_item = sub.takeAt(0)
                            sub_widget = sub_item.widget()
                            if sub_widget is not None:
                                sub_widget.deleteLater()

    # ------------------------------------------------------------------
    # Force Voltage 曲线逐点悬浮预览（原始数据 / 算法处理后数据）
    # ------------------------------------------------------------------

    def _attach_fv_hover(self, pw):
        """给主图挂悬浮预览：鼠标接近曲线点时显示该点逐样本数据预览。"""
        self._fv_hover_last_idx = -1
        pw.scene().sigMouseMoved.connect(lambda pos, _pw=pw: self._on_fv_mouse_moved(_pw, pos))
        # sigMouseMoved 只在图表面口内触发，离开需 Leave 事件兜底隐藏
        pw.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        """光标离开图表视口时隐藏悬浮预览。"""
        if event.type() == QEvent.Leave:
            self._fv_preview_hide()
        return super().eventFilter(obj, event)

    def _fv_preview_show(self, global_pos):
        """显示/移动悬浮预览窗（自定义 QLabel，生命周期完全自控，不随鼠标移动消失）。"""
        if self._fv_preview_label is None:
            self._fv_preview_label = QLabel(None, Qt.ToolTip)
            self._fv_preview_label.setStyleSheet(
                "background-color: #0d1b3e; color: #dce6f8; border: 1px solid #24365e;"
                "padding: 6px 8px; font-size: 11px;"
            )
        label = self._fv_preview_label
        if label.text() != self._fv_hover_text_cache:
            label.setText(self._fv_hover_text_cache)
            label.adjustSize()
        x = global_pos.x() + 14
        y = global_pos.y() + 16
        screen = QApplication.screenAt(global_pos)
        if screen is not None:
            area = screen.availableGeometry()
            if x + label.width() > area.right():
                x = global_pos.x() - label.width() - 14
            if y + label.height() > area.bottom():
                y = global_pos.y() - label.height() - 16
        label.move(x, y)
        if not label.isVisible():
            label.show()

    def _fv_preview_hide(self):
        if self._fv_preview_label is not None:
            self._fv_preview_label.hide()
        self._fv_hover_last_idx = -1

    def _on_fv_mouse_moved(self, pw, pos):
        """悬浮命中检测：x/y 归一化后取最近点，命中显示预览（跟随光标），未命中/离开隐藏。"""
        data = self._fv_hover_data
        if not data:
            return
        try:
            vb = pw.plotItem.vb
            inside = vb.sceneBoundingRect().contains(pos)
            view_pos = vb.mapSceneToView(pos) if inside else None
        except RuntimeError:
            return
        if not inside:
            self._fv_preview_hide()
            return
        xs = data.get('x') or []
        ys = data.get('y') or []
        if not xs or not ys:
            return
        vx, vy = view_pos.x(), view_pos.y()
        x_span = (max(xs) - min(xs)) or 1.0
        y_span = (max(ys) - min(ys)) or 1.0
        best_idx = -1
        best_d = _FV_HOVER_RADIUS
        for i in range(len(xs)):
            dx = (xs[i] - vx) / x_span
            dy = (ys[i] - vy) / y_span
            d = math.hypot(dx, dy)
            if d < best_d:
                best_d = d
                best_idx = i
        if best_idx < 0:
            self._fv_preview_hide()
            return
        if best_idx != self._fv_hover_last_idx:
            self._fv_hover_last_idx = best_idx
            self._fv_hover_text_cache = self._fv_hover_text(best_idx)
        self._fv_preview_show(QCursor.pos())

    def _fv_hover_text(self, idx):
        """悬浮预览文本：按模式分发（Force Voltage 逐点 / 1000CNT 逐样本）。"""
        data = self._fv_hover_data or {}
        if data.get('mode') == 'cnt':
            return self._cnt_hover_text(idx)
        xs = data.get('x') or []
        if idx >= len(xs):
            return ""
        lines = [f"<b>V = {xs[idx]:.4f} V</b>（点 {idx + 1}/{len(xs)}）"]
        raw_samples = data.get('raw_samples') or []
        raw_before = data.get('raw_before') or []
        before = raw_before[idx] if idx < len(raw_before) else None
        proc = raw_samples[idx] if idx < len(raw_samples) else None
        if before:
            lines.append(self._fv_series_line("RAW", before))
        if proc:
            tag = f"PROC ({describe_algorithm(data.get('algorithm'))})" if before else "RAW"
            lines.append(self._fv_series_line(tag, proc))
        if not before and not proc:
            lines.append("（该记录无逐点样本数据）")
        return "<br>".join(lines)

    def _fv_series_line(self, tag, samples):
        """单组样本的预览：AVG/STD/P-P/N 统计 + 前 10 个样本值。"""
        s = compute_detailed_stats(samples)
        head = ", ".join(self._fmt_data_value(v) for v in samples[:10])
        if len(samples) > 10:
            head += ", ..."
        return (f"{tag} AVG={s['avg']:.2f} STD={s['std']:.3f} P-P={s['pp']:.0f} N={s['count']}"
                f"<br><span style='color:#8fa8d0'>{head}</span>")

    def _cnt_hover_text(self, idx):
        """1000CNT 分布图悬浮文本：样本序号 + RAW（算法前）/ PROC（处理后）单值。

        算法为缩短长度类（如 debounce）时前后样本序号不对应，RAW 降级为统计提示。
        """
        data = self._fv_hover_data or {}
        raw = data.get('raw_samples') or []
        if idx >= len(raw):
            return ""
        n = len(raw)
        lines = [f"<b>样本 #{idx + 1}</b>（共 {n} 个）"]
        before = data.get('raw_before') or []
        before_avg = data.get('before_avg')
        aligned = len(before) == n
        if before and before_avg is not None:
            if aligned:
                v = before[idx]
                lines.append(f"RAW = {self._fmt_data_value(v)}（偏差 {v - before_avg:+.3f}）")
            else:
                lines.append(f"RAW 经算法重采样 {len(before)}→{n} 点，逐样本不对应"
                             f"（RAW AVG={before_avg:.2f}）")
        ys = data.get('y') or []
        dev = ys[idx] if idx < len(ys) else None
        tag = f"PROC ({describe_algorithm(data.get('algorithm'))})" if before else "RAW"
        text = f"{tag} = {self._fmt_data_value(raw[idx])}"
        if dev is not None:
            text += f"（偏差 {dev:+.3f}）"
        lines.append(text)
        return "<br>".join(lines)

    def _plot_voltage_adc_curve(self, voltage_data, mean_cali, adc_min_cali=None, adc_max_cali=None, is_temp_mode=False):
        try:
            import pyqtgraph as pg
            import numpy as np

            # Curve View 过滤（载入 Recent 记录时生效；刚完成测试时三项默认全开）
            show_mean = self._is_curve_view_enabled('mean')
            show_band = self._is_curve_view_enabled('band')
            show_error = self._is_curve_view_enabled('error')
            if not (show_mean or show_band or show_error):
                show_mean = True

            self._clear_chart_placeholder()
            layout = self.chart_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(self.chart_placeholder)
            layout.setContentsMargins(14, 14, 14, 10)
            layout.setSpacing(8)

            # 当前记录专属色（有载入记录时用其色，否则默认绿）
            curve_color = "#00d39a"
            record_name = ""
            if self._loaded_record is not None:
                curve_color = self._record_color(self._loaded_record['id'])
                record_name = f" #{self._loaded_record['id']} {self._record_display_name(self._loaded_record)} · "

            legend_row = QHBoxLayout()
            legend_row.addStretch()
            if is_temp_mode:
                cali_legend = QLabel(f"● {record_name}Calibrated Temperature (°C)")
                x_axis_title = "Input Temperature (°C)"
                y_axis_title = "Calibrated Temperature (°C)"
            else:
                cali_legend = QLabel(f"● {record_name}Calibrated Voltage (V)")
                x_axis_title = "Input Voltage (V)"
                y_axis_title = "Calibrated Voltage (V)"
            cali_legend.setStyleSheet(f"color: {curve_color}; font-size: 12px;")
            ideal_legend = QLabel("● Ideal (y = x)")
            ideal_legend.setStyleSheet("color: #7e96bf; font-size: 12px;")
            band_legend = QLabel("▨ Max/Min Error Band")
            band_legend.setStyleSheet("color: #f0a040; font-size: 12px;")
            legend_row.addWidget(cali_legend)
            legend_row.addSpacing(16)
            legend_row.addWidget(ideal_legend)
            legend_row.addSpacing(16)
            legend_row.addWidget(band_legend)
            if not is_temp_mode:
                # 误差单位按量级自适应：<1V 显示 mV，否则 V（图例与轴标题共用）
                err_arr = np.array(mean_cali, dtype=float) - np.array(voltage_data, dtype=float)
                max_abs_err = float(np.max(np.abs(err_arr))) if err_arr.size else 0.0
                err_unit = "mV" if max_abs_err < 1.0 else "V"
                err_legend = QLabel(f"● Error (Actual - Ideal) ({err_unit})")
                err_legend.setStyleSheet("color: #e05c5c; font-size: 12px;")
                legend_row.addSpacing(16)
                legend_row.addWidget(err_legend)
            legend_row.addStretch()
            layout.addLayout(legend_row)

            pw = pg.PlotWidget()
            pw.setBackground("#0a1735")
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.setLabel("left",   y_axis_title, color="#a0b4d8")
            pw.setLabel("bottom", x_axis_title, color="#a0b4d8")
            self._attach_curve_context_menu(pw)

            for axis_name in ("left", "bottom"):
                axis = pw.getAxis(axis_name)
                axis.setTextPen(pg.mkPen("#a0b4d8"))
                axis.setPen(pg.mkPen("#3a4f7a"))

            # Force Voltage 逐点悬浮预览（仅电压模式且有悬浮数据时挂载）
            if not is_temp_mode and self._fv_hover_data:
                self._attach_fv_hover(pw)

            x = np.array(voltage_data, dtype=float)
            y = np.array(mean_cali,    dtype=float)

            # Min-Max Band 下沉为主图下方独立子图：画 Max/Min 相对 Mean 的偏差，
            # Y 轴自适应 Band 宽度，测试范围宽时也能直观看出 Band 范围
            pw_band = None
            if show_band and adc_min_cali is not None and adc_max_cali is not None:
                n = min(len(x), len(y), len(adc_min_cali), len(adc_max_cali))
                bx = x[:n]
                dev_hi = np.array(adc_max_cali, dtype=float)[:n] - y[:n]
                dev_lo = np.array(adc_min_cali, dtype=float)[:n] - y[:n]

                if is_temp_mode:
                    band_unit = "°C"
                    band_scale = 1.0
                else:
                    spread = float(np.max(dev_hi - dev_lo)) if n > 0 else 0.0
                    band_unit = "mV" if spread < 1.0 else "V"
                    band_scale = 1000.0 if band_unit == "mV" else 1.0
                dev_hi = dev_hi * band_scale
                dev_lo = dev_lo * band_scale

                pw_band = pg.PlotWidget()
                pw_band.setBackground("#0a1735")
                pw_band.showGrid(x=True, y=True, alpha=0.15)
                pw_band.setLabel("left", f"Max/Min Deviation ({band_unit})", color="#f0a040")
                pw_band.plotItem.setXLink(pw.plotItem)
                self._attach_curve_context_menu(pw_band)
                for axis_name in ("left", "bottom"):
                    axis = pw_band.getAxis(axis_name)
                    axis.setTextPen(pg.mkPen("#a0b4d8"))
                    axis.setPen(pg.mkPen("#3a4f7a"))

                pw_band.addLine(y=0, pen=pg.mkPen("#7e96bf", width=1,
                                style=pg.QtCore.Qt.DashLine))
                pw_band.addItem(pg.FillBetweenItem(
                    pg.PlotDataItem(bx, dev_hi),
                    pg.PlotDataItem(bx, dev_lo),
                    brush=pg.mkBrush(240, 160, 64, 50),
                ))
                pw_band.plot(bx, dev_hi, pen=pg.mkPen(color="#f0a040", width=1,
                             style=pg.QtCore.Qt.DashLine))
                pw_band.plot(bx, dev_lo, pen=pg.mkPen(color="#f0a040", width=1,
                             style=pg.QtCore.Qt.DashLine))

            if show_mean:
                pw.plot(x, x, pen=pg.mkPen(color="#7e96bf", width=1,
                        style=pg.QtCore.Qt.DashLine))

                pw.plot(x, y, pen=pg.mkPen(color=curve_color, width=2),
                        symbol="o", symbolSize=5,
                        symbolBrush=curve_color, symbolPen=None)

            if show_error and not is_temp_mode:
                # 右 Y 轴：Actual - Ideal 差值曲线（校准电压 - 输入电压）
                # 单位与图例共用 err_unit（mV 时数据放大 1000 倍）
                diff = y - x
                if err_unit == "mV":
                    diff = diff * 1000.0

                pw.showAxis('right')
                right_axis = pw.getAxis('right')
                right_axis.setLabel(f"Error ({err_unit})", color="#e05c5c")
                right_axis.setTextPen(pg.mkPen("#e05c5c"))
                right_axis.setPen(pg.mkPen("#3a4f7a"))

                right_view = pg.ViewBox()
                right_view.setMouseEnabled(x=False, y=False)
                pw.plotItem.scene().addItem(right_view)
                right_axis.linkToView(right_view)
                right_view.setXLink(pw.plotItem)
                pw.plotItem.vb.sigResized.connect(
                    lambda: right_view.setGeometry(pw.plotItem.vb.sceneBoundingRect()))
                right_view.setGeometry(pw.plotItem.vb.sceneBoundingRect())

                right_view.addItem(pg.PlotDataItem(
                    x, diff,
                    pen=pg.mkPen(color="#e05c5c", width=2),
                    symbol="o", symbolSize=4,
                    symbolBrush="#e05c5c", symbolPen=None))

            layout.addWidget(pw, 3 if pw_band is not None else 1)
            if pw_band is not None:
                layout.addWidget(pw_band, 1)

            x_label = QLabel(x_axis_title)
            x_label.setAlignment(Qt.AlignCenter)
            x_label.setObjectName("muted_label")
            layout.addWidget(x_label)

            try:
                import io
                from pyqtgraph.exporters import ImageExporter
                from PySide6.QtCore import QBuffer, QIODevice
                from PySide6.QtGui import QImage, QPainter

                def _snapshot(item, width=1200):
                    # 仅指定宽度（同时指定 height 会按 cover 缩放导致宽度不精确）
                    exporter = ImageExporter(item)
                    exporter.parameters()['width'] = width
                    snap = exporter.export(toBytes=True)
                    if not isinstance(snap, QImage):
                        snap = QImage.fromData(bytes(snap))
                    return snap

                if pw_band is not None:
                    # 主图 + Band 子图纵向合成为一张快照（背景与图表底色一致）
                    img_main = _snapshot(pw.plotItem)
                    img_band = _snapshot(pw_band.plotItem)
                    combined = QImage(img_main.width(),
                                      img_main.height() + img_band.height(),
                                      QImage.Format_ARGB32)
                    combined.fill(QColor(10, 23, 53))
                    painter = QPainter(combined)
                    painter.drawImage(0, 0, img_main)
                    painter.drawImage(0, img_main.height(), img_band)
                    painter.end()
                    result = combined
                else:
                    result = _snapshot(pw.plotItem)

                qbuf = QBuffer()
                qbuf.open(QIODevice.WriteOnly)
                result.save(qbuf, "PNG")
                raw = bytes(qbuf.data())
                qbuf.close()
                buf = io.BytesIO(raw)
                self._chart_image_bytes = buf
            except Exception as ex:
                self._append_log(f"[WARN] Chart snapshot failed: {ex}")
                self._chart_image_bytes = None

        except Exception as e:
            self._append_log(f"[ERROR] Error plotting voltage-ADC curve: {e}")
            logger.error("Error plotting voltage-ADC curve: %s", e, exc_info=True)

    def _update_ft_result_cards(self, result):
        """FT Calibration Check 指标卡刷新（P1/P2 偏差仅 IIC 方式，CONS 仅 UART 方式）。"""
        pcs = result.get('point_checks') or []
        if len(pcs) >= 2:
            self.ft_p1_value.setText(f"{pcs[0]['dev_lsb']:+.2f}")
            self.ft_p2_value.setText(f"{pcs[1]['dev_lsb']:+.2f}")
        else:
            self.ft_p1_value.setText("---")
            self.ft_p2_value.setText("---")
        stats = result.get('stats') or {}
        self.ft_max_err_value.setText(f"{stats['max_abs_mv']:.2f}" if stats else "---")
        self.ft_rms_err_value.setText(f"{stats['rms_mv']:.2f}" if stats else "---")
        cons = result.get('cons_stats')
        self.ft_cons_value.setText(f"{cons['max_abs_mv']:.2f}" if cons else "---")
        passed = result.get('passed', False)
        self.ft_result_value.setText("PASS" if passed else "FAIL")
        color = "#00d39a" if passed else "#ff5a7a"
        self.ft_result_value.setStyleSheet(f"color: {color}; font-weight: 700;")

    def _plot_ft_check_curve(self, result):
        """FT Calibration Check 曲线：主图 = 理想曲线(y=x) + 校准电压传输曲线，
        下方子图 = 校准误差 (mV) vs 施加电压，带 ±Limit 判定线（X 轴联动，3:1）。

        UART 方式误差子图叠加一致性误差曲线（用户两点 K,B 反推电压 vs DUT volt）。
        """
        try:
            import pyqtgraph as pg
            import numpy as np

            voltage = result.get('voltage') or []
            cal_volt = result.get('cal_volt') or []
            err_mv = result.get('err_mv') or []
            cons_mv = result.get('cons_mv') or None
            limit = result.get('err_limit_mv', 0.0)
            x_title = "Input Voltage (V)"
            if not voltage or not err_mv:
                return

            self._clear_chart_placeholder()
            layout = self.chart_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(self.chart_placeholder)
            layout.setContentsMargins(14, 14, 14, 10)
            layout.setSpacing(8)

            legend_row = QHBoxLayout()
            legend_row.addStretch()
            cal_legend = QLabel("● Calibrated Voltage (V)")
            cal_legend.setStyleSheet("color: #00d39a; font-size: 12px;")
            legend_row.addWidget(cal_legend)
            legend_row.addSpacing(16)
            ideal_legend = QLabel("● Ideal (y = x)")
            ideal_legend.setStyleSheet("color: #7e96bf; font-size: 12px;")
            legend_row.addWidget(ideal_legend)
            legend_row.addSpacing(16)
            err_legend = QLabel("● Calib Error (mV)")
            err_legend.setStyleSheet("color: #e05c5c; font-size: 12px;")
            legend_row.addWidget(err_legend)
            if cons_mv:
                legend_row.addSpacing(16)
                cons_legend = QLabel("● K,B Consistency (mV)")
                cons_legend.setStyleSheet("color: #f0a040; font-size: 12px;")
                legend_row.addWidget(cons_legend)
            legend_row.addSpacing(16)
            limit_legend = QLabel(f"┄ Limit ±{limit:.1f} mV")
            limit_legend.setStyleSheet("color: #7e96bf; font-size: 12px;")
            legend_row.addWidget(limit_legend)
            legend_row.addStretch()
            layout.addLayout(legend_row)

            def _style_axes(plot):
                for axis_name in ("left", "bottom"):
                    axis = plot.getAxis(axis_name)
                    axis.setTextPen(pg.mkPen("#a0b4d8"))
                    axis.setPen(pg.mkPen("#3a4f7a"))

            x = np.array(voltage, dtype=float)

            # 主图：理想曲线(y=x) + 校准电压传输曲线
            pw = pg.PlotWidget()
            pw.setBackground("#0a1735")
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.setLabel("left", "Calibrated Voltage (V)", color="#a0b4d8")
            pw.setLabel("bottom", x_title, color="#a0b4d8")
            self._attach_curve_context_menu(pw)
            _style_axes(pw)
            pw.plot(x, x, pen=pg.mkPen(color="#7e96bf", width=1,
                    style=pg.QtCore.Qt.DashLine))
            if cal_volt:
                n = min(len(x), len(cal_volt))
                pw.plot(x[:n], np.array(cal_volt, dtype=float)[:n],
                        pen=pg.mkPen(color="#00d39a", width=2),
                        symbol="o", symbolSize=5, symbolBrush="#00d39a", symbolPen=None)

            # 误差子图：Calib Error + ±Limit 判定线（UART 叠加一致性曲线），X 轴联动
            pw_err = pg.PlotWidget()
            pw_err.setBackground("#0a1735")
            pw_err.showGrid(x=True, y=True, alpha=0.15)
            pw_err.setLabel("left", "Error (mV)", color="#a0b4d8")
            pw_err.setLabel("bottom", x_title, color="#a0b4d8")
            pw_err.plotItem.setXLink(pw.plotItem)
            self._attach_curve_context_menu(pw_err)
            _style_axes(pw_err)
            pw_err.addLine(y=0, pen=pg.mkPen("#7e96bf", width=1,
                           style=pg.QtCore.Qt.DashLine))
            if limit > 0:
                pw_err.addLine(y=limit, pen=pg.mkPen("#e05c5c", width=1,
                               style=pg.QtCore.Qt.DashLine))
                pw_err.addLine(y=-limit, pen=pg.mkPen("#e05c5c", width=1,
                               style=pg.QtCore.Qt.DashLine))
            pw_err.plot(x, np.array(err_mv, dtype=float),
                        pen=pg.mkPen(color="#e05c5c", width=2),
                        symbol="o", symbolSize=5, symbolBrush="#e05c5c", symbolPen=None)
            if cons_mv:
                n = min(len(x), len(cons_mv))
                pw_err.plot(x[:n], np.array(cons_mv, dtype=float)[:n],
                            pen=pg.mkPen(color="#f0a040", width=2),
                            symbol="t", symbolSize=5, symbolBrush="#f0a040", symbolPen=None)

            layout.addWidget(pw, 3)
            layout.addWidget(pw_err, 1)

            x_label = QLabel(x_title)
            x_label.setAlignment(Qt.AlignCenter)
            x_label.setObjectName("muted_label")
            layout.addWidget(x_label)

            try:
                import io
                from pyqtgraph.exporters import ImageExporter
                from PySide6.QtCore import QBuffer, QIODevice
                from PySide6.QtGui import QImage, QPainter

                def _snapshot(item, width=1200):
                    # 仅指定宽度（同时指定 height 会按 cover 缩放导致宽度不精确）
                    exporter = ImageExporter(item)
                    exporter.parameters()['width'] = width
                    snap = exporter.export(toBytes=True)
                    if not isinstance(snap, QImage):
                        snap = QImage.fromData(bytes(snap))
                    return snap

                # 主图 + 误差子图纵向合成为一张快照（背景与图表底色一致）
                img_main = _snapshot(pw.plotItem)
                img_err = _snapshot(pw_err.plotItem)
                combined = QImage(img_main.width(),
                                  img_main.height() + img_err.height(),
                                  QImage.Format_ARGB32)
                combined.fill(QColor(10, 23, 53))
                painter = QPainter(combined)
                painter.drawImage(0, 0, img_main)
                painter.drawImage(0, img_main.height(), img_err)
                painter.end()

                qbuf = QBuffer()
                qbuf.open(QIODevice.WriteOnly)
                combined.save(qbuf, "PNG")
                self._chart_image_bytes = io.BytesIO(bytes(qbuf.data()))
                qbuf.close()
            except Exception as ex:
                self._append_log(f"[WARN] Chart snapshot failed: {ex}")
                self._chart_image_bytes = None

        except Exception as e:
            self._append_log(f"[ERROR] Error plotting FT calibration curve: {e}")
            logger.error("Error plotting FT calibration curve: %s", e, exc_info=True)

    def _plot_cnt_distribution(self, result, algorithm=None):
        """1000CNT 原始数据分布图：逐样本画相对 AVG 的偏差波动（code）。

        algorithm 为该次测试的算法配置快照（载入记录时传 record['algorithm']），
        供逐样本悬浮预览标注 PROC 段算法名。
        """
        try:
            import pyqtgraph as pg
            import numpy as np

            raw = result.get("raw") or []
            if not raw:
                return
            avg = float(result.get("avg", 0.0))
            std = float(result.get("std", 0.0))

            self._clear_chart_placeholder()
            layout = self.chart_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(self.chart_placeholder)
            layout.setContentsMargins(14, 14, 14, 10)
            layout.setSpacing(8)

            # 当前记录专属色（有载入记录时用其色，否则默认绿）
            curve_color = "#00d39a"
            record_name = ""
            if self._loaded_record is not None:
                curve_color = self._record_color(self._loaded_record['id'])
                record_name = f" #{self._loaded_record['id']} {self._record_display_name(self._loaded_record)} · "

            legend_row = QHBoxLayout()
            legend_row.addStretch()
            dev_legend = QLabel(f"● {record_name}Deviation from AVG (code)")
            dev_legend.setStyleSheet(f"color: {curve_color}; font-size: 12px;")
            avg_legend = QLabel("─ AVG Level")
            avg_legend.setStyleSheet("color: #7e96bf; font-size: 12px;")
            std_legend = QLabel("- - ±1 STD")
            std_legend.setStyleSheet("color: #f0a040; font-size: 12px;")
            legend_row.addWidget(dev_legend)
            legend_row.addSpacing(16)
            legend_row.addWidget(avg_legend)
            legend_row.addSpacing(16)
            legend_row.addWidget(std_legend)
            legend_row.addStretch()
            layout.addLayout(legend_row)

            pw = pg.PlotWidget()
            pw.setBackground("#0a1735")
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.setLabel("left", "Deviation from AVG (code)", color="#a0b4d8")
            pw.setLabel("bottom", "Sample Index", color="#a0b4d8")
            for axis_name in ("left", "bottom"):
                axis = pw.getAxis(axis_name)
                axis.setTextPen(pg.mkPen("#a0b4d8"))
                axis.setPen(pg.mkPen("#3a4f7a"))

            x = np.arange(1, len(raw) + 1)
            dev = np.array(raw, dtype=float) - avg

            # AVG 零基准线 + ±1 STD 虚线
            pw.addLine(y=0, pen=pg.mkPen("#7e96bf", width=1))
            if std > 0:
                pw.addLine(y=std, pen=pg.mkPen(color="#f0a040", width=1,
                           style=pg.QtCore.Qt.DashLine))
                pw.addLine(y=-std, pen=pg.mkPen(color="#f0a040", width=1,
                           style=pg.QtCore.Qt.DashLine))

            pw.plot(x, dev, pen=pg.mkPen(color=curve_color, width=2),
                    symbol="o", symbolSize=4,
                    symbolBrush=curve_color, symbolPen=None)

            # 逐样本悬浮预览（RAW=算法前，PROC=处理后；长度不一致时降级为统计提示）
            raw_before = result.get("raw_before_algo") or []
            before_avg = (compute_detailed_stats(raw_before)['avg'] if raw_before else None)
            self._fv_hover_data = {
                'mode': 'cnt',
                'x': [int(v) for v in x],
                'y': [float(v) for v in dev],
                'raw_samples': list(raw),
                'raw_before': list(raw_before),
                'before_avg': before_avg,
                'algorithm': algorithm,
            }
            self._attach_fv_hover(pw)

            layout.addWidget(pw, 1)

            x_label = QLabel("Sample Index")
            x_label.setAlignment(Qt.AlignCenter)
            x_label.setObjectName("muted_label")
            layout.addWidget(x_label)

            try:
                import io
                from pyqtgraph.exporters import ImageExporter
                from PySide6.QtCore import QBuffer, QIODevice
                from PySide6.QtGui import QImage

                # 仅指定宽度（同时指定 height 会按 cover 缩放导致宽度不精确）
                exporter = ImageExporter(pw.plotItem)
                exporter.parameters()['width'] = 1200
                snap = exporter.export(toBytes=True)
                if not isinstance(snap, QImage):
                    snap = QImage.fromData(bytes(snap))
                qbuf = QBuffer()
                qbuf.open(QIODevice.WriteOnly)
                snap.save(qbuf, "PNG")
                raw_png = bytes(qbuf.data())
                qbuf.close()
                self._chart_image_bytes = io.BytesIO(raw_png)
            except Exception as ex:
                self._append_log(f"[WARN] Chart snapshot failed: {ex}")
                self._chart_image_bytes = None

        except Exception as e:
            self._append_log(f"[ERROR] Error plotting 1000CNT distribution: {e}")
            logger.error("Error plotting 1000CNT distribution: %s", e, exc_info=True)

    def _plot_temp_consistency_curves(self, result):
        try:
            import pyqtgraph as pg
            import numpy as np

            temp_list    = result["temp"]
            voltage_pts  = result["voltage"]
            mean_matrix  = result["mean"]
            min_matrix   = result["min"]
            max_matrix   = result["max"]

            show_band = self._is_curve_view_enabled('band')

            self._clear_chart_placeholder()
            layout = self.chart_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(self.chart_placeholder)
            layout.setContentsMargins(14, 14, 14, 10)
            layout.setSpacing(8)

            palette = [
                "#00d39a", "#f0a040", "#7e96bf", "#e05c5c",
                "#a78bfa", "#34d399", "#fb923c", "#60a5fa",
            ]

            legend_row = QHBoxLayout()
            legend_row.addStretch()
            for i, t in enumerate(temp_list):
                color = palette[i % len(palette)]
                lbl = QLabel(f"● {t:.1f}°C")
                lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
                legend_row.addWidget(lbl)
                legend_row.addSpacing(8)
            legend_row.addStretch()
            layout.addLayout(legend_row)

            pw = pg.PlotWidget()
            pw.setBackground("#0a1735")
            pw.showGrid(x=True, y=True, alpha=0.15)
            pw.setLabel("left",   "ADC Code",         color="#a0b4d8")
            pw.setLabel("bottom", "Input Voltage (V)", color="#a0b4d8")
            self._attach_curve_context_menu(pw)

            for axis_name in ("left", "bottom"):
                axis = pw.getAxis(axis_name)
                axis.setTextPen(pg.mkPen("#a0b4d8"))
                axis.setPen(pg.mkPen("#3a4f7a"))

            x = np.array(voltage_pts, dtype=float)

            for i, t in enumerate(temp_list):
                if i >= len(mean_matrix):
                    break
                color = palette[i % len(palette)]
                mean_row = np.array(mean_matrix[i], dtype=float)
                min_row  = np.array(min_matrix[i],  dtype=float)
                max_row  = np.array(max_matrix[i],  dtype=float)

                n = min(len(x), len(mean_row))

                if show_band:
                    fill = pg.FillBetweenItem(
                        pg.PlotDataItem(x[:n], max_row[:n]),
                        pg.PlotDataItem(x[:n], min_row[:n]),
                        brush=pg.mkBrush(
                            int(color[1:3], 16),
                            int(color[3:5], 16),
                            int(color[5:7], 16),
                            35,
                        )
                    )
                    pw.addItem(fill)

                    pw.plot(x[:n], max_row[:n],
                            pen=pg.mkPen(color=color, width=1,
                                         style=pg.QtCore.Qt.DashLine))
                    pw.plot(x[:n], min_row[:n],
                            pen=pg.mkPen(color=color, width=1,
                                         style=pg.QtCore.Qt.DashLine))
                pw.plot(x[:n], mean_row[:n],
                        pen=pg.mkPen(color=color, width=2),
                        symbol="o", symbolSize=4,
                        symbolBrush=color, symbolPen=None,
                        name=f"{t:.1f}°C")

            layout.addWidget(pw, 1)

            x_label = QLabel("Input Voltage (V)")
            x_label.setAlignment(Qt.AlignCenter)
            x_label.setObjectName("muted_label")
            layout.addWidget(x_label)

            try:
                import io
                from pyqtgraph.exporters import ImageExporter
                from PySide6.QtCore import QBuffer, QIODevice
                from PySide6.QtGui import QImage
                exporter = ImageExporter(pw.plotItem)
                exporter.parameters()['width'] = 1200
                exporter.parameters()['height'] = 700
                snap = exporter.export(toBytes=True)
                if isinstance(snap, QImage):
                    qbuf = QBuffer()
                    qbuf.open(QIODevice.WriteOnly)
                    snap.save(qbuf, "PNG")
                    raw = bytes(qbuf.data())
                    qbuf.close()
                else:
                    raw = bytes(snap)
                self._chart_image_bytes = io.BytesIO(raw)
            except Exception as ex:
                self._append_log(f"[WARN] Chart snapshot failed: {ex}")
                self._chart_image_bytes = None

        except Exception as e:
            self._append_log(f"[ERROR] Error plotting temp consistency curves: {e}")
            logger.error("Error plotting temp consistency curves: %s", e, exc_info=True)

    def _plot_multi_ch_temp_curves(self, result):
        """多通道高低温测试曲线：每通道一个 Tab。

        扫压通道：X=电压，每温度一条曲线（调色板色系，可选 Min-Max 包络带）；
        定点通道：X=温度，Mean 主线 + 可选 Min/Max 虚线。
        """
        try:
            import pyqtgraph as pg
            import numpy as np

            temp_list = result.get('temp') or []
            channels = result.get('channels') or []
            show_band = self._is_curve_view_enabled('band')

            self._clear_chart_placeholder()
            layout = self.chart_placeholder.layout()
            if layout is None:
                layout = QVBoxLayout(self.chart_placeholder)
            layout.setContentsMargins(6, 6, 6, 6)
            layout.setSpacing(6)

            tabs = QTabWidget()
            palette = self._COMPARE_PALETTE

            for ch in channels:
                name = ch.get('name') or "CH"
                pw = pg.PlotWidget()
                pw.setBackground("#0a1735")
                pw.showGrid(x=True, y=True, alpha=0.15)
                self._attach_curve_context_menu(pw)
                for axis_name in ("left", "bottom"):
                    axis = pw.getAxis(axis_name)
                    axis.setTextPen(pg.mkPen("#a0b4d8"))
                    axis.setPen(pg.mkPen("#3a4f7a"))

                if ch.get('sweep'):
                    vpts = np.array(ch.get('voltage') or [], dtype=float)
                    pw.setLabel("left", "ADC Code", color="#a0b4d8")
                    pw.setLabel("bottom", "Input Voltage (V)", color="#a0b4d8")
                    mean_matrix = ch.get('mean') or []
                    min_matrix = ch.get('min') or []
                    max_matrix = ch.get('max') or []
                    for i, t in enumerate(temp_list):
                        if i >= len(mean_matrix):
                            break
                        color = palette[i % len(palette)]
                        mean_row = np.array(mean_matrix[i], dtype=float)
                        n = min(len(vpts), len(mean_row))
                        if n == 0:
                            continue
                        if show_band and i < len(min_matrix) and i < len(max_matrix):
                            min_row = np.array(min_matrix[i], dtype=float)
                            max_row = np.array(max_matrix[i], dtype=float)
                            m = min(n, len(min_row), len(max_row))
                            if m > 0:
                                fill = pg.FillBetweenItem(
                                    pg.PlotDataItem(vpts[:m], max_row[:m]),
                                    pg.PlotDataItem(vpts[:m], min_row[:m]),
                                    brush=pg.mkBrush(
                                        int(color[1:3], 16),
                                        int(color[3:5], 16),
                                        int(color[5:7], 16),
                                        35,
                                    ),
                                )
                                pw.addItem(fill)
                        pw.plot(vpts[:n], mean_row[:n],
                                pen=pg.mkPen(color=color, width=2),
                                symbol="o", symbolSize=4,
                                symbolBrush=color, symbolPen=None,
                                name=f"{t:.1f}°C")
                else:
                    mean_list = ch.get('mean') or []
                    min_list = ch.get('min') or []
                    max_list = ch.get('max') or []
                    n = min(len(temp_list), len(mean_list))
                    x = np.array(temp_list[:n], dtype=float)
                    mean_arr = np.array(mean_list[:n], dtype=float)
                    pw.setLabel("left", "ADC Code", color="#a0b4d8")
                    pw.setLabel("bottom", "Temperature (°C)", color="#a0b4d8")
                    color = "#00d39a"
                    if n > 0:
                        if show_band and len(min_list) >= n and len(max_list) >= n:
                            min_arr = np.array(min_list[:n], dtype=float)
                            max_arr = np.array(max_list[:n], dtype=float)
                            pw.plot(x, max_arr, pen=pg.mkPen(color="#f0a040", width=1,
                                                             style=Qt.DashLine))
                            pw.plot(x, min_arr, pen=pg.mkPen(color="#f0a040", width=1,
                                                             style=Qt.DashLine))
                        pw.plot(x, mean_arr,
                                pen=pg.mkPen(color=color, width=2),
                                symbol="o", symbolSize=5,
                                symbolBrush=color, symbolPen=None,
                                name="Mean")
                tabs.addTab(pw, name)

            layout.addWidget(tabs, 1)

            # 快照（当前 Tab）供 Excel 嵌入
            try:
                import io
                from PySide6.QtCore import QBuffer, QIODevice
                pixmap = tabs.grab()
                qbuf = QBuffer()
                qbuf.open(QIODevice.WriteOnly)
                pixmap.save(qbuf, "PNG")
                raw = bytes(qbuf.data())
                qbuf.close()
                self._chart_image_bytes = io.BytesIO(raw)
            except Exception as ex:
                self._append_log(f"[WARN] Chart snapshot failed: {ex}")
                self._chart_image_bytes = None

        except Exception as e:
            self._append_log(f"[ERROR] Error plotting multi-ch temp curves: {e}")
            logger.error("Error plotting multi-ch temp curves: %s", e, exc_info=True)

    def _plot_temperature_adc_curve(self, temp_data, adc_data):
        """绘制温度-ADC曲线到UI"""
        try:
            self._clear_chart_placeholder()
            chart_placeholder_layout = self.chart_placeholder.layout()
            if chart_placeholder_layout is None:
                chart_placeholder_layout = QVBoxLayout(self.chart_placeholder)
            chart_placeholder_layout.setContentsMargins(22, 22, 22, 18)
            chart_placeholder_layout.setSpacing(12)
            
            # 添加图例
            legend_row = QHBoxLayout()
            legend_row.addStretch()
            
            temp_legend = QLabel("↔ Temperature (°C)")
            temp_legend.setStyleSheet("color: #00d39a; font-size: 12px;")
            adc_legend = QLabel("↔ ADC Value")
            adc_legend.setStyleSheet("color: #59a8ff; font-size: 12px;")
            
            legend_row.addWidget(temp_legend)
            legend_row.addWidget(adc_legend)
            legend_row.addStretch()
            chart_placeholder_layout.addLayout(legend_row)
            
            # 创建绘图区域
            plot_area = QFrame()
            plot_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            plot_area.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                    border-left: 1px solid #6f7fa5;
                    border-bottom: 1px solid #6f7fa5;
                    border-top: 1px dashed rgba(126,150,191,0.18);
                    border-right: none;
                    border-radius: 0px;
                }
            """)
            
            # 简单的曲线绘制（使用QLabel模拟，实际项目中应该使用专业绘图库）
            import numpy as np
            
            # 创建一个简单的文本显示，显示曲线数据
            curve_data = """
Temperature (°C) | ADC Value
----------------|----------
"""
            for t, adc in zip(temp_data, adc_data):
                curve_data += f"{t:>15.1f} | {adc:>10.3f}\n"
            
            # 添加统计信息
            curve_data += "\n" + "="*40 + "\n"
            curve_data += f"Min Temp: {min(temp_data):.1f}°C\n"
            curve_data += f"Max Temp: {max(temp_data):.1f}°C\n"
            curve_data += f"Min ADC:  {min(adc_data):.3f}\n"
            curve_data += f"Max ADC:  {max(adc_data):.3f}\n"
            curve_data += f"Avg ADC:  {np.mean(adc_data):.3f}\n"
            
            data_label = QLabel(curve_data)
            data_label.setStyleSheet(f"color: #d8e3ff; font-family: {FONT_MONO}; font-size: 10px;")
            data_label.setWordWrap(True)
            
            # 创建滚动区域以显示大量数据
            scroll_area = QScrollArea()
            scroll_area.setWidget(data_label)
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("background: transparent; border: none;" + SCROLL_AREA_STYLE)
            
            # 添加到布局
            chart_placeholder_layout.addWidget(scroll_area, 1)
            
            # 添加轴标签
            x_label = QLabel("Temperature (°C)")
            x_label.setAlignment(Qt.AlignCenter)
            x_label.setObjectName("muted_label")
            chart_placeholder_layout.addWidget(x_label)
            
            # 在实际项目中，应该使用matplotlib或PyQtGraph等专业绘图库
            # 这里只是一个简单的模拟实现
            
        except Exception as e:
            self._append_log(f"[ERROR] Error plotting temperature-ADC curve: {e}")
            logger.error("Error plotting temperature-ADC curve: %s", e, exc_info=True)
            
            # 如果绘图失败，显示错误信息
            error_label = QLabel(f"绘图失败: {str(e)}")
            error_label.setStyleSheet("color: #ff5a7a; font-size: 14px;")
            error_label.setAlignment(Qt.AlignCenter)

            self._clear_chart_placeholder()
            chart_placeholder_layout = self.chart_placeholder.layout()
            if chart_placeholder_layout is None:
                chart_placeholder_layout = QVBoxLayout(self.chart_placeholder)
            chart_placeholder_layout.addWidget(error_label, 1, Qt.AlignCenter)

    # ------------------------------------------------------------------
    # AIControllablePage 契约实现（AIAssist_PageScopedControlPlan.md §2 / Phase 5）
    #
    # GPADC 测试接入 AI 受控契约，薄封装既有方法：
    #   - ai_get_config 复用 get_test_config()
    #   - ai_apply_config 经 apply_config_to_controls() 单一写入口回填控件
    #   - ai_start_test/ai_stop_test 复用 _start_test/_stop_test
    # 枢纽（MainWindow.resolve_active_ai_page）经 Tab 子页下钻拿到本实例，
    # 鸭子调用契约方法，无需 core / handler 改动。
    # ------------------------------------------------------------------
