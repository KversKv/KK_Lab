#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test UI组件
用于对DUT进行固件下载和功耗测试
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ui.widgets.dark_combobox import DarkComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QGridLayout, QFrame, QApplication, QFileDialog,
    QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont
import pyvisa

from instruments.power.keysight.n6705c import N6705C


class _ConsumptionTestWorker(QObject):
    channel_result = Signal(int, float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, n6705c, channels, test_time, sample_period):
        super().__init__()
        self.n6705c = n6705c
        self.channels = channels
        self.test_time = test_time
        self.sample_period = sample_period
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            if self._is_stopped:
                self.finished.emit()
                return
            result = self.n6705c.fetch_current_by_datalog(
                self.channels, self.test_time, self.sample_period
            )
            for ch, avg_current in result.items():
                if self._is_stopped:
                    break
                self.channel_result.emit(ch, float(avg_current))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


class _SearchN6705CWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        rm = None
        try:
            rm = pyvisa.ResourceManager()
            resources = list(rm.list_resources()) or []
            n6705c_devices = []
            for dev in resources:
                try:
                    instr = rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception:
                    pass
            self.finished.emit(n6705c_devices)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass


class ConsumptionTestUI(QWidget):
    connection_status_changed = Signal(bool)

    CHANNEL_COLORS = {
        1: {"accent": "#d4a514", "bg": "#1a1708", "border": "#3d2e08"},
        2: {"accent": "#18b67a", "bg": "#081a14", "border": "#0a3d28"},
        3: {"accent": "#2f6fed", "bg": "#081028", "border": "#0c2a5e"},
        4: {"accent": "#d14b72", "bg": "#1a080e", "border": "#3d0c22"},
    }

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.firmware_path = ""
        self.config_path = ""
        self.is_testing = False

        self._search_thread = None
        self._search_worker = None
        self._test_thread = None
        self._test_worker = None

        self._setup_style()
        self._create_layout()
        self._sync_from_top()

    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setObjectName("ConsumptionTestRoot")
        _cb_icons = self._get_checkmark_path("5d45ff")
        self.setStyleSheet("""
        QWidget#ConsumptionTestRoot {
            background-color: #050b1a;
        }

        QWidget {
            background-color: #050b1a;
            color: #d8e3ff;
        }

        QLabel {
            color: #c8d6f0;
            background: transparent;
            border: none;
        }

        QLineEdit, QComboBox {
            background-color: #020816;
            border: 1px solid #1c2f54;
            border-radius: 6px;
            padding: 6px 10px;
            color: #d7e3ff;
            min-height: 32px;
        }

        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #5b7cff;
        }

        QComboBox::drop-down {
            border: none;
            width: 22px;
        }

        QComboBox QAbstractItemView {
            background-color: #020816;
            color: #d7e3ff;
            border: 1px solid #1c2f54;
            selection-background-color: #1a3260;
            outline: 0px;
        }

        QComboBox QAbstractItemView::item {
            background-color: #020816;
            color: #d7e3ff;
            padding: 4px 8px;
        }

        QComboBox QAbstractItemView::item:hover {
            background-color: #1a3260;
        }

        QComboBox QFrame {
            background-color: #020816;
            border: 1px solid #1c2f54;
        }

        QPushButton {
            background-color: #162544;
            border: 1px solid #25355c;
            border-radius: 8px;
            padding: 6px 14px;
            color: #dbe7ff;
            min-height: 32px;
        }

        QPushButton:hover {
            background-color: #1c315b;
        }

        QPushButton:pressed {
            background-color: #10203d;
        }

        QPushButton:disabled {
            background-color: #0f1930;
            color: #5a6b8e;
            border: 1px solid #1b2847;
        }

        QCheckBox {
            color: #d8e3ff;
            spacing: 6px;
            background: transparent;
        }

        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            image: url("__UNCHECKED__");
        }

        QCheckBox::indicator:checked {
            image: url("__CHECKED__");
        }
        """.replace("__UNCHECKED__", _cb_icons['unchecked']).replace("__CHECKED__", _cb_icons['checked']))

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 16)
        main_layout.setSpacing(16)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        title_label = QLabel("⚡ Consumption Test")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 800;
                color: #ffffff;
            }
        """)
        subtitle_label = QLabel("Measure average current consumption and manage DUT firmware/configuration.")
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #7e96bf;
            }
        """)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        main_layout.addWidget(self._create_connection_panel())
        main_layout.addWidget(self._create_firmware_config_panel())
        main_layout.addWidget(self._create_consumption_test_panel(), 1)

    def _create_connection_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 16px; color: #00f5c4;")
        title = QLabel("N6705C Connection")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        resource_label = QLabel("Resource")
        resource_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        layout.addWidget(resource_label)

        resource_row = QHBoxLayout()
        resource_row.setSpacing(8)

        self.device_combo = DarkComboBox(bg="#020816", border="#1c2f54")
        self.device_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.device_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")

        self.search_btn = QPushButton("🔍")
        self.search_btn.setFixedWidth(38)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-size: 14px;
                min-height: 32px;
            }
            QPushButton:hover { background-color: #1c315b; }
        """)

        self.instrument_status = QLabel("N6705C DC Power Analyzer")
        self.instrument_status.setStyleSheet("color: #7e96bf; font-size: 12px; font-weight: 600;")

        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("color: #ff5a7a; font-size: 11px;")

        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.setFixedWidth(100)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 211, 154, 0.14);
                color: #00d39a;
                border: 1px solid rgba(0, 211, 154, 0.25);
                border-radius: 8px;
                font-weight: 600;
                min-height: 34px;
            }
            QPushButton:hover {
                background-color: rgba(0, 211, 154, 0.22);
            }
        """)

        resource_row.addWidget(self.device_combo, 1)
        resource_row.addWidget(self.search_btn)

        status_block = QVBoxLayout()
        status_block.setSpacing(2)
        status_block.addWidget(self.instrument_status)
        status_block.addWidget(self.connection_status_label)

        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #071126;
                border: 1px solid #152240;
                border-radius: 8px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.addLayout(status_block, 1)
        info_layout.addWidget(self.connect_btn)

        layout.addLayout(resource_row)
        layout.addWidget(info_frame)

        self.search_btn.clicked.connect(self._search_devices)
        self.connect_btn.clicked.connect(self._toggle_connection)

        return panel

    def _create_firmware_config_panel(self):
        outer = QFrame()
        outer.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(12)

        fw_panel = QFrame()
        fw_panel.setStyleSheet("""
            QFrame {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        fw_layout = QVBoxLayout(fw_panel)
        fw_layout.setContentsMargins(16, 14, 16, 14)
        fw_layout.setSpacing(8)

        fw_title = QLabel("📁 Firmware Download (BIN/HEX)")
        fw_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        fw_layout.addWidget(fw_title)

        fw_file_label = QLabel("Select Firmware File")
        fw_file_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        fw_layout.addWidget(fw_file_label)

        fw_file_row = QHBoxLayout()
        fw_file_row.setSpacing(6)
        self.firmware_file_input = QLineEdit("No file selected...")
        self.firmware_file_input.setReadOnly(True)
        self.firmware_browse_btn = QPushButton("Browse")
        self.firmware_browse_btn.setFixedWidth(72)
        self.firmware_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d45ff;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                min-height: 32px;
            }
            QPushButton:hover { background-color: #6d55ff; }
        """)
        fw_file_row.addWidget(self.firmware_file_input, 1)
        fw_file_row.addWidget(self.firmware_browse_btn)
        fw_layout.addLayout(fw_file_row)

        self.download_btn = QPushButton("⬇ Download to DUT")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 8px;
                font-weight: 600;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #1c315b; }
        """)
        fw_layout.addWidget(self.download_btn)

        config_panel = QFrame()
        config_panel.setStyleSheet("""
            QFrame {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        config_layout = QVBoxLayout(config_panel)
        config_layout.setContentsMargins(16, 14, 16, 14)
        config_layout.setSpacing(8)

        config_title = QLabel("📁 Configuration Import (YAML)")
        config_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        config_layout.addWidget(config_title)

        config_file_label = QLabel("Select Config File")
        config_file_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        config_layout.addWidget(config_file_label)

        config_file_row = QHBoxLayout()
        config_file_row.setSpacing(6)
        self.config_file_input = QLineEdit("No file selected...")
        self.config_file_input.setReadOnly(True)
        self.config_browse_btn = QPushButton("Browse")
        self.config_browse_btn.setFixedWidth(72)
        self.config_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d45ff;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                min-height: 32px;
            }
            QPushButton:hover { background-color: #6d55ff; }
        """)
        config_file_row.addWidget(self.config_file_input, 1)
        config_file_row.addWidget(self.config_browse_btn)
        config_layout.addLayout(config_file_row)

        self.import_config_btn = QPushButton("⬇ Import Configuration")
        self.import_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 8px;
                font-weight: 600;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #1c315b; }
        """)
        config_layout.addWidget(self.import_config_btn)

        outer_layout.addWidget(fw_panel, 1)
        outer_layout.addWidget(config_panel, 1)

        self.firmware_browse_btn.clicked.connect(self._browse_firmware)
        self.config_browse_btn.clicked.connect(self._browse_config)
        self.download_btn.clicked.connect(self._download_to_dut)
        self.import_config_btn.clicked.connect(self._import_configuration)

        return outer

    def _create_consumption_test_panel(self):
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 16px; color: #f2c94c;")
        title = QLabel("Current Consumption Test")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        header_row.addWidget(icon)
        header_row.addWidget(title)
        header_row.addStretch()

        self.save_datalog_btn = QPushButton("💾 Save DataLog")
        self.save_datalog_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-size: 11px;
                padding: 4px 10px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #1c315b; }
        """)
        header_row.addWidget(self.save_datalog_btn)
        layout.addLayout(header_row)

        params_row = QHBoxLayout()
        params_row.setSpacing(12)

        time_label = QLabel("Test Time (s)")
        time_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.test_time_input = QLineEdit("10")
        self.test_time_input.setFixedWidth(80)
        self.test_time_input.setAlignment(Qt.AlignCenter)

        period_label = QLabel("Sample Period (s)")
        period_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.sample_period_input = QLineEdit("0.001")
        self.sample_period_input.setFixedWidth(80)
        self.sample_period_input.setAlignment(Qt.AlignCenter)

        params_row.addWidget(time_label)
        params_row.addWidget(self.test_time_input)
        params_row.addSpacing(8)
        params_row.addWidget(period_label)
        params_row.addWidget(self.sample_period_input)
        params_row.addStretch()
        layout.addLayout(params_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.start_test_btn = QPushButton("▶ START TEST")
        self.start_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_test_btn.setStyleSheet("""
            QPushButton {
                background-color: #0d6b4f;
                color: #ffffff;
                border: 1px solid #18a87a;
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                min-height: 40px;
            }
            QPushButton:hover { background-color: #0f7d5c; }
            QPushButton:disabled {
                background-color: #0f1930;
                color: #5a6b8e;
                border: 1px solid #1b2847;
            }
        """)

        self.stop_test_btn = QPushButton("🟥 STOP")
        self.stop_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 90, 122, 0.12);
                color: #ff7593;
                border: 1px solid rgba(255, 90, 122, 0.28);
                border-radius: 8px;
                font-weight: 700;
                font-size: 13px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: rgba(255, 90, 122, 0.20);
            }
            QPushButton:disabled {
                background-color: #0f1930;
                color: #5a6b8e;
                border: 1px solid #1b2847;
            }
        """)

        btn_row.addWidget(self.start_test_btn, 1)
        btn_row.addWidget(self.stop_test_btn, 1)
        layout.addLayout(btn_row)

        channels_row = QHBoxLayout()
        channels_row.setSpacing(10)

        self.channel_cards = {}
        for ch in range(1, 5):
            card = self._create_channel_card(ch)
            channels_row.addWidget(card, 1)

        layout.addLayout(channels_row, 1)

        self.start_test_btn.clicked.connect(self._start_test)
        self.stop_test_btn.clicked.connect(self._stop_test)
        self.save_datalog_btn.clicked.connect(self._save_datalog)

        return panel

    def _get_checkmark_path(self, accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

    def _create_channel_card(self, ch_num):
        colors = self.CHANNEL_COLORS[ch_num]

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {colors['bg']};
                border: 1px solid {colors['border']};
                border-radius: 10px;
            }}
        """)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        checkbox = QCheckBox(f"CH {ch_num}")
        checkbox.setChecked(False)
        icons = self._get_checkmark_path(colors['accent'])
        checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                image: url("{icons['unchecked']}");
            }}
            QCheckBox::indicator:checked {{
                image: url("{icons['checked']}");
            }}
        """)

        top_row.addWidget(checkbox)
        top_row.addStretch()
        layout.addLayout(top_row)

        layout.addStretch()

        avg_label = QLabel("AVG CURRENT")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setStyleSheet("color: #7e96bf; font-size: 11px; font-weight: 600;")
        layout.addWidget(avg_label)

        value_label = QLabel("- - -")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['accent']};
                font-size: 18px;
                font-weight: 700;
                letter-spacing: 4px;
            }}
        """)
        layout.addWidget(value_label)

        layout.addStretch()

        self.channel_cards[ch_num] = {
            "card": card,
            "checkbox": checkbox,
            "value_label": value_label,
        }

        return card

    def _set_status(self, text, status_type="err"):
        if status_type == "ok":
            self.connection_status_label.setStyleSheet("color: #00d39a; font-size: 11px; font-weight: 600;")
        elif status_type == "warn":
            self.connection_status_label.setStyleSheet("color: #ffb84d; font-size: 11px; font-weight: 600;")
        else:
            self.connection_status_label.setStyleSheet("color: #ff5a7a; font-size: 11px; font-weight: 600;")
        self.connection_status_label.setText(text)

    def _search_devices(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        self._set_status("Searching...", "warn")
        self.search_btn.setEnabled(False)

        worker = _SearchN6705CWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_search_done)
        worker.error.connect(self._on_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._search_thread = thread
        self._search_worker = worker
        thread.start()

    def _on_search_done(self, devices):
        default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
        self.device_combo.clear()
        if devices:
            for dev in devices:
                self.device_combo.addItem(dev)
            if default_device not in devices:
                self.device_combo.addItem(default_device)
            self._set_status("Device Available", "ok")
        else:
            self.device_combo.addItem(default_device)
            self._set_status("Using Default Resource", "warn")
        self.search_btn.setEnabled(True)

    def _on_search_error(self, err):
        print(f"Search error: {err}")
        self._set_status(f"Search Error: {err}", "err")
        self.search_btn.setEnabled(True)

    def _toggle_connection(self):
        if self.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        self._set_status("Connecting...", "warn")
        self.connect_btn.setEnabled(False)
        try:
            device_address = self.device_combo.currentText()
            self.n6705c = N6705C(device_address)
            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self.is_connected = True
                self._set_status("Connected", "ok")
                self.instrument_status.setText(f"N6705C DC Power Analyzer")
                self.instrument_status.setStyleSheet("color: #00d39a; font-size: 12px; font-weight: 600;")
                self.connect_btn.setText("Disconnect")
                self.connect_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 90, 122, 0.14);
                        color: #ff6f8e;
                        border: 1px solid rgba(255, 90, 122, 0.25);
                        border-radius: 8px;
                        font-weight: 600;
                        min-height: 34px;
                    }
                    QPushButton:hover { background-color: rgba(255, 90, 122, 0.22); }
                """)
                self.connect_btn.setEnabled(True)

                if self._n6705c_top:
                    self._n6705c_top.connect_a(device_address, self.n6705c)

                self.connection_status_changed.emit(True)
            else:
                self._set_status("Device Mismatch", "err")
                self.connect_btn.setEnabled(True)
        except Exception as e:
            print(f"Connect error: {e}")
            self._set_status(f"Error: {e}", "err")
            self.connect_btn.setEnabled(True)

    def _disconnect(self):
        self._set_status("Disconnecting...", "warn")
        self.connect_btn.setEnabled(False)
        try:
            if self._n6705c_top:
                self._n6705c_top.disconnect_a()
                self.n6705c = None
            else:
                if self.n6705c:
                    if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                        self.n6705c.instr.close()
                    if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                        self.n6705c.rm.close()
                    self.n6705c = None

            self.is_connected = False
            self._set_status("Disconnected", "err")
            self.instrument_status.setText("N6705C DC Power Analyzer")
            self.instrument_status.setStyleSheet("color: #7e96bf; font-size: 12px; font-weight: 600;")
            self.connect_btn.setText("🔌 Connect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 211, 154, 0.14);
                    color: #00d39a;
                    border: 1px solid rgba(0, 211, 154, 0.25);
                    border-radius: 8px;
                    font-weight: 600;
                    min-height: 34px;
                }
                QPushButton:hover { background-color: rgba(0, 211, 154, 0.22); }
            """)
            self.connect_btn.setEnabled(True)
            self.connection_status_changed.emit(False)
        except Exception as e:
            print(f"Disconnect error: {e}")
            self._set_status(f"Error: {e}", "err")
            self.connect_btn.setEnabled(True)

    def _sync_from_top(self):
        if not self._n6705c_top:
            return
        if self._n6705c_top.is_connected_a and self._n6705c_top.n6705c_a:
            self.n6705c = self._n6705c_top.n6705c_a
            self.is_connected = True
            self._set_status("Connected", "ok")
            self.instrument_status.setText("N6705C DC Power Analyzer")
            self.instrument_status.setStyleSheet("color: #00d39a; font-size: 12px; font-weight: 600;")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 90, 122, 0.14);
                    color: #ff6f8e;
                    border: 1px solid rgba(255, 90, 122, 0.25);
                    border-radius: 8px;
                    font-weight: 600;
                    min-height: 34px;
                }
                QPushButton:hover { background-color: rgba(255, 90, 122, 0.22); }
            """)
            self.connect_btn.setEnabled(True)
            self.search_btn.setEnabled(False)
            if self._n6705c_top.visa_resource_a:
                self.device_combo.clear()
                self.device_combo.addItem(self._n6705c_top.visa_resource_a)
        elif not self.is_connected:
            self._set_status("Disconnected", "err")
            self.connect_btn.setText("🔌 Connect")
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(0, 211, 154, 0.14);
                    color: #00d39a;
                    border: 1px solid rgba(0, 211, 154, 0.25);
                    border-radius: 8px;
                    font-weight: 600;
                    min-height: 34px;
                }
                QPushButton:hover { background-color: rgba(0, 211, 154, 0.22); }
            """)

    def _browse_firmware(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware File", "",
            "Firmware Files (*.bin *.hex);;All Files (*)"
        )
        if file_path:
            self.firmware_path = file_path
            self.firmware_file_input.setText(os.path.basename(file_path))

    def _browse_config(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Config File", "",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        if file_path:
            self.config_path = file_path
            self.config_file_input.setText(os.path.basename(file_path))

    def _download_to_dut(self):
        if not self.firmware_path:
            print("No firmware file selected")
            return
        print(f"Downloading firmware to DUT: {self.firmware_path}")

    def _import_configuration(self):
        if not self.config_path:
            print("No config file selected")
            return
        print(f"Importing configuration: {self.config_path}")

    def _start_test(self):
        if self.is_testing:
            return
        if not self.is_connected or not self.n6705c:
            self._set_status("Please connect N6705C first", "err")
            return

        selected_channels = [
            ch for ch in range(1, 5)
            if self.channel_cards[ch]["checkbox"].isChecked()
        ]
        if not selected_channels:
            self._set_status("No channel selected", "warn")
            return

        try:
            test_time = float(self.test_time_input.text())
            sample_period = float(self.sample_period_input.text())
        except ValueError:
            self._set_status("Invalid test time or sample period", "err")
            return

        self.is_testing = True
        self.start_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)

        for ch in range(1, 5):
            self.channel_cards[ch]["value_label"].setText("- - -")

        worker = _ConsumptionTestWorker(
            self.n6705c, selected_channels, test_time, sample_period
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.channel_result.connect(self._on_channel_result)
        worker.error.connect(self._on_test_error)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        thread.start()

    def _on_channel_result(self, channel, avg_current):
        self.update_channel_current(channel, avg_current)

    def _on_test_error(self, err_msg):
        self._set_status(err_msg, "err")

    def _on_test_finished(self):
        self.is_testing = False
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)

    def _on_test_thread_cleaned(self):
        self._test_worker = None
        self._test_thread = None

    def _stop_test(self):
        if self._test_worker:
            self._test_worker.stop()
        self.is_testing = False
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)

    def _save_datalog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DataLog", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            print(f"Saving datalog to: {file_path}")

    @staticmethod
    def _format_current(current_A):
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.3f} A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.3f} mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.3f} µA"
        elif abs_i >= 1e-9:
            return f"{current_A*1e9:.3f} nA"
        else:
            return f"{current_A:.3e} A"

    def update_channel_current(self, channel_num, avg_current):
        if channel_num in self.channel_cards:
            label = self.channel_cards[channel_num]["value_label"]
            if avg_current is not None:
                label.setText(self._format_current(avg_current))
            else:
                label.setText("- - -")

    def get_selected_channels(self):
        return [
            ch for ch in range(1, 5)
            if self.channel_cards[ch]["checkbox"].isChecked()
        ]

    def set_system_status(self, status, is_error=False):
        pass

    def update_instrument_info(self, instrument_info):
        pass

    def get_test_config(self):
        return {
            'n6705c_connected': self.is_connected,
            'firmware_path': self.firmware_path,
            'config_path': self.config_path,
            'selected_channels': self.get_selected_channels(),
        }

    def update_test_result(self, result):
        if isinstance(result, dict):
            for ch in range(1, 5):
                key = f"ch{ch}_avg_current"
                if key in result:
                    self.update_channel_current(ch, result[key])

    def clear_results(self):
        for ch in range(1, 5):
            self.channel_cards[ch]["value_label"].setText("- - -")

    def get_test_mode(self):
        return "Consumption Test"

    def set_test_mode(self, mode):
        pass

    def get_test_id(self):
        return "CONSUMPTION_TEST_001"

    def set_test_id(self, test_id):
        pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = ConsumptionTestUI()
    win.setWindowTitle("Consumption Test")
    win.setGeometry(100, 100, 1200, 820)
    win.show()

    sys.exit(app.exec())
