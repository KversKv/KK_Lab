import time
import pyvisa
from log_config import get_logger

logger = get_logger(__name__)


class MSO64B:
    def __init__(self, resource, visa_library=None):
        logger.debug("MSO64B __init__: resource=%s", resource)
        try:
            if visa_library:
                self.rm = pyvisa.ResourceManager(visa_library)
            else:
                self.rm = pyvisa.ResourceManager()
        except (OSError, ValueError) as e:
            logger.warning(
                "MSO64B: 系统 VISA 不可用(%s)，回退到 pyvisa-py('@py')", e
            )
            self.rm = pyvisa.ResourceManager('@py')
        logger.debug("MSO64B visalib=%s", self.rm.visalib)
        if resource.startswith('TCPIP0::') or resource.startswith('USB0::'):
            self.instrument = self.rm.open_resource(resource)
        else:
            self.instrument = self.rm.open_resource(f'TCPIP0::{resource}::inst0::INSTR')

        self.instrument.timeout = 10000
        self.instrument.encoding = 'utf-8'
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'
        logger.debug("MSO64B connected, timeout=%d ms", self.instrument.timeout)

    def identify_instrument(self):
        return self.instrument.query('*IDN?').strip()

    def _safe_float(self, value):
        v = float(value.strip())
        if abs(v) > 1e36:
            raise ValueError(f'仪器当前无法得到有效测量值: {v}')
        return v

    def _measure_immediate(self, channel, measure_type):
        logger.debug("MSO64B _measure_immediate: CH%s type=%s", channel, measure_type)
        self.instrument.write(f'MEASUrement:IMMed:SOURCE1 CH{channel}')
        self.instrument.write(f'MEASUrement:IMMed:TYPE {measure_type}')
        result = self._safe_float(self.instrument.query('MEASUrement:IMMed:VALUE?'))
        logger.debug("MSO64B _measure_immediate result: CH%s %s = %s", channel, measure_type, result)
        return result

    def get_channel_mean(self, channel):
        return self._measure_immediate(channel, 'MEAN')

    def get_channel_pk2pk(self, channel):
        return self._measure_immediate(channel, 'PK2PK')

    def get_channel_frequency(self, channel):
        return self._measure_immediate(channel, 'FREQUENCY')

    def get_channel_max(self, channel):
        return self._measure_immediate(channel, 'MAXIMUM')

    def get_channel_min(self, channel):
        return self._measure_immediate(channel, 'MINIMUM')

    def get_channel_rms(self, channel):
        return self._measure_immediate(channel, 'RMS')

    def set_trigger_edge(self, source_channel, level, slope='POS'):
        logger.debug("MSO64B set_trigger_edge: CH%s, level=%s, slope=%s", source_channel, level, slope)
        slope_map = {'POS': 'RISe', 'NEG': 'FALL', 'EITH': 'EITher'}
        tek_slope = slope_map.get(slope.upper(), 'RISe')
        self.instrument.write(f'TRIGger:A:TYPe EDGE')
        self.instrument.write(f'TRIGger:A:EDGE:SOUrce CH{source_channel}')
        self.instrument.write(f'TRIGger:A:EDGE:SLOpe {tek_slope}')
        self.instrument.write(f'TRIGger:A:LEVel:CH{source_channel} {level}')

    def set_dvm_trigger_frequency_counter_enabled(self, enable=True):
        """
        设置 DVM trigger frequency counter 显示开关
        """
        value = 'ON' if enable else 'OFF'
        self.instrument.write(f'DVM:TRIGger:FREQuency:COUNTer {value}')

    def get_dvm_trigger_frequency_counter_enabled(self):
        """
        获取 DVM trigger frequency counter 是否开启
        返回 True / False
        """
        result = self.instrument.query('DVM:TRIGger:FREQuency:COUNTer?').strip().upper()
        return result in ('1', 'ON')

    def get_dvm_frequency(self, enable_counter=True, wait_time=0.3):
        """
        获取 DVM 测得的频率值

        参数:
            enable_counter: 是否在读取前自动开启 trigger frequency counter
            wait_time: 开启后等待仪器更新的时间
        """
        if enable_counter:
            self.set_dvm_trigger_frequency_counter_enabled(True)
            time.sleep(wait_time)

        return self._safe_float(self.instrument.query('DVM:MEASUrement:FREQuency?'))

    def get_dvm_dc(self, channel, wait_time=0.3):
        self.instrument.write('DVM:STATE ON')
        self.instrument.write(f'DVM:SOURCE CH{channel}')
        self.instrument.write('DVM:MODE DC')
        time.sleep(wait_time)
        return self._safe_float(self.instrument.query('DVM:MEASUREMENT:VALUE?'))

    def get_dvm_ac_rms(self, channel, wait_time=0.3):
        self.instrument.write('DVM:STATE ON')
        self.instrument.write(f'DVM:SOURCE CH{channel}')
        self.instrument.write('DVM:MODE ACRMS')
        time.sleep(wait_time)
        return self._safe_float(self.instrument.query('DVM:MEASUREMENT:VALUE?'))

    def get_dvm_dc_ac_rms(self, channel, wait_time=0.3):
        self.instrument.write('DVM:STATE ON')
        self.instrument.write(f'DVM:SOURCE CH{channel}')
        self.instrument.write('DVM:MODE DCRMS')
        time.sleep(wait_time)
        return self._safe_float(self.instrument.query('DVM:MEASUREMENT:VALUE?'))

    def configure_horizontal(self, duration_s, sample_rate_mhz):
        logger.debug("MSO64B configure_horizontal: duration=%ss, sample_rate=%s MHz", duration_s, sample_rate_mhz)
        num_divs = 10
        scale = duration_s / num_divs
        record_length = int(duration_s * sample_rate_mhz * 1e6)
        record_length = max(1000, min(record_length, 62_500_000))
        self.instrument.write('HORizontal:MODE MANUAL')
        self.instrument.write(f'HORizontal:MODE:SAMPLERate {sample_rate_mhz * 1e6:.0f}')
        self.instrument.write(f'HORizontal:MODE:RECOrdlength {record_length}')
        self.instrument.write(f'HORizontal:SCAle {scale}')
        self.instrument.write(f'HORizontal:POSition 50')
        time.sleep(0.5)

    def setup_edge_search(self, channel, slope='BOTH', threshold=None):
        self.instrument.write('SEARCH:SEARCH1:STATE OFF')
        time.sleep(0.2)
        self.instrument.write('SEARCH:SEARCH1:TRIGger:A:TYPe EDGE')
        self.instrument.write(f'SEARCH:SEARCH1:TRIGger:A:EDGE:SOUrce CH{channel}')
        self.instrument.write(f'SEARCH:SEARCH1:TRIGger:A:EDGE:SLOpe {slope}')
        if threshold is not None:
            self.instrument.write(f'SEARCH:SEARCH1:TRIGger:A:EDGE:THReshold {threshold}')
        self.instrument.write('SEARCH:SEARCH1:STATE ON')
        time.sleep(0.5)

    def single_acquisition(self, timeout_s=60):
        logger.debug("MSO64B single_acquisition: timeout=%ss", timeout_s)
        self.instrument.write('ACQuire:STOPAfter SEQuence')
        self.instrument.write('ACQuire:STATE RUN')
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            state = self.instrument.query('ACQuire:STATE?').strip()
            if state == '0':
                return True
            time.sleep(0.5)
        raise TimeoutError(f'采集超时 ({timeout_s}s)')

    def export_search_table_csv(self, remote_path='C:/Temp/search_export.csv'):
        self.instrument.write(f'SAVe:EVENTtable:SEARCHTable "{remote_path}"')
        time.sleep(2.0)

    def read_remote_file(self, remote_path):
        old_timeout = self.instrument.timeout
        self.instrument.timeout = 30000
        try:
            self.instrument.write(f'FILESystem:READFile "{remote_path}"')
            raw = self.instrument.read_raw()
            return raw.decode('utf-8', errors='replace')
        finally:
            self.instrument.timeout = old_timeout

    def delete_remote_file(self, remote_path):
        try:
            self.instrument.write(f'FILESystem:DELEte "{remote_path}"')
        except Exception:
            pass

    def get_search_total(self):
        result = self.instrument.query('SEARCH:SEARCH1:TOTAL?').strip()
        return int(result)

    def set_channel_display(self, channel, on=True):
        value = 'ON' if on else 'OFF'
        self.instrument.write(f'DISPlay:GLObal:CH{channel}:STATE {value}')

    def is_channel_displayed(self, channel):
        result = self.instrument.query(f'DISPlay:GLObal:CH{channel}:STATE?').strip().upper()
        return result in ('1', 'ON')

    def set_channel_coupling(self, channel, coupling='DC'):
        coupling = coupling.upper()
        if coupling not in ('AC', 'DC'):
            raise ValueError(f'coupling must be AC / DC, got: {coupling}')
        self.instrument.write(f'CH{channel}:COUPling {coupling}')

    def get_channel_coupling(self, channel):
        return self.instrument.query(f'CH{channel}:COUPling?').strip()

    def set_channel_bandwidth(self, channel, bandwidth='FULl'):
        self.instrument.write(f'CH{channel}:BANdwidth {bandwidth}')

    def set_channel_scale(self, channel, volts_per_div):
        self.instrument.write(f'CH{channel}:SCAle {volts_per_div}')

    def get_channel_scale(self, channel):
        return self._safe_float(self.instrument.query(f'CH{channel}:SCAle?'))

    def set_channel_offset(self, channel, offset):
        self.instrument.write(f'CH{channel}:OFFSet {offset}')

    def get_channel_offset(self, channel):
        return self._safe_float(self.instrument.query(f'CH{channel}:OFFSet?'))

    def set_timebase_scale(self, seconds_per_div):
        self.instrument.write(f'HORizontal:SCAle {seconds_per_div}')

    def set_timebase_position(self, position_pct):
        self.instrument.write(f'HORizontal:POSition {position_pct}')

    def clear_all_measurements(self):
        self.instrument.write('MEASUrement:DELete:ALL')
        time.sleep(0.2)

    def stop(self):
        self.instrument.write('ACQuire:STATE STOP')

    def run(self):
        self.instrument.write('ACQuire:STATE RUN')

    def set_AutoRipple_test(self, channel):
        self.clear_all_measurements()

        self.set_timebase_scale(0.001)
        time.sleep(0.1)
        self.set_timebase_position(50)
        time.sleep(0.1)

        self.set_channel_scale(channel, 0.5)
        time.sleep(0.1)
        self.set_channel_offset(channel, 0.0)
        time.sleep(0.1)

        mean_vol = self.get_channel_mean(channel)

        self.set_channel_scale(channel, 0.02)
        time.sleep(0.1)

        self.set_channel_offset(channel, mean_vol - 0.02)
        time.sleep(0.1)

    def disconnect(self):
        logger.debug("MSO64B disconnect called")
        if self.instrument is not None:
            try:
                self.instrument.close()
            except Exception:
                pass
            self.instrument = None
        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass
            self.rm = None

    def capture_screen_png(self, **kwargs) -> bytes:
        logger.debug("MSO64B capture_screen_png called")
        remote_path = 'C:/Temp/tek_screenshot.png'
        old_timeout = self.instrument.timeout
        self.instrument.timeout = 30000
        try:
            self.instrument.write('SAVe:IMAGe:FILEFormat PNG')
            self.instrument.write(f'SAVe:IMAGe "{remote_path}"')
            time.sleep(2.0)

            self.instrument.write(f'FILESystem:READFile "{remote_path}"')
            raw = self.instrument.read_raw()

            if len(raw) > 2 and raw[0:1] == b'#':
                n_digits = int(chr(raw[1]))
                data_length = int(raw[2:2 + n_digits])
                data_start = 2 + n_digits
                png_data = raw[data_start:data_start + data_length]
            else:
                png_data = raw

            try:
                self.instrument.write(f'FILESystem:DELEte "{remote_path}"')
            except Exception:
                pass

            return png_data
        finally:
            self.instrument.timeout = old_timeout


if __name__ == '__main__':
    ip_address = '192.168.3.27'
    mso64b = MSO64B(ip_address)

    try:
        logger.info(mso64b.identify_instrument())
        logger.info('CH2 Mean: %.6f', mso64b.get_channel_mean(2))
        logger.info('CH2 Peak-to-Peak: %.6f', mso64b.get_channel_pk2pk(2))
        logger.info('CH2 Frequency: %.6f', mso64b.get_channel_frequency(2))

        logger.info('DVM Trigger Counter Enabled (before): %s', mso64b.get_dvm_trigger_frequency_counter_enabled())
        mso64b.set_dvm_trigger_frequency_counter_enabled(True)
        logger.info('DVM Trigger Counter Enabled (after): %s', mso64b.get_dvm_trigger_frequency_counter_enabled())
        logger.info('DVM Frequency: %.9f', mso64b.get_dvm_frequency())

    finally:
        mso64b.disconnect()