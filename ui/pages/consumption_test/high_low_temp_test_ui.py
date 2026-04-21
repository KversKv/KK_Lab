#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import os
import time
import csv

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGridLayout, QFrame, QScrollArea,
    QSizePolicy, QSpinBox, QDoubleSpinBox,
    QFileDialog
)
from PySide6.QtCore import (
    Qt, Signal, QThread, QObject, QRectF,
    QPropertyAnimation, Property, QEasingCurve
)
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen, QBrush
from PySide6.QtSvg import QSvgRenderer
import pyqtgraph as pg

from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import VT6002ConnectionMixin
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.styles import SCROLL_AREA_STYLE, START_BTN_STYLE, update_start_btn_state
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockVT6002

from log_config import get_logger

logger = get_logger(__name__)

_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "resources", "icons"
)


def _tinted_svg_icon(svg_path, color, size=18):
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)


class _ToggleSwitch(QWidget):

    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._thumb_pos = 1.0 if checked else 0.0
        self.setFixedSize(36, 20)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumb_pos")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_thumb_pos(self):
        return self._thumb_pos

    def _set_thumb_pos(self, val):
        self._thumb_pos = val
        self.update()

    thumb_pos = Property(float, _get_thumb_pos, _set_thumb_pos)

    def isChecked(self):
        return self._checked

    def setChecked(self, val):
        if val == self._checked:
            return
        self._checked = val
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if val else 0.0)
        self._anim.start()
        self.toggled.emit(val)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2.0

        if self._checked:
            track_color = QColor("#5b5cf6")
        else:
            track_color = QColor("#2a3555")

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(0, 0, w, h, radius, radius)

        thumb_r = h - 6
        x = 3 + self._thumb_pos * (w - thumb_r - 6)
        y = 3
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(int(x), int(y), int(thumb_r), int(thumb_r))
        p.end()


class _HighLowTempTestWorker(QObject):
    log = Signal(str)
    finished = Signal(dict)
    progress = Signal(dict)
    progress_int = Signal(int)
    error = Signal(str)

    def __init__(self, config, n6705c_a=None, n6705c_b=None, vt6002=None, mock_mode=False, parent=None):
        super().__init__(parent)
        self.config = config
        self.n6705c_a = n6705c_a
        self.n6705c_b = n6705c_b
        self.vt6002 = vt6002
        self.mock_mode = mock_mode
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def _float_range(self, start, end, step):
        arr = []
        if step <= 0:
            return arr
        if start <= end:
            x = start
            while x <= end + 1e-9:
                arr.append(round(x, 3))
                x += step
        else:
            x = start
            while x >= end - 1e-9:
                arr.append(round(x, 3))
                x -= step
        return arr

    def run(self):
        try:
            result = self._run_temp_consumption()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _run_temp_consumption(self):
        temp_start = self.config["temp_start"]
        temp_end = self.config["temp_end"]
        temp_step = self.config["temp_step"]
        soak_time = self.config.get("soak_time", 180)
        tolerance = self.config.get("stable_tolerance", 0.5)
        test_time = self.config.get("test_time", 5)
        sample_period = self.config.get("sample_period", 0.02)
        channels = self.config.get("channels", [1])

        temps = self._float_range(temp_start, temp_end, temp_step)
        if not temps:
            raise ValueError("Invalid temperature range")

        all_results = []
        self.log.emit("[INFO] Starting High-Low Temperature Consumption Test")
        self.log.emit(f"[INFO] Temperature Range = {temp_start} °C -> {temp_end} °C, step={temp_step} °C")
        self.log.emit(f"[INFO] Soak Time = {soak_time} s, Tolerance = {tolerance} °C")
        self.log.emit(f"[INFO] Measurement Time = {test_time} s, Sample Period = {sample_period} s")
        self.log.emit(f"[INFO] Measurement Channels = {channels}")

        if self.mock_mode:
            self.log.emit("[MOCK] Using simulated chamber and power data")
            total_temps = len(temps)
            for idx, t in enumerate(temps):
                if self._stop_flag:
                    self.log.emit("[WARN] Test stopped")
                    break
                base_current = 5.0 + (t - 25.0) * 0.03
                noise = math.sin(t / 10.0) * 0.2
                ch_results = {}
                for ch in channels:
                    avg_current = base_current + noise + ch * 0.5
                    ch_results[ch] = avg_current
                all_results.append({"temp": t, "currents": ch_results})
                self.progress.emit({"temp": t, "currents": ch_results})
                self.progress_int.emit(int((idx + 1) * 100 / total_temps))
                ch_str = "  ".join([f"CH{ch}={ch_results[ch]:.3f}mA" for ch in channels])
                self.log.emit(f"[DATA] Temp={t:>7.1f} °C  |  {ch_str}")
                time.sleep(0.05)
            return {"data": all_results, "channels": channels}

        chamber = self.vt6002
        if not chamber:
            raise RuntimeError("VT6002 chamber not connected")

        n6705c = self.n6705c_a
        if not n6705c:
            raise RuntimeError("N6705C not connected")

        total_temps = len(temps)
        for idx, t in enumerate(temps):
            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            chamber.set_temperature(t)
            if idx == 0:
                try:
                    chamber.start()
                    self.log.emit("[INFO] Chamber start command sent.")
                except Exception as e:
                    self.log.emit(f"[WARN] Chamber start command failed: {e}")
            self.log.emit(f"[INFO] [{idx + 1}/{total_temps}] Chamber set temperature: {t:.1f} °C, waiting for stabilization...")

            history = []
            stable_count = 0
            wait_t0 = time.time()
            while True:
                if self._stop_flag:
                    break
                actual_temp = chamber.get_current_temp()
                history.append(actual_temp)
                if len(history) > 10:
                    history.pop(0)
                if len(history) >= 5:
                    if max(history) - min(history) < tolerance:
                        stable_count += 1
                    else:
                        stable_count = 0
                    if stable_count >= 3:
                        break
                time.sleep(30)

            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            wait_elapsed = time.time() - wait_t0
            actual_temp = chamber.get_current_temp()
            self.log.emit(
                f"[INFO] [{idx + 1}/{total_temps}] Temperature stabilized: "
                f"target={t:.1f} °C, actual={actual_temp:.2f} °C, waited {wait_elapsed:.0f}s"
            )

            self.log.emit(f"[INFO] DUT thermal soak in progress ({soak_time}s)...")
            for i in range(soak_time):
                if self._stop_flag:
                    break
                time.sleep(1)

            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            ch_results = {}
            stop_check = lambda: self._stop_flag
            self.log.emit(f"[INFO] [{idx + 1}/{total_temps}] Measuring average current via datalog (time={test_time}s, period={sample_period}s)...")
            datalog_result = n6705c.fetch_current_by_datalog(
                channels, test_time, sample_period,
                stop_check=stop_check,
            )
            for ch in channels:
                avg_current_a = datalog_result.get(ch, 0.0)
                ch_results[ch] = avg_current_a * 1000.0

            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            actual_temp = chamber.get_current_temp()
            all_results.append({"temp": actual_temp, "currents": ch_results})
            self.progress.emit({"temp": actual_temp, "currents": ch_results})
            self.progress_int.emit(int((idx + 1) * 100 / total_temps))
            ch_str = "  ".join([f"CH{ch}={ch_results[ch]:.3f}mA" for ch in channels])
            self.log.emit(f"[DATA] Temp={actual_temp:>7.2f} °C  |  {ch_str}")

        chamber.set_temperature(25.0)
        self.log.emit("[INFO] Chamber restored to 25.0 °C")

        if all_results:
            self.log.emit("")
            self.log.emit("=" * 70)
            self.log.emit("  High-Low Temperature Consumption Test Summary")
            self.log.emit("=" * 70)
            header = f"  {'#':>3}  {'Temp (°C)':>10}"
            for ch in channels:
                header += f"  {'CH' + str(ch) + ' (mA)':>12}"
            self.log.emit(header)
            self.log.emit("-" * 70)
            for i, r in enumerate(all_results):
                row = f"  {i + 1:>3}  {r['temp']:>10.2f}"
                for ch in channels:
                    row += f"  {r['currents'].get(ch, 0.0):>12.3f}"
                self.log.emit(row)
            self.log.emit("=" * 70)

        return {"data": all_results, "channels": channels}


class HighLowTempConsumptionTestUI(N6705CConnectionMixin, VT6002ConnectionMixin, QWidget):

    connection_status_changed = Signal(bool)

    CHANNEL_COLORS = [
        "#d4a514", "#18b67a", "#2f6fed", "#d14b72",
        "#a855f7", "#06b6d4", "#f97316", "#ec4899",
    ]

    def __init__(self, n6705c_top=None, parent=None):
        super().__init__(parent)
        self._n6705c_top = n6705c_top
        self.init_n6705c_connection(n6705c_top)
        self.init_vt6002_connection()

        self._test_thread = None
        self._test_worker = None
        self.result_data = []

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()
        self.sync_n6705c_from_top()

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)
        self.setStyleSheet("""
            QWidget {
                background-color: #020618;
                color: #c8c8c8;
                border: none;
            }

            QFrame#page {
                background-color: #020618;
            }

            QFrame#panel, QFrame#chart_panel {
                background-color: #0a1428;
                border: 1.5px solid #162040;
                border-radius: 10px;
            }

            QFrame#config_inner_panel {
                background-color: #0b1630;
                border: 1px solid #1e3060;
                border-radius: 8px;
            }

            QLabel#section_title {
                color: #8faad8;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1.5px;
            }

            QLabel#title_label {
                font-size: 18px;
                font-weight: 700;
                color: #e8eeff;
            }

            QLabel#subtitle_label {
                font-size: 12px;
                color: #6878a8;
            }

            QLabel#muted_label {
                color: #4a5a80;
                font-size: 11px;
            }

            QDoubleSpinBox, QSpinBox {
                background-color: #0a1733;
                border: 1.5px solid #1e3060;
                border-radius: 5px;
                padding: 3px 6px;
                color: #c8d8f8;
                font-size: 12px;
            }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px; height: 0px; border: none;
            }

            QLabel {
                color: #c8c8c8;
                border: none;
                background: transparent;
            }

            QLabel#statusOk { color: #15d1a3; font-weight: 600; background-color: transparent; }
            QLabel#statusWarn { color: #ffb84d; font-weight: 600; background-color: transparent; }
            QLabel#statusErr { color: #ff5e7a; font-weight: 600; background-color: transparent; }

            QFrame#left_scroll_content {
                background-color: transparent;
                border: none;
            }
        """ + START_BTN_STYLE + SCROLL_AREA_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 6, 8, 8)
        root_layout.setSpacing(8)

        self.page = QFrame()
        self.page.setObjectName("page")
        page_layout = QVBoxLayout(self.page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(
            _tinted_svg_icon(os.path.join(_ICONS_DIR, "thermometer.svg"), "#4dc9f6", 22).pixmap(22, 22)
        )
        icon_label.setFixedSize(22, 22)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title_text = "High-Low Temperature Consumption Test"
        if DEBUG_MOCK:
            title_text += "  🟡 MOCK MODE"
        title_label = QLabel(title_text)
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("border: none")

        subtitle_label = QLabel("Measure chip power consumption curves across different temperatures using VT6002 chamber and N6705C power analyzer.")
        subtitle_label.setObjectName("subtitle_label")
        subtitle_label.setStyleSheet("border: none")

        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)
        header_layout.addWidget(icon_label, 0, Qt.AlignTop)
        header_layout.addLayout(title_col)
        header_layout.addStretch()
        page_layout.addLayout(header_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        left_wrapper = QVBoxLayout()
        left_wrapper.setContentsMargins(0, 0, 0, 0)
        left_wrapper.setSpacing(8)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.left_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.left_scroll.setMinimumWidth(320)
        self.left_scroll.setMaximumWidth(320)

        left_content = QFrame()
        left_content.setObjectName("left_scroll_content")
        left_content.setMinimumWidth(298)
        left_content.setMaximumWidth(298)
        left_content.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        left_col = QVBoxLayout(left_content)
        left_col.setContentsMargins(0, 0, 6, 0)
        left_col.setSpacing(12)

        instruments_panel = QFrame()
        instruments_panel.setObjectName("panel")
        instruments_layout = QVBoxLayout(instruments_panel)
        instruments_layout.setContentsMargins(12, 12, 12, 12)
        instruments_layout.setSpacing(10)

        instruments_title = QLabel("Instrument Connection")
        instruments_title.setObjectName("section_title")
        instruments_layout.addWidget(instruments_title)

        n6705c_card = QFrame()
        n6705c_card.setObjectName("config_inner_panel")
        n6705c_card_layout = QVBoxLayout(n6705c_card)
        n6705c_card_layout.setContentsMargins(10, 10, 10, 10)
        n6705c_card_layout.setSpacing(6)
        n6705c_title_row = QHBoxLayout()
        n6705c_title_row.setSpacing(6)
        n6705c_title = QLabel("N6705C Power Analyzer")
        n6705c_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        n6705c_title_row.addWidget(n6705c_title)
        n6705c_title_row.addStretch()
        n6705c_card_layout.addLayout(n6705c_title_row)
        self.build_n6705c_connection_widgets(n6705c_card_layout, title_row=n6705c_title_row)
        instruments_layout.addWidget(n6705c_card)

        vt6002_card = QFrame()
        vt6002_card.setObjectName("config_inner_panel")
        vt6002_card_layout = QVBoxLayout(vt6002_card)
        vt6002_card_layout.setContentsMargins(10, 10, 10, 10)
        vt6002_card_layout.setSpacing(6)
        vt6002_title_row = QHBoxLayout()
        vt6002_title_row.setSpacing(6)
        vt6002_title = QLabel("VT6002 Chamber")
        vt6002_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        vt6002_title_row.addWidget(vt6002_title)
        vt6002_title_row.addStretch()
        vt6002_card_layout.addLayout(vt6002_title_row)
        self.build_vt6002_connection_widgets(vt6002_card_layout)
        vt6002_card_layout.removeWidget(self.vt6002_status_label)
        vt6002_title_row.addWidget(self.vt6002_status_label)
        instruments_layout.addWidget(vt6002_card)

        left_col.addWidget(instruments_panel)

        params_panel = QFrame()
        params_panel.setObjectName("panel")
        params_layout = QVBoxLayout(params_panel)
        params_layout.setContentsMargins(12, 12, 12, 12)
        params_layout.setSpacing(8)

        params_title = QLabel("Temperature Parameters")
        params_title.setObjectName("section_title")
        params_layout.addWidget(params_title)

        temp_frame = QFrame()
        temp_frame.setObjectName("config_inner_panel")
        temp_grid = QGridLayout(temp_frame)
        temp_grid.setContentsMargins(10, 10, 10, 10)
        temp_grid.setHorizontalSpacing(6)
        temp_grid.setVerticalSpacing(6)

        temp_grid.addWidget(QLabel("Start Temp (°C)"), 0, 0)
        temp_grid.addWidget(QLabel("Stop Temp (°C)"), 0, 1)
        temp_grid.addWidget(QLabel("Step Temp (°C)"), 0, 2)

        self.temp_start = QDoubleSpinBox()
        self.temp_start.setRange(-80.0, 180.0)
        self.temp_start.setValue(-40.0)
        self.temp_start.setSingleStep(5.0)
        self.temp_start.setDecimals(1)

        self.temp_end = QDoubleSpinBox()
        self.temp_end.setRange(-80.0, 180.0)
        self.temp_end.setValue(85.0)
        self.temp_end.setSingleStep(5.0)
        self.temp_end.setDecimals(1)

        self.temp_step = QDoubleSpinBox()
        self.temp_step.setRange(0.1, 100.0)
        self.temp_step.setValue(5.0)
        self.temp_step.setSingleStep(1.0)
        self.temp_step.setDecimals(1)

        temp_grid.addWidget(self.temp_start, 1, 0)
        temp_grid.addWidget(self.temp_end, 1, 1)
        temp_grid.addWidget(self.temp_step, 1, 2)

        temp_grid.addWidget(QLabel("Soak Time (s)"), 2, 0)
        temp_grid.addWidget(QLabel("Tolerance (°C)"), 2, 1)

        self.soak_time = QSpinBox()
        self.soak_time.setRange(0, 3600)
        self.soak_time.setValue(180)
        self.soak_time.setSingleStep(30)

        self.stable_tolerance = QDoubleSpinBox()
        self.stable_tolerance.setRange(0.1, 5.0)
        self.stable_tolerance.setValue(0.5)
        self.stable_tolerance.setSingleStep(0.1)
        self.stable_tolerance.setDecimals(1)

        temp_grid.addWidget(self.soak_time, 3, 0)
        temp_grid.addWidget(self.stable_tolerance, 3, 1)

        params_layout.addWidget(temp_frame)

        measure_frame = QFrame()
        measure_frame.setObjectName("config_inner_panel")
        measure_grid = QGridLayout(measure_frame)
        measure_grid.setContentsMargins(10, 10, 10, 10)
        measure_grid.setHorizontalSpacing(6)
        measure_grid.setVerticalSpacing(6)

        measure_grid.addWidget(QLabel("Measure Time (s)"), 0, 0)
        measure_grid.addWidget(QLabel("Sample Period (s)"), 0, 1)

        self.test_time = QDoubleSpinBox()
        self.test_time.setRange(0.1, 600.0)
        self.test_time.setValue(5.0)
        self.test_time.setSingleStep(1.0)
        self.test_time.setDecimals(1)

        self.sample_period = QDoubleSpinBox()
        self.sample_period.setRange(0.001, 10.0)
        self.sample_period.setValue(0.02)
        self.sample_period.setSingleStep(0.01)
        self.sample_period.setDecimals(3)

        measure_grid.addWidget(self.test_time, 1, 0)
        measure_grid.addWidget(self.sample_period, 1, 1)

        params_layout.addWidget(measure_frame)

        channels_frame = QFrame()
        channels_frame.setObjectName("config_inner_panel")
        channels_vbox = QVBoxLayout(channels_frame)
        channels_vbox.setContentsMargins(10, 10, 10, 10)
        channels_vbox.setSpacing(6)

        channels_title = QLabel("Channels")
        channels_title.setStyleSheet("color: #8faad8; font-size: 11px; font-weight: 600; border: none;")
        channels_vbox.addWidget(channels_title)

        self.ch_toggles = {}
        ch_colors = ["#d4a514", "#18b67a", "#2f6fed", "#d14b72"]
        for i in range(4):
            ch_num = i + 1
            row = QHBoxLayout()
            row.setSpacing(8)
            toggle = _ToggleSwitch(checked=(ch_num == 1))
            label = QLabel(f"CH{ch_num}")
            label.setStyleSheet(f"color: {ch_colors[i]}; font-size: 11px; font-weight: 600; border: none;")
            row.addWidget(toggle)
            row.addWidget(label)
            row.addStretch()
            channels_vbox.addLayout(row)
            self.ch_toggles[ch_num] = toggle

        params_layout.addWidget(channels_frame)

        left_col.addWidget(params_panel)

        left_col.addStretch()

        self.left_scroll.setWidget(left_content)
        left_wrapper.addWidget(self.left_scroll, 1)

        self.start_btn = QPushButton("▷ Start Test")
        self.start_btn.setObjectName("primaryStartBtn")
        left_wrapper.addWidget(self.start_btn)

        body_layout.addLayout(left_wrapper)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        chart_panel = QFrame()
        chart_panel.setObjectName("chart_panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(12, 12, 12, 12)
        chart_layout.setSpacing(6)

        chart_header = QHBoxLayout()
        chart_title = QLabel("Temperature vs Current Consumption")
        chart_title.setObjectName("section_title")
        chart_header.addWidget(chart_title)
        chart_header.addStretch()
        self.export_csv_btn = QPushButton("💾 Export CSV")
        self.export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 10px;
                min-height: 24px;
                max-height: 24px;
            }
            QPushButton:hover { background-color: #1c315b; }
        """)
        chart_header.addWidget(self.export_csv_btn)
        chart_layout.addLayout(chart_header)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#050d1e")
        self.plot_widget.setMinimumHeight(300)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_widget.setLabel("left", "Current (mA)")
        self.plot_widget.setLabel("bottom", "Temperature (°C)")
        self.plot_widget.addLegend(offset=(10, 10))
        chart_layout.addWidget(self.plot_widget, 1)

        right_col.addWidget(chart_panel, 1)

        self.execution_logs = ExecutionLogsFrame(show_progress=True)
        self.execution_logs.setMaximumHeight(150)
        right_col.addWidget(self.execution_logs)

        body_layout.addLayout(right_col, 1)
        page_layout.addLayout(body_layout, 1)
        root_layout.addWidget(self.page)

    def _init_ui_elements(self):
        self._update_n6705c_connect_button_state(False)
        self._plot_curves = {}

    def _bind_signals(self):
        self.bind_n6705c_signals()
        self.bind_vt6002_signals()
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.export_csv_btn.clicked.connect(self._on_export_csv)

    def _on_start_clicked(self):
        if self._test_thread and self._test_thread.isRunning():
            if self._test_worker:
                self._test_worker.stop()
            self.start_btn.setEnabled(False)
            self.append_log("[INFO] Stopping test, please wait...")
            return

        if not DEBUG_MOCK:
            if not hasattr(self, 'vt6002') or self.vt6002 is None:
                self.append_log("[ERROR] VT6002 chamber not connected")
                return
            if not hasattr(self, 'n6705c') or self.n6705c is None:
                self.append_log("[ERROR] N6705C not connected")
                return

        channels = [ch for ch, toggle in self.ch_toggles.items() if toggle.isChecked()]
        if not channels:
            self.append_log("[ERROR] At least one channel must be enabled")
            return
        config = {
            "temp_start": self.temp_start.value(),
            "temp_end": self.temp_end.value(),
            "temp_step": self.temp_step.value(),
            "soak_time": self.soak_time.value(),
            "stable_tolerance": self.stable_tolerance.value(),
            "test_time": self.test_time.value(),
            "sample_period": self.sample_period.value(),
            "channels": channels,
        }

        if config["temp_step"] <= 0:
            self.append_log("[ERROR] Temperature step must be > 0")
            return

        self.execution_logs.set_progress(0)
        self.plot_widget.clear()
        self._plot_curves = {}
        self.result_data = []

        vt6002 = getattr(self, 'vt6002', None)
        n6705c_a = getattr(self, 'n6705c', None)

        self._test_worker = _HighLowTempTestWorker(
            config=config,
            n6705c_a=n6705c_a,
            n6705c_b=None,
            vt6002=vt6002,
            mock_mode=DEBUG_MOCK,
        )
        self._test_thread = QThread()
        self._test_worker.moveToThread(self._test_thread)

        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.log.connect(self.append_log)
        self._test_worker.progress.connect(self._on_progress)
        self._test_worker.progress_int.connect(self._on_progress_int)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.error.connect(self._on_test_error)
        self._test_worker.finished.connect(self._test_thread.quit)
        self._test_worker.error.connect(self._test_thread.quit)
        self._test_thread.finished.connect(self._on_thread_cleaned)

        self._test_thread.start()
        update_start_btn_state(self.start_btn, running=True,
                               start_text="▷ Start Test", stop_text="■ Stop Test")

    def _on_progress(self, data):
        temp = data["temp"]
        currents = data["currents"]
        self.result_data.append(data)

        channels = list(currents.keys())
        for ch in channels:
            if ch not in self._plot_curves:
                color_idx = (ch - 1) % len(self.CHANNEL_COLORS)
                pen = pg.mkPen(color=self.CHANNEL_COLORS[color_idx], width=2)
                self._plot_curves[ch] = self.plot_widget.plot(
                    [], [], pen=pen, name=f"CH{ch}",
                    symbol='o', symbolSize=6,
                    symbolBrush=self.CHANNEL_COLORS[color_idx]
                )

        for ch in channels:
            temps = [r["temp"] for r in self.result_data]
            vals = [r["currents"].get(ch, 0.0) for r in self.result_data]
            self._plot_curves[ch].setData(temps, vals)

    def _on_progress_int(self, val):
        self.execution_logs.set_progress(val)

    def _on_test_finished(self, result):
        self.execution_logs.set_progress(100)
        self.append_log("[INFO] Test completed successfully.")

    def _on_test_error(self, err_msg):
        self.append_log(f"[ERROR] {err_msg}")

    def _on_thread_cleaned(self):
        if self._test_worker is not None:
            self._test_worker.deleteLater()
        if self._test_thread is not None:
            self._test_thread.deleteLater()
        self._test_worker = None
        self._test_thread = None
        update_start_btn_state(self.start_btn, running=False,
                               start_text="▷ Start Test", stop_text="■ Stop Test")
        self.start_btn.setEnabled(True)

    def _on_export_csv(self):
        if not self.result_data:
            self.append_log("[WARN] No data to export")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return

        channels = list(self.result_data[0]["currents"].keys()) if self.result_data else []
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                header = ["Temperature (°C)"] + [f"CH{ch} (mA)" for ch in channels]
                writer.writerow(header)
                for r in self.result_data:
                    row = [f"{r['temp']:.2f}"] + [f"{r['currents'].get(ch, 0.0):.4f}" for ch in channels]
                    writer.writerow(row)
            self.append_log(f"[INFO] Data exported to: {path}")
        except Exception as e:
            self.append_log(f"[ERROR] Export failed: {e}")

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def get_test_mode(self):
        return "High-Low Temperature Consumption Test"
