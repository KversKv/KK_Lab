#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BES chip 检测 Worker。"""

from PySide6.QtCore import QObject, Signal


class ChipCheckWorker(QObject):
    finished = Signal(object)
    error = Signal(str)

    def run(self):
        try:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            i2c = I2CInterface()
            if not i2c.initialize():
                self.error.emit("I2C interface initialization failed.")
                return
            chip_info = i2c.bes_chip_check()
            self.finished.emit(chip_info)
        except Exception as e:
            self.error.emit(str(e))


__all__ = ["ChipCheckWorker"]
