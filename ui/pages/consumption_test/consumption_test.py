#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test UI组件
用于对DUT进行固件下载和功耗测试
"""

import sys
import os
from ui.resource_path import get_resource_base
import re
import json

try:
    import yaml
except ImportError:
    yaml = None

sys.path.append(get_resource_base())

from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin, MODE_INLINE
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QPlainTextEdit,
    QFrame, QApplication, QFileDialog,
    QCheckBox, QSizePolicy, QMessageBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QThread, QObject, QSize,
    QRectF, QRect, QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import (
    QFont, QIcon, QPixmap, QPainter, QColor, QPen,
    QFontMetrics
)
from PySide6.QtSvg import QSvgRenderer

from lib.download_tools.download_script import download_bin, DownloadMode, DownloadState, DownloadResult, detect_chip_from_bin
from chips.bes_chip_configs.bes_chip_configs import SUPPORTED_CHIPS, get_chip_config
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.progress_button import ProgressButton
from log_config import get_logger
from ui.theme import Colors, FontSizes, Radius, Spacing, FONT_FAMILY, FONT_MONO
from ui.styles import get_page_base_qss, SCROLLBAR_STYLE

from core.consumption_test.workers import (
    CURRENT_UNIT,
    _UNIT_CONFIG,
    _format_current_unified,
    _ChipCheckWorker,
    _ConsumptionTestForceHighWorker,
    _ConsumptionTestForceWorker,
)
from ui.pages.consumption_test.widgets import (
    DownloadModeToggle, ControlMethodToggle, PolarityToggle,
)
from ui.pages.consumption_test.view_config import ConsumptionTestViewConfigMixin
from ui.pages.consumption_test.view_results import ConsumptionTestViewResultsMixin
from ui.pages.consumption_test.view_panels import ConsumptionTestViewPanelsMixin
from core.consumption_test.consumption_controller import ConsumptionController

logger = get_logger(__name__)


class _SearchMcuPortWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, mcu_type="yd_rp2040"):
        super().__init__()
        self._mcu_type = mcu_type

    def run(self):
        try:
            if self._mcu_type == "ch9114f":
                from instruments.MCU_IO.ch9114f import (
                    list_ch9114f_ports, CH9114_USB_VID, CH9114_USB_PID,
                )
                import serial.tools.list_ports
                ports = list_ch9114f_ports() or []
                # 构建 device -> description 映射，补全下拉显示的完整端口名
                desc_map = {}
                for info in serial.tools.list_ports.comports():
                    if info.vid == CH9114_USB_VID and info.pid == CH9114_USB_PID:
                        desc_map[info.device] = info.description or info.device
                labels = [f"{p} - {desc_map.get(p, p)}" for p in ports]
                self.finished.emit(labels)
            else:
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                self.finished.emit([f"{p.device} - {p.description}" for p in ports])
        except Exception as e:
            logger.error("MCU port scan failed: %s", e, exc_info=True)
            self.error.emit(str(e))


class _ConnectMcuWorker(QObject):
    finished = Signal(object, str)
    error = Signal(str)

    def __init__(self, port, mcu_type="yd_rp2040", baudrate=921600):
        super().__init__()
        self._port = port
        self._mcu_type = mcu_type
        self._baudrate = baudrate

    def run(self):
        try:
            from instruments.factory import create_mcu_io
            if self._mcu_type == "ch9114f":
                inst = create_mcu_io("ch9114f", port=self._port)
            else:
                inst = create_mcu_io("yd_rp2040", port=self._port, baudrate=self._baudrate)
            ok = inst.connect()
            if not ok:
                self.error.emit(f"Failed to connect {self._port}")
                return
            self.finished.emit(inst, inst.identify())
        except Exception as e:
            logger.error("MCU IO connection failed: %s", e, exc_info=True)
            self.error.emit(str(e))


_ICONS_DIR = os.path.join(
    get_resource_base(),
    "resources", "icons"
)

_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "consumption_test_SVGs"
)

_MAIN_CHIP_CONFIGS_DIR = os.path.join(
    get_resource_base(),
    "chips", "bes_chip_configs", "main_chip_configs"
)

from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon


class ConsumptionTestUI(QWidget, ConsumptionTestViewConfigMixin, ConsumptionTestViewResultsMixin, ConsumptionTestViewPanelsMixin, N6705CConnectionMixin, SerialComMixin):
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

    def __init__(self, n6705c_top=None, instrument_manager=None):
        super().__init__()

        self._n6705c_top = n6705c_top
        self._instrument_manager = instrument_manager
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

    def _on_device_search(self, label):
        top = self._n6705c_top
        if top:
            is_conn = getattr(top, f"is_connected_{label.lower()}", False)
            if is_conn:
                return

        from debug_config import DEBUG_MOCK
        w = self._n6705c_conn_widgets[label]
        if DEBUG_MOCK:
            w["combo"].clear()
            w["combo"].addItem(f"DEBUG::MOCK::N6705C::{label}")
            w["status"].setText("● Mock Ready")
            w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[DEBUG] Mock device {label} loaded, skip real VISA scan.")
            return

        w["status"].setText("● Searching")
        w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
        w["search_btn"].setEnabled(False)
        w["connect_btn"].setEnabled(False)
        self.append_log(f"[SYSTEM] Scanning VISA resources for N6705C-{label}...")

        from ui.modules.n6705c_module_frame import _SearchN6705CWorker
        worker = _SearchN6705CWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda devs, lbl=label: self._on_device_search_done(lbl, devs))
        worker.error.connect(lambda err, lbl=label: self._on_device_search_error(lbl, err))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        setattr(self, f"_search_thread_{label}", thread)
        setattr(self, f"_search_worker_{label}", worker)
        thread.start()

    def _on_device_search_done(self, label, devices):
        w = self._n6705c_conn_widgets[label]
        w["combo"].setEnabled(True)
        w["combo"].clear()
        if devices:
            for dev in devices:
                w["combo"].addItem(dev)
            w["status"].setText(f"● Found {len(devices)}")
            w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[SYSTEM] Found {len(devices)} N6705C device(s) for slot {label}.")
        else:
            w["combo"].addItem("No N6705C device found")
            w["combo"].setEnabled(False)
            w["status"].setText("● Not Found")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
        w["search_btn"].setEnabled(True)
        w["connect_btn"].setEnabled(True)

    def _on_device_search_error(self, label, err):
        w = self._n6705c_conn_widgets[label]
        w["status"].setText("● Failed")
        w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
        self.append_log(f"[ERROR] Search failed for N6705C-{label}: {err}")
        w["search_btn"].setEnabled(True)
        w["connect_btn"].setEnabled(True)

    def _on_device_connect_or_disconnect(self, label):
        attr = label.lower()
        is_conn = getattr(self, f"is_connected_{attr}", False)
        if is_conn:
            self._disconnect_device(label)
        else:
            self._connect_device(label)

    def _connect_device(self, label):
        attr = label.lower()
        w = self._n6705c_conn_widgets[label]
        from debug_config import DEBUG_MOCK
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()

        if DEBUG_MOCK:
            from instruments.mock.mock_instruments import MockN6705C
            inst = MockN6705C()
            setattr(self, f"n6705c_{attr}", inst)
            setattr(self, f"is_connected_{attr}", True)
            _update_n6705c_btn_state(w["connect_btn"], connected=True)
            w["search_btn"].setEnabled(False)
            w["status"].setText("● Connected")
            w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[DEBUG] Mock N6705C-{label} connected.")
            visa = w["combo"].currentText()
            self._syncing = True
            try:
                if self._n6705c_top:
                    getattr(self._n6705c_top, f"connect_{attr}")(visa, inst, f"MOCK-{label}")
            finally:
                self._syncing = False
            new_count = self._connected_device_count()
            self._apply_preset_channels(prev_count, new_count)
            self._update_available_channels()
            return

        w["status"].setText("● Connecting")
        w["status"].setStyleSheet("color: #ff9800; font-weight: bold; background: transparent; border: none;")
        w["connect_btn"].setEnabled(False)
        self.append_log(f"[SYSTEM] Connecting N6705C-{label}...")

        if self._instrument_manager:
            from core.instruments import InstrumentSpec
            visa = w["combo"].currentText()
            self._instrument_manager.connect_async(InstrumentSpec(
                instrument_type="n6705c",
                role="power_analyzer",
                connection_kind="visa",
                slot=label,
                resource=visa,
            ))
            return

        try:
            from instruments.power.keysight.n6705c import N6705C
            visa = w["combo"].currentText()
            inst = N6705C(visa)
            idn = inst.instr.query("*IDN?")
            if "N6705C" in idn:
                setattr(self, f"n6705c_{attr}", inst)
                setattr(self, f"is_connected_{attr}", True)
                _update_n6705c_btn_state(w["connect_btn"], connected=True)
                w["search_btn"].setEnabled(False)
                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
                self.append_log(f"[SYSTEM] N6705C-{label} connected. IDN: {idn.strip()}")
                self._syncing = True
                try:
                    if self._n6705c_top:
                        serial = ""
                        try:
                            serial = idn.strip().split(",")[2].strip()
                        except Exception:
                            pass
                        getattr(self._n6705c_top, f"connect_{attr}")(visa, inst, serial)
                finally:
                    self._syncing = False
                new_count = self._connected_device_count()
                self._apply_preset_channels(prev_count, new_count)
                self._update_available_channels()
            else:
                w["status"].setText("● Mismatch")
                w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
                self.append_log(f"[ERROR] Connected device on {label} is not N6705C.")
        except Exception as e:
            w["status"].setText("● Failed")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[ERROR] Connection failed for N6705C-{label}: {e}")
        finally:
            w["connect_btn"].setEnabled(True)

    def _disconnect_device(self, label):
        attr = label.lower()
        w = self._n6705c_conn_widgets[label]
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()

        try:
            self._syncing = True
            try:
                if self._n6705c_top:
                    getattr(self._n6705c_top, f"disconnect_{attr}")()
                else:
                    inst = getattr(self, f"n6705c_{attr}", None)
                    if inst:
                        if hasattr(inst, 'disconnect'):
                            inst.disconnect()
                        else:
                            if hasattr(inst, 'instr') and inst.instr:
                                inst.instr.close()
                            if hasattr(inst, 'rm') and inst.rm:
                                inst.rm.close()
            finally:
                self._syncing = False
            setattr(self, f"n6705c_{attr}", None)
            setattr(self, f"is_connected_{attr}", False)
            _update_n6705c_btn_state(w["connect_btn"], connected=False)
            w["search_btn"].setEnabled(True)
            w["combo"].setEnabled(True)
            w["status"].setText("● Disconnected")
            w["status"].setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[SYSTEM] N6705C-{label} disconnected.")
            new_count = self._connected_device_count()
            self._apply_preset_channels(prev_count, new_count)
            self._update_available_channels()
        except Exception as e:
            w["status"].setText("● Failed")
            w["status"].setStyleSheet("color: #e53935; font-weight: bold; background: transparent; border: none;")
            self.append_log(f"[ERROR] Disconnect failed for N6705C-{label}: {e}")

    def _sync_n6705c_dual_from_top(self):
        top = self._n6705c_top
        if not top:
            self._update_test_panel_state()
            return
        from ui.modules.n6705c_module_frame import _update_n6705c_btn_state
        prev_count = self._connected_device_count()
        for label, attr in [("A", "a"), ("B", "b")]:
            n6705c = getattr(top, f"n6705c_{attr}", None)
            is_conn = getattr(top, f"is_connected_{attr}", False)
            visa_res = getattr(top, f"visa_resource_{attr}", "")
            if label not in self._n6705c_conn_widgets:
                continue
            w = self._n6705c_conn_widgets[label]
            if is_conn and n6705c:
                setattr(self, f"n6705c_{attr}", n6705c)
                setattr(self, f"is_connected_{attr}", True)
                _update_n6705c_btn_state(w["connect_btn"], connected=True)
                w["search_btn"].setEnabled(False)
                if visa_res:
                    w["combo"].clear()
                    w["combo"].addItem(visa_res)
                w["status"].setText("● Connected")
                w["status"].setStyleSheet("color: #00a859; font-weight: bold; background: transparent; border: none;")
            else:
                setattr(self, f"n6705c_{attr}", None)
                setattr(self, f"is_connected_{attr}", False)
                _update_n6705c_btn_state(w["connect_btn"], connected=False)
                w["search_btn"].setEnabled(True)
                w["combo"].setEnabled(True)
                w["status"].setText("● Disconnected")
                w["status"].setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
        self.n6705c = self.n6705c_a
        self.is_connected = self.is_connected_a
        new_count = self._connected_device_count()
        self._apply_preset_channels(prev_count, new_count)
        self._update_available_channels()

    def sync_n6705c_from_top(self):
        if self._syncing:
            return
        self._sync_n6705c_dual_from_top()

    def set_system_status(self, status, is_error=False):
        pass

    def _get_available_channel_options(self):
        options = []
        for label in ["A", "B"]:
            for ch in range(1, 5):
                options.append(f"{label}-CH{ch}")
        return options

    def _connected_device_count(self):
        count = 0
        if self.is_connected_a:
            count += 1
        if self.is_connected_b:
            count += 1
        return count

    def _update_available_channels(self):
        options = self._get_available_channel_options()
        pending_ch = self._pending_channel_selections or {}
        for i, wdata in enumerate(self._channel_config_widgets):
            combo = wdata["channel_combo"]
            # 目标值:优先使用待恢复的导入值,否则使用 _channel_configs 里记录的通道
            desired = None
            if i in pending_ch:
                desired = pending_ch[i]
            elif i < len(self._channel_configs):
                desired = self._channel_configs[i].get("channel", "")
            if not desired:
                desired = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            for opt in options:
                combo.addItem(opt)
            matched = False
            for j in range(combo.count()):
                if combo.itemText(j) == desired:
                    combo.setCurrentIndex(j)
                    matched = True
                    break
            combo.blockSignals(False)
            # 若期望值在选项里找到了,同步回 _channel_configs,并清理 pending
            if matched and i < len(self._channel_configs):
                self._channel_configs[i]["channel"] = desired
            if i in pending_ch and matched:
                pending_ch.pop(i, None)
        if self._pending_channel_selections is not None and not pending_ch:
            self._pending_channel_selections = None

        pending_aux = self._pending_aux_selections or {}
        aux_options = self._get_control_channel_options()
        for key, extra_combo in (("poweron", self.poweron_channel_combo),
                                 ("reset", self.reset_channel_combo)):
            if extra_combo is None:
                continue
            desired = pending_aux.get(key) if pending_aux else None
            if not desired:
                desired = extra_combo.currentText()
            extra_combo.blockSignals(True)
            extra_combo.clear()
            for opt in aux_options:
                extra_combo.addItem(opt)
            matched = False
            for j in range(extra_combo.count()):
                if extra_combo.itemText(j) == desired:
                    extra_combo.setCurrentIndex(j)
                    matched = True
                    break
            extra_combo.blockSignals(False)
            if matched and pending_aux:
                pending_aux.pop(key, None)
        if self._pending_aux_selections is not None and not pending_aux:
            self._pending_aux_selections = None

        self._refresh_result_cards()
        self._update_test_panel_state()

    def _apply_preset_channels(self, prev_count, new_count):
        if prev_count == new_count:
            return
        # 导入配置流程中不允许 preset 覆盖导入后的通道配置
        if getattr(self, "_suppress_preset_channels", False):
            return

        if new_count == 0:
            self._clear_all_channel_configs()
        elif new_count == 1:
            self._clear_all_channel_configs()
            for cfg in self.SINGLE_DEVICE_CHANNEL_CONFIGS:
                self._add_channel_config_card(cfg["name"], cfg["channel"], cfg["enabled"])
        elif new_count >= 2 and prev_count < 2:
            self._clear_all_channel_configs()
            for cfg in self.DUAL_DEVICE_CHANNEL_CONFIGS:
                self._add_channel_config_card(cfg["name"], cfg["channel"], cfg["enabled"])

    def _clear_all_channel_configs(self):
        for wdata in reversed(self._channel_config_widgets):
            wdata["card"].hide()
            wdata["card"].deleteLater()
        self._channel_configs.clear()
        self._channel_config_widgets.clear()
        while self.result_cards_layout.count():
            item = self.result_cards_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.deleteLater()
        self.channel_cards = {}

    def _update_test_panel_state(self):
        has_device = self._connected_device_count() > 0
        if hasattr(self, '_disabled_overlay'):
            if has_device:
                self._disabled_overlay.hide()
            else:
                self._disabled_overlay.show()
                self._disabled_overlay.raise_()

    def _get_checkmark_path(self, accent_color):
        safe_name = accent_color.replace("#", "").replace(" ", "")
        icons_dir = os.path.join(
            get_resource_base(),
            "resources", "icons"
        )
        return {
            "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
            "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
        }

    def _browse_firmware(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Firmware File(s)", "",
            "Firmware Files (*.bin *.hex);;All Files (*)"
        )
        if file_paths:
            self.firmware_paths = file_paths
            self.firmware_path = file_paths[0]
            names = [os.path.basename(p) for p in file_paths]
            self.firmware_file_input.setText("; ".join(names))
            for fp in file_paths:
                self.append_log(f"[SYSTEM] Firmware file selected: {os.path.basename(fp)}")

    def _download_to_dut(self):
        if not self.firmware_path:
            logger.warning("No firmware file selected")
            self.append_log("[WARNING] No firmware file selected.")
            return

        if self._controller.is_download_running():
            logger.warning("Download already in progress")
            self.append_log("[WARNING] Download already in progress.")
            return

        port_text = self.get_selected_serial_port()
        if not port_text:
            logger.warning("No serial port selected")
            self.append_log("[WARNING] No serial port selected.")
            return

        m = re.search(r'(\d+)', port_text)
        com_port = m.group(1) if m else port_text

        mode_str = self.download_mode_toggle.value().lower()
        mode = DownloadMode.FLASH if mode_str == "flash" else DownloadMode.RAMRUN

        self._controller.start_download(com_port, self.firmware_path, mode)

    def _on_ctrl_download_started(self, file_size):
        self.download_btn.setFileSize(file_size)
        self.download_btn.setStateWaiting()

    def _on_ctrl_download_state_changed(self, state_value):
        if state_value in (DownloadState.WAITING_SYNC.value, DownloadState.SYNCING.value):
            if self.download_btn.state() != ProgressButton.STATE_WAITING:
                self.download_btn.setStateWaiting()
        elif state_value == DownloadState.PROGRAMMING.value:
            self.download_btn.setStateProgramming()

    def _on_ctrl_download_finished(self, result):
        if result.success:
            self.download_btn.setStateComplete()
        else:
            self.download_btn.setStateFailed()

    def _on_ctrl_download_error(self, err_msg):
        self.download_btn.setStateFailed()

    def _on_ctrl_download_cleaned(self):
        pass

    def _stop_download(self):
        self._controller.stop_download()
        self.download_btn.setStateFailed()
        self.append_log("[DOWNLOAD] Download stopped by user.")
        logger.info("Download stopped by user")

    def _on_chip_selected(self, index):
        if index <= 0:
            self.selected_chip_config = None
            self._refresh_saved_config_combo(None)
            return
        chip_name = self.chip_combo.currentText()
        cfg = get_chip_config(chip_name)
        self.selected_chip_config = cfg
        if cfg:
            logger.info("Chip selected: %s", chip_name)
            self.append_log(f"[SYSTEM] Chip selected: {chip_name}")
        else:
            logger.warning("No config found for chip: %s", chip_name)
            self.append_log(f"[WARNING] No config found for chip: {chip_name}")
        self._refresh_saved_config_combo(chip_name)

    def _refresh_saved_config_combo(self, chip_name):
        """根据所选芯片,扫描 main_chip_configs/<chip>.yaml 并刷新 Config 下拉。"""
        combo = getattr(self, "saved_config_combo", None)
        if combo is None:
            return

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("-- Select Config --")
        self._saved_config_current_chip = chip_name
        self._saved_config_yaml_text = ""
        self._saved_config_entries = []

        if not chip_name:
            combo.setEnabled(False)
            combo.blockSignals(False)
            return

        yaml_path = os.path.join(_MAIN_CHIP_CONFIGS_DIR, f"{chip_name}.yaml")
        if not os.path.isfile(yaml_path):
            combo.addItem("(No saved config)")
            combo.setEnabled(False)
            combo.blockSignals(False)
            return

        if yaml is None:
            combo.addItem("(PyYAML not installed)")
            combo.setEnabled(False)
            combo.blockSignals(False)
            self.append_log("[WARNING] PyYAML not installed; cannot parse saved configs.")
            return

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                yaml_text = f.read()
            parsed = yaml.safe_load(yaml_text) or {}
        except Exception as e:
            combo.addItem("(Parse error)")
            combo.setEnabled(False)
            combo.blockSignals(False)
            logger.warning("Failed to parse saved configs %s: %s", yaml_path, e)
            self.append_log(f"[WARNING] Failed to parse saved configs for {chip_name}: {e}")
            return

        self._saved_config_yaml_text = yaml_text
        if isinstance(parsed, dict) and parsed:
            for key in parsed.keys():
                key_str = str(key)
                self._saved_config_entries.append(key_str)
                combo.addItem(key_str)
            combo.setEnabled(True)
        else:
            combo.addItem("(Empty)")
            combo.setEnabled(False)

        combo.blockSignals(False)

    def _on_saved_config_selected(self, index):
        """选中 Config 下拉项后,将整个 YAML 文件内容填入 Config Content 编辑框。"""
        if index <= 0:
            return
        if not self._saved_config_entries:
            return
        entry_index = index - 1
        if entry_index >= len(self._saved_config_entries):
            return
        if not hasattr(self, "config_text_edit") or self.config_text_edit is None:
            return

        chip_name = self._saved_config_current_chip or ""
        entry_name = self._saved_config_entries[entry_index]

        self.config_text_edit.setPlainText(self._saved_config_yaml_text)
        self.append_log(
            f"[SYSTEM] Loaded saved config '{entry_name}' for {chip_name} into Config Content."
        )

    def _on_chip_check(self):
        if self._chip_check_thread is not None and self._chip_check_thread.isRunning():
            self.append_log("[WARNING] Chip check already in progress.")
            return

        self.chip_check_btn.setEnabled(False)
        self.append_log("[SYSTEM] Starting chip check via I2C...")

        worker = _ChipCheckWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_chip_check_finished)
        worker.error.connect(self._on_chip_check_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(self._on_chip_check_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._chip_check_thread = thread
        self._chip_check_worker = worker
        thread.start()

    def _on_chip_check_finished(self, chip_info):
        self.chip_check_btn.setEnabled(True)

        self.append_log(
            f"[CHIP_CHECK] chip={chip_info.get('chip_name') or 'N/A'}"
            f"  main_die={chip_info.get('main_die') or 'N/A'}({chip_info.get('main_die_version') or '?'}, addr={chip_info.get('main_die_i2c_addr') or 'N/A'}, {chip_info.get('main_die_i2c_width') or 'N/A'}bit)"
            f"  main_die_pmu={chip_info.get('main_die_pmu') or 'N/A'}(addr={chip_info.get('main_die_pmu_i2c_addr') or 'N/A'}, {chip_info.get('main_die_pmu_i2c_width') or 'N/A'}bit)"
            f"  has_pmu={chip_info.get('has_pmu', False)}"
            f"  pmu={chip_info.get('pmu') or 'N/A'}({chip_info.get('pmu_version') or '?'}, addr={chip_info.get('pmu_i2c_addr') or 'N/A'}, {chip_info.get('pmu_i2c_width') or 'N/A'}bit)"
        )

        warning = chip_info.get("warning")
        if warning:
            self.append_log(f"[CHIP_CHECK] ⚠ {warning}")

        detected_name = chip_info.get("chip_name")
        if not detected_name:
            self.append_log("[WARNING] Chip check: no chip detected.")
            return

        exact_idx = self.chip_combo.findText(detected_name, Qt.MatchExactly)
        if exact_idx >= 0:
            self.chip_combo.setCurrentIndex(exact_idx)
            self.append_log(f"[CHIP_CHECK] Chip matched: {detected_name}")
            return

        prefix_match = detected_name.split("_")[0] if "_" in detected_name else detected_name
        for i in range(1, self.chip_combo.count()):
            item = self.chip_combo.itemText(i)
            if item == prefix_match or item.startswith(detected_name):
                self.chip_combo.setCurrentIndex(i)
                self.append_log(f"[CHIP_CHECK] Chip matched (prefix): {item}")
                return

        self.append_log(f"[WARNING] No matching chip found in list for: {detected_name}")

    def _on_chip_check_error(self, err_msg):
        self.chip_check_btn.setEnabled(True)
        logger.error("Chip check error: %s", err_msg)
        self.append_log(f"[ERROR] Chip check failed: {err_msg}")

    def _on_chip_check_thread_cleaned(self):
        self._chip_check_worker = None
        self._chip_check_thread = None

    def _import_configuration(self):
        config_text = self.config_text_edit.toPlainText().strip()
        if not config_text:
            logger.warning("No configuration content provided")
            self.append_log("[WARNING] No configuration content provided.")
            return
        self.config_content = config_text
        logger.info("Configuration imported from text input (%d chars)", len(config_text))
        self.append_log(f"[SYSTEM] Configuration imported from text input ({len(config_text)} chars)")

    def _execute_configuration(self):
        chip_name = self.chip_combo.currentText()
        if self.chip_combo.currentIndex() <= 0 or self.selected_chip_config is None:
            logger.warning("No chip selected for configuration execution")
            self.append_log("[WARNING] No chip selected. Please select a chip first.")
            return

        refreshed = get_chip_config(chip_name, force_reload=True)
        if refreshed:
            self.selected_chip_config = refreshed

        self.append_log(f"[EXECUTE] Starting configuration for chip: {chip_name}")

        try:
            from lib.i2c.i2c_interface_x64 import I2CInterface
            i2c = I2CInterface()
            if not i2c.initialize():
                self.append_log("[ERROR] I2C interface initialization failed.")
                return
            self.append_log("[EXECUTE] I2C interface initialized successfully.")
        except Exception as e:
            logger.error("I2C initialization error: %s", e)
            self.append_log(f"[ERROR] I2C initialization error: {e}")
            return

        try:
            chip_info = i2c.bes_chip_check()
            self.append_log(f"[EXECUTE] Chip detected: {chip_info.get('chip_name', 'N/A')}")
        except Exception as e:
            logger.error("bes_chip_check failed: %s", e)
            self.append_log(f"[ERROR] Chip check failed: {e}")
            return

        self._compare_chip_info(chip_info, self.selected_chip_config)

        config_text = self.config_text_edit.toPlainText().strip()
        config_commands = None
        config_source = None

        if config_text:
            config_commands = self._parse_config_commands(config_text)
            config_source = "user_paste"
            self.append_log(f"[EXECUTE] Using pasted configuration ({len(config_commands)} commands)")
        else:
            pd = self.selected_chip_config.get("power_distribution")
            if pd and isinstance(pd, dict) and len(pd) > 0:
                raw_lines = []
                for section, cmds in pd.items():
                    if isinstance(cmds, list):
                        raw_lines.extend(cmds)
                config_commands = self._parse_config_commands("\n".join(raw_lines))
                config_source = "chip_config"
                self.append_log(f"[EXECUTE] Using chip config power_distribution ({len(config_commands)} commands)")
            else:
                logger.warning("No configuration available: neither pasted text nor chip power_distribution found")
                self.append_log("[WARNING] No configuration available. Please paste configuration or ensure chip config has power_distribution.")
                return

        if config_source == "user_paste":
            reply = QMessageBox.question(
                self,
                "Import Configuration",
                f"Do you want to save the pasted configuration to chip config '{chip_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._update_chip_config_file(chip_name, config_text)

        self._run_config_commands(i2c, chip_info, config_commands)
        self.append_log("[EXECUTE] Configuration execution completed.")

    def _compare_chip_info(self, detected, config):
        compare_keys = [
            "chip_name", "main_die", "main_die_version",
            "main_die_i2c_width", "main_die_i2c_addr",
            "main_die_pmu", "main_die_pmu_version",
            "main_die_pmu_i2c_width", "main_die_pmu_i2c_addr",
            "has_pmu", "pmu", "pmu_version", "pmu_i2c_width", "pmu_i2c_addr",
        ]
        for key in compare_keys:
            det_val = detected.get(key)
            cfg_val = config.get(key)
            if cfg_val in (None, "", {}):
                continue
            if self._chip_values_equal(det_val, cfg_val):
                continue
            logger.warning(
                "Chip info mismatch [%s]: detected=%s, config=%s",
                key, det_val, cfg_val
            )
            self.append_log(
                f"[WARNING] Chip info mismatch [{key}]: detected={det_val}, config={cfg_val}"
            )

    @staticmethod
    def _chip_values_equal(a, b):
        if a == b:
            return True
        if a is None or b is None:
            return False
        str_a = str(a).strip().lower()
        str_b = str(b).strip().lower()
        if str_a == str_b:
            return True
        try:
            return int(str_a, 0) == int(str_b, 0)
        except (ValueError, TypeError):
            pass
        if isinstance(a, bool) or isinstance(b, bool):
            truthy = {"true", "1", "yes"}
            falsy = {"false", "0", "no", ""}
            a_bool = str_a in truthy
            b_bool = str_b in truthy
            a_is_bool = str_a in truthy or str_a in falsy
            b_is_bool = str_b in truthy or str_b in falsy
            if a_is_bool and b_is_bool:
                return a_bool == b_bool
        return False

    @staticmethod
    def _parse_config_commands(text):
        commands = []
        lines = text.strip().splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if line.startswith("-"):
                line = line[1:].strip()
            if line.startswith("'") or line.startswith('"'):
                line = line[1:]
            if line.endswith("'") or line.endswith('"'):
                line = line[:-1]
            line = line.strip()

            comment_idx = line.find("//")
            if comment_idx >= 0:
                line = line[:comment_idx].strip()

            if not line:
                continue

            upper = line.upper()
            if not any(kw in upper for kw in ("WRITE_BITS", "WRITE", "READ")):
                continue

            target = "NO_PREFIX"
            if ":" in line:
                prefix, rest = line.split(":", 1)
                prefix_upper = prefix.strip().upper()
                rest_upper = rest.strip().upper()
                has_command = any(kw in rest_upper for kw in ("WRITE_BITS", "WRITE", "READ"))
                if has_command:
                    if prefix_upper == "DUT":
                        target = "DUT"
                        line = rest.strip()
                    elif prefix_upper == "PMU":
                        target = "MAIN_DIE_PMU"
                        line = rest.strip()
                    elif prefix_upper == "MAIN_DIE_PMU":
                        target = "MAIN_DIE_PMU"
                        line = rest.strip()
                    elif prefix_upper.endswith("_PMU"):
                        target = "EXT_PMU"
                        line = rest.strip()
                    elif prefix_upper.endswith("_DUT") or prefix_upper.endswith("_MAIN"):
                        target = "DUT"
                        line = rest.strip()

            parts = line.split()
            if len(parts) < 2:
                continue

            op = parts[0].upper()
            if op == "WRITE_BITS" and len(parts) >= 5:
                reg_addr = int(parts[1], 0)
                msb = int(parts[2], 0)
                lsb = int(parts[3], 0)
                value = int(parts[4], 0)
                commands.append({
                    "op": "WRITE_BITS",
                    "target": target,
                    "reg_addr": reg_addr,
                    "msb": msb,
                    "lsb": lsb,
                    "value": value,
                })
            elif op == "WRITE" and len(parts) >= 3:
                reg_addr = int(parts[1], 0)
                value = int(parts[2], 0)
                commands.append({
                    "op": "WRITE",
                    "target": target,
                    "reg_addr": reg_addr,
                    "value": value,
                })
            elif op == "READ" and len(parts) >= 2:
                reg_addr = int(parts[1], 0)
                commands.append({
                    "op": "READ",
                    "target": target,
                    "reg_addr": reg_addr,
                })

        return commands

    @staticmethod
    def _to_int_addr(addr):
        if addr is None:
            return None
        if isinstance(addr, int):
            return addr
        if isinstance(addr, str):
            return int(addr, 0)
        return None

    def _resolve_device(self, chip_info, target):
        if target == "DUT":
            addr = self._to_int_addr(chip_info.get("main_die_i2c_addr"))
            width = chip_info.get("main_die_i2c_width")
            return addr, width
        if target == "EXT_PMU":
            addr = self._to_int_addr(chip_info.get("pmu_i2c_addr"))
            width = chip_info.get("pmu_i2c_width")
            return addr, width
        if target == "MAIN_DIE_PMU":
            addr = self._to_int_addr(chip_info.get("main_die_pmu_i2c_addr"))
            width = chip_info.get("main_die_pmu_i2c_width")
            return addr, width
        if chip_info.get("has_pmu") and chip_info.get("pmu_i2c_addr"):
            addr = self._to_int_addr(chip_info.get("pmu_i2c_addr"))
            width = chip_info.get("pmu_i2c_width")
        else:
            addr = self._to_int_addr(chip_info.get("main_die_pmu_i2c_addr"))
            width = chip_info.get("main_die_pmu_i2c_width")
        return addr, width

    def _run_config_commands(self, i2c, chip_info, commands):
        for idx, cmd in enumerate(commands):
            op = cmd["op"]
            target = cmd.get("target", "NO_PREFIX")
            reg_addr = cmd["reg_addr"]

            device_addr, width = self._resolve_device(chip_info, target)
            if device_addr is None or width is None:
                self.append_log(
                    f"[ERROR] Cannot resolve device address for target={target}, skipping command #{idx+1}"
                )
                continue

            try:
                if op == "WRITE_BITS":
                    msb = cmd["msb"]
                    lsb = cmd["lsb"]
                    value = cmd["value"]
                    current_val = i2c.read(device_addr, reg_addr, width)
                    bit_mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                    new_val = (current_val & ~bit_mask) | ((value << lsb) & bit_mask)
                    i2c.write(device_addr, reg_addr, new_val, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} WRITE_BITS dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} [{msb}:{lsb}]=0x{value:X} "
                        f"(0x{current_val:X} -> 0x{new_val:X})"
                    )

                elif op == "WRITE":
                    value = cmd["value"]
                    i2c.write(device_addr, reg_addr, value, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} WRITE dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} data=0x{value:X}"
                    )

                elif op == "READ":
                    read_val = i2c.read(device_addr, reg_addr, width)
                    self.append_log(
                        f"[EXECUTE] #{idx+1} READ dev=0x{device_addr:02X} "
                        f"reg=0x{reg_addr:08X} => 0x{read_val:X}"
                    )

            except Exception as e:
                logger.error("Command #%d failed: %s", idx + 1, e)
                self.append_log(f"[ERROR] Command #{idx+1} failed: {e}")

    def _update_chip_config_file(self, chip_name, config_text):
        try:
            config_lines = []
            for raw_line in config_text.strip().splitlines():
                line = raw_line.strip()
                if line:
                    config_lines.append(line)

            chips_dir = os.path.join(
                get_resource_base(),
                "chips", "bes_chip_configs"
            )
            if chip_name.startswith("pmu_"):
                config_file = os.path.join(chips_dir, "pmu_chips", f"{chip_name}.py")
            else:
                config_file = os.path.join(chips_dir, "main_chips", f"{chip_name}.py")

            if not os.path.exists(config_file):
                logger.warning("Chip config file not found: %s", config_file)
                self.append_log(f"[WARNING] Chip config file not found: {config_file}")
                return

            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()

            import ast
            tree = ast.parse(content)
            chip_config_dict = None
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == "CHIP_CONFIG":
                            chip_config_dict = ast.literal_eval(content[node.value.col_offset:].split("\n}")[0] + "\n}")
                            break

            if chip_config_dict is None:
                chip_config_dict = {}

            chip_config_dict["power_distribution"] = {"user_config": config_lines}

            lines = ["CHIP_CONFIG = {\n"]
            for key, val in chip_config_dict.items():
                lines.append(f"    {key!r}: {val!r},\n")
            lines.append("}\n")

            with open(config_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            logger.info("Chip config updated: %s", config_file)
            self.append_log(f"[SYSTEM] Chip config updated: {chip_name}")

            refreshed = get_chip_config(chip_name, force_reload=True)
            if refreshed:
                self.selected_chip_config = refreshed
        except Exception as e:
            logger.error("Failed to update chip config: %s", e)
            self.append_log(f"[ERROR] Failed to update chip config: {e}")

    def _parse_channel_key(self, channel_key):
        m = re.match(r'^([AB])-CH(\d+)$', channel_key)
        if m:
            return m.group(1), int(m.group(2))
        m = re.match(r'^GPIO(\d+)$', channel_key, re.IGNORECASE)
        if m:
            return "MCU", int(m.group(1))
        return None, None

    def _build_channel_force_configs(self):
        """构建每通道的 force 配置字典。

        返回:
            {(device_label, hw_ch): {
                "force_mode": "force"/"auto",
                "force_value": float,        # force 模式下的目标电压(V)
                "boost_mode": "constant"/"percent",
                "boost_value": float,        # auto 模式下的增压值
            }}
            Force 模式且 force_value 为空/非法时跳过该通道(走 Auto 默认值)。
            Auto 模式下 boost_value 为空/非法时使用默认 0.02。
        """
        configs = {}
        for cfg in self._channel_configs:
            if not cfg["enabled"]:
                continue
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                continue

            force_mode = cfg.get("force_mode", "auto")
            entry = {
                "force_mode": force_mode,
                "force_value": None,
                "boost_mode": cfg.get("boost_mode", "constant"),
                "boost_value": 0.02,
            }

            if force_mode == "force":
                val_text = cfg.get("force_value", "").strip()
                if not val_text:
                    continue
                try:
                    entry["force_value"] = float(val_text)
                except ValueError:
                    continue
            else:
                val_text = cfg.get("boost_value", "").strip()
                if val_text:
                    try:
                        entry["boost_value"] = float(val_text)
                    except ValueError:
                        pass

            configs[(device_label, hw_ch)] = entry
        return configs

    def _current_mcu_type(self):
        if hasattr(self, "mcu_type_combo") and self.mcu_type_combo is not None:
            data = self.mcu_type_combo.currentData()
            if data in ("yd_rp2040", "ch9114f"):
                return data
        return getattr(self, "_default_mcu_type", "ch9114f")

    def _get_mcu_gpio_options(self):
        if self._current_mcu_type() == "ch9114f":
            return [f"GPIO{i}" for i in (0, 1, 6, 7, 2, 8, 14, 20)]
        return [f"GPIO{i}" for i in range(0, 30)]

    def _get_control_channel_options(self, method=None):
        method = method or (
            self.control_method_toggle.value()
            if getattr(self, "control_method_toggle", None) else "N6705C"
        )
        if method == "MCU":
            return self._get_mcu_gpio_options()
        return self._get_available_channel_options()

    @staticmethod
    def _set_combo_options(combo, options, desired=None):
        if combo is None:
            return False
        if desired is None:
            desired = combo.currentText()
        combo.blockSignals(True)
        combo.clear()
        for opt in options:
            combo.addItem(opt)
        matched = False
        if desired:
            for i in range(combo.count()):
                if combo.itemText(i) == desired:
                    combo.setCurrentIndex(i)
                    matched = True
                    break
        if not matched and combo.count() > 0:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)
        return matched

    def _selected_mcu_port(self):
        text = self.mcu_port_combo.currentText() if getattr(self, "mcu_port_combo", None) else ""
        if not text or text in (
            "No serial ports found",
            "No CH9114F ports found",
            "Select MCU COM...",
            "Select CH9114F COM...",
        ):
            return None
        return text.split()[0]

    def _on_mcu_search(self):
        from debug_config import DEBUG_MOCK
        mcu_type = self._current_mcu_type()
        if DEBUG_MOCK:
            self.mcu_port_combo.clear()
            if mcu_type == "ch9114f":
                self.mcu_port_combo.addItem("[MOCK] COM99 - Mock CH9114F")
            else:
                self.mcu_port_combo.addItem("[MOCK] COM98 - Mock YD RP2040")
            self.mcu_status_label.setText("● Mock Ready")
            self.mcu_status_label.setStyleSheet(
                "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_connect_btn.setEnabled(True)
            self.append_log(f"[DEBUG] Mock {mcu_type} port loaded.")
            return

        if self._mcu_search_thread is not None and self._mcu_search_thread.isRunning():
            return
        self.mcu_status_label.setText("● Searching")
        self.mcu_status_label.setStyleSheet(
            "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(False)
        self.mcu_connect_btn.setEnabled(False)
        if mcu_type == "ch9114f":
            self.append_log("[MCU] Scanning for CH9114F ports...")
        else:
            self.append_log("[MCU] Scanning serial ports for YD RP2040...")

        worker = _SearchMcuPortWorker(mcu_type)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_search_done)
        worker.error.connect(self._on_mcu_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_mcu_search_thread_cleanup())
        self._mcu_search_worker = worker
        self._mcu_search_thread = thread
        thread.start()

    def _on_mcu_search_done(self, ports):
        mcu_type = self._current_mcu_type()
        self.mcu_port_combo.clear()
        self.mcu_port_combo.setEnabled(True)
        if ports:
            for port in ports:
                self.mcu_port_combo.addItem(port)
            self.mcu_status_label.setText(f"● Found {len(ports)}")
            self.mcu_status_label.setStyleSheet(
                "color: #00a859; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            label = "CH9114F port(s)" if mcu_type == "ch9114f" else "serial port(s)"
            self.append_log(f"[MCU] Found {len(ports)} {label}.")
        else:
            if mcu_type == "ch9114f":
                self.mcu_port_combo.addItem("No CH9114F ports found")
            else:
                self.mcu_port_combo.addItem("No serial ports found")
            self.mcu_port_combo.setEnabled(False)
            self.mcu_status_label.setText("● Not Found")
            self.mcu_status_label.setStyleSheet(
                "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(bool(ports))

    def _on_mcu_search_error(self, err):
        self.mcu_status_label.setText("● Search Failed")
        self.mcu_status_label.setStyleSheet(
            "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.append_log(f"[MCU] Search failed: {err}")
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(True)

    def _on_mcu_search_thread_cleanup(self):
        self._mcu_search_thread = None
        self._mcu_search_worker = None

    def _on_mcu_connect_or_disconnect(self):
        if self.is_mcu_connected:
            self._disconnect_mcu()
        else:
            self._connect_mcu()

    def _connect_mcu(self):
        port = self._selected_mcu_port()
        if not port:
            self.append_log("[MCU] No valid MCU port selected.")
            return
        mcu_type = self._current_mcu_type()
        if self._mcu_connect_thread is not None and self._mcu_connect_thread.isRunning():
            return
        self.mcu_status_label.setText("● Connecting")
        self.mcu_status_label.setStyleSheet(
            "color: #ff9800; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(False)
        self.mcu_connect_btn.setEnabled(False)
        type_label = "CH9114F" if mcu_type == "ch9114f" else "YD RP2040"
        self.append_log(f"[MCU] Connecting {type_label} on {port}...")

        worker = _ConnectMcuWorker(port, mcu_type=mcu_type)
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_mcu_connected)
        worker.error.connect(self._on_mcu_connect_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_mcu_connect_thread_cleanup())
        self._mcu_connect_worker = worker
        self._mcu_connect_thread = thread
        thread.start()

    def _on_mcu_connected(self, inst, idn):
        self.mcu_io = inst
        self.is_mcu_connected = True
        self.mcu_status_label.setText("● Connected")
        self.mcu_status_label.setStyleSheet(
            "color: #00a859; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(False)
        self.mcu_connect_btn.setEnabled(True)
        self.mcu_connect_btn.setText("Disconnect")
        self.append_log(f"[MCU] Connected: {idn}")
        self._suppress_preset_channels = False

    def _on_mcu_connect_error(self, err):
        self.mcu_status_label.setText("● Failed")
        self.mcu_status_label.setStyleSheet(
            "color: #e53935; font-size: 10px; font-weight: bold; background: transparent; border: none;"
        )
        self.mcu_search_btn.setEnabled(True)
        self.mcu_connect_btn.setEnabled(True)
        self.append_log(f"[MCU] Connection failed: {err}")
        self._suppress_preset_channels = False

    def _on_mcu_connect_thread_cleanup(self):
        self._mcu_connect_thread = None
        self._mcu_connect_worker = None

    def _disconnect_mcu(self):
        try:
            if self.mcu_io is not None:
                self.mcu_io.disconnect()
        except Exception as e:
            logger.error("MCU disconnect failed: %s", e, exc_info=True)
            self.append_log(f"[MCU] Disconnect failed: {e}")
        finally:
            self.mcu_io = None
            self.is_mcu_connected = False
            self.mcu_status_label.setText("● Disconnected")
            self.mcu_status_label.setStyleSheet(
                "color: #8ea6cf; font-size: 10px; font-weight: bold; background: transparent; border: none;"
            )
            self.mcu_search_btn.setEnabled(True)
            self.mcu_connect_btn.setEnabled(True)
            self.mcu_connect_btn.setText("Connect")
            self.append_log("[MCU] Disconnected.")

    # =====================================================================
    # 导入 / 导出 测试配置
    # =====================================================================
    CONFIG_SCHEMA_VERSION = 1

    def _collect_config_snapshot(self):
        """把当前 UI 上所有测试相关的参数序列化成一个可 JSON 化的 dict。"""
        # 仪器:N6705C-A / N6705C-B 的 VISA resource 与连接状态
        n6705c = {}
        for label in ("A", "B"):
            attr = label.lower()
            visa = ""
            if label in getattr(self, "_n6705c_conn_widgets", {}):
                visa = self._n6705c_conn_widgets[label]["combo"].currentText()
            n6705c[label] = {
                "visa": visa,
                "connected": bool(getattr(self, f"is_connected_{attr}", False)),
            }

        # 串口
        serial_port = ""
        if hasattr(self, "serial_combo") and self.serial_combo is not None:
            serial_port = self.serial_combo.currentText() or ""

        mcu_io = {
            "port": (
                self.mcu_port_combo.currentText()
                if getattr(self, "mcu_port_combo", None) is not None else ""
            ),
            "connected": bool(getattr(self, "is_mcu_connected", False)),
            "type": self._current_mcu_type(),
        }

        # 通道配置(_channel_configs 内容已能描述每个通道)
        channel_configs = [dict(cfg) for cfg in self._channel_configs]

        # 固件下载相关
        download = {
            "mode": self.download_mode_toggle.value() if hasattr(self, "download_mode_toggle") and self.download_mode_toggle else "FLASH",
            "firmware_path": getattr(self, "firmware_path", "") or "",
            "firmware_paths": list(getattr(self, "firmware_paths", []) or []),
        }

        # Chip 与额外 YAML config
        chip_selected = ""
        if hasattr(self, "chip_combo") and self.chip_combo is not None:
            chip_selected = self.chip_combo.currentText()
        config_text = ""
        if hasattr(self, "config_text_edit") and self.config_text_edit is not None:
            config_text = self.config_text_edit.toPlainText()

        # 测试参数
        try:
            test_time = float(self.test_time_input.text())
        except Exception:
            test_time = 10.0
        control_method = (
            self.control_method_toggle.value()
            if hasattr(self, "control_method_toggle") and self.control_method_toggle
            else "N6705C"
        )
        poweron_ch = (
            self.poweron_channel_combo.currentText()
            if getattr(self, "poweron_channel_combo", None) else ""
        )
        reset_ch = (
            self.reset_channel_combo.currentText()
            if getattr(self, "reset_channel_combo", None) else ""
        )
        poweron_pol = (
            self.poweron_polarity_toggle.value()
            if getattr(self, "poweron_polarity_toggle", None) else "rising"
        )
        reset_pol = (
            self.reset_polarity_toggle.value()
            if getattr(self, "reset_polarity_toggle", None) else "rising"
        )
        reset_enabled = (
            self.reset_enable_cb.isChecked()
            if getattr(self, "reset_enable_cb", None) else False
        )
        force_config_enabled = (
            self.force_config_cb.isChecked()
            if getattr(self, "force_config_cb", None) else False
        )

        return {
            "schema_version": self.CONFIG_SCHEMA_VERSION,
            "page": "consumption_test",
            "n6705c": n6705c,
            "serial_port": serial_port,
            "mcu_io": mcu_io,
            "channel_configs": channel_configs,
            "download": download,
            "chip_selected": chip_selected,
            "config_text": config_text,
            "force_config_enabled": force_config_enabled,
            "test": {
                "test_time": test_time,
                "control_method": control_method,
                "poweron_channel": poweron_ch,
                "poweron_polarity": poweron_pol,
                "reset_channel": reset_ch,
                "reset_polarity": reset_pol,
                "reset_enabled": reset_enabled,
            },
        }

    def _export_config(self):
        """把当前 UI 配置导出到 JSON 文件。"""
        try:
            default_dir = os.getcwd()
            default_name = os.path.join(default_dir, "consumption_test_config.json")
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Consumption Test Config",
                default_name, "JSON Files (*.json);;All Files (*)"
            )
            if not file_path:
                return
            snapshot = self._collect_config_snapshot()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2, ensure_ascii=False)
            self.append_log(f"[CONFIG] Exported to: {file_path}")
        except Exception as e:
            self.append_log(f"[ERROR] Export config failed: {e}")
            QMessageBox.critical(self, "Export Failed", f"Failed to export config:\n{e}")

    def _import_config(self):
        """从 JSON 文件加载配置,应用到 UI,并尝试自动连接仪器。"""
        if getattr(self, "is_testing", False):
            QMessageBox.warning(self, "Cannot Import",
                                "A test is running. Please stop it before importing config.")
            return
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Consumption Test Config",
                os.getcwd(), "JSON Files (*.json);;All Files (*)"
            )
            if not file_path:
                return
            with open(file_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except Exception as e:
            self.append_log(f"[ERROR] Import config failed: {e}")
            QMessageBox.critical(self, "Import Failed", f"Failed to read config:\n{e}")
            return

        if not isinstance(snapshot, dict):
            QMessageBox.critical(self, "Import Failed", "Config file format is invalid.")
            return
        if snapshot.get("page") and snapshot.get("page") != "consumption_test":
            ret = QMessageBox.question(
                self, "Page Mismatch",
                f"This config was exported from page '{snapshot.get('page')}'.\n"
                f"Apply it to Consumption Test anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        try:
            self._apply_imported_config(snapshot)
            self.append_log(f"[CONFIG] Imported from: {file_path}")
        except Exception as e:
            # 异常时确保 preset 屏蔽标志被恢复,避免卡在抑制状态
            self._suppress_preset_channels = False
            self.append_log(f"[ERROR] Apply imported config failed: {e}")
            QMessageBox.critical(self, "Import Failed", f"Failed to apply config:\n{e}")

    def _apply_imported_config(self, snapshot):
        """将 snapshot 中的设置应用到 UI。仪器连接使用 QTimer 异步触发。"""
        # 整个导入流程中屏蔽 preset 通道覆盖逻辑(仪器连接时会触发)
        self._suppress_preset_channels = True
        # ---- 1. N6705C 仪器的 VISA 地址 ----
        n6705c_cfg = snapshot.get("n6705c", {}) or {}
        pending_connects = []
        for label in ("A", "B"):
            item = n6705c_cfg.get(label, {}) or {}
            visa = item.get("visa", "") or ""
            want_connect = bool(item.get("connected"))
            widgets = getattr(self, "_n6705c_conn_widgets", {}).get(label)
            if widgets is None:
                continue
            combo = widgets["combo"]
            if visa:
                # 加入下拉选项(若不存在)并选中
                found_idx = -1
                for i in range(combo.count()):
                    if combo.itemText(i) == visa:
                        found_idx = i
                        break
                if found_idx < 0:
                    combo.addItem(visa)
                    found_idx = combo.count() - 1
                combo.setCurrentIndex(found_idx)
            # 记录是否需要自动连接
            if want_connect:
                pending_connects.append(label)

        # ---- 2. 串口 ----
        serial_port = snapshot.get("serial_port", "") or ""
        if serial_port and hasattr(self, "serial_combo") and self.serial_combo is not None:
            found_idx = -1
            for i in range(self.serial_combo.count()):
                if self.serial_combo.itemText(i) == serial_port:
                    found_idx = i
                    break
            if found_idx < 0:
                self.serial_combo.addItem(serial_port)
                found_idx = self.serial_combo.count() - 1
            self.serial_combo.setEnabled(True)
            self.serial_combo.setCurrentIndex(found_idx)

        # ---- 2.1 MCU IO ----
        mcu_cfg = snapshot.get("mcu_io", {}) or {}
        mcu_port = mcu_cfg.get("port", "") or ""
        pending_mcu_connect = bool(mcu_cfg.get("connected"))
        mcu_type = mcu_cfg.get("type", "yd_rp2040")
        if mcu_type in ("yd_rp2040", "ch9114f") and getattr(self, "mcu_type_combo", None) is not None:
            for i in range(self.mcu_type_combo.count()):
                if self.mcu_type_combo.itemData(i) == mcu_type:
                    self.mcu_type_combo.setCurrentIndex(i)
                    break
        # 切换 mcu_type 会重置 port_combo 的占位符,先确保占位符匹配当前类型
        if getattr(self, "mcu_port_combo", None) is not None:
            self.mcu_port_combo.clear()
            self.mcu_port_combo.addItem(
                "Select CH9114F COM..." if mcu_type == "ch9114f" else "Select MCU COM..."
            )
        if mcu_port and getattr(self, "mcu_port_combo", None) is not None:
            found_idx = -1
            for i in range(self.mcu_port_combo.count()):
                if self.mcu_port_combo.itemText(i) == mcu_port:
                    found_idx = i
                    break
            if found_idx < 0:
                self.mcu_port_combo.addItem(mcu_port)
                found_idx = self.mcu_port_combo.count() - 1
            self.mcu_port_combo.setEnabled(True)
            self.mcu_port_combo.setCurrentIndex(found_idx)

        # ---- 3. 通道配置(重建所有 channel 卡片) ----
        channel_configs = snapshot.get("channel_configs", []) or []
        if channel_configs:
            self._clear_all_channel_configs()
            # 预先把通道期望值记到 pending,供后续 _update_available_channels 使用
            self._pending_channel_selections = {}
            for i, cfg in enumerate(channel_configs):
                name = cfg.get("name", "")
                ch = cfg.get("channel", "")
                enabled = bool(cfg.get("enabled", False))
                self._add_channel_config_card(name, ch, enabled)
                idx = len(self._channel_configs) - 1
                # 强制把通道值写回(即使当前 combo 选项里没有该项)
                self._channel_configs[idx]["channel"] = ch
                if ch:
                    self._pending_channel_selections[idx] = ch
                fv_mode = cfg.get("force_mode", "auto")
                fv_val = cfg.get("force_value", "") or ""
                bm = cfg.get("boost_mode", "constant")
                bv = cfg.get("boost_value", "0.02") or "0.02"
                self._channel_configs[idx]["force_mode"] = fv_mode
                self._channel_configs[idx]["force_value"] = fv_val
                self._channel_configs[idx]["boost_mode"] = bm
                self._channel_configs[idx]["boost_value"] = bv
                wdata = self._channel_config_widgets[idx]
                wdata["force_mode_toggle"].setValue(fv_mode)
                wdata["force_value_input"].setText(fv_val)
                wdata["boost_mode_toggle"].setValue(bm)
                wdata["boost_value_input"].setText(bv)
                is_force = (fv_mode == "force")
                wdata["force_value_input"].setEnabled(enabled and is_force)
                wdata["boost_mode_label"].setEnabled(enabled and not is_force)
                wdata["boost_mode_toggle"].setEnabled(enabled and not is_force)
                wdata["boost_value_input"].setEnabled(enabled and not is_force)
            # 立即尝试应用一次(若仪器已连接,通道就能匹配;否则等仪器连接后再应用)
            self._update_available_channels()

        # ---- 4. 固件下载 ----
        dl = snapshot.get("download", {}) or {}
        dl_mode = dl.get("mode", "FLASH")
        if hasattr(self, "download_mode_toggle") and self.download_mode_toggle:
            self.download_mode_toggle.setValue(dl_mode)
        fw_paths = dl.get("firmware_paths") or []
        fw_single = dl.get("firmware_path", "") or ""
        if fw_paths:
            self.firmware_paths = list(fw_paths)
            self.firmware_path = fw_paths[0]
        elif fw_single:
            self.firmware_paths = [fw_single]
            self.firmware_path = fw_single
        else:
            self.firmware_paths = []
            self.firmware_path = ""
        # 同步显示到 UI 的 QLineEdit(实际控件名是 firmware_file_input)
        if hasattr(self, "firmware_file_input") and self.firmware_file_input is not None:
            if self.firmware_paths:
                names = [os.path.basename(p) for p in self.firmware_paths]
                self.firmware_file_input.setText("; ".join(names))
            else:
                self.firmware_file_input.setText("")

        # ---- 5. Chip 选择与 config_text ----
        chip_name = snapshot.get("chip_selected", "") or ""
        if chip_name and hasattr(self, "chip_combo") and self.chip_combo is not None:
            for i in range(self.chip_combo.count()):
                if self.chip_combo.itemText(i) == chip_name:
                    self.chip_combo.setCurrentIndex(i)
                    break
        cfg_text = snapshot.get("config_text", "") or ""
        if hasattr(self, "config_text_edit") and self.config_text_edit is not None:
            self.config_text_edit.setPlainText(cfg_text)
        if getattr(self, "force_config_cb", None) is not None and "force_config_enabled" in snapshot:
            try:
                self.force_config_cb.setChecked(bool(snapshot.get("force_config_enabled", False)))
            except Exception:
                pass

        # ---- 6. 测试参数 ----
        test_cfg = snapshot.get("test", {}) or {}
        if "test_time" in test_cfg and hasattr(self, "test_time_input"):
            try:
                self.test_time_input.setText(str(test_cfg["test_time"]))
            except Exception:
                pass
        if hasattr(self, "control_method_toggle") and self.control_method_toggle:
            cm = test_cfg.get("control_method", "N6705C")
            if cm in ("N6705C", "MCU"):
                self.control_method_toggle.setValue(cm)

        def _select_combo_text(combo, text):
            if combo is None or not text:
                return False
            for i in range(combo.count()):
                if combo.itemText(i) == text:
                    combo.setCurrentIndex(i)
                    return True
            return False

        # poweron / reset 通道:若当前选项还没有,记到 pending,等仪器连接后应用
        self._pending_aux_selections = {}
        poweron_txt = test_cfg.get("poweron_channel", "") or ""
        reset_txt = test_cfg.get("reset_channel", "") or ""
        if poweron_txt and not _select_combo_text(
                getattr(self, "poweron_channel_combo", None), poweron_txt):
            self._pending_aux_selections["poweron"] = poweron_txt
        if reset_txt and not _select_combo_text(
                getattr(self, "reset_channel_combo", None), reset_txt):
            self._pending_aux_selections["reset"] = reset_txt
        if not self._pending_aux_selections:
            self._pending_aux_selections = None

        if getattr(self, "poweron_polarity_toggle", None):
            self.poweron_polarity_toggle.setValue(test_cfg.get("poweron_polarity", "rising"))
        if getattr(self, "reset_polarity_toggle", None):
            self.reset_polarity_toggle.setValue(test_cfg.get("reset_polarity", "rising"))
        if getattr(self, "reset_enable_cb", None) is not None and "reset_enabled" in test_cfg:
            try:
                self.reset_enable_cb.setChecked(bool(test_cfg.get("reset_enabled", False)))
            except Exception:
                pass

        # ---- 7. 自动连接仪器(延迟到事件循环,避免阻塞 UI) ----
        if pending_connects:
            self.append_log(
                f"[CONFIG] Auto-connecting N6705C: {', '.join(pending_connects)} ..."
            )
            QTimer.singleShot(100, lambda labels=list(pending_connects):
                              self._auto_connect_instruments(labels))
        if pending_mcu_connect and not getattr(self, "is_mcu_connected", False):
            self.append_log("[CONFIG] Auto-connecting MCU IO ...")
            QTimer.singleShot(150, self._connect_mcu)
        if pending_connects or pending_mcu_connect:
            return
        else:
            # 没有需要自动连接的仪器,立即恢复 preset 机制
            self._suppress_preset_channels = False

    def _auto_connect_instruments(self, labels):
        """按列表顺序自动连接 N6705C 仪器。已连接的跳过。"""
        try:
            for label in labels:
                attr = label.lower()
                if getattr(self, f"is_connected_{attr}", False):
                    continue
                try:
                    self._connect_device(label)
                except Exception as e:
                    self.append_log(f"[WARNING] Auto-connect N6705C-{label} failed: {e}")
        finally:
            # 仪器连接完成后恢复 preset 机制,并再跑一次通道刷新,
            # 使得此时仪器上线带来的可用通道列表能应用到导入的配置上
            self._suppress_preset_channels = False
            try:
                self._update_available_channels()
            except Exception as e:
                self.append_log(f"[WARNING] Post-connect channel refresh failed: {e}")

    def _on_start_test(self):
        self._start_test()

    def _start_test(self):
        if self.is_testing:
            return

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        force_high_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}

        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                self.append_log(f"[ERROR] Invalid channel key: {cfg['channel']}")
                return
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            is_conn = getattr(self, f"is_connected_{attr}", False)
            if not is_conn or not inst:
                self.append_log(f"[ERROR] N6705C-{device_label} is not connected (required by {cfg['name']}).")
                return
            if device_label not in force_high_map:
                force_high_map[device_label] = (inst, [])
            if hw_ch not in force_high_map[device_label][1]:
                force_high_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = 0
        self.bin_result_table.hide()
        self.start_test_btn.setStateWaiting()
        self.append_log(
            f"[TEST] Starting force-high consumption test: "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"time={test_time}s, base_period={sample_period*1e6:.0f}us"
        )

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is not None and hw_ch is not None:
                channel_names[(device_label, hw_ch)] = cfg["name"]

        worker = _ConsumptionTestForceHighWorker(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_high_map, test_time, sample_period,
            channel_names=channel_names,
            channel_force_configs=self._build_channel_force_configs(),
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.channel_result.connect(self._on_force_high_channel_result)
        worker.test_summary.connect(self._on_test_summary)
        worker.progress.connect(self.start_test_btn.setProgress)
        worker.error.connect(self._on_test_error)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        self.start_test_btn.setStateProgramming()
        self.start_test_btn._progress_timer.stop()
        thread.start()

    def consumption_test_force(self):
        if self.is_testing:
            return

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        force_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}

        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                self.append_log(f"[ERROR] Invalid channel key: {cfg['channel']}")
                return
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            is_conn = getattr(self, f"is_connected_{attr}", False)
            if not is_conn or not inst:
                self.append_log(f"[ERROR] N6705C-{device_label} is not connected (required by {cfg['name']}).")
                return
            if device_label not in force_map:
                force_map[device_label] = (inst, [])
            if hw_ch not in force_map[device_label][1]:
                force_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = 0
        self.bin_result_table.hide()
        self.start_test_btn.setStateWaiting()
        self.append_log(
            f"[TEST] Starting force-auto consumption test: "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"time={test_time}s, base_period={sample_period*1e6:.0f}us"
        )

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is not None and hw_ch is not None:
                channel_names[(device_label, hw_ch)] = cfg["name"]

        worker = _ConsumptionTestForceWorker(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_map, test_time, sample_period,
            channel_names=channel_names,
            channel_force_configs=self._build_channel_force_configs(),
        )
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.log_message.connect(self.append_log)
        worker.channel_result.connect(self._on_force_high_channel_result)
        worker.test_summary.connect(self._on_test_summary)
        worker.progress.connect(self.start_test_btn.setProgress)
        worker.error.connect(self._on_test_error)
        worker.finished.connect(self._on_test_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(self._on_test_thread_cleaned)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._test_thread = thread
        self._test_worker = worker
        self.start_test_btn.setStateProgramming()
        self.start_test_btn._progress_timer.stop()
        thread.start()

    def _on_force_high_channel_result(self, device_label, hw_channel, avg_current, phase):
        cfg_idx = self._config_index_map.get(device_label, {}).get(hw_channel)
        if cfg_idx is not None and cfg_idx in self.channel_cards:
            label = self.channel_cards[cfg_idx]["value_label"]
            label.setText(self._format_current(avg_current))

    def _on_test_summary(self, summary):
        vbat_remain = summary.get("vbat_remain")
        if vbat_remain is not None and self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText(self._format_current(vbat_remain))

        if self._current_total_bins > 1:
            self._bin_results_data.append(summary)
            self._add_bin_result_row(summary)

    def _on_test_error(self, err_msg):
        self.append_log(f"[ERROR] {err_msg}")

    def _on_test_finished(self):
        self.is_testing = False
        self.start_test_btn.setStateComplete()
        self.append_log("[TEST] Test completed.")

    def _on_test_thread_cleaned(self):
        self._test_worker = None
        self._test_thread = None

    def _stop_test(self):
        if self._test_worker:
            self._test_worker.stop()
        self.is_testing = False
        self.start_test_btn.setStateFailed()
        self.append_log("[TEST] Test stopped.")

    def _on_auto_test(self):
        if self.is_testing:
            self.append_log("[WARNING] A test is already running.")
            return

        firmware_paths = getattr(self, 'firmware_paths', [])
        if not firmware_paths:
            if self.firmware_path:
                firmware_paths = [self.firmware_path]
            else:
                self.append_log("[ERROR] No firmware file selected.")
                return

        port_text = self.get_selected_serial_port()
        if not port_text:
            self.append_log("[ERROR] No serial port selected.")
            return
        m = re.search(r'(\d+)', port_text)
        com_port = m.group(1) if m else port_text

        mode_str = self.download_mode_toggle.value().lower()
        download_mode = DownloadMode.FLASH if mode_str == "flash" else DownloadMode.RAMRUN

        enabled_configs = [
            (i, cfg) for i, cfg in enumerate(self._channel_configs) if cfg["enabled"]
        ]
        if not enabled_configs:
            self.append_log("[ERROR] No channel enabled.")
            return

        vbat_idx = None
        vbat_cfg = None
        for i, cfg in enabled_configs:
            if cfg["name"].lower().startswith("vbat"):
                vbat_idx = i
                vbat_cfg = cfg
                break
        if vbat_cfg is None:
            vbat_idx, vbat_cfg = enabled_configs[0]

        vbat_device_label, vbat_hw_ch = self._parse_channel_key(vbat_cfg["channel"])
        if vbat_device_label is None or vbat_hw_ch is None:
            self.append_log(f"[ERROR] Invalid Vbat channel key: {vbat_cfg['channel']}")
            return

        vbat_attr = vbat_device_label.lower()
        vbat_inst = getattr(self, f"n6705c_{vbat_attr}", None)
        vbat_conn = getattr(self, f"is_connected_{vbat_attr}", False)
        if not vbat_conn or not vbat_inst:
            self.append_log(f"[ERROR] N6705C-{vbat_device_label} is not connected (required by Vbat).")
            return

        poweron_key = self.poweron_channel_combo.currentText() if self.poweron_channel_combo else ""
        reset_enabled = (
            self.reset_enable_cb.isChecked()
            if getattr(self, "reset_enable_cb", None) is not None else False
        )
        control_method = (
            self.control_method_toggle.value()
            if getattr(self, "control_method_toggle", None) else "N6705C"
        )
        reset_key = self.reset_channel_combo.currentText() if self.reset_channel_combo else ""
        if not poweron_key:
            self.append_log("[ERROR] PowerON channel not configured.")
            return
        if reset_enabled and not reset_key:
            self.append_log("[ERROR] RESET channel not configured.")
            return

        poweron_dl, poweron_hw = self._parse_channel_key(poweron_key)
        if poweron_dl is None:
            self.append_log("[ERROR] Invalid PowerON channel key.")
            return
        if reset_enabled:
            reset_dl, reset_hw = self._parse_channel_key(reset_key)
            if reset_dl is None:
                self.append_log("[ERROR] Invalid RESET channel key.")
                return
        else:
            reset_dl, reset_hw = None, None

        if control_method == "MCU":
            if poweron_dl != "MCU" or (reset_enabled and reset_dl != "MCU"):
                self.append_log("[ERROR] MCU control requires GPIO channels for PowerON/RESET.")
                return
            if not self.is_mcu_connected or self.mcu_io is None:
                self.append_log("[ERROR] MCU IO is not connected (required by PowerON/RESET).")
                return
            poweron_inst = self.mcu_io
            poweron_dl = "MCU"
            if reset_enabled:
                reset_inst = self.mcu_io
                reset_dl = "MCU"
            else:
                reset_inst = None
        else:
            poweron_attr = poweron_dl.lower()
            poweron_inst = getattr(self, f"n6705c_{poweron_attr}", None)
            poweron_conn = getattr(self, f"is_connected_{poweron_attr}", False)
            if not poweron_conn or not poweron_inst:
                self.append_log(f"[ERROR] N6705C-{poweron_dl} is not connected (required by PowerON).")
                return

            if reset_enabled:
                reset_attr = reset_dl.lower()
                reset_inst = getattr(self, f"n6705c_{reset_attr}", None)
                reset_conn = getattr(self, f"is_connected_{reset_attr}", False)
                if not reset_conn or not reset_inst:
                    self.append_log(f"[ERROR] N6705C-{reset_dl} is not connected (required by RESET).")
                    return
            else:
                reset_inst = None

        poweron_polarity = self.poweron_polarity_toggle.value()
        reset_polarity = (
            self.reset_polarity_toggle.value() if reset_enabled else "rising"
        )

        force_map = {}
        config_index_map = {vbat_device_label: {vbat_hw_ch: vbat_idx}}
        sub_configs = [(i, cfg) for i, cfg in enabled_configs if i != vbat_idx]
        for i, cfg in sub_configs:
            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
            if device_label is None or hw_ch is None:
                self.append_log(f"[ERROR] Invalid channel key: {cfg['channel']}")
                return
            attr = device_label.lower()
            inst = getattr(self, f"n6705c_{attr}", None)
            is_conn = getattr(self, f"is_connected_{attr}", False)
            if not is_conn or not inst:
                self.append_log(f"[ERROR] N6705C-{device_label} is not connected (required by {cfg['name']}).")
                return
            if device_label not in force_map:
                force_map[device_label] = (inst, [])
            if hw_ch not in force_map[device_label][1]:
                force_map[device_label][1].append(hw_ch)
            config_index_map.setdefault(device_label, {})[hw_ch] = i

        try:
            test_time = float(self.test_time_input.text())
        except ValueError:
            self.append_log("[ERROR] Invalid test time.")
            return
        sample_period = 20.0 / 1_000_000

        channel_names = {}
        channel_names[(vbat_device_label, vbat_hw_ch)] = vbat_cfg["name"]
        for i, cfg in sub_configs:
            dl, hw = self._parse_channel_key(cfg["channel"])
            if dl is not None and hw is not None:
                channel_names[(dl, hw)] = cfg["name"]

        config_text = self.config_text_edit.toPlainText().strip()
        chip_combo_text = self.chip_combo.currentText() if self.chip_combo.currentIndex() > 0 else None

        self.is_testing = True
        self._config_index_map = config_index_map
        self._current_total_bins = len(firmware_paths)
        self.auto_test_btn.setStateWaiting()

        for idx in self.channel_cards:
            self.channel_cards[idx]["value_label"].setText("- - -")
        if self._vbat_remain_card is not None:
            self._vbat_remain_card["value_label"].setText("- - -")

        if self._current_total_bins > 1:
            self._setup_bin_result_table()
        else:
            self.bin_result_table.hide()

        reset_desc = f"{reset_key}({reset_polarity})" if reset_enabled else "DISABLED"
        self.append_log(
            f"[AUTO_TEST] Starting auto test: {len(firmware_paths)} BIN(s), "
            f"Vbat={vbat_cfg['name']}({vbat_cfg['channel']}), "
            f"Control={control_method}, "
            f"PowerON={poweron_key}({poweron_polarity}), "
            f"RESET={reset_desc}"
        )

        worker_kwargs = dict(
            com_port=com_port,
            firmware_paths=firmware_paths,
            download_mode=download_mode,
            poweron_device_label=poweron_dl,
            poweron_inst=poweron_inst,
            poweron_hw_ch=poweron_hw,
            poweron_polarity=poweron_polarity,
            reset_device_label=reset_dl,
            reset_inst=reset_inst,
            reset_hw_ch=reset_hw,
            reset_polarity=reset_polarity,
            vbat_device_label=vbat_device_label,
            vbat_inst=vbat_inst,
            vbat_hw_ch=vbat_hw_ch,
            force_map=force_map,
            test_time=test_time,
            sample_period=sample_period,
            channel_names=channel_names,
            chip_combo_text=chip_combo_text,
            selected_chip_config=self.selected_chip_config,
            config_text=config_text,
            parse_config_commands_fn=self._parse_config_commands,
            resolve_device_fn=self._resolve_device,
            channel_force_configs=self._build_channel_force_configs(),
            force_config_enabled=(
                self.force_config_cb.isChecked()
                if getattr(self, "force_config_cb", None) is not None else False
            ),
            control_method=control_method,
        )
        self._controller.start_auto_test(worker_kwargs)
        self.auto_test_btn.setStateProgramming()
        self.auto_test_btn._progress_timer.stop()

    def _on_auto_test_error(self, err_msg):
        pass

    def _on_auto_test_finished(self):
        self.is_testing = False
        self.auto_test_btn.setStateComplete()

    def _on_auto_test_thread_cleaned(self):
        self._auto_test_worker = None
        self._auto_test_thread = None

    def _stop_auto_test(self):
        self._controller.stop_auto_test()
        self.is_testing = False
        self.auto_test_btn.setStateFailed()
        self.append_log("[AUTO_TEST] Auto test stopped by user.")

    def _save_datalog(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save DataLog", "",
            "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            logger.info("Saving datalog to: %s", file_path)
            self.append_log(f"[SYSTEM] DataLog saved to: {file_path}")

    def _export_bin_results_to_excel(self):
        """把 BIN 结果导出为 .xlsx。

        - 电流列(每个 enabled 通道 + Vbat_remain)统一换算为 µA,
          且单位只写在表头(形如 "Vbat (µA)"),数据单元格里只保留裸数值,
          方便后续在 Excel 里继续计算 / 画图。
        - 非电流列(BIN / Voltage)保持原样(Voltage 仍为 "3.800 | 3.800" 这类
          由 UI 组装好的字符串,与 QTableWidget 一致)。
        - 数据源优先使用 self._bin_results_data(即测试时原始 summary,含浮点数),
          因此不受 UI 单位自动换算格式(mA/µA/nA)的影响。
        """
        table = getattr(self, "bin_result_table", None)
        summaries = list(getattr(self, "_bin_results_data", []) or [])
        if table is None or table.columnCount() == 0 or not summaries:
            QMessageBox.information(
                self, "Nothing to Export",
                "There are no BIN results to export yet.\n"
                "Run an Auto Test first and try again."
            )
            return

        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            QMessageBox.critical(
                self, "Export Failed",
                "Python package 'openpyxl' is required to export Excel.\n"
                "Please install it first:\n\n    pip install openpyxl"
            )
            return

        from datetime import datetime
        default_name = f"consumption_bin_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        default_path = os.path.join(os.getcwd(), default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export BIN Results",
            default_path,
            "Excel Files (*.xlsx);;All Files (*)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".xlsx"):
            file_path += ".xlsx"

        try:
            # ---- 先根据 enabled 通道配置组装列定义 ----
            # column 元组: (title, kind)
            #   kind = "bin" | "voltage" | "current" | "vbat_remain"
            unit_suffix = " (\u00b5A)"  # µA
            columns = [("BIN", "bin"), ("Voltage", "voltage")]
            enabled_cfgs = [cfg for cfg in self._channel_configs if cfg["enabled"]]
            for cfg in enabled_cfgs:
                columns.append((f"{cfg['name']}{unit_suffix}", "current", cfg))
            has_sub = any(
                not cfg["name"].lower().startswith("vbat") for cfg in enabled_cfgs
            )
            if has_sub:
                columns.append((f"Vbat_remain{unit_suffix}", "vbat_remain"))

            def _to_ua(value):
                """A -> µA;None / 非数值返回空串。"""
                if value is None:
                    return ""
                try:
                    return round(float(value) * 1e6, 3)
                except (TypeError, ValueError):
                    return ""

            def _voltage_text(summary):
                channel_voltages = summary.get("channel_voltages", {}) or {}
                parts = []
                for cfg in enabled_cfgs:
                    device_label, hw_ch = self._parse_channel_key(cfg["channel"])
                    v = channel_voltages.get((device_label, hw_ch))
                    parts.append(f"{v:.4g}" if v is not None else "N/A")
                return " | ".join(parts) if parts else "- - -"

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "BIN Results"

            header_font = Font(bold=True, color="FFFFFF", size=11)
            header_fill = PatternFill("solid", fgColor="1F3864")
            header_align = Alignment(horizontal="center", vertical="center")
            cell_align = Alignment(horizontal="center", vertical="center")
            thin_side = Side(style="thin", color="B4C7E7")
            thin_border = Border(
                left=thin_side, right=thin_side,
                top=thin_side, bottom=thin_side,
            )
            row_fill_even = PatternFill("solid", fgColor="F2F6FC")

            for col_idx, col_def in enumerate(columns, start=1):
                title = col_def[0]
                cell = ws.cell(row=1, column=col_idx, value=title)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_align
                cell.border = thin_border

            # ---- 数据行 ----
            for r, summary in enumerate(summaries):
                excel_row = r + 2
                bin_name = summary.get("bin_name", f"BIN-{r + 1}")
                channels = summary.get("channels", {}) or {}
                vbat_current = summary.get("vbat")
                vbat_remain = summary.get("vbat_remain")

                for col_idx, col_def in enumerate(columns, start=1):
                    kind = col_def[1]
                    if kind == "bin":
                        value = bin_name
                    elif kind == "voltage":
                        value = _voltage_text(summary)
                    elif kind == "current":
                        cfg = col_def[2]
                        if cfg["name"].lower().startswith("vbat"):
                            value = _to_ua(vbat_current)
                        else:
                            device_label, hw_ch = self._parse_channel_key(cfg["channel"])
                            value = _to_ua(channels.get((device_label, hw_ch)))
                    elif kind == "vbat_remain":
                        value = _to_ua(vbat_remain)
                    else:
                        value = ""

                    cell = ws.cell(row=excel_row, column=col_idx, value=value)
                    cell.alignment = cell_align
                    cell.border = thin_border
                    if isinstance(value, (int, float)):
                        cell.number_format = "0.000"
                    if r % 2 == 1:
                        cell.fill = row_fill_even

            # ---- 列宽自适应 ----
            for col_idx, col_def in enumerate(columns, start=1):
                title = col_def[0]
                max_len = len(str(title))
                for row_cells in ws.iter_rows(
                    min_row=2, max_row=len(summaries) + 1,
                    min_col=col_idx, max_col=col_idx,
                ):
                    for c in row_cells:
                        tl = len(str(c.value)) if c.value is not None else 0
                        if tl > max_len:
                            max_len = tl
                ws.column_dimensions[get_column_letter(col_idx)].width = min(
                    max(max_len + 4, 10), 40
                )
            ws.row_dimensions[1].height = 22
            ws.freeze_panes = "A2"

            wb.save(file_path)
            self.append_log(f"[EXPORT] BIN results exported to: {file_path}")
            QMessageBox.information(
                self, "Export Succeeded",
                f"BIN results have been exported to:\n{file_path}"
            )
        except Exception as e:
            logger.exception("Export BIN results failed")
            self.append_log(f"[ERROR] Export BIN results failed: {e}")
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export BIN results:\n{e}"
            )

    @staticmethod
    def _format_current(current_A):
        abs_i = abs(current_A)
        if abs_i >= 1:
            return f"{current_A:.3f} A"
        elif abs_i >= 1e-3:
            return f"{current_A*1e3:.3f} mA"
        elif abs_i >= 1e-6:
            return f"{current_A*1e6:.3f} µA"
        elif abs_i >= 1e-9:
            return f"{current_A*1e9:.3f} nA"
        else:
            return f"{current_A:.3e} A"

    def update_channel_current(self, channel_idx, avg_current):
        if channel_idx in self.channel_cards:
            label = self.channel_cards[channel_idx]["value_label"]
            if avg_current is not None:
                label.setText(self._format_current(avg_current))
            else:
                label.setText("- - -")

    def get_selected_channels(self):
        return [
            cfg["channel"] for cfg in self._channel_configs if cfg["enabled"]
        ]

    def get_test_config(self):
        return {
            'n6705c_a_connected': self.is_connected_a,
            'n6705c_b_connected': self.is_connected_b,
            'firmware_path': self.firmware_path,
            'config_content': self.config_content,
            'selected_chip': self.selected_chip_config,
            'channel_configs': self._channel_configs,
        }

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
