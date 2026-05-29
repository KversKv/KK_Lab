from __future__ import annotations

from instruments.mock.mock_instruments import (
    MockChamber,
    MockI2C,
    MockMSO64B,
    MockN6705C,
    MockPicoGPIO,
    MockUART,
)

from core.custom_test.adapters.base import (
    I2CAdapter,
    RuntimeInstrumentAdapter,
    UARTAdapter,
)


def create_mock_adapter(runtime_key: str) -> object | None:
    if runtime_key == "n6705c":
        return RuntimeInstrumentAdapter(MockN6705C())
    if runtime_key == "scope":
        return RuntimeInstrumentAdapter(MockMSO64B())
    if runtime_key == "chamber":
        chamber = MockChamber()
        chamber.connect()
        return RuntimeInstrumentAdapter(chamber)
    if runtime_key == "i2c":
        i2c = MockI2C()
        i2c.initialize()
        return I2CAdapter(i2c)
    if runtime_key == "uart":
        return UARTAdapter(MockUART())
    if runtime_key == "mcu_io":
        gpio = MockPicoGPIO()
        gpio.connect()
        return RuntimeInstrumentAdapter(gpio)
    return None
