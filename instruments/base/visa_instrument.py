#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VISA 仪器控制
"""

import pyvisa as visa


class VisaInstrument:
    """VISA 仪器控制类"""
    
    def __init__(self):
        self.rm = None
        self.instrument = None
        self.current_channel = 1
    
    def scan_devices(self):
        """扫描可用的 VISA 设备"""
        try:
            if self.rm:
                try:
                    self.rm.close()
                except Exception:
                    pass
            self.rm = visa.ResourceManager()
            devices = self.rm.list_resources()
            return devices
        except Exception as e:
            print(f"扫描设备错误: {e}")
            return []
    
    def connect(self, device_address):
        """连接到指定设备"""
        try:
            if not self.rm:
                self.rm = visa.ResourceManager()
            
            self.instrument = self.rm.open_resource(device_address)
            self.instrument.timeout = 5000  # 设置超时时间
            
            # 验证连接
            idn = self.instrument.query('*IDN?')
            print(f"已连接到: {idn}")
            
            return True
        except Exception as e:
            print(f"连接设备错误: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            if self.instrument:
                self.instrument.close()
            if self.rm:
                self.rm.close()
            
            self.instrument = None
            self.rm = None
            return True
        except Exception as e:
            print(f"断开连接错误: {e}")
            return False
    
    def is_connected(self):
        """检查是否已连接"""
        return self.instrument is not None
    
    def set_channel(self, channel):
        """设置通道"""
        self.current_channel = channel
    
    def set_voltage(self, voltage):
        """设置输出电压"""
        try:
            if self.instrument:
                # 参考 N6705C 命令格式
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                self.instrument.write(f"VOLT {voltage}")
                return True
            return False
        except Exception as e:
            print(f"设置电压错误: {e}")
            return False
    
    def set_current_limit(self, current_limit):
        """设置限流"""
        try:
            if self.instrument:
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                self.instrument.write(f"CURR {current_limit}")
                return True
            return False
        except Exception as e:
            print(f"设置限流错误: {e}")
            return False
    
    def get_current(self):
        """获取电流值"""
        try:
            if self.instrument:
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                current = float(self.instrument.query("MEAS:CURR?"))
                return current
            return 0.0
        except Exception as e:
            print(f"获取电流错误: {e}")
            return 0.0
    
    def get_voltage(self):
        """获取电压值"""
        try:
            if self.instrument:
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                voltage = float(self.instrument.query("MEAS:VOLT?"))
                return voltage
            return 0.0
        except Exception as e:
            print(f"获取电压错误: {e}")
            return 0.0
    
    def set_output(self, enabled):
        """设置输出状态"""
        try:
            if self.instrument:
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                state = "ON" if enabled else "OFF"
                self.instrument.write(f"OUTP {state}")
                return True
            return False
        except Exception as e:
            print(f"设置输出状态错误: {e}")
            return False
