#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import math
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QGridLayout, QFrame, QCheckBox,
    QRadioButton, QButtonGroup, QSizePolicy, QFileDialog,
    QScrollArea, QGraphicsRectItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor, QBrush, QPen, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
import pyqtgraph as pg
import pyvisa
import os

from instruments.n6705c import N6705C

DEBUG_FLAG = False
DEBUG_N6705C_FLAG = True


class _MockInstr:
    def write(self, cmd):
        pass

    def query(self, cmd):
        return ""


class _MockN6705C:
    def __init__(self):
        self.instr = _MockInstr()

    def disconnect(self):
        pass

    def channel_on(self, channel):
        pass

    def channel_off(self, channel):
        pass

    def set_voltage(self, channel, voltage):
        pass

    def set_current(self, channel, current):
        pass

    def set_current_limit(self, channel, current_limit):
        pass

    def measure_voltage(self, channel):
        return 0.0

    def measure_current(self, channel):
        return 0.0


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
    m = re.search(r'CH(\d+)\s*(I|V|P)', label.strip())
    if m:
        ch_num = int(m.group(1))
        mtype = m.group(2)
        is_b = label.strip().startswith("B ")
        return ch_num, mtype, is_b
    return None, None, False


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
    ch_num, mtype, is_b = _parse_ch_label(label)
    unit_order = 1 if is_b else 0
    ch_order = ch_num if ch_num else 0
    type_order = {"V": 0, "I": 1, "P": 2}.get(mtype, 3)
    return (unit_order, ch_order, type_order)


def _parse_value_with_unit(text):
    import re
    text = text.strip()
    m = re.match(r'^([+-]?\d*\.?\d+)\s*(uA|uV|uW|mA|mV|mW|A|V|W)?$', text, re.IGNORECASE)
    if not m:
        try:
            return float(text)
        except ValueError:
            return None
    num = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit in ("ua", "uv", "uw"):
        return num * 1e-3
    elif unit in ("ma", "mv", "mw"):
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
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def blockSignals(self, b):
        super().blockSignals(b)


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
                        self.device_found.emit(serial, model, ip, res)
                except Exception:
                    pass
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
                n6705c = _MockN6705C()
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

    def _read_mmem_data(self, instr, filepath):
        import struct
        old_timeout = instr.timeout
        old_chunk = getattr(instr, 'chunk_size', 20480)
        instr.timeout = 300000
        instr.chunk_size = 1024 * 1024

        try:
            instr.write(f'MMEM:DATA? "{filepath}"')

            hash_char = instr.read_bytes(1)
            if hash_char != b'#':
                rest = instr.read_raw()
                return (hash_char + rest).decode('ascii', errors='replace')

            digit_count_byte = instr.read_bytes(1)
            digit_count = int(digit_count_byte.decode('ascii'))
            data_len_bytes = instr.read_bytes(digit_count)
            data_len = int(data_len_bytes.decode('ascii'))

            print(f"[Datalog] IEEE block: data_len={data_len} bytes")

            raw_data = b""
            remaining = data_len
            while remaining > 0:
                read_size = min(remaining, 1024 * 1024)
                chunk = instr.read_bytes(read_size)
                raw_data += chunk
                remaining -= len(chunk)

            try:
                instr.read_bytes(1)
            except Exception:
                pass

            return raw_data
        finally:
            instr.timeout = old_timeout
            instr.chunk_size = old_chunk

    def _parse_csv_text(self, csv_text, curr_channels, volt_channels, ulabel, sample_period_s):
        import re
        actual_interval = None
        match = re.search(r'Sample interval:\s*([\d.eE+\-]+)', csv_text)
        if match:
            actual_interval = float(match.group(1))

        if actual_interval is not None:
            sample_period_s = actual_interval
            print(f"[Datalog] Using sample interval from CSV: {sample_period_s}")

        lines = csv_text.splitlines()
        print(f"[Datalog] Total CSV lines: {len(lines)}")

        ordered_cols = []
        all_chs = sorted(set(curr_channels) | set(volt_channels))
        for ch in all_chs:
            if ch in volt_channels:
                ordered_cols.append(("volt", ch))
            if ch in curr_channels:
                ordered_cols.append(("curr", ch))

        col_data = {i: [] for i in range(len(ordered_cols))}

        for line in lines:
            if not line.strip() or "," not in line:
                continue
            parts = line.split(",")
            try:
                float(parts[0])
            except (ValueError, IndexError):
                continue
            for col_idx in range(len(ordered_cols)):
                try:
                    col_data[col_idx].append(float(parts[1 + col_idx]))
                except (ValueError, IndexError):
                    pass

        all_data = {}
        for col_idx, (meas_type, ch) in enumerate(ordered_cols):
            suffix = "I" if meas_type == "curr" else "V"
            label = f"{ulabel} CH{ch} {suffix}".strip()
            values = col_data[col_idx]
            print(f"[Datalog] {label}: {len(values)} points")
            if values:
                values = [v * 1000.0 for v in values]
                t = [i * sample_period_s for i in range(len(values))]
                all_data[label] = {"time": t, "values": values}

        return all_data

    def _parse_dlog_binary(self, raw_data, curr_channels, volt_channels, ulabel, sample_period_s):
        import struct, re
        all_data = {}
        try:
            xml_header = raw_data[:min(len(raw_data), 8192)].decode('ascii', errors='replace')

            tint_match = re.search(r'<tint>([\d.eE+\-]+)</tint>', xml_header)
            if tint_match:
                sample_period_s = float(tint_match.group(1))
                print(f"[Datalog] dlog tint (sample interval): {sample_period_s}")

            dlog_curr_chs = []
            dlog_volt_chs = []
            for m in re.finditer(r'<channel id="(\d+)">(.*?)</channel>', xml_header, re.DOTALL):
                ch_id = int(m.group(1))
                ch_xml = m.group(2)
                sc = re.search(r'<sense_curr>(\d+)</sense_curr>', ch_xml)
                sv = re.search(r'<sense_volt>(\d+)</sense_volt>', ch_xml)
                if sc and sc.group(1) == '1':
                    dlog_curr_chs.append(ch_id)
                if sv and sv.group(1) == '1':
                    dlog_volt_chs.append(ch_id)

            dlog_col_order = []
            all_ch_ids = sorted(set(dlog_curr_chs + dlog_volt_chs))
            for ch in all_ch_ids:
                if ch in dlog_volt_chs:
                    dlog_col_order.append(("volt", ch))
                if ch in dlog_curr_chs:
                    dlog_col_order.append(("curr", ch))

            num_traces = len(dlog_col_order)
            if num_traces == 0:
                print("[Datalog] No active traces found in dlog XML header")
                return None

            close_tag = b'</dlog>'
            tag_pos = raw_data.find(close_tag)
            if tag_pos < 0:
                print("[Datalog] Could not find </dlog> tag in dlog file")
                return None

            data_offset = tag_pos + len(close_tag) + 9

            if data_offset + num_traces * 4 > len(raw_data):
                print(f"[Datalog] dlog file too small for data at offset {data_offset}")
                return None

            print(f"[Datalog] dlog data_offset: {data_offset}, traces: {num_traces}")

            data_section = raw_data[data_offset:]
            float_count = len(data_section) // 4
            num_samples = float_count // num_traces

            print(f"[Datalog] dlog: {float_count} floats, {num_samples} samples, {num_traces} traces")

            values_all = struct.unpack_from(f'>{float_count}f', data_section, 0)

            requested = []
            all_req_chs = sorted(set(curr_channels) | set(volt_channels))
            for ch in all_req_chs:
                if ch in volt_channels:
                    requested.append(("volt", ch))
                if ch in curr_channels:
                    requested.append(("curr", ch))

            for meas_type, ch in requested:
                try:
                    col_idx = dlog_col_order.index((meas_type, ch))
                except ValueError:
                    continue

                values = [values_all[i * num_traces + col_idx] * 1000.0
                          for i in range(num_samples)]

                suffix = "I" if meas_type == "curr" else "V"
                label = f"{ulabel} CH{ch} {suffix}".strip()
                print(f"[Datalog] {label}: {len(values)} points (from dlog)")
                if values:
                    t = [i * sample_period_s for i in range(len(values))]
                    all_data[label] = {"time": t, "values": values}

            return all_data
        except Exception as e:
            print(f"[Datalog] dlog parse error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def run(self):
        import time
        try:
            sample_period_s = self.sample_period_us / 1_000_000.0

            if self.debug:
                all_data = self._generate_mock_data(sample_period_s)
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
                    print(f"[Datalog] Unit {unit_idx} INIT:DLOG sent at {time.time():.6f}")
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

            all_data = {}
            raw_dlog_list = []

            print(f"[Datalog] Waiting {self.monitoring_time_s + 5}s for capture...")
            wait_end = time.time() + self.monitoring_time_s + 5
            while time.time() < wait_end:
                if self._is_stopped:
                    print("[Datalog] Stopped by user during capture wait")
                    self.finished.emit()
                    return
                time.sleep(0.2)

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
                    raw_dlog = self._read_mmem_data(n6705c.instr, dlog_file)
                    t1 = time.time()
                    if isinstance(raw_dlog, bytes):
                        print(f"[Datalog] dlog downloaded: {len(raw_dlog)} bytes in {t1-t0:.1f}s")
                        raw_dlog_list.append(raw_dlog)

                        unit_data = self._parse_dlog_binary(
                            raw_dlog, curr_channels, volt_channels,
                            ulabel, sample_period_s
                        )
                except Exception as e:
                    print(f"[Datalog] dlog download/parse failed: {e}")

                if not unit_data:
                    print(f"[Datalog] Falling back to CSV export...")
                    csv_file = f"internal:\\datalog_cap_{unit_idx}.csv"
                    n6705c.instr.write(f'MMEM:EXP:DLOG "{csv_file}"')
                    for _ in range(15):
                        if self._is_stopped:
                            break
                        time.sleep(0.2)

                    t0 = time.time()
                    raw_csv = self._read_mmem_data(n6705c.instr, csv_file)
                    t1 = time.time()
                    if isinstance(raw_csv, bytes):
                        csv_text = raw_csv.decode('ascii', errors='replace')
                    else:
                        csv_text = raw_csv
                    print(f"[Datalog] CSV download: {len(csv_text)} chars in {t1-t0:.1f}s")

                    unit_data = self._parse_csv_text(
                        csv_text, curr_channels, volt_channels,
                        ulabel, sample_period_s
                    )

                if unit_data:
                    all_data.update(unit_data)

            print(f"[Datalog] Total channels with data: {len(all_data)}")
            self.dlog_raw_ready.emit(raw_dlog_list)
            self.data_ready.emit(all_data)
            self.finished.emit()
        except Exception as e:
            print(f"[Datalog] ERROR: {e}")
            import traceback
            traceback.print_exc()
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


class FixedPopupComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.view().window().setStyleSheet(
            "background-color: #0a1733; border: 1px solid #27406f;"
        )
        self.view().setStyleSheet(
            "background-color: #0a1733; color: #eaf2ff; "
            "selection-background-color: #334a7d; outline: 0px;"
        )

    def showPopup(self):
        super().showPopup()
        view = self.view()
        if view and view.window():
            popup = view.window()
            popup.setStyleSheet(
                "background-color: #0a1733; border: 1px solid #27406f;"
            )
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(global_pos.x(), global_pos.y())


class N6705CDatalogUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self):
        super().__init__()

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
        self._band_info = {}
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_region = None
        self.box_zoom_enabled = False
        self._pending_marker = None
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

        if DEBUG_N6705C_FLAG:
            self._add_default_debug_device()
            self._sync_device_card_states()

    @staticmethod
    def _get_checkmark_path(accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
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
        self.setStyleSheet("""
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

            QPushButton#searchBtn {
                min-height: 30px;
                max-width: 34px;
                min-width: 34px;
                padding: 0;
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
                font-size: 13px;
            }

            QPushButton#searchBtn:hover {
                background-color: #1a3260;
            }

            QPushButton#dynamicConnectBtn {
                min-height: 30px;
                min-width: 110px;
                border-radius: 8px;
                padding: 4px 12px;
                font-weight: 700;
            }

            QPushButton#dynamicConnectBtn[connected="false"] {
                background-color: #053b38;
                border: 1px solid #08c9a5;
                color: #10e7bc;
            }

            QPushButton#dynamicConnectBtn[connected="false"]:hover {
                background-color: #064744;
                border: 1px solid #19f0c5;
                color: #43f3d0;
            }

            QPushButton#dynamicConnectBtn[connected="true"] {
                background-color: #3a0828;
                border: 1px solid #d61b67;
                color: #ffb7d3;
            }

            QPushButton#dynamicConnectBtn[connected="true"]:hover {
                background-color: #4a0b31;
                border: 1px solid #f0287b;
                color: #ffd0e2;
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

            QScrollArea {
                background: transparent;
                border: none;
            }

            QScrollBar:vertical {
                background: #0a1733;
                width: 6px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical {
                background: #27406f;
                border-radius: 3px;
                min-height: 20px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """.replace("__UNCHECKED__", _cb_icons['unchecked']).replace("__CHECKED__", _cb_icons['checked']))

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
        content_layout.setSpacing(0)
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
        self.refresh_search_btn = QPushButton("\U0001F50D  Refresh Search")
        self.refresh_search_btn.setObjectName("chartToolBtn")
        self.refresh_search_btn.clicked.connect(self._on_refresh_search)
        search_row.addWidget(self.refresh_search_btn)
        search_row.addStretch()
        instr_inner.addLayout(search_row)

        self.device_list_scroll = QScrollArea()
        self.device_list_scroll.setWidgetResizable(True)
        self.device_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.device_list_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
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
        self.left_layout.setContentsMargins(0, 0, 4, 0)
        self.left_layout.setSpacing(10)

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

        self.reset_view_btn = QPushButton("\u2316 Reset View")
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

        self.channel_config_card = CardFrame("CHANNEL CONFIG", "\u2699")
        self._build_channel_config_card()
        main_area.addWidget(self.channel_config_card)

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
            "Set both Marker A and Marker B on the chart to see measurements."
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
        svg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons", "n6705c_thumb.svg")
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

        connect_btn = QPushButton("\U0001F517  Connect")
        connect_btn.setObjectName("dynamicConnectBtn")
        connect_btn.setProperty("connected", "false")
        connect_btn.clicked.connect(lambda: self._on_device_connect(visa_resource, serial))
        card_layout.addWidget(connect_btn)

        disconnect_btn = QPushButton("\u21BA  Disconnect")
        disconnect_btn.setObjectName("dynamicConnectBtn")
        disconnect_btn.setProperty("connected", "true")
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

        if DEBUG_N6705C_FLAG:
            self._add_default_debug_device()

        self.refresh_search_btn.setEnabled(False)
        self.refresh_search_btn.setText("Scanning...")

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
        self.refresh_search_btn.setEnabled(True)
        self.refresh_search_btn.setText("\U0001F50D  Refresh Search")
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
        self._connect_worker = _ConnectWorker(visa_resource, serial, DEBUG_FLAG)
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
        elif slot_label == "B":
            self.n6705c_b = n6705c
            self.is_connected_b = True

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
        for label_char in ["A", "B", "C", "D"]:
            slot = self.slot_frames[label_char]
            if slot.property("assigned_serial") == serial:
                self._clear_slot(label_char)

                if label_char == "A":
                    n6705c_to_close = self.n6705c_a
                    self.n6705c_a = None
                    self.is_connected_a = False
                elif label_char == "B":
                    n6705c_to_close = self.n6705c_b
                    self.n6705c_b = None
                    self.is_connected_b = False
                break

        self.connection_status_changed.emit(self.is_connected_a)
        self._refresh_channel_config()
        self._sync_device_card_states()

        if n6705c_to_close:
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
            "QScrollArea { background: transparent; border: none; }"
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
        self.channel_config_inner = QWidget()
        self.channel_config_inner.setStyleSheet("background: transparent;")
        self.channel_config_inner_layout = QHBoxLayout(self.channel_config_inner)
        self.channel_config_inner_layout.setContentsMargins(0, 0, 0, 0)
        self.channel_config_inner_layout.setSpacing(20)
        self.channel_config_layout.addWidget(self.channel_config_inner)

        self.ch_checkboxes_a = []
        self.ch_voltage_cbs_a = []
        self.ch_current_cbs_a = []
        self.ch_checkboxes_b = []
        self.ch_voltage_cbs_b = []
        self.ch_current_cbs_b = []
        self.unit_a_ch_label = QLabel()
        self.unit_a_ch_label.hide()
        self.unit_b_ch_label = QLabel()
        self.unit_b_ch_label.hide()
        self.ch_row_b_widget = QWidget()
        self.ch_row_b_widget.hide()

        self.no_instrument_label = QLabel("No instruments connected. Open Instrument Connection panel to connect.")
        self.no_instrument_label.setObjectName("hintLabel")
        self.no_instrument_label.setAlignment(Qt.AlignCenter)
        self.channel_config_layout.addWidget(self.no_instrument_label)

    def _refresh_channel_config(self):
        connected_slots = []
        for label_char in ["A", "B", "C", "D"]:
            slot = self.slot_frames[label_char]
            if slot.property("assigned_serial"):
                connected_slots.append(label_char)

        old_inner = self.channel_config_inner
        self.channel_config_layout.removeWidget(old_inner)
        old_inner.deleteLater()

        self.channel_config_inner = QWidget()
        self.channel_config_inner.setStyleSheet("background: transparent;")
        inner_layout = QHBoxLayout(self.channel_config_inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(16)
        self.channel_config_inner_layout = inner_layout

        self.ch_checkboxes_a = []
        self.ch_voltage_cbs_a = []
        self.ch_current_cbs_a = []
        self.ch_checkboxes_b = []
        self.ch_voltage_cbs_b = []
        self.ch_current_cbs_b = []

        if not connected_slots:
            self.no_instrument_label.show()
            self.channel_config_layout.insertWidget(0, self.channel_config_inner)
            return

        self.no_instrument_label.hide()

        for slot_char in connected_slots:
            slot = self.slot_frames[slot_char]
            serial = slot.property("assigned_serial")

            slot_frame = QFrame()
            slot_frame.setStyleSheet("""
                QFrame {
                    background-color: #070f24;
                    border: 1px solid #1a2b52;
                    border-radius: 6px;
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

                    scale_edit = QLineEdit(default_scale)
                    scale_edit.setMinimumWidth(38)
                    scale_edit.setAlignment(Qt.AlignCenter)
                    scale_edit.setStyleSheet(edit_style)
                    scale_edit.setProperty("ch_idx", ch)
                    scale_edit.setProperty("meas_type", prefix)
                    scale_edit.setProperty("field", "scale")

                    sep = QLabel("/")
                    sep.setFixedWidth(8)
                    sep.setAlignment(Qt.AlignCenter)
                    sep.setStyleSheet("color: #3a5070; font-size: 10px; border: none;")

                    offset_edit = QLineEdit(default_offset)
                    offset_edit.setMinimumWidth(38)
                    offset_edit.setAlignment(Qt.AlignCenter)
                    offset_edit.setStyleSheet(edit_style)
                    offset_edit.setProperty("ch_idx", ch)
                    offset_edit.setProperty("meas_type", prefix)
                    offset_edit.setProperty("field", "offset")

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

            if slot_char == "A":
                self.ch_checkboxes_a = current_cbs
                self.ch_voltage_cbs_a = voltage_cbs
                self.ch_current_cbs_a = current_cbs
            elif slot_char == "B":
                self.ch_checkboxes_b = current_cbs
                self.ch_voltage_cbs_b = voltage_cbs
                self.ch_current_cbs_b = current_cbs

            inner_layout.addWidget(slot_frame)

        inner_layout.addStretch()
        self.channel_config_layout.insertWidget(0, self.channel_config_inner)

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
        self._on_channel_visibility_changed()

    def _get_ch_scale_offset(self, data_key):
        ch_num, mtype, is_b = _parse_ch_label(data_key)
        if ch_num is None:
            return None, None, False

        slot_char = "B" if is_b else "A"
        prefix = mtype if mtype else "I"

        all_cbs = []
        if slot_char == "A":
            if prefix == "V":
                all_cbs = getattr(self, 'ch_voltage_cbs_a', [])
            else:
                all_cbs = getattr(self, 'ch_current_cbs_a', [])
        else:
            if prefix == "V":
                all_cbs = getattr(self, 'ch_voltage_cbs_b', [])
            else:
                all_cbs = getattr(self, 'ch_current_cbs_b', [])

        idx = ch_num - 1
        if idx < 0 or idx >= len(all_cbs):
            return None, None, False

        btn = all_cbs[idx]
        user_edited = btn.property("user_edited") or False
        scale_edit = btn.property("scale_edit")
        offset_edit = btn.property("offset_edit")
        if not scale_edit or not offset_edit:
            return None, None, False

        scale_val = _parse_value_with_unit(scale_edit.text())
        offset_val = _parse_value_with_unit(offset_edit.text())
        return scale_val, offset_val, user_edited

    def _set_ch_scale_offset_text(self, data_key, scale_text, offset_text):
        ch_num, mtype, is_b = _parse_ch_label(data_key)
        if ch_num is None:
            return

        slot_char = "B" if is_b else "A"
        prefix = mtype if mtype else "I"

        all_cbs = []
        if slot_char == "A":
            if prefix == "V":
                all_cbs = getattr(self, 'ch_voltage_cbs_a', [])
            else:
                all_cbs = getattr(self, 'ch_current_cbs_a', [])
        else:
            if prefix == "V":
                all_cbs = getattr(self, 'ch_voltage_cbs_b', [])
            else:
                all_cbs = getattr(self, 'ch_current_cbs_b', [])

        idx = ch_num - 1
        if idx < 0 or idx >= len(all_cbs):
            return

        btn = all_cbs[idx]
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
            getattr(self, 'ch_voltage_cbs_b', []),
            getattr(self, 'ch_current_cbs_b', []),
        ]
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

        lines = [f"Time: {x:.2f} s"]

        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        for idx, label in enumerate(sorted_keys):
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
                lines.append(f"<span style='color:{color}'>{label.strip()} : {_auto_format(val, ch_unit)}</span>")

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
        btn.setProperty("connected", "true" if connected else "false")
        btn.setText("\u21BA  Disconnect" if connected else "\U0001F517  Connect")
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

    def _update_recording_button_state(self, recording):
        self.is_recording = recording
        self.start_btn.setProperty("running", "true" if recording else "false")
        self.start_btn.setText(
            "\u25A0  Stop Recording" if recording else "\u25B7  Start Recording"
        )
        self.start_btn.style().unpolish(self.start_btn)
        self.start_btn.style().polish(self.start_btn)
        self.start_btn.update()

    def _on_record_type_changed(self):
        if self.type_current.isChecked():
            self.plot_widget.setLabel("left", "", color="#8eb0e3")
        else:
            self.plot_widget.setLabel("left", "", color="#8eb0e3")
        self._clear_analysis_card_cache()
        self._update_marker_analysis()

    def _get_visible_keys(self):
        visible_keys = set()
        for i, cb in enumerate(self.ch_current_cbs_a):
            if cb.isChecked():
                ch = i + 1
                for key in self.datalog_data:
                    k = key.strip()
                    if k.endswith(f"CH{ch} I") or k == f"CH{ch} I":
                        visible_keys.add(key)
        for i, cb in enumerate(self.ch_voltage_cbs_a):
            if cb.isChecked():
                ch = i + 1
                for key in self.datalog_data:
                    k = key.strip()
                    if k.endswith(f"CH{ch} V") or k == f"CH{ch} V":
                        visible_keys.add(key)
        for i, cb in enumerate(getattr(self, 'ch_current_cbs_b', [])):
            if cb.isChecked():
                ch = i + 1
                for key in self.datalog_data:
                    k = key.strip()
                    if k.endswith(f"CH{ch} I") and "B" in k:
                        visible_keys.add(key)
        for i, cb in enumerate(getattr(self, 'ch_voltage_cbs_b', [])):
            if cb.isChecked():
                ch = i + 1
                for key in self.datalog_data:
                    k = key.strip()
                    if k.endswith(f"CH{ch} V") and "B" in k:
                        visible_keys.add(key)
        for key in self.datalog_data:
            k = key.strip()
            ch_num, mtype, _ = _parse_ch_label(k)
            if mtype == "P" and ch_num is not None:
                visible_keys.add(key)
        return visible_keys

    def _on_channel_visibility_changed(self):
        if not self.datalog_data:
            return

        visible_keys = self._get_visible_keys()
        sorted_keys = sorted(self.datalog_data.keys(), key=_sort_key_for_label)
        visible_sorted = [k for k in sorted_keys if k in visible_keys]
        n = len(visible_sorted)

        for key, curve in self.plot_curves.items():
            curve.setVisible(key in visible_keys)

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
            list(getattr(self, 'ch_current_cbs_b', [])) +
            list(getattr(self, 'ch_voltage_cbs_b', []))
        )
        for cb in all_cbs:
            cb.blockSignals(True)
            cb.setChecked(False)
            ch_color = cb.property("ch_color") if hasattr(cb, 'property') else None
            if ch_color:
                cb.setStyleSheet(self._ch_toggle_style(ch_color, False))
            cb.blockSignals(False)

        for key, ch_data in self.datalog_data.items():
            k = key.strip()
            m = re.search(r'CH(\d+)\s+(I|V)', k)
            if not m:
                continue
            ch_num = int(m.group(1))
            mtype = m.group(2)
            is_b = "B " in key or "B_" in key

            if ch_num < 1 or ch_num > 4:
                continue

            idx = ch_num - 1
            if is_b:
                cbs = getattr(self, 'ch_current_cbs_b', []) if mtype == "I" else getattr(self, 'ch_voltage_cbs_b', [])
            else:
                cbs = self.ch_current_cbs_a if mtype == "I" else self.ch_voltage_cbs_a

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

                    unit = "mA" if mtype == "I" else "mV"
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
            if active_a or voltage_a:
                n6705c_list.append(self.n6705c_a)
                channels_per_unit.append(active_a)
                voltage_channels_per_unit.append(voltage_a)
                unit_labels.append("A")

        if self.is_connected_b and self.n6705c_b:
            active_b = [i + 1 for i, cb in enumerate(self.ch_current_cbs_b) if cb.isChecked()]
            voltage_b = [i + 1 for i, cb in enumerate(self.ch_voltage_cbs_b) if cb.isChecked()]
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

        self._record_thread = QThread()
        self._record_worker = _DatalogWorker(
            n6705c_list, channels_per_unit, unit_labels,
            record_type, sample_period, monitor_time,
            debug=DEBUG_FLAG,
            voltage_channels_per_unit=voltage_channels_per_unit
        )
        self._record_worker.moveToThread(self._record_thread)

        self._record_thread.started.connect(self._record_worker.run)
        self._record_worker.data_ready.connect(self._on_data_ready)
        self._record_worker.dlog_raw_ready.connect(self._on_dlog_raw_ready)
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

    def _on_data_ready(self, data):
        self.datalog_data = data
        self._clear_analysis_card_cache()
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _on_dlog_raw_ready(self, dlog_list):
        self._raw_dlog_list = dlog_list

    def _on_recording_finished(self):
        self._update_recording_button_state(False)
        self._record_worker = None
        self._record_thread = None

    def _on_recording_error(self, msg):
        print(f"[Datalog] Recording error: {msg}")
        self._update_recording_button_state(False)

    def _refresh_plot(self):
        self.plot_widget.clear()
        self.plot_curves.clear()
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_region = None
        self._band_info = {}

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
            self.box_zoom_btn.setText("\u2316 Box Zoom: OFF")

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.setMouseMode(vb.PanMode)
        self.plot_widget.setMouseEnabled(x=True, y=False)

        self._refresh_plot()

    def _toggle_box_zoom(self):
        self.box_zoom_enabled = not self.box_zoom_enabled
        if self.box_zoom_enabled:
            self.box_zoom_btn.setText("\u2316 Box Zoom: ON")
            self.plot_widget.setMouseEnabled(x=True, y=True)
            vb = self.plot_widget.getPlotItem().getViewBox()
            vb.setMouseMode(vb.RectMode)
        else:
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
            display = self.ch_name_renames.get(key, key.strip())
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
        if self.marker_a_pos is None or self.marker_b_pos is None:
            self.analysis_hint_label.setVisible(True)
            self.meas_table.setVisible(False)
            return

        self.analysis_hint_label.setVisible(False)
        self.meas_table.setVisible(True)

        t_a = self.marker_a_pos
        t_b = self.marker_b_pos
        t1 = min(t_a, t_b)
        t2 = max(t_a, t_b)
        delta = t2 - t1
        freq = 1.0 / delta if delta > 0 else 0.0

        is_current = self.type_current.isChecked()

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

        ch_list = [(k, self.datalog_data[k]) for k in sorted(self.datalog_data.keys(), key=_sort_key_for_label)]
        num_rows = 1 + len(ch_list)
        num_cols = len(headers)

        self.meas_table.blockSignals(True)
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

        info_text = f"\u0394 = {delta:.6f} s    Freq = {freq_str}"

        self._set_meas_cell(0, 0, "Time", "#5a7fad", bg="#0b1528")
        self._set_meas_cell(0, 1, f"{t_a:.6f} s", "#8eb0e3", bg="#0b1528")

        mid_col = 2
        if selected:
            mid_span = len(selected)
            self.meas_table.setSpan(0, mid_col, 1, mid_span)
            self._set_meas_cell(0, mid_col, info_text, "#5a7fad", align=Qt.AlignCenter, bg="#0b1528")
        else:
            self._set_meas_cell(0, mid_col, info_text, "#5a7fad", align=Qt.AlignCenter, bg="#0b1528")

        self._set_meas_cell(0, num_cols - 1, f"{t_b:.6f} s", "#8eb0e3", bg="#0b1528")

        ROW_BG = ["#080f22", "#0a1530"]

        for ch_idx, (label, ch_data) in enumerate(ch_list):
            row = 1 + ch_idx
            color_hex = _color_for_label(label)
            row_bg = ROW_BG[ch_idx % 2]

            ch_num, mtype, _ = _parse_ch_label(label)
            ch_is_current = (mtype == "I") if mtype else is_current
            val_unit = "mA" if ch_is_current else "mV"

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

            self._set_meas_cell(row, 0, label.strip(), color_hex, bg=row_bg)
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
                    val_str = _auto_format(c, "mAh" if ch_is_current else "mWh")
                elif metric_key == "charge_c":
                    c = seg_avg * dt / 1000.0
                    val_str = _auto_format(c, "C" if ch_is_current else "J")
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
        for label in self.datalog_data.keys():
            self.label_ch_combo.addItem(label.strip())
        idx = self.label_ch_combo.findText(current)
        if idx >= 0:
            self.label_ch_combo.setCurrentIndex(idx)
        elif self.label_ch_combo.count() > 0:
            self.label_ch_combo.setCurrentIndex(0)

    def _add_custom_label(self):
        ch_name = self.label_ch_combo.currentText().strip()
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
        except Exception:
            pass

    def _import_csv(self, path):
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if not lines:
            return

        header = lines[0].strip().split(",")
        if len(header) < 2:
            return

        channel_names = [h.strip() for h in header[1:]]

        all_data = {}
        for name in channel_names:
            all_data[name] = {"time": [], "values": []}

        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue

            try:
                t = float(parts[0])
            except ValueError:
                continue

            for col_idx, name in enumerate(channel_names):
                try:
                    val = float(parts[1 + col_idx])
                except (ValueError, IndexError):
                    val = 0.0
                all_data[name]["time"].append(t)
                all_data[name]["values"].append(val)

        empty_keys = [k for k, v in all_data.items() if not v["time"]]
        for k in empty_keys:
            del all_data[k]

        if not all_data:
            return

        self.datalog_data = all_data
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _import_edlg(self, path):
        import zipfile, struct, re
        from xml.etree import ElementTree

        with zipfile.ZipFile(path, 'r') as zf:
            mdlg_name = None
            dlog_name = None
            for name in zf.namelist():
                if name.endswith('.mdlg'):
                    mdlg_name = name
                elif name.endswith('.dlog'):
                    dlog_name = name

            if not dlog_name:
                return

            trace_names = []
            if mdlg_name:
                mdlg_xml = zf.read(mdlg_name).decode('utf-8', errors='replace')
                root = ElementTree.fromstring(mdlg_xml)
                for trace_el in root.findall('.//TraceSettings/Frames/Frame/Trace'):
                    name_el = trace_el.find('Name')
                    if name_el is not None and name_el.text:
                        trace_names.append(name_el.text.strip())

            raw_data = zf.read(dlog_name)

        xml_header = raw_data[:min(len(raw_data), 8192)].decode('ascii', errors='replace')

        sample_period_s = 0.001
        tint_match = re.search(r'<tint>([\d.eE+\-]+)</tint>', xml_header)
        if tint_match:
            sample_period_s = float(tint_match.group(1))

        dlog_col_order = []
        for m in re.finditer(r'<channel id="(\d+)">(.*?)</channel>', xml_header, re.DOTALL):
            ch_id = int(m.group(1))
            ch_xml = m.group(2)
            sc = re.search(r'<sense_curr>(\d+)</sense_curr>', ch_xml)
            sv = re.search(r'<sense_volt>(\d+)</sense_volt>', ch_xml)
            if sv and sv.group(1) == '1':
                dlog_col_order.append(("volt", ch_id))
            if sc and sc.group(1) == '1':
                dlog_col_order.append(("curr", ch_id))

        num_traces = len(dlog_col_order)
        if num_traces == 0:
            return

        close_tag = b'</dlog>'
        tag_pos = raw_data.find(close_tag)
        if tag_pos < 0:
            return

        data_start = tag_pos + len(close_tag)
        while data_start < len(raw_data) and raw_data[data_start:data_start+1] in (b'\r', b'\n'):
            data_start += 1
        data_start += 8

        if data_start + num_traces * 4 > len(raw_data):
            return

        data_section = raw_data[data_start:]
        float_count = len(data_section) // 4
        num_samples = float_count // num_traces

        values_all = struct.unpack_from(f'>{float_count}f', data_section, 0)

        has_power = any(n.endswith('-P1') or n.endswith('-P2') or n.endswith('-P3') or n.endswith('-P4')
                        for n in trace_names)

        all_data = {}
        for col_idx, (meas_type, ch) in enumerate(dlog_col_order):
            values = [values_all[i * num_traces + col_idx] * 1000.0
                      for i in range(num_samples)]
            suffix = "I" if meas_type == "curr" else "V"
            label = f"CH{ch} {suffix}"
            if values:
                t = [i * sample_period_s for i in range(len(values))]
                all_data[label] = {"time": t, "values": values}

        if has_power:
            for ch_id in sorted(set(c for _, c in dlog_col_order)):
                v_label = f"CH{ch_id} V"
                i_label = f"CH{ch_id} I"
                if v_label in all_data and i_label in all_data:
                    v_vals = all_data[v_label]["values"]
                    i_vals = all_data[i_label]["values"]
                    t = all_data[v_label]["time"]
                    p_vals = [v * i / 1000.0 for v, i in zip(v_vals, i_vals)]
                    all_data[f"CH{ch_id} P"] = {"time": t, "values": p_vals}

        if not all_data:
            return

        self._raw_dlog_list = [raw_data]
        self.datalog_data = all_data
        self._sync_checkboxes_to_data()
        self._refresh_plot()

    def _import_dlog(self, path):
        import struct, re

        with open(path, "rb") as f:
            raw_data = f.read()

        xml_header = raw_data[:min(len(raw_data), 8192)].decode('ascii', errors='replace')

        sample_period_s = 0.001
        tint_match = re.search(r'<tint>([\d.eE+\-]+)</tint>', xml_header)
        if tint_match:
            sample_period_s = float(tint_match.group(1))

        dlog_col_order = []
        for m in re.finditer(r'<channel id="(\d+)">(.*?)</channel>', xml_header, re.DOTALL):
            ch_id = int(m.group(1))
            ch_xml = m.group(2)
            sc = re.search(r'<sense_curr>(\d+)</sense_curr>', ch_xml)
            sv = re.search(r'<sense_volt>(\d+)</sense_volt>', ch_xml)
            if sv and sv.group(1) == '1':
                dlog_col_order.append(("volt", ch_id))
            if sc and sc.group(1) == '1':
                dlog_col_order.append(("curr", ch_id))

        num_traces = len(dlog_col_order)
        if num_traces == 0:
            return

        close_tag = b'</dlog>'
        tag_pos = raw_data.find(close_tag)
        if tag_pos < 0:
            return

        data_offset = tag_pos + len(close_tag) + 9
        if data_offset + num_traces * 4 > len(raw_data):
            return

        data_section = raw_data[data_offset:]
        float_count = len(data_section) // 4
        num_samples = float_count // num_traces

        values_all = struct.unpack_from(f'>{float_count}f', data_section, 0)

        all_data = {}
        for col_idx, (meas_type, ch) in enumerate(dlog_col_order):
            values = [values_all[i * num_traces + col_idx] * 1000.0
                      for i in range(num_samples)]
            suffix = "I" if meas_type == "curr" else "V"
            label = f"CH{ch} {suffix}"
            if values:
                t = [i * sample_period_s for i in range(len(values))]
                all_data[label] = {"time": t, "values": values}

        if not all_data:
            return

        self._raw_dlog_list = [raw_data]
        self.datalog_data = all_data
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
                    header = "Time(s)," + ",".join(labels)
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