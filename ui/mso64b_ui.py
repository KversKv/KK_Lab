#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MSO64B示波器UI组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QComboBox, QLabel, QLineEdit, QGridLayout, 
    QFrame, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class MSO64BUI(QWidget):
    """MSO64B示波器UI组件"""
    
    def __init__(self):
        super().__init__()
        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        
    def _setup_style(self):
        """设置界面样式"""
        # 设置字体
        font = QFont("Segoe UI", 9)
        self.setFont(font)
        
        # 设置样式表
        self.setStyleSheet("""
            QWidget {
                background-color: #16181c;
                color: #c8c8c8;
            }
            QGroupBox {
                border: 1px solid #333;
                border-radius: 6px;
                margin-top: 6px;
                background-color: #020618;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
                color: #c8c8c8;
            }
            QPushButton {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QPushButton:hover {
                background-color: #3a3d43;
            }
            QPushButton:pressed {
                background-color: #2a2d32;
            }
            QPushButton:disabled {
                background-color: #2a2d32;
                color: #666;
            }
            QComboBox {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 20px 4px 8px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QLineEdit {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QLabel {
                color: #c8c8c8;
            }
            QFrame {
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #020618;
            }
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #020618;
            }
            QTabBar::tab {
                background-color: #2a2d32;
                color: #c8c8c8;
                padding: 6px 12px;
                border: 1px solid #333;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #32353a;
                border-top: 2px solid #2a82da;
            }
        """)
    
    def _create_layout(self):
        """创建布局"""
        main_layout = QVBoxLayout(self)
        
        # 创建顶部控制栏
        top_control_bar = self._create_top_control_bar()
        main_layout.addWidget(top_control_bar)
        
        # 创建主内容区域（使用标签页）
        main_tab_widget = QTabWidget()
        
        # 通道设置标签页
        self.channels_tab = self._create_channels_tab()
        main_tab_widget.addTab(self.channels_tab, "Channels")
        
        # 测量标签页
        self.measure_tab = self._create_measure_tab()
        main_tab_widget.addTab(self.measure_tab, "Measure")
        
        # 波形显示标签页
        self.display_tab = self._create_display_tab()
        main_tab_widget.addTab(self.display_tab, "Display")
        
        main_layout.addWidget(main_tab_widget)
    
    def _create_top_control_bar(self):
        """创建顶部控制栏"""
        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #1a1d21; border-bottom: 1px solid #333;")
        top_bar_layout = QHBoxLayout(top_bar)
        
        # 连接控制
        connect_layout = QHBoxLayout()
        
        self.ip_address_edit = QLineEdit("192.168.3.27")
        self.ip_address_edit.setPlaceholderText("示波器IP地址")
        self.ip_address_edit.setFixedWidth(150)
        connect_layout.addWidget(self.ip_address_edit)
        
        self.connect_btn = QPushButton("连接")
        connect_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.setEnabled(False)
        connect_layout.addWidget(self.disconnect_btn)
        
        top_bar_layout.addLayout(connect_layout)
        
        # 仪器信息
        top_bar_layout.addStretch()
        
        self.instrument_info = QLabel("未连接")
        self.instrument_info.setStyleSheet("color: #888; padding: 10px;")
        top_bar_layout.addWidget(self.instrument_info)
        
        return top_bar
    
    def _create_channels_tab(self):
        """创建通道设置标签页"""
        channels_tab = QWidget()
        channels_layout = QVBoxLayout(channels_tab)
        
        # 4个通道设置
        channels_grid = QGridLayout()
        channels_grid.setSpacing(20)
        channels_grid.setContentsMargins(20, 20, 20, 20)
        
        self.channels = []
        for i in range(4):
            channel_widget = self._create_channel_widget(i+1)
            row = i // 2
            col = i % 2
            channels_grid.addWidget(channel_widget, row, col)
        
        channels_layout.addLayout(channels_grid)
        
        return channels_tab
    
    def _create_channel_widget(self, channel_num):
        """创建单个通道控件"""
        channel_frame = QFrame()
        channel_frame.setStyleSheet("""
            QFrame {
                background-color: #020618;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        channel_layout = QVBoxLayout(channel_frame)
        
        # 通道标题栏
        channel_header = QHBoxLayout()
        
        channel_label = QLabel(f"CH{channel_num}")
        channel_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        channel_header.addWidget(channel_label)
        
        channel_header.addStretch()
        
        # ON/OFF 开关
        self.channel_toggle = QPushButton("ON")
        self.channel_toggle.setCheckable(True)
        self.channel_toggle.setChecked(True)
        self.channel_toggle.setStyleSheet("""
            QPushButton {
                background-color: #00a859;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                min-width: 60px;
                font-size: 11px;
            }
            QPushButton:!checked {
                background-color: #555;
            }
        """)
        channel_header.addWidget(self.channel_toggle)
        
        channel_layout.addLayout(channel_header)
        
        # 参数设置区域
        params_grid = QGridLayout()
        params_grid.setSpacing(10)
        
        # 刻度设置
        params_grid.addWidget(QLabel("刻度:"), 0, 0)
        self.scale_edit = QLineEdit("1.0")
        self.scale_edit.setFixedWidth(60)
        params_grid.addWidget(self.scale_edit, 0, 1)
        params_grid.addWidget(QLabel("V/div"), 0, 2)
        
        # 位置设置
        params_grid.addWidget(QLabel("位置:"), 1, 0)
        self.position_edit = QLineEdit("0.0")
        self.position_edit.setFixedWidth(60)
        params_grid.addWidget(self.position_edit, 1, 1)
        params_grid.addWidget(QLabel("div"), 1, 2)
        
        # 耦合方式
        params_grid.addWidget(QLabel("耦合:"), 0, 3)
        self.coupling_combo = QComboBox()
        self.coupling_combo.addItems(["DC", "AC", "GND"])
        params_grid.addWidget(self.coupling_combo, 0, 4)
        
        # 带宽限制
        params_grid.addWidget(QLabel("带宽:"), 1, 3)
        self.bandwidth_combo = QComboBox()
        self.bandwidth_combo.addItems(["Full", "20MHz", "200MHz"])
        params_grid.addWidget(self.bandwidth_combo, 1, 4)
        
        channel_layout.addLayout(params_grid)
        
        channel_data = {
            'toggle': self.channel_toggle,
            'scale_edit': self.scale_edit,
            'position_edit': self.position_edit,
            'coupling_combo': self.coupling_combo,
            'bandwidth_combo': self.bandwidth_combo
        }
        
        self.channels.append(channel_data)
        
        return channel_frame
    
    def _create_measure_tab(self):
        """创建测量标签页"""
        measure_tab = QWidget()
        measure_layout = QVBoxLayout(measure_tab)
        
        # 测量控制区域
        measure_control_group = QGroupBox("测量控制")
        measure_control_layout = QGridLayout()
        
        # 通道选择
        measure_control_layout.addWidget(QLabel("通道:"), 0, 0)
        self.measure_channel_combo = QComboBox()
        self.measure_channel_combo.addItems(["CH1", "CH2", "CH3", "CH4"])
        measure_control_layout.addWidget(self.measure_channel_combo, 0, 1)
        
        # 测量类型
        measure_control_layout.addWidget(QLabel("类型:"), 0, 2)
        self.measure_type_combo = QComboBox()
        self.measure_type_combo.addItems(["MEAN", "PK2PK"])
        measure_control_layout.addWidget(self.measure_type_combo, 0, 3)
        
        # 测量按钮
        self.measure_btn = QPushButton("执行测量")
        measure_control_layout.addWidget(self.measure_btn, 0, 4)
        
        measure_control_group.setLayout(measure_control_layout)
        measure_layout.addWidget(measure_control_group)
        
        # 测量结果区域
        result_group = QGroupBox("测量结果")
        result_layout = QGridLayout()
        
        self.mean_result_label = QLabel("平均值: ---")
        self.mean_result_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        result_layout.addWidget(self.mean_result_label, 0, 0)
        
        self.pk2pk_result_label = QLabel("峰峰值: ---")
        self.pk2pk_result_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        result_layout.addWidget(self.pk2pk_result_label, 0, 1)
        
        result_group.setLayout(result_layout)
        measure_layout.addWidget(result_group)
        
        measure_layout.addStretch()
        
        return measure_tab
    
    def _create_display_tab(self):
        """创建波形显示标签页"""
        display_tab = QWidget()
        display_layout = QVBoxLayout(display_tab)
        
        # 波形显示区域
        display_group = QGroupBox("波形显示")
        display_group_layout = QVBoxLayout(display_group)
        
        # 这里可以添加pyqtgraph或其他绘图组件
        self.display_placeholder = QLabel("波形显示区域")
        self.display_placeholder.setAlignment(Qt.AlignCenter)
        self.display_placeholder.setStyleSheet("""
            QLabel {
                background-color: #1a1d21;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 50px;
                font-size: 16px;
                color: #666;
            }
        """)
        display_group_layout.addWidget(self.display_placeholder)
        
        display_layout.addWidget(display_group)
        
        # 显示控制区域
        control_group = QGroupBox("显示控制")
        control_layout = QGridLayout()
        
        # 时基设置
        control_layout.addWidget(QLabel("时基:"), 0, 0)
        self.timebase_edit = QLineEdit("10.0")
        self.timebase_edit.setFixedWidth(60)
        control_layout.addWidget(self.timebase_edit, 0, 1)
        control_layout.addWidget(QLabel("us/div"), 0, 2)
        
        # 触发源
        control_layout.addWidget(QLabel("触发源:"), 0, 3)
        self.trigger_source_combo = QComboBox()
        self.trigger_source_combo.addItems(["CH1", "CH2", "CH3", "CH4", "EXT"])
        control_layout.addWidget(self.trigger_source_combo, 0, 4)
        
        # 触发类型
        control_layout.addWidget(QLabel("触发类型:"), 1, 0)
        self.trigger_type_combo = QComboBox()
        self.trigger_type_combo.addItems(["Edge", "Pulse", "Rise", "Fall"])
        control_layout.addWidget(self.trigger_type_combo, 1, 1)
        
        # 触发电平
        control_layout.addWidget(QLabel("触发电平:"), 1, 3)
        self.trigger_level_edit = QLineEdit("1.0")
        self.trigger_level_edit.setFixedWidth(60)
        control_layout.addWidget(self.trigger_level_edit, 1, 4)
        control_layout.addWidget(QLabel("V"), 1, 5)
        
        control_group.setLayout(control_layout)
        display_layout.addWidget(control_group)
        
        return display_tab
    
    def _init_ui_elements(self):
        """初始化UI元素"""
        # 初始化通道设置的默认值
        for i, channel in enumerate(self.channels):
            channel['scale_edit'].setText("1.0")
            channel['position_edit'].setText("0.0")
            channel['coupling_combo'].setCurrentIndex(0)  # DC
            channel['bandwidth_combo'].setCurrentIndex(0)  # Full
    
    def get_connection_info(self):
        """获取连接信息"""
        return {
            'ip_address': self.ip_address_edit.text()
        }
    
    def get_channel_settings(self, channel_num):
        """获取指定通道的设置"""
        if 1 <= channel_num <= 4:
            channel = self.channels[channel_num - 1]
            return {
                'enabled': channel['toggle'].isChecked(),
                'scale': float(channel['scale_edit'].text()),
                'position': float(channel['position_edit'].text()),
                'coupling': channel['coupling_combo'].currentText(),
                'bandwidth': channel['bandwidth_combo'].currentText()
            }
        return None
    
    def get_measure_settings(self):
        """获取测量设置"""
        return {
            'channel': int(self.measure_channel_combo.currentText()[2:]),
            'type': self.measure_type_combo.currentText()
        }
    
    def update_measure_result(self, measure_type, value):
        """更新测量结果显示"""
        if measure_type == 'MEAN':
            self.mean_result_label.setText(f"平均值: {value:.6f} V")
        elif measure_type == 'PK2PK':
            self.pk2pk_result_label.setText(f"峰峰值: {value:.6f} V")
    
    def update_connection_status(self, connected, instrument_info=None):
        """更新连接状态"""
        if connected:
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.instrument_info.setText(instrument_info if instrument_info else "已连接")
            self.instrument_info.setStyleSheet("color: #00a859; padding: 10px;")
        else:
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.instrument_info.setText("未连接")
            self.instrument_info.setStyleSheet("color: #888; padding: 10px;")
