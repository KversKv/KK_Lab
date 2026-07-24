# -*- coding: utf-8 -*-
"""属性面板: 使能/模式/电压调节 + I2C 寄存器显示 + 连接信息。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QSlider, QDoubleSpinBox, QButtonGroup,
)

from chips.bes1811_pmu import align_to_step

from ui.pages.pmu.pmu_1811.constants import (
    COL_PANEL_BG, COL_CARD_BG, COL_BORDER, COL_BORDER_HOVER, COL_BORDER_SELECTED,
    COL_EMERALD, COL_EMERALD_SOFT, COL_TEXT, COL_TEXT_MUTED, COL_TEXT_DIM, FONT_MONO,
)
from ui.pages.pmu.pmu_1811.models import PmuModule
from ui.pages.pmu.pmu_1811.widgets.toggle_switch import ToggleSwitch


class PropertyPanel(QFrame):
    enable_changed = Signal(str, bool)
    mode_changed = Signal(str, str)
    voltage_changed = Signal(str, float)
    voltage_dsleep_changed = Signal(str, float)
    voltage_rc_changed = Signal(str, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("propertyPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(320)
        self.setStyleSheet(
            f"QFrame#propertyPanel {{ background:{COL_PANEL_BG};"
            f" border-left:1px solid {COL_BORDER}; }}"
            f"QLabel {{ background:transparent; border:none; color:{COL_TEXT_MUTED}; }}"
            f"QFrame#sectionCard {{ background:{COL_CARD_BG};"
            f" border:1px solid {COL_BORDER}; border-radius:10px; }}"
            f"QPushButton#modeBtn {{ background:{COL_BORDER}; color:{COL_TEXT_MUTED};"
            f" border:1px solid {COL_BORDER}; border-radius:6px; padding:6px 0;"
            f" font-size:12px; }}"
            f"QPushButton#modeBtn:checked {{ background:{COL_EMERALD_SOFT};"
            f" color:{COL_EMERALD}; border:1px solid {COL_EMERALD}; font-weight:700; }}"
            f"QPushButton#modeBtn:hover {{ border:1px solid {COL_BORDER_HOVER}; }}"
            f"QSlider::groove:horizontal {{ background:{COL_BORDER}; height:4px;"
            f" border-radius:2px; }}"
            f"QSlider::sub-page:horizontal {{ background:{COL_EMERALD};"
            f" border-radius:2px; }}"
            f"QSlider::handle:horizontal {{ background:{COL_EMERALD}; width:14px;"
            f" margin:-6px 0; border-radius:7px; }}"
        )

        self._mod: PmuModule | None = None
        self._syncing = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 头部
        self.title_lbl = QLabel("—")
        self.title_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-size:16px; font-weight:700;"
        )
        self.type_lbl = QLabel("Type: —")
        self.type_lbl.setStyleSheet(
            f"color:{COL_TEXT_MUTED}; font-family:{FONT_MONO}; font-size:11px;"
        )
        root.addWidget(self.title_lbl)
        root.addWidget(self.type_lbl)

        # Status
        root.addWidget(self._section_label("Status"))
        status_card = QFrame(self)
        status_card.setObjectName("sectionCard")
        sl = QHBoxLayout(status_card)
        sl.setContentsMargins(12, 8, 12, 8)
        self.status_name_lbl = self._muted_label("Output Enable")
        sl.addWidget(self.status_name_lbl)
        sl.addStretch(1)
        self.toggle = ToggleSwitch(self)
        self.toggle.toggled.connect(self._on_toggle)
        sl.addWidget(self.toggle)
        root.addWidget(status_card)

        # Mode + Voltage 三档: 仅 LDO/BUCK 使用, SW 隐藏
        self.ldo_buck_section = QFrame(self)
        lb_layout = QVBoxLayout(self.ldo_buck_section)
        lb_layout.setContentsMargins(0, 0, 0, 0)
        lb_layout.setSpacing(12)

        self.mode_label = self._section_label("Mode")
        lb_layout.addWidget(self.mode_label)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_row = QFrame(self)
        self.mode_layout = QHBoxLayout(self.mode_row)
        self.mode_layout.setContentsMargins(0, 0, 0, 0)
        self.mode_layout.setSpacing(6)
        lb_layout.addWidget(self.mode_row)

        # Voltage - Normal (唤醒模式)
        lb_layout.addWidget(self._section_label("Voltage - Normal (V)"))
        (
            self.spin, self.slider,
            self.min_lbl, self.max_lbl,
        ) = self._build_voltage_card(lb_layout, self._on_spin, self._on_slider)

        # Voltage - Deep Sleep (睡眠模式)
        lb_layout.addWidget(self._section_label("Voltage - Deep Sleep (V)"))
        (
            self.spin_dsleep, self.slider_dsleep,
            self.min_lbl_dsleep, self.max_lbl_dsleep,
        ) = self._build_voltage_card(lb_layout, self._on_spin_dsleep, self._on_slider_dsleep)

        # Voltage - RC (RC 模式)
        lb_layout.addWidget(self._section_label("Voltage - RC (V)"))
        (
            self.spin_rc, self.slider_rc,
            self.min_lbl_rc, self.max_lbl_rc,
        ) = self._build_voltage_card(lb_layout, self._on_spin_rc, self._on_slider_rc)
        root.addWidget(self.ldo_buck_section)

        # SW 专用: Rdson + 输入/输出节点 (LDO/BUCK 隐藏)
        self.sw_section = QFrame(self)
        sw_layout = QVBoxLayout(self.sw_section)
        sw_layout.setContentsMargins(0, 0, 0, 0)
        sw_layout.setSpacing(12)

        sw_layout.addWidget(self._section_label("Switch Info"))
        sw_card = QFrame(self)
        sw_card.setObjectName("sectionCard")
        sl2 = QVBoxLayout(sw_card)
        sl2.setContentsMargins(12, 10, 12, 10)
        sl2.setSpacing(6)
        self.rdson_lbl = QLabel("Rdson: —")
        self.rdson_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px;"
        )
        self.sw_in_lbl = QLabel("Input: —")
        self.sw_in_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px;"
        )
        self.sw_out_lbl = QLabel("Output: —")
        self.sw_out_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px;"
        )
        sl2.addWidget(self.rdson_lbl)
        sl2.addWidget(self.sw_in_lbl)
        sl2.addWidget(self.sw_out_lbl)
        sw_layout.addWidget(sw_card)
        root.addWidget(self.sw_section)
        self.sw_section.setVisible(False)

        # I2C
        root.addWidget(self._section_label("I2C Registers"))
        i2c_card = QFrame(self)
        i2c_card.setObjectName("sectionCard")
        il = QVBoxLayout(i2c_card)
        il.setContentsMargins(12, 10, 12, 10)
        il.setSpacing(6)
        self.addr_lbl = QLabel("Address: —")
        self.addr_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px;"
        )
        self.value_lbl = QLabel("Value: —")
        self.value_lbl.setStyleSheet(
            f"color:{COL_EMERALD}; font-family:{FONT_MONO}; font-size:12px;"
        )
        il.addWidget(self.addr_lbl)
        il.addWidget(self.value_lbl)
        root.addWidget(i2c_card)

        # Connection
        root.addWidget(self._section_label("Connection Info"))
        self.conn_lbl = QLabel("Input Source: —")
        self.conn_lbl.setStyleSheet(
            f"color:{COL_TEXT}; font-family:{FONT_MONO}; font-size:12px;"
        )
        root.addWidget(self.conn_lbl)

        root.addStretch(1)

        for child in self.findChildren(QFrame):
            child.setAttribute(Qt.WA_StyledBackground, True)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{COL_TEXT_DIM}; font-size:11px; font-weight:700;"
            f" letter-spacing:0.5px; text-transform:uppercase;"
        )
        return lbl

    @staticmethod
    def _muted_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{COL_TEXT_MUTED}; font-size:12px;")
        return lbl

    def _build_voltage_card(self, root_layout, spin_cb, slider_cb):
        """构造一个电压调节卡片 (Normal / Deep Sleep / RC 通用)。

        Returns:
            (spin, slider, min_lbl, max_lbl) — 调用方持有引用以便 load() 时同步状态。
        """
        v_card = QFrame(self)
        v_card.setObjectName("sectionCard")
        vl = QVBoxLayout(v_card)
        vl.setContentsMargins(12, 10, 12, 12)
        vl.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(self._muted_label("Target (V)"))
        top.addStretch(1)
        spin = QDoubleSpinBox(self)
        spin.setDecimals(3)
        spin.setSingleStep(0.05)
        spin.setMinimumWidth(90)
        spin.setAlignment(Qt.AlignRight)
        spin.valueChanged.connect(spin_cb)
        top.addWidget(spin)
        vl.addLayout(top)

        slider = QSlider(Qt.Horizontal, self)
        slider.setFocusPolicy(Qt.NoFocus)
        slider.valueChanged.connect(slider_cb)
        vl.addWidget(slider)

        rng = QHBoxLayout()
        min_lbl = self._muted_label("—")
        max_lbl = self._muted_label("—")
        max_lbl.setAlignment(Qt.AlignRight)
        rng.addWidget(min_lbl)
        rng.addStretch(1)
        rng.addWidget(max_lbl)
        vl.addLayout(rng)
        root_layout.addWidget(v_card)

        for child in v_card.findChildren(QFrame):
            child.setAttribute(Qt.WA_StyledBackground, True)
        return spin, slider, min_lbl, max_lbl

    def _rebuild_mode_buttons(self):
        for btn in list(self.mode_group.buttons()):
            self.mode_group.removeButton(btn)
            self.mode_layout.removeWidget(btn)
            btn.deleteLater()
        if self._mod is None:
            return
        for m in self._mod.modes:
            b = QPushButton(m, self)
            b.setObjectName("modeBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            if m == self._mod.mode:
                b.setChecked(True)
            b.clicked.connect(lambda _=False, mm=m: self._on_mode(mm))
            self.mode_group.addButton(b)
            self.mode_layout.addWidget(b)

    def load(self, mod: PmuModule):
        self._mod = mod
        self._syncing = True
        self.title_lbl.setText(mod.name)
        self.type_lbl.setText(f"Type: {mod.type}")
        self.type_lbl.setStyleSheet(
            f"color:{COL_TEXT_MUTED}; font-family:{FONT_MONO}; font-size:11px;"
        )
        is_sw = mod.type == "SW"
        # SW: 开关态 (闭合/开路); LDO/BUCK: 输出使能
        self.status_name_lbl.setText("Switch State" if is_sw else "Output Enable")
        self.toggle.set_checked(mod.enabled)

        # 按类型显隐: SW 无模式/电压; LDO/BUCK 无 Switch Info
        self.ldo_buck_section.setVisible(not is_sw)
        self.sw_section.setVisible(is_sw)

        if not is_sw:
            self._rebuild_mode_buttons()
            # 三套电压控件共用同一 range/step (来自 vbit 查找表, 三档位完全一致)
            self._sync_voltage_widgets(self.spin, self.slider, self.min_lbl, self.max_lbl,
                                       mod.voltage, mod)
            self._sync_voltage_widgets(self.spin_dsleep, self.slider_dsleep,
                                       self.min_lbl_dsleep, self.max_lbl_dsleep,
                                       mod.voltage_dsleep, mod)
            self._sync_voltage_widgets(self.spin_rc, self.slider_rc,
                                       self.min_lbl_rc, self.max_lbl_rc,
                                       mod.voltage_rc, mod)
        else:
            # SW 信息: Rdson / 输入节点 / 输出节点
            self.rdson_lbl.setText(f"Rdson: {mod.rdson:.4f} mΩ")
            self.sw_in_lbl.setText(f"Input:  {mod.input}")
            self.sw_out_lbl.setText(f"Output: {mod.output or '—'}")

        self.conn_lbl.setText(
            f"Input Source: {mod.input}" if not is_sw else f"VIN Node: {mod.input}"
        )
        self._syncing = False
        self._refresh_i2c()

    def _sync_voltage_widgets(self, spin, slider, min_lbl, max_lbl, voltage, mod):
        """把 PmuModule 的某档电压同步到对应的 spin/slider/label。"""
        spin.setRange(mod.min_voltage, mod.max_voltage)
        spin.setSingleStep(mod.step)
        spin.setDecimals(3)
        spin.setValue(voltage)

        smin = int(round(mod.min_voltage / mod.step))
        smax = int(round(mod.max_voltage / mod.step))
        sval = int(round(voltage / mod.step))
        slider.setRange(smin, smax)
        slider.setValue(sval)

        min_lbl.setText(f"{mod.min_voltage:.3f} V")
        max_lbl.setText(f"{mod.max_voltage:.3f} V")

    def _refresh_i2c(self):
        if self._mod is None:
            return
        rm = self._mod.reg_map
        if rm is not None:
            self.addr_lbl.setText(
                f"Ctrl: 0x{rm.pu.reg_addr:03X}  PU_Status: 0x{rm.pu_status.reg_addr:03X}"
                f"[{rm.pu_status.high_bit}:{rm.pu_status.low_bit}]"
            )
            self.value_lbl.setText(
                f"vbit_n@0x{rm.vbit_normal.reg_addr:03X}  "
                f"vbit_d@0x{rm.vbit_dsleep.reg_addr:03X}  "
                f"vbit_rc@0x{rm.vbit_rc.reg_addr:03X}"
            )
            return
        # SW 寄存器: en / en_dr 两个位域, 无 pu_status / vbit
        sw_rm = self._mod.sw_reg_map
        if sw_rm is not None:
            self.addr_lbl.setText(
                f"EN: 0x{sw_rm.en.reg_addr:03X}[{sw_rm.en.high_bit}:{sw_rm.en.low_bit}]  "
                f"EN_DR: 0x{sw_rm.en_dr.reg_addr:03X}[{sw_rm.en_dr.high_bit}:{sw_rm.en_dr.low_bit}]"
            )
            state = "闭合 (dr=1,en=1)" if self._mod.enabled else "开路 (dr=1,en=0)"
            self.value_lbl.setText(f"Domain: {sw_rm.domain}  → {state}")
        else:
            self.addr_lbl.setText("Address: — (无寄存器映射)")
            self.value_lbl.setText("Value: —")

    def _on_toggle(self, checked: bool):
        if self._mod is None or self._syncing:
            return
        self._mod.enabled = checked
        self._refresh_i2c()
        self.enable_changed.emit(self._mod.id, checked)

    def _on_mode(self, mode: str):
        if self._mod is None or self._syncing:
            return
        if mode == self._mod.mode:
            return
        self._mod.mode = mode
        self._refresh_i2c()
        self.mode_changed.emit(self._mod.id, mode)

    def _on_spin(self, v: float):
        self._handle_spin(self.spin, self.slider, v, "voltage",
                          self._mod.voltage, self.voltage_changed)

    def _on_slider(self, val: int):
        self._handle_slider(self.spin, self.slider, val, "voltage",
                            self.voltage_changed)

    def _on_spin_dsleep(self, v: float):
        self._handle_spin(self.spin_dsleep, self.slider_dsleep, v, "voltage_dsleep",
                          self._mod.voltage_dsleep, self.voltage_dsleep_changed)

    def _on_slider_dsleep(self, val: int):
        self._handle_slider(self.spin_dsleep, self.slider_dsleep, val, "voltage_dsleep",
                            self.voltage_dsleep_changed)

    def _on_spin_rc(self, v: float):
        self._handle_spin(self.spin_rc, self.slider_rc, v, "voltage_rc",
                          self._mod.voltage_rc, self.voltage_rc_changed)

    def _on_slider_rc(self, val: int):
        self._handle_slider(self.spin_rc, self.slider_rc, val, "voltage_rc",
                            self.voltage_rc_changed)

    def _handle_spin(self, spin, slider, v: float, attr: str, current: float, signal):
        """通用 spin 处理: 临近吸附 + 同步 slider + 更新 mod + emit 信号。"""
        if self._mod is None or self._syncing:
            return
        # 临近吸附: 把输入值对齐到最近 step 档位
        snapped = align_to_step(v, self._mod.step)
        if abs(snapped - v) > 1e-9 and abs(snapped - current) > 1e-9:
            self._syncing = True
            spin.setValue(snapped)
            self._syncing = False
            v = snapped
        self._syncing = True
        slider.setValue(int(round(v / self._mod.step)))
        self._syncing = False
        setattr(self._mod, attr, v)
        self._refresh_i2c()
        signal.emit(self._mod.id, v)

    def _handle_slider(self, spin, slider, val: int, attr: str, signal):
        """通用 slider 处理: 同步 spin + 更新 mod + emit 信号。"""
        if self._mod is None or self._syncing:
            return
        v = val * self._mod.step
        self._syncing = True
        spin.setValue(v)
        self._syncing = False
        setattr(self._mod, attr, v)
        self._refresh_i2c()
        signal.emit(self._mod.id, v)
