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
        self._channel_states = {1: False, 2: False, 3: False, 4: False}
        self._channel_modes = {1: "PS2Q", 2: "PS2Q", 3: "PS2Q", 4: "PS2Q"}
        self._channel_voltages = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self._channel_currents = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
        self._channel_current_limits = {1: 1.0, 2: 1.0, 3: 1.0, 4: 1.0}
        self._channel_voltage_limits = {1: 20.0, 2: 20.0, 3: 20.0, 4: 20.0}
        self.instr = MockInstr()

    def set_channel_range(self, channel):
        pass

    def set_channel_range_off(self, channel):
        pass

    def channel_on(self, channel):
        self._channel_states[channel] = True

    def channel_off(self, channel):
        self._channel_states[channel] = False

    def get_channel_state(self, channel):
        return self._channel_states.get(channel, False)

    def set_current(self, channel, current):
        self._iload = abs(current)
        self._iload_ch = channel
        self._channel_currents[channel] = current

    def set_current_limit(self, channel, current_limit):
        self._channel_current_limits[channel] = current_limit

    def get_current_limit(self, channel):
        return str(self._channel_current_limits.get(channel, 1.0))

    def set_voltage_limit(self, channel, voltage_limit):
        self._channel_voltage_limits[channel] = voltage_limit

    def set_mode(self, channel, mode):
        self._channel_modes[channel] = mode

    def get_mode(self, channel):
        return self._channel_modes.get(channel, "PS2Q")

    def set_voltage(self, channel, voltage):
        self._voltage = voltage
        self._channel_voltages[channel] = voltage
        if self._mock_i2c is not None:
            self._mock_i2c.set_mock_voltage(voltage)

    def set_voltagemode(self, channel):
        self._channel_modes[channel] = "VMETer"

    def set_measurement_range(self, channel, measurement_type, range_value):
        pass

    def _sim_eff(self):
        eff = 0.75 + 0.15 * (1 - math.exp(-self._iload / 0.3)) + self._rng.gauss(0, 0.005)
        return max(0.6, min(0.95, eff))

    def measure_voltage(self, channel):
        noise = self._rng.gauss(0, 0.002)
        if channel == self._vin_ch:
            return self._vin + noise
        return self._last_expected_v + noise

    def fetch_voltage(self, channel):
        return str(self.measure_voltage(channel))

    def measure_voltage_fast(self, channel):
        return self.measure_voltage(channel)

    def measure_current(self, channel):
        if channel == self._iload_ch:
            val = -(self._iload + self._rng.gauss(0, 0.0002))
        else:
            if self._iload <= 0:
                val = 0.00001
            else:
                val = (self._vout * self._iload) / (self._vin * self._sim_eff())
        return f"{val:.6f}"

    def fetch_current(self, channel):
        return float(self.measure_current(channel))

    def disconnect(self):
        pass

    def read_mmem_data(self, filepath):
        return b""

    def format_current(self, current_A):
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.3f} A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.3f} mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.3f} µA"
        else:
            return f"{current_A:.3e} A"

    def arb_on(self, channel):
        pass

    def arb_off(self, channel):
        pass

    def arb_run(self):
        pass

    def arb_stop(self):
        pass

    def arb_status(self, channel):
        return "0"

    def set_arb_type(self, channel, arb_type="VOLT"):
        pass

    def set_arb_step(self, channel, v0, v1, t0, t1):
        pass

    def set_arb_staircase(self, channel, v0, v1, t0, t1, t2, steps):
        pass

    def set_arb_pulse(self, channel, v0, v1, t0, t1, t2, frequency):
        pass

    def set_arb_continuous(self, channel, flag=False):
        pass

    def clear_arb_all_channels(self, total_channels=4):
        pass

    def restore_arb_trigger_source(self):
        pass

    def trg(self):
        pass

    def dlog_config(self, ch):
        pass

    def BUS_TRG(self):
        pass

    def export_file(self):
        pass

    def get_average_current(self, channels, duration):
        if isinstance(channels, int):
            channels = [channels]
        return {ch: 0.001 for ch in channels}

    def get_current_by_datalog(self, channels, test_time, sample_period,
                               marker1_percent=10, marker2_percent=90):
        if isinstance(channels, int):
            channels = [channels]
        return {ch: 0.001 for ch in channels}

    def fetch_current_by_datalog(self, channels, test_time, sample_period,
                                 marker1_percent=10, marker2_percent=90):
        if isinstance(channels, int):
            channels = [channels]
        return {ch: 0.001 for ch in channels}

    def fetch_by_datalog(self, curr_channels, volt_channels, test_time, sample_period):
        if curr_channels is None:
            curr_channels = []
        if volt_channels is None:
            volt_channels = []
        if isinstance(curr_channels, int):
            curr_channels = [curr_channels]
        if isinstance(volt_channels, int):
            volt_channels = [volt_channels]
        curr_result = {ch: float(self.measure_current(ch)) for ch in curr_channels}
        volt_result = {ch: float(self.measure_voltage(ch)) for ch in volt_channels}
        return curr_result, volt_result


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


class _MockSerial:
    def __init__(self):
        self.is_open = True

    def close(self):
        self.is_open = False


class MockVT6002:

    def __init__(self):
        self._target_temp = 25.0
        self._is_running = False
        self.ser = _MockSerial()

    def set_temperature(self, temp):
        self._target_temp = temp

    def get_current_temp(self):
        return self._target_temp

    def get_set_temp(self):
        return self._target_temp

    def read_humidity_pv(self):
        return 50.0

    def read_temperature_sv(self):
        return self._target_temp

    def read_humidity_sv(self):
        return 50.0

    def read_temperature_output(self):
        return 0

    def read_humidity_output(self):
        return 0

    def start(self):
        self._is_running = True

    def stop(self):
        self._is_running = False

    def close(self):
        self.ser.is_open = False


class MockMSO64B:

    def __init__(self):
        self.instrument = MockInstr()
        self._channel_display = {1: True, 2: True, 3: True, 4: True}

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

    def set_channel_display(self, channel, on=True):
        self._channel_display[channel] = on

    def is_channel_displayed(self, channel):
        return self._channel_display.get(channel, True)

    def set_channel_scale(self, channel, volts_per_div):
        pass

    def set_channel_offset(self, channel, offset):
        pass

    def get_channel_scale(self, channel):
        return 1.0

    def get_channel_offset(self, channel):
        return 0.0

    def set_timebase_scale(self, seconds_per_div):
        pass

    def set_trigger_edge(self, source_channel, level, slope='POS'):
        pass

    def capture_screen_png(self, **kwargs):
        return None

    def get_channel_mean(self, channel):
        return 1.0 + random.gauss(0, 0.01)

    def get_channel_pk2pk(self, channel):
        return 0.1 + random.gauss(0, 0.005)

    def get_channel_frequency(self, channel):
        return 1000.0 + random.gauss(0, 1.0)

    def get_channel_max(self, channel):
        return 1.05 + random.gauss(0, 0.01)

    def get_channel_min(self, channel):
        return 0.95 + random.gauss(0, 0.01)

    def get_channel_rms(self, channel):
        return 0.05 + random.gauss(0, 0.005)

    def set_channel_bandwidth(self, channel, bandwidth='FULl'):
        pass

    def set_timebase_position(self, position_pct):
        pass

    def set_AutoRipple_test(self, channel):
        pass
