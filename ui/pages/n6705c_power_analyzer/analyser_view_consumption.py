#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QCheckBox, QSizePolicy, QFileDialog,
)
from PySide6.QtCore import Qt, QThread
from log_config import get_logger
from ui.pages.n6705c_power_analyzer.widgets import (
    _get_checkmark_path,
    _format_current,
    collapsible_header_style,
    CHANNEL_COLORS,
    PANEL_BG, PANEL_BORDER, CONTAINER_RADIUS, WIDGET_RADIUS,
    CARD_BG, CARD_BORDER, MUTED_TEXT,
    DISABLED_TEXT, DISABLED_BTN_BORDER,
)
from core.n6705c import ConsumptionTestWorker as _ConsumptionTestWorker

logger = get_logger(__name__)


class ConsumptionViewMixin:
    def _create_consumption_test_panel(self):
        self.ct_collapsed = True

        outer = QWidget()
        outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.ct_toggle_btn = QPushButton("\u25b6  Current Consumption Test")
        self.ct_toggle_btn.setStyleSheet(collapsible_header_style(True))
        self.ct_toggle_btn.clicked.connect(self._toggle_ct_panel)
        outer_layout.addWidget(self.ct_toggle_btn)

        self.ct_content = QFrame()
        self.ct_content.setStyleSheet(f"""
            QFrame {{
                background-color: {PANEL_BG};
                border: 1px solid {PANEL_BORDER};
                border-top: none;
                border-bottom-left-radius: {CONTAINER_RADIUS};
                border-bottom-right-radius: {CONTAINER_RADIUS};
            }}
        """)
        self.ct_content.setVisible(False)

        layout = QVBoxLayout(self.ct_content)
        layout.setContentsMargins(16, 10, 16, 14)
        layout.setSpacing(10)

        _ct_input_style = f"""
            QLineEdit {{
                background-color: #111d36; color: #dbe6ff;
                border: 1px solid #1e3050; border-radius: {WIDGET_RADIUS};
                padding: 4px 8px; font-size: 12px; font-weight: 600;
            }}
            QLineEdit:focus {{ border: 1px solid #3a5a90; color: #ffffff; }}
            QLineEdit:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """

        params_row = QHBoxLayout()
        params_row.setSpacing(12)

        time_label = QLabel("Test Time (s):")
        time_label.setStyleSheet(f"font-size: 11px; color: {MUTED_TEXT}; border: none;")
        self.ct_test_time_input = QLineEdit("10")
        self.ct_test_time_input.setFixedWidth(80)
        self.ct_test_time_input.setAlignment(Qt.AlignCenter)
        self.ct_test_time_input.setStyleSheet(_ct_input_style)

        period_label = QLabel("Sample Period (us):")
        period_label.setStyleSheet(f"font-size: 11px; color: {MUTED_TEXT}; border: none;")
        self.ct_sample_period_input = QLineEdit("20")
        self.ct_sample_period_input.setFixedWidth(80)
        self.ct_sample_period_input.setAlignment(Qt.AlignCenter)
        self.ct_sample_period_input.setStyleSheet(_ct_input_style)

        params_row.addWidget(time_label)
        params_row.addWidget(self.ct_test_time_input)
        params_row.addSpacing(8)
        params_row.addWidget(period_label)
        params_row.addWidget(self.ct_sample_period_input)
        params_row.addStretch()

        self.ct_save_btn = QPushButton("Save DataLog")
        self.ct_save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0b1730; color: #dbe6ff;
                border: 1px solid #23417a; border-radius: {WIDGET_RADIUS};
                font-size: 11px; padding: 4px 10px; min-height: 28px;
            }}
            QPushButton:hover {{ background-color: #10203e; }}
        """)
        params_row.addWidget(self.ct_save_btn)
        layout.addLayout(params_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.ct_start_btn = QPushButton("\u25b6  START TEST")
        self.ct_start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ct_start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #062b2b; color: #00f5c4;
                border: 1px solid #00cfa6; border-radius: {WIDGET_RADIUS};
                font-weight: 700; font-size: 13px; min-height: 38px;
            }}
            QPushButton:hover {{ background-color: #0a3a3a; }}
            QPushButton:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """)

        self.ct_stop_btn = QPushButton("\u25a0  STOP")
        self.ct_stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.ct_stop_btn.setEnabled(False)
        self.ct_stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #2a0a1c; color: #ff4fa3;
                border: 1px solid #d63384; border-radius: {WIDGET_RADIUS};
                font-weight: 700; font-size: 13px; min-height: 38px;
            }}
            QPushButton:hover {{ background-color: #3a1028; }}
            QPushButton:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
        """)

        btn_row.addWidget(self.ct_start_btn, 1)
        btn_row.addWidget(self.ct_stop_btn, 1)
        layout.addLayout(btn_row)

        self._ct_cards_widget = QWidget()
        self._ct_cards_widget.setStyleSheet("QWidget { background: transparent; border: none; }")
        self._ct_cards_layout = QHBoxLayout(self._ct_cards_widget)
        self._ct_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._ct_cards_layout.setSpacing(12)
        self.ct_channel_cards = {}
        self._build_ct_cards()
        layout.addWidget(self._ct_cards_widget, 1)

        self.ct_start_btn.clicked.connect(self._ct_start_test)
        self.ct_stop_btn.clicked.connect(self._ct_stop_test)
        self.ct_save_btn.clicked.connect(self._ct_save_datalog)

        outer_layout.addWidget(self.ct_content)
        return outer

    def _toggle_ct_panel(self):
        self.ct_collapsed = not self.ct_collapsed
        self.ct_content.setVisible(not self.ct_collapsed)
        if self.ct_collapsed:
            self.ct_toggle_btn.setText("\u25b6  Current Consumption Test")
        else:
            self.ct_toggle_btn.setText("\u25bc  Current Consumption Test")
        self.ct_toggle_btn.setStyleSheet(collapsible_header_style(self.ct_collapsed))

    def _build_ct_cards(self):
        for i in reversed(range(self._ct_cards_layout.count())):
            item = self._ct_cards_layout.takeAt(i)
            w = item.widget()
            if w:
                w.deleteLater()
        self.ct_channel_cards.clear()

        dual = self._is_dual_mode()
        if dual:
            for dev_label, dev_color in [("A", "#00f5c4"), ("B", "#f2994a")]:
                dev_frame = QFrame()
                dev_frame.setStyleSheet(f"""
                    QFrame {{ background-color: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: {CONTAINER_RADIUS}; }}
                """)
                dev_layout = QVBoxLayout(dev_frame)
                dev_layout.setContentsMargins(10, 8, 10, 8)
                dev_layout.setSpacing(6)

                dev_title = QLabel(f"Device {dev_label}")
                dev_title.setStyleSheet(f"color: {dev_color}; font-weight: 700; font-size: 12px; border: none;")
                dev_layout.addWidget(dev_title)

                ch_row = QHBoxLayout()
                ch_row.setSpacing(6)
                for ch in range(1, 5):
                    card = self._create_ct_channel_card(dev_label, ch)
                    ch_row.addWidget(card, 1)
                dev_layout.addLayout(ch_row)

                self._ct_cards_layout.addWidget(dev_frame, 1)
        else:
            single_label = self._get_single_device_label()
            channels_row = QHBoxLayout()
            channels_row.setSpacing(10)
            ch_container = QWidget()
            ch_container.setStyleSheet("QWidget { background: transparent; border: none; }")
            ch_container_layout = QHBoxLayout(ch_container)
            ch_container_layout.setContentsMargins(0, 0, 0, 0)
            ch_container_layout.setSpacing(10)
            for ch in range(1, 5):
                card = self._create_ct_channel_card(single_label, ch)
                ch_container_layout.addWidget(card, 1)
            self._ct_cards_layout.addWidget(ch_container, 1)

    def _create_ct_channel_card(self, dev_label, ch_num):
        colors = CHANNEL_COLORS[ch_num]
        dual = self._is_dual_mode()
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{ background-color: {colors['bg']}; border: 1px solid {colors['border']}; border-radius: {CONTAINER_RADIUS}; }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setMinimumHeight(80 if dual else 100)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        icons = _get_checkmark_path(colors['accent'])
        checkbox = QCheckBox(f"CH {ch_num}")
        checkbox.setChecked(False)
        checkbox.setStyleSheet(f"""
            QCheckBox {{ color: #ffffff; font-size: 13px; font-weight: 700; background: transparent; spacing: 6px; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; image: url("{icons['unchecked']}"); }}
            QCheckBox::indicator:checked {{ image: url("{icons['checked']}"); }}
        """)

        top_row.addWidget(checkbox)
        top_row.addStretch()
        layout.addLayout(top_row)
        layout.addStretch()

        avg_label = QLabel("AVG CURRENT")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setStyleSheet("color: #8ea6cf; font-size: 10px; font-weight: 700; letter-spacing: 1.5px; border: none;")
        layout.addWidget(avg_label)

        value_label = QLabel("- - -")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['accent']}; font-size: 18px;
                font-weight: 700; letter-spacing: 2px;
            }}
        """)
        layout.addWidget(value_label)
        layout.addStretch()

        key = (dev_label, ch_num)
        self.ct_channel_cards[key] = {
            "card": card, "checkbox": checkbox, "value_label": value_label,
        }
        return card

    def _ct_start_test(self):
        if self.is_testing:
            return

        any_connected = any(d["is_connected"] for d in self.devices.values())
        if not any_connected:
            return

        try:
            test_time = float(self.ct_test_time_input.text())
            sample_period = float(self.ct_sample_period_input.text()) / 1_000_000.0
        except ValueError:
            return

        logger.debug("CT start_test: test_time=%s, sample_period=%s", test_time, sample_period)
        self.is_testing = True
        self.ct_start_btn.setEnabled(False)
        self.ct_stop_btn.setEnabled(True)

        for key in self.ct_channel_cards:
            self.ct_channel_cards[key]["value_label"].setText("- - -")

        self._test_finished_count = 0
        self._test_expected_count = 0

        for label, dev in self.devices.items():
            if not dev["is_connected"] or not dev["n6705c"]:
                continue
            channels = [ch for (dl, ch), card_data in self.ct_channel_cards.items()
                        if dl == label and card_data["checkbox"].isChecked()]
            if not channels:
                continue

            self._test_expected_count += 1
            worker = _ConsumptionTestWorker(dev["n6705c"], label, channels, test_time, sample_period)
            thread = QThread()
            worker.moveToThread(thread)
            thread.started.connect(worker.run)
            worker.channel_result.connect(self._ct_on_channel_result)
            worker.error.connect(self._ct_on_error)
            worker.finished.connect(thread.quit)
            worker.finished.connect(self._ct_on_one_finished)
            thread.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            self._test_threads[label] = thread
            self._test_workers[label] = worker
            thread.start()

        if self._test_expected_count == 0:
            self.is_testing = False
            self.ct_start_btn.setEnabled(True)
            self.ct_stop_btn.setEnabled(False)

    def _ct_on_channel_result(self, dev_label, ch, avg_current):
        logger.debug("CT channel result: %s CH%s = %.6e A", dev_label, ch, avg_current)
        key = (dev_label, ch)
        if key in self.ct_channel_cards:
            self.ct_channel_cards[key]["value_label"].setText(_format_current(avg_current))

    def _ct_on_error(self, err_msg):
        logger.error("Consumption test error: %s", err_msg)

    def _ct_on_one_finished(self):
        self._test_finished_count += 1
        logger.debug("CT one test finished: %d/%d", self._test_finished_count, self._test_expected_count)
        if self._test_finished_count >= self._test_expected_count:
            self.is_testing = False
            self.ct_start_btn.setEnabled(True)
            self.ct_stop_btn.setEnabled(False)
            self._test_threads.clear()
            self._test_workers.clear()

    def _ct_stop_test(self):
        logger.debug("CT stop_test called")
        for worker in self._test_workers.values():
            worker.stop()
        self.is_testing = False
        self.ct_start_btn.setEnabled(True)
        self.ct_stop_btn.setEnabled(False)

    def _ct_save_datalog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DataLog", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            logger.info("Saving datalog to: %s", file_path)
