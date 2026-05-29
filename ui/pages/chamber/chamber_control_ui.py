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
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QLineEdit, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QApplication, QGridLayout
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
    chamber_display_name,
    chamber_type_label,
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
        self.timer = QTimer()
        self.is_chamber_on = False
        self.current_chamber_type = "vt6002"
        self.current_chamber_session_id = None
        self.current_port = None
        self.preset_buttons = []

        # 初始化界面
        self._setup_ui()
        self._connect_signals()

        # 开始定时更新温度
        self.timer.start(1000)

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

        subtitle_label = QLabel("Thermal chamber control and monitoring via serial port.")
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

        connection_title = QLabel("Serial Connection")
        connection_title.setObjectName("connectionTitle")
        connection_title.setStyleSheet("border: none")

        connection_subtitle = QLabel("Select chamber model and COM port")
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

        port_label = QLabel("COM Port")
        port_label.setObjectName("fieldLabel")
        port_label.setStyleSheet("border: none")

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
        form_layout.addWidget(port_label, 0, 1)
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

        control_layout.addWidget(power_panel)
        control_layout.addWidget(temp_panel)
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
        self.timer.timeout.connect(self._update_temperatures)
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
            self._set_power_ui(False)
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
        self._set_power_ui(False)
        self.connection_changed.emit()

    def _on_manager_connect_failed(self, session_id: str, error: str):
        if session_id != self.current_chamber_session_id and not session_id.endswith(":chamber"):
            return
        logger.error("Chamber connection failed via manager: %s", error)
        self._set_connection_ui(False)
        self._set_controls_enabled(False)

    def _on_chamber_type_changed(self):
        self.current_chamber_type = self._selected_chamber_type()
        if self.chamber is None:
            self.port_combo.clear()

    def _selected_chamber_type(self):
        data = self.chamber_type_combo.currentData()
        return str(data or self.current_chamber_type or "vt6002")

    def _set_type_combo(self, chamber_type: str):
        idx = self.chamber_type_combo.findData(chamber_type)
        if idx >= 0:
            self.chamber_type_combo.setCurrentIndex(idx)

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
        """

    def _set_controls_enabled(self, enabled: bool):
        """统一启用/禁用控制按钮"""
        self.power_btn.setEnabled(enabled)
        self.set_btn.setEnabled(enabled)
        for btn in self.preset_buttons:
            btn.setEnabled(enabled)

    def _set_connection_ui(self, connected: bool):
        update_connect_button_state(self.connect_btn, connected)
        self.chamber_type_combo.setEnabled(not connected)
        self.port_combo.setEnabled(not connected)
        self.scan_btn.setEnabled(not connected)
        if connected:
            self.status_detail.setText(f"{chamber_display_name(self.current_chamber_type)} Connected & Ready")
            self.status_dot.setStyleSheet("color: #15e6a3; font-size: 16px;border: none")
        else:
            self.status_detail.setText("Disconnected")
            self.status_dot.setStyleSheet("color: #5d78a7; font-size: 16px;border: none")

    def _set_power_ui(self, chamber_on: bool):
        """更新温箱电源按钮样式"""
        if chamber_on:
            self.power_btn.setText("⏻  CHAMBER ON")
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
                }
                QPushButton#powerButton:pressed {
                    background-color: #0d7f58;
                }
            """)
        else:
            self.power_btn.setText("⏻  TURN ON CHAMBER")
            self.power_btn.setStyleSheet("""
                QPushButton#powerButton {
                    background-color: #223150;
                    border: 1px solid #34486f;
                    border-radius: 8px;
                    color: #5f7397;
                    font-size: 15px;
                    font-weight: 800;
                    padding: 10px 16px;
                }
                QPushButton#powerButton:hover:!disabled {
                    background-color: #2a3a5e;
                }
                QPushButton#powerButton:pressed:!disabled {
                    background-color: #243350;
                }
                QPushButton#powerButton:disabled {
                    background-color: #1a2642;
                    color: #4f6287;
                    border: 1px solid #2a3b63;
                }
            """)

    def _scan_ports(self):
        chamber_type = self._selected_chamber_type()
        if DEBUG_MOCK:
            self.port_combo.clear()
            self.port_combo.addItem(f"MOCK (Mock {chamber_type_label(chamber_type)})")
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
                    self._set_power_ui(False)
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
                self._set_power_ui(False)
                self.connection_changed.emit()
            except Exception as e:
                logger.error("连接设备错误: %s", e, exc_info=True)
                self.chamber = None
                self.current_port = None
                self._set_connection_ui(False)
                self._set_controls_enabled(False)

    def _toggle_chamber_power(self):
        """切换温箱电源"""
        if self.chamber is None:
            return

        if self.is_chamber_on:
            try:
                self.chamber.stop()
                self.is_chamber_on = False
                self._set_power_ui(False)
            except Exception as e:
                logger.error("关闭温箱错误: %s", e)
        else:
            try:
                self.chamber.start()
                self.is_chamber_on = True
                self._set_power_ui(True)
            except Exception as e:
                logger.error("打开温箱错误: %s", e)

    def _set_temperature(self):
        """设置温度"""
        if self.chamber is None:
            return

        try:
            temp = float(self.temp_input.text())
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
            self.chamber.set_temperature(temp)
            self.set_temp_value.setText(f"{temp:.1f} °C")
        except ValueError:
            logger.warning("设置预设温度错误: 输入不是有效数字")
        except Exception as e:
            logger.error("设置预设温度错误: %s", e)

    def _update_temperatures(self):
        if self.chamber is not None and hasattr(self.chamber, "is_connected"):
            is_connected = self.chamber.is_connected()
        else:
            is_connected = self.chamber is not None and hasattr(self.chamber, 'ser') and self.chamber.ser.is_open

        if is_connected:
            try:
                actual_temp = self.chamber.get_current_temp()
                if actual_temp is not None:
                    self.temp_gauge.set_temperature(actual_temp)

                set_temp = self.chamber.get_set_temp()
                if set_temp is not None:
                    self.set_temp_value.setText(f"{set_temp:.1f} °C")
            except Exception as e:
                logger.error("更新温度错误: %s", e)
        else:
            self.temp_gauge.set_temperature(None)


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
    
