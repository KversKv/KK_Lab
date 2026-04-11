#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import math

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "lib", "i2c"))

from log_config import get_logger

from ui.widgets.dark_combobox import DarkComboBox
from ui.styles import SCROLLBAR_STYLE
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QGridLayout, QSpinBox, QDoubleSpinBox, QFrame,
    QTextEdit, QProgressBar, QSizePolicy,
    QApplication, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer, QMargins, QPointF
from PySide6.QtGui import QFont
import time
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C
from i2c_interface_x64 import I2CInterface
from Bes_I2CIO_Interface import I2CSpeedMode, I2CWidthFlag

try:
    from PySide6.QtCharts import (
        QChart, QChartView, QLineSeries, QValueAxis, QScatterSeries
    )
    from PySide6.QtGui import QPainter, QColor, QPen
    HAS_QTCHARTS = True
except Exception:
    HAS_QTCHARTS = False

logger = get_logger(__name__)

SAVE_DEBUG_DLOG_FLAG = False

ITERM_REGISTER_MAP = {
    0: {"code": 0x00, "current_ma": 60},
    1: {"code": 0x01, "current_ma": 120},
    2: {"code": 0x02, "current_ma": 180},
    3: {"code": 0x03, "current_ma": 240},
    4: {"code": 0x04, "current_ma": 300},
    5: {"code": 0x05, "current_ma": 360},
    6: {"code": 0x06, "current_ma": 420},
    7: {"code": 0x07, "current_ma": 480},
}


def _fmt_val(value, min_decimals=4, sig_digits=4):
    if value == 0:
        return f"{value:.{min_decimals}f}"
    abs_val = abs(value)
    magnitude = -int(math.floor(math.log10(abs_val)))
    decimals = max(min_decimals, magnitude + sig_digits - 1)
    decimals = min(decimals, 10)
    return f"{value:.{decimals}f}"


class _ItermTestWorker(QObject):
    log_message = Signal(str)
    progress = Signal(int)
    result_row = Signal(dict)
    test_finished = Signal(bool)
    chart_clear = Signal()
    chart_series_data = Signal(list, list, float, float, float)
    traverse_chart_point = Signal(float, float)
    traverse_chart_clear = Signal()
    traverse_result_update = Signal(dict)

    def __init__(self, n6705c, config):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._stop_flag = False
        self._suppress_inner_progress = False
        self._suppress_inner_chart = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        test_item = self._cfg.get("test_item", "Single Iterm Test")
        if test_item == "Single Iterm Test":
            self._run_single()
        else:
            self._run_traverse()

    def _run_single(self):
        try:
            vbat_channel = self._cfg["vbat_channel"]
            current_channel = self._cfg["measure_channel"]
            voreg = self._cfg.get("voreg", 4.2)
            average_time = self._cfg.get("average_time_ms", 100) / 1000.0

            msg = (f"Single Iterm Test: VBAT CH{vbat_channel}, "
            f"Current CH{current_channel}, Voreg={voreg:.2f}V, "
            f"Average Time={average_time*1000.0:.3f}ms")
            logger.info(msg)
            self.log_message.emit(f"[TEST] {msg}")
            iterm = self.single_iterm_test(vbat_channel, current_channel, voreg, average_time)

            if iterm is not None:
                msg = f"[RESULT] Iterm = {_fmt_val(iterm * 1000.0)} mA"
                logger.info(msg)
                self.log_message.emit(msg)
                self.result_row.emit({
                    "code": "---",
                    "measured_ma": f"{abs(iterm) * 1000.0:.4f}",
                    "result": "DONE",
                })
            self.test_finished.emit(True)
        except Exception as e:
            logger.error(f"{e}")
            self.log_message.emit(f"[ERROR] {e}")
            self.test_finished.emit(False)

    def _run_traverse(self):
        try:
            device_addr = self._cfg["device_addr"]
            iterm_reg = self._cfg["iterm_reg"]
            iic_width = self._cfg["iic_width"]
            vbat_channel = self._cfg["vbat_channel"]
            current_channel = self._cfg["measure_channel"]
            voreg = self._cfg.get("voreg", 4.2)
            average_time = self._cfg.get("average_time_ms", 100) / 1000.0
            msb = self._cfg["msb"]
            lsb = self._cfg["lsb"]
            min_code = self._cfg["min_code"]
            max_code = self._cfg["max_code"]

            self.traverse_iterm_test(
                device_addr, iterm_reg, iic_width,
                vbat_channel, current_channel, voreg, average_time,
                msb, lsb, min_code, max_code,
            )
            self.test_finished.emit(True)
        except Exception as e:
            logger.error(f"{e}")
            self.log_message.emit(f"[ERROR] {e}")
            self.test_finished.emit(False)
        finally:
            self._suppress_inner_progress = False
            self._suppress_inner_chart = False

    def single_iterm_test(self, vbat_channel, current_channel, voreg, average_time):
        from instruments.power.keysight.n6705c_datalog_process import parse_dlog_binary

        arb_v0 = voreg - 0.2
        arb_v1 = voreg + 0.1
        arb_t0 = 0
        arb_t1 = 5
        arb_t2 = 0
        arb_steps = 500
        arb_total_time = arb_t0 + arb_t1 + arb_t2
        sample_period_s = 0.00004
        logger.debug(
            f"ARB Staircase: V0={arb_v0:.3f}V -> V1={arb_v1:.3f}V, "
            f"steps={arb_steps}, total_time={arb_total_time:.1f}s"
        )

        msg = "Step 1: Setting Vbat to 3V to ensure DUT enters charging state..."
        logger.debug(msg)
        self._n6705c.set_voltage(vbat_channel, 3.0)
        self._n6705c.channel_on(vbat_channel)
        time.sleep(0.1)

        if self._stop_flag:
            logger.warning("Stopped by user.")
            self.log_message.emit("[TEST] Stopped by user.")
            return None

        msg = "Step 2: Clearing all channel ARB configurations..."
        logger.debug(msg)
        self._n6705c.clear_arb_all_channels()

        msg = "Step 3: Configuring ARB staircase waveform..."
        logger.debug(msg)
        self._n6705c.set_arb_staircase(
            vbat_channel,
            v0=arb_v0, v1=arb_v1,
            t0=arb_t0, t1=arb_t1, t2=arb_t2,
            steps=arb_steps
        )
        self._n6705c.set_arb_continuous(vbat_channel, flag=False)
        self._n6705c.arb_on(vbat_channel)

        msg = "Step 4: Configuring Datalog for highest precision recording..."
        logger.debug(msg)
        self._n6705c.instr.write("*CLS")
        try:
            self._n6705c.instr.write("ABOR:DLOG")
        except Exception:
            pass

        for ch in range(1, 5):
            self._n6705c.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
            self._n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")

        self._n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT ON,(@{vbat_channel})")
        self._n6705c.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{current_channel})")
        self._n6705c.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{current_channel})")

        self._n6705c.instr.write(f"SENS:DLOG:TIME {arb_total_time}")
        self._n6705c.instr.write(f"SENS:DLOG:PER {sample_period_s}")
        self._n6705c.instr.write("TRIG:DLOG:SOUR IMM")

        dlog_file = "internal:\\iterm_test.dlog"

        msg = "Step 5: Starting ARB and Datalog simultaneously..."
        logger.debug(msg)
        self._n6705c.instr.write(f'INIT:DLOG "{dlog_file}"')
        self._n6705c.arb_run()

        msg = f"Step 6: Waiting for ARB and Datalog to complete ({arb_total_time:.1f}s)..."
        logger.debug(msg)
        wait_end = time.time() + arb_total_time + 5
        while time.time() < wait_end:
            if self._stop_flag:
                logger.warning("Stopped by user.")
                self.log_message.emit("[TEST] Stopped by user.")
                return None
            elapsed = time.time() - (wait_end - arb_total_time - 5)
            pct = min(int(elapsed / arb_total_time * 90), 90)
            if not self._suppress_inner_progress:
                self.progress.emit(pct)
            time.sleep(0.5)

        msg = "Step 7: Downloading Datalog data (dlog)..."
        logger.debug(msg)
        if not self._suppress_inner_progress:
            self.progress.emit(92)

        raw_dlog = self._n6705c.read_mmem_data(dlog_file)

        if not isinstance(raw_dlog, bytes) or len(raw_dlog) == 0:
            logger.error("Failed to download dlog data.")
            self.log_message.emit("[ERROR] Failed to download dlog data.")
            return None

        logger.debug(f"Downloaded {len(raw_dlog)} bytes of dlog data.")

        msg = "Step 8: Restoring ARB trigger source..."
        logger.debug(msg)
        self._n6705c.restore_arb_trigger_source()

        if SAVE_DEBUG_DLOG_FLAG:
            try:
                from datetime import datetime
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                results_dir = os.path.join(base_dir, "Results", "iterm_test")
                os.makedirs(results_dir, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                dlog_path = os.path.join(results_dir, f"iterm_{ts}.dlog")
                with open(dlog_path, "wb") as f:
                    f.write(raw_dlog)
                logger.debug(f"Dlog saved to {dlog_path}")
            except Exception as e:
                logger.info(f"Failed to save dlog: {e}")

        volt_channels = [vbat_channel]
        curr_channels = [current_channel]
        all_data = parse_dlog_binary(
            raw_dlog, curr_channels, volt_channels,
            "", sample_period_s
        )

        if not all_data:
            logger.error("Failed to parse dlog data.")
            self.log_message.emit("[ERROR] Failed to parse dlog data.")
            return None

        v_label = f"CH{vbat_channel} V"
        i_label = f"CH{current_channel} I"

        if i_label not in all_data:
            logger.error(f"Current data for CH{current_channel} not found in dlog.")
            self.log_message.emit(f"[ERROR] Current data for CH{current_channel} not found in dlog.")
            return None

        timestamps = all_data[i_label]["time"]
        currents_mA = all_data[i_label]["values"]
        currents = [c / 1000.0 for c in currents_mA]

        voltages = None
        if v_label in all_data:
            voltages_mV = all_data[v_label]["values"]
            voltages = [v / 1000.0 for v in voltages_mV]

        logger.debug(
            f"Datalog parsed: {len(timestamps)} points, "
            f"duration={timestamps[-1]:.2f}s"
        )

        if not self._suppress_inner_chart:
            self.chart_clear.emit()
        if not self._suppress_inner_progress:
            self.progress.emit(95)

        msg = "Step 9: Analyzing current curve to find termination current..."
        logger.debug(msg)

        iterm = self._analyze_iterm_from_curve(timestamps, currents, voltages, voreg, average_time)

        if not self._suppress_inner_progress:
            self.progress.emit(100)
        return iterm

    def _analyze_iterm_from_curve(self, timestamps, currents, voltages, voreg, average_time):
        if len(currents) < 10:
            logger.error("Not enough data points to analyse.")
            self.log_message.emit("[ERROR] Not enough data points to analyse.")
            if not self._suppress_inner_chart:
                self.chart_series_data.emit(timestamps, currents, -1.0, 0.0, 0.0)
            return None

        total = len(currents)
        abs_currents = [abs(c) for c in currents]

        block_size = 500
        n_blocks = total // block_size
        block_avgs = []
        for b in range(n_blocks):
            s = b * block_size
            block_avgs.append(sum(abs_currents[s:s + block_size]) / block_size)

        post_term_block = None
        for b in range(n_blocks):
            if block_avgs[b] < 1e-3:
                post_term_block = b
                break

        if post_term_block is None:
            logger.info("No post-termination region found.")
            self.log_message.emit("[WARN] No post-termination region found.")
            if not self._suppress_inner_chart:
                self.chart_series_data.emit(timestamps, currents, -1.0, 0.0, 0.0)
            return None

        plateau_blocks = block_avgs[post_term_block:post_term_block + 10]
        plateau_level = sum(plateau_blocks) / len(plateau_blocks)
        active_threshold = plateau_level * 10

        logger.debug(
            f"Post-term plateau: {plateau_level * 1000:.4f} mA, "
            f"active threshold: {active_threshold * 1000:.4f} mA"
        )

        t_term_idx = None
        for i in range(total - 1, 0, -1):
            if abs_currents[i] > active_threshold:
                t_term_idx = i
                break

        if t_term_idx is None:
            logger.info("No termination point found in current curve.")
            self.log_message.emit("[WARN] No termination point found in current curve.")
            if not self._suppress_inner_chart:
                self.chart_series_data.emit(timestamps, currents, -1.0, 0.0, 0.0)
            return None

        t_term = timestamps[t_term_idx]
        v_term = voltages[t_term_idx] if voltages and t_term_idx < len(voltages) else 0.0
        logger.debug(
            f"Termination point found at index {t_term_idx}, "
            f"t={t_term:.6f}s, I={currents[t_term_idx]:.6f}A, V={v_term:.4f}V"
        )

        dt = timestamps[1] - timestamps[0] if total > 1 else 1.0
        iterm_points = max(1, int(average_time / dt))
        iterm_start = max(0, t_term_idx - iterm_points)
        iterm_vals = currents[iterm_start:t_term_idx + 1]
        iterm = sum(iterm_vals) / len(iterm_vals) if iterm_vals else 0.0

        logger.debug(
            f"Iterm calculated from {len(iterm_vals)} points "
            f"in [{timestamps[iterm_start]:.6f}s, {t_term:.6f}s] "
            f"(avg window: {average_time*1000:.1f}ms): "
            f"{_fmt_val(iterm * 1000.0)} mA"
        )

        if not self._suppress_inner_chart:
            self.chart_series_data.emit(timestamps, currents, t_term, iterm, v_term)

        return iterm

    def traverse_iterm_test(
        self, device_addr, iterm_reg, iic_width,
        vbat_channel, current_channel, voreg, average_time,
        msb, lsb, min_code, max_code,
    ):
        i2c = I2CInterface()
        self._i2c = i2c

        bit_count = msb - lsb + 1
        mask = (1 << bit_count) - 1
        max_code = min(max_code, mask)
        min_code = max(min_code, 0)

        default_reg = i2c.read(device_addr, iterm_reg, iic_width)
        data_base = default_reg & (~(mask << lsb))
        default_code = (default_reg >> lsb) & mask

        total_points = max_code - min_code + 1
        if total_points <= 0:
            logger.error("Invalid code range.")
            self.log_message.emit("[ERROR] Invalid code range.")
            return

        msg = (f"Traverse Iterm Test: Device=0x{device_addr:02X}, "
               f"Reg=0x{iterm_reg:02X}, MSB={msb}, LSB={lsb}")
        logger.info(msg)
        self.log_message.emit(f"[TEST] {msg}")
        msg = f"Code range: 0x{min_code:X} ~ 0x{max_code:X} ({total_points} points)"
        logger.info(msg)
        self.log_message.emit(f"[TEST] {msg}")

        hex_width = len(f"{max_code:X}")

        self.traverse_chart_clear.emit()

        codes = []
        iterms = []
        default_iterm = None

        self._suppress_inner_progress = True
        self._suppress_inner_chart = True
        default_iterm_val = self.single_iterm_test(vbat_channel, current_channel, voreg, average_time)
        if default_iterm_val is not None:
            default_iterm = abs(default_iterm_val) * 1000.0
            self.log_message.emit(f"[TEST] Default Iterm: {default_iterm:.4f} mA (code=0x{default_code:X})")
        write_reg = data_base | (min_code << lsb)
        i2c.write(device_addr, iterm_reg, min_code, iic_width)
        time.sleep(1)
        for idx, code in enumerate(range(min_code, max_code + 1)):
            if self._stop_flag:
                logger.warning("Stopped by user.")
                self.log_message.emit("[TEST] Stopped by user.")
                break

            write_reg = data_base | (code << lsb)
            i2c.write(device_addr, iterm_reg, write_reg, iic_width)
            logger.debug(f"Code=0x{code:0{hex_width}X}, writing reg=0x{write_reg:04X}")
            time.sleep(0.2)

            iterm = self.single_iterm_test(vbat_channel, current_channel, voreg, average_time)

            if iterm is not None:
                iterm_ma = abs(iterm) * 1000.0
                codes.append(code)
                iterms.append(iterm_ma)

                self.traverse_chart_point.emit(float(code), iterm_ma)

                self.result_row.emit({
                    "code": f"0x{code:0{hex_width}X}",
                    "measured_ma": f"{iterm_ma:.4f}",
                    "result": "DONE",
                })

                msg = f"Code=0x{code:0{hex_width}X}: Iterm={iterm_ma:.4f}mA"
                logger.info(msg)
                self.log_message.emit(f"[DATA] {msg}")
            else:
                msg = f"Code=0x{code:0{hex_width}X}: Iterm measurement failed."
                logger.info(msg)
                self.log_message.emit(f"[WARN] {msg}")

            result = {"progress": int((idx + 1) / total_points * 100)}
            if default_iterm is not None:
                result["default_value"] = default_iterm
                result["default_code"] = default_code
            if len(iterms) >= 1:
                result["min_value"] = min(iterms)
                result["max_value"] = max(iterms)
                result["valid_min_code"] = codes[0]
                result["valid_max_code"] = codes[-1]
            if len(iterms) >= 2:
                avg_step = (iterms[-1] - iterms[0]) / (len(iterms) - 1)
                result["step_value"] = avg_step

                full_scale = iterms[-1] - iterms[0]
                if abs(full_scale) > 1e-9:
                    n = len(iterms)
                    ideal_step = full_scale / (n - 1)
                    max_dev = 0.0
                    for j in range(n):
                        ideal_v = iterms[0] + ideal_step * j
                        dev = abs(iterms[j] - ideal_v)
                        if dev > max_dev:
                            max_dev = dev
                    result["linearity"] = max_dev / abs(full_scale) * 100.0
                else:
                    result["linearity"] = 0.0

            result["unit"] = "mA"
            self.traverse_result_update.emit(result)

            pct = int((idx + 1) / total_points * 100)
            self.progress.emit(pct)

        i2c.write(device_addr, iterm_reg, default_reg, iic_width)
        logger.info("Register restored to default value.")
        self.log_message.emit("[TEST] Register restored to default value.")



class _BackgroundTaskWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._func(*self._args, **self._kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CardFrame(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(12)

        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.main_layout.addWidget(self.title_label)
        else:
            self.title_label = None


class ItermTestUI(QWidget):
    connection_status_changed = Signal(bool)

    def __init__(self, n6705c_top=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []

        self.is_test_running = False
        self.test_thread = None
        self.test_worker = None
        self._bg_thread = None
        self._bg_worker = None
        self._export_data = []
        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0
        self._traverse_min_x = float('inf')
        self._traverse_max_x = float('-inf')
        self._traverse_min_y = float('inf')
        self._traverse_max_y = float('-inf')

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()
        self._sync_from_top()

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)

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
            QFrame#panelFrame {
                background-color: #08132d;
                border: 1px solid #16274d;
                border-radius: 18px;
            }
            QFrame#cardFrame {
                background-color: #071127;
                border: 1px solid #1a2b52;
                border-radius: 14px;
            }
            QLabel#cardTitle {
                font-size: 11px;
                font-weight: 700;
                color: #f4f7ff;
                letter-spacing: 0.5px;
                background-color: transparent;
            }
            QLabel#sectionTitle {
                font-size: 12px;
                font-weight: 700;
                color: #f4f7ff;
                background-color: transparent;
            }
            QLabel#fieldLabel {
                color: #8eb0e3;
                font-size: 11px;
                background-color: transparent;
            }
            QLabel#statusOk {
                color: #15d1a3;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusWarn {
                color: #ffb84d;
                font-weight: 600;
                background-color: transparent;
            }
            QLabel#statusErr {
                color: #ff5e7a;
                font-weight: 600;
                background-color: transparent;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                border-radius: 8px;
                padding: 6px 10px;
                selection-background-color: #4f46e5;
            }
            QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4cc9f0;
            }
            QComboBox { padding-right: 24px; }
            QComboBox::drop-down {
                border: none; width: 22px; background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #0a1733;
                color: #eaf2ff;
                border: 1px solid #27406f;
                selection-background-color: #334a7d;
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
            QPushButton:pressed { background-color: #0d1a37; }
            QPushButton:disabled {
                background-color: #0b1430;
                color: #5c7096;
                border: 1px solid #1a2850;
            }
            QPushButton#primaryStartBtn {
                min-height: 36px;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 800;
                color: white;
                border: 1px solid #645bff;
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #5b5cf6, stop:1 #6a38ff
                );
            }
            QPushButton#primaryStartBtn:hover {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6b6cff, stop:1 #7d4cff
                );
            }
            QPushButton#stopBtn {
                background-color: #4a1020;
                border: 1px solid #d9485f;
                color: #ffd5db;
            }
            QPushButton#stopBtn:hover { background-color: #5a1326; }
            QPushButton#smallActionBtn {
                min-height: 28px;
                padding: 4px 10px;
                border-radius: 8px;
                background-color: #13254b;
                color: #dce7ff;
            }
            QPushButton#dynamicConnectBtn {
                min-height: 34px;
                border-radius: 10px;
                padding: 6px 14px;
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
            QPushButton#exportBtn {
                min-height: 28px;
                padding: 4px 12px;
                border-radius: 8px;
                background-color: #16284f;
                color: #dfe8ff;
            }
            QFrame#chartContainer, QFrame#logContainer {
                background-color: #09142e;
                border: 1px solid #1a2d57;
                border-radius: 16px;
            }
            QTextEdit#logEdit {
                background-color: #061022;
                border: 1px solid #1f315d;
                border-radius: 8px;
                color: #7cecc8;
                font-family: Consolas, "Courier New", monospace;
                font-size: 11px;
            }
            QProgressBar {
                background-color: #152749;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: #b7c8ea;
                min-height: 8px;
                max-height: 8px;
            }
            QProgressBar::chunk {
                background-color: #5b5cf6;
                border-radius: 4px;
            }
            QLabel#metricLabel {
                color: #9db6db;
                font-size: 12px;
                background-color: transparent;
            }
            QLabel#metricValue {
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                background-color: transparent;
            }
            QFrame#miniStatCard {
                background-color: #0a1733;
                border: 1px solid #1b315f;
                border-radius: 10px;
            }
        """ + SCROLLBAR_STYLE)

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        self.page_title = QLabel("\U0001f50b Iterm Test")
        self.page_title.setObjectName("pageTitle")

        self.page_subtitle = QLabel(
            "Validate Charger IC termination current settings across all Iterm codes."
        )
        self.page_subtitle.setObjectName("pageSubtitle")

        header_layout.addWidget(self.page_title)
        header_layout.addWidget(self.page_subtitle)
        root_layout.addLayout(header_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)
        root_layout.addLayout(content_layout, 1)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("panelFrame")
        self.left_panel.setFixedWidth(275)

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(18, 18, 18, 18)
        left_layout.setSpacing(16)

        self.connection_card = CardFrame("\u26a1 N6705C CONNECTION")
        self._build_connection_card()
        left_layout.addWidget(self.connection_card)

        self.test_item_card = CardFrame("\u2630 TEST ITEM")
        self._build_test_item_card()
        left_layout.addWidget(self.test_item_card)

        self.test_config_card = CardFrame("\u2637 TEST CONFIG")
        self._build_test_config_card()
        left_layout.addWidget(self.test_config_card)

        self.param_card = CardFrame("\u21c4 REGISTER RANGE")
        self._build_param_card()
        left_layout.addWidget(self.param_card)

        left_layout.addStretch()

        self.start_test_btn = QPushButton("\u25b6 START ITERM TEST")
        self.start_test_btn.setObjectName("primaryStartBtn")
        left_layout.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("\u25a0 STOP")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.hide()

        content_layout.addWidget(self.left_panel)

        right_layout = QVBoxLayout()
        right_layout.setSpacing(14)
        content_layout.addLayout(right_layout, 1)

        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("chartContainer")
        chart_outer_layout = QVBoxLayout(self.chart_frame)
        chart_outer_layout.setContentsMargins(16, 16, 16, 16)
        chart_outer_layout.setSpacing(10)

        chart_header_layout = QHBoxLayout()
        self.chart_title = QLabel("\u2248 Current vs Time")
        self.chart_title.setObjectName("sectionTitle")
        chart_header_layout.addWidget(self.chart_title)
        chart_header_layout.addStretch()

        self.export_result_btn = QPushButton("\u21e9 Export CSV")
        self.export_result_btn.setObjectName("exportBtn")
        chart_header_layout.addWidget(self.export_result_btn)

        chart_outer_layout.addLayout(chart_header_layout)

        self.chart_widget = self._create_chart_widget()
        chart_outer_layout.addWidget(self.chart_widget, 1)

        self.single_stat_layout = QHBoxLayout()
        self.single_stat_layout.setSpacing(10)

        self.iterm_card = self._create_mini_stat("Iterm", "---")
        self.voreg_card = self._create_mini_stat("Voreg", "---")

        self.single_stat_layout.addWidget(self.iterm_card["frame"])
        self.single_stat_layout.addWidget(self.voreg_card["frame"])

        self.traverse_stat_layout = QHBoxLayout()
        self.traverse_stat_layout.setSpacing(10)

        self.default_iterm_card = self._create_mini_stat("默认值", "---")
        self.min_iterm_card = self._create_mini_stat("最小值", "---")
        self.max_iterm_card = self._create_mini_stat("最大值", "---")
        self.step_iterm_card = self._create_mini_stat("步进", "---")
        self.linearity_iterm_card = self._create_mini_stat("线性度", "---")

        self.traverse_stat_layout.addWidget(self.default_iterm_card["frame"])
        self.traverse_stat_layout.addWidget(self.min_iterm_card["frame"])
        self.traverse_stat_layout.addWidget(self.max_iterm_card["frame"])
        self.traverse_stat_layout.addWidget(self.step_iterm_card["frame"])
        self.traverse_stat_layout.addWidget(self.linearity_iterm_card["frame"])

        self.stat_container = QWidget()
        self.stat_container.setStyleSheet("background: transparent;")
        self.stat_container_layout = QVBoxLayout(self.stat_container)
        self.stat_container_layout.setContentsMargins(0, 0, 0, 0)
        self.stat_container_layout.setSpacing(0)
        self.stat_container_layout.addLayout(self.single_stat_layout)
        self.stat_container_layout.addLayout(self.traverse_stat_layout)

        self._set_traverse_stat_visible(False)

        chart_outer_layout.addWidget(self.stat_container)

        right_layout.addWidget(self.chart_frame, 4)

        self.log_frame = QFrame()
        self.log_frame.setObjectName("logContainer")
        log_layout = QVBoxLayout(self.log_frame)
        log_layout.setContentsMargins(16, 16, 16, 16)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()
        log_title = QLabel("\u2299 Execution Logs")
        log_title.setObjectName("sectionTitle")
        log_header.addWidget(log_title)
        log_header.addStretch()

        self.progress_text_label = QLabel("0% Complete")
        self.progress_text_label.setObjectName("fieldLabel")
        log_header.addWidget(self.progress_text_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(120)
        log_header.addWidget(self.progress_bar)

        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("smallActionBtn")
        log_header.addWidget(self.clear_log_btn)

        log_layout.addLayout(log_header)

        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)
        log_layout.addWidget(self.log_edit)

        right_layout.addWidget(self.log_frame, 1)

    def _build_connection_card(self):
        layout = self.connection_card.main_layout

        self.system_status_label = QLabel("\u25cf Ready")
        self.system_status_label.setObjectName("statusOk")
        layout.addWidget(self.system_status_label)

        self.instrument_info_label = QLabel("USB0::0x0957::0x0F07::MY53004321")
        self.instrument_info_label.setObjectName("fieldLabel")
        self.instrument_info_label.setWordWrap(True)
        layout.addWidget(self.instrument_info_label)

        self.visa_resource_combo = DarkComboBox()
        self.visa_resource_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
        layout.addWidget(self.visa_resource_combo)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("smallActionBtn")
        search_row.addWidget(self.search_btn)

        layout.addLayout(search_row)

        self.connect_btn = QPushButton("\U0001f517  Connect")
        self.connect_btn.setObjectName("dynamicConnectBtn")
        self.connect_btn.setProperty("connected", "false")
        layout.addWidget(self.connect_btn)

    def _build_test_item_card(self):
        layout = self.test_item_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        test_item_label = QLabel("Test Item")
        test_item_label.setObjectName("fieldLabel")

        self.test_item_combo = DarkComboBox()
        self.test_item_combo.addItems(["Single Iterm Test", "Traverse Iterm Test"])

        grid.addWidget(test_item_label, 0, 0)
        grid.addWidget(self.test_item_combo, 0, 1)

        layout.addLayout(grid)

    def _create_chart_widget(self):
        if HAS_QTCHARTS:
            self.current_series = QLineSeries()
            pen = QPen(QColor("#00d6a2"))
            pen.setWidth(2)
            self.current_series.setPen(pen)

            self.term_marker_series = QScatterSeries()
            self.term_marker_series.setMarkerSize(10)
            self.term_marker_series.setColor(QColor("#ff5e7a"))
            self.term_marker_series.setBorderColor(QColor("#ff5e7a"))

            self.traverse_series = QLineSeries()
            traverse_pen = QPen(QColor("#5b5cf6"))
            traverse_pen.setWidth(2)
            self.traverse_series.setPen(traverse_pen)

            chart = QChart()
            chart.setBackgroundVisible(False)
            chart.setPlotAreaBackgroundVisible(True)
            chart.setPlotAreaBackgroundBrush(QColor("#09142e"))
            chart.legend().hide()
            chart.addSeries(self.current_series)
            chart.addSeries(self.term_marker_series)
            chart.addSeries(self.traverse_series)
            chart.setMargins(QMargins(0, 0, 0, 0))

            self.axis_x = QValueAxis()
            self.axis_x.setRange(0, 10)
            self.axis_x.setTickCount(9)
            self.axis_x.setLabelFormat("%.1f")
            self.axis_x.setTitleText("Time (s)")
            self.axis_x.setLabelsColor(QColor("#9fc0ef"))
            self.axis_x.setTitleBrush(QColor("#9fc0ef"))
            self.axis_x.setGridLineColor(QColor("#2a3f6a"))

            self.axis_y = QValueAxis()
            self.axis_y.setRange(0.0, 0.01)
            self.axis_y.setTickCount(9)
            self.axis_y.setTitleText("Current (A)")
            self.axis_y.setLabelsColor(QColor("#9fc0ef"))
            self.axis_y.setTitleBrush(QColor("#9fc0ef"))
            self.axis_y.setGridLineColor(QColor("#2a3f6a"))

            chart.addAxis(self.axis_x, Qt.AlignBottom)
            chart.addAxis(self.axis_y, Qt.AlignLeft)
            self.current_series.attachAxis(self.axis_x)
            self.current_series.attachAxis(self.axis_y)
            self.term_marker_series.attachAxis(self.axis_x)
            self.term_marker_series.attachAxis(self.axis_y)
            self.traverse_series.attachAxis(self.axis_x)
            self.traverse_series.attachAxis(self.axis_y)

            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.Antialiasing)
            chart_view.setStyleSheet("background: transparent; border: none;")
            return chart_view

        placeholder = QFrame()
        placeholder.setStyleSheet("""
            QFrame {
                background-color: #09142e;
                border: 1px solid #1b315f;
                border-radius: 10px;
            }
        """)
        v = QVBoxLayout(placeholder)
        label = QLabel("Iterm Test Chart")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color:#7da2d6; font-size:14px; font-weight:600; background: transparent;")
        v.addWidget(label)
        return placeholder

    def _build_test_config_card(self):
        layout = self.test_config_card.main_layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        vbat_ch_label = QLabel("Vbat Channel")
        vbat_ch_label.setObjectName("fieldLabel")

        self.vbat_channel_combo = DarkComboBox()
        self.vbat_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])

        charge_ch_label = QLabel("Current Channel")
        charge_ch_label.setObjectName("fieldLabel")

        self.measure_channel_combo = DarkComboBox()
        self.measure_channel_combo.addItems(["CH 1", "CH 2", "CH 3", "CH 4"])
        self.measure_channel_combo.setCurrentIndex(2)

        avg_time_label = QLabel("Average Time (ms)")
        avg_time_label.setObjectName("fieldLabel")

        self.avg_time_spin = QSpinBox()
        self.avg_time_spin.setRange(1, 60000)
        self.avg_time_spin.setValue(10)
        self.avg_time_spin.setSingleStep(1)

        voreg_label = QLabel("Voreg (V)")
        voreg_label.setObjectName("fieldLabel")

        self.voreg_spin = QDoubleSpinBox()
        self.voreg_spin.setRange(0.0, 20.0)
        self.voreg_spin.setValue(4.2)
        self.voreg_spin.setSingleStep(0.1)
        self.voreg_spin.setDecimals(2)

        grid.addWidget(vbat_ch_label, 0, 0)
        grid.addWidget(self.vbat_channel_combo, 0, 1)
        grid.addWidget(charge_ch_label, 1, 0)
        grid.addWidget(self.measure_channel_combo, 1, 1)
        grid.addWidget(avg_time_label, 2, 0)
        grid.addWidget(self.avg_time_spin, 2, 1)
        grid.addWidget(voreg_label, 3, 0)
        grid.addWidget(self.voreg_spin, 3, 1)

        layout.addLayout(grid)

    def _build_param_card(self):
        layout = self.param_card.main_layout

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        lbl_width = QLabel("IIC Width")
        lbl_width.setObjectName("fieldLabel")
        self.iic_width_combo = DarkComboBox()
        self.iic_width_combo.addItem("8 BIT", I2CWidthFlag.BIT_8)
        self.iic_width_combo.addItem("10 BIT", I2CWidthFlag.BIT_10)
        self.iic_width_combo.addItem("32 BIT", I2CWidthFlag.BIT_32)
        self.iic_width_combo.setCurrentIndex(1)

        lbl_dev = QLabel("Device Addr (Hex)")
        lbl_dev.setObjectName("fieldLabel")
        self.device_addr_edit = QLineEdit("0x1A")

        lbl_reg_addr = QLabel("Reg Addr (Hex)")
        lbl_reg_addr.setObjectName("fieldLabel")
        self.reg_addr_edit = QLineEdit("0x0005")

        lbl_msb = QLabel("MSB")
        lbl_msb.setObjectName("fieldLabel")
        self.msb_edit = QLineEdit("3")

        lbl_lsb = QLabel("LSB")
        lbl_lsb.setObjectName("fieldLabel")
        self.lsb_edit = QLineEdit("2")

        lbl_min_code = QLabel("Min Code")
        lbl_min_code.setObjectName("fieldLabel")
        self.min_code_edit = QLineEdit("0x00")

        lbl_max_code = QLabel("Max Code")
        lbl_max_code.setObjectName("fieldLabel")
        self.max_code_edit = QLineEdit("0xFF")

        grid.addWidget(lbl_width, 0, 0)
        grid.addWidget(self.iic_width_combo, 0, 1)
        grid.addWidget(lbl_dev, 1, 0)
        grid.addWidget(self.device_addr_edit, 1, 1)
        grid.addWidget(lbl_reg_addr, 2, 0)
        grid.addWidget(self.reg_addr_edit, 2, 1)
        grid.addWidget(lbl_msb, 3, 0)
        grid.addWidget(self.msb_edit, 3, 1)
        grid.addWidget(lbl_lsb, 4, 0)
        grid.addWidget(self.lsb_edit, 4, 1)
        grid.addWidget(lbl_min_code, 5, 0)
        grid.addWidget(self.min_code_edit, 5, 1)
        grid.addWidget(lbl_max_code, 6, 0)
        grid.addWidget(self.max_code_edit, 6, 1)

        layout.addLayout(grid)

    def _create_mini_stat(self, label_text, value_text):
        frame = QFrame()
        frame.setObjectName("miniStatCard")
        frame.setFixedHeight(60)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        lbl = QLabel(label_text)
        lbl.setObjectName("metricLabel")
        val = QLabel(value_text)
        val.setObjectName("metricValue")
        lay.addWidget(lbl)
        lay.addWidget(val)
        return {"frame": frame, "label": lbl, "value": val}

    def _set_traverse_stat_visible(self, traverse):
        for card in [self.default_iterm_card, self.min_iterm_card, self.max_iterm_card,
                     self.step_iterm_card, self.linearity_iterm_card]:
            card["frame"].setVisible(traverse)
        for card in [self.iterm_card, self.voreg_card]:
            card["frame"].setVisible(not traverse)

    def _init_ui_elements(self):
        self._update_connect_button_state(False)
        logger.info("Iterm Test ready.")
        self._append_to_log("[SYSTEM] Iterm Test ready.")

    def _bind_signals(self):
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect_or_disconnect)
        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._on_stop_test)
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        self.export_result_btn.clicked.connect(self._on_export_csv)
        self.msb_edit.textChanged.connect(self._update_code_range)
        self.lsb_edit.textChanged.connect(self._update_code_range)
        self.test_item_combo.currentTextChanged.connect(self._on_test_item_changed)
        self._update_code_range()

    def _on_test_item_changed(self, text):
        is_traverse = text != "Single Iterm Test"
        self._set_traverse_stat_visible(is_traverse)
        if HAS_QTCHARTS and hasattr(self, 'axis_x'):
            if is_traverse:
                self.axis_x.setTitleText("Register Code")
                self.axis_x.setLabelFormat("%d")
                self.axis_y.setTitleText("Iterm (mA)")
                self.chart_title.setText("\u2248 Iterm vs Register Code")
            else:
                self.axis_x.setTitleText("Time (s)")
                self.axis_x.setLabelFormat("%.1f")
                self.axis_y.setTitleText("Current (A)")
                self.chart_title.setText("\u2248 Current vs Time")

    def _update_code_range(self):
        try:
            msb = int(self.msb_edit.text())
            lsb = int(self.lsb_edit.text())
        except ValueError:
            return
        if msb < lsb:
            return
        bit_count = msb - lsb + 1
        max_val = (1 << bit_count) - 1
        self.min_code_edit.setText("0x0")
        self.max_code_edit.setText(f"0x{max_val:X}")

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._on_stop_test()
        else:
            self._on_start_test()

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        self.connect_btn.setProperty("connected", "true" if connected else "false")
        self.connect_btn.setText("\u21b2  Disconnect" if connected else "\U0001f517  Connect")

        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.connect_btn.update()

    def _sync_from_top(self):
        if not self._n6705c_top:
            return
        if self._n6705c_top.is_connected_a and self._n6705c_top.n6705c_a:
            self.n6705c = self._n6705c_top.n6705c_a
            self._update_connect_button_state(True)
            self.search_btn.setEnabled(False)
            if self._n6705c_top.visa_resource_a:
                self.visa_resource_combo.clear()
                self.visa_resource_combo.addItem(self._n6705c_top.visa_resource_a)
        elif not self.is_connected:
            self._update_connect_button_state(False)

    def _run_in_background(self, func, on_finished, on_error=None):
        if self._bg_thread is not None:
            self._bg_thread.quit()
            self._bg_thread.wait()

        self._bg_thread = QThread()
        self._bg_worker = _BackgroundTaskWorker(func)
        self._bg_worker.moveToThread(self._bg_thread)
        self._bg_worker.finished.connect(on_finished)
        if on_error:
            self._bg_worker.error.connect(on_error)
        self._bg_worker.finished.connect(self._cleanup_bg_thread)
        self._bg_worker.error.connect(self._cleanup_bg_thread)
        self._bg_thread.started.connect(self._bg_worker.run)
        self._bg_thread.start()

    def _cleanup_bg_thread(self):
        if self._bg_thread is not None:
            self._bg_thread.quit()
            self._bg_thread.wait()
            self._bg_thread = None
            self._bg_worker = None

    def _on_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        self.set_system_status("\u25cf Searching")
        logger.info("Scanning VISA resources...")
        self._append_to_log("[SYSTEM] Scanning VISA resources...")
        self.search_btn.setEnabled(False)
        self.connect_btn.setEnabled(False)
        self._run_in_background(self._search_devices_bg, self._on_search_finished, self._on_search_error)

    def _search_devices_bg(self):
        rm = self.rm
        if rm is None:
            try:
                rm = pyvisa.ResourceManager()
            except Exception:
                rm = pyvisa.ResourceManager('@ni')
            self.rm = rm

        all_devices = list(rm.list_resources()) or []
        self.available_devices = all_devices

        n6705c_devices = []
        for dev in all_devices:
            try:
                instr = rm.open_resource(dev, timeout=1000)
                idn = instr.query('*IDN?').strip()
                instr.close()
                if "N6705C" in idn:
                    n6705c_devices.append(dev)
            except Exception:
                pass
        return n6705c_devices

    def _on_search_finished(self, n6705c_devices):
        self.visa_resource_combo.setEnabled(True)
        self.visa_resource_combo.clear()

        if n6705c_devices:
            for dev in n6705c_devices:
                self.visa_resource_combo.addItem(dev)

            count = len(n6705c_devices)
            self.set_system_status(f"\u25cf Found {count} device(s)")
            logger.info(f"Found {count} compatible N6705C device(s).")
            self._append_to_log(f"[SYSTEM] Found {count} compatible N6705C device(s).")

            default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
            if default_device in n6705c_devices:
                self.visa_resource_combo.setCurrentText(default_device)
            else:
                self.visa_resource_combo.setCurrentIndex(0)
        else:
            self.visa_resource_combo.addItem("No N6705C device found")
            self.visa_resource_combo.setEnabled(False)
            self.set_system_status("\u25cf No device found", is_error=True)
            logger.info("No compatible N6705C instrument found.")
            self._append_to_log("[SYSTEM] No compatible N6705C instrument found.")

        self.search_btn.setEnabled(True)
        self.connect_btn.setEnabled(True)

    def _on_search_error(self, err_msg):
        self.set_system_status("\u25cf Search failed", is_error=True)
        logger.error(f"Search failed: {err_msg}")
        self._append_to_log(f"[ERROR] Search failed: {err_msg}")
        self.search_btn.setEnabled(True)
        self.connect_btn.setEnabled(True)

    def _on_connect_or_disconnect(self):
        if self.is_connected:
            self._on_disconnect()
        else:
            self._on_connect()

    def _on_connect(self):
        self.set_system_status("\u25cf Connecting")
        logger.info("Attempting instrument connection...")
        self._append_to_log("[SYSTEM] Attempting instrument connection...")
        self.connect_btn.setEnabled(False)
        self.search_btn.setEnabled(False)

        device_address = self.visa_resource_combo.currentText()
        self._pending_device_address = device_address

        if DEBUG_MOCK:
            self.n6705c = MockN6705C()
            self._update_connect_button_state(True)
            self.set_system_status("\u25cf Connected (Mock)")
            self.search_btn.setEnabled(False)
            self.instrument_info_label.setText("Mock N6705C (DEBUG)")
            self._append_to_log("[DEBUG] Mock N6705C connected.")
            if self._n6705c_top:
                self._n6705c_top.connect_a(device_address, self.n6705c)
            self.connection_status_changed.emit(True)
            self.connect_btn.setEnabled(True)
            return

        def _connect_bg():
            n6705c = N6705C(device_address)
            idn = n6705c.instr.query("*IDN?")
            return {"n6705c": n6705c, "idn": idn, "address": device_address}

        self._run_in_background(_connect_bg, self._on_connect_finished, self._on_connect_error)

    def _on_connect_finished(self, result):
        n6705c = result["n6705c"]
        idn = result["idn"]
        device_address = result["address"]

        if "N6705C" in idn:
            self.n6705c = n6705c
            self._update_connect_button_state(True)
            self.set_system_status("\u25cf Connected")
            self.search_btn.setEnabled(False)

            pretty_name = device_address
            try:
                pretty_name = device_address.split("::")[1]
            except Exception:
                pass

            self.instrument_info_label.setText(pretty_name)
            logger.info("N6705C connected successfully.")
            self._append_to_log("[SYSTEM] N6705C connected successfully.")
            logger.debug(f"IDN: {idn.strip()}")

            if self._n6705c_top:
                self._n6705c_top.connect_a(device_address, n6705c)

            self.connection_status_changed.emit(True)
        else:
            self.set_system_status("\u25cf Device mismatch", is_error=True)
            logger.error("Connected device is not N6705C.")
            self._append_to_log("[ERROR] Connected device is not N6705C.")

        self.connect_btn.setEnabled(True)

    def _on_connect_error(self, err_msg):
        self.set_system_status("\u25cf Connection failed", is_error=True)
        logger.error(f"Connection failed: {err_msg}")
        self._append_to_log(f"[ERROR] Connection failed: {err_msg}")
        self.connect_btn.setEnabled(True)
        self.search_btn.setEnabled(True)

    def _on_disconnect(self):
        self.set_system_status("\u25cf Disconnecting")
        logger.info("Disconnecting instrument...")
        self._append_to_log("[SYSTEM] Disconnecting instrument...")
        self.connect_btn.setEnabled(False)
        self.search_btn.setEnabled(False)

        n6705c_top = self._n6705c_top
        n6705c = self.n6705c

        def _disconnect_bg():
            if n6705c_top:
                n6705c_top.disconnect_a()
            else:
                if n6705c is not None:
                    if hasattr(n6705c, 'instr') and n6705c.instr:
                        n6705c.instr.close()
                    if hasattr(n6705c, 'rm') and n6705c.rm:
                        n6705c.rm.close()
            return True

        self._run_in_background(_disconnect_bg, self._on_disconnect_finished, self._on_disconnect_error)

    def _on_disconnect_finished(self, _result):
        self.n6705c = None
        self._update_connect_button_state(False)
        self.set_system_status("\u25cf Ready")
        self.search_btn.setEnabled(True)
        self.instrument_info_label.setText("USB0::0x0957::0x0F07::MY53004321")
        logger.info("Instrument disconnected.")
        self._append_to_log("[SYSTEM] Instrument disconnected.")
        self.connection_status_changed.emit(False)
        self.connect_btn.setEnabled(True)

    def _on_disconnect_error(self, err_msg):
        self.set_system_status("\u25cf Disconnect failed", is_error=True)
        logger.error(f"Disconnect failed: {err_msg}")
        self._append_to_log(f"[ERROR] Disconnect failed: {err_msg}")
        self.connect_btn.setEnabled(True)
        self.search_btn.setEnabled(True)

    def _on_start_test(self):
        if not self.is_connected or self.n6705c is None:
            logger.error("Not connected to N6705C instrument.")
            self._append_to_log("[ERROR] Not connected to N6705C instrument.")
            return
        if self.is_test_running:
            return

        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0
        self._export_data = []

        try:
            device_addr = int(self.device_addr_edit.text(), 16)
            reg_addr = int(self.reg_addr_edit.text(), 16)
            msb = int(self.msb_edit.text())
            lsb = int(self.lsb_edit.text())
            min_code = int(self.min_code_edit.text(), 16)
            max_code = int(self.max_code_edit.text(), 16)
        except ValueError:
            logger.error("Invalid hex address or parameter.")
            self._append_to_log("[ERROR] Invalid hex address or parameter.")
            return

        iic_width = self.iic_width_combo.currentData()
        test_item = self.test_item_combo.currentText()

        if test_item == "Single Iterm Test":
            self._set_traverse_stat_visible(False)
            if HAS_QTCHARTS and hasattr(self, 'axis_x'):
                self.axis_x.setTitleText("Time (s)")
                self.axis_x.setLabelFormat("%.1f")
                self.axis_y.setTitleText("Current (A)")
                self.chart_title.setText("\u2248 Current vs Time")
        else:
            self._set_traverse_stat_visible(True)
            if HAS_QTCHARTS and hasattr(self, 'axis_x'):
                self.axis_x.setTitleText("Register Code")
                self.axis_x.setLabelFormat("%d")
                self.axis_y.setTitleText("Iterm (mA)")
                self.chart_title.setText("\u2248 Iterm vs Register Code")

        config = {
            "test_item": test_item,
            "device_addr": device_addr,
            "iterm_reg": reg_addr,
            "iic_width": iic_width,
            "vbat_channel": int(self.vbat_channel_combo.currentText().replace("CH ", "")),
            "measure_channel": int(self.measure_channel_combo.currentText().replace("CH ", "")),
            "average_time_ms": self.avg_time_spin.value(),
            "voreg": self.voreg_spin.value(),
            "msb": msb,
            "lsb": lsb,
            "min_code": min_code,
            "max_code": max_code,
        }

        self.set_test_running(True)
        self.set_progress(0)

        self.test_thread = QThread()
        self.test_worker = _ItermTestWorker(self.n6705c, config)
        self.test_worker.moveToThread(self.test_thread)

        self.test_worker.log_message.connect(self._append_to_log)
        self.test_worker.progress.connect(self.set_progress)
        self.test_worker.result_row.connect(self._on_result_row)
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_worker.chart_clear.connect(self._on_chart_clear)
        self.test_worker.chart_series_data.connect(self._on_chart_series_data)
        self.test_worker.traverse_chart_point.connect(self._on_traverse_chart_point)
        self.test_worker.traverse_chart_clear.connect(self._on_traverse_chart_clear)
        self.test_worker.traverse_result_update.connect(self._on_traverse_result_update)
        self.test_thread.started.connect(self.test_worker.run)

        self.test_thread.start()

    def _on_stop_test(self):
        if self.test_worker is not None:
            self.test_worker.request_stop()
        logger.info("Stop requested...")
        self._append_to_log("[TEST] Stop requested...")

    def _on_result_row(self, row):
        self._total_count += 1
        if row["result"] == "PASS":
            self._pass_count += 1
        else:
            self._fail_count += 1

        self._export_data.append(row)

    def _on_test_finished(self, success):
        self.set_test_running(False)
        if success:
            logger.info("Iterm test completed.")
            self._append_to_log("[TEST] Iterm test completed.")
        else:
            logger.error("Iterm test ended with errors.")
            self._append_to_log("[TEST] Iterm test ended with errors.")
        if self.test_thread is not None:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_thread = None
            self.test_worker = None

    def _on_clear_log(self):
        self.log_edit.clear()

    def _on_chart_clear(self):
        if HAS_QTCHARTS and hasattr(self, 'current_series'):
            self.current_series.clear()
            self.term_marker_series.clear()

    def _on_chart_series_data(self, timestamps, currents, t_term, iterm, v_term):
        if not HAS_QTCHARTS or not hasattr(self, 'current_series'):
            return

        self.current_series.clear()
        self.term_marker_series.clear()

        self._export_data.extend(zip(timestamps, currents))

        total = len(timestamps)
        max_chart_points = 5000
        if total > max_chart_points:
            step = total // max_chart_points
            points = [QPointF(timestamps[idx], currents[idx]) for idx in range(0, total, step)]
        else:
            points = [QPointF(t, i) for t, i in zip(timestamps, currents)]
        self.current_series.replace(points)

        if t_term >= 0:
            t_idx = None
            for j, t in enumerate(timestamps):
                if abs(t - t_term) < 0.001:
                    t_idx = j
                    break
            if t_idx is not None:
                self.term_marker_series.append(t_term, currents[t_idx])

        if timestamps:
            min_x = min(timestamps)
            max_x = max(timestamps)
            margin_x = max((max_x - min_x) * 0.05, 0.1)
            self.axis_x.setRange(min_x - margin_x, max_x + margin_x)

        if currents:
            min_y = min(currents)
            max_y = max(currents)
            margin_y = max((max_y - min_y) * 0.05, 0.001)
            self.axis_y.setRange(min_y - margin_y, max_y + margin_y)

        if iterm != 0.0:
            self.iterm_card["value"].setText(f"{_fmt_val(abs(iterm) * 1000.0)} mA")
        if v_term > 0.0:
            self.voreg_card["value"].setText(f"{v_term:.4f} V")

    def _on_traverse_chart_clear(self):
        if HAS_QTCHARTS and hasattr(self, 'traverse_series'):
            self.traverse_series.clear()
            self.current_series.clear()
            self.term_marker_series.clear()
        self._traverse_min_x = float('inf')
        self._traverse_max_x = float('-inf')
        self._traverse_min_y = float('inf')
        self._traverse_max_y = float('-inf')

    def _on_traverse_chart_point(self, code, iterm_ma):
        if not HAS_QTCHARTS or not hasattr(self, 'traverse_series'):
            return

        self.traverse_series.append(code, iterm_ma)
        self._export_data.append((code, iterm_ma))

        self._traverse_min_x = min(self._traverse_min_x, code)
        self._traverse_max_x = max(self._traverse_max_x, code)
        self._traverse_min_y = min(self._traverse_min_y, iterm_ma)
        self._traverse_max_y = max(self._traverse_max_y, iterm_ma)

        if hasattr(self, 'axis_x'):
            margin_x = max(int((self._traverse_max_x - self._traverse_min_x) * 0.05), 1)
            self.axis_x.setRange(
                max(0, int(self._traverse_min_x) - margin_x),
                int(self._traverse_max_x) + margin_x
            )

        if hasattr(self, 'axis_y'):
            margin_y = max((self._traverse_max_y - self._traverse_min_y) * 0.05, 0.01)
            self.axis_y.setRange(self._traverse_min_y - margin_y, self._traverse_max_y + margin_y)

    def _on_traverse_result_update(self, result):
        if 'default_value' in result:
            code_str = f"(0x{result['default_code']:X})" if 'default_code' in result else ""
            self.default_iterm_card["value"].setText(f"{result['default_value']:.4f} mA{code_str}")
        if 'min_value' in result:
            code_str = f" (0x{result['valid_min_code']:X})" if 'valid_min_code' in result else ""
            self.min_iterm_card["value"].setText(f"{result['min_value']:.4f} mA{code_str}")
        if 'max_value' in result:
            code_str = f" (0x{result['valid_max_code']:X})" if 'valid_max_code' in result else ""
            self.max_iterm_card["value"].setText(f"{result['max_value']:.4f} mA{code_str}")
        if 'step_value' in result:
            self.step_iterm_card["value"].setText(f"{result['step_value']:.4f} mA")
        if 'linearity' in result:
            self.linearity_iterm_card["value"].setText(f"{result['linearity']:.4f}%")
        if 'progress' in result:
            self.set_progress(result['progress'])

    def _on_export_csv(self):
        if not self._export_data:
            logger.info("No data to export.")
            self._append_to_log("[EXPORT] No data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("X,Y\n")
                for x_val, y_val in self._export_data:
                    f.write(f"{x_val:.10g},{y_val:.10g}\n")
            logger.info(f"Data exported to {path}")
            self._append_to_log(f"[EXPORT] Data exported to {path}")
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self._append_to_log(f"[ERROR] Export failed: {e}")

    def set_test_running(self, running):
        self.is_test_running = running
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(running)
        if running:
            self.start_test_btn.setText("\u25a0 STOP")
            self.start_test_btn.setObjectName("stopBtn")
        else:
            self.start_test_btn.setText("\u25b6 START ITERM TEST")
            self.start_test_btn.setObjectName("primaryStartBtn")
        self.start_test_btn.style().unpolish(self.start_test_btn)
        self.start_test_btn.style().polish(self.start_test_btn)
        self.start_test_btn.update()
        self.device_addr_edit.setEnabled(not running)
        self.reg_addr_edit.setEnabled(not running)
        self.msb_edit.setEnabled(not running)
        self.lsb_edit.setEnabled(not running)
        self.min_code_edit.setEnabled(not running)
        self.max_code_edit.setEnabled(not running)
        self.iic_width_combo.setEnabled(not running)
        self.measure_channel_combo.setEnabled(not running)
        self.vbat_channel_combo.setEnabled(not running)
        self.test_item_combo.setEnabled(not running)
        self.avg_time_spin.setEnabled(not running)
        self.visa_resource_combo.setEnabled(not running)
        self.search_btn.setEnabled(not running)
        self.connect_btn.setEnabled(not running)

        if running:
            self.set_system_status("\u25cf Running")
        else:
            self.set_system_status("\u25cf Ready" if not self.is_connected else "\u25cf Connected")

    def set_progress(self, value):
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}% Complete")

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Running" in status or "Searching" in status or "Connecting" in status or "Disconnecting" in status:
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def _append_to_log(self, msg):
        self.log_edit.append(msg)
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def get_test_config(self):
        try:
            device_addr = int(self.device_addr_edit.text(), 16)
            reg_addr = int(self.reg_addr_edit.text(), 16)
            msb = int(self.msb_edit.text())
            lsb = int(self.lsb_edit.text())
            min_code = int(self.min_code_edit.text(), 16)
            max_code = int(self.max_code_edit.text(), 16)
        except ValueError:
            device_addr = 0
            reg_addr = 0
            msb = 9
            lsb = 5
            min_code = 0
            max_code = 0xFF
        return {
            "device_addr": device_addr,
            "reg_addr": reg_addr,
            "iic_width": self.iic_width_combo.currentData(),
            "measure_channel": int(self.measure_channel_combo.currentText().replace("CH ", "")),
            "msb": msb,
            "lsb": lsb,
            "min_code": min_code,
            "max_code": max_code,
        }

    def clear_results(self):
        self._pass_count = 0
        self._fail_count = 0
        self._total_count = 0
        self.iterm_card["value"].setText("---")
        self.iterm_card["label"].setText("Iterm")
        self.voreg_card["value"].setText("---")
        self.voreg_card["label"].setText("Voreg")
        self.default_iterm_card["value"].setText("---")
        self.min_iterm_card["value"].setText("---")
        self.max_iterm_card["value"].setText("---")
        self.step_iterm_card["value"].setText("---")
        self.linearity_iterm_card["value"].setText("---")
        if HAS_QTCHARTS:
            if hasattr(self, 'current_series'):
                self.current_series.clear()
            if hasattr(self, 'term_marker_series'):
                self.term_marker_series.clear()
            if hasattr(self, 'traverse_series'):
                self.traverse_series.clear()

    def update_test_result(self, result):
        if "iterm" in result:
            self.iterm_card["value"].setText(str(result["iterm"]))
        if "voreg" in result:
            self.voreg_card["value"].setText(str(result["voreg"]))
        if "default_value" in result:
            code_str = f"(0x{result['default_code']:X})" if 'default_code' in result else ""
            self.default_iterm_card["value"].setText(f"{result['default_value']:.4f} mA{code_str}")
        if "min_value" in result:
            code_str = f" (0x{result['valid_min_code']:X})" if 'valid_min_code' in result else ""
            self.min_iterm_card["value"].setText(f"{result['min_value']:.4f} mA{code_str}")
        if "max_value" in result:
            code_str = f" (0x{result['valid_max_code']:X})" if 'valid_max_code' in result else ""
            self.max_iterm_card["value"].setText(f"{result['max_value']:.4f} mA{code_str}")
        if "step_value" in result:
            self.step_iterm_card["value"].setText(f"{result['step_value']:.4f} mA/code")
        if "linearity" in result:
            self.linearity_iterm_card["value"].setText(f"{result['linearity']:.4f}%")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ItermTestUI()
    window.setWindowTitle("Iterm Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())
