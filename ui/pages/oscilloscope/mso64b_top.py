#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal
from log_config import get_logger

logger = get_logger(__name__)


class MSO64BTop(QObject):
    connection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mso64b = None
        self.is_connected = False
        self.visa_resource = ""
        self.scope_type = ""
        self._manager = None

    def set_instrument_manager(self, manager):
        self._manager = manager
        if manager:
            manager.session_connected.connect(self._on_session_connected)
            manager.session_disconnected.connect(self._on_session_disconnected)

    def _resolve_scope_session_id(self, scope_type=""):
        inst_type = scope_type.lower() if scope_type else "mso64b"
        if inst_type not in ("mso64b", "dsox4034a"):
            inst_type = "mso64b"
        return f"{inst_type}:main_scope"

    def _on_session_connected(self, session_id: str):
        if session_id.endswith(":main_scope"):
            session = self._manager.get_session(session_id)
            if session and session.connected:
                self.mso64b = session.instance
                self.is_connected = True
                self.visa_resource = session.resource
                self.scope_type = session.model or session.instrument_type.upper()
                self.connection_changed.emit()

    def _on_session_disconnected(self, session_id: str):
        if session_id.endswith(":main_scope"):
            self.mso64b = None
            self.is_connected = False
            self.visa_resource = ""
            self.scope_type = ""
            self.connection_changed.emit()

    def connect_instrument(self, visa_resource, mso64b_instance=None, scope_type="MSO64B"):
        logger.debug("MSO64BTop connect_instrument: resource=%s, type=%s", visa_resource, scope_type)
        if mso64b_instance is not None:
            self.mso64b = mso64b_instance
        else:
            from instruments.scopes.tektronix.mso64b import MSO64B
            self.mso64b = MSO64B(visa_resource)
        self.is_connected = True
        self.visa_resource = visa_resource
        self.scope_type = scope_type
        inst_type = scope_type.lower() if scope_type else "mso64b"
        if inst_type not in ("mso64b", "dsox4034a"):
            inst_type = "mso64b"
        if self._manager:
            from core.instruments import InstrumentSpec
            self._manager.attach_external(
                InstrumentSpec(
                    instrument_type=inst_type,
                    resource=visa_resource,
                    slot="main_scope",
                ),
                instance=self.mso64b, serial="", model=scope_type,
            )
        self.connection_changed.emit()

    def disconnect(self):
        logger.debug("MSO64BTop disconnect")
        scope_type = self.scope_type
        if self._manager:
            session_id = self._resolve_scope_session_id(scope_type)
            session = self._manager.get_session(session_id)
            if session and session.connected:
                self._manager.disconnect_async(session_id)
                return
        if self.mso64b:
            try:
                self.mso64b.disconnect()
            except Exception:
                pass
        self.mso64b = None
        self.is_connected = False
        self.visa_resource = ""
        self.scope_type = ""
        self.connection_changed.emit()
