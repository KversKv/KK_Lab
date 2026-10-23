# -*- coding: utf-8 -*-
"""BES GPIO Workbench 纯函数工具（I2C 速度选项 / SVG 图标 / 数值格式化 / 脚本行）。"""

import os

from ui.utils.icon_utils import tinted_svg_icon

from ui.pages.gpio.gpio_control.style import _ICONS_DIR

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


def _icon(name, color, size=14):
    return tinted_svg_icon(os.path.join(_ICONS_DIR, name), color, size)


def _fmt32(value):
    return "0x{0:08X}".format(value & 0xFFFFFFFF)


def _popcount(value):
    return bin(value & 0xFFFFFFFF).count("1")


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _parse_hex(text):
    """解析 16 进制输入（容忍 0x 前缀/空格）；非法返回 None。"""
    text = (text or "").strip()
    if not text:
        return None
    try:
        return int(text, 16) & 0xFFFFFFFF
    except ValueError:
        return None


def _write_bits_line(op, addr, value, hi, lo):
    """寄存器动作 -> WRITE_BITS 脚本行；set/clear 单 bit 整写转位域写。"""
    if hi < 0:
        if value and (value & (value - 1)) == 0:
            bit = value.bit_length() - 1
            hi, lo, value = bit, bit, 1
        else:
            hi, lo = 31, 0
    return "WRITE_BITS 0x{0:08X} {1} {2} 0x{3:X}".format(addr, hi, lo, value)
