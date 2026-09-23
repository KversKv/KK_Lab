#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import os
from ui.resource_path import get_resource_base
import time
import csv

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGridLayout, QFrame, QScrollArea,
    QSizePolicy, QSpinBox, QDoubleSpinBox,
    QFileDialog, QLineEdit
)
from PySide6.QtCore import (
    Qt, Signal, QThread, QObject, QRectF, QSize,
    QPropertyAnimation, Property, QEasingCurve
)
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPen, QBrush
import pyqtgraph as pg

from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import ChamberConnectionMixin
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.styles import SCROLL_AREA_STYLE, START_BTN_STYLE, update_start_btn_state
from debug_config import DEBUG_MOCK
from instruments.chambers import TemperatureStabilizer

from log_config import get_logger

logger = get_logger(__name__)

_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "consumption_test_SVGs"
)

from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.config_memory import ConfigMemory


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

    def __init__(self, config, n6705c_a=None, n6705c_b=None, chamber=None, mock_mode=False, parent=None):
        super().__init__(parent)
        self.config = config
        self.n6705c_a = n6705c_a
        self.n6705c_b = n6705c_b
        self.chamber = chamber
        self.mock_mode = mock_mode
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def _interruptible_sleep(self, duration, interval=0.2):
        elapsed = 0.0
        while elapsed < duration:
            if self._stop_flag:
                return
            step = min(interval, duration - elapsed)
            time.sleep(step)
            elapsed += step

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
        ext_power = self.config.get("ext_power", {})
        ext_rails = ext_power.get("rails", []) if ext_power.get("enabled") else []

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
                rail_results = {}
                rail_vouts = {}
                for rail in ext_rails:
                    rail_results[rail["name"]] = (
                        rail["current_limit"] * 1000.0 * 0.4
                        + (t - 25.0) * 0.01
                        + math.sin(t / 8.0) * 0.05
                    )
                    rail_vouts[rail["name"]] = (
                        rail["voltage"] * 0.98 + math.sin(t / 6.0) * 0.005
                    )
                all_results.append({"temp": t, "currents": ch_results, "rails": rail_results,
                                    "rail_vouts": rail_vouts})
                self.progress.emit({"temp": t, "currents": ch_results, "rails": rail_results,
                                    "rail_vouts": rail_vouts})
                self.progress_int.emit(int((idx + 1) * 100 / total_temps))
                ch_str = "  ".join([f"CH{ch}={ch_results[ch]:.6f}mA" for ch in channels])
                rail_str = "  ".join([f"{name}={rail_results[name]:.6f}mA" for name in rail_results])
                vout_str = "  ".join([f"{name}_Vout={rail_vouts[name]:.6f}V" for name in rail_vouts])
                self.log.emit(f"[DATA] Temp={t:>7.1f} °C  |  {ch_str}"
                              + (f"  |  {rail_str}" if rail_str else "")
                              + (f"  |  {vout_str}" if vout_str else ""))
                time.sleep(0.05)
            return {"data": all_results, "channels": channels}

        chamber = self.chamber
        if not chamber:
            raise RuntimeError("Chamber not connected")

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

            stabilizer = TemperatureStabilizer(
                chamber,
                tolerance=tolerance,
                log_fn=self.log.emit,
                stop_check=lambda: self._stop_flag,
            )
            result = stabilizer.wait_for_stable(t)

            if self._stop_flag or result.reason == "stopped":
                self.log.emit("[WARN] Test stopped")
                break

            actual_temp = result.actual if result.actual is not None else chamber.get_current_temp()
            self.log.emit(
                f"[INFO] [{idx + 1}/{total_temps}] Temperature {result.reason}: "
                f"target={t:.1f} °C, actual={actual_temp:.2f} °C, "
                f"waited {result.waited_s:.0f}s, polls={result.poll_count}"
            )

            self.log.emit(f"[INFO] DUT thermal soak in progress ({soak_time}s)...")
            self._interruptible_sleep(soak_time)

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

            rail_results = {}
            rail_vouts = {}
            for rail in ext_rails:
                if self._stop_flag:
                    self.log.emit("[WARN] Test stopped")
                    break
                rail_ch = rail["channel"]
                rail_name = rail["name"]
                try:
                    n6705c.set_voltagemode(rail_ch)
                    rail_vouts[rail_name] = n6705c.measure_voltage(rail_ch)
                    self.log.emit(
                        f"[DATA] Temp={t:>7.1f} °C  |  Rail {rail_name} "
                        f"(CH{rail_ch}) DUT Vout = {rail_vouts[rail_name]:.6f}V"
                    )
                except Exception as e:
                    self.log.emit(f"[ERROR] Rail {rail_name} (CH{rail_ch}) DUT Vout measure failed: {e}")
                try:
                    n6705c.set_mode(rail_ch, "PS2Q")
                    n6705c.set_voltage(rail_ch, rail["voltage"])
                    n6705c.set_current_limit(rail_ch, rail["current_limit"])
                    n6705c.channel_on(rail_ch)
                    try:
                        self._interruptible_sleep(0.2)
                        rail_results[rail_name] = n6705c.measure_current(rail_ch) * 1000.0
                    finally:
                        n6705c.channel_off(rail_ch)
                    self.log.emit(
                        f"[DATA] Temp={t:>7.1f} °C  |  Rail {rail_name} "
                        f"(CH{rail_ch}, {rail['voltage']:.3f}V, lim {rail['current_limit']:.3f}A) "
                        f"= {rail_results[rail_name]:.6f}mA"
                    )
                except Exception as e:
                    self.log.emit(f"[ERROR] Rail {rail_name} (CH{rail_ch}) measure failed: {e}")

            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            actual_temp = chamber.get_current_temp()
            all_results.append({"temp": actual_temp, "currents": ch_results, "rails": rail_results,
                                "rail_vouts": rail_vouts})
            self.progress.emit({"temp": actual_temp, "currents": ch_results, "rails": rail_results,
                                "rail_vouts": rail_vouts})
            self.progress_int.emit(int((idx + 1) * 100 / total_temps))
            ch_str = "  ".join([f"CH{ch}={ch_results[ch]:.6f}mA" for ch in channels])
            rail_str = "  ".join([f"{name}={rail_results[name]:.6f}mA" for name in rail_results])
            vout_str = "  ".join([f"{name}_Vout={rail_vouts[name]:.6f}V" for name in rail_vouts])
            self.log.emit(f"[DATA] Temp={actual_temp:>7.2f} °C  |  {ch_str}"
                          + (f"  |  {rail_str}" if rail_str else "")
                          + (f"  |  {vout_str}" if vout_str else ""))

        chamber.set_temperature(25.0)
        self.log.emit("[INFO] Chamber restored to 25.0 °C")

        if all_results:
            self.log.emit("")
            self.log.emit("[SUMMARY] " + "=" * 70)
            self.log.emit("[SUMMARY]   High-Low Temperature Consumption Test Summary")
            self.log.emit("[SUMMARY] " + "=" * 70)
            header = f"  {'#':>3}  {'Temp (°C)':>10}"
            for ch in channels:
                header += f"  {'CH' + str(ch) + ' (mA)':>14}"
            for rail in ext_rails:
                header += f"  {rail['name'][:9] + ' (mA)':>14}"
                header += f"  {rail['name'][:9] + ' Vout(V)':>14}"
            self.log.emit(f"[SUMMARY] {header}")
            self.log.emit("[SUMMARY] " + "-" * 70)
            for i, r in enumerate(all_results):
                row = f"  {i + 1:>3}  {r['temp']:>10.2f}"
                for ch in channels:
                    row += f"  {r['currents'].get(ch, 0.0):>14.6f}"
                for rail in ext_rails:
                    row += f"  {r.get('rails', {}).get(rail['name'], 0.0):>14.6f}"
                    row += f"  {r.get('rail_vouts', {}).get(rail['name'], 0.0):>14.6f}"
                self.log.emit(f"[SUMMARY] {row}")
            self.log.emit("[SUMMARY] " + "=" * 70)

        return {"data": all_results, "channels": channels}


class HighLowTempConsumptionTestUI(N6705CConnectionMixin, ChamberConnectionMixin, QWidget):

    connection_status_changed = Signal(bool)

    CHANNEL_COLORS = [
        "#d4a514", "#18b67a", "#2f6fed", "#d14b72",
        "#a855f7", "#06b6d4", "#f97316", "#ec4899",
    ]

    def __init__(self, n6705c_top=None, instrument_manager=None, parent=None):
        super().__init__(parent)
        self._n6705c_top = n6705c_top
        self._instrument_manager = instrument_manager
        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)
        self.init_chamber_connection(instrument_manager=instrument_manager)

        self._test_thread = None
        self._test_worker = None
        self.result_data = []

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()
        self.sync_n6705c_from_top()

        # 上次配置自动记忆（绑定模式，仅恢复控件值，不触发仪器连接）
        self._config_memory = ConfigMemory("consumption_test/high_low_temp", self)
        self._config_memory.bind("temp_start", self.temp_start)
        self._config_memory.bind("temp_end", self.temp_end)
        self._config_memory.bind("temp_step", self.temp_step)
        self._config_memory.bind("soak_time", self.soak_time)
        self._config_memory.bind("stable_tolerance", self.stable_tolerance)
        self._config_memory.bind("test_time", self.test_time)
        self._config_memory.bind("sample_period", self.sample_period)
        for i, row in enumerate(self._ext_rail_rows):
            self._config_memory.bind(f"rail_{i}_name", row["name_edit"])
            self._config_memory.bind(f"rail_{i}_channel", row["ch_combo"])
            self._config_memory.bind(f"rail_{i}_voltage", row["volt_spin"])
            self._config_memory.bind(f"rail_{i}_limit", row["limit_spin"])
        self._config_memory.restore()

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
                border-radius: 12px;
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
                border-radius: 6px;
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

            QLineEdit {
                background-color: #0a1733;
                border: 1.5px solid #1e3060;
                border-radius: 6px;
                padding: 3px 6px;
                color: #c8d8f8;
                font-size: 12px;
            }

            QPushButton#extRailAddBtn {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-size: 11px;
                padding: 0px 10px;
                min-height: 22px;
                max-height: 22px;
            }
            QPushButton#extRailAddBtn:hover { background-color: #1c315b; }
            QPushButton#extRailAddBtn:disabled { color: #4a5a80; background-color: #101c38; }

            QPushButton#extRailDelBtn {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 2px;
                min-height: 20px;
                max-height: 20px;
                min-width: 20px;
                max-width: 20px;
            }
            QPushButton#extRailDelBtn:hover { background-color: #2a1630; }
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
            _tinted_svg_icon(os.path.join(_PAGE_SVGS_DIR, "thermometer.svg"), "#4dc9f6", 22).pixmap(22, 22)
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

        subtitle_label = QLabel("Measure chip power consumption curves across different temperatures using chamber and N6705C power analyzer.")
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

        chamber_card = QFrame()
        chamber_card.setObjectName("config_inner_panel")
        chamber_card_layout = QVBoxLayout(chamber_card)
        chamber_card_layout.setContentsMargins(10, 10, 10, 10)
        chamber_card_layout.setSpacing(6)
        chamber_title_row = QHBoxLayout()
        chamber_title_row.setSpacing(6)
        chamber_title = QLabel("Chamber")
        chamber_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        chamber_title_row.addWidget(chamber_title)
        chamber_title_row.addStretch()
        chamber_card_layout.addLayout(chamber_title_row)
        self.build_chamber_connection_widgets(chamber_card_layout)
        chamber_card_layout.removeWidget(self.chamber_status_label)
        chamber_title_row.addWidget(self.chamber_status_label)
        instruments_layout.addWidget(chamber_card)

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
        measure_grid.addWidget(QLabel("Sample Period (us)"), 0, 1)

        self.test_time = QDoubleSpinBox()
        self.test_time.setRange(0.1, 600.0)
        self.test_time.setValue(5.0)
        self.test_time.setSingleStep(1.0)
        self.test_time.setDecimals(1)

        self.sample_period = QDoubleSpinBox()
        self.sample_period.setRange(20.0, 10_000_000.0)
        self.sample_period.setValue(20.0)
        self.sample_period.setSingleStep(1000.0)
        self.sample_period.setDecimals(0)

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

        ext_power_panel = QFrame()
        ext_power_panel.setObjectName("panel")
        ext_power_layout = QVBoxLayout(ext_power_panel)
        ext_power_layout.setContentsMargins(12, 12, 12, 12)
        ext_power_layout.setSpacing(8)

        ext_power_title_row = QHBoxLayout()
        ext_power_title_row.setSpacing(6)
        ext_power_title = QLabel("External Power Supply")
        ext_power_title.setObjectName("section_title")
        ext_power_title_row.addWidget(ext_power_title)
        ext_power_title_row.addStretch()
        self.ext_power_enabled = _ToggleSwitch(checked=False)
        ext_power_title_row.addWidget(self.ext_power_enabled)
        ext_power_layout.addLayout(ext_power_title_row)

        self.ext_power_content = QFrame()
        self.ext_power_content.setObjectName("left_scroll_content")
        ext_power_content_layout = QVBoxLayout(self.ext_power_content)
        ext_power_content_layout.setContentsMargins(0, 0, 0, 0)
        ext_power_content_layout.setSpacing(6)

        rails_frame = QFrame()
        rails_frame.setObjectName("config_inner_panel")
        self._ext_rail_grid = QGridLayout(rails_frame)
        self._ext_rail_grid.setContentsMargins(10, 10, 10, 10)
        self._ext_rail_grid.setHorizontalSpacing(4)
        self._ext_rail_grid.setVerticalSpacing(6)

        header_style = "color: #8faad8; font-size: 10px; font-weight: 600; border: none;"
        for col, text in enumerate(("Name", "CH", "Volt (V)", "Lim (A)", "")):
            header_label = QLabel(text)
            header_label.setStyleSheet(header_style)
            self._ext_rail_grid.addWidget(header_label, 0, col)
        self._ext_rail_grid.setColumnStretch(0, 1)

        ext_power_content_layout.addWidget(rails_frame)

        self._ext_rail_rows = []
        self._ext_rail_next_row = 1

        self.ext_rail_add_btn = QPushButton("+ Add Rail")
        self.ext_rail_add_btn.setObjectName("extRailAddBtn")
        ext_power_content_layout.addWidget(self.ext_rail_add_btn, 0, Qt.AlignLeft)

        ext_power_layout.addWidget(self.ext_power_content)
        left_col.addWidget(ext_power_panel)

        self._add_ext_rail_row(name="Vcore", channel=4, voltage=0.82, current_limit=0.05)
        self.ext_power_content.setEnabled(False)

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
        self.export_csv_btn = QPushButton("Export CSV")
        _export_svg = os.path.join(_PAGE_SVGS_DIR, "save.svg")
        if os.path.isfile(_export_svg):
            self.export_csv_btn.setIcon(_tinted_svg_icon(_export_svg, "#dbe7ff", 16))
            self.export_csv_btn.setIconSize(QSize(16, 16))
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

        right_splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            chart_panel, show_progress=True, stretch=(3, 1)
        )
        right_col.addWidget(right_splitter, 1)

        body_layout.addLayout(right_col, 1)
        page_layout.addLayout(body_layout, 1)
        root_layout.addWidget(self.page)

    def _init_ui_elements(self):
        self._update_n6705c_connect_button_state(False)
        self._plot_curves = {}

    def _add_ext_rail_row(self, name="", channel=4, voltage=0.8, current_limit=0.05):
        row_idx = self._ext_rail_next_row
        self._ext_rail_next_row += 1

        name_edit = QLineEdit(name)
        name_edit.setPlaceholderText("Rail name")

        ch_combo = DarkComboBox(bg="#0a1733", border="#1e3060",
                                arrow_color="#8faad8", hover_color="#2f6fed")
        ch_combo.addItems([f"CH{i}" for i in range(1, 5)])
        ch = min(max(int(channel), 1), 4)
        ch_combo.setCurrentIndex(ch - 1)

        volt_spin = QDoubleSpinBox()
        volt_spin.setRange(0.0, 20.0)
        volt_spin.setDecimals(3)
        volt_spin.setSingleStep(0.05)
        volt_spin.setValue(voltage)

        limit_spin = QDoubleSpinBox()
        limit_spin.setRange(0.001, 5.0)
        limit_spin.setDecimals(3)
        limit_spin.setSingleStep(0.01)
        limit_spin.setValue(current_limit)

        del_btn = QPushButton()
        del_btn.setObjectName("extRailDelBtn")
        del_btn.setToolTip("Remove rail")
        del_svg = os.path.join(_PAGE_SVGS_DIR, "x-circle.svg")
        if os.path.isfile(del_svg):
            del_btn.setIcon(_tinted_svg_icon(del_svg, "#ff5e7a", 14))
            del_btn.setIconSize(QSize(14, 14))
        else:
            del_btn.setText("x")

        self._ext_rail_grid.addWidget(name_edit, row_idx, 0)
        self._ext_rail_grid.addWidget(ch_combo, row_idx, 1)
        self._ext_rail_grid.addWidget(volt_spin, row_idx, 2)
        self._ext_rail_grid.addWidget(limit_spin, row_idx, 3)
        self._ext_rail_grid.addWidget(del_btn, row_idx, 4)

        row = {
            "name_edit": name_edit,
            "ch_combo": ch_combo,
            "volt_spin": volt_spin,
            "limit_spin": limit_spin,
            "del_btn": del_btn,
        }
        self._ext_rail_rows.append(row)
        del_btn.clicked.connect(lambda checked=False, r=row: self._remove_ext_rail_row(r))

    def _remove_ext_rail_row(self, row):
        if row not in self._ext_rail_rows:
            return
        self._ext_rail_rows.remove(row)
        for widget in row.values():
            self._ext_rail_grid.removeWidget(widget)
            widget.deleteLater()

    def _collect_ext_rails(self):
        rails = []
        for row in self._ext_rail_rows:
            name = row["name_edit"].text().strip()
            if not name:
                name = f"Rail CH{row['ch_combo'].currentIndex() + 1}"
            rails.append({
                "name": name,
                "channel": row["ch_combo"].currentIndex() + 1,
                "voltage": row["volt_spin"].value(),
                "current_limit": row["limit_spin"].value(),
            })
        return rails

    def _bind_signals(self):
        self.bind_n6705c_signals()
        self.bind_chamber_signals()
        self.start_btn.clicked.connect(self._on_start_clicked)
        self.export_csv_btn.clicked.connect(self._on_export_csv)
        self.ext_power_enabled.toggled.connect(self.ext_power_content.setEnabled)
        self.ext_rail_add_btn.clicked.connect(lambda: self._add_ext_rail_row())

    def _on_start_clicked(self):
        if self._test_thread and self._test_thread.isRunning():
            if self._test_worker:
                self._test_worker.stop()
            self.start_btn.setEnabled(False)
            self.append_log("[INFO] Stopping test, please wait...")
            return

        if not DEBUG_MOCK:
            if not hasattr(self, 'chamber') or self.chamber is None:
                self.append_log("[ERROR] Chamber not connected")
                return
            if not hasattr(self, 'n6705c') or self.n6705c is None:
                self.append_log("[ERROR] N6705C not connected")
                return

        channels = [ch for ch, toggle in self.ch_toggles.items() if toggle.isChecked()]
        if not channels:
            self.append_log("[ERROR] At least one channel must be enabled")
            return

        ext_power_enabled = self.ext_power_enabled.isChecked()
        ext_rails = self._collect_ext_rails() if ext_power_enabled else []
        if ext_power_enabled:
            if not ext_rails:
                self.append_log("[ERROR] External power enabled but no rail configured")
                return
            names = [r["name"] for r in ext_rails]
            if len(names) != len(set(names)):
                self.append_log("[ERROR] Duplicate rail names in external power list")
                return

        config = {
            "temp_start": self.temp_start.value(),
            "temp_end": self.temp_end.value(),
            "temp_step": self.temp_step.value(),
            "soak_time": self.soak_time.value(),
            "stable_tolerance": self.stable_tolerance.value(),
            "test_time": self.test_time.value(),
            "sample_period": self.sample_period.value() / 1_000_000.0,
            "channels": channels,
            "ext_power": {
                "enabled": ext_power_enabled,
                "rails": ext_rails,
            },
        }

        if config["temp_step"] <= 0:
            self.append_log("[ERROR] Temperature step must be > 0")
            return

        self.execution_logs.set_progress(0)
        self.plot_widget.clear()
        self._plot_curves = {}
        self.result_data = []

        chamber = getattr(self, 'chamber', None)
        n6705c_a = getattr(self, 'n6705c', None)

        self._test_worker = _HighLowTempTestWorker(
            config=config,
            n6705c_a=n6705c_a,
            n6705c_b=None,
            chamber=chamber,
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
        rails = data.get("rails", {})
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

        rail_names = list(rails.keys())
        for rail_idx, name in enumerate(rail_names):
            curve_key = ("rail", name)
            if curve_key not in self._plot_curves:
                color_idx = (4 + rail_idx) % len(self.CHANNEL_COLORS)
                pen = pg.mkPen(color=self.CHANNEL_COLORS[color_idx], width=2)
                self._plot_curves[curve_key] = self.plot_widget.plot(
                    [], [], pen=pen, name=name,
                    symbol='t', symbolSize=7, connect='finite',
                    symbolBrush=self.CHANNEL_COLORS[color_idx]
                )

        for name in rail_names:
            temps = [r["temp"] for r in self.result_data]
            vals = [
                r.get("rails", {}).get(name, float("nan"))
                for r in self.result_data
            ]
            self._plot_curves[("rail", name)].setData(temps, vals)

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
        rail_names = []
        for r in self.result_data:
            for name in r.get("rails", {}):
                if name not in rail_names:
                    rail_names.append(name)
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                header = (["Temperature (°C)"]
                          + [f"CH{ch} (mA)" for ch in channels]
                          + [f"{name} (mA)" for name in rail_names]
                          + [f"{name} DUT Vout (V)" for name in rail_names])
                writer.writerow(header)
                for r in self.result_data:
                    row = ([f"{r['temp']:.2f}"]
                           + [f"{r['currents'].get(ch, 0.0):.6f}" for ch in channels]
                           + [f"{r.get('rails', {}).get(name, 0.0):.6f}" for name in rail_names]
                           + [f"{r.get('rail_vouts', {}).get(name, 0.0):.6f}" for name in rail_names])
                    writer.writerow(row)
            self.append_log(f"[INFO] Data exported to: {path}")
        except Exception as e:
            self.append_log(f"[ERROR] Export failed: {e}")

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def get_test_mode(self):
        return "High-Low Temperature Consumption Test"


def main():
    from ui.standalone import run_standalone_widget

    return run_standalone_widget(
        lambda: HighLowTempConsumptionTestUI(),
        "High-Low Temperature Test",
    )


if __name__ == "__main__":
    raise SystemExit(main())
