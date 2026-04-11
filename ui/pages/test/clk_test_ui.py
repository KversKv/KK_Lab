#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import math
import os
import statistics
import subprocess
import time
import serial
import serial.tools.list_ports

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QGridLayout, QFrame, QScrollArea,
    QSizePolicy, QSpinBox, QDoubleSpinBox, QComboBox,
    QTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont
import pyqtgraph as pg
from ui.styles import SCROLL_AREA_STYLE
from debug_config import DEBUG_MOCK


class DarkComboBox(QComboBox):
    def __init__(self, bg="#0b1630", border="#24365e", parent=None):
        super().__init__(parent)
        self._popup_bg = "#111c38"
        self._border = border
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg};
                border: 1.5px solid {border};
                border-radius: 6px;
                padding: 4px 28px 4px 10px;
                color: #c8d8f8;
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #111c38;
                color: #c8d8f8;
                border: 1px solid {border};
                selection-background-color: #1e3870;
                outline: 0;
                padding: 0px;
                margin: 0px;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: #111c38;
                color: #c8d8f8;
                padding: 4px 10px;
                border: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #1e3870;
            }}
        """)
        self.setMaxVisibleItems(30)

    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        if popup:
            popup.setStyleSheet(
                f"background-color: {self._popup_bg}; "
                f"border: 1px solid {self._border}; "
                f"padding: 0px; margin: 0px;"
            )


class _SearchMSO64BWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        rm = None
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
            devices = rm.list_resources()
            mso_devices = [d for d in devices if 'MSO' in d or 'TCPIP' in d or 'USB' in d]
            self.finished.emit(list(mso_devices))
        except Exception as e1:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass
                rm = None
            try:
                import pyvisa
                rm = pyvisa.ResourceManager('@py')
                devices = rm.list_resources()
                mso_devices = [d for d in devices if 'MSO' in d or 'TCPIP' in d or 'USB' in d]
                self.finished.emit(list(mso_devices))
            except Exception as e2:
                self.error.emit(f"NI-VISA: {e1}; pyvisa-py: {e2}")
                self.finished.emit([])
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass


class _SearchSerialWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            ports = serial.tools.list_ports.comports()
            result = [f"{p.device} - {p.description}" for p in ports]
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _CLKTestWorker(QObject):
    log = Signal(str)
    finished = Signal(dict)
    progress = Signal(dict)
    error = Signal(str)

    def __init__(self, test_item, config, mso64b=None, vt6002=None, mock_mode=False, parent=None):
        super().__init__(parent)
        self.test_item = test_item
        self.config = config
        self.mso64b = mso64b
        self.vt6002 = vt6002
        self.mock_mode = mock_mode
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

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

        values = []
        codes = list(range(start_code, end_code + 1, step))
        if not codes:
            raise ValueError("补偿码范围无效")

        self.log.emit("[INFO] 开始测试：补偿电容和频率关系")
        self.log.emit(f"[INFO] IIC Device Addr = 0x{device_addr:02X}, REG Addr = 0x{reg_addr:04X}")
        self.log.emit(f"[INFO] Width Flag = {width_flag}, MSB = {msb}, LSB = {lsb}")
        self.log.emit(f"[INFO] MSO64B Channel = CH{mso_channel}")

        bit_mask = ((1 << (msb - lsb + 1)) - 1) << lsb

        if not self.mock_mode:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            iic = I2CInterface()
            if not iic.initialize():
                raise RuntimeError("I2C接口初始化失败")
            self.log.emit("[INFO] I2C接口初始化成功")
            self.mso64b.instrument.write(f'DVM:SOURCE CH{mso_channel}')
            self.log.emit(f"[INFO] MSO64B DVM Source set to CH{mso_channel}")

            orig_val = iic.read(device_addr, reg_addr, width_flag)
            self.log.emit(f"[INFO] 寄存器原始值 = 0x{orig_val:04X}, bit_mask = 0x{bit_mask:04X}")
            base_val = orig_val & ~bit_mask
            default_code = (orig_val & bit_mask) >> lsb
            iic.write(device_addr, reg_addr, base_val, width_flag)
            time.sleep(0.5)
            self.log.emit(f"[INFO] 保留位值 (other bits) = 0x{base_val:04X}")
            self.log.emit(f"[INFO] Default Code = {default_code}")
        else:
            orig_val = 0x1120
            base_val = orig_val & ~bit_mask
            default_code = (orig_val & bit_mask) >> lsb
            self.log.emit(f"[MOCK] 寄存器模拟原始值 = 0x{orig_val:04X}, 保留位值 = 0x{base_val:04X}, Default Code = {default_code}")

        for code in codes:
            if self._stop_flag:
                self.log.emit("[WARN] 测试被停止")
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
                freq = self.mso64b.get_dvm_frequency(enable_counter=True, wait_time=0.3)

            values.append({"x": code, "freq": freq})
            self.progress.emit({"mode": "cap_freq", "current": code, "freq": freq})
            self.log.emit(f"[DATA] Code={code:>4d}  |  RegVal=0x{write_val:04X}  |  Freq={freq:>18.6f} Hz")
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
            raise ValueError("温度范围无效")

        values = []
        self.log.emit("[INFO] 开始测试：高低温频偏测试")
        self.log.emit(f"[INFO] 温度范围        = {temp_start} °C -> {temp_end} °C, step={temp_step} °C")
        self.log.emit(f"[INFO] Soak Time       = {soak_time} s, Tolerance = {tolerance} °C")

        if self.mock_mode:
            self.log.emit("[MOCK] 使用模拟温箱和频率数据")
            mock_nominal = 32768.0
            for t in temps:
                if self._stop_flag:
                    self.log.emit("[WARN] 测试被停止")
                    break
                delta_ppm = (t - 25.0) * 0.8 + math.sin(t / 15.0) * 0.6
                freq = mock_nominal * (1.0 + delta_ppm / 1_000_000.0)
                values.append({"x": t, "freq": freq})
                self.progress.emit({"mode": "temp_freq", "current": t, "freq": freq})
                self.log.emit(f"[DATA] Temp={t:>7.1f} °C  |  Freq={freq:>18.6f} Hz")
                time.sleep(0.05)
            return {"mode": "temp_freq", "data": values}

        chamber = self.vt6002
        if not chamber:
            raise RuntimeError("VT6002温箱未连接")

        self.mso64b.instrument.write(f'DVM:SOURCE CH{mso_channel}')
        self.log.emit(f"[INFO] MSO64B DVM Source set to CH{mso_channel}")

        for idx, t in enumerate(temps):
            if self._stop_flag:
                self.log.emit("[WARN] 测试被停止")
                break

            chamber.set_temperature(t)
            self.log.emit(f"[INFO] [{idx + 1}/{len(temps)}] 温箱设定温度: {t:.1f} °C, 等待温度稳定...")

            history = []
            stable_count = 0
            poll_count = 0
            wait_t0 = time.time()
            while True:
                if self._stop_flag:
                    break
                actual_temp = chamber.get_current_temp()
                history.append(actual_temp)
                poll_count += 1
                if len(history) > 10:
                    history.pop(0)
                if len(history) >= 5:
                    if max(history) - min(history) < tolerance:
                        stable_count += 1
                    else:
                        stable_count = 0
                    if stable_count >= 3:
                        break
                time.sleep(30)

            wait_elapsed = time.time() - wait_t0

            if self._stop_flag:
                self.log.emit("[WARN] 测试被停止")
                break

            actual_temp = chamber.get_current_temp()
            self.log.emit(
                f"[INFO] [{idx + 1}/{len(temps)}] 温度已稳定: "
                f"target={t:.1f} °C, actual={actual_temp:.2f} °C, "
                f"轮询 {poll_count} 次, 等待 {wait_elapsed:.0f}s"
            )

            self.log.emit(f"[INFO] DUT温度均衡中 ({soak_time}s)...")
            for i in range(soak_time):
                if self._stop_flag:
                    break
                time.sleep(1)

            if self._stop_flag:
                self.log.emit("[WARN] 测试被停止")
                break

            freq = self.mso64b.get_dvm_frequency(enable_counter=True, wait_time=0.3)
            actual_temp = chamber.get_current_temp()
            values.append({"x": actual_temp, "freq": freq})
            self.progress.emit({"mode": "temp_freq", "current": actual_temp, "freq": freq})
            self.log.emit(f"[DATA] Temp={actual_temp:>7.2f} °C  |  Freq={freq:>18.6f} Hz")

        chamber.set_temperature(25.0)
        self.log.emit("[INFO] 温箱已恢复至 25.0 °C")

        if values:
            self.log.emit("")
            self.log.emit("=" * 60)
            self.log.emit("  高低温频偏测试结果汇总")
            self.log.emit("=" * 60)
            self.log.emit(f"  {'#':>3}  {'温度 (°C)':>10}  {'频率 (Hz)':>18}  {'偏移 (ppm)':>12}")
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
        self.log.emit("[INFO] 开始测试：时钟性能测试")
        self.log.emit(f"[INFO] 数据源          = {source}")

        if source == "Import CSV":
            samples = self._clk_perf_from_csv()
        elif source == "MSO64B":
            samples = self._clk_perf_from_mso64b()
        elif source == "DSLogic":
            samples = self._clk_perf_from_dslogic()
        else:
            raise ValueError(f"未知数据源: {source}")

        return self._analyze_clk_perf(samples)

    def _clk_perf_from_csv(self):
        csv_path = self.config.get("csv_path", "")
        if not csv_path:
            raise ValueError("未选择CSV文件")

        with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
            raw_lines = f.readlines()

        if not raw_lines:
            raise ValueError("CSV文件为空")

        first_lines = "".join(raw_lines[:10]).lower()

        if "tekscope" in first_lines or "name,type,src" in first_lines:
            samples = self._parse_tek_csv(raw_lines)
            self.log.emit(f"[INFO] 检测到MSO64B (TekScope) CSV格式")
        elif "libsigrok" in first_lines or "dslogic" in first_lines or "sample rate" in first_lines:
            samples = self._parse_dslogic_csv(raw_lines)
            self.log.emit(f"[INFO] 检测到DSLogic CSV格式")
        else:
            samples = self._parse_generic_csv(raw_lines)
            self.log.emit(f"[INFO] 使用通用CSV解析")

        if not samples:
            raise ValueError("CSV中未解析到有效周期数据")

        self.log.emit(f"[INFO] CSV解析完成, 共 {len(samples)} 个周期数据点")
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
            raise ValueError("TekScope CSV数据行不足")

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
            raise ValueError("DSLogic CSV中上升沿数据不足")

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
        self.log.emit(f"[INFO] MSO64B 采样率 = {sample_rate_mhz} MHz, 测试时间 = {duration} s")
        self.log.emit(f"[INFO] MSO64B Channel = CH{mso_channel}")

        samples = []
        if self.mock_mode:
            mock_nominal = 32768.0
            nominal_period = 1.0 / mock_nominal
            count = max(100, int(duration * 1000))
            for i in range(count):
                if self._stop_flag:
                    self.log.emit("[WARN] 测试被停止")
                    break
                t = i * 0.001
                jitter = math.sin(i / 35.0) * nominal_period * 0.003 + (math.cos(i / 13.0) * nominal_period * 0.001)
                period = nominal_period + jitter
                samples.append((t, period))
            self.log.emit(f"[MOCK] MSO64B 在线采样点数 = {len(samples)}")
        else:
            scope = self.mso64b
            remote_csv = 'C:/Temp/clk_edge_search.csv'

            self.log.emit("[INFO] 配置MSO64B水平参数...")
            scope.configure_horizontal(duration, sample_rate_mhz)
            self.log.emit(f"[INFO] Horizontal Scale = {duration / 10:.4f} s/div, Duration = {duration} s")

            if self._stop_flag:
                return samples

            self.log.emit(f"[INFO] 配置Edge Search: CH{mso_channel}, BOTH edges")
            scope.setup_edge_search(mso_channel, slope='BOTH')

            if self._stop_flag:
                return samples

            acq_timeout = max(duration * 3, 30)
            self.log.emit(f"[INFO] 启动单次采集 (超时 {acq_timeout:.0f}s)...")
            scope.single_acquisition(timeout_s=acq_timeout)
            self.log.emit("[INFO] 采集完成")

            if self._stop_flag:
                return samples

            time.sleep(1.0)
            total_marks = scope.get_search_total()
            self.log.emit(f"[INFO] Edge Search 结果: {total_marks} 个标记点")

            if total_marks < 3:
                raise ValueError(f"Edge Search仅找到 {total_marks} 个边沿, 数据不足")

            self.log.emit(f"[INFO] 导出Search Table -> {remote_csv}")
            scope.export_search_table_csv(remote_csv)
            time.sleep(1.0)

            if self._stop_flag:
                return samples

            self.log.emit("[INFO] 从MSO64B读取CSV文件...")
            csv_content = scope.read_remote_file(remote_csv)
            scope.delete_remote_file(remote_csv)

            raw_lines = csv_content.splitlines(keepends=True)
            if not raw_lines:
                raise ValueError("从MSO64B读取的CSV为空")

            self.log.emit(f"[INFO] CSV内容 {len(raw_lines)} 行, 开始解析...")
            samples = self._parse_tek_csv(raw_lines)

            if not samples:
                raise ValueError("未能从MSO64B导出的CSV中解析到有效周期数据")

            self.log.emit(f"[INFO] MSO64B在线采集解析完成, 共 {len(samples)} 个周期数据点")

        return samples

    def _clk_perf_from_dslogic(self):
        duration = self.config["clk_duration"]
        sample_rate_mhz = self.config.get("clk_sample_rate", 100.0)
        self.log.emit(f"[INFO] DSLogic 采样率 = {sample_rate_mhz} MHz, 测试时间 = {duration} s")

        samples = []
        if self.mock_mode:
            mock_nominal = 32768.0
            nominal_period = 1.0 / mock_nominal
            count = max(100, int(duration * 1000))
            for i in range(count):
                if self._stop_flag:
                    self.log.emit("[WARN] 测试被停止")
                    break
                t = i * 0.001
                jitter = math.sin(i / 28.0) * nominal_period * 0.004 + (math.cos(i / 11.0) * nominal_period * 0.0015)
                period = nominal_period + jitter
                samples.append((t, period))
            self.log.emit(f"[MOCK] DSLogic 在线采样点数 = {len(samples)}")
        else:
            sample_rate_hz = int(sample_rate_mhz * 1e6)
            total_samples = int(sample_rate_hz * duration)
            self.log.emit(f"[INFO] 总采样点数 = {total_samples:,}")

            sigrok_cli = self._find_sigrok_cli()
            if not sigrok_cli:
                raise FileNotFoundError(
                    "未找到 sigrok-cli，请安装 sigrok 套件并确保 sigrok-cli 在 PATH 中, "
                    "或将 sigrok-cli.exe 所在路径添加到系统环境变量"
                )
            self.log.emit(f"[INFO] sigrok-cli 路径: {sigrok_cli}")

            if self._stop_flag:
                return samples

            self.log.emit("[INFO] 扫描 DSLogic 设备...")
            scan_cmd = [sigrok_cli, "--driver", "dreamsourcelab-dslogic", "--scan"]
            try:
                scan_result = subprocess.run(
                    scan_cmd, capture_output=True, text=True, timeout=15, encoding="utf-8"
                )
                if scan_result.returncode != 0:
                    err_msg = scan_result.stderr.strip() or scan_result.stdout.strip()
                    raise ConnectionError(f"DSLogic 设备扫描失败: {err_msg}")
                scan_output = scan_result.stdout.strip()
                if not scan_output:
                    raise ConnectionError("未检测到 DSLogic 设备，请检查 USB 连接和驱动")
                self.log.emit(f"[INFO] 检测到设备: {scan_output}")
            except subprocess.TimeoutExpired:
                raise ConnectionError("DSLogic 设备扫描超时")

            if self._stop_flag:
                return samples

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
            self.log.emit(f"[INFO] 启动采集 (dedup模式): samplerate={sample_rate_hz}, samples={total_samples}")
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
                        self.log.emit("[WARN] 用户中止采集")
                        return samples
                    elapsed = time.time() - t0
                    if elapsed > capture_timeout:
                        proc.terminate()
                        proc.wait(timeout=5)
                        raise TimeoutError(f"DSLogic 采集超时 ({capture_timeout:.0f}s)")
                    if int(elapsed) % 5 == 0 and elapsed > 1:
                        pct = min(elapsed / duration * 100, 99)
                        self.log.emit(f"[INFO] 采集中... {elapsed:.0f}s / {duration}s ({pct:.0f}%)")
                    time.sleep(0.5)

                stdout_data = proc.stdout.read().decode("utf-8", errors="replace")
                stderr_data = proc.stderr.read().decode("utf-8", errors="replace")

                if proc.returncode != 0:
                    raise RuntimeError(f"sigrok-cli 采集失败 (code={proc.returncode}): {stderr_data.strip()}")

                self.log.emit("[INFO] 采集完成")
            except FileNotFoundError:
                raise FileNotFoundError(f"无法执行: {sigrok_cli}")

            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"采集输出文件不存在: {csv_path}")

            file_size = os.path.getsize(csv_path)
            self.log.emit(f"[INFO] CSV 文件大小 (dedup): {file_size / 1024:.1f} KB")

            if self._stop_flag:
                return samples

            self.log.emit("[INFO] 解析采集数据...")
            with open(csv_path, "r", encoding="utf-8") as f:
                raw_lines = f.readlines()

            self.log.emit(f"[INFO] 读取 {len(raw_lines)} 行数据")
            samples = self._parse_dslogic_csv(raw_lines)

            if not samples:
                raise ValueError("未能从 DSLogic 采集数据中解析到有效周期数据")

            self.log.emit(f"[INFO] DSLogic 在线采集解析完成, 共 {len(samples)} 个周期数据点")

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
            raise ValueError("无有效采样数据")

        periods = [p for _, p in samples if p > 0]
        if not periods:
            raise ValueError("无有效周期数据")

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
            self.log.emit("[BLE] SCA = 时钟自身稳定性 (以自身均值为基准)")
            self.log.emit("=" * 60)
            self.log.emit(f"[BLE] Measured Avg Freq     = {avg_freq:.6f} Hz (作为基准)")
            self.log.emit(f"[BLE] Total Measure Time   = {total_time:.3f} s")
            self.log.emit(f"[BLE] Freq Drift           = {freq_drift_ppm:+.3f} ppm")
            self.log.emit("-" * 60)

            ble_windows = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 4.0]
            worst_stability_ppm = abs(freq_drift_ppm)

            self.log.emit("[BLE] Window Stability Analysis (相对自身均值):")
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
            self.log.emit("[BLE] SCA 等级参考表 (Bluetooth Core Spec):")
            self.log.emit("[BLE]   SCA=7: 0-20 ppm    (最佳, 最小窗口加宽)")
            self.log.emit("[BLE]   SCA=6: 21-30 ppm")
            self.log.emit("[BLE]   SCA=5: 31-50 ppm   (推荐 Master/Central)")
            self.log.emit("[BLE]   SCA=4: 51-75 ppm")
            self.log.emit("[BLE]   SCA=3: 76-100 ppm")
            self.log.emit("[BLE]   SCA=2: 101-150 ppm")
            self.log.emit("[BLE]   SCA=1: 151-250 ppm")
            self.log.emit("[BLE]   SCA=0: 251-500 ppm (最低, 最大窗口加宽)")
            self.log.emit("-" * 60)

            if matched_sca:
                sca_val, _, _ = matched_sca
                conn_interval_s = 1.0
                peer_sca_ppm = 50.0
                own_sca_ppm = worst_stability_ppm
                combined_sca = own_sca_ppm + peer_sca_ppm
                window_widening_us = combined_sca * conn_interval_s * 2
                self.log.emit(f"[BLE] 窗口加宽估算 (Connection Interval = {conn_interval_s*1000:.0f}ms, Peer SCA = ±{peer_sca_ppm:.0f} ppm):")
                self.log.emit(f"[BLE]   Combined SCA        = ±{combined_sca:.1f} ppm")
                self.log.emit(f"[BLE]   Window Widening     = {window_widening_us:.1f} us")
                self.log.emit(f"[BLE]   (公式: widening = (masterSCA + slaveSCA) × timeSinceLastAnchor × 2)")

            self.log.emit("=" * 60)
        else:
            self.log.emit(f"[INFO] 数据时长 {total_time:.2f}s < {ble_min_time:.1f}s, 跳过蓝牙适用性分析 (需要 ≥ {ble_min_time:.1f}s)")

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


class CLKTestUI(QWidget):
    """
    CLK Test 主 UI 组件
    测试项目：
      1. cap_freq  — 补偿电容和频率关系
      2. temp_freq — 高低温频偏测试
      3. clk_perf  — 时钟性能测试（支持CSV导入）
    """

    TEST_CAP_FREQ = "cap_freq"
    TEST_TEMP_FREQ = "temp_freq"
    TEST_CLK_PERF = "clk_perf"

    def __init__(self, mso64b_top=None, parent=None):
        super().__init__(parent)
        self._mso64b_top = mso64b_top
        self.current_test_item = self.TEST_CAP_FREQ

        # 仪器实例
        self.mso64b = None
        self.vt6002 = None
        self.is_mso64b_connected = False
        self.is_vt6002_connected = False

        # 工作线程属性
        self._test_thread = None
        self._test_worker = None
        self._start_btn_text = "▶ START TEST"
        self._mso64b_search_thread = None
        self._mso64b_search_worker = None
        self._vt6002_search_thread = None
        self._vt6002_search_worker = None

        # 结果数据
        self.result_data = []
        self.result_mode = None
        self.result_summary = {}
        self.csv_file_path = ""

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._sync_from_top()

    # -------------------------------------------------------
    # 样式
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

            QFrame#panel, QFrame#action_panel, QFrame#chart_panel {
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
                font-size: 11px;
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

            QPushButton#start_test_btn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1e3fa0, stop:1 #3060d0);
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                min-height: 36px;
                padding: 0 12px;
            }
            QPushButton#start_test_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2850c0, stop:1 #4070e8);
            }
            QPushButton#start_test_btn:disabled {
                background-color: #1a2040;
                color: #4a5a80;
            }

            QPushButton#stop_test_btn {
                background-color: #2a1a1a;
                color: #ff5a7a;
                border: 1px solid #6a2030;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 700;
                min-height: 36px;
                min-width: 36px;
                padding: 0 10px;
            }
            QPushButton#stop_test_btn:hover {
                background-color: #3a1a1a;
            }
            QPushButton#stop_test_btn:disabled {
                background-color: #1a1a22;
                color: #4a3040;
                border-color: #2a1a28;
            }

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
                background-color: #0b1630;
                border: 1.5px solid #1e3060;
                border-radius: 5px;
                padding: 3px 6px;
                color: #c8d8f8;
                font-size: 12px;
            }

            QLineEdit {
                background-color: #0b1630;
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
    # 辅助组件
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
        name_lbl.setStyleSheet("color: #c8d8ff; font-size: 13px; font-weight: 600; border: none;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #4a6a98; font-size: 11px; border: none;")
        desc_lbl.setWordWrap(True)

        title_box.addWidget(name_lbl)
        title_box.addWidget(desc_lbl)

        status_lbl = QLabel("Not Connected")
        status_lbl.setStyleSheet("color: #ff5a7a; font-weight: 600; border: none;")
        status_lbl.setWordWrap(True)
        setattr(self, status_attr, status_lbl)

        btn_connect = QPushButton("Connect")
        btn_connect.setObjectName("connect_btn")
        btn_connect.setFixedWidth(90)
        setattr(self, connect_btn_attr, btn_connect)
        setattr(self, disconnect_btn_attr, btn_connect)

        top_row.addLayout(title_box, 1)
        top_row.addWidget(btn_connect, 0, Qt.AlignTop)

        select_row = QHBoxLayout()
        select_row.setSpacing(6)

        combo = DarkComboBox(bg="#0b1630", border="#24365e")
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        search_btn = QPushButton("Search")
        search_btn.setObjectName("tool_btn")
        search_btn.setFixedWidth(70)
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
    # 布局
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

        # ---- 左侧滚动区 ----
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.left_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.left_scroll.setMinimumWidth(390)
        self.left_scroll.setMaximumWidth(390)

        left_content = QFrame()
        left_content.setObjectName("left_scroll_content")
        left_content.setMinimumWidth(368)
        left_content.setMaximumWidth(368)
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

        test_select_title = QLabel("✦ TEST ITEM")
        test_select_title.setObjectName("section_title")
        test_select_layout.addWidget(test_select_title)

        self.test_item_combo = DarkComboBox()
        self.test_item_combo.addItem("测试项1: 补偿电容和频率的关系", self.TEST_CAP_FREQ)
        self.test_item_combo.addItem("测试项2: 高低温频偏测试", self.TEST_TEMP_FREQ)
        self.test_item_combo.addItem("测试项3: 时钟性能测试", self.TEST_CLK_PERF)
        test_select_layout.addWidget(self.test_item_combo)

        self.test_item_desc = QLabel("")
        self.test_item_desc.setStyleSheet("color: #7e96bf; font-size: 11px;")
        self.test_item_desc.setWordWrap(True)
        test_select_layout.addWidget(self.test_item_desc)
        left_col.addWidget(test_select_panel)

        # ---- DATA SOURCE (测试项3专用) ----
        self.clk_data_source_panel = QFrame()
        self.clk_data_source_panel.setObjectName("panel")
        ds_layout = QVBoxLayout(self.clk_data_source_panel)
        ds_layout.setContentsMargins(12, 10, 12, 10)
        ds_layout.setSpacing(6)

        ds_title = QLabel("📡 DATA SOURCE")
        ds_title.setObjectName("section_title")
        ds_layout.addWidget(ds_title)

        ds_row = QHBoxLayout()
        ds_row.addWidget(QLabel("Data Source"))
        self.clk_source_combo = DarkComboBox(bg="#0b1630", border="#24365e")
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

        instruments_title = QLabel("🔌 INSTRUMENT CONNECTION")
        instruments_title.setObjectName("section_title")
        instruments_layout.addWidget(instruments_title)

        # 频率仪器选择
        self.freq_instr_frame = QFrame()
        self.freq_instr_frame.setObjectName("config_inner_panel")
        freq_instr_layout = QVBoxLayout(self.freq_instr_frame)
        freq_instr_layout.setContentsMargins(10, 10, 10, 10)
        freq_instr_layout.setSpacing(6)

        freq_type_row = QHBoxLayout()
        freq_type_row.addWidget(QLabel("频率测试仪器"))
        self.freq_instr_type_combo = DarkComboBox()
        self.freq_instr_type_combo.addItems(["MSO64B", "53230A", "DigitMultimeter"])
        freq_type_row.addWidget(self.freq_instr_type_combo, 1)
        freq_instr_layout.addLayout(freq_type_row)

        self.freq_instr_tip = QLabel("根据测试项选择并连接频率测试仪器。")
        self.freq_instr_tip.setStyleSheet("color: #4a6a98; font-size: 11px;")
        self.freq_instr_tip.setWordWrap(True)
        freq_instr_layout.addWidget(self.freq_instr_tip)
        instruments_layout.addWidget(self.freq_instr_frame)

        # MSO64B
        self.mso64b_card = self._create_instrument_card(
            "MSO64B Oscilloscope",
            "频率测量 / 逻辑分析输入",
            "mso64b_combo",
            "mso64b_search_btn",
            "mso64b_connect_btn",
            "mso64b_disconnect_btn",
            "mso64b_status"
        )
        instruments_layout.addWidget(self.mso64b_card)

        mso64b_card_layout = self.mso64b_card.layout()
        mso_ch_row = QHBoxLayout()
        mso_ch_row.setSpacing(6)
        mso_ch_label = QLabel("测量通道")
        mso_ch_label.setStyleSheet("color: #8faad8; font-size: 12px; border: none;")
        self.mso64b_channel_combo = DarkComboBox()
        self.mso64b_channel_combo.addItems(["CH1", "CH2", "CH3", "CH4"])
        self.mso64b_channel_combo.setCurrentIndex(1)
        mso_ch_row.addWidget(mso_ch_label)
        mso_ch_row.addWidget(self.mso64b_channel_combo, 1)
        mso64b_card_layout.addLayout(mso_ch_row)

        # 53230A
        self.counter_card = self._create_instrument_card(
            "53230A Counter",
            "高精度频率计数器",
            "counter_combo",
            "counter_search_btn",
            "counter_connect_btn",
            "counter_disconnect_btn",
            "counter_status"
        )
        instruments_layout.addWidget(self.counter_card)

        # DigitMultimeter
        self.dmm_card = self._create_instrument_card(
            "DigitMultimeter",
            "数字万用表（如支持频率测量）",
            "dmm_combo",
            "dmm_search_btn",
            "dmm_connect_btn",
            "dmm_disconnect_btn",
            "dmm_status"
        )
        instruments_layout.addWidget(self.dmm_card)

        # 温箱
        self.vt6002_card = self._create_instrument_card(
            "VT6002 Chamber",
            "高低温测试温箱",
            "vt6002_combo",
            "vt6002_search_btn",
            "vt6002_connect_btn",
            "vt6002_disconnect_btn",
            "vt6002_status"
        )
        instruments_layout.addWidget(self.vt6002_card)

        left_col.addWidget(instruments_panel)

        # ---- PARAMETERS ----
        params_panel = QFrame()
        params_panel.setObjectName("panel")
        params_layout = QVBoxLayout(params_panel)
        params_layout.setContentsMargins(12, 12, 12, 12)
        params_layout.setSpacing(8)

        self.params_title = QLabel("☷ PARAMETERS")
        self.params_title.setObjectName("section_title")
        params_layout.addWidget(self.params_title)

        self.params_mode_label = QLabel("")
        self.params_mode_label.setStyleSheet("color: #7e96bf; font-size: 11px; font-weight: 700;")
        params_layout.addWidget(self.params_mode_label)

        # -- 测试项1参数 --
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

        # -- 测试项2参数 --
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

        # -- 测试项3参数 --
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
        self.clk_chart_type_combo = DarkComboBox(bg="#0b1630", border="#24365e")
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

        self.required_instr_label = QLabel("")
        self.required_instr_label.setStyleSheet("color: #ffb84d; font-size: 11px;")
        self.required_instr_label.setWordWrap(True)
        params_layout.addWidget(self.required_instr_label)

        left_col.addWidget(params_panel)

        # ---- ACTION ----
        action_panel = QFrame()
        action_panel.setObjectName("action_panel")
        action_layout = QHBoxLayout(action_panel)
        action_layout.setContentsMargins(12, 12, 12, 12)
        action_layout.setSpacing(8)

        self.start_test_btn = QPushButton("▶ START TEST")
        self.start_test_btn.setObjectName("start_test_btn")
        self.start_test_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.stop_test_btn = QPushButton("■")
        self.stop_test_btn.setObjectName("stop_test_btn")
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.hide()

        action_layout.addWidget(self.start_test_btn, 1)
        left_col.addWidget(action_panel)
        left_col.addStretch()

        self.left_scroll.setWidget(left_content)

        # ---- 右侧结果区 ----
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

        log_panel = QFrame()
        log_panel.setObjectName("panel")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(6)

        log_title_row = QHBoxLayout()
        log_title = QLabel("TEST LOG")
        log_title.setObjectName("section_title")
        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("tool_btn")
        self.clear_log_btn.setFixedWidth(60)
        log_title_row.addWidget(log_title)
        log_title_row.addStretch()
        log_title_row.addWidget(self.clear_log_btn)
        log_layout.addLayout(log_title_row)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text, 1)

        right_col.addWidget(chart_panel, 3)
        right_col.addWidget(log_panel, 2)

        body_layout.addWidget(self.left_scroll, 0)
        body_layout.addLayout(right_col, 1)

        page_layout.addLayout(body_layout, 1)
        root_layout.addWidget(self.page, 1)

    # -------------------------------------------------------
    # 图表设置
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
    # 初始化
    # -------------------------------------------------------
    def _init_ui_elements(self):
        self.test_item_combo.currentIndexChanged.connect(self._on_test_item_combo_changed)

        self.mso64b_search_btn.clicked.connect(self._search_mso64b)
        self.mso64b_connect_btn.clicked.connect(self._toggle_mso64b)

        self.counter_search_btn.clicked.connect(self._search_counter)
        self.counter_connect_btn.clicked.connect(self._toggle_counter)

        self.dmm_search_btn.clicked.connect(self._search_dmm)
        self.dmm_connect_btn.clicked.connect(self._toggle_dmm)

        self.vt6002_search_btn.clicked.connect(self._search_vt6002)
        self.vt6002_connect_btn.clicked.connect(self._toggle_vt6002)

        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._stop_test)
        self.export_result_btn.clicked.connect(self.export_result)
        self.clear_log_btn.clicked.connect(self.log_text.clear)

        self.import_csv_btn.clicked.connect(self._import_csv)
        self.clk_source_combo.currentIndexChanged.connect(self._on_clk_source_changed)
        self.clk_chart_type_combo.currentIndexChanged.connect(self._on_clk_chart_type_changed)
        self.clk_n_cycle_spin.valueChanged.connect(self._on_clk_chart_param_changed)
        self.clk_abs_window_spin.valueChanged.connect(self._on_clk_chart_param_changed)
        self.freq_instr_type_combo.currentIndexChanged.connect(self._update_instrument_visibility)

        self._set_test_item(self.TEST_CAP_FREQ)
        self._on_clk_source_changed(self.clk_source_combo.currentIndex())
        self._search_mso64b()
        self._search_counter()
        self._search_dmm()
        self._search_vt6002()

        if DEBUG_MOCK:
            self._append_log("[MOCK] ========== MOCK DEBUG MODE ACTIVE ==========")
            self._append_log("[MOCK] All instruments use simulated data, no real hardware required.")

    # -------------------------------------------------------
    # 测试项切换
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
            self.test_item_desc.setText(
                "测试项1：遍历寄存器最小值到最大值，测试补偿电容设置与频率的关系。"
            )
            self.params_mode_label.setText("CAPACITOR CODE / REGISTER SWEEP")
            self.cap_params_frame.show()
            self.temp_params_frame.hide()
            self.clk_params_frame.hide()
            self.clk_data_source_panel.hide()
            self.freq_instr_frame.show()
            self.start_test_btn.setText("▶ START CAP-FREQ TEST")
            self._start_btn_text = "▶ START CAP-FREQ TEST"
            self.chart_title.setText("补偿电容和频率关系结果")
            self._update_chart_labels("Register Value / Cap Code", "Frequency (Hz)")
            self.required_instr_label.setText(
                "需要仪器：MSO64B（DVM频率测量） + I2C接口（USB-I2C适配器）"
            )
            self._update_top_card_titles("DEFAULT FREQ", "MIN FREQ", "MAX FREQ", "STEP FREQ", "LINEARITY")

        elif test_item == self.TEST_TEMP_FREQ:
            self.test_item_desc.setText(
                "测试项2：遍历温度范围，测试不同温度下的时钟频率和频偏。"
            )
            self.params_mode_label.setText("TEMPERATURE SWEEP")
            self.cap_params_frame.hide()
            self.temp_params_frame.show()
            self.clk_params_frame.hide()
            self.clk_data_source_panel.hide()
            self.freq_instr_frame.show()
            self.start_test_btn.setText("▶ START TEMP OFFSET TEST")
            self._start_btn_text = "▶ START TEMP OFFSET TEST"
            self.chart_title.setText("高低温频偏测试结果")
            self._update_chart_labels("Temperature (°C)", "Frequency (Hz)")
            self.required_instr_label.setText(
                "需要仪器：温箱 + 频率测试仪器（MSO64B / 53230A / DigitMultimeter）"
            )
            self._update_top_card_titles("25℃ FREQ", "MIN FREQ", "MAX FREQ", "PER ℃ FREQ", "LINEARITY")

        elif test_item == self.TEST_CLK_PERF:
            self.test_item_desc.setText(
                "测试项3：连接逻辑分析仪在线采样，或者导入CSV，对时钟进行抖动、频偏等性能分析。"
            )
            self.params_mode_label.setText("CLOCK PERFORMANCE ANALYSIS")
            self.cap_params_frame.hide()
            self.temp_params_frame.hide()
            self.clk_params_frame.show()
            self.clk_data_source_panel.show()
            self.freq_instr_frame.hide()
            self.start_test_btn.setText("▶ START CLK PERFORMANCE TEST")
            self._start_btn_text = "▶ START CLK PERFORMANCE TEST"
            self.chart_title.setText("时钟性能分析结果")
            self._update_chart_labels("Time (s)", "Frequency (Hz)")
            self.required_instr_label.setText(
                "需要仪器：逻辑分析仪（可使用MSO64B）或导入CSV文件"
            )
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
    # 搜索仪器
    def _sync_from_top(self):
        if not self._mso64b_top:
            return
        if self._mso64b_top.is_connected and self._mso64b_top.mso64b:
            self.mso64b = self._mso64b_top.mso64b
            self.is_mso64b_connected = True
            self._set_status_label(self.mso64b_status, "Connected", "ok")
            self._set_btn_connected(self.mso64b_connect_btn)
            self.mso64b_search_btn.setEnabled(False)
            if self._mso64b_top.visa_resource:
                self.mso64b_combo.clear()
                self.mso64b_combo.addItem(self._mso64b_top.visa_resource)
        elif not self.is_mso64b_connected:
            self._set_btn_disconnected(self.mso64b_connect_btn)

    # -------------------------------------------------------
    def _search_mso64b(self):
        if self._mso64b_top and self._mso64b_top.is_connected:
            return
        if DEBUG_MOCK:
            self.mso64b_combo.clear()
            self.mso64b_combo.addItem("[MOCK] TCPIP0::192.168.3.27::inst0::INSTR")
            self._set_status_label(self.mso64b_status, "Available (Mock)", "ok")
            return

        if self._mso64b_search_thread is not None and self._mso64b_search_thread.isRunning():
            return

        self._set_status_label(self.mso64b_status, "Searching...", "warn")
        self.mso64b_search_btn.setEnabled(False)

        worker = _SearchMSO64BWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mso64b_search_done)
        worker.error.connect(lambda e: self._append_log(f"[WARN] MSO64B search: {e}"))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_mso64b_thread_finished())

        self._mso64b_search_thread = thread
        self._mso64b_search_worker = worker
        thread.start()

    def _on_mso64b_thread_finished(self):
        self._mso64b_search_thread = None
        self._mso64b_search_worker = None

    def _on_mso64b_search_done(self, devices):
        self.mso64b_combo.clear()
        default_addr = "TCPIP0::192.168.3.27::inst0::INSTR"
        if devices:
            for d in devices:
                self.mso64b_combo.addItem(d)
            if DEBUG_MOCK and default_addr not in devices:
                self.mso64b_combo.addItem(default_addr)
            self._set_status_label(self.mso64b_status, "Available", "ok")
        else:
            if DEBUG_MOCK:
                self.mso64b_combo.addItem(default_addr)
                self._set_status_label(self.mso64b_status, "Default Device Available (Debug)", "ok")
            else:
                self._set_status_label(self.mso64b_status, "No Device Found", "err")
        self.mso64b_search_btn.setEnabled(True)

    def _search_counter(self):
        if DEBUG_MOCK:
            self.counter_combo.clear()
            self.counter_combo.addItem("[MOCK] TCPIP0::53230A::inst0::INSTR")
            self._set_status_label(self.counter_status, "Available (Mock)", "ok")
            return
        self.counter_combo.clear()
        self.counter_combo.addItem("TCPIP0::53230A::inst0::INSTR")
        self._set_status_label(self.counter_status, "Available", "ok")

    def _search_dmm(self):
        if DEBUG_MOCK:
            self.dmm_combo.clear()
            self.dmm_combo.addItem("[MOCK] USB0::DMM::INSTR")
            self._set_status_label(self.dmm_status, "Available (Mock)", "ok")
            return
        self.dmm_combo.clear()
        self.dmm_combo.addItem("USB0::DMM::INSTR")
        self._set_status_label(self.dmm_status, "Available", "ok")

    def _search_vt6002(self):
        if DEBUG_MOCK:
            self.vt6002_combo.clear()
            self.vt6002_combo.addItem("[MOCK] COM3 - VT6002 Chamber")
            self._set_status_label(self.vt6002_status, "Available (Mock)", "ok")
            return

        if self._vt6002_search_thread is not None and self._vt6002_search_thread.isRunning():
            return

        self._set_status_label(self.vt6002_status, "Searching...", "warn")
        self.vt6002_search_btn.setEnabled(False)
        self.vt6002_connect_btn.setEnabled(False)

        worker = _SearchSerialWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_vt6002_search_done)
        worker.error.connect(self._on_vt6002_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_vt6002_thread_finished())

        self._vt6002_search_thread = thread
        self._vt6002_search_worker = worker
        thread.start()

    def _on_vt6002_thread_finished(self):
        self._vt6002_search_thread = None
        self._vt6002_search_worker = None

    def _on_vt6002_search_done(self, ports):
        self.vt6002_combo.clear()
        if ports:
            for port in ports:
                self.vt6002_combo.addItem(port)
            self._set_status_label(self.vt6002_status, "Available", "ok")
            self.vt6002_connect_btn.setEnabled(True)
        else:
            self.vt6002_combo.addItem("No serial ports found")
            self._set_status_label(self.vt6002_status, "Not Available", "err")
            self.vt6002_connect_btn.setEnabled(False)
        self.vt6002_search_btn.setEnabled(True)

    def _on_vt6002_search_error(self, err):
        self._append_log(f"[WARN] VT6002 search error: {err}")
        self._set_status_label(self.vt6002_status, f"Error: {err}", "err")
        self.vt6002_search_btn.setEnabled(True)
        self.vt6002_connect_btn.setEnabled(False)

    # -------------------------------------------------------
    # 连接 / 断开
    # -------------------------------------------------------
    def _toggle_mso64b(self):
        if self.is_mso64b_connected:
            self._disconnect_mso64b()
        else:
            self._connect_mso64b()

    def _connect_mso64b(self):
        self._set_status_label(self.mso64b_status, "Connecting...", "warn")
        self.mso64b_connect_btn.setEnabled(False)
        if DEBUG_MOCK:
            self.mso64b = None
            self.is_mso64b_connected = True
            self._set_status_label(self.mso64b_status, "Connected: [MOCK] MSO64B", "ok")
            self._set_btn_connected(self.mso64b_connect_btn)
            self.mso64b_search_btn.setEnabled(False)
            self._append_log("[MOCK] MSO64B connected (mock mode)")
            return
        try:
            from instruments.scopes.tektronix.mso64b import MSO64B
            addr = self.mso64b_combo.currentText().strip()
            if not addr:
                raise ValueError("未选择MSO64B仪器地址，请先搜索或手动输入")
            self._append_log(f"[INFO] Connecting to MSO64B: {addr}")
            self.mso64b = MSO64B(addr)
            idn = self.mso64b.identify_instrument()
            self.is_mso64b_connected = True
            self._set_status_label(self.mso64b_status, f"Connected: {idn[:30]}", "ok")
            self._set_btn_connected(self.mso64b_connect_btn)
            self.mso64b_search_btn.setEnabled(False)
            self._append_log(f"[INFO] MSO64B connected: {idn}")

            if self._mso64b_top:
                self._mso64b_top.connect_instrument(addr, self.mso64b)
        except Exception as e:
            self._append_log(f"[ERROR] MSO64B connection failed: {e}")
            self._set_status_label(self.mso64b_status, f"Error: {e}", "err")
            self._set_btn_disconnected(self.mso64b_connect_btn)

    def _disconnect_mso64b(self):
        try:
            if self._mso64b_top:
                self._mso64b_top.disconnect()
                self.mso64b = None
            else:
                if self.mso64b:
                    self.mso64b.disconnect()
                    self.mso64b = None
        except Exception:
            pass
        self.is_mso64b_connected = False
        self._set_status_label(self.mso64b_status, "Disconnected", "err")
        self._set_btn_disconnected(self.mso64b_connect_btn)
        self.mso64b_search_btn.setEnabled(True)

    def _toggle_counter(self):
        if self.counter_connect_btn.text() == "Disconnect":
            self._disconnect_counter()
        else:
            self._connect_counter()

    def _connect_counter(self):
        self._set_status_label(self.counter_status, f"Connected: {self.counter_combo.currentText()}", "ok")
        self._set_btn_connected(self.counter_connect_btn)

    def _disconnect_counter(self):
        self._set_status_label(self.counter_status, "Disconnected", "err")
        self._set_btn_disconnected(self.counter_connect_btn)

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

    def _toggle_vt6002(self):
        if self.is_vt6002_connected:
            self._disconnect_vt6002()
        else:
            self._connect_vt6002()

    def _connect_vt6002(self):
        self._set_status_label(self.vt6002_status, "Connecting...", "warn")
        self.vt6002_connect_btn.setEnabled(False)
        if DEBUG_MOCK:
            self.vt6002 = None
            self.is_vt6002_connected = True
            self._set_status_label(self.vt6002_status, "Connected: [MOCK] VT6002", "ok")
            self._set_btn_connected(self.vt6002_connect_btn)
            self.vt6002_search_btn.setEnabled(False)
            self._append_log("[MOCK] VT6002 connected (mock mode)")
            return
        try:
            from instruments.chambers.vt6002_chamber import VT6002
            port_str = self.vt6002_combo.currentText()
            device_port = port_str.split()[0]
            self._append_log(f"[INFO] Connecting to VT6002: {device_port}")
            self.vt6002 = VT6002(device_port)
            self.is_vt6002_connected = True
            self._set_status_label(self.vt6002_status, "Connected", "ok")
            self._set_btn_connected(self.vt6002_connect_btn)
            self.vt6002_search_btn.setEnabled(False)
            self._append_log(f"[INFO] VT6002 connected: {device_port}")
        except Exception as e:
            self._append_log(f"[ERROR] VT6002 connection failed: {e}")
            self._set_status_label(self.vt6002_status, f"Error: {e}", "err")
            self._set_btn_disconnected(self.vt6002_connect_btn)

    def _disconnect_vt6002(self):
        self._set_status_label(self.vt6002_status, "Disconnecting...", "warn")
        self.vt6002_connect_btn.setEnabled(False)
        try:
            if self.vt6002:
                self.vt6002.close()
                self.vt6002 = None
            self.is_vt6002_connected = False
            self._set_status_label(self.vt6002_status, "Disconnected", "err")
            self._set_btn_disconnected(self.vt6002_connect_btn)
            self.vt6002_search_btn.setEnabled(True)
        except Exception as e:
            self._append_log(f"[ERROR] VT6002 disconnect failed: {e}")
            self._set_status_label(self.vt6002_status, f"Error: {e}", "err")
            self._set_btn_connected(self.vt6002_connect_btn)

    # -------------------------------------------------------
    # 辅助方法
    # -------------------------------------------------------
    def _set_status_label(self, label, text, state):
        label.setText(text)
        color_map = {"ok": "#18a067", "warn": "#d4a514", "err": "#d14b72"}
        color = color_map.get(state, "#c8c8c8")
        label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _set_btn_connected(self, btn):
        btn.setText("Disconnect")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3a2a;
                border: 1px solid #18a067;
                border-radius: 4px;
                color: #18a067;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #1e4a34; }
        """)
        btn.setEnabled(True)

    def _set_btn_disconnected(self, btn):
        btn.setText("Connect")
        btn.setStyleSheet("""
            QPushButton {
                background-color: #1a3060;
                color: #4a9fff;
                border: 1px solid #2a4a90;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                min-height: 28px;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #1e3a80;
            }
        """)
        btn.setEnabled(True)

    def _append_log(self, text):
        self.log_text.append(text)

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

    def _validate_before_test(self):
        if DEBUG_MOCK:
            self._append_log("[MOCK] Skipping instrument validation (mock mode)")
            return

        if self.current_test_item == self.TEST_CAP_FREQ:
            if not self.is_mso64b_connected:
                raise ValueError("测试项1需要先连接MSO64B用于频率测量")
            if self.reg_min.value() > self.reg_max.value():
                raise ValueError("Register Min 不能大于 Register Max")

        elif self.current_test_item == self.TEST_TEMP_FREQ:
            if not self.is_vt6002_connected:
                raise ValueError("测试项2需要先连接VT6002温箱")
            if not self.is_mso64b_connected:
                raise ValueError("测试项2需要先连接MSO64B用于频率测量")
            if self.temp_step.value() <= 0:
                raise ValueError("步进温度必须大于0")

        elif self.current_test_item == self.TEST_CLK_PERF:
            clk_source = self.clk_source_combo.currentText()
            if clk_source == "MSO64B":
                if not self.is_mso64b_connected:
                    raise ValueError("MSO64B模式需要先连接MSO64B")
            elif clk_source == "DSLogic":
                pass
            elif clk_source == "Import CSV":
                if not self.csv_file_path:
                    raise ValueError("请选择CSV文件")

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
    # 测试控制
    # -------------------------------------------------------
    def _on_start_or_stop(self):
        if self._test_thread is not None:
            self._stop_test()
        else:
            self._start_test()

    def _start_test(self):
        if self._test_thread is not None:
            QMessageBox.information(self, "Info", "测试正在进行中")
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

        self._append_log(f"[INFO] Starting {self.current_test_item} test...")

        self._test_thread = QThread()
        self._test_worker = _CLKTestWorker(
            self.current_test_item, config,
            mso64b=self.mso64b,
            vt6002=self.vt6002,
            mock_mode=DEBUG_MOCK,
        )
        self._test_worker.moveToThread(self._test_thread)

        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.log.connect(self._append_log)
        self._test_worker.progress.connect(self._on_test_progress)
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
        if running:
            self.start_test_btn.setText("■ STOP")
            self.start_test_btn.setObjectName("stop_test_btn")
        else:
            self.start_test_btn.setText(self._start_btn_text)
            self.start_test_btn.setObjectName("start_test_btn")
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.start_test_btn.update()

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
    # 结果显示
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
    # 导出 / 导入
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