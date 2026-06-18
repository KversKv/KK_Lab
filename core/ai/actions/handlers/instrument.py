"""仪器类动作 handlers（AI_Assist.md §8 / §10）。

一律经 InstrumentManager，AI 无法绕过 instruments/：
  query_instrument       : low，对已连接会话发只读 SCPI 查询（query 接口）；
  connect_instrument     : medium，按 instrument_type 触发异步扫描/连接（受确认配置）；
  disconnect_instrument  : medium，断开指定会话；
  set_instrument_output  : high，开/关通道输出，必须弹确认后才下发（OUTP ON/OFF）；
  set_instrument_voltage : high，设置通道电压，必须弹确认后才下发（VOLT）；
  set_instrument_current : high，设置通道电流，必须弹确认后才下发（CURR）。

写类高风险动作：会话须已连接、未被其它 owner 占用；执行期间通过 try_set_busy
取得短租约后调用驱动方法（驱动内部对量程/SCPI 安全做硬熔断，AI 无法突破）。
只读 query 不需 lease，但需会话已连接。本模块禁 import Qt。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import CATEGORY_INSTRUMENT, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="query_instrument",
        description="对已连接仪器会话发送只读 SCPI 查询并返回结果（经 InstrumentManager）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "command": {"type": "string"},
            },
            "required": ["session_id", "command"],
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="disconnect_instrument",
        description="断开指定仪器会话（经 InstrumentManager，异步）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="medium",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="set_instrument_output",
        description="开/关已连接仪器的通道输出（OUTP ON/OFF，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
                "enabled": {"type": "boolean"},
            },
            "required": ["session_id", "channel", "enabled"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="set_instrument_voltage",
        description="设置已连接仪器指定通道的输出电压（VOLT，单位 V，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
                "voltage": {"type": "number"},
            },
            "required": ["session_id", "channel", "voltage"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="set_instrument_current",
        description="设置已连接仪器指定通道的输出电流（CURR，单位 A，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
                "current": {"type": "number"},
            },
            "required": ["session_id", "channel", "current"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_INSTRUMENT,
    ),
]


def _is_query(command: str) -> bool:
    # SCPI 查询以 '?' 标识，但带通道参数时 '?' 不在结尾，
    # 例如 "MEAS:CURR? (@1)"，故判断是否包含 '?' 而非以 '?' 结尾。
    return "?" in command


def _resolve_query_fn(instance: Any) -> Any:
    # 优先用驱动自身封装的 query；N6705C 等驱动未封装 query，
    # 则回退到底层 pyvisa resource（instance.instr.query）。
    if instance is None:
        return None
    fn = getattr(instance, "query", None)
    if callable(fn):
        return fn
    instr = getattr(instance, "instr", None)
    instr_query = getattr(instr, "query", None)
    if callable(instr_query):
        return instr_query
    return None


_LEASE_OWNER = "AIAssist"


def _run_write_action(
    manager: Any,
    session_id: str,
    apply_fn: Any,
    success_message: str,
) -> dict:
    """写类高风险动作的统一执行骨架。

    流程：会话存在且已连接 -> 未被占用 -> try_set_busy 取租约 ->
    apply_fn(instance) 调用驱动方法（驱动内部硬熔断）-> finally 释放租约。
    """
    if manager is None:
        return {"ok": False, "_message": "InstrumentManager 不可用。"}
    if not session_id:
        return {"ok": False, "_message": "缺少 session_id。"}
    session = manager.get_session(session_id)
    if session is None or not session.connected:
        return {"ok": False, "_message": f"会话未连接：{session_id}"}
    if getattr(session, "busy", False):
        owner = getattr(session, "busy_owner", "")
        return {
            "ok": False,
            "_message": f"仪器忙（owner={owner or '未知'}），拒绝抢占以免中断运行。",
        }
    instance = manager.get_instance(session_id)
    if instance is None:
        return {"ok": False, "_message": f"无法获取仪器实例：{session_id}"}
    if not manager.try_set_busy(session_id, True, owner=_LEASE_OWNER):
        return {"ok": False, "_message": "无法取得仪器租约（可能已被占用）。"}
    try:
        result = apply_fn(instance)
    except (ValueError, AttributeError) as exc:
        logger.error("仪器写动作失败：%s", exc, exc_info=True)
        return {"ok": False, "_message": f"执行失败：{exc}"}
    except Exception:  # noqa: BLE001 - 兜底防止异常逃逸破坏会话状态
        logger.error("仪器写动作发生未预期异常", exc_info=True)
        return {"ok": False, "_message": "执行失败：仪器通信异常，详见日志。"}
    finally:
        manager.try_set_busy(session_id, False, owner=_LEASE_OWNER)
    payload = {"ok": True, "session_id": session_id, "_message": success_message}
    if isinstance(result, dict):
        payload.update(result)
    return payload


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def query_instrument(args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"ok": False, "_message": "InstrumentManager 不可用。"}
        session_id = str(args.get("session_id", ""))
        command = str(args.get("command", "")).strip()
        if not _is_query(command):
            return {"ok": False, "_message": "仅允许只读查询（命令须包含 '?'）。"}
        session = manager.get_session(session_id)
        if session is None or not session.connected:
            return {"ok": False, "_message": f"会话未连接：{session_id}"}
        if getattr(session, "busy", False):
            return {"ok": False, "_message": "仪器忙（运行中），拒绝查询以免抢占。"}
        instance = manager.get_instance(session_id)
        query_fn = _resolve_query_fn(instance)
        if query_fn is None:
            return {"ok": False, "_message": "该仪器不支持 query 接口。"}
        value = query_fn(command)
        return {
            "ok": True,
            "session_id": session_id,
            "command": command,
            "response": str(value),
            "_message": "查询完成。",
        }

    def disconnect_instrument(args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"ok": False, "_message": "InstrumentManager 不可用。"}
        session_id = str(args.get("session_id", ""))
        session = manager.get_session(session_id)
        if session is None:
            return {"ok": False, "_message": f"会话不存在：{session_id}"}
        if getattr(session, "busy", False):
            return {"ok": False, "_message": "仪器忙（运行中），拒绝断开以免中断测试。"}
        manager.disconnect_async(session_id)
        return {"ok": True, "session_id": session_id, "_message": "已发起断开（异步）。"}

    def set_instrument_output(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))
        enabled = bool(args.get("enabled", False))

        def apply(instance: Any) -> dict:
            method_name = "channel_on" if enabled else "channel_off"
            fn = getattr(instance, method_name, None)
            if not callable(fn):
                raise AttributeError(f"该仪器不支持 {method_name}。")
            fn(channel)
            return {"channel": channel, "enabled": enabled}

        state = "ON" if enabled else "OFF"
        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已将通道 {channel} 输出设为 {state}。",
        )

    def set_instrument_voltage(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))
        voltage = float(args.get("voltage", 0.0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_voltage", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 set_voltage。")
            fn(channel, voltage)
            return {"channel": channel, "voltage": voltage}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置通道 {channel} 电压为 {voltage} V。",
        )

    def set_instrument_current(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))
        current = float(args.get("current", 0.0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_current", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 set_current。")
            fn(channel, current)
            return {"channel": channel, "current": current}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置通道 {channel} 电流为 {current} A。",
        )

    return {
        "query_instrument": query_instrument,
        "disconnect_instrument": disconnect_instrument,
        "set_instrument_output": set_instrument_output,
        "set_instrument_voltage": set_instrument_voltage,
        "set_instrument_current": set_instrument_current,
    }
