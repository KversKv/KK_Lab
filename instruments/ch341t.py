#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CH341T I2C 控制
"""

import ctypes
import os


class CH341T:
    """CH341T I2C 控制类"""
    
    def __init__(self):
        self.dll_path = None
        self.ch341_dll = None
        self.device_handle = None
    
    def _load_dll(self):
        """加载 CH341T 动态链接库"""
        # 查找 DLL 文件
        possible_paths = [
            './i2c_demo_x64.dll',
            'i2c_demo_x64.dll',
            os.path.join(os.getcwd(), 'i2c_demo_x64.dll')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.dll_path = path
                break
        
        if not self.dll_path:
            print("未找到 CH341T DLL 文件")
            return False
        
        try:
            self.ch341_dll = ctypes.WinDLL(self.dll_path)
            return True
        except Exception as e:
            print(f"加载 DLL 错误: {e}")
            return False
    
    def scan_ports(self):
        """扫描可用的 CH341T 端口"""
        if not self.ch341_dll:
            if not self._load_dll():
                return []
        
        try:
            # 这里需要根据实际 DLL 的函数接口来实现
            # 假设 DLL 提供了扫描端口的函数
            # 示例代码，需要根据实际情况修改
            ports = []
            for i in range(16):  # 假设最多 16 个端口
                # 这里需要调用实际的端口检测函数
                # 示例：如果端口存在，添加到列表
                ports.append(f"COM{i+1}")
            return ports
        except Exception as e:
            print(f"扫描端口错误: {e}")
            return []
    
    def connect(self, port):
        """连接到 CH341T 端口"""
        if not self.ch341_dll:
            if not self._load_dll():
                return False
        
        try:
            # 这里需要根据实际 DLL 的函数接口来实现
            # 假设 DLL 提供了打开设备的函数
            # 示例代码，需要根据实际情况修改
            # self.device_handle = self.ch341_dll.CH341OpenDevice(port)
            # if self.device_handle != -1:
            self.device_handle = 1  # 模拟连接成功
            print(f"已连接到 CH341T 端口: {port}")
            return True
        except Exception as e:
            print(f"连接 CH341T 错误: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.device_handle:
                # 这里需要调用实际的关闭设备函数
                # 示例：self.ch341_dll.CH341CloseDevice(self.device_handle)
                self.device_handle = None
            return True
        except Exception as e:
            print(f"断开连接错误: {e}")
            return False
    
    def is_connected(self):
        """检查是否已连接"""
        return self.device_handle is not None
    
    def send_command(self, command):
        """发送 IIC 指令"""
        if not self.device_handle:
            print("未连接到 CH341T")
            return False
        
        try:
            # 解析命令
            # 这里需要根据实际的命令格式来解析
            # 示例：将十六进制字符串转换为字节
            if command.startswith('0x'):
                cmd_bytes = bytes.fromhex(command[2:])
            else:
                cmd_bytes = bytes.fromhex(command)
            
            # 这里需要调用实际的 I2C 写入函数
            # 示例：self.ch341_dll.CH341WriteI2C(self.device_handle, cmd_bytes, len(cmd_bytes))
            print(f"发送 IIC 指令: {command}")
            return True
        except Exception as e:
            print(f"发送指令错误: {e}")
            return False
    
    def read_data(self, length=1):
        """读取 IIC 数据"""
        if not self.device_handle:
            print("未连接到 CH341T")
            return []
        
        try:
            # 这里需要调用实际的 I2C 读取函数
            # 示例：data = self.ch341_dll.CH341ReadI2C(self.device_handle, length)
            # 模拟返回数据
            data = [0x00] * length
            print(f"读取 IIC 数据: {data}")
            return data
        except Exception as e:
            print(f"读取数据错误: {e}")
            return []
