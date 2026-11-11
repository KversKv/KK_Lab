#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PMU PSRR 扫频测试页面。"""
from __future__ import annotations

import copy
import datetime
import math
import os
import threading
from typing import Any

import pyqtgraph as pg
from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
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
    AUDIO_PRECISION_FFT_LENGTHS,
    AUDIO_PRECISION_FFT_WINDOWS,
    AudioPrecisionConnectionWorker,
    AudioPrecisionOutputWorker,
    AudioPrecisionPSRRWorker,
    PSRRTestWorker,
    audio_precision_config_from_dict,
    config_from_dict,
)
from debug_config import DEBUG_MOCK
from log_config import get_logger
from resource_path import get_resource_base
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.oscilloscope_module_frame import OscilloscopeConnectionMixin
from ui.widgets.config_memory import ConfigMemory
from ui.widgets.button import update_connect_button_state
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

    RECENT_TEST_LIMIT = 10
    _COMPARE_PALETTE = [
        "#19d9c0", "#f0a040", "#5b9cf5", "#e05c5c",
        "#a78bfa", "#34d399", "#fb923c", "#60a5fa",
    ]

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
        self._ap_connection_widgets: list[QWidget] = []
        self.audio_precision = None
        self.ap_ssh_session = None
        self.ap_connected = False
        self._ap_connection_busy = False
        self._ap_connection_operation = ""
        self._ap_connection_thread = None
        self._ap_connection_worker = None
        self._ap_output_busy = False
        self._ap_output_operation = ""
        self._ap_output_on = False
        self._ap_output_thread = None
        self._ap_output_worker = None
        self._recent_test_records: list[dict] = []
        self._recent_test_seq = 0
        self._loaded_record = None
        self._comparison_records: list[dict] = []
        self._comparison_curves = []
        self._comparison_limit_lines = []
        self._recent_panel_sizes = [1200, 280]
        self._highlight_record_id = None

        self._setup_style()
        self._create_layout()
        self.bind_n6705c_signals()
        self.bind_oscilloscope_signals()
        self.start_test_btn.clicked.connect(self._toggle_test)
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
        icons_dir = os.path.join(get_resource_base(), "resources", "icons")
        checkbox_checked = os.path.join(icons_dir, "checked_4f46e5.svg").replace("\\", "/")
        checkbox_unchecked = os.path.join(icons_dir, "unchecked_4f46e5.svg").replace("\\", "/")
        page_qss = ("""
            QWidget { background-color: #050b1a; color: #e8eefc; }
            QWidget#leftPanelInner { background-color: transparent; }
            QFrame#apSshFrame, QFrame#apConnectionContent {
                background-color: transparent; border: none;
            }
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
            QPushButton#apOutputToggleBtn {
                min-height: 33px; max-height: 33px; padding: 0px 12px;
                background-color: #07463f; border: 1px solid #10bfa0; color: #72f4d7;
            }
            QPushButton#apOutputToggleBtn[outputOn="true"] {
                background-color: #4a1730; border: 1px solid #d84578; color: #ff9abb;
            }
            QPushButton#apConnectionToggleBtn {
                min-height: 20px; max-height: 20px; padding: 0px;
                background-color: transparent; border: none; color: #8fa7d6;
            }
            QPushButton#apConnectionToggleBtn:hover {
                background-color: #1a2748; color: #f4f7ff;
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
            QCheckBox#includeEndpointsCheckbox {
                background-color: transparent;
                border: none;
            }
            QCheckBox#includeEndpointsCheckbox::indicator {
                width: 16px;
                height: 16px;
                image: url("__UNCHECKED__");
            }
            QCheckBox#includeEndpointsCheckbox::indicator:checked {
                image: url("__CHECKED__");
            }
            QFrame#recentPanel {
                background-color: #0d1833; border: 1px solid #1a2a52; border-radius: 12px;
            }
            QPushButton#recentToolBtn {
                min-height: 20px; max-height: 20px; padding: 0px 7px;
                border-radius: 6px; background-color: #1a2748; color: #dce8ff;
            }
            QPushButton#recentToolBtn:checked {
                background-color: #1a3260; border: 1px solid #5b9cf5;
            }
            QListWidget#recentTestList {
                background-color: #020b22; color: #b7c8ea; border: 1px solid #1a2d57;
                border-radius: 8px; padding: 4px; outline: none;
            }
            QListWidget#recentTestList::item {
                background: transparent; border: none; border-radius: 4px; padding: 5px 4px;
            }
            QListWidget#recentTestList::item:hover { background-color: #122448; }
            QListWidget#recentTestList::item:selected { background-color: #1a3260; }
            QLabel#recentHint { color: #7d94c5; font-size: 10px; }
            QSplitter#recentCurveSplitter::handle { background-color: transparent; }
            QSplitter#recentCurveSplitter::handle:horizontal { width: 3px; }
            QSplitter#recentCurveSplitter::handle:horizontal:hover { background-color: #1a2d57; }
            QSplitter#recentCurveSplitter::handle:horizontal:pressed { background-color: #5b9cf5; }
        """).replace("__UNCHECKED__", checkbox_unchecked).replace("__CHECKED__", checkbox_checked)
        self.setStyleSheet(page_qss + SCROLLBAR_STYLE)

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

        self.n6705c_card = CardFrame("Power Supply Connection")
        self.register_power_title_card(
            self.n6705c_card, default_title="Power Supply Connection",
            connected_fmt="{model} Connection",
        )
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
        self.register_power_channel_combo(
            self.source_channel_combo, text_fmt="CH {}", with_data=True
        )
        self.dc_voltage_spin = self._double_spin(0.1, 20.0, 5.0, 0.1, 3)
        self.afg_amplitude_spin = self._double_spin(0.1, 2000.0, 100.0, 10.0, 2)
        self.start_frequency_spin = self._double_spin(0.1, 50e6, 100.0, 100.0, 3)
        self.end_frequency_spin = self._double_spin(0.1, 50e6, 100000.0, 1000.0, 3)
        self.frequency_points_spin = QSpinBox()
        self.frequency_points_spin.setRange(2, 1001)
        self.frequency_points_spin.setValue(4)
        include_endpoints_label = QLabel("Include Start/End Points")
        include_endpoints_label.setObjectName("fieldLabel")
        include_endpoints_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.include_endpoints_check = QCheckBox()
        self.include_endpoints_check.setObjectName("includeEndpointsCheckbox")
        self.include_endpoints_check.setFixedSize(22, 22)
        self.include_endpoints_check.setCursor(Qt.PointingHandCursor)
        self.include_endpoints_check.setChecked(True)
        include_endpoints_row = QHBoxLayout()
        include_endpoints_row.setContentsMargins(0, 0, 0, 0)
        include_endpoints_row.setSpacing(8)
        include_endpoints_row.addWidget(include_endpoints_label)
        include_endpoints_row.addStretch()
        include_endpoints_row.addWidget(self.include_endpoints_check)
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
        self.excitation_card.main_layout.addLayout(include_endpoints_row)
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

        self.ap_connection_card = CardFrame("Audio Precision Connection")
        self.ap_status_label = QLabel("● Ready")
        self.ap_status_label.setObjectName("statusOk")
        self.ap_connection_card.title_row.addWidget(self.ap_status_label)
        self.ap_connection_toggle_btn = QPushButton("▼")
        self.ap_connection_toggle_btn.setObjectName("apConnectionToggleBtn")
        self.ap_connection_toggle_btn.setFixedWidth(24)
        self.ap_connection_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.ap_connection_toggle_btn.setToolTip("Collapse")
        self.ap_connection_card.title_row.addWidget(self.ap_connection_toggle_btn)
        self.ap_connection_content = QFrame()
        self.ap_connection_content.setObjectName("apConnectionContent")
        ap_connection_layout = QVBoxLayout(self.ap_connection_content)
        ap_connection_layout.setContentsMargins(0, 0, 0, 0)
        ap_connection_layout.setSpacing(8)
        self.ap_connection_combo = QComboBox()
        self.ap_connection_combo.addItem("Virtual Machine SSH", "vm_ssh")
        self.ap_connection_combo.addItem("Local AP Direct", "local")
        self._add_field(ap_connection_layout, "Connection", self.ap_connection_combo)
        self.ap_ssh_frame = QFrame()
        self.ap_ssh_frame.setObjectName("apSshFrame")
        ap_ssh_layout = QVBoxLayout(self.ap_ssh_frame)
        ap_ssh_layout.setContentsMargins(0, 0, 0, 0)
        ap_ssh_layout.setSpacing(6)
        self.ap_ssh_profile_edit = QLineEdit("testvm")
        self.ap_ssh_profile_edit.setPlaceholderText("Preferred SSH profile from ~/.ssh/config")
        self.ap_ssh_host_edit = QLineEdit("192.168.208.128")
        self.ap_ssh_user_edit = QLineEdit("administrator")
        self.ap_ssh_port_spin = QSpinBox()
        self.ap_ssh_port_spin.setRange(1, 65535)
        self.ap_ssh_port_spin.setValue(22)
        self.ap_ssh_python_edit = QLineEdit("py -3.12")
        self._add_field(ap_ssh_layout, "SSH Profile (preferred)", self.ap_ssh_profile_edit)
        self._add_field(ap_ssh_layout, "Guest IP (fallback)", self.ap_ssh_host_edit)
        self._add_field(ap_ssh_layout, "SSH User", self.ap_ssh_user_edit)
        self._add_field(ap_ssh_layout, "SSH Port (IP fallback)", self.ap_ssh_port_spin)
        self._add_field(ap_ssh_layout, "Guest Python Command", self.ap_ssh_python_edit)
        ap_connection_layout.addWidget(self.ap_ssh_frame)
        self.ap_connection_card.main_layout.addWidget(self.ap_connection_content)
        self.ap_connect_btn = QPushButton()
        update_connect_button_state(self.ap_connect_btn, connected=False)
        self.ap_connection_card.main_layout.addWidget(self.ap_connect_btn)
        left.addWidget(self.ap_connection_card)

        self.ap_output_card = CardFrame("Audio Precision OUTPUT")
        self.ap_output_status_label = QLabel("OFF")
        self.ap_output_status_label.setObjectName("statusErr")
        self.ap_output_card.title_row.addWidget(self.ap_output_status_label)
        self.ap_output_channel_combo = QComboBox()
        self.ap_output_channel_combo.addItem("CH 1", 1)
        self.ap_output_channel_combo.addItem("CH 2", 2)
        self.ap_amplitude_spin = self._double_spin(0.1, 1000.0, 100.0, 10.0, 2)
        self.ap_offset_spin = self._double_spin(0.1, 20.0, 3.8, 0.1, 3)
        self._add_field(
            self.ap_output_card.main_layout, "Output Channel", self.ap_output_channel_combo
        )
        self._add_field(
            self.ap_output_card.main_layout, "Output Amplitude (mVrms)", self.ap_amplitude_spin
        )
        self._add_field(self.ap_output_card.main_layout, "DC Offset (V)", self.ap_offset_spin)
        self.ap_output_toggle_btn = QPushButton("TURN OUTPUT ON")
        self.ap_output_toggle_btn.setObjectName("apOutputToggleBtn")
        self.ap_output_card.main_layout.addWidget(self.ap_output_toggle_btn)
        left.addWidget(self.ap_output_card)

        self.ap_card = CardFrame("Audio Precision Test Parameters")
        self.ap_vin_input_channel_combo = self._ap_input_channel_combo()
        self.ap_vout_input_channel_combo = self._ap_input_channel_combo(2)
        self.ap_start_frequency_spin = self._double_spin(0.1, 1e6, 100.0, 100.0, 3)
        self.ap_end_frequency_spin = self._double_spin(0.1, 1e6, 100000.0, 1000.0, 3)
        self.ap_frequency_points_spin = QSpinBox()
        self.ap_frequency_points_spin.setRange(2, 1001)
        self.ap_frequency_points_spin.setValue(4)
        ap_include_endpoints_label = QLabel("Include Start/End Points")
        ap_include_endpoints_label.setObjectName("fieldLabel")
        ap_include_endpoints_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.ap_include_endpoints_check = QCheckBox()
        self.ap_include_endpoints_check.setObjectName("includeEndpointsCheckbox")
        self.ap_include_endpoints_check.setFixedSize(22, 22)
        self.ap_include_endpoints_check.setCursor(Qt.PointingHandCursor)
        self.ap_include_endpoints_check.setChecked(True)
        ap_include_endpoints_row = QHBoxLayout()
        ap_include_endpoints_row.setContentsMargins(0, 0, 0, 0)
        ap_include_endpoints_row.setSpacing(8)
        ap_include_endpoints_row.addWidget(ap_include_endpoints_label)
        ap_include_endpoints_row.addStretch()
        ap_include_endpoints_row.addWidget(self.ap_include_endpoints_check)
        self.ap_fft_length_combo = QComboBox()
        for length in AUDIO_PRECISION_FFT_LENGTHS:
            if length < 1000:
                label = str(length)
            elif length % 1000 == 0:
                label = f"{length // 1000}k"
            else:
                label = f"{length // 1024}k"
            self.ap_fft_length_combo.addItem(label, length)
        self.ap_fft_length_combo.setCurrentIndex(
            self.ap_fft_length_combo.findData(48000)
        )
        self.ap_fft_window_combo = QComboBox()
        for window in AUDIO_PRECISION_FFT_WINDOWS:
            self.ap_fft_window_combo.addItem(window, window)
        self.ap_fft_averages_spin = QSpinBox()
        self.ap_fft_averages_spin.setRange(1, 100)
        self.ap_fft_averages_spin.setValue(5)
        self.ap_limit_spin = self._double_spin(-100.0, 200.0, 0.0, 1.0, 2)
        self._add_field(
            self.ap_card.main_layout, "VIN Input Channel", self.ap_vin_input_channel_combo
        )
        self._add_field(
            self.ap_card.main_layout, "VOUT Input Channel", self.ap_vout_input_channel_combo
        )
        self._add_field(
            self.ap_card.main_layout, "Start Frequency (Hz)", self.ap_start_frequency_spin
        )
        self._add_field(
            self.ap_card.main_layout, "End Frequency (Hz)", self.ap_end_frequency_spin
        )
        self._add_field(self.ap_card.main_layout, "Points", self.ap_frequency_points_spin)
        self.ap_card.main_layout.addLayout(ap_include_endpoints_row)
        self._add_field(self.ap_card.main_layout, "FFT Length", self.ap_fft_length_combo)
        self._add_field(self.ap_card.main_layout, "FFT Window", self.ap_fft_window_combo)
        self._add_field(self.ap_card.main_layout, "Averages", self.ap_fft_averages_spin)
        self._add_field(
            self.ap_card.main_layout, "Minimum PSRR Limit (dB)", self.ap_limit_spin
        )
        left.addWidget(self.ap_card)

        self._config_widgets = [
            self.method_combo, self.source_channel_combo, self.dc_voltage_spin,
            self.afg_amplitude_spin, self.start_frequency_spin, self.end_frequency_spin,
            self.frequency_points_spin, self.include_endpoints_check,
            self.input_channel_combo, self.output_channel_combo,
            self.cycles_spin, self.output_scale_spin, self.limit_spin,
            self.close_channel_check, self.ap_output_channel_combo, self.ap_amplitude_spin,
            self.ap_offset_spin, self.ap_vin_input_channel_combo,
            self.ap_vout_input_channel_combo, self.ap_start_frequency_spin,
            self.ap_end_frequency_spin, self.ap_frequency_points_spin,
            self.ap_include_endpoints_check, self.ap_fft_length_combo,
            self.ap_fft_window_combo, self.ap_fft_averages_spin, self.ap_limit_spin,
        ]
        self._ap_connection_widgets = [
            self.ap_connection_combo, self.ap_ssh_profile_edit, self.ap_ssh_host_edit,
            self.ap_ssh_user_edit, self.ap_ssh_port_spin, self.ap_ssh_python_edit,
        ]
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        for spin in (
            self.start_frequency_spin, self.end_frequency_spin,
            self.ap_start_frequency_spin, self.ap_end_frequency_spin,
        ):
            spin.valueChanged.connect(self._update_frequency_ticks)
        self.ap_connection_combo.currentIndexChanged.connect(self._on_ap_connection_changed)
        self.ap_connection_toggle_btn.clicked.connect(self._toggle_ap_connection_collapsed)
        self.ap_connect_btn.clicked.connect(self._on_ap_connect_or_disconnect)
        self.ap_output_toggle_btn.clicked.connect(self._on_ap_output_toggle)

        self.start_test_btn = QPushButton("START TEST")
        self.start_test_btn.setObjectName("startTestBtn")
        left.addWidget(self.start_test_btn)
        left.addStretch()

        right = QVBoxLayout()
        right.setSpacing(0)
        content.addLayout(right, 1)
        self.result_container = QFrame()
        self.result_container.setObjectName("resultContainer")
        result_layout = QVBoxLayout(self.result_container)
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
        self.toggle_recent_btn = QPushButton("Recent ▶")
        self.toggle_recent_btn.setObjectName("recentToolBtn")
        self.toggle_recent_btn.setCheckable(True)
        self.toggle_recent_btn.setToolTip("Show or hide recent test records")
        self.toggle_recent_btn.toggled.connect(self._on_toggle_recent_panel)
        plot_header.addWidget(self.toggle_recent_btn)
        plot_layout.addLayout(plot_header)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#020b22")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.18)
        self.plot_widget.setLogMode(x=True, y=False)
        self.plot_widget.setLabel("bottom", "Frequency (Hz)")
        self.plot_widget.setLabel("left", "PSRR (dB)")
        self.plot_widget.addLegend(offset=(10, 10))
        for axis_name in ("left", "bottom"):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setPen(pg.mkPen("#6e88b6"))
            axis.setTextPen(pg.mkPen("#9bb6e8"))
        self.psrr_curve = self.plot_widget.plot(
            [], [], pen=pg.mkPen("#19d9c0", width=2),
            symbol="o", symbolSize=7, symbolBrush="#19d9c0", symbolPen="#b8fff2",
            name="Current",
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
            self.result_container, show_progress=True, stretch=(4, 1)
        )
        self.recent_curve_splitter = QSplitter(Qt.Horizontal)
        self.recent_curve_splitter.setObjectName("recentCurveSplitter")
        self.recent_curve_splitter.addWidget(self.execution_splitter)
        self.recent_curve_splitter.addWidget(self._create_recent_tests_panel())
        self.recent_curve_splitter.setStretchFactor(0, 1)
        self.recent_curve_splitter.setStretchFactor(1, 0)
        self.recent_curve_splitter.setSizes(self._recent_panel_sizes)
        self.recent_curve_splitter.widget(1).setVisible(False)
        right.addWidget(self.recent_curve_splitter)
        self._on_method_changed()

    def get_capture_widget(self):
        return self.result_container

    @staticmethod
    def _channel_combo(default: int = 1) -> QComboBox:
        combo = QComboBox()
        for channel in range(1, 5):
            combo.addItem(f"CH {channel}", channel)
        combo.setCurrentIndex(default - 1)
        return combo

    @staticmethod
    def _ap_input_channel_combo(default: int = 1) -> QComboBox:
        combo = QComboBox()
        for channel in (1, 2):
            combo.addItem(f"INPUT {channel}", channel)
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

    def _create_recent_tests_panel(self):
        panel = QFrame()
        panel.setObjectName("recentPanel")
        panel.setMinimumWidth(260)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(5)
        title = QLabel("Recent Tests")
        title.setObjectName("cardTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.compare_recent_btn = QPushButton("Compare")
        self.load_recent_btn = QPushButton("Load")
        self.clear_recent_btn = QPushButton("Clear")
        for button, tooltip in (
            (self.compare_recent_btn, "Plot two or more checked records on the same chart"),
            (self.load_recent_btn, "Load the first checked record"),
            (self.clear_recent_btn, "Clear all recent test records"),
        ):
            button.setObjectName("recentToolBtn")
            button.setToolTip(tooltip)
            title_row.addWidget(button)
        layout.addLayout(title_row)

        self.recent_test_list = QListWidget()
        self.recent_test_list.setObjectName("recentTestList")
        self.recent_test_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.recent_test_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.recent_test_list.setToolTip(
            "Check records to compare; double-click to load; right-click for more actions"
        )
        layout.addWidget(self.recent_test_list, 1)
        hint = QLabel("Check 2+ records and click Compare. Double-click a record to load it.")
        hint.setObjectName("recentHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.compare_recent_btn.clicked.connect(self._on_compare_recent_tests)
        self.load_recent_btn.clicked.connect(self._on_load_recent_test)
        self.clear_recent_btn.clicked.connect(self._on_clear_recent_tests)
        self.recent_test_list.itemDoubleClicked.connect(self._on_recent_item_double_clicked)
        self.recent_test_list.itemSelectionChanged.connect(self._on_recent_selection_changed)
        self.recent_test_list.customContextMenuRequested.connect(self._show_recent_item_menu)
        return panel

    def _on_toggle_recent_panel(self, checked: bool):
        panel = self.recent_curve_splitter.widget(1)
        if checked:
            panel.setVisible(True)
            self.recent_curve_splitter.setSizes(self._recent_panel_sizes)
            self.toggle_recent_btn.setText("Recent ◀")
        else:
            self._recent_panel_sizes = self.recent_curve_splitter.sizes()
            panel.setVisible(False)
            self.toggle_recent_btn.setText("Recent ▶")

    def _record_color(self, record_id: int) -> str:
        return self._COMPARE_PALETTE[record_id % len(self._COMPARE_PALETTE)]

    @staticmethod
    def _record_display_name(record: dict) -> str:
        return record.get("label") or record["name"]

    @staticmethod
    def _result_limit_db(result: dict) -> float:
        config = result.get("config") or {}
        return float(config.get("limit_db", config.get("ap_limit_db", 0.0)))

    def _record_tooltip(self, record: dict) -> str:
        result = record["result"]
        summary = result.get("summary") or {}
        method = "Audio Precision" if record["method"] == "audio_precision" else "MSO64B + J2120A"
        return "\n".join((
            self._record_display_name(record),
            f"Time: {record['time'].strftime('%Y-%m-%d %H:%M:%S')}",
            f"Method: {method}",
            f"Points: {summary.get('point_count', 0)}",
            f"Minimum: {summary.get('min_psrr_db', 0.0):.2f} dB",
            f"Average: {summary.get('average_psrr_db', 0.0):.2f} dB",
            f"Worst Frequency: {summary.get('min_frequency_hz', 0.0):g} Hz",
            f"Limit: {self._result_limit_db(result):.2f} dB",
            f"Result: {'PASS' if summary.get('passed') else 'FAIL'}",
        ))

    def _record_recent_test(self, result: dict | None):
        if not result or not result.get("points"):
            return
        self._recent_test_seq += 1
        config = result.get("config") or {}
        summary = result.get("summary") or {}
        method = config.get("measurement_method", "mso64b_j2120a")
        record = {
            "id": self._recent_test_seq,
            "time": datetime.datetime.now(),
            "name": f"PSRR_{self._recent_test_seq:03d}",
            "label": "",
            "method": method,
            "result": copy.deepcopy(result),
        }
        self._recent_test_records.append(record)
        while len(self._recent_test_records) > self.RECENT_TEST_LIMIT:
            self._recent_test_records.pop(0)
        self._refresh_recent_test_list()
        self.append_log(
            f"[INFO] Saved recent test #{record['id']} {record['name']} "
            f"({summary.get('point_count', 0)} points)"
        )

    def _refresh_recent_test_list(self):
        checked_ids = set()
        for index in range(self.recent_test_list.count()):
            item = self.recent_test_list.item(index)
            record = item.data(Qt.UserRole)
            if item.checkState() == Qt.Checked and record is not None:
                checked_ids.add(record["id"])
        self.recent_test_list.blockSignals(True)
        self.recent_test_list.clear()
        for record in self._recent_test_records:
            summary = record["result"].get("summary") or {}
            method = "AP" if record["method"] == "audio_precision" else "MSO"
            text = (
                f"● #{record['id']} {self._record_display_name(record)} | {method} | "
                f"{record['time'].strftime('%m-%d %H:%M:%S')}\n"
                f"{summary.get('point_count', 0)} pts | Min "
                f"{summary.get('min_psrr_db', 0.0):.2f} dB | "
                f"{'PASS' if summary.get('passed') else 'FAIL'}"
            )
            item = QListWidgetItem(text)
            item.setForeground(QBrush(QColor(self._record_color(record["id"]))))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if record["id"] in checked_ids else Qt.Unchecked)
            item.setData(Qt.UserRole, record)
            item.setToolTip(self._record_tooltip(record))
            self.recent_test_list.addItem(item)
            if record["id"] == self._highlight_record_id:
                self.recent_test_list.setCurrentItem(item)
        self.recent_test_list.blockSignals(False)

    def _get_checked_records(self) -> list[dict]:
        records = []
        for index in range(self.recent_test_list.count()):
            item = self.recent_test_list.item(index)
            record = item.data(Qt.UserRole)
            if item.checkState() == Qt.Checked and record is not None:
                records.append(record)
        return records

    def _on_recent_selection_changed(self):
        items = self.recent_test_list.selectedItems()
        record = items[0].data(Qt.UserRole) if items else None
        self._highlight_record_id = record["id"] if record is not None else None
        checked = self._get_checked_records()
        if len(checked) >= 2:
            self._plot_comparison_curves(checked)

    def _on_compare_recent_tests(self):
        records = self._get_checked_records()
        if len(records) < 2:
            self.append_log("[WARN] Check at least two recent records to compare")
            return
        self._plot_comparison_curves(records)

    def _on_load_recent_test(self):
        records = self._get_checked_records()
        if not records:
            items = self.recent_test_list.selectedItems()
            records = [items[0].data(Qt.UserRole)] if items else []
        if not records:
            self.append_log("[WARN] Check or select one recent record to load")
            return
        if len(records) > 1:
            self.append_log("[WARN] Load supports one record; using the first checked record")
        self._load_recent_record(records[0])

    def _on_recent_item_double_clicked(self, item):
        record = item.data(Qt.UserRole)
        if record is not None:
            self._load_recent_record(record)

    def _load_recent_record(self, record: dict):
        result = copy.deepcopy(record["result"])
        self._comparison_records = []
        self._clear_comparison_items()
        self._loaded_record = record
        self._points = copy.deepcopy(result.get("points") or [])
        self._last_result = result
        self._update_plot(self._record_display_name(record))
        self._on_result_ready(result)
        self._update_frequency_ticks_for_points(self._points)
        self.result_status_label.setText("LOADED")
        self.append_log(f"[INFO] Loaded recent record #{record['id']} {self._record_display_name(record)}")

    def _show_recent_item_menu(self, pos):
        item = self.recent_test_list.itemAt(pos)
        menu = QMenu(self)
        if item is not None:
            record = item.data(Qt.UserRole)
            rename_action = QAction("Rename...", menu)
            rename_action.triggered.connect(lambda: self._rename_recent_record(record))
            menu.addAction(rename_action)
            load_action = QAction("Load Curve", menu)
            load_action.triggered.connect(lambda: self._load_recent_record(record))
            menu.addAction(load_action)
            check_action = QAction(
                "Uncheck" if item.checkState() == Qt.Checked else "Check for Compare", menu
            )
            check_action.triggered.connect(
                lambda: item.setCheckState(
                    Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                )
            )
            menu.addAction(check_action)
            menu.addSeparator()
            remove_action = QAction("Remove", menu)
            remove_action.triggered.connect(lambda: self._delete_recent_record(record))
            menu.addAction(remove_action)
            menu.addSeparator()
        clear_action = QAction("Clear All", menu)
        clear_action.triggered.connect(self._on_clear_recent_tests)
        menu.addAction(clear_action)
        menu.exec(self.recent_test_list.mapToGlobal(pos))

    def _rename_recent_record(self, record: dict):
        text, accepted = QInputDialog.getText(
            self, "Rename Recent Test", "Display name:",
            text=self._record_display_name(record),
        )
        if not accepted:
            return
        record["label"] = text.strip()
        self._refresh_recent_test_list()
        if record in self._comparison_records:
            self._plot_comparison_curves(self._comparison_records)
        elif self._loaded_record is record:
            self._update_plot(self._record_display_name(record))
        self.append_log(f"[INFO] Renamed recent record #{record['id']}")

    def _delete_recent_record(self, record: dict):
        try:
            self._recent_test_records.remove(record)
        except ValueError:
            return
        was_loaded = self._loaded_record is record
        remaining_comparison = [r for r in self._comparison_records if r is not record]
        if self._highlight_record_id == record["id"]:
            self._highlight_record_id = None
        self._refresh_recent_test_list()
        if was_loaded:
            self.clear_results()
        elif remaining_comparison != self._comparison_records:
            if len(remaining_comparison) >= 2:
                self._plot_comparison_curves(remaining_comparison)
            elif remaining_comparison:
                self._load_recent_record(remaining_comparison[0])
            else:
                self.clear_results()
        self.append_log(f"[INFO] Removed recent record #{record['id']}")

    def _on_clear_recent_tests(self):
        if not self._recent_test_records:
            return
        showing_history = self._loaded_record is not None or bool(self._comparison_records)
        self._recent_test_records.clear()
        self.recent_test_list.clear()
        self._highlight_record_id = None
        self._loaded_record = None
        self._comparison_records = []
        if showing_history:
            self.clear_results()
        self.append_log("[INFO] Cleared all recent test records")

    def _clear_comparison_items(self):
        for curve in self._comparison_curves:
            self.plot_widget.removeItem(curve)
        for line in self._comparison_limit_lines:
            self.plot_widget.removeItem(line)
        self._comparison_curves.clear()
        self._comparison_limit_lines.clear()
        self.psrr_curve.setVisible(True)
        self.limit_line.setVisible(True)
        legend = self.plot_widget.plotItem.legend
        if legend is not None:
            legend.clear()

    def _update_comparison_metrics(self, records: list[dict]):
        summaries = [
            record["result"].get("summary") or {}
            for record in records
            if (record["result"].get("summary") or {}).get("point_count")
        ]
        if not summaries:
            return
        worst = min(summaries, key=lambda summary: summary["min_psrr_db"])
        average = sum(summary["average_psrr_db"] for summary in summaries) / len(summaries)
        passed = all(summary.get("passed") for summary in summaries)
        self.metric_values["min"].setText(f"{worst['min_psrr_db']:.2f}")
        self.metric_values["avg"].setText(f"{average:.2f}")
        self.metric_values["freq"].setText(f"{worst['min_frequency_hz']:g}")
        self.metric_values["pass"].setText("PASS" if passed else "FAIL")
        self.metric_values["pass"].setStyleSheet(
            f"color: {'#19f5c8' if passed else '#ff6f96'};"
        )

    def _plot_comparison_curves(self, records: list[dict]):
        self._loaded_record = None
        self._comparison_records = list(records)
        self._clear_comparison_items()
        self.psrr_curve.setVisible(False)
        self.limit_line.setVisible(False)
        highlight_id = self._highlight_record_id
        dim_others = highlight_id is not None and any(r["id"] == highlight_id for r in records)
        all_points = []
        plotted = 0
        for record in records:
            points = sorted(
                record["result"].get("points") or [], key=lambda point: point["frequency_hz"]
            )
            if not points:
                continue
            all_points.extend(points)
            color = QColor(self._record_color(record["id"]))
            symbol_color = QColor(color)
            if dim_others and record["id"] != highlight_id:
                color.setAlpha(90)
                symbol_color.setAlpha(90)
            curve = self.plot_widget.plot(
                [point["frequency_hz"] for point in points],
                [point["psrr_db"] for point in points],
                pen=pg.mkPen(color, width=3 if record["id"] == highlight_id else 2),
                symbol="o", symbolSize=6, symbolBrush=symbol_color, symbolPen=None,
                name=f"#{record['id']} {self._record_display_name(record)}",
            )
            self._comparison_curves.append(curve)
            limit_color = QColor(color)
            limit_color.setAlpha(150)
            limit_line = pg.InfiniteLine(
                angle=0, movable=False,
                pen=pg.mkPen(limit_color, width=1, style=Qt.DashLine),
            )
            limit_line.setValue(self._result_limit_db(record["result"]))
            limit_line.setToolTip(f"#{record['id']} limit")
            self.plot_widget.addItem(limit_line)
            self._comparison_limit_lines.append(limit_line)
            plotted += 1
        if not plotted:
            self.append_log("[WARN] The checked records contain no curve data")
            return
        self._update_frequency_ticks_for_points(all_points)
        self._update_comparison_metrics(records)
        self.result_status_label.setText("COMPARE")
        self.result_summary_label.setText(
            f"Comparing {plotted} records | Select a record to highlight its curve; "
            "double-click to load a single result."
        )
        self.plot_widget.autoRange()
        self.append_log(f"[INFO] Plotted {plotted} recent PSRR records for comparison")

    def _sync_scope_from_top(self):
        self.sync_oscilloscope_from_top()

    def _on_method_changed(self):
        is_j2120a = self.method_combo.currentData() == "mso64b_j2120a"
        for card in (
            self.n6705c_card, self.scope_card, self.excitation_card, self.acquisition_card
        ):
            card.setVisible(is_j2120a)
        self.ap_connection_card.setVisible(not is_j2120a)
        self.ap_output_card.setVisible(not is_j2120a)
        self.ap_card.setVisible(not is_j2120a)
        if not self._comparison_records and self._loaded_record is None:
            self.limit_line.setValue(self._current_limit_db())
            self._update_frequency_ticks()
        self._sync_ap_output_controls()

    def _on_ap_connection_changed(self):
        self.ap_ssh_frame.setVisible(self.ap_connection_combo.currentData() == "vm_ssh")

    def _toggle_ap_connection_collapsed(self):
        self._set_ap_connection_collapsed(not self.ap_connection_content.isHidden())

    def _set_ap_connection_collapsed(self, collapsed: bool):
        self.ap_connection_content.setVisible(not collapsed)
        self.ap_connection_toggle_btn.setText("▶" if collapsed else "▼")
        self.ap_connection_toggle_btn.setToolTip("Expand" if collapsed else "Collapse")

    def _on_ap_connect_or_disconnect(self):
        if self._ap_connection_busy or self._ap_output_busy or self.is_test_running:
            return
        operation = "disconnect" if self.ap_connected else "connect"
        config = None
        if operation == "connect":
            try:
                config = audio_precision_config_from_dict(self.get_test_config())
            except (TypeError, ValueError) as exc:
                self._set_ap_status("● Invalid configuration", "error")
                self.append_log(f"[ERROR] AP 连接配置无效：{exc}")
                return
        self._ap_connection_operation = operation
        self._ap_connection_busy = True
        self._set_ap_status(
            "● Disconnecting" if self.ap_connected else "● Connecting", "busy"
        )
        self._sync_ap_connection_controls()
        target = self.audio_precision or self.ap_ssh_session
        self._ap_connection_thread = QThread(self)
        self._ap_connection_worker = AudioPrecisionConnectionWorker(
            config=config, operation=operation, target=target
        )
        self._ap_connection_worker.moveToThread(self._ap_connection_thread)
        self._ap_connection_thread.started.connect(self._ap_connection_worker.run)
        self._ap_connection_worker.log.connect(self.append_log)
        self._ap_connection_worker.succeeded.connect(self._on_ap_connection_succeeded)
        self._ap_connection_worker.failed.connect(self._on_ap_connection_failed)
        self._ap_connection_worker.succeeded.connect(self._ap_connection_thread.quit)
        self._ap_connection_worker.failed.connect(self._ap_connection_thread.quit)
        self._ap_connection_thread.finished.connect(self._ap_connection_worker.deleteLater)
        self._ap_connection_thread.finished.connect(self._ap_connection_thread.deleteLater)
        self._ap_connection_thread.finished.connect(self._on_ap_connection_thread_finished)
        self._ap_connection_thread.start()

    def _on_ap_connection_succeeded(self, target):
        operation = self._ap_connection_operation
        self._ap_connection_busy = False
        if operation == "connect":
            if self.ap_connection_combo.currentData() == "vm_ssh" and not DEBUG_MOCK:
                self.ap_ssh_session = target
            else:
                self.audio_precision = target
            self.ap_connected = True
            self._set_ap_status("● Connected")
            self._set_ap_connection_collapsed(True)
            self.append_log(f"[INFO] Audio Precision connected: {self.ap_connection_combo.currentText()}")
        else:
            self._clear_ap_connection()
            self._set_ap_status("● Ready")
            self.append_log("[INFO] Audio Precision disconnected")
        update_connect_button_state(self.ap_connect_btn, self.ap_connected)
        self._sync_ap_connection_controls()
        if operation == "connect":
            self._start_ap_output_operation(query_only=True)

    def _on_ap_connection_failed(self, message: str):
        operation = self._ap_connection_operation
        self._ap_connection_busy = False
        if operation == "connect":
            self._clear_ap_connection()
        self._set_ap_status(
            "● Disconnect failed" if operation == "disconnect" else "● Connection failed",
            "error",
        )
        self.append_log(f"[ERROR] Audio Precision {operation} failed: {message}")
        update_connect_button_state(self.ap_connect_btn, self.ap_connected)
        self._sync_ap_connection_controls()

    def _on_ap_connection_thread_finished(self):
        self._ap_connection_thread = None
        self._ap_connection_worker = None

    def _clear_ap_connection(self):
        self.audio_precision = None
        self.ap_ssh_session = None
        self.ap_connected = False
        self._set_ap_output_state(False)

    def _set_ap_status(self, status: str, state: str = "ok"):
        self.ap_status_label.setText(status)
        self.ap_status_label.setObjectName({
            "ok": "statusOk", "busy": "statusWarn", "error": "statusErr",
        }[state])
        self.ap_status_label.style().unpolish(self.ap_status_label)
        self.ap_status_label.style().polish(self.ap_status_label)

    def _sync_ap_connection_controls(self):
        enabled = (
            not self.ap_connected and not self._ap_connection_busy
            and not self._ap_output_busy and not self.is_test_running
        )
        connect_enabled = (
            not self._ap_connection_busy and not self._ap_output_busy
            and not self.is_test_running
        )
        if not connect_enabled and self.ap_connect_btn.hasFocus():
            self.ap_connection_toggle_btn.setFocus(Qt.OtherFocusReason)
        for widget in self._ap_connection_widgets:
            widget.setEnabled(enabled)
        self.ap_connect_btn.setEnabled(connect_enabled)
        self._sync_ap_output_controls()

    def _refresh_ap_connection(self):
        if not self.ap_connected:
            return
        target = self.audio_precision or self.ap_ssh_session
        if target is not None and bool(getattr(target, "connected", False)):
            return
        self._clear_ap_connection()
        update_connect_button_state(self.ap_connect_btn, connected=False)
        self._set_ap_status("● Connection lost", "error")
        self.append_log("[WARN] Audio Precision connection lost")
        self._sync_ap_connection_controls()

    def _on_ap_output_toggle(self):
        if self._ap_output_busy or self.is_test_running:
            return
        self._refresh_ap_connection()
        if not self.ap_connected:
            self._set_ap_status("● Connect Audio Precision first", "error")
            self.append_log("[ERROR] Connect Audio Precision before controlling OUTPUT")
            return
        try:
            config = audio_precision_config_from_dict(self.get_test_config())
        except (TypeError, ValueError) as exc:
            self.append_log(f"[ERROR] Invalid Audio Precision OUTPUT configuration: {exc}")
            return

        self._start_ap_output_operation(config, enabled=not self._ap_output_on)

    def _start_ap_output_operation(self, config=None, *, enabled=False, query_only=False):
        self._ap_output_busy = True
        self._ap_output_operation = "query" if query_only else "set"
        self.ap_output_status_label.setText("SYNCING" if query_only else "UPDATING")
        self.ap_output_status_label.setObjectName("statusWarn")
        self.ap_output_status_label.style().unpolish(self.ap_output_status_label)
        self.ap_output_status_label.style().polish(self.ap_output_status_label)
        if self.ap_output_toggle_btn.hasFocus():
            self.ap_connection_toggle_btn.setFocus(Qt.OtherFocusReason)
        self._sync_ap_connection_controls()

        self._ap_output_thread = QThread(self)
        self._ap_output_worker = AudioPrecisionOutputWorker(
            config,
            enabled=enabled,
            audio_precision=self.audio_precision,
            ssh_session=self.ap_ssh_session,
            query_only=query_only,
        )
        self._ap_output_worker.moveToThread(self._ap_output_thread)
        self._ap_output_thread.started.connect(self._ap_output_worker.run)
        self._ap_output_worker.log.connect(self.append_log)
        self._ap_output_worker.finished.connect(self._on_ap_output_finished)
        self._ap_output_worker.finished.connect(self._ap_output_thread.quit)
        self._ap_output_thread.finished.connect(self._ap_output_worker.deleteLater)
        self._ap_output_thread.finished.connect(self._ap_output_thread.deleteLater)
        self._ap_output_thread.finished.connect(self._on_ap_output_thread_finished)
        self._ap_output_thread.start()

    def _on_ap_output_finished(self, success: bool, enabled: bool, message: str):
        operation = self._ap_output_operation
        self._ap_output_busy = False
        self._ap_output_operation = ""
        if success:
            self._set_ap_output_state(enabled)
            self.append_log(f"[INFO] {message}")
        else:
            self.ap_output_status_label.setText("UNKNOWN" if operation == "query" else "ERROR")
            self.ap_output_status_label.setObjectName("statusErr")
            self.ap_output_status_label.style().unpolish(self.ap_output_status_label)
            self.ap_output_status_label.style().polish(self.ap_output_status_label)
            action = "synchronization" if operation == "query" else "operation"
            self.append_log(f"[ERROR] Audio Precision OUTPUT {action} failed: {message}")
        self._sync_ap_connection_controls()

    def _on_ap_output_thread_finished(self):
        self._ap_output_thread = None
        self._ap_output_worker = None

    def _set_ap_output_state(self, enabled: bool):
        self._ap_output_on = bool(enabled)
        self.ap_output_status_label.setText("ON" if enabled else "OFF")
        self.ap_output_status_label.setObjectName("statusOk" if enabled else "statusErr")
        self.ap_output_status_label.style().unpolish(self.ap_output_status_label)
        self.ap_output_status_label.style().polish(self.ap_output_status_label)
        self.ap_output_toggle_btn.setText("TURN OUTPUT OFF" if enabled else "TURN OUTPUT ON")
        self.ap_output_toggle_btn.setProperty("outputOn", bool(enabled))
        self.ap_output_toggle_btn.style().unpolish(self.ap_output_toggle_btn)
        self.ap_output_toggle_btn.style().polish(self.ap_output_toggle_btn)

    def _sync_ap_output_controls(self):
        parameters_enabled = (
            not self.is_test_running and not self._ap_output_busy and not self._ap_output_on
        )
        for widget in (
            self.ap_output_channel_combo, self.ap_amplitude_spin, self.ap_offset_spin
        ):
            widget.setEnabled(parameters_enabled)
        self.method_combo.setEnabled(parameters_enabled)
        self.ap_output_toggle_btn.setEnabled(
            self.ap_connected and not self._ap_connection_busy
            and not self._ap_output_busy and not self.is_test_running
        )
        self.start_test_btn.setEnabled(not self._ap_output_busy)

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
            "include_endpoints": self.include_endpoints_check.isChecked(),
            "frequencies_hz": list(self._frequencies_from_controls()),
            "cycles": self.cycles_spin.value(),
            "output_scale_mv": self.output_scale_spin.value(),
            "limit_db": self.limit_spin.value(),
            "close_channel_after": self.close_channel_check.isChecked(),
            "ap_connection_mode": self.ap_connection_combo.currentData(),
            "ap_ssh_profile": self.ap_ssh_profile_edit.text().strip(),
            "ap_ssh_host": self.ap_ssh_host_edit.text().strip(),
            "ap_ssh_user": self.ap_ssh_user_edit.text().strip(),
            "ap_ssh_port": self.ap_ssh_port_spin.value(),
            "ap_ssh_python": self.ap_ssh_python_edit.text().strip(),
            "ap_project_path": "",
            "ap_signal_path": "Signal Path1",
            "ap_measurement": "Signal Analyzer",
            "ap_vin_input_channel": self.ap_vin_input_channel_combo.currentData(),
            "ap_vout_input_channel": self.ap_vout_input_channel_combo.currentData(),
            "ap_output_channel": self.ap_output_channel_combo.currentData(),
            "ap_amplitude_mvrms": self.ap_amplitude_spin.value(),
            "ap_offset_v": self.ap_offset_spin.value(),
            "ap_start_frequency_hz": self.ap_start_frequency_spin.value(),
            "ap_end_frequency_hz": self.ap_end_frequency_spin.value(),
            "ap_frequency_points": self.ap_frequency_points_spin.value(),
            "ap_include_endpoints": self.ap_include_endpoints_check.isChecked(),
            "ap_fft_length": self.ap_fft_length_combo.currentData(),
            "ap_fft_window": self.ap_fft_window_combo.currentData(),
            "ap_fft_averages": self.ap_fft_averages_spin.value(),
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
            include_endpoints=getattr(self, f"{prefix}include_endpoints_check").isChecked(),
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
        if is_audio_precision:
            self._refresh_ap_connection()
            if not self.ap_connected:
                self.set_system_status("请先连接 Audio Precision", True)
                self.append_log("[ERROR] 启动测试前请先连接 Audio Precision")
                return
            if self._ap_output_busy:
                self.set_system_status("Audio Precision OUTPUT is being updated", True)
                return
            if not self._ap_output_on:
                self.set_system_status("Turn on Audio Precision OUTPUT before starting", True)
                self.append_log("[ERROR] Turn on Audio Precision OUTPUT before starting the test")
                return
        else:
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
            self.test_worker = AudioPrecisionPSRRWorker(
                config,
                audio_precision=self.audio_precision,
                ssh_session=self.ap_ssh_session,
                mock_mode=DEBUG_MOCK,
            )
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
        self.start_test_btn.setEnabled(False)

    def _set_test_running(self, running: bool):
        self.start_test_btn.setText("STOP TEST" if running else "START TEST")
        self.start_test_btn.setProperty("running", running)
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        for widget in self._config_widgets:
            widget.setEnabled(not running)
        for widget in (
            self.recent_test_list, self.compare_recent_btn,
            self.load_recent_btn, self.clear_recent_btn,
        ):
            widget.setEnabled(not running)
        self._sync_ap_connection_controls()
        self._sync_ap_output_controls()

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
        self._refresh_ap_connection()
        self._set_test_running(False)
        self.result_status_label.setText("DONE" if success else "STOPPED")
        self.set_system_status(message, not success)
        self.append_log(f"[{'RESULT' if success else 'WARN'}] {message}")
        if success:
            self._record_recent_test(self._last_result)
        self.sequence_execution_finished.emit(success, message)

    def _cleanup_test_thread(self):
        self.test_thread = None
        self.test_worker = None

    @staticmethod
    def _frequency_tick_values(start_hz: float, end_hz: float) -> list[float]:
        start_hz, end_hz = sorted((float(start_hz), float(end_hz)))
        if start_hz <= 0:
            return []
        preferred = (10, 100, 1000, 20000, 50000, 100000, 1e6, 2e6)
        ticks = [start_hz, end_hz]
        ticks.extend(
            frequency for frequency in preferred
            if start_hz < frequency < end_hz and not (20000 < end_hz < 100000 and frequency == 20000)
        )
        return sorted(set(ticks))

    @staticmethod
    def _format_frequency_tick(frequency_hz: float) -> str:
        if frequency_hz >= 1e6:
            return f"{frequency_hz / 1e6:.6g}M"
        if frequency_hz >= 1e3:
            return f"{frequency_hz / 1e3:.6g}k"
        return f"{frequency_hz:.6g}"

    def _update_frequency_ticks(self):
        prefix = "ap_" if self.method_combo.currentData() == "audio_precision" else ""
        start_hz, end_hz = sorted((
            getattr(self, f"{prefix}start_frequency_spin").value(),
            getattr(self, f"{prefix}end_frequency_spin").value(),
        ))
        ticks = [
            (math.log10(frequency), self._format_frequency_tick(frequency))
            for frequency in self._frequency_tick_values(start_hz, end_hz)
        ]
        self.plot_widget.getAxis("bottom").setTicks([ticks])
        if start_hz < end_hz:
            self.plot_widget.setXRange(math.log10(start_hz), math.log10(end_hz), padding=0.02)

    def _update_frequency_ticks_for_points(self, points: list[dict]):
        frequencies = [point["frequency_hz"] for point in points if point["frequency_hz"] > 0]
        if not frequencies:
            self._update_frequency_ticks()
            return
        ticks = [
            (math.log10(frequency), self._format_frequency_tick(frequency))
            for frequency in self._frequency_tick_values(min(frequencies), max(frequencies))
        ]
        self.plot_widget.getAxis("bottom").setTicks([ticks])

    def _update_plot(self, name: str = "Current"):
        ordered = sorted(self._points, key=lambda point: point["frequency_hz"])
        self.psrr_curve.setData(
            [point["frequency_hz"] for point in ordered],
            [point["psrr_db"] for point in ordered],
        )
        self.psrr_curve.setVisible(True)
        self.limit_line.setVisible(True)
        legend = self.plot_widget.plotItem.legend
        if legend is not None:
            legend.clear()
            if ordered:
                legend.addItem(self.psrr_curve, name)
        limit_db = (
            self._result_limit_db(self._last_result)
            if self._loaded_record is not None and self._last_result is not None
            else self._current_limit_db()
        )
        self.limit_line.setValue(limit_db)

    def clear_results(self):
        self._points.clear()
        self._last_result = None
        self._loaded_record = None
        self._comparison_records = []
        self._clear_comparison_items()
        self.psrr_curve.setData([], [])
        self.limit_line.setValue(self._current_limit_db())
        self._update_frequency_ticks()
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
        if self.ap_connected and not self.is_test_running:
            self._on_ap_connect_or_disconnect()
        elif self.ap_ssh_session is not None:
            self.ap_ssh_session.terminate()
            self._clear_ap_connection()

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
        if self.ap_connected:
            current = self.get_test_config()
            connection_keys = (
                "ap_connection_mode", "ap_ssh_profile", "ap_ssh_host",
                "ap_ssh_user", "ap_ssh_port", "ap_ssh_python",
            )
            if any(key in cfg and cfg[key] != current[key] for key in connection_keys):
                return False, "请先断开 Audio Precision，再修改连接参数。"
        if self._ap_output_on or self._ap_output_busy:
            current = self.get_test_config()
            output_keys = (
                "measurement_method", "ap_output_channel",
                "ap_amplitude_mvrms", "ap_offset_v",
            )
            if any(key in cfg and cfg[key] != current[key] for key in output_keys):
                return False, (
                    "Turn off Audio Precision OUTPUT before changing "
                    "measurement method or output parameters."
                )

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
        if "ap_connection_mode" in cfg:
            index = self.ap_connection_combo.findData(str(cfg["ap_connection_mode"]))
            if index >= 0:
                self.ap_connection_combo.setCurrentIndex(index)
                applied.append("ap_connection_mode")
                touched.append(self.ap_connection_combo)
        set_combo(self.source_channel_combo, "source_channel")
        set_combo(self.input_channel_combo, "input_channel")
        set_combo(self.output_channel_combo, "output_channel")
        set_combo(self.ap_vin_input_channel_combo, "ap_vin_input_channel")
        set_combo(self.ap_vout_input_channel_combo, "ap_vout_input_channel")
        set_combo(self.ap_output_channel_combo, "ap_output_channel")
        set_combo(self.ap_fft_length_combo, "ap_fft_length")
        if "ap_fft_window" in cfg:
            index = self.ap_fft_window_combo.findData(str(cfg["ap_fft_window"]))
            if index >= 0:
                self.ap_fft_window_combo.setCurrentIndex(index)
                applied.append("ap_fft_window")
                touched.append(self.ap_fft_window_combo)
        for spin, key in (
            (self.dc_voltage_spin, "dc_voltage"),
            (self.cycles_spin, "cycles"),
            (self.output_scale_spin, "output_scale_mv"),
            (self.limit_spin, "limit_db"),
            (self.start_frequency_spin, "start_frequency_hz"),
            (self.end_frequency_spin, "end_frequency_hz"),
            (self.frequency_points_spin, "frequency_points"),
            (self.ap_ssh_port_spin, "ap_ssh_port"),
            (self.ap_amplitude_spin, "ap_amplitude_mvrms"),
            (self.ap_offset_spin, "ap_offset_v"),
            (self.ap_start_frequency_spin, "ap_start_frequency_hz"),
            (self.ap_end_frequency_spin, "ap_end_frequency_hz"),
            (self.ap_frequency_points_spin, "ap_frequency_points"),
            (self.ap_fft_averages_spin, "ap_fft_averages"),
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
        if not all(key in cfg for key in (
            "start_frequency_hz", "end_frequency_hz", "frequency_points"
        )):
            set_legacy_frequencies(
                self.start_frequency_spin, self.end_frequency_spin,
                self.frequency_points_spin, "frequencies_hz"
            )
        if not all(key in cfg for key in (
            "ap_start_frequency_hz", "ap_end_frequency_hz", "ap_frequency_points"
        )):
            set_legacy_frequencies(
                self.ap_start_frequency_spin, self.ap_end_frequency_spin,
                self.ap_frequency_points_spin, "ap_frequencies_hz"
            )
        set_line(self.ap_ssh_profile_edit, "ap_ssh_profile")
        set_line(self.ap_ssh_host_edit, "ap_ssh_host")
        set_line(self.ap_ssh_user_edit, "ap_ssh_user")
        set_line(self.ap_ssh_python_edit, "ap_ssh_python")
        for checkbox, key in (
            (self.include_endpoints_check, "include_endpoints"),
            (self.ap_include_endpoints_check, "ap_include_endpoints"),
        ):
            if key in cfg:
                checkbox.setChecked(bool(cfg[key]))
                applied.append(key)
                touched.append(checkbox)
        if "close_channel_after" in cfg:
            self.close_channel_check.setChecked(bool(cfg["close_channel_after"]))
            applied.append("close_channel_after")
            touched.append(self.close_channel_check)
        if not applied:
            return False, "配置草案未包含任何可识别的 PSRR 配置项。"
        self._on_method_changed()
        self._on_ap_connection_changed()
        if not self._comparison_records and self._loaded_record is None:
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
