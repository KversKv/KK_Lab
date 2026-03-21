#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N6705C电源分析仪UI组件
"""
import sys
import os
# 将项目根目录添加到Python路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QComboBox, QLabel, QLineEdit, QGridLayout, 
    QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
import pyvisa
from instruments.n6705c import N6705C


class N6705CUI(QWidget):
    """N6705C电源分析仪UI组件"""
    
    # 定义信号
    connection_status_changed = Signal(bool)  # 参数表示是否连接成功
    
    def __init__(self):
        super().__init__()
        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        
        # 初始化仪器实例和状态
        self.rm = None  # VISA资源管理器
        self.instrument = None  # 仪器实例
        self.n6705c = None  # N6705C控制器
        self.is_connected = False
        self.available_devices = []  # 搜索到的设备列表
        
        # 设置通道切换信号连接
        for i, channel in enumerate(self.channels):
            channel['toggle'].toggled.connect(lambda checked, ch=i+1: self._on_channel_toggle(checked, ch))
        

        
        # 初始化设备搜索定时器
        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._search_devices)
        self.search_timer.setSingleShot(True)
        
    def _create_top_bar(self):
        """创建顶部仪器信息栏，参照pmu_oscp_ui的风格"""
        top_group = QGroupBox("PMU System")
        top_layout = QGridLayout()
        top_layout.setSpacing(8)

        # 状态指示
        self.connection_status = QLabel("● 就绪")
        self.connection_status.setStyleSheet("color:#00a859; font-weight:bold;")

        # 设备信息
        self.instrument_name = QLabel("N6705C + MSO64B")

        # 设备选择下拉菜单（VISA资源）
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(250)
        # 初始化下拉菜单（设置默认设备）
        self.device_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
        self.device_combo.setToolTip("选择要连接的设备")

        # 控制按钮
        self.search_btn = QPushButton("搜索")
        self.connect_btn = QPushButton("连接")
        self.disconnect_btn = QPushButton("断开")
        self.disconnect_btn.setEnabled(False)  # 初始状态为禁用


        # 布局设置
        top_layout.addWidget(QLabel("状态"), 0, 0)
        top_layout.addWidget(self.connection_status, 0, 1)

        top_layout.addWidget(QLabel("设备"), 0, 2)
        top_layout.addWidget(self.instrument_name, 0, 3, 1, 3)

        top_layout.addWidget(QLabel("资源"), 1, 0)
        top_layout.addWidget(self.device_combo, 1, 1, 1, 3)

        top_layout.addWidget(self.search_btn, 1, 4)
        top_layout.addWidget(self.connect_btn, 1, 5)
        top_layout.addWidget(self.disconnect_btn, 1, 6)

        # 连接按钮点击事件
        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self._on_disconnect)

        top_group.setLayout(top_layout)
        return top_group

    def _setup_style(self):
        """设置界面样式，与pmu_oscp_ui保持一致"""
        # 设置字体
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        # 设置样式表
        self.setStyleSheet("""
        QWidget {
            background-color: #13161a;
            color: #d0d0d0;
        }

        QGroupBox {
            border: 1px solid #2a2f36;
            border-radius: 6px;
            margin-top: 8px;
            background-color: #1b1f24;
            padding: 8px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #9aa0a6;
        }

        QPushButton {
            background-color: #2a2f36;
            border: 1px solid #3a3f45;
            border-radius: 4px;
            padding: 6px 14px;
        }

        QPushButton:hover {
            background-color: #3a3f45;
        }

        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #2a2f36;
            border: 1px solid #444;
            border-radius: 4px;
            padding: 4px 6px;
        }

        QLabel {
            color: #c8c8c8;
        }
        """)
    
    def _create_layout(self):
        """创建布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        # 顶部仪器信息栏
        self.top_bar = self._create_top_bar()
        main_layout.addWidget(self.top_bar)
        # 通道控制区域
        channels_widget = QWidget()
        channels_layout = QGridLayout(channels_widget)
        channels_layout.setSpacing(10)
        channels_layout.setContentsMargins(10, 10, 10, 10)  # 顶部边距调小
        self.channels = []
        setting_widget = self._create_setting_widget()
        channels_layout.addWidget(setting_widget, 0, 0)
        main_layout.addWidget(channels_widget, 1)  # 占满剩余空间
        
    def _create_setting_widget(self):
        """创建设置控件"""
        setting_frame = QFrame()
        # setting_frame.setFixedHeight(400)
        setting_frame.setStyleSheet("""
            QFrame {
                background-color: #202328;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 0px;
            }
        """)
        setting_layout = QVBoxLayout(setting_frame)
        setting_layout.setAlignment(Qt.AlignTop) # ⭐ 防止内容被拉散
        setting_layout.setContentsMargins(8, 4, 8, 8)   # 调小顶部空白
        setting_layout.setSpacing(6)
        # 通道标题栏
        setting_header = QHBoxLayout()
        setting_header.setContentsMargins(0, 0, 0, 0)   # 去掉header额外空白
        setting_header.setSpacing(6)
        
        # 通道选择下拉框
        channel_label = QLabel("Channel:")
        channel_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        setting_header.addWidget(channel_label)
        
        self.channel_combo = QComboBox()
        self.channel_combo.setStyleSheet("""
            QComboBox {
                background-color: #32353a;
                color: #c8c8c8;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 60px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #555;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url("data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 6'><polygon points='0,0 10,0 5,6' fill='%23c8c8c8'/></svg>");
                width: 8px;
                height: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #32353a;
                color: #c8c8c8;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        # 添加1-4通道选项
        for i in range(1, 5):
            self.channel_combo.addItem(str(i))
        setting_header.addWidget(self.channel_combo)

        # 通道选择下拉框
        channel_mode_label = QLabel("Mode:")
        channel_mode_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        setting_header.addWidget(channel_mode_label)
        
        self.channel_mode_combo = QComboBox()
        self.channel_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #32353a;
                color: #c8c8c8;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
                min-width: 60px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #555;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url("data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 6'><polygon points='0,0 10,0 5,6' fill='%23c8c8c8'/></svg>");
                width: 8px;
                height: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #32353a;
                color: #c8c8c8;
                border: 1px solid #555;
                border-radius: 4px;
            }
        """)
        # 添加1-4通道选项
        #设置模式
        #mode option: PS4Q |PS2Q |PS1Q |BATTery |CHARger |CCLoad |CVLoad |VMETer |AMETer
        self.channel_mode_combo.addItems(["PS2Q", "PS1Q", "PS4Q", "BATTery", "CHARger", "CCLoad", "CVLoad", "VMETer", "AMETer"])
        setting_header.addWidget(self.channel_mode_combo)


        # set mode button
        channel_toggle = QPushButton("SET")
        channel_toggle.setStyleSheet("""
            QPushButton {
                background-color: #00a859;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                min-width: 60px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #00b869;
            }
        """)
        # 连接ON按钮的点击事件
        channel_toggle.clicked.connect(self._set_mode)
        setting_header.addWidget(channel_toggle)


        setting_header.addStretch()
        # ON 按钮（只负责打开通道）
        channel_toggle = QPushButton("ON")
        channel_toggle.setStyleSheet("""
            QPushButton {
                background-color: #00a859;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                min-width: 60px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #00b869;
            }
        """)
        # 连接ON按钮的点击事件
        channel_toggle.clicked.connect(self._on_channel_toggle)
        setting_header.addWidget(channel_toggle)
        
        # OFF按钮
        off_button = QPushButton("OFF")
        off_button.setStyleSheet("""
            QPushButton {
                background-color: #e53935;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                min-width: 60px;
                font-size: 11px;
                margin-left: 5px;
            }
            QPushButton:hover {
                background-color: #f54945;
            }
        """)
        off_button.clicked.connect(self._on_off_button_clicked)
        setting_header.addWidget(off_button)
        setting_header.setContentsMargins(0, 0, 0, 0)
        setting_layout.addLayout(setting_header)
        
        # 参数显示区域 - 创建一个大的容器frame
        params_container = QFrame()
        params_container.setStyleSheet("""
            QFrame {
                background-color: #1a1d21;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        params_grid = QGridLayout(params_container)
        params_grid.setSpacing(6)
        
        # 电压显示
        voltage_frame = QFrame()
        voltage_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 10px;
            }
        """)
        voltage_layout = QVBoxLayout(voltage_frame)
        voltage_layout.setSpacing(2)
        voltage_label = QLabel("Voltage (V)")
        voltage_label.setStyleSheet("font-size: 11px; color: #888; margin-bottom: 5px;")
        voltage_layout.addWidget(voltage_label)
        
        voltage_value = QLineEdit("0.0000")
        voltage_value.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                color: #c8c8c8;
                background-color: #2a2d32;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 8px;
            }
        """)
        voltage_value.setFixedHeight(30)
        voltage_layout.addWidget(voltage_value)
        
        params_grid.addWidget(voltage_frame, 0, 0)
        
        # 电流显示
        current_frame = QFrame()
        current_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 10px;
            }
        """)
        current_layout = QVBoxLayout(current_frame)
        current_layout.setSpacing(2)
        current_label = QLabel("Current (A)")
        current_label.setStyleSheet("font-size: 11px; color: #888; margin-bottom: 5px;")
        current_layout.addWidget(current_label)
        
        current_value = QLineEdit("0.0000")
        current_value.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                color: #c8c8c8;
                background-color: #2a2d32;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 8px;
            }
        """)
        current_value.setFixedHeight(30)
        current_layout.addWidget(current_value)
        
        params_grid.addWidget(current_frame, 0, 1)
        

        # 限流显示
        limit_current_frame = QFrame()
        limit_current_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 10px;
            }
        """)
        limit_current_layout = QVBoxLayout(limit_current_frame)
        limit_current_layout.setSpacing(2)
        limit_current_label = QLabel("+/-Lim (A)")
        limit_current_label.setStyleSheet("font-size: 11px; color: #888; margin-bottom: 5px;")
        limit_current_layout.addWidget(limit_current_label)
        
        limit_current_value = QLineEdit("0.0000")
        limit_current_value.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                color: #c8c8c8;
                background-color: #2a2d32;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 8px;
            }
        """)
        limit_current_value.setFixedHeight(30)
        limit_current_layout.addWidget(limit_current_value)
        
        params_grid.addWidget(limit_current_frame, 0, 2)



        # 按钮显示
        boutton_frame = QFrame()
        boutton_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 10px;
            }
        """)
        boutton_layout = QVBoxLayout(boutton_frame)
        boutton_layout.setSpacing(2)
        
        # 添加measure_btn到button_frame
        measure_btn = QPushButton("MEASURE")
        measure_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                min-width: 80px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        measure_btn.clicked.connect(self._on_measure_button_clicked)
        boutton_layout.addWidget(measure_btn)


        # 添加SET按钮到button_frame
        set_btn = QPushButton("SET")
        set_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                min-width: 80px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        set_btn.clicked.connect(self._on_set_button_clicked)
        boutton_layout.addWidget(set_btn)
        
        params_grid.addWidget(boutton_frame, 0, 3)
        
        setting_layout.addWidget(params_container)
        
        # 添加工具容器
        tools_container = QFrame()
        tools_container.setStyleSheet("""
            QFrame {
                background-color: #1a1d21;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setSpacing(8)
        
        # 工具标题
        tools_title = QLabel("一键调整")
        tools_title.setStyleSheet("font-weight: bold; font-size: 12px; margin-bottom: 5px;")
        tools_layout.addWidget(tools_title)
        
        # 第一行：通道选择
        channel_select_layout = QHBoxLayout()
        channel_select_layout.setSpacing(10)
        
        channel_select_label = QLabel("通道选择:")
        channel_select_label.setStyleSheet("font-size: 11px; color: #888;")
        channel_select_layout.addWidget(channel_select_label)
        
        self.channel_checkboxes = []
        for i in range(1, 5):
            checkbox = QPushButton(f"通道 {i}")
            checkbox.setCheckable(True)
            # 默认勾选后三个通道（2,3,4）
            if i in [2, 3, 4]:
                checkbox.setChecked(True)
            checkbox.setStyleSheet("""
                QPushButton {
                    background-color: #32353a;
                    color: #c8c8c8;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    min-width: 60px;
                }
                QPushButton:checked {
                    background-color: #2a82da;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #3a3d43;
                }
                QPushButton:checked:hover {
                    background-color: #3a92ea;
                }
            """)
            self.channel_checkboxes.append(checkbox)
            channel_select_layout.addWidget(checkbox)
        
        channel_select_layout.addStretch()
        tools_layout.addLayout(channel_select_layout)
        
        # 第二行：通道电压设置
        voltage_set_layout = QHBoxLayout()
        voltage_set_layout.setSpacing(10)
        
        voltage_set_label = QLabel("电压设置(V):")
        voltage_set_label.setStyleSheet("font-size: 11px; color: #888;")
        voltage_set_layout.addWidget(voltage_set_label)
        
        self.voltage_inputs = []
        default_voltages = [3.8, 0.8, 1.2, 1.8]
        for i, voltage in enumerate(default_voltages):
            input_box = QLineEdit(f"{voltage:.4f}")
            input_box.setStyleSheet("""
                QLineEdit {
                    background-color: #32353a;
                    color: #c8c8c8;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    min-width: 60px;
                }
            """)
            self.voltage_inputs.append(input_box)
            voltage_set_layout.addWidget(input_box)
        
        voltage_set_layout.addStretch()
        tools_layout.addLayout(voltage_set_layout)
        
        # 第三行：限流设置
        current_limit_layout = QHBoxLayout()
        current_limit_layout.setSpacing(10)
        
        current_limit_label = QLabel("限流设置(A):")
        current_limit_label.setStyleSheet("font-size: 11px; color: #888;")
        current_limit_layout.addWidget(current_limit_label)
        
        self.current_limit_inputs = []
        default_currents = [0.2, 0.02, 0.02, 0.02]
        for i, current in enumerate(default_currents):
            input_box = QLineEdit(f"{current:.4f}")
            input_box.setStyleSheet("""
                QLineEdit {
                    background-color: #32353a;
                    color: #c8c8c8;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                    min-width: 60px;
                }
            """)
            self.current_limit_inputs.append(input_box)
            current_limit_layout.addWidget(input_box)
        
        current_limit_layout.addStretch()
        tools_layout.addLayout(current_limit_layout)
        
        # 第四行：功能按钮
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Measure按钮
        measure_all_btn = QPushButton("Measure")
        measure_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        measure_all_btn.clicked.connect(self._on_measure_all_clicked)
        buttons_layout.addWidget(measure_all_btn)
        
        # Set按钮
        set_all_btn = QPushButton("Set")
        set_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        set_all_btn.clicked.connect(self._on_set_all_clicked)
        buttons_layout.addWidget(set_all_btn)
        
        # Auto按钮
        auto_btn = QPushButton("Auto")
        auto_btn.setStyleSheet("""
            QPushButton {
                background-color: #2a82da;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3a92ea;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        auto_btn.clicked.connect(self._on_auto_clicked)
        buttons_layout.addWidget(auto_btn)
        
        buttons_layout.addStretch()
        tools_layout.addLayout(buttons_layout)
        
        setting_layout.addWidget(tools_container)
        
        channel_data = {
            'toggle': channel_toggle,
            'off_button': off_button,
            'voltage_value': voltage_value,
            'current_value': current_value,
            'limit_current_value': limit_current_value,
            'set_btn': set_btn
        }
        
        self.channels.append(channel_data)
        
        
        return setting_frame
    
    def _init_ui_elements(self):
        """初始化UI元素"""
        # 初始化通道设置的默认值
        for i, channel in enumerate(self.channels):
            # 默认值已经在_create_channel_widget中设置
            pass

    def get_channel_settings(self, channel_num):
        """获取指定通道的设置"""
        if 1 <= channel_num <= 4 and self.channels:
            # 现在只有一个设置控件，所以总是返回第一个元素
            channel = self.channels[0]
            return {
                'enabled': channel['toggle'].isChecked(),
                'voltage_set': float(channel['voltage_value'].text()),
                'current_set': float(channel['current_value'].text()),
                'current_limit': float(channel['limit_current_value'].text())
            }
        return None
    
    def update_channel_values(self, channel_num, voltage, current, limit_current):
        """更新通道的电压、电流和限流显示"""
        if 1 <= channel_num <= 4 and self.channels:
            # 现在只有一个设置控件，所以总是使用第一个元素
            channel = self.channels[0]
            channel['voltage_value'].setText(f"{voltage:.4f}")
            channel['current_value'].setText(f"{current:.4f}")
            channel['limit_current_value'].setText(f"{limit_current:.4f}")
    
    def set_all_channels_enabled(self, enabled):
        """设置所有通道的启用状态"""
        for channel in self.channels:
            channel['toggle'].setChecked(enabled)
    
    def get_channel_toggle(self, channel_num):
        """获取指定通道的开关按钮"""
        if 1 <= channel_num <= 4 and self.channels:
            # 现在只有一个设置控件，所以总是返回第一个元素的切换开关
            return self.channels[0]['toggle']
        return None
    
    def _on_search(self):
        """搜索设备按钮点击事件"""
        self.connection_status.setText("搜索中...")
        self.connection_status.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
        
        # 禁用搜索按钮
        self.search_btn.setEnabled(False)
        
        # 启动设备搜索
        self.search_timer.start(100)  # 短暂延迟后开始搜索
    
    def _search_devices(self):
        """搜索VISA设备"""
        try:
            # 初始化VISA资源管理器，尝试不同的后端
            if self.rm is None:
                try:
                    # 先尝试默认后端
                    self.rm = pyvisa.ResourceManager()
                except Exception:
                    # 如果失败，尝试使用NI-VISA后端
                    self.rm = pyvisa.ResourceManager('@ni')
            
            # 列出所有可用设备并转换为列表
            self.available_devices = list(self.rm.list_resources()) or []
            
            # 显示找到的设备数量
            print(f"找到 {len(self.available_devices)} 个设备")
            for dev in self.available_devices:
                print(f"设备地址: {dev}")
            
            # 过滤设备：先尝试所有设备，再过滤N6705C
            compatible_devices = []
            
            # 首先，添加所有找到的设备（包括可能的N6705C）
            if self.available_devices:
                compatible_devices = self.available_devices.copy()
            
            # 然后尝试直接查询设备ID来确认是否为N6705C
            n6705c_devices = []
            for dev in compatible_devices:
                try:
                    # 尝试打开设备并查询ID
                    instr = self.rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    
                    print(f"设备 {dev} 的IDN: {idn}")
                    
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception as e:
                    print(f"查询设备 {dev} 失败: {str(e)}")
                    # 如果无法查询ID，继续保留设备在兼容列表中
                    pass
            
            # 更新设备列表到下拉菜单（只显示N6705C设备）
            self.device_combo.clear()
            
            # 仅添加N6705C设备
            n6705c_count = len(n6705c_devices)
            if n6705c_devices:
                for dev in n6705c_devices:
                    self.device_combo.addItem(dev)
                
                # 设置状态和按钮
                self.connection_status.setText(f"找到 {n6705c_count} 个N6705C设备")
                self.connection_status.setStyleSheet("color: #00a859; padding: 10px; font-weight: bold;")
                self.connect_btn.setEnabled(True)
                
                # 默认选择指定的N6705C设备
                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    # 如果默认设备存在，选择它
                    self.device_combo.setCurrentText(default_device)
                else:
                    # 否则选择第一个设备
                    self.device_combo.setCurrentIndex(0)
            else:
                # 没有找到N6705C设备
                self.device_combo.addItem("未找到N6705C设备")
                self.device_combo.setEnabled(False)
                self.connection_status.setText("未找到N6705C设备")
                self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
                self.connect_btn.setEnabled(False)
            
        except Exception as e:
            print(f"搜索过程中发生错误: {str(e)}")
            self.connection_status.setText(f"搜索失败: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.connect_btn.setEnabled(False)
        finally:
            # 启用搜索按钮
            self.search_btn.setEnabled(True)
    
    def _on_connect(self):
        """连接设备按钮点击事件"""
        self.connection_status.setText("连接中...")
        self.connection_status.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
        
        # 禁用连接按钮
        self.connect_btn.setEnabled(False)
        
        try:
            # 获取用户选择的设备地址
            device_address = self.device_combo.currentText()
            # 创建N6705C控制器实例
            self.n6705c = N6705C(device_address)
            
            # 发送*IDN?命令确认连接
            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self.is_connected = True
                self.connection_status.setText("已连接")
                self.connection_status.setStyleSheet("color: #00a859; padding: 10px; font-weight: bold;")
                
                # 更新按钮状态
                self.disconnect_btn.setEnabled(True)
                

                
                # 发射连接成功信号
                self.connection_status_changed.emit(True)

            else:
                self.connection_status.setText("设备不匹配")
                self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
                self.connect_btn.setEnabled(True)
        
        except Exception as e:
            self.connection_status.setText(f"连接失败: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.connect_btn.setEnabled(True)
    
    def _on_disconnect(self):
        """断开设备按钮点击事件"""
        self.connection_status.setText("断开中...")
        self.connection_status.setStyleSheet("color: #ff9800; padding: 10px; font-weight: bold;")
        
        # 禁用断开按钮
        self.disconnect_btn.setEnabled(False)
        
        try:

            
            # 关闭通道1
            # self.n6705c.channel_off(1)
            
            # 关闭仪器连接和资源管理器（由N6705C类内部管理）
            if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                self.n6705c.instr.close()
            if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                self.n6705c.rm.close()
            
            # 重置UI状态
            self.instrument = None
            self.n6705c = None
            self.is_connected = False
            
            self.connection_status.setText("未连接")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            
            # 更新按钮状态
            self.connect_btn.setEnabled(True)
            
            # 发射连接断开信号
            self.connection_status_changed.emit(False)
            
        except Exception as e:
            self.connection_status.setText(f"断开失败: {str(e)}")
            self.connection_status.setStyleSheet("color: #e53935; padding: 10px; font-weight: bold;")
            self.disconnect_btn.setEnabled(True)
    
    def _set_mode(self, unused_checked=False):
        if self.is_connected and self.n6705c:
            try:
                # 使用当前下拉框中选择的通道号
                channel_num = int(self.channel_combo.currentText())
                mode = self.channel_mode_combo.currentText()
                # 应用通道设置
                settings = self.get_channel_settings(channel_num)
                if settings:
                    # 设置电压
                    self.n6705c.set_mode(channel_num, mode)
                    
                    print(f"通道{channel_num}已设置为{mode}模式")
                    
            except Exception as e:
                print(f"设置通道{channel_num}模式失败: {str(e)}")

    def _on_channel_toggle(self, unused_checked=False):
        """ON按钮点击事件，只负责打开通道"""
        if self.is_connected and self.n6705c:
            try:
                # 使用当前下拉框中选择的通道号
                channel_num = int(self.channel_combo.currentText())
                
                # 应用通道设置
                settings = self.get_channel_settings(channel_num)
                if settings:
                    # # 设置电压
                    # self.n6705c.set_voltage(channel_num, settings['voltage_set'])
                    
                    # # 设置电流
                    # self.n6705c.set_current(channel_num, settings['current_set'])
                    
                    # # 设置电流限制
                    # self.n6705c.set_current_limit(channel_num, settings['current_limit'])
                    
                    # 打开通道
                    self.n6705c.channel_on(channel_num)
                    
                    print(f"通道{channel_num}已打开")
                    
            except Exception as e:
                print(f"打开通道{channel_num}失败: {str(e)}")
    
    def _on_off_button_clicked(self):
        """OFF按钮点击事件，关闭当前选择的通道"""
        if self.is_connected and self.n6705c:
            try:
                # 使用当前下拉框中选择的通道号
                channel_num = int(self.channel_combo.currentText())
                
                # 关闭通道
                self.n6705c.channel_off(channel_num)
                
                # 更新UI状态，确保ON/OFF开关显示为OFF
                self.channels[0]['toggle'].setChecked(False)
                
                print(f"通道{channel_num}已关闭")
                
            except Exception as e:
                print(f"关闭通道{channel_num}失败: {str(e)}")
    
    def _on_set_button_clicked(self):
        """SET按钮点击事件，将电压和电流限制值发送到仪器"""
        if not self.is_connected or not self.n6705c:
            return
            
        try:
            # 获取当前选择的通道号
            channel_num = int(self.channel_combo.currentText())
            
            # 获取输入的电压、电流和电流限制值
            voltage_set = float(self.channels[0]['voltage_value'].text())
            current_set = float(self.channels[0]['current_value'].text())
            limit_current_set = float(self.channels[0]['limit_current_value'].text())
            
            # 将设置发送到仪器
            self.n6705c.set_voltage(channel_num, voltage_set)
            self.n6705c.set_current(channel_num, current_set)  # 设置电流值
            self.n6705c.set_current_limit(channel_num, limit_current_set)  # 设置电流限制
            
            print(f"通道{channel_num}设置已发送 - 电压: {voltage_set}V, 电流: {current_set}A, 电流限制: {limit_current_set}A")
            
        except Exception as e:
            print(f"设置发送失败: {str(e)}")
    
    
    def _on_measure_button_clicked(self):
        """MEASURE按钮点击事件，获取当前电压和电流"""
        if not self.is_connected or not self.n6705c:
            return
            
        try:
            # 获取当前选择的通道号
            channel_num = int(self.channel_combo.currentText())
            
            # 获取电压和电流
            voltage = float(self.n6705c.measure_voltage(channel_num))
            current = float(self.n6705c.measure_current(channel_num))
            limit_current = float(self.n6705c.get_current_limit(channel_num))
            
            # 更新UI显示
            self.update_channel_values(channel_num, voltage, current, limit_current)
            
            print(f"通道{channel_num}测量值 - 电压: {voltage:.4f}V, 电流: {current:.4f}A, 电流限制: {limit_current:.4f}A")
            
        except Exception as e:
            print(f"测量失败: {str(e)}")
    
    
    def set_all_channels_enabled(self, enabled):
        """设置所有通道的启用状态"""
        super().set_all_channels_enabled(enabled)
        
        # 如果已连接，同步到实际仪器
        if self.is_connected and self.n6705c:
            # 只处理通道1
            channel_num = 1
            if enabled:
                # 应用设置后开启通道
                settings = self.get_channel_settings(channel_num)
                if settings:
                    self.n6705c.set_voltage(channel_num, settings['voltage_set'])
                    self.n6705c.set_current_limit(channel_num, settings['current_limit'])
                    self.n6705c.channel_on(channel_num)
            else:
                # 关闭通道
                self.n6705c.channel_off(channel_num)
    
    def _on_measure_all_clicked(self):
        """Measure按钮点击事件，将选择的通道设置为电压表模式"""
        if not self.is_connected or not self.n6705c:
            return
            
        try:
            # 获取所有勾选的通道
            selected_channels = []
            for i, checkbox in enumerate(self.channel_checkboxes):
                if checkbox.isChecked():
                    selected_channels.append(i + 1)
            
            if not selected_channels:
                print("未选择任何通道")
                return
            
            # 将选中的通道设置为电压表模式
            for channel_num in selected_channels:
                self.n6705c.set_mode(channel_num, "VMETer")
                print(f"通道{channel_num}已设置为电压表模式")
                
        except Exception as e:
            print(f"设置电压表模式失败: {str(e)}")
    
    def _on_set_all_clicked(self):
        """Set按钮点击事件，将输入的参数设置到勾选的通道里面"""
        if not self.is_connected or not self.n6705c:
            return
            
        try:
            # 获取所有勾选的通道
            selected_channels = []
            for i, checkbox in enumerate(self.channel_checkboxes):
                if checkbox.isChecked():
                    selected_channels.append(i + 1)
            
            if not selected_channels:
                print("未选择任何通道")
                return
            
            # 获取输入的电压和电流限制值
            voltages = []
            current_limits = []
            for i in range(4):
                voltages.append(float(self.voltage_inputs[i].text()))
                current_limits.append(float(self.current_limit_inputs[i].text()))
            
            # 将设置发送到选中的通道
            for channel_num in selected_channels:
                idx = channel_num - 1
                voltage = voltages[idx]
                current_limit = current_limits[idx]
                self.n6705c.set_mode(channel_num, "PS2Q")
                self.n6705c.set_voltage(channel_num, voltage)
                self.n6705c.set_current_limit(channel_num, current_limit)
                self.n6705c.channel_on(channel_num)
                
                print(f"通道{channel_num}设置已发送 - 电压: {voltage}V, 电流限制: {current_limit}A")
                
        except Exception as e:
            print(f"设置发送失败: {str(e)}")
    
    def _on_auto_clicked(self):
        """Auto按钮点击事件：
        1. 先通电压模式测试勾选通道的模式
        2. 再在测试的结果上面加0.01V
        3. 设置勾选的通道为PS2Q
        4. 再将这个电压到勾选的通道上面
        5. 并将对应Channel On
        """
        if not self.is_connected or not self.n6705c:
            return
            
        try:
            # 获取所有勾选的通道
            selected_channels = []
            for i, checkbox in enumerate(self.channel_checkboxes):
                if checkbox.isChecked():
                    selected_channels.append(i + 1)
            
            if not selected_channels:
                print("未选择任何通道")
                return
            
            # 对每个选中的通道执行Auto操作
            for channel_num in selected_channels:
                # 1. 先将通道设置为电压表模式，测量当前电压
                self.n6705c.set_mode(channel_num, "VMETer")
                measured_voltage = float(self.n6705c.measure_voltage(channel_num))
                print(f"通道{channel_num}测量电压: {measured_voltage:.4f}V")
                
                # 2. 在测量结果上加0.01V
                new_voltage = measured_voltage + 0.01
                print(f"通道{channel_num}新电压: {new_voltage:.4f}V")
                
                # 3. 设置通道为PS2Q模式
                self.n6705c.set_mode(channel_num, "PS2Q")
                print(f"通道{channel_num}已设置为PS2Q模式")
                
                # 4. 设置新的电压值
                self.n6705c.set_voltage(channel_num, new_voltage)
                print(f"通道{channel_num}电压已设置为: {new_voltage:.4f}V")
                
                # 5. 打开通道
                self.n6705c.channel_on(channel_num)
                print(f"通道{channel_num}已打开")
                
        except Exception as e:
            print(f"Auto操作失败: {str(e)}")


# Demo显示函数
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 创建N6705C测试主UI
    n6705c_ui_test = N6705CUI()
    n6705c_ui_test.setWindowTitle("N6705C测试系统")
    n6705c_ui_test.setGeometry(100, 100, 1200, 800)
    n6705c_ui_test.show()
    
    sys.exit(app.exec())

