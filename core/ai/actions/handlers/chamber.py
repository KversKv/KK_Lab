"""温箱类动作 handlers（AI_AssistFunction.md §5.4 P3）。

一律经 InstrumentManager 取得温箱驱动实例（VT6002 / MT3065 / WT2040 / Mock），
AI 无法绕过 instruments/。复用 instrument 模块的 _run_read_action / _run_write_action
骨架（会话存在 + 已连接 + 未被占用 + 租约管理 + 异常兜底），与仪器/示波器类动作
保持一致。

读类（low，不持租约，仪器忙时拒绝以免抢占运行中测试）：
  chamber_get_current_temp : 读取当前温度 PV（get_current_temp）；
  chamber_get_set_temp     : 读取设定温度 SV（get_set_temp）。

写类（high，必须确认；均持租约）：
  chamber_set_temperature  : 设置目标温度（set_temperature，影响 DUT 环境）；
  chamber_start            : 启动温箱控温（start）；
  chamber_stop             : 停止温箱控温（stop）。

长流程（high，必须确认；经 UI 注入的 chamber_wait_stable_callback 走 QThread worker）：
  chamber_wait_stable      : 等待温度到达并稳定（复用 TemperatureStabilizer），
                             执行期持 busy 租约，禁止阻塞 UI 线程。

本模块禁 import Qt：wait_stable 的 worker 由 UI 层（MainWindow）经回调注入实现，
handler 仅做参数校验与委托。
"""
from __future__ import annotations

from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.handlers.instrument import _run_read_action, _run_write_action
from core.ai.actions.registry import CATEGORY_CHAMBER, ActionSpec
from log_config import get_logger

logger = get_logger(__name__)

_MAX_WAIT_TIMEOUT_S = 3600.0

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="chamber_get_current_temp",
        description="读取已连接温箱的当前温度 PV 值（get_current_temp，单位 °C）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="low",
        category=CATEGORY_CHAMBER,
    ),
    ActionSpec(
        name="chamber_get_set_temp",
        description="读取已连接温箱的设定温度 SV 值（get_set_temp，单位 °C）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="low",
        category=CATEGORY_CHAMBER,
    ),
    ActionSpec(
        name="chamber_set_temperature",
        description=(
            "设置已连接温箱的目标温度（set_temperature，单位 °C，high：必须弹确认后才下发；"
            "影响 DUT 环境，建议先确认温箱量程与 DUT 承受能力）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "temperature": {
                    "type": "number",
                    "description": "目标温度（°C）。",
                },
            },
            "required": ["session_id", "temperature"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_CHAMBER,
    ),
    ActionSpec(
        name="chamber_start",
        description="启动已连接温箱的控温运行（start，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_CHAMBER,
    ),
    ActionSpec(
        name="chamber_stop",
        description="停止已连接温箱的控温运行（stop，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_CHAMBER,
    ),
    ActionSpec(
        name="chamber_wait_stable",
        description=(
            "等待已连接温箱到达目标温度并稳定（复用 TemperatureStabilizer，high：必须弹确认；"
            "长耗时动作，经 QThread worker 执行并持 busy 租约，不阻塞 UI）。"
            "调用前应已通过 chamber_set_temperature 设置目标温度。"
            "返回 stable/actual/waited_s/reason 等判稳结果。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "target": {
                    "type": "number",
                    "description": "期望稳定的目标温度（°C）。",
                },
                "tolerance": {
                    "type": "number",
                    "minimum": 0.01,
                    "description": "稳定判据：窗口内最大-最小温差容差（°C），默认 0.2。",
                },
                "timeout": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": _MAX_WAIT_TIMEOUT_S,
                    "description": "最大等待时间（秒），超时返回未稳定，默认 600。",
                },
            },
            "required": ["session_id", "target"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_CHAMBER,
    ),
]


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def chamber_get_current_temp(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "get_current_temp", None)
            if not callable(fn):
                raise AttributeError("该温箱不支持 get_current_temp。")
            return {"current_temp": fn()}

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"温箱 {session_id} 当前温度读取完成。",
        )

    def chamber_get_set_temp(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "get_set_temp", None)
            if not callable(fn):
                raise AttributeError("该温箱不支持 get_set_temp。")
            return {"set_temp": fn()}

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"温箱 {session_id} 设定温度读取完成。",
        )

    def chamber_set_temperature(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        temperature = float(args.get("temperature", 0.0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_temperature", None)
            if not callable(fn):
                raise AttributeError("该温箱不支持 set_temperature。")
            fn(temperature)
            return {"temperature": temperature}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置温箱 {session_id} 目标温度为 {temperature} °C。",
        )

    def chamber_start(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "start", None)
            if not callable(fn):
                raise AttributeError("该温箱不支持 start。")
            fn()
            return {}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"温箱 {session_id} 已启动控温。",
        )

    def chamber_stop(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "stop", None)
            if not callable(fn):
                raise AttributeError("该温箱不支持 stop。")
            fn()
            return {}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"温箱 {session_id} 已停止控温。",
        )

    def chamber_wait_stable(args: dict) -> dict:
        callback = deps.chamber_wait_stable_callback
        if callback is None:
            return {
                "ok": False,
                "_message": "温箱等待稳定能力不可用（未注入 worker 回调）。",
            }
        session_id = str(args.get("session_id", ""))
        if not session_id:
            return {"ok": False, "_message": "缺少 session_id。"}
        target = float(args.get("target", 0.0))
        tolerance = float(args.get("tolerance", 0.2))
        if tolerance <= 0:
            return {"ok": False, "_message": "tolerance 必须大于 0。"}
        timeout = float(args.get("timeout", 600.0))
        if timeout <= 0 or timeout > _MAX_WAIT_TIMEOUT_S:
            return {
                "ok": False,
                "_message": f"timeout 须在 (0, {_MAX_WAIT_TIMEOUT_S:.0f}] 秒。",
            }
        try:
            return callback(session_id, target, tolerance, timeout)
        except (ValueError, AttributeError) as exc:
            logger.error("温箱等待稳定失败：%s", exc, exc_info=True)
            return {"ok": False, "_message": f"执行失败：{exc}"}
        except Exception:  # noqa: BLE001 - 兜底防止异常逃逸破坏会话状态
            logger.error("温箱等待稳定发生未预期异常", exc_info=True)
            return {"ok": False, "_message": "执行失败：温箱通信异常，详见日志。"}

    return {
        "chamber_get_current_temp": chamber_get_current_temp,
        "chamber_get_set_temp": chamber_get_set_temp,
        "chamber_set_temperature": chamber_set_temperature,
        "chamber_start": chamber_start,
        "chamber_stop": chamber_stop,
        "chamber_wait_stable": chamber_wait_stable,
    }
