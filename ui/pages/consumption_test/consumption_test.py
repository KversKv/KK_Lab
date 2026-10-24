#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test UI组件
用于对DUT进行固件下载和功耗测试

视图已按职责平移拆分为同包 Mixin（行为零变更）：
view_config / view_panels / view_results / view_device /
view_chip_config / view_mcu / view_test_exec / view_ai；
MCU 后台 Worker 下沉 core/consumption_test/workers/mcu_workers.py。
"""

import sys
from resource_path import get_resource_base

sys.path.append(get_resource_base())
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.serialCom_module.serialCom_module_frame import (
    SerialComMixin,
    MODE_INLINE,
)
from PySide6.QtWidgets import (
    QWidget,
    QApplication,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from ui.widgets.config_memory import ConfigMemory
from ui.theme import (
    Colors,
    Radius,
)
from ui.styles import get_page_base_qss
from core.consumption_test.consumption_controller import ConsumptionController
from ui.pages.consumption_test.view_config import ConsumptionTestViewConfigMixin
from ui.pages.consumption_test.view_results import ConsumptionTestViewResultsMixin
from ui.pages.consumption_test.view_panels import ConsumptionTestViewPanelsMixin
from ui.pages.consumption_test.view_device import ConsumptionTestViewDeviceMixin
from ui.pages.consumption_test.view_chip_config import ConsumptionTestViewChipConfigMixin
from ui.pages.consumption_test.view_mcu import ConsumptionTestViewMcuMixin
from ui.pages.consumption_test.view_test_exec import ConsumptionTestViewTestExecMixin
from ui.pages.consumption_test.view_ai import ConsumptionTestViewAiMixin


class ConsumptionTestUI(QWidget, ConsumptionTestViewConfigMixin, ConsumptionTestViewResultsMixin, ConsumptionTestViewPanelsMixin, ConsumptionTestViewDeviceMixin, ConsumptionTestViewChipConfigMixin, ConsumptionTestViewMcuMixin, ConsumptionTestViewTestExecMixin, ConsumptionTestViewAiMixin, N6705CConnectionMixin, SerialComMixin):
    connection_status_changed = Signal(bool)
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    CHANNEL_COLORS_LIST = [
        {"accent": "#d4a514", "bg": "#1a1708", "border": "#3d2e08"},
        {"accent": "#18b67a", "bg": "#081a14", "border": "#0a3d28"},
        {"accent": "#2f6fed", "bg": "#081028", "border": "#0c2a5e"},
        {"accent": "#d14b72", "bg": "#1a080e", "border": "#3d0c22"},
        {"accent": "#a855f7", "bg": "#150a20", "border": "#3a1a5e"},
        {"accent": "#06b6d4", "bg": "#081a1e", "border": "#0a3d4a"},
        {"accent": "#f97316", "bg": "#1a1008", "border": "#3d2808"},
        {"accent": "#ec4899", "bg": "#1a0812", "border": "#3d0c28"},
    ]

    NAME_OPTIONS = ["Vbat", "Vcore", "VcoreM", "VcoreL", "VANA", "VHPPA", "Vusb"]

    SINGLE_DEVICE_CHANNEL_CONFIGS = [
        {"name": "Vbat", "channel": "A-CH1", "enabled": True},
        {"name": "Vcore", "channel": "A-CH2", "enabled": True},
        {"name": "VANA", "channel": "A-CH3", "enabled": True},
        {"name": "VHPPA", "channel": "A-CH4", "enabled": True},
    ]

    DUAL_DEVICE_CHANNEL_CONFIGS = [
        {"name": "Vbat", "channel": "A-CH1", "enabled": True},
        {"name": "Vcore", "channel": "A-CH2", "enabled": True},
        {"name": "VANA", "channel": "A-CH3", "enabled": True},
        {"name": "VHPPA", "channel": "A-CH4", "enabled": True},
        {"name": "CH5", "channel": "B-CH1", "enabled": False},
        {"name": "CH6", "channel": "B-CH2", "enabled": False},
        {"name": "CH7", "channel": "B-CH3", "enabled": False},
        {"name": "CH8", "channel": "B-CH4", "enabled": False},
    ]

    def __init__(self, n6705c_top=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry
        self.n6705c_a = None
        self.n6705c_b = None
        self.is_connected_a = False
        self.is_connected_b = False
        self.mcu_io = None
        self.is_mcu_connected = False
        self._mcu_search_thread = None
        self._mcu_search_worker = None
        self._mcu_connect_thread = None
        self._mcu_connect_worker = None
        self._mcu_highz_thread = None
        self._mcu_highz_worker = None
        self._io_state_thread = None
        self._io_state_worker = None
        self._default_mcu_type = "ch9114f"

        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)
        self.init_serial_connection(mode=MODE_INLINE, prefix="DUT Serial")

        self.firmware_path = ""
        self.firmware_paths = []
        self.config_content = ""
        self.selected_chip_config = None
        self.is_testing = False

        self._test_thread = None
        self._test_worker = None
        self._download_thread = None
        self._download_worker = None
        self._chip_check_thread = None
        self._chip_check_worker = None
        self._auto_test_thread = None
        self._auto_test_worker = None
        self._bin_results_data = []
        self._current_total_bins = 0

        self._channel_configs = []
        self._channel_config_widgets = []
        self._syncing = False

        self._pending_channel_selections = None
        self._pending_aux_selections = None
        self._suppress_preset_channels = False

        self.poweron_channel_combo = None
        self.reset_channel_combo = None
        self._saved_control_channels = {
            "N6705C": {"poweron": "B-CH1", "reset": "B-CH2"},
            "MCU": {"poweron": "GPIO0", "reset": "GPIO1"},
        }
        self._current_control_method = "MCU"

        self._controller = ConsumptionController(parent=self)
        self._controller.log_message.connect(self.append_log)
        self._controller.download_started.connect(self._on_ctrl_download_started)
        self._controller.download_state_changed.connect(self._on_ctrl_download_state_changed)
        self._controller.download_finished.connect(self._on_ctrl_download_finished)
        self._controller.download_error.connect(self._on_ctrl_download_error)
        self._controller.download_cleaned.connect(self._on_ctrl_download_cleaned)

        self._controller.auto_test_channel_result.connect(self._on_force_high_channel_result)
        self._controller.auto_test_summary.connect(self._on_test_summary)
        self._controller.auto_test_progress.connect(lambda v: self.auto_test_btn.setProgress(v))
        self._controller.auto_test_error.connect(self._on_auto_test_error)
        self._controller.auto_test_finished.connect(self._on_auto_test_finished)
        self._controller.auto_test_cleaned.connect(self._on_auto_test_thread_cleaned)

        self._setup_style()
        self._create_layout()
        self._sync_n6705c_dual_from_top()
        self._bind_mcu_manager_signals()
        self._sync_mcu_from_manager()

        # §5b：登记本页无专用接口的按钮为具名 UI 动作（白名单制，handler 复用原槽）
        self._register_ai_ui_actions()

        # 上次配置自动记忆：接口模式（get/apply 单一写入口）+ bind 补充接口
        # 未覆盖的页面级配置（DUT 串口 / MCU 端口下拉，仅恢复显示，绝不触发连接）
        self._config_memory = ConfigMemory("consumption_test/main", self)
        self._config_memory.bind_interface(
            self.get_test_config,
            lambda cfg: self.apply_config_to_controls(cfg, silent=True),
        )
        self._config_memory.bind("serial_port", self.serial_combo)
        self._config_memory.bind("mcu_port", self.mcu_port_combo)
        self._config_memory.watch(self)
        self._config_memory.restore()

    def _setup_style(self):
        self.setFont(QFont("Segoe UI", 9))
        self.setObjectName("ConsumptionTestRoot")
        _cb_icons = self._get_checkmark_path("5d45ff")
        page_extra = f"""
        QWidget#ConsumptionTestRoot {{
            background-color: {Colors.bg_secondary};
        }}

        QFrame#logContainer {{
            background-color: {Colors.bg_deep};
            border: 1px solid {Colors.border_secondary};
            border-radius: {Radius.container}px;
        }}

        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            image: url("__UNCHECKED__");
        }}

        QCheckBox::indicator:checked {{
            image: url("__CHECKED__");
        }}
        """.replace("__UNCHECKED__", _cb_icons['unchecked']).replace("__CHECKED__", _cb_icons['checked'])
        self.setStyleSheet(get_page_base_qss() + page_extra)

    def set_system_status(self, status, is_error=False):
        pass

    @property
    def logs_frame(self):
        """logs_frame 属性别名：暴露 execution_logs 给 AI 枢纽读取执行日志。

        枢纽 _get_ai_execution_logs 读 page.logs_frame._all_logs；
        本页 execution_logs 就是 ExecutionLogsFrame 实例。
        """
        return getattr(self, "execution_logs", None)

    def update_test_result(self, result):
        if isinstance(result, dict):
            for idx, cfg in enumerate(self._channel_configs):
                if not cfg["enabled"]:
                    continue
                key = cfg["channel"]
                if key in result:
                    self.update_channel_current(idx, result[key])

    def append_log(self, message):
        self.execution_logs.append_log(message)

    def _on_clear_log(self):
        self.execution_logs.clear_log()

    def clear_results(self):
        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")
        self._bin_results_data = []
        self._current_total_bins = 0
        self.bin_result_table.setRowCount(0)
        self.bin_result_table.hide()
        if hasattr(self, "_bin_result_header"):
            self._bin_result_header.hide()

    def get_test_mode(self):
        return "Consumption Test"

    def set_test_mode(self, mode):
        pass

    def get_test_id(self):
        return "CONSUMPTION_TEST_001"

    def set_test_id(self, test_id):
        pass


if __name__ == "__main__":
    from ui.standalone import resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = ConsumptionTestUI()
    win.setWindowTitle("Consumption Test")
    resize_and_center_window(win)
    win.show()

    sys.exit(app.exec())
