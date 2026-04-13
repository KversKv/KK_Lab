#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU DCDC Efficiency测试UI组件
暗色卡片式重构版本（PySide6）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QSpinBox, QDoubleSpinBox, QFrame, QTextEdit,
    QSizePolicy, QButtonGroup, QFileDialog, QProgressBar,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem
)
from ui.widgets.dark_combobox import DarkComboBox
from ui.styles.button import SpinningSearchButton, update_connect_button_state
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QMargins, QPointF
from PySide6.QtGui import QFont, QCursor
import pyvisa
import math
import time

from instruments.power.keysight.n6705c import N6705C
from ui.styles import SCROLLBAR_STYLE
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C

SMOOTH_WINDOW = 5   # 平滑窗口大小（越大越平滑，建议奇数：3/5/7/9）
SMOOTH_POLY_ORDER = 2   # 多项式阶数（2=二次拟合，保留曲率；1=等效加权移动平均）


def _savgol_smooth(y_vals, window=SMOOTH_WINDOW, poly_order=SMOOTH_POLY_ORDER):
    n = len(y_vals)
    if n < window or window < poly_order + 1:
        return list(y_vals)
    if window % 2 == 0:
        window += 1
    half = window // 2
    result = list(y_vals)
    for i in range(half, n - half):
        xs = list(range(-half, half + 1))
        ys = y_vals[i - half: i + half + 1]
        coeffs = _polyfit(xs, ys, poly_order)
        result[i] = coeffs[0]
    return result


def _polyfit(xs, ys, order):
    n = len(xs)
    mat = [[0.0] * (order + 1) for _ in range(order + 1)]
    rhs = [0.0] * (order + 1)
    for i in range(order + 1):
        for j in range(order + 1):
            mat[i][j] = sum(x ** (i + j) for x in xs)
        rhs[i] = sum(ys[k] * xs[k] ** i for k in range(n))
    for col in range(order + 1):
        pivot = col
        for row in range(col + 1, order + 1):
            if abs(mat[row][col]) > abs(mat[pivot][col]):
                pivot = row
        mat[col], mat[pivot] = mat[pivot], mat[col]
        rhs[col], rhs[pivot] = rhs[pivot], rhs[col]
        diag = mat[col][col]
        if abs(diag) < 1e-15:
            continue
        for j in range(col, order + 1):
            mat[col][j] /= diag
        rhs[col] /= diag
        for row in range(order + 1):
            if row == col:
                continue
            factor = mat[row][col]
            for j in range(col, order + 1):
                mat[row][j] -= factor * mat[col][j]
            rhs[row] -= factor * rhs[col]
    return rhs



try:
    from PySide6.QtCharts import (
        QChart, QChartView, QLineSeries, QValueAxis, QLogValueAxis
    )
    from PySide6.QtGui import QPainter, QColor, QPen, QBrush
    HAS_QTCHARTS = True
except Exception:
    HAS_QTCHARTS = False


if HAS_QTCHARTS:
    class InteractiveChartView(QChartView):
        ZOOM_FACTOR = 1.25

        def __init__(self, chart, parent=None):
            super().__init__(chart, parent)
            self.setRenderHint(QPainter.Antialiasing)
            self._panning = False
            self._last_mouse_pos = QPointF()
            self._marker_enabled = False
            self._marker_dot = None
            self._marker_vline = None
            self._marker_hline = None
            self._marker_label = None
            self._series_ref = None
            self.setMouseTracking(True)

        def set_series(self, series):
            self._series_ref = series

        def wheelEvent(self, event):
            angle = event.angleDelta().y()
            if angle == 0:
                return
            factor = self.ZOOM_FACTOR if angle > 0 else 1.0 / self.ZOOM_FACTOR
            center = self.mapToScene(event.position().toPoint())
            self.chart().zoom(factor)
            event.accept()

        def mousePressEvent(self, event):
            if event.button() == Qt.MiddleButton or (
                event.button() == Qt.LeftButton and not self._marker_enabled
            ):
                self._panning = True
                self._last_mouse_pos = event.position()
                self.setCursor(QCursor(Qt.ClosedHandCursor))
                event.accept()
            else:
                super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            if self._panning:
                delta = event.position() - self._last_mouse_pos
                self._last_mouse_pos = event.position()
                self.chart().scroll(-delta.x(), delta.y())
                event.accept()
            elif self._marker_enabled and self._series_ref:
                self._update_marker(event.position())
                event.accept()
            else:
                super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):
            if self._panning:
                self._panning = False
                self.setCursor(QCursor(Qt.ArrowCursor))
                event.accept()
            else:
                super().mouseReleaseEvent(event)

        def auto_fit(self):
            ch = self.chart()
            if not self._series_ref:
                return
            pts = self._series_ref.points()
            if not pts:
                return
            x_vals = [p.x() for p in pts]
            y_vals = [p.y() for p in pts]
            min_x, max_x = min(x_vals), max(x_vals)
            min_y, max_y = min(y_vals), max(y_vals)

            for axis in ch.axes(Qt.Horizontal):
                if isinstance(axis, QLogValueAxis):
                    if min_x > 0 and max_x > 0:
                        axis.setRange(min_x * 0.8, max_x * 1.2)
                else:
                    margin_x = max((max_x - min_x) * 0.1, 0.5)
                    axis.setRange(max(0, min_x - margin_x), max_x + margin_x)

            for axis in ch.axes(Qt.Vertical):
                margin_y = max((max_y - min_y) * 0.1, 2.0)
                axis.setRange(max(0, min_y - margin_y), min(120, max_y + margin_y))

        def set_marker_enabled(self, enabled):
            self._marker_enabled = enabled
            if not enabled:
                self._remove_marker_items()
            self.setCursor(QCursor(Qt.CrossCursor) if enabled else QCursor(Qt.ArrowCursor))

        def _update_marker(self, pos):
            scene = self.chart().scene()
            if not scene or not self._series_ref:
                return
            pts = self._series_ref.points()
            if not pts:
                return

            chart_pos = self.chart().mapToValue(self.mapToScene(pos.toPoint()))
            cx, cy = chart_pos.x(), chart_pos.y()

            best = None
            best_dist = float('inf')
            plot_area = self.chart().plotArea()
            for p in pts:
                sp = self.chart().mapToPosition(p)
                dx = sp.x() - self.mapToScene(pos.toPoint()).x()
                dy = sp.y() - self.mapToScene(pos.toPoint()).y()
                d = dx * dx + dy * dy
                if d < best_dist:
                    best_dist = d
                    best = p
            if best is None:
                return

            snap_scene = self.chart().mapToPosition(best)

            if not plot_area.contains(snap_scene):
                self._remove_marker_items()
                return

            self._remove_marker_items()

            dot_r = 5
            self._marker_dot = QGraphicsEllipseItem(
                snap_scene.x() - dot_r, snap_scene.y() - dot_r, dot_r * 2, dot_r * 2
            )
            self._marker_dot.setBrush(QBrush(QColor("#ff6b6b")))
            self._marker_dot.setPen(QPen(QColor("#ffffff"), 1.5))
            scene.addItem(self._marker_dot)

            pen_v = QPen(QColor("#ffffff60"), 1, Qt.DashLine)
            self._marker_vline = QGraphicsLineItem(
                snap_scene.x(), plot_area.top(), snap_scene.x(), plot_area.bottom()
            )
            self._marker_vline.setPen(pen_v)
            scene.addItem(self._marker_vline)

            self._marker_hline = QGraphicsLineItem(
                plot_area.left(), snap_scene.y(), plot_area.right(), snap_scene.y()
            )
            self._marker_hline.setPen(pen_v)
            scene.addItem(self._marker_hline)

            label_text = f"  {best.x():.2f} mA, {best.y():.2f}%"
            self._marker_label = QGraphicsSimpleTextItem(label_text)
            self._marker_label.setBrush(QBrush(QColor("#ffffff")))
            font = QFont("Consolas", 9)
            font.setBold(True)
            self._marker_label.setFont(font)

            lx = snap_scene.x() + 8
            ly = snap_scene.y() - 20
            label_w = self._marker_label.boundingRect().width()
            if lx + label_w > plot_area.right():
                lx = snap_scene.x() - label_w - 8
            if ly < plot_area.top():
                ly = snap_scene.y() + 8
            self._marker_label.setPos(lx, ly)
            scene.addItem(self._marker_label)

        def _remove_marker_items(self):
            scene = self.chart().scene() if self.chart() else None
            for item in (self._marker_dot, self._marker_vline,
                         self._marker_hline, self._marker_label):
                if item and scene:
                    scene.removeItem(item)
            self._marker_dot = None
            self._marker_vline = None
            self._marker_hline = None
            self._marker_label = None


class CardFrame(QFrame):
    """卡片容器"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(12)

        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.main_layout.addWidget(self.title_label)
        else:
            self.title_label = None


class SegmentedButton(QPushButton):
    """分段按钮"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("segmentedButton")


class DCDCEfficiencyTestThread(QThread):
    log_message = Signal(str)
    progress = Signal(int)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    result_update = Signal(dict)
    baseline_row = Signal(dict)
    data_row = Signal(dict)
    test_finished = Signal()

    def __init__(self, n6705c, config, debug_flag=False):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._debug = debug_flag
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        try:
            cfg = self._cfg
            start_a = abs(cfg["start_current_a"])
            end_a = abs(cfg["end_current_a"])
            sweep_mode = cfg["sweep_mode"]

            vin_ch = int(cfg["vin_channel"].replace("CH ", ""))
            vout_ch = int(cfg["vout_channel"].replace("CH ", ""))
            iload_ch = int(cfg["cc_load_channel"].replace("CH ", ""))

            if sweep_mode == "Log":
                points_per_dec = cfg["points_per_dec"]
                log_start = math.log10(start_a)
                log_end = math.log10(end_a)
                dec_start = math.floor(log_start)
                dec_end = math.ceil(log_end)
                current_points = []
                for d in range(dec_start, dec_end):
                    for k in range(points_per_dec):
                        val = 10 ** (d + k / points_per_dec)
                        if start_a <= val <= end_a:
                            current_points.append(val)
                val_end = 10 ** dec_end
                if start_a <= val_end <= end_a and (not current_points or abs(current_points[-1] - val_end) > 1e-12):
                    current_points.append(val_end)
                if not current_points:
                    current_points = [start_a, end_a]
            else:
                step_a = abs(cfg["step_current_a"])
                total_points = max(2, int(round(abs(end_a - start_a) / step_a)) + 1)
                current_points = [start_a + i * step_a for i in range(total_points) if start_a + i * step_a <= end_a + step_a * 0.001]

            current_points_neg = [-abs(c) for c in current_points]

            self.log_message.emit(f"[TEST] Mode: {sweep_mode}, Points: {len(current_points)}")
            self.log_message.emit(f"[TEST] VIN ch={vin_ch}, VOUT ch={vout_ch}, ILOAD ch={iload_ch}")

            n = self._n6705c
            if self._debug and isinstance(n, MockN6705C):
                n._vin_ch = vin_ch
                n._iload_ch = iload_ch

            sleep_settle = 0.0 if self._debug else 2
            sleep_measure = 0.0 if self._debug else 0.003

            n.set_mode(vin_ch, "PS2Q")
            n.set_mode(vout_ch, "VMETer")
            n.set_mode(iload_ch, "CCLoad")
            self.log_message.emit(f"[TEST] CH{vin_ch}=PS2Q, CH{vout_ch}=VMETer, CH{iload_ch}=CCLoad")

            n.set_current_limit(vin_ch, 0.5)

            for ch in (vin_ch, vout_ch, iload_ch):
                n.set_channel_range(ch)

            n.set_current(iload_ch, 0)
            n.channel_off(iload_ch)
            QThread.msleep(int(sleep_settle * 1000))

            i_base = float(n.measure_current(iload_ch).strip())
            vin_base = float(n.measure_voltage(vin_ch))
            vout_base = float(n.measure_voltage(vout_ch))
            iin_base = float(n.measure_current(vin_ch).strip())
            self.log_message.emit(
                f"[TEST] Baseline Vin={vin_base:.3f}V  Vout={vout_base:.3f}V  "
                f"Iin={iin_base:.6f}A  Iload_base={i_base:.6f}A"
            )
            self.baseline_row.emit({
                "cc_load": 0.0,
                "efficiency": 0.0,
                "vin": vin_base,
                "iin": iin_base,
                "vout": vout_base,
                "iout": 0.0,
            })

            n.set_current(iload_ch, current_points_neg[0])
            n.channel_on(iload_ch)

            QThread.msleep(int(sleep_settle * 1000))

            self.chart_clear.emit()
            self.progress.emit(0)

            output = []
            max_eff = 0.0
            max_eff_iout = 0.0
            sum_eff = 0.0
            sum_vin = 0.0
            sum_vout = 0.0
            total_count = len(current_points)

            hdr = (f"{'#':>4s}  {'Iset(mA)':>10s}  {'Vin(V)':>8s}  "
                   f"{'Vout(V)':>8s}  {'Iin(A)':>10s}  {'Iout(A)':>10s}  "
                   f"{'Iload(A)':>10s}  {'Eff(%)':>7s}")
            self.log_message.emit(hdr)
            self.log_message.emit("-" * len(hdr))

            t_start = time.time()

            for idx, i_set in enumerate(current_points):
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user.")
                    break

                n.set_current(iload_ch, current_points_neg[idx])
                QThread.msleep(int(sleep_measure * 1000))

                vbat = float(n.measure_voltage(vin_ch))
                vout = float(n.measure_voltage(vout_ch))
                i_in = float(n.measure_current(vin_ch).strip())
                i_out = float(n.measure_current(iload_ch).strip())

                i_load_actual = max(i_base - i_out, 1e-9)
                denom = vbat * max(i_in - iin_base, 1e-9)
                eff = (vout * i_load_actual) / denom
                eff = max(min(eff, 1.2), 0.0)
                eff_pct = eff * 100

                self.log_message.emit(
                    f"{idx+1:4d}  {current_points_neg[idx]*1000:10.3f}  {vbat:8.4f}  "
                    f"{vout:8.4f}  {i_in:10.6f}  {i_out:10.6f}  "
                    f"{i_load_actual:10.6f}  {eff_pct:7.2f}"
                )

                abs_iout = abs(i_out)
                output.append((abs_iout, eff_pct))
                sum_eff += eff_pct
                sum_vin += vbat
                sum_vout += vout
                if eff_pct > max_eff:
                    max_eff = eff_pct
                    max_eff_iout = abs_iout

                self.chart_point.emit(abs_iout, eff_pct)

                self.data_row.emit({
                    "cc_load": current_points_neg[idx],
                    "efficiency": eff_pct,
                    "vin": vbat,
                    "iin": i_in,
                    "vout": vout,
                    "iout": abs_iout,
                })

                n_pts = len(output)
                result = {
                    "vin": sum_vin / n_pts,
                    "vout": sum_vout / n_pts,
                    "efficiency": sum_eff / n_pts,
                    "max_efficiency": max_eff,
                    "max_eff_load": max_eff_iout,
                }
                self.result_update.emit(result)

                self.progress.emit(int((idx + 1) * 100 / total_count))

            elapsed = time.time() - t_start
            minutes, seconds = divmod(elapsed, 60)
            completed = len(output)
            if completed > 0:
                avg = elapsed / completed
                self.log_message.emit(
                    f"[TIME] Total: {int(minutes)}m {seconds:.1f}s | "
                    f"Points: {completed} | Avg: {avg:.2f}s/point"
                )
            else:
                self.log_message.emit(f"[TIME] Total: {int(minutes)}m {seconds:.1f}s")

            n.set_current(iload_ch, -0.001)
            n.channel_off(iload_ch)

        except Exception as e:
            self.log_message.emit(f"[ERROR] Test failed: {e}")
        finally:
            self.test_finished.emit()


class PMUDCDCEfficiencyUI(QWidget):
    """PMU DCDC Efficiency测试UI组件"""

    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []

        self.is_test_running = False
        self.test_thread = None
        self._export_data = []

        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._search_devices)
        self.search_timer.setSingleShot(True)

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()
        self._sync_from_top()

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        self.setStyleSheet("""
            QWidget {
                background-color: #020817;
                color: #dbe7ff;
            }

            QLabel {
                background-color: transparent;
                color: #dbe7ff;
                border: none;
            }

            QLabel#pageTitle {
                font-size: 18px;
                font-weight: 700;
                color: #f8fbff;
                background-color: transparent;
            }

            QLabel#pageSubtitle {
                font-size: 12px;
                color: #7da2d6;
                background-color: transparent;
            }

            QFrame#panelFrame {
                background-color: #08132d;
                border: 1px solid #16274d;
                border-radius: 18px;
            }

            QFrame#cardFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 14px;
            }

            QLabel#cardTitle {
                font-size: 11px;
                font-weight: 700;
                color: #f4f7ff;
                letter-spacing: 0.5px;
                background-color: transparent;
            }

            QLabel#sectionTitle {
                font-size: 12px;
                font-weight: 700;
                color: #f4f7ff;
                background-color: transparent;
            }

            QLabel#fieldLabel {
                color: #8eb0e3;
                font-size: 11px;
                background-color: transparent;
            }

            QLabel#statusOk {
                color: #15d1a3;
                font-weight: 600;
                background-color: transparent;
            }

            QLabel#statusWarn {
                color: #ffb84d;
                font-weight: 600;
                background-color: transparent;
            }

            QLabel#statusErr {
                color: #ff5e7a;
                font-weight: 600;
                background-color: transparent;
            }

            QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #4f46e5;
            }

            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus {
                border: 1px solid #4cc9f0;
            }

            QComboBox {
                padding-right: 24px;
            }

            QComboBox::drop-down {
                border: none;
                width: 22px;
                background: transparent;
            }

            QComboBox QAbstractItemView {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                selection-background-color: #334a7d;
            }

            QComboBox QAbstractItemView::item {
                background-color: #0a1733;
                color: #eaf2ff;
                padding: 4px 8px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #1a3260;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #334a7d;
            }

            QComboBox QFrame {
                background-color: #0a1733;
                border: 1px solid #27406f;
            }

            QPushButton {
                min-height: 34px;
                border-radius: 9px;
                padding: 6px 14px;
                border: 1px solid #2a4272;
                background-color: #102042;
                color: #dfeaff;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #162a56;
                border: 1px solid #3c5fa1;
            }

            QPushButton:pressed {
                background-color: #0d1a37;
            }

            QPushButton:disabled {
                background-color: #0b1430;
                color: #5c7096;
                border: 1px solid #1a2850;
            }

            QPushButton#smallActionBtn {
                min-height: 34px;
                padding: 6px 10px;
                border-radius: 10px;
                background-color: #13254b;
                color: #dce7ff;
            }

            QPushButton#primaryStartBtn {
                min-height: 36px;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 800;
                color: white;
                border: 1px solid #645bff;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5b5cf6,
                    stop:1 #6a38ff
                );
            }

            QPushButton#primaryStartBtn:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b6cff,
                    stop:1 #7d4cff
                );
            }

            QPushButton#stopBtn {
                background-color: #4a1020;
                border: 1px solid #d9485f;
                color: #ffd5db;
            }

            QPushButton#stopBtn:hover {
                background-color: #5a1326;
            }

            QPushButton#exportBtn {
                min-height: 28px;
                padding: 4px 12px;
                border-radius: 8px;
                background-color: #16284f;
                color: #dfe8ff;
            }

            QPushButton#chartToolBtn {
                min-height: 26px;
                min-width: 26px;
                padding: 3px 8px;
                border-radius: 7px;
                background-color: #0e1d3d;
                border: 1px solid #28406b;
                color: #9fb6df;
                font-size: 11px;
            }

            QPushButton#chartToolBtn:hover {
                background-color: #162a56;
                border: 1px solid #3c5fa1;
                color: #dfeaff;
            }

            QPushButton#chartToolBtn:checked {
                background-color: #4f46e5;
                border: 1px solid #7872ff;
                color: white;
            }

            QFrame#segmentedContainer {
                background-color: #0e1d3d;
                border: 1px solid #28406b;
                border-radius: 10px;
                padding: 2px;
            }

            QPushButton#segmentedButton {
                min-height: 24px;
                padding: 2px 14px;
                border-radius: 8px;
                background-color: transparent;
                border: none;
                color: #9fb6df;
                font-weight: 600;
                font-size: 11px;
            }

            QPushButton#segmentedButton:hover {
                color: #dfeaff;
            }

            QPushButton#segmentedButton:checked {
                background-color: #4f46e5;
                border: none;
                color: white;
            }

            QFrame#chartContainer, QFrame#logContainer {
                background-color: #09142e;
                border: 1px solid #1a2d57;
                border-radius: 16px;
            }

            QTextEdit#logEdit {
                background-color: #061022;
                border: 1px solid #1f315d;
                border-radius: 8px;
                color: #7cecc8;
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
            }

            QProgressBar {
                background-color: #152749;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: #b7c8ea;
                min-height: 8px;
                max-height: 8px;
            }

            QProgressBar::chunk {
                background-color: #5b5cf6;
                border-radius: 4px;
            }

            QLabel#metricLabel {
                color: #9db6db;
                font-size: 12px;
                background-color: transparent;
            }

            QLabel#metricValue {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                background-color: transparent;
            }

            QFrame#miniStatCard {
                background-color: #0a1733;
                border: 1px solid #1b315f;
                border-radius: 10px;
            }
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.page_title = QLabel("⚙ DCDC Efficiency Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Configure and execute automated DCDC efficiency validation sequences.")
        self.page_subtitle.setObjectName("pageSubtitle")

        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_subtitle)
        root_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        root_layout.addLayout(content_layout, 1)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("panelFrame")
        self.left_panel.setFixedWidth(275)

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(16)

        self.connection_card = CardFrame("⚡ N6705C CONNECTION")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.channel_card = CardFrame("⇄ CHANNEL SELECTION")
        self._build_channel_card()
        left_layout.addWidget(self.channel_card)

        self.sweep_card = CardFrame("∿ SWEEP\nPARAMETERS")
        self._build_sweep_card()
        left_layout.addWidget(self.sweep_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("▶ START SEQUENCE")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_layout.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("■ STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()

        content_layout.addWidget(self.left_panel)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartContainer")
        chart_outer_layout = QVBoxLayout(self.chart_frame)
        chart_outer_layout.setContentsMargins(16, 16, 16, 16)
        chart_outer_layout.setSpacing(10)

        chart_header_layout = QHBoxLayout()
        self.chart_title = QLabel("∿ Live Efficiency Curve")
        self.chart_title.setObjectName("sectionTitle")
        chart_header_layout.addWidget(self.chart_title)
        chart_header_layout.addStretch()

        self.chart_zoom_in_btn = QPushButton("+")
        self.chart_zoom_in_btn.setObjectName("chartToolBtn")
        self.chart_zoom_in_btn.setToolTip("Zoom In")

        self.chart_zoom_out_btn = QPushButton("−")
        self.chart_zoom_out_btn.setObjectName("chartToolBtn")
        self.chart_zoom_out_btn.setToolTip("Zoom Out")

        self.chart_auto_btn = QPushButton("Auto")
        self.chart_auto_btn.setObjectName("chartToolBtn")
        self.chart_auto_btn.setToolTip("Auto Fit")

        self.chart_marker_btn = QPushButton("Marker")
        self.chart_marker_btn.setObjectName("chartToolBtn")
        self.chart_marker_btn.setCheckable(True)
        self.chart_marker_btn.setToolTip("Toggle Marker")

        chart_header_layout.addWidget(self.chart_zoom_in_btn)
        chart_header_layout.addWidget(self.chart_zoom_out_btn)
        chart_header_layout.addWidget(self.chart_auto_btn)
        chart_header_layout.addWidget(self.chart_marker_btn)

        self.import_result_btn = QPushButton("⇧ Import CSV")
        self.import_result_btn.setObjectName("exportBtn")
        chart_header_layout.addWidget(self.import_result_btn)

        self.export_result_btn = QPushButton("⇩ Export CSV")
        self.export_result_btn.setObjectName("exportBtn")
        chart_header_layout.addWidget(self.export_result_btn)

        chart_outer_layout.addLayout(chart_header_layout)

        self.chart_widget = self._create_chart_widget()
        chart_outer_layout.addWidget(self.chart_widget, 1)

        stat_layout = QHBoxLayout()
        stat_layout.setSpacing(10)

        self.vin_card = self._create_mini_stat("Vin", "---")
        self.vout_card = self._create_mini_stat("Vout", "---")
        self.efficiency_card = self._create_mini_stat("平均效率", "---")
        self.max_efficiency_card = self._create_mini_stat("最大效率", "---")
        self.max_eff_load_card = self._create_mini_stat("最大效率负载点", "---")

        stat_layout.addWidget(self.vin_card["frame"])
        stat_layout.addWidget(self.vout_card["frame"])
        stat_layout.addWidget(self.efficiency_card["frame"])
        stat_layout.addWidget(self.max_efficiency_card["frame"])
        stat_layout.addWidget(self.max_eff_load_card["frame"])

        chart_outer_layout.addLayout(stat_layout)
        right_layout.addWidget(self.chart_frame, 4)

        self.log_frame = QFrame()
        self.log_frame.setObjectName("logContainer")
        log_layout = QVBoxLayout(self.log_frame)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        self.log_title = QLabel("⊙ Execution Logs")
        self.log_title.setObjectName("sectionTitle")
        log_header.addWidget(self.log_title)
        log_header.addStretch()

        self.progress_text_label = QLabel("0% Complete")
        self.progress_text_label.setObjectName("fieldLabel")
        log_header.addWidget(self.progress_text_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(120)
        log_header.addWidget(self.progress_bar)

        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("smallActionBtn")
        log_header.addWidget(self.clear_log_btn)

        log_layout.addLayout(log_header)

        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)

        log_layout.addWidget(self.log_edit)

        right_layout.addWidget(self.log_frame, 1)

    def _build_connection_card(self):
        layout = self.connection_card.main_layout

        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        layout.addWidget(self.system_status_label)

        self.instrument_info_label = QLabel("USB0::0x0957::0x0F07::MY53004321")
        self.instrument_info_label.setObjectName("fieldLabel")
        self.instrument_info_label.setWordWrap(True)
        layout.addWidget(self.instrument_info_label)

        self.visa_resource_combo = DarkComboBox()
        self.visa_resource_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
        layout.addWidget(self.visa_resource_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.search_btn = SpinningSearchButton()

        self.connect_btn = QPushButton()
        update_connect_button_state(self.connect_btn, connected=False)

        btn_row.addWidget(self.search_btn)
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

    def _build_channel_card(self):
        layout = self.channel_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.vin_channel_label = QLabel("VIN Channel")
        self.vin_channel_label.setObjectName("fieldLabel")
        self.vin_channel_combo = DarkComboBox()
        self.vin_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])

        self.vout_channel_label = QLabel("VOUT Channel")
        self.vout_channel_label.setObjectName("fieldLabel")
        self.vout_channel_combo = DarkComboBox()
        self.vout_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        self.vout_channel_combo.setCurrentIndex(1)

        self.cc_load_channel_label = QLabel("CC Load Channel")
        self.cc_load_channel_label.setObjectName("fieldLabel")
        self.cc_load_channel_combo = DarkComboBox()
        self.cc_load_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        self.cc_load_channel_combo.setCurrentIndex(2)

        grid.addWidget(self.vin_channel_label, 0, 0)
        grid.addWidget(self.vin_channel_combo, 0, 1)

        grid.addWidget(self.vout_channel_label, 1, 0)
        grid.addWidget(self.vout_channel_combo, 1, 1)

        grid.addWidget(self.cc_load_channel_label, 2, 0)
        grid.addWidget(self.cc_load_channel_combo, 2, 1)

        layout.addLayout(grid)

    def _build_sweep_card(self):
        layout = self.sweep_card.main_layout

        mode_row = QHBoxLayout()
        mode_row.addStretch()

        self.seg_container = QFrame()
        self.seg_container.setObjectName("segmentedContainer")
        seg_layout = QHBoxLayout(self.seg_container)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(0)

        self.linear_mode_btn = SegmentedButton("Linear")
        self.log_mode_btn = SegmentedButton("Log")
        self.linear_mode_btn.setChecked(True)

        self.sweep_mode_group = QButtonGroup(self)
        self.sweep_mode_group.setExclusive(True)
        self.sweep_mode_group.addButton(self.linear_mode_btn)
        self.sweep_mode_group.addButton(self.log_mode_btn)

        seg_layout.addWidget(self.linear_mode_btn)
        seg_layout.addWidget(self.log_mode_btn)

        mode_row.addWidget(self.seg_container)
        layout.addLayout(mode_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.lbl_start = QLabel("Start Current (A)")
        self.lbl_start.setObjectName("fieldLabel")
        self.load_current_start_spin = QDoubleSpinBox()
        self.load_current_start_spin.setRange(-100.0, 100.0)
        self.load_current_start_spin.setDecimals(3)
        self.load_current_start_spin.setSingleStep(0.001)
        self.load_current_start_spin.setValue(0.001)

        self.lbl_end = QLabel("End Current (A)")
        self.lbl_end.setObjectName("fieldLabel")
        self.load_current_end_spin = QDoubleSpinBox()
        self.load_current_end_spin.setRange(-100.0, 100.0)
        self.load_current_end_spin.setDecimals(3)
        self.load_current_end_spin.setSingleStep(0.001)
        self.load_current_end_spin.setValue(0.2)

        self.lbl_step = QLabel("Step Current (A)")
        self.lbl_step.setObjectName("fieldLabel")
        self.step_current_spin = QDoubleSpinBox()
        self.step_current_spin.setRange(-100.0, 100.0)
        self.step_current_spin.setDecimals(3)
        self.step_current_spin.setSingleStep(0.001)
        self.step_current_spin.setValue(0.001)

        self.lbl_points = QLabel("Points (per dec)")
        self.lbl_points.setObjectName("fieldLabel")
        self.points_per_dec_spin = QSpinBox()
        self.points_per_dec_spin.setRange(2, 100)
        self.points_per_dec_spin.setValue(10)

        grid.addWidget(self.lbl_start, 0, 0)
        grid.addWidget(self.load_current_start_spin, 1, 0)

        grid.addWidget(self.lbl_end, 0, 1)
        grid.addWidget(self.load_current_end_spin, 1, 1)

        grid.addWidget(self.lbl_step, 2, 0, 1, 2)
        grid.addWidget(self.step_current_spin, 3, 0, 1, 2)

        grid.addWidget(self.lbl_points, 2, 0, 1, 2)
        grid.addWidget(self.points_per_dec_spin, 3, 0, 1, 2)

        layout.addLayout(grid)

        self._on_sweep_mode_changed()

    def _on_sweep_mode_changed(self):
        is_log = self.log_mode_btn.isChecked()

        self.lbl_step.setVisible(not is_log)
        self.step_current_spin.setVisible(not is_log)

        self.lbl_points.setVisible(is_log)
        self.points_per_dec_spin.setVisible(is_log)

        if HAS_QTCHARTS and hasattr(self, 'series'):
            self._rebuild_chart_x_axis(is_log)

    def _create_chart_widget(self):
        if HAS_QTCHARTS:
            self._raw_points = []

            self.series = QLineSeries()
            pen_raw = QPen(QColor("#00d6a240"))
            pen_raw.setWidth(1)
            self.series.setPen(pen_raw)

            self.smooth_series = QLineSeries()
            pen_smooth = QPen(QColor("#00d6a2"))
            pen_smooth.setWidth(2)
            self.smooth_series.setPen(pen_smooth)

            self.chart = QChart()
            self.chart.setBackgroundVisible(False)
            self.chart.setPlotAreaBackgroundVisible(True)
            self.chart.setPlotAreaBackgroundBrush(QColor("#09142e"))
            self.chart.legend().hide()
            self.chart.addSeries(self.series)
            self.chart.addSeries(self.smooth_series)
            self.chart.setMargins(QMargins(0, 0, 0, 0))

            self.axis_y = QValueAxis()
            self.axis_y.setRange(0, 100)
            self.axis_y.setTickCount(11)
            self.axis_y.setTitleText("EFFICIENCY (%)")
            self.axis_y.setLabelsColor(QColor("#9fc0ef"))
            self.axis_y.setTitleBrush(QColor("#9fc0ef"))
            self.axis_y.setGridLineColor(QColor("#2a3f6a"))

            self.chart.addAxis(self.axis_y, Qt.AlignLeft)
            self.series.attachAxis(self.axis_y)
            self.smooth_series.attachAxis(self.axis_y)

            self.axis_x = None
            is_log = self.log_mode_btn.isChecked()
            self._rebuild_chart_x_axis(is_log)

            self.chart_view = InteractiveChartView(self.chart)
            self.chart_view.set_series(self.smooth_series)
            self.chart_view.setStyleSheet("background: transparent; border: none;")
            return self.chart_view

        placeholder = QFrame()
        placeholder.setStyleSheet("""
            QFrame {
                background-color: #09142e;
                border: 1px solid #1b315f;
                border-radius: 10px;
            }
        """)
        v = QVBoxLayout(placeholder)
        label = QLabel("Live Efficiency Chart")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#7da2d6; font-size:14px; font-weight:600; background: transparent;")
        v.addWidget(label)
        return placeholder

    def _rebuild_chart_x_axis(self, is_log):
        if not HAS_QTCHARTS or not hasattr(self, 'chart'):
            return

        if self.axis_x is not None:
            self.series.detachAxis(self.axis_x)
            if hasattr(self, 'smooth_series'):
                self.smooth_series.detachAxis(self.axis_x)
            self.chart.removeAxis(self.axis_x)

        if is_log:
            self.axis_x = QLogValueAxis()
            self.axis_x.setBase(10)
            self.axis_x.setLabelFormat("%g")
            self.axis_x.setRange(10, 2000)
            self.axis_x.setMinorTickCount(8)
            self.axis_x.setMinorGridLineVisible(True)
        else:
            self.axis_x = QValueAxis()
            self.axis_x.setRange(0, 2000)
            self.axis_x.setTickCount(11)

        self.axis_x.setTitleText("I_LOAD (mA)")
        self.axis_x.setGridLineVisible(True)
        self.axis_x.setLabelsColor(QColor("#9fc0ef"))
        self.axis_x.setTitleBrush(QColor("#9fc0ef"))
        self.axis_x.setGridLineColor(QColor("#2a3f6a"))
        if is_log:
            self.axis_x.setMinorGridLineColor(QColor("#1c2f56"))

        self.chart.addAxis(self.axis_x, Qt.AlignBottom)
        self.series.attachAxis(self.axis_x)
        if hasattr(self, 'smooth_series'):
            self.smooth_series.attachAxis(self.axis_x)

    def _create_mini_stat(self, title, value):
        frame = QFrame()
        frame.setObjectName("miniStatCard")
        frame.setMinimumHeight(68)
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("metricLabel")

        value_label = QLabel(value)
        value_label.setObjectName("metricValue")

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return {
            "frame": frame,
            "title": title_label,
            "value": value_label
        }

    def _init_ui_elements(self):
        self._update_connect_button_state(False)
        self.append_log("[SYSTEM] Ready. Waiting for instrument connection.")
        self.append_log("[TEST] UI initialized successfully.")
        self.set_progress(0)

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)
        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.export_result_btn.clicked.connect(self._on_export_csv)
        self.import_result_btn.clicked.connect(self._on_import_csv)
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        self.linear_mode_btn.clicked.connect(self._on_sweep_mode_changed)
        self.log_mode_btn.clicked.connect(self._on_sweep_mode_changed)
        self.chart_zoom_in_btn.clicked.connect(self._on_chart_zoom_in)
        self.chart_zoom_out_btn.clicked.connect(self._on_chart_zoom_out)
        self.chart_auto_btn.clicked.connect(self._on_chart_auto_fit)
        self.chart_marker_btn.toggled.connect(self._on_chart_marker_toggled)

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        update_connect_button_state(self.connect_btn, connected)

    def _sync_from_top(self):
        if not self._n6705c_top:
            return
        if self._n6705c_top.is_connected_a and self._n6705c_top.n6705c_a:
            self.n6705c = self._n6705c_top.n6705c_a
            self._update_connect_button_state(True)
            self.search_btn.setEnabled(False)
            if self._n6705c_top.visa_resource_a:
                self.visa_resource_combo.clear()
                self.visa_resource_combo.addItem(self._n6705c_top.visa_resource_a)
        elif not self.is_connected:
            self._update_connect_button_state(False)

    def append_log(self, message):
        self.log_edit.append(message)

    def _on_clear_log(self):
        self.log_edit.clear()

    def set_progress(self, value: int):
        value = max(0, min(100, int(value)))
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}% Complete")

    def _on_start_test(self):
        if not self.is_connected or self.n6705c is None:
            self.append_log("[ERROR] Not connected to instrument.")
            return
        if self.is_test_running:
            return
        self._export_data = []
        self.set_test_running(True)
        self.set_progress(0)
        cfg = self.get_test_config()
        self.test_thread = DCDCEfficiencyTestThread(self.n6705c, cfg, DEBUG_MOCK)
        self.test_thread.log_message.connect(self.append_log)
        self.test_thread.progress.connect(self.set_progress)
        self.test_thread.chart_point.connect(self._update_chart_point)
        self.test_thread.chart_clear.connect(self._on_chart_clear)
        self.test_thread.result_update.connect(self.update_test_result)
        self.test_thread.baseline_row.connect(self._on_baseline_row)
        self.test_thread.data_row.connect(self._on_data_row)
        self.test_thread.test_finished.connect(self._on_test_finished)
        self.test_thread.start()

    def _on_stop_test(self):
        if self.test_thread is not None:
            self.test_thread.request_stop()
        self.append_log("[TEST] Stop requested...")

    def _on_chart_clear(self):
        if HAS_QTCHARTS and hasattr(self, 'series'):
            self.series.clear()
        if HAS_QTCHARTS and hasattr(self, 'smooth_series'):
            self.smooth_series.clear()
        if hasattr(self, '_raw_points'):
            self._raw_points = []

    def _on_chart_zoom_in(self):
        if HAS_QTCHARTS and hasattr(self, 'chart'):
            self.chart.zoomIn()

    def _on_chart_zoom_out(self):
        if HAS_QTCHARTS and hasattr(self, 'chart'):
            self.chart.zoomOut()

    def _on_chart_auto_fit(self):
        if HAS_QTCHARTS and hasattr(self, 'chart_view'):
            self.chart_view.auto_fit()

    def _on_chart_marker_toggled(self, checked):
        if HAS_QTCHARTS and hasattr(self, 'chart_view'):
            self.chart_view.set_marker_enabled(checked)

    def _on_test_finished(self):
        self.set_test_running(False)

    def _on_baseline_row(self, row):
        self._export_data.insert(0, row)

    def _on_data_row(self, row):
        self._export_data.append(row)

    def _on_export_csv(self):
        if not self._export_data:
            self.append_log("[EXPORT] No data to export.")
            return

        from datetime import datetime
        default_name = f"dcdc_efficiency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", default_name, "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                f.write("CC Load(A),Efficiency(%),Vin(V),Iin(A),Vout(V),Iout(A)\n")
                for row in self._export_data:
                    f.write(
                        f"{row['cc_load']:.6f},"
                        f"{row['efficiency']:.2f},"
                        f"{row['vin']:.6f},"
                        f"{row['iin']:.6f},"
                        f"{row['vout']:.6f},"
                        f"{row['iout']:.6f}\n"
                    )
            self.append_log(f"[EXPORT] Data exported to {file_path}")
        except Exception as e:
            self.append_log(f"[ERROR] Export failed: {e}")

    def _on_import_csv(self):
        if self.is_test_running:
            self.append_log("[IMPORT] Cannot import while test is running.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            rows = []
            with open(file_path, "r", encoding="utf-8") as f:
                header = f.readline().strip()
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) < 6:
                        continue
                    rows.append({
                        "cc_load": float(parts[0]),
                        "efficiency": float(parts[1]),
                        "vin": float(parts[2]),
                        "iin": float(parts[3]),
                        "vout": float(parts[4]),
                        "iout": float(parts[5]),
                    })

            if not rows:
                self.append_log("[IMPORT] No valid data found in CSV.")
                return

            self._export_data = rows
            self._on_chart_clear()

            data_rows = [r for r in rows if r["efficiency"] > 0]
            if not data_rows:
                self.append_log("[IMPORT] No measurement data found.")
                return

            sum_vin = 0.0
            sum_vout = 0.0
            sum_eff = 0.0
            max_eff = 0.0
            max_eff_iout = 0.0

            for r in data_rows:
                iout = r["iout"]
                eff = r["efficiency"]
                sum_vin += r["vin"]
                sum_vout += r["vout"]
                sum_eff += eff
                if eff > max_eff:
                    max_eff = eff
                    max_eff_iout = iout
                self._update_chart_point(iout, eff)

            n = len(data_rows)
            self.update_test_result({
                "vin": sum_vin / n,
                "vout": sum_vout / n,
                "efficiency": sum_eff / n,
                "max_efficiency": max_eff,
                "max_eff_load": max_eff_iout,
            })
            self.set_progress(100)

            self.append_log(f"[IMPORT] Loaded {len(rows)} rows from {file_path}")
            self.append_log(
                f"[IMPORT] Avg Eff={sum_eff/n:.2f}%  Max Eff={max_eff:.2f}%  "
                f"@ {max_eff_iout*1000:.3f} mA"
            )
        except Exception as e:
            self.append_log(f"[ERROR] Import failed: {e}")

    def _update_chart_point(self, i_out_a, eff_pct):
        if HAS_QTCHARTS and hasattr(self, 'series'):
            i_out_ma = i_out_a * 1000
            self._raw_points.append((i_out_ma, eff_pct))
            self.series.append(i_out_ma, eff_pct)

            x_list = [p[0] for p in self._raw_points]
            y_list = [p[1] for p in self._raw_points]
            y_smooth = _savgol_smooth(y_list)

            self.smooth_series.clear()
            for x, ys in zip(x_list, y_smooth):
                self.smooth_series.append(x, ys)

            if self.axis_x is not None:
                min_x = min(x_list)
                max_x = max(x_list)
                is_log = isinstance(self.axis_x, QLogValueAxis)
                if is_log:
                    if min_x > 0 and max_x > 0:
                        if min_x == max_x:
                            self.axis_x.setRange(min_x * 0.5, max_x * 2.0)
                        else:
                            self.axis_x.setRange(min_x * 0.8, max_x * 1.2)
                else:
                    if min_x == max_x:
                        margin = max(min_x * 0.5, 1.0)
                    else:
                        margin = max((max_x - min_x) * 0.1, 0.5)
                    self.axis_x.setRange(max(0, min_x - margin), max_x + margin)

            if self.axis_y is not None:
                min_y = max(0, min(y_smooth) - 5)
                max_y = min(120, max(y_smooth) + 5)
                if min_y == max_y:
                    min_y = max(0, min_y - 10)
                    max_y = min(120, max_y + 10)
                self.axis_y.setRange(min_y, max_y)

    def get_test_config(self):
        return {
            "vin_channel": self.vin_channel_combo.currentText(),
            "vout_channel": self.vout_channel_combo.currentText(),
            "cc_load_channel": self.cc_load_channel_combo.currentText(),
            "sweep_mode": "Log" if self.log_mode_btn.isChecked() else "Linear",
            "start_current_a": self.load_current_start_spin.value(),
            "end_current_a": self.load_current_end_spin.value(),
            "step_current_a": self.step_current_spin.value(),
            "points_per_dec": self.points_per_dec_spin.value()
        }

    def set_test_running(self, running):
        self.is_test_running = running

        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(running)
        if running:
            self.start_test_btn.setText("■ STOP")
            self.start_test_btn.setObjectName("stopBtn")
        else:
            self.start_test_btn.setText("▶ START SEQUENCE")
            self.start_test_btn.setObjectName("primaryStartBtn")
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.start_test_btn.update()

        widgets = [
            self.vin_channel_combo,
            self.vout_channel_combo,
            self.cc_load_channel_combo,
            self.linear_mode_btn,
            self.log_mode_btn,
            self.load_current_start_spin,
            self.load_current_end_spin,
            self.step_current_spin,
            self.points_per_dec_spin,
            self.visa_resource_combo,
            self.search_btn,
            self.connect_btn
        ]

        for widget in widgets:
            widget.setEnabled(not running)

        if running:
            self.set_system_status("● Running")
            self.append_log("[TEST] Starting DCDC Efficiency Test Sequence...")
        else:
            self.set_system_status("● Ready" if not self.is_connected else "● Connected")
            self.append_log("[TEST] Test stopped or completed.")

    def update_test_result(self, result):
        if "vin" in result:
            self.vin_card["value"].setText(f"{result['vin']:.4f} V")
        if "vout" in result:
            self.vout_card["value"].setText(f"{result['vout']:.4f} V")
        if "efficiency" in result:
            self.efficiency_card["value"].setText(f"{result['efficiency']:.2f}%")
        if "max_efficiency" in result:
            self.max_efficiency_card["value"].setText(f"{result['max_efficiency']:.2f}%")
        if "max_eff_load" in result:
            self.max_eff_load_card["value"].setText(f"{result['max_eff_load']*1000:.3f} mA")

    def clear_results(self):
        self.vin_card["value"].setText("---")
        self.vout_card["value"].setText("---")
        self.efficiency_card["value"].setText("---")
        self.max_efficiency_card["value"].setText("---")
        self.max_eff_load_card["value"].setText("---")
        self.append_log("[SYSTEM] Results cleared.")

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)

        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Running" in status or "Searching" in status or "Connecting" in status or "Disconnecting" in status:
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")

        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def update_instrument_info(self, instrument_info):
        self.instrument_info_label.setText(instrument_info)

    def _on_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        if DEBUG_MOCK:
            self.visa_resource_combo.clear()
            self.visa_resource_combo.addItem("DEBUG::MOCK::N6705C")
            self.set_system_status("● Mock device ready")
            self.append_log("[DEBUG] Mock device loaded, skip real VISA scan.")
            return
        self.set_system_status("● Searching")
        self.append_log("[SYSTEM] Scanning VISA resources...")
        self.search_btn.setEnabled(False)
        self.search_timer.start(100)

    def _search_devices(self):
        try:
            if self.rm is None:
                try:
                    self.rm = pyvisa.ResourceManager()
                except Exception:
                    self.rm = pyvisa.ResourceManager('@ni')

            self.available_devices = list(self.rm.list_resources()) or []

            compatible_devices = []
            if self.available_devices:
                compatible_devices = self.available_devices.copy()

            n6705c_devices = []
            for dev in compatible_devices:
                try:
                    instr = self.rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()

                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception:
                    pass

            self.visa_resource_combo.setEnabled(True)
            self.visa_resource_combo.clear()

            if n6705c_devices:
                for dev in n6705c_devices:
                    self.visa_resource_combo.addItem(dev)

                count = len(n6705c_devices)
                self.set_system_status(f"● Found {count} device(s)")
                self.append_log(f"[SYSTEM] Found {count} compatible N6705C device(s).")

                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    self.visa_resource_combo.setCurrentText(default_device)
                else:
                    self.visa_resource_combo.setCurrentIndex(0)
            else:
                self.visa_resource_combo.addItem("No N6705C device found")
                self.visa_resource_combo.setEnabled(False)
                self.set_system_status("● No device found", is_error=True)
                self.append_log("[SYSTEM] No compatible N6705C instrument found.")

        except Exception as e:
            self.set_system_status("● Search failed", is_error=True)
            self.append_log(f"[ERROR] Search failed: {str(e)}")
        finally:
            self.search_btn.setEnabled(True)

    def _on_connect_or_disconnect(self):
        """动态连接按钮：未连接时执行连接，已连接时执行断开"""
        if self.is_connected:
            self._on_disconnect()
        else:
            self._on_connect()

    def _on_connect(self):
        if DEBUG_MOCK:
            self.n6705c = MockN6705C()
            self._update_connect_button_state(True)
            self.set_system_status("● Connected (Mock)")
            self.search_btn.setEnabled(False)
            self.instrument_info_label.setText("Mock N6705C (DEBUG)")
            self.append_log("[DEBUG] Mock N6705C connected.")
            self.connection_status_changed.emit(True)
            return
        self.set_system_status("● Connecting")
        self.append_log("[SYSTEM] Attempting instrument connection...")
        self.connect_btn.setEnabled(False)

        try:
            device_address = self.visa_resource_combo.currentText()
            self.n6705c = N6705C(device_address)

            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self._update_connect_button_state(True)
                self.set_system_status("● Connected")
                self.search_btn.setEnabled(False)

                pretty_name = device_address
                try:
                    pretty_name = device_address.split("::")[1]
                except Exception:
                    pass

                self.instrument_info_label.setText(pretty_name)
                self.append_log("[SYSTEM] N6705C connected successfully.")
                self.append_log(f"[IDN] {idn.strip()}")

                if self._n6705c_top:
                    self._n6705c_top.connect_a(device_address, self.n6705c)

                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("● Device mismatch", is_error=True)
                self.append_log("[ERROR] Connected device is not N6705C.")
        except Exception as e:
            self.set_system_status("● Connection failed", is_error=True)
            self.append_log(f"[ERROR] Connection failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_disconnect(self):
        self.set_system_status("● Disconnecting")
        self.append_log("[SYSTEM] Disconnecting instrument...")
        self.connect_btn.setEnabled(False)

        try:
            if self._n6705c_top:
                self._n6705c_top.disconnect_a()
                self.n6705c = None
            else:
                if self.n6705c is not None:
                    if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                        self.n6705c.instr.close()
                    if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                        self.n6705c.rm.close()
                self.n6705c = None

            self._update_connect_button_state(False)

            self.set_system_status("● Ready")
            self.search_btn.setEnabled(True)
            self.instrument_info_label.setText("USB0::0x0957::0x0F07::MY53004321")
            self.append_log("[SYSTEM] Instrument disconnected.")

            self.connection_status_changed.emit(False)

        except Exception as e:
            self.set_system_status("● Disconnect failed", is_error=True)
            self.append_log(f"[ERROR] Disconnect failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def get_n6705c_instance(self):
        return self.n6705c

    def is_n6705c_connected(self):
        return self.is_connected


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from log_config import setup_logging, get_logger
    setup_logging()
    _logger = get_logger(__name__)

    def custom_message_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return
        _logger.debug("%s:%s - %s", context.file, context.line, message)

    qInstallMessageHandler(custom_message_handler)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = PMUDCDCEfficiencyUI()
    window.setWindowTitle("PMU DCDC Efficiency Test")
    window.resize(1200, 800)
    window.show()

    sys.exit(app.exec())