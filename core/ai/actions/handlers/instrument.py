"""仪器类动作 handlers（AI_Assist.md §8 / §10）。

一律经 InstrumentManager，AI 无法绕过 instruments/：
  query_instrument     : low，对已连接会话发只读 SCPI 查询（query 接口）；
  connect_instrument   : medium，按 instrument_type 触发异步扫描/连接（受确认配置）；
  disconnect_instrument: medium，断开指定会话；
  set_instrument_output: critical，默认禁止 AI 直接执行（仅生成建议）。

仪器忙（busy/lease）时拒绝抢占；只读 query 不需 lease，但需会话已连接。
本模块禁 import Qt。
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
        description="设置仪器通道输出（critical：默认禁止 AI 直接执行，仅供生成人工操作建议）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
                "enabled": {"type": "boolean"},
            },
            "required": ["session_id", "channel", "enabled"],
        },
        risk_level="critical",
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

    def set_instrument_output(_args: dict) -> dict:
        # PermissionChecker 在 critical+allow_critical=False 时已拦截；此处兜底。
        return {
            "ok": False,
            "_message": "set_instrument_output 为 critical 动作，禁止 AI 直接执行，请人工操作。",
        }

    return {
        "query_instrument": query_instrument,
        "disconnect_instrument": disconnect_instrument,
        "set_instrument_output": set_instrument_output,
    }
