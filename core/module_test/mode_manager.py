"""静态电流差分测量：ENABLE 双寄存器位写 + 使能/关断做差。

纯函数，禁依赖 Qt；供 items/* 复用（对齐 _common.py 风格）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.module_test._common import ItemContext, cfg_int, create_i2c, settle
from log_config import get_logger

logger = get_logger(__name__)


def _to_int(value: Any, default: int = 0) -> int:
    """把 '0x30' / '48' / 48 统一转 int（沿用 cfg_int 的十六进制约定）。"""
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        return int(s, 16) if s.lower().startswith("0x") else int(s, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
@dataclass
class EnableRegSpec:
    """ENABLE 双寄存器（dr + en）位段声明，从 cfg 的 iq_* 参数解析而来。"""

    dr_addr: int
    en_addr: int
    dr_bit: int
    en_bit: int
    on_dr_val: int
    on_en_val: int
    off_dr_val: int
    off_en_val: int


def parse_enable_regs(cfg: dict) -> EnableRegSpec | None:
    """解析 cfg 中的 ENABLE 双寄存器参数；地址均为 0 视为未配置返回 None。"""
    dr_addr = _to_int(cfg.get("iq_en_dr_addr"), 0)
    en_addr = _to_int(cfg.get("iq_en_addr"), 0)
    if dr_addr == 0 and en_addr == 0:
        return None
    return EnableRegSpec(
        dr_addr=dr_addr,
        en_addr=en_addr,
        dr_bit=_to_int(cfg.get("iq_en_dr_bit"), 0),
        en_bit=_to_int(cfg.get("iq_en_bit"), 0),
        on_dr_val=_to_int(cfg.get("iq_on_dr_val"), 1),
        on_en_val=_to_int(cfg.get("iq_on_en_val"), 1),
        off_dr_val=_to_int(cfg.get("iq_off_dr_val"), 1),
        off_en_val=_to_int(cfg.get("iq_off_en_val"), 0),
    )


def _write_field(i2c: Any, device_addr: int, width_flag: int,
                 addr: int, bit: int, value: int) -> None:
    """读改写寄存器单个 bit（保留其余位），value 须为 0/1。"""
    reg = i2c.read(device_addr, addr, width_flag)
    mask = 1 << bit
    reg = (reg & ~mask) | ((value & 1) << bit)
    i2c.write(device_addr, addr, reg, width_flag)


def set_dut_enable(ctx: ItemContext, regs: EnableRegSpec, *, on: bool) -> bool:
    """写 ENABLE 双寄存器，使被测 LDO/DCDC 使能(on)或关断(off)。

    Mock 模式为 no-op 返回 True；真机按 dr → en 顺序位段写，失败降级 False。
    仅改被测本路的 dr/en 位段，不动 SOC 其余部分。
    """
    if ctx.is_mock:
        return True
    device_addr = cfg_int(ctx.config, "device_addr", 0x00)
    width_flag = cfg_int(ctx.config, "width_flag", 1)
    dr_val = regs.on_dr_val if on else regs.off_dr_val
    en_val = regs.on_en_val if on else regs.off_en_val
    try:
        i2c = create_i2c(ctx)
        _write_field(i2c, device_addr, width_flag,
                     regs.dr_addr, regs.dr_bit, dr_val)
        _write_field(i2c, device_addr, width_flag,
                     regs.en_addr, regs.en_bit, en_val)
        ctx.log_fn(f"[enable] {'ON' if on else 'OFF'} "
                   f"dr=0x{regs.dr_addr:X}<-{dr_val} en=0x{regs.en_addr:X}<-{en_val}")
        return True
    except Exception:  # noqa: BLE001 - 写使能寄存器失败降级，不中断整体
        logger.error("写 ENABLE 寄存器失败 (on=%s)", on, exc_info=True)
        return False


def iq_diff_measure(ctx: ItemContext, item_key: str, vin_ch: int, vout_src_ch: int,
                    vout_supply_v: float, en_regs: EnableRegSpec,
                    settle_s: float, avg_cnt: int,
                    mock_base_ua: float = 80.0) -> tuple:
    """静态电流差分测量核心（LDO/DCDC 共用）。

    外供 Vout 源到 vout_supply_v，分别在使能 / 关断两态测 Vin+Vout 电流做差。
    返回 (dIvin_uA, dIvout_uA, Iq_uA)，均已四舍五入到 3 位。
    """
    from core.module_test._common import (
        measure_avg, mock_jitter, setup_source_channel,
    )

    st = max(settle_s * 4, 0.2)
    if ctx.is_mock:
        ivin_on = mock_jitter(mock_base_ua * 0.6, 0.05)
        ivout_on = mock_jitter(mock_base_ua * 0.4, 0.05)
        ivin_off = mock_jitter(mock_base_ua * 0.05, 0.1)
        ivout_off = mock_jitter(mock_base_ua * 0.02, 0.1)
    else:
        # 外供 Vout 源（双象限，可吸可灌），限流兜底
        setup_source_channel(ctx, vout_src_ch, vout_supply_v, current_limit=0.5)
        # 使能态
        set_dut_enable(ctx, en_regs, on=True)
        settle(ctx, st)
        ivin_on = measure_avg(ctx, "measure_current", vin_ch,
                              count=avg_cnt, settle_s=settle_s) * 1e6
        ivout_on = measure_avg(ctx, "measure_current", vout_src_ch,
                               count=avg_cnt, settle_s=settle_s) * 1e6
        # 关断态
        set_dut_enable(ctx, en_regs, on=False)
        settle(ctx, st)
        ivin_off = measure_avg(ctx, "measure_current", vin_ch,
                               count=avg_cnt, settle_s=settle_s) * 1e6
        ivout_off = measure_avg(ctx, "measure_current", vout_src_ch,
                                count=avg_cnt, settle_s=settle_s) * 1e6
    d_ivin = ivin_on - ivin_off
    d_ivout = ivout_on - ivout_off
    iq = d_ivin + d_ivout
    return (round(d_ivin, 3), round(d_ivout, 3), round(iq, 3))
