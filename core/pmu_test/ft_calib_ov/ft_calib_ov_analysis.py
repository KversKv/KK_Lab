# -*- coding: utf-8 -*-
"""FT Calibration Check - Output Voltage Check 纯算法（无 Qt）。

芯片 → 多 rail（DCDC/LDO）校准验证：EFUSE 码提取、偏移/绝对双模式校准码
计算、目标电压解析与容差判定。配置 schema 见 ft_calib_ov_store。
"""

import math

_RAIL_TYPES = ("DCDC", "LDO")
_CALIB_MODES = ("offset", "absolute")
_TARGET_SOURCES = ("config", "derived")
_EFUSE_LINKS = ("script", "i2c")
_WIDTH_FLAGS = (8, 10, 32, 88)
_SPEED_KHZ = (20, 100, 400, 750)
_MAX_BIT_INDEX = 31


def parse_int_value(value):
    """解析整数配置值：int 直取；字符串支持十进制 / 0x 十六进制。非法抛 ValueError。"""
    if isinstance(value, bool):
        raise ValueError(f"Invalid integer value: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"Invalid integer value: {value!r}")
        return int(value)
    text = str(value).strip()
    if not text:
        raise ValueError("Empty integer value")
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(text, 10)
    except ValueError:
        raise ValueError(f"Invalid integer value: {value!r}") from None


def _field_mask(msb, lsb):
    return (1 << (msb - lsb + 1)) - 1


def extract_bits(raw, msb, lsb, signed=False, sign_bit=None):
    """从寄存器原始值提取 [lsb, msb] 位域。

    signed=True 按二进制补码符号扩展；sign_bit 指定独立符号位
    （sign-magnitude：幅度无符号，符号位 1=负，如 BES1811/1860 EFUSE trim）。
    两者互斥，sign_bit 优先校验由 validate_rail 保证。
    """
    value = (int(raw) >> lsb) & _field_mask(msb, lsb)
    if sign_bit is not None:
        if (int(raw) >> int(sign_bit)) & 1:
            value = -value
        return value
    if signed:
        bit_count = msb - lsb + 1
        if value & (1 << (bit_count - 1)):
            value -= 1 << bit_count
    return value


def insert_bits(orig, code, msb, lsb):
    """read-modify-write：把 code 写入 orig 的 [lsb, msb] 位域，其余位保留。"""
    mask = _field_mask(msb, lsb)
    return (int(orig) & ~(mask << lsb)) | ((int(code) & mask) << lsb)


def compute_code(mode, base_code, efuse_value, offset_lsb=0):
    """校准码计算：offset = base_code + efuse + offset；absolute = efuse + offset。"""
    if mode == "offset":
        return int(base_code) + int(efuse_value) + int(offset_lsb)
    if mode == "absolute":
        return int(efuse_value) + int(offset_lsb)
    raise ValueError(f"Unknown calibration mode: {mode!r}")


def clamp_code(code, msb, lsb):
    """校准码钳位到位域可表示范围。返回 (钳位后码, 是否发生钳位)。"""
    mask = _field_mask(msb, lsb)
    clamped = max(0, min(int(code), mask))
    return clamped, clamped != int(code)


def resolve_target_mv(rail, code):
    """目标电压 (mV)：config 直取配置值；derived = code × step_mv + base_voltage_mv。"""
    target = rail.get("target") or {}
    source = target.get("source", "config")
    if source == "config":
        return float(target["voltage_mv"])
    if source == "derived":
        return int(code) * float(rail["step_mv"]) + float(rail["base_voltage_mv"])
    raise ValueError(f"Unknown target source: {source!r}")


def judge(measured_v, target_mv, tolerance_mv):
    """容差判定：|measured - target| <= tolerance 判 PASS（边界含等号）。

    返回 (误差 mV, 是否通过)。measured_v 单位 V。
    """
    err_mv = (float(measured_v) * 1000.0) - float(target_mv)
    return err_mv, abs(err_mv) <= float(tolerance_mv)


def summarize(rail_results):
    """逐 rail 结果汇总：total/passed/failed/max_abs_err_mv/overall_pass。"""
    total = len(rail_results)
    passed = sum(1 for r in rail_results if r.get("passed"))
    errors = [abs(r["err_mv"]) for r in rail_results if "err_mv" in r]
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "max_abs_err_mv": max(errors) if errors else 0.0,
        "overall_pass": total > 0 and passed == total,
    }


def _validate_bit_field(field, label):
    if not isinstance(field, dict):
        raise ValueError(f"{label}: expected dict")
    reg = parse_int_value(field.get("reg_addr"))
    if reg < 0:
        raise ValueError(f"{label}: reg_addr must be >= 0")
    msb = int(field.get("msb", -1))
    lsb = int(field.get("lsb", -1))
    if not (0 <= lsb <= msb <= _MAX_BIT_INDEX):
        raise ValueError(f"{label}: require 0 <= LSB <= MSB <= {_MAX_BIT_INDEX}")


def _validate_width_speed(node, label):
    width = node.get("width_flag")
    if width not in _WIDTH_FLAGS:
        raise ValueError(f"{label}: width_flag must be one of {_WIDTH_FLAGS}")
    speed = node.get("speed_khz")
    if speed not in _SPEED_KHZ:
        raise ValueError(f"{label}: speed_khz must be one of {_SPEED_KHZ}")


def _finite(value, label, positive=False):
    try:
        num = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: expected a number, got {value!r}") from None
    if not math.isfinite(num):
        raise ValueError(f"{label}: must be finite")
    if positive and num <= 0:
        raise ValueError(f"{label}: must be > 0")
    return num


def validate_rail(rail):
    """校验单个 rail 配置，非法抛 ValueError。"""
    if not isinstance(rail, dict):
        raise ValueError("Rail: expected dict")
    name = str(rail.get("name", "")).strip()
    if not name:
        raise ValueError("Rail: name must not be empty")
    if rail.get("type") not in _RAIL_TYPES:
        raise ValueError(f"Rail {name}: type must be one of {_RAIL_TYPES}")

    vbit = rail.get("vbit") or {}
    _validate_bit_field(vbit, f"Rail {name} vbit")
    vbit_width = vbit.get("width_flag")
    if vbit_width is not None and vbit_width not in _WIDTH_FLAGS:
        raise ValueError(f"Rail {name}: vbit.width_flag must be null or one of {_WIDTH_FLAGS}")

    efuse_field = rail.get("efuse_field") or {}
    _validate_bit_field(efuse_field, f"Rail {name} efuse_field")
    sign_bit = efuse_field.get("sign_bit")
    if sign_bit is not None:
        if isinstance(sign_bit, bool) or not isinstance(sign_bit, int) \
                or not (0 <= sign_bit <= _MAX_BIT_INDEX):
            raise ValueError(f"Rail {name}: efuse_field.sign_bit must be 0..{_MAX_BIT_INDEX}")
        if efuse_field["lsb"] <= sign_bit <= efuse_field["msb"]:
            raise ValueError(f"Rail {name}: sign_bit must be outside the magnitude field")
        if efuse_field.get("signed", False):
            raise ValueError(f"Rail {name}: signed and sign_bit are mutually exclusive")

    mode = rail.get("mode")
    if mode not in _CALIB_MODES:
        raise ValueError(f"Rail {name}: mode must be one of {_CALIB_MODES}")
    if mode == "offset":
        base = parse_int_value(rail.get("base_code"))
        if base < 0:
            raise ValueError(f"Rail {name}: base_code must be >= 0")
    offset = rail.get("offset_lsb", 0)
    if isinstance(offset, bool) or not isinstance(offset, (int, float)):
        raise ValueError(f"Rail {name}: offset_lsb must be an integer")
    if int(offset) != offset:
        raise ValueError(f"Rail {name}: offset_lsb must be an integer")

    _finite(rail.get("step_mv"), f"Rail {name} step_mv", positive=True)
    _finite(rail.get("base_voltage_mv"), f"Rail {name} base_voltage_mv")

    target = rail.get("target") or {}
    source = target.get("source")
    if source not in _TARGET_SOURCES:
        raise ValueError(f"Rail {name}: target.source must be one of {_TARGET_SOURCES}")
    if source == "config":
        _finite(target.get("voltage_mv"), f"Rail {name} target.voltage_mv", positive=True)

    _finite(rail.get("tolerance_mv"), f"Rail {name} tolerance_mv", positive=True)
    settle = rail.get("settle_ms", 0)
    if isinstance(settle, bool) or not isinstance(settle, (int, float)) or settle < 0:
        raise ValueError(f"Rail {name}: settle_ms must be >= 0")


def validate_chip_config(chip):
    """校验芯片级配置（含全部 rail），非法抛 ValueError。仪器操作前全量调用。"""
    if not isinstance(chip, dict):
        raise ValueError("Chip: expected dict")
    name = str(chip.get("name", "")).strip()
    if not name:
        raise ValueError("Chip: name must not be empty")

    i2c = chip.get("i2c") or {}
    dev = parse_int_value(i2c.get("device_addr"))
    if dev < 0:
        raise ValueError(f"Chip {name}: i2c.device_addr must be >= 0")
    _validate_width_speed(i2c, f"Chip {name} i2c")

    efuse = chip.get("efuse") or {}
    link = efuse.get("link")
    if link not in _EFUSE_LINKS:
        raise ValueError(f"Chip {name}: efuse.link must be one of {_EFUSE_LINKS}")
    if link == "script":
        script = str(efuse.get("script_filename", "")).strip()
        if not script:
            raise ValueError(f"Chip {name}: efuse.script_filename required for script link")
        efuse_width = efuse.get("width_flag", i2c.get("width_flag"))
        if efuse_width not in (8, 10, 32):
            raise ValueError(f"Chip {name}: script link requires width_flag 8/10/32")
    efuse_dev = efuse.get("device_addr", i2c.get("device_addr"))
    if parse_int_value(efuse_dev) < 0:
        raise ValueError(f"Chip {name}: efuse.device_addr must be >= 0")
    merged_efuse = {
        "width_flag": efuse.get("width_flag", i2c.get("width_flag")),
        "speed_khz": efuse.get("speed_khz", i2c.get("speed_khz")),
    }
    _validate_width_speed(merged_efuse, f"Chip {name} efuse")

    rails = chip.get("rails")
    if not isinstance(rails, list):
        raise ValueError(f"Chip {name}: rails must be a list")
    seen = set()
    for rail in rails:
        validate_rail(rail)
        rail_name = str(rail["name"]).strip()
        if rail_name in seen:
            raise ValueError(f"Chip {name}: duplicate rail name {rail_name!r}")
        seen.add(rail_name)
