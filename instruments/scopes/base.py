from abc import abstractmethod
from typing import Optional, List, Dict, Any, Callable

from instruments.base.instrument_base import InstrumentBase


class OscilloscopeBase(InstrumentBase):

    @abstractmethod
    def identify_instrument(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_channel_pk2pk(self, channel: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_channel_frequency(self, channel: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_channel_mean(self, channel: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_channel_max(self, channel: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_channel_min(self, channel: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_channel_rms(self, channel: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def set_channel_display(self, channel: int, on: bool):
        raise NotImplementedError

    @abstractmethod
    def set_channel_scale(self, channel: int, volts_per_div: float):
        raise NotImplementedError

    @abstractmethod
    def set_channel_offset(self, channel: int, offset: float):
        raise NotImplementedError

    @abstractmethod
    def set_timebase_scale(self, seconds_per_div: float):
        raise NotImplementedError

    @abstractmethod
    def set_trigger_edge(self, source_channel: int, level: float, slope: str = 'POS'):
        raise NotImplementedError

    @abstractmethod
    def capture_screen_png(self, **kwargs) -> bytes:
        raise NotImplementedError


class OscilloscopeController:

    def __init__(self):
        self._instrument = None
        self._instrument_info: str = ""
        self._log_callback: Optional[Callable[[str], None]] = None

    @property
    def instrument(self):
        return self._instrument

    @property
    def instrument_info(self) -> str:
        return self._instrument_info

    @property
    def is_connected(self) -> bool:
        return self._instrument is not None

    def set_log_callback(self, callback: Callable[[str], None]):
        self._log_callback = callback

    def _log(self, message: str):
        if self._log_callback:
            self._log_callback(message)

    @staticmethod
    def _is_visa_resource(resource: str) -> bool:
        upper = resource.upper()
        return (
            upper.startswith("USB")
            or upper.startswith("GPIB")
            or upper.startswith("TCPIP")
        )

    def connect_instrument(self, resource: str) -> dict:
        from instruments.scopes.keysight.dsox4034a import DSOX4034A
        from instruments.scopes.tektronix.mso64b import MSO64B

        self._log(f"[SYSTEM] Connecting to {resource}...")

        if self._is_visa_resource(resource):
            self._instrument = DSOX4034A(resource)
        else:
            self._instrument = MSO64B(resource)

        info = self._instrument.identify_instrument()
        self._instrument_info = info
        self._log(f"[SYSTEM] Connected: {info}")

        return {
            "info": info,
            "title": info.split(",")[1].strip() if "," in info else info,
            "is_dsox": isinstance(self._instrument, DSOX4034A),
            "is_mso64b": isinstance(self._instrument, MSO64B),
        }

    def disconnect_instrument(self) -> dict:
        from instruments.scopes.tektronix.mso64b import MSO64B

        self._log("[SYSTEM] Disconnecting instrument...")
        is_mso64b = isinstance(self._instrument, MSO64B) if self._instrument else False

        if self._instrument:
            self._instrument.disconnect()
            self._instrument = None
            self._instrument_info = ""

        self._log("[SYSTEM] Disconnected.")
        return {"is_mso64b": is_mso64b}

    def measure_channel(self, channel: int) -> Dict[str, Any]:
        if not self._instrument:
            return {}

        self._log("[INFO] Starting measurements...")
        results = {}
        measure_types = [
            ('PK2PK', self._instrument.get_channel_pk2pk),
            ('FREQUENCY', self._instrument.get_channel_frequency),
            ('VMAX', self._instrument.get_channel_max),
            ('VMIN', self._instrument.get_channel_min),
        ]

        for mtype, func in measure_types:
            try:
                result = func(channel)
                results[mtype] = result
                self._log(f"[MEASURE] CH{channel} {mtype}: {result}")
            except Exception as e:
                self._log(f"[ERROR] CH{channel} {mtype} failed: {e}")

        self._log("[INFO] Measurements complete.")
        return results

    def capture_screen(self, invert: bool = False) -> Optional[bytes]:
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return None

        mode_text = "inverted background" if invert else "original color"
        self._log(f"[INFO] Capturing screenshot ({mode_text})...")
        png_data = self._instrument.capture_screen_png(invert=invert)

        if png_data:
            self._log("[INFO] Screenshot captured successfully.")
        else:
            self._log("[WARN] No image data received.")
        return png_data

    def apply_settings(
        self,
        timebase_seconds: float,
        channel_settings: List[Dict[str, Any]],
        trigger_settings: Dict[str, Any],
        num_channels: int = 4,
    ):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return

        self._log("[INFO] Applying settings to instrument...")

        try:
            self._instrument.set_timebase_scale(timebase_seconds)
            self._log(f"[SETTING] Timebase: {timebase_seconds} s/div")
        except Exception as e:
            self._log(f"[ERROR] Timebase setting failed: {e}")

        for ch_num in range(1, num_channels + 1):
            try:
                settings = channel_settings[ch_num - 1] if ch_num - 1 < len(channel_settings) else None
                if settings is None:
                    continue

                self._instrument.set_channel_display(ch_num, settings['enabled'])

                if settings['enabled']:
                    self._instrument.set_channel_scale(ch_num, settings['scale'])
                    self._instrument.set_channel_offset(ch_num, settings['offset'])

                    coupling = settings.get('coupling')
                    if coupling and hasattr(self._instrument, 'set_channel_coupling'):
                        self._instrument.set_channel_coupling(ch_num, coupling)

                self._log(
                    f"[SETTING] CH{ch_num}: {'ON' if settings['enabled'] else 'OFF'}, "
                    f"Scale={settings['scale']} V/div, Offset={settings['offset']} V"
                    f"{', Coupling=' + settings.get('coupling', '') if settings.get('coupling') else ''}"
                )
            except Exception as e:
                self._log(f"[ERROR] CH{ch_num} setting failed: {e}")

        try:
            source_text = trigger_settings['source']
            trigger_level = trigger_settings['level']
            slope = trigger_settings['slope']

            if source_text.startswith("CH"):
                trigger_ch = int(source_text[2:])
                self._instrument.set_trigger_edge(trigger_ch, trigger_level, slope)
                self._log(
                    f"[SETTING] Trigger: CH{trigger_ch}, Level={trigger_level} V, Slope={slope}"
                )
        except Exception as e:
            self._log(f"[ERROR] Trigger setting failed: {e}")

        self._log("[INFO] All settings applied successfully.")

    def apply_timebase_only(self, timebase_seconds: float):
        if not self._instrument:
            self._log("[WARN] Instrument not connected.")
            return

        try:
            self._instrument.set_timebase_scale(timebase_seconds)
            self._log(f"[SETTING] Timebase: {timebase_seconds} s/div")
        except Exception as e:
            self._log(f"[ERROR] Timebase setting failed: {e}")

    def search_visa_devices(self, log_callback: Optional[Callable[[str], None]] = None) -> List[str]:
        log = log_callback or self._log
        log("[SYSTEM] Scanning VISA / network resources...")

        import pyvisa
        rm = None
        try:
            try:
                rm = pyvisa.ResourceManager()
            except Exception:
                rm = pyvisa.ResourceManager('@ni')

            available = list(rm.list_resources()) or []

            scope_devices = []
            for dev in available:
                try:
                    instr = rm.open_resource(dev, timeout=2000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    scope_devices.append(dev)
                    log(f"[SCAN] {dev} → {idn}")
                except Exception:
                    pass

            if scope_devices:
                log(f"[SYSTEM] Found {len(scope_devices)} VISA device(s).")
            else:
                log("[SYSTEM] No VISA instrument found.")

            return scope_devices
        except Exception as e:
            log(f"[ERROR] Search failed: {str(e)}")
            return []
        finally:
            if rm:
                try:
                    rm.close()
                except Exception:
                    pass
