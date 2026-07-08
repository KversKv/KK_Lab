import math
import random
import time
from contextlib import contextmanager


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

    def set_output_off_mode(self, channel, mode="HIGHZ"):
        mode_str = str(mode).strip().upper()
        if mode_str not in ("HIGHZ", "LOWZ"):
            raise ValueError(
                f"Invalid output off mode '{mode}', expected 'HIGHZ' or 'LOWZ'"
            )
        if not hasattr(self, "_channel_off_modes"):
            self._channel_off_modes = {}
        self._channel_off_modes[channel] = mode_str

    def get_output_off_mode(self, channel):
        if not hasattr(self, "_channel_off_modes"):
            self._channel_off_modes = {}
        return self._channel_off_modes.get(channel, "LOWZ")

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

    def get_voltage_limit(self, channel):
        return str(self._channel_voltage_limits.get(channel, 20.0))

    def set_voltage_limit(self, channel, voltage_limit):
        self._channel_voltage_limits[channel] = voltage_limit

    def set_mode(self, channel, mode):
        self._channel_modes[channel] = mode

    def get_mode(self, channel):
        return self._channel_modes.get(channel, "PS2Q")

    def set_voltage(self, channel, voltage):
        self._voltage = voltage
        self._channel_voltages[channel] = voltage
        self._last_expected_v = voltage
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
        return self._channel_voltages.get(channel, self._last_expected_v) + noise

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
        return val

    def fetch_current(self, channel):
        return self.measure_current(channel)

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
                                 marker1_percent=10, marker2_percent=90,
                                 on_progress=None, stop_check=None):
        if isinstance(channels, int):
            channels = [channels]
        if on_progress:
            on_progress(1.0)
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

    def prepare_force_high(self, channels, voltage_offset, current_limit,
                           monitor_channels=None):
        if isinstance(channels, int):
            channels = [channels]
        return {ch: float(self.measure_voltage(ch)) for ch in channels}

    def prepare_force_auto(self, channels, current_limit,
                           monitor_channels=None):
        if isinstance(channels, int):
            channels = [channels]
        return {ch: float(self.measure_voltage(ch)) for ch in channels}

    def configure_datalog(self, channels, test_time, sample_period):
        pass

    def start_datalog(self, dlog_file="internal:\\temp_fetch.dlog"):
        pass

    def fetch_datalog_marker_results(self, channels, test_time):
        if isinstance(channels, int):
            channels = [channels]
        return {ch: abs(float(self.measure_current(ch))) for ch in channels}

    def restore_channels_to_vmeter(self, channels):
        pass

    def force_high_and_measure(self, channels, voltage_offset, current_limit, test_time, sample_period,
                               on_progress=None, stop_check=None, monitor_channels=None):
        if isinstance(channels, int):
            channels = [channels]
        if monitor_channels is None:
            monitor_channels = []
        elif isinstance(monitor_channels, int):
            monitor_channels = [monitor_channels]
        all_ch = list(channels) + [ch for ch in monitor_channels if ch not in channels]
        if on_progress:
            on_progress(1.0)
        curr_result = {ch: abs(float(self.measure_current(ch))) for ch in all_ch}
        volt_result = {ch: float(self.measure_voltage(ch)) for ch in channels}
        return curr_result, volt_result


class MockPicoGPIO:
    def __init__(self, port="MOCK", baudrate=921600):
        self.port = port
        self.baudrate = baudrate
        self._connected = False
        self._pin_values = {}
        self._pin_modes = {}

    def connect(self):
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def close(self):
        self.disconnect()

    def is_connected(self):
        return self._connected

    def identify(self):
        return f"Mock YD RP2040 GPIO ({self.port})"

    def out(self, pin, value):
        pin = int(pin)
        self._pin_modes[pin] = "out"
        self._pin_values[pin] = int(value)

    def high(self, pin):
        self.out(pin, 1)

    def low(self, pin):
        self.out(pin, 0)

    def toggle(self, pin):
        pin = int(pin)
        self.out(pin, 0 if self._pin_values.get(pin, 0) else 1)

    def pulse(self, pin, width_ms=10, active=1, release_high_z=True):
        active = int(active)
        self.out(pin, active)
        time.sleep(max(0, int(width_ms)) / 1000.0)
        self.out(pin, 0 if active else 1)
        if release_high_z:
            self.in_pull(pin, "none")

    def hiz(self, pin):
        self.in_pull(pin, "none")

    def in_pull(self, pin, pull="none"):
        self._pin_modes[int(pin)] = f"in_{pull}"

    def read(self, pin):
        return self._pin_values.get(int(pin), 0)

    def read_pull(self, pin, pull="none"):
        self.in_pull(pin, pull)
        return self.read(pin)

    def read_adc(self, pin):
        return 32768

    def read_voltage(self, pin):
        return self.read_adc(pin) * 3.3 / 65535

    def read_temperature(self):
        return 25.0

    def pwm(self, pin, freq=1000, duty_u16=32768):
        self._pin_modes[int(pin)] = f"pwm_{freq}_{duty_u16}"

    def pwm_off(self, pin):
        self._pin_modes.pop(int(pin), None)

    def soft_reset(self):
        self._pin_values.clear()
        self._pin_modes.clear()


class MockCH9114F:
    DIR_INPUT = 0
    DIR_OUTPUT = 1

    def __init__(self, port="MOCK"):
        self.port = port
        self._connected = False
        self._gpio_count = 16
        self._pin_values = {}
        self._pin_dirs = {}
        self._pin_func = {}

    def connect(self):
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    def close(self):
        self.disconnect()

    def is_connected(self):
        return self._connected

    def identify(self):
        return f"Mock CH9114F GPIO ({self.port}, pins={self._gpio_count})"

    @property
    def gpio_count(self):
        return self._gpio_count

    def config(self, pin, direction=DIR_OUTPUT, gpio_func=True):
        pin = int(pin)
        self._pin_dirs[pin] = direction
        self._pin_func[pin] = bool(gpio_func)

    def set_output(self, pin):
        self.config(pin, direction=self.DIR_OUTPUT, gpio_func=True)

    def set_input(self, pin, gpio_func=True):
        self.config(pin, direction=self.DIR_INPUT, gpio_func=gpio_func)

    def out(self, pin, value):
        pin = int(pin)
        self.set_output(pin)
        self._pin_values[pin] = 1 if int(value) else 0

    def in_pull(self, pin, pull="none"):
        pin = int(pin)
        self.set_input(pin, gpio_func=True)

    def high(self, pin):
        self.out(pin, 1)

    def low(self, pin):
        self.out(pin, 0)

    def toggle(self, pin):
        self.out(pin, 0 if self._pin_values.get(int(pin), 0) else 1)

    def read(self, pin):
        return self._pin_values.get(int(pin), 0)

    def read_all(self):
        value = 0
        for pin, level in self._pin_values.items():
            if level:
                value |= (1 << pin)
        return value

    def get_config(self, pin):
        pin = int(pin)
        return {
            "gpio_func": self._pin_func.get(pin, True),
            "direction": self._pin_dirs.get(pin, self.DIR_INPUT),
            "level": self._pin_values.get(pin, 0),
        }

    def config_mask(self, enable_mask, func_mask, dir_out_mask):
        for pin in range(self._gpio_count):
            if enable_mask & (1 << pin):
                self._pin_func[pin] = bool(func_mask & (1 << pin))
                self._pin_dirs[pin] = self.DIR_OUTPUT if dir_out_mask & (1 << pin) else self.DIR_INPUT

    def set_mask(self, enable_mask, data_out_mask):
        for pin in range(self._gpio_count):
            if enable_mask & (1 << pin):
                self._pin_values[pin] = 1 if data_out_mask & (1 << pin) else 0

    def __enter__(self):
        if not self._connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.disconnect()
        return False

    @contextmanager
    def _session(self):
        opened_here = False
        if not self._connected:
            self.connect()
            opened_here = True
        try:
            yield self
        finally:
            if opened_here:
                self.disconnect()

    def set_gpio(self, pin, level):
        with self._session():
            self.set_output(pin)
            self.out(pin, 1 if int(level) else 0)
        return int(bool(level))

    def get_gpio(self, pin):
        with self._session():
            return self.read(pin)

    def read_input(self, pin):
        with self._session():
            self.set_input(pin)
            return self.read(pin)

    def toggle_gpio(self, pin):
        with self._session():
            self.set_output(pin)
            new_level = 0 if self.read(pin) else 1
            self.out(pin, new_level)
        return new_level


def _mock_make_set(pin):
    def _setter(self, level=1):
        return self.set_gpio(pin, level)
    _setter.__name__ = f"setGPIO{pin}"
    return _setter


def _mock_make_get(pin):
    def _getter(self):
        return self.get_gpio(pin)
    _getter.__name__ = f"getGPIO{pin}"
    return _getter


def _mock_make_toggle(pin):
    def _toggler(self):
        return self.toggle_gpio(pin)
    _toggler.__name__ = f"toggleGPIO{pin}"
    return _toggler


for _mock_pin in range(16):
    setattr(MockCH9114F, f"setGPIO{_mock_pin}", _mock_make_set(_mock_pin))
    setattr(MockCH9114F, f"getGPIO{_mock_pin}", _mock_make_get(_mock_pin))
    setattr(MockCH9114F, f"toggleGPIO{_mock_pin}", _mock_make_toggle(_mock_pin))
del _mock_pin


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


class _MockSerialBuffer:
    def __init__(self):
        self.is_open = True
        self._rx = bytearray()
        self._tx = []

    @property
    def in_waiting(self):
        return len(self._rx)

    def queue_response(self, payload):
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self._rx.extend(payload)

    def write(self, payload):
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self._tx.append(bytes(payload))
        stripped = bytes(payload).strip()
        if stripped.upper().startswith(b"AT"):
            self.queue_response(b"OK\r\n")
        else:
            self.queue_response(bytes(payload))
        return len(payload)

    def read(self, size=1):
        size = max(0, int(size))
        data = bytes(self._rx[:size])
        del self._rx[:size]
        return data

    def close(self):
        self.is_open = False


class MockUART:
    def __init__(self):
        self.serial_conn = _MockSerialBuffer()

    def is_connected(self):
        return self.serial_conn.is_open

    def get_serial_connection(self):
        return self.serial_conn

    def serial_send(self, payload):
        self.serial_conn.write(payload)
        return True

    def write(self, payload):
        return self.serial_conn.write(payload)

    def close(self):
        self.serial_conn.close()


class MockChamber:

    def __init__(self, model="MOCK Chamber"):
        self.model = model
        self._target_temp = 25.0
        self._is_running = False
        self.ser = _MockSerial()

    def connect(self):
        self.ser.is_open = True
        return True

    def disconnect(self):
        self.close()

    def is_connected(self):
        return self.ser.is_open

    def identify(self):
        return self.model

    def set_temperature(self, temp):
        self._target_temp = float(temp)

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
        self._last_known_running_state = True
        self._last_known_running_state_verified = True

    def stop(self):
        self._is_running = False
        self._last_known_running_state = False
        self._last_known_running_state_verified = True

    def is_running(self):
        self._last_known_running_state = self._is_running
        self._last_known_running_state_verified = True
        return self._is_running

    isRunning = is_running

    def close(self):
        self.ser.is_open = False


class MockVT6002(MockChamber):
    def __init__(self):
        super().__init__("Mock VT6002 Temperature Chamber")


class MockMT3065(MockChamber):
    def __init__(self):
        super().__init__("Mock MT3065 Temperature Chamber")


class MockWT2040(MockChamber):
    def __init__(self):
        super().__init__("Mock WT2040 Temperature Chamber")


class MockMSO64B:

    def __init__(self):
        self.instrument = MockInstr()
        self._channel_display = {1: True, 2: True, 3: True, 4: True}
        self._acquiring = True
        self._timebase_scale = 1e-6
        self._timebase_position = 0.0
        self._channel_bandwidth = {1: 'FUL', 2: 'FUL', 3: 'FUL', 4: 'FUL'}
        self._trigger_source = 'CH1'
        self._trigger_slope = 'POS'
        self._trigger_level = 1.25

    def identify_instrument(self):
        return "TEKTRONIX,MSO64B,MOCK000,FW1.0"

    def run(self):
        self._acquiring = True

    def stop(self):
        self._acquiring = False

    def single(self):
        self._acquiring = False

    def is_acquiring(self):
        return self._acquiring

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
        self._timebase_scale = seconds_per_div

    def get_timebase_scale(self):
        return self._timebase_scale

    def set_trigger_mode(self, mode='EDGE'):
        pass

    def set_trigger_source(self, source_channel):
        self._trigger_source = f'CH{source_channel}'

    def get_trigger_source(self):
        return self._trigger_source

    def set_trigger_slope(self, slope='POS'):
        self._trigger_slope = slope.upper()

    def get_trigger_slope(self):
        return self._trigger_slope

    def set_trigger_level(self, source_channel, level):
        self._trigger_level = level

    def get_trigger_level(self):
        return self._trigger_level

    def set_trigger_config(self, source_channel, level, slope='POS'):
        self.set_trigger_source(source_channel)
        self.set_trigger_slope(slope)
        self.set_trigger_level(source_channel, level)

    def set_trigger_sweep(self, mode='AUTO'):
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
        self._channel_bandwidth[channel] = bandwidth

    def get_channel_bandwidth(self, channel):
        return self._channel_bandwidth.get(channel, 'FUL')

    def set_timebase_position(self, position_pct):
        self._timebase_position = position_pct

    def get_timebase_position(self):
        return self._timebase_position

    def set_AutoRipple_test(self, channel):
        pass


class MockKeysight53230A:

    VALID_CHANNELS = (1, 2)

    def __init__(self):
        self._rng = random.Random(0)
        self._base_freq = 32768.0
        self._gate_time = 0.1
        self._sample_count = 1
        self._trigger_count = 1
        self._function = '"FREQ (@1)"'
        self._coupling = {1: "DC", 2: "DC"}
        self._impedance = {1: 1e6, 2: 1e6}
        self._attenuation = {1: 1, 2: 1}
        self._lowpass = {1: False, 2: False}
        self._slope = {1: "POS", 2: "POS"}
        self._level = {1: 0.0, 2: 0.0}
        self._level_auto = {1: True, 2: True}
        self._range = {1: 5.0, 2: 5.0}
        self._trigger_source = "IMM"
        self._reference = "INT"
        self._stat_enabled = False
        self._last_values = []
        self.instr = MockInstr()

    def _sim_one(self):
        return self._base_freq + self._rng.gauss(0, 0.01)

    def _sim_batch(self, n):
        return [self._sim_one() for _ in range(max(1, int(n)))]

    def identify(self):
        return "Keysight Technologies,53230A,MOCK000,FW1.0"

    def reset(self):
        pass

    def clear_status(self):
        pass

    def self_test(self):
        return "+0"

    def query_opc(self, timeout_s=5.0):
        return True

    def get_errors(self, max_count=20):
        return ['+0,"No error"']

    def set_input_coupling(self, channel, coupling="DC"):
        self._coupling[int(channel)] = str(coupling).upper()

    def get_input_coupling(self, channel):
        return self._coupling.get(int(channel), "DC")

    def set_input_impedance(self, channel, impedance="1E6"):
        val = str(impedance).upper()
        self._impedance[int(channel)] = 50.0 if val == "50" else 1e6

    def get_input_impedance(self, channel):
        return self._impedance.get(int(channel), 1e6)

    def set_input_attenuation(self, channel, attenuation=1):
        self._attenuation[int(channel)] = int(attenuation)

    def get_input_attenuation(self, channel):
        return float(self._attenuation.get(int(channel), 1))

    def set_input_lowpass_filter(self, channel, enabled):
        self._lowpass[int(channel)] = bool(enabled)

    def get_input_lowpass_filter(self, channel):
        return self._lowpass.get(int(channel), False)

    def set_input_range(self, channel, volt_range):
        self._range[int(channel)] = float(volt_range)

    def get_input_range(self, channel):
        return self._range.get(int(channel), 5.0)

    def set_input_range_auto(self, channel, enabled=True):
        pass

    def set_trigger_level(self, channel, level):
        self._level[int(channel)] = float(level)
        self._level_auto[int(channel)] = False

    def get_trigger_level(self, channel):
        return self._level.get(int(channel), 0.0)

    def set_trigger_level_auto(self, channel, enabled=True):
        self._level_auto[int(channel)] = bool(enabled)

    def set_trigger_level_relative(self, channel, percent):
        pass

    def set_trigger_slope(self, channel, slope="POS"):
        self._slope[int(channel)] = str(slope).upper()

    def get_trigger_slope(self, channel):
        return self._slope.get(int(channel), "POS")

    def set_trigger_hysteresis(self, channel, level):
        pass

    def configure_input(self, channel, coupling="DC", impedance="1E6",
                        attenuation=1, lowpass=False, slope="POS",
                        level=None, level_auto=None):
        self.set_input_coupling(channel, coupling)
        self.set_input_impedance(channel, impedance)
        self.set_input_attenuation(channel, attenuation)
        self.set_input_lowpass_filter(channel, lowpass)
        self.set_trigger_slope(channel, slope)
        if level_auto is True:
            self.set_trigger_level_auto(channel, True)
        elif level is not None:
            self.set_trigger_level(channel, level)

    def set_gate_time(self, gate_time_s):
        self._gate_time = float(gate_time_s)

    def get_gate_time(self):
        return self._gate_time

    def set_gate_source(self, source="TIME"):
        pass

    def get_gate_source(self):
        return "TIME"

    def set_gate_polarity(self, polarity="POS"):
        pass

    def set_function(self, func, channel=1):
        self._function = f'"{str(func).upper()} (@{int(channel)})"'

    def get_function(self):
        return self._function

    def measure_frequency(self, channel=1, expected=None, resolution=None):
        return self._sim_one()

    def measure_period(self, channel=1):
        return 1.0 / self._sim_one()

    def measure_duty_cycle(self, channel=1):
        return 50.0 + self._rng.gauss(0, 0.1)

    def measure_pulse_width(self, channel=1, positive=True):
        return 0.5 / self._sim_one()

    def measure_rise_time(self, channel=1):
        return 1e-9

    def measure_fall_time(self, channel=1):
        return 1e-9

    def configure_frequency(self, channel=1, expected=None, resolution=None):
        self._function = f'"FREQ (@{int(channel)})"'

    def configure_period(self, channel=1):
        self._function = f'"PER (@{int(channel)})"'

    def set_sample_count(self, count):
        self._sample_count = max(1, int(count))

    def get_sample_count(self):
        return self._sample_count

    def set_trigger_count(self, count):
        self._trigger_count = max(1, int(count))

    def initiate(self):
        self._last_values = self._sim_batch(self._sample_count)

    def abort(self):
        pass

    def read_value(self):
        return self._sim_one()

    def read_values(self, count=None):
        if count is not None:
            self.set_sample_count(count)
        self._last_values = self._sim_batch(self._sample_count)
        return list(self._last_values)

    def fetch_values(self):
        if not self._last_values:
            self._last_values = self._sim_batch(self._sample_count)
        return list(self._last_values)

    def data_points(self):
        return len(self._last_values)

    def data_remove(self, count, wait=False):
        n = min(int(count), len(self._last_values))
        taken = self._last_values[:n]
        self._last_values = self._last_values[n:]
        return taken

    def set_trigger_source(self, source="IMM"):
        self._trigger_source = str(source).upper()

    def get_trigger_source(self):
        return self._trigger_source

    def set_trigger_slope_edge(self, slope="POS"):
        pass

    def set_trigger_delay(self, delay_s):
        pass

    def trigger_bus(self):
        pass

    def enable_statistics(self, enabled=True):
        self._stat_enabled = bool(enabled)

    def clear_statistics(self):
        self._last_values = []

    def _stats(self):
        vals = self._last_values or self._sim_batch(self._sample_count)
        n = len(vals)
        avg = sum(vals) / n
        mn = min(vals)
        mx = max(vals)
        sd = (sum((v - avg) ** 2 for v in vals) / n) ** 0.5 if n > 1 else 0.0
        return avg, sd, mn, mx, n

    def stat_average(self):
        return self._stats()[0]

    def stat_min(self):
        return self._stats()[2]

    def stat_max(self):
        return self._stats()[3]

    def stat_stddev(self):
        return self._stats()[1]

    def stat_count(self):
        return self._stats()[4]

    def stat_all(self):
        avg, sd, mn, mx, n = self._stats()
        return {"average": avg, "stddev": sd, "min": mn, "max": mx, "count": n}

    def set_reference_source(self, source="INT"):
        self._reference = str(source).upper()

    def get_reference_source(self):
        return self._reference

    def set_reference_auto(self, enabled=True):
        pass

    def get_reference_external_frequency(self):
        return 10e6

    def set_reference_external_frequency(self, freq_hz):
        pass

    def measure_frequency_averaged(self, channel=1, sample_count=10,
                                   gate_time=None, expected=None,
                                   resolution=None):
        if gate_time is not None:
            self.set_gate_time(gate_time)
        self.set_sample_count(sample_count)
        values = self.read_values()
        stats = self.stat_all()
        return {
            "values": values,
            "average": stats["average"],
            "stddev": stats["stddev"],
            "min": stats["min"],
            "max": stats["max"],
            "count": stats["count"],
        }

    def identify_instrument(self):
        return self.identify()

    def disconnect(self):
        pass

    def close(self):
        pass

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


class MockKeysight34461A:

    def __init__(self):
        self._rng = random.Random(0)
        self._function = "VOLT"
        self._range = {}
        self._auto_range = {}
        self._nplc = {}
        self._trigger_source = "IMM"
        self._trigger_count = 1
        self._sample_count = 1
        self._stat_enabled = False
        self._last_values = []
        self.instr = MockInstr()

    def _sim_value(self):
        func = self._function.upper()
        if func.startswith("VOLT") and not func.endswith("AC"):
            return 3.3 + self._rng.gauss(0, 1e-4)
        if func.startswith("VOLT"):
            return 0.5 + self._rng.gauss(0, 1e-4)
        if func.startswith("CURR") and not func.endswith("AC"):
            return 0.012 + self._rng.gauss(0, 1e-6)
        if func.startswith("CURR"):
            return 0.001 + self._rng.gauss(0, 1e-6)
        if func.startswith("FRES"):
            return 100.05 + self._rng.gauss(0, 1e-3)
        if func.startswith("RES"):
            return 1000.0 + self._rng.gauss(0, 0.1)
        if func.startswith("FREQ"):
            return 1000.0 + self._rng.gauss(0, 0.01)
        if func.startswith("PER"):
            return 1e-3 + self._rng.gauss(0, 1e-9)
        if func.startswith("CAP"):
            return 1e-7 + self._rng.gauss(0, 1e-10)
        if func.startswith("TEMP"):
            return 25.0 + self._rng.gauss(0, 0.05)
        return 0.0 + self._rng.gauss(0, 1e-4)

    def _sim_batch(self, n):
        return [self._sim_value() for _ in range(max(1, int(n)))]

    # —— IEEE 488 ——
    def identify(self):
        return "Keysight Technologies,34461A,MOCK000,A.02.17-02.40-02.17-00.52-04-01"

    def reset(self):
        self._function = "VOLT"

    def clear_status(self):
        pass

    def self_test(self):
        return "+0"

    def query_opc(self, timeout_s=5.0):
        return True

    def get_errors(self, max_count=20):
        return ['+0,"No error"']

    # —— 显示 / 系统 ——
    def display_enable(self, enabled=True):
        pass

    def display_text(self, text):
        pass

    def display_text_clear(self):
        pass

    def beep(self):
        pass

    def set_beeper(self, enabled=True):
        pass

    def go_local(self):
        pass

    def go_remote(self):
        pass

    # —— SENSe ——
    def set_function(self, function):
        self._function = str(function).upper()

    def get_function(self):
        return self._function

    def set_range(self, function, range_value, auto=False):
        self._auto_range[str(function).upper()] = bool(auto)
        if not auto:
            self._range[str(function).upper()] = float(range_value)

    def get_range(self, function):
        return self._range.get(str(function).upper(), 10.0)

    def set_auto_range(self, function, enabled=True):
        self._auto_range[str(function).upper()] = bool(enabled)

    def set_nplc(self, function, nplc):
        self._nplc[str(function).upper()] = float(nplc)

    def get_nplc(self, function):
        return self._nplc.get(str(function).upper(), 10.0)

    def set_aperture(self, function, aperture_s):
        pass

    def set_autozero(self, function, enabled=True):
        pass

    def set_input_impedance_auto(self, enabled=True):
        pass

    # —— MEASure ——
    def _measure(self, func, range_value=None, resolution=None):
        self._function = func.upper()
        return self._sim_value()

    def measure_voltage_dc(self, range_value=None, resolution=None):
        return self._measure("VOLT", range_value, resolution)

    def measure_voltage_ac(self, range_value=None, resolution=None):
        return self._measure("VOLT:AC", range_value, resolution)

    def measure_current_dc(self, range_value=None, resolution=None):
        return self._measure("CURR", range_value, resolution)

    def measure_current_ac(self, range_value=None, resolution=None):
        return self._measure("CURR:AC", range_value, resolution)

    def measure_resistance(self, range_value=None, resolution=None):
        return self._measure("RES", range_value, resolution)

    def measure_resistance_4w(self, range_value=None, resolution=None):
        return self._measure("FRES", range_value, resolution)

    def measure_frequency(self, range_value=None, resolution=None):
        return self._measure("FREQ", range_value, resolution)

    def measure_period(self, range_value=None, resolution=None):
        return self._measure("PER", range_value, resolution)

    def measure_capacitance(self, range_value=None, resolution=None):
        return self._measure("CAP", range_value, resolution)

    def measure_temperature(self):
        return self._measure("TEMP")

    def measure_diode(self):
        return 0.65 + self._rng.gauss(0, 1e-3)

    def measure_continuity(self):
        return 5.0 + self._rng.gauss(0, 0.1)

    # —— CONFigure + READ?/FETCh? ——
    def _configure(self, func, range_value=None, resolution=None):
        self._function = func.upper()

    def configure_voltage_dc(self, range_value=None, resolution=None):
        self._configure("VOLT", range_value, resolution)

    def configure_voltage_ac(self, range_value=None, resolution=None):
        self._configure("VOLT:AC", range_value, resolution)

    def configure_current_dc(self, range_value=None, resolution=None):
        self._configure("CURR", range_value, resolution)

    def configure_current_ac(self, range_value=None, resolution=None):
        self._configure("CURR:AC", range_value, resolution)

    def configure_resistance(self, range_value=None, resolution=None):
        self._configure("RES", range_value, resolution)

    def configure_resistance_4w(self, range_value=None, resolution=None):
        self._configure("FRES", range_value, resolution)

    def configure_frequency(self, range_value=None, resolution=None):
        self._configure("FREQ", range_value, resolution)

    def configure_period(self, range_value=None, resolution=None):
        self._configure("PER", range_value, resolution)

    def configure_capacitance(self, range_value=None, resolution=None):
        self._configure("CAP", range_value, resolution)

    def configure_temperature(self):
        self._configure("TEMP")

    def get_configuration(self):
        return self._function

    def read_value(self):
        return self._sim_value()

    def read_values(self):
        self._last_values = self._sim_batch(self._sample_count)
        return list(self._last_values)

    def fetch_value(self):
        return self._sim_value()

    def fetch_values(self):
        if not self._last_values:
            self._last_values = self._sim_batch(self._sample_count)
        return list(self._last_values)

    # —— 触发 / 采样 ——
    def set_trigger_source(self, source="IMM"):
        self._trigger_source = str(source).upper()

    def get_trigger_source(self):
        return self._trigger_source

    def set_trigger_count(self, count):
        self._trigger_count = int(count)

    def get_trigger_count(self):
        return self._trigger_count

    def set_trigger_delay(self, delay_s):
        pass

    def set_trigger_delay_auto(self, enabled=True):
        pass

    def set_trigger_slope(self, slope="NEG"):
        pass

    def set_sample_count(self, count):
        self._sample_count = int(count)

    def get_sample_count(self):
        return self._sample_count

    def set_sample_source(self, source="IMM"):
        pass

    def set_sample_timer(self, interval_s):
        pass

    def initiate(self):
        self._last_values = self._sim_batch(self._sample_count)

    def abort(self):
        pass

    def trigger_bus(self):
        pass

    # —— 数据缓冲 ——
    def data_points(self):
        return len(self._last_values)

    def data_remove(self, count):
        n = min(int(count), len(self._last_values))
        taken = self._last_values[:n]
        self._last_values = self._last_values[n:]
        return taken

    # —— 统计 ——
    def enable_statistics(self, enabled=True):
        self._stat_enabled = bool(enabled)

    def clear_statistics(self):
        self._last_values = []

    def _stats(self):
        vals = self._last_values or self._sim_batch(self._sample_count)
        n = len(vals)
        avg = sum(vals) / n
        mn = min(vals)
        mx = max(vals)
        sd = (sum((v - avg) ** 2 for v in vals) / n) ** 0.5 if n > 1 else 0.0
        return avg, sd, mn, mx, n

    def stat_average(self):
        return self._stats()[0]

    def stat_min(self):
        return self._stats()[2]

    def stat_max(self):
        return self._stats()[3]

    def stat_stddev(self):
        return self._stats()[1]

    def stat_count(self):
        return self._stats()[4]

    def stat_peak_to_peak(self):
        _, _, mn, mx, _ = self._stats()
        return mx - mn

    def enable_null(self, enabled=True, offset=None):
        pass

    def set_limit_test(self, lower, upper, enabled=True):
        pass

    # —— 温度 ——
    def set_temperature_transducer(self, transducer="FRTD", value=None):
        pass

    def set_temperature_unit(self, unit="C"):
        pass

    # —— 高层便捷 ——
    def measure_average(self, function="VOLTage:DC", sample_count=10,
                        range_value=None, resolution=None):
        self._configure(function.upper(), range_value, resolution)
        self.set_sample_count(sample_count)
        values = self.read_values()
        avg, sd, mn, mx, n = self._stats()
        return {
            "values": values,
            "average": avg,
            "min": mn,
            "max": mx,
            "stddev": sd,
            "ptp": mx - mn,
            "count": n,
        }

    def measure_burst(self, function="VOLTage:DC", sample_count=100,
                      sample_interval_s=None, range_value=None, resolution=None):
        self._configure(function.upper(), range_value, resolution)
        self.set_sample_count(sample_count)
        return self.read_values()

    def identify_instrument(self):
        return self.identify()

    def disconnect(self):
        pass

    def close(self):
        pass

    def format_voltage(self, voltage_V):
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
        abs_r = abs(resistance_ohm)
        if abs_r >= 1e9:
            return f"{resistance_ohm/1e9:.4f} GΩ"
        elif abs_r >= 1e6:
            return f"{resistance_ohm/1e6:.4f} MΩ"
        elif abs_r >= 1e3:
            return f"{resistance_ohm/1e3:.4f} kΩ"
        else:
            return f"{resistance_ohm:.4f} Ω"


class _MockCMWBase:
    """R&S CMW 系列 (CMW270 / CMW500) 无线综测仪 Mock 基类。"""

    MODEL = "MOCK CMW"
    DEFAULT_RESOURCE = "TCPIP0::10.31.31.236::hislip0::INSTR"

    BT_MEAS = "BLUetooth:MEASurement"
    BT_SIGN = "BLUetooth:SIGNaling"
    BLE_MEAS = "BLUetooth:MEASurement"
    BLE_SIGN = "BLUetooth:SIGNaling"
    LTE_SIGN = "LTE:SIGNaling"
    LTE_MEAS = "LTE:MEASurement"
    WIFI_MEAS = "WLAN:MEASurement"
    WIFI_SIGN = "WLAN:SIGNaling"

    def __init__(self, resource=None, visa_library=None, timeout_ms=10000):
        self.resource = resource or self.DEFAULT_RESOURCE
        self._rng = random.Random(0)
        self._connected = True
        self.instr = MockInstr()

    # —— 基础 IO ——
    def write(self, cmd):
        pass

    def query(self, cmd):
        return "0"

    def query_float(self, cmd):
        return 0.0

    def query_int(self, cmd):
        return 0

    def query_values(self, cmd):
        return [0.0]

    # —— IEEE 488.2 ——
    def identify(self):
        return f"Rohde&Schwarz,{self.MODEL.replace('MOCK ', '')},MOCK000,3.8.10"

    def reset(self):
        pass

    def clear_status(self):
        pass

    def self_test(self):
        return "0"

    def wait(self):
        pass

    def operation_complete(self):
        pass

    def query_opc(self, timeout_s=10.0):
        return True

    def get_errors(self, max_count=50):
        return ['0,"No error"']

    def get_options(self):
        return ["CMW-KM010", "CMW-KM050", "CMW-KM500", "CMW-KW500"]

    def get_firmware_version(self):
        return "3.8.10"

    def set_remote(self):
        pass

    def go_to_local(self):
        pass

    def set_timeout(self, timeout_ms):
        pass

    # —— 通用测量控制 ——
    def init_measurement(self, application):
        pass

    def stop_measurement(self, application):
        pass

    def abort_measurement(self, application):
        pass

    def fetch(self, application_path):
        return [self._rng.uniform(-5, 5)]

    def read(self, application_path):
        return [self._rng.uniform(-5, 5)]

    def get_measurement_state(self, application):
        return "RDY"

    def wait_for_ready(self, application, timeout_s=30.0, poll_s=0.5):
        return True

    def disconnect(self):
        self._connected = False

    def is_connected(self):
        return self._connected

    # —— BT ——
    def bt_reset(self): pass
    def bt_set_demod_mode(self, mode="BRATe"): pass
    def bt_get_demod_mode(self): return "BRATe"
    def bt_set_burst_type(self, burst_type="BR"): pass
    def bt_set_packet_type(self, packet_type="DH1"): pass
    def bt_get_packet_type(self): return "DH1"
    def bt_set_payload_length(self, length): pass
    def bt_get_payload_length(self): return 37
    def bt_set_pattern(self, pattern="PRBS9"): pass
    def bt_get_pattern(self): return "PRBS9"
    def bt_set_trigger(self, source="IFPower"): pass
    def bt_set_trigger_level(self, level_dbm=-20): pass
    def bt_set_rf_input(self, connector="RF1C", attenuation_db=0.0): pass
    def bt_get_rf_connector(self): return "RF1C"
    def bt_set_frequency(self, freq_hz): pass
    def bt_get_frequency(self): return 2402e6
    def bt_channel_to_freq_hz(self, channel): return (2402 + int(channel)) * 1_000_000
    def bt_set_channel(self, channel): pass
    def bt_set_expected_power(self, power_dbm): pass
    def bt_get_expected_power(self): return 0.0
    def bt_set_expected_power_auto(self, auto=True): pass
    def bt_set_user_margin(self, margin_db=0.0): pass
    def bt_get_user_margin(self): return 0.0
    def bt_set_repetition(self, mode="SINGleshot"): pass
    def bt_get_repetition(self): return "SINGleshot"
    def bt_set_meas_count(self, count): pass
    def bt_get_meas_count(self): return 10
    def bt_init_meval(self): pass
    def bt_abort_meval(self): pass
    def bt_stop_meval(self): pass
    def bt_meval_state(self): return "RDY"
    def bt_fetch_power(self): return [0.5 + self._rng.gauss(0, 0.1)]
    def bt_read_power(self): return [0.5 + self._rng.gauss(0, 0.1)]
    def bt_fetch_peak_power(self): return [1.5 + self._rng.gauss(0, 0.1)]
    def bt_fetch_modulation(self): return [150e3, 130e3, 0.9]
    def bt_fetch_edr_modulation(self): return [0.05, 0.12, 0.10]
    def bt_fetch_freq_offset(self): return [-30.0, -32.0]
    def bt_fetch_spectrum_acp(self): return [-40.0, -42.0]
    def bt_fetch_20db_bandwidth(self): return [950e3]
    def bt_get_average_power_dbm(self): return 0.5 + self._rng.gauss(0, 0.1)
    def bt_signaling_on(self): pass
    def bt_signaling_off(self): pass
    def bt_signaling_state(self): return "ON"
    def bt_set_tx_power(self, power_dbm): pass
    def bt_get_tx_power(self): return -40.0
    def bt_set_test_mode(self, mode="LOOPback"): pass
    def bt_get_test_mode(self): return "LOOPback"
    def bt_set_dut_bd_address(self, bd_address): pass
    def bt_get_dut_bd_address(self): return "00:11:22:33:44:55"
    def bt_connect_dut(self, bd_address=None): pass
    def bt_disconnect_dut(self): pass
    def bt_get_connection_state(self): return "CONN"
    def bt_inquiry(self): pass
    def bt_page(self): pass
    def bt_abort_call(self): pass
    def bt_set_page_scan(self, enabled=True): pass
    def bt_set_inquiry_scan(self, enabled=True): pass
    def bt_set_per_packets(self, packet_count): pass
    def bt_get_per_packets(self): return 1000
    def bt_set_per_payload_length(self, length): pass
    def bt_init_per(self): pass
    def bt_abort_per(self): pass
    def bt_fetch_per(self): return [0.0, 1000]
    def bt_get_per_percent(self): return 0.0

    # —— BLE ——
    def ble_reset(self): pass
    def ble_set_phy(self, phy="LE1M"): pass
    def ble_get_phy(self): return "LE1M"
    def ble_set_packet_type(self, packet_type="RFPHytest"): pass
    def ble_get_packet_type(self): return "RFPHytest"
    def ble_set_payload_length(self, length): pass
    def ble_get_payload_length(self): return 37
    def ble_set_pattern(self, pattern="ALL1"): pass
    def ble_get_pattern(self): return "ALL1"
    def ble_set_trigger(self, source="IFPower"): pass
    def ble_set_trigger_level(self, level_dbm=-20): pass
    def ble_set_rf_input(self, connector="RF1C", attenuation_db=0.0): pass
    def ble_get_rf_connector(self): return "RF1C"
    def ble_set_frequency(self, freq_hz): pass
    def ble_get_frequency(self): return 2402e6
    def ble_channel_to_freq_hz(self, channel): return 2402e6
    def ble_set_channel(self, channel): pass
    def ble_get_channel(self): return 0
    def ble_set_expected_power(self, power_dbm): pass
    def ble_get_expected_power(self): return 0.0
    def ble_set_expected_power_auto(self, auto=True): pass
    def ble_set_user_margin(self, margin_db=0.0): pass
    def ble_get_user_margin(self): return 0.0
    def ble_set_repetition(self, mode="SINGleshot"): pass
    def ble_get_repetition(self): return "SINGleshot"
    def ble_set_meas_count(self, count): pass
    def ble_get_meas_count(self): return 10
    def ble_init_meval(self): pass
    def ble_abort_meval(self): pass
    def ble_stop_meval(self): pass
    def ble_meval_state(self): return "RDY"
    def ble_fetch_power(self): return [0.0 + self._rng.gauss(0, 0.1)]
    def ble_read_power(self): return [0.0 + self._rng.gauss(0, 0.1)]
    def ble_fetch_peak_power(self): return [1.0 + self._rng.gauss(0, 0.1)]
    def ble_fetch_modulation(self): return [250e3, 230e3, 0.92]
    def ble_fetch_freq_accuracy(self): return [-10.0, 5.0, 8.0]
    def ble_fetch_spectrum_acp(self): return [-35.0, -37.0]
    def ble_fetch_20db_bandwidth(self): return [850e3]
    def ble_get_average_power_dbm(self): return 0.0 + self._rng.gauss(0, 0.1)
    def ble_signaling_on(self): pass
    def ble_signaling_off(self): pass
    def ble_signaling_state(self): return "ON"
    def ble_set_tx_power(self, power_dbm): pass
    def ble_get_tx_power(self): return -40.0
    def ble_set_dut_address(self, address): pass
    def ble_get_dut_address(self): return "00:11:22:33:44:55"
    def ble_connect_dut(self, address=None): pass
    def ble_disconnect_dut(self): pass
    def ble_get_connection_state(self): return "CONN"
    def ble_abort_call(self): pass
    def ble_set_connection_interval(self, interval_ms): pass
    def ble_get_connection_interval(self): return 30.0
    def ble_set_connection_latency(self, latency): pass
    def ble_get_connection_latency(self): return 0
    def ble_set_connection_timeout(self, timeout_ms): pass
    def ble_get_connection_timeout(self): return 1000.0
    def ble_set_phy_update(self, phy="LE1M"): pass
    def ble_get_phy_update(self): return "LE1M"
    def ble_set_advertising_type(self, adv_type="ADVIND"): pass
    def ble_set_advertising_interval(self, interval_ms): pass
    def ble_set_advertising_channel(self, channels="37,38,39"): pass
    def ble_set_per_packets(self, packet_count): pass
    def ble_get_per_packets(self): return 1500
    def ble_set_per_phy(self, phy="LE1M"): pass
    def ble_init_per(self): pass
    def ble_abort_per(self): pass
    def ble_fetch_per(self): return [0.0, 1500]
    def ble_get_per_percent(self): return 0.0

    # —— LTE ——
    def lte_reset(self): pass
    def lte_set_duplex_mode(self, mode="FDD"): pass
    def lte_get_duplex_mode(self): return "FDD"
    def lte_set_band(self, band): pass
    def lte_get_band(self): return "OB1"
    def lte_set_dl_channel(self, earfcn): pass
    def lte_get_dl_channel(self): return 100
    def lte_set_ul_channel(self, earfcn): pass
    def lte_get_ul_channel(self): return 18100
    def lte_set_bandwidth(self, bw="B100"): pass
    def lte_get_dl_bandwidth(self): return "B100"
    def lte_get_ul_bandwidth(self): return "B100"
    def lte_set_tdd_uldl_config(self, config=0): pass
    def lte_set_tdd_special_subframe(self, ss_config=7): pass
    def lte_set_rf_connector(self, output="RF1C", input_conn="RF1C"): pass
    def lte_set_dl_power(self, power_dbm): pass
    def lte_get_dl_power(self): return -80.0
    def lte_set_expected_ul_power(self, power_dbm): pass
    def lte_get_expected_ul_power(self): return 23.0
    def lte_set_external_attenuation(self, output_db=0.0, input_db=0.0): pass
    def lte_cell_on(self): pass
    def lte_cell_off(self): pass
    def lte_cell_state(self): return "ON,ADJ"
    def lte_get_connection_state(self): return "CEST"
    def lte_connect_ue(self): pass
    def lte_disconnect_ue(self): pass
    def lte_attach_ue(self): pass
    def lte_detach_ue(self): pass
    def lte_abort_call(self): pass
    def lte_get_cell_id(self): return 100
    def lte_set_cell_id(self, pci): pass
    def lte_set_imsi(self, imsi): pass
    def lte_get_imsi(self): return "001010000000000"
    def lte_set_imei(self, imei): pass
    def lte_get_imei(self): return "000000000000000"
    def lte_set_scheduling_type(self, sched="RMC"): pass
    def lte_set_ul_rb(self, num_rb, start_rb=0): pass
    def lte_set_dl_rb(self, num_rb, start_rb=0): pass
    def lte_set_ul_modulation(self, modulation="QPSK"): pass
    def lte_set_dl_modulation(self, modulation="QPSK"): pass
    def lte_set_transmission_mode(self, tm=1): pass
    def lte_get_transmission_mode(self): return 1
    def lte_set_mimo(self, antenna_config="1x1"): pass
    def lte_set_ul_tpc(self, tpc_step_db=0): pass
    def lte_set_meas_connector(self, connector="RF1C"): pass
    def lte_set_meas_frequency(self, freq_hz): pass
    def lte_set_meas_bandwidth(self, bw="B100"): pass
    def lte_set_meas_expected_power(self, power_dbm): pass
    def lte_init_meval(self): pass
    def lte_abort_meval(self): pass
    def lte_stop_meval(self): pass
    def lte_meval_state(self): return "RDY"
    def lte_fetch_tx_power(self): return [23.0 + self._rng.gauss(0, 0.2)]
    def lte_fetch_modulation(self): return [1.5, 0.02, 0.01]
    def lte_fetch_evm(self): return [1.5, 1.8]
    def lte_fetch_spectrum(self): return [-40.0, -42.0]
    def lte_fetch_spectrum_emask(self): return [-40.0, -42.0]
    def lte_fetch_iq_offset(self): return [-30.0]
    def lte_fetch_freq_error(self): return [50.0]
    def lte_init_throughput(self): pass
    def lte_abort_throughput(self): pass
    def lte_fetch_bler(self): return [0.0, 100.0]
    def lte_fetch_ul_throughput(self): return [5.0]
    def lte_fetch_dl_throughput(self): return [50.0]
    def lte_set_ping_target(self, target="127.0.0.1"): pass
    def lte_set_ping_count(self, count=4): pass
    def lte_init_ping(self): pass
    def lte_fetch_ping(self): return [4, 4, 0, 10.0]

    # —— WIFI ——
    def wifi_reset(self): pass
    def wifi_set_standard(self, standard="NSTD"): pass
    def wifi_get_standard(self): return "NSTD"
    def wifi_set_bandwidth(self, bandwidth="BW20"): pass
    def wifi_get_bandwidth(self): return "BW20"
    def wifi_set_mcs(self, mcs): pass
    def wifi_get_mcs(self): return 0
    def wifi_set_spatial_streams(self, streams=1): pass
    def wifi_set_guard_interval(self, gi="GI400"): pass
    def wifi_set_bursts_count(self, count): pass
    def wifi_set_power_count(self, count): pass
    def wifi_set_trigger(self, source="IFPower"): pass
    def wifi_set_trigger_level(self, level_dbm=-20): pass
    def wifi_set_rf_input(self, connector="RF1C", attenuation_db=0.0): pass
    def wifi_get_rf_connector(self): return "RF1C"
    def wifi_set_frequency(self, freq_hz): pass
    def wifi_get_frequency(self): return 2437e6
    def wifi_channel_to_freq_hz(self, channel, band="B24G"): return 2437e6
    def wifi_set_channel(self, channel, band="B24G"): pass
    def wifi_get_channel(self): return "6,B24G"
    def wifi_set_expected_power(self, power_dbm): pass
    def wifi_get_expected_power(self): return 0.0
    def wifi_set_expected_power_auto(self, auto=True): pass
    def wifi_set_user_margin(self, margin_db=0.0): pass
    def wifi_get_user_margin(self): return 0.0
    def wifi_set_repetition(self, mode="SINGleshot"): pass
    def wifi_get_repetition(self): return "SINGleshot"
    def wifi_init_meval(self): pass
    def wifi_abort_meval(self): pass
    def wifi_stop_meval(self): pass
    def wifi_meval_state(self): return "RDY"
    def wifi_fetch_power(self): return [10.0 + self._rng.gauss(0, 0.2)]
    def wifi_read_power(self): return [10.0 + self._rng.gauss(0, 0.2)]
    def wifi_fetch_peak_power(self): return [15.0 + self._rng.gauss(0, 0.2)]
    def wifi_fetch_modulation(self): return [-35.0, 1.0, 2.0]
    def wifi_fetch_evm(self): return [-35.0, -33.0]
    def wifi_fetch_center_freq_error(self): return [100.0]
    def wifi_fetch_clock_error(self): return [5.0]
    def wifi_fetch_iq_offset(self): return [-30.0]
    def wifi_fetch_spectrum(self): return [-45.0, -47.0]
    def wifi_fetch_spectrum_flatness(self): return [-2.0, 2.0]
    def wifi_get_average_power_dbm(self): return 10.0 + self._rng.gauss(0, 0.2)
    def wifi_signaling_on(self): pass
    def wifi_signaling_off(self): pass
    def wifi_signaling_state(self): return "ON"
    def wifi_set_operation_mode(self, mode="AP"): pass
    def wifi_get_operation_mode(self): return "AP"
    def wifi_set_ssid(self, ssid): pass
    def wifi_get_ssid(self): return "CMW_AP"
    def wifi_set_signaling_standard(self, standard="NSTD"): pass
    def wifi_set_signaling_channel(self, channel, band="B24G"): pass
    def wifi_set_signaling_bandwidth(self, bw="BW20"): pass
    def wifi_set_tx_power(self, power_dbm): pass
    def wifi_get_tx_power(self): return -50.0
    def wifi_set_security(self, security="OPEN"): pass
    def wifi_set_passphrase(self, passphrase): pass
    def wifi_connect_dut(self): pass
    def wifi_disconnect_dut(self): pass
    def wifi_abort_call(self): pass
    def wifi_get_connection_state(self): return "ASSociated"
    def wifi_set_per_packets(self, packet_count): pass
    def wifi_get_per_packets(self): return 1000
    def wifi_init_per(self): pass
    def wifi_abort_per(self): pass
    def wifi_fetch_per(self): return [0.0, 1000]
    def wifi_get_per_percent(self): return 0.0
    def wifi_init_throughput(self): pass
    def wifi_abort_throughput(self): pass
    def wifi_fetch_throughput(self): return [50.0, 5.0]
    def wifi_set_ping_target(self, target="127.0.0.1"): pass
    def wifi_set_ping_count(self, count=4): pass
    def wifi_init_ping(self): pass
    def wifi_fetch_ping(self): return [4, 4, 0, 10.0]


class MockCMW270(_MockCMWBase):
    MODEL = "MOCK CMW270"


class MockCMW500(_MockCMWBase):
    MODEL = "MOCK CMW500"
