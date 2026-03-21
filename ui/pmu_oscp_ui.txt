#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU OSCP测试UI组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QComboBox, QLabel, QLineEdit, QGridLayout, 
    QSpinBox, QDoubleSpinBox, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont
import pyvisa
import sys
import time
from pathlib import Path
from instruments.n6705c import N6705C

# 添加I2C相关模块路径
i2c_lib_path = Path(__file__).parent.parent / "lib" / "i2c"
sys.path.insert(0, str(i2c_lib_path))

# 导入I2C接口
from i2c_interface_x64 import I2CInterface
from Bes_I2CIO_Interface import I2CSpeedMode, I2CWidthFlag



class TestThread(QThread):
    """测试线程类，用于在后台运行测试逻辑"""
    
    # 定义信号
    status_update = Signal(str, bool)  # 参数：状态消息，是否为错误
    result_update = Signal(str, float)  # 参数：结果类型，结果值
    test_finished = Signal(bool)  # 参数：测试是否成功完成
    
    def __init__(self, test_type, n6705c, **kwargs):
        super().__init__()
        self.test_type = test_type
        self.n6705c = n6705c
        self.kwargs = kwargs
        self.is_running = True
        
    def run(self):
        """运行测试逻辑"""
        try:
            if self.test_type == "OVP":
                self.run_ovp_test()
            elif self.test_type == "UVP":
                self.run_uvp_test()
            elif self.test_type == "OCP":
                self.run_ocp_test()
            elif self.test_type == "SCP":
                self.run_scp_test()
            self.test_finished.emit(True)
        except Exception as e:
            self.status_update.emit(f"测试失败: {str(e)}", True)
            self.test_finished.emit(False)
    
    def stop(self):
        """停止测试"""
        self.is_running = False
    
    def run_ovp_test(self):
        """运行OVP测试"""
        vbat_channel = int(self.kwargs.get("power_channel", 1))
        vol_channel = int(self.kwargs.get("test_channel", 2))
        start_voltage = self.kwargs.get("voltage_start", 0.7)
        end_voltage = self.kwargs.get("voltage_end", 1.5)
        step_voltage = self.kwargs.get("voltage_step", 0.1)
        
        self.status_update.emit("执行OVP测试...", False)
        self.n6705c.set_mode(vol_channel, "PS2Q")
        self.n6705c.set_voltage(vol_channel, start_voltage)
        self.n6705c.channel_on(vol_channel)
        
        time.sleep(0.5)
        cnt_voltage = start_voltage
        
        while cnt_voltage <= end_voltage + 0.05 and self.is_running:
            current_before = float(self.n6705c.measure_current(vbat_channel))
            self.n6705c.set_voltage(vol_channel, cnt_voltage)
            
            # 使用QThread.msleep代替time.sleep，避免阻塞线程事件循环
            QThread.msleep(500)
            
            current_after = float(self.n6705c.measure_current(vbat_channel))
            
            if current_after < current_before - 0.00001:
                self.status_update.emit(f"OVP触发，电压: {cnt_voltage:.3f} V", False)
                self.result_update.emit("保护电压", cnt_voltage)
                break
            
            cnt_voltage += step_voltage
    
    def run_uvp_test(self):
        """运行UVP测试"""
        vbat_channel = int(self.kwargs.get("power_channel", 1))
        vol_channel = int(self.kwargs.get("test_channel", 2))
        start_voltage = self.kwargs.get("voltage_start", 0.7)
        end_voltage = self.kwargs.get("voltage_end", 1.5)
        step_voltage = self.kwargs.get("voltage_step", 0.1)
        
        self.status_update.emit("执行UVP测试...", False)
        self.n6705c.set_mode(vol_channel, "CVLoad")
        self.n6705c.set_voltage(vol_channel, end_voltage)
        self.n6705c.channel_on(vol_channel)
        
        time.sleep(0.5)
        cnt_voltage = end_voltage
        
        while cnt_voltage >= start_voltage - 0.05 and self.is_running:
            current_before = float(self.n6705c.measure_current(vbat_channel))
            self.n6705c.set_voltage(vol_channel, cnt_voltage)
            
            # 使用QThread.msleep代替time.sleep，避免阻塞线程事件循环
            QThread.msleep(100)
            
            current_after = float(self.n6705c.measure_current(vbat_channel))
            
            if current_after < current_before - 0.01:
                self.status_update.emit(f"UVP触发，电压: {cnt_voltage:.3f} V", False)
                self.result_update.emit("保护电压", cnt_voltage)
                break
            
            cnt_voltage -= step_voltage
    
    def run_ocp_test(self):
        """运行OCP测试（待实现）"""
        self.status_update.emit("OCP测试功能尚未实现", False)
    
    def run_scp_test(self):
        """运行SCP测试（待实现）"""
        self.status_update.emit("SCP测试功能尚未实现", False)


class PMUOSCPUI(QWidget):
    """PMU OSCP测试UI组件"""
    
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
        font = QFont("Segoe UI", 9)
        self.setFont(font)

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

        QPushButton#start_test_btn {
            background-color: #00a859;
            color: white;
        }

        QPushButton#stop_test_btn {
            background-color: #e53935;
            color: white;
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
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ================== 顶部：设备连接 ==================
        top_group = QGroupBox("PMU System")
        top_layout = QGridLayout()
        top_layout.setSpacing(8)

        self.system_status_label = QLabel("● 就绪")
        self.system_status_label.setStyleSheet("color:#00a859; font-weight:bold;")

        self.instrument_info_label = QLabel("N6705C + MSO64B")

        self.visa_resource_combo = QComboBox()
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

        # ================== 中部：配置 + 控制 ==================
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(10)

        # -------- 左：OSCP参数 --------
        config_group = QGroupBox("OSCP Config")
        config_layout = QGridLayout()
        config_layout.setSpacing(6)

        self.test_type_combo = QComboBox()
        self.test_type_combo.addItems(["OCP", "SCP", "OVP", "UVP"])

        self.power_channel_combo = QComboBox()
        self.power_channel_combo.addItems(["1", "2", "3", "4"])

        self.test_channel_combo = QComboBox()
        self.test_channel_combo.addItems(["1", "2", "3", "4"])

        self.start_spin = QDoubleSpinBox()
        self.end_spin = QDoubleSpinBox()
        self.step_spin = QDoubleSpinBox()

        self.device_addr_spin = QSpinBox()
        self.reg_addr_spin = QSpinBox()
        self.msb_spin = QSpinBox()
        self.lsb_spin = QSpinBox()
        self.ocp_spin = QDoubleSpinBox()

        # 左侧参数
        config_layout.addWidget(QLabel("Type"), 0, 0)
        config_layout.addWidget(self.test_type_combo, 0, 1)

        config_layout.addWidget(QLabel("Power CH"), 1, 0)
        config_layout.addWidget(self.power_channel_combo, 1, 1)

        config_layout.addWidget(QLabel("Test CH"), 2, 0)
        config_layout.addWidget(self.test_channel_combo, 2, 1)

        config_layout.addWidget(QLabel("Start(A)"), 3, 0)
        config_layout.addWidget(self.start_spin, 3, 1)

        config_layout.addWidget(QLabel("End(A)"), 4, 0)
        config_layout.addWidget(self.end_spin, 4, 1)

        config_layout.addWidget(QLabel("Step(A)"), 5, 0)
        config_layout.addWidget(self.step_spin, 5, 1)

        # 右侧寄存器参数
        config_layout.addWidget(QLabel("Dev Addr"), 0, 2)
        config_layout.addWidget(self.device_addr_spin, 0, 3)

        config_layout.addWidget(QLabel("Reg Addr"), 1, 2)
        config_layout.addWidget(self.reg_addr_spin, 1, 3)

        config_layout.addWidget(QLabel("MSB"), 2, 2)
        config_layout.addWidget(self.msb_spin, 2, 3)

        config_layout.addWidget(QLabel("LSB"), 3, 2)
        config_layout.addWidget(self.lsb_spin, 3, 3)

        config_layout.addWidget(QLabel("OCP(A)"), 4, 2)
        config_layout.addWidget(self.ocp_spin, 4, 3)

        config_group.setLayout(config_layout)

        # -------- 右：控制区 --------
        control_group = QGroupBox("Control")
        control_layout = QVBoxLayout()
        control_layout.setSpacing(8)

        self.start_test_btn = QPushButton("START")
        self.start_test_btn.setObjectName("start_test_btn")

        self.stop_test_btn = QPushButton("STOP")
        self.stop_test_btn.setObjectName("stop_test_btn")

        self.single_test_btn = QPushButton("SINGLE")
        self.iteration_test_btn = QPushButton("LOOP")
        self.test_btn = QPushButton("DEBUG")

        self.save_btn = QPushButton("保存配置")
        self.load_btn = QPushButton("加载配置")

        control_layout.addWidget(self.start_test_btn)
        control_layout.addWidget(self.stop_test_btn)
        control_layout.addWidget(self.single_test_btn)
        control_layout.addWidget(self.iteration_test_btn)
        control_layout.addWidget(self.test_btn)
        control_layout.addSpacing(10)
        control_layout.addWidget(self.save_btn)
        control_layout.addWidget(self.load_btn)
        control_layout.addStretch()

        control_group.setLayout(control_layout)

        mid_layout.addWidget(config_group, 3)
        mid_layout.addWidget(control_group, 1)

        main_layout.addLayout(mid_layout)

        # ================== 图表区域（核心） ==================
        chart_group = QGroupBox("OSCP Curve")
        chart_layout = QVBoxLayout()

        self.chart_placeholder = QFrame()
        self.chart_placeholder.setMinimumHeight(350)
        self.chart_placeholder.setStyleSheet("""
            background-color: #0f1115;
            border: 1px solid #2a2f36;
            border-radius: 6px;
        """)

        chart_layout.addWidget(self.chart_placeholder)
        chart_group.setLayout(chart_layout)

        main_layout.addWidget(chart_group, 1)

        # ================== 底部结果 ==================
        result_layout = QHBoxLayout()

        self.protection_current_label = QLabel("Protect: ---")
        self.recovery_current_label = QLabel("Recover: ---")
        self.trigger_time_label = QLabel("Trig: ---")
        self.recovery_time_label = QLabel("Rec: ---")

        self.export_btn = QPushButton("导出结果")

        result_layout.addWidget(self.protection_current_label)
        result_layout.addWidget(self.recovery_current_label)
        result_layout.addWidget(self.trigger_time_label)
        result_layout.addWidget(self.recovery_time_label)
        result_layout.addStretch()
        result_layout.addWidget(self.export_btn)

        main_layout.addLayout(result_layout)
    
    def _init_ui_elements(self):
        """初始化UI元素"""
        # 设置默认值和初始状态
        
        # 连接按钮点击事件
        self.single_test_btn.clicked.connect(self._on_single_test)
        self.iteration_test_btn.clicked.connect(self._on_iteration_test)
        self.test_btn.clicked.connect(self.debug_test)
    
    def _on_single_test(self):
        """单次测试按钮点击事件"""
        if self.is_test_running:
            self.set_system_status("测试正在运行中...", True)
            return
            
        # 获取当前测试配置
        config = self.get_test_config()
        test_type = config["test_type"]
        
        # 检查仪器是否连接
        if not self.is_connected or self.n6705c is None:
            self.set_system_status("请先连接N6705C仪器", True)
            return
        
        self.set_system_status("执行单次测试...")
        self.is_test_running = True
        self.set_test_running(True)
        
        # 创建并启动测试线程
        # 从config中移除test_type，避免参数冲突
        config_copy = config.copy()
        config_copy.pop('test_type', None)
        
        self.test_thread = TestThread(test_type, self.n6705c, **config_copy)
        self.test_thread.status_update.connect(self.set_system_status)
        self.test_thread.result_update.connect(self._on_test_result)
        self.test_thread.test_finished.connect(self._on_test_finished)
        self.test_thread.start()
        
        # 示例：输出当前配置信息
        print("执行单次测试，配置:", config)
        
        # 这里可以添加实际的单次测试逻辑
        # 例如：设置参数、执行测试、获取结果等
    def debug_test(self):
        """Debug测试方法 - 演示10bit模式下的读写操作"""
        self.set_system_status("执行Debug测试...")
        # 获取当前测试配置
        config = self.get_test_config()
        print("执行Debug测试，配置:", config)
        self.n6705c=N6705C("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
        self.n6705c.set_voltage(2,0.65)
        # self.ovp_test(1, 2, 1.35, 1.6, 0.001)
        self.uvp_test(1, 2, 0.5, 0.55, 0.001)
        
    def ovp_test(self, vbat_channel=1, vol_channel=2, start_voltage=0.7, end_voltage=1.5, step_voltage=0.1):
        """OVP测试方法 - 演示10bit模式下的读写操作"""
        # self.n6705c.set_mode(vol_channel, "VMETer")
        # default_voltage = self.n6705c.measure_voltage(vol_channel)
        self.n6705c.set_mode(vol_channel, "PS2Q")
        self.n6705c.set_voltage(vol_channel, start_voltage)
        self.n6705c.channel_on(vol_channel)
        time.sleep(0.5)
        self.set_system_status("执行OVP测试...")
        print(f"OVP测试: 起始电压={start_voltage:.3f} V, 结束电压={end_voltage:.3f} V, 步进电压={step_voltage:.3f} V")
        cnt_voltage = start_voltage
        while cnt_voltage <= end_voltage + 0.05:
            current_before = float(self.n6705c.measure_current(vbat_channel))
            self.n6705c.set_voltage(vol_channel, cnt_voltage)
            time.sleep(0.5)
            current_after = float(self.n6705c.measure_current(vbat_channel))
            print(f"Test voltage: {cnt_voltage:.3f} V, current_before: {current_before*1000:.4f} mA, current_after: {current_after*1000:.4f} mA")
            if current_after < current_before-0.00001:
                print(f"OVP触发，电压: {cnt_voltage:.3f} V, 电流: {current_after*1000:.4f} mA")
                self.protection_current_label.setText(f"保护电压: {cnt_voltage:.3f} V")
                break
            cnt_voltage += step_voltage
    
    def uvp_test(self, vbat_channel=1, vol_channel=2, start_voltage=0.7, end_voltage=1.5, step_voltage=0.1):
        """UVP测试方法 - 演示10bit模式下的读写操作"""
        self.n6705c.set_mode(vol_channel, "CVLoad")
        self.n6705c.set_voltage(vol_channel, end_voltage)
        self.n6705c.channel_on(vol_channel)
        time.sleep(0.5)
        self.set_system_status("执行UVP测试...")
        print(f"UVP测试: 起始电压={start_voltage:.3f} V, 结束电压={end_voltage:.3f} V, 步进电压={step_voltage:.3f} V")
        cnt_voltage = end_voltage
        while cnt_voltage >= start_voltage - 0.05:
            current_before = float(self.n6705c.measure_current(vbat_channel))
            self.n6705c.set_voltage(vol_channel, cnt_voltage)
            time.sleep(0.1)
            current_after = float(self.n6705c.measure_current(vbat_channel))
            print(f"Test voltage: {cnt_voltage:.3f} V, current_before: {current_before*1000:.4f} mA, current_after: {current_after*1000:.4f} mA")
            if current_after < current_before-0.01:
                print(f"UVP触发，电压: {cnt_voltage:.3f} V, 电流: {current_after*1000:.4f} mA")
                self.protection_current_label.setText(f"保护电压: {cnt_voltage:.3f} V")
                break
            cnt_voltage -= step_voltage
        
        
    def _on_iteration_test(self):
        """遍历测试按钮点击事件"""
        self.set_system_status("执行遍历测试...")
        i2c = I2CInterface()
        self.n6705c.measure_voltage(1)
        # 获取当前测试配置
        config = self.get_test_config()
        
        # 示例：输出当前配置信息
        print("执行遍历测试，配置:", config)
        
        # 这里可以添加实际的遍历测试逻辑
        # 例如：设置多个测试点、循环执行测试、收集所有结果等
    
    def i2c_test(self):
        """I2C测试方法 - 演示10bit模式下的读写操作"""
        self.set_system_status("执行I2C测试...")
        
        try:
            # 创建I2C接口实例（默认使用100kHz速度）
            i2c = I2CInterface()
            self.set_system_status("I2C接口初始化成功")
            
            # 测试参数配置
            device_addr = 0x17  # 器件地址
            width_flag = I2CWidthFlag.BIT_10  # 10bit模式
            
            # 1. 读取操作：器件地址0x17，寄存器地址0x0000
            reg_addr_read = 0x0000
            print(f"\n1. 读取操作：")
            print(f"   设备地址: 0x{device_addr:02X}")
            print(f"   寄存器地址: 0x{reg_addr_read:04X}")
            print(f"   位宽模式: {width_flag.name}")
            
            read_data = i2c.read(device_addr, reg_addr_read, width_flag)
            print(f"   读取结果: 0x{read_data:04X}")
            self.set_system_status(f"I2C读取成功: 0x{read_data:04X}")
            
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
            self.set_system_status("I2C写入成功")
            
            # 3. 验证写入结果
            time.sleep(0.1)  # 延迟确保写入完成
            print(f"\n3. 验证写入结果：")
            verify_data = i2c.read(device_addr, reg_addr_write, width_flag)
            print(f"   寄存器地址0x{reg_addr_write:04X}的当前值: 0x{verify_data:04X}")
            print(f"   验证{'成功' if verify_data == write_data else '失败'}")
            
            if verify_data == write_data:
                self.set_system_status("I2C测试完成，验证成功")
            else:
                self.set_system_status("I2C测试完成，但验证失败", is_error=True)
            
            return True
            
        except Exception as e:
            error_msg = f"I2C测试操作失败: {e}"
            print(error_msg)
            self.set_system_status(error_msg, is_error=True)
            return False
    
    def _update_test_config(self, index):
        """根据选择的测试类型更新测试配置界面"""
        test_type = self.test_type_combo.currentText()
        
        if test_type in ["OCP", "SCP"]:
            # 电流相关测试
            self.channel_label.setText("电流通道:")
            self.start_label.setText("起始电流 (A):")
            self.end_label.setText("结束电流 (A):")
            self.step_label.setText("步进电流 (A):")
            
            # 设置电流范围和精度
            self.start_spin.setRange(0.0, 10.0)
            self.start_spin.setSingleStep(0.001)  # 支持到小数点后三位
            self.start_spin.setDecimals(3)        # 显示三位小数
            self.end_spin.setRange(0.0, 10.0)
            self.end_spin.setSingleStep(0.001)    # 支持到小数点后三位
            self.end_spin.setDecimals(3)          # 显示三位小数
            self.step_spin.setRange(0.001, 1.0)
            self.step_spin.setSingleStep(0.001)   # 支持到小数点后三位
            self.step_spin.setDecimals(4)         # 显示四位小数
            self.protection_spin.setRange(0.0, 10.0)
            self.protection_spin.setSingleStep(0.001)  # 支持到小数点后三位
            self.protection_spin.setDecimals(3)         # 显示三位小数
            
            # 更新保护值标签
            if test_type == "OCP":
                self.protection_label.setText("OCP值 (A):")
            else:  # SCP
                self.protection_label.setText("SCP值 (A):")
        else:
            # 电压相关测试
            self.channel_label.setText("电压通道:")
            self.start_label.setText("起始电压 (V):")
            self.end_label.setText("结束电压 (V):")
            self.step_label.setText("步进电压 (V):")
            
            # 设置电压范围和精度
            self.start_spin.setRange(0.0, 20.0)
            self.start_spin.setSingleStep(0.001)  # 支持到小数点后三位
            self.start_spin.setDecimals(3)        # 显示三位小数
            self.end_spin.setRange(0.0, 20.0)
            self.end_spin.setSingleStep(0.001)    # 支持到小数点后三位
            self.end_spin.setDecimals(3)          # 显示三位小数
            self.step_spin.setRange(0.001, 2.0)
            self.step_spin.setSingleStep(0.001)   # 支持到小数点后三位
            self.step_spin.setDecimals(4)         # 显示四位小数
            self.protection_spin.setRange(0.0, 20.0)
            self.protection_spin.setSingleStep(0.001)  # 支持到小数点后三位
            self.protection_spin.setDecimals(3)         # 显示三位小数
            
            # 更新保护值标签
            if test_type == "OVP":
                self.protection_label.setText("OVP值 (V):")
            else:  # UVP
                self.protection_label.setText("UVP值 (V):")
    
    def get_test_config(self):
        """获取测试配置"""
        test_type = self.test_type_combo.currentText()
        
        # 根据测试类型确定返回的配置字段
        config = {
            'test_type': test_type,
            'power_channel': self.power_channel_combo.currentText(),
            'test_channel': self.test_channel_combo.currentText(),
            'device_address': self.device_addr_spin.value(),
            'register_address': self.reg_addr_spin.value(),
            'msb': self.msb_spin.value(),
            'lsb': self.lsb_spin.value()
        }
        
        if test_type in ['OCP', 'SCP']:
            # 电流相关测试
            config.update({
                'current_channel': self.test_channel_combo.currentText(),
                'current_start': self.start_spin.value(),
                'current_end': self.end_spin.value(),
                'current_step': self.step_spin.value()
            })
            
            if test_type == 'OCP':
                config['ocp_value'] = self.protection_spin.value()
            else:
                config['scp_value'] = self.protection_spin.value()
        else:
            # 电压相关测试
            config.update({
                'voltage_channel': self.test_channel_combo.currentText(),
                'voltage_start': self.start_spin.value(),
                'voltage_end': self.end_spin.value(),
                'voltage_step': self.step_spin.value()
            })
            
            if test_type == 'OVP':
                config['ovp_value'] = self.protection_spin.value()
            else:
                config['uvp_value'] = self.protection_spin.value()
                
        return config
    
    def set_test_running(self, running):
        """设置测试运行状态"""
        self.start_test_btn.setEnabled(not running)
        self.stop_test_btn.setEnabled(running)
        
        # 禁用/启用配置控件
        widgets = [
            self.test_type_combo,
            self.power_channel_combo,
            self.test_channel_combo,
            self.start_spin,
            self.end_spin,
            self.step_spin,
            self.device_addr_spin,
            self.reg_addr_spin,
            self.msb_spin,
            self.lsb_spin,
            self.protection_spin,
            self.single_test_btn,
            self.iteration_test_btn,
            self.test_btn,
            self.save_config_btn,
            self.load_config_btn
        ]
        
        for widget in widgets:
            widget.setEnabled(not running)
    
    def _on_stop_test(self):
        """停止测试按钮点击事件"""
        if self.is_test_running and self.test_thread:
            self.set_system_status("正在停止测试...")
            self.test_thread.stop()
            self.test_thread.wait(1000)  # 等待最多1秒让线程结束
            self._on_test_finished(False)  # 强制标记测试结束
    
    def _on_test_result(self, result_type, value):
        """处理测试结果更新"""
        if result_type == "保护电压":
            self.protection_current_label.setText(f"保护电压: {value:.3f} V")
        elif result_type == "保护电流":
            self.protection_current_label.setText(f"保护电流: {value:.3f} A")
    
    def _on_test_finished(self, success):
        """处理测试完成事件"""
        self.is_test_running = False
        self.set_test_running(False)
        
        if success:
            self.set_system_status("测试完成")
        else:
            self.set_system_status("测试停止")
        
        # 清理测试线程
        if self.test_thread:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_thread = None
    
    def update_test_result(self, result):
        """更新测试结果"""
        if 'protection_current' in result:
            self.protection_current_label.setText(f"保护电流: {result['protection_current']:.4f} A")
        if 'recovery_current' in result:
            self.recovery_current_label.setText(f"恢复电流: {result['recovery_current']:.4f} A")
        if 'trigger_time' in result:
            self.trigger_time_label.setText(f"触发时间: {result['trigger_time']:.4f} ms")
        if 'recovery_time' in result:
            self.recovery_time_label.setText(f"恢复时间: {result['recovery_time']:.4f} ms")
    
    def clear_results(self):
        """清空测试结果"""
        self.protection_current_label.setText("保护电流: ---")
        self.recovery_current_label.setText("恢复电流: ---")
        self.trigger_time_label.setText("触发时间: ---")
        self.recovery_time_label.setText("恢复时间: ---")
    
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
    
    def get_test_mode(self):
        """获取测试模式"""
        return self.test_mode_combo.currentText()
    
    def set_test_mode(self, mode):
        """设置测试模式"""
        index = self.test_mode_combo.findText(mode)
        if index >= 0:
            self.test_mode_combo.setCurrentIndex(index)
    
    def get_test_id(self):
        """获取测试编号"""
        return self.test_id_edit.text()
    
    def set_test_id(self, test_id):
        """设置测试编号"""
        self.test_id_edit.setText(test_id)
    
    def _on_search(self):
        """搜索N6705C设备按钮点击事件"""
        self.connection_status_label.setText("搜索中...")
        self.connection_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        
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
            self.n6705c_combo.clear()
            
            # 仅添加N6705C设备
            n6705c_count = len(n6705c_devices)
            if n6705c_devices:
                for dev in n6705c_devices:
                    self.n6705c_combo.addItem(dev)
                
                # 设置状态和按钮
                self.connection_status_label.setText(f"找到 {n6705c_count} 个N6705C设备")
                self.connection_status_label.setStyleSheet("color: #00a859; font-weight: bold;")
                self.connect_btn.setEnabled(True)
                
                # 默认选择指定的N6705C设备
                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    # 如果默认设备存在，选择它
                    self.n6705c_combo.setCurrentText(default_device)
                else:
                    # 否则选择第一个设备
                    self.n6705c_combo.setCurrentIndex(0)
            else:
                # 没有找到N6705C设备
                self.n6705c_combo.addItem("未找到N6705C设备")
                self.n6705c_combo.setEnabled(False)
                self.connection_status_label.setText("未找到N6705C设备")
                self.connection_status_label.setStyleSheet("color: #e53935; font-weight: bold;")
                self.connect_btn.setEnabled(False)
            
        except Exception as e:
            print(f"搜索过程中发生错误: {str(e)}")
            self.connection_status_label.setText(f"搜索失败: {str(e)}")
            self.connection_status_label.setStyleSheet("color: #e53935; font-weight: bold;")
            self.connect_btn.setEnabled(False)
        finally:
            # 启用搜索按钮
            self.search_btn.setEnabled(True)
    
    def _on_connect(self):
        """连接N6705C设备按钮点击事件"""
        self.connection_status_label.setText("连接中...")
        self.connection_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        
        # 禁用连接按钮
        self.connect_btn.setEnabled(False)
        
        try:
            # 获取用户选择的设备地址
            device_address = self.n6705c_combo.currentText()
            # 创建N6705C控制器实例
            self.n6705c = N6705C(device_address)
            
            # 发送*IDN?命令确认连接
            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self.is_connected = True
                self.connection_status_label.setText("已连接")
                self.connection_status_label.setStyleSheet("color: #00a859; font-weight: bold;")
                
                # 更新按钮状态
                self.disconnect_btn.setEnabled(True)
                self.search_btn.setEnabled(False)  # 连接后禁用搜索
                
                # 更新仪器信息
                self.instrument_info_label.setText(f"N6705C ({device_address.split('::')[1]}) + MSO64B")
                
                # 发射连接成功信号
                self.connection_status_changed.emit(True)
            else:
                self.connection_status_label.setText("设备不匹配")
                self.connection_status_label.setStyleSheet("color: #e53935; font-weight: bold;")
                self.connect_btn.setEnabled(True)
        
        except Exception as e:
            self.connection_status_label.setText(f"连接失败: {str(e)}")
            self.connection_status_label.setStyleSheet("color: #e53935; font-weight: bold;")
            self.connect_btn.setEnabled(True)
    
    def _on_disconnect(self):
        """断开N6705C设备按钮点击事件"""
        self.connection_status_label.setText("断开中...")
        self.connection_status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        
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
            
            self.connection_status_label.setText("未连接")
            self.connection_status_label.setStyleSheet("color: #e53935; font-weight: bold;")
            
            # 更新按钮状态
            self.connect_btn.setEnabled(True)
            self.search_btn.setEnabled(True)
            
            # 恢复仪器信息
            self.instrument_info_label.setText("N6705C + MSO64B")
            
            # 发射连接断开信号
            self.connection_status_changed.emit(False)
            
        except Exception as e:
            self.connection_status_label.setText(f"断开失败: {str(e)}")
            self.connection_status_label.setStyleSheet("color: #e53935; font-weight: bold;")
            self.disconnect_btn.setEnabled(True)
    
    def get_n6705c_instance(self):
        """获取N6705C控制器实例"""
        return self.n6705c
    
    def is_n6705c_connected(self):
        """检查N6705C是否已连接"""
        return self.is_connected


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 创建PMU测试主UI
    pmu_test_ui = PMUOSCPUI()
    pmu_test_ui.debug_test()



    # pmu_test_ui.setWindowTitle("PMU测试系统")
    # pmu_test_ui.setGeometry(100, 100, 1200, 800)
    # pmu_test_ui.show()
    
    # sys.exit(app.exec())