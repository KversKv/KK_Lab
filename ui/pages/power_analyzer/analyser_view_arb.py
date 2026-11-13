#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QPushButton, QStackedWidget, QListWidget, QListWidgetItem,
    QMessageBox, QInputDialog, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread

from log_config import get_logger
from resource_path import get_user_data_dir
from ui.widgets.dark_combobox import DarkComboBox
from ui.pages.power_analyzer.widgets import (
    ChannelTabBar, SlideToggle, SelectAllLineEdit, collapsible_header_style,
    CONTENT_BG, PANEL_BG, PANEL_BORDER, CARD_BG, CARD_BORDER,
    CONTAINER_RADIUS, WIDGET_RADIUS, MUTED_TEXT,
    DISABLED_TEXT, DISABLED_BTN_BG, DISABLED_BTN_BORDER,
    INACTIVE_TAB_BG, INACTIVE_TAB_HOVER_BG,
)

logger = get_logger(__name__)

# (shape_key, 显示名) —— 顺序即下拉与 QStackedWidget 页序
_ARB_SHAPES = [
    ("sine", "Sine"),
    ("step", "Step"),
    ("staircase", "Staircase"),
    ("pulse_v", "Pulse (V)"),
    ("pulse_i", "Pulse (I)"),
]

# shape_key -> [(label, field_key, default_text, wheel_step), ...]
# 时间字段按时间流排序（start -> top -> end），field_key 与驱动参数对应
_ARB_FIELDS = {
    "sine": [
        ("DC Offset (V):", "offset_v", "3.3", 0.1),
        ("Amplitude (Vrms):", "ampl_vrms", "0.1", 0.01),
        ("Frequency (Hz):", "freq_hz", "1000", 1),
    ],
    "step": [
        ("Start Voltage (V):", "v0", "3.3", 0.1),
        ("End Voltage (V):", "v1", "3.8", 0.1),
        ("Start Hold (s):", "t0", "0.01", 0.001),
        ("End Hold (s):", "t1", "0.01", 0.001),
    ],
    "staircase": [
        ("Start Voltage (V):", "v0", "3.0", 0.1),
        ("End Voltage (V):", "v1", "4.0", 0.1),
        ("Start Hold (s):", "t0", "0.005", 0.001),
        ("Stair Time (s):", "t1", "0.05", 0.001),
        ("End Hold (s):", "t2", "0.005", 0.001),
        ("Steps:", "steps", "10", 1),
    ],
    "pulse_v": [
        ("Base Voltage (V):", "v0", "3.3", 0.1),
        ("Top Voltage (V):", "v1", "3.8", 0.1),
        ("Start Hold (s):", "t0", "0.0005", 0.0001),
        ("Top Hold (s):", "t2", "0.0005", 0.0001),
        ("End Hold (s):", "t1", "0", 0.0001),
        ("Frequency (Hz):", "freq_hz", "100", 1),
    ],
    "pulse_i": [
        ("Base Current (A):", "i0", "0", 0.01),
        ("Top Current (A):", "i1", "-0.5", 0.01),
        ("Start Hold (s):", "t0", "0.0005", 0.0001),
        ("Top Hold (s):", "t2", "0.0005", 0.0001),
        ("End Hold (s):", "t1", "0", 0.0001),
        ("Frequency (Hz):", "freq_hz", "100", 1),
    ],
}

_ARB_INPUT_STYLE = f"""
    QLineEdit {{
        background-color: #111d36; color: #dbe6ff;
        border: 1px solid #1e3050; border-radius: {WIDGET_RADIUS};
        padding: 4px 8px; font-size: 12px; font-weight: 600;
    }}
    QLineEdit:focus {{ border: 1px solid #3a5a90; color: #ffffff; }}
    QLineEdit:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
"""

_ARB_PRESETS_FILENAME = "arb_presets.json"


def _arb_presets_path() -> str:
    return os.path.join(get_user_data_dir("n6705c"), _ARB_PRESETS_FILENAME)


class _ArbRunWorker(QObject):
    """Arb 下发 / 停止 worker（QThread 内执行，UI 不阻塞）。"""

    finished = Signal(str, bool, str)  # dev_label, success, message

    def __init__(self, instance, dev_label, channel, mode,
                 shape_key=None, values=None, continuous=False, io_lock=None):
        super().__init__()
        self._instance = instance
        self._dev_label = dev_label
        self._channel = channel
        self._mode = mode  # "apply" | "stop"
        self._shape_key = shape_key
        self._values = values or {}
        self._continuous = continuous
        self._io_lock = io_lock

    def run(self):
        try:
            if self._io_lock is not None:
                self._io_lock.acquire()
            try:
                if self._mode == "apply":
                    self._apply()
                    message = f"{self._dev_label}-CH{self._channel} arb started"
                else:
                    self._instance.arb_stop(self._channel)
                    message = f"{self._dev_label}-CH{self._channel} arb stopped"
            finally:
                if self._io_lock is not None:
                    self._io_lock.release()
            logger.info("Arb %s ok: %s", self._mode, message)
            self.finished.emit(self._dev_label, True, message)
        except Exception as exc:
            logger.error("Arb %s failed: %s", self._mode, exc, exc_info=True)
            self.finished.emit(self._dev_label, False, str(exc))

    def _apply(self):
        inst = self._instance
        ch = self._channel
        v = self._values
        if self._shape_key == "sine":
            inst.set_arb_sine(ch, v["offset_v"], v["ampl_vrms"], v["freq_hz"])
        elif self._shape_key == "step":
            inst.set_arb_step(ch, v["v0"], v["v1"], v["t0"], v["t1"])
        elif self._shape_key == "staircase":
            inst.set_arb_staircase(
                ch, v["v0"], v["v1"], v["t0"], v["t1"], v["t2"], int(v["steps"])
            )
        elif self._shape_key == "pulse_v":
            inst.set_arb_pulse(ch, v["v0"], v["v1"], v["t0"], v["t1"], v["t2"], v["freq_hz"])
        elif self._shape_key == "pulse_i":
            inst.set_arb_current_pulse(
                ch, v["i0"], v["i1"], v["t0"], v["t1"], v["t2"], v["freq_hz"]
            )
        else:
            raise ValueError(f"Unknown arb shape: {self._shape_key}")
        # Continuous 须在形状配置完成后、触发前设置（驱动契约）
        inst.set_arb_continuous(ch, self._continuous)
        inst.arb_on(ch)


class ArbViewMixin:
    """Arb Set 面板：左侧通道 Arb 配置（独立 tab），右侧常用预设（JSON 持久化）。"""

    # ------------------------------------------------------------------ panel
    def _create_arb_panel(self):
        self.arb_collapsed = True
        self._arb_current_device = "A"
        self._arb_current_channel = 1
        self._arb_param_store = {}
        self._arb_loading = False
        self._arb_last_shape = "sine"
        self._arb_threads = {}
        self._arb_workers = {}
        self._arb_presets = []

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.arb_toggle_btn = QPushButton("\u25b6  Arb Set")
        self.arb_toggle_btn.setStyleSheet(collapsible_header_style(True))
        self.arb_toggle_btn.clicked.connect(self._toggle_arb_panel)
        outer_layout.addWidget(self.arb_toggle_btn)

        self.arb_content = QFrame()
        self.arb_content.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {PANEL_BORDER};
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
            }}
        """)
        self.arb_content.setVisible(False)

        content_layout = QHBoxLayout(self.arb_content)
        content_layout.setContentsMargins(16, 10, 16, 14)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._create_arb_channel_zone(), 3)
        content_layout.addWidget(self._create_arb_preset_zone(), 2)

        outer_layout.addWidget(self.arb_content)

        self._build_arb_tab_buttons()
        self._arb_load_channel_params()
        self._arb_load_presets()
        self._arb_refresh_action_state()
        return outer

    def _toggle_arb_panel(self):
        self.arb_collapsed = not self.arb_collapsed
        self.arb_content.setVisible(not self.arb_collapsed)
        self.arb_toggle_btn.setText(
            "\u25b6  Arb Set" if self.arb_collapsed else "\u25bc  Arb Set"
        )
        self.arb_toggle_btn.setStyleSheet(collapsible_header_style(self.arb_collapsed))

    # ----------------------------------------------------------- channel zone
    def _create_arb_channel_zone(self):
        zone = QWidget()
        zone.setStyleSheet("QWidget { background: transparent; border: none; }")
        zone_layout = QVBoxLayout(zone)
        zone_layout.setContentsMargins(0, 0, 0, 0)
        zone_layout.setSpacing(0)

        self._arb_tab_bar = ChannelTabBar()
        self._arb_tabs_layout = self._arb_tab_bar.layout()
        self.arb_tab_buttons = []
        self._arb_tab_separator = None
        zone_layout.addWidget(self._arb_tab_bar)

        self.arb_body = QFrame()
        self.arb_body.setObjectName("ArbContentFrame")
        zone_layout.addWidget(self.arb_body)

        body_layout = QVBoxLayout(self.arb_body)
        body_margins = (12, 12, 12, 12)
        body_layout.setContentsMargins(*body_margins)
        body_layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.arb_ch_title = QLabel("Channel 1")
        self.arb_ch_title.setStyleSheet(
            "QLabel { font-size: 14px; font-weight: 800; color: #ffffff; border: none; background: transparent; }"
        )
        title_row.addWidget(self.arb_ch_title)
        title_row.addStretch()
        cont_label = QLabel("Continuous")
        cont_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        title_row.addWidget(cont_label)
        self.arb_continuous_toggle = SlideToggle()
        self.arb_continuous_toggle.clicked.connect(self._arb_on_continuous_toggled)
        title_row.addWidget(self.arb_continuous_toggle)
        body_layout.addLayout(title_row)

        shape_row = QHBoxLayout()
        shape_row.setSpacing(8)
        shape_label = QLabel("Waveform:")
        shape_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        shape_row.addWidget(shape_label)
        self.arb_shape_combo = DarkComboBox()
        for _key, label in _ARB_SHAPES:
            self.arb_shape_combo.addItem(label)
        self.arb_shape_combo.currentIndexChanged.connect(self._arb_on_shape_changed)
        shape_row.addWidget(self.arb_shape_combo, 1)
        body_layout.addLayout(shape_row)

        self.arb_params_stack = QStackedWidget()
        self.arb_param_inputs = {}  # shape_key -> {field_key: SelectAllLineEdit}
        for shape_key, _label in _ARB_SHAPES:
            page, inputs = self._create_arb_params_page(shape_key)
            self.arb_params_stack.addWidget(page)
            self.arb_param_inputs[shape_key] = inputs
        body_layout.addWidget(self.arb_params_stack)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.arb_apply_btn = QPushButton("APPLY && RUN")
        self.arb_apply_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.arb_apply_btn.clicked.connect(self._arb_apply)
        self.arb_stop_btn = QPushButton("\u25a0  STOP")
        self.arb_stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.arb_stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a0a1c; color: #ff4fa3;
                border: 1px solid #d63384; border-radius: {WIDGET_RADIUS};
                font-weight: 700; font-size: 12px; min-height: 32px;
            }}
            QPushButton:hover {{ background-color: #3a1028; }}
            QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """)
        self.arb_stop_btn.clicked.connect(self._arb_stop)
        btn_row.addWidget(self.arb_apply_btn, 1)
        btn_row.addWidget(self.arb_stop_btn, 1)
        body_layout.addLayout(btn_row)

        self._arb_apply_channel_theme()
        return zone

    def _create_arb_params_page(self, shape_key):
        page = QFrame()
        page.setStyleSheet(
            f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}"
        )
        grid = QGridLayout(page)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        inputs = {}
        fields = _ARB_FIELDS[shape_key]
        for idx, (label_text, field_key, default_text, wheel_step) in enumerate(fields):
            row, col = divmod(idx, 2)
            label = QLabel(label_text)
            label.setStyleSheet(
                f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
            )
            edit = SelectAllLineEdit(default_text)
            edit.set_wheel_step(wheel_step)
            edit.setFixedWidth(100)
            edit.setAlignment(Qt.AlignCenter)
            edit.setStyleSheet(_ARB_INPUT_STYLE)
            grid.addWidget(label, row, col * 2)
            grid.addWidget(edit, row, col * 2 + 1)
            inputs[field_key] = edit
        grid.setColumnStretch(4, 1)
        return page, inputs

    # ------------------------------------------------------------ preset zone
    def _create_arb_preset_zone(self):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}"
        )
        card.setMinimumWidth(220)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title = QLabel("QUICK PRESETS")
        title.setStyleSheet(
            f"QLabel {{ color: {MUTED_TEXT}; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; border: none; }}"
        )
        layout.addWidget(title)

        self.arb_preset_list = QListWidget()
        self.arb_preset_list.setStyleSheet(f"""
            QListWidget {{
                background-color: #091426; color: #dbe6ff;
                border: 1px solid {CARD_BORDER}; border-radius: {WIDGET_RADIUS};
                font-size: 12px; outline: 0;
            }}
            QListWidget::item {{ padding: 5px 8px; }}
            QListWidget::item:selected {{ background-color: #1a2a50; color: #ffffff; }}
            QListWidget::item:hover {{ background-color: #12213f; }}
        """)
        self.arb_preset_list.itemClicked.connect(self._arb_on_preset_clicked)
        layout.addWidget(self.arb_preset_list, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.arb_preset_save_btn = QPushButton("Save")
        self.arb_preset_delete_btn = QPushButton("Delete")
        for btn in (self.arb_preset_save_btn, self.arb_preset_delete_btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #0b1730; color: #dbe6ff;
                    border: 1px solid #23417a; border-radius: {WIDGET_RADIUS};
                    font-size: 11px; padding: 4px 10px; min-height: 26px;
                }}
                QPushButton:hover {{ background-color: #10203e; }}
                QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
            """)
        self.arb_preset_save_btn.clicked.connect(self._arb_on_save_preset)
        self.arb_preset_delete_btn.clicked.connect(self._arb_on_delete_preset)
        btn_row.addWidget(self.arb_preset_save_btn, 1)
        btn_row.addWidget(self.arb_preset_delete_btn, 1)
        layout.addLayout(btn_row)
        return card

    # -------------------------------------------------------------- tab logic
    def _build_arb_tab_buttons(self):
        if not hasattr(self, "_arb_tabs_layout"):
            return
        for btn in self.arb_tab_buttons:
            self._arb_tabs_layout.removeWidget(btn)
            btn.deleteLater()
        self.arb_tab_buttons.clear()

        if self._arb_tab_separator is not None:
            self._arb_tabs_layout.removeWidget(self._arb_tab_separator)
            self._arb_tab_separator.deleteLater()
            self._arb_tab_separator = None

        while self._arb_tabs_layout.count():
            item = self._arb_tabs_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._arb_tabs_layout.setContentsMargins(0, 4, 0, 0)
        self._arb_tabs_layout.setSpacing(2)

        # 当前通道不可用时回退到第一个可用通道（未连接保持默认）
        connected = self._connected_device_labels()
        if connected and (
            self._arb_current_device not in connected
            or not self._is_channel_supported(self._arb_current_device, self._arb_current_channel)
        ):
            selected = next(
                (
                    (label, ch)
                    for label in connected
                    for ch in self._supported_channels_for_device(label)
                ),
                None,
            )
            if selected is not None:
                self._arb_current_device, self._arb_current_channel = selected
            elif self._arb_current_device not in connected:
                self._arb_current_device = connected[0]

        dual = self._is_dual_mode()
        if dual:
            for dev_label in ["A", "B"]:
                for ch in self._channels_for_device(dev_label):
                    self._arb_tabs_layout.addWidget(
                        self._make_arb_tab_button(f"\u25cf {dev_label}-CH{ch}", dev_label, ch)
                    )
                if dev_label == "A":
                    sep = QFrame()
                    sep.setFixedWidth(2)
                    sep.setFixedHeight(24)
                    sep.setStyleSheet("QFrame { background: #1b2847; border: none; }")
                    self._arb_tab_separator = sep
                    self._arb_tabs_layout.addWidget(sep)
        else:
            single_label = self._get_single_device_label()
            for ch in self._channels_for_device(single_label):
                self._arb_tabs_layout.addWidget(
                    self._make_arb_tab_button(f"\u25cf CH{ch}", single_label, ch)
                )

        self._arb_tabs_layout.addStretch()
        self._arb_load_channel_params()
        self._arb_apply_channel_theme()

    def _make_arb_tab_button(self, text, dev_label, ch):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setProperty("device_label", dev_label)
        btn.setProperty("channel", ch)
        btn.setMinimumSize(80, 32)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setEnabled(self._is_channel_supported(dev_label, ch))
        btn.setToolTip(self._channel_module_tooltip(dev_label, ch))
        btn.clicked.connect(
            lambda checked=False, d=dev_label, c=ch: self._arb_switch_channel(d, c)
        )
        self.arb_tab_buttons.append(btn)
        return btn

    def _arb_switch_channel(self, dev_label, ch):
        if not self._is_channel_supported(dev_label, ch):
            return
        if dev_label == self._arb_current_device and ch == self._arb_current_channel:
            return
        self._arb_store_current_params()
        self._arb_current_device = dev_label
        self._arb_current_channel = ch
        self._arb_load_channel_params()
        self._arb_apply_channel_theme()
        self._arb_refresh_action_state()

    def _arb_tab_style(self, dev_label, ch, checked=False):
        theme = self._channel_theme(dev_label, ch)
        active_border = theme["accent_border"]
        font_size = "11px" if self._is_dual_mode() else "12px"
        radius = (
            f"border-top-left-radius: {WIDGET_RADIUS}; border-top-right-radius: {WIDGET_RADIUS};"
            " border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;"
        )
        disabled_part = f"""
            QPushButton:disabled {{
                background-color: #0a1224; color: #3a4a6a;
                border: 1px solid #151f36;
                border-bottom: 1px solid #151f36;
                {radius}
                padding: 7px 10px; font-size: {font_size}; font-weight: 700;
            }}
        """
        if checked:
            return f"""
            QPushButton {{
                background-color: {CONTENT_BG}; color: {theme['accent']};
                border: 1px solid {active_border};
                border-bottom: 1px solid {CONTENT_BG};
                {radius}
                padding: 7px 10px; font-size: {font_size}; font-weight: 700;
                margin-bottom: 0px;
            }}
            {disabled_part}
            """
        return f"""
        QPushButton {{
            background-color: {INACTIVE_TAB_BG}; color: {theme['text_dim']};
            border: 1px solid #1b2847;
            border-bottom: 1px solid {active_border};
            {radius}
            padding: 7px 10px; font-size: {font_size}; font-weight: 700;
        }}
        QPushButton:hover {{
            background-color: {INACTIVE_TAB_HOVER_BG}; color: #ffffff;
            border: 1px solid {active_border};
            border-bottom: 1px solid {active_border};
        }}
        {disabled_part}
        """

    def _refresh_arb_tab_styles(self):
        active_btn = None
        for btn in getattr(self, "arb_tab_buttons", []):
            dev_label = btn.property("device_label")
            ch = int(btn.property("channel"))
            is_active = (
                dev_label == self._arb_current_device
                and ch == self._arb_current_channel
                and self._is_channel_supported(dev_label, ch)
            )
            btn.setStyleSheet(self._arb_tab_style(dev_label, ch, is_active))
            btn.setChecked(is_active)
            if is_active:
                active_btn = btn
        QTimer.singleShot(0, lambda: self._update_arb_tab_bar_active_rect(active_btn))

    def _update_arb_tab_bar_active_rect(self, active_btn):
        if not hasattr(self, "_arb_tab_bar"):
            return
        if active_btn:
            self._arb_tab_bar.set_active_tab_rect(active_btn.geometry())
        else:
            self._arb_tab_bar.set_active_tab_rect(None)

    def _arb_apply_channel_theme(self):
        if not hasattr(self, "arb_body"):
            return
        theme = self._channel_theme(self._arb_current_device, self._arb_current_channel)
        accent_border = theme["accent_border"]

        if self._is_dual_mode():
            self.arb_ch_title.setText(
                f"{self._arb_current_device} - Channel {self._arb_current_channel}"
            )
        else:
            self.arb_ch_title.setText(f"Channel {self._arb_current_channel}")

        self.arb_body.setStyleSheet(f"""
            QFrame#ArbContentFrame {{
                background-color: {CONTENT_BG};
                border: 1px solid {accent_border};
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)
        self._arb_tab_bar.set_border_color(accent_border)
        self.arb_continuous_toggle.setAccentColor(theme["accent"])
        self.arb_apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0c1a38; color: {theme['accent']};
                border: 1px solid {theme['accent']}; border-radius: {WIDGET_RADIUS};
                font-size: 12px; min-height: 32px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #12213f; color: {theme['accent_hover']}; border: 1px solid {theme['accent_hover']}; }}
            QPushButton:disabled {{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """)
        self._refresh_arb_tab_styles()

    # --------------------------------------------------------- params memory
    def _arb_current_shape_key(self):
        idx = self.arb_shape_combo.currentIndex()
        return _ARB_SHAPES[idx][0]

    def _arb_on_shape_changed(self, index):
        new_shape = _ARB_SHAPES[index][0]
        old_shape = self._arb_last_shape
        self._arb_last_shape = new_shape
        if old_shape != new_shape:
            # 滚轮调值走 setText（仅 textChanged），切走前全量保存旧页
            self._arb_store_shape_params(old_shape)
        self.arb_params_stack.setCurrentIndex(index)
        self._arb_load_shape_params(new_shape)
        self._arb_store_current_params()

    def _arb_load_shape_params(self, shape):
        """从当前通道 store 恢复指定波形页的已存值（无记录则保留默认）。"""
        key = (self._arb_current_device, self._arb_current_channel)
        saved = self._arb_param_store.get(key, {}).get("params", {}).get(shape, {})
        if not saved:
            return
        prev = self._arb_loading
        self._arb_loading = True
        try:
            for field_key, edit in self.arb_param_inputs[shape].items():
                if field_key in saved:
                    edit.setText(str(saved[field_key]))
        finally:
            self._arb_loading = prev

    def _arb_on_continuous_toggled(self, _checked):
        self._arb_store_current_params()

    def _arb_store_shape_params(self, shape):
        if self._arb_loading or not hasattr(self, "arb_shape_combo"):
            return
        params = {
            field_key: edit.text()
            for field_key, edit in self.arb_param_inputs[shape].items()
        }
        key = (self._arb_current_device, self._arb_current_channel)
        entry = self._arb_param_store.setdefault(key, {"params": {}})
        entry["shape"] = self._arb_current_shape_key()
        entry["continuous"] = self.arb_continuous_toggle.isChecked()
        entry["params"][shape] = params

    def _arb_store_current_params(self):
        self._arb_store_shape_params(self._arb_current_shape_key())

    def _arb_load_channel_params(self):
        if not hasattr(self, "arb_shape_combo"):
            return
        self._arb_loading = True
        try:
            key = (self._arb_current_device, self._arb_current_channel)
            entry = self._arb_param_store.get(key, {})
            shape = entry.get("shape", "sine")
            shape_keys = [k for k, _label in _ARB_SHAPES]
            if shape not in shape_keys:
                shape = "sine"
            self.arb_shape_combo.setCurrentIndex(shape_keys.index(shape))
            self.arb_params_stack.setCurrentIndex(shape_keys.index(shape))
            self.arb_continuous_toggle.setChecked(bool(entry.get("continuous", False)))
            saved = entry.get("params", {}).get(shape, {})
            for field_key, edit in self.arb_param_inputs[shape].items():
                if field_key in saved:
                    edit.setText(str(saved[field_key]))
            self._arb_last_shape = shape
        finally:
            self._arb_loading = False

    def _arb_collect_values(self):
        """解析当前波形参数为数值；非法输入抛 ValueError。"""
        shape = self._arb_current_shape_key()
        values = {}
        for label_text, field_key, _default, _step in _ARB_FIELDS[shape]:
            text = self.arb_param_inputs[shape][field_key].text().strip()
            try:
                values[field_key] = float(text)
            except ValueError as exc:
                raise ValueError(f"{label_text.rstrip(':')} invalid: '{text}'") from exc
        if shape == "staircase":
            values["steps"] = int(values["steps"])
        return values

    # ------------------------------------------------------------ apply/stop
    def _arb_io_lock(self, dev_label):
        if not self._instrument_manager:
            return None
        getter = getattr(self._instrument_manager, "io_lock", None)
        if not callable(getter):
            return None
        return getter(f"n6705c:{dev_label}")

    def _arb_apply(self):
        dev_label = self._arb_current_device
        ch = self._arb_current_channel
        dev = self.devices.get(dev_label, {})
        instance = dev.get("n6705c")
        if not dev.get("is_connected") or instance is None:
            return
        if not self._is_channel_supported(dev_label, ch) or dev_label in self._arb_threads:
            return
        try:
            values = self._arb_collect_values()
        except ValueError as exc:
            QMessageBox.warning(self, "Arb Set", str(exc))
            return
        self._arb_store_current_params()
        self._arb_start_worker(dev_label, instance, ch, "apply",
                               shape_key=self._arb_current_shape_key(),
                               values=values,
                               continuous=self.arb_continuous_toggle.isChecked())

    def _arb_stop(self):
        dev_label = self._arb_current_device
        ch = self._arb_current_channel
        dev = self.devices.get(dev_label, {})
        instance = dev.get("n6705c")
        if not dev.get("is_connected") or instance is None or dev_label in self._arb_threads:
            return
        self._arb_start_worker(dev_label, instance, ch, "stop")

    def _arb_start_worker(self, dev_label, instance, ch, mode, **kwargs):
        worker = _ArbRunWorker(
            instance, dev_label, ch, mode, io_lock=self._arb_io_lock(dev_label), **kwargs
        )
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._arb_on_run_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            lambda lb=dev_label: self._arb_on_thread_cleaned(lb)
        )
        self._arb_threads[dev_label] = thread
        self._arb_workers[dev_label] = worker
        self._arb_refresh_action_state()
        thread.start()

    def _arb_on_thread_cleaned(self, dev_label):
        self._arb_workers.pop(dev_label, None)
        self._arb_threads.pop(dev_label, None)
        self._arb_refresh_action_state()

    def _arb_on_run_finished(self, dev_label, success, message):
        if not success:
            QMessageBox.warning(self, "Arb Set", message)

    def _arb_refresh_action_state(self):
        if not hasattr(self, "arb_apply_btn"):
            return
        dev = self.devices.get(self._arb_current_device, {})
        connected = bool(dev.get("is_connected"))
        supported = self._is_channel_supported(self._arb_current_device, self._arb_current_channel)
        running = self._arb_current_device in self._arb_threads
        self.arb_apply_btn.setEnabled(connected and supported and not running)
        self.arb_stop_btn.setEnabled(connected and supported and not running)

    # ---------------------------------------------------------------- presets
    def _arb_load_presets(self):
        path = _arb_presets_path()
        presets = []
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f) or {}
                if isinstance(raw.get("presets"), list):
                    presets = [p for p in raw["presets"] if isinstance(p, dict) and p.get("name")]
            except (OSError, json.JSONDecodeError):
                logger.error("读取 arb_presets.json 失败: %s", path, exc_info=True)
        self._arb_presets = presets
        self._arb_refresh_preset_list()

    def _arb_save_presets(self):
        path = _arb_presets_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"presets": self._arb_presets}, f, ensure_ascii=False, indent=2)
        except OSError:
            logger.error("写入 arb_presets.json 失败: %s", path, exc_info=True)

    def _arb_refresh_preset_list(self):
        if not hasattr(self, "arb_preset_list"):
            return
        self.arb_preset_list.clear()
        for preset in self._arb_presets:
            item = QListWidgetItem(str(preset.get("name", "")))
            item.setToolTip(self._arb_preset_summary(preset))
            self.arb_preset_list.addItem(item)

    def _arb_preset_summary(self, preset):
        shape = preset.get("shape", "")
        shape_label = dict(_ARB_SHAPES).get(shape, shape)
        params = preset.get("params", {})
        parts = [f"{k}={v}" for k, v in params.items()]
        cont = "continuous" if preset.get("continuous") else "single"
        return f"{shape_label} | {cont} | {', '.join(parts)}"

    def _arb_on_save_preset(self):
        try:
            values = self._arb_collect_values()
        except ValueError as exc:
            QMessageBox.warning(self, "Arb Set", str(exc))
            return
        name, ok = QInputDialog.getText(self, "Save Arb Preset", "Preset name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        preset = {
            "name": name,
            "shape": self._arb_current_shape_key(),
            "continuous": self.arb_continuous_toggle.isChecked(),
            "params": values,
        }
        self._arb_presets = [p for p in self._arb_presets if p.get("name") != name]
        self._arb_presets.append(preset)
        self._arb_save_presets()
        self._arb_refresh_preset_list()
        logger.info("Arb preset saved: %s", name)

    def _arb_on_delete_preset(self):
        row = self.arb_preset_list.currentRow()
        if row < 0 or row >= len(self._arb_presets):
            return
        name = self._arb_presets[row].get("name", "")
        del self._arb_presets[row]
        self._arb_save_presets()
        self._arb_refresh_preset_list()
        logger.info("Arb preset deleted: %s", name)

    def _arb_on_preset_clicked(self, item):
        row = self.arb_preset_list.row(item)
        if row < 0 or row >= len(self._arb_presets):
            return
        preset = self._arb_presets[row]
        shape = preset.get("shape", "sine")
        shape_keys = [k for k, _label in _ARB_SHAPES]
        if shape not in shape_keys:
            return
        self._arb_loading = True
        try:
            self.arb_shape_combo.setCurrentIndex(shape_keys.index(shape))
            self.arb_params_stack.setCurrentIndex(shape_keys.index(shape))
            self.arb_continuous_toggle.setChecked(bool(preset.get("continuous", False)))
            params = preset.get("params", {})
            for field_key, edit in self.arb_param_inputs[shape].items():
                if field_key in params:
                    edit.setText(str(params[field_key]))
        finally:
            self._arb_loading = False
        self._arb_store_current_params()
