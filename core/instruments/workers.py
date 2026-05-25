from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from core.instruments.instrument_session import (
    InstrumentCandidate,
    InstrumentIdentity,
    InstrumentSpec,
)
from core.instruments.profiles import InstrumentProfile
from log_config import get_logger

logger = get_logger(__name__)


class ConnectWorker(QObject):
    connected = Signal(str, object, InstrumentIdentity)
    failed = Signal(str, str)
    finished = Signal()

    def __init__(self, session_id: str, spec: InstrumentSpec, profile: InstrumentProfile):
        super().__init__()
        self._session_id = session_id
        self._spec = spec
        self._profile = profile

    def run(self):
        instance = None
        try:
            instance = self._profile.create(self._spec)
            identity = self._profile.verify(instance)
            self.connected.emit(self._session_id, instance, identity)
        except Exception as e:
            logger.error(
                "Connect failed for %s: %s", self._session_id, e, exc_info=True
            )
            if instance is not None:
                try:
                    self._profile.disconnect(instance)
                except Exception as disc_err:
                    logger.warning(
                        "Failed to close half-connected instance for %s: %s",
                        self._session_id, disc_err, exc_info=True,
                    )
            self.failed.emit(self._session_id, str(e))
        finally:
            self.finished.emit()


class DisconnectWorker(QObject):
    disconnected = Signal(str)
    failed = Signal(str, str)
    finished = Signal()

    def __init__(self, session_id: str, instance: object, profile: InstrumentProfile):
        super().__init__()
        self._session_id = session_id
        self._instance = instance
        self._profile = profile

    def run(self):
        try:
            self._profile.disconnect(self._instance)
            self.disconnected.emit(self._session_id)
        except Exception as e:
            logger.error(
                "Disconnect failed for %s: %s", self._session_id, e, exc_info=True
            )
            self.failed.emit(self._session_id, str(e))
        finally:
            self.finished.emit()


class ScanWorker(QObject):
    scan_finished = Signal(str, list)
    scan_failed = Signal(str, str)
    finished = Signal()

    def __init__(self, instrument_type: str, profile: InstrumentProfile):
        super().__init__()
        self._instrument_type = instrument_type
        self._profile = profile

    def run(self):
        try:
            candidates = self._profile.scan()
            self.scan_finished.emit(self._instrument_type, candidates)
        except Exception as e:
            logger.error(
                "Scan failed for %s: %s", self._instrument_type, e, exc_info=True
            )
            self.scan_failed.emit(self._instrument_type, str(e))
        finally:
            self.finished.emit()
