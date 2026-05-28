from abc import abstractmethod

from instruments.base.instrument_base import InstrumentBase


class ChamberBase(InstrumentBase):
    """Abstract interface implemented by every temperature chamber driver."""

    @abstractmethod
    def connect(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        raise NotImplementedError

    def close(self):
        self.disconnect()

    @abstractmethod
    def is_connected(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def identify(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_temperature(self, temp_celsius: float):
        raise NotImplementedError

    @abstractmethod
    def get_current_temp(self):
        raise NotImplementedError

    @abstractmethod
    def get_set_temp(self):
        raise NotImplementedError

    @abstractmethod
    def start(self):
        raise NotImplementedError

    @abstractmethod
    def stop(self):
        raise NotImplementedError
