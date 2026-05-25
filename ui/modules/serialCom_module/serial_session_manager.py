import uuid

from PySide6.QtCore import QObject, Signal

from log_config import get_logger
from ui.modules.serialCom_module.serial_session import SerialSession

logger = get_logger(__name__)


class SerialSessionManager(QObject):
    session_added = Signal(str)
    session_removed = Signal(str)
    active_session_changed = Signal(str)
    session_connected_changed = Signal(str, bool)
    session_data_received = Signal(str, bytes)
    session_error = Signal(str, str)
    session_tx_done = Signal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions: dict[str, SerialSession] = {}
        self._active_session_id: str | None = None

    @property
    def active_session_id(self) -> str | None:
        return self._active_session_id

    @property
    def active_session(self) -> SerialSession | None:
        if self._active_session_id is None:
            return None
        return self._sessions.get(self._active_session_id)

    @property
    def sessions(self) -> dict[str, SerialSession]:
        return dict(self._sessions)

    @property
    def session_ids(self) -> list[str]:
        return list(self._sessions.keys())

    def create_session(self, session_id: str | None = None,
                       display_name: str = "", auto_activate: bool = True) -> SerialSession:
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"

        if session_id in self._sessions:
            return self._sessions[session_id]

        session = SerialSession(session_id, display_name, parent=self)
        session.connected_changed.connect(self._on_session_connected_changed)
        session.data_received.connect(self._on_session_data_received)
        session.error_occurred.connect(self._on_session_error)
        session.tx_done.connect(self._on_session_tx_done)

        self._sessions[session_id] = session
        self.session_added.emit(session_id)

        if auto_activate and self._active_session_id is None:
            self.set_active_session(session_id)

        return session

    def remove_session(self, session_id: str) -> bool:
        session = self._sessions.pop(session_id, None)
        if session is None:
            return False

        session.cleanup()
        self.session_removed.emit(session_id)

        if self._active_session_id == session_id:
            remaining = list(self._sessions.keys())
            if remaining:
                self.set_active_session(remaining[0])
            else:
                self._active_session_id = None
                self.active_session_changed.emit("")

        return True

    def get_session(self, session_id: str) -> SerialSession | None:
        return self._sessions.get(session_id)

    def set_active_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False
        if self._active_session_id == session_id:
            return True
        self._active_session_id = session_id
        self.active_session_changed.emit(session_id)
        return True

    def send_to_session(self, session_id: str, data) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            logger.warning("send_to_session: session %s not found", session_id)
            return False
        return session.send(data)

    def send_to_active_session(self, data) -> bool:
        session = self.active_session
        if session is None:
            return False
        return session.send(data)

    def broadcast_send(self, data, session_ids: list[str] | None = None) -> dict[str, bool]:
        targets = session_ids if session_ids is not None else list(self._sessions.keys())
        results = {}
        for sid in targets:
            session = self._sessions.get(sid)
            if session is not None:
                results[sid] = session.send(data)
            else:
                results[sid] = False
        return results

    def connect_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session is None:
            return False
        return session.connect_port()

    def disconnect_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if session is not None:
            session.disconnect_port()

    def disconnect_all(self):
        for session in self._sessions.values():
            session.disconnect_port()

    def cleanup_all(self):
        for session in list(self._sessions.values()):
            session.cleanup()
        self._sessions.clear()
        self._active_session_id = None

    def to_config(self) -> dict:
        return {
            "sessions": [s.to_config() for s in self._sessions.values()],
            "active_session_id": self._active_session_id or "",
        }

    def load_config(self, config: dict):
        sessions_cfg = config.get("sessions", [])
        for s_cfg in sessions_cfg:
            session_id = s_cfg.get("session_id", "")
            if not session_id or session_id in self._sessions:
                continue
            session = SerialSession.from_config(s_cfg, parent=self)
            session.connected_changed.connect(self._on_session_connected_changed)
            session.data_received.connect(self._on_session_data_received)
            session.error_occurred.connect(self._on_session_error)
            session.tx_done.connect(self._on_session_tx_done)
            self._sessions[session_id] = session
            self.session_added.emit(session_id)

        active_id = config.get("active_session_id", "")
        if active_id and active_id in self._sessions:
            self.set_active_session(active_id)
        elif self._sessions and self._active_session_id is None:
            self.set_active_session(next(iter(self._sessions)))

    def _on_session_connected_changed(self, session_id: str, connected: bool):
        self.session_connected_changed.emit(session_id, connected)

    def _on_session_data_received(self, session_id: str, data: bytes):
        self.session_data_received.emit(session_id, data)

    def _on_session_error(self, session_id: str, message: str):
        self.session_error.emit(session_id, message)

    def _on_session_tx_done(self, session_id: str, byte_count: int):
        self.session_tx_done.emit(session_id, byte_count)
