#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# run cmd:
# python d:\CodeProject\TRAE_Projects\KK_Lab\ui\n6705c_datalog_ui.py


import sys
import os
import math
import random

def _get_base_path():
    """Get project root path, compatible with PyInstaller bundled and dev environment."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


sys.path.append(_get_base_path())

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QGridLayout, QFrame, QCheckBox,
    QRadioButton, QButtonGroup, QSizePolicy, QFileDialog,
    QScrollArea, QGraphicsRectItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QToolButton, QDialog, QTabWidget, QTabBar,
    QProgressBar,
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor, QBrush, QPen, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
import pyqtgraph as pg
import pyvisa
import os

from instruments.power.keysight.n6705c import N6705C
from ui.styles.button import SpinningSearchButton, update_connect_button_state
from instruments.power.keysight.n6705c_datalog_process import (
    parse_csv_text, parse_dlog_binary, compute_power_channels,
    calc_power_for_ch, import_csv_file, import_edlg_file, import_dlog_file,
)
from ui.widgets.dark_combobox import DarkComboBox
from ui.styles import SCROLL_AREA_STYLE
from log_config import get_logger
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C

logger = get_logger(__name__)


CHANNEL_COLORS = [
    "#18b67a",
    "#d4a514",
    "#2f6fed",
    "#d14b72",
    "#00bcd4",
    "#ff9800",
    "#ab47bc",
    "#8bc34a",
]

CHANNEL_LABEL_COLORS = [
    "#7fffcf",
    "#ffe566",
    "#8cb8ff",
    "#ff9ab8",
    "#7ef5ff",
    "#ffc966",
    "#dda0ff",
    "#c8ff7e",
]

VOLTAGE_COLORS = [
    "#10946a",
    "#a88010",
    "#2558ba",
    "#a83a5a",
    "#009aad",
    "#cc7a00",
    "#883a96",
    "#6e9c3a",
]

POWER_COLORS = [
    "#b05ce6",
    "#e6a33c",
    "#3cb0e6",
    "#e63c6e",
    "#6ee63c",
    "#e6ce3c",
    "#3c6ee6",
    "#e63cb0",
]


def _parse_ch_label(label):
    import re
    raw = label.strip()
    file_prefix = ""
    fm = re.match(r'^(F\d+)-(.*)', raw)
    if fm:
        file_prefix = fm.group(1)
        raw = fm.group(2).strip()
    m = re.search(r'CH(\d+)\s*(I|V|P)', raw)
    if m:
        ch_num = int(m.group(1))
        mtype = m.group(2)
        is_b = raw.startswith("B ") or raw.startswith("B_")
        return ch_num, mtype, is_b
    return None, None, False


def _display_label(key):
    import re
    raw = key.strip()
    file_prefix = ""
    fm = re.match(r'^(F\d+)-(.*)', raw)
    if fm:
        file_prefix = fm.group(1)
        raw = fm.group(2).strip()
    ch_num, mtype, is_b = _parse_ch_label(raw)
    if ch_num is None:
        return raw
    slot = "B" if is_b else "A"
    if file_prefix:
        return f"{file_prefix}-{slot}-{mtype}{ch_num}"
    return f"{slot}-{mtype}{ch_num}"


def _color_for_label(label):
    ch_num, mtype, is_b = _parse_ch_label(label)
    if ch_num is None:
        return CHANNEL_COLORS[0]
    base_idx = (ch_num - 1) + (4 if is_b else 0)
    if mtype == "V":
        return VOLTAGE_COLORS[base_idx % len(VOLTAGE_COLORS)]
    if mtype == "P":
        return POWER_COLORS[base_idx % len(POWER_COLORS)]
    return CHANNEL_COLORS[base_idx % len(CHANNEL_COLORS)]


def _sort_key_for_label(label):
    import re
    raw = label.strip()
    file_order = 0
    fm = re.match(r'^F(\d+)-(.*)', raw)
    if fm:
        file_order = int(fm.group(1))
    ch_num, mtype, is_b = _parse_ch_label(label)
    unit_order = 1 if is_b else 0
    ch_order = ch_num if ch_num else 0
    type_order = {"V": 0, "I": 1, "P": 2}.get(mtype, 3)
    return (file_order, unit_order, ch_order, type_order)


def _parse_value_with_unit(text, base_unit=None):
    import re
    text = text.strip()
    m = re.match(r'^([+-]?\d*\.?\d+)\s*([a-zA-Z\u00B5\u03BC]*)\s*$', text)
    if not m:
        try:
            return float(text)
        except ValueError:
            return None
    num = float(m.group(1))
    raw_unit = m.group(2).strip()

    if not raw_unit and base_unit:
        raw_unit = base_unit

    unit = raw_unit.lower().replace('\u00b5', 'u').replace('\u03bc', 'u')

    if unit in ("ua", "uv", "uw", "u"):
        return num * 1e-3
    elif unit in ("ma", "mv", "mw", "m"):
        return num
    elif unit in ("a", "v", "w"):
        return num * 1e3
    return num


def _unit_for_label(label):
    _, mtype, _ = _parse_ch_label(label)
    if mtype == "V":
        return "mV"
    if mtype == "P":
        return "mW"
    return "mA"


def _format_value(value_mA):
    abs_v = abs(value_mA)
    if abs_v >= 1000:
        return f"{value_mA / 1000:.3f} A"
    elif abs_v >= 1:
        return f"{value_mA:.2f} mA"
    elif abs_v > 0:
        return f"{value_mA * 1000:.2f} \u00B5A"
    else:
        return f"0.00 mA"


def _format_time(seconds):
    abs_val = abs(seconds)
    if abs_val == 0:
        return "0 s"
    if abs_val < 1e-3:
        return f"{seconds * 1e6:.3f} us"
    if abs_val < 1.0:
        return f"{seconds * 1e3:.3f} ms"
    return f"{seconds:.6f} s"


def _auto_format(value, base_unit):
    UNIT_MAP = {
        "mA": ("\u00B5A", "mA", "A"),
        "mV": ("\u00B5V", "mV", "V"),
        "mW": ("\u00B5W", "mW", "W"),
        "mAh": ("\u00B5Ah", "mAh", "Ah"),
        "mWh": ("\u00B5Wh", "mWh", "Wh"),
        "C": ("mC", "C", "kC"),
        "J": ("mJ", "J", "kJ"),
    }
    units = UNIT_MAP.get(base_unit)
    if not units:
        return f"{value:.4f} {base_unit}"

    abs_v = abs(value)
    if base_unit in ("C", "J"):
        if abs_v < 1:
            return f"{value * 1000:.4f} {units[0]}"
        elif abs_v >= 1000:
            return f"{value / 1000:.4f} {units[2]}"
        else:
            return f"{value:.4f} {units[1]}"
    else:
        if abs_v >= 1000:
            return f"{value / 1000:.4f} {units[2]}"
        elif abs_v >= 1:
            return f"{value:.4f} {units[1]}"
        elif abs_v > 0:
            return f"{value * 1000:.4f} {units[0]}"
        else:
            return f"0.0000 {units[1]}"


class ToggleLabel(QLabel):
    toggled = Signal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._checked = False
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked
        self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if not self.isEnabled():
            return
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def blockSignals(self, b):
        super().blockSignals(b)


class ScaleOffsetEdit(QLineEdit):
    wheel_adjusted = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        factor = 1.1 if delta > 0 else 0.9
        current = _parse_value_with_unit(self.text())
        if current is None:
            event.accept()
            return
        new_val = current * factor
        base_unit = self.property("base_unit") or "mA"
        self.setText(_auto_format(new_val, base_unit))
        self.wheel_adjusted.emit()
        event.accept()


class ChannelNameLabel(QWidget):
    renamed = Signal(str, str)

    def __init__(self, key, display_name, color, parent=None):
        super().__init__(parent)
        self._key = key
        self._display_name = display_name
        self._color = color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(0)

        self._label = QLabel(display_name)
        self._label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: 800; border: none; padding: 0 2px;"
        )
        layout.addWidget(self._label)

        self._edit = QLineEdit(display_name)
        self._edit.setAlignment(Qt.AlignRight)
        self._edit.setStyleSheet(
            f"background: #0c1a35; color: {color}; font-size: 13px; font-weight: 800; "
            f"border: 1px solid {color}; border-radius: 2px; padding: 0 2px;"
        )
        self._edit.hide()
        layout.addWidget(self._edit)

        self._edit.returnPressed.connect(self._finish_edit)
        self._edit.editingFinished.connect(self._finish_edit)

    def mouseDoubleClickEvent(self, event):
        self._label.hide()
        self._edit.setText(self._display_name)
        self._edit.show()
        self._edit.setFocus()
        self._edit.selectAll()

    def _finish_edit(self):
        new_name = self._edit.text().strip()
        if new_name and new_name != self._display_name:
            self._display_name = new_name
            self._label.setText(new_name)
            self.renamed.emit(self._key, new_name)
        self._edit.hide()
        self._label.show()

    @property
    def key(self):
        return self._key


class _ScanWorker(QObject):
    device_found = Signal(str, str, str, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, rm=None):
        super().__init__()
        self._rm = rm

    def run(self):
        try:
            if self._rm is None:
                try:
                    self._rm = pyvisa.ResourceManager()
                except Exception:
                    self._rm = pyvisa.ResourceManager("@py")

            resources = list(self._rm.list_resources()) or []
            seen = {}
            for res in resources:
                try:
                    instr = self._rm.open_resource(res, timeout=2000)
                    idn = instr.query("*IDN?").strip()
                    instr.close()
                    if "N6705C" in idn:
                        parts = idn.split(",")
                        model = parts[1].strip() if len(parts) > 1 else "N6705C"
                        serial = parts[2].strip() if len(parts) > 2 else "Unknown"
                        ip = res.split("::")[1] if "::" in res else res
                        if serial in seen:
                            if "hislip" in res and "hislip" not in seen[serial][3]:
                                seen[serial] = (serial, model, ip, res)
                        else:
                            seen[serial] = (serial, model, ip, res)
                except Exception:
                    pass
            for serial, model, ip, res in seen.values():
                self.device_found.emit(serial, model, ip, res)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @property
    def rm(self):
        return self._rm


class _ConnectWorker(QObject):
    success = Signal(object, str, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, visa_resource, serial, debug=False):
        super().__init__()
        self._visa_resource = visa_resource
        self._serial = serial
        self._debug = debug

    def run(self):
        try:
            if self._debug:
                n6705c = MockN6705C()
            else:
                n6705c = N6705C(self._visa_resource)
            self.success.emit(n6705c, self._serial, self._visa_resource)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class _DatalogWorker(QObject):
    data_ready = Signal(dict)
    dlog_raw_ready = Signal(list)
    finished = Signal()
    error = Signal(str)
    progress_update = Signal(int, str)

    def __init__(self, n6705c_list, channels_per_unit, unit_labels,
                 record_type, sample_period_us, monitoring_time_s,
                 debug=False, voltage_channels_per_unit=None):
        super().__init__()
        self.n6705c_list = n6705c_list
        self.channels_per_unit = channels_per_unit
        self.unit_labels = unit_labels
        self.record_type = record_type
        self.sample_period_us = sample_period_us
        self.monitoring_time_s = monitoring_time_s
        self.debug = debug
        self.voltage_channels_per_unit = voltage_channels_per_unit or [[] for _ in n6705c_list]
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        import time
        try:
            run_start = time.time()
            sample_period_s = self.sample_period_us / 1_000_000.0

            if self.debug:
                self.progress_update.emit(5, "Generating mock data...")
                logger.debug("[Datalog][Progress] Mock mode start at %.3fs", time.time() - run_start)
                mock_start = time.time()
                all_data = self._generate_mock_data(sample_period_s)
                logger.debug("[Datalog][Progress] Mock data generated in %.3fs", time.time() - mock_start)
                self.progress_update.emit(100, "Done")
                self.data_ready.emit(all_data)
                self.finished.emit()
                return

            import threading

            active_units = []
            for unit_idx, n6705c in enumerate(self.n6705c_list):
                curr_channels = self.channels_per_unit[unit_idx]
                volt_channels = self.voltage_channels_per_unit[unit_idx]
                if curr_channels or volt_channels:
                    active_units.append((unit_idx, n6705c, curr_channels, volt_channels))

            if not active_units:
                self.finished.emit()
                return

            self.progress_update.emit(2, "Configuring instruments...")
            logger.debug("[Datalog][Progress] Configure start at %.3fs", time.time() - run_start)
            config_start = time.time()

            barrier = threading.Barrier(len(active_units), timeout=30)
            init_errors = [None] * len(active_units)

            def configure_and_start(idx, unit_idx, n6705c, curr_channels, volt_channels):
                try:
                    n6705c.instr.write("*CLS")
                    try:
                        n6705c.instr.write("ABOR:DLOG")
                    except Exception:
                        pass

                    for ch in range(1, 5):
                        n6705c.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
                        n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")

                    for ch in curr_channels:
                        n6705c.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{ch})")
                        n6705c.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{ch})")

                    for ch in volt_channels:
                        n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT ON,(@{ch})")

                    n6705c.instr.write(f"SENS:DLOG:TIME {self.monitoring_time_s}")
                    n6705c.instr.write(f"SENS:DLOG:PER {sample_period_s}")
                    n6705c.instr.write("TRIG:DLOG:SOUR IMM")

                    dlog_file = f"internal:\\datalog_cap_{unit_idx}.dlog"

                    barrier.wait()

                    n6705c.instr.write(f'INIT:DLOG "{dlog_file}"')
                    logger.debug("[Datalog] Unit %d INIT:DLOG sent at %.6f", unit_idx, time.time())
                except Exception as e:
                    init_errors[idx] = e

            threads = []
            for idx, (unit_idx, n6705c, curr_ch, volt_ch) in enumerate(active_units):
                t = threading.Thread(
                    target=configure_and_start,
                    args=(idx, unit_idx, n6705c, curr_ch, volt_ch),
                    daemon=True,
                )
                threads.append(t)

            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=60)

            logger.debug("[Datalog][Progress] Configure done in %.3fs", time.time() - config_start)
            self.progress_update.emit(2, "Capturing data...")
            logger.debug("[Datalog][Progress] Capture wait start at %.3fs", time.time() - run_start)

            all_data = {}
            raw_dlog_list = []

            logger.info("[Datalog] Waiting %ds for capture...", self.monitoring_time_s + 5)
            wait_end = time.time() + self.monitoring_time_s + 5
            capture_start = time.time()
            capture_total = self.monitoring_time_s + 5
            while time.time() < wait_end:
                if self._is_stopped:
                    logger.info("[Datalog] Stopped by user during capture wait")
                    self.finished.emit()
                    return
                elapsed = time.time() - capture_start
                capture_pct = min(elapsed / capture_total, 1.0)
                overall_pct = int(2 + capture_pct * 91)
                self.progress_update.emit(overall_pct, "Capturing data...")
                time.sleep(0.5)

            logger.debug("[Datalog][Progress] Capture wait done in %.3fs", time.time() - capture_start)
            self.progress_update.emit(93, "Downloading data...")
            logger.debug("[Datalog][Progress] Download start at %.3fs", time.time() - run_start)
            download_start = time.time()

            for unit_idx, n6705c in enumerate(self.n6705c_list):
                if self._is_stopped:
                    break
                curr_channels = self.channels_per_unit[unit_idx]
                volt_channels = self.voltage_channels_per_unit[unit_idx]
                if not curr_channels and not volt_channels:
                    continue

                ulabel = self.unit_labels[unit_idx]
                unit_data = None

                dlog_file = f"internal:\\datalog_cap_{unit_idx}.dlog"
                try:
                    t0 = time.time()
                    raw_dlog = n6705c.read_mmem_data(dlog_file)
                    t1 = time.time()
                    if isinstance(raw_dlog, bytes):
                        logger.info("[Datalog] dlog downloaded: %d bytes in %.1fs", len(raw_dlog), t1-t0)
                        raw_dlog_list.append(raw_dlog)

                        unit_data = parse_dlog_binary(
                            raw_dlog, curr_channels, volt_channels,
                            ulabel, sample_period_s
                        )
                except Exception as e:
                    logger.error("[Datalog] dlog download/parse failed: %s", e)

                if not unit_data:
                    logger.info("[Datalog] Falling back to CSV export...")
                    csv_file = f"internal:\\datalog_cap_{unit_idx}.csv"
                    n6705c.instr.write(f'MMEM:EXP:DLOG "{csv_file}"')
                    for _ in range(15):
                        if self._is_stopped:
                            break
                        time.sleep(0.2)

                    t0 = time.time()
                    raw_csv = n6705c.read_mmem_data(csv_file)
                    t1 = time.time()
                    if isinstance(raw_csv, bytes):
                        csv_text = raw_csv.decode('ascii', errors='replace')
                    else:
                        csv_text = raw_csv
                    logger.info("[Datalog] CSV download: %d chars in %.1fs", len(csv_text), t1-t0)

                    unit_data = parse_csv_text(
                        csv_text, curr_channels, volt_channels,
                        ulabel, sample_period_s
                    )

                if unit_data:
                    all_data.update(unit_data)

            logger.debug("[Datalog][Progress] Download done in %.3fs", time.time() - download_start)
            self.progress_update.emit(98, "Processing results...")
            logger.debug("[Datalog][Progress] Emitting results at %.3fs", time.time() - run_start)
            logger.info("[Datalog] Total channels with data: %d", len(all_data))
            self.dlog_raw_ready.emit(raw_dlog_list)
            self.data_ready.emit(all_data)
            self.progress_update.emit(100, "Done")
            logger.debug("[Datalog][Progress] Total run time: %.3fs", time.time() - run_start)
            self.finished.emit()
        except Exception as e:
            logger.error("[Datalog] ERROR: %s", e, exc_info=True)
            self.error.emit(str(e))
            self.finished.emit()

    def _generate_mock_data(self, sample_period_s):
        rng = random.Random(42)
        total_points = int(self.monitoring_time_s / sample_period_s)
        total_points = min(total_points, 50000)

        all_data = {}
        ch_global_idx = 0
        for unit_idx in range(len(self.channels_per_unit)):
            curr_channels = self.channels_per_unit[unit_idx]
            volt_channels = self.voltage_channels_per_unit[unit_idx]
            ulabel = self.unit_labels[unit_idx]

            all_chs = sorted(set(curr_channels) | set(volt_channels))
            for ch in all_chs:
                if ch in volt_channels:
                    label = f"{ulabel} CH{ch} V".strip()
                    t = [i * sample_period_s for i in range(total_points)]
                    base_mV = 1200 + ch_global_idx * 600
                    values = [
                        base_mV
                        + 5 * math.sin(2 * math.pi * 0.3 * ti)
                        + rng.gauss(0, 3)
                        for ti in t
                    ]
                    all_data[label] = {"time": t, "values": values}
                    ch_global_idx += 1

                if ch in curr_channels:
                    label = f"{ulabel} CH{ch} I".strip()
                    t = [i * sample_period_s for i in range(total_points)]
                    base_mA = 1780 + ch_global_idx * 120
                    noise_std = 15 + ch_global_idx * 5
                    values = [
                        base_mA
                        + 8 * math.sin(2 * math.pi * 0.5 * ti)
                        + rng.gauss(0, noise_std)
                        for ti in t
                    ]
                    all_data[label] = {"time": t, "values": values}
                    ch_global_idx += 1

        return all_data


class VerticalTextButton(QWidget):
    clicked = Signal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text
        self._checked = False
        self._hovered = False
        self.setFixedWidth(28)
        self.setMinimumHeight(180)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover)

    def isChecked(self):
        return self._checked

    def setChecked(self, val):
        self._checked = val
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self.update()
        self.clicked.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        if self._checked:
            bg = QColor("#1a3260")
            border = QColor("#3a6fd4")
        elif self._hovered:
            bg = QColor("#1a3260")
            border = QColor("#27406f")
        else:
            bg = QColor("#13254b")
            border = QColor("#27406f")

        p.setBrush(bg)
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(0, 0, w - 1, h - 1, 6, 6)

        text_color = QColor("#dce7ff") if (self._checked or self._hovered) else QColor("#8eb0e3")
        p.setPen(text_color)
        font = QFont()
        font.setWeight(QFont.DemiBold)
        font.setPixelSize(12)
        p.setFont(font)

        p.save()
        p.translate(w / 2, h / 2)
        p.rotate(90)
        p.drawText(-h // 2, -w // 2, h, w, Qt.AlignCenter, self._text)
        p.restore()

        p.end()


class CardFrame(QFrame):
    def __init__(self, title="", icon="", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)

        if title:
            self.title_label = QLabel(f"{icon}  {title}" if icon else title)
            self.title_label.setObjectName("cardTitle")
            self.main_layout.addWidget(self.title_label)


class FixedPopupComboBox(DarkComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def showPopup(self):
        super().showPopup()
        view = self.view()
        if view and view.window():
            popup = view.window()
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(global_pos.x(), global_pos.y())


class N6705CDatalogUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._top = n6705c_top
        self.rm = None
        self.n6705c_a = None
        self.n6705c_b = None
        self.is_connected_a = False
        self.is_connected_b = False
        self.is_recording = False

        self._record_thread = None
        self._record_worker = None

        self.datalog_data = {}
        self._raw_dlog_list = []
        self._imported_tab_configs = []
        self._import_counter = 0
        self._band_info = {}
        self._sep_lines = []
        self._selected_ch_key = None
        self._selected_highlight = None
        self._ch_drag_active = False
        self._ch_drag_last_y = None
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_region = None
        self.box_zoom_enabled = False
        self._box_zoom_auto_off_timer = QTimer(self)
        self._box_zoom_auto_off_timer.setSingleShot(True)
        self._box_zoom_auto_off_timer.setInterval(4000)
        self._box_zoom_auto_off_timer.timeout.connect(self._auto_off_box_zoom)
        self._pending_marker = None
        self._marker_drag_target = None
        self._marker_snap_px = 10
        self.custom_labels = []
        self.custom_label_lines = []

        self.crosshair_v = None
        self.crosshair_tooltip = None
        self.crosshair_dots = []

        self.type_current = QRadioButton()
        self.type_current.setChecked(True)
        self.type_current.hide()

        self.mode_group = QButtonGroup(self)
        self.mode_4ch = QRadioButton()
        self.mode_8ch = QRadioButton()
        self.mode_4ch.setChecked(True)
        self.mode_group.addButton(self.mode_4ch, 0)
        self.mode_group.addButton(self.mode_8ch, 1)

        self.search_timer_a = QTimer(self)
        self.search_timer_a.timeout.connect(lambda: self._search_devices("a"))
        self.search_timer_a.setSingleShot(True)

        self.search_timer_b = QTimer(self)
        self.search_timer_b.timeout.connect(lambda: self._search_devices("b"))
        self.search_timer_b.setSingleShot(True)

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()

        if DEBUG_MOCK:
            self._add_default_debug_device()
            self._sync_device_card_states()

        if self._top:
            self._sync_from_top()

    def _sync_from_top(self):
        if not self._top:
            return
        for label, attr_suffix in [("A", "a"), ("B", "b")]:
            n6705c = getattr(self._top, f"n6705c_{attr_suffix}", None)
            is_conn = getattr(self._top, f"is_connected_{attr_suffix}", False)
            visa_res = getattr(self._top, f"visa_resource_{attr_suffix}", "")
            serial = getattr(self._top, f"serial_{attr_suffix}", "")
            if is_conn and n6705c:
                if label == "A":
                    self.n6705c_a = n6705c
                    self.is_connected_a = True
                elif label == "B":
                    self.n6705c_b = n6705c
                    self.is_connected_b = True
                display_serial = serial if serial else (visa_res.split("::")[1] if "::" in visa_res else visa_res)
                self._assign_slot(label, display_serial, "N6705C", visa_res)
                self._ensure_device_card_exists(display_serial, "N6705C", visa_res)
        self._refresh_channel_config()
        self._sync_device_card_states()

    def _ensure_device_card_exists(self, serial, model, visa_resource):
        existing_serials = {c.property("serial") for c in self.device_cards}
        if serial in existing_serials:
            return
        display_ip = visa_resource
        if "TCPIP" in visa_resource and "::" in visa_resource:
            parts = visa_resource.split("::")
            if len(parts) >= 2:
                display_ip = parts[1]
        card = self._create_device_card(serial, model, display_ip, visa_resource)
        self.device_list_layout.insertWidget(
            self.device_list_layout.count() - 1, card
        )
        self.device_cards.append(card)

    @staticmethod
    def _get_checkmark_path(accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            _get_base_path(),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

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

            QLabel#pageTitle {
                font-size: 18px;
                font-weight: 700;
                color: #f8fbff;
                background-color: transparent;
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
                color: #8eb0e3;
                font-size: 11px;
                background-color: transparent;
            }

            QLabel#hintLabel {
                color: #5c7a9e;
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
                border-radius: 14px;
            }

            QFrame#topControlsFrame {
                background-color: #0a1733;
                border: 1px solid #1a2b52;
                border-radius: 16px;
            }

            QFrame#chartFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 14px;
            }

            QFrame#chResultCard {
                background-color: #0a1733;
                border: 1px solid #1a2b52;
                border-radius: 10px;
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
                border-radius: 8px;
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
                border-radius: 9px;
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
                color: #5c7096;
                border: 1px solid #1a2850;
            }

            QPushButton#chartToolBtn {
                min-height: 28px;
                padding: 4px 12px;
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
                font-size: 11px;
            }

            QPushButton#chartToolBtn:hover {
                background-color: #1a3260;
                border: 1px solid #3c5fa1;
            }

            QPushButton#primaryActionBtn {
                min-height: 40px;
                border-radius: 10px;
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
                border-radius: 8px;
                background-color: #16284f;
                color: #dfe8ff;
            }

            QPushButton#exportBtn:hover {
                background-color: #1e3466;
            }

            QPushButton#addLabelBtn {
                min-height: 30px;
                padding: 0px 8px;
                border-radius: 8px;
                background-color: #5b5cf6;
                color: white;
                font-size: 16px;
                font-weight: 700;
            }

            QPushButton#addLabelBtn:hover {
                background-color: #6b6cff;
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
        """ + SCROLL_AREA_STYLE).replace("__UNCHECKED__", _cb_icons['unchecked']).replace("__CHECKED__", _cb_icons['checked'])
        self.setStyleSheet(full_style)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(6, 6, 6, 6)
        root_layout.setSpacing(6)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_row = QHBoxLayout()
        icon_lbl = QLabel("\u2728")
        icon_lbl.setStyleSheet("font-size: 20px; color: #d4a514;")
        self.page_title = QLabel("Keysight N6705C Datalog Analyzer")
        self.page_title.setObjectName("pageTitle")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(self.page_title)
        title_row.addStretch()
        title_layout.addLayout(title_row)

        self.page_subtitle = QLabel(
            "Record, analyze, and export high-resolution datalogs from the N6705C."
        )
        self.page_subtitle.setObjectName("pageSubtitle")
        title_layout.addWidget(self.page_subtitle)

        root_layout.addLayout(title_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(6)
        root_layout.addLayout(content_layout, 1)

        instr_sidebar = QWidget()
        instr_sidebar.setStyleSheet("QWidget { background: transparent; }")
        instr_sidebar_layout = QHBoxLayout(instr_sidebar)
        instr_sidebar_layout.setContentsMargins(0, 0, 0, 0)
        instr_sidebar_layout.setSpacing(0)

        self.instrument_toggle_btn = VerticalTextButton("Instrument Connection")
        self.instrument_toggle_btn.clicked.connect(self._toggle_instrument_panel)
        instr_sidebar_layout.addWidget(self.instrument_toggle_btn, 0, Qt.AlignTop)

        self.instrument_panel = QFrame()
        self.instrument_panel.setObjectName("topControlsFrame")
        self.instrument_panel.setFixedWidth(360)
        self.instrument_panel.hide()
        instr_inner = QVBoxLayout(self.instrument_panel)
        instr_inner.setContentsMargins(8, 8, 8, 8)
        instr_inner.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.refresh_search_btn = SpinningSearchButton()
        self.refresh_search_btn.setFixedSize(40, 40)
        self.refresh_search_btn.setStyleSheet("""
            QPushButton {
                background-color: #13254b;
                border: 1px solid #22376A;
                border-radius: 8px;
                color: #dce7ff;
                font-weight: 600;
                min-height: 0px;
                max-height: 40px;
                min-width: 0px;
                max-width: 40px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #1C2D55;
                border: 1px solid #3A5A9F;
            }
            QPushButton:pressed {
                background-color: #102040;
            }
        """)
        self.refresh_search_btn.clicked.connect(self._on_refresh_search)
        search_row.addWidget(self.refresh_search_btn)
        search_row.addStretch()

        self.instr_more_btn = QToolButton()
        self.instr_more_btn.setText("⋯")
        self.instr_more_btn.setFixedSize(40, 40)
        self.instr_more_btn.setPopupMode(QToolButton.InstantPopup)
        self.instr_more_btn.setStyleSheet("""
            QToolButton {
                background-color: #13254b;
                color: #8eb0e3;
                font-size: 18px;
                font-weight: bold;
                border: 1px solid #22376A;
                border-radius: 8px;
                padding: 0px;
                min-height: 0px;
                max-height: 40px;
                min-width: 0px;
                max-width: 40px;
            }
            QToolButton:hover {
                background-color: #1C2D55;
                border: 1px solid #3A5A9F;
            }
            QToolButton::menu-indicator { image: none; }
        """)
        instr_more_menu = QMenu(self.instr_more_btn)
        instr_more_menu.setStyleSheet("""
            QMenu {
                background-color: #0c1a35;
                border: 1px solid #1e3460;
                color: #c8daf5;
                font-size: 11px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
            }
            QMenu::item:selected {
                background-color: #1e3460;
            }
        """)
        add_manual_action = instr_more_menu.addAction("\U0001F517  Add Instrument Manually")
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
        separator.setStyleSheet("background-color: #1b2c4f;")
        instr_inner.addWidget(separator)

        slot_title = QLabel("\u26A1  Available Instruments")
        slot_title.setObjectName("cardTitle")
        instr_inner.addWidget(slot_title)

        slot_grid = QGridLayout()
        slot_grid.setSpacing(6)

        self.slot_frames = {}
        for idx, label_char in enumerate(["A", "B", "C", "D"]):
            slot = self._create_slot_widget(label_char)
            row, col = divmod(idx, 2)
            slot_grid.addWidget(slot, row, col)
            self.slot_frames[label_char] = slot

        instr_inner.addLayout(slot_grid)

        instr_sidebar_layout.addWidget(self.instrument_panel)

        content_layout.addWidget(instr_sidebar)

        main_area = QVBoxLayout()
        main_area.setSpacing(6)
        content_layout.addLayout(main_area, 1)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(6)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFixedWidth(240)

        left_container = QWidget()
        left_container.setStyleSheet("background: transparent;")
        self.left_layout = QVBoxLayout(left_container)
        self.left_layout.setContentsMargins(0, 6, 4, 0)
        self.left_layout.setSpacing(14)

        self.config_card = CardFrame("DATALOG CONFIG", "\u2699")
        self._build_config_card()
        self.left_layout.addWidget(self.config_card)

        self.meas_settings_card = CardFrame("Measurement Settings", "\u25CE")
        self._build_meas_settings_card()
        self.left_layout.addWidget(self.meas_settings_card)

        self.left_layout.addStretch()

        self.start_btn = QPushButton("\u25B7  Start Recording")
        self.start_btn.setObjectName("primaryActionBtn")
        self.start_btn.setProperty("running", "false")
        self.left_layout.addWidget(self.start_btn)

        self.export_btn = QPushButton("\u2913  Export Datalog")
        self.export_btn.setObjectName("exportBtn")
        self.left_layout.addWidget(self.export_btn)

        self.import_btn = QPushButton("\u2912  Import Datalog")
        self.import_btn.setObjectName("exportBtn")
        self.left_layout.addWidget(self.import_btn)

        left_scroll.setWidget(left_container)
        mid_layout.addWidget(left_scroll)

        center_right_layout = QVBoxLayout()
        center_right_layout.setSpacing(6)

        chart_and_labels = QHBoxLayout()
        chart_and_labels.setSpacing(6)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartFrame")
        chart_outer = QVBoxLayout(self.chart_frame)
        chart_outer.setContentsMargins(12, 10, 12, 10)
        chart_outer.setSpacing(8)

        chart_header = QHBoxLayout()
        chart_icon = QLabel("\u2728")
        chart_icon.setStyleSheet("font-size: 16px; color: #d4a514;")
        chart_title = QLabel("Datalog Viewer")
        chart_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #f4f7ff;"
        )
        chart_header.addWidget(chart_icon)
        chart_header.addWidget(chart_title)
        chart_header.addStretch()

        self.box_zoom_btn = QPushButton("\u2316 Box Zoom: OFF")
        self.box_zoom_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.box_zoom_btn)

        self.reset_view_btn = QPushButton("\u2316 Auto")
        self.reset_view_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.reset_view_btn)

        self.marker_a_btn = QPushButton("Set Marker A")
        self.marker_a_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.marker_a_btn)

        self.marker_b_btn = QPushButton("Set Marker B")
        self.marker_b_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.marker_b_btn)

        self.clear_markers_btn = QPushButton("Clear Markers")
        self.clear_markers_btn.setObjectName("chartToolBtn")
        chart_header.addWidget(self.clear_markers_btn)

        chart_outer.addLayout(chart_header)

        self.plot_widget = pg.PlotWidget()
        self._setup_plot()

        self.ch_name_labels = []
        self.ch_name_renames = {}
        self._ch_label_items = []

        chart_outer.addWidget(self.plot_widget, 1)

        self._progress_overlay = QFrame(self.chart_frame)
        self._progress_overlay.setStyleSheet(
            "QFrame { background-color: rgba(2, 8, 23, 180); border: none; border-radius: 14px; }"
        )
        self._progress_overlay.hide()
        overlay_layout = QVBoxLayout(self._progress_overlay)
        overlay_layout.setAlignment(Qt.AlignCenter)
        overlay_layout.setSpacing(12)

        self._progress_stage_label = QLabel("Preparing...")
        self._progress_stage_label.setAlignment(Qt.AlignCenter)
        self._progress_stage_label.setStyleSheet(
            "color: #c8daf5; font-size: 13px; font-weight: 600; background: transparent;"
        )
        overlay_layout.addWidget(self._progress_stage_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFixedWidth(320)
        self._progress_bar.setFixedHeight(18)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #152749;
                border: 1px solid #27406f;
                border-radius: 9px;
                text-align: center;
                color: #b7c8ea;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:1 #7c3aed);
                border-radius: 8px;
            }
        """)
        overlay_layout.addWidget(self._progress_bar, 0, Qt.AlignCenter)

        self._progress_time_label = QLabel("")
        self._progress_time_label.setAlignment(Qt.AlignCenter)
        self._progress_time_label.setStyleSheet(
            "color: #5c7a9e; font-size: 11px; background: transparent;"
        )
        overlay_layout.addWidget(self._progress_time_label)

        chart_and_labels.addWidget(self.chart_frame, 1)

        self.label_card = CardFrame("CUSTOM LABELS", "\u2756")
        self._build_label_card()
        self.label_card.setFixedWidth(240)
        chart_and_labels.addWidget(self.label_card)

        center_right_layout.addLayout(chart_and_labels, 1)

        self.measurement_card = CardFrame("MEASUREMENT", "\u25CE")
        self._build_measurement_card()
        center_right_layout.addWidget(self.measurement_card)

        mid_layout.addLayout(center_right_layout, 1)
        main_area.addLayout(mid_layout, 1)

        self.channel_config_collapsed = False

        self.channel_config_outer = QWidget()
        self.channel_config_outer.setStyleSheet("QWidget { background: transparent; border: none; }")
        ch_outer_layout = QVBoxLayout(self.channel_config_outer)
        ch_outer_layout.setContentsMargins(0, 0, 0, 0)
        ch_outer_layout.setSpacing(0)

        self.channel_config_toggle_btn = QPushButton("\u25bc  \u2699 Channel Config")
        self.channel_config_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a1930; color: #b8d0f0;
                border: 1px solid #132849; border-bottom: none;
                border-top-left-radius: 8px; border-top-right-radius: 8px;
                border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
                padding: 4px 16px; font-size: 12px; font-weight: 700;
                text-align: left;
            }
            QPushButton:hover { background-color: #0e1f3d; color: #d0e4ff; }
        """)
        self.channel_config_toggle_btn.clicked.connect(self._toggle_channel_config_panel)
        ch_outer_layout.addWidget(self.channel_config_toggle_btn)

        self.channel_config_card = CardFrame("", "")
        self.channel_config_card.setStyleSheet("""
            #cardFrame {
                background-color: #0a1930;
                border: 1px solid #132849;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        self._build_channel_config_card()
        self.channel_config_card.setVisible(True)
        ch_outer_layout.addWidget(self.channel_config_card)

        main_area.addWidget(self.channel_config_outer)

        self._channel_config_overlay = QFrame(self.channel_config_card)
        self._channel_config_overlay.setStyleSheet(
            "QFrame { background-color: rgba(2, 8, 23, 160); border: none; border-radius: 14px; }"
        )
        self._channel_config_overlay.hide()
        ch_overlay_layout = QVBoxLayout(self._channel_config_overlay)
        ch_overlay_layout.setAlignment(Qt.AlignCenter)
        ch_lock_label = QLabel("\U0001F512  Recording in progress...")
        ch_lock_label.setAlignment(Qt.AlignCenter)
        ch_lock_label.setStyleSheet(
            "color: #5c7a9e; font-size: 12px; font-weight: 600; background: transparent;"
        )
        ch_overlay_layout.addWidget(ch_lock_label)

    def _build_measurement_card(self):
        layout = self.measurement_card.main_layout

        self.meas_table = QTableWidget()
        self.meas_table.setObjectName("measTable")
        self.meas_table.setStyleSheet("""
            QTableWidget#measTable {
                background-color: transparent;
                border: none;
                gridline-color: #152040;
                color: #c8daf5;
                font-size: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            QTableWidget#measTable::item {
                padding: 2px 8px;
            }
            QTableWidget#measTable::item:selected {
                background-color: transparent;
                color: inherit;
            }
            QTableWidget#measTable QHeaderView::section {
                background-color: #0b1528;
                color: #5a7fad;
                font-weight: 600;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
                padding: 3px 8px;
                border: none;
                border-bottom: 1px solid #1e3460;
                border-right: 1px solid #12203a;
            }
            QTableWidget#measTable QHeaderView::section:last {
                border-right: none;
            }
            QTableWidget#measTable QTableCornerButton::section {
                background-color: #0b1528;
                border: none;
                border-bottom: 1px solid #1e3460;
            }
            QTableWidget#measTable QScrollBar {
                width: 0px;
                height: 0px;
            }
        """)
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

    def _create_slot_widget(self, label_char):
        frame = QFrame()
        frame.setObjectName("cardFrame")
        frame.setFixedHeight(60)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        letter = QLabel(label_char)
        letter.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #3a6fd4; border: none;"
        )
        letter.setFixedWidth(24)
        layout.addWidget(letter)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel("Not Supported")
        name_label.setStyleSheet("font-size: 11px; color: #556a8c; border: none;")
        info_layout.addWidget(name_label)
        layout.addLayout(info_layout, 1)

        frame.setProperty("slot_label", label_char)
        frame.setProperty("name_label", name_label)
        frame.setProperty("assigned_serial", "")
        frame.setProperty("connected", False)
        frame.setContextMenuPolicy(Qt.CustomContextMenu)
        frame.customContextMenuRequested.connect(
            lambda pos, f=frame: self._on_slot_context_menu(f, pos)
        )

        return frame

    def _create_device_card(self, serial, model, ip_addr, visa_resource):
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setFixedHeight(70)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(10)

        icon_layout = QVBoxLayout()
        icon_layout.setSpacing(2)
        thumb_label = QLabel()
        thumb_label.setStyleSheet("border: none;")
        thumb_label.setFixedSize(64, 38)
        svg_path = os.path.join(_get_base_path(), "resources", "icons", "n6705c_thumb.svg")
        if os.path.exists(svg_path):
            pixmap = QPixmap(64, 38)
            pixmap.fill(QColor(0, 0, 0, 0))
            renderer = QSvgRenderer(svg_path)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            thumb_label.setPixmap(pixmap)
        serial_label = QLabel(serial)
        serial_label.setStyleSheet("font-size: 9px; color: #556a8c; border: none;")
        serial_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(thumb_label)
        icon_layout.addWidget(serial_label)
        card_layout.addLayout(icon_layout)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        model_label = QLabel(model)
        model_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #eaf2ff; border: none;")
        ip_label = QLabel(ip_addr)
        ip_label.setStyleSheet("font-size: 11px; color: #8eb0e3; border: none;")
        info_layout.addWidget(model_label)
        info_layout.addWidget(ip_label)
        card_layout.addLayout(info_layout, 1)

        connect_btn = QPushButton()
        update_connect_button_state(connect_btn, connected=False)
        connect_btn.setFixedWidth(120)
        connect_btn.clicked.connect(lambda: self._on_device_connect(visa_resource, serial))
        card_layout.addWidget(connect_btn)

        disconnect_btn = QPushButton()
        update_connect_button_state(disconnect_btn, connected=True)
        disconnect_btn.setFixedWidth(120)
        disconnect_btn.clicked.connect(lambda: self._on_device_disconnect(serial))
        disconnect_btn.hide()
        card_layout.addWidget(disconnect_btn)

        card.setProperty("visa_resource", visa_resource)
        card.setProperty("serial", serial)
        card.setProperty("connect_btn", connect_btn)
        card.setProperty("disconnect_btn", disconnect_btn)

        return card

    def _on_refresh_search(self):
        for card in self.device_cards:
            self.device_list_layout.removeWidget(card)
            card.deleteLater()
        self.device_cards.clear()

        if DEBUG_MOCK:
            self._add_default_debug_device()

        self.refresh_search_btn.setEnabled(False)
        self.refresh_search_btn.start_spinning()

        self._scan_thread = QThread()
        self._scan_worker = _ScanWorker(self.rm)
        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_worker.device_found.connect(self._on_scan_device_found)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(lambda e: None)
        self._scan_thread.started.connect(self._scan_worker.run)

        self._scan_thread.start()

    def _on_scan_device_found(self, serial, model, ip, visa_resource):
        card = self._create_device_card(serial, model, ip, visa_resource)
        self.device_list_layout.insertWidget(
            self.device_list_layout.count() - 1, card
        )
        self.device_cards.append(card)

    def _on_scan_finished(self):
        if hasattr(self, '_scan_worker') and self._scan_worker:
            self.rm = self._scan_worker.rm
        self.refresh_search_btn.stop_spinning()
        self.refresh_search_btn.setEnabled(True)
        if hasattr(self, '_scan_thread'):
            self._scan_thread.quit()
            self._scan_thread.wait()
        self._sync_device_card_states()

    def _sync_device_card_states(self):
        connected_serials = set()
        for label_char in ["A", "B", "C", "D"]:
            s = self.slot_frames[label_char].property("assigned_serial")
            if s:
                connected_serials.add(s.strip())

        for card in self.device_cards:
            card_serial = (card.property("serial") or "").strip()
            connect_btn = card.property("connect_btn")
            disconnect_btn = card.property("disconnect_btn")
            if card_serial in connected_serials:
                if connect_btn:
                    connect_btn.hide()
                if disconnect_btn:
                    disconnect_btn.show()
            else:
                if connect_btn:
                    connect_btn.show()
                if disconnect_btn:
                    disconnect_btn.hide()

    def _find_next_free_slot(self):
        for label_char in ["A", "B", "C", "D"]:
            slot = self.slot_frames[label_char]
            if not slot.property("assigned_serial"):
                return label_char
        return None

    def _on_device_connect(self, visa_resource, serial):
        slot_label = self._find_next_free_slot()
        if slot_label is None:
            return

        for card in self.device_cards:
            if card.property("serial") == serial:
                btn = card.property("connect_btn")
                if btn:
                    btn.setEnabled(False)
                    btn.setText("Connecting...")
                break

        self._connect_thread = QThread()
        self._connect_worker = _ConnectWorker(visa_resource, serial, DEBUG_MOCK)
        self._connect_worker.moveToThread(self._connect_thread)

        self._connect_worker.success.connect(
            lambda n6705c, s, r: self._on_connect_success(n6705c, s, r, slot_label)
        )
        self._connect_worker.error.connect(
            lambda e: self._on_connect_error(serial)
        )
        self._connect_worker.finished.connect(self._on_connect_thread_done)
        self._connect_thread.started.connect(self._connect_worker.run)

        self._connect_thread.start()

    def _on_connect_success(self, n6705c, serial, visa_resource, slot_label):
        if slot_label == "A":
            self.n6705c_a = n6705c
            self.is_connected_a = True
            if self._top:
                self._top.connect_a(visa_resource, n6705c_instance=n6705c, serial=serial)
        elif slot_label == "B":
            self.n6705c_b = n6705c
            self.is_connected_b = True
            if self._top:
                self._top.connect_b(visa_resource, n6705c_instance=n6705c, serial=serial)

        self._assign_slot(slot_label, serial, "N6705C", visa_resource)

        self.connection_status_changed.emit(self.is_connected_a)
        self._refresh_channel_config()
        self._sync_device_card_states()

    def _on_connect_error(self, serial):
        for card in self.device_cards:
            if card.property("serial") == serial:
                btn = card.property("connect_btn")
                if btn:
                    btn.setEnabled(True)
                    btn.setText("Connect")
                break

    def _on_connect_thread_done(self):
        if hasattr(self, '_connect_thread'):
            self._connect_thread.quit()
            self._connect_thread.wait()

    def _on_slot_context_menu(self, frame, pos):
        serial = frame.property("assigned_serial")
        if not serial:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0c1a35;
                border: 1px solid #1e3460;
                color: #c8daf5;
                font-size: 11px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #1e3460;
            }
        """)
        disconnect_action = menu.addAction("Disconnect")
        action = menu.exec(frame.mapToGlobal(pos))
        if action == disconnect_action:
            self._on_device_disconnect(serial)

    def _on_device_disconnect(self, serial):
        n6705c_to_close = None
        should_close_locally = True
        for label_char in ["A", "B", "C", "D"]:
            slot = self.slot_frames[label_char]
            if slot.property("assigned_serial") == serial:
                self._clear_slot(label_char)

                if label_char == "A":
                    n6705c_to_close = self.n6705c_a
                    self.n6705c_a = None
                    self.is_connected_a = False
                    if self._top:
                        self._top.disconnect_a()
                        should_close_locally = False
                elif label_char == "B":
                    n6705c_to_close = self.n6705c_b
                    self.n6705c_b = None
                    self.is_connected_b = False
                    if self._top:
                        self._top.disconnect_b()
                        should_close_locally = False
                break

        self.connection_status_changed.emit(self.is_connected_a)
        self._refresh_channel_config()
        self._sync_device_card_states()

        if n6705c_to_close and should_close_locally:
            import threading
            threading.Thread(
                target=self._close_instrument, args=(n6705c_to_close,), daemon=True
            ).start()

    @staticmethod
    def _close_instrument(n6705c):
        try:
            n6705c.disconnect()
        except Exception:
            pass

    def _assign_slot(self, label_char, serial, model, visa_resource):
        slot = self.slot_frames[label_char]
        slot.setProperty("assigned_serial", serial)
        slot.setProperty("connected", True)
        slot.setStyleSheet("""
            QFrame#cardFrame {
                background-color: #0c2254;
                border: 1px solid #3a6fd4;
                border-radius: 14px;
            }
        """)
        name_label = slot.property("name_label")
        name_label.setText(f"{model}\n{serial}\n{visa_resource.split('::')[1] if '::' in visa_resource else ''}")
        name_label.setStyleSheet("font-size: 10px; color: #8eb0e3; border: none;")

        letter = slot.findChildren(QLabel)[0]
        letter.setStyleSheet("font-size: 18px; font-weight: bold; color: #4ae68a; border: none;")

    def _clear_slot(self, label_char):
        slot = self.slot_frames[label_char]
        slot.setProperty("assigned_serial", "")
        slot.setProperty("connected", False)
        slot.setStyleSheet("")
        name_label = slot.property("name_label")
        name_label.setText("Not Supported")
        name_label.setStyleSheet("font-size: 11px; color: #556a8c; border: none;")

        letter = slot.findChildren(QLabel)[0]
        letter.setStyleSheet("font-size: 18px; font-weight: bold; color: #3a6fd4; border: none;")

    def _build_config_card(self):
        layout = self.config_card.main_layout

        param_grid = QGridLayout()
        param_grid.setHorizontalSpacing(10)
        param_grid.setVerticalSpacing(6)

        sp_label = QLabel("Sampling\nPeriod (\u00B5s)")
        sp_label.setObjectName("fieldLabel")
        self.sample_period_edit = QLineEdit("20")
        self.sample_period_edit.setFixedWidth(80)
        self.sample_period_edit.editingFinished.connect(self._validate_sample_period)

        self.min_period_cb = QCheckBox("Minimum")
        self.min_period_cb.setStyleSheet("font-size: 10px; color: #8eb0e3;")
        self.min_period_cb.stateChanged.connect(self._on_min_period_toggled)

        mt_label = QLabel("Monitoring\nTime (s)")
        mt_label.setObjectName("fieldLabel")
        self.monitor_time_edit = QLineEdit("5")
        self.monitor_time_edit.setFixedWidth(80)

        param_grid.addWidget(sp_label, 0, 0)
        param_grid.addWidget(mt_label, 0, 1)
        param_grid.addWidget(self.sample_period_edit, 1, 0)
        param_grid.addWidget(self.monitor_time_edit, 1, 1)
        param_grid.addWidget(self.min_period_cb, 2, 0)

        layout.addLayout(param_grid)

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
        self.label_time_edit.setPlaceholderText("Input label time")
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

        self.add_label_btn = QPushButton("+")
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

        self.channel_config_tab = QTabWidget()
        self.channel_config_tab.setDocumentMode(True)
        self.channel_config_tab.tabBar().setDrawBase(False)
        self.channel_config_tab.setStyleSheet("""
            QTabWidget::pane {
                border-top: 1px solid #1a2b52;
                background-color: transparent;
                margin-top: -1px;
            }
            QTabBar {
                background: transparent;
            }
            QTabBar::tab {
                background-color: #0b1630;
                color: #4a6a96;
                border: 1px solid #1a2b52;
                border-bottom: 1px solid #1a2b52;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 5px 14px;
                margin-right: 1px;
                font-size: 11px;
                font-weight: 600;
                min-width: 60px;
            }
            QTabBar::tab:selected {
                background-color: #071127;
                color: #dce7ff;
                border: 1px solid #1a2b52;
                border-bottom: 1px solid #071127;
            }
            QTabBar::tab:hover:!selected {
                background-color: #0e1d40;
                color: #8eb0e3;
            }
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
        """)
        self.channel_config_layout.addWidget(self.channel_config_tab)

        self._instruments_tab = QWidget()
        self._instruments_tab.setStyleSheet("background: #071127;")
        self._instruments_tab.setMinimumHeight(140)
        self._instruments_tab_layout = QVBoxLayout(self._instruments_tab)
        self._instruments_tab_layout.setContentsMargins(0, 6, 0, 0)
        self._instruments_tab_layout.setSpacing(0)
        self.channel_config_tab.addTab(self._instruments_tab, "\u26A1 Active")
        self.channel_config_tab.setTabsClosable(False)

        self.channel_config_inner = QWidget()
        self.channel_config_inner.setStyleSheet("background: #071127;")
        self.channel_config_inner_layout = QHBoxLayout(self.channel_config_inner)
        self.channel_config_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_config_inner_layout.setSpacing(0)
        self._instruments_tab_layout.addWidget(self.channel_config_inner)

        self.ch_checkboxes_a = []
        self.ch_voltage_cbs_a = []
        self.ch_current_cbs_a = []
        self.ch_power_cbs_a = []
        self.ch_checkboxes_b = []
        self.ch_voltage_cbs_b = []
        self.ch_current_cbs_b = []
        self.ch_power_cbs_b = []
        self.unit_a_ch_label = QLabel()
        self.unit_a_ch_label.hide()
        self.unit_b_ch_label = QLabel()
        self.unit_b_ch_label.hide()
        self.ch_row_b_widget = QWidget()
        self.ch_row_b_widget.hide()

        self.no_instrument_label = QLabel("No instruments connected. Open Instrument Connection panel to connect.")
        self.no_instrument_label.setObjectName("hintLabel")
        self.no_instrument_label.setAlignment(Qt.AlignCenter)
        self._instruments_tab_layout.addWidget(self.no_instrument_label)

    def _toggle_channel_config_panel(self):
        self.channel_config_collapsed = not self.channel_config_collapsed
        self.channel_config_card.setVisible(not self.channel_config_collapsed)
        if self.channel_config_collapsed:
            self.channel_config_toggle_btn.setText("\u25b6  \u2699 Channel Config")
            self.channel_config_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930; color: #8ea6cf;
                    border: 1px solid #132849; border-radius: 8px;
                    padding: 4px 16px; font-size: 12px; font-weight: 700; text-align: left;
                }
                QPushButton:hover { background-color: #0e1f3d; color: #b8d0f0; }
            """)
        else:
            self.channel_config_toggle_btn.setText("\u25bc  \u2699 Channel Config")
            self.channel_config_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a1930; color: #b8d0f0;
                    border: 1px solid #132849; border-bottom: none;
                    border-top-left-radius: 8px; border-top-right-radius: 8px;
                    border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
                    padding: 4px 16px; font-size: 12px; font-weight: 700; text-align: left;
                }
                QPushButton:hover { background-color: #0e1f3d; color: #d0e4ff; }
            """)

    def _refresh_channel_config(self):
        connected_slots = []
        for label_char in ["A", "B", "C", "D"]:
            slot = self.slot_frames[label_char]
            if slot.property("assigned_serial"):
                connected_slots.append(label_char)

        old_inner = self.channel_config_inner
        self._instruments_tab_layout.removeWidget(old_inner)
        old_inner.deleteLater()

        self.channel_config_inner = QWidget()
        self.channel_config_inner.setStyleSheet("background: #071127;")
        inner_layout = QHBoxLayout(self.channel_config_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        self.channel_config_inner_layout = inner_layout

        self.ch_checkboxes_a = []
        self.ch_voltage_cbs_a = []
        self.ch_current_cbs_a = []
        self.ch_power_cbs_a = []
        self.ch_checkboxes_b = []
        self.ch_voltage_cbs_b = []
        self.ch_current_cbs_b = []
        self.ch_power_cbs_b = []

        if not connected_slots:
            self.no_instrument_label.show()
            self._instruments_tab_layout.insertWidget(0, self.channel_config_inner)
            return

        self.no_instrument_label.hide()

        for slot_char in connected_slots:
            slot = self.slot_frames[slot_char]
            serial = slot.property("assigned_serial")

            slot_frame = QFrame()
            slot_frame.setStyleSheet("""
                QFrame {
                    background-color: #071127;
                    border: none;
                }
            """)
            slot_layout = QVBoxLayout(slot_frame)
            slot_layout.setContentsMargins(6, 4, 6, 4)
            slot_layout.setSpacing(0)

            slot_title = QLabel(f"Slot {slot_char}  ─  {serial}")
            slot_title.setStyleSheet(
                "color: #556a8c; font-size: 10px; border: none; padding-bottom: 2px;"
            )
            slot_layout.addWidget(slot_title)

            outputs_row = QHBoxLayout()
            outputs_row.setContentsMargins(0, 0, 0, 0)
            outputs_row.setSpacing(4)
            slot_layout.addLayout(outputs_row)

            voltage_cbs = []
            current_cbs = []
            power_cbs = []

            edit_style = (
                "QLineEdit { background: #0c1a35; color: #8eb0e3; font-size: 10px; "
                "border: 1px solid #1e3460; border-radius: 2px; }"
                "QLineEdit:focus { border-color: #3a6aad; }"
            )

            for ch in range(4):
                ch_color = CHANNEL_COLORS[ch % len(CHANNEL_COLORS)]

                out_frame = QFrame()
                out_frame.setMaximumWidth(260)
                out_frame.setStyleSheet(
                    "QFrame { background-color: #0a1430; border: 1px solid #152040; border-radius: 4px; }"
                )
                out_vbox = QVBoxLayout(out_frame)
                out_vbox.setContentsMargins(4, 2, 4, 3)
                out_vbox.setSpacing(1)

                title_lbl = QLabel(f"OUTPUT {ch + 1}")
                title_lbl.setAlignment(Qt.AlignCenter)
                title_lbl.setStyleSheet(
                    f"color: {ch_color}; font-size: 10px; font-weight: 700; "
                    f"border: none; padding: 1px 0;"
                )
                out_vbox.addWidget(title_lbl)

                for row_idx, (prefix, default_scale, default_offset, unit) in enumerate([
                    ("V", "1V", "0V", "V"),
                    ("I", "1mA", "0mA", "mA"),
                    ("P", "1W", "0W", "W"),
                ]):
                    btn = ToggleLabel(f"{prefix}{ch+1}")
                    btn.setFixedWidth(30)
                    btn.setProperty("ch_color", ch_color)
                    btn.setProperty("ch_idx", ch)
                    btn.setProperty("meas_type", prefix)
                    btn.setStyleSheet(self._ch_toggle_style(ch_color, False))
                    btn.toggled.connect(lambda checked, b=btn: self._on_ch_toggle(b, checked))

                    base_unit = {"V": "mV", "I": "mA", "P": "mW"}.get(prefix, "mA")

                    scale_edit = ScaleOffsetEdit(default_scale)
                    scale_edit.setMinimumWidth(38)
                    scale_edit.setAlignment(Qt.AlignCenter)
                    scale_edit.setStyleSheet(edit_style)
                    scale_edit.setProperty("ch_idx", ch)
                    scale_edit.setProperty("meas_type", prefix)
                    scale_edit.setProperty("field", "scale")
                    scale_edit.setProperty("base_unit", base_unit)

                    sep = QLabel("/")
                    sep.setFixedWidth(8)
                    sep.setAlignment(Qt.AlignCenter)
                    sep.setStyleSheet("color: #3a5070; font-size: 10px; border: none;")

                    offset_edit = ScaleOffsetEdit(default_offset)
                    offset_edit.setMinimumWidth(38)
                    offset_edit.setAlignment(Qt.AlignCenter)
                    offset_edit.setStyleSheet(edit_style)
                    offset_edit.setProperty("ch_idx", ch)
                    offset_edit.setProperty("meas_type", prefix)
                    offset_edit.setProperty("field", "offset")
                    offset_edit.setProperty("base_unit", base_unit)

                    row_layout = QHBoxLayout()
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(1)
                    row_layout.addWidget(btn)
                    row_layout.addWidget(scale_edit)
                    row_layout.addWidget(sep)
                    row_layout.addWidget(offset_edit)

                    container = QWidget()
                    container.setStyleSheet("border: none;")
                    container.setLayout(row_layout)
                    out_vbox.addWidget(container)

                    scale_edit.returnPressed.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.returnPressed.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))
                    scale_edit.wheel_adjusted.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.wheel_adjusted.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))

                    btn.setProperty("scale_edit", scale_edit)
                    btn.setProperty("offset_edit", offset_edit)
                    btn.setProperty("slot_char", slot_char)
                    btn.setProperty("user_edited", False)

                    if prefix == "V":
                        voltage_cbs.append(btn)
                    elif prefix == "I":
                        current_cbs.append(btn)
                    else:
                        power_cbs.append(btn)

                outputs_row.addWidget(out_frame)

            outputs_row.addStretch()

            if slot_char == "A":
                self.ch_checkboxes_a = current_cbs
                self.ch_voltage_cbs_a = voltage_cbs
                self.ch_current_cbs_a = current_cbs
                self.ch_power_cbs_a = power_cbs
            elif slot_char == "B":
                self.ch_checkboxes_b = current_cbs
                self.ch_voltage_cbs_b = voltage_cbs
                self.ch_current_cbs_b = current_cbs
                self.ch_power_cbs_b = power_cbs

            inner_layout.addWidget(slot_frame)

        self._instruments_tab_layout.insertWidget(0, self.channel_config_inner)

    def _build_imported_channel_config(self, tab_name=None, data_keys=None):
        import re

        if data_keys is None:
            data_keys = set(self.datalog_data.keys())

        groups = {}
        for key in data_keys:
            ch_num, mtype, is_b = _parse_ch_label(key)
            if ch_num is None:
                continue
            slot = "B" if is_b else "A"
            groups.setdefault(slot, {})
            groups[slot].setdefault(ch_num, set())
            groups[slot][ch_num].add(mtype)

        if not groups:
            return

        if tab_name is None:
            tab_name = "Imported"

        tab_widget = QWidget()
        tab_widget.setStyleSheet("background: #071127;")
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 6, 0, 0)
        tab_layout.setSpacing(0)

        inner = QWidget()
        inner.setStyleSheet("background: #071127;")
        inner_layout = QHBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        tab_config = {
            "tab_name": tab_name,
            "tab_widget": tab_widget,
            "data_keys": set(data_keys),
            "voltage_cbs_a": [],
            "current_cbs_a": [],
            "power_cbs_a": [],
            "voltage_cbs_b": [],
            "current_cbs_b": [],
            "power_cbs_b": [],
        }

        edit_style = (
            "QLineEdit { background: #0c1a35; color: #8eb0e3; font-size: 10px; "
            "border: 1px solid #1e3460; border-radius: 2px; }"
            "QLineEdit:focus { border-color: #3a6aad; }"
        )

        for slot_char in sorted(groups.keys()):
            ch_map = groups[slot_char]
            max_ch = max(ch_map.keys())

            slot_frame = QFrame()
            slot_frame.setStyleSheet(
                "QFrame { background-color: #071127; border: none; }"
            )
            slot_layout = QVBoxLayout(slot_frame)
            slot_layout.setContentsMargins(6, 4, 6, 4)
            slot_layout.setSpacing(0)

            slot_title = QLabel(f"{tab_name}  ─  Slot {slot_char}")
            slot_title.setStyleSheet(
                "color: #556a8c; font-size: 10px; border: none; padding-bottom: 2px;"
            )
            slot_layout.addWidget(slot_title)

            outputs_row = QHBoxLayout()
            outputs_row.setContentsMargins(0, 0, 0, 0)
            outputs_row.setSpacing(4)
            slot_layout.addLayout(outputs_row)

            voltage_cbs = []
            current_cbs = []
            power_cbs = []

            for ch in range(1, max_ch + 1):
                ch_color = CHANNEL_COLORS[(ch - 1) % len(CHANNEL_COLORS)]
                available_types = ch_map.get(ch, set())

                out_frame = QFrame()
                out_frame.setMaximumWidth(260)
                out_frame.setStyleSheet(
                    "QFrame { background-color: #0a1430; border: 1px solid #152040; border-radius: 4px; }"
                )
                out_vbox = QVBoxLayout(out_frame)
                out_vbox.setContentsMargins(4, 2, 4, 3)
                out_vbox.setSpacing(1)

                title_lbl = QLabel(f"OUTPUT {ch}")
                title_lbl.setAlignment(Qt.AlignCenter)
                title_lbl.setStyleSheet(
                    f"color: {ch_color}; font-size: 10px; font-weight: 700; "
                    f"border: none; padding: 1px 0;"
                )
                out_vbox.addWidget(title_lbl)

                for prefix, default_scale, default_offset, unit in [
                    ("V", "1V", "0V", "V"),
                    ("I", "1mA", "0mA", "mA"),
                    ("P", "1W", "0W", "W"),
                ]:
                    if prefix not in available_types:
                        dummy = ToggleLabel(f"{prefix}{ch}")
                        dummy.setFixedWidth(30)
                        dummy.setProperty("ch_color", ch_color)
                        dummy.setProperty("ch_idx", ch - 1)
                        dummy.setProperty("meas_type", prefix)
                        dummy.setStyleSheet(self._ch_toggle_style(ch_color, False))
                        dummy.setEnabled(False)
                        dummy.setStyleSheet(
                            "background-color: #0a1020; color: #2a3a55; "
                            "font-size: 10px; font-weight: 700; "
                            "border: 1px solid #121e38; border-radius: 2px;"
                        )
                        dummy_scale = QLineEdit(default_scale)
                        dummy_scale.setMinimumWidth(38)
                        dummy_scale.setAlignment(Qt.AlignCenter)
                        dummy_scale.setStyleSheet(edit_style)
                        dummy_scale.setEnabled(False)
                        dummy_sep = QLabel("/")
                        dummy_sep.setFixedWidth(8)
                        dummy_sep.setAlignment(Qt.AlignCenter)
                        dummy_sep.setStyleSheet("color: #3a5070; font-size: 10px; border: none;")
                        dummy_offset = QLineEdit(default_offset)
                        dummy_offset.setMinimumWidth(38)
                        dummy_offset.setAlignment(Qt.AlignCenter)
                        dummy_offset.setStyleSheet(edit_style)
                        dummy_offset.setEnabled(False)
                        row_layout = QHBoxLayout()
                        row_layout.setContentsMargins(0, 0, 0, 0)
                        row_layout.setSpacing(1)
                        row_layout.addWidget(dummy)
                        row_layout.addWidget(dummy_scale)
                        row_layout.addWidget(dummy_sep)
                        row_layout.addWidget(dummy_offset)
                        container = QWidget()
                        container.setStyleSheet("border: none;")
                        container.setLayout(row_layout)
                        out_vbox.addWidget(container)
                        if prefix == "V":
                            voltage_cbs.append(dummy)
                        elif prefix == "I":
                            current_cbs.append(dummy)
                        else:
                            power_cbs.append(dummy)
                        dummy.setProperty("scale_edit", dummy_scale)
                        dummy.setProperty("offset_edit", dummy_offset)
                        dummy.setProperty("slot_char", slot_char)
                        dummy.setProperty("user_edited", False)
                        continue

                    btn = ToggleLabel(f"{prefix}{ch}")
                    btn.setFixedWidth(30)
                    btn.setProperty("ch_color", ch_color)
                    btn.setProperty("ch_idx", ch - 1)
                    btn.setProperty("meas_type", prefix)
                    btn.setStyleSheet(self._ch_toggle_style(ch_color, False))
                    btn.toggled.connect(lambda checked, b=btn: self._on_ch_toggle(b, checked))

                    base_unit = {"V": "mV", "I": "mA", "P": "mW"}.get(prefix, "mA")

                    scale_edit = ScaleOffsetEdit(default_scale)
                    scale_edit.setMinimumWidth(38)
                    scale_edit.setAlignment(Qt.AlignCenter)
                    scale_edit.setStyleSheet(edit_style)
                    scale_edit.setProperty("ch_idx", ch - 1)
                    scale_edit.setProperty("meas_type", prefix)
                    scale_edit.setProperty("field", "scale")
                    scale_edit.setProperty("base_unit", base_unit)

                    sep = QLabel("/")
                    sep.setFixedWidth(8)
                    sep.setAlignment(Qt.AlignCenter)
                    sep.setStyleSheet("color: #3a5070; font-size: 10px; border: none;")

                    offset_edit = ScaleOffsetEdit(default_offset)
                    offset_edit.setMinimumWidth(38)
                    offset_edit.setAlignment(Qt.AlignCenter)
                    offset_edit.setStyleSheet(edit_style)
                    offset_edit.setProperty("ch_idx", ch - 1)
                    offset_edit.setProperty("meas_type", prefix)
                    offset_edit.setProperty("field", "offset")
                    offset_edit.setProperty("base_unit", base_unit)

                    row_layout = QHBoxLayout()
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(1)
                    row_layout.addWidget(btn)
                    row_layout.addWidget(scale_edit)
                    row_layout.addWidget(sep)
                    row_layout.addWidget(offset_edit)

                    container = QWidget()
                    container.setStyleSheet("border: none;")
                    container.setLayout(row_layout)
                    out_vbox.addWidget(container)

                    scale_edit.returnPressed.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.returnPressed.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))
                    scale_edit.wheel_adjusted.connect(
                        lambda se=scale_edit: self._on_scale_offset_edited(se))
                    offset_edit.wheel_adjusted.connect(
                        lambda oe=offset_edit: self._on_scale_offset_edited(oe))

                    btn.setProperty("scale_edit", scale_edit)
                    btn.setProperty("offset_edit", offset_edit)
                    btn.setProperty("slot_char", slot_char)
                    btn.setProperty("user_edited", False)

                    if prefix == "V":
                        voltage_cbs.append(btn)
                    elif prefix == "I":
                        current_cbs.append(btn)
                    else:
                        power_cbs.append(btn)

                outputs_row.addWidget(out_frame)

            outputs_row.addStretch()

            if slot_char == "A":
                tab_config["voltage_cbs_a"] = voltage_cbs
                tab_config["current_cbs_a"] = current_cbs
                tab_config["power_cbs_a"] = power_cbs
            elif slot_char == "B":
                tab_config["voltage_cbs_b"] = voltage_cbs
                tab_config["current_cbs_b"] = current_cbs
                tab_config["power_cbs_b"] = power_cbs

            inner_layout.addWidget(slot_frame)

        tab_layout.addWidget(inner)
        tab_layout.addStretch()

        self._imported_tab_configs.append(tab_config)
        tab_idx = self.channel_config_tab.addTab(tab_widget, f"\U0001F4C4 {tab_name}")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #4a6a96; font-size: 11px; "
            "border: none; border-radius: 3px; padding: 0; margin: 0; min-height: 0; }"
            "QPushButton:hover { background: #2a1525; color: #ff6b6b; }"
        )
        close_btn.clicked.connect(lambda _checked=False, w=tab_widget: self._on_config_tab_close(
            self.channel_config_tab.indexOf(w)))
        self.channel_config_tab.tabBar().setTabButton(tab_idx, QTabBar.RightSide, close_btn)
        tab_config["close_btn"] = close_btn
        self.channel_config_tab.setCurrentIndex(tab_idx)

    def _on_config_tab_close(self, index):
        if index <= 0:
            return
        widget = self.channel_config_tab.widget(index)
        if widget is None:
            return
        tc_to_remove = None
        for tc in self._imported_tab_configs:
            if tc.get("tab_widget") is widget:
                tc_to_remove = tc
                break
        if tc_to_remove:
            removed_keys = tc_to_remove.get("data_keys", set())
            self._imported_tab_configs.remove(tc_to_remove)
            still_used = set()
            for tc in self._imported_tab_configs:
                still_used |= tc.get("data_keys", set())
            for k in removed_keys:
                if k not in still_used:
                    self.datalog_data.pop(k, None)
        self.channel_config_tab.removeTab(index)
        if widget:
            widget.deleteLater()
        self._refresh_plot()

    def _ch_toggle_style(self, color, active):
        if active:
            return (
                f"background-color: {color}; color: #ffffff; "
                f"font-size: 10px; font-weight: 800; "
                f"border: 1px solid {color}; border-radius: 2px;"
            )
        else:
            return (
                "background-color: #152040; color: #8eb0e3; "
                "font-size: 10px; font-weight: 700; "
                "border: 1px solid #1e3460; border-radius: 2px;"
            )

    def _on_ch_toggle(self, btn, checked):
        ch_color = btn.property("ch_color")
        btn.setStyleSheet(self._ch_toggle_style(ch_color, checked))
        self._validate_sample_period()

        if checked and btn.property("meas_type") == "P" and self.datalog_data:
            ch_idx = btn.property("ch_idx")
            ch = ch_idx + 1
            slot_char = btn.property("slot_char") or "A"
            is_b_target = (slot_char == "B")
            matched = False
            for key in list(self.datalog_data.keys()):
                c_num, c_type, c_is_b = _parse_ch_label(key)
                if c_num == ch and c_type == "V" and c_is_b == is_b_target:
                    import re
                    pfx_m = re.match(r'^(F\d+-)?', key.strip())
                    pfx = pfx_m.group(1) if pfx_m and pfx_m.group(1) else ""
                    raw_part = key.strip()[len(pfx):]
                    p_key = f"{pfx}{raw_part.replace(' V', ' P')}"
                    if p_key not in self.datalog_data:
                        calc_power_for_ch(self.datalog_data, ch,
                                          raw_part.split("CH")[0].strip() if "CH" in raw_part else "",
                                          key_prefix=pfx)
                    if p_key in self.datalog_data:
                        matched = True
            if matched:
                self._refresh_plot()
                return

        self._on_channel_visibility_changed()

    def _find_all_cbs_for_key(self, data_key):
        ch_num, mtype, is_b = _parse_ch_label(data_key)
        if ch_num is None:
            return []
        slot_char = "B" if is_b else "A"
        prefix = mtype if mtype else "I"
        idx = ch_num - 1

        imported_keys = set()
        for tc in self._imported_tab_configs:
            imported_keys |= tc.get("data_keys", set())

        results = []

        if data_key not in imported_keys:
            src = {
                "voltage_a": getattr(self, 'ch_voltage_cbs_a', []),
                "current_a": getattr(self, 'ch_current_cbs_a', []),
                "power_a": getattr(self, 'ch_power_cbs_a', []),
                "voltage_b": getattr(self, 'ch_voltage_cbs_b', []),
                "current_b": getattr(self, 'ch_current_cbs_b', []),
                "power_b": getattr(self, 'ch_power_cbs_b', []),
            }
            cbs = self._pick_cbs_from_src(src, slot_char, prefix)
            if 0 <= idx < len(cbs):
                results.append(cbs[idx])

        for tc in self._imported_tab_configs:
            if data_key in tc.get("data_keys", set()):
                src = {
                    "voltage_a": tc.get("voltage_cbs_a", []),
                    "current_a": tc.get("current_cbs_a", []),
                    "power_a": tc.get("power_cbs_a", []),
                    "voltage_b": tc.get("voltage_cbs_b", []),
                    "current_b": tc.get("current_cbs_b", []),
                    "power_b": tc.get("power_cbs_b", []),
                }
                cbs = self._pick_cbs_from_src(src, slot_char, prefix)
                if 0 <= idx < len(cbs):
                    results.append(cbs[idx])
        return results

    @staticmethod
    def _pick_cbs_from_src(src, slot_char, prefix):
        if slot_char == "A":
            if prefix == "V":
                return src["voltage_a"]
            elif prefix == "P":
                return src["power_a"]
            else:
                return src["current_a"]
        else:
            if prefix == "V":
                return src["voltage_b"]
            elif prefix == "P":
                return src["power_b"]
            else:
                return src["current_b"]

    def _get_ch_scale_offset(self, data_key):
        btns = self._find_all_cbs_for_key(data_key)
        if not btns:
            return None, None, False

        btn = btns[0]
        user_edited = btn.property("user_edited") or False
        scale_edit = btn.property("scale_edit")
        offset_edit = btn.property("offset_edit")
        if not scale_edit or not offset_edit:
            return None, None, False

        scale_val = _parse_value_with_unit(scale_edit.text(), _unit_for_label(data_key))
        offset_val = _parse_value_with_unit(offset_edit.text(), _unit_for_label(data_key))
        return scale_val, offset_val, user_edited

    def _set_ch_scale_offset_text(self, data_key, scale_text, offset_text):
        btns = self._find_all_cbs_for_key(data_key)
        for btn in btns:
            scale_edit = btn.property("scale_edit")
            offset_edit = btn.property("offset_edit")
            if scale_edit:
                scale_edit.setText(scale_text)
            if offset_edit:
                offset_edit.setText(offset_text)
            btn.setProperty("user_edited", False)

    def _on_scale_offset_edited(self, edit_widget):
        ch_idx = edit_widget.property("ch_idx")
        meas_type = edit_widget.property("meas_type")
        field = edit_widget.property("field")

        all_btn_lists = [
            getattr(self, 'ch_voltage_cbs_a', []),
            getattr(self, 'ch_current_cbs_a', []),
            getattr(self, 'ch_power_cbs_a', []),
            getattr(self, 'ch_voltage_cbs_b', []),
            getattr(self, 'ch_current_cbs_b', []),
            getattr(self, 'ch_power_cbs_b', []),
        ]
        for tc in self._imported_tab_configs:
            for suffix in ["voltage_cbs_a", "current_cbs_a", "power_cbs_a",
                           "voltage_cbs_b", "current_cbs_b", "power_cbs_b"]:
                all_btn_lists.append(tc.get(suffix, []))
        for btn_list in all_btn_lists:
            for btn in btn_list:
                if btn.property("ch_idx") == ch_idx and btn.property("meas_type") == meas_type:
                    btn.setProperty("user_edited", True)
                    break

        self._on_scale_offset_changed()

    def _on_scale_offset_changed(self):
        if not self.datalog_data:
            return

        visible_keys = self._get_visible_keys()
        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        visible_sorted = [k for k in sorted_keys if k in visible_keys]
        n = len(visible_sorted)
        if n == 0:
            return

        for idx, key in enumerate(visible_sorted):
            ch_data = self.datalog_data[key]
            raw_vals = ch_data["values"]
            if not raw_vals:
                continue

            scale_val, offset_val, user_edited = self._get_ch_scale_offset(key)

            band_top = 1.0 - idx / n
            band_bottom = 1.0 - (idx + 1) / n
            margin = (band_top - band_bottom) * 0.08
            plot_top = band_top - margin
            plot_bottom = band_bottom + margin
            plot_range = plot_top - plot_bottom

            if user_edited and scale_val and scale_val > 0 and offset_val is not None:
                num_divs = 5
                half_range = scale_val * num_divs
                display_min = offset_val - half_range
                display_max = offset_val + half_range
                display_range = display_max - display_min
                if display_range == 0:
                    display_range = 1.0

                norm_vals = [
                    plot_bottom + (v - display_min) / display_range * plot_range
                    for v in raw_vals
                ]

                self._band_info[key] = {
                    "raw_min": display_min,
                    "raw_max": display_max,
                    "raw_range": display_range,
                    "band_top": band_top,
                    "band_bottom": band_bottom,
                    "plot_top": plot_top,
                    "plot_bottom": plot_bottom,
                    "plot_range": plot_range,
                }
            else:
                raw_min = min(raw_vals)
                raw_max = max(raw_vals)
                raw_range = raw_max - raw_min
                if raw_range == 0:
                    raw_range = 1.0

                norm_vals = [
                    plot_bottom + (v - raw_min) / raw_range * plot_range
                    for v in raw_vals
                ]

                self._band_info[key] = {
                    "raw_min": raw_min,
                    "raw_max": raw_max,
                    "raw_range": raw_range,
                    "band_top": band_top,
                    "band_bottom": band_bottom,
                    "plot_top": plot_top,
                    "plot_bottom": plot_bottom,
                    "plot_range": plot_range,
                }

            curve = self.plot_curves.get(key)
            if curve:
                times = ch_data["time"]
                curve.setData(times, norm_vals)

        self._update_marker_analysis()

    def _toggle_instrument_panel(self, checked):
        self.instrument_panel.setVisible(checked)

    def _on_add_instrument_manually(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Instrument Manually")
        dialog.setFixedWidth(400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #0a1628;
                color: #c8daf5;
            }
            QLabel {
                color: #8eb0e3;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #0c1a35;
                border: 1px solid #1e3460;
                border-radius: 6px;
                color: #eaf2ff;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #3a6fd4;
            }
            QComboBox {
                background-color: #0c1a35;
                border: 1px solid #1e3460;
                border-radius: 6px;
                color: #eaf2ff;
                padding: 6px 10px;
                font-size: 12px;
            }
            QComboBox:focus {
                border-color: #3a6fd4;
            }
            QComboBox QAbstractItemView {
                background-color: #0c1a35;
                border: 1px solid #1e3460;
                color: #eaf2ff;
                selection-background-color: #1e3460;
            }
            QPushButton {
                background-color: #162d55;
                border: 1px solid #1e3460;
                border-radius: 6px;
                color: #c8daf5;
                padding: 6px 18px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1e3460;
                border-color: #3a6fd4;
            }
        """)

        form_layout = QVBoxLayout(dialog)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(12)

        title = QLabel("\U0001F517  Add Instrument Manually")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #eaf2ff;")
        form_layout.addWidget(title)

        conn_type_label = QLabel("Connection Type")
        form_layout.addWidget(conn_type_label)
        conn_type_combo = QComboBox()
        conn_type_combo.addItems(["TCP/IP (LAN)", "USB"])
        form_layout.addWidget(conn_type_combo)

        ip_label = QLabel("IP Address")
        form_layout.addWidget(ip_label)
        ip_edit = QLineEdit()
        ip_edit.setPlaceholderText("e.g. 192.168.3.99")
        form_layout.addWidget(ip_edit)

        usb_label = QLabel("USB Resource String")
        usb_edit = QLineEdit()
        usb_edit.setPlaceholderText("e.g. USB0::0x2A8D::0x1802::MY56006098::INSTR")
        form_layout.addWidget(usb_label)
        form_layout.addWidget(usb_edit)
        usb_label.hide()
        usb_edit.hide()

        serial_label = QLabel("Serial Number (optional)")
        form_layout.addWidget(serial_label)
        serial_edit = QLineEdit()
        serial_edit.setPlaceholderText("e.g. MY56006098")
        form_layout.addWidget(serial_edit)

        def _on_conn_type_changed(index):
            if index == 0:
                ip_label.show()
                ip_edit.show()
                usb_label.hide()
                usb_edit.hide()
            else:
                ip_label.hide()
                ip_edit.hide()
                usb_label.show()
                usb_edit.show()

        conn_type_combo.currentIndexChanged.connect(_on_conn_type_changed)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        connect_btn = QPushButton("\U0001F517  Connect")
        connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a4b8c;
                border: 1px solid #3a6fd4;
                border-radius: 6px;
                color: #eaf2ff;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #245bb5;
            }
        """)
        connect_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(connect_btn)
        form_layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.Accepted:
            return

        conn_index = conn_type_combo.currentIndex()
        serial = serial_edit.text().strip()

        if conn_index == 0:
            ip = ip_edit.text().strip()
            if not ip:
                return
            visa_resource = f"TCPIP0::{ip}::hislip0::INSTR"
            display_ip = ip
        else:
            usb_str = usb_edit.text().strip()
            if not usb_str:
                return
            visa_resource = usb_str
            display_ip = usb_str

        if not serial:
            serial = visa_resource

        existing_serials = {c.property("serial") for c in self.device_cards}
        if serial in existing_serials:
            return

        card = self._create_device_card(serial, "N6705C", display_ip, visa_resource)
        self.device_list_layout.insertWidget(
            self.device_list_layout.count() - 1, card
        )
        self.device_cards.append(card)
        self._sync_device_card_states()

    def _add_default_debug_device(self):
        existing_serials = {c.property("serial") for c in self.device_cards}
        if "MY56006098" not in existing_serials:
            card = self._create_device_card(
                "MY56006098", "N6705C", "192.168.3.99",
                "TCPIP0::192.168.3.99::hislip0::INSTR"
            )
            self.device_list_layout.insertWidget(self.device_list_layout.count() - 1, card)
            self.device_cards.append(card)

    def _setup_plot(self):
        self.plot_widget.setBackground("#071127")
        self.plot_widget.showGrid(x=True, y=False, alpha=0.15)

        axis_pen = pg.mkPen(color="#2a4272", width=1)
        text_color = "#8eb0e3"

        bottom_axis = self.plot_widget.getPlotItem().getAxis("bottom")
        bottom_axis.setPen(axis_pen)
        bottom_axis.setTextPen(pg.mkPen(text_color))
        bottom_axis.setStyle(tickLength=-5)

        left_axis = self.plot_widget.getPlotItem().getAxis("left")
        left_axis.setPen(pg.mkPen(color="#0a1733"))
        left_axis.setTicks([])
        left_axis.setLabel("")
        left_axis.setWidth(0)

        self.plot_widget.setLabel("bottom", "Time (s)", color=text_color)

        self.plot_widget.setXRange(0, 10)
        self.plot_widget.setYRange(-0.02, 1.02)

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.setMouseEnabled(x=True, y=False)

        self.legend = None

        self.crosshair_v = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color="#4a6a9e", width=1, style=Qt.DashLine)
        )
        self.crosshair_v.setVisible(False)
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)

        self.tooltip_text = pg.TextItem(
            text="", color="#dbe7ff",
            anchor=(1, 1),
            fill=pg.mkBrush(10, 20, 45, 220),
            border=pg.mkPen(color="#2a4272")
        )
        self.tooltip_text.setVisible(False)
        self.tooltip_text.setZValue(100)
        self.plot_widget.addItem(self.tooltip_text, ignoreBounds=True)

        self.plot_curves = {}

        self.proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=30, slot=self._on_mouse_moved
        )

        self.plot_widget.scene().sigMouseClicked.connect(self._on_chart_clicked)

        self.plot_widget.sigRangeChanged.connect(self._on_range_changed)

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.installEventFilter(self)

    def _find_nearest_marker_at_scene(self, scene_pos):
        vb = self.plot_widget.getPlotItem().getViewBox()
        snap_px = self._marker_snap_px
        best = None
        best_dist = snap_px + 1

        for tag, line, pos in [
            ("A", self.marker_a_line, self.marker_a_pos),
            ("B", self.marker_b_line, self.marker_b_pos),
        ]:
            if line is None or pos is None:
                continue
            line_scene_x = vb.mapViewToScene(pg.Point(pos, 0)).x()
            dist = abs(scene_pos.x() - line_scene_x)
            if dist < best_dist:
                best_dist = dist
                best = tag
        return best

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        vb = self.plot_widget.getPlotItem().getViewBox()
        if obj is not vb:
            return super().eventFilter(obj, event)

        if event.type() == QEvent.GraphicsSceneWheel:
            if self._selected_ch_key and self._selected_ch_key in self._band_info:
                self._wheel_scale_channel(event)
                return True

        if event.type() == QEvent.GraphicsSceneMousePress:
            if event.button() == Qt.LeftButton and self._pending_marker is None and not self.box_zoom_enabled:
                scene_pos = event.scenePos()
                snap_marker = self._find_nearest_marker_at_scene(scene_pos)
                if snap_marker:
                    self._marker_drag_target = snap_marker
                    return True

                mouse_point = vb.mapSceneToView(scene_pos)
                y = mouse_point.y()
                clicked_key = self._find_band_at_y(y)
                if clicked_key:
                    self._select_channel(clicked_key)
                    self._ch_drag_active = True
                    self._ch_drag_last_y = y
                    return True
                else:
                    self._deselect_channel()

        if event.type() == QEvent.GraphicsSceneMouseMove:
            scene_pos = event.scenePos()

            if self._marker_drag_target:
                mouse_point = vb.mapSceneToView(scene_pos)
                x_val = mouse_point.x()
                if self._marker_drag_target == "A":
                    self._place_marker_a(x_val)
                else:
                    self._place_marker_b(x_val)
                self._update_marker_region()
                self._update_marker_analysis()
                return True

            if self._ch_drag_active and self._selected_ch_key:
                mouse_point = vb.mapSceneToView(scene_pos)
                y = mouse_point.y()
                self._drag_offset_channel(y)
                return True

            snap_marker = self._find_nearest_marker_at_scene(scene_pos)
            widget = self.plot_widget.viewport() if hasattr(self.plot_widget, 'viewport') else self.plot_widget
            if snap_marker:
                widget.setCursor(Qt.SizeHorCursor)
            else:
                widget.unsetCursor()

        if event.type() == QEvent.GraphicsSceneMouseRelease:
            if event.button() == Qt.LeftButton:
                if self._marker_drag_target:
                    self._marker_drag_target = None
                    return True
                if self._ch_drag_active:
                    self._ch_drag_active = False
                    self._ch_drag_last_y = None
                    return True

        return super().eventFilter(obj, event)

    def _find_band_at_y(self, y):
        for key, band in self._band_info.items():
            if band["band_bottom"] <= y <= band["band_top"]:
                return key
        return None

    def _select_channel(self, key):
        if self._selected_ch_key == key:
            return
        self._deselect_channel()
        self._selected_ch_key = key
        band = self._band_info.get(key)
        if not band:
            return
        color = _color_for_label(key)
        region = pg.LinearRegionItem(
            values=[band["band_bottom"], band["band_top"]],
            orientation='horizontal',
            movable=False,
            brush=pg.mkBrush(color + "18"),
            pen=pg.mkPen(color, width=1, style=Qt.DashLine),
        )
        region.setZValue(-10)
        self.plot_widget.addItem(region, ignoreBounds=True)
        self._selected_highlight = region

    def _deselect_channel(self):
        self._selected_ch_key = None
        self._ch_drag_active = False
        self._ch_drag_last_y = None
        if self._selected_highlight:
            try:
                self.plot_widget.removeItem(self._selected_highlight)
            except Exception:
                pass
            self._selected_highlight = None

    def _wheel_scale_channel(self, event):
        key = self._selected_ch_key
        band = self._band_info.get(key)
        if not band:
            return

        delta = event.delta()
        factor = 0.9 if delta > 0 else 1.1

        raw_min = band["raw_min"]
        raw_range = band["raw_range"]
        raw_center = raw_min + raw_range / 2.0

        new_range = raw_range * factor
        new_min = raw_center - new_range / 2.0
        new_max = raw_center + new_range / 2.0

        band["raw_min"] = new_min
        band["raw_max"] = new_max
        band["raw_range"] = new_range

        self._redraw_single_channel(key)
        self._update_ch_scale_offset_display(key)

    def _drag_offset_channel(self, y):
        key = self._selected_ch_key
        band = self._band_info.get(key)
        if not band or self._ch_drag_last_y is None:
            self._ch_drag_last_y = y
            return

        dy = y - self._ch_drag_last_y
        self._ch_drag_last_y = y

        plot_range = band["plot_range"]
        if plot_range == 0:
            return

        raw_range = band["raw_range"]
        raw_shift = -dy / plot_range * raw_range

        band["raw_min"] += raw_shift
        band["raw_max"] += raw_shift

        self._redraw_single_channel(key)
        self._update_ch_scale_offset_display(key)

    def _redraw_single_channel(self, key):
        band = self._band_info.get(key)
        curve = self.plot_curves.get(key)
        ch_data = self.datalog_data.get(key)
        if not band or not curve or not ch_data:
            return

        raw_vals = ch_data["values"]
        times = ch_data["time"]
        raw_min = band["raw_min"]
        raw_range = band["raw_range"]
        plot_bottom = band["plot_bottom"]
        plot_range = band["plot_range"]

        if raw_range == 0:
            raw_range = 1.0

        norm_vals = [
            plot_bottom + (v - raw_min) / raw_range * plot_range
            for v in raw_vals
        ]
        curve.setData(times, norm_vals)

    def _update_ch_scale_offset_display(self, key):
        band = self._band_info.get(key)
        if not band:
            return
        raw_min = band["raw_min"]
        raw_range = band["raw_range"]
        raw_center = raw_min + raw_range / 2.0
        raw_div = raw_range / 5.0

        ch_unit = _unit_for_label(key)
        scale_str = _auto_format(raw_div, ch_unit)
        offset_str = _auto_format(raw_center, ch_unit)
        self._set_ch_scale_offset_text(key.strip(), scale_str, offset_str)

    def _on_mouse_moved(self, evt):
        pos = evt[0]
        vb = self.plot_widget.getPlotItem().getViewBox()
        if not self.plot_widget.sceneBoundingRect().contains(pos):
            self.crosshair_v.setVisible(False)
            self.tooltip_text.setVisible(False)
            for dot in self.crosshair_dots:
                try:
                    self.plot_widget.removeItem(dot)
                except Exception:
                    pass
            self.crosshair_dots.clear()
            return

        mouse_point = vb.mapSceneToView(pos)
        x = mouse_point.x()

        self.crosshair_v.setPos(x)
        self.crosshair_v.setVisible(True)

        for dot in self.crosshair_dots:
            try:
                self.plot_widget.removeItem(dot)
            except Exception:
                pass
        self.crosshair_dots.clear()

        if not self.datalog_data:
            self.tooltip_text.setVisible(False)
            return

        visible_keys = self._get_visible_keys()
        if not visible_keys:
            visible_keys = set(self.datalog_data.keys())

        lines = [f"Time: {x:.2f} s"]

        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        for idx, label in enumerate(sorted_keys):
            if label not in visible_keys:
                continue
            ch_data = self.datalog_data[label]
            times = ch_data["time"]
            values = ch_data["values"]
            if not times:
                continue

            i = self._find_nearest_index(times, x)
            if i is not None:
                val = values[i]
                color = _color_for_label(label)
                ch_unit = _unit_for_label(label)
                lines.append(f"<span style='color:{color}'>{_display_label(label)} : {_auto_format(val, ch_unit)}</span>")

                band = self._band_info.get(label)
                if band:
                    norm_y = band["plot_bottom"] + (val - band["raw_min"]) / band["raw_range"] * band["plot_range"]
                else:
                    norm_y = val

                dot = pg.ScatterPlotItem(
                    [times[i]], [norm_y], size=10,
                    pen=pg.mkPen(color=color, width=2),
                    brush=pg.mkBrush(color="#071127"),
                    symbol='o'
                )
                self.plot_widget.addItem(dot)
                self.crosshair_dots.append(dot)

        html = "<br>".join(lines)
        self.tooltip_text.setHtml(
            f"<div style='padding:4px; font-size:11px;'>{html}</div>"
        )
        self.tooltip_text.setPos(mouse_point)
        self.tooltip_text.setVisible(True)

    def _find_nearest_index(self, times, x):
        if not times:
            return None
        if x <= times[0]:
            return 0
        if x >= times[-1]:
            return len(times) - 1
        lo, hi = 0, len(times) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if times[mid] <= x:
                lo = mid
            else:
                hi = mid
        if abs(times[lo] - x) <= abs(times[hi] - x):
            return lo
        return hi

    def _init_ui_elements(self):
        self._update_recording_button_state(False)

    def _bind_signals(self):
        self.start_btn.clicked.connect(self._on_start_or_stop_recording)
        self.export_btn.clicked.connect(self._on_export)
        self.import_btn.clicked.connect(self._on_import)

        self.box_zoom_btn.clicked.connect(self._toggle_box_zoom)
        self.reset_view_btn.clicked.connect(self._reset_view)
        self.marker_a_btn.clicked.connect(lambda: self._set_marker_mode("A"))
        self.marker_b_btn.clicked.connect(lambda: self._set_marker_mode("B"))
        self.clear_markers_btn.clicked.connect(self._clear_markers)

        self.add_label_btn.clicked.connect(self._add_custom_label)

    def _is_8ch_mode(self):
        return self.is_connected_b

    def _update_connect_btn(self, btn, connected):
        update_connect_button_state(btn, connected)

    def _update_recording_button_state(self, recording):
        self.is_recording = recording
        self.start_btn.setProperty("running", "true" if recording else "false")
        self.start_btn.setText(
            "\u25A0  Stop Recording" if recording else "\u25B7  Start Recording"
        )
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        self.start_btn.update()

    def _show_progress_overlay(self, total_seconds):
        import time as _time
        self._progress_bar.setValue(0)
        self._progress_stage_label.setText("Preparing...")
        self._progress_time_label.setText(f"Estimated total: {total_seconds:.0f}s")
        self._progress_total_s = total_seconds
        self._progress_start_time = _time.time()
        self._progress_overlay.setGeometry(self.chart_frame.rect())
        self._progress_overlay.raise_()
        self._progress_overlay.show()

        self.plot_widget.setEnabled(False)
        self.channel_config_toggle_btn.setEnabled(False)
        self.channel_config_card.setEnabled(False)
        self._channel_config_overlay.setGeometry(self.channel_config_card.rect())
        self._channel_config_overlay.raise_()
        self._channel_config_overlay.show()

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(500)
        self._progress_timer.timeout.connect(self._update_progress_elapsed)
        self._progress_timer.start()

    def _update_progress_elapsed(self):
        import time as _time
        elapsed = _time.time() - self._progress_start_time
        remaining = max(0, self._progress_total_s - elapsed)
        if remaining > 0:
            self._progress_time_label.setText(
                f"Elapsed: {elapsed:.0f}s / ~{self._progress_total_s:.0f}s  |  Remaining: ~{remaining:.0f}s"
            )
        else:
            self._progress_time_label.setText(
                f"Elapsed: {elapsed:.0f}s / ~{self._progress_total_s:.0f}s  |  Finishing..."
            )

    def _hide_progress_overlay(self):
        if hasattr(self, '_progress_timer') and self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer = None
        self._progress_overlay.hide()
        self._channel_config_overlay.hide()
        self.plot_widget.setEnabled(True)
        self.channel_config_toggle_btn.setEnabled(True)
        self.channel_config_card.setEnabled(True)

    def _on_worker_progress(self, pct, stage):
        self._progress_bar.setValue(pct)
        self._progress_stage_label.setText(stage)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_progress_overlay') and self._progress_overlay.isVisible():
            self._progress_overlay.setGeometry(self.chart_frame.rect())
        if hasattr(self, '_channel_config_overlay') and self._channel_config_overlay.isVisible():
            self._channel_config_overlay.setGeometry(self.channel_config_card.rect())

    def event(self, ev):
        if ev.type() == ev.Type.LayoutRequest:
            if hasattr(self, '_progress_overlay') and self._progress_overlay.isVisible():
                QTimer.singleShot(0, lambda: self._progress_overlay.setGeometry(self.chart_frame.rect()))
            if hasattr(self, '_channel_config_overlay') and self._channel_config_overlay.isVisible():
                QTimer.singleShot(0, lambda: self._channel_config_overlay.setGeometry(self.channel_config_card.rect()))
        return super().event(ev)

    def _on_record_type_changed(self):
        if self.type_current.isChecked():
            self.plot_widget.setLabel("left", "", color="#8eb0e3")
        else:
            self.plot_widget.setLabel("left", "", color="#8eb0e3")
        self._clear_analysis_card_cache()
        self._update_marker_analysis()

    def _get_visible_keys(self):
        imported_keys = set()
        for tc in self._imported_tab_configs:
            imported_keys |= tc.get("data_keys", set())
        active_data = {k: v for k, v in self.datalog_data.items() if k not in imported_keys}

        visible_keys = set()
        self._collect_visible_keys_from_cbs(
            visible_keys,
            self.ch_current_cbs_a, self.ch_voltage_cbs_a,
            getattr(self, 'ch_power_cbs_a', []),
            getattr(self, 'ch_current_cbs_b', []),
            getattr(self, 'ch_voltage_cbs_b', []),
            getattr(self, 'ch_power_cbs_b', []),
            active_data,
        )
        for tc in self._imported_tab_configs:
            tc_keys = tc.get("data_keys", set())
            sub_data = {k: v for k, v in self.datalog_data.items() if k in tc_keys}
            self._collect_visible_keys_from_cbs(
                visible_keys,
                tc.get("current_cbs_a", []), tc.get("voltage_cbs_a", []),
                tc.get("power_cbs_a", []),
                tc.get("current_cbs_b", []), tc.get("voltage_cbs_b", []),
                tc.get("power_cbs_b", []),
                sub_data,
            )
        return visible_keys

    def _collect_visible_keys_from_cbs(self, visible_keys,
                                        current_a, voltage_a, power_a,
                                        current_b, voltage_b, power_b,
                                        data_dict):
        for i, cb in enumerate(current_a):
            if cb.isChecked():
                ch = i + 1
                for key in data_dict:
                    k = key.strip()
                    if k.endswith(f"CH{ch} I") or k == f"CH{ch} I":
                        visible_keys.add(key)
        for i, cb in enumerate(voltage_a):
            if cb.isChecked():
                ch = i + 1
                for key in data_dict:
                    k = key.strip()
                    if k.endswith(f"CH{ch} V") or k == f"CH{ch} V":
                        visible_keys.add(key)
        for i, cb in enumerate(current_b):
            if cb.isChecked():
                ch = i + 1
                for key in data_dict:
                    k = key.strip()
                    if k.endswith(f"CH{ch} I") and "B" in k:
                        visible_keys.add(key)
        for i, cb in enumerate(voltage_b):
            if cb.isChecked():
                ch = i + 1
                for key in data_dict:
                    k = key.strip()
                    if k.endswith(f"CH{ch} V") and "B" in k:
                        visible_keys.add(key)
        for i, cb in enumerate(power_a):
            if cb.isChecked():
                ch = i + 1
                for key in data_dict:
                    k = key.strip()
                    if (k.endswith(f"CH{ch} P") or k == f"CH{ch} P") and "B" not in k:
                        visible_keys.add(key)
        for i, cb in enumerate(power_b):
            if cb.isChecked():
                ch = i + 1
                for key in data_dict:
                    k = key.strip()
                    if k.endswith(f"CH{ch} P") and "B" in k:
                        visible_keys.add(key)

    def _on_channel_visibility_changed(self):
        if not self.datalog_data:
            return

        self._deselect_channel()

        visible_keys = self._get_visible_keys()
        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        visible_sorted = [k for k in sorted_keys if k in visible_keys]
        n = len(visible_sorted)

        for key, curve in self.plot_curves.items():
            curve.setVisible(key in visible_keys)

        for sl in self._sep_lines:
            self.plot_widget.removeItem(sl)
        self._sep_lines.clear()

        self._band_info = {}

        if n == 0:
            for item in self._ch_label_items:
                item.setVisible(False)
            return

        for idx, key in enumerate(visible_sorted):
            ch_data = self.datalog_data[key]
            raw_vals = ch_data["values"]
            if not raw_vals:
                continue

            raw_min = min(raw_vals)
            raw_max = max(raw_vals)
            raw_range = raw_max - raw_min
            if raw_range == 0:
                raw_range = 1.0

            band_top = 1.0 - idx / n
            band_bottom = 1.0 - (idx + 1) / n
            margin = (band_top - band_bottom) * 0.08
            plot_top = band_top - margin
            plot_bottom = band_bottom + margin
            plot_range = plot_top - plot_bottom

            norm_vals = [
                plot_bottom + (v - raw_min) / raw_range * plot_range
                for v in raw_vals
            ]

            self._band_info[key] = {
                "raw_min": raw_min,
                "raw_max": raw_max,
                "raw_range": raw_range,
                "band_top": band_top,
                "band_bottom": band_bottom,
                "plot_top": plot_top,
                "plot_bottom": plot_bottom,
                "plot_range": plot_range,
            }

            curve = self.plot_curves.get(key)
            if curve:
                times = ch_data["time"]
                curve.setData(times, norm_vals)

            if idx > 0:
                sep_line = pg.InfiniteLine(
                    pos=band_top, angle=0, movable=False,
                    pen=pg.mkPen(color="#1e3460", width=1, style=Qt.DashLine)
                )
                self.plot_widget.addItem(sep_line, ignoreBounds=True)
                self._sep_lines.append(sep_line)

            raw_center = (raw_min + raw_max) / 2
            raw_div = raw_range / 5
            ch_unit = _unit_for_label(key)
            scale_str = _auto_format(raw_div, ch_unit)
            offset_str = _auto_format(raw_center, ch_unit)
            self._set_ch_scale_offset_text(key.strip(), scale_str, offset_str)

        panel_entries = [(k, _color_for_label(k)) for k in visible_sorted]
        self._rebuild_ch_name_panel(panel_entries)
        self.plot_widget.setYRange(-0.02, 1.02)

    def _sync_checkboxes_to_data(self):
        import re
        all_cbs = (
            list(self.ch_current_cbs_a) +
            list(self.ch_voltage_cbs_a) +
            list(getattr(self, 'ch_power_cbs_a', [])) +
            list(getattr(self, 'ch_current_cbs_b', [])) +
            list(getattr(self, 'ch_voltage_cbs_b', [])) +
            list(getattr(self, 'ch_power_cbs_b', []))
        )
        for tc in self._imported_tab_configs:
            for suffix in ["current_cbs_a", "voltage_cbs_a", "power_cbs_a",
                           "current_cbs_b", "voltage_cbs_b", "power_cbs_b"]:
                all_cbs += list(tc.get(suffix, []))

        for cb in all_cbs:
            cb.blockSignals(True)
            cb.setChecked(False)
            ch_color = cb.property("ch_color") if hasattr(cb, 'property') else None
            if ch_color:
                cb.setStyleSheet(self._ch_toggle_style(ch_color, False))
            cb.blockSignals(False)

        imported_keys = set()
        for tc in self._imported_tab_configs:
            imported_keys |= tc.get("data_keys", set())
        active_data = {k: v for k, v in self.datalog_data.items() if k not in imported_keys}

        self._sync_cbs_for_data(
            active_data,
            self.ch_current_cbs_a, self.ch_voltage_cbs_a,
            getattr(self, 'ch_power_cbs_a', []),
            getattr(self, 'ch_current_cbs_b', []),
            getattr(self, 'ch_voltage_cbs_b', []),
            getattr(self, 'ch_power_cbs_b', []),
        )

        for tc in self._imported_tab_configs:
            tc_keys = tc.get("data_keys", set())
            sub_data = {k: v for k, v in self.datalog_data.items() if k in tc_keys}
            self._sync_cbs_for_data(
                sub_data,
                tc.get("current_cbs_a", []), tc.get("voltage_cbs_a", []),
                tc.get("power_cbs_a", []),
                tc.get("current_cbs_b", []), tc.get("voltage_cbs_b", []),
                tc.get("power_cbs_b", []),
            )

    def _sync_cbs_for_data(self, data_dict, current_a, voltage_a, power_a,
                           current_b, voltage_b, power_b):
        import re
        for key, ch_data in data_dict.items():
            k = key.strip()
            m = re.search(r'CH(\d+)\s+(I|V|P)', k)
            if not m:
                continue
            ch_num = int(m.group(1))
            mtype = m.group(2)
            is_b = "B " in key or "B_" in key

            if ch_num < 1 or ch_num > 4:
                continue

            idx = ch_num - 1
            if is_b:
                if mtype == "I":
                    cbs = current_b
                elif mtype == "V":
                    cbs = voltage_b
                else:
                    cbs = power_b
            else:
                if mtype == "I":
                    cbs = current_a
                elif mtype == "V":
                    cbs = voltage_a
                else:
                    cbs = power_a

            if idx < len(cbs):
                btn = cbs[idx]
                btn.blockSignals(True)
                btn.setChecked(True)
                ch_color = btn.property("ch_color")
                if ch_color:
                    btn.setStyleSheet(self._ch_toggle_style(ch_color, True))
                btn.blockSignals(False)

                values = ch_data.get("values", [])
                if values:
                    v_min = min(values)
                    v_max = max(values)
                    v_range = v_max - v_min
                    if v_range < 1e-9:
                        v_range = abs(v_max) * 0.1 if abs(v_max) > 1e-9 else 1.0
                    scale_val = v_range
                    offset_val = (v_max + v_min) / 2.0

                    unit = "mA" if mtype == "I" else ("mW" if mtype == "P" else "mV")
                    scale_str = _auto_format(scale_val, unit)
                    offset_str = _auto_format(offset_val, unit)

                    scale_edit = btn.property("scale_edit")
                    offset_edit = btn.property("offset_edit")
                    if scale_edit:
                        scale_edit.setText(scale_str)
                    if offset_edit:
                        offset_edit.setText(offset_str)

    def _get_active_dlog_channel_count(self):
        count_a = 0
        for cb in self.ch_current_cbs_a:
            if cb.isChecked():
                count_a += 1
        for cb in self.ch_voltage_cbs_a:
            if cb.isChecked():
                count_a += 1

        count_b = 0
        for cb in getattr(self, 'ch_current_cbs_b', []):
            if cb.isChecked():
                count_b += 1
        for cb in getattr(self, 'ch_voltage_cbs_b', []):
            if cb.isChecked():
                count_b += 1

        return max(count_a, count_b, 1)

    def _get_min_period_per_unit(self):
        count_a = 0
        for cb in self.ch_current_cbs_a:
            if cb.isChecked():
                count_a += 1
        for cb in self.ch_voltage_cbs_a:
            if cb.isChecked():
                count_a += 1

        count_b = 0
        for cb in getattr(self, 'ch_current_cbs_b', []):
            if cb.isChecked():
                count_b += 1
        for cb in getattr(self, 'ch_voltage_cbs_b', []):
            if cb.isChecked():
                count_b += 1

        min_a = max(count_a, 1) * 20
        min_b = max(count_b, 1) * 20 if count_b > 0 else 0
        return min_a, min_b

    def _on_min_period_toggled(self, state):
        is_min = self.min_period_cb.isChecked()
        self.sample_period_edit.setReadOnly(is_min)
        self.sample_period_edit.setStyleSheet(
            "QLineEdit { background: #1a2b52; color: #556a8c; }" if is_min
            else ""
        )
        if is_min:
            self._apply_minimum_period()

    def _apply_minimum_period(self):
        min_a, min_b = self._get_min_period_per_unit()
        min_period = max(min_a, min_b, 20)
        self.sample_period_edit.setText(str(int(min_period)))

    def _validate_sample_period(self):
        if self.min_period_cb.isChecked():
            self._apply_minimum_period()
            return

        try:
            val = float(self.sample_period_edit.text())
        except ValueError:
            val = 20.0

        num_ch = self._get_active_dlog_channel_count()
        min_period = num_ch * 20.0

        val = round(val / 20.0) * 20.0
        if val < min_period:
            val = min_period
        val = max(val, 20.0)

        self.sample_period_edit.setText(str(int(val)))

    def _on_start_or_stop_recording(self):
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        if self._record_thread and self._record_thread.isRunning():
            self._stop_recording()

        self._validate_sample_period()

        n6705c_list = []
        channels_per_unit = []
        voltage_channels_per_unit = []
        unit_labels = []

        if self.is_connected_a and self.n6705c_a:
            active_a = [i + 1 for i, cb in enumerate(self.ch_current_cbs_a) if cb.isChecked()]
            voltage_a = [i + 1 for i, cb in enumerate(self.ch_voltage_cbs_a) if cb.isChecked()]
            power_a = [i + 1 for i, cb in enumerate(getattr(self, 'ch_power_cbs_a', [])) if cb.isChecked()]
            for ch in power_a:
                if ch not in voltage_a:
                    voltage_a.append(ch)
                if ch not in active_a:
                    active_a.append(ch)
            voltage_a.sort()
            active_a.sort()
            if active_a or voltage_a:
                n6705c_list.append(self.n6705c_a)
                channels_per_unit.append(active_a)
                voltage_channels_per_unit.append(voltage_a)
                unit_labels.append("A")

        if self.is_connected_b and self.n6705c_b:
            active_b = [i + 1 for i, cb in enumerate(self.ch_current_cbs_b) if cb.isChecked()]
            voltage_b = [i + 1 for i, cb in enumerate(self.ch_voltage_cbs_b) if cb.isChecked()]
            power_b = [i + 1 for i, cb in enumerate(getattr(self, 'ch_power_cbs_b', [])) if cb.isChecked()]
            for ch in power_b:
                if ch not in voltage_b:
                    voltage_b.append(ch)
                if ch not in active_b:
                    active_b.append(ch)
            voltage_b.sort()
            active_b.sort()
            if active_b or voltage_b:
                n6705c_list.append(self.n6705c_b)
                channels_per_unit.append(active_b)
                voltage_channels_per_unit.append(voltage_b)
                unit_labels.append("B")

        total_active = sum(len(c) for c in channels_per_unit) + sum(len(c) for c in voltage_channels_per_unit)
        if total_active == 0:
            return

        if len(n6705c_list) == 1:
            unit_labels = [""]

        record_type = "current" if self.type_current.isChecked() else "voltage"

        try:
            sample_period = float(self.sample_period_edit.text())
        except ValueError:
            sample_period = 1000.0

        try:
            monitor_time = float(self.monitor_time_edit.text())
        except ValueError:
            monitor_time = 5.0

        timeout_ms = int((monitor_time + 120) * 1000)
        for n6705c in n6705c_list:
            n6705c.instr.timeout = max(timeout_ms, 300000)

        self._update_recording_button_state(True)

        estimated_export_time = monitor_time * 0.06 + 0.3
        total_estimated = monitor_time + 5 + estimated_export_time
        logger.debug("[Datalog][Progress] Estimated total time: %.1fs (monitoring=%.1fs + wait=5s + export=%.1fs)",
                    total_estimated, monitor_time, estimated_export_time)
        self._show_progress_overlay(total_estimated)

        self._record_thread = QThread()
        self._record_worker = _DatalogWorker(
            n6705c_list, channels_per_unit, unit_labels,
            record_type, sample_period, monitor_time,
            debug=DEBUG_MOCK,
            voltage_channels_per_unit=voltage_channels_per_unit
        )
        self._record_worker.moveToThread(self._record_thread)

        self._record_thread.started.connect(self._record_worker.run)
        self._record_worker.data_ready.connect(self._on_data_ready)
        self._record_worker.dlog_raw_ready.connect(self._on_dlog_raw_ready)
        self._record_worker.progress_update.connect(self._on_worker_progress)
        self._record_worker.finished.connect(self._record_thread.quit)
        self._record_worker.error.connect(self._on_recording_error)
        self._record_thread.finished.connect(self._on_recording_finished)
        self._record_thread.finished.connect(self._record_worker.deleteLater)
        self._record_thread.finished.connect(self._record_thread.deleteLater)

        self._record_thread.start()

    def _stop_recording(self):
        if self._record_worker:
            self._record_worker.stop()
        if self._record_thread and self._record_thread.isRunning():
            self._record_thread.quit()
            self._record_thread.wait(5000)
        self._record_worker = None
        self._record_thread = None
        self._update_recording_button_state(False)
        self._hide_progress_overlay()

    def _on_data_ready(self, data):
        power_chs_a = [cb.isChecked() for cb in getattr(self, 'ch_power_cbs_a', [])]
        power_chs_b = [cb.isChecked() for cb in getattr(self, 'ch_power_cbs_b', [])]
        compute_power_channels(data, power_chs_a, power_chs_b)
        self.datalog_data.update(data)
        self._clear_analysis_card_cache()
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _on_dlog_raw_ready(self, dlog_list):
        self._raw_dlog_list = dlog_list

    def _on_recording_finished(self):
        self._update_recording_button_state(False)
        self._hide_progress_overlay()
        self._record_worker = None
        self._record_thread = None

    def _on_recording_error(self, msg):
        logger.error("[Datalog] Recording error: %s", msg)
        self._update_recording_button_state(False)
        self._hide_progress_overlay()

    def _refresh_plot(self):
        self.plot_widget.clear()
        self.plot_curves.clear()
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_region = None
        self._band_info = {}
        self._sep_lines = []
        self._selected_ch_key = None
        self._selected_highlight = None
        self._ch_drag_active = False
        self._ch_drag_last_y = None
        self._marker_drag_target = None

        self.crosshair_v = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color="#4a6a9e", width=1, style=Qt.DashLine)
        )
        self.crosshair_v.setVisible(False)
        self.plot_widget.addItem(self.crosshair_v, ignoreBounds=True)

        self.tooltip_text = pg.TextItem(
            text="", color="#dbe7ff",
            anchor=(1, 1),
            fill=pg.mkBrush(10, 20, 45, 220),
            border=pg.mkPen(color="#2a4272")
        )
        self.tooltip_text.setVisible(False)
        self.tooltip_text.setZValue(100)
        self.plot_widget.addItem(self.tooltip_text, ignoreBounds=True)

        self.legend = None

        n = len(self.datalog_data)
        if n == 0:
            self._rebuild_ch_name_panel([])
            return

        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)

        left_axis = self.plot_widget.getPlotItem().getAxis("left")
        left_axis.setTicks([])
        left_axis.setLabel("")
        left_axis.setWidth(0)

        panel_entries = []

        for idx, label in enumerate(sorted_keys):
            ch_data = self.datalog_data[label]
            color = _color_for_label(label)
            times = ch_data["time"]
            raw_vals = ch_data["values"]

            if not raw_vals:
                continue

            raw_min = min(raw_vals)
            raw_max = max(raw_vals)
            raw_range = raw_max - raw_min if raw_max > raw_min else 1.0

            band_top = 1.0 - idx / n
            band_bottom = 1.0 - (idx + 1) / n
            margin = (band_top - band_bottom) * 0.08
            plot_top = band_top - margin
            plot_bottom = band_bottom + margin
            plot_range = plot_top - plot_bottom

            norm_vals = [
                plot_bottom + (v - raw_min) / raw_range * plot_range
                for v in raw_vals
            ]

            self._band_info[label] = {
                "raw_min": raw_min,
                "raw_max": raw_max,
                "raw_range": raw_range,
                "band_top": band_top,
                "band_bottom": band_bottom,
                "plot_top": plot_top,
                "plot_bottom": plot_bottom,
                "plot_range": plot_range,
            }

            pen = pg.mkPen(color=color, width=1.5)
            curve = self.plot_widget.plot(
                times, norm_vals,
                pen=pen
            )
            curve.setClipToView(True)
            curve.setDownsampling(auto=True, method='peak')
            self.plot_curves[label] = curve

            if idx > 0:
                sep_line = pg.InfiniteLine(
                    pos=band_top, angle=0, movable=False,
                    pen=pg.mkPen(color="#1e3460", width=1, style=Qt.DashLine)
                )
                self.plot_widget.addItem(sep_line, ignoreBounds=True)
                self._sep_lines.append(sep_line)

            panel_entries.append((label, color))

            raw_center = (raw_min + raw_max) / 2
            raw_div = raw_range / 5
            ch_unit = _unit_for_label(label)
            scale_str = _auto_format(raw_div, ch_unit)
            offset_str = _auto_format(raw_center, ch_unit)
            self._set_ch_scale_offset_text(label.strip(), scale_str, offset_str)

        if self.datalog_data:
            all_times = []
            for ch_data in self.datalog_data.values():
                all_times.extend(ch_data["time"])
            if all_times:
                self.plot_widget.setXRange(min(all_times), max(all_times))
            self.plot_widget.setYRange(-0.02, 1.02)

        self._rebuild_ch_name_panel(panel_entries)

        self._restore_markers()
        self._restore_label_lines()
        self._update_marker_analysis()
        self._refresh_label_ch_combo()

    def _reset_view(self):
        if not self.datalog_data:
            self.plot_widget.setXRange(0, 10)
            self.plot_widget.setYRange(-0.02, 1.02)
            return

        if self.box_zoom_enabled:
            self.box_zoom_enabled = False
            self._box_zoom_auto_off_timer.stop()
            self.box_zoom_btn.setText("\u2316 Box Zoom: OFF")

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.setMouseMode(vb.PanMode)
        self.plot_widget.setMouseEnabled(x=True, y=False)

        visible_keys = self._get_visible_keys()
        if not visible_keys:
            visible_keys = set(self.datalog_data.keys())

        all_times = []
        for key in visible_keys:
            ch_data = self.datalog_data.get(key)
            if ch_data and ch_data["time"]:
                all_times.extend(ch_data["time"])

        if all_times:
            self.plot_widget.setXRange(min(all_times), max(all_times))

        self._on_channel_visibility_changed()

    def _toggle_box_zoom(self):
        self.box_zoom_enabled = not self.box_zoom_enabled
        if self.box_zoom_enabled:
            self.box_zoom_btn.setText("\u2316 Box Zoom: ON")
            self.plot_widget.setMouseEnabled(x=True, y=True)
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.RectMode)
            self._box_zoom_auto_off_timer.start()
        else:
            self._box_zoom_auto_off_timer.stop()
            self.box_zoom_btn.setText("\u2316 Box Zoom: OFF")
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.PanMode)
            self.plot_widget.setMouseEnabled(x=True, y=False)
            self.plot_widget.setYRange(-0.02, 1.02)

    def _auto_off_box_zoom(self):
        if self.box_zoom_enabled:
            self.box_zoom_enabled = False
            self.box_zoom_btn.setText("\u2316 Box Zoom: OFF")
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.PanMode)
            self.plot_widget.setMouseEnabled(x=True, y=False)
            self.plot_widget.setYRange(-0.02, 1.02)

    def _set_marker_mode(self, marker):
        self._pending_marker = marker

    def _on_chart_clicked(self, event):
        if self._pending_marker is None:
            return

        pos = event.scenePos()
        vb = self.plot_widget.getPlotItem().getViewBox()
        mouse_point = vb.mapSceneToView(pos)
        x_val = mouse_point.x()

        if self._pending_marker == "A":
            self._place_marker_a(x_val)
        elif self._pending_marker == "B":
            self._place_marker_b(x_val)

        self._pending_marker = None
        self._update_marker_region()
        self._update_marker_analysis()

    def _place_marker_a(self, x):
        if self.marker_a_line:
            self.plot_widget.removeItem(self.marker_a_line)
        self.marker_a_pos = x
        self.marker_a_line = pg.InfiniteLine(
            pos=x, angle=90, movable=True,
            pen=pg.mkPen(color="#d4a514", width=2, style=Qt.DashLine),
            label=f"A",
            labelOpts={"color": "#d4a514", "position": 0.98}
        )
        self.marker_a_line.sigPositionChanged.connect(
            lambda line: self._on_marker_moved("A", line.value())
        )
        self.plot_widget.addItem(self.marker_a_line)
        self.marker_a_btn.setText(f"Set Marker A ({x:.4f}s)")

    def _place_marker_b(self, x):
        if self.marker_b_line:
            self.plot_widget.removeItem(self.marker_b_line)
        self.marker_b_pos = x
        self.marker_b_line = pg.InfiniteLine(
            pos=x, angle=90, movable=True,
            pen=pg.mkPen(color="#4cc9f0", width=2, style=Qt.DashLine),
            label=f"B",
            labelOpts={"color": "#4cc9f0", "position": 0.98}
        )
        self.marker_b_line.sigPositionChanged.connect(
            lambda line: self._on_marker_moved("B", line.value())
        )
        self.plot_widget.addItem(self.marker_b_line)
        self.marker_b_btn.setText(f"Set Marker B ({x:.4f}s)")

    def _on_marker_moved(self, which, value):
        if which == "A":
            self.marker_a_pos = value
            self.marker_a_btn.setText(f"Set Marker A ({value:.4f}s)")
        else:
            self.marker_b_pos = value
            self.marker_b_btn.setText(f"Set Marker B ({value:.4f}s)")
        self._update_marker_region()
        self._update_marker_analysis()

    def _update_marker_region(self):
        if self.marker_region:
            self.plot_widget.removeItem(self.marker_region)
            self.marker_region = None

        if self.marker_a_pos is not None and self.marker_b_pos is not None:
            t1 = min(self.marker_a_pos, self.marker_b_pos)
            t2 = max(self.marker_a_pos, self.marker_b_pos)
            self.marker_region = pg.LinearRegionItem(
                values=[t1, t2], movable=False,
                brush=pg.mkBrush(40, 80, 180, 50),
                pen=pg.mkPen(None)
            )
            self.plot_widget.addItem(self.marker_region)
            self.marker_region.setZValue(-10)

    def _clear_markers(self):
        self._marker_drag_target = None
        if self.marker_a_line:
            self.plot_widget.removeItem(self.marker_a_line)
            self.marker_a_line = None
        if self.marker_b_line:
            self.plot_widget.removeItem(self.marker_b_line)
            self.marker_b_line = None
        if self.marker_region:
            self.plot_widget.removeItem(self.marker_region)
            self.marker_region = None
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_btn.setText("Set Marker A")
        self.marker_b_btn.setText("Set Marker B")
        self._clear_analysis_card_cache()
        self._update_marker_analysis()

    def _clear_analysis_card_cache(self):
        pass

    def _rebuild_ch_name_panel(self, entries):
        for item in self._ch_label_items:
            try:
                self.plot_widget.removeItem(item)
            except Exception:
                pass
        self._ch_label_items.clear()

        left_axis = self.plot_widget.getPlotItem().getAxis("left")

        if not entries:
            left_axis.setWidth(0)
            return

        left_axis.setWidth(65)

        for key, color in entries:
            display = self.ch_name_renames.get(key, _display_label(key))
            band = self._band_info.get(key)
            if band:
                y_center = (band["plot_top"] + band["plot_bottom"]) / 2
            else:
                y_center = 0.5

            text_item = pg.TextItem(
                html=f"<div style='background:#071127; padding:1px 6px 1px 2px; border-radius:2px;'>"
                     f"<span style='color:{color}; font-size:12px; font-weight:800;'>"
                     f"{display}</span></div>",
                anchor=(0, 0.5),
            )
            text_item.setZValue(200)
            self.plot_widget.addItem(text_item, ignoreBounds=True)
            text_item.setProperty("y_center", y_center)
            self._ch_label_items.append(text_item)

        vb = self.plot_widget.getPlotItem().getViewBox()
        try:
            vb.sigRangeChanged.disconnect(self._update_ch_label_positions)
        except Exception:
            pass
        vb.sigRangeChanged.connect(self._update_ch_label_positions)
        self._update_ch_label_positions()

    def _update_ch_label_positions(self, *args):
        vb = self.plot_widget.getPlotItem().getViewBox()
        x_min, _ = vb.viewRange()[0]
        for item in self._ch_label_items:
            try:
                y_center = item.property("y_center")
            except Exception:
                y_center = 0.5
            item.setPos(x_min, y_center)

    def _on_ch_name_renamed(self, key, new_name):
        self.ch_name_renames[key] = new_name

    def _restore_markers(self):
        if self.marker_a_pos is not None:
            self._place_marker_a(self.marker_a_pos)
        if self.marker_b_pos is not None:
            self._place_marker_b(self.marker_b_pos)
        self._update_marker_region()

    def _update_marker_analysis(self):
        has_both_markers = self.marker_a_pos is not None and self.marker_b_pos is not None
        has_data = bool(self.datalog_data)

        if not has_both_markers and not has_data:
            self.analysis_hint_label.setVisible(True)
            self.meas_table.setVisible(False)
            return

        self.analysis_hint_label.setVisible(False)
        self.meas_table.setVisible(True)

        is_current = self.type_current.isChecked()

        visible_keys = self._get_visible_keys()
        if not visible_keys:
            visible_keys = set(self.datalog_data.keys())
        ch_list = [(k, self.datalog_data[k]) for k in sorted(self.datalog_data.keys(), key=_sort_key_for_label) if k in visible_keys]

        if has_both_markers:
            self._update_marker_analysis_with_markers(ch_list, is_current)
        else:
            self._update_marker_analysis_full_wave(ch_list, is_current)

    def _update_marker_analysis_full_wave(self, ch_list, is_current):
        headers = ["", "Avg"]
        num_rows = len(ch_list)
        num_cols = len(headers)

        self.meas_table.blockSignals(True)
        self.meas_table.clearSpans()
        self.meas_table.setRowCount(num_rows)
        self.meas_table.setColumnCount(num_cols)
        self.meas_table.setHorizontalHeaderLabels(headers)

        hi = self.meas_table.horizontalHeaderItem(1)
        if hi:
            f = hi.font()
            f.setBold(True)
            hi.setFont(f)

        ROW_BG = ["#080f22", "#0a1530"]

        for ch_idx, (label, ch_data) in enumerate(ch_list):
            color_hex = _color_for_label(label)
            row_bg = ROW_BG[ch_idx % 2]

            ch_num, mtype, _ = _parse_ch_label(label)
            ch_is_current = (mtype == "I") if mtype else is_current
            ch_is_power = (mtype == "P") if mtype else False
            val_unit = "mW" if ch_is_power else ("mA" if ch_is_current else "mV")

            values = ch_data["values"]
            if values:
                seg_avg = sum(values) / len(values)
            else:
                seg_avg = 0.0

            self._set_meas_cell(ch_idx, 0, _display_label(label), color_hex, bg=row_bg)
            self._set_meas_cell(ch_idx, 1, _auto_format(seg_avg, val_unit), color_hex, bg=row_bg, bold=True)

        row_h = 24
        total_h = (num_rows + 1) * row_h + 4
        self.meas_table.setFixedHeight(min(total_h, 200))
        for r in range(num_rows):
            self.meas_table.setRowHeight(r, row_h)

        self.meas_table.blockSignals(False)

    def _update_marker_analysis_with_markers(self, ch_list, is_current):
        t_a = self.marker_a_pos
        t_b = self.marker_b_pos
        t1 = min(t_a, t_b)
        t2 = max(t_a, t_b)
        delta = t2 - t1
        freq = 1.0 / delta if delta > 0 else 0.0

        METRIC_DEFS = [
            ("min", self.meas_minimum_cb, "Min"),
            ("avg", self.meas_average_cb, "Avg"),
            ("max", self.meas_maximum_cb, "Max"),
            ("p2p", self.meas_peak2peak_cb, "P2P"),
            ("charge_ah", self.meas_charge_ah_cb, "Ah/Wh"),
            ("charge_c", self.meas_charge_c_cb, "C/J"),
        ]
        selected = [(k, hdr) for k, cb, hdr in METRIC_DEFS if cb.isChecked()]

        headers = [""]
        headers.append("Marker A")
        for _, hdr in selected:
            headers.append(hdr)
        headers.append("Marker B")

        from bisect import bisect_left, bisect_right

        num_rows = 1 + len(ch_list)
        num_cols = len(headers)

        self.meas_table.blockSignals(True)
        self.meas_table.clearSpans()
        self.meas_table.setRowCount(num_rows)
        self.meas_table.setColumnCount(num_cols)
        self.meas_table.setHorizontalHeaderLabels(headers)

        for ci, h in enumerate(headers):
            if h == "Avg":
                hi = self.meas_table.horizontalHeaderItem(ci)
                if hi:
                    f = hi.font()
                    f.setBold(True)
                    hi.setFont(f)

        if freq >= 1.0:
            freq_str = f"{freq:.3f} Hz"
        else:
            freq_str = f"{freq * 1000:.3f} mHz"

        info_text = f"\u0394 = {_format_time(delta)}    Freq = {freq_str}"

        self._set_meas_cell(0, 0, "Time", "#5a7fad", bg="#0b1528")
        self._set_meas_cell(0, 1, _format_time(t_a), "#8eb0e3", bg="#0b1528")

        mid_col = 2
        if selected:
            mid_span = len(selected)
            self.meas_table.setSpan(0, mid_col, 1, mid_span)
            self._set_meas_cell(0, mid_col, info_text, "#5a7fad", align=Qt.AlignCenter, bg="#0b1528")
        else:
            self._set_meas_cell(0, mid_col, info_text, "#5a7fad", align=Qt.AlignCenter, bg="#0b1528")

        self._set_meas_cell(0, num_cols - 1, _format_time(t_b), "#8eb0e3", bg="#0b1528")

        ROW_BG = ["#080f22", "#0a1530"]

        for ch_idx, (label, ch_data) in enumerate(ch_list):
            row = 1 + ch_idx
            color_hex = _color_for_label(label)
            row_bg = ROW_BG[ch_idx % 2]

            ch_num, mtype, _ = _parse_ch_label(label)
            ch_is_current = (mtype == "I") if mtype else is_current
            ch_is_power = (mtype == "P") if mtype else False
            val_unit = "mW" if ch_is_power else ("mA" if ch_is_current else "mV")

            times = ch_data["time"]
            values = ch_data["values"]

            idx_a = self._find_nearest_index(times, t_a)
            idx_b = self._find_nearest_index(times, t_b)
            val_a = values[idx_a] if idx_a is not None else 0.0
            val_b = values[idx_b] if idx_b is not None else 0.0

            i_start = bisect_left(times, t1)
            i_end = bisect_right(times, t2)
            segment = values[i_start:i_end]

            if segment:
                time_seg = times[i_start:i_end]
                dt = (time_seg[-1] - time_seg[0]) if len(time_seg) >= 2 else delta
                seg_min = min(segment)
                seg_max = max(segment)
                seg_avg = sum(segment) / len(segment)
            else:
                dt = delta
                seg_min = seg_max = seg_avg = 0.0

            self._set_meas_cell(row, 0, _display_label(label), color_hex, bg=row_bg)
            self._set_meas_cell(row, 1, _auto_format(val_a, val_unit), color_hex, bg=row_bg)

            col = 2
            for metric_key, _ in selected:
                if metric_key == "min":
                    val_str = _auto_format(seg_min, val_unit)
                elif metric_key == "avg":
                    val_str = _auto_format(seg_avg, val_unit)
                elif metric_key == "max":
                    val_str = _auto_format(seg_max, val_unit)
                elif metric_key == "p2p":
                    val_str = _auto_format(seg_max - seg_min, val_unit)
                elif metric_key == "charge_ah":
                    c = seg_avg * dt / 3600.0
                    val_str = _auto_format(c, "mWh" if ch_is_power else ("mAh" if ch_is_current else "mWh"))
                elif metric_key == "charge_c":
                    c = seg_avg * dt / 1000.0
                    val_str = _auto_format(c, "J" if ch_is_power else ("C" if ch_is_current else "J"))
                else:
                    val_str = ""
                self._set_meas_cell(row, col, val_str, color_hex, bg=row_bg, bold=(metric_key == "avg"))
                col += 1

            self._set_meas_cell(row, num_cols - 1, _auto_format(val_b, val_unit), color_hex, bg=row_bg)

        row_h = 24
        total_h = (num_rows + 1) * row_h + 4
        self.meas_table.setFixedHeight(min(total_h, 200))
        for r in range(num_rows):
            self.meas_table.setRowHeight(r, row_h)

        self.meas_table.blockSignals(False)

    def _set_meas_cell(self, row, col, text, color_hex, align=Qt.AlignCenter, bg=None, bold=False):
        item = self.meas_table.item(row, col)
        if item is None:
            item = QTableWidgetItem(text)
            item.setTextAlignment(align)
            item.setForeground(QColor(color_hex))
            if bg:
                item.setBackground(QColor(bg))
            if bold:
                f = item.font()
                f.setBold(True)
                item.setFont(f)
            self.meas_table.setItem(row, col, item)
        else:
            item.setText(text)
            item.setForeground(QColor(color_hex))
            if bg:
                item.setBackground(QColor(bg))
            f = item.font()
            f.setBold(bold)
            item.setFont(f)

    def _on_range_changed(self):
        self._update_ch_label_positions()
        self._update_scale_offset_from_view()
        if self.box_zoom_enabled and self._box_zoom_auto_off_timer.isActive():
            self._box_zoom_auto_off_timer.start()

    def _update_scale_offset_from_view(self):
        if not self.datalog_data or not self._band_info:
            return

        vb = self.plot_widget.getPlotItem().getViewBox()
        y_min, y_max = vb.viewRange()[1]
        y_span = y_max - y_min

        for key, band in self._band_info.items():
            plot_top = band["plot_top"]
            plot_bottom = band["plot_bottom"]
            plot_range = band["plot_range"]
            raw_min = band["raw_min"]
            raw_range = band["raw_range"]

            if plot_range == 0:
                continue

            visible_data_min = raw_min + (y_min - plot_bottom) / plot_range * raw_range
            visible_data_max = raw_min + (y_max - plot_bottom) / plot_range * raw_range
            visible_data_range = visible_data_max - visible_data_min
            visible_center = (visible_data_min + visible_data_max) / 2
            visible_div = visible_data_range / 10

            ch_unit = _unit_for_label(key)
            scale_str = _auto_format(visible_div, ch_unit)
            offset_str = _auto_format(visible_center, ch_unit)
            self._set_ch_scale_offset_text(key.strip(), scale_str, offset_str)

    def _refresh_label_ch_combo(self):
        current = self.label_ch_combo.currentText()
        self.label_ch_combo.clear()
        for label in sorted(self.datalog_data.keys(), key=_sort_key_for_label):
            self.label_ch_combo.addItem(_display_label(label), label)
        idx = self.label_ch_combo.findText(current)
        if idx >= 0:
            self.label_ch_combo.setCurrentIndex(idx)
        elif self.label_ch_combo.count() > 0:
            self.label_ch_combo.setCurrentIndex(0)

    def _add_custom_label(self):
        idx = self.label_ch_combo.currentIndex()
        if idx < 0:
            return
        ch_name = self.label_ch_combo.itemData(idx) or self.label_ch_combo.currentText().strip()
        time_str = self.label_time_edit.text().strip()
        text = self.label_text_edit.text().strip()
        if not time_str or not text or not ch_name:
            return
        try:
            t = float(time_str)
        except ValueError:
            return

        self.custom_labels.append({"time": t, "text": text, "channel": ch_name})
        self._refresh_labels_display()
        self._draw_label_item(t, text, ch_name)

        self.label_time_edit.clear()
        self.label_text_edit.clear()

    def _get_value_at_time(self, ch_name, t):
        for label, ch_data in self.datalog_data.items():
            if label.strip() == ch_name:
                times = ch_data["time"]
                values = ch_data["values"]
                if not times:
                    return None
                idx = self._find_nearest_index(times, t)
                if idx is not None:
                    raw_val = values[idx]
                    band = self._band_info.get(label)
                    if band:
                        return band["plot_bottom"] + (raw_val - band["raw_min"]) / band["raw_range"] * band["plot_range"]
                    return raw_val
        return None

    def _get_channel_color(self, ch_name):
        color = _color_for_label(ch_name)
        return (color, color)

    def _draw_label_item(self, t, text, ch_name):
        color, _ = self._get_channel_color(ch_name)
        y_val = self._get_value_at_time(ch_name, t)
        if y_val is None:
            y_val = 0.5

        band = None
        raw_val = None
        for label in self.datalog_data:
            if label.strip() == ch_name:
                band = self._band_info.get(label)
                ch_data = self.datalog_data[label]
                times = ch_data["time"]
                idx = self._find_nearest_index(times, t)
                if idx is not None:
                    raw_val = ch_data["values"][idx]
                break

        if band:
            label_y = band["plot_top"] - 0.01
        else:
            label_y = y_val + 0.05

        ch_unit = _unit_for_label(ch_name)
        val_str = _auto_format(raw_val, ch_unit) if raw_val is not None else "—"

        label_item = pg.TextItem(
            html=f"<div style='background:#0a1733ee; padding:2px 5px; "
                 f"border: 1px solid {color}; border-radius:3px; "
                 f"font-size:10px; font-weight:700; color:{color};'>"
                 f"{text}: {val_str}</div>",
            anchor=(0.5, 1),
        )
        label_item.setZValue(55)
        label_item.setPos(t, label_y)
        self.plot_widget.addItem(label_item)

        self.custom_label_lines.append({"text_item": label_item})

    def _restore_label_lines(self):
        for item in self.custom_label_lines:
            try:
                if isinstance(item, dict):
                    for key in ["vline", "dot", "text_item", "arrow"]:
                        if key in item:
                            self.plot_widget.removeItem(item[key])
                else:
                    self.plot_widget.removeItem(item)
            except Exception:
                pass
        self.custom_label_lines.clear()
        for lbl in self.custom_labels:
            self._draw_label_item(lbl["time"], lbl["text"], lbl.get("channel", ""))

    def _refresh_labels_display(self):
        while self.labels_list_layout_inner.count() > 0:
            item = self.labels_list_layout_inner.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.custom_labels:
            self.labels_list_label = QLabel("No labels added.")
            self.labels_list_label.setObjectName("hintLabel")
            self.labels_list_layout_inner.addWidget(self.labels_list_label)
            self.labels_list_layout_inner.addStretch()
            return

        for i, lbl in enumerate(self.custom_labels):
            ch = lbl.get("channel", "")
            color = _color_for_label(ch) if ch else "#8eb0e3"

            row_frame = QFrame()
            row_frame.setStyleSheet(
                f"QFrame {{ background-color: #0c1a35; border-left: 3px solid {color}; "
                f"border-radius: 3px; padding: 0px; }}"
            )
            row_layout = QHBoxLayout(row_frame)
            row_layout.setContentsMargins(6, 3, 4, 3)
            row_layout.setSpacing(6)

            info_layout = QVBoxLayout()
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(0)

            ch_lbl = QLabel(ch if ch else "—")
            ch_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700; border: none;")
            info_layout.addWidget(ch_lbl)

            detail_lbl = QLabel(f"{lbl['time']}s  ·  {lbl['text']}")
            detail_lbl.setStyleSheet("color: #556a8c; font-size: 10px; border: none;")
            info_layout.addWidget(detail_lbl)

            row_layout.addLayout(info_layout, 1)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(20, 20)
            del_btn.setStyleSheet(
                "QPushButton { background: transparent; color: #3a5070; font-size: 12px; "
                "border: none; border-radius: 2px; }"
                "QPushButton:hover { background: #1e3460; color: #ff6b6b; }"
            )
            del_btn.clicked.connect(lambda checked=False, idx=i: self._delete_custom_label(idx))
            row_layout.addWidget(del_btn)

            self.labels_list_layout_inner.addWidget(row_frame)

        self.labels_list_layout_inner.addStretch()

    def _delete_custom_label(self, idx):
        if 0 <= idx < len(self.custom_labels):
            self.custom_labels.pop(idx)
            self._refresh_labels_display()
            self._restore_label_lines()

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Datalog", "",
            "Datalog Files (*.csv *.dlog *.edlg);;CSV Files (*.csv);;Dlog Files (*.dlog);;EDLG Files (*.edlg);;All Files (*)"
        )
        if not path:
            return

        try:
            if path.lower().endswith(".edlg"):
                self._import_edlg(path)
            elif path.lower().endswith(".dlog"):
                self._import_dlog(path)
            else:
                self._import_csv(path)
        except Exception as e:
            import traceback
            logger.error(f"Import failed: {e}\n{traceback.format_exc()}")

    def _import_csv(self, path):
        all_data = import_csv_file(path)
        if not all_data:
            return

        self._import_counter += 1
        prefix = f"F{self._import_counter}-"
        prefixed = {f"{prefix}{k}": v for k, v in all_data.items()}
        new_keys = set(prefixed.keys())
        self.datalog_data.update(prefixed)
        tab_name = os.path.basename(path)
        self._build_imported_channel_config(tab_name=tab_name, data_keys=new_keys)
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _import_edlg(self, path):
        result = import_edlg_file(path)
        if result is None or result[0] is None:
            return

        all_data, raw_data = result
        self._raw_dlog_list.append(raw_data)
        self._import_counter += 1
        prefix = f"F{self._import_counter}-"
        prefixed = {f"{prefix}{k}": v for k, v in all_data.items()}
        new_keys = set(prefixed.keys())
        self.datalog_data.update(prefixed)
        tab_name = os.path.basename(path)
        self._build_imported_channel_config(tab_name=tab_name, data_keys=new_keys)
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _import_dlog(self, path):
        result = import_dlog_file(path)
        if result is None or result[0] is None:
            return

        all_data, raw_data = result
        self._raw_dlog_list.append(raw_data)
        self._import_counter += 1
        prefix = f"F{self._import_counter}-"
        prefixed = {f"{prefix}{k}": v for k, v in all_data.items()}
        new_keys = set(prefixed.keys())
        self.datalog_data.update(prefixed)
        tab_name = os.path.basename(path)
        self._build_imported_channel_config(tab_name=tab_name, data_keys=new_keys)
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _on_export(self):
        if not self.datalog_data:
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Datalog", "",
            "Dlog Files (*.dlog);;CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        try:
            if path.lower().endswith(".dlog"):
                if self._raw_dlog_list:
                    with open(path, 'wb') as f:
                        f.write(self._raw_dlog_list[0])
                    if len(self._raw_dlog_list) > 1:
                        import os
                        base, ext = os.path.splitext(path)
                        for idx in range(1, len(self._raw_dlog_list)):
                            with open(f"{base}_unit{idx}{ext}", 'wb') as f:
                                f.write(self._raw_dlog_list[idx])
            else:
                max_len = max(len(d["time"]) for d in self.datalog_data.values())
                labels = list(self.datalog_data.keys())

                with open(path, "w", newline="") as f:
                    header = "Time(s)," + ",".join(_display_label(l) for l in labels)
                    f.write(header + "\n")

                    for i in range(max_len):
                        row_parts = []
                        first = list(self.datalog_data.values())[0]
                        if i < len(first["time"]):
                            row_parts.append(f"{first['time'][i]:.6f}")
                        else:
                            row_parts.append("")

                        for lbl in labels:
                            ch = self.datalog_data[lbl]
                            if i < len(ch["values"]):
                                row_parts.append(f"{ch['values'][i]:.9f}")
                            else:
                                row_parts.append("")

                        f.write(",".join(row_parts) + "\n")
        except Exception:
            pass


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from PySide6.QtGui import QIcon

    def _msg_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return

    qInstallMessageHandler(_msg_handler)
    app = QApplication(sys.argv)

    # Set application icon for taskbar and window
    _icon_path = os.path.join(_get_base_path(), "resources", "icons", "n6705c.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget {
            background-color: #030b23;
            color: #eaf1ff;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: 14px;
        }
        QPushButton {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px 12px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QPushButton:hover { background-color: #3a3d43; }
        QPushButton:pressed { background-color: #2a2d32; }
        QPushButton:disabled { background-color: #2a2d32; color: #666; }
        QComboBox {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 20px 4px 8px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QComboBox QAbstractItemView {
            background-color: #32353a;
            color: #c8c8c8;
            border: 1px solid #555;
            selection-background-color: #4a4d52;
            outline: 0px;
        }
        QLineEdit {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 8px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QLabel { color: #c8c8c8; }
        QCheckBox { color: #c8c8c8; }
        QFrame {
            border: 1px solid #333;
            border-radius: 4px;
            background-color: #020618;
        }
    """)

    w = N6705CDatalogUI()
    w.setWindowTitle("N6705C Datalog - Debug")
    w.resize(1400, 900)
    if os.path.exists(_icon_path):
        w.setWindowIcon(QIcon(_icon_path))
    w.show()
    sys.exit(app.exec())