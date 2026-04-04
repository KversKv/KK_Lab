import time
import pyvisa


class MSO64B:
    def __init__(self, resource):
        self.rm = pyvisa.ResourceManager('@py')
        if resource.startswith('TCPIP0::') or resource.startswith('USB0::'):
            self.instrument = self.rm.open_resource(resource)
        else:
            self.instrument = self.rm.open_resource(f'TCPIP0::{resource}::inst0::INSTR')

        self.instrument.timeout = 10000
        self.instrument.encoding = 'utf-8'
        self.instrument.read_termination = '\n'
        self.instrument.write_termination = '\n'

    def identify_instrument(self):
        return self.instrument.query('*IDN?').strip()

    def _safe_float(self, value):
        v = float(value.strip())
        if abs(v) > 1e36:
            raise ValueError(f'仪器当前无法得到有效测量值: {v}')
        return v

    def _measure_immediate(self, channel, measure_type):
        self.instrument.write(f'MEASUrement:IMMed:SOURCE1 CH{channel}')
        self.instrument.write(f'MEASUrement:IMMed:TYPE {measure_type}')
        return self._safe_float(self.instrument.query('MEASUrement:IMMed:VALUE?'))

    def get_channel_mean(self, channel):
        return self._measure_immediate(channel, 'MEAN')

    def get_channel_pk2pk(self, channel):
        return self._measure_immediate(channel, 'PK2PK')

    def get_channel_frequency(self, channel):
        return self._measure_immediate(channel, 'FREQUENCY')

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

    def disconnect(self):
        if self.instrument is not None:
            self.instrument.close()
            self.instrument = None


if __name__ == '__main__':
    ip_address = '192.168.3.27'
    mso64b = MSO64B(ip_address)

    try:
        print(mso64b.identify_instrument())
        print(f'CH2 Mean: {mso64b.get_channel_mean(2):.6f}')
        print(f'CH2 Peak-to-Peak: {mso64b.get_channel_pk2pk(2):.6f}')
        print(f'CH2 Frequency: {mso64b.get_channel_frequency(2):.6f}')

        print(f'DVM Trigger Counter Enabled (before): {mso64b.get_dvm_trigger_frequency_counter_enabled()}')
        mso64b.set_dvm_trigger_frequency_counter_enabled(True)
        print(f'DVM Trigger Counter Enabled (after): {mso64b.get_dvm_trigger_frequency_counter_enabled()}')
        print(f'DVM Frequency: {mso64b.get_dvm_frequency():.9f}')

    finally:
        mso64b.disconnect()