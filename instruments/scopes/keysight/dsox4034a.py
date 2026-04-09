import time
from typing import Optional, Tuple, Dict, Any

import pyvisa
from pyvisa import VisaIOError


class ScopeError(Exception):
    """示波器通用异常"""
    pass


class InstrumentConnectionError(ScopeError):
    """仪器连接异常"""
    pass


class MeasurementError(ScopeError):
    """测量值异常"""
    pass


class DSOX4034A:
    """
    Keysight/Agilent DSOX4034A SCPI 驱动
    """

    INVALID_MEAS_THRESHOLD = 1e36

    def __init__(
        self,
        resource: str,
        visa_library: Optional[str] = None,
        timeout_ms: int = 10000,
        open_timeout_ms: int = 5000,
        read_termination: str = '\n',
        write_termination: str = '\n',
        encoding: str = 'utf-8',
        query_delay: float = 0.05,
        opc_timeout_s: float = 5.0,
        auto_clear: bool = True,
        auto_stop_before_measure: bool = False,
        debug: bool = False,
    ):
        self.resource = resource
        self.visa_library = visa_library
        self.timeout_ms = timeout_ms
        self.open_timeout_ms = open_timeout_ms
        self.read_termination = read_termination
        self.write_termination = write_termination
        self.encoding = encoding
        self.query_delay = query_delay
        self.opc_timeout_s = opc_timeout_s
        self.auto_clear = auto_clear
        self.auto_stop_before_measure = auto_stop_before_measure
        self.debug = debug

        self.rm = None
        self.instrument = None
        self.idn = None

        self.connect()

    # =========================
    # 生命周期管理
    # =========================

    def connect(self):
        if self.instrument is not None:
            return

        try:
            if self.visa_library:
                self.rm = pyvisa.ResourceManager(self.visa_library)
            else:
                self.rm = pyvisa.ResourceManager()

            self._log(f'Using VISA library: {self.rm.visalib}')
            self._log(f'Available resources: {self.rm.list_resources()}')
            self._log(f'Opening resource: {self.resource}')

            self.instrument = self.rm.open_resource(
                self.resource,
                open_timeout=self.open_timeout_ms
            )

            self.instrument.timeout = self.timeout_ms
            self.instrument.encoding = self.encoding
            self.instrument.read_termination = self.read_termination
            self.instrument.write_termination = self.write_termination
            self.instrument.chunk_size = 1024 * 1024

            if self.auto_clear:
                self.clear_status()

            self.idn = self.query('*IDN?').strip()
            self._log(f'Connected instrument: {self.idn}')

        except Exception as e:
            self.instrument = None
            raise InstrumentConnectionError(
                f'无法连接仪器: {self.resource}, 错误: {e}'
            ) from e

    def disconnect(self):
        if self.instrument is not None:
            try:
                self.instrument.close()
            finally:
                self.instrument = None

        if self.rm is not None:
            try:
                self.rm.close()
            finally:
                self.rm = None

    def close(self):
        self.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.disconnect()

    # =========================
    # 基础 IO
    # =========================

    def _log(self, msg: str):
        if self.debug:
            print(f'[DSOX4034A] {msg}')

    def _ensure_connected(self):
        if self.instrument is None:
            raise InstrumentConnectionError('仪器尚未连接')

    def write(self, cmd: str):
        self._ensure_connected()
        self._log(f'WRITE: {cmd}')
        self.instrument.write(cmd)

    def read(self) -> str:
        self._ensure_connected()
        data = self.instrument.read()
        self._log(f'READ: {data}')
        return data

    def query(self, cmd: str, delay: Optional[float] = None) -> str:
        self._ensure_connected()
        d = self.query_delay if delay is None else delay
        self._log(f'QUERY: {cmd}')
        if d and d > 0:
            time.sleep(d)
        data = self.instrument.query(cmd)
        self._log(f'RESP: {data}')
        return data

    def query_opc(self, timeout_s: Optional[float] = None) -> bool:
        self._ensure_connected()
        old_timeout = self.instrument.timeout
        try:
            if timeout_s is None:
                timeout_s = self.opc_timeout_s
            self.instrument.timeout = int(timeout_s * 1000)
            resp = self.query('*OPC?', delay=0.0).strip()
            return resp == '1'
        finally:
            self.instrument.timeout = old_timeout

    # =========================
    # 状态/控制
    # =========================

    def identify_instrument(self) -> str:
        return self.query('*IDN?').strip()

    def reset(self):
        self.write('*RST')
        self.query_opc(timeout_s=10.0)

    def clear_status(self):
        self.write('*CLS')

    def get_errors(self, max_count: int = 20):
        errors = []
        for _ in range(max_count):
            err = self.query(':SYSTem:ERRor?').strip()
            errors.append(err)
            if err.startswith('+0') or 'No error' in err or '0,' in err:
                break
        return errors

    def run(self):
        self.write(':RUN')

    def stop(self):
        self.write(':STOP')

    def single(self):
        self.write(':SINGLE')

    def autoscale(self):
        self.write(':AUToscale')
        self.query_opc(timeout_s=10.0)

    # =========================
    # 通道
    # =========================

    @staticmethod
    def _validate_channel(channel: int):
        if channel not in (1, 2, 3, 4):
            raise ValueError(f'无效通道号: {channel}，仅支持 1~4')

    def set_channel_display(self, channel: int, on: bool):
        self._validate_channel(channel)
        self.write(f':CHANnel{channel}:DISPlay {"ON" if on else "OFF"}')

    def is_channel_displayed(self, channel: int) -> bool:
        self._validate_channel(channel)
        resp = self.query(f':CHANnel{channel}:DISPlay?').strip()
        return resp in ('1', 'ON')

    def set_channel_scale(self, channel: int, volts_per_div: float):
        self._validate_channel(channel)
        self.write(f':CHANnel{channel}:SCALe {volts_per_div}')

    def get_channel_scale(self, channel: int) -> float:
        self._validate_channel(channel)
        return self._safe_float(self.query(f':CHANnel{channel}:SCALe?'))

    def set_channel_offset(self, channel: int, offset: float):
        self._validate_channel(channel)
        self.write(f':CHANnel{channel}:OFFSet {offset}')

    def get_channel_offset(self, channel: int) -> float:
        self._validate_channel(channel)
        return self._safe_float(self.query(f':CHANnel{channel}:OFFSet?'))

    # =========================
    # 时基
    # =========================

    def set_timebase_scale(self, seconds_per_div: float):
        self.write(f':TIMebase:SCALe {seconds_per_div}')

    def get_timebase_scale(self) -> float:
        return self._safe_float(self.query(':TIMebase:SCALe?'))

    def set_timebase_position(self, position_s: float):
        self.write(f':TIMebase:POSition {position_s}')

    def get_timebase_position(self) -> float:
        return self._safe_float(self.query(':TIMebase:POSition?'))

    # =========================
    # 触发
    # =========================

    def set_trigger_edge(self, source_channel: int, level: float, slope: str = 'POS'):
        self._validate_channel(source_channel)
        slope = slope.upper()
        if slope not in ('POS', 'NEG', 'EITH'):
            raise ValueError('slope 必须是 POS / NEG / EITH')

        self.write(':TRIGger:MODE EDGE')
        self.write(f':TRIGger:EDGE:SOURce CHANnel{source_channel}')
        self.write(f':TRIGger:EDGE:SLOPe {slope}')
        self.write(f':TRIGger:LEVel CHANnel{source_channel},{level}')

    def get_trigger_source(self) -> str:
        return self.query(':TRIGger:EDGE:SOURce?').strip()

    # =========================
    # 测量
    # =========================

    def _safe_float(self, value: str) -> float:
        try:
            v = float(value.strip())
        except Exception as e:
            raise MeasurementError(f'无法将返回值解析为浮点数: {value!r}') from e

        if abs(v) > self.INVALID_MEAS_THRESHOLD:
            raise MeasurementError(f'仪器当前无法得到有效测量值: {v}')
        return v

    def _prepare_measurement(self, channel: int, ensure_display: bool = True):
        self._validate_channel(channel)

        if ensure_display and not self.is_channel_displayed(channel):
            self.set_channel_display(channel, True)
            time.sleep(0.2)

        if self.auto_stop_before_measure:
            self.stop()
            time.sleep(0.1)

    def _measure_query(
        self,
        query_cmd: str,
        channel: int,
        pre_cmd: Optional[str] = None,
        ensure_display: bool = True,
        settle_s: float = 0.2,
        retries: int = 2,
    ) -> float:
        self._prepare_measurement(channel, ensure_display=ensure_display)

        last_err = None
        for attempt in range(retries + 1):
            try:
                if pre_cmd:
                    self.write(pre_cmd)
                    time.sleep(settle_s)

                value = self._safe_float(self.query(query_cmd))
                return value

            except (MeasurementError, VisaIOError, ValueError) as e:
                last_err = e
                self._log(f'Measure attempt {attempt + 1} failed: {e}')
                time.sleep(0.2)

        raise MeasurementError(
            f'测量失败，命令={query_cmd}, channel={channel}, 错误={last_err}'
        )

    def get_channel_mean(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:VAVerage? DISPlay,CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:VAVerage DISPlay,CHANnel{channel}',
        )

    def get_channel_pk2pk(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:VPP? CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:VPP CHANnel{channel}',
        )

    def get_channel_frequency(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:FREQuency? CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:FREQuency CHANnel{channel}',
        )

    def get_channel_amplitude(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:VAMPlitude? CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:VAMPlitude CHANnel{channel}',
        )

    def get_channel_rms(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:VRMS? DISPlay,AC,CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:VRMS DISPlay,AC,CHANnel{channel}',
        )

    def get_channel_dc_rms(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:VRMS? DISPlay,DC,CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:VRMS DISPlay,DC,CHANnel{channel}',
        )

    def get_channel_max(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:VMAX? CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:VMAX CHANnel{channel}',
        )

    def get_channel_min(self, channel: int) -> float:
        return self._measure_query(
            query_cmd=f':MEASure:VMIN? CHANnel{channel}',
            channel=channel,
            pre_cmd=f':MEASure:VMIN CHANnel{channel}',
        )

    def get_basic_measurements(self, channel: int) -> Dict[str, Any]:
        result = {}
        for name, func in (
            ('mean', self.get_channel_mean),
            ('pk2pk', self.get_channel_pk2pk),
            ('amplitude', self.get_channel_amplitude),
            ('frequency', self.get_channel_frequency),
            ('rms_ac', self.get_channel_rms),
            ('rms_dc', self.get_channel_dc_rms),
            ('vmax', self.get_channel_max),
            ('vmin', self.get_channel_min),
        ):
            try:
                result[name] = func(channel)
            except Exception as e:
                result[name] = f'ERROR: {e}'
        return result


    def clear_all_measurements(self):
        self._ensure_connected()
        self.write(':MEASure:CLEar')
        time.sleep(0.2)

    def set_AutoRipple_test(self, channel: int):
        self._validate_channel(channel)

        self.clear_all_measurements()
        
        # 1. 基础设置
        self.set_timebase_scale(0.001)
        time.sleep(0.1)
        self.set_timebase_position(0.0)
        time.sleep(0.1)

        # 2. 先用大刻度测平均值
        self.set_channel_scale(channel, 0.5)
        time.sleep(0.1)
        self.set_channel_offset(channel, 0.0)
        time.sleep(0.1)

        mean_vol = self.get_channel_mean(channel)
        print(f'Channel {channel} Mean: {mean_vol:.6f} V')

        # 3. 先切目标 scale
        self.set_channel_scale(channel, 0.02)
        time.sleep(0.1)

        # 4. 再设置 offset 到均值附近
        self.set_channel_offset(channel, mean_vol - 0.02)
        time.sleep(0.1)

        # mean_vol = self.get_channel_mean(channel)
        # vpp = self.get_channel_pk2pk(channel)
        # print(f'Channel {channel} Mean: {mean_vol:.6f} V, VPP: {vpp:.6f} V')


    # =========================
    # 其他
    # =========================

    def ping(self) -> bool:
        try:
            _ = self.identify_instrument()
            return True
        except Exception:
            return False

    def capture_screen_png(self, invert: bool = False) -> bytes:
        self._ensure_connected()
        old_timeout = self.instrument.timeout
        old_term = self.instrument.read_termination
        old_chunk = self.instrument.chunk_size
        self.instrument.timeout = 30000
        self.instrument.read_termination = None
        self.instrument.chunk_size = 1024 * 1024
        try:
            ink_saver = 'ON' if invert else 'OFF'
            self.write(f':HARDcopy:INKSaver {ink_saver}')
            self.write(':DISPlay:DATA? PNG, COLor')
            raw = self.instrument.read_raw()

            n_digits = int(chr(raw[1]))
            data_length = int(raw[2:2 + n_digits])
            data_start = 2 + n_digits
            return raw[data_start:data_start + data_length]
        finally:
            self.instrument.timeout = old_timeout
            self.instrument.read_termination = old_term
            self.instrument.chunk_size = old_chunk


def main():
    import os

    resource_addr = 'USB0::0x0957::0x17A4::MY61500152::INSTR'
    visa_lib = None
    output_dir = os.path.join(os.path.dirname(__file__), 'screenshot_test')
    os.makedirs(output_dir, exist_ok=True)

    print('========== DSOX4034A Screenshot Invert Test ==========')
    try:
        with DSOX4034A(
            resource=resource_addr,
            visa_library=visa_lib,
            timeout_ms=10000,
            open_timeout_ms=5000,
            debug=True
        ) as scope:
            print(f'Connected: {scope.identify_instrument()}')

            print('\n--- Test 1: invert=False (COLor mode) ---')
            png_color = scope.capture_screen_png(invert=False)
            path_color = os.path.join(output_dir, 'test_invert_false_COLor.png')
            with open(path_color, 'wb') as f:
                f.write(png_color)
            print(f'  Saved: {path_color} ({len(png_color)} bytes)')

            print('\n--- Test 2: invert=True (INVert mode) ---')
            png_invert = scope.capture_screen_png(invert=True)
            path_invert = os.path.join(output_dir, 'test_invert_true_INVert.png')
            with open(path_invert, 'wb') as f:
                f.write(png_invert)
            print(f'  Saved: {path_invert} ({len(png_invert)} bytes)')

            print('\n========== Results ==========')
            print(f'  COLor (invert=False): {path_color}')
            print(f'  INVert (invert=True): {path_invert}')
            print('  Please open both files and verify:')
            print('    - invert=False should be the original screen colors (dark background)')
            print('    - invert=True  should be inverted colors (white background)')

    except InstrumentConnectionError as e:
        print(f'Connection failed: {e}')
    except Exception as e:
        print(f'Error: {e}')


if __name__ == '__main__':
    main()