#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU DCDC Efficiency测试UI组件
暗色卡片式重构版本（PySide6）
"""

import sys
import os
import threading
from typing import Any
from ui.resource_path import get_resource_base
sys.path.append(get_resource_base())

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QSpinBox, QDoubleSpinBox, QFrame, QTextEdit,
    QSizePolicy, QButtonGroup, QFileDialog, QProgressBar,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem,
    QScrollArea
)
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QMargins, QPointF
from PySide6.QtGui import QFont, QCursor
import time

from instruments.power.keysight.n6705c import N6705C
from ui.styles import SCROLLBAR_STYLE, START_BTN_STYLE, update_start_btn_state
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.chamber_module_frame import ChamberConnectionMixin
from debug_config import DEBUG_MOCK
from ui.theme import FONT_MONO
from core.pmu_test.dcdc import (
    DCDCEfficiencyTestThread, DCDCVinSweepTestThread, DCDCTempSweepTestThread,
    savgol_smooth as _savgol_smooth,
)
from core.ai.page_contract import (
    CAP_APPLY_CONFIG,
    CAP_GET_CONFIG,
    CAP_GET_RESULT,
    CAP_START_TEST,
    CAP_STOP_TEST,
)
from log_config import get_logger

_logger = get_logger(__name__)

# AI 回填可视化（AIAssist_PageScopedControlPlan.md §4.2 / Phase 3）：
# 被 AI 修改的控件临时高亮边框色 + 持续时长。色值与页面 statusOk 一致，
# 仅改 border 颜色（宽度沿用页面 QSS 的 1px，避免布局抖动）。
_AI_HIGHLIGHT_QSS = "border: 1px solid #15d1a3;"
_AI_HIGHLIGHT_MS = 1500


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
            all_x = []
            all_y = []
            for s in ch.series():
                if not s.isVisible():
                    continue
                for p in s.points():
                    all_x.append(p.x())
                    all_y.append(p.y())
            if not all_x or not all_y:
                return
            min_x, max_x = min(all_x), max(all_x)
            min_y, max_y = min(all_y), max(all_y)

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
            font = QFont("JetBrains Mono", 9)
            font.setStyleHint(QFont.Monospace)
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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 10, 8)
        self.main_layout.setSpacing(8)

        if title:
            self.title_row = QHBoxLayout()
            self.title_row.setSpacing(8)
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.title_row.addWidget(self.title_label)
            self.title_row.addStretch()
            self.main_layout.addLayout(self.title_row)
        else:
            self.title_label = None
            self.title_row = None


class SegmentedButton(QPushButton):
    """分段按钮"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("segmentedButton")




class PMUDCDCEfficiencyUI(N6705CConnectionMixin, ChamberConnectionMixin, QWidget):
    """PMU DCDC Efficiency测试UI组件"""

    connection_status_changed = Signal(bool)
    # 测试结束 → AI 异步动作回灌续跑（与 Orchestrator 同契约，§4 / S3-2）。
    # MainWindow._ai_on_sequence_finished_resume 监听本信号，回灌 pending 任务。
    sequence_execution_finished = Signal(bool, str)

    def __init__(self, n6705c_top=None, chamber_ui=None, instrument_manager=None):
        super().__init__()

        self._instrument_manager = instrument_manager
        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)
        self.init_chamber_connection(chamber_ui, instrument_manager=instrument_manager)

        self.is_test_running = False
        self.test_thread = None
        self._export_data = []

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
                background-color: #020817;
                color: #dbe7ff;
            }

            QWidget#leftPanelInner {
                background-color: transparent;
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
                border-radius: 16px;
            }

            QFrame#cardFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 12px;
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
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px; height: 0px; border: none;
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
                border-radius: 8px;
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
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
            }
""" + START_BTN_STYLE + """
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
                border-radius: 6px;
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
                border-radius: 8px;
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
                font-family: """ + FONT_MONO + """;
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
                border-radius: 12px;
            }
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.page_title = QLabel("DCDC Efficiency Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel("Configure and execute automated DCDC efficiency validation sequences.")
        self.page_subtitle.setObjectName("pageSubtitle")

        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_subtitle)
        root_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)
        root_layout.addLayout(content_layout, 1)

        left_wrapper = QVBoxLayout()
        left_wrapper.setContentsMargins(0, 0, 0, 0)
        left_wrapper.setSpacing(8)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.left_scroll.setFixedWidth(320)
        self.left_scroll.setObjectName("leftScrollArea")
        self.left_scroll.setStyleSheet("""
            QScrollArea#leftScrollArea {
                background-color: #08132d;
                border: 1px solid #16274d;
                border-radius: 16px;
            }
        """ + SCROLLBAR_STYLE)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("leftPanelInner")

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)

        self.test_item_card = CardFrame("Test Item")
        self._build_test_item_card()
        left_layout.addWidget(self.test_item_card)

        self.connection_card = CardFrame("N6705C ")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.chamber_card = CardFrame("Chamber")
        self._build_chamber_card()
        left_layout.addWidget(self.chamber_card)

        self.test_config_card = CardFrame("Test Config")
        self._build_test_config_card()
        left_layout.addWidget(self.test_config_card)

        self.channel_card = CardFrame("Channel Selection")
        self._build_channel_card()
        left_layout.addWidget(self.channel_card)

        self.measurement_card = CardFrame("Measurement Settings")
        self._build_measurement_card()
        left_layout.addWidget(self.measurement_card)

        left_layout.addStretch()

        self.left_scroll.setWidget(self.left_panel)
        left_wrapper.addWidget(self.left_scroll, 1)

        self.start_test_btn = QPushButton("▶ START SEQUENCE")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_wrapper.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("■ STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()

        content_layout.addLayout(left_wrapper)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        content_layout.addLayout(right_layout, 1)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartContainer")
        chart_outer_layout = QVBoxLayout(self.chart_frame)
        chart_outer_layout.setContentsMargins(16, 16, 16, 16)
        chart_outer_layout.setSpacing(12)

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

        self.stat_container = QFrame()
        self.stat_container.setStyleSheet("QFrame { background: transparent; border: none; }")
        stat_layout = QHBoxLayout(self.stat_container)
        stat_layout.setContentsMargins(0, 0, 0, 0)
        stat_layout.setSpacing(8)

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

        chart_outer_layout.addWidget(self.stat_container)

        right_splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            self.chart_frame, show_progress=True, stretch=(4, 1)
        )
        self.log_edit = self.execution_logs.log_edit
        self.progress_bar = self.execution_logs.progress_bar
        self.progress_text_label = self.execution_logs.progress_text_label
        self.clear_log_btn = self.execution_logs.clear_log_btn
        right_layout.addWidget(right_splitter, 1)

    def _build_connection_card(self):
        self.build_n6705c_connection_widgets(
            self.connection_card.main_layout,
            title_row=self.connection_card.title_row,
        )

    def _build_test_item_card(self):
        layout = self.test_item_card.main_layout

        self.test_item_combo = DarkComboBox()
        self.test_item_combo.addItems([
            "Efficiency Curve",
            "VIN Sweep",
            "Temperature Sweep",
        ])
        layout.addWidget(self.test_item_combo)

    def _on_test_item_changed(self):
        item = self.test_item_combo.currentText()
        is_vin = (item == "VIN Sweep")
        is_temp = (item == "Temperature Sweep")
        is_eff = (item == "Efficiency Curve")

        if hasattr(self, 'chamber_card'):
            self.chamber_card.setVisible(is_temp)
        if hasattr(self, 'vin_sweep_container'):
            self.vin_sweep_container.setVisible(is_vin)
        if hasattr(self, 'temp_sweep_container'):
            self.temp_sweep_container.setVisible(is_temp)
        if hasattr(self, 'stat_container'):
            self.stat_container.setVisible(is_eff)

    def _build_test_config_card(self):
        layout = self.test_config_card.main_layout

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

        self.test_config_card.title_row.addWidget(self.seg_container)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

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

        self.lbl_avg_cnt = QLabel("Average CNT")
        self.lbl_avg_cnt.setObjectName("fieldLabel")
        self.average_cnt_spin = QSpinBox()
        self.average_cnt_spin.setRange(1, 100)
        self.average_cnt_spin.setValue(1)
        self.average_cnt_spin.setToolTip(
            "Number of measurements to average per point.\n"
            "1 = single measurement (fastest),\n"
            "N = average of N measurements (more accurate)."
        )

        grid.addWidget(self.lbl_avg_cnt, 4, 0, 1, 2)
        grid.addWidget(self.average_cnt_spin, 5, 0, 1, 2)

        layout.addLayout(grid)

        self._on_sweep_mode_changed()

        self.vin_sweep_container = QFrame()
        self.vin_sweep_container.setStyleSheet("QFrame { background: transparent; border: none; }")
        vin_grid = QGridLayout(self.vin_sweep_container)
        vin_grid.setContentsMargins(0, 0, 0, 0)
        vin_grid.setHorizontalSpacing(10)
        vin_grid.setVerticalSpacing(6)

        self.lbl_vin_start = QLabel("VIN Start (V)")
        self.lbl_vin_start.setObjectName("fieldLabel")
        self.vin_start_spin = QDoubleSpinBox()
        self.vin_start_spin.setRange(0.0, 60.0)
        self.vin_start_spin.setDecimals(2)
        self.vin_start_spin.setSingleStep(0.1)
        self.vin_start_spin.setValue(3.0)

        self.lbl_vin_end = QLabel("VIN End (V)")
        self.lbl_vin_end.setObjectName("fieldLabel")
        self.vin_end_spin = QDoubleSpinBox()
        self.vin_end_spin.setRange(0.0, 60.0)
        self.vin_end_spin.setDecimals(2)
        self.vin_end_spin.setSingleStep(0.1)
        self.vin_end_spin.setValue(4.2)

        self.lbl_vin_step = QLabel("VIN Step (V)")
        self.lbl_vin_step.setObjectName("fieldLabel")
        self.vin_step_spin = QDoubleSpinBox()
        self.vin_step_spin.setRange(0.01, 10.0)
        self.vin_step_spin.setDecimals(2)
        self.vin_step_spin.setSingleStep(0.1)
        self.vin_step_spin.setValue(0.1)

        vin_grid.addWidget(self.lbl_vin_start, 0, 0)
        vin_grid.addWidget(self.vin_start_spin, 1, 0)
        vin_grid.addWidget(self.lbl_vin_end, 0, 1)
        vin_grid.addWidget(self.vin_end_spin, 1, 1)
        vin_grid.addWidget(self.lbl_vin_step, 2, 0)
        vin_grid.addWidget(self.vin_step_spin, 3, 0)

        layout.addWidget(self.vin_sweep_container)

        self.temp_sweep_container = QFrame()
        self.temp_sweep_container.setStyleSheet("QFrame { background: transparent; border: none; }")
        temp_grid = QGridLayout(self.temp_sweep_container)
        temp_grid.setContentsMargins(0, 0, 0, 0)
        temp_grid.setHorizontalSpacing(10)
        temp_grid.setVerticalSpacing(6)

        self.lbl_temp_start = QLabel("Temp Start (°C)")
        self.lbl_temp_start.setObjectName("fieldLabel")
        self.temp_start_spin = QDoubleSpinBox()
        self.temp_start_spin.setRange(-55.0, 200.0)
        self.temp_start_spin.setDecimals(1)
        self.temp_start_spin.setSingleStep(5)
        self.temp_start_spin.setValue(-40.0)

        self.lbl_temp_end = QLabel("Temp End (°C)")
        self.lbl_temp_end.setObjectName("fieldLabel")
        self.temp_end_spin = QDoubleSpinBox()
        self.temp_end_spin.setRange(-55.0, 200.0)
        self.temp_end_spin.setDecimals(1)
        self.temp_end_spin.setSingleStep(5)
        self.temp_end_spin.setValue(85.0)

        self.lbl_temp_step = QLabel("Temp Step (°C)")
        self.lbl_temp_step.setObjectName("fieldLabel")
        self.temp_step_spin = QDoubleSpinBox()
        self.temp_step_spin.setRange(1.0, 100.0)
        self.temp_step_spin.setDecimals(1)
        self.temp_step_spin.setSingleStep(5)
        self.temp_step_spin.setValue(25.0)

        self.lbl_temp_fixed_load = QLabel("Fixed Load (A)")
        self.lbl_temp_fixed_load.setObjectName("fieldLabel")
        self.temp_fixed_load_spin = QDoubleSpinBox()
        self.temp_fixed_load_spin.setRange(0.0, 10.0)
        self.temp_fixed_load_spin.setDecimals(3)
        self.temp_fixed_load_spin.setSingleStep(0.01)
        self.temp_fixed_load_spin.setValue(0.1)

        temp_grid.addWidget(self.lbl_temp_start, 0, 0)
        temp_grid.addWidget(self.temp_start_spin, 1, 0)
        temp_grid.addWidget(self.lbl_temp_end, 0, 1)
        temp_grid.addWidget(self.temp_end_spin, 1, 1)
        temp_grid.addWidget(self.lbl_temp_step, 2, 0)
        temp_grid.addWidget(self.temp_step_spin, 3, 0)
        temp_grid.addWidget(self.lbl_temp_fixed_load, 2, 1)
        temp_grid.addWidget(self.temp_fixed_load_spin, 3, 1)

        layout.addWidget(self.temp_sweep_container)

    def _build_measurement_card(self):
        layout = self.measurement_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        self.lbl_settle_time = QLabel("Settle Time (ms)")
        self.lbl_settle_time.setObjectName("fieldLabel")
        self.settle_time_spin = QSpinBox()
        self.settle_time_spin.setRange(0, 10000)
        self.settle_time_spin.setValue(3)
        self.settle_time_spin.setSingleStep(10)
        self.settle_time_spin.setToolTip(
            "Wait time after setting load current before measurement.\n"
            "0~3ms = fastest (original), 50~200ms = recommended for accuracy."
        )

        self.lbl_sampling = QLabel("Sampling Method")
        self.lbl_sampling.setObjectName("fieldLabel")
        self.sampling_method_combo = DarkComboBox()
        self.sampling_method_combo.addItems(["Instant MEAS", "DataLogger"])

        self.lbl_dlog_duration = QLabel("DataLog Duration (s)")
        self.lbl_dlog_duration.setObjectName("fieldLabel")
        self.dlog_duration_spin = QDoubleSpinBox()
        self.dlog_duration_spin.setRange(0.1, 30.0)
        self.dlog_duration_spin.setDecimals(1)
        self.dlog_duration_spin.setSingleStep(0.5)
        self.dlog_duration_spin.setValue(1.0)
        self.dlog_duration_spin.setToolTip(
            "Duration for DataLogger sampling per point.\n"
            "Longer = more accurate average, slower test."
        )

        grid.addWidget(self.lbl_settle_time, 0, 0)
        grid.addWidget(self.settle_time_spin, 1, 0)
        grid.addWidget(self.lbl_sampling, 0, 1)
        grid.addWidget(self.sampling_method_combo, 1, 1)
        grid.addWidget(self.lbl_dlog_duration, 2, 0, 1, 2)
        grid.addWidget(self.dlog_duration_spin, 3, 0, 1, 2)

        layout.addLayout(grid)

    def _on_sampling_method_changed(self):
        is_dlog = (self.sampling_method_combo.currentText() == "DataLogger")
        self.lbl_dlog_duration.setVisible(is_dlog)
        self.dlog_duration_spin.setVisible(is_dlog)

    def _build_chamber_card(self):
        layout = self.chamber_card.main_layout
        self.build_chamber_connection_widgets(layout)

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
                border-radius: 12px;
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
        self._update_n6705c_connect_button_state(False)
        self.append_log("[SYSTEM] Ready. Waiting for instrument connection.")
        self.append_log("[TEST] UI initialized successfully.")
        self.set_progress(0)
        self._on_test_item_changed()
        self._on_sampling_method_changed()

    def _bind_signals(self):
        self.bind_n6705c_signals()
        self.bind_chamber_signals()
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
        self.test_item_combo.currentTextChanged.connect(self._on_test_item_changed)
        self.sampling_method_combo.currentTextChanged.connect(self._on_sampling_method_changed)

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def _on_clear_log(self):
        self.execution_logs.clear_log()

    def set_progress(self, value: int):
        self.execution_logs.set_progress(value)

    def _on_start_test(self):
        if not self.is_connected or self.n6705c is None:
            self.append_log("[ERROR] Not connected to instrument.")
            return
        if self.is_test_running:
            return
        self._export_data = []
        self._test_stop_requested = False
        self.set_test_running(True)
        self.set_progress(0)
        cfg = self.get_test_config()
        test_item = cfg.get("test_item", "Efficiency Curve")

        if test_item == "VIN Sweep":
            self.test_thread = DCDCVinSweepTestThread(self.n6705c, cfg, DEBUG_MOCK)
        elif test_item == "Temperature Sweep":
            if not self.is_chamber_connected or self.chamber is None:
                self.append_log("[ERROR] Chamber not connected. Please connect chamber first.")
                self.set_test_running(False)
                return
            self.test_thread = DCDCTempSweepTestThread(
                self.n6705c, cfg, DEBUG_MOCK, chamber=self.chamber
            )
        else:
            self.test_thread = DCDCEfficiencyTestThread(self.n6705c, cfg, DEBUG_MOCK)

        self.test_thread.log_message.connect(self.append_log)
        self.test_thread.progress.connect(self.set_progress)
        if test_item == "VIN Sweep":
            self.test_thread.chart_point.connect(self._update_vin_sweep_chart_point)
            self.test_thread.chart_new_series.connect(self._on_vin_sweep_new_series)
        else:
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
        self._test_stop_requested = True
        self.append_log("[TEST] Stop requested...")

    def _on_chart_clear(self):
        if HAS_QTCHARTS and hasattr(self, 'series'):
            self.series.clear()
        if HAS_QTCHARTS and hasattr(self, 'smooth_series'):
            self.smooth_series.clear()
        if hasattr(self, '_raw_points'):
            self._raw_points = []
        if HAS_QTCHARTS and hasattr(self, '_vin_sweep_series_list'):
            for s in self._vin_sweep_series_list:
                self.chart.removeSeries(s)
            self._vin_sweep_series_list = []
            self._vin_sweep_current_series = None
            self._vin_sweep_current_raw = []
            self._vin_sweep_all_points = []
            self.chart.legend().hide()
            self.series.setVisible(True)
            self.smooth_series.setVisible(True)

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

    VIN_SWEEP_COLORS = [
        "#00d6a2", "#ff6b6b", "#4ecdc4", "#ffe66d", "#a29bfe",
        "#fd79a8", "#74b9ff", "#ffeaa7", "#55efc4", "#fab1a0",
        "#81ecec", "#dfe6e9", "#e17055", "#00cec9", "#6c5ce7",
    ]

    def _on_vin_sweep_new_series(self, label):
        if not HAS_QTCHARTS or not hasattr(self, 'chart'):
            return
        if not hasattr(self, '_vin_sweep_series_list'):
            self._vin_sweep_series_list = []
            self._vin_sweep_current_series = None
            self._vin_sweep_current_raw = []
            self._vin_sweep_all_points = []

        self.series.setVisible(False)
        self.smooth_series.setVisible(False)

        color_idx = len(self._vin_sweep_series_list) % len(self.VIN_SWEEP_COLORS)
        color = QColor(self.VIN_SWEEP_COLORS[color_idx])

        new_series = QLineSeries()
        new_series.setName(label)
        pen = QPen(color)
        pen.setWidth(2)
        new_series.setPen(pen)

        self.chart.addSeries(new_series)
        new_series.attachAxis(self.axis_x)
        new_series.attachAxis(self.axis_y)

        self._vin_sweep_series_list.append(new_series)
        self._vin_sweep_current_series = new_series
        self._vin_sweep_current_raw = []

        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignRight)
        self.chart.legend().setLabelColor(QColor("#9fc0ef"))
        self.chart.legend().setBackgroundVisible(False)

    def _update_vin_sweep_chart_point(self, i_out_a, eff_pct):
        if not HAS_QTCHARTS or not hasattr(self, '_vin_sweep_current_series'):
            return
        if self._vin_sweep_current_series is None:
            return

        i_out_ma = i_out_a * 1000
        self._vin_sweep_current_raw.append((i_out_ma, eff_pct))
        self._vin_sweep_all_points.append((i_out_ma, eff_pct))

        x_list = [p[0] for p in self._vin_sweep_current_raw]
        y_list = [p[1] for p in self._vin_sweep_current_raw]
        y_smooth = _savgol_smooth(y_list)

        self._vin_sweep_current_series.clear()
        for x, ys in zip(x_list, y_smooth):
            self._vin_sweep_current_series.append(x, ys)

        all_x = [p[0] for p in self._vin_sweep_all_points]
        all_y = [p[1] for p in self._vin_sweep_all_points]

        if self.axis_x is not None and all_x:
            min_x = min(all_x)
            max_x = max(all_x)
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

        if self.axis_y is not None and all_y:
            min_y = max(0, min(all_y) - 5)
            max_y = min(120, max(all_y) + 5)
            if min_y == max_y:
                min_y = max(0, min_y - 10)
                max_y = min(120, max_y + 10)
            self.axis_y.setRange(min_y, max_y)

    def _on_test_finished(self):
        self.set_test_running(False)
        # 通知 AI 异步动作层：测试结束，触发 pending 任务回灌续跑（§4 / S3-2）。
        # 成功判据：未被用户中止且采集到有效数据行；否则视为未完成/失败。
        stopped = bool(getattr(self, "_test_stop_requested", False))
        rows = len(self._export_data) if self._export_data else 0
        success = (not stopped) and rows > 0
        if stopped:
            summary = f"测试被中止（已采集 {rows} 行）"
        elif rows > 0:
            summary = f"测试完成（采集 {rows} 行）"
        else:
            summary = "测试结束但未采集到有效数据"
        self.sequence_execution_finished.emit(success, summary)

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
        base = {
            "test_item": self.test_item_combo.currentText(),
            "vin_channel": self.vin_channel_combo.currentText(),
            "vout_channel": self.vout_channel_combo.currentText(),
            "cc_load_channel": self.cc_load_channel_combo.currentText(),
            "sweep_mode": "Log" if self.log_mode_btn.isChecked() else "Linear",
            "start_current_a": self.load_current_start_spin.value(),
            "end_current_a": self.load_current_end_spin.value(),
            "step_current_a": self.step_current_spin.value(),
            "points_per_dec": self.points_per_dec_spin.value(),
            "average_cnt": self.average_cnt_spin.value(),
            "settle_time_ms": self.settle_time_spin.value(),
            "sampling_method": self.sampling_method_combo.currentText(),
            "dlog_duration_s": self.dlog_duration_spin.value(),
            "vin_start": self.vin_start_spin.value(),
            "vin_end": self.vin_end_spin.value(),
            "vin_step": self.vin_step_spin.value(),
            "temp_start": self.temp_start_spin.value(),
            "temp_end": self.temp_end_spin.value(),
            "temp_step": self.temp_step_spin.value(),
        }
        if self.test_item_combo.currentText() == "Temperature Sweep":
            base["fixed_load_a"] = self.temp_fixed_load_spin.value()
        return base

    def set_test_running(self, running):
        self.is_test_running = running

        update_start_btn_state(self.start_test_btn, running,
                               start_text="▶ START SEQUENCE",
                               stop_text="■ STOP")
        self.stop_test_btn.setEnabled(running)

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
            self.average_cnt_spin,
            self.visa_resource_combo,
            self.search_btn,
            self.connect_btn,
            self.test_item_combo,
            self.settle_time_spin,
            self.sampling_method_combo,
            self.dlog_duration_spin,
            self.vin_start_spin,
            self.vin_end_spin,
            self.vin_step_spin,
            self.temp_start_spin,
            self.temp_end_spin,
            self.temp_step_spin,
            self.temp_fixed_load_spin,
            self.chamber_search_btn,
            self.chamber_connect_btn,
            self.chamber_port_combo,
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

    def update_instrument_info(self, instrument_info):
        if self.is_connected:
            self.set_system_status("● Connected")

    # ------------------------------------------------------------------
    # AIControllablePage 契约实现（AIAssist_PageScopedControlPlan.md §2 / Phase 2）
    #
    # PMU DCDC Efficiency 作为首个接入契约的专项页样板，薄封装既有方法：
    #   - ai_get_config 复用 get_test_config()
    #   - ai_apply_config 经 apply_config_to_controls() 单一写入口回填控件
    #   - ai_start_test/ai_stop_test 复用 _on_start_test/_on_stop_test
    # 枢纽（MainWindow.resolve_active_ai_page）经 Tab 子页下钻拿到本实例，
    # 鸭子调用契约方法，无需 core / handler 改动。
    # ------------------------------------------------------------------
    def ai_capabilities(self) -> set[str]:
        return {
            CAP_GET_CONFIG,
            CAP_APPLY_CONFIG,
            CAP_START_TEST,
            CAP_STOP_TEST,
            CAP_GET_RESULT,
        }

    def ai_get_config(self) -> dict[str, Any] | None:
        try:
            cfg = dict(self.get_test_config())
        except Exception:  # noqa: BLE001 - 快照失败降级为 None
            _logger.error("AI 读取 DCDC 效率测试配置失败", exc_info=True)
            return None
        # 仅暴露当前测试项「真正会遍历」的维度，避免 AI 把 UI 上常驻但未激活的
        # VIN / 温度扫描字段当成会执行的遍历维度（如 Efficiency Curve 仅扫电流，
        # 不遍历 VIN / 温度）。否则 AI 会臆造「电流×VIN×温度」的组合数误导用户。
        test_item = cfg.get("test_item", "Efficiency Curve")
        if test_item != "VIN Sweep":
            for key in ("vin_start", "vin_end", "vin_step"):
                cfg.pop(key, None)
        if test_item != "Temperature Sweep":
            for key in ("temp_start", "temp_end", "temp_step", "fixed_load_a"):
                cfg.pop(key, None)
        cfg["sweep_dimensions"] = ["load_current"]
        if test_item == "VIN Sweep":
            cfg["sweep_dimensions"].append("vin")
        elif test_item == "Temperature Sweep":
            cfg["sweep_dimensions"].append("temperature")
        return cfg

    def ai_apply_config(self, payload: Any) -> tuple[bool, str]:
        """落地配置草案到控件（写操作，经确认+审计后由枢纽调用）。

        运行中拒绝改配置（§6.3），避免与正在执行的扫描冲突。
        """
        if self.is_test_running:
            return False, "测试运行中，无法修改配置，请先停止测试。"
        return self.apply_config_to_controls(payload if isinstance(payload, dict) else {})

    def ai_start_test(self) -> tuple[bool, str]:
        if not self.is_connected or self.n6705c is None:
            return False, "未连接 N6705C 仪器，请先连接再启动测试。"
        if self.is_test_running:
            return False, "测试已在运行中。"
        cfg = self.get_test_config()
        if cfg.get("test_item") == "Temperature Sweep" and (
            not self.is_chamber_connected or self.chamber is None
        ):
            return False, "当前测试项为 Temperature Sweep，但未连接温箱，请先连接温箱。"
        self.append_log(
            f"[AI] 请求启动测试：{cfg.get('test_item', 'Efficiency Curve')}，"
            f"扫描 {cfg.get('start_current_a')}~{cfg.get('end_current_a')}A。"
        )
        try:
            self._on_start_test()
        except Exception:  # noqa: BLE001 - 启动异常转可读结果
            _logger.error("AI 启动 DCDC 效率测试失败", exc_info=True)
            return False, "启动测试异常，请查看日志。"
        if self.is_test_running:
            return True, "已请求启动 DCDC 效率测试。"
        return False, "启动未成功，请查看执行日志。"

    def ai_stop_test(self) -> tuple[bool, str]:
        if not self.is_test_running:
            return False, "当前未在运行测试。"
        self.append_log("[AI] 请求停止测试。")
        try:
            self._on_stop_test()
        except Exception:  # noqa: BLE001 - 停止异常转可读结果
            _logger.error("AI 停止 DCDC 效率测试失败", exc_info=True)
            return False, "停止测试异常，请查看日志。"
        return True, "已发送停止请求。"

    def ai_get_result_summary(self) -> dict[str, Any] | None:
        if not self._export_data:
            return None
        rows = [r for r in self._export_data if r.get("efficiency", 0) > 0]
        summary: dict[str, Any] = {
            "available": True,
            "running": self.is_test_running,
            "rows": len(self._export_data),
            "test_item": self.test_item_combo.currentText(),
        }
        if not rows:
            return summary
        max_row = max(rows, key=lambda r: r["efficiency"])
        summary["max_efficiency"] = round(max_row["efficiency"], 2)
        summary["max_eff_load_a"] = round(max_row.get("cc_load", 0.0), 6)
        summary["avg_efficiency"] = round(
            sum(r["efficiency"] for r in rows) / len(rows), 2
        )
        return summary

    # ------------------------------------------------------------------
    # UI 回填单一写入口（AIAssist_PageScopedControlPlan.md §4.2）
    #
    # apply_config_to_controls(cfg) 是回填测试配置控件的唯一入口，
    # AI 回填与未来轮询/手动刷新共用，杜绝两套逻辑漂移。键名与
    # get_test_config() 输出对齐；电流字段兼容 *_ma（毫安）别名。
    # ------------------------------------------------------------------
    def apply_config_to_controls(self, cfg: dict) -> tuple[bool, str]:
        if not isinstance(cfg, dict):
            return False, "配置草案格式无效（期望 dict）。"

        # 线程边界（§4.2-2）：AI 决策在 QThread，回填须经主线程执行；
        # dispatcher 经 QTimer.singleShot(0) 已切回主线程，此处加防御性守卫，
        # 杜绝 worker 线程直接 setValue 违反「UI 禁阻塞 / 跨线程改控件」铁律。
        if threading.current_thread() is not threading.main_thread():
            _logger.error(
                "apply_config_to_controls 在非主线程被调用，拒绝回填以防违反线程边界"
            )
            return False, "配置回填未在主线程执行，已拒绝。"

        applied: list[str] = []
        touched: list = []  # 被 AI 修改的控件，用于回填后高亮（§4.2-3 / Phase 3）

        def _pick(canonical: str, *aliases: str):
            for k in (canonical, *aliases):
                if k in cfg:
                    return k, cfg[k]
            return None, None

        def _pick_current(canonical: str, *aliases: str) -> float | None:
            k, v = _pick(canonical, *aliases)
            if k is None or v is None:
                return None
            try:
                val = float(v)
            except (TypeError, ValueError):
                return None
            if k.endswith("_ma"):
                val *= 0.001
            return val

        def _pick_int(canonical: str, *aliases: str) -> int | None:
            _, v = _pick(canonical, *aliases)
            if v is None:
                return None
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return None

        def _pick_float(canonical: str, *aliases: str) -> float | None:
            _, v = _pick(canonical, *aliases)
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        def _normalize_channel(val) -> str | None:
            s = str(val).strip().upper()
            if not s:
                return None
            digits = ""
            for ch in s[::-1]:
                if ch.isdigit():
                    digits = ch + digits
                else:
                    break
            return f"CH {digits}" if digits else None

        def _set_combo(combo, canonical: str, *aliases: str, normalize=None):
            _, val = _pick(canonical, *aliases)
            if val is None:
                return
            text = normalize(val) if normalize is not None else str(val)
            if text is None:
                return
            idx = combo.findText(text)
            if idx >= 0:
                combo.setCurrentIndex(idx)
                applied.append(canonical)
                touched.append(combo)

        def _set_spin(spin, canonical: str, *aliases: str, picker=_pick_float):
            val = picker(canonical, *aliases)
            if val is None:
                return
            spin.setValue(val)
            applied.append(canonical)
            touched.append(spin)

        # 测试项
        _, test_item = _pick("test_item")
        if test_item is not None:
            idx = self.test_item_combo.findText(str(test_item))
            if idx >= 0:
                self.test_item_combo.setCurrentIndex(idx)
                applied.append("test_item")
                touched.append(self.test_item_combo)

        # 扫描模式（Linear / Log）
        _, sweep_mode = _pick("sweep_mode")
        if sweep_mode is not None:
            is_log = str(sweep_mode).lower().startswith("log")
            self.log_mode_btn.setChecked(is_log)
            self.linear_mode_btn.setChecked(not is_log)
            self._on_sweep_mode_changed()
            applied.append("sweep_mode")
            touched.extend([self.log_mode_btn, self.linear_mode_btn])

        # 采样方式
        _set_combo(self.sampling_method_combo, "sampling_method")

        # 通道（兼容 "1" / "CH1" / "CH 1"）
        _set_combo(self.vin_channel_combo, "vin_channel",
                   "vin_ch", "input_channel", normalize=_normalize_channel)
        _set_combo(self.vout_channel_combo, "vout_channel",
                   "vout_ch", "output_channel", normalize=_normalize_channel)
        _set_combo(self.cc_load_channel_combo, "cc_load_channel",
                   "load_channel", "cc_load_ch", normalize=_normalize_channel)

        # 电流扫描范围（A，兼容 _ma 毫安别名）
        _set_spin(self.load_current_start_spin, "start_current_a",
                  "start_current", "i_start", "start_current_ma", "i_start_ma",
                  picker=_pick_current)
        _set_spin(self.load_current_end_spin, "end_current_a",
                  "end_current", "i_end", "end_current_ma", "i_end_ma",
                  picker=_pick_current)
        _set_spin(self.step_current_spin, "step_current_a",
                  "step_current", "i_step", "step_current_ma", "i_step_ma",
                  picker=_pick_current)

        # 其它数值参数
        _set_spin(self.points_per_dec_spin, "points_per_dec",
                  "points_per_decade", picker=_pick_int)
        _set_spin(self.average_cnt_spin, "average_cnt",
                  "avg_cnt", "average_count", picker=_pick_int)
        _set_spin(self.settle_time_spin, "settle_time_ms",
                  "settle_time", "settle_time_s", picker=_pick_int)
        _set_spin(self.dlog_duration_spin, "dlog_duration_s",
                  "dlog_duration", picker=_pick_float)

        # VIN 扫描
        _set_spin(self.vin_start_spin, "vin_start", "vin_start_v", picker=_pick_float)
        _set_spin(self.vin_end_spin, "vin_end", "vin_end_v", picker=_pick_float)
        _set_spin(self.vin_step_spin, "vin_step", "vin_step_v", picker=_pick_float)

        # 温度扫描
        _set_spin(self.temp_start_spin, "temp_start", "temp_start_c", picker=_pick_float)
        _set_spin(self.temp_end_spin, "temp_end", "temp_end_c", picker=_pick_float)
        _set_spin(self.temp_step_spin, "temp_step", "temp_step_c", picker=_pick_float)
        _set_spin(self.temp_fixed_load_spin, "fixed_load_a",
                  "fixed_load", "fixed_load_ma", picker=_pick_current)

        if not applied:
            return False, "配置草案未包含任何可识别的配置项。"
        # §4.2-3 可视化反馈：被 AI 修改的控件临时高亮（Phase 3）。
        self._highlight_widgets(touched)
        self.append_log(f"[AI] 已应用配置：{', '.join(applied)}")
        return True, f"已应用配置项：{', '.join(applied)}。"

    def _highlight_widgets(self, widgets: list) -> None:
        """被 AI 修改的控件临时高亮边框（§4.2-3 / Phase 3）。

        复用页面 QSS：仅覆盖 border 颜色（不重写背景/padding，未指定的属性
        仍由页面 QSS 提供），到期后清空 widget 本地 stylesheet 让页面 QSS 复原。
        """
        if not widgets:
            return
        for widget in widgets:
            if widget is None:
                continue
            widget.setStyleSheet(_AI_HIGHLIGHT_QSS)
            widget.setProperty("aiHighlighted", True)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            # 持有各自定时器引用避免被 GC；到期清回空样式让页面 QSS 接管
            def _clear(_w=widget, _qss_ref=widget):
                try:
                    _w.setStyleSheet("")
                    _w.setProperty("aiHighlighted", False)
                    _w.style().unpolish(_w)
                    _w.style().polish(_w)
                except RuntimeError:  # noqa: BLE001 - widget 可能已销毁
                    pass
            QTimer.singleShot(_AI_HIGHLIGHT_MS, _clear)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from log_config import setup_logging, get_logger
    from ui.standalone import resize_and_center_window
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
    resize_and_center_window(window)
    window.show()

    sys.exit(app.exec())

