"""仪器类动作 handlers（AIAssist_Architecture.md §8 / §10）。

一律经 InstrumentManager，AI 无法绕过 instruments/：
  query_instrument            : low，对已连接会话发只读 SCPI 查询（query 接口）；
  connect_instrument          : medium，按 instrument_type 触发异步连接（受确认）；
  scan_instruments            : low，异步扫描 + 回灌上次缓存候选；
  disconnect_instrument       : medium，断开指定会话；
  disconnect_all_instruments  : medium，断开所有已连接会话（受确认）；
  find_instrument_sessions    : low，按角色/能力查找已连接会话；
  get_instrument_capabilities : low，读取会话能力集合；
  measure_voltage             : low，测量通道电压（MEAS:VOLT?）；
  measure_current             : low，测量通道电流（MEAS:CURR?）；
  get_channel_output_state    : low，读取通道输出开关状态（OUTP?）；
  get_channel_limits          : low，读取通道电流/电压限值（CURR:LIM? / VOLT:LIM?）；
  set_instrument_output       : high，开/关通道输出，必须弹确认后才下发（OUTP ON/OFF）；
  set_instrument_voltage      : high，设置通道电压，必须弹确认后才下发（VOLT）；
  set_instrument_current      : high，设置通道电流，必须弹确认后才下发（CURR）；
  set_current_limit           : high，设置通道电流限值（CURR:LIM，必须确认）；
  set_output_off_mode         : high，设置输出关闭模式（OUTP:TMOD HIGHZ/LOWZ，必须确认）。

写类高风险动作：会话须已连接、未被其它 owner 占用；执行期间通过 try_set_busy
取得短租约后调用驱动方法（驱动内部对量程/SCPI 安全做硬熔断，AI 无法突破）。
只读 query/测量不需 lease，但需会话已连接且未被占用。本模块禁 import Qt。
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
    ActionSpec(
        name="connect_instrument",
        description=(
            "按仪器类型发起异步连接（经 InstrumentManager.connect_async）。"
            "resource 为 VISA 地址（如 'TCPIP0::192.168.1.5::inst0::INSTR'）或串口名；"
            "slot 用于区分同类型多台仪器（缺省 'default'）。"
            "连接结果异步返回，可稍后用 get_instrument_status 确认。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "instrument_type": {
                    "type": "string",
                    "description": "仪器类型，如 'n6705c'/'dsox4034a'/'mso64b'/'vt6002'。",
                },
                "resource": {"type": "string", "description": "VISA 资源地址或串口名。"},
                "role": {"type": "string", "description": "角色标签（可选），如 'power'/'scope'。"},
                "slot": {"type": "string", "description": "槽位标识（可选，缺省 'default'）。"},
            },
            "required": ["instrument_type", "resource"],
        },
        risk_level="medium",
        require_confirmation=True,
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="scan_instruments",
        description=(
            "发起指定仪器类型的异步扫描（经 InstrumentManager.scan_async），"
            "并返回上一次扫描缓存到的候选列表（若有）。扫描完成后再次调用可获取最新结果。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "instrument_type": {"type": "string", "description": "仪器类型，如 'n6705c'。"},
            },
            "required": ["instrument_type"],
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="disconnect_all_instruments",
        description="断开所有已连接的仪器会话（经 InstrumentManager.disconnect_all_async，异步）。",
        parameters_schema={"type": "object", "properties": {}},
        risk_level="medium",
        require_confirmation=True,
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="find_instrument_sessions",
        description="按角色/能力查找已连接的仪器会话（经 InstrumentManager.find_sessions）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "role": {"type": "string", "description": "角色过滤（可选）。"},
                "required_capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要求具备的能力集合（可选）。",
                },
            },
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="get_instrument_capabilities",
        description="读取指定仪器会话的能力集合（InstrumentSnapshot.capabilities）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="measure_voltage",
        description="测量已连接仪器指定通道的电压（MEAS:VOLT?，单位 V）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
            },
            "required": ["session_id", "channel"],
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="measure_current",
        description="测量已连接仪器指定通道的电流（MEAS:CURR?，单位 A）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
            },
            "required": ["session_id", "channel"],
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="get_channel_output_state",
        description="读取已连接仪器指定通道的输出开关状态（OUTP?）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
            },
            "required": ["session_id", "channel"],
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="get_channel_limits",
        description="读取已连接仪器指定通道的电流/电压限值（CURR:LIM? / VOLT:LIM?）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
            },
            "required": ["session_id", "channel"],
        },
        risk_level="low",
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="set_current_limit",
        description="设置已连接仪器指定通道的电流限值（CURR:LIM，单位 A，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
                "limit": {"type": "number", "description": "电流限值（A）。"},
            },
            "required": ["session_id", "channel", "limit"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_INSTRUMENT,
    ),
    ActionSpec(
        name="set_output_off_mode",
        description=(
            "设置已连接仪器指定通道的输出关闭模式（OUTP:TMOD，HIGHZ/LOWZ，"
            "high：必须弹确认后才下发；影响 DUT 安全）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer"},
                "mode": {"type": "string", "enum": ["HIGHZ", "LOWZ"]},
            },
            "required": ["session_id", "channel", "mode"],
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


def _to_float_or_str(value: Any) -> Any:
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value).strip()


def _candidate_to_dict(candidate: Any) -> dict:
    return {
        "instrument_type": getattr(candidate, "instrument_type", ""),
        "connection_kind": getattr(candidate, "connection_kind", ""),
        "resource": getattr(candidate, "resource", ""),
        "model_hint": getattr(candidate, "model_hint", ""),
        "serial_hint": getattr(candidate, "serial_hint", ""),
        "display_name": getattr(candidate, "display_name", ""),
    }


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


def _run_read_action(
    manager: Any,
    session_id: str,
    apply_fn: Any,
    success_message: str,
) -> dict:
    """只读测量类动作的统一执行骨架。

    流程：会话存在且已连接 -> 未被占用（不取租约，仅避让运行中仪器）->
    apply_fn(instance) 调用驱动只读方法 -> 返回结果。读类不持租约，与
    query_instrument 一致：仪器忙时拒绝以免抢占运行中的测试。
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
            "_message": f"仪器忙（owner={owner or '未知'}），拒绝读取以免抢占。",
        }
    instance = manager.get_instance(session_id)
    if instance is None:
        return {"ok": False, "_message": f"无法获取仪器实例：{session_id}"}
    try:
        result = apply_fn(instance)
    except (ValueError, AttributeError) as exc:
        logger.error("仪器读动作失败：%s", exc, exc_info=True)
        return {"ok": False, "_message": f"执行失败：{exc}"}
    except Exception:  # noqa: BLE001 - 兜底防止异常逃逸破坏会话状态
        logger.error("仪器读动作发生未预期异常", exc_info=True)
        return {"ok": False, "_message": "执行失败：仪器通信异常，详见日志。"}
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

    def connect_instrument(args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"ok": False, "_message": "InstrumentManager 不可用。"}
        instrument_type = str(args.get("instrument_type", "")).strip()
        resource = str(args.get("resource", "")).strip()
        if not instrument_type or not resource:
            return {"ok": False, "_message": "缺少 instrument_type 或 resource。"}
        if manager.registry.get(instrument_type) is None:
            return {"ok": False, "_message": f"未注册的仪器类型：{instrument_type}"}
        role = str(args.get("role", "")).strip()
        slot = str(args.get("slot", "")).strip() or "default"
        from core.instruments.instrument_session import InstrumentSpec

        spec = InstrumentSpec(
            instrument_type=instrument_type,
            resource=resource,
            role=role,
            slot=slot,
        )
        try:
            session_id = manager.connect_async(spec)
        except ValueError as exc:
            return {"ok": False, "_message": f"连接发起失败：{exc}"}
        session = manager.get_session(session_id)
        already = session is not None and session.connected
        message = (
            "会话已连接。"
            if already
            else "已发起连接（异步），可稍后用 get_instrument_status 确认。"
        )
        return {"ok": True, "session_id": session_id, "_message": message}

    def scan_instruments(args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"ok": False, "_message": "InstrumentManager 不可用。"}
        instrument_type = str(args.get("instrument_type", "")).strip()
        if not instrument_type:
            return {"ok": False, "_message": "缺少 instrument_type。"}
        if manager.registry.get(instrument_type) is None:
            return {"ok": False, "_message": f"未注册的仪器类型：{instrument_type}"}
        cached = manager.get_last_scan(instrument_type)
        cached_list = [_candidate_to_dict(c) for c in cached] if cached else []
        manager.scan_async(instrument_type)
        payload: dict = {"ok": True, "instrument_type": instrument_type}
        # 异步动作升级（§4 / S3-1）：登记 pending 任务，完成后由 UI 回灌续跑
        registry = deps.pending_task_registry
        if registry is not None:
            session_key = ""
            if deps.session_key_getter is not None:
                try:
                    session_key = deps.session_key_getter() or ""
                except Exception:  # noqa: BLE001
                    logger.error("session_key_getter 调用异常", exc_info=True)
            task_id = registry.register(
                session_key, "scan_instruments", title=instrument_type
            )
            payload["task_id"] = task_id
        if cached_list:
            payload["cached_candidates"] = cached_list
            payload["_message"] = (
                f"已发起新一轮扫描；上次扫描到 {len(cached_list)} 个候选。"
                "完成后会自动回灌最新结果。"
            )
        else:
            payload["_message"] = "已发起扫描（异步），完成后会自动回灌结果。"
        return payload

    def disconnect_all_instruments(_args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"ok": False, "_message": "InstrumentManager 不可用。"}
        connected = [s for s in manager.sessions() if s.connected]
        if not connected:
            return {"ok": True, "_message": "当前无已连接仪器会话。"}
        manager.disconnect_all_async()
        return {
            "ok": True,
            "disconnecting_count": len(connected),
            "_message": f"已发起断开 {len(connected)} 个已连接会话（异步）。",
        }

    def find_instrument_sessions(args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"ok": False, "_message": "InstrumentManager 不可用。"}
        role = str(args.get("role", "")).strip()
        raw_caps = args.get("required_capabilities") or []
        if isinstance(raw_caps, str):
            raw_caps = [raw_caps]
        caps_set = {str(c) for c in raw_caps if str(c).strip()} or None
        snaps = manager.find_sessions(
            role=role,
            required_capabilities=caps_set,
            connected_only=True,
        )
        items = [
            {
                "session_id": s.session_id,
                "instrument_type": s.instrument_type,
                "role": s.role,
                "model": s.model,
            }
            for s in snaps
        ]
        return {
            "ok": True,
            "count": len(items),
            "sessions": items,
            "_message": f"找到 {len(items)} 个匹配会话。",
        }

    def get_instrument_capabilities(args: dict) -> dict:
        manager = deps.instrument_manager
        if manager is None:
            return {"ok": False, "_message": "InstrumentManager 不可用。"}
        session_id = str(args.get("session_id", ""))
        session = manager.get_session(session_id)
        if session is None:
            return {"ok": False, "_message": f"会话不存在：{session_id}"}
        caps = sorted(session.capabilities)
        return {
            "ok": True,
            "session_id": session_id,
            "instrument_type": session.instrument_type,
            "connected": bool(session.connected),
            "capabilities": caps,
            "_message": f"会话 {session_id} 能力：{', '.join(caps) or '无'}",
        }

    def measure_voltage(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "measure_voltage", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 measure_voltage。")
            return {"channel": channel, "voltage": fn(channel)}

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"通道 {channel} 电压测量完成。",
        )

    def measure_current(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "measure_current", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 measure_current。")
            return {"channel": channel, "current": fn(channel)}

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"通道 {channel} 电流测量完成。",
        )

    def get_channel_output_state(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "get_channel_state", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 get_channel_state。")
            return {"channel": channel, "enabled": bool(fn(channel))}

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"通道 {channel} 输出状态读取完成。",
        )

    def get_channel_limits(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))

        def apply(instance: Any) -> dict:
            result: dict = {"channel": channel}
            curr_fn = getattr(instance, "get_current_limit", None)
            if callable(curr_fn):
                result["current_limit"] = _to_float_or_str(curr_fn(channel))
            volt_fn = getattr(instance, "get_voltage_limit", None)
            if callable(volt_fn):
                result["voltage_limit"] = _to_float_or_str(volt_fn(channel))
            if "current_limit" not in result and "voltage_limit" not in result:
                raise AttributeError("该仪器不支持读取通道限值。")
            return result

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"通道 {channel} 限值读取完成。",
        )

    def set_current_limit(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))
        limit = float(args.get("limit", 0.0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_current_limit", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 set_current_limit。")
            fn(channel, limit)
            return {"channel": channel, "current_limit": limit}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置通道 {channel} 电流限值为 {limit} A。",
        )

    def set_output_off_mode(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))
        mode = str(args.get("mode", "")).strip().upper()
        if mode not in ("HIGHZ", "LOWZ"):
            return {"ok": False, "_message": "mode 必须为 HIGHZ 或 LOWZ。"}

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_output_off_mode", None)
            if not callable(fn):
                raise AttributeError("该仪器不支持 set_output_off_mode。")
            fn(channel, mode)
            return {"channel": channel, "off_mode": mode}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置通道 {channel} 输出关闭模式为 {mode}。",
        )

    return {
        "query_instrument": query_instrument,
        "disconnect_instrument": disconnect_instrument,
        "set_instrument_output": set_instrument_output,
        "set_instrument_voltage": set_instrument_voltage,
        "set_instrument_current": set_instrument_current,
        "connect_instrument": connect_instrument,
        "scan_instruments": scan_instruments,
        "disconnect_all_instruments": disconnect_all_instruments,
        "find_instrument_sessions": find_instrument_sessions,
        "get_instrument_capabilities": get_instrument_capabilities,
        "measure_voltage": measure_voltage,
        "measure_current": measure_current,
        "get_channel_output_state": get_channel_output_state,
        "get_channel_limits": get_channel_limits,
        "set_current_limit": set_current_limit,
        "set_output_off_mode": set_output_off_mode,
    }
