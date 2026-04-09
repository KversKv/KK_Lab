from abc import abstractmethod
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
