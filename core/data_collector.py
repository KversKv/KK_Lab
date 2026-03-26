#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据采集器
"""

import time
from PySide6.QtCore import QObject, Signal, QTimer


class DataCollector(QObject):
    """数据采集器"""
    
    # 数据采集信号
    data_collected = Signal(float, float, float)
    # 采集完成信号
    finished = Signal()
    
    def __init__(self, visa_instrument, sampling_rate=100):
        super().__init__()
        self.visa_instrument = visa_instrument
        self.sampling_rate = sampling_rate
        self.is_collecting = False
        self.start_time = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._collect_data)
    
    def start_collection(self):
        """开始数据采集"""
        self.is_collecting = True
        self.start_time = time.time()
        # 设置定时器间隔
        interval = int(1000 / self.sampling_rate)  # 转换为毫秒
        self.timer.start(interval)
    
    def stop_collection(self):
        """停止数据采集"""
        self.is_collecting = False
        self.timer.stop()
        self.finished.emit()
    
    def _collect_data(self):
        """采集数据"""
        if not self.is_collecting:
            return
        
        try:
            # 计算当前时间
            current_time = time.time() - self.start_time
            
            # 从仪器获取数据
            current = self.visa_instrument.get_current()
            voltage = self.visa_instrument.get_voltage()
            
            # 发送数据信号
            self.data_collected.emit(current_time, current, voltage)
        except Exception as e:
            print(f"数据采集错误: {e}")
