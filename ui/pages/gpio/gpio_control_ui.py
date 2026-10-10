#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DUT GPIO 控制页。

经 USB-I2C 直操作 BES 芯片 AON GPIO 寄存器：
Detect DUT（bes_chip_check）→ 按 chip_name 加载 chips/gpio_configs/<chip>.json
→ 展示全部 GPIO → 点击单个 GPIO 设置 输出高/低、输入高阻/上拉/下拉、
驱动速率，或回读输入电平。

铁律：页面不做阻塞 I2C，所有读写走 core/gpio/ Worker（QThread）。
"""

import sys
import os

if not getattr(sys, "frozen", False):
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QFrame, QGroupBox, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QThread, QTimer

from log_config import get_logger
from ui.widgets.dark_combobox import DarkComboBox
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from core.gpio.gpio_config import (
    load_gpio_config, mode_label,
    MODE_OUT_HIGH, MODE_OUT_LOW, MODE_IN_FLOAT,
    MODE_IN_PULL_UP, MODE_IN_PULL_DOWN,
    PINS_PER_GROUP, GROUPS_PER_BANK,
)
from core.gpio.gpio_workers import (
    GpioChipCheckWorker, GpioReadBanksWorker, GpioApplyWorker,
)

logger = get_logger(__name__)

_GPIO_PAGE_QSS = """
QWidget#gpioPage {
    background-color: #020817;
    color: #dbe7ff;
}
QLabel {
    background-color: transparent;
    color: #dbe7ff;
    border: none;
}
QLabel#gpioTitle {
    font-size: 15px;
    font-weight: 700;
}
QLabel#gpioStatus { color: #7b93bf; }
QLabel#gpioStatus[ok="1"] { color: #15d1a3; }
QLabel#gpioStatus[err="1"] { color: #ff5e7a; }
QGroupBox#gpioBank {
    background-color: #060f24;
    border: 1px solid #17345f;
    border-radius: 8px;
    margin-top: 18px;
    font-weight: 600;
    color: #9db4dd;
}
QGroupBox#gpioBank::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 2px 6px;
}
QLabel#gpioGroupName { color: #7b93bf; font-size: 11px; }
QPushButton#gpioPin {
    background-color: #0f1b33;
    color: #c7d5f2;
    border: 1px solid #22355c;
    border-radius: 4px;
    font-size: 10px;
    min-height: 24px;
    max-height: 24px;
    padding: 0px;
}
QPushButton#gpioPin:hover { border-color: #3d5a94; }
QPushButton#gpioPin[lvl="h"] { color: #7df0cd; border-color: #15d1a3; }
QPushButton#gpioPin[lvl="l"] { color: #8fa3cc; border-color: #33456b; }
QPushButton#gpioPin[mode="out_h"] {
    background-color: #3a2c10; color: #ffcf7d; border-color: #8a6420;
}
QPushButton#gpioPin[mode="out_l"] {
    background-color: #241f12; color: #b39a68; border-color: #57481f;
}
QPushButton#gpioPin[sel="1"] { border: 1px solid #7ea1ff; }
QFrame#gpioDetail {
    background-color: #060f24;
    border: 1px solid #17345f;
    border-radius: 8px;
}
QLabel#gpioPinName { font-size: 16px; font-weight: 700; color: #ffcf7d; }
QLabel#gpioPinInfo { color: #7b93bf; font-size: 11px; }
QLabel#gpioPinState { font-size: 12px; }
QPushButton#gpioAction {
    background-color: #123055;
    color: #cfe0ff;
    border: 1px solid #1f4d85;
    border-radius: 4px;
    min-height: 26px;
    max-height: 26px;
    padding: 0px 8px;
}
QPushButton#gpioAction:hover { background-color: #173d6b; }
QPushButton#gpioAction:disabled {
    background-color: #0b1428; color: #4a5a7c; border-color: #1a2a4a;
}
QPushButton#gpioTopBtn {
    background-color: #123055;
    color: #cfe0ff;
    border: 1px solid #1f4d85;
    border-radius: 4px;
    min-height: 24px;
    max-height: 24px;
    padding: 0px 12px;
}
QPushButton#gpioTopBtn:hover { background-color: #173d6b; }
QPushButton#gpioTopBtn:disabled {
    background-color: #0b1428; color: #4a5a7c; border-color: #1a2a4a;
}
"""

_SPEED_OPTIONS = None  # [(I2CSpeedMode, label), ...] 懒加载


def _speed_options():
    global _SPEED_OPTIONS
    if _SPEED_OPTIONS is None:
        from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
        _SPEED_OPTIONS = [
            (I2CSpeedMode.SPEED_20K, "20 kHz"),
            (I2CSpeedMode.SPEED_100K, "100 kHz"),
            (I2CSpeedMode.SPEED_400K, "400 kHz"),
            (I2CSpeedMode.SPEED_750K, "750 kHz"),
        ]
    return _SPEED_OPTIONS


class GpioControlUI(QWidget):
    """DUT GPIO 控制页：Detect DUT → GPIO 网格 → 单脚模式/电平/drv 控制。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gpioPage")
        self._cfg = None            # GpioChipConfig
        self._chip_info = None
        self._dev_addr = None
        self._selected = None       # (group, pin)
        self._pin_buttons = {}      # (group, pin) -> QPushButton
        self._pin_state = {}        # (group, pin) -> {"mode": str|None, "level": int|None}
        self._thread = None
        self._worker = None
        self._build_ui()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        self.setStyleSheet(_GPIO_PAGE_QSS)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        root.addLayout(self._build_top_bar())

        main = QHBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(8)

        self._banks_scroll = QScrollArea()
        self._banks_scroll.setWidgetResizable(True)
        self._banks_scroll.setFrameShape(QFrame.NoFrame)
        self._banks_placeholder = QLabel("请先点击 Detect DUT 识别芯片并加载 GPIO 配置")
        self._banks_placeholder.setObjectName("gpioStatus")
        self._banks_placeholder.setAlignment(Qt.AlignCenter)
        self._banks_scroll.setWidget(self._banks_placeholder)
        main.addWidget(self._banks_scroll, 1)

        main.addWidget(self._build_detail_panel())

        main_frame = QFrame()
        main_frame.setLayout(main)
        self._splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            main_frame, title="Activity Logs", show_progress=False,
            stretch=(4, 1))
        root.addWidget(self._splitter, 1)

        self.append_log("[INFO] DUT GPIO 页面已初始化，请先 Detect DUT")

    def _build_top_bar(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        title = QLabel("DUT GPIO")
        title.setObjectName("gpioTitle")
        row.addWidget(title)
        row.addSpacing(12)

        row.addWidget(QLabel("Speed"))
        self.speed_combo = DarkComboBox()
        for mode, label in _speed_options():
            self.speed_combo.addItem(label, mode)
        self.speed_combo.setCurrentIndex(1)  # 100 kHz
        row.addWidget(self.speed_combo)

        self.detect_btn = QPushButton("Detect DUT")
        self.detect_btn.setObjectName("gpioTopBtn")
        self.detect_btn.clicked.connect(self._on_detect_clicked)
        row.addWidget(self.detect_btn)

        self.refresh_btn = QPushButton("Refresh All")
        self.refresh_btn.setObjectName("gpioTopBtn")
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.clicked.connect(self._on_refresh_all_clicked)
        row.addWidget(self.refresh_btn)

        row.addSpacing(12)
        self.status_label = QLabel("未检测")
        self.status_label.setObjectName("gpioStatus")
        row.addWidget(self.status_label)
        row.addStretch(1)
        return row

    def _build_detail_panel(self):
        panel = QFrame()
        panel.setObjectName("gpioDetail")
        panel.setFixedWidth(250)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(6)

        self.detail_name = QLabel("未选择 GPIO")
        self.detail_name.setObjectName("gpioPinName")
        lay.addWidget(self.detail_name)

        self.detail_info = QLabel("-")
        self.detail_info.setObjectName("gpioPinInfo")
        lay.addWidget(self.detail_info)

        self.detail_state = QLabel("")
        self.detail_state.setObjectName("gpioPinState")
        lay.addWidget(self.detail_state)

        lay.addSpacing(6)
        self._mode_buttons = {}
        for mode in (MODE_OUT_HIGH, MODE_OUT_LOW, MODE_IN_FLOAT,
                     MODE_IN_PULL_UP, MODE_IN_PULL_DOWN):
            btn = QPushButton(mode_label(mode))
            btn.setObjectName("gpioAction")
            btn.setEnabled(False)
            btn.clicked.connect(
                lambda _=False, m=mode: self._on_mode_clicked(m))
            self._mode_buttons[mode] = btn
            lay.addWidget(btn)

        lay.addSpacing(4)
        drv_row = QHBoxLayout()
        drv_row.setSpacing(6)
        drv_row.addWidget(QLabel("Drv"))
        self.drv_slow_btn = QPushButton("Slow")
        self.drv_slow_btn.setObjectName("gpioAction")
        self.drv_slow_btn.setEnabled(False)
        self.drv_slow_btn.clicked.connect(lambda: self._on_drv_clicked(False))
        drv_row.addWidget(self.drv_slow_btn)
        self.drv_fast_btn = QPushButton("Fast")
        self.drv_fast_btn.setObjectName("gpioAction")
        self.drv_fast_btn.setEnabled(False)
        self.drv_fast_btn.clicked.connect(lambda: self._on_drv_clicked(True))
        drv_row.addWidget(self.drv_fast_btn)
        lay.addLayout(drv_row)

        self.read_btn = QPushButton("Read Level")
        self.read_btn.setObjectName("gpioAction")
        self.read_btn.setEnabled(False)
        self.read_btn.clicked.connect(self._on_read_pin_clicked)
        lay.addWidget(self.read_btn)

        lay.addStretch(1)
        return panel

    # ------------------------------------------------------------ 网格构建

    def _rebuild_banks(self):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)
        self._pin_buttons.clear()

        for bank_idx, bank in enumerate(self._cfg.banks):
            box = QGroupBox("{0}  (base 0x{1:08X})".format(bank.name, bank.base))
            box.setObjectName("gpioBank")
            grid = QGridLayout()
            grid.setContentsMargins(10, 4, 10, 10)
            grid.setSpacing(4)
            for g_in_bank in range(GROUPS_PER_BANK):
                group = bank_idx * GROUPS_PER_BANK + g_in_bank
                name = QLabel("Group{0}".format(group))
                name.setObjectName("gpioGroupName")
                grid.addWidget(name, g_in_bank, 0)
                for pin in range(PINS_PER_GROUP):
                    btn = QPushButton(self._cfg.gpio_name(group, pin))
                    btn.setObjectName("gpioPin")
                    btn.setFixedWidth(58)
                    btn.setProperty("lvl", "x")
                    btn.setProperty("sel", "0")
                    btn.clicked.connect(
                        lambda _=False, g=group, p=pin: self._on_pin_clicked(g, p))
                    bit = self._cfg.bit_in_bank(group, pin)
                    btn.setToolTip(
                        "{0} · {1} bit{2}".format(
                            self._cfg.gpio_name(group, pin), bank.name, bit))
                    grid.addWidget(btn, g_in_bank, pin + 1)
                    self._pin_buttons[(group, pin)] = btn
                    self._pin_state[(group, pin)] = {"mode": None, "level": None}
            box.setLayout(grid)
            vbox.addWidget(box)
        vbox.addStretch(1)

        old = self._banks_scroll.takeWidget()
        if old is not None:
            old.deleteLater()
        self._banks_scroll.setWidget(container)

    # ------------------------------------------------------------ 状态刷新

    def _update_pin_button(self, group, pin):
        btn = self._pin_buttons.get((group, pin))
        state = self._pin_state.get((group, pin))
        if btn is None or state is None:
            return
        mode_prop = {"out_high": "out_h", "out_low": "out_l"}.get(
            state["mode"], "in")
        if state["mode"] is None:
            mode_prop = "none"
        btn.setProperty("mode", mode_prop)
        btn.setProperty("lvl", {0: "l", 1: "h"}.get(state["level"], "x"))
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _update_detail_panel(self):
        sel = self._selected
        has = sel is not None and self._cfg is not None
        if not has:
            self.detail_name.setText("未选择 GPIO")
            self.detail_info.setText("-")
            self.detail_state.setText("")
        else:
            group, pin = sel
            state = self._pin_state.get(sel, {"mode": None, "level": None})
            bank = self._cfg.bank(group)
            bit = self._cfg.bit_in_bank(group, pin)
            self.detail_name.setText(self._cfg.gpio_name(group, pin))
            self.detail_info.setText(
                "{0} · Group{1} Pin{2} · bit{3}".format(
                    bank.name, group, pin, bit))
            level_txt = {0: "低", 1: "高"}.get(state["level"], "-")
            drv_txt = ""
            if self._cfg.drv_supported:
                drv_txt = "  |  Drv: {0}".format(state.get("drv") or "-")
            self.detail_state.setText(
                "电平: {0}  |  模式: {1}{2}".format(
                    level_txt, mode_label(state["mode"]), drv_txt))

        detected = self._cfg is not None and self._dev_addr is not None
        busy = self._thread is not None and self._thread.isRunning()
        for mode, btn in self._mode_buttons.items():
            ok = has and detected and not busy
            if ok and mode in (MODE_IN_PULL_UP, MODE_IN_PULL_DOWN):
                ok = self._cfg.pull_supported(sel[0])
            btn.setEnabled(ok)
        drv_ok = has and detected and not busy and self._cfg.drv_supported
        self.drv_slow_btn.setEnabled(drv_ok)
        self.drv_fast_btn.setEnabled(drv_ok)
        self.read_btn.setEnabled(has and detected and not busy)

    def _set_status(self, text, ok=False, err=False):
        self.status_label.setText(text)
        self.status_label.setProperty("ok", "1" if ok else "0")
        self.status_label.setProperty("err", "1" if err else "0")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def append_log(self, msg):
        self.execution_logs.append_log(msg)

    # ------------------------------------------------------------ 线程装配

    def _busy(self):
        return self._thread is not None and self._thread.isRunning()

    def _run_worker(self, worker, on_done, on_error):
        """装配并启动单次 Worker 线程（QObject + moveToThread）。"""
        if self._busy():
            return False
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        if hasattr(worker, "progress"):
            worker.progress.connect(self.append_log)
        if on_done is not None:
            worker.finished.connect(on_done)
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

    def _on_thread_cleanup(self):
        self._thread = None
        self._worker = None
        self._set_top_busy(False)
        self._update_detail_panel()

    def _set_top_busy(self, busy):
        self.detect_btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(
            not busy and self._cfg is not None and self._dev_addr is not None)

    def _on_op_error(self, msg):
        self.append_log("[ERR] {0}".format(msg))
        self._set_status("操作失败: {0}".format(msg), err=True)

    # ------------------------------------------------------------ 事件处理

    def _on_detect_clicked(self):
        if self._busy():
            return
        speed = self.speed_combo.currentData()
        self._set_status("检测中...")
        self.append_log("[I2C] BES 芯片检测中...")
        worker = GpioChipCheckWorker(None, speed)
        self._run_worker(worker, self._on_detect_done, self._on_op_error)

    def _on_detect_done(self, chip_info):
        self._chip_info = chip_info
        chip_name = chip_info.get("chip_name")
        main_die = chip_info.get("main_die")
        if chip_info.get("warning"):
            self.append_log("[WARN] {0}".format(chip_info["warning"]))
        if not main_die or not chip_info.get("main_die_i2c_addr"):
            self._cfg = None
            self._dev_addr = None
            self._set_status("Main-die 无法读取，请确认芯片已开机并处于非休眠状态",
                             err=True)
            self.append_log("[ERR] Main-die 检测失败")
            self._set_top_busy(False)
            return
        addr = chip_info["main_die_i2c_addr"]
        self._dev_addr = int(addr, 0) if isinstance(addr, str) else int(addr)
        self.append_log("[I2C] 检测结果: {0} {1} · dev=0x{2:02X}".format(
            main_die, chip_info.get("main_die_version") or "", self._dev_addr))

        self._cfg = load_gpio_config(chip_name)
        if self._cfg is None:
            self._set_status(
                "{0} · 无 GPIO 配置 chips/gpio_configs/{1}.json".format(
                    main_die, chip_name), err=True)
            self.append_log(
                "[WARN] 未找到芯片 {0} 的 GPIO 配置，请添加 "
                "chips/gpio_configs/{0}.json".format(chip_name))
            self._set_top_busy(False)
            return

        self._selected = None
        self._pin_state.clear()
        self._rebuild_banks()
        self._set_status("{0} {1} · dev 0x{2:02X} · {3} banks".format(
            main_die, chip_info.get("main_die_version") or "",
            self._dev_addr, len(self._cfg.banks)), ok=True)
        self.append_log("[I2C] GPIO 配置已加载: {0}（{1} banks / {2} GPIO）".format(
            self._cfg.chip, len(self._cfg.banks),
            len(self._cfg.banks) * 32))
        self._set_top_busy(False)
        self._update_detail_panel()
        # 检测完成后自动全量回读一轮输入电平（§26：延迟 ≥50ms 再起新线程）
        QTimer.singleShot(80, self._start_read_all_banks)

    def _on_refresh_all_clicked(self):
        if self._busy() or self._cfg is None:
            return
        self._start_read_all_banks()

    def _start_read_all_banks(self):
        if self._busy() or self._cfg is None or self._dev_addr is None:
            return
        read_list = [(i, self._cfg.banks[i].base + 0x50)
                     for i in range(len(self._cfg.banks))]
        self.append_log("[I2C] 回读全部 bank 输入电平...")
        worker = GpioReadBanksWorker(
            None, self.speed_combo.currentData(), self._dev_addr, read_list)
        self._run_worker(worker, self._on_banks_read, self._on_op_error)

    def _on_banks_read(self, values):
        for bank_idx, val in values.items():
            for g_in_bank in range(GROUPS_PER_BANK):
                group = bank_idx * GROUPS_PER_BANK + g_in_bank
                for pin in range(PINS_PER_GROUP):
                    bit = self._cfg.bit_in_bank(group, pin)
                    state = self._pin_state.get((group, pin))
                    if state is not None:
                        state["level"] = (val >> bit) & 1
                        self._update_pin_button(group, pin)
        self.append_log("[I2C] 输入电平已刷新")
        self._update_detail_panel()

    def _on_pin_clicked(self, group, pin):
        if self._selected is not None:
            old_btn = self._pin_buttons.get(self._selected)
            if old_btn is not None:
                old_btn.setProperty("sel", "0")
                old_btn.style().unpolish(old_btn)
                old_btn.style().polish(old_btn)
        self._selected = (group, pin)
        btn = self._pin_buttons.get((group, pin))
        if btn is not None:
            btn.setProperty("sel", "1")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._update_detail_panel()

    def _on_mode_clicked(self, mode):
        if self._busy() or self._selected is None or self._cfg is None:
            return
        group, pin = self._selected
        actions = self._cfg.build_mode_actions(group, pin, mode)
        name = self._cfg.gpio_name(group, pin)
        if actions is None:
            self.append_log(
                "[WARN] {0} {1} 需要上下拉地址，但 JSON 未配置 "
                "(pull_up/pull_down_bases)".format(name, mode_label(mode)))
            return
        self.append_log("[I2C] {0} → {1}".format(name, mode_label(mode)))
        worker = GpioApplyWorker(
            None, self.speed_combo.currentData(), self._dev_addr,
            actions, label=name)
        bank_idx = self._cfg.bank_index(group)
        self._run_worker(
            worker,
            lambda: self._on_apply_done(mode=mode, bank_idx=bank_idx),
            self._on_op_error)

    def _on_drv_clicked(self, fast):
        if self._busy() or self._selected is None or self._cfg is None:
            return
        group, pin = self._selected
        actions = self._cfg.build_drv_actions(group, pin, fast)
        name = self._cfg.gpio_name(group, pin)
        if actions is None:
            self.append_log("[WARN] {0} 不支持 drv 配置".format(name))
            return
        self.append_log("[I2C] {0} drv → {1}".format(
            name, "fast" if fast else "slow"))
        worker = GpioApplyWorker(
            None, self.speed_combo.currentData(), self._dev_addr,
            actions, label=name)
        self._run_worker(
            worker,
            lambda: self._on_drv_apply_done(fast),
            self._on_op_error)

    def _on_drv_apply_done(self, fast):
        if self._selected is not None:
            state = self._pin_state.get(self._selected)
            if state is not None:
                state["drv"] = "Fast" if fast else "Slow"
        self.append_log("[I2C] drv 设置完成")
        self._update_detail_panel()

    def _on_apply_done(self, mode, bank_idx):
        if self._selected is not None:
            state = self._pin_state.get(self._selected)
            if state is not None:
                state["mode"] = mode
                group, pin = self._selected
                self._update_pin_button(group, pin)
        self.append_log("[I2C] 模式设置完成")
        self._update_detail_panel()
        # 设置后回读该 bank 电平（§26：延迟 ≥50ms 再起新线程）
        QTimer.singleShot(80, lambda: self._start_read_bank(bank_idx))

    def _on_read_pin_clicked(self):
        if self._busy() or self._selected is None or self._cfg is None:
            return
        group, _pin = self._selected
        self._start_read_bank(self._cfg.bank_index(group))

    def _start_read_bank(self, bank_idx):
        if self._busy() or self._cfg is None or self._dev_addr is None:
            return
        bank = self._cfg.banks[bank_idx]
        worker = GpioReadBanksWorker(
            None, self.speed_combo.currentData(), self._dev_addr,
            [(bank_idx, bank.base + 0x50)])
        self._run_worker(worker, self._on_banks_read, self._on_op_error)

    # ------------------------------------------------------------ 收尾

    def closeEvent(self, event):
        try:
            if self._thread is not None and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(2000)
        except Exception:
            logger.error("GPIO page close wait failed", exc_info=True)
        super().closeEvent(event)
