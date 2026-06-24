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
        self._pin_dirs[pin] = self.DIR_OUTPUT
        self._pin_values[pin] = 1 if int(value) else 0

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
