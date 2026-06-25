"""示波器类动作 handlers（AIAssist_ActionCatalog.md §5.3 P2）。

一律经 InstrumentManager 取得示波器驱动实例（DSOX4034A / MSO64B / MockMSO64B），
AI 无法绕过 instruments/。复用 instrument 模块的 _run_read_action / _run_write_action
骨架（会话存在 + 已连接 + 未被占用 + 租约管理 + 异常兜底），与仪器类动作保持一致。

读类（low，不持租约，仪器忙时拒绝以免抢占运行中测试）：
  scope_measure_channel  : 一次取 PK2PK/FREQUENCY/VMAX/VMIN 四项（容忍单项失败）；
  scope_get_measurement  : 按类型取单项测量（pk2pk/frequency/mean/max/min/rms/amplitude）；
  scope_capture_screen   : 截屏 PNG 落盘到 user_data/ai/screenshots/，只回路径/尺寸/状态；
  scope_is_acquiring     : 读取采集状态（is_acquiring）。

写类（medium，不强制确认；high，必须确认；均持租约）：
  scope_autoscale        : medium，一键自动量程（仅 DSOX4034A 支持）；
  scope_run/stop/single  : medium，控制采集运行/停止/单次；
  scope_set_timebase     : high，设置时基（秒/格）；
  scope_set_channel_scale: high，设置通道垂直档位（V/格）；
  scope_set_trigger      : high，设置边沿触发（源/电平/斜率）。

截图为二进制，回灌模型时只回路径/尺寸/状态，图像走 P6 产物通道，
不塞进对话上下文（防撑爆 token）。本模块禁 import Qt。
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.handlers.instrument import _run_read_action, _run_write_action
from core.ai.actions.registry import CATEGORY_SCOPE, ActionSpec
from log_config import get_logger
from ui.resource_path import get_user_data_dir

logger = get_logger(__name__)

# 单项测量类型 -> 驱动方法名映射（DSOX4034A / MSO64B / MockMSO64B 通用子集）。
_MEASUREMENT_TYPES: dict[str, str] = {
    "pk2pk": "get_channel_pk2pk",
    "frequency": "get_channel_frequency",
    "mean": "get_channel_mean",
    "max": "get_channel_max",
    "min": "get_channel_min",
    "rms": "get_channel_rms",
    "amplitude": "get_channel_amplitude",
}

# scope_measure_channel 一次取的四项（对齐 OscilloscopeController.measure_channel）。
_BATCH_MEASUREMENTS: tuple[tuple[str, str], ...] = (
    ("PK2PK", "get_channel_pk2pk"),
    ("FREQUENCY", "get_channel_frequency"),
    ("VMAX", "get_channel_max"),
    ("VMIN", "get_channel_min"),
)

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="scope_measure_channel",
        description=(
            "对已连接示波器指定通道一次性取 PK2PK/FREQUENCY/VMAX/VMIN 四项测量"
            "（经 InstrumentManager，容忍单项失败）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer", "minimum": 1, "maximum": 4},
            },
            "required": ["session_id", "channel"],
        },
        risk_level="low",
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_get_measurement",
        description=(
            "对已连接示波器指定通道按类型取单项测量（pk2pk/frequency/mean/max/min/rms/amplitude）。"
            "amplitude 仅部分型号支持。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer", "minimum": 1, "maximum": 4},
                "type": {
                    "type": "string",
                    "enum": list(_MEASUREMENT_TYPES.keys()),
                    "description": "测量类型。",
                },
            },
            "required": ["session_id", "channel", "type"],
        },
        risk_level="low",
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_capture_screen",
        description=(
            "截取已连接示波器屏幕 PNG 并落盘到用户数据目录，返回文件路径/字节数/状态"
            "（图像不塞进对话上下文，仅回路径，便于后续查看或导出）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "invert": {
                    "type": "boolean",
                    "description": "是否反色（白底），默认 False。",
                },
            },
            "required": ["session_id"],
        },
        risk_level="low",
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_autoscale",
        description="对已连接示波器执行一键自动量程（仅 DSOX4034A 支持，MSO64B 无此能力）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="medium",
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_set_timebase",
        description="设置已连接示波器的时基（秒/格，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "seconds_per_div": {
                    "type": "number",
                    "minimum": 1e-12,
                    "description": "每格时间（秒），如 1e-6 表示 1 μs/div。",
                },
            },
            "required": ["session_id", "seconds_per_div"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_set_channel_scale",
        description="设置已连接示波器指定通道的垂直档位（V/格，high：必须弹确认后才下发）。",
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "channel": {"type": "integer", "minimum": 1, "maximum": 4},
                "volts_per_div": {
                    "type": "number",
                    "minimum": 1e-3,
                    "description": "每格电压（V）。",
                },
            },
            "required": ["session_id", "channel", "volts_per_div"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_set_trigger",
        description=(
            "设置已连接示波器的边沿触发（源通道/触发电平/斜率，high：必须弹确认后才下发）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "source": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4,
                    "description": "触发源通道号（1~4）。",
                },
                "level": {"type": "number", "description": "触发电平（V）。"},
                "slope": {
                    "type": "string",
                    "enum": ["POS", "NEG", "EITH"],
                    "description": "触发斜率：POS 上升沿 / NEG 下降沿 / EITH 任一边沿。",
                },
            },
            "required": ["session_id", "source", "level"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_run",
        description="让已连接示波器进入连续采集（RUN）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="medium",
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_stop",
        description="停止已连接示波器的采集（STOP）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="medium",
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_single",
        description="让已连接示波器执行单次采集（SINGLE）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="medium",
        category=CATEGORY_SCOPE,
    ),
    ActionSpec(
        name="scope_is_acquiring",
        description="读取已连接示波器当前是否正在采集（is_acquiring）。",
        parameters_schema={
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
        risk_level="low",
        category=CATEGORY_SCOPE,
    ),
]


def _save_screenshot(session_id: str, png_data: bytes) -> str | None:
    """把截屏 PNG 落盘到 user_data/ai/screenshots/，返回绝对路径。"""
    if not png_data:
        return None
    out_dir = get_user_data_dir("ai", "screenshots")
    safe_sid = session_id.replace(":", "_").replace("\\", "_").replace("/", "_")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"scope_{safe_sid}_{ts}.png")
    with open(path, "wb") as fh:
        fh.write(png_data)
    return path


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def scope_measure_channel(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))

        def apply(instance: Any) -> dict:
            result: dict[str, Any] = {"channel": channel}
            for mtype, method_name in _BATCH_MEASUREMENTS:
                fn = getattr(instance, method_name, None)
                if not callable(fn):
                    result[mtype] = None
                    continue
                try:
                    result[mtype] = fn(channel)
                except Exception as exc:  # noqa: BLE001 - 单项失败不阻断其余项
                    logger.debug("scope_measure_channel %s 失败：%s", mtype, exc)
                    result[mtype] = f"ERROR: {exc}"
            return result

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"通道 {channel} 批量测量完成（PK2PK/FREQUENCY/VMAX/VMIN）。",
        )

    def scope_get_measurement(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))
        meas_type = str(args.get("type", "")).strip().lower()
        method_name = _MEASUREMENT_TYPES.get(meas_type)
        if method_name is None:
            return {
                "ok": False,
                "_message": f"不支持的测量类型：{meas_type}（可选 {list(_MEASUREMENT_TYPES.keys())}）。",
            }

        def apply(instance: Any) -> dict:
            fn = getattr(instance, method_name, None)
            if not callable(fn):
                raise AttributeError(f"该示波器不支持 {method_name}。")
            return {"channel": channel, "type": meas_type, "value": fn(channel)}

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"通道 {channel} 的 {meas_type} 测量完成。",
        )

    def scope_capture_screen(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        invert = bool(args.get("invert", False))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "capture_screen_png", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持截屏。")
            png_data = fn(invert=invert)
            if not png_data:
                return {
                    "captured": False,
                    "bytes": 0,
                    "_message": "仪器未返回截图数据（可能是 Mock 模式或采集未就绪）。",
                }
            path = _save_screenshot(session_id, png_data)
            return {
                "captured": True,
                "bytes": len(png_data),
                "path": path,
                "invert": invert,
                "_message": f"截屏已保存：{path}" if path else "截屏已捕获但落盘失败。",
            }

        result = _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"示波器 {session_id} 截屏完成。",
        )
        if (
            result.get("ok")
            and result.get("path")
            and deps.artifact_registry is not None
        ):
            result["artifact_id"] = deps.artifact_registry.register(
                "scope_screenshot",
                result["path"],
                session_id=session_id,
                bytes=int(result.get("bytes", 0)),
            )
        return result

    def scope_autoscale(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "autoscale", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 autoscale（仅 DSOX4034A 支持）。")
            fn()
            return {}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"示波器 {session_id} 已执行自动量程。",
        )

    def scope_set_timebase(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        seconds_per_div = float(args.get("seconds_per_div", 0.0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_timebase_scale", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 set_timebase_scale。")
            fn(seconds_per_div)
            return {"seconds_per_div": seconds_per_div}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置时基为 {seconds_per_div} s/div。",
        )

    def scope_set_channel_scale(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        channel = int(args.get("channel", 0))
        volts_per_div = float(args.get("volts_per_div", 0.0))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_channel_scale", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 set_channel_scale。")
            fn(channel, volts_per_div)
            return {"channel": channel, "volts_per_div": volts_per_div}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置通道 {channel} 垂直档位为 {volts_per_div} V/div。",
        )

    def scope_set_trigger(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))
        source = int(args.get("source", 0))
        level = float(args.get("level", 0.0))
        slope = str(args.get("slope", "POS")).strip().upper() or "POS"
        if slope not in ("POS", "NEG", "EITH"):
            return {"ok": False, "_message": "slope 必须为 POS / NEG / EITH。"}

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "set_trigger_config", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 set_trigger_config。")
            fn(source, level, slope)
            return {"source": source, "level": level, "slope": slope}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"已设置触发：源 CH{source}，电平 {level} V，斜率 {slope}。",
        )

    def scope_run(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "run", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 run。")
            fn()
            return {}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"示波器 {session_id} 已进入连续采集（RUN）。",
        )

    def scope_stop(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "stop", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 stop。")
            fn()
            return {}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"示波器 {session_id} 已停止采集（STOP）。",
        )

    def scope_single(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "single", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 single。")
            fn()
            return {}

        return _run_write_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"示波器 {session_id} 已发起单次采集（SINGLE）。",
        )

    def scope_is_acquiring(args: dict) -> dict:
        session_id = str(args.get("session_id", ""))

        def apply(instance: Any) -> dict:
            fn = getattr(instance, "is_acquiring", None)
            if not callable(fn):
                raise AttributeError("该示波器不支持 is_acquiring。")
            return {"acquiring": bool(fn())}

        return _run_read_action(
            deps.instrument_manager,
            session_id,
            apply,
            f"示波器 {session_id} 采集状态读取完成。",
        )

    return {
        "scope_measure_channel": scope_measure_channel,
        "scope_get_measurement": scope_get_measurement,
        "scope_capture_screen": scope_capture_screen,
        "scope_autoscale": scope_autoscale,
        "scope_set_timebase": scope_set_timebase,
        "scope_set_channel_scale": scope_set_channel_scale,
        "scope_set_trigger": scope_set_trigger,
        "scope_run": scope_run,
        "scope_stop": scope_stop,
        "scope_single": scope_single,
        "scope_is_acquiring": scope_is_acquiring,
    }
