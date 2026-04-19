#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VISA 仪器控制
"""

import pyvisa as visa
from instruments.base.instrument_base import InstrumentBase
from log_config import get_logger

logger = get_logger(__name__)


class VisaInstrument(InstrumentBase):
    """VISA 仪器控制类"""
    
    def __init__(self):
        self.rm = None
        self.instrument = None
        self.current_channel = 1
    
    def scan_devices(self):
        """扫描可用的 VISA 设备"""
        try:
            if self.rm:
                logger.debug("Closing existing ResourceManager before scan")
                try:
                    self.rm.close()
                except Exception:
                    pass
            self.rm = visa.ResourceManager()
            devices = self.rm.list_resources()
            logger.debug("VISA scan found %d device(s): %s", len(devices), devices)
            return devices
        except Exception as e:
            logger.error("扫描设备错误: %s", e)
            return []
    
    def connect(self, device_address):
        """连接到指定设备"""
        try:
            logger.debug("Connecting to VISA device: %s", device_address)
            if not self.rm:
                self.rm = visa.ResourceManager()
            
            self.instrument = self.rm.open_resource(device_address)
            self.instrument.timeout = 5000
            
            idn = self.instrument.query('*IDN?')
            logger.info("已连接到: %s", idn)
            logger.debug("VISA timeout set to %d ms", self.instrument.timeout)
            
            return True
        except Exception as e:
            logger.error("连接设备错误: %s", e)
            return False
    
    def disconnect(self):
        """断开连接"""
        try:
            logger.debug("Disconnecting VISA instrument")
            if self.instrument:
                self.instrument.close()
            if self.rm:
                self.rm.close()
            
            self.instrument = None
            self.rm = None
            logger.debug("VISA instrument disconnected successfully")
            return True
        except Exception as e:
            logger.error("断开连接错误: %s", e)
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
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                self.instrument.write(f"VOLT {voltage}")
                logger.debug("Set voltage CH%d = %s V", self.current_channel, voltage)
                return True
            return False
        except Exception as e:
            logger.error("设置电压错误: %s", e)
            return False
    
    def set_current_limit(self, current_limit):
        """设置限流"""
        try:
            if self.instrument:
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                self.instrument.write(f"CURR {current_limit}")
                logger.debug("Set current limit CH%d = %s A", self.current_channel, current_limit)
                return True
            return False
        except Exception as e:
            logger.error("设置限流错误: %s", e)
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
            logger.error("获取电流错误: %s", e)
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
            logger.error("获取电压错误: %s", e)
            return 0.0
    
    def set_output(self, enabled):
        """设置输出状态"""
        try:
            if self.instrument:
                self.instrument.write(f"INST:SEL CH{self.current_channel}")
                state = "ON" if enabled else "OFF"
                self.instrument.write(f"OUTP {state}")
                logger.debug("Set output CH%d = %s", self.current_channel, state)
                return True
            return False
        except Exception as e:
            logger.error("设置输出状态错误: %s", e)
            return False
