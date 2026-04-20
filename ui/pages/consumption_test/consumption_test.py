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

from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from ui.modules.serialCom_module_frame import SerialComMixin, MODE_INLINE
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QPlainTextEdit,
    QFrame, QApplication, QFileDialog,
    QCheckBox, QSizePolicy, QMessageBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView
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

CURRENT_UNIT = "uA"

_UNIT_CONFIG = {
    "A":  {"scale": 1.0,    "suffix": "A"},
    "mA": {"scale": 1e3,    "suffix": "mA"},
    "uA": {"scale": 1e6,    "suffix": "uA"},
}


def _format_current_unified(current_A, unit=None):
    if unit is None:
        unit = CURRENT_UNIT
    cfg = _UNIT_CONFIG.get(unit, _UNIT_CONFIG["uA"])
    return f"{current_A * cfg['scale']:.4f}{cfg['suffix']}"


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


class ControlMethodToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self._value = "N6705C"
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
        if val not in ("N6705C", "MCU"):
            return
        if val == self._value:
            return
        self._value = val
        target = 0.0 if val == "N6705C" else 1.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled.emit(self._value)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = "MCU" if self._value == "N6705C" else "N6705C"
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
        p.drawText(left_rect, Qt.AlignCenter, "N6705C")

        p.setPen(self._text_active if self._anim_progress >= 0.5 else self._text_inactive)
        p.drawText(right_rect, Qt.AlignCenter, "MCU")

        p.end()

    def sizeHint(self):
        return QSize(160, 32)


_POLARITY_OPTIONS = [
    {"key": "rising", "label": "Rising Edge", "svg": os.path.join(_ICONS_DIR, "polarity_rising.svg")},
    {"key": "falling", "label": "Falling Edge", "svg": os.path.join(_ICONS_DIR, "polarity_falling.svg")},
]


class PolarityToggle(QWidget):
    polarity_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._options = _POLARITY_OPTIONS
        self._index = 0
        self._anim_progress = 0.0
        self._n = len(self._options)

        self.setFixedHeight(28)
        self.setFixedWidth(self._n * 32)
        self.setCursor(Qt.PointingHandCursor)

        self._bg_color = QColor("#1A2750")
        self._knob_color = QColor("#243760")
        self._icon_active_color = QColor("#F3F6FF")
        self._icon_inactive_color = QColor("#5F77AE")
        self._border_color = QColor("#22376A")

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

        self._icon_cache = {}

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def _render_icon(self, svg_path, color, size=16):
        cache_key = (svg_path, color.name(), size)
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        renderer = QSvgRenderer(svg_path)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        self._icon_cache[cache_key] = pixmap
        return pixmap

    def value(self):
        return self._options[self._index]["key"]

    def setValue(self, key):
        for i, opt in enumerate(self._options):
            if opt["key"] == key:
                if i == self._index:
                    return
                self._index = i
                target = float(i)
                self._anim.stop()
                self._anim.setStartValue(self._anim_progress)
                self._anim.setEndValue(target)
                self._anim.start()
                self.polarity_changed.emit(key)
                return

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            seg_w = self.width() / self._n
            clicked_idx = int(event.position().x() / seg_w)
            clicked_idx = max(0, min(clicked_idx, self._n - 1))
            if clicked_idx != self._index:
                self._index = clicked_idx
                target = float(clicked_idx)
                self._anim.stop()
                self._anim.setStartValue(self._anim_progress)
                self._anim.setEndValue(target)
                self._anim.start()
                self.polarity_changed.emit(self._options[self._index]["key"])
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2

        p.setPen(QPen(self._border_color, 1))
        p.setBrush(self._bg_color)
        p.drawRoundedRect(QRect(0, 0, w, h), radius, radius)

        margin = 3
        seg_w = w / self._n
        knob_w = seg_w - margin
        knob_h = h - margin * 2
        knob_x = margin + self._anim_progress * seg_w
        knob_y = margin

        p.setPen(Qt.NoPen)
        p.setBrush(self._knob_color)
        p.drawRoundedRect(QRectF(knob_x, knob_y, knob_w, knob_h),
                          knob_h / 2, knob_h / 2)

        icon_size = 16
        for i, opt in enumerate(self._options):
            cx = seg_w * i + seg_w / 2
            cy = h / 2
            dist = abs(self._anim_progress - i)
            is_active = dist < 0.5
            color = self._icon_active_color if is_active else self._icon_inactive_color
            pixmap = self._render_icon(opt["svg"], color, icon_size)
            ix = int(cx - icon_size / 2)
            iy = int(cy - icon_size / 2)
            p.drawPixmap(ix, iy, pixmap)

        p.end()

    def sizeHint(self):
        return QSize(self._n * 32, 28)

    def toolTip(self):
        return self._options[self._index]["label"]

    def event(self, ev):
        if ev.type() == ev.Type.ToolTip:
            from PySide6.QtWidgets import QToolTip
            seg_w = self.width() / self._n
            x = ev.pos().x()
            idx = int(x / seg_w)
            idx = max(0, min(idx, self._n - 1))
            QToolTip.showText(ev.globalPos(), self._options[idx]["label"], self)
            return True
        return super().event(ev)


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
            logger.debug("DownloadWorker run: port=%s, bin=%s, mode=%s, timeout=%s",
                         self.com_port, self.bin_file, self.mode, self.timeout)

            def _on_state(state: DownloadState):
                self.state_changed.emit(state.value)

            result = download_bin(
                com_port=self.com_port,
                bin_file=self.bin_file,
                mode=self.mode,
                timeout=self.timeout,
                on_state_change=_on_state,
            )
            logger.debug("DownloadWorker finished: success=%s, state=%s",
                         result.success, result.state.value)
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
            logger.debug("ConsumptionTestWorker run: test_time=%s, sample_period=%s, devices=%s",
                         self.test_time, self.sample_period, list(self.device_channel_map.keys()))
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
                    logger.debug("ConsumptionTestWorker result: %s CH%s = %.6e A",
                                 device_label, ch, float(avg_current))
                    self.channel_result.emit(device_label, ch, float(avg_current))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit()


class _ConsumptionTestForceHighWorker(QObject):
    log_message = Signal(str)
    channel_result = Signal(str, int, float, str)
    test_summary = Signal(dict)
    progress = Signal(float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, vbat_device_label, vbat_inst, vbat_hw_ch,
                 force_high_map, test_time, sample_period,
                 channel_names=None):
        super().__init__()
        self.vbat_device_label = vbat_device_label
        self.vbat_inst = vbat_inst
        self.vbat_hw_ch = vbat_hw_ch
        self.force_high_map = force_high_map
        self.test_time = test_time
        self.sample_period = sample_period
        self.channel_names = channel_names or {}
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            self._consumption_test_force_high()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @staticmethod
    def _estimate_datalog_time(test_time):
        return test_time + 4.0

    @staticmethod
    def _estimate_force_high_time(test_time):
        return test_time + 5.0

    def _make_sub_progress(self, base, span, total_est):
        def _on_progress(frac):
            self.progress.emit(min((base + frac * span) / total_est, 1.0))
        return _on_progress

    def _consumption_test_force_high(self):
        import threading

        logger.debug("ForceHighWorker: vbat=%s CH%s, force_high_devices=%s, test_time=%s, sample_period=%s",
                     self.vbat_device_label, self.vbat_hw_ch,
                     list(self.force_high_map.keys()), self.test_time, self.sample_period)

        vbat_ch = self.vbat_hw_ch
        vbat_inst = self.vbat_inst
        vbat_label = self.vbat_device_label

        setup_time = 1.0
        step1_time = self._estimate_datalog_time(self.test_time)
        step2_time = self._estimate_force_high_time(self.test_time)

        total_est = setup_time + step1_time + step2_time
        if total_est <= 0:
            total_est = 1.0

        cursor = 0.0
        self.progress.emit(0.0)
        stop_check = lambda: self._is_stopped

        results = {}
        vbat_remain = None

        self.log_message.emit("[TEST] Resetting sub-channels to VMeter mode...")
        for device_label, (n6705c_inst, hw_channels) in self.force_high_map.items():
            for ch in hw_channels:
                try:
                    n6705c_inst.set_mode(ch, "VMETer")
                    n6705c_inst.channel_on(ch)
                except Exception as e:
                    self.log_message.emit(f"[WARNING] Failed to set {device_label}-CH{ch} to VMeter: {e}")
        cursor = setup_time
        self.progress.emit(cursor / total_est)

        self.log_message.emit(f"[TEST] Measuring Vbat (CH{vbat_ch}) total current...")
        vbat_period = self.sample_period
        vbat_result = vbat_inst.fetch_current_by_datalog(
            [vbat_ch], self.test_time, vbat_period,
            on_progress=self._make_sub_progress(cursor, step1_time, total_est),
            stop_check=stop_check,
        )
        cursor += step1_time
        self.progress.emit(min(cursor / total_est, 1.0))
        if self._is_stopped:
            return
        vbat_current = vbat_result.get(vbat_ch, 0.0)
        logger.debug("ForceHighWorker: Vbat total current = %.6e A", vbat_current)
        self.channel_result.emit(vbat_label, vbat_ch, float(vbat_current), "vbat")
        results[(vbat_label, vbat_ch)] = float(vbat_current)

        channel_voltages = {}
        try:
            vbat_v = float(vbat_inst.measure_voltage(vbat_ch))
            channel_voltages[(vbat_label, vbat_ch)] = vbat_v
        except Exception:
            channel_voltages[(vbat_label, vbat_ch)] = 0.0

        self.log_message.emit("[TEST] Force high on sub-channels (+20mV) — parallel sync...")

        task_list = []
        for device_label, (n6705c_inst, hw_channels) in self.force_high_map.items():
            monitor_chs = []
            if device_label == vbat_label and vbat_ch not in hw_channels:
                monitor_chs.append(vbat_ch)
            all_datalog_chs = list(hw_channels) + [ch for ch in monitor_chs if ch not in hw_channels]
            num_ch = len(all_datalog_chs)
            ch_period = self.sample_period * num_ch
            task_list.append({
                "device_label": device_label,
                "inst": n6705c_inst,
                "force_channels": list(hw_channels),
                "monitor_channels": monitor_chs,
                "all_datalog_channels": all_datalog_chs,
                "sample_period": ch_period,
                "measured_voltages": None,
                "curr_result": None,
                "error": None,
            })

        if not task_list:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        self.log_message.emit("[TEST] Preparing force high on all instruments...")
        prepare_errors = [None] * len(task_list)

        def prepare_worker(idx, task):
            try:
                mv = task["inst"].prepare_force_high(
                    task["force_channels"],
                    voltage_offset=0.02,
                    current_limit=1.0,
                    monitor_channels=task["monitor_channels"],
                )
                task["measured_voltages"] = mv
            except Exception as e:
                prepare_errors[idx] = e

        prepare_threads = []
        for idx, task in enumerate(task_list):
            t = threading.Thread(target=prepare_worker, args=(idx, task), daemon=True)
            prepare_threads.append(t)
        for t in prepare_threads:
            t.start()
        for t in prepare_threads:
            t.join(timeout=30)

        for idx, err in enumerate(prepare_errors):
            if err:
                dl = task_list[idx]["device_label"]
                self.log_message.emit(f"[ERROR] Prepare force high failed on {dl}: {err}")

        active_tasks = [t for i, t in enumerate(task_list) if prepare_errors[i] is None]

        for task in active_tasks:
            mv = task.get("measured_voltages") or {}
            for ch, v in mv.items():
                channel_voltages[(task["device_label"], ch)] = v

        if not active_tasks:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        self.log_message.emit("[TEST] Configuring datalog on all instruments...")
        for task in active_tasks:
            try:
                task["inst"].configure_datalog(
                    task["all_datalog_channels"], self.test_time, task["sample_period"]
                )
            except Exception as e:
                task["error"] = str(e)
                self.log_message.emit(f"[ERROR] Configure datalog failed on {task['device_label']}: {e}")

        active_tasks = [t for t in active_tasks if t["error"] is None]
        if not active_tasks:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        barrier = threading.Barrier(len(active_tasks), timeout=30)
        init_errors = [None] * len(active_tasks)

        def start_datalog_worker(idx, task):
            try:
                barrier.wait()
                task["inst"].start_datalog()
            except Exception as e:
                init_errors[idx] = e

        self.log_message.emit(f"[TEST] Sync-starting datalog on {len(active_tasks)} instrument(s)...")
        logger.debug("ForceHighWorker: sync-starting datalog on %d instruments", len(active_tasks))
        start_threads = []
        for idx, task in enumerate(active_tasks):
            t = threading.Thread(target=start_datalog_worker, args=(idx, task), daemon=True)
            start_threads.append(t)
        for t in start_threads:
            t.start()
        for t in start_threads:
            t.join(timeout=30)

        for idx, err in enumerate(init_errors):
            if err:
                dl = active_tasks[idx]["device_label"]
                self.log_message.emit(f"[ERROR] Start datalog failed on {dl}: {err}")

        import time as _time
        datalog_wait = self.test_time + 1
        total_wait_est = datalog_wait + 3.0
        wait_progress_span = datalog_wait / total_wait_est * step2_time
        interval = 0.5
        elapsed = 0.0
        while elapsed < datalog_wait:
            if self._is_stopped:
                return
            step = min(interval, datalog_wait - elapsed)
            _time.sleep(step)
            elapsed += step
            frac = min(elapsed / datalog_wait, 1.0)
            self.progress.emit(min((cursor + frac * wait_progress_span) / total_est, 1.0))
        if self._is_stopped:
            return

        self.log_message.emit("[TEST] Fetching results from all instruments...")
        fetch_errors = [None] * len(active_tasks)

        def fetch_worker(idx, task):
            try:
                task["curr_result"] = task["inst"].fetch_datalog_marker_results(
                    task["all_datalog_channels"], self.test_time
                )
            except Exception as e:
                fetch_errors[idx] = e

        fetch_threads = []
        for idx, task in enumerate(active_tasks):
            t = threading.Thread(target=fetch_worker, args=(idx, task), daemon=True)
            fetch_threads.append(t)
        for t in fetch_threads:
            t.start()
        for t in fetch_threads:
            t.join(timeout=30)

        for task in active_tasks:
            task["inst"].restore_channels_to_vmeter(task["force_channels"])

        cursor = setup_time + step1_time + step2_time
        self.progress.emit(min(cursor / total_est, 1.0))

        for idx, task in enumerate(active_tasks):
            if fetch_errors[idx]:
                self.log_message.emit(
                    f"[ERROR] Fetch failed on {task['device_label']}: {fetch_errors[idx]}"
                )
                continue
            cr = task["curr_result"] or {}
            for ch in task["force_channels"]:
                avg_i = cr.get(ch, 0.0)
                logger.debug("ForceHighWorker result: %s CH%s = %.6e A", task["device_label"], ch, avg_i)
                self.channel_result.emit(task["device_label"], ch, float(avg_i), "force_high")
                results[(task["device_label"], ch)] = float(avg_i)
            if task["device_label"] == vbat_label and vbat_ch in cr:
                vbat_remain = float(cr[vbat_ch])

        self.progress.emit(1.0)
        self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
        self.log_message.emit("[TEST] Force high consumption test completed.")

    def _emit_summary(self, results, vbat_current, vbat_remain, channel_voltages=None):
        if channel_voltages is None:
            channel_voltages = {}
        vbat_name = self.channel_names.get(
            (self.vbat_device_label, self.vbat_hw_ch), "Vbat"
        )
        parts = [f"{vbat_name}: {_format_current_unified(vbat_current)}"]
        ordered_keys = []
        for device_label, (n6705c_inst, hw_channels) in self.force_high_map.items():
            for ch in hw_channels:
                ordered_keys.append((device_label, ch))
        for key in ordered_keys:
            name = self.channel_names.get(key, f"{key[0]}-CH{key[1]}")
            val = results.get(key, 0.0)
            parts.append(f"{name}: {_format_current_unified(val)}")
        if vbat_remain is not None:
            parts.append(f"Vbat_remain: {_format_current_unified(vbat_remain)}")

        summary_line = " | ".join(parts)
        self.log_message.emit(f"[RESULT] {summary_line}")

        voltage_parts = []
        vbat_v = channel_voltages.get((self.vbat_device_label, self.vbat_hw_ch))
        if vbat_v is not None:
            voltage_parts.append(f"{vbat_name}={vbat_v:.4g}V")
        for key in ordered_keys:
            v = channel_voltages.get(key)
            if v is not None:
                name = self.channel_names.get(key, f"{key[0]}-CH{key[1]}")
                voltage_parts.append(f"{name}={v:.4g}V")
        if voltage_parts:
            self.log_message.emit(f"[VOLTAGE] {', '.join(voltage_parts)}")

        summary = {
            "vbat": vbat_current,
            "channels": {k: results[k] for k in ordered_keys if k in results},
            "vbat_remain": vbat_remain,
            "channel_voltages": channel_voltages,
        }
        self.test_summary.emit(summary)

    @staticmethod
    def _format_current_short(current_A):
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.4f}A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.4f}mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.4f}uA"
        else:
            return f"{current_A*1e9:.4f}nA"


class _ConsumptionTestForceWorker(QObject):
    log_message = Signal(str)
    channel_result = Signal(str, int, float, str)
    test_summary = Signal(dict)
    progress = Signal(float)
    finished = Signal()
    error = Signal(str)

    def __init__(self, vbat_device_label, vbat_inst, vbat_hw_ch,
                 force_map, test_time, sample_period,
                 channel_names=None):
        super().__init__()
        self.vbat_device_label = vbat_device_label
        self.vbat_inst = vbat_inst
        self.vbat_hw_ch = vbat_hw_ch
        self.force_map = force_map
        self.test_time = test_time
        self.sample_period = sample_period
        self.channel_names = channel_names or {}
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            self._consumption_test_force()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @staticmethod
    def _estimate_datalog_time(test_time):
        return test_time + 4.0

    @staticmethod
    def _estimate_force_time(test_time):
        return test_time + 5.0

    def _make_sub_progress(self, base, span, total_est):
        def _on_progress(frac):
            self.progress.emit(min((base + frac * span) / total_est, 1.0))
        return _on_progress

    def _consumption_test_force(self):
        import threading

        vbat_ch = self.vbat_hw_ch
        vbat_inst = self.vbat_inst
        vbat_label = self.vbat_device_label

        setup_time = 1.0
        step1_time = self._estimate_datalog_time(self.test_time)
        step2_time = self._estimate_force_time(self.test_time)

        total_est = setup_time + step1_time + step2_time
        if total_est <= 0:
            total_est = 1.0

        cursor = 0.0
        self.progress.emit(0.0)
        stop_check = lambda: self._is_stopped

        results = {}
        vbat_remain = None

        self.log_message.emit("[TEST] Resetting sub-channels to VMeter mode...")
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                try:
                    n6705c_inst.set_mode(ch, "VMETer")
                    n6705c_inst.channel_on(ch)
                except Exception as e:
                    self.log_message.emit(f"[WARNING] Failed to set {device_label}-CH{ch} to VMeter: {e}")
        cursor = setup_time
        self.progress.emit(cursor / total_est)

        self.log_message.emit(f"[TEST] Measuring Vbat (CH{vbat_ch}) total current...")
        vbat_period = self.sample_period
        vbat_result = vbat_inst.fetch_current_by_datalog(
            [vbat_ch], self.test_time, vbat_period,
            on_progress=self._make_sub_progress(cursor, step1_time, total_est),
            stop_check=stop_check,
        )
        cursor += step1_time
        self.progress.emit(min(cursor / total_est, 1.0))
        if self._is_stopped:
            return
        vbat_current = vbat_result.get(vbat_ch, 0.0)
        self.channel_result.emit(vbat_label, vbat_ch, float(vbat_current), "vbat")
        results[(vbat_label, vbat_ch)] = float(vbat_current)

        channel_voltages = {}
        try:
            vbat_v = float(vbat_inst.measure_voltage(vbat_ch))
            channel_voltages[(vbat_label, vbat_ch)] = vbat_v
        except Exception:
            channel_voltages[(vbat_label, vbat_ch)] = 0.0

        self.log_message.emit("[TEST] Force auto on sub-channels (align voltage) — parallel sync...")

        task_list = []
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            monitor_chs = []
            if device_label == vbat_label and vbat_ch not in hw_channels:
                monitor_chs.append(vbat_ch)
            all_datalog_chs = list(hw_channels) + [ch for ch in monitor_chs if ch not in hw_channels]
            num_ch = len(all_datalog_chs)
            ch_period = self.sample_period * num_ch
            task_list.append({
                "device_label": device_label,
                "inst": n6705c_inst,
                "force_channels": list(hw_channels),
                "monitor_channels": monitor_chs,
                "all_datalog_channels": all_datalog_chs,
                "sample_period": ch_period,
                "measured_voltages": None,
                "curr_result": None,
                "error": None,
            })

        if not task_list:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        self.log_message.emit("[TEST] Preparing force auto on all instruments...")
        prepare_errors = [None] * len(task_list)

        def prepare_worker(idx, task):
            try:
                mv = task["inst"].prepare_force_auto(
                    task["force_channels"],
                    current_limit=1.0,
                    monitor_channels=task["monitor_channels"],
                )
                task["measured_voltages"] = mv
            except Exception as e:
                prepare_errors[idx] = e

        prepare_threads = []
        for idx, task in enumerate(task_list):
            t = threading.Thread(target=prepare_worker, args=(idx, task), daemon=True)
            prepare_threads.append(t)
        for t in prepare_threads:
            t.start()
        for t in prepare_threads:
            t.join(timeout=30)

        for idx, err in enumerate(prepare_errors):
            if err:
                dl = task_list[idx]["device_label"]
                self.log_message.emit(f"[ERROR] Prepare force auto failed on {dl}: {err}")

        active_tasks = [t for i, t in enumerate(task_list) if prepare_errors[i] is None]

        for task in active_tasks:
            mv = task.get("measured_voltages") or {}
            for ch, v in mv.items():
                channel_voltages[(task["device_label"], ch)] = v

        if not active_tasks:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        self.log_message.emit("[TEST] Configuring datalog on all instruments...")
        for task in active_tasks:
            try:
                task["inst"].configure_datalog(
                    task["all_datalog_channels"], self.test_time, task["sample_period"]
                )
            except Exception as e:
                task["error"] = str(e)
                self.log_message.emit(f"[ERROR] Configure datalog failed on {task['device_label']}: {e}")

        active_tasks = [t for t in active_tasks if t["error"] is None]
        if not active_tasks:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        barrier = threading.Barrier(len(active_tasks), timeout=30)
        init_errors = [None] * len(active_tasks)

        def start_datalog_worker(idx, task):
            try:
                barrier.wait()
                task["inst"].start_datalog()
            except Exception as e:
                init_errors[idx] = e

        self.log_message.emit(f"[TEST] Sync-starting datalog on {len(active_tasks)} instrument(s)...")
        start_threads = []
        for idx, task in enumerate(active_tasks):
            t = threading.Thread(target=start_datalog_worker, args=(idx, task), daemon=True)
            start_threads.append(t)
        for t in start_threads:
            t.start()
        for t in start_threads:
            t.join(timeout=30)

        for idx, err in enumerate(init_errors):
            if err:
                dl = active_tasks[idx]["device_label"]
                self.log_message.emit(f"[ERROR] Start datalog failed on {dl}: {err}")

        import time as _time
        datalog_wait = self.test_time + 1
        total_wait_est = datalog_wait + 3.0
        wait_progress_span = datalog_wait / total_wait_est * step2_time
        interval = 0.5
        elapsed = 0.0
        while elapsed < datalog_wait:
            if self._is_stopped:
                return
            step = min(interval, datalog_wait - elapsed)
            _time.sleep(step)
            elapsed += step
            frac = min(elapsed / datalog_wait, 1.0)
            self.progress.emit(min((cursor + frac * wait_progress_span) / total_est, 1.0))
        if self._is_stopped:
            return

        self.log_message.emit("[TEST] Fetching results from all instruments...")
        fetch_errors = [None] * len(active_tasks)

        def fetch_worker(idx, task):
            try:
                task["curr_result"] = task["inst"].fetch_datalog_marker_results(
                    task["all_datalog_channels"], self.test_time
                )
            except Exception as e:
                fetch_errors[idx] = e

        fetch_threads = []
        for idx, task in enumerate(active_tasks):
            t = threading.Thread(target=fetch_worker, args=(idx, task), daemon=True)
            fetch_threads.append(t)
        for t in fetch_threads:
            t.start()
        for t in fetch_threads:
            t.join(timeout=30)

        for task in active_tasks:
            task["inst"].restore_channels_to_vmeter(task["force_channels"])

        cursor = setup_time + step1_time + step2_time
        self.progress.emit(min(cursor / total_est, 1.0))

        for idx, task in enumerate(active_tasks):
            if fetch_errors[idx]:
                self.log_message.emit(
                    f"[ERROR] Fetch failed on {task['device_label']}: {fetch_errors[idx]}"
                )
                continue
            cr = task["curr_result"] or {}
            for ch in task["force_channels"]:
                avg_i = cr.get(ch, 0.0)
                self.channel_result.emit(task["device_label"], ch, float(avg_i), "force_auto")
                results[(task["device_label"], ch)] = float(avg_i)
            if task["device_label"] == vbat_label and vbat_ch in cr:
                vbat_remain = float(cr[vbat_ch])

        self.progress.emit(1.0)
        self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
        self.log_message.emit("[TEST] Force auto consumption test completed.")

    def _emit_summary(self, results, vbat_current, vbat_remain, channel_voltages=None):
        if channel_voltages is None:
            channel_voltages = {}
        vbat_name = self.channel_names.get(
            (self.vbat_device_label, self.vbat_hw_ch), "Vbat"
        )
        parts = [f"{vbat_name}: {_format_current_unified(vbat_current)}"]
        ordered_keys = []
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                ordered_keys.append((device_label, ch))
        for key in ordered_keys:
            name = self.channel_names.get(key, f"{key[0]}-CH{key[1]}")
            val = results.get(key, 0.0)
            parts.append(f"{name}: {_format_current_unified(val)}")
        if vbat_remain is not None:
            parts.append(f"Vbat_remain: {_format_current_unified(vbat_remain)}")

        summary_line = " | ".join(parts)
        self.log_message.emit(f"[RESULT] {summary_line}")

        voltage_parts = []
        vbat_v = channel_voltages.get((self.vbat_device_label, self.vbat_hw_ch))
        if vbat_v is not None:
            voltage_parts.append(f"{vbat_name}={vbat_v:.4g}V")
        for key in ordered_keys:
            v = channel_voltages.get(key)
            if v is not None:
                name = self.channel_names.get(key, f"{key[0]}-CH{key[1]}")
                voltage_parts.append(f"{name}={v:.4g}V")
        if voltage_parts:
            self.log_message.emit(f"[VOLTAGE] {', '.join(voltage_parts)}")

        summary = {
            "vbat": vbat_current,
            "channels": {k: results[k] for k in ordered_keys if k in results},
            "vbat_remain": vbat_remain,
            "channel_voltages": channel_voltages,
        }
        self.test_summary.emit(summary)

    @staticmethod
    def _format_current_short(current_A):
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.4f}A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.4f}mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.4f}uA"
        else:
            return f"{current_A*1e9:.4f}nA"


class _AutoTestWorker(QObject):
    log_message = Signal(str)
    channel_result = Signal(str, int, float, str)
    test_summary = Signal(dict)
    progress = Signal(float)
    download_state_changed = Signal(str)
    download_finished = Signal(object)
    download_error = Signal(str)
    finished = Signal()
    error = Signal(str)

    _AUTO_SET_SPECIAL_VOLTAGES = [0.625, 0.67, 0.725, 0.78]

    def __init__(self, com_port, firmware_paths, download_mode,
                 poweron_device_label, poweron_inst, poweron_hw_ch, poweron_polarity,
                 reset_device_label, reset_inst, reset_hw_ch, reset_polarity,
                 vbat_device_label, vbat_inst, vbat_hw_ch,
                 force_map, test_time, sample_period,
                 channel_names=None,
                 chip_combo_text=None, selected_chip_config=None,
                 config_text=None, parse_config_commands_fn=None,
                 resolve_device_fn=None):
        super().__init__()
        self.com_port = com_port
        self.firmware_paths = list(firmware_paths)
        self.download_mode = download_mode
        self.poweron_device_label = poweron_device_label
        self.poweron_inst = poweron_inst
        self.poweron_hw_ch = poweron_hw_ch
        self.poweron_polarity = poweron_polarity
        self.reset_device_label = reset_device_label
        self.reset_inst = reset_inst
        self.reset_hw_ch = reset_hw_ch
        self.reset_polarity = reset_polarity
        self.vbat_device_label = vbat_device_label
        self.vbat_inst = vbat_inst
        self.vbat_hw_ch = vbat_hw_ch
        self.force_map = force_map
        self.test_time = test_time
        self.sample_period = sample_period
        self.channel_names = channel_names or {}
        self.chip_combo_text = chip_combo_text
        self.selected_chip_config = selected_chip_config
        self.config_text = config_text or ""
        self._parse_config_commands_fn = parse_config_commands_fn
        self._resolve_device_fn = resolve_device_fn
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            self._auto_test()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @staticmethod
    def _align_voltage(v, special_values=None):
        if special_values is None:
            special_values = _AutoTestWorker._AUTO_SET_SPECIAL_VOLTAGES
        grid_v = round(round(v / 0.05) * 0.05, 4)
        best = grid_v
        best_dist = abs(v - grid_v)
        for sv in special_values:
            dist = abs(v - sv)
            if dist < best_dist:
                best = sv
                best_dist = dist
        return best

    def _toggle_signal(self, inst, hw_ch, polarity):
        import time as _time
        if polarity == "rising":
            active_v = 2.3
            inactive_v = 0.1
        else:
            active_v = 0.1
            inactive_v = 2.3
        inst.set_voltage(hw_ch, active_v)
        _time.sleep(0.1)
        inst.set_voltage(hw_ch, inactive_v)

    def _setup_control_channel(self, inst, hw_ch, polarity):
        if polarity == "rising":
            v = 0.1
        else:
            v = 2.3
        inst.set_mode(hw_ch, "PS2Q")
        inst.set_voltage(hw_ch, v)
        inst.set_current_limit(hw_ch, 0.2)
        inst.channel_on(hw_ch)

    def _auto_test(self):
        import time as _time
        import threading

        total_bins = len(self.firmware_paths)
        if total_bins == 0:
            self.error.emit("No firmware files provided.")
            return

        all_bin_results = []

        for bin_idx, bin_path in enumerate(self.firmware_paths):
            if self._is_stopped:
                return

            bin_name = os.path.basename(bin_path)
            bin_progress_base = bin_idx / total_bins
            bin_progress_span = 1.0 / total_bins
            self.log_message.emit(f"[AUTO_TEST] === BIN {bin_idx+1}/{total_bins}: {bin_name} ===")

            self.log_message.emit("[AUTO_TEST] Step 1: Configuring PowerON and RESET channels...")
            self._setup_control_channel(
                self.poweron_inst, self.poweron_hw_ch, self.poweron_polarity
            )
            self._setup_control_channel(
                self.reset_inst, self.reset_hw_ch, self.reset_polarity
            )
            self.progress.emit(bin_progress_base + 0.02 * bin_progress_span)

            if self._is_stopped:
                return

            self.log_message.emit("[AUTO_TEST] Step 2: Configuring Vbat channel (3.8V, 0.2A)...")
            self.vbat_inst.set_mode(self.vbat_hw_ch, "PS2Q")
            self.vbat_inst.set_voltage(self.vbat_hw_ch, 3.8)
            self.vbat_inst.set_current_limit(self.vbat_hw_ch, 0.2)
            self.vbat_inst.channel_on(self.vbat_hw_ch)
            _time.sleep(0.5)
            self.progress.emit(bin_progress_base + 0.04 * bin_progress_span)

            if self._is_stopped:
                return

            self.log_message.emit(f"[AUTO_TEST] Step 3: Starting download listener: {bin_name}")
            chip = detect_chip_from_bin(bin_path)
            detected_chip_name = None
            if chip:
                self.log_message.emit(f"[AUTO_TEST] Detected chip from BIN: {chip}")
                detected_chip_name = f"bes{chip.lower()}"

            download_thread, result_queue = self._start_download_async(bin_path)
            _time.sleep(1.0)

            self.log_message.emit("[AUTO_TEST] Step 4: Triggering RESET then POWERON for download handshake...")
            self._toggle_signal(self.reset_inst, self.reset_hw_ch, self.reset_polarity)
            _time.sleep(0.05)
            self._toggle_signal(self.poweron_inst, self.poweron_hw_ch, self.poweron_polarity)

            self.log_message.emit("[AUTO_TEST] Waiting for download to complete...")
            download_thread.join(timeout=180)
            download_result = None
            try:
                download_result = result_queue.get_nowait()
            except Exception:
                pass
            self.progress.emit(bin_progress_base + 0.30 * bin_progress_span)

            if self._is_stopped:
                return

            if download_result is None or not download_result.success:
                err_msg = "Unknown error"
                if download_result and download_result.error_message:
                    err_msg = download_result.error_message
                self.log_message.emit(f"[AUTO_TEST] Download failed: {err_msg}")
                self.error.emit(f"Download failed for {bin_name}: {err_msg}")
                return

            self.log_message.emit("[AUTO_TEST] Step 5: Download completed successfully.")

            if self._is_stopped:
                return

            self.log_message.emit("[AUTO_TEST] Step 6: Sending POWERON then RESET to boot chip...")
            self._toggle_signal(self.poweron_inst, self.poweron_hw_ch, self.poweron_polarity)
            _time.sleep(0.05)
            self._toggle_signal(self.reset_inst, self.reset_hw_ch, self.reset_polarity)
            self.log_message.emit("[AUTO_TEST] Waiting 2s for chip stabilization...")
            _time.sleep(2.0)
            self.progress.emit(bin_progress_base + 0.35 * bin_progress_span)

            if self._is_stopped:
                return

            self.log_message.emit("[AUTO_TEST] Step 7: Measuring Vbat total current...")
            vbat_period = self.sample_period
            stop_check = lambda: self._is_stopped
            vbat_result = self.vbat_inst.fetch_current_by_datalog(
                [self.vbat_hw_ch], self.test_time, vbat_period,
                stop_check=stop_check,
            )
            if self._is_stopped:
                return
            vbat_current = vbat_result.get(self.vbat_hw_ch, 0.0)
            self.channel_result.emit(
                self.vbat_device_label, self.vbat_hw_ch, float(vbat_current), "vbat"
            )
            self.log_message.emit(
                f"[AUTO_TEST] Vbat total current: "
                f"{_format_current_unified(vbat_current)}"
            )
            self.progress.emit(bin_progress_base + 0.50 * bin_progress_span)

            if self._is_stopped:
                return

            self.log_message.emit("[AUTO_TEST] Step 8: Recording default sub-channel voltages...")
            default_voltages = {}
            for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
                for ch in hw_channels:
                    try:
                        n6705c_inst.set_mode(ch, "VMETer")
                        n6705c_inst.channel_on(ch)
                    except Exception as e:
                        self.log_message.emit(f"[WARNING] Failed to set {device_label}-CH{ch} to VMeter: {e}")
            _time.sleep(0.5)
            for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
                for ch in hw_channels:
                    try:
                        v = float(n6705c_inst.measure_voltage(ch))
                        default_voltages[(device_label, ch)] = v
                        self.log_message.emit(
                            f"[AUTO_TEST]   {self.channel_names.get((device_label, ch), f'{device_label}-CH{ch}')}: {v:.4f}V"
                        )
                    except Exception as e:
                        self.log_message.emit(f"[WARNING] Failed to measure {device_label}-CH{ch}: {e}")
                        default_voltages[(device_label, ch)] = 0.0

            original_registers = {}
            chip_config = self.selected_chip_config
            if detected_chip_name:
                refreshed = get_chip_config(detected_chip_name, force_reload=True)
                if refreshed:
                    chip_config = refreshed
                    self.log_message.emit(f"[AUTO_TEST] Using chip config for: {detected_chip_name}")

            config_commands = None
            if self.config_text:
                config_commands = self._parse_config_commands_fn(self.config_text)
                self.log_message.emit(f"[AUTO_TEST] Using pasted configuration ({len(config_commands)} commands)")
            elif chip_config:
                pd = chip_config.get("power_distribution")
                if pd and isinstance(pd, dict) and len(pd) > 0:
                    raw_lines = []
                    for section, cmds in pd.items():
                        if isinstance(cmds, list):
                            raw_lines.extend(cmds)
                    config_commands = self._parse_config_commands_fn("\n".join(raw_lines))
                    self.log_message.emit(
                        f"[AUTO_TEST] Using chip config power_distribution ({len(config_commands)} commands)"
                    )

            if config_commands:
                self.log_message.emit("[AUTO_TEST] Step 8 (cont.): Recording original register values...")
                try:
                    from lib.i2c.i2c_interface_x64 import I2CInterface
                    i2c = I2CInterface()
                    if not i2c.initialize():
                        self.log_message.emit("[ERROR] I2C interface initialization failed.")
                        config_commands = None
                    else:
                        chip_info = i2c.bes_chip_check()
                        self.log_message.emit(f"[AUTO_TEST] Chip detected via I2C: {chip_info.get('chip_name', 'N/A')}")
                        for cmd in config_commands:
                            if cmd["op"] in ("WRITE", "WRITE_BITS"):
                                target = cmd.get("target", "NO_PREFIX")
                                reg_addr = cmd["reg_addr"]
                                device_addr, width = self._resolve_device_fn(chip_info, target)
                                if device_addr is not None and width is not None:
                                    key = (device_addr, reg_addr, width)
                                    if key not in original_registers:
                                        try:
                                            val = i2c.read(device_addr, reg_addr, width)
                                            original_registers[key] = val
                                            self.log_message.emit(
                                                f"[AUTO_TEST]   Saved reg dev=0x{device_addr:02X} "
                                                f"addr=0x{reg_addr:08X} = 0x{val:X}"
                                            )
                                        except Exception as e:
                                            self.log_message.emit(
                                                f"[WARNING] Failed to read reg 0x{reg_addr:08X}: {e}"
                                            )
                except Exception as e:
                    self.log_message.emit(f"[ERROR] I2C setup failed: {e}")
                    config_commands = None

            self.progress.emit(bin_progress_base + 0.55 * bin_progress_span)

            if self._is_stopped:
                return

            self.log_message.emit("[AUTO_TEST] Step 9: Setting sub-channels to default voltage + 20mV...")
            for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
                for ch in hw_channels:
                    try:
                        v_default = default_voltages.get((device_label, ch), 0.0)
                        v_plus20 = v_default + 0.02
                        n6705c_inst.set_mode(ch, "PS2Q")
                        n6705c_inst.set_voltage(ch, v_plus20)
                        n6705c_inst.set_current_limit(ch, 0.02)
                        n6705c_inst.channel_on(ch)
                        final_limit = 0.07 if v_plus20 < 1.0 else 0.15
                        n6705c_inst.set_current_limit(ch, final_limit)
                        ch_name = self.channel_names.get((device_label, ch), f"{device_label}-CH{ch}")
                        self.log_message.emit(f"[AUTO_TEST]   {ch_name}: {v_default:.4f}V -> {v_plus20:.4f}V (+20mV)")
                    except Exception as e:
                        self.log_message.emit(f"[ERROR] Failed to set {device_label}-CH{ch}: {e}")

            self.progress.emit(bin_progress_base + 0.58 * bin_progress_span)

            if self._is_stopped:
                return

            if config_commands and i2c:
                self.log_message.emit("[AUTO_TEST] Step 10: Executing configuration commands...")
                try:
                    for idx_cmd, cmd in enumerate(config_commands):
                        op = cmd["op"]
                        target = cmd.get("target", "NO_PREFIX")
                        reg_addr = cmd["reg_addr"]
                        device_addr, width = self._resolve_device_fn(chip_info, target)
                        if device_addr is None or width is None:
                            self.log_message.emit(
                                f"[ERROR] Cannot resolve device for target={target}, skip cmd #{idx_cmd+1}"
                            )
                            continue
                        if op == "WRITE_BITS":
                            msb = cmd["msb"]
                            lsb = cmd["lsb"]
                            value = cmd["value"]
                            current_val = i2c.read(device_addr, reg_addr, width)
                            bit_mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                            new_val = (current_val & ~bit_mask) | ((value << lsb) & bit_mask)
                            i2c.write(device_addr, reg_addr, new_val, width)
                            self.log_message.emit(
                                f"[AUTO_TEST]   #{idx_cmd+1} WRITE_BITS dev=0x{device_addr:02X} "
                                f"reg=0x{reg_addr:08X} [{msb}:{lsb}]=0x{value:X} "
                                f"(0x{current_val:X} -> 0x{new_val:X})"
                            )
                        elif op == "WRITE":
                            value = cmd["value"]
                            i2c.write(device_addr, reg_addr, value, width)
                            self.log_message.emit(
                                f"[AUTO_TEST]   #{idx_cmd+1} WRITE dev=0x{device_addr:02X} "
                                f"reg=0x{reg_addr:08X} data=0x{value:X}"
                            )
                        elif op == "READ":
                            read_val = i2c.read(device_addr, reg_addr, width)
                            self.log_message.emit(
                                f"[AUTO_TEST]   #{idx_cmd+1} READ dev=0x{device_addr:02X} "
                                f"reg=0x{reg_addr:08X} => 0x{read_val:X}"
                            )
                except Exception as e:
                    self.log_message.emit(f"[ERROR] Config execution failed: {e}")

            self.progress.emit(bin_progress_base + 0.62 * bin_progress_span)

            if self._is_stopped:
                return

            self.log_message.emit("[AUTO_TEST] Step 11: Adjusting sub-channels with Auto Set logic (using Step 8 voltages)...")
            for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
                for ch in hw_channels:
                    try:
                        v_default = default_voltages.get((device_label, ch), 0.0)
                        new_v = self._align_voltage(v_default)
                        n6705c_inst.set_mode(ch, "PS2Q")
                        n6705c_inst.set_voltage(ch, new_v)
                        n6705c_inst.set_current_limit(ch, 0.02)
                        n6705c_inst.channel_on(ch)
                        final_limit = 0.07 if new_v < 1.0 else 0.15
                        n6705c_inst.set_current_limit(ch, final_limit)
                        ch_name = self.channel_names.get((device_label, ch), f"{device_label}-CH{ch}")
                        self.log_message.emit(f"[AUTO_TEST]   {ch_name}: default={v_default:.4f}V -> aligned={new_v:.4f}V")
                    except Exception as e:
                        self.log_message.emit(f"[ERROR] Auto set failed {device_label}-CH{ch}: {e}")

            self.progress.emit(bin_progress_base + 0.65 * bin_progress_span)

            if self._is_stopped:
                return

            self.log_message.emit("[AUTO_TEST] Step 12: Running sub-channel consumption test...")
            results = {(self.vbat_device_label, self.vbat_hw_ch): float(vbat_current)}
            vbat_remain = None

            task_list = []
            vbat_label = self.vbat_device_label
            vbat_ch = self.vbat_hw_ch
            for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
                monitor_chs = []
                if device_label == vbat_label and vbat_ch not in hw_channels:
                    monitor_chs.append(vbat_ch)
                all_datalog_chs = list(hw_channels) + [c for c in monitor_chs if c not in hw_channels]
                num_ch = len(all_datalog_chs)
                ch_period = self.sample_period * num_ch
                task_list.append({
                    "device_label": device_label,
                    "inst": n6705c_inst,
                    "force_channels": list(hw_channels),
                    "monitor_channels": monitor_chs,
                    "all_datalog_channels": all_datalog_chs,
                    "sample_period": ch_period,
                    "curr_result": None,
                    "error": None,
                })

            if task_list:
                self.log_message.emit("[AUTO_TEST] Configuring datalog on instruments...")
                for task in task_list:
                    try:
                        task["inst"].configure_datalog(
                            task["all_datalog_channels"], self.test_time, task["sample_period"]
                        )
                    except Exception as e:
                        task["error"] = str(e)
                        self.log_message.emit(f"[ERROR] Configure datalog failed on {task['device_label']}: {e}")

                active_tasks = [t for t in task_list if t["error"] is None]

                if active_tasks:
                    barrier = threading.Barrier(len(active_tasks), timeout=30)
                    init_errors = [None] * len(active_tasks)

                    def start_datalog_worker(idx_t, task_t):
                        try:
                            barrier.wait()
                            task_t["inst"].start_datalog()
                        except Exception as exc:
                            init_errors[idx_t] = exc

                    start_threads = []
                    for idx_t, task_t in enumerate(active_tasks):
                        t = threading.Thread(target=start_datalog_worker, args=(idx_t, task_t), daemon=True)
                        start_threads.append(t)
                    for t in start_threads:
                        t.start()
                    for t in start_threads:
                        t.join(timeout=30)

                    datalog_wait = self.test_time + 1
                    interval = 0.5
                    elapsed = 0.0
                    while elapsed < datalog_wait:
                        if self._is_stopped:
                            return
                        step = min(interval, datalog_wait - elapsed)
                        _time.sleep(step)
                        elapsed += step
                        frac = min(elapsed / datalog_wait, 1.0)
                        self.progress.emit(
                            bin_progress_base + (0.65 + frac * 0.25) * bin_progress_span
                        )
                    if self._is_stopped:
                        return

                    self.log_message.emit("[AUTO_TEST] Fetching results...")
                    fetch_errors = [None] * len(active_tasks)

                    def fetch_worker(idx_f, task_f):
                        try:
                            task_f["curr_result"] = task_f["inst"].fetch_datalog_marker_results(
                                task_f["all_datalog_channels"], self.test_time
                            )
                        except Exception as exc:
                            fetch_errors[idx_f] = exc

                    fetch_threads = []
                    for idx_f, task_f in enumerate(active_tasks):
                        t = threading.Thread(target=fetch_worker, args=(idx_f, task_f), daemon=True)
                        fetch_threads.append(t)
                    for t in fetch_threads:
                        t.start()
                    for t in fetch_threads:
                        t.join(timeout=30)

                    for idx_f, task_f in enumerate(active_tasks):
                        if fetch_errors[idx_f]:
                            self.log_message.emit(
                                f"[ERROR] Fetch failed on {task_f['device_label']}: {fetch_errors[idx_f]}"
                            )
                            continue
                        cr = task_f["curr_result"] or {}
                        for ch in task_f["force_channels"]:
                            avg_i = cr.get(ch, 0.0)
                            self.channel_result.emit(task_f["device_label"], ch, float(avg_i), "force_auto")
                            results[(task_f["device_label"], ch)] = float(avg_i)
                        if task_f["device_label"] == vbat_label and vbat_ch in cr:
                            vbat_remain = float(cr[vbat_ch])

            self.progress.emit(bin_progress_base + 0.92 * bin_progress_span)

            if self._is_stopped:
                return

            if config_commands and original_registers and i2c:
                self.log_message.emit("[AUTO_TEST] Step 13: Restoring original register values...")
                for (device_addr, reg_addr, width), orig_val in original_registers.items():
                    try:
                        i2c.write(device_addr, reg_addr, orig_val, width)
                        self.log_message.emit(
                            f"[AUTO_TEST]   Restored dev=0x{device_addr:02X} "
                            f"reg=0x{reg_addr:08X} = 0x{orig_val:X}"
                        )
                    except Exception as e:
                        self.log_message.emit(
                            f"[WARNING] Failed to restore reg 0x{reg_addr:08X}: {e}"
                        )

            self.log_message.emit("[AUTO_TEST] Step 14: Restoring sub-channels to VMeter mode...")
            for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
                n6705c_inst.restore_channels_to_vmeter(hw_channels)

            channel_voltages = {}
            try:
                vbat_v = float(self.vbat_inst.measure_voltage(self.vbat_hw_ch))
            except Exception:
                vbat_v = 3.8
            channel_voltages[(self.vbat_device_label, self.vbat_hw_ch)] = vbat_v
            for key, v in default_voltages.items():
                channel_voltages[key] = v

            self._emit_summary(results, vbat_current, vbat_remain, bin_name, channel_voltages)
            all_bin_results.append({
                "bin_name": bin_name,
                "vbat": vbat_current,
                "channels": dict(results),
                "vbat_remain": vbat_remain,
                "channel_voltages": channel_voltages,
            })
            self.progress.emit(bin_progress_base + bin_progress_span)
            self.log_message.emit(f"[AUTO_TEST] === BIN {bin_idx+1}/{total_bins}: {bin_name} completed ===")

        self.progress.emit(1.0)
        if len(all_bin_results) > 1:
            self._emit_final_summary_table(all_bin_results)
        self.log_message.emit("[AUTO_TEST] All auto test completed.")

    def _start_download_async(self, bin_path):
        import queue
        import threading
        result_queue = queue.Queue()

        def _download_thread_fn():
            try:
                def _on_state(state):
                    self.download_state_changed.emit(state.value)
                result = download_bin(
                    com_port=self.com_port,
                    bin_file=bin_path,
                    mode=self.download_mode,
                    timeout=120,
                    on_state_change=_on_state,
                )
                result_queue.put(result)
            except Exception as e:
                self.download_error.emit(str(e))
                result_queue.put(None)

        t = threading.Thread(target=_download_thread_fn, daemon=True)
        t.start()
        return t, result_queue

    def _run_download(self, bin_path):
        import queue
        result_queue = queue.Queue()

        def _download_thread_fn():
            try:
                def _on_state(state):
                    self.download_state_changed.emit(state.value)
                result = download_bin(
                    com_port=self.com_port,
                    bin_file=bin_path,
                    mode=self.download_mode,
                    timeout=120,
                    on_state_change=_on_state,
                )
                result_queue.put(result)
            except Exception as e:
                self.download_error.emit(str(e))
                result_queue.put(None)

        import threading
        t = threading.Thread(target=_download_thread_fn, daemon=True)
        t.start()
        t.join(timeout=180)
        try:
            return result_queue.get_nowait()
        except queue.Empty:
            return None

    def _emit_summary(self, results, vbat_current, vbat_remain, bin_name="", channel_voltages=None):
        if channel_voltages is None:
            channel_voltages = {}
        vbat_name = self.channel_names.get(
            (self.vbat_device_label, self.vbat_hw_ch), "Vbat"
        )
        parts = [f"{vbat_name}: {_format_current_unified(vbat_current)}"]
        ordered_keys = []
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                ordered_keys.append((device_label, ch))
        for key in ordered_keys:
            name = self.channel_names.get(key, f"{key[0]}-CH{key[1]}")
            val = results.get(key, 0.0)
            parts.append(f"{name}: {_format_current_unified(val)}")
        if vbat_remain is not None:
            parts.append(f"Vbat_remain: {_format_current_unified(vbat_remain)}")

        prefix = f"[{bin_name}] " if bin_name else ""
        summary_line = " | ".join(parts)
        self.log_message.emit(f"[RESULT] {prefix}{summary_line}")

        voltage_parts = []
        vbat_v = channel_voltages.get((self.vbat_device_label, self.vbat_hw_ch))
        if vbat_v is not None:
            voltage_parts.append(f"{vbat_name}={vbat_v:.4g}V")
        for key in ordered_keys:
            v = channel_voltages.get(key)
            if v is not None:
                name = self.channel_names.get(key, f"{key[0]}-CH{key[1]}")
                voltage_parts.append(f"{name}={v:.4g}V")
        if voltage_parts:
            self.log_message.emit(f"[VOLTAGE] {prefix}{', '.join(voltage_parts)}")

        summary = {
            "bin_name": bin_name,
            "vbat": vbat_current,
            "channels": {k: results[k] for k in ordered_keys if k in results},
            "vbat_remain": vbat_remain,
            "channel_voltages": channel_voltages,
        }
        self.test_summary.emit(summary)

    def _emit_final_summary_table(self, all_bin_results):
        vbat_name = self.channel_names.get(
            (self.vbat_device_label, self.vbat_hw_ch), "Vbat"
        )
        ordered_keys = []
        for device_label, (n6705c_inst, hw_channels) in self.force_map.items():
            for ch in hw_channels:
                ordered_keys.append((device_label, ch))

        col_headers = [vbat_name]
        for key in ordered_keys:
            col_headers.append(self.channel_names.get(key, f"{key[0]}-CH{key[1]}"))
        has_vbat_remain = any(r.get("vbat_remain") is not None for r in all_bin_results)
        if has_vbat_remain:
            col_headers.append("Vbat_remain")

        cfg = _UNIT_CONFIG.get(CURRENT_UNIT, _UNIT_CONFIG["uA"])
        scale = cfg["scale"]
        suffix = cfg["suffix"]

        rows = []
        voltage_rows = []
        for r in all_bin_results:
            bin_name = r["bin_name"]
            channels = r.get("channels", {})
            vals = [f"{r.get('vbat', 0.0) * scale:.4f}"]
            for key in ordered_keys:
                vals.append(f"{channels.get(key, 0.0) * scale:.4f}")
            if has_vbat_remain:
                vr = r.get("vbat_remain")
                vals.append(f"{vr * scale:.4f}" if vr is not None else "N/A")
            rows.append((bin_name, vals))

            cv = r.get("channel_voltages", {})
            vbat_v = cv.get((self.vbat_device_label, self.vbat_hw_ch))
            v_vals = [f"{vbat_v:.4g}" if vbat_v is not None else "N/A"]
            for key in ordered_keys:
                kv = cv.get(key)
                v_vals.append(f"{kv:.4g}" if kv is not None else "N/A")
            if has_vbat_remain:
                v_vals.append("")
            voltage_rows.append((bin_name, v_vals))

        bin_col_width = max(len(r[0]) for r in rows)
        bin_col_width = max(bin_col_width, len("BIN"), len("Voltage"))
        val_col_widths = []
        for i, hdr in enumerate(col_headers):
            max_w = len(hdr)
            for _, vals in rows:
                max_w = max(max_w, len(vals[i]))
            for _, v_vals in voltage_rows:
                max_w = max(max_w, len(v_vals[i]))
            val_col_widths.append(max_w)

        unit_label = f"(Unit: {suffix})"
        header_cells = [f"{'BIN':<{bin_col_width}}"]
        for i, hdr in enumerate(col_headers):
            header_cells.append(f"{hdr:>{val_col_widths[i]}}")
        header_line = "  ".join(header_cells)
        sep_line = "-" * len(header_line)

        self.log_message.emit("[SUMMARY] " + "=" * 60)
        self.log_message.emit(f"[SUMMARY] Auto Test Results {unit_label}")
        self.log_message.emit("[SUMMARY] " + sep_line)
        self.log_message.emit(f"[SUMMARY] {header_line}")
        self.log_message.emit("[SUMMARY] " + sep_line)
        for idx, (bin_name, vals) in enumerate(rows):
            cells = [f"{bin_name:<{bin_col_width}}"]
            for i, v in enumerate(vals):
                cells.append(f"{v:>{val_col_widths[i]}}")
            self.log_message.emit(f"[SUMMARY] {'  '.join(cells)}")
            v_bin_name, v_vals = voltage_rows[idx]
            v_cells = [f"{'Voltage':<{bin_col_width}}"]
            for i, v in enumerate(v_vals):
                v_cells.append(f"{v:>{val_col_widths[i]}}")
            self.log_message.emit(f"[SUMMARY] {'  '.join(v_cells)}")
        self.log_message.emit("[SUMMARY] " + "=" * 60)


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

    NAME_OPTIONS = ["Vbat", "Vcore", "VcoreM", "VcoreL", "VANA", "VHPPA", "Vusb"]

    SINGLE_DEVICE_CHANNEL_CONFIGS = [
        {"name": "Vbat", "channel": "A-CH1", "enabled": True},
        {"name": "Vcore", "channel": "A-CH2", "enabled": True},
        {"name": "VANA", "channel": "A-CH3", "enabled": True},
        {"name": "VHPPA", "channel": "A-CH4", "enabled": True},
    ]

    DUAL_DEVICE_CHANNEL_CONFIGS = [
        {"name": "Vbat", "channel": "A-CH1", "enabled": True},
        {"name": "Vcore", "channel": "A-CH2", "enabled": True},
        {"name": "VANA", "channel": "A-CH3", "enabled": True},
        {"name": "VHPPA", "channel": "A-CH4", "enabled": True},
        {"name": "CH5", "channel": "B-CH1", "enabled": False},
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
        self.firmware_paths = []
        self.config_content = ""
        self.selected_chip_config = None
        self.is_testing = False

        self._test_thread = None
        self._test_worker = None
        self._download_thread = None
        self._download_worker = None
        self._chip_check_thread = None
        self._chip_check_worker = None
        self._auto_test_thread = None
        self._auto_test_worker = None
        self._bin_results_data = []
        self._current_total_bins = 0

        self._channel_configs = []
        self._channel_config_widgets = []
        self._syncing = False

        self.poweron_channel_combo = None
        self.reset_channel_combo = None

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
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(10)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.addWidget(self._create_connection_panel())
        fw_panel, config_panel = self._create_firmware_and_config_panels()
        left_column.addWidget(fw_panel)
        left_column.addWidget(config_panel)
        left_column.addWidget(self._create_test_config_panel())
        left_column.addStretch()

        left_inner = QWidget()
        left_inner.setStyleSheet("background: transparent; border: none;")
        left_inner.setLayout(left_column)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setFixedWidth(320)
        left_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: #0a1228; width: 6px; border: none; border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #2a3f6e; min-height: 30px; border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        left_scroll.setWidget(left_inner)

        right_column = QVBoxLayout()
        right_column.setSpacing(10)
        right_column.addWidget(self._create_channel_config_section())
        right_column.addWidget(self._create_test_buttons_row())
        right_column.addWidget(self._create_consumption_test_panel(), 1)

        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent; border: none;")
        right_widget.setLayout(right_column)

        body_layout.addWidget(left_scroll)
        body_layout.addWidget(right_widget, 1)

        main_layout.addLayout(body_layout, 1)

        self.execution_logs = ExecutionLogsFrame(show_progress=False)
        self.log_edit = self.execution_logs.log_edit
        self.clear_log_btn = self.execution_logs.clear_log_btn
        self.log_edit.setMinimumHeight(40)
        self.log_edit.setMaximumHeight(80)
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
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        self._n6705c_conn_widgets = {}
        _default_resources = {
            "B": "TCPIP0::K-N6705C-03845.local::hislip0::INSTR",
        }
        _tag_colors = {"A": "#00f5c4", "B": "#f2994a"}
        _border_colors = {"A": "#18284d", "B": "#18284d"}

        for label in ("A", "B"):
            tag_color = _tag_colors.get(label, "#00f5c4")
            border_color = _border_colors.get(label, "#18284d")
            default_res = _default_resources.get(label, "")

            sub_frame = QFrame()
            sub_frame.setObjectName(f"connSub{label}")
            sub_frame.setStyleSheet(f"""
                QFrame#connSub{label} {{
                    background-color: #0d1a38;
                    border: 1px solid {border_color};
                    border-radius: 8px;
                }}
            """)
            sub_layout = QVBoxLayout(sub_frame)
            sub_layout.setContentsMargins(8, 6, 8, 6)
            sub_layout.setSpacing(2)

            header = QHBoxLayout()
            header.setSpacing(4)
            header.setContentsMargins(0, 2, 0, 0)
            tag = QLabel(f"N6705C {label}")
            tag.setStyleSheet(
                f"color: {tag_color}; font-weight: 700; font-size: 11px;"
                " background: transparent; border: none;"
            )
            status_label = QLabel("● Disconnected")
            status_label.setStyleSheet(
                "color: #8ea6cf; font-size: 10px; font-weight: bold;"
                " background: transparent; border: none;"
            )
            header.addWidget(tag)
            header.addStretch()
            header.addWidget(status_label)
            sub_layout.addLayout(header)

            visa_combo = DarkComboBox(bg="#091426", border="#17345f")
            visa_combo.setSizeAdjustPolicy(
                DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            visa_combo.setMinimumContentsLength(10)
            visa_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            visa_combo.setFixedHeight(24)
            font = visa_combo.font()
            font.setPixelSize(10)
            visa_combo.setFont(font)
            visa_combo.addItem(default_res if default_res else "TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
            sub_layout.addWidget(visa_combo)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(4)
            _btn_h = 24
            _btn_height_fix = f"QPushButton {{ min-height: {_btn_h}px; max-height: {_btn_h}px; }}"
            search_btn = SpinningSearchButton(parent=sub_frame)
            search_btn.setFixedHeight(_btn_h)
            search_btn.setStyleSheet(search_btn.styleSheet() + _btn_height_fix)
            connect_btn = QPushButton()
            connect_btn.setFixedHeight(_btn_h)
            update_connect_button_state(connect_btn, connected=False)
            connect_btn.setStyleSheet(connect_btn.styleSheet() + _btn_height_fix)
            btn_row.addWidget(search_btn)
            btn_row.addWidget(connect_btn)
            sub_layout.addLayout(btn_row)

            layout.addWidget(sub_frame)

            widgets = {
                "tag": tag,
                "status": status_label,
                "combo": visa_combo,
                "search_btn": search_btn,
                "connect_btn": connect_btn,
            }
            self._n6705c_conn_widgets[label] = widgets
            search_btn.clicked.connect(lambda checked=False, lbl=label: self._on_device_search(lbl))
            connect_btn.clicked.connect(lambda checked=False, lbl=label: self._on_device_connect_or_disconnect(lbl))

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
            w["status"].setText("● Mock Ready")
            w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[DEBUG] Mock device {label} loaded, skip real VISA scan.")
            return

        w["status"].setText("● Searching")
        w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
        w["search_btn"].setEnabled(False)
        w["connect_btn"].setEnabled(False)
        self.append_log(f"[SYSTEM] Scanning VISA resources for N6705C-{label}...")

        from ui.modules.n6705c_module_frame import _SearchN6705CWorker
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
            w["status"].setText(f"● Found {len(devices)}")
            w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[SYSTEM] Found {len(devices)} N6705C device(s) for slot {label}.")
        else:
            w["combo"].addItem("No N6705C device found")
            w["combo"].setEnabled(False)
            w["status"].setText("● Not Found")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
        w["search_btn"].setEnabled(True)
        w["connect_btn"].setEnabled(True)

    def _on_device_search_error(self, label, err):
        w = self._n6705c_conn_widgets[label]
        w["status"].setText("● Failed")
        w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
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
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()

        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C
            inst = MockN6705C()
            setattr(self, f"n6705c_{attr}", inst)
            setattr(self, f"is_connected_{attr}", True)
            _update_n6705c_btn_state(w["connect_btn"], connected=True)
            w["search_btn"].setEnabled(False)
            w["status"].setText("● Connected")
            w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
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
        w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
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
                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
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
                w["status"].setText("● Mismatch")
                w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
                self.append_log(f"[ERROR] Connected device on {label} is not N6705C.")
        except Exception as e:
            w["status"].setText("● Failed")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[ERROR] Connection failed for N6705C-{label}: {e}")
        finally:
            w["connect_btn"].setEnabled(True)

    def _disconnect_device(self, label):
        attr = label.lower()
        w = self._n6705c_conn_widgets[label]
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
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
            w["status"].setText("● Disconnected")
            w["status"].setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[SYSTEM] N6705C-{label} disconnected.")
            new_count = self._connected_device_count()
            self._apply_preset_channels(prev_count, new_count)
            self._update_available_channels()
        except Exception as e:
            w["status"].setText("● Failed")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[ERROR] Disconnect failed for N6705C-{label}: {e}")

    def _sync_n6705c_dual_from_top(self):
        top = self._n6705c_top
        if not top:
            self._update_test_panel_state()
            return
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
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
                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            else:
                setattr(self, f"n6705c_{attr}", None)
                setattr(self, f"is_connected_{attr}", False)
                _update_n6705c_btn_state(w["connect_btn"], connected=False)
                w["search_btn"].setEnabled(True)
                w["combo"].setEnabled(True)
                w["status"].setText("● Disconnected")
                w["status"].setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
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
        for label in ["A", "B"]:
            for ch in range(1, 5):
                options.append(f"{label}-CH{ch}")
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
            combo.blockSignals(True)
            combo.clear()
            for opt in options:
                combo.addItem(opt)
            for i in range(combo.count()):
                if combo.itemText(i) == current_text:
                    combo.setCurrentIndex(i)
                    break
            combo.blockSignals(False)
        for extra_combo in [self.poweron_channel_combo, self.reset_channel_combo]:
            if extra_combo is not None:
                current_text = extra_combo.currentText()
                extra_combo.blockSignals(True)
                extra_combo.clear()
                for opt in options:
                    extra_combo.addItem(opt)
                for i in range(extra_combo.count()):
                    if extra_combo.itemText(i) == current_text:
                        extra_combo.setCurrentIndex(i)
                        break
                extra_combo.blockSignals(False)
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

    def _create_firmware_and_config_panels(self):
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
        fw_layout.setContentsMargins(12, 10, 12, 10)
        fw_layout.setSpacing(6)

        fw_title = QLabel("📁 Firmware Download")
        fw_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
        fw_layout.addWidget(fw_title)

        self.build_serial_connection_widgets(fw_layout)
        self.bind_serial_signals()

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        mode_label = QLabel("Mode")
        mode_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.download_mode_toggle = DownloadModeToggle()
        self.download_mode_toggle.setFixedWidth(140)
        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.download_mode_toggle)
        mode_row.addStretch()
        fw_layout.addLayout(mode_row)

        fw_file_row = QHBoxLayout()
        fw_file_row.setSpacing(4)
        self.firmware_file_input = QLineEdit("No file selected...")
        self.firmware_file_input.setReadOnly(True)
        self.firmware_file_input.setStyleSheet("""
            QLineEdit {
                background-color: #020816;
                border: 1px solid #1c2f54;
                border-radius: 6px;
                padding: 4px 6px;
                color: #d7e3ff;
                min-height: 28px;
                font-size: 10px;
            }
        """)
        self.firmware_browse_btn = QPushButton("...")
        self.firmware_browse_btn.setFixedWidth(36)
        self.firmware_browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d45ff;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                min-height: 28px;
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
        config_layout.setContentsMargins(12, 10, 12, 10)
        config_layout.setSpacing(6)

        config_title_row = QHBoxLayout()
        config_title_row.setSpacing(4)
        config_icon_label = QLabel()
        config_icon_label.setPixmap(
            _tinted_svg_icon(os.path.join(_ICONS_DIR, "file-json.svg"), "#94a3b8", 16).pixmap(16, 16)
        )
        config_icon_label.setFixedSize(16, 16)
        config_title = QLabel("Config Import")
        config_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
        config_title_row.addWidget(config_icon_label)
        config_title_row.addWidget(config_title)
        config_title_row.addStretch()
        config_layout.addLayout(config_title_row)

        chip_row = QHBoxLayout()
        chip_row.setSpacing(4)
        chip_select_label = QLabel("Chip")
        chip_select_label.setStyleSheet(
            "font-size: 10px; color: #7e96bf; background: transparent; border: none;"
        )
        chip_row.addWidget(chip_select_label)

        self.chip_combo = DarkComboBox()
        self.chip_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.chip_combo.setMinimumContentsLength(10)
        self.chip_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
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

        config_file_label = QLabel("Config Content")
        config_file_label.setStyleSheet("font-size: 10px; color: #7e96bf;")
        config_layout.addWidget(config_file_label)

        self.config_text_edit = QPlainTextEdit()
        self.config_text_edit.setPlaceholderText("Paste YAML config here...")
        self.config_text_edit.setMinimumHeight(60)
        self.config_text_edit.setMaximumHeight(120)
        self.config_text_edit.setStyleSheet("""
            QPlainTextEdit {
                background-color: #0d1b3e;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-family: Consolas, monospace;
                font-size: 10px;
                padding: 4px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #5d45ff;
            }
        """)
        config_layout.addWidget(self.config_text_edit)

        config_btn_row = QHBoxLayout()
        config_btn_row.setSpacing(4)

        self.import_config_btn = QPushButton("Import")
        self.import_config_btn.setIcon(_tinted_svg_icon(os.path.join(_ICONS_DIR, "upload.svg"), "#dbe7ff"))
        self.import_config_btn.setIconSize(QSize(14, 14))
        self.import_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #162544;
                color: #dbe7ff;
                border: 1px solid #25355c;
                border-radius: 6px;
                font-weight: 600;
                min-height: 30px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #1c315b; }
        """)
        config_btn_row.addWidget(self.import_config_btn, 1)

        self.execute_config_btn = QPushButton("⚙ Exec")
        self.execute_config_btn.setStyleSheet("""
            QPushButton {
                background-color: #5d45ff;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                min-height: 30px;
                font-size: 11px;
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

        self.firmware_browse_btn.clicked.connect(self._browse_firmware)
        self.download_btn.clicked.connect(self._download_to_dut)
        self.download_btn.stop_clicked.connect(self._stop_download)
        self.chip_combo.currentIndexChanged.connect(self._on_chip_selected)
        self.chip_check_btn.clicked.connect(self._on_chip_check)
        self.import_config_btn.clicked.connect(self._import_configuration)
        self.execute_config_btn.clicked.connect(self._execute_configuration)

        return fw_panel, config_panel

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
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        self.result_cards_container = QWidget()
        self.result_cards_container.setStyleSheet("background: transparent; border: none;")
        self.result_cards_layout = QHBoxLayout(self.result_cards_container)
        self.result_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.result_cards_layout.setSpacing(10)
        self.channel_cards = {}
        layout.addWidget(self.result_cards_container, 0)

        self.bin_result_table = QTableWidget(0, 0)
        self.bin_result_table.setObjectName("binResultTable")
        self.bin_result_table.setStyleSheet("""
            QTableWidget#binResultTable {
                background-color: #060e22;
                border: 1px solid #1a2d57;
                border-radius: 8px;
                gridline-color: #15284f;
                color: #dbe7ff;
                font-size: 11px;
            }
            QTableWidget#binResultTable QHeaderView::section {
                background-color: #0b1630;
                color: #8eb0e3;
                border: none;
                border-bottom: 1px solid #1a2d57;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 700;
            }
            QTableWidget#binResultTable::item {
                padding: 4px 8px;
                border-bottom: 1px solid #102448;
            }
        """)
        self.bin_result_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        self.bin_result_table.verticalHeader().setVisible(False)
        self.bin_result_table.setAlternatingRowColors(False)
        self.bin_result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.bin_result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.bin_result_table.setShowGrid(False)
        self.bin_result_table.hide()
        layout.addWidget(self.bin_result_table, 1)

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

        self.save_datalog_btn.clicked.connect(self._save_datalog)

        return wrapper

    def _create_test_buttons_row(self):
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background: transparent; border: none;")
        btn_row = QHBoxLayout(btn_widget)
        btn_row.setContentsMargins(0, 0, 0, 0)
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
            "min_height": 36,
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
            "min_height": 36,
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

        self.start_test_btn.clicked.connect(self._on_start_test)
        self.start_test_btn.stop_clicked.connect(self._stop_test)
        self.auto_test_btn.clicked.connect(self._on_auto_test)
        self.auto_test_btn.stop_clicked.connect(self._stop_auto_test)

        return btn_widget

    def _create_test_config_panel(self):
        config_frame = QFrame()
        config_frame.setObjectName("testConfigPanel")
        config_frame.setStyleSheet("""
            QFrame#testConfigPanel {
                background-color: #0a1228;
                border: 1px solid #1a2d57;
                border-radius: 10px;
            }
        """)
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(12, 10, 12, 10)
        config_layout.setSpacing(6)

        config_header = QHBoxLayout()
        config_header.setSpacing(6)
        cfg_icon = QLabel("🔧")
        cfg_icon.setStyleSheet("font-size: 13px; color: #c8d6f0;")
        cfg_title = QLabel("Test Config")
        cfg_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
        config_header.addWidget(cfg_icon)
        config_header.addWidget(cfg_title)
        config_header.addStretch()
        config_layout.addLayout(config_header)

        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        time_label = QLabel("Test Time (s)")
        time_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.test_time_input = QLineEdit("10")
        self.test_time_input.setFixedHeight(26)
        self.test_time_input.setAlignment(Qt.AlignCenter)
        self.test_time_input.setStyleSheet("""
            QLineEdit {
                background-color: #020816;
                border: 1px solid #1c2f54;
                border-radius: 6px;
                padding: 4px 8px;
                color: #d7e3ff;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #5b7cff;
            }
        """)
        time_row.addWidget(time_label)
        time_row.addWidget(self.test_time_input, 1)
        config_layout.addLayout(time_row)

        method_row = QHBoxLayout()
        method_row.setSpacing(6)
        method_label = QLabel("Control")
        method_label.setStyleSheet("font-size: 11px; color: #7e96bf;")
        self.control_method_toggle = ControlMethodToggle()
        self.control_method_toggle.setFixedWidth(140)
        method_row.addWidget(method_label)
        method_row.addWidget(self.control_method_toggle)
        method_row.addStretch()
        config_layout.addLayout(method_row)

        label_style = "font-size: 10px; color: #7e96bf;"

        poweron_row = QHBoxLayout()
        poweron_row.setSpacing(4)
        poweron_label = QLabel("PwrON")
        poweron_label.setStyleSheet(label_style)
        self.poweron_channel_combo = DarkComboBox()
        self.poweron_channel_combo.setFixedHeight(24)
        font = self.poweron_channel_combo.font()
        font.setPixelSize(11)
        self.poweron_channel_combo.setFont(font)
        for opt in self._get_available_channel_options():
            self.poweron_channel_combo.addItem(opt)
        for i in range(self.poweron_channel_combo.count()):
            if self.poweron_channel_combo.itemText(i) == "B-CH1":
                self.poweron_channel_combo.setCurrentIndex(i)
                break
        self.poweron_polarity_toggle = PolarityToggle()
        poweron_row.addWidget(poweron_label)
        poweron_row.addWidget(self.poweron_channel_combo, 1)
        poweron_row.addWidget(self.poweron_polarity_toggle)

        reset_row = QHBoxLayout()
        reset_row.setSpacing(4)
        reset_label = QLabel("Reset")
        reset_label.setStyleSheet(label_style)
        self.reset_channel_combo = DarkComboBox()
        self.reset_channel_combo.setFixedHeight(24)
        font = self.reset_channel_combo.font()
        font.setPixelSize(11)
        self.reset_channel_combo.setFont(font)
        for opt in self._get_available_channel_options():
            self.reset_channel_combo.addItem(opt)
        for i in range(self.reset_channel_combo.count()):
            if self.reset_channel_combo.itemText(i) == "B-CH2":
                self.reset_channel_combo.setCurrentIndex(i)
                break
        self.reset_polarity_toggle = PolarityToggle()
        reset_row.addWidget(reset_label)
        reset_row.addWidget(self.reset_channel_combo, 1)
        reset_row.addWidget(self.reset_polarity_toggle)

        self._n6705c_channel_widget = QWidget()
        self._n6705c_channel_widget.setStyleSheet("background: transparent; border: none;")
        ch_layout = QVBoxLayout(self._n6705c_channel_widget)
        ch_layout.setContentsMargins(0, 0, 0, 0)
        ch_layout.setSpacing(4)
        ch_layout.addLayout(poweron_row)
        ch_layout.addLayout(reset_row)
        config_layout.addWidget(self._n6705c_channel_widget)

        self.control_method_toggle.toggled.connect(self._on_control_method_changed)
        self._n6705c_channel_widget.setVisible(True)

        return config_frame

    def _on_control_method_changed(self, method):
        self._n6705c_channel_widget.setVisible(method == "N6705C")

    def _create_channel_config_section(self):
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
        cfg_title = QLabel("Channel Config")
        cfg_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        config_header.addWidget(cfg_icon)
        config_header.addWidget(cfg_title)
        config_header.addStretch()
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

        name_input = DarkComboBox()
        name_input.setFixedHeight(26)
        font = name_input.font()
        font.setPixelSize(12)
        name_input.setFont(font)
        for opt in self.NAME_OPTIONS:
            name_input.addItem(opt)
        for i in range(name_input.count()):
            if name_input.itemText(i) == name:
                name_input.setCurrentIndex(i)
                break
        else:
            name_input.setEditable(True)
            name_input.setCurrentText(name)
            name_input.setEditable(False)
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
            if channel_combo.itemText(i) == channel_key:
                channel_combo.setCurrentIndex(i)
                break
        card_layout.addWidget(channel_combo)

        stretch_idx = self._channel_config_row.count() - 1
        self._channel_config_row.insertWidget(stretch_idx, card)

        wdata = {
            "card": card,
            "card_id": card_id,
            "enable_cb": enable_cb,
            "name_input": name_input,
            "channel_combo": channel_combo,
            "remove_btn": remove_btn,
            "name_label": name_label,
            "ch_label": ch_label,
            "config_index": idx,
        }
        self._channel_config_widgets.append(wdata)

        enable_cb.toggled.connect(lambda checked, i=idx: self._on_config_enable_changed(i, checked))
        name_input.currentTextChanged.connect(lambda text, i=idx: self._on_config_name_changed(i, text))
        channel_combo.currentIndexChanged.connect(lambda ci, i=idx: self._on_config_channel_changed(i))
        remove_btn.clicked.connect(lambda checked=False, i=idx: self._remove_channel_config(i))

        self._update_card_disabled_state(wdata, enabled)
        self._refresh_result_cards()

    def _on_config_enable_changed(self, idx, checked):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["enabled"] = checked
            self._update_card_disabled_state(self._channel_config_widgets[idx], checked)
            self._refresh_result_cards()

    def _update_card_disabled_state(self, wdata, enabled):
        wdata["name_input"].setEnabled(enabled)
        wdata["channel_combo"].setEnabled(enabled)
        wdata["remove_btn"].setEnabled(enabled)

        card = wdata["card"]
        card_id = wdata["card_id"]
        if enabled:
            card.setStyleSheet(f"""
                QFrame#{card_id} {{
                    background-color: #0d1b3e;
                    border: 1px solid #1c2f54;
                    border-radius: 8px;
                }}
            """)
            wdata["name_label"].setStyleSheet("font-size: 10px; color: #7e96bf;")
            wdata["ch_label"].setStyleSheet("font-size: 10px; color: #7e96bf;")
            wdata["remove_btn"].setStyleSheet("""
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
        else:
            card.setStyleSheet(f"""
                QFrame#{card_id} {{
                    background-color: #080e1e;
                    border: 1px solid #131d36;
                    border-radius: 8px;
                }}
            """)
            wdata["name_label"].setStyleSheet("font-size: 10px; color: #3a4a6a;")
            wdata["ch_label"].setStyleSheet("font-size: 10px; color: #3a4a6a;")
            wdata["remove_btn"].setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #2a3550;
                    border: none;
                    font-size: 13px;
                    font-weight: 700;
                    min-height: 0px;
                    padding: 0px;
                }
            """)

    def _on_config_name_changed(self, idx, text):
        if idx < len(self._channel_configs):
            self._channel_configs[idx]["name"] = text
            self._refresh_result_cards()

    def _on_config_channel_changed(self, idx):
        if idx < len(self._channel_configs):
            wdata = self._channel_config_widgets[idx]
            raw = wdata["channel_combo"].currentText()
            self._channel_configs[idx]["channel"] = raw
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
            w["name_input"].currentTextChanged.disconnect()
            w["channel_combo"].currentIndexChanged.disconnect()
            w["remove_btn"].clicked.disconnect()
            w["enable_cb"].toggled.connect(lambda checked, ci=i: self._on_config_enable_changed(ci, checked))
            w["name_input"].currentTextChanged.connect(lambda text, ci=i: self._on_config_name_changed(ci, text))
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
        self._vbat_remain_card = None

        vbat_idx = None
        has_sub_channel = False
        for i, cfg in enumerate(self._channel_configs):
            if not cfg["enabled"]:
                continue
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
            else:
                has_sub_channel = True
            colors = self.CHANNEL_COLORS_LIST[i % len(self.CHANNEL_COLORS_LIST)]
            card = self._create_result_card(i, cfg["name"], cfg["channel"], colors)
            self.result_cards_layout.addWidget(card, 1)

        if has_sub_channel and vbat_idx is not None:
            remain_colors = {"accent": "#a0a0a0", "bg": "#121218", "border": "#2a2a36"}
            remain_card = self._create_result_card(-1, "Vbat_remain", "", remain_colors)
            self.result_cards_layout.addWidget(remain_card, 1)
            self._vbat_remain_card = self.channel_cards.pop(-1)

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
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Firmware File(s)", "",
            "Firmware Files (*.bin *.hex);;All Files (*)"
        )
        if file_paths:
            self.firmware_paths = file_paths
            self.firmware_path = file_paths[0]
            names = [os.path.basename(p) for p in file_paths]
            self.firmware_file_input.setText("; ".join(names))
            for fp in file_paths:
                self.append_log(f"[SYSTEM] Firmware file selected: {os.path.basename(fp)}")

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

        refreshed = get_chip_config(chip_name, force_reload=True)
        if refreshed:
            self.selected_chip_config = refreshed

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

            target = "NO_PREFIX"
            if ":" in line:
                prefix, rest = line.split(":", 1)
                prefix_upper = prefix.strip().upper()
                rest_upper = rest.strip().upper()
                has_command = any(kw in rest_upper for kw in ("WRITE_BITS", "WRITE", "READ"))
                if has_command:
                    if prefix_upper == "DUT":
                        target = "DUT"
                        line = rest.strip()
                    elif prefix_upper == "PMU":
                        target = "MAIN_DIE_PMU"
                        line = rest.strip()
                    elif prefix_upper == "MAIN_DIE_PMU":
                        target = "MAIN_DIE_PMU"
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
        if target == "MAIN_DIE_PMU":
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
            target = cmd.get("target", "NO_PREFIX")
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
            if chip_name.startswith("pmu_"):
                config_file = os.path.join(chips_dir, "pmu_chips", f"{chip_name}.py")
            else:
                config_file = os.path.join(chips_dir, "main_chips", f"{chip_name}.py")

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

            refreshed = get_chip_config(chip_name, force_reload=True)
            if refreshed:
                self.selected_chip_config = refreshed
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

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        force_high_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}

        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
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
            if device_label not in force_high_map:
                force_high_map[device_label] = (inst, [])
            if hw_ch not in force_high_map[device_label][1]:
                force_high_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = 0
        self.bin_result_table.hide()
        self.start_test_btn.setStateWaiting()
        self.append_log(
            f"[TEST] Starting force-high consumption test: "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"time={test_time}s, base_period={sample_period*1e6:.0f}us"
        )

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is not None and hw_ch is not None:
                channel_names[(device_label, hw_ch)] = cfg["name"]

        worker = _ConsumptionTestForceHighWorker(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_high_map, test_time, sample_period,
            channel_names=channel_names,
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.channel_result.connect(self._on_force_high_channel_result)
        worker.test_summary.connect(self._on_test_summary)
        worker.progress.connect(self.start_test_btn.setProgress)
        worker.error.connect(self._on_test_error)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        self.start_test_btn.setStateProgramming()
        self.start_test_btn._progress_timer.stop()
        thread.start()

    def consumption_test_force(self):
        if self.is_testing:
            return

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        force_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}

        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
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
            if device_label not in force_map:
                force_map[device_label] = (inst, [])
            if hw_ch not in force_map[device_label][1]:
                force_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = 0
        self.bin_result_table.hide()
        self.start_test_btn.setStateWaiting()
        self.append_log(
            f"[TEST] Starting force-auto consumption test: "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"time={test_time}s, base_period={sample_period*1e6:.0f}us"
        )

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is not None and hw_ch is not None:
                channel_names[(device_label, hw_ch)] = cfg["name"]

        worker = _ConsumptionTestForceWorker(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_map, test_time, sample_period,
            channel_names=channel_names,
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.channel_result.connect(self._on_force_high_channel_result)
        worker.test_summary.connect(self._on_test_summary)
        worker.progress.connect(self.start_test_btn.setProgress)
        worker.error.connect(self._on_test_error)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        self.start_test_btn.setStateProgramming()
        self.start_test_btn._progress_timer.stop()
        thread.start()

    def _on_force_high_channel_result(self, device_label, hw_channel, avg_current, phase):
        cfg_idx = self._config_index_map.get(device_label, {}).get(hw_channel)
        if cfg_idx is not None and cfg_idx in self.channel_cards:
            label = self.channel_cards[cfg_idx]["value_label"]
            label.setText(self._format_current(avg_current))

    def _on_test_summary(self, summary):
        vbat_remain = summary.get("vbat_remain")
        if vbat_remain is not None and self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText(self._format_current(vbat_remain))

        if self._current_total_bins > 1:
            self._bin_results_data.append(summary)
            self._add_bin_result_row(summary)

    def _setup_bin_result_table(self):
        self._bin_results_data = []
        self.bin_result_table.setRowCount(0)

        headers = ["BIN"]
        for i, cfg in enumerate(self._channel_configs):
            if cfg["enabled"]:
                headers.append(cfg["name"])
        has_sub = any(
            cfg["enabled"] and not cfg["name"].lower().startswith("vbat")
            for cfg in self._channel_configs
        )
        if has_sub:
            headers.append("Vbat_remain")

        self.bin_result_table.setColumnCount(len(headers))
        self.bin_result_table.setHorizontalHeaderLabels(headers)
        self.bin_result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bin_result_table.show()

    def _add_bin_result_row(self, summary):
        row = self.bin_result_table.rowCount()
        self.bin_result_table.insertRow(row)

        bin_name = summary.get("bin_name", f"BIN-{row // 2 + 1}")
        col = 0
        bin_item = QTableWidgetItem(bin_name)
        bin_item.setTextAlignment(Qt.AlignCenter)
        bin_item.setForeground(QColor("#eaf2ff"))
        self.bin_result_table.setItem(row, col, bin_item)
        col += 1

        channels = summary.get("channels", {})
        vbat_current = summary.get("vbat")

        for i, cfg in enumerate(self._channel_configs):
            if not cfg["enabled"]:
                continue
            if cfg["name"].lower().startswith("vbat") and vbat_current is not None:
                val_text = self._format_current(vbat_current)
            else:
                device_label, hw_ch = self._parse_channel_key(cfg["channel"])
                key = (device_label, hw_ch)
                val = channels.get(key)
                val_text = self._format_current(val) if val is not None else "- - -"
            colors = self.CHANNEL_COLORS_LIST[i % len(self.CHANNEL_COLORS_LIST)]
            item = QTableWidgetItem(val_text)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(colors["accent"]))
            self.bin_result_table.setItem(row, col, item)
            col += 1

        has_sub = any(
            cfg["enabled"] and not cfg["name"].lower().startswith("vbat")
            for cfg in self._channel_configs
        )
        if has_sub:
            vbat_remain = summary.get("vbat_remain")
            remain_text = self._format_current(vbat_remain) if vbat_remain is not None else "- - -"
            remain_item = QTableWidgetItem(remain_text)
            remain_item.setTextAlignment(Qt.AlignCenter)
            remain_item.setForeground(QColor("#a0a0a0"))
            self.bin_result_table.setItem(row, col, remain_item)

        v_row = self.bin_result_table.rowCount()
        self.bin_result_table.insertRow(v_row)
        v_col = 0
        v_label_item = QTableWidgetItem("Voltage")
        v_label_item.setTextAlignment(Qt.AlignCenter)
        v_label_item.setForeground(QColor("#8899bb"))
        self.bin_result_table.setItem(v_row, v_col, v_label_item)
        v_col += 1

        channel_voltages = summary.get("channel_voltages", {})
        for i, cfg in enumerate(self._channel_configs):
            if not cfg["enabled"]:
                continue
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            key = (device_label, hw_ch)
            v = channel_voltages.get(key)
            v_text = f"{v:.4g}V" if v is not None else "- - -"
            v_item = QTableWidgetItem(v_text)
            v_item.setTextAlignment(Qt.AlignCenter)
            v_item.setForeground(QColor("#8899bb"))
            self.bin_result_table.setItem(v_row, v_col, v_item)
            v_col += 1

        if has_sub:
            empty_item = QTableWidgetItem("")
            empty_item.setTextAlignment(Qt.AlignCenter)
            self.bin_result_table.setItem(v_row, v_col, empty_item)

        self.bin_result_table.scrollToBottom()

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
        if self.is_testing:
            self.append_log("[WARNING] A test is already running.")
            return

        firmware_paths = getattr(self, 'firmware_paths', [])
        if not firmware_paths:
            if self.firmware_path:
                firmware_paths = [self.firmware_path]
            else:
                self.append_log("[ERROR] No firmware file selected.")
                return

        port_text = self.get_selected_serial_port()
        if not port_text:
            self.append_log("[ERROR] No serial port selected.")
            return
        m = re.search(r'(\d+)', port_text)
        com_port = m.group(1) if m else port_text

        mode_str = self.download_mode_toggle.value().lower()
        download_mode = DownloadMode.FLASH if mode_str == "flash" else DownloadMode.RAMRUN

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        poweron_key = self.poweron_channel_combo.currentText() if self.poweron_channel_combo else ""
        reset_key = self.reset_channel_combo.currentText() if self.reset_channel_combo else ""
        if not poweron_key or not reset_key:
            self.append_log("[ERROR] PowerON or RESET channel not configured.")
            return

        poweron_dl, poweron_hw = self._parse_channel_key(poweron_key)
        reset_dl, reset_hw = self._parse_channel_key(reset_key)
        if poweron_dl is None or reset_dl is None:
            self.append_log("[ERROR] Invalid PowerON/RESET channel key.")
            return

        poweron_attr = poweron_dl.lower()
        poweron_inst = getattr(self, f"n6705c_{poweron_attr}", None)
        poweron_conn = getattr(self, f"is_connected_{poweron_attr}", False)
        if not poweron_conn or not poweron_inst:
            self.append_log(f"[ERROR] N6705C-{poweron_dl} is not connected (required by PowerON).")
            return

        reset_attr = reset_dl.lower()
        reset_inst = getattr(self, f"n6705c_{reset_attr}", None)
        reset_conn = getattr(self, f"is_connected_{reset_attr}", False)
        if not reset_conn or not reset_inst:
            self.append_log(f"[ERROR] N6705C-{reset_dl} is not connected (required by RESET).")
            return

        poweron_polarity = self.poweron_polarity_toggle.value()
        reset_polarity = self.reset_polarity_toggle.value()

        force_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}
        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
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
            if device_label not in force_map:
                force_map[device_label] = (inst, [])
            if hw_ch not in force_map[device_label][1]:
                force_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            dl, hw = self._parse_channel_key(cfg["channel"])
            if dl is not None and hw is not None:
                channel_names[(dl, hw)] = cfg["name"]

        config_text = self.config_text_edit.toPlainText().strip()
        chip_combo_text = self.chip_combo.currentText() if self.chip_combo.currentIndex() > 0 else None

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = len(firmware_paths)
        self.auto_test_btn.setStateWaiting()

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        if self._current_total_bins > 1:
            self._setup_bin_result_table()
        else:
            self.bin_result_table.hide()

        self.append_log(
            f"[AUTO_TEST] Starting auto test: {len(firmware_paths)} BIN(s), "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"PowerON={poweron_key}({poweron_polarity}), "
            f"RESET={reset_key}({reset_polarity})"
        )

        worker = _AutoTestWorker(
            com_port=com_port,
            firmware_paths=firmware_paths,
            download_mode=download_mode,
            poweron_device_label=poweron_dl,
            poweron_inst=poweron_inst,
            poweron_hw_ch=poweron_hw,
            poweron_polarity=poweron_polarity,
            reset_device_label=reset_dl,
            reset_inst=reset_inst,
            reset_hw_ch=reset_hw,
            reset_polarity=reset_polarity,
            vbat_device_label=vbat_device_label,
            vbat_inst=vbat_inst,
            vbat_hw_ch=vbat_hw_ch,
            force_map=force_map,
            test_time=test_time,
            sample_period=sample_period,
            channel_names=channel_names,
            chip_combo_text=chip_combo_text,
            selected_chip_config=self.selected_chip_config,
            config_text=config_text,
            parse_config_commands_fn=self._parse_config_commands,
            resolve_device_fn=self._resolve_device,
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.channel_result.connect(self._on_force_high_channel_result)
        worker.test_summary.connect(self._on_test_summary)
        worker.progress.connect(self.auto_test_btn.setProgress)
        worker.download_state_changed.connect(
            lambda s: self.append_log(f"[AUTO_TEST] Download state: {s}")
        )
        worker.error.connect(self._on_auto_test_error)
        worker.finished.connect(self._on_auto_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_auto_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._auto_test_thread = thread
        self._auto_test_worker = worker
        self.auto_test_btn.setStateProgramming()
        self.auto_test_btn._progress_timer.stop()
        thread.start()

    def _on_auto_test_error(self, err_msg):
        self.append_log(f"[AUTO_TEST] Error: {err_msg}")

    def _on_auto_test_finished(self):
        self.is_testing = False
        self.auto_test_btn.setStateComplete()
        self.append_log("[AUTO_TEST] Auto test completed.")

    def _on_auto_test_thread_cleaned(self):
        self._auto_test_worker = None
        self._auto_test_thread = None

    def _stop_auto_test(self):
        if self._auto_test_worker:
            self._auto_test_worker.stop()
        self.is_testing = False
        self.auto_test_btn.setStateFailed()
        self.append_log("[AUTO_TEST] Auto test stopped by user.")

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
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")
        self._bin_results_data = []
        self._current_total_bins = 0
        self.bin_result_table.setRowCount(0)
        self.bin_result_table.hide()

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