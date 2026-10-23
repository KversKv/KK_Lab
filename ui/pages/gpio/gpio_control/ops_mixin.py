# -*- coding: utf-8 -*-
"""GPIO 页 Worker 线程管道与硬件操作 Mixin（Detect / Batch / Poll / Raw / Pin / Drv / Inspector）。"""

import os

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QIcon, QTransform

from log_config import get_logger
from ui.utils.icon_utils import tinted_svg_pixmap
from core.gpio.gpio_config import (
    load_gpio_config, OP_WRITE, OP_BITS, OFFSET_OUT_SET,
    OFFSET_DIR_SET, OFFSET_OUT_CLR, OFFSET_DIR_CLR,
    OFFSET_IN_READ, PINS_PER_GROUP
)
from core.gpio.gpio_workers import GpioChipCheckWorker, GpioReadBanksWorker, GpioApplyWorker

from ui.pages.gpio.gpio_control.style import _ICONS_DIR
from ui.pages.gpio.gpio_control.utils import (
    _icon, _fmt32, _repolish, _parse_hex
)

logger = get_logger(__name__)

class OpsMixin:
    """Worker 线程管道与硬件操作（Detect/Batch/Poll/Raw/Pin/Drv/Inspector）。"""

    def _mask_pins(self, mask):
        bits = [i for i in range(32) if (mask >> i) & 1]
        if not bits:
            return "no pin (mask: {0})".format(_fmt32(mask))
        if len(bits) > 8:
            head = "{0} pins".format(len(bits))
        else:
            head = " ".join("BIT{0:02d}".format(i) for i in bits)
        return "{0} (mask: {1})".format(head, _fmt32(mask))

    def _busy(self):
        return self._thread is not None and self._thread.isRunning()

    def _run_worker(self, worker, on_done, on_error):
        """装配并启动单次 Worker 线程（QObject + moveToThread）。

        线程不挂父对象：本页为内嵌子页面，销毁时不走 closeEvent；
        worker 到页面的信号均为绑定方法连接（页面销毁自动断开），
        线程自身由 finished -> deleteLater 自清理，杜绝"运行中的
        QThread 随页面析构"导致的进程崩溃（access violation）。
        """
        if self._busy():
            return False
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        if hasattr(worker, "progress"):
            worker.progress.connect(self.append_log)
        self._worker_done_cb = on_done
        worker.finished.connect(self._on_worker_done)
        worker.error.connect(on_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_cleanup)
        self._worker = worker
        self._thread = thread
        self._set_top_busy(True)
        thread.start()
        return True

    def _on_worker_done(self, *args):
        """worker.finished 统一分发（绑定方法连接，页面销毁自动断开）。"""
        cb, self._worker_done_cb = self._worker_done_cb, None
        if cb is not None:
            cb(*args)

    def _on_thread_cleanup(self):
        # 旧线程 finished 晚到时勿清新线程引用（sender 校验）
        sender = self.sender()
        if sender is not None and self._thread is not None \
                and sender is not self._thread:
            return
        self._thread = None
        self._worker = None
        self._set_top_busy(False)

    def _defer_read(self, fn, delay_ms=80):
        """延迟执行读操作（§26）；定时器为页内子对象，页面销毁自动失效。"""
        self._deferred_read_fn = fn
        self._deferred_timer.start(delay_ms)

    def _on_deferred_read(self):
        fn, self._deferred_read_fn = self._deferred_read_fn, None
        if fn is not None:
            fn()

    def _set_top_busy(self, busy):
        self._update_op_enabled()

    def _on_op_error(self, msg):
        self.append_log("[ERROR] {0}".format(msg))
        self._sniff("ERROR", None, None, "Operation failed: {0}".format(msg))
        self._set_status("Operation failed: {0}".format(msg), err=True)
        self._stop_spin()

    def _apply_to_shadow(self, actions):
        for op, addr, value, hi, lo in actions:
            if op == OP_BITS:
                cur = self._reg_shadow.get(addr, 0)
                mask = ((1 << (hi - lo + 1)) - 1) << lo
                self._reg_shadow[addr] = (cur & ~mask) | ((value << lo) & mask)
                continue
            matched = False
            if self._cfg is not None:
                for b_idx, bank in enumerate(self._cfg.banks):
                    off = addr - bank.base
                    if off == OFFSET_OUT_SET:
                        self._out_shadow[b_idx] = \
                            self._out_shadow.get(b_idx, 0) | value
                        matched = True
                        break
                    if off == OFFSET_OUT_CLR:
                        self._out_shadow[b_idx] = \
                            self._out_shadow.get(b_idx, 0) & ~value & 0xFFFFFFFF
                        matched = True
                        break
                    if off == OFFSET_DIR_SET:
                        self._dir_shadow[b_idx] = \
                            self._dir_shadow.get(b_idx, 0) | value
                        matched = True
                        break
                    if off == OFFSET_DIR_CLR:
                        self._dir_shadow[b_idx] = \
                            self._dir_shadow.get(b_idx, 0) & ~value & 0xFFFFFFFF
                        matched = True
                        break
            if not matched:
                self._reg_shadow[addr] = value & 0xFFFFFFFF

    def _apply_actions(self, actions, label="", on_done=None):
        """统一下发管道：嗅探 -> 影子更新 -> 硬件 Worker。"""
        if not actions:
            return False
        if not self._ready():
            self.append_log("[WARN] DUT not connected. Run i2c.bes_chip_check() first")
            return False
        if self._busy():
            self.append_log("[WARN] Previous operation still running, "
                            "please wait ({0})".format(label))
            return False
        for op, addr, value, hi, lo in actions:
            self._sniff("WRITE32", addr, value,
                        self._describe_write(op, addr, value, hi, lo))
        if label:
            self.append_log("[I2C] {0}".format(label))
        self._apply_to_shadow(actions)
        worker = GpioApplyWorker(
            None, self.speed_combo.currentData(), self._dev_addr,
            actions, label=label)
        return self._run_worker(
            worker,
            lambda: self._on_hw_applied(on_done),
            self._on_op_error)

    def _on_hw_applied(self, on_done=None):
        self._refresh_after_hw()
        if on_done is not None:
            on_done()

    def _read_registers(self, pairs, on_done=None):
        """pairs: [(key, addr)]；硬件走 Worker 异步读取。"""
        if not pairs:
            return False
        if not self._ready():
            self.append_log("[WARN] DUT not connected, cannot read")
            return False
        if self._busy():
            return False
        worker = GpioReadBanksWorker(
            None, self.speed_combo.currentData(), self._dev_addr, pairs)
        return self._run_worker(
            worker,
            lambda values: self._on_read_done(pairs, values, on_done),
            self._on_op_error)

    def _on_read_done(self, pairs, values, on_done=None):
        for key, addr in pairs:
            value = values.get(key)
            if value is None:
                continue
            desc = self._describe_read(addr, value)
            self._sniff("READ32", addr, value, desc)
            self.append_log("[I2C] READ {0} = {1}  {2}".format(
                _fmt32(addr), _fmt32(value), desc))
            matched = False
            if self._cfg is not None:
                for b_idx, bank in enumerate(self._cfg.banks):
                    if addr == bank.base + OFFSET_IN_READ:
                        self._in_value[b_idx] = value
                        matched = True
                        break
            if not matched:
                self._reg_shadow[addr] = value & 0xFFFFFFFF
        self._refresh_after_hw()
        if on_done is not None:
            on_done(values)

    # ================================================================ 事件：顶部

    def _on_tab_changed(self, idx):
        self._stack.setCurrentIndex(idx)

    def _on_spin_tick(self):
        self._spin_angle = (self._spin_angle + 90) % 360
        pm = tinted_svg_pixmap(os.path.join(_ICONS_DIR, "refresh-cw.svg"),
                               "#22D3EE", 13)
        if not pm.isNull():
            self.detect_btn.setIcon(
                QIcon(pm.transformed(QTransform().rotate(self._spin_angle))))

    def _start_spin(self):
        self._spin_angle = 0
        self._spin_timer.start()

    def _stop_spin(self):
        self._spin_timer.stop()
        self.detect_btn.setIcon(_icon("refresh-cw.svg", "#22D3EE", 13))

    def _on_detect_clicked(self):
        if self._busy():
            return
        self._sniff("CHIP_CHECK", None, None,
                    "i2c.bes_chip_check() -> dev 0x11 reg 0x40080000 (32bit)")
        self._set_status("Detecting...")
        self._start_spin()
        self.append_log("[I2C] Detecting BES chip...")
        worker = GpioChipCheckWorker(None, self.speed_combo.currentData())
        self._run_worker(worker, self._on_detect_done, self._on_op_error)

    def _on_detect_done(self, chip_info):
        self._stop_spin()
        self._chip_info = chip_info
        chip_name = chip_info.get("chip_name")
        main_die = chip_info.get("main_die")
        if chip_info.get("warning"):
            self.append_log("[WARN] {0}".format(chip_info["warning"]))
        if not main_die or not chip_info.get("main_die_i2c_addr"):
            self._cfg = None
            self._dev_addr = None
            self._set_status("Cannot read Main-die. Ensure the chip is "
                             "powered on and not in sleep", err=True)
            self.append_log("[ERROR] Main-die detection failed")
            self._sniff("ERROR", None, None, "Main-die detection failed")
            self._refresh_all_views()
            return
        addr = chip_info["main_die_i2c_addr"]
        self._dev_addr = int(addr, 0) if isinstance(addr, str) else int(addr)
        self.append_log("[I2C] Detect result: {0} {1} · dev=0x{2:02X}".format(
            main_die, chip_info.get("main_die_version") or "", self._dev_addr))
        self._sniff("CHIP_CHECK", None, None,
                    "Identified: {0} {1} · main_die dev=0x{2:02X}".format(
                        main_die, chip_info.get("main_die_version") or "",
                        self._dev_addr))

        self._cfg = load_gpio_config(chip_name)
        if self._cfg is None:
            self._set_status(
                "{0} · No GPIO config chips/gpio_configs/{1}.json".format(
                    main_die, chip_name), err=True)
            self.append_log(
                "[WARN] GPIO config for chip {0} not found. Add "
                "chips/gpio_configs/{0}.json".format(chip_name))
            self._refresh_all_views()
            return

        idx = self.profile_combo.findData(chip_name)
        if idx >= 0:
            self.profile_combo.blockSignals(True)
            self.profile_combo.setCurrentIndex(idx)
            self.profile_combo.blockSignals(False)

        self._reset_session_state()
        self._set_status("{0} {1} · dev 0x{2:02X} · {3} banks".format(
            main_die, chip_info.get("main_die_version") or "",
            self._dev_addr, len(self._cfg.banks)), ok=True)
        self.append_log("[I2C] GPIO config loaded: {0} ({1} banks / {2} GPIO)".format(
            self._cfg.chip, len(self._cfg.banks),
            self._cfg.group_count * PINS_PER_GROUP))
        self._load_json_editor()
        self._refresh_all_views()
        # 检测完成后自动全量回读一轮输入电平（§26：延迟 ≥50ms 再起新线程）
        self._defer_read(self._start_read_all_banks)

    def _on_load_profile_clicked(self):
        if self._busy():
            return
        name = self.profile_combo.currentData()
        if not name:
            self._set_status("No DUT Profile available", err=True)
            return
        if self._dev_addr is None:
            self.append_log("[WARN] Run i2c.bes_chip_check() before loading Profile")
            self._set_status("Detect DUT first", err=True)
            return
        cfg = load_gpio_config(name)
        if cfg is None:
            self._set_status("Profile load failed: {0}".format(name), err=True)
            return
        self._cfg = cfg
        self._reset_session_state()
        self._sniff("CHIP_CHECK", None, None,
                    "DUT Profile loaded manually: {0}".format(name))
        self._set_status("Profile: {0} · {1} banks".format(name, len(cfg.banks)),
                         ok=True)
        self.append_log("[I2C] DUT Profile loaded: {0}".format(name))
        self._load_json_editor()
        self._refresh_all_views()
        self._start_read_all_banks()

    def _on_bank_changed(self, idx):
        if idx == self._cur_bank or self._cfg is None:
            return
        self._cur_bank = idx
        self._selected = None
        self._selected_pins = []
        self._rebuild_matrix()
        self._rebuild_regmap()
        self._refresh_addr_bar()
        self._refresh_stats()
        self._refresh_inspector()

    # ================================================================ 事件：批处理

    def _batch_apply(self, actions, label):
        if not self._ready():
            self.append_log("[WARN] DUT not connected. Detect or load Profile first")
            return
        self._apply_actions(actions, label=label,
                            on_done=lambda: self._queue_bank_read(self._cur_bank))

    def _queue_bank_read(self, bank_idx):
        # §26：worker finished 槽链里再起读线程须延迟 ≥50ms
        self._defer_read(lambda: self._start_read_bank(bank_idx))

    def _on_batch_out_high(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        mask = self._bank_pin_mask(self._cur_bank)
        self._batch_apply(
            self._func_sel_mask_actions(self._cur_bank, mask) + [
                (OP_WRITE, bank.base + OFFSET_DIR_SET, mask, -1, -1),
                (OP_WRITE, bank.base + OFFSET_OUT_SET, mask, -1, -1),
            ], "All OUT HIGH -> Bank{0}".format(self._cur_bank))

    def _on_batch_out_low(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        mask = self._bank_pin_mask(self._cur_bank)
        self._batch_apply(
            self._func_sel_mask_actions(self._cur_bank, mask) + [
                (OP_WRITE, bank.base + OFFSET_DIR_SET, mask, -1, -1),
                (OP_WRITE, bank.base + OFFSET_OUT_CLR, mask, -1, -1),
            ], "All OUT LOW -> Bank{0}".format(self._cur_bank))

    def _on_batch_in_hiz(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        mask = self._bank_pin_mask(self._cur_bank)
        actions = self._func_sel_mask_actions(self._cur_bank, mask)
        actions.append((OP_WRITE, bank.base + OFFSET_DIR_CLR, mask, -1, -1))
        for addr in (self._cfg.pull_up_bases[self._cur_bank]
                     if self._cur_bank < len(self._cfg.pull_up_bases) else None,
                     self._cfg.pull_down_bases[self._cur_bank]
                     if self._cur_bank < len(self._cfg.pull_down_bases) else None):
            if addr is not None:
                actions.append((OP_BITS, addr, 0, 31, 0))
        self._batch_apply(actions, "All IN Hi-Z -> Bank{0}".format(self._cur_bank))

    def _on_batch_pull(self, up):
        if self._cfg is None:
            return
        b = self._cur_bank
        pu = self._cfg.pull_up_bases[b] if b < len(self._cfg.pull_up_bases) else None
        pd = self._cfg.pull_down_bases[b] if b < len(self._cfg.pull_down_bases) else None
        if pu is None or pd is None:
            self.append_log(
                "[WARN] Bank{0} pull addresses not configured in JSON".format(b))
            return
        actions = self._func_sel_mask_actions(b, self._bank_pin_mask(b))
        actions += [
            (OP_BITS, pd if up else pu, 0, 31, 0),
            (OP_BITS, pu if up else pd, self._bank_pin_mask(b), 31, 0),
        ]
        self._batch_apply(
            actions, "All {0} -> Bank{1}".format("PU" if up else "PD", b))

    def _on_batch_invert(self):
        if self._cfg is None:
            return
        bank = self._cfg.banks[self._cur_bank]
        b = self._cur_bank
        dir_v = self._dir_shadow.get(b, 0)
        out_v = self._out_shadow.get(b, 0)
        pin_mask = self._bank_pin_mask(b)
        set_mask = (~out_v) & dir_v & pin_mask
        clr_mask = out_v & dir_v & pin_mask
        actions = self._func_sel_mask_actions(b, dir_v)
        if set_mask:
            actions.append((OP_WRITE, bank.base + OFFSET_OUT_SET, set_mask, -1, -1))
        if clr_mask:
            actions.append((OP_WRITE, bank.base + OFFSET_OUT_CLR, clr_mask, -1, -1))
        if not actions:
            self.append_log("[INFO] Bank{0} has no output pins to invert".format(b))
            return
        self._batch_apply(actions, "Invert OUT -> Bank{0}".format(b))

    def _on_mask_write_clicked(self):
        if not self._ready():
            self.append_log("[WARN] DUT not connected, cannot write mask")
            return
        mask = _parse_hex(self.mask_edit.text())
        if mask is None:
            self._set_status("Invalid mask format (e.g. 0x000000FF)", err=True)
            return
        bank = self._cfg.banks[self._cur_bank]
        off = self.mask_target.currentData()
        addr = bank.base + off
        self._apply_actions(
            self._func_sel_mask_actions(self._cur_bank, mask)
            + [(OP_WRITE, addr, mask, -1, -1)],
            label="Mask inject {0} -> {1}".format(
                _fmt32(mask), self.mask_target.currentText()),
            on_done=lambda: self._queue_bank_read(self._cur_bank))

    def _on_poll_toggled(self):
        if self._poll_timer.isActive():
            self._stop_polling()
            return
        if not self._ready():
            self.append_log("[WARN] DUT not connected, cannot start polling")
            return
        self._poll_timer.start(self.poll_combo.currentData())
        self.poll_btn.setText("Stop Poll")
        self.poll_btn.setProperty("on", "1")
        _repolish(self.poll_btn)
        self.append_log("[I2C] 0x50 polling started ({0})".format(
            self.poll_combo.currentText()))

    def _stop_polling(self):
        if self._poll_timer.isActive():
            self._poll_timer.stop()
            self.append_log("[I2C] 0x50 polling stopped")
        self.poll_btn.setText("Start Poll")
        self.poll_btn.setProperty("on", "0")
        _repolish(self.poll_btn)

    def _on_poll_interval_changed(self):
        if self._poll_timer.isActive():
            self._poll_timer.start(self.poll_combo.currentData())

    def _on_poll_tick(self):
        if self._busy() or not self._ready():
            return
        self._start_read_bank(self._cur_bank)

    # ================================================================ 事件：读取

    def _on_read_bank_clicked(self):
        if not self._ready():
            self.append_log("[WARN] DUT not connected, cannot read")
            return
        self._start_read_bank(self._cur_bank)

    def _start_read_all_banks(self):
        """全量回读可读状态：各 bank 0x50 电平 + PU/PD + drv + func_sel。"""
        if self._cfg is None or self._dev_addr is None:
            return
        cfg = self._cfg
        pairs = []
        for i, bank in enumerate(cfg.banks):
            pairs.append((i, bank.base + OFFSET_IN_READ))
            for addr in (cfg.pull_up_bases[i] if i < len(cfg.pull_up_bases) else None,
                         cfg.pull_down_bases[i] if i < len(cfg.pull_down_bases) else None):
                if addr is not None:
                    pairs.append(("reg_{0:08X}".format(addr), addr))
        seen = set()
        for addr, _first in cfg.drv_registers():
            if addr not in seen:
                seen.add(addr)
                pairs.append(("reg_{0:08X}".format(addr), addr))
        for g in range(cfg.group_count):
            field_ = cfg.func_sel_field(g, 0)
            if field_ is not None and field_[0] not in seen:
                seen.add(field_[0])
                pairs.append(("reg_{0:08X}".format(field_[0]), field_[0]))
        self.append_log(
            "[I2C] Reading back all IO states (level/pull/drv/func_sel)...")
        self._read_registers(pairs)

    def _start_read_bank(self, bank_idx):
        if self._cfg is None or bank_idx >= len(self._cfg.banks):
            return
        bank = self._cfg.banks[bank_idx]
        self._read_registers([(bank_idx, bank.base + OFFSET_IN_READ)])

    def _on_refresh_readable(self):
        if not self._ready():
            return
        pairs = []
        bank = self._cfg.banks[self._cur_bank]
        pairs.append((self._cur_bank, bank.base + OFFSET_IN_READ))
        b = self._cur_bank
        for addr in (self._cfg.pull_up_bases[b] if b < len(self._cfg.pull_up_bases) else None,
                     self._cfg.pull_down_bases[b] if b < len(self._cfg.pull_down_bases) else None):
            if addr is not None:
                pairs.append(("reg_{0:08X}".format(addr), addr))
        for card in self._reg_cards:
            if card["kind"] in ("drv", "fsel") and card["addr"] is not None:
                pairs.append(("reg_{0:08X}".format(card["addr"]), card["addr"]))
        self._read_registers(pairs)

    def _on_raw_write(self):
        if not self._ready():
            self.append_log("[WARN] DUT not connected, cannot write")
            return
        addr = _parse_hex(self.raw_addr.text())
        data = _parse_hex(self.raw_data.text())
        if addr is None or data is None:
            self._set_status("Invalid Raw address / data format", err=True)
            return
        self._apply_actions([(OP_WRITE, addr, data, -1, -1)],
                            label="Raw write {0} = {1}".format(
                                _fmt32(addr), _fmt32(data)))

    def _on_raw_read(self):
        if not self._ready():
            self.append_log("[WARN] DUT not connected, cannot read")
            return
        addr = _parse_hex(self.raw_addr.text())
        if addr is None:
            self._set_status("Invalid Raw address format", err=True)
            return
        self._read_registers(
            [("raw", addr)],
            on_done=lambda values: self.raw_result.setText(
                _fmt32(values.get("raw", 0))))

    def _on_reg_read(self, kind, addr):
        if not self._ready():
            return
        if kind == "val_in":
            self._start_read_bank(self._cur_bank)
        else:
            self._read_registers([("reg_{0:08X}".format(addr), addr)])

    # ================================================================ 事件：引脚操作

    def _on_pin_clicked(self, group, pin, modifiers=Qt.NoModifier):
        """卡片点击选中；按住 Ctrl 累加/移除多选（属性面板切换为选中列表）。"""
        key = (group, pin)
        if modifiers & Qt.ControlModifier:
            if key in self._selected_pins:
                self._selected_pins.remove(key)
            else:
                self._selected_pins.append(key)
        else:
            self._selected_pins = [key]
        self._selected = self._selected_pins[-1] if self._selected_pins else None
        for k in self._pin_cards:
            self._refresh_pin_card(*k)
        self._refresh_inspector()

    def _remove_selected_pin(self, group, pin):
        key = (group, pin)
        if key in self._selected_pins:
            self._selected_pins.remove(key)
        self._selected = self._selected_pins[-1] if self._selected_pins else None
        for k in self._pin_cards:
            self._refresh_pin_card(*k)
        self._refresh_inspector()

    def _on_card_dir(self, group, pin):
        if not self._ready():
            return
        self._selected = (group, pin)
        self._selected_pins = [(group, pin)]
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        out_now = bool(self._dir_bit(bank_idx, bit))
        addr = (self._cfg.dir_clr_addr(group) if out_now
                else self._cfg.dir_set_addr(group))
        name = self._cfg.gpio_name(group, pin)
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} -> {1}".format(name, "INPUT" if out_now else "OUTPUT"),
            on_done=lambda: self._queue_bank_read(bank_idx))

    def _on_card_level(self, group, pin):
        if not self._ready():
            return
        self._selected = (group, pin)
        self._selected_pins = [(group, pin)]
        bank_idx = self._cfg.bank_index(group)
        bit = self._cfg.bit_in_bank(group, pin)
        name = self._cfg.gpio_name(group, pin)
        if not self._dir_bit(bank_idx, bit):
            self._on_input_read(group, pin)
            return
        high_now = bool(self._out_bit(bank_idx, bit))
        addr = (self._cfg.out_clr_addr(group) if high_now
                else self._cfg.out_set_addr(group))
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} -> {1}".format(name, "LOW" if high_now else "HIGH"),
            on_done=lambda: self._queue_bank_read(bank_idx))

    def _on_input_read(self, group, pin):
        """输入脚点击：触发所属 Bank 0x50 输入电平回读。"""
        if not self._ready():
            return
        self._start_read_bank(self._cfg.bank_index(group))

    def _on_card_pull(self, group, pin):
        if not self._ready() or not self._cfg.pull_supported(group):
            return
        self._selected = (group, pin)
        self._selected_pins = [(group, pin)]
        bit = self._cfg.bit_in_bank(group, pin)
        nxt = (self._pull_state(group, bit) + 1) % 3
        self._apply_pull(group, pin, nxt)

    def _apply_pull(self, group, pin, state):
        name = self._cfg.gpio_name(group, pin)
        label = {0: "Hi-Z", 1: "Pull-Up", 2: "Pull-Down"}[state]
        self._apply_actions(
            self._pull_pin_actions(group, pin, state),
            label="{0} pull -> {1}".format(name, label),
            on_done=lambda: self._queue_bank_read(self._cfg.bank_index(group)))

    def _pull_pin_actions(self, group, pin, state):
        """单脚上下拉动作为：func_sel 前置 + PU/PD 位域写。"""
        bit = self._cfg.bit_in_bank(group, pin)
        pu = self._cfg.pull_up_addr(group)
        pd = self._cfg.pull_down_addr(group)
        actions = self._func_sel_pin_actions(group, pin)
        if state == 0:
            actions.append((OP_BITS, pu, 0, bit, bit))
            actions.append((OP_BITS, pd, 0, bit, bit))
        elif state == 1:
            actions.append((OP_BITS, pd, 0, bit, bit))
            actions.append((OP_BITS, pu, 1, bit, bit))
        else:
            actions.append((OP_BITS, pu, 0, bit, bit))
            actions.append((OP_BITS, pd, 1, bit, bit))
        return actions

    def _selected_by_bank(self):
        """选中脚位按 bank 聚合 {bank_idx: 位掩码}（多选统一配置用）。"""
        banks = {}
        for group, pin in self._selected_pins:
            b = self._cfg.bank_index(group)
            banks[b] = banks.get(b, 0) | (1 << self._cfg.bit_in_bank(group, pin))
        return banks

    def _queue_banks_read(self, bank_indices):
        """延迟回读多个 bank 的 0x50 输入电平（§26 延迟合并）。"""
        pairs = [(b, self._cfg.banks[b].base + OFFSET_IN_READ)
                 for b in sorted(bank_indices)]
        self._defer_read(lambda: self._read_registers(pairs))

    def _on_drv_step(self, delta):
        if not self._selected_pins or not self._ready():
            return
        if len(self._selected_pins) > 1:
            actions = []
            for group, pin in self._selected_pins:
                cur = self._drv_field_value(group, pin)
                if cur is None:
                    continue
                actions += self._func_sel_pin_actions(group, pin)
                actions += self._cfg.build_drv_actions(group, pin, cur + delta)
            if not actions:
                return
            self._apply_actions(
                actions, label="{0} pins drv {1:+d}".format(
                    len(self._selected_pins), delta))
            return
        group, pin = self._selected_pins[0]
        cur = self._drv_field_value(group, pin)
        if cur is None:
            return
        self._apply_drv(group, pin, cur + delta)

    def _apply_drv(self, group, pin, level):
        if not self._ready():
            return
        actions = self._cfg.build_drv_actions(group, pin, level)
        name = self._cfg.gpio_name(group, pin)
        if actions is None:
            self.append_log("[WARN] {0} does not support drv config".format(name))
            return
        level = actions[0][2]
        ohm = self._drv_ohm_text(level)
        actions = self._func_sel_pin_actions(group, pin) + actions
        self._apply_actions(
            actions, label="{0} drv -> Lv{1}{2}".format(
                name, level, " ({0})".format(ohm) if ohm else ""))

    def _on_insp_dir(self, output):
        if not self._selected_pins or not self._ready():
            return
        if len(self._selected_pins) > 1:
            banks = self._selected_by_bank()
            off = OFFSET_DIR_SET if output else OFFSET_DIR_CLR
            actions = []
            for b, mask in banks.items():
                actions += self._func_sel_mask_actions(b, mask)
                actions.append(
                    (OP_WRITE, self._cfg.banks[b].base + off, mask, -1, -1))
            self._apply_actions(
                actions,
                label="{0} pins dir -> {1}".format(
                    len(self._selected_pins), "OUTPUT" if output else "INPUT"),
                on_done=lambda: self._queue_banks_read(banks))
            return
        group, pin = self._selected_pins[0]
        addr = (self._cfg.dir_set_addr(group) if output
                else self._cfg.dir_clr_addr(group))
        bit = self._cfg.bit_in_bank(group, pin)
        name = self._cfg.gpio_name(group, pin)
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} dir -> {1}".format(name, "OUTPUT" if output else "INPUT"),
            on_done=lambda: self._queue_bank_read(self._cfg.bank_index(group)))

    def _on_insp_level(self, high):
        if not self._selected_pins or not self._ready():
            return
        if len(self._selected_pins) > 1:
            banks = self._selected_by_bank()
            off = OFFSET_OUT_SET if high else OFFSET_OUT_CLR
            actions = []
            for b, mask in banks.items():
                actions += self._func_sel_mask_actions(b, mask)
                actions.append(
                    (OP_WRITE, self._cfg.banks[b].base + off, mask, -1, -1))
            self._apply_actions(
                actions,
                label="{0} pins level -> {1}".format(
                    len(self._selected_pins), "HIGH" if high else "LOW"),
                on_done=lambda: self._queue_banks_read(banks))
            return
        group, pin = self._selected_pins[0]
        addr = (self._cfg.out_set_addr(group) if high
                else self._cfg.out_clr_addr(group))
        bit = self._cfg.bit_in_bank(group, pin)
        name = self._cfg.gpio_name(group, pin)
        self._apply_actions(
            self._func_sel_pin_actions(group, pin)
            + [(OP_WRITE, addr, 1 << bit, -1, -1)],
            label="{0} level -> {1}".format(name, "HIGH" if high else "LOW"),
            on_done=lambda: self._queue_bank_read(self._cfg.bank_index(group)))

    def _on_insp_pull(self, state):
        if not self._selected_pins or not self._ready():
            return
        if len(self._selected_pins) > 1:
            if not all(self._cfg.pull_supported(g)
                       for g, _ in self._selected_pins):
                self.append_log(
                    "[WARN] Pull addresses not configured for some Bank")
                return
            label = {0: "Hi-Z", 1: "Pull-Up", 2: "Pull-Down"}[state]
            actions = []
            for group, pin in self._selected_pins:
                actions += self._pull_pin_actions(group, pin, state)
            self._apply_actions(
                actions,
                label="{0} pins pull -> {1}".format(
                    len(self._selected_pins), label),
                on_done=lambda: self._queue_banks_read(
                    self._selected_by_bank()))
            return
        group, pin = self._selected_pins[0]
        if not self._cfg.pull_supported(group):
            self.append_log("[WARN] Pull addresses not configured for this Bank")
            return
        self._apply_pull(group, pin, state)

    def _on_alias_edited(self):
        if self._selected is None or self._cfg is None:
            return
        group, pin = self._selected
        alias = self.alias_edit.text().strip()
        self._meta(group, pin)["alias"] = alias
        self._refresh_pin_card(group, pin)
        if alias:
            self.append_log("[INFO] {0} alias -> {1}".format(
                self._cfg.gpio_name(group, pin), alias))

    # ================================================================ 事件：寄存器视图

    def _on_reg_bit(self, kind, addr, bit):
        if not self._ready():
            return
        bank = self._cfg.banks[self._cur_bank]
        mask = 1 << bit
        if kind == "val_set":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_OUT_SET, mask, -1, -1)],
                label="Bit flip VAL_SET bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "val_clr":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_OUT_CLR, mask, -1, -1)],
                label="Bit flip VAL_CLR bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "dir_set":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_DIR_SET, mask, -1, -1)],
                label="Bit flip DIR_SET bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "dir_clr":
            self._apply_actions(
                [(OP_WRITE, bank.base + OFFSET_DIR_CLR, mask, -1, -1)],
                label="Bit flip DIR_CLR bit{0}".format(bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))
        elif kind == "val_in":
            self._start_read_bank(self._cur_bank)
        elif kind in ("drv", "fsel"):
            bits = (self._cfg.drv_bits_per_gpio if kind == "drv"
                    else self._cfg.func_sel_bits_per_gpio)
            low = bit - (bit % bits)
            high = low + bits - 1
            fmask = (1 << bits) - 1
            cur = (self._reg_shadow.get(addr, 0) >> low) & fmask
            new = cur ^ (1 << (bit - low))
            new_txt = ("Lv{0}".format(new) if kind == "drv"
                       else "0x{0:X}".format(new))
            self._apply_actions(
                [(OP_BITS, addr, new, high, low)],
                label="Bit flip {0} [{1}:{2}] -> {3}".format(
                    kind.upper(), high, low, new_txt))
        elif kind in ("pu", "pd"):
            cur = (self._reg_shadow.get(addr, 0) >> bit) & 1
            self._apply_actions(
                [(OP_BITS, addr, 0 if cur else 1, bit, bit)],
                label="Bit flip {0} bit{1}".format(kind.upper(), bit),
                on_done=lambda: self._queue_bank_read(self._cur_bank))

    # ================================================================ JSON 配置视图

    def cleanup_threads(self):
        """关停定时器并等待 Worker 线程退出（CleanupMixin 契约）。

        MainWindow 关闭时经 _perform_close_cleanup 调用；closeEvent 复用。
        """
        try:
            self._stop_polling()
            self._spin_timer.stop()
            self._deferred_timer.stop()
            self._deferred_read_fn = None
            self._worker_done_cb = None
            if self._thread is not None and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(2000)
        except Exception:
            logger.error("GPIO page cleanup wait failed", exc_info=True)
