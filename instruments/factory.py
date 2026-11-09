from instruments.scopes.keysight.dsox4034a import DSOX4034A
from instruments.scopes.tektronix.mso64b import MSO64B
from instruments.power.keysight.n6705c import N6705C
from instruments.power.itech.it2705 import IT2705
from instruments.chambers.mt3065 import MT3065
from instruments.chambers.vt6002_chamber import VT6002
from instruments.chambers.wt2040_chamber import WT2040
from instruments.frequencyCounter.keysight_53230A import Keysight53230A
from instruments.digitMultimeter.keysight.keysight_34461A import Keysight34461A
from instruments.MCU_IO.YD_RP2040 import PicoGPIO
from instruments.MCU_IO.ch9114f import CH9114F
from instruments.wirelessConnectivityTester.rohde_schwarz import CMW270, CMW500
from instruments.base.visa_instrument import VisaInstrument
from log_config import get_logger

logger = get_logger(__name__)


_INSTRUMENT_CREATORS = {
    "n6705c": lambda **kw: N6705C(kw["resource"]),
    "it2705": lambda **kw: IT2705(kw["resource"], visa_library=kw.get("visa_library")),
    "mso64b": lambda **kw: MSO64B(kw["resource"]),
    "dsox4034a": lambda **kw: DSOX4034A(kw["resource"]),
    "vt6002": lambda **kw: VT6002(kw.get("port", kw.get("resource", "")), kw.get("baudrate", 9600)),
    "mt3065": lambda **kw: MT3065(kw.get("port", kw.get("resource", "")), kw.get("baudrate", 19200)),
    "wt2040": lambda **kw: WT2040(
        kw.get("host") or kw.get("resource") or kw.get("port") or "",
        tcp_port=kw.get("tcp_port", WT2040.DEFAULT_PORT),
        timeout=kw.get("timeout", 5.0),
    ),
    "keysight53230a": lambda **kw: Keysight53230A(kw["resource"]),
    "keysight34461a": lambda **kw: Keysight34461A(kw["resource"]),
    "yd_rp2040": lambda **kw: PicoGPIO(
        kw.get("port", kw.get("resource", "")),
        kw.get("baudrate", kw.get("baud", 921600)),
        kw.get("timeout", 0.5),
    ),
    "ch9114f": lambda **kw: CH9114F(
        kw.get("port", kw.get("resource", "auto")),
    ),
    "cmw270": lambda **kw: CMW270(kw.get("resource") or kw.get("address")),
    "cmw500": lambda **kw: CMW500(kw.get("resource") or kw.get("address")),
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


def get_power_analyzer_idn(instance) -> str:
    """返回已识别或实时查询的电源 IDN。"""
    cached = str(getattr(instance, "_kk_lab_idn", "") or "").strip()
    if cached:
        return cached
    if hasattr(instance, "identify"):
        idn = str(instance.identify() or "").strip()
    elif hasattr(instance, "instr") and instance.instr is not None:
        idn = str(instance.instr.query("*IDN?") or "").strip()
    else:
        idn = ""
    if idn:
        instance._kk_lab_idn = idn
    return idn


def get_power_analyzer_model(instance) -> str:
    """从 IDN 第二段取得真实型号。"""
    parts = get_power_analyzer_idn(instance).split(",")
    if len(parts) > 1 and parts[1].strip():
        return parts[1].strip()
    return type(instance).__name__.removeprefix("Mock")


def _power_analyzer_type_from_idn(idn: str) -> str:
    upper = idn.upper()
    if "N6705" in upper:
        return "n6705c"
    if "IT2705" in upper:
        return "it2705"
    raise ValueError(f"Unsupported power analyzer IDN: {idn}")


def create_power_analyzer(
    resource: str,
    analyzer_type: str = "n6705c",
    visa_library=None,
):
    from debug_config import DEBUG_MOCK

    key = str(analyzer_type).strip().lower()
    logger.debug(
        "create_power_analyzer: type=%s, resource=%s", key, resource
    )
    if key == "auto":
        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockIT2705, MockN6705C
            if "IT2705" in str(resource).upper():
                instance = MockIT2705(resource or "MOCK::IT2705")
            else:
                instance = MockN6705C()
                instance._kk_lab_idn = "MOCK,N6705C,MOCK,1.0"
            return instance

        probe = N6705C(resource, visa_library=visa_library)
        instance = None
        try:
            idn = get_power_analyzer_idn(probe)
            detected_type = _power_analyzer_type_from_idn(idn)
            if detected_type == "n6705c":
                return probe
            probe.disconnect()
            instance = IT2705(resource, visa_library=visa_library)
            identified_idn = get_power_analyzer_idn(instance)
            if _power_analyzer_type_from_idn(identified_idn) != detected_type:
                raise ConnectionError(
                    f"Power analyzer identity changed during connection: {identified_idn}"
                )
            return instance
        except Exception:
            if instance is not None:
                instance.disconnect()
            probe.disconnect()
            raise
    if key == "n6705c":
        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C
            instance = MockN6705C()
            instance._kk_lab_idn = "MOCK,N6705C,MOCK,1.0"
            return instance
        return N6705C(resource, visa_library=visa_library)
    if key == "it2705":
        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockIT2705
            return MockIT2705(resource or "MOCK")
        return IT2705(resource, visa_library=visa_library)
    raise ValueError(f"Unknown power analyzer type: {analyzer_type}")


def create_audio_precision():
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockAudioPrecision
        return MockAudioPrecision()
    from instruments.audioPrecision.apx500_driver import APxConnection
    return APxConnection()


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
        host = port or resource
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


def create_digital_multimeter(dmm_type: str, resource: str):
    from debug_config import DEBUG_MOCK
    logger.debug("create_digital_multimeter: type=%s, resource=%s", dmm_type, resource)
    key = str(dmm_type).strip().lower()
    if key in ("34461a", "keysight_34461a", "keysight34461a"):
        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockKeysight34461A
            return MockKeysight34461A()
        return Keysight34461A(resource)
    else:
        raise ValueError(f"Unknown digital multimeter type: {dmm_type}")


def create_wireless_tester(tester_type: str = "cmw270", resource: str = ""):
    from debug_config import DEBUG_MOCK
    logger.debug("create_wireless_tester: type=%s, resource=%s", tester_type, resource)
    key = str(tester_type).strip().lower()
    addr = (resource or "").strip()
    if key in ("cmw270", "cmw-270"):
        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockCMW270
            return MockCMW270(addr)
        if not addr:
            raise ValueError("create_wireless_tester: resource 必填（地址禁硬编码，无默认地址）")
        return CMW270(addr)
    if key in ("cmw500", "cmw-500"):
        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockCMW500
            return MockCMW500(addr)
        if not addr:
            raise ValueError("create_wireless_tester: resource 必填（地址禁硬编码，无默认地址）")
        return CMW500(addr)
    raise ValueError(f"Unknown wireless tester type: {tester_type}")


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
