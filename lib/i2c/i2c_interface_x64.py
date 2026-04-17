#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
I2C读写接口封装类

封装了I2C接口的读写操作，提供简洁的API接口
支持8位、10位、32位地址/数据宽度的操作

作者: 芯片调试工具
创建时间: 2025
"""

import sys
import time
import threading
from pathlib import Path


script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from Bes_I2CIO_Interface import (
    BESI2CIO, I2CSpeedMode, I2CWidthFlag,
    I2CError, I2CDeviceError, I2COperationError, I2CParameterError, I2CStatus,
)

import logging
logger = logging.getLogger(__name__)

_INT_TO_WIDTH_FLAG = {
    8: I2CWidthFlag.BIT_8,
    10: I2CWidthFlag.BIT_10,
    32: I2CWidthFlag.BIT_32,
}


class I2CInterface:
    """I2C接口封装类，提供简洁的I2C操作API"""

    _init_lock = threading.Lock()

    def __init__(self, dll_path=None, speed_mode=I2CSpeedMode.SPEED_100K,
                 verbose=False):
        """
        初始化I2C接口

        参数:
        dll_path: I2C接口DLL文件路径，如果为None则使用默认路径
        speed_mode: I2C通信速度模式，默认100kHz
        verbose: 是否显示DLL内部调试输出，默认False
        """
        self._speed_mode = speed_mode
        self._verbose = verbose

        if dll_path is None:
            dll_path = str(script_dir / "config" / "BES_USBIO_I2C_X64.dll")

        self._dll_path = dll_path
        self._i2c: BESI2CIO | None = None
        self._initialized = False

    @property
    def speed_mode(self) -> I2CSpeedMode:
        return self._speed_mode

    @speed_mode.setter
    def speed_mode(self, value: I2CSpeedMode):
        self._speed_mode = value

    @property
    def initialized(self) -> bool:
        return self._initialized

    def config(self, dll_path=None, speed_mode=None):
        """
        配置I2C接口参数

        参数:
        dll_path: I2C接口DLL文件路径（修改后需重新初始化）
        speed_mode: I2C通信速度模式（仅更新参数，不触发重新初始化）
        """
        need_reinit = False

        if speed_mode is not None:
            self._speed_mode = speed_mode

        if dll_path is not None and dll_path != self._dll_path:
            self._dll_path = dll_path
            need_reinit = True

        if need_reinit and self._initialized:
            old_i2c = self._i2c
            try:
                self.initialize()
            except Exception:
                self._i2c = old_i2c
                self._initialized = old_i2c is not None
                raise

    def initialize(self):
        """初始化I2C接口"""
        try:
            self._i2c = BESI2CIO(self._dll_path, verbose=self._verbose)
            self._initialized = True
            return True
        except Exception as e:
            logger.error("I2C接口初始化失败: %s", e)
            self._initialized = False
            return False

    def _ensure_initialized(self):
        if self._initialized:
            return
        with self._init_lock:
            if not self._initialized:
                if not self.initialize():
                    raise I2CDeviceError(
                        I2CStatus.ERROR_OPEN_DEVICE, "I2C接口未初始化成功"
                    )

    @staticmethod
    def _normalize_width_flag(width_flag):
        if isinstance(width_flag, I2CWidthFlag):
            return width_flag
        if width_flag in _INT_TO_WIDTH_FLAG:
            return _INT_TO_WIDTH_FLAG[width_flag]
        try:
            return I2CWidthFlag(width_flag)
        except ValueError:
            raise ValueError(f"Invalid width_flag: {width_flag}")

    def read(self, device_addr, reg_addr, width_flag):
        """
        从I2C设备读取数据

        参数:
        device_addr: 设备地址
        reg_addr: 寄存器地址
        width_flag: 位宽标志（I2CWidthFlag 或 整数 8/10/32）

        返回:
        读取到的数据

        异常:
        I2CDeviceError: 设备打开或连接失败
        I2COperationError: I2C通信操作失败
        I2CParameterError: 参数无效
        ValueError: width_flag 值非法
        """
        self._ensure_initialized()
        width_flag = self._normalize_width_flag(width_flag)
        return self._i2c.read(
            self._speed_mode,
            device_addr,
            reg_addr,
            width_flag,
        )

    def write(self, device_addr, reg_addr, write_data, width_flag):
        """
        向I2C设备写入数据

        参数:
        device_addr: 设备地址
        reg_addr: 寄存器地址
        write_data: 要写入的数据
        width_flag: 位宽标志（I2CWidthFlag 或 整数 8/10/32）

        异常:
        I2CDeviceError: 设备打开或连接失败
        I2COperationError: I2C通信操作失败
        I2CParameterError: 参数无效
        ValueError: width_flag 值非法
        """
        self._ensure_initialized()
        width_flag = self._normalize_width_flag(width_flag)
        self._i2c.write(
            self._speed_mode,
            device_addr,
            reg_addr,
            write_data,
            width_flag,
        )
        return True

    @property
    def raw(self) -> BESI2CIO:
        """获取底层I2C对象，用于高级操作（如 read_data / write_data）"""
        self._ensure_initialized()
        return self._i2c

    def close(self):
        """释放I2C接口资源"""
        self._i2c = None
        self._initialized = False

    def __enter__(self):
        self._ensure_initialized()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# 示例用法
if __name__ == "__main__":
    """示例用法演示"""
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
    logger.info("I2C接口封装类示例")
    logger.info("=" * 50)
    
    # 创建I2C接口实例
    i2c = I2CInterface()
    
    # 配置参数（可选，如果使用默认参数则不需要）
    # i2c.config(speed_mode=I2CSpeedMode.SPEED_400K)
    
    # 测试参数
    device_addr = 0x17
    width_flag = I2CWidthFlag.BIT_10
    
    try:
        # 1. 读取操作：器件地址0x17，寄存器地址0x0000
        reg_addr_read = 0x0000
        logger.info("1. 读取操作：")
        logger.info("   设备地址: 0x%02X", device_addr)
        logger.info("   寄存器地址: 0x%04X", reg_addr_read)
        logger.info("   位宽模式: %s", width_flag.name)
        
        read_data = i2c.read(device_addr, reg_addr_read, width_flag)
        logger.info("   读取结果: 0x%04X", read_data)
        
        reg_addr_write = 0x1e7
        write_data = 0x20AA
        logger.info("2. 写入操作：")
        logger.info("   设备地址: 0x%02X", device_addr)
        logger.info("   寄存器地址: 0x%04X", reg_addr_write)
        logger.info("   写入数据: 0x%04X", write_data)
        logger.info("   位宽模式: %s", width_flag.name)
        
        i2c.write(device_addr, reg_addr_write, write_data, width_flag)
        logger.info("   写入成功")
        
        time.sleep(0.1)
        verify_data = i2c.read(device_addr, reg_addr_write, width_flag)
        logger.info("3. 验证写入结果：")
        logger.info("   寄存器地址0x%04X的当前值: 0x%04X", reg_addr_write, verify_data)
        logger.info("   验证%s", '成功' if verify_data == write_data else '失败')
        
    except Exception as e:
        logger.error("I2C操作失败: %s", e)