#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Single Vmin Test 子页面

在 VminHunter 探底找到 Vmin 电压后，于指定电压点单次执行 Vmin 测试序列
（唤醒 -> STATUS 睡眠 -> 降压保持 -> 恢复 -> STATUS 唤醒 -> 判活），
用于流程确认。

复用 VminHunterUI 的连接面板 / Channel Config / 结果表与 core 引擎编排，
仅将"电压扫描配置"替换为"单点电压配置"（Default + Vmin 单点）。
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QCheckBox, QFrame, QMessageBox,
)

from ui.pages.vmin_hunter.vmin_hunter_ui import VminHunterUI, _TEST_MODES
from ui.widgets.dark_combobox import DarkComboBox
from log_config import get_logger

logger = get_logger(__name__)


class VminSingleTestUI(VminHunterUI):
    """单次 Vmin 测试页面：在指定 Vmin 电压点执行一次完整测试序列。"""

    def __init__(self, n6705c_top=None, instrument_manager=None, parent=None):
        super().__init__(n6705c_top=n6705c_top,
                         instrument_manager=instrument_manager, parent=parent)
        self.page_title.setText("Single Vmin Test")
        self.page_subtitle.setText(
            "Run the Vmin test sequence once at the found Vmin voltage to confirm the flow."
        )
        self.start_btn.setText("Start Test")

    # ------------------------------------------------------------------
    # Test Config 面板（单点电压配置，替代父类扫描配置）
    # ------------------------------------------------------------------
    def _create_test_config_panel(self):
        panel = QFrame()
        panel.setObjectName("vhPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        layout.addLayout(self._section_title("activity.svg", "Test Config", "#5b9cf5"))

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)

        form.addWidget(self._field_label("Test CNT"), 0, 0)
        self.test_cnt_input = QLineEdit("1")
        self.test_cnt_input.setToolTip("Number of test iterations at the Vmin voltage")
        form.addWidget(self.test_cnt_input, 0, 1)

        form.addWidget(self._field_label("Test Mode"), 1, 0)
        self.test_mode_combo = DarkComboBox(bg="#091426", border="#17345f")
        for key, label in _TEST_MODES:
            self.test_mode_combo.addItem(label, key)
        # 同父类：吞掉滚轮，防止页面滚动误切换 Test Mode
        self.test_mode_combo.installEventFilter(self)
        form.addWidget(self.test_mode_combo, 1, 1)

        layout.addLayout(form)

        # ---- 温度控制 ----
        temp_row = QHBoxLayout()
        temp_row.setSpacing(6)
        self.temp_enable_cb = QCheckBox("Temperature Control")
        self.temp_enable_cb.setStyleSheet("color: #dbe7ff; font-size: 11px; font-weight: 600;")
        temp_row.addWidget(self.temp_enable_cb)
        temp_row.addStretch()
        layout.addLayout(temp_row)

        self.temp_points_input = QLineEdit("-40, 25, 85")
        self.temp_points_input.setToolTip("Temperature points (°C), comma separated")
        self.temp_points_input.setEnabled(False)
        layout.addWidget(self._labeled("Temp Points (°C)", self.temp_points_input))

        # ---- 监测通道 ----
        ch_title = QLabel("Monitor Channels")
        ch_title.setObjectName("fieldLabel")
        layout.addWidget(ch_title)

        ch_row = QHBoxLayout()
        ch_row.setSpacing(12)
        self.vcorem_cb = QCheckBox("VcoreM (required)")
        self.vcorem_cb.setChecked(True)
        self.vcorem_cb.setEnabled(False)
        self.vcorem_cb.setStyleSheet("color: #dbe7ff; font-size: 11px; font-weight: 600;")
        self.vcorel_cb = QCheckBox("VcoreL (optional)")
        self.vcorel_cb.setStyleSheet("color: #dbe7ff; font-size: 11px; font-weight: 600;")
        ch_row.addWidget(self.vcorem_cb)
        ch_row.addWidget(self.vcorel_cb)
        ch_row.addStretch()
        layout.addLayout(ch_row)

        # ---- 单点电压配置 ----
        volt_title = QLabel("Single Voltage Configuration")
        volt_title.setObjectName("vhSweepHeader")
        layout.addWidget(volt_title)

        self.voltage_default_input = QLineEdit("0.80")
        self.voltage_default_input.setToolTip("Default voltage (V): wake/restore voltage around the sleep point")
        self.vmin_voltage_input = QLineEdit("0.70")
        self.vmin_voltage_input.setToolTip("Vmin voltage (V): the sleep voltage point to confirm")

        volt_grid = QGridLayout()
        volt_grid.setHorizontalSpacing(12)
        volt_grid.setVerticalSpacing(8)
        volt_grid.addLayout(self._sweep_field("Default (V)", self.voltage_default_input), 0, 0)
        volt_grid.addLayout(self._sweep_field("Vmin (V)", self.vmin_voltage_input), 0, 1)
        volt_grid.setColumnStretch(0, 1)
        volt_grid.setColumnStretch(1, 1)
        layout.addLayout(volt_grid)

        self.vcorel_default_input = QLineEdit("0.80")
        self.vcorel_default_input.setToolTip("VcoreL default voltage (V)")
        self.vcorel_vmin_input = QLineEdit("0.70")
        self.vcorel_vmin_input.setToolTip("VcoreL Vmin voltage (V): the sleep voltage point to confirm")

        self._vcorel_volt_box = QWidget()
        self._vcorel_volt_box.setObjectName("vhSingleVcorelBox")
        self._vcorel_volt_box.setStyleSheet(
            "QWidget#vhSingleVcorelBox { background: transparent; border: none; }"
        )
        vcorel_grid = QGridLayout(self._vcorel_volt_box)
        vcorel_grid.setContentsMargins(0, 0, 0, 0)
        vcorel_grid.setHorizontalSpacing(12)
        vcorel_grid.setVerticalSpacing(8)
        vcorel_grid.addLayout(self._sweep_field("VcoreL Default (V)", self.vcorel_default_input), 0, 0)
        vcorel_grid.addLayout(self._sweep_field("VcoreL Vmin (V)", self.vcorel_vmin_input), 0, 1)
        vcorel_grid.setColumnStretch(0, 1)
        vcorel_grid.setColumnStretch(1, 1)
        self._vcorel_volt_box.setVisible(False)
        layout.addWidget(self._vcorel_volt_box)

        hint = QLabel(
            "Run the sleep / drop / hold / restore / wake sequence once at the "
            "given Vmin voltage to confirm the test flow after hunting."
        )
        hint.setObjectName("sweepHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return panel

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------
    def _on_vcorel_toggled(self, checked):
        self._vcorel_enabled = checked
        self._vcorel_iic["card"].setVisible(checked)
        self._set_iic_group_enabled(self._vcorel_iic, checked)
        for w in self._vcorel_n6705c_widgets:
            w.setVisible(checked)
        self._vcorel_volt_box.setVisible(checked)

    # ------------------------------------------------------------------
    # 参数读取 / 配置导入导出
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_voltage_value(text, field):
        try:
            return float(str(text).strip())
        except ValueError:
            raise ValueError(f"{field} must be a number")

    def _read_params(self):
        try:
            test_cnt = int(self.test_cnt_input.text().strip())
        except ValueError:
            raise ValueError("Test CNT must be an integer")
        if test_cnt <= 0:
            raise ValueError("Test CNT must be positive")

        default_v = self._parse_voltage_value(
            self.voltage_default_input.text(), "Default Voltage")
        vmin_v = self._parse_voltage_value(
            self.vmin_voltage_input.text(), "Vmin Voltage")

        vcorel_sweep = None
        vcorel_points = []
        if self._vcorel_enabled:
            vl_default = self._parse_voltage_value(
                self.vcorel_default_input.text(), "VcoreL Default Voltage")
            vl_vmin = self._parse_voltage_value(
                self.vcorel_vmin_input.text(), "VcoreL Vmin Voltage")
            vcorel_sweep = {"default": vl_default}
            vcorel_points = [vl_vmin]

        params = {
            "test_cnt": test_cnt,
            "test_mode": self.test_mode_combo.currentData(),
            "test_items": {
                "sleep_probe": self.sleep_probe_cb.isChecked(),
                "wake_popup": self.wake_popup_cb.isChecked(),
            },
            "temperature": {
                "enable": self._temp_enabled,
                "points": self._parse_float_list(self.temp_points_input.text(), "Temp Points")
                if self._temp_enabled else [],
            },
            "monitor_channels": {
                "VcoreM": True,
                "VcoreL": self._vcorel_enabled,
            },
            "voltage_sweep": {
                "default": default_v,
            },
            "voltage_points": [vmin_v],
            "vcorel_voltage_sweep": vcorel_sweep,
            "vcorel_voltage_points": vcorel_points,
            "channel_config": {
                "n6705c": {
                    "VcoreM_channel": int(self.vcorem_channel_combo.currentText()),
                    "VcoreL_channel": int(self.vcorel_channel_combo.currentText()),
                    "VcoreM_current_limit_ma": self.vcorem_ilimit_spin.value(),
                    "VcoreL_current_limit_ma": self.vcorel_ilimit_spin.value(),
                },
                "iic": {
                    "VcoreM": self._read_iic_group(self._vcorem_iic),
                    "VcoreL": self._read_iic_group(self._vcorel_iic),
                },
            },
            "uart": {
                "port": self.get_selected_serial_port() or "",
                "baudrate": int(self._serial_baudrate),
            },
            "alive_rule": getattr(self, "_serial_alive_rule", None) or {
                "wake_pattern": self._wake_pattern,
                "sleep_pattern": self._sleep_pattern,
            },
        }
        return params

    def _apply_config(self, data):
        try:
            self.test_cnt_input.setText(str(data.get("test_cnt", 1)))
            mode = data.get("test_mode", "internal")
            for i in range(self.test_mode_combo.count()):
                if self.test_mode_combo.itemData(i) == mode:
                    self.test_mode_combo.setCurrentIndex(i)
                    break

            temp = data.get("temperature", {})
            self.temp_enable_cb.setChecked(bool(temp.get("enable", False)))
            if temp.get("points"):
                self.temp_points_input.setText(", ".join(str(p) for p in temp["points"]))

            test_items = data.get("test_items", {})
            self.sleep_probe_cb.setChecked(bool(test_items.get("sleep_probe", True)))
            self.wake_popup_cb.setChecked(bool(test_items.get("wake_popup", False)))

            channels = data.get("monitor_channels", {})
            self.vcorel_cb.setChecked(bool(channels.get("VcoreL", False)))

            sweep = data.get("voltage_sweep")
            if isinstance(sweep, dict) and sweep.get("default") is not None:
                self.voltage_default_input.setText(str(sweep["default"]))

            vmin = data.get("vmin_voltage")
            if vmin is None:
                points = data.get("voltage_points")
                if isinstance(points, list) and points:
                    try:
                        vmin = min(float(v) for v in points)
                    except (TypeError, ValueError):
                        vmin = None
            if vmin is not None:
                self.vmin_voltage_input.setText(str(vmin))

            vcorel_sweep = data.get("vcorel_voltage_sweep")
            if isinstance(vcorel_sweep, dict) and vcorel_sweep.get("default") is not None:
                self.vcorel_default_input.setText(str(vcorel_sweep["default"]))
            vcorel_points = data.get("vcorel_voltage_points")
            if isinstance(vcorel_points, list) and vcorel_points:
                try:
                    self.vcorel_vmin_input.setText(
                        str(min(float(v) for v in vcorel_points)))
                except (TypeError, ValueError):
                    logger.warning("Invalid vcorel_voltage_points in config", exc_info=True)

            self._apply_channel_and_link_config(data)
        except (TypeError, ValueError):
            logger.error("Failed to apply Single Vmin Test config", exc_info=True)
            QMessageBox.warning(self, "Import Warning", "Config partially applied; some fields invalid.")
