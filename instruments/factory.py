from instruments.scopes.keysight.dsox4034a import DSOX4034A
from instruments.scopes.tektronix.mso64b import MSO64B
from instruments.power.keysight.n6705c import N6705C
from instruments.chambers.mt3065 import MT3065
from instruments.chambers.vt6002_chamber import VT6002
from instruments.chambers.wt2040_chamber import WT2040
from instruments.frequencyCounter.keysight_53230A import Keysight53230A
from instruments.MCU_IO.YD_RP2040 import PicoGPIO
from instruments.MCU_IO.ch9114f import CH9114F
from instruments.base.visa_instrument import VisaInstrument
from log_config import get_logger

logger = get_logger(__name__)


_INSTRUMENT_CREATORS = {
    "n6705c": lambda **kw: N6705C(kw["resource"]),
    "mso64b": lambda **kw: MSO64B(kw["resource"]),
    "dsox4034a": lambda **kw: DSOX4034A(kw["resource"]),
    "vt6002": lambda **kw: VT6002(kw.get("port", kw.get("resource", "")), kw.get("baudrate", 9600)),
    "mt3065": lambda **kw: MT3065(kw.get("port", kw.get("resource", "")), kw.get("baudrate", 19200)),
    "wt2040": lambda **kw: WT2040(
        kw.get("host") or kw.get("resource") or kw.get("port") or WT2040.DEFAULT_HOST,
        tcp_port=kw.get("tcp_port", WT2040.DEFAULT_PORT),
        timeout=kw.get("timeout", 5.0),
    ),
    "keysight53230a": lambda **kw: Keysight53230A(kw["resource"]),
    "yd_rp2040": lambda **kw: PicoGPIO(
        kw.get("port", kw.get("resource", "")),
        kw.get("baudrate", kw.get("baud", 921600)),
        kw.get("timeout", 0.5),
    ),
    "ch9114f": lambda **kw: CH9114F(
        kw.get("port", kw.get("resource", "auto")),
    ),
}


def create_instrument(instrument_type: str, **kwargs):
    logger.debug("create_instrument: type=%s, kwargs=%s", instrument_type, kwargs)
    key = str(instrument_type).strip().lower()
    creator = _INSTRUMENT_CREATORS.get(key)
    if creator is None:
        raise ValueError(f"Unknown instrument type: {instrument_type}")
    return creator(**kwargs)


def create_oscilloscope(osc_type: str, resource: str):
    logger.debug("create_oscilloscope: type=%s, resource=%s", osc_type, resource)
    if osc_type == "dsox4034a":
        return DSOX4034A(resource)
    elif osc_type == "mso64b":
        return MSO64B(resource)
    else:
        raise ValueError(f"Unknown oscilloscope type: {osc_type}")


def create_power_analyzer(resource: str):
    logger.debug("create_power_analyzer: resource=%s", resource)
    return N6705C(resource)


def create_chamber(chamber_type: str = "vt6002", port: str = "", baudrate: int | None = None, resource: str = ""):
    from debug_config import DEBUG_MOCK
    port = port or resource
    key = str(chamber_type).strip().lower()
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockMT3065, MockVT6002, MockWT2040
        if key == "wt2040":
            return MockWT2040()
        if key == "mt3065":
            return MockMT3065()
        return MockVT6002()
    if key == "wt2040":
        host = port or resource or WT2040.DEFAULT_HOST
        logger.debug("create_chamber: type=%s, host=%s", key, host)
        return create_instrument(key, host=host, resource=host)
    default_baudrate = 19200 if key == "mt3065" else 9600
    baudrate = default_baudrate if baudrate is None else baudrate
    logger.debug("create_chamber: type=%s, port=%s, baudrate=%d", key, port, baudrate)
    return create_instrument(key, port=port, resource=port, baudrate=baudrate)


def create_frequency_counter(counter_type: str, resource: str):
    logger.debug("create_frequency_counter: type=%s, resource=%s", counter_type, resource)
    key = str(counter_type).strip().lower()
    if key in ("53230a", "keysight_53230a", "keysight53230a"):
        return Keysight53230A(resource)
    else:
        raise ValueError(f"Unknown frequency counter type: {counter_type}")


def create_mcu_io(mcu_type: str = "yd_rp2040", port: str = "", baudrate: int = 921600):
    from debug_config import DEBUG_MOCK
    key = str(mcu_type).strip().lower()
    if key in ("ch9114f", "ch9114"):
        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockCH9114F
            return MockCH9114F(port=port or "MOCK")
        return create_instrument("ch9114f", port=port or "auto")
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockPicoGPIO
        return MockPicoGPIO(port=port, baudrate=baudrate)
    if key in ("yd_rp2040", "rp2040", "pico", "picogpio"):
        return create_instrument("yd_rp2040", port=port, baudrate=baudrate)
    raise ValueError(f"Unknown MCU IO type: {mcu_type}")
