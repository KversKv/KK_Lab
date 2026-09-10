# -*- coding: utf-8 -*-
"""GPADC 多通道高低温测试配置面板（ui/pages/pmu_test/gpadc_test_ui.py 内嵌）。

组成：
- IicWritesTable：IIC 写序列编辑表（前置配置使用）；
- ChannelEditDialog：单通道编辑（名称 / 扫压开关 / 切换命令文本 / 采样寄存器覆盖 / 扫压参数）；
- PreConfigDialog：前置配置编辑（写序列 + 测试后恢复原值）；
- MultiChTempPanel：左列内嵌面板（通道表 + 增删改 + 前置配置入口 + 配置保存/加载）。

通道切换配置采用 consumption_test 同款 YAML 风格命令文本（core 侧
parse_iic_command_text 解析），通道 / 写操作均为纯 dict/str（JSON 可序列化）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from core.pmu_test.gpadc.gpadc_multi_temp import (
    parse_iic_command_text,
    writes_to_command_text,
)
from ui.theme import apply_qss, dp
from ui.widgets.dark_combobox import DarkComboBox

# 写序列表列定义（表头即配置键名，含单位/进制提示）
_WRITE_COLUMNS = ["Dev (Hex)", "Reg (Hex)", "Val (Hex)", "Width (bit)",
                  "High (bit)", "Low (bit)", "Note"]

# 通道切换命令文本格式说明（与 consumption_test 配置格式一致）
_SWITCH_TEXT_HINT = (
    "每行一条命令，支持 // 注释；无前缀时使用页面全局 IIC 设备地址/位宽：\n"
    "WRITE <reg> <val>          整寄存器写，如 WRITE 0x10 0x01\n"
    "WRITE_BITS <reg> <msb> <lsb> <val>   位写，如 WRITE_BITS 0x10 3 0 0x5\n"
    "READ <reg>                 读回验证（日志输出读值）\n"
    "0x17: WRITE ...            可选设备地址前缀，覆盖页面全局"
)

# 内置默认通道：Temp / Vbat / EXT；切换寄存器值为占位，须按实际芯片修改
DEFAULT_CHANNELS = [
    {
        "enabled": True, "name": "Temp", "sweep_enabled": False,
        "switch_writes_text": "WRITE 0x10 0x00  // select Temp ch (占位)",
        "read_dev": "", "read_reg": "", "read_width": 0,
        "voltage_channel": 1, "v_min": 0.1, "v_max": 1.8, "v_step": 0.05,
    },
    {
        "enabled": True, "name": "Vbat", "sweep_enabled": True,
        "switch_writes_text": "WRITE 0x10 0x01  // select Vbat ch (占位)",
        "read_dev": "", "read_reg": "", "read_width": 0,
        "voltage_channel": 4, "v_min": 3.0, "v_max": 4.2, "v_step": 0.1,
    },
    {
        "enabled": True, "name": "EXT", "sweep_enabled": True,
        "switch_writes_text": "WRITE 0x10 0x02  // select EXT ch (占位)",
        "read_dev": "", "read_reg": "", "read_width": 0,
        "voltage_channel": 1, "v_min": 0.1, "v_max": 1.8, "v_step": 0.05,
    },
]

DEFAULT_PRE_CONFIG = {"restore_after": True, "writes": []}


def _blank(value) -> str:
    return "" if value is None else str(value)


class IicWritesTable(QWidget):
    """IIC 写序列编辑表：行 = 一条写操作，支持增删行。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.table = QTableWidget(0, len(_WRITE_COLUMNS))
        self.table.setHorizontalHeaderLabels(_WRITE_COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        for col in range(6):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.add_btn = QPushButton("Add Row")
        self.add_btn.setObjectName("tool_btn")
        self.del_btn = QPushButton("Remove Row")
        self.del_btn.setObjectName("tool_btn")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.add_btn.clicked.connect(lambda: self._append_row({}))
        self.del_btn.clicked.connect(self._remove_current_row)
        self._sync_min_height()

    def _sync_min_height(self):
        rows = max(1, min(self.table.rowCount(), 6))
        self.table.setMinimumHeight(self.table.horizontalHeader().height() + 30 * rows + 6)

    def _append_row(self, write: dict):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = [
            _blank(write.get("dev", "0x17")),
            _blank(write.get("reg", "0x00")),
            _blank(write.get("val", "0x00")),
            _blank(write.get("width", 8)),
            "" if write.get("high", -1) in (None, -1) else str(write.get("high")),
            "" if write.get("low", -1) in (None, -1) else str(write.get("low")),
            _blank(write.get("note", "")),
        ]
        for col, text in enumerate(values):
            self.table.setItem(row, col, QTableWidgetItem(text))
        self._sync_min_height()

    def _remove_current_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._sync_min_height()

    def _cell_text(self, row, col) -> str:
        item = self.table.item(row, col)
        return item.text().strip() if item is not None else ""

    def get_writes(self) -> list[dict]:
        writes = []
        for row in range(self.table.rowCount()):
            dev = self._cell_text(row, 0)
            reg = self._cell_text(row, 1)
            if not dev or not reg:
                continue
            try:
                width = int(self._cell_text(row, 3) or "8", 0)
            except ValueError:
                width = 8
            try:
                high = int(self._cell_text(row, 4), 0) if self._cell_text(row, 4) else -1
            except ValueError:
                high = -1
            try:
                low = int(self._cell_text(row, 5), 0) if self._cell_text(row, 5) else -1
            except ValueError:
                low = -1
            writes.append({
                "dev": dev, "reg": reg, "val": self._cell_text(row, 2) or "0x00",
                "width": width, "high": high, "low": low,
                "note": self._cell_text(row, 6),
            })
        return writes

    def set_writes(self, writes):
        self.table.setRowCount(0)
        for w in writes or []:
            self._append_row(w)
        self._sync_min_height()


def _channel_switch_text(channel: dict) -> str:
    """取通道切换命令文本；旧版 switch_writes dict 列表自动转换兼容。"""
    text = channel.get("switch_writes_text")
    if isinstance(text, str):
        return text
    return writes_to_command_text(channel.get("switch_writes") or [])


def _make_section(title: str, parent: QWidget) -> tuple[QFrame, QVBoxLayout]:
    """配置分组卡片：#cfgSection 底色+边框（dialog.qss），返回 (frame, 内容布局)。"""
    frame = QFrame(parent)
    frame.setObjectName("cfgSection")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(dp(12), dp(10), dp(12), dp(12))
    lay.setSpacing(dp(8))
    lbl = QLabel(title, frame)
    lbl.setObjectName("cfgSectionTitle")
    lay.addWidget(lbl)
    return frame, lay


class ChannelEditDialog(QDialog):
    """单通道编辑对话框。"""

    def __init__(self, channel: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Channel")
        self.setMinimumWidth(680)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ---- 基本设置 ----
        basic_frame, basic_lay = _make_section("基本设置", self)
        top_grid = QGridLayout()
        top_grid.setHorizontalSpacing(8)
        top_grid.setVerticalSpacing(6)

        self.enabled_check = QCheckBox("启用该通道")
        self.enabled_check.setChecked(bool(channel.get("enabled", True)))
        top_grid.addWidget(self.enabled_check, 0, 0, 1, 2)

        top_grid.addWidget(QLabel("通道名称"), 1, 0)
        self.name_edit = QLineEdit(str(channel.get("name") or ""))
        top_grid.addWidget(self.name_edit, 1, 1)

        self.sweep_check = QCheckBox("启用电压扫描（N6705C 扫压，语义同 Temp Consistency）")
        self.sweep_check.setChecked(bool(channel.get("sweep_enabled", False)))
        top_grid.addWidget(self.sweep_check, 2, 0, 1, 2)
        basic_lay.addLayout(top_grid)
        layout.addWidget(basic_frame)

        # ---- 切换命令 ----
        switch_frame, switch_lay = _make_section(
            "切换命令（采样前执行，选择该通道；格式同 Consumption Test 配置）", self)
        self.switch_text_edit = QPlainTextEdit()
        self.switch_text_edit.setPlaceholderText(_SWITCH_TEXT_HINT)
        self.switch_text_edit.setMinimumHeight(110)
        self.switch_text_edit.setPlainText(_channel_switch_text(channel))
        switch_lay.addWidget(self.switch_text_edit)
        layout.addWidget(switch_frame)

        # ---- 采样寄存器覆盖 ----
        read_frame, read_lay = _make_section(
            "采样寄存器覆盖（留空 = 页面 Data Acquisition 全局配置）", self)
        read_grid = QGridLayout()
        read_grid.setHorizontalSpacing(8)
        read_grid.setVerticalSpacing(6)
        read_grid.addWidget(QLabel("Device Address (Hex)"), 0, 0)
        read_grid.addWidget(QLabel("Raw Data Register (Hex)"), 0, 1)
        read_grid.addWidget(QLabel("Width (bit)"), 0, 2)
        self.read_dev_edit = QLineEdit(_blank(channel.get("read_dev")))
        self.read_dev_edit.setPlaceholderText("页面全局")
        self.read_reg_edit = QLineEdit(_blank(channel.get("read_reg")))
        self.read_reg_edit.setPlaceholderText("页面全局")
        self.read_width_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        self.read_width_combo.addItem("页面全局", 0)
        for w in (8, 10, 32):
            self.read_width_combo.addItem(f"{w}-bit", w)
        idx = self.read_width_combo.findData(int(channel.get("read_width") or 0))
        self.read_width_combo.setCurrentIndex(max(0, idx))
        read_grid.addWidget(self.read_dev_edit, 1, 0)
        read_grid.addWidget(self.read_reg_edit, 1, 1)
        read_grid.addWidget(self.read_width_combo, 1, 2)
        read_lay.addLayout(read_grid)
        layout.addWidget(read_frame)

        # ---- 扫压参数 ----
        self.sweep_frame, sweep_lay = _make_section("电压扫描参数（N6705C）", self)
        sweep_grid = QGridLayout()
        sweep_grid.setHorizontalSpacing(8)
        sweep_grid.setVerticalSpacing(6)
        sweep_grid.addWidget(QLabel("N6705C Channel"), 0, 0)
        sweep_grid.addWidget(QLabel("V Min (V)"), 0, 1)
        sweep_grid.addWidget(QLabel("V Max (V)"), 0, 2)
        sweep_grid.addWidget(QLabel("V Step (V)"), 0, 3)
        self.voltage_channel_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        for ch in range(1, 5):
            self.voltage_channel_combo.addItem(f"Channel {ch}", ch)
        idx = self.voltage_channel_combo.findData(int(channel.get("voltage_channel") or 1))
        self.voltage_channel_combo.setCurrentIndex(max(0, idx))
        self.v_min_spin = QDoubleSpinBox()
        self.v_min_spin.setRange(0.0, 24.0)
        self.v_min_spin.setDecimals(3)
        self.v_min_spin.setSingleStep(0.1)
        self.v_min_spin.setValue(float(channel.get("v_min", 0.1)))
        self.v_max_spin = QDoubleSpinBox()
        self.v_max_spin.setRange(0.0, 24.0)
        self.v_max_spin.setDecimals(3)
        self.v_max_spin.setSingleStep(0.1)
        self.v_max_spin.setValue(float(channel.get("v_max", 1.8)))
        self.v_step_spin = QDoubleSpinBox()
        self.v_step_spin.setRange(0.001, 5.0)
        self.v_step_spin.setDecimals(3)
        self.v_step_spin.setSingleStep(0.01)
        self.v_step_spin.setValue(float(channel.get("v_step", 0.05)))
        sweep_grid.addWidget(self.voltage_channel_combo, 1, 0)
        sweep_grid.addWidget(self.v_min_spin, 1, 1)
        sweep_grid.addWidget(self.v_max_spin, 1, 2)
        sweep_grid.addWidget(self.v_step_spin, 1, 3)
        sweep_lay.addLayout(sweep_grid)
        layout.addWidget(self.sweep_frame)

        self.sweep_frame.setVisible(self.sweep_check.isChecked())
        self.sweep_check.toggled.connect(self.sweep_frame.setVisible)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
        ok_btn.setText("OK")
        cancel_btn.setText("Cancel")
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        apply_qss(self, "dialog")

    def get_channel(self) -> dict:
        return {
            "enabled": self.enabled_check.isChecked(),
            "name": self.name_edit.text().strip() or "CH",
            "sweep_enabled": self.sweep_check.isChecked(),
            "switch_writes_text": self.switch_text_edit.toPlainText().strip(),
            "read_dev": self.read_dev_edit.text().strip(),
            "read_reg": self.read_reg_edit.text().strip(),
            "read_width": int(self.read_width_combo.currentData() or 0),
            "voltage_channel": int(self.voltage_channel_combo.currentData() or 1),
            "v_min": self.v_min_spin.value(),
            "v_max": self.v_max_spin.value(),
            "v_step": self.v_step_spin.value(),
        }


class PreConfigDialog(QDialog):
    """前置配置编辑对话框：测试开始前执行一次的 IIC 写序列。"""

    def __init__(self, pre_config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Pre-Config")
        self.setMinimumWidth(680)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hint = QLabel("测试开始前按顺序执行一次；勾选恢复时，写入前先读原值，测试结束（含中止）后写回。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.restore_check = QCheckBox("测试结束后恢复原值")
        self.restore_check.setChecked(bool(pre_config.get("restore_after", True)))
        layout.addWidget(self.restore_check)

        self.writes_table = IicWritesTable(self)
        self.writes_table.set_writes(pre_config.get("writes") or [])
        layout.addWidget(self.writes_table)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
        ok_btn.setText("OK")
        cancel_btn.setText("Cancel")
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        apply_qss(self, "dialog")

    def get_pre_config(self) -> dict:
        return {
            "restore_after": self.restore_check.isChecked(),
            "writes": self.writes_table.get_writes(),
        }


class MultiChTempPanel(QFrame):
    """多通道高低温测试配置面板（内嵌 GPADC 页左列）。"""

    save_requested = Signal()
    load_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panel")

        self._channels: list[dict] = [dict(ch) for ch in DEFAULT_CHANNELS]
        self._pre_config: dict = dict(DEFAULT_PRE_CONFIG)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QLabel("Multi-Channel Config")
        title.setObjectName("section_title")
        title.setStyleSheet("border: none;")
        layout.addWidget(title)

        hint = QLabel("默认通道的切换寄存器为占位值，请按实际芯片修改；双击行编辑通道。")
        hint.setWordWrap(True)
        hint.setObjectName("muted_label")
        layout.addWidget(hint)

        self.ch_table = QTableWidget(0, 3)
        self.ch_table.setHorizontalHeaderLabels(["通道", "扫压", "切换写"])
        self.ch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ch_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.ch_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.ch_table.verticalHeader().setVisible(False)
        self.ch_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ch_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.ch_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.ch_table)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.add_btn = QPushButton("Add")
        self.add_btn.setObjectName("tool_btn")
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setObjectName("tool_btn")
        self.del_btn = QPushButton("Del")
        self.del_btn.setObjectName("tool_btn")
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.edit_btn)
        btn_row.addWidget(self.del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        pre_row = QHBoxLayout()
        pre_row.setSpacing(6)
        self.pre_summary_label = QLabel()
        self.pre_summary_label.setObjectName("muted_label")
        self.pre_edit_btn = QPushButton("Pre-Config")
        self.pre_edit_btn.setObjectName("tool_btn")
        self.pre_edit_btn.setToolTip("编辑测试开始前执行的前置配置 IIC 写序列")
        pre_row.addWidget(self.pre_summary_label, 1)
        pre_row.addWidget(self.pre_edit_btn)
        layout.addLayout(pre_row)

        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(6)
        self.save_cfg_btn = QPushButton("Save Config")
        self.save_cfg_btn.setObjectName("tool_btn")
        self.load_cfg_btn = QPushButton("Load Config")
        self.load_cfg_btn.setObjectName("tool_btn")
        cfg_row.addWidget(self.save_cfg_btn)
        cfg_row.addWidget(self.load_cfg_btn)
        cfg_row.addStretch()
        layout.addLayout(cfg_row)

        self.add_btn.clicked.connect(self._on_add_channel)
        self.edit_btn.clicked.connect(self._on_edit_channel)
        self.del_btn.clicked.connect(self._on_del_channel)
        self.ch_table.cellDoubleClicked.connect(lambda *_: self._on_edit_channel())
        self.ch_table.itemChanged.connect(self._on_item_changed)
        self.pre_edit_btn.clicked.connect(self._on_edit_pre_config)
        self.save_cfg_btn.clicked.connect(self.save_requested.emit)
        self.load_cfg_btn.clicked.connect(self.load_requested.emit)

        self._rebuild_table()
        self._refresh_pre_summary()

    # ---------------- 通道表 ----------------
    def _rebuild_table(self):
        self.ch_table.blockSignals(True)
        self.ch_table.setRowCount(0)
        for ch in self._channels:
            row = self.ch_table.rowCount()
            self.ch_table.insertRow(row)
            name_item = QTableWidgetItem(str(ch.get("name") or "CH"))
            name_item.setFlags(name_item.flags() | Qt.ItemIsUserCheckable)
            name_item.setCheckState(Qt.Checked if ch.get("enabled", True) else Qt.Unchecked)
            self.ch_table.setItem(row, 0, name_item)
            self.ch_table.setItem(row, 1, QTableWidgetItem("Yes" if ch.get("sweep_enabled") else "No"))
            n_cmds = len(parse_iic_command_text(_channel_switch_text(ch)))
            self.ch_table.setItem(row, 2, QTableWidgetItem(str(n_cmds)))
        self.ch_table.blockSignals(False)
        rows = max(1, min(len(self._channels), 5))
        self.ch_table.setMinimumHeight(
            self.ch_table.horizontalHeader().height() + 30 * rows + 6
        )

    def _on_item_changed(self, item):
        if item is None or item.column() != 0:
            return
        row = item.row()
        if 0 <= row < len(self._channels):
            self._channels[row]["enabled"] = item.checkState() == Qt.Checked

    def _current_row(self) -> int:
        return self.ch_table.currentRow()

    def _on_add_channel(self):
        new_ch = {
            "enabled": True, "name": f"CH{len(self._channels) + 1}", "sweep_enabled": False,
            "switch_writes_text": "", "read_dev": "", "read_reg": "", "read_width": 0,
            "voltage_channel": 1, "v_min": 0.1, "v_max": 1.8, "v_step": 0.05,
        }
        dlg = ChannelEditDialog(new_ch, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._channels.append(dlg.get_channel())
            self._rebuild_table()

    def _on_edit_channel(self):
        row = self._current_row()
        if not (0 <= row < len(self._channels)):
            return
        dlg = ChannelEditDialog(dict(self._channels[row]), parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._channels[row] = dlg.get_channel()
            self._rebuild_table()

    def _on_del_channel(self):
        row = self._current_row()
        if 0 <= row < len(self._channels):
            self._channels.pop(row)
            self._rebuild_table()

    # ---------------- 前置配置 ----------------
    def _on_edit_pre_config(self):
        dlg = PreConfigDialog(dict(self._pre_config), parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._pre_config = dlg.get_pre_config()
            self._refresh_pre_summary()

    def _refresh_pre_summary(self):
        n = len(self._pre_config.get("writes") or [])
        restore = "恢复" if self._pre_config.get("restore_after", True) else "不恢复"
        self.pre_summary_label.setText(f"Pre-Config: {n} writes ({restore})")

    # ---------------- 对外接口 ----------------
    def get_channels(self) -> list[dict]:
        return [dict(ch) for ch in self._channels]

    def set_channels(self, channels):
        if isinstance(channels, list) and channels:
            self._channels = [dict(ch) for ch in channels if isinstance(ch, dict)]
            self._rebuild_table()

    def get_pre_config(self) -> dict:
        return dict(self._pre_config)

    def set_pre_config(self, pre_config):
        if isinstance(pre_config, dict):
            self._pre_config = {
                "restore_after": bool(pre_config.get("restore_after", True)),
                "writes": list(pre_config.get("writes") or []),
            }
            self._refresh_pre_summary()
