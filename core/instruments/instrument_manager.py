from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from core.instruments.instrument_session import (
    InstrumentCandidate,
    InstrumentIdentity,
    InstrumentSession,
    InstrumentSnapshot,
    InstrumentSpec,
)
from core.instruments.profiles import InstrumentProfile
from core.instruments.registry import ProfileRegistry, create_default_registry
from core.instruments.workers import ConnectWorker, DisconnectWorker, ScanWorker
from log_config import get_logger

logger = get_logger(__name__)


class InstrumentManager(QObject):
    sessions_changed = Signal()
    session_connected = Signal(str)
    session_disconnected = Signal(str)
    connection_failed = Signal(str, str)
    scan_finished = Signal(str, list)
    scan_failed = Signal(str, str)

    def __init__(self, registry: ProfileRegistry | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._registry = registry or create_default_registry()
        self._sessions: dict[str, InstrumentSession] = {}
        self._threads: dict[str, QThread] = {}
        self._workers: dict[str, QObject] = {}
        self._scan_threads: dict[str, QThread] = {}
        self._scan_workers: dict[str, QObject] = {}

    @property
    def registry(self) -> ProfileRegistry:
        return self._registry

    def sessions(
        self,
        instrument_type: str | None = None,
        role: str | None = None,
    ) -> list[InstrumentSnapshot]:
        result = []
        for session in self._sessions.values():
            if instrument_type and session.instrument_type != instrument_type:
                continue
            if role and session.role != role:
                continue
            result.append(session.to_snapshot())
        return result

    def get_session(self, session_id: str) -> InstrumentSession | None:
        return self._sessions.get(session_id)

    def get_instance(self, session_id: str) -> object | None:
        session = self._sessions.get(session_id)
        if session and session.connected:
            return session.instance
        return None

    def find_sessions(
        self,
        role: str = "",
        required_capabilities: set[str] | None = None,
        connected_only: bool = True,
    ) -> list[InstrumentSnapshot]:
        result = []
        for session in self._sessions.values():
            if connected_only and not session.connected:
                continue
            if role and session.role != role:
                continue
            if required_capabilities and not required_capabilities.issubset(session.capabilities):
                continue
            result.append(session.to_snapshot())
        return result

    def _make_session_id(self, spec: InstrumentSpec) -> str:
        slot = spec.slot
        if not slot or slot == "default":
            profile = self._registry.get(spec.instrument_type)
            slot = profile.default_slot if profile else "default"
        return f"{spec.instrument_type}:{slot}"

    def connect_async(self, spec: InstrumentSpec) -> str:
        profile = self._registry.get(spec.instrument_type)
        if not profile:
            err = f"No profile registered for instrument type: {spec.instrument_type}"
            logger.error(err)
            raise ValueError(err)

        session_id = self._make_session_id(spec)

        existing = self._sessions.get(session_id)
        if existing and existing.connected:
            logger.warning("Session %s already connected, disconnect first", session_id)
            return session_id

        if session_id in self._threads:
            logger.warning("Connection already in progress for %s", session_id)
            return session_id

        slot = spec.slot
        if not slot or slot == "default":
            slot = profile.default_slot

        session = InstrumentSession(
            session_id=session_id,
            instrument_type=spec.instrument_type,
            role=spec.role or profile.role,
            slot=slot,
            connection_kind=spec.connection_kind or profile.connection_kind,
            resource=spec.resource,
            serial=spec.serial,
            capabilities=set(profile.capabilities),
        )
        self._sessions[session_id] = session

        thread = QThread()
        worker = ConnectWorker(session_id, spec, profile)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.connected.connect(self._on_connected)
        worker.failed.connect(self._on_connect_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda sid=session_id: self._cleanup_connect_thread(sid))

        self._threads[session_id] = thread
        self._workers[session_id] = worker
        thread.start()

        logger.debug("Connect async started for %s (resource=%s)", session_id, spec.resource)
        return session_id

    def attach_external(
        self,
        spec: InstrumentSpec,
        instance: object,
        serial: str = "",
        model: str = "",
    ) -> str:
        profile = self._registry.get(spec.instrument_type)
        if not profile:
            err = f"No profile registered for instrument type: {spec.instrument_type}"
            logger.error(err)
            raise ValueError(err)

        session_id = self._make_session_id(spec)

        slot = spec.slot
        if not slot or slot == "default":
            slot = profile.default_slot

        session = InstrumentSession(
            session_id=session_id,
            instrument_type=spec.instrument_type,
            role=spec.role or profile.role,
            slot=slot,
            connection_kind=spec.connection_kind or profile.connection_kind,
            resource=spec.resource,
            serial=serial or spec.serial,
            model=model or spec.model_hint,
            capabilities=set(profile.capabilities),
            instance=instance,
            connected=True,
            owner="external",
        )
        self._sessions[session_id] = session
        logger.info("Attached external session %s (resource=%s)", session_id, spec.resource)
        self.session_connected.emit(session_id)
        self.sessions_changed.emit()
        return session_id

    def disconnect_async(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("No session found for %s", session_id)
            return
        if not session.connected:
            logger.warning("Session %s not connected", session_id)
            return

        profile = self._registry.get(session.instrument_type)
        if not profile:
            logger.warning("No profile for %s, removing session directly", session_id)
            session.instance = None
            session.connected = False
            self.session_disconnected.emit(session_id)
            self.sessions_changed.emit()
            return

        instance = session.instance
        session.instance = None
        session.connected = False
        self.session_disconnected.emit(session_id)
        self.sessions_changed.emit()

        if instance is None:
            return

        thread_key = f"disconnect:{session_id}"
        thread = QThread()
        worker = DisconnectWorker(session_id, instance, profile)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda k=thread_key: self._threads.pop(k, None))

        self._threads[thread_key] = thread
        thread.start()
        logger.debug("Disconnect async started for %s", session_id)

    def disconnect_all_async(self) -> None:
        session_ids = [
            sid for sid, s in self._sessions.items() if s.connected
        ]
        for session_id in session_ids:
            self.disconnect_async(session_id)

    def scan_async(self, instrument_type: str) -> None:
        profile = self._registry.get(instrument_type)
        if not profile:
            err = f"No profile for instrument_type: {instrument_type}"
            logger.error(err)
            self.scan_failed.emit(instrument_type, err)
            return

        if instrument_type in self._scan_threads:
            logger.warning("Scan already in progress for %s", instrument_type)
            return

        thread = QThread()
        worker = ScanWorker(instrument_type, profile)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.scan_finished.connect(self._on_scan_finished)
        worker.scan_failed.connect(self._on_scan_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=instrument_type: self._cleanup_scan_thread(t))

        self._scan_threads[instrument_type] = thread
        self._scan_workers[instrument_type] = worker
        thread.start()
        logger.debug("Scan async started for %s", instrument_type)

    def try_set_busy(self, session_id: str, busy: bool, owner: str = "") -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False
        if busy:
            if session.busy and session.busy_owner != owner:
                logger.warning(
                    "Session %s already busy (owner=%s), cannot set busy for %s",
                    session_id, session.busy_owner, owner,
                )
                return False
            session.busy = True
            session.busy_owner = owner
        else:
            session.busy = False
            session.busy_owner = ""
        self.sessions_changed.emit()
        return True

    def remove_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session:
            if session.connected and session.instance:
                profile = self._registry.get(session.instrument_type)
                if profile:
                    try:
                        profile.disconnect(session.instance)
                    except Exception as e:
                        logger.warning("Error disconnecting removed session %s: %s", session_id, e)
            self.sessions_changed.emit()

    def _on_connected(self, session_id: str, instance: object, identity: InstrumentIdentity):
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("Session %s not found on connect callback", session_id)
            return
        session.instance = instance
        session.connected = True
        session.model = identity.model
        session.serial = identity.serial
        session.last_error = ""
        logger.info(
            "Session %s connected: model=%s, serial=%s",
            session_id, identity.model, identity.serial,
        )
        self.session_connected.emit(session_id)
        self.sessions_changed.emit()

    def _on_connect_failed(self, session_id: str, error: str):
        session = self._sessions.get(session_id)
        if session:
            session.last_error = error
            session.connected = False
            session.instance = None
        logger.error("Session %s connection failed: %s", session_id, error)
        self.connection_failed.emit(session_id, error)
        self.sessions_changed.emit()

    def _on_scan_finished(self, instrument_type: str, candidates: list):
        logger.debug("Scan finished for %s: %d candidates", instrument_type, len(candidates))
        self.scan_finished.emit(instrument_type, candidates)

    def _on_scan_failed(self, instrument_type: str, error: str):
        logger.error("Scan failed for %s: %s", instrument_type, error)
        self.scan_failed.emit(instrument_type, error)

    def _cleanup_connect_thread(self, session_id: str):
        self._threads.pop(session_id, None)
        self._workers.pop(session_id, None)

    def _cleanup_scan_thread(self, instrument_type: str):
        self._scan_threads.pop(instrument_type, None)
        self._scan_workers.pop(instrument_type, None)

    def shutdown(self) -> None:
        for thread in list(self._threads.values()):
            if thread.isRunning():
                thread.quit()
                thread.wait(3000)
        for thread in list(self._scan_threads.values()):
            if thread.isRunning():
                thread.quit()
                thread.wait(3000)
        self._threads.clear()
        self._workers.clear()
        self._scan_threads.clear()
        self._scan_workers.clear()

        for session in self._sessions.values():
            if session.connected and session.instance:
                profile = self._registry.get(session.instrument_type)
                if profile:
                    try:
                        profile.disconnect(session.instance)
                    except Exception as e:
                        logger.warning("Shutdown disconnect error for %s: %s", session.session_id, e)
                session.instance = None
                session.connected = False
        self._sessions.clear()
        logger.info("InstrumentManager shutdown complete")
