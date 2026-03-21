#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波形绘制组件
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import pyqtgraph as pg


class PlotWidget(QWidget):
    """波形绘制组件"""
    
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        
        # 创建绘图窗口
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)
        
        # 设置绘图样式
        self._setup_plot_style()
        
        # 初始化数据
        self.time_data = []
        self.current_data = []
        self.voltage_data = []
        
        # 创建曲线
        self.current_curve = self.plot_widget.plot(
            self.time_data, self.current_data, 
            pen=pg.mkPen(color=(0, 255, 0), width=2),
            name="电流 (A)"
        )
        
        self.voltage_curve = self.plot_widget.plot(
            self.time_data, self.voltage_data, 
            pen=pg.mkPen(color=(0, 128, 255), width=2),
            name="电压 (V)"
        )
    
    def _setup_plot_style(self):
        """设置绘图样式"""
        # 设置背景颜色
        self.plot_widget.setBackground('#222222')
        
        # X 轴
        bottom_axis = self.plot_widget.getAxis('bottom')
        bottom_axis.setTextPen(pg.mkPen('#ffffff'))
        bottom_axis.setPen(pg.mkPen('#ffffff'))
        self.plot_widget.setLabel('bottom', '时间 (s)', color='#ffffff')
        
        # Y 轴
        left_axis = self.plot_widget.getAxis('left')
        left_axis.setTextPen(pg.mkPen('#ffffff'))
        left_axis.setPen(pg.mkPen('#ffffff'))
        self.plot_widget.setLabel('left', '值', color='#ffffff')
        
        # 添加图例
        self.plot_widget.addLegend()
        
        # 设置网格
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
    
    def update_plot(self, data):
        """更新波形"""
        if data and 'current' in data:
            # 更新数据
            if 'time' in data:
                self.time_data = data['time']
            if 'current' in data:
                self.current_data = data['current']
            if 'voltage' in data:
                self.voltage_data = data['voltage']
            
            # 更新曲线
            self.current_curve.setData(self.time_data, self.current_data)
            self.voltage_curve.setData(self.time_data, self.voltage_data)
            
            # 自动调整坐标轴范围
            if self.time_data and (self.current_data or self.voltage_data):
                self.plot_widget.setXRange(min(self.time_data), max(self.time_data))
                
                all_data = []
                if self.current_data:
                    all_data.extend(self.current_data)
                if self.voltage_data:
                    all_data.extend(self.voltage_data)
                
                if all_data:
                    min_val = min(all_data)
                    max_val = max(all_data)
                    padding = (max_val - min_val) * 0.1
                    self.plot_widget.setYRange(
                        min_val - padding if min_val > padding else 0,
                        max_val + padding
                    )
    
    def clear_plot(self):
        """清空波形"""
        self.time_data = []
        self.current_data = []
        self.voltage_data = []
        self.current_curve.setData(self.time_data, self.current_data)
        self.voltage_curve.setData(self.time_data, self.voltage_data)

