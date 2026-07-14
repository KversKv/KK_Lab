# I2C 模块常量与工具函数

import os
import re

from ui.resource_path import get_user_data_dir

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

I2C_BTN_HEIGHT = 22

_I2C_WIDTH_META = {}


def _load_width_meta():
    from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
    return {
        I2CWidthFlag.BIT_8: ("8R/16D", 8, 16),
        I2CWidthFlag.BIT_10: ("16R/16D", 16, 16),
        I2CWidthFlag.BIT_32: ("32R/32D", 32, 32),
    }


def _load_speed_options():
    from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
    return [
        (I2CSpeedMode.SPEED_20K, "20 kHz"),
        (I2CSpeedMode.SPEED_100K, "100 kHz"),
        (I2CSpeedMode.SPEED_400K, "400 kHz"),
        (I2CSpeedMode.SPEED_750K, "750 kHz"),
    ]


# UI 位宽选项：(reg_bits, data_bits) → 显示文本
# BIT_8  = 8位寄存器地址, 16位数据（DLL 原生）
# BIT_10 = 16位寄存器地址, 16位数据
# BIT_32 = 32位寄存器地址, 32位数据
# 8R/8D: 使用 BIT_8（8位寄存器地址）读取后掩码到 8 位实现
_I2C_UI_WIDTHS = [
    ((8, 8), "8R / 8D"),
    ((8, 16), "8R / 16D"),
    ((16, 16), "16R / 16D"),
    ((32, 32), "32R / 32D"),
]


def _ui_width_to_flag(reg_bits):
    from lib.i2c.Bes_I2CIO_Interface import I2CWidthFlag
    if reg_bits == 8:
        return I2CWidthFlag.BIT_8
    if reg_bits == 32:
        return I2CWidthFlag.BIT_32
    return I2CWidthFlag.BIT_10


def _infer_reg_bits(data_bits):
    """从 data_bits 推断 reg_bits（向后兼容旧模板/状态）。"""
    if data_bits == 8:
        return 8
    if data_bits == 32:
        return 32
    return 16


def _width_label(flag):
    meta = _I2C_WIDTH_META.get(flag)
    return meta[0] if meta else str(flag)


def _reg_addr_bits(flag):
    meta = _I2C_WIDTH_META.get(flag)
    return meta[1] if meta else 16


def _data_bits(flag):
    meta = _I2C_WIDTH_META.get(flag)
    return meta[2] if meta else 16


def _hex_digits(bits):
    return max(1, (bits + 3) // 4)


def _fmt_hex(value, bits):
    return "0x%0{0}X".format(_hex_digits(bits)) % (int(value) & ((1 << bits) - 1))


def _fmt_bin(value, bits):
    return format(int(value) & ((1 << bits) - 1), "0{0}b".format(bits))


def _fmt_bin_grouped(value, bits):
    raw = _fmt_bin(value, bits)
    return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def _parse_hex_int(text):
    t = (text or "").strip()
    if not t:
        return 0
    neg = False
    if t.startswith("-"):
        neg = True
        t = t[1:]
    if t.lower().startswith("0x"):
        t = t[2:]
    if not re.fullmatch(r"[0-9a-fA-F]*", t):
        return None
    val = int(t, 16) if t else 0
    return -val if neg else val


def _parse_int_safe(text):
    """安全解析十进制整数（用于位索引、延时等），失败返回 0。"""
    try:
        return int((text or "").strip())
    except (ValueError, TypeError):
        return 0


def _i2c_template_dir():
    return get_user_data_dir("i2c_templates")


# ---------------------------------------------------------------------------
# 主题色（Tailwind Slate / Indigo / Emerald）
# ---------------------------------------------------------------------------

SLATE_950 = "#020617"
SLATE_900 = "#0f172a"
SLATE_800 = "#1e293b"
SLATE_700 = "#334155"
INDIGO = "#6366f1"
INDIGO_LIGHT = "#c7d2fe"
EMERALD = "#10b981"
EMERALD_LIGHT = "#34d399"
TEXT_MAIN = "#e2e8f0"
TEXT_MUTED = "#94a3b8"
