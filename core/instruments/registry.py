from __future__ import annotations

from core.instruments.profiles import InstrumentProfile
from core.instruments.instrument_session import (
    InstrumentCandidate,
    InstrumentIdentity,
    InstrumentSpec,
)
from log_config import get_logger

logger = get_logger(__name__)


class ProfileRegistry:
    def __init__(self):
        self._profiles: dict[str, InstrumentProfile] = {}

    def register(self, profile: InstrumentProfile) -> None:
        self._profiles[profile.instrument_type] = profile
        logger.debug("Registered instrument profile: %s", profile.instrument_type)

    def get(self, instrument_type: str) -> InstrumentProfile | None:
        return self._profiles.get(instrument_type)

    def all_profiles(self) -> list[InstrumentProfile]:
        return list(self._profiles.values())

    def types(self) -> list[str]:
        return list(self._profiles.keys())

    def find_by_role(self, role: str) -> list[InstrumentProfile]:
        return [p for p in self._profiles.values() if p.role == role]

    def find_by_capability(self, capability: str) -> list[InstrumentProfile]:
        return [p for p in self._profiles.values() if capability in p.capabilities]


def _create_n6705c(spec: InstrumentSpec) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockN6705C
        return MockN6705C()
    from instruments.factory import create_power_analyzer
    return create_power_analyzer(spec.resource)


def _verify_n6705c(instance: object) -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model="N6705C", serial="MOCK", vendor="Keysight", firmware="MOCK",
        )
    idn = ""
    if hasattr(instance, "instr") and instance.instr is not None:
        idn = instance.instr.query("*IDN?").strip()
    if not idn:
        raise ConnectionError("N6705C verify failed: unable to query *IDN?")
    upper_idn = idn.upper()
    if "N6705C" not in upper_idn and "N6705" not in upper_idn:
        raise ConnectionError(
            f"N6705C verify failed: IDN does not match expected device. Got: {idn}"
        )
    parts = idn.split(",")
    return InstrumentIdentity(
        model=parts[1].strip() if len(parts) > 1 else "N6705C",
        serial=parts[2].strip() if len(parts) > 2 else "",
        vendor=parts[0].strip() if len(parts) > 0 else "Keysight",
        firmware=parts[3].strip() if len(parts) > 3 else "",
    )


def _scan_n6705c() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="n6705c",
                connection_kind="visa",
                resource="MOCK::N6705C::A",
                model_hint="N6705C",
                serial_hint="MOCK-A",
                display_name="Mock N6705C A",
            ),
            InstrumentCandidate(
                instrument_type="n6705c",
                connection_kind="visa",
                resource="MOCK::N6705C::B",
                model_hint="N6705C",
                serial_hint="MOCK-B",
                display_name="Mock N6705C B",
            ),
        ]
    import pyvisa
    candidates = []
    rm = None
    try:
        rm = pyvisa.ResourceManager()
        resources = list(rm.list_resources()) or []
        for dev in resources:
            instr = None
            try:
                instr = rm.open_resource(dev, timeout=2000)
                idn = instr.query("*IDN?").strip()
                if "N6705C" in idn.upper():
                    parts = idn.split(",")
                    candidates.append(InstrumentCandidate(
                        instrument_type="n6705c",
                        connection_kind="visa",
                        resource=dev,
                        model_hint=parts[1].strip() if len(parts) > 1 else "",
                        serial_hint=parts[2].strip() if len(parts) > 2 else "",
                        display_name=idn,
                    ))
            except Exception:
                pass
            finally:
                if instr is not None:
                    try:
                        instr.close()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning("N6705C scan failed: %s", e)
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass
    return candidates


def _disconnect_n6705c(instance: object) -> None:
    if hasattr(instance, "disconnect"):
        try:
            instance.disconnect()
        except Exception as e:
            logger.warning("N6705C disconnect error: %s", e)


def _create_mso64b(spec: InstrumentSpec) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockMSO64B
        return MockMSO64B()
    from instruments.factory import create_oscilloscope
    return create_oscilloscope("mso64b", spec.resource)


def _verify_mso64b(instance: object) -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model="MSO64B", serial="MOCK000", vendor="Tektronix", firmware="MOCK",
        )
    idn = ""
    if hasattr(instance, "identify_instrument"):
        idn = instance.identify_instrument()
    elif hasattr(instance, "instrument") and instance.instrument is not None:
        idn = instance.instrument.query("*IDN?").strip()
    if not idn:
        raise ConnectionError("MSO64B verify failed: unable to query identity")
    upper_idn = idn.upper()
    if "MSO64B" not in upper_idn and "MSO6" not in upper_idn:
        raise ConnectionError(
            f"MSO64B verify failed: IDN does not match expected device. Got: {idn}"
        )
    parts = idn.split(",")
    return InstrumentIdentity(
        model=parts[1].strip() if len(parts) > 1 else "MSO64B",
        serial=parts[2].strip() if len(parts) > 2 else "",
        vendor=parts[0].strip() if len(parts) > 0 else "Tektronix",
        firmware=parts[3].strip() if len(parts) > 3 else "",
    )


def _scan_mso64b() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="mso64b",
                connection_kind="visa",
                resource="MOCK::MSO64B",
                model_hint="MSO64B",
                serial_hint="MOCK000",
                display_name="Mock MSO64B",
            ),
        ]
    import pyvisa
    candidates = []
    rm = None
    try:
        rm = pyvisa.ResourceManager()
        resources = list(rm.list_resources()) or []
        for dev in resources:
            instr = None
            try:
                instr = rm.open_resource(dev, timeout=2000)
                idn = instr.query("*IDN?").strip()
                if "MSO64B" in idn.upper() or "MSO6" in idn.upper():
                    parts = idn.split(",")
                    candidates.append(InstrumentCandidate(
                        instrument_type="mso64b",
                        connection_kind="visa",
                        resource=dev,
                        model_hint=parts[1].strip() if len(parts) > 1 else "",
                        serial_hint=parts[2].strip() if len(parts) > 2 else "",
                        display_name=idn,
                    ))
            except Exception:
                pass
            finally:
                if instr is not None:
                    try:
                        instr.close()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning("MSO64B scan failed: %s", e)
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass
    return candidates


def _disconnect_mso64b(instance: object) -> None:
    if hasattr(instance, "disconnect"):
        try:
            instance.disconnect()
        except Exception as e:
            logger.warning("MSO64B disconnect error: %s", e)


def _create_dsox4034a(spec: InstrumentSpec) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockMSO64B
        return MockMSO64B()
    from instruments.factory import create_oscilloscope
    return create_oscilloscope("dsox4034a", spec.resource)


def _verify_dsox4034a(instance: object) -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model="DSOX4034A", serial="MOCK000", vendor="Keysight", firmware="MOCK",
        )
    idn = ""
    if hasattr(instance, "identify_instrument"):
        idn = instance.identify_instrument()
    elif hasattr(instance, "instrument") and instance.instrument is not None:
        idn = instance.instrument.query("*IDN?").strip()
    if not idn:
        raise ConnectionError("DSOX4034A verify failed: unable to query identity")
    upper_idn = idn.upper()
    if "DSOX4034A" not in upper_idn and "DSO-X 4034A" not in upper_idn.replace(" ", " "):
        raise ConnectionError(
            f"DSOX4034A verify failed: IDN does not match expected device. Got: {idn}"
        )
    parts = idn.split(",")
    return InstrumentIdentity(
        model=parts[1].strip() if len(parts) > 1 else "DSOX4034A",
        serial=parts[2].strip() if len(parts) > 2 else "",
        vendor=parts[0].strip() if len(parts) > 0 else "Keysight",
        firmware=parts[3].strip() if len(parts) > 3 else "",
    )


def _scan_dsox4034a() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="dsox4034a",
                connection_kind="visa",
                resource="MOCK::DSOX4034A",
                model_hint="DSOX4034A",
                serial_hint="MOCK000",
                display_name="Mock DSOX4034A",
            ),
        ]
    import pyvisa
    candidates = []
    rm = None
    try:
        rm = pyvisa.ResourceManager()
        resources = list(rm.list_resources()) or []
        for dev in resources:
            instr = None
            try:
                instr = rm.open_resource(dev, timeout=2000)
                idn = instr.query("*IDN?").strip()
                if "DSOX4034A" in idn.upper() or "DSO-X 4034A" in idn.upper():
                    parts = idn.split(",")
                    candidates.append(InstrumentCandidate(
                        instrument_type="dsox4034a",
                        connection_kind="visa",
                        resource=dev,
                        model_hint=parts[1].strip() if len(parts) > 1 else "",
                        serial_hint=parts[2].strip() if len(parts) > 2 else "",
                        display_name=idn,
                    ))
            except Exception:
                pass
            finally:
                if instr is not None:
                    try:
                        instr.close()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning("DSOX4034A scan failed: %s", e)
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass
    return candidates


def _disconnect_dsox4034a(instance: object) -> None:
    _disconnect_mso64b(instance)


def _create_chamber(spec: InstrumentSpec, chamber_type: str, mock_class_name: str) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from instruments import mock as mock_module
        return getattr(mock_module, mock_class_name)()
    from instruments.factory import create_chamber
    return create_chamber(chamber_type=chamber_type, port=spec.resource)


def _verify_chamber(instance: object, model: str, vendor: str = "") -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model=model, serial="", vendor=vendor,
        )
    if hasattr(instance, "get_current_temp"):
        temp = instance.get_current_temp()
        if temp is None:
            raise ConnectionError(
                f"{model} verify failed: unable to read current temperature"
            )
    elif hasattr(instance, "ser") and instance.ser is not None:
        if not instance.ser.is_open:
            raise ConnectionError(f"{model} verify failed: serial port not open")
    else:
        raise ConnectionError(f"{model} verify failed: no valid interface found")
    for method_name in ("is_running", "isRunning"):
        method = getattr(instance, method_name, None)
        if callable(method):
            try:
                setattr(instance, "_last_known_running_state", bool(method()))
                setattr(instance, "_last_known_running_state_verified", True)
            except Exception as e:
                logger.warning("%s running state check failed: %s", model, e, exc_info=True)
            break
    return InstrumentIdentity(
        model=model,
        serial="",
        vendor=vendor,
    )


def _scan_serial_chamber(instrument_type: str, model: str, connection_kind: str) -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type=instrument_type,
                connection_kind=connection_kind,
                resource=f"MOCK::{model}",
                model_hint=model,
                display_name=f"Mock {model}",
            ),
        ]
    import serial.tools.list_ports
    candidates = []
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            candidates.append(InstrumentCandidate(
                instrument_type=instrument_type,
                connection_kind=connection_kind,
                resource=port.device,
                model_hint=model,
                display_name=f"{port.device} - {port.description}",
            ))
    except Exception as e:
        logger.warning("%s serial scan failed: %s", model, e)
    return candidates


def _disconnect_chamber(instance: object, model: str) -> None:
    if hasattr(instance, "close"):
        try:
            instance.close()
        except Exception as e:
            logger.warning("%s disconnect error: %s", model, e)


def _create_vt6002(spec: InstrumentSpec) -> object:
    return _create_chamber(spec, "vt6002", "MockVT6002")


def _verify_vt6002(instance: object) -> InstrumentIdentity:
    return _verify_chamber(instance, "VT6002", "Votsch")


def _scan_vt6002() -> list[InstrumentCandidate]:
    return _scan_serial_chamber("vt6002", "VT6002", "serial_modbus")


def _disconnect_vt6002(instance: object) -> None:
    _disconnect_chamber(instance, "VT6002")


def _create_mt3065(spec: InstrumentSpec) -> object:
    return _create_chamber(spec, "mt3065", "MockMT3065")


def _verify_mt3065(instance: object) -> InstrumentIdentity:
    return _verify_chamber(instance, "MT3065")


def _scan_mt3065() -> list[InstrumentCandidate]:
    return _scan_serial_chamber("mt3065", "MT3065", "serial_ascii")


def _disconnect_mt3065(instance: object) -> None:
    _disconnect_chamber(instance, "MT3065")


def _create_wt2040(spec: InstrumentSpec) -> object:
    return _create_chamber(spec, "wt2040", "MockWT2040")


def _verify_wt2040(instance: object) -> InstrumentIdentity:
    return _verify_chamber(instance, "WT2040")


def _scan_wt2040() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="wt2040",
                connection_kind="tcp_hmi",
                resource="MOCK::WT2040",
                model_hint="WT2040",
                display_name="Mock WT2040",
            ),
        ]
    from instruments.chambers.wt2040_chamber import WT2040
    return [
        InstrumentCandidate(
            instrument_type="wt2040",
            connection_kind="tcp_hmi",
            resource=WT2040.DEFAULT_HOST,
            model_hint="WT2040",
            display_name=f"WT2040 - {WT2040.DEFAULT_HOST}",
        ),
    ]


def _disconnect_wt2040(instance: object) -> None:
    _disconnect_chamber(instance, "WT2040")


def _create_keysight53230a(spec: InstrumentSpec) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockKeysight53230A
        return MockKeysight53230A()
    from instruments.factory import create_frequency_counter
    return create_frequency_counter("keysight53230a", spec.resource)


def _verify_keysight53230a(instance: object) -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model="53230A", serial="MOCK000", vendor="Keysight", firmware="MOCK",
        )
    idn = ""
    if hasattr(instance, "identify"):
        idn = instance.identify()
    elif hasattr(instance, "identify_instrument"):
        idn = instance.identify_instrument()
    if not idn:
        raise ConnectionError("53230A verify failed: unable to query identity")
    if "53230" not in idn:
        raise ConnectionError(
            f"53230A verify failed: IDN does not match expected device. Got: {idn}"
        )
    parts = idn.split(",")
    return InstrumentIdentity(
        model=parts[1].strip() if len(parts) > 1 else "53230A",
        serial=parts[2].strip() if len(parts) > 2 else "",
        vendor=parts[0].strip() if len(parts) > 0 else "Keysight",
        firmware=parts[3].strip() if len(parts) > 3 else "",
    )


def _scan_keysight53230a() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="keysight53230a",
                connection_kind="visa",
                resource="MOCK::53230A",
                model_hint="53230A",
                serial_hint="MOCK000",
                display_name="Mock Keysight 53230A",
            ),
        ]
    import pyvisa
    candidates = []
    rm = None
    try:
        rm = pyvisa.ResourceManager()
        resources = list(rm.list_resources()) or []
        for dev in resources:
            instr = None
            try:
                instr = rm.open_resource(dev, timeout=2000)
                idn = instr.query("*IDN?").strip()
                if "53230" in idn:
                    parts = idn.split(",")
                    candidates.append(InstrumentCandidate(
                        instrument_type="keysight53230a",
                        connection_kind="visa",
                        resource=dev,
                        model_hint=parts[1].strip() if len(parts) > 1 else "",
                        serial_hint=parts[2].strip() if len(parts) > 2 else "",
                        display_name=idn,
                    ))
            except Exception:
                pass
            finally:
                if instr is not None:
                    try:
                        instr.close()
                    except Exception:
                        pass
    except Exception as e:
        logger.warning("53230A scan failed: %s", e)
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass
    return candidates


def _disconnect_keysight53230a(instance: object) -> None:
    if hasattr(instance, "disconnect"):
        try:
            instance.disconnect()
        except Exception as e:
            logger.warning("53230A disconnect error: %s", e)
    elif hasattr(instance, "close"):
        try:
            instance.close()
        except Exception as e:
            logger.warning("53230A close error: %s", e)


def _create_mcu_io(spec: InstrumentSpec) -> object:
    from instruments.factory import create_mcu_io
    inst = create_mcu_io("yd_rp2040", port=spec.resource, baudrate=921600)
    if hasattr(inst, "connect"):
        ok = inst.connect()
        if ok is False:
            raise ConnectionError(f"MCU_IO connect failed: {spec.resource}")
    return inst


def _verify_mcu_io(instance: object) -> InstrumentIdentity:
    if hasattr(instance, "is_connected") and not instance.is_connected():
        raise ConnectionError("MCU_IO verify failed: device is not connected")
    model = "YD_RP2040"
    if hasattr(instance, "identify"):
        text = instance.identify()
        if text:
            model = text
    serial = getattr(instance, "port", "")
    return InstrumentIdentity(
        model=model,
        serial=serial,
        vendor="YD",
    )


def _scan_mcu_io() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="mcu_io",
                connection_kind="serial_raw_repl",
                resource="MOCK::YD_RP2040",
                model_hint="YD_RP2040",
                serial_hint="MOCK",
                display_name="Mock YD RP2040 GPIO",
            ),
        ]
    import serial.tools.list_ports
    candidates = []
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            candidates.append(InstrumentCandidate(
                instrument_type="mcu_io",
                connection_kind="serial_raw_repl",
                resource=port.device,
                model_hint="YD_RP2040",
                serial_hint=getattr(port, "serial_number", "") or "",
                display_name=f"{port.device} - {port.description}",
            ))
    except Exception as e:
        logger.warning("MCU_IO serial scan failed: %s", e)
    return candidates


def _disconnect_mcu_io(instance: object) -> None:
    if hasattr(instance, "disconnect"):
        try:
            instance.disconnect()
        except Exception as e:
            logger.warning("MCU_IO disconnect error: %s", e)
    elif hasattr(instance, "close"):
        try:
            instance.close()
        except Exception as e:
            logger.warning("MCU_IO close error: %s", e)


N6705C_PROFILE = InstrumentProfile(
    instrument_type="n6705c",
    display_name="Keysight N6705C DC Power Analyzer",
    connection_kind="visa",
    role="power_analyzer",
    capabilities=frozenset({
        "set_voltage", "measure_current", "measure_voltage",
        "datalog", "multi_channel_output", "set_current_limit",
    }),
    create=_create_n6705c,
    verify=_verify_n6705c,
    scan=_scan_n6705c,
    disconnect=_disconnect_n6705c,
    default_slot="A",
)

MSO64B_PROFILE = InstrumentProfile(
    instrument_type="mso64b",
    display_name="Tektronix MSO64B Oscilloscope",
    connection_kind="visa",
    role="scope",
    capabilities=frozenset({
        "capture_screen", "measure_waveform", "auto_detect_channels",
        "measure_frequency", "dvm_frequency",
    }),
    create=_create_mso64b,
    verify=_verify_mso64b,
    scan=_scan_mso64b,
    disconnect=_disconnect_mso64b,
    default_slot="main_scope",
)

DSOX4034A_PROFILE = InstrumentProfile(
    instrument_type="dsox4034a",
    display_name="Keysight DSOX4034A Oscilloscope",
    connection_kind="visa",
    role="scope",
    capabilities=frozenset({
        "capture_screen", "measure_waveform",
    }),
    create=_create_dsox4034a,
    verify=_verify_dsox4034a,
    scan=_scan_dsox4034a,
    disconnect=_disconnect_dsox4034a,
    default_slot="main_scope",
)

VT6002_PROFILE = InstrumentProfile(
    instrument_type="vt6002",
    display_name="VT6002 Temperature Chamber",
    connection_kind="serial_modbus",
    role="chamber",
    capabilities=frozenset({
        "set_temperature", "read_temperature", "stabilize_wait",
    }),
    create=_create_vt6002,
    verify=_verify_vt6002,
    scan=_scan_vt6002,
    disconnect=_disconnect_vt6002,
    default_slot="chamber",
)

MT3065_PROFILE = InstrumentProfile(
    instrument_type="mt3065",
    display_name="MT3065 Temperature Chamber",
    connection_kind="serial_ascii",
    role="chamber",
    capabilities=frozenset({
        "set_temperature", "read_temperature", "stabilize_wait",
    }),
    create=_create_mt3065,
    verify=_verify_mt3065,
    scan=_scan_mt3065,
    disconnect=_disconnect_mt3065,
    default_slot="chamber",
)

WT2040_PROFILE = InstrumentProfile(
    instrument_type="wt2040",
    display_name="WT2040 Temperature Chamber",
    connection_kind="tcp_hmi",
    role="chamber",
    capabilities=frozenset({
        "set_temperature", "read_temperature", "stabilize_wait",
    }),
    create=_create_wt2040,
    verify=_verify_wt2040,
    scan=_scan_wt2040,
    disconnect=_disconnect_wt2040,
    default_slot="chamber",
)

KEYSIGHT53230A_PROFILE = InstrumentProfile(
    instrument_type="keysight53230a",
    display_name="Keysight 53230A Frequency Counter",
    connection_kind="visa",
    role="counter",
    capabilities=frozenset({
        "measure_frequency", "measure_period",
    }),
    create=_create_keysight53230a,
    verify=_verify_keysight53230a,
    scan=_scan_keysight53230a,
    disconnect=_disconnect_keysight53230a,
    default_slot="counter",
)

MCU_IO_PROFILE = InstrumentProfile(
    instrument_type="mcu_io",
    display_name="YD RP2040 MCU IO",
    connection_kind="serial_raw_repl",
    role="mcu_io",
    capabilities=frozenset({
        "gpio_out", "gpio_input", "gpio_read", "gpio_pulse",
    }),
    create=_create_mcu_io,
    verify=_verify_mcu_io,
    scan=_scan_mcu_io,
    disconnect=_disconnect_mcu_io,
    default_slot="default",
)


def _create_serial_port(spec: InstrumentSpec) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from unittest.mock import MagicMock
        mock_ser = MagicMock()
        mock_ser.is_open = True
        mock_ser.port = spec.resource
        return mock_ser
    import serial
    return serial.Serial(spec.resource, baudrate=115200, timeout=1)


def _verify_serial_port(instance: object) -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model="SerialPort", serial="", vendor="Generic",
        )
    if hasattr(instance, "is_open") and instance.is_open:
        port = getattr(instance, "port", "unknown")
        return InstrumentIdentity(
            model="SerialPort", serial=port, vendor="Generic",
        )
    raise ConnectionError("Serial port verify failed: port not open")


def _scan_serial_port() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="serial_port",
                connection_kind="serial",
                resource="MOCK::COM1",
                display_name="Mock Serial Port",
            ),
        ]
    import serial.tools.list_ports
    candidates = []
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            candidates.append(InstrumentCandidate(
                instrument_type="serial_port",
                connection_kind="serial",
                resource=port.device,
                display_name=f"{port.device} - {port.description}",
            ))
    except Exception as e:
        logger.warning("Serial port scan failed: %s", e)
    return candidates


def _disconnect_serial_port(instance: object) -> None:
    if hasattr(instance, "close"):
        try:
            instance.close()
        except Exception as e:
            logger.warning("Serial port disconnect error: %s", e)


def _create_bes_usb_i2c(spec: InstrumentSpec) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from unittest.mock import MagicMock
        mock_adapter = MagicMock()
        mock_adapter.is_connected = True
        mock_adapter.adapter_id = "MOCK_I2C"
        return mock_adapter
    try:
        from instruments.i2c.bes_usb_i2c import BesUsbI2C
        adapter = BesUsbI2C()
        adapter.open()
        return adapter
    except ImportError:
        raise ConnectionError(
            "BES USB-I2C driver not available: DLL or module missing"
        )


def _verify_bes_usb_i2c(instance: object) -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model="BES_USB_I2C", serial="MOCK", vendor="BES",
        )
    if hasattr(instance, "is_connected") and instance.is_connected:
        adapter_id = getattr(instance, "adapter_id", "unknown")
        return InstrumentIdentity(
            model="BES_USB_I2C", serial=adapter_id, vendor="BES",
        )
    raise ConnectionError("BES USB-I2C verify failed: adapter not connected")


def _scan_bes_usb_i2c() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="bes_usb_i2c",
                connection_kind="usb",
                resource="MOCK::BES_I2C",
                display_name="Mock BES USB-I2C Adapter",
            ),
        ]
    try:
        from instruments.i2c.bes_usb_i2c import BesUsbI2C
        candidates = []
        adapters = BesUsbI2C.enumerate_adapters()
        for adapter_info in adapters:
            candidates.append(InstrumentCandidate(
                instrument_type="bes_usb_i2c",
                connection_kind="usb",
                resource=adapter_info.get("id", ""),
                display_name=adapter_info.get("name", "BES USB-I2C"),
            ))
        return candidates
    except ImportError:
        logger.warning("BES USB-I2C DLL not available for scan")
        return []
    except Exception as e:
        logger.warning("BES USB-I2C scan failed: %s", e)
        return []


def _disconnect_bes_usb_i2c(instance: object) -> None:
    if hasattr(instance, "close"):
        try:
            instance.close()
        except Exception as e:
            logger.warning("BES USB-I2C disconnect error: %s", e)


SERIAL_PORT_PROFILE = InstrumentProfile(
    instrument_type="serial_port",
    display_name="Serial Port (Generic)",
    connection_kind="serial",
    role="serial",
    capabilities=frozenset({
        "serial_tx", "serial_rx",
    }),
    create=_create_serial_port,
    verify=_verify_serial_port,
    scan=_scan_serial_port,
    disconnect=_disconnect_serial_port,
    default_slot="default",
)

BES_USB_I2C_PROFILE = InstrumentProfile(
    instrument_type="bes_usb_i2c",
    display_name="BES USB-I2C Adapter",
    connection_kind="usb",
    role="i2c_adapter",
    capabilities=frozenset({
        "i2c_read", "i2c_write", "efuse_read", "efuse_write",
    }),
    create=_create_bes_usb_i2c,
    verify=_verify_bes_usb_i2c,
    scan=_scan_bes_usb_i2c,
    disconnect=_disconnect_bes_usb_i2c,
    default_slot="default",
)


def create_default_registry() -> ProfileRegistry:
    registry = ProfileRegistry()
    registry.register(N6705C_PROFILE)
    registry.register(MSO64B_PROFILE)
    registry.register(DSOX4034A_PROFILE)
    registry.register(VT6002_PROFILE)
    registry.register(MT3065_PROFILE)
    registry.register(WT2040_PROFILE)
    registry.register(KEYSIGHT53230A_PROFILE)
    registry.register(MCU_IO_PROFILE)
    registry.register(SERIAL_PORT_PROFILE)
    registry.register(BES_USB_I2C_PROFILE)
    return registry
