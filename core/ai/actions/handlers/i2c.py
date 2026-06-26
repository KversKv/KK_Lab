"""I2C（IIC）类动作 handlers（AIAssist_Architecture.md §8）。

i2c_read       : low，按 device_addr/reg_addr/width 读取一个寄存器值（只读）；
i2c_write      : high，向寄存器写值（必须确认，可能改变芯片状态），支持按位写；
bes_chip_check : low，自动探测 Main-die / 内置 PMU / 独立 PMU 型号版本与 I2C 配置。

device_addr/reg_addr/write_value 接受 16 进制字符串（如 '0x17'）或整数；width 仅 8/10/32。
不依赖常驻连接：每次动作临时创建 I2CInterface() 用完即关，与现有页面用法一致。
本模块禁 import Qt；I2C 走 lib/i2c（core→lib 合法）。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_I2C, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

_VALID_WIDTHS = (8, 10, 32)

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="i2c_read",
        description=(
            "通过 USB-I2C 读取一个寄存器值（只读）。device_addr/reg_addr 可填 16 进制字符串"
            "（如 '0x17'）或整数；width 为位宽 8/10/32（默认 10）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "device_addr": {
                    "type": ["string", "integer"],
                    "description": "I2C 设备地址，如 '0x17' 或 23。",
                },
                "reg_addr": {
                    "type": ["string", "integer"],
                    "description": "寄存器地址，如 '0x0000' 或 0。",
                },
                "width": {
                    "type": "integer",
                    "enum": list(_VALID_WIDTHS),
                    "description": "位宽，8/10/32，默认 10。",
                },
            },
            "required": ["device_addr", "reg_addr"],
        },
        risk_level="low",
        category=CATEGORY_I2C,
    ),
    ActionSpec(
        name="i2c_write",
        description=(
            "通过 USB-I2C 向寄存器写值（高风险，需确认，可能改变芯片状态）。"
            "支持按位写：high_bit/low_bit 给定时仅写该位段，省略则整寄存器写。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "device_addr": {
                    "type": ["string", "integer"],
                    "description": "I2C 设备地址，如 '0x17' 或 23。",
                },
                "reg_addr": {
                    "type": ["string", "integer"],
                    "description": "寄存器地址，如 '0x1e7'。",
                },
                "write_value": {
                    "type": ["string", "integer"],
                    "description": "要写入的值，如 '0x20AA' 或 8362。",
                },
                "width": {
                    "type": "integer",
                    "enum": list(_VALID_WIDTHS),
                    "description": "位宽，8/10/32，默认 10。",
                },
                "high_bit": {
                    "type": "integer",
                    "description": "按位写的高位位置，省略/-1 表示整寄存器写。",
                },
                "low_bit": {
                    "type": "integer",
                    "description": "按位写的低位位置，省略/-1 表示整寄存器写。",
                },
            },
            "required": ["device_addr", "reg_addr", "write_value"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_I2C,
    ),
    ActionSpec(
        name="bes_chip_check",
        description=(
            "自动探测 BES 芯片：返回 Main-die / 内置 PMU / 独立 PMU 的型号、版本、"
            "I2C 位宽与设备地址等信息（只读）。"
        ),
        parameters_schema={"type": "object", "properties": {}},
        risk_level="low",
        category=CATEGORY_I2C,
    ),
]


def _parse_int(value: Any) -> int:
    """把 16 进制字符串（'0x..'）/十进制字符串/整数统一解析为 int。"""
    if isinstance(value, bool):  # bool 是 int 子类，需先排除避免误解析
        raise ValueError("不接受布尔值。")
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("空值。")
    return int(text, 0)


def _parse_width(value: Any) -> int:
    width = _parse_int(value) if value is not None else 10
    if width not in _VALID_WIDTHS:
        raise ValueError(f"width 只能为 {_VALID_WIDTHS} 之一。")
    return width


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    # deps 当前不参与 I2C 访问（每次临时创建），保留签名以与其它 handler 一致。
    _ = deps

    def _new_interface():
        """临时创建并初始化一个 I2CInterface，失败抛异常由调用方转可读结果。"""
        from lib.i2c.i2c_interface_x64 import I2CInterface

        i2c = I2CInterface()
        if not i2c.initialize():
            raise RuntimeError("I2C 接口初始化失败（USB-I2C 设备未连接或驱动缺失？）。")
        return i2c

    def i2c_read(args: dict) -> dict:
        try:
            device_addr = _parse_int(args.get("device_addr"))
            reg_addr = _parse_int(args.get("reg_addr"))
            width = _parse_width(args.get("width"))
        except (ValueError, TypeError) as exc:
            return {"ok": False, "_message": f"参数无效：{exc}"}

        i2c = None
        try:
            i2c = _new_interface()
            value = i2c.read(device_addr, reg_addr, width)
        except Exception as exc:  # noqa: BLE001 - I2C 异常转可读结果
            logger.error("AI i2c_read 失败", exc_info=True)
            return {"ok": False, "_message": f"I2C 读取失败：{exc}"}
        finally:
            if i2c is not None:
                i2c.close()

        hex_value = f"0x{value:X}" if isinstance(value, int) else str(value)
        return {
            "ok": True,
            "device_addr": f"0x{device_addr:02X}",
            "reg_addr": f"0x{reg_addr:X}",
            "width": width,
            "value": value,
            "value_hex": hex_value,
            "_message": (
                f"读取 device=0x{device_addr:02X} reg=0x{reg_addr:X} "
                f"({width}bit) => {hex_value}"
            ),
        }

    def i2c_write(args: dict) -> dict:
        try:
            device_addr = _parse_int(args.get("device_addr"))
            reg_addr = _parse_int(args.get("reg_addr"))
            write_value = _parse_int(args.get("write_value"))
            width = _parse_width(args.get("width"))
            high_bit = int(args.get("high_bit", -1))
            low_bit = int(args.get("low_bit", -1))
        except (ValueError, TypeError) as exc:
            return {"ok": False, "_message": f"参数无效：{exc}"}

        i2c = None
        try:
            i2c = _new_interface()
            i2c.write(device_addr, reg_addr, write_value, width, high_bit, low_bit)
        except Exception as exc:  # noqa: BLE001 - I2C 异常转可读结果
            logger.error("AI i2c_write 失败", exc_info=True)
            return {"ok": False, "_message": f"I2C 写入失败：{exc}"}
        finally:
            if i2c is not None:
                i2c.close()

        bit_note = (
            f"（位段 [{high_bit}:{low_bit}]）" if high_bit >= 0 and low_bit >= 0 else ""
        )
        return {
            "ok": True,
            "device_addr": f"0x{device_addr:02X}",
            "reg_addr": f"0x{reg_addr:X}",
            "write_value": f"0x{write_value:X}",
            "width": width,
            "_message": (
                f"已写入 device=0x{device_addr:02X} reg=0x{reg_addr:X} "
                f"value=0x{write_value:X} ({width}bit){bit_note}。"
            ),
        }

    def bes_chip_check(_args: dict) -> dict:
        i2c = None
        try:
            i2c = _new_interface()
            info = i2c.bes_chip_check()
        except Exception as exc:  # noqa: BLE001 - I2C 异常转可读结果
            logger.error("AI bes_chip_check 失败", exc_info=True)
            return {"ok": False, "_message": f"芯片检测失败：{exc}"}
        finally:
            if i2c is not None:
                i2c.close()

        chip_name = info.get("chip_name") if isinstance(info, dict) else None
        return {
            "ok": True,
            "chip_info": info,
            "_message": (
                f"检测完成：{chip_name or '未识别到芯片'}。" if isinstance(info, dict)
                else "检测完成。"
            ),
        }

    return {
        "i2c_read": i2c_read,
        "i2c_write": i2c_write,
        "bes_chip_check": bes_chip_check,
    }
