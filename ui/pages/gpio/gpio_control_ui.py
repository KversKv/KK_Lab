#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BES GPIO Workbench — DUT GPIO 控制页（暗色精密仪器工作台）。

布局：Top Bar（品牌 + DUT 副标题 / 5 大视图 Tab / i2c.bes_chip_check() 主按钮）
→ DUT 状态与 Bank 面板（Profile / Bank / 地址速览 / 遥测统计）
→ 批处理与掩码注入工具条（全组操作 / 32bit 掩码）
→ 中央主工作视口（Pin Matrix / Register Map / I2C Sniffer /
  JSON Config / Confirm Note 五大视图）。

硬件语义（严格 SET/CLR，杜绝读-改-写竞态）：
OUTPUT=Base+0x04 / INPUT=Base+0x10 / HIGH=Base+0x00 / LOW=Base+0x0C / 读=Base+0x50。
PU/PD/drv 为普通 RW 寄存器，必须 OP_BITS 位域写（DLL RMW）。

铁律：真实硬件读写一律走 core/gpio/ Worker（QThread），页面无阻塞 I2C。
方向寄存器无回读，模式状态仅会话内记忆。
"""

import sys
import os

if not getattr(sys, "frozen", False):
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QIcon

from ui.resource_path import get_resource_base
from core.gpio.gpio_config import (
    MODE_OUT_HIGH, MODE_OUT_LOW, MODE_IN_PULL_UP,
    MODE_IN_PULL_DOWN, OFFSET_OUT_SET, OFFSET_DIR_SET,
    OFFSET_OUT_CLR, OFFSET_DIR_CLR
)

from ui.pages.gpio.gpio_control.view_build import ViewBuildMixin
from ui.pages.gpio.gpio_control.state_refresh import StateRefreshMixin
from ui.pages.gpio.gpio_control.ops_mixin import OpsMixin
from ui.pages.gpio.gpio_control.features_mixin import FeaturesMixin

class GpioControlUI(ViewBuildMixin, StateRefreshMixin, OpsMixin, FeaturesMixin, QWidget):
    """BES GPIO Workbench：Detect DUT -> Bank 管理 -> 5 大视图 GPIO 操控。"""

    VIEW_TITLES = [
        ("Pin Matrix", "Pin Matrix Grid"),
        ("Register Map", "Register Map (low-level register view)"),
        ("I2C Sniffer", "I2C Bus Sniffer (bus transaction monitor)"),
        ("JSON Config", "DUT JSON Config (chip config file manager)"),
        ("Confirm Note", "DUT Confirmation Note (hardware checklist)"),
    ]

    MASK_TARGETS = [
        ("VAL_SET (+0x00)", OFFSET_OUT_SET),
        ("DIR_SET (+0x04)", OFFSET_DIR_SET),
        ("VAL_CLR (+0x0C)", OFFSET_OUT_CLR),
        ("DIR_CLR (+0x10)", OFFSET_DIR_CLR),
    ]

    # Pin Matrix 右键 Export Config 可导出配置（标签, mode）
    EXPORT_MODES = [
        ("Output High", MODE_OUT_HIGH),
        ("Output Low", MODE_OUT_LOW),
        ("Input Pull-Up", MODE_IN_PULL_UP),
        ("Input Pull-Down", MODE_IN_PULL_DOWN),
    ]
    _EXPORT_MODE_LABELS = {mode: label for label, mode in EXPORT_MODES}

    POLL_INTERVALS = [(200, "200 ms"), (500, "500 ms"),
                      (1000, "1000 ms"), (2000, "2000 ms")]

    SNIFF_KINDS = ["WRITE32", "READ32", "CHIP_CHECK", "ERROR"]

    _SNIFF_COLORS = {
        "WRITE32": "#22D3EE",
        "READ32": "#10B981",
        "CHIP_CHECK": "#A78BFA",
        "ERROR": "#EF4444",
    }

    def __init__(self, parent=None, ui_action_registry=None):
        super().__init__(parent)
        self.setObjectName("gpioPage")
        self._ui_action_registry = ui_action_registry
        self._cfg = None            # GpioChipConfig
        self._chip_info = None
        self._dev_addr = None
        self._cur_bank = 0
        self._selected = None       # (group, pin) 主选中脚（最后点击）
        self._selected_pins = []    # [(group, pin)] Ctrl 多选（有序，含主选中）
        self._pin_cards = {}        # (group, pin) -> _PinCard（当前 bank）
        self._pin_meta = {}         # (group, pin) -> {"alias": str}
        self._dir_shadow = {}       # bank_idx -> 32bit（会话影子，dir 无回读）
        self._out_shadow = {}       # bank_idx -> 32bit
        self._reg_shadow = {}       # addr -> 32bit（PU/PD/drv/任意写影子）
        self._in_value = {}         # bank_idx -> 32bit|None（0x50 最近读值）
        self._reg_cards = []        # [(kind, addr|None, card_widgets)]
        self._sniff_entries = []    # [(kind, raw, html)]
        self._sniff_kind = None     # None = All
        self._sniff_paused = False
        self._json_path = None
        self._thread = None
        self._worker = None
        self._worker_done_cb = None
        self._spin_angle = 0
        self._export_items = []     # [(group, pin, mode)] 导出管理器条目
        self._build_ui()

    def append_log(self, msg):
        self.execution_logs.append_log(msg)

    def closeEvent(self, event):
        self.cleanup_threads()
        super().closeEvent(event)


if __name__ == "__main__":
    """独立运行：python ui/pages/gpio/gpio_control_ui.py"""
    from ui.standalone import run_standalone_widget

    def _create_window():
        window = GpioControlUI()
        icon_path = os.path.join(
            get_resource_base(), "resources", "icons", "gpio_control_ui.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            window.setWindowIcon(icon)
            app = QApplication.instance()
            if app is not None:
                app.setWindowIcon(icon)
        return window

    sys.exit(run_standalone_widget(
        _create_window, "BES GPIO Workbench", size=(1200, 700)))
