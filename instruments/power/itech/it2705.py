import json
import math
import os
import sys
import time

import pyvisa

if __name__ == "__main__" and __package__ is None:
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from instruments.base.visa_instrument import VisaInstrument
from log_config import get_logger

logger = get_logger(__name__)


class IT2705(VisaInstrument):
    """ITECH IT2705 多通道源载系统 SCPI 驱动。"""

    VALID_CHANNELS = tuple(range(1, 9))
    SUPPORTED_MODULE_MODELS = frozenset({"IT27814", "IT27814E"})
    DLOG_PERIOD_MIN = 20e-6
    DLOG_PERIOD_MAX = 60.0
    INVALID_MEAS_THRESHOLD = 9.9e37

    def __init__(self, resource, visa_library=None, timeout_ms=10000):
        super().__init__()
        self.resource = str(resource).strip()
        if not self.resource:
            raise ValueError("IT2705: resource 必填")
        self.visa_library = visa_library
        self.timeout_ms = int(timeout_ms)
        self.channel_module_models = {ch: "" for ch in self.VALID_CHANNELS}
        self.connect()

    def refresh_channel_modules(self):
        self.channel_module_models = {ch: "" for ch in self.VALID_CHANNELS}
        channel_list = ",".join(str(ch) for ch in self.VALID_CHANNELS)
        try:
            response = self.query(f":SYSTem:CHANnel:STATus? (@{channel_list})")
            statuses = [value.strip() for value in str(response).split(",")]
            if len(statuses) != len(self.VALID_CHANNELS):
                raise ValueError(f"unexpected channel status response: {response!r}")
        except Exception:
            logger.warning(
                "IT2705 channel status query failed; all channels disabled",
                exc_info=True,
            )
            return dict(self.channel_module_models)

        for channel, status in zip(self.VALID_CHANNELS, statuses):
            if status != "1":
                logger.debug("IT2705 CH%d module: EMPTY", channel)
                continue
            try:
                response = self.query(f":SYSTem:CHANnel:MODel? (@{channel})")
                model = str(response).strip().strip("\"'").strip().upper()
                self.channel_module_models[channel] = model
                logger.debug("IT2705 CH%d module: %s", channel, model or "EMPTY")
            except Exception:
                logger.warning(
                    "IT2705 CH%d module query failed; channel disabled",
                    channel,
                    exc_info=True,
                )
        return dict(self.channel_module_models)

    def is_channel_supported(self, channel):
        model = self.channel_module_models.get(int(channel), "")
        return model in self.SUPPORTED_MODULE_MODELS

    @property
    def instr(self):
        return self.instrument

    @instr.setter
    def instr(self, value):
        self.instrument = value

    @staticmethod
    def _resource_name(resource):
        resource = str(resource).strip()
        upper = resource.upper()
        visa_prefixes = ("TCPIP", "USB", "GPIB", "ASRL", "VXI", "PXI", "HISLIP")
        if "::" in resource and (
            upper.endswith("::INSTR")
            or upper.endswith("::SOCKET")
            or upper.startswith(visa_prefixes)
        ):
            return resource
        return f"TCPIP0::{resource}::inst0::INSTR"

    def _create_resource_manager(self):
        try:
            if self.visa_library:
                return pyvisa.ResourceManager(self.visa_library)
            return pyvisa.ResourceManager()
        except (OSError, ValueError, pyvisa.errors.VisaIOError) as exc:
            logger.warning(
                "IT2705: 系统 VISA 不可用，回退到 pyvisa-py: %s", exc, exc_info=True
            )
            return pyvisa.ResourceManager("@py")

    def connect(self, device_address=None):
        if device_address is not None:
            self.resource = str(device_address).strip()
        if not self.resource:
            raise ValueError("IT2705: device_address 必填")
        self.disconnect()
        self.rm = self._create_resource_manager()
        try:
            self.instrument = self.rm.open_resource(self._resource_name(self.resource))
            self.instrument.timeout = self.timeout_ms
            self.instrument.encoding = "utf-8"
            self.instrument.read_termination = "\n"
            self.instrument.write_termination = "\n"
        except Exception:
            logger.error("IT2705: 连接失败: %s", self.resource, exc_info=True)
            self.disconnect()
            raise
        logger.info("IT2705 已连接: %s", self.resource)
        return True

    def disconnect(self):
        success = True
        if self.instrument is not None:
            try:
                self.instrument.close()
            except Exception:
                success = False
                logger.error("IT2705: 关闭仪器连接失败", exc_info=True)
        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                success = False
                logger.error("IT2705: 关闭 VISA ResourceManager 失败", exc_info=True)
        self.instrument = None
        self.rm = None
        return success

    def close(self):
        return self.disconnect()

    def is_connected(self):
        return self.instrument is not None

    def _ensure_connected(self):
        if self.instrument is None:
            raise RuntimeError("IT2705: instrument not connected")

    def write(self, command):
        self._ensure_connected()
        logger.debug("IT2705 WRITE: %s", command)
        return self.instrument.write(command)

    def query(self, command):
        self._ensure_connected()
        logger.debug("IT2705 QUERY: %s", command)
        response = self.instrument.query(command)
        logger.debug("IT2705 RESP: %s", response.strip())
        return response

    def _query_float(self, command):
        raw = self.query(command).strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"IT2705: 无法解析数值 {raw!r}") from exc
        if abs(value) >= self.INVALID_MEAS_THRESHOLD:
            raise ValueError(f"IT2705: 无有效测量值 {value}")
        return value

    @classmethod
    def _validate_channel(cls, channel):
        try:
            value = int(channel)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"IT2705: 无效通道号 {channel!r}") from exc
        if value not in cls.VALID_CHANNELS:
            raise ValueError(f"IT2705: 无效通道号 {channel}，仅支持 1-8")
        return value

    @classmethod
    def _normalize_channels(cls, channels):
        if isinstance(channels, int):
            channels = [channels]
        normalized = [cls._validate_channel(channel) for channel in channels]
        normalized = list(dict.fromkeys(normalized))
        if not normalized:
            raise ValueError("IT2705: 至少指定一个通道")
        return normalized

    @staticmethod
    def _normalize_choice(value, choices, name):
        normalized = str(value).strip().upper()
        if normalized not in choices:
            raise ValueError(f"IT2705: {name} 必须属于 {sorted(choices)}")
        return normalized

    @staticmethod
    def _on_off(enabled):
        return "ON" if enabled else "OFF"

    def identify(self):
        return self.query("*IDN?").strip()

    def reset(self):
        self.write("*RST")

    def clear_status(self):
        self.write("*CLS")

    def set_voltage(self, channel, voltage):
        channel = self._validate_channel(channel)
        self.write(f"VOLT {float(voltage)},(@{channel})")

    def get_voltage_setpoint(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"VOLT? (@{channel})")

    def set_current(self, channel, current):
        channel = self._validate_channel(channel)
        self.write(f"CURR {float(current)},(@{channel})")

    def get_current_setpoint(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"CURR? (@{channel})")

    def set_current_limit(self, channel, current_limit):
        channel = self._validate_channel(channel)
        self.write(f"CURR:LIM {float(current_limit)},(@{channel})")

    def get_current_limit(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"CURR:LIM? (@{channel})")

    def set_voltage_limit(self, channel, voltage_limit):
        channel = self._validate_channel(channel)
        self.write(f"VOLT:LIM:HIGH {float(voltage_limit)},(@{channel})")

    def get_voltage_limit(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"VOLT:LIM:HIGH? (@{channel})")

    def set_measurement_range(self, channel, measurement_type, range_value):
        channel = self._validate_channel(channel)
        measurement_type = str(measurement_type).strip().lower()
        if measurement_type == "voltage":
            self.write(f"VOLT:RANG {float(range_value)},(@{channel})")
        elif measurement_type == "current":
            self.write(f"CURR:RANG {float(range_value)},(@{channel})")
        else:
            raise ValueError("IT2705: measurement_type 仅支持 voltage 或 current")

    def set_mode(self, channel, mode):
        channel = self._validate_channel(channel)
        self.write(f"EMUL {str(mode).strip()},(@{channel})")

    def get_mode(self, channel):
        channel = self._validate_channel(channel)
        return self.query(f"EMUL? (@{channel})").strip()

    def set_function(self, channel, function):
        channel = self._validate_channel(channel)
        functions = {
            "CURR", "CURRENT", "VOLT", "VOLTAGE", "POW", "POWER", "RES", "RESISTANCE",
            "CC+CV", "CR+CV", "CP+CV", "CC+CR", "AUTO", "BSIM",
        }
        function = self._normalize_choice(function, functions, "function")
        self.write(f"FUNC {function},(@{channel})")

    def set_function_mode(self, channel, mode, input_mode=False):
        channel = self._validate_channel(channel)
        modes = {
            "FIX", "FIXED", "ARB", "BCHARGE", "BEMULATION", "TRAN", "TRANSIENT",
            "SEQ", "SEQUENCE", "CDARB", "SSWEEP", "LIST", "BDISCHARGE",
        }
        mode = self._normalize_choice(mode, modes, "function mode")
        subsystem = "INP" if input_mode else "OUTP"
        self.write(f"{subsystem}:FUNC:MODE {mode},(@{channel})")

    def channel_on(self, channel):
        channel = self._validate_channel(channel)
        self.write(f"OUTP ON,(@{channel})")

    def channel_off(self, channel):
        channel = self._validate_channel(channel)
        self.write(f"OUTP OFF,(@{channel})")

    def get_channel_state(self, channel):
        channel = self._validate_channel(channel)
        return self.query(f"OUTP? (@{channel})").strip().upper() in {"1", "ON"}

    def set_output_off_mode(self, channel, mode="HIGHZ"):
        channel = self._validate_channel(channel)
        mode = self._normalize_choice(mode, {"HIGHZ", "LOWZ"}, "output off mode")
        self.write(f"OUTP:TMOD {mode},(@{channel})")

    def get_output_off_mode(self, channel):
        channel = self._validate_channel(channel)
        return self.query(f"OUTP:TMOD? (@{channel})").strip().upper()

    def measure_voltage(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"MEAS:VOLT? (@{channel})")

    def measure_current(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"MEAS:CURR? (@{channel})")

    def measure_power(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"MEAS:POW? (@{channel})")

    def fetch_voltage(self, channel):
        channel = self._validate_channel(channel)
        return self._query_float(f"FETC:VOLT? (@{channel})")

    def fetch_current(self, channel):
        channel = self._validate_channel(channel)
        self.write(f"INIT:ACQ (@{channel})")
        return self._query_float(f"FETC:CURR? (@{channel})")

    def measure_voltage_fast(self, channel):
        channel = self._validate_channel(channel)
        self.write(f"INIT:ACQ (@{channel})")
        return self._query_float(f"FETC:VOLT? (@{channel})")

    def set_arb_type(self, channel, arb_type="VOLT"):
        channel = self._validate_channel(channel)
        types = {"CURR", "CURRENT", "VOLT", "VOLTAGE", "POW", "POWER", "RES", "RESISTANCE"}
        arb_type = self._normalize_choice(arb_type, types, "ARB type")
        self.write(f"ARB:FUNC:TYPE {arb_type},(@{channel})")

    def set_arb_shape(self, channel, shape="STEP"):
        channel = self._validate_channel(channel)
        shapes = {
            "STEP", "RAMP", "STA", "STAIRCASE", "SIN", "SINUSOID", "PULS", "PULSE",
            "TRAP", "TRAPEZOID", "EXP", "EXPONENTIAL", "UDEF", "UDEFINED",
        }
        shape = self._normalize_choice(shape, shapes, "ARB shape")
        self.write(f"ARB:FUNC:SHAP {shape},(@{channel})")

    def set_arb_sine(self, channel, dc_offset, amplitude_vrms, frequency):
        channel = self._validate_channel(channel)
        if amplitude_vrms <= 0 or frequency <= 0:
            raise ValueError("IT2705: 正弦幅度与频率必须大于 0")
        amplitude_peak = math.sqrt(2.0) * amplitude_vrms
        self.set_arb_type(channel, "VOLT")
        self.set_arb_shape(channel, "SIN")
        self.write(f"ARB:VOLT:SIN:OFFS {float(dc_offset)},(@{channel})")
        self.write(f"ARB:VOLT:SIN:AMPL {amplitude_peak},(@{channel})")
        self.write(f"ARB:VOLT:SIN:FREQ {float(frequency)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_step(self, channel, v0, v1, t0, t1):
        channel = self._validate_channel(channel)
        self.set_arb_type(channel, "VOLT")
        self.set_arb_shape(channel, "STEP")
        self.write(f"ARB:VOLT:STEP:STAR {float(v0)},(@{channel})")
        self.write(f"ARB:VOLT:STEP:END {float(v1)},(@{channel})")
        self.write(f"ARB:VOLT:STEP:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"ARB:VOLT:STEP:END:TIME {float(t1)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_staircase(self, channel, v0, v1, t0, t1, t2, steps):
        channel = self._validate_channel(channel)
        if int(steps) < 1:
            raise ValueError("IT2705: steps 必须大于 0")
        self.set_arb_type(channel, "VOLT")
        self.set_arb_shape(channel, "STA")
        self.write(f"ARB:VOLT:STA:STAR {float(v0)},(@{channel})")
        self.write(f"ARB:VOLT:STA:END {float(v1)},(@{channel})")
        self.write(f"ARB:VOLT:STA:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"ARB:VOLT:STA:TIME {float(t1)},(@{channel})")
        self.write(f"ARB:VOLT:STA:END:TIME {float(t2)},(@{channel})")
        self.write(f"ARB:VOLT:STA:NST {int(steps)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def _set_arb_pulse(self, channel, arb_type, start, top, t0, t1, t2, frequency):
        if frequency <= 0:
            raise ValueError("IT2705: 脉冲频率必须大于 0")
        self.set_arb_type(channel, arb_type)
        self.set_arb_shape(channel, "PULS")
        prefix = "ARB:VOLT:PULS" if arb_type == "VOLT" else "ARB:CURR:PULS"
        self.write(f"{prefix}:STAR {float(start)},(@{channel})")
        self.write(f"{prefix}:TOP {float(top)},(@{channel})")
        self.write(f"{prefix}:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"{prefix}:END:TIME {float(t1)},(@{channel})")
        self.write(f"{prefix}:TOP:TIME {float(t2)},(@{channel})")
        self.write(f"{prefix}:FREQ {float(frequency)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_pulse(self, channel, v0, v1, t0, t1, t2, frequency):
        self._set_arb_pulse(
            self._validate_channel(channel), "VOLT", v0, v1, t0, t1, t2, frequency
        )

    def set_arb_current_pulse(self, channel, i0, i1, t0, t1, t2, frequency):
        self._set_arb_pulse(
            self._validate_channel(channel), "CURR", i0, i1, t0, t1, t2, frequency
        )

    def set_current_slew(self, channel, slew="MAX"):
        channel = self._validate_channel(channel)
        if str(slew).strip().upper() == "MAX":
            self.write(f"CURR:SLEW:MAX ON,(@{channel})")
            return
        try:
            value = float(slew)
        except (TypeError, ValueError) as exc:
            raise ValueError("IT2705: slew 必须为 MAX 或数值") from exc
        self.write(f"CURR:SLEW {value},(@{channel})")

    def set_arb_continuous(self, channel, flag=False):
        channel = self._validate_channel(channel)
        self.write(f"ARB:COUN {0 if flag else 1},(@{channel})")

    def set_arb_trigger_source(self, channel, source="BUS"):
        channel = self._validate_channel(channel)
        source = self._normalize_choice(source, {"IMM", "IMMEDIATE", "BUS", "MAN", "MANUAL"}, "trigger source")
        self.write(f"TRIG:TRAN:SOUR {source},(@{channel})")

    def arb_on(self, channel):
        channel = self._validate_channel(channel)
        self.write(f"INIT:TRAN (@{channel})")

    def arb_off(self, channel):
        self.arb_stop(channel)

    def arb_run(self, channels=None):
        if channels is not None:
            for channel in self._normalize_channels(channels):
                self.set_arb_trigger_source(channel, "BUS")
        self.trg()

    def arb_stop(self, channel=None):
        channels = self.VALID_CHANNELS if channel is None else [self._validate_channel(channel)]
        self.write(f"ABOR:TRAN (@{','.join(map(str, channels))})")

    def arb_status(self, channel):
        channel = self._validate_channel(channel)
        return self.query(f"STAT:OPER:COND? (@{channel})").strip()

    def restore_arb_trigger_source(self, channels=None):
        channels = self.VALID_CHANNELS if channels is None else self._normalize_channels(channels)
        for channel in channels:
            self.set_arb_trigger_source(channel, "IMM")

    def clear_arb_all_channels(self, total_channels=8):
        channels = range(1, int(total_channels) + 1)
        self.write(f"ABOR:TRAN (@{','.join(map(str, channels))})")
        for channel in channels:
            self._validate_channel(channel)
            self.set_function_mode(channel, "FIX")

    def exit_arb_current(self, channel):
        self.set_function_mode(channel, "FIX")

    def exit_arb_voltage(self, channel):
        self.set_function_mode(channel, "FIX")

    def trg(self):
        self.write("*TRG")

    @classmethod
    def _clamp_dlog_period(cls, sample_period, context=""):
        period = float(sample_period)
        clamped = min(max(period, cls.DLOG_PERIOD_MIN), cls.DLOG_PERIOD_MAX)
        if clamped != period:
            logger.warning(
                "IT2705 DLOG:PER %.6fs 超出范围，调整为 %.6fs%s",
                period,
                clamped,
                f" ({context})" if context else "",
            )
        return clamped

    def configure_datalog(self, channels, test_time, sample_period):
        self.configure_datalog_channels(channels, [], test_time, sample_period)

    def configure_datalog_channels(self, curr_channels, volt_channels, test_time, sample_period):
        curr_channels = self._normalize_channels(curr_channels) if curr_channels else []
        volt_channels = self._normalize_channels(volt_channels) if volt_channels else []
        if not curr_channels and not volt_channels:
            raise ValueError("IT2705: DLOG 至少指定一个电压或电流通道")
        if test_time <= 0:
            raise ValueError("IT2705: DLOG 记录时间必须大于 0")
        sample_period = self._clamp_dlog_period(sample_period, "configure_datalog")
        self.clear_status()
        self.stop_datalog()
        for channel in self.VALID_CHANNELS:
            self.write(f"SENS:DLOG:FUNC:CURR OFF,(@{channel})")
            self.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{channel})")
        for channel in curr_channels:
            self.write(f"SENS:DLOG:FUNC:CURR ON,(@{channel})")
        for channel in volt_channels:
            self.write(f"SENS:DLOG:FUNC:VOLT ON,(@{channel})")
        self.write(f"SENS:DLOG:TIME {float(test_time)}")
        self.write(f"SENS:DLOG:PER {sample_period}")
        self.write("TRIG:DLOG:SOUR IMM")

    @staticmethod
    def _validate_dlog_filename(dlog_file):
        filename = str(dlog_file).strip()
        if not filename or '"' in filename or "\n" in filename or "\r" in filename:
            raise ValueError("IT2705: 无效 DLOG 文件名")
        return filename

    def start_datalog(self, dlog_file="Dlog_file"):
        filename = self._validate_dlog_filename(dlog_file)
        self.write(f'INIT:DLOG "{filename}"')

    def trigger_datalog(self, channels=None):
        if channels is None:
            self.write("TRIG:DLOG")
        else:
            channel_list = ",".join(map(str, self._normalize_channels(channels)))
            self.write(f"TRIG:DLOG (@{channel_list})")

    def stop_datalog(self):
        self.write("ABOR:DLOG")

    def set_datalog_markers(self, marker1_s, marker2_s):
        if marker1_s >= marker2_s:
            raise ValueError("IT2705: marker1_s 必须小于 marker2_s")
        self.write(f"SENS:DLOG:MARK1:POIN {float(marker1_s)}")
        self.write(f"SENS:DLOG:MARK2:POIN {float(marker2_s)}")

    def fetch_datalog_all(self, channel):
        channel = self._validate_channel(channel)
        raw = self.query(f"FETC:DLOG:ALL? (@{channel})").strip()
        try:
            values = [float(value) for value in raw.split(",")]
        except ValueError as exc:
            raise ValueError(f"IT2705: 无法解析 DLOG 返回值 {raw!r}") from exc
        if len(values) != 10:
            raise ValueError(f"IT2705: DLOG:ALL 应返回 10 个值，实际为 {len(values)}")
        keys = (
            "ahour", "whour", "current_avg", "voltage_avg", "current_max",
            "voltage_max", "current_min", "voltage_min", "current_ptp", "voltage_ptp",
        )
        return dict(zip(keys, values, strict=True))

    def fetch_datalog_marker_results(self, channels, test_time):
        channels = self._normalize_channels(channels)
        self.set_datalog_markers(test_time * 0.1, test_time * 0.9)
        return {
            channel: self._query_float(f"FETC:DLOG:CURR? (@{channel})")
            for channel in channels
        }

    @staticmethod
    def _interruptible_sleep(duration, on_progress=None, stop_check=None):
        interval = 0.5
        elapsed = 0.0
        while elapsed < duration:
            if stop_check and stop_check():
                return False
            step = min(interval, duration - elapsed)
            time.sleep(step)
            elapsed += step
            if on_progress:
                on_progress(min(elapsed / duration, 1.0))
        if on_progress:
            on_progress(1.0)
        return True

    def fetch_current_by_datalog(
        self,
        channels,
        test_time,
        sample_period,
        marker1_percent=10,
        marker2_percent=90,
        on_progress=None,
        stop_check=None,
    ):
        channels = self._normalize_channels(channels)
        if not 0 <= marker1_percent < marker2_percent <= 100:
            raise ValueError("IT2705: DLOG marker 百分比必须满足 0 <= M1 < M2 <= 100")
        self.configure_datalog(channels, test_time, sample_period)
        for channel in channels:
            self.channel_on(channel)
        self.start_datalog()
        if not self._interruptible_sleep(test_time, on_progress, stop_check):
            self.stop_datalog()
            raise RuntimeError("IT2705: DLOG 采集已取消")
        self.set_datalog_markers(
            test_time * marker1_percent / 100.0,
            test_time * marker2_percent / 100.0,
        )
        return {
            channel: self._query_float(f"FETC:DLOG:CURR? (@{channel})")
            for channel in channels
        }

    def get_current_by_datalog(self, channels, test_time, sample_period):
        return self.fetch_current_by_datalog(channels, test_time, sample_period)

    def get_average_current(self, channels, duration):
        return self.fetch_current_by_datalog(
            channels, duration, sample_period=0.001, marker1_percent=0, marker2_percent=100
        )

    def fetch_by_datalog(self, curr_channels, volt_channels, test_time, sample_period):
        curr_channels = self._normalize_channels(curr_channels) if curr_channels else []
        volt_channels = self._normalize_channels(volt_channels) if volt_channels else []
        all_channels = sorted(set(curr_channels) | set(volt_channels))
        self.configure_datalog_channels(curr_channels, volt_channels, test_time, sample_period)
        for channel in all_channels:
            self.channel_on(channel)
        self.start_datalog()
        time.sleep(test_time)
        self.set_datalog_markers(test_time * 0.1, test_time * 0.9)
        curr_result = {
            channel: self._query_float(f"FETC:DLOG:CURR? (@{channel})")
            for channel in curr_channels
        }
        volt_result = {
            channel: self._query_float(f"FETC:DLOG:VOLT? (@{channel})")
            for channel in volt_channels
        }
        return curr_result, volt_result

    @staticmethod
    def format_current(current_a):
        abs_i = abs(current_a)
        if abs_i >= 1:
            return f"{current_a:.3f} A"
        if abs_i >= 1e-3:
            return f"{current_a * 1e3:.3f} mA"
        if abs_i >= 1e-6:
            return f"{current_a * 1e6:.3f} µA"
        if abs_i >= 1e-9:
            return f"{current_a * 1e9:.3f} nA"
        return f"{current_a:.3e} A"


def main():
    from log_config import setup_logging

    setup_logging()
    config_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "tests", "it2705_test_config.json"
        )
    )
    with open(config_path, encoding="utf-8") as config_file:
        config = json.load(config_file)
    channel = int(config.get("channel", 1))
    instrument = IT2705(config["resource"])
    try:
        logger.info("已连接: %s", instrument.identify())
        logger.info("通道 %s 输出状态: %s", channel, instrument.get_channel_state(channel))
        logger.info("电压测量值: %.6f V", instrument.fetch_voltage(channel))
        logger.info("电流测量值: %.6f A", instrument.fetch_current(channel))
    finally:
        instrument.disconnect()
        logger.info("已断开连接")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
