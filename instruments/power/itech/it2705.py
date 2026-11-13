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
    # ELOG 外部记录仪（真机 2026-11 实测）：PER 范围 20us-60s（手册写 0.0001-1 不准）；
    # FETC:ELOG? 仅运行中可读（ABOR 后缓冲清空），maxrecords >30000 无响应，chanlist 多通道超时。
    ELOG_PERIOD_MIN = 20e-6
    ELOG_PERIOD_MAX = 60.0
    ELOG_FETCH_MAX_RECORDS = 20000
    INVALID_MEAS_THRESHOLD = 9.9e37
    # MEAS 按通道积分时间（SENS:APER）采集后才返回；面板可设到 20.48s（NPLC 1024），
    # 超过 VISA 超时会造成迟到响应污染缓冲区、后续读写全部错位。测量前临时压到该值（1 PLC）。
    MEAS_APER_FAST = 0.02
    # APER 查询结果按通道短 TTL 缓存（面板手动改 APER 最坏 TTL 秒后自愈）；
    # 驱动自身写 SENS:APER 时同步刷新缓存，避免测量路径每次多一次往返。
    MEAS_APER_CACHE_TTL_S = 5.0

    def __init__(self, resource, visa_library=None, timeout_ms=10000):
        super().__init__()
        self.resource = str(resource).strip()
        if not self.resource:
            raise ValueError("IT2705: resource 必填")
        self.visa_library = visa_library
        self.timeout_ms = int(timeout_ms)
        self.channel_module_models = {ch: "" for ch in self.VALID_CHANNELS}
        self._elog_funcs = {}
        self._aper_cache = {}  # {channel: (monotonic_ts, aperture_s)}
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
        # rm 不 close（共享 RM 误杀其它仪器连接，03 §43），仅关自身 session
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
        try:
            response = self.instrument.query(command)
        except Exception:
            # 超时后仪器迟到的响应会滞留接收缓冲区，污染后续所有读数，尽力清空
            try:
                self.instrument.clear()
            except Exception:
                logger.debug("IT2705: 清空接收缓冲区失败", exc_info=True)
            raise
        logger.debug("IT2705 RESP: %s", response.strip())
        return response

    def _query_float(self, command):
        raw = self.query(command).strip()
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"IT2705: 无法解析数值 {raw!r}") from exc
        if math.isnan(value) or abs(value) >= self.INVALID_MEAS_THRESHOLD:
            raise ValueError(f"IT2705: 无有效测量值 {raw!r}")
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

    def set_channel_range(self, channel):
        # N6705C 语义 = SENS:CURR:RANG:AUTO ON；IT2700 SENSe 子系统无电流
        # 量程/自动量程命令（仅 SENS:VOLT:RANG:AUTO 电压自动量程），此处 no-op。
        self._validate_channel(channel)
        logger.debug(
            "IT2705 set_channel_range: CH%s no-op（IT2700 无电流自动量程命令）",
            channel,
        )

    def set_channel_range_off(self, channel):
        # 同上，IT2700 无电流自动量程概念，no-op。
        self._validate_channel(channel)
        logger.debug(
            "IT2705 set_channel_range_off: CH%s no-op（IT2700 无电流自动量程命令）",
            channel,
        )

    def set_sense_mode(self, channel, mode="INT"):
        """设置通道 Sense 方式：Local/INT 为本地检测，4 Wire/EXT 为远端检测。

        手册 §15：SENSe[:REMote][:STATe] 0|OFF|1|ON,(@ch)。
        """
        channel = self._validate_channel(channel)
        mode_str = str(mode).strip().upper()
        mode_map = {
            "INT": False,
            "INTERNAL": False,
            "LOCAL": False,
            "EXT": True,
            "EXTERNAL": True,
            "4WIRE": True,
            "4 WIRE": True,
            "4-WIRE": True,
        }
        if mode_str not in mode_map:
            raise ValueError(
                f"Invalid sense mode '{mode}', expected 'LOCAL' or '4 WIRE'"
            )
        state = self._on_off(mode_map[mode_str])
        logger.debug("IT2705 set_sense_mode: CH%s = remote %s", channel, state)
        self.write(f"SENS {state},(@{channel})")

    PS_EMULATION_MODES = frozenset({"PS4Q", "PS2Q", "PS1Q"})

    def set_mode(self, channel, mode):
        channel = self._validate_channel(channel)
        mode = str(mode).strip()
        self.write(f"EMUL {mode},(@{channel})")
        if mode.upper() in self.PS_EMULATION_MODES:
            # 电流优先下 PS 通道按 CURR 定值输出，CURR:LIM 不起限流作用；
            # 必须切电压优先，电源模式（电压定值 + 限流）语义才成立
            self.write(f"FUNC VOLT,(@{channel})")

    def get_mode(self, channel):
        channel = self._validate_channel(channel)
        return self.query(f"EMUL? (@{channel})").strip()

    def set_voltagemode(self, channel):
        # 与 N6705C 同义：切电压表模式（手册 EMUL 列表含 VMETer）
        self.set_mode(channel, "VMETer")

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

    def _channel_aperture(self, channel):
        """读通道积分时间（短 TTL 缓存；驱动自身写 APER 时同步更新缓存）。"""
        now = time.monotonic()
        ts, cached = self._aper_cache.get(channel, (0.0, None))
        if cached is not None and now - ts < self.MEAS_APER_CACHE_TTL_S:
            return cached
        aperture = self._query_float(f"SENS:APER? (@{channel})")
        self._aper_cache[channel] = (now, aperture)
        return aperture

    def _set_channel_aperture(self, channel, aperture):
        self.write(f"SENS:APER {aperture},(@{channel})")
        self._aper_cache[channel] = (time.monotonic(), float(aperture))

    def _measure_scalar(self, channel, quantity):
        channel = self._validate_channel(channel)
        command = f"MEAS:{quantity}? (@{channel})"
        try:
            aperture = self._channel_aperture(channel)
        except Exception:
            logger.debug("IT2705: 积分时间查询失败，直接测量", exc_info=True)
            return self._query_float(command)
        if aperture <= self.MEAS_APER_FAST:
            return self._query_float(command)
        self._set_channel_aperture(channel, self.MEAS_APER_FAST)
        try:
            return self._query_float(command)
        finally:
            try:
                self._set_channel_aperture(channel, aperture)
            except Exception:
                logger.warning("IT2705: 恢复积分时间失败", exc_info=True)

    def measure_voltage(self, channel):
        return self._measure_scalar(channel, "VOLT")

    def measure_current(self, channel):
        return self._measure_scalar(channel, "CURR")

    def measure_power(self, channel):
        return self._measure_scalar(channel, "POW")

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

    def set_arb_sine(self, channel, dc_offset, amplitude_vrms, frequency, arb_type="VOLT"):
        channel = self._validate_channel(channel)
        if amplitude_vrms <= 0 or frequency <= 0:
            raise ValueError("IT2705: 正弦幅度与频率必须大于 0")
        tp = "CURR" if str(arb_type).strip().upper().startswith("CURR") else "VOLT"
        amplitude_peak = math.sqrt(2.0) * amplitude_vrms
        self.set_arb_type(channel, tp)
        self.set_arb_shape(channel, "SIN")
        self.write(f"ARB:{tp}:SIN:OFFS {float(dc_offset)},(@{channel})")
        self.write(f"ARB:{tp}:SIN:AMPL {amplitude_peak},(@{channel})")
        self.write(f"ARB:{tp}:SIN:FREQ {float(frequency)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_step(self, channel, v0, v1, t0, t1, arb_type="VOLT"):
        channel = self._validate_channel(channel)
        tp = "CURR" if str(arb_type).strip().upper().startswith("CURR") else "VOLT"
        self.set_arb_type(channel, tp)
        self.set_arb_shape(channel, "STEP")
        self.write(f"ARB:{tp}:STEP:STAR {float(v0)},(@{channel})")
        self.write(f"ARB:{tp}:STEP:END {float(v1)},(@{channel})")
        self.write(f"ARB:{tp}:STEP:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"ARB:{tp}:STEP:END:TIME {float(t1)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_staircase(self, channel, v0, v1, t0, t1, t2, steps, arb_type="VOLT"):
        channel = self._validate_channel(channel)
        if int(steps) < 1:
            raise ValueError("IT2705: steps 必须大于 0")
        tp = "CURR" if str(arb_type).strip().upper().startswith("CURR") else "VOLT"
        self.set_arb_type(channel, tp)
        self.set_arb_shape(channel, "STA")
        self.write(f"ARB:{tp}:STA:STAR {float(v0)},(@{channel})")
        self.write(f"ARB:{tp}:STA:END {float(v1)},(@{channel})")
        self.write(f"ARB:{tp}:STA:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"ARB:{tp}:STA:TIME {float(t1)},(@{channel})")
        self.write(f"ARB:{tp}:STA:END:TIME {float(t2)},(@{channel})")
        self.write(f"ARB:{tp}:STA:NST {int(steps)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_ramp(self, channel, v0, v1, t0, rt, t1, arb_type="VOLT"):
        """配置 ARB 斜坡波形：v0/v1 起止电平，t0 起始保持(s)，rt 上升(s)，t1 终止保持(s)。"""
        channel = self._validate_channel(channel)
        if rt <= 0:
            raise ValueError("IT2705: 斜坡上升时间必须大于 0")
        tp = "CURR" if str(arb_type).strip().upper().startswith("CURR") else "VOLT"
        self.set_arb_type(channel, tp)
        self.set_arb_shape(channel, "RAMP")
        self.write(f"ARB:{tp}:RAMP:STAR {float(v0)},(@{channel})")
        self.write(f"ARB:{tp}:RAMP:END {float(v1)},(@{channel})")
        self.write(f"ARB:{tp}:RAMP:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"ARB:{tp}:RAMP:RTIM {float(rt)},(@{channel})")
        self.write(f"ARB:{tp}:RAMP:END:TIME {float(t1)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_trapezoid(self, channel, v0, v1, t0, rt, tt, ft, t1, arb_type="VOLT"):
        """配置 ARB 梯形波形：v0 起始/v1 顶部电平，t0 起始保持，rt 上升，tt 顶部保持，ft 下降，t1 结束保持(s)。"""
        channel = self._validate_channel(channel)
        if rt <= 0 or ft <= 0:
            raise ValueError("IT2705: 梯形上升/下降时间必须大于 0")
        tp = "CURR" if str(arb_type).strip().upper().startswith("CURR") else "VOLT"
        self.set_arb_type(channel, tp)
        self.set_arb_shape(channel, "TRAP")
        self.write(f"ARB:{tp}:TRAP:STAR {float(v0)},(@{channel})")
        self.write(f"ARB:{tp}:TRAP:TOP {float(v1)},(@{channel})")
        self.write(f"ARB:{tp}:TRAP:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"ARB:{tp}:TRAP:RTIM {float(rt)},(@{channel})")
        self.write(f"ARB:{tp}:TRAP:TOP:TIME {float(tt)},(@{channel})")
        self.write(f"ARB:{tp}:TRAP:FTIM {float(ft)},(@{channel})")
        self.write(f"ARB:{tp}:TRAP:END:TIME {float(t1)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_exponential(self, channel, v0, v1, t0, tc, t1, arb_type="VOLT"):
        """配置 ARB 指数波形：v0/v1 起止电平，t0 起始延迟(s)，tc 时间常数(s)，t1 波形总时长(s)。"""
        channel = self._validate_channel(channel)
        if tc <= 0 or t1 <= 0:
            raise ValueError("IT2705: 指数时间常数与总时长必须大于 0")
        tp = "CURR" if str(arb_type).strip().upper().startswith("CURR") else "VOLT"
        self.set_arb_type(channel, tp)
        self.set_arb_shape(channel, "EXP")
        self.write(f"ARB:{tp}:EXP:STAR {float(v0)},(@{channel})")
        self.write(f"ARB:{tp}:EXP:END {float(v1)},(@{channel})")
        self.write(f"ARB:{tp}:EXP:STAR:TIME {float(t0)},(@{channel})")
        self.write(f"ARB:{tp}:EXP:TCON {float(tc)},(@{channel})")
        self.write(f"ARB:{tp}:EXP:TIME {float(t1)},(@{channel})")
        self.set_function_mode(channel, "ARB")

    def set_arb_none(self, channel, arb_type="VOLT"):
        """退出 ARB（等效 N6705C 面板 "No Arb Configured"）：恢复 FIX 模式。"""
        channel = self._validate_channel(channel)
        self.set_function_mode(channel, "FIX")

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

    _AUTO_SET_SPECIAL_VOLTAGES = [0.625, 0.67, 0.725, 0.78]

    @staticmethod
    def _align_voltage(v, special_values=None):
        if special_values is None:
            special_values = IT2705._AUTO_SET_SPECIAL_VOLTAGES
        grid_v = round(round(v / 0.05) * 0.05, 4)
        best = grid_v
        best_dist = abs(v - grid_v)
        for sv in special_values:
            dist = abs(v - sv)
            if dist < best_dist:
                best = sv
                best_dist = dist
        return best

    def prepare_force_high(self, channels, voltage_offset, current_limit,
                           monitor_channels=None):
        channels = self._normalize_channels(channels)
        logger.debug("prepare_force_high: channels=%s, voltage_offset=%s, current_limit=%s",
                     channels, voltage_offset, current_limit)
        if monitor_channels is None:
            monitor_channels = []
        elif isinstance(monitor_channels, int):
            monitor_channels = [monitor_channels]
        else:
            monitor_channels = list(monitor_channels)

        for ch in channels:
            self.set_mode(ch, "VMETer")
            self.channel_on(ch)

        time.sleep(0.5)

        measured_voltages = {}
        for ch in channels:
            measured_voltages[ch] = float(self.measure_voltage(ch))

        for ch in channels:
            new_v = measured_voltages[ch] + voltage_offset
            logger.debug("prepare_force_high: CH%s measured=%.4f V, forcing=%.4f V",
                         ch, measured_voltages[ch], new_v)
            self.set_mode(ch, "PS2Q")
            self.set_voltage(ch, new_v)
            self.set_current_limit(ch, current_limit)
            self.channel_on(ch)

        time.sleep(0.5)
        return measured_voltages

    def prepare_force_auto(self, channels, current_limit,
                           monitor_channels=None):
        channels = self._normalize_channels(channels)
        logger.debug("prepare_force_auto: channels=%s, current_limit=%s", channels, current_limit)
        if monitor_channels is None:
            monitor_channels = []
        elif isinstance(monitor_channels, int):
            monitor_channels = [monitor_channels]
        else:
            monitor_channels = list(monitor_channels)

        for ch in channels:
            self.set_mode(ch, "VMETer")
            self.channel_on(ch)

        time.sleep(0.5)

        measured_voltages = {}
        for ch in channels:
            measured_voltages[ch] = float(self.measure_voltage(ch))

        for ch in channels:
            new_v = self._align_voltage(measured_voltages[ch])
            logger.debug("prepare_force_auto: CH%s measured=%.4f V, aligned=%.4f V",
                         ch, measured_voltages[ch], new_v)
            self.set_mode(ch, "PS2Q")
            self.set_voltage(ch, new_v)
            self.set_current_limit(ch, current_limit)
            self.channel_on(ch)
            final_limit = 0.07 if new_v < 1.0 else 0.15
            self.set_current_limit(ch, final_limit)

        time.sleep(0.5)
        return measured_voltages

    def restore_channels_to_vmeter(self, channels):
        channels = self._normalize_channels(channels)
        logger.debug("restore_channels_to_vmeter: channels=%s", channels)
        for ch in channels:
            try:
                self.set_mode(ch, "VMETer")
                self.channel_on(ch)
            except Exception:
                pass

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

    def configure_elog(self, curr_channels, volt_channels, sample_period):
        """配置 ELOG 外部记录仪（不启动），返回实际生效的积分时间(s)。

        记录格式：每通道每条记录按使能项依次排列（如 V+I 为使能时 [V, I]）；
        MINMax 固定关闭以保持紧凑记录。OFF 仅下发到在位通道，避免空槽报 502。
        """
        curr_channels = self._normalize_channels(curr_channels) if curr_channels else []
        volt_channels = self._normalize_channels(volt_channels) if volt_channels else []
        targets = sorted(set(curr_channels) | set(volt_channels))
        if not targets:
            raise ValueError("IT2705: ELOG 至少指定一个电压或电流通道")
        period = float(sample_period)
        clamped = min(max(period, self.ELOG_PERIOD_MIN), self.ELOG_PERIOD_MAX)
        if clamped != period:
            logger.warning(
                "IT2705 ELOG:PER %.6fs 超出范围，调整为 %.6fs", period, clamped
            )
        populated = [
            ch for ch in self.VALID_CHANNELS if self.channel_module_models.get(ch)
        ]
        touched = populated or targets
        self.clear_status()
        self.write(f"ABOR:ELOG (@{','.join(map(str, touched))})")
        for channel in touched:
            if channel in targets:
                continue
            self.write(f"SENS:ELOG:FUNC:VOLT OFF,(@{channel})")
            self.write(f"SENS:ELOG:FUNC:CURR OFF,(@{channel})")
        self._elog_funcs = {}
        for channel in targets:
            want_v = channel in volt_channels
            want_i = channel in curr_channels
            self.write(
                f"SENS:ELOG:FUNC:VOLT {'ON' if want_v else 'OFF'},(@{channel})"
            )
            self.write(
                f"SENS:ELOG:FUNC:CURR {'ON' if want_i else 'OFF'},(@{channel})"
            )
            self.write(f"SENS:ELOG:FUNC:VOLT:MINM OFF,(@{channel})")
            self.write(f"SENS:ELOG:FUNC:CURR:MINM OFF,(@{channel})")
            self.write(f"SENS:ELOG:PER {clamped},(@{channel})")
            self._elog_funcs[channel] = (want_v, want_i)
        chanlist = ",".join(map(str, targets))
        self.write(f"TRIG:ELOG:SOUR IMM,(@{chanlist})")
        return clamped

    def start_elog(self):
        targets = sorted(self._elog_funcs)
        if not targets:
            raise RuntimeError("IT2705: 请先 configure_elog 再 start_elog")
        chanlist = ",".join(map(str, targets))
        self.write(f"INIT:ELOG (@{chanlist})")
        self.write(f"TRIG:ELOG (@{chanlist})")
        # 录制全程保持二进制块格式（BORD NORM=大端），避免逐通道取数时反复
        # 切换 FORM REAL/ASC 造成每通道 3 次额外往返；stop_elog 统一恢复 ASC。
        self.write("FORM REAL")
        self.write("FORM:BORD NORM")

    def fetch_elog_records(self, channel, max_records=None):
        """取回 ELOG 记录，返回 {"voltage": [...], "current": [...]}（SI 单位 V/A）。

        仅运行中可读；须在 start_elog 之后调用（FORM REAL 已生效），
        stop_elog 负责恢复 FORM ASC。
        """
        channel = self._validate_channel(channel)
        want_v, want_i = self._elog_funcs.get(channel, (False, False))
        result = {"voltage": [], "current": []}
        if not (want_v or want_i):
            return result
        max_records = int(max_records or self.ELOG_FETCH_MAX_RECORDS)
        max_records = min(max(max_records, 1), self.ELOG_FETCH_MAX_RECORDS)
        try:
            values = self.instrument.query_binary_values(
                f"FETC:ELOG? {max_records},(@{channel})",
                datatype="f",
                container=list,
                is_big_endian=True,
            )
        except Exception:
            try:
                self.instrument.clear()
            except Exception:
                logger.debug("IT2705: ELOG 取数异常后清空缓冲失败", exc_info=True)
            raise
        if want_v and want_i:
            result["voltage"] = [float(v) for v in values[0::2]]
            result["current"] = [float(v) for v in values[1::2]]
        elif want_v:
            result["voltage"] = [float(v) for v in values]
        else:
            result["current"] = [float(v) for v in values]
        return result

    def stop_elog(self, channels=None):
        if channels is None:
            channels = sorted(self._elog_funcs) or [
                ch for ch in self.VALID_CHANNELS if self.channel_module_models.get(ch)
            ]
        channels = self._normalize_channels(channels)
        try:
            self.write(f"ABOR:ELOG (@{','.join(map(str, channels))})")
        finally:
            # 与 start_elog 的 FORM REAL 配对，恢复 ASCII 响应格式
            try:
                self.write("FORM ASC")
            except Exception:
                logger.warning("IT2705: 恢复 FORM ASC 失败", exc_info=True)

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
