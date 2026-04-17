#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test UI组件
用于对DUT进行固件下载和功耗测试
"""

import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from ui.styles.n6705c_module_frame import N6705CConnectionMixin, build_n6705c_inline_row
from ui.styles.serialCom_module_frame import SerialComMixin, MODE_INLINE
from ui.styles.execution_logs_module_frame import ExecutionLogsFrame
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QPlainTextEdit,
    QFrame, QApplication, QFileDialog,
    QCheckBox, QSizePolicy, QMessageBox, QScrollArea
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QThread, QObject, QSize,
    QRectF, QRect, QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QColor, QPen,
    QFontMetrics
)
from PySide6.QtSvg import QSvgRenderer

from lib.download_tools.download_script import download_bin, DownloadMode, DownloadState, DownloadResult, detect_chip_from_bin
from chips.bes_chip_configs.bes_chip_configs import SUPPORTED_CHIPS, get_chip_config
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.progress_button import ProgressButton
from log_config import get_logger

logger = get_logger(__name__)

_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "resources", "icons"
)


def _tinted_svg_icon(svg_path, color, size=18):
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)


class DownloadModeToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._value = "FLASH"
        self._anim_progress = 0.0

        self._bg_color = QColor("#1A2750")
        self._knob_color = QColor("#243760")
        self._text_active = QColor("#F3F6FF")
        self._text_inactive = QColor("#5F77AE")
        self._border_color = QColor("#22376A")

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.setCursor(Qt.PointingHandCursor)

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def value(self):
        return self._value

    def setValue(self, val):
        val = val.upper()
        if val not in ("FLASH", "RAMRUN"):
            return
        if val == self._value:
            return
        self._value = val
        target = 0.0 if val == "FLASH" else 1.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled.emit(self._value)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = "RAMRUN" if self._value == "FLASH" else "FLASH"
            self.setValue(new_val)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2

        p.setPen(QPen(self._border_color, 1))
        p.setBrush(self._bg_color)
        p.drawRoundedRect(QRect(0, 0, w, h), radius, radius)

        knob_margin = 3
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_y = knob_margin

        p.setPen(Qt.NoPen)
        p.setBrush(self._knob_color)
        p.drawRoundedRect(QRect(int(knob_x), int(knob_y), int(knob_w), int(knob_h)),
                          knob_h / 2, knob_h / 2)

        font = p.font()
        font.setWeight(QFont.Bold)
        font.setPointSize(9)
        p.setFont(font)

        left_rect = QRect(0, 0, w // 2, h)
        right_rect = QRect(w // 2, 0, w // 2, h)

        p.setPen(self._text_active if self._anim_progress < 0.5 else self._text_inactive)
        p.drawText(left_rect, Qt.AlignCenter, "Flash")

        p.setPen(self._text_active if self._anim_progress >= 0.5 else self._text_inactive)
        p.drawText(right_rect, Qt.AlignCenter, "RAMRUN")

        p.end()

    def sizeHint(self):
        return QSize(160, 32)


class _DownloadWorker(QObject):
    state_changed = Signal(str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, com_port, bin_file, mode, timeout=120):
        super().__init__()
        self.com_port = com_port
        self.bin_file = bin_file
        self.mode = mode
        self.timeout = timeout

    def run(self):
        try:
            def _on_state(state: DownloadState):
                self.state_changed.emit(state.value)

            result = download_bin(
                com_port=self.com_port,
                bin_file=self.bin_file,
                mode=self.mode,
                timeout=self.timeout,
                on_state_change=_on_state,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _ChipCheckWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def run(self):
        try:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            i2c = I2CInterface()
            if not i2c.initialize():
                self.error.emit("I2C interface initialization failed.")
                return
            chip_info = i2c.bes_chip_check()
            self.finished.emit(chip_info)
        except Exception as e:
            self.error.emit(str(e))


class _ConsumptionTestWorker(QObject):
    channel_result = Signal(str, int, float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, device_channel_map, test_time, sample_period):
        super().__init__()
        self.device_channel_map = device_channel_map
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
            for device_label, (n6705c_inst, hw_channels) in self.device_channel_map.items():
                if self._is_stopped:
                    break
                result = n6705c_inst.fetch_current_by_datalog(
                    hw_channels, self.test_time, self.sample_period
                )
                for ch, avg_current in result.items():
                    if self._is_stopped:
                        break
                    self.channel_result.emit(device_label, ch, float(avg_current))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


class ConsumptionTestUI(QWidget, N6705CConnectionMixin, SerialComMixin):
    connection_status_changed = Signal(bool)
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    CHANNEL_COLORS_LIST = [
        {"accent": "#d4a514", "bg": "#1a1708", "border": "#3d2e08"},
        {"accent": "#18b67a", "bg": "#081a14", "border": "#0a3d28"},
        {"accent": "#2f6fed", "bg": "#081028", "border": "#0c2a5e"},
        {"accent": "#d14b72", "bg": "#1a080e", "border": "#3d0c22"},
        {"accent": "#a855f7", "bg": "#150a20", "border": "#3a1a5e"},
        {"accent": "#06b6d4", "bg": "#081a1e", "border": "#0a3d4a"},
        {"accent": "#f97316", "bg": "#1a1008", "border": "#3d2808"},
        {"accent": "#ec4899", "bg": "#1a0812", "border": "#3d0c28"},
    ]

    SINGLE_DEVICE_CHANNEL_CONFIGS = [
        {"name": "Vbat", "channel": "A-CH1", "enabled": True},
        {"name": "Vcore", "channel": "A-CH2", "enabled": True},
        {"name": "VANA", "channel": "A-CH3", "enabled": True},
        {"name": "VHPPA", "channel": "A-CH4", "enabled": True},
    ]

    DUAL_DEVICE_CHANNEL_CONFIGS = [
        {"name": "Vbat", "channel": "A-CH1", "enabled": True},
        {"name": "VcoreM", "channel": "A-CH2", "enabled": True},
        {"name": "VcoreL", "channel": "A-CH3", "enabled": True},
        {"name": "VANA", "channel": "A-CH4", "enabled": True},
        {"name": "VHPPA", "channel": "B-CH1", "enabled": True},
        {"name": "CH6", "channel": "B-CH2", "enabled": False},
        {"name": "CH7", "channel": "B-CH3", "enabled": False},
        {"name": "CH8", "channel": "B-CH4", "enabled": False},
    ]

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self.n6705c_a = None
        self.n6705c_b = None
        self.is_connected_a = False
        self.is_connected_b = False

        self.init_n6705c_connection(n6705c_top)
        self.init_serial_connection(mode=MODE_INLINE, prefix="DUT Serial")

        self.firmware_path = ""
        self.config_content = ""
        self.selected_chip_config = None
        self.is_testing = False

        self._test_thread = None
        self._test_worker = None
        self._download_thread = None
        self._download_worker = None
        self._chip_check_thread = None
        self._chip_check_worker = None

        self._channel_configs = []
        self._channel_config_widgets = []
        self._syncing = False

        self._setup_style()
        self._create_layout()
        self._sync_n6705c_dual_from_top()

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

        QFrame#logContainer {
            background-color: #09142e;
            border: 1px solid #1a2d57;
            border-radius: 16px;
        }

        QLineEdit {
            background-color: #020816;
            border: 1px solid #1c2f54;
            border-radius: 6px;
            padding: 6px 10px;
            color: #d7e3ff;
            min-height: 32px;
        }

        QLineEdit:focus {
            border: 1px solid #5b7cff;
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

        self.execution_logs = ExecutionLogsFrame(show_progress=False)
        self.log_edit = self.execution_logs.log_edit
        self.clear_log_btn = self.execution_logs.clear_log_btn
        main_layout.addWidget(self.execution_logs)

    def _create_connection_panel(self):
        panel = QFrame()
        panel.setObjectName("connectionPanel")
        panel.setStyleSheet("""
            QFrame#connectionPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

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

        self._n6705c_conn_widgets = {}
        for label in ("A", "B"):
            row, widgets = build_n6705c_inline_row(label, parent=panel)
            layout.addLayout(row)
            self._n6705c_conn_widgets[label] = widgets
            widgets["search_btn"].clicked.connect(lambda checked=False, lbl=label: self._on_device_search(lbl))
            widgets["connect_btn"].clicked.connect(lambda checked=False, lbl=label: self._on_device_connect_or_disconnect(lbl))

        return panel

    def _on_device_search(self, label):
        top = self._n6705c_top
        if top:
            is_conn = getattr(top, f"is_connected_{label.lower()}", False)
            if is_conn:
                return

        from debug_config import DEBUG_MOCK
        w = self._n6705c_conn_widgets[label]
        if DEBUG_MOCK:
            w["combo"].clear()
            w["combo"].addItem(f"DEBUG::MOCK::N6705C::{label}")
            w["status"].setText("● Mock device ready")
            self.append_log(f"[DEBUG] Mock device {label} loaded, skip real VISA scan.")
            return

        w["status"].setText("● Searching")
        w["search_btn"].setEnabled(False)
        w["connect_btn"].setEnabled(False)
        self.append_log(f"[SYSTEM] Scanning VISA resources for N6705C-{label}...")

        from ui.styles.n6705c_module_frame import _SearchN6705CWorker
        worker = _SearchN6705CWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda devs, lbl=label: self._on_device_search_done(lbl, devs))
        worker.error.connect(lambda err, lbl=label: self._on_device_search_error(lbl, err))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        setattr(self, f"_search_thread_{label}", thread)
        setattr(self, f"_search_worker_{label}", worker)
        thread.start()

    def _on_device_search_done(self, label, devices):
        w = self._n6705c_conn_widgets[label]
        w["combo"].setEnabled(True)
        w["combo"].clear()
        if devices:
            for dev in devices:
                w["combo"].addItem(dev)
            w["status"].setText(f"● Found {len(devices)} device(s)")
            self.append_log(f"[SYSTEM] Found {len(devices)} N6705C device(s) for slot {label}.")
        else:
            w["combo"].addItem("No N6705C device found")
            w["combo"].setEnabled(False)
            w["status"].setText("● No device found")
        w["search_btn"].setEnabled(True)
        w["connect_btn"].setEnabled(True)

    def _on_device_search_error(self, label, err):
        w = self._n6705c_conn_widgets[label]
        w["status"].setText("● Search failed")
        self.append_log(f"[ERROR] Search failed for N6705C-{label}: {err}")
        w["search_btn"].setEnabled(True)
        w["connect_btn"].setEnabled(True)

    def _on_device_connect_or_disconnect(self, label):
        attr = label.lower()
        is_conn = getattr(self, f"is_connected_{attr}", False)
        if is_conn:
            self._disconnect_device(label)
        else:
            self._connect_device(label)

    def _connect_device(self, label):
        attr = label.lower()
        w = self._n6705c_conn_widgets[label]
        from debug_config import DEBUG_MOCK
        from ui.styles.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()

        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C
            inst = MockN6705C()
            setattr(self, f"n6705c_{attr}", inst)
            setattr(self, f"is_connected_{attr}", True)
            _update_n6705c_btn_state(w["connect_btn"], connected=True)
            w["search_btn"].setEnabled(False)
            w["status"].setText(f"● Connected: Mock-{label}")
            self.append_log(f"[DEBUG] Mock N6705C-{label} connected.")
            visa = w["combo"].currentText()
            self._syncing = True
            try:
                if self._n6705c_top:
                    getattr(self._n6705c_top, f"connect_{attr}")(visa, inst, f"MOCK-{label}")
            finally:
                self._syncing = False
            new_count = self._connected_device_count()
            self._apply_preset_channels(prev_count, new_count)
            self._update_available_channels()
            return

        w["status"].setText("● Connecting")
        w["connect_btn"].setEnabled(False)
        self.append_log(f"[SYSTEM] Connecting N6705C-{label}...")

        try:
            from instruments.power.keysight.n6705c import N6705C
            visa = w["combo"].currentText()
            inst = N6705C(visa)
            idn = inst.instr.query("*IDN?")
            if "N6705C" in idn:
                setattr(self, f"n6705c_{attr}", inst)
                setattr(self, f"is_connected_{attr}", True)
                _update_n6705c_btn_state(w["connect_btn"], connected=True)
                w["search_btn"].setEnabled(False)
                pretty = visa
                try:
                    pretty = visa.split("::")[1]
                except Exception:
                    pass
                w["status"].setText(f"● Connected: {pretty}")
                self.append_log(f"[SYSTEM] N6705C-{label} connected. IDN: {idn.strip()}")
                self._syncing = True
                try:
                    if self._n6705c_top:
                        serial = ""
                        try:
                            serial = idn.strip().split(",")[2].strip()
                        except Exception:
                            pass
                        getattr(self._n6705c_top, f"connect_{attr}")(visa, inst, serial)
                finally:
                    self._syncing = False
                new_count = self._connected_device_count()
                self._apply_preset_channels(prev_count, new_count)
                self._update_available_channels()
            else:
                w["status"].setText("● Device mismatch")
                self.append_log(f"[ERROR] Connected device on {label} is not N6705C.")
        except Exception as e:
            w["status"].setText("● Connection failed")
            self.append_log(f"[ERROR] Connection failed for N6705C-{label}: {e}")
        finally:
            w["connect_btn"].setEnabled(True)

    def _disconnect_device(self, label):
        attr = label.lower()
        w = self._n6705c_conn_widgets[label]
        from ui.styles.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()

        try:
            self._syncing = True
            try:
                if self._n6705c_top:
                    getattr(self._n6705c_top, f"disconnect_{attr}")()
                else:
                    inst = getattr(self, f"n6705c_{attr}", None)
                    if inst:
                        if hasattr(inst, 'disconnect'):
                            inst.disconnect()
                        else:
                            if hasattr(inst, 'instr') and inst.instr:
                                inst.instr.close()
                            if hasattr(inst, 'rm') and inst.rm:
                                inst.rm.close()
            finally:
                self._syncing = False
            setattr(self, f"n6705c_{attr}", None)
            setattr(self, f"is_connected_{attr}", False)
            _update_n6705c_btn_state(w["connect_btn"], connected=False)
            w["search_btn"].setEnabled(True)
            w["combo"].setEnabled(True)
            w["status"].setText("● Ready")
            self.append_log(f"[SYSTEM] N6705C-{label} disconnected.")
            new_count = self._connected_device_count()
            self._apply_preset_channels(prev_count, new_count)
            self._update_available_channels()
        except Exception as e:
            w["status"].setText("● Disconnect failed")
            self.append_log(f"[ERROR] Disconnect failed for N6705C-{label}: {e}")

    def _sync_n6705c_dual_from_top(self):
        top = self._n6705c_top
        if not top:
            self._update_test_panel_state()
            return
        from ui.styles.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()
        for label, attr in [("A", "a"), ("B", "b")]:
            n6705c = getattr(top, f"n6705c_{attr}", None)
            is_conn = getattr(top, f"is_connected_{attr}", False)
            visa_res = getattr(top, f"visa_resource_{attr}", "")
            if label not in self._n6705c_conn_widgets:
                continue
            w = self._n6705c_conn_widgets[label]
            if is_conn and n6705c:
                setattr(self, f"n6705c_{attr}", n6705c)
                setattr(self, f"is_connected_{attr}", True)
                _update_n6705c_btn_state(w["connect_btn"], connected=True)
                w["search_btn"].setEnabled(False)
                if visa_res:
                    w["combo"].clear()
                    w["combo"].addItem(visa_res)
                pretty = visa_res
                try:
                    pretty = visa_res.split("::")[1]
                except Exception:
                    pass
                w["status"].setText(f"● Connected: {pretty}")
            else:
                setattr(self, f"n6705c_{attr}", None)
                setattr(self, f"is_connected_{attr}", False)
                _update_n6705c_btn_state(w["connect_btn"], connected=False)
                w["search_btn"].setEnabled(True)
                w["combo"].setEnabled(True)
                w["status"].setText("● Ready")
        self.n6705c = self.n6705c_a
        self.is_connected = self.is_connected_a
        new_count = self._connected_device_count()
        self._apply_preset_channels(prev_count, new_count)
        self._update_available_channels()

    def sync_n6705c_from_top(self):
        if self._syncing:
            return
        self._sync_n6705c_dual_from_top()

    def set_system_status(self, status, is_error=False):
        pass

    def _get_available_channel_options(self):
        options = []
        for label, attr in [("A", "a"), ("B", "b")]:
            is_conn = getattr(self, f"is_connected_{attr}", False)
            status = "Online" if is_conn else "Offline"
            for ch in range(1, 5):
                options.append(f"{label}-CH{ch} ({status})")
        return options

    def _connected_device_count(self):
        count = 0
        if self.is_connected_a:
            count += 1
        if self.is_connected_b:
            count += 1
        return count

    def _update_available_channels(self):
        options = self._get_available_channel_options()
        for wdata in self._channel_config_widgets:
            combo = wdata["channel_combo"]
            current_text = combo.currentText()
            current_key = current_text.split(" (")[0] if " (" in current_text else current_text
            combo.blockSignals(True)
            combo.clear()
            for opt in options:
                combo.addItem(opt)
            for i in range(combo.count()):
                if combo.itemText(i).startswith(current_key + " "):
                    combo.setCurrentIndex(i)
                    break
            combo.blockSignals(False)
        self._refresh_result_cards()
        self._update_test_panel_state()

    def _apply_preset_channels(self, prev_count, new_count):
        if prev_count == new_count:
            return

        if new_count == 0:
            self._clear_all_channel_configs()
        elif new_count == 1:
            self._clear_all_channel_configs()
            for cfg in self.SINGLE_DEVICE_CHANNEL_CONFIGS:
                self._add_channel_config_card(cfg["name"], cfg["channel"], cfg["enabled"])
        elif new_count >= 2 and prev_count < 2:
            self._clear_all_channel_configs()
            for cfg in self.DUAL_DEVICE_CHANNEL_CONFIGS:
                self._add_channel_config_card(cfg["name"], cfg["channel"], cfg["enabled"])

    def _clear_all_channel_configs(self):
        for wdata in reversed(self._channel_config_widgets):
            wdata["card"].hide()
            wdata["card"].deleteLater()
        self._channel_configs.clear()
        self._channel_config_widgets.clear()
        while self.result_cards_layout.count():
            item = self.result_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()
        self.channel_cards = {}

    def _update_test_panel_state(self):
        has_device = self._connected_device_count() > 0
        if hasattr(self, '_disabled_overlay'):
            if has_device:
                self._disabled_overlay.hide()
            else:
                self._disabled_overlay.show()
                self._disabled_overlay.raise_()

    def _create_firmware_config_panel(self):
        outer = QFrame()
        outer.setObjectName("fwConfigOuter")
        outer.setStyleSheet("""
            QFrame#fwConfigOuter {
                background-color: transparent;
                border: none;
            }
        """)
        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(12)

        fw_panel = QFrame()
        fw_panel.setObjectName("fwPanel")
        fw_panel.setStyleSheet("""
            QFrame#fwPanel {
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

        self.build_serial_connection_widgets(fw_layout)
        self.bind_serial_signals()

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_label = QLabel("Download Mode")
        mode_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.download_mode_toggle = DownloadModeToggle()
        self.download_mode_toggle.setFixedWidth(160)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.download_mode_toggle)
        mode_row.addStretch()
        fw_layout.addLayout(mode_row)

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

        self.download_btn = ProgressButton()
        fw_layout.addWidget(self.download_btn)

        config_panel = QFrame()
        config_panel.setObjectName("configPanel")
        config_panel.setStyleSheet("""
            QFrame#configPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        config_layout = QVBoxLayout(config_panel)
        config_layout.setContentsMargins(16, 14, 16, 14)
        config_layout.setSpacing(8)

        config_title_row = QHBoxLayout()
        config_title_row.setSpacing(6)
        config_icon_label = QLabel()
        config_icon_label.setPixmap(
            _tinted_svg_icon(os.path.join(_ICONS_DIR, "file-json.svg"), "#94a3b8", 18).pixmap(18, 18)
        )
        config_icon_label.setFixedSize(18, 18)
        config_title = QLabel("Configuration Import (YAML)")
        config_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        config_title_row.addWidget(config_icon_label)
        config_title_row.addWidget(config_title)
        config_title_row.addStretch()
        config_layout.addLayout(config_title_row)

        chip_row = QHBoxLayout()
        chip_row.setSpacing(6)
        chip_select_label = QLabel("Select Chip")
        chip_select_label.setStyleSheet(
            "font-size: 11px; color: #7e96bf; background: transparent; border: none;"
        )
        chip_row.addWidget(chip_select_label)

        self.chip_combo = DarkComboBox()
        self.chip_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.chip_combo.setMinimumContentsLength(10)
        self.chip_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.chip_combo.setFixedHeight(22)
        font = self.chip_combo.font()
        font.setPixelSize(11)
        self.chip_combo.setFont(font)
        self.chip_combo.addItem("-- Select Chip --")
        for chip_name in SUPPORTED_CHIPS:
            self.chip_combo.addItem(chip_name)
        chip_row.addWidget(self.chip_combo, 1)

        self.chip_check_btn = QPushButton("Check")
        self.chip_check_btn.setFixedWidth(60)
        self.chip_check_btn.setFixedHeight(22)
        font_btn = self.chip_check_btn.font()
        font_btn.setPixelSize(11)
        self.chip_check_btn.setFont(font_btn)
        self.chip_check_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-weight: 600;
                min-height: 0px;
                padding: 2px 8px;
            }
            QPushButton:hover { background-color: #1c315b; }
            QPushButton:disabled {
                background-color: #0f1930;
                color: #5a6b8e;
                border: 1px solid #1b2847;
            }
        """)
        chip_row.addWidget(self.chip_check_btn)

        config_layout.addLayout(chip_row)

        config_file_label = QLabel("Paste Configuration Content")
        config_file_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        config_layout.addWidget(config_file_label)

        self.config_text_edit = QPlainTextEdit()
        self.config_text_edit.setPlaceholderText("Paste your YAML configuration here...")
        self.config_text_edit.setMinimumHeight(80)
        self.config_text_edit.setMaximumHeight(160)
        self.config_text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1b3e;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 11px;
                padding: 6px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #5d45ff;
            }
        """)
        config_layout.addWidget(self.config_text_edit)

        config_btn_row = QHBoxLayout()
        config_btn_row.setSpacing(8)

        self.import_config_btn = QPushButton(" Import Configuration")
        self.import_config_btn.setIcon(_tinted_svg_icon(os.path.join(_ICONS_DIR, "upload.svg"), "#dbe7ff"))
        self.import_config_btn.setIconSize(QSize(18, 18))
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
        config_btn_row.addWidget(self.import_config_btn, 1)

        self.execute_config_btn = QPushButton("⚙ Execute")
        self.execute_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d45ff;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #6d55ff; }
            QPushButton:disabled {
                background-color: #0f1930;
                color: #5a6b8e;
                border: 1px solid #1b2847;
            }
        """)
        config_btn_row.addWidget(self.execute_config_btn, 1)

        config_layout.addLayout(config_btn_row)

        outer_layout.addWidget(fw_panel, 1)
        outer_layout.addWidget(config_panel, 1)

        self.firmware_browse_btn.clicked.connect(self._browse_firmware)
        self.download_btn.clicked.connect(self._download_to_dut)
        self.download_btn.stop_clicked.connect(self._stop_download)
        self.chip_combo.currentIndexChanged.connect(self._on_chip_selected)
        self.chip_check_btn.clicked.connect(self._on_chip_check)
        self.import_config_btn.clicked.connect(self._import_configuration)
        self.execute_config_btn.clicked.connect(self._execute_configuration)

        return outer

    def _create_consumption_test_panel(self):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        panel = QFrame()
        panel.setObjectName("consumptionPanel")
        panel.setStyleSheet("""
            QFrame#consumptionPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        self._consumption_panel = panel
        wrapper_layout.addWidget(panel)

        self._disabled_overlay = QWidget(wrapper)
        self._disabled_overlay.setStyleSheet("""
            QWidget {
                background-color: rgba(5, 11, 26, 180);
                border-radius: 12px;
            }
        """)
        self._disabled_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        overlay_layout = QVBoxLayout(self._disabled_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_hint = QLabel("Please connect N6705C first")
        overlay_hint.setAlignment(Qt.AlignCenter)
        overlay_hint.setStyleSheet("""
            QLabel {
                color: #5a6b8e;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        overlay_layout.addWidget(overlay_hint)
        self._disabled_overlay.raise_()
        self._disabled_overlay.show()

        def _resize_overlay(event):
            self._disabled_overlay.setGeometry(panel.geometry())
        wrapper.resizeEvent = _resize_overlay
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

        period_label = QLabel("Sample Period (us)")
        period_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.sample_period_input = QLineEdit("20")
        self.sample_period_input.setFixedWidth(80)
        self.sample_period_input.setAlignment(Qt.AlignCenter)

        params_row.addWidget(time_label)
        params_row.addWidget(self.test_time_input)
        params_row.addSpacing(8)
        params_row.addWidget(period_label)
        params_row.addWidget(self.sample_period_input)
        params_row.addStretch()
        layout.addLayout(params_row)

        layout.addWidget(self._create_test_config_section())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        start_test_style = {
            "bg": "#0d6b4f",
            "border": "#18a87a",
            "text_color": "#ffffff",
            "progress_color": (24, 168, 122, 60),
            "complete_bg": (13, 107, 79, 80),
            "complete_text_color": "#4ade80",
            "failed_bg": "#2a0f1a",
            "failed_border": "#6b2040",
            "failed_text_color": "#ff7593",
            "waiting_text_color": "#a0b4d8",
            "spinner_color": (24, 168, 122, 200),
            "separator_color": "#18a87a",
            "stop_color_normal": "#8a9bbe",
            "stop_color_hover": "#ff5a5a",
            "min_height": 40,
        }
        self.start_test_btn = ProgressButton(
            idle_text="▶ START TEST",
            waiting_text="Preparing...",
            programming_text="Testing",
            complete_text="✓  Test complete",
            failed_text="Test failed",
            icon_path=os.path.join(_ICONS_DIR, "zap.svg"),
            style_overrides=start_test_style,
        )
        self.start_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        auto_test_style = {
            "bg": "#162544",
            "border": "#25355c",
            "text_color": "#dbe7ff",
            "progress_color": (93, 69, 255, 60),
            "complete_bg": (13, 107, 79, 80),
            "complete_text_color": "#4ade80",
            "failed_bg": "#2a0f1a",
            "failed_border": "#6b2040",
            "failed_text_color": "#ff7593",
            "waiting_text_color": "#a0b4d8",
            "spinner_color": (93, 69, 255, 200),
            "separator_color": "#25355c",
            "stop_color_normal": "#8a9bbe",
            "stop_color_hover": "#ff5a5a",
            "min_height": 40,
        }
        self.auto_test_btn = ProgressButton(
            idle_text="Auto Test",
            waiting_text="Preparing...",
            programming_text="Auto Testing",
            complete_text="✓  Auto test done",
            failed_text="Auto test failed",
            icon_path=os.path.join(_ICONS_DIR, "activity.svg"),
            style_overrides=auto_test_style,
        )
        self.auto_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        btn_row.addWidget(self.start_test_btn, 1)
        btn_row.addWidget(self.auto_test_btn, 1)
        layout.addLayout(btn_row)

        self.result_cards_container = QWidget()
        self.result_cards_container.setStyleSheet("background: transparent; border: none;")
        self.result_cards_layout = QHBoxLayout(self.result_cards_container)
        self.result_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.result_cards_layout.setSpacing(10)
        self.channel_cards = {}
        layout.addWidget(self.result_cards_container, 1)

        self.start_test_btn.clicked.connect(self._on_start_test)
        self.start_test_btn.stop_clicked.connect(self._stop_test)
        self.auto_test_btn.clicked.connect(self._on_auto_test)
        self.auto_test_btn.stop_clicked.connect(self._stop_auto_test)
        self.save_datalog_btn.clicked.connect(self._save_datalog)

        return wrapper

    def _create_test_config_section(self):
        config_frame = QFrame()
        config_frame.setObjectName("testConfigFrame")
        config_frame.setStyleSheet("""
            QFrame#testConfigFrame {
                background-color: #0a1228;
                border: 1px solid #1a2d57;
                border-radius: 10px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(14, 10, 14, 10)
        config_layout.setSpacing(8)

        config_header = QHBoxLayout()
        config_header.setSpacing(8)
        cfg_icon = QLabel("⚙")
        cfg_icon.setStyleSheet("font-size: 14px; color: #c8d6f0;")
        cfg_title = QLabel("Test Configuration")
        cfg_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        config_header.addWidget(cfg_icon)
        config_header.addWidget(cfg_title)
        config_header.addStretch()

        self.add_channel_btn = QPushButton("+ Add Channel")
        self.add_channel_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d45ff;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 11px;
                padding: 4px 12px;
                min-height: 26px;
            }
            QPushButton:hover { background-color: #6d55ff; }
        """)
        self.add_channel_btn.clicked.connect(self._add_channel_config)
        config_header.addWidget(self.add_channel_btn)
        config_layout.addLayout(config_header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setFixedHeight(140)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QWidget#channelConfigContainer {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: #0a1228;
                height: 6px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: #2a3f6e;
                min-width: 30px;
                border-radius: 3px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        self._channel_config_container = QWidget()
        self._channel_config_container.setObjectName("channelConfigContainer")
        self._channel_config_row = QHBoxLayout(self._channel_config_container)
        self._channel_config_row.setContentsMargins(0, 0, 0, 0)
        self._channel_config_row.setSpacing(10)
        self._channel_config_row.addStretch()

        scroll_area.setWidget(self._channel_config_container)
        config_layout.addWidget(scroll_area)

        return config_frame

    def _add_channel_config(self):
        idx = len(self._channel_configs)
        default_ch_idx = idx % 8
        labels = ["A-CH1", "A-CH2", "A-CH3", "A-CH4", "B-CH1", "B-CH2", "B-CH3", "B-CH4"]
        ch = labels[default_ch_idx] if default_ch_idx < len(labels) else "A-CH1"
        self._add_channel_config_card(f"CH{idx + 1}", ch, True)

    def _add_channel_config_card(self, name, channel_key, enabled):
        idx = len(self._channel_configs)
        config = {"name": name, "channel": channel_key, "enabled": enabled}
        self._channel_configs.append(config)

        card = QFrame()
        card_id = f"cfgCard{idx}"
        card.setObjectName(card_id)
        card.setStyleSheet(f"""
            QFrame#{card_id} {{
                background-color: #0d1b3e;
                border: 1px solid #1c2f54;
                border-radius: 8px;
            }}
        """)
        card.setFixedWidth(140)
        card.setMinimumHeight(100)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(5)

        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        enable_cb = QCheckBox("Enable")
        enable_cb.setChecked(enabled)
        enable_cb.setStyleSheet("""
            QCheckBox {
                color: #ffffff;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        top_row.addWidget(enable_cb)
        top_row.addStretch()

        remove_btn = QPushButton("✕")
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #5a6b8e;
                border: none;
                font-size: 13px;
                font-weight: 700;
                min-height: 0px;
                padding: 0px;
            }
            QPushButton:hover { color: #ff5a5a; }
        """)
        top_row.addWidget(remove_btn)
        card_layout.addLayout(top_row)

        name_label = QLabel("Name")
        name_label.setStyleSheet("font-size: 10px; color: #7e96bf;")
        card_layout.addWidget(name_label)

        name_input = QLineEdit(name)
        name_input.setFixedHeight(26)
        name_input.setStyleSheet("""
            QLineEdit {
                background-color: #020816;
                border: 1px solid #1c2f54;
                border-radius: 4px;
                padding: 2px 6px;
                color: #d7e3ff;
                font-size: 12px;
                min-height: 0px;
            }
            QLineEdit:focus { border: 1px solid #5b7cff; }
        """)
        card_layout.addWidget(name_input)

        ch_label = QLabel("Channel (N6705C)")
        ch_label.setStyleSheet("font-size: 10px; color: #7e96bf;")
        card_layout.addWidget(ch_label)

        channel_combo = DarkComboBox()
        channel_combo.setFixedHeight(26)
        font = channel_combo.font()
        font.setPixelSize(11)
        channel_combo.setFont(font)
        options = self._get_available_channel_options()
        for opt in options:
            channel_combo.addItem(opt)
        for i in range(channel_combo.count()):
            if channel_combo.itemText(i).startswith(channel_key + " "):
                channel_combo.setCurrentIndex(i)
                break
        card_layout.addWidget(channel_combo)

        stretch_idx = self._channel_config_row.count() - 1
        self._channel_config_row.insertWidget(stretch_idx, card)

        wdata = {
            "card": card,
            "enable_cb": enable_cb,
            "name_input": name_input,
            "channel_combo": channel_combo,
            "remove_btn": remove_btn,
            "config_index": idx,
        }
        self._channel_config_widgets.append(wdata)

        enable_cb.toggled.connect(lambda checked, i=idx: self._on_config_enable_changed(i, checked))
        name_input.textChanged.connect(lambda text, i=idx: self._on_config_name_changed(i, text))
        channel_combo.currentIndexChanged.connect(lambda ci, i=idx: self._on_config_channel_changed(i))
        remove_btn.clicked.connect(lambda checked=False, i=idx: self._remove_channel_config(i))

        self._refresh_result_cards()

    def _on_config_enable_changed(self, idx, checked):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["enabled"] = checked
            self._refresh_result_cards()

    def _on_config_name_changed(self, idx, text):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["name"] = text
            self._refresh_result_cards()

    def _on_config_channel_changed(self, idx):
        if idx < len(self._channel_configs):
            wdata = self._channel_config_widgets[idx]
            raw = wdata["channel_combo"].currentText()
            key = raw.split(" (")[0] if " (" in raw else raw
            self._channel_configs[idx]["channel"] = key
            self._refresh_result_cards()

    def _remove_channel_config(self, idx):
        if idx >= len(self._channel_configs):
            return
        wdata = self._channel_config_widgets[idx]
        wdata["card"].hide()
        wdata["card"].deleteLater()

        self._channel_configs.pop(idx)
        self._channel_config_widgets.pop(idx)

        for i, w in enumerate(self._channel_config_widgets):
            w["config_index"] = i
            w["enable_cb"].toggled.disconnect()
            w["name_input"].textChanged.disconnect()
            w["channel_combo"].currentIndexChanged.disconnect()
            w["remove_btn"].clicked.disconnect()
            w["enable_cb"].toggled.connect(lambda checked, ci=i: self._on_config_enable_changed(ci, checked))
            w["name_input"].textChanged.connect(lambda text, ci=i: self._on_config_name_changed(ci, text))
            w["channel_combo"].currentIndexChanged.connect(lambda cii, ci=i: self._on_config_channel_changed(ci))
            w["remove_btn"].clicked.connect(lambda checked=False, ci=i: self._remove_channel_config(ci))

        self._refresh_result_cards()

    def _refresh_result_cards(self):
        while self.result_cards_layout.count():
            item = self.result_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()
        self.channel_cards = {}

        for i, cfg in enumerate(self._channel_configs):
            if not cfg["enabled"]:
                continue
            colors = self.CHANNEL_COLORS_LIST[i % len(self.CHANNEL_COLORS_LIST)]
            card = self._create_result_card(i, cfg["name"], cfg["channel"], colors)
            self.result_cards_layout.addWidget(card, 1)

    def _create_result_card(self, idx, name, channel_key, colors):
        card = QFrame()
        card_id = f"resultCard{idx}"
        card.setObjectName(card_id)
        card.setStyleSheet(f"""
            QFrame#{card_id} {{
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

        title_label = QLabel(f"{name}")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['accent']};
                font-size: 13px;
                font-weight: 700;
                background: transparent;
            }}
        """)
        top_row.addWidget(title_label)
        top_row.addStretch()

        ch_tag = QLabel(channel_key)
        ch_tag.setStyleSheet(f"""
            QLabel {{
                color: #7e96bf;
                font-size: 10px;
                background: transparent;
            }}
        """)
        top_row.addWidget(ch_tag)
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

        self.channel_cards[idx] = {
            "card": card,
            "value_label": value_label,
            "name": name,
            "channel_key": channel_key,
        }

        return card

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

    def _browse_firmware(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Firmware File", "",
            "Firmware Files (*.bin *.hex);;All Files (*)"
        )
        if file_path:
            self.firmware_path = file_path
            self.firmware_file_input.setText(os.path.basename(file_path))
            self.append_log(f"[SYSTEM] Firmware file selected: {os.path.basename(file_path)}")

    def _download_to_dut(self):
        if not self.firmware_path:
            logger.warning("No firmware file selected")
            self.append_log("[WARNING] No firmware file selected.")
            return

        if self._download_thread is not None and self._download_thread.isRunning():
            logger.warning("Download already in progress")
            self.append_log("[WARNING] Download already in progress.")
            return

        port_text = self.get_selected_serial_port()
        if not port_text:
            logger.warning("No serial port selected")
            self.append_log("[WARNING] No serial port selected.")
            return

        m = re.search(r'(\d+)', port_text)
        com_port = m.group(1) if m else port_text

        mode_str = self.download_mode_toggle.value().lower()
        mode = DownloadMode.FLASH if mode_str == "flash" else DownloadMode.RAMRUN

        logger.info("Downloading firmware to DUT: port=%s, file=%s, mode=%s",
                     com_port, self.firmware_path, mode.value)
        self.append_log(f"[DOWNLOAD] Starting download: port={com_port}, file={os.path.basename(self.firmware_path)}, mode={mode.value}")

        chip = detect_chip_from_bin(self.firmware_path)
        if chip:
            logger.info("Detected chip model: %s", chip)
            self.append_log(f"[DOWNLOAD] Detected chip model: {chip}")
        else:
            logger.warning("Could not detect chip model from firmware file")
            self.append_log("[DOWNLOAD] Could not detect chip model from firmware file")

        try:
            file_size = os.path.getsize(self.firmware_path)
        except OSError:
            file_size = 0
        self.download_btn.setFileSize(file_size)
        self.download_btn.setStateWaiting()

        worker = _DownloadWorker(com_port, self.firmware_path, mode)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.state_changed.connect(self._on_download_state_changed)
        worker.finished.connect(self._on_download_finished)
        worker.error.connect(self._on_download_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._on_download_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._download_thread = thread
        self._download_worker = worker
        thread.start()

    def _on_download_state_changed(self, state_value):
        logger.info("Download state: %s", state_value)
        self.append_log(f"[DOWNLOAD] State: {state_value}")
        if state_value in (DownloadState.WAITING_SYNC.value, DownloadState.SYNCING.value):
            if self.download_btn.state() != ProgressButton.STATE_WAITING:
                self.download_btn.setStateWaiting()
        elif state_value == DownloadState.PROGRAMMING.value:
            self.download_btn.setStateProgramming()

    def _on_download_finished(self, result: DownloadResult):
        if result.success:
            logger.info("Download succeeded")
            self.append_log("[DOWNLOAD] ✅ Download succeeded.")
            self.download_btn.setStateComplete()
        else:
            logger.error("Download failed: %s", result.error_message)
            self.append_log(f"[ERROR] Download failed: {result.error_message}")
            self.download_btn.setStateFailed()

    def _on_download_error(self, err_msg):
        logger.error("Download error: %s", err_msg)
        self.append_log(f"[ERROR] Download error: {err_msg}")
        self.download_btn.setStateFailed()

    def _on_download_thread_cleaned(self):
        self._download_worker = None
        self._download_thread = None

    def _stop_download(self):
        if self._download_worker is not None:
            try:
                from lib.download_tools.download_script import DldTool
                proc = getattr(self._download_worker, '_dld', None)
                if proc and hasattr(proc, 'cancel'):
                    proc.cancel()
            except Exception:
                pass
        if self._download_thread is not None and self._download_thread.isRunning():
            self._download_thread.quit()
            self._download_thread.wait(3000)
        self.download_btn.setStateFailed()
        self.append_log("[DOWNLOAD] Download stopped by user.")
        logger.info("Download stopped by user")

    def _on_chip_selected(self, index):
        if index <= 0:
            self.selected_chip_config = None
            return
        chip_name = self.chip_combo.currentText()
        cfg = get_chip_config(chip_name)
        self.selected_chip_config = cfg
        if cfg:
            logger.info("Chip selected: %s", chip_name)
            self.append_log(f"[SYSTEM] Chip selected: {chip_name}")
        else:
            logger.warning("No config found for chip: %s", chip_name)
            self.append_log(f"[WARNING] No config found for chip: {chip_name}")

    def _on_chip_check(self):
        if self._chip_check_thread is not None and self._chip_check_thread.isRunning():
            self.append_log("[WARNING] Chip check already in progress.")
            return

        self.chip_check_btn.setEnabled(False)
        self.append_log("[SYSTEM] Starting chip check via I2C...")

        worker = _ChipCheckWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_chip_check_finished)
        worker.error.connect(self._on_chip_check_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._on_chip_check_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._chip_check_thread = thread
        self._chip_check_worker = worker
        thread.start()

    def _on_chip_check_finished(self, chip_info):
        self.chip_check_btn.setEnabled(True)

        self.append_log(
            f"[CHIP_CHECK] chip={chip_info.get('chip_name') or 'N/A'}"
            f"  main_die={chip_info.get('main_die') or 'N/A'}({chip_info.get('main_die_version') or '?'}, addr={chip_info.get('main_die_i2c_addr') or 'N/A'}, {chip_info.get('main_die_i2c_width') or 'N/A'}bit)"
            f"  main_die_pmu={chip_info.get('main_die_pmu') or 'N/A'}(addr={chip_info.get('main_die_pmu_i2c_addr') or 'N/A'}, {chip_info.get('main_die_pmu_i2c_width') or 'N/A'}bit)"
            f"  has_pmu={chip_info.get('has_pmu', False)}"
            f"  pmu={chip_info.get('pmu') or 'N/A'}({chip_info.get('pmu_version') or '?'}, addr={chip_info.get('pmu_i2c_addr') or 'N/A'}, {chip_info.get('pmu_i2c_width') or 'N/A'}bit)"
        )

        warning = chip_info.get("warning")
        if warning:
            self.append_log(f"[CHIP_CHECK] ⚠ {warning}")

        detected_name = chip_info.get("chip_name")
        if not detected_name:
            self.append_log("[WARNING] Chip check: no chip detected.")
            return

        exact_idx = self.chip_combo.findText(detected_name, Qt.MatchExactly)
        if exact_idx >= 0:
            self.chip_combo.setCurrentIndex(exact_idx)
            self.append_log(f"[CHIP_CHECK] Chip matched: {detected_name}")
            return

        prefix_match = detected_name.split("_")[0] if "_" in detected_name else detected_name
        for i in range(1, self.chip_combo.count()):
            item = self.chip_combo.itemText(i)
            if item == prefix_match or item.startswith(detected_name):
                self.chip_combo.setCurrentIndex(i)
                self.append_log(f"[CHIP_CHECK] Chip matched (prefix): {item}")
                return

        self.append_log(f"[WARNING] No matching chip found in list for: {detected_name}")

    def _on_chip_check_error(self, err_msg):
        self.chip_check_btn.setEnabled(True)
        logger.error("Chip check error: %s", err_msg)
        self.append_log(f"[ERROR] Chip check failed: {err_msg}")

    def _on_chip_check_thread_cleaned(self):
        self._chip_check_worker = None
        self._chip_check_thread = None

    def _import_configuration(self):
        config_text = self.config_text_edit.toPlainText().strip()
        if not config_text:
            logger.warning("No configuration content provided")
            self.append_log("[WARNING] No configuration content provided.")
            return
        self.config_content = config_text
        logger.info("Configuration imported from text input (%d chars)", len(config_text))
        self.append_log(f"[SYSTEM] Configuration imported from text input ({len(config_text)} chars)")

    def _execute_configuration(self):
        chip_name = self.chip_combo.currentText()
        if self.chip_combo.currentIndex() <= 0 or self.selected_chip_config is None:
            logger.warning("No chip selected for configuration execution")
            self.append_log("[WARNING] No chip selected. Please select a chip first.")
            return

        self.append_log(f"[EXECUTE] Starting configuration for chip: {chip_name}")

        try:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            i2c = I2CInterface()
            if not i2c.initialize():
                self.append_log("[ERROR] I2C interface initialization failed.")
                return
            self.append_log("[EXECUTE] I2C interface initialized successfully.")
        except Exception as e:
            logger.error("I2C initialization error: %s", e)
            self.append_log(f"[ERROR] I2C initialization error: {e}")
            return

        try:
            chip_info = i2c.bes_chip_check()
            self.append_log(f"[EXECUTE] Chip detected: {chip_info.get('chip_name', 'N/A')}")
        except Exception as e:
            logger.error("bes_chip_check failed: %s", e)
            self.append_log(f"[ERROR] Chip check failed: {e}")
            return

        self._compare_chip_info(chip_info, self.selected_chip_config)

        config_text = self.config_text_edit.toPlainText().strip()
        config_commands = None
        config_source = None

        if config_text:
            config_commands = self._parse_config_commands(config_text)
            config_source = "user_paste"
            self.append_log(f"[EXECUTE] Using pasted configuration ({len(config_commands)} commands)")
        else:
            pd = self.selected_chip_config.get("power_distribution")
            if pd and isinstance(pd, dict) and len(pd) > 0:
                raw_lines = []
                for section, cmds in pd.items():
                    if isinstance(cmds, list):
                        raw_lines.extend(cmds)
                config_commands = self._parse_config_commands("\n".join(raw_lines))
                config_source = "chip_config"
                self.append_log(f"[EXECUTE] Using chip config power_distribution ({len(config_commands)} commands)")
            else:
                logger.warning("No configuration available: neither pasted text nor chip power_distribution found")
                self.append_log("[WARNING] No configuration available. Please paste configuration or ensure chip config has power_distribution.")
                return

        if config_source == "user_paste":
            reply = QMessageBox.question(
                self,
                "Import Configuration",
                f"Do you want to save the pasted configuration to chip config '{chip_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._update_chip_config_file(chip_name, config_text)

        self._run_config_commands(i2c, chip_info, config_commands)
        self.append_log("[EXECUTE] Configuration execution completed.")

    def _compare_chip_info(self, detected, config):
        compare_keys = [
            "chip_name", "main_die", "main_die_version",
            "main_die_i2c_width", "main_die_i2c_addr",
            "main_die_pmu", "main_die_pmu_version",
            "main_die_pmu_i2c_width", "main_die_pmu_i2c_addr",
            "has_pmu", "pmu", "pmu_version", "pmu_i2c_width", "pmu_i2c_addr",
        ]
        for key in compare_keys:
            det_val = detected.get(key)
            cfg_val = config.get(key)
            if cfg_val in (None, "", {}):
                continue
            if self._chip_values_equal(det_val, cfg_val):
                continue
            logger.warning(
                "Chip info mismatch [%s]: detected=%s, config=%s",
                key, det_val, cfg_val
            )
            self.append_log(
                f"[WARNING] Chip info mismatch [{key}]: detected={det_val}, config={cfg_val}"
            )

    @staticmethod
    def _chip_values_equal(a, b):
        if a == b:
            return True
        if a is None or b is None:
            return False
        str_a = str(a).strip().lower()
        str_b = str(b).strip().lower()
        if str_a == str_b:
            return True
        try:
            return int(str_a, 0) == int(str_b, 0)
        except (ValueError, TypeError):
            pass
        if isinstance(a, bool) or isinstance(b, bool):
            truthy = {"true", "1", "yes"}
            falsy = {"false", "0", "no", ""}
            a_bool = str_a in truthy
            b_bool = str_b in truthy
            a_is_bool = str_a in truthy or str_a in falsy
            b_is_bool = str_b in truthy or str_b in falsy
            if a_is_bool and b_is_bool:
                return a_bool == b_bool
        return False

    @staticmethod
    def _parse_config_commands(text):
        commands = []
        lines = text.strip().splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("-"):
                line = line[1:].strip()
            if line.startswith("'") or line.startswith('"'):
                line = line[1:]
            if line.endswith("'") or line.endswith('"'):
                line = line[:-1]
            line = line.strip()

            comment_idx = line.find("//")
            if comment_idx >= 0:
                line = line[:comment_idx].strip()

            if not line:
                continue

            upper = line.upper()
            if not any(kw in upper for kw in ("WRITE_BITS", "WRITE", "READ")):
                continue

            target = "DUT"
            if ":" in line:
                prefix, rest = line.split(":", 1)
                prefix_upper = prefix.strip().upper()
                if prefix_upper in ("DUT", "PMU", "MAIN_DIE_PMU"):
                    target = prefix_upper
                    line = rest.strip()
                elif prefix_upper.endswith("_PMU"):
                    target = "EXT_PMU"
                    line = rest.strip()
                elif prefix_upper.endswith("_DUT") or prefix_upper.endswith("_MAIN"):
                    target = "DUT"
                    line = rest.strip()

            parts = line.split()
            if len(parts) < 2:
                continue

            op = parts[0].upper()
            if op == "WRITE_BITS" and len(parts) >= 5:
                reg_addr = int(parts[1], 0)
                msb = int(parts[2], 0)
                lsb = int(parts[3], 0)
                value = int(parts[4], 0)
                commands.append({
                    "op": "WRITE_BITS",
                    "target": target,
                    "reg_addr": reg_addr,
                    "msb": msb,
                    "lsb": lsb,
                    "value": value,
                })
            elif op == "WRITE" and len(parts) >= 3:
                reg_addr = int(parts[1], 0)
                value = int(parts[2], 0)
                commands.append({
                    "op": "WRITE",
                    "target": target,
                    "reg_addr": reg_addr,
                    "value": value,
                })
            elif op == "READ" and len(parts) >= 2:
                reg_addr = int(parts[1], 0)
                commands.append({
                    "op": "READ",
                    "target": target,
                    "reg_addr": reg_addr,
                })

        return commands

    @staticmethod
    def _to_int_addr(addr):
        if addr is None:
            return None
        if isinstance(addr, int):
            return addr
        if isinstance(addr, str):
            return int(addr, 0)
        return None

    def _resolve_device(self, chip_info, target):
        if target == "DUT":
            addr = self._to_int_addr(chip_info.get("main_die_i2c_addr"))
            width = chip_info.get("main_die_i2c_width")
            return addr, width
        if target == "EXT_PMU":
            addr = self._to_int_addr(chip_info.get("pmu_i2c_addr"))
            width = chip_info.get("pmu_i2c_width")
            return addr, width
        if target in ("PMU", "MAIN_DIE_PMU"):
            addr = self._to_int_addr(chip_info.get("main_die_pmu_i2c_addr"))
            width = chip_info.get("main_die_pmu_i2c_width")
            return addr, width
        if chip_info.get("has_pmu") and chip_info.get("pmu_i2c_addr"):
            addr = self._to_int_addr(chip_info.get("pmu_i2c_addr"))
            width = chip_info.get("pmu_i2c_width")
        else:
            addr = self._to_int_addr(chip_info.get("main_die_pmu_i2c_addr"))
            width = chip_info.get("main_die_pmu_i2c_width")
        return addr, width

    def _run_config_commands(self, i2c, chip_info, commands):
        for idx, cmd in enumerate(commands):
            op = cmd["op"]
            target = cmd.get("target", "DUT")
            reg_addr = cmd["reg_addr"]

            device_addr, width = self._resolve_device(chip_info, target)
            if device_addr is None or width is None:
                self.append_log(
                    f"[ERROR] Cannot resolve device address for target={target}, skipping command #{idx+1}"
                )
                continue

            try:
                if op == "WRITE_BITS":
                    msb = cmd["msb"]
                    lsb = cmd["lsb"]
                    value = cmd["value"]
                    current_val = i2c.read(device_addr, reg_addr, width)
                    bit_mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                    new_val = (current_val & ~bit_mask) | ((value << lsb) & bit_mask)
                    i2c.write(device_addr, reg_addr, new_val, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} WRITE_BITS dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} [{msb}:{lsb}]=0x{value:X} "
                        f"(0x{current_val:X} -> 0x{new_val:X})"
                    )

                elif op == "WRITE":
                    value = cmd["value"]
                    i2c.write(device_addr, reg_addr, value, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} WRITE dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} data=0x{value:X}"
                    )

                elif op == "READ":
                    read_val = i2c.read(device_addr, reg_addr, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} READ dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} => 0x{read_val:X}"
                    )

            except Exception as e:
                logger.error("Command #%d failed: %s", idx + 1, e)
                self.append_log(f"[ERROR] Command #{idx+1} failed: {e}")

    def _update_chip_config_file(self, chip_name, config_text):
        try:
            config_lines = []
            for raw_line in config_text.strip().splitlines():
                line = raw_line.strip()
                if line:
                    config_lines.append(line)

            chips_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                "chips", "bes_chip_configs"
            )
            config_file = os.path.join(chips_dir, f"{chip_name}.py")

            if not os.path.exists(config_file):
                logger.warning("Chip config file not found: %s", config_file)
                self.append_log(f"[WARNING] Chip config file not found: {config_file}")
                return

            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()

            import ast
            tree = ast.parse(content)
            chip_config_dict = None
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == "CHIP_CONFIG":
                            chip_config_dict = ast.literal_eval(content[node.value.col_offset:].split("\n}")[0] + "\n}")
                            break

            if chip_config_dict is None:
                chip_config_dict = {}

            chip_config_dict["power_distribution"] = {"user_config": config_lines}

            lines = ["CHIP_CONFIG = {\n"]
            for key, val in chip_config_dict.items():
                lines.append(f"    {key!r}: {val!r},\n")
            lines.append("}\n")

            with open(config_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info("Chip config updated: %s", config_file)
            self.append_log(f"[SYSTEM] Chip config updated: {chip_name}")
        except Exception as e:
            logger.error("Failed to update chip config: %s", e)
            self.append_log(f"[ERROR] Failed to update chip config: {e}")

    def _parse_channel_key(self, channel_key):
        m = re.match(r'^([AB])-CH(\d+)$', channel_key)
        if m:
            return m.group(1), int(m.group(2))
        return None, None

    def _on_start_test(self):
        self._start_test()

    def _start_test(self):
        if self.is_testing:
            return

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        device_channel_map = {}
        config_index_map = {}
        for i, cfg in enabled_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                self.append_log(f"[ERROR] Invalid channel key: {cfg['channel']}")
                return
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            is_conn = getattr(self, f"is_connected_{attr}", False)
            if not is_conn or not inst:
                self.append_log(f"[ERROR] N6705C-{device_label} is not connected (required by {cfg['name']}).")
                return
            if device_label not in device_channel_map:
                device_channel_map[device_label] = (inst, [])
                config_index_map[device_label] = {}
            if hw_ch not in device_channel_map[device_label][1]:
                device_channel_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
            sample_period = float(self.sample_period_input.text()) / 1_000_000
        except ValueError:
            self.append_log("[ERROR] Invalid test time or sample period.")
            return

        self.is_testing = True
        self._config_index_map = config_index_map
        self.start_test_btn.setStateWaiting()
        self.append_log(f"[TEST] Starting consumption test: time={test_time}s, period={sample_period}s")

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")

        worker = _ConsumptionTestWorker(device_channel_map, test_time, sample_period)
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
        self.start_test_btn.setStateProgramming()
        thread.start()

    def _on_channel_result(self, device_label, hw_channel, avg_current):
        cfg_idx = self._config_index_map.get(device_label, {}).get(hw_channel)
        if cfg_idx is not None and cfg_idx in self.channel_cards:
            label = self.channel_cards[cfg_idx]["value_label"]
            label.setText(self._format_current(avg_current))
        name = f"{device_label}-CH{hw_channel}"
        for cfg in self._channel_configs:
            if cfg["channel"] == f"{device_label}-CH{hw_channel}" and cfg["enabled"]:
                name = cfg["name"]
                break
        self.append_log(f"[TEST] {name} ({device_label}-CH{hw_channel}) avg current: {self._format_current(avg_current)}")

    def _on_test_error(self, err_msg):
        self.append_log(f"[ERROR] {err_msg}")

    def _on_test_finished(self):
        self.is_testing = False
        self.start_test_btn.setStateComplete()
        self.append_log("[TEST] Test completed.")

    def _on_test_thread_cleaned(self):
        self._test_worker = None
        self._test_thread = None

    def _stop_test(self):
        if self._test_worker:
            self._test_worker.stop()
        self.is_testing = False
        self.start_test_btn.setStateFailed()
        self.append_log("[TEST] Test stopped.")

    def _on_auto_test(self):
        self.append_log("[AUTO_TEST] Auto test started (not implemented yet).")
        self.auto_test_btn.setStateWaiting()

    def _stop_auto_test(self):
        self.append_log("[AUTO_TEST] Auto test stopped.")
        self.auto_test_btn.setStateFailed()

    def _save_datalog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DataLog", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            logger.info("Saving datalog to: %s", file_path)
            self.append_log(f"[SYSTEM] DataLog saved to: {file_path}")

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

    def update_channel_current(self, channel_idx, avg_current):
        if channel_idx in self.channel_cards:
            label = self.channel_cards[channel_idx]["value_label"]
            if avg_current is not None:
                label.setText(self._format_current(avg_current))
            else:
                label.setText("- - -")

    def get_selected_channels(self):
        return [
            cfg["channel"] for cfg in self._channel_configs if cfg["enabled"]
        ]

    def get_test_config(self):
        return {
            'n6705c_a_connected': self.is_connected_a,
            'n6705c_b_connected': self.is_connected_b,
            'firmware_path': self.firmware_path,
            'config_content': self.config_content,
            'selected_chip': self.selected_chip_config,
            'channel_configs': self._channel_configs,
        }

    def update_test_result(self, result):
        if isinstance(result, dict):
            for idx, cfg in enumerate(self._channel_configs):
                if not cfg["enabled"]:
                    continue
                key = cfg["channel"]
                if key in result:
                    self.update_channel_current(idx, result[key])

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def _on_clear_log(self):
        self.execution_logs.clear_log()

    def clear_results(self):
        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")

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