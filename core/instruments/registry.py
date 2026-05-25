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


def _create_vt6002(spec: InstrumentSpec) -> object:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        from instruments.mock.mock_instruments import MockVT6002
        return MockVT6002()
    from instruments.factory import create_chamber
    return create_chamber(spec.resource)


def _verify_vt6002(instance: object) -> InstrumentIdentity:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return InstrumentIdentity(
            model="VT6002", serial="", vendor="Votsch",
        )
    if hasattr(instance, "get_current_temp"):
        temp = instance.get_current_temp()
        if temp is None:
            raise ConnectionError(
                "VT6002 verify failed: unable to read current temperature"
            )
    elif hasattr(instance, "ser") and instance.ser is not None:
        if not instance.ser.is_open:
            raise ConnectionError("VT6002 verify failed: serial port not open")
    else:
        raise ConnectionError("VT6002 verify failed: no valid interface found")
    return InstrumentIdentity(
        model="VT6002",
        serial="",
        vendor="Votsch",
    )


def _scan_vt6002() -> list[InstrumentCandidate]:
    from debug_config import DEBUG_MOCK
    if DEBUG_MOCK:
        return [
            InstrumentCandidate(
                instrument_type="vt6002",
                connection_kind="serial_modbus",
                resource="MOCK::VT6002",
                model_hint="VT6002",
                display_name="Mock VT6002",
            ),
        ]
    import serial.tools.list_ports
    candidates = []
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            candidates.append(InstrumentCandidate(
                instrument_type="vt6002",
                connection_kind="serial_modbus",
                resource=port.device,
                display_name=f"{port.device} - {port.description}",
            ))
    except Exception as e:
        logger.warning("VT6002 serial scan failed: %s", e)
    return candidates


def _disconnect_vt6002(instance: object) -> None:
    if hasattr(instance, "close"):
        try:
            instance.close()
        except Exception as e:
            logger.warning("VT6002 disconnect error: %s", e)


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


def create_default_registry() -> ProfileRegistry:
    registry = ProfileRegistry()
    registry.register(N6705C_PROFILE)
    registry.register(MSO64B_PROFILE)
    registry.register(DSOX4034A_PROFILE)
    registry.register(VT6002_PROFILE)
    registry.register(KEYSIGHT53230A_PROFILE)
    return registry
