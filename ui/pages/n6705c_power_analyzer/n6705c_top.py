#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal
from instruments.power.keysight.n6705c import N6705C
from log_config import get_logger

logger = get_logger(__name__)


class N6705CTop(QObject):
    connection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rm = None
        self.n6705c_a = None
        self.n6705c_b = None
        self.is_connected_a = False
        self.is_connected_b = False
        self.visa_resource_a = ""
        self.visa_resource_b = ""
        self.serial_a = ""
        self.serial_b = ""

    def connect_a(self, visa_resource, n6705c_instance=None, serial=""):
        logger.debug("N6705CTop connect_a: resource=%s, serial=%s", visa_resource, serial)
        if n6705c_instance is not None:
            self.n6705c_a = n6705c_instance
        else:
            self.n6705c_a = N6705C(visa_resource)
        self.is_connected_a = True
        self.visa_resource_a = visa_resource
        self.serial_a = serial
        self.connection_changed.emit()

    def connect_b(self, visa_resource, n6705c_instance=None, serial=""):
        logger.debug("N6705CTop connect_b: resource=%s, serial=%s", visa_resource, serial)
        if n6705c_instance is not None:
            self.n6705c_b = n6705c_instance
        else:
            self.n6705c_b = N6705C(visa_resource)
        self.is_connected_b = True
        self.visa_resource_b = visa_resource
        self.serial_b = serial
        self.connection_changed.emit()

    def disconnect_a(self):
        logger.debug("N6705CTop disconnect_a")
        if self.n6705c_a:
            try:
                self.n6705c_a.disconnect()
            except Exception:
                pass
        self.n6705c_a = None
        self.is_connected_a = False
        self.visa_resource_a = ""
        self.serial_a = ""
        self.connection_changed.emit()

    def disconnect_b(self):
        logger.debug("N6705CTop disconnect_b")
        if self.n6705c_b:
            try:
                self.n6705c_b.disconnect()
            except Exception:
                pass
        self.n6705c_b = None
        self.is_connected_b = False
        self.visa_resource_b = ""
        self.serial_b = ""
        self.connection_changed.emit()

    def disconnect_all(self):
        logger.debug("N6705CTop disconnect_all")
        self.disconnect_a()
        self.disconnect_b()
