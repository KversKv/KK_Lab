#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import math
import os
import statistics
import subprocess
import sys
import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QGridLayout, QFrame, QScrollArea,
    QSizePolicy, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QFileDialog, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
import pyqtgraph as pg
from ui.styles import SCROLL_AREA_STYLE, START_BTN_STYLE, update_start_btn_state
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from ui.widgets.dark_combobox import DarkComboBox
from ui.modules.oscilloscope_module_frame import OscilloscopeConnectionMixin
from ui.modules.chamber_module_frame import VT6002ConnectionMixin
from ui.modules.keysight_53230a_module_frame import Keysight53230AConnectionMixin
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockMSO64B, MockVT6002, MockKeysight53230A
from instruments.chambers import TemperatureStabilizer


class _CLKTestWorker(QObject):
    log = Signal(str)
    finished = Signal(dict)
    progress = Signal(dict)
    progress_int = Signal(int)
    error = Signal(str)

    def __init__(self, test_item, config, mso64b=None, vt6002=None, counter=None, mock_mode=False, parent=None):
        super().__init__(parent)
        self.test_item = test_item
        self.config = config
        self.mso64b = mso64b
        self.vt6002 = vt6002
        self.counter = counter
        self.mock_mode = mock_mode
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def _read_frequency(self, mso_channel=1, counter_channel=1):
        freq_instrument = self.config.get("freq_instrument", "MSO64B")
        if freq_instrument == "53230A":
            if self.counter is None:
                raise RuntimeError("53230A frequency counter not connected")
            return float(self.counter.measure_frequency(channel=counter_channel))
        if freq_instrument == "DigitMultimeter":
            raise NotImplementedError("DigitMultimeter frequency read is not implemented yet")
        if self.mso64b is None:
            raise RuntimeError("MSO64B oscilloscope not connected")
        return float(self.mso64b.get_dvm_frequency(enable_counter=True, wait_time=0.3))

    def run(self):
        try:
            if self.test_item == "cap_freq":
                result = self._run_cap_freq()
            elif self.test_item == "temp_freq":
                result = self._run_temp_freq()
            elif self.test_item == "clk_perf":
                result = self._run_clk_perf()
            else:
                raise ValueError("Unknown test item")
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _simulate_frequency(self, x, nominal=32768.0, gain=1.0, noise=0.5):
        base = nominal + x * gain
        ripple = math.sin(x / 5.0) * noise
        return base + ripple

    def _run_cap_freq(self):
        start_code = self.config["reg_min"]
        end_code = self.config["reg_max"]
        step = self.config["reg_step"]
        device_addr = int(self.config["iic_device_addr"], 16)
        reg_addr = int(self.config["iic_reg_addr"], 16)
        width_flag = self.config["iic_width_flag"]
        msb = self.config["iic_msb"]
        lsb = self.config["iic_lsb"]
        mso_channel = self.config.get("mso_channel", 2)
        freq_instrument = self.config.get("freq_instrument", "MSO64B")

        values = []
        codes = list(range(start_code, end_code + 1, step))
        if not codes:
            raise ValueError("Invalid compensation code range")

        self.log.emit("[INFO] Starting test: Ctrim vs Frequency")
        self.log.emit(f"[INFO] IIC Device Addr = 0x{device_addr:02X}, REG Addr = 0x{reg_addr:04X}")
        self.log.emit(f"[INFO] Width Flag = {width_flag}, MSB = {msb}, LSB = {lsb}")
        self.log.emit(f"[INFO] Frequency Instrument = {freq_instrument}")
        if freq_instrument == "MSO64B":
            self.log.emit(f"[INFO] MSO64B Channel = CH{mso_channel}")

        bit_mask = ((1 << (msb - lsb + 1)) - 1) << lsb

        if not self.mock_mode:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            iic = I2CInterface()
            if not iic.initialize():
                raise RuntimeError("I2C interface initialization failed")
            self.log.emit("[INFO] I2C interface initialized successfully")
            if freq_instrument == "MSO64B":
                if self.mso64b is None:
                    raise RuntimeError("MSO64B oscilloscope not connected")
                self.mso64b.instrument.write(f'DVM:SOURCE CH{mso_channel}')
                self.log.emit(f"[INFO] MSO64B DVM Source set to CH{mso_channel}")
            elif freq_instrument == "53230A" and self.counter is None:
                raise RuntimeError("53230A frequency counter not connected")

            orig_val = iic.read(device_addr, reg_addr, width_flag)
            self.log.emit(f"[INFO] Register original value = 0x{orig_val:04X}, bit_mask = 0x{bit_mask:04X}")
            base_val = orig_val & ~bit_mask
            default_code = (orig_val & bit_mask) >> lsb
            iic.write(device_addr, reg_addr, base_val, width_flag)
            time.sleep(0.5)
            self.log.emit(f"[INFO] Reserved bits (other bits) = 0x{base_val:04X}")
            self.log.emit(f"[INFO] Default Code = {default_code}")
        else:
            orig_val = 0x1120
            base_val = orig_val & ~bit_mask
            default_code = (orig_val & bit_mask) >> lsb
            self.log.emit(f"[MOCK] Register mock original value = 0x{orig_val:04X}, Reserved bits = 0x{base_val:04X}, Default Code = {default_code}")

        total_codes = len(codes)
        for idx, code in enumerate(codes):
            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            write_val = base_val | ((code << lsb) & bit_mask)
            if self.mock_mode:
                mock_nominal = 32768.0
                freq = self._simulate_frequency(
                    code, nominal=mock_nominal,
                    gain=3.5, noise=max(0.02, mock_nominal * 0.000001)
                )
                self.log.emit(f"[MOCK] I2C write 0x{device_addr:02X} reg=0x{reg_addr:04X} data=0x{write_val:04X}")
            else:
                iic.write(device_addr, reg_addr, write_val, width_flag)
                time.sleep(0.1)
                freq = self._read_frequency(mso_channel=mso_channel)

            values.append({"x": code, "freq": freq})
            self.progress.emit({"mode": "cap_freq", "current": code, "freq": freq})
            self.progress_int.emit(int((idx + 1) * 100 / total_codes))
            self.log.emit(f"[DATA] Code={code:>3d}  |  RegVal=0x{write_val:04X}  |  Freq={freq:>15.6f} Hz")
            time.sleep(0.03)
        iic.write(device_addr, reg_addr, orig_val, width_flag)
        return {"mode": "cap_freq", "data": values, "default_code": default_code}

    def _float_range(self, start, end, step):
        arr = []
        if step <= 0:
            return arr
        if start <= end:
            x = start
            while x <= end + 1e-9:
                arr.append(round(x, 3))
                x += step
        else:
            x = start
            while x >= end - 1e-9:
                arr.append(round(x, 3))
                x -= step
        return arr

    def _run_temp_freq(self):
        temp_start = self.config["temp_start"]
        temp_end = self.config["temp_end"]
        temp_step = self.config["temp_step"]
        soak_time = self.config.get("temp_soak_time", 180)
        tolerance = self.config.get("temp_stable_tolerance", 0.5)
        mso_channel = self.config.get("mso_channel", 2)

        temps = self._float_range(temp_start, temp_end, temp_step)
        if not temps:
            raise ValueError("Invalid temperature range")

        values = []
        self.log.emit("[INFO] Starting test: Temperature vs Frequency")
        self.log.emit(f"[INFO] Temperature Range = {temp_start} °C -> {temp_end} °C, step={temp_step} °C")
        self.log.emit(f"[INFO] Soak Time       = {soak_time} s, Tolerance = {tolerance} °C")

        if self.mock_mode:
            self.log.emit("[MOCK] Using simulated chamber and frequency data")
            mock_nominal = 32768.0
            total_temps = len(temps)
            for idx, t in enumerate(temps):
                if self._stop_flag:
                    self.log.emit("[WARN] Test stopped")
                    break
                delta_ppm = (t - 25.0) * 0.8 + math.sin(t / 15.0) * 0.6
                freq = mock_nominal * (1.0 + delta_ppm / 1_000_000.0)
                values.append({"x": t, "freq": freq})
                self.progress.emit({"mode": "temp_freq", "current": t, "freq": freq})
                self.progress_int.emit(int((idx + 1) * 100 / total_temps))
                self.log.emit(f"[DATA] Temp={t:>7.1f} °C  |  Freq={freq:>15.6f} Hz")
                time.sleep(0.05)
            return {"mode": "temp_freq", "data": values}

        chamber = self.vt6002
        if not chamber:
            raise RuntimeError("VT6002 chamber not connected")

        freq_instrument = self.config.get("freq_instrument", "MSO64B")
        if freq_instrument == "MSO64B":
            if self.mso64b is None:
                raise RuntimeError("MSO64B oscilloscope not connected")
            self.mso64b.instrument.write(f'DVM:SOURCE CH{mso_channel}')
            self.log.emit(f"[INFO] MSO64B DVM Source set to CH{mso_channel}")
        elif freq_instrument == "53230A":
            if self.counter is None:
                raise RuntimeError("53230A frequency counter not connected")
            self.log.emit("[INFO] 53230A frequency counter ready")

        total_temps = len(temps)
        for idx, t in enumerate(temps):
            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            chamber.set_temperature(t)
            self.log.emit(f"[INFO] [{idx + 1}/{len(temps)}] Chamber set temperature: {t:.1f} °C, waiting for stabilization...")

            if idx == 0:
                try:
                    chamber.start()
                    self.log.emit("[INFO] Chamber started (constant-temp run command sent)")
                except Exception as e:
                    self.log.emit(f"[WARN] Chamber start command failed: {e}")

            stabilizer = TemperatureStabilizer(
                chamber,
                tolerance=tolerance,
                log_fn=self.log.emit,
                stop_check=lambda: self._stop_flag,
            )
            result = stabilizer.wait_for_stable(t)

            if self._stop_flag or result.reason == "stopped":
                self.log.emit("[WARN] Test stopped")
                break

            actual_temp = result.actual if result.actual is not None else chamber.get_current_temp()
            self.log.emit(
                f"[INFO] [{idx + 1}/{len(temps)}] Temperature {result.reason}: "
                f"target={t:.1f} °C, actual={actual_temp:.2f} °C, "
                f"polled {result.poll_count} times, waited {result.waited_s:.0f}s"
            )

            self.log.emit(f"[INFO] DUT thermal soak in progress ({soak_time}s)...")
            for i in range(soak_time):
                if self._stop_flag:
                    break
                time.sleep(1)

            if self._stop_flag:
                self.log.emit("[WARN] Test stopped")
                break

            freq = self._read_frequency(mso_channel=mso_channel)
            actual_temp = chamber.get_current_temp()
            values.append({"x": actual_temp, "freq": freq})
            self.progress.emit({"mode": "temp_freq", "current": actual_temp, "freq": freq})
            self.progress_int.emit(int((idx + 1) * 100 / total_temps))
            self.log.emit(f"[DATA] Temp={actual_temp:>7.2f} °C  |  Freq={freq:>15.6f} Hz")

        chamber.set_temperature(25.0)
        self.log.emit("[INFO] Chamber restored to 25.0 °C")

        if values:
            self.log.emit("")
            self.log.emit("=" * 60)
            self.log.emit("  Temperature Frequency Deviation Test Summary")
            self.log.emit("=" * 60)
            self.log.emit(f"  {'#':>3}  {'Temp (°C)':>10}  {'Freq (Hz)':>18}  {'Offset (ppm)':>12}")
            self.log.emit("-" * 60)
            ref_freq = values[0]["freq"] if values else 0
            for i, v in enumerate(values):
                ppm = (v["freq"] - ref_freq) / ref_freq * 1e6 if ref_freq else 0
                self.log.emit(
                    f"  {i + 1:>3}  {v['x']:>10.2f}  {v['freq']:>18.6f}  {ppm:>+12.2f}"
                )
            self.log.emit("=" * 60)
            self.log.emit("")

        return {"mode": "temp_freq", "data": values}

    def _run_clk_perf(self):
        source = self.config["clk_source"]
        self.log.emit("[INFO] Starting test: Clock Performance Analysis")
        self.log.emit(f"[INFO] Data Source      = {source}")

        self.progress_int.emit(0)

        if source == "Import CSV":
            samples = self._clk_perf_from_csv()
        elif source == "MSO64B":
            samples = self._clk_perf_from_mso64b()
        elif source == "DSLogic":
            samples = self._clk_perf_from_dslogic()
        else:
            raise ValueError(f"Unknown data source: {source}")

        self.progress_int.emit(50)

        result = self._analyze_clk_perf(samples)

        self.progress_int.emit(100)

        return result

    def _clk_perf_from_csv(self):
        csv_path = self.config.get("csv_path", "")
        if not csv_path:
            raise ValueError("No CSV file selected")

        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            raw_lines = f.readlines()

        if not raw_lines:
            raise ValueError("CSV file is empty")

        first_lines = "".join(raw_lines[:10]).lower()

        if "tekscope" in first_lines or "name,type,src" in first_lines:
            samples = self._parse_tek_csv(raw_lines)
            self.log.emit(f"[INFO] Detected MSO64B (TekScope) CSV format")
        elif "libsigrok" in first_lines or "dslogic" in first_lines or "sample rate" in first_lines:
            samples = self._parse_dslogic_csv(raw_lines)
            self.log.emit(f"[INFO] Detected DSLogic CSV format")
        else:
            samples = self._parse_generic_csv(raw_lines)
            self.log.emit(f"[INFO] Using generic CSV parser")

        if not samples:
            raise ValueError("No valid period data found in CSV")

        self.log.emit(f"[INFO] CSV parsing complete, {len(samples)} period data points")
        return samples

    def _parse_tek_csv(self, lines):
        data_rows = []
        header_found = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("name,type"):
                header_found = True
                continue
            if not header_found:
                continue
            parts = line.split(",")
            if len(parts) >= 5:
                try:
                    timestamp = float(parts[3])
                    delta = float(parts[4])
                    data_rows.append((timestamp, delta))
                except ValueError:
                    continue

        if len(data_rows) < 3:
            raise ValueError("Insufficient data rows in TekScope CSV")

        samples = []
        i = 1
        while i < len(data_rows) - 1:
            _, d1 = data_rows[i]
            _, d2 = data_rows[i + 1]
            if d1 > 0 and d2 > 0:
                full_period = d1 + d2
                mid_time = data_rows[i][0] + d1 / 2.0
                samples.append((mid_time, full_period))
            i += 2

        return samples

    def _parse_dslogic_csv(self, lines):
        sample_rate = None
        edges = []
        data_started = False

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith(";"):
                lower = line.lower()
                if "sample rate" in lower:
                    parts = lower.split(":")
                    if len(parts) >= 2:
                        rate_str = parts[-1].strip()
                        rate_str = rate_str.replace("mhz", "e6").replace("khz", "e3").replace("ghz", "e9")
                        rate_str = rate_str.replace("m samples", "").replace("samples", "").strip()
                        try:
                            sample_rate = float(rate_str)
                        except ValueError:
                            import re
                            m = re.search(r'([\d.]+)\s*(mhz|khz|ghz|hz)', lower)
                            if m:
                                val = float(m.group(1))
                                unit = m.group(2)
                                mul = {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
                                sample_rate = val * mul.get(unit, 1)
                continue
            if line.lower().startswith("time"):
                data_started = True
                continue
            if not data_started:
                continue

            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    t = float(parts[0])
                    level = int(parts[1].strip())
                    edges.append((t, level))
                except (ValueError, IndexError):
                    continue

        if sample_rate:
            self.log.emit(f"[INFO] DSLogic Sample Rate = {sample_rate / 1e6:.3f} MHz")

        rising_times = []
        for i in range(len(edges)):
            if edges[i][1] == 1:
                if i == 0 or edges[i - 1][1] == 0:
                    rising_times.append(edges[i][0])

        if len(rising_times) < 2:
            raise ValueError("Insufficient rising edge data in DSLogic CSV")

        samples = []
        for i in range(1, len(rising_times)):
            period = rising_times[i] - rising_times[i - 1]
            if period > 0:
                mid_time = (rising_times[i - 1] + rising_times[i]) / 2.0
                samples.append((mid_time, period))

        return samples

    def _parse_generic_csv(self, lines):
        samples = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith(";") or line.startswith("#"):
                continue
            parts = line.split(",")
            try:
                if len(parts) >= 2:
                    t = float(parts[0])
                    period = float(parts[1])
                    if period > 0:
                        samples.append((t, period))
                elif len(parts) == 1:
                    period = float(parts[0])
                    if period > 0:
                        samples.append((len(samples), period))
            except ValueError:
                continue
        return samples

    def _clk_perf_from_mso64b(self):
        duration = self.config["clk_duration"]
        sample_rate_mhz = self.config.get("clk_sample_rate", 100.0)
        mso_channel = self.config.get("mso_channel", 2)
        self.log.emit(f"[INFO] MSO64B Sample Rate = {sample_rate_mhz} MHz, Duration = {duration} s")
        self.log.emit(f"[INFO] MSO64B Channel = CH{mso_channel}")

        samples = []
        if self.mock_mode:
            mock_nominal = 32768.0
            nominal_period = 1.0 / mock_nominal
            count = max(100, int(duration * 1000))
            for i in range(count):
                if self._stop_flag:
                    self.log.emit("[WARN] Test stopped")
                    break
                t = i * 0.001
                jitter = math.sin(i / 35.0) * nominal_period * 0.003 + (math.cos(i / 13.0) * nominal_period * 0.001)
                period = nominal_period + jitter
                samples.append((t, period))
                if (i + 1) % max(1, count // 50) == 0:
                    self.progress_int.emit(int((i + 1) * 50 / count))
            self.log.emit(f"[MOCK] MSO64B online sample count = {len(samples)}")
        else:
            scope = self.mso64b
            remote_csv = 'C:/Temp/clk_edge_search.csv'

            self.log.emit("[INFO] Configuring MSO64B horizontal parameters...")
            scope.configure_horizontal(duration, sample_rate_mhz)
            self.log.emit(f"[INFO] Horizontal Scale = {duration / 10:.4f} s/div, Duration = {duration} s")
            self.progress_int.emit(5)

            if self._stop_flag:
                return samples

            self.log.emit(f"[INFO] Configuring Edge Search: CH{mso_channel}, BOTH edges")
            scope.setup_edge_search(mso_channel, slope='BOTH')
            self.progress_int.emit(10)

            if self._stop_flag:
                return samples

            acq_timeout = max(duration * 3, 30)
            self.log.emit(f"[INFO] Starting single acquisition (timeout {acq_timeout:.0f}s)...")
            scope.single_acquisition(timeout_s=acq_timeout)
            self.log.emit("[INFO] Acquisition complete")
            self.progress_int.emit(30)

            if self._stop_flag:
                return samples

            time.sleep(1.0)
            total_marks = scope.get_search_total()
            self.log.emit(f"[INFO] Edge Search result: {total_marks} marks found")

            if total_marks < 3:
                raise ValueError(f"Edge Search found only {total_marks} edges, insufficient data")

            self.log.emit(f"[INFO] Exporting Search Table -> {remote_csv}")
            scope.export_search_table_csv(remote_csv)
            time.sleep(1.0)
            self.progress_int.emit(35)

            if self._stop_flag:
                return samples

            self.log.emit("[INFO] Reading CSV file from MSO64B...")
            csv_content = scope.read_remote_file(remote_csv)
            scope.delete_remote_file(remote_csv)
            self.progress_int.emit(40)

            raw_lines = csv_content.splitlines(keepends=True)
            if not raw_lines:
                raise ValueError("CSV retrieved from MSO64B is empty")

            self.log.emit(f"[INFO] CSV content {len(raw_lines)} lines, parsing...")
            samples = self._parse_tek_csv(raw_lines)

            if not samples:
                raise ValueError("No valid period data parsed from MSO64B exported CSV")

            self.log.emit(f"[INFO] MSO64B online acquisition parsed, {len(samples)} period data points")

        return samples

    def _clk_perf_from_dslogic(self):
        duration = self.config["clk_duration"]
        sample_rate_mhz = self.config.get("clk_sample_rate", 100.0)
        self.log.emit(f"[INFO] DSLogic Sample Rate = {sample_rate_mhz} MHz, Duration = {duration} s")

        samples = []
        if self.mock_mode:
            mock_nominal = 32768.0
            nominal_period = 1.0 / mock_nominal
            count = max(100, int(duration * 1000))
            for i in range(count):
                if self._stop_flag:
                    self.log.emit("[WARN] Test stopped")
                    break
                t = i * 0.001
                jitter = math.sin(i / 28.0) * nominal_period * 0.004 + (math.cos(i / 11.0) * nominal_period * 0.0015)
                period = nominal_period + jitter
                samples.append((t, period))
                if (i + 1) % max(1, count // 50) == 0:
                    self.progress_int.emit(int((i + 1) * 50 / count))
            self.log.emit(f"[MOCK] DSLogic online sample count = {len(samples)}")
        else:
            sample_rate_hz = int(sample_rate_mhz * 1e6)
            total_samples = int(sample_rate_hz * duration)
            self.log.emit(f"[INFO] Total samples = {total_samples:,}")

            sigrok_cli = self._find_sigrok_cli()
            if not sigrok_cli:
                raise FileNotFoundError(
                    "sigrok-cli not found. Please install the sigrok suite and ensure sigrok-cli is in PATH, "
                    "or add the sigrok-cli.exe directory to the system environment variable"
                )
            self.log.emit(f"[INFO] sigrok-cli path: {sigrok_cli}")

            if self._stop_flag:
                return samples

            self.log.emit("[INFO] Scanning DSLogic devices...")
            scan_cmd = [sigrok_cli, "--driver", "dreamsourcelab-dslogic", "--scan"]
            try:
                scan_result = subprocess.run(
                    scan_cmd, capture_output=True, text=True, timeout=15, encoding="utf-8"
                )
                if scan_result.returncode != 0:
                    err_msg = scan_result.stderr.strip() or scan_result.stdout.strip()
                    raise ConnectionError(f"DSLogic device scan failed: {err_msg}")
                scan_output = scan_result.stdout.strip()
                if not scan_output:
                    raise ConnectionError("No DSLogic device detected, please check USB connection and driver")
                self.log.emit(f"[INFO] Device detected: {scan_output}")
            except subprocess.TimeoutExpired:
                raise ConnectionError("DSLogic device scan timed out")

            if self._stop_flag:
                return samples

            if getattr(sys, 'frozen', False):
                results_dir = os.path.join(os.path.dirname(sys.executable), "Results")
            else:
                results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "Results")
            os.makedirs(results_dir, exist_ok=True)
            csv_path = os.path.join(results_dir, "dslogic_capture.csv")

            if os.path.exists(csv_path):
                os.remove(csv_path)

            capture_cmd = [
                sigrok_cli,
                "--driver", "dreamsourcelab-dslogic",
                "--config", f"samplerate={sample_rate_hz}",
                "--samples", str(total_samples),
                "--channels", "0",
                "--output-format", "csv:dedup",
                "--output-file", csv_path,
            ]
            self.log.emit(f"[INFO] Starting capture (dedup mode): samplerate={sample_rate_hz}, samples={total_samples}")
            self.log.emit(f"[CMD] {' '.join(capture_cmd)}")

            capture_timeout = max(duration * 3 + 30, 60)
            try:
                proc = subprocess.Popen(
                    capture_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                t0 = time.time()
                while proc.poll() is None:
                    if self._stop_flag:
                        proc.terminate()
                        proc.wait(timeout=5)
                        self.log.emit("[WARN] User aborted capture")
                        return samples
                    elapsed = time.time() - t0
                    if elapsed > capture_timeout:
                        proc.terminate()
                        proc.wait(timeout=5)
                        raise TimeoutError(f"DSLogic capture timed out ({capture_timeout:.0f}s)")
                    if int(elapsed) % 5 == 0 and elapsed > 1:
                        pct = min(elapsed / duration * 100, 99)
                        self.log.emit(f"[INFO] Capturing... {elapsed:.0f}s / {duration}s ({pct:.0f}%)")
                        self.progress_int.emit(int(min(pct * 0.45, 45)))
                    time.sleep(0.5)

                stdout_data = proc.stdout.read().decode("utf-8", errors="replace")
                stderr_data = proc.stderr.read().decode("utf-8", errors="replace")

                if proc.returncode != 0:
                    raise RuntimeError(f"sigrok-cli capture failed (code={proc.returncode}): {stderr_data.strip()}")

                self.log.emit("[INFO] Capture complete")
            except FileNotFoundError:
                raise FileNotFoundError(f"Unable to execute: {sigrok_cli}")

            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"Capture output file not found: {csv_path}")

            file_size = os.path.getsize(csv_path)
            self.log.emit(f"[INFO] CSV file size (dedup): {file_size / 1024:.1f} KB")

            if self._stop_flag:
                return samples

            self.log.emit("[INFO] Parsing capture data...")
            with open(csv_path, "r", encoding="utf-8") as f:
                raw_lines = f.readlines()

            self.log.emit(f"[INFO] Read {len(raw_lines)} lines of data")
            samples = self._parse_dslogic_csv(raw_lines)

            if not samples:
                raise ValueError("No valid period data parsed from DSLogic capture")

            self.log.emit(f"[INFO] DSLogic online acquisition parsed, {len(samples)} period data points")

        return samples

    @staticmethod
    def _find_sigrok_cli():
        import shutil
        path = shutil.which("sigrok-cli")
        if path:
            return path
        common_paths = [
            r"C:\Program Files\sigrok\sigrok-cli\sigrok-cli.exe",
            r"C:\Program Files (x86)\sigrok\sigrok-cli\sigrok-cli.exe",
            r"C:\sigrok\sigrok-cli.exe",
        ]
        for p in common_paths:
            if os.path.isfile(p):
                return p
        return None

    def _analyze_clk_perf(self, samples):
        if not samples:
            raise ValueError("No valid sample data")

        periods = [p for _, p in samples if p > 0]
        if not periods:
            raise ValueError("No valid period data")

        n = len(periods)
        avg_period = statistics.mean(periods)
        avg_freq = 1.0 / avg_period
        min_period = min(periods)
        max_period = max(periods)
        min_freq = 1.0 / max_period
        max_freq = 1.0 / min_period

        period_jitter_pp = (max_period - min_period) * 1e9
        period_std = statistics.pstdev(periods) * 1e9 if n > 1 else 0.0

        c2c_diffs = [abs(periods[i] - periods[i - 1]) for i in range(1, n)]
        c2c_jitter_max = max(c2c_diffs) * 1e9 if c2c_diffs else 0.0
        c2c_jitter_rms = (statistics.mean([d ** 2 for d in c2c_diffs]) ** 0.5) * 1e9 if c2c_diffs else 0.0

        cum_errors = []
        ideal_accum = 0.0
        real_accum = 0.0
        for p in periods:
            ideal_accum += avg_period
            real_accum += p
            cum_errors.append((real_accum - ideal_accum) * 1e9)
        tie_max = max(abs(e) for e in cum_errors) if cum_errors else 0.0

        times = [t for t, _ in samples if _ > 0]
        if n >= 10:
            seg = max(1, n // 10)
            first_freqs = [1.0 / p for p in periods[:seg]]
            last_freqs = [1.0 / p for p in periods[-seg:]]
            freq_first = statistics.mean(first_freqs)
            freq_last = statistics.mean(last_freqs)
            freq_drift_ppm = (freq_last - freq_first) / avg_freq * 1_000_000.0
            total_time = times[-1] - times[0] if len(times) > 1 else 1.0
            freq_drift_ppm_per_s = freq_drift_ppm / total_time if total_time > 0 else 0.0
        else:
            freq_drift_ppm = 0.0
            freq_drift_ppm_per_s = 0.0

        self.log.emit("=" * 60)
        self.log.emit("[PERF] ===== Clock Performance Analysis =====")
        self.log.emit("=" * 60)
        self.log.emit(f"[PERF] Total Periods      = {n}")
        self.log.emit(f"[PERF] Avg Frequency       = {avg_freq:.6f} Hz")
        self.log.emit(f"[PERF] Avg Period          = {avg_period * 1e6:.6f} us")
        self.log.emit("-" * 60)
        self.log.emit(f"[PERF] Min Period          = {min_period * 1e6:.6f} us  ({min_freq:.4f} Hz)")
        self.log.emit(f"[PERF] Max Period          = {max_period * 1e6:.6f} us  ({max_freq:.4f} Hz)")
        self.log.emit("-" * 60)
        self.log.emit(f"[PERF] Period Jitter (P-P) = {period_jitter_pp:.3f} ns")
        self.log.emit(f"[PERF] Period Std Dev      = {period_std:.3f} ns")
        self.log.emit("-" * 60)
        self.log.emit(f"[PERF] Cycle-to-Cycle Max  = {c2c_jitter_max:.3f} ns")
        self.log.emit(f"[PERF] Cycle-to-Cycle RMS  = {c2c_jitter_rms:.3f} ns")
        self.log.emit("-" * 60)
        self.log.emit(f"[PERF] TIE Max (Accum Err) = {tie_max:.3f} ns")
        self.log.emit("-" * 60)
        self.log.emit(f"[PERF] Freq Drift          = {freq_drift_ppm:+.3f} ppm (total)")
        self.log.emit(f"[PERF] Freq Drift Rate     = {freq_drift_ppm_per_s:+.4f} ppm/s")
        self.log.emit("=" * 60)

        total_time = times[-1] - times[0] if len(times) > 1 else sum(periods)

        ble_min_time = self.config.get("ble_min_time", 0.1)
        if total_time >= ble_min_time:
            self.log.emit("")
            self.log.emit("=" * 60)
            self.log.emit("[BLE] ===== Bluetooth Clock Suitability Analysis =====")
            self.log.emit("[BLE] (Ref: Bluetooth Core Spec Vol 6, Part B, 4.2.2)")
            self.log.emit("[BLE] SCA = Clock intrinsic stability (relative to its own average)")
            self.log.emit("=" * 60)
            self.log.emit(f"[BLE] Measured Avg Freq     = {avg_freq:.6f} Hz (as reference)")
            self.log.emit(f"[BLE] Total Measure Time   = {total_time:.3f} s")
            self.log.emit(f"[BLE] Freq Drift           = {freq_drift_ppm:+.3f} ppm")
            self.log.emit("-" * 60)

            ble_windows = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 4.0]
            worst_stability_ppm = abs(freq_drift_ppm)

            self.log.emit("[BLE] Window Stability Analysis (relative to own average):")
            for win in ble_windows:
                n_per_win = int(round(win / avg_period))
                if n_per_win < 1 or n_per_win >= n:
                    continue
                ideal_time = n_per_win * avg_period
                max_err = 0.0
                for i in range(0, n - n_per_win + 1, max(1, (n - n_per_win) // 500)):
                    actual_time = sum(periods[i:i + n_per_win])
                    err_ppm = abs(actual_time - ideal_time) / ideal_time * 1_000_000.0
                    if err_ppm > max_err:
                        max_err = err_ppm
                if max_err > worst_stability_ppm:
                    worst_stability_ppm = max_err
                self.log.emit(f"[BLE]   Window={win*1000:>7.1f} ms  |  Max Deviation={max_err:>8.3f} ppm")

            self.log.emit("-" * 60)
            self.log.emit(f"[BLE] Worst-case Stability = {worst_stability_ppm:.3f} ppm")
            self.log.emit("-" * 60)

            sca_thresholds = [
                (7, 20,  "0-20 ppm"),
                (6, 30,  "21-30 ppm"),
                (5, 50,  "31-50 ppm"),
                (4, 75,  "51-75 ppm"),
                (3, 100, "76-100 ppm"),
                (2, 150, "101-150 ppm"),
                (1, 250, "151-250 ppm"),
                (0, 500, "251-500 ppm"),
            ]

            matched_sca = None
            for sca_val, limit, label in sca_thresholds:
                if worst_stability_ppm <= limit:
                    matched_sca = (sca_val, limit, label)
                    break

            ble_ok = worst_stability_ppm <= 500.0
            ble_sym = "✅" if ble_ok else "❌"
            ble_str = "PASS" if ble_ok else "FAIL"

            self.log.emit(f"[BLE] BLE SCA Compliance (≤ ±500 ppm): {ble_sym} {ble_str}  ({worst_stability_ppm:.3f} ppm)")

            if matched_sca:
                sca_val, limit, label = matched_sca
                self.log.emit(f"[BLE] SCA Field Value      = {sca_val} ({label})")
            else:
                self.log.emit(f"[BLE] SCA Field Value      = N/A (exceeds ±500 ppm, not BLE compliant)")

            self.log.emit("-" * 60)
            self.log.emit("[BLE] SCA Level Reference Table (Bluetooth Core Spec):")
            self.log.emit("[BLE]   SCA=7: 0-20 ppm    (Best, minimum window widening)")
            self.log.emit("[BLE]   SCA=6: 21-30 ppm")
            self.log.emit("[BLE]   SCA=5: 31-50 ppm   (Recommended for Master/Central)")
            self.log.emit("[BLE]   SCA=4: 51-75 ppm")
            self.log.emit("[BLE]   SCA=3: 76-100 ppm")
            self.log.emit("[BLE]   SCA=2: 101-150 ppm")
            self.log.emit("[BLE]   SCA=1: 151-250 ppm")
            self.log.emit("[BLE]   SCA=0: 251-500 ppm (Worst, maximum window widening)")
            self.log.emit("-" * 60)

            if matched_sca:
                sca_val, _, _ = matched_sca
                conn_interval_s = 1.0
                peer_sca_ppm = 50.0
                own_sca_ppm = worst_stability_ppm
                combined_sca = own_sca_ppm + peer_sca_ppm
                window_widening_us = combined_sca * conn_interval_s * 2
                self.log.emit(f"[BLE] Window Widening Estimate (Connection Interval = {conn_interval_s*1000:.0f}ms, Peer SCA = ±{peer_sca_ppm:.0f} ppm):")
                self.log.emit(f"[BLE]   Combined SCA        = ±{combined_sca:.1f} ppm")
                self.log.emit(f"[BLE]   Window Widening     = {window_widening_us:.1f} us")
                self.log.emit(f"[BLE]   (Formula: widening = (masterSCA + slaveSCA) × timeSinceLastAnchor × 2)")

            self.log.emit("=" * 60)
        else:
            self.log.emit(f"[INFO] Data duration {total_time:.2f}s < {ble_min_time:.1f}s, skipping Bluetooth suitability analysis (requires >= {ble_min_time:.1f}s)")

        points = []
        for t, p in samples:
            if p > 0:
                freq = 1.0 / p
                ppm = (freq - avg_freq) / avg_freq * 1_000_000.0
                points.append({"x": t, "freq": freq, "ppm": ppm})

        return {
            "mode": "clk_perf",
            "data": points,
            "summary": {
                "avg_freq": avg_freq,
                "avg_period_us": avg_period * 1e6,
                "min_freq": min_freq,
                "max_freq": max_freq,
                "min_period_us": min_period * 1e6,
                "max_period_us": max_period * 1e6,
                "period_jitter_pp_ns": period_jitter_pp,
                "period_std_ns": period_std,
                "c2c_jitter_max_ns": c2c_jitter_max,
                "c2c_jitter_rms_ns": c2c_jitter_rms,
                "tie_max_ns": tie_max,
                "freq_drift_ppm": freq_drift_ppm,
                "freq_drift_ppm_per_s": freq_drift_ppm_per_s,
            }
        }


class CLKTestUI(OscilloscopeConnectionMixin, VT6002ConnectionMixin, Keysight53230AConnectionMixin, QWidget):
    """
    CLK Test Main UI Component
    Test Items:
      1. cap_freq  — Ctrim vs Frequency
      2. temp_freq — Temperature vs Frequency
      3. clk_perf  — Clock Performance Analysis (CSV import supported)
    """

    TEST_CAP_FREQ = "cap_freq"
    TEST_TEMP_FREQ = "temp_freq"
    TEST_CLK_PERF = "clk_perf"

    def __init__(self, mso64b_top=None, parent=None):
        super().__init__(parent)
        self.init_oscilloscope_connection(mso64b_top)
        self.init_vt6002_connection()
        self.init_counter_connection()
        self.current_test_item = self.TEST_CAP_FREQ

        self._test_thread = None
        self._test_worker = None
        self._start_btn_text = "▷ Start Sequence"

        self.result_data = []
        self.result_mode = None
        self.result_summary = {}
        self.csv_file_path = ""

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self.sync_oscilloscope_from_top()

    # -------------------------------------------------------
    # Styles
    # -------------------------------------------------------
    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)
        self.setStyleSheet("""
            QWidget {
                background-color: #020618;
                color: #c8c8c8;
                border: none;
            }

            QFrame#page {
                background-color: #020618;
            }

            QFrame#panel, QFrame#chart_panel {
                background-color: #0a1428;
                border: 1.5px solid #162040;
                border-radius: 10px;
            }

            QFrame#config_inner_panel {
                background-color: #0b1630;
                border: 1px solid #1e3060;
                border-radius: 8px;
            }

            QLabel#section_title {
                color: #8faad8;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1.5px;
            }

            QLabel#title_label {
                font-size: 18px;
                font-weight: 700;
                color: #e8eeff;
            }

            QLabel#subtitle_label {
                font-size: 12px;
                color: #6878a8;
            }

            QLabel#muted_label {
                color: #4a5a80;
                font-size: 11px;
            }

            QLabel#metric_value_green {
                font-size: 20px;
                font-weight: 700;
                color: #00d39a;
            }
            QLabel#metric_value_blue {
                font-size: 20px;
                font-weight: 700;
                color: #3da8ff;
            }
            QLabel#metric_value_yellow {
                font-size: 20px;
                font-weight: 700;
                color: #ffb84d;
            }
            QLabel#metric_value_purple {
                font-size: 20px;
                font-weight: 700;
                color: #b48aff;
            }
""" + START_BTN_STYLE + """
            QPushButton#connect_btn {
                background-color: #1a3060;
                color: #4a9fff;
                border: 1px solid #2a4a90;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                min-height: 28px;
                padding: 0 10px;
            }
            QPushButton#connect_btn:hover {
                background-color: #1e3a80;
            }

            QPushButton#tool_btn {
                background-color: #0e1e40;
                color: #6898e0;
                border: 1.5px solid #1e3060;
                border-radius: 6px;
                font-size: 12px;
                min-height: 28px;
                padding: 0 10px;
            }
            QPushButton#tool_btn:hover {
                background-color: #162848;
                color: #8abaff;
            }

            QDoubleSpinBox, QSpinBox {
                background-color: #0a1733;
                border: 1.5px solid #1e3060;
                border-radius: 5px;
                padding: 3px 6px;
                color: #c8d8f8;
                font-size: 12px;
            }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 0px; height: 0px; border: none;
            }

            QLineEdit {
                background-color: #0a1733;
                border: 1.5px solid #1e3060;
                border-radius: 5px;
                padding: 3px 8px;
                color: #c8d8f8;
                font-size: 12px;
            }

            QTextEdit {
                background-color: #050d1e;
                border: 1px solid #0e1e40;
                border-radius: 6px;
                color: #8abaff;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                padding: 6px;
            }

            QLabel {
                color: #c8c8c8;
                border: none;
                background: transparent;
            }

            QFrame#left_scroll_content {
                background-color: transparent;
                border: none;
            }
        """ + SCROLL_AREA_STYLE)

    # -------------------------------------------------------
    # Helper components
    # -------------------------------------------------------
    def _create_metric_card(self, title, default_value, value_obj_name="metric_value_green"):
        card = QFrame()
        card.setObjectName("panel")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("muted_label")
        title_lbl.setAlignment(Qt.AlignCenter)

        value_lbl = QLabel(default_value)
        value_lbl.setObjectName(value_obj_name)
        value_lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)
        return card, title_lbl, value_lbl

    def _create_instrument_card(self, name, desc,
                                combo_attr, search_btn_attr,
                                connect_btn_attr, disconnect_btn_attr,
                                status_attr):
        card = QFrame()
        card.setObjectName("config_inner_panel")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #4a6a98; font-size: 11px; border: none;")
        desc_lbl.setWordWrap(True)

        title_box.addWidget(name_lbl)
        title_box.addWidget(desc_lbl)

        status_lbl = QLabel("Not Connected")
        status_lbl.setStyleSheet("color: #ff5a7a; font-weight: 600; border: none;")
        status_lbl.setWordWrap(True)
        setattr(self, status_attr, status_lbl)

        btn_connect = QPushButton()
        update_connect_button_state(btn_connect, connected=False)
        btn_connect.setFixedWidth(120)
        setattr(self, connect_btn_attr, btn_connect)
        setattr(self, disconnect_btn_attr, btn_connect)

        top_row.addLayout(title_box, 1)
        top_row.addWidget(btn_connect, 0, Qt.AlignTop)

        select_row = QHBoxLayout()
        select_row.setSpacing(6)

        combo = DarkComboBox(bg="#0a1733", border="#24365e")
        combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(10)
        combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

        search_btn = SpinningSearchButton()
        search_btn.setFixedWidth(44)
        setattr(self, combo_attr, combo)
        setattr(self, search_btn_attr, search_btn)

        select_row.addWidget(combo, 1)
        select_row.addWidget(search_btn)

        layout.addLayout(top_row)
        layout.addWidget(status_lbl)
        layout.addLayout(select_row)
        return card

    def _create_hline(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #1a2a4a; max-height: 1px;")
        return line

    # -------------------------------------------------------
    # Layout
    # -------------------------------------------------------
    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 6, 8, 8)
        root_layout.setSpacing(8)

        self.page = QFrame()
        self.page.setObjectName("page")
        page_layout = QVBoxLayout(self.page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        title_text = "⏱ CLK Test"
        if DEBUG_MOCK:
            title_text += "  🟡 MOCK MODE"
        title_label = QLabel(title_text)
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("border: none")

        subtitle_label = QLabel("Clock test range: typical 32kHz ~ 48MHz. Support cap sweep, temperature drift and clock performance analysis.")
        subtitle_label.setObjectName("subtitle_label")
        subtitle_label.setStyleSheet("border: none")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        page_layout.addLayout(header_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        left_wrapper = QVBoxLayout()
        left_wrapper.setContentsMargins(0, 0, 0, 0)
        left_wrapper.setSpacing(8)

        # ---- Left scroll area ----
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.left_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.left_scroll.setMinimumWidth(320)
        self.left_scroll.setMaximumWidth(320)

        left_content = QFrame()
        left_content.setObjectName("left_scroll_content")
        left_content.setMinimumWidth(298)
        left_content.setMaximumWidth(298)
        left_content.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        left_col = QVBoxLayout(left_content)
        left_col.setContentsMargins(0, 0, 6, 0)
        left_col.setSpacing(12)

        # ---- TEST ITEM SELECT ----
        test_select_panel = QFrame()
        test_select_panel.setObjectName("panel")
        test_select_layout = QVBoxLayout(test_select_panel)
        test_select_layout.setContentsMargins(12, 12, 12, 12)
        test_select_layout.setSpacing(8)

        test_select_title = QLabel("Test Item")
        test_select_title.setObjectName("section_title")
        test_select_layout.addWidget(test_select_title)

        self.test_item_combo = DarkComboBox()
        self.test_item_combo.addItem("Ctrim vs Frequency", self.TEST_CAP_FREQ)
        self.test_item_combo.addItem("Temperature vs Frequency", self.TEST_TEMP_FREQ)
        self.test_item_combo.addItem("Clock Performance Analysis", self.TEST_CLK_PERF)
        test_select_layout.addWidget(self.test_item_combo)

        left_col.addWidget(test_select_panel)

        # ---- DATA SOURCE (Test Item 3 only) ----
        self.clk_data_source_panel = QFrame()
        self.clk_data_source_panel.setObjectName("panel")
        ds_layout = QVBoxLayout(self.clk_data_source_panel)
        ds_layout.setContentsMargins(12, 10, 12, 10)
        ds_layout.setSpacing(6)

        ds_title = QLabel("Data Source")
        ds_title.setObjectName("section_title")
        ds_layout.addWidget(ds_title)

        ds_row = QHBoxLayout()
        ds_row.addWidget(QLabel("Data Source"))
        self.clk_source_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        self.clk_source_combo.addItems(["MSO64B", "DSLogic", "Import CSV"])
        ds_row.addWidget(self.clk_source_combo, 1)
        ds_layout.addLayout(ds_row)

        self.clk_data_source_panel.setVisible(False)
        left_col.addWidget(self.clk_data_source_panel)

        # ---- INSTRUMENTS ----
        instruments_panel = QFrame()
        instruments_panel.setObjectName("panel")
        instruments_layout = QVBoxLayout(instruments_panel)
        instruments_layout.setContentsMargins(12, 12, 12, 12)
        instruments_layout.setSpacing(10)

        instruments_title = QLabel("Instrument Connection")
        instruments_title.setObjectName("section_title")
        instruments_layout.addWidget(instruments_title)

        # Frequency instrument selection
        self.freq_instr_frame = QFrame()
        self.freq_instr_frame.setObjectName("config_inner_panel")
        freq_instr_layout = QVBoxLayout(self.freq_instr_frame)
        freq_instr_layout.setContentsMargins(10, 10, 10, 10)
        freq_instr_layout.setSpacing(6)

        freq_type_row = QHBoxLayout()
        freq_type_row.addWidget(QLabel("Frequency Instrument"))
        self.freq_instr_type_combo = DarkComboBox()
        self.freq_instr_type_combo.addItems(["MSO64B", "53230A", "DigitMultimeter"])
        freq_type_row.addWidget(self.freq_instr_type_combo, 1)
        freq_instr_layout.addLayout(freq_type_row)
        instruments_layout.addWidget(self.freq_instr_frame)

        # MSO64B
        self.mso64b_card = QFrame()
        self.mso64b_card.setObjectName("config_inner_panel")
        mso64b_card_layout = QVBoxLayout(self.mso64b_card)
        mso64b_card_layout.setContentsMargins(10, 10, 10, 10)
        mso64b_card_layout.setSpacing(6)
        mso64b_title = QLabel("MSO64B Oscilloscope")
        mso64b_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        mso64b_card_layout.addWidget(mso64b_title)

        self.build_oscilloscope_connection_widgets(mso64b_card_layout)
        instruments_layout.addWidget(self.mso64b_card)

        mso_ch_row = QHBoxLayout()
        mso_ch_row.setSpacing(6)
        mso_ch_label = QLabel("Measurement Channel")
        mso_ch_label.setStyleSheet("color: #8faad8; font-size: 12px; border: none;")
        self.mso64b_channel_combo = DarkComboBox()
        self.mso64b_channel_combo.addItems(["CH1", "CH2", "CH3", "CH4"])
        self.mso64b_channel_combo.setCurrentIndex(1)
        mso_ch_row.addWidget(mso_ch_label)
        mso_ch_row.addWidget(self.mso64b_channel_combo, 1)
        mso64b_card_layout.addLayout(mso_ch_row)

        # 53230A
        self.counter_card = QFrame()
        self.counter_card.setObjectName("config_inner_panel")
        counter_card_layout = QVBoxLayout(self.counter_card)
        counter_card_layout.setContentsMargins(10, 10, 10, 10)
        counter_card_layout.setSpacing(6)
        counter_title_row = QHBoxLayout()
        counter_title_row.setSpacing(8)
        counter_title_row.setContentsMargins(0, 0, 0, 0)
        counter_title = QLabel("53230A Counter")
        counter_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        counter_title_row.addWidget(counter_title, 0, Qt.AlignVCenter)
        counter_title_row.addStretch(1)
        counter_card_layout.addLayout(counter_title_row)
        self.build_counter_connection_widgets(counter_card_layout, title_row=counter_title_row)
        instruments_layout.addWidget(self.counter_card)

        # DigitMultimeter
        self.dmm_card = self._create_instrument_card(
            "DigitMultimeter",
            "Digital Multimeter (Frequency Capable)",
            "dmm_combo",
            "dmm_search_btn",
            "dmm_connect_btn",
            "dmm_disconnect_btn",
            "dmm_status"
        )
        instruments_layout.addWidget(self.dmm_card)

        # Temperature chamber
        self.vt6002_card = QFrame()
        self.vt6002_card.setObjectName("config_inner_panel")
        vt6002_card_layout = QVBoxLayout(self.vt6002_card)
        vt6002_card_layout.setContentsMargins(10, 10, 10, 10)
        vt6002_card_layout.setSpacing(6)
        vt6002_title = QLabel("VT6002 Chamber")
        vt6002_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        vt6002_card_layout.addWidget(vt6002_title)
        self.build_vt6002_connection_widgets(vt6002_card_layout)
        instruments_layout.addWidget(self.vt6002_card)

        left_col.addWidget(instruments_panel)

        # ---- PARAMETERS ----
        params_panel = QFrame()
        params_panel.setObjectName("panel")
        params_layout = QVBoxLayout(params_panel)
        params_layout.setContentsMargins(12, 12, 12, 12)
        params_layout.setSpacing(8)

        self.params_title = QLabel("Parameters")
        self.params_title.setObjectName("section_title")
        params_layout.addWidget(self.params_title)

        self.params_mode_label = QLabel("")
        self.params_mode_label.setStyleSheet("color: #7e96bf; font-size: 11px; font-weight: 700;")
        params_layout.addWidget(self.params_mode_label)

        # -- Test Item 1 parameters --
        self.cap_params_frame = QFrame()
        self.cap_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        cap_layout = QGridLayout(self.cap_params_frame)
        cap_layout.setContentsMargins(0, 0, 0, 0)
        cap_layout.setHorizontalSpacing(6)
        cap_layout.setVerticalSpacing(6)

        cap_iic_frame = QFrame()
        cap_iic_frame.setObjectName("config_inner_panel")
        cap_iic_layout = QGridLayout(cap_iic_frame)
        cap_iic_layout.setContentsMargins(10, 10, 10, 10)
        cap_iic_layout.setHorizontalSpacing(6)
        cap_iic_layout.setVerticalSpacing(6)

        cap_iic_layout.addWidget(QLabel("IIC Device Address"), 0, 0)
        cap_iic_layout.addWidget(QLabel("REG Address"), 0, 1)
        self.iic_device_addr = QLineEdit("0x1A")
        self.iic_reg_addr = QLineEdit("0xD3")
        cap_iic_layout.addWidget(self.iic_device_addr, 1, 0)
        cap_iic_layout.addWidget(self.iic_reg_addr, 1, 1)

        cap_iic_layout.addWidget(QLabel("Width Flag"), 2, 0)
        cap_iic_layout.addWidget(QLabel("MSB"), 2, 1)
        self.iic_width_flag_combo = DarkComboBox()
        self.iic_width_flag_combo.addItem("BIT_8  (8-bit addr, 16-bit data)", 8)
        self.iic_width_flag_combo.addItem("BIT_10 (10-bit addr, 16-bit data)", 10)
        self.iic_width_flag_combo.addItem("BIT_32 (32-bit addr, 32-bit data)", 32)
        self.iic_width_flag_combo.setCurrentIndex(1)
        self.iic_msb = QSpinBox()
        self.iic_msb.setRange(0, 31)
        self.iic_msb.setValue(8)
        cap_iic_layout.addWidget(self.iic_width_flag_combo, 3, 0)
        cap_iic_layout.addWidget(self.iic_msb, 3, 1)

        cap_iic_layout.addWidget(QLabel("LSB"), 4, 0)
        self.iic_lsb = QSpinBox()
        self.iic_lsb.setRange(0, 31)
        self.iic_lsb.setValue(0)
        cap_iic_layout.addWidget(self.iic_lsb, 5, 0)

        cap_layout.addWidget(cap_iic_frame, 0, 0, 1, 3)

        cap_layout.addWidget(QLabel("Register Min"), 1, 0)
        cap_layout.addWidget(QLabel("Register Max"), 1, 1)
        cap_layout.addWidget(QLabel("Step"), 1, 2)

        self.reg_min = QSpinBox()
        self.reg_min.setRange(0, 511)
        self.reg_min.setValue(0)

        self.reg_max = QSpinBox()
        self.reg_max.setRange(0, 511)
        self.reg_max.setValue(511)

        self.reg_step = QSpinBox()
        self.reg_step.setRange(1, 1024)
        self.reg_step.setValue(1)

        cap_layout.addWidget(self.reg_min, 2, 0)
        cap_layout.addWidget(self.reg_max, 2, 1)
        cap_layout.addWidget(self.reg_step, 2, 2)

        self.iic_msb.valueChanged.connect(self._update_reg_range)
        self.iic_lsb.valueChanged.connect(self._update_reg_range)

        # -- Test Item 2 parameters --
        self.temp_params_frame = QFrame()
        self.temp_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        temp_layout = QGridLayout(self.temp_params_frame)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        temp_layout.setHorizontalSpacing(6)
        temp_layout.setVerticalSpacing(6)

        temp_layout.addWidget(QLabel("Start Temp (°C)"), 0, 0)
        temp_layout.addWidget(QLabel("Stop Temp (°C)"), 0, 1)
        temp_layout.addWidget(QLabel("Step Temp (°C)"), 0, 2)

        self.temp_start = QDoubleSpinBox()
        self.temp_start.setRange(-80.0, 180.0)
        self.temp_start.setValue(-40.0)
        self.temp_start.setSingleStep(1.0)
        self.temp_start.setDecimals(1)

        self.temp_end = QDoubleSpinBox()
        self.temp_end.setRange(-80.0, 180.0)
        self.temp_end.setValue(85.0)
        self.temp_end.setSingleStep(1.0)
        self.temp_end.setDecimals(1)

        self.temp_step = QDoubleSpinBox()
        self.temp_step.setRange(0.1, 100.0)
        self.temp_step.setValue(5.0)
        self.temp_step.setSingleStep(1.0)
        self.temp_step.setDecimals(1)

        temp_layout.addWidget(self.temp_start, 1, 0)
        temp_layout.addWidget(self.temp_end, 1, 1)
        temp_layout.addWidget(self.temp_step, 1, 2)

        temp_layout.addWidget(QLabel("Soak Time (s)"), 2, 0)
        temp_layout.addWidget(QLabel("Stable Tolerance (°C)"), 2, 1)
        self.temp_soak_time = QSpinBox()
        self.temp_soak_time.setRange(0, 3600)
        self.temp_soak_time.setValue(180)
        self.temp_soak_time.setSingleStep(30)
        self.temp_stable_tolerance = QDoubleSpinBox()
        self.temp_stable_tolerance.setRange(0.1, 5.0)
        self.temp_stable_tolerance.setValue(0.5)
        self.temp_stable_tolerance.setSingleStep(0.1)
        self.temp_stable_tolerance.setDecimals(1)
        temp_layout.addWidget(self.temp_soak_time, 3, 0)
        temp_layout.addWidget(self.temp_stable_tolerance, 3, 1)

        # -- Test Item 3 parameters --
        self.clk_params_frame = QFrame()
        self.clk_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        clk_layout = QVBoxLayout(self.clk_params_frame)
        clk_layout.setContentsMargins(0, 0, 0, 0)
        clk_layout.setSpacing(6)

        self.clk_online_params_frame = QFrame()
        self.clk_online_params_frame.setObjectName("config_inner_panel")
        clk_online_layout = QGridLayout(self.clk_online_params_frame)
        clk_online_layout.setContentsMargins(10, 10, 10, 10)
        clk_online_layout.setHorizontalSpacing(6)
        clk_online_layout.setVerticalSpacing(6)

        clk_online_layout.addWidget(QLabel("Sample Rate (MHz)"), 0, 0)
        clk_online_layout.addWidget(QLabel("Measure Duration (s)"), 0, 1)

        self.clk_sample_rate = QDoubleSpinBox()
        self.clk_sample_rate.setRange(0.001, 10000.0)
        self.clk_sample_rate.setValue(100.0)
        self.clk_sample_rate.setSingleStep(10.0)
        self.clk_sample_rate.setDecimals(3)

        self.clk_duration = QDoubleSpinBox()
        self.clk_duration.setRange(0.1, 3600.0)
        self.clk_duration.setValue(10.0)
        self.clk_duration.setSingleStep(1.0)
        self.clk_duration.setDecimals(1)

        clk_online_layout.addWidget(self.clk_sample_rate, 1, 0)
        clk_online_layout.addWidget(self.clk_duration, 1, 1)
        clk_layout.addWidget(self.clk_online_params_frame)

        self.clk_csv_frame = QFrame()
        self.clk_csv_frame.setObjectName("config_inner_panel")
        csv_row_layout = QHBoxLayout(self.clk_csv_frame)
        csv_row_layout.setContentsMargins(8, 8, 8, 8)
        csv_row_layout.setSpacing(8)
        self.csv_path_label = QLabel("No file selected")
        self.csv_path_label.setStyleSheet("color: #4a6a98; font-size: 11px; border: none;")
        self.csv_path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.import_csv_btn = QPushButton("Import CSV")
        self.import_csv_btn.setObjectName("tool_btn")
        csv_row_layout.addWidget(self.csv_path_label, 1)
        csv_row_layout.addWidget(self.import_csv_btn)
        self.clk_csv_frame.setVisible(False)
        clk_layout.addWidget(self.clk_csv_frame)

        clk_chart_frame = QFrame()
        clk_chart_frame.setObjectName("config_inner_panel")
        clk_chart_layout = QVBoxLayout(clk_chart_frame)
        clk_chart_layout.setContentsMargins(10, 10, 10, 10)
        clk_chart_layout.setSpacing(6)

        chart_type_row = QHBoxLayout()
        chart_type_row.addWidget(QLabel("Chart Type"))
        self.clk_chart_type_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        self.clk_chart_type_combo.addItem("Frequency vs Time", "freq_vs_time")
        self.clk_chart_type_combo.addItem("Period vs Time", "period_vs_time")
        self.clk_chart_type_combo.addItem("Period Histogram", "period_histogram")
        self.clk_chart_type_combo.addItem("N-Cycle Timing Error", "n_cycle_tie")
        self.clk_chart_type_combo.addItem("Abs Window vs CLK Error", "abs_window_err")
        self.clk_chart_type_combo.addItem("Time Domain Analysis", "time_domain")
        chart_type_row.addWidget(self.clk_chart_type_combo, 1)
        clk_chart_layout.addLayout(chart_type_row)

        self.clk_n_cycle_frame = QFrame()
        self.clk_n_cycle_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        n_cycle_row = QHBoxLayout(self.clk_n_cycle_frame)
        n_cycle_row.setContentsMargins(0, 0, 0, 0)
        n_cycle_row.addWidget(QLabel("N (cycles)"))
        self.clk_n_cycle_spin = QSpinBox()
        self.clk_n_cycle_spin.setRange(1, 100000)
        self.clk_n_cycle_spin.setValue(100)
        self.clk_n_cycle_spin.setSingleStep(10)
        n_cycle_row.addWidget(self.clk_n_cycle_spin, 1)
        self.clk_n_cycle_frame.setVisible(False)
        clk_chart_layout.addWidget(self.clk_n_cycle_frame)

        self.clk_abs_window_frame = QFrame()
        self.clk_abs_window_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        abs_win_row = QHBoxLayout(self.clk_abs_window_frame)
        abs_win_row.setContentsMargins(0, 0, 0, 0)
        abs_win_row.addWidget(QLabel("Abs Window (ms)"))
        self.clk_abs_window_spin = QDoubleSpinBox()
        self.clk_abs_window_spin.setRange(0.01, 3600000.0)
        self.clk_abs_window_spin.setValue(1000.0)
        self.clk_abs_window_spin.setSingleStep(100.0)
        self.clk_abs_window_spin.setDecimals(2)
        abs_win_row.addWidget(self.clk_abs_window_spin, 1)
        self.clk_abs_window_frame.setVisible(False)
        clk_chart_layout.addWidget(self.clk_abs_window_frame)

        clk_layout.addWidget(clk_chart_frame)

        clk_ble_frame = QFrame()
        clk_ble_frame.setObjectName("config_inner_panel")
        clk_ble_layout = QHBoxLayout(clk_ble_frame)
        clk_ble_layout.setContentsMargins(10, 10, 10, 10)
        clk_ble_layout.setSpacing(6)
        clk_ble_layout.addWidget(QLabel("BLE Analysis Min Time (s)"))
        self.clk_ble_min_time = QDoubleSpinBox()
        self.clk_ble_min_time.setRange(0.1, 3600.0)
        self.clk_ble_min_time.setValue(5.0)
        self.clk_ble_min_time.setSingleStep(1.0)
        self.clk_ble_min_time.setDecimals(1)
        clk_ble_layout.addWidget(self.clk_ble_min_time, 1)
        clk_layout.addWidget(clk_ble_frame)

        params_layout.addWidget(self.cap_params_frame)
        params_layout.addWidget(self.temp_params_frame)
        params_layout.addWidget(self.clk_params_frame)

        left_col.addWidget(params_panel)

        left_col.addStretch()

        self.left_scroll.setWidget(left_content)
        left_wrapper.addWidget(self.left_scroll, 1)

        self.start_test_btn = QPushButton("▷ Start Sequence")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_wrapper.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("■ Stop")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.hide()

        # ---- Right result area ----
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(8)

        self.top_card1, self.top_title1, self.top_value1 = self._create_metric_card(
            "DEFAULT FREQ", "--- Hz", "metric_value_green"
        )
        self.top_card2, self.top_title2, self.top_value2 = self._create_metric_card(
            "MIN FREQ", "--- Hz", "metric_value_blue"
        )
        self.top_card3, self.top_title3, self.top_value3 = self._create_metric_card(
            "MAX FREQ", "--- Hz", "metric_value_yellow"
        )
        self.top_card4, self.top_title4, self.top_value4 = self._create_metric_card(
            "STEP FREQ", "---", "metric_value_purple"
        )
        self.top_card5, self.top_title5, self.top_value5 = self._create_metric_card(
            "LINEARITY", "---", "metric_value_green"
        )

        metrics_layout.addWidget(self.top_card1)
        metrics_layout.addWidget(self.top_card2)
        metrics_layout.addWidget(self.top_card3)
        metrics_layout.addWidget(self.top_card4)
        metrics_layout.addWidget(self.top_card5)
        right_col.addLayout(metrics_layout)

        chart_panel = QFrame()
        chart_panel.setObjectName("chart_panel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(14, 14, 14, 14)
        chart_layout.setSpacing(10)

        chart_top = QHBoxLayout()
        self.chart_title = QLabel("Result")
        self.chart_title.setObjectName("section_title")
        self.export_result_btn = QPushButton("Export Result")
        self.export_result_btn.setObjectName("tool_btn")
        chart_top.addWidget(self.chart_title)
        chart_top.addStretch()
        chart_top.addWidget(self.export_result_btn)
        chart_layout.addLayout(chart_top)

        self.plot_widget = pg.PlotWidget()
        self._setup_chart_plot()
        chart_layout.addWidget(self.plot_widget, 1)

        self.execution_logs = ExecutionLogsFrame(title="TEST LOG", show_progress=True)
        self.log_text = self.execution_logs.log_edit
        self.progress_bar = self.execution_logs.progress_bar
        self.progress_text_label = self.execution_logs.progress_text_label
        self.clear_log_btn = self.execution_logs.clear_log_btn

        right_col.addWidget(chart_panel, 3)
        right_col.addWidget(self.execution_logs, 2)

        body_layout.addLayout(left_wrapper, 0)
        body_layout.addLayout(right_col, 1)

        page_layout.addLayout(body_layout, 1)
        root_layout.addWidget(self.page, 1)

    # -------------------------------------------------------
    # Chart setup
    # -------------------------------------------------------
    def _setup_chart_plot(self):
        self.plot_widget.setBackground("#071127")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)

        axis_pen = pg.mkPen(color="#2a4272", width=1)
        text_color = "#8eb0e3"

        bottom_axis = self.plot_widget.getPlotItem().getAxis("bottom")
        bottom_axis.setPen(axis_pen)
        bottom_axis.setTextPen(pg.mkPen(text_color))
        bottom_axis.setStyle(tickLength=-5)

        left_axis = self.plot_widget.getPlotItem().getAxis("left")
        left_axis.setPen(axis_pen)
        left_axis.setTextPen(pg.mkPen(text_color))
        left_axis.setStyle(tickLength=-5)

        self.plot_widget.setLabel("bottom", "X", color=text_color)
        self.plot_widget.setLabel("left", "Frequency (Hz)", color=text_color)

        vb = self.plot_widget.getPlotItem().getViewBox()
        vb.setMouseEnabled(x=True, y=True)

        self.plot_curve = None
        self._rt_x_data = []
        self._rt_y_data = []

    def _clear_chart(self):
        self.plot_widget.clear()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.15)
        self.plot_curve = None
        self._rt_x_data = []
        self._rt_y_data = []

    def _update_chart_labels(self, x_label, y_label):
        text_color = "#8eb0e3"
        self.plot_widget.setLabel("bottom", x_label, color=text_color)
        self.plot_widget.setLabel("left", y_label, color=text_color)

    # -------------------------------------------------------
    # Initialization
    # -------------------------------------------------------
    def _init_ui_elements(self):
        self.test_item_combo.currentIndexChanged.connect(self._on_test_item_combo_changed)

        self.bind_oscilloscope_signals()
        self.bind_vt6002_signals()
        self.bind_counter_signals()

        self.dmm_search_btn.clicked.connect(self._search_dmm)
        self.dmm_connect_btn.clicked.connect(self._toggle_dmm)

        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._stop_test)
        self.export_result_btn.clicked.connect(self.export_result)

        self.import_csv_btn.clicked.connect(self._import_csv)
        self.clk_source_combo.currentIndexChanged.connect(self._on_clk_source_changed)
        self.clk_chart_type_combo.currentIndexChanged.connect(self._on_clk_chart_type_changed)
        self.clk_n_cycle_spin.valueChanged.connect(self._on_clk_chart_param_changed)
        self.clk_abs_window_spin.valueChanged.connect(self._on_clk_chart_param_changed)
        self.freq_instr_type_combo.currentIndexChanged.connect(self._update_instrument_visibility)

        self._set_test_item(self.TEST_CAP_FREQ)
        self._on_clk_source_changed(self.clk_source_combo.currentIndex())
        self._search_dmm()

        if DEBUG_MOCK:
            self._append_log("[MOCK] ========== MOCK DEBUG MODE ACTIVE ==========")
            self._append_log("[MOCK] All instruments use simulated data, no real hardware required.")

    # -------------------------------------------------------
    # Test item switching
    # -------------------------------------------------------
    def _on_test_item_combo_changed(self, index):
        test_item = self.test_item_combo.currentData()
        self._set_test_item(test_item)

    def _set_test_item(self, test_item):
        self.current_test_item = test_item

        idx = self.test_item_combo.findData(test_item)
        if idx >= 0 and self.test_item_combo.currentIndex() != idx:
            self.test_item_combo.setCurrentIndex(idx)

        if test_item == self.TEST_CAP_FREQ:
            self.params_mode_label.setText("CAPACITOR CODE / REGISTER SWEEP")
            self.cap_params_frame.show()
            self.temp_params_frame.hide()
            self.clk_params_frame.hide()
            self.clk_data_source_panel.hide()
            self.freq_instr_frame.show()
            self.start_test_btn.setText("▷ Start Sequence")
            self._start_btn_text = "▷ Start Sequence"
            self.chart_title.setText("Capacitance vs Frequency Result")
            self._update_chart_labels("Register Value / Cap Code", "Frequency (Hz)")
            self._update_top_card_titles("DEFAULT FREQ", "MIN FREQ", "MAX FREQ", "STEP FREQ", "LINEARITY")

        elif test_item == self.TEST_TEMP_FREQ:
            self.params_mode_label.setText("TEMPERATURE SWEEP")
            self.cap_params_frame.hide()
            self.temp_params_frame.show()
            self.clk_params_frame.hide()
            self.clk_data_source_panel.hide()
            self.freq_instr_frame.show()
            self.start_test_btn.setText("▷ Start Sequence")
            self._start_btn_text = "▷ Start Sequence"
            self.chart_title.setText("Temperature vs Frequency Result")
            self._update_chart_labels("Temperature (°C)", "Frequency (Hz)")
            self._update_top_card_titles("25℃ FREQ", "MIN FREQ", "MAX FREQ", "PER ℃ FREQ", "LINEARITY")

        elif test_item == self.TEST_CLK_PERF:
            self.params_mode_label.setText("CLOCK PERFORMANCE ANALYSIS")
            self.cap_params_frame.hide()
            self.temp_params_frame.hide()
            self.clk_params_frame.show()
            self.clk_data_source_panel.show()
            self.freq_instr_frame.hide()
            self.start_test_btn.setText("▷ Start Sequence")
            self._start_btn_text = "▷ Start Sequence"
            self.chart_title.setText("Clock Performance Analysis Result")
            self._update_chart_labels("Time (s)", "Frequency (Hz)")
            self._update_top_card_titles("AVG FREQ (PERIOD)", "MIN PERIOD", "MAX PERIOD", "PERIOD JITTER (P-P)", "FREQ DRIFT")

        self._update_instrument_visibility()

    def _update_instrument_visibility(self):
        freq_type = self.freq_instr_type_combo.currentText()

        mso64b_visible = freq_type == "MSO64B" or self.current_test_item == self.TEST_CLK_PERF
        self.mso64b_card.setVisible(mso64b_visible)
        self.counter_card.setVisible(freq_type == "53230A")
        self.dmm_card.setVisible(freq_type == "DigitMultimeter")
        self.vt6002_card.setVisible(self.current_test_item == self.TEST_TEMP_FREQ)

        if self.current_test_item == self.TEST_CLK_PERF:
            clk_source = self.clk_source_combo.currentText()
            self.mso64b_card.setVisible(clk_source == "MSO64B")
            self.counter_card.hide()
            self.dmm_card.hide()
            self.vt6002_card.hide()

    # -------------------------------------------------------
    # Instrument search
    def _search_dmm(self):
        if DEBUG_MOCK:
            self.dmm_combo.clear()
            self.dmm_combo.addItem("[MOCK] USB0::DMM::INSTR")
            self._set_status_label(self.dmm_status, "Available (Mock)", "ok")
            return
        self.dmm_combo.clear()
        self.dmm_combo.addItem("USB0::DMM::INSTR")
        self._set_status_label(self.dmm_status, "Available", "ok")

    def _toggle_dmm(self):
        if self.dmm_connect_btn.text() == "Disconnect":
            self._disconnect_dmm()
        else:
            self._connect_dmm()

    def _connect_dmm(self):
        self._set_status_label(self.dmm_status, f"Connected: {self.dmm_combo.currentText()}", "ok")
        self._set_btn_connected(self.dmm_connect_btn)

    def _disconnect_dmm(self):
        self._set_status_label(self.dmm_status, "Disconnected", "err")
        self._set_btn_disconnected(self.dmm_connect_btn)

    def _set_status_label(self, label, text, state):
        label.setText(text)
        color_map = {"ok": "#18a067", "warn": "#d4a514", "err": "#d14b72"}
        color = color_map.get(state, "#c8c8c8")
        label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _set_btn_connected(self, btn):
        update_connect_button_state(btn, connected=True)
        btn.setEnabled(True)

    def _set_btn_disconnected(self, btn):
        update_connect_button_state(btn, connected=False)
        btn.setEnabled(True)

    def _append_log(self, text):
        self.execution_logs.append_log(text)

    def append_log(self, text):
        self.execution_logs.append_log(text)

    def set_progress(self, value: int):
        self.execution_logs.set_progress(value)

    def _format_freq(self, value):
        if value is None:
            return "--- Hz"
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:.6f} MHz"
        if abs(value) >= 1_000:
            return f"{value / 1_000:.6f} kHz"
        return f"{value:.6f} Hz"

    def _current_freq_instrument(self):
        return self.freq_instr_type_combo.currentText()

    def _update_reg_range(self):
        msb = self.iic_msb.value()
        lsb = self.iic_lsb.value()
        if msb < lsb:
            self.iic_msb.setValue(lsb)
            msb = lsb
        bit_width = msb - lsb + 1
        max_code = (1 << bit_width) - 1
        old_max_range = self.reg_max.maximum()
        old_max_val = self.reg_max.value()
        self.reg_min.setRange(0, max_code)
        self.reg_max.setRange(0, max_code)
        if self.reg_min.value() > max_code:
            self.reg_min.setValue(0)
        if old_max_val >= old_max_range or old_max_val > max_code:
            self.reg_max.setValue(max_code)

    def _validate_freq_instrument(self, test_label):
        freq_instrument = self._current_freq_instrument()
        if freq_instrument == "MSO64B":
            if not self.scope_connected:
                raise ValueError(f"{test_label} requires MSO64B connection for frequency measurement")
        elif freq_instrument == "53230A":
            if not getattr(self, "counter_connected", False):
                raise ValueError(f"{test_label} requires 53230A frequency counter connection")
        elif freq_instrument == "DigitMultimeter":
            raise ValueError("DigitMultimeter frequency measurement is not implemented yet")
        else:
            raise ValueError(f"Unsupported frequency instrument: {freq_instrument}")

    def _validate_before_test(self):
        if DEBUG_MOCK:
            self._append_log("[MOCK] Skipping instrument validation (mock mode)")
            return

        if self.current_test_item == self.TEST_CAP_FREQ:
            self._validate_freq_instrument("Test Item 1")
            if self.reg_min.value() > self.reg_max.value():
                raise ValueError("Register Min must not exceed Register Max")

        elif self.current_test_item == self.TEST_TEMP_FREQ:
            if not self.is_vt6002_connected:
                raise ValueError("Test Item 2 requires VT6002 chamber connection")
            self._validate_freq_instrument("Test Item 2")
            if self.temp_step.value() <= 0:
                raise ValueError("Temperature step must be greater than 0")

        elif self.current_test_item == self.TEST_CLK_PERF:
            clk_source = self.clk_source_combo.currentText()
            if clk_source == "MSO64B":
                if not self.scope_connected:
                    raise ValueError("MSO64B mode requires MSO64B connection")
            elif clk_source == "DSLogic":
                pass
            elif clk_source == "Import CSV":
                if not self.csv_file_path:
                    raise ValueError("Please select a CSV file")

    def _build_test_config(self):
        mso_ch_text = self.mso64b_channel_combo.currentText()
        mso_channel = int(mso_ch_text.replace("CH", "")) if mso_ch_text else 2
        cfg = {
            "freq_instrument": self._current_freq_instrument(),
            "temp_instrument": "VT6002",
            "iic_device_addr": self.iic_device_addr.text().strip(),
            "iic_reg_addr": self.iic_reg_addr.text().strip(),
            "iic_width_flag": self.iic_width_flag_combo.currentData(),
            "iic_msb": self.iic_msb.value(),
            "iic_lsb": self.iic_lsb.value(),
            "mso_channel": mso_channel,
            "reg_min": self.reg_min.value(),
            "reg_max": self.reg_max.value(),
            "reg_step": self.reg_step.value(),
            "temp_start": self.temp_start.value(),
            "temp_end": self.temp_end.value(),
            "temp_step": self.temp_step.value(),
            "temp_soak_time": self.temp_soak_time.value(),
            "temp_stable_tolerance": self.temp_stable_tolerance.value(),
            "clk_duration": self.clk_duration.value(),
            "clk_sample_rate": self.clk_sample_rate.value(),
            "clk_source": self.clk_source_combo.currentText(),
            "csv_path": self.csv_file_path,
            "ble_min_time": self.clk_ble_min_time.value(),
        }
        return cfg

    def _reset_metrics(self):
        self.top_value1.setText("---")
        self.top_value2.setText("---")
        self.top_value3.setText("---")
        self.top_value4.setText("---")
        self.top_value5.setText("---")

    def _update_top_card_titles(self, t1, t2, t3, t4, t5):
        self.top_title1.setText(t1)
        self.top_title2.setText(t2)
        self.top_title3.setText(t3)
        self.top_title4.setText(t4)
        self.top_title5.setText(t5)
        self._reset_metrics()

    # -------------------------------------------------------
    # Test control
    # -------------------------------------------------------
    def _on_start_or_stop(self):
        if self._test_thread is not None:
            self._stop_test()
        else:
            self._start_test()

    def _start_test(self):
        if self._test_thread is not None:
            QMessageBox.information(self, "Info", "Test is already in progress")
            return

        try:
            self._validate_before_test()
            config = self._build_test_config()
        except Exception as e:
            QMessageBox.warning(self, "Start Test Failed", str(e))
            return

        self.result_data = []
        self.result_mode = self.current_test_item
        self._clear_chart()
        self._reset_metrics()

        if self.current_test_item == self.TEST_CAP_FREQ:
            self._start_cap_freq_test(config)
        elif self.current_test_item == self.TEST_TEMP_FREQ:
            self._start_temp_freq_test(config)
        elif self.current_test_item == self.TEST_CLK_PERF:
            self._start_clk_perf_test(config)
        else:
            QMessageBox.warning(self, "Error", f"Unknown test item: {self.current_test_item}")
            return

    def _start_cap_freq_test(self, config):
        self._update_chart_labels("Register Value / Cap Code", "Frequency (Hz)")
        self._launch_test_worker(config)

    def _start_temp_freq_test(self, config):
        self._update_chart_labels("Temperature (°C)", "Frequency (Hz)")
        self._launch_test_worker(config)

    def _start_clk_perf_test(self, config):
        self._update_chart_labels("Time (s)", "Frequency (Hz)")
        self._launch_test_worker(config)

    def _launch_test_worker(self, config):
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(True)
        self._update_test_button_state(True)
        self.set_progress(0)

        self._append_log(f"[INFO] Starting {self.current_test_item} test...")

        self._test_thread = QThread()
        self._test_worker = _CLKTestWorker(
            self.current_test_item, config,
            mso64b=self.Osc_ins,
            vt6002=self.vt6002,
            counter=self.Counter_ins,
            mock_mode=DEBUG_MOCK,
        )
        self._test_worker.moveToThread(self._test_thread)

        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.log.connect(self._append_log)
        self._test_worker.progress.connect(self._on_test_progress)
        self._test_worker.progress_int.connect(self.set_progress)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.error.connect(self._on_test_error)

        self._test_worker.finished.connect(self._test_thread.quit)
        self._test_worker.error.connect(self._test_thread.quit)
        self._test_thread.finished.connect(self._cleanup_test_thread)

        self._test_thread.start()

    def _stop_test(self):
        if self._test_worker is not None:
            self._test_worker.stop()
            self._append_log("[INFO] Stop requested...")
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self._update_test_button_state(False)

    def _cleanup_test_thread(self):
        if self._test_worker is not None:
            self._test_worker.deleteLater()
        if self._test_thread is not None:
            self._test_thread.deleteLater()
        self._test_worker = None
        self._test_thread = None
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self._update_test_button_state(False)

    def _update_test_button_state(self, running):
        update_start_btn_state(self.start_test_btn, running,
                               start_text=self._start_btn_text,
                               stop_text="■ Stop")

    def _on_test_progress(self, info):
        mode = info.get("mode")
        if mode == "cap_freq":
            x = info["current"]
            y = info["freq"]
        elif mode == "temp_freq":
            x = info["current"]
            y = info["freq"]
        else:
            return

        self._rt_x_data.append(x)
        self._rt_y_data.append(y)

        if self.plot_curve is None:
            pen = pg.mkPen(color="#00d39a", width=2)
            self.plot_curve = self.plot_widget.plot(
                self._rt_x_data, self._rt_y_data,
                pen=pen, symbol='o', symbolSize=5,
                symbolBrush=pg.mkBrush("#00d39a"), symbolPen=None
            )
        else:
            self.plot_curve.setData(self._rt_x_data, self._rt_y_data)

    def _on_test_finished(self, result):
        self.result_mode = result.get("mode")
        self.result_data = result.get("data", [])
        self.result_summary = result.get("summary", {})

        if self.result_mode in ("cap_freq", "temp_freq"):
            default_code = result.get("default_code")
            self._show_sweep_result(self.result_mode, self.result_data, default_code=default_code)
        elif self.result_mode == "clk_perf":
            self._show_clk_perf_result(self.result_data, self.result_summary)

        self._append_log("[INFO] Test finished.")

    def _on_test_error(self, err):
        QMessageBox.warning(self, "Test Error", err)
        self._append_log(f"[ERROR] {err}")

    # -------------------------------------------------------
    # Result display
    # -------------------------------------------------------
    def _show_sweep_result(self, mode, data, default_code=None):
        if not data:
            return

        freqs = [d["freq"] for d in data]
        x_vals = [d["x"] for d in data]
        min_freq = min(freqs)
        max_freq = max(freqs)

        if mode == "cap_freq":
            default_freq = None
            if default_code is not None:
                for d in data:
                    if d["x"] == default_code:
                        default_freq = d["freq"]
                        break
                if default_freq is None:
                    closest = min(data, key=lambda d: abs(d["x"] - default_code))
                    default_freq = closest["freq"]

            n = len(data)
            step_freq = (freqs[-1] - freqs[0]) / (n - 1) if n > 1 else 0.0

            if n > 1:
                fs = abs(freqs[-1] - freqs[0])
                if fs > 1e-12:
                    slope = (freqs[-1] - freqs[0]) / (x_vals[-1] - x_vals[0])
                    max_err = max(
                        abs(freqs[i] - (freqs[0] + slope * (x_vals[i] - x_vals[0])))
                        for i in range(n)
                    )
                    linearity = max_err / fs * 100.0
                else:
                    linearity = 0.0
            else:
                linearity = 0.0

            self.top_value1.setText(self._format_freq(default_freq) if default_freq else "---")
            self.top_value2.setText(self._format_freq(min_freq))
            self.top_value3.setText(self._format_freq(max_freq))
            self.top_value4.setText(self._format_freq(step_freq) + "/step")
            self.top_value5.setText(f"{linearity:.3f} %FS")

        elif mode == "temp_freq":
            freq_25 = None
            for d in data:
                if abs(d["x"] - 25.0) < 0.01:
                    freq_25 = d["freq"]
                    break
            if freq_25 is None:
                closest = min(data, key=lambda d: abs(d["x"] - 25.0))
                freq_25 = closest["freq"]

            temp_range = x_vals[-1] - x_vals[0]
            per_c_freq = (freqs[-1] - freqs[0]) / temp_range if abs(temp_range) > 1e-9 else 0.0

            n = len(data)
            if n > 1:
                fs = abs(freqs[-1] - freqs[0])
                if fs > 1e-12:
                    slope = (freqs[-1] - freqs[0]) / (x_vals[-1] - x_vals[0])
                    max_err = max(
                        abs(freqs[i] - (freqs[0] + slope * (x_vals[i] - x_vals[0])))
                        for i in range(n)
                    )
                    linearity = max_err / fs * 100.0
                else:
                    linearity = 0.0
            else:
                linearity = 0.0

            self.top_value1.setText(self._format_freq(freq_25))
            self.top_value2.setText(self._format_freq(min_freq))
            self.top_value3.setText(self._format_freq(max_freq))
            self.top_value4.setText(self._format_freq(per_c_freq) + "/°C")
            self.top_value5.setText(f"{linearity:.3f} %FS")

        self._clear_chart()
        y_vals = freqs

        if mode == "cap_freq":
            self._update_chart_labels("Register Value / Cap Code", "Frequency (Hz)")
        else:
            self._update_chart_labels("Temperature (°C)", "Frequency (Hz)")

        pen = pg.mkPen(color="#00d39a", width=2)
        self.plot_curve = self.plot_widget.plot(
            x_vals, y_vals,
            pen=pen, symbol='o', symbolSize=5,
            symbolBrush=pg.mkBrush("#00d39a"), symbolPen=None
        )

        freq_margin = (max_freq - min_freq) * 0.1 if max_freq != min_freq else 1.0
        self.plot_widget.setYRange(min_freq - freq_margin, max_freq + freq_margin)

        if mode == "cap_freq" and default_code is not None and default_freq is not None:
            default_scatter = pg.ScatterPlotItem(
                [default_code], [default_freq],
                symbol='star', size=18,
                brush=pg.mkBrush("#ff5a7a"),
                pen=pg.mkPen("#ffffff", width=1.5)
            )
            self.plot_widget.addItem(default_scatter)

            default_label = pg.TextItem(
                f"Default (Code=0x{default_code:04X}, {self._format_freq(default_freq)})",
                color="#ff5a7a", anchor=(0, 1.3)
            )
            default_label.setPos(default_code, default_freq)
            self.plot_widget.addItem(default_label)

        if mode == "temp_freq" and freq_25 is not None:
            t25_scatter = pg.ScatterPlotItem(
                [25.0], [freq_25],
                symbol='star', size=18,
                brush=pg.mkBrush("#ffb84d"),
                pen=pg.mkPen("#ffffff", width=1.5)
            )
            self.plot_widget.addItem(t25_scatter)
            t25_label = pg.TextItem(
                f"25°C ({self._format_freq(freq_25)})",
                color="#ffb84d", anchor=(0, 1.3)
            )
            t25_label.setPos(25.0, freq_25)
            self.plot_widget.addItem(t25_label)

    def _show_clk_perf_result(self, data, summary):
        if not data:
            return

        avg_freq = summary.get("avg_freq", 0.0)
        avg_period_us = summary.get("avg_period_us", 0.0)
        min_period_us = summary.get("min_period_us", 0.0)
        max_period_us = summary.get("max_period_us", 0.0)
        period_jitter_pp = summary.get("period_jitter_pp_ns", 0.0)
        freq_drift_ppm = summary.get("freq_drift_ppm", 0.0)

        self.top_value1.setText(f"{self._format_freq(avg_freq)} ({avg_period_us:.4f} us)")
        self.top_value2.setText(f"{min_period_us:.4f} us")
        self.top_value3.setText(f"{max_period_us:.4f} us")
        self.top_value4.setText(f"{period_jitter_pp:.3f} ns")
        self.top_value5.setText(f"{freq_drift_ppm:+.3f} ppm")

        self._render_clk_chart(data, summary)

    def _render_clk_chart(self, data, summary):
        chart_type = self.clk_chart_type_combo.currentData()
        self._clear_chart()

        if chart_type == "freq_vs_time":
            self._chart_freq_vs_time(data, summary)
        elif chart_type == "period_vs_time":
            self._chart_period_vs_time(data, summary)
        elif chart_type == "period_histogram":
            self._chart_period_histogram(data, summary)
        elif chart_type == "n_cycle_tie":
            self._chart_n_cycle_tie(data, summary)
        elif chart_type == "abs_window_err":
            self._chart_abs_window_err(data, summary)
        elif chart_type == "time_domain":
            self._chart_time_domain(data, summary)

    def _chart_freq_vs_time(self, data, summary):
        self._update_chart_labels("Time (s)", "Frequency (Hz)")
        x_vals = [d["x"] for d in data]
        y_vals = [d["freq"] for d in data]
        avg_freq = summary.get("avg_freq", 0.0)

        pen = pg.mkPen(color="#3da8ff", width=1.5)
        self.plot_curve = self.plot_widget.plot(x_vals, y_vals, pen=pen)

        if y_vals:
            min_f, max_f = min(y_vals), max(y_vals)
            margin = (max_f - min_f) * 0.1 if max_f != min_f else 1.0
            self.plot_widget.setYRange(min_f - margin, max_f + margin)

        avg_line = pg.InfiniteLine(
            pos=avg_freq, angle=0, movable=False,
            pen=pg.mkPen(color="#ffb84d", width=1, style=Qt.DashLine),
            label=f"Avg: {self._format_freq(avg_freq)}",
            labelOpts={"color": "#ffb84d", "position": 0.05}
        )
        self.plot_widget.addItem(avg_line)

    def _chart_period_vs_time(self, data, summary):
        self._update_chart_labels("Time (s)", "Period (us)")
        avg_freq = summary.get("avg_freq", 1.0)
        avg_period_us = summary.get("avg_period_us", 1.0 / avg_freq * 1e6)

        x_vals = [d["x"] for d in data]
        y_vals = [1.0 / d["freq"] * 1e6 for d in data if d["freq"] > 0]
        x_vals = x_vals[:len(y_vals)]

        pen = pg.mkPen(color="#00d39a", width=1.5)
        self.plot_curve = self.plot_widget.plot(x_vals, y_vals, pen=pen)

        if y_vals:
            min_p, max_p = min(y_vals), max(y_vals)
            margin = (max_p - min_p) * 0.1 if max_p != min_p else 0.01
            self.plot_widget.setYRange(min_p - margin, max_p + margin)

        avg_line = pg.InfiniteLine(
            pos=avg_period_us, angle=0, movable=False,
            pen=pg.mkPen(color="#ffb84d", width=1, style=Qt.DashLine),
            label=f"Avg: {avg_period_us:.4f} us",
            labelOpts={"color": "#ffb84d", "position": 0.05}
        )
        self.plot_widget.addItem(avg_line)

    def _chart_period_histogram(self, data, summary):
        self._update_chart_labels("Period (us)", "Count")
        import numpy as np
        periods_us = [1.0 / d["freq"] * 1e6 for d in data if d["freq"] > 0]
        if not periods_us:
            return

        arr = np.array(periods_us)
        bin_count = min(200, max(20, len(arr) // 50))
        hist, bin_edges = np.histogram(arr, bins=bin_count)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
        bar_width = (bin_edges[1] - bin_edges[0]) * 0.9

        bargraph = pg.BarGraphItem(
            x=bin_centers, height=hist, width=bar_width,
            brush=pg.mkBrush("#3da8ff80"), pen=pg.mkPen("#3da8ff", width=0.5)
        )
        self.plot_widget.addItem(bargraph)

        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))

        avg_line = pg.InfiniteLine(
            pos=mean_val, angle=90, movable=False,
            pen=pg.mkPen(color="#ffb84d", width=1.5, style=Qt.DashLine),
            label=f"Avg: {mean_val:.4f} us",
            labelOpts={"color": "#ffb84d", "position": 0.95}
        )
        self.plot_widget.addItem(avg_line)

        sigma_styles = [
            (1, "#00d39a", 0.90),
            (2, "#e066ff", 0.85),
            (3, "#ff5a7a", 0.80),
        ]
        for k, color, lbl_pos in sigma_styles:
            for sign in (-1, 1):
                pos = mean_val + sign * k * std_val
                side = "+" if sign > 0 else "-"
                line = pg.InfiniteLine(
                    pos=pos, angle=90, movable=False,
                    pen=pg.mkPen(color=color, width=1, style=Qt.DotLine),
                    label=f"{side}{k}\u03c3",
                    labelOpts={"color": color, "position": lbl_pos}
                )
                self.plot_widget.addItem(line)

    def _chart_n_cycle_tie(self, data, summary):
        n = self.clk_n_cycle_spin.value()
        self._update_chart_labels("Time (s)", f"{n}-Cycle Timing Error (ns)")

        avg_freq = summary.get("avg_freq", 1.0)
        avg_period = 1.0 / avg_freq if avg_freq > 0 else 1.0

        periods = [1.0 / d["freq"] for d in data if d["freq"] > 0]
        times = [d["x"] for d in data if d["freq"] > 0]

        if len(periods) < n:
            return

        x_vals = []
        y_vals = []
        ideal_n_period = avg_period * n
        for i in range(len(periods) - n + 1):
            actual_sum = sum(periods[i:i + n])
            err_ns = (actual_sum - ideal_n_period) * 1e9
            x_vals.append(times[i])
            y_vals.append(err_ns)

        pen = pg.mkPen(color="#e066ff", width=1.5)
        self.plot_curve = self.plot_widget.plot(x_vals, y_vals, pen=pen)

        if y_vals:
            min_e, max_e = min(y_vals), max(y_vals)
            margin = (max_e - min_e) * 0.1 if max_e != min_e else 1.0
            self.plot_widget.setYRange(min_e - margin, max_e + margin)

        zero_line = pg.InfiniteLine(
            pos=0, angle=0, movable=False,
            pen=pg.mkPen(color="#ffb84d", width=1, style=Qt.DashLine)
        )
        self.plot_widget.addItem(zero_line)

    def _chart_abs_window_err(self, data, summary):
        window_ms = self.clk_abs_window_spin.value()
        window = window_ms / 1000.0
        self._update_chart_labels("Window Start (s)", f"CLK Time Error in {window_ms:.2f}ms Window (ns)")

        avg_freq = summary.get("avg_freq", 1.0)
        avg_period = 1.0 / avg_freq if avg_freq > 0 else 1.0

        periods = [1.0 / d["freq"] for d in data if d["freq"] > 0]
        times = [d["x"] for d in data if d["freq"] > 0]
        if not periods:
            return

        cum_times = [0.0]
        for p in periods:
            cum_times.append(cum_times[-1] + p)

        n_per_window = int(round(window / avg_period))
        if n_per_window < 1:
            n_per_window = 1

        x_vals = []
        y_vals = []
        for i in range(len(periods) - n_per_window + 1):
            actual_time = sum(periods[i:i + n_per_window])
            ideal_time = n_per_window * avg_period
            err_ns = (actual_time - ideal_time) * 1e9
            x_vals.append(times[i] if i < len(times) else cum_times[i])
            y_vals.append(err_ns)

        pen = pg.mkPen(color="#ff7f50", width=1.5)
        self.plot_curve = self.plot_widget.plot(x_vals, y_vals, pen=pen)

        if y_vals:
            min_e, max_e = min(y_vals), max(y_vals)
            margin = (max_e - min_e) * 0.1 if max_e != min_e else 1.0
            self.plot_widget.setYRange(min_e - margin, max_e + margin)

        zero_line = pg.InfiniteLine(
            pos=0, angle=0, movable=False,
            pen=pg.mkPen(color="#ffb84d", width=1, style=Qt.DashLine)
        )
        self.plot_widget.addItem(zero_line)

    def _chart_time_domain(self, data, summary):
        self._update_chart_labels("Time (s)", "Cumulative TIE (ns)")

        avg_freq = summary.get("avg_freq", 1.0)
        avg_period = 1.0 / avg_freq if avg_freq > 0 else 1.0

        periods = [1.0 / d["freq"] for d in data if d["freq"] > 0]
        times = [d["x"] for d in data if d["freq"] > 0]
        if not periods:
            return

        x_vals = []
        y_vals = []
        ideal_accum = 0.0
        real_accum = 0.0
        for i, p in enumerate(periods):
            ideal_accum += avg_period
            real_accum += p
            tie_ns = (real_accum - ideal_accum) * 1e9
            x_vals.append(times[i])
            y_vals.append(tie_ns)

        pen = pg.mkPen(color="#00bfff", width=1.5)
        self.plot_curve = self.plot_widget.plot(x_vals, y_vals, pen=pen)

        if y_vals:
            min_t, max_t = min(y_vals), max(y_vals)
            margin = (max_t - min_t) * 0.1 if max_t != min_t else 1.0
            self.plot_widget.setYRange(min_t - margin, max_t + margin)

        zero_line = pg.InfiniteLine(
            pos=0, angle=0, movable=False,
            pen=pg.mkPen(color="#ffb84d", width=1, style=Qt.DashLine)
        )
        self.plot_widget.addItem(zero_line)

    # -------------------------------------------------------
    # Export / Import
    # -------------------------------------------------------
    def export_result(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Result", "", "CSV Files (*.csv)")
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)

                if self.result_mode == "cap_freq":
                    writer.writerow(["value", "frequency_hz"])
                    for d in self.result_data:
                        writer.writerow([d["x"], d["freq"]])

                elif self.result_mode == "temp_freq":
                    writer.writerow(["temperature_c", "frequency_hz", "deviation_ppm"])
                    for d in self.result_data:
                        writer.writerow([d["x"], d["freq"], d["ppm"]])

                elif self.result_mode == "clk_perf":
                    writer.writerow(["time_s", "frequency_hz", "deviation_ppm"])
                    for d in self.result_data:
                        writer.writerow([d["x"], d["freq"], d["ppm"]])
                else:
                    writer.writerow(["result"])
                    writer.writerow(["no data"])

            self.log_text.append(f"[INFO] Exported to: {path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", str(e))

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import CSV", "", "CSV Files (*.csv)")
        if path:
            self.csv_file_path = path
            self.csv_path_label.setText(path)
            self.log_text.append(f"[INFO] Imported from: {path}")

    def _on_clk_source_changed(self, index):
        source_text = self.clk_source_combo.currentText()
        is_csv = (source_text == "Import CSV")
        is_online = not is_csv
        self.clk_online_params_frame.setVisible(is_online)
        self.clk_csv_frame.setVisible(is_csv)
        self._update_instrument_visibility()
        self.log_text.append(f"[INFO] CLK source changed to {source_text}")

    def _on_clk_chart_type_changed(self, index):
        chart_type = self.clk_chart_type_combo.currentData()
        self.clk_n_cycle_frame.setVisible(chart_type == "n_cycle_tie")
        self.clk_abs_window_frame.setVisible(chart_type == "abs_window_err")
        if self.result_mode == "clk_perf" and self.result_data:
            self._render_clk_chart(self.result_data, self.result_summary)

    def _on_clk_chart_param_changed(self):
        if self.result_mode == "clk_perf" and self.result_data:
            self._render_clk_chart(self.result_data, self.result_summary)