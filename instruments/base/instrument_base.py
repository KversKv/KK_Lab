from abc import ABC, abstractmethod


class InstrumentBase(ABC):

    @abstractmethod
    def connect(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def disconnect(self):
        raise NotImplementedError

    def is_connected(self) -> bool:
        raise NotImplementedError
