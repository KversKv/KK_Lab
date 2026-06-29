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

from log_config import get_logger

logger = get_logger(__name__)


class Keysight34461A:
    """Keysight 34461A 6½ 位数字万用表 (Truevolt 系列) 驱动。

    通过 VISA 与仪器通信，支持 DCV / ACV / DCI / ACI / 2W & 4W 电阻 /
    频率 / 周期 / 电容 / 温度 / 二极管 / 通断 等测量功能，并提供
    CONFigure + READ?/FETCh? 流程、触发与采样配置、统计计算等。
    """

    # —— 测量功能合法值 ——
    VALID_FUNCTIONS = (
        "VOLT", "VOLT:AC", "CURR", "CURR:AC",
        "RES", "FRES", "FREQ", "PER",
        "CAP", "TEMP", "DIOD", "CONT",
    )

    # —— DCV 量程 (V) ——
    DCV_RANGES = (0.1, 1.0, 10.0, 100.0, 1000.0)
    # —— DCI 量程 (A) ——
    DCI_RANGES = (1e-4, 1e-3, 1e-2, 1e-1, 1.0, 3.0, 10.0)
    # —— 2W/4W 电阻量程 (Ω) ——
    RES_RANGES = (1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9)

    # —— 合法 NPLC (积分时间, 电源周期数) ——
    VALID_NPLC = (0.02, 0.2, 1.0, 10.0, 100.0)

    # —— 触发源 ——
    VALID_TRIGGER_SOURCES = ("IMM", "EXT", "BUS", "INT")

    # —— 温度传感器类型 ——
    VALID_TEMP_TRANSDUCERS = ("FRTD", "RTD", "FTH", "THER", "TCO")

    # 仪器溢出标志值 (overload)
    OVERLOAD_THRESHOLD = 9.9e37

    def __init__(self, resource, visa_library=None, timeout_ms=10000):
        logger.debug("Keysight34461A __init__: resource=%s", resource)
        try:
            if visa_library:
                self.rm = pyvisa.ResourceManager(visa_library)
            else:
                self.rm = pyvisa.ResourceManager()
        except (OSError, ValueError) as e:
            logger.warning(
                "Keysight34461A: 系统 VISA 不可用(%s)，回退到 pyvisa-py('@py')", e
            )
            self.rm = pyvisa.ResourceManager('@py')
        logger.debug("Keysight34461A visalib=%s", self.rm.visalib)
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
            self.instr = self.rm.open_resource(f'TCPIP0::{resource_str}::hislip0::INSTR')
        self.instr.timeout = int(timeout_ms)
        self.instr.encoding = 'utf-8'
        logger.debug("Keysight34461A connected, timeout=%d ms", self.instr.timeout)

    # =========================
    # 基础 IO
    # =========================

    def _ensure_connected(self):
        if self.instr is None:
            raise RuntimeError("Keysight34461A: instrument not connected")

    def write(self, cmd):
        self._ensure_connected()
        logger.debug("34461A WRITE: %s", cmd)
        self.instr.write(cmd)

    def query(self, cmd):
        self._ensure_connected()
        logger.debug("34461A QUERY: %s", cmd)
        resp = self.instr.query(cmd)
        logger.debug("34461A RESP : %s", resp.strip() if isinstance(resp, str) else resp)
        return resp

    def _query_float(self, cmd):
        raw = self.query(cmd).strip()
        try:
            val = float(raw.split(",")[0])
        except ValueError as e:
            raise ValueError(f"无法将返回值解析为浮点数: {raw!r}") from e
        if abs(val) >= self.OVERLOAD_THRESHOLD:
            raise ValueError(f"仪器测量溢出/无有效值: {val}")
        return val

    @staticmethod
    def _normalize_choice(value, choices, name):
        v = str(value).strip().upper()
        norm_choices = [str(c).upper() for c in choices]
        if v not in norm_choices:
            raise ValueError(f"{name} 必须属于 {choices}, 收到: {value}")
        return v

    @staticmethod
    def _bool_state(enabled):
        return "ON" if enabled else "OFF"

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
        old_timeout = self.instr.timeout
        try:
            self.instr.timeout = 30000
            return self.query("*TST?").strip()
        finally:
            self.instr.timeout = old_timeout

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
    # 显示 / 系统
    # =========================

    def display_enable(self, enabled=True):
        self.write(f"DISPlay {self._bool_state(enabled)}")

    def display_text(self, text):
        self.write(f'DISPlay:TEXT "{text}"')

    def display_text_clear(self):
        self.write("DISPlay:TEXT:CLEar")

    def beep(self):
        self.write("SYSTem:BEEPer")

    def set_beeper(self, enabled=True):
        self.write(f"SYSTem:BEEPer:STATe {self._bool_state(enabled)}")

    def go_local(self):
        self.write("SYSTem:LOCal")

    def go_remote(self):
        self.write("SYSTem:REMote")

    # =========================
    # 测量功能配置 (SENSe)
    # =========================

    def set_function(self, function):
        """设置当前测量功能, function 见 VALID_FUNCTIONS。"""
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        self.write(f'FUNCtion "{func}"')

    def get_function(self):
        return self.query("FUNCtion?").strip().strip('"')

    def set_range(self, function, range_value, auto=False):
        """设置指定功能的量程。auto=True 时启用自动量程。"""
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        if auto:
            self.write(f"SENSe:{func}:RANGe:AUTO ON")
        else:
            self.write(f"SENSe:{func}:RANGe:AUTO OFF")
            self.write(f"SENSe:{func}:RANGe {range_value}")

    def get_range(self, function):
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        return self._query_float(f"SENSe:{func}:RANGe?")

    def set_auto_range(self, function, enabled=True):
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        self.write(f"SENSe:{func}:RANGe:AUTO {self._bool_state(enabled)}")

    def set_nplc(self, function, nplc):
        """设置积分时间 (NPLC)。仅对 VOLT/CURR/RES/FRES/TEMP 有效。"""
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        n = float(nplc)
        if n not in self.VALID_NPLC:
            logger.warning("NPLC %.3f 非标准值 %s, 仪器将就近选择", n, self.VALID_NPLC)
        self.write(f"SENSe:{func}:NPLC {n}")

    def get_nplc(self, function):
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        return self._query_float(f"SENSe:{func}:NPLC?")

    def set_aperture(self, function, aperture_s):
        """设置孔径积分时间 (秒)，与 NPLC 互斥。"""
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        self.write(f"SENSe:{func}:APERture:ENABled ON")
        self.write(f"SENSe:{func}:APERture {float(aperture_s)}")

    def set_autozero(self, function, enabled=True):
        func = self._normalize_choice(function, self.VALID_FUNCTIONS, "function")
        self.write(f"SENSe:{func}:ZERO:AUTO {self._bool_state(enabled)}")

    def set_input_impedance_auto(self, enabled=True):
        """DCV 输入阻抗自动 (ON: 高阻 >10GΩ on 100mV/1V/10V; OFF: 10MΩ)。"""
        self.write(f"SENSe:VOLTage:DC:IMPedance:AUTO {self._bool_state(enabled)}")

    # =========================
    # 便捷测量 (MEASure:*) —— 配置并立即返回结果
    # =========================

    def measure_voltage_dc(self, range_value=None, resolution=None):
        return self._measure("VOLTage:DC", range_value, resolution)

    def measure_voltage_ac(self, range_value=None, resolution=None):
        return self._measure("VOLTage:AC", range_value, resolution)

    def measure_current_dc(self, range_value=None, resolution=None):
        return self._measure("CURRent:DC", range_value, resolution)

    def measure_current_ac(self, range_value=None, resolution=None):
        return self._measure("CURRent:AC", range_value, resolution)

    def measure_resistance(self, range_value=None, resolution=None):
        return self._measure("RESistance", range_value, resolution)

    def measure_resistance_4w(self, range_value=None, resolution=None):
        return self._measure("FRESistance", range_value, resolution)

    def measure_frequency(self, range_value=None, resolution=None):
        return self._measure("FREQuency", range_value, resolution)

    def measure_period(self, range_value=None, resolution=None):
        return self._measure("PERiod", range_value, resolution)

    def measure_capacitance(self, range_value=None, resolution=None):
        return self._measure("CAPacitance", range_value, resolution)

    def measure_temperature(self):
        return self._query_float("MEASure:TEMPerature?")

    def measure_diode(self):
        return self._query_float("MEASure:DIODe?")

    def measure_continuity(self):
        return self._query_float("MEASure:CONTinuity?")

    def _measure(self, func, range_value=None, resolution=None):
        args = []
        if range_value is not None:
            args.append(str(range_value))
            if resolution is not None:
                args.append(str(resolution))
        elif resolution is not None:
            args.append("AUTO")
            args.append(str(resolution))
        arg_str = " " + ",".join(args) if args else ""
        return self._query_float(f"MEASure:{func}?{arg_str}")

    # =========================
    # CONFigure + READ?/FETCh? 流程
    # =========================

    def configure_voltage_dc(self, range_value=None, resolution=None):
        self._configure("VOLTage:DC", range_value, resolution)

    def configure_voltage_ac(self, range_value=None, resolution=None):
        self._configure("VOLTage:AC", range_value, resolution)

    def configure_current_dc(self, range_value=None, resolution=None):
        self._configure("CURRent:DC", range_value, resolution)

    def configure_current_ac(self, range_value=None, resolution=None):
        self._configure("CURRent:AC", range_value, resolution)

    def configure_resistance(self, range_value=None, resolution=None):
        self._configure("RESistance", range_value, resolution)

    def configure_resistance_4w(self, range_value=None, resolution=None):
        self._configure("FRESistance", range_value, resolution)

    def configure_frequency(self, range_value=None, resolution=None):
        self._configure("FREQuency", range_value, resolution)

    def configure_period(self, range_value=None, resolution=None):
        self._configure("PERiod", range_value, resolution)

    def configure_capacitance(self, range_value=None, resolution=None):
        self._configure("CAPacitance", range_value, resolution)

    def configure_temperature(self):
        self.write("CONFigure:TEMPerature")

    def _configure(self, func, range_value=None, resolution=None):
        args = []
        if range_value is not None:
            args.append(str(range_value))
            if resolution is not None:
                args.append(str(resolution))
        elif resolution is not None:
            args.append("AUTO")
            args.append(str(resolution))
        arg_str = " " + ",".join(args) if args else ""
        self.write(f"CONFigure:{func}{arg_str}")

    def get_configuration(self):
        return self.query("CONFigure?").strip()

    def read_value(self):
        """启动测量并返回单个读数 (INIT + FETC)。"""
        return self._query_float("READ?")

    def read_values(self):
        """启动测量并返回所有读数列表。"""
        raw = self.query("READ?").strip()
        return [float(x) for x in raw.split(",") if x]

    def fetch_value(self):
        return self._query_float("FETCh?")

    def fetch_values(self):
        raw = self.query("FETCh?").strip()
        return [float(x) for x in raw.split(",") if x]

    # =========================
    # 触发 / 采样子系统
    # =========================

    def set_trigger_source(self, source="IMM"):
        val = self._normalize_choice(source, self.VALID_TRIGGER_SOURCES, "trigger source")
        self.write(f"TRIGger:SOURce {val}")

    def get_trigger_source(self):
        return self.query("TRIGger:SOURce?").strip()

    def set_trigger_count(self, count):
        n = int(count)
        if n < 1:
            raise ValueError(f"trigger count 必须 >= 1, 收到: {count}")
        self.write(f"TRIGger:COUNt {n}")

    def get_trigger_count(self):
        return int(float(self.query("TRIGger:COUNt?").strip()))

    def set_trigger_delay(self, delay_s):
        self.write(f"TRIGger:DELay {float(delay_s)}")

    def set_trigger_delay_auto(self, enabled=True):
        self.write(f"TRIGger:DELay:AUTO {self._bool_state(enabled)}")

    def set_trigger_slope(self, slope="NEG"):
        val = self._normalize_choice(slope, ("POS", "NEG"), "trigger slope")
        self.write(f"TRIGger:SLOPe {val}")

    def set_sample_count(self, count):
        n = int(count)
        if n < 1:
            raise ValueError(f"sample count 必须 >= 1, 收到: {count}")
        self.write(f"SAMPle:COUNt {n}")

    def get_sample_count(self):
        return int(float(self.query("SAMPle:COUNt?").strip()))

    def set_sample_source(self, source="IMM"):
        val = self._normalize_choice(source, ("IMM", "TIM"), "sample source")
        self.write(f"SAMPle:SOURce {val}")

    def set_sample_timer(self, interval_s):
        self.write(f"SAMPle:TIMer {float(interval_s)}")

    def initiate(self):
        self.write("INITiate")

    def abort(self):
        self.write("ABORt")

    def trigger_bus(self):
        self.write("*TRG")

    # =========================
    # 数据缓冲区 (DATA)
    # =========================

    def data_points(self):
        return int(float(self.query("DATA:POINts?").strip()))

    def data_remove(self, count):
        raw = self.query(f"DATA:REMove? {int(count)}").strip()
        return [float(x) for x in raw.split(",") if x]

    # =========================
    # 数学 / 统计 (CALCulate)
    # =========================

    def enable_statistics(self, enabled=True):
        self.write(f"CALCulate:AVERage:STATe {self._bool_state(enabled)}")

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

    def stat_peak_to_peak(self):
        return self._query_float("CALCulate:AVERage:PTPeak?")

    def enable_null(self, enabled=True, offset=None):
        """启用 Null (相对) 运算。offset 为 None 时使用当前读数作为参考。"""
        self.write(f"CALCulate:SCALe:STATe {self._bool_state(enabled)}")
        if enabled:
            self.write("CALCulate:SCALe:FUNCtion NULL")
            if offset is None:
                self.write("CALCulate:SCALe:REFerence:AUTO ON")
            else:
                self.write("CALCulate:SCALe:REFerence:AUTO OFF")
                self.write(f"CALCulate:SCALe:REFerence {float(offset)}")

    def set_limit_test(self, lower, upper, enabled=True):
        """设置上下限超限检测。"""
        self.write(f"CALCulate:LIMit:LOWer {float(lower)}")
        self.write(f"CALCulate:LIMit:UPPer {float(upper)}")
        self.write(f"CALCulate:LIMit:STATe {self._bool_state(enabled)}")

    # =========================
    # 温度测量配置
    # =========================

    def set_temperature_transducer(self, transducer="FRTD", value=None):
        """设置温度传感器类型 (FRTD/RTD/FTH/THER/TCO) 及其参数。"""
        val = self._normalize_choice(transducer, self.VALID_TEMP_TRANSDUCERS, "transducer")
        self.write(f"SENSe:TEMPerature:TRANsducer:TYPE {val}")
        if value is not None:
            if val in ("FRTD", "RTD"):
                self.write(f"SENSe:TEMPerature:TRANsducer:{val}:RESistance {float(value)}")
            elif val == "TCO":
                self.write(f"SENSe:TEMPerature:TRANsducer:TCO:TYPE {value}")

    def set_temperature_unit(self, unit="C"):
        u = self._normalize_choice(unit, ("C", "F", "K"), "temperature unit")
        self.write(f"UNIT:TEMPerature {u}")

    # =========================
    # 数据记录 / 多次采样高层便捷方法
    # =========================

    def measure_average(self, function="VOLTage:DC", sample_count=10,
                        range_value=None, resolution=None):
        """配置指定功能, 连续采集 sample_count 个点并返回统计结果。

        返回 dict: {values, average, min, max, stddev, ptp, count}
        """
        self._configure(function, range_value, resolution)
        self.set_sample_count(sample_count)
        self.enable_statistics(True)
        self.clear_statistics()
        values = self.read_values()
        return {
            "values": values,
            "average": self.stat_average(),
            "min": self.stat_min(),
            "max": self.stat_max(),
            "stddev": self.stat_stddev(),
            "ptp": self.stat_peak_to_peak(),
            "count": self.stat_count(),
        }

    def measure_burst(self, function="VOLTage:DC", sample_count=100,
                      sample_interval_s=None, range_value=None, resolution=None):
        """以固定采样间隔连续采集一批读数 (Timer 采样)。返回读数列表。"""
        self._configure(function, range_value, resolution)
        self.set_trigger_source("IMM")
        self.set_sample_count(sample_count)
        if sample_interval_s is not None:
            self.set_sample_source("TIM")
            self.set_sample_timer(sample_interval_s)
        old_timeout = self.instr.timeout
        try:
            est = (sample_interval_s or 0.02) * sample_count
            self.instr.timeout = max(old_timeout, int(est * 1000) + 10000)
            return self.read_values()
        finally:
            self.instr.timeout = old_timeout

    # =========================
    # 连接管理
    # =========================

    def disconnect(self):
        """断开与仪器的连接。"""
        logger.debug("Keysight34461A disconnect called")
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

    # =========================
    # 工具方法
    # =========================

    def format_voltage(self, voltage_V):
        """将电压(V)格式化为人类易读单位字符串。"""
        abs_v = abs(voltage_V)
        if abs_v >= 1:
            return f"{voltage_V:.6f} V"
        elif abs_v >= 1e-3:
            return f"{voltage_V*1e3:.4f} mV"
        elif abs_v >= 1e-6:
            return f"{voltage_V*1e6:.3f} µV"
        else:
            return f"{voltage_V:.3e} V"

    def format_current(self, current_A):
        """将电流(A)格式化为人类易读单位字符串。"""
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.4f} A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.4f} mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.3f} µA"
        elif abs_i >= 1e-9:
            return f"{current_A*1e9:.3f} nA"
        else:
            return f"{current_A:.3e} A"

    def format_resistance(self, resistance_ohm):
        """将电阻(Ω)格式化为人类易读单位字符串。"""
        abs_r = abs(resistance_ohm)
        if abs_r >= 1e9:
            return f"{resistance_ohm/1e9:.4f} GΩ"
        elif abs_r >= 1e6:
            return f"{resistance_ohm/1e6:.4f} MΩ"
        elif abs_r >= 1e3:
            return f"{resistance_ohm/1e3:.4f} kΩ"
        else:
            return f"{resistance_ohm:.4f} Ω"

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

    resource_addr = "TCPIP0::K-34461A-22847.local::hislip0::INSTR"

    dmm = Keysight34461A(resource_addr)
    try:
        idn = dmm.identify()
        logger.info("已连接: %s", idn)

        dmm.reset()
        dmm.clear_status()

        # —— 直流电压 ——
        vdc = dmm.measure_voltage_dc()
        logger.info("DCV 测量: %s", dmm.format_voltage(vdc))

        # —— 直流电流 ——
        try:
            idc = dmm.measure_current_dc()
            logger.info("DCI 测量: %s", dmm.format_current(idc))
        except ValueError as e:
            logger.warning("DCI 测量无有效值: %s", e)

        # —— 2 线电阻 ——
        try:
            res = dmm.measure_resistance()
            logger.info("2W 电阻测量: %s", dmm.format_resistance(res))
        except ValueError as e:
            logger.warning("电阻测量无有效值(开路?): %s", e)

        # —— 交流电压 ——
        try:
            vac = dmm.measure_voltage_ac()
            logger.info("ACV 测量: %s", dmm.format_voltage(vac))
        except ValueError as e:
            logger.warning("ACV 测量无有效值: %s", e)

        # —— CONFigure + READ? 流程 + NPLC ——
        dmm.configure_voltage_dc(range_value=10)
        dmm.set_nplc("VOLT", 10)
        dmm.set_autozero("VOLT", True)
        v = dmm.read_value()
        logger.info("配置式 DCV 读数 (10V, 10NPLC): %s", dmm.format_voltage(v))

        # —— 多次采样统计 ——
        stats = dmm.measure_average("VOLTage:DC", sample_count=10, range_value=10)
        logger.info(
            "DCV 统计: avg=%s, min=%s, max=%s, stddev=%.3e, count=%d",
            dmm.format_voltage(stats["average"]),
            dmm.format_voltage(stats["min"]),
            dmm.format_voltage(stats["max"]),
            stats["stddev"],
            stats["count"],
        )

        errors = dmm.get_errors()
        logger.info("仪器错误队列: %s", errors)
    finally:
        dmm.disconnect()
        logger.info("已断开连接")
