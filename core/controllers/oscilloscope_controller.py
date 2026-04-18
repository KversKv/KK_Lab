from instruments.scopes.keysight.dsox4034a import DSOX4034A
from instruments.scopes.tektronix.mso64b import MSO64B
from log_config import get_logger

logger = get_logger(__name__)


class OscilloscopeController:

    def __init__(self):
        self.instrument = None
        self.osc_type = None

    def connect(self, osc_type: str, resource: str):
        logger.debug("OscilloscopeController connect: type=%s, resource=%s", osc_type, resource)
        self.osc_type = osc_type
        if osc_type == "dsox4034a":
            self.instrument = DSOX4034A(resource)
        else:
            self.instrument = MSO64B(resource)
        idn = self.instrument.identify_instrument()
        logger.debug("OscilloscopeController connected: %s", idn)
        return idn

    def disconnect(self):
        logger.debug("OscilloscopeController disconnect")
        if self.instrument is not None:
            self.instrument.disconnect()
            self.instrument = None
            self.osc_type = None

    def is_connected(self) -> bool:
        return self.instrument is not None

    def measure(self, channel: int):
        if self.instrument is None:
            return {}

        logger.debug("OscilloscopeController measure: CH%d, osc_type=%s", channel, self.osc_type)
        results = {}
        try:
            results['PK2PK'] = self.instrument.get_channel_pk2pk(channel)
        except Exception:
            pass
        try:
            results['FREQUENCY'] = self.instrument.get_channel_frequency(channel)
        except Exception:
            pass

        if isinstance(self.instrument, DSOX4034A):
            try:
                results['VMAX'] = self.instrument.get_channel_max(channel)
            except Exception:
                pass
            try:
                results['VMIN'] = self.instrument.get_channel_min(channel)
            except Exception:
                pass
        else:
            try:
                results['MEAN'] = self.instrument.get_channel_mean(channel)
            except Exception:
                pass
            try:
                results['RMS'] = self.instrument._measure_immediate(channel, 'RMS')
            except Exception:
                pass

        return results

    def capture_screen(self, **kwargs) -> bytes:
        if self.instrument is None:
            return b''
        logger.debug("OscilloscopeController capture_screen: kwargs=%s", kwargs)
        return self.instrument.capture_screen_png(**kwargs)

    def apply_settings(self, settings: dict):
        if self.instrument is None:
            return

        logger.debug("OscilloscopeController apply_settings: %s", settings)

        if 'timebase' in settings:
            self.instrument.set_timebase_scale(settings['timebase'])

        for ch_settings in settings.get('channels', []):
            ch_num = ch_settings['channel']
            self.instrument.set_channel_display(ch_num, ch_settings['enabled'])
            if ch_settings['enabled']:
                self.instrument.set_channel_scale(ch_num, ch_settings['scale'])
                self.instrument.set_channel_offset(ch_num, ch_settings.get('offset', 0))
