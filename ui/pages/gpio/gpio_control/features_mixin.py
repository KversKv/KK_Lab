# -*- coding: utf-8 -*-
"""GPIO 页功能 Mixin（Sniffer / JSON Config / Export Manager / Confirm Note / AI 动作注册）。"""

import os
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QFrame, QFileDialog,
    QApplication, QMenu
)

from log_config import get_logger
from ui.resource_path import get_user_data_dir
from core.ai.ui_action_registry import UIActionSpec
from core.gpio.gpio_config import (
    load_gpio_config, MODE_OUT_HIGH, MODE_OUT_LOW,
    MODE_IN_PULL_UP, MODE_IN_PULL_DOWN, OP_BITS, OFFSET_OUT_SET,
    OFFSET_DIR_SET, OFFSET_OUT_CLR, OFFSET_DIR_CLR,
    OFFSET_IN_READ, PINS_PER_GROUP
)

from ui.pages.gpio.gpio_control.utils import (
    _icon, _fmt32, _repolish, _write_bits_line
)

logger = get_logger(__name__)

class FeaturesMixin:
    """Sniffer / JSON Config / Export Manager / Confirm Note / AI 动作注册。"""

    def _sniff(self, kind, addr, data, semantic):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        parts = ["{0} [{1}]".format(ts, kind)]
        if addr is not None:
            parts.append("ADDR: {0}".format(_fmt32(addr)))
        if data is not None:
            parts.append("DATA: {0}".format(_fmt32(data)))
        parts.append(semantic)
        raw = "  ".join(parts)

        color = self._SNIFF_COLORS.get(kind, "#94A3B8")
        esc = semantic.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = (
            '<span style="color:#475569">{0}</span> '
            '<span style="color:{1};font-weight:600">[{2}]</span> '.format(ts, color, kind))
        if addr is not None:
            html += '<span style="color:#22D3EE">ADDR: {0}</span> '.format(_fmt32(addr))
        if data is not None:
            html += '<span style="color:#F59E0B">DATA: {0}</span> '.format(_fmt32(data))
        html += '<span style="color:#94A3B8">{0}</span>'.format(esc)
        self._sniff_entries.append((kind, raw, html))
        if not self._sniff_paused and self._sniff_match(kind, raw):
            self.sniff_view.append(html)
            self._sniff_scroll_bottom()

    def _sniff_match(self, kind, raw):
        if self._sniff_kind and kind != self._sniff_kind:
            return False
        text = self.sniff_search.text().strip().lower()
        if text and text not in raw.lower():
            return False
        return True

    def _sniff_scroll_bottom(self):
        sb = self.sniff_view.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _render_sniffer(self):
        self.sniff_view.clear()
        for kind, raw, html in self._sniff_entries:
            if self._sniff_match(kind, raw):
                self.sniff_view.append(html)
        self._sniff_scroll_bottom()

    def _on_sniff_kind_changed(self, idx):
        self._sniff_kind = None if idx < 0 else self.SNIFF_KINDS[idx]
        self._render_sniffer()

    def _on_sniff_pause(self, paused):
        self._sniff_paused = paused
        self.sniff_pause_btn.setText("Resume" if paused else "Pause")
        if not paused:
            self._render_sniffer()

    def _on_sniff_clear(self):
        self._sniff_entries = []
        self.sniff_view.clear()

    def _on_sniff_export(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export I2C Sniffer Log",
            "gpio_i2c_sniffer_{0}.log".format(ts),
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("BES GPIO Workbench - I2C Bus Sniffer Log\n")
                f.write("Chip: {0}  Mode: USB-I2C Bridge\n".format(
                    self._cfg.chip if self._cfg else "--"))
                for _kind, raw, _html in self._sniff_entries:
                    f.write(raw + "\n")
            self.append_log("[EXPORT] Sniffer log exported: {0}".format(path))
        except OSError as e:
            logger.error("sniffer export failed: %s", e, exc_info=True)
            self.append_log("[ERROR] Sniffer log export failed: {0}".format(e))

    def _describe_write(self, op, addr, value, hi, lo):
        cfg = self._cfg
        if cfg is not None:
            for bank in cfg.banks:
                off = addr - bank.base
                if off == OFFSET_OUT_SET:
                    return "Output control (set): Write 1 to be HIGH -> {0}".format(
                        self._mask_pins(value))
                if off == OFFSET_OUT_CLR:
                    return "Output control (clr): Write 1 to be LOW -> {0}".format(
                        self._mask_pins(value))
                if off == OFFSET_DIR_SET:
                    return "Dir control (set): Write 1 to be OUTPUT -> {0}".format(
                        self._mask_pins(value))
                if off == OFFSET_DIR_CLR:
                    return "Dir control (clr): Write 1 to be INPUT -> {0}".format(
                        self._mask_pins(value))
            for b_idx in range(len(cfg.banks)):
                pu = cfg.pull_up_bases[b_idx] if b_idx < len(cfg.pull_up_bases) else None
                pd = cfg.pull_down_bases[b_idx] if b_idx < len(cfg.pull_down_bases) else None
                if pu is not None and addr == pu:
                    return "Pull-up enable (RMW [{0}:{1}] = {2}) -> {3}".format(
                        hi, lo, value, self._mask_pins(
                            ((value & ((1 << (hi - lo + 1)) - 1)) << lo)))
                if pd is not None and addr == pd:
                    return "Pull-down enable (RMW [{0}:{1}] = {2}) -> {3}".format(
                        hi, lo, value, self._mask_pins(
                            ((value & ((1 << (hi - lo + 1)) - 1)) << lo)))
            g = cfg.func_sel_reg_group(addr)
            if g is not None:
                if lo == 0 and hi == 31:
                    return "Func sel: [31:0] = {0} -> Group{1} all 8 pins".format(
                        _fmt32(value), g)
                pin = lo // cfg.func_sel_bits_per_gpio
                if pin < PINS_PER_GROUP:
                    fname = cfg.func_name(g, pin, value)
                    tag = " ({0})".format(fname) if fname else ""
                    return "Func sel: [{0}:{1}] = 0x{2:X}{3} -> {4}".format(
                        hi, lo, value, tag, cfg.gpio_name(g, pin))
            if cfg.drv_supported:
                owner = cfg.drv_field_owner(addr, lo)
                if owner is not None:
                    g, p = owner
                    ohm = self._drv_ohm_text(value)
                    return "Drv strength: [{0}:{1}] = Lv{2}{3} -> {4}".format(
                        hi, lo, value,
                        " ({0})".format(ohm) if ohm else "",
                        cfg.gpio_name(g, p))
        if op == OP_BITS:
            return "Raw bits write [{0}:{1}] = 0x{2:X}".format(hi, lo, value)
        return "Raw register write"

    def _describe_read(self, addr, value):
        cfg = self._cfg
        if cfg is not None:
            for bank in cfg.banks:
                if addr == bank.base + OFFSET_IN_READ:
                    return "Input status read ({0} VAL_IN +0x50)".format(bank.name)
            for b_idx in range(len(cfg.banks)):
                pu = cfg.pull_up_bases[b_idx] if b_idx < len(cfg.pull_up_bases) else None
                pd = cfg.pull_down_bases[b_idx] if b_idx < len(cfg.pull_down_bases) else None
                if pu is not None and addr == pu:
                    return "Pull-up enable read (Bank{0})".format(b_idx)
                if pd is not None and addr == pd:
                    return "Pull-down enable read (Bank{0})".format(b_idx)
            g = cfg.func_sel_reg_group(addr)
            if g is not None:
                return "Func sel read (Group{0})".format(g)
            if cfg.drv_supported \
                    and any(a == addr for a, _ in cfg.drv_registers()):
                return "Drv strength read"
        return "Raw register read"

    # ================================================================ 执行管道

    def _config_path(self, chip_name):
        import chips
        return os.path.join(
            os.path.dirname(os.path.abspath(chips.__file__)),
            "gpio_configs", "{0}.json".format(chip_name.lower()))

    def _load_json_editor(self):
        self.json_err_label.setText("")
        if self._cfg is None:
            self.json_edit.setPlainText("")
            self.json_file_label.setText("chips/gpio_configs/--.json")
            self._json_path = None
            return
        path = self._config_path(self._cfg.chip)
        self._json_path = path
        self.json_file_label.setText(
            "chips/gpio_configs/{0}.json".format(self._cfg.chip.lower()))
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.json_edit.setPlainText(f.read())
        except OSError as e:
            logger.error("read gpio json failed: %s", e, exc_info=True)
            self.json_edit.setPlainText("")
            self.json_err_label.setText("Read failed: {0}".format(e))

    def _on_json_reload(self):
        self._load_json_editor()
        self.append_log("[INFO] JSON config reloaded from disk")

    def _on_json_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Chip JSON Config", "", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.json_edit.setPlainText(f.read())
            self.json_err_label.setText("")
            self.append_log(
                "[INFO] JSON imported: {0} "
                "(not applied; Apply Config to take effect)".format(path))
        except OSError as e:
            logger.error("import gpio json failed: %s", e, exc_info=True)
            self.json_err_label.setText("Import failed: {0}".format(e))

    def _on_json_export(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        chip = self._cfg.chip.lower() if self._cfg else "dut"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chip JSON Config",
            "{0}_gpio_config_{1}.json".format(chip, ts),
            "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.json_edit.toPlainText())
            self.append_log("[EXPORT] JSON config exported: {0}".format(path))
        except OSError as e:
            logger.error("export gpio json failed: %s", e, exc_info=True)
            self.json_err_label.setText("Export failed: {0}".format(e))

    def _on_json_apply(self):
        text = self.json_edit.toPlainText()
        try:
            raw = json.loads(text)
        except ValueError as e:
            self.json_err_label.setText("JSON syntax error: {0}".format(e))
            self.append_log("[ERROR] JSON syntax validation failed: {0}".format(e))
            return
        banks = raw.get("gpio_banks")
        if not isinstance(banks, list) or not banks:
            self.json_err_label.setText("Validation failed: gpio_banks missing or empty")
            return
        chip = str(raw.get("chip") or self.profile_combo.currentData() or "dut")
        path = self._config_path(chip)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
                f.write("\n")
        except OSError as e:
            logger.error("apply gpio json failed: %s", e, exc_info=True)
            self.json_err_label.setText("Write-back failed: {0}".format(e))
            self.append_log("[ERROR] JSON write-back failed: {0}".format(e))
            return
        self.json_err_label.setText("")
        cfg = load_gpio_config(chip)
        if cfg is None:
            self.json_err_label.setText(
                "Config written but failed to parse; check fields")
            return
        self._cfg = cfg
        idx = self.profile_combo.findData(chip.lower())
        if idx < 0:
            self.profile_combo.addItem(chip.upper(), chip.lower())
            idx = self.profile_combo.findData(chip.lower())
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)
        self._reset_session_state()
        self._set_status("Config applied: {0} · {1} banks".format(chip, len(cfg.banks)),
                         ok=True)
        self.append_log("[I2C] Apply Config applied: {0}; "
                        "pin map and register map rebuilt".format(chip))
        self._sniff("CHIP_CHECK", None, None,
                    "Apply JSON Config -> {0}".format(chip))
        self._load_json_editor()
        self._refresh_all_views()
        self._start_read_all_banks()

    # ================================================================ Export Manager

    def _on_pin_context_menu(self, group, pin, pos):
        """Pin Matrix 卡片右键：Set Function 切换复用功能；Export Config 收集导出配置。"""
        if not self._ready():
            return
        self._on_pin_clicked(group, pin)
        menu = QMenu(self)
        fsub = menu.addMenu("Set Function")
        cur = self._func_sel_value(group, pin)
        options = self._cfg.func_options(group, pin)
        for value, fname in options:
            act = fsub.addAction(fname)
            act.setCheckable(True)
            act.setChecked(value == cur)
            act.triggered.connect(
                lambda checked=False, g=group, p=pin, v=value, n=fname:
                self._set_pin_function(g, p, v, n))
        fsub.setEnabled(bool(options))
        sub = menu.addMenu("Export Config")
        for label, mode in self.EXPORT_MODES:
            act = sub.addAction(label)
            if (mode in (MODE_IN_PULL_UP, MODE_IN_PULL_DOWN)
                    and not self._cfg.pull_supported(group)):
                act.setEnabled(False)
            act.triggered.connect(
                lambda checked=False, g=group, p=pin, m=mode:
                self._add_export_item(g, p, m))
        menu.exec(pos)

    def _set_pin_function(self, group, pin, value, fname):
        """Set Function：该脚 func sel 位域写为选定功能值（影子同步）。"""
        if not self._ready():
            return
        field_ = self._cfg.func_sel_field(group, pin)
        if field_ is None:
            return
        addr, high, low = field_
        name = self._cfg.gpio_name(group, pin)
        self._apply_actions(
            [(OP_BITS, addr, value, high, low)],
            label="{0} function -> {1}".format(name, fname))

    def _add_export_item(self, group, pin, mode):
        item = (group, pin, mode)
        name = self._cfg.gpio_name(group, pin)
        label = self._EXPORT_MODE_LABELS[mode]
        if item in self._export_items:
            self.append_log("[INFO] {0} ({1}) already in export list".format(name, label))
            return
        self._export_items.append(item)
        self._save_export_items()
        self._refresh_export_manager()
        self.append_log("[EXPORT] Added to export: {0} ({1})".format(name, label))

    def _remove_export_item(self, index):
        if not (0 <= index < len(self._export_items)):
            return
        group, pin, mode = self._export_items.pop(index)
        self._save_export_items()
        self._refresh_export_manager()
        self.append_log("[EXPORT] Removed from export: {0} ({1})".format(
            self._cfg.gpio_name(group, pin), self._EXPORT_MODE_LABELS[mode]))

    def _clear_export_items(self):
        if not self._export_items:
            return
        self._export_items = []
        self._save_export_items()
        self._refresh_export_manager()
        self.append_log("[EXPORT] Export list cleared")

    def _export_store_path(self):
        return os.path.join(get_user_data_dir("gpio"), "export_items.json")

    def _save_export_items(self):
        """导出列表按芯片持久化到 user_data（重开窗口自动恢复）。"""
        if self._cfg is None:
            return
        path = self._export_store_path()
        data = {}
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError) as e:
                logger.warning("读取 GPIO 导出列表存档失败: %s", e, exc_info=True)
        if not isinstance(data, dict):
            data = {}
        if self._export_items:
            data[self._cfg.chip] = [list(it) for it in self._export_items]
        else:
            data.pop(self._cfg.chip, None)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError as e:
            logger.warning("保存 GPIO 导出列表失败: %s", e, exc_info=True)

    def _load_export_items(self):
        """按当前芯片恢复导出列表（校验脚位范围 / mode / 上下拉支持）。"""
        if self._cfg is None:
            return []
        path = self._export_store_path()
        if not os.path.isfile(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            logger.warning("读取 GPIO 导出列表失败: %s", e, exc_info=True)
            return []
        raw = data.get(self._cfg.chip, []) if isinstance(data, dict) else []
        items = []
        for entry in raw if isinstance(raw, list) else []:
            try:
                group, pin, mode = entry
                group, pin = int(group), int(pin)
            except (TypeError, ValueError):
                continue
            if not (0 <= group < self._cfg.group_count
                    and 0 <= pin < PINS_PER_GROUP):
                continue
            if mode not in self._EXPORT_MODE_LABELS:
                continue
            if (mode in (MODE_IN_PULL_UP, MODE_IN_PULL_DOWN)
                    and not self._cfg.pull_supported(group)):
                continue
            item = (group, pin, mode)
            if item not in items:
                items.append(item)
        return items

    def _refresh_export_manager(self):
        has = self._cfg is not None and bool(self._export_items)
        self._export_panel.setVisible(has)
        if not has:
            return
        self._export_count.setText("({0})".format(len(self._export_items)))
        while self._export_list_lay.count():
            item = self._export_list_lay.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        for idx, (group, pin, mode) in enumerate(self._export_items):
            row = QFrame()
            row.setObjectName("exportRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 0, 4, 0)
            rl.setSpacing(6)
            name = QLabel(self._cfg.gpio_name(group, pin))
            name.setObjectName("pinName")
            rl.addWidget(name)
            mode_lb = QLabel(self._EXPORT_MODE_LABELS[mode])
            mode_lb.setObjectName("exportMode")
            rl.addWidget(mode_lb, 1)
            del_btn = QPushButton()
            del_btn.setObjectName("exportDel")
            del_btn.setIcon(_icon("x-close.svg", "#94A3B8", 10))
            del_btn.setToolTip("Remove from export list")
            del_btn.clicked.connect(
                lambda checked=False, i=idx: self._remove_export_item(i))
            rl.addWidget(del_btn)
            self._export_list_lay.addWidget(row)
        self._export_list_lay.addStretch(1)
        self._export_preview.setPlainText(self._gen_export_script())

    def _export_item_actions(self, group, pin, mode):
        """单脚导出/执行动作：func_sel 前置 +（输出模式清 PU/PD）+ 模式动作。"""
        actions = list(self._cfg.build_func_sel_actions(group, pin) or [])
        if mode in (MODE_OUT_HIGH, MODE_OUT_LOW):
            # 输出模式显式关闭上下拉，避免残留输入上下拉状态
            bit = self._cfg.bit_in_bank(group, pin)
            pu = self._cfg.pull_up_addr(group)
            pd = self._cfg.pull_down_addr(group)
            if pu is not None:
                actions.append((OP_BITS, pu, 0, bit, bit))
            if pd is not None:
                actions.append((OP_BITS, pd, 0, bit, bit))
        actions += self._cfg.build_mode_actions(group, pin, mode) or []
        return actions

    def _gen_export_script(self):
        """导出列表 -> 单段合并 WRITE_BITS 脚本。

        段名合并全部 GPIO 编号（如 GPIO05_62_63_Config，同脚去重）；
        每脚动作块前以 `  - //GPIO名_mode` 注释标注来源。
        """
        if self._cfg is None or not self._export_items:
            return ""
        lines = ["# WRITE_BITS <reg_addr_hex> <high_bit> <low_bit> <value_hex>"
                 "  # write specific bits"]
        names = list(dict.fromkeys(
            self._cfg.gpio_name(group, pin)
            for group, pin, _ in self._export_items))
        title = names[0] + "".join("_" + n[4:] for n in names[1:])
        lines.append(title + "_Config:")
        for group, pin, mode in self._export_items:
            lines.append("  - //{0}_{1}".format(
                self._cfg.gpio_name(group, pin), mode))
            for op, addr, value, hi, lo in self._export_item_actions(
                    group, pin, mode):
                lines.append("  - " + _write_bits_line(op, addr, value, hi, lo))
        return "\n".join(lines)

    def _on_export_exec(self):
        """Exec：导出列表全部 GPIO 状态经统一下发管道在 DUT 上执行一遍。"""
        if self._cfg is None or not self._export_items:
            return
        actions = []
        for group, pin, mode in self._export_items:
            actions += self._export_item_actions(group, pin, mode)
        names = ",".join(dict.fromkeys(
            self._cfg.gpio_name(group, pin)
            for group, pin, _ in self._export_items))
        self._apply_actions(
            actions,
            label="Exec export list ({0} items): {1}".format(
                len(self._export_items), names),
            on_done=lambda: self._defer_read(self._start_read_all_banks))

    def _on_export_copy(self):
        text = self._export_preview.toPlainText()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.append_log(
            "[EXPORT] GPIO config script copied to clipboard ({0} items)".format(
                len(self._export_items)))

    # ================================================================ 确认清单视图

    def _refresh_notes(self):
        cfg = self._cfg
        # 1. PU/PD 地址
        if cfg is None:
            self._note_bodies[0].setText(
                "Load a DUT config to show pull register address confirmation.")
            self._set_note_status(0, "--", False)
        else:
            lines = []
            all_ok = True
            for i in range(len(cfg.banks)):
                pu = cfg.pull_up_bases[i] if i < len(cfg.pull_up_bases) else None
                pd = cfg.pull_down_bases[i] if i < len(cfg.pull_down_bases) else None
                if pu is None or pd is None:
                    all_ok = False
                lines.append("Bank{0}: PU={1} PD={2}".format(
                    i,
                    _fmt32(pu) if pu is not None else "TBD",
                    _fmt32(pd) if pd is not None else "TBD"))
            self._note_bodies[0].setText(
                "PU/PD each have an independent register region (1bit/GPIO, "
                "parallel to gpio_banks); when address is null, the UI "
                "disables pull buttons automatically.\n" + "\n".join(lines))
            self._set_note_status(0, "Confirmed" if all_ok else "To Confirm (TBD)",
                                  all_ok)
        # 2. drv 档位与阻抗
        if cfg is None or not cfg.drv_supported:
            self._note_bodies[1].setText(
                "drv_sel not configured in current chip JSON.")
            self._set_note_status(1, "To Confirm", False)
        else:
            lines = ["Group{0}: {1}".format(first // PINS_PER_GROUP,
                                            _fmt32(addr))
                     for addr, first in cfg.drv_registers()]
            ohm_txt = ("0~{0} level output impedance table configured "
                       "(UI shows rounded Ω)."
                       .format(cfg.drv_max_level)
                       if cfg.drv_out_high_ohm and cfg.drv_out_low_ohm
                       else "No level impedance table configured "
                            "(level number only).")
            self._note_bodies[1].setText(
                "drv_sel per-group registers: each 32-bit register holds "
                "8 pins x {0}bit, pin N field [N*{0}+{1}:N*{0}], "
                "levels 0~{2} (lower ohm = stronger drive); non-contiguous "
                "addresses are listed explicitly via JSON group_bases.\n{3}\n{4}"
                .format(cfg.drv_bits_per_gpio, cfg.drv_bits_per_gpio - 1,
                        cfg.drv_max_level, "\n".join(lines), ohm_txt))
            self._set_note_status(1, "Confirmed", True)
        # 3. I2C 地址
        dev_txt = ("0x{0:02X}".format(self._dev_addr)
                   if self._dev_addr is not None else "--")
        self._note_bodies[2].setText(
            "Main-die 32-bit address space (GPIO registers at 0x4008xxxx); "
            "device address comes from main_die_i2c_addr returned by "
            "bes_chip_check() (0x11 / 0x31 adaptive), width fixed BIT_32.\n"
            "Current session dev = {0}.".format(dev_txt))
        self._set_note_status(
            2, "Connected" if self._dev_addr is not None else "Not Connected",
            self._dev_addr is not None)
        # 4. 桥接
        self._note_bodies[3].setText(
            "Current: USB-I2C physical fixture bridge (I2CInterface DLL, "
            "async via core/gpio/ Worker; no blocking I2C on the page).")
        self._set_note_status(3, "USB-I2C", True)
        # 5. func sel
        if cfg is None or not cfg.func_sel_supported:
            self._note_bodies[4].setText(
                "func_sel not configured in current chip JSON.")
            self._set_note_status(4, "To Confirm", False)
        else:
            per_reg = 32 // cfg.func_sel_bits_per_gpio
            n = cfg.func_sel_groups or cfg.group_count
            self._note_bodies[4].setText(
                "Pin function mux select: base {0}, each register holds "
                "{1} pins x {2}bit, valid Group0~{3}; before controlling "
                "GPIO state (direction/level/pull/drv/batch/mask), the page "
                "automatically writes the pin field to 0x{4:X} to select "
                "GPIO function, skipped when shadow is already 0x{4:X}.\n"
                "Note: RegMap bit flip / Raw are low-level debug entries "
                "without automatic func sel."
                .format(_fmt32(cfg.func_sel_base), per_reg,
                        cfg.func_sel_bits_per_gpio, n - 1,
                        cfg.func_sel_gpio_value))
            self._set_note_status(4, "Confirmed", True)

    def _set_note_status(self, idx, text, ok):
        lbl = self._note_status_labels[idx]
        lbl.setText(text)
        lbl.setProperty("ok", "1" if ok else "0")
        _repolish(lbl)

    # ================================================================ 通用

    def _register_ai_ui_actions(self):
        """§5b.5：登记本页无专用接口的按钮为 AI 可触发的具名 UI 动作。

        handler 直接复用按钮原 clicked.connect 的槽，行为与人点完全一致；
        仅登记只读 / 会话状态类入口（Detect / Load Profile / Read / Poll /
        Sniffer 导出），引脚电平 / 方向 / 上下拉 / drv / Raw / Mask 等写 DUT
        硬件状态的操作不开放给 AI（引导用户手动或用 Export Config 脚本流）。
        enabled_when 不满足时 list_ui_actions 不返回、ui_invoke 明示不可用。
        """
        registry = self._ui_action_registry
        if registry is None:
            return

        def _wrap(label, fn):
            def _run() -> tuple[bool, str]:
                try:
                    fn()
                    return True, "{0} executed.".format(label)
                except Exception as exc:  # noqa: BLE001
                    logger.error("%s failed", label, exc_info=True)
                    return False, "{0} failed: {1}".format(label, exc)
            return _run

        def _idle_ready() -> bool:
            return self._ready() and not self._busy()

        registry.register_many([
            UIActionSpec(
                id="gpio.detect",
                label="Detect DUT",
                page_key="gpio",
                handler=_wrap("Detect DUT", self._on_detect_clicked),
                risk="low",
                confirm=False,
                enabled_when=lambda: not self._busy(),
                description=(
                    "Run i2c.bes_chip_check(): identify the connected BES chip, "
                    "load its GPIO config and auto read back all pin states. "
                    "Required before any other GPIO operation."
                ),
            ),
            UIActionSpec(
                id="gpio.load_profile",
                label="Load Profile",
                page_key="gpio",
                handler=_wrap("Load Profile", self._on_load_profile_clicked),
                risk="low",
                confirm=False,
                enabled_when=lambda: self._dev_addr is not None
                and not self._busy(),
                description=(
                    "Load the DUT Profile selected in the profile combo and "
                    "read back all banks. Requires Detect DUT first."
                ),
            ),
            UIActionSpec(
                id="gpio.read_all",
                label="Read All",
                page_key="gpio",
                handler=_wrap("Read All", self._start_read_all_banks),
                risk="low",
                confirm=False,
                enabled_when=_idle_ready,
                description=(
                    "Read back all banks: 0x50 input levels + PU/PD + drv + "
                    "func_sel, syncing shadows and pin cards."
                ),
            ),
            UIActionSpec(
                id="gpio.refresh_regmap",
                label="Refresh RegMap",
                page_key="gpio",
                handler=_wrap("Refresh RegMap", self._on_refresh_readable),
                risk="low",
                confirm=False,
                enabled_when=_idle_ready,
                description=(
                    "Re-read all readable registers of the current bank "
                    "(input level + PU/PD + drv/func_sel cards)."
                ),
            ),
            UIActionSpec(
                id="gpio.poll_toggle",
                label="Start / Stop Poll",
                page_key="gpio",
                handler=_wrap("Poll toggle", self._on_poll_toggled),
                risk="low",
                confirm=False,
                enabled_when=lambda: self._poll_timer.isActive() or _idle_ready(),
                description=(
                    "Toggle periodic polling of the current bank input level "
                    "register (0x50) at the interval selected in the poll combo."
                ),
            ),
            UIActionSpec(
                id="gpio.sniff_export",
                label="Export Sniffer Log",
                page_key="gpio",
                handler=_wrap("Export Sniffer Log", self._on_sniff_export),
                risk="low",
                confirm=False,
                enabled_when=lambda: bool(self._sniff_entries),
                description=(
                    "Export the Sniffer view entries (I2C traffic captured by "
                    "this page) to a log file. Requires at least one entry."
                ),
            ),
        ])
