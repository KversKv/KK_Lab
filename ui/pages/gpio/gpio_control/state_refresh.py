# -*- coding: utf-8 -*-
"""GPIO 页会话影子状态派生与视图刷新 Mixin。"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
)
from PySide6.QtCore import Qt

from core.gpio.gpio_config import (
    mode_label, MODE_OUT_HIGH, MODE_OUT_LOW, MODE_IN_FLOAT,
    MODE_IN_PULL_UP, MODE_IN_PULL_DOWN, OP_BITS, OFFSET_OUT_SET,
    OFFSET_DIR_SET, OFFSET_OUT_CLR, OFFSET_DIR_CLR,
    OFFSET_IN_READ, PINS_PER_GROUP, GROUPS_PER_BANK
)

from ui.pages.gpio.gpio_control.utils import (
    _icon, _fmt32, _popcount, _repolish
)
from ui.pages.gpio.gpio_control.pin_card import _PinCard

class StateRefreshMixin:
    """会话影子派生状态 + 视图刷新（Matrix/RegMap/Inspector/统计）。"""

    def _ready(self):
        return self._cfg is not None and self._dev_addr is not None

    def _meta(self, group, pin):
        return self._pin_meta.setdefault((group, pin), {"alias": ""})

    def _alias(self, group, pin):
        return self._pin_meta.get((group, pin), {}).get("alias") or ""

    def _dir_bit(self, bank_idx, bit):
        return (self._dir_shadow.get(bank_idx, 0) >> bit) & 1

    def _out_bit(self, bank_idx, bit):
        return (self._out_shadow.get(bank_idx, 0) >> bit) & 1

    def _pull_state(self, group, bit):
        """0=Hi-Z 1=PU 2=PD（由 PU/PD 影子寄存器推导）。"""
        if self._cfg is None:
            return 0
        bank_idx = self._cfg.bank_index(group)
        pu_addr = self._cfg.pull_up_addr(group)
        pd_addr = self._cfg.pull_down_addr(group)
        pu = (self._reg_shadow.get(pu_addr, 0) >> bit) & 1 if pu_addr is not None else 0
        pd = (self._reg_shadow.get(pd_addr, 0) >> bit) & 1 if pd_addr is not None else 0
        if pu and not pd:
            return 1
        if pd and not pu:
            return 2
        return 0

    def _drv_field_value(self, group, pin):
        field_ = self._cfg.drv_field(group, pin) if self._cfg else None
        if field_ is None:
            return None
        addr, high, low = field_
        mask = (1 << (high - low + 1)) - 1
        return (self._reg_shadow.get(addr, 0) >> low) & mask

    def _drv_ohm_text(self, level):
        """该档位输出阻抗取整文本（"1463/1472 Ω"），无表返回 ""。"""
        hh, ll = self._cfg.drv_ohm(level)
        if hh is None or ll is None:
            return ""
        return "{0}/{1} Ω".format(round(hh), round(ll))

    def _drv_level_text(self, val):
        if val is None:
            return "Lv --"
        ohm = self._drv_ohm_text(val)
        return "Lv{0} · {1}".format(val, ohm) if ohm else "Lv{0}".format(val)

    def _func_sel_value(self, group, pin):
        """该脚 func sel 当前值（影子推导）；未配置返回 None。"""
        field_ = self._cfg.func_sel_field(group, pin) if self._cfg else None
        if field_ is None:
            return None
        addr, high, low = field_
        mask = (1 << (high - low + 1)) - 1
        return (self._reg_shadow.get(addr, 0) >> low) & mask

    def _func_display(self, group, pin):
        """卡片 GPIO 名后的当前功能名；未配置返回 ""，未命名值回退 0xN。"""
        val = self._func_sel_value(group, pin)
        if val is None:
            return ""
        return self._cfg.func_name(group, pin, val) or "0x{0:X}".format(val)

    def _func_sel_pin_actions(self, group, pin):
        """单脚控制前置：func sel 未选 GPIO 功能时生成配置动作（否则空）。"""
        field_ = self._cfg.func_sel_field(group, pin) if self._cfg else None
        if field_ is None:
            return []
        addr, high, low = field_
        if self._func_sel_value(group, pin) == self._cfg.func_sel_gpio_value:
            return []
        return [(OP_BITS, addr, self._cfg.func_sel_gpio_value, high, low)]

    def _func_sel_mask_actions(self, bank_idx, bank_mask):
        """bank 位掩码涉及脚的 func sel 配置动作，按 group 合并整寄存器写
        （未涉及字段取影子值保持；影子已为 GPIO 功能时跳过该 group）。"""
        if self._cfg is None or not self._cfg.func_sel_supported:
            return []
        actions = []
        bits = self._cfg.func_sel_bits_per_gpio
        fmask = (1 << bits) - 1
        want = self._cfg.func_sel_gpio_value & fmask
        g0 = bank_idx * GROUPS_PER_BANK
        for g in range(g0, g0 + self._cfg.bank_group_count(bank_idx)):
            field_ = self._cfg.func_sel_field(g, 0)
            if field_ is None:
                continue
            pins = (bank_mask >> ((g - g0) * PINS_PER_GROUP)) & 0xFF
            if not pins:
                continue
            addr = field_[0]
            cur = self._reg_shadow.get(addr, 0)
            new = cur
            for p in range(PINS_PER_GROUP):
                if (pins >> p) & 1:
                    new = (new & ~(fmask << (p * bits))) | (want << (p * bits))
            if new != cur:
                actions.append((OP_BITS, addr, new, 31, 0))
        return actions

    def _in_bit(self, bank_idx, bit):
        val = self._in_value.get(bank_idx)
        if val is None:
            return None
        return (val >> bit) & 1

    def _bank_pin_mask(self, bank_idx):
        """该 bank 有效引脚位掩码（高位 group 不存在时仅低位有效）。"""
        return (1 << (self._cfg.bank_group_count(bank_idx)
                      * PINS_PER_GROUP)) - 1

    def _pin_mode(self, group, pin):
        """由影子寄存器推导工作模式（用于 label / Inspector）。"""
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        if self._dir_bit(bank_idx, bit):
            return MODE_OUT_HIGH if self._out_bit(bank_idx, bit) else MODE_OUT_LOW
        pull = self._pull_state(group, bit)
        if pull == 1:
            return MODE_IN_PULL_UP
        if pull == 2:
            return MODE_IN_PULL_DOWN
        return MODE_IN_FLOAT

    def _reset_session_state(self):
        self._selected = None
        self._selected_pins = []
        self._pin_meta = {}
        self._dir_shadow = {i: 0 for i in range(len(self._cfg.banks))}
        self._out_shadow = {i: 0 for i in range(len(self._cfg.banks))}
        self._reg_shadow = {}
        self._in_value = {i: None for i in range(len(self._cfg.banks))}
        self._export_items = self._load_export_items()
        self._refresh_export_manager()

    # ================================================================ 刷新

    def _refresh_all_views(self):
        self._rebuild_bank_buttons()
        self._rebuild_matrix()
        self._rebuild_regmap()
        self._refresh_addr_bar()
        self._refresh_stats()
        self._refresh_inspector()
        self._refresh_notes()
        self._refresh_export_manager()
        self._update_op_enabled()

    def _refresh_after_hw(self):
        """硬件状态变化后的轻量刷新（不重建控件）。"""
        for group, pin in list(self._pin_cards.keys()):
            self._refresh_pin_card(group, pin)
        self._refresh_reg_cards()
        self._refresh_stats()
        self._refresh_inspector()

    def _rebuild_bank_buttons(self):
        for btn in self._bank_buttons:
            self._bank_group.removeButton(btn)
            btn.deleteLater()
        self._bank_buttons = []
        while self._bank_box.count():
            item = self._bank_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        count = len(self._cfg.banks) if self._cfg else 0
        if count == 0:
            lbl = QLabel("--")
            lbl.setObjectName("gpioDim")
            self._bank_box.addWidget(lbl)
            return
        if self._cur_bank >= count:
            self._cur_bank = 0
        for i in range(count):
            bank = self._cfg.banks[i]
            g0 = i * GROUPS_PER_BANK
            g1 = g0 + bank.groups - 1
            btn = QPushButton(str(i))
            btn.setObjectName("gpioBankBtn")
            btn.setCheckable(True)
            btn.setToolTip("Bank {0} · {1} · GPIO_Group{2}~{3} · base {4}".format(
                i, bank.name, g0, g1, _fmt32(bank.base)))
            self._bank_group.addButton(btn, i)
            self._bank_box.addWidget(btn)
            self._bank_buttons.append(btn)
        self._bank_buttons[self._cur_bank].setChecked(True)

    def _rebuild_matrix(self):
        for col in (self._matrix_col_l, self._matrix_col_r):
            while col.count():
                item = col.takeAt(0)
                if item.widget() is not None:
                    item.widget().deleteLater()
        self._pin_cards = {}
        if self._cfg is None:
            ph = QLabel("Run i2c.bes_chip_check() or load a DUT Profile first")
            ph.setObjectName("gpioStatus")
            ph.setAlignment(Qt.AlignCenter)
            self._matrix_col_l.addWidget(ph)
            self._matrix_col_l.addStretch(1)
            self._matrix_col_r.addStretch(1)
            return
        base_group = self._cur_bank * GROUPS_PER_BANK
        n_bits = self._cfg.bank_group_count(self._cur_bank) * PINS_PER_GROUP
        for bit in range(n_bits - 1, -1, -1):
            group = base_group + bit // PINS_PER_GROUP
            pin = bit % PINS_PER_GROUP
            card = _PinCard(
                group, pin,
                on_select=self._on_pin_clicked,
                on_dir=self._on_card_dir,
                on_level=self._on_card_level,
                on_pull=self._on_card_pull,
                on_menu=self._on_pin_context_menu)
            # 两列排布：左列 BIT31~16 自上往下，右列 BIT15~0 自上往下
            # 行距 0，相邻行以 alt 斑马纹背景区分
            if bit >= 16:
                row, col = 31 - bit, self._matrix_col_l
            else:
                row, col = 15 - bit, self._matrix_col_r
            card.setProperty("alt", str(row % 2))
            col.addWidget(card)
            self._pin_cards[(group, pin)] = card
            self._refresh_pin_card(group, pin)

    def _refresh_pin_card(self, group, pin):
        card = self._pin_cards.get((group, pin))
        if card is None or self._cfg is None:
            return
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        linear = self._cfg.linear_index(group, pin)
        alias = self._alias(group, pin)
        func = self._func_display(group, pin)
        card.name_label.setText(self._cfg.gpio_name(group, pin))
        card.bit_label.setText("BIT{0:02d}".format(bit))
        card.alias_label.setText(" · ".join(t for t in (func, alias) if t))
        card.setToolTip("{0} · {1} BIT{2:02d} · Global #{3}{4}".format(
            self._cfg.gpio_name(group, pin), self._cfg.banks[bank_idx].name,
            bit, linear,
            " · Function: {0}".format(func) if func else ""))

        is_out = bool(self._dir_bit(bank_idx, bit))
        card.dir_btn.setText("OUT" if is_out else "IN")
        card.dir_btn.setProperty("cur", "out" if is_out else "in")
        _repolish(card.dir_btn)

        if is_out:
            lvl = self._out_bit(bank_idx, bit)
            card.level_btn.setText("H" if lvl else "L")
            card.level_btn.setProperty("cur", "h" if lvl else "l")
        else:
            in_lvl = self._in_bit(bank_idx, bit)
            if in_lvl is not None:
                card.level_btn.setText(str(in_lvl))
                card.level_btn.setProperty("cur", "h" if in_lvl else "l")
            else:
                card.level_btn.setText("-")
                card.level_btn.setProperty("cur", "")
        # 输出电平与方向联动：INPUT 时电平按钮禁用置灰
        card.level_btn.setEnabled(is_out)
        _repolish(card.level_btn)

        pull_ok = self._cfg.pull_supported(group)
        pull = self._pull_state(group, bit)
        card.pull_btn.setText({0: "Z", 1: "PU", 2: "PD"}[pull])
        card.pull_btn.setProperty("cur", {0: "", 1: "pu", 2: "pd"}[pull])
        card.pull_btn.setEnabled(pull_ok)
        card.pull_btn.setToolTip(
            "Cycle pull: Hi-Z -> PU -> PD" if pull_ok
            else "Pull addresses not configured in JSON for this Bank "
                 "(pull_up/pull_down_bases)")
        _repolish(card.pull_btn)

        if is_out:
            lvl_prop = "h" if self._out_bit(bank_idx, bit) else "l"
        else:
            in_lvl = self._in_bit(bank_idx, bit)
            lvl_prop = {0: "l", 1: "h"}.get(in_lvl, "x")
        if card.property("lvl") != lvl_prop:
            card.setProperty("lvl", lvl_prop)
            _repolish(card)
        card.setProperty("sel", "1" if (group, pin) in self._selected_pins else "0")
        _repolish(card)

    def _rebuild_regmap(self):
        while self._regmap_grid.count():
            item = self._regmap_grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._reg_cards = []
        if self._cfg is None:
            ph = QLabel("Load a DUT config to show the register map")
            ph.setObjectName("gpioStatus")
            ph.setAlignment(Qt.AlignCenter)
            self._regmap_grid.addWidget(ph, 0, 0)
            return
        bank = self._cfg.banks[self._cur_bank]
        specs = [
            ("val_set", bank.base + OFFSET_OUT_SET, "VAL_SET",
             "Output set: write 1 -> pin outputs HIGH", False),
            ("dir_set", bank.base + OFFSET_DIR_SET, "DIR_SET",
             "Direction set: write 1 -> pin becomes OUTPUT", False),
            ("val_clr", bank.base + OFFSET_OUT_CLR, "VAL_CLR",
             "Output clear: write 1 -> pin outputs LOW", False),
            ("dir_clr", bank.base + OFFSET_DIR_CLR, "DIR_CLR",
             "Direction clear: write 1 -> pin becomes INPUT", False),
            ("val_in", bank.base + OFFSET_IN_READ, "VAL_IN",
             "Input level read (click card to refresh)", True),
        ]
        if self._cfg.drv_supported:
            for addr, first in self._cfg.drv_registers(self._cur_bank):
                specs.append(("drv", addr,
                              "DRV_GPIO{0}0".format(first // PINS_PER_GROUP),
                              "Drive strength {0}bit/pin "
                              "(click bits to flip level)".format(
                                  self._cfg.drv_bits_per_gpio), True))
        if self._cfg.func_sel_supported:
            g0 = self._cur_bank * GROUPS_PER_BANK
            for g in range(g0, g0 + self._cfg.bank_group_count(self._cur_bank)):
                field_ = self._cfg.func_sel_field(g, 0)
                if field_ is None:
                    continue
                specs.append(("fsel", field_[0], "FSEL_GPIO{0}0".format(g),
                              "Function mux select: 0x{0:X}=GPIO "
                              "(auto-written before control)".format(
                                  self._cfg.func_sel_gpio_value), True))
        pu_addr = self._cfg.pull_up_bases[self._cur_bank] \
            if self._cur_bank < len(self._cfg.pull_up_bases) else None
        pd_addr = self._cfg.pull_down_bases[self._cur_bank] \
            if self._cur_bank < len(self._cfg.pull_down_bases) else None
        specs.append(("pu", pu_addr, "PU_REG",
                      "Pull-up enable (1bit/pin, OP_BITS bitfield write)", True))
        specs.append(("pd", pd_addr, "PD_REG",
                      "Pull-down enable (1bit/pin, OP_BITS bitfield write)", True))

        for i, (kind, addr, name, hint, readable) in enumerate(specs):
            card = self._make_reg_card(kind, addr, name, hint, readable)
            self._regmap_grid.addWidget(card["frame"], i // 2, i % 2)
            self._reg_cards.append(card)
        self._refresh_reg_cards()

    def _make_reg_card(self, kind, addr, name, hint, readable):
        frame = QFrame()
        frame.setObjectName("regCard")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(10, 6, 10, 8)
        lay.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(6)
        n = QLabel(name)
        n.setObjectName("regCardName")
        head.addWidget(n)
        a = QLabel(_fmt32(addr) if addr is not None else "TBD")
        a.setObjectName("regCardAddr")
        head.addWidget(a)
        head.addStretch(1)
        v = QLabel("--")
        v.setObjectName("regCardVal")
        head.addWidget(v)
        if readable and addr is not None:
            r = QPushButton("R")
            r.setObjectName("gpioCellBtn")
            r.setToolTip("Read back this register")
            r.clicked.connect(lambda _=False, k=kind, ad=addr: self._on_reg_read(k, ad))
            head.addWidget(r)
        lay.addLayout(head)

        h = QLabel(hint if addr is not None
                   else "Address TBD (not configured in JSON), write disabled")
        h.setObjectName("regCardHint")
        lay.addWidget(h)

        bit_row = QHBoxLayout()
        bit_row.setContentsMargins(0, 0, 0, 0)
        bit_row.setSpacing(2)
        bit_row.addStretch(1)
        bits = []
        for bit in range(31, -1, -1):
            b = QPushButton("0")
            b.setObjectName("regBit")
            b.setProperty("on", "0")
            b.setToolTip("Bit {0}".format(bit))
            if readable:
                b.setProperty("rd", "1")
            if addr is None:
                b.setEnabled(False)
            else:
                b.clicked.connect(
                    lambda _=False, k=kind, ad=addr, bi=bit: self._on_reg_bit(k, ad, bi))
            bit_row.addWidget(b)
            bits.append((bit, b))
        bit_row.addStretch(1)
        lay.addLayout(bit_row)
        return {"frame": frame, "kind": kind, "addr": addr, "val": v, "bits": bits}

    def _reg_card_value(self, kind, addr):
        if addr is None or self._cfg is None:
            return None
        bank = self._cfg.banks[self._cur_bank]
        if kind in ("val_set", "val_clr"):
            return self._out_shadow.get(self._cur_bank, 0)
        if kind in ("dir_set", "dir_clr"):
            return self._dir_shadow.get(self._cur_bank, 0)
        if kind == "val_in":
            return self._in_value.get(self._cur_bank)
        return self._reg_shadow.get(addr, 0)

    def _refresh_reg_cards(self):
        for card in self._reg_cards:
            value = self._reg_card_value(card["kind"], card["addr"])
            card["val"].setText("--" if value is None else _fmt32(value))
            shown = value or 0
            for bit, btn in card["bits"]:
                on = (shown >> bit) & 1
                if btn.text() != str(on):
                    btn.setText(str(on))
                if btn.property("on") != str(on):
                    btn.setProperty("on", str(on))
                    _repolish(btn)

    def _refresh_addr_bar(self):
        if self._cfg is None:
            self.addr_label.setText("Base --")
            self.bank_label.setText("Bank --")
            self.dut_sub.setText("DUT: --")
            return
        bank = self._cfg.banks[self._cur_bank]
        g0 = self._cur_bank * GROUPS_PER_BANK
        self.addr_label.setText("Base {0}".format(_fmt32(bank.base)))
        self.bank_label.setText("Bank{0} (GPIO_Group{1}~{2})".format(
            self._cur_bank, g0, g0 + bank.groups - 1))
        mode = ("dev 0x{0:02X}".format(self._dev_addr)
                if self._dev_addr is not None else "--")
        self.dut_sub.setText("DUT: {0} · {1}".format(
            self._cfg.chip.upper(), mode))

    def _refresh_stats(self):
        vals = {k: "-" for k in self._stat_vals}
        if self._cfg is not None:
            b = self._cur_bank
            n_pins = self._cfg.bank_group_count(b) * PINS_PER_GROUP
            dir_v = self._dir_shadow.get(b, 0)
            out_n = _popcount(dir_v)
            vals["out"] = str(out_n)
            vals["in"] = str(n_pins - out_n)
            in_v = self._in_value.get(b)
            if in_v is not None:
                high_n = _popcount(in_v & self._bank_pin_mask(b))
                vals["high"] = str(high_n)
                vals["low"] = str(n_pins - high_n)
            pu_addr = self._cfg.pull_up_bases[b] \
                if b < len(self._cfg.pull_up_bases) else None
            pd_addr = self._cfg.pull_down_bases[b] \
                if b < len(self._cfg.pull_down_bases) else None
            if pu_addr is not None:
                vals["pu"] = str(_popcount(self._reg_shadow.get(pu_addr, 0)))
            if pd_addr is not None:
                vals["pd"] = str(_popcount(self._reg_shadow.get(pd_addr, 0)))
        for k, v in self._stat_vals.items():
            v.setText(vals[k])

    def _refresh_inspector(self):
        pins = self._selected_pins
        sel = pins[0] if pins else None
        has = sel is not None and self._cfg is not None
        multi = has and len(pins) > 1
        ready = self._ready()
        self._insp_single_box.setVisible(has and not multi)
        self._insp_state_box.setVisible(has and not multi)
        self._insp_multi_box.setVisible(multi)
        if not has:
            self.insp_name.setText("GPIO--")
            self.insp_info.setText("No pin selected")
            self.insp_mask.setText("Mask --")
            self.alias_edit.setText("")
            self.insp_big_state.setText("LOGIC --")
            self.insp_big_state.setProperty("lvl", "")
            _repolish(self.insp_big_state)
        elif multi:
            self._refresh_multi_rows()
        else:
            group, pin = sel
            bank_idx = self._cfg.bank_index(group)
            bit = self._cfg.bit_in_bank(group, pin)
            linear = self._cfg.linear_index(group, pin)
            is_out = bool(self._dir_bit(bank_idx, bit))
            self.insp_name.setText(self._cfg.gpio_name(group, pin))
            self.insp_info.setText("{0} BIT{1:02d} · Group{2} Pin{3} · Global #{4} · {5}".format(
                self._cfg.banks[bank_idx].name, bit,
                group, pin, linear, mode_label(self._pin_mode(group, pin))))
            if self.alias_edit.text() != self._alias(group, pin) \
                    and not self.alias_edit.hasFocus():
                self.alias_edit.setText(self._alias(group, pin))

            self.insp_dir_out.setProperty("cur", "1" if is_out else "0")
            self.insp_dir_in.setProperty("cur", "0" if is_out else "1")
            _repolish(self.insp_dir_out)
            _repolish(self.insp_dir_in)
            lvl = self._out_bit(bank_idx, bit)
            self.insp_lvl_h.setProperty("cur", "1" if (is_out and lvl) else "0")
            self.insp_lvl_l.setProperty("cur", "1" if (is_out and not lvl) else "0")
            _repolish(self.insp_lvl_h)
            _repolish(self.insp_lvl_l)

            pull = self._pull_state(group, bit)
            self.insp_pull_hiz.setProperty("cur", "1" if pull == 0 else "0")
            self.insp_pull_pu.setProperty("cur", "pu" if pull == 1 else "0")
            self.insp_pull_pd.setProperty("cur", "pd" if pull == 2 else "0")
            for b in (self.insp_pull_hiz, self.insp_pull_pu, self.insp_pull_pd):
                _repolish(b)
            if self._cfg.pull_up_ohm is not None \
                    and self._cfg.pull_down_ohm is not None:
                self.insp_pull_key.setText(
                    "Pull Tri-State (PU≈{0} Ω / PD≈{1} Ω)".format(
                        round(self._cfg.pull_up_ohm),
                        round(self._cfg.pull_down_ohm)))
            else:
                self.insp_pull_key.setText(
                    "Pull Tri-State (PU/PD are RW registers, bitfield write)")

            field_ = self._cfg.drv_field(group, pin)
            if field_ is not None:
                val = self._drv_field_value(group, pin)
                self.insp_drv_val.setText(self._drv_level_text(val))
                self.insp_drv_key.setText("Drive Strength")
            else:
                self.insp_drv_val.setText("Lv --")
                self.insp_drv_key.setText(
                    "Drive Strength ({0})".format(
                        "no drv_sel register for this pin"
                        if self._cfg.drv_supported
                        else "drv_sel not configured in chip JSON"))

            in_lvl = self._in_bit(bank_idx, bit)
            if in_lvl is None:
                self.insp_big_state.setText("LOGIC --")
                self.insp_big_state.setProperty("lvl", "")
            else:
                self.insp_big_state.setText(
                    "LOGIC {0} ({1})".format("HIGH" if in_lvl else "LOW", in_lvl))
                self.insp_big_state.setProperty("lvl", "h" if in_lvl else "l")
            _repolish(self.insp_big_state)

            drv_txt = ""
            if field_ is not None:
                drv_txt = " · drv {0} [{1}:{2}]".format(
                    _fmt32(field_[0]), field_[1], field_[2])
            self.insp_mask.setText(
                "Mask {0} · bank bit {1}{2}".format(_fmt32(1 << bit), bit, drv_txt))

        if multi:
            self._update_multi_op_enabled(ready)
        else:
            pull_ok = has and self._cfg.pull_supported(sel[0])
            drv_ok = has and self._cfg.drv_field(sel[0], sel[1]) is not None
            drv_val = self._drv_field_value(sel[0], sel[1]) if drv_ok else None
            # 输出电平与方向联动：INPUT 时 HIGH/LOW 禁用置灰
            out_ok = has and bool(self._dir_bit(
                self._cfg.bank_index(sel[0]),
                self._cfg.bit_in_bank(sel[0], sel[1])))
            for b in (self.insp_dir_out, self.insp_dir_in, self.insp_read_btn):
                b.setEnabled(has and ready)
            for b in (self.insp_lvl_h, self.insp_lvl_l):
                b.setEnabled(has and ready and out_ok)
            for b in (self.insp_pull_hiz, self.insp_pull_pu, self.insp_pull_pd):
                b.setEnabled(has and ready and pull_ok)
            self.insp_drv_dec.setEnabled(
                ready and drv_val is not None and drv_val > 0)
            self.insp_drv_inc.setEnabled(
                ready and drv_val is not None and drv_val < self._cfg.drv_max_level)
            self.insp_drv_val.setEnabled(drv_ok)
            self.alias_edit.setEnabled(has)

    def _refresh_multi_rows(self):
        """多选列表行：GPIO 名 + 当前模式 + 行内移除。"""
        pins = self._selected_pins
        self.insp_name.setText("{0} pins".format(len(pins)))
        while self._multi_list_lay.count():
            item = self._multi_list_lay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for group, pin in pins:
            row = QFrame()
            row.setObjectName("exportRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 0, 4, 0)
            rl.setSpacing(6)
            name = QLabel(self._cfg.gpio_name(group, pin))
            name.setObjectName("pinName")
            rl.addWidget(name)
            mode_lb = QLabel(mode_label(self._pin_mode(group, pin)))
            mode_lb.setObjectName("exportMode")
            rl.addWidget(mode_lb, 1)
            del_btn = QPushButton()
            del_btn.setObjectName("exportDel")
            del_btn.setIcon(_icon("x-close.svg", "#94A3B8", 10))
            del_btn.setToolTip("Remove from selection")
            del_btn.clicked.connect(
                lambda checked=False, g=group, p=pin:
                self._remove_selected_pin(g, p))
            rl.addWidget(del_btn)
            self._multi_list_lay.addWidget(row)
        self._multi_list_lay.addStretch(1)

    def _update_multi_op_enabled(self, ready):
        """多选模式：配置区按全体选中脚判定使能，单脚状态高亮复位。"""
        pins = self._selected_pins
        all_out = all(self._dir_bit(self._cfg.bank_index(g),
                                    self._cfg.bit_in_bank(g, p))
                      for g, p in pins)
        pull_ok = all(self._cfg.pull_supported(g) for g, _ in pins)
        drvs = [self._drv_field_value(g, p) for g, p in pins]
        drv_ok = all(v is not None for v in drvs)
        for b in (self.insp_dir_out, self.insp_dir_in, self.insp_read_btn):
            b.setEnabled(ready)
        for b in (self.insp_lvl_h, self.insp_lvl_l):
            b.setEnabled(ready and all_out)
        for b in (self.insp_pull_hiz, self.insp_pull_pu, self.insp_pull_pd):
            b.setEnabled(ready and pull_ok)
        self.insp_drv_dec.setEnabled(ready and drv_ok and min(drvs) > 0)
        self.insp_drv_inc.setEnabled(
            ready and drv_ok and max(drvs) < self._cfg.drv_max_level)
        self.insp_drv_val.setEnabled(drv_ok)
        self.alias_edit.setEnabled(False)
        if drv_ok:
            lo, hi = min(drvs), max(drvs)
            self.insp_drv_val.setText(
                self._drv_level_text(lo) if lo == hi
                else "Lv{0}~{1}".format(lo, hi))
        else:
            self.insp_drv_val.setText("Lv --")
        self.insp_drv_key.setText("Drive Strength")
        for b in (self.insp_dir_out, self.insp_dir_in, self.insp_lvl_h,
                  self.insp_lvl_l, self.insp_pull_hiz, self.insp_pull_pu,
                  self.insp_pull_pd):
            b.setProperty("cur", "0")
            _repolish(b)

    def _update_op_enabled(self):
        ready = self._ready()
        busy = self._busy()
        for btn in self._batch_buttons:
            btn.setEnabled(ready and not busy)
        self.mask_btn.setEnabled(ready and not busy)
        self.read_btn.setEnabled(ready and not busy)
        self.raw_write_btn.setEnabled(ready and not busy)
        self.raw_read_btn.setEnabled(ready and not busy)
        self.reg_refresh_btn.setEnabled(ready and not busy)
        self.poll_btn.setEnabled(ready)
        self.detect_btn.setEnabled(not busy)
        self.load_btn.setEnabled(not busy)
        self._exec_btn.setEnabled(ready and not busy)

    # ================================================================ Sniffer

    def _set_status(self, text, ok=False, err=False):
        self.status_label.setText(text)
        self.status_label.setProperty("ok", "1" if ok else "0")
        self.status_label.setProperty("err", "1" if err else "0")
        _repolish(self.status_label)

    # ================================================================ AI 动作登记
