# -*- coding: utf-8 -*-
"""
CLK 测试 Worker（仅依赖 PySide6.QtCore，不依赖 QtWidgets）。

从 ui/pages/pmu_test/clk_test_ui.py 的 _CLKTestWorker 平移而来，
算法/解析委托 core.pmu_test.clk.clk_analysis，行为零变更。
"""

import math
import os
import subprocess
import sys
import time

from PySide6.QtCore import QObject, Signal

from instruments.chambers import TemperatureStabilizer
from .clk_analysis import (
    simulate_frequency,
    float_range,
    parse_tek_csv,
    parse_dslogic_csv,
    parse_generic_csv,
    find_sigrok_cli,
    analyze_clk_perf,
)


class ClkTestWorker(QObject):
    log = Signal(str)
    finished = Signal(dict)
    progress = Signal(dict)
    progress_int = Signal(int)
    error = Signal(str)

    def __init__(self, test_item, config, mso64b=None, chamber=None, counter=None, mock_mode=False, parent=None):
        super().__init__(parent)
        self.test_item = test_item
        self.config = config
        self.mso64b = mso64b
        self.chamber = chamber
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
                freq = simulate_frequency(
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

    def _run_temp_freq(self):
        temp_start = self.config["temp_start"]
        temp_end = self.config["temp_end"]
        temp_step = self.config["temp_step"]
        soak_time = self.config.get("temp_soak_time", 180)
        tolerance = self.config.get("temp_stable_tolerance", 0.5)
        mso_channel = self.config.get("mso_channel", 2)

        temps = float_range(temp_start, temp_end, temp_step)
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

        chamber = self.chamber
        if not chamber:
            raise RuntimeError("Chamber not connected")

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

        ble_min_time = self.config.get("ble_min_time", 0.1)
        result = analyze_clk_perf(samples, ble_min_time=ble_min_time, log_fn=self.log.emit)

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
            samples = parse_tek_csv(raw_lines)
            self.log.emit(f"[INFO] Detected MSO64B (TekScope) CSV format")
        elif "libsigrok" in first_lines or "dslogic" in first_lines or "sample rate" in first_lines:
            samples = parse_dslogic_csv(raw_lines, log_fn=self.log.emit)
            self.log.emit(f"[INFO] Detected DSLogic CSV format")
        else:
            samples = parse_generic_csv(raw_lines)
            self.log.emit(f"[INFO] Using generic CSV parser")

        if not samples:
            raise ValueError("No valid period data found in CSV")

        self.log.emit(f"[INFO] CSV parsing complete, {len(samples)} period data points")
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
            samples = parse_tek_csv(raw_lines)

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

            sigrok_cli = find_sigrok_cli()
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
                results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))), "Results")
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
            samples = parse_dslogic_csv(raw_lines, log_fn=self.log.emit)

            if not samples:
                raise ValueError("No valid period data parsed from DSLogic capture")

            self.log.emit(f"[INFO] DSLogic online acquisition parsed, {len(samples)} period data points")

        return samples
