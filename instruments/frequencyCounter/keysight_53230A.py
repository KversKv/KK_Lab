import os
import sys
import time

import pyvisa

if __name__ == "__main__" and __package__ is None:
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from log_config import get_logger

logger = get_logger(__name__)


class Keysight53230A:

    VALID_CHANNELS = (1, 2)
    VALID_COUPLING = ("AC", "DC")
    VALID_IMPEDANCE = ("50", "1E6")
    VALID_SLOPE = ("POS", "NEG")
    VALID_ATTENUATION = (1, 10)
    VALID_FILTER = ("ON", "OFF")
    VALID_GATE_SOURCE = ("TIME", "ADV", "EXT", "IMM")
    VALID_GATE_POLARITY = ("POS", "NEG")
    VALID_REFERENCE = ("INT", "EXT")
    INVALID_MEAS_THRESHOLD = 9.9e37

    def __init__(self, resource, visa_library=None, timeout_ms=10000):
        logger.debug("Keysight53230A __init__: resource=%s", resource)
        try:
            if visa_library:
                self.rm = pyvisa.ResourceManager(visa_library)
            else:
                self.rm = pyvisa.ResourceManager()
        except (OSError, ValueError) as e:
            logger.warning(
                "Keysight53230A: 系统 VISA 不可用(%s)，回退到 pyvisa-py('@py')", e
            )
            self.rm = pyvisa.ResourceManager('@py')
        logger.debug("Keysight53230A visalib=%s", self.rm.visalib)
        resource_str = str(resource).strip()
        upper = resource_str.upper()
        visa_prefixes = ("TCPIP", "USB", "GPIB", "ASRL", "VXI", "PXI", "HISLIP")
        is_visa_resource = (
            "::" in resource_str
            and (upper.endswith("::INSTR") or upper.endswith("::SOCKET")
                 or upper.startswith(visa_prefixes))
        )
        if is_visa_resource:
            self.instr = self.rm.open_resource(resource_str)
        else:
            self.instr = self.rm.open_resource(f'TCPIP0::{resource_str}::inst0::INSTR')
        self.instr.timeout = int(timeout_ms)
        self.instr.encoding = 'utf-8'
        logger.debug("Keysight53230A connected, timeout=%d ms", self.instr.timeout)

    # =========================
    # 基础 IO
    # =========================

    def _ensure_connected(self):
        if self.instr is None:
            raise RuntimeError("Keysight53230A: instrument not connected")

    def write(self, cmd):
        self._ensure_connected()
        logger.debug("53230A WRITE: %s", cmd)
        self.instr.write(cmd)

    def query(self, cmd):
        self._ensure_connected()
        logger.debug("53230A QUERY: %s", cmd)
        resp = self.instr.query(cmd)
        logger.debug("53230A RESP : %s", resp.strip() if isinstance(resp, str) else resp)
        return resp

    def _query_float(self, cmd):
        raw = self.query(cmd).strip()
        try:
            val = float(raw)
        except ValueError as e:
            raise ValueError(f"无法将返回值解析为浮点数: {raw!r}") from e
        if abs(val) >= self.INVALID_MEAS_THRESHOLD:
            raise ValueError(f"仪器当前无有效测量值: {val}")
        return val

    @classmethod
    def _validate_channel(cls, channel):
        if int(channel) not in cls.VALID_CHANNELS:
            raise ValueError(f"无效通道号: {channel}，仅支持 1 或 2")
        return int(channel)

    @staticmethod
    def _normalize_choice(value, choices, name):
        v = str(value).strip().upper()
        norm_choices = [str(c).upper() for c in choices]
        if v not in norm_choices:
            raise ValueError(f"{name} 必须属于 {choices}, 收到: {value}")
        return v

    # =========================
    # IEEE 488 公共指令
    # =========================

    def identify(self):
        return self.query("*IDN?").strip()

    def reset(self):
        self.write("*RST")
        self.query_opc(timeout_s=10.0)

    def clear_status(self):
        self.write("*CLS")

    def self_test(self):
        return self.query("*TST?").strip()

    def query_opc(self, timeout_s=5.0):
        old_timeout = self.instr.timeout
        try:
            self.instr.timeout = int(timeout_s * 1000)
            resp = self.query("*OPC?").strip()
            return resp.startswith("1")
        finally:
            self.instr.timeout = old_timeout

    def get_errors(self, max_count=20):
        errors = []
        for _ in range(max_count):
            err = self.query("SYSTem:ERRor?").strip()
            errors.append(err)
            if err.startswith("+0") or err.startswith("0,") or "No error" in err:
                break
        return errors

    # =========================
    # 输入通道 (INPut1 / INPut2)
    # =========================

    def set_input_coupling(self, channel, coupling="DC"):
        ch = self._validate_channel(channel)
        val = self._normalize_choice(coupling, self.VALID_COUPLING, "coupling")
        self.write(f"INPut{ch}:COUPling {val}")

    def get_input_coupling(self, channel):
        ch = self._validate_channel(channel)
        return self.query(f"INPut{ch}:COUPling?").strip()

    def set_input_impedance(self, channel, impedance="1E6"):
        ch = self._validate_channel(channel)
        val = str(impedance).strip().upper()
        if val in ("1M", "1MEG", "1E+6", "1.0E6", "1000000"):
            val = "1E6"
        if val not in self.VALID_IMPEDANCE:
            raise ValueError(
                f"impedance 必须属于 {self.VALID_IMPEDANCE}, 收到: {impedance}"
            )
        self.write(f"INPut{ch}:IMPedance {val}")

    def get_input_impedance(self, channel):
        ch = self._validate_channel(channel)
        return self._query_float(f"INPut{ch}:IMPedance?")

    def set_input_attenuation(self, channel, attenuation=1):
        ch = self._validate_channel(channel)
        a = int(attenuation)
        if a not in self.VALID_ATTENUATION:
            raise ValueError(
                f"attenuation 必须属于 {self.VALID_ATTENUATION}, 收到: {attenuation}"
            )
        self.write(f"INPut{ch}:ATTenuation {a}")

    def get_input_attenuation(self, channel):
        ch = self._validate_channel(channel)
        return self._query_float(f"INPut{ch}:ATTenuation?")

    def set_input_lowpass_filter(self, channel, enabled):
        ch = self._validate_channel(channel)
        state = "ON" if enabled else "OFF"
        self.write(f"INPut{ch}:FILTer:LPASs:STATe {state}")

    def get_input_lowpass_filter(self, channel):
        ch = self._validate_channel(channel)
        resp = self.query(f"INPut{ch}:FILTer:LPASs:STATe?").strip()
        return resp in ("1", "ON")

    def set_input_range(self, channel, volt_range):
        ch = self._validate_channel(channel)
        self.write(f"INPut{ch}:RANGe {float(volt_range)}")

    def get_input_range(self, channel):
        ch = self._validate_channel(channel)
        return self._query_float(f"INPut{ch}:RANGe?")

    def set_input_range_auto(self, channel, enabled=True):
        ch = self._validate_channel(channel)
        state = "ON" if enabled else "OFF"
        self.write(f"INPut{ch}:RANGe:AUTO {state}")

    def set_trigger_level(self, channel, level):
        ch = self._validate_channel(channel)
        self.write(f"INPut{ch}:LEVel {float(level)}")

    def get_trigger_level(self, channel):
        ch = self._validate_channel(channel)
        return self._query_float(f"INPut{ch}:LEVel?")

    def set_trigger_level_auto(self, channel, enabled=True):
        ch = self._validate_channel(channel)
        state = "ON" if enabled else "OFF"
        self.write(f"INPut{ch}:LEVel:AUTO {state}")

    def set_trigger_level_relative(self, channel, percent):
        ch = self._validate_channel(channel)
        p = float(percent)
        if not 10.0 <= p <= 90.0:
            raise ValueError(
                f"relative level 必须在 10~90% 之间, 收到: {percent}"
            )
        self.write(f"INPut{ch}:LEVel:RELative {p}")

    def set_trigger_slope(self, channel, slope="POS"):
        ch = self._validate_channel(channel)
        val = self._normalize_choice(slope, self.VALID_SLOPE, "slope")
        self.write(f"INPut{ch}:SLOPe {val}")

    def get_trigger_slope(self, channel):
        ch = self._validate_channel(channel)
        return self.query(f"INPut{ch}:SLOPe?").strip()

    def set_trigger_hysteresis(self, channel, level):
        ch = self._validate_channel(channel)
        lv = int(level)
        if lv not in (0, 1, 2):
            raise ValueError(f"hysteresis 必须是 0/1/2, 收到: {level}")
        self.write(f"INPut{ch}:NREJection {lv}")

    def configure_input(
        self,
        channel,
        coupling="DC",
        impedance="1E6",
        attenuation=1,
        lowpass=False,
        slope="POS",
        level=None,
        level_auto=None,
    ):
        ch = self._validate_channel(channel)
        self.set_input_coupling(ch, coupling)
        self.set_input_impedance(ch, impedance)
        self.set_input_attenuation(ch, attenuation)
        self.set_input_lowpass_filter(ch, lowpass)
        self.set_trigger_slope(ch, slope)
        if level_auto is True:
            self.set_trigger_level_auto(ch, True)
        elif level is not None:
            self.set_trigger_level_auto(ch, False)
            self.set_trigger_level(ch, level)

    # =========================
    # 门限 (Gate) 配置 - SENSe:FREQuency:GATE
    # =========================

    def set_gate_time(self, gate_time_s):
        self.write(f"SENSe:FREQuency:GATE:TIME {float(gate_time_s)}")
        self.write("SENSe:FREQuency:GATE:SOURce TIME")

    def get_gate_time(self):
        return self._query_float("SENSe:FREQuency:GATE:TIME?")

    def set_gate_source(self, source="TIME"):
        val = self._normalize_choice(source, self.VALID_GATE_SOURCE, "gate source")
        self.write(f"SENSe:FREQuency:GATE:SOURce {val}")

    def get_gate_source(self):
        return self.query("SENSe:FREQuency:GATE:SOURce?").strip()

    def set_gate_polarity(self, polarity="POS"):
        val = self._normalize_choice(polarity, self.VALID_GATE_POLARITY, "gate polarity")
        self.write(f"SENSe:FREQuency:GATE:POLarity {val}")

    # =========================
    # 测量功能 & 分辨率
    # =========================

    def set_function(self, func, channel=1):
        ch = self._validate_channel(channel)
        func = str(func).strip().upper()
        mapping = {
            "FREQ": f'"FREQ (@{ch})"',
            "FREQUENCY": f'"FREQ (@{ch})"',
            "PER": f'"PER (@{ch})"',
            "PERIOD": f'"PER (@{ch})"',
            "DCYC": f'"DCYCle (@{ch})"',
            "DUTY": f'"DCYCle (@{ch})"',
            "PWID": f'"PWIDth (@{ch})"',
            "NWID": f'"NWIDth (@{ch})"',
            "RISE": f'"RTIMe (@{ch})"',
            "FALL": f'"FTIMe (@{ch})"',
        }
        if func not in mapping:
            raise ValueError(
                f"func 必须属于 {list(mapping.keys())}, 收到: {func}"
            )
        self.write(f"FUNCtion:ON {mapping[func]}")

    def get_function(self):
        return self.query("FUNCtion:ON?").strip()

    # =========================
    # 便捷测量 (MEASure:*)
    # =========================

    def measure_frequency(self, channel=1, expected=None, resolution=None):
        ch = self._validate_channel(channel)
        args = []
        if expected is not None:
            args.append(str(expected))
            if resolution is not None:
                args.append(str(resolution))
        arg_str = ", ".join(args)
        if arg_str:
            cmd = f"MEASure:FREQuency? {arg_str}, (@{ch})"
        else:
            cmd = f"MEASure:FREQuency? (@{ch})"
        return self._query_float(cmd)

    def measure_period(self, channel=1):
        ch = self._validate_channel(channel)
        return self._query_float(f"MEASure:PERiod? (@{ch})")

    def measure_duty_cycle(self, channel=1):
        ch = self._validate_channel(channel)
        return self._query_float(f"MEASure:DCYCle? (@{ch})")

    def measure_pulse_width(self, channel=1, positive=True):
        ch = self._validate_channel(channel)
        cmd = "PWIDth" if positive else "NWIDth"
        return self._query_float(f"MEASure:{cmd}? (@{ch})")

    def measure_rise_time(self, channel=1):
        ch = self._validate_channel(channel)
        return self._query_float(f"MEASure:RTIMe? (@{ch})")

    def measure_fall_time(self, channel=1):
        ch = self._validate_channel(channel)
        return self._query_float(f"MEASure:FTIMe? (@{ch})")

    # =========================
    # CONFigure + READ?/FETCh? 流程
    # =========================

    def configure_frequency(self, channel=1, expected=None, resolution=None):
        ch = self._validate_channel(channel)
        args = []
        if expected is not None:
            args.append(str(expected))
            if resolution is not None:
                args.append(str(resolution))
        arg_str = ", ".join(args)
        if arg_str:
            self.write(f"CONFigure:FREQuency {arg_str}, (@{ch})")
        else:
            self.write(f"CONFigure:FREQuency (@{ch})")

    def configure_period(self, channel=1):
        ch = self._validate_channel(channel)
        self.write(f"CONFigure:PERiod (@{ch})")

    def set_sample_count(self, count):
        n = int(count)
        if n < 1:
            raise ValueError(f"sample count 必须 >= 1, 收到: {count}")
        self.write(f"SAMPle:COUNt {n}")

    def get_sample_count(self):
        return int(float(self.query("SAMPle:COUNt?").strip()))

    def set_trigger_count(self, count):
        n = int(count)
        if n < 1:
            raise ValueError(f"trigger count 必须 >= 1, 收到: {count}")
        self.write(f"TRIGger:COUNt {n}")

    def initiate(self):
        self.write("INITiate:IMMediate")

    def abort(self):
        self.write("ABORt")

    def read_value(self):
        return self._query_float("READ?")

    def read_values(self, count=None):
        if count is not None:
            self.set_sample_count(count)
        raw = self.query("READ?").strip()
        return [float(x) for x in raw.split(",") if x]

    def fetch_values(self):
        raw = self.query("FETCh?").strip()
        return [float(x) for x in raw.split(",") if x]

    def data_points(self):
        return int(float(self.query("DATA:POINts?").strip()))

    def data_remove(self, count, wait=False):
        cmd = f"DATA:REMove? {int(count)}"
        if wait:
            cmd += ", WAIT"
        raw = self.query(cmd).strip()
        return [float(x) for x in raw.split(",") if x]

    # =========================
    # 触发子系统 (TRIGger)
    # =========================

    def set_trigger_source(self, source="IMM"):
        val = str(source).strip().upper()
        allowed = ("IMM", "IMMEDIATE", "EXT", "EXTERNAL", "BUS")
        if val not in allowed:
            raise ValueError(
                f"trigger source 必须属于 {allowed}, 收到: {source}"
            )
        self.write(f"TRIGger:SOURce {val}")

    def get_trigger_source(self):
        return self.query("TRIGger:SOURce?").strip()

    def set_trigger_slope_edge(self, slope="POS"):
        val = self._normalize_choice(slope, self.VALID_SLOPE, "trigger slope")
        self.write(f"TRIGger:SLOPe {val}")

    def set_trigger_delay(self, delay_s):
        self.write(f"TRIGger:DELay {float(delay_s)}")

    def trigger_bus(self):
        self.write("*TRG")

    # =========================
    # CALCulate:STATistic 统计
    # =========================

    def enable_statistics(self, enabled=True):
        state = "ON" if enabled else "OFF"
        self.write(f"CALCulate:STATistic:STATe {state}")

    def clear_statistics(self):
        self.write("CALCulate:AVERage:CLEar")

    def stat_average(self):
        return self._query_float("CALCulate:AVERage:AVERage?")

    def stat_min(self):
        return self._query_float("CALCulate:AVERage:MINimum?")

    def stat_max(self):
        return self._query_float("CALCulate:AVERage:MAXimum?")

    def stat_stddev(self):
        return self._query_float("CALCulate:AVERage:SDEViation?")

    def stat_count(self):
        return int(float(self.query("CALCulate:AVERage:COUNt?").strip()))

    def stat_all(self):
        raw = self.query("CALCulate:AVERage:ALL?").strip()
        parts = [float(x) for x in raw.split(",") if x]
        keys = ("average", "stddev", "min", "max", "count")
        return dict(zip(keys, parts))

    # =========================
    # 参考时基 (ROSCillator)
    # =========================

    def set_reference_source(self, source="INT"):
        val = self._normalize_choice(source, self.VALID_REFERENCE, "reference")
        self.write(f"ROSCillator:SOURce {val}")

    def get_reference_source(self):
        return self.query("ROSCillator:SOURce?").strip()

    def set_reference_auto(self, enabled=True):
        state = "ON" if enabled else "OFF"
        self.write(f"ROSCillator:SOURce:AUTO {state}")

    def get_reference_external_frequency(self):
        return self._query_float("ROSCillator:EXTernal:FREQuency?")

    def set_reference_external_frequency(self, freq_hz):
        self.write(f"ROSCillator:EXTernal:FREQuency {float(freq_hz)}")

    # =========================
    # 高层便捷方法
    # =========================

    def measure_frequency_averaged(
        self,
        channel=1,
        sample_count=10,
        gate_time=None,
        expected=None,
        resolution=None,
    ):
        self._validate_channel(channel)
        self.configure_frequency(channel, expected=expected, resolution=resolution)
        if gate_time is not None:
            self.set_gate_time(gate_time)
        self.set_sample_count(sample_count)
        self.enable_statistics(True)
        self.clear_statistics()
        values = self.read_values()
        stats = self.stat_all()
        return {
            "values": values,
            "average": stats.get("average"),
            "stddev": stats.get("stddev"),
            "min": stats.get("min"),
            "max": stats.get("max"),
            "count": stats.get("count"),
        }

    def disconnect(self):
        """
        断开与仪器的连接
        """
        logger.debug("Keysight53230A disconnect called")
        if self.instr is not None:
            try:
                self.instr.close()
            except Exception:
                pass
            self.instr = None
        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
            self.rm = None

    def close(self):
        self.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()

    def format_current(self, current_A):
        """
        将电流(A)格式化为人类易读单位字符串
        """
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

    def _normalize_channels(self, channels):
        if isinstance(channels, int):
            return [channels]
        return list(channels)

    def _channel_list_str(self, channels):
        return ",".join(str(ch) for ch in channels)

    @staticmethod
    def _interruptible_sleep(duration, on_progress=None, stop_check=None,
                             progress_start=0.0, progress_end=1.0):
        if duration <= 0:
            if on_progress:
                on_progress(progress_end)
            return
        interval = 0.5
        elapsed = 0.0
        while elapsed < duration:
            if stop_check and stop_check():
                return
            step = min(interval, duration - elapsed)
            time.sleep(step)
            elapsed += step
            if on_progress:
                frac = min(elapsed / duration, 1.0)
                on_progress(progress_start + frac * (progress_end - progress_start))



if __name__ == "__main__":
    from log_config import setup_logging
    setup_logging()
    resource_addr = 'USB0::0x0957::0x1907::MY62340214::INSTR'
    CHANNEL = 1

    counter = Keysight53230A(resource_addr)
    try:
        idn = counter.identify()
        logger.info("已连接: %s", idn)
        test_freq = counter.measure_frequency(CHANNEL)
        logger.info("测试频率: %f Hz", test_freq)
    finally:
        counter.disconnect()
        logger.info("已断开连接")
