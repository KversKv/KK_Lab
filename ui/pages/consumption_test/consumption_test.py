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

from ui.styles.n6705c_module_frame import N6705CConnectionMixin
from ui.styles.serialCom_module_frame import SerialComMixin, MODE_INLINE
from ui.styles.execution_logs_module_frame import ExecutionLogsFrame
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QPlainTextEdit,
    QGridLayout, QFrame, QApplication, QFileDialog,
    QCheckBox, QSizePolicy, QToolTip, QListView
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QThread, QObject, QSize,
    QRectF, QRect, QPropertyAnimation, QEasingCurve, Property,
    QElapsedTimer as _QElapsedTimer
)
from PySide6.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QColor, QPen,
    QFontMetrics, QPainterPath, QCursor, QPalette
)
from PySide6.QtSvg import QSvgRenderer

from lib.download_tools.download_script import download_bin, DownloadMode, DownloadState, DownloadResult, detect_chip_from_bin
from chips.bes_chip_configs.bes_chip_configs import SUPPORTED_CHIPS, get_chip_config
from ui.widgets.dark_combobox import DarkComboBox
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


class ProgrammingButton(QWidget):
    clicked = Signal()
    stop_clicked = Signal()

    STATE_IDLE = "idle"
    STATE_WAITING = "waiting"
    STATE_PROGRAMMING = "programming"
    STATE_COMPLETE = "complete"
    STATE_FAILED = "failed"

    BAUD_RATE = 921600

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self.STATE_IDLE
        self._progress = 0.0
        self._file_size = 0
        self._stop_hovered = False
        self._spinner_angle = 0.0
        self._stop_zone_width = 38

        self.setMinimumHeight(48)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        self._download_svg = QSvgRenderer(os.path.join(_ICONS_DIR, "download.svg"))

        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(30)
        self._spinner_timer.timeout.connect(self._tick_spinner)

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(50)
        self._progress_timer.timeout.connect(self._tick_progress)
        self._elapsed = _QElapsedTimer()

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_to_idle)

    def state(self):
        return self._state

    def setFileSize(self, size_bytes):
        self._file_size = size_bytes

    def setStateIdle(self):
        self._state = self.STATE_IDLE
        self._progress = 0.0
        self._spinner_timer.stop()
        self._progress_timer.stop()
        self._reset_timer.stop()
        self.setCursor(Qt.PointingHandCursor)
        self.update()

    def setStateWaiting(self):
        self._state = self.STATE_WAITING
        self._progress = 0.0
        self._spinner_angle = 0.0
        self._spinner_timer.start()
        self._progress_timer.stop()
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def setStateProgramming(self):
        self._state = self.STATE_PROGRAMMING
        self._progress = 0.0
        self._spinner_timer.stop()
        self._elapsed.start()
        self._progress_timer.start()
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def setStateComplete(self):
        self._state = self.STATE_COMPLETE
        self._progress = 1.0
        self._spinner_timer.stop()
        self._progress_timer.stop()
        self.setCursor(Qt.ArrowCursor)
        self.update()
        self._reset_timer.start(1500)

    def setStateFailed(self):
        self._state = self.STATE_FAILED
        self._progress = 0.0
        self._spinner_timer.stop()
        self._progress_timer.stop()
        self.setCursor(Qt.ArrowCursor)
        self.update()
        self._reset_timer.start(2000)

    def _reset_to_idle(self):
        self.setStateIdle()

    def _tick_spinner(self):
        self._spinner_angle = (self._spinner_angle + 8.0) % 360.0
        self.update()

    def _tick_progress(self):
        if self._file_size <= 0:
            return
        elapsed_s = self._elapsed.elapsed() / 1000.0
        bytes_per_sec = self.BAUD_RATE / 10.0
        transferred = elapsed_s * bytes_per_sec
        self._progress = min(transferred / self._file_size, 0.98)
        self.update()

    def _stop_rect(self):
        return QRect(self.width() - self._stop_zone_width, 0,
                     self._stop_zone_width, self.height())

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        if self._state == self.STATE_PROGRAMMING:
            if self._stop_rect().contains(event.pos()):
                self.stop_clicked.emit()
        elif self._state == self.STATE_IDLE:
            self.clicked.emit()

    def mouseMoveEvent(self, event):
        if self._state == self.STATE_PROGRAMMING:
            in_stop = self._stop_rect().contains(event.pos())
            if in_stop != self._stop_hovered:
                self._stop_hovered = in_stop
                self.setCursor(Qt.PointingHandCursor if in_stop else Qt.ArrowCursor)
                if in_stop:
                    QToolTip.showText(QCursor.pos(), "Stop download")
                self.update()
        else:
            self._stop_hovered = False
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._stop_hovered:
            self._stop_hovered = False
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = 8.0

        if self._state == self.STATE_FAILED:
            bg = QColor("#2a0f1a")
            border = QColor("#6b2040")
        else:
            bg = QColor("#162544")
            border = QColor("#25355c")

        btn_path = QPainterPath()
        btn_path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        p.drawPath(btn_path)

        if self._state == self.STATE_PROGRAMMING:
            fill_w = max(0, (w - self._stop_zone_width) * self._progress)
            if fill_w > 0:
                clip = QPainterPath()
                clip.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
                p.save()
                p.setClipPath(clip)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(93, 69, 255, 60))
                p.drawRect(QRectF(0, 0, fill_w, h))
                p.restore()
        elif self._state == self.STATE_COMPLETE:
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
            p.save()
            p.setClipPath(clip)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(13, 107, 79, 80))
            p.drawRect(QRectF(0, 0, w, h))
            p.restore()

        font = self.font()
        if font.family() != "Segoe UI":
            font = QFont("Segoe UI", 9)
        font.setWeight(QFont.DemiBold)
        p.setFont(font)
        fm = QFontMetrics(font)

        icon_size = 18
        icon_text_gap = 6
        left_margin = 14

        if self._state == self.STATE_IDLE:
            text = "Programming to DUT"
            text_color = QColor("#dbe7ff")
            tw = fm.horizontalAdvance(text)
            total_w = icon_size + icon_text_gap + tw
            start_x = (w - total_w) / 2

            tinted = QPixmap(icon_size, icon_size)
            tinted.fill(Qt.transparent)
            tp = QPainter(tinted)
            tp.setRenderHint(QPainter.Antialiasing)
            tp.setRenderHint(QPainter.SmoothPixmapTransform)
            self._download_svg.render(tp, QRectF(0, 0, icon_size, icon_size))
            tp.setCompositionMode(QPainter.CompositionMode_SourceIn)
            tp.fillRect(tinted.rect(), text_color)
            tp.end()
            p.drawPixmap(int(start_x), int((h - icon_size) / 2), tinted)

            p.setPen(text_color)
            p.drawText(QRectF(start_x + icon_size + icon_text_gap, 0, tw + 2, h),
                       Qt.AlignVCenter | Qt.AlignLeft, text)

        elif self._state == self.STATE_WAITING:
            text = "Wait for sync"
            text_color = QColor("#a0b4d8")
            tw = fm.horizontalAdvance(text)
            total_w = icon_size + icon_text_gap + tw
            start_x = (w - total_w) / 2

            cx = start_x + icon_size / 2
            cy = h / 2
            p.save()
            p.translate(cx, cy)
            p.rotate(self._spinner_angle)
            pen = QPen(QColor(93, 69, 255, 200), 2.5)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(QRectF(-icon_size / 2, -icon_size / 2, icon_size, icon_size),
                       0 * 16, 270 * 16)
            p.restore()

            p.setPen(text_color)
            p.drawText(QRectF(start_x + icon_size + icon_text_gap, 0, tw + 2, h),
                       Qt.AlignVCenter | Qt.AlignLeft, text)

        elif self._state == self.STATE_PROGRAMMING:
            pct = int(self._progress * 100)
            text_color = QColor("#dbe7ff")
            main_w = w - self._stop_zone_width

            prefix = "Programming "
            suffix = "%"
            max_num = "100"
            max_full = prefix + max_num + suffix
            max_tw = fm.horizontalAdvance(max_full)
            anchor_x = (main_w - max_tw) / 2

            prefix_w = fm.horizontalAdvance(prefix)
            max_num_w = fm.horizontalAdvance(max_num)
            num_str = str(pct)
            num_w = fm.horizontalAdvance(num_str)

            p.setPen(text_color)
            p.drawText(QRectF(anchor_x, 0, prefix_w, h),
                       Qt.AlignVCenter | Qt.AlignLeft, prefix)
            p.drawText(QRectF(anchor_x + prefix_w, 0, max_num_w, h),
                       Qt.AlignVCenter | Qt.AlignRight, num_str)
            p.drawText(QRectF(anchor_x + prefix_w + max_num_w, 0,
                              fm.horizontalAdvance(suffix) + 2, h),
                       Qt.AlignVCenter | Qt.AlignLeft, suffix)

            sep_x = w - self._stop_zone_width
            p.setPen(QPen(QColor("#25355c"), 1))
            p.drawLine(int(sep_x), 4, int(sep_x), h - 4)

            stop_rect = self._stop_rect()
            if self._stop_hovered:
                p.save()
                clip = QPainterPath()
                clip.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
                p.setClipPath(clip)
                p.setPen(Qt.NoPen)
                p.setBrush(QColor(255, 70, 70, 40))
                p.drawRect(stop_rect)
                p.restore()

            stop_icon_s = 12
            six = stop_rect.x() + (stop_rect.width() - stop_icon_s) / 2
            siy = (h - stop_icon_s) / 2
            stop_color = QColor("#ff5a5a") if self._stop_hovered else QColor("#8a9bbe")
            p.setPen(Qt.NoPen)
            p.setBrush(stop_color)
            p.drawRoundedRect(QRectF(six, siy, stop_icon_s, stop_icon_s), 2, 2)

        elif self._state == self.STATE_COMPLETE:
            text = "✓  Program complete"
            text_color = QColor("#4ade80")
            tw = fm.horizontalAdvance(text)
            tx = (w - tw) / 2
            p.setPen(text_color)
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, text)

        elif self._state == self.STATE_FAILED:
            text = "Program failed"
            text_color = QColor("#ff7593")
            p.setPen(text_color)
            p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, text)

        p.end()

    def sizeHint(self):
        return QSize(220, 48)


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


class ConsumptionTestUI(QWidget, N6705CConnectionMixin, SerialComMixin):
    connection_status_changed = Signal(bool)
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    CHANNEL_COLORS = {
        1: {"accent": "#d4a514", "bg": "#1a1708", "border": "#3d2e08"},
        2: {"accent": "#18b67a", "bg": "#081a14", "border": "#0a3d28"},
        3: {"accent": "#2f6fed", "bg": "#081028", "border": "#0c2a5e"},
        4: {"accent": "#d14b72", "bg": "#1a080e", "border": "#3d0c22"},
    }

    def __init__(self, n6705c_top=None):
        super().__init__()

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

        self._setup_style()
        self._create_layout()
        self.sync_n6705c_from_top()

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
        outer = QFrame()
        outer.setObjectName("connOuter")
        outer.setStyleSheet("""
            QFrame#connOuter {
                background-color: transparent;
                border: none;
            }
        """)
        outer_layout = QHBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(12)

        n6705c_panel = QFrame()
        n6705c_panel.setObjectName("connectionPanel")
        n6705c_panel.setStyleSheet("""
            QFrame#connectionPanel {
                background-color: #0b1630;
                border: 1px solid #18284d;
                border-radius: 12px;
            }
        """)
        n6705c_layout = QVBoxLayout(n6705c_panel)
        n6705c_layout.setContentsMargins(16, 14, 16, 14)
        n6705c_layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        icon = QLabel("⚡")
        icon.setStyleSheet("font-size: 16px; color: #00f5c4;")
        title = QLabel("N6705C Connection")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        title_row.addWidget(icon)
        title_row.addWidget(title)
        title_row.addStretch()
        n6705c_layout.addLayout(title_row)

        self.build_n6705c_connection_widgets(n6705c_layout)
        self.bind_n6705c_signals()

        outer_layout.addWidget(n6705c_panel, 1)

        return outer

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

        self.download_btn = ProgrammingButton()
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
        self.chip_combo.setView(QListView())
        self.chip_combo.view().setMouseTracking(True)
        palette = self.chip_combo.view().palette()
        palette.setColor(QPalette.Highlight, QColor("#5d45ff"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.chip_combo.view().setPalette(palette)
        self.chip_combo.view().setStyleSheet("""
            QListView {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                outline: 0;
            }
            QListView::item {
                padding: 4px 8px;
                border: none;
            }
            QListView::item:hover {
                background-color: #5d45ff;
                color: white;
            }
            QListView::item:selected {
                background-color: #5d45ff;
                color: white;
                border: none;
                outline: none;
            }
        """)
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
        config_layout.addWidget(self.import_config_btn)

        outer_layout.addWidget(fw_panel, 1)
        outer_layout.addWidget(config_panel, 1)

        self.firmware_browse_btn.clicked.connect(self._browse_firmware)
        self.download_btn.clicked.connect(self._download_to_dut)
        self.download_btn.stop_clicked.connect(self._stop_download)
        self.chip_combo.currentIndexChanged.connect(self._on_chip_selected)
        self.import_config_btn.clicked.connect(self._import_configuration)

        return outer

    def _create_consumption_test_panel(self):
        panel = QFrame()
        panel.setObjectName("consumptionPanel")
        panel.setStyleSheet("""
            QFrame#consumptionPanel {
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
        self._start_btn_style = """
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
        """
        self._stop_btn_style = """
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
        """
        self.start_test_btn.setStyleSheet(self._start_btn_style)

        self.stop_test_btn = QPushButton("🟥 STOP")
        self.stop_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.setStyleSheet(self._stop_btn_style)
        self.stop_test_btn.hide()

        btn_row.addWidget(self.start_test_btn, 1)
        layout.addLayout(btn_row)

        channels_row = QHBoxLayout()
        channels_row.setSpacing(10)

        self.channel_cards = {}
        for ch in range(1, 5):
            card = self._create_channel_card(ch)
            channels_row.addWidget(card, 1)

        layout.addLayout(channels_row, 1)

        self.start_test_btn.clicked.connect(self._on_start_or_stop)
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
        card.setObjectName(f"channelCard{ch_num}")
        card.setStyleSheet(f"""
            QFrame#channelCard{ch_num} {{
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
            if self.download_btn.state() != ProgrammingButton.STATE_WAITING:
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

    def _import_configuration(self):
        config_text = self.config_text_edit.toPlainText().strip()
        if not config_text:
            logger.warning("No configuration content provided")
            self.append_log("[WARNING] No configuration content provided.")
            return
        self.config_content = config_text
        logger.info("Configuration imported from text input (%d chars)", len(config_text))
        self.append_log(f"[SYSTEM] Configuration imported from text input ({len(config_text)} chars)")

    def _on_start_or_stop(self):
        if self.is_testing:
            self._stop_test()
        else:
            self._start_test()

    def _update_test_button_state(self, running):
        if running:
            self.start_test_btn.setText("🟥 STOP")
            self.start_test_btn.setStyleSheet(self._stop_btn_style)
        else:
            self.start_test_btn.setText("▶ START TEST")
            self.start_test_btn.setStyleSheet(self._start_btn_style)

    def _start_test(self):
        if self.is_testing:
            return
        if not self.is_connected or not self.n6705c:
            self.set_system_status("Please connect N6705C first", is_error=True)
            self.append_log("[ERROR] Please connect N6705C first.")
            return

        selected_channels = [
            ch for ch in range(1, 5)
            if self.channel_cards[ch]["checkbox"].isChecked()
        ]
        if not selected_channels:
            self.set_system_status("No channel selected", is_error=True)
            self.append_log("[ERROR] No channel selected.")
            return

        try:
            test_time = float(self.test_time_input.text())
            sample_period = float(self.sample_period_input.text())
        except ValueError:
            self.set_system_status("Invalid test time or sample period", is_error=True)
            self.append_log("[ERROR] Invalid test time or sample period.")
            return

        self.is_testing = True
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(True)
        self._update_test_button_state(True)
        self.append_log(f"[TEST] Starting consumption test: channels={selected_channels}, time={test_time}s, period={sample_period}s")

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
        self.append_log(f"[TEST] CH{channel} avg current: {self._format_current(avg_current)}")

    def _on_test_error(self, err_msg):
        self.set_system_status(err_msg, is_error=True)
        self.append_log(f"[ERROR] {err_msg}")

    def _on_test_finished(self):
        self.is_testing = False
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self._update_test_button_state(False)
        self.append_log("[TEST] Test completed.")

    def _on_test_thread_cleaned(self):
        self._test_worker = None
        self._test_thread = None

    def _stop_test(self):
        if self._test_worker:
            self._test_worker.stop()
        self.is_testing = False
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self._update_test_button_state(False)
        self.append_log("[TEST] Test stopped.")

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

    def get_test_config(self):
        return {
            'n6705c_connected': self.is_connected,
            'firmware_path': self.firmware_path,
            'config_content': self.config_content,
            'selected_chip': self.selected_chip_config,
            'selected_channels': self.get_selected_channels(),
        }

    def update_test_result(self, result):
        if isinstance(result, dict):
            for ch in range(1, 5):
                key = f"ch{ch}_avg_current"
                if key in result:
                    self.update_channel_current(ch, result[key])

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def _on_clear_log(self):
        self.execution_logs.clear_log()

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