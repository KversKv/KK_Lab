#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generic temperature chamber control page."""

import sys
import os
from ui.resource_path import get_resource_base


# 添加项目根目录到sys.path，解决模块导入问题
sys.path.append(get_resource_base())

from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.button import update_connect_button_state
from ui.widgets.instrument_state_poller import InstrumentStatePoller
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QLineEdit, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QApplication, QGridLayout, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QRectF, QSize, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QFont, QPixmap
from PySide6.QtSvg import QSvgRenderer
from debug_config import DEBUG_MOCK
from instruments.factory import create_chamber
from log_config import get_logger
from ui.modules.chamber_module_frame import (
    CHAMBER_TYPES,
    chamber_baudrate,
    chamber_connection_kind,
    chamber_default_resource,
    chamber_display_name,
    chamber_type_label,
    chamber_uses_network,
)

logger = get_logger(__name__)

_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "chamber_SVGs"
)
_THERMOMETER_SVG_PATH = os.path.join(_PAGE_SVGS_DIR, "thermometer.svg")
_SEARCH_SVG_PATH = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Common", "search.svg"
)


class TemperatureGauge(QWidget):
    """圆形温度显示控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actual_temp = None
        self.setMinimumSize(240, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_temperature(self, value):
        self._actual_temp = value
        self.update()

    def sizeHint(self):
        return QSize(280, 280)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        side = min(rect.width(), rect.height()) - 18
        x = (rect.width() - side) / 2
        y = (rect.height() - side) / 2
        circle_rect = QRectF(x, y, side, side)

        # 外环
        ring_pen = QPen(QColor("#1b2d4d"))
        ring_pen.setWidth(8)
        painter.setPen(ring_pen)
        painter.setBrush(QColor("#02092a"))
        painter.drawEllipse(circle_rect)

        # 标题
        painter.setPen(QColor("#6d83b1"))
        title_font = QFont("Segoe UI", max(8, int(side * 0.04)))
        title_font.setBold(True)
        painter.setFont(title_font)
        title_rect = QRectF(circle_rect.left(), circle_rect.top() + side * 0.33, side, 24)
        painter.drawText(title_rect, Qt.AlignCenter, "ACTUAL TEMP")

        # 数值
        painter.setPen(QColor("#ffffff"))
        value_font = QFont("JetBrains Mono", max(18, int(side * 0.11)))
        value_font.setStyleHint(QFont.Monospace)
        value_font.setBold(True)
        painter.setFont(value_font)

        if self._actual_temp is None:
            value_text = "---°C"
        else:
            value_text = f"{self._actual_temp:.1f}°C"

        value_rect = QRectF(circle_rect.left(), circle_rect.top() + side * 0.46, side, 40)
        painter.drawText(value_rect, Qt.AlignCenter, value_text)


class ChamberControlUI(QWidget):
    """Generic temperature chamber control UI."""

    connection_changed = Signal()

    def __init__(self, instrument_manager=None):
        super().__init__()
        self.chamber = None
        self._instrument_manager = instrument_manager
        self._state_poller = InstrumentStatePoller(
            read_state_fn=self._read_chamber_snapshot,
            apply_state_fn=self._apply_chamber_snapshot,
            interval_s=1.0,
            busy_check_fn=self._is_chamber_session_busy,
            parent=self,
        )
        self.is_chamber_on = False
        self.current_chamber_type = "vt6002"
        self.current_chamber_session_id = None
        self.current_port = None
        self.preset_buttons = []

        # 温度循环序列状态
        self.loop_timer = QTimer()
        self.loop_timer.setInterval(1000)
        self._loop_running = False
        self._loop_sequence = []
        self._loop_index = 0
        self._loop_cycle = 0
        self._loop_phase = "idle"
        self._loop_dwell_remaining = 0
        self._loop_tolerance = 1.0
        self._loop_dwell_seconds = 0
        self._loop_forever = False
        self._loop_cycles_total = 1

        # 初始化界面
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置界面"""
        self.setObjectName("rootWidget")
        self.setStyleSheet(self._build_stylesheet())

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(18)

        # 标题区
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        title_icon = QLabel()
        title_icon.setFixedSize(24, 24)
        if os.path.isfile(_THERMOMETER_SVG_PATH):
            with open(_THERMOMETER_SVG_PATH, "r", encoding="utf-8") as f:
                svg_data = f.read().replace('stroke="currentColor"', 'stroke="#fb7185"').encode("utf-8")
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.transparent)
            renderer = QSvgRenderer(svg_data)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            title_icon.setPixmap(pixmap)
        title_icon.setStyleSheet("border: none; background: transparent;")
        title_row.addWidget(title_icon)

        title_label = QLabel("Chamber")
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("border: none")
        title_row.addWidget(title_label)
        title_row.addStretch()

        header_layout.addLayout(title_row)

        subtitle_label = QLabel("Thermal chamber control and monitoring via serial or Ethernet.")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setStyleSheet("border: none")

        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        # 串口连接卡片
        serial_group = QFrame()
        serial_group.setObjectName("connectionCard")
        serial_layout = QVBoxLayout(serial_group)
        serial_layout.setContentsMargins(18, 16, 18, 18)
        serial_layout.setSpacing(14)

        connection_header = QHBoxLayout()
        connection_header.setContentsMargins(0, 0, 0, 0)
        connection_header.setSpacing(10)

        connection_title_col = QVBoxLayout()
        connection_title_col.setContentsMargins(0, 0, 0, 0)
        connection_title_col.setSpacing(2)

        connection_title = QLabel("Connection")
        connection_title.setObjectName("connectionTitle")
        connection_title.setStyleSheet("border: none")

        connection_subtitle = QLabel("Select chamber model and connection resource")
        connection_subtitle.setObjectName("connectionSubtitle")
        connection_subtitle.setStyleSheet("border: none")

        connection_title_col.addWidget(connection_title)
        connection_title_col.addWidget(connection_subtitle)
        connection_header.addLayout(connection_title_col)
        connection_header.addStretch()
        serial_layout.addLayout(connection_header)

        type_label = QLabel("Chamber Type")
        type_label.setObjectName("fieldLabel")
        type_label.setStyleSheet("border: none")

        self.chamber_type_combo = DarkComboBox(bg="#04102b", border="#1a315d")
        self.chamber_type_combo.setObjectName("comboBox")
        for chamber_type, meta in CHAMBER_TYPES.items():
            self.chamber_type_combo.addItem(meta["label"], chamber_type)

        self.port_label = QLabel("COM Port")
        self.port_label.setObjectName("fieldLabel")
        self.port_label.setStyleSheet("border: none")

        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(14)

        form_panel = QFrame()
        form_panel.setObjectName("connectionPanel")
        form_layout = QGridLayout(form_panel)
        form_layout.setContentsMargins(14, 12, 14, 14)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(8)

        self.port_combo = DarkComboBox(bg="#04102b", border="#1a315d")
        self.port_combo.setObjectName("comboBox")

        self.scan_btn = QPushButton()
        self.scan_btn.setObjectName("iconButton")
        self.scan_btn.setFixedSize(40, 38)
        self.scan_btn.setToolTip("Search serial ports")
        if os.path.isfile(_SEARCH_SVG_PATH):
            self.scan_btn.setIcon(QIcon(_SEARCH_SVG_PATH))
            self.scan_btn.setIconSize(QSize(16, 16))
        self.scan_btn.clicked.connect(self._scan_ports)

        port_control_layout = QHBoxLayout()
        port_control_layout.setContentsMargins(0, 0, 0, 0)
        port_control_layout.setSpacing(8)
        port_control_layout.addWidget(self.port_combo, 1)
        port_control_layout.addWidget(self.scan_btn, 0)

        form_layout.addWidget(type_label, 0, 0)
        form_layout.addWidget(self.port_label, 0, 1)
        form_layout.addWidget(self.chamber_type_combo, 1, 0)
        form_layout.addLayout(port_control_layout, 1, 1)
        form_layout.setColumnStretch(0, 1)
        form_layout.setColumnStretch(1, 2)

        self.status_frame = QFrame()
        self.status_frame.setObjectName("statusWrap")
        self.status_frame.setMinimumHeight(92)
        self.status_frame.setMaximumWidth(370)
        status_layout = QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(16, 14, 12, 14)
        status_layout.setSpacing(12)

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setStyleSheet("border: none")

        status_text_layout = QVBoxLayout()
        status_text_layout.setSpacing(0)

        self.status_title = QLabel("Chamber Status")
        self.status_title.setObjectName("statusTitle")
        self.status_title.setStyleSheet("border: none")

        self.status_detail = QLabel("Disconnected")
        self.status_detail.setObjectName("statusDesc")
        self.status_detail.setStyleSheet("border: none")

        status_text_layout.addWidget(self.status_title)
        status_text_layout.addWidget(self.status_detail)

        self.connect_btn = QPushButton()
        update_connect_button_state(self.connect_btn, connected=False)
        self.connect_btn.setObjectName("connectButton")
        self.connect_btn.setFixedSize(116, 38)

        status_layout.addWidget(self.status_dot)
        status_layout.addLayout(status_text_layout)
        status_layout.addStretch()
        status_layout.addWidget(self.connect_btn)

        row_layout.addWidget(form_panel, 3)
        row_layout.addWidget(self.status_frame, 2)

        serial_layout.addLayout(row_layout)
        self._apply_shadow(serial_group)
        main_layout.addWidget(serial_group)

        # 中间内容区
        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        # 左侧温度监控卡片
        monitor_group = QGroupBox("⌁ Temperature Monitor")
        monitor_group.setObjectName("cardGroup")
        monitor_layout = QVBoxLayout(monitor_group)
        monitor_layout.setContentsMargins(18, 18, 18, 18)
        monitor_layout.setSpacing(18)

        monitor_layout.addSpacing(4)

        self.temp_gauge = TemperatureGauge()
        monitor_layout.addStretch(1)
        monitor_layout.addWidget(self.temp_gauge, 0, alignment=Qt.AlignHCenter)

        set_temp_widget = QFrame()
        set_temp_widget.setObjectName("miniInfoBox")
        set_temp_layout = QHBoxLayout(set_temp_widget)
        set_temp_layout.setContentsMargins(16, 12, 16, 12)

        set_temp_label = QLabel("SET TEMP")
        set_temp_label.setObjectName("miniInfoLabel")
        set_temp_label.setStyleSheet("border: none")

        self.set_temp_value = QLabel("--- °C")
        self.set_temp_value.setObjectName("miniInfoValue")
        self.set_temp_value.setStyleSheet("border: none")

        set_temp_layout.addWidget(set_temp_label)
        set_temp_layout.addStretch()
        set_temp_layout.addWidget(self.set_temp_value)

        monitor_layout.addWidget(set_temp_widget)
        monitor_layout.addStretch(2)

        self._apply_shadow(monitor_group)
        content_layout.addWidget(monitor_group, 1)

        # 右侧控制卡片
        control_group = QGroupBox("Chamber Control")
        control_group.setObjectName("cardGroup")
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(18, 18, 18, 18)
        control_layout.setSpacing(18)

        # 电源区域
        power_panel = QFrame()
        power_panel.setObjectName("innerPanel")
        power_panel_layout = QVBoxLayout(power_panel)
        power_panel_layout.setContentsMargins(18, 18, 18, 18)
        power_panel_layout.setSpacing(10)

        power_label = QLabel("Chamber Power")
        power_label.setObjectName("fieldLabel")
        power_label.setStyleSheet("border: none")

        self.power_btn = QPushButton("⏻  TURN ON CHAMBER")
        self.power_btn.setObjectName("powerButton")
        self.power_btn.setFixedHeight(46)
        self.power_btn.setEnabled(False)

        power_panel_layout.addWidget(power_label)
        power_panel_layout.addWidget(self.power_btn)

        # 温度设置区域
        temp_panel = QFrame()
        temp_panel.setObjectName("innerPanel")
        temp_panel_layout = QVBoxLayout(temp_panel)
        temp_panel_layout.setContentsMargins(18, 18, 18, 18)
        temp_panel_layout.setSpacing(12)

        temp_label = QLabel("Target Temperature (°C)")
        temp_label.setObjectName("fieldLabel")
        temp_label.setStyleSheet("border: none")

        temp_input_layout = QHBoxLayout()
        temp_input_layout.setSpacing(10)

        self.temp_input = QLineEdit()
        self.temp_input.setObjectName("tempInput")
        self.temp_input.setFixedHeight(44)
        self.temp_input.setText("25.0")

        self.set_btn = QPushButton("SET")
        self.set_btn.setObjectName("setButton")
        self.set_btn.setFixedHeight(44)
        self.set_btn.setEnabled(False)

        temp_input_layout.addWidget(self.temp_input, 1)
        temp_input_layout.addWidget(self.set_btn, 0)

        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)

        preset_temps = ["-40°C", "-20°C", "0°C", "25°C", "50°C", "85°C", "125°C"]
        for temp in preset_temps:
            btn = QPushButton(temp)
            btn.setObjectName("presetButton")
            btn.setFixedHeight(30)
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked=False, t=temp: self._set_preset_temp(t))
            self.preset_buttons.append(btn)
            preset_layout.addWidget(btn)

        temp_panel_layout.addWidget(temp_label)
        temp_panel_layout.addLayout(temp_input_layout)
        temp_panel_layout.addLayout(preset_layout)

        # 温度循环序列区域
        loop_panel = QFrame()
        loop_panel.setObjectName("innerPanel")
        loop_panel_layout = QVBoxLayout(loop_panel)
        loop_panel_layout.setContentsMargins(18, 18, 18, 18)
        loop_panel_layout.setSpacing(12)

        loop_header = QHBoxLayout()
        loop_header.setContentsMargins(0, 0, 0, 0)
        loop_header.setSpacing(8)
        loop_title = QLabel("Temperature Loop")
        loop_title.setObjectName("fieldLabel")
        loop_title.setStyleSheet("border: none")
        loop_header.addWidget(loop_title)
        loop_header.addStretch()
        self.loop_forever_check = QCheckBox("Repeat forever")
        self.loop_forever_check.setObjectName("loopCheck")
        loop_header.addWidget(self.loop_forever_check)
        loop_panel_layout.addLayout(loop_header)

        seq_label = QLabel("Temperature Sequence (°C, comma separated)")
        seq_label.setObjectName("fieldLabelSmall")
        seq_label.setStyleSheet("border: none")
        loop_panel_layout.addWidget(seq_label)

        self.loop_sequence_input = QLineEdit()
        self.loop_sequence_input.setObjectName("loopInput")
        self.loop_sequence_input.setFixedHeight(40)
        self.loop_sequence_input.setPlaceholderText("e.g. -20, 25, 85, 125")
        self.loop_sequence_input.setText("-20, 25, 85")
        loop_panel_layout.addWidget(self.loop_sequence_input)

        loop_params_layout = QGridLayout()
        loop_params_layout.setHorizontalSpacing(12)
        loop_params_layout.setVerticalSpacing(6)

        dwell_label = QLabel("Dwell per Step (min)")
        dwell_label.setObjectName("fieldLabelSmall")
        dwell_label.setStyleSheet("border: none")
        tol_label = QLabel("Arrival Tolerance (°C)")
        tol_label.setObjectName("fieldLabelSmall")
        tol_label.setStyleSheet("border: none")
        cycles_label = QLabel("Cycles")
        cycles_label.setObjectName("fieldLabelSmall")
        cycles_label.setStyleSheet("border: none")

        self.loop_dwell_input = QLineEdit()
        self.loop_dwell_input.setObjectName("loopInput")
        self.loop_dwell_input.setFixedHeight(38)
        self.loop_dwell_input.setText("5")
        self.loop_tolerance_input = QLineEdit()
        self.loop_tolerance_input.setObjectName("loopInput")
        self.loop_tolerance_input.setFixedHeight(38)
        self.loop_tolerance_input.setText("1.0")
        self.loop_cycles_input = QLineEdit()
        self.loop_cycles_input.setObjectName("loopInput")
        self.loop_cycles_input.setFixedHeight(38)
        self.loop_cycles_input.setText("1")

        loop_params_layout.addWidget(dwell_label, 0, 0)
        loop_params_layout.addWidget(tol_label, 0, 1)
        loop_params_layout.addWidget(cycles_label, 0, 2)
        loop_params_layout.addWidget(self.loop_dwell_input, 1, 0)
        loop_params_layout.addWidget(self.loop_tolerance_input, 1, 1)
        loop_params_layout.addWidget(self.loop_cycles_input, 1, 2)
        loop_panel_layout.addLayout(loop_params_layout)

        loop_btn_layout = QHBoxLayout()
        loop_btn_layout.setSpacing(10)
        self.loop_start_btn = QPushButton("▶  START LOOP")
        self.loop_start_btn.setObjectName("loopStartButton")
        self.loop_start_btn.setFixedHeight(42)
        self.loop_start_btn.setEnabled(False)
        self.loop_stop_btn = QPushButton("■  STOP LOOP")
        self.loop_stop_btn.setObjectName("loopStopButton")
        self.loop_stop_btn.setFixedHeight(42)
        self.loop_stop_btn.setEnabled(False)
        loop_btn_layout.addWidget(self.loop_start_btn, 1)
        loop_btn_layout.addWidget(self.loop_stop_btn, 1)
        loop_panel_layout.addLayout(loop_btn_layout)

        self.loop_status_label = QLabel("Loop idle")
        self.loop_status_label.setObjectName("loopStatusLabel")
        self.loop_status_label.setStyleSheet("border: none")
        self.loop_status_label.setWordWrap(True)
        loop_panel_layout.addWidget(self.loop_status_label)

        control_layout.addWidget(power_panel)
        control_layout.addWidget(temp_panel)
        control_layout.addWidget(loop_panel)
        control_layout.addStretch()

        self._apply_shadow(control_group)
        content_layout.addWidget(control_group, 1)

        main_layout.addLayout(content_layout)

        # 扫描可用端口
        self._scan_ports()

    def _connect_signals(self):
        self.chamber_type_combo.currentIndexChanged.connect(self._on_chamber_type_changed)
        self.connect_btn.clicked.connect(self._toggle_connection)
        self.power_btn.clicked.connect(self._toggle_chamber_power)
        self.set_btn.clicked.connect(self._set_temperature)
        self.loop_start_btn.clicked.connect(self._start_loop)
        self.loop_stop_btn.clicked.connect(self._stop_loop)
        self.loop_timer.timeout.connect(self._loop_tick)
        if self._instrument_manager:
            self._instrument_manager.session_connected.connect(
                self._on_manager_session_connected
            )
            self._instrument_manager.session_disconnected.connect(
                self._on_manager_session_disconnected
            )
            self._instrument_manager.connection_failed.connect(
                self._on_manager_connect_failed
            )

    def _on_manager_session_connected(self, session_id: str):
        session = self._instrument_manager.get_session(session_id)
        if not session or session.role != "chamber":
            return
        if session and session.connected:
            self.chamber = session.instance
            self.current_chamber_type = session.instrument_type
            self.current_chamber_session_id = session_id
            self.current_port = session.resource
            self._set_type_combo(session.instrument_type)
            self._set_connection_ui(True)
            self._set_controls_enabled(True)
            self._sync_power_state_from_chamber()
            self.connection_changed.emit()

    def _on_manager_session_disconnected(self, session_id: str):
        if session_id != self.current_chamber_session_id:
            return
        self.chamber = None
        self.current_port = None
        self.current_chamber_session_id = None
        self.is_chamber_on = False
        self._set_connection_ui(False)
        self._set_controls_enabled(False)
        self._set_power_ui(False, connected=False)
        self.connection_changed.emit()

    def _on_manager_connect_failed(self, session_id: str, error: str):
        if session_id != self.current_chamber_session_id and not session_id.endswith(":chamber"):
            return
        logger.error("Chamber connection failed via manager: %s", error)
        self._set_connection_ui(False)
        self._set_controls_enabled(False)
        self._set_power_ui(False, connected=False)

    def _on_chamber_type_changed(self):
        self.current_chamber_type = self._selected_chamber_type()
        if self.chamber is None:
            self._scan_ports()

    def _selected_chamber_type(self):
        data = self.chamber_type_combo.currentData()
        return str(data or self.current_chamber_type or "vt6002")

    def _set_type_combo(self, chamber_type: str):
        idx = self.chamber_type_combo.findData(chamber_type)
        if idx >= 0:
            self.chamber_type_combo.setCurrentIndex(idx)

    def _update_connection_resource_mode(self, chamber_type: str):
        uses_network = chamber_uses_network(chamber_type)
        self.port_label.setText("IP Address" if uses_network else "COM Port")
        self.port_combo.setEditable(uses_network)
        self.scan_btn.setToolTip("Use default IP address" if uses_network else "Search serial ports")

    def _apply_shadow(self, widget):
        """卡片阴影"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 80))
        widget.setGraphicsEffect(shadow)

    def _build_stylesheet(self):
        return """
        QWidget#rootWidget {
            background-color: #030b23;
            color: #eaf1ff;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: 14px;
        }

        QLabel {
            background: transparent;
        }

        #titleLabel {
            font-size: 20px;
            font-weight: 800;
            color: #f4f7ff;
        }

        #subtitleLabel {
            font-size: 13px;
            color: #7f95bf;
        }

        QGroupBox#cardGroup {
            background-color: #0a1738;
            border: 1px solid rgba(94, 126, 190, 0.18);
            border-radius: 16px;
            margin-top: 0px;
            padding-top: 14px;
            font-size: 16px;
            font-weight: 700;
            color: #f4f7ff;
        }

        QGroupBox#cardGroup::title {
            subcontrol-origin: margin;
            left: 18px;
            top: 14px;
            padding: 0 4px 0 4px;
            color: #f4f7ff;
            font-size: 16px;
            font-weight: 700;
        }

        QFrame#connectionCard {
            background-color: #0a1738;
            border: 1px solid rgba(94, 126, 190, 0.22);
            border-radius: 14px;
        }

        QFrame#connectionPanel {
            background-color: #07132e;
            border: 1px solid #17305f;
            border-radius: 10px;
        }

        #connectionTitle {
            font-size: 15px;
            font-weight: 800;
            color: #f4f7ff;
        }

        #connectionSubtitle {
            font-size: 12px;
            color: #8ca5d3;
        }

        #fieldLabel {
            font-size: 12px;
            font-weight: 650;
            color: #8ca5d3;
        }

        #comboBox {
            background-color: #04102b;
            border: 1px solid #1a315d;
            border-radius: 8px;
            padding: 0 12px;
            min-height: 36px;
            color: #eef4ff;
        }

        #comboBox:hover {
            border-color: #27457d;
        }

        #comboBox::drop-down {
            border: none;
            width: 24px;
        }

        #comboBox QAbstractItemView {
            background-color: #04102b;
            color: #eef4ff;
            border: 1px solid #1a315d;
            selection-background-color: #1a3260;
            outline: 0px;
        }

        #comboBox QAbstractItemView::item {
            background-color: #04102b;
            color: #eef4ff;
            padding: 4px 8px;
        }

        #comboBox QAbstractItemView::item:hover {
            background-color: #1a3260;
        }

        QComboBox QFrame {
            background-color: #04102b;
            border: 1px solid #1a315d;
        }

        #iconButton {
            background-color: #13254b;
            border: 1px solid #22365d;
            border-radius: 8px;
            color: #b7c7e6;
            font-size: 16px;
            font-weight: 700;
        }

        #iconButton:hover {
            background-color: #213258;
        }

        #iconButton:pressed {
            background-color: #182847;
        }

        #statusWrap {
            background-color: #07132e;
            border: 1px solid #17305f;
            border-radius: 10px;
        }

        #statusDot {
            color: #5d78a7;
            font-size: 18px;
        }

        #statusTitle {
            font-size: 14px;
            font-weight: 700;
            color: #dfe8fb;
        }

        #statusDesc {
            font-size: 12px;
            color: #7e95bf;
        }

        QPushButton#connectButton {
            min-height: 38px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 800;
            padding: 0 14px;
        }

        #miniInfoBox {
            background-color: #040d28;
            border: 1px solid #17305f;
            border-radius: 12px;
        }

        #miniInfoLabel {
            color: #8ca5d3;
            font-size: 13px;
        }

        #miniInfoValue {
            color: #6f7dff;
            font-size: 18px;
            font-weight: 800;
        }

        #innerPanel {
            background-color: #040d28;
            border: 1px solid #17305f;
            border-radius: 12px;
        }

        #powerButton {
            background-color: #223150;
            border: 1px solid #34486f;
            border-radius: 8px;
            color: #5f7397;
            font-size: 15px;
            font-weight: 800;
            padding: 10px 16px;
        }

        #powerButton:hover:!disabled {
            background-color: #2a3a5e;
        }

        #powerButton:pressed:!disabled {
            background-color: #243350;
        }

        #powerButton:disabled {
            background-color: #1a2642;
            color: #4f6287;
            border: 1px solid #2a3b63;
        }

        #tempInput {
            background-color: #06122f;
            border: 1px solid #183261;
            border-radius: 8px;
            color: #eaf1ff;
            padding: 0 14px;
            font-size: 16px;
            font-weight: 600;
        }

        #tempInput:focus {
            border: 1px solid #4a68ff;
        }

        #setButton {
            background-color: #3d2bc6;
            border: none;
            border-radius: 8px;
            color: #cfd5f3;
            font-weight: 800;
            padding: 0 22px;
        }

        #setButton:hover:!disabled {
            background-color: #4b38df;
            color: white;
        }

        #setButton:pressed:!disabled {
            background-color: #3726b7;
        }

        #setButton:disabled {
            background-color: #20294a;
            color: #5a6d96;
        }

        #presetButton {
            background-color: #182545;
            border: 1px solid #1d2d53;
            border-radius: 8px;
            color: #7f93bd;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 600;
        }

        #presetButton:hover:!disabled {
            background-color: #22345d;
            color: #dfe8fb;
        }

        #presetButton:pressed:!disabled {
            background-color: #1b2b4d;
        }

        #presetButton:disabled {
            background-color: #121d38;
            color: #51658f;
            border: 1px solid #1b2948;
        }

        #fieldLabelSmall {
            font-size: 11px;
            font-weight: 600;
            color: #7e95bf;
        }

        #loopInput {
            background-color: #06122f;
            border: 1px solid #183261;
            border-radius: 8px;
            color: #eaf1ff;
            padding: 0 12px;
            font-size: 14px;
            font-weight: 600;
        }

        #loopInput:focus {
            border: 1px solid #4a68ff;
        }

        #loopInput:disabled {
            background-color: #0a1430;
            color: #51658f;
            border: 1px solid #16264a;
        }

        QCheckBox#loopCheck {
            color: #8ca5d3;
            font-size: 12px;
            font-weight: 600;
            spacing: 6px;
        }

        QCheckBox#loopCheck::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid #2a3b63;
            background-color: #06122f;
        }

        QCheckBox#loopCheck::indicator:checked {
            background-color: #3d2bc6;
            border: 1px solid #4b38df;
        }

        QCheckBox#loopCheck:disabled {
            color: #51658f;
        }

        #loopStartButton {
            background-color: #0f8f63;
            border: 1px solid #15e6a3;
            border-radius: 8px;
            color: white;
            font-size: 13px;
            font-weight: 800;
        }

        #loopStartButton:hover:!disabled {
            background-color: #11a36f;
            border-color: #42f0bd;
        }

        #loopStartButton:pressed:!disabled {
            background-color: #0d7f58;
        }

        #loopStartButton:disabled {
            background-color: #1a2642;
            color: #4f6287;
            border: 1px solid #2a3b63;
        }

        #loopStopButton {
            background-color: #a9153e;
            border: 1px solid #ff4f7b;
            border-radius: 8px;
            color: white;
            font-size: 13px;
            font-weight: 800;
        }

        #loopStopButton:hover:!disabled {
            background-color: #c31d4c;
            border-color: #ff6b91;
        }

        #loopStopButton:pressed:!disabled {
            background-color: #8d1134;
        }

        #loopStopButton:disabled {
            background-color: #1a2642;
            color: #4f6287;
            border: 1px solid #2a3b63;
        }

        #loopStatusLabel {
            font-size: 12px;
            font-weight: 600;
            color: #8ca5d3;
        }
        """

    def _set_controls_enabled(self, enabled: bool):
        """统一启用/禁用控制按钮"""
        self.power_btn.setEnabled(enabled)
        self.set_btn.setEnabled(enabled)
        for btn in self.preset_buttons:
            btn.setEnabled(enabled)
        if not enabled and self._loop_running:
            self._stop_loop(reason="Chamber disconnected")
        self.loop_start_btn.setEnabled(enabled and not self._loop_running)

    def _set_connection_ui(self, connected: bool):
        update_connect_button_state(self.connect_btn, connected)
        self.chamber_type_combo.setEnabled(not connected)
        self.port_combo.setEnabled(not connected)
        self.scan_btn.setEnabled(not connected)
        if connected:
            self.status_detail.setText(f"{chamber_display_name(self.current_chamber_type)} Connected & Ready")
            self.status_dot.setStyleSheet("color: #15e6a3; font-size: 16px;border: none")
            if self.isVisible():
                self._state_poller.resume()
        else:
            self.status_detail.setText("Disconnected")
            self.status_dot.setStyleSheet("color: #5d78a7; font-size: 16px;border: none")
            self._state_poller.pause()

    def _set_power_ui(self, chamber_on: bool, connected: bool | None = None):
        """更新温箱电源按钮样式"""
        if connected is None:
            connected = self._is_current_chamber_connected()
        self.is_chamber_on = bool(chamber_on) if connected else False
        self.power_btn.setEnabled(connected)

        if not connected:
            self.power_btn.setText("⏻  CHAMBER OFFLINE")
            self.power_btn.setStyleSheet("""
                QPushButton#powerButton {
                    background-color: #1a2642;
                    border: 1px solid #2a3b63;
                    border-radius: 8px;
                    color: #4f6287;
                    font-size: 15px;
                    font-weight: 800;
                    padding: 10px 16px;
                }
            """)
            return

        if chamber_on:
            self.power_btn.setText("⏻  STOP CHAMBER")
            self.power_btn.setStyleSheet("""
                QPushButton#powerButton {
                    background-color: #a9153e;
                    border: 1px solid #ff4f7b;
                    border-radius: 8px;
                    color: white;
                    font-size: 15px;
                    font-weight: 800;
                    padding: 10px 16px;
                }
                QPushButton#powerButton:hover {
                    background-color: #c31d4c;
                    border-color: #ff6b91;
                }
                QPushButton#powerButton:pressed {
                    background-color: #8d1134;
                }
            """)
            return

        self.power_btn.setText("⏻  START CHAMBER")
        self.power_btn.setStyleSheet("""
            QPushButton#powerButton {
                background-color: #0f8f63;
                border: 1px solid #15e6a3;
                border-radius: 8px;
                color: white;
                font-size: 15px;
                font-weight: 800;
                padding: 10px 16px;
            }
            QPushButton#powerButton:hover {
                background-color: #11a36f;
                border-color: #42f0bd;
            }
            QPushButton#powerButton:pressed {
                background-color: #0d7f58;
            }
        """)

    def _is_current_chamber_connected(self) -> bool:
        if self.chamber is None:
            return False
        if hasattr(self.chamber, "is_connected"):
            try:
                return bool(self.chamber.is_connected())
            except Exception:
                logger.debug("Chamber is_connected check failed", exc_info=True)
                return False
        return bool(hasattr(self.chamber, "ser") and self.chamber.ser is not None and self.chamber.ser.is_open)

    def _sync_power_state_from_chamber(self, allow_io: bool = True):
        connected = self._is_current_chamber_connected()
        if not connected:
            self._set_power_ui(False, connected=False)
            return
        chamber_on = self._read_chamber_running_state(allow_io=allow_io)
        if chamber_on is None:
            chamber_on = self.is_chamber_on
        self._set_power_ui(bool(chamber_on), connected=True)

    def _read_chamber_running_state(self, allow_io: bool = True):
        if self.chamber is None:
            return None
        cached = getattr(self.chamber, "_last_known_running_state", None)
        if not allow_io:
            return bool(cached) if cached is not None else None
        for method_name in ("is_running", "isRunning"):
            method = getattr(self.chamber, method_name, None)
            if callable(method):
                try:
                    running = bool(method())
                    setattr(self.chamber, "_last_known_running_state", running)
                    setattr(self.chamber, "_last_known_running_state_verified", True)
                    return running
                except Exception as e:
                    logger.warning("读取温箱运行状态失败: %s", e, exc_info=True)
                    return bool(cached) if cached is not None else None
        return bool(cached) if cached is not None else None

    def _scan_ports(self):
        chamber_type = self._selected_chamber_type()
        self._update_connection_resource_mode(chamber_type)
        if DEBUG_MOCK:
            self.port_combo.clear()
            self.port_combo.addItem(f"MOCK (Mock {chamber_type_label(chamber_type)})")
            return
        if chamber_uses_network(chamber_type):
            self.port_combo.clear()
            self.port_combo.addItem(chamber_default_resource(chamber_type))
            return
        try:
            from serial.tools.list_ports import comports
            ports = []
            for port in comports():
                ports.append(f"{port.device} ({port.description})")

            self.port_combo.clear()
            if ports:
                self.port_combo.addItems(ports)
            else:
                self.port_combo.addItem("No Serial Ports Found")
        except Exception as e:
            logger.error("扫描端口错误: %s", e)
            self.port_combo.clear()
            self.port_combo.addItem("Scan Failed")

    def _toggle_connection(self):
        is_connected = self.chamber is not None and (
            self.chamber.is_connected()
            if hasattr(self.chamber, "is_connected")
            else hasattr(self.chamber, "ser") and self.chamber.ser.is_open
        )

        if is_connected:
            try:
                if self._instrument_manager and self.current_chamber_session_id:
                    self._instrument_manager.disconnect_async(self.current_chamber_session_id)
                else:
                    self.chamber.close()
                    self.chamber = None
                    self.current_port = None
                    self.current_chamber_session_id = None
                    self.is_chamber_on = False

                    self._set_connection_ui(False)
                    self._set_controls_enabled(False)
                    self._set_power_ui(False, connected=False)
                    self.connection_changed.emit()
            except Exception as e:
                logger.error("断开连接错误: %s", e, exc_info=True)
        else:
            chamber_type = self._selected_chamber_type()
            current_text = self.port_combo.currentText().strip()
            if not current_text or current_text in ("No Serial Ports Found", "Scan Failed"):
                return

            try:
                device_port = f"MOCK::{chamber_type_label(chamber_type)}" if DEBUG_MOCK else current_text.split()[0]
                if self._instrument_manager:
                    from core.instruments import InstrumentSpec
                    self.current_chamber_session_id = self._instrument_manager.connect_async(InstrumentSpec(
                        instrument_type=chamber_type,
                        role="chamber",
                        connection_kind=chamber_connection_kind(chamber_type),
                        slot="default",
                        resource=device_port,
                    ))
                    return

                self.chamber = create_chamber(
                    chamber_type=chamber_type,
                    port=device_port,
                    baudrate=chamber_baudrate(chamber_type),
                )
                self.current_chamber_type = chamber_type
                self.current_port = device_port

                if self._instrument_manager:
                    from core.instruments import InstrumentSpec
                    self._instrument_manager.attach_external(
                        InstrumentSpec(
                            instrument_type=chamber_type,
                            role="chamber",
                            connection_kind=chamber_connection_kind(chamber_type),
                            resource=self.current_port,
                            slot="default",
                        ),
                        instance=self.chamber, serial="", model=chamber_type_label(chamber_type),
                    )
                self._set_connection_ui(True)
                self._set_controls_enabled(True)
                self._sync_power_state_from_chamber()
                self.connection_changed.emit()
            except Exception as e:
                logger.error("连接设备错误: %s", e, exc_info=True)
                self.chamber = None
                self.current_port = None
                self._set_connection_ui(False)
                self._set_controls_enabled(False)
                self._set_power_ui(False, connected=False)

    def _toggle_chamber_power(self):
        """切换温箱电源"""
        if self.chamber is None:
            return

        if self.is_chamber_on:
            try:
                if self._loop_running:
                    self._stop_loop(reason="Loop stopped: chamber powered off")
                with self._state_poller.writing():
                    self.chamber.stop()
                setattr(self.chamber, "_last_known_running_state", False)
                setattr(self.chamber, "_last_known_running_state_verified", True)
                self._set_power_ui(False, connected=True)
            except Exception as e:
                logger.error("关闭温箱错误: %s", e, exc_info=True)
        else:
            try:
                with self._state_poller.writing():
                    self.chamber.start()
                setattr(self.chamber, "_last_known_running_state", True)
                setattr(self.chamber, "_last_known_running_state_verified", True)
                self._set_power_ui(True, connected=True)
            except Exception as e:
                logger.error("打开温箱错误: %s", e, exc_info=True)

    def _set_temperature(self):
        """设置温度"""
        if self.chamber is None:
            return

        try:
            temp = float(self.temp_input.text())
            with self._state_poller.writing():
                self.chamber.set_temperature(temp)
            self.set_temp_value.setText(f"{temp:.1f} °C")
        except ValueError:
            logger.warning("设置温度错误: 输入不是有效数字")
        except Exception as e:
            logger.error("设置温度错误: %s", e)

    def _set_preset_temp(self, temp_str):
        """设置预设温度"""
        if self.chamber is None:
            return

        try:
            temp = float(temp_str.replace("°C", ""))
            self.temp_input.setText(str(temp))
            with self._state_poller.writing():
                self.chamber.set_temperature(temp)
            self.set_temp_value.setText(f"{temp:.1f} °C")
        except ValueError:
            logger.warning("设置预设温度错误: 输入不是有效数字")
        except Exception as e:
            logger.error("设置预设温度错误: %s", e)

    def _parse_loop_sequence(self):
        raw = self.loop_sequence_input.text().strip()
        sequence = []
        for token in raw.replace(";", ",").split(","):
            token = token.strip()
            if not token:
                continue
            try:
                sequence.append(float(token))
            except ValueError:
                raise ValueError(f"Invalid temperature value: '{token}'")
        return sequence

    def _start_loop(self):
        if self.chamber is None or self._loop_running:
            return
        try:
            sequence = self._parse_loop_sequence()
        except ValueError as e:
            self.loop_status_label.setText(f"Loop error: {e}")
            logger.warning("温度循环序列解析失败: %s", e)
            return
        if not sequence:
            self.loop_status_label.setText("Loop error: sequence is empty")
            return

        try:
            dwell_min = float(self.loop_dwell_input.text())
            if dwell_min < 0:
                raise ValueError
        except ValueError:
            self.loop_status_label.setText("Loop error: invalid dwell time")
            return
        try:
            tolerance = float(self.loop_tolerance_input.text())
            if tolerance <= 0:
                raise ValueError
        except ValueError:
            self.loop_status_label.setText("Loop error: invalid tolerance")
            return

        self._loop_forever = self.loop_forever_check.isChecked()
        if self._loop_forever:
            self._loop_cycles_total = 0
        else:
            try:
                cycles = int(float(self.loop_cycles_input.text()))
                if cycles < 1:
                    raise ValueError
            except ValueError:
                self.loop_status_label.setText("Loop error: invalid cycles")
                return
            self._loop_cycles_total = cycles

        self._loop_sequence = sequence
        self._loop_tolerance = tolerance
        self._loop_dwell_seconds = int(round(dwell_min * 60))
        self._loop_index = 0
        self._loop_cycle = 1
        self._loop_running = True
        self._loop_phase = "ramp"
        self._loop_dwell_remaining = 0

        try:
            if not self.is_chamber_on:
                self.chamber.start()
                setattr(self.chamber, "_last_known_running_state", True)
                setattr(self.chamber, "_last_known_running_state_verified", True)
                self._set_power_ui(True, connected=True)
        except Exception as e:
            logger.error("启动温箱以执行循环失败: %s", e, exc_info=True)
            self._loop_running = False
            self.loop_status_label.setText("Loop error: failed to start chamber")
            return

        self._set_loop_running_ui(True)
        self._state_poller.pause()
        self._apply_loop_target()
        self.loop_timer.start()
        logger.info(
            "温度循环开始: 序列=%s 保压=%ss 容差=%.1f°C 循环=%s",
            self._loop_sequence, self._loop_dwell_seconds, self._loop_tolerance,
            "forever" if self._loop_forever else self._loop_cycles_total,
        )

    def _stop_loop(self, reason: str = "Loop stopped"):
        was_running = self._loop_running
        self._loop_running = False
        self._loop_phase = "idle"
        self.loop_timer.stop()
        self._set_loop_running_ui(False)
        connected = self._is_current_chamber_connected()
        self.loop_start_btn.setEnabled(connected and True)
        self.loop_status_label.setText(reason)
        if connected and self.isVisible():
            self._state_poller.resume()
        if was_running:
            logger.info("温度循环停止: %s", reason)

    def _apply_loop_target(self):
        target = self._loop_sequence[self._loop_index]
        try:
            self.chamber.set_temperature(target)
            self.set_temp_value.setText(f"{target:.1f} °C")
            self.temp_input.setText(f"{target:.1f}")
        except Exception as e:
            logger.error("循环设置温度失败: %s", e, exc_info=True)
            self._stop_loop(reason="Loop error: failed to set temperature")
            return
        self._loop_phase = "ramp"
        self._update_loop_status()

    def _loop_tick(self):
        if not self._loop_running or self.chamber is None:
            return
        if not self._is_current_chamber_connected():
            self._stop_loop(reason="Loop error: chamber disconnected")
            return

        target = self._loop_sequence[self._loop_index]
        try:
            actual = self.chamber.get_current_temp()
        except Exception as e:
            logger.warning("循环读取温度失败: %s", e, exc_info=True)
            actual = None

        if self._loop_phase == "ramp":
            if actual is not None and abs(actual - target) <= self._loop_tolerance:
                self._loop_phase = "dwell"
                self._loop_dwell_remaining = self._loop_dwell_seconds
            self._update_loop_status(actual)
        elif self._loop_phase == "dwell":
            if self._loop_dwell_remaining > 0:
                self._loop_dwell_remaining -= 1
                self._update_loop_status(actual)
            else:
                self._advance_loop()

    def _advance_loop(self):
        self._loop_index += 1
        if self._loop_index >= len(self._loop_sequence):
            self._loop_index = 0
            if not self._loop_forever:
                if self._loop_cycle >= self._loop_cycles_total:
                    self._stop_loop(reason="Loop finished")
                    return
            self._loop_cycle += 1
        self._apply_loop_target()

    def _update_loop_status(self, actual=None):
        if not self._loop_running:
            return
        target = self._loop_sequence[self._loop_index]
        step_txt = f"Step {self._loop_index + 1}/{len(self._loop_sequence)}"
        if self._loop_forever:
            cycle_txt = f"Cycle {self._loop_cycle}/∞"
        else:
            cycle_txt = f"Cycle {self._loop_cycle}/{self._loop_cycles_total}"
        actual_txt = "--" if actual is None else f"{actual:.1f}"
        if self._loop_phase == "ramp":
            phase_txt = f"Ramping to {target:.1f} °C (now {actual_txt} °C)"
        elif self._loop_phase == "dwell":
            mins, secs = divmod(max(0, self._loop_dwell_remaining), 60)
            phase_txt = (
                f"Holding {target:.1f} °C, {mins:02d}:{secs:02d} left "
                f"(now {actual_txt} °C)"
            )
        else:
            phase_txt = ""
        self.loop_status_label.setText(f"{cycle_txt} · {step_txt} · {phase_txt}")

    def _set_loop_running_ui(self, running: bool):
        self.loop_start_btn.setEnabled(not running)
        self.loop_stop_btn.setEnabled(running)
        self.loop_sequence_input.setEnabled(not running)
        self.loop_dwell_input.setEnabled(not running)
        self.loop_tolerance_input.setEnabled(not running)
        self.loop_cycles_input.setEnabled(not running)
        self.loop_forever_check.setEnabled(not running)
        self.set_btn.setEnabled(not running and self._is_current_chamber_connected())
        for btn in self.preset_buttons:
            btn.setEnabled(not running and self._is_current_chamber_connected())

    def _is_chamber_session_busy(self):
        if not self._instrument_manager or not self.current_chamber_session_id:
            return False
        session = self._instrument_manager.get_session(self.current_chamber_session_id)
        if session and session.connected:
            return bool(session.busy)
        return False

    def _read_chamber_snapshot(self):
        if self.chamber is None:
            return None
        if hasattr(self.chamber, "is_connected"):
            try:
                is_connected = bool(self.chamber.is_connected())
            except Exception:
                is_connected = False
        else:
            is_connected = hasattr(self.chamber, 'ser') and self.chamber.ser is not None and self.chamber.ser.is_open

        snapshot = {"connected": is_connected}
        if not is_connected:
            return snapshot

        try:
            snapshot["actual_temp"] = self.chamber.get_current_temp()
        except Exception:
            snapshot["actual_temp"] = None
        try:
            snapshot["set_temp"] = self.chamber.get_set_temp()
        except Exception:
            snapshot["set_temp"] = None
        snapshot["running"] = self._read_chamber_running_state(allow_io=True)
        return snapshot

    def _apply_chamber_snapshot(self, snapshot):
        if not snapshot.get("connected"):
            self.temp_gauge.set_temperature(None)
            self._set_power_ui(False, connected=False)
            return

        actual_temp = snapshot.get("actual_temp")
        if actual_temp is not None:
            self.temp_gauge.set_temperature(actual_temp)

        set_temp = snapshot.get("set_temp")
        if set_temp is not None:
            self.set_temp_value.setText(f"{set_temp:.1f} °C")

        chamber_on = snapshot.get("running")
        if chamber_on is None:
            chamber_on = self.is_chamber_on
        self._set_power_ui(bool(chamber_on), connected=True)

    def showEvent(self, event):
        super().showEvent(event)
        if self._is_current_chamber_connected():
            self._state_poller.resume()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._state_poller.pause()

    def closeEvent(self, event):
        self._state_poller.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    """测试温箱界面"""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from ui.standalone import resize_and_center_window

    def custom_message_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return
        logger.debug("%s:%s - %s", context.file, context.line, message)

    qInstallMessageHandler(custom_message_handler)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ChamberControlUI()
    window.setWindowTitle("Chamber Test")
    resize_and_center_window(window)
    window.show()

    sys.exit(app.exec())
    
