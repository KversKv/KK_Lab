#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU DCDC Efficiency测试UI组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QComboBox, QLabel, QLineEdit, QGridLayout, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
import pyvisa
from instruments.n6705c import N6705C


class PMUDCDCEfficiencyUI(QWidget):
    """PMU DCDC Efficiency测试UI组件"""
    
    # 定义信号
    connection_status_changed = Signal(bool)  # 参数表示是否连接成功
    
    def __init__(self):
        super().__init__()
        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        
        # 初始化N6705C相关属性
        self.rm = None  # VISA资源管理器
        self.n6705c = None  # N6705C控制器
        self.is_connected = False
        self.available_devices = []  # 搜索到的设备列表
        
        # 测试线程管理
        self.is_test_running = False
        self.test_thread = None  # 用于存储测试线程实例
        
        # 初始化设备搜索定时器
        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._search_devices)
        self.search_timer.setSingleShot(True)
        
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
                background-color: #202328;
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
            QPushButton#start_test_btn {
                background-color: #00a859;
                color: white;
            }
            QPushButton#start_test_btn:hover {
                background-color: #00b869;
            }
            QPushButton#stop_test_btn {
                background-color: #e53935;
                color: white;
            }
            QPushButton#stop_test_btn:hover {
                background-color: #f54945;
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
            QSpinBox, QDoubleSpinBox {
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                background-color: #32353a;
                color: #c8c8c8;
            }
            QLabel {
                color: #c8c8c8;
            }
            QCheckBox {
                color: #c8c8c8;
            }
            QFrame {
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #202328;
            }
        """)
    
    def _create_layout(self):
        """创建布局"""
        main_layout = QVBoxLayout(self)
        
        # 设备连接区域
        top_group = QGroupBox("PMU System")
        top_layout = QGridLayout()
        top_layout.setSpacing(8)

        self.system_status_label = QLabel("● 就绪")
        self.system_status_label.setStyleSheet("color:#00a859; font-weight:bold;")

        self.instrument_info_label = QLabel("N6705C + MSO64B")

        self.visa_resource_combo = QComboBox()
        # 初始化下拉菜单（设置默认设备）
        self.visa_resource_combo.addItem("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
        self.search_btn = QPushButton("搜索")
        self.connect_btn = QPushButton("连接")
        self.disconnect_btn = QPushButton("断开")

        top_layout.addWidget(QLabel("状态"), 0, 0)
        top_layout.addWidget(self.system_status_label, 0, 1)

        top_layout.addWidget(QLabel("设备"), 0, 2)
        top_layout.addWidget(self.instrument_info_label, 0, 3, 1, 3)

        top_layout.addWidget(QLabel("资源"), 1, 0)
        top_layout.addWidget(self.visa_resource_combo, 1, 1, 1, 3)

        top_layout.addWidget(self.search_btn, 1, 4)
        top_layout.addWidget(self.connect_btn, 1, 5)
        top_layout.addWidget(self.disconnect_btn, 1, 6)

        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)
        
        # 测试配置区域
        config_group = QGroupBox("DCDC Efficiency测试配置")
        config_layout = QGridLayout()
        config_layout.setSpacing(15)
        config_layout.setContentsMargins(20, 15, 20, 15)
        
        # DCDC通道选择
        config_layout.addWidget(QLabel("DCDC通道:"), 0, 0)
        self.dcdc_channel_combo = QComboBox()
        self.dcdc_channel_combo.addItems(["DC1", "DC2", "DC3", "DC4"])
        config_layout.addWidget(self.dcdc_channel_combo, 0, 1)
        
        # 输入电压
        config_layout.addWidget(QLabel("输入电压 (V):"), 0, 2)
        self.input_voltage_spin = QDoubleSpinBox()
        self.input_voltage_spin.setRange(0.0, 20.0)
        self.input_voltage_spin.setSingleStep(0.1)
        self.input_voltage_spin.setValue(5.0)
        config_layout.addWidget(self.input_voltage_spin, 0, 3)
        
        # 输出电压范围
        config_layout.addWidget(QLabel("输出电压范围 (V):"), 1, 0)
        self.output_voltage_min_spin = QDoubleSpinBox()
        self.output_voltage_min_spin.setRange(0.0, 20.0)
        self.output_voltage_min_spin.setSingleStep(0.1)
        self.output_voltage_min_spin.setValue(1.0)
        config_layout.addWidget(self.output_voltage_min_spin, 1, 1)
        
        config_layout.addWidget(QLabel("到"), 1, 2)
        
        self.output_voltage_max_spin = QDoubleSpinBox()
        self.output_voltage_max_spin.setRange(0.0, 20.0)
        self.output_voltage_max_spin.setSingleStep(0.1)
        self.output_voltage_max_spin.setValue(5.0)
        config_layout.addWidget(self.output_voltage_max_spin, 1, 3)
        
        # 电压步进
        config_layout.addWidget(QLabel("电压步进 (V):"), 2, 0)
        self.voltage_step_spin = QDoubleSpinBox()
        self.voltage_step_spin.setRange(0.01, 1.0)
        self.voltage_step_spin.setSingleStep(0.01)
        self.voltage_step_spin.setValue(0.1)
        config_layout.addWidget(self.voltage_step_spin, 2, 1)
        
        # 负载电流
        config_layout.addWidget(QLabel("负载电流 (mA):"), 2, 2)
        self.load_current_spin = QDoubleSpinBox()
        self.load_current_spin.setRange(0.0, 5000.0)
        self.load_current_spin.setSingleStep(10.0)
        self.load_current_spin.setValue(100.0)
        config_layout.addWidget(self.load_current_spin, 2, 3)
        
        # 测量次数
        config_layout.addWidget(QLabel("测量次数:"), 3, 0)
        self.measure_count_spin = QSpinBox()
        self.measure_count_spin.setRange(1, 100)
        self.measure_count_spin.setValue(5)
        config_layout.addWidget(self.measure_count_spin, 3, 1)
        
        # 采样间隔
        config_layout.addWidget(QLabel("采样间隔 (ms):"), 3, 2)
        self.sample_interval_spin = QSpinBox()
        self.sample_interval_spin.setRange(10, 1000)
        self.sample_interval_spin.setValue(100)
        config_layout.addWidget(self.sample_interval_spin, 3, 3)
        
        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)
        
        # 测试控制区域
        control_group = QGroupBox("测试控制")
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        control_layout.setContentsMargins(20, 15, 20, 15)
        
        self.start_test_btn = QPushButton("开始测试")
        self.start_test_btn.setObjectName("start_test_btn")
        self.stop_test_btn = QPushButton("停止测试")
        self.stop_test_btn.setObjectName("stop_test_btn")
        self.stop_test_btn.setEnabled(False)
        
        control_layout.addWidget(self.start_test_btn)
        control_layout.addWidget(self.stop_test_btn)
        control_layout.addStretch()
        
        self.save_config_btn = QPushButton("保存配置")
        self.load_config_btn = QPushButton("加载配置")
        
        control_layout.addWidget(self.save_config_btn)
        control_layout.addWidget(self.load_config_btn)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 测试结果区域
        result_group = QGroupBox("测试结果")
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(20, 15, 20, 15)
        
        # 结果图表区域
        self.chart_placeholder = QFrame()
        self.chart_placeholder.setMinimumHeight(300)
        self.chart_placeholder.setStyleSheet("""
            QFrame {
                background-color: #1a1d21;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        chart_layout = QVBoxLayout(self.chart_placeholder)
        chart_label = QLabel("效率曲线图表区域")
        chart_label.setAlignment(Qt.AlignCenter)
        chart_label.setStyleSheet("color: #666; font-size: 14px;")
        chart_layout.addWidget(chart_label)
        result_layout.addWidget(self.chart_placeholder)
        
        # 结果数据区域
        data_layout = QGridLayout()
        data_layout.setSpacing(15)
        
        # 效率结果
        self.efficiency_label = QLabel("平均效率: ---")
        self.efficiency_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        data_layout.addWidget(self.efficiency_label, 0, 0)
        
        # 最大效率
        self.max_efficiency_label = QLabel("最大效率: ---")
        self.max_efficiency_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        data_layout.addWidget(self.max_efficiency_label, 0, 1)
        
        # 效率对应电压
        self.efficiency_voltage_label = QLabel("最大效率电压: ---")
        self.efficiency_voltage_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        data_layout.addWidget(self.efficiency_voltage_label, 1, 0)
        
        # 功耗
        self.power_label = QLabel("总功耗: ---")
        self.power_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        data_layout.addWidget(self.power_label, 1, 1)
        
        result_layout.addLayout(data_layout)
        
        # 导出按钮
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        self.export_result_btn = QPushButton("导出结果")
        export_layout.addWidget(self.export_result_btn)
        
        result_layout.addLayout(export_layout)
        
        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)
        
        main_layout.addStretch()
    
    def _init_ui_elements(self):
        """初始化UI元素"""
        # 设置默认值和初始状态
        pass
    
    def get_test_config(self):
        """获取测试配置"""
        return {
            'dcdc_channel': self.dcdc_channel_combo.currentText(),
            'input_voltage': self.input_voltage_spin.value(),
            'output_voltage_min': self.output_voltage_min_spin.value(),
            'output_voltage_max': self.output_voltage_max_spin.value(),
            'voltage_step': self.voltage_step_spin.value(),
            'load_current': self.load_current_spin.value(),
            'measure_count': self.measure_count_spin.value(),
            'sample_interval': self.sample_interval_spin.value()
        }
    
    def set_test_running(self, running):
        """设置测试运行状态"""
        self.start_test_btn.setEnabled(not running)
        self.stop_test_btn.setEnabled(running)
        
        # 禁用/启用配置控件
        widgets = [
            self.dcdc_channel_combo,
            self.input_voltage_spin,
            self.output_voltage_min_spin,
            self.output_voltage_max_spin,
            self.voltage_step_spin,
            self.load_current_spin,
            self.measure_count_spin,
            self.sample_interval_spin,
            self.save_config_btn,
            self.load_config_btn,
            self.visa_resource_combo,
            self.search_btn,
            self.connect_btn,
            self.disconnect_btn
        ]
        
        for widget in widgets:
            widget.setEnabled(not running)
    
    def update_test_result(self, result):
        """更新测试结果"""
        if 'efficiency' in result:
            self.efficiency_label.setText(f"平均效率: {result['efficiency']:.2f}%")
        if 'max_efficiency' in result:
            self.max_efficiency_label.setText(f"最大效率: {result['max_efficiency']:.2f}%")
        if 'max_efficiency_voltage' in result:
            self.efficiency_voltage_label.setText(f"最大效率电压: {result['max_efficiency_voltage']:.2f} V")
        if 'total_power' in result:
            self.power_label.setText(f"总功耗: {result['total_power']:.4f} W")
    
    def clear_results(self):
        """清空测试结果"""
        self.efficiency_label.setText("平均效率: ---")
        self.max_efficiency_label.setText("最大效率: ---")
        self.efficiency_voltage_label.setText("最大效率电压: ---")
        self.power_label.setText("总功耗: ---")
    
    def set_system_status(self, status, is_error=False):
        """设置系统状态"""
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setStyleSheet("color: #e53935; font-weight: bold;")
        elif status == "测试进行中":
            self.system_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        else:
            self.system_status_label.setStyleSheet("color: #00a859; font-weight: bold;")
    
    def update_instrument_info(self, instrument_info):
        """更新连接的仪器信息"""
        self.instrument_info_label.setText(instrument_info)
    

    
    def _on_search(self):
        """搜索N6705C设备按钮点击事件"""
        self.set_system_status("搜索中...")
        
        # 禁用搜索按钮
        self.search_btn.setEnabled(False)
        
        # 启动设备搜索
        self.search_timer.start(100)  # 短暂延迟后开始搜索
    
    def _search_devices(self):
        """搜索N6705C设备"""
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
                    
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception as e:
                    # 如果无法查询ID，继续保留设备在兼容列表中
                    pass
            
            # 更新设备列表到下拉菜单（只显示N6705C设备）
            self.visa_resource_combo.clear()
            
            # 仅添加N6705C设备
            n6705c_count = len(n6705c_devices)
            if n6705c_devices:
                for dev in n6705c_devices:
                    self.visa_resource_combo.addItem(dev)
                
                # 设置状态和按钮
                self.set_system_status(f"找到 {n6705c_count} 个N6705C设备")
                self.connect_btn.setEnabled(True)
                
                # 默认选择指定的N6705C设备
                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    # 如果默认设备存在，选择它
                    self.visa_resource_combo.setCurrentText(default_device)
                else:
                    # 否则选择第一个设备
                    self.visa_resource_combo.setCurrentIndex(0)
            else:
                # 没有找到N6705C设备
                self.visa_resource_combo.addItem("未找到N6705C设备")
                self.visa_resource_combo.setEnabled(False)
                self.set_system_status("未找到N6705C设备", is_error=True)
                self.connect_btn.setEnabled(False)
            
        except Exception as e:
            print(f"搜索过程中发生错误: {str(e)}")
            self.set_system_status(f"搜索失败: {str(e)}", is_error=True)
            self.connect_btn.setEnabled(False)
        finally:
            # 启用搜索按钮
            self.search_btn.setEnabled(True)
    
    def _on_connect(self):
        """连接N6705C设备按钮点击事件"""
        self.set_system_status("连接中...")
        
        # 禁用连接按钮
        self.connect_btn.setEnabled(False)
        
        try:
            # 获取用户选择的设备地址
            device_address = self.visa_resource_combo.currentText()
            # 创建N6705C控制器实例
            self.n6705c = N6705C(device_address)
            
            # 发送*IDN?命令确认连接
            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self.is_connected = True
                self.set_system_status("已连接")
                
                # 更新按钮状态
                self.disconnect_btn.setEnabled(True)
                self.search_btn.setEnabled(False)  # 连接后禁用搜索
                
                # 更新仪器信息
                self.instrument_info_label.setText(f"N6705C ({device_address.split('::')[1]}) + MSO64B")
                
                # 发射连接成功信号
                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("设备不匹配", is_error=True)
                self.connect_btn.setEnabled(True)
        
        except Exception as e:
            self.set_system_status(f"连接失败: {str(e)}", is_error=True)
            self.connect_btn.setEnabled(True)
    
    def _on_disconnect(self):
        """断开N6705C设备按钮点击事件"""
        self.set_system_status("断开中...")
        
        # 禁用断开按钮
        self.disconnect_btn.setEnabled(False)
        
        try:
            # 关闭仪器连接和资源管理器（由N6705C类内部管理）
            if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                self.n6705c.instr.close()
            if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                self.n6705c.rm.close()
            
            # 重置UI状态
            self.n6705c = None
            self.is_connected = False
            
            self.set_system_status("未连接")
            
            # 更新按钮状态
            self.connect_btn.setEnabled(True)
            self.search_btn.setEnabled(True)
            
            # 恢复仪器信息
            self.instrument_info_label.setText("N6705C + MSO64B")
            
            # 发射连接断开信号
            self.connection_status_changed.emit(False)
            
        except Exception as e:
            self.set_system_status(f"断开失败: {str(e)}", is_error=True)
            self.disconnect_btn.setEnabled(True)
    
    def get_n6705c_instance(self):
        """获取N6705C控制器实例"""
        return self.n6705c
    
    def is_n6705c_connected(self):
        """检查N6705C是否已连接"""
        return self.is_connected
