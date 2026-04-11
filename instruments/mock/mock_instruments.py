import math
import random


class MockInstr:
    def write(self, cmd):
        pass

    def query(self, cmd):
        return ""


class MockN6705C:

    def __init__(self):
        self._rng = random.Random(0)
        self._vin = 3.8
        self._vout = 1.8
        self._iload = 0.0
        self._vin_ch = 1
        self._iload_ch = 3
        self._voltage = 0.0
        self._mock_i2c = None
        self._last_expected_v = 1.0
        self.instr = MockInstr()

    def set_channel_range(self, channel):
        pass

    def channel_on(self, channel):
        pass

    def channel_off(self, channel):
        pass

    def set_current(self, channel, current):
        self._iload = abs(current)
        self._iload_ch = channel

    def set_current_limit(self, channel, current_limit):
        pass

    def set_mode(self, channel, mode):
        pass

    def set_voltage(self, channel, voltage):
        self._voltage = voltage
        if self._mock_i2c is not None:
            self._mock_i2c.set_mock_voltage(voltage)

    def _sim_eff(self):
        eff = 0.75 + 0.15 * (1 - math.exp(-self._iload / 0.3)) + self._rng.gauss(0, 0.005)
        return max(0.6, min(0.95, eff))

    def measure_voltage(self, channel):
        noise = self._rng.gauss(0, 0.002)
        if channel == self._vin_ch:
            return self._vin + noise
        return self._last_expected_v + noise

    def measure_current(self, channel):
        if channel == self._iload_ch:
            val = -(self._iload + self._rng.gauss(0, 0.0002))
        else:
            if self._iload <= 0:
                val = 0.00001
            else:
                val = (self._vout * self._iload) / (self._vin * self._sim_eff())
        return f"{val:.6f}"

    def disconnect(self):
        pass

    def read_mmem_data(self, filepath):
        return b""


class MockI2C:

    def __init__(self):
        self._voltage = 0.9
        self._rng = random.Random(42)
        self._regs = {}

    def set_mock_voltage(self, voltage):
        self._voltage = voltage

    def initialize(self):
        return True

    def read(self, device_addr, reg_addr, iic_weight):
        if (device_addr, reg_addr) in self._regs:
            return self._regs[(device_addr, reg_addr)]
        ideal = self._voltage * 3276.8
        noise = self._rng.gauss(0, 2.0)
        return max(0, int(ideal + noise))

    def write(self, device_addr, reg_addr, write_data, width_flag):
        self._regs[(device_addr, reg_addr)] = write_data


class MockVT6002:

    def __init__(self):
        self._target_temp = 25.0

    def set_temperature(self, temp):
        self._target_temp = temp

    def get_current_temp(self):
        return self._target_temp

    def close(self):
        pass


class MockMSO64B:

    def __init__(self):
        self.instrument = MockInstr()

    def identify_instrument(self):
        return "TEKTRONIX,MSO64B,MOCK000,FW1.0"

    def disconnect(self):
        pass

    def get_dvm_frequency(self, enable_counter=True, wait_time=0.3):
        return 32768.0 + random.gauss(0, 0.01)

    def configure_horizontal(self, duration, sample_rate_mhz):
        pass

    def setup_edge_search(self, channel, slope='BOTH'):
        pass

    def single_acquisition(self, timeout_s=30):
        pass

    def get_search_total(self):
        return 100

    def export_search_table_csv(self, path):
        pass

    def read_remote_file(self, path):
        return ""

    def delete_remote_file(self, path):
        pass
