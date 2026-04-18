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
        self.connection_changed.emit()

    def disconnect(self):
        logger.debug("MSO64BTop disconnect")
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
