#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import pyqtgraph as pg
from PySide6.QtCore import (
    QByteArray,
    QPointF,
    QRect,
    QSize,
    Qt,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from core.ai.ui_action_registry import UIActionSpec
from instruments.power.keysight.n6705c_datalog_process import parse_channel_label
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.pages.n6705c_power_analyzer.n6705c_datalog_help import DatalogHelpDialog, GuideTourOverlay
from ui.pages.n6705c_power_analyzer.n6705c_settings_dialog import N6705CSettingsDialog
from ui.pages.n6705c_power_analyzer.widgets import SelectAllLineEdit
from resource_path import get_resource_base
from ui.styles import SCROLL_AREA_STYLE
from ui.widgets.button import SpinningSearchButton
from ui.pages.n6705c_power_analyzer.datalog.helpers import _build_summary_stages, _make_svg_icon, _render_waveform_summary_image
from ui.pages.n6705c_power_analyzer.datalog.widgets import CardFrame, ChannelConfigTabBar, ClickableHeader, FixedPopupComboBox
from log_config import get_logger

logger = get_logger(__name__)

class LayoutViewMixin:
    """Datalog 页布局视图：样式 / 布局 / 卡片构建 / 面板显隐 / 设置与帮助入口 / 窗口几何。"""

    def _register_ai_ui_actions(self):
        """§5b.5：登记本页无专用接口的按钮为 AI 可触发的具名 UI 动作。

        handler 直接复用按钮原 clicked.connect 的槽（_reset_view / _on_export / _on_import），
        行为与人点按钮完全一致；导出类绑定 datalog_data 前置校验，无数据时
        list_ui_actions 不返回、ui_invoke 明示不可用（不盲点）。
        """
        registry = self._ui_action_registry
        if registry is None:
            return

        def _wrap(label, fn):
            def _run() -> tuple[bool, str]:
                try:
                    fn()
                    return True, f"{label} 已执行。"
                except Exception as exc:  # noqa: BLE001
                    logger.error("%s 执行失败", label, exc_info=True)
                    return False, f"{label} 执行失败：{exc}"
            return _run

        registry.register_many([
            UIActionSpec(
                id="datalog.auto_fit",
                label="Auto Fit 自适应视图",
                page_key="datalog",
                handler=_wrap("Auto Fit 自适应视图", self._reset_view),
                risk="low",
                confirm=False,
                description="把 Datalog 波形图缩放还原到自适应视图。",
            ),
            UIActionSpec(
                id="datalog.export",
                label="导出 Datalog",
                page_key="datalog",
                handler=_wrap("导出 Datalog", self._on_export),
                risk="low",
                confirm=False,
                enabled_when=lambda: bool(self.datalog_data),
                description="导出当前 Datalog 数据。需已有采集/导入的数据。",
            ),
            UIActionSpec(
                id="datalog.import",
                label="导入 Datalog",
                page_key="datalog",
                handler=_wrap("导入 Datalog", self._on_import),
                risk="low",
                confirm=False,
                description="从文件导入历史 Datalog 数据用于查看/对比。",
            ),
        ])

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        _cb_icons = self._get_checkmark_path("4f46e5")
        full_style = ("""
            QWidget {
                background-color: #020817;
                color: #dbe7ff;
            }

            QLabel {
                background-color: transparent;
                color: #dbe7ff;
                border: none;
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
                color: #9abee8;
                font-size: 11px;
                background-color: transparent;
            }

            QLabel#hintLabel {
                color: #708fad;
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
                border-radius: 6px;
            }

            QFrame#topControlsFrame {
                background-color: #0a1733;
                border: 1px solid #1a2b52;
                border-radius: 6px;
            }

            QFrame#chartFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 6px;
            }

            QFrame#chResultCard {
                background-color: #0a1733;
                border: 1px solid #1a2b52;
                border-radius: 6px;
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
                border-radius: 4px;
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
                border-radius: 4px;
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
                color: #6b82a3;
                border: 1px solid #1a2850;
            }

            QPushButton#chartToolBtn {
                min-height: 28px;
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #13254b;
                color: #dce7ff;
                font-size: 11px;
            }

            QPushButton#chartToolBtn:hover {
                background-color: #1a3260;
                border: 1px solid #3c5fa1;
            }

            QPushButton#chartToolBtn:pressed {
                background-color: #0d1a37;
            }

            QPushButton#chartIconBtn {
                min-width: 30px;
                max-width: 30px;
                min-height: 28px;
                max-height: 28px;
                padding: 0px;
                border-radius: 4px;
                border: 1px solid transparent;
                background-color: #13254b;
            }

            QPushButton#chartIconBtn:hover {
                background-color: #1a3260;
                border: 1px solid #3c5fa1;
            }

            QPushButton#chartIconBtn:pressed {
                background-color: #0d1a37;
            }

            QPushButton#chartIconBtn:checked {
                background-color: rgba(56, 189, 248, 26);
                border: 1px solid rgba(56, 189, 248, 128);
            }

            QPushButton#chartIconBtn[accent="gold"]:checked {
                background-color: rgba(234, 179, 8, 26);
                border: 1px solid rgba(234, 179, 8, 128);
            }

            QPushButton#chartIconBtn[accent="cyan"]:checked {
                background-color: rgba(34, 211, 238, 26);
                border: 1px solid rgba(34, 211, 238, 128);
            }

            QPushButton#chartIconBtn:disabled {
                background-color: #0e1c3a;
                border: 1px solid transparent;
            }

            QPushButton#primaryActionBtn {
                min-height: 40px;
                border-radius: 4px;
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
                border-radius: 4px;
                background-color: #16284f;
                color: #dfe8ff;
            }

            QPushButton#exportBtn:hover {
                background-color: #1e3466;
            }

            QPushButton#addLabelBtn {
                min-height: 30px;
                padding: 0px 8px;
                border-radius: 4px;
                background-color: #5b5cf6;
                color: white;
                font-size: 22px;
                font-weight: 700;
            }

            QPushButton#addLabelBtn:hover {
                background-color: #6b6cff;
            }

            QPushButton#addLabelBtn:pressed {
                background-color: #4a4be0;
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

            QPushButton#railIconBtn {
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                padding: 0px;
                border-radius: 3px;
                border: 1px solid transparent;
                background-color: transparent;
            }

            QPushButton#railIconBtn:hover {
                background-color: #16294f;
                border: 1px solid transparent;
            }

            QPushButton#railIconBtn:checked {
                background-color: #1a3260;
                border: 1px solid #3a6fd4;
            }

            QPushButton#primaryActionBtn {
                min-height: 34px;
                max-height: 34px;
                padding: 0px 18px;
            }

            QPushButton#exportBtn {
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                padding: 0px;
            }

            QPushButton#bottomSettingsBtn {
                min-width: 34px;
                max-width: 34px;
                min-height: 34px;
                max-height: 34px;
                padding: 0px;
                border-radius: 4px;
                border: none;
                background-color: transparent;
            }

            QPushButton#bottomSettingsBtn:hover {
                background-color: #1a3260;
            }
        """ + SCROLL_AREA_STYLE).replace("__UNCHECKED__", _cb_icons['unchecked']).replace("__CHECKED__", _cb_icons['checked'])
        self.setStyleSheet(full_style)

    @staticmethod
    def _svg_icon_label(svg_file, color="#d4a514", size=20):
        svg_path = os.path.join(get_resource_base(), "resources", "pages", "n6705c_power_analyzer_SVGs", svg_file)
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_data = f.read().replace("currentColor", color)
        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        lbl = QLabel()
        lbl.setPixmap(pixmap)
        lbl.setFixedSize(size, size)
        lbl.setStyleSheet("border: none; background: transparent;")
        return lbl

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        self.page_subtitle = QLabel(
            "Record, analyze, and export high-resolution datalogs from the N6705C."
        )
        self.page_subtitle.setObjectName("pageSubtitle")
        title_layout.addWidget(self.page_subtitle)

        root_layout.addLayout(title_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(6)
        root_layout.addLayout(content_layout, 1)

        # --- 左侧窄边栏（单图标 rail：Settings / Instrument Connection 互斥单开）---
        self.left_rail = QWidget()
        self.left_rail.setObjectName("leftRail")
        self.left_rail.setStyleSheet("QWidget#leftRail { background: transparent; }")
        rail_layout = QVBoxLayout(self.left_rail)
        rail_layout.setContentsMargins(0, 0, 0, 0)
        rail_layout.setSpacing(6)

        self._rail_icon_normal = "#8eb0e3"
        self._rail_icon_active = "#dce7ff"

        self.rail_settings_btn = QPushButton()
        self.rail_settings_btn.setObjectName("railIconBtn")
        self.rail_settings_btn.setIcon(_make_svg_icon("settings.svg", self._rail_icon_normal, 16, zoom=1.15))
        self.rail_settings_btn.setIconSize(QSize(16, 16))
        self.rail_settings_btn.setCheckable(True)
        self.rail_settings_btn.setToolTip("Settings")
        self.rail_settings_btn.clicked.connect(self._toggle_settings_panel)
        rail_layout.addWidget(self.rail_settings_btn, 0, Qt.AlignTop)

        self.rail_instrument_btn = QPushButton()
        self.rail_instrument_btn.setObjectName("railIconBtn")
        self.rail_instrument_btn.setIcon(_make_svg_icon("link-connect.svg", self._rail_icon_normal, 16, zoom=1.15))
        self.rail_instrument_btn.setIconSize(QSize(16, 16))
        self.rail_instrument_btn.setCheckable(True)
        self.rail_instrument_btn.setToolTip("Instrument Connection")
        self.rail_instrument_btn.clicked.connect(self._toggle_instrument_panel)
        rail_layout.addWidget(self.rail_instrument_btn, 0, Qt.AlignTop)

        rail_layout.addStretch()
        content_layout.addWidget(self.left_rail)

        # --- 左侧面板宿主：设置面板与仪器面板互斥单开，全收起时仅剩窄边栏 ---
        self.left_panel_host = QWidget()
        self.left_panel_host.setStyleSheet("QWidget { background: transparent; }")
        host_layout = QHBoxLayout(self.left_panel_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        self.settings_panel = QFrame()
        self.settings_panel.setObjectName("topControlsFrame")
        self.settings_panel.setFixedWidth(240)
        self.settings_panel.hide()
        settings_inner = QVBoxLayout(self.settings_panel)
        settings_inner.setContentsMargins(8, 8, 8, 8)
        settings_inner.setSpacing(8)

        self.settings_panel_header = ClickableHeader(
            "SETTINGS", svg_icon="settings.svg", svg_color="#8eb0e3"
        )
        self.settings_panel_header.setToolTip("Collapse")
        self.settings_panel_header.clicked.connect(self._collapse_settings_panel)
        settings_inner.addWidget(self.settings_panel_header)

        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        settings_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }" + SCROLL_AREA_STYLE
        )
        settings_container = QWidget()
        settings_container.setStyleSheet("background: transparent;")
        settings_panel_layout = QVBoxLayout(settings_container)
        settings_panel_layout.setContentsMargins(0, 0, 4, 0)
        settings_panel_layout.setSpacing(12)

        self.config_card = CardFrame("DATALOG CONFIG", svg_icon="settings.svg", svg_color="#8eb0e3")
        self._build_config_card()
        settings_panel_layout.addWidget(self.config_card)

        self.meas_settings_card = CardFrame("Measurement Settings", svg_icon="crosshair.svg", svg_color="#8eb0e3")
        self._build_meas_settings_card()
        settings_panel_layout.addWidget(self.meas_settings_card)
        settings_panel_layout.addStretch()

        settings_scroll.setWidget(settings_container)
        settings_inner.addWidget(settings_scroll, 1)
        host_layout.addWidget(self.settings_panel)

        self.instrument_panel = QFrame()
        self.instrument_panel.setObjectName("topControlsFrame")
        self.instrument_panel.setFixedWidth(360)
        self.instrument_panel.hide()
        instr_inner = QVBoxLayout(self.instrument_panel)
        instr_inner.setContentsMargins(8, 8, 8, 8)
        instr_inner.setSpacing(8)

        self.instrument_panel_header = ClickableHeader(
            "INSTRUMENT CONNECTION", svg_icon="link-connect.svg", svg_color="#8eb0e3"
        )
        self.instrument_panel_header.setToolTip("Collapse")
        self.instrument_panel_header.clicked.connect(self._collapse_instrument_panel)
        instr_inner.addWidget(self.instrument_panel_header)

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.refresh_search_btn = SpinningSearchButton()
        self.refresh_search_btn.setFixedSize(40, 40)
        self.refresh_search_btn.setStyleSheet(dss.SEARCH_BTN_STYLE)
        self.refresh_search_btn.clicked.connect(self._on_refresh_search)
        search_row.addWidget(self.refresh_search_btn)
        search_row.addStretch()

        self.instr_more_btn = QToolButton()
        self.instr_more_btn.setIcon(_make_svg_icon("more-horizontal.svg", "#8eb0e3", 18))
        self.instr_more_btn.setFixedSize(40, 40)
        self.instr_more_btn.setPopupMode(QToolButton.InstantPopup)
        self.instr_more_btn.setStyleSheet(dss.MORE_BTN_STYLE)
        instr_more_menu = QMenu(self.instr_more_btn)
        instr_more_menu.setStyleSheet(dss.INSTR_MENU_STYLE)
        add_manual_action = instr_more_menu.addAction(_make_svg_icon("link-connect.svg", "#8eb0e3", 14), "Add Instrument Manually")
        add_manual_action.triggered.connect(self._on_add_instrument_manually)
        self.instr_more_btn.setMenu(instr_more_menu)
        search_row.addWidget(self.instr_more_btn)

        instr_inner.addLayout(search_row)

        self.device_list_scroll = QScrollArea()
        self.device_list_scroll.setWidgetResizable(True)
        self.device_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.device_list_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }" + SCROLL_AREA_STYLE
        )
        self.device_list_container = QWidget()
        self.device_list_container.setStyleSheet("background: transparent;")
        self.device_list_layout = QVBoxLayout(self.device_list_container)
        self.device_list_layout.setContentsMargins(0, 0, 0, 0)
        self.device_list_layout.setSpacing(6)
        self.device_list_layout.addStretch()
        self.device_list_scroll.setWidget(self.device_list_container)
        instr_inner.addWidget(self.device_list_scroll, 1)

        self.device_cards = []

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(dss.SEPARATOR_LINE_STYLE)
        instr_inner.addWidget(separator)

        slot_title_row = QHBoxLayout()
        slot_title_row.setSpacing(6)
        slot_title_row.setContentsMargins(0, 0, 0, 0)
        slot_title_icon = self._svg_icon_label("zap.svg", "#8eb0e3", 14)
        slot_title = QLabel("Available Instruments")
        slot_title.setObjectName("cardTitle")
        slot_title_row.addWidget(slot_title_icon)
        slot_title_row.addWidget(slot_title)
        slot_title_row.addStretch()
        instr_inner.addLayout(slot_title_row)

        slot_grid = QGridLayout()
        slot_grid.setSpacing(6)

        self.slot_frames = {}
        for idx, label_char in enumerate(["A", "B", "C", "D"]):
            slot = self._create_slot_widget(label_char)
            row, col = divmod(idx, 2)
            slot_grid.addWidget(slot, row, col)
            self.slot_frames[label_char] = slot

        instr_inner.addLayout(slot_grid)

        host_layout.addWidget(self.instrument_panel)

        content_layout.addWidget(self.left_panel_host)

        main_area = QVBoxLayout()
        main_area.setSpacing(6)
        content_layout.addLayout(main_area, 1)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(6)

        # 中列：Datalog Viewer + MEASUREMENT（上）与 Channel Config（下）同宽对齐
        center_col_layout = QVBoxLayout()
        center_col_layout.setSpacing(6)

        chart_and_meas_layout = QVBoxLayout()
        chart_and_meas_layout.setSpacing(6)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartFrame")
        chart_outer = QVBoxLayout(self.chart_frame)
        chart_outer.setContentsMargins(12, 3, 12, 10)
        chart_outer.setSpacing(8)

        chart_header = QHBoxLayout()
        chart_icon = self._svg_icon_label("sparkles.svg", "#d4a514", 16)
        chart_title = QLabel("Datalog Viewer")
        chart_title.setStyleSheet(dss.CHART_TITLE_STYLE)
        chart_header.addWidget(chart_icon)
        chart_header.addWidget(chart_title)
        chart_header.addStretch()

        self.box_zoom_btn = QPushButton()
        self.box_zoom_btn.setObjectName("chartIconBtn")
        self.box_zoom_btn.setProperty("accent", "sky")
        self.box_zoom_btn.setIcon(_make_svg_icon("box-select.svg", "#38bdf8", 16))
        self.box_zoom_btn.setCheckable(True)
        self.box_zoom_btn.setToolTip("框选缩放: OFF")
        chart_header.addWidget(self.box_zoom_btn)

        self.reset_view_btn = QPushButton()
        self.reset_view_btn.setObjectName("chartIconBtn")
        self.reset_view_btn.setIcon(_make_svg_icon("fit-view.svg", "#38bdf8", 16))
        self.reset_view_btn.setToolTip("自动适配视图")
        chart_header.addWidget(self.reset_view_btn)

        self.marker_a_btn = QPushButton()
        self.marker_a_btn.setObjectName("chartIconBtn")
        self.marker_a_btn.setProperty("accent", "gold")
        self.marker_a_btn.setIcon(_make_svg_icon("marker-a.svg", "#eab308", 16))
        self.marker_a_btn.setCheckable(True)
        self.marker_a_btn.setToolTip("Marker A: 点击进入放置模式")
        self.marker_a_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        chart_header.addWidget(self.marker_a_btn)

        self.marker_b_btn = QPushButton()
        self.marker_b_btn.setObjectName("chartIconBtn")
        self.marker_b_btn.setProperty("accent", "cyan")
        self.marker_b_btn.setIcon(_make_svg_icon("marker-b.svg", "#22d3ee", 16))
        self.marker_b_btn.setCheckable(True)
        self.marker_b_btn.setToolTip("Marker B: 点击进入放置模式")
        self.marker_b_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        chart_header.addWidget(self.marker_b_btn)

        self.add_markers_btn = QPushButton()
        self.add_markers_btn.setObjectName("chartIconBtn")
        self.add_markers_btn.setIcon(_make_svg_icon("markers-add.svg", "#38bdf8", 16))
        self.add_markers_btn.setToolTip("添加标记 (当前已加: 0 组)")
        chart_header.addWidget(self.add_markers_btn)

        self._clear_markers_icon_normal = _make_svg_icon("markers-clear.svg", "#94a3b8", 16)
        self._clear_markers_icon_hover = _make_svg_icon("markers-clear.svg", "#f87171", 16)
        self.clear_markers_btn = QPushButton()
        self.clear_markers_btn.setObjectName("chartIconBtn")
        self.clear_markers_btn.setIcon(self._clear_markers_icon_normal)
        self.clear_markers_btn.setToolTip("清除标记")
        self.clear_markers_btn.setEnabled(False)
        self.clear_markers_btn.installEventFilter(self)
        chart_header.addWidget(self.clear_markers_btn)

        self.time_offset_btn = QPushButton()
        self.time_offset_btn.setObjectName("chartIconBtn")
        self.time_offset_btn.setProperty("accent", "sky")
        self.time_offset_btn.setIcon(_make_svg_icon("time-offset.svg", "#38bdf8", 16))
        self.time_offset_btn.setCheckable(True)
        self.time_offset_btn.setToolTip("时间偏移")
        self.time_offset_btn.hide()
        chart_header.addWidget(self.time_offset_btn)

        chart_outer.addLayout(chart_header)

        self.plot_widget = pg.PlotWidget()
        self._setup_plot()

        self.ch_name_labels = []
        self.ch_name_renames = {}
        self._ch_label_items = []
        self._ch_label_range_connected = False

        chart_outer.addWidget(self.plot_widget, 1)

        self._progress_overlay = QFrame(self.chart_frame)
        self._progress_overlay.setStyleSheet(dss.PROGRESS_OVERLAY_STYLE)
        self._progress_overlay.hide()
        overlay_layout = QVBoxLayout(self._progress_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setSpacing(12)

        self._progress_stage_label = QLabel("Preparing...")
        self._progress_stage_label.setAlignment(Qt.AlignCenter)
        self._progress_stage_label.setStyleSheet(dss.PROGRESS_STAGE_STYLE)
        overlay_layout.addWidget(self._progress_stage_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFixedWidth(320)
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.setStyleSheet(dss.PROGRESS_BAR_STYLE)
        overlay_layout.addWidget(self._progress_bar, 0, Qt.AlignCenter)

        self._progress_time_label = QLabel("")
        self._progress_time_label.setAlignment(Qt.AlignCenter)
        self._progress_time_label.setStyleSheet(dss.PROGRESS_TIME_STYLE)
        overlay_layout.addWidget(self._progress_time_label)

        chart_and_meas_layout.addWidget(self.chart_frame, 1)

        # 无独立标题行：MEASUREMENT 图标+标题放入结果表左上角表头单元格，省一行高度
        self.measurement_card = CardFrame()
        self.measurement_card.main_layout.setContentsMargins(14, 2, 14, 6)
        self._build_measurement_card()
        chart_and_meas_layout.addWidget(self.measurement_card)

        center_col_layout.addLayout(chart_and_meas_layout, 1)

        # Custom Labels 展开/折叠入口在标题栏（一键截图右侧），页面内不再放切换按钮
        self.label_card = CardFrame("CUSTOM LABELS", svg_icon="tag.svg", svg_color="#8eb0e3")
        self.label_card.setFixedWidth(240)
        self.label_card.set_header_clickable("Collapse")
        self.label_card.header_clicked.connect(self._collapse_label_card_panel)
        self._build_label_card()
        self.label_card.hide()

        mid_layout.addLayout(center_col_layout, 1)
        mid_layout.addWidget(self.label_card)
        main_area.addLayout(mid_layout, 1)

        # --- 底部控制栏：Start/Export/Import 靠左（统一高度），设置齿轮靠右 ---
        self.bottom_bar = QWidget()
        self.bottom_bar.setObjectName("bottomBar")
        self.bottom_bar.setStyleSheet("QWidget#bottomBar { background: transparent; }")
        bottom_bar_layout = QHBoxLayout(self.bottom_bar)
        bottom_bar_layout.setContentsMargins(0, 0, 0, 0)
        bottom_bar_layout.setSpacing(8)

        self.start_btn = QPushButton("Start Recording")
        self.start_btn.setIcon(_make_svg_icon("play.svg", "#ffffff", 16))
        self.start_btn.setObjectName("primaryActionBtn")
        self.start_btn.setProperty("running", "false")
        bottom_bar_layout.addWidget(self.start_btn)

        self.export_btn = QPushButton()
        self.export_btn.setIcon(_make_svg_icon("download.svg"))
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.setToolTip("Export Datalog")
        bottom_bar_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton()
        self.import_btn.setIcon(_make_svg_icon("upload.svg"))
        self.import_btn.setObjectName("exportBtn")
        self.import_btn.setToolTip("Import Datalog")
        bottom_bar_layout.addWidget(self.import_btn)

        bottom_bar_layout.addStretch()

        self.bottom_settings_btn = QPushButton()
        self.bottom_settings_btn.setObjectName("bottomSettingsBtn")
        self.bottom_settings_btn.setIcon(_make_svg_icon("settings.svg", "#8eb0e3", 16))
        self.bottom_settings_btn.setToolTip("Settings")
        self.bottom_settings_btn.clicked.connect(self._on_open_settings_dialog)
        bottom_bar_layout.addWidget(self.bottom_settings_btn)

        self.bottom_help_btn = QPushButton()
        self.bottom_help_btn.setObjectName("bottomSettingsBtn")
        self.bottom_help_btn.setIcon(_make_svg_icon("help-circle.svg", "#8eb0e3", 16))
        self.bottom_help_btn.setToolTip("Help / Guided Tour")
        self.bottom_help_btn.clicked.connect(self._on_open_help_dialog)
        bottom_bar_layout.addWidget(self.bottom_help_btn)

        main_area.addWidget(self.bottom_bar)

        self.channel_config_collapsed = False

        self.channel_config_outer = QWidget()
        self.channel_config_outer.setObjectName("chConfigOuter")
        self.channel_config_outer.setStyleSheet(dss.CH_CFG_OUTER_STYLE)
        ch_outer_layout = QVBoxLayout(self.channel_config_outer)
        ch_outer_layout.setContentsMargins(0, 0, 0, 0)
        ch_outer_layout.setSpacing(0)

        self.channel_config_header_row = QWidget()
        self.channel_config_header_row.setObjectName("chConfigHeaderRow")
        self.channel_config_header_row.setStyleSheet(dss.CH_CFG_HEADER_ROW_STYLE)
        self.channel_config_header_row.setFixedHeight(32)
        ch_header_layout = QHBoxLayout(self.channel_config_header_row)
        ch_header_layout.setContentsMargins(0, 0, 0, 0)
        ch_header_layout.setSpacing(0)

        self._ch_config_icon_collapsed = _make_svg_icon("panel-bottom.svg", "#8ea6cf", 20)
        self._ch_config_icon_expanded = _make_svg_icon("panel-bottom-close.svg", "#b8d0f0", 16)

        self.channel_config_toggle_btn = QPushButton("Channel Config")
        self.channel_config_toggle_btn.setIcon(self._ch_config_icon_expanded)
        self.channel_config_toggle_btn.setStyleSheet(dss.CH_CFG_TOGGLE_BTN_EXPANDED)
        self.channel_config_toggle_btn.clicked.connect(self._toggle_channel_config_panel)
        ch_header_layout.addWidget(self.channel_config_toggle_btn, 0)

        self.channel_config_tabbar_placeholder = QWidget()
        self.channel_config_tabbar_placeholder.setObjectName("chConfigTabbarHolder")
        self.channel_config_tabbar_placeholder.setStyleSheet(dss.CH_CFG_TABBAR_HOLDER_STYLE)
        ch_tabbar_placeholder_layout = QHBoxLayout(self.channel_config_tabbar_placeholder)
        ch_tabbar_placeholder_layout.setContentsMargins(4, 0, 0, 0)
        ch_tabbar_placeholder_layout.setSpacing(0)
        ch_header_layout.addWidget(self.channel_config_tabbar_placeholder, 1)

        ch_outer_layout.addWidget(self.channel_config_header_row)

        self.channel_config_card = CardFrame("", "")
        self.channel_config_card.main_layout.setContentsMargins(0, 0, 0, 6)
        self.channel_config_card.main_layout.setSpacing(0)
        self.channel_config_card.setStyleSheet(dss.CH_CFG_CARD_STYLE)
        self._build_channel_config_card()
        self.channel_config_card.setVisible(True)
        ch_outer_layout.addWidget(self.channel_config_card)

        center_col_layout.addWidget(self.channel_config_outer)

        self._channel_config_overlay = QFrame(self.channel_config_card)
        self._channel_config_overlay.setStyleSheet(dss.CH_CFG_OVERLAY_STYLE)
        self._channel_config_overlay.hide()
        ch_overlay_layout = QVBoxLayout(self._channel_config_overlay)
        ch_overlay_layout.setAlignment(Qt.AlignCenter)
        ch_lock_row = QHBoxLayout()
        ch_lock_row.setAlignment(Qt.AlignCenter)
        ch_lock_row.setSpacing(6)
        ch_lock_icon = self._svg_icon_label("lock.svg", "#5c7a9e", 14)
        ch_lock_row.addWidget(ch_lock_icon)
        ch_lock_label = QLabel("Recording in progress...")
        ch_lock_label.setAlignment(Qt.AlignCenter)
        ch_lock_label.setStyleSheet(dss.CH_LOCK_LABEL_STYLE)
        ch_lock_row.addWidget(ch_lock_label)
        ch_overlay_layout.addLayout(ch_lock_row)

    def _build_measurement_card(self):
        layout = self.measurement_card.main_layout

        self._meas_corner_icon = _make_svg_icon("crosshair.svg", "#8eb0e3", 12)
        self.meas_table = QTableWidget()
        self.meas_table.setObjectName("measTable")
        self.meas_table.setStyleSheet(dss.MEAS_TABLE_STYLE)
        self.meas_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.meas_table.setSelectionMode(QTableWidget.NoSelection)
        self.meas_table.setFocusPolicy(Qt.NoFocus)
        self.meas_table.setShowGrid(False)
        self.meas_table.verticalHeader().setVisible(False)
        self.meas_table.horizontalHeader().setStretchLastSection(True)
        self.meas_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.meas_table.horizontalHeader().setMinimumSectionSize(80)
        self.meas_table.setMinimumHeight(50)
        self.meas_table.setMaximumHeight(200)
        self.meas_table.setVisible(False)
        layout.addWidget(self.meas_table)

        self.analysis_hint_label = QLabel(
            "Load data to see measurements."
        )
        self.analysis_hint_label.setObjectName("hintLabel")
        self.analysis_hint_label.setAlignment(Qt.AlignCenter)
        self.analysis_hint_label.setWordWrap(True)
        layout.addWidget(self.analysis_hint_label)

    def _apply_meas_corner_title(self):
        """MEASUREMENT 图标+标题写入结果表左上角表头单元格（替代独立标题行）。"""
        hi = self.meas_table.horizontalHeaderItem(0)
        if hi is None:
            return
        hi.setText("MEASUREMENT")
        hi.setIcon(self._meas_corner_icon)
        hi.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def get_capture_pixmap(self):
        """一键截图目标：Datalog 波形卡（chart_frame）+ MEASUREMENT 卡 + Channel Config 纵向合成。

        MainWindow 顶栏截图按钮的最高优先级钩子；返回 None 时降级为整页截图。
        """
        pieces = []
        for widget in (self.chart_frame, self.measurement_card, self.channel_config_outer):
            if not isinstance(widget, QWidget) or not widget.isVisibleTo(self):
                continue
            pm = widget.grab()
            if not pm.isNull():
                pieces.append(pm)
        if not pieces:
            return None
        if len(pieces) == 1:
            return pieces[0]

        gap = 6  # 与 chart_and_meas_layout 行间距一致（逻辑像素）
        # grab() 返回带 devicePixelRatio 的物理像素图，合成图必须同 DPR，QPainter 按逻辑坐标绘制才不留空白
        dpr = pieces[0].devicePixelRatio()
        width = max(pm.width() for pm in pieces)
        height = sum(pm.height() for pm in pieces) + round(gap * dpr) * (len(pieces) - 1)
        merged = QPixmap(width, height)
        merged.setDevicePixelRatio(dpr)
        merged.fill(QColor("#020817"))  # 与 _setup_style 页面背景一致
        painter = QPainter(merged)
        try:
            y = 0.0
            for pm in pieces:
                painter.drawPixmap(QPointF(0, y), pm)
                y += pm.height() / dpr + gap
        finally:
            painter.end()
        return merged

    def get_waveform_summary_pixmap(self):
        """导出波形摘要图：基于 AI 摘要算法（build_waveform_digest）把波形压成
        平直线段示意图并标注阶段，下方附各阶段持续时长与平均电流汇总表。

        优先取电流通道（无电流通道时回退全部通道），无数据返回 None。
        """
        if not self.datalog_data:
            return None
        digest = self.build_waveform_digest()
        if digest is None or not getattr(digest, "stats", None):
            return None
        stats = [s for s in digest.stats if s.label in self.datalog_data]
        if not stats:
            return None
        current_stats = [s for s in stats if parse_channel_label(s.label)[1] == "I"]
        chosen = (current_stats or stats)[:8]
        sections = []
        for stat in chosen:
            channel = self.datalog_data.get(stat.label) or {}
            times = list(channel.get("time") or [])
            values = list(channel.get("values") or [])
            if len(times) < 2 or len(times) != len(values):
                continue
            stages = _build_summary_stages(times, values, stat)
            if not stages:
                continue
            means = [st["mean"] for st in stages]
            sections.append({
                "label": stat.label,
                "unit": getattr(stat, "unit", "") or "",
                "is_current": parse_channel_label(stat.label)[1] == "I",
                "t0": float(times[0]),
                "t1": float(times[-1]),
                "vmin": min(means),
                "vmax": max(means),
                "stages": stages,
            })
        if not sections:
            return None
        width = max(820, self.chart_frame.width())
        return _render_waveform_summary_image(sections, width)

    def _build_system_mode_card(self):
        layout = self.system_mode_card.main_layout
        self._build_system_mode_card_inline(layout)

    def _build_system_mode_card_inline(self, layout):
        self.mode_group = QButtonGroup(self)
        self.mode_4ch = QRadioButton()
        self.mode_8ch = QRadioButton()
        self.mode_4ch.setChecked(True)
        self.mode_group.addButton(self.mode_4ch, 0)
        self.mode_group.addButton(self.mode_8ch, 1)
        self.mode_4ch.hide()
        self.mode_8ch.hide()

    def _build_config_card(self):
        layout = self.config_card.main_layout

        from PySide6.QtGui import QIntValidator

        sp_label = QLabel("Sampling Period (\u00B5s) :")
        sp_label.setObjectName("fieldLabel")
        self.sample_period_edit = SelectAllLineEdit("20")
        self.sample_period_edit.set_wheel_step(1)
        self.sample_period_edit.setFixedWidth(56)
        self.sample_period_edit.setFixedHeight(24)
        self.sample_period_edit.setStyleSheet(dss.SAMPLE_PERIOD_EDIT_STYLE)
        self.sample_period_edit.editingFinished.connect(self._validate_sample_period)

        self.min_period_cb = QCheckBox("Minimum")
        self.min_period_cb.setChecked(True)
        self.min_period_cb.setStyleSheet(dss.MIN_PERIOD_CB_STYLE)
        self.min_period_cb.stateChanged.connect(self._on_min_period_toggled)

        sp_title_row = QHBoxLayout()
        sp_title_row.setContentsMargins(0, 0, 0, 0)
        sp_title_row.addWidget(sp_label)
        sp_title_row.addStretch(1)

        indent_px = 16

        sp_edit_row = QHBoxLayout()
        sp_edit_row.setContentsMargins(0, 0, 0, 0)
        sp_edit_row.setSpacing(8)
        sp_edit_row.addSpacing(indent_px)
        sp_edit_row.addWidget(self.sample_period_edit)
        sp_edit_row.addWidget(self.min_period_cb)
        sp_edit_row.addStretch(1)

        mt_label = QLabel("Monitoring Time :")
        mt_label.setObjectName("fieldLabel")

        time_edit_width = 36

        def _make_time_edit(default_text):
            edit = QLineEdit(default_text)
            edit.setFixedWidth(time_edit_width)
            edit.setFixedHeight(24)
            edit.setAlignment(Qt.AlignCenter)
            edit.setValidator(QIntValidator(0, 999999, self))
            edit.setStyleSheet(dss.TIME_EDIT_STYLE)
            edit.editingFinished.connect(self._validate_monitor_time)
            return edit

        self.monitor_time_d_edit = _make_time_edit("0")
        self.monitor_time_h_edit = _make_time_edit("0")
        self.monitor_time_m_edit = _make_time_edit("0")
        self.monitor_time_s_edit = _make_time_edit("5")

        def _make_unit_label(text):
            lbl = QLabel(text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(dss.TIME_UNIT_LABEL_STYLE)
            lbl.setFixedWidth(time_edit_width)
            return lbl

        def _make_colon():
            lbl = QLabel(":")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(dss.TIME_COLON_STYLE)
            lbl.setFixedWidth(6)
            return lbl

        mt_dd_lbl = _make_unit_label("DD")
        mt_hh_lbl = _make_unit_label("HH")
        mt_mm_lbl = _make_unit_label("MM")
        mt_ss_lbl = _make_unit_label("SS")

        mt_title_row = QHBoxLayout()
        mt_title_row.setContentsMargins(0, 0, 0, 0)
        mt_title_row.addWidget(mt_label)
        mt_title_row.addStretch(1)

        mt_units_row = QHBoxLayout()
        mt_units_row.setContentsMargins(0, 0, 0, 0)
        mt_units_row.setSpacing(2)
        mt_units_row.addSpacing(indent_px)
        mt_units_row.addWidget(mt_dd_lbl)
        mt_units_row.addWidget(_make_colon())
        mt_units_row.addWidget(mt_hh_lbl)
        mt_units_row.addWidget(_make_colon())
        mt_units_row.addWidget(mt_mm_lbl)
        mt_units_row.addWidget(_make_colon())
        mt_units_row.addWidget(mt_ss_lbl)
        mt_units_row.addStretch(1)

        mt_edits_row = QHBoxLayout()
        mt_edits_row.setContentsMargins(0, 0, 0, 0)
        mt_edits_row.setSpacing(2)
        mt_edits_row.addSpacing(indent_px)
        mt_edits_row.addWidget(self.monitor_time_d_edit)
        mt_edits_row.addWidget(_make_colon())
        mt_edits_row.addWidget(self.monitor_time_h_edit)
        mt_edits_row.addWidget(_make_colon())
        mt_edits_row.addWidget(self.monitor_time_m_edit)
        mt_edits_row.addWidget(_make_colon())
        mt_edits_row.addWidget(self.monitor_time_s_edit)
        mt_edits_row.addStretch(1)

        self.monitor_time_edit = self.monitor_time_s_edit

        params_vbox = QVBoxLayout()
        params_vbox.setContentsMargins(0, 0, 0, 0)
        params_vbox.setSpacing(4)
        params_vbox.addLayout(sp_title_row)
        params_vbox.addLayout(sp_edit_row)
        params_vbox.addSpacing(4)
        params_vbox.addLayout(mt_title_row)
        params_vbox.addLayout(mt_units_row)
        params_vbox.addLayout(mt_edits_row)

        layout.addLayout(params_vbox)

    def _build_meas_settings_card(self):
        layout = self.meas_settings_card.main_layout

        self.meas_select_all_cb = QCheckBox("Select All")
        self.meas_minimum_cb = QCheckBox("Minimum")
        self.meas_average_cb = QCheckBox("Average")
        self.meas_average_cb.setChecked(True)
        self.meas_maximum_cb = QCheckBox("Maximum")
        self.meas_maximum_cb.setChecked(True)
        self.meas_peak2peak_cb = QCheckBox("Peak to Peak")
        self.meas_charge_ah_cb = QCheckBox("Charge (Ah) / Energy (Wh)")
        self.meas_charge_c_cb = QCheckBox("Charge (C) / Energy (J)")

        self._meas_metric_cbs = [
            self.meas_minimum_cb,
            self.meas_average_cb,
            self.meas_maximum_cb,
            self.meas_peak2peak_cb,
            self.meas_charge_ah_cb,
            self.meas_charge_c_cb,
        ]

        self.meas_select_all_cb.stateChanged.connect(self._on_meas_select_all)
        for cb in self._meas_metric_cbs:
            cb.stateChanged.connect(self._on_meas_metric_toggled)

        layout.addWidget(self.meas_select_all_cb)
        for cb in self._meas_metric_cbs:
            layout.addWidget(cb)

    def _on_meas_select_all(self, state):
        checked = state == Qt.Checked.value if hasattr(Qt.Checked, 'value') else state == 2
        for cb in self._meas_metric_cbs:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._update_marker_analysis()

    def _on_meas_metric_toggled(self, _state):
        all_checked = all(cb.isChecked() for cb in self._meas_metric_cbs)
        self.meas_select_all_cb.blockSignals(True)
        self.meas_select_all_cb.setChecked(all_checked)
        self.meas_select_all_cb.blockSignals(False)
        self._clear_analysis_card_cache()
        self._update_marker_analysis()

    def _build_label_card(self):
        layout = self.label_card.main_layout

        form_layout = QVBoxLayout()
        form_layout.setSpacing(6)

        ch_row = QHBoxLayout()
        ch_label = QLabel("Channel")
        ch_label.setObjectName("fieldLabel")
        ch_label.setFixedWidth(60)
        self.label_ch_combo = FixedPopupComboBox()
        self.label_ch_combo.setPlaceholderText("CH1")
        ch_row.addWidget(ch_label)
        ch_row.addWidget(self.label_ch_combo, 1)
        form_layout.addLayout(ch_row)

        time_row = QHBoxLayout()
        time_label = QLabel("Time")
        time_label.setObjectName("fieldLabel")
        time_label.setFixedWidth(60)
        self.label_time_edit = QLineEdit()
        self.label_time_edit.setPlaceholderText("e.g. 1.2s, 100ms, 2min")
        time_row.addWidget(time_label)
        time_row.addWidget(self.label_time_edit, 1)
        form_layout.addLayout(time_row)

        desc_row = QHBoxLayout()
        desc_label = QLabel("Des.")
        desc_label.setObjectName("fieldLabel")
        desc_label.setFixedWidth(60)
        self.label_text_edit = QLineEdit()
        self.label_text_edit.setPlaceholderText("Input label name")
        desc_row.addWidget(desc_label)
        desc_row.addWidget(self.label_text_edit, 1)
        form_layout.addLayout(desc_row)

        self.add_label_btn = QPushButton()
        self.add_label_btn.setIcon(_make_svg_icon("plus.svg", "#ffffff", 14))
        self.add_label_btn.setObjectName("addLabelBtn")
        form_layout.addWidget(self.add_label_btn)

        layout.addLayout(form_layout)

        self.labels_list_scroll = QScrollArea()
        self.labels_list_scroll.setWidgetResizable(True)
        self.labels_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.labels_list_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }" + SCROLL_AREA_STYLE
        )
        self.labels_list_container = QWidget()
        self.labels_list_container.setStyleSheet("background: transparent;")
        self.labels_list_layout_inner = QVBoxLayout(self.labels_list_container)
        self.labels_list_layout_inner.setContentsMargins(0, 0, 0, 0)
        self.labels_list_layout_inner.setSpacing(4)

        self.labels_list_label = QLabel("No labels added.")
        self.labels_list_label.setObjectName("hintLabel")
        self.labels_list_layout_inner.addWidget(self.labels_list_label)
        self.labels_list_layout_inner.addStretch()

        self.labels_list_scroll.setWidget(self.labels_list_container)
        layout.addWidget(self.labels_list_scroll, 1)

    def _build_channel_config_card(self):
        self.channel_config_layout = self.channel_config_card.main_layout

        self.channel_config_tabbar = ChannelConfigTabBar()
        self.channel_config_tabbar.setDrawBase(False)
        self.channel_config_tabbar.setExpanding(False)
        self.channel_config_tabbar.setIconSize(QSize(14, 14))
        self.channel_config_tabbar.setStyleSheet(dss.CH_CFG_TABBAR_STYLE)
        self.channel_config_tabbar_placeholder.layout().addWidget(self.channel_config_tabbar, 1)

        self.channel_config_stack = QStackedWidget()
        self.channel_config_stack.setStyleSheet("background: transparent;")
        self.channel_config_layout.addWidget(self.channel_config_stack)

        self.channel_config_tabbar.currentChanged.connect(self._on_channel_config_tab_changed)
        self.channel_config_tabbar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.channel_config_tabbar.customContextMenuRequested.connect(self._on_ch_tabbar_context_menu)

        self._instruments_tab = QWidget()
        self._instruments_tab.setStyleSheet("background: #071127;")
        self._instruments_tab_layout = QVBoxLayout(self._instruments_tab)
        self._instruments_tab_layout.setContentsMargins(0, 2, 0, 0)
        self._instruments_tab_layout.setSpacing(0)
        active_tab_idx = self.channel_config_tabbar.addTab("Active")
        self.channel_config_tabbar.setTabIcon(active_tab_idx, _make_svg_icon("zap.svg", "#8eb0e3", 14))
        self.channel_config_tabbar.setTabData(active_tab_idx, "active")
        self.channel_config_stack.addWidget(self._instruments_tab)
        self._channel_config_last_tab_index = active_tab_idx
        self._add_channel_config_import_tab()

        self.channel_config_inner = QWidget()
        self.channel_config_inner.setStyleSheet("background: #071127;")
        self.channel_config_inner_layout = QHBoxLayout(self.channel_config_inner)
        self.channel_config_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_config_inner_layout.setSpacing(0)
        self._instruments_tab_layout.addWidget(self.channel_config_inner)

        self.unit_a_ch_label = QLabel()
        self.unit_a_ch_label.hide()
        self.unit_b_ch_label = QLabel()
        self.unit_b_ch_label.hide()
        self.ch_row_b_widget = QWidget()
        self.ch_row_b_widget.hide()

        self.no_instrument_label = QLabel("No instruments connected. Open Instrument Connection panel to connect.")
        self.no_instrument_label.setObjectName("hintLabel")
        self.no_instrument_label.setAlignment(Qt.AlignCenter)
        self.no_instrument_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._instruments_tab_layout.addWidget(self.no_instrument_label)
        # 与导入页签一致：末尾 stretch 收口袋，多余纵向空间沉底，不回灌各行撑宽边距
        self._instruments_tab_layout.addStretch()

    def _toggle_channel_config_panel(self):
        self.channel_config_collapsed = not self.channel_config_collapsed
        self.channel_config_card.setVisible(not self.channel_config_collapsed)
        self.channel_config_tabbar_placeholder.setVisible(not self.channel_config_collapsed)
        if self.channel_config_collapsed:
            self.channel_config_toggle_btn.setIcon(self._ch_config_icon_collapsed)
            self.channel_config_toggle_btn.setStyleSheet(dss.CH_CFG_TOGGLE_BTN_COLLAPSED)
        else:
            self.channel_config_toggle_btn.setIcon(self._ch_config_icon_expanded)
            self.channel_config_toggle_btn.setStyleSheet(dss.CH_CFG_TOGGLE_BTN_EXPANDED)

    def set_labels_panel_visible(self, visible):
        """Custom Labels 面板显隐唯一入口（页面卡片头与三种标题栏按钮共用）。"""
        self.label_card.setVisible(visible)
        self.labels_panel_toggled.emit(visible)

    def is_labels_panel_visible(self):
        # 用 isHidden 反向判定（显式显隐标志），父链暂隐（如 suite 切页）时不丢状态
        return not self.label_card.isHidden()

    def _collapse_label_card_panel(self):
        self.set_labels_panel_visible(False)

    def _show_left_panel(self, which):
        """左侧面板互斥单开：which ∈ {"settings", "instrument", None}。"""
        self.settings_panel.setVisible(which == "settings")
        self.instrument_panel.setVisible(which == "instrument")
        self.rail_settings_btn.blockSignals(True)
        self.rail_settings_btn.setChecked(which == "settings")
        self.rail_settings_btn.blockSignals(False)
        self.rail_instrument_btn.blockSignals(True)
        self.rail_instrument_btn.setChecked(which == "instrument")
        self.rail_instrument_btn.blockSignals(False)
        settings_color = self._rail_icon_active if which == "settings" else self._rail_icon_normal
        self.rail_settings_btn.setIcon(_make_svg_icon("settings.svg", settings_color, 16, zoom=1.15))
        instr_color = self._rail_icon_active if which == "instrument" else self._rail_icon_normal
        self.rail_instrument_btn.setIcon(_make_svg_icon("link-connect.svg", instr_color, 16, zoom=1.15))

    def _toggle_settings_panel(self, checked):
        self._show_left_panel("settings" if checked else None)

    def _collapse_settings_panel(self):
        self._show_left_panel(None)

    def _toggle_instrument_panel(self, checked):
        self._show_left_panel("instrument" if checked else None)

    def _collapse_instrument_panel(self):
        self._show_left_panel(None)

    def _on_open_settings_dialog(self):
        """底部控制栏设置齿轮：弹出五标签设置对话框（仪器/网段/DLog/摘要/关于）。"""
        dialog = N6705CSettingsDialog(self)
        dialog.exec()

    def _on_open_help_dialog(self):
        """底部控制栏帮助按钮：弹出帮助手册对话框；点「一键引导」则启动逐步引导。"""
        dialog = DatalogHelpDialog(self)
        if dialog.exec() == DatalogHelpDialog.GUIDE_REQUESTED:
            self._start_guide_tour()

    def _start_guide_tour(self):
        """一键引导：高亮关键控件，逐步讲解 连接仪器→配置→采集→分析→导出 基础流程。"""
        if self._guide_tour is not None:
            return
        show_panel = self._show_left_panel
        prev_panel = ("settings" if not self.settings_panel.isHidden()
                      else "instrument" if not self.instrument_panel.isHidden() else None)
        steps = [
            {
                "target": None,
                "title": "欢迎使用 N6705C Datalog",
                "text": "本引导将带你完成一次完整的数据采集流程：\n连接仪器 → 配置采集参数 → 勾选通道 → 开始记录 → 分析波形 → 导出数据。\n\n点击「下一步」继续，随时可按 Esc 或「跳过引导」退出。",
            },
            {
                "target": self.rail_instrument_btn,
                "title": "第 1 步：打开仪器连接面板",
                "text": "点击左侧边栏的链接图标，打开 Instrument Connection 面板。\n（引导已为你自动展开）",
                "on_enter": lambda: show_panel("instrument"),
            },
            {
                "target": self.instrument_panel,
                "title": "第 2 步：搜索并连接仪器",
                "text": "点击左上角搜索按钮扫描局域网内的 N6705C；在设备卡片上点击 Connect 完成连接，设备自动分配到插槽 A / B / C / D。\n\n搜索不到时，可通过右上角「⋯」→ Add Instrument Manually 手动添加（TCP/IP 或 USB）。",
                "on_enter": lambda: show_panel("instrument"),
            },
            {
                "target": self.config_card,
                "title": "第 3 步：配置采集参数",
                "text": "打开 Settings 面板，在 DATALOG CONFIG 中设置：\n· Sampling Period (μs)：采样周期，默认 20；勾选 Minimum 自动使用最小周期\n· Monitoring Time (s)：监控时长，到时自动停止采集",
                "on_enter": lambda: show_panel("settings"),
            },
            {
                "target": self.meas_settings_card,
                "title": "第 4 步：选择测量项",
                "text": "在 Measurement Settings 中勾选需要统计的指标（Average / Maximum / Minimum / Peak to Peak / Charge / Energy），采集完成后显示在波形下方的测量表中。",
                "on_enter": lambda: show_panel("settings"),
            },
            {
                "target": self.channel_config_outer,
                "title": "第 5 步：勾选采集通道",
                "text": "在 Channel Config 的 Active 页签中，为每个通道勾选需要采集的类型：I（电流）/ V（电压）/ P（功率）。\n波形显示超出范围时可调整各通道的 Scale / Offset。",
                "on_enter": lambda: show_panel(None),
            },
            {
                "target": self.start_btn,
                "title": "第 6 步：开始采集",
                "text": "点击 Start Recording 开始记录，进度条显示采集进度；到达监控时长后自动停止，波形立即绘制到图表中。",
            },
            {
                "target": self.chart_frame,
                "title": "第 7 步：分析波形",
                "text": "· 点击通道区域选中，拖拽调整偏移、滚轮缩放比例\n· 悬停查看各通道在当前时间点的数值\n· 工具栏 Marker A / B 放置标记线，空白处右键可移动 Marker\n· Box Zoom 框选放大，Fit View 一键全览",
            },
            {
                "target": self.measurement_card,
                "title": "第 8 步：查看测量结果",
                "text": "测量表实时显示各通道的统计值（第 4 步勾选的指标）；放置 Marker A / B 后，统计范围自动限定在标记区间内。",
            },
            {
                "target": self.export_btn,
                "title": "第 9 步：导出数据",
                "text": "点击 Export Datalog 将数据导出为 CSV 或 DLOG 文件；旁边的 Import 按钮可导入外部数据文件进行对比分析。",
            },
            {
                "target": None,
                "title": "引导完成",
                "text": "你已经掌握了 Datalog 的基础流程！\n\n· 底部齿轮按钮：打开设置对话框（默认仪器 / 网段 / 自动保存 / 摘要算法）\n· 底部问号按钮：随时重新打开帮助手册与一键引导",
            },
        ]
        tour = GuideTourOverlay(self.window(), steps)
        self._guide_tour = tour
        tour.finished.connect(lambda: self._show_left_panel(prev_panel))
        tour.destroyed.connect(lambda: setattr(self, "_guide_tour", None))

    def _window_geometry_path(self):
        from resource_path import get_user_data_dir
        return os.path.join(get_user_data_dir("n6705c"), "window_geometry.json")

    def _screen_available_geometry_for(self, point=None):
        app = QApplication.instance()
        screen = None
        if app is not None and point is not None:
            screen = app.screenAt(point)
        if screen is None and app is not None:
            screen = app.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
        return QRect(0, 0, 1280, 720)

    def _default_window_geometry(self):
        available = self._screen_available_geometry_for()
        target_w, target_h = self._WINDOW_DEFAULT_SIZE
        margin = self._WINDOW_MARGIN
        width = min(target_w, max(640, available.width() - margin))
        height = min(target_h, max(480, available.height() - margin))
        x = available.x() + max(0, (available.width() - width) // 2)
        y = available.y() + max(0, (available.height() - height) // 2)
        return QRect(x, y, width, height)

    def _clamped_window_geometry(self, window_cfg):
        saved = QRect(
            int(window_cfg.get("x", 0)),
            int(window_cfg.get("y", 0)),
            int(window_cfg.get("width", 0)),
            int(window_cfg.get("height", 0)),
        )
        if saved.width() <= 0 or saved.height() <= 0:
            return self._default_window_geometry()

        available = self._screen_available_geometry_for(saved.center())
        width = min(saved.width(), available.width())
        height = min(saved.height(), available.height())

        x = min(max(saved.x(), available.x()), available.right() - width + 1)
        y = min(max(saved.y(), available.y()), available.bottom() - height + 1)
        return QRect(x, y, width, height)

    def _load_window_geometry(self):
        path = self._window_geometry_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            logger.debug("Load window_geometry.json failed", exc_info=True)
            return None

    def _collect_window_state(self):
        if not self.isWindow() or not self.isVisible() or self.isMinimized():
            return {}
        geom = self.normalGeometry() if self.isMaximized() else self.geometry()
        if geom.width() <= 0 or geom.height() <= 0:
            return {}
        return {
            "x": int(geom.x()),
            "y": int(geom.y()),
            "width": int(geom.width()),
            "height": int(geom.height()),
            "maximized": bool(self.isMaximized()),
        }

    def _save_window_geometry(self):
        state = self._collect_window_state()
        if not state:
            return
        path = self._window_geometry_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            logger.warning("Save window_geometry.json failed", exc_info=True)

    def apply_window_geometry(self):
        """独立窗口态下应用记忆的位置/大小；首次打开则用 800x600 居中。"""
        window_cfg = self._load_window_geometry()
        if isinstance(window_cfg, dict):
            self.setGeometry(self._clamped_window_geometry(window_cfg))
            self._restore_maximized = bool(window_cfg.get("maximized", False))
            return
        self.setGeometry(self._default_window_geometry())
        self._restore_maximized = False
