#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal


class MSO64BTop(QObject):
    connection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mso64b = None
        self.is_connected = False
        self.visa_resource = ""

    def connect(self, visa_resource, mso64b_instance=None):
        if mso64b_instance is not None:
            self.mso64b = mso64b_instance
        else:
            from instruments.scopes.tektronix.mso64b import MSO64B
            self.mso64b = MSO64B(visa_resource)
        self.is_connected = True
        self.visa_resource = visa_resource
        self.connection_changed.emit()

    def disconnect(self):
        if self.mso64b:
            try:
                self.mso64b.disconnect()
            except Exception:
                pass
        self.mso64b = None
        self.is_connected = False
        self.visa_resource = ""
        self.connection_changed.emit()
