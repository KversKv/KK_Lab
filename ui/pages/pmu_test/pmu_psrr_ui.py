#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PMU PSRR 扫频测试页面。"""
from __future__ import annotations

import math
import threading
from typing import Any

import pyqtgraph as pg
from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.ai.page_contract import (
    CAP_APPLY_CONFIG,
    CAP_GET_CONFIG,
    CAP_GET_RESULT,
    CAP_START_TEST,
    CAP_STOP_TEST,
)
from core.pmu_test.psrr import (
    AudioPrecisionPSRRWorker,
    PSRRTestWorker,
    audio_precision_config_from_dict,
    config_from_dict,
)
from debug_config import DEBUG_MOCK
from log_config import get_logger
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.oscilloscope_module_frame import OscilloscopeConnectionMixin
from ui.widgets.config_memory import ConfigMemory
from ui.widgets.scrollbar import SCROLLBAR_STYLE

logger = get_logger(__name__)


class CardFrame(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)
        self.main_layout.setSpacing(8)
        self.title_row = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        self.title_row.addWidget(self.title_label)
        self.title_row.addStretch()
        self.main_layout.addLayout(self.title_row)


class PMUPSRRUI(N6705CConnectionMixin, OscilloscopeConnectionMixin, QWidget):
    """MSO64B + J2120A 或 Audio Precision 的 PSRR 测试页面。"""

    connection_status_changed = Signal(bool)
    sequence_execution_finished = Signal(bool, str)

    def __init__(self, n6705c_top=None, mso64b_top=None, instrument_manager=None):
        super().__init__()
        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)
        self.init_oscilloscope_connection(mso64b_top, instrument_manager=instrument_manager)
        self.is_test_running = False
        self.test_thread = None
        self.test_worker = None
        self._points: list[dict] = []
        self._last_result: dict | None = None
        self._test_mode = "手动测试"
        self._test_id = "PMU_PSRR_001"
        self._config_widgets: list[QWidget] = []

        self._setup_style()
        self._create_layout()
        self.bind_n6705c_signals()
        self.bind_oscilloscope_signals()
        self.start_test_btn.clicked.connect(self._toggle_test)
        self.stop_test_btn.clicked.connect(self.stop_test)
        self.sync_n6705c_from_top()
        self._sync_scope_from_top()
        self.clear_results()

        self._config_memory = ConfigMemory("pmu_test/psrr", self)
        self._config_memory.bind_interface(
            self.get_test_config,
            lambda cfg: self.apply_config_to_controls(cfg, silent=True),
        )
        self._config_memory.watch(self)
        self._config_memory.restore()

    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setStyleSheet("""
            QWidget { background-color: #050b1a; color: #e8eefc; }
            QWidget#leftPanelInner { background-color: transparent; }
            QLabel { background-color: transparent; color: #dbe7ff; border: none; }
            QLabel#pageTitle { font-size: 18px; font-weight: 700; color: #f8fbff; }
            QLabel#pageSubtitle { font-size: 12px; color: #7da2d6; }
            QFrame#cardFrame {
                background-color: #0d1833; border: 1px solid #1a2a52; border-radius: 12px;
            }
            QLabel#cardTitle { font-size: 11px; font-weight: 700; color: #f4f7ff; }
            QLabel#fieldLabel { color: #8fa7d6; font-size: 11px; }
            QLabel#statusOk { color: #15d1a3; font-weight: 600; }
            QLabel#statusWarn { color: #ffb84d; font-weight: 600; }
            QLabel#statusErr { color: #ff5e7a; font-weight: 600; }
            QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {
                background-color: #0a1733; color: #eef4ff; border: 1px solid #20335f;
                border-radius: 8px; padding: 6px 10px; selection-background-color: #1fa3ff;
            }
            QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus,
            QWidget[aiHighlighted="true"] { border: 1px solid #15d1a3; }
            QComboBox::drop-down { border: none; width: 22px; background: transparent; }
            QComboBox QAbstractItemView {
                background-color: #0a1733; color: #eef4ff; border: 1px solid #20335f;
                selection-background-color: #1a3260; outline: 0px;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px; height: 0px; border: none;
            }
            QPushButton {
                border-radius: 8px; padding: 6px 14px; border: 1px solid #273a66;
                background-color: #1a2748; color: #dce8ff; font-weight: 600;
            }
            QPushButton:hover { background-color: #22345e; border-color: #35508c; }
            QPushButton:disabled { background-color: #11182b; color: #5f6d8f; }
            QPushButton#startTestBtn {
                min-height: 33px; max-height: 33px; padding: 0px 12px;
                background-color: #07463f; border: 1px solid #10bfa0; color: #72f4d7;
            }
            QPushButton#startTestBtn[running="true"] {
                background-color: #4a1730; border: 1px solid #d84578; color: #ff9abb;
            }
            QPushButton#stopTestBtn {
                min-height: 33px; max-height: 33px; padding: 0px 12px;
                background-color: #3d1830; border: 1px solid #5f2748; color: #ff8ead;
            }
            QFrame#resultContainer {
                background-color: #09142e; border: 1px solid #1a2d57; border-radius: 16px;
            }
            QFrame#plotPanel {
                background-color: #020b22; border: 1px solid #1a2d57; border-radius: 12px;
            }
            QFrame[role="resultBox"] {
                background-color: #020b22; border: 1px solid #1a2d57; border-radius: 12px;
            }
            QLabel[role="resultValue"] { color: #19f5c8; font-size: 18px; font-weight: 800; }
            QLabel[role="resultCaption"] { color: #7d94c5; font-size: 10px; }
            QLabel#resultSummary { color: #9bb6e8; font-size: 11px; }
            QCheckBox { background-color: transparent; color: #a9bde2; }
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        title = QLabel("PSRR Automated Test")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Sweep input ripple and measure power-supply rejection with dual-channel RMS acquisition.")
        subtitle.setObjectName("pageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(14)
        root.addLayout(content, 1)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setFixedWidth(330)
        self.left_scroll.setObjectName("leftScrollArea")
        self.left_scroll.setStyleSheet("""
            QScrollArea#leftScrollArea {
                background-color: #0d1833; border: 1px solid #1a2a52; border-radius: 16px;
            }
        """ + SCROLLBAR_STYLE)
        left_panel = QWidget()
        left_panel.setObjectName("leftPanelInner")
        left = QVBoxLayout(left_panel)
        left.setContentsMargins(10, 10, 10, 10)
        left.setSpacing(10)
        self.left_scroll.setWidget(left_panel)
        content.addWidget(self.left_scroll)

        method_card = CardFrame("Measurement Method")
        self.method_combo = QComboBox()
        self.method_combo.addItem("MSO64B + J2120A", "mso64b_j2120a")
        self.method_combo.addItem("Audio Precision", "audio_precision")
        method_card.main_layout.addWidget(self.method_combo)
        left.addWidget(method_card)

        self.n6705c_card = CardFrame("N6705C Connection")
        self.build_n6705c_connection_widgets(
            self.n6705c_card.main_layout, title_row=self.n6705c_card.title_row
        )
        left.addWidget(self.n6705c_card)

        self.scope_card = CardFrame("Oscilloscope Connection")
        self.build_oscilloscope_connection_widgets(
            self.scope_card.main_layout, title_row=self.scope_card.title_row
        )
        left.addWidget(self.scope_card)

        self.excitation_card = CardFrame("Excitation")
        self.source_channel_combo = self._channel_combo()
        self.dc_voltage_spin = self._double_spin(0.1, 20.0, 5.0, 0.1, 3)
        self.afg_amplitude_spin = self._double_spin(0.1, 2000.0, 100.0, 10.0, 2)
        self.start_frequency_spin = self._double_spin(0.1, 50e6, 100.0, 100.0, 3)
        self.end_frequency_spin = self._double_spin(0.1, 50e6, 100000.0, 1000.0, 3)
        self.frequency_points_spin = QSpinBox()
        self.frequency_points_spin.setRange(2, 1001)
        self.frequency_points_spin.setValue(4)
        self._add_field(self.excitation_card.main_layout, "Source Channel", self.source_channel_combo)
        self._add_field(self.excitation_card.main_layout, "DC Voltage (V)", self.dc_voltage_spin)
        self._add_field(
            self.excitation_card.main_layout, "AFG Amplitude (mVpp)", self.afg_amplitude_spin
        )
        self._add_field(
            self.excitation_card.main_layout, "Start Frequency (Hz)", self.start_frequency_spin
        )
        self._add_field(
            self.excitation_card.main_layout, "End Frequency (Hz)", self.end_frequency_spin
        )
        self._add_field(self.excitation_card.main_layout, "Points", self.frequency_points_spin)
        left.addWidget(self.excitation_card)

        self.acquisition_card = CardFrame("Acquisition & Limit")
        self.input_channel_combo = self._channel_combo()
        self.output_channel_combo = self._channel_combo(2)
        self.cycles_spin = self._double_spin(1.0, 20.0, 5.0, 1.0, 1)
        self.output_scale_spin = self._double_spin(0.01, 1000.0, 10.0, 1.0, 2)
        self.limit_spin = self._double_spin(-100.0, 200.0, 0.0, 1.0, 2)
        self.close_channel_check = QCheckBox("Turn off source channel after test")
        self._add_field(self.acquisition_card.main_layout, "Input Scope Channel", self.input_channel_combo)
        self._add_field(self.acquisition_card.main_layout, "Output Scope Channel", self.output_channel_combo)
        self._add_field(self.acquisition_card.main_layout, "Capture Cycles", self.cycles_spin)
        self._add_field(
            self.acquisition_card.main_layout, "Output Scale (mV/div)", self.output_scale_spin
        )
        self._add_field(
            self.acquisition_card.main_layout, "Minimum PSRR Limit (dB)", self.limit_spin
        )
        self.acquisition_card.main_layout.addWidget(self.close_channel_check)
        left.addWidget(self.acquisition_card)

        self.ap_card = CardFrame("Audio Precision")
        self.ap_project_edit = QLineEdit()
        self.ap_project_edit.setPlaceholderText("Optional APx project path")
        self.ap_signal_path_edit = QLineEdit("Signal Path1")
        self.ap_measurement_edit = QLineEdit("PSRR")
        self.ap_start_frequency_spin = self._double_spin(0.1, 50e6, 100.0, 100.0, 3)
        self.ap_end_frequency_spin = self._double_spin(0.1, 50e6, 100000.0, 1000.0, 3)
        self.ap_frequency_points_spin = QSpinBox()
        self.ap_frequency_points_spin.setRange(2, 1001)
        self.ap_frequency_points_spin.setValue(4)
        self.ap_limit_spin = self._double_spin(-100.0, 200.0, 0.0, 1.0, 2)
        self._add_field(self.ap_card.main_layout, "Project Path", self.ap_project_edit)
        self._add_field(self.ap_card.main_layout, "Signal Path", self.ap_signal_path_edit)
        self._add_field(self.ap_card.main_layout, "Measurement", self.ap_measurement_edit)
        self._add_field(
            self.ap_card.main_layout, "Start Frequency (Hz)", self.ap_start_frequency_spin
        )
        self._add_field(
            self.ap_card.main_layout, "End Frequency (Hz)", self.ap_end_frequency_spin
        )
        self._add_field(self.ap_card.main_layout, "Points", self.ap_frequency_points_spin)
        self._add_field(
            self.ap_card.main_layout, "Minimum PSRR Limit (dB)", self.ap_limit_spin
        )
        left.addWidget(self.ap_card)

        self._config_widgets = [
            self.method_combo, self.source_channel_combo, self.dc_voltage_spin,
            self.afg_amplitude_spin, self.start_frequency_spin, self.end_frequency_spin,
            self.frequency_points_spin, self.input_channel_combo, self.output_channel_combo,
            self.cycles_spin, self.output_scale_spin, self.limit_spin,
            self.close_channel_check, self.ap_project_edit, self.ap_signal_path_edit,
            self.ap_measurement_edit, self.ap_start_frequency_spin,
            self.ap_end_frequency_spin, self.ap_frequency_points_spin, self.ap_limit_spin,
        ]
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)

        button_row = QHBoxLayout()
        self.start_test_btn = QPushButton("START TEST")
        self.start_test_btn.setObjectName("startTestBtn")
        self.stop_test_btn = QPushButton("STOP")
        self.stop_test_btn.setObjectName("stopTestBtn")
        self.stop_test_btn.setEnabled(False)
        button_row.addWidget(self.start_test_btn, 1)
        button_row.addWidget(self.stop_test_btn)
        left.addLayout(button_row)
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(0)
        content.addLayout(right, 1)
        result_container = QFrame()
        result_container.setObjectName("resultContainer")
        result_layout = QVBoxLayout(result_container)
        result_layout.setContentsMargins(12, 12, 12, 12)
        result_layout.setSpacing(10)

        status_row = QHBoxLayout()
        result_title = QLabel("MEASUREMENT RESULT")
        result_title.setObjectName("cardTitle")
        self.result_status_label = QLabel("WAITING")
        self.result_status_label.setObjectName("statusOk")
        status_row.addWidget(result_title)
        status_row.addStretch()
        status_row.addWidget(self.result_status_label)
        result_layout.addLayout(status_row)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.metric_values = {}
        for key, caption in (
            ("min", "Minimum PSRR (dB)"),
            ("avg", "Average PSRR (dB)"),
            ("freq", "Worst Frequency (Hz)"),
            ("pass", "Limit Result"),
        ):
            box, value = self._metric_box(caption)
            self.metric_values[key] = value
            metrics.addWidget(box, 1)
        result_layout.addLayout(metrics)

        plot_panel = QFrame()
        plot_panel.setObjectName("plotPanel")
        plot_layout = QVBoxLayout(plot_panel)
        plot_layout.setContentsMargins(8, 8, 8, 8)
        plot_header = QHBoxLayout()
        plot_title = QLabel("PSRR vs Frequency")
        plot_title.setObjectName("cardTitle")
        plot_header.addWidget(plot_title)
        plot_header.addStretch()
        plot_layout.addLayout(plot_header)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#020b22")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.18)
        self.plot_widget.setLogMode(x=True, y=False)
        self.plot_widget.setLabel("bottom", "Frequency (Hz)")
        self.plot_widget.setLabel("left", "PSRR (dB)")
        for axis_name in ("left", "bottom"):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setPen(pg.mkPen("#6e88b6"))
            axis.setTextPen(pg.mkPen("#9bb6e8"))
        self.psrr_curve = self.plot_widget.plot(
            [], [], pen=pg.mkPen("#19d9c0", width=2),
            symbol="o", symbolSize=7, symbolBrush="#19d9c0", symbolPen="#b8fff2",
        )
        self.limit_line = pg.InfiniteLine(
            angle=0, movable=False, pen=pg.mkPen("#ffb84d", width=1, style=Qt.DashLine)
        )
        self.plot_widget.addItem(self.limit_line)
        plot_layout.addWidget(self.plot_widget, 1)
        result_layout.addWidget(plot_panel, 1)

        self.result_summary_label = QLabel("Configure the sweep and start a test to view PSRR results.")
        self.result_summary_label.setObjectName("resultSummary")
        self.result_summary_label.setWordWrap(True)
        result_layout.addWidget(self.result_summary_label)

        self.execution_splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            result_container, show_progress=True, stretch=(4, 1)
        )
        right.addWidget(self.execution_splitter)
        self._on_method_changed()

    @staticmethod
    def _channel_combo(default: int = 1) -> QComboBox:
        combo = QComboBox()
        for channel in range(1, 5):
            combo.addItem(f"CH {channel}", channel)
        combo.setCurrentIndex(default - 1)
        return combo

    @staticmethod
    def _double_spin(minimum: float, maximum: float, value: float,
                     step: float, decimals: int) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setKeyboardTracking(False)
        return spin

    @staticmethod
    def _add_field(layout: QVBoxLayout, text: str, widget: QWidget):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        layout.addWidget(label)
        layout.addWidget(widget)

    @staticmethod
    def _metric_box(caption: str):
        box = QFrame()
        box.setProperty("role", "resultBox")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        value = QLabel("---")
        value.setProperty("role", "resultValue")
        caption_label = QLabel(caption)
        caption_label.setProperty("role", "resultCaption")
        layout.addWidget(value)
        layout.addWidget(caption_label)
        return box, value

    def _sync_scope_from_top(self):
        self.sync_oscilloscope_from_top()

    def _on_method_changed(self):
        is_j2120a = self.method_combo.currentData() == "mso64b_j2120a"
        for card in (
            self.n6705c_card, self.scope_card, self.excitation_card, self.acquisition_card
        ):
            card.setVisible(is_j2120a)
        self.ap_card.setVisible(not is_j2120a)
        self.limit_line.setValue(self._current_limit_db())

    def _current_limit_db(self) -> float:
        if self.method_combo.currentData() == "audio_precision":
            return self.ap_limit_spin.value()
        return self.limit_spin.value()

    def get_test_config(self) -> dict:
        return {
            "measurement_method": self.method_combo.currentData(),
            "source_channel": self.source_channel_combo.currentData(),
            "input_channel": self.input_channel_combo.currentData(),
            "output_channel": self.output_channel_combo.currentData(),
            "dc_voltage": self.dc_voltage_spin.value(),
            "afg_amplitude_mvpp": self.afg_amplitude_spin.value(),
            "start_frequency_hz": self.start_frequency_spin.value(),
            "end_frequency_hz": self.end_frequency_spin.value(),
            "frequency_points": self.frequency_points_spin.value(),
            "frequencies_hz": list(self._frequencies_from_controls()),
            "cycles": self.cycles_spin.value(),
            "output_scale_mv": self.output_scale_spin.value(),
            "limit_db": self.limit_spin.value(),
            "close_channel_after": self.close_channel_check.isChecked(),
            "ap_project_path": self.ap_project_edit.text().strip(),
            "ap_signal_path": self.ap_signal_path_edit.text().strip(),
            "ap_measurement": self.ap_measurement_edit.text().strip(),
            "ap_start_frequency_hz": self.ap_start_frequency_spin.value(),
            "ap_end_frequency_hz": self.ap_end_frequency_spin.value(),
            "ap_frequency_points": self.ap_frequency_points_spin.value(),
            "ap_frequencies_hz": list(self._frequencies_from_controls(audio_precision=True)),
            "ap_limit_db": self.ap_limit_spin.value(),
        }

    def _frequencies_from_controls(self, audio_precision: bool = False):
        from core.pmu_test.psrr import generate_frequency_points
        prefix = "ap_" if audio_precision else ""
        return generate_frequency_points(
            getattr(self, f"{prefix}start_frequency_spin").value(),
            getattr(self, f"{prefix}end_frequency_spin").value(),
            getattr(self, f"{prefix}frequency_points_spin").value(),
        )

    def _validated_config(self):
        config = self.get_test_config()
        if config["measurement_method"] == "audio_precision":
            return audio_precision_config_from_dict(config)
        return config_from_dict(config)

    def _toggle_test(self):
        if self.is_test_running:
            self.stop_test()
        else:
            self.start_test()

    def start_test(self):
        if self.is_test_running:
            return
        try:
            config = self._validated_config()
        except (TypeError, ValueError) as exc:
            self.set_system_status(str(exc), True)
            self.append_log(f"[ERROR] 配置校验失败：{exc}")
            return
        is_audio_precision = self.method_combo.currentData() == "audio_precision"
        if not is_audio_precision:
            if not DEBUG_MOCK and (not self.is_connected or self.n6705c is None):
                self.set_system_status("请先连接 N6705C", True)
                return
            if not DEBUG_MOCK and (not self.scope_connected or self.get_scope_instance() is None):
                self.set_system_status("请先连接 MSO64B", True)
                return
            if self.n6705c is None or self.get_scope_instance() is None:
                self.set_system_status("请先在两个连接面板中连接仪器", True)
                return

        self.clear_results()
        self.is_test_running = True
        self._set_test_running(True)
        self.set_system_status("PSRR 测试进行中")
        self.append_log(f"[INFO] 启动 {self.method_combo.currentText()} PSRR 测试")

        self.test_thread = QThread(self)
        if is_audio_precision:
            self.test_worker = AudioPrecisionPSRRWorker(config)
        else:
            self.test_worker = PSRRTestWorker(
                config,
                n6705c=self.n6705c,
                oscilloscope=self.get_scope_instance(),
                mock_mode=DEBUG_MOCK,
            )
        self.test_worker.moveToThread(self.test_thread)
        self.test_thread.started.connect(self.test_worker.start)
        self.test_worker.log.connect(self.append_log)
        self.test_worker.progress.connect(self.execution_logs.set_progress)
        self.test_worker.point_ready.connect(self._on_point_ready)
        self.test_worker.result_ready.connect(self._on_result_ready)
        self.test_worker.finished.connect(self._on_test_finished)
        self.test_worker.finished.connect(self.test_thread.quit)
        self.test_thread.finished.connect(self.test_worker.deleteLater)
        self.test_thread.finished.connect(self.test_thread.deleteLater)
        self.test_thread.finished.connect(self._cleanup_test_thread)
        self.test_thread.start()
        logger.info("启动 PSRR 测试，配置: %s", self.get_test_config())

    def stop_test(self):
        if not self.is_test_running:
            return
        self.set_system_status("正在停止 PSRR 测试...", True)
        self.append_log("[WARN] 请求停止测试")
        if self.test_worker is not None:
            self.test_worker.stop()
        self.stop_test_btn.setEnabled(False)

    def _set_test_running(self, running: bool):
        self.start_test_btn.setText("STOP TEST" if running else "START TEST")
        self.start_test_btn.setProperty("running", running)
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.stop_test_btn.setEnabled(running)
        for widget in self._config_widgets:
            widget.setEnabled(not running)

    def _on_point_ready(self, point: dict):
        self._points.append(dict(point))
        self._update_plot()
        self.result_status_label.setText("RUNNING")

    def _on_result_ready(self, result: dict):
        self._last_result = result
        summary = result.get("summary", {})
        if not summary.get("point_count"):
            return
        self.metric_values["min"].setText(f"{summary['min_psrr_db']:.2f}")
        self.metric_values["avg"].setText(f"{summary['average_psrr_db']:.2f}")
        self.metric_values["freq"].setText(f"{summary['min_frequency_hz']:g}")
        passed = summary.get("passed")
        self.metric_values["pass"].setText("PASS" if passed else "FAIL")
        self.metric_values["pass"].setStyleSheet(
            f"color: {'#19f5c8' if passed else '#ff6f96'};"
        )
        result_config = result.get("config", {})
        limit_db = result_config.get("limit_db", result_config.get("ap_limit_db", 0.0))
        self.result_summary_label.setText(
            f"{summary['point_count']} points | Minimum {summary['min_psrr_db']:.2f} dB at "
            f"{summary['min_frequency_hz']:g} Hz | Limit {limit_db:.2f} dB"
        )

    def _on_test_finished(self, success: bool, message: str):
        self.is_test_running = False
        self._set_test_running(False)
        self.result_status_label.setText("DONE" if success else "STOPPED")
        self.set_system_status(message, not success)
        self.append_log(f"[{'RESULT' if success else 'WARN'}] {message}")
        self.sequence_execution_finished.emit(success, message)

    def _cleanup_test_thread(self):
        self.test_thread = None
        self.test_worker = None

    def _update_plot(self):
        ordered = sorted(self._points, key=lambda point: point["frequency_hz"])
        self.psrr_curve.setData(
            [point["frequency_hz"] for point in ordered],
            [point["psrr_db"] for point in ordered],
        )
        self.limit_line.setValue(self._current_limit_db())

    def clear_results(self):
        self._points.clear()
        self._last_result = None
        self.psrr_curve.setData([], [])
        self.limit_line.setValue(self._current_limit_db())
        for value in self.metric_values.values():
            value.setText("---")
        self.metric_values["pass"].setStyleSheet("")
        self.result_status_label.setText("WAITING")
        self.result_summary_label.setText("Configure the sweep and start a test to view PSRR results.")
        self.execution_logs.set_progress(0)

    def update_test_result(self, result: dict):
        if isinstance(result, dict) and "summary" in result:
            self._on_result_ready(result)

    def append_log(self, message: str):
        self.execution_logs.append_log(message)

    def set_system_status(self, status: str, is_error: bool = False):
        if not hasattr(self, "system_status_label"):
            return
        self.system_status_label.setText(status)
        self.system_status_label.setObjectName("statusErr" if is_error else "statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)

    def update_instrument_info(self, instrument_info):
        if self.is_connected:
            self.set_system_status("N6705C Connected")

    def get_test_mode(self):
        return self._test_mode

    def set_test_mode(self, mode: str):
        self._test_mode = mode

    def get_test_id(self):
        return self._test_id

    def set_test_id(self, test_id: str):
        self._test_id = test_id

    def cleanup(self):
        self.stop_test()

    def ai_capabilities(self) -> set[str]:
        return {CAP_GET_CONFIG, CAP_APPLY_CONFIG, CAP_START_TEST, CAP_STOP_TEST, CAP_GET_RESULT}

    def ai_get_config(self) -> dict[str, Any] | None:
        try:
            return self.get_test_config()
        except (TypeError, ValueError):
            logger.error("AI 读取 PSRR 配置失败", exc_info=True)
            return None

    def ai_apply_config(self, payload: Any) -> tuple[bool, str]:
        if self.is_test_running:
            return False, "测试运行中，无法修改配置，请先停止测试。"
        return self.apply_config_to_controls(payload if isinstance(payload, dict) else {})

    def ai_start_test(self) -> tuple[bool, str]:
        if self.is_test_running:
            return False, "PSRR 测试已在运行中。"
        try:
            self._validated_config()
        except (TypeError, ValueError) as exc:
            return False, f"配置校验失败：{exc}"
        self.append_log("[AI] 请求启动 PSRR 测试")
        self.start_test()
        if self.is_test_running:
            return True, "已启动 PSRR 扫频测试。"
        return False, "启动未成功，请检查仪器连接与执行日志。"

    def ai_stop_test(self) -> tuple[bool, str]:
        if not self.is_test_running:
            return False, "当前未在运行 PSRR 测试。"
        self.append_log("[AI] 请求停止 PSRR 测试")
        self.stop_test()
        return True, "已发送停止请求。"

    def ai_get_result_summary(self) -> dict[str, Any] | None:
        if self._last_result is None:
            return {"available": False, "running": self.is_test_running}
        return {
            "available": True,
            "running": self.is_test_running,
            "success": self._last_result.get("success"),
            "mock_mode": self._last_result.get("mock_mode"),
            **self._last_result.get("summary", {}),
        }

    def apply_config_to_controls(self, cfg: dict, silent: bool = False) -> tuple[bool, str]:
        if not isinstance(cfg, dict):
            return False, "配置草案格式无效（期望 dict）。"
        if threading.current_thread() is not threading.main_thread():
            logger.error("PSRR 配置在非主线程回填，已拒绝")
            return False, "配置回填未在主线程执行，已拒绝。"

        applied: list[str] = []
        touched: list[QWidget] = []

        def set_combo(combo: QComboBox, key: str):
            if key not in cfg:
                return
            index = combo.findData(int(cfg[key]))
            if index >= 0:
                combo.setCurrentIndex(index)
                applied.append(key)
                touched.append(combo)

        def set_spin(spin: QDoubleSpinBox | QSpinBox, key: str):
            if key not in cfg:
                return
            value = int(cfg[key]) if isinstance(spin, QSpinBox) else float(cfg[key])
            spin.setValue(value)
            applied.append(key)
            touched.append(spin)

        def set_line(edit: QLineEdit, key: str):
            if key not in cfg:
                return
            edit.setText(str(cfg[key]))
            applied.append(key)
            touched.append(edit)

        def set_legacy_frequencies(start_spin, end_spin, points_spin, key: str):
            if key not in cfg:
                return
            from core.pmu_test.psrr import parse_frequency_points
            frequencies = parse_frequency_points(cfg[key])
            if len(frequencies) < 2:
                raise ValueError("旧频率列表至少需要两个频点才能转换为起止频率和点数")
            start_spin.setValue(frequencies[0])
            end_spin.setValue(frequencies[-1])
            points_spin.setValue(len(frequencies))
            applied.append(key)
            touched.extend((start_spin, end_spin, points_spin))

        if "measurement_method" in cfg:
            index = self.method_combo.findData(str(cfg["measurement_method"]))
            if index >= 0:
                self.method_combo.setCurrentIndex(index)
                applied.append("measurement_method")
                touched.append(self.method_combo)
        set_combo(self.source_channel_combo, "source_channel")
        set_combo(self.input_channel_combo, "input_channel")
        set_combo(self.output_channel_combo, "output_channel")
        for spin, key in (
            (self.dc_voltage_spin, "dc_voltage"),
            (self.cycles_spin, "cycles"),
            (self.output_scale_spin, "output_scale_mv"),
            (self.limit_spin, "limit_db"),
            (self.start_frequency_spin, "start_frequency_hz"),
            (self.end_frequency_spin, "end_frequency_hz"),
            (self.frequency_points_spin, "frequency_points"),
            (self.ap_start_frequency_spin, "ap_start_frequency_hz"),
            (self.ap_end_frequency_spin, "ap_end_frequency_hz"),
            (self.ap_frequency_points_spin, "ap_frequency_points"),
            (self.ap_limit_spin, "ap_limit_db"),
        ):
            set_spin(spin, key)
        if "afg_amplitude_mvpp" in cfg:
            set_spin(self.afg_amplitude_spin, "afg_amplitude_mvpp")
        elif "ripple_mv_rms" in cfg:
            self.afg_amplitude_spin.setValue(
                float(cfg["ripple_mv_rms"]) * 2.0 * math.sqrt(2.0)
            )
            applied.append("afg_amplitude_mvpp")
            touched.append(self.afg_amplitude_spin)
        set_legacy_frequencies(
            self.start_frequency_spin, self.end_frequency_spin,
            self.frequency_points_spin, "frequencies_hz"
        )
        set_legacy_frequencies(
            self.ap_start_frequency_spin, self.ap_end_frequency_spin,
            self.ap_frequency_points_spin, "ap_frequencies_hz"
        )
        set_line(self.ap_project_edit, "ap_project_path")
        set_line(self.ap_signal_path_edit, "ap_signal_path")
        set_line(self.ap_measurement_edit, "ap_measurement")
        if "close_channel_after" in cfg:
            self.close_channel_check.setChecked(bool(cfg["close_channel_after"]))
            applied.append("close_channel_after")
            touched.append(self.close_channel_check)
        if not applied:
            return False, "配置草案未包含任何可识别的 PSRR 配置项。"
        self._on_method_changed()
        self._update_plot()
        if not silent:
            self._highlight_widgets(touched)
            self.append_log(f"[AI] 已应用配置：{', '.join(applied)}")
        return True, f"已应用配置项：{', '.join(applied)}。"

    @staticmethod
    def _highlight_widgets(widgets: list[QWidget]):
        for widget in widgets:
            widget.setProperty("aiHighlighted", True)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

            def clear(w=widget):
                w.setProperty("aiHighlighted", False)
                w.style().unpolish(w)
                w.style().polish(w)

            QTimer.singleShot(1500, clear)
