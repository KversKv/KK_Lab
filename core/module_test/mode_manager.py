"""DUT 工作模式管理：解析模式声明 + 提供"进入模式"原子能力。

纯函数，禁依赖 Qt；供 items/* 与 runner 复用（对齐 _common.py 风格）。
覆盖三类进入方式（方案 §1.2 / §3）：
  - reg    : 写 I2C 寄存器（LDO 含 bias 挡）——CASE A 寄存器可控。
  - load   : 设负载点 + 可选回读芯片实际模式——CASE B 负载自动切换。
  - manual : 发暂停请求等用户手动切好确认——CASE C 手动台架。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.module_test._common import (
    ItemContext, cfg_int, create_i2c, parse_channel, set_load_current, settle,
)
from log_config import get_logger

logger = get_logger(__name__)

_VALID_ENTER = ("reg", "load", "manual")


@dataclass
class ModeSpec:
    """单个工作模式声明（由 cfg['dut_modes'] 元素解析而来）。"""

    name: str
    enter: str = "reg"
    reg_writes: list[dict] = field(default_factory=list)  # [{addr,value}] 顺序写入
    load_ma: float = 0.0                                   # enter==load 触发负载点
    mode_readback: dict | None = None                      # {addr,msb,lsb,expect}
    prompt: str = ""                                       # enter==manual 提示
    settle_s: float | None = None                          # 覆盖项级稳定时间


@dataclass
class ModeEntryResult:
    """进入模式的结果。"""

    ok: bool
    actual_mode: str          # load 场景为回读结果；reg/manual 即声明 name
    note: str = ""


def parse_dut_modes(cfg: dict) -> list[ModeSpec]:
    """解析 cfg['dut_modes'] 为 ModeSpec 列表。

    缺字段给合理默认并 log 警告，不抛裸异常；enter 非法回退 'manual'。
    无声明时返回空列表（调用方自行兜底）。
    """
    raw = cfg.get("dut_modes")
    if not isinstance(raw, list):
        return []
    modes: list[ModeSpec] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            logger.warning("dut_modes[%d] 非 dict，已跳过", i)
            continue
        name = str(item.get("name", "")).strip() or f"Mode{i + 1}"
        enter = str(item.get("enter", "reg")).strip().lower()
        if enter not in _VALID_ENTER:
            logger.warning("模式 %s 的 enter=%r 非法，回退 manual", name, enter)
            enter = "manual"
        reg_writes = item.get("reg_writes") if isinstance(item.get("reg_writes"), list) else []
        readback = item.get("mode_readback") if isinstance(item.get("mode_readback"), dict) else None
        settle_s = item.get("settle_s")
        modes.append(ModeSpec(
            name=name,
            enter=enter,
            reg_writes=[w for w in reg_writes if isinstance(w, dict)],
            load_ma=float(item.get("load_ma", 0.0) or 0.0),
            mode_readback=readback,
            prompt=str(item.get("prompt", "")).strip(),
            settle_s=(float(settle_s) if isinstance(settle_s, (int, float)) else None),
        ))
    return modes


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


def _enter_mode_reg(ctx: ItemContext, mode: ModeSpec) -> ModeEntryResult:
    """CASE A：按声明顺序写 I2C 寄存器进入模式。"""
    if ctx.is_mock:
        return ModeEntryResult(ok=True, actual_mode=mode.name, note="mock")
    if not mode.reg_writes:
        return ModeEntryResult(ok=True, actual_mode=mode.name, note="无寄存器写入")
    cfg = ctx.config
    device_addr = cfg_int(cfg, "device_addr", 0x00)
    width_flag = cfg_int(cfg, "width_flag", 1)
    i2c = create_i2c(ctx)
    for w in mode.reg_writes:
        addr = _to_int(w.get("addr"), 0)
        value = _to_int(w.get("value"), 0)
        try:
            i2c.write(device_addr, addr, value, width_flag)
            ctx.log_fn(f"[mode:{mode.name}] write 0x{addr:X}=0x{value:X}")
        except Exception:  # noqa: BLE001 - 写失败降级记录，不中断整体
            logger.error("模式 %s 写寄存器 0x%X 失败", mode.name, addr, exc_info=True)
            return ModeEntryResult(ok=False, actual_mode=mode.name, note=f"写 0x{addr:X} 失败")
    return ModeEntryResult(ok=True, actual_mode=mode.name)


def _enter_mode_load(ctx: ItemContext, mode: ModeSpec) -> ModeEntryResult:
    """CASE B：设负载电流触发自动切换，可选回读芯片实际模式。"""
    if ctx.is_mock:
        # 按负载点粗略映射一个 mock 实际模式，便于验证回读链路
        if mode.load_ma <= 1.0:
            actual = "ULP"
        elif mode.load_ma <= 100.0:
            actual = "BURST"
        else:
            actual = "PWM"
        return ModeEntryResult(ok=True, actual_mode=actual, note="mock")
    iload_ch = parse_channel(ctx.config.get("iload_channel", 3))
    set_load_current(ctx, iload_ch, mode.load_ma / 1000.0)  # mA -> A
    ctx.log_fn(f"[mode:{mode.name}] set load {mode.load_ma:.3f} mA")
    settle(ctx, mode.settle_s if mode.settle_s is not None else 0.2)
    actual = mode.name
    rb = mode.mode_readback
    if rb:
        try:
            device_addr = cfg_int(ctx.config, "device_addr", 0x00)
            width_flag = cfg_int(ctx.config, "width_flag", 1)
            addr = _to_int(rb.get("addr"), 0)
            msb = _to_int(rb.get("msb"), 0)
            lsb = _to_int(rb.get("lsb"), 0)
            i2c = create_i2c(ctx)
            reg = i2c.read(device_addr, addr, width_flag)
            mask = (1 << (msb - lsb + 1)) - 1
            field_val = (reg >> lsb) & mask
            actual = f"{mode.name}(rb={field_val})"
            expect = rb.get("expect")
            if expect is not None and field_val != _to_int(expect, -1):
                return ModeEntryResult(ok=False, actual_mode=actual,
                                       note=f"回读 {field_val} != 期望 {expect}")
        except Exception:  # noqa: BLE001 - 回读失败降级记录，不中断整体
            logger.error("模式 %s 回读失败", mode.name, exc_info=True)
            return ModeEntryResult(ok=False, actual_mode=mode.name, note="回读失败")
    return ModeEntryResult(ok=True, actual_mode=actual)


def _enter_mode_manual(ctx: ItemContext, mode: ModeSpec) -> ModeEntryResult:
    """CASE C：请求 UI 弹确认框，阻塞等待用户手动切好。"""
    if ctx.is_mock:
        return ModeEntryResult(ok=True, actual_mode=mode.name, note="mock")
    prompt = mode.prompt or f"请手动将 DUT 切到「{mode.name}」模式后点击确认"
    confirmed = ctx.pause_fn(prompt)
    if not confirmed:
        return ModeEntryResult(ok=False, actual_mode=mode.name, note="用户取消/停止")
    return ModeEntryResult(ok=True, actual_mode=mode.name)


def enter_mode(ctx: ItemContext, mode: ModeSpec) -> ModeEntryResult:
    """按 mode.enter 分派进入模式；异常降级为失败态，禁裸 except 传播。"""
    try:
        if mode.enter == "reg":
            return _enter_mode_reg(ctx, mode)
        if mode.enter == "load":
            return _enter_mode_load(ctx, mode)
        return _enter_mode_manual(ctx, mode)
    except Exception:  # noqa: BLE001 - 进入模式异常降级，不中断整体流程
        logger.error("进入模式 %s 异常", mode.name, exc_info=True)
        return ModeEntryResult(ok=False, actual_mode=mode.name, note="进入模式异常")
