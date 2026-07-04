#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 测试项参数 schema 定义。

每个测试项在注册表中携带一份 ``ParamSpec`` 序列，描述该项"可在弹窗内单独设置"
的参数字段。UI 依据 schema 自动生成表单，运行时将用户填写的 override 浅合并进
``ctx.config``（仅对该项生效）。基类参数（来自被测配置界面）通过 ``base_key`` 声明
其在全局 cfg 里的默认取值来源，弹窗预填该值且可编辑。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ParamSpec:
    """单个参数字段定义。

    Attributes:
        key: 写入 override / cfg 的键名（如 ``settle_time_s``）。
        label: 弹窗内显示的中文标签。
        ptype: 输入类型，取值 ``int`` / ``float`` / ``text``。
        default: 该项自身缺省值（当 base_key 也取不到时兜底）。
        unit: 单位（追加到标签，如 ``s`` / ``mA``）；无单位留空。
        base_key: 基类 cfg 中的取值来源键；非空则弹窗预填该全局值。
        minimum / maximum: 数值输入范围（仅 int/float 生效）。
        decimals: float 小数位（仅 float 生效）。
        hint: 输入框占位提示。
    """

    key: str
    label: str
    ptype: str = "float"
    default: Any = 0.0
    unit: str = ""
    base_key: str = ""
    minimum: float = 0.0
    maximum: float = 1_000_000.0
    decimals: int = 3
    hint: str = ""


# 常用基类衍生字段的复用定义（避免各项重复书写）
def settle_time() -> ParamSpec:
    return ParamSpec("settle_time_s", "稳定时间", "float", 0.05, "s",
                     minimum=0.0, maximum=60.0, decimals=3)


def average_cnt(default: int = 3) -> ParamSpec:
    return ParamSpec("average_cnt", "平均次数", "int", default, "",
                     minimum=1, maximum=100)


def vin_bias(default: float = 3.7) -> ParamSpec:
    return ParamSpec("vin_v", "输入偏置", "float", default, "V",
                     minimum=0.0, maximum=60.0, decimals=3)


def vout_tol(key: str = "vout_tol", default: float = 0.02) -> ParamSpec:
    return ParamSpec(key, "输出容差", "float", default, "",
                     minimum=0.0, maximum=1.0, decimals=4,
                     hint="如 0.02 表示 ±2%")


# —— 负载扫描三件套（起始 / 结束 / 步进），随对应测试项设置 ——
def load_start(default: float = 1.0) -> ParamSpec:
    return ParamSpec("iload_start_ma", "起始负载", "float", default, "mA",
                     minimum=0.0, maximum=100_000.0, decimals=3)


def load_end(default: float = 200.0) -> ParamSpec:
    return ParamSpec("iload_end_ma", "结束负载", "float", default, "mA",
                     minimum=0.0, maximum=100_000.0, decimals=3)


def load_step(default: float = 20.0) -> ParamSpec:
    return ParamSpec("iload_step_ma", "负载步进", "float", default, "mA",
                     minimum=0.1, maximum=100_000.0, decimals=3)


def load_sweep(start: float = 1.0, end: float = 200.0, step: float = 20.0) -> tuple[ParamSpec, ...]:
    return (load_start(start), load_end(end), load_step(step))


# —— Vin 扫描三件套（起始 / 结束 / 步进），随对应测试项设置 ——
def vin_start(default: float = 3.2) -> ParamSpec:
    return ParamSpec("vin_start_v", "Vin 起始", "float", default, "V",
                     minimum=0.0, maximum=60.0, decimals=3)


def vin_end(default: float = 4.2) -> ParamSpec:
    return ParamSpec("vin_end_v", "Vin 结束", "float", default, "V",
                     minimum=0.0, maximum=60.0, decimals=3)


def vin_step(default: float = 0.2) -> ParamSpec:
    return ParamSpec("vin_step_v", "Vin 步进", "float", default, "V",
                     minimum=0.001, maximum=60.0, decimals=3)


def vin_sweep(start: float = 3.2, end: float = 4.2, step: float = 0.2) -> tuple[ParamSpec, ...]:
    return (vin_start(start), vin_end(end), vin_step(step))


# —— 寄存器扫描配置（原被测配置界面字段，现随 Output Voltage Scan 项设置）——
def reg_scan_params() -> tuple[ParamSpec, ...]:
    """挡位寄存器扫描所需参数：Code 起始/结束 + 寄存器地址 + MSB/LSB。"""
    return (
        ParamSpec("reg_addr", "寄存器地址", "text", "0x00", "",
                  hint="如 0x0132"),
        ParamSpec("msb", "MSB", "int", 7, "", minimum=0, maximum=31),
        ParamSpec("lsb", "LSB", "int", 0, "", minimum=0, maximum=31),
        ParamSpec("min_code", "Code 起始", "int", 0, "", minimum=0, maximum=65535),
        ParamSpec("max_code", "Code 结束", "int", 255, "", minimum=0, maximum=65535),
    )
