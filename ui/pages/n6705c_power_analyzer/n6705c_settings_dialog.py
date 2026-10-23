# -*- coding: utf-8 -*-
"""N6705C Datalog 设置对话框（底部控制栏齿轮入口）。

五个标签页：
1. Instruments      —— 默认仪器管理（新增/修改/删除 + 自动连接，与仪器连接面板联动）
2. Network Scan     —— 跨网段主动扫描 CIDR 配置（discovery.json extra_subnets）
3. DLog Save        —— 录制完成后自动保存 .dlog（开关/目录/命名模板/序号递增）
4. Waveform Summary —— 波形摘要事件算法与分段参数（AISettings + 本模块设置）
5. About            —— 版本信息 / 配置目录 / RESET JSON 还原默认配置

本模块不 import 主页面模块（n6705c_datalog_ui），仅持有其引用调用公共方法，
避免循环依赖；设置存取为模块级函数，供主页面热路径（波形摘要渲染 /
录制收尾自动保存）直接读取。
"""

import dataclasses
import ipaddress
import json
import os
import platform
import re
from datetime import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)

from core.ai.config import AISettings
from log_config import get_logger
from ui.resource_path import get_user_data_dir, is_frozen
from ui.pages.n6705c_power_analyzer import datalog_style as dss

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Datalog 应用设置（user_data/n6705c/datalog_settings.json）
# ---------------------------------------------------------------------------

_SETTINGS_FILENAME = "datalog_settings.json"

_DEFAULT_SETTINGS = {
    "auto_connect_enabled": True,
    "dlog_save": {
        "auto_save": False,
        "save_dir": "",
        "name_template": "dlog_{datetime}",
        "auto_increment": False,
        "next_seq": 1,
    },
    "waveform_summary": {
        "max_stages": 40,
        "lttb_threshold": 3000,
        "pelt_max_n": 4000,
    },
}


def _settings_path() -> str:
    return os.path.join(get_user_data_dir("n6705c"), _SETTINGS_FILENAME)


def load_datalog_app_settings() -> dict:
    """读取 Datalog 应用设置；文件缺失/损坏时回退默认值。"""
    cfg = json.loads(json.dumps(_DEFAULT_SETTINGS))  # 深拷贝默认
    path = _settings_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            for key, val in raw.items():
                if isinstance(val, dict) and isinstance(cfg.get(key), dict):
                    cfg[key].update(val)
                elif key in cfg:
                    cfg[key] = val
        except (OSError, json.JSONDecodeError):
            logger.error("读取 datalog_settings.json 失败: %s", path, exc_info=True)
    return cfg


def save_datalog_app_settings(cfg: dict) -> bool:
    path = _settings_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        logger.error("写入 datalog_settings.json 失败: %s", path, exc_info=True)
        return False


def waveform_summary_params() -> dict:
    """波形摘要渲染参数（_build_summary_stages 用）：max_stages/lttb_threshold/pelt_max_n。"""
    cfg = load_datalog_app_settings().get("waveform_summary", {})
    try:
        max_stages = max(1, int(cfg.get("max_stages", 40)))
    except (TypeError, ValueError):
        max_stages = 40
    try:
        lttb = max(100, int(cfg.get("lttb_threshold", 3000)))
    except (TypeError, ValueError):
        lttb = 3000
    try:
        pelt_max_n = max(100, int(cfg.get("pelt_max_n", 4000)))
    except (TypeError, ValueError):
        pelt_max_n = 4000
    return {
        "max_stages": max_stages,
        "lttb_threshold": lttb,
        "pelt_max_n": pelt_max_n,
    }


def default_dlog_save_dir() -> str:
    """自动保存默认目录：开发态 <项目根>/Results/datalog；打包后用户数据目录。"""
    if is_frozen():
        return get_user_data_dir("n6705c", "datalog")
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )))
    return os.path.join(project_root, "Results", "datalog")


def _dedupe_dlog_base(base: str) -> str:
    """未开序号递增时避免覆盖：base.dlog 已存在则追加 _2/_3..."""
    candidate = base
    idx = 2
    while os.path.exists(f"{candidate}.dlog"):
        candidate = f"{base}_{idx}"
        idx += 1
    return candidate


def build_auto_save_paths(cfg: dict, unit_count: int) -> tuple[list[str], int | None]:
    """按 DLog Save 设置生成自动保存路径。

    模板占位符：{date}=YYYYMMDD、{time}=HHMMSS、{datetime}=YYYYMMDD_HHMMSS、{seq}=NNN。
    auto_increment 开启：模板含 {seq} 则替换为当前序号，否则文件名追加 _NNN；
    返回的 next_seq 由调用方落盘。未开启时文件已存在则追加 _2/_3 防覆盖。

    返回 (paths, next_seq)；next_seq 为 None 表示本次未消耗序号。
    """
    save_cfg = cfg.get("dlog_save", {}) if isinstance(cfg, dict) else {}
    template = str(save_cfg.get("name_template") or "dlog_{datetime}").strip() \
        or "dlog_{datetime}"
    save_dir = str(save_cfg.get("save_dir") or "").strip() or default_dlog_save_dir()

    now = datetime.now()
    name = template.replace("{datetime}", now.strftime("%Y%m%d_%H%M%S"))
    name = name.replace("{date}", now.strftime("%Y%m%d"))
    name = name.replace("{time}", now.strftime("%H%M%S"))

    auto_inc = bool(save_cfg.get("auto_increment"))
    next_seq = None
    if auto_inc:
        try:
            seq = max(1, int(save_cfg.get("next_seq", 1)))
        except (TypeError, ValueError):
            seq = 1
        next_seq = seq + 1
        if "{seq}" in name:
            name = name.replace("{seq}", f"{seq:03d}")
        else:
            name = f"{name}_{seq:03d}"
    else:
        name = name.replace("{seq}", "")
        # 占位符置空后折叠残留的分隔符（run__20261023 → run_20261023）
        name = re.sub(r"[_\-]{2,}", "_", name).strip("_-")

    name = re.sub(r'[<>:"/\\|?*]', "_", name).strip(" ._-") or "dlog"
    base = os.path.join(save_dir, name)
    if not auto_inc:
        base = _dedupe_dlog_base(base)

    unit_count = max(1, int(unit_count))
    paths = [f"{base}.dlog"]
    paths.extend(f"{base}_unit{idx}.dlog" for idx in range(1, unit_count))
    return paths, next_seq


# ---------------------------------------------------------------------------
# 默认仪器列表（user_data/n6705c/default_devices.json）读写
# ---------------------------------------------------------------------------

def _default_devices_path() -> str:
    return os.path.join(get_user_data_dir("n6705c"), "default_devices.json")


def load_default_devices() -> list[dict]:
    path = _default_devices_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        devices = data.get("devices", []) if isinstance(data, dict) else []
        return [d for d in devices if isinstance(d, dict) and d.get("visa_resource")]
    except (OSError, json.JSONDecodeError):
        logger.debug("Load default_devices.json failed", exc_info=True)
        return []


def save_default_devices(devices: list[dict]) -> bool:
    path = _default_devices_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"devices": devices}, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        logger.warning("Write default_devices.json failed", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# 对话框 QSS（叠加在 dss.dlg_style 之上）
# ---------------------------------------------------------------------------

_SETTINGS_QSS = """
    QTabWidget::pane {
        border: 1px solid #1e3460;
        border-radius: 3px;
        background-color: #0a1628;
        top: -1px;
    }
    QTabBar::tab {
        background-color: #0c1a35;
        color: #8eb0e3;
        padding: 6px 12px;
        border: 1px solid #1e3460;
        border-bottom: none;
        border-top-left-radius: 3px;
        border-top-right-radius: 3px;
        margin-right: 2px;
        font-size: 12px;
    }
    QTabBar::tab:selected {
        background-color: #162d55;
        color: #eaf2ff;
    }
    QTabBar::tab:hover:!selected {
        background-color: #122448;
    }
    QCheckBox {
        color: #c8daf5;
        font-size: 12px;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 14px;
        height: 14px;
    }
    QCheckBox:disabled {
        color: #3a5070;
    }
    QSpinBox, QDoubleSpinBox {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        border-radius: 3px;
        color: #eaf2ff;
        padding: 4px 8px;
        font-size: 12px;
    }
    QSpinBox:focus, QDoubleSpinBox:focus {
        border-color: #3a6fd4;
    }
    QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {
        background-color: #0a1428;
        color: #3a5070;
        border-color: #142542;
    }
    QTableWidget#settingsTable {
        background-color: transparent;
        border: 1px solid #152040;
        color: #c8daf5;
        font-size: 12px;
        gridline-color: #152040;
    }
    QTableWidget#settingsTable::item {
        padding: 2px 8px;
    }
    QTableWidget#settingsTable::item:selected {
        background-color: #1e3460;
    }
    QTableWidget#settingsTable QHeaderView::section {
        background-color: #0b1528;
        color: #5a7fad;
        font-weight: 600;
        font-size: 11px;
        padding: 4px 8px;
        border: none;
        border-bottom: 2px solid #1a2b52;
        border-right: 1px solid #12203a;
    }
    QTableWidget#settingsTable QHeaderView::section:last {
        border-right: none;
    }
    QListWidget#settingsList {
        background-color: #0c1a35;
        border: 1px solid #1e3460;
        border-radius: 3px;
        color: #eaf2ff;
        font-size: 12px;
    }
    QListWidget#settingsList::item {
        padding: 4px 8px;
    }
    QListWidget#settingsList::item:selected {
        background-color: #1e3460;
    }
"""

_RESET_BTN_STYLE = """
    QPushButton {
        background-color: #4a1626;
        border: 1px solid #d14b72;
        border-radius: 3px;
        color: #ffd7e2;
        padding: 6px 18px;
        font-size: 12px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #6b1f35;
    }
"""


# ---------------------------------------------------------------------------
# 单台仪器 新增/修改 子对话框
# ---------------------------------------------------------------------------

class _InstrumentEditDialog(QDialog):
    """新增/修改一台默认仪器；返回 {serial, model, display_ip, visa_resource, auto_connect}。"""

    def __init__(self, parent=None, device=None, lock_address=False):
        super().__init__(parent)
        self._result = None
        self.setWindowTitle("Edit Instrument" if device else "Add Instrument")
        self.setFixedWidth(420)
        self.setStyleSheet(dss.dlg_style(combo=True))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Edit Instrument" if device else "Add Instrument")
        title.setStyleSheet(dss.DIALOG_TITLE_STYLE)
        layout.addWidget(title)

        device = device or {}
        visa_resource = device.get("visa_resource", "")
        is_usb = visa_resource.upper().startswith("USB")

        layout.addWidget(QLabel("Connection Type"))
        self._conn_type_combo = QComboBox()
        self._conn_type_combo.addItems(["TCP/IP (LAN)", "USB"])
        self._conn_type_combo.setCurrentIndex(1 if is_usb else 0)
        layout.addWidget(self._conn_type_combo)

        self._ip_label = QLabel("IP Address")
        layout.addWidget(self._ip_label)
        self._ip_edit = QLineEdit()
        self._ip_edit.setPlaceholderText("e.g. 192.168.3.99")
        layout.addWidget(self._ip_edit)

        self._usb_label = QLabel("USB Resource String")
        layout.addWidget(self._usb_label)
        self._usb_edit = QLineEdit()
        self._usb_edit.setPlaceholderText("e.g. USB0::0x2A8D::0x1802::MY56006098::INSTR")
        layout.addWidget(self._usb_edit)

        if is_usb:
            self._usb_edit.setText(visa_resource)
            self._ip_label.hide()
            self._ip_edit.hide()
        else:
            ip = visa_resource.split("::")[1] if "::" in visa_resource else ""
            self._ip_edit.setText(device.get("display_ip") or ip)
            self._usb_label.hide()
            self._usb_edit.hide()

        layout.addWidget(QLabel("Serial Number (optional)"))
        self._serial_edit = QLineEdit()
        self._serial_edit.setPlaceholderText("e.g. MY56006098")
        self._serial_edit.setText(device.get("serial", ""))
        layout.addWidget(self._serial_edit)

        self._auto_connect_cb = QCheckBox("Auto Connect (connect on startup)")
        self._auto_connect_cb.setChecked(bool(device.get("auto_connect", False)))
        layout.addWidget(self._auto_connect_cb)

        if lock_address:
            # 已连接 / 连接中的仪器禁止改地址，仅允许改序列号与自动连接
            self._conn_type_combo.setEnabled(False)
            self._ip_edit.setEnabled(False)
            self._usb_edit.setEnabled(False)
            lock_hint = QLabel("该仪器当前已连接或连接中，地址不可修改。")
            lock_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
            layout.addWidget(lock_hint)

        self._conn_type_combo.currentIndexChanged.connect(self._on_conn_type_changed)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QPushButton("Save")
        ok_btn.setStyleSheet(dss.PRIMARY_BTN_STYLE)
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        ok_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _on_conn_type_changed(self, index):
        lan = index == 0
        self._ip_label.setVisible(lan)
        self._ip_edit.setVisible(lan)
        self._usb_label.setVisible(not lan)
        self._usb_edit.setVisible(not lan)

    def _on_save(self):
        if self._conn_type_combo.currentIndex() == 0:
            ip = self._ip_edit.text().strip()
            if not ip:
                QMessageBox.warning(self, "输入不完整", "请填写 IP 地址。")
                return
            visa_resource = f"TCPIP0::{ip}::hislip0::INSTR"
            display_ip = ip
        else:
            usb_str = self._usb_edit.text().strip()
            if not usb_str:
                QMessageBox.warning(self, "输入不完整", "请填写 USB 资源串。")
                return
            visa_resource = usb_str
            display_ip = usb_str
        serial = self._serial_edit.text().strip() or visa_resource
        self._result = {
            "serial": serial,
            "model": "N6705C",
            "display_ip": display_ip,
            "visa_resource": visa_resource,
            "auto_connect": self._auto_connect_cb.isChecked(),
        }
        self.accept()

    def result_device(self):
        return self._result


# ---------------------------------------------------------------------------
# 设置主对话框
# ---------------------------------------------------------------------------

class N6705CSettingsDialog(QDialog):
    """Datalog 页设置对话框（五标签页）。

    datalog_ui：N6705CDatalogUI 实例，用于仪器列表变更后的卡片联动
    （apply_instrument_settings / is_instrument_busy / 自动连接触发）。
    """

    def __init__(self, datalog_ui):
        super().__init__(datalog_ui)
        self._ui = datalog_ui
        self.setWindowTitle("Settings")
        self.setMinimumSize(640, 520)
        self.setStyleSheet(dss.dlg_style(combo=True) + _SETTINGS_QSS)

        self._settings = load_datalog_app_settings()
        self._ai_settings = AISettings.load()
        self._devices = load_default_devices()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_instruments_tab(), "Instruments")
        self._tabs.addTab(self._build_network_tab(), "Network Scan")
        self._tabs.addTab(self._build_dlog_tab(), "DLog Save")
        self._tabs.addTab(self._build_waveform_tab(), "Waveform Summary")
        self._tabs.addTab(self._build_about_tab(), "About")
        layout.addWidget(self._tabs, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setDefault(False)
        self._cancel_btn.setAutoDefault(False)
        self._cancel_btn.clicked.connect(self.reject)
        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setDefault(False)
        self._apply_btn.setAutoDefault(False)
        self._apply_btn.clicked.connect(self._apply_all)
        self._ok_btn = QPushButton("OK")
        self._ok_btn.setStyleSheet(dss.PRIMARY_BTN_STYLE)
        self._ok_btn.setDefault(True)
        self._ok_btn.setAutoDefault(True)
        self._ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._apply_btn)
        btn_layout.addWidget(self._ok_btn)
        layout.addLayout(btn_layout)

    # ---- Tab 1: Instruments -------------------------------------------------

    def _build_instruments_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._auto_connect_enabled_cb = QCheckBox(
            "Enable auto connect on startup (per-instrument Auto Connect below)"
        )
        self._auto_connect_enabled_cb.setChecked(
            bool(self._settings.get("auto_connect_enabled", True))
        )
        layout.addWidget(self._auto_connect_enabled_cb)

        hint = QLabel(
            "管理默认仪器列表（与左侧仪器连接面板的设备卡片同源）。"
            "已连接或连接中的仪器不能删除，地址不可修改。"
        )
        hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._instruments_table = QTableWidget()
        self._instruments_table.setObjectName("settingsTable")
        self._instruments_table.setColumnCount(4)
        self._instruments_table.setHorizontalHeaderLabels(
            ["Model", "Serial", "Address", "Auto Connect"]
        )
        self._instruments_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._instruments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._instruments_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._instruments_table.verticalHeader().setVisible(False)
        self._instruments_table.horizontalHeader().setStretchLastSection(False)
        self._instruments_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._instruments_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._instruments_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._instruments_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._instruments_table.itemChanged.connect(self._on_instrument_item_changed)
        layout.addWidget(self._instruments_table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        add_btn = QPushButton("Add...")
        add_btn.setDefault(False)
        add_btn.setAutoDefault(False)
        add_btn.clicked.connect(self._on_add_instrument)
        self._edit_instr_btn = QPushButton("Edit...")
        self._edit_instr_btn.setDefault(False)
        self._edit_instr_btn.setAutoDefault(False)
        self._edit_instr_btn.clicked.connect(self._on_edit_instrument)
        self._remove_instr_btn = QPushButton("Remove")
        self._remove_instr_btn.setDefault(False)
        self._remove_instr_btn.setAutoDefault(False)
        self._remove_instr_btn.clicked.connect(self._on_remove_instrument)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(self._edit_instr_btn)
        btn_row.addWidget(self._remove_instr_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._reload_instruments_table()
        return tab

    def _reload_instruments_table(self):
        table = self._instruments_table
        table.blockSignals(True)
        table.setRowCount(len(self._devices))
        for row, dev in enumerate(self._devices):
            visa_resource = dev.get("visa_resource", "")
            serial = dev.get("serial", "")
            busy = self._is_instrument_busy(serial, visa_resource)

            model_item = QTableWidgetItem(dev.get("model", "N6705C"))
            serial_text = serial + ("  (connected)" if busy else "")
            serial_item = QTableWidgetItem(serial_text)
            addr_item = QTableWidgetItem(visa_resource)
            addr_item.setToolTip(visa_resource)
            auto_item = QTableWidgetItem()
            auto_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable
            )
            auto_item.setCheckState(
                Qt.Checked if dev.get("auto_connect") else Qt.Unchecked
            )
            for item in (model_item, serial_item, addr_item):
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(row, 0, model_item)
            table.setItem(row, 1, serial_item)
            table.setItem(row, 2, addr_item)
            table.setItem(row, 3, auto_item)
        table.blockSignals(False)

    def _on_instrument_item_changed(self, item):
        if item is None or item.column() != 3:
            return
        row = item.row()
        if 0 <= row < len(self._devices):
            self._devices[row]["auto_connect"] = item.checkState() == Qt.Checked

    def _is_instrument_busy(self, serial, visa_resource) -> bool:
        checker = getattr(self._ui, "is_instrument_busy", None)
        if callable(checker):
            return bool(checker(serial, visa_resource))
        return False

    def _selected_instrument_row(self) -> int:
        selected = self._instruments_table.selectedItems()
        if not selected:
            return -1
        return selected[0].row()

    def _on_add_instrument(self):
        dialog = _InstrumentEditDialog(self)
        if dialog.exec() != QDialog.Accepted or not dialog.result_device():
            return
        dev = dialog.result_device()
        if any(d.get("visa_resource") == dev["visa_resource"] for d in self._devices):
            QMessageBox.information(self, "已存在", "该地址的仪器已在列表中。")
            return
        self._devices.append(dev)
        self._reload_instruments_table()

    def _on_edit_instrument(self):
        row = self._selected_instrument_row()
        if not (0 <= row < len(self._devices)):
            QMessageBox.information(self, "未选择", "请先在列表中选择一台仪器。")
            return
        dev = dict(self._devices[row])
        busy = self._is_instrument_busy(dev.get("serial"), dev.get("visa_resource"))
        dialog = _InstrumentEditDialog(self, device=dev, lock_address=busy)
        if dialog.exec() != QDialog.Accepted or not dialog.result_device():
            return
        new_dev = dialog.result_device()
        if busy:
            # 地址锁定时保留原地址（理论上控件已禁用，双保险）
            new_dev["visa_resource"] = dev["visa_resource"]
            new_dev["display_ip"] = dev.get("display_ip", "")
        elif any(
            d.get("visa_resource") == new_dev["visa_resource"]
            for i, d in enumerate(self._devices) if i != row
        ):
            QMessageBox.information(self, "已存在", "该地址已被列表中另一台仪器使用。")
            return
        self._devices[row] = new_dev
        self._reload_instruments_table()

    def _on_remove_instrument(self):
        row = self._selected_instrument_row()
        if not (0 <= row < len(self._devices)):
            QMessageBox.information(self, "未选择", "请先在列表中选择一台仪器。")
            return
        dev = self._devices[row]
        if self._is_instrument_busy(dev.get("serial"), dev.get("visa_resource")):
            QMessageBox.information(
                self, "无法删除", "该仪器已连接或正在连接中，请先断开连接后再删除。"
            )
            return
        del self._devices[row]
        self._reload_instruments_table()

    # ---- Tab 2: Network Scan ------------------------------------------------

    def _build_network_tab(self) -> QWidget:
        from core.n6705c.search_worker import _load_extra_subnets

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(
            "mDNS 只能自动发现本广播域（同一网段）内的仪器；被路由器 / VLAN 隔开的"
            "其它网段需在此配置后才会被主动扫描（CIDR 格式，如 10.31.40.0/24）。\n"
            "配置在下次点击 Refresh Search 时生效。"
        )
        hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._subnet_list = QListWidget()
        self._subnet_list.setObjectName("settingsList")
        self._subnet_list.setSelectionMode(QAbstractItemView.SingleSelection)
        for cidr in _load_extra_subnets():
            self._subnet_list.addItem(cidr)
        layout.addWidget(self._subnet_list, 1)

        add_row = QHBoxLayout()
        add_row.setSpacing(8)
        self._subnet_edit = QLineEdit()
        self._subnet_edit.setPlaceholderText("e.g. 10.31.40.0/24")
        add_subnet_btn = QPushButton("Add")
        add_subnet_btn.setDefault(False)
        add_subnet_btn.setAutoDefault(False)
        add_subnet_btn.clicked.connect(self._on_add_subnet)
        remove_subnet_btn = QPushButton("Remove")
        remove_subnet_btn.setDefault(False)
        remove_subnet_btn.setAutoDefault(False)
        remove_subnet_btn.clicked.connect(self._on_remove_subnet)
        add_row.addWidget(self._subnet_edit, 1)
        add_row.addWidget(add_subnet_btn)
        add_row.addWidget(remove_subnet_btn)
        layout.addLayout(add_row)
        return tab

    def _on_add_subnet(self):
        cidr = self._subnet_edit.text().strip()
        if not cidr:
            return
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            QMessageBox.warning(
                self, "格式错误", f"无效的网段（CIDR）：{cidr}\n示例：10.31.40.0/24"
            )
            return
        normalized = str(net)
        existing = [
            self._subnet_list.item(i).text() for i in range(self._subnet_list.count())
        ]
        if normalized in existing or cidr in existing:
            QMessageBox.information(self, "已存在", f"网段 {cidr} 已在列表中。")
            return
        self._subnet_list.addItem(cidr)
        self._subnet_edit.clear()

    def _on_remove_subnet(self):
        row = self._subnet_list.currentRow()
        if row < 0:
            QMessageBox.information(self, "未选择", "请先选择一个网段。")
            return
        self._subnet_list.takeItem(row)

    # ---- Tab 3: DLog Save ---------------------------------------------------

    def _build_dlog_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        save_cfg = self._settings.get("dlog_save", {})

        hint = QLabel(
            "录制（含手动停止）正常结束后，自动把原始 .dlog 写入指定目录，"
            "不再弹出保存对话框；多台仪器时第二台文件自动追加 _unit1 后缀。"
        )
        hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._auto_save_cb = QCheckBox("Auto save after recording stops")
        self._auto_save_cb.setChecked(bool(save_cfg.get("auto_save", False)))
        layout.addWidget(self._auto_save_cb)

        form = QFormLayout()
        form.setSpacing(8)

        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(8)
        self._save_dir_edit = QLineEdit(save_cfg.get("save_dir", ""))
        self._save_dir_edit.setPlaceholderText(f"默认: {default_dlog_save_dir()}")
        browse_btn = QPushButton("Browse...")
        browse_btn.setDefault(False)
        browse_btn.setAutoDefault(False)
        browse_btn.clicked.connect(self._on_browse_save_dir)
        dir_layout.addWidget(self._save_dir_edit, 1)
        dir_layout.addWidget(browse_btn)
        form.addRow("Save Directory", dir_row)

        self._name_template_edit = QLineEdit(
            save_cfg.get("name_template", "dlog_{datetime}")
        )
        self._name_template_edit.setPlaceholderText("dlog_{datetime}")
        self._name_template_edit.textChanged.connect(self._refresh_save_preview)
        form.addRow("Name Template", self._name_template_edit)

        self._auto_increment_cb = QCheckBox("Auto increment sequence number")
        self._auto_increment_cb.setChecked(bool(save_cfg.get("auto_increment", False)))
        self._auto_increment_cb.toggled.connect(self._refresh_save_preview)
        form.addRow("", self._auto_increment_cb)

        self._next_seq_spin = QSpinBox()
        self._next_seq_spin.setRange(1, 999999)
        try:
            self._next_seq_spin.setValue(max(1, int(save_cfg.get("next_seq", 1))))
        except (TypeError, ValueError):
            self._next_seq_spin.setValue(1)
        self._next_seq_spin.valueChanged.connect(self._refresh_save_preview)
        form.addRow("Next Sequence", self._next_seq_spin)

        layout.addLayout(form)

        tpl_hint = QLabel(
            "模板占位符：{date}=20261023，{time}=153012，{datetime}=20261023_153012，"
            "{seq}=001（仅勾选序号递增时生效；模板不含 {seq} 时自动追加 _NNN）。"
        )
        tpl_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        tpl_hint.setWordWrap(True)
        layout.addWidget(tpl_hint)

        self._save_preview_label = QLabel("")
        self._save_preview_label.setStyleSheet(dss.HINT_TEXT_STYLE)
        self._save_preview_label.setWordWrap(True)
        layout.addWidget(self._save_preview_label)
        layout.addStretch(1)
        self._refresh_save_preview()
        return tab

    def _on_browse_save_dir(self):
        current = self._save_dir_edit.text().strip() or default_dlog_save_dir()
        path = QFileDialog.getExistingDirectory(
            self, "Select Save Directory", current
        )
        if path:
            self._save_dir_edit.setText(path)

    def _refresh_save_preview(self):
        preview_cfg = {
            "dlog_save": {
                "save_dir": self._save_dir_edit.text(),
                "name_template": self._name_template_edit.text(),
                "auto_increment": self._auto_increment_cb.isChecked(),
                "next_seq": self._next_seq_spin.value(),
            }
        }
        paths, _ = build_auto_save_paths(preview_cfg, 1)
        self._save_preview_label.setText(f"预览: {paths[0]}" if paths else "")

    # ---- Tab 4: Waveform Summary --------------------------------------------

    def _build_waveform_tab(self) -> QWidget:
        from core.ai.algorithms import available, get

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(
            "选择波形摘要（右上角「导出波形摘要」按钮与 AI 波形分析共用）使用的事件"
            "检测算法；切换算法会显示该算法的常用参数，仅保存与默认不同的覆盖值。"
        )
        hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(8)
        self._wave_algo_combo = QComboBox()
        self._wave_event_algos = available("event")
        for algo_name in self._wave_event_algos:
            self._wave_algo_combo.addItem(algo_name, algo_name)
        cur = self._ai_settings.waveform_event_algo
        idx = self._wave_algo_combo.findData(cur)
        if idx < 0 and self._wave_event_algos:
            idx = 0
        if idx >= 0:
            self._wave_algo_combo.setCurrentIndex(idx)
        self._wave_algo_combo.setToolTip("kind=event 的算法自动列举；新增算法会自动出现")
        form.addRow("事件算法", self._wave_algo_combo)
        layout.addLayout(form)

        self._wave_param_form = QFormLayout()
        self._wave_param_form.setSpacing(8)
        param_box = QWidget()
        param_box.setLayout(self._wave_param_form)
        layout.addWidget(param_box)

        sep_hint = QLabel("—— 摘要分段渲染参数 ——")
        sep_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        layout.addWidget(sep_hint)

        ws_cfg = self._settings.get("waveform_summary", {})
        summary_form = QFormLayout()
        summary_form.setSpacing(8)

        self._max_stages_spin = QSpinBox()
        self._max_stages_spin.setRange(1, 500)
        self._max_stages_spin.setValue(int(ws_cfg.get("max_stages", 40)))
        self._max_stages_spin.setToolTip("每通道最多输出的阶段（段）数量，超出部分被合并截断")
        summary_form.addRow("Max Stages", self._max_stages_spin)

        self._lttb_spin = QSpinBox()
        self._lttb_spin.setRange(100, 100000)
        self._lttb_spin.setSingleStep(100)
        self._lttb_spin.setValue(int(ws_cfg.get("lttb_threshold", 3000)))
        self._lttb_spin.setToolTip("原始波形先经 LTTB 保形降采样到该点数以内再分段")
        summary_form.addRow("LTTB Threshold (points)", self._lttb_spin)

        self._pelt_max_n_spin = QSpinBox()
        self._pelt_max_n_spin.setRange(100, 100000)
        self._pelt_max_n_spin.setSingleStep(100)
        self._pelt_max_n_spin.setValue(int(ws_cfg.get("pelt_max_n", 4000)))
        self._pelt_max_n_spin.setToolTip("PELT 变点检测允许的最大输入点数（性能保护上限）")
        summary_form.addRow("PELT Max Points (points)", self._pelt_max_n_spin)

        layout.addLayout(summary_form)
        layout.addStretch(1)

        self._wave_param_editors: dict = {}
        self._wave_get_algo = get
        self._wave_algo_combo.currentIndexChanged.connect(self._rebuild_wave_params)
        self._rebuild_wave_params()
        return tab

    def _rebuild_wave_params(self):
        """按当前所选算法的 params_cls 重建参数控件，回填已保存覆盖值。"""
        while self._wave_param_form.rowCount() > 0:
            self._wave_param_form.removeRow(0)
        self._wave_param_editors = {}

        algo_name = self._wave_algo_combo.currentData()
        if not algo_name:
            return
        try:
            instance = self._wave_get_algo(algo_name)
        except KeyError:
            return
        params_cls = getattr(instance, "params_cls", None)
        if params_cls is None:
            return

        saved = self._ai_settings.waveform_algo_params.get(algo_name, {})
        for fld in dataclasses.fields(params_cls):
            default = saved.get(fld.name, fld.default)
            if fld.type in ("int", int):
                editor = QSpinBox()
                editor.setRange(0, 10_000_000)
                editor.setValue(int(default))
            else:
                editor = QDoubleSpinBox()
                editor.setDecimals(6)
                editor.setRange(0.0, 1_000_000.0)
                editor.setSingleStep(0.01)
                editor.setValue(float(default))
            editor.setToolTip(f"{fld.name}（默认 {fld.default}）")
            self._wave_param_form.addRow(fld.name, editor)
            self._wave_param_editors[fld.name] = editor

    # ---- Tab 5: About ---------------------------------------------------------

    def _build_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        try:
            from version import version_string
            app_version = version_string()
        except Exception:
            logger.debug("version 模块不可用，About 页回退显示应用名", exc_info=True)
            app_version = "KK_Lab"

        try:
            import PySide6
            pyside_version = PySide6.__version__
        except Exception:
            pyside_version = "unknown"
        from PySide6.QtCore import qVersion

        form = QFormLayout()
        form.setSpacing(6)
        form.addRow("Software", QLabel(app_version))
        form.addRow("Module", QLabel("N6705C Power Analyzer — Datalog"))
        form.addRow("Python", QLabel(platform.python_version()))
        form.addRow("PySide6 / Qt", QLabel(f"{pyside_version} / {qVersion()}"))
        layout.addLayout(form)

        config_dir = get_user_data_dir()
        layout.addWidget(QLabel("Config Directory"))
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        dir_edit = QLineEdit(config_dir)
        dir_edit.setReadOnly(True)
        open_dir_btn = QPushButton("Open Folder")
        open_dir_btn.setDefault(False)
        open_dir_btn.setAutoDefault(False)
        open_dir_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(config_dir))
        )
        dir_row.addWidget(dir_edit, 1)
        dir_row.addWidget(open_dir_btn)
        layout.addLayout(dir_row)

        n6705c_dir = get_user_data_dir("n6705c")
        files_hint = QLabel(
            "本页相关配置文件：\n"
            f"  {os.path.join(n6705c_dir, 'default_devices.json')}  —— 默认仪器列表\n"
            f"  {os.path.join(n6705c_dir, 'discovery.json')}  —— 跨网段扫描配置\n"
            f"  {os.path.join(n6705c_dir, 'datalog_settings.json')}  —— 本对话框设置\n"
            f"  {os.path.join(n6705c_dir, 'window_geometry.json')}  —— 窗口位置记忆\n"
            f"  {os.path.join(get_user_data_dir('ai'), 'config.json')}  —— AI 配置（含波形算法）"
        )
        files_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        files_hint.setWordWrap(True)
        layout.addWidget(files_hint)

        layout.addStretch(1)

        reset_row = QHBoxLayout()
        reset_row.setSpacing(8)
        reset_btn = QPushButton("RESET JSON")
        reset_btn.setStyleSheet(_RESET_BTN_STYLE)
        reset_btn.setDefault(False)
        reset_btn.setAutoDefault(False)
        reset_btn.setToolTip("删除/重置上述配置文件，还原到默认配置")
        reset_btn.clicked.connect(self._on_reset_json)
        reset_row.addWidget(reset_btn)
        reset_hint = QLabel("还原默认配置：清空仪器列表、网段、本页设置与波形算法参数。")
        reset_hint.setStyleSheet(dss.HINT_TEXT_STYLE)
        reset_hint.setWordWrap(True)
        reset_row.addWidget(reset_hint, 1)
        layout.addLayout(reset_row)
        return tab

    def _on_reset_json(self):
        n6705c_dir = get_user_data_dir("n6705c")
        ret = QMessageBox.question(
            self,
            "RESET JSON",
            "将执行以下还原操作：\n\n"
            "1. 清空默认仪器列表（default_devices.json）\n"
            "2. 清空跨网段扫描配置（discovery.json）\n"
            "3. 重置本页设置（datalog_settings.json，含 DLog 保存 / 摘要参数）\n"
            "4. 清除窗口位置记忆（window_geometry.json）\n"
            "5. 波形摘要算法恢复默认（stalta，清空参数覆盖）\n\n"
            "已连接的仪器不会断开。是否继续？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return

        errors = []

        if not save_default_devices([]):
            errors.append("default_devices.json")

        from core.n6705c.search_worker import save_extra_subnets
        if not save_extra_subnets([]):
            errors.append("discovery.json")

        for filename in (_SETTINGS_FILENAME, "window_geometry.json"):
            path = os.path.join(n6705c_dir, filename)
            try:
                if os.path.isfile(path):
                    os.remove(path)
            except OSError:
                logger.error("删除 %s 失败", path, exc_info=True)
                errors.append(filename)

        self._ai_settings.waveform_event_algo = "stalta"
        self._ai_settings.waveform_algo_params = {}
        if not self._ai_settings.save():
            errors.append("ai/config.json")

        # 内存态与控件同步回默认
        self._settings = load_datalog_app_settings()
        self._devices = []
        self._reload_instruments_table()
        self._subnet_list.clear()
        self._auto_connect_enabled_cb.setChecked(
            bool(self._settings.get("auto_connect_enabled", True))
        )
        dlog_cfg = self._settings.get("dlog_save", {})
        self._auto_save_cb.setChecked(bool(dlog_cfg.get("auto_save", False)))
        self._save_dir_edit.setText(dlog_cfg.get("save_dir", ""))
        self._name_template_edit.setText(dlog_cfg.get("name_template", "dlog_{datetime}"))
        self._auto_increment_cb.setChecked(bool(dlog_cfg.get("auto_increment", False)))
        self._next_seq_spin.setValue(int(dlog_cfg.get("next_seq", 1)))
        ws_cfg = self._settings.get("waveform_summary", {})
        self._max_stages_spin.setValue(int(ws_cfg.get("max_stages", 40)))
        self._lttb_spin.setValue(int(ws_cfg.get("lttb_threshold", 3000)))
        self._pelt_max_n_spin.setValue(int(ws_cfg.get("pelt_max_n", 4000)))
        idx = self._wave_algo_combo.findData("stalta")
        if idx >= 0:
            self._wave_algo_combo.setCurrentIndex(idx)
        self._rebuild_wave_params()
        self._refresh_save_preview()

        # 主页面联动：清空未连接的设备卡片
        apply_fn = getattr(self._ui, "apply_instrument_settings", None)
        if callable(apply_fn):
            apply_fn([], auto_connect_enabled=False)

        if errors:
            QMessageBox.warning(
                self, "RESET JSON",
                "部分文件重置失败（详见日志）：\n" + "\n".join(errors),
            )
        else:
            QMessageBox.information(
                self, "RESET JSON", "已还原到默认配置。"
            )

    # ---- 应用（OK / Apply） ---------------------------------------------------

    def _on_ok(self):
        if self._apply_all():
            self.accept()

    def _apply_all(self) -> bool:
        """把各标签页的变更落盘并联动主页面；任一校验失败返回 False 不关闭。"""
        # 1) Instruments：设备列表 + 自动连接总开关
        auto_connect_enabled = self._auto_connect_enabled_cb.isChecked()
        if not save_default_devices(self._devices):
            QMessageBox.warning(self, "保存失败", "写入 default_devices.json 失败，请查看日志。")
            return False
        apply_fn = getattr(self._ui, "apply_instrument_settings", None)
        if callable(apply_fn):
            apply_fn(list(self._devices), auto_connect_enabled=auto_connect_enabled)

        # 2) Network Scan：extra_subnets
        from core.n6705c.search_worker import save_extra_subnets
        subnets = [
            self._subnet_list.item(i).text().strip()
            for i in range(self._subnet_list.count())
            if self._subnet_list.item(i).text().strip()
        ]
        if not save_extra_subnets(subnets):
            QMessageBox.warning(self, "保存失败", "写入 discovery.json 失败，请查看日志。")
            return False

        # 3) DLog Save
        template = self._name_template_edit.text().strip() or "dlog_{datetime}"
        self._settings["auto_connect_enabled"] = auto_connect_enabled
        self._settings["dlog_save"] = {
            "auto_save": self._auto_save_cb.isChecked(),
            "save_dir": self._save_dir_edit.text().strip(),
            "name_template": template,
            "auto_increment": self._auto_increment_cb.isChecked(),
            "next_seq": self._next_seq_spin.value(),
        }

        # 4) Waveform Summary
        self._settings["waveform_summary"] = {
            "max_stages": self._max_stages_spin.value(),
            "lttb_threshold": self._lttb_spin.value(),
            "pelt_max_n": self._pelt_max_n_spin.value(),
        }
        self._apply_waveform_algo_settings()

        if not save_datalog_app_settings(self._settings):
            QMessageBox.warning(self, "保存失败", "写入 datalog_settings.json 失败，请查看日志。")
            return False
        if not self._ai_settings.save():
            QMessageBox.warning(self, "保存失败", "写入 AI 配置失败，请查看日志。")
            return False
        return True

    def _apply_waveform_algo_settings(self):
        """把波形算法标签页的选择与参数写回 AISettings（仅存非默认覆盖值）。"""
        algo_name = self._wave_algo_combo.currentData()
        if not algo_name:
            return
        self._ai_settings.waveform_event_algo = algo_name
        try:
            instance = self._wave_get_algo(algo_name)
        except KeyError:
            return
        params_cls = getattr(instance, "params_cls", None)
        if params_cls is None:
            return
        overrides = {}
        for fld in dataclasses.fields(params_cls):
            editor = self._wave_param_editors.get(fld.name)
            if editor is None:
                continue
            value = editor.value()
            if value != fld.default:
                overrides[fld.name] = value
        params_map = dict(self._ai_settings.waveform_algo_params)
        if overrides:
            params_map[algo_name] = overrides
        else:
            params_map.pop(algo_name, None)
        self._ai_settings.waveform_algo_params = params_map
