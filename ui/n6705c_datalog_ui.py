#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import math
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QGridLayout, QFrame, QCheckBox,
    QRadioButton, QButtonGroup, QSizePolicy, QFileDialog,
    QScrollArea, QGraphicsRectItem
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor, QBrush, QPen
import pyqtgraph as pg
import pyvisa

from instruments.n6705c import N6705C

DEBUG_FLAG = True


class _MockInstr:
    def write(self, cmd):
        pass

    def query(self, cmd):
        return ""


class _MockN6705C:
    def __init__(self):
        self.instr = _MockInstr()

    def disconnect(self):
        pass

    def channel_on(self, channel):
        pass

    def channel_off(self, channel):
        pass

    def set_voltage(self, channel, voltage):
        pass

    def set_current(self, channel, current):
        pass

    def set_current_limit(self, channel, current_limit):
        pass

    def measure_voltage(self, channel):
        return 0.0

    def measure_current(self, channel):
        return 0.0


CHANNEL_COLORS = [
    "#18b67a",
    "#d4a514",
    "#2f6fed",
    "#d14b72",
    "#00bcd4",
    "#ff9800",
    "#ab47bc",
    "#8bc34a",
]

CHANNEL_LABEL_COLORS = [
    "#7fffcf",
    "#ffe566",
    "#8cb8ff",
    "#ff9ab8",
    "#7ef5ff",
    "#ffc966",
    "#dda0ff",
    "#c8ff7e",
]


def _format_value(value_mA):
    abs_v = abs(value_mA)
    if abs_v >= 1000:
        return f"{value_mA / 1000:.3f} A"
    elif abs_v >= 1:
        return f"{value_mA:.1f} mA"
    elif abs_v >= 0.001:
        return f"{value_mA * 1000:.1f} \u00B5A"
    else:
        return f"{value_mA:.4f} mA"


class _DatalogWorker(QObject):
    data_ready = Signal(dict)
    finished = Signal()
    error = Signal(str)

    def __init__(self, n6705c_list, channels_per_unit, unit_labels,
                 record_type, sample_period_us, monitoring_time_s,
                 debug=False):
        super().__init__()
        self.n6705c_list = n6705c_list
        self.channels_per_unit = channels_per_unit
        self.unit_labels = unit_labels
        self.record_type = record_type
        self.sample_period_us = sample_period_us
        self.monitoring_time_s = monitoring_time_s
        self.debug = debug
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        import time
        try:
            sample_period_s = self.sample_period_us / 1_000_000.0

            if self.debug:
                all_data = self._generate_mock_data(sample_period_s)
                self.data_ready.emit(all_data)
                self.finished.emit()
                return

            all_data = {}
            for unit_idx, n6705c in enumerate(self.n6705c_list):
                if self._is_stopped:
                    break
                channels = self.channels_per_unit[unit_idx]
                if not channels:
                    continue

                for ch in range(1, 5):
                    n6705c.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
                    n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")

                for ch in channels:
                    if self.record_type == "current":
                        n6705c.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{ch})")
                        n6705c.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{ch})")
                    else:
                        n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT ON,(@{ch})")

                n6705c.instr.write(f"SENS:DLOG:TIME {self.monitoring_time_s}")
                n6705c.instr.write(f"SENS:DLOG:PER {sample_period_s}")
                n6705c.instr.write("TRIG:DLOG:SOUR IMM")

                dlog_file = "internal:\\datalog_capture.dlog"
                n6705c.instr.write(f'INIT:DLOG "{dlog_file}"')

            time.sleep(self.monitoring_time_s + 2)

            for unit_idx, n6705c in enumerate(self.n6705c_list):
                if self._is_stopped:
                    break
                channels = self.channels_per_unit[unit_idx]
                if not channels:
                    continue

                csv_file = "internal:\\datalog_capture.csv"
                n6705c.instr.write(f'MMEM:EXP:DLOG "{csv_file}"')
                time.sleep(3)

                n6705c.instr.write("FORM ASC")
                raw = n6705c.instr.query(f'MMEM:DATA? "{csv_file}"')
                lines = raw.splitlines()

                ulabel = self.unit_labels[unit_idx]
                for ch_idx, ch in enumerate(channels):
                    label = f"{ulabel} CH{ch}"
                    ch_data = []
                    for line in lines:
                        if "," in line:
                            parts = line.split(",")
                            try:
                                col = 1 + ch_idx
                                ch_data.append(float(parts[col]))
                            except (ValueError, IndexError):
                                pass
                    if ch_data:
                        t = [i * sample_period_s for i in range(len(ch_data))]
                        all_data[label] = {"time": t, "values": ch_data}

            self.data_ready.emit(all_data)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()

    def _generate_mock_data(self, sample_period_s):
        rng = random.Random(42)
        total_points = int(self.monitoring_time_s / sample_period_s)
        total_points = min(total_points, 50000)

        all_data = {}
        ch_global_idx = 0
        for unit_idx in range(len(self.channels_per_unit)):
            channels = self.channels_per_unit[unit_idx]
            ulabel = self.unit_labels[unit_idx]
            for ch in channels:
                label = f"{ulabel} CH{ch}".strip()
                t = [i * sample_period_s for i in range(total_points)]

                if self.record_type == "current":
                    base_mA = 1780 + ch_global_idx * 120
                    noise_std = 15 + ch_global_idx * 5
                    values = [
                        base_mA
                        + 8 * math.sin(2 * math.pi * 0.5 * ti)
                        + rng.gauss(0, noise_std)
                        for ti in t
                    ]
                else:
                    base_mV = 1200 + ch_global_idx * 600
                    values = [
                        base_mV
                        + 5 * math.sin(2 * math.pi * 0.3 * ti)
                        + rng.gauss(0, 3)
                        for ti in t
                    ]

                all_data[label] = {"time": t, "values": values}
                ch_global_idx += 1

        return all_data


class CardFrame(QFrame):
    def __init__(self, title="", icon="", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)

        if title:
            self.title_label = QLabel(f"{icon}  {title}" if icon else title)
            self.title_label.setObjectName("cardTitle")
            self.main_layout.addWidget(self.title_label)


class FixedPopupComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.view().window().setStyleSheet(
            "background-color: #0a1733; border: 1px solid #27406f;"
        )
        self.view().setStyleSheet(
            "background-color: #0a1733; color: #eaf2ff; "
            "selection-background-color: #334a7d; outline: 0px;"
        )

    def showPopup(self):
        super().showPopup()
        view = self.view()
        if view and view.window():
            popup = view.window()
            popup.setStyleSheet(
                "background-color: #0a1733; border: 1px solid #27406f;"
            )
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(global_pos.x(), global_pos.y())


class N6705CDatalogUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self):
        super().__init__()

        self.rm = None
        self.n6705c_a = None
        self.n6705c_b = None
        self.is_connected_a = False
        self.is_connected_b = False
        self.is_recording = False

        self._record_thread = None
        self._record_worker = None

        self.datalog_data = {}
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_region = None
        self.box_zoom_enabled = False
        self._pending_marker = None
        self.custom_labels = []
        self.custom_label_lines = []

        self.crosshair_v = None
        self.crosshair_tooltip = None
        self.crosshair_dots = []

        self.search_timer_a = QTimer(self)
        self.search_timer_a.timeout.connect(lambda: self._search_devices("a"))
        self.search_timer_a.setSingleShot(True)

        self.search_timer_b = QTimer(self)
        self.search_timer_b.timeout.connect(lambda: self._search_devices("b"))
        self.search_timer_b.setSingleShot(True)

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()

    @staticmethod
    def _get_checkmark_path(accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        _cb_icons = self._get_checkmark_path("4f46e5")
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

            QLabel#cardTitle {
                font-size: 11px;
                font-weight: 700;
                color: #f4f7ff;
                letter-spacing: 0.5px;
                background-color: transparent;
            }

            QLabel#fieldLabel {
                color: #8eb0e3;
                font-size: 11px;
                background-color: transparent;
            }

            QLabel#hintLabel {
                color: #5c7a9e;
                font-size: 11px;
                font-style: italic;
                background-color: transparent;
            }

            QLabel#analysisTitle {
                color: #8eb0e3;
                font-size: 12px;
                background-color: transparent;
            }

            QLabel#analysisDelta {
                color: #7da2d6;
                font-size: 11px;
                background-color: transparent;
            }

            QFrame#cardFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 14px;
            }

            QFrame#chartFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 14px;
            }

            QFrame#chResultCard {
                background-color: #0a1733;
                border: 1px solid #1a2b52;
                border-radius: 10px;
            }

            QFrame#separator {
                background-color: #1a2b52;
                border: none;
                max-height: 1px;
                min-height: 1px;
            }

            QLineEdit, QComboBox {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #4f46e5;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4cc9f0;
            }

            QComboBox {
                padding-right: 24px;
            }

            QComboBox::drop-down {
                border: none;
                width: 22px;
                background: transparent;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }

            QComboBox QAbstractItemView {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                selection-background-color: #334a7d;
                outline: 0px;
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

            QPushButton#chartToolBtn {
                min-height: 28px;
                padding: 4px 12px;
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
                font-size: 11px;
            }

            QPushButton#chartToolBtn:hover {
                background-color: #1a3260;
                border: 1px solid #3c5fa1;
            }

            QPushButton#searchBtn {
                min-height: 30px;
                max-width: 34px;
                min-width: 34px;
                padding: 0;
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
                font-size: 13px;
            }

            QPushButton#searchBtn:hover {
                background-color: #1a3260;
            }

            QPushButton#dynamicConnectBtn {
                min-height: 30px;
                border-radius: 8px;
                padding: 4px 12px;
                font-weight: 700;
            }

            QPushButton#dynamicConnectBtn[connected="false"] {
                background-color: #053b38;
                border: 1px solid #08c9a5;
                color: #10e7bc;
            }

            QPushButton#dynamicConnectBtn[connected="false"]:hover {
                background-color: #064744;
                border: 1px solid #19f0c5;
                color: #43f3d0;
            }

            QPushButton#dynamicConnectBtn[connected="true"] {
                background-color: #3a0828;
                border: 1px solid #d61b67;
                color: #ffb7d3;
            }

            QPushButton#dynamicConnectBtn[connected="true"]:hover {
                background-color: #4a0b31;
                border: 1px solid #f0287b;
                color: #ffd0e2;
            }

            QPushButton#primaryActionBtn {
                min-height: 40px;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
                color: white;
            }

            QPushButton#primaryActionBtn[running="false"] {
                border: 1px solid #645bff;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5b5cf6,
                    stop:1 #6a38ff
                );
            }

            QPushButton#primaryActionBtn[running="false"]:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b6cff,
                    stop:1 #7d4cff
                );
            }

            QPushButton#primaryActionBtn[running="true"] {
                background-color: #8d0f3e;
                border: 1px solid #df4a7a;
                color: #ffd9e6;
            }

            QPushButton#primaryActionBtn[running="true"]:hover {
                background-color: #a11247;
                border: 1px solid #f05a8c;
            }

            QPushButton#exportBtn {
                min-height: 30px;
                padding: 4px 12px;
                border-radius: 8px;
                background-color: #16284f;
                color: #dfe8ff;
            }

            QPushButton#exportBtn:hover {
                background-color: #1e3466;
            }

            QPushButton#addLabelBtn {
                min-height: 30px;
                min-width: 30px;
                max-width: 30px;
                padding: 0px;
                border-radius: 8px;
                background-color: #5b5cf6;
                color: white;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#addLabelBtn:hover {
                background-color: #6b6cff;
            }

            QRadioButton {
                color: #dbe7ff;
                background: transparent;
                spacing: 6px;
            }

            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }

            QRadioButton::indicator:unchecked {
                border: 2px solid #44608e;
                background: #0a1733;
                border-radius: 8px;
            }

            QRadioButton::indicator:checked {
                border: 2px solid #4cc9f0;
                background-color: #4f46e5;
                border-radius: 8px;
            }

            QCheckBox {
                color: #dbe7ff;
                background: transparent;
                spacing: 6px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                image: url("__UNCHECKED__");
            }

            QCheckBox::indicator:checked {
                image: url("__CHECKED__");
            }

            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: #0a1733;
                width: 6px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical {
                background: #27406f;
                border-radius: 3px;
                min-height: 20px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """.replace("__UNCHECKED__", _cb_icons['unchecked']).replace("__CHECKED__", _cb_icons['checked']))

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_row = QHBoxLayout()
        icon_lbl = QLabel("\u2728")
        icon_lbl.setStyleSheet("font-size: 20px; color: #d4a514;")
        self.page_title = QLabel("Keysight N6705C Datalog Analyzer")
        self.page_title.setObjectName("pageTitle")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(self.page_title)
        title_row.addStretch()
        title_layout.addLayout(title_row)

        self.page_subtitle = QLabel(
            "Record, analyze, and export high-resolution datalogs from the N6705C."
        )
        self.page_subtitle.setObjectName("pageSubtitle")
        title_layout.addWidget(self.page_subtitle)

        root_layout.addLayout(title_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        root_layout.addLayout(content_layout, 1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFixedWidth(270)

        left_container = QWidget()
        left_container.setStyleSheet("background: transparent;")
        self.left_layout = QVBoxLayout(left_container)
        self.left_layout.setContentsMargins(0, 0, 4, 0)
        self.left_layout.setSpacing(10)

        self.system_mode_card = CardFrame("SYSTEM MODE", "\u2699")
        self._build_system_mode_card()
        self.left_layout.addWidget(self.system_mode_card)

        self.connection_card_a = CardFrame("CONNECTION \u2014 Unit A", "\u26A1")
        self._build_connection_card_a()
        self.left_layout.addWidget(self.connection_card_a)

        self.connection_card_b = CardFrame("CONNECTION \u2014 Unit B", "\u26A1")
        self._build_connection_card_b()
        self.left_layout.addWidget(self.connection_card_b)
        self.connection_card_b.hide()

        self.config_card = CardFrame("DATALOG CONFIG", "\u2699")
        self._build_config_card()
        self.left_layout.addWidget(self.config_card)

        self.left_layout.addStretch()

        self.start_btn = QPushButton("\u25B7  Start Recording")
        self.start_btn.setObjectName("primaryActionBtn")
        self.start_btn.setProperty("running", "false")
        self.left_layout.addWidget(self.start_btn)

        self.export_btn = QPushButton("\u2913  Export Datalog")
        self.export_btn.setObjectName("exportBtn")
        self.left_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("\u2912  Import Datalog")
        self.import_btn.setObjectName("exportBtn")
        self.left_layout.addWidget(self.import_btn)

        left_scroll.setWidget(left_container)
        content_layout.addWidget(left_scroll)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        content_layout.addLayout(right_layout, 1)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartFrame")
        chart_outer = QVBoxLayout(self.chart_frame)
        chart_outer.setContentsMargins(12, 10, 12, 10)
        chart_outer.setSpacing(8)

        chart_header = QHBoxLayout()
        chart_icon = QLabel("\u2728")
        chart_icon.setStyleSheet("font-size: 16px; color: #d4a514;")
        chart_title = QLabel("Datalog Viewer")
        chart_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #f4f7ff;"
        )
        chart_header.addWidget(chart_icon)
        chart_header.addWidget(chart_title)
        chart_header.addStretch()

        self.box_zoom_btn = QPushButton("\u2316 Box Zoom: OFF")
        self.box_zoom_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.box_zoom_btn)

        self.reset_view_btn = QPushButton("\u2316 Reset View")
        self.reset_view_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.reset_view_btn)

        self.marker_a_btn = QPushButton("Set Marker A")
        self.marker_a_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.marker_a_btn)

        self.marker_b_btn = QPushButton("Set Marker B")
        self.marker_b_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.marker_b_btn)

        self.clear_markers_btn = QPushButton("Clear Markers")
        self.clear_markers_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.clear_markers_btn)

        chart_outer.addLayout(chart_header)

        self.plot_widget = pg.PlotWidget()
        self._setup_plot()
        chart_outer.addWidget(self.plot_widget, 1)

        scale_row = QHBoxLayout()
        scale_row.setSpacing(10)

        x_label = QLabel("X Scale (s/div):")
        x_label.setObjectName("fieldLabel")
        self.x_scale_edit = QLineEdit("1")
        self.x_scale_edit.setFixedWidth(100)

        self.y_scale_label = QLabel("Y Scale (mA/div):")
        self.y_scale_label.setObjectName("fieldLabel")
        self.y_scale_edit = QLineEdit("50")
        self.y_scale_edit.setFixedWidth(100)

        self.scale_hint = QLabel("Press Enter to apply")
        self.scale_hint.setObjectName("hintLabel")

        scale_row.addWidget(x_label)
        scale_row.addWidget(self.x_scale_edit)
        scale_row.addSpacing(20)
        scale_row.addWidget(self.y_scale_label)
        scale_row.addWidget(self.y_scale_edit)
        scale_row.addSpacing(20)
        scale_row.addWidget(self.scale_hint)
        scale_row.addStretch()

        chart_outer.addLayout(scale_row)

        right_layout.addWidget(self.chart_frame, 1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.marker_card = CardFrame("MARKER ANALYSIS", "\u25CE")
        self._build_marker_analysis_card()
        self.marker_card.setMinimumHeight(140)

        self.label_card = CardFrame("CUSTOM LABELS", "\u2756")
        self._build_label_card()
        self.label_card.setMinimumHeight(140)

        bottom_row.addWidget(self.marker_card, 1)
        bottom_row.addWidget(self.label_card, 1)

        right_layout.addLayout(bottom_row)

    def _build_marker_analysis_card(self):
        layout = self.marker_card.main_layout

        self.analysis_title_label = QLabel("Average Current between A & B")
        self.analysis_title_label.setObjectName("analysisTitle")
        self.analysis_title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.analysis_title_label)

        self.analysis_cards_layout = QHBoxLayout()
        self.analysis_cards_layout.setSpacing(10)
        layout.addLayout(self.analysis_cards_layout)

        self.analysis_hint_label = QLabel(
            "Set both Marker A and Marker B on the chart to\n"
            "calculate the average value."
        )
        self.analysis_hint_label.setObjectName("hintLabel")
        self.analysis_hint_label.setAlignment(Qt.AlignCenter)
        self.analysis_hint_label.setWordWrap(True)
        layout.addWidget(self.analysis_hint_label)

        self.analysis_delta_label = QLabel("")
        self.analysis_delta_label.setObjectName("analysisDelta")
        self.analysis_delta_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.analysis_delta_label)

    def _build_system_mode_card(self):
        layout = self.system_mode_card.main_layout

        self.mode_group = QButtonGroup(self)
        self.mode_4ch = QRadioButton("4 Channels (1 Unit)")
        self.mode_8ch = QRadioButton("8 Channels (2 Units)")
        self.mode_4ch.setChecked(True)

        self.mode_group.addButton(self.mode_4ch, 0)
        self.mode_group.addButton(self.mode_8ch, 1)

        layout.addWidget(self.mode_4ch)
        layout.addWidget(self.mode_8ch)

    def _create_search_btn(self):
        btn = QPushButton("\U0001F50D")
        btn.setObjectName("searchBtn")
        return btn

    def _create_connect_btn(self):
        btn = QPushButton("\U0001F517  Connect")
        btn.setObjectName("dynamicConnectBtn")
        btn.setProperty("connected", "false")
        return btn

    def _build_connection_card_a(self):
        layout = self.connection_card_a.main_layout

        res_row = QHBoxLayout()
        self.visa_combo_a = FixedPopupComboBox()
        self.visa_combo_a.addItem("USB0::0x0957::0x0F07::")
        self.visa_combo_a.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.search_btn_a = self._create_search_btn()

        res_row.addWidget(self.visa_combo_a, 1)
        res_row.addWidget(self.search_btn_a)
        layout.addLayout(res_row)

        self.connect_btn_a = self._create_connect_btn()
        layout.addWidget(self.connect_btn_a)

    def _build_connection_card_b(self):
        layout = self.connection_card_b.main_layout

        res_row = QHBoxLayout()
        self.visa_combo_b = FixedPopupComboBox()
        self.visa_combo_b.addItem("USB0::0x0957::0x0F07::")
        self.visa_combo_b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.search_btn_b = self._create_search_btn()

        res_row.addWidget(self.visa_combo_b, 1)
        res_row.addWidget(self.search_btn_b)
        layout.addLayout(res_row)

        self.connect_btn_b = self._create_connect_btn()
        layout.addWidget(self.connect_btn_b)

    def _build_config_card(self):
        layout = self.config_card.main_layout

        type_label = QLabel("Record Type")
        type_label.setObjectName("fieldLabel")
        layout.addWidget(type_label)

        type_row = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        self.type_current = QRadioButton("Current (A)")
        self.type_voltage = QRadioButton("Voltage (V)")
        self.type_current.setChecked(True)
        self.type_group.addButton(self.type_current, 0)
        self.type_group.addButton(self.type_voltage, 1)
        type_row.addWidget(self.type_current)
        type_row.addWidget(self.type_voltage)
        type_row.addStretch()
        layout.addLayout(type_row)

        self.unit_a_ch_label = QLabel("Unit A Channels")
        self.unit_a_ch_label.setObjectName("fieldLabel")
        layout.addWidget(self.unit_a_ch_label)

        ch_row_a = QHBoxLayout()
        ch_row_a.setSpacing(8)
        self.ch_checkboxes_a = []
        for i in range(1, 5):
            cb = QCheckBox(f"CH{i}")
            if i <= 2:
                cb.setChecked(True)
            self.ch_checkboxes_a.append(cb)
            ch_row_a.addWidget(cb)
        layout.addLayout(ch_row_a)

        self.unit_b_ch_label = QLabel("Unit B Channels")
        self.unit_b_ch_label.setObjectName("fieldLabel")
        layout.addWidget(self.unit_b_ch_label)
        self.unit_b_ch_label.hide()

        self.ch_row_b_widget = QWidget()
        self.ch_row_b_widget.setStyleSheet("background: transparent;")
        ch_row_b = QHBoxLayout(self.ch_row_b_widget)
        ch_row_b.setContentsMargins(0, 0, 0, 0)
        ch_row_b.setSpacing(8)
        self.ch_checkboxes_b = []
        for i in range(1, 5):
            cb = QCheckBox(f"CH{i}")
            self.ch_checkboxes_b.append(cb)
            ch_row_b.addWidget(cb)
        layout.addWidget(self.ch_row_b_widget)
        self.ch_row_b_widget.hide()

        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(10)
        param_grid.setVerticalSpacing(6)

        sp_label = QLabel("Sampling\nPeriod (\u00B5s)")
        sp_label.setObjectName("fieldLabel")
        self.sample_period_edit = QLineEdit("1000")
        self.sample_period_edit.setFixedWidth(80)

        mt_label = QLabel("Monitoring\nTime (s)")
        mt_label.setObjectName("fieldLabel")
        self.monitor_time_edit = QLineEdit("10")
        self.monitor_time_edit.setFixedWidth(80)

        param_grid.addWidget(sp_label, 0, 0)
        param_grid.addWidget(mt_label, 0, 1)
        param_grid.addWidget(self.sample_period_edit, 1, 0)
        param_grid.addWidget(self.monitor_time_edit, 1, 1)

        layout.addLayout(param_grid)

    def _build_label_card(self):
        layout = self.label_card.main_layout

        add_row = QHBoxLayout()
        add_row.setSpacing(6)

        self.label_ch_combo = FixedPopupComboBox()
        self.label_ch_combo.setFixedWidth(90)
        self.label_ch_combo.setPlaceholderText("Channel")

        self.label_time_edit = QLineEdit()
        self.label_time_edit.setPlaceholderText("Time (s)")
        self.label_time_edit.setFixedWidth(70)

        self.label_text_edit = QLineEdit()
        self.label_text_edit.setPlaceholderText("Label text...")

        self.add_label_btn = QPushButton("+")
        self.add_label_btn.setObjectName("addLabelBtn")

        add_row.addWidget(self.label_ch_combo)
        add_row.addWidget(self.label_time_edit)
        add_row.addWidget(self.label_text_edit, 1)
        add_row.addWidget(self.add_label_btn)
        layout.addLayout(add_row)

        self.labels_list_label = QLabel("No labels added.")
        self.labels_list_label.setObjectName("hintLabel")
        layout.addWidget(self.labels_list_label)

    def _setup_plot(self):
        self.plot_widget.setBackground("#071127")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)

        axis_pen = pg.mkPen(color="#2a4272", width=1)
        text_color = "#8eb0e3"

        for axis_name in ("bottom", "left"):
            axis = self.plot_widget.getPlotItem().getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(pg.mkPen(text_color))
            axis.setStyle(tickLength=-5)

        self.plot_widget.setLabel("bottom", "Time (s)", color=text_color)
        self.plot_widget.setLabel("left", "Current (mA)", color=text_color)

        self.plot_widget.setXRange(0, 10)
        self.plot_widget.setYRange(0, 2000)

        self.legend = self.plot_widget.addLegend(
            offset=(-10, 340),
            labelTextColor=text_color,
        )
        self.legend.setBrush(pg.mkBrush(7, 17, 39, 200))
        self.legend.setPen(pg.mkPen(color="#1a2b52"))

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

        self.plot_curves = {}

        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=30, slot=self._on_mouse_moved
        )

        self.plot_widget.scene().sigMouseClicked.connect(self._on_chart_clicked)

        self.plot_widget.sigRangeChanged.connect(self._on_range_changed)

    def _on_mouse_moved(self, evt):
        pos = evt[0]
        vb = self.plot_widget.getPlotItem().getViewBox()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            self.crosshair_v.setVisible(False)
            self.tooltip_text.setVisible(False)
            for dot in self.crosshair_dots:
                try:
                    self.plot_widget.removeItem(dot)
                except Exception:
                    pass
            self.crosshair_dots.clear()
            return

        mouse_point = vb.mapSceneToView(pos)
        x = mouse_point.x()

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

        unit = "mA" if self.type_current.isChecked() else "mV"
        lines = [f"Time: {x:.2f} s"]

        for idx, (label, ch_data) in enumerate(self.datalog_data.items()):
            times = ch_data["time"]
            values = ch_data["values"]
            if not times:
                continue

            i = self._find_nearest_index(times, x)
            if i is not None:
                val = values[i]
                color = CHANNEL_COLORS[idx % len(CHANNEL_COLORS)]
                lines.append(f"<span style='color:{color}'>{label.strip()} : {val:.0f} {unit}</span>")

                dot = pg.ScatterPlotItem(
                    [times[i]], [val], size=10,
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

    def _init_ui_elements(self):
        self._update_connect_btn(self.connect_btn_a, False)
        self._update_connect_btn(self.connect_btn_b, False)
        self._update_recording_button_state(False)

    def _bind_signals(self):
        self.search_btn_a.clicked.connect(lambda: self._on_search("a"))
        self.connect_btn_a.clicked.connect(lambda: self._on_connect_or_disconnect("a"))
        self.search_btn_b.clicked.connect(lambda: self._on_search("b"))
        self.connect_btn_b.clicked.connect(lambda: self._on_connect_or_disconnect("b"))

        self.start_btn.clicked.connect(self._on_start_or_stop_recording)
        self.export_btn.clicked.connect(self._on_export)
        self.import_btn.clicked.connect(self._on_import)

        self.box_zoom_btn.clicked.connect(self._toggle_box_zoom)
        self.reset_view_btn.clicked.connect(self._reset_view)
        self.marker_a_btn.clicked.connect(lambda: self._set_marker_mode("A"))
        self.marker_b_btn.clicked.connect(lambda: self._set_marker_mode("B"))
        self.clear_markers_btn.clicked.connect(self._clear_markers)

        self.x_scale_edit.returnPressed.connect(self._apply_scale)
        self.y_scale_edit.returnPressed.connect(self._apply_scale)

        self.add_label_btn.clicked.connect(self._add_custom_label)

        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        self.type_group.buttonClicked.connect(self._on_record_type_changed)

    def _is_8ch_mode(self):
        return self.mode_8ch.isChecked()

    def _update_connect_btn(self, btn, connected):
        btn.setProperty("connected", "true" if connected else "false")
        btn.setText("\u21BA  Disconnect" if connected else "\U0001F517  Connect")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

    def _update_recording_button_state(self, recording):
        self.is_recording = recording
        self.start_btn.setProperty("running", "true" if recording else "false")
        self.start_btn.setText(
            "\u25A0  Stop Recording" if recording else "\u25B7  Start Recording"
        )
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        self.start_btn.update()

    def _on_mode_changed(self):
        is_8ch = self._is_8ch_mode()

        if is_8ch:
            self.connection_card_a.title_label.setText("\u26A1  CONNECTION \u2014 Unit A")
            self.connection_card_b.show()
            self.unit_a_ch_label.setText("Unit A Channels")
            self.unit_b_ch_label.show()
            self.ch_row_b_widget.show()
        else:
            self.connection_card_a.title_label.setText("\u26A1  CONNECTION")
            self.connection_card_b.hide()
            self.unit_a_ch_label.setText("Active Channels")
            self.unit_b_ch_label.hide()
            self.ch_row_b_widget.hide()

    def _on_record_type_changed(self):
        if self.type_current.isChecked():
            self.y_scale_edit.setText("50")
            self.y_scale_label.setText("Y Scale (mA/div):")
            self.plot_widget.setLabel("left", "Current (mA)", color="#8eb0e3")
            self.analysis_title_label.setText("Average Current between A & B")
        else:
            self.y_scale_edit.setText("100")
            self.y_scale_label.setText("Y Scale (mV/div):")
            self.plot_widget.setLabel("left", "Voltage (mV)", color="#8eb0e3")
            self.analysis_title_label.setText("Average Voltage between A & B")

    def _on_search(self, unit):
        if DEBUG_FLAG:
            combo = self.visa_combo_a if unit == "a" else self.visa_combo_b
            combo.clear()
            combo.addItem("DEBUG::MOCK::N6705C")
            return
        if unit == "a":
            self.search_btn_a.setEnabled(False)
            self.search_timer_a.start(100)
        else:
            self.search_btn_b.setEnabled(False)
            self.search_timer_b.start(100)

    def _search_devices(self, unit):
        combo = self.visa_combo_a if unit == "a" else self.visa_combo_b
        search_btn = self.search_btn_a if unit == "a" else self.search_btn_b
        try:
            if self.rm is None:
                try:
                    self.rm = pyvisa.ResourceManager()
                except Exception:
                    self.rm = pyvisa.ResourceManager("@py")

            resources = list(self.rm.list_resources()) or []
            n6705c_devices = []
            for dev in resources:
                try:
                    instr = self.rm.open_resource(dev, timeout=1000)
                    idn = instr.query("*IDN?").strip()
                    instr.close()
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception:
                    pass

            combo.clear()
            if n6705c_devices:
                for d in n6705c_devices:
                    combo.addItem(d)
            else:
                for d in resources:
                    combo.addItem(d)
        except Exception:
            pass
        finally:
            search_btn.setEnabled(True)

    def _on_connect_or_disconnect(self, unit):
        if unit == "a":
            if self.is_connected_a:
                self._disconnect_unit("a")
            else:
                self._connect_unit("a")
        else:
            if self.is_connected_b:
                self._disconnect_unit("b")
            else:
                self._connect_unit("b")

    def _connect_unit(self, unit):
        if unit == "a":
            if DEBUG_FLAG:
                self.n6705c_a = _MockN6705C()
                self.is_connected_a = True
                self._update_connect_btn(self.connect_btn_a, True)
                return
            resource = self.visa_combo_a.currentText().strip()
            if not resource:
                return
            try:
                self.n6705c_a = N6705C(resource)
                self.is_connected_a = True
                self._update_connect_btn(self.connect_btn_a, True)
            except Exception:
                self.is_connected_a = False
                self._update_connect_btn(self.connect_btn_a, False)
        else:
            if DEBUG_FLAG:
                self.n6705c_b = _MockN6705C()
                self.is_connected_b = True
                self._update_connect_btn(self.connect_btn_b, True)
                return
            resource = self.visa_combo_b.currentText().strip()
            if not resource:
                return
            try:
                self.n6705c_b = N6705C(resource)
                self.is_connected_b = True
                self._update_connect_btn(self.connect_btn_b, True)
            except Exception:
                self.is_connected_b = False
                self._update_connect_btn(self.connect_btn_b, False)

        self.connection_status_changed.emit(self.is_connected_a)

    def _disconnect_unit(self, unit):
        try:
            if unit == "a" and self.n6705c_a:
                self.n6705c_a.disconnect()
                self.n6705c_a = None
                self.is_connected_a = False
                self._update_connect_btn(self.connect_btn_a, False)
            elif unit == "b" and self.n6705c_b:
                self.n6705c_b.disconnect()
                self.n6705c_b = None
                self.is_connected_b = False
                self._update_connect_btn(self.connect_btn_b, False)
        except Exception:
            pass
        self.connection_status_changed.emit(self.is_connected_a)

    def _on_start_or_stop_recording(self):
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if not self.is_connected_a or not self.n6705c_a:
            return

        active_a = [i + 1 for i, cb in enumerate(self.ch_checkboxes_a) if cb.isChecked()]

        n6705c_list = [self.n6705c_a]
        channels_per_unit = [active_a]
        unit_labels = ["A"]

        if self._is_8ch_mode():
            active_b = [i + 1 for i, cb in enumerate(self.ch_checkboxes_b) if cb.isChecked()]
            if active_b and self.is_connected_b and self.n6705c_b:
                n6705c_list.append(self.n6705c_b)
                channels_per_unit.append(active_b)
                unit_labels.append("B")

        total_active = sum(len(c) for c in channels_per_unit)
        if total_active == 0:
            return

        record_type = "current" if self.type_current.isChecked() else "voltage"

        try:
            sample_period = float(self.sample_period_edit.text())
        except ValueError:
            sample_period = 1000.0

        try:
            monitor_time = float(self.monitor_time_edit.text())
        except ValueError:
            monitor_time = 10.0

        if not self._is_8ch_mode():
            unit_labels = [""]

        self._update_recording_button_state(True)

        self._record_thread = QThread()
        self._record_worker = _DatalogWorker(
            n6705c_list, channels_per_unit, unit_labels,
            record_type, sample_period, monitor_time,
            debug=DEBUG_FLAG
        )
        self._record_worker.moveToThread(self._record_thread)

        self._record_thread.started.connect(self._record_worker.run)
        self._record_worker.data_ready.connect(self._on_data_ready)
        self._record_worker.finished.connect(self._record_thread.quit)
        self._record_worker.error.connect(self._on_recording_error)
        self._record_thread.finished.connect(self._on_recording_finished)
        self._record_thread.finished.connect(self._record_worker.deleteLater)
        self._record_thread.finished.connect(self._record_thread.deleteLater)

        self._record_thread.start()

    def _stop_recording(self):
        if self._record_worker:
            self._record_worker.stop()
        self._update_recording_button_state(False)

    def _on_data_ready(self, data):
        self.datalog_data = data
        self._refresh_plot()

    def _on_recording_finished(self):
        self._update_recording_button_state(False)
        self._record_worker = None
        self._record_thread = None

    def _on_recording_error(self, msg):
        self._update_recording_button_state(False)

    def _refresh_plot(self):
        self.plot_widget.clear()
        self.plot_curves.clear()
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_region = None

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

        self.legend = self.plot_widget.addLegend(
            offset=(-10, 340),
            labelTextColor="#8eb0e3",
        )
        self.legend.setBrush(pg.mkBrush(7, 17, 39, 200))
        self.legend.setPen(pg.mkPen(color="#1a2b52"))

        for idx, (label, ch_data) in enumerate(self.datalog_data.items()):
            color = CHANNEL_COLORS[idx % len(CHANNEL_COLORS)]
            pen = pg.mkPen(color=color, width=1.5)
            curve = self.plot_widget.plot(
                ch_data["time"], ch_data["values"],
                pen=pen, name=label.strip()
            )
            self.plot_curves[label] = curve

        if self.datalog_data:
            all_times = []
            all_vals = []
            for ch_data in self.datalog_data.values():
                all_times.extend(ch_data["time"])
                all_vals.extend(ch_data["values"])

            if all_times and all_vals:
                self.plot_widget.setXRange(min(all_times), max(all_times))
                min_v = min(all_vals)
                max_v = max(all_vals)
                pad = (max_v - min_v) * 0.1 if max_v > min_v else 50
                self.plot_widget.setYRange(min_v - pad, max_v + pad)

        self._restore_markers()
        self._restore_label_lines()
        self._update_marker_analysis()
        self._refresh_label_ch_combo()

    def _reset_view(self):
        if not self.datalog_data:
            self.plot_widget.setXRange(0, 10)
            self.plot_widget.setYRange(0, 2000)
            return

        all_times = []
        all_vals = []
        for ch_data in self.datalog_data.values():
            all_times.extend(ch_data["time"])
            all_vals.extend(ch_data["values"])

        if all_times and all_vals:
            self.plot_widget.setXRange(min(all_times), max(all_times))
            min_v = min(all_vals)
            max_v = max(all_vals)
            pad = (max_v - min_v) * 0.1 if max_v > min_v else 50
            self.plot_widget.setYRange(min_v - pad, max_v + pad)

    def _toggle_box_zoom(self):
        self.box_zoom_enabled = not self.box_zoom_enabled
        if self.box_zoom_enabled:
            self.box_zoom_btn.setText("\u2316 Box Zoom: ON")
            self.plot_widget.setMouseEnabled(x=True, y=True)
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.RectMode)
        else:
            self.box_zoom_btn.setText("\u2316 Box Zoom: OFF")
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.PanMode)

    def _set_marker_mode(self, marker):
        self._pending_marker = marker

    def _on_chart_clicked(self, event):
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

        self._pending_marker = None
        self._update_marker_region()
        self._update_marker_analysis()

    def _place_marker_a(self, x):
        if self.marker_a_line:
            self.plot_widget.removeItem(self.marker_a_line)
        self.marker_a_pos = x
        self.marker_a_line = pg.InfiniteLine(
            pos=x, angle=90, movable=True,
            pen=pg.mkPen(color="#d4a514", width=2, style=Qt.DashLine),
            label=f"A",
            labelOpts={"color": "#d4a514", "position": 0.98}
        )
        self.marker_a_line.sigPositionChanged.connect(
            lambda line: self._on_marker_moved("A", line.value())
        )
        self.plot_widget.addItem(self.marker_a_line)
        self.marker_a_btn.setText(f"Set Marker A ({x:.4f}s)")

    def _place_marker_b(self, x):
        if self.marker_b_line:
            self.plot_widget.removeItem(self.marker_b_line)
        self.marker_b_pos = x
        self.marker_b_line = pg.InfiniteLine(
            pos=x, angle=90, movable=True,
            pen=pg.mkPen(color="#4cc9f0", width=2, style=Qt.DashLine),
            label=f"B",
            labelOpts={"color": "#4cc9f0", "position": 0.98}
        )
        self.marker_b_line.sigPositionChanged.connect(
            lambda line: self._on_marker_moved("B", line.value())
        )
        self.plot_widget.addItem(self.marker_b_line)
        self.marker_b_btn.setText(f"Set Marker B ({x:.4f}s)")

    def _on_marker_moved(self, which, value):
        if which == "A":
            self.marker_a_pos = value
            self.marker_a_btn.setText(f"Set Marker A ({value:.4f}s)")
        else:
            self.marker_b_pos = value
            self.marker_b_btn.setText(f"Set Marker B ({value:.4f}s)")
        self._update_marker_region()
        self._update_marker_analysis()

    def _update_marker_region(self):
        if self.marker_region:
            self.plot_widget.removeItem(self.marker_region)
            self.marker_region = None

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

    def _clear_markers(self):
        if self.marker_a_line:
            self.plot_widget.removeItem(self.marker_a_line)
            self.marker_a_line = None
        if self.marker_b_line:
            self.plot_widget.removeItem(self.marker_b_line)
            self.marker_b_line = None
        if self.marker_region:
            self.plot_widget.removeItem(self.marker_region)
            self.marker_region = None
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_btn.setText("Set Marker A")
        self.marker_b_btn.setText("Set Marker B")
        self._update_marker_analysis()

    def _restore_markers(self):
        if self.marker_a_pos is not None:
            self._place_marker_a(self.marker_a_pos)
        if self.marker_b_pos is not None:
            self._place_marker_b(self.marker_b_pos)
        self._update_marker_region()

    def _update_marker_analysis(self):
        while self.analysis_cards_layout.count():
            item = self.analysis_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if self.marker_a_pos is None or self.marker_b_pos is None:
            self.analysis_hint_label.setVisible(True)
            self.analysis_delta_label.setText("")
            return

        self.analysis_hint_label.setVisible(False)

        t1 = min(self.marker_a_pos, self.marker_b_pos)
        t2 = max(self.marker_a_pos, self.marker_b_pos)
        delta = t2 - t1

        unit = "mA" if self.type_current.isChecked() else "mV"

        for idx, (label, ch_data) in enumerate(self.datalog_data.items()):
            times = ch_data["time"]
            values = ch_data["values"]
            segment = [
                v for t, v in zip(times, values) if t1 <= t <= t2
            ]
            if not segment:
                continue

            avg = sum(segment) / len(segment)
            color = CHANNEL_COLORS[idx % len(CHANNEL_COLORS)]

            card = QFrame()
            card.setObjectName("chResultCard")
            card.setMinimumWidth(100)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(4)
            card_layout.setAlignment(Qt.AlignCenter)

            name_label = QLabel(label.strip())
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet(
                f"color: {color}; font-size: 12px; font-weight: 700;"
            )
            card_layout.addWidget(name_label)

            val_label = QLabel(f"{avg:.0f}")
            val_label.setAlignment(Qt.AlignCenter)
            val_label.setStyleSheet(
                "color: #f4f7ff; font-size: 20px; font-weight: 800;"
            )
            card_layout.addWidget(val_label)

            unit_label = QLabel(unit)
            unit_label.setAlignment(Qt.AlignCenter)
            unit_label.setStyleSheet(
                "color: #7da2d6; font-size: 11px;"
            )
            card_layout.addWidget(unit_label)

            self.analysis_cards_layout.addWidget(card)

        self.analysis_delta_label.setText(f"\u0394t = {delta:.2f} s")

    def _apply_scale(self):
        try:
            x_div = float(self.x_scale_edit.text())
        except ValueError:
            x_div = 1.0
        try:
            y_div = float(self.y_scale_edit.text())
        except ValueError:
            y_div = 50.0

        x_range = self.plot_widget.viewRange()[0]
        y_range = self.plot_widget.viewRange()[1]

        x_center = (x_range[0] + x_range[1]) / 2
        y_center = (y_range[0] + y_range[1]) / 2

        num_divs = 10
        half_x = x_div * num_divs / 2
        half_y = y_div * num_divs / 2

        self.plot_widget.setXRange(x_center - half_x, x_center + half_x)
        self.plot_widget.setYRange(y_center - half_y, y_center + half_y)

        self.x_scale_edit.setText(f"{x_div}")
        self.y_scale_edit.setText(f"{y_div}")

    def _on_range_changed(self):
        vr = self.plot_widget.viewRange()
        x_span = vr[0][1] - vr[0][0]
        y_span = vr[1][1] - vr[1][0]

        num_divs = 10
        x_div = x_span / num_divs
        y_div = y_span / num_divs

        self.x_scale_edit.blockSignals(True)
        self.y_scale_edit.blockSignals(True)

        if x_div >= 1:
            self.x_scale_edit.setText(f"{x_div:.4g}")
        else:
            self.x_scale_edit.setText(f"{x_div:.6g}")

        if y_div >= 1:
            self.y_scale_edit.setText(f"{y_div:.4g}")
        else:
            self.y_scale_edit.setText(f"{y_div:.6g}")

        self.x_scale_edit.blockSignals(False)
        self.y_scale_edit.blockSignals(False)

    def _refresh_label_ch_combo(self):
        current = self.label_ch_combo.currentText()
        self.label_ch_combo.clear()
        for label in self.datalog_data.keys():
            self.label_ch_combo.addItem(label.strip())
        idx = self.label_ch_combo.findText(current)
        if idx >= 0:
            self.label_ch_combo.setCurrentIndex(idx)

    def _add_custom_label(self):
        ch_name = self.label_ch_combo.currentText().strip()
        time_str = self.label_time_edit.text().strip()
        text = self.label_text_edit.text().strip()
        if not time_str or not text or not ch_name:
            return
        try:
            t = float(time_str)
        except ValueError:
            return

        self.custom_labels.append({"time": t, "text": text, "channel": ch_name})
        self._refresh_labels_display()
        self._draw_label_item(t, text, ch_name)

        self.label_time_edit.clear()
        self.label_text_edit.clear()

    def _get_value_at_time(self, ch_name, t):
        for label, ch_data in self.datalog_data.items():
            if label.strip() == ch_name:
                times = ch_data["time"]
                values = ch_data["values"]
                if not times:
                    return None
                idx = self._find_nearest_index(times, t)
                if idx is not None:
                    return values[idx]
        return None

    def _get_channel_color(self, ch_name):
        for idx, label in enumerate(self.datalog_data.keys()):
            if label.strip() == ch_name:
                return (
                    CHANNEL_COLORS[idx % len(CHANNEL_COLORS)],
                    CHANNEL_LABEL_COLORS[idx % len(CHANNEL_LABEL_COLORS)],
                )
        return ("#d4a514", "#ffe566")

    def _draw_label_item(self, t, text, ch_name):
        color, light_color = self._get_channel_color(ch_name)
        y_val = self._get_value_at_time(ch_name, t)
        if y_val is None:
            y_val = self.plot_widget.viewRange()[1][1] * 0.9

        arrow = pg.ArrowItem(
            pos=(t, y_val),
            angle=-90,
            tipAngle=30,
            headLen=14,
            tailLen=12,
            tailWidth=3,
            pen=pg.mkPen(color=color, width=2),
            brush=pg.mkBrush(color=color),
        )
        arrow.setZValue(50)
        self.plot_widget.addItem(arrow)

        label_item = pg.TextItem(
            html=f"<div style='background:#0a1733ee; padding:4px 8px; "
                 f"border: 1px solid {color}; border-radius:4px; "
                 f"font-size:16px; font-weight:700; color:{light_color};'>"
                 f"{text}</div>",
            anchor=(0.5, 1),
        )
        label_item.setZValue(50)
        label_item.setPos(t, y_val)
        self.plot_widget.addItem(label_item)

        self.custom_label_lines.append({"arrow": arrow, "text_item": label_item})

    def _restore_label_lines(self):
        for item in self.custom_label_lines:
            try:
                if isinstance(item, dict):
                    self.plot_widget.removeItem(item["arrow"])
                    self.plot_widget.removeItem(item["text_item"])
                else:
                    self.plot_widget.removeItem(item)
            except Exception:
                pass
        self.custom_label_lines.clear()
        for lbl in self.custom_labels:
            self._draw_label_item(lbl["time"], lbl["text"], lbl.get("channel", ""))

    def _refresh_labels_display(self):
        if not self.custom_labels:
            self.labels_list_label.setText("No labels added.")
            return
        parts = []
        for lbl in self.custom_labels:
            ch = lbl.get("channel", "")
            parts.append(f"  [{ch}] {lbl['time']}s : {lbl['text']}")
        self.labels_list_label.setText("\n".join(parts))

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Datalog", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if not lines:
                return

            header = lines[0].strip().split(",")
            if len(header) < 2:
                return

            channel_names = [h.strip() for h in header[1:]]

            all_data = {}
            for name in channel_names:
                all_data[name] = {"time": [], "values": []}

            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(",")
                if len(parts) < 2:
                    continue

                try:
                    t = float(parts[0])
                except ValueError:
                    continue

                for col_idx, name in enumerate(channel_names):
                    try:
                        val = float(parts[1 + col_idx])
                    except (ValueError, IndexError):
                        val = 0.0
                    all_data[name]["time"].append(t)
                    all_data[name]["values"].append(val)

            empty_keys = [k for k, v in all_data.items() if not v["time"]]
            for k in empty_keys:
                del all_data[k]

            if not all_data:
                return

            self.datalog_data = all_data
            self._refresh_plot()
        except Exception:
            pass

    def _on_export(self):
        if not self.datalog_data:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Datalog", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        try:
            max_len = max(len(d["time"]) for d in self.datalog_data.values())
            labels = list(self.datalog_data.keys())

            with open(path, "w", newline="") as f:
                header = "Time(s)," + ",".join(labels)
                f.write(header + "\n")

                for i in range(max_len):
                    row_parts = []
                    first = list(self.datalog_data.values())[0]
                    if i < len(first["time"]):
                        row_parts.append(f"{first['time'][i]:.6f}")
                    else:
                        row_parts.append("")

                    for lbl in labels:
                        ch = self.datalog_data[lbl]
                        if i < len(ch["values"]):
                            row_parts.append(f"{ch['values'][i]:.9f}")
                        else:
                            row_parts.append("")

                    f.write(",".join(row_parts) + "\n")
        except Exception:
            pass