#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PMU OSCP测试UI组件
深色卡片风格 + PySide6原生实现
"""

from ui.dark_combobox import DarkComboBox
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QGridLayout,
    QSpinBox, QDoubleSpinBox, QFrame, QApplication
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

    status_update = Signal(str, bool)       # 状态消息, 是否错误
    result_update = Signal(str, float)      # 结果类型, 结果值
    test_finished = Signal(bool)            # 测试是否成功完成

    def __init__(self, test_type, n6705c, **kwargs):
        super().__init__()
        self.test_type = test_type
        self.n6705c = n6705c
        self.kwargs = kwargs
        self.is_running = True

    def run(self):
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
        self.is_running = False

    def run_ovp_test(self):
        vbat_channel = int(self.kwargs.get("power_channel", 1))
        vol_channel = int(self.kwargs.get("test_channel", 2))
        start_voltage = self.kwargs.get("voltage_start", 0.7)
        end_voltage = self.kwargs.get("voltage_end", 1.5)
        step_voltage = self.kwargs.get("voltage_step", 0.1)

        self.status_update.emit("执行OVP测试...", False)
        self.thread_ovp_test(vbat_channel, vol_channel, start_voltage, end_voltage, step_voltage)

        self.status_update.emit("OVP测试结束，未检测到触发", False)

    def run_uvp_test(self):
        vbat_channel = int(self.kwargs.get("power_channel", 1))
        vol_channel = int(self.kwargs.get("test_channel", 2))
        start_voltage = self.kwargs.get("voltage_start", 0.7)
        end_voltage = self.kwargs.get("voltage_end", 1.5)
        step_voltage = self.kwargs.get("voltage_step", 0.1)

        self.status_update.emit("执行UVP测试...", False)
        self.thread_uvp_test(vbat_channel, vol_channel, start_voltage, end_voltage, step_voltage)
        self.status_update.emit("UVP测试结束，未检测到触发", False)

    def run_ocp_test(self):
        self.status_update.emit("OCP测试功能尚未实现", False)

    def run_scp_test(self):
        self.status_update.emit("SCP测试功能尚未实现", False)


    def thread_ovp_test(self, vbat_channel=1, vol_channel=2, start_voltage=0.7, end_voltage=1.5, step_voltage=0.1):
        try:
            self.n6705c.set_mode(vol_channel, "PS2Q")
            self.n6705c.set_voltage(vol_channel, start_voltage)
            self.n6705c.channel_on(vol_channel)
            QThread.msleep(500)

            self.status_update.emit("执行OVP测试...", False)
            print(f"OVP测试: 起始电压={start_voltage:.3f} V, 结束电压={end_voltage:.3f} V, 步进电压={step_voltage:.3f} V")

            cnt_voltage = start_voltage
            while cnt_voltage <= end_voltage + 0.001 and self.is_running:
                current_before = float(self.n6705c.measure_current(vbat_channel))
                self.n6705c.set_voltage(vol_channel, cnt_voltage)
                QThread.msleep(500)
                current_after = float(self.n6705c.measure_current(vbat_channel))

                print(f"Test voltage: {cnt_voltage:.3f} V, current_before: {current_before * 1000:.4f} mA, current_after: {current_after * 1000:.4f} mA")

                if current_after < current_before - 0.00001:
                    print(f"OVP触发，电压: {cnt_voltage:.3f} V, 电流: {current_after * 1000:.4f} mA")
                    self.result_update.emit("保护电压", cnt_voltage)
                    break

                cnt_voltage += step_voltage
        except Exception as e:
            self.status_update.emit(f"OVP测试执行错误: {str(e)}", True)
            print(f"OVP测试执行错误: {str(e)}")

    def thread_uvp_test(self, vbat_channel=1, vol_channel=2, start_voltage=0.7, end_voltage=1.5, step_voltage=0.1):
        try:
            self.n6705c.set_mode(vol_channel, "CVLoad")
            self.n6705c.set_voltage(vol_channel, end_voltage)
            self.n6705c.channel_on(vol_channel)
            QThread.msleep(500)

            self.status_update.emit("执行UVP测试...", False)
            print(f"UVP测试: 起始电压={start_voltage:.3f} V, 结束电压={end_voltage:.3f} V, 步进电压={step_voltage:.3f} V")

            cnt_voltage = end_voltage
            while cnt_voltage >= start_voltage - 0.05 and self.is_running:
                current_before = float(self.n6705c.measure_current(vbat_channel))
                self.n6705c.set_voltage(vol_channel, cnt_voltage)
                QThread.msleep(100)
                current_after = float(self.n6705c.measure_current(vbat_channel))

                print(f"Test voltage: {cnt_voltage:.3f} V, current_before: {current_before * 1000:.4f} mA, current_after: {current_after * 1000:.4f} mA")

                if current_after < current_before - 0.01:
                    print(f"UVP触发，电压: {cnt_voltage:.3f} V, 电流: {current_after * 1000:.4f} mA")
                    self.result_update.emit("保护电压", cnt_voltage)
                    break

                cnt_voltage -= step_voltage
        except Exception as e:
            self.status_update.emit(f"UVP测试执行错误: {str(e)}", True)
            print(f"UVP测试执行错误: {str(e)}")


class PMUOSCPUI(QWidget):
    """PMU OSCP测试UI组件"""

    connection_status_changed = Signal(bool)

    def __init__(self):
        super().__init__()

        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []

        self.is_test_running = False
        self.test_thread = None

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()

        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._search_devices)
        self.search_timer.setSingleShot(True)

    def _setup_style(self):
        font = QFont("Segoe UI", 10)
        self.setFont(font)

        self.setStyleSheet("""
        QWidget {
            background-color: #050b1a;
            color: #e8eefc;
            font-family: "Segoe UI";
            font-size: 10pt;
        }


        QGroupBox {
            background-color: #0d1833;
            border: 1px solid #1a2a52;
            border-radius: 14px;
            margin-top: 12px;
            padding: 16px;
            font-weight: 600;
        }

        QGroupBox#oscpConfigGroup {
            padding: 12px;
        }
        QGroupBox#oscpConfigGroup QLabel {
            border: none;
            background: transparent;
            padding: 0px;
            margin: 0px 0px 1px 0px;
            min-height: 0px;
        }
        QGroupBox#oscpConfigGroup QLineEdit,
        QGroupBox#oscpConfigGroup QComboBox,
        QGroupBox#oscpConfigGroup QSpinBox,
        QGroupBox#oscpConfigGroup QDoubleSpinBox {
            padding: 4px 8px;
            min-height: 18px;
        }

        QGroupBox#oscpConfigGroup QLabel {
            border: none;
            background: transparent;
            padding: 0px;
            margin: 0px 0px 1px 0px;
            min-height: 0px;
            color: #8fa7d6;
            font-size: 9pt;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            top: -2px;
            padding: 0 6px;
            color: #f3f7ff;
            background: transparent;
        }

        QLabel {
            color: #aebcdf;
            background: transparent;
        }

        QGroupBox#oscpConfigGroup QLabel {
            border: none;
            background: transparent;
            padding: 0px;
            margin: 0px;
        }

        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #02091d;
            border: 1px solid #20335f;
            border-radius: 8px;
            padding: 8px 10px;
            min-height: 22px;
            color: #eef4ff;
            selection-background-color: #1fa3ff;
        }

        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border: 1px solid #2dd4ff;
        }

        QComboBox::drop-down {
            border: none;
            width: 24px;
            background: transparent;
        }

        QComboBox QAbstractItemView {
            background-color: #02091d;
            color: #eef4ff;
            border: 1px solid #20335f;
            selection-background-color: #1a3260;
            outline: 0px;
        }

        QComboBox QAbstractItemView::item {
            background-color: #02091d;
            color: #eef4ff;
            padding: 4px 8px;
        }

        QComboBox QAbstractItemView::item:hover {
            background-color: #1a3260;
        }

        QComboBox QFrame {
            background-color: #02091d;
            border: 1px solid #20335f;
        }

        QPushButton {
            background-color: #1a2748;
            color: #dce8ff;
            border: 1px solid #273a66;
            border-radius: 10px;
            padding: 10px 16px;
            min-height: 22px;
            font-weight: 600;
        }

        QPushButton:hover {
            background-color: #22345e;
            border: 1px solid #35508c;
        }

        QPushButton:pressed {
            background-color: #16233f;
        }

        QPushButton:disabled {
            background-color: #11182b;
            color: #5f6d8f;
            border: 1px solid #1c2742;
        }

        QPushButton#start_test_btn {
            background-color: #10b981;
            color: white;
            border: 1px solid #19d39a;
            border-radius: 10px;
            font-weight: 700;
        }

        QPushButton#start_test_btn:hover {
            background-color: #12c48a;
            border: 1px solid #33e6af;
        }

        QPushButton#start_test_btn:pressed {
            background-color: #0d9b6c;
        }

        QPushButton#stop_test_btn {
            background-color: #5a1531;
            color: #ff7f9c;
            border: 1px solid #8c234b;
            border-radius: 10px;
            font-weight: 700;
        }

        QPushButton#stop_test_btn:hover {
            background-color: #6f1a3c;
            border: 1px solid #b62f61;
            color: #ff9cb2;
        }

        QPushButton#stop_test_btn:pressed {
            background-color: #4c1229;
        }

        QPushButton[role="secondary"] {
            background-color: #1d2a49;
            color: #c8d7f5;
            border: 1px solid #26385f;
            border-radius: 8px;
        }

        QPushButton[role="secondary"]:hover {
            background-color: #24365c;
            border: 1px solid #355184;
        }

        QPushButton[role="outline"] {
            background-color: #081227;
            color: #c8d7f5;
            border: 1px solid #28406f;
            border-radius: 8px;
        }

        QPushButton[role="outline"]:hover {
            background-color: #0b1730;
            border: 1px solid #3b5b98;
        }

        QFrame#chartFrame {
            background-color: #02060f;
            border: 1px solid #1a2a52;
            border-radius: 10px;
        }

        QFrame[role="resultBox"] {
            background-color: #020b22;
            border: 1px solid #1a2d57;
            border-radius: 10px;
        }
        """)

    def _create_layout(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(14)

        # ================== Header ==================
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)

        title = QLabel("OSCP Automated Test")
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #f5f7ff;border: none;")
        subtitle = QLabel("Configure and execute OSCP validation sequences.")
        subtitle.setStyleSheet("font-size: 11px; color: #8fa7d6;border: none;")

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # ================== PMU System ==================
        top_group = QGroupBox("PMU System")
        top_layout = QGridLayout()
        top_layout.setHorizontalSpacing(12)
        top_layout.setVerticalSpacing(10)
        
        self.resource_label = QLabel("Resource")
        self.resource_label.setStyleSheet("font-size: 11px; color: #8fa7d6;border: none;")



        # ⌕
        self.visa_resource_combo = DarkComboBox(bg="#02091d", border="#20335f")
        self.visa_resource_combo.addItems(["TCPIP0::K-N6705C-06098.local::hislip0::INSTR"])
        self.search_btn = QPushButton("⌕")
        self.search_btn.setFixedWidth(44)

        self.instrument_info_label = QLabel("● N6705C")
        self.instrument_info_label.setStyleSheet("color:#d7e3ff; font-weight:600;border: none;")

        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("color:#7e8fb8;border: none;")

        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setProperty("role", "outline")

        top_layout.addWidget(self.resource_label, 0, 0)
        top_layout.addWidget(self.visa_resource_combo, 1, 0, 1, 6)
        top_layout.addWidget(self.search_btn, 1, 6)
        top_layout.addWidget(self.instrument_info_label, 1, 7)
        top_layout.addWidget(self.connection_status_label, 1, 8)
        top_layout.addWidget(self.connect_btn, 1, 9)
        top_layout.addWidget(self.disconnect_btn, 1, 10)

        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)

        # ================== Middle ==================
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(14)

        # -------- Config --------
        config_group = QGroupBox("OSCP Configuration")
        config_group.setObjectName("oscpConfigGroup")
        
        config_layout = QGridLayout()
        config_layout.setHorizontalSpacing(12)
        config_layout.setVerticalSpacing(4)

        self.test_type_combo = DarkComboBox(bg="#02091d", border="#20335f")
        self.test_type_combo.addItems(["OCP", "SCP", "OVP", "UVP"])

        self.device_addr_spin = QSpinBox()
        self.device_addr_spin.setRange(0, 0x3FF)

        self.reg_addr_spin = QSpinBox()
        self.reg_addr_spin.setRange(0, 0xFFFF)

        self.power_channel_combo = DarkComboBox(bg="#02091d", border="#20335f")
        self.power_channel_combo.addItems(["1", "2", "3", "4"])

        self.test_channel_combo = DarkComboBox(bg="#02091d", border="#20335f")
        self.test_channel_combo.addItems(["1", "2", "3", "4"])
        self.test_channel_combo.setCurrentIndex(1)

        self.msb_spin = QSpinBox()
        self.msb_spin.setRange(0, 0xFF)

        self.lsb_spin = QSpinBox()
        self.lsb_spin.setRange(0, 0xFF)

        self.start_spin = QDoubleSpinBox()
        self.end_spin = QDoubleSpinBox()
        self.step_spin = QDoubleSpinBox()
        self.protection_spin = QDoubleSpinBox()

        for spin in [self.start_spin, self.end_spin, self.step_spin, self.protection_spin]:
            spin.setDecimals(3)
            spin.setRange(0.0, 9999.0)
            spin.setSingleStep(0.01)

        self.start_spin.setValue(0.0)
        self.end_spin.setValue(0.0)
        self.step_spin.setValue(0.0)
        self.protection_spin.setValue(0.0)

        self.type_label = QLabel("Type")
        self.dev_addr_label = QLabel("Dev Addr")
        self.reg_addr_label = QLabel("Reg Addr")
        self.power_ch_label = QLabel("Power CH")
        self.test_ch_label = QLabel("Test CH")
        self.msb_label = QLabel("MSB")
        self.lsb_label = QLabel("LSB")
        self.start_label = QLabel("Start (A)")
        self.end_label = QLabel("End (A)")
        self.step_label = QLabel("Step (A)")
        self.protection_label = QLabel("OCP (A)")

        fields = [
            (self.type_label, self.test_type_combo),
            (self.dev_addr_label, self.device_addr_spin),
            (self.reg_addr_label, self.reg_addr_spin),
            (self.power_ch_label, self.power_channel_combo),
            (self.test_ch_label, self.test_channel_combo),
            (self.msb_label, self.msb_spin),
            (self.lsb_label, self.lsb_spin),
            (self.start_label, self.start_spin),
            (self.end_label, self.end_spin),
            (self.step_label, self.step_spin),
            (self.protection_label, self.protection_spin),
        ]

        row, col = 0, 0
        for text_label, widget in fields:
            config_layout.addWidget(text_label, row, col)
            config_layout.addWidget(widget, row + 1, col)
            col += 1
            if col >= 6:
                col = 0
                row += 2

        config_group.setLayout(config_layout)

        # -------- Control --------
        control_group = QGroupBox("Control")
        control_layout = QGridLayout()
        control_layout.setSpacing(10)

        self.start_test_btn = QPushButton("▶ START")
        self.start_test_btn.setObjectName("start_test_btn")
        self.start_test_btn.setMinimumHeight(40)

        self.stop_test_btn = QPushButton("■ STOP")
        self.stop_test_btn.setObjectName("stop_test_btn")
        self.stop_test_btn.setMinimumHeight(40)

        self.single_test_btn = QPushButton("SINGLE")
        self.iteration_test_btn = QPushButton("LOOP")
        self.test_btn = QPushButton("DEBUG")
        self.load_btn = QPushButton("Load")
        self.save_btn = QPushButton("Calibrate")
        self.reset_btn = QPushButton("Reset")
        self.abort_btn = QPushButton("⏻ Abort All")

        for btn in [self.single_test_btn, self.iteration_test_btn, self.test_btn, self.load_btn]:
            btn.setProperty("role", "secondary")
            btn.style().polish(btn)

        for btn in [self.save_btn, self.reset_btn]:
            btn.setProperty("role", "outline")
            btn.style().polish(btn)

        self.abort_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d1830;
                color: #ff6f96;
                border: 1px solid #5f2748;
                border-radius: 8px;
                padding: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #51203e;
            }
            QPushButton:disabled {
                background-color: #251421;
                color: #805469;
                border: 1px solid #3b2130;
            }
        """)

        control_layout.addWidget(self.start_test_btn, 0, 0)
        control_layout.addWidget(self.stop_test_btn, 0, 1)
        control_layout.addWidget(self.single_test_btn, 1, 0)
        control_layout.addWidget(self.iteration_test_btn, 1, 1)
        control_layout.addWidget(self.test_btn, 2, 0)
        control_layout.addWidget(self.load_btn, 2, 1)
        control_layout.addWidget(self.save_btn, 3, 0)
        control_layout.addWidget(self.reset_btn, 3, 1)
        control_layout.addWidget(self.abort_btn, 4, 0, 1, 2)

        control_group.setLayout(control_layout)

        mid_layout.addWidget(config_group, 4)
        mid_layout.addWidget(control_group, 1)

        main_layout.addLayout(mid_layout)

        # ================== Curve & Results ==================
        curve_group = QGroupBox("OSCP Curve & Results")
        curve_layout = QVBoxLayout()
        curve_layout.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.export_btn = QPushButton("Export")
        self.export_btn.setFixedWidth(90)
        top_bar.addWidget(self.export_btn)

        self.chart_placeholder = QFrame()
        self.chart_placeholder.setObjectName("chartFrame")
        self.chart_placeholder.setMinimumHeight(320)

        chart_inner_layout = QVBoxLayout(self.chart_placeholder)
        chart_inner_layout.setContentsMargins(0, 0, 0, 0)

        waiting_label = QLabel("Waiting for data...")
        waiting_label.setAlignment(Qt.AlignCenter)
        waiting_label.setStyleSheet("color:#536b9d; font-family:Consolas;")
        chart_inner_layout.addWidget(waiting_label)

        result_row = QHBoxLayout()
        result_row.setSpacing(12)

        self.result_boxes = []
        result_titles = ["PROTECT", "RECOVER", "TRIG", "REC"]

        for title_text in result_titles:
            box = QFrame()
            box.setProperty("role", "resultBox")
            box.style().polish(box)

            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(10, 8, 10, 8)

            title_lbl = QLabel(title_text)
            title_lbl.setAlignment(Qt.AlignCenter)
            title_lbl.setStyleSheet("color:#6b84b8; font-size:10px;")

            value_lbl = QLabel("---")
            value_lbl.setAlignment(Qt.AlignCenter)
            value_lbl.setStyleSheet("color:#f2f6ff; font-size:14px; font-weight:700;")

            box_layout.addWidget(title_lbl)
            box_layout.addWidget(value_lbl)
            result_row.addWidget(box)
            self.result_boxes.append(value_lbl)

        self.protection_current_label = self.result_boxes[0]
        self.recovery_current_label = self.result_boxes[1]
        self.trigger_time_label = self.result_boxes[2]
        self.recovery_time_label = self.result_boxes[3]

        curve_layout.addLayout(top_bar)
        curve_layout.addWidget(self.chart_placeholder)
        curve_layout.addLayout(result_row)

        curve_group.setLayout(curve_layout)
        main_layout.addWidget(curve_group, 1)

    def _init_ui_elements(self):
        self.disconnect_btn.setEnabled(False)
        self.stop_test_btn.setEnabled(False)

        self.test_type_combo.currentIndexChanged.connect(self._update_test_config)

        self.search_btn.clicked.connect(self._on_search)
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn.clicked.connect(self._on_disconnect)

        self.start_test_btn.clicked.connect(self._on_single_test)
        self.stop_test_btn.clicked.connect(self._on_stop_test)

        self.single_test_btn.clicked.connect(self._on_single_test)
        self.iteration_test_btn.clicked.connect(self._on_iteration_test)
        self.test_btn.clicked.connect(self.debug_test)

        self._update_test_config()

    def _update_test_config(self, index=None):
        test_type = self.test_type_combo.currentText()

        if test_type in ["OCP", "SCP"]:
            self.start_label.setText("Start (A)")
            self.end_label.setText("End (A)")
            self.step_label.setText("Step (A)")
            self.protection_label.setText("OCP (A)" if test_type == "OCP" else "SCP (A)")

            self.start_spin.setRange(0.0, 10.0)
            self.end_spin.setRange(0.0, 10.0)
            self.step_spin.setRange(0.001, 1.0)
            self.protection_spin.setRange(0.0, 10.0)

            self.start_spin.setSingleStep(0.001)
            self.end_spin.setSingleStep(0.001)
            self.step_spin.setSingleStep(0.001)
            self.protection_spin.setSingleStep(0.001)

            self.start_spin.setDecimals(3)
            self.end_spin.setDecimals(3)
            self.step_spin.setDecimals(4)
            self.protection_spin.setDecimals(3)
        else:
            self.start_label.setText("Start (V)")
            self.end_label.setText("End (V)")
            self.step_label.setText("Step (V)")
            self.protection_label.setText("OVP (V)" if test_type == "OVP" else "UVP (V)")

            self.start_spin.setRange(0.0, 20.0)
            self.end_spin.setRange(0.0, 20.0)
            self.step_spin.setRange(0.001, 2.0)
            self.protection_spin.setRange(0.0, 20.0)

            self.start_spin.setSingleStep(0.001)
            self.end_spin.setSingleStep(0.001)
            self.step_spin.setSingleStep(0.001)
            self.protection_spin.setSingleStep(0.001)

            self.start_spin.setDecimals(3)
            self.end_spin.setDecimals(3)
            self.step_spin.setDecimals(4)
            self.protection_spin.setDecimals(3)

    def get_test_config(self):
        test_type = self.test_type_combo.currentText()

        config = {
            "test_type": test_type,
            "power_channel": self.power_channel_combo.currentText(),
            "test_channel": self.test_channel_combo.currentText(),
            "device_address": self.device_addr_spin.value(),
            "register_address": self.reg_addr_spin.value(),
            "msb": self.msb_spin.value(),
            "lsb": self.lsb_spin.value(),
        }

        if test_type in ["OCP", "SCP"]:
            config.update({
                "current_channel": self.test_channel_combo.currentText(),
                "current_start": self.start_spin.value(),
                "current_end": self.end_spin.value(),
                "current_step": self.step_spin.value(),
            })
            if test_type == "OCP":
                config["ocp_value"] = self.protection_spin.value()
            else:
                config["scp_value"] = self.protection_spin.value()
        else:
            config.update({
                "voltage_channel": self.test_channel_combo.currentText(),
                "voltage_start": self.start_spin.value(),
                "voltage_end": self.end_spin.value(),
                "voltage_step": self.step_spin.value(),
            })
            if test_type == "OVP":
                config["ovp_value"] = self.protection_spin.value()
            else:
                config["uvp_value"] = self.protection_spin.value()

        return config

    def set_test_running(self, running):
        self.start_test_btn.setEnabled(not running)
        self.stop_test_btn.setEnabled(running)

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
            self.save_btn,
            self.load_btn,
            self.search_btn,
            self.connect_btn,
            self.disconnect_btn,
        ]

        for widget in widgets:
            widget.setEnabled(not running)

    def _on_single_test(self):
        if self.is_test_running:
            self.set_system_status("测试正在运行中...", True)
            return

        config = self.get_test_config()
        test_type = config["test_type"]

        if not self.is_connected or self.n6705c is None:
            self.set_system_status("请先连接N6705C仪器", True)
            return

        self.clear_results()
        self.set_system_status("测试进行中")
        self.is_test_running = True
        self.set_test_running(True)

        config_copy = config.copy()
        config_copy.pop("test_type", None)

        self.test_thread = TestThread(test_type, self.n6705c, **config_copy)
        self.test_thread.status_update.connect(self.set_system_status)
        self.test_thread.result_update.connect(self._on_test_result)
        self.test_thread.test_finished.connect(self._on_test_finished)
        self.test_thread.start()

        print("执行单次测试，配置:", config)

    def _on_stop_test(self):
        if self.is_test_running and self.test_thread:
            self.set_system_status("正在停止测试...")
            self.test_thread.stop()
            self.test_thread.wait(1000)
            self._on_test_finished(False)

    def _on_iteration_test(self):
        self.set_system_status("执行遍历测试...")
        config = self.get_test_config()
        print("执行遍历测试，配置:", config)

    def _on_test_result(self, result_type, value):
        if result_type == "保护电压":
            self.protection_current_label.setText(f"{value:.3f} V")
        elif result_type == "保护电流":
            self.protection_current_label.setText(f"{value:.3f} A")

    def _on_test_finished(self, success):
        self.is_test_running = False
        self.set_test_running(False)

        if success:
            self.set_system_status("测试完成")
        else:
            self.set_system_status("测试停止", True)

        if self.test_thread:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_thread = None

    def update_test_result(self, result):
        if "protection_current" in result:
            self.protection_current_label.setText(f"{result['protection_current']:.4f} A")
        if "recovery_current" in result:
            self.recovery_current_label.setText(f"{result['recovery_current']:.4f} A")
        if "trigger_time" in result:
            self.trigger_time_label.setText(f"{result['trigger_time']:.4f} ms")
        if "recovery_time" in result:
            self.recovery_time_label.setText(f"{result['recovery_time']:.4f} ms")

    def clear_results(self):
        self.protection_current_label.setText("---")
        self.recovery_current_label.setText("---")
        self.trigger_time_label.setText("---")
        self.recovery_time_label.setText("---")

    def set_system_status(self, status, is_error=False):
        self.connection_status_label.setText(status)
        if is_error:
            self.connection_status_label.setStyleSheet("color: #ff7f9c; font-weight: 600;")
        elif status == "测试进行中":
            self.connection_status_label.setStyleSheet("color: #f7c948; font-weight: 600;")
        elif status in ["已连接", "测试完成"]:
            self.connection_status_label.setStyleSheet("color: #10b981; font-weight: 600;")
        else:
            self.connection_status_label.setStyleSheet("color: #aebcdf; font-weight: 600;")

    def update_instrument_info(self, instrument_info):
        self.instrument_info_label.setText(instrument_info)

    def _on_search(self):
        self.set_system_status("搜索中...")
        self.search_btn.setEnabled(False)
        self.search_timer.start(100)

    def _search_devices(self):
        try:
            if self.rm is None:
                try:
                    self.rm = pyvisa.ResourceManager()
                except Exception:
                    self.rm = pyvisa.ResourceManager('@ni')

            self.available_devices = list(self.rm.list_resources()) or []

            compatible_devices = self.available_devices.copy()
            n6705c_devices = []

            for dev in compatible_devices:
                try:
                    instr = self.rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()

                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception:
                    pass

            self.visa_resource_combo.clear()

            if n6705c_devices:
                for dev in n6705c_devices:
                    self.visa_resource_combo.addItem(dev)

                self.set_system_status(f"找到 {len(n6705c_devices)} 个N6705C设备")
                self.connect_btn.setEnabled(True)
                self.visa_resource_combo.setEnabled(True)

                default_device = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"
                if default_device in n6705c_devices:
                    self.visa_resource_combo.setCurrentText(default_device)
                else:
                    self.visa_resource_combo.setCurrentIndex(0)
            else:
                self.visa_resource_combo.addItem("未找到N6705C设备")
                self.visa_resource_combo.setEnabled(False)
                self.set_system_status("未找到N6705C设备", True)
                self.connect_btn.setEnabled(False)

        except Exception as e:
            print(f"搜索过程中发生错误: {str(e)}")
            self.set_system_status(f"搜索失败: {str(e)}", True)
            self.connect_btn.setEnabled(False)
        finally:
            self.search_btn.setEnabled(True)

    def _on_connect(self):
        device_address = self.visa_resource_combo.currentText()
        if not device_address or "未找到" in device_address:
            self.set_system_status("无可连接设备", True)
            return

        self.set_system_status("连接中...")
        self.connect_btn.setEnabled(False)

        try:
            self.n6705c = N6705C(device_address)
            idn = self.n6705c.instr.query("*IDN?").strip()

            if "N6705C" in idn:
                self.is_connected = True
                self.set_system_status("已连接")

                self.disconnect_btn.setEnabled(True)
                self.search_btn.setEnabled(False)
                self.visa_resource_combo.setEnabled(False)

                try:
                    device_name = device_address.split("::")[1]
                except Exception:
                    device_name = device_address

                self.instrument_info_label.setText(f"● N6705C ({device_name}) + MSO64B")
                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("设备不匹配", True)
                self.connect_btn.setEnabled(True)

        except Exception as e:
            self.set_system_status(f"连接失败: {str(e)}", True)
            self.connect_btn.setEnabled(True)

    def _on_disconnect(self):
        self.set_system_status("断开中...")
        self.disconnect_btn.setEnabled(False)

        try:
            if self.n6705c is not None:
                if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                    self.n6705c.instr.close()
                if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                    self.n6705c.rm.close()

            self.n6705c = None
            self.is_connected = False

            self.set_system_status("Disconnected")
            self.connect_btn.setEnabled(True)
            self.search_btn.setEnabled(True)
            self.visa_resource_combo.setEnabled(True)

            self.instrument_info_label.setText("● N6705C + MSO64B")
            self.connection_status_changed.emit(False)

        except Exception as e:
            self.set_system_status(f"断开失败: {str(e)}", True)
            self.disconnect_btn.setEnabled(True)

    def get_n6705c_instance(self):
        return self.n6705c

    def is_n6705c_connected(self):
        return self.is_connected

    def debug_test(self):
        self.set_system_status("执行Debug测试...")
        try:
            if self.n6705c is None:
                self.n6705c = N6705C("TCPIP0::K-N6705C-06098.local::hislip0::INSTR")
            self.ovp_test(1, 2, 1.33, 1.5, 0.001)
            # self.uvp_test(1, 2, 0.5, 0.55, 0.001)
        except Exception as e:
            self.set_system_status(f"Debug失败: {e}", True)

    def ovp_test(self, vbat_channel=1, vol_channel=2, start_voltage=0.7, end_voltage=1.5, step_voltage=0.1):
        self.n6705c.set_mode(vol_channel, "PS2Q")
        self.n6705c.set_voltage(vol_channel, start_voltage)
        self.n6705c.channel_on(vol_channel)
        time.sleep(0.5)

        self.set_system_status("执行OVP测试...")
        print(f"OVP测试: 起始电压={start_voltage:.3f} V, 结束电压={end_voltage:.3f} V, 步进电压={step_voltage:.3f} V")

        cnt_voltage = start_voltage
        while cnt_voltage <= end_voltage + 0.001:
            current_before = float(self.n6705c.measure_current(vbat_channel))
            self.n6705c.set_voltage(vol_channel, cnt_voltage)
            time.sleep(0.5)
            current_after = float(self.n6705c.measure_current(vbat_channel))

            print(f"Test voltage: {cnt_voltage:.3f} V, current_before: {current_before * 1000:.4f} mA, current_after: {current_after * 1000:.4f} mA")

            if current_after < current_before - 0.00001:
                print(f"OVP触发，电压: {cnt_voltage:.3f} V, 电流: {current_after * 1000:.4f} mA")
                self.protection_current_label.setText(f"{cnt_voltage:.3f} V")
                break

            cnt_voltage += step_voltage

    def uvp_test(self, vbat_channel=1, vol_channel=2, start_voltage=0.7, end_voltage=1.5, step_voltage=0.1):
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

            print(f"Test voltage: {cnt_voltage:.3f} V, current_before: {current_before * 1000:.4f} mA, current_after: {current_after * 1000:.4f} mA")

            if current_after < current_before - 0.01:
                print(f"UVP触发，电压: {cnt_voltage:.3f} V, 电流: {current_after * 1000:.4f} mA")
                self.protection_current_label.setText(f"{cnt_voltage:.3f} V")
                break

            cnt_voltage -= step_voltage

    def i2c_test(self):
        self.set_system_status("执行I2C测试...")

        try:
            i2c = I2CInterface()
            self.set_system_status("I2C接口初始化成功")

            device_addr = 0x17
            width_flag = I2CWidthFlag.BIT_10

            reg_addr_read = 0x0000
            print(f"\n1. 读取操作：")
            print(f"   设备地址: 0x{device_addr:02X}")
            print(f"   寄存器地址: 0x{reg_addr_read:04X}")
            print(f"   位宽模式: {width_flag.name}")

            read_data = i2c.read(device_addr, reg_addr_read, width_flag)
            print(f"   读取结果: 0x{read_data:04X}")
            self.set_system_status(f"I2C读取成功: 0x{read_data:04X}")

            reg_addr_write = 0x1e7
            write_data = 0x20AA
            print(f"\n2. 写入操作：")
            print(f"   设备地址: 0x{device_addr:02X}")
            print(f"   寄存器地址: 0x{reg_addr_write:04X}")
            print(f"   写入数据: 0x{write_data:04X}")
            print(f"   位宽模式: {width_flag.name}")

            i2c.write(device_addr, reg_addr_write, write_data, width_flag)
            print("   写入成功")
            self.set_system_status("I2C写入成功")

            time.sleep(0.1)
            print(f"\n3. 验证写入结果：")
            verify_data = i2c.read(device_addr, reg_addr_write, width_flag)
            print(f"   寄存器地址0x{reg_addr_write:04X}的当前值: 0x{verify_data:04X}")
            print(f"   验证{'成功' if verify_data == write_data else '失败'}")

            if verify_data == write_data:
                self.set_system_status("I2C测试完成，验证成功")
            else:
                self.set_system_status("I2C测试完成，但验证失败", True)

            return True

        except Exception as e:
            error_msg = f"I2C测试操作失败: {e}"
            print(error_msg)
            self.set_system_status(error_msg, True)
            return False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    pmu_test_ui = PMUOSCPUI()
    pmu_test_ui.setWindowTitle("PMU OSCP Automated Test")
    pmu_test_ui.resize(1560, 820)
    pmu_test_ui.show()

    sys.exit(app.exec())