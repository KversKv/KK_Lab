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
from pathlib import Path


script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# 导入I2C接口
from Bes_I2CIO_Interface import BESI2CIO, I2CSpeedMode, I2CWidthFlag


class I2CInterface:
    """I2C接口封装类，提供简洁的I2C操作API"""
    
    def __init__(self, dll_path=None, speed_mode=I2CSpeedMode.SPEED_100K):
        """
        初始化I2C接口
        
        参数:
        dll_path: I2C接口DLL文件路径，如果为None则使用默认路径
        speed_mode: I2C通信速度模式，默认100kHz
        """
        self.speed_mode = speed_mode
        
        # 设置默认DLL路径
        if dll_path is None:
            dll_path = str(script_dir / "config" / "BES_USBIO_I2C_X64.dll")
        
        self.dll_path = dll_path
        self.i2c = None
        self.initialized = False
        
    def config(self, dll_path=None, speed_mode=None):
        """
        配置I2C接口参数
        
        参数:
        dll_path: I2C接口DLL文件路径
        speed_mode: I2C通信速度模式
        """
        if dll_path is not None:
            self.dll_path = dll_path
        
        if speed_mode is not None:
            self.speed_mode = speed_mode
        
        # 如果已经初始化，重新初始化
        if self.initialized:
            self.initialize()
    
    def initialize(self):
        """初始化I2C接口"""
        try:
            self.i2c = BESI2CIO(self.dll_path)
            self.initialized = True
            return True
        except Exception as e:
            print(f"I2C接口初始化失败: {e}")
            self.initialized = False
            return False
    
    def read(self, device_addr, reg_addr, width_flag):
        """
        从I2C设备读取数据
        
        参数:
        device_addr: 设备地址
        reg_addr: 寄存器地址
        width_flag: 位宽标志（I2CWidthFlag）
        
        返回:
        读取到的数据
        """
        if not self.initialized:
            if not self.initialize():
                raise Exception("I2C接口未初始化成功")
        
        try:
            return self.i2c.read(
                self.speed_mode,
                device_addr,
                reg_addr,
                width_flag
            )
        except Exception as e:
            raise Exception(f"I2C读取失败: {e}")
    
    def write(self, device_addr, reg_addr, write_data, width_flag):
        """
        向I2C设备写入数据
        
        参数:
        device_addr: 设备地址
        reg_addr: 寄存器地址
        write_data: 要写入的数据
        width_flag: 位宽标志（I2CWidthFlag）
        """
        if not self.initialized:
            if not self.initialize():
                raise Exception("I2C接口未初始化成功")
        
        try:
            self.i2c.write(
                self.speed_mode,
                device_addr,
                reg_addr,
                write_data,
                width_flag
            )
            return True
        except Exception as e:
            raise Exception(f"I2C写入失败: {e}")


# 示例用法
if __name__ == "__main__":
    """示例用法演示"""
    print("I2C接口封装类示例")
    print("=" * 50)
    
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
        print(f"\n1. 读取操作：")
        print(f"   设备地址: 0x{device_addr:02X}")
        print(f"   寄存器地址: 0x{reg_addr_read:04X}")
        print(f"   位宽模式: {width_flag.name}")
        
        read_data = i2c.read(device_addr, reg_addr_read, width_flag)
        print(f"   读取结果: 0x{read_data:04X}")
        
        # 2. 写入操作：器件地址0x17，寄存器地址0x1e7，数据0x20AA
        reg_addr_write = 0x1e7
        write_data = 0x20AA
        print(f"\n2. 写入操作：")
        print(f"   设备地址: 0x{device_addr:02X}")
        print(f"   寄存器地址: 0x{reg_addr_write:04X}")
        print(f"   写入数据: 0x{write_data:04X}")
        print(f"   位宽模式: {width_flag.name}")
        
        i2c.write(device_addr, reg_addr_write, write_data, width_flag)
        print(f"   写入成功")
        
        # 3. 验证写入结果
        time.sleep(0.1)
        verify_data = i2c.read(device_addr, reg_addr_write, width_flag)
        print(f"\n3. 验证写入结果：")
        print(f"   寄存器地址0x{reg_addr_write:04X}的当前值: 0x{verify_data:04X}")
        print(f"   验证{'成功' if verify_data == write_data else '失败'}")
        
    except Exception as e:
        print(f"I2C操作失败: {e}")