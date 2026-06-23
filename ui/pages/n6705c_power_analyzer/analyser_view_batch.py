#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt
from log_config import get_logger
from ui.pages.n6705c_power_analyzer.widgets import (
    _batch_channel_button_style,
    collapsible_header_style,
    PANEL_BG, PANEL_BORDER, CONTAINER_RADIUS, WIDGET_RADIUS,
    CARD_BG, CARD_BORDER, LABEL_DIM,
    DISABLED_TEXT, DISABLED_BTN_BG, DISABLED_BTN_BORDER,
)

logger = get_logger(__name__)


class BatchViewMixin:
    _AUTO_SET_SPECIAL_VOLTAGES = [0.625, 0.67, 0.725, 0.78]

    def _create_batch_tools_panel(self):
        self.batch_collapsed = False

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: #0b1020; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.batch_toggle_btn = QPushButton("\u25bc  Quick Setup")
        self.batch_toggle_btn.setStyleSheet(collapsible_header_style(False))
        self.batch_toggle_btn.clicked.connect(self._toggle_batch_panel)
        outer_layout.addWidget(self.batch_toggle_btn)

        self.batch_content = QFrame()
        self.batch_content.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {PANEL_BORDER};
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
            }}
        """)
        self.batch_content.setVisible(True)

        content_layout = QVBoxLayout(self.batch_content)
        content_layout.setContentsMargins(16, 10, 16, 14)
        content_layout.setSpacing(12)

        self.batch_channel_buttons = []
        self.batch_voltage_inputs = {}
        self.batch_current_inputs = {}

        self._batch_columns_widget = QWidget()
        self._batch_columns_widget.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._batch_columns_layout = QHBoxLayout(self._batch_columns_widget)
        self._batch_columns_layout.setContentsMargins(0, 0, 0, 0)
        self._batch_columns_layout.setSpacing(12)
        content_layout.addWidget(self._batch_columns_widget)

        self._build_batch_columns()

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {PANEL_BORDER}; border: none;")
        content_layout.addWidget(sep)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self._batch_measure_btn = QPushButton("Measure")
        self._batch_set_btn = QPushButton("Set")
        self._batch_auto_btn = QPushButton("Auto Set")
        self._batch_auto_20mv_btn = QPushButton("Auto Set (+20mV)")

        _batch_btn_base = f"""
            QPushButton {{{{
                background-color: {{bg}}; color: {{fg}};
                border: 1px solid {{border}}; border-radius: {WIDGET_RADIUS};
                padding: 9px 18px; font-size: 12px; font-weight: 700;
            }}}}
            QPushButton:hover {{{{ background-color: {{hover_bg}}; color: {{hover_fg}}; border: 1px solid {{hover_border}}; }}}}
            QPushButton:disabled {{{{ background-color: {DISABLED_BTN_BG}; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}}}
        """

        self._batch_measure_btn.setStyleSheet(_batch_btn_base.format(
            bg="#0c1a38", fg="#8eb4e8", border="#23417a",
            hover_bg="#122448", hover_fg="#b8d4ff", hover_border="#3a6cc8"
        ))
        self._batch_set_btn.setStyleSheet(_batch_btn_base.format(
            bg="#0c1a38", fg="#8eb4e8", border="#23417a",
            hover_bg="#122448", hover_fg="#b8d4ff", hover_border="#3a6cc8"
        ))
        _batch_auto_style = f"""
            QPushButton {{
                background-color: #4318d9; color: #ffffff;
                border: 1px solid #5a2ef0; border-radius: {WIDGET_RADIUS};
                padding: 9px 24px; font-size: 12px; font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #5628f0; color: #ffffff; border: 1px solid #7040ff; }}
            QPushButton:disabled {{ background-color: #1a1040; color: #4a3a7a; border: 1px solid #2a1860; }}
        """
        self._batch_auto_btn.setStyleSheet(_batch_auto_style)
        self._batch_auto_20mv_btn.setStyleSheet(_batch_auto_style)

        buttons_layout.addWidget(self._batch_measure_btn, 1)
        buttons_layout.addWidget(self._batch_set_btn, 1)
        buttons_layout.addWidget(self._batch_auto_btn, 1)
        buttons_layout.addWidget(self._batch_auto_20mv_btn, 1)

        self._batch_measure_btn.clicked.connect(self._on_batch_measure)
        self._batch_set_btn.clicked.connect(self._on_batch_set)
        self._batch_auto_btn.clicked.connect(self._on_batch_auto_set)
        self._batch_auto_20mv_btn.clicked.connect(self._on_batch_auto_20mv)

        content_layout.addLayout(buttons_layout)

        outer_layout.addWidget(self.batch_content)
        return outer

    def _toggle_batch_panel(self):
        self.batch_collapsed = not self.batch_collapsed
        self.batch_content.setVisible(not self.batch_collapsed)
        if self.batch_collapsed:
            self.batch_toggle_btn.setText("\u25b6  Quick Setup")
        else:
            self.batch_toggle_btn.setText("\u25bc  Quick Setup")
        self.batch_toggle_btn.setStyleSheet(collapsible_header_style(self.batch_collapsed))

    def _build_batch_columns(self):
        for i in reversed(range(self._batch_columns_layout.count())):
            item = self._batch_columns_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()

        self.batch_channel_buttons.clear()
        self.batch_voltage_inputs.clear()
        self.batch_current_inputs.clear()

        _label_style = f"font-size: 12px; color: {LABEL_DIM}; font-weight: 600; border: none; background: transparent;"
        _input_style = f"""
            QLineEdit {{
                background-color: #111d36; color: #99aacc;
                border: 1px solid #1e3050; border-radius: {WIDGET_RADIUS};
                padding: 7px 10px; font-size: 12px; font-weight: 600;
                text-align: center;
            }}
            QLineEdit:focus {{ border: 1px solid #3a5a90; color: #b0c0e0; }}
            QLineEdit:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """

        dual = self._is_dual_mode()
        if dual:
            device_list = [("A", "#00f5c4"), ("B", "#f2994a")]
        else:
            single_label = self._get_single_device_label()
            device_list = [(single_label, "#00f5c4")]

        for dev_label, dev_color in device_list:
            dev_frame = QFrame()
            dev_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {CARD_BG};
                    border: 1px solid {CARD_BORDER};
                    border-radius: {CONTAINER_RADIUS};
                }}
            """)
            grid = QGridLayout(dev_frame)
            grid.setContentsMargins(10, 8, 10, 8)
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(8)

            row = 0
            if dual:
                col_title = QLabel(f"Device {dev_label}")
                col_title.setStyleSheet(f"color: {dev_color}; font-weight: 800; font-size: 13px; border: none; background: transparent;")
                grid.addWidget(col_title, row, 0, 1, 5)
                row += 1

            ch_label = QLabel("通道选择")
            ch_label.setStyleSheet(_label_style)
            ch_label.setFixedWidth(70)
            grid.addWidget(ch_label, row, 0)
            for col_idx, ch_idx in enumerate(range(1, 5)):
                cb = QPushButton(f"CH {ch_idx}")
                cb.setCheckable(True)
                if dev_label != "B" and ch_idx in [2, 3, 4]:
                    cb.setChecked(True)
                cb.setStyleSheet(_batch_channel_button_style())
                self.batch_channel_buttons.append((dev_label, ch_idx, cb))
                grid.addWidget(cb, row, col_idx + 1)
            row += 1

            v_label = QLabel("电压 (V)")
            v_label.setStyleSheet(_label_style)
            v_label.setFixedWidth(70)
            grid.addWidget(v_label, row, 0)
            self.batch_voltage_inputs[dev_label] = []
            for col_idx, v in enumerate([3.8, 0.8, 1.2, 1.8]):
                inp = QLineEdit(f"{v:.4f}")
                inp.setAlignment(Qt.AlignCenter)
                inp.setStyleSheet(_input_style)
                self.batch_voltage_inputs[dev_label].append(inp)
                grid.addWidget(inp, row, col_idx + 1)
            row += 1

            c_label = QLabel("限流 (A)")
            c_label.setStyleSheet(_label_style)
            c_label.setFixedWidth(70)
            grid.addWidget(c_label, row, 0)
            self.batch_current_inputs[dev_label] = []
            for col_idx, c in enumerate([0.2, 0.02, 0.02, 0.02]):
                inp = QLineEdit(f"{c:.4f}")
                inp.setAlignment(Qt.AlignCenter)
                inp.setStyleSheet(_input_style)
                self.batch_current_inputs[dev_label].append(inp)
                grid.addWidget(inp, row, col_idx + 1)

            for col in range(1, 5):
                grid.setColumnStretch(col, 1)

            self._batch_columns_layout.addWidget(dev_frame, 1)

    def _get_selected_batch_channels(self, dev_label):
        return [ch for dl, ch, cb in self.batch_channel_buttons if dl == dev_label and cb.isChecked()]

    def _on_batch_measure(self):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._get_selected_batch_channels(label)
                for ch in channels:
                    try:
                        dev["n6705c"].set_mode(ch, "VMETer")
                        dev["n6705c"].channel_on(ch)
                    except Exception as e:
                        logger.error("[%s] CH%d VMeter failed: %s", label, ch, e)
        self._start_channel_sync()

    def _on_batch_set(self):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._get_selected_batch_channels(label)
                if label not in self.batch_voltage_inputs:
                    continue
                voltages = [float(inp.text()) for inp in self.batch_voltage_inputs[label]]
                currents = [float(inp.text()) for inp in self.batch_current_inputs[label]]
                for ch in channels:
                    try:
                        idx = ch - 1
                        dev["n6705c"].set_mode(ch, "PS2Q")
                        dev["n6705c"].set_voltage(ch, voltages[idx])
                        dev["n6705c"].set_current_limit(ch, currents[idx])
                        dev["n6705c"].channel_on(ch)
                    except Exception as e:
                        logger.error("[%s] CH%d Set failed: %s", label, ch, e)
        self._start_channel_sync()

    def _on_batch_auto_20mv(self):
        self._on_batch_auto_with_offset(0.02)

    @staticmethod
    def _align_voltage(v, special_values=None):
        if special_values is None:
            special_values = BatchViewMixin._AUTO_SET_SPECIAL_VOLTAGES
        grid_v = round(round(v / 0.05) * 0.05, 4)
        best = grid_v
        best_dist = abs(v - grid_v)
        for sv in special_values:
            dist = abs(v - sv)
            if dist < best_dist:
                best = sv
                best_dist = dist
        return best

    def _on_batch_auto_set(self):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._get_selected_batch_channels(label)
                for ch in channels:
                    try:
                        dev["n6705c"].set_mode(ch, "VMETer")
                        v = float(dev["n6705c"].measure_voltage(ch))
                        new_v = self._align_voltage(v)
                        dev["n6705c"].set_mode(ch, "PS2Q")
                        dev["n6705c"].set_voltage(ch, new_v)
                        dev["n6705c"].set_current_limit(ch, 0.02)
                        dev["n6705c"].channel_on(ch)
                        final_limit = 0.07 if new_v < 1.0 else 0.15
                        dev["n6705c"].set_current_limit(ch, final_limit)
                    except Exception as e:
                        logger.error("[%s] CH%d Auto Set failed: %s", label, ch, e)
        self._start_channel_sync()

    def _on_batch_auto_with_offset(self, offset):
        with self._state_poller.writing():
            for label, dev in self.devices.items():
                if not dev["is_connected"] or not dev["n6705c"]:
                    continue
                channels = self._get_selected_batch_channels(label)
                for ch in channels:
                    try:
                        dev["n6705c"].set_mode(ch, "VMETer")
                        v = float(dev["n6705c"].measure_voltage(ch))
                        new_v = v + offset
                        dev["n6705c"].set_mode(ch, "PS2Q")
                        dev["n6705c"].set_voltage(ch, new_v)
                        dev["n6705c"].set_current_limit(ch, 0.02)
                        dev["n6705c"].channel_on(ch)
                        final_limit = 0.07 if new_v < 1.0 else 0.15
                        dev["n6705c"].set_current_limit(ch, final_limit)
                    except Exception as e:
                        logger.error("[%s] CH%d Auto failed: %s", label, ch, e)
        self._start_channel_sync()
