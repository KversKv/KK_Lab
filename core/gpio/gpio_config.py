#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DUT GPIO 配置加载与寄存器地址计算（纯 Python，无 Qt，可单测）。

JSON 配置位于 chips/gpio_configs/<chip_name>.json，按 bes_chip_check()
返回的 chip_name（如 "bes1701"）匹配加载。

bank 内寄存器偏移（各组一致，硬约定）：
    Out Set    = base + 0x00   写 1 输出高
    Dir Set    = base + 0x04   写 1 设为输出
    Out Clr    = base + 0x0C   写 1 输出低
    Dir Clr    = base + 0x10   写 1 设为输入
    Input Read = base + 0x50   读输入电平
每 bank 32 个 GPIO（Group x4 ~ x4+3），bit = (group % 4) * 8 + pin。

drv_sel 独立地址区：从 drv.base 起每 32bit 寄存器连续排布，
bits_per_gpio=2 → 每寄存器 16 个 GPIO；bits_per_gpio=4 → 每寄存器 8 个。
字段地址 = base + (linear // per_reg) * 4，
位域 = [(linear % per_reg) * bits + bits - 1 : (linear % per_reg) * bits]，
linear = group * 8 + pin。

上下拉为两个独立地址区（PU / PD 各一），与 gpio_banks 平行按 bank 给基地址，
每 bank 一个 32bit 寄存器、1 bit/GPIO（1=使能），位序与 GPIO bit 一致。
"""

import json
import os
from dataclasses import dataclass, field

from log_config import get_logger

logger = get_logger(__name__)

# bank 内寄存器偏移（所有组一致）
OFFSET_OUT_SET = 0x00
OFFSET_DIR_SET = 0x04
OFFSET_OUT_CLR = 0x0C
OFFSET_DIR_CLR = 0x10
OFFSET_IN_READ = 0x50

PINS_PER_GROUP = 8
GROUPS_PER_BANK = 4
GPIOS_PER_BANK = PINS_PER_GROUP * GROUPS_PER_BANK  # 32

# GPIO 工作模式
MODE_OUT_HIGH = "out_high"
MODE_OUT_LOW = "out_low"
MODE_IN_FLOAT = "in_float"        # 输入高阻（无上下拉）
MODE_IN_PULL_UP = "in_pull_up"
MODE_IN_PULL_DOWN = "in_pull_down"

_MODE_LABELS = {
    MODE_OUT_HIGH: "Output High",
    MODE_OUT_LOW: "Output Low",
    MODE_IN_FLOAT: "Input Hi-Z",
    MODE_IN_PULL_UP: "Input Pull-Up",
    MODE_IN_PULL_DOWN: "Input Pull-Down",
}

# Worker 动作类型（op, addr, value, high_bit, low_bit）
OP_WRITE = "write"    # 整寄存器写（set/clear 寄存器，无需 RMW）
OP_BITS = "bits"      # 位域写（DLL 内部 read-modify-write）


def mode_label(mode):
    return _MODE_LABELS.get(mode, mode or "-")


@dataclass
class GpioBank:
    name: str
    base: int


@dataclass
class GpioChipConfig:
    chip: str
    banks: list = field(default_factory=list)          # list[GpioBank]
    drv_base: int = None
    drv_bits_per_gpio: int = 2
    drv_fast: int = 3
    drv_slow: int = 0
    pull_up_bases: list = field(default_factory=list)   # list[int|None] 与 banks 平行
    pull_down_bases: list = field(default_factory=list)

    # ---- 基本映射 ----

    @property
    def group_count(self):
        return len(self.banks) * GROUPS_PER_BANK

    @staticmethod
    def gpio_name(group, pin):
        """扁平命名：Group0 → GPIO00~07，Group1 → GPIO10~17，…"""
        return "GPIO{0}{1}".format(group, pin)

    @staticmethod
    def bank_index(group):
        return group // GROUPS_PER_BANK

    @staticmethod
    def bit_in_bank(group, pin):
        return (group % GROUPS_PER_BANK) * PINS_PER_GROUP + pin

    @staticmethod
    def linear_index(group, pin):
        return group * PINS_PER_GROUP + pin

    def bank(self, group):
        return self.banks[self.bank_index(group)]

    # ---- bank 寄存器地址 ----

    def out_set_addr(self, group):
        return self.bank(group).base + OFFSET_OUT_SET

    def out_clr_addr(self, group):
        return self.bank(group).base + OFFSET_OUT_CLR

    def dir_set_addr(self, group):
        return self.bank(group).base + OFFSET_DIR_SET

    def dir_clr_addr(self, group):
        return self.bank(group).base + OFFSET_DIR_CLR

    def in_read_addr(self, group):
        return self.bank(group).base + OFFSET_IN_READ

    # ---- drv_sel 位域 ----

    @property
    def drv_supported(self):
        return self.drv_base is not None

    def drv_field(self, group, pin):
        """返回 (addr, high_bit, low_bit)；不支持时返回 None。"""
        if self.drv_base is None:
            return None
        per_reg = 32 // self.drv_bits_per_gpio
        idx = self.linear_index(group, pin)
        addr = self.drv_base + (idx // per_reg) * 4
        low = (idx % per_reg) * self.drv_bits_per_gpio
        return addr, low + self.drv_bits_per_gpio - 1, low

    # ---- 上下拉地址 ----

    def pull_up_addr(self, group):
        idx = self.bank_index(group)
        if idx < len(self.pull_up_bases):
            return self.pull_up_bases[idx]
        return None

    def pull_down_addr(self, group):
        idx = self.bank_index(group)
        if idx < len(self.pull_down_bases):
            return self.pull_down_bases[idx]
        return None

    def pull_supported(self, group):
        return (self.pull_up_addr(group) is not None
                and self.pull_down_addr(group) is not None)

    # ---- 动作构造（供 Worker 执行） ----

    def build_mode_actions(self, group, pin, mode):
        """构造设置某 GPIO 工作模式的寄存器动作列表。

        返回 [(op, addr, value, high_bit, low_bit), ...]；
        模式需要上下拉但 JSON 未配置地址时返回 None。
        """
        bit = self.bit_in_bank(group, pin)
        mask = 1 << bit
        actions = []
        if mode == MODE_OUT_HIGH:
            actions.append((OP_WRITE, self.dir_set_addr(group), mask, -1, -1))
            actions.append((OP_WRITE, self.out_set_addr(group), mask, -1, -1))
        elif mode == MODE_OUT_LOW:
            actions.append((OP_WRITE, self.dir_set_addr(group), mask, -1, -1))
            actions.append((OP_WRITE, self.out_clr_addr(group), mask, -1, -1))
        elif mode in (MODE_IN_FLOAT, MODE_IN_PULL_UP, MODE_IN_PULL_DOWN):
            actions.append((OP_WRITE, self.dir_clr_addr(group), mask, -1, -1))
            if mode == MODE_IN_FLOAT:
                # 高阻 = PU/PD 均关闭；地址未配置时退化为仅切输入
                pu = self.pull_up_addr(group)
                pd = self.pull_down_addr(group)
                if pu is not None:
                    actions.append((OP_BITS, pu, 0, bit, bit))
                if pd is not None:
                    actions.append((OP_BITS, pd, 0, bit, bit))
            else:
                if not self.pull_supported(group):
                    return None
                pu = self.pull_up_addr(group)
                pd = self.pull_down_addr(group)
                if mode == MODE_IN_PULL_UP:
                    actions.append((OP_BITS, pd, 0, bit, bit))
                    actions.append((OP_BITS, pu, 1, bit, bit))
                else:
                    actions.append((OP_BITS, pu, 0, bit, bit))
                    actions.append((OP_BITS, pd, 1, bit, bit))
        else:
            return None
        return actions

    def build_drv_actions(self, group, pin, fast):
        """构造驱动速率设置动作；不支持时返回 None。"""
        field_ = self.drv_field(group, pin)
        if field_ is None:
            return None
        addr, high, low = field_
        value = self.drv_fast if fast else self.drv_slow
        return [(OP_BITS, addr, value, high, low)]


def _parse_int(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return int(str(value).strip(), 0)


def _config_dir():
    import chips
    return os.path.join(os.path.dirname(os.path.abspath(chips.__file__)),
                        "gpio_configs")


def list_gpio_config_chips():
    """列出已有 GPIO JSON 配置的芯片名。"""
    cfg_dir = _config_dir()
    names = []
    try:
        for fname in os.listdir(cfg_dir):
            if fname.lower().endswith(".json"):
                names.append(os.path.splitext(fname)[0])
    except OSError:
        logger.error("GPIO 配置目录不可读: %s", cfg_dir, exc_info=True)
    return sorted(names)


def load_gpio_config(chip_name):
    """按芯片名加载 GPIO 配置；无配置或解析失败返回 None。"""
    if not chip_name:
        return None
    path = os.path.join(_config_dir(), "{0}.json".format(chip_name.lower()))
    if not os.path.isfile(path):
        logger.warning("GPIO 配置不存在: %s", path)
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        banks = [GpioBank(name=str(b.get("name", "BANK{0}".format(i))),
                          base=_parse_int(b.get("base")))
                 for i, b in enumerate(raw.get("gpio_banks", []))]
        banks = [b for b in banks if b.base is not None]
        if not banks:
            logger.error("GPIO 配置无有效 bank: %s", path)
            return None
        drv = raw.get("drv") or {}
        cfg = GpioChipConfig(
            chip=str(raw.get("chip") or chip_name),
            banks=banks,
            drv_base=_parse_int(drv.get("base")),
            drv_bits_per_gpio=int(drv.get("bits_per_gpio", 2) or 2),
            drv_fast=int(drv.get("fast", 3)),
            drv_slow=int(drv.get("slow", 0)),
            pull_up_bases=[_parse_int(v)
                           for v in raw.get("pull_up_bases", [])],
            pull_down_bases=[_parse_int(v)
                             for v in raw.get("pull_down_bases", [])],
        )
        if cfg.drv_bits_per_gpio not in (2, 4):
            logger.error("drv bits_per_gpio 非法: %s", cfg.drv_bits_per_gpio)
            return None
        return cfg
    except Exception:
        logger.error("GPIO 配置解析失败: %s", path, exc_info=True)
        return None


__all__ = [
    "GpioBank", "GpioChipConfig", "load_gpio_config", "list_gpio_config_chips",
    "mode_label",
    "MODE_OUT_HIGH", "MODE_OUT_LOW", "MODE_IN_FLOAT",
    "MODE_IN_PULL_UP", "MODE_IN_PULL_DOWN",
    "OP_WRITE", "OP_BITS",
    "OFFSET_OUT_SET", "OFFSET_DIR_SET", "OFFSET_OUT_CLR", "OFFSET_DIR_CLR",
    "OFFSET_IN_READ", "PINS_PER_GROUP", "GROUPS_PER_BANK", "GPIOS_PER_BANK",
]
