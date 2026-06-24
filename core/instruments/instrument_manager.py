from __future__ import annotations

import time

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
    session_changed = Signal(str)
    session_connected = Signal(str)
    session_disconnected = Signal(str)
    disconnect_finished = Signal(str)
    disconnect_failed = Signal(str, str)
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
        self._pending_removal: set[str] = set()
        self._last_scan: dict[str, tuple[float, list[InstrumentCandidate]]] = {}

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
            self.connection_failed.emit(
                session_id, "Connection already in progress, please wait."
            )
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
        self.session_changed.emit(session_id)
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
        if session.disconnecting:
            logger.warning("Session %s already disconnecting", session_id)
            return

        profile = self._registry.get(session.instrument_type)
        if not profile:
            logger.warning("No profile for %s, removing session directly", session_id)
            session.instance = None
            session.connected = False
            session.disconnecting = False
            session.touch()
            self.session_disconnected.emit(session_id)
            self.session_changed.emit(session_id)
            self.sessions_changed.emit()
            self.disconnect_finished.emit(session_id)
            return

        session.disconnecting = True
        session.touch()
        self.session_changed.emit(session_id)
        self.sessions_changed.emit()

        instance = session.instance

        if instance is None:
            session.connected = False
            session.disconnecting = False
            session.touch()
            self.session_disconnected.emit(session_id)
            self.session_changed.emit(session_id)
            self.sessions_changed.emit()
            self.disconnect_finished.emit(session_id)
            return

        thread_key = f"disconnect:{session_id}"
        thread = QThread()
        worker = DisconnectWorker(session_id, instance, profile)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.disconnected.connect(self._on_disconnect_finished)
        worker.failed.connect(self._on_disconnect_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda k=thread_key: self._threads.pop(k, None))
        thread.finished.connect(lambda k=thread_key: self._workers.pop(k, None))

        self._threads[thread_key] = thread
        self._workers[thread_key] = worker
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

    def get_last_scan(self, instrument_type: str) -> list[InstrumentCandidate] | None:
        """返回最近一次扫描的候选列表副本（无缓存返回 None）。

        供 AI 动作层轮询取回异步扫描结果（scan_async 为 fire-and-forget）。
        """
        entry = self._last_scan.get(instrument_type)
        if entry is None:
            return None
        return list(entry[1])

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
        session.touch()
        self.session_changed.emit(session_id)
        self.sessions_changed.emit()
        return True

    def create_lease(self, session_id: str, owner: str) -> "InstrumentLease":
        from core.instruments.instrument_session import InstrumentLease
        return InstrumentLease(self, session_id, owner)

    def remove_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        if session.connected and session.instance:
            self._pending_removal.add(session_id)
            self.disconnect_async(session_id)
            return
        self._sessions.pop(session_id, None)
        self._pending_removal.discard(session_id)
        self.session_changed.emit(session_id)
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
        session.touch()
        logger.info(
            "Session %s connected: model=%s, serial=%s",
            session_id, identity.model, identity.serial,
        )
        self.session_connected.emit(session_id)
        self.session_changed.emit(session_id)
        self.sessions_changed.emit()

    def _on_connect_failed(self, session_id: str, error: str):
        self._sessions.pop(session_id, None)
        logger.error("Session %s connection failed: %s", session_id, error)
        self.connection_failed.emit(session_id, error)
        self.session_changed.emit(session_id)
        self.sessions_changed.emit()

    def _on_disconnect_finished(self, session_id: str):
        session = self._sessions.get(session_id)
        if session:
            session.instance = None
            session.connected = False
            session.disconnecting = False
            session.last_error = ""
            session.touch()
        logger.info("Session %s disconnected successfully", session_id)
        self.session_disconnected.emit(session_id)
        self.session_changed.emit(session_id)
        self.sessions_changed.emit()
        self.disconnect_finished.emit(session_id)
        if session_id in self._pending_removal:
            self._sessions.pop(session_id, None)
            self._pending_removal.discard(session_id)
            self.session_changed.emit(session_id)
            self.sessions_changed.emit()

    def _on_disconnect_failed(self, session_id: str, error: str):
        session = self._sessions.get(session_id)
        if session:
            session.disconnecting = False
            session.last_error = error
            session.touch()
        logger.error("Session %s disconnect failed: %s", session_id, error)
        self.disconnect_failed.emit(session_id, error)
        self.session_changed.emit(session_id)
        self.sessions_changed.emit()
        self._pending_removal.discard(session_id)

    def _on_scan_finished(self, instrument_type: str, candidates: list):
        logger.debug("Scan finished for %s: %d candidates", instrument_type, len(candidates))
        self._last_scan[instrument_type] = (time.time(), list(candidates))
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
                if not thread.wait(3000):
                    logger.warning("Thread did not finish in time during shutdown")
                    thread.terminate()
                    thread.wait(1000)
        for thread in list(self._scan_threads.values()):
            if thread.isRunning():
                thread.quit()
                if not thread.wait(3000):
                    logger.warning("Scan thread did not finish in time during shutdown")
                    thread.terminate()
                    thread.wait(1000)
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
                        logger.warning(
                            "Shutdown disconnect error for %s: %s",
                            session.session_id, e, exc_info=True,
                        )
                session.instance = None
                session.connected = False
                session.disconnecting = False
        self._sessions.clear()
        self._pending_removal.clear()
        logger.info("InstrumentManager shutdown complete")
