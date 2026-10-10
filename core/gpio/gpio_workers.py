#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DUT GPIO I2C 异步 Worker（QObject + moveToThread，仅 QtCore）。

每次操作按需创建/销毁 I2CInterface，与 IIC_Module 既有范式一致。
GPIO 寄存器位于 Main-die 32bit 地址空间（0x4008xxxx），
设备地址取 bes_chip_check() 返回的 main_die_i2c_addr。
"""

from PySide6.QtCore import QObject, Signal

from log_config import get_logger

from core.gpio.gpio_config import OP_BITS, OP_WRITE

logger = get_logger(__name__)


def _open_i2c(dll_path, speed_mode):
    from lib.i2c.i2c_interface_x64 import I2CInterface
    i2c = I2CInterface(dll_path=dll_path, speed_mode=speed_mode)
    if not i2c.initialize():
        i2c.close()
        return None
    return i2c


def _bit32():
    from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
    return I2CWidthFlag.BIT_32


class GpioChipCheckWorker(QObject):
    """BES 芯片检测，用于自动匹配 GPIO JSON 配置。"""

    finished = Signal(object)   # chip_info dict
    error = Signal(str)

    def __init__(self, dll_path, speed_mode):
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode

    def run(self):
        i2c = _open_i2c(self._dll, self._speed)
        if i2c is None:
            self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
            return
        try:
            self.finished.emit(i2c.bes_chip_check())
        except Exception as e:
            logger.error("GPIO chip check failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                i2c.close()
            except Exception:
                logger.error("GPIO chip check close failed", exc_info=True)


class GpioReadBanksWorker(QObject):
    """批量读取各 bank 的输入电平寄存器（base+0x50）。"""

    finished = Signal(object)   # dict: bank_index -> 32bit value
    error = Signal(str)

    def __init__(self, dll_path, speed_mode, dev_addr, read_list):
        """read_list: [(bank_index, in_read_addr), ...]"""
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode
        self._dev = dev_addr
        self._read_list = list(read_list)

    def run(self):
        i2c = _open_i2c(self._dll, self._speed)
        if i2c is None:
            self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
            return
        try:
            width = _bit32()
            values = {}
            for bank_index, addr in self._read_list:
                values[bank_index] = int(i2c.read(self._dev, addr, width))
            self.finished.emit(values)
        except Exception as e:
            logger.error("GPIO read banks failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                i2c.close()
            except Exception:
                logger.error("GPIO read banks close failed", exc_info=True)


class GpioApplyWorker(QObject):
    """顺序执行一组 GPIO 寄存器动作（模式切换 / drv 设置）。"""

    progress = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, dll_path, speed_mode, dev_addr, actions, label=""):
        """actions: [(op, addr, value, high_bit, low_bit), ...]"""
        super().__init__()
        self._dll = dll_path
        self._speed = speed_mode
        self._dev = dev_addr
        self._actions = list(actions)
        self._label = label

    def run(self):
        i2c = _open_i2c(self._dll, self._speed)
        if i2c is None:
            self.error.emit("I2C 接口初始化失败 (DLL 加载或设备打开失败)")
            return
        try:
            width = _bit32()
            for op, addr, value, high, low in self._actions:
                if op == OP_BITS:
                    i2c.write(self._dev, addr, value, width, high, low)
                    self.progress.emit(
                        "WRITE_BITS 0x{0:08X} [{1}:{2}] = 0x{3:X}".format(
                            addr, high, low, value))
                elif op == OP_WRITE:
                    i2c.write(self._dev, addr, value, width)
                    self.progress.emit(
                        "WRITE 0x{0:08X} = 0x{1:08X}".format(addr, value))
                else:
                    logger.warning("未知 GPIO 动作(跳过): %s", op)
            self.finished.emit()
        except Exception as e:
            logger.error("GPIO apply failed: %s", e, exc_info=True)
            self.error.emit(str(e))
        finally:
            try:
                i2c.close()
            except Exception:
                logger.error("GPIO apply close failed", exc_info=True)


__all__ = ["GpioChipCheckWorker", "GpioReadBanksWorker", "GpioApplyWorker"]
