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
        sl.addWidget(self._muted_label("Output Enable"))
        sl.addStretch(1)
        self.toggle = ToggleSwitch(self)
        self.toggle.toggled.connect(self._on_toggle)
        sl.addWidget(self.toggle)
        root.addWidget(status_card)

        # Mode
        self.mode_label = self._section_label("Mode")
        root.addWidget(self.mode_label)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_row = QFrame(self)
        self.mode_layout = QHBoxLayout(self.mode_row)
        self.mode_layout.setContentsMargins(0, 0, 0, 0)
        self.mode_layout.setSpacing(6)
        root.addWidget(self.mode_row)

        # Voltage
        root.addWidget(self._section_label("Voltage (V)"))
        v_card = QFrame(self)
        v_card.setObjectName("sectionCard")
        vl = QVBoxLayout(v_card)
        vl.setContentsMargins(12, 10, 12, 12)
        vl.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(self._muted_label("Target (V)"))
        top.addStretch(1)
        self.spin = QDoubleSpinBox(self)
        self.spin.setDecimals(3)
        self.spin.setSingleStep(0.05)
        self.spin.setMinimumWidth(90)
        self.spin.setAlignment(Qt.AlignRight)
        self.spin.valueChanged.connect(self._on_spin)
        top.addWidget(self.spin)
        vl.addLayout(top)

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setFocusPolicy(Qt.NoFocus)
        self.slider.valueChanged.connect(self._on_slider)
        vl.addWidget(self.slider)

        rng = QHBoxLayout()
        self.min_lbl = self._muted_label("—")
        self.max_lbl = self._muted_label("—")
        self.max_lbl.setAlignment(Qt.AlignRight)
        rng.addWidget(self.min_lbl)
        rng.addStretch(1)
        rng.addWidget(self.max_lbl)
        vl.addLayout(rng)
        root.addWidget(v_card)

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
        self.toggle.set_checked(mod.enabled)
        self._rebuild_mode_buttons()

        self.spin.setRange(mod.min_voltage, mod.max_voltage)
        self.spin.setSingleStep(mod.step)
        self.spin.setDecimals(3)
        self.spin.setValue(mod.voltage)

        smin = int(round(mod.min_voltage / mod.step))
        smax = int(round(mod.max_voltage / mod.step))
        sval = int(round(mod.voltage / mod.step))
        self.slider.setRange(smin, smax)
        self.slider.setValue(sval)

        self.min_lbl.setText(f"{mod.min_voltage:.3f} V")
        self.max_lbl.setText(f"{mod.max_voltage:.3f} V")
        self.conn_lbl.setText(f"Input Source: {mod.input}")
        self._syncing = False
        self._refresh_i2c()

    def _refresh_i2c(self):
        if self._mod is None:
            return
        rm = self._mod.reg_map
        if rm is not None:
            self.addr_lbl.setText(
                f"Ctrl: 0x{rm.pu.reg_addr:03X}  Vbit: 0x{rm.vbit_normal.reg_addr:03X}  "
                f"PU_Status: 0x{rm.pu_status.reg_addr:03X}[{rm.pu_status.high_bit}:{rm.pu_status.low_bit}]"
            )
            self.value_lbl.setText(
                f"pu={int(self._mod.enabled)}  mode={self._mod.mode}  "
                f"vbit_n=?  (需读取)"
            )
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
        if self._mod is None or self._syncing:
            return
        # 临近吸附: 把输入值对齐到最近 step 档位
        snapped = align_to_step(v, self._mod.step)
        if abs(snapped - v) > 1e-9 and abs(snapped - self._mod.voltage) > 1e-9:
            self._syncing = True
            self.spin.setValue(snapped)
            self._syncing = False
            v = snapped
        self._syncing = True
        self.slider.setValue(int(round(v / self._mod.step)))
        self._syncing = False
        self._mod.voltage = v
        self._refresh_i2c()
        self.voltage_changed.emit(self._mod.id, v)

    def _on_slider(self, val: int):
        if self._mod is None or self._syncing:
            return
        v = val * self._mod.step
        self._syncing = True
        self.spin.setValue(v)
        self._syncing = False
        self._mod.voltage = v
        self._refresh_i2c()
        self.voltage_changed.emit(self._mod.id, v)
