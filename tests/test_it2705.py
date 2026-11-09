import math

import pytest

import instruments.factory as factory
import instruments.power.itech.it2705 as it2705_module
from instruments.mock.mock_instruments import MockIT2705
from instruments.power.itech.it2705 import IT2705


class FakeSession:
    def __init__(self):
        self.timeout = None
        self.encoding = None
        self.closed = False
        self.commands = []
        self.responses = {"*IDN?": "ITECH,IT2705,TEST,1.0"}

    def write(self, command):
        self.commands.append(command)
        return 0

    def query(self, command):
        self.commands.append(command)
        return self.responses.get(command, "0")

    def close(self):
        self.closed = True


class FakeResourceManager:
    def __init__(self):
        self.session = FakeSession()
        self.opened_resources = []
        self.closed = False

    def open_resource(self, resource):
        self.opened_resources.append(resource)
        return self.session

    def close(self):
        self.closed = True


@pytest.fixture
def connected_driver(monkeypatch):
    resource_manager = FakeResourceManager()
    monkeypatch.setattr(
        it2705_module.pyvisa, "ResourceManager", lambda *args: resource_manager
    )
    driver = IT2705("MOCK")
    return driver, resource_manager


def test_connect_identify_and_disconnect(connected_driver):
    driver, resource_manager = connected_driver
    assert resource_manager.opened_resources == ["TCPIP0::MOCK::inst0::INSTR"]
    assert driver.instr.timeout == 10000
    assert driver.identify() == "ITECH,IT2705,TEST,1.0"
    assert driver.is_connected()
    assert driver.disconnect()
    assert resource_manager.session.closed
    assert resource_manager.closed
    assert not driver.is_connected()


def test_n6705c_probe_configures_socket_terminations(monkeypatch):
    import instruments.power.keysight.n6705c as n6705c_module

    resource_manager = FakeResourceManager()
    resource_manager.visalib = "MOCK"
    monkeypatch.setattr(
        n6705c_module.pyvisa, "ResourceManager", lambda *args: resource_manager
    )
    driver = n6705c_module.N6705C("TCPIP0::MOCK::30000::SOCKET")

    assert driver.instr.read_termination == "\n"
    assert driver.instr.write_termination == "\n"
    driver.disconnect()


def test_channel_module_whitelist_and_empty_slots(connected_driver, monkeypatch):
    driver, resource_manager = connected_driver
    session = resource_manager.session
    models = {
        1: '"IT27814"',
        2: "IT27814E",
        3: "IT27812",
        4: "NONE",
        5: "",
        6: "it27814e",
        7: "IT27814",
    }
    for channel, model in models.items():
        session.responses[f"SYST:CHAN:MOD? (@{channel})"] = model
    original_query = session.query

    def query_with_failure(command):
        if command == "SYST:CHAN:MOD? (@8)":
            raise RuntimeError("query failed")
        return original_query(command)

    monkeypatch.setattr(session, "query", query_with_failure)
    assert driver.refresh_channel_modules() == {
        **models,
        1: "IT27814",
        6: "IT27814E",
        8: "",
    }
    assert [
        channel for channel in driver.VALID_CHANNELS
        if driver.is_channel_supported(channel)
    ] == [1, 2, 6, 7]


def test_channel_voltage_current_and_output_commands(connected_driver):
    driver, resource_manager = connected_driver
    driver.set_voltage(2, 3.3)
    driver.set_current(2, 0.25)
    driver.set_current_limit(2, 0.5)
    driver.set_voltage_limit(2, 5.0)
    driver.channel_on(2)
    driver.set_output_off_mode(2, "HIGHZ")
    assert resource_manager.session.commands == [
        "VOLT 3.3,(@2)",
        "CURR 0.25,(@2)",
        "CURR:LIM 0.5,(@2)",
        "VOLT:LIM:HIGH 5.0,(@2)",
        "OUTP ON,(@2)",
        "OUTP:TMOD HIGHZ,(@2)",
    ]
    with pytest.raises(ValueError, match="无效通道号"):
        driver.channel_on(9)


def test_arb_voltage_sine_uses_it2700_mode_command(connected_driver):
    driver, resource_manager = connected_driver
    driver.set_arb_sine(1, dc_offset=3.0, amplitude_vrms=0.1, frequency=1000)
    commands = resource_manager.session.commands
    assert commands[0] == "ARB:FUNC:TYPE VOLT,(@1)"
    assert commands[1] == "ARB:FUNC:SHAP SIN,(@1)"
    amplitude_command = commands[3]
    amplitude = float(amplitude_command.split()[1].split(",", 1)[0])
    assert amplitude == pytest.approx(math.sqrt(2) * 0.1)
    assert commands[-1] == "OUTP:FUNC:MODE ARB,(@1)"


def test_arb_current_pulse_and_continuous(connected_driver):
    driver, resource_manager = connected_driver
    driver.set_arb_current_pulse(3, -0.01, -0.1, 0.004, 0.0, 0.006, 100)
    driver.set_arb_continuous(3, flag=True)
    driver.arb_on(3)
    driver.arb_run(3)
    commands = resource_manager.session.commands
    assert "ARB:CURR:PULS:TOP -0.1,(@3)" in commands
    assert "ARB:CURR:PULS:TOP:TIME 0.006,(@3)" in commands
    assert "ARB:COUN 0,(@3)" in commands
    assert "INIT:TRAN (@3)" in commands
    assert "TRIG:TRAN:SOUR BUS,(@3)" in commands
    assert commands[-1] == "*TRG"


def test_fetch_current_by_datalog(connected_driver, monkeypatch):
    driver, resource_manager = connected_driver
    resource_manager.session.responses["FETC:DLOG:CURR? (@1)"] = "0.125"
    monkeypatch.setattr(
        IT2705,
        "_interruptible_sleep",
        staticmethod(lambda duration, on_progress=None, stop_check=None: True),
    )
    result = driver.fetch_current_by_datalog([1], test_time=2, sample_period=0.001)
    assert result == {1: 0.125}
    commands = resource_manager.session.commands
    assert "SENS:DLOG:FUNC:CURR ON,(@1)" in commands
    assert "SENS:DLOG:TIME 2.0" in commands
    assert "SENS:DLOG:PER 0.001" in commands
    assert 'INIT:DLOG "Dlog_file"' in commands
    assert "SENS:DLOG:MARK1:POIN 0.2" in commands
    assert "SENS:DLOG:MARK2:POIN 1.8" in commands


def test_fetch_datalog_all(connected_driver):
    driver, resource_manager = connected_driver
    resource_manager.session.responses["FETC:DLOG:ALL? (@2)"] = (
        "1,2,3,4,5,6,7,8,9,10"
    )
    result = driver.fetch_datalog_all(2)
    assert result["ahour"] == 1
    assert result["current_avg"] == 3
    assert result["voltage_ptp"] == 10


def test_mock_supports_power_and_datalog_interfaces(monkeypatch):
    mock = MockIT2705()
    assert mock.identify() == "ITECH,IT2705,MOCK,1.0"
    mock.set_voltage(1, 3.8)
    mock.set_current(1, 0.02)
    mock.channel_on(1)
    assert mock.measure_voltage(1) == pytest.approx(3.8)
    assert mock.measure_current(1) == pytest.approx(0.02)
    assert mock.measure_power(1) == pytest.approx(3.8 * 0.02)
    assert mock.get_channel_state(1)
    monkeypatch.setattr(it2705_module.time, "sleep", lambda duration: None)
    currents, voltages = mock.fetch_by_datalog([1], [1], 1, 0.001)
    assert currents == {1: 0.02}
    assert voltages == {1: 3.8}
    assert mock.fetch_datalog_all(1)["current_avg"] == 0.02
    mock.disconnect()
    assert not mock.is_connected()
    assert mock.connect()
    assert mock.is_connected()


def test_factory_registers_it2705_and_returns_mock(monkeypatch):
    created = []

    class FakeIT2705:
        def __init__(self, resource, visa_library=None):
            created.append((resource, visa_library))

    monkeypatch.setattr(factory, "IT2705", FakeIT2705)
    result = factory.create_instrument(
        "it2705", resource="MOCK_RESOURCE", visa_library="MOCK_LIBRARY"
    )
    assert isinstance(result, FakeIT2705)
    assert created == [("MOCK_RESOURCE", "MOCK_LIBRARY")]

    import debug_config

    monkeypatch.setattr(debug_config, "DEBUG_MOCK", True)
    mock = factory.create_power_analyzer("", analyzer_type="it2705")
    assert isinstance(mock, MockIT2705)
    auto_mock = factory.create_power_analyzer(
        "MOCK::IT2705::A", analyzer_type="auto"
    )
    assert isinstance(auto_mock, MockIT2705)
    assert factory.get_power_analyzer_model(auto_mock) == "IT2705"


def _fake_power_class(idn):
    class FakePower:
        instances = []

        def __init__(self, resource, visa_library=None):
            self.resource = resource
            self.visa_library = visa_library
            self.disconnect_calls = 0
            self.module_refresh_calls = 0
            type(self).instances.append(self)

        def refresh_channel_modules(self):
            self.module_refresh_calls += 1

        def identify(self):
            return idn

        def disconnect(self):
            self.disconnect_calls += 1

    return FakePower


@pytest.mark.parametrize(
    ("probe_idn", "expected_model", "expect_it2705"),
    [
        ("KEYSIGHT,N6705C,SERIAL,1.0", "N6705C", False),
        ("ITECH,IT2705,SERIAL,1.0", "IT2705", True),
    ],
)
def test_factory_auto_detects_power_model(
    monkeypatch, probe_idn, expected_model, expect_it2705
):
    import debug_config

    probe_class = _fake_power_class(probe_idn)
    it2705_class = _fake_power_class("ITECH,IT2705,SERIAL,1.0")
    monkeypatch.setattr(debug_config, "DEBUG_MOCK", False)
    monkeypatch.setattr(factory, "N6705C", probe_class)
    monkeypatch.setattr(factory, "IT2705", it2705_class)

    result = factory.create_power_analyzer(
        "TEST_RESOURCE", analyzer_type="auto", visa_library="TEST_LIBRARY"
    )

    assert factory.get_power_analyzer_model(result) == expected_model
    assert isinstance(result, it2705_class if expect_it2705 else probe_class)
    assert result.module_refresh_calls == 1
    assert probe_class.instances[0].visa_library == "TEST_LIBRARY"
    if expect_it2705:
        assert probe_class.instances[0].disconnect_calls == 1
        assert it2705_class.instances[0].resource == "TEST_RESOURCE"
    else:
        assert probe_class.instances[0].disconnect_calls == 0
        assert not it2705_class.instances


def test_factory_auto_rejects_unsupported_idn_and_disconnects(monkeypatch):
    import debug_config

    probe_class = _fake_power_class("VENDOR,UNKNOWN,SERIAL,1.0")
    it2705_class = _fake_power_class("ITECH,IT2705,SERIAL,1.0")
    monkeypatch.setattr(debug_config, "DEBUG_MOCK", False)
    monkeypatch.setattr(factory, "N6705C", probe_class)
    monkeypatch.setattr(factory, "IT2705", it2705_class)

    with pytest.raises(ValueError, match="Unsupported power analyzer IDN"):
        factory.create_power_analyzer("TEST_RESOURCE", analyzer_type="auto")

    assert probe_class.instances[0].disconnect_calls == 1
    assert not it2705_class.instances


def test_factory_auto_cleans_up_when_identity_changes(monkeypatch):
    import debug_config

    probe_class = _fake_power_class("ITECH,IT2705,SERIAL,1.0")
    changed_class = _fake_power_class("KEYSIGHT,N6705C,SERIAL,1.0")
    monkeypatch.setattr(debug_config, "DEBUG_MOCK", False)
    monkeypatch.setattr(factory, "N6705C", probe_class)
    monkeypatch.setattr(factory, "IT2705", changed_class)

    with pytest.raises(ConnectionError, match="identity changed"):
        factory.create_power_analyzer("TEST_RESOURCE", analyzer_type="auto")

    assert changed_class.instances[0].disconnect_calls == 1
    assert probe_class.instances[0].disconnect_calls >= 1


def test_power_profile_verify_uses_idn_identity():
    from core.instruments.registry import _verify_n6705c

    instance = _fake_power_class("ITECH,IT2705,SERIAL123,2.0")("TEST_RESOURCE")
    identity = _verify_n6705c(instance)

    assert identity.vendor == "ITECH"
    assert identity.model == "IT2705"
    assert identity.serial == "SERIAL123"
    assert identity.firmware == "2.0"


def test_datalog_worker_samples_it2705_in_real_units():
    from ui.pages.power_anaalyzer.datalog.workers import _DatalogWorker

    class SoftwarePower:
        def measure_voltage(self, channel):
            return channel + 0.5

        def measure_current(self, channel):
            return channel / 1000.0

    worker = _DatalogWorker(
        [SoftwarePower()], [[1, 8]], [""], "current", 20, 0,
        debug=False, voltage_channels_per_unit=[[1, 8]],
    )
    results = []
    raw_results = []
    errors = []
    finished = []
    worker.data_ready.connect(results.append)
    worker.dlog_raw_ready.connect(raw_results.append)
    worker.error.connect(errors.append)
    worker.finished.connect(lambda: finished.append(True))

    worker.run()

    assert errors == []
    assert finished == [True]
    assert raw_results == [[]]
    data = results[0]
    assert data["CH1 V"]["values"] == [1500.0]
    assert data["CH8 V"]["values"] == [8500.0]
    assert data["CH1 I"]["values"] == [1.0]
    assert data["CH8 I"]["values"] == [8.0]
    assert all(series["time"][0] >= 0 for series in data.values())


def test_datalog_worker_mixes_native_and_software_units(monkeypatch):
    from ui.pages.power_anaalyzer.datalog import workers as datalog_workers

    class NativeInstr:
        def __init__(self):
            self.timeout = 1000
            self.commands = []

        def write(self, command):
            self.commands.append(command)

        def query(self, command):
            self.commands.append(command)
            return "0" if command.startswith("STAT:OPER:COND?") else "1"

    class NativePower:
        def __init__(self):
            self.instr = NativeInstr()

        def read_mmem_data(self, filepath):
            return b"native-dlog"

    class SoftwarePower:
        def measure_voltage(self, channel):
            return 3.3

        def measure_current(self, channel):
            return 0.025

    monkeypatch.setattr(datalog_workers.time, "sleep", lambda duration: None)
    monkeypatch.setattr(
        datalog_workers,
        "parse_dlog_binary",
        lambda raw, curr, volt, label, period: {
            "A CH1 I": {"time": [0.0], "values": [10.0]}
        },
    )
    worker = datalog_workers._DatalogWorker(
        [NativePower(), SoftwarePower()], [[1], [8]], ["A", "B"],
        "current", 20, 0, debug=False, voltage_channels_per_unit=[[1], [8]],
    )
    results = []
    raw_results = []
    errors = []
    worker.data_ready.connect(results.append)
    worker.dlog_raw_ready.connect(raw_results.append)
    worker.error.connect(errors.append)

    worker.run()

    assert errors == []
    assert raw_results == [[b"native-dlog"]]
    data = results[0]
    assert set(data) == {"A CH1 I", "B CH8 V", "B CH8 I"}
    assert data["B CH8 V"]["values"] == [3300.0]
    assert data["B CH8 I"]["values"] == [25.0]
