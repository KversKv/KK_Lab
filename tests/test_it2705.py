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
