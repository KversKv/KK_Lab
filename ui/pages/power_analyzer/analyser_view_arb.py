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
from resource_path import get_resource_base, get_user_data_dir
from ui.utils.icon_utils import tinted_svg_icon, tinted_svg_pixmap
from ui.widgets.dark_combobox import DarkComboBox
from ui.pages.power_analyzer.widgets import (
    ChannelTabBar, SlideToggle, SelectAllLineEdit, collapsible_header_style,
    is_it2705_instrument,
    CONTENT_BG, PANEL_BG, PANEL_BORDER, CARD_BG, CARD_BORDER,
    CONTAINER_RADIUS, WIDGET_RADIUS, MUTED_TEXT,
    DISABLED_TEXT, DISABLED_BTN_BG, DISABLED_BTN_BORDER,
    INACTIVE_TAB_BG, INACTIVE_TAB_HOVER_BG,
)

logger = get_logger(__name__)

_ARB_TYPES = [("VOLT", "Voltage"), ("CURR", "Current")]

# (shape_key, 显示名, 图标文件名) —— 顺序即下拉与 QStackedWidget 页序
_ARB_SHAPES = [
    ("none", "No Arb Configured", "arb_none.svg"),
    ("sine", "Sine", "arb_sine.svg"),
    ("step", "Step", "arb_step.svg"),
    ("ramp", "Ramp", "arb_ramp.svg"),
    ("staircase", "Staircase", "arb_staircase.svg"),
    ("pulse", "Pulse", "arb_pulse.svg"),
    ("trapezoid", "Trapezoid", "arb_trapezoid.svg"),
    ("exponential", "Exponential", "arb_exponential.svg"),
    ("cdwell", "Constant Dwell (CD)", "arb_cdwell.svg"),
    ("udef", "User Defined", "arb_udef.svg"),
    ("seq", "Sequence", "arb_sequence.svg"),
]

# SEQ 本阶段占位（编辑后续版本提供）；IT2705 无 CDW 指令、UDEF 为机内波形文件、SEQ 语法不同
_ARB_PLACEHOLDER_SHAPES = frozenset({"seq"})
_ARB_IT2705_UNSUPPORTED = frozenset({"cdwell", "udef", "seq"})

# 旧版预设（pulse_v/pulse_i 与旧字段名）兼容映射
_LEGACY_SHAPE_MAP = {"pulse_v": ("pulse", "VOLT"), "pulse_i": ("pulse", "CURR")}
_LEGACY_FIELD_MAP = {"i0": "v0", "i1": "v1", "offset_v": "offset", "ampl_vrms": "ampl"}

# shape_key -> [(label_tpl, field_key, default, wheel_step, kind), ...]
# label_tpl 中 {u} 随 Arb Type 替换为 V / A；kind: level/time/freq/steps/list_level/list_time
# 时间字段按时间流排序（start -> top -> end），field_key 与驱动参数对应
_ARB_FIELDS = {
    "none": [],
    "sine": [
        ("DC Offset ({u}):", "offset", "3.3", 0.1, "level"),
        ("Amplitude ({u}rms):", "ampl", "0.1", 0.01, "level"),
        ("Frequency (Hz):", "freq_hz", "1000", 1, "freq"),
    ],
    "step": [
        ("Start Level ({u}):", "v0", "3.3", 0.1, "level"),
        ("End Level ({u}):", "v1", "3.8", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.01", 0.001, "time"),
        ("End Hold (s):", "t1", "0.01", 0.001, "time"),
    ],
    "ramp": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("End Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.005", 0.001, "time"),
        ("Rise Time (s):", "rt", "0.05", 0.001, "time"),
        ("End Hold (s):", "t1", "0.005", 0.001, "time"),
    ],
    "staircase": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("End Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.005", 0.001, "time"),
        ("Stair Time (s):", "t1", "0.05", 0.001, "time"),
        ("End Hold (s):", "t2", "0.005", 0.001, "time"),
        ("Steps:", "steps", "10", 1, "steps"),
    ],
    "pulse": [
        ("Base Level ({u}):", "v0", "3.3", 0.1, "level"),
        ("Top Level ({u}):", "v1", "3.8", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.0005", 0.0001, "time"),
        ("Top Hold (s):", "t2", "0.0005", 0.0001, "time"),
        ("End Hold (s):", "t1", "0", 0.0001, "time"),
        ("Frequency (Hz):", "freq_hz", "100", 1, "freq"),
    ],
    "trapezoid": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("Top Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Hold (s):", "t0", "0.005", 0.001, "time"),
        ("Rise Time (s):", "rt", "0.01", 0.001, "time"),
        ("Top Hold (s):", "tt", "0.02", 0.001, "time"),
        ("Fall Time (s):", "ft", "0.01", 0.001, "time"),
        ("End Hold (s):", "t1", "0.005", 0.001, "time"),
    ],
    "exponential": [
        ("Start Level ({u}):", "v0", "3.0", 0.1, "level"),
        ("End Level ({u}):", "v1", "4.0", 0.1, "level"),
        ("Start Delay (s):", "t0", "0.005", 0.001, "time"),
        ("Time Constant (s):", "tc", "0.02", 0.001, "time"),
        ("Total Time (s):", "t1", "0.1", 0.001, "time"),
    ],
    "cdwell": [
        ("Levels ({u}, comma list):", "levels", "3.2, 3.4, 3.6, 3.8", None, "list_level"),
        ("Dwell (s):", "dwell", "0.01", 0.001, "time"),
    ],
    "udef": [
        ("Levels ({u}, comma list):", "levels", "3.0, 3.5, 4.0, 3.5", None, "list_level"),
        ("Dwells (s, comma list, optional):", "dwells", "", None, "list_time"),
    ],
    "seq": [],
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

_ARB_ICON_COLOR = "#c8d5e2"


def _arb_presets_path() -> str:
    return os.path.join(get_user_data_dir("n6705c"), _ARB_PRESETS_FILENAME)


def _arb_icon_dir() -> str:
    return os.path.join(get_resource_base(), "resources", "icons")


class _ArbRunWorker(QObject):
    """Arb 下发 / 停止 worker（QThread 内执行，UI 不阻塞）。"""

    finished = Signal(str, bool, str)  # dev_label, success, message

    def __init__(self, instance, dev_label, channel, mode,
                 shape_key=None, values=None, arb_type="VOLT",
                 continuous=False, io_lock=None):
        super().__init__()
        self._instance = instance
        self._dev_label = dev_label
        self._channel = channel
        self._mode = mode  # "apply" | "stop"
        self._shape_key = shape_key
        self._values = values or {}
        self._arb_type = arb_type
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
        shape = self._shape_key
        tp = self._arb_type
        if shape == "none":
            inst.set_arb_none(ch, tp)
            return
        if shape == "sine":
            inst.set_arb_sine(ch, v["offset"], v["ampl"], v["freq_hz"], arb_type=tp)
        elif shape == "step":
            inst.set_arb_step(ch, v["v0"], v["v1"], v["t0"], v["t1"], arb_type=tp)
        elif shape == "ramp":
            inst.set_arb_ramp(ch, v["v0"], v["v1"], v["t0"], v["rt"], v["t1"], arb_type=tp)
        elif shape == "staircase":
            inst.set_arb_staircase(
                ch, v["v0"], v["v1"], v["t0"], v["t1"], v["t2"], int(v["steps"]), arb_type=tp
            )
        elif shape == "pulse":
            inst.set_arb_pulse(
                ch, v["v0"], v["v1"], v["t0"], v["t1"], v["t2"], v["freq_hz"], arb_type=tp
            )
        elif shape == "trapezoid":
            inst.set_arb_trapezoid(
                ch, v["v0"], v["v1"], v["t0"], v["rt"], v["tt"], v["ft"], v["t1"], arb_type=tp
            )
        elif shape == "exponential":
            inst.set_arb_exponential(
                ch, v["v0"], v["v1"], v["t0"], v["tc"], v["t1"], arb_type=tp
            )
        elif shape == "cdwell":
            inst.set_arb_constant_dwell(ch, v["levels"], v["dwell"], arb_type=tp)
        elif shape == "udef":
            inst.set_arb_user_defined(ch, v["levels"], v.get("dwells"), arb_type=tp)
        else:
            raise ValueError(f"Unknown arb shape: {shape}")
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
        self._arb_last_shape = "none"
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
        body_layout.setContentsMargins(12, 12, 12, 12)
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

        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_label = QLabel("Arb Type:")
        type_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        type_row.addWidget(type_label)
        self.arb_type_combo = DarkComboBox()
        for _key, label in _ARB_TYPES:
            self.arb_type_combo.addItem(label)
        self.arb_type_combo.currentIndexChanged.connect(self._arb_on_type_changed)
        type_row.addWidget(self.arb_type_combo, 1)

        shape_row = QHBoxLayout()
        shape_row.setSpacing(8)
        shape_label = QLabel("Waveform:")
        shape_label.setStyleSheet(
            f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
        )
        shape_row.addWidget(shape_label)
        self.arb_shape_combo = DarkComboBox()
        for _key, label, icon_file in _ARB_SHAPES:
            icon = tinted_svg_icon(
                os.path.join(_arb_icon_dir(), icon_file), _ARB_ICON_COLOR, 16
            )
            self.arb_shape_combo.addItem(icon, label)
        self.arb_shape_combo.currentIndexChanged.connect(self._arb_on_shape_changed)
        shape_row.addWidget(self.arb_shape_combo, 1)
        self.arb_shape_preview = QLabel()
        self.arb_shape_preview.setFixedSize(32, 32)
        self.arb_shape_preview.setStyleSheet(
            "QLabel { background: transparent; border: none; }"
        )
        shape_row.addWidget(self.arb_shape_preview)

        self.arb_params_stack = QStackedWidget()
        self.arb_param_inputs = {}  # shape_key -> {field_key: SelectAllLineEdit}
        self.arb_param_labels = {}  # shape_key -> [(QLabel, label_tpl)]
        for shape_key, _label, _icon in _ARB_SHAPES:
            page, inputs, labels = self._create_arb_params_page(shape_key)
            self.arb_params_stack.addWidget(page)
            self.arb_param_inputs[shape_key] = inputs
            self.arb_param_labels[shape_key] = labels

        # 左列紧凑选择器（Arb Type / Waveform），右侧为对应波形参数区
        config_row = QHBoxLayout()
        config_row.setSpacing(10)
        selector_col = QVBoxLayout()
        selector_col.setSpacing(8)
        selector_col.addLayout(type_row)
        selector_col.addLayout(shape_row)
        selector_col.addStretch()
        config_row.addLayout(selector_col)
        config_row.addWidget(self.arb_params_stack, 1)
        body_layout.addLayout(config_row, 1)

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
        self._arb_update_shape_icon()
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
        labels = []
        fields = _ARB_FIELDS[shape_key]
        if not fields:
            hint = QLabel(
                "Sequence editing will be available in a future release."
                if shape_key == "seq"
                else "Clears the Arb configuration of this channel."
            )
            hint.setWordWrap(True)
            hint.setStyleSheet(
                f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
            )
            grid.addWidget(hint, 0, 0, 1, 4)
        for idx, (label_tpl, field_key, default_text, wheel_step, _kind) in enumerate(fields):
            row, col = divmod(idx, 2)
            label = QLabel(label_tpl.replace("{u}", "V"))
            label.setStyleSheet(
                f"QLabel {{ font-size: 11px; color: {MUTED_TEXT}; border: none; background: transparent; }}"
            )
            edit = SelectAllLineEdit(default_text)
            edit.set_wheel_step(wheel_step)
            edit.setAlignment(Qt.AlignCenter)
            edit.setStyleSheet(_ARB_INPUT_STYLE)
            if _kind in ("list_level", "list_time"):
                edit.setMinimumWidth(200)
                edit.setAlignment(Qt.AlignLeft)
                grid.addWidget(label, row * 2, 0, 1, 4)
                grid.addWidget(edit, row * 2 + 1, 0, 1, 4)
            else:
                edit.setFixedWidth(100)
                grid.addWidget(label, row, col * 2)
                grid.addWidget(edit, row, col * 2 + 1)
            inputs[field_key] = edit
            labels.append((label, label_tpl))
        grid.setColumnStretch(4, 1)
        return page, inputs, labels

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
        self._arb_refresh_shape_availability()
        self._arb_update_shape_icon()
        self._refresh_arb_tab_styles()

    # --------------------------------------------------- type / shape / units
    def _arb_current_type(self):
        return _ARB_TYPES[self.arb_type_combo.currentIndex()][0]

    def _arb_current_shape_key(self):
        idx = self.arb_shape_combo.currentIndex()
        return _ARB_SHAPES[idx][0]

    def _arb_on_type_changed(self, _index):
        if self._arb_loading:
            return
        self._arb_update_unit_labels()
        self._arb_store_current_params()

    def _arb_on_shape_changed(self, index):
        new_shape = _ARB_SHAPES[index][0]
        old_shape = self._arb_last_shape
        self._arb_last_shape = new_shape
        if old_shape != new_shape:
            # 滚轮调值走 setText（仅 textChanged），切走前全量保存旧页
            self._arb_store_shape_params(old_shape)
        self.arb_params_stack.setCurrentIndex(index)
        if not self._arb_loading:
            self._arb_load_shape_params(new_shape)
            self._arb_store_current_params()
        self._arb_update_shape_icon()

    def _arb_update_unit_labels(self):
        unit = "V" if self._arb_current_type() == "VOLT" else "A"
        for shape_labels in self.arb_param_labels.values():
            for label, tpl in shape_labels:
                label.setText(tpl.replace("{u}", unit))

    def _arb_update_shape_icon(self):
        if not hasattr(self, "arb_shape_preview"):
            return
        idx = self.arb_shape_combo.currentIndex()
        icon_file = _ARB_SHAPES[idx][2]
        pixmap = tinted_svg_pixmap(
            os.path.join(_arb_icon_dir(), icon_file), _ARB_ICON_COLOR, 28
        )
        self.arb_shape_preview.setPixmap(pixmap)

    def _arb_refresh_shape_availability(self):
        """按当前通道仪器型号禁用不支持的波形（SEQ 全局占位禁用）。"""
        if not hasattr(self, "arb_shape_combo"):
            return
        instance = self.devices.get(self._arb_current_device, {}).get("n6705c")
        is_it2705 = bool(instance is not None and is_it2705_instrument(instance))
        model = self.arb_shape_combo.model()
        current_key = self._arb_current_shape_key()
        need_fallback = False
        for idx, (key, _label, _icon) in enumerate(_ARB_SHAPES):
            item = model.item(idx)
            if item is None:
                continue
            disabled = key in _ARB_PLACEHOLDER_SHAPES or (
                is_it2705 and key in _ARB_IT2705_UNSUPPORTED
            )
            item.setEnabled(not disabled)
            if disabled:
                reason = (
                    "Sequence editing will be available in a future release"
                    if key == "seq"
                    else "Not supported by IT2705"
                )
                item.setToolTip(reason)
            else:
                item.setToolTip("")
            if disabled and key == current_key:
                need_fallback = True
        if need_fallback:
            self._arb_loading = True
            try:
                self.arb_shape_combo.setCurrentIndex(0)  # none
                self.arb_params_stack.setCurrentIndex(0)
                self._arb_last_shape = "none"
            finally:
                self._arb_loading = False
            self._arb_update_shape_icon()

    # --------------------------------------------------------- params memory
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
        entry["arb_type"] = self._arb_current_type()
        entry["shape"] = self._arb_current_shape_key()
        entry["continuous"] = self.arb_continuous_toggle.isChecked()
        entry["params"][shape] = params

    def _arb_store_current_params(self):
        self._arb_store_shape_params(self._arb_current_shape_key())

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

    def _arb_load_channel_params(self):
        if not hasattr(self, "arb_shape_combo"):
            return
        self._arb_loading = True
        try:
            key = (self._arb_current_device, self._arb_current_channel)
            entry = self._arb_param_store.get(key, {})
            arb_type = entry.get("arb_type", "VOLT")
            type_keys = [k for k, _label in _ARB_TYPES]
            if arb_type not in type_keys:
                arb_type = "VOLT"
            self.arb_type_combo.setCurrentIndex(type_keys.index(arb_type))
            shape = entry.get("shape", "none")
            shape_keys = [k for k, _label, _icon in _ARB_SHAPES]
            if shape not in shape_keys:
                shape = "none"
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
        self._arb_update_unit_labels()
        self._arb_refresh_shape_availability()
        self._arb_update_shape_icon()

    def _arb_collect_values(self):
        """解析当前波形参数为数值；非法输入抛 ValueError。"""
        shape = self._arb_current_shape_key()
        values = {}
        for label_tpl, field_key, _default, _step, kind in _ARB_FIELDS[shape]:
            text = self.arb_param_inputs[shape][field_key].text().strip()
            unit = "V" if self._arb_current_type() == "VOLT" else "A"
            label = label_tpl.replace("{u}", unit)
            if kind in ("list_level", "list_time"):
                if not text:
                    if kind == "list_time":
                        values[field_key] = None
                        continue
                    raise ValueError(f"{label.rstrip(':')} requires at least one value")
                try:
                    values[field_key] = [
                        float(part) for part in text.split(",") if part.strip()
                    ]
                except ValueError as exc:
                    raise ValueError(f"{label.rstrip(':')} invalid list: '{text}'") from exc
                if not values[field_key]:
                    if kind == "list_time":
                        values[field_key] = None
                        continue
                    raise ValueError(f"{label.rstrip(':')} requires at least one value")
            else:
                try:
                    values[field_key] = float(text)
                except ValueError as exc:
                    raise ValueError(f"{label.rstrip(':')} invalid: '{text}'") from exc
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
        shape = self._arb_current_shape_key()
        if shape in _ARB_PLACEHOLDER_SHAPES:
            return
        try:
            values = self._arb_collect_values()
        except ValueError as exc:
            QMessageBox.warning(self, "Arb Set", str(exc))
            return
        self._arb_store_current_params()
        self._arb_start_worker(dev_label, instance, ch, "apply",
                               shape_key=shape,
                               values=values,
                               arb_type=self._arb_current_type(),
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
        self._arb_presets = [self._arb_normalize_preset(p) for p in presets]
        self._arb_refresh_preset_list()

    @staticmethod
    def _arb_normalize_preset(preset):
        """旧版 pulse_v/pulse_i 与旧字段名映射到新结构。"""
        preset = dict(preset)
        shape = preset.get("shape", "none")
        if shape in _LEGACY_SHAPE_MAP:
            shape, arb_type = _LEGACY_SHAPE_MAP[shape]
            preset.setdefault("arb_type", arb_type)
        preset["shape"] = shape
        preset.setdefault("arb_type", "VOLT")
        params = preset.get("params")
        if isinstance(params, dict):
            preset["params"] = {
                _LEGACY_FIELD_MAP.get(k, k): v for k, v in params.items()
            }
        return preset

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
        shape_label = {k: lbl for k, lbl, _i in _ARB_SHAPES}.get(shape, shape)
        type_label = dict(_ARB_TYPES).get(preset.get("arb_type", "VOLT"), "Voltage")
        params = preset.get("params", {})
        parts = [f"{k}={v}" for k, v in params.items()]
        cont = "continuous" if preset.get("continuous") else "single"
        return f"{shape_label} | {type_label} | {cont} | {', '.join(parts)}"

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
            "arb_type": self._arb_current_type(),
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
        shape = preset.get("shape", "none")
        shape_keys = [k for k, _label, _icon in _ARB_SHAPES]
        if shape not in shape_keys:
            return
        self._arb_loading = True
        try:
            arb_type = preset.get("arb_type", "VOLT")
            type_keys = [k for k, _label in _ARB_TYPES]
            self.arb_type_combo.setCurrentIndex(
                type_keys.index(arb_type) if arb_type in type_keys else 0
            )
            self.arb_shape_combo.setCurrentIndex(shape_keys.index(shape))
            self.arb_params_stack.setCurrentIndex(shape_keys.index(shape))
            self.arb_continuous_toggle.setChecked(bool(preset.get("continuous", False)))
            params = preset.get("params", {})
            for field_key, edit in self.arb_param_inputs[shape].items():
                if field_key in params and params[field_key] is not None:
                    value = params[field_key]
                    if isinstance(value, list):
                        edit.setText(", ".join(str(v) for v in value))
                    else:
                        edit.setText(str(value))
            self._arb_last_shape = shape
        finally:
            self._arb_loading = False
        self._arb_update_unit_labels()
        self._arb_update_shape_icon()
        self._arb_store_current_params()
