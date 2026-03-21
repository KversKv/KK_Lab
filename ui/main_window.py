#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QComboBox, QLabel, QLineEdit, QGridLayout, 
    QTabWidget, QStatusBar, QCheckBox, QSplitter, QFrame, QButtonGroup
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette, QColor, QFont
from ui.plot_widget import PlotWidget
from ui.mso64b_ui import MSO64BUI
from ui.n6705c_ui import N6705CUI
from ui.pmu_test_ui import PMUTestUI
from ui.sidebar_nav_button import SidebarNavButton
from core.test_manager import TestManager
from instruments.visa_instrument import VisaInstrument
from instruments.ch341t import CH341T
from instruments.mso64b import MSO64B


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("功耗测试工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化测试管理器
        self.test_manager = TestManager()
        
        # 初始化仪器
        self.visa_instrument = VisaInstrument()
        self.ch341t = CH341T()
        self.mso64b_instrument = None
        
        # 初始化UI组件
        self.n6705c_ui = None
        self.mso64b_ui = None
        self.pmu_test_ui = None
        self.current_instrument_ui = None
        
        # 设置样式
        self._setup_style()
        
        # 创建主布局
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建顶部状态栏
        self._create_status_bar()
        
        # 创建主内容区域
        self._create_main_content()
        
        # 连接信号槽
        self._connect_signals()
    
    def _setup_style(self):
        """设置界面样式"""
        # 设置暗色主题 - Keysight风格
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(22, 24, 28))  # 更深的背景
        palette.setColor(QPalette.WindowText, QColor(200, 200, 200))
        palette.setColor(QPalette.Base, QColor(32, 35, 40))
        palette.setColor(QPalette.AlternateBase, QColor(40, 43, 48))
        palette.setColor(QPalette.ToolTipBase, QColor(40, 43, 48))
        palette.setColor(QPalette.ToolTipText, QColor(200, 200, 200))
        palette.setColor(QPalette.Text, QColor(200, 200, 200))
        palette.setColor(QPalette.Button, QColor(50, 53, 58))
        palette.setColor(QPalette.ButtonText, QColor(200, 200, 200))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(30, 30, 30))
        self.setPalette(palette)
        
        # 设置字体
        font = QFont("Segoe UI", 9)  # 更接近仪器界面的字体
        self.setFont(font)
        
        # 设置窗口样式
        self.setWindowTitle("LabControl Pro")
        self.setStyleSheet("""
            QMainWindow {
                background-color: #16181c;
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
            QCheckBox {
                color: #c8c8c8;
            }
            QStatusBar {
                background-color: #16181c;
                color: #c8c8c8;
                border-top: 1px solid #333;
            }
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #202328;
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
            QFrame {
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #202328;
            }
        """)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 仪器连接状态
        self.visa_status = QLabel("VISA: 未连接")
        self.ch341t_status = QLabel("CH341T: 未连接")
        
        self.status_bar.addWidget(self.visa_status)
        self.status_bar.addWidget(self.ch341t_status)
    
    def _create_main_content(self):
        """创建主内容区域"""
        main_splitter = QSplitter(Qt.Horizontal)
        # 左侧导航栏
        self.left_nav = QFrame()
        self.left_nav.setFixedWidth(280)
        self.left_nav.setObjectName("leftNav")
        self.left_nav.setStyleSheet("""
            QFrame#leftNav {
                background-color: #0b1020;
                border: none;
                border-radius: 0px;
            }
        """)
        left_nav_layout = QVBoxLayout(self.left_nav)
        left_nav_layout.setContentsMargins(14, 18, 14, 18)
        left_nav_layout.setSpacing(10)
        # 顶部标题
        logo_label = QLabel("LabControl Pro")
        logo_label.setStyleSheet("""
            QLabel {
                color: #7ea1ff;
                font-size: 18px;
                font-weight: 700;
                padding: 6px 4px 12px 4px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(logo_label)
        # 分组标题：INSTRUMENTS
        instruments_title = QLabel("INSTRUMENTS")
        instruments_title.setStyleSheet("""
            QLabel {
                color: #5f78a8;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 10px 6px 4px 6px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(instruments_title)
        # 导航按钮
        self.power_analyzer_btn = SidebarNavButton(
            "N6705C Power\nAnalyzer",
            "",
            "⚡"
        )
        self.power_analyzer_btn.setChecked(True)
        self.oscilloscope_btn = SidebarNavButton(
            "MSO64B Oscilloscope",
            "",
            "∿"
        )
        left_nav_layout.addWidget(self.power_analyzer_btn)
        left_nav_layout.addWidget(self.oscilloscope_btn)
        # 分组标题：AUTOMATION
        automation_title = QLabel("AUTOMATION")
        automation_title.setStyleSheet("""
            QLabel {
                color: #5f78a8;
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 18px 6px 4px 6px;
                border: none;
                background: transparent;
            }
        """)
        left_nav_layout.addWidget(automation_title)
        self.pmu_auto_test_btn = SidebarNavButton(
            "PMU Auto Test",
            "",
            "⚙"
        )
        left_nav_layout.addWidget(self.pmu_auto_test_btn)
        # 单选组
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)
        self.nav_button_group.addButton(self.power_analyzer_btn)
        self.nav_button_group.addButton(self.oscilloscope_btn)
        self.nav_button_group.addButton(self.pmu_auto_test_btn)
        left_nav_layout.addStretch()
        # 底部按钮
        self.download_btn = QPushButton("Download Python Code")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setStyleSheet("""
            QPushButton {
                margin-top: 10px;
                min-height: 42px;
                background-color: #1d2740;
                color: #dbe6ff;
                border: 1px solid #2c3a5e;
                border-radius: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #24314f;
            }
            QPushButton:pressed {
                background-color: #1a243a;
            }
        """)
        left_nav_layout.addWidget(self.download_btn)
        main_splitter.addWidget(self.left_nav)
        # 右侧主内容区域
        self.right_content = QWidget()
        self.right_content_layout = QVBoxLayout(self.right_content)
        self.right_content_layout.setContentsMargins(0, 0, 0, 0)
        self.instrument_ui_container = QWidget()
        self.instrument_ui_container_layout = QVBoxLayout(self.instrument_ui_container)
        self.instrument_ui_container_layout.setContentsMargins(0, 0, 0, 0)
        self._create_power_analyzer_ui()
        self.right_content_layout.addWidget(self.instrument_ui_container)
        main_splitter.addWidget(self.right_content)
        main_splitter.setSizes([280, 920])
        self.main_layout.addWidget(main_splitter)
    
    def _create_power_analyzer_ui(self):
        """创建电源分析仪UI"""
        # 清空容器
        self._clear_instrument_ui_container()
        
        # 创建新的N6705C UI组件实例
        self.n6705c_ui = N6705CUI()
        
        # 通道切换信号已在n6705c_ui内部处理，不再需要外部连接
        
        self.instrument_ui_container_layout.addWidget(self.n6705c_ui)
        self.current_instrument_ui = "power_analyzer"
        
        # 保存通道引用
        self.channels = self.n6705c_ui.channels if hasattr(self.n6705c_ui, 'channels') else []
    
    def _create_oscilloscope_ui(self):
        """创建示波器UI"""
        # 清空容器
        self._clear_instrument_ui_container()
        
        # 创建新的示波器UI组件实例
        self.mso64b_ui = MSO64BUI()
        
        # 连接示波器UI的信号
        self.mso64b_ui.connect_btn.clicked.connect(self._connect_mso64b)
        self.mso64b_ui.disconnect_btn.clicked.connect(self._disconnect_mso64b)
        self.mso64b_ui.measure_btn.clicked.connect(self._measure_mso64b)
        
        self.instrument_ui_container_layout.addWidget(self.mso64b_ui)
        self.current_instrument_ui = "oscilloscope"
    
    def _create_pmu_test_ui(self):
        """创建PMU测试UI"""
        # 清空容器
        self._clear_instrument_ui_container()
        
        # 创建新的PMU测试UI组件实例
        self.pmu_test_ui = PMUTestUI()
        
        self.instrument_ui_container_layout.addWidget(self.pmu_test_ui)
        self.current_instrument_ui = "pmu_test"
    
    def _clear_instrument_ui_container(self):
        """清空仪器UI容器"""
        while self.instrument_ui_container_layout.count() > 0:
            widget = self.instrument_ui_container_layout.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()
    

    
    def _connect_signals(self):
        """连接信号槽"""
        # 仪器扫描和连接
        # self.scan_visa_btn.clicked.connect(self._scan_visa)
        # self.connect_visa_btn.clicked.connect(self._connect_visa)
        # self.scan_ch341t_btn.clicked.connect(self._scan_ch341t)
        # self.connect_ch341t_btn.clicked.connect(self._connect_ch341t)
        
        # 导航按钮
        self.power_analyzer_btn.clicked.connect(self._on_nav_button_clicked)
        self.oscilloscope_btn.clicked.connect(self._on_nav_button_clicked)
        self.pmu_auto_test_btn.clicked.connect(self._on_nav_button_clicked)
        

        
        # 通道切换按钮 - 在_create_power_analyzer_ui中连接
        
        # 下载按钮
        self.download_btn.clicked.connect(self._on_download_code)
        
        # 测试控制
        # self.start_test_btn.clicked.connect(self._start_test)
        # self.stop_test_btn.clicked.connect(self._stop_test)
        
        # IIC 指令
        # self.send_iic_btn.clicked.connect(self._send_iic_command)
        
        # 数据导出
        # self.export_btn.clicked.connect(self._export_data)
        
        # 测试管理器信号
        self.test_manager.data_updated.connect(self._update_data)
    
    def _on_nav_button_clicked(self):
        """导航按钮点击事件"""
        sender = self.sender()

        if sender == self.power_analyzer_btn:
            self._create_power_analyzer_ui()
        elif sender == self.oscilloscope_btn:
            self._create_oscilloscope_ui()
        elif sender == self.pmu_auto_test_btn:
            self._create_pmu_test_ui()
        
    def _on_channel_toggle(self):
        """ON按钮点击事件"""
        # 获取当前选择的通道号
        if self.n6705c_ui and hasattr(self.n6705c_ui, 'channel_combo'):
            channel_num = int(self.n6705c_ui.channel_combo.currentText())
            print(f"Channel {channel_num} ON")
        # 这里可以添加实际的通道开关逻辑
    
    def _on_download_code(self):
        """下载代码按钮点击事件"""
        print("Download Python Code clicked")
        # 这里可以添加下载代码的逻辑
    
    def _connect_mso64b(self):
        """连接MSO64B示波器"""
        if not self.mso64b_ui:
            return
        
        connection_info = self.mso64b_ui.get_connection_info()
        ip_address = connection_info.get('ip_address')
        
        try:
            self.mso64b_instrument = MSO64B(ip_address)
            instrument_info = self.mso64b_instrument.identify_instrument()
            self.mso64b_ui.update_connection_status(True, instrument_info)
            # 更新状态栏
            self.visa_status.setText(f"示波器: 已连接 - {ip_address}")
        except Exception as e:
            print(f"连接示波器失败: {str(e)}")
            self.mso64b_ui.update_connection_status(False)
            self.visa_status.setText("示波器: 连接失败")
    
    def _disconnect_mso64b(self):
        """断开MSO64B示波器"""
        if self.mso64b_instrument:
            self.mso64b_instrument.disconnect()
            self.mso64b_instrument = None
        
        if self.mso64b_ui:
            self.mso64b_ui.update_connection_status(False)
        
        self.visa_status.setText("示波器: 未连接")
    
    def _measure_mso64b(self):
        """执行MSO64B测量"""
        if not self.mso64b_instrument or not self.mso64b_ui:
            return
        
        try:
            measure_settings = self.mso64b_ui.get_measure_settings()
            channel = measure_settings.get('channel')
            measure_type = measure_settings.get('type')
            
            if measure_type == 'MEAN':
                result = self.mso64b_instrument.get_channel_mean(channel)
            elif measure_type == 'PK2PK':
                result = self.mso64b_instrument.get_channel_pk2pk(channel)
            else:
                return
            
            self.mso64b_ui.update_measure_result(measure_type, result)
        except Exception as e:
            print(f"测量失败: {str(e)}")
        
    def _scan_visa(self):
        """扫描 VISA 设备"""
        devices = self.visa_instrument.scan_devices()
        self.visa_combo.clear()
        self.visa_combo.addItems(devices)
    
    def _connect_visa(self):
        """连接 VISA 设备"""
        device = self.visa_combo.currentText()
        if device:
            success = self.visa_instrument.connect(device)
            if success:
                self.visa_status.setText(f"VISA: 已连接 - {device}")
                self.connect_visa_btn.setText("断开")
            else:
                self.visa_status.setText("VISA: 连接失败")
        else:
            if self.visa_instrument.is_connected():
                self.visa_instrument.disconnect()
                self.visa_status.setText("VISA: 未连接")
                self.connect_visa_btn.setText("连接")
    
    def _scan_ch341t(self):
        """扫描 CH341T 端口"""
        ports = self.ch341t.scan_ports()
        self.ch341t_combo.clear()
        self.ch341t_combo.addItems(ports)
    
    def _connect_ch341t(self):
        """连接 CH341T"""
        port = self.ch341t_combo.currentText()
        if port:
            success = self.ch341t.connect(port)
            if success:
                self.ch341t_status.setText(f"CH341T: 已连接 - {port}")
                self.connect_ch341t_btn.setText("断开")
            else:
                self.ch341t_status.setText("CH341T: 连接失败")
        else:
            if self.ch341t.is_connected():
                self.ch341t.disconnect()
                self.ch341t_status.setText("CH341T: 未连接")
                self.connect_ch341t_btn.setText("连接")
    
    def _start_test(self):
        """开始测试"""
        # 获取参数
        channel = int(self.channel_combo.currentText())
        voltage = float(self.voltage_edit.text())
        current_limit = float(self.current_limit_edit.text())
        sampling_rate = int(self.sampling_rate_edit.text())
        
        # 配置仪器
        self.visa_instrument.set_channel(channel)
        self.visa_instrument.set_voltage(voltage)
        self.visa_instrument.set_current_limit(current_limit)
        
        # 启动测试
        self.test_manager.start_test(
            visa_instrument=self.visa_instrument,
            sampling_rate=sampling_rate
        )
        
        self.start_test_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(True)
    
    def _stop_test(self):
        """停止测试"""
        self.test_manager.stop_test()
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
    
    def _send_iic_command(self):
        """发送 IIC 指令"""
        command = self.iic_command_edit.text()
        if self.ch341t.is_connected():
            self.ch341t.send_command(command)
    
    def _export_data(self):
        """导出数据"""
        self.test_manager.export_data()
    
    def _update_data(self, data):
        """更新数据"""
        # 更新波形
        # self.plot_widget.update_plot(data)
        
        # 根据当前显示的UI更新数据
        if self.current_instrument_ui == "power_analyzer" and self.n6705c_ui:
            if data and isinstance(data, list) and len(data) == 4:
                for i, channel_data in enumerate(data):
                    voltage = channel_data.get('voltage', 0.0)
                    current = channel_data.get('current', 0.0)
                    self.n6705c_ui.update_channel_values(i+1, voltage, current)
            elif data and 'current' in data:
                # 兼容旧的数据格式，只更新第一个通道
                current = data['current'][-1] if data['current'] else 0.0
                voltage = data['voltage'][-1] if data['voltage'] else 0.0
                self.n6705c_ui.update_channel_values(1, voltage, current)
        elif self.current_instrument_ui == "pmu_test" and self.pmu_test_ui:
            # PMU测试UI的数据更新
            # 根据data中的测试类型将结果传递给相应的子页面
            if data and isinstance(data, dict):
                test_type = data.get('test_type')
                result = data.get('result', {})
                if test_type:
                    self.pmu_test_ui.update_test_result(test_type, result)
        else:
            # 兼容旧的UI结构
            if data and isinstance(data, list) and len(data) == 4:
                for i, channel_data in enumerate(data):
                    if i < len(self.channels):
                        voltage = channel_data.get('voltage', 0.0)
                        current = channel_data.get('current', 0.0)
                        self.channels[i]['voltage_value'].setText(f"{voltage:.4f}")
                        self.channels[i]['current_value'].setText(f"{current:.4f}")
            elif data and 'current' in data:
                # 兼容旧的数据格式，只更新第一个通道
                if self.channels:
                    current = data['current'][-1] if data['current'] else 0.0
                    voltage = data['voltage'][-1] if data['voltage'] else 0.0
                    self.channels[0]['voltage_value'].setText(f"{voltage:.4f}")
                    self.channels[0]['current_value'].setText(f"{current:.4f}")
