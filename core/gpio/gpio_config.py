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

drv_sel 两种寻址方式（按 JSON 配置二选一）：
1. drv.group_bases：per-group 显式寄存器地址表（每寄存器 8 脚×bits_per_gpio），
   pin N 位域 = [N*bits+bits-1 : N*bits]，支持地址区不连续（如 BES1701）。
2. drv.base 线性模式：从 base 起每 32bit 寄存器连续排布，
   bits_per_gpio=2 → 每寄存器 16 个 GPIO；bits_per_gpio=4 → 每寄存器 8 个。
   字段地址 = base + (linear // per_reg) * 4，
   位域 = [(linear % per_reg) * bits + bits - 1 : (linear % per_reg) * bits]，
   linear = group * 8 + pin。
档位取值 0 ~ drv.levels-1（levels 缺省 = 2**bits_per_gpio）；
drv.out_high_ohm / out_low_ohm 为各档位输出阻抗表（可选，UI 取整显示）。

上下拉为两个独立地址区（PU / PD 各一），与 gpio_banks 平行按 bank 给基地址，
每 bank 一个 32bit 寄存器、1 bit/GPIO（1=使能），位序与 GPIO bit 一致。
pull_ohm.up / down 为输入上下拉阻抗（可选，UI 取整显示）。

func_sel（pin function 复用选择，可选）：控制 GPIO 状态前须先把对应脚的
sel 位域写为 func_sel.gpio_value（BES1701 = 0xF 选为 GPIO 功能）。
地址 = base + (linear // per_reg) * 4，位域排布同 drv 线性模式；
func_sel.groups 限制有效 group 数（0 = 不限制）。
func_sel.functions 为 iomux 复用功能表（可选）：键 "GPIO_P{G}_{P}"，
值为 [Func_0..Func_N] 名字列表，list index = sel 位域值，null = 该值未用；
UI 据此显示当前功能名并提供 Set Function 菜单。
"""

import json
import os
import re
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
    groups: int = GROUPS_PER_BANK   # 有效 group 数；高位 group 物理不存在时 < 4


@dataclass
class GpioChipConfig:
    chip: str
    banks: list = field(default_factory=list)          # list[GpioBank]
    drv_base: int = None
    drv_group_bases: list = field(default_factory=list)  # list[int|None] 按 group
    drv_bits_per_gpio: int = 2
    drv_levels: int = 0        # 0 → 2**bits_per_gpio
    drv_out_high_ohm: list = field(default_factory=list)  # 各档位输出阻抗（Ω）
    drv_out_low_ohm: list = field(default_factory=list)
    pull_up_ohm: float = None
    pull_down_ohm: float = None
    pull_up_bases: list = field(default_factory=list)   # list[int|None] 与 banks 平行
    pull_down_bases: list = field(default_factory=list)
    func_sel_base: int = None
    func_sel_bits_per_gpio: int = 4
    func_sel_gpio_value: int = 0xF
    func_sel_groups: int = 0     # 有效 group 数上限；0 = 不限制
    func_sel_functions: dict = field(default_factory=dict)  # (group,pin) -> [名字|None]，index=sel 值

    # ---- 基本映射 ----

    @property
    def group_count(self):
        return sum(b.groups for b in self.banks)

    def bank_group_count(self, bank_idx):
        """该 bank 有效 group 数（高位 group 不存在时 < GROUPS_PER_BANK）。"""
        if 0 <= bank_idx < len(self.banks):
            return self.banks[bank_idx].groups
        return GROUPS_PER_BANK

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
        return (self.drv_base is not None
                or any(a is not None for a in self.drv_group_bases))

    @property
    def drv_level_count(self):
        return self.drv_levels or (1 << self.drv_bits_per_gpio)

    @property
    def drv_max_level(self):
        return self.drv_level_count - 1

    def drv_reg(self, group, pin):
        """返回 (寄存器地址, 位域低位)；该脚不支持 drv 时返回 None。"""
        idx = self.linear_index(group, pin)
        if 0 <= group < len(self.drv_group_bases) \
                and self.drv_group_bases[group] is not None:
            return self.drv_group_bases[group], pin * self.drv_bits_per_gpio
        if self.drv_base is not None:
            per_reg = 32 // self.drv_bits_per_gpio
            return (self.drv_base + (idx // per_reg) * 4,
                    (idx % per_reg) * self.drv_bits_per_gpio)
        return None

    def drv_field(self, group, pin):
        """返回 (addr, high_bit, low_bit)；不支持时返回 None。"""
        reg = self.drv_reg(group, pin)
        if reg is None:
            return None
        addr, low = reg
        return addr, low + self.drv_bits_per_gpio - 1, low

    def drv_registers(self, bank_idx=None):
        """drv_sel 寄存器列表 [(addr, first_linear)]；bank_idx 限定该 bank。"""
        g0 = 0 if bank_idx is None else bank_idx * GROUPS_PER_BANK
        g1 = self.group_count if bank_idx is None \
            else g0 + self.bank_group_count(bank_idx)
        regs, seen = [], set()
        for g in range(g0, min(g1, self.group_count)):
            reg = self.drv_reg(g, 0)
            if reg is None or reg[0] in seen:
                continue
            seen.add(reg[0])
            regs.append((reg[0], g * PINS_PER_GROUP))
        return regs

    def drv_field_owner(self, addr, low_bit):
        """由寄存器地址与位域低位反查 (group, pin)；未命中返回 None。"""
        per_reg = 32 // self.drv_bits_per_gpio
        for reg_addr, first in self.drv_registers():
            if reg_addr == addr:
                idx = first + low_bit // self.drv_bits_per_gpio
                if idx < first + per_reg:
                    return divmod(idx, PINS_PER_GROUP)
        return None

    def drv_ohm(self, level):
        """该档位 (out_high_ohm, out_low_ohm)；未配置返回 (None, None)。"""
        hh = (self.drv_out_high_ohm[level]
              if 0 <= level < len(self.drv_out_high_ohm) else None)
        ll = (self.drv_out_low_ohm[level]
              if 0 <= level < len(self.drv_out_low_ohm) else None)
        return hh, ll

    # ---- func_sel 位域 ----

    @property
    def func_sel_supported(self):
        return self.func_sel_base is not None

    def func_sel_reg_group(self, addr):
        """由寄存器地址反查 group；未命中返回 None。"""
        if self.func_sel_base is None:
            return None
        delta = addr - self.func_sel_base
        if delta < 0 or delta % 4 != 0:
            return None
        per_reg = 32 // self.func_sel_bits_per_gpio
        group = (delta // 4) * per_reg // PINS_PER_GROUP
        if self.func_sel_groups and group >= self.func_sel_groups:
            return None
        return group

    def func_sel_field(self, group, pin):
        """返回 (addr, high_bit, low_bit)；未配置或超出范围返回 None。"""
        if self.func_sel_base is None:
            return None
        if self.func_sel_groups and group >= self.func_sel_groups:
            return None
        per_reg = 32 // self.func_sel_bits_per_gpio
        idx = self.linear_index(group, pin)
        addr = self.func_sel_base + (idx // per_reg) * 4
        low = (idx % per_reg) * self.func_sel_bits_per_gpio
        return addr, low + self.func_sel_bits_per_gpio - 1, low

    def build_func_sel_actions(self, group, pin):
        """构造 func sel 选为 GPIO 功能的动作；未配置时返回 None。"""
        field_ = self.func_sel_field(group, pin)
        if field_ is None:
            return None
        addr, high, low = field_
        return [(OP_BITS, addr, self.func_sel_gpio_value, high, low)]

    def func_name(self, group, pin, value):
        """该脚某 sel 值对应的功能名；gpio_value → "GPIO"，未配置/未命名 → None。"""
        if self.func_sel_base is None:
            return None
        if value == self.func_sel_gpio_value:
            return "GPIO"
        names = self.func_sel_functions.get((group, pin))
        if names and 0 <= value < len(names):
            return names[value]
        return None

    def func_options(self, group, pin):
        """该脚可选功能 [(value, name)]：GPIO 在前，后接已命名复用功能。"""
        if self.func_sel_field(group, pin) is None:
            return []
        options = [(self.func_sel_gpio_value, "GPIO")]
        names = self.func_sel_functions.get((group, pin)) or []
        options.extend(
            (i, name) for i, name in enumerate(names)
            if name and i != self.func_sel_gpio_value)
        return options

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

    def build_drv_actions(self, group, pin, level):
        """构造驱动强度档位设置动作（level 自动钳位 0~max）；不支持时返回 None。"""
        field_ = self.drv_field(group, pin)
        if field_ is None:
            return None
        addr, high, low = field_
        level = max(0, min(int(level), self.drv_max_level))
        return [(OP_BITS, addr, level, high, low)]


def _parse_int(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    return int(str(value).strip(), 0)


def _parse_func_sel_functions(raw):
    """解析 func_sel.functions：键 "GPIO_P{G}_{P}" → {(group, pin): [名字|None]}。"""
    functions = {}
    for key, names in (raw or {}).items():
        m = re.fullmatch(r"GPIO_P(\d+)_(\d+)", str(key).strip().upper())
        if not m or not isinstance(names, list):
            continue
        functions[(int(m.group(1)), int(m.group(2)))] = [
            str(n).strip() if n is not None and str(n).strip() else None
            for n in names]
    return functions


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
        banks = []
        for i, b in enumerate(raw.get("gpio_banks", [])):
            try:
                groups = int(b.get("groups", GROUPS_PER_BANK)
                             or GROUPS_PER_BANK)
            except (TypeError, ValueError):
                groups = GROUPS_PER_BANK
            groups = max(1, min(groups, GROUPS_PER_BANK))
            banks.append(GpioBank(name=str(b.get("name", "BANK{0}".format(i))),
                                  base=_parse_int(b.get("base")),
                                  groups=groups))
        banks = [b for b in banks if b.base is not None]
        if not banks:
            logger.error("GPIO 配置无有效 bank: %s", path)
            return None
        drv = raw.get("drv") or {}
        pull_ohm = raw.get("pull_ohm") or {}
        fsel = raw.get("func_sel") or {}
        cfg = GpioChipConfig(
            chip=str(raw.get("chip") or chip_name),
            banks=banks,
            drv_base=_parse_int(drv.get("base")),
            drv_group_bases=[_parse_int(v)
                             for v in drv.get("group_bases", [])],
            drv_bits_per_gpio=int(drv.get("bits_per_gpio", 2) or 2),
            drv_levels=int(drv.get("levels", 0) or 0),
            drv_out_high_ohm=[float(v)
                              for v in drv.get("out_high_ohm", [])],
            drv_out_low_ohm=[float(v)
                             for v in drv.get("out_low_ohm", [])],
            pull_up_ohm=(float(pull_ohm["up"])
                         if pull_ohm.get("up") is not None else None),
            pull_down_ohm=(float(pull_ohm["down"])
                           if pull_ohm.get("down") is not None else None),
            pull_up_bases=[_parse_int(v)
                           for v in raw.get("pull_up_bases", [])],
            pull_down_bases=[_parse_int(v)
                             for v in raw.get("pull_down_bases", [])],
            func_sel_base=_parse_int(fsel.get("base")),
            func_sel_bits_per_gpio=int(fsel.get("bits_per_gpio", 4) or 4),
            func_sel_gpio_value=int(fsel.get("gpio_value", 0xF)),
            func_sel_groups=int(fsel.get("groups", 0) or 0),
            func_sel_functions=_parse_func_sel_functions(
                fsel.get("functions")),
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
