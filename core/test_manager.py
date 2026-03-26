#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试管理器
"""

import time
import csv
import os
from PySide6.QtCore import QObject, QThread, Signal
from core.data_collector import DataCollector


class TestManager(QObject):
    """测试管理器"""
    
    # 数据更新信号
    data_updated = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.data_collector = None
        self.collector_thread = None
        self.test_data = {
            'time': [],
            'current': [],
            'voltage': []
        }
    
    def start_test(self, visa_instrument, sampling_rate=100):
        """开始测试"""
        # 清空之前的数据
        self.test_data = {
            'time': [],
            'current': [],
            'voltage': []
        }
        
        # 创建数据采集器
        self.data_collector = DataCollector(visa_instrument, sampling_rate)
        
        # 创建线程
        self.collector_thread = QThread()
        self.data_collector.moveToThread(self.collector_thread)
        
        # 连接信号槽
        self.collector_thread.started.connect(self.data_collector.start_collection)
        self.data_collector.data_collected.connect(self._on_data_collected)
        self.data_collector.finished.connect(self.collector_thread.quit)
        self.data_collector.finished.connect(self.data_collector.deleteLater)
        self.collector_thread.finished.connect(self.collector_thread.deleteLater)
        
        # 启动线程
        self.collector_thread.start()
    
    def stop_test(self):
        """停止测试"""
        if self.data_collector:
            self.data_collector.stop_collection()
    
    def _on_data_collected(self, time_val, current, voltage):
        """处理采集到的数据"""
        # 添加数据
        self.test_data['time'].append(time_val)
        self.test_data['current'].append(current)
        self.test_data['voltage'].append(voltage)
        
        # 发送信号更新 UI
        self.data_updated.emit(self.test_data)
    
    def export_data(self):
        """导出数据"""
        if not self.test_data['time']:
            return
        
        # 创建导出目录
        export_dir = os.path.join(os.getcwd(), 'exports')
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
        
        # 生成文件名
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = os.path.join(export_dir, f'power_test_{timestamp}.csv')
        
        # 写入 CSV 文件
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow(['时间 (s)', '电流 (A)', '电压 (V)', '功耗 (W)'])
            
            # 写入数据
            for i in range(len(self.test_data['time'])):
                t = self.test_data['time'][i]
                current = self.test_data['current'][i]
                voltage = self.test_data['voltage'][i]
                power = current * voltage
                writer.writerow([t, current, voltage, power])
        
        print(f"数据已导出到: {filename}")
